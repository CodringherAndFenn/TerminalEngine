"""
render/horsemen.py -- the Four Horsemen (M29.5, ai/horsemen.py): each on
its flayed horse (render/paradise_art.py), and what its moves show:

  * an arrow volley's or a blood charge's line (dots), a slash's arc;
  * the duel's ring of blood (closing while it's shown);
  * Famine's marked weights, its hunger (a dark ring round it), its scales
    tipping; Death's darkened quarter and the spinning scythe, and Hades,
    a dark maw following it;
  * a banner's burning ground (render/paradise.draw_paradise_tells calls
    draw_banner);
and, on the heroes: a crown while crowned, a struck-out "+" while healing
is blocked, the duel's mark.
"""

from __future__ import annotations

import math

from .. import palette
from ..ai.horsemen import ConquestBanner, Horseman
from .ascii_fx import _Batch
from .forest import _dots
from .mounts import draw_rider, gallop_frame

SCALE = 4
LOOKS = {"conquest": ("conquest", "flayed_white"), "war": ("war", "flayed_red"),
         "famine": ("famine", "flayed_black"), "death": ("death", "flayed_pale")}


def _ring(batch, camera, x, y, r, n, glyph, color, turn=0.0) -> None:
    for k in range(n):
        a = turn + k * math.tau / n
        px, py = camera.world_to_px(x + math.cos(a) * r, y + math.sin(a) * r)
        batch.put_c(px, py, glyph, color)


def draw_horseman(text, bank, camera, h: Horseman) -> None:
    x, y = camera.world_to_px(h.x, h.y)
    batch = _Batch(text)
    t = h.time
    blink = int(t * 8) % 2
    if h.kit == "death":                                  # (Hades, a dark maw, behind it)
        mx, my = camera.world_to_px(h.x - math.cos(h.facing) * 3.2,
                                    h.y - math.sin(h.facing) * 2.4)
        for dx, dy, g in ((-12, -6, "("), (12, -6, ")"), (0, -10, "^"), (0, 4, "v"),
                          (-6, -2, "w"), (6, -2, "w")):
            batch.put_c(mx + dx, my + dy, g, palette.HADES[blink])
    if h.has("hunger"):
        from .. import config
        _ring(batch, camera, h.x, h.y, config.HUNGER, 30, ".", palette.HUNGER, t * 0.2)
    batch.flush()
    rider, mount = LOOKS[h.kit]
    draw_rider(bank, x, y, rider, mount, SCALE, h.facing_left(), gallop_frame(h),
               h.hurt_flash > 0)
    batch = _Batch(text)
    if h.aim_line is not None:
        x0, y0, x1, y1 = h.aim_line
        _dots(batch, camera, x0, y0, math.atan2(y1 - y0, x1 - x0), math.hypot(x1 - x0, y1 - y0),
              palette.PLAINS_TELL[1])
    if h.arc is not None:
        a, reach, half = h.arc
        for k in range(9):
            b = a - half + 2 * half * k / 8
            px, py = camera.world_to_px(h.x + math.cos(b) * reach, h.y + math.sin(b) * reach)
            batch.put_c(px, py, ")" if math.cos(b) >= 0 else "(", palette.WAR_RED[blink])
    if h.ring is not None:
        cx, cy, r, left = h.ring
        shown = r + left * 6.0                            # (it closes in while it's shown)
        _ring(batch, camera, cx, cy, shown, 36, "o" if left <= 0 else ".", palette.WAR_RED[0],
              t * 0.3)
    for wx, wy in h.weights:
        _ring(batch, camera, wx, wy, 1.3, 10, "*" if blink else ".", palette.WEIGHT_MARK, t)
        px, py = camera.world_to_px(wx, wy)
        batch.put_c(px, py, "!", palette.WEIGHT_MARK)
    if h.quarter is not None:                             # (a quarter darkening: get out)
        cx, cy, r, q, left = h.quarter
        col = palette.QUARTER[0 if left > 0.5 or blink else 1]
        for ring in range(1, 9):
            n = 3 + ring * 2
            for k in range(n):
                a = q * math.tau / 4 + (k + 0.5) * (math.tau / 4) / n
                px, py = camera.world_to_px(cx + math.cos(a) * r * ring / 8,
                                            cy + math.sin(a) * r * ring / 8)
                batch.put_c(px, py, "▓" if ring == 8 else "░", col)
    if h.scythe is not None:
        from .. import config
        reach = config.HM_REAP[2]
        for k in range(1, 6):
            px, py = camera.world_to_px(h.x + math.cos(h.scythe) * reach * k / 5,
                                        h.y + math.sin(h.scythe) * reach * k / 5)
            batch.put_c(px, py, "-" if abs(math.cos(h.scythe)) > 0.5 else "|", palette.SCYTHE)
    if h.weighed is not None:
        _, lost, _ = h.weighed
        batch.put_c(x - 10, y - 96, "\\" if lost else "/", palette.SCALES)
        batch.put_c(x, y - 98, "T", palette.SCALES)
        batch.put_c(x + 10, y - 96, "/" if lost else "\\", palette.SCALES)
    if h.planted and int(t * 6) % 2:
        batch.put_c(x, y - 104, "!", palette.PLAINS_TELL[0])
    batch.flush()


