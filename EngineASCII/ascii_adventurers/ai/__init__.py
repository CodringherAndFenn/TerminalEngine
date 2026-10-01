"""
ai -- enemy behaviour.

  brain.py      senses, memory, aggro/infighting (shared by all enemies)
  steering.py   Noita-style clumsy obstacle avoidance (no pathfinding)
  shooters.py   goblin archer, warlock, ogre, spell tower (Character bodies)
  creatures.py  fallen warrior, spore puffer, burrower

make_enemy() builds one from its config.ENEMIES key.
"""

from __future__ import annotations

import random

from .. import config
from .creatures import Boar, Burrower, DustDevil, Puffer, Warrior
from .shooters import Archer, Ogre, Spitter, Toad, Tower, Warlock, Wisp

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
}


def make_enemy(key: str, x: float, y: float, rng: random.Random, spawn_id=None):
    spec = config.ENEMIES[key]
    e = KINDS[spec.kind](spec, x, y, rng, spawn_id)
    e.kind_key = key              # its config.ENEMIES key (the bestiary)
    return e
