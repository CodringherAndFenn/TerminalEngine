"""
entities/weapon.py -- a gun's fire cadence (hold-to-fire, and bursts).

The weapon is separate from the tank so it can be swapped (weapon pickups,
choosing a starting weapon) by building a new Weapon from another
WeaponSpec in config.WEAPONS.
"""

from __future__ import annotations

from ..specs import WeaponSpec


class Weapon:
    def __init__(self, spec: WeaponSpec) -> None:
        self.spec = spec
        self.cooldown = 0.0
        self._burst_left = 0      # extra shots still to come in this burst
        self._burst_timer = 0.0

    def update(self, dt: float, trigger_held: bool) -> bool:
        """Advance the cooldown; return True if a shot fires this frame.

        While the trigger is held, trigger pulls come exactly every
        fire_interval: the cooldown is *added to* rather than reset, so the
        time a frame overshoots is carried into the next shot instead of
        lost (no drift in the cadence at any frame rate). When the trigger
        is released the cooldown bottoms out at 0 -- a fresh click fires
        immediately, but idle time never banks extra shots.

        A burst weapon fires `burst` shots per pull, `burst_gap` apart; a
        started burst always finishes, even if the trigger is let go.
        """
        self.cooldown -= dt
        if self._burst_left > 0:
            self._burst_timer -= dt
            if self._burst_timer <= 0:
                self._burst_left -= 1
                self._burst_timer += self.spec.burst_gap
                return True
            return False
        if not trigger_held:
            self.cooldown = max(self.cooldown, 0.0)
            return False
        if self.cooldown <= 0.0:
            self.cooldown += self.spec.fire_interval
            self._burst_left = self.spec.burst - 1
            self._burst_timer = self.spec.burst_gap
            return True
        return False

    @property
    def ready(self) -> bool:
        return self.cooldown <= 0.0 and self._burst_left == 0
