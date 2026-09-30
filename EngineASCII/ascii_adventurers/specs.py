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
    sound: str = "bolt"     # played when fired: key into engine_ext/sfx.py recipes
    pierce: int = 0         # enemies it passes through before stopping (arrows)
    chain: int = 0          # jumps to further enemies after a hit (lightning)
    chain_range: float = 0.0        # tiles a jump can reach (needs a clear line)
    chain_falloff: float = 0.7      # each jump does this fraction of the previous


@dataclass(frozen=True)
class WeaponSpec:
    """How an attack works. `kind`:
      * "shot"  -- fires `pellets` projectiles (ShellSpec), fanned over
                   `spread_deg` (bolts, arrows, the rainbow's colors);
      * "melee" -- a swing hitting everything within `reach` tiles and
                   `arc_deg` of the aim (the knight's sword);
      * "pulse" -- a burst hitting everything within `reach` tiles all
                   around (the bard's music).
    `auto` weapons fire on their own, without the trigger."""

    name: str
    fire_interval: float    # seconds between attacks (hold to fire / AI cadence)
    shell: ShellSpec | None = None  # "shot" weapons
    burst: int = 1          # shots per trigger pull (spell towers fire bursts)
    burst_gap: float = 0.12 # seconds between shots within a burst
    kind: str = "shot"
    pellets: int = 1        # projectiles per shot
    spread_deg: float = 0.0 # total fan width of the pellets
    damage: int = 0         # "melee"/"pulse" damage (shots use shell.damage)
    reach: float = 0.0      # "melee"/"pulse" radius, tiles
    arc_deg: float = 0.0    # "melee" swing width
    auto: bool = False      # fires by itself on the beat (no trigger)
    blurb: str = ""         # one line for the hero select screen

    @property
    def aims(self) -> bool:
        """False for attacks that go all round (pulses): no reticle."""
        return self.kind != "pulse"


@dataclass(frozen=True)
class CardSpec:
    """A level-up card. `mods` are (stat, op, value) steps applied once per
    copy taken, op "add" or "mul" (see players/cards.py for the stats).
    `heroes` / `kinds` limit who can be offered it (empty = anyone)."""

    name: str
    text: str                        # one short line on the card
    mods: tuple[tuple[str, str, float], ...]
    rarity: str = "common"           # common | rare | epic (how often it's offered)
    max_stacks: int = 3              # copies one hero can take
    heroes: tuple[str, ...] = ()     # only for these heroes
    kinds: tuple[str, ...] = ()      # only for these weapon kinds (shot / melee / pulse)


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
    xp: int = 5                     # experience for the player who kills it
