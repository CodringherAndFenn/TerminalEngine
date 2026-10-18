"""
render/inkcap.py -- Mycelium the shaggy ink cap ("the Lawyer"), its ink
(puddles, the flowing pool, blots), its scrawled letters, ink-cap sprouts,
cracks and lobbed ink, the blindness of being inked, and the ink imp's and
mycologist's pictures (M26.2).

It's painted (render/painted.paint_inkcap), more of its cap turning to ink
each phase. Its tells, in pale blue (design/BOSSES.md 5.3):
  * melt: it slumps; the bubbling spot where it'll reform ("o" rings) shows
    from the start, and the pool flows there;
  * rear (blots, ink spray, scales, clusters): it tilts back; rings show
    where lobbed ink lands (blots' rings are bigger, with "@");
  * write: the letters of its word appear one by one, an ink blot round each;
  * sink (burst up): a ring of cracks under you;
  * shake: its cap shaking.
Ink on the floor is "%" in dark blue with a pale rim. Inked, everything
beyond INK_SIGHT tiles of you goes dark.
"""

from __future__ import annotations

import math

import pygame

from .. import config, palette
from ..engine_ext.camera import Camera
from .ascii_fx import _Batch, _ring
from .characters import ART, draw_character
from .fallout import _hash01
from .magus import _px_ring
from .plains_art import _pad
from .sprites import SpriteBank

SCALE = 6
LIFT = SCALE

ART["ink_imp"] = _pad([
    "...k...k",
    "..kJk.kJk",
    "..kJJJJJk",
    ".kJwkJwkJk",
    ".kJJJJJJJk",
    "..kJkkkJk",
    ".kJJJJJJJk",
    "kJ.kJJJk.Jk",
    "...kJ.Jk",
    "..kJk.kJk",
    "..kk...kk",
])


def _pose(boss) -> str:
    kind = boss.tell[0] if boss.tell is not None else None
    look = min(boss.phase, 2)
    act = {"melt": "melt", "rear": "rear", "write": "write", "shake": "shake",
           "sink": "sink"}.get(kind, "")
    if boss.shaking:
        act = "shake"
    return f"{look}:{act}"


def _ink(batch, camera: Camera, x: float, y: float, r: float, seed: int, n: int | None = None):
    """A splat of ink: "%" in dark blue over the area, a pale rim."""
    n = n or max(6, int(r * r * 3))
    _px_ring(batch, camera, x, y, r, max(8, int(r * 7)), ".", palette.INK_COL[2])
    for k in range(n):
        a = _hash01(k, seed, 3) * math.tau
        d = math.sqrt(_hash01(k, seed, 5)) * r * 0.9
        px, py = camera.world_to_px(x + math.cos(a) * d, y + math.sin(a) * d)
        batch.put_c(px, py, "%", palette.INK_COL[k % 2])


