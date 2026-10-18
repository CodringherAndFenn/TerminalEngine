"""
render/amanita.py -- Mycelium the fly agaric, its warts and flies, its
network's threads, trip clouds and fake shots, sprouts and slams, and the
truffle hunter's picture (M26.1).

It's painted (render/painted.paint_amanita); its warts are white blobs drawn
over its cap here, one per wart body still on. Its tells, in pale red
(design/BOSSES.md 5.3):
  * drink (regrowing warts): its threads glow; a DRINK bar;
  * sink (network): the whole path lit along the threads, then a mound
    moving along it while it's underground;
  * puff (spores, trip): pores open, spores rising;
  * stench (flies): wavy lines rising off it;
  * slam: its landing ring, it arcing over;
  * cracks (sprouts): ":" along the lines the toadstools will come up on;
  * spin: its cap tilting.
Threads show faintly between its rings all fight; a lit one glows. Trip
clouds are a ring of pink and white specks; while you're tripping, fake
shots (flickering, see-through) and a rainbow shimmer round you.
"""

from __future__ import annotations

import math

import pygame

from .. import config, palette
from ..engine_ext.camera import Camera
from .ascii_fx import SHOT_LOOKS, _Batch, _ring
from .characters import draw_character
from .fallout import _bar, _hash01, _nearest
from .magus import _dotted, _px_ring
from .sprites import SpriteBank

SCALE = 6
LIFT = SCALE                 # px: the figure sits so its stem's middle is on its spot



