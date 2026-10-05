"""
ai -- enemy behaviour.

  brain.py      senses, memory, aggro/infighting (shared by all enemies)
  steering.py   Noita-style clumsy obstacle avoidance (no pathfinding)
  shooters.py   goblin archer, warlock, ogre, spell tower (Character bodies)
  creatures.py  fallen warrior, spore puffer, burrower
  bosses.py     bosses (M17): phases, moves, Froggy McFrogface, the Leech
                Swarm (M22), Lady Proboscia (M22.2), Khepri (M23.1)

make_enemy() builds one from its config.ENEMIES key.
"""

from __future__ import annotations

import random

from .. import config
from .bosses import Froggy, Khepri, LeechSwarm, Proboscia
from .creatures import (Boar, Burrower, DustDevil, GoldenScarab, Leech, Mosquito, Puffer,
                        Scarab, Warrior)
from .shooters import Archer, Ogre, PsyFrog, Spitter, Toad, Tower, Warlock, Wisp

KINDS = {
    "archer": Archer,
    "warlock": Warlock,
    "ogre": Ogre,
    "tower": Tower,
    "burrower": Burrower,
    "puffer": Puffer,
    "warrior": Warrior,
    # M12
    "wisp": Wisp,
    "toad": Toad,
    "spitter": Spitter,
    "boar": Boar,
    "devil": DustDevil,
    # M17
    "psyfrog": PsyFrog,
    "froggy": Froggy,
    # M22
    "leech": Leech,
    "leech_swarm": LeechSwarm,
    # M22.2
    "mosquito": Mosquito,
    "proboscia": Proboscia,
    # M23.1
    "golden_scarab": GoldenScarab,
    "scarab": Scarab,
    "khepri": Khepri,
}


def make_enemy(key: str, x: float, y: float, rng: random.Random, spawn_id=None):
    spec = config.ENEMIES[key]
    e = KINDS[spec.kind](spec, x, y, rng, spawn_id)
    e.kind_key = key              # its config.ENEMIES key (the bestiary)
    return e
