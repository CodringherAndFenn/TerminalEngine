"""
ui/widgets.py -- game-specific widgets for the engine's WidgetList: the
hero picker (cards with a sprite preview) and the seed field.

They follow the engine's Widget interface (draw / activate / adjust /
click / hit), so keyboard focus and mouse routing come from WidgetList.
"""

from __future__ import annotations

from typing import Callable

import pygame

from engine import TextRenderer, Widget, colors

from .. import config
from ..render.characters import draw_character
from ..render.sprites import SpriteBank
from .frame import draw_box

CARD_W = 15          # cells per hero card (plus 1 gap)
CARD_H = 7           # rows: frame, 4 rows of sprite, name, frame
PREVIEW_SCALE = 4    # sprite pixels -> canvas pixels


class HeroPicker(Widget):
    """A row of hero cards. Left/Right or a click picks one; the picked
    hero walks on the spot. `row` is the cards' top row."""

    def __init__(self, col: int, row: int, heroes: list[str], bank: SpriteBank, *,
                 index: int = 0, on_change: Callable[[str], None] | None = None) -> None:
        super().__init__(col, row, len(heroes) * (CARD_W + 1) - 1)
        self.heroes = heroes
        self.bank = bank
        self.index = index
        self.on_change = on_change
        self.clock = 0.0          # drives the walk animation

    @property
    def value(self) -> str:
        return self.heroes[self.index]

    def hit(self, col: int, row: int) -> bool:
        return (self.enabled and self.row <= row < self.row + CARD_H
                and self.col <= col < self.col + self.width)

    def _pick(self, index: int) -> None:
        self.index = index % len(self.heroes)
        if self.on_change is not None:
            self.on_change(self.value)

    def adjust(self, delta: int) -> None:
        self._pick(self.index + delta)

    def click(self, col: int, row: int) -> None:
        self._pick(min(len(self.heroes) - 1, (col - self.col) // (CARD_W + 1)))

    def draw(self, text: TextRenderer, focused: bool) -> None:
        cw, ch = text.display.cell_w, text.display.cell_h
        for i, name in enumerate(self.heroes):
            left = self.col + i * (CARD_W + 1)
            picked = i == self.index
            frame = (colors.AMBER if focused else colors.GREEN) if picked else colors.GREEN_DIM
            draw_box(text, left, self.row, CARD_W, CARD_H, frame)
            label = name.upper()
            text.put(left + (CARD_W - len(label)) // 2, self.row + CARD_H - 2, label,
                     colors.WHITE if picked else colors.GREY)
            walking = picked and focused
            frame_no = int(self.clock * 6) % 4 if walking else 0
            x = (left + CARD_W / 2) * cw
            y = (self.row + 1 + 2) * ch + 2
            spec = config.HEROES[name]
            draw_character(self.bank, x, y, spec.sprite, PREVIEW_SCALE, False, frame_no, False)


class SeedField(Widget):
    """The island seed: empty means a random island. Digits type, Backspace
    deletes, Delete clears."""

    MAX_DIGITS = 9

    def __init__(self, col: int, row: int, width: int, label: str, seed: int | None = None,
                 on_activate: Callable[[], None] | None = None) -> None:
        super().__init__(col, row, width)
        self.label = label
        self.digits = str(seed) if seed else ""
        self.on_activate = on_activate
        self.clock = 0.0

    @property
    def seed(self) -> int | None:
        return int(self.digits) if self.digits and int(self.digits) > 0 else None

    def type_key(self, event: pygame.event.Event) -> bool:
        """Handle a KEYDOWN aimed at the field; True if it was used."""
        if event.key == pygame.K_BACKSPACE:
            self.digits = self.digits[:-1]
            return True
        if event.key == pygame.K_DELETE:
            self.digits = ""
            return True
        ch = getattr(event, "unicode", "")
        if ch and ch.isdigit() and len(self.digits) < self.MAX_DIGITS:
            self.digits = (self.digits + ch).lstrip("0")
            return True
        return False

    def activate(self) -> None:
        if self.on_activate is not None:
            self.on_activate()

    def draw(self, text: TextRenderer, focused: bool) -> None:
        label_fg = colors.WHITE if focused else colors.GREEN
        text.put(self.col, self.row, ">" if focused else " ", colors.AMBER, colors.BACKGROUND)
        text.put(self.col + 2, self.row, self.label, label_fg, colors.BACKGROUND)
        cursor = "_" if focused and int(self.clock * 2) % 2 == 0 else " "
        if self.digits:
            value, fg = self.digits + cursor, colors.AMBER if focused else colors.AMBER_DIM
        else:
            value = "random (type a number)" if focused else "random"
            fg = colors.GREY
        text.put(self.col + self.width - 24, self.row, f"{value:<24}", fg, colors.BACKGROUND)
