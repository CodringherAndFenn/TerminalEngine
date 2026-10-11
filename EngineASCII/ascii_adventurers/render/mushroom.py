"""
render/mushroom.py -- the mushroom biome's P12 tells, drawn over the enemies
by render/plains.draw_plains_tells:

  * the rootweaver's roots: cracks racing along the ground toward you, and
    the roots about to burst (flashing just before);
  * the mantis crouching: the line of its leap;
  * the fungal brute regrowing: green "+" rising off it;
  * the fairy ring: dots between its caps (the ring you shouldn't step in).
(The pollen, slime and mold are zones: render/spell_fx.py.)
"""

from __future__ import annotations

import math

from .. import palette
from ..ai.mushroom import FairyRing, FungalBrute, Mantis, Rootweaver
from .forest import _dots


def draw_mushroom_tells(batch, camera, e) -> None:
    if isinstance(e, Rootweaver):
        for x, y, crack, burst in e.roots:
            if crack > 0:
                continue                                   # the crack isn't there yet
            px, py = camera.world_to_px(x, y)
            if burst > 0:
                soon = burst < 0.15
                batch.put_c(px, py, "^" if soon else ",",
                            palette.ROOTS[0 if soon or int(burst * 20) % 2 else 1])
            else:
                batch.put_c(px, py, "Y", palette.ROOTS[0])
    if isinstance(e, Mantis) and e.state == "crouch":
        d = math.hypot(e.goal[0] - e.x, e.goal[1] - e.y)
        _dots(batch, camera, e.x, e.y, e.aim, d, palette.PLAINS_TELL[1])
    if isinstance(e, FungalBrute) and e.regrowing and int(e.unhit * 4) % 2 == 0:
        x, y = camera.world_to_px(e.x, e.y)
        batch.put_c(x + 10, y - 40 - (e.unhit * 20) % 12, "+", palette.HEAL_BEAM[0])
    if isinstance(e, FairyRing):
        caps = [c for c in e.caps if c.alive]
        for a, b in zip(caps, caps[1:] + caps[:1]):
            if a is b:
                continue
            for k in (1, 2):
                x, y = camera.world_to_px(a.x + (b.x - a.x) * k / 3, a.y + (b.y - a.y) * k / 3)
                batch.put_c(x, y, ".", palette.FAIRY_DOTS)
