"""
ui/gear_picker.py -- the level-up gear pick (design/GEAR.md 15.4, M28.1).

Three (or more) piece cards across the middle of the screen, each with its
own "wearing" strip under it -- what's in that card's slot now, EMPTY, or
how many ring / trinket slots are free (user: "I will be wearing multiple
pieces, so displaying just one worn piece underneath is not enough") --
then UPGRADE..., REROLL, BANISH and SKIP.

Left / Right (A / D, the d-pad or left stick) move between the cards,
Enter / Space (gamepad A) takes the highlighted one; the mouse highlights
the card under it and a click takes it. Down moves to the row of buttons.
Hotkeys: U upgrade, R reroll, B banish, X skip. In single player the game
is paused while it's up (`pauses`); in multiplayer it keeps running.

UPGRADE opens its own screen (ui/gear_screen.GearScreen "upgrade": every
worn piece, choose one for +1; ESC back). Taking a swap for a ring or a
trinket first asks which one it replaces; a swap with the bag full asks
which piece to salvage. The picker only shows and chooses: `choose`
gets an offer index, ("take", index, slot, drop), ("upgrade", slot),
"reroll", "skip" or ("banish", index); the game applies it and calls
refresh().
"""

from __future__ import annotations

from typing import Callable

import pygame

from engine import TextRenderer, colors

from .. import config, palette
from ..players.gear import base_slot
from .frame import center, glint
from .gear_screen import GearScreen, piece_lines, slot_label

CARD_H = 15
GAP = 3
MAX_CARD_W = 30
STRIP_H = 3
_LEFT = (pygame.K_LEFT, pygame.K_a)
_RIGHT = (pygame.K_RIGHT, pygame.K_d)
_UP = (pygame.K_UP, pygame.K_w)
_DOWN = (pygame.K_DOWN, pygame.K_s)
_TAKE = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)
BUTTONS = ("upgrade", "reroll", "banish", "skip")
_HOTKEYS = {pygame.K_u: "upgrade", pygame.K_r: "reroll", pygame.K_b: "banish", pygame.K_x: "skip"}


