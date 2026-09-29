"""
world/explored.py -- what the player has seen, for the minimap and big map.

Every chunk that gets generated near the player counts as explored. Its tiles
are stored as one byte each: a "map class", the index of the tile type in
MAP_TILES (the map colors each class by tile type -- ground, trees, water,
walls...). Chunks stay remembered after they unload, and destroyed tiles
update their class, so the map shows the island as you left it. Cost: about
1 KB per chunk, so even thousands of explored chunks are a few MB.

Storage: one growing (capacity, n, n) uint8 array plus a sorted array of
packed chunk keys. Looking up any set of tiles is then a handful of numpy
operations (binary search for the chunk, then index into it), whatever the
number of chunks or points -- the whole-island big map samples thousands of
far-apart tiles at once.
"""

from __future__ import annotations

import numpy as np

from .. import config
from . import tiles
from .tiles import TileType

# Every tile type, in a fixed order: a tile's map class is its index here.
MAP_TILES: tuple[TileType, ...] = tuple(
    v for v in vars(tiles).values() if isinstance(v, TileType)
)
_CLASS = {t: i for i, t in enumerate(MAP_TILES)}
UNSEEN = 255

_OFF = 1 << 20      # chunk coords are shifted positive before packing


def _pack(kx, ky):
    """Chunk key(s) -> one int64 each (sortable, searchable)."""
    return ((np.asarray(kx, dtype=np.int64) + _OFF) << 22) | (np.asarray(ky, dtype=np.int64) + _OFF)


class ExploredMap:
    def __init__(self) -> None:
        n = config.CHUNK_SIZE
        self._n = n
        self._shift = n.bit_length() - 1
        self._slot: dict[tuple[int, int], int] = {}
        self._data = np.empty((64, n, n), dtype=np.uint8)
        self._sorted_keys = np.empty(0, dtype=np.int64)
        self._sorted_slots = np.empty(0, dtype=np.int64)
        self._index_dirty = False
        # Bumped on every change, so map views know when to redraw.
        self.version = 0

    def __len__(self) -> int:
        return len(self._slot)

    # --- Recording ------------------------------------------------------------------------

    def record(self, cx: int, cy: int, chunk_tiles: list[TileType]) -> None:
        """Remember a chunk's tiles (called whenever one is generated)."""
        slot = self._slot.get((cx, cy))
        if slot is None:
            slot = len(self._slot)
            if slot == len(self._data):
                self._data = np.concatenate([self._data, np.empty_like(self._data)])
            self._slot[(cx, cy)] = slot
            self._index_dirty = True
        classes = np.fromiter((_CLASS[t] for t in chunk_tiles), dtype=np.uint8,
                              count=self._n * self._n)
        self._data[slot] = classes.reshape(self._n, self._n)
        self.version += 1

    def set_tile(self, tx: int, ty: int, tile: TileType) -> None:
        """A tile changed (e.g. a wall was destroyed)."""
        slot = self._slot.get((tx >> self._shift, ty >> self._shift))
        if slot is not None:
            m = self._n - 1
            self._data[slot, ty & m, tx & m] = _CLASS[tile]
            self.version += 1

    def is_explored(self, tx: int, ty: int) -> bool:
        return (tx >> self._shift, ty >> self._shift) in self._slot

    # --- Lookup ---------------------------------------------------------------------------

    def sample(self, txs, tys) -> np.ndarray:
        """Map classes at integer tile coordinates (arrays that broadcast);
        UNSEEN where the chunk was never explored."""
        txs, tys = np.broadcast_arrays(np.asarray(txs, dtype=np.int64),
                                       np.asarray(tys, dtype=np.int64))
        out = np.full(txs.shape, UNSEEN, dtype=np.uint8)
        if not self._slot:
            return out
        if self._index_dirty:
            items = sorted((int(_pack(k[0], k[1])), s) for k, s in self._slot.items())
            self._sorted_keys = np.array([k for k, _ in items], dtype=np.int64)
            self._sorted_slots = np.array([s for _, s in items], dtype=np.int64)
            self._index_dirty = False
        keys = _pack(txs >> self._shift, tys >> self._shift)
        i = np.searchsorted(self._sorted_keys, keys)
        i = np.minimum(i, len(self._sorted_keys) - 1)
        found = self._sorted_keys[i] == keys
        m = self._n - 1
        out[found] = self._data[self._sorted_slots[i[found]], tys[found] & m, txs[found] & m]
        return out
