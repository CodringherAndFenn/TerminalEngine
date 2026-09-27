"""
scenes/intro.py -- the opening animation.

Fades up (the SceneManager handles that) on a centered logo, types out a
tagline with the Typewriter, holds a beat, then advances to the menu. Any key
or click skips ahead: first press finishes the typewriter, a second (or a press
once it's done) jumps straight to the menu.
"""

from __future__ import annotations

import pygame

from engine import Scene, TextRenderer, Typewriter, colors

# Placeholder logo; border glyphs are synthesized so they connect seamlessly.
LOGO = """\
┌──────────────────────────────────────┐
│  ▓▓░░                          ░░▓▓  │
│        N A R R A T I V E             │
│            E N G I N E               │
│  ▓▓░░                          ░░▓▓  │
└──────────────────────────────────────┘"""

TAGLINE = "a story is loading..."

# Seconds to linger after the tagline finishes before auto-advancing.
_HOLD = 1.4


class IntroScene(Scene):
    def on_enter(self) -> None:
        cols = self.manager.display.cols
        self._logo_col = (cols - 40) // 2
        self._tagline_col = (cols - len(TAGLINE)) // 2
        self._typewriter = Typewriter(
            TAGLINE, self._tagline_col, 12, fg=colors.GREEN, chars_per_second=24
        )
        self._hold = 0.0

    def handle_event(self, event: pygame.event.Event) -> None:
        pressed = event.type == pygame.KEYDOWN or (
            event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
        )
        if not pressed:
            return
        if self._typewriter.done:
            self._advance()
        else:
            self._typewriter.skip()

    def update(self, dt: float) -> None:
        self._typewriter.update(dt)
        if self._typewriter.done:
            self._hold += dt
            if self._hold >= _HOLD:
                self._advance()

    def draw(self, text: TextRenderer) -> None:
        text.clear(colors.BACKGROUND)
        text.put_block(self._logo_col, 4, LOGO, colors.AMBER)
        self._typewriter.draw(text)

    def _advance(self) -> None:
        from .menu import MenuScene  # lazy import avoids an import cycle

        self.manager.switch_to(MenuScene())
