"""
systems/temptation.py -- Pandemonium's temptation (M30.2, design/OCEAN.md 14):
the trance reaches you too.

Within TEMPT[1] tiles of a banquet table, a bandstand or a wine fountain
(ai/pandemonium.lures) a hero's meter fills, faster the closer; clear of
them it drains (twice as fast while the hero is hitting something). Wine
puddles, toasts and the piper's song add to it (`add`). Full, the hero is
entranced for TEMPT[5] s: drifting toward the nearest lure, no attacks; a
roll snaps them out.
"""

from __future__ import annotations

import math

from .. import config
from ..entities.effects import Effect


def add(hero, amount: float) -> None:
    """More temptation (a puddle, a toast, a song); entranced heroes take none."""
    if getattr(hero, "entranced", 0) > 0 or not hasattr(hero, "temptation"):
        return
    hero.temptation = min(config.TEMPT[0], hero.temptation + amount)


def _nearest(lures, x: float, y: float):
    if not lures:
        return None, math.inf
    best = min(lures, key=lambda q: math.hypot(q[0] - x, q[1] - y))
    return best, math.hypot(best[0] - x, best[1] - y)


def step(scene, p, inp, dt: float) -> None:
    """One player's temptation this step (before the move: an entranced
    hero's input is turned toward the lure)."""
    from ..ai.pandemonium import lures as lures_of
    h = p.hero
    full, reach, fill, drain, hitting, entranced, drift = config.TEMPT
    lures = lures_of(scene.world)
    if h.entranced > 0:
        if inp.roll:
            h.entranced = 0.0                     # (snapped out: the roll goes ahead)
        else:
            h.entranced = max(0.0, h.entranced - dt)
            lure, d = _nearest(lures, h.x, h.y)
            if lure is not None and d > 1.0:
                inp.move_x = (lure[0] - h.x) / d * drift
                inp.move_y = (lure[1] - h.y) / d * drift
            else:
                inp.move_x = inp.move_y = 0.0
            return
    _, d = _nearest(lures, h.x, h.y)
    if d < reach:
        near = min(1.0, max(0.0, 1.0 - (d - 1.0) / (reach - 1.0)))
        h.temptation += full / fill * near * dt
    else:
        fast = hitting if h.struck_at > h.time - 0.5 else 1.0
        h.temptation -= full / drain * fast * dt
    h.temptation = min(full, max(0.0, h.temptation))
    if h.temptation >= full:
        h.temptation = 0.0
        h.entranced = entranced
        scene.effects.append(Effect("toast", h.x, h.y - 1.5, label="ENTRANCED!"))
