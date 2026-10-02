"""
systems/spells.py -- spells and items that cards grant (config.SPELLS).

A hero has up to SPELL_SLOTS of them (Arcane Wing: one more). Each works
on its own, every simulation step, around the hero:

  orbit  (Orbiting Daggers) `count` daggers circle the hero at `radius`
         tiles, turning `turn` rad/s; each dagger hits an enemy it touches
         at most once every `rehit` s.
  aura   (Ember Aura) every `interval` s, every enemy within `radius` gets
         `stacks` of the spell's status (burn).
  nova   (Frost Nova) every `interval` s, a ring bursts out to `radius`:
         `damage` and `stacks` of its status (chill) to every enemy in it
         that isn't behind a wall.
  wolf   (Spirit Wolf) `count` wolves run at the nearest enemy within
         `sight` of the hero and bite for `damage` every `bite` s; with
         nothing to hunt they trot back to the hero. Spirits: nothing hurts
         them, walls stop them.
  rune   (Rune Trap) every `interval` s a rune is left where the hero
         stands (at most `max`, each lasting `life` s); the first enemy to
         come within `trigger` sets it off: `damage` to all within `radius`.
  flask  (Poison Flask) every `interval` s `count` flasks are lobbed at
         the nearest enemies within `reach` (extra ones land beside the
         target when there are fewer enemies); `flight` s later each
         smashes into a poison pool (systems/zones.py) for `life` s.
  cloud  (Storm Cloud) hangs over the hero; every `interval` s strikes
         `strikes` random enemies within `reach`: `damage` and shock.
  totem  (Healing Totem) planted every `interval` s; for `life` s it heals
         every hero within `radius` by `heal` HP/s, and (with `chill`)
         chills every enemy there `chill` times every `chill_every` s.
  wand   (Fire Wand) every `interval` s a burning bolt flies at the
         nearest enemy in sight within `reach` (Multishot: more bolts, fanned).
  chain  (Chain Lightning, the wizard's) every `interval` s a bolt flies
         at the nearest enemy in sight within `reach` and jumps on (the
         shock bolt's 2 jumps + `jumps` + Storm Caller; Conductor's reach
         and fade, Supercell, Ball Lightning all work on it).
  turret (Bone Turret) every `interval` s a turret is placed (at most
         `count` standing), shooting the nearest enemy in sight within
         `reach` every `fire` s for `life` s; its bolts pass through
         `pierce` enemies.
  ward / thorns (Ward Charm, Thorn Mail) are passive: their numbers become
         the hero's shield / thorns stats (players/stats.py).

A spell's numbers are its level-1 `base` with each further level's
change applied (players/stats.spell_params). The hero's stats then scale
them where they're used: area x radius, spell cooldown x interval, and
every hit goes through combat.strike (damage %, tag %, crits, on-hit
statuses). Summons (wolves, turrets) don't crit or apply your statuses,
unless you have Pack Leader, which also adds one wolf and one turret.

Everything here is simulation state and replays exactly (randomness comes
from the hero's seeded dice); drawing only reads it (render/spell_fx.py).
"""

from __future__ import annotations

import math
from dataclasses import replace

from .. import config
from ..entities.effects import Effect
from ..entities.projectile import Projectile
from ..players.stats import spell_params
from .collision import move_hull
from .combat import _may_hurt, strike
from .raycast import first_hit
from .statuses import inflict
from .zones import Zone

DAGGER_HIT_RADIUS = 0.45     # tiles
WOLF_HALF_PX = 8             # a wolf's collision half-size
WOLF_REACH = 0.9             # tiles: a bite lands this close (plus the enemy's size)
WOLF_HEEL = 2.0              # tiles: with nothing to hunt, a wolf stays this close
CLOUD_OFFSET = (1.2, -2.2)   # where the storm cloud hangs, from the hero (tiles)


