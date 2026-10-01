"""
meta/run_stats.py -- what happened in the run in progress.

The game scene feeds it every frame (alive time, where the hero is) and on
every kill; the game-over screen shows it and hands it to the records.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field


@dataclass
class RunStats:
    hero: str
    seed: int | None
    start: tuple[float, float]
    time: float = 0.0                    # seconds alive (paused time excluded)
    furthest: float = 0.0                # max distance from the start, tiles
    walked: float = 0.0                  # tiles walked
    kills: Counter = field(default_factory=Counter)   # enemy name -> count
    biomes: list[str] = field(default_factory=list)   # in the order found
    cards: list[str] = field(default_factory=list)    # card keys, in the order taken
    loot: float = 0.0                    # found this run (kept however it ends)

    @property
    def total_kills(self) -> int:
        return sum(self.kills.values())

    def tick(self, dt: float, x: float, y: float, walked: float, biome: str | None) -> None:
        self.time += dt
        self.furthest = max(self.furthest, math.hypot(x - self.start[0], y - self.start[1]))
        self.walked = walked
        if biome is not None and biome not in self.biomes:
            self.biomes.append(biome)

    def killed(self, name: str) -> None:
        self.kills[name] += 1


def format_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"
