"""
entities/drops.py -- pieces of gear lying on the ground (M28.4a, GEAR.md 4.2).

An elite's kill (ELITE_DROP of the time) or a chest leaves a `GearDrop`
where it fell: a rolled piece (players/gear.draw_drop) with its rarity's
glow and its name as a label. A living hero within GEAR_DROP_RADIUS opens
the pickup panel (ui/drop_panel.py): wear it (a swap or a +1), bag it, or
salvage it; LEAVE closes the panel and the piece stays. A left piece
doesn't open again until that hero has walked away and come back
(`cooled`). Drops never fade; one that's taken is removed by the game.
Seen drops (a hero came within GEAR_DROP_SEEN) are pinned on the maps.

Deterministic: part of the simulation step, no clock.
"""

from __future__ import annotations

import math

from .. import config
from ..players.gear import Piece


class GearDrop:
    __slots__ = ("x", "y", "piece", "id", "seen", "cooled", "taken", "age")

    def __init__(self, x: float, y: float, piece: Piece, id_: int) -> None:
        self.x, self.y = x, y
        self.piece = piece
        self.id = id_              # stable across steps (the panel names it; ids never repeat)
        self.seen = False
        self.cooled: set = set()   # player indexes who LEFT it and haven't walked away yet
        self.taken = False
        self.age = 0.0

    @property
    def name(self) -> str:
        return self.piece.name


def update_drops(drops: list[GearDrop], players, dt: float) -> list[tuple[object, GearDrop]]:
    """Age the drops, note which were seen, and find who's standing over
    one: (player, drop) for every living non-ghost hero within
    GEAR_DROP_RADIUS of a drop they haven't LEFT (a left drop cools once
    they're out of twice the radius). Taken drops are removed."""
    out = []
    heroes = [p for p in players if p.alive and not p.ghost]
    for d in drops:
        d.age += dt
        for p in heroes:
            dist = math.hypot(p.hero.x - d.x, p.hero.y - d.y)
            if dist <= config.GEAR_DROP_SEEN:
                d.seen = True
            if p.index in d.cooled:
                if dist > config.GEAR_DROP_RADIUS * 2:
                    d.cooled.discard(p.index)
                continue
            if dist <= config.GEAR_DROP_RADIUS:
                out.append((p, d))
    drops[:] = [d for d in drops if not d.taken]
    return out
