"""
world/generator.py -- builds one chunk of the infinite world.

Determinism: everything a chunk contains is a pure function of
(seed, chunk x, chunk y). Smooth fields come from world/noise.py, which is
keyed by *global* tile coordinates (so fields are seamless across chunk
edges), and the per-tile dice come from a random.Random seeded with
hash_coords(seed, cx, cy) and consumed in a fixed order. Chunks can
therefore be generated in any order, unloaded and regenerated, and always
come out identical.

Time slicing: build_chunk is a Python generator. It yields after each
expensive step (one noise field, or 8 rows of tiles), so the world can
spread a chunk's ~5-8 ms of work over several frames instead of hitching.
Run it to completion to get the Chunk (returned via StopIteration.value).
"""

from __future__ import annotations

import math
import random
from typing import Generator

from .. import config
from . import biomes, tiles
from .noise import fbm_at, fbm_grid, value_noise_at, value_noise_grid
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


def sample_biome(seed: int, tx: int, ty: int) -> biomes.Biome:
    """The broad biome at a tile without generating its chunk: the same
    fields build_chunk uses, sampled at one point, minus the border wobble.
    Cheap enough for scanning large areas (tests, a future minimap)."""
    x, y = tx + 0.5, ty + 0.5
    if math.hypot(x, y) < config.SPAWN_PLAINS_RADIUS:
        return biomes.PLAINS
    return biomes.classify(
        fbm_at(seed, 11, x, y, config.BIOME_HEAT_SCALE),
        fbm_at(seed, 23, x, y, config.BIOME_WET_SCALE),
        value_noise_at(seed, 37, x, y, config.BIOME_RARE_SCALE),
        value_noise_at(seed, 41, x, y, config.BIOME_RARE_SCALE * 0.9),
    )


def difficulty(tx: float, ty: float) -> float:
    """0 at the spawn, rising linearly to 1 at DIFFICULTY_RAMP_TILES away."""
    return min(1.0, math.hypot(tx, ty) / config.DIFFICULTY_RAMP_TILES)


# --- Per-biome feature placement -------------------------------------------------
# Each takes the tile's detail/lake noise, the chunk RNG and the difficulty,
# and returns the tile. `detail` varies over ~DETAIL_SCALE tiles, so
# thresholding it makes clumps (tree clusters, pools, rock outcrops).


def _lake_allowed(dist, heat, wet, ruins, shroom) -> bool:
    """Lakes form in plains, forest and mushroom land (swamps have bogs,
    deserts and ruins stay dry). Decided from the *un-jittered* biome so a
    lake never gets sprinkled along a ragged biome border."""
    if dist < config.SPAWN_PLAINS_RADIUS:
        return True
    return biomes.classify(heat, wet, ruins, shroom) in (biomes.PLAINS, biomes.FOREST, biomes.MUSHROOM)


def _plains(detail, lake, rng, diff):
    r = rng.random()
    if r < config.PLAINS_TREE_CHANCE:
        return tiles.TREE
    if r < config.PLAINS_TREE_CHANCE + config.PLAINS_ROCK_CHANCE * (1 + diff):
        return tiles.ROCK
    if detail > config.PLAINS_TALL_GRASS:
        return tiles.TALL_GRASS
    if rng.random() < config.PLAINS_FLOWER_CHANCE:
        return tiles.FLOWERS
    return tiles.PLAINS


def _forest(detail, lake, rng, diff):
    if detail > config.FOREST_PINE_MIN and rng.random() < config.FOREST_PINE_DENSITY:
        return tiles.PINE
    return tiles.FOREST_FLOOR


def _desert(detail, lake, rng, diff):
    # Mesas grow a little larger farther out (harsher terrain).
    if detail > config.DESERT_MESA_MIN - 0.04 * diff:
        return tiles.MESA
    lo, hi = config.DESERT_DUNE_BAND
    if lo < detail < hi:
        return tiles.DUNE
    if rng.random() < config.DESERT_CACTUS_CHANCE:
        return tiles.CACTUS
    return tiles.SAND


def _swamp(detail, lake, rng, diff):
    if detail > config.SWAMP_BOG_MIN:
        return tiles.BOG
    if detail > config.SWAMP_REED_MIN and rng.random() < 0.6:
        return tiles.REEDS
    if rng.random() < config.SWAMP_MANGROVE_CHANCE:
        return tiles.MANGROVE
    return tiles.MUD


