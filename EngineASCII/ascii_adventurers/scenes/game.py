"""
scenes/game.py -- the in-game scene: walk, aim, shoot, fight, scroll.

Players. The game runs a list of players (players/player.py), each with a
hero, a control source and a camera of their own, free to roam anywhere.
Solo play is a list of one. The world streams, and enemies wake and think,
around every player's view; enemies pick targets among all heroes. Debug
ghost players (run.py --ghosts N) are bots that exercise this.

Clock. The world advances in fixed steps of 1/SIM_HZ s (see config), as
many per frame as real time calls for (at most MAX_STEPS_PER_FRAME):

  step:  every player's controls are read (walk / aim point / trigger /
         card choice / roll) -> heroes roll or walk (box collision; roll
         cards act along the way, systems/roll.py) -> effects age ->
         heroes aim and fire (enemies nearby hear it), their spells work ->
         awake enemies near any player think and act (chilled ones slower,
         frozen ones not at all) -> shots move and hit (terrain, heroes,
         enemies; friendly fire on; rolling heroes can't be hit, Close
         Call counts the shots they rolled through) -> statuses tick ->
         deaths (chain
         reactions; a player's kill drops an XP gem and is worth loot at
         once) -> gems fly to the
         heroes who pull them in (XP, level-ups) -> enemies wake near
         players / sleep far away.
  frame: steps -> cameras ease toward their heroes -> the frame's sounds ->
         chunk streaming with the time left.

The step depends only on the game state and the players' inputs -- never
on frame timing (cameras, chunk-loading progress) -- so the same inputs
give the same game on any machine at any frame rate. Anything added to
the step must keep it that way (e.g. no time.time(), no unseeded random).
  draw:  (positions blended between the last two steps, so motion is
         smooth at any refresh rate) terrain -> ground effects -> enemies ->
         heroes -> shots -> air effects -> minimap -> crosshair -> HUD ->
         big map / pause / game over.

The view shows one player (the local one; F10 cycles through the others
while debug ghosts are running).

Quests (M17, systems/quests.py): each ring biome's quest giver waits at
their camp, pinned on the maps; E (gamepad A) next to them talks. Their
quest's targets, its boss's lair, the sealed fight and the rewards are run
by the Quests object inside the step; the HUD shows the quest log, a boss's
health bar, and an arrow toward the boss when it's off screen.

M opens the big map (ui/maps.py), ESC the pause menu (ui/overlays.py); both
pause the game. Shift dodge-rolls. Gamepads: Start pauses, Back opens the
map, the sticks walk and aim, the right trigger fires, B or LB rolls. The run's stats (meta/run_stats.py) are
kept per player; when every human player has fallen, or the run is
abandoned or quit, the local player's are folded into the saved records
once, and the game-over box shows them while the world keeps running.
"""

from __future__ import annotations

import math
import time
from contextlib import contextmanager

import pygame

from engine import Scene, TextRenderer

from .. import config, palette
from ..ai.brain import AIContext
from ..app import app_of
from ..engine_ext.camera import Camera
from ..engine_ext.gamepads import BUTTON_A, BUTTON_B, BUTTON_LB, BUTTON_RB, EV_BUTTON
from ..engine_ext.input import Mouse, move_axes
from ..entities.character import Character
from ..entities.effects import Effect, update_effects
from ..entities.gems import Gem, drop, update_gems
from ..entities.projectile import Projectile
from ..meta.run_stats import RunStats
from ..players.cards import build_loadout, draw_offer
from ..players.controls import AutoControls, GhostControls, PlayerInput
from ..players.player import Player, player_color
from ..render.ascii_fx import draw_effects, draw_projectiles
from ..render.bosses import draw_banner, draw_froggy, draw_npc, draw_pointer
from ..render.characters import draw_body
from ..render.enemies_sprite import draw_enemy
from ..render.slash import draw_slashes
from ..render.spell_fx import draw_gems, draw_spells, draw_statuses, draw_summons
from ..render.sprites import SpriteBank
from ..render.terrain import TerrainRenderer
from ..systems import combat, roll
from ..systems.quests import Quests, free_spot
from ..systems.spawner import Spawner
from ..systems.run_rules import RunRules, pact_totals
from ..systems.spells import sync_spells, update_spells
from ..systems.statuses import update_statuses
from ..systems.zones import update_zones
from ..ui.crosshair import draw_crosshair
from ..ui.frame import center, dim_canvas
from ..ui.card_picker import CardPicker
from ..ui.hud import HudInfo, draw_hud
from ..ui.maps import BigMap, Minimap
from ..ui.quest_log import draw_quest_log
from ..ui.overlays import GameOverPanel, PauseMenu
from ..ui.settings_panel import SettingsPanel
from ..world import make_world
from ..world.rng import hash_coords
from .common import app_events

# Effects drawn under the characters (they belong to the ground).
_GROUND_EFFECTS = ("tile_flash", "fizzle", "burrow", "roll_dust")
# The game-over box appears this long after the last hero falls (the death
# is seen first, and a click that was firing can't hit its buttons).
_GAME_OVER_DELAY = 1.0


