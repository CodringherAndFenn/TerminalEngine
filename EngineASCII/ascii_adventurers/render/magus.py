"""
render/magus.py -- the Nameless Magus, Holder of Time, his runes, beams,
time zones and sand, his creatures, and the runaway apprentice's star
circles (M23.3).

The Magus is a character picture (render/characters.ART["nameless_magus"],
drawn big); his staff's lens glows while he casts. Everything he does on
the ground is glyphs, in his own colours (design/BOSSES.md 5.3):
  * runes: a ring of glyphs that lights up as it charges (all lit and
    blinking: about to fire), its kind in the middle ("*" firestorm, "x"
    blades, "#" golem);
  * sun lance: a dotted gold aim line, then the beam ("=" along it);
  * dunes: sand rippling along where the walls will rise (the walls are
    tiles); quicksand: a turning ring of ":";
  * time zones: a ring of "o" (SLOW, blue) or "+" (FAST, gold) with its
    word in the middle;
  * vortex: a marked ring, then a turning spiral of "%";
  * serpent: a blinking "^" line, then its head "@" and body racing along;
  * blink: a shimmer where he'll appear;
  * drained / stunned: kneeling, stars over his head.
"""

from __future__ import annotations

import math

import pygame

from .. import config, palette
from ..engine_ext.camera import Camera
from ..systems.quests import circle_radius
from .ascii_fx import _Batch, _ring, draw_hp_bar
from .characters import draw_character
from .sprites import SpriteBank

MAGUS_SCALE = 5              # his picture: 70 x 90 px
_KIND_GLYPH = {"fire": "*", "blades": "x", "golem": "#"}


def _px_ring(batch, camera, x, y, r_tiles, n, glyph, color, turn=0.0, lit=None):
    """n glyphs round a circle of r_tiles tiles at (x, y) (tiles aren't
    square: 20 x 24 px), the first `lit` (if given) in `color`, the rest
    dim."""
    px, py = camera.world_to_px(x, y)
    rx, ry = r_tiles * config.TILE_PX_W, r_tiles * config.TILE_PX_H
    for k in range(n):
        a = turn + k * math.tau / n
        col = color if lit is None or k < lit else palette.RUNE[2]
        batch.put_c(px + math.cos(a) * rx, py + math.sin(a) * ry, glyph, col)


def _dotted(batch, camera, x0, y0, x1, y1, col, glyph=".", step=0.8, mark=None, every=4):
    length = math.hypot(x1 - x0, y1 - y0)
    d, k = 0.6, 0
    while d < length:
        f = d / length
        px, py = camera.world_to_px(x0 + (x1 - x0) * f, y0 + (y1 - y0) * f)
        batch.put_c(px, py, mark if mark and k % every == 0 else glyph, col)
        d += step
        k += 1


