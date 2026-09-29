"""
entities/character.py -- a walking body with a weapon: the hero, and the
enemies that shoot (goblin archer, warlock, ogre, spell tower).

Movement is free in 8 directions: the input (or the AI) gives a direction,
and the velocity eases toward direction * max_speed at `accel` (or down to
zero at `brake` when there's no input). Collision is a square box of
`size_px` against the tile grid, resolved one axis at a time so walking
diagonally into a wall slides along it (systems/collision.py).

Aiming is separate from walking: `aim_angle` is where the weapon points
(the hero: straight at the mouse; enemies turn it at `aim_turn_speed`).
Characters face left or right toward their aim -- that's how the sprite is
drawn.

Angles are in radians in WORLD space, measured with atan2(dy, dx) where +y
points DOWN the screen. So 0 = east, +pi/2 = south, -pi/2 = north.
"""

from __future__ import annotations

import math

from .. import config
from ..specs import CharacterSpec
from ..systems.collision import TileSource, move_hull
from .actor import Actor
from .weapon import Weapon

# A hit counts as "on the front" when it comes from within this angle of
# where the character faces (its aim) -- used for front_armor (the ogre).
FRONT_ARC = math.radians(55)

TAU = 2 * math.pi


def wrap_angle(a: float) -> float:
    """Wrap an angle to (-pi, pi]."""
    a = math.fmod(a + math.pi, TAU)
    if a <= 0:
        a += TAU
    return a - math.pi


def rotate_toward(current: float, target: float, max_step: float) -> float:
    """Turn `current` toward `target` by at most `max_step`, the short way."""
    err = wrap_angle(target - current)
    if abs(err) <= max_step:
        return target
    return current + math.copysign(max_step, err)


def _approach(v: float, target: float, rate: float) -> float:
    if abs(target - v) <= rate:
        return target
    return v + math.copysign(rate, target - v)


class Character(Actor):
    faction = "player"

    def __init__(self, spec: CharacterSpec, x: float, y: float, max_hp: int | None = None) -> None:
        # Hit circle: a bit bigger than half the box, in tiles.
        super().__init__(max_hp if max_hp is not None else spec.max_hp,
                         spec.size_px / 2 / config.TILE_PX_W + 0.15)
        self.spec = spec
        self.x, self.y = x, y
        self.vx = self.vy = 0.0          # tiles/s (enemies lead their shots with this)
        self.aim_angle = 0.0
        self.heading = 0.0               # direction of the last movement
        self.walked = 0.0                # tiles walked in total (walk animation)
        self.last_blocked = False
        self.half = spec.size_px / 2     # collision half-size, px
        self.weapon = Weapon(config.WEAPONS[spec.weapon])

    @property
    def facing_left(self) -> bool:
        return math.cos(self.aim_angle) < 0

    @property
    def speed(self) -> float:
        return math.hypot(self.vx, self.vy)

    # --- Damage ------------------------------------------------------------------------

    def take_damage(self, amount, source, from_angle):
        """Armor: a hit coming from the side the character faces (its aim)
        is scaled by the spec's front_armor."""
        if from_angle is not None and self.spec.front_armor != 1.0:
            came_from = from_angle + math.pi     # a hit comes *from* opposite its travel
            if abs(wrap_angle(came_from - self.aim_angle)) < FRONT_ARC:
                amount *= self.spec.front_armor
        return super().take_damage(amount, source, from_angle)

    # --- Moving -------------------------------------------------------------------------

    def move(self, ax: float, ay: float, dt: float, world: TileSource) -> None:
        """One frame of walking toward direction (ax, ay) (any length; zero
        = stop), with collision."""
        self.last_blocked = False
        spec = self.spec
        if spec.max_speed <= 0:
            return   # towers don't walk
        n = math.hypot(ax, ay)
        if n > 0:
            tx, ty = ax / n * spec.max_speed, ay / n * spec.max_speed
            rate = spec.accel * dt
        else:
            tx = ty = 0.0
            rate = spec.brake * dt
        self.vx = _approach(self.vx, tx, rate)
        self.vy = _approach(self.vy, ty, rate)
        if self.vx == 0.0 and self.vy == 0.0:
            return
        dx, dy = self.vx * dt, self.vy * dt
        x0, y0 = self.x, self.y
        self.x, self.y, bx, by = move_hull(world, self.x, self.y, 0.0, self.half, self.half, dx, dy)
        if bx:
            self.vx = 0.0
        if by:
            self.vy = 0.0
        self.last_blocked = bx or by
        moved = math.hypot(self.x - x0, self.y - y0)
        if moved > 1e-9:
            self.heading = math.atan2(self.y - y0, self.x - x0)
            self.walked += moved

    # --- Aiming ---------------------------------------------------------------------------

    def aim_at(self, wx: float, wy: float, dt: float) -> None:
        """Point the weapon at world point (wx, wy): the true angle, so shots
        travel exactly through it."""
        if wx == self.x and wy == self.y:
            return
        self.aim_angle_toward(math.atan2(wy - self.y, wx - self.x), dt)

    def aim_angle_toward(self, target: float, dt: float) -> None:
        """Turn the aim toward a world angle at the spec's speed (instantly
        if it's 0, as for the player)."""
        speed = self.spec.aim_turn_speed
        if speed <= 0:
            self.aim_angle = target
        else:
            self.aim_angle = wrap_angle(rotate_toward(self.aim_angle, target, speed * dt))

    def aim_on_target(self, target: float, tolerance: float) -> bool:
        return abs(wrap_angle(target - self.aim_angle)) <= tolerance
