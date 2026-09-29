"""
specs.py -- data definitions for characters, weapons, shots and enemies.

These are plain, immutable records; the actual values live in config.py
(HEROES / BODIES / WEAPONS / ENEMIES registries) so balance stays in one
file. Keeping heroes, weapons and enemies as data is what lets later
milestones add hero selection, weapon pickups, unlockable starting weapons
and new enemy types without touching game logic.

Damage and hit points share one scale everywhere: a shot's `damage` comes
off an enemy's, the player's or a destructible tile's hit points alike.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ShellSpec:
    """A projectile: anything fired (spell bolts, arrows, thrown rocks)."""

    speed: float            # tiles/s
    damage: int             # hit points removed from whatever it hits
    max_range: float        # tiles travelled before it falls to the ground
    damages_terrain: bool = True   # False: bursts on walls/trees harmlessly
    look: str = "bolt"      # how it's drawn: key into render/ascii_fx.SHOT_LOOKS


@dataclass(frozen=True)
class WeaponSpec:
    name: str
    fire_interval: float    # seconds between shots (hold to fire / AI cadence)
    shell: ShellSpec
    burst: int = 1          # shots per trigger pull (spell towers fire bursts)
    burst_gap: float = 0.12 # seconds between shots within a burst


@dataclass(frozen=True)
class CharacterSpec:
    """A body that walks and fires a weapon: every hero, and the enemies
    that shoot (goblin archer, warlock, ogre, spell tower)."""

    name: str
    weapon: str             # key into config.WEAPONS: the starting weapon
    sprite: str             # key into render/characters.ART
    max_speed: float        # tiles/s (0 = never moves, e.g. a tower)
    accel: float            # tiles/s^2 speeding up
    brake: float            # tiles/s^2 slowing down / no input
    size_px: int            # collision box (square), canvas px (1 tile = 20 x 24)
    max_hp: int = 100
    sprite_scale: int = 3   # screen px per sprite pixel
    aim_turn_speed: float = 0.0     # rad/s; 0 = aims instantly (the player)
    front_armor: float = 1.0        # damage multiplier for hits on the side it faces
    hold_px: int = 18       # shots leave this far from the centre, toward the aim


@dataclass(frozen=True)
class EnemySpec:
    """One enemy type. `kind` picks the behaviour (ai/*.py); shooters
    (archer, warlock, ogre, tower) have a CharacterSpec body, creatures use
    the creature fields."""

    name: str
    kind: str                       # archer|warlock|ogre|tower|burrower|puffer|warrior
    max_hp: int
    sight: float                    # tiles: how far it can see you
    biomes: tuple[str, ...]         # where it spawns
    weight: int = 1                 # relative spawn chance within those biomes
    body: str | None = None         # shooters: key into config.BODIES
    preferred_range: tuple[float, float] = (6.0, 10.0)   # tiles to keep from target
    speed: float = 4.0              # creatures: tiles/s
    damage: int = 10                # creatures: damage of their attack
    attack_radius: float = 1.5      # creatures: reach / blast radius, tiles
    windup: float = 0.5             # creatures/warlock: telegraph time before attacking
    cooldown: float = 1.5           # creatures: time between attacks
    size_px: int = 16               # creatures: body size (collision + drawing)
