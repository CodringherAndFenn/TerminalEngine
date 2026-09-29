"""
world/biomes.py -- the biomes. Where each one lies on the island is decided
by world/layout.py; what grows in it, by world/generator.py.
"""

from __future__ import annotations

from dataclasses import dataclass

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
OCEAN = Biome(6, "ocean", tiles.WATER)       # everything past the coast

BY_ID = (PLAINS, FOREST, DESERT, RUINS, SWAMP, MUSHROOM, OCEAN)
BY_NAME = {b.name: b for b in BY_ID}
