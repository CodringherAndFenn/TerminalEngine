"""
scenes/menu.py -- the main menu and the New Game placeholder.

MenuScene draws the framed background and a centered Menu (New Game / Settings /
Quit) navigable by keyboard and mouse. New Game currently opens a "coming soon"
placeholder; Settings opens the settings screen; Quit exits.
"""

from __future__ import annotations

import pygame

from engine import Menu, Scene, TextRenderer, colors

from .common import draw_screen


class MenuScene(Scene):
    def on_enter(self) -> None:
        cols = self.manager.display.cols
        rows = self.manager.display.rows
        self._menu = Menu(
            [
                ("New Game", self._new_game),
                ("Settings", self._settings),
                ("Quit", self.manager.quit),
            ],
            top_row=rows // 2 - 1,
            cols=cols,
        )

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_q):
            self.manager.quit()
            return
        # Play a blip when a button is triggered by keyboard.
        if event.type == pygame.KEYDOWN and event.key in (
            pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE,
        ):
            self.manager.audio.play_blip()
        self._menu.handle_event(event, self.manager.display)

    def draw(self, text: TextRenderer) -> None:
        cols = self.manager.display.cols
        rows = self.manager.display.rows
        draw_screen(text, cols, rows, "NARRATIVE ENGINE")
        self._menu.draw(text)
        hint = "Arrows / mouse: move   Enter / click: select   Esc: quit"
        text.put((cols - len(hint)) // 2, rows - 2, hint, colors.GREY)

    def _new_game(self) -> None:
        self.manager.switch_to(PlaceholderScene())

    def _settings(self) -> None:
        from .settings_scene import SettingsScene  # lazy import avoids a cycle

        self.manager.switch_to(SettingsScene())


class PlaceholderScene(Scene):
    """Stand-in for the not-yet-built New Game flow. Any key / click returns."""

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN or (
            event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
        ):
            self.manager.switch_to(MenuScene())

    def draw(self, text: TextRenderer) -> None:
        cols = self.manager.display.cols
        rows = self.manager.display.rows
        draw_screen(text, cols, rows, "NEW GAME")
        msg = "Coming soon."
        text.put((cols - len(msg)) // 2, rows // 2, msg, colors.GREEN)
        hint = "press any key to go back"
        text.put((cols - len(hint)) // 2, rows - 2, hint, colors.GREY)
