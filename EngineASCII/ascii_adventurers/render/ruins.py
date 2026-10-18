"""
render/ruins.py -- the ruins' P10 tells, drawn over the enemies by
render/plains.draw_plains_tells:

  * the gargoyle lining up: the line it will dive along;
  * the crossbow sniper aiming: its long line (it stops following you a
    moment before the shot);
  * the colossus's stomp: its rings rolling out along the ground;
  * the flail brute spinning: the ring of the flail, growing;
  * the rune mine: its ring, flashing faster as it's about to blow;
  * the rubble crab's shell: a grey bar over its health bar.
"""

from __future__ import annotations

import math

from .. import config, palette
from ..ai.ruins import Colossus, FlailBrute, Gargoyle, RubbleCrab, RuneMine, Sniper
from .forest import _dots


def _ring(batch, camera, x0, y0, r, n, glyph, color) -> None:
    for k in range(n):
        a = k * math.tau / n
        x, y = camera.world_to_px(x0 + math.cos(a) * r, y0 + math.sin(a) * r)
        batch.put_c(x, y, glyph, color)


def draw_ruins_tells(batch, camera, e) -> None:
    if isinstance(e, Gargoyle) and e.state == "mark":
        _dots(batch, camera, e.x, e.y, e.aim, config.GARGOYLE[1], palette.PLAINS_TELL[1])
    if isinstance(e, Sniper) and e.windup > 0:
        locked = e.windup <= config.SNIPER[2]
        _dots(batch, camera, e.x, e.y, e.aim, config.WEAPONS["heavy_bolt"].shell.max_range,
              palette.SNIPER_LINE[1 if locked else 0], step=0.9)
    if isinstance(e, Colossus):
        for r, _ in e.rings:
            _ring(batch, camera, e.x, e.y, r, max(12, int(r * 7)), "o", palette.STOMP)
    if isinstance(e, FlailBrute) and e.spin > 0:
        r = e.ring
        _ring(batch, camera, e.x, e.y, r, max(10, int(r * 8)), ".", palette.PLAINS_TELL[1])
        x, y = camera.world_to_px(e.x + math.cos(e.angle) * r, e.y + math.sin(e.angle) * r)
        batch.put_c(x, y, "@", palette.FLAIL)
    if isinstance(e, RuneMine):
        r = e.espec.attack_radius
        armed = e.windup > 0
        on = not armed or int(e.windup * 12) % 2 == 0
        if on:
            _ring(batch, camera, e.x, e.y, r, 14, "." if not armed else "*",
                  palette.RUNE[0 if armed else 1])
    if isinstance(e, RubbleCrab) and e.shell > 0:
        x, y = camera.world_to_px(e.x, e.y)
        cells = max(1, round(e.shell / config.CRAB_SHELL[0] * 4))
        batch.put_c(x, y - e.espec.scale * 9 - 18, "=" * cells + "-" * (4 - cells),
                    palette.CRAB_SHELL_BAR)
