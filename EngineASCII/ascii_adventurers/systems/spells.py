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
unless you have Pack Leader, which also adds one wolf and one turret
(Packmaster +9: two; +6: a turret that runs out stands again, once; +9:
wolves rush whoever hit the hero).

The trinkets' +3 / +6 / +9 tricks (M28.2f, design/GEAR.md 17.6) live
with their spells here: Grounding, Overload and Eternal arc ride on the
bolt (`Projectile.charm`, combat.chain_from); Glow and Will-o'-wisps on
the wand's bolts (combat); Howl in Character.take_damage; Downpour's
puddle is a zone (zones.py, statuses._wet). Their legendary tricks
(M28.3i, GEAR.md 19.7) too: Conduit (run_rules' combo calls `conduit`),
Satellite (the daggers' centre), Afterburn (auras left behind), Black ice
(an "ice" zone), Spirit pack, Rekindled, Lingering, Storm front (the
cloud's ground spot, `hero.cloud_front`), Lifeline, Firefly
(`hero.fireflies`, set by combat when a bolt hits) and Walking dead.

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
    def __init__(self, key: str, level: int = 1, boost: float = 0.0) -> None:
        self.key = key
        self.spec = config.SPELLS[key]
        self.level = 0
        self.boost = boost         # gear past +4 (players/stats.spell_params)
        self.params: dict = {}
        self.timer = 0.0           # aura / nova: seconds to the next pulse
        self.angle = 0.0           # orbit: where the first dagger is
        self.clock = 0.0
        self._next_hit: dict[tuple[int, int], float] = {}   # (dagger, id(enemy)) -> time
        # What some spells leave in the world: wolves / runes / turrets /
        # totems as small dicts, flasks in the air.
        self.things: list[dict] = []
        self.waiting: list[dict] = []   # turrets down, standing again soon (Packmaster +6)
        # M28.2f, the trinkets' tricks: casts / pulses / novas / bolts /
        # flasks so far (every Nth one is special); the hero's rolls and
        # hits taken when last looked (a new roll: Fling, Runeburst; a new
        # hit: Cold heart, once a nova); the outer ring (Blade storm), the
        # fling (s left, direction), Sunfire's growth, the howl's clock,
        # the rune serials and line hits (Rune lines), the puddle (Downpour),
        # the second cloud's strikes to come (Eye of the storm).
        self.count = 0
        self.rolls: int | None = None
        self.hits: int | None = None
        self.cold = False
        self.angle2 = 0.0
        self.fling = 0.0
        self.fling_dir = (1.0, 0.0)
        self.sun = 0.0
        self.howl = 0.0
        self.serial = 0
        self._line_hit: dict[tuple, float] = {}
        self.puddle = None
        self.eye: list[float] = []
        # M28.3i: auras left behind, each [x, y, s left] (Afterburn); runes
        # coming back, each {x, y, t} (Rekindled).
        self.left: list[list[float]] = []
        self.later: list[dict] = []
        self.set_level(level, boost)
        self.timer = self.params.get("interval", 0.0) * 0.5   # first pulse comes soon

    def set_level(self, level: int, boost: float = 0.0) -> None:
        self.level = level
        self.boost = boost
        self.params = spell_params(self.key, level, boost)

    def dagger_positions(self, hero) -> list[tuple[float, float, float]]:
        """(x, y, angle) of each dagger; angle is where it points (along
        its orbit). Bladewheel Charm: +6 (Breathing ring) the orbit swells
        now and then; +9 (Blade storm) two more daggers, the daggers split
        into two rings, the outer one turning the other way; +3 (Fling)
        out along a roll and back."""
        p = self.params
        n = int(p["count"])
        r = p["radius"] * _area(hero)
        foe = satellite(hero)
        if foe is not None:                     # (Satellite: just outside its body, to cut it)
            r = min(r, foe.hit_radius + config.SATELLITE[1])
        r *= self.breath(hero)
        rings = [(n, self.angle, r, 1)]
        if _has(hero, "daggers+9"):
            more, wide = config.BLADE_STORM
            outer = (n + more) // 2
            rings = [(n + more - outer, self.angle, r, 1), (outer, self.angle2, r * wide, -1)]
        cx, cy = satellite_centre(hero)
        ox, oy = cx - hero.x, cy - hero.y
        if self.fling > 0:
            out, seconds = config.FLING
            reach = out * math.sin(math.pi * (1 - self.fling / seconds))
            ox, oy = ox + self.fling_dir[0] * reach, oy + self.fling_dir[1] * reach
        dots = []
        for k, start, rr, way in rings:
            for i in range(k):
                a = start + i * math.tau / k
                dots.append((hero.x + ox + math.cos(a) * rr, hero.y + oy + math.sin(a) * rr,
                             a + way * math.pi / 2))
        return dots

    def breath(self, hero) -> float:
        """Breathing ring (Bladewheel +6): x the orbit's width right now."""
        if not _has(hero, "daggers+6"):
            return 1.0
        every, swell, most = config.BREATHING
        t = self.clock % every
        return 1 + (most - 1) * math.sin(math.pi * t / swell) if t < swell else 1.0


def satellite(hero):
    """Bladewheel Charm (L), Satellite: the enemy the daggers circle -- the
    one the hero hit last, until it dies or SATELLITE[0] s pass without a
    hit on it (combat.strike keeps `hero.satellite`); None: the hero."""
    sat = getattr(hero, "satellite", None)
    if sat is not None and _has(hero, "daggers+L"):
        foe, t = sat
        if foe.alive and foe.hittable and hero.time - t <= config.SATELLITE[0] + 1e-9:
            return foe
        hero.satellite = None
    return None


def satellite_centre(hero) -> tuple[float, float]:
    """Where the daggers circle: the hero, or Satellite's enemy."""
    foe = satellite(hero)
    return (foe.x, foe.y) if foe is not None else (hero.x, hero.y)


def _area(hero) -> float:
    return hero.stats.area_scale if hero.stats is not None else 1.0


def _cooldown(hero) -> float:
    return hero.stats.cooldown_scale if hero.stats is not None else 1.0


def sync_spells(spells: dict[str, SpellState], levels: dict[str, int],
                boosts: dict[str, float] | None = None) -> None:
    """Match a player's spell states to their gear (new spells, level-ups,
    a trinket taken off). `boosts`: HeroStats.spell_boost."""
    boosts = boosts or {}
    for key, level in levels.items():
        boost = boosts.get(key, 0.0)
        if key not in spells:
            spells[key] = SpellState(key, level, boost)
        elif spells[key].level != level or spells[key].boost != boost:
            spells[key].set_level(level, boost)
    for key in [k for k in spells if k not in levels]:
        del spells[key]


def update_spells(hero, spells: dict[str, SpellState], world, actors, effects: list[Effect],
                  dt: float, projectiles: list | None = None,
                  zones: list | None = None) -> list[str]:
    """Run a hero's spells for one step. Returns sound events."""
    events: list[str] = []
    projectiles = projectiles if projectiles is not None else []
    zones = zones if zones is not None else []
    shots, grounds = len(projectiles), len(zones)
    hero.spelling = True                 # (M28.3l: Fortissimo Lute (L), Tutti: spells' hits)
    try:
        for s in spells.values():
            s.clock += dt
            run = _KINDS.get(s.spec.kind)
            if run is not None:
                events += run(hero, s, world, actors, effects, dt, projectiles, zones) or []
    finally:
        hero.spelling = False
    for q in projectiles[shots:]:
        if q.owner is hero:
            q.spell = True
    for z in zones[grounds:]:
        if z.source is hero:
            z.spell = True
    return events


def _has(hero, flag: str) -> bool:
    return hero.stats is not None and hero.stats.has(flag)


def _rolled(hero, s: SpellState) -> bool:
    """Whether the hero started a roll since the spell last looked."""
    rolls = getattr(hero, "rolls", 0)
    new = s.rolls is not None and rolls != s.rolls
    s.rolls = rolls
    return new


def _pack(hero) -> bool:
    return hero.stats is not None and hero.stats.has("pack_leader")


def _extra(hero) -> int:
    """Summons Pack Leader adds: one, two with Packmaster +9 (The pack)."""
    return (1 if _pack(hero) else 0) + (1 if _pack(hero) and hero.stats.has("pack_leader+9") else 0)


def _rushed(hero):
    """Packmaster +9 (The pack): whoever hit the hero lately, while it lives."""
    rush = getattr(hero, "rush", None)
    if rush is None:
        return None
    foe, until = rush
    if until < hero.time or not foe.alive or not foe.hittable:
        hero.rush = None
        return None
    return foe


def haste(hero) -> float:
    """War Drum (L), Warpath: x how fast the hero's spells' clocks (and
    their summons' attacks) run while a frenzy is on."""
    return config.WARPATH if getattr(hero, "warpath", False) else 1.0


def _due(hero, s: SpellState, dt: float) -> bool:
    """Count the spell's timer down; True (and rewound) when it's time."""
    s.timer -= dt * haste(hero)
    if s.timer > 1e-9:
        return False
    s.timer += s.params["interval"] * _cooldown(hero)
    return True


def _nearest(hero, actors, reach: float, world=None, prefer=None):
    """The nearest enemy within `reach` of the hero (in sight, if `world`);
    with `prefer`, the nearest one it's true for comes first."""
    best, best_key = None, None
    for a in _near(hero, actors, reach):
        d = math.hypot(a.x - hero.x, a.y - hero.y)
        if d > reach:
            continue
        key = (prefer is not None and not prefer(a), d)
        if (best_key is None or key < best_key) and (
                world is None or first_hit(world.tile_at, hero.x, hero.y, a.x, a.y) is None):
            best, best_key = a, key
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
    s.angle2 = (s.angle2 - p["turn"] * dt) % math.tau
    s.fling = max(0.0, s.fling - dt)
    if _rolled(hero, s) and _has(hero, "daggers+3"):            # Fling
        dx, dy = hero.roll_dir
        n = math.hypot(dx, dy) or 1.0
        s.fling, s.fling_dir = config.FLING[1], (dx / n, dy / n)
    daggers = s.dagger_positions(hero)
    cx, cy = satellite_centre(hero)
    reach = max((math.hypot(x - cx, y - cy) for x, y, _ in daggers), default=0.0) \
        + DAGGER_HIT_RADIUS
    hero.orbiting = True                      # (their hits don't move Satellite's enemy)
    for a in list(_near_point(hero, actors, cx, cy, reach)):
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
    hero.orbiting = False
    if len(s._next_hit) > 256:          # forget enemies long gone
        s._next_hit = {k: t for k, t in s._next_hit.items() if t > s.clock}


def aura_radius(hero, s: SpellState) -> float:
    """The ember aura's reach (tiles), Sunfire's growth included."""
    return s.params["radius"] * _area(hero) + s.sun


def _aura(hero, s: SpellState, world, actors, effects, dt, projectiles, zones) -> None:
    p = s.params
    for left in s.left:
        left[2] -= dt
    s.left = [a for a in s.left if a[2] > 1e-9]
    if _rolled(hero, s) and _has(hero, "ember_aura+L"):        # (L): Afterburn
        x, y = getattr(hero, "roll_from", (hero.x, hero.y))
        s.left.append([x, y, config.AFTERBURN])
    if not _due(hero, s, dt):
        return
    s.count += 1
    r = aura_radius(hero, s)
    stacks = int(p["stacks"])
    every, flare = config.FLARE_UP
    if _has(hero, "ember_aura+6") and s.count % every == 0:     # Flare-up
        stacks = max(stacks, flare)
        effects.append(Effect("pulse", hero.x, hero.y, size=r))
    for x, y, _ in s.left:                                     # (the auras left behind)
        for a in list(_near_point(hero, actors, x, y, r)):
            if math.hypot(a.x - x, a.y - y) <= r + a.hit_radius:
                inflict(a, p["inflicts"], hero, stacks)
    burned = 0
    for a in list(_near(hero, actors, r)):
        if math.hypot(a.x - hero.x, a.y - hero.y) <= r + a.hit_radius:
            inflict(a, p["inflicts"], hero, stacks)
            burned += 1
    if _has(hero, "ember_aura+3") and burned >= config.WARMTH:  # Warmth
        hero.heal(burned // config.WARMTH)
    if _has(hero, "ember_aura+9"):                             # Sunfire
        per, most = config.SUNFIRE
        burning = sum(1 for a in _near(hero, actors, r)
                      if a.alive and math.hypot(a.x - hero.x, a.y - hero.y) <= r + a.hit_radius
                      and a.status is not None and a.status.has("burn"))
        s.sun = min(most, per * burning)
    else:
        s.sun = 0.0


def _nova(hero, s: SpellState, world, actors, effects, dt, projectiles, zones) -> list[str]:
    p = s.params
    hits = getattr(hero, "hits_taken", 0)
    if s.hits is not None and hits > s.hits and not s.cold \
            and _has(hero, "frost_nova+3"):                    # Cold heart (once a nova)
        s.timer -= config.COLD_HEART
        s.cold = True
    s.hits = hits
    if not _due(hero, s, dt):
        return []
    s.cold = False
    s.count += 1
    r = p["radius"] * _area(hero)
    every, wide = config.AVALANCHE
    avalanche = _has(hero, "frost_nova+9") and s.count % every == 0
    if avalanche:
        r *= wide
    effects.append(Effect("nova", hero.x, hero.y, size=r))
    chilled = 0
    for a in list(_near(hero, actors, r)):
        if math.hypot(a.x - hero.x, a.y - hero.y) > r + a.hit_radius:
            continue
        if first_hit(world.tile_at, hero.x, hero.y, a.x, a.y) is not None:
            continue
        angle = math.atan2(a.y - hero.y, a.x - hero.x)
        strike(a, p["damage"], hero, angle, effects, s.spec.tags)
        if a.alive:
            stacks = int(p["stacks"])
            if avalanche and not getattr(a, "boss", False):     # (frozen at once)
                stacks = config.STATUSES["chill"].max_stacks
            inflict(a, p["inflicts"], hero, stacks)
            chilled += 1
    if chilled and _has(hero, "frost_nova+6"):                 # Ice armor
        per, most = config.ICE_ARMOR
        top = hero.stats.shield + most
        hero.shield = max(hero.shield, min(top, hero.shield + per * chilled))
    if _has(hero, "frost_nova+L"):                             # (L): Black ice
        seconds, every = config.BLACK_ICE
        ice = Zone("ice", hero.x, hero.y, r, seconds * hero.stats.duration_scale, every, 0.0,
                   hero, s.spec.tags, p["inflicts"], 1)
        ice.timer = every                        # (the nova itself just chilled them)
        zones.append(ice)
    return ["nova"]


def _scent(hero, reach: float):
    """Scent (Wolfcall +3): the enemy the hero hit last, while it lives
    within the wolves' sight of the hero."""
    foe = getattr(hero, "scent", None)
    if foe is None or not _has(hero, "spirit_wolf+3"):
        return None
    if not foe.alive or not foe.hittable or math.hypot(foe.x - hero.x, foe.y - hero.y) > reach:
        return None
    return foe


def dire(hero) -> float:
    """Dire wolves (Wolfcall +9): x a wolf's size."""
    return config.DIRE_WOLVES[0] if _has(hero, "spirit_wolf+9") else 1.0


def _wolf(hero, s: SpellState, world, actors, effects, dt, projectiles, zones) -> None:
    p = s.params
    want = int(p["count"]) + _extra(hero)
    wolves = s.things
    while len(wolves) < want:
        wolves.append({"x": hero.x, "y": hero.y, "bite": 0.0, "facing": 0.0})
    del wolves[want:]
    full = _pack(hero)
    rushed = _rushed(hero) or _scent(hero, p["sight"])
    size = dire(hero)
    spirits = _has(hero, "spirit_wolf+L")
    damage = image_bite(hero, p["damage"]) * (config.DIRE_WOLVES[1] if size > 1 else 1.0)
    if _has(hero, "spirit_wolf+6"):                            # Howl
        s.howl += dt
        every, reach, _, seconds = config.HOWL
        if s.howl >= every:
            s.howl -= every
            for w in wolves:
                effects.append(Effect("howl", w["x"], w["y"], size=reach))
                for a in _near_point(hero, actors, w["x"], w["y"], reach):
                    if math.hypot(a.x - w["x"], a.y - w["y"]) <= reach + a.hit_radius:
                        a.howled = (hero, hero.time + seconds)
    for w in wolves:
        w["bite"] = max(0.0, w["bite"] - dt * haste(hero))   # (Warpath: bites faster)
        target = None
        best = p["sight"]
        if rushed is not None:
            target, best = rushed, math.hypot(rushed.x - w["x"], rushed.y - w["y"])
        else:
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
            if best <= WOLF_REACH * size + target.hit_radius:
                if w["bite"] <= 0:
                    w["bite"] = p["bite"]
                    angle = math.atan2(gy - w["y"], gx - w["x"])
                    strike(target, damage, hero, angle, effects, s.spec.tags,
                           on_hit=full, can_crit=full, pet=True)
                    if size > 1 and target.alive:                 # (Dire wolves: bleed)
                        inflict(target, "bleed", hero, config.DIRE_WOLVES[2])
                    effects.append(Effect("impact", target.x, target.y, angle))
                continue
        dist = math.hypot(gx - w["x"], gy - w["y"])
        step = min(dist, p["speed"] * dt)
        w["facing"] = math.atan2(gy - w["y"], gx - w["x"])
        dx, dy = (gx - w["x"]) / dist * step, (gy - w["y"]) / dist * step
        if spirits:                              # (L): Spirit pack -- through it all
            w["x"], w["y"] = w["x"] + dx, w["y"] + dy
            continue
        half = round(WOLF_HALF_PX * size)
        w["x"], w["y"], _, _ = move_hull(world, w["x"], w["y"], 0.0, half, half, dx, dy)


def rune_links(hero, s: SpellState) -> list[tuple[dict, dict]]:
    """Rune lines (Runestone +3): the pairs of runes close enough to link."""
    if not _has(hero, "rune_trap+3"):
        return []
    reach = config.RUNE_LINES[0]
    runes = s.things
    return [(a, b) for i, a in enumerate(runes) for b in runes[i + 1:]
            if math.hypot(a["x"] - b["x"], a["y"] - b["y"]) <= reach]


def _rune(hero, s: SpellState, world, actors, effects, dt, projectiles, zones) -> list[str]:
    p = s.params
    runes = s.things
    for r in runes:
        r["age"] += dt
    if _due(hero, s, dt):
        s.serial += 1
        runes.append({"x": hero.x, "y": hero.y, "age": 0.0, "n": s.serial})
        del runes[:-int(p["max"])]
    for back in s.later:                                       # (L): Rekindled
        back["t"] -= dt
        if back["t"] <= 1e-9:
            s.serial += 1
            runes.append({"x": back["x"], "y": back["y"], "age": 0.0, "n": s.serial, "again": True})
    s.later = [b for b in s.later if b["t"] > 1e-9]
    if _has(hero, "rune_trap+6"):                              # Seeking runes
        notice, speed = config.SEEKING_RUNES
        for r in runes:
            best, best_d = None, notice
            for a in _near_point(hero, actors, r["x"], r["y"], notice):
                d = math.hypot(a.x - r["x"], a.y - r["y"])
                if d < best_d:
                    best, best_d = a, d
            if best is not None and best_d > 1e-6:
                step = min(best_d, speed * dt)
                r["x"], r["y"], _, _ = move_hull(world, r["x"], r["y"], 0.0, 2, 2,
                                                 (best.x - r["x"]) / best_d * step,
                                                 (best.y - r["y"]) / best_d * step)
    events = []
    radius = p["radius"] * _area(hero)
    burst_all = _rolled(hero, s) and _has(hero, "rune_trap+9")  # Runeburst
    for r in runes:
        trip = burst_all or any(
            math.hypot(a.x - r["x"], a.y - r["y"]) <= p["trigger"] + a.hit_radius
            for a in _near_point(hero, actors, r["x"], r["y"], p["trigger"]))
        if not trip:
            continue
        r["age"] = p["life"]                     # used up
        if _has(hero, "rune_trap+L") and not r.get("again"):
            s.later.append({"x": r["x"], "y": r["y"], "t": config.REKINDLED})
        effects.append(Effect("rune_burst", r["x"], r["y"], size=radius))
        for a in list(_near_point(hero, actors, r["x"], r["y"], radius)):
            if math.hypot(a.x - r["x"], a.y - r["y"]) <= radius + a.hit_radius:
                strike(a, p["damage"], hero, math.atan2(a.y - r["y"], a.x - r["x"]), effects,
                       s.spec.tags)
        events.append("break")
    s.things = [r for r in runes if r["age"] < p["life"]]
    _rune_lines(hero, s, actors, effects)
    return events


def _rune_lines(hero, s: SpellState, actors, effects) -> None:
    """Rune lines (Runestone +3): an enemy on a line between two linked
    runes takes RUNE_LINES[1], once every RUNE_LINES[2] s a line."""
    _, damage, again = config.RUNE_LINES
    for r1, r2 in rune_links(hero, s):
        dx, dy = r2["x"] - r1["x"], r2["y"] - r1["y"]
        mx, my = (r1["x"] + r2["x"]) / 2, (r1["y"] + r2["y"]) / 2
        half = math.hypot(dx, dy) / 2
        for a in list(_near_point(hero, actors, mx, my, half + 0.5)):
            if _to_segment(a.x, a.y, r1["x"], r1["y"], dx, dy) > a.hit_radius + 0.2:
                continue
            key = (r1["n"], r2["n"], id(a))
            if s._line_hit.get(key, -1.0) > s.clock:
                continue
            s._line_hit[key] = s.clock + again
            strike(a, damage, hero, math.atan2(dy, dx) + math.pi / 2, effects, s.spec.tags)
    if len(s._line_hit) > 256:
        s._line_hit = {k: t for k, t in s._line_hit.items() if t > s.clock}


def _to_segment(px: float, py: float, x0: float, y0: float, dx: float, dy: float) -> float:
    """Distance from (px, py) to the segment (x0, y0) + t (dx, dy)."""
    n = dx * dx + dy * dy
    t = 0.0 if n == 0 else max(0.0, min(1.0, ((px - x0) * dx + (py - y0) * dy) / n))
    return math.hypot(px - x0 - t * dx, py - y0 - t * dy)


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
            s.count += 1
            brew = p["inflicts"]
            every, brews = config.WITCHS_BREW
            if _has(hero, "poison_flask+6") and s.count % every == 0:   # Witch's brew
                brew = brews[int(hero.rng.random() * len(brews)) % len(brews)]
            s.things.append({"x0": hero.x, "y0": hero.y, "x1": tx, "y1": ty,
                             "t": 0.0, "flight": p["flight"], "brew": brew})
    for f in s.things:
        if f["t"] >= f["flight"]:
            brew = f.get("brew", p["inflicts"])
            tags = s.spec.tags if brew == p["inflicts"] else \
                (config.STATUSES[brew].tag, "area")
            pool = Zone("pool", f["x1"], f["y1"], p["radius"] * _area(hero),
                        p["life"] * (hero.stats.duration_scale if hero.stats else 1.0),
                        0.5, 0.0, hero, tags, brew, int(p["stacks"]))
            pool.flask = True
            if _has(hero, "poison_flask+3"):                     # Bubbling
                pool.grow = config.BUBBLING
            if _has(hero, "poison_flask+9"):                     # Cauldron
                pool = _cauldron(pool, zones, p["radius"] * _area(hero) * config.CAULDRON_MAX)
            pool.linger = _has(hero, "poison_flask+L")          # (L): Lingering
            zones.append(pool)
    s.things = [f for f in s.things if f["t"] < f["flight"]]
    _linger(hero, actors, zones)


def _linger(hero, actors, zones) -> None:
    """Witch's Flask (L), Lingering: while an enemy stands in one of the
    hero's pools, it doesn't run out (LINGERING[1] s more once it's left),
    up to LINGERING[0] s in all."""
    most, after = config.LINGERING
    for z in zones:
        if not getattr(z, "linger", False) or z.source is not hero or z.age >= z.life:
            continue
        if any(math.hypot(a.x - z.x, a.y - z.y) <= z.radius + a.hit_radius
               for a in _near_point(hero, actors, z.x, z.y, z.radius)):
            z.life = min(most, max(z.life, z.age + after))


def _cauldron(pool: Zone, zones: list, most: float) -> Zone:
    """Cauldron (Witch's Flask +9): the hero's pools of the same brew that
    touch the new one merge into it -- their areas add up (to a radius of
    `most`), centred between them by area, lasting as long as the new one."""
    merged = True
    while merged:
        merged = False
        for z in zones:
            if not getattr(z, "flask", False) or z.source is not pool.source \
                    or z.inflicts != pool.inflicts or z.age >= z.life:
                continue
            if math.hypot(z.x - pool.x, z.y - pool.y) > z.radius + pool.radius:
                continue
            a1, a2 = pool.radius ** 2, z.radius ** 2
            pool.x = (pool.x * a1 + z.x * a2) / (a1 + a2)
            pool.y = (pool.y * a1 + z.y * a2) / (a1 + a2)
            pool.radius = min(most, math.sqrt(a1 + a2))
            zones.remove(z)
            merged = True
            break
    pool.base = pool.radius
    return pool


def cloud_ground(hero) -> tuple[float, float]:
    """The ground the storm cloud is over: the hero -- or, Stormjar (L)
    (Storm front), the spot it drifts to toward the aim."""
    front = getattr(hero, "cloud_front", None)
    return front if front is not None else (hero.x, hero.y)


def cloud_position(hero) -> tuple[float, float]:
    gx, gy = cloud_ground(hero)
    return gx + CLOUD_OFFSET[0], gy + CLOUD_OFFSET[1]


def _drift(hero, dt: float) -> None:
    """Storm front: the cloud drifts at STORM_FRONT[1] tiles/s toward the
    spot STORM_FRONT[0] tiles (at most) from the hero toward the aim."""
    if not _has(hero, "storm_cloud+L"):
        hero.cloud_front = None
        return
    most, speed = config.STORM_FRONT
    ax, ay = hero.aim_point if hero.aim_point is not None else (
        hero.x + math.cos(hero.aim_angle) * most, hero.y + math.sin(hero.aim_angle) * most)
    far = math.hypot(ax - hero.x, ay - hero.y)
    if far > most:
        ax, ay = hero.x + (ax - hero.x) / far * most, hero.y + (ay - hero.y) / far * most
    fx, fy = hero.cloud_front if hero.cloud_front is not None else (hero.x, hero.y)
    d = math.hypot(ax - fx, ay - fy)
    step = min(d, speed * dt)
    if d > 1e-9:
        fx, fy = fx + (ax - fx) / d * step, fy + (ay - fy) / d * step
    off = math.hypot(fx - hero.x, fy - hero.y)
    if off > most:                               # (it never trails more than that behind you)
        fx, fy = hero.x + (fx - hero.x) / off * most, hero.y + (fy - hero.y) / off * most
    hero.cloud_front = (fx, fy)


def eye_position(hero, s: SpellState) -> tuple[float, float]:
    """Eye of the storm (Stormjar +9): the second cloud, circling the hero."""
    _, radius, turn = config.EYE_OF_THE_STORM
    a = s.clock * turn
    return hero.x + math.cos(a) * radius, hero.y + math.sin(a) * radius + CLOUD_OFFSET[1]


def puddle_spot(hero) -> tuple[float, float]:
    """Downpour (Stormjar +3): the ground under the cloud."""
    gx, gy = cloud_ground(hero)
    return gx + CLOUD_OFFSET[0], gy


def _cloud(hero, s: SpellState, world, actors, effects, dt, projectiles, zones) -> list[str]:
    p = s.params
    _drift(hero, dt)
    if _has(hero, "storm_cloud+3"):                            # Downpour
        x, y = puddle_spot(hero)
        z = s.puddle
        if z is None or z.age >= z.life or not any(q is z for q in zones):
            z = s.puddle = Zone("puddle", x, y, config.DOWNPOUR * _area(hero), 0.5, 0.25, 0.0,
                                hero)
            z.wet = True
            zones.append(z)
        z.x, z.y, z.age = x, y, 0.0
    events = []
    eye = _has(hero, "storm_cloud+9")
    for i in range(len(s.eye)):
        s.eye[i] -= dt
    if eye:
        while s.eye and s.eye[0] <= 1e-9:
            s.eye.pop(0)
            events += _strikes(hero, s, *eye_position(hero, s), actors, effects, (hero.x, hero.y))
    else:
        s.eye.clear()
    if not _due(hero, s, dt):
        return events
    events += _strikes(hero, s, *cloud_position(hero), actors, effects, cloud_ground(hero))
    if eye:
        s.eye.append(config.EYE_OF_THE_STORM[0])
    return events


def _strikes(hero, s: SpellState, cx: float, cy: float, actors, effects,
             around: tuple[float, float]) -> list[str]:
    """A storm cloud's strikes: `strikes` random enemies within reach of the
    ground it's over (`around`: the hero, or Storm front's spot);
    Thunderhead (Stormjar +6) strikes whoever hit the hero last first."""
    p = s.params
    gx, gy = around
    near = [a for a in _near_point(hero, actors, gx, gy, p["reach"])
            if math.hypot(a.x - gx, a.y - gy) <= p["reach"]]
    last = getattr(hero, "struck_by", None)
    first = last if (last is not None and last in near and _has(hero, "storm_cloud+6")) else None
    events = []
    for _ in range(int(p["strikes"])):
        if not near:
            break
        if first is not None:
            a, first = first, None
            near.remove(a)
        else:
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
    tree = _has(hero, "healing_totem+9")                      # Tree of life
    if _due(hero, s, dt):
        if tree:
            s.things.clear()
        s.things.append({"x": hero.x, "y": hero.y, "age": 0.0, "chill": 0.0, "in": []})
    life = math.inf if tree else p["life"] * (hero.stats.duration_scale if hero.stats else 1.0)
    s.things = [t for t in s.things if t["age"] < life]
    radius = p["radius"] * _area(hero)
    cleanse = _has(hero, "healing_totem+3")
    for t in s.things:
        if _has(hero, "healing_totem+6"):                     # Carried
            d = math.hypot(hero.x - t["x"], hero.y - t["y"])
            if d > 0.5:
                step = min(d - 0.5, config.CARRIED * dt)
                t["x"], t["y"], _, _ = move_hull(world, t["x"], t["y"], 0.0, 4, 4,
                                                 (hero.x - t["x"]) / d * step,
                                                 (hero.y - t["y"]) / d * step)
        chill = False
        if p["chill"]:
            t["chill"] -= dt
            if t["chill"] <= 1e-9:
                t["chill"] += p["chill_every"]
                chill = True
        inside = t.setdefault("in", [])
        for a in actors:
            d = math.hypot(a.x - t["x"], a.y - t["y"])
            if a.faction == "player":
                if a is hero and a.alive and d > radius and _has(hero, "healing_totem+L"):
                    a.heal(p["heal"] * config.LIFELINE * dt)       # (L): Lifeline
                if a.alive and d <= radius:
                    a.heal(p["heal"] * dt)
                    if cleanse and not any(h is a for h in inside):   # Cleansing light
                        inside.append(a)
                        _cleanse(a, effects)
                elif any(h is a for h in inside):
                    inside[:] = [h for h in inside if h is not a]
            elif chill and d <= radius + a.hit_radius and a.hittable and _may_hurt(hero, a):
                inflict(a, "chill", hero, int(p["chill"]))


def _cleanse(hero, effects) -> None:
    """Cleansing light (Mender's Totem +3, user 2026-10-19): stepping into
    the ring ends what enemies and bosses put on you -- slows and roots,
    stone, the Fallout King's rads, the Snow King's chill and ice, Nettle's
    shrinking."""
    had = (getattr(hero, "slow_t", 0) > 0 or getattr(hero, "petrified", 0) > 0
           or getattr(hero, "rads", 0) > 0 or getattr(hero, "irradiated", 0) > 0
           or getattr(hero, "chill", 0) > 0 or getattr(hero, "encased", 0) > 0
           or getattr(hero, "shrunk", 0) > 0)
    if not had:
        return
    hero.slow_t, hero.slow_mult = 0.0, 1.0
    hero.petrified = 0.0
    hero.rads = hero.irradiated = 0.0
    hero.chill = hero.encased = 0.0
    hero.shrunk = 0.0
    effects.append(Effect("heal_beam", hero.x, hero.y - 1.0, x2=hero.x, y2=hero.y))


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


def _burning(a) -> bool:
    return a.status is not None and a.status.has("burn")


def _fireflies(hero, dt: float) -> None:
    """Firefly Lantern (L), Firefly: a bolt that hit buzzes round its enemy
    (hero.fireflies: [enemy, s left, s to the next burn, (status, stacks)],
    combat._hit_actor), burning it every FIREFLY[1] s for FIREFLY[0] s."""
    for f in hero.fireflies:
        foe = f[0]
        f[1] -= dt
        f[2] -= dt
        if f[2] <= 1e-9 and f[1] > -1e-9 and foe.alive:
            f[2] += config.FIREFLY[1]
            inflict(foe, f[3][0], hero, f[3][1])
    hero.fireflies = [f for f in hero.fireflies if f[1] > 1e-9 and f[0].alive]


def _wand(hero, s: SpellState, world, actors, effects, dt, projectiles, zones) -> list[str]:
    p = s.params
    if hero.fireflies:
        _fireflies(hero, dt)
    if not _due(hero, s, dt):
        return []
    moth = _burning if _has(hero, "fire_wand+6") else None    # Moth
    target = _nearest(hero, actors, p["reach"], world, prefer=moth)
    if target is None:
        return []
    before = len(projectiles)
    _shoot(hero, hero.x, hero.y, target, config.SPELL_SHELLS["wand"], p["damage"], s.spec.tags,
           effects, projectiles, inflicts=(p["inflicts"], int(p["stacks"])))
    for shot in projectiles[before:]:
        shot.glow = _has(hero, "fire_wand+3")                 # Glow
        shot.firefly = _has(hero, "fire_wand+L")              # (L): Firefly
        s.count += 1
        if _has(hero, "fire_wand+9") and s.count % config.WISPS[0] == 0:
            shot.wisp = True                                  # Will-o'-wisps
    return ["spark"]


def _chain(hero, s: SpellState, world, actors, effects, dt, projectiles, zones) -> list[str]:
    p = s.params
    if not _due(hero, s, dt):
        return []
    target = _nearest(hero, actors, p["reach"], world)
    if target is None:
        return []
    shell = _chain_shell(hero, s)
    s.count += 1
    if _has(hero, "chain_lightning+6") and s.count % config.OVERLOAD == 0:   # Overload
        shell = replace(shell, chain=shell.chain * 2)
    targets = [target]
    most, near = config.DOWNDRAFT
    if _has(hero, "supercell+6") and sum(                  # Thunderhead Rod +6 (Downdraft)
            1 for a in _near(hero, actors, near)
            if _shocked(a) and math.hypot(a.x - hero.x, a.y - hero.y) <= near) >= most:
        targets.append(_nearest(hero, actors, p["reach"], world, prefer=lambda a: a is not target))
    for i, t in enumerate(targets):
        before = len(projectiles)
        _shoot(hero, hero.x, hero.y, t, shell, p["damage"], s.spec.tags, effects, projectiles)
        for shot in projectiles[before:]:
            shot.charm = True                     # (Grounding, Eternal arc: combat.chain_from)
        if i == 0 and _has(hero, "ball_lightning+9") and s.count % config.THUNDERBALL[0] == 0:
            projectiles[before].ball = [(hero.x, hero.y)]   # Crackle Staff +9 (Thunderball)
    return ["spark"]


def _chain_shell(hero, s: SpellState):
    """Chain Lightning's bolt: the shock bolt with the spell's jumps and the
    build's (Storm Caller, Conductor's reach and fade)."""
    p = s.params
    st = hero.stats
    shell = config.SPELL_SHELLS["chain"]
    if st is not None:
        shell = replace(shell, chain=shell.chain + int(p["jumps"]) + round(st.chain)
                        + (config.THUNDERLORD[0] if st.has("storm_caller+9") else 0),
                        chain_range=shell.chain_range * (1 + st.chain_range),
                        chain_falloff=min(0.95, shell.chain_falloff + st.chain_falloff))
    return shell


def conduit(hero, s: SpellState, at, world, actors, effects, projectiles) -> list[str]:
    """Chainbolt Charm (L), Conduit: a crit casts the spell's bolt from the
    enemy it hit (`at`) at the nearest other one in sight within reach of
    it, jumping on as usual (run_rules keeps it to CONDUIT a second)."""
    reach = s.params["reach"]
    best, best_d = None, reach
    for a in _near_point(hero, actors, at.x, at.y, reach):
        d = math.hypot(a.x - at.x, a.y - at.y)
        if a is at or d > best_d or first_hit(world.tile_at, at.x, at.y, a.x, a.y) is not None:
            continue
        best, best_d = a, d
    if best is None:
        return []
    before = len(projectiles)
    _shoot(hero, at.x, at.y, best, _chain_shell(hero, s), s.params["damage"], s.spec.tags,
           effects, projectiles)
    for shot in projectiles[before:]:
        shot.charm = True                     # (Grounding, Eternal arc ride on it too)
        shot.hit.add(id(at))
    return ["spark"]


def _shocked(a) -> bool:
    return a.status is not None and a.status.has("shock")


def _turret(hero, s: SpellState, world, actors, effects, dt, projectiles, zones) -> list[str]:
    p = s.params
    for t in s.things:
        t["age"] += dt
        t["fire"] -= dt * haste(hero)                        # (Warpath: it shoots faster)
    legion = _has(hero, "bone_turret+9")                     # Bone legion
    most = int(p["count"]) + _extra(hero) + (config.BONE_LEGION if legion else 0)
    calcify = _has(hero, "bone_turret+6")
    if _due(hero, s, dt):
        x, y = hero.x, hero.y
        spot = getattr(hero, "kill_spot", None)
        if spot is not None and _has(hero, "bone_turret+3") \
                and math.hypot(spot[0] - x, spot[1] - y) <= config.OSSUARY_REACH:
            x, y = spot                                        # Ossuary
        s.things.append({"x": x, "y": y, "age": 0.0, "fire": 0.0})
        for t in s.things[:-most]:
            if calcify:
                _calcify(hero, t, s, effects, projectiles)
        del s.things[:-most]
    life = math.inf if legion else p["life"] * (hero.stats.duration_scale if hero.stats else 1.0)
    loyal = hero.stats is not None and hero.stats.has("pack_leader+6")
    for t in s.things:
        if t["age"] >= life:
            if calcify:
                _calcify(hero, t, s, effects, projectiles)
            if loyal and not t.get("again"):
                s.waiting.append({"x": t["x"], "y": t["y"], "t": config.LOYAL})   # Packmaster +6
    s.things = [t for t in s.things if t["age"] < life]
    for w in s.waiting:
        w["t"] -= dt
        if w["t"] <= 1e-9:                          # (Loyal: it stands again, for good this time)
            s.things.append({"x": w["x"], "y": w["y"], "age": 0.0, "fire": 0.0, "again": True})
            for t in s.things[:-most]:
                if calcify:
                    _calcify(hero, t, s, effects, projectiles)
            del s.things[:-most]
    s.waiting = [w for w in s.waiting if w["t"] > 1e-9]
    events = []
    if _has(hero, "bone_turret+L"):
        _walk(hero, s, world, actors, dt)                     # (L): Walking dead
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
        if _pack(hero) and _has(hero, "pack_leader+L"):
            events += _in_my_image(hero, t, best, world, actors, effects, projectiles)
            continue
        _shoot(hero, t["x"], t["y"], best, config.SPELL_SHELLS["turret"], p["damage"],
               s.spec.tags, effects, projectiles, summon=True, pierce=int(p["pierce"]))
        events.append("bolt")
    return events


def _walk(hero, s: SpellState, world, actors, dt: float) -> None:
    """Skull Sentry (L), Walking dead: each turret walks at WALKING_DEAD[0]
    tiles/s toward the nearest enemy within its reach, stopping
    WALKING_DEAD[1] tiles short of it."""
    speed, short = config.WALKING_DEAD
    reach = s.params["reach"]
    for t in s.things:
        best, best_d = None, reach
        for a in _near_point(hero, actors, t["x"], t["y"], reach):
            d = math.hypot(a.x - t["x"], a.y - t["y"])
            if d <= best_d:
                best, best_d = a, d
        if best is None:
            continue
        gap = best_d - short - best.hit_radius
        if gap <= 1e-6:
            continue
        step = min(gap, speed * dt)
        t["x"], t["y"], _, _ = move_hull(world, t["x"], t["y"], 0.0, 4, 4,
                                         (best.x - t["x"]) / best_d * step,
                                         (best.y - t["y"]) / best_d * step)


def _in_my_image(hero, t: dict, target, world, actors, effects, projectiles) -> list[str]:
    """Packmaster Ring (L), In my image: a turret fires a copy of the
    hero's own attack at `target` (IN_MY_IMAGE x; the shots are the hero's,
    so the gear's tricks ride on them) -- or beats, for the bard's lute."""
    from .combat import pulse, volley
    spec = hero.weapon.spec
    if spec.kind == "pulse":
        return pulse(hero, world, actors, effects, mult=config.IN_MY_IMAGE, origin=(t["x"], t["y"]))
    shell = spec.shell
    angle = math.atan2(target.y - t["y"], target.x - t["x"])
    before = len(projectiles)
    sounds = volley(hero, world, projectiles, effects, angle, max(1, spec.pellets),
                    spec.spread_deg, shell, spec.tags, shell.damage, mult=config.IN_MY_IMAGE,
                    origin=(t["x"], t["y"]), actors=actors)
    if shell.seek_turn > 0:
        for q in projectiles[before:]:              # (darts home on the turret's target)
            q.seek, q.seek_point = target, (target.x, target.y)
    return sounds


def image_bite(hero, damage: float) -> float:
    """Packmaster Ring (L), In my image: a wolf bites for the hero's
    attack's hit (one shot, or a beat) when that's more than its own."""
    if not (_pack(hero) and _has(hero, "pack_leader+L")):
        return damage
    spec = hero.weapon.spec
    own = spec.damage if spec.kind == "pulse" or spec.shell is None else spec.shell.damage
    return max(damage, own)


def _calcify(hero, t: dict, s: SpellState, effects, projectiles) -> None:
    """Calcify (Skull Sentry +6): a turret whose time ends (or that's
    replaced) bursts into CALCIFY[0] bone shards, all round."""
    n, damage = config.CALCIFY
    shell = config.SPELL_SHELLS["turret"]
    for k in range(n):
        shot = Projectile(t["x"], t["y"], k * math.tau / n, shell, owner=hero, damage=damage)
        shot.tags = s.spec.tags
        shot.summon = True
        projectiles.append(shot)
    effects.append(Effect("rune_burst", t["x"], t["y"], size=1.0))


_KINDS = {"orbit": _orbit, "aura": _aura, "nova": _nova, "wolf": _wolf, "rune": _rune,
          "flask": _flask, "cloud": _cloud, "totem": _totem, "wand": _wand, "turret": _turret,
          "chain": _chain}
