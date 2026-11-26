"""
systems/panopticon.py -- the dangers of Panopticon's land (M32.1, design/OCEAN.md 35).

What's where is world/panopticon.Plan's (fences, presses, spans); this is
their timing and what they do to a hero on the island (the machines, M32.2,
know the city's patterns: none of it hurts them):

  * laser fences: a blinking fence is on PANOPTICON_LASER[3] s and off [4]
    s, a faint line [2] s before it comes on; a sweeping one is always on,
    sliding [5] tiles along its street and back every [6] s. Touching a beam
    that's on burns [0] every [1] s;
  * conveyors carry whoever stands on them PANOPTICON_BELT tiles/s; a press
    slams down every PANOPTICON_PRESS[0] s (its shadow growing [1] s
    before), down [2] s: [3] to whoever is under it, once a slam;
  * live power: a live cable or puddle shocks PANOPTICON_SHOCK[0] every
    [1] s; every span arcs every ~PANOPTICON_ARC[0] s (its own beat, +-
    [1]), crackling [2] s first: [3] to anyone within [4] tiles of it or
    [5] of its pylons. Break a pylon and its spans go dead for good (their
    cables and puddles turn dead tiles, world.set_tile);
  * the cleaning: every ~PANOPTICON_SWEEP[0] s (+- [1]) a sweeper washes a
    street near each hero (one of the nearest few): its lane marked [2] s,
    then it drives down it at [3] tiles/s spraying whatever's alive (heroes:
    the machines aren't), [5] each. None on the tower's plaza.

The land's damage scales like an enemy's (systems/pangaea.hazard). The
scene keeps one `City` (the clock, the sweepers, each hero's next one) and
calls `step` once a step, after the heroes have moved; render/panopticon.py
draws the beams, the presses' shadows and rams, the arcs and the sweepers.
"""

from __future__ import annotations

import math

from .. import config
from ..entities.effects import Effect
from ..world import tiles
from .pangaea import hazard


class City:
    """The city's clock, the sweepers out, and when each hero gets the next."""

    def __init__(self) -> None:
        self.clock = 0.0
        self.sweeps: list[list] = []        # [x0, y0, ux, uy, length, half, t, hit]
        self.next: dict[int, float] = {}    # player index -> s until their next sweeper


def plan_of_scene(scene):
    """Panopticon's plan, if this world has the zone (or None)."""
    layout = getattr(scene.world, "layout", None)
    z = layout.zone("panopticon") if layout is not None and hasattr(layout, "zone") else None
    if z is None:
        return None
    from ..world.zones import plan_of
    return plan_of(layout, z)


def _on_panopticon(scene, x: float, y: float) -> bool:
    biome_at = getattr(scene.world, "biome_at", None)
    return biome_at is not None and biome_at(math.floor(x), math.floor(y)).name == "panopticon"


def dead_spans(world) -> set:
    """The spans whose pylon has been broken (for good, this run)."""
    got = getattr(world, "dead_spans", None)
    if got is None:
        got = world.dead_spans = set()
    return got


def _seg_dist(x: float, y: float, ax: float, ay: float, bx: float, by: float) -> float:
    dx, dy = bx - ax, by - ay
    ll = dx * dx + dy * dy
    f = 0.0 if ll <= 0 else max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / ll))
    return math.hypot(x - ax - dx * f, y - ay - dy * f)


# --- Timing ------------------------------------------------------------------------------


def fence_now(f, t: float):
    """A fence at time t: ("on" | "tell" | "off", its beam (x0, y0, x1, y1))."""
    laser = config.PANOPTICON_LASER
    if f.kind == "sweep":
        off = f.span / 2 * math.sin(math.tau * (t + f.phase) / laser[6])
        return "on", (f.x0 + f.nx * off, f.y0 + f.ny * off, f.x1 + f.nx * off, f.y1 + f.ny * off)
    period = laser[3] + laser[4]
    ph = (t + f.phase) % period
    seg = (f.x0, f.y0, f.x1, f.y1)
    if ph < laser[3]:
        return "on", seg
    return ("tell" if ph > period - laser[2] else "off"), seg


def press_now(press, t: float):
    """A press at time t: ("down" | "shadow" | "up", how far its shadow has
    grown (0-1), which slam this is)."""
    period, shadow, down, _ = config.PANOPTICON_PRESS
    x = t + press[2]
    ph = x % period
    cycle = math.floor(x / period)
    if ph < down:
        return "down", 1.0, cycle
    if ph > period - shadow:
        return "shadow", (ph - (period - shadow)) / shadow, cycle + 1
    return "up", 0.0, cycle


