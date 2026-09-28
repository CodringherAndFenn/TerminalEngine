"""
ai/pathing.py -- a small, local path search, used only when frustrated.

Enemies normally steer with the clumsy probe-and-commit logic in
steering.py. Only when that has clearly failed (no progress for a while,
e.g. inside a U-shaped ruin) do they "think harder": a breadth-first search
over the tiles within `radius` of them, treating a tile as open if a body of
the given clearance fits there. It returns waypoints to the reachable tile
nearest the goal -- the goal itself if it's inside the search window,
otherwise just a better spot to try again from. So they still don't know
the whole map; they just stop banging into the same wall.

Speed (pure Python, so it matters):
  1. The window's terrain is read once into a flat 0/1 grid.
  2. A summed-area table over that grid makes "is there any solid tile in
     the (2c+1) x (2c+1) box around this tile?" one O(1) lookup instead of
     up to 25 tile reads.
  3. The BFS runs over flat integer indices.
A search over the default 25 x 25 window costs a couple of milliseconds.
"""

from __future__ import annotations

import math
from collections import deque

SEARCH_RADIUS = 12

_STEPS = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1))


def local_path(world, sx: float, sy: float, gx: float, gy: float,
               radius: int = SEARCH_RADIUS, clearance: int = 1) -> list[tuple[float, float]]:
    """Waypoints (tile centers) from (sx, sy) toward (gx, gy), or [] if no
    tile within the window gets closer than where we are."""
    stx, sty = math.floor(sx), math.floor(sy)
    gtx, gty = math.floor(gx), math.floor(gy)
    c = clearance
    # Terrain window, padded by the clearance so boxes near the edge work.
    ox, oy = stx - radius - c, sty - radius - c
    size = 2 * (radius + c) + 1
    tile_at = world.tile_at
    # Summed-area table: sat[y][x] = number of solid tiles in the window's
    # rectangle [0, x) x [0, y). Any box's solid count is 4 lookups.
    sat = [[0] * (size + 1) for _ in range(size + 1)]
    for y in range(size):
        row_sum = 0
        above, cur = sat[y], sat[y + 1]
        for x in range(size):
            row_sum += tile_at(ox + x, oy + y).solid
            cur[x + 1] = above[x + 1] + row_sum

    n = 2 * radius + 1          # BFS grid (unpadded), node (i, j) = tile (stx-r+i, sty-r+j)
    box = 2 * c + 1
    free = bytearray(n * n)
    for j in range(n):
        y0, y1 = j, j + box     # in padded-window coords: tile j-r+... padded by c
        r0, r1 = sat[y0], sat[y1]
        base = j * n
        for i in range(n):
            if r1[i + box] - r1[i] - r0[i + box] + r0[i] == 0:
                free[base + i] = 1

    start = radius * n + radius
    if not free[start]:
        free[start] = 1         # we're here, so it fits (collision says so)
    tgx, tgy = gtx - (stx - radius), gty - (sty - radius)   # goal in grid coords
    came = [-2] * (n * n)
    came[start] = -1
    q = deque([start])
    best, best_d = start, (tgx - radius) ** 2 + (tgy - radius) ** 2
    while q:
        cur = q.popleft()
        cj, ci = divmod(cur, n)
        d = (tgx - ci) ** 2 + (tgy - cj) ** 2
        if d < best_d:
            best, best_d = cur, d
            if d == 0:
                break
        for dx, dy in _STEPS:
            ni, nj = ci + dx, cj + dy
            if not (0 <= ni < n and 0 <= nj < n):
                continue
            nxt = nj * n + ni
            if came[nxt] != -2 or not free[nxt]:
                continue
            # No cutting corners diagonally past a wall.
            if dx and dy and not (free[cj * n + ni] and free[nj * n + ci]):
                continue
            came[nxt] = cur
            q.append(nxt)
    if best == start:
        return []
    path = []
    node = best
    while node != start:
        j, i = divmod(node, n)
        path.append((stx - radius + i + 0.5, sty - radius + j + 0.5))
        node = came[node]
    path.reverse()
    # Every other tile is plenty for the steering to follow, but always keep
    # the final tile.
    waypoints = path[1::2]
    if not waypoints or waypoints[-1] != path[-1]:
        waypoints.append(path[-1])
    return waypoints
