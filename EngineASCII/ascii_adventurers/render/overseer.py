"""
render/overseer.py -- drawing the Overseer, form 1 (M32.4, ai/overseer.py):
its ceiling rail (a dotted ring), the eye hanging from it (its picture
dropping as it comes down low, the cable lengthening), its searchlight's
cone (magenta while it sees you), and what its signatures and moves show:
the cell's ring before the bars shut, the laser grid (faint, then on), the
sweep's arc and its beam, the salvo's lock-on marks and the missiles
coming down, the drop's electric ring and its arcs to the hall's pylons,
the floor scan's lit squares (light added to the floor: it still shows
through). Its recordings: the hero's own picture in flickering magenta
static.
"""

from __future__ import annotations

import math

import pygame

from .. import config, palette
from .ascii_fx import _Batch
from .characters import ART_H, ART_W, _picture, _walk_frame, draw_character
from .panopticon import _along, _beam_glyph, _blink, _ray, _ring

_TAU = 2.0 * math.pi


def draw_overseer(text, bank, camera, e) -> None:
    if e.form == 2:                                       # (M32.5: the walking city)
        from .walking_city import draw_walking_city
        draw_walking_city(text, bank, camera, e)
        return
    if e.form == "tearing":
        _draw_tearing(text, bank, camera, e)
        return
    batch = _Batch(text)
    tw, th = config.TILE_PX_W, config.TILE_PX_H
    cx, cy, ra, rb = e.arena()
    k = config.OVERSEER_RAIL[0]
    for q in range(72):                                   # (its ceiling rail)
        a = q * _TAU / 72
        px, py = camera.world_to_px(cx + math.cos(a) * ra * k, cy + math.sin(a) * rb * k)
        batch.put_c(px, py, "=" if q % 2 else "-", palette.RAIL[q % 2])
    if e.scan is not None:
        _scan(text, camera, e)
    if e.grid is not None:
        beams = e.grid_beams()
        if e.grid[1] < 0:
            for b in beams:
                _along(batch, camera, *b, 1.2, ".", palette.GRID_TELL)
        else:
            for k_, b in enumerate(beams):
                col = palette.GRID_BEAM[(int(e.real_t * 18) + k_) % 2]
                _along(batch, camera, *b, 0.5, _beam_glyph(b[2] - b[0], b[3] - b[1]), col)
    if e.lock is not None:                                # (the cell's ring: roll out)
        lx, ly, left = e.lock
        _ring(batch, camera, lx, ly, config.OVERSEER_CELLS[3], "|", _blink(left, palette.GRID_BEAM), 12)
    for mx, my, left in e.missiles:                       # (locked on, coming down)
        col = _blink(left, palette.MISSILE)
        _ring(batch, camera, mx, my, config.OVERSEER_SALVO[4], "+", col, 10)
        if left < 0.35:
            px, py = camera.world_to_px(mx, my)
            batch.put_c(px, py - left * 160, "V", palette.MISSILE[1])
    if e.sweep is not None:
        a0, a1, f, length = e.sweep
        if f < 0:
            col = palette.SWEEP_ARC[0]
            for a in (a0, a1):
                _ray(batch, camera, e.x, e.y, a, length, 1.4, ".", col)
            n = 14
            for q in range(n + 1):
                a = a0 + (a1 - a0) * q / n
                px, py = camera.world_to_px(e.x + math.cos(a) * length, e.y + math.sin(a) * length)
                batch.put_c(px, py, ".", palette.SWEEP_ARC[1])
        else:
            a = a0 + (a1 - a0) * f
            col = palette.WARDEN_BEAM[int(e.real_t * 20) % 2]
            _ray(batch, camera, e.x, e.y, a, length, 0.5, _beam_glyph(math.cos(a), math.sin(a)), col)
    if e.ring is not None:                                # (the drop's electric ring)
        _ring(batch, camera, e.x, e.y, e.ring, "o", palette.DROP_RING[int(e.real_t * 14) % 2])
    if e.arcs > 0:                                        # (arcs to the hall's pylons)
        for q, (px_, py_) in enumerate(e.pylons()):
            n = max(2, int(math.hypot(px_ - e.x, py_ - e.y) / 0.7))
            for s in range(n + 1):
                f = s / n
                w = (0.35 if (s + q + int(e.real_t * 20)) % 2 else -0.35) if 0 < s < n else 0.0
                ux, uy = px_ - e.x, py_ - e.y
                ll = math.hypot(ux, uy) or 1.0
                x = e.x + ux * f - uy / ll * w
                y = e.y + uy * f + ux / ll * w
                px, py = camera.world_to_px(x, y)
                batch.put_c(px, py, "*" if s % 3 == 0 else "/", palette.ARC[s % 2])
    if e.planted and e.low < 1.0 and e.ring is None and e.arcs <= 0:   # (coming down: the tell)
        px, py = camera.world_to_px(e.x, e.y)
        batch.put_c(px, py - 70, "!", palette.PLAINS_TELL[0] if int(e.real_t * 10) % 2 else
                    palette.DROP_RING[1])
    seeing = e.seeing                                     # (its searchlight: its two edges)
    half = math.radians(config.OVERSEER_GAZE[0]) / 2
    for side in (-1, 1):
        _ray(batch, camera, e.x, e.y, e.gaze_a + side * half, config.OVERSEER_GAZE[1], 1.6, ".",
             palette.EYE_GAZE[1 if seeing is not None else 0])
    if seeing is not None:                                # (an eye over the hero it sees)
        hx, hy = camera.world_to_px(seeing.x, seeing.y)
        batch.put_c(hx, hy - 52, "o", palette.SEEN_EYE[int(e.real_t * 6) % 2])
    x, y = camera.world_to_px(e.x, e.y)
    lift = (1.0 - e.low) * 18
    for q in range(4 if e.low < 0.5 else 7):              # (its cable up to the rail)
        batch.put_c(x, y - lift - e.espec.scale * 7 - q * th * 0.5, "|", palette.RAIL[0])
    batch.flush()
    if e.low < 0.5:                                       # (its shadow on the floor below)
        sh = _Batch(text)
        sh.put_c(x, y + 18, "___", palette.BOMB_SHADOW)
        sh.flush()
    draw_character(bank, x, y - lift, e.sprite_now(), e.espec.scale,
                   math.cos(e.facing) < 0, 0, e.hurt_flash > 0)


