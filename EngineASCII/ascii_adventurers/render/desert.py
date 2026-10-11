"""
render/desert.py -- the desert's P9 tells, drawn over the enemies by
render/plains.draw_plains_tells:

  * the scorpion's tail rising: the line its stab will reach;
  * the basilisk flaring its frill: the line it will stare down;
  * the mummy unwinding: the line its bandages will lash along, and the
    bandage itself while it drags someone in;
  * the djinn lamp's vortex: sand swirling round it, out to its reach.
"""

from __future__ import annotations

import math

from .. import config, palette
from ..ai.desert import Basilisk, DjinnLamp, Mummy, Scorpion
from .forest import _dots


def draw_desert_tells(batch, camera, e) -> None:
    if isinstance(e, Scorpion) and e.tail > 0:
        _dots(batch, camera, e.x, e.y, e.facing, config.SCORPION[4], palette.PLAINS_TELL[1],
              step=0.8)
    if isinstance(e, Basilisk) and e.windup > 0:
        _dots(batch, camera, e.x, e.y, e.aim, e.espec.attack_radius, palette.GAZE[1])
    if isinstance(e, Mummy):
        if e.windup > 0:
            _dots(batch, camera, e.x, e.y, e.aim, e.espec.attack_radius, palette.BANDAGE[1])
        if e.pulling is not None:
            h = e.pulling
            n = max(2, int(math.hypot(h.x - e.x, h.y - e.y) / 0.5))
            for k in range(1, n):
                x, y = camera.world_to_px(e.x + (h.x - e.x) * k / n, e.y + (h.y - e.y) * k / n)
                batch.put_c(x, y, "~", palette.BANDAGE[k % 2])
    if isinstance(e, DjinnLamp):
        radius = config.LAMP[1]
        for k in range(24):
            a = e.spin * 1.8 + k * math.tau / 24
            r = radius * (0.25 + 0.75 * ((k * 0.37 + e.spin * 0.4) % 1.0))
            x, y = camera.world_to_px(e.x + math.cos(a) * r, e.y + math.sin(a) * r)
            batch.put_c(x, y, "," if k % 3 else ".", palette.VORTEX[k % 2])
