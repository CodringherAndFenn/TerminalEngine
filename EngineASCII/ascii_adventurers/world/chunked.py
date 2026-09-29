"""
world/chunked.py -- the island world: chunk streaming and terrain damage.

Offers the same interface as TestMap (tile_at, glyph_at, damage_tile, hp_at,
spawn_point), so driving, shooting, collision and rendering don't know which
world they're in.

Streaming, once per frame (update):
  1. Every chunk touching a view plus LOAD_MARGIN tiles is wanted (one view
     per player: players roam independently). Missing
     ones get a builder (world/generator.py) queued.
  2. Builders run nearest-first for up to CHUNK_BUILD_BUDGET_MS, a few
     steps at a time, so generation never causes a visible hitch.
  3. Chunks farther than UNLOAD_MARGIN outside the view are dropped. The
     gap between the two margins stops a chunk flickering in and out when
     the hero walks back and forth over a border.
If something needs a tile in a chunk that isn't ready (the view jumped, or
a very long shot), that chunk is finished on the spot. It's correct, just
not budgeted; with the margins this basically never happens during play.

Only chunks near the view ever exist, so the island's size (config
WORLD_RADIUS) costs nothing by itself; the layout (world/layout.py) says
what any chunk will contain before it's built.

Damage persists: tile changes (worn hit points, destroyed tiles) are kept
per chunk outside the chunk data, and reapplied whenever the chunk is
generated again.
"""

from __future__ import annotations

import math
import time

from .. import config
from . import biomes, tiles
from .biomes import Biome
from .explored import ExploredMap
from .generator import Chunk, build_chunk
from .layout import IslandLayout
from .tiles import Damage, TileType