def draw_magus(text, bank: SpriteBank, camera: Camera, boss) -> None:
    """The Magus and everything he's put on the field."""
    batch = _Batch(text)
    blink = int(boss.time * 8) % 2
    # Time zones and quicksand first (under everything).
    for zx, zy, kind in boss.zones:
        cols = palette.TIME_SLOW_ZONE if kind == "slow" else palette.TIME_FAST_ZONE
        glyph = "o" if kind == "slow" else "+"
        spin = boss.time * (0.3 if kind == "slow" else 1.2)
        _px_ring(batch, camera, zx, zy, config.TIME_ZONE_RADIUS, 36, glyph, cols[blink], spin)
        _px_ring(batch, camera, zx, zy, config.TIME_ZONE_RADIUS * 0.6, 20, ".", cols[1], -spin)
        px, py = camera.world_to_px(zx, zy)
        batch.put_c(px, py, "SLOW" if kind == "slow" else "FAST", cols[0])
    for qx, qy, _ in boss.quicksand:
        r = config.QUICKSAND[0]
        _px_ring(batch, camera, qx, qy, r, 18, ":", palette.QUICKSAND_COL[0], boss.time * 0.8)
        _px_ring(batch, camera, qx, qy, r * 0.5, 9, ":", palette.QUICKSAND_COL[1], -boss.time)
    # Runes.
    for r in boss.runes:
        f = r["charge"] / config.RUNE_CHARGE
        n = 16
        lit = round(f * n)
        col = palette.RUNE[0] if f > 0.8 and blink else palette.RUNE[1]
        _px_ring(batch, camera, r["x"], r["y"], config.RUNE_RADIUS, n, "o", col, -math.pi / 2,
                 lit)
        px, py = camera.world_to_px(r["x"], r["y"])
        batch.put_c(px, py, _KIND_GLYPH.get(r["kind"], "*"), col)
    tell = boss.tell
    kind = tell[0] if tell is not None else None
    if kind == "lance":
        _dotted(batch, camera, *tell[1:5], palette.LANCE_TELL[blink])
    elif kind == "dunes":
        for line in tell[1]:
            for k, (x, y, _, _) in enumerate(line):
                px, py = camera.world_to_px(x, y)
                batch.put_c(px, py + (3 if (k + blink) % 2 else -3), "," if k % 2 else ".",
                            palette.DUNE_WALL_FG)
    elif kind == "vortex":
        _px_ring(batch, camera, tell[1], tell[2], config.MAGUS_VORTEX[2] * 0.25, 10, "%",
                 palette.VORTEX_COL[blink], boss.time * 4)
        _px_ring(batch, camera, tell[1], tell[2], config.MAGUS_VORTEX[2], 28, ".",
                 palette.VORTEX_COL[1], boss.time)
    elif kind == "serpent":
        _dotted(batch, camera, *tell[1:5], palette.SERPENT[blink], glyph="^", step=1.0)
    elif kind == "blink":
        px, py = camera.world_to_px(tell[1], tell[2])
        for dx, dy, glyph, c in _ring(10, 30, "'", palette.MAGUS["lens"], boss.time * 5):
            batch.put_c(px + dx, py + dy * 1.4 + math.sin(boss.time * 9 + dx) * 4, glyph, c)
    if boss.vortex is not None:
        vx, vy = boss.vortex
        px, py = camera.world_to_px(vx, vy)
        for k in range(24):
            a = boss.time * 5 + k * 0.55
            rr = 6 + k * 7
            batch.put_c(px + math.cos(a) * rr, py + math.sin(a) * rr * 1.1, "%",
                        palette.VORTEX_COL[k % 2])
    if boss.serpent is not None:
        x0, y0, x1, y1, gone = boss.serpent
        total = math.hypot(x1 - x0, y1 - y0) or 1.0
        for k in range(10):
            d = gone - k * 0.9
            if d < 0:
                break
            f = d / total
            px, py = camera.world_to_px(x0 + (x1 - x0) * f, y0 + (y1 - y0) * f)
            batch.put_c(px, py + math.sin(d * 2) * 4, "@" if k == 0 else "o",
                        palette.SERPENT[0 if k == 0 else 1])
    if boss.beam is not None:
        x0, y0, x1, y1 = boss.beam
        _dotted(batch, camera, x0, y0, x1, y1, palette.LANCE[1], glyph="-", step=0.5)
        _dotted(batch, camera, x0, y0, x1, y1, palette.LANCE[0], glyph="=", step=0.9)
    batch.flush()

    # Him.
    x, y = camera.world_to_px(boss.x, boss.y)
    hurt = boss.hurt_flash > 0
    down = boss.dazed > 0
    left = math.cos(boss.facing) < 0
    draw_character(bank, x, y + (14 if down else 0), "nameless_magus", MAGUS_SCALE, left, 0,
                   hurt)
    batch = _Batch(text)
    lens_x = x + (-24 if left else 24)
    lens_y = y - 40 + (14 if down else 0)
    if boss.casting or kind == "cast":
        for dx, dy, glyph, c in _ring(8, 12 + 4 * blink, "*", palette.MAGUS["lens"],
                                      boss.time * 6):
            batch.put_c(lens_x + dx, lens_y + dy, glyph, c)
    if down:
        for k in range(3):
            a = boss.time * 4 + k * math.tau / 3
            batch.put_c(x + math.cos(a) * 26, y - 54 + math.sin(a) * 6, "*", palette.TOAST)
    batch.flush()


