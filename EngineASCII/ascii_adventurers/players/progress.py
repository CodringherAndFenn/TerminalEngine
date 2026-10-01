"""
players/progress.py -- a player's level and experience.

XP comes from gems that kills drop (each enemy type's `xp` in
config.ENEMIES; entities/gems.py); later from other deeds too. Each level needs more XP than the last:

    xp to go from level n to n+1 = LEVEL_XP_BASE * LEVEL_XP_GROWTH ** (n - 1)

(12, 16, 22, 30, 40, ... with the defaults), so early levels come quickly
and later ones take a real fight. Levels stop at MAX_LEVEL. Every level gained is a card pick
(`picks`), spent on a card or a skip (players/cards.py). Rerolls and
banishes are per run.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .. import config


def xp_for_level(level: int) -> int:
    """XP needed to go from `level` to the next."""
    return max(1, round(config.LEVEL_XP_BASE * config.LEVEL_XP_GROWTH ** (level - 1)))


@dataclass
class Progress:
    level: int = 1
    xp: float = 0.0          # toward the next level
    picks: int = 0           # level-ups not yet spent on a card
    cards: Counter = field(default_factory=Counter)   # card key -> copies taken
    taken: list = field(default_factory=list)          # (key, rarity), in the order taken
    offer: list = field(default_factory=list)          # (key, rarity) on the table now
    offers: int = 0          # offers drawn so far (seeds the next draw)
    rerolls: int = config.CARD_REROLLS
    banishes: int = config.CARD_BANISHES
    banished: set = field(default_factory=set)         # card keys out of this run

    @property
    def needed(self) -> int:
        return xp_for_level(self.level)

    @property
    def frac(self) -> float:
        return 1.0 if self.maxed else self.xp / self.needed

    @property
    def maxed(self) -> bool:
        return self.level >= config.MAX_LEVEL

    def take(self, key: str, rarity: str) -> None:
        self.cards[key] += 1
        self.taken.append((key, rarity))

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
