"""
render/walking_city.py -- drawing the Overseer's second form, the walking
city (M32.5, ai/walking_city.py), from ai/overseer's draw_overseer.

On the floor first: the cables it's plugged in by (from each junction to its
body, sparks running along them), the stomp's marked spots and the shock
rings, the eyes' cones (dotted edges; lit while one sees you), the laser
strikes' marks (closing in, then a cross as they lock), the throw's line and
where it lands, the swing's arc (shown) and the great beam's line (two
dotted edges while it charges; three bands of beam firing). Then its body:
a shadow, its four legs (hip, knee, foot: a lifted foot drawn raised), the
plates on its far side, its picture raised above its feet (the eye in its
chest glowing while the beam charges), the plates on its near side (each a
piece of the hall: a cell door, a screen, a pillar's slab, torn floor),
the eyes riding on it, its turrets (phase 4), its arms (reaching, holding,
the piece it holds up, the arm of chained cell doors swinging) and what it
threw, in the air.
"""

from __future__ import annotations

import math

from .. import config, palette
from .ascii_fx import _Batch
from .characters import draw_character
from .panopticon import _along, _beam_glyph, _blink, _ray, _ring

LIFT = 1.6                 # tiles its body stands above its feet (drawing)
PLATE_LOOKS = {"door": "plate_door", "screen": "plate_screen", "pillar": "plate_pillar",
               "rubble": "plate_rubble"}


def _segment(batch, x0, y0, x1, y1, step, glyph, col) -> None:
    """A line of `glyph` between two canvas points (None: by direction)."""
    n = max(1, int(math.hypot(x1 - x0, y1 - y0) / step))
    g = glyph or _beam_glyph(x1 - x0, y1 - y0)
    for q in range(n + 1):
        f = q / n
        batch.put_c(x0 + (x1 - x0) * f, y0 + (y1 - y0) * f, g, col)


def _floor(batch, camera, e) -> None:
    t = e.real_t
    for j in e.cables:                                   # (plugged in: sparks run along)
        jx, jy = e.junction_spot(j)
        n = max(2, int(math.hypot(e.x - jx, e.y - jy) / 0.8))
        for q in range(n + 1):
            f = q / n
            px, py = camera.world_to_px(jx + (e.x - jx) * f, jy + (e.y - jy) * f)
            hot = (q + int(t * 16)) % 5 == 0
            batch.put_c(px, py - LIFT * config.TILE_PX_H * f * 0.6, "*" if hot else "=",
                        palette.WALKER_CABLE[1 if hot else 0])
    for s in e.shocks:
        _ring(batch, camera, s[0], s[1], s[2], "o", palette.WALKER_SHOCK[int(t * 14) % 2])
    for m in e.stomp_marks:
        col = _blink(m[2], palette.STOMP_MARK)
        _ring(batch, camera, m[0], m[1], 1.3, "o", col, 10)
        px, py = camera.world_to_px(m[0], m[1])
        batch.put_c(px, py, "!", col)
    cx, cy = camera.x, camera.y                          # (only the eyes near the view)
    half = math.radians(config.WALKER_EYES[6]) / 2
    for eye in e.eyes:                                   # (their cones: lit while one sees you)
        if not eye.alive or abs(eye.x - cx) > 70 or abs(eye.y - cy) > 40:
            continue
        seeing = eye.seeing is not None
        col = palette.WALKER_EYE_CONE[1 if seeing else 0]
        for side in (-1, 1):
            _ray(batch, camera, eye.x, eye.y, eye.facing + side * half, eye.reach, 1.0, ".", col)
    follow, hold, radius = config.WALKER_EYES[11], config.WALKER_EYES[12], config.WALKER_EYES[13]
    for s in e.strikes:                                  # (closing in; a cross once it locks)
        left = follow + hold - s[3]
        locked = s[3] >= follow
        r = radius * (1.0 + 0.8 * max(0.0, left / (follow + hold)))
        col = _blink(left, palette.WALKER_STRIKE)
        _ring(batch, camera, s[1], s[2], r, "+" if not locked else "x", col, 10)
        if locked:
            px, py = camera.world_to_px(s[1], s[2])
            batch.put_c(px, py, "X", palette.WALKER_STRIKE[1])
    if e.throw_line is not None:
        x0, y0, x1, y1 = e.throw_line
        _along(batch, camera, x0, y0, x1, y1, 1.0, ".", palette.WALKER_THROW[0])
        wide = config.WALKER_GRAB[9] if e.grabbed is None else 1.0
        _ring(batch, camera, x1, y1, wide, "o", palette.WALKER_THROW[int(t * 8) % 2], 12)
    if e.arm_swing is not None:
        a0, a1, f, length = e.arm_swing
        if f < 0:                                        # (its arc shown: the whole sweep)
            col = palette.WALKER_SWING_ARC[int(t * 10) % 2]
            for a in (a0, a1):
                _ray(batch, camera, e.x, e.y, a, length, 1.0, ":", col)
            n = 28
            for q in range(n + 1):
                a = a0 + (a1 - a0) * q / n
                for r, g in ((length, "o"), (length * 0.6, ".")):
                    px, py = camera.world_to_px(e.x + math.cos(a) * r, e.y + math.sin(a) * r)
                    batch.put_c(px, py, g, col)
    if e.great_beam is not None:
        a, f, length = e.great_beam
        half = config.WALKER_BEAM[1]
        ux, uy = math.cos(a), math.sin(a)
        vx, vy = -uy, ux
        if f < 0:                                        # (charging: its line shown)
            col = palette.WALKER_BEAM_TELL[int(t * 10) % 2]
            for s in (-1, 1):
                ox, oy = e.x + vx * half * s, e.y + vy * half * s
                _along(batch, camera, ox, oy, ox + ux * length, oy + uy * length, 1.3, ".", col)
            _along(batch, camera, e.x, e.y, e.x + ux * length, e.y + uy * length, 2.6, "-",
                   palette.WALKER_BEAM_TELL[1])
        else:
            g = _beam_glyph(ux, uy)
            for s, k in ((-0.6, 0), (0.0, 1), (0.6, 0)):
                ox, oy = e.x + vx * half * s, e.y + vy * half * s
                col = palette.GREAT_BEAM[k if (int(t * 20) % 2) else 1 - k]
                _along(batch, camera, ox, oy, ox + ux * length, oy + uy * length, 0.5, g, col)


