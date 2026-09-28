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
    solid: bool = False          # blocks tanks
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
    solid=True,  # tanks can't ford it, but shells fly over it
)
VOID = TileType(
    "void", ("  ",), palette.VOID_FG, palette.VOID_BG,
    solid=True, blocks_shots=True,
)
