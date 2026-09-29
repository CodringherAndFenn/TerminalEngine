"""
scenes/title.py -- the title screen: logo, New run / Settings / Quit, and
the player's records, over the drifting island.
"""

from __future__ import annotations

import pygame

from engine import Menu, TextRenderer, colors

from .. import palette
from ..meta.run_stats import format_time
from ..ui.frame import center
from ..ui.logo import draw_logo
from .common import MenuScene

HINT = "Up/Down or mouse: choose   Enter or click: select   F11: window mode   Esc: quit"


class TitleScene(MenuScene):
    ITEMS = ("new run", "settings", "quit")

    def __init__(self, focus: str = "new run") -> None:
        self.focus = focus                # which button starts focused

    def on_enter(self) -> None:
        super().on_enter()
        self._menu = None
        self._shape = None

    def _ensure_menu(self) -> Menu:
        d = self.manager.display
        if self._menu is None or self._shape != (d.cols, d.rows):
            index = self._menu.index if self._menu is not None else self.ITEMS.index(self.focus)
            self._menu = Menu(
                [("New run", self._new_run), ("Settings", self._settings), ("Quit", self.manager.quit)],
                top_row=16, cols=d.cols, width=24,
            )
            self._menu.index = index
            self._shape = (d.cols, d.rows)
        return self._menu

    def menu_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.manager.quit()
            return
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER,
                                                          pygame.K_SPACE):
            self.manager.audio.play_blip()
        self._ensure_menu().handle_event(event, self.manager.display)

    def _new_run(self) -> None:
        from .new_run import NewRunScene
        self.manager.switch_to(NewRunScene(), fade=False)

    def _settings(self) -> None:
        from .settings import SettingsScene
        self.manager.switch_to(SettingsScene(), fade=False)

    def draw(self, text: TextRenderer) -> None:
        d = self.manager.display
        self.draw_backdrop(text)
        draw_logo(text, 2, palette.LOGO, palette.LOGO_SHADOW)
        self._ensure_menu().draw(text)
        rec = self.app.records
        if rec.runs:
            line = (f"runs {rec.runs}    best time {format_time(rec.longest_time)}    "
                    f"most kills {rec.most_kills}    furthest {rec.furthest:.0f}    "
                    f"biomes {rec.most_biomes}")
            center(text, 23, "RECORDS", colors.AMBER_DIM, bg=None)
            center(text, 24, line, colors.GREEN, bg=None)
        center(text, d.rows - 2, HINT, colors.GREY, bg=None)
