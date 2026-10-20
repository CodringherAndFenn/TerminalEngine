"""
players/progress.py -- a player's level and experience.

XP comes from gems that kills drop (each enemy type's `xp` in
config.ENEMIES; entities/gems.py); later from other deeds too. Each level needs more XP than the last:

    xp to go from level n to n+1 = LEVEL_XP_BASE * LEVEL_XP_GROWTH ** (n - 1)

(12, 16, 22, 30, 40, ... with the defaults), so early levels come quickly
and later ones take a real fight. Levels stop at MAX_LEVEL. Every level gained is a gear pick
(`picks`), spent on a piece, an UPGRADE or a skip (players/gear.py). Rerolls
and banishes are per run. What the hero wears is `gear`.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .. import config
from .gear import Equipment


def xp_for_level(level: int) -> int:
    """XP needed to go from `level` to the next."""
    return max(1, round(config.LEVEL_XP_BASE * config.LEVEL_XP_GROWTH ** (level - 1)))


@dataclass
class Progress:
    level: int = 1
    xp: float = 0.0          # toward the next level
    picks: int = 0           # level-ups not yet spent on a gear pick
    gear: Equipment = field(default_factory=Equipment)  # worn pieces and the bag (M28.1)
    offer: list = field(default_factory=list)          # gear.Offer on the table now
    offers: int = 0          # offers drawn so far (seeds the next draw)
    rerolls: int = config.CARD_REROLLS
    banishes: int = config.CARD_BANISHES
    banished: set = field(default_factory=set)         # bases out of this run
    resolved: int = 0        # picks spent (taken or skipped): Encore Tour counts them
    decree: str | None = None    # Royal Decree: the next offer is this rarity or better
    free_upgrades: int = 0   # Grizzled Signet +6 (Drilled): UPGRADEs that don't cost the pick
    # Fourleaf Ring (L), Foresight (M28.3h): the next level's offer, drawn
    # early; the index of the piece kept in it (the gear screen's NEXT
    # OFFER page); on the table, the kept piece and its place (it stays
    # through rerolls until the pick is spent).
    next_offer: list = field(default_factory=list)
    kept: int | None = None
    keep: tuple | None = None

    @property
    def needed(self) -> int:
        return xp_for_level(self.level)

    @property
    def frac(self) -> float:
        return 1.0 if self.maxed else self.xp / self.needed

    @property
    def maxed(self) -> bool:
        return self.level >= config.MAX_LEVEL

    @property
    def cards(self) -> Counter:
        """Worn bases (level + 1 each) and affix lines (Equipment.counts)."""
        return self.gear.counts()

    def add(self, amount: float) -> int:
        """Gain XP; returns how many levels that gained. Stops at MAX_LEVEL."""
        if self.maxed:
            return 0
        self.xp += amount
        gained = 0
        while self.xp >= self.needed and not self.maxed:
            self.xp -= self.needed
            self.level += 1
            self.picks += 1
            gained += 1
        if self.maxed:
            self.xp = 0.0
        return gained
