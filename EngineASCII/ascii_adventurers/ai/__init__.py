"""
ai -- enemy behaviour.

  brain.py      senses, memory, aggro/infighting (shared by all enemies)
  steering.py   Noita-style clumsy obstacle avoidance (no pathfinding)
  shooters.py   goblin archer, warlock, ogre, spell tower (Character bodies)
  creatures.py  fallen warrior, spore puffer, burrower
  bosses.py     bosses (M17): phases, moves, Froggy McFrogface, the Leech
                Swarm (M22), Lady Proboscia (M22.2), Khepri (M23.1),
                Ol' Spitter (M23.2), the Nameless Magus (M23.3),
                the Fallout King (M24.1),
                the Snow King (M24.2),
                Fragile (M24.3), Nettle (M25.1)
  plains.py     the plains' P7 enemies: chasers (rats, farmhands, geese,
                mole rats, crows), hounds, hawk, molehill, bull, lancer,
                shieldbearer, priest, straw golem, scarecrow, drummer

make_enemy() builds one from its config.ENEMIES key.
"""

from __future__ import annotations

import random

from .. import config
from .bosses import (FalloutKing, Fragile, Froggy, Glamour, Khepri, LeechSwarm, Magus, Nettle,
                     OlSpitter, Proboscia, SnowKing)
from .creatures import (Boar, Burrower, Camel, DustDevil, FrostWraith, Ghoul, GoldenScarab,
                        Hourglass, IsotopeRod, Leech, Mosquito, Puffer, SandElemental, SandGolem, Scarab,
                        Sigil, ToxicBarrel, Warrior)
from .plains import (Bull, Chaser, Crow, Drummer, Hawk, Hound, Lancer, Molehill, Priest,
                     Scarecrow, Shieldbearer, StrawGolem)
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
    # M23.2
    "camel": Camel,
    "ol_spitter": OlSpitter,
    # M23.3
    "elemental": SandElemental,
    "golem": SandGolem,
    "sigil": Sigil,
    "hourglass": Hourglass,
    "nameless_magus": Magus,
    # M24.1
    "ghoul": Ghoul,
    "rod": IsotopeRod,
    "barrel": ToxicBarrel,
    "fallout_king": FalloutKing,
    # M24.2
    "wraith": FrostWraith,
    "snow_king": SnowKing,
    # M24.3
    "fragile": Fragile,
    # M25.1
    "glamour": Glamour,
    "nettle": Nettle,
    # P7: the plains
    "chaser": Chaser,
    "crow": Crow,
    "hound": Hound,
    "hawk": Hawk,
    "molehill": Molehill,
    "bull": Bull,
    "lancer": Lancer,
    "shieldbearer": Shieldbearer,
    "priest": Priest,
    "straw_golem": StrawGolem,
    "scarecrow": Scarecrow,
    "drummer": Drummer,
}


def make_enemy(key: str, x: float, y: float, rng: random.Random, spawn_id=None):
    spec = config.ENEMIES[key]
    e = KINDS[spec.kind](spec, x, y, rng, spawn_id)
    e.kind_key = key              # its config.ENEMIES key (the bestiary)
    return e
