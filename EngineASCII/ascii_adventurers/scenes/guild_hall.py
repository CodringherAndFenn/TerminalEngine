"""
scenes/guild_hall.py -- the Guild Hall: a small hall you walk around in
between runs, spending loot.

You come in as your current hero. Walk (WASD / arrows / left stick) up to
someone and press E or Enter (gamepad A) to talk:
  * the guildmaster (great hall, behind the desk): upgrades for everyone;
  * the trainer (training yard, west): each hero's own upgrades;
  * the archivist (archive, east): shelves of cards, spells, pacts and
    bestiary pages;
  * the heroes' statues (north): walk up to one to play as that hero
    (your own pedestal stands empty);
  * the dungeon gate (south): switch pacts on or off, then off to a run
    (hero select / island seed).
Esc leaves for the title screen. The shops are ui/guild_panel.py; what's
bought is saved straight away (meta/guild.py).

No simulation clock here: nothing in the hall needs to replay, so the
hero just walks with the frame's dt.
"""

from __future__ import annotations

import math

import pygame

from engine import Scene, TextRenderer, colors

from .. import config, palette
from ..app import app_of
from ..engine_ext.camera import Camera
from ..engine_ext.input import move_axes
from ..entities.character import Character
from ..render.characters import draw_body, draw_character
from ..render.glyphs import loot_glyph
from ..render.terrain import TerrainRenderer
from ..ui.frame import center, dim_canvas
from ..ui.guild_panel import GuildPanel
from ..world.hub import Station, load_hub
from .common import app_events, sprites_of

INTERACT_RADIUS = 2.6     # tiles
_TALK = (pygame.K_e, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)
NAMES = {"guild": "GUILDMASTER", "hero": "TRAINER", "cards": "ARCHIVIST", "gate": "DUNGEON"}
PROMPTS = {"guild": "talk to the guildmaster", "hero": "train with the trainer",
           "cards": "browse the archive", "gate": "the dungeon gate (pacts, enter)"}
HINT = "WASD / arrows: walk    E or Enter: talk    Esc: leave"


