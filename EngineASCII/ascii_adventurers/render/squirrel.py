"""
render/squirrel.py -- Love & Cuddles, its mounds, wires, logs, pinecones
and cleaver blades, the hollow oak's markers, and the rabid squirrels'
picture (M25.2).

It's painted (render/painted.paint_love), its look going from adorable to
not with the phase (blood, a red eye, the grin). On the ground it has a
shadow; up an oak it's drawn in the crown, which shakes as the trunk is
hit (a meter over it). Its tells, in pink (design/BOSSES.md 5.3):
  * cleaver (spin): the cleaver raised, "!" over it;
  * puff (acorn barrage): cheeks stuffed, "o" round it;
  * throw (pinecones): a pinecone held back, then rings where they'll
    land ("x" in the middle) with the cones arcing over;
  * call (squirrel gang): a pulsing ring;
  * dig (bury): paws in the dirt, dirt flying;
  * string (tripwires): "-" spinning round it;
  * scurry (to a tree), leap (a dotted line with ">" to the next oak),
    pounce (a ring where it'll land), dash (frenzy: a dotted line, red);
  * frenzy: "!" in red all round it.
Mounds are a dirt hump with an acorn peeking out; wires a faint line with
glints running along it (red ":" while a log creaks), the log a "#" bar
swinging along it.
"""

from __future__ import annotations

import math

import pygame

from .. import config, palette
from ..engine_ext.camera import Camera
from .ascii_fx import _Batch, _ring
from .characters import ART, draw_character
from .fallout import _bar, _nearest
from .magus import _dotted, _px_ring
from .plains_art import _pad
from .sprites import SpriteBank

SCALE = 5
UP = 14              # px it sits up in an oak's crown (over the trunk: aim at it, hit the trunk)

ART["rabid_squirrel"] = _pad([
    ".kkk",
    "knnnk.....k.k",
    "knNnnk...knkn",
    "kknNnk..knnnnk",
    ".knnnk.knnrnwk",
    "..knnkknnnnnkk",
    "..knnnnnnnnk",
    "...knnnnnnk",
    "...kNk..kNk",
    "...kk...kk",
])


def _paint_shadow(w: int):
    def paint(surf, to_px):
        cx, cy = to_px(0, 0)
        rect = pygame.Rect(round(cx - w), round(cy - w * 0.3), 2 * w, round(w * 0.6))
        pygame.draw.ellipse(surf, palette.LOVE_SHADOW, rect)
    return paint


def _pose(boss) -> str:
    """Its look (the phase) and what it's doing, for paint_love."""
    kind = boss.tell[0] if boss.tell is not None else None
    if boss.panting:
        act = "pant"
    elif boss.dashing or kind in ("frenzy", "dash"):
        act = "frenzy"
    elif kind == "cleaver" or boss.spin is not None:
        act = "cleaver"
    elif kind in ("puff", "throw", "call"):
        act = kind
    elif kind in ("dig",) or boss.digging > 0:
        act = "dig"
    elif kind == "string":
        act = "call"
    else:
        act = ""
    return f"{min(boss.phase, 2)}:{act}"


