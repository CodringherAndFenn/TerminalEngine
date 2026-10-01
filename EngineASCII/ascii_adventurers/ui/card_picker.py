"""
ui/card_picker.py -- choosing a level-up card: big cards across the middle
of the screen, with reroll / banish / skip below them.

Left / Right (A / D, the d-pad or left stick) move between the cards,
Enter / Space (gamepad A) takes the highlighted one; the mouse highlights
the card under it and a click takes it. Down moves to the row of buttons
under the cards (Up goes back): REROLL draws a new offer, BANISH removes
the highlighted card for the rest of the run (and draws a new offer),
SKIP takes no card and heals SKIP_HEAL of max HP. Hotkeys: R, B, X.
In single player the game is paused while the cards are up (`pauses`); in
multiplayer it keeps running (each player picks on their own screen).

Each card: its rarity at the top (in the rarity's color, which also
frames it), the name, the effect wrapped over a few lines (a tiered card
shows its number for the rarity it rolled; a spell you own shows its next
level), and whose card it is if it belongs to one hero. The highlighted
card has a bright frame, a lighter background and a bar above and below.

The picker only shows and chooses: `choose(action)` gets a card index,
"reroll", "skip" or ("banish", index); the game applies it and calls
refresh() with the result.
"""

from __future__ import annotations

import textwrap
from typing import Callable

import pygame

from engine import TextRenderer, colors

from .. import config, palette
from ..players.cards import card_text
from .frame import center

CARD_H = 13
GAP = 3
MAX_CARD_W = 30
_LEFT = (pygame.K_LEFT, pygame.K_a)
_RIGHT = (pygame.K_RIGHT, pygame.K_d)
_UP = (pygame.K_UP, pygame.K_w)
_DOWN = (pygame.K_DOWN, pygame.K_s)
_TAKE = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)
BUTTONS = ("reroll", "banish", "skip")
_HOTKEYS = {pygame.K_r: "reroll", pygame.K_b: "banish", pygame.K_x: "skip"}


