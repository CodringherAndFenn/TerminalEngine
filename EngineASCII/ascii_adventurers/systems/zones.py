"""
systems/zones.py -- patches of ground that hurt enemies for a while.

  crackle  Ball Lightning: where a bolt hit, it keeps crackling, striking
           everything within `radius` every `every` s for `damage`.
  pool     Poison Flask: everything standing in it gets `stacks` of the
           zone's status every `every` s.
  trail    a dodge roll's trail (Scorched Trail, Prism Dash; systems/roll.py):
           works like a pool, a small one.
  puddle   Downpour (Stormjar +3): the rain under the storm cloud. It hurts
           nobody; enemies in it count as standing in water (Ground fault).
  wisp     Will-o'-wisps (Firefly Lantern +9): burns everything round it.
  ball     Thunderball (Crackle Staff +9): a big crackle rolling along
           `path` (a bolt's way, end to end over its life).
  well     Singularity (Gravewell Staff +9): drags enemies in at `pull`
           tiles/s (bosses and things that never move stay put).

A zone belongs to the hero who made it (damage and statuses are theirs,
kill credit too) and is gone after `life` s. Part of the simulation step.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .. import config
from ..entities.effects import Effect
from .statuses import has, inflict, wounded


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
    # M28.2f: a Witch's Flask pool (Cauldron merges them); it grows `grow`
    # x its `base` radius over its life (Bubbling); wet ground (Downpour).
    flask: bool = False
    grow: float = 0.0
    base: float = 0.0
    wet: bool = False
    # M28.2g: a crackle on an enemy moves with it (Sticky); a ball rolls
    # along `path`; a well drags enemies in at `pull` tiles/s.
    follow: object = None
    path: list | None = None
    pull: float = 0.0
    # M28.3l: a spell's ground (Fortissimo Lute (L), Tutti: the crescendo
    # counts for its hits).
    spell: bool = False
    timer: float = 0.0
    age: float = field(default=0.0)


def update_zones(zones: list[Zone], actors, effects: list[Effect], dt: float,
                 world=None) -> None:
    from .combat import _may_hurt, ground_cut, skims, strike
    for z in zones:
        z.age += dt
        if z.follow is not None:
            if z.follow.alive:
                z.x, z.y = z.follow.x, z.follow.y
            else:
                z.follow = None                   # (it stays where its enemy fell)
        if z.path:
            z.x, z.y = along(z.path, min(1.0, z.age / z.life))
        if z.pull > 0:
            _drag(z, actors, dt, world)
        if z.grow:
            if not z.base:
                z.base = z.radius
            z.radius = z.base * (1 + z.grow * min(1.0, z.age / z.life))
        z.timer -= dt
        if z.timer > 1e-9:
            continue
        z.timer += z.every
        for a in actors:
            if z.heal and getattr(a, "faction", "") == "enemy" and a.alive and a.hp < a.max_hp \
                    and not getattr(a, "boss", False) and not wounded(a) \
                    and math.hypot(a.x - z.x, a.y - z.y) <= z.radius + a.hit_radius:
                a.hp = min(float(a.max_hp), a.hp + a.max_hp * z.heal)   # (P12: pollen)
                continue
            if not a.hittable or not _may_hurt(z.source, a):
                continue
            if z.kind in config.PLAGUE_DOCTOR and has(a, "virulence+6") \
                    and getattr(z.source, "faction", None) != "player":
                continue                              # (Plaguebeak +6: toxic ground)
            if getattr(z.source, "faction", None) != "player" and skims(a):
                continue                              # (Wingheel +9: over the ground)
            if math.hypot(a.x - z.x, a.y - z.y) > z.radius + a.hit_radius:
                continue
            if z.wet:
                a.wet = z                             # (Downpour: statuses._wet)
            if z.damage > 0:
                cut = ground_cut(a) if getattr(z.source, "faction", None) != "player" else 1.0
                if z.spell:
                    z.source.spelling = True
                strike(a, z.damage * cut, z.source, math.atan2(a.y - z.y, a.x - z.x), effects, z.tags)
                if z.spell:
                    z.source.spelling = False
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
                if a.alive and hasattr(a, "slowed") and _may_hurt(z.source, a) and not skims(a) \
                        and math.hypot(a.x - z.x, a.y - z.y) <= z.radius + a.hit_radius:
                    a.slowed(0.0, z.root)
                    effects.append(Effect("toast", a.x, a.y - 2, label="ROOTED!"))
    zones[:] = [z for z in zones if z.age < z.life]


def along(path: list, f: float) -> tuple[float, float]:
    """The point a share `f` (0..1) of the way along a path of points."""
    legs = [math.hypot(x1 - x0, y1 - y0) for (x0, y0), (x1, y1) in zip(path, path[1:])]
    left = sum(legs) * f
    for ((x0, y0), (x1, y1)), leg in zip(zip(path, path[1:]), legs):
        if left <= leg and leg > 0:
            return x0 + (x1 - x0) * left / leg, y0 + (y1 - y0) * left / leg
        left -= leg
    return path[-1]


def _drag(z: Zone, actors, dt: float, world) -> None:
    """A well's pull this step (combat.push leaves bosses and things that
    never move where they are)."""
    from .combat import _may_hurt, push
    if world is None:
        return
    for a in actors:
        if not a.hittable or not _may_hurt(z.source, a):
            continue
        d = math.hypot(a.x - z.x, a.y - z.y)
        if 0.3 < d <= z.radius + a.hit_radius:
            step = min(z.pull * dt, d - 0.3)
            push(a, world, (z.x - a.x) / d * step, (z.y - a.y) / d * step)
