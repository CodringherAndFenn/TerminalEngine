"""
render/beetle.py -- Khepri the Dung Emperor, his dung ball, and the
scarabs (M23.1).

Beetles are drawn top-down along their heading (baked per angle bucket by
the SpriteBank): a domed shell split down the middle with a shine on it, a
plated thorax, a toothed head with a horn, and six legs that walk while
they move. Khepri opens his shell and spreads his wings for the dust storm.
His ball is a lumpy brown sphere flecked with straw, baked per size (a
tenth of a tile) and turned as it rolls.

His tells, in their own orange (design/BOSSES.md 5.3):
  * roll: a dotted lane as wide as the ball, from the ball to where it'll
    stop;
  * charge: a dotted line with ">" along it;
  * a new ball: dust kicked up round it;
  * burrow: "^" where the sand moves over him, then a blinking ring where
    he'll come up;
  * dust storm: his wings out, "%" swirling round him;
  * scarab call: a pulsing ring;
  * stars over his head while he's stunned (the time to hit him).
A golden scarab glints; digging in, it's half sunk in dust.
"""

from __future__ import annotations

import math

import pygame

from .. import config, palette
from ..engine_ext.camera import Camera
from .ascii_fx import _Batch, _ring
from .sprites import SpriteBank

KHEPRI_SCALE = 2.3           # his body: ~115 px horn to tail
SCARAB_SCALE = 0.5
_K = palette.KHEPRI


def _paint_beetle(colors: dict, scale: float, frame: int, hurt: bool, wings: bool = False,
                  horn: bool = True):
    """A beetle facing +x (rotated per bucket). `frame`: the walk cycle's
    leg pose (0 / 1), `wings`: shell open, wings spread."""
    def for_angle(a):
        ca, sa = math.cos(a), math.sin(a)

        def paint(surf, to_px):
            def P(u, v):
                u, v = u * scale, v * scale
                x, y = to_px(u * ca - v * sa, u * sa + v * ca)
                return round(x), round(y)

            def oval(u0, v0, ru, rv, color, n=16):
                pts = [P(u0 + math.cos(t) * ru, v0 + math.sin(t) * rv)
                       for t in (k * math.tau / n for k in range(n))]
                pygame.draw.polygon(surf, color, pts)

            flash = palette.HIT_FLASH if hurt else None
            shell = flash or colors["shell"]
            edge = colors["edge"]
            w = max(1, round(scale * 1.2))
            # Legs: three pairs, alternating with the walk frame.
            for side in (-1, 1):
                for k, (u0, out, sweep) in enumerate(((10, 12, 8), (2, 15, 0), (-8, 13, -9))):
                    step = (2.5 if (k + frame + (side > 0)) % 2 else -2.5)
                    knee = P(u0 + sweep * 0.4 + step, side * out)
                    foot = P(u0 + sweep + step, side * (out + 7))
                    root = P(u0, side * 6)
                    pygame.draw.line(surf, colors["leg"], root, knee, w)
                    pygame.draw.line(surf, colors["leg"], knee, foot, w)
            if wings:
                for side in (-1, 1):            # membrane wings behind the open shell
                    pts = [P(4, side * 4), P(-6, side * 26), P(-26, side * 22), P(-20, side * 6)]
                    pygame.draw.polygon(surf, colors.get("wing", (200, 200, 160, 120)), pts)
            # Shell (elytra): split down the middle; open, the halves swing out.
            spread = 5 if wings else 0
            for side in (-1, 1):
                oval(-6, side * (6 + spread), 17, 7.5, edge)
                oval(-6, side * (6 + spread), 15.5, 6.5, shell)
                pygame.draw.line(surf, flash or colors["shine"], P(-14, side * (5 + spread)),
                                 P(2, side * (8 + spread)), w)
            # Thorax and head.
            oval(12, 0, 7, 10, edge)
            oval(12, 0, 6, 9, shell)
            pygame.draw.line(surf, flash or colors["shine"], P(10, -5), P(14, -2), w)
            oval(20, 0, 4, 6, edge)
            for t in (-4, -2, 0, 2, 4):          # the toothed head (a dung beetle's rake)
                pygame.draw.line(surf, edge, P(22, t), P(25, t * 1.2), w)
            if horn:
                pygame.draw.line(surf, colors.get("horn", edge), P(20, 0), P(30, 0),
                                 max(1, round(scale * 2)))
            if "eye" in colors:
                for side in (-1, 1):
                    pygame.draw.circle(surf, colors["eye"], P(19, side * 4),
                                       max(1, round(scale * 1.2)))
        return paint
    return for_angle


