"""
ui/card_picker.py -- choosing a level-up card: big cards across the middle
of the screen.

Left / Right (A / D, the d-pad or left stick) move between the cards,
Enter / Space (gamepad A) takes the highlighted one; the mouse highlights
the card under it and a click takes it. In single player the game is
paused while the cards are up (`pauses`); in multiplayer it will keep
running (each player picks on their own screen).

Each card: its rarity at the top (in the rarity's color, which also
frames it), the name, the effect wrapped over a few lines, and whose card
it is if it belongs to one hero. The highlighted card has a bright frame,
a lighter background and a bar above and below it.
"""

from __future__ import annotations

import textwrap
from typing import Callable

import pygame

from engine import TextRenderer, colors

from .. import config, palette
from .frame import center

CARD_H = 13
GAP = 3
MAX_CARD_W = 30
_LEFT = (pygame.K_LEFT, pygame.K_a)
_RIGHT = (pygame.K_RIGHT, pygame.K_d)
_TAKE = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)


class CardPicker:
    def __init__(self, manager, offer: list[str], waiting: int,
                 choose: Callable[[int], None], pauses: bool = True) -> None:
        self.manager = manager
        self.offer = list(offer)
        self.waiting = waiting            # picks banked after this one
        self.choose = choose
        self.pauses = pauses
        self.index = 0

    def set_offer(self, offer: list[str], waiting: int) -> None:
        """The next offer (more picks banked): start again on the first card."""
        self.offer, self.waiting, self.index = list(offer), waiting, 0

    # --- Layout ---------------------------------------------------------------------

    def _layout(self) -> tuple[int, int, int]:
        """(left column, top row, card width) for the current grid."""
        d = self.manager.display
        n = max(1, len(self.offer))
        w = min(MAX_CARD_W, (d.cols - 4 - GAP * (n - 1)) // n)
        total = n * w + (n - 1) * GAP
        top = max(2, (d.rows - CARD_H) // 2)
        return (d.cols - total) // 2, top, w

    def card_at(self, col: int, row: int) -> int | None:
        left, top, w = self._layout()
        if not top <= row < top + CARD_H:
            return None
        for i in range(len(self.offer)):
            c = left + i * (w + GAP)
            if c <= col < c + w:
                return i
        return None

    # --- Input ------------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        if not self.offer:
            return
        if event.type == pygame.KEYDOWN:
            if event.key in _LEFT:
                self.index = (self.index - 1) % len(self.offer)
            elif event.key in _RIGHT:
                self.index = (self.index + 1) % len(self.offer)
            elif event.key in _TAKE:
                self.choose(self.index)
            return
        if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
            cell = self.manager.display.window_to_cell(*event.pos)
            i = self.card_at(*cell) if cell is not None else None
            if i is None:
                return
            self.index = i
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.choose(i)

    # --- Drawing ----------------------------------------------------------------------

    def draw(self, text: TextRenderer) -> None:
        if not self.offer:
            return
        d = self.manager.display
        left, top, w = self._layout()
        total = len(self.offer) * w + (len(self.offer) - 1) * GAP
        more = f"   (+{self.waiting} more)" if self.waiting > 0 else ""
        center(text, top - 2, f" LEVEL UP!  choose a card{more} ", palette.CARD_TITLE,
               left, total, palette.HUD_PANEL)
        for i, key in enumerate(self.offer):
            self._card(text, left + i * (w + GAP), top, w, key, i == self.index)
        hint = " LEFT / RIGHT choose    ENTER or click take "
        center(text, top + CARD_H + 1, hint, colors.GREY, left, total, palette.HUD_PANEL)

    def _card(self, text: TextRenderer, col: int, top: int, w: int, key: str,
              selected: bool) -> None:
        card = config.CARDS[key]
        rarity = palette.CARD_RARITY[card.rarity]
        edge = palette.CARD_SELECTED if selected else rarity
        bg = palette.CARD_BG_SELECTED if selected else palette.HUD_PANEL
        text.put(col, top, "┌" + "─" * (w - 2) + "┐", edge, bg)
        for r in range(top + 1, top + CARD_H - 1):
            text.put(col, r, "│" + " " * (w - 2) + "│", edge, bg)
        text.put(col, top + CARD_H - 1, "└" + "─" * (w - 2) + "┘", edge, bg)
        inner = w - 4
        center(text, top + 2, card.rarity.upper(), rarity, col, w, bg)
        center(text, top + 4, card.name.upper()[:inner], palette.CARD_TITLE, col, w, bg)
        for j, line in enumerate(wrap(card.text, inner)):
            center(text, top + 6 + j, line, palette.CARD_TEXT, col, w, bg)
        if card.heroes and len(card.heroes) == 1:
            center(text, top + CARD_H - 3, card.heroes[0].upper(), palette.CARD_TAG, col, w, bg)
        if selected:
            # Bars hugging the card above and below (half blocks: the font
            # has no arrow glyphs).
            center(text, top - 1, "▄" * (w - 4), palette.CARD_SELECTED, col, w, None)
            center(text, top + CARD_H, "▀" * (w - 4), palette.CARD_SELECTED, col, w, None)


def wrap(s: str, width: int) -> list[str]:
    """A card's effect in at most four lines of `width`."""
    return textwrap.wrap(s, max(8, width))[:4]
