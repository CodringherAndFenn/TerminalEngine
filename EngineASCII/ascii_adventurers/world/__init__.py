"""
world -- terrain: tile types, deterministic hashing, noise, biomes, and the
two world implementations (the island, ChunkedWorld, and the fixed TestMap),
which share one interface: tile_at / glyph_at / damage_tile / hp_at /
spawn_point.
"""

from __future__ import annotations

import random

from .. import config


def make_world(seed: int | None = None):
    """The world selected by config.WORLD_MODE. The island uses `seed`,
    else config.SEED, else a fresh random seed."""
    if config.WORLD_MODE == "test":
        from .test_map import TestMap

        return TestMap.load(config.TEST_MAP_FILE)
    from .chunked import ChunkedWorld

    if seed is None:
        seed = config.SEED if config.SEED is not None else random_seed()
    return ChunkedWorld(seed)


def random_seed() -> int:
    return random.SystemRandom().randrange(1, 10**6)