def _paint_ball(r_px: float):
    """A dung ball r_px screen pixels round, turned to the bucket's angle
    (it rolls: the lumps and straw go round)."""
    base, dark, light, straw = palette.DUNG

    def for_angle(a):
        def paint(surf, to_px):
            cx, cy = to_px(0, 0)
            pygame.draw.circle(surf, dark, (round(cx), round(cy)), round(r_px))
            pygame.draw.circle(surf, base, (round(cx), round(cy)), max(1, round(r_px - 2)))
            for k in range(7):                   # lumps
                t = a + k * 2.4
                d = r_px * (0.25 + 0.5 * ((k * 37) % 7) / 7)
                pygame.draw.circle(surf, dark if k % 2 else light,
                                   (round(cx + math.cos(t) * d), round(cy + math.sin(t) * d)),
                                   max(1, round(r_px * 0.16)))
            for k in range(5):                   # straw
                t = a + k * 1.7 + 0.5
                d = r_px * 0.6
                x0, y0 = cx + math.cos(t) * d, cy + math.sin(t) * d
                pygame.draw.line(surf, straw, (round(x0), round(y0)),
                                 (round(x0 + math.cos(t + 1.2) * r_px * 0.3),
                                  round(y0 + math.sin(t + 1.2) * r_px * 0.3)))
            # A highlight (fixed: the light comes from the top left).
            pygame.draw.circle(surf, light, (round(cx - r_px * 0.35), round(cy - r_px * 0.35)),
                               max(1, round(r_px * 0.18)))
        return paint
    return for_angle


def draw_scarab(bank: SpriteBank, camera: Camera, e) -> None:
    """A scarab add, or a golden scarab (digging in: half sunk; gone:
    nothing)."""
    state = getattr(e, "state", "")
    if state == "gone":
        return
    golden = state != ""
    x, y = camera.world_to_px(e.x, e.y)
    moving = (getattr(e, "phase", 0.0) or getattr(e, "wriggle", 0.0))
    frame = int(moving * 1.5) % 2
    colors = palette.GOLD_SCARAB if golden else palette.SCARAB
    key = ("gscarab" if golden else "scarab", frame, e.hurt_flash > 0)
    sprite = bank.rotated(key, e.facing, 32,
                          _paint_beetle(colors, SCARAB_SCALE, frame, e.hurt_flash > 0,
                                        horn=False), 16)
    bank.draw(sprite, x, y + (6 if state == "dig" else 0))
    if golden and int(e.phase) % 5 == 0:         # a glint now and then
        bank.draw(bank.static("glint", _glint, 4), x + 4, y - 5)


def _glint(surf, to_px):
    cx, cy = to_px(0, 0)
    c = palette.GOLD_SCARAB["shine"]
    pygame.draw.line(surf, c, (round(cx - 3), round(cy)), (round(cx + 3), round(cy)))
    pygame.draw.line(surf, c, (round(cx), round(cy - 3)), (round(cx), round(cy + 3)))


