"""
render/chests.py -- chests and mimics (M28.4b/c).

A shut chest twinkles; a guarded one shows how many guards are left over
it. The chest tile itself is terrain (world/tiles.CHEST). The mimic is a
letter-art creature (render/plains.draw_plains), one body per biome
(MIMIC_ART, built from one picture: the box's wood takes the biome's
colour), with its own tells here (draw_mimic_tells): the lunge line, the
tongue.
"""

from __future__ import annotations

import math

from .. import config, palette
from .ascii_fx import _Batch
from .characters import ART
from .plains import _line
from .plains_art import _pad

# The picture: 'x' / 'X' is the box (recoloured per biome), 'm' its bands,
# 'w' the teeth, 'r' the tongue, 'y' the eyes, 'k' outline.
_MIMIC = [
    "...kkkkkkkkk",
    "..kxxxxxxxxxk",
    ".kxXxxxxxxxXxk",
    ".kxxyxxxxxyxxk",
    ".kmmmmmmmmmmmk",
    ".kwkwkwkwkwkwk",
    ".krrrrrrrrrrrk",
    ".kwkwkwkwkwkwk",
    ".kXXXXXXXXXXXk",
    ".kXmXXXXXXXmXk",
    ".kXmXXXXXXXmXk",
    ".kXXXXXXXXXXXk",
    "..kkkkkkkkkkk",
    "...kk.....kk",
]
# The box's colour letters per biome (palette.SPRITE_COLORS): mossy wood in
# the forest, sun-bleached in the desert, stone in the ruins, mud-dark in
# the swamp, violet in the mushroom biome.
_BOX = {"forest": ("g", "G"), "desert": ("l", "L"), "ruins": ("m", "M"), "swamp": ("n", "N"),
        "mushroom": ("v", "V"), "plains": ("t", "T")}

MIMIC_ART = {}
for _biome, (_lo, _hi) in _BOX.items():
    MIMIC_ART[f"mimic_{_biome}"] = _pad([r.replace("x", _lo).replace("X", _hi) for r in _MIMIC])
ART.update(MIMIC_ART)


def draw_chests(text, camera, chests, steps: int) -> None:
    """A spark over every shut chest in view; a guarded one's count."""
    if not chests.states:
        return
    batch = _Batch(text)
    x0, y0 = camera.canvas_to_world(0, 0)
    x1, y1 = camera.canvas_to_world(camera.view_w, camera.view_h)
    ch = text.display.cell_h
    for s in chests.states:
        if s.done or not (x0 - 2 <= s.x <= x1 + 2 and y0 - 3 <= s.y <= y1 + 2):
            continue
        px, py = camera.world_to_px(s.x, s.y)
        k = (steps // 10 + s.n) % 6
        if k < 2:
            batch.put_c(px + (8 if k else -8), py - ch * 0.9, "*" if k else "'",
                        palette.CHEST_SPARK[k])
        left = chests.guards_left(s)
        if left:
            batch.put_c(px, py - ch * 1.4, f"{left} GUARD{'S' if left > 1 else ''}",
                        palette.CHEST_GUARD_TEXT)
    batch.flush()


def draw_mimic_tells(batch, camera, e) -> None:
    """The lunge's line while it crouches, the tongue's line while it
    winds up, and the tongue itself."""
    if e.state == "crouch":
        _line(batch, camera, e.x, e.y, e.aim, config.MIMIC_LUNGE[2], palette.PLAINS_TELL[1])
    elif e.state == "lash":
        _line(batch, camera, e.x, e.y, e.aim, config.MIMIC_TONGUE[1], palette.MIMIC_TONGUE[1],
              step=0.8)
    if e.tongue_t > 0:
        ex, ey = e.tongue_end
        n = max(2, int(math.hypot(ex - e.x, ey - e.y) / 0.5))
        for i in range(1, n + 1):
            f = i / n
            px, py = camera.world_to_px(e.x + (ex - e.x) * f, e.y + (ey - e.y) * f)
            batch.put_c(px, py, "=" if i < n else "o", palette.MIMIC_TONGUE[0])
