"""
scenes/game.py -- the in-game scene: drive, aim, scroll.

Per frame:
  update: clamp dt -> poll held keys -> drive the tank (with collision)
          -> ease the camera toward it -> map the mouse to the world -> aim.
  draw:   terrain -> tank -> crosshair -> HUD. Everything in the world is
          drawn at pixel positions (engine put_px), so it scrolls smoothly.

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
from ..entities.tank import Tank
from ..render.sprites import SpriteBank
from ..render.tank_sprite import draw_tank
from ..render.terrain import draw_terrain
from ..ui.crosshair import draw_crosshair
from ..ui.hud import draw_hud
from ..world.test_map import TestMap


class GameScene(Scene):
    def on_enter(self) -> None:
        d = self.manager.display
        self.world = TestMap.load(config.TEST_MAP_FILE)
        self.tank = Tank(*self.world.spawn_point())
        self.camera = Camera(d.cols, d.rows - config.HUD_ROWS, d.cell_w, d.cell_h)
        self.camera.center_on(self.tank.x, self.tank.y)
        self.mouse = Mouse(d)
        self.sprites = SpriteBank(self.manager.text, config.CELLS_PER_TILE)
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

    def draw(self, text: TextRenderer) -> None:
        d = self.manager.display
        text.clear(palette.BACKGROUND)
        draw_terrain(text, self.world, self.camera)
        draw_tank(self.sprites, self.camera, self.tank)
        draw_crosshair(self.sprites, self.camera, self.mouse.canvas_pos)
        draw_hud(text, d.cols, d.rows, self.tank, self.fps)
