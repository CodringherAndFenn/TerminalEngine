"""
systems/collision.py -- rotated tank hull vs. the tile grid.

The hull is a rectangle (hull_length_px x hull_width_px) turned to the
tank's heading -- exactly the shape that's drawn -- so a tank at 45 degrees
can no longer poke its corners into walls.

Geometry runs in PIXEL space (1 tile = TILE_PX_W x TILE_PX_H), because a
rectangle in pixel space is not a rectangle in tile units (tiles aren't
square), and the drawn hull is a true rectangle on screen.

Overlap test: Separating Axis Theorem. Two convex shapes are disjoint iff
there's an axis on which their projections don't overlap; for a rotated
rectangle vs. an axis-aligned one, only 4 axes can separate them: the tile's
x and y axes and the hull's own length (u) and width (v) axes. Touching
edges don't count as overlap.

Movement is resolved one axis at a time (x, then y). If the full step on an
axis would overlap, a short binary search finds the furthest safe fraction,
so the hull stops flush against the wall (no visible gap) -- and because
the other axis still moves, driving diagonally into a wall slides along it.
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


# Directions tried when nudging a turning hull off a wall (unit vectors).
_NUDGE_DIRS = [(math.cos(k * math.pi / 4), math.sin(k * math.pi / 4)) for k in range(8)]


def try_turn(
    world: TileSource, x: float, y: float, old_angle: float, new_angle: float,
    hl: float, hw: float,
) -> tuple[float, float, float]:
    """Rotate a hull from old_angle to new_angle if it fits.

    If the new heading would overlap a wall, look for the smallest nudge
    (up to config.TURN_NUDGE_MAX tiles, 8 directions) that makes it fit --
    like the tank shoving itself off the wall as it turns. If nothing fits,
    the turn is refused for this frame. Returns (x, y, angle).
    """
    if not hull_hits_solid(world, x, y, new_angle, hl, hw):
        return x, y, new_angle
    if hull_hits_solid(world, x, y, old_angle, hl, hw):
        return x, y, new_angle  # already stuck; don't make it worse by refusing
    step = 0.04
    dist = step
    while dist <= config.TURN_NUDGE_MAX + 1e-9:
        for ux, uy in _NUDGE_DIRS:
            nx, ny = x + ux * dist, y + uy * dist
            if not hull_hits_solid(world, nx, ny, new_angle, hl, hw):
                return nx, ny, new_angle
        dist += step
    return x, y, old_angle
