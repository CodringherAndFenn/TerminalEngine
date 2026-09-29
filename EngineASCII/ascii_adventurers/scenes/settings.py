"""
scenes/settings.py -- the settings screen from the title menu (the pause
menu shows the same panel over the game).
"""

from __future__ import annotations

import pygame

from engine import TextRenderer

from ..ui.settings_panel import SettingsPanel
from .common import MenuScene


class SettingsScene(MenuScene):
    def on_enter(self) -> None:
        super().on_enter()
        self.panel = SettingsPanel(self.manager, self._back)

    def _back(self) -> None:
        from .title import TitleScene
        self.manager.switch_to(TitleScene('settings'), fade=False)

    def menu_event(self, event: pygame.event.Event) -> None:
        self.panel.handle_event(event)

    def draw(self, text: TextRenderer) -> None:
        self.draw_backdrop(text)
        self.panel.draw(text)
