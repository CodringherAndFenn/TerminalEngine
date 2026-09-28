"""
entities/projectile.py -- shells in flight.

A shell flies in a straight line along the turret's true aim angle at its
ShellSpec speed, until it hits something that blocks shots or has travelled
its max range. Hit detection lives in systems/combat.py.
"""

from __future__ import annotations

import math

from ..specs import ShellSpec


class Projectile:
    def __init__(self, x: float, y: float, angle: float, spec: ShellSpec) -> None:
        self.x = x
        self.y = y
        self.angle = angle            # world radians
        self.spec = spec
        self.dir_x = math.cos(angle)  # unit direction, world tiles
        self.dir_y = math.sin(angle)
        self.travelled = 0.0          # tiles
        self.alive = True