# --- His creatures -------------------------------------------------------------------------


def _paint_elemental(frame: int, hurt: bool):
    body, dark, eyes = palette.ELEMENTAL

    def paint(surf, to_px):
        cx, cy = to_px(0, 0)
        c = palette.HIT_FLASH if hurt else body
        pygame.draw.ellipse(surf, dark, pygame.Rect(round(cx - 9), round(cy - 12), 18, 26))
        pygame.draw.ellipse(surf, c, pygame.Rect(round(cx - 7), round(cy - 11), 14, 21))
        for k in range(3):                         # its swirling skirt of sand
            a = frame * 0.8 + k * math.tau / 3
            pygame.draw.circle(surf, dark, (round(cx + math.cos(a) * 8), round(cy + 11)), 3)
        for side in (-1, 1):
            pygame.draw.circle(surf, eyes, (round(cx + side * 3), round(cy - 5)), 2)
    return paint


def _paint_golem(raised: bool, hurt: bool):
    g = palette.GOLEM

    def paint(surf, to_px):
        cx, cy = to_px(0, 0)
        body = palette.HIT_FLASH if hurt else g["body"]
        pygame.draw.rect(surf, g["dark"], pygame.Rect(round(cx - 15), round(cy - 16), 30, 32))
        pygame.draw.rect(surf, body, pygame.Rect(round(cx - 13), round(cy - 14), 26, 26))
        pygame.draw.rect(surf, g["dark"], pygame.Rect(round(cx - 8), round(cy - 24), 16, 12))
        pygame.draw.rect(surf, body, pygame.Rect(round(cx - 6), round(cy - 22), 12, 9))
        for side in (-1, 1):
            pygame.draw.circle(surf, g["eye"], (round(cx + side * 3), round(cy - 18)), 2)
            fy = cy - 30 if raised else cy - 4
            pygame.draw.rect(surf, g["dark"], pygame.Rect(round(cx + side * 19 - 6), round(fy), 12, 12))
            pygame.draw.rect(surf, body, pygame.Rect(round(cx + side * 19 - 4), round(fy + 2), 8, 8))
    return paint


def _paint_hourglass(level: int, hurt: bool):
    h = palette.HOURGLASS_COL

    def paint(surf, to_px):
        cx, cy = to_px(0, 0)
        frame = palette.HIT_FLASH if hurt else h["frame"]
        top = [(cx - 14, cy - 24), (cx + 14, cy - 24), (cx + 2, cy), (cx - 2, cy)]
        bot = [(cx - 2, cy), (cx + 2, cy), (cx + 14, cy + 24), (cx - 14, cy + 24)]
        for tri in (top, bot):
            pygame.draw.polygon(surf, h["glass"], [(round(a), round(b)) for a, b in tri])
        f = level / 8                               # sand left in the top
        if f > 0:
            w = 12 * f
            pygame.draw.polygon(surf, h["sand"], [(round(cx - w), round(cy - 24 * f)),
                                                  (round(cx + w), round(cy - 24 * f)),
                                                  (round(cx), round(cy - 1))])
        g = 1 - f                                   # ...and fallen into the bottom
        if g > 0:
            w = 13 * g
            pygame.draw.polygon(surf, h["sand"], [(round(cx - w), round(cy + 24)),
                                                  (round(cx + w), round(cy + 24)),
                                                  (round(cx), round(cy + 24 - 20 * g))])
        for yy in (cy - 28, cy + 24):
            pygame.draw.rect(surf, h["edge"], pygame.Rect(round(cx - 18), round(yy), 36, 5))
            pygame.draw.rect(surf, frame, pygame.Rect(round(cx - 17), round(yy + 1), 34, 3))
        for side in (-1, 1):
            pygame.draw.line(surf, frame, (round(cx + side * 16), round(cy - 24)),
                             (round(cx + side * 16), round(cy + 24)), 3)
    return paint


