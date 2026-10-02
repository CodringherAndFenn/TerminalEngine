"""
render/haunt.py -- the haunted forest's wisp lights (M21).

Faint lights hang over the forest floor (world/generator._haunt puts them
in the chunk data). They bob up and down and flicker between a few soft
colours, each on its own phase, so the forest feels alive. Drawing only:
they don't exist for the game (no light, no collision, nothing to hit).
"""

from __future__ import annotations

import math

from .. import palette
from ..engine_ext.camera import Camera
from .ascii_fx import _Batch

BOB_PX = 5            # how far a light drifts up and down
TRAIL = ".'"          # the faint sparks under it


def draw_wisps(text, camera: Camera, world, steps: int) -> None:
    lights_in = getattr(world, "lights_in", None)
    if lights_in is None:
        return
    x0, y0 = camera.canvas_to_world(0, 0)
    x1, y1 = camera.canvas_to_world(camera.view_w, camera.view_h)
    lights = lights_in(x0 - 1, y0 - 1, x1 + 1, y1 + 1)
    if not lights:
        return
    batch = _Batch(text)
    cols = palette.HAUNT_WISP
    for wx, wy in lights:
        phase = (wx * 12.9898 + wy * 78.233) % math.tau      # each light its own rhythm
        t = steps / 60.0
        bob = math.sin(t * 1.3 + phase) * BOB_PX
        sway = math.sin(t * 0.7 + phase * 2) * 3
        x, y = camera.world_to_px(wx, wy)
        col = cols[int((t * 2 + phase) % len(cols))]
        batch.put_c(x + sway, y - 10 + bob, "*" if math.sin(t * 5 + phase) > -0.3 else "+", col)
        batch.put_c(x + sway * 0.5, y + 2 + bob * 0.5, TRAIL[int(t * 3 + phase) % 2], cols[1])
    batch.flush()
