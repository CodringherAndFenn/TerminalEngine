"""
render/forest.py -- the haunted forest's P8 tells, drawn over the enemies
by render/plains.draw_plains_tells (the bodies are letter-art, like the
plains'):

  * the grave digger's spot: the ground cracking where a skeleton is about
    to climb out (faster as it nears);
  * the cultist's ring: dotted lines between its burning candles;
  * the banshee breathing in: the edges of the cone it will scream into;
  * the wendigo crouching: the line of its lunge;
  * the headless knight staggering: stars over its shoulders.
"""

from __future__ import annotations

import math

from .. import config, palette
from ..ai.forest import Banshee, Cultist, GraveDigger, HeadlessKnight, Wendigo
from . import forest_art  # noqa: F401  (adds the pictures to characters.ART)


def _dots(batch, camera, x0, y0, angle, length, color, step=1.2) -> None:
    ca, sa = math.cos(angle), math.sin(angle)
    k = step
    while k <= length:
        x, y = camera.world_to_px(x0 + ca * k, y0 + sa * k)
        batch.put_c(x, y, ".", color)
        k += step


def draw_forest_tells(batch, camera, e) -> None:
    if isinstance(e, GraveDigger) and e.dig is not None:
        x, y = camera.world_to_px(e.dig[0], e.dig[1])
        fast = e.dig[2] < 0.4
        flick = int(e.dig[2] * (16 if fast else 8)) % 2
        col = palette.DIG_CRACK[flick]
        for dx, dy, g in ((-8, 0, "\\"), (0, -3, "_"), (8, 1, "/"), (0, 4, ",")):
            batch.put_c(x + dx, y + dy, g, col)
    if isinstance(e, Cultist) and e.ring is not None:
        lit = e.burning
        for a, b in zip(lit, lit[1:] + lit[:1]):
            if a is b:
                continue
            n = max(2, int(math.hypot(b.x - a.x, b.y - a.y) / 0.6))
            for k in range(1, n):
                x, y = camera.world_to_px(a.x + (b.x - a.x) * k / n, a.y + (b.y - a.y) * k / n)
                batch.put_c(x, y, ".", palette.RITUAL[k % 2])
    if isinstance(e, Banshee) and e.windup > 0:
        half = math.radians(config.BANSHEE[1]) / 2
        for side in (-1, 1):
            _dots(batch, camera, e.x, e.y, e.facing + side * half, e.espec.attack_radius,
                  palette.SCREAM[1])
    if isinstance(e, Wendigo) and e.state == "crouch":
        _dots(batch, camera, e.x, e.y, e.aim, config.WENDIGO_LUNGE[0], palette.PLAINS_TELL[1])
    if isinstance(e, HeadlessKnight) and e.stagger > 0:
        x, y = camera.world_to_px(e.x, e.y)
        spin = e.stagger * 6
        for k in range(3):
            a = spin + k * math.tau / 3
            batch.put_c(x + math.cos(a) * 16, y - 44 + math.sin(a) * 5, "*", palette.DAZE)
