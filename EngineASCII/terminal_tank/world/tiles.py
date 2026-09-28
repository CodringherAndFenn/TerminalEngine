"""
world/tiles.py -- terrain tile types.

Each tile is drawn as CELLS_PER_TILE (2) characters. A type lists several
2-character glyph variants; which one a given tile shows is picked by a
position hash, so ground looks varied but stays stable as you scroll.

Only ASCII and the engine's synthesized box/block glyphs are used (VT323 has
no other symbols -- see CLAUDE.md).
"""

from __future__ import annotations

from dataclasses import dataclass

from .. import palette
from .rng import hash_coords


@dataclass(frozen=True)
class TileType:
    name: str
    glyphs: tuple[str, ...]      # 2-char variants
    fg: tuple
    bg: tuple
    solid: bool = False          # blocks tanks
    blocks_shots: bool = False   # stops projectiles (milestone 2)
    hp: int = 0                  # 0 = indestructible (milestone 2)

    def glyph_at(self, tx: int, ty: int) -> str:
        return self.glyphs[hash_coords(tx, ty, 0x71E) % len(self.glyphs)]


GROUND = TileType(
    "ground", ("  ", "  ", "  ", ". ", " .", " '", "` "), palette.GROUND_FG, palette.GROUND_BG,
)
GRASS = TileType(
    "grass", ('" ', ' "', "''", ", ", " ,"), palette.GRASS_FG, palette.GROUND_BG,
)
TREE = TileType(
    "tree", ("^^", "^A", "A^", "^^"), palette.TREE_FG, palette.TREE_BG,
    solid=True, blocks_shots=True, hp=2,
)
WALL = TileType(
    "wall", ("██",), palette.WALL_FG, palette.WALL_BG,
    solid=True, blocks_shots=True, hp=6,
)
ROCK = TileType(
    "rock", ("▓▓", "▓▒", "▒▓"), palette.ROCK_FG, palette.ROCK_BG,
    solid=True, blocks_shots=True,
)
RUBBLE = TileType(
    "rubble", (".:", ":.", ";,", ",;"), palette.RUBBLE_FG, palette.GROUND_BG,
)
WATER = TileType(
    # VT323's "~" renders like an "N", so water is a sparse dither instead.
    "water", ("░ ", " ░", "  ", "  ", "▒░"), palette.WATER_FG, palette.WATER_BG,
    solid=True,  # tanks can't ford it, but shells fly over it
)
VOID = TileType(
    "void", ("  ",), palette.VOID_FG, palette.VOID_BG,
    solid=True, blocks_shots=True,
)
