"""
specs.py -- data definitions for tanks, weapons, shells and enemies.

These are plain, immutable records; the actual values live in config.py
(TANKS / WEAPONS / ENEMIES registries) so balance stays in one file. Keeping
tanks, guns and enemies as data is what lets later milestones add tank
selection, weapon pickups, unlockable starting weapons and new enemy types
without touching game logic.

Damage and hit points share one scale everywhere: a shell's `damage` comes
off an enemy's, the player's or a destructible tile's hit points alike.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ShellSpec:
    speed: float            # tiles/s
    damage: int             # hit points removed from whatever it hits
    max_range: float        # tiles travelled before the shell fizzles out
    damages_terrain: bool = True   # False: explodes on walls/trees harmlessly
    length_px: int = 9      # drawn size of the shell
    width_px: int = 4


@dataclass(frozen=True)
class WeaponSpec:
    name: str
    fire_interval: float    # seconds between shots (hold to fire / AI cadence)
    shell: ShellSpec
    burst: int = 1          # shots per trigger pull (turrets fire bursts)
    burst_gap: float = 0.12 # seconds between shots within a burst


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
    max_hp: int = 100
    turret_turn_speed: float = 0.0  # rad/s; 0 = turret snaps to its aim instantly
    colors: str = "player"          # key into palette.TANK_COLORS
    hull_style: str = "tank"        # "tank" (treads) or "bunker" (fixed emplacement)
    front_armor: float = 1.0        # damage multiplier for hits on the front arc


@dataclass(frozen=True)
class EnemySpec:
    """One enemy type. `kind` picks the behaviour (ai/*.py); vehicles
    (tankette, sniper, heavy, turret) drive a TankSpec, creatures use the
    creature fields."""

    name: str
    kind: str                       # tankette|sniper|heavy|turret|burrower|puffer|warrior
    max_hp: int
    sight: float                    # tiles: how far it can see you
    biomes: tuple[str, ...]         # where it spawns
    weight: int = 1                 # relative spawn chance within those biomes
    min_difficulty: float = 0.0     # doesn't spawn closer to the start than this
    tank: str | None = None         # vehicles: key into config.TANKS
    preferred_range: tuple[float, float] = (6.0, 10.0)   # tiles to keep from target
    speed: float = 4.0              # creatures: tiles/s
    damage: int = 10                # creatures: damage of their attack
    attack_radius: float = 1.5      # creatures: reach / blast radius, tiles
    windup: float = 0.5             # creatures/sniper: telegraph time before attacking
    cooldown: float = 1.5           # creatures: time between attacks
    size_px: int = 16               # creatures: body size (collision + drawing)
