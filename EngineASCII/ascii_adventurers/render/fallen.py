"""
render/fallen.py -- The Fallen, the still grove's lookalike trees, its roots,
sap, sweeps and maw, the grove's markers, and the mimic sapling's, bark
beetle's and lumberjack's pictures (M25.3).

It's painted (render/painted.paint_fallen). The grove's trees are the same
figure posed as a tree ("still"), drawn by draw_groves whatever the quest's
stage; while it hides it's drawn in that pose too, at its tree, mirrored
like the tree it took -- only its eye opening ("blink") gives it away. Its
tells, in pale green (design/BOSSES.md 5.3):
  * hide: arms up, leaves swirling ("*") over every tree it may become;
  * roots: the ground cracking at its feet (":" round them), then the roots
    themselves growing out ("%", their tips bright); a root holding
    someone glows red with SHOOT IT;
  * sweep: the arc it will sweep, dotted, its arm drawn back;
  * charge: a dotted line with ">";
  * maw: its trunk splitting, then a SAP bar while it's open;
  * throw (sap): rings where the globs land, the globs arcing over;
  * cast (leaf storm): "*" round it.
"""

from __future__ import annotations

import math

import pygame

from .. import config, palette
from ..engine_ext.camera import Camera
from .ascii_fx import _Batch, _ring
from .characters import ART, draw_character
from .fallout import _bar, _hash01, _nearest
from .magus import _dotted, _px_ring
from .plains_art import _pad
from .sprites import SpriteBank

SCALE = 6

ART["mimic_sapling"] = _pad([
    "...g.G.g",
    "..gGgGgGg",
    "...GgGgG",
    "....kTk",
    "...kTyTk",
    "...kTTTk",
    "..kTkwkTk",
    ".kT.kTk.Tk",
    ".k..kTk..k",
    "...kT.Tk",
    "..kT...Tk",
    "..kk...kk",
])
ART["bark_beetle"] = _pad([
    "....k...k",
    ".....k.k",
    "...kkkkkk",
    "..kTtTtTtk",
    ".kTtTkTtTyk",
    ".kTtTkTtTkk",
    "..kTtTtTtk",
    "..k.k.k.k",
])


def _flip(i: int) -> bool:
    """Which way a grove tree faces (the same every run, per tree)."""
    return _hash01(i, 7, 3) < 0.5


def _paint_shadow(w: int):
    def paint(surf, to_px):
        cx, cy = to_px(0, 0)
        rect = pygame.Rect(round(cx - w), round(cy - w * 0.3), 2 * w, round(w * 0.6))
        pygame.draw.ellipse(surf, (0, 0, 0, 90), rect)
    return paint


def _pose(boss) -> str:
    kind = boss.tell[0] if boss.tell is not None else None
    look = min(boss.phase, 2)
    if boss.hid_at is not None:
        return f"0:{'blink' if boss.eye_open > 0 else 'still'}"
    if boss.dazed > 0:
        act = "stun"
    elif boss.maw_open or kind == "maw":
        act = "maw"
    elif boss.arc is not None:
        act = "sweep" if boss.sweep_at is None else "swing"
    elif boss.dashing or kind == "charge":
        act = "charge"
    elif kind in ("cast", "roots", "hide", "throw"):
        act = "cast"
    else:
        act = ""
    return f"{look}:{act}"


def draw_groves(text, bank: SpriteBank, camera: Camera, quests, time: float) -> None:
    """The still grove's lookalike trees, wherever the quest is (all but the
    one it's posing as: it draws itself)."""
    x0, y0 = camera.canvas_to_world(0, 0)
    x1, y1 = camera.canvas_to_world(camera.view_w, camera.view_h)
    for s in quests.states.values():
        lair = s.lair
        if lair.key != "still_grove" or lair.x0 > x1 + 6 or lair.x0 + lair.w < x0 - 6 \
                or lair.y0 > y1 + 8 or lair.y0 + lair.h < y0 - 8:
            continue
        boss = s.boss if s.stage == "fight" and s.boss is not None and s.boss.alive else None
        for i, (tx, ty) in enumerate(lair.props.get("trees", [])):
            if not (x0 - 4 <= tx <= x1 + 4 and y0 - 6 <= ty <= y1 + 6):
                continue
            if boss is not None and boss.hid_at == i:
                continue
            px, py = camera.world_to_px(tx, ty)
            jig = 0.0
            if boss is not None and i in boss.lashing:
                jig = math.sin(time * 70 + i) * 4
            draw_character(bank, px + jig, py, "the_fallen", SCALE, _flip(i), 0, False, "0:still")