def draw_walking_city(text, bank, camera, e) -> None:
    tw, th = config.TILE_PX_W, config.TILE_PX_H
    batch = _Batch(text)
    _floor(batch, camera, e)
    t = e.real_t
    x, y = camera.world_to_px(e.x, e.y)
    size = e.size
    lift = LIFT * th
    shadow = "_" * max(3, round(5 * size))
    batch.put_c(x, y + 6, shadow, palette.BOMB_SHADOW)
    batch.put_c(x, y + 14, shadow[:-2], palette.BOMB_SHADOW)
    # Its legs: hip (on its body), knee (up and out), foot (raised while it steps).
    from ..ai.walking_city import HIPS
    for i, f in enumerate(e.feet):
        hx, hy = HIPS[i]
        px0 = x + hx * size * tw * 0.55
        py0 = y - lift + hy * size * th * 0.45 + 8
        fx, fy = camera.world_to_px(f.x, f.y)
        fy -= f.lift * 16
        kx = (px0 + fx) / 2 + (1 if hx > 0 else -1) * 12 * size
        ky = min(py0, fy) - 10
        _segment(batch, px0, py0, kx, ky, 7, "#", palette.WALKER_LEG[0])
        _segment(batch, kx, ky, fx, fy, 7, None, palette.WALKER_LEG[1])
        batch.put_c(fx, fy, "[#]", palette.WALKER_LEG[0])
    batch.flush()
    scale = max(1, round(config.WALKER_BODY[1] * size))
    rx = 7 * scale * 1.0                                  # (where the plates sit: on its outline, px)
    ry = 7 * scale * 0.8
    by = y - lift
    flip = math.cos(e.facing) < 0
    plate_scale = max(2, round(5 * size))
    order = []
    for k, p in enumerate(e.plates):
        if p is None:
            continue
        a = e.facing + e.slot_angle(k)
        order.append((math.sin(a), k, p, a))
    order.sort()
    for s, k, p, a in order:                              # (its far side first)
        if s >= 0:
            break
        _plate(bank, x + math.cos(a) * rx, by + math.sin(a) * ry, p, plate_scale)
    if e.form == 2:
        draw_character(bank, x, by, e.sprite_now(), scale, flip, 0, e.hurt_flash > 0)
    for s, k, p, a in order:
        if s >= 0:
            _plate(bank, x + math.cos(a) * rx, by + math.sin(a) * ry, p, plate_scale)
    over = _Batch(text)
    for eye in e.eyes:                                    # (the eyes riding on it)
        if eye.alive and eye.on_body:
            ex, ey = camera.world_to_px(eye.x, eye.y)
            draw_character(bank, ex, ey - lift, "walker_eye", eye.espec.scale + 1, eye.facing_left(), 0,
                           eye.hurt_flash > 0)
    if e.phase >= 3 and e.turret_t:
        from ..ai.walking_city import TURRET_SLOTS
        for k in range(len(e.turret_t)):
            tx, ty = camera.world_to_px(*e.body_point(TURRET_SLOTS[k % len(TURRET_SLOTS)], 1.0))
            fired = k < len(e.turret_fired) and e.turret_fired[k] > 0
            over.put_c(tx, ty - lift, "[T]" if not fired else "[*]", palette.WALKER_TURRET)
    ax, ay = x, by
    if e.arm is not None:                                 # (its arm reaching out)
        hx, hy, s, of, kind = e.arm
        f = min(1.0, s / of) if of > 0 else 1.0
        if kind == "hold":
            f = 1.0
        tx, ty = camera.world_to_px(hx, hy)
        ex, ey = ax + (tx - ax) * f, ay + (ty - ay) * f
        _segment(over, ax, ay, ex, ey, 9, None, palette.WALKER_ARM[0])
        over.put_c(ex, ey, "@" if kind == "hold" else "#", palette.WALKER_ARM[1])
        if kind == "grab":
            _ring(over, camera, hx, hy, config.WALKER_GRAB[2], "o", _blink(of - s, palette.WALKER_THROW), 12)
    if e.building is not None:                            # (an arm tearing a piece out)
        px_, py_, kind, s = e.building[0], e.building[1], e.building[2], e.building[3]
        f = s / 0.35 if s < 0.35 else max(0.0, 1.0 - (s - 0.35) / 0.35)
        tx, ty = camera.world_to_px(px_, py_)
        ex, ey = ax + (tx - ax) * f, ay + (ty - ay) * f
        _segment(over, ax, ay, ex, ey, 9, None, palette.WALKER_ARM[1])
        over.put_c(ex, ey, "%" if s >= 0.35 else "#", palette.WALKER_ARM[0])
    if e.lifted is not None:                              # (the piece held up, about to be thrown)
        over.put_c(ax, ay - 7 * scale - 10, "[%%]", palette.WALKER_THROW[0])
    if e.arm_swing is not None and e.arm_swing[2] >= 0:   # (the arm of chained cell doors)
        a0, a1, f, length = e.arm_swing
        a = a0 + (a1 - a0) * f
        n = max(3, int(length / 0.9))
        for q in range(1, n + 1):
            d = length * q / n
            px, py = camera.world_to_px(e.x + math.cos(a) * d, e.y + math.sin(a) * d)
            py -= lift * (1.0 - q / n) * 0.8
            over.put_c(px, py, "|#" if q % 2 else "#|", palette.WALKER_ARM[q % 2])
    if e.thrown is not None:                              # (in the air)
        x0, y0, x1, y1, s, of, kind = e.thrown
        f = min(1.0, s / of) if of > 0 else 1.0
        px, py = camera.world_to_px(x0 + (x1 - x0) * f, y0 + (y1 - y0) * f)
        over.put_c(px, py - math.sin(math.pi * f) * 60 - lift * (1 - f), "[%]", palette.WALKER_THROW[0])
    if e.great_beam is not None and e.great_beam[1] < 0:  # (the eye charging: a glow on its chest)
        over.put_c(x, by - 2, "(*)" if int(t * 12) % 2 else "(O)", palette.GREAT_BEAM[1])
    over.flush()


def _plate(bank, x: float, y: float, p, scale: int) -> None:
    rise = p.fresh * 30                                   # (bolted on just now: still settling)
    draw_character(bank, x, y - rise, PLATE_LOOKS.get(p.kind, "plate_rubble"), scale, False, 0,
                   p.flash > 0)
