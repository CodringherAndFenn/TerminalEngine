"""
render/drops.py -- pieces of gear lying on the ground (M28.4a).

A drop is a "[]" in its rarity's colour that twinkles (a legendary runs a
spark round it, like its card's glint); its name shows above it once the
viewing hero is within GEAR_DROP_LABEL tiles.
"""

from __future__ import annotations

import math

from .. import config, palette
from ..engine_ext.camera import Camera
from .ascii_fx import _Batch

_SPARK = ("*", "+", "'", ".")


def draw_drops(text, camera: Camera, drops, steps: int, near: tuple[float, float] | None) -> None:
    if not drops:
        return
    batch = _Batch(text)
    x0, y0 = camera.canvas_to_world(0, 0)
    x1, y1 = camera.canvas_to_world(camera.view_w, camera.view_h)
    cw, ch = text.display.cell_w, text.display.cell_h
    for i, d in enumerate(drops):
        if not (x0 - 2 <= d.x <= x1 + 2 and y0 - 2 <= d.y <= y1 + 2):
            continue
        color = palette.CARD_RARITY[d.piece.rarity]
        x, y = camera.world_to_px(d.x, d.y)
        bright, dim = palette.GEAR_DROP_GLOW
        twinkle = (steps // 12 + i) % 4 == 0
        batch.put_c(x, y, "[]", bright if twinkle else color)
        if d.piece.rarity == "legendary":
            # A spark running round the piece (M28.3a's glint, on the ground).
            k = (steps // 4 + i * 3) % 8
            a = k * math.tau / 8
            batch.put_c(x + math.cos(a) * cw * 1.6, y + math.sin(a) * ch * 0.9,
                        _SPARK[(steps // 4) % 4], palette.LEGEND_GLINT[k % 3])
        elif twinkle:
            batch.put_c(x - cw * 1.4, y - ch * 0.6, "'", dim)
        if near is not None and math.hypot(near[0] - d.x, near[1] - d.y) <= config.GEAR_DROP_LABEL:
            batch.put_c(x, y - ch, d.name.upper(), color)
    batch.flush()
