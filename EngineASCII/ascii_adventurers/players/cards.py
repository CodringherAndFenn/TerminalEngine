"""
players/cards.py -- level-up cards: what's offered, and what taking one does.

The catalog (design/CARDS.md) lives as data in config.CARDS; the numbers
cards change are players/stats.HeroStats.

Offers. When a player has a card pick banked (players/progress.py) and no
offer on the table, CARD_OFFER_SIZE different cards are drawn. Each slot:
  1. rolls a rarity: CARD_RARITY_WEIGHT, with luck shifting weight upward
     (rarity_weights);
  2. picks a card that can appear at that rarity -- a tiered card at any
     rarity it has a value for, a fixed card only at its own -- weighted
     x CARD_SYNERGY_WEIGHT if it shares a tag with the build. No card at
     that rarity: the nearest rarity below that has one (then above).
Only cards the hero may take are drawn (eligible): unlocked (meta/guild),
their hero / weapon kind, not maxed out or banished, their gate met (a status payoff needs a
status source, a spell level-up needs the spell, a new spell needs a free
slot). The draw is seeded from the island seed, the player's slot and how
many offers they've had, so a run replays the same way (and every machine
in online co-op agrees). A reroll is simply the next draw.

Effects. After every pick the hero's stats, body and weapon are rebuilt
from the base specs plus the Guild's upgrades (meta steps) plus every
card taken (build_loadout). A tiered card counts with the rarity it was
taken at.
"""

from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass, replace

from .. import config
from ..specs import CardSpec, CharacterSpec, WeaponSpec
from ..world.rng import hash_coords
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
        return f"{name} {ROMAN[level]}", s.levels[level - 1][0]
    return c.name, c.label(rarity)


# --- Who may be offered what ------------------------------------------------------------


def build_tags(weapon: WeaponSpec, stats: HeroStats) -> set[str]:
    """Every tag the build has: the weapon's, the spells', and those of the
    statuses it can inflict."""
    tags = set(weapon.tags)
    for key in stats.spells:
        tags.update(config.SPELLS[key].tags)
    for s in stats.sources:
        tags.add(config.STATUSES[s].tag)
    return tags


def _gate_met(need: str, stats: HeroStats, tags: set[str]) -> bool:
    if need == "status":
        return bool(stats.sources)
    if need == "spell":
        return bool(stats.spells)
    if need in config.STATUSES:
        return need in stats.sources
    return need in tags


def eligible(hero_key: str, weapon: WeaponSpec, taken: Counter, stats: HeroStats | None = None,
             banished=(), unlocked: set | None = None) -> list[str]:
    """Card keys the hero may be offered. `unlocked`: the cards the player
    has (meta/guild.Guild.unlocked_cards); None skips that check (tools,
    tests)."""
    stats = stats if stats is not None else HeroStats()
    tags = build_tags(weapon, stats)
    out = []
    for key, c in config.CARDS.items():
        if taken[key] >= c.max_stacks or key in banished:
            continue
        if c.heroes and hero_key not in c.heroes:
            continue
        if c.kinds and weapon.kind not in c.kinds:
            continue
        if unlocked is not None and key not in unlocked:
            continue
        if not all(_gate_met(n, stats, tags) for n in c.needs):
            continue
        spell = spell_of(c)
        if spell is not None and spell not in stats.spells \
                and len(stats.spells) >= stats.spell_slots:
            continue
        out.append(key)
    return out


def rarity_weights(luck: float) -> list[float]:
    """CARD_RARITY_WEIGHT with luck applied: each rarity step above common
    multiplies the weight by (1 + LUCK_STEP * luck) once more."""
    lift = max(0.0, 1 + config.LUCK_STEP * luck)
    return [config.CARD_RARITY_WEIGHT[r] * lift ** i for i, r in enumerate(config.RARITIES)]


def draw_offer(hero_key: str, weapon: WeaponSpec, taken: Counter, seed: int,
               player_index: int, draw_no: int, stats: HeroStats | None = None,
               banished=(), unlocked: set | None = None) -> list[tuple[str, str]]:
    """Up to CARD_OFFER_SIZE different (card key, rarity) pairs."""
    stats = stats if stats is not None else HeroStats()
    rng = random.Random(hash_coords(seed or 0, 0xCA7D, player_index, draw_no))
    pool = eligible(hero_key, weapon, taken, stats, banished, unlocked)
    tags = build_tags(weapon, stats)
    weights = rarity_weights(stats.luck)
    n_rar = len(config.RARITIES)
    offer: list[tuple[str, str]] = []
    while pool and len(offer) < config.CARD_OFFER_SIZE:
        rolled = rng.choices(range(n_rar), weights)[0]
        # The rolled rarity, then lower ones, then higher ones.
        order = list(range(rolled, -1, -1)) + list(range(rolled + 1, n_rar))
        for i in order:
            rarity = config.RARITIES[i]
            cands = [k for k in pool if rarity in rarities_of(config.CARDS[k])]
            if cands:
                break
        w = [config.CARD_SYNERGY_WEIGHT if tags & set(config.CARDS[k].tags) else 1.0
             for k in cands]
        pick = rng.choices(cands, w)[0]
        offer.append((pick, rarity))
        pool.remove(pick)
    return offer


# --- What the cards do ------------------------------------------------------------------


def hero_stats(taken: list[tuple[str, str]], meta=()) -> HeroStats:
    steps = list(meta) + [s for key, rarity in taken for s in card_steps(key, rarity)]
    return apply_mods(HeroStats(), steps)


def build_loadout(hero_key: str, taken, meta=()) -> Loadout:
    """The hero's stats, body and weapon with the Guild's upgrades (`meta`,
    see meta/guild.Guild.meta_steps) and every card in `taken` (a list of
    (key, rarity); a Counter of keys is read as their first rarity)."""
    if isinstance(taken, Counter):
        taken = [(k, rarities_of(config.CARDS[k])[0]) for k in sorted(taken)
                 for _ in range(taken[k])]
    stats = hero_stats(taken, meta)
    body = config.HEROES[hero_key]
    weapon = config.WEAPONS[body.weapon]
    shell = weapon.shell
    interval = stats.interval(weapon.fire_interval)
    spread = min(160.0, max(0.0, (weapon.spread_deg + stats.spread) * stats.spread_mult))
    if shell is not None:
        shell = replace(
            shell,
            max_range=shell.max_range * (1 + stats.range),
            speed=shell.speed * (1 + stats.shot_speed),
            pierce=shell.pierce + (0 if shell.returns else round(stats.pierce)),
            chain=shell.chain + round(stats.chain),
            chain_range=shell.chain_range * (1 + stats.chain_range),
            chain_falloff=min(0.95, shell.chain_falloff + stats.chain_falloff))
        weapon = replace(weapon, shell=shell, fire_interval=interval,
                         pellets=weapon.pellets + round(stats.pellets), spread_deg=spread)
    else:
        # A pulse's reach grows with both range and area.
        grow = stats.range + (stats.area if weapon.kind == "pulse" else 0.0)
        weapon = replace(weapon, fire_interval=interval, reach=weapon.reach * (1 + grow))
    body = replace(body, max_hp=round(body.max_hp + stats.max_hp),
                   max_speed=body.max_speed * (1 + stats.move))
    return Loadout(body, weapon, stats)
