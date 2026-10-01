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
    lob: bool = False       # lobbed: flies over everything to a target point, then bursts
    blast_radius: float = 0.0       # lobbed shells: burst radius, tiles
    returns: bool = False   # boomerang (the dwarf's axes): flies out to max_range, then
                            # back to the thrower; passes through every enemy, hitting
                            # each once per leg


@dataclass(frozen=True)
class WeaponSpec:
    """How an attack works. `kind`:
      * "shot"  -- fires `pellets` projectiles (ShellSpec), fanned over
                   `spread_deg` (bolts, arrows, the rainbow's colors);
      * "melee" -- a swing hitting everything within `reach` tiles and
                   `arc_deg` of the aim (a sword; no hero uses one now);
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
    tags: tuple[str, ...] = ()      # projectile / area / physical / lightning / arcane...

    @property
    def aims(self) -> bool:
        """False for attacks that go all round (pulses): no reticle."""
        return self.kind != "pulse"


@dataclass(frozen=True)
class CardSpec:
    """A level-up card (players/cards.py; the catalog: design/CARDS.md).

    `mods` are (stat, op, value) steps applied once per copy taken:
      op "add" / "mul"  -- add to / multiply a stat of players/stats.HeroStats;
      op "flag"         -- a rule-changing effect (stat = its name, value = 1);
      op "status"       -- adds a status to those your hits can inflict
                           (stat = the status, see config.STATUSES);
      op "source"       -- the card itself inflicts that status (so status
                           payoff cards become available), without adding
                           it to your on-hit list;
      op "spell"        -- grants the spell (stat = key into config.SPELLS),
                           or levels it up if already owned.
    A value of "X" means the card's tier value (`tiers`) times `x_scale`.

    Rarity: a fixed `rarity`, or `tiers` -- a tiered card rolls a rarity
    each time it's offered and its number grows with it; `tiers` holds the
    value for each of config.RARITIES, None where the card can't appear.
    `heroes` / `kinds` limit who can be offered it (empty = anyone);
    `needs` gates it: "status" (you inflict some status), "spell" (you own
    a spell), "element" (any of fire / frost / poison / lightning), "heal"
    (you have some healing), "stat:<name>" (that stat above its base), a
    card key (you took it), or a tag / status name you must have. Every
    entry must hold. `tags` drive the
    "x1.5 when it shares a tag with your build" offer weighting. `unlock`
    is "start", "L:<loot>" (bought in the Guild Hall's archive) or
    "A:<achievement>"; locked cards are never offered."""

    name: str
    text: str                        # one short line on the card; "{X}" = the tier value
    mods: tuple[tuple[str, str, object], ...]
    rarity: str = "common"
    max_stacks: int = 3              # copies one hero can take
    heroes: tuple[str, ...] = ()     # only for these heroes
    kinds: tuple[str, ...] = ()      # only for these weapon kinds (shot / melee / pulse)
    tiers: tuple | None = None       # tiered cards: value per rarity (None: not at that rarity)
    x_scale: float = 0.01            # tier value -> stat units (percent by default)
    needs: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    unlock: str = "start"
    code: str = ""                   # catalog number (G01, W3...)
    min_level: int = 0               # offered from this level on (capstones)

    @property
    def tiered(self) -> bool:
        return self.tiers is not None

    def value(self, rarity: str) -> float:
        """The tier value at `rarity` (tiered cards)."""
        from .config import RARITIES
        return self.tiers[RARITIES.index(rarity)]

    def label(self, rarity: str) -> str:
        """The card's text with its number filled in for `rarity`."""
        if not self.tiered:
            return self.text
        v = self.value(rarity)
        return self.text.replace("{X}", f"{v:g}")


@dataclass(frozen=True)
class SpellSpec:
    """A spell or item granted by a card (systems/spells.py). `kind` picks
    the behaviour (orbit / aura / nova); `base` holds its level-1 numbers
    and `levels` the change each further level makes, as (field, op,
    value) on those numbers plus the line the level-up card shows."""

    name: str
    short: str                        # HUD label
    kind: str
    tags: tuple[str, ...]
    base: dict
    levels: tuple[tuple[str, tuple[tuple[str, str, float], ...]], ...]
    rarity: str = "uncommon"
    text: str = ""                    # the first card's text


@dataclass(frozen=True)
class UpgradeSpec:
    """A Guild Hall upgrade (meta/guild.py), bought with loot between runs.
    Each level adds `mods` once more (same (stat, op, value) steps as a
    card, see CardSpec); level n+1 costs base_cost x growth ** n."""

    name: str
    text: str                        # what one level does
    mods: tuple[tuple[str, str, float], ...]
    max_level: int = 5
    base_cost: int = 100
    growth: float = 1.6

    def cost(self, level: int) -> int:
        """Price of the next level when `level` are owned."""
        return round(self.base_cost * self.growth ** level)


@dataclass(frozen=True)
class PactSpec:
    """A pact (the archivist sells it, the dungeon gate switches it on):
    the run gets harder in the ways given, and pays `loot` more."""

    name: str
    text: str
    loot: float                      # +loot fraction while it's on
    price: int
    enemy_damage: float = 0.0        # +fraction
    enemy_count: float = 0.0         # +fraction of enemies
    enemy_haste: float = 0.0         # +fraction faster (move and attack)
    enemy_levels: int = 0            # enemies wake this many levels tougher
    hero_hp: float = 0.0             # +fraction of your max HP (negative: less)
    famine: bool = False             # no regeneration; skip doesn't heal


@dataclass(frozen=True)
class StatusSpec:
    """A status effect enemies can suffer (systems/statuses.py)."""

    name: str
    tag: str                 # fire / poison / frost / lightning / physical
    duration: float          # seconds; a new stack refreshes it
    max_stacks: int = 1
    dps: float = 0.0         # damage per second per stack (bucket S)
    slow: float = 0.0        # chill: move/attack speed lost per stack
    vulnerability: float = 0.0   # shock: extra damage taken from everything


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
