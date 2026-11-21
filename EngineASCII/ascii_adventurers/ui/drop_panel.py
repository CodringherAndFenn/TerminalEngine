"""
ui/drop_panel.py -- the pickup panel for a piece of gear on the ground
(M28.4a, GEAR.md 4.2).

A hero stands over a dropped piece: its card comes up like a level-up
pick's (one card, with the "wearing" strip under it), and the buttons are
WEAR (a new piece, a swap -- which ring / trinket, and which bag piece to
salvage when the bag is full, asked like the picker does -- or +1 to the
worn piece of that base), BAG (into the bag; a full bag asks which piece
to salvage), SALVAGE (loot at once) and LEAVE (it stays on the ground).
Hotkeys W / B / X / ESC. In single player the game is paused meanwhile.

It only shows and chooses: `choose` gets ("found", drop id, "take", slot,
drop index), ("found", id, "bag", drop index), ("found", id, "salvage") or
("found", id, "leave"); the game applies it (scenes/game.py _found_action).
"""

from __future__ import annotations

from typing import Callable

import pygame

from .. import config
from ..players.gear import offer_for
from .gear_picker import GearPicker
from .gear_screen import GearScreen

BUTTONS = ("wear", "bag", "salvage", "leave")
_HOTKEYS = {pygame.K_w: "wear", pygame.K_b: "bag", pygame.K_x: "salvage",
            pygame.K_ESCAPE: "leave"}


class DropPanel(GearPicker):
    def __init__(self, manager, progress, drop, choose: Callable[[object], None],
                 pauses: bool = True) -> None:
        self.drop = drop
        super().__init__(manager, progress, choose, pauses)
        self.buttons = BUTTONS
        self.hotkeys = _HOTKEYS
        self.title = f" FOUND: {drop.name} "

    def refresh(self, progress) -> None:
        """The panel shows the found piece, not the level-up offer."""
        self.progress = progress
        self.offer = [offer_for(self.drop.piece, progress.gear)]
        self.eq = progress.gear
        self.waiting = 0
        self.rerolls = self.banishes = 0
        if self.sub is not None:
            self.sub.refresh(progress)

    def enabled(self, button: str) -> bool:
        if button == "wear":
            o = self.offer[0]
            if o.kind == "plus":
                worn = self.eq.worn.get(self.eq.wearing(o.key))
                return worn is not None and worn.level < config.GEAR_MAX_LEVEL
        return True

    def _labels(self) -> list[str]:
        o = self.offer[0]
        wear = " [W] +1 TO WORN " if o.kind == "plus" else " [W] WEAR " if o.kind == "new" \
            else " [W] SWAP IN "
        return [wear, " [B] BAG IT ", " [X] SALVAGE ", " [ESC] LEAVE "]

    # --- Choosing (the picker's take() handles the swap questions) --------------------

    def take(self, i: int) -> None:
        if self.offer[0].kind == "swap":
            super().take(0)              # (which ring / trinket; a full bag: salvage which)
        else:
            self._send(0, None, None)    # a new piece, or +1 to the worn one

    def _send(self, i: int, slot: str, drop) -> None:
        self.sub = None
        self.choose(("found", self.drop.id, "take", slot, drop))

    def _bag(self) -> None:
        if len(self.eq.bag) >= self.eq.bag_size:
            self.sub = GearScreen(self.manager, self.progress, "drop",
                                  outgoing=self.drop.piece,
                                  done=self._bagged, cancel=self._back, pauses=self.pauses)
        else:
            self._bagged(None)

    def _bagged(self, drop) -> None:
        self.sub = None
        self.choose(("found", self.drop.id, "bag", drop))

    def _act(self, button: str) -> None:
        if not self.enabled(button):
            return
        if button == "wear":
            self.take(0)
        elif button == "bag":
            self._bag()
        elif button == "salvage":
            self.choose(("found", self.drop.id, "salvage"))
        else:
            self.choose(("found", self.drop.id, "leave"))

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.sub is not None and event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._back()                 # (ESC in a sub-question: back to the panel)
            return
        super().handle_event(event)
