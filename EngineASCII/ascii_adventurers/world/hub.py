"""
world/hub.py -- the Guild Hall's floor plan: indoor tiles and where the
people and things you can talk to stand.

The map is a hand-drawn file (assets/maps/guild_hall.txt) loaded as a
TestMap with its own legend, so the game's terrain renderer and collision
work on it unchanged.

Legend:
    #  stone wall      .  wooden floor     ,  flagstones      "  grass
    =  carpet          B  bookshelf        C  counter / desk  F  banner
    *  torch stand     D  training dummy   G  dungeon gate    ~  fountain
    T  tree            @  where you come in
  Stations (you walk up to them and press E / Enter):
    g  the guildmaster (shared upgrades)    t  the trainer (hero upgrades)
    a  the archivist (card unlocks)         d  the dungeon gate (start a run)
    1-5  the heroes' statues, in config.HEROES order (play as that hero)
  NPCs and statues stand on tiles you can't walk through.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from .. import config, palette
from . import tiles
from .test_map import MAPS_DIR, TestMap
from .tiles import TileType

HUB_MAP = "guild_hall.txt"

WOOD_FLOOR = TileType("wood floor", ("  ", "  ", "' ", " .", "  "), palette.HUB_WOOD_FG,
                      palette.HUB_WOOD_BG)
FLAGSTONE = TileType("flagstones", ("  ", ". ", " ,", "  "), palette.HUB_STONE_FG,
                     palette.HUB_STONE_BG)
CARPET = TileType("carpet", ("░░",), palette.HUB_CARPET_FG, palette.HUB_CARPET_BG)
STONE_WALL = TileType("stone wall", ("▓▓", "▓▒", "▒▓"), palette.HUB_WALL_FG, palette.HUB_WALL_BG,
                      solid=True, blocks_shots=True)
BOOKSHELF = TileType("bookshelf", ("||", "|:", ":|", "||"), palette.HUB_BOOKS_FG,
                     palette.HUB_BOOKS_BG, solid=True, blocks_shots=True)
COUNTER = TileType("counter", ("▀▀",), palette.HUB_COUNTER_FG, palette.HUB_COUNTER_BG,
                   solid=True)
BANNER = TileType("banner", ("██",), palette.HUB_BANNER, palette.HUB_WALL_BG, solid=True,
                  blocks_shots=True)
TORCH = TileType("torch", (" *",), palette.HUB_TORCH, palette.HUB_WOOD_BG, solid=True)
DUMMY = TileType("dummy", ("[]",), palette.HUB_DUMMY, palette.HUB_STONE_BG, solid=True)
GATE = TileType("gate", ("||",), palette.HUB_GATE_FG, palette.HUB_GATE_BG, solid=True,
                blocks_shots=True)
PEDESTAL = TileType("pedestal", ("▄▄",), palette.HUB_PEDESTAL, palette.HUB_WOOD_BG, solid=True)

LEGEND = {
    "#": STONE_WALL, ".": WOOD_FLOOR, ",": FLAGSTONE, '"': tiles.GRASS, "=": CARPET,
    "B": BOOKSHELF, "C": COUNTER, "F": BANNER, "*": TORCH, "D": DUMMY, "G": GATE,
    "~": tiles.WATER, "T": tiles.TREE, "@": CARPET,
    # Stations: people stand on solid floor; the gate's spot is plain carpet.
    "g": replace(WOOD_FLOOR, name="guildmaster", solid=True),
    "a": replace(WOOD_FLOOR, name="archivist", solid=True),
    "t": replace(FLAGSTONE, name="trainer", solid=True),
    "d": CARPET,
    **{str(i + 1): PEDESTAL for i in range(len(config.HEROES))},
}

# Station marker -> (kind, NPC sprite or None).
_PEOPLE = {"g": ("guild", "guildmaster"), "t": ("hero", "trainer"), "a": ("cards", "archivist"),
           "d": ("gate", None)}


@dataclass
class Station:
    kind: str            # guild | hero | cards | gate | statue
    x: float             # tile centre, world tiles
    y: float
    sprite: str | None = None    # an NPC's or statue's picture (render/characters.ART)
    hero: str | None = None      # statues: whose


def load_hub(name: str = HUB_MAP) -> tuple[TestMap, list[Station]]:
    rows = (MAPS_DIR / name).read_text(encoding="utf-8").splitlines()
    heroes = list(config.HEROES)
    stations = []
    for ty, line in enumerate(rows):
        for tx, ch in enumerate(line):
            if ch in _PEOPLE:
                kind, sprite = _PEOPLE[ch]
                stations.append(Station(kind, tx + 0.5, ty + 0.5, sprite))
            elif ch.isdigit() and 0 < int(ch) <= len(heroes):
                hero = heroes[int(ch) - 1]
                stations.append(Station("statue", tx + 0.5, ty + 0.5, hero, hero))
    return TestMap(rows, LEGEND), stations