class SpellState:
    def __init__(self, key: str, level: int = 1) -> None:
        self.key = key
        self.spec = config.SPELLS[key]
        self.level = 0
        self.params: dict = {}
        self.timer = 0.0           # aura / nova: seconds to the next pulse
        self.angle = 0.0           # orbit: where the first dagger is
        self.clock = 0.0
        self._next_hit: dict[tuple[int, int], float] = {}   # (dagger, id(enemy)) -> time
        # What some spells leave in the world: wolves / runes / turrets /
        # totems as small dicts, flasks in the air.
        self.things: list[dict] = []
        self.set_level(level)
        self.timer = self.params.get("interval", 0.0) * 0.5   # first pulse comes soon

    def set_level(self, level: int) -> None:
        self.level = level
        self.params = spell_params(self.key, level)

    def dagger_positions(self, hero) -> list[tuple[float, float, float]]:
        """(x, y, angle) of each dagger; angle is where it points (along
        its orbit)."""
        p = self.params
        n = int(p["count"])
        r = p["radius"] * _area(hero)
        out = []
        for i in range(n):
            a = self.angle + i * math.tau / n
            out.append((hero.x + math.cos(a) * r, hero.y + math.sin(a) * r, a + math.pi / 2))
        return out


def _area(hero) -> float:
    return hero.stats.area_scale if hero.stats is not None else 1.0


def _cooldown(hero) -> float:
    return hero.stats.cooldown_scale if hero.stats is not None else 1.0


def sync_spells(spells: dict[str, SpellState], levels: dict[str, int]) -> None:
    """Match a player's spell states to their cards (new spells, level-ups)."""
    for key, level in levels.items():
        if key not in spells:
            spells[key] = SpellState(key, level)
        elif spells[key].level != level:
            spells[key].set_level(level)
    for key in [k for k in spells if k not in levels]:
        del spells[key]


def update_spells(hero, spells: dict[str, SpellState], world, actors, effects: list[Effect],
                  dt: float, projectiles: list | None = None,
                  zones: list | None = None) -> list[str]:
    """Run a hero's spells for one step. Returns sound events."""
    events: list[str] = []
    projectiles = projectiles if projectiles is not None else []
    zones = zones if zones is not None else []
    for s in spells.values():
        s.clock += dt
        run = _KINDS.get(s.spec.kind)
        if run is not None:
            events += run(hero, s, world, actors, effects, dt, projectiles, zones) or []
    return events


def _pack(hero) -> bool:
    return hero.stats is not None and hero.stats.has("pack_leader")


def _due(hero, s: SpellState, dt: float) -> bool:
    """Count the spell's timer down; True (and rewound) when it's time."""
    s.timer -= dt
    if s.timer > 1e-9:
        return False
    s.timer += s.params["interval"] * _cooldown(hero)
    return True


def _nearest(hero, actors, reach: float, world=None):
    """The nearest enemy within `reach` of the hero (in sight, if `world`)."""
    best, best_d = None, reach
    for a in _near(hero, actors, reach):
        d = math.hypot(a.x - hero.x, a.y - hero.y)
        if d <= best_d and (world is None
                            or first_hit(world.tile_at, hero.x, hero.y, a.x, a.y) is None):
            best, best_d = a, d
    return best


def _near(hero, actors, reach: float):
    for a in actors:
        if a.hittable and _may_hurt(hero, a) \
                and abs(a.x - hero.x) <= reach + a.hit_radius \
                and abs(a.y - hero.y) <= reach + a.hit_radius:
            yield a


def _orbit(hero, s: SpellState, world, actors, effects, dt, projectiles, zones) -> None:
    p = s.params
    s.angle = (s.angle + p["turn"] * dt) % math.tau
    daggers = s.dagger_positions(hero)
    reach = p["radius"] * _area(hero) + DAGGER_HIT_RADIUS
    for a in _near(hero, actors, reach):
        for i, (x, y, facing) in enumerate(daggers):
            if math.hypot(a.x - x, a.y - y) > DAGGER_HIT_RADIUS + a.hit_radius:
                continue
            key = (i, id(a))
            if s._next_hit.get(key, -1.0) > s.clock:
                continue
            s._next_hit[key] = s.clock + p["rehit"]
            strike(a, p["damage"], hero, facing, effects, s.spec.tags)
            effects.append(Effect("impact", a.x, a.y, facing))
            if not a.alive:
                break
    if len(s._next_hit) > 256:          # forget enemies long gone
        s._next_hit = {k: t for k, t in s._next_hit.items() if t > s.clock}