def draw_love(text, bank: SpriteBank, camera: Camera, boss) -> None:
    """It, and everything it's put on the field."""
    batch = _Batch(text)
    t = boss.time
    blink = int(t * 8) % 2
    # Buried acorns: a hump of dirt, the acorn peeking out.
    for m in boss.mounds:
        px, py = camera.world_to_px(m[0], m[1])
        batch.put_c(px, py, "/\\", palette.MOUND_COL[0])
        batch.put_c(px, py - 10, "o", palette.MOUND_COL[1])
    # Wires: a faint line, glints running along it; a log's wire creaks red.
    for w in boss.wires:
        armed = w[4] >= 0.6
        col = palette.WIRE_COL[1] if armed else palette.WIRE_COL[0]
        _dotted(batch, camera, *w[:4], col, glyph="-", step=0.7)
        length = math.hypot(w[2] - w[0], w[3] - w[1]) or 1.0
        for k in range(max(1, int(length / 14))):
            f = ((t * 0.35 + k * 14 / length) % 1.0)
            px, py = camera.world_to_px(w[0] + (w[2] - w[0]) * f, w[1] + (w[3] - w[1]) * f)
            batch.put_c(px, py, "*" if blink else "+", palette.WIRE_COL[0])
    for g in boss.logs:
        at = boss.log_at(g)
        if at is None:
            _dotted(batch, camera, *g[:4], palette.TELEGRAPH[blink], glyph=":", step=1.0)
            continue
        px, py = camera.world_to_px(*at)
        batch.put_c(px, py, "[##]", palette.LOG_COL[0])
        batch.put_c(px, py - 14, "||", palette.LOG_COL[1])
    # Pinecones: a ring where each lands (tighter as it falls), the cone
    # arcing over.
    radius = config.LOVE_CONES[2]
    for c in boss.cones:
        f = max(0.0, c[4] / c[5]) if c[5] > 0 else 1.0
        _px_ring(batch, camera, c[2], c[3], radius, 12, "o", palette.TELEGRAPH[blink], t)
        px, py = camera.world_to_px(c[2], c[3])
        batch.put_c(px, py, "x", palette.LOVE_TELL[0])
        if c[4] >= 0:
            sx, sy = camera.world_to_px(c[0] + (c[2] - c[0]) * f, c[1] + (c[3] - c[1]) * f)
            batch.put_c(sx, sy - 4 * 60 * f * (1 - f), "@", palette.SHOT_ACORN[0])
    tell = boss.tell
    kind = tell[0] if tell is not None else None
    if kind == "dash":
        _dotted(batch, camera, *tell[1:5], palette.MADNESS_COL[blink], mark=">")
    if boss.leap is not None:
        _dotted(batch, camera, *boss.leap, palette.LOVE_TELL[blink], mark=">")
    if boss.pounce is not None:
        _px_ring(batch, camera, *boss.pounce, config.TREE_POUNCE[2], 14, "v",
                 palette.TELEGRAPH[blink], t)
    batch.flush()

    # It: in a tree's crown, or on the ground with its shadow.
    x, y = camera.world_to_px(boss.x, boss.y)
    frame = int(boss.walked * 1.5) % 4 if boss.dazed <= 0 else int(t * 3) % 4
    left = math.cos(boss.facing) < 0
    if boss.up and boss.leap is None:
        jig = math.sin(t * 60) * 4 if boss.shook > 0 else 0.0
        draw_character(bank, x + jig, y - UP, "love_cuddles", SCALE, left, frame,
                       boss.hurt_flash > 0, _pose(boss))
        crown = _Batch(text)
        for k in range(14):                          # leaves round it, shaking
            a = k * math.tau / 14
            r = 52 + (k % 3) * 6
            shake = math.sin(t * 50 + k) * 4 if boss.shook > 0 else 0.0
            crown.put_c(x + math.cos(a) * r + shake, y - UP + math.sin(a) * r * 0.6 + 10, "&",
                        palette.OAK_CROWN_FG)
        _bar(crown, x, y - UP - 90, text.display.cell_w, boss.shake_frac(), 10, "SHAKE",
             palette.LOVE_TELL[0], palette.HUD_EMPTY)
        crown.flush()
    else:
        lift = 0.0
        if boss.airborne > 0:                        # (leaping between oaks)
            lift = UP
        bank.draw(bank.static("love_shadow", _paint_shadow(26), 30), x, y + 34)
        draw_character(bank, x, y - lift, "love_cuddles", SCALE, left, frame,
                       boss.hurt_flash > 0, _pose(boss))
    batch = _Batch(text)
    yy = y - (UP if boss.up or boss.airborne > 0 else 0)
    if boss.spin is not None:                        # the cleaver blades whirling
        r = config.LOVE_SPIN[2]
        for k in range(config.LOVE_SPIN[1]):
            a = boss.spin + k * math.tau / config.LOVE_SPIN[1]
            bx = x + math.cos(a) * r * config.TILE_PX_W
            by = y + math.sin(a) * r * 0.7 * config.TILE_PX_H
            batch.put_c(bx, by, "x" if (k + blink) % 2 else "+", palette.SHOT_CLEAVER[0])
    if kind == "cleaver":
        batch.put_c(x + 30, yy - 70, "!", palette.LOVE_TELL[blink])
    elif kind == "puff":
        for dx, dy, glyph, c in _ring(8, 40 + 4 * blink, "o", palette.LOVE_TELL[0], t * 4):
            batch.put_c(x + dx, yy + dy, glyph, c)
    elif kind == "call":
        rr = 44 + (t * 80) % 30
        for dx, dy, glyph, c in _ring(16, rr, "o", palette.LOVE_TELL[blink], t):
            batch.put_c(x + dx, yy + dy * 0.8, glyph, c)
    elif kind == "string":
        for dx, dy, glyph, c in _ring(10, 42, "-", palette.WIRE_COL[blink], t * 5):
            batch.put_c(x + dx, yy + dy, glyph, c)
    elif kind == "dig":
        for k in range(4):
            a = t * 9 + k * 1.7
            batch.put_c(x + 30 + math.cos(a) * 14, yy + 26 - abs(math.sin(a)) * 22, ".",
                        palette.MOUND_COL[0])
    elif kind == "frenzy" or (boss.phase >= 2 and boss.madness >= 0.75 and not boss.panting):
        n = 10 if kind == "frenzy" else 4
        for dx, dy, glyph, c in _ring(n, 46 + 6 * blink, "!", palette.MADNESS_COL[blink], t * 3):
            batch.put_c(x + dx, yy + dy, glyph, c)
    if boss.digging > 0:
        _bar(batch, x, yy - 80, text.display.cell_w, boss.digging / config.HOARD_DIG, 6, "DIG",
             palette.MOUND_COL[1], palette.HUD_EMPTY)
    batch.flush()


