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

    __slots__ = ("cx", "cy", "tiles", "glyphs", "biomes")

    def __init__(self, cx: int, cy: int, tiles_: list, glyphs: list, biome_ids: bytearray):
        self.cx, self.cy = cx, cy
        self.tiles: list[TileType] = tiles_
        self.glyphs: list[str] = glyphs
        self.biomes = biome_ids


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
)
_IDX = {t: i for i, t in enumerate(_TILES)}
_T = _IDX.__getitem__

# Noise salts.
SALT_LAKE = 53
_SALT_DETAIL = 67

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
    pine = (detail > config.FOREST_PINE_MIN) & (r1 < config.FOREST_PINE_DENSITY)
    return np.where(pine, _T(tiles.PINE), _T(tiles.FOREST_FLOOR))


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
        return _finish(cx, cy, ids, biome_ids, rng, None)

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
                   random.Random(hash_coords(seed, 0xB1D, cx, cy)) if buildings else None)


def _finish(cx, cy, ids, biome_ids, rng, building_rng) -> Chunk:
    """Turn the index arrays into the Chunk's lists: optional ruined
    buildings (per-tile Python, only in ruins chunks), then one glyph
    variant per tile."""
    n = config.CHUNK_SIZE
    grid = [_TILES[i] for i in ids.ravel().tolist()]
    flat_biomes = bytearray(biome_ids.astype(np.uint8).tobytes())
    if building_rng is not None:
        _place_buildings(grid, flat_biomes, building_rng, n)
    picks = rng.random(n * n).tolist()
    glyphs = [t.glyphs[int(p * len(t.glyphs))] for t, p in zip(grid, picks)]
    return Chunk(cx, cy, grid, glyphs, flat_biomes)


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
