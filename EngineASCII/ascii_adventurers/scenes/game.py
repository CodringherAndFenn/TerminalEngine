"""
scenes/game.py -- the in-game scene: walk, aim, shoot, fight, scroll.

Players. The game runs a list of players (players/player.py), each with a
hero, a control source and a camera of their own, free to roam anywhere.
Solo play is a list of one. The world streams, and enemies wake and think,
around every player's view; enemies pick targets among all heroes. Debug
ghost players (run.py --ghosts N) are bots that exercise this.

Clock. The world advances in fixed steps of 1/SIM_HZ s (see config), as
many per frame as real time calls for (at most MAX_STEPS_PER_FRAME):

  step:  every player's controls are read (walk / aim point / trigger) ->
         heroes walk (box collision) -> effects age -> heroes aim and fire
         (enemies nearby hear it) -> awake enemies near any player think
         and act -> shots move and hit (terrain, heroes, enemies; friendly
         fire on) -> deaths (chain reactions, kill credit to the player who
         landed the last hit) -> enemies wake near players / sleep far away.
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

M opens the big map (ui/maps.py), ESC the pause menu (ui/overlays.py); both
pause the game. Gamepads: Start pauses, Back opens the map, the sticks walk
and aim, the right trigger fires. The run's stats (meta/run_stats.py) are
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
from ..engine_ext.gamepads import BUTTON_LB, BUTTON_RB, EV_BUTTON
from ..engine_ext.input import Mouse, move_axes
from ..entities.character import Character
from ..entities.effects import Effect, update_effects
from ..entities.projectile import Projectile
from ..meta.run_stats import RunStats
from ..players.controls import AutoControls, GhostControls, PlayerInput
from ..players.player import Player, player_color
from ..render.ascii_fx import draw_effects, draw_projectiles
from ..render.characters import draw_body
from ..render.enemies_sprite import draw_enemy
from ..render.sprites import SpriteBank
from ..render.terrain import TerrainRenderer
from ..systems import combat
from ..systems.spawner import Spawner
from ..ui.crosshair import draw_crosshair
from ..ui.frame import dim_canvas
from ..ui.hud import draw_hud
from ..ui.maps import BigMap, Minimap
from ..ui.overlays import GameOverPanel, PauseMenu
from ..ui.settings_panel import SettingsPanel
from ..world import make_world
from .common import app_events

# Effects drawn under the characters (they belong to the ground).
_GROUND_EFFECTS = ("tile_flash", "fizzle", "burrow")
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
        self.spawner = Spawner(self.world, seed) if seed is not None else None
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
        if ghost:
            hero.invulnerable = True
            controls = GhostControls((seed or 0) * 31 + index)
        else:
            controls = AutoControls(self.mouse, self.app.pads)
        has_maps = getattr(self.world, "layout", None) is not None
        return Player(index, hero, controls, camera, RunStats(hero_key, seed, (sx, sy)),
                      local=local, ghost=ghost, color=player_color(index),
                      minimap=Minimap() if has_maps and local else None)

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
                settings=self._open_settings, abandon=self._abandon, quit_game=self._quit)
        self._set_overlay(self._pause_menu)

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

    # --- Frame -------------------------------------------------------------------------

    def update(self, dt: float) -> None:
        started = time.perf_counter()
        if dt > 0:                       # smoothed FPS readout (real frame time)
            self.fps += (1.0 / dt - self.fps) * 0.05
        if self.map_open:
            self.big_map.pan(*self._pan_axes(), min(dt, config.MAX_DT))
            return   # the game is paused behind the map
        if self.overlay is not None and not isinstance(self.overlay, GameOverPanel):
            return   # paused (pause menu or settings)

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

        if self.game_over_for >= _GAME_OVER_DELAY and self.overlay is None:
            self._set_overlay(GameOverPanel(
                self.manager, self.stats, self.app.records, self.broken,
                again=self._restart, change_hero=self._change_hero, title=self._abandon))

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
            inputs[p.index] = inp
            p.hero.move(inp.move_x, inp.move_y, dt, self.world)
            biome_at = getattr(self.world, "biome_at", None)
            biome = biome_at(math.floor(p.hero.x), math.floor(p.hero.y)).name if biome_at else None
            p.stats.tick(dt, p.hero.x, p.hero.y, p.hero.walked, biome)

        update_effects(self.effects, dt)   # age first: new effects show frame 0
        for p in living:
            inp = inputs[p.index]
            if inp.aim is not None:
                p.hero.aim_at(*inp.aim, dt)
                p.aim = inp.aim
            if p.hero.weapon.update(dt, inp.fire):
                shot = combat.fire(p.hero, self.world, self.projectiles, self.effects)
                if p.local:
                    sounds += shot
                for e in self.enemies:
                    e.hear(p.hero.x, p.hero.y)

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
                for x0, x1, y0, y1 in boxes:
                    if x0 <= x <= x1 and y0 <= y <= y1:
                        e.think(ctx, dt)
                        break
        sounds += ctx.events
        ctx.events.clear()

        sounds += combat.update_projectiles(self.projectiles, self.world, self.effects, dt,
                                            self._actors())
        sounds += self._handle_deaths(ctx)

        for p in self.players:
            if not p.alive:
                p.dead_for += dt
        if self.game_over_for >= 0:
            self.game_over_for += dt

        # Enemies wake near players and sleep far from all of them.
        if self.spawner is not None:
            self.spawner.update_views(self.enemies, self._views())

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
                if killer is not None:
                    killer.stats.killed(e.espec.name)
            ctx.actors = self._actors()
        events += ctx.events
        ctx.events.clear()
        for p in self.players:
            if not p.hero.alive and p.alive:
                p.dead_for = 0.0
                self.projectiles = [s for s in self.projectiles if s.owner is not p.hero]
                self.effects.append(Effect("explosion", p.hero.x, p.hero.y))
                events.append(combat.BREAK)
        humans = [p for p in self.players if not p.ghost]
        if self.game_over_for < 0 and humans and not any(p.alive for p in humans):
            self.game_over_for = 0.0
            self._end_run()
        return events

    # --- World streaming ------------------------------------------------------------------

    def _stream_world(self, budget_ms: float | None = config.CHUNK_BUILD_BUDGET_MS) -> None:
        """Load/unload chunks around every player's view, time-budgeted
        (enemies wake and sleep in the simulation step instead, from the
        players' positions alone). budget_ms=None builds everything needed
        right away (at startup)."""
        if getattr(self.world, "update_views", None) is None:
            return  # the fixed test map has nothing to stream
        views = self._views()
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
        margin = 3
        x0, y0 = cam.canvas_to_world(0, 0)
        x1, y1 = cam.canvas_to_world(cam.view_w, cam.view_h)
        for e in self.enemies:
            if x0 - margin <= e.x <= x1 + margin and y0 - margin <= e.y <= y1 + margin:
                draw_enemy(text, self.sprites, cam, self.world, e)
        for p in self.players:
            h = p.hero
            if p.alive and x0 - margin <= h.x <= x1 + margin and y0 - margin <= h.y <= y1 + margin:
                draw_body(self.sprites, cam, h)
        draw_projectiles(text, cam, self.projectiles)
        draw_effects(text, cam, self.world, air)
        others = [(p.hero.x, p.hero.y, p.color) for p in self.players if p is not me and p.alive]
        minimap = self.players[0].minimap
        if minimap is not None and not self.map_open:
            minimap.draw(text, self.sprites, self.world, me.hero.x, me.hero.y,
                         me.hero.aim_angle, others)
        if me.alive and not self.map_open and self.overlay is None and not me.ghost:
            if me.controls.uses_mouse:
                draw_crosshair(self.sprites, cam, self.mouse.canvas_pos)
            elif me.aim is not None:
                draw_crosshair(self.sprites, cam, cam.world_to_px(*me.aim))
        draw_hud(text, d.cols, d.rows, me.hero, self.world, self.spawn,
                 self.fps if self.app.settings.show_fps else None, me.stats.total_kills)
        if self.map_open:
            self.big_map.draw(text, self.sprites, cam.view_rows,
                              (me.hero.x, me.hero.y), me.hero.aim_angle, others)
        elif self.overlay is not None:
            dim_canvas(text, 110)
            self.overlay.draw(text)