def _paint_wart(r: int):
    def paint(surf, to_px):
        c = to_px(0, 0)
        pygame.draw.circle(surf, palette.WART_COL[1], c, r + 1)
        pygame.draw.circle(surf, palette.WART_COL[0], c, r)
        pygame.draw.circle(surf, (255, 255, 255), (c[0] - r // 3, c[1] - r // 3), max(1, r // 3))
    return paint


def _pose(boss) -> str:
    kind = boss.tell[0] if boss.tell is not None else None
    look = min(boss.phase, 2)
    if boss.dazed > 0:
        act = "stun"
    elif boss.airborne > 0:
        act = "hop"
    elif boss.spinning or kind == "spin":
        act = "spin"
    elif kind == "drink":
        act = "drink"
    elif kind in ("puff", "stench"):
        act = "puff"
    else:
        act = ""
    return f"{look}:{act}"


def draw_amanita(text, bank: SpriteBank, camera: Camera, boss) -> None:
    """It, and everything it's put on the field."""
    batch = _Batch(text)
    t = boss.time
    blink = int(t * 8) % 2
    # The network's threads (from phase 2), the lit path.
    rings = boss.props.get("rings", [])
    if boss.phase >= 1:
        live = set(boss.live_rings())
        for p, q in boss.props.get("threads", []):
            if p in live and q in live:
                _dotted(batch, camera, *rings[p], *rings[q], palette.THREAD_COL[0], glyph=".",
                        step=1.6)
    if boss.lit:
        for k in range(len(boss.lit) - 1):
            _dotted(batch, camera, *boss.lit[k], *boss.lit[k + 1],
                    palette.THREAD_COL[1 + blink], glyph=":", step=0.8)
    # Trip clouds.
    radius, life = config.TRIP_CLOUD
    for c in boss.clouds:
        fade = c[2] / life
        _px_ring(batch, camera, c[0], c[1], radius, 18, "*",
                 palette.TRIP_CLOUD_COL[2 if fade > 0.7 else 0], t * 0.4)
        for k in range(16):
            a = _hash01(k, round(c[0] * 7)) * math.tau + t * 0.5
            d = math.sqrt(_hash01(k, round(c[1] * 7))) * radius * 0.9
            px, py = camera.world_to_px(c[0] + math.cos(a) * d, c[1] + math.sin(a) * d)
            batch.put_c(px, py, "'" if (k + int(t * 5)) % 3 else "*",
                        palette.TRIP_CLOUD_COL[k % 2])
    # Sprouts: fallen warts' toadstools, the sprouts' cracks and toadstools.
    for s in boss.sprouts:
        px, py = camera.world_to_px(s[0], s[1])
        late = s[2] > config.WART_SPROUT[0] - 0.8
        batch.put_c(px, py, "n", palette.WART_COL[0] if not late or blink else palette.TELEGRAPH[0])
    for x, y in boss.cracks:
        px, py = camera.world_to_px(x, y)
        batch.put_c(px, py, ":", palette.AMANITA_TELL[blink])
    for x, y, age in boss.shrooms:
        px, py = camera.world_to_px(x, y)
        batch.put_c(px, py - min(1.0, age * 6) * 8, "nn", palette.RING_SHROOM_FG)
        if age > config.AMANITA_SPROUTS[5] * 0.5:
            _px_ring(batch, camera, x, y, config.AMANITA_SPROUTS[6], 8, ".",
                     palette.TELEGRAPH[blink], t)
    if boss.slam_at is not None:
        _px_ring(batch, camera, *boss.slam_at, config.AMANITA_SLAM[1], 18, "o",
                 palette.TELEGRAPH[blink], t)
    batch.flush()

    # It: underground, a mound moving along the thread; else its figure, its
    # warts over its cap, its flies round it.
    x, y = camera.world_to_px(boss.x, boss.y)
    if boss.submerged:
        batch = _Batch(text)
        batch.put_c(x, y, "/^^\\", palette.THREAD_COL[1])
        batch.put_c(x, y - 14, "..", palette.SPILL_RED_FG)
        batch.flush()
        return
    lift = math.sin(boss.hop * math.pi) * 70 if boss.airborne > 0 else 0.0
    if boss.airborne > 0:
        bank.draw(bank.static("amanita_shadow", _paint_shadow(30), 34), x, y + 44)
    frame = int(boss.walked * 1.3) % 4 if not boss.spinning else int(t * 12) % 4
    draw_character(bank, x, y - LIFT - lift, "mycelium_amanita", SCALE,
                   math.cos(boss.facing) < 0, frame, boss.hurt_flash > 0, _pose(boss))
    wart = bank.static("amanita_wart", _paint_wart(5), 8)
    for w in boss.warts:
        if w is not None and w.alive:
            wx, wy = camera.world_to_px(w.x, w.y)
            bank.draw(wart, wx, wy - lift)
    batch = _Batch(text)
    for f in boss.flies:
        if f.alive:
            fx, fy = camera.world_to_px(f.x, f.y)
            batch.put_c(fx, fy, "w" if int(t * 14 + f.slot) % 2 else "v", palette.FLY_COL[0])
    kind = boss.tell[0] if boss.tell is not None else None
    if kind == "stench":
        for k in range(5):
            u = -40 + k * 20
            rise = (t * 40 + k * 13) % 50
            batch.put_c(x + u + math.sin(t * 6 + k) * 5, y - 70 - rise, "S",
                        palette.TRIP_CLOUD_COL[2])
    elif kind == "sink":
        for dx, dy, glyph, c in _ring(12, 40 + 6 * blink, ":", palette.THREAD_COL[1], t * 3, 0.4):
            batch.put_c(x + dx, y + 30 + dy, glyph, c)
    if kind == "drink":
        _bar(batch, x, y - 96, text.display.cell_w, 1.0 - (boss._wait / max(0.01,
             config.WART_REGROW[1])), 6, "DRINK", palette.AMANITA_TELL[0], palette.HUD_EMPTY)
    batch.flush()


def _paint_shadow(w: int):
    def paint(surf, to_px):
        cx, cy = to_px(0, 0)
        rect = pygame.Rect(round(cx - w), round(cy - w * 0.3), 2 * w, round(w * 0.6))
        pygame.draw.ellipse(surf, (0, 0, 0, 110), rect)
    return paint


def draw_ring_marks(text, bank: SpriteBank, camera: Camera, boss, hero, time: float) -> None:
    """Its network's live nodes (NODE, from phase 2), and -- while you're
    tripping -- the fake shots you see and a shimmer round you."""
    from .bosses import draw_pointer
    batch = _Batch(text)
    cw = text.display.cell_w
    if boss.phase >= 1:
        rings = boss.props.get("rings", [])
        for i in boss.live_rings():
            rx, ry = rings[i]
            px, py = camera.world_to_px(rx, ry)
            if -60 <= px <= camera.view_w + 60 and -60 <= py <= camera.view_h + 60:
                s = "NODE"
                batch.put_px(px - len(s) * cw / 2, py - 34, s, palette.NET_NODE_FG,
                             palette.HUD_PANEL)
        for i, left in boss.regrowing.items():
            rx, ry = rings[i]
            px, py = camera.world_to_px(rx, ry)
            s = f"REGROWS {math.ceil(left)}"
            batch.put_px(px - len(s) * cw / 2, py - 34, s, palette.MYCELIUM_FG, palette.HUD_PANEL)
    if boss.tripping(hero):
        flick = int(time * 10) % 3
        for f in boss.fakes:
            if (int(f[0] * 3) + flick) % 3 == 0:
                continue                           # (they flicker)
            head, _, col = SHOT_LOOKS.get(f[5], ("*", None, palette.SHOT_RED_SPORE))
            px, py = camera.world_to_px(f[0], f[1])
            c = col[0]
            batch.put_c(px, py, head or "*", (c[0] // 2 + 60, c[1] // 2 + 60, c[2] // 2 + 60))
        hx, hy = camera.world_to_px(hero.x, hero.y)
        for k in range(6):
            a = time * 4 + k * math.tau / 6
            batch.put_c(hx + math.cos(a) * 26, hy + math.sin(a) * 18, "*",
                        palette.TRIP_COL[(k + int(time * 6)) % 4])
    batch.flush()
    if boss.submerged and boss.lit:
        ex, ey = boss.lit[-1]
        draw_pointer(text, bank, camera, ex, ey,
                     f"IT RISES {math.hypot(ex - hero.x, ey - hero.y):.0f}", 30,
                     palette.THREAD_COL[1])
