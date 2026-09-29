"""
entities/effects.py -- short-lived visual effects (muzzle flash, impacts,
damage numbers...).

An effect is just a kind, a position and a timer; render/ascii_fx.py turns
(kind, progress) into an animation frame of font glyphs. They never affect
gameplay.
"""

from __future__ import annotations

from dataclasses import dataclass

from .. import config

# kind -> lifetime in seconds
DURATIONS = {
    "muzzle": config.MUZZLE_FLASH_TIME,
    "impact": config.IMPACT_TIME,
    "debris": config.IMPACT_TIME * 1.5,
    "fizzle": config.FIZZLE_TIME,
    "tile_flash": config.TILE_FLASH_TIME,
    # Milestone 4
    "explosion": 0.55,      # an enemy or the hero destroyed
    "slash": 0.18,          # fallen warrior's blade swing
    "number": config.NUMBER_TIME,   # floating damage number
    "spores": 0.6,          # spore puffer burst
    "eruption": 0.45,       # burrower bursting out of the sand
    "burrow": 0.5,          # dust kicked up by a burrower underground
}


@dataclass
class Effect:
    kind: str
    x: float                # world position (tile coords for tile_flash)
    y: float
    angle: float = 0.0      # world radians, for directional effects
    t: float = 0.0          # age, seconds
    value: int = 0          # "number": the damage shown
    player: bool = False    # "number": the hero got hurt (drawn in red)

    @property
    def duration(self) -> float:
        return DURATIONS[self.kind]

    @property
    def progress(self) -> float:
        """0 at spawn -> 1 at expiry."""
        return min(1.0, self.t / self.duration)


def update_effects(effects: list[Effect], dt: float) -> None:
    """Age every effect and drop the expired ones (in place)."""
    for e in effects:
        e.t += dt
    effects[:] = [e for e in effects if e.t < e.duration]