def draw_fallen(text, bank: SpriteBank, camera: Camera, boss) -> None:
    """It, and everything it's put on the field."""
    batch = _Batch(text)
    t = boss.time
    blink = int(t * 8) % 2
    tw, th = config.TILE_PX_W, config.TILE_PX_H
    # Sap puddles, globs in flight.
    radius = config.FALLEN_SAP[2]
    for p in boss.puddles:
        col = palette.SAP_COL[0 if p[2] < config.FALLEN_SAP[3] * 0.75 else 1]
        _px_ring(batch, camera, p[0], p[1], radius, 14, "o", col, t * 0.3)
        for k in range(8):
            a = _hash01(k, round(p[0] * 5)) * math.tau
            d = math.sqrt(_hash01(k, round(p[1] * 5))) * radius * 0.85
            px, py = camera.world_to_px(p[0] + math.cos(a) * d, p[1] + math.sin(a) * d)
            batch.put_c(px, py, ":", col)
    for g in boss.globs:
        f = max(0.0, g[4] / g[5]) if g[5] > 0 else 1.0
        _px_ring(batch, camera, g[2], g[3], radius, 12, "o", palette.TELEGRAPH[blink], t)
        if g[4] >= 0:
            sx, sy = camera.world_to_px(g[0] + (g[2] - g[0]) * f, g[1] + (g[3] - g[1]) * f)
            batch.put_c(sx, sy - 4 * 60 * f * (1 - f), "@", palette.SAP_COL[0])
    # Roots: "%" along each, the growing tip bright; one holding someone red.
    held = {id(v[0]) for v in boss.held.values()}
    for r in boss.roots:
        x0, y0, x1, y1 = boss.root_seg(r)
        if r[6] > 0:
            col = palette.FIRE_LIT_FG
        elif id(r) in held:
            col = palette.ROOT_HELD
        else:
            col = palette.ROOT_COL[1 if r[5] < config.ROOT_LIFE - 1.5 else 2]
        length = r[3]
        d = 0.5
        k = 0
        while d < length:
            wob = math.sin(d * 1.3 + r[2] * 5) * 0.3
            px, py = camera.world_to_px(x0 + math.cos(r[2]) * d - math.sin(r[2]) * wob,
                                        y0 + math.sin(r[2]) * d + math.cos(r[2]) * wob)
            batch.put_c(px, py, "%" if k % 2 == 0 else ":", col)
            d += 0.7
            k += 1
        if r[3] < r[4] and r[6] <= 0:
            px, py = camera.world_to_px(x1, y1)
            batch.put_c(px, py, "%", palette.ROOT_COL[0])
    tell = boss.tell
    kind = tell[0] if tell is not None else None
    if kind == "charge":
        _dotted(batch, camera, *tell[1:5], palette.FALLEN_TELL[blink], mark=">")
    if boss.arc is not None:
        a, reach, half, way = boss.arc
        for k in range(15):
            aa = a - half + 2 * half * k / 14
            px, py = camera.world_to_px(boss.x + math.cos(aa) * reach, boss.y + math.sin(aa) * reach)
            batch.put_c(px, py, ".", palette.TELEGRAPH[blink])
        if boss.sweep_at is not None:
            for k in range(1, 8):
                px, py = camera.world_to_px(boss.x + math.cos(boss.sweep_at) * reach * k / 7,
                                            boss.y + math.sin(boss.sweep_at) * reach * k / 7)
                batch.put_c(px, py, "#", palette.FALLEN_TELL[0])
    if kind == "roots":
        px, py = camera.world_to_px(boss.x, boss.y + 1.8)
        for dx, dy, glyph, c in _ring(10, 30 + 6 * blink, ":", palette.ROOT_COL[0], t * 3, 0.5):
            batch.put_c(px + dx, py + dy, glyph, c)
    # Leaves swirling over the trees it may become.
    if boss.flurry:
        for k, (fx, fy) in enumerate(boss.flurry):
            px, py = camera.world_to_px(fx, fy)
            for j in range(10):
                a = t * 5 + j * math.tau / 10 + k
                batch.put_c(px + math.cos(a) * (24 + j * 2), py - 20 + math.sin(a) * 30, "*",
                            palette.LEAF_FLURRY[(j + k) % 3])
    batch.flush()

    # It.
    x, y = camera.world_to_px(boss.x, boss.y)
    if boss.hid_at is None:
        bank.draw(bank.static("fallen_shadow", _paint_shadow(26), 30), x, y + 50)
        frame = int(boss.walked * 1.2) % 4 if boss.dazed <= 0 else int(t * 3) % 4
        left = math.cos(boss.facing) < 0
    else:
        frame, left = 0, _flip(boss.hid_at)
    draw_character(bank, x, y, "the_fallen", SCALE, left, frame,
                   boss.hurt_flash > 0 and boss.hid_at is None, _pose(boss))
    batch = _Batch(text)
    if boss.maw_open:
        _bar(batch, x, y - 92, text.display.cell_w, boss.choke_frac(), 10, "SAP",
             palette.SAP_COL[0], palette.HUD_EMPTY)
    elif boss.dazed > 0 and boss.hid_at is None:
        for dx, dy, glyph, c in _ring(5, 22, "*", palette.FALLEN_TELL[0], t * 4, 0.4):
            batch.put_c(x + dx, y - 64 + dy, glyph, c)
    if kind == "cast":
        for dx, dy, glyph, c in _ring(8, 52 + 4 * blink, "*", palette.FALLEN_TELL[0], t * 6):
            batch.put_c(x + dx, y + dy, glyph, c)
    batch.flush()


