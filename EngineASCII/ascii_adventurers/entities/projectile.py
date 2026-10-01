"""
entities/projectile.py -- shots in flight (bolts, arrows, rocks...).

A shot flies in a straight line along the aim angle at its ShellSpec speed,
until it hits an actor or something that blocks shots, or has travelled its
max range. Hit detection lives in systems/combat.py. A returning shot (the
dwarf's axe) then turns and flies back to its owner.
"""

from __future__ import annotations

import math

from ..specs import ShellSpec


class Projectile:
    def __init__(
        self, x: float, y: float, angle: float, spec: ShellSpec,
        owner=None, damage: float | None = None,
    ) -> None:
        self.x = x
        self.y = y
        self.angle = angle            # world radians
        self.spec = spec
        self.owner = owner            # the Actor that fired it (never hits itself)
        self.damage = spec.damage if damage is None else damage
        self.dir_x = math.cos(angle)  # unit direction, world tiles
        self.dir_y = math.sin(angle)
        self.travelled = 0.0          # tiles
        self.alive = True
        self.pierce_left = spec.pierce  # enemies it may still pass through
        self.hit: set[int] = set()    # ids of actors already hit (pierce)
        self.variant = 0              # which of a spread's pellets (its color)
        self.tags: tuple[str, ...] = ()   # the weapon's damage tags (bucket T)
        self.mult = 1.0               # per-shot damage multiplier (Overload)
        self.extra_chain = 0          # per-shot extra lightning jumps (Overload)
        # Cards (M16): how far it may fly (Deadeye doubles it), its hit radius
        # bonus (Bright Colors), the colors of its shot (Prism), wall bounces
        # (Ricochet), whether it split off another shot (can't split again),
        # whether a summon fired it (no crits / statuses unless Pack
        # Leader), and a status it carries ((name, stacks): Fire Wand).
        self.max_range = spec.max_range
        self.size = 0.0
        self.group: dict | None = None
        self.bounces = 0
        self.child = False
        self.summon = False
        self.inflicts: tuple[str, int] | None = None
        self.returning = False        # boomerangs: on the way back to the owner
        # M17 (bosses): the aim a weaving shot (spec.wobble) weaves around,
        # and seconds it waits in place before flying (harmless meanwhile:
        # a contracting ring shows where it'll close first). `tint` picks a
        # color from a look's palette (psychedelic shots).
        self.base_angle = angle
        self.hold = 0.0
        self.tint = 0
        # Lobbed shells: where it comes down, and how far that is (full range
        # straight ahead unless combat.fire aims it at a point).
        self.flight = spec.max_range
        self.target: tuple[float, float] | None = (
            (x + self.dir_x * spec.max_range, y + self.dir_y * spec.max_range) if spec.lob else None)
