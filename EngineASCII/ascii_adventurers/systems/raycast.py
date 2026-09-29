"""
systems/raycast.py -- find the first tile a straight path hits.

Shells are fast (a couple of tiles per frame at top speed), so checking only
where a shell *ends up* each frame would let it skip straight over a
one-tile wall. Instead each frame's movement is treated as a line segment
and walked tile by tile.

Algorithm: Amanatides & Woo grid traversal ("A Fast Voxel Traversal
Algorithm", 1987). Tiles are unit squares, so along the segment
p(t) = p0 + t * d  (t in [0, 1]) the path crosses a vertical tile edge every
1/|dx| of t and a horizontal one every 1/|dy|. We keep, for each axis, the
t of the *next* crossing (t_max_x / t_max_y) and always step across
whichever comes first. That visits exactly the tiles the segment passes
through, in order, with no gaps and no repeats.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

from ..world.tiles import TileType


@dataclass(frozen=True)
class RayHit:
    tx: int
    ty: int
    t: float        # fraction of the segment at which the tile is entered
    x: float        # world point where the segment enters the tile
    y: float


def first_hit(
    tile_at: Callable[[int, int], TileType],
    x0: float, y0: float, x1: float, y1: float,
    blocks: Callable[[TileType], bool] = lambda t: t.blocks_shots,
) -> RayHit | None:
    """First tile along the segment (x0, y0) -> (x1, y1) for which
    `blocks(tile)` is true, or None if the segment is clear. A segment that
    starts inside a blocking tile hits it at t = 0."""
    tx, ty = math.floor(x0), math.floor(y0)
    if blocks(tile_at(tx, ty)):
        return RayHit(tx, ty, 0.0, x0, y0)

    dx, dy = x1 - x0, y1 - y0
    end_tx, end_ty = math.floor(x1), math.floor(y1)
    step_x = 1 if dx > 0 else -1
    step_y = 1 if dy > 0 else -1
    # t to cross one whole tile along each axis (inf if not moving on it).
    t_delta_x = abs(1.0 / dx) if dx else math.inf
    t_delta_y = abs(1.0 / dy) if dy else math.inf
    # t of the first edge crossing on each axis.
    if dx > 0:
        t_max_x = (tx + 1 - x0) / dx
    elif dx < 0:
        t_max_x = (x0 - tx) / -dx
    else:
        t_max_x = math.inf
    if dy > 0:
        t_max_y = (ty + 1 - y0) / dy
    elif dy < 0:
        t_max_y = (y0 - ty) / -dy
    else:
        t_max_y = math.inf

    # Bounded loop: one step per tile boundary crossed, plus slack.
    for _ in range(abs(end_tx - tx) + abs(end_ty - ty) + 2):
        if t_max_x > 1.0 and t_max_y > 1.0:
            return None  # segment ends inside the current (clear) tile
        if t_max_x < t_max_y:
            t = t_max_x
            tx += step_x
            t_max_x += t_delta_x
        elif t_max_y < t_max_x:
            t = t_max_y
            ty += step_y
            t_max_y += t_delta_y
        else:
            # Exactly through a corner: it touches both side neighbours, and
            # a shell shouldn't squeeze diagonally between two walls.
            t = t_max_x
            for cx, cy in ((tx + step_x, ty), (tx, ty + step_y)):
                if blocks(tile_at(cx, cy)):
                    return RayHit(cx, cy, t, x0 + dx * t, y0 + dy * t)
            tx += step_x
            ty += step_y
            t_max_x += t_delta_x
            t_max_y += t_delta_y
        if blocks(tile_at(tx, ty)):
            return RayHit(tx, ty, t, x0 + dx * t, y0 + dy * t)
    return None
