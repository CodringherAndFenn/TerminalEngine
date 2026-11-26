"""
render/panopticon.py -- the dangers of Panopticon's land drawn over its
tiles (M32.1, systems/panopticon.py): the laser fences' beams (and a faint
line just before a blinking one comes on; a sweeping one's posts sliding
with it), the presses' shadows growing on their beds and the rams slamming
down, the live spans crackling before they arc and the arcs themselves, the
sweepers' lanes marked and the sweepers spraying down them. Only what's in
view (the plan's chunk indexes).

M32.2: a district's gates sealed in lockdown (their beams doubled and
bright), the machines' tells (`draw_panopticon_tells`, from
render/plains.draw_plains_tells: a camera's cone, a drone's searchlight, an
eye over each machine that sees you, the charges and crates in the air,
the warden's beam and tether, a welder's torch, a hauler's lane, an
assembler's build, the foreman's presses and bark), and the screen's edge
pulsing magenta in lockdown (`draw_lockdown`).
"""

from __future__ import annotations

import math

from .. import config, palette
import pygame

from ..systems import alert as city_alert
from ..systems.panopticon import dead_spans, fence_state, plan_of_scene, press_now, span_now
from .ascii_fx import _Batch


def _beam_glyph(dx: float, dy: float) -> str:
    if abs(dx) > 2 * abs(dy):
        return "-"
    if abs(dy) > 2 * abs(dx):
        return "|"
    return "\\" if dx * dy > 0 else "/"


def _along(batch, camera, x0, y0, x1, y1, step, glyph, col) -> None:
    n = max(1, int(math.hypot(x1 - x0, y1 - y0) / step))
    for q in range(n + 1):
        f = q / n
        px, py = camera.world_to_px(x0 + (x1 - x0) * f, y0 + (y1 - y0) * f)
        batch.put_c(px, py, glyph, col)