def _aura(hero, s: SpellState, world, actors, effects, dt, projectiles, zones) -> None:
    p = s.params
    if not _due(hero, s, dt):
        return
    r = p["radius"] * _area(hero)
    for a in _near(hero, actors, r):
        if math.hypot(a.x - hero.x, a.y - hero.y) <= r + a.hit_radius:
            inflict(a, p["inflicts"], hero, int(p["stacks"]))


def _nova(hero, s: SpellState, world, actors, effects, dt, projectiles, zones) -> list[str]:
    p = s.params
    if not _due(hero, s, dt):
        return []
    r = p["radius"] * _area(hero)
    effects.append(Effect("nova", hero.x, hero.y, size=r))
    for a in list(_near(hero, actors, r)):
        if math.hypot(a.x - hero.x, a.y - hero.y) > r + a.hit_radius:
            continue
        if first_hit(world.tile_at, hero.x, hero.y, a.x, a.y) is not None:
            continue
        angle = math.atan2(a.y - hero.y, a.x - hero.x)
        strike(a, p["damage"], hero, angle, effects, s.spec.tags)
        if a.alive:
            inflict(a, p["inflicts"], hero, int(p["stacks"]))
    return ["nova"]


def _wolf(hero, s: SpellState, world, actors, effects, dt, projectiles, zones) -> None:
    p = s.params
    want = int(p["count"]) + (1 if _pack(hero) else 0)
    wolves = s.things
    while len(wolves) < want:
        wolves.append({"x": hero.x, "y": hero.y, "bite": 0.0, "facing": 0.0})
    del wolves[want:]
    full = _pack(hero)
    for w in wolves:
        w["bite"] = max(0.0, w["bite"] - dt)
        target = None
        best = p["sight"]
        for a in _near(hero, actors, p["sight"]):
            d = math.hypot(a.x - w["x"], a.y - w["y"])
            if d < best:
                target, best = a, d
        if target is None:
            gx, gy = hero.x, hero.y
            if math.hypot(gx - w["x"], gy - w["y"]) <= WOLF_HEEL:
                continue
        else:
            gx, gy = target.x, target.y
            if best <= WOLF_REACH + target.hit_radius:
                if w["bite"] <= 0:
                    w["bite"] = p["bite"]
                    angle = math.atan2(gy - w["y"], gx - w["x"])
                    strike(target, p["damage"], hero, angle, effects, s.spec.tags,
                           on_hit=full, can_crit=full)
                    effects.append(Effect("impact", target.x, target.y, angle))
                continue
        dist = math.hypot(gx - w["x"], gy - w["y"])
        step = min(dist, p["speed"] * dt)
        w["facing"] = math.atan2(gy - w["y"], gx - w["x"])
        w["x"], w["y"], _, _ = move_hull(world, w["x"], w["y"], 0.0, WOLF_HALF_PX, WOLF_HALF_PX,
                                         (gx - w["x"]) / dist * step, (gy - w["y"]) / dist * step)


def _rune(hero, s: SpellState, world, actors, effects, dt, projectiles, zones) -> list[str]:
    p = s.params
    runes = s.things
    for r in runes:
        r["age"] += dt
    if _due(hero, s, dt):
        runes.append({"x": hero.x, "y": hero.y, "age": 0.0})
        del runes[:-int(p["max"])]
    events = []
    radius = p["radius"] * _area(hero)
    for r in runes:
        trip = any(math.hypot(a.x - r["x"], a.y - r["y"]) <= p["trigger"] + a.hit_radius
                   for a in _near_point(hero, actors, r["x"], r["y"], p["trigger"]))
        if not trip:
            continue
        r["age"] = p["life"]                     # used up
        effects.append(Effect("rune_burst", r["x"], r["y"], size=radius))
        for a in list(_near_point(hero, actors, r["x"], r["y"], radius)):
            if math.hypot(a.x - r["x"], a.y - r["y"]) <= radius + a.hit_radius:
                strike(a, p["damage"], hero, math.atan2(a.y - r["y"], a.x - r["x"]), effects,
                       s.spec.tags)
        events.append("break")
    s.things = [r for r in runes if r["age"] < p["life"]]
    return events