def draw_grove_marks(text, bank: SpriteBank, camera: Camera, boss, hero, time: float) -> None:
    """While its roots are out: the fire bowls (FIRE, a ring) and an arrow to
    the nearest; a root holding someone: SHOOT THE ROOT!"""
    from .bosses import draw_pointer
    batch = _Batch(text)
    blink = int(time * 6) % 2
    cw = text.display.cell_w
    fires = boss.props.get("fires", [])
    if boss.roots:
        for fx, fy in fires:
            px, py = camera.world_to_px(fx, fy)
            if not (-60 <= px <= camera.view_w + 60 and -60 <= py <= camera.view_h + 60):
                continue
            _px_ring(batch, camera, fx, fy, config.FIRE_SEAR, 14, "+",
                     palette.FIRE_LIT_FG if blink else palette.SAP_COL[1], time)
            s = "FIRE"
            batch.put_px(px - len(s) * cw / 2, py - 36, s, palette.FIRE_LIT_FG, palette.HUD_PANEL)
    for k, (r, _, _) in boss.held.items():
        x0, y0, x1, y1 = boss.root_seg(r)
        px, py = camera.world_to_px((x0 + x1) / 2, (y0 + y1) / 2)
        s = "SHOOT THE ROOT!"
        batch.put_px(px - len(s) * cw / 2, py - 30, s, palette.ROOT_HELD, palette.HUD_PANEL)
    batch.flush()
    if boss.roots and fires:
        fx, fy = _nearest(fires, hero.x, hero.y)
        draw_pointer(text, bank, camera, fx, fy,
                     f"FIRE {math.hypot(fx - hero.x, fy - hero.y):.0f}", 20, palette.FIRE_LIT_FG)
