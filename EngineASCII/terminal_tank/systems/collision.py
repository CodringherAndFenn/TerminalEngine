"""
systems/collision.py -- axis-aligned box vs. tile-grid collision.

Movement is resolved one axis at a time (x, then y). If a step on one axis
ends overlapping a solid tile, the box is pushed back flush against that
tile's edge on that axis only. Resolving the axes separately is what makes a
tank driving diagonally into a wall *slide* along it instead of sticking.

Assumes a single step moves less than one tile, which config.MAX_DT
guarantees at any sane speed.
"""

from __future__ import annotations

import math
from typing import Protocol

from ..world.tiles import TileType

# Keeps a pushed-back box a hair away from the tile edge, so floor() of its
# edge doesn't land back inside the solid tile on the next check.
_EPS = 1e-4


class TileSource(Protocol):
    def tile_at(self, tx: int, ty: int) -> TileType: ...


def box_hits_solid(world: TileSource, x: float, y: float, hw: float, hh: float) -> bool:
    """True if the box centered at (x, y) with half-extents (hw, hh) overlaps
    any solid tile."""
    tx0, tx1 = math.floor(x - hw), math.floor(x + hw - _EPS)
    ty0, ty1 = math.floor(y - hh), math.floor(y + hh - _EPS)
    for ty in range(ty0, ty1 + 1):
        for tx in range(tx0, tx1 + 1):
            if world.tile_at(tx, ty).solid:
                return True
    return False


def move_box(
    world: TileSource, x: float, y: float, hw: float, hh: float, dx: float, dy: float
) -> tuple[float, float, bool, bool]:
    """Move a box by (dx, dy) against the tile grid.

    Returns (new_x, new_y, blocked_x, blocked_y).
    """
    blocked_x = blocked_y = False

    if dx:
        nx = x + dx
        if box_hits_solid(world, nx, y, hw, hh):
            blocked_x = True
            if dx > 0:
                # Right edge ran into the tile column containing it: sit just
                # left of that column.
                nx = math.floor(nx + hw - _EPS) - hw - _EPS
            else:
                nx = math.floor(nx - hw) + 1 + hw + _EPS
            # If snapping still overlaps (e.g. we started inside something),
            # don't move at all on this axis.
            if box_hits_solid(world, nx, y, hw, hh):
                nx = x
        x = nx

    if dy:
        ny = y + dy
        if box_hits_solid(world, x, ny, hw, hh):
            blocked_y = True
            if dy > 0:
                ny = math.floor(ny + hh - _EPS) - hh - _EPS
            else:
                ny = math.floor(ny - hh) + 1 + hh + _EPS
            if box_hits_solid(world, x, ny, hw, hh):
                ny = y
        y = ny

    return x, y, blocked_x, blocked_y
