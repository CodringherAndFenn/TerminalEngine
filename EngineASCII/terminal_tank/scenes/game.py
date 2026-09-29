"""
scenes/game.py -- the in-game scene: walk, aim, shoot, fight, scroll.

Per frame:
  update: clamp dt -> poll held keys -> walk the hero (box collision) ->
          ease the camera toward it -> map the mouse to the world -> aim ->
          fire while the left button is held (enemies nearby hear it) ->
          every awake enemy thinks and acts -> move shots and
          resolve hits (terrain, the player, enemies -- friendly fire on)
          -> handle deaths (chain reactions, e.g. a popped puffer) -> age
          effects -> play the frame's sounds -> stream world chunks with
          the time left (time-budgeted) and wake/sleep their enemies.
  draw:   terrain -> ground effects -> enemies -> hero -> shots -> air
          effects -> minimap -> crosshair -> HUD -> map / death overlay. Everything in the
          world is drawn at pixel positions (engine put_px), so it scrolls
          smoothly.

The camera is followed *before* aiming so the mouse->world mapping uses the
same camera the frame is drawn with; otherwise the crosshair and the aimed
point would disagree by one frame of scrolling.

A minimap sits in the top-right corner; M opens the big map (ui/maps.py),
which pauses the game and takes the mouse and WASD for zooming and panning.

When the hero falls the world keeps running behind a death overlay; R or a
click starts a new run (a full game-over screen with run stats comes with
the menus).
"""

from __future__ import annotations

import math
import time

import pygame

from engine import Scene, TextRenderer

from .. import config, palette
from ..ai.brain import AIContext
from ..engine_ext.camera import Camera
from ..engine_ext.input import Mouse, move_axes
from ..engine_ext.screen import fit_grid_to_window
from ..engine_ext.sfx import Sfx
from ..entities.effects import Effect, update_effects
from ..entities.projectile import Projectile
from ..entities.character import Character
from ..render.ascii_fx import draw_effects, draw_projectiles
from ..render.characters import draw_body
from ..render.enemies_sprite import draw_enemy
from ..render.sprites import SpriteBank
from ..render.terrain import draw_terrain
from ..systems import combat
from ..systems.spawner import Spawner
from ..ui.crosshair import draw_crosshair
from ..ui.death import draw_death_overlay
from ..ui.hud import draw_hud
from ..ui.maps import BigMap, Minimap
from ..world import make_world

# Effects drawn under the characters (they belong to the ground).
_GROUND_EFFECTS = ("tile_flash", "fizzle", "burrow")
# A click can't restart until the death overlay has been up this long
# (so the click that was firing when you died doesn't skip it).
_RESTART_DELAY = 0.8


