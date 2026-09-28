"""
ai -- enemy behaviour.

  brain.py      senses, memory, aggro/infighting (shared by all enemies)
  steering.py   Noita-style clumsy obstacle avoidance (no pathfinding)
  vehicles.py   tankette, sniper, heavy tank, turret (Tank bodies)
  creatures.py  fallen warrior, spore puffer, burrower

make_enemy() builds one from its config.ENEMIES key.
"""

from __future__ import annotations

import random

from .. import config
from .creatures import Burrower, Puffer, Warrior
from .vehicles import Heavy, Sniper, Tankette, Turret

KINDS = {
    "tankette": Tankette,
    "sniper": Sniper,
    "heavy": Heavy,
    "turret": Turret,
    "burrower": Burrower,
    "puffer": Puffer,
    "warrior": Warrior,
}


def make_enemy(key: str, x: float, y: float, difficulty: float,
               rng: random.Random, spawn_id=None):
    spec = config.ENEMIES[key]
    return KINDS[spec.kind](spec, x, y, difficulty, rng, spawn_id)