class GameScene(Scene):
    def __init__(self, hero: str | None = None, seed: int | None = None) -> None:
        self.hero_key = hero          # None: the last hero picked (settings)
        self.seed_choice = seed       # None: a random island

    # --- Setup ---------------------------------------------------------------------------

    def on_enter(self) -> None:
        self.app = app_of(self.manager)
        if self.hero_key not in config.HEROES:
            s = self.app.settings
            self.hero_key = s.hero if s.hero in config.HEROES else config.START_HERO
        self.world = make_world(self.seed_choice)
        self.spawn = self.world.spawn_point()
        seed = getattr(self.world, "seed", None)
        self.mouse = Mouse(self.manager.display)
        # The pacts switched on at the dungeon gate (design/GUILD.md 4.3), and
        # the cards that react to what happens (systems/run_rules.py).
        self.pact_keys = sorted(self.app.guild.active_pacts)
        self.pacts = pact_totals(self.pact_keys)
        self.rules = RunRules(self)
        self.zones: list = []
        self.players: list[Player] = [self._make_player(0, self.hero_key, local=True)]
        for i in range(self.app.ghosts):
            heroes = [h for h in config.HEROES if h != self.hero_key] or list(config.HEROES)
            self.players.append(self._make_player(i + 1, heroes[i % len(heroes)], ghost=True))
        self.view_index = 0               # which player the screen shows
        self.sprites = SpriteBank(self.manager.text, config.CELLS_PER_TILE)
        self.terrain = TerrainRenderer(self.manager.text)
        self.sfx = self.app.sfx
        self.projectiles: list[Projectile] = []
        self.effects: list[Effect] = []
        self.enemies: list = []
        self.gems: list[Gem] = []
        self.spawner = Spawner(self.world, seed) if seed is not None else None
        self._update_spawner()
        self.quests = Quests(self)
        # Maps exist only on the island (the test map has no layout).
        self.big_map = BigMap(self.world) if self.players[0].minimap is not None else None
        self._run_recorded = False
        self.broken: set[str] = set()     # records this run broke
        self.overlay = None               # None | PauseMenu | SettingsPanel | GameOverPanel
        self._pause_menu = None
        self.game_over_for = -1.0         # seconds since every human fell; <0: someone's alive
        self.fps = 60.0
        self.steps = 0                    # simulation steps run so far
        self._acc = 0.0                   # real time not yet simulated
        self.alpha = 1.0                  # draw blend between the last two steps
        self._sounds: list[str] = []
        self._last_draw_ms = 0.0
        self._stream_world(budget_ms=None)  # build the start area up front
        pygame.mouse.set_visible(False)

    def _make_player(self, index: int, hero_key: str, local=False, ghost=False) -> Player:
        d = self.manager.display
        sx, sy = self.spawn
        if ghost:                          # side by side, facing the same island
            sx, sy = self._free_spot(sx + 2.0 * index, sy)
        hero = Character(config.HEROES[hero_key], sx, sy)
        camera = Camera(d.cols, d.rows - config.HUD_ROWS, d.cell_w, d.cell_h)
        camera.center_on(sx, sy)
        seed = getattr(self.world, "seed", None)
        hero.rng.seed(hash_coords(seed or 0, 0x5EED, index))   # crits, evasions: replayable
        guild = self.app.guild
        meta = [] if ghost else guild.meta_steps(hero_key)
        if not ghost and self.pacts["hero_hp"]:                    # Pact of Glass
            meta.append(("max_hp_mult", "mul", 1 + self.pacts["hero_hp"]))
        if ghost:
            hero.invulnerable = True
            controls = GhostControls((seed or 0) * 31 + index)
        else:
            controls = AutoControls(self.mouse, self.app.pads)
        has_maps = getattr(self.world, "layout", None) is not None
        p = Player(index, hero, controls, camera, RunStats(hero_key, seed, (sx, sy)),
                   local=local, ghost=ghost, color=player_color(index),
                   minimap=Minimap() if has_maps and local else None,
                   meta=meta, unlocked=None if ghost else guild.unlocked_cards())
        self._apply_loadout(p)
        st = hero.stats
        prog = p.progress
        prog.rerolls += round(st.rerolls)
        prog.banishes += round(st.banishes)
        if st.start_level:                                         # Recruit's Kit
            prog.level += round(st.start_level)
            prog.picks += round(st.start_level)
        if st.royal_decree:                                        # Royal Decree
            prog.decree = config.RARITIES[min(4, 1 + round(st.royal_decree))]
            prog.picks += 1
        if not ghost:
            hero.bestiary = guild.known_pages()
        return p

    def _update_spawner(self) -> None:
        """Pacts, Beacon and Bounty: how many enemies, how tough, how fast."""
        sp = self.spawner
        if sp is None:
            return
        flags = set()
        for p in self.players:
            if not p.ghost and p.hero.stats is not None:
                flags |= p.hero.stats.flags
        pacts = self.pacts
        sp.density = (1 + pacts["enemy_count"]) * (1 + (config.BEACON_SPAWNS if "beacon" in flags
                                                        else 0.0))
        sp.level_bonus = pacts["enemy_levels"]
        sp.damage_bonus = pacts["enemy_damage"]
        sp.haste = pacts["enemy_haste"] + (config.HASTE_BOUNTY if "bounty" in flags else 0.0)

    def _free_spot(self, x: float, y: float) -> tuple[float, float]:
        from ..systems.collision import hull_hits_solid
        half = config.HEROES[self.hero_key].size_px / 2
        for r in range(0, 12):
            for dx, dy in ((r, 0), (-r, 0), (0, r), (0, -r)):
                if not hull_hits_solid(self.world, x + dx, y + dy, 0.0, half, half):
                    return x + dx, y + dy
        return x, y

    def on_exit(self) -> None:
        pygame.mouse.set_visible(True)

    # --- The local player (single-player code, HUD, tests) --------------------------------

    @property
    def me(self) -> Player:
        return self.players[0]

    @property
    def hero(self) -> Character:
        return self.me.hero

    @property
    def stats(self) -> RunStats:
        return self.me.stats

    @property
    def camera(self) -> Camera:
        return self.viewed.camera

    @property
    def viewed(self) -> Player:
        return self.players[self.view_index % len(self.players)]

    @property
    def player_dead(self) -> bool:
        return not self.me.alive

    # --- Run end / overlays ------------------------------------------------------------

    def _end_run(self) -> None:
        """Fold this run into the records (once, however the run ends)."""
        if self._run_recorded:
            return
        self._run_recorded = True
        self.broken = self.app.records.add_run(self.stats)
        self.app.save_records()
        self.app.guild.bank_run(self.stats)      # loot is kept however the run ends
        self.app.save_guild()

    def _set_overlay(self, overlay) -> None:
        self.overlay = overlay
        pygame.mouse.set_visible(overlay is not None or self.map_open)
        if overlay is None:
            for p in self.players:
                p.controls.block_fire()     # the click that closed it doesn't fire

    def _pause(self) -> None:
        # One pause menu per run, so coming back from Settings keeps its place.
        if self._pause_menu is None:
            self._pause_menu = PauseMenu(
                self.manager, self.stats, resume=lambda: self._set_overlay(None),
                settings=self._open_settings, abandon=self._abandon, quit_game=self._quit,
                details=self._where)
        self._set_overlay(self._pause_menu)

    def _where(self) -> str:
        """Biome, distance from the start and seed (the pause menu's line;
        they're not on the HUD)."""
        h = self.viewed.hero
        biome_at = getattr(self.world, "biome_at", None)
        biome = biome_at(math.floor(h.x), math.floor(h.y)).name.upper() if biome_at else "TEST MAP"
        dist = math.hypot(h.x - self.spawn[0], h.y - self.spawn[1])
        seed = getattr(self.world, "seed", None)
        return f"{biome}   {dist:.0f} tiles out" + (f"   seed {seed}" if seed is not None else "")

    def _open_settings(self) -> None:
        self._set_overlay(SettingsPanel(self.manager, self._pause))

    def _abandon(self) -> None:
        self._end_run()
        from .title import TitleScene
        self.manager.switch_to(TitleScene())

    def _quit(self) -> None:
        self._end_run()
        self.manager.quit()

    def _change_hero(self) -> None:
        from .new_run import NewRunScene
        self.manager.switch_to(NewRunScene())

    def _guild_hall(self) -> None:
        self._end_run()
        from .guild_hall import GuildHallScene
        self.manager.switch_to(GuildHallScene(self.hero_key))

    def _dev_level_up(self) -> None:
        """Developer mode: exactly enough XP for the next level (its card
        offer comes up as usual)."""
        prog = self.me.progress
        if prog.add(prog.needed - prog.xp):
            self.effects.append(Effect("levelup", self.hero.x, self.hero.y))
            self._sounds.append("chime")

    def _dev_quest(self, key: int) -> None:
        """Developer mode: F6 jumps next to the first quest giver, F7
        finishes its hunt (the boss wakes), F8 jumps outside its lair's gate."""
        if key == pygame.K_F7:
            if self.quests.dev_finish_hunt():
                self._sounds.append("chime")
            return
        spot = self.quests.dev_spot("giver" if key == pygame.K_F6 else "lair")
        if spot is None or not self.me.alive:
            return
        h = self.hero
        self._stream_world(budget_ms=None)
        self.world.ensure_ready(int(spot[0]) - 48, int(spot[1]) - 20, int(spot[0]) + 48,
                                int(spot[1]) + 20)
        h.x, h.y = free_spot(self.world, *spot, h.half)
        h.prev_pos = (h.x, h.y)
        self.me.camera.center_on(h.x, h.y)
        self._stream_world(budget_ms=None)

    def _restart(self) -> None:
        """Go again: same hero, and the same island if a seed was chosen."""
        self.manager.switch_to(GameScene(self.hero_key, self.seed_choice))

    @property
    def map_open(self) -> bool:
        return self.big_map is not None and self.big_map.is_open

    def _toggle_map(self) -> None:
        if self.map_open:
            self.big_map.close()
            for p in self.players:
                p.controls.block_fire()
        else:
            self.big_map.open(self.viewed.hero.x, self.viewed.hero.y)
        pygame.mouse.set_visible(self.map_open)   # a real cursor for dragging

    # --- Events ------------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        in_menu = self.overlay is not None or self.map_open
        if self.map_open and event.type == EV_BUTTON and event.button in (BUTTON_LB, BUTTON_RB):
            self._pad_zoom(1 if event.button == BUTTON_RB else -1)
            return
        if not in_menu and event.type == EV_BUTTON and event.button == BUTTON_A:
            self.me.controls.queue_interact()     # talk (in play, A isn't a menu key)
            return
        if not in_menu and event.type == EV_BUTTON and event.button in (BUTTON_B, BUTTON_LB):
            self.me.controls.queue_roll()
            return
        for ev in app_events(self.manager, event, menu=in_menu):
            self._handle(ev)

    def _pad_zoom(self, notches: int) -> None:
        d = self.manager.display
        centre = (d.canvas.get_width() / 2, self.camera.view_h / 2)
        self.big_map.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=notches),
                                  centre, d.cell_w, d.cell_h,
                                  (self.viewed.hero.x, self.viewed.hero.y))

    def _handle(self, event: pygame.event.Event) -> None:
        if self.overlay is not None:
            if isinstance(self.overlay, PauseMenu) and event.type == pygame.KEYDOWN \
                    and event.key == pygame.K_ESCAPE:
                self._set_overlay(None)
            elif isinstance(self.overlay, GameOverPanel) and event.type == pygame.KEYDOWN \
                    and event.key == pygame.K_r:
                self._restart()
            elif isinstance(self.overlay, CardPicker) and event.type == pygame.KEYDOWN \
                    and event.key == pygame.K_ESCAPE:
                self._pause()      # the cards come back when the game resumes
            else:
                self.overlay.handle_event(event)
            return
        if self.map_open:
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_m, pygame.K_ESCAPE):
                self._toggle_map()
                return
            d = self.manager.display
            pos = getattr(event, "pos", None) or pygame.mouse.get_pos()
            self.big_map.handle_event(event, d.window_to_canvas(*pos), d.cell_w, d.cell_h,
                                      (self.viewed.hero.x, self.viewed.hero.y))
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._pause()
            elif event.key == pygame.K_m and self.big_map is not None:
                self._toggle_map()
            elif event.key == pygame.K_r and self.player_dead:
                self._restart()
            elif event.key == pygame.K_F10 and len(self.players) > 1:
                self.view_index = (self.view_index + 1) % len(self.players)
            elif event.key == pygame.K_e:
                self.me.controls.queue_interact()
            elif event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                self.me.controls.queue_roll()
            elif event.key == pygame.K_l and self.app.dev and self.me.alive:
                self._dev_level_up()
            elif event.key in (pygame.K_F6, pygame.K_F7, pygame.K_F8) and self.app.dev:
                self._dev_quest(event.key)

    # --- Frame -------------------------------------------------------------------------

    def update(self, dt: float) -> None:
        started = time.perf_counter()
        if dt > 0:                       # smoothed FPS readout (real frame time)
            self.fps += (1.0 / dt - self.fps) * 0.05
        if self.map_open:
            self.big_map.pan(*self._pan_axes(), min(dt, config.MAX_DT))
            return   # the game is paused behind the map
        if self.overlay is not None and getattr(self.overlay, "pauses", True) \
                and not isinstance(self.overlay, GameOverPanel):
            return   # paused (pause menu, settings, or choosing a card in single player)

        d = self.manager.display
        for p in self.players:
            p.camera.resize(d.cols, d.rows - config.HUD_ROWS)

        # Run as many fixed steps as real time calls for.
        step = 1.0 / config.SIM_HZ
        self._acc = min(self._acc + dt, step * config.MAX_STEPS_PER_FRAME)
        while self._acc >= step - 1e-9:
            self._remember_positions()
            self._step(step)
            self._acc -= step
        self._acc = max(self._acc, 0.0)
        self.alpha = min(1.0, self._acc / step)

        # Cameras ease toward where their heroes are drawn this frame.
        frame_dt = min(dt, config.MAX_DT)
        for p in self.players:
            p.camera.follow(*self._drawn_pos(p.hero), frame_dt)

        # Cards on offer: up they come (pausing the game in single player).
        if self.overlay is None and self.me.alive and self.me.progress.offer:
            self._set_overlay(CardPicker(self.manager, self.me.progress, self._choose_card,
                                         spells=self._spell_levels(self.me), pauses=self._solo))
        else:
            self._sync_picker()      # (multiplayer: choices land with the next step)

        if self.game_over_for >= _GAME_OVER_DELAY and self.overlay is None:
            self._set_overlay(GameOverPanel(
                self.manager, self.stats, self.app.records, self.broken,
                again=self._restart, change_hero=self._change_hero, title=self._abandon,
                guild_hall=self._guild_hall, purse=self.app.guild.loot))

        for name in dict.fromkeys(self._sounds):   # each sound at most once per frame
            self.sfx.play(name)
        self._sounds.clear()

        # Chunk generation gets whatever is left of this frame's time: the
        # frame target minus this update's work so far and last frame's
        # drawing, capped at CHUNK_BUILD_BUDGET_MS and never below
        # CHUNK_BUILD_MIN_MS (so streaming always progresses). Heavy frames
        # (e.g. a wide grid) generate less and catch up on lighter ones;
        # the load margin gives plenty of slack before a chunk is on screen.
        used_ms = (time.perf_counter() - started) * 1000 + self._last_draw_ms
        budget = config.FRAME_TARGET_MS - used_ms
        self._stream_world(max(config.CHUNK_BUILD_MIN_MS, min(config.CHUNK_BUILD_BUDGET_MS, budget)))

    def _pan_axes(self) -> tuple[float, float]:
        ax, ay = move_axes()
        if not (ax or ay):
            for pad in self.app.pads.pads:
                sx, sy = pad.left_stick()
                if sx or sy:
                    return sx, sy
        return ax, ay

    # --- Simulation step ------------------------------------------------------------------

    def _step(self, dt: float) -> None:
        self.steps += 1
        sounds = self._sounds
        living = [p for p in self.players if p.alive]

        inputs: dict[int, PlayerInput] = {}
        for p in living:
            inp = p.controls.read(p.hero, p.camera, self.world, self.enemies)
            if inp.pick is None:
                inp.pick = p.controls.take_pick()
            inp.interact = inp.interact or p.controls.take_interact()
            inp.roll = inp.roll or p.controls.take_roll()
            if p.ghost and p.progress.offer:
                inp.pick = 0                  # bots take the first card
            if p.hero.stats is not None and p.hero.stats.has("hunters_mark"):
                self._hunters_mark(p, dt)
            inputs[p.index] = inp
            self._cards(p, inp.pick)
            self.rules.tick(p, dt)
            if p.regen > 0 and not self.pacts["famine"]:
                p.hero.heal(p.regen * dt)
            roll.step(self, p, inp, dt)
            rolling, x0, y0 = p.hero.rolling, p.hero.x, p.hero.y
            p.hero.move(inp.move_x, inp.move_y, dt, self.world)
            roll.after_move(self, p, rolling, x0, y0)
            biome_at = getattr(self.world, "biome_at", None)
            biome = biome_at(math.floor(p.hero.x), math.floor(p.hero.y)).name if biome_at else None
            p.stats.tick(dt, p.hero.x, p.hero.y, p.hero.walked, biome)

        update_effects(self.effects, dt)   # age first: new effects show frame 0
        for p in living:
            inp = inputs[p.index]
            if inp.aim is not None:
                p.hero.aim_at(*inp.aim, dt)
                p.aim = inp.aim
            weapon = p.hero.weapon
            if weapon.update(self.rules.weapon_dt(p, dt), inp.fire or weapon.spec.auto):
                self._attack(p)
            if p.spells:
                cast = update_spells(p.hero, p.spells, self.world, self._actors(), self.effects, dt,
                                     self.projectiles, self.zones)
                if p.local:
                    sounds += cast

        # Enemies act. Only those near some player think; others wait frozen.
        heroes = [p.hero for p in self.players]
        ctx = AIContext(self.world, heroes, self._actors(), self.projectiles, self.effects)
        m = config.ENEMY_ACTIVE_MARGIN
        boxes = [(f.x - f.half_w - m, f.x + f.half_w + m, f.y - f.half_h - m, f.y + f.half_h + m)
                 for f in (p.focus() for p in self.players if p.alive or not p.ghost)]
        for h in heroes:
            h.tick_flash(dt)
        for e in self.enemies:
            e.tick_flash(dt)
            if e.alive:
                x, y = e.x, e.y
                # Chill slows the enemy's whole clock; frozen, it doesn't act.
                # Pacts and Bounty speed it up.
                scale = (e.status.time_scale if e.status is not None else 1.0) * (1 + getattr(e, "haste", 0.0))
                if getattr(e, "boss", False):
                    # A boss fights wherever it is in its arena, and is
                    # never frozen solid.
                    e.think(ctx, dt * max(scale, config.BOSS_MIN_TIME_SCALE))
                    continue
                if scale <= 0:
                    continue
                for x0, x1, y0, y1 in boxes:
                    if x0 <= x <= x1 and y0 <= y <= y1:
                        e.think(ctx, dt * scale)
                        break
        sounds += ctx.events
        ctx.events.clear()

        sounds += combat.update_projectiles(self.projectiles, self.world, self.effects, dt,
                                            self._actors(), self.zones)
        roll.close_calls(self.players, self.projectiles, dt)
        update_zones(self.zones, self._actors(), self.effects, dt)
        update_statuses(self.enemies, dt, self.effects)
        self.rules.resolve_combos()
        sounds += self._handle_deaths(ctx)
        self.quests.step(dt, self.players, inputs)
        for p, xp in update_gems(self.gems, self.players, dt):
            self._gain_xp(p, xp)
        for p in self.players:
            if p.hero.evaded:
                self.effects.append(Effect("evade", p.hero.x, p.hero.y - p.hero.hit_radius))
                p.hero.evaded = 0

        for p in self.players:
            if not p.alive:
                p.dead_for += dt
        if self.game_over_for >= 0:
            self.game_over_for += dt

        # Enemies wake near players (as tough as the highest human's level)
        # and sleep far from all of them.
        if self.spawner is not None:
            humans = [p.progress.level for p in self.players if not p.ghost]
            self.spawner.level = max(humans) if humans else 1
            self._update_spawner()
            self.spawner.update_views(self.enemies, self._views())

    def _attack(self, p: Player, echo: bool = False) -> None:
        """The hero's weapon goes off (with this attack's card changes)."""
        kw = self.rules.attack_mods(p, echo)
        shot = combat.attack(p.hero, self.world, self.projectiles, self.effects, self._actors(),
                             **kw)
        shot += self.rules.patterns(p, kw)
        if p.local:
            self._sounds.extend(shot)
        for e in self.enemies:
            e.hear(p.hero.x, p.hero.y)

    def _gain_xp(self, p: Player, xp: float) -> None:
        if p.progress.add(xp):
            self.effects.append(Effect("levelup", p.hero.x, p.hero.y))
            if p.local:
                self._sounds.append("chime")
            self.rules.on_level_up(p)

    # --- Cards ------------------------------------------------------------------------

    @property
    def _solo(self) -> bool:
        """One human player (debug ghosts don't count): card picks pause."""
        return sum(1 for p in self.players if not p.ghost) == 1

    def _choose_card(self, action) -> None:
        """The local player chose in the card picker: a card's index, or
        "reroll", "skip", ("banish", index). In single player the game is
        paused, so it's applied right away; otherwise it travels with the
        next step's input like any other."""
        me = self.me
        if self._solo:
            self._cards(me, action)
        else:
            me.controls.queue_pick(action)
        self._sync_picker()

    def _sync_picker(self) -> None:
        """Keep the picker showing the local player's offer; close it once
        there's none."""
        picker = self.overlay
        if not isinstance(picker, CardPicker):
            return
        if self.me.progress.offer:
            picker.refresh(self.me.progress, self._spell_levels(self.me))
        else:
            self._set_overlay(None)

    def _cards(self, p: Player, pick) -> None:
        """Act on the player's card choice, if any (see _choose_card), then
        put a new offer on the table while picks are banked."""
        prog = p.progress
        if pick is not None and prog.offer:
            if pick == "reroll":
                if prog.rerolls > 0:
                    prog.rerolls -= 1
                    prog.offer = []
            elif pick == "skip":
                prog.picks -= 1
                prog.resolved += 1
                prog.offer = []
                prog.decree = None
                if not self.pacts["famine"]:                       # Pact of Famine
                    p.hero.heal(p.hero.max_hp * config.SKIP_HEAL)
            elif isinstance(pick, tuple) and pick[0] == "banish":
                if prog.banishes > 0 and 0 <= pick[1] < len(prog.offer):
                    prog.banishes -= 1
                    prog.banished.add(prog.offer[pick[1]][0])
                    prog.offer = []
            elif isinstance(pick, int) and 0 <= pick < len(prog.offer):
                key, rarity = prog.offer[pick]
                prog.take(key, rarity)
                prog.picks -= 1
                prog.resolved += 1
                prog.offer = []
                prog.decree = None
                p.stats.cards.append(key)
                self._apply_loadout(p)
                self.rules.check_build(p)
            if p.local:
                self._sounds.append("ui")
        if prog.picks > 0 and not prog.offer:
            st = p.hero.stats
            size = config.CARD_OFFER_SIZE + round(st.offer_size)
            if st.encore_tour:                                     # Encore Tour
                every = max(2, 6 - round(st.encore_tour))
                if (prog.resolved + 1) % every == 0:
                    size += 1
            prog.offer = draw_offer(p.stats.hero, config.WEAPONS[config.HEROES[p.stats.hero].weapon],
                                    prog.cards, getattr(self.world, "seed", 0) or 0, p.index,
                                    prog.offers, st, prog.banished, p.unlocked,
                                    level=prog.level, size=size, min_rarity=prog.decree)
            prog.offers += 1
            if not prog.offer:
                prog.picks = 0             # every card maxed out: nothing left to offer

    @staticmethod
    def _spell_levels(p: Player) -> dict:
        return dict(p.hero.stats.spells) if p.hero.stats is not None else {}

    @staticmethod
    def _apply_loadout(p: Player) -> None:
        """Rebuild the hero from the base specs plus every card taken."""
        lo = build_loadout(p.stats.hero, p.progress.taken, p.meta)
        hero = p.hero
        gained = lo.body.max_hp - hero.max_hp
        old_shield = hero.stats.shield if hero.stats is not None else 0.0
        hero.shield += max(0.0, lo.stats.shield - old_shield)   # a new ward comes charged
        hero.spec = lo.body
        hero.weapon.spec = lo.weapon
        hero.stats = lo.stats
        hero.max_hp = lo.body.max_hp
        hero.hp = min(hero.max_hp, hero.hp + max(0, gained))   # new max HP comes filled
        hero.lifesteal = lo.stats.lifesteal
        p.regen = lo.stats.regen
        sync_spells(p.spells, lo.stats.spells)

    def _hunters_mark(self, p: Player, dt: float) -> None:
        """Hunter's Mark (a card): every MARK_INTERVAL s (or when the mark
        dies) the toughest enemy in the player's view is marked."""
        hero = p.hero
        p.mark_timer -= dt
        if p.mark_timer > 0 and hero.marked is not None and hero.marked.alive:
            return
        p.mark_timer = config.MARK_INTERVAL
        f = p.focus()
        seen = [e for e in self.enemies if e.alive and e.hittable and f.near(e.x, e.y, 0.0)]
        hero.marked = max(seen, key=lambda e: (e.max_hp, -math.hypot(e.x - hero.x, e.y - hero.y)),
                          default=None)

    def _actors(self) -> list:
        return [p.hero for p in self.players if p.hero.alive] + [e for e in self.enemies if e.alive]

    def _player_of(self, actor) -> Player | None:
        return next((p for p in self.players if p.hero is actor), None)

    def _handle_deaths(self, ctx: AIContext) -> list[str]:
        """Remove dead enemies (with their death effects), repeating while
        deaths cause more deaths -- a popped puffer's spores can finish off
        a neighbour. The kill goes to the player whose hero hit it last (a
        monster killed by another monster counts for nobody). Also notices
        heroes falling, and the run ending when every human has."""
        events: list[str] = []
        while True:
            dying = [e for e in self.enemies if not e.alive]
            if not dying:
                break
            self.enemies = [e for e in self.enemies if e.alive]
            for e in dying:
                on_death = getattr(e, "on_death", None)
                if on_death is not None:
                    on_death(ctx)
                else:
                    self.effects.append(Effect("explosion", e.x, e.y))
                    events.append(combat.BREAK)
                if self.spawner is not None:
                    self.spawner.killed(e)
                killer = self._player_of(e.last_hit_by)
                self.quests.on_death(e, killer)
                if killer is not None:
                    killer.stats.killed(e.espec.name)
                    drop(self.gems, e.x, e.y, e.espec.xp)
                    self._loot(killer, e)
                    self.rules.on_kill(killer, e)
            ctx.actors = self._actors()
        events += ctx.events
        ctx.events.clear()
        for p in self.players:
            if not p.hero.alive and p.alive:
                if self.rules.revive(p):              # Phoenix, Second Chance
                    continue
                p.dead_for = 0.0
                self.projectiles = [s for s in self.projectiles if s.owner is not p.hero]
                self.effects.append(Effect("explosion", p.hero.x, p.hero.y))
                events.append(combat.BREAK)
        humans = [p for p in self.players if not p.ghost]
        if self.game_over_for < 0 and humans and not any(p.alive for p in humans):
            self.game_over_for = 0.0
            self._end_run()
        return events

    def _loot(self, p: Player, enemy, times: int = 1) -> None:
        """A kill's loot goes straight into the run's purse; a shard flies
        from the body to the hero to show it. The loot bonus and the active
        pacts' bonus add to it; `times`: a Bounty cache, worth many kills."""
        stats = p.hero.stats
        bonus = stats.loot if stats is not None else 0.0
        amount = (enemy.espec.xp * config.LOOT_PER_XP * (1 + bonus) * (1 + self.pacts["loot"])
                  * times)
        p.stats.loot += amount
        self.effects.append(Effect("loot", enemy.x, enemy.y, target=p.hero,
                                   value=max(1, round(amount))))

    # --- World streaming ------------------------------------------------------------------

    def _stream_world(self, budget_ms: float | None = config.CHUNK_BUILD_BUDGET_MS) -> None:
        """Load/unload chunks around every player's view, time-budgeted
        (enemies wake and sleep in the simulation step instead, from the
        players' positions alone). budget_ms=None builds everything needed
        right away (at startup)."""
        if getattr(self.world, "update_views", None) is None:
            return  # the fixed test map has nothing to stream
        # (A boss fight's arena stays loaded too: its boss roams all of it.)
        views = self._views() + self.quests.stream_views()
        if budget_ms is None:
            for p in self.players:
                self.world.ensure_ready(*p.camera.visible_tiles())
            budget_ms = 1e9
        self.world.update_views(views, budget_ms)
        self.world.drain_loaded()      # (the spawner works out rosters itself)

    def _views(self) -> list[tuple[float, float, float, float]]:
        return [(f.x, f.y, f.half_w, f.half_h) for f in (p.focus() for p in self.players)]

    # --- Drawing ---------------------------------------------------------------------------

    def _movers(self):
        yield from (p.hero for p in self.players)
        yield from self.enemies
        yield from self.projectiles
        yield from self.gems

    def _remember_positions(self) -> None:
        """Where everything was before this step, for blending when drawing."""
        for o in self._movers():
            o.prev_pos = (o.x, o.y)

    def _drawn_pos(self, o) -> tuple[float, float]:
        prev = getattr(o, "prev_pos", None)
        if prev is None:
            return o.x, o.y
        a = self.alpha
        return prev[0] + (o.x - prev[0]) * a, prev[1] + (o.y - prev[1]) * a

    @contextmanager
    def _blended(self):
        """Temporarily move everything to where it's drawn this frame
        (between the last two steps), so rendering code needn't know."""
        saved = []
        for o in self._movers():
            if getattr(o, "prev_pos", None) is not None:
                saved.append((o, o.x, o.y))
                o.x, o.y = self._drawn_pos(o)
        try:
            yield
        finally:
            for o, x, y in saved:
                o.x, o.y = x, y

    def draw(self, text: TextRenderer) -> None:
        started = time.perf_counter()
        with self._blended():
            self._draw(text)
        self._last_draw_ms = (time.perf_counter() - started) * 1000

    def _draw(self, text: TextRenderer) -> None:
        d = self.manager.display
        me = self.viewed
        cam = me.camera
        text.clear(palette.BACKGROUND)
        self.terrain.draw(self.world, cam)
        ground = [e for e in self.effects if e.kind in _GROUND_EFFECTS]
        air = [e for e in self.effects if e.kind not in _GROUND_EFFECTS]
        draw_effects(text, cam, self.world, ground)
        draw_gems(text, cam, self.gems, self.steps)
        margin = 3
        x0, y0 = cam.canvas_to_world(0, 0)
        x1, y1 = cam.canvas_to_world(cam.view_w, cam.view_h)
        for e in self.enemies:
            # (A boss is always drawn: its tells reach far beyond its body.)
            if getattr(e, "boss", False) or (x0 - margin <= e.x <= x1 + margin
                                             and y0 - margin <= e.y <= y1 + margin):
                draw_enemy(text, self.sprites, cam, self.world, e)
        talk_to = self.quests.npc_near(me.hero) if me.alive else None
        for npc in self.quests.npcs:
            if x0 - margin <= npc.x <= x1 + margin and y0 - margin <= npc.y <= y1 + margin:
                draw_npc(text, self.sprites, cam, npc, me.hero.x, npc is talk_to)
        for p in self.players:
            h = p.hero
            if p.alive and x0 - margin <= h.x <= x1 + margin and y0 - margin <= h.y <= y1 + margin:
                draw_body(self.sprites, cam, h)
        draw_statuses(text, cam, self.enemies, [p.hero.marked for p in self.players
                                                 if p.alive and p.hero.marked is not None])
        draw_spells(text, cam, [p for p in self.players if p.alive], self.steps)
        draw_summons(text, cam, [p for p in self.players if p.alive], self.zones, self.steps)
        draw_slashes(self.sprites, cam, self.effects)
        draw_projectiles(text, cam, self.projectiles)
        draw_effects(text, cam, self.world, air)
        others = [(p.hero.x, p.hero.y, p.color) for p in self.players if p is not me and p.alive]
        pins = self.quests.pins((me.hero.x, me.hero.y))
        fight = self.quests.fight
        if fight is not None and fight.boss is not None and fight.boss.alive and not self.map_open:
            b = fight.boss
            dist = math.hypot(b.x - me.hero.x, b.y - me.hero.y)
            draw_pointer(text, self.sprites, cam, b.x, b.y, f"{dist:.0f}")
        minimap = self.players[0].minimap
        if minimap is not None and not self.map_open and not isinstance(self.overlay, CardPicker):
            minimap.draw(text, self.sprites, self.world, me.hero.x, me.hero.y,
                         me.hero.aim_angle, others, pins)
        # No reticle for weapons that don't aim (the bard's pulse goes all round).
        if (me.alive and not self.map_open and self.overlay is None and not me.ghost
                and me.hero.weapon.spec.aims):
            if me.controls.uses_mouse:
                draw_crosshair(self.sprites, cam, self.mouse.canvas_pos)
            elif me.aim is not None:
                draw_crosshair(self.sprites, cam, cam.world_to_px(*me.aim))
        if not self.map_open:
            boss = None
            if fight is not None and fight.boss is not None and fight.boss.alive:
                boss = (fight.boss.espec.name, fight.boss.frac)
            draw_hud(text, HudInfo(
                hp=me.hero.hp, max_hp=me.hero.max_hp, level=me.progress.level,
                xp_frac=me.progress.frac, kills=me.stats.total_kills, time=me.stats.time,
                fps=self.fps if self.app.settings.show_fps else None,
                spells=tuple((s.spec.short, s.level) for s in me.spells.values()),
                loot=int(me.stats.loot), shield=me.hero.shield, boss=boss,
                roll=(me.hero.roll_charges, me.hero.stats.max_rolls if me.hero.stats else 1,
                      roll.recharge_frac(me.hero))))
            if self.quests.states:
                draw_quest_log(text, self.quests.log(), 6 if me.spells else 5)
            if self.quests.banner is not None and self.overlay is None:
                draw_banner(text, self.quests.banner)
            if talk_to is not None and self.overlay is None:
                center(text, d.rows - 3, f"  E / A: talk to the {talk_to.name}  ",
                       palette.HUB_PROMPT, bg=palette.HUD_PANEL)
        if self.app.dev and not self.map_open:
            text.put(0, d.rows - 1, " DEV  L: level up  F6: to quest giver  F7: finish hunt  "
                                    "F8: to lair ", palette.DEV_TAG, palette.HUD_PANEL)
        if self.map_open:
            self.big_map.draw(text, self.sprites, cam.view_rows,
                              (me.hero.x, me.hero.y), me.hero.aim_angle, others, pins,
                              self.quests.log())
        elif self.overlay is not None:
            dim_canvas(text, 110)
            self.overlay.draw(text)