def draw_oak_marks(text, bank: SpriteBank, camera: Camera, boss, hero, time: float) -> None:
    """Buried acorns (STEAL, a ring) and the oak it's up (SHAKE IT!), and an
    arrow to the nearest acorn while it's digging, or to its tree."""
    from .bosses import draw_pointer
    batch = _Batch(text)
    blink = int(time * 6) % 2
    cw = text.display.cell_w
    for m in boss.mounds:
        px, py = camera.world_to_px(m[0], m[1])
        if not (-60 <= px <= camera.view_w + 60 and -60 <= py <= camera.view_h + 60):
            continue
        _px_ring(batch, camera, m[0], m[1], config.HOARD_STEAL, 10, "+",
                 palette.PIN_MOUND[0] if blink else palette.MOUND_COL[0], time)
        s = "STEAL"
        batch.put_px(px - len(s) * cw / 2, py - 58, s, palette.PIN_MOUND[0], palette.HUD_PANEL)
    if boss.up:
        tx, ty = boss.trees[boss.tree]
        px, py = camera.world_to_px(tx, ty)
        s = "SHOOT THE TRUNK!"
        batch.put_px(px - len(s) * cw / 2, py + 26, s, palette.PIN_OAK[0], palette.HUD_PANEL)
    batch.flush()
    want = None
    if boss.up:
        want = (boss.trees[boss.tree], "OAK", palette.PIN_OAK[0])
    elif boss.mounds and (boss.digging > 0 or boss._gen is None):
        want = (_nearest(boss.mounds, hero.x, hero.y), "ACORN", palette.PIN_MOUND[0])
    if want is not None and want[0] is not None:
        (tx, ty), name, col = want
        draw_pointer(text, bank, camera, tx, ty,
                     f"{name} {math.hypot(tx - hero.x, ty - hero.y):.0f}", 20, col)