class ChunkedWorld:
    def __init__(self, seed: int, radius: float | None = None) -> None:
        n = config.CHUNK_SIZE
        assert n & (n - 1) == 0, "CHUNK_SIZE must be a power of two"
        self.seed = seed
        self.layout = IslandLayout(seed, radius)
        # What the player has seen (every chunk ever generated), for the maps.
        self.explored = ExploredMap()
        self._shift = n.bit_length() - 1   # tx >> shift == floor(tx / n)
        self._mask = n - 1                 # tx & mask == tx mod n (also < 0)
        self._chunks: dict[tuple[int, int], Chunk] = {}
        self._building: dict[tuple[int, int], object] = {}   # key -> generator
        # Persistent terrain changes: chunk key -> {local index: new tile}.
        self._changes: dict[tuple[int, int], dict[int, TileType]] = {}
        self._hp: dict[tuple[int, int], int] = {}             # damaged tiles
        self._changed: set[tuple[int, int]] = set()          # see drain_changed
        self.sync_builds = 0   # chunks that had to be finished on demand
        # Keys of chunks loaded since the last drain_loaded() -- the enemy
        # spawner listens to this.
        self._loaded_log: list[tuple[int, int]] = []

    # --- Queries (hot path: called for every visible tile each frame) --------------

    def _chunk(self, tx: int, ty: int) -> Chunk:
        key = (tx >> self._shift, ty >> self._shift)
        chunk = self._chunks.get(key)
        return chunk if chunk is not None else self._build_now(key)

    def tile_at(self, tx: int, ty: int) -> TileType:
        c = self._chunk(tx, ty)
        return c.tiles[((ty & self._mask) << self._shift) | (tx & self._mask)]

    def glyph_at(self, tx: int, ty: int) -> str:
        c = self._chunk(tx, ty)
        return c.glyphs[((ty & self._mask) << self._shift) | (tx & self._mask)]

    def biome_at(self, tx: int, ty: int) -> Biome:
        c = self._chunk(tx, ty)
        return biomes.BY_ID[c.biomes[((ty & self._mask) << self._shift) | (tx & self._mask)]]

    def hp_at(self, tx: int, ty: int) -> int | None:
        return self._hp.get((tx, ty))

    def spawn_point(self) -> tuple[float, float]:
        # Near the island's centre, never trapped by a lake (see
        # IslandLayout.spawn); the generator keeps SPAWN_CLEAR_RADIUS around
        # it empty.
        sx, sy = self.layout.spawn
        return (sx + 0.5, sy + 0.5)

    # --- Damage --------------------------------------------------------------------

    def drain_changed(self) -> set[tuple[int, int]]:
        """Tiles whose look changed since the last call (for the terrain
        renderer's cached blocks)."""
        changed, self._changed = self._changed, set()
        return changed

    def damage_tile(self, tx: int, ty: int, amount: int) -> Damage:
        c = self._chunk(tx, ty)
        i = ((ty & self._mask) << self._shift) | (tx & self._mask)
        tile = c.tiles[i]
        if not tile.destructible:
            return Damage.NONE
        hp = self._hp.get((tx, ty), tile.hp) - amount
        if hp <= 0:
            self._hp.pop((tx, ty), None)
            debris = tile.becomes or tiles.RUBBLE
            c.tiles[i] = debris
            c.glyphs[i] = debris.glyph_at(tx, ty)
            self._changes.setdefault((c.cx, c.cy), {})[i] = debris
            self.explored.set_tile(tx, ty, debris)
            self._changed.add((tx, ty))
            return Damage.DESTROYED
        self._hp[(tx, ty)] = hp
        c.glyphs[i] = tile.glyph_at(tx, ty, hp)
        self._changed.add((tx, ty))
        return Damage.DAMAGED

    # --- Streaming -----------------------------------------------------------------

    def update(self, x: float, y: float, half_w: float, half_h: float,
               budget_ms: float = config.CHUNK_BUILD_BUDGET_MS) -> None:
        """Stream chunks around one view centered at world (x, y) with the
        given half-size in tiles. Call once per frame."""
        self.update_views([(x, y, half_w, half_h)], budget_ms)

    def update_views(self, views, budget_ms: float = config.CHUNK_BUILD_BUDGET_MS) -> None:
        """Stream chunks around several views at once -- one per player,
        each (x, y, half_w, half_h) in tiles. A chunk is wanted if it's near
        any view and kept while it's within the unload margin of any view;
        builds go nearest-to-some-view first."""
        views = list(views)
        want: set = set()
        keep: set = set()
        for x, y, hw, hh in views:
            want |= self._keys_in(x, y, hw + config.LOAD_MARGIN, hh + config.LOAD_MARGIN)
            keep |= self._keys_in(x, y, hw + config.UNLOAD_MARGIN, hh + config.UNLOAD_MARGIN)
        for key in want:
            if key not in self._chunks and key not in self._building:
                self._building[key] = build_chunk(self.layout, *key)

        # Unload chunks (and abandon builds) that drifted far outside every view.
        for key in [k for k in self._chunks if k not in keep]:
            del self._chunks[key]
        for key in [k for k in self._building if k not in keep]:
            del self._building[key]

        # Advance builders, nearest to a view center first, within budget.
        n = config.CHUNK_SIZE

        def dist2(k):
            cx, cy = k[0] * n + n / 2, k[1] * n + n / 2
            return min((cx - x) ** 2 + (cy - y) ** 2 for x, y, _, _ in views)

        deadline = time.perf_counter() + budget_ms / 1000.0
        for key in sorted(self._building, key=dist2):
            gen = self._building[key]
            try:
                while time.perf_counter() < deadline:
                    next(gen)
            except StopIteration as done:
                self._install(done.value)
                del self._building[key]
                continue
            break  # out of time this frame

    def ensure_ready(self, tx0: int, ty0: int, tx1: int, ty1: int) -> None:
        """Make sure every chunk overlapping the tile rect is built (e.g. the
        visible area before drawing)."""
        s = self._shift
        for cy in range(ty0 >> s, (ty1 >> s) + 1):
            for cx in range(tx0 >> s, (tx1 >> s) + 1):
                if (cx, cy) not in self._chunks:
                    self._build_now((cx, cy))

    def is_generated(self, tx: int, ty: int) -> bool:
        """Whether the chunk holding tile (tx, ty) is built (so reading it
        won't build it on the spot)."""
        return (tx >> self._shift, ty >> self._shift) in self._chunks

    @property
    def loaded_chunks(self) -> int:
        return len(self._chunks)

    @property
    def pending_chunks(self) -> int:
        return len(self._building)

    def _keys_in(self, x, y, half_w, half_h) -> set[tuple[int, int]]:
        s = self._shift
        cx0, cx1 = math.floor(x - half_w) >> s, math.floor(x + half_w) >> s
        cy0, cy1 = math.floor(y - half_h) >> s, math.floor(y + half_h) >> s
        return {(cx, cy) for cy in range(cy0, cy1 + 1) for cx in range(cx0, cx1 + 1)}

    def _build_now(self, key: tuple[int, int]) -> Chunk:
        """Finish (or run) a chunk's builder immediately."""
        gen = self._building.pop(key, None) or build_chunk(self.layout, *key)
        try:
            while True:
                next(gen)
        except StopIteration as done:
            chunk = done.value
        self.sync_builds += 1
        self._install(chunk)
        return chunk

    def _install(self, chunk: Chunk) -> None:
        """Store a freshly generated chunk, reapplying remembered damage."""
        key = (chunk.cx, chunk.cy)
        n = config.CHUNK_SIZE
        for i, tile in self._changes.get(key, {}).items():
            chunk.tiles[i] = tile
            chunk.glyphs[i] = tile.glyph_at(chunk.cx * n + (i & self._mask), chunk.cy * n + (i >> self._shift))
        # Standing tiles that were damaged but not destroyed show their wear.
        x0, y0 = chunk.cx * n, chunk.cy * n
        for (tx, ty), hp in self._hp.items():
            if x0 <= tx < x0 + n and y0 <= ty < y0 + n:
                i = ((ty & self._mask) << self._shift) | (tx & self._mask)
                chunk.glyphs[i] = chunk.tiles[i].glyph_at(tx, ty, hp)
        self._chunks[key] = chunk
        self.explored.record(chunk.cx, chunk.cy, chunk.tiles)
        self._loaded_log.append(key)

    def drain_loaded(self) -> list[tuple[int, int]]:
        """Chunk keys loaded since the last call (for spawning their enemies)."""
        keys, self._loaded_log = self._loaded_log, []
        return keys