class GameScene(Scene):
    def on_enter(self) -> None:
        d = self.manager.display
        self.world = make_world()
        self.spawn = self.world.spawn_point()
        self.hero = Character(config.HEROES[config.START_HERO], *self.spawn)
        self.camera = Camera(d.cols, d.rows - config.HUD_ROWS, d.cell_w, d.cell_h)
        self.camera.center_on(self.hero.x, self.hero.y)
        self.mouse = Mouse(d)
        self.sprites = SpriteBank(self.manager.text, config.CELLS_PER_TILE)
        self.sfx = Sfx(self.manager.audio)
        self.projectiles: list[Projectile] = []
        self.effects: list[Effect] = []
        self.enemies: list = []
        seed = getattr(self.world, "seed", None)
        self.spawner = Spawner(self.world, seed) if seed is not None else None
        # Maps exist only on the island (the test map has no layout).
        has_maps = getattr(self.world, "layout", None) is not None
        self.big_map = BigMap(self.world) if has_maps else None   # M; pauses the game
        self.minimap = Minimap() if has_maps else None
        self.kills = 0
        self.dead_for = -1.0          # seconds since the player died; <0 = alive
        self.fps = 60.0
        self._last_draw_ms = 0.0
        self._stream_world(budget_ms=None)  # build the start area up front
        pygame.mouse.set_visible(False)

    def on_exit(self) -> None:
        pygame.mouse.set_visible(True)

    @property
    def player_dead(self) -> bool:
        return self.dead_for >= 0

    @property
    def map_open(self) -> bool:
        return self.big_map is not None and self.big_map.is_open

    def _toggle_map(self) -> None:
        if self.map_open:
            self.big_map.close()
        else:
            self.big_map.open(self.hero.x, self.hero.y)
        pygame.mouse.set_visible(self.map_open)   # a real cursor for dragging

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.map_open:
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_m, pygame.K_ESCAPE):
                self._toggle_map()
                return
            d = self.manager.display
            pos = getattr(event, "pos", None) or pygame.mouse.get_pos()
            self.big_map.handle_event(event, d.window_to_canvas(*pos), d.cell_w, d.cell_h,
                                      (self.hero.x, self.hero.y))
            if event.type != pygame.KEYDOWN or event.key != pygame.K_F11:
                return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.manager.quit()
            elif event.key == pygame.K_F11:
                self.manager.display.cycle_mode()
                fit_grid_to_window(self.manager.display)
            elif event.key == pygame.K_m and self.big_map is not None:
                self._toggle_map()
            elif event.key == pygame.K_r and self.player_dead:
                self._restart()
        elif (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
              and self.dead_for >= _RESTART_DELAY):
            self._restart()

    def _restart(self) -> None:
        self.manager.switch_to(GameScene())

    # --- Update --------------------------------------------------------------------------

    def update(self, dt: float) -> None:
        started = time.perf_counter()
        # Smoothed FPS readout uses the real dt, before clamping.
        if dt > 0:
            self.fps += (1.0 / dt - self.fps) * 0.05
        dt = min(dt, config.MAX_DT)
        if self.map_open:
            self.big_map.pan(*move_axes(), dt)
            return   # the game is paused behind the map

        d = self.manager.display
        self.camera.resize(d.cols, d.rows - config.HUD_ROWS)
        sounds: list[str] = []

        if not self.player_dead:
            ax, ay = move_axes()
            self.hero.move(ax, ay, dt, self.world)
        else:
            self.dead_for += dt
        self.camera.follow(self.hero.x, self.hero.y, dt)

        px, py = self.mouse.poll()
        update_effects(self.effects, dt)   # age first: new effects show frame 0
        if not self.player_dead:
            self.hero.aim_at(*self.camera.canvas_to_world(px, py), dt)
            if self.hero.weapon.update(dt, self.mouse.left_held()):
                sounds += combat.fire(self.hero, self.world, self.projectiles, self.effects)
                for e in self.enemies:
                    e.hear(self.hero.x, self.hero.y)

        # Enemies act.
        actors = self._actors()
        ctx = AIContext(self.world, self.hero, actors, self.projectiles, self.effects)
        self.hero.tick_flash(dt)
        # Only enemies near the view think; distant ones wait frozen.
        half_w = self.camera.view_w / self.camera.tile_w / 2 + config.ENEMY_ACTIVE_MARGIN
        half_h = self.camera.view_h / self.camera.tile_h / 2 + config.ENEMY_ACTIVE_MARGIN
        for e in self.enemies:
            e.tick_flash(dt)
            if e.alive and abs(e.x - self.camera.x) < half_w and abs(e.y - self.camera.y) < half_h:
                e.think(ctx, dt)
        sounds += ctx.events
        ctx.events.clear()

        sounds += combat.update_projectiles(self.projectiles, self.world, self.effects, dt,
                                            self._actors())
        sounds += self._handle_deaths(ctx)
        for name in dict.fromkeys(sounds):  # each sound at most once per frame
            self.sfx.play(name)

        # Chunk generation gets whatever is left of this frame's time: the
        # frame target minus this update's work so far and last frame's
        # drawing, capped at CHUNK_BUILD_BUDGET_MS and never below
        # CHUNK_BUILD_MIN_MS (so streaming always progresses). Heavy frames
        # (e.g. a wide grid) generate less and catch up on lighter ones;
        # the load margin gives plenty of slack before a chunk is on screen.
        used_ms = (time.perf_counter() - started) * 1000 + self._last_draw_ms
        budget = config.FRAME_TARGET_MS - used_ms
        self._stream_world(max(config.CHUNK_BUILD_MIN_MS, min(config.CHUNK_BUILD_BUDGET_MS, budget)))

    def _actors(self) -> list:
        return [self.hero] + [e for e in self.enemies if e.alive]

    def _handle_deaths(self, ctx: AIContext) -> list[str]:
        """Remove dead enemies (with their death effects), repeating while
        deaths cause more deaths -- a popped puffer's spores can finish off
        a neighbour. Also notices the player's death."""
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
                self.kills += 1
            ctx.actors = self._actors()
        events += ctx.events
        ctx.events.clear()
        if not self.hero.alive and not self.player_dead:
            self.dead_for = 0.0
            self.projectiles = [p for p in self.projectiles if p.owner is not self.hero]
            self.effects.append(Effect("explosion", self.hero.x, self.hero.y))
            events.append(combat.BREAK)
        return events

    def _stream_world(self, budget_ms: float | None = config.CHUNK_BUILD_BUDGET_MS) -> None:
        """Let an infinite world load/unload chunks around the view, and
        wake/sleep enemies with them. budget_ms=None builds everything
        needed right away (at startup)."""
        stream = getattr(self.world, "update", None)
        if stream is None:
            return  # the fixed test map has nothing to stream
        half_w = self.camera.view_w / self.camera.tile_w / 2
        half_h = self.camera.view_h / self.camera.tile_h / 2
        if budget_ms is None:
            self.world.ensure_ready(*self.camera.visible_tiles())
            budget_ms = 1e9
        stream(self.camera.x, self.camera.y, half_w, half_h, budget_ms)
        if self.spawner is None:
            return
        for cx, cy in self.world.drain_loaded():
            self.spawner.chunk_loaded(cx, cy)
        self.spawner.update(self.enemies, self.camera.x, self.camera.y, half_w, half_h)

    # --- Draw ------------------------------------------------------------------------------

    def draw(self, text: TextRenderer) -> None:
        started = time.perf_counter()
        self._draw(text)
        self._last_draw_ms = (time.perf_counter() - started) * 1000

    def _draw(self, text: TextRenderer) -> None:
        d = self.manager.display
        text.clear(palette.BACKGROUND)
        draw_terrain(text, self.world, self.camera)
        ground = [e for e in self.effects if e.kind in _GROUND_EFFECTS]
        air = [e for e in self.effects if e.kind not in _GROUND_EFFECTS]
        draw_effects(text, self.camera, self.world, ground)
        margin = 3
        x0, y0 = self.camera.canvas_to_world(0, 0)
        x1, y1 = self.camera.canvas_to_world(self.camera.view_w, self.camera.view_h)
        for e in self.enemies:
            if x0 - margin <= e.x <= x1 + margin and y0 - margin <= e.y <= y1 + margin:
                draw_enemy(text, self.sprites, self.camera, self.world, e)
        if not self.player_dead:
            draw_body(self.sprites, self.camera, self.hero)
        draw_projectiles(text, self.camera, self.projectiles)
        draw_effects(text, self.camera, self.world, air)
        if self.minimap is not None and not self.map_open:
            self.minimap.draw(text, self.sprites, self.world, self.hero.x, self.hero.y,
                              self.hero.aim_angle)
        if not self.player_dead and not self.map_open:
            draw_crosshair(self.sprites, self.camera, self.mouse.canvas_pos)
        dist = math.hypot(self.hero.x - self.spawn[0], self.hero.y - self.spawn[1])
        draw_hud(text, d.cols, d.rows, self.hero, self.world, self.spawn, self.fps, self.kills)
        if self.map_open:
            self.big_map.draw(text, self.sprites, self.camera.view_rows,
                              (self.hero.x, self.hero.y), self.hero.aim_angle)
        elif self.player_dead:
            draw_death_overlay(text, d.cols, self.camera.view_rows, dist, self.kills,
                               getattr(self.world, "seed", None), self.dead_for >= _RESTART_DELAY)
