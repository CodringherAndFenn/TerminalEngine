"""
world/tiles.py -- terrain tile types.

Each tile is drawn as CELLS_PER_TILE (2) characters. A type lists several
2-character glyph variants; which one a given tile shows is picked by a
position hash, so ground looks varied but stays stable as you scroll.

Destructible types have hit points (`hp` > 0), `wear` glyph sets shown as
they take damage, and `becomes`: the (passable) tile left once destroyed.

Only ASCII and the engine's synthesized box/block glyphs are used (VT323 has
no other symbols -- see CLAUDE.md).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from .. import config, palette
from .rng import hash_coords


class Damage(Enum):
    """Outcome of a world's damage_tile()."""

    NONE = "none"            # not destructible (rock, void, open ground)
    DAMAGED = "damaged"      # lost hit points, still standing
    DESTROYED = "destroyed"  # replaced by its rubble


@dataclass(frozen=True)
class TileType:
    name: str
    glyphs: tuple[str, ...]      # 2-char variants
    fg: tuple
    bg: tuple
    solid: bool = False          # blocks walking
    blocks_shots: bool = False   # stops projectiles
    hp: int = 0                  # 0 = indestructible
    # Glyph variant sets for increasing damage: wear[0] = lightly damaged,
    # wear[-1] = nearly destroyed. Empty = looks intact until destroyed.
    wear: tuple[tuple[str, ...], ...] = ()
    becomes: TileType | None = None  # what's left when destroyed

    @property
    def destructible(self) -> bool:
        return self.hp > 0

    def glyph_at(self, tx: int, ty: int, hp_left: int | None = None) -> str:
        """Glyph for the tile at (tx, ty), given its remaining hit points
        (None = undamaged). Any damage shows wear[0]; the fraction of hp lost
        picks later stages evenly (a 4 hp wall with 2 stages: 3-2 hp ->
        wear[0], 1 hp -> wear[1])."""
        variants = self.glyphs
        if hp_left is not None and self.wear and hp_left < self.hp:
            lost = 1.0 - hp_left / self.hp                 # 0 < lost < 1
            stage = min(len(self.wear), max(1, math.ceil(lost * len(self.wear) - 1e-9)))
            variants = self.wear[stage - 1]
        return variants[hash_coords(tx, ty, 0x71E) % len(variants)]


GROUND = TileType(
    "ground", ("  ", "  ", "  ", ". ", " .", " '", "` "), palette.GROUND_FG, palette.GROUND_BG,
)
GRASS = TileType(
    "grass", ('" ', ' "', "''", ", ", " ,"), palette.GRASS_FG, palette.GROUND_BG,
)
RUBBLE = TileType(
    "rubble", (".:", ":.", ";,", ",;"), palette.RUBBLE_FG, palette.GROUND_BG,
)
SPLINTERS = TileType(
    # What a destroyed tree leaves: passable, like rubble.
    "splinters", ("_,", ",_", "._", "_."), palette.SPLINTER_FG, palette.GROUND_BG,
)
TREE = TileType(
    "tree", ("^^", "^A", "A^", "^^"), palette.TREE_FG, palette.TREE_BG,
    solid=True, blocks_shots=True, hp=config.TREE_HP,
    wear=(("^,", ",^", "^."),),
    becomes=SPLINTERS,
)
WALL = TileType(
    "wall", ("██",), palette.WALL_FG, palette.WALL_BG,
    solid=True, blocks_shots=True, hp=config.WALL_HP,
    # Shade glyphs get sparser as the wall crumbles: cracked, then breaking up.
    wear=(("▓▒", "▒▓", "▓▓"), ("░▒", "▒░", "░ ", " ░")),
    becomes=RUBBLE,
)
ROCK = TileType(
    "rock", ("▓▓", "▓▒", "▒▓"), palette.ROCK_FG, palette.ROCK_BG,
    solid=True, blocks_shots=True,
)
WATER = TileType(
    # VT323's "~" renders like an "N", so water is a sparse dither instead.
    "water", ("░ ", " ░", "  ", "  ", "▒░"), palette.WATER_FG, palette.WATER_BG,
    solid=True,  # can't be crossed on foot, but shots fly over it
)
VOID = TileType(
    "void", ("  ",), palette.VOID_FG, palette.VOID_BG,
    solid=True, blocks_shots=True,
)


# --- Biome tiles (milestone 3) -------------------------------------------------------
# Every destroyed thing leaves passable debris matching its biome's ground.

# Plains: wide open grassland (the start area).
PLAINS = TileType(
    "plains", ("  ", "  ", "  ", ". ", " '", "  "), palette.PLAINS_GRASS, palette.PLAINS_BG,
)
TALL_GRASS = TileType(
    "tall grass", ('" ', ' "', '""', "',"), palette.PLAINS_GRASS, palette.PLAINS_BG,
)
FLOWERS = TileType(
    "flowers", ("* ", " *", ".*"), palette.PLAINS_FLOWER, palette.PLAINS_BG,
)

