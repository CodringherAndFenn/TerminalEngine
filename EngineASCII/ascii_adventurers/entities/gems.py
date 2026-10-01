"""
entities/gems.py -- XP gems: dropped by kills, pulled in, collected.

A player's kill drops a gem worth the enemy's `xp` where it fell. A gem
lies still until a living hero comes within their pickup radius (Magnet
cards widen it); then it's theirs: it flies to them, speeding up from
GEM_PULL_SPEED[0] to [1], and is collected within GEM_CATCH_RADIUS. Its
XP is multiplied by the collector's XP bonus (Scholar). Gems fade after
GEM_LIFETIME; over GEM_MAX on the ground, the oldest one merges into the
gem nearest to it, so no XP is ever lost to the cap.

Everything here is part of the simulation step (deterministic: no clock,
no randomness).
"""

from __future__ import annotations

import math

from .. import config


class Gem:
    __slots__ = ("x", "y", "value", "age", "target", "speed", "alive", "prev_pos")

    def __init__(self, x: float, y: float, value: float) -> None:
        self.x, self.y = x, y
        self.value = value
        self.age = 0.0
        self.target = None          # the hero pulling it in
        self.speed = 0.0
        self.alive = True
        self.prev_pos = None

    @property
    def tier(self) -> int:
        """0 small, 1 medium, 2 big (its look)."""
        small, medium = config.GEM_TIERS
        return 0 if self.value < small else 1 if self.value < medium else 2


def drop(gems: list[Gem], x: float, y: float, value: float) -> None:
    if value <= 0:
        return
    gems.append(Gem(x, y, value))
    if len(gems) > config.GEM_MAX:
        oldest = gems.pop(0)
        if gems:
            near = min(gems, key=lambda g: (g.x - oldest.x) ** 2 + (g.y - oldest.y) ** 2)
            near.value += oldest.value


def update_gems(gems: list[Gem], players, dt: float) -> list[tuple[object, float]]:
    """Age, attract and collect gems. `players` are the game's players
    (hero + stats). Returns (player, xp) for every gem collected this step."""
    collected = []
    heroes = [p for p in players if p.alive]
    for g in gems:
        g.age += dt
        if g.target is None:
            if g.age >= config.GEM_LIFETIME:
                g.alive = False
                continue
            for p in heroes:
                stats = p.hero.stats
                r = stats.pickup_radius if stats is not None else config.PICKUP_RADIUS
                if (p.hero.x - g.x) ** 2 + (p.hero.y - g.y) ** 2 <= r * r:
                    g.target, g.speed = p, config.GEM_PULL_SPEED[0]
                    break
            if g.target is None:
                continue
        p = g.target
        if not p.alive:                 # its hero fell: it drops where it is
            g.target = None
            continue
        g.speed = min(config.GEM_PULL_SPEED[1], g.speed + config.GEM_PULL_ACCEL * dt)
        dx, dy = p.hero.x - g.x, p.hero.y - g.y
        dist = math.hypot(dx, dy)
        step = g.speed * dt
        if dist - step <= config.GEM_CATCH_RADIUS:
            g.alive = False
            stats = p.hero.stats
            collected.append((p, g.value * (1 + (stats.xp if stats is not None else 0.0))))
            continue
        g.x += dx / dist * step
        g.y += dy / dist * step
    gems[:] = [g for g in gems if g.alive]
    return collected
