"""
render/first_angel.py -- the Fossil Angel's form 2, the first angel unveiled
(M33.2, ai/first_angel.py), drawn round its body by render/fossil_angel.py.

Its wings: two of raw flesh (the stone wings' shape), six from its last
phase (the top pair raised over it, the middle pair, the low pair), the one
about to beat raised and its cone shown. Its eyes: "( )" with a red iris
on its flesh ("-" where one is closed), a gaze's line shown where it starts
(and where it ends, faint), then the beam sweeping, cut short where it's
stopped. The first word: a white ring round it while it speaks, then the
ring of light spreading across the land. Its halo's wheels: rings of fire
racing along. Red amber rising: "#" blinking over the resin that's about
to harden into a wall. The claw rake's lines are form 1's line tells in
blood red (render/fossil_angel.py).
"""

from __future__ import annotations

import math

from .. import config, palette
from ..ai.first_angel import WINGS
from .ascii_fx import _Batch
from .characters import ART_H, ART_W, draw_character
from .pangaea import _blink, _dots, _shape


def draw_wings(bank, b, x: float, by: float, scale: int, hurt: bool, up: bool) -> None:
    """Its two wings of raw flesh -- or, from its last phase, six."""
    beat = b.beating[0] if b.beating is not None else None
    if not b.six_wings:
        wing = "flesh_wing_up" if up else "flesh_wing"
        off = ART_W * scale * 0.62
        wy = ART_H * scale * (0.18 if up else 0.08)
        draw_character(bank, x + off, by - wy, wing, scale, False, 0, hurt)
        draw_character(bank, x - off, by - wy, wing, scale, True, 0, hurt)
        return
    rows = ((max(3, scale - 2), 0.30, 0.50), (scale, 0.08, 0.62), (max(3, scale - 3), -0.14, 0.50))
    for i, (side, _) in enumerate(WINGS):
        s, wy, ox = rows[i // 2]
        raised = up or i == beat or i < 2
        wing = "flesh_wing_up" if raised else "flesh_wing"
        draw_character(bank, x + side * ART_W * scale * ox, by - ART_H * scale * wy, wing, s,
                       side < 0, 0, hurt or i == beat and int(b.time * 12) % 2 == 0)


def draw_tells(batch, camera, b) -> None:
    """Under its body: the gazes' lines and beams, the beating wing's cone,
    the red amber about to rise, the word spreading."""
    clock = b.time
    reach, half = config.FOSSIL_EYES[9], config.FOSSIL_EYES[10]
    for eye in b.eyes:
        if eye is None or eye.gaze is None:
            continue
        g = eye.gaze
        if g["t"] < g["tell"]:
            col = _blink(g["tell"] - g["t"], palette.FOSSIL_GAZE)
            _dots(batch, camera, eye.x, eye.y, g["a0"], g["length"], col)
            _dots(batch, camera, eye.x, eye.y, g["a0"] + g["turn"], reach, palette.FOSSIL_GAZE[1],
                  step=2.5)
            continue
        a = eye.facing
        for off in (-half * 0.6, 0.0, half * 0.6):
            _dots(batch, camera, eye.x, eye.y, a, g["length"], palette.FOSSIL_GAZE[0], step=0.6,
                  off=off)
    if b.beating is not None:
        i, left = b.beating
        x, y = b.wing_at(i)
        t = b.nearest() if b.ctx is not None else None
        a = math.atan2(t.y - y, t.x - x) if t is not None else 0.0
        _, _, arc, wreach = config.FOSSIL_WINGS[:4]
        _shape(batch, camera, "cone", x, y, a, wreach, math.radians(arc) / 2,
               _blink(left, palette.FOSSIL_BLOOD))
    if b.red:
        col = _blink(clock % 0.4, palette.FOSSIL_BLOOD)
        for (tx, ty), (state, _, _) in b.red.items():
            if state == "rising":
                px, py = camera.world_to_px(tx + 0.5, ty + 0.5)
                batch.put_c(px, py, "#", col)
    if b.pose == "word":                                   # (it speaks)
        r = 2.0 + (clock * 6.0) % 4.0
        _shape(batch, camera, "circle", b.x, b.y, 0.0, r, 0.0, _blink(clock % 0.5, palette.FOSSIL_WORD))
    w = b.word
    if w is not None:                                      # (the ring of light spreading)
        tw, th = config.TILE_PX_W, config.TILE_PX_H
        px, py = camera.world_to_px(w["x"], w["y"])
        n = min(220, max(24, int(w["r"] * 5)))
        for k in range(n):
            a = k * math.tau / n
            batch.put_c(px + math.cos(a) * w["r"] * tw, py + math.sin(a) * w["r"] * th,
                        "O" if k % 2 else "o", palette.FOSSIL_WORD[k % 2])


def draw_over(text, camera, b, lift: float) -> None:
    """Over its body: its eyes (open, or closed), its halo's wheels."""
    batch = _Batch(text)
    for i, eye in enumerate(b.eyes):
        ex, ey = b.eye_at(i)
        px, py = camera.world_to_px(ex, ey)
        py -= lift
        if eye is None:
            batch.put_c(px, py, "-", palette.FOSSIL_EYE[2])
            continue
        hot = eye.hurt_flash > 0
        batch.put_c(px, py, "( )", palette.FOSSIL_EYE[0])
        iris = palette.FOSSIL_EYE[0] if hot else palette.FOSSIL_EYE[1]
        dx = math.cos(eye.facing) * 3
        batch.put_c(px + dx, py, "@", iris)
    tw, th = config.TILE_PX_W, config.TILE_PX_H
    for w in b.wheels:
        x, y = camera.world_to_px(w.x, w.y)
        n = 10
        for k in range(n):
            a = k * math.tau / n + w.spin
            batch.put_c(x + math.cos(a) * w.radius * tw * 0.8, y + math.sin(a) * w.radius * th * 0.7,
                        "@" if k % 3 == 0 else "o", palette.FOSSIL_FIRE[(k + int(w.t * 10)) % 3])
        batch.put_c(x, y, "*", palette.FOSSIL_FIRE[1])
    batch.flush()
