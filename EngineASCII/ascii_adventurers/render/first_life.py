"""
render/first_life.py -- the Ancestor's second form, the first life (M31.5,
ai/first_life.py), drawn under its body by render/ancestor.draw_ancestor.
The flooded caldera is tiles (the shallows, the deep, the rocks in the tide:
world/tiles.py); this draws what's in the sea: a whirlpool's tell (its rim
blinking) and its spiralling current; boiling bubbles' marked rings; the
tidal wave's front (where it'll start, then the crest and its trail rolling
across the caldera); its arms -- a lash's shown line, then the arm whipping
out and dragging back; a tentacle's rippling spot and its marked arc, then
the arm sweeping through it; the swelling ripple where it'll surface; and the
echoes of all of these about to play again (their tells in ghost blue, a
ghost of whatever did it).
"""

from __future__ import annotations

import math

from .. import config, palette
from ..ai.first_life import Lash, Sweep, Whirl, Wave
from .ascii_fx import _Batch
from .pangaea import _blink, _figure, _shape

_TAU = math.tau
KINDS = ("whirl", "bubbles", "lashes", "sweeps", "wave")   # (its own echoes' kinds)


def _chain(batch, camera, view, x0, y0, angle, length, cols, step=0.8) -> None:
    """An arm from (x0, y0) along `angle`: segments, its tip."""
    vx0, vy0, vx1, vy1 = view
    ca, sa = math.cos(angle), math.sin(angle)
    k = 0.4
    while k < length - 0.3:
        x, y = x0 + ca * k, y0 + sa * k
        if vx0 <= x <= vx1 and vy0 <= y <= vy1:
            px, py = camera.world_to_px(x, y)
            batch.put_c(px, py, "o" if k < length * 0.6 else "s", cols[1])
        k += step
    px, py = camera.world_to_px(x0 + ca * length, y0 + sa * length)
    batch.put_c(px, py, "@", cols[0])


def _dots(batch, camera, view, x0, y0, angle, length, glyph, col, step=1.0, off=0.0) -> None:
    from .ancestor import _rail
    _rail(batch, camera, view, x0, y0, angle, length, off, glyph, col, step=step)


def _whirl(batch, camera, view, w: Whirl, clock: float, tell: bool = False) -> None:
    cols = palette.WHIRL_ECHO if (w.echo or tell) else palette.WHIRL
    if tell or not w.spinning:
        left = clock % 0.5 if tell else w.shown - w.t
        _shape(batch, camera, "circle", w.x, w.y, 0.0, w.radius, 0.0,
               _blink(left, palette.ECHO_TELL if tell else (cols[0], cols[1])))
        return
    t = w.t - w.shown
    for arm in range(4):                              # (four arms spiralling in)
        r = w.core * 0.4
        while r <= w.radius:
            a = arm * _TAU / 4 + w.turn * (t * 3.2 - r * 0.42)
            x, y = w.x + math.cos(a) * r, w.y + math.sin(a) * r * 0.9
            if view[0] <= x <= view[2] and view[1] <= y <= view[3]:
                px, py = camera.world_to_px(x, y)
                k = 0 if r < w.core + 0.5 else 1 if r < w.radius * 0.6 else 2
                batch.put_c(px, py, ("@", "o", ":")[k], cols[k])
            r += 0.6
    n = max(12, int(w.radius * 5))                    # (its rim, turning)
    px, py = camera.world_to_px(w.x, w.y)
    for j in range(n):
        a = j * _TAU / n + w.turn * t
        batch.put_c(px + math.cos(a) * w.radius * config.TILE_PX_W,
                    py + math.sin(a) * w.radius * 0.9 * config.TILE_PX_H, "." if j % 2 else ":",
                    cols[2])


def _wave_line(batch, camera, view, b, fx, fy, angle, glyph, col, off=0.0) -> None:
    """A line square to `angle` through (fx, fy), across the caldera."""
    side = angle + math.pi / 2
    c = b._chord(fx - math.cos(angle) * off, fy - math.sin(angle) * off, side)
    if c is not None:
        _dots(batch, camera, view, c[0], c[1], side, c[2], glyph, col)


def _wave(batch, camera, view, b, w: Wave, tell: bool = False) -> None:
    if tell:
        _wave_line(batch, camera, view, b, w.x0, w.y0, w.angle, "=", palette.ECHO_TELL[0])
        return
    fx, fy = w.front
    cols = (palette.ECHO_TELL[0], palette.ECHO_TELL[1], palette.ECHO_TELL[1]) if w.echo \
        else palette.WAVE_FRONT
    for off, glyph, col in ((0.0, "^", cols[0]), (0.7, "=", cols[0]), (1.6, "#", cols[1]),
                            (2.6, ":", cols[1]), (3.8, ".", cols[2])):   # (the crest, the swell)
        _wave_line(batch, camera, view, b, fx, fy, w.angle, glyph, col, off=off)