def span_now(s: int, t: float):
    """A span at time t: ("tell" | "arc" | "idle", how far through its
    crackle (0-1), which arc this is). Each span keeps its own beat."""
    every, jitter, tell = config.PANOPTICON_ARC[0], config.PANOPTICON_ARC[1], config.PANOPTICON_ARC[2]
    period = every + ((s * 2654435761) % 1000 / 1000.0 - 0.5) * 2 * jitter
    x = t + (s * 40503 % 997) / 997.0 * period
    ph = x % period
    cycle = math.floor(x / period)
    if ph < tell:
        return "tell", ph / tell, cycle
    if ph < tell + 0.15:
        return "arc", 1.0, cycle
    return "idle", 0.0, cycle


# --- A step --------------------------------------------------------------------------


def step(scene, living, dt: float) -> None:
    """One step of the city's dangers for everyone on Panopticon."""
    plan = plan_of_scene(scene)
    if plan is None:
        return
    world = scene.world
    broke = getattr(world, "broke", None)
    if broke and any(b[2] in _OURS for b in broke):
        cut = [b for b in broke if b[2] is tiles.PYLON]
        messes = [b for b in broke if b[2] in _MESS]
        broke[:] = [b for b in broke if b[2] not in _OURS]
        if cut:
            _cut(scene, plan, cut)
        for tx, ty, _ in messes:
            mess(scene, tx + 0.5, ty + 0.5)
    city = scene.city
    city.clock += dt
    from .alert import alert_of, step as alert_step
    alert_step(scene, plan, living, dt)             # (M32.2: the city's alert)
    here = [p for p in living if not p.ghost and _on_panopticon(scene, p.hero.x, p.hero.y)]
    if not here and not city.sweeps:
        return
    t = city.clock
    dead = dead_spans(world)
    sealed = alert_of(world).sealed
    for p in here:
        h = p.hero
        _soap(scene, h)
        _underfoot(scene, plan, h, world.tile_at(math.floor(h.x), math.floor(h.y)), t, dt)
        _lasers(scene, plan, h, t, dt, sealed)
        _arcs(scene, plan, h, t, dead)
    if here:
        _carry(scene, dt)
    _sweeps(scene, plan, city, here, living, dt)


_MESS = frozenset((tiles.SET_TABLE, tiles.MADE_BED, tiles.HEDGE))
_OURS = _MESS | {tiles.PYLON}


def mess(scene, x: float, y: float) -> None:
    """Something broken in the kept homes (M32.3): every housekeeper within
    MESS_REACH tiles comes for whoever's nearest (A MESS!)."""
    from ..ai.panopticon import Keeper
    heroes = [p.hero for p in scene.players if p.alive]
    if not heroes:
        return
    h = min(heroes, key=lambda q: math.hypot(q.x - x, q.y - y))
    came = 0
    for e in scene.enemies:
        if isinstance(e, Keeper) and e.alive and math.hypot(e.x - x, e.y - y) <= config.MESS_REACH:
            e.called_to(h)
            came += 1
    if came and scene.steps - getattr(scene, "mess_said", -999) > 60:
        scene.mess_said = scene.steps
        scene.effects.append(Effect("toast", x, y - 1.0, label="A MESS!"))
        scene._sounds.append("whistle")


def _soap(scene, h) -> None:
    """A scrubber's soap underfoot (M32.3): you slide (SCRUBBER[5] traction)."""
    on = any(z.kind == "soap" and math.hypot(h.x - z.x, h.y - z.y) <= z.radius + h.hit_radius * 0.5
             for z in scene.zones)
    if on:
        h.traction = config.SCRUBBER[5]
        h.soaped = True
    elif getattr(h, "soaped", False):
        h.traction = 1.0
        h.soaped = False


def _carry(scene, dt: float) -> None:
    """The belts carry the machines along too (M32.2; none of the rest
    touches them: they know the city's patterns)."""
    from ..ai.panopticon import Machine
    from .combat import push
    world = scene.world
    for e in scene.enemies:
        if not isinstance(e, Machine) or e.hovers or e.espec.speed <= 0 or not e.alive:
            continue
        belt = tiles.BELTS.get(world.tile_at(math.floor(e.x), math.floor(e.y)))
        if belt is not None:
            push(e, world, belt[0] * config.PANOPTICON_BELT * dt, belt[1] * config.PANOPTICON_BELT * dt)


