"""
render/fallout.py -- the Fallout King, his glow, beams, fallout, goo and
barrels, his ghouls, rods and skulls, and the core and valve gauges
(M24.1).

The King is a character picture (render/characters.ART["fallout_king"],
drawn big); the core in his chest pulses, and blazes while it's exposed.
His glow's reach (where rads build) is a faint dotted ring round him.
Tells, in his own green (design/BOSSES.md 5.3):
  * gamma cross: four dotted aim lines, then four beams ("|"/"-" along
    them);
  * barrels: he heaves; each barrel arcs with a ring where it'll land;
  * roar (ghouls, skulls): a pulsing ring; EMP: crackling "+" round him;
  * grate dive: he sinks into a grate, the one he'll burst from rattles;
  * stomp: rings where the fallout will land;
  * the core: a CORE gauge over him in phase 3, a big MELTDOWN countdown,
    valve progress bars at the valves being shut.
"""

from __future__ import annotations

import math

import pygame

from .. import config, palette
from ..engine_ext.camera import Camera
from .ascii_fx import _Batch, _ring
from .characters import draw_character
from .magus import _dotted, _px_ring
from .sprites import SpriteBank

KING_SCALE = 6               # his picture: 84 x 108 px


def _bar(batch, x: float, y: float, cw: int, frac: float, width: int, label: str,
         full: tuple, empty: tuple) -> None:
    filled = round(max(0.0, min(1.0, frac)) * width)
    s = label + " [" if label else "["
    left = x - (len(s) + width + 1) * cw / 2
    batch.put_px(left, y, s, full, palette.HUD_PANEL)
    left += len(s) * cw
    batch.put_px(left, y, "█" * filled, full, palette.HUD_PANEL)
    batch.put_px(left + filled * cw, y, "░" * (width - filled) + "]", empty, palette.HUD_PANEL)


