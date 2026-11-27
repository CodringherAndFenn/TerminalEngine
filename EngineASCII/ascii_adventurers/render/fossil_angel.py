"""
render/fossil_angel.py -- the Fossil Angel, form 1 (M33.1, ai/fossil_angel.py)
and the hunt every final shares (ai/finals.py).

The hunt: crouching before a leap (a "!" over it), up in the air (its
shadow on the ground, the body high above it), and where it will land (a
ring that tightens and flashes faster as it comes, an "x" in the middle).

The angel: its body (render/finals_art.py), a stone wing either side
(folded, or beating up while it calls something down), its halo of lava
over its head (gone while it's rolling as a wheel, or cooled); its echoes
(render/pangaea.draw_echoes: a faded ghost where it stood, the shape coming
again; the falling stars too); and its tells: the feathers' lines, the wing
sweep's and the ash breath's cones, the dive's line, a "!" while it's
planted. The resin it weeps shows as RESIN tiles; ahead of a river's front
the way it will run blinks. The wheel (LavaHalo): a spinning ring of fire.

M33.2: while it unveils, its bones and wings flicker into flesh; form 2's
wings, eyes, gazes, word and wheels are render/first_angel.py's.
"""

from __future__ import annotations

import math

from .. import config, palette
from ..ai.fossil_angel import FossilAngel, LavaHalo
from . import finals_art  # noqa: F401  (adds the pictures to ART)
from . import first_angel
from .ascii_fx import _Batch
from .characters import ART_H, ART_W, draw_character
from .pangaea import _blink, _dots, _shape, draw_echoes

_WINGS = ("beat", "halo", "weep", "word")


def draw_leap(batch, camera, b) -> float:
    """A final's leap (any final's): the landing mark, its shadow. Returns
    how high its body is drawn (canvas px)."""
    lift = 0.0
    if b.mark is not None:
        x1, y1 = b.mark
        leap = b.leap
        left = config.FINAL_LEAP[2] - (leap[1] if leap is not None and leap[0] == "air" else 0.0)
        r = config.FINAL_LEAP[5] * (0.8 + 0.2 * max(0.0, min(1.0, left / config.FINAL_LEAP[2])))
        col = _blink(left, palette.FINAL_LEAP_MARK)
        _shape(batch, camera, "circle", x1, y1, 0.0, r, 0.0, col)
        px, py = camera.world_to_px(x1, y1)
        batch.put_c(px, py, "x", col)
    if b.airborne > 0:
        high = b.leap is not None and b.leap[0] == "air"
        lift = b.airborne * (160.0 if high else 26.0)
        x, y = camera.world_to_px(b.x, b.y)
        batch.put_c(x, y + b.espec.scale * 6, "_____" if lift > 40 else "___", palette.FINAL_SHADOW)
    return lift


def draw_fossil_angel(text, bank, camera, b: FossilAngel) -> None:
    clock = b.time
    scale = b.espec.scale
    draw_echoes(text, bank, camera, b, scale)
    batch = _Batch(text)
    lift = draw_leap(batch, camera, b)
    tell = _blink(clock % 0.5, palette.FOSSIL_TELL)
    rake = b.pose == "rake"                                # (M33.2: the claw rake's, in blood)
    lcol = _blink(clock % 0.5, palette.FOSSIL_BLOOD) if rake else tell
    for x0, y0, a, length, half in b.lines:               # (the feathers' lines, the rake's)
        for side in (-1, 1):
            _dots(batch, camera, x0, y0, a, length, lcol, off=side * half)
        _dots(batch, camera, x0, y0, a, length,
              palette.FOSSIL_BLOOD[1] if rake else palette.FOSSIL_TELL[1], step=2.0)
    if b.form == 2:
        first_angel.draw_tells(batch, camera, b)
    if b.cone is not None:
        x, y, a, reach, half = b.cone
        _shape(batch, camera, "cone", x, y, a, reach, half, tell)
    if b.line is not None:                                 # (the dive's line)
        x0, y0, a, length, half = b.line
        for side in (-1, 1):
            _dots(batch, camera, x0, y0, a, length, tell, off=side * half)
    for r in b.rivers:                                     # (where the resin will run)
        left = r["length"] - r["done"]
        if left <= 0.5:
            continue
        ca, sa = math.cos(r["angle"]), math.sin(r["angle"])
        _dots(batch, camera, r["x0"] + ca * r["done"], r["y0"] + sa * r["done"], r["angle"], left,
              _blink(clock % 0.4, palette.FOSSIL_RESIN), step=1.2)
    x, y = camera.world_to_px(b.x, b.y)
    batch.flush()
    hurt = b.hurt_flash > 0
    by = y - lift + (6 if b.pose == "crouch" or (b.leap is not None and b.leap[0] == "crouch")
                     else 0)
    up = b.pose in _WINGS or (b.leap is not None and b.leap[0] == "air")
    flesh = b.form == 2 or (b.form == "unveiling" and b.sprite_now() == "fossil_angel_flesh")
    if flesh:
        first_angel.draw_wings(bank, b, x, by, scale, hurt, up)
    else:
        wing = "fossil_wing_up" if up else "fossil_wing"
        off = ART_W * scale * 0.62
        wy = ART_H * scale * (0.18 if up else 0.08)
        draw_character(bank, x + off, by - wy, wing, scale, False, 0, hurt)
        draw_character(bank, x - off, by - wy, wing, scale, True, 0, hurt)
    frame = int(b.walked * 1.2) % 2
    draw_character(bank, x, by, b.sprite_now(), scale, math.cos(b.facing) < 0, frame, hurt)
    batch = _Batch(text)
    if b.has_halo:                                         # (its halo of lava over its head)
        hx, hy = x, by - ART_H * scale / 2 + scale * 1.5 - 14
        n = 12
        for k in range(n):
            a = k * math.tau / n + clock * 2.0
            batch.put_c(hx + math.cos(a) * 26, hy + math.sin(a) * 7,
                        "o" if k % 2 else "*", palette.FOSSIL_FIRE[(k + int(clock * 8)) % 3])
    if (b.planted or (b.leap is not None and b.leap[0] == "crouch")) and int(clock * 8) % 2:
        batch.put_c(x, by - ART_H * scale / 2 - 28, "!", palette.PLAINS_TELL[0])
    batch.flush()
    if b.form == 2:
        first_angel.draw_over(text, camera, b, lift)


def draw_lava_halo(text, camera, w: LavaHalo) -> None:
    """The halo rolling as a burning wheel: a spinning ring of fire, and its
    health under it once it's been hit."""
    batch = _Batch(text)
    x, y = camera.world_to_px(w.x, w.y)
    tw, th = config.TILE_PX_W, config.TILE_PX_H
    r = w.hit_radius
    n = 10
    hot = w.hurt_flash > 0
    for k in range(n):
        a = k * math.tau / n + w.facing
        col = palette.FOSSIL_FIRE[0] if hot else palette.FOSSIL_FIRE[(k + int(w.t * 10)) % 3]
        batch.put_c(x + math.cos(a) * r * tw * 0.8, y + math.sin(a) * r * th * 0.7,
                    "@" if k % 3 == 0 else "o", col)
    batch.put_c(x, y, "*", palette.FOSSIL_FIRE[1])
    if w.hp < w.max_hp:
        f = max(0.0, w.hp / w.max_hp)
        bar = "=" * round(f * 6) + "-" * (6 - round(f * 6))
        batch.put_c(x, y - r * th - 6, bar, palette.HP_BAR_FULL)
    batch.flush()
