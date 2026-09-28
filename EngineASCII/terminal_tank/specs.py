"""
specs.py -- data definitions for tanks, weapons and shells.

These are plain, immutable records; the actual values live in config.py
(TANKS / WEAPONS registries) so balance stays in one file. Keeping tanks and
guns as data is what lets later milestones add tank selection, weapon
pickups and unlockable starting weapons without touching game logic: a
pickup just swaps the tank's Weapon for one built from another WeaponSpec.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ShellSpec:
    speed: float            # tiles/s
    damage: int             # hit points removed from a tile (later: enemies)
    max_range: float        # tiles travelled before the shell fizzles out
    length_px: int = 9      # drawn size of the shell
    width_px: int = 4


@dataclass(frozen=True)
class WeaponSpec:
    name: str
    fire_interval: float    # seconds between shots while the button is held
    shell: ShellSpec


@dataclass(frozen=True)
class TankSpec:
    name: str
    weapon: str             # key into config.WEAPONS: the starting gun
    max_speed: float        # tiles/s forward
    reverse_speed: float    # tiles/s backing up
    accel: float            # tiles/s^2 speeding up
    brake: float            # tiles/s^2 slowing down / no input
    hull_turn_speed: float  # rad/s
    # Drawn (and collision) size, in canvas pixels (1 tile = 20 x 24 px).
    hull_length_px: int
    hull_width_px: int
    turret_radius_px: int
    barrel_length_px: int
    barrel_width_px: int