# Forest: dense pines with clearings.
FOREST_FLOOR = TileType(
    "forest floor", (", ", " ,", "  ", ". "), palette.FOREST_FLOOR, palette.FOREST_BG,
)
PINE_DEBRIS = TileType(
    "splinters", ("_,", ",_", "._"), palette.SPLINTER_FG, palette.FOREST_BG,
)
PINE = TileType(
    "pine", ("/\\", "^^", "A^", "^A"), palette.PINE_FG, palette.PINE_BG,
    solid=True, blocks_shots=True, hp=config.TREE_HP,
    wear=(("/.", ".\\", "^."),),
    becomes=PINE_DEBRIS,
)

# Desert: sand, dunes, cacti and mesa rock.
SAND = TileType(
    "sand", ("  ", ". ", " .", "  ", "  "), palette.SAND_FG, palette.SAND_BG,
)
DUNE = TileType(
    "dunes", ("--", "-.", ".-", "_-"), palette.DUNE_FG, palette.SAND_BG,
)
CACTUS_DEBRIS = TileType(
    "cactus pulp", ("_.", "._", ",."), palette.CACTUS_FG, palette.SAND_BG,
)
CACTUS = TileType(
    "cactus", ("Y ", " Y", "Y'", "'Y"), palette.CACTUS_FG, palette.SAND_BG,
    solid=True, blocks_shots=True, hp=config.CACTUS_HP,
    becomes=CACTUS_DEBRIS,
)
MESA = TileType(
    "mesa rock", ("▓▓", "▓▒", "▒▓"), palette.MESA_FG, palette.MESA_BG,
    solid=True, blocks_shots=True,
)

# Ruins: concrete lots and broken buildings (built from WALL / RUBBLE).
CONCRETE = TileType(
    "concrete", ("  ", ". ", " .", "  ", ":."), palette.CONCRETE_FG, palette.CONCRETE_BG,
)

# Swamp: mud, reeds, bog pools (like water: can't be walked through, shots fly over)
# and mangroves.
MUD = TileType(
    "mud", ("  ", ", ", " .", "  "), palette.MUD_FG, palette.MUD_BG,
)
REEDS = TileType(
    "reeds", ("|'", "'|", "||", "|,"), palette.REED_FG, palette.MUD_BG,
)
BOG = TileType(
    "bog", ("░ ", " ░", "  ", "  "), palette.BOG_FG, palette.BOG_BG,
    solid=True,
)
MANGROVE_ROOTS = TileType(
    "roots", ("_,", ",_", "._"), palette.MANGROVE_FG, palette.MUD_BG,
)
MANGROVE = TileType(
    "mangrove", ("%%", "%&", "&%"), palette.MANGROVE_FG, palette.MANGROVE_BG,
    solid=True, blocks_shots=True, hp=config.MANGROVE_HP,
    wear=(("%.", ".%"),),
    becomes=MANGROVE_ROOTS,
)

# Mushroom: purple mycelium, glowing spores, giant mushrooms.
MYCELIUM = TileType(
    "mycelium", ("  ", ". ", " ,", "  "), palette.MYCELIUM_FG, palette.MYCELIUM_BG,
)
SPORES = TileType(
    "spores", ("o ", " o", ".o", "o."), palette.SPORE_FG, palette.MYCELIUM_BG,
)
SHROOM_MUSH = TileType(
    "mush", ("..", ".,", ",."), palette.SHROOM_FG, palette.MYCELIUM_BG,
)
GIANT_SHROOM = TileType(
    "giant mushroom", ("()", "{}", "()"), palette.SHROOM_FG, palette.SHROOM_BG,
    solid=True, blocks_shots=True, hp=config.SHROOM_HP,
    wear=((") ", " (", "(."),),
    becomes=SHROOM_MUSH,
)


# --- Landmarks (M17, world/landmarks.py) -----------------------------------------------
# Hand-placed structures stamped over the generated biome. None of their
# walls can be destroyed: quest places must survive the fight.

# A boss lair's ring of standing stones, and the thorn gate that seals it.
LAIR_STONE = TileType(
    "standing stones", ("▓▓", "█▓", "▓█"), palette.LAIR_STONE_FG, palette.LAIR_STONE_BG,
    solid=True, blocks_shots=True,
)
THORN_GATE = TileType(
    "thorn gate", ("><", "}{", "X>", "<X"), palette.THORN_FG, palette.THORN_BG,
    solid=True, blocks_shots=True,
)
# Froggy's pools: like bog (can't be walked through, shots fly over), and
# the boss dives into them.
POND = TileType(
    "pond", ("░ ", " ░", "  ", "▒░"), palette.POND_FG, palette.POND_BG,
    solid=True,
)
LILY_PADS = TileType(
    "lily pads", ("o ", " o", "  ", "o."), palette.LILY_FG, palette.MUD_BG,
)
# The frog hunter's hut on its deck.
PLANK_WALL = TileType(
    "plank wall", ("||", "|:", ":|"), palette.PLANK_FG, palette.PLANK_BG,
    solid=True, blocks_shots=True,
)
DECK = TileType(
    "deck", ("==", "=-", "-="), palette.DECK_FG, palette.DECK_BG,
)
DRYING_RACK = TileType(
    "drying rack", ("TT", "T'", "'T"), palette.RACK_FG, palette.DECK_BG,
    solid=True,
)
# Where a quest giver stands (on the deck, so nobody walks through them).
HUNTER_POST = TileType(
    "hunter's post", ("==",), palette.DECK_FG, palette.DECK_BG,
    solid=True,
)