class GearPicker:
    def __init__(self, manager, progress, choose: Callable[[object], None],
                 pauses: bool = True) -> None:
        self.manager = manager
        self.choose = choose
        self.pauses = pauses
        self.index = 0                    # highlighted card
        self.row = 0                      # 0: the cards, 1: the buttons
        self.button = 0                   # highlighted button (row 1)
        self.sub: GearScreen | None = None
        self.progress = progress
        self.refresh(progress)

    def refresh(self, progress) -> None:
        """Show the player's current offer and counts (after a choice)."""
        self.progress = progress
        offer = list(progress.offer)
        if offer != getattr(self, "offer", None):
            self.index = 0
            self.sub = None              # (multiplayer: the offer changed under a question)
        self.offer = offer
        self.eq = progress.gear
        self.waiting = progress.picks - 1      # picks banked after this one
        self.rerolls = progress.rerolls
        self.banishes = progress.banishes
        if self.sub is not None:
            self.sub.refresh(progress)

    def can_upgrade(self) -> bool:
        return any(p.level < config.GEAR_MAX_LEVEL for p in self.eq.worn.values())

    def enabled(self, button: str) -> bool:
        if button == "upgrade":
            return self.can_upgrade()
        if button == "reroll":
            return self.rerolls > 0
        if button == "banish":
            return self.banishes > 0
        return True

    # --- Layout ---------------------------------------------------------------------

    def _card_w(self) -> int:
        d = self.manager.display
        n = max(1, len(self.offer))
        return min(MAX_CARD_W, (d.cols - 4 - GAP * (n - 1)) // n)

    def _lines(self, i: int) -> list:
        o = self.offer[i]
        level = self.eq.worn[self.eq.wearing(o.key)].level if o.kind == "plus" else 0
        return piece_lines(o.key, o.rarity, level, o.affixes, self._card_w() - 4, o.kind)

    def card_h(self) -> int:
        """Card height: CARD_H, taller if a card's text needs it."""
        most = max((len(self._lines(i)) for i in range(len(self.offer))), default=0)
        return max(CARD_H, most + 3)

    def _layout(self) -> tuple[int, int, int]:
        """(left column, top row, card width) for the current grid."""
        d = self.manager.display
        n = max(1, len(self.offer))
        w = self._card_w()
        total = n * w + (n - 1) * GAP
        block = self.card_h() + STRIP_H + 4
        top = max(2, (d.rows - block) // 2)
        return (d.cols - total) // 2, top, w

    def card_at(self, col: int, row: int) -> int | None:
        left, top, w = self._layout()
        if not top <= row < top + self.card_h() + STRIP_H:
            return None
        for i in range(len(self.offer)):
            c = left + i * (w + GAP)
            if c <= col < c + w:
                return i
        return None

    def _labels(self) -> list[str]:
        heal = round(config.SKIP_HEAL * 100)
        free = getattr(self.progress, "free_upgrades", 0)        # (Grizzled Signet +6)
        up = f" [U] FREE UPGRADE {free} " if free else " [U] UPGRADE... "
        return [up, f" [R] REROLL {self.rerolls} ", f" [B] BANISH {self.banishes} ",
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
            out.append((col, top + self.card_h() + STRIP_H + 1, s))
            col += len(s) + 2
        return out

    def button_at(self, col: int, row: int) -> int | None:
        for i, (c, r, s) in enumerate(self._buttons()):
            if r == row and c <= col < c + len(s):
                return i
        return None

    # --- Choosing -------------------------------------------------------------------

    def take(self, i: int) -> None:
        o = self.offer[i]
        if o.kind != "swap":
            self.choose(i)
            return
        kind = base_slot(o.key)
        slots = self.eq.slots_of(kind)
        if len(slots) > 1:
            self.sub = GearScreen(self.manager, self.progress, "slot", kind=kind,
                                  done=lambda s: self._swap_into(i, s), cancel=self._back,
                                  pauses=self.pauses)
        else:
            self._swap_into(i, slots[0])

    def _swap_into(self, i: int, slot: str) -> None:
        self.sub = None
        if len(self.eq.bag) >= config.GEAR_BAG:
            self.sub = GearScreen(self.manager, self.progress, "drop",
                                  outgoing=self.eq.worn.get(slot),
                                  done=lambda d: self._send(i, slot, d), cancel=self._back,
                                  pauses=self.pauses)
        else:
            self._send(i, slot, None)

    def _send(self, i: int, slot: str, drop) -> None:
        self.sub = None
        self.choose(("take", i, slot, drop))

    def _upgrade(self) -> None:
        self.sub = GearScreen(self.manager, self.progress, "upgrade",
                              done=self._upgraded, cancel=self._back, pauses=self.pauses)

    def _upgraded(self, slot: str) -> None:
        self.sub = None
        self.choose(("upgrade", slot))

    def _back(self) -> None:
        self.sub = None

    def _act(self, button: str) -> None:
        if not self.enabled(button):
            return
        if button == "upgrade":
            self._upgrade()
        elif button == "banish":
            self.choose(("banish", self.index))
        else:
            self.choose(button)

    # --- Input ------------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        if not self.offer:
            return
        if self.sub is not None:
            self.sub.handle_event(event)
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
                    self.take(self.index)
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
                    self.take(i)
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
        if self.sub is not None:
            self.sub.draw(text)
            return
        left, top, w = self._layout()
        total = len(self.offer) * w + (len(self.offer) - 1) * GAP
        more = f"   (+{self.waiting} more)" if self.waiting > 0 else ""
        center(text, top - 2, f" LEVEL UP!  choose a piece of gear{more} ", palette.CARD_TITLE,
               left, total, palette.HUD_PANEL)
        for i in range(len(self.offer)):
            col = left + i * (w + GAP)
            self._card(text, col, top, w, i, i == self.index)
            self._strip(text, col, top + self.card_h(), w, i)
        for i, (col, row, label) in enumerate(self._buttons()):
            on = self.row == 1 and i == self.button
            fg = (palette.CARD_SELECTED if on else palette.CARD_TEXT) \
                if self.enabled(BUTTONS[i]) else palette.CARD_TAG
            text.put(col, row, label, fg, palette.CARD_BG_SELECTED if on else palette.HUD_PANEL)
        hint = " LEFT / RIGHT choose   ENTER or click take   DOWN for the buttons "
        if len(hint) > total:
            hint = " ENTER take   DOWN buttons "
        center(text, top + self.card_h() + STRIP_H + 3, hint, colors.GREY, left, total,
               palette.HUD_PANEL)

    def _card(self, text: TextRenderer, col: int, top: int, w: int, i: int,
              selected: bool) -> None:
        o = self.offer[i]
        color = palette.CARD_RARITY[o.rarity]
        bright = selected and self.row == 0
        edge = palette.CARD_SELECTED if bright else color
        bg = palette.CARD_BG_SELECTED if selected else palette.HUD_PANEL
        h = self.card_h()
        text.put(col, top, "┌" + "─" * (w - 2) + "┐", edge, bg)
        for r in range(top + 1, top + h - 1):
            text.put(col, r, "│" + " " * (w - 2) + "│", edge, bg)
        text.put(col, top + h - 1, "└" + "─" * (w - 2) + "┘", edge, bg)
        if o.rarity == "legendary":
            glint(text, col, top, w, h, bg)            # (M28.3a: the legendary look)
        for j, (line, fg) in enumerate(self._lines(i)[:h - 3]):
            center(text, top + 1 + j, line[:w - 4], fg, col, w, bg)
        if bright:
            # Bars hugging the card above and below (half blocks: the font
            # has no arrow glyphs).
            center(text, top - 1, "▄" * (w - 4), palette.CARD_SELECTED, col, w, None)

    def _strip(self, text: TextRenderer, col: int, top: int, w: int, i: int) -> None:
        """What the card's slot holds now."""
        o = self.offer[i]
        kind = base_slot(o.key)
        slots = self.eq.slots_of(kind)
        bg = palette.HUD_PANEL
        text.put(col, top, " " * w, colors.GREY, bg)
        text.put(col, top + 1, " " * w, colors.GREY, bg)
        text.put(col, top + 2, " " * w, colors.GREY, bg)
        text.put(col + 1, top, "wearing:", palette.CARD_TAG, bg)
        if o.kind == "plus":
            p = self.eq.worn[self.eq.wearing(o.key)]
            text.put(col + 1, top + 1, f"{p.name} +{p.level}"[:w - 2], palette.CARD_RARITY[p.rarity], bg)
            text.put(col + 1, top + 2, "(this one gets +1)"[:w - 2], palette.CARD_TAG, bg)
        elif len(slots) > 1:
            used = sum(1 for s in slots if s in self.eq.worn)
            names = ", ".join(self.eq.worn[s].name for s in slots if s in self.eq.worn) or "nothing"
            text.put(col + 1, top + 1, f"{used} of {len(slots)} {kind}s"[:w - 2], colors.GREY, bg)
            line = names if o.kind == "new" else "(swap one: to the bag)"
            text.put(col + 1, top + 2, line[:w - 2], palette.CARD_TAG, bg)
        elif slots[0] in self.eq.worn:
            p = self.eq.worn[slots[0]]
            lv = f" +{p.level}" if p.level else ""
            text.put(col + 1, top + 1, f"{p.name}{lv}"[:w - 2], palette.CARD_RARITY[p.rarity], bg)
            text.put(col + 1, top + 2, "(swap: to the bag)"[:w - 2], palette.CARD_TAG, bg)
        else:
            text.put(col + 1, top + 1, f"{slot_label(slots[0])}: EMPTY"[:w - 2], palette.CARD_TEXT, bg)
