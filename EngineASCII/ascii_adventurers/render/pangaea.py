"""
render/pangaea.py -- Pangaea's land at work (M31.1, systems/pangaea.py): the
volcano's lava bombs (the ring marking where each will land, tightening and
flashing as it comes; the bomb itself falling out of the sky toward it) and
the bubbles round a hero sinking in tar. A bomb's burst is an effect
("lava_burst"), the burning rock it leaves a zone ("lava_splash",
render/spell_fx.py).
"""

from __future__ import annotations

import math

from .. import config, palette
from .ascii_fx import _Batch

_FALL_PX = 150              # how high above its mark a bomb shows first (canvas px)


def draw_pangaea(text, camera, volcano, heroes) -> None:
    if volcano is None:
        return
    batch = _Batch(text)
    radius = config.LAVA_BOMB[3]
    tw, th = config.TILE_PX_W, config.TILE_PX_H
    for x, y, left, total in volcano.bombs:
        q = 1.0 - left / total if total > 0 else 1.0
        px, py = camera.world_to_px(x, y)
        hot = left < 0.6 and int(left * 10) % 2 == 0
        col = palette.LAVA_MARK[0 if hot else 1]
        r = radius * (1.15 - 0.15 * q)
        for k in range(14):
            a = k * math.tau / 14 + q
            batch.put_c(px + math.cos(a) * r * tw, py + math.sin(a) * r * th, "o" if k % 2 else ".", col)
        batch.put_c(px, py, "x", col)
        if q > 0.35:                                  # (the bomb, coming down)
            f = (q - 0.35) / 0.65
            batch.put_c(px + (1.0 - f) * 40, py - (1.0 - f) * _FALL_PX, "@", palette.LAVA_BOMB_FG)
    for h in heroes:
        if getattr(h, "tar_t", 0.0) > 0 and h.alive:
            x, y = camera.world_to_px(h.x, h.y)
            for k in range(3):
                a = k * math.tau / 3 + h.tar_t * 4
                batch.put_c(x + math.cos(a) * 12, y + 8 + math.sin(a) * 4, "o" if k else ".",
                            palette.TAR_SINK)
    batch.flush()