def _near_point(hero, actors, x: float, y: float, reach: float):
    for a in actors:
        if a.hittable and _may_hurt(hero, a) and abs(a.x - x) <= reach + a.hit_radius \
                and abs(a.y - y) <= reach + a.hit_radius:
            yield a


def _flask(hero, s: SpellState, world, actors, effects, dt, projectiles, zones) -> None:
    p = s.params
    for f in s.things:
        f["t"] += dt
    if _due(hero, s, dt):
        near = sorted((a for a in _near(hero, actors, p["reach"])
                       if math.hypot(a.x - hero.x, a.y - hero.y) <= p["reach"]),
                      key=lambda a: math.hypot(a.x - hero.x, a.y - hero.y))
        for i in range(int(p["count"]) if near else 0):
            if i < len(near):
                tx, ty = near[i].x, near[i].y
            else:
                # More flasks than enemies: the rest land round the nearest,
                # a pool's width away.
                a = i * math.tau / int(p["count"])
                off = p["radius"] * _area(hero)
                tx, ty = near[0].x + math.cos(a) * off, near[0].y + math.sin(a) * off
            s.things.append({"x0": hero.x, "y0": hero.y, "x1": tx, "y1": ty,
                             "t": 0.0, "flight": p["flight"]})
    for f in s.things:
        if f["t"] >= f["flight"]:
            zones.append(Zone("pool", f["x1"], f["y1"], p["radius"] * _area(hero),
                              p["life"] * (hero.stats.duration_scale if hero.stats else 1.0),
                              0.5, 0.0, hero, s.spec.tags, p["inflicts"], int(p["stacks"])))
    s.things = [f for f in s.things if f["t"] < f["flight"]]


def cloud_position(hero) -> tuple[float, float]:
    return hero.x + CLOUD_OFFSET[0], hero.y + CLOUD_OFFSET[1]


def _cloud(hero, s: SpellState, world, actors, effects, dt, projectiles, zones) -> list[str]:
    p = s.params
    if not _due(hero, s, dt):
        return []
    near = [a for a in _near(hero, actors, p["reach"])
            if math.hypot(a.x - hero.x, a.y - hero.y) <= p["reach"]]
    cx, cy = cloud_position(hero)
    events = []
    for _ in range(int(p["strikes"])):
        if not near:
            break
        a = near.pop(int(hero.rng.random() * len(near)) % len(near))
        effects.append(Effect("arc", cx, cy, x2=a.x, y2=a.y))
        strike(a, p["damage"], hero, math.atan2(a.y - cy, a.x - cx), effects, s.spec.tags)
        if a.alive:
            inflict(a, p["inflicts"], hero)
        events.append("zap")
    return events


def _totem(hero, s: SpellState, world, actors, effects, dt, projectiles, zones) -> None:
    p = s.params
    for t in s.things:
        t["age"] += dt
    if _due(hero, s, dt):
        s.things.append({"x": hero.x, "y": hero.y, "age": 0.0, "chill": 0.0})
    life = p["life"] * (hero.stats.duration_scale if hero.stats else 1.0)
    s.things = [t for t in s.things if t["age"] < life]
    radius = p["radius"] * _area(hero)
    for t in s.things:
        chill = False
        if p["chill"]:
            t["chill"] -= dt
            if t["chill"] <= 1e-9:
                t["chill"] += p["chill_every"]
                chill = True
        for a in actors:
            d = math.hypot(a.x - t["x"], a.y - t["y"])
            if a.faction == "player":
                if a.alive and d <= radius:
                    a.heal(p["heal"] * dt)
            elif chill and d <= radius + a.hit_radius and a.hittable and _may_hurt(hero, a):
                inflict(a, "chill", hero, int(p["chill"]))


