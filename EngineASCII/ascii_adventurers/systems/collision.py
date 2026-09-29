"""
systems/collision.py -- a character's box (optionally rotated) vs. the tile grid.

Characters and creatures collide as a square box (size_px), unrotated. The
test itself supports any rotated rectangle, which is why it takes an angle.

Geometry runs in PIXEL space (1 tile = TILE_PX_W x TILE_PX_H), because a
rectangle in pixel space is not a rectangle in tile units (tiles aren't
square).

Overlap test: Separating Axis Theorem. Two convex shapes are disjoint iff
there's an axis on which their projections don't overlap; for a rotated
rectangle vs. an axis-aligned one, only 4 axes can separate them: the tile's
x and y axes and the box's own length (u) and width (v) axes. Touching
edges don't count as overlap.

Movement is resolved one axis at a time (x, then y). If the full step on an
axis would overlap, a short binary search finds the furthest safe fraction,
so the box stops flush against the wall (no visible gap) -- and because
the other axis still moves, walking diagonally into a wall slides along it.
"""

from __future__ import annotations

import math
from typing import Protocol

from .. import config
from ..world.tiles import TileType

_EPS = 1e-6          # pixels; touching is not overlapping
_SEARCH_STEPS = 10   # binary search: 1/1024 of a step, well under a pixel


class TileSource(Protocol):
    def tile_at(self, tx: int, ty: int) -> TileType: ...


def screen_angle(world_angle: float) -> float:
    """World angle -> the same direction measured in pixel space."""
    return math.atan2(
        math.sin(world_angle) * config.TILE_PX_H, math.cos(world_angle) * config.TILE_PX_W
    )


def hull_hits_solid(
    world: TileSource, x: float, y: float, angle: float, half_len: float, half_wid: float
) -> bool:
    """True if a hull centered at world (x, y), heading `angle` (world
    radians), with half-length/half-width in pixels, overlaps a solid tile."""
    tw, th = config.TILE_PX_W, config.TILE_PX_H
    if angle == 0.0:
        # Unrotated box (every character): the SAT test reduces to the two
        # tile axes, so only tiles really overlapping it (not just touching)
        # are looked at. Tile tx overlaps the box's x span [cx-hl, cx+hl]
        # iff tx*tw < cx+hl and (tx+1)*tw > cx-hl, less _EPS for touching.
        cx, cy = x * tw, y * th
        tile_at = world.tile_at
        tx0 = math.floor((cx - half_len + _EPS) / tw)
        tx1 = math.ceil((cx + half_len - _EPS) / tw)
        ty0 = math.floor((cy - half_wid + _EPS) / th)
        ty1 = math.ceil((cy + half_wid - _EPS) / th)
        for ty in range(ty0, ty1):
            for tx in range(tx0, tx1):
                if tile_at(tx, ty).solid:
                    return True
        return False
    s = screen_angle(angle)
    c, sn = math.cos(s), math.sin(s)
    ac, asn = abs(c), abs(sn)
    cx, cy = x * tw, y * th
    # Half-size of the hull's axis-aligned bounding box: which tiles to test.
    ex = ac * half_len + asn * half_wid
    ey = asn * half_len + ac * half_wid
    # A tile's half-size projected onto the hull's u and v axes (the same for
    # every tile, since tiles don't rotate).
    rhw, rhh = tw / 2, th / 2
    r_u = rhw * ac + rhh * asn
    r_v = rhw * asn + rhh * ac

    for ty in range(math.floor((cy - ey) / th), math.floor((cy + ey) / th) + 1):
        for tx in range(math.floor((cx - ex) / tw), math.floor((cx + ex) / tw) + 1):
            if not world.tile_at(tx, ty).solid:
                continue
            dx = (tx + 0.5) * tw - cx      # tile center relative to hull center
            dy = (ty + 0.5) * th - cy
            if abs(dx) >= ex + rhw - _EPS:                       # tile x axis
                continue
            if abs(dy) >= ey + rhh - _EPS:                       # tile y axis
                continue
            if abs(dx * c + dy * sn) >= half_len + r_u - _EPS:   # hull length
                continue
            if abs(-dx * sn + dy * c) >= half_wid + r_v - _EPS:  # hull width
                continue
            return True
    return False


def _furthest_safe(world, x, y, angle, hl, hw, dx, dy) -> float:
    """Largest fraction f of (dx, dy) in [0, 1) that keeps the hull clear,
    assuming f = 0 is clear and f = 1 is not."""
    lo, hi = 0.0, 1.0
    for _ in range(_SEARCH_STEPS):
        mid = (lo + hi) / 2
        if hull_hits_solid(world, x + dx * mid, y + dy * mid, angle, hl, hw):
            hi = mid
        else:
            lo = mid
    return lo


def move_hull(
    world: TileSource, x: float, y: float, angle: float, hl: float, hw: float,
    dx: float, dy: float,
) -> tuple[float, float, bool, bool]:
    """Move a hull by (dx, dy) world tiles against the grid.

    Returns (new_x, new_y, blocked_x, blocked_y). If the hull already
    overlaps something (it shouldn't), it's allowed to move freely so it
    can escape rather than lock up.
    """
    if hull_hits_solid(world, x, y, angle, hl, hw):
        return x + dx, y + dy, False, False
    blocked_x = blocked_y = False
    if dx:
        if hull_hits_solid(world, x + dx, y, angle, hl, hw):
            blocked_x = True
            x += dx * _furthest_safe(world, x, y, angle, hl, hw, dx, 0.0)
        else:
            x += dx
    if dy:
        if hull_hits_solid(world, x, y + dy, angle, hl, hw):
            blocked_y = True
            y += dy * _furthest_safe(world, x, y, angle, hl, hw, 0.0, dy)
        else:
            y += dy
    return x, y, blocked_x, blocked_y
