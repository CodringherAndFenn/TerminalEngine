"""
scenes/common.py -- shared by the scenes: the drifting island backdrop, and
events handled everywhere (F11 cycles the window mode; gamepads plug in and
drive the menus).
"""

from __future__ import annotations

import math
import random

import pygame

from engine import Scene, TextRenderer

from .. import config
from ..app import App, app_of
from ..engine_ext.camera import Camera
from ..engine_ext.gamepads import BUTTON_BACK, BUTTON_START, EV_AXIS, EV_BUTTON
from ..engine_ext.screen import apply_window
from ..render.sprites import SpriteBank
from ..render.terrain import TerrainRenderer
from ..ui.frame import dim_canvas
from ..world import random_seed
from ..world.chunked import ChunkedWorld


class Backdrop:
    """A random island seen from above, drifting slowly around it through
    the ring of biomes, darkened behind the menus. One is shared by all menu
    screens (kept on the App) so it glides on uninterrupted between them."""

    SPEED = 2.0       # tiles per second
    DIM = 150         # darkening, 0-255

    def __init__(self, text: TextRenderer) -> None:
        self.world = ChunkedWorld(random_seed())
        lay = self.world.layout
        # A circle through the biome ring, starting somewhere random on it.
        self.radius = (lay.plains_radius + lay.max_land_radius) * 0.35
        self.angle = random.uniform(0, math.tau)
        self.terrain = TerrainRenderer(text)
        d = text.display
        self.camera = Camera(d.cols, d.rows, d.cell_w, d.cell_h)
        self._place()
        self.world.ensure_ready(*self.camera.visible_tiles())

    def _place(self) -> None:
        self.camera.center_on(math.cos(self.angle) * self.radius,
                              math.sin(self.angle) * self.radius)

    def update(self, dt: float, display) -> None:
        self.angle += self.SPEED * dt / self.radius
        self.camera.resize(display.cols, display.rows)
        self._place()
        half_w = self.camera.view_w / self.camera.tile_w / 2
        half_h = self.camera.view_h / self.camera.tile_h / 2
        self.world.update(self.camera.x, self.camera.y, half_w, half_h, budget_ms=2.0)

    def draw(self, text: TextRenderer) -> None:
        self.terrain.draw(self.world, self.camera)
        dim_canvas(text, self.DIM)


def backdrop_of(app: App, text: TextRenderer) -> Backdrop:
    bd = getattr(app, "backdrop", None)
    if bd is None or bd.terrain.text is not text:
        bd = app.backdrop = Backdrop(text)
    return bd


def sprites_of(app: App, text: TextRenderer) -> SpriteBank:
    bank = getattr(app, "menu_sprites", None)
    if bank is None or bank.text is not text:
        bank = app.menu_sprites = SpriteBank(text, config.CELLS_PER_TILE)
    return bank


def app_events(manager, event: pygame.event.Event, menu: bool = True) -> list[pygame.event.Event]:
    """Handle what works on every screen, and return the events the screen
    itself should see:
      * F11 cycles the window mode (and saves it) -> [];
      * gamepads plugged in or out -> [];
      * gamepad buttons / stick -> the keys menus understand (menu=True);
        during play (menu=False) only Start (pause) and Back (map) become
        keys -- the sticks, triggers and other buttons are read directly
        by the player's controls;
      * anything else -> [event].
    """
    app = app_of(manager)
    if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
        d = manager.display
        d.cycle_mode()
        apply_window(d, app.settings.window_size)
        app.settings.window_mode = d.mode.value
        app.save_settings()
        return []
    if app.pads.handle_event(event):
        return []
    if event.type in (EV_BUTTON, EV_AXIS):
        if menu:
            return app.pads.menu_keys(event)
        if event.type == EV_BUTTON and event.button in (BUTTON_START, BUTTON_BACK):
            return app.pads.menu_keys(event)
        return []
    return [event]


class MenuScene(Scene):
    """Base for menu screens: backdrop, visible mouse, F11, gamepads."""

    def on_enter(self) -> None:
        self.app = app_of(self.manager)
        pygame.mouse.set_visible(True)

    def handle_event(self, event: pygame.event.Event) -> None:
        for ev in app_events(self.manager, event):
            self.menu_event(ev)

    def menu_event(self, event: pygame.event.Event) -> None:
        """Override: this screen's own event handling."""

    def update(self, dt: float) -> None:
        backdrop_of(self.app, self.manager.text).update(dt, self.manager.display)

    def draw_backdrop(self, text: TextRenderer) -> None:
        backdrop_of(self.app, text).draw(text)