def _shoot(hero, x: float, y: float, target, shell, damage: float, tags, effects,
           projectiles, summon: bool = False, inflicts=None, pierce: int = 0) -> None:
    """A spell's bolt at `target`; Multishot adds bolts, fanned
    MIN_PELLET_GAP degrees apart around the aim (M19)."""
    aim = math.atan2(target.y - y, target.x - x)
    n = 1 + (max(0, round(hero.stats.pellets)) if hero.stats is not None else 0)
    gap = math.radians(config.MIN_PELLET_GAP)
    for i in range(n):
        angle = aim + gap * (i - (n - 1) / 2)
        shot = Projectile(x, y, angle, shell, owner=hero, damage=damage)
        shot.tags = tags
        shot.summon = summon
        shot.inflicts = inflicts
        shot.pierce_left += pierce
        projectiles.append(shot)
    effects.append(Effect("muzzle", x, y, aim))


def _wand(hero, s: SpellState, world, actors, effects, dt, projectiles, zones) -> list[str]:
    p = s.params
    if not _due(hero, s, dt):
        return []
    target = _nearest(hero, actors, p["reach"], world)
    if target is None:
        return []
    _shoot(hero, hero.x, hero.y, target, config.SPELL_SHELLS["wand"], p["damage"], s.spec.tags,
           effects, projectiles, inflicts=(p["inflicts"], int(p["stacks"])))
    return ["spark"]


def _chain(hero, s: SpellState, world, actors, effects, dt, projectiles, zones) -> list[str]:
    p = s.params
    if not _due(hero, s, dt):
        return []
    target = _nearest(hero, actors, p["reach"], world)
    if target is None:
        return []
    st = hero.stats
    shell = config.SPELL_SHELLS["chain"]
    if st is not None:
        shell = replace(shell, chain=shell.chain + int(p["jumps"]) + round(st.chain),
                        chain_range=shell.chain_range * (1 + st.chain_range),
                        chain_falloff=min(0.95, shell.chain_falloff + st.chain_falloff))
    _shoot(hero, hero.x, hero.y, target, shell, p["damage"], s.spec.tags, effects, projectiles)
    return ["spark"]


def _turret(hero, s: SpellState, world, actors, effects, dt, projectiles, zones) -> list[str]:
    p = s.params
    for t in s.things:
        t["age"] += dt
        t["fire"] -= dt
    if _due(hero, s, dt):
        s.things.append({"x": hero.x, "y": hero.y, "age": 0.0, "fire": 0.0})
        del s.things[:-(int(p["count"]) + (1 if _pack(hero) else 0))]
    life = p["life"] * (hero.stats.duration_scale if hero.stats else 1.0)
    s.things = [t for t in s.things if t["age"] < life]
    events = []
    for t in s.things:
        if t["fire"] > 0:
            continue
        best, best_d = None, p["reach"]
        for a in _near_point(hero, actors, t["x"], t["y"], p["reach"]):
            d = math.hypot(a.x - t["x"], a.y - t["y"])
            if d <= best_d and first_hit(world.tile_at, t["x"], t["y"], a.x, a.y) is None:
                best, best_d = a, d
        if best is None:
            continue
        t["fire"] = p["fire"]
        _shoot(hero, t["x"], t["y"], best, config.SPELL_SHELLS["turret"], p["damage"],
               s.spec.tags, effects, projectiles, summon=True, pierce=int(p["pierce"]))
        events.append("bolt")
    return events


_KINDS = {"orbit": _orbit, "aura": _aura, "nova": _nova, "wolf": _wolf, "rune": _rune,
          "flask": _flask, "cloud": _cloud, "totem": _totem, "wand": _wand, "turret": _turret,
          "chain": _chain}