class CardPicker:
    def __init__(self, manager, progress, choose: Callable[[object], None],
                 spells: dict | None = None, pauses: bool = True) -> None:
        self.manager = manager
        self.choose = choose
        self.pauses = pauses
        self.index = 0                    # highlighted card
        self.row = 0                      # 0: the cards, 1: the buttons
        self.button = 0                   # highlighted button (row 1)
        self.refresh(progress, spells)

    def refresh(self, progress, spells: dict | None = None) -> None:
        """Show the player's current offer and counts (after a choice)."""
        offer = list(progress.offer)
        if offer != getattr(self, "offer", None):
            self.index = 0
        self.offer = offer
        self.waiting = progress.picks - 1      # picks banked after this one
        self.rerolls = progress.rerolls
        self.banishes = progress.banishes
        self.spells = dict(spells or {})

    def enabled(self, button: str) -> bool:
        if button == "reroll":
            return self.rerolls > 0
        if button == "banish":
            return self.banishes > 0
        return True

    # --- Layout ---------------------------------------------------------------------

    def _layout(self) -> tuple[int, int, int]:
        """(left column, top row, card width) for the current grid."""
        d = self.manager.display
        n = max(1, len(self.offer))
        w = min(MAX_CARD_W, (d.cols - 4 - GAP * (n - 1)) // n)
        total = n * w + (n - 1) * GAP
        top = max(2, (d.rows - self.card_h()) // 2 - 1)
        return (d.cols - total) // 2, top, w

    def card_h(self) -> int:
        """Card height: CARD_H, taller if a narrow card's text needs it (4
        cards on a small screen)."""
        d = self.manager.display
        n = max(1, len(self.offer))
        inner = min(MAX_CARD_W, (d.cols - 4 - GAP * (n - 1)) // n) - 4
        lines = max((len(wrap(card_text(k, r, self.spells)[1], inner, None))
                     for k, r in self.offer), default=0)
        return max(CARD_H, 6 + lines + 4)

    def card_at(self, col: int, row: int) -> int | None:
        left, top, w = self._layout()
        if not top <= row < top + self.card_h():
            return None
        for i in range(len(self.offer)):
            c = left + i * (w + GAP)
            if c <= col < c + w:
                return i
        return None

    def _labels(self) -> list[str]:
        heal = round(config.SKIP_HEAL * 100)
        return [f" [R] REROLL {self.rerolls} ", f" [B] BANISH {self.banishes} ",
                f" [X] SKIP +{heal}% HP "]

    def _buttons(self) -> list[tuple[int, int, str]]:
        """(column, row, label) of each button, centred under the cards."""
        left, top, w = self._layout()
        n = max(1, len(self.offer))
        total = n * w + (n - 1) * GAP
        labels = self._labels()
        span = sum(len(s) for s in labels) + 2 * (len(labels) - 1)
        col = left + (total - span) // 2
        out = []
        for s in labels:
            out.append((col, top + self.card_h() + 1, s))
            col += len(s) + 2
        return out

    def button_at(self, col: int, row: int) -> int | None:
        for i, (c, r, s) in enumerate(self._buttons()):
            if r == row and c <= col < c + len(s):
                return i
        return None

    # --- Input ------------------------------------------------------------------------

    def _act(self, button: str) -> None:
        if not self.enabled(button):
            return
        self.choose(("banish", self.index) if button == "banish" else button)

    def handle_event(self, event: pygame.event.Event) -> None:
        if not self.offer:
            return
        if event.type == pygame.KEYDOWN:
            if event.key in _HOTKEYS:
                self._act(_HOTKEYS[event.key])
            elif event.key in _DOWN:
                self.row = 1
            elif event.key in _UP:
                self.row = 0
            elif event.key in _LEFT + _RIGHT:
                step = -1 if event.key in _LEFT else 1
                if self.row == 0:
                    self.index = (self.index + step) % len(self.offer)
                else:
                    self.button = (self.button + step) % len(BUTTONS)
            elif event.key in _TAKE:
                if self.row == 0:
                    self.choose(self.index)
                else:
                    self._act(BUTTONS[self.button])
            return
        if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
            cell = self.manager.display.window_to_cell(*event.pos)
            if cell is None:
                return
            click = event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
            i = self.card_at(*cell)
            if i is not None:
                self.index, self.row = i, 0
                if click:
                    self.choose(i)
                return
            b = self.button_at(*cell)
            if b is not None:
                self.button, self.row = b, 1
                if click:
                    self._act(BUTTONS[b])

    # --- Drawing ----------------------------------------------------------------------

    def draw(self, text: TextRenderer) -> None:
        if not self.offer:
            return
        left, top, w = self._layout()
        total = len(self.offer) * w + (len(self.offer) - 1) * GAP
        more = f"   (+{self.waiting} more)" if self.waiting > 0 else ""
        center(text, top - 2, f" LEVEL UP!  choose a card{more} ", palette.CARD_TITLE,
               left, total, palette.HUD_PANEL)
        for i, (key, rarity) in enumerate(self.offer):
            self._card(text, left + i * (w + GAP), top, w, key, rarity, i == self.index)
        for i, (col, row, label) in enumerate(self._buttons()):
            on = self.row == 1 and i == self.button
            fg = (palette.CARD_SELECTED if on else palette.CARD_TEXT) \
                if self.enabled(BUTTONS[i]) else palette.CARD_TAG
            text.put(col, row, label, fg, palette.CARD_BG_SELECTED if on else palette.HUD_PANEL)
        hint = " LEFT / RIGHT choose   ENTER or click take   DOWN for the buttons "
        if len(hint) > total:
            hint = " ENTER take   DOWN buttons "
        center(text, top + self.card_h() + 3, hint, colors.GREY, left, total, palette.HUD_PANEL)

    def _card(self, text: TextRenderer, col: int, top: int, w: int, key: str, rarity: str,
              selected: bool) -> None:
        card = config.CARDS[key]
        name, effect = card_text(key, rarity, self.spells)
        color = palette.CARD_RARITY[rarity]
        bright = selected and self.row == 0
        edge = palette.CARD_SELECTED if bright else color
        bg = palette.CARD_BG_SELECTED if selected else palette.HUD_PANEL
        h = self.card_h()
        text.put(col, top, "┌" + "─" * (w - 2) + "┐", edge, bg)
        for r in range(top + 1, top + h - 1):
            text.put(col, r, "│" + " " * (w - 2) + "│", edge, bg)
        text.put(col, top + h - 1, "└" + "─" * (w - 2) + "┘", edge, bg)
        inner = w - 4
        center(text, top + 2, rarity.upper(), color, col, w, bg)
        center(text, top + 4, name.upper()[:inner], palette.CARD_TITLE, col, w, bg)
        for j, line in enumerate(wrap(effect, inner, None)):
            center(text, top + 6 + j, line, palette.CARD_TEXT, col, w, bg)
        if card.heroes and len(card.heroes) == 1:
            center(text, top + h - 3, card.heroes[0].upper(), palette.CARD_TAG, col, w, bg)
        elif key in config.SPELLS:
            center(text, top + h - 3, "SPELL", palette.CARD_TAG, col, w, bg)
        if bright:
            # Bars hugging the card above and below (half blocks: the font
            # has no arrow glyphs).
            center(text, top - 1, "▄" * (w - 4), palette.CARD_SELECTED, col, w, None)
            center(text, top + h, "▀" * (w - 4), palette.CARD_SELECTED, col, w, None)


def wrap(s: str, width: int, most: int | None = 4) -> list[str]:
    """A card's effect in lines of `width` (at most `most` of them)."""
    lines = textwrap.wrap(s, max(8, width))
    return lines if most is None else lines[:most]