def draw_minion(text, bank: SpriteBank, camera: Camera, e) -> None:
    """A sand elemental, a sand golem, a sigil or the hourglass."""
    x, y = camera.world_to_px(e.x, e.y)
    key = getattr(e, "kind_key", "")
    hurt = e.hurt_flash > 0
    batch = _Batch(text)
    if key == "sand_elemental":
        if e.gone > 0:
            for dx, dy, glyph, c in _ring(6, 10, ".", palette.ELEMENTAL[1], e.phase):
                batch.put_c(x + dx, y + dy, glyph, c)
        else:
            frame = int(e.phase) % 4
            bank.draw(bank.static(f"elemental{frame}{hurt}", _paint_elemental(frame, hurt), 22),
                      x, y)
            if e.windup > 0:
                batch.put_c(x, y - 26, "!", palette.ELEMENTAL[2])
    elif key == "sand_golem":
        raised = e.windup > 0
        bank.draw(bank.static(f"golem{raised}{hurt}", _paint_golem(raised, hurt), 36), x, y)
        if raised:
            _px_ring(batch, camera, e.x, e.y, e.espec.attack_radius, 14, ".",
                     palette.TELEGRAPH[int(e.windup * 10) % 2])
    elif key == "sigil":
        col = palette.SIGIL[int(e.phase) % 2]
        batch.put_c(x, y, "@", col)
        for dx, dy, glyph, c in _ring(4, 11, "+", col, e.phase):
            batch.put_c(x + dx, y + dy, glyph, c)
    elif key == "hourglass":
        level = round(getattr(e, "sand", 1.0) * 8)
        bank.draw(bank.static(f"hourglass{level}{hurt}", _paint_hourglass(level, hurt), 40), x, y)
        draw_hp_bar(text, x, y - 40, e.hp / e.max_hp)
    batch.flush()


# --- The apprentice's star circles --------------------------------------------------------


def draw_seals(text, camera: Camera, quests, time: float) -> None:
    """A star circle being broken: its ring glowing, and how worn its seal
    is as a bar over it."""
    batch = _Batch(text)
    x0, y0 = camera.canvas_to_world(0, 0)
    x1, y1 = camera.canvas_to_world(camera.view_w, camera.view_h)
    cw = text.display.cell_w
    for s in quests.states.values():
        if s.spec.kind not in ("survive", "escort", "rescue", "cleanse") or s.stage != "hunt":
            continue
        full = {"survive": config.SEAL_TIME, "escort": config.ESCORT_SETUP,
                "rescue": config.RESCUE_THAW, "cleanse": config.CLEANSE_TIME}[s.spec.kind]
        for i, (sx, sy) in enumerate(s.camp.spots):
            if i in s.lit or not (x0 - 6 <= sx <= x1 + 6 and y0 - 8 <= sy <= y1 + 6):
                continue
            worn = s.heat.get(i, 0.0)
            if worn <= 0:
                continue
            blink = int(time * 6) % 2
            if s.spec.kind == "survive":
                _px_ring(batch, camera, sx, sy, config.SEAL_RADIUS, 24, "*",
                         palette.STAR_RING_FG if blink else palette.SEAL_FG, time)
            elif s.spec.kind == "cleanse":            # (M25.1: the ring tightening)
                r = circle_radius("cleanse", worn)
                _px_ring(batch, camera, sx, sy, r, max(12, int(r * 6)), "*",
                         palette.SHRINE_CLEAN_FG if blink else palette.ROT_RING_FG, time)
            frac = min(1.0, worn / full)
            width = 10
            filled = round(frac * width)
            px, py = camera.world_to_px(sx, sy)
            left = px - (width + 2) * cw / 2
            top = py - config.SEAL_RADIUS * config.TILE_PX_H - 20
            batch.put_px(left, top, "[" + "█" * filled, palette.SEAL_FG, palette.HUD_PANEL)
            batch.put_px(left + (1 + filled) * cw, top, "░" * (width - filled) + "]",
                         palette.SEAL_BROKEN_FG, palette.HUD_PANEL)
    batch.flush()