def draw_king(text, bank: SpriteBank, camera: Camera, boss) -> None:
    batch = _Batch(text)
    blink = int(boss.time * 8) % 2
    cw = text.display.cell_w
    # The ground: fallout, goo, his glow's reach.
    for p in boss.patches:
        r = boss._patch_radius(p)
        _px_ring(batch, camera, p["x"], p["y"], r, max(10, int(r * 7)), "*",
                 palette.FALLOUT_COL[blink], boss.pulse * 0.5)
        _px_ring(batch, camera, p["x"], p["y"], r * 0.6, max(6, int(r * 4)), ".",
                 palette.FALLOUT_COL[1], -boss.pulse * 0.7)
    r = config.KING_BARRELS[4]
    for gx, gy, _ in boss.goo:
        _px_ring(batch, camera, gx, gy, r, 16, ":", palette.GOO[0], boss.pulse * 0.4)
        _px_ring(batch, camera, gx, gy, r * 0.5, 8, ":", palette.GOO[1], -boss.pulse * 0.4)
    if not boss.submerged:
        _px_ring(batch, camera, boss.x, boss.y, config.RADS_GLOW_RANGE + boss.hit_radius, 40,
                 ".", palette.FALLOUT_COL[1], boss.pulse * 0.2)
    tell = boss.tell
    kind = tell[0] if tell is not None else None
    if kind == "gamma":
        for line in tell[1]:
            _dotted(batch, camera, *line, palette.KING_TELL[blink])
    elif kind == "stomp":
        for x, y in tell[1]:
            _px_ring(batch, camera, x, y, config.FALLOUT_STOMP[3], 16, "o",
                     palette.TELEGRAPH[blink])
            px, py = camera.world_to_px(x, y)
            batch.put_c(px, py, "x", palette.TELEGRAPH[blink])
    elif kind == "rattle":
        px, py = camera.world_to_px(tell[1], tell[2])
        for k in range(6):
            batch.put_c(px + math.sin(boss.time * 40 + k) * 6 + (k - 2.5) * 10,
                        py + math.cos(boss.time * 37 + k) * 4, "#", palette.KING_TELL[blink])
        _px_ring(batch, camera, tell[1], tell[2], config.KING_GRATE[2], 16, "o",
                 palette.TELEGRAPH[blink])
    for line in boss.beams:
        x0, y0, x1, y1 = line
        _dotted(batch, camera, x0, y0, x1, y1, palette.GAMMA[1], glyph="+", step=0.6)
        _dotted(batch, camera, x0, y0, x1, y1, palette.GAMMA[0], glyph="#", step=1.1)
    batch.flush()

    if not boss.submerged:
        x, y = camera.world_to_px(boss.x, boss.y)
        hurt = boss.hurt_flash > 0
        draw_character(bank, x, y, "fallout_king", KING_SCALE, math.cos(boss.facing) < 0, 0, hurt)
        batch = _Batch(text)
        core = palette.KING["core"] if boss.exposed > 0 else palette.KING["glow"]
        size = 10 + (6 if boss.exposed > 0 else 3) * (1 + math.sin(boss.pulse * 6))
        for dx, dy, glyph, c in _ring(8, size, "*" if boss.exposed > 0 else ".", core,
                                      boss.pulse * 3):
            batch.put_c(x + dx, y + 2 + dy, glyph, c)
        if kind in ("roar", "heave"):
            rr = 50 + (boss.time * 80) % 30
            for dx, dy, glyph, c in _ring(16, rr, "o", palette.KING_TELL[blink], boss.time):
                batch.put_c(x + dx, y + dy * 0.8, glyph, c)
        elif kind == "emp":
            for dx, dy, glyph, c in _ring(12, 60, "+", palette.SHOT_EMP[0], boss.time * 7):
                batch.put_c(x + dx + math.sin(boss.time * 30 + dy) * 3, y + dy * 0.8, glyph, c)
        elif kind == "sink":
            for dx, dy, glyph, c in _ring(10, 40, ".", palette.FALLOUT_COL[0], boss.time * 3):
                batch.put_c(x + dx, y + 40 + dy * 0.3, glyph, c)
        if boss.phase >= 2:
            if boss.exposed > 0:
                _bar(batch, x, y - 92, cw, boss.exposed / config.CORE_EXPOSED[0], 10, "EXPOSED",
                     palette.KING["core"], palette.HUD_EMPTY)
            elif boss.meltdown > 0:
                s = f" MELTDOWN IN {math.ceil(boss.meltdown)}! HIDE BEHIND LEAD! "
                batch.put_px(x - len(s) * cw / 2, y - 92, s,
                             palette.TELEGRAPH[blink], palette.HUD_PANEL)
            else:
                _bar(batch, x, y - 92, cw, boss.heat / 100.0, 10, "CORE",
                     palette.RADS_BAR[2] if boss.heat > 75 else palette.RADS_BAR[1],
                     palette.HUD_EMPTY)
        batch.flush()

    # Valves being shut.
    valves = boss.props.get("valves", [])
    if boss.phase >= 2 and boss.exposed <= 0:
        batch = _Batch(text)
        for i, (vx, vy) in enumerate(valves):
            t = boss.valve_t.get(i, 0.0)
            if t > 0:
                px, py = camera.world_to_px(vx, vy)
                _bar(batch, px, py - 40, cw, t / config.VALVE_TIME, 6, "", palette.VALVE_SHUT_FG,
                     palette.HUD_EMPTY)
        batch.flush()


# --- His creatures -------------------------------------------------------------------------


def _paint_ghoul(frame: int, hurt: bool):
    g = palette.GHOUL

    def paint(surf, to_px):
        cx, cy = to_px(0, 0)
        body = palette.HIT_FLASH if hurt else g["body"]
        pygame.draw.ellipse(surf, g["dark"], pygame.Rect(round(cx - 8), round(cy - 10), 16, 22))
        pygame.draw.ellipse(surf, body, pygame.Rect(round(cx - 6), round(cy - 9), 12, 18))
        pygame.draw.circle(surf, g["dark"], (round(cx), round(cy - 12)), 6)
        pygame.draw.circle(surf, body, (round(cx), round(cy - 12)), 5)
        for side in (-1, 1):
            pygame.draw.circle(surf, g["eye"], (round(cx + side * 2), round(cy - 13)), 1)
            arm = 4 if (frame + (side > 0)) % 2 else -2
            pygame.draw.line(surf, g["dark"], (round(cx + side * 6), round(cy - 4)),
                             (round(cx + side * 11), round(cy + arm)), 2)
    return paint


def _paint_rod(phase: int):
    r = palette.ROD

    def paint(surf, to_px):
        cx, cy = to_px(0, 0)
        glow = r["rod"] if phase % 2 else r["dark"]
        pygame.draw.rect(surf, r["cap"], pygame.Rect(round(cx - 6), round(cy - 22), 12, 5))
        pygame.draw.rect(surf, glow, pygame.Rect(round(cx - 4), round(cy - 17), 8, 22))
        pygame.draw.rect(surf, r["cap"], pygame.Rect(round(cx - 6), round(cy + 4), 12, 5))
    return paint


