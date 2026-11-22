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
    label: str = ""    # shown to players (pause menu, stats); "" = name

    @property
    def title(self) -> str:
        return self.label or self.name


PLAINS = Biome(0, "plains", tiles.PLAINS)
# The forest became the haunted forest in M21; inside it's still "forest"
# (enemy tables, saved records), players see the label.
FOREST = Biome(1, "forest", tiles.DEAD_LEAVES, "haunted forest")
DESERT = Biome(2, "desert", tiles.SAND)
RUINS = Biome(3, "ruins", tiles.CONCRETE)
SWAMP = Biome(4, "swamp", tiles.MUD)
MUSHROOM = Biome(5, "mushroom", tiles.MYCELIUM)
OCEAN = Biome(6, "ocean", tiles.WATER)       # everything past the coast
# The ocean zones (M29, design/OCEAN.md): islands of their own out at sea.
PARADISE = Biome(7, "paradise", tiles.CLOUD)
PANDEMONIUM = Biome(8, "pandemonium", tiles.OBSIDIAN)

BY_ID = (PLAINS, FOREST, DESERT, RUINS, SWAMP, MUSHROOM, OCEAN, PARADISE, PANDEMONIUM)
# The zones' biomes by zone key.
ZONES = {"paradise": PARADISE, "pandemonium": PANDEMONIUM}
BY_NAME = {b.name: b for b in BY_ID}