def _mushroom(detail, lake, rng, diff):
    if detail > config.MUSHROOM_SHROOM_MIN and rng.random() < config.MUSHROOM_SHROOM_DENSITY:
        return tiles.GIANT_SHROOM
    if rng.random() < config.MUSHROOM_SPORE_CHANCE:
        return tiles.SPORES
    return tiles.MYCELIUM


def _ruins(detail, lake, rng, diff):
    if rng.random() < config.RUINS_RUBBLE_CHANCE:
        return tiles.RUBBLE
    return tiles.CONCRETE


_FEATURES = {
    biomes.PLAINS.id: _plains,
    biomes.FOREST.id: _forest,
    biomes.DESERT.id: _desert,
    biomes.RUINS.id: _ruins,
    biomes.SWAMP.id: _swamp,
    biomes.MUSHROOM.id: _mushroom,
}


# --- Chunk builder ---------------------------------------------------------------


def build_chunk(seed: int, cx: int, cy: int) -> Generator[None, None, Chunk]:
    n = config.CHUNK_SIZE
    x0, y0 = cx * n, cy * n

    # Smooth fields for the whole chunk, one per step.
    heat = fbm_grid(seed, 11, x0, y0, n, n, config.BIOME_HEAT_SCALE)
    yield
    wet = fbm_grid(seed, 23, x0, y0, n, n, config.BIOME_WET_SCALE)
    yield
    rare_ruins = value_noise_grid(seed, 37, x0, y0, n, n, config.BIOME_RARE_SCALE)
    rare_shroom = value_noise_grid(seed, 41, x0, y0, n, n, config.BIOME_RARE_SCALE * 0.9)
    yield
    # Two octaves so shores are irregular rather than perfect ovals.
    lake = fbm_grid(seed, 53, x0, y0, n, n, config.LAKE_SCALE)
    yield
    detail = fbm_grid(seed, 67, x0, y0, n, n, config.DETAIL_SCALE)
    # Small-scale noise that wobbles the biome fields, so borders are ragged
    # in clumps rather than a salt-and-pepper mix of single tiles.
    edge = value_noise_grid(seed, 79, x0, y0, n, n, config.BIOME_BORDER_SCALE)
    yield

    rng = random.Random(hash_coords(seed, 0xC4, cx, cy))
    jitter = config.BIOME_BORDER_JITTER
    plains_r = config.SPAWN_PLAINS_RADIUS
    clear_r2 = config.SPAWN_CLEAR_RADIUS ** 2
    grid: list[TileType] = [tiles.PLAINS] * (n * n)
    biome_ids = bytearray(n * n)

    for ly in range(n):
        ty = y0 + ly
        for lx in range(n):
            tx = x0 + lx
            j = (edge[ly][lx] - 0.5) * 2 * jitter
            dist = math.hypot(tx + 0.5, ty + 0.5)
            if dist < plains_r * (1 + 2 * j):  # ragged edge, like other borders
                biome = biomes.PLAINS
            else:
                biome = biomes.classify(
                    heat[ly][lx] + j, wet[ly][lx] - j,
                    rare_ruins[ly][lx] + j, rare_shroom[ly][lx] + j,
                )
            i = ly * n + lx
            biome_ids[i] = biome.id
            if dist * dist < clear_r2:
                grid[i] = biome.ground
            elif lake[ly][lx] > config.LAKE_MIN and _lake_allowed(
                dist, heat[ly][lx], wet[ly][lx], rare_ruins[ly][lx], rare_shroom[ly][lx]
            ):
                grid[i] = tiles.WATER
            else:
                grid[i] = _FEATURES[biome.id](
                    detail[ly][lx], lake[ly][lx], rng, dist / config.DIFFICULTY_RAMP_TILES
                )
        if ly % 8 == 7:
            yield

    ruins_tiles = sum(1 for b in biome_ids if b == biomes.RUINS.id)
    if ruins_tiles > n * n * 0.3:
        _place_buildings(grid, biome_ids, rng, n)

    glyphs = [t.glyphs[rng.randrange(len(t.glyphs))] for t in grid]
    return Chunk(cx, cy, grid, glyphs, biome_ids)


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