def _wave_coming(batch, camera, view, b, clock: float) -> None:
    """Before it rolls: the line it'll start from, and arrows the way it'll go."""
    from .ancestor import _arrow
    x0, y0, a, length = b.wave_tell
    col = _blink(clock % 0.5, palette.ANCESTOR_TELL)
    _wave_line(batch, camera, view, b, x0, y0, a, "=", col)
    side = a + math.pi / 2
    for k in range(-6, 7):
        for f in (3.0, 9.0, 15.0):
            x = x0 + math.cos(side) * k * 5.0 + math.cos(a) * f
            y = y0 + math.sin(side) * k * 5.0 + math.sin(a) * f
            if b._inside(x, y) and view[0] <= x <= view[2] and view[1] <= y <= view[3]:
                px, py = camera.world_to_px(x, y)
                batch.put_c(px, py, _arrow(a), palette.ANCESTOR_TELL[1])


def _sweep(batch, camera, view, s: Sweep, clock: float, tell: bool = False) -> None:
    if tell or not s.up:
        col = _blink(clock % 0.5 if tell else s.shown - s.t,
                     palette.ECHO_TELL if (tell or s.echo) else palette.ANCESTOR_TELL)
        _shape(batch, camera, "circle", s.bx, s.by, 0.0, 1.0 + 0.4 * math.sin(clock * 9), 0.0, col)
        for a in (s.a0, s.a0 + s.arc):
            _dots(batch, camera, view, s.bx, s.by, a, s.length, ".", col)
        n = max(4, int(abs(s.arc) * s.length / 1.2))
        for k in range(n + 1):
            a = s.a0 + s.arc * k / n
            x, y = s.bx + math.cos(a) * s.length, s.by + math.sin(a) * s.length
            px, py = camera.world_to_px(x, y)
            batch.put_c(px, py, "o", col)
        return
    cols = palette.FIRST_ARM_ECHO if s.echo else palette.FIRST_ARM
    _chain(batch, camera, view, s.bx, s.by, s.angle, s.length, cols)
    px, py = camera.world_to_px(s.bx, s.by)
    batch.put_c(px, py, "O", cols[2])


def _lash(batch, camera, view, m: Lash, clock: float, tell: bool = False) -> None:
    if tell or m.t < m.shown:
        col = _blink(clock % 0.5 if tell else m.shown - m.t,
                     palette.ECHO_TELL if (tell or m.echo) else palette.ANCESTOR_TELL)
        _dots(batch, camera, view, m.x0, m.y0, m.angle, m.length, ".", col)
        return
    if m.len > 0.3:
        _chain(batch, camera, view, m.x0, m.y0, m.angle, m.len,
               palette.FIRST_ARM_ECHO if m.echo else palette.FIRST_ARM)


def _ripple(batch, camera, x, y, q: float, clock: float) -> None:
    """Where it'll burst up: rings swelling, faster as it comes."""
    tw, th = config.TILE_PX_W, config.TILE_PX_H
    px, py = camera.world_to_px(x, y)
    fast = 10 if q < 0.6 else 20
    for k, r in enumerate((0.6 + 2.6 * q, 0.3 + 1.4 * q)):
        n = max(8, int(r * 7))
        col = palette.RIPPLE[(int(clock * fast) + k) % 2]
        for j in range(n):
            a = j * _TAU / n + clock
            batch.put_c(px + math.cos(a) * r * tw, py + math.sin(a) * r * th * 0.9,
                        "o" if j % 2 else ".", col)


def draw_first_life(text, bank, camera, b, view, clock: float) -> None:
    """Everything of form 2's under its body (see the module's docstring)."""
    batch = _Batch(text)
    scale = b.espec.scale
    for ech in b.echoes:                              # (its own kinds, coming again)
        if ech.kind not in KINDS or ech.t > ech.tell:
            continue
        d = ech.data
        if ech.kind == "whirl":
            _whirl(batch, camera, view, Whirl(**d), clock, tell=True)
        elif ech.kind == "bubbles":
            col = _blink(ech.t, palette.ECHO_TELL)
            for x, y, _ in d["spots"]:
                px, py = camera.world_to_px(x, y)
                batch.put_c(px, py, "o", col)
        elif ech.kind == "lashes":
            for p in d["arms"]:
                _lash(batch, camera, view, Lash(**p), clock, tell=True)
        elif ech.kind == "sweeps":
            for p in d["arms"]:
                _sweep(batch, camera, view, Sweep(**p), clock, tell=True)
        else:
            _wave(batch, camera, view, b, Wave(**d), tell=True)
        _figure(bank, camera, ech.x, ech.y, ech.sprite, scale, math.cos(ech.facing) < 0, "ghost")
    for w in b.whirls:
        _whirl(batch, camera, view, w, clock)
    for x, y, left, echo, radius, _ in b.bubbles:     # (a chain of them; the next ones' rings)
        cols = palette.ECHO_TELL if echo else palette.BUBBLE_MARK
        if left < 0.45:
            _shape(batch, camera, "circle", x, y, 0.0, radius, 0.0, _blink(left, cols))
        px, py = camera.world_to_px(x, y)
        batch.put_c(px, py, "O" if left < 0.45 else "o", cols[0 if left < 0.45 else 1])
    for w in b.waves:
        _wave(batch, camera, view, b, w)
    if b.wave_tell is not None:
        _wave_coming(batch, camera, view, b, clock)
    for s in b.sweeps:
        _sweep(batch, camera, view, s, clock)
    for m in b.lashes:
        _lash(batch, camera, view, m, clock)
    if b.ripple is not None:
        x, y, t, of = b.ripple
        _ripple(batch, camera, x, y, min(1.0, t / of) if of > 0 else 1.0, clock)
    batch.flush()
