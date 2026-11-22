"""
render/pandemonium.py -- Pandemonium's revellers' tells (M30.2): bottles in
the air and where they'll land, a dancer's dash and a masked dancer's stab
(their lines), the piper's song (a fan of notes), a reveller drinking at a
fountain or gorging at a table; and an entranced hero's sparkles. Their
pictures are render/pandemonium_art.py; their rings and flashes are effects
(render/ascii_fx.py).
"""

from __future__ import annotations

import math

from .. import config, palette
from ..ai.pandemonium import Dancer, Glutton, MaskedDancer, Piper
from .ascii_fx import _Batch
from .forest import _dots


def draw_pandemonium_tells(batch, camera, e) -> None:
    if not getattr(e, "revel", False):
        return
    x, y = camera.world_to_px(e.x, e.y)
    for x0, y0, x1, y1, t, flight, what in e.lobs:          # (bottles in the air)
        f = t / flight
        tx, ty = camera.world_to_px(x1, y1)
        near = f > 0.7 and int(e.clock * 16) % 2
        batch.put_c(tx, ty, "x" if near else "+", palette.PLAINS_TELL[0 if near else 1])
        px, py = camera.world_to_px(x0 + (x1 - x0) * f, y0 + (y1 - y0) * f)
        batch.put_c(px, py - math.sin(math.pi * f) * 40, "o", palette.REVEL_BOTTLE)
    if isinstance(e, Dancer) and e.unveiled and e.windup > 0:
        _, _, _, dash, fast = config.DANCE_STEPS
        _dots(batch, camera, e.x, e.y, e.aim, dash * fast, palette.PLAINS_TELL[1])
    if isinstance(e, MaskedDancer) and e.unveiled and e.windup > 0:
        _dots(batch, camera, e.x, e.y, e.aim, config.MASKED[2], palette.PLAINS_TELL[1])
    if isinstance(e, Piper) and e.singing:
        half = math.radians(config.PIPER[2]) / 2
        reach = config.PIPER[3]
        for k in range(5):                                    # (a fan of notes, drifting out)
            a = e.aim - half + 2 * half * k / 4
            r = ((e.clock * 6 + k * 1.7) % reach) + 1.0
            px, py = camera.world_to_px(e.x + math.cos(a) * r, e.y + math.sin(a) * r)
            batch.put_c(px, py, "'" if k % 2 else "*", palette.REVEL_SONG[k % 2])
        for a in (e.aim - half, e.aim + half):                # (its edges)
            px, py = camera.world_to_px(e.x + math.cos(a) * reach, e.y + math.sin(a) * reach)
            batch.put_c(px, py, ".", palette.REVEL_SONG[1])
    if isinstance(e, Glutton) and e.gorging > 0 and int(e.clock * 5) % 2 == 0:
        batch.put_c(x + 10, y - 44 - (e.clock * 20) % 12, "%", palette.REVEL_SPILL[1])
    if e.drinking and int(e.clock * 4) % 2 == 0:
        batch.put_c(x + 10, y - 40 - (e.clock * 20) % 12, "+", palette.REVEL_WINE[0])


def draw_entranced(text, camera, heroes) -> None:
    """Sparkles circling an entranced hero (the TMP meter says the rest)."""
    batch = _Batch(text)
    for h in heroes:
        if getattr(h, "entranced", 0) <= 0:
            continue
        x, y = camera.world_to_px(h.x, h.y)
        for k in range(4):
            a = h.time * 3.0 + k * math.tau / 4
            batch.put_c(x + math.cos(a) * 22, y - 18 + math.sin(a) * 10,
                        "*" if k % 2 else "'", palette.REVEL_TEMPT[k % 2])
    batch.flush()
