"""
world/generator.py -- builds one chunk of the island.

Determinism: everything a chunk contains is a pure function of
(seed, chunk x, chunk y). The biome of each tile comes from the island
layout (world/layout.py); smooth local fields come from world/noise.py,
keyed by *global* tile coordinates (so they're seamless across chunk
edges); and the per-tile dice come from a numpy Generator (plus a
random.Random for ruined buildings) seeded with hash_coords(seed, cx, cy).
Chunks can therefore be generated in any order, unloaded and regenerated,
and always come out identical.

Everything is computed for the whole 32 x 32 chunk at once with numpy: each
biome's rules below are array masks ("where detail > X and roll < Y ->
pine"), not per-tile Python.

Time slicing: build_chunk is a Python generator that yields between its
steps, so the world can spread a chunk's work over several frames instead of
hitching. Run it to completion to get the Chunk (returned via
StopIteration.value). Chunks entirely out at sea skip all of it.
"""

from __future__ import annotations

import math
import random
from typing import Generator

import numpy as np

from .. import config
from . import biomes, tiles
from .layout import IslandLayout
from .noise import chunk_axes, fbm
from .rng import hash_coords
from .tiles import TileType


class Chunk:
    """One generated chunk: flat row-major arrays of CHUNK_SIZE^2 tiles."""

    __slots__ = ("cx", "cy", "tiles", "glyphs", "biomes", "lights")

    def __init__(self, cx: int, cy: int, tiles_: list, glyphs: list, biome_ids: bytearray,
                 lights: tuple = ()):
        self.cx, self.cy = cx, cy
        self.tiles: list[TileType] = tiles_
        self.glyphs: list[str] = glyphs
        self.biomes = biome_ids
        # Haunted forest wisp lights in this chunk, as world points (drawn
        # floating by render/haunt.py; they never touch the game).
        self.lights: tuple = lights


# Tile types the generator can place, by index (chunks are built as arrays
# of these indices, then turned into TileType lists).
_TILES = (
    tiles.PLAINS, tiles.TALL_GRASS, tiles.FLOWERS, tiles.TREE, tiles.ROCK,
    tiles.FOREST_FLOOR, tiles.PINE,
    tiles.SAND, tiles.DUNE, tiles.CACTUS, tiles.MESA,
    tiles.CONCRETE, tiles.RUBBLE,
    tiles.MUD, tiles.REEDS, tiles.BOG, tiles.MANGROVE,
    tiles.MYCELIUM, tiles.SPORES, tiles.GIANT_SHROOM,
    tiles.WATER,
    tiles.DEAD_LEAVES, tiles.FOG, tiles.GNARLED_TRUNK, tiles.STUMP,
    tiles.LOG_LEFT, tiles.LOG_MID, tiles.LOG_RIGHT,
    *tiles.CROWN.values(),
)
_IDX = {t: i for i, t in enumerate(_TILES)}
_T = _IDX.__getitem__

# Noise salts.
SALT_LAKE = 53
_SALT_DETAIL = 67
_SALT_HAUNT = 71

# --- Per-biome feature placement -------------------------------------------------
# Each takes the chunk's `detail` field and two independent dice arrays
# (uniform 0..1 per tile) and returns tile indices for the whole chunk; the
# builder keeps each result only where that biome is. `detail` varies over
# ~DETAIL_SCALE tiles, so thresholding it makes clumps (tree clusters,
# pools, rock outcrops). np.select picks the first rule that matches.


def _plains(detail, r1, r2):
    tree = config.PLAINS_TREE_CHANCE
    return np.select(
        [r1 < tree, r1 < tree + config.PLAINS_ROCK_CHANCE,
         detail > config.PLAINS_TALL_GRASS, r2 < config.PLAINS_FLOWER_CHANCE],
        [_T(tiles.TREE), _T(tiles.ROCK), _T(tiles.TALL_GRASS), _T(tiles.FLOWERS)],
        _T(tiles.PLAINS))


