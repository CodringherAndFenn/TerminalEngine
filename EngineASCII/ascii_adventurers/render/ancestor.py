"""
render/ancestor.py -- the Ancestor, form 1 (M31.4, ai/ancestor.py): its body
in each age (render/pangaea_art.py's pictures), flickering between the old
shape and the new while it moults; the husks it leaves (the old shape, dry
and dull, over the husk tiles); its echoes (render/pangaea.draw_echoes: a
faded ghost where it stood, the shape coming again); the stampede's spirit
herd (in ochre, its echo in ghost blue); the swarm's rivers (insects
streaming along a drifting band; before they sting, the band they'll pour
down, blinking); and its tells: the lanes, the roar's and the sweep's cones,
a charge's line, a spit fan's lines, a shadow under it in the air.

M31.5, form 2 (the first life): what's in the sea is render/first_life.py's;
here its body (nothing of it while it's under the sea; flickering between
the insect and the first life while it rises), and the husks woken as
echoes of the ages (ghosts of their ages over their skins) with what they're
about to do (a stampede's lanes, a roar's cone).
"""

from __future__ import annotations

import math

from .. import config, palette
from ..ai.ancestor import Ancestor, River
from .ascii_fx import _Batch
from .characters import draw_character
from .pangaea import _blink, _figure, _shape, draw_echoes

_STEP = 1.4                 # tiles between the dots of a lane's or a river's line


def _view(camera, pad: float = 3.0) -> tuple[float, float, float, float]:
    x0, y0 = camera.canvas_to_world(0, 0)
    x1, y1 = camera.canvas_to_world(camera.view_w, camera.view_h)
    return x0 - pad, y0 - pad, x1 + pad, y1 + pad


def _rail(batch, camera, view, x0, y0, angle, length, off, glyph, col, step=_STEP, shift=0.0):
    """Dots along a line (`off` tiles to its side), only those in view."""
    vx0, vy0, vx1, vy1 = view
    ca, sa = math.cos(angle), math.sin(angle)
    k = shift % step
    while k <= length:
        x, y = x0 + ca * k - sa * off, y0 + sa * k + ca * off
        if vx0 <= x <= vx1 and vy0 <= y <= vy1:
            px, py = camera.world_to_px(x, y)
            batch.put_c(px, py, glyph, col)
        k += step


def _arrow(angle: float) -> str:
    """The glyph pointing along `angle` (screen y grows down)."""
    k = round((angle % math.tau) / (math.pi / 2)) % 4
    return (">", "v", "<", "^")[k]


def _lane(batch, camera, view, x0, y0, angle, length, half, col, edge, shift=0.0) -> None:
    """A lane something will run down: arrows down its middle the way it'll
    run, its edges dotted (dimmer)."""
    _rail(batch, camera, view, x0, y0, angle, length, 0.0, _arrow(angle), col, step=1.2,
          shift=shift)
    for side in (-1, 1):
        _rail(batch, camera, view, x0, y0, angle, length, side * half, ".", edge, step=1.2)


def _river(batch, camera, view, b: Ancestor, r, clock: float, col_set, t: float | None = None,
           tell: bool = False) -> None:
    """A river of insects: along its band's line as it is `t` s in."""
    off = r.offset(t)
    ca, sa = math.cos(r.angle), math.sin(r.angle)
    c = b._chord(r.x0 - sa * off, r.y0 + ca * off, r.angle, grow=2.0)
    if c is None:
        return
    sx, sy, length = c
    if tell or not r.stinging:
        col = _blink(r.shown - r.t if not tell else clock % 0.5, col_set)
        for side in (-1, 1):
            _rail(batch, camera, view, sx, sy, r.angle, length, side * r.half, ".", col)
        return
    flow = clock * 7.0
    for lane, (glyph, col) in enumerate(((".", col_set[1]), (":", col_set[0]), ("'", col_set[-1]))):
        wob = math.sin(clock * 5 + lane * 2.1) * 0.3
        _rail(batch, camera, view, sx, sy, r.angle, length, (lane - 1) * r.half * 0.6 + wob,
              glyph, col, step=0.9 if lane == 1 else 1.1, shift=flow + lane * 0.4)