class GuildHallScene(Scene):
    def __init__(self, hero: str | None = None) -> None:
        self.hero_key = hero

    def on_enter(self) -> None:
        self.app = app_of(self.manager)
        if self.hero_key not in config.HEROES:
            s = self.app.settings.hero
            self.hero_key = s if s in config.HEROES else config.START_HERO
        self.world, self.stations = load_hub()
        d = self.manager.display
        self.hero = Character(config.HEROES[self.hero_key], *self.world.spawn_point())
        self.hero.aim_angle = -math.pi / 2
        self.camera = Camera(d.cols, d.rows, d.cell_w, d.cell_h)
        self.camera.center_on(*self._camera_target())
        self.terrain = TerrainRenderer(self.manager.text)
        self.sprites = sprites_of(self.app, self.manager.text)
        self.panel: GuildPanel | None = None
        self.near: Station | None = None
        pygame.mouse.set_visible(True)

    # --- Events ---------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        for ev in app_events(self.manager, event, menu=True):
            self._handle(ev)

    def _handle(self, event: pygame.event.Event) -> None:
        if self.panel is not None:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.panel = None
            else:
                self.panel.handle_event(event)
            return
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            from .title import TitleScene
            self.manager.switch_to(TitleScene("guild hall"))
        elif event.key in _TALK and self.near is not None:
            self.interact(self.near)

    def interact(self, station: Station) -> None:
        self.app.ui_sound()
        if station.kind in ("guild", "hero", "cards"):
            mode = "archive" if station.kind == "cards" else station.kind
            self.panel = GuildPanel(self.manager, self.app.guild, mode, self.hero_key,
                                    on_buy=self._bought)
        elif station.kind == "gate":
            self.panel = GuildPanel(self.manager, self.app.guild, "gate", self.hero_key,
                                    on_buy=lambda ok: self.app.save_guild(), enter=self._enter)
        elif station.kind == "statue":
            self.become(station.hero)

    def _enter(self) -> None:
        from .new_run import NewRunScene
        self.manager.switch_to(NewRunScene())

    def become(self, hero: str) -> None:
        """Play as another hero: they step off the pedestal where you stood."""
        if hero == self.hero_key:
            return
        self.hero_key = hero
        self.app.settings.hero = hero
        self.app.save_settings()
        old = self.hero
        self.hero = Character(config.HEROES[hero], old.x, old.y)
        self.hero.aim_angle = old.aim_angle

    def _bought(self, ok: bool) -> None:
        if ok:
            self.app.save_guild()
            self.app.sfx.play("chime")
        else:
            self.app.sfx.play("thud")

    # --- Frame ----------------------------------------------------------------------

    def update(self, dt: float) -> None:
        dt = min(dt, config.MAX_DT)
        d = self.manager.display
        self.camera.resize(d.cols, d.rows)
        if self.panel is None:
            ax, ay = self._move_axes()
            self.hero.move(ax, ay, dt, self.world)
            if ax or ay:
                self.hero.aim_angle = math.atan2(ay, ax)    # face where you walk
        self.camera.follow(*self._camera_target(), dt)
        self.near = self.nearest_station()

    def _camera_target(self) -> tuple[float, float]:
        """Follow the hero, but never show past the hall's walls: a hall
        smaller than the screen sits in the middle of it."""
        cam, w = self.camera, self.world
        out = []
        for pos, size, view in ((self.hero.x, w.width, cam.view_w / config.TILE_PX_W),
                                (self.hero.y, w.height, cam.view_h / config.TILE_PX_H)):
            half = view / 2
            out.append(size / 2 if size <= view else min(max(pos, half), size - half))
        return out[0], out[1]

    def _move_axes(self) -> tuple[float, float]:
        ax, ay = move_axes()
        if not (ax or ay):
            for pad in self.app.pads.pads:
                sx, sy = pad.left_stick()
                if sx or sy:
                    return sx, sy
        return ax, ay

    def nearest_station(self) -> Station | None:
        h = self.hero
        best, best_d = None, INTERACT_RADIUS
        for s in self.stations:
            if s.kind == "statue" and s.hero == self.hero_key:
                continue                  # your own, empty pedestal
            dist = math.hypot(s.x - h.x, s.y - h.y)
            if dist <= best_d:
                best, best_d = s, dist
        return best

    # --- Drawing --------------------------------------------------------------------

    def draw(self, text: TextRenderer) -> None:
        d = self.manager.display
        cam = self.camera
        text.clear(palette.BACKGROUND)
        self.terrain.draw(self.world, cam)
        for s in self.stations:
            x, y = cam.world_to_px(s.x, s.y)
            if s.kind == "statue":
                if s.hero != self.hero_key:
                    draw_character(self.sprites, x, y - 14, s.sprite, 3, False, 0, False)
                self._label(text, x, y - 66, s.hero.upper(),
                            palette.HUB_LABEL if s is self.near else colors.GREY)
            elif s.sprite is not None:
                draw_character(self.sprites, x, y - 8, s.sprite, 3, s.x > self.hero.x, 0, False)
                self._label(text, x, y - 56, NAMES[s.kind], palette.HUB_LABEL)
            else:
                self._label(text, x, y + 22, NAMES[s.kind], palette.HUB_LABEL)
        draw_body(self.sprites, cam, self.hero)
        purse = f" GUILD HALL   LOOT {loot_glyph(text)} {self.app.guild.loot} "
        if self.app.dev:
            purse += " DEV: nothing bought is saved "
        text.put(0, 0, purse, palette.LOOT_TEXT, palette.HUD_PANEL)
        if self.panel is not None:
            dim_canvas(text, 110)
            self.panel.draw(text)
            return
        if self.near is not None:
            s = self.near
            what = f"play as the {s.hero}" if s.kind == "statue" else PROMPTS[s.kind]
            center(text, d.rows - 4, f"  E / Enter: {what}  ", palette.HUB_PROMPT,
                   bg=palette.HUD_PANEL)
        center(text, d.rows - 2, HINT, colors.GREY, bg=palette.HUD_PANEL)

    @staticmethod
    def _label(text: TextRenderer, x: float, y: float, s: str, color) -> None:
        cw = text.display.cell_w
        text.put_px(x - len(s) * cw / 2, y, s, color, None)
