"""
entities/tank.py -- the player's tank: hull driving and turret aiming.

Angles are in radians in WORLD space, measured with atan2(dy, dx) where +y
points DOWN the screen. So 0 = east, +pi/2 = south, -pi/2 = north.

The tank moves only along its hull heading (tanks don't strafe). `speed` is
signed: negative means backing up.

A Tank is built from a TankSpec (config.TANKS) and carries a swappable
Weapon, so different tank types and weapon pickups are just data.
"""

from __future__ import annotations

import math

from .. import config
from ..specs import TankSpec
from ..systems.collision import TileSource, move_hull, try_turn
from .actor import Actor
from .weapon import Weapon

# A hit counts as "on the front" when it comes from within this angle of
# the hull's heading (used for front_armor, e.g. the heavy tank).
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


def approach(value: float, target: float, accel: float, brake: float, dt: float) -> float:
    """Move `value` toward `target`, using `accel` when speeding up in the
    same direction and `brake` when slowing down or reversing."""
    speeding_up = abs(target) > abs(value) and (value == 0 or (value > 0) == (target > 0))
    step = (accel if speeding_up else brake) * dt
    if abs(target - value) <= step:
        return target
    return value + math.copysign(step, target - value)


class Tank(Actor):
    faction = "player"

    def __init__(self, spec: TankSpec, x: float, y: float, max_hp: int | None = None) -> None:
        # Hit circle: the average of the hull's half-length and half-width.
        radius = (spec.hull_length_px + spec.hull_width_px) / 4 / config.TILE_PX_W
        super().__init__(max_hp if max_hp is not None else spec.max_hp, radius)
        self.spec = spec
        self.x = x
        self.y = y
        self.hull_angle = -math.pi / 2   # start facing north
        self.turret_angle = -math.pi / 2
        self.speed = 0.0
        self.last_blocked = False
        self.weapon = Weapon(config.WEAPONS[spec.weapon])
        # Collision uses the drawn hull rectangle, in pixels.
        self.half_len = spec.hull_length_px / 2
        self.half_wid = spec.hull_width_px / 2
        # True while "direct" drive has chosen to back up rather than turn
        # around; remembered so the choice doesn't flicker frame to frame.
        self._reversing = False

    # --- Driving ---------------------------------------------------------------

    def take_damage(self, amount, source, from_angle):
        """Armor: a hit travelling *toward* the hull's front (i.e. coming
        from ahead) is scaled by the spec's front_armor."""
        if from_angle is not None and self.spec.front_armor != 1.0:
            # The hit comes *from* the opposite of its travel direction.
            came_from = from_angle + math.pi
            if abs(wrap_angle(came_from - self.hull_angle)) < FRONT_ARC:
                amount *= self.spec.front_armor
        return super().take_damage(amount, source, from_angle)

    def drive(
        self, ax: float, ay: float, dt: float, world: TileSource, mode: str | None = None,
        allow_reverse: bool = True,
    ) -> None:
        """Apply one frame of driving input (axes from input.move_axes, or
        any direction vector from the AI).

        Steering proposes a new heading; try_turn only accepts it if the
        rotated hull fits (nudging off a wall slightly if needed). Then the
        hull moves along its heading with collision. `mode` overrides
        config.DRIVE_MODE (the AI always drives "direct"). With
        allow_reverse=False, "direct" mode always turns to face the
        direction instead of backing up (heavy tanks keep their armored
        front toward the enemy).
        """
        self.last_blocked = False   # did a wall stop the hull this frame?
        if self.spec.max_speed <= 0:
            return  # emplacements don't drive
        if (mode or config.DRIVE_MODE) == "tank":
            new_angle, target_speed = self._steer_tank(ax, ay, dt)
        else:
            new_angle, target_speed = self._steer_direct(ax, ay, dt, allow_reverse)
        if new_angle != self.hull_angle:
            self.x, self.y, self.hull_angle = try_turn(
                world, self.x, self.y, self.hull_angle, new_angle, self.half_len, self.half_wid
            )

        spec = self.spec
        self.speed = approach(self.speed, target_speed, spec.accel, spec.brake, dt)
        if self.speed == 0.0:
            return

        dx = math.cos(self.hull_angle) * self.speed * dt
        dy = math.sin(self.hull_angle) * self.speed * dt
        self.x, self.y, bx, by = move_hull(
            world, self.x, self.y, self.hull_angle, self.half_len, self.half_wid, dx, dy
        )
        # Sliding along a wall keeps momentum; only a dead stop (both axes
        # that we tried to move on were blocked) kills speed.
        self.last_blocked = bx or by
        if (bx or not dx) and (by or not dy):
            self.speed = 0.0

    def _steer_tank(self, ax: int, ay: int, dt: float) -> tuple[float, float]:
        """Classic tank controls: A/D rotate, W/S throttle.
        Returns (proposed heading, target speed)."""
        angle = wrap_angle(self.hull_angle + ax * self.spec.hull_turn_speed * dt)
        if ay < 0:
            return angle, self.spec.max_speed
        if ay > 0:
            return angle, -self.spec.reverse_speed
        return angle, 0.0

    def _steer_direct(self, ax: float, ay: float, dt: float,
                      allow_reverse: bool = True) -> tuple[float, float]:
        """Direction-based controls: drive toward the held direction.

        If the wanted direction is behind the tank, it's usually faster to
        back up than to swing the hull 180 degrees, so the hull aligns its
        *rear* with the direction and reverses. A small hysteresis keeps it
        from flip-flopping when the direction is near 90 degrees off.
        Returns (proposed heading, target speed).
        """
        if ax == 0 and ay == 0:
            return self.hull_angle, 0.0
        want = math.atan2(ay, ax)
        fwd_err = wrap_angle(want - self.hull_angle)
        back_err = wrap_angle(want + math.pi - self.hull_angle)
        bias = math.radians(15)
        if not allow_reverse:
            self._reversing = False
        elif self._reversing:
            self._reversing = abs(back_err) < abs(fwd_err) + bias
        else:
            self._reversing = abs(back_err) + bias < abs(fwd_err)

        facing = want + math.pi if self._reversing else want
        angle = wrap_angle(rotate_toward(self.hull_angle, facing, self.spec.hull_turn_speed * dt))
        # Throttle scales with how well the hull lines up: full speed when
        # aligned, easing off while turning, nothing if way off.
        err = abs(wrap_angle(facing - angle))
        if err > config.DIRECT_MAX_DRIVE_ERROR:
            return angle, 0.0
        top = -self.spec.reverse_speed if self._reversing else self.spec.max_speed
        return angle, top * math.cos(err)

    # --- Aiming ------------------------------------------------------------------

    def aim_at(self, wx: float, wy: float, dt: float) -> None:
        """Point the turret at world point (wx, wy).

        Uses the true angle, not an 8-way snap: shells will travel exactly
        along turret_angle.
        """
        if wx == self.x and wy == self.y:
            return
        self.aim_angle_toward(math.atan2(wy - self.y, wx - self.x), dt)

    def aim_angle_toward(self, target: float, dt: float) -> None:
        """Turn the turret toward a world angle at the spec's traverse speed
        (instantly if it's 0, as for the player)."""
        speed = self.spec.turret_turn_speed
        if speed <= 0:
            self.turret_angle = target
        else:
            self.turret_angle = wrap_angle(rotate_toward(self.turret_angle, target, speed * dt))

    def turret_on_target(self, target: float, tolerance: float) -> bool:
        return abs(wrap_angle(target - self.turret_angle)) <= tolerance

    @property
    def hull_dir8(self) -> int:
        """Hull heading snapped to 8 directions: 0=E, 1=SE, 2=S, ... 7=NE."""
        return round(self.hull_angle / (math.pi / 4)) % 8
