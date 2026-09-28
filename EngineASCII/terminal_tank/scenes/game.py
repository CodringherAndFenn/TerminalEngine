"""
scenes/game.py -- the in-game scene: drive, aim, shoot, scroll.

Per frame:
  update: clamp dt -> poll held keys -> drive the tank (rotated-hull
          collision) -> ease the camera toward it -> map the mouse to the
          world -> aim -> fire while the left button is held -> move shells
          and resolve hits -> age effects -> play the frame's sounds.
  draw:   terrain -> ground effects (tile flashes, dust) -> tank -> shells
          -> muzzle flashes & impacts -> crosshair -> HUD. Everything in the
          world is drawn at pixel positions (engine put_px), so it scrolls
          smoothly.

The camera is followed *before* aiming so the mouse->world mapping uses the
same camera the frame is drawn with; otherwise the crosshair and the aimed
point would disagree by one frame of scrolling.
"""

from __future__ import annotations

import pygame

from engine import Scene, TextRenderer

from .. import config, palette
from ..engine_ext.camera import Camera
from ..engine_ext.input import Mouse, move_axes
from ..engine_ext.screen import fit_grid_to_window
from ..engine_ext.sfx import Sfx
from ..entities.effects import Effect, update_effects
from ..entities.projectile import Projectile
from ..entities.tank import Tank
from ..render.effects_sprite import draw_effects, draw_projectiles
from ..render.sprites import SpriteBank
from ..render.tank_sprite import draw_tank
from ..render.terrain import draw_terrain
from ..systems import combat
from ..ui.crosshair import draw_crosshair
from ..ui.hud import draw_hud
from ..world.test_map import TestMap

# Effects drawn under the tank (they belong to the ground).
_GROUND_EFFECTS = ("tile_flash", "fizzle")


class GameScene(Scene):
    def on_enter(self) -> None:
        d = self.manager.display
        self.world = TestMap.load(config.TEST_MAP_FILE)
        self.tank = Tank(config.TANKS[config.START_TANK], *self.world.spawn_point())
        self.camera = Camera(d.cols, d.rows - config.HUD_ROWS, d.cell_w, d.cell_h)
        self.camera.center_on(self.tank.x, self.tank.y)
        self.mouse = Mouse(d)
        self.sprites = SpriteBank(self.manager.text, config.CELLS_PER_TILE)
        self.sfx = Sfx(self.manager.audio)
        self.projectiles: list[Projectile] = []
        self.effects: list[Effect] = []
        self.fps = 60.0
        pygame.mouse.set_visible(False)

    def on_exit(self) -> None:
        pygame.mouse.set_visible(True)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            self.manager.quit()
        elif event.key == pygame.K_F11:
            self.manager.display.cycle_mode()
            fit_grid_to_window(self.manager.display)

    def update(self, dt: float) -> None:
        # Smoothed FPS readout uses the real dt, before clamping.
        if dt > 0:
            self.fps += (1.0 / dt - self.fps) * 0.05
        dt = min(dt, config.MAX_DT)

        d = self.manager.display
        self.camera.resize(d.cols, d.rows - config.HUD_ROWS)

        ax, ay = move_axes()
        self.tank.drive(ax, ay, dt, self.world)
        self.camera.follow(self.tank.x, self.tank.y, dt)

        px, py = self.mouse.poll()
        self.tank.aim_at(*self.camera.canvas_to_world(px, py), dt)

        # Effects age first, so ones spawned this frame show their first frame.
        update_effects(self.effects, dt)
        sounds: list[str] = []
        if self.tank.weapon.update(dt, self.mouse.left_held()):
            sounds += combat.fire(self.tank, self.world, self.projectiles, self.effects)
        sounds += combat.update_projectiles(self.projectiles, self.world, self.effects, dt)
        for name in dict.fromkeys(sounds):  # each sound at most once per frame
            self.sfx.play(name)

    def draw(self, text: TextRenderer) -> None:
        d = self.manager.display
        text.clear(palette.BACKGROUND)
        draw_terrain(text, self.world, self.camera)
        ground = [e for e in self.effects if e.kind in _GROUND_EFFECTS]
        air = [e for e in self.effects if e.kind not in _GROUND_EFFECTS]
        draw_effects(text, self.sprites, self.camera, self.world, ground)
        draw_tank(self.sprites, self.camera, self.tank)
        draw_projectiles(self.sprites, self.camera, self.projectiles)
        draw_effects(text, self.sprites, self.camera, self.world, air)
        draw_crosshair(self.sprites, self.camera, self.mouse.canvas_pos)
        draw_hud(text, d.cols, d.rows, self.tank, self.fps)