def draw_ancestor(text, bank, camera, b: Ancestor) -> None:
    clock = b.time
    view = _view(camera)
    scale = b.espec.scale
    for h in b.husks:                                  # (the old bodies, lying there)
        if not h.crumbled:
            _figure(bank, camera, h.x, h.y, h.sprite, scale, math.cos(h.facing) < 0,
                    "ghost" if h.awake and int(clock * 3 + h.age) % 3 else "husk")
    draw_echoes(text, bank, camera, b, scale)
    if b.form != 1:
        from .first_life import draw_first_life
        draw_first_life(text, bank, camera, b, view, clock)
    batch = _Batch(text)
    for ech in b.echoes:                               # (a river coming again)
        if ech.kind == "river" and ech.t <= ech.tell:
            _river(batch, camera, view, b, River(**ech.data), clock, palette.ECHO_TELL, t=0.0,
                   tell=True)
    for r in b.rivers:
        _river(batch, camera, view, b, r, clock, palette.SWARM_ECHO if r.echo else palette.SWARM)
    for r in b.runners:                                # (a running spirit's lane, ahead of it)
        if r.look == "ochre" or r.sprite in ("mammoth", "woolly_rhino"):
            ahead = max(0.0, r.done)
            col = palette.ECHO_TELL[1] if r.look == "ghost" else palette.ANCESTOR_TELL[1]
            _lane(batch, camera, view, r.x0 + math.cos(r.angle) * ahead,
                  r.y0 + math.sin(r.angle) * ahead, r.angle, r.length - ahead, r.radius, col, col)
    for src in [b] + [h for h in b.husks if h.awake]:  # (the spirit herd's lanes; a roar's cone)
        for x0, y0, a, length, half in src.lanes:
            _lane(batch, camera, view, x0, y0, a, length, half,
                  _blink(clock % 0.6, palette.ANCESTOR_TELL), palette.ANCESTOR_TELL[1],
                  shift=clock * 4)
        if src.cone is not None:
            x, y, a, reach, half = src.cone
            _shape(batch, camera, "cone", x, y, a, reach, half,
                   _blink(clock % 0.5, palette.ANCESTOR_TELL))
    if b.line is not None:
        x0, y0, a, length, half = b.line
        _lane(batch, camera, view, x0, y0, a, length, half,
              _blink(clock % 0.5, palette.ANCESTOR_TELL), palette.ANCESTOR_TELL[1], shift=clock * 4)
    for a in b.fans:
        _rail(batch, camera, view, b.x, b.y, a, 7.0, 0.0, ".", palette.ANCESTOR_TELL[1], step=1.0)
    x, y = camera.world_to_px(b.x, b.y)
    lift = 0
    if b.airborne > 0:                                 # (the insect up in the air, its shadow)
        lift = 26
        batch.put_c(x, y + scale * 6, "___", palette.BOMB_SHADOW)
    batch.flush()
    if b.submerged:                                    # (under the sea: only its ripple shows)
        return
    sprite = b.sprite_now()
    if b.moulting > 0 and int(b.moulting * 10) % 2 == 0 and b.husks:
        sprite = b.husks[-1].sprite                    # (bursting out of the old skin)
    if b.form == "rising" and int(b.rise_t * 6) % 2 == 0 and b.husks:
        sprite = b.husks[-1].sprite                    # (the first life rising out of the insect)
    frame = int(b.walked * 1.2) % 2
    draw_character(bank, x, y - lift, sprite, scale, math.cos(b.facing) < 0, frame, b.hurt_flash > 0)
    if b.tell is not None and (b.planted or b.busy) and int(clock * 8) % 2:
        batch = _Batch(text)
        batch.put_c(x, y - lift - scale * 10, "!", palette.PLAINS_TELL[0])
        batch.flush()
