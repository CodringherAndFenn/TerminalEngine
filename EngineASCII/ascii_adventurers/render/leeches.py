"""
render/leeches.py -- the leech swarm, its leeches and tells, and the leech
doctor's bloated leeches and leechlings (M22).

A leech is a short segmented worm, drawn top-down along its heading (baked
per angle bucket by the SpriteBank); one that's latched on is gorged red.
The swarm's tells, in the telegraph red nothing else uses:
  * surge: a dotted line from the swarm along the way it'll dash;
  * spit: the swarm pulsing (rings round its middle) before the drops;
  * nest: rings of ripples on the pool it'll burst out of;
  * whirlpool: nothing extra -- the ring of leeches is the tell, and its
    gap is the way out.
"""

from __future__ import annotations

import math

import pygame

from .. import config, palette
from ..engine_ext.camera import Camera
from .ascii_fx import _Batch, _ring
from .sprites import SpriteBank


def _paint_leech(length: float, body: tuple, belly: tuple):
    """A leech `length` px long: three blobs tapering to the tail, a pale
    belly stripe, a darker sucker at the head."""
    def for_angle(a):
        def paint(surf, to_px):
            def rot(u, v):
                return (u * math.cos(a) - v * math.sin(a), u * math.sin(a) + v * math.cos(a))
            seg = length / 6
            for u, r in ((-2 * seg, seg * 0.9), (0, seg * 1.25), (2 * seg, seg)):
                x, y = to_px(*rot(u, 0))
                pygame.draw.circle(surf, palette.LEECH[0], (round(x), round(y)), max(1, round(r + 1)))
                pygame.draw.circle(surf, body, (round(x), round(y)), max(1, round(r)))
            x0, y0 = to_px(*rot(-2 * seg, 0))
            x1, y1 = to_px(*rot(2 * seg, 0))
            pygame.draw.line(surf, belly, (round(x0), round(y0)), (round(x1), round(y1)), 1)
            hx, hy = to_px(*rot(3 * seg, 0))
            pygame.draw.circle(surf, palette.LEECH[0], (round(hx), round(hy)), max(1, round(seg * 0.6)))
        return paint
    return for_angle


def _draw_leech(bank: SpriteBank, camera: Camera, x: float, y: float, facing: float,
                length: float, gorged: bool, hurt: bool, wriggle: float = 0.0) -> None:
    body = palette.HIT_FLASH if hurt else (palette.LEECH[2] if gorged else palette.LEECH[1])
    belly = palette.LEECH[2] if not gorged else palette.LEECH[1]
    sprite = bank.rotated(("leech", round(length), gorged, hurt), facing + math.sin(wriggle) * 0.25,
                          32, _paint_leech(length, body, belly), length * 0.7 + 4)
    px, py = camera.world_to_px(x, y)
    bank.draw(sprite, px, py)


def draw_leech_part(bank: SpriteBank, camera: Camera, part) -> None:
    """One leech of the swarm (not while it's nesting under a pool)."""
    if part.submerged:
        return
    wriggle = part.part_of.time * 9 + part.index
    _draw_leech(bank, camera, part.x, part.y, part.facing, 14, part.latched is not None,
                part.hurt_flash > 0, wriggle)


def draw_leech_creature(bank: SpriteBank, camera: Camera, e) -> None:
    """A bloated leech or a leechling (rearing up -- bigger -- while it
    winds up a bite)."""
    length = e.espec.size_px * (1.25 if e.windup > 0 else 1.0)
    _draw_leech(bank, camera, e.x, e.y, e.facing, length, e.espec.size_px > 16,
                e.hurt_flash > 0, e.wriggle)


def draw_swarm(text, camera: Camera, core) -> None:
    """The swarm's tells (its leeches are drawn as enemies of their own)."""
    tell = core.tell
    if tell is None:
        return
    batch = _Batch(text)
    blink = int(core.time * 8) % 2
    col = palette.LEECH_TELL[blink]
    tw, th = config.TILE_PX_W, config.TILE_PX_H
    if tell[0] == "line":
        _, x0, y0, x1, y1 = tell
        length = math.hypot(x1 - x0, y1 - y0)
        d = 1.5
        while d <= length:
            f = d / length
            x, y = camera.world_to_px(x0 + (x1 - x0) * f, y0 + (y1 - y0) * f)
            batch.put_c(x, y, ">" if int(d) % 3 == 0 else ".", col)
            d += 0.9
    elif tell[0] == "swell":
        cx, cy = camera.world_to_px(core.x, core.y)
        r = 30 + (core.time * 60) % 30
        for dx, dy, glyph, c in _ring(14, r, "o", col, core.time):
            batch.put_c(cx + dx, cy + dy * 0.8, glyph, c)
    elif tell[0] == "ripples":
        _, rx, ry = tell
        cx, cy = camera.world_to_px(rx, ry)
        for i, base in enumerate((1.2, 2.6, 4.0)):
            r = base + (core.time * 2.0) % 1.4
            c = palette.LEECH_TELL[(i + blink) % 2]
            n = int(8 + r * 5)
            for k in range(n):
                a = k * math.tau / n + i * 0.4
                batch.put_c(cx + math.cos(a) * r * tw, cy + math.sin(a) * r * th * 0.8,
                            "o" if i % 2 == 0 else ".", c)
    batch.flush()
