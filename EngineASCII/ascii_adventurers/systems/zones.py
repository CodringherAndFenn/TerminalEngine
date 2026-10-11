"""
systems/zones.py -- patches of ground that hurt enemies for a while.

  crackle  Ball Lightning: where a bolt hit, it keeps crackling, striking
           everything within `radius` every `every` s for `damage`.
  pool     Poison Flask: everything standing in it gets `stacks` of the
           zone's status every `every` s.
  trail    a dodge roll's trail (Scorched Trail, Prism Dash; systems/roll.py):
           works like a pool, a small one.

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
    slow: float = 0.0                 # P8 webs: who stands in it is slowed to x this
    restore: tuple | None = None      # P11: (tx, ty, tile) put back on the world when it ends
    root: float = 0.0                 # P11: s anyone in it at its end is rooted (a hag's curse)
    heal: float = 0.0                 # P12: x max HP healed each tick, enemies only (pollen)
    timer: float = 0.0
    age: float = field(default=0.0)


def update_zones(zones: list[Zone], actors, effects: list[Effect], dt: float,
                 world=None) -> None:
    from .combat import _may_hurt, strike
    for z in zones:
        z.age += dt
        z.timer -= dt
        if z.timer > 1e-9:
            continue
        z.timer += z.every
        for a in actors:
            if z.heal and getattr(a, "faction", "") == "enemy" and a.alive and a.hp < a.max_hp \
                    and not getattr(a, "boss", False) \
                    and math.hypot(a.x - z.x, a.y - z.y) <= z.radius + a.hit_radius:
                a.hp = min(float(a.max_hp), a.hp + a.max_hp * z.heal)   # (P12: pollen)
                continue
            if not a.hittable or not _may_hurt(z.source, a):
                continue
            if math.hypot(a.x - z.x, a.y - z.y) > z.radius + a.hit_radius:
                continue
            if z.damage > 0:
                strike(a, z.damage, z.source, math.atan2(a.y - z.y, a.x - z.x), effects, z.tags)
            if z.inflicts and a.alive:
                inflict(a, z.inflicts, z.source, z.stacks)
            if z.slow and hasattr(a, "slowed"):
                a.slowed(z.slow, z.every * 1.5)
    for z in zones:
        if z.age < z.life:
            continue
        if z.restore is not None and world is not None and hasattr(world, "set_tile"):
            world.set_tile(*z.restore)                # (P11: a stuck javelin's spot)
        if z.root > 0:                                # (P11: the hag's curse lands)
            from .combat import _may_hurt
            for a in actors:
                if a.alive and hasattr(a, "slowed") and _may_hurt(z.source, a) \
                        and math.hypot(a.x - z.x, a.y - z.y) <= z.radius + a.hit_radius:
                    a.slowed(0.0, z.root)
                    effects.append(Effect("toast", a.x, a.y - 2, label="ROOTED!"))
    zones[:] = [z for z in zones if z.age < z.life]