def draw_inkcap(text, bank: SpriteBank, camera: Camera, boss) -> None:
    """It, and everything it's put on the field."""
    batch = _Batch(text)
    t = boss.time
    blink = int(t * 8) % 2
    for p in boss.puddles:
        _ink(batch, camera, p[0], p[1], boss.puddle_radius(p), round(p[0] * 13 + p[1] * 7))
    for b in boss.blots:
        _ink(batch, camera, b[0], b[1], config.BLOT_RADIUS, round(b[0] * 11 + b[1] * 5))
        px, py = camera.world_to_px(b[0], b[1])
        batch.put_c(px, py, "@", palette.INK_COL[2])
    if boss.reform is not None:                    # (where it'll reform: bubbling)
        rr = 0.8 + (t * 2) % 1.4
        _px_ring(batch, camera, *boss.reform, rr, 10, "o", palette.INKCAP_TELL[blink], t)
    for g in boss.globs:
        f = max(0.0, g[4] / g[5]) if g[5] > 0 else 1.0
        blot = g[6] == "blot"
        r = config.BLOT_RADIUS if blot else config.INKCAP_SPRAY[2]
        _px_ring(batch, camera, g[2], g[3], r, 14 if blot else 10, "@" if blot else "o",
                 palette.TELEGRAPH[blink], t)
        if g[4] >= 0:
            sx, sy = camera.world_to_px(g[0] + (g[2] - g[0]) * f, g[1] + (g[3] - g[1]) * f)
            batch.put_c(sx, sy - 4 * 60 * f * (1 - f), "@", palette.INK_COL[2])
    if boss.crack_at is not None:
        _px_ring(batch, camera, *boss.crack_at, config.INKCAP_BURST[1], 16, ":",
                 palette.TELEGRAPH[blink], t)
    for x, y, ch, age in boss.letters:             # (the scrawl: big letters in ink)
        px, py = camera.world_to_px(x, y)
        for dx, dy, glyph, c in _ring(6, 14, ".", palette.INK_COL[0], age * 2):
            batch.put_c(px + dx, py + dy * 0.8, glyph, c)
        batch.put_c(px, py, ch, palette.SCRAWL_COL[blink if age > 0.3 else 1])
    for s in boss.sprouts:                         # (ink-cap sprouts, growing)
        if not s.alive:
            continue
        px, py = camera.world_to_px(s.x, s.y)
        g = min(1.0, s.age / config.CLUSTER_GROW)
        tall = 1 + int(g * 3)
        for k in range(tall):
            batch.put_c(px, py - k * 12, "||" if k < tall - 1 else "/\\",
                        palette.INKCAP["cap"] if k == tall - 1 else palette.INKCAP["stem"])
        if g > 0.7:
            batch.put_c(px, py + 12, "%%", palette.INK_COL[blink])
    batch.flush()

    x, y = camera.world_to_px(boss.x, boss.y)
    if boss.pooling:                               # (a pool of ink, flowing)
        batch = _Batch(text)
        _ink(batch, camera, boss.x, boss.y, config.POOL_RADIUS, int(t * 3))
        for k in range(3):
            a = t * 4 + k * 2.1
            batch.put_c(x + math.cos(a) * 16, y + math.sin(a) * 9, "o", palette.INK_COL[2])
        batch.flush()
        return
    if boss.submerged:                             # (burst up: under the ground)
        batch = _Batch(text)
        batch.put_c(x, y, "%%", palette.INK_COL[0])
        batch.flush()
        return
    frame = int(boss.walked * 1.3) % 4 if not boss.shaking else int(t * 12) % 4
    draw_character(bank, x, y - LIFT, "mycelium_inkcap", SCALE, math.cos(boss.facing) < 0, frame,
                   boss.hurt_flash > 0, _pose(boss))


_DARK: dict = {}


def _hole(rx: int, ry: int):
    """A dark square with a soft-edged clear ellipse in it (cached)."""
    key = (rx, ry)
    if key not in _DARK:
        surf = pygame.Surface((2 * rx, 2 * ry), pygame.SRCALPHA)
        surf.fill(palette.INK_DARK)
        steps = 6
        for k in range(steps):
            f = 1.0 - k / steps
            a = round(palette.INK_DARK[3] * f * f)
            rect = pygame.Rect(0, 0, round(2 * rx * (0.7 + 0.3 * f)), round(2 * ry * (0.7 + 0.3 * f)))
            rect.center = (rx, ry)
            pygame.draw.ellipse(surf, (*palette.INK_DARK[:3], a), rect)
        _DARK[key] = surf
    return _DARK[key]


def draw_ink_marks(text, bank: SpriteBank, camera: Camera, boss, hero, time: float) -> None:
    """While you're inked: dark beyond INK_SIGHT tiles of you (WIPE IT OFF:
    ROLL); where it'll reform while it flows."""
    if boss.blind(hero):
        canvas = text.display.canvas
        hx, hy = camera.world_to_px(hero.x, hero.y)
        rx = round(config.INK_SIGHT * config.TILE_PX_W)
        ry = round(config.INK_SIGHT * config.TILE_PX_H)
        hole = _hole(rx, ry)
        x0, y0 = round(hx - rx), round(hy - ry)
        w, h = canvas.get_size()
        dark = palette.INK_DARK[:3]
        canvas.fill(dark, pygame.Rect(0, 0, w, max(0, y0)))
        canvas.fill(dark, pygame.Rect(0, y0 + 2 * ry, w, max(0, h - y0 - 2 * ry)))
        canvas.fill(dark, pygame.Rect(0, y0, max(0, x0), 2 * ry))
        canvas.fill(dark, pygame.Rect(x0 + 2 * rx, y0, max(0, w - x0 - 2 * rx), 2 * ry))
        canvas.blit(hole, (x0, y0))
        batch = _Batch(text)
        s = "INKED! ROLL TO WIPE IT OFF"
        cw = text.display.cell_w
        batch.put_px(hx - len(s) * cw / 2, hy - ry - 30, s, palette.SCRAWL_COL[1],
                     palette.HUD_PANEL)
        batch.flush()
