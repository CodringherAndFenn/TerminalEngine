"""
render/feast.py -- the Host of the Feast, form 1 (M30.4, ai/feast.py): him
(render/pandemonium_art.py: his pictures standing, toasting, bowing,
spinning) and everything his hospitality puts on the floor:

  * his charm's reach (a faint rose ring round him);
  * the dance floor: the squares lit for this beat (gold light) and the
    next (dim), the unlit ones glowing red as a beat is about to land;
  * dishes sliding (a demon waiter carrying it, in the later rooms), the
    jellies (and the shadow where each will land), the cake tower's line;
  * marked circles: chandeliers ("*", glass), pouring coins ("$");
  * heaps of gold sliding across, coins tossed to you (catch them);
  * the beckoning's cone and pull, the carving set's aim.
"""

from __future__ import annotations

import math

import pygame

from .. import config, palette
from ..ai.feast import FeastHost
from .ascii_fx import _Batch
from .characters import draw_character

SCALE = 6


def _ring(batch, camera, x, y, r, n, glyph, color, turn=0.0) -> None:
    for k in range(n):
        a = turn + k * math.tau / n
        px, py = camera.world_to_px(x + math.cos(a) * r, y + math.sin(a) * r)
        batch.put_c(px, py, glyph, color)


def _line(batch, camera, x0, y0, x1, y1, glyph, color, step=0.8) -> None:
    n = max(1, int(math.hypot(x1 - x0, y1 - y0) / step))
    for k in range(n + 1):
        px, py = camera.world_to_px(x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n)
        batch.put_c(px, py, glyph, color)


