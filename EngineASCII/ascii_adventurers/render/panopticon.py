"""
render/panopticon.py -- the dangers of Panopticon's land drawn over its
tiles (M32.1, systems/panopticon.py): the laser fences' beams (and a faint
line just before a blinking one comes on; a sweeping one's posts sliding
with it), the presses' shadows growing on their beds and the rams slamming
down, the live spans crackling before they arc and the arcs themselves, the
sweepers' lanes marked and the sweepers spraying down them. Only what's in
view (the plan's chunk indexes).
"""

from __future__ import annotations

import math

from .. import config, palette
from ..systems.panopticon import dead_spans, fence_now, plan_of_scene, press_now, span_now
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

    for i in plan.near(plan._fence_idx, mx, my, reach):
        f = plan.fences[i]
        state, (x0, y0, x1, y1) = fence_now(f, t)
        if not (seen(x0, y0, 8) or seen(x1, y1, 8)):
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