def _underfoot(scene, plan, h, tile, t: float, dt: float) -> None:
    from .combat import push, skims, strike
    if skims(h):
        h.shock_t = 0.0
        return
    belt = tiles.BELTS.get(tile)
    if belt is not None:
        push(h, scene.world, belt[0] * config.PANOPTICON_BELT * dt, belt[1] * config.PANOPTICON_BELT * dt)
    if tile is tiles.CABLE or tile is tiles.PUDDLE:
        h.shock_t = getattr(h, "shock_t", 0.0) - dt
        if h.shock_t <= 0:
            h.shock_t = config.PANOPTICON_SHOCK[1]
            strike(h, hazard(scene, config.PANOPTICON_SHOCK[0]), None, None, scene.effects)
    else:
        h.shock_t = 0.0
    if tile is tiles.PRESS_BED:
        i = plan.press_at.get((math.floor(h.x), math.floor(h.y)))
        if i is not None:
            state, _, cycle = press_now(plan.presses[i], t)
            if state == "down" and getattr(h, "press_hit", None) != (i, cycle):
                h.press_hit = (i, cycle)
                strike(h, hazard(scene, config.PANOPTICON_PRESS[3]), None, None, scene.effects)
                scene.effects.append(Effect("spark_burst", h.x, h.y, size=1.2))
                scene._sounds.append("boulder")


def fence_state(plan, i: int, t: float, sealed=None):
    """Fence i at time t, sealed or not (M32.2: a district's gates in
    lockdown): ("sealed", its beam) or fence_now's."""
    if sealed and i in sealed:
        f = plan.fences[i]
        return "sealed", (f.x0, f.y0, f.x1, f.y1)
    return fence_now(plan.fences[i], t)


def _lasers(scene, plan, h, t: float, dt: float, sealed=None) -> None:
    from .combat import strike
    touching = False
    for i in plan.near(plan._fence_idx, h.x, h.y):
        state, seg = fence_state(plan, i, t, sealed)
        if state == "sealed":
            touching = _bar(scene, h, seg) or touching
            continue
        if state == "on" and _seg_dist(h.x, h.y, *seg) < 0.55:
            touching = True
            break
    if not touching:
        h.laser_t = 0.0
        return
    h.laser_t = getattr(h, "laser_t", 0.0) - dt
    if h.laser_t <= 0:
        h.laser_t = config.PANOPTICON_LASER[1]
        strike(h, hazard(scene, config.PANOPTICON_LASER[0]), None, None, scene.effects)
        scene._sounds.append("fizzle")


def _bar(scene, h, seg) -> bool:
    """A sealed gate's fence: it burns like any beam, and nobody gets
    through it -- a hero touching it is put back on the side they're on.
    True if they touched it."""
    from .combat import push
    x0, y0, x1, y1 = seg
    if _seg_dist(h.x, h.y, x0, y0, x1, y1) >= 0.7:
        return False
    dx, dy = x1 - x0, y1 - y0
    ll = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / ll, dx / ll
    s = (h.x - x0) * nx + (h.y - y0) * ny
    if abs(s) < 1e-3:                        # (right on it: back the way it came)
        s = -(h.vx * nx + h.vy * ny) or 1.0
    side = 1.0 if s > 0 else -1.0
    gap = 0.75 - abs((h.x - x0) * nx + (h.y - y0) * ny)
    if gap > 0:
        push(h, scene.world, nx * side * gap, ny * side * gap)
    return True


def _arcs(scene, plan, h, t: float, dead: set) -> None:
    from .combat import strike
    arc = config.PANOPTICON_ARC
    hits = getattr(h, "arc_hits", None)
    for s in plan.near(plan._span_idx, h.x, h.y):
        if s in dead:
            continue
        state, _, cycle = span_now(s, t)
        if state != "arc":
            continue
        if hits is not None and hits.get(s) == cycle:
            continue
        i, j, ax, ay, bx, by = plan.spans[s]
        close = _seg_dist(h.x, h.y, ax, ay, bx, by) < arc[4] or math.hypot(h.x - ax, h.y - ay) < arc[5] \
            or (j >= 0 and math.hypot(h.x - bx, h.y - by) < arc[5])
        if not close:
            continue
        if hits is None:
            hits = h.arc_hits = {}
        hits[s] = cycle
        strike(h, hazard(scene, arc[3]), None, None, scene.effects)
        scene.effects.append(Effect("spark_burst", h.x, h.y, size=1.0))
        scene._sounds.append("zap")


