"""
render/paradise.py -- Paradise's enemies' tells (M29.2), drawn over them by
render/plains.draw_plains_tells (their pictures: render/paradise_art.py;
the unveiling's flicker is the picture itself, ai/paradise.Angel.sprite_now,
with the usual red "!" over it):

  * the watcher: its gaze line while it fixes on you (dots, following you),
    then the beam itself while it burns;
  * the lines of what's coming: an ophan lining up its race, the Lamb
    scraping before its charge, a cherub crouched to lunge;
  * an unveiled one bleeding (drops falling off it), and drinking at a
    font (red "+" rising);
  * M29.3: coals and tears in the air (an arc, and a mark where each will
    land), the trumpeter's plague (the marked circle, then the strikes),
    the bowl-bearer's mark where it'll pour, a chorister singing, the
    behemoth's charge line.
(The ophan's slick of blood is a zone: render/spell_fx.py. The stains are
tiles: world/tiles.STAINS.)
"""

from __future__ import annotations

import math

from .. import config, palette
from ..ai.paradise import (Angel, Behemoth, BowlBearer, Cherub, Chorister, Lamb, Ophan,
                           Trumpeter, Watcher)
from .forest import _dots


def draw_paradise_tells(batch, camera, e) -> None:
    if not isinstance(e, Angel):
        return
    x, y = camera.world_to_px(e.x, e.y)
    if isinstance(e, Watcher):
        if e.beam is not None:
            x0, y0, x1, y1 = e.beam
            n = max(2, int(math.hypot(x1 - x0, y1 - y0) / 0.5))
            flick = int(e.clock * 30) % 2
            for k in range(1, n + 1):
                px, py = camera.world_to_px(x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n)
                batch.put_c(px, py, "*" if (k + flick) % 2 else "=", palette.GAZE[1])
        elif e.unveiled and e.windup > 0 and e.aim_end is not None:
            x1, y1 = e.aim_end
            _dots(batch, camera, e.x, e.y, e.aim, math.hypot(x1 - e.x, y1 - e.y),
                  palette.GAZE[0 if e.windup > config.WATCHER[4] or int(e.clock * 16) % 2 else 1])
    if isinstance(e, Ophan) and e.rolling == "aim":
        _dots(batch, camera, e.x, e.y, e.aim, config.OPHAN[2] * 0.6, palette.PLAINS_TELL[1])
    if isinstance(e, Lamb) and e.charging == "scrape":
        _dots(batch, camera, e.x, e.y, e.facing, config.LAMB[1], palette.PLAINS_TELL[1])
    if isinstance(e, Cherub) and e.unveiled and e.move == "lunge" and e.windup > 0:
        _dots(batch, camera, e.x, e.y, e.aim, config.CHERUB[5], palette.PLAINS_TELL[1])
    if isinstance(e, Behemoth) and e.charging == "scrape":
        _dots(batch, camera, e.x, e.y, e.facing, config.BEHEMOTH[1], palette.PLAINS_TELL[1])
    for x0, y0, x1, y1, t, flight, what in e.lobs:          # (coals and tears in the air)
        f = t / flight
        tx, ty = camera.world_to_px(x1, y1)
        near = f > 0.7 and int(e.clock * 16) % 2
        batch.put_c(tx, ty, "x" if near else "+", palette.PLAINS_TELL[0 if near else 1])
        px, py = camera.world_to_px(x0 + (x1 - x0) * f, y0 + (y1 - y0) * f)
        lift = math.sin(math.pi * f) * 40                      # (pixels up: the arc)
        batch.put_c(px, py - lift, "*" if what == "coal" else "o",
                    palette.SHOT_EMBER[0] if what == "coal" else palette.SLICK[0])
    if isinstance(e, Trumpeter) and e.plague is not None:
        px, py, mark = e.plague[:3]
        r = config.TRUMPET[4]
        col = palette.PLAGUE[0 if mark > 0.4 or int(e.clock * 16) % 2 else 1]
        for k in range(28):
            a = k * math.tau / 28
            cx, cy = camera.world_to_px(px + math.cos(a) * r, py + math.sin(a) * r)
            batch.put_c(cx, cy, ":" if mark > 0 else "*" if k % 2 else "'", col)
        cx, cy = camera.world_to_px(px, py)
        batch.put_c(cx, cy, "+", col)
    if isinstance(e, BowlBearer) and e.mark is not None and e.windup > 0:
        mx, my = e.mark
        grow = 1.0 - e.windup / e.espec.windup
        r = config.BOWL[1] * (0.4 + 0.6 * grow)
        for k in range(10):
            a = k * math.tau / 10
            cx, cy = camera.world_to_px(mx + math.cos(a) * r, my + math.sin(a) * r)
            batch.put_c(cx, cy, ".", palette.SLICK[0])
    if isinstance(e, Chorister) and e.serene and e.singing and int(e.clock * 3) % 2 == 0:
        batch.put_c(x + 12, y - 44 - (e.clock * 18) % 14, "'", palette.SHOT_LYRE[0])
    if e.unveiled:
        if e.drinking and int(e.clock * 4) % 2 == 0:
            batch.put_c(x + 10, y - 40 - (e.clock * 20) % 12, "+", palette.DRINK)
        drop = (e.clock * 1.7 + (id(e) % 7) / 7) % 1.0       # (a drop falling off it)
        if drop < 0.6:
            batch.put_c(x - 4 + (id(e) % 9), y + 6 + drop * 24, "," if drop > 0.3 else "'",
                        palette.SLICK[0])

