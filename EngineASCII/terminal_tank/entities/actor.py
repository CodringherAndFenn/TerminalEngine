"""
entities/actor.py -- anything with hit points that shells and blasts can hurt.

The player's tank and every enemy are Actors, so combat treats them alike:
shells test `hit_radius` circles, blasts check distance, and friendly fire
falls out naturally -- a shell hurts whichever actor it reaches first,
except the one that fired it.
"""

from __future__ import annotations


class Actor:
    faction = "neutral"   # "player" or "enemy"

    def __init__(self, max_hp: int, hit_radius: float) -> None:
        self.max_hp = max_hp
        self.hp = float(max_hp)
        self.hit_radius = hit_radius      # tiles
        self.x = 0.0
        self.y = 0.0
        self.hurt_flash = 0.0             # seconds left of the "just got hit" blink

    @property
    def alive(self) -> bool:
        return self.hp > 0

    @property
    def hittable(self) -> bool:
        """False while an actor can't be hit (e.g. a burrower underground)."""
        return self.alive

    def take_damage(self, amount: float, source: "Actor | None", from_angle: float | None) -> float:
        """Apply damage; returns the amount actually dealt. `from_angle` is
        the world direction the hit travelled in (None for blasts)."""
        if not self.alive:
            return 0.0
        self.hp = max(0.0, self.hp - amount)
        self.hurt_flash = 0.12
        return amount

    def tick_flash(self, dt: float) -> None:
        self.hurt_flash = max(0.0, self.hurt_flash - dt)
