"""
world/test_map.py -- a fixed, hand-authored map for milestones 1-2.

Exposes the same query interface the infinite chunked world will have
(`tile_at`, `spawn_point`), so the scene and systems don't care which one
they're given. Outside the authored area everything is VOID (solid).

Map file legend (one character per tile):
    .  ground        "  grass        T  tree       #  wall
    R  rock          :  rubble       ~  water      @  player spawn
"""

from __future__ import annotations

from pathlib import Path

from . import tiles
from .tiles import TileType

MAPS_DIR = Path(__file__).resolve().parent.parent / "assets" / "maps"

LEGEND: dict[str, TileType] = {
    ".": tiles.GROUND,
    '"': tiles.GRASS,
    "T": tiles.TREE,
    "#": tiles.WALL,
    "R": tiles.ROCK,
    ":": tiles.RUBBLE,
    "~": tiles.WATER,
    "@": tiles.GROUND,
}


class TestMap:
    __test__ = False  # not a unittest class, despite the name

    def __init__(self, rows: list[str]) -> None:
        self.height = len(rows)
        self.width = max((len(r) for r in rows), default=0)
        self._tiles: list[list[TileType]] = []
        # Glyph variant per tile, precomputed once: hashing positions every
        # frame was the single biggest rendering cost.
        self._glyphs: list[list[str]] = []
        self._spawn = (self.width / 2, self.height / 2)
        for ty, line in enumerate(rows):
            row = []
            for tx in range(self.width):
                ch = line[tx] if tx < len(line) else "."
                if ch == "@":
                    # Spawn at the tile's center.
                    self._spawn = (tx + 0.5, ty + 0.5)
                row.append(LEGEND.get(ch, tiles.GROUND))
            self._tiles.append(row)
            self._glyphs.append([t.glyph_at(tx, ty) for tx, t in enumerate(row)])

    @classmethod
    def load(cls, name: str) -> "TestMap":
        text = (MAPS_DIR / name).read_text(encoding="utf-8")
        return cls(text.splitlines())

    def tile_at(self, tx: int, ty: int) -> TileType:
        if 0 <= ty < self.height and 0 <= tx < self.width:
            return self._tiles[ty][tx]
        return tiles.VOID

    def glyph_at(self, tx: int, ty: int) -> str:
        """The 2-char glyph this tile is drawn with."""
        if 0 <= ty < self.height and 0 <= tx < self.width:
            return self._glyphs[ty][tx]
        return tiles.VOID.glyphs[0]

    def spawn_point(self) -> tuple[float, float]:
        return self._spawn