def _paint_barrel(hurt: bool):
    b = palette.BARREL

    def paint(surf, to_px):
        cx, cy = to_px(0, 0)
        body = palette.HIT_FLASH if hurt else b["body"]
        pygame.draw.rect(surf, b["band"], pygame.Rect(round(cx - 8), round(cy - 10), 16, 20))
        pygame.draw.rect(surf, body, pygame.Rect(round(cx - 7), round(cy - 9), 14, 18))
        for yy in (cy - 4, cy + 4):
            pygame.draw.line(surf, b["band"], (round(cx - 7), round(yy)), (round(cx + 7), round(yy)))
        pygame.draw.circle(surf, b["goo"], (round(cx), round(cy)), 3)
    return paint


def draw_king_minion(text, bank: SpriteBank, camera: Camera, e) -> None:
    """A glowing ghoul, an isotope rod, a toxic barrel or a gamma skull."""
    x, y = camera.world_to_px(e.x, e.y)
    key = getattr(e, "kind_key", "")
    hurt = e.hurt_flash > 0
    batch = _Batch(text)
    if key == "glowing_ghoul":
        frame = int(e.wriggle) % 2
        bank.draw(bank.static(f"ghoul{frame}{hurt}", _paint_ghoul(frame, hurt), 20), x, y)
        if e.windup > 0:
            batch.put_c(x, y - 24, "!", palette.GHOUL["eye"])
    elif key == "isotope_rod":
        ph = int(e.phase) % 2
        bank.draw(bank.static(f"rod{ph}", _paint_rod(ph), 24), x, y)
    elif key == "toxic_barrel":
        tx, ty = camera.world_to_px(*e.target)
        blink = int(e.t * 10) % 2
        _px_ring(batch, camera, e.target[0], e.target[1], config.KING_BARRELS[4], 14, ".",
                 palette.GOO[blink])
        batch.put_c(tx, ty, "x", palette.GOO[blink])
        batch.put_c(x, y, ".", palette.BOMB_SHADOW)
        bank.draw(bank.static(f"barrel{hurt}", _paint_barrel(hurt), 14), x,
                  y - e.height * 50)
    elif key == "gamma_skull":
        col = palette.SKULL[int(e.phase) % 2]
        batch.put_c(x, y, "@", col)
        batch.put_c(x - 4, y + 9, "''", col)
    batch.flush()


# --- The meltdown wave, and the vault's markers (what to run to) ---------------------------


def _hash01(*v) -> float:
    h = 2166136261
    for x in v:
        h = ((h ^ (int(x) & 0xFFFFFFFF)) * 16777619) & 0xFFFFFFFF
    return h / 0xFFFFFFFF


