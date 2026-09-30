"""
players/cards.py -- level-up cards: what's offered, and what taking one does.

Offers. When a player has a card pick banked (players/progress.py) and no
offer on the table, CARD_OFFER_SIZE different cards are drawn from those
the hero may take (config.CARDS `heroes` / `kinds`) and hasn't maxed out,
weighted by CARD_RARITY_WEIGHT. The draw is seeded from the island seed,
the player's slot and how many offers they've had, so a run replays the
same way (and every machine in online co-op agrees).

Effects. A hero's stats are never nudged in place. After every pick the
hero's body and weapon are rebuilt from the base specs plus every card
taken so far (build_loadout), so stacking is exact and order-independent:
all "add" steps first, then all "mul" steps, then limits (e.g. attacks
can't get faster than MIN_INTERVAL, a swing can't pass 360 degrees).
"""

from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass, replace

from .. import config
from ..specs import CardSpec, CharacterSpec, WeaponSpec
from ..world.rng import hash_coords

MIN_INTERVAL = 0.08       # fastest attack cadence any stack of cards can reach


@dataclass
class Loadout:
    body: CharacterSpec
    weapon: WeaponSpec
    regen: float = 0.0        # hp per second
    lifesteal: float = 0.0    # fraction of damage dealt healed


def eligible(hero_key: str, weapon: WeaponSpec, taken: Counter) -> list[str]:
    out = []
    for key, card in config.CARDS.items():
        if taken[key] >= card.max_stacks:
            continue
        if card.heroes and hero_key not in card.heroes:
            continue
        if card.kinds and weapon.kind not in card.kinds:
            continue
        out.append(key)
    return out


def draw_offer(hero_key: str, weapon: WeaponSpec, taken: Counter, seed: int,
               player_index: int, draw_no: int) -> list[str]:
    """Up to CARD_OFFER_SIZE different card keys, weighted by rarity."""
    rng = random.Random(hash_coords(seed or 0, 0xCA7D, player_index, draw_no))
    pool = eligible(hero_key, weapon, taken)
    offer = []
    while pool and len(offer) < config.CARD_OFFER_SIZE:
        weights = [config.CARD_RARITY_WEIGHT[config.CARDS[k].rarity] for k in pool]
        pick = rng.choices(pool, weights)[0]
        offer.append(pick)
        pool.remove(pick)
    return offer


def build_loadout(hero_key: str, taken: Counter) -> Loadout:
    """The hero's body and weapon with every card in `taken` applied."""
    body = config.HEROES[hero_key]
    weapon = config.WEAPONS[body.weapon]
    shell = weapon.shell
    v = {
        "damage": float(shell.damage if shell else weapon.damage),
        "interval": weapon.fire_interval,
        "range": shell.max_range if shell else weapon.reach,
        "pellets": float(weapon.pellets),
        "spread": weapon.spread_deg,
        "pierce": float(shell.pierce) if shell else 0.0,
        "chain": float(shell.chain) if shell else 0.0,
        "chain_range": shell.chain_range if shell else 0.0,
        "chain_falloff": shell.chain_falloff if shell else 0.0,
        "shot_speed": shell.speed if shell else 0.0,
        "arc": weapon.arc_deg,
        "max_hp": float(body.max_hp),
        "move": body.max_speed,
        "regen": 0.0,
        "lifesteal": 0.0,
    }
    steps = [(stat, op, val) for key in sorted(taken) for _ in range(taken[key])
             for stat, op, val in config.CARDS[key].mods]
    for stat, op, val in steps:
        if op == "add":
            v[stat] += val
    for stat, op, val in steps:
        if op == "mul":
            v[stat] *= val
    v["interval"] = max(MIN_INTERVAL, v["interval"])
    v["arc"] = min(360.0, v["arc"])
    v["spread"] = min(160.0, max(0.0, v["spread"]))
    v["chain_falloff"] = min(0.95, v["chain_falloff"])

    if shell is not None:
        shell = replace(shell, damage=round(v["damage"]), max_range=v["range"],
                        pierce=round(v["pierce"]), chain=round(v["chain"]),
                        chain_range=v["chain_range"], chain_falloff=v["chain_falloff"],
                        speed=v["shot_speed"])
        weapon = replace(weapon, shell=shell, fire_interval=v["interval"],
                         pellets=round(v["pellets"]), spread_deg=v["spread"])
    else:
        weapon = replace(weapon, damage=round(v["damage"]), fire_interval=v["interval"],
                         reach=v["range"], arc_deg=v["arc"])
    body = replace(body, max_hp=round(v["max_hp"]), max_speed=v["move"])
    return Loadout(body, weapon, regen=v["regen"], lifesteal=v["lifesteal"])


def card(key: str) -> CardSpec:
    return config.CARDS[key]
