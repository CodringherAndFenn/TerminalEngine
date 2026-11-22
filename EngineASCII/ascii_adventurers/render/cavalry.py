"""
render/cavalry.py -- the Serene Cavalry (M29.4, ai/cavalry.py): its four
riders (white knights on white horses, render/paradise_art.py) and what
its moves show:

  * the formation charge's lanes (dots while they line up, a bright line
    while they charge) and a trample's line;
  * the carousel's tightening ring; the halo rain's marked circles;
  * lances in the air (and where each will stick), the fences of light
    between the pillars of a cage;
  * the hymn: a gold ring round them while the chord holds, notes rising,
    the lead singer glowing;
  * the four winds: the corner about to blow (flashing), the gust's
    streaks across the cage, the calm spots.
"""

from __future__ import annotations

import math

from .. import config, palette
from ..ai.cavalry import Cavalry, Rider
from .ascii_fx import _Batch
from .forest import _dots
from .mounts import draw_rider, gallop_frame

RIDER_SCALE = 4


def _ring(batch, camera, x, y, r, n, glyph, color, turn=0.0) -> None:
    for k in range(n):
        a = turn + k * math.tau / n
        px, py = camera.world_to_px(x + math.cos(a) * r, y + math.sin(a) * r)
        batch.put_c(px, py, glyph, color)


def _line(batch, camera, x0, y0, x1, y1, glyph, color, step=0.7) -> None:
    n = max(1, int(math.hypot(x1 - x0, y1 - y0) / step))
    for k in range(n + 1):
        px, py = camera.world_to_px(x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n)
        batch.put_c(px, py, glyph, color)


def draw_cavalry_rider(text, bank, camera, r: Rider) -> None:
    x, y = camera.world_to_px(r.x, r.y)
    draw_rider(bank, x, y, "white_knight", "white_horse", RIDER_SCALE, r.facing_left(),
               gallop_frame(r), r.hurt_flash > 0)
    core = r.part_of
    if r.lead and core.hymn is not None:                  # (the lead singer)
        batch = _Batch(text)
        t = core.time
        batch.put_c(x, y - 88, "*" if int(t * 6) % 2 else "+", palette.HYMN[0])
        batch.put_c(x + 16, y - 70 - (t * 30) % 20, "'", palette.HYMN[0])
        batch.flush()


def draw_cavalry(text, bank, camera, c: Cavalry) -> None:
    batch = _Batch(text)
    t = c.time
    blink = int(t * 8) % 2
    for x0, y0, x1, y1 in c.lanes:                        # (formation)
        if c.charging:
            _line(batch, camera, x0, y0, x1, y1, "=", palette.LANE[1 if blink else 0], 0.8)
        else:
            _line(batch, camera, x0, y0, x1, y1, ":", palette.LANE[0], 0.6)
            px, py = camera.world_to_px(x1, y1)
            batch.put_c(px, py, ">" if x1 >= x0 else "<", palette.LANE[1])
    if c.line is not None:                                # (trample)
        x0, y0, x1, y1 = c.line
        _dots(batch, camera, x0, y0, math.atan2(y1 - y0, x1 - x0), math.hypot(x1 - x0, y1 - y0),
              palette.PLAINS_TELL[1])
    if c.ring is not None:                                # (carousel)
        x, y, r = c.ring
        _ring(batch, camera, x, y, r, 32, ".", palette.LANE[0], t * 0.5)
    for x, y, r in c.marks:                               # (halo rain)
        _ring(batch, camera, x, y, r, 14, "o" if blink else "*", palette.GOLD, t)
        px, py = camera.world_to_px(x, y)
        batch.put_c(px, py, "@", palette.GOLD)
    for x0, y0, x1, y1, s, of in c.lances:                # (lances in the air)
        f = s / of
        px, py = camera.world_to_px(x0 + (x1 - x0) * f, y0 + (y1 - y0) * f)
        batch.put_c(px, py - math.sin(math.pi * f) * 50, "|", palette.LANE[1])
        tx, ty = camera.world_to_px(x1, y1)
        batch.put_c(tx, ty, "x" if f > 0.6 and blink else "+", palette.LANE[1])
    for x0, y0, x1, y1 in c.fences():                     # (fences of light)
        glyph = "|" if abs(x1 - x0) * 0.8 < abs(y1 - y0) else "-"
        _line(batch, camera, x0, y0, x1, y1, glyph, palette.FENCE[blink], 0.5)
    if c.hymn is not None and c.hymn["together"]:         # (the chord holds)
        n = len(c.riders)
        mx = sum(r.x for r in c.riders) / n
        my = sum(r.y for r in c.riders) / n
        _ring(batch, camera, mx, my, 4.5, 26, "*" if blink else "o", palette.HYMN[0], t)
        px, py = camera.world_to_px(mx, my)
        batch.put_c(px + 20, py - 60 - (t * 24) % 24, "'", palette.HYMN[1])
    w = c.winds
    if w is not None:                                     # (the four winds)
        for x, y in w["calm"]:
            _ring(batch, camera, x, y, config.CAV_WINDS[5], 12, "o", palette.CALM, t * 0.3)
        if w["next"] is not None:
            x, y = w["corners"][w["next"]]
            _ring(batch, camera, x, y, 2.5, 10, "*", palette.WIND[1 if blink else 0], t)
        if w["gust"] is not None:
            wx, wy = w["corners"][w["gust"]]
            ox, oy = w["centre"]
            a = math.atan2(oy - wy, ox - wx)
            ux, uy = math.cos(a), math.sin(a)
            for k in range(9):                            # (streaks across the cage)
                side = (k - 4) * 1.6
                along = ((t * 18 + k * 3.7) % 22) - 12     # (from behind the cage to past it)
                px, py = camera.world_to_px(ox + ux * along - uy * side, oy + uy * along + ux * side)
                batch.put_c(px, py, "-" if abs(ux) > abs(uy) else "|", palette.WIND[0])
    batch.flush()