def draw_banner(batch, camera, b: ConquestBanner) -> None:
    """A banner's burning ground: its circle, flickering."""
    col = palette.BANNER_FIRE[int(b.clock * 8) % 2]
    n = max(12, int(b.radius * 6))
    _ring(batch, camera, b.x, b.y, b.radius, n, "^" if int(b.clock * 4) % 2 else "*", col,
          b.clock * 0.4)


def draw_horsemen_marks(text, camera, heroes, enemies=()) -> None:
    """On the heroes: a crown while crowned (half damage), a struck "+"
    while healing is blocked (hunger, Hades), the duel; their relics' (the
    Ring of Blood's ring, the Black Scales tipping). On enemies: a crown
    while a Crown of Conquest's holds."""
    batch = _Batch(text)
    for e in enemies:
        by = getattr(e, "crowned_by", None)
        if by is not None and e.alive and by.time < getattr(e, "crown_until", -1.0):
            x, y = camera.world_to_px(e.x, e.y)
            batch.put_c(x - 6, y - 50, "w", palette.GOLD)
            batch.put_c(x + 6, y - 50, "w", palette.GOLD)
    for h in heroes:
        if not h.alive:
            continue
        x, y = camera.world_to_px(h.x, h.y)
        if getattr(h, "crowned", False):
            batch.put_c(x - 6, y - 52, "w", palette.GOLD)
            batch.put_c(x + 6, y - 52, "w", palette.GOLD)
        if getattr(h, "time", 0.0) < getattr(h, "starved_until", -1.0):
            batch.put_c(x + 16, y - 40, "+", palette.HUNGER)
            batch.put_c(x + 16, y - 40, "/", palette.WAR_RED[0])
        if getattr(h, "duel", None) is not None:
            batch.put_c(x - 16, y - 40, "x", palette.WAR_RED[0])
        ring = getattr(h, "blood_ring", None)
        if ring is not None:
            _ring(batch, camera, ring["x"], ring["y"], ring["r"], 32, "o", palette.WAR_RED[0],
                  getattr(h, "time", 0.0) * 0.3)
        weighed = getattr(h, "weighed", None)
        if weighed is not None:
            _, lost, _ = weighed
            batch.put_c(x - 10, y - 62, "\\" if lost else "/", palette.SCALES)
            batch.put_c(x, y - 64, "T", palette.SCALES)
            batch.put_c(x + 10, y - 62, "/" if lost else "\\", palette.SCALES)
    batch.flush()


def draw_pale_allies(bank, camera, heroes) -> None:
    """The Pale Rider's Cloak's shades, fighting for their hero."""
    from .characters import draw_character
    from .. import config
    for h in heroes:
        for s in getattr(h, "pale", ()):
            x, y = camera.world_to_px(s["x"], s["y"])
            frame = int(s["walked"] * config.WALK_STEPS_PER_TILE) % 4
            draw_character(bank, x, y, "pale_shade", 2, math.cos(s["facing"]) < 0, frame, False)
