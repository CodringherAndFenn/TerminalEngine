"""
scenes/new_run.py -- before a run: pick a hero, the difficulty (P5: the
levels opened so far) and (optionally) an island seed. All three are
remembered for next time (save/settings.json).
"""

from __future__ import annotations

import pygame

from engine import Button, OptionSelector, TextRenderer, WidgetList, colors

from .. import config
from ..ui.frame import center, draw_box
from ..ui.widgets import CARD_H, CARD_W, HeroPicker, SeedField
from ..systems.run_rules import difficulty_totals
from .common import MenuScene, sprites_of

HINT = ("Left/Right: hero / difficulty   Up/Down: move   type digits for a seed   "
        "Enter: start   Esc: back")


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
        # Difficulty (P5): the levels opened so far (all of them in dev mode).
        top = len(config.DIFFICULTIES) - 1 if self.app.dev else self.app.guild.difficulty_open
        levels = list(range(top + 1))
        difficulty = OptionSelector(c2, row, w, "Difficulty", levels,
                                    index=min(s.difficulty, top),
                                    formatter=lambda n: config.DIFFICULTIES[n],
                                    on_change=self._on_hero)
        difficulty.activate = self._start
        seed = SeedField(c2, row + 3, w, "Island seed", s.seed, on_activate=self._start)
        widgets = [picker, difficulty, seed,
                   Button(c2, row + 6, w, "Start", self._start),
                   Button(c2, row + 8, w, "Back", self._back)]
        index = self._ui.index if self._ui is not None else 0
        self._ui = WidgetList(widgets)
        self._ui.index = index
        self._picker, self._seed, self._difficulty = picker, seed, difficulty
        self._shape = (d.cols, d.rows)
        return self._ui

    def _on_hero(self, _value) -> None:
        self.app.ui_sound()

    def _start(self) -> None:
        from .game import GameScene
        s = self.app.settings
        s.hero = self._picker.value
        s.seed = self._seed.seed
        s.difficulty = self._difficulty.value
        self.app.save_settings()
        self.app.ui_sound()
        self.manager.switch_to(GameScene(hero=s.hero, seed=s.seed, difficulty=s.difficulty))

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
        draw_box(text, (d.cols - box_w) // 2, 5 + CARD_H + 1, box_w, 12)
        ui.draw(text)
        what, unlock = self._difficulty_lines()
        center(text, 5 + CARD_H + 3, what, colors.GREY, bg=None)
        if unlock:
            center(text, 5 + CARD_H + 4, unlock, colors.AMBER_DIM, bg=None)

    def _difficulty_lines(self) -> tuple[str, str]:
        """Under the difficulty: what it does, and (on the highest one opened)
        how the next one opens."""
        n = self._difficulty.value
        t = difficulty_totals(n)
        what = ("the island as it always was" if n == 0 else
                f"enemy HP x{t['hp']:.1f}  damage x{t['damage']:.2f}  "
                f"enemies x{1 + t['enemies']:.1f}  loot +{t['loot'] * 100:.0f}%")
        last = len(config.DIFFICULTIES) - 1
        unlock = (f"beat a boss here to open {config.DIFFICULTIES[n + 1]}"
                  if n == self.app.guild.difficulty_open and n < last and not self.app.dev
                  else "")
        return what, unlock
        center(text, d.rows - 2, HINT, colors.GREY, bg=None)