def _draw_tearing(text, bank, camera, e) -> None:
    """The eye tearing free (M32.5): down out of the ceiling, flickering
    between itself and the body it builds out of the hall, the hall's pieces
    flying in to it."""
    batch = _Batch(text)
    x, y = camera.world_to_px(e.x, e.y)
    left = max(0.0, e.tear_t) / config.WALKER_TEAR
    for q in range(10):                                   # (pieces flying in)
        a = q * _TAU / 10 + e.real_t * 0.7
        r = 40 + 160 * ((left * 3 + q * 0.37) % 1.0)
        batch.put_c(x + math.cos(a) * r, y - 30 + math.sin(a) * r * 0.6, "%#"[q % 2],
                    palette.HALL_PILLAR_FG if q % 2 else palette.CELL_DOOR_FG)
    batch.put_c(x, y + 18, "_____", palette.BOMB_SHADOW)
    batch.flush()
    built = int(e.real_t * 10) % 3 == 0 and left < 0.7 or left < 0.25
    sprite = "walking_city" if built else "overseer_low"
    scale = config.WALKER_BODY[1] if built else e.espec.scale
    draw_character(bank, x, y - (1.0 - left) * 30, sprite, scale, math.cos(e.facing) < 0, 0, False)


def _scan(text, camera, e) -> None:
    """The floor scan's lit squares, light added to the floor."""
    squares, left, struck = e.scan
    size = config.OVERSEER_SCAN[0]
    canvas = text.display.canvas
    col = palette.SCAN_LIT[1] if struck or left < 0.35 else palette.SCAN_LIT[0]
    if not struck and left >= 0.35 and int(left * 6) % 2:
        col = tuple(v // 2 for v in col)
    w, h = canvas.get_size()
    for x0, y0 in squares:
        ax, ay = camera.world_to_px(x0, y0)
        bx, by = camera.world_to_px(x0 + size, y0 + size)
        r = pygame.Rect(round(ax), round(ay), round(bx - ax) - 1, round(by - ay) - 1)
        if r.right < 0 or r.bottom < 0 or r.left > w or r.top > h:
            continue
        canvas.fill(col, r, special_flags=pygame.BLEND_RGB_ADD)


def _static(name: str, scale: int, flip: bool, frame: int, look, flick: int):
    """A painter for picture `name` as a recording: magenta static, its
    scanlines flickering (`flick` picks which)."""
    def paint(surf, to_px):
        base = _picture(name, False, look)
        img = pygame.Surface(base.get_size(), pygame.SRCALPHA)
        w, h = base.get_size()
        for py in range(h):
            col = palette.STATIC[(py + flick) % 2]
            for px in range(w):
                c = base.get_at((px, py))
                if c.a == 0:
                    continue
                lum = (c.r + c.g + c.b) / 3 / 255
                img.set_at((px, py), (round(col[0] * (0.4 + 0.6 * lum)), round(col[1] * (0.4 + 0.6 * lum)),
                                      round(col[2] * (0.4 + 0.6 * lum)), 190))
        img = _walk_frame(img, frame)
        if flip:
            img = pygame.transform.flip(img, True, False)
        img = pygame.transform.scale(img, (ART_W * scale, ART_H * scale))
        x, y = to_px(-ART_W * scale / 2, -ART_H * scale / 2)
        surf.blit(img, (round(x), round(y)))
    return paint


def draw_recording(text, bank, camera, e) -> None:
    """A copy of you, in magenta static (its scanlines flicker)."""
    x, y = camera.world_to_px(e.x, e.y)
    frame = int(e.walked * config.WALK_STEPS_PER_TILE) % 4 if e._moved > 1e-6 else 0
    flick = int(e.t * 10) % 2
    look = e.look
    key = f"rec:{e.sprite}:{getattr(look, 'key', '')}:{e.scale}:{int(e.left_side)}:{frame}:{flick}"
    reach = max(ART_W, ART_H) * e.scale / 2 + 1
    bank.draw(bank.static(key, _static(e.sprite, e.scale, e.left_side, frame, look, flick), reach), x, y)
