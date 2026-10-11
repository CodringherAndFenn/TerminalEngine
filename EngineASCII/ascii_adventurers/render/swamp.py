"""
render/swamp.py -- the swamp's P11 tells, drawn over the enemies by
render/plains.draw_plains_tells:

  * the crocodile crouching: the line of its lunge; clamped on: its jaws'
    "!" over the hero it holds (the toast says so too);
  * the heron drawing its neck back: the line it will stab along;
  * the real marsh light: a glint that blinks to its own beat (the two
    illusions don't have it).
(The hag's curse and the corpse's cloud are zones: render/spell_fx.py.)
"""

from __future__ import annotations

from .. import config, palette
from ..ai.swamp import Crocodile, Heron, MarshLight
from .forest import _dots


def draw_swamp_tells(batch, camera, e) -> None:
    if isinstance(e, Crocodile) and e.state == "crouch":
        _dots(batch, camera, e.x, e.y, e.aim, config.CROC[1], palette.PLAINS_TELL[1])
    if isinstance(e, Heron) and e.windup > 0:
        _dots(batch, camera, e.x, e.y, e.aim, e.espec.attack_radius, palette.PLAINS_TELL[1],
              step=0.7)
    if isinstance(e, MarshLight) and not e.fake and int(e.drift * 7) % 3 == 0:
        x, y = camera.world_to_px(e.x, e.y)
        batch.put_c(x + 6, y - 14, "'", palette.MARSH_REAL)
