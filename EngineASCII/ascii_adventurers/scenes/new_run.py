"""
scenes/new_run.py -- before a run: pick a hero and (optionally) an island
seed. Both are remembered for next time (save/settings.json).
"""

from __future__ import annotations

import pygame

from engine import Button, TextRenderer, WidgetList, colors

from .. import config
from ..ui.frame import center, draw_box
from ..ui.widgets import CARD_H, CARD_W, HeroPicker, SeedField
from .common import MenuScene, sprites_of

HINT = "Left/Right: hero   Up/Down: move   type digits for a seed   Enter: start   Esc: back"


class NewRunScene(MenuScene):
    def on_enter(self) -> None:
        super().on_enter()
        self._ui: WidgetList | None = None
        self._shape = None
        self.clock = 0.0

    def _ensure_ui(self) -> WidgetList:
        d = self.manager.display
        if self._ui is not None and self._shape == (d.cols, d.rows):
            return self._ui
        s = self.app.settings
        heroes = list(config.HEROES)
        picker_w = len(heroes) * (CARD_W + 1) - 1
        col = (d.cols - picker_w) // 2
        picker = HeroPicker(col, 5, heroes, sprites_of(self.app, self.manager.text),
                            index=heroes.index(s.hero) if s.hero in heroes else 0,
                            on_change=self._on_hero)
        picker.activate = self._start
        w = 50
        c2 = (d.cols - w) // 2
        row = 5 + CARD_H + 2
        seed = SeedField(c2, row, w, "Island seed", s.seed, on_activate=self._start)
        widgets = [picker, seed,
                   Button(c2, row + 3, w, "Start", self._start),
                   Button(c2, row + 5, w, "Back", self._back)]
        index = self._ui.index if self._ui is not None else 0
        self._ui = WidgetList(widgets)
        self._ui.index = index
        self._picker, self._seed = picker, seed
        self._shape = (d.cols, d.rows)
        return self._ui

    def _on_hero(self, hero: str) -> None:
        self.app.ui_sound()

    def _start(self) -> None:
        from .game import GameScene
        s = self.app.settings
        s.hero = self._picker.value
        s.seed = self._seed.seed
        self.app.save_settings()
        self.app.ui_sound()
        self.manager.switch_to(GameScene(hero=s.hero, seed=s.seed))

    def _back(self) -> None:
        from .title import TitleScene
        self.manager.switch_to(TitleScene('new run'), fade=False)

    def menu_event(self, event: pygame.event.Event) -> None:
        ui = self._ensure_ui()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._back()
                return
            # Digits / Backspace / Delete type into the seed field from
            # anywhere on the screen.
            if event.key not in (pygame.K_RETURN, pygame.K_KP_ENTER) and self._seed.type_key(event):
                return
        ui.handle_event(event, self.manager.display)

    def update(self, dt: float) -> None:
        super().update(dt)
        self.clock += dt
        if self._ui is not None:
            self._picker.clock = self._seed.clock = self.clock

    def draw(self, text: TextRenderer) -> None:
        d = self.manager.display
        ui = self._ensure_ui()
        self.draw_backdrop(text)
        center(text, 2, "CHOOSE YOUR ADVENTURER", colors.AMBER, bg=None)
        weapon = config.WEAPONS[config.HEROES[self._picker.value].weapon]
        center(text, 3, f"{weapon.name.upper()}: {weapon.blurb}", colors.GREY, bg=None)
        box_w = 56
        draw_box(text, (d.cols - box_w) // 2, 5 + CARD_H + 1, box_w, 9)
        ui.draw(text)
        center(text, d.rows - 2, HINT, colors.GREY, bg=None)
