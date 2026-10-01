"""
systems/zones.py -- patches of ground that hurt enemies for a while.

  crackle  Ball Lightning: where a bolt hit, it keeps crackling, striking
           everything within `radius` every `every` s for `damage`.
  pool     Poison Flask: everything standing in it gets `stacks` of the
           zone's status every `every` s.

A zone belongs to the hero who made it (damage and statuses are theirs,
kill credit too) and is gone after `life` s. Part of the simulation step.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ..entities.effects import Effect
from .statuses import inflict


@dataclass
class Zone:
    kind: str
    x: float
    y: float
    radius: float
    life: float
    every: float
    damage: float
    source: object
    tags: tuple = ()
    inflicts: str | None = None
    stacks: int = 1
    timer: float = 0.0
    age: float = field(default=0.0)


def update_zones(zones: list[Zone], actors, effects: list[Effect], dt: float) -> None:
    from .combat import _may_hurt, strike
    for z in zones:
        z.age += dt
        z.timer -= dt
        if z.timer > 1e-9:
            continue
        z.timer += z.every
        for a in actors:
            if not a.hittable or not _may_hurt(z.source, a):
                continue
            if math.hypot(a.x - z.x, a.y - z.y) > z.radius + a.hit_radius:
                continue
            if z.damage > 0:
                strike(a, z.damage, z.source, math.atan2(a.y - z.y, a.x - z.x), effects, z.tags)
            if z.inflicts and a.alive:
                inflict(a, z.inflicts, z.source, z.stacks)
    zones[:] = [z for z in zones if z.age < z.life]
