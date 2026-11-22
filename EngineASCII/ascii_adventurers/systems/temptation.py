"""
systems/temptation.py -- Pandemonium's temptation (M30.2, design/OCEAN.md 14):
the trance reaches you too.

Within TEMPT[1] tiles of a banquet table, a bandstand or a wine fountain
(ai/pandemonium.lures) a hero's meter fills, faster the closer (and slower
for every bandstand silenced, M30.4); within the Host of the Feast's charm
it fills too, and full you're swept into his dance; clear of them it
drains (twice as fast while the hero is hitting something). Wine
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


def charmer(world):
    """Whoever's charm reaches across the floor just now (M30.4: the Host of
    the Feast, ai/feast.py), or None."""
    c = getattr(world, "charmer", None)
    return c if c is not None and c.alive else None


def step(scene, p, inp, dt: float) -> None:
    """One player's temptation this step (before the move: an entranced
    hero's input is turned toward the lure -- or, swept into the Host's
    dance, toward him)."""
    from ..ai.pandemonium import lures as lures_of, silenced
    h = p.hero
    full, reach, fill, drain, hitting, entranced, drift = config.TEMPT
    world = scene.world
    lures = lures_of(world)
    if h.entranced > 0:
        if inp.roll:
            h.entranced = 0.0                     # (snapped out: the roll goes ahead)
            h.swept = None
        else:
            h.entranced = max(0.0, h.entranced - dt)
            partner = h.swept if h.swept is not None and h.swept.alive else None
            lure, d = ((partner.x, partner.y), math.hypot(partner.x - h.x, partner.y - h.y)) \
                if partner is not None else _nearest(lures, h.x, h.y)
            if lure is not None and d > 1.0:
                inp.move_x = (lure[0] - h.x) / d * drift
                inp.move_y = (lure[1] - h.y) / d * drift
            else:
                inp.move_x = inp.move_y = 0.0
            if h.entranced <= 0:
                h.swept = None
            return
    rate = 0.0
    _, d = _nearest(lures, h.x, h.y)
    if d < reach:                                 # (the music: thinner for every silenced band)
        near = min(1.0, max(0.0, 1.0 - (d - 1.0) / (reach - 1.0)))
        quiet = max(0.0, 1.0 - config.SILENCE_TEMPT * len(silenced(world)))
        rate += full / fill * near * quiet
    host = charmer(world)
    charmed = host.charm_at(h) if host is not None else 0.0
    rate += full / config.HOST_CHARM[1] * charmed
    if rate > 0:
        h.temptation += rate * dt
    else:
        fast = hitting if h.struck_at > h.time - 0.5 else 1.0
        h.temptation -= full / drain * fast * dt
    h.temptation = min(full, max(0.0, h.temptation))
    if h.temptation >= full:
        h.temptation = 0.0
        h.entranced = entranced
        h.swept = host if charmed > 0 else None
        scene.effects.append(Effect("toast", h.x, h.y - 1.5,
                                    label="SWEPT INTO HIS DANCE!" if charmed > 0 else "ENTRANCED!"))
