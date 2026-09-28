"""
world/biomes.py -- the six biomes and how the world picks one per tile.

Biome choice is a lookup on smooth noise fields (see config for the rules):
"heat" and "wetness" vary over hundreds of tiles and decide between plains,
forest, desert and swamp; two patchier fields add the rarer ruins and
mushroom regions on top. A per-tile random wobble (BIOME_BORDER_JITTER)
makes the borders ragged. Around the spawn the world is forced to plains so
every run starts in open ground.
"""

from __future__ import annotations

from dataclasses import dataclass

from .. import config
from . import tiles
from .tiles import TileType


@dataclass(frozen=True)
class Biome:
    id: int
    name: str
    ground: TileType   # the default floor, used for cleared spawn area etc.


PLAINS = Biome(0, "plains", tiles.PLAINS)
FOREST = Biome(1, "forest", tiles.FOREST_FLOOR)
DESERT = Biome(2, "desert", tiles.SAND)
RUINS = Biome(3, "ruins", tiles.CONCRETE)
SWAMP = Biome(4, "swamp", tiles.MUD)
MUSHROOM = Biome(5, "mushroom", tiles.MYCELIUM)

BY_ID = (PLAINS, FOREST, DESERT, RUINS, SWAMP, MUSHROOM)


def classify(heat: float, wet: float, ruins: float, shroom: float) -> Biome:
    """Biome for one tile from its (jittered) field values."""
    if shroom > config.MUSHROOM_MIN:
        return MUSHROOM
    if ruins > config.RUINS_MIN:
        return RUINS
    if wet > config.SWAMP_WET and heat > config.SWAMP_HEAT:
        return SWAMP
    if wet > config.FOREST_WET:
        return FOREST
    if heat > config.DESERT_HEAT and wet < config.DESERT_DRY:
        return DESERT
    return PLAINS