def _floor(text, camera, h: FeastHost, view) -> None:
    """The dance floor's squares, lit from below (added light, so the floor
    still shows): bright for this beat, dim for the next; as a beat is
    about to land, the unlit ones glow red."""
    canvas = text.display.canvas
    fl = h.floor
    x0, y0, x1, y1 = h.floor_rect()
    cx, cy, a, b, _, _ = h._hall()
    size = config.HOST_DANCE[2]
    tw, th = config.TILE_PX_W, config.TILE_PX_H
    w, hh = size * tw - 4, size * th - 4
    nx, ny = math.ceil((x1 - x0) / size), math.ceil((y1 - y0) / size)
    vx0, vy0, vx1, vy1 = view
    i0, i1 = max(0, int((vx0 - x0) // size)), min(nx - 1, int((vx1 - x0) // size))
    j0, j1 = max(0, int((vy0 - y0) // size)), min(ny - 1, int((vy1 - y0) // size))
    landing = fl["beat"] < 0.3
    for j in range(j0, j1 + 1):
        for i in range(i0, i1 + 1):
            sx, sy = x0 + i * size, y0 + j * size
            if ((sx + size / 2 - cx) / a) ** 2 + ((sy + size / 2 - cy) / b) ** 2 > 0.97:
                continue                              # (past the hall's wall)
            if (i, j) in fl["now"]:
                col = palette.FEAST_FLOOR[0]
            elif (i, j) in fl["next"]:
                col = palette.FEAST_FLOOR[1]
            elif landing:
                col = palette.FEAST_FLOOR[2]
            else:
                continue
            px, py = camera.world_to_px(sx, sy)
            canvas.fill(col, (round(px) + 2, round(py) + 2, w, hh), special_flags=pygame.BLEND_ADD)


def draw_feast_host(text, bank, camera, h: FeastHost) -> None:
    t = h.time
    blink = int(t * 8) % 2
    vx0, vy0 = camera.canvas_to_world(0, 0)
    vx1, vy1 = camera.canvas_to_world(camera.view_w, camera.view_h)
    view = (vx0 - 4, vy0 - 4, vx1 + 4, vy1 + 4)
    if h.floor is not None:
        _floor(text, camera, h, view)
    batch = _Batch(text)
    _ring(batch, camera, h.x, h.y, config.HOST_CHARM[0], 30, ".", palette.FEAST_CHARM[1], t * 0.25)
    for w in h.walls:                                 # (heaps of gold, sliding)
        _line(batch, camera, w[0], w[1], w[2], w[3], "#" if blink else "$", palette.FEAST_GOLD[0], 0.6)
    for x, y, r, left, kind in h.marks:               # (chandeliers, pouring coins)
        col = palette.FEAST_GLASS[blink] if kind == "chandelier" else palette.FEAST_GOLD[blink]
        _ring(batch, camera, x, y, r, 12, "*" if kind == "chandelier" else "$", col, t)
        px, py = camera.world_to_px(x, y)
        batch.put_c(px, py - left * 60, "V" if kind == "chandelier" else "o", col)   # (falling)
        batch.put_c(px, py, "!", col)
    for x0, y0, x1, y1, left in h.cakes:             # (the cake tower about to topple)
        _line(batch, camera, x0, y0, x1, y1, ":", palette.FEAST_DISH["cake"], 0.7)
    for d in h.dishes:
        px, py = camera.world_to_px(d[1], d[2])
        col = palette.FEAST_DISH[d[0]]
        glyph = {"soup": "u", "roast": "@", "jelly": "o", "cake": "A"}[d[0]]
        if d[6]:                                      # (a demon waiter carrying it in)
            batch.put_c(px, py + 6, "w", palette.FEAST_WAITER)
            batch.put_c(px, py - 14, "_", palette.FEAST_GOLD[1])
            batch.put_c(px, py - 22, glyph, col)
        else:
            batch.put_c(px, py, "_", palette.FEAST_GOLD[1])
            batch.put_c(px, py - 8, glyph, col)
    for j in h.jellies:                               # (where each will land, and it, bouncing)
        frac = 1.0 - max(0.0, j[3]) / config.HOST_JELLY[2]
        px, py = camera.world_to_px(j[6], j[7])
        batch.put_c(px, py, "o", palette.FEAST_DISH["jelly"] if blink else palette.FEAST_STEP[1])
        jx, jy = j[4] + (j[6] - j[4]) * frac, j[5] + (j[7] - j[5]) * frac
        px, py = camera.world_to_px(jx, jy)
        batch.put_c(px, py - math.sin(frac * math.pi) * 30, "O", palette.FEAST_DISH["jelly"])
    for x, y, left in h.coins:                        # (tossed to you: catch one)
        px, py = camera.world_to_px(x, y)
        if left > 1.5 or blink:
            batch.put_c(px, py - abs(math.sin(t * 6 + x)) * 6, "$", palette.FEAST_COIN[blink])
    if h.cone is not None:                            # (the beckoning's slash to come)
        a, r, half = h.cone
        col = palette.PLAINS_TELL[1 if h.pulling and blink else 0]
        for k in range(9):
            b = a - half + 2 * half * k / 8
            px, py = camera.world_to_px(h.x + math.cos(b) * r, h.y + math.sin(b) * r)
            batch.put_c(px, py, ")" if math.cos(b) >= 0 else "(", col)
        if h.pulling:                                 # (the pull: lines at whoever it's drawing)
            for hero in h.heroes():
                if math.hypot(hero.x - h.x, hero.y - h.y) <= config.HOST_BECKON[2]:
                    _line(batch, camera, h.x, h.y, hero.x, hero.y, "~", palette.FEAST_CHARM[0], 1.4)
    if h.carve is not None:                           # (the carving set's aim)
        a = h.carve
        for k in range(1, 7):
            px, py = camera.world_to_px(h.x + math.cos(a) * k * 1.5, h.y + math.sin(a) * k * 1.5)
            batch.put_c(px, py, ".", palette.PLAINS_TELL[1])
    batch.flush()
    x, y = camera.world_to_px(h.x, h.y)
    sprite = {"toast": "host_of_feast_toast", "bow": "host_of_feast_bow",
              "spin": "host_of_feast_spin"}.get(h.pose, "host_of_feast")
    left = math.cos(h.facing) < 0 if h.pose != "spin" else int(h.spin) % 2 == 0
    draw_character(bank, x, y, sprite, SCALE, left, int(h.walked * 1.2) % 2, h.hurt_flash > 0)
    if h.tell is not None and h.planted and blink:
        batch = _Batch(text)
        batch.put_c(x, y - SCALE * 10, "!", palette.PLAINS_TELL[0])
        batch.flush()


def draw_feast_marks(text, camera, heroes) -> None:
    """On the heroes: a whirl round one swept into the Host's dance, a gold
    "$" over one gilded by a caught coin."""
    batch = _Batch(text)
    for h in heroes:
        if not h.alive:
            continue
        x, y = camera.world_to_px(h.x, h.y)
        if getattr(h, "swept", None) is not None and h.entranced > 0:
            a = h.time * 6.0
            for k in range(3):
                b = a + k * math.tau / 3
                batch.put_c(x + math.cos(b) * 16, y - 20 + math.sin(b) * 8, "~",
                            palette.FEAST_CHARM[0])
        if getattr(h, "time", 0.0) < getattr(h, "gilt_until", -1.0):
            batch.put_c(x, y - 44, "$", palette.FEAST_GILT)
    batch.flush()
