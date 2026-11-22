"""
One island build per seed for the whole test process.

A ChunkedWorld places every landmark when it is made (world/landmarks.py:
every quest's camp, lair and spots, the chests, the ocean zones' plans).
That takes seconds, and each new zone adds to it, while hundreds of tests
start a game on the same few seeds. So the tests build each (seed, radius)
layout once and hand every new world its own deep copy, which is about ten
times cheaper.

The copy is a true copy: landmarks, props, spots, zones and the zone plans
are all fresh, so nothing a test changes reaches the next one. Only the
tile types and biomes stay shared, because they are frozen singletons the
game compares with `is`.

tests/__init__.py installs this for every test. To check that two builds
of one seed really agree, build inside `with fresh_islands():`.
"""

from __future__ import annotations

import copy
from contextlib import contextmanager

from ascii_adventurers.world import chunked
from ascii_adventurers.world.biomes import Biome
from ascii_adventurers.world.layout import IslandLayout
from ascii_adventurers.world.tiles import TileType

# (seed, radius) -> (the layout as first built, {id: obj} of what every copy shares)
_built: dict[tuple, tuple[IslandLayout, dict]] = {}
_fresh = 0


def _singletons(root) -> dict:
    """Every TileType and Biome reachable from `root`, as a deepcopy memo:
    the copies point at these same objects instead of cloning them."""
    found: dict = {}
    seen: set = set()
    todo = [root]
    while todo:
        o = todo.pop()
        if id(o) in seen or isinstance(o, (str, int, float, bool, bytes, type(None), type)):
            continue
        seen.add(id(o))
        if isinstance(o, (TileType, Biome)):
            found[id(o)] = o
        elif isinstance(o, dict):
            todo += o.keys()
            todo += o.values()
        elif isinstance(o, (list, tuple, set, frozenset)):
            todo += o
        elif hasattr(o, "__dict__"):
            todo += vars(o).values()
    return found


def island(seed: int, radius: float | None = None) -> IslandLayout:
    """IslandLayout(seed, radius) with its landmarks placed, copied from
    the first build of that seed."""
    if _fresh:
        return IslandLayout(seed, radius)
    key = (seed, radius)
    if key not in _built:
        first = IslandLayout(seed, radius)
        first.landmarks
        _built[key] = (first, _singletons(first))
    first, shared = _built[key]
    return copy.deepcopy(first, dict(shared))


@contextmanager
def fresh_islands():
    """Worlds made inside this block build their island from scratch."""
    global _fresh
    _fresh += 1
    try:
        yield
    finally:
        _fresh -= 1


def install() -> None:
    """Make ChunkedWorld use island() for its layout (the only place the
    game builds one)."""
    chunked.IslandLayout = island