def _forest(detail, r1, r2):
    """The haunted forest's ground: dead leaves, fog patches, lone stumps.
    Its trees, logs and lights are stamped afterwards (_haunt), since they
    span several tiles."""
    return np.select(
        [r1 < config.HAUNT_STUMP_CHANCE, detail > config.HAUNT_FOG_MIN],
        [_T(tiles.STUMP), _T(tiles.FOG)],
        _T(tiles.DEAD_LEAVES))


def _desert(detail, r1, r2):
    lo, hi = config.DESERT_DUNE_BAND
    return np.select(
        [detail > config.DESERT_MESA_MIN, (detail > lo) & (detail < hi),
         r1 < config.DESERT_CACTUS_CHANCE],
        [_T(tiles.MESA), _T(tiles.DUNE), _T(tiles.CACTUS)],
        _T(tiles.SAND))


def _swamp(detail, r1, r2):
    return np.select(
        [detail > config.SWAMP_BOG_MIN, (detail > config.SWAMP_REED_MIN) & (r1 < 0.6),
         r2 < config.SWAMP_MANGROVE_CHANCE],
        [_T(tiles.BOG), _T(tiles.REEDS), _T(tiles.MANGROVE)],
        _T(tiles.MUD))


def _mushroom(detail, r1, r2):
    return np.select(
        [(detail > config.MUSHROOM_SHROOM_MIN) & (r1 < config.MUSHROOM_SHROOM_DENSITY),
         r2 < config.MUSHROOM_SPORE_CHANCE],
        [_T(tiles.GIANT_SHROOM), _T(tiles.SPORES)],
        _T(tiles.MYCELIUM))


def _ruins(detail, r1, r2):
    return np.where(r1 < config.RUINS_RUBBLE_CHANCE, _T(tiles.RUBBLE), _T(tiles.CONCRETE))


def _ocean(detail, r1, r2):
    return np.full(detail.shape, _T(tiles.WATER))


_FEATURES = {
    biomes.PLAINS.id: _plains,
    biomes.FOREST.id: _forest,
    biomes.DESERT.id: _desert,
    biomes.RUINS.id: _ruins,
    biomes.SWAMP.id: _swamp,
    biomes.MUSHROOM.id: _mushroom,
    biomes.OCEAN.id: _ocean,
}
# Lakes form in plains, forest and mushroom land (swamps have bogs, deserts
# and ruins stay dry).
LAKE_BIOMES = np.array([biomes.PLAINS.id, biomes.FOREST.id, biomes.MUSHROOM.id], dtype=np.uint8)


# --- Chunk builder ---------------------------------------------------------------


def build_chunk(layout: IslandLayout, cx: int, cy: int) -> Generator[None, None, Chunk]:
    n = config.CHUNK_SIZE
    x0, y0 = cx * n, cy * n
    seed = layout.seed
    rng = np.random.default_rng(hash_coords(seed, 0xC4, cx, cy))

    if layout.all_ocean(x0, y0, x0 + n, y0 + n):
        ids = np.full((n, n), _T(tiles.WATER))
        biome_ids = np.full((n, n), biomes.OCEAN.id, dtype=np.uint8)
        return _finish(cx, cy, ids, biome_ids, rng, None, layout)

    xs, ys = chunk_axes(x0, y0, n, n)
    biome_ids, smooth_ids = layout.biome_ids_both(xs, ys)
    yield
    # Lakes: see IslandLayout.lake_mask (the spawn search uses the same one).
    lakes = layout.lake_mask(xs, ys, smooth_ids)
    detail = fbm(seed, _SALT_DETAIL, xs, ys, config.DETAIL_SCALE)

    r1, r2 = rng.random((n, n)), rng.random((n, n))
    ids = np.zeros((n, n), dtype=np.int64)
    for bid in np.unique(biome_ids):
        mask = biome_ids == bid
        ids[mask] = _FEATURES[int(bid)](detail, r1, r2)[mask]
    ids[lakes] = _T(tiles.WATER)
    lights: tuple = ()
    if (biome_ids == biomes.FOREST.id).any():
        lights = _haunt(layout, x0, y0, ids, biome_ids)
        yield
    # The start is swept clean.
    sx, sy = layout.spawn
    clear = np.hypot(xs - (sx + 0.5), ys - (sy + 0.5)) < config.SPAWN_CLEAR_RADIUS
    if clear.any():
        ground = np.array([_T(b.ground) for b in biomes.BY_ID])
        ids[clear] = ground[biome_ids[clear]]
    yield

    ruins_tiles = int((biome_ids == biomes.RUINS.id).sum())
    buildings = ruins_tiles > n * n * 0.3
    return _finish(cx, cy, ids, biome_ids, rng,
                   random.Random(hash_coords(seed, 0xB1D, cx, cy)) if buildings else None,
                   layout, lights)


