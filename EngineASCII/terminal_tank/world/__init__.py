"""
world -- terrain: tile types, deterministic hashing, noise, biomes, and the
two world implementations (the infinite ChunkedWorld and the fixed TestMap),
which share one interface: tile_at / glyph_at / damage_tile / hp_at /
spawn_point.
"""

from __future__ import annotations

import random

from .. import config


def make_world():
    """The world selected by config.WORLD_MODE. The infinite world uses
    config.SEED, or a fresh random seed when it's None."""
    if config.WORLD_MODE == "test":
        from .test_map import TestMap

        return TestMap.load(config.TEST_MAP_FILE)
    from .chunked import ChunkedWorld

    seed = config.SEED if config.SEED is not None else random.SystemRandom().randrange(1, 10**6)
    return ChunkedWorld(seed)
