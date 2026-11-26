"""
systems/alert.py -- Panopticon's alert (M32.2, design/OCEAN.md 36): the city
watches.

One meter for the whole island (it's the city's alarm, not yours: every
hero on it shares it), 0 to PANOPTICON_ALERT[0], in three levels:

  CALM      the machines go about their work;
  SEARCH    from [1]: a machine that sees you calls every machine near it
            to where you are (ai/panopticon.Machine), and the turrets wake;
  LOCKDOWN  once it's full: the gates of each hero's district seal round
            them ([5] s: their fences stay on, and you can't get through),
            a hunter squad is sent (PANOPTICON_SQUAD) and the cleaning sweeps
            your street. It holds at least [4] s, the meter full.

Whatever sees a hero (a camera, a machine) reports it with `seen` during the
enemies' turn; the next `step` raises the meter by the fastest eye on anyone
(ALERT_EYES, a second). With nothing seeing anyone for [2] s it drains [3] a
second. A warden that has marked you holds it at lockdown while it lives
(`hold`, refreshed every turn it's alive). The meter lives on the world
(`alert_of`); the HUD shows it (with its level's name) to a hero on the
island, and in lockdown the screen's edge pulses magenta
(render/panopticon.draw_lockdown).
"""

from __future__ import annotations

import math
import random

from .. import config
from ..entities.effects import Effect
from ..world.rng import hash_coords

CALM, SEARCH, LOCKDOWN = 0, 1, 2
NAMES = ("CALM", "SEARCH", "LOCKDOWN")


class Alert:
    """The city's alert: the meter, how long nothing has seen anyone, how
    long lockdown still holds, the sealed gates' fences (fence index -> s
    left), the hunters out, and the fastest eye on anyone this step."""

    def __init__(self) -> None:
        self.meter = 0.0
        self.quiet = 0.0
        self.lock_t = 0.0
        self.level = CALM
        self.rate = 0.0               # the fastest eye reported since the last step
        self.held = 0.0               # s a warden's mark still holds it at lockdown
        self.sealed: dict[int, float] = {}
        self.hunters: list = []
        self.lockdowns = 0            # how many times it has gone to lockdown (this run)

    @property
    def frac(self) -> float:
        return self.meter / config.PANOPTICON_ALERT[0]


def alert_of(world) -> Alert:
    """The world's alert (made the first time it's asked for)."""
    a = getattr(world, "city_alert", None)
    if a is None:
        a = world.city_alert = Alert()
    return a


def level_of(world) -> int:
    a = getattr(world, "city_alert", None)
    return CALM if a is None else a.level


def seen(world, rate: float) -> None:
    """Something sees a hero, filling the alert `rate` a second."""
    a = alert_of(world)
    if rate > a.rate:
        a.rate = rate


def hold(world, seconds: float = 0.5) -> None:
    """A warden's mark: the alert stays at lockdown for `seconds` more."""
    a = alert_of(world)
    a.held = max(a.held, seconds)


def step(scene, plan, living, dt: float) -> None:
    """The alert's step (from systems/panopticon.step, before the enemies'
    turn: what they saw last step counts now)."""
    a = alert_of(scene.world)
    full, search, quiet, drain, hold_s, seal_s = config.PANOPTICON_ALERT[:6]
    rate, a.rate = a.rate, 0.0
    a.held = max(0.0, a.held - dt)
    if a.held > 0:                                # (marked: straight to lockdown, and it stays)
        a.meter = full
        a.quiet = 0.0
    elif rate > 0:
        a.meter = min(full, a.meter + rate * dt)
        a.quiet = 0.0
    else:
        a.quiet += dt
    if a.lock_t > 0:
        a.lock_t = max(0.0, a.lock_t - dt)
        a.meter = full
    elif a.quiet >= quiet:
        a.meter = max(0.0, a.meter - drain * dt)
    was = a.level
    a.level = LOCKDOWN if a.meter >= full else SEARCH if a.meter >= search else CALM
    if a.level == LOCKDOWN and was != LOCKDOWN:
        a.lock_t = hold_s
        a.lockdowns += 1
        _lockdown(scene, plan, a, living, seal_s)
    if a.sealed:
        for i in list(a.sealed):
            a.sealed[i] -= dt
            if a.sealed[i] <= 0:
                del a.sealed[i]
    if a.hunters:
        a.hunters = [e for e in a.hunters if e.alive and e in scene.enemies]
    for p in scene.players:
        h = p.hero
        on = p.alive and _on_island(scene, h.x, h.y)
        h.alert_hud = (a.level, a.frac) if on else None


def _on_island(scene, x: float, y: float) -> bool:
    biome_at = getattr(scene.world, "biome_at", None)
    return biome_at is not None and biome_at(math.floor(x), math.floor(y)).name == "panopticon"


# --- Lockdown ---------------------------------------------------------------------------


def _lockdown(scene, plan, a: Alert, living, seal_s: float) -> None:
    """Gates seal round each hero on the island, a hunter squad comes for
    them, and the cleaning sweeps their street."""
    from .panopticon import _pick_lane
    here = [p for p in living if not p.ghost and p.alive and _on_island(scene, p.hero.x, p.hero.y)]
    if not here:
        return
    scene._sounds.append("whistle")
    for p in here:
        h = p.hero
        scene.effects.append(Effect("toast", h.x, h.y - 2.0, label="LOCKDOWN!"))
        for i in plan.district_gates(plan.district_at(h.x, h.y)):
            a.sealed[i] = seal_s
        if not plan.in_plaza(h.x, h.y, 2.0):
            lane = _pick_lane(scene, plan, h)
            if lane is not None:
                scene.city.sweeps.append(lane)
                scene.city.next[p.index] = config.PANOPTICON_SWEEP[0]
    _send_squad(scene, a, here[0].hero)


def _send_squad(scene, a: Alert, h) -> None:
    """The hunter squad (PANOPTICON_SQUAD): from ~[0] tiles out round the
    hero, on open ground on the island, knowing where they are."""
    from .collision import hull_hits_solid
    reach, who, most = config.PANOPTICON_SQUAD
    room = most - len(a.hunters)
    if room <= 0 or scene.spawner is None:
        return
    rng = random.Random(hash_coords(getattr(scene.world, "seed", 0) or 0, 0xA1E7, a.lockdowns))
    base = rng.uniform(0.0, math.tau)
    for n, key in enumerate(who[:room]):
        for k in range(16):
            ang = base + n * math.tau / len(who) + k * 0.4
            r = reach + rng.uniform(-3.0, 3.0)
            x, y = h.x + math.cos(ang) * r, h.y + math.sin(ang) * r
            if not _on_island(scene, x, y) or hull_hits_solid(scene.world, x, y, 0.0, 1.2, 1.2):
                continue
            e = scene.spawner.wake(key, x, y, None, random.Random(rng.random()))
            e.alert = True
            e.target = h
            e.last_known = (h.x, h.y)
            e.forget_timer = config.FORGET_TIME * 2
            e.hunter = True
            if hasattr(e, "called_to"):
                e.called_to(h)
            scene.enemies.append(e)
            a.hunters.append(e)
            scene.effects.append(Effect("spark_burst", x, y, size=1.4))
            break