# Tiles a tree's crown or a log may be drawn over (the open forest floor).
_OPEN = np.array([_T(tiles.DEAD_LEAVES), _T(tiles.FOG)])


def _haunt(layout: IslandLayout, x0: int, y0: int, ids, biome_ids) -> tuple:
    """Stamp the haunted forest's trees and logs into chunk `ids` and
    return its wisp lights.

    Everything comes from the global HAUNT_CELL grid (config): each cell's
    dice are hash_coords(seed, salt, cell x, cell y), so a tree whose crown
    crosses a chunk edge is worked out the same way by both chunks, and
    trees come out seamless. A trunk stands only where the world there is
    forest and not lake (asked of the layout, as the trunk may lie in the
    next chunk); crown, roots and logs are drawn only over open forest
    floor inside this chunk."""
    n = config.CHUNK_SIZE
    cell = config.HAUNT_CELL
    seed = layout.seed
    tree_p, log_p, wisp_p = (config.HAUNT_TREE_CHANCE, config.HAUNT_LOG_CHANCE,
                             config.HAUNT_WISP_CHANCE)
    forest = biomes.FOREST.id
    trunks, logs, lights = [], [], []
    # Cells whose tree could reach into this chunk (a crown reaches 2 tiles).
    for gy in range((y0 - 2) // cell, (y0 + n + 2) // cell + 1):
        for gx in range((x0 - 2) // cell, (x0 + n + 2) // cell + 1):
            h = hash_coords(seed, _SALT_HAUNT, gx, gy)
            u = (h & 0xFFFF) / 65536.0
            if u < tree_p:
                trunks.append((gx * cell + 1 + (h >> 16) % 3, gy * cell + 2 + (h >> 20) % 2))
            elif u < tree_p + log_p:
                length = 2 + (h >> 24) % 2
                logs.append((gx * cell + 1, gy * cell + 1 + (h >> 16) % 3, length))
            elif u < tree_p + log_p + wisp_p:
                wx, wy = gx * cell + 2.5, gy * cell + 2.5
                if x0 <= wx < x0 + n and y0 <= wy < y0 + n \
                        and biome_ids[math.floor(wy) - y0, math.floor(wx) - x0] == forest:
                    lights.append((wx, wy))
    if trunks:
        # Where each trunk is forest and not lake: one vectorised layout query.
        px = np.array([t[0] + 0.5 for t in trunks])
        py = np.array([t[1] + 0.5 for t in trunks])
        ragged, smooth = layout.biome_ids_both(px, py)
        ok = (ragged == forest) & ~layout.lake_mask(px, py, smooth)
        for (tx, ty), good in zip(trunks, ok.tolist()):
            if not good:
                continue
            _put(ids, biome_ids, x0, y0, tx, ty, tiles.GNARLED_TRUNK, open_only=False)
            for (dx, dy), piece in tiles.CROWN.items():
                _put(ids, biome_ids, x0, y0, tx + dx, ty + dy, piece)
    for lx, ly, length in logs:
        parts = [tiles.LOG_LEFT] + [tiles.LOG_MID] * (length - 2) + [tiles.LOG_RIGHT]
        # Only whole logs: every tile of it inside this chunk and open.
        spots = [(lx + i, ly) for i in range(length)]
        if all(x0 <= x < x0 + n and y0 <= y < y0 + n and biome_ids[y - y0, x - x0] == forest
               and ids[y - y0, x - x0] in _OPEN for x, y in spots):
            for (x, y), part in zip(spots, parts):
                ids[y - y0, x - x0] = _T(part)
    return tuple(lights)


def _put(ids, biome_ids, x0, y0, tx, ty, tile, open_only=True) -> None:
    """Place `tile` at world tile (tx, ty) if it's in this chunk and forest
    (and, unless open_only is False, open floor)."""
    n = config.CHUNK_SIZE
    x, y = tx - x0, ty - y0
    if not (0 <= x < n and 0 <= y < n) or biome_ids[y, x] != biomes.FOREST.id:
        return
    if open_only and ids[y, x] not in _OPEN:
        return
    ids[y, x] = _T(tile)


def _finish(cx, cy, ids, biome_ids, rng, building_rng, layout=None, lights=()) -> Chunk:
    """Turn the index arrays into the Chunk's lists: optional ruined
    buildings (per-tile Python, only in ruins chunks), the landmarks over
    it (world/landmarks.py: quest camps, boss lairs), then one glyph
    variant per tile."""
    n = config.CHUNK_SIZE
    grid = [_TILES[i] for i in ids.ravel().tolist()]
    flat_biomes = bytearray(biome_ids.astype(np.uint8).tobytes())
    if building_rng is not None:
        _place_buildings(grid, flat_biomes, building_rng, n)
    if layout is not None:
        for mark in layout.landmarks:
            mark.stamp(grid, cx, cy, n)
    picks = rng.random(n * n).tolist()
    glyphs = [t.glyphs[int(p * len(t.glyphs))] for t, p in zip(grid, picks)]
    return Chunk(cx, cy, grid, glyphs, flat_biomes, lights)


def _place_buildings(grid, biome_ids, rng: random.Random, n: int) -> None:
    """Broken buildings: wall rectangles with a doorway, some wall segments
    already collapsed into rubble, rubble-strewn floors. Kept inside the
    chunk (1-tile margin) so no building ever spans two chunks, and only
    drawn over ruins tiles, so buildings on a biome edge look cut off."""
    lo, hi = config.RUINS_BUILDINGS
    for _ in range(rng.randint(lo, hi)):
        w, h = rng.randint(7, 13), rng.randint(5, 9)
        bx, by = rng.randint(1, n - w - 1), rng.randint(1, n - h - 1)
        door_side = rng.randrange(4)
        # A 3-wide doorway fits between the corners: offsets 1 .. side-4.
        door_at = rng.randint(1, (w if door_side < 2 else h) - 4)
        for y in range(by, by + h):
            for x in range(bx, bx + w):
                i = y * n + x
                if biome_ids[i] != biomes.RUINS.id:
                    continue
                edge = x in (bx, bx + w - 1) or y in (by, by + h - 1)
                if not edge:
                    grid[i] = tiles.RUBBLE if rng.random() < 0.25 else tiles.CONCRETE
                    continue
                # Position along the door's side, for a 2-3 tile doorway.
                side_pos = {0: x - bx if y == by else -9, 1: x - bx if y == by + h - 1 else -9,
                            2: y - by if x == bx else -9, 3: y - by if x == bx + w - 1 else -9}
                if door_at <= side_pos[door_side] < door_at + 3:
                    grid[i] = tiles.CONCRETE
                elif rng.random() < config.RUINS_WALL_GAP_CHANCE:
                    grid[i] = tiles.RUBBLE
                else:
                    grid[i] = tiles.WALL
