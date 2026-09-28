"""
entities/tank.py -- the player's tank: hull driving and turret aiming.

Angles are in radians in WORLD space, measured with atan2(dy, dx) where +y
points DOWN the screen. So 0 = east, +pi/2 = south, -pi/2 = north.

The tank moves only along its hull heading (tanks don't strafe). `speed` is
signed: negative means backing up.
"""

from __future__ import annotations

import math

from .. import config
from ..systems.collision import TileSource, move_box

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


class Tank:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y
        self.hull_angle = -math.pi / 2   # start facing north
        self.turret_angle = -math.pi / 2
        self.speed = 0.0
        self.half_w = config.TANK_HALF_W
        self.half_h = config.TANK_HALF_H
        # True while "direct" drive has chosen to back up rather than turn
        # around; remembered so the choice doesn't flicker frame to frame.
        self._reversing = False

    # --- Driving ---------------------------------------------------------------

    def drive(self, ax: int, ay: int, dt: float, world: TileSource) -> None:
        """Apply one frame of driving input (axes from input.move_axes)."""
        if config.DRIVE_MODE == "tank":
            target_speed = self._steer_tank(ax, ay, dt)
        else:
            target_speed = self._steer_direct(ax, ay, dt)

        self.speed = approach(self.speed, target_speed, config.TANK_ACCEL, config.TANK_BRAKE, dt)
        if self.speed == 0.0:
            return

        dx = math.cos(self.hull_angle) * self.speed * dt
        dy = math.sin(self.hull_angle) * self.speed * dt
        self.x, self.y, bx, by = move_box(world, self.x, self.y, self.half_w, self.half_h, dx, dy)
        # Sliding along a wall keeps momentum; only a dead stop (both axes
        # that we tried to move on were blocked) kills speed.
        if (bx or not dx) and (by or not dy):
            self.speed = 0.0

    def _steer_tank(self, ax: int, ay: int, dt: float) -> float:
        """Classic tank controls: A/D rotate, W/S throttle."""
        self.hull_angle = wrap_angle(self.hull_angle + ax * config.HULL_TURN_SPEED * dt)
        if ay < 0:
            return config.TANK_MAX_SPEED
        if ay > 0:
            return -config.TANK_REVERSE_SPEED
        return 0.0

    def _steer_direct(self, ax: int, ay: int, dt: float) -> float:
        """Direction-based controls: drive toward the held direction.

        If the wanted direction is behind the tank, it's usually faster to
        back up than to swing the hull 180 degrees, so the hull aligns its
        *rear* with the direction and reverses. A small hysteresis keeps it
        from flip-flopping when the direction is near 90 degrees off.
        """
        if ax == 0 and ay == 0:
            return 0.0
        want = math.atan2(ay, ax)
        fwd_err = wrap_angle(want - self.hull_angle)
        back_err = wrap_angle(want + math.pi - self.hull_angle)
        bias = math.radians(15)
        if self._reversing:
            self._reversing = abs(back_err) < abs(fwd_err) + bias
        else:
            self._reversing = abs(back_err) + bias < abs(fwd_err)

        facing = want + math.pi if self._reversing else want
        self.hull_angle = wrap_angle(
            rotate_toward(self.hull_angle, facing, config.HULL_TURN_SPEED * dt)
        )
        # Throttle scales with how well the hull lines up: full speed when
        # aligned, easing off while turning, nothing if way off.
        err = abs(wrap_angle(facing - self.hull_angle))
        if err > config.DIRECT_MAX_DRIVE_ERROR:
            return 0.0
        top = -config.TANK_REVERSE_SPEED if self._reversing else config.TANK_MAX_SPEED
        return top * math.cos(err)

    # --- Aiming ------------------------------------------------------------------

    def aim_at(self, wx: float, wy: float, dt: float) -> None:
        """Point the turret at world point (wx, wy).

        Uses the true angle, not an 8-way snap: shells will travel exactly
        along turret_angle.
        """
        if wx == self.x and wy == self.y:
            return
        target = math.atan2(wy - self.y, wx - self.x)
        if config.TURRET_TURN_SPEED <= 0:
            self.turret_angle = target
        else:
            self.turret_angle = wrap_angle(
                rotate_toward(self.turret_angle, target, config.TURRET_TURN_SPEED * dt)
            )

    @property
    def hull_dir8(self) -> int:
        """Hull heading snapped to 8 directions: 0=E, 1=SE, 2=S, ... 7=NE."""
        return round(self.hull_angle / (math.pi / 4)) % 8
