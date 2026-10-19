"""
players/cards.py -- the powers: what each card's effect does to a hero.

M28.1 (design/GEAR.md): the cards became gear. Offers, slots and levels
are players/gear.py now; this module keeps the effect layer under it. The
catalog (design/CARDS.md) lives as data in config.CARDS -- a piece of
gear's power is its card's mods, a plain-stat affix is a stat card's -- and
the numbers they change are players/stats.HeroStats.

Effects. After every change the hero's stats, body and weapon are rebuilt
from the base specs plus the Guild's upgrades (meta steps) plus every
(stat, op, value) step the worn gear gives (loadout_from_steps). A tiered
card counts with the rarity it was rolled at.

Gates (gate_met): what a power or affix needs before it's offered -- a
status source, a spell, an element, a stat above its base, another card.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace

from .. import config
from ..specs import CardSpec, CharacterSpec, WeaponSpec
from .stats import HeroStats, apply_mods

ROMAN = ("I", "II", "III", "IV", "V")


@dataclass
class Loadout:
    body: CharacterSpec
    weapon: WeaponSpec
    stats: HeroStats

    @property
    def regen(self) -> float:
        return self.stats.regen

    @property
    def lifesteal(self) -> float:
        return self.stats.lifesteal


def card(key: str) -> CardSpec:
    return config.CARDS[key]


def card_steps(key: str, rarity: str) -> list[tuple[str, str, float]]:
    """A card's mods with "X" filled in for the rarity it was taken at."""
    c = config.CARDS[key]
    return [(stat, op, c.value(rarity) * c.x_scale if val == "X" else val)
            for stat, op, val in c.mods]


def rarities_of(c: CardSpec) -> list[str]:
    if c.tiered:
        return [r for r, v in zip(config.RARITIES, c.tiers) if v is not None]
    return [c.rarity]


def spell_of(c: CardSpec) -> str | None:
    return next((stat for stat, op, _ in c.mods if op == "spell"), None)


def card_text(key: str, rarity: str, spells: dict | None = None) -> tuple[str, str]:
    """(title, effect line) as the card shows them. A spell card you own
    already is its next level: "Ember Aura II", and what that level adds."""
    c = config.CARDS[key]
    spell = spell_of(c)
    if spell is not None:
        s = config.SPELLS[spell]
        level = (spells or {}).get(spell, 0)
        if level == 0:
            return s.name, s.text
        name = s.name if len(s.name) <= 14 else s.short.title()   # room for " III"
        return f"{name} {ROMAN[min(level, len(ROMAN) - 1)]}", s.levels[min(level, len(s.levels)) - 1][0]
    return c.name, c.label(rarity)


# --- Who may be offered what ------------------------------------------------------------


def build_tags(weapon: WeaponSpec, stats: HeroStats) -> set[str]:
    """Every tag the build has: the weapon's, the spells', and those of the
    statuses it can inflict."""
    tags = set(weapon.tags)
    for key in stats.spells:
        tags.update(config.SPELLS[key].tags)
    if stats.has("sheet_music"):                  # the bard's notes are projectiles
        tags.add("projectile")
    for s in stats.sources:
        tags.add(config.STATUSES[s].tag)
    return tags


_ELEMENTS = {"fire", "frost", "poison", "lightning"}
_BASE = HeroStats()


def gate_met(need: str, stats: HeroStats, tags: set[str], taken: Counter,
              weapon: WeaponSpec | None = None) -> bool:
    if need == "status":
        return bool(stats.sources)
    if need == "shots":                       # pattern cards: the attack itself shoots
        return (weapon is not None and weapon.shell is not None) or stats.has("sheet_music")
    if need == "duration":                    # Lingering: something that lasts
        return bool(stats.sources) or any(k in stats.spells for k in config.DURATION_SPELLS)
    if need == "spell":
        return bool(stats.spells)
    if need == "element":
        return bool(tags & _ELEMENTS)
    if need == "heal":
        return stats.regen > 0 or stats.lifesteal > 0 or stats.soul_harvest > 0 \
            or "healing_totem" in stats.spells or stats.has("lullaby")
    if need.startswith("stat:"):
        name = need[5:]
        return getattr(stats, name) > getattr(_BASE, name)
    if need in config.CARDS:
        return taken[need] > 0
    if need in config.STATUSES:
        return need in stats.sources
    return need in tags


_BY_CODE = {c.code: k for k, c in config.CARDS.items()}
ARCHETYPE_CARDS = {name: frozenset(_BY_CODE[code] for code in codes)
                   for name, codes in config.ARCHETYPES.items()}