def _cut(scene, plan, broken) -> None:
    """Pylons broken: their spans go dead (their cables and puddles too)."""
    world = scene.world
    dead = dead_spans(world)
    for tx, ty, _ in broken:
        i = plan.pylon_at.get((tx, ty))
        if i is None:
            continue
        for s in plan.pylon_spans.get(i, ()):
            if s in dead:
                continue
            dead.add(s)
            for x, y in plan.span_tiles.get(s, ()):
                was = world.tile_at(x, y)
                if was is tiles.CABLE:
                    world.set_tile(x, y, tiles.DEAD_CABLE)
                elif was is tiles.PUDDLE:
                    world.set_tile(x, y, tiles.DEAD_PUDDLE)
        scene.effects.append(Effect("spark_burst", tx + 0.5, ty + 0.5, size=1.8))
        scene._sounds.append("zap")


# --- The cleaning ----------------------------------------------------------------------


def _pick_lane(scene, plan, h):
    """A street near the hero to wash: one of the nearest few, trimmed to
    its open length (at most PANOPTICON_SWEEP[4] tiles round the hero's
    spot on it), driven from either end."""
    length = config.PANOPTICON_SWEEP[4]
    world = scene.world
    cands = plan.lanes_near(h.x, h.y)
    h.rng.shuffle(cands)
    for lx, ly, ux, uy, half in cands:
        reach = []
        for sign in (-1, 1):
            d = 0
            while d < length / 2:
                tx, ty = math.floor(lx + ux * sign * (d + 1)), math.floor(ly + uy * sign * (d + 1))
                if world.tile_at(tx, ty).solid or not _on_panopticon(scene, tx + 0.5, ty + 0.5):
                    break
                d += 1
            reach.append(d)
        back, fwd = reach
        if back + fwd < 14:
            continue
        sx, sy = lx - ux * back, ly - uy * back
        if h.rng.random() < 0.5:                      # (from the other end)
            sx, sy, ux, uy = lx + ux * fwd, ly + uy * fwd, -ux, -uy
        return [sx, sy, ux, uy, float(back + fwd), half, -config.PANOPTICON_SWEEP[2], set()]
    return None


def _sweeps(scene, plan, city: City, here, living, dt: float) -> None:
    from .combat import skims, strike
    every, jitter, _, speed, _, damage = config.PANOPTICON_SWEEP
    for p in here:
        h = p.hero
        if plan.in_plaza(h.x, h.y, 2.0):
            continue                                  # (none on the tower's plaza)
        if p.index not in city.next:
            city.next[p.index] = every + h.rng.uniform(-jitter, jitter)
        city.next[p.index] -= dt
        if city.next[p.index] > 0:
            continue
        city.next[p.index] = every + h.rng.uniform(-jitter, jitter)
        lane = _pick_lane(scene, plan, h)
        if lane is not None:
            city.sweeps.append(lane)
    if not city.sweeps:
        return
    keep = []
    for sw in city.sweeps:
        sw[6] += dt
        x0, y0, ux, uy, length, half, t, hit = sw
        if t >= 0:
            pos = t * speed
            for p in living:
                h = p.hero
                if p.ghost or not h.alive or p.index in hit or skims(h):
                    continue
                rx, ry = h.x - x0, h.y - y0
                s = rx * ux + ry * uy
                if abs(-rx * uy + ry * ux) < half + 0.3 and pos - 1.6 < s < pos + 0.6 and s <= length:
                    hit.add(p.index)
                    strike(h, hazard(scene, damage), None, None, scene.effects)
                    scene.effects.append(Effect("splash", h.x, h.y))
            if pos > length + 3:
                continue
        keep.append(sw)
    city.sweeps = keep


def district_banner(scene, p, plan) -> None:
    """The first time a player walks into the factory, the scrapyard, the
    kept homes or onto the tower's plaza, its name comes up as a banner (the
    docks' is the island's own arrival banner)."""
    if scene.steps % 15:
        return
    name = plan.district_at(p.hero.x, p.hero.y)
    key = f"panopticon:{name}"
    if name not in config.PANOPTICON_DISTRICTS or key in scene.arrived:
        return
    scene.arrived.add(key)
    from .quests import Banner
    scene.quests.banner = Banner(*config.PANOPTICON_DISTRICTS[name])