def draw_meltdown(text, camera: Camera, e) -> None:
    """The meltdown: a flash, then a band of radiation racing out from the
    King across the whole vault (e.size tiles), sparks lingering behind it.
    Drawn on a screen grid (one glyph a tile), so it covers what you see."""
    batch = _Batch(text)
    f = e.progress
    r = min(e.size, e.t * config.MELTDOWN_SPEED)     # (the same speed as its hits)
    tw, th = config.TILE_PX_W, config.TILE_PX_H
    cols, rows = int(camera.view_w // tw) + 2, int(camera.view_h // th) + 2
    k_glyph = ("%", "#", "*")
    for j in range(rows):
        for i in range(cols):
            px, py = i * tw + tw / 2, j * th + th / 2
            wx, wy = camera.canvas_to_world(px, py)
            d = math.hypot(wx - e.x, wy - e.y)
            h = _hash01(i * 7 + round(wx), j * 13 + round(wy))
            if e.t < 0.12:                                  # the flash
                batch.put_c(px, py, "░", palette.KING["core"])
            elif r - 4.0 <= d <= r:                         # the front
                batch.put_c(px, py, k_glyph[int(h * 3)], palette.KING["core"] if h > 0.4
                            else palette.KING["glow"])
            elif r - 12.0 <= d < r - 4.0 and h > 0.55:     # its wake
                batch.put_c(px, py, "*" if h > 0.8 else "+", palette.FALLOUT_COL[0])
            elif d < r - 12.0 and h > 0.9 - 0.3 * (1 - f):  # sparks settling behind
                batch.put_c(px, py - (1 - f) * 10 * h, ".", palette.FALLOUT_COL[1])
    batch.flush()


def _nearest(points, x, y):
    return min(points, key=lambda p: math.hypot(p[0] - x, p[1] - y), default=None)


def draw_vault_marks(text, bank: SpriteBank, camera: Camera, boss, hero, time: float) -> None:
    """What the Fallout King's fight asks you to find, marked: the showers
    (a ring and SHOWER, or DRY and how long), from phase 3 the valves (VALVE
    / SHUT), the lead walls during a meltdown countdown (HIDE), the core
    while it's exposed (HIT THE CORE!) -- and an arrow at the screen's edge
    to the one you need now: the nearest running shower when your rads are
    high, the nearest open valve, or the nearest lead wall in a countdown.
    During the countdown, radiation motes rise all over the vault."""
    from .bosses import draw_pointer
    props = boss.props
    batch = _Batch(text)
    blink = int(time * 6) % 2
    cw = text.display.cell_w
    x0, y0 = camera.canvas_to_world(0, 0)
    x1, y1 = camera.canvas_to_world(camera.view_w, camera.view_h)

    def seen(x, y, m=3.0):
        return x0 - m <= x <= x1 + m and y0 - m <= y <= y1 + m

    def label(x, y, s, col, up=34):
        px, py = camera.world_to_px(x, y)
        batch.put_px(px - len(s) * cw / 2, py - up, s, col, palette.HUD_PANEL)

    showers = props.get("showers", [])
    for i, (sx, sy) in enumerate(showers):
        if not seen(sx, sy):
            continue
        dry = boss.dry.get(i, 0.0)
        if dry > 0:
            label(sx, sy, f"DRY {math.ceil(dry)}", palette.SHOWER_OFF_FG)
        else:
            _px_ring(batch, camera, sx, sy, config.SHOWER[2] + 0.4, 12, "o",
                     palette.SHOWER_FG, time * 2)
            label(sx, sy, "SHOWER", palette.SHOWER_FG)
    if boss.phase >= 2:
        for i, (vx, vy) in enumerate(props.get("valves", [])):
            if seen(vx, vy) and boss.exposed <= 0 and boss.meltdown <= 0:
                shut = i in boss.shut
                if not shut:
                    _px_ring(batch, camera, vx, vy, config.VALVE_REACH, 14, "+",
                             palette.VALVE_FG if blink else palette.PIN_VALVE[1], -time)
                label(vx, vy, "SHUT" if shut else "VALVE",
                      palette.VALVE_SHUT_FG if shut else palette.VALVE_FG)
        if boss.meltdown > 0:
            for lx, ly in props.get("leads", []):
                if seen(lx, ly):
                    label(lx, ly, "HIDE BEHIND", palette.TELEGRAPH[blink], up=40)
            # Motes rising all over the vault.
            for k in range(140):
                hx, hy = _hash01(k, 1), _hash01(k, 2)
                wx = x0 + (x1 - x0) * hx
                wy = y1 - ((y1 - y0) * (hy + time * 0.25 * (0.5 + hx))) % (y1 - y0)
                if boss.lair is None or boss.lair.inside(wx, wy):
                    px, py = camera.world_to_px(wx, wy)
                    batch.put_c(px, py, "'" if k % 3 else "*", palette.FALLOUT_COL[k % 2])
        if boss.exposed > 0 and not boss.submerged and seen(boss.x, boss.y, 5.0):
            px, py = camera.world_to_px(boss.x, boss.y)
            for dx, dy, glyph, c in _ring(12, 34 + 6 * blink, "+", palette.KING["core"], time * 4):
                batch.put_c(px + dx, py + dy, glyph, c)
            s = " HIT THE CORE! "
            batch.put_px(px - len(s) * cw / 2, py - 112, s, palette.KING["core"], palette.HUD_PANEL)
    batch.flush()

    # The arrow to what you need now.
    want = None
    if boss.meltdown > 0:
        want = (_nearest(props.get("leads", []), hero.x, hero.y), "LEAD", palette.PIN_LEAD[0])
    elif hero.rads >= 60 or hero.irradiated > 0:
        live = [s for i, s in enumerate(showers) if boss.dry.get(i, 0.0) <= 0]
        want = (_nearest(live, hero.x, hero.y), "SHOWER", palette.SHOWER_FG)
    elif boss.phase >= 2 and boss.exposed <= 0:
        open_ = [v for i, v in enumerate(props.get("valves", [])) if i not in boss.shut]
        want = (_nearest(open_, hero.x, hero.y), "VALVE", palette.VALVE_FG)
    if want is not None and want[0] is not None:
        (tx, ty), name, col = want
        draw_pointer(text, bank, camera, tx, ty,
                     f"{name} {math.hypot(tx - hero.x, ty - hero.y):.0f}", 20, col)