def leading_archetype(taken: Counter) -> str | None:
    """The archetype the build leans to: the one it holds the most cards of
    (copies and spell levels count), if that's at least ARCHETYPE_MIN."""
    best, most = None, config.ARCHETYPE_MIN - 1
    for name, keys in ARCHETYPE_CARDS.items():
        n = sum(taken[k] for k in keys)
        if n > most:
            best, most = name, n
    return best


def rarity_weights(luck: float) -> list[float]:
    """CARD_RARITY_WEIGHT with luck applied: each rarity step above common
    multiplies the weight by (1 + LUCK_STEP * luck) once more."""
    lift = max(0.0, 1 + config.LUCK_STEP * luck)
    return [config.CARD_RARITY_WEIGHT[r] * lift ** i for i, r in enumerate(config.RARITIES)]


# --- What the cards do ------------------------------------------------------------------


def hero_stats(taken: list[tuple[str, str]], meta=()) -> HeroStats:
    steps = list(meta) + [s for key, rarity in taken for s in card_steps(key, rarity)]
    return apply_mods(HeroStats(), steps)


def level_speed(level: int) -> float:
    """P3: the move speed bonus a hero's level gives (a fraction)."""
    return min(config.LEVEL_SPEED_CAP, config.LEVEL_SPEED * max(0, level - 1))


def build_loadout(hero_key: str, taken, meta=(), level: int = 1) -> Loadout:
    """The hero's stats, body and weapon with the Guild's upgrades (`meta`,
    see meta/guild.Guild.meta_steps), every card in `taken` (a list of
    (key, rarity); a Counter of keys is read as their first rarity) and
    the speed their `level` gives (P3)."""
    if isinstance(taken, Counter):
        taken = [(k, rarities_of(config.CARDS[k])[0]) for k in sorted(taken)
                 for _ in range(taken[k])]
    return loadout_from_steps(hero_key, [st for key, rarity in taken
                                         for st in card_steps(key, rarity)], meta, level)


def loadout_from_steps(hero_key: str, steps, meta=(), level: int = 1) -> Loadout:
    """build_loadout from raw (stat, op, value) steps (players/gear.py's
    Equipment.steps: the powers and affixes worn)."""
    if level_speed(level):
        meta = list(meta) + [("move", "add", level_speed(level))]
    stats = apply_mods(HeroStats(), list(meta) + list(steps))
    body = config.HEROES[hero_key]
    weapon = config.WEAPONS[body.weapon]
    shell = weapon.shell
    interval = stats.interval(weapon.fire_interval)
    # Extra projectiles widen the fan by at least MIN_PELLET_GAP each (M19).
    extra = max(0, round(stats.pellets))
    fan = max(weapon.spread_deg + stats.spread, weapon.spread_deg + config.MIN_PELLET_GAP * extra)
    spread = min(160.0, max(0.0, fan * stats.spread_mult))
    if shell is not None:
        shell = replace(
            shell,
            max_range=shell.max_range * (1 + stats.range),
            speed=shell.speed * (1 + stats.shot_speed),
            pierce=shell.pierce + (0 if shell.returns else round(stats.pierce)),
            # (Storm Caller's jumps are Chain Lightning's: only a weapon
            # that already chains gets them -- not the wizard's darts.)
            chain=shell.chain + (round(stats.chain) if shell.chain else 0),
            chain_range=shell.chain_range * (1 + stats.chain_range),
            chain_falloff=min(0.95, shell.chain_falloff + stats.chain_falloff),
            # Homing darts turn faster with Tracking, twice as fast with Seeker.
            seek_turn=shell.seek_turn * (1 + stats.seek_turn)
            * (config.SEEKER if stats.has("seeker") else 1.0))
        weapon = replace(weapon, shell=shell, fire_interval=interval,
                         pellets=weapon.pellets + round(stats.pellets), spread_deg=spread)
    else:
        # A pulse's reach grows with both range and area.
        grow = stats.range + (stats.area if weapon.kind == "pulse" else 0.0)
        weapon = replace(weapon, fire_interval=interval, reach=weapon.reach * (1 + grow))
    hp_mult = stats.max_hp_mult
    if stats.has("veteran+9"):                  # Grizzled Signet +9 (Legend)
        hp_mult *= 1 + config.LEGEND * stats.veteran_levels(level)
    body = replace(body, max_hp=max(1, round((body.max_hp + stats.max_hp) * hp_mult)),
                   max_speed=body.max_speed * (1 + stats.move))
    return Loadout(body, weapon, stats)
