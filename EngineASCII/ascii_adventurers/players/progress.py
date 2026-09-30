"""
players/progress.py -- a player's level and experience.

XP comes from kills (each enemy type's `xp` in config.ENEMIES); later from
other deeds too. Each level needs more XP than the last:

    xp to go from level n to n+1 = LEVEL_XP_BASE * LEVEL_XP_GROWTH ** (n - 1)

(12, 16, 22, 30, 40, ... with the defaults), so early levels come quickly
and later ones take a real fight. Every level gained is a card pick
(`picks`), spent when cards arrive (M11).
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
    xp: int = 0              # toward the next level
    picks: int = 0           # level-ups not yet spent on a card
    cards: Counter = field(default_factory=Counter)   # card key -> copies taken
    offer: list[str] = field(default_factory=list)     # cards on the table now
    offers: int = 0          # offers drawn so far (seeds the next draw)

    @property
    def needed(self) -> int:
        return xp_for_level(self.level)

    @property
    def frac(self) -> float:
        return self.xp / self.needed

    def add(self, amount: int) -> int:
        """Gain XP; returns how many levels that gained."""
        self.xp += amount
        gained = 0
        while self.xp >= self.needed:
            self.xp -= self.needed
            self.level += 1
            self.picks += 1
            gained += 1
        return gained
