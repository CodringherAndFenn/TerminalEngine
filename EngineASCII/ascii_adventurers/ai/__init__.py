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
                Fragile (M24.3), Nettle (M25.1), Love & Cuddles (M25.2),
                The Fallen (M25.3), Mycelium the fly agaric (M26.1),
                Mycelium the shaggy ink cap (M26.2), Mycelium the giant puffball (M26.3),
                More than Life / More than Death (M27, the plains boss)
  plains.py     the plains' P7 enemies: chasers (rats, farmhands, geese,
                mole rats, crows), hounds, hawk, molehill, bull, lancer,
                shieldbearer, priest, straw golem, scarecrow, drummer
  desert.py     the desert's P9 enemies: sand imps (hoppers), scorpion,
                vulture, basilisk, rattlesnake, mummy, fire dancer, dune
                raider, tumbleweed, cactus golem, djinn lamp
  ruins.py      the ruins' P10 enemies: gargoyle, clockwork sentry, colossus,
                rubble crab, gem thief, crossbow sniper, flail brute, rune
                mine, haunted blades, bell ghost
  swamp.py      the swamp's P11 enemies: bog crocodile, snapping turtle, heron,
                swamp hag, marsh lights, bloated corpse, sludge
  mushroom.py   the mushroom biome's P12 enemies: myconid shaman, cordyceps
                hunter, fungal brute, rootweaver, giant snail, pillbug,
                mantis, fairy ring (and caps), mold core
  forest.py     the haunted forest's P8 enemies: skeletons (and bone piles),
                bats, banshee, phantom, grave digger, headless knight (and
                its head), centipede, giant spider, cultist (and candles),
                wendigo

make_enemy() builds one from its config.ENEMIES key.
"""

from __future__ import annotations

import random

from .. import config
from .bosses import (Amanita, FalloutKing, Fragile, Froggy, Glamour, InkCap, Khepri,
                     LeechSwarm, LoveCuddles, Magus, MycoPart, Nettle, OlSpitter, Proboscia,
                     LegionPart, Necromancer, PuffHalf, Puffball, SnowKing, TheFallen)
from .creatures import (Boar, Burrower, Camel, DustDevil, FrostWraith, Ghoul, GoldenScarab,
                        Hourglass, IsotopeRod, Leech, Mosquito, Puffer, SandElemental, SandGolem, Scarab,
                        Sigil, ToxicBarrel, Warrior)
from .desert import (Basilisk, CactusGolem, DjinnLamp, DuneRaider, FireDancer, Hopper, Mummy,
                     Rattlesnake, Scorpion, Tumbleweed, Vulture)
from .mushroom import (CordycepsHunter, FairyCap, FairyRing, FungalBrute, GiantSnail, Mantis,
                       MoldCore, Myconid, Pillbug, Rootweaver)
from .swamp import (BloatedCorpse, Crocodile, Heron, MarshLight, Sludge, SwampHag, Turtle)
from .ruins import (BellGhost, Clockwork, Colossus, FlailBrute, Gargoyle, GemThief, HauntedBlade,
                    RubbleCrab, RuneMine, Sniper)
from .forest import (Banshee, Bat, BonePile, Candle, Centipede, Cultist, GiantSpider,
                     GraveDigger, HeadlessKnight, KnightHead, Phantom, Skeleton, Wendigo)
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
    # M25.2
    "love_cuddles": LoveCuddles,
    # M25.3
    "the_fallen": TheFallen,
    # M26.1
    "mycelium_amanita": Amanita,
    "myco_part": MycoPart,
    # M26.2
    "mycelium_inkcap": InkCap,
    # M26.3
    "mycelium_puffball": Puffball,
    "puff_half": PuffHalf,
    # M27
    "necromancer": Necromancer,
    "legion_part": LegionPart,
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
    # P8: the haunted forest
    "skeleton": Skeleton,
    "bone_pile": BonePile,
    "bat": Bat,
    "banshee": Banshee,
    "phantom": Phantom,
    "grave_digger": GraveDigger,
    "headless_knight": HeadlessKnight,
    "knight_head": KnightHead,
    "centipede": Centipede,
    "giant_spider": GiantSpider,
    "cultist": Cultist,
    "candle": Candle,
    "wendigo": Wendigo,
    # P9: the desert
    "hopper": Hopper,
    "scorpion": Scorpion,
    "vulture": Vulture,
    "basilisk": Basilisk,
    "rattlesnake": Rattlesnake,
    "mummy": Mummy,
    "fire_dancer": FireDancer,
    "dune_raider": DuneRaider,
    "tumbleweed": Tumbleweed,
    "cactus_golem": CactusGolem,
    "djinn_lamp": DjinnLamp,
    # P10: the ruins
    "gargoyle": Gargoyle,
    "clockwork": Clockwork,
    "colossus": Colossus,
    "rubble_crab": RubbleCrab,
    "gem_thief": GemThief,
    "sniper": Sniper,
    "flail_brute": FlailBrute,
    "rune_mine": RuneMine,
    "haunted_blade": HauntedBlade,
    "bell_ghost": BellGhost,
    # P11: the swamp
    "crocodile": Crocodile,
    "turtle": Turtle,
    "heron": Heron,
    "swamp_hag": SwampHag,
    "marsh_light": MarshLight,
    "bloated_corpse": BloatedCorpse,
    "sludge": Sludge,
    # P12: the mushroom biome
    "myconid": Myconid,
    "cordyceps": CordycepsHunter,
    "fungal_brute": FungalBrute,
    "rootweaver": Rootweaver,
    "giant_snail": GiantSnail,
    "pillbug": Pillbug,
    "mantis": Mantis,
    "fairy_ring": FairyRing,
    "fairy_cap": FairyCap,
    "mold_core": MoldCore,
}


def make_enemy(key: str, x: float, y: float, rng: random.Random, spawn_id=None):
    spec = config.ENEMIES[key]
    e = KINDS[spec.kind](spec, x, y, rng, spawn_id)
    e.kind_key = key              # its config.ENEMIES key (the bestiary)
    return e