def draw_khepri(text, bank: SpriteBank, camera: Camera, boss) -> None:
    """Khepri, his ball, his tells."""
    batch = _Batch(text)
    blink = int(boss.time * 8) % 2
    col = palette.KHEPRI_TELL[blink]
    tw = config.TILE_PX_W
    tell = boss.tell
    kind = tell[0] if tell is not None else None
    if kind in ("roll", "charge"):
        x0, y0, x1, y1 = tell[1:5]
        width = tell[5] if kind == "roll" else 0.0
        length = math.hypot(x1 - x0, y1 - y0) or 1.0
        nx, ny = -(y1 - y0) / length, (x1 - x0) / length
        d = 1.0
        while d < length:
            f = d / length
            mx, my = x0 + (x1 - x0) * f, y0 + (y1 - y0) * f
            if kind == "roll":
                for side in (-1, 1):
                    px, py = camera.world_to_px(mx + nx * width * side, my + ny * width * side)
                    batch.put_c(px, py, ".", col)
                if int(d) % 3 == 0:
                    px, py = camera.world_to_px(mx, my)
                    batch.put_c(px, py, "=", col)
            else:
                px, py = camera.world_to_px(mx, my)
                batch.put_c(px, py, ">" if int(d) % 4 == 0 else ".", col)
            d += 0.9
        px, py = camera.world_to_px(x1, y1)
        batch.put_c(px, py, "x", col)
    elif kind == "erupt":
        _, rx, ry, radius = tell
        px, py = camera.world_to_px(rx, ry)
        for dx, dy, glyph, c in _ring(16, radius * tw, "x" if blink else "+", col, 0.0):
            batch.put_c(px + dx, py + dy * 0.8, glyph, c)
    if boss.ripple is not None:
        px, py = camera.world_to_px(*boss.ripple)
        for dx, dy, glyph, c in _ring(6, 18, "^", palette.BURROW_DUST[blink], boss.time * 3):
            batch.put_c(px + dx, py + dy * 0.6, glyph, c)
    batch.flush()

    # The ball (behind him when it's in front: drawn first).
    if boss.ball is not None:
        bx, by, r = boss.ball
        r_px = round(r * tw * 10) / 10
        sprite = bank.rotated(("dung", r_px), boss.spin, 16, _paint_ball(r_px), r_px + 2)
        px, py = camera.world_to_px(bx, by)
        bank.draw(sprite, px, py)

    if boss.submerged:
        return
    x, y = camera.world_to_px(boss.x, boss.y)
    frame = int(boss.legs) % 2
    hurt = boss.hurt_flash > 0
    sprite = bank.rotated(("khepri", frame, hurt, boss.wings), boss.facing, 32,
                          _paint_beetle(_K, KHEPRI_SCALE, frame, hurt, boss.wings),
                          34 * KHEPRI_SCALE)
    bank.draw(sprite, x, y)

    batch = _Batch(text)
    if kind == "gather" and boss.ball is not None:
        bx, by, r = boss.ball
        px, py = camera.world_to_px(bx, by)
        for dx, dy, glyph, c in _ring(8, r * tw + 10, ".", palette.BURROW_DUST[blink],
                                      boss.time * 4):
            batch.put_c(px + dx, py + dy * 0.7, glyph, c)
    elif kind == "dig":
        for dx, dy, glyph, c in _ring(10, 50, ".", palette.BURROW_DUST[blink], boss.time * 3):
            batch.put_c(x + dx, y + dy * 0.6, glyph, c)
    elif kind == "storm":
        for dx, dy, glyph, c in _ring(8, 70, "%", palette.SHOT_DUST[0], boss.time * 5):
            batch.put_c(x + dx, y + dy * 0.6, glyph, c)
    elif kind == "click":
        r = 40 + (boss.time * 70) % 30
        for dx, dy, glyph, c in _ring(14, r, "o", col, boss.time):
            batch.put_c(x + dx, y + dy * 0.8, glyph, c)
    if boss.dazed > 0:
        for k in range(3):
            a = boss.time * 4 + k * math.tau / 3
            batch.put_c(x + math.cos(a) * 30, y - 50 + math.sin(a) * 6, "*", palette.TOAST)
    batch.flush()
