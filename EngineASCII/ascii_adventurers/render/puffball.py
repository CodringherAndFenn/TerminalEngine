"""
render/puffball.py -- Mycelium the giant puffball, its halves, its mines,
spore clouds and the wind, its leaps, rolls and mortars (M26.3).

It's painted (render/painted.paint_puffball), cracking open each phase;
split, its halves are the same picture, smaller. Its tells, in pale cream
(design/BOSSES.md 5.3):
  * a leap: a ring of "o" where it (or a half) lands, it arcing over;
  * roll: a dotted line with ">";
  * puff (mines, rings, mortars): puffed up; mortars' rings where they land;
  * breath: puffed up, mouth open; the clouds then drift off downwind;
  * squash: squashed flat;
  * split: pinched in two.
Mines are little white puffballs; a lit fuse blinks red with "!". From phase
3 the wind shows as streaks drifting across the screen, and WIND with which
way it blows over you.
"""

from __future__ import annotations

import math

import pygame

from .. import config, palette
from ..engine_ext.camera import Camera
from .ascii_fx import _Batch, _ring
from .characters import draw_character
from .fallout import _hash01
from .magus import _dotted, _px_ring
from .sprites import SpriteBank

SCALE = 6
HALF_SCALE = 4


def _paint_mine(r: int, lit: bool):
    def paint(surf, to_px):
        c = to_px(0, 0)
        if lit:
            pygame.draw.circle(surf, palette.MINE_COL[1], c, r + 2)
        pygame.draw.circle(surf, palette.PUFFBALL["edge"], c, r + 1)
        pygame.draw.circle(surf, palette.MINE_COL[0], c, r)
        pygame.draw.circle(surf, palette.PUFFBALL["skin_shade"], (c[0] + r // 3, c[1] + r // 3),
                           max(1, r // 2))
        pygame.draw.circle(surf, palette.PUFFBALL["shine"], (c[0] - r // 3, c[1] - r // 3),
                           max(1, r // 4))
    return paint


def _pose(boss, body=None) -> str:
    kind = boss.tell[0] if boss.tell is not None else None
    look = min(boss.phase, 2)
    b = body or boss
    if body is None and boss.dazed > 0:
        act = "dizzy"
    elif b.airborne > 0:
        act = "air"
    elif body is None and (boss.squashed or kind == "squash"):
        act = "squash"
    elif body is None and (boss.dashing or kind == "roll"):
        act = "roll"
    elif body is None and kind == "breath":
        act = "breath"
    elif body is None and kind == "split":
        act = "split"
    else:
        act = ""
    return f"{look}:{act}"


def _wind_glyph(a: float) -> str:
    """A streak along angle `a` (y down): "-", "\\", "|" or "/"."""
    return ("-", "\\", "|", "/")[round(a / (math.pi / 4)) % 4]


def draw_puffball(text, bank: SpriteBank, camera: Camera, boss) -> None:
    """It, and everything it's put on the field."""
    batch = _Batch(text)
    t = boss.time
    blink = int(t * 8) % 2
    # The wind (phase 3): streaks drifting across the view.
    if boss.phase >= 2:
        glyph = _wind_glyph(boss.wind)
        wx, wy = math.cos(boss.wind), math.sin(boss.wind)
        w, h = camera.view_w, camera.view_h
        for k in range(28):
            u = (_hash01(k, 3) * w + wx * t * 120) % w
            v = (_hash01(k, 7) * h + wy * t * 120) % h
            batch.put_c(u, v, glyph, palette.WIND_COL)
    for c in boss.clouds:                           # (spore clouds)
        fade = c[2] / c[3]
        col = palette.DUST_COL[1 if fade > 0.7 else 0]
        _px_ring(batch, camera, c[0], c[1], c[4], 16, "*", col, t * 0.4)
        for k in range(14):
            a = _hash01(k, round(c[0] * 9)) * math.tau + t * 0.7
            d = math.sqrt(_hash01(k, round(c[1] * 9))) * c[4] * 0.9
            px, py = camera.world_to_px(c[0] + math.cos(a) * d, c[1] + math.sin(a) * d)
            batch.put_c(px, py, "`" if (k + int(t * 5)) % 3 else "*", palette.DUST_COL[k % 3])
    for l in boss.lobs:                             # (mortars in flight)
        if l[4] >= l[5]:
            continue
        f = max(0.0, l[4] / l[5])
        _px_ring(batch, camera, l[2], l[3], config.PUFF_MORTARS[2], 12, "o",
                 palette.TELEGRAPH[blink], t)
        if l[4] >= 0:
            sx, sy = camera.world_to_px(l[0] + (l[2] - l[0]) * f, l[1] + (l[3] - l[1]) * f)
            batch.put_c(sx, sy - 4 * 60 * f * (1 - f), "@", palette.DUST_COL[2])
    for b in [boss] + list(boss.halves):            # (where a leap lands)
        if b.landing is not None:
            r = config.BOUND_LAND[0] if b is boss else config.SPLIT_HALF[2]
            _px_ring(batch, camera, *b.landing, r, 14, "o", palette.TELEGRAPH[blink], t)
    tell = boss.tell
    if tell is not None and tell[0] == "roll":
        _dotted(batch, camera, *tell[1:5], palette.PUFF_TELL[blink], mark=">")
    for m in boss.mines:                            # (fuses lit: "!")
        if m.alive and m.age > 0:
            px, py = camera.world_to_px(m.x, m.y)
            batch.put_c(px, py - 16, "!", palette.MINE_COL[1] if blink else palette.MINE_COL[0])
    batch.flush()
    for m in boss.mines:
        if m.alive:
            px, py = camera.world_to_px(m.x, m.y)
            lit = m.age > 0 and blink
            bank.draw(bank.static(f"puff_mine_{int(lit)}", _paint_mine(6, lit), 9), px, py)

    # It -- or its two halves.
    if boss.halves:
        for h in boss.halves:
            if not h.alive:
                continue
            x, y = camera.world_to_px(h.x, h.y)
            lift = math.sin(h.hop * math.pi) * 50 if h.airborne > 0 else 0.0
            draw_character(bank, x, y - HALF_SCALE - lift, "mycelium_puffball", HALF_SCALE,
                           False, int(t * 4) % 4, h.hurt_flash > 0, _pose(boss, h))
        return
    x, y = camera.world_to_px(boss.x, boss.y)
    lift = math.sin(boss.hop * math.pi) * 70 if boss.airborne > 0 else 0.0
    frame = int(boss.rolled * 0.8) % 4 if (boss.dashing or boss.move == "roll") else int(t * 4) % 4
    draw_character(bank, x, y - SCALE - lift, "mycelium_puffball", SCALE,
                   math.cos(boss.facing) < 0, frame, boss.hurt_flash > 0, _pose(boss))


def draw_puff_marks(text, bank: SpriteBank, camera: Camera, boss, hero, time: float) -> None:
    """From phase 3: WIND and which way it blows, over you."""
    if boss.phase < 2:
        return
    batch = _Batch(text)
    hx, hy = camera.world_to_px(hero.x, hero.y)
    d = round(boss.wind / (math.pi / 4)) % 8
    way = (">", "v>", "v", "<v", "<", "<^", "^", "^>")[d]
    s = f"WIND {way}"
    cw = text.display.cell_w
    batch.put_px(hx - len(s) * cw / 2, hy - 54, s, palette.WIND_COL, palette.HUD_PANEL)
    batch.flush()