def draw_panopticon(text, camera, scene) -> None:
    city = getattr(scene, "city", None)
    if city is None:
        return
    plan = plan_of_scene(scene)
    if plan is None:
        return
    tx0, ty0, tx1, ty1 = camera.visible_tiles()
    mx, my = (tx0 + tx1) / 2, (ty0 + ty1) / 2
    if not plan.zone.near(mx, my, max(tx1 - tx0, ty1 - ty0) + config.PANOPTICON_OIL):
        return
    reach = (max(tx1 - tx0, ty1 - ty0) // config.CHUNK_SIZE) // 2 + 1
    t = city.clock
    batch = _Batch(text)

    def seen(x, y, pad=2.0):
        return tx0 - pad <= x <= tx1 + 1 + pad and ty0 - pad <= y <= ty1 + 1 + pad

    sealed = city_alert.alert_of(scene.world).sealed
    for i in plan.near(plan._fence_idx, mx, my, reach):
        f = plan.fences[i]
        state, (x0, y0, x1, y1) = fence_state(plan, i, t, sealed)
        if not (seen(x0, y0, 8) or seen(x1, y1, 8)):
            continue
        if state == "sealed":                            # (M32.2: lockdown, doubled and bright)
            dx, dy = x1 - x0, y1 - y0
            ll = math.hypot(dx, dy) or 1.0
            nx, ny = -dy / ll * 0.3, dx / ll * 0.3
            g = _beam_glyph(dx, dy)
            for k, side in enumerate((-1, 1)):
                col = palette.SEALED_BEAM[(int(t * 10) + k) % 2]
                _along(batch, camera, x0 + nx * side, y0 + ny * side, x1 + nx * side,
                       y1 + ny * side, 0.4, g, col)
            continue
        if state == "on":
            col = palette.LASER_BEAM[int(t * 20 + i) % 2]
            _along(batch, camera, x0, y0, x1, y1, 0.5, _beam_glyph(x1 - x0, y1 - y0), col)
            if f.kind == "sweep":                        # (its posts, sliding with it)
                for x, y in ((x0, y0), (x1, y1)):
                    px, py = camera.world_to_px(x, y)
                    batch.put_c(px, py, "#", palette.LASER_POST_FG)
        elif state == "tell":
            _along(batch, camera, x0, y0, x1, y1, 1.0, ".", palette.LASER_TELL)
    tw, th = config.TILE_PX_W, config.TILE_PX_H
    for i in plan.near(plan._press_idx, mx, my, reach):
        state, q, _ = press_now(plan.presses[i], t)
        if state == "up":
            continue
        for tx, ty in plan.press_beds.get(i, ()):
            if not seen(tx, ty, 0):
                continue
            px, py = camera.tile_to_px(tx, ty)
            if state == "down":
                batch.put_px(px, py, "▓▓", palette.PRESS_RAM[0], palette.PRESS_RAM[1])
            else:
                glyph = ".." if q < 0.4 else "::" if q < 0.75 else "##"
                batch.put_c(px + tw / 2, py + th / 2, glyph, palette.PRESS_SHADOW[1 if q > 0.75 else 0])
    dead = dead_spans(scene.world)
    for s in plan.near(plan._span_idx, mx, my, reach):
        if s in dead:
            continue
        state, q, cycle = span_now(s, t)
        if state == "idle":
            continue
        i, j, ax, ay, bx, by = plan.spans[s]
        if not (seen(ax, ay) or seen(bx, by)):
            continue
        if state == "tell":                              # (sparks crawling along it)
            for k in range(3):
                f = ((t * 3.1 + k * 0.37 + s * 0.13) % 1.0)
                px, py = camera.world_to_px(ax + (bx - ax) * f, ay + (by - ay) * f)
                batch.put_c(px, py, "*" if k % 2 else "'", palette.ARC_TELL[k % 2])
            for x, y, own in ((ax, ay, True), (bx, by, j >= 0)):
                if own:
                    px, py = camera.world_to_px(x, y)
                    batch.put_c(px, py - th * 0.5, "*", palette.ARC_TELL[0 if q > 0.5 else 1])
            continue
        n = max(2, int(math.hypot(bx - ax, by - ay) / 0.6))
        nx, ny = -(by - ay), bx - ax
        ll = math.hypot(nx, ny) or 1.0
        nx, ny = nx / ll, ny / ll
        for k in range(n + 1):
            f = k / n
            w = (0.35 if (k + cycle) % 2 else -0.35) if 0 < k < n else 0.0
            px, py = camera.world_to_px(ax + (bx - ax) * f + nx * w, ay + (by - ay) * f + ny * w)
            batch.put_c(px, py, "*" if k % 3 == 0 else ("/" if w > 0 else "\\"), palette.ARC[k % 2])
    sweep = config.PANOPTICON_SWEEP
    for x0, y0, ux, uy, length, half, st, _ in city.sweeps:
        if not (seen(x0, y0, length) or seen(x0 + ux * length, y0 + uy * length, 4)):
            continue
        vx, vy = -uy, ux
        if st < 0:                                       # (its lane marked)
            col = palette.SWEEP_MARK[int(t * 6) % 2]
            for side in (-1, 1):
                ex, ey = x0 + vx * half * side, y0 + vy * half * side
                _along(batch, camera, ex, ey, ex + ux * length, ey + uy * length, 1.0, "=", col)
            arrow = ">" if ux > 0.5 else "<" if ux < -0.5 else "v" if uy > 0.5 else "^"
            d = (t * 6) % 3.0
            while d < length:
                px, py = camera.world_to_px(x0 + ux * d, y0 + uy * d)
                batch.put_c(px, py, arrow, palette.SWEEP_MARK[0])
                d += 3.0
            continue
        pos = min(length, st * sweep[3])
        w = -half
        while w <= half + 1e-6:                          # (the sweeper, across the lane)
            x, y = x0 + ux * pos + vx * w, y0 + uy * pos + vy * w
            px, py = camera.world_to_px(x, y)
            batch.put_px(px - tw / 2, py - th / 2, "##", palette.SWEEPER[0], palette.SWEEPER[1])
            for k, ahead in enumerate((0.9, 1.7)):       # (its spray, ahead of it)
                sx, sy = camera.world_to_px(x + ux * ahead, y + uy * ahead)
                batch.put_c(sx, sy, "*" if (k + int(t * 12)) % 2 else "'", palette.SPRAY[k])
            w += 1.0
    batch.flush()


# --- M32.2: the machines' tells ---------------------------------------------------------


def _blink(left: float, cols) -> tuple:
    return cols[0 if int(left * (8 if left > 0.3 else 16)) % 2 == 0 else 1]


def _ray(batch, camera, x0, y0, angle, length, step, glyph, col) -> None:
    ca, sa = math.cos(angle), math.sin(angle)
    d = step * 0.5
    while d <= length:
        px, py = camera.world_to_px(x0 + ca * d, y0 + sa * d)
        batch.put_c(px, py, glyph, col)
        d += step


def _cone(batch, camera, x, y, angle, reach, half, col, step=1.4) -> None:
    """A cone's two edges and its far rim, dotted."""
    tw, th = config.TILE_PX_W, config.TILE_PX_H
    for side in (-1, 1):
        _ray(batch, camera, x, y, angle + side * half, reach, step, ".", col)
    n = max(3, int(reach * half * 2.8 / step))
    px, py = camera.world_to_px(x, y)
    for k in range(n + 1):
        a = angle - half + 2 * half * k / n
        batch.put_c(px + math.cos(a) * reach * tw, py + math.sin(a) * reach * th, ".", col)


def _ring(batch, camera, x, y, r, glyph, col, n=None) -> None:
    tw, th = config.TILE_PX_W, config.TILE_PX_H
    n = n or max(8, int(r * 6))
    px, py = camera.world_to_px(x, y)
    for k in range(n):
        a = k * math.tau / n
        batch.put_c(px + math.cos(a) * r * tw, py + math.sin(a) * r * th, glyph, col)


def _lobs(batch, camera, e) -> None:
    """What a machine has in the air: the arc, and the ring where it lands."""
    for x0, y0, x1, y1, s, of, what in e.lobs:
        f = s / of if of > 0 else 1.0
        x, y = x0 + (x1 - x0) * f, y0 + (y1 - y0) * f
        px, py = camera.world_to_px(x, y)
        lift = math.sin(math.pi * f) * 40
        if what == "crate":
            batch.put_c(px, py - lift, "#", palette.CRATE_FLY)
            _ring(batch, camera, x1, y1, config.HAULER[8], "o", _blink(of - s, palette.HAUL_LANE))
        else:
            batch.put_c(px, py - lift, "@", palette.STUN_RING[0])
            _ring(batch, camera, x1, y1, config.RIOT[8], "o", _blink(of - s, palette.STUN_RING))


def draw_panopticon_tells(batch, camera, e) -> None:
    """Over one of Panopticon's machines: what it sees and what's coming."""
    from ..ai.panopticon import (Assembler, Camera, Foreman, Hauler, Machine, RiotRobot,
                                 SentryDrone, Spotter, Turret, Warden, Welder)
    if not isinstance(e, Machine) or e.dormant:
        return
    x, y = camera.world_to_px(e.x, e.y)
    top = y - e.espec.scale * 9 - 10
    seeing = e.seeing
    if isinstance(e, Camera) and e.base is not None:
        cone = math.radians(config.PANOPTICON_CAMERAS[2]) / 2
        _cone(batch, camera, e.x, e.y, e.facing, config.PANOPTICON_CAMERAS[3], cone,
              palette.CAMERA_CONE[1 if seeing is not None else 0])
    if isinstance(e, SentryDrone):
        lit = e.prey is not None
        _cone(batch, camera, e.x, e.y, e.light, config.DRONE[2], math.radians(config.DRONE[1]) / 2,
              palette.SEARCHLIGHT[1 if lit else 0], 2.0)
    if isinstance(e, Spotter) and seeing is not None:                 # (its gaze on you)
        _along(batch, camera, e.x, e.y, seeing.x, seeing.y, 1.2, ".", palette.SEEN_EYE[0])
    if seeing is not None and not isinstance(e, Camera):
        batch.put_c(x, top - (22 if e.espec.elite else 10), "o",
                    palette.SEEN_EYE[int(e.clock * 6) % 2])
    if isinstance(e, Turret) and e.windup > 0:
        _ray(batch, camera, e.x, e.y, e.facing, 6.0, 1.0, ".", _blink(e.windup, palette.SEEN_EYE))
    if e.lobs:
        _lobs(batch, camera, e)
    if isinstance(e, RiotRobot) and e.blocked > 0:                   # (a hit off the shield)
        sx, sy = camera.world_to_px(e.x + math.cos(e.facing) * 1.2, e.y + math.sin(e.facing) * 1.2)
        batch.put_c(sx, sy, "*", palette.SPARK_HOT)
    if isinstance(e, RiotRobot) and e.state == "shove":
        from .pangaea import _shape
        _shape(batch, camera, "cone", e.x, e.y, e.facing, e.espec.attack_radius,
               math.radians(config.RIOT[2]) / 2, _blink(e.timer, palette.HAUL_LANE))
    if isinstance(e, Warden):
        _warden(batch, camera, e)
    if isinstance(e, Welder) and e.state in ("flare", "drag"):
        a = e.torch if e.state == "drag" else e.facing
        reach = e.espec.attack_radius
        col = palette.TORCH[int(e.clock * 14) % 2]
        _ray(batch, camera, e.x, e.y, a, reach, 0.4, "*" if e.state == "drag" else ".", col)
        if e.state == "flare":
            from .pangaea import _shape
            _shape(batch, camera, "cone", e.x, e.y, e.facing, reach,
                   math.radians(config.WELDER[1]) / 2, _blink(e.timer, palette.TORCH))
    if isinstance(e, Hauler) and e.state == "line":
        col = _blink(e.timer, palette.HAUL_LANE)
        ca, sa = math.cos(e.aim), math.sin(e.aim)
        for side in (-1, 1):
            off = side * e.hit_radius
            _ray(batch, camera, e.x - sa * off, e.y + ca * off, e.aim, config.HAULER[2], 1.0, ".", col)
    if isinstance(e, Assembler) and e.state == "build":               # (the build bar)
        n = 8
        done = round(e.progress * n)
        bx = x - n * 3
        for k in range(n):
            batch.put_c(bx + k * 6, top - 4, "=" if k < done else "-",
                        palette.BUILD_BAR[0 if k < done else 1])
        sx, sy = camera.world_to_px(*e.build_at)
        batch.put_c(sx, sy, "*" if int(e.clock * 12) % 2 else "+", palette.TORCH[0])
    if isinstance(e, Foreman):
        for dx, dy, s in e.drops:
            q = s / config.FOREMAN[8]
            col = palette.FOREMAN_DROP[1 if q > 0.7 else 0]
            r = config.FOREMAN[9] * (0.4 + 0.6 * q)
            _ring(batch, camera, dx, dy, r, "#" if q > 0.7 else ":", col, 10)
            px, py = camera.world_to_px(dx, dy)
            batch.put_c(px, py, "x", palette.FOREMAN_DROP[1])
        for r, _ in e.rings:
            _ring(batch, camera, e.x, e.y, r, "o", palette.BARK_RING[0])
    if getattr(e, "hunter", False):
        batch.put_c(x + 12, top, "!", palette.SEEN_EYE[0])


def _warden(batch, camera, e) -> None:
    if e.marking is not None:                            # (its eye on you: marking)
        h = e.marking
        col = palette.SEEN_EYE[int(e.mark_t * (8 if e.mark_t < 0.8 else 16)) % 2]
        _along(batch, camera, e.x, e.y, h.x, h.y, 0.8, "-", col)
    if e.state == "aim":                                 # (the arc it'll sweep)
        col = _blink(e.timer, palette.WARDEN_BEAM)
        for a in (e.beam_from, e.beam_to):
            _ray(batch, camera, e.x, e.y, a, config.WARDEN[6], 1.2, ".", col)
    if e.state == "beam":
        a = e.beam_angle
        col = palette.WARDEN_BEAM[int(e.clock * 20) % 2]
        _ray(batch, camera, e.x, e.y, a, e.beam_len, 0.5, _beam_glyph(math.cos(a), math.sin(a)), col)
    if e.state == "backhand":
        from .pangaea import _shape
        _shape(batch, camera, "cone", e.x, e.y, e.facing, e.espec.attack_radius,
               math.radians(config.WARDEN[13]) / 2, _blink(e.timer, palette.WARDEN_BEAM))
    if e.chained is not None:                            # (the tether to its spot)
        h, ax, ay, _ = e.chained
        _along(batch, camera, ax, ay, h.x, h.y, 0.5, "-", palette.TETHER[int(e.clock * 8) % 2])
        px, py = camera.world_to_px(ax, ay)
        batch.put_c(px, py, "@", palette.TETHER[0])


# --- M32.2: lockdown --------------------------------------------------------------------

_EDGE: dict = {}


def draw_lockdown(canvas, scene, hero) -> None:
    """In lockdown, for a hero on the island, the screen's edge pulses
    magenta (a frame baked once per canvas size; only its alpha changes)."""
    hud = getattr(hero, "alert_hud", None)
    if hud is None or hud[0] != city_alert.LOCKDOWN:
        return
    w, h = canvas.get_size()
    img = _EDGE.get((w, h))
    if img is None:
        img = pygame.Surface((w, h), pygame.SRCALPHA)
        col = palette.LOCKDOWN_EDGE[0]
        band = max(6, min(w, h) // 28)
        for k in range(band):
            a = round(150 * (1 - k / band) ** 2)
            pygame.draw.rect(img, (*col, a), pygame.Rect(k, k, w - 2 * k, h - 2 * k), 1)
        _EDGE.clear()
        _EDGE[(w, h)] = img
    pulse = 0.5 + 0.5 * math.sin(scene.steps / config.SIM_HZ * math.tau * 1.2)
    img.set_alpha(round(90 + 160 * pulse))
    canvas.blit(img, (0, 0))
