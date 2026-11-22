"""
ai/cavalry.py -- Paradise's boss, form 1: THE SERENE CAVALRY (M29.4,
design/OCEAN.md 6.1). Four radiant white knights on white horses riding as
one cavalry with ONE shared health bar.

The cavalry (Cavalry) is the boss the quest wakes and the game's boss bar
reads; it has no body of its own. Its four riders (Rider) are the bodies:
shots and blasts stop on them, and whatever hurts one hurts the cavalry.

ALWAYS RIDING (user): they gallop round you the whole fight -- a circle, a
figure-eight, crossing lanes (a new pattern every CAV_RIDE[3] s) round a
middle that follows their target -- slowed in a move but never stopped. A
rider that runs into you tramples you.

Signatures, one more each phase (four phases: 100-75-50-25%):
  1. FORMATION CHARGE: lanes of light mark where they'll ride, then all
     four charge through together -- a line, a wedge, or a cross from four
     sides. Read the lanes, roll through the gaps.
  2. LIGHT LANCES: each rider throws a lance that sticks in the marble as a
     pillar of light (ai/paradise.LightPillar); fences of light join them
     into a cage round you that stings and throws you back. Break a pillar
     to open it.
  3. THE HYMN: they gather close and sing: shielded (x CAV_HYMN[1] damage)
     and healing while together. Break the chord: hurt the lead singer
     (glowing) enough, or come close to a rider so it breaks off at you.
  4. THE FOUR WINDS: they throw a cage of lances round you, take the four
     corners, and the winds blow from each in turn, pushing you into the
     fences; stand in a calm spot.
Moves (all four, all phases): carousel (circling you, tightening, light
thrown inward; out through the gaps), hoof rings (rings of light from their
hooves as they gallop), halo rain (gold halos into marked circles),
trample (one breaks off along a shown line, then rejoins).

FORM 2 (M29.5): at 0 it doesn't fall -- it unveils (HORSEMEN_UNVEIL s) into
the Four Horsemen (ai/horsemen.py), each with its own health. It still
rides them; it runs War's strife and Death's dead rising for whoever has
those powers, passes a fallen Horseman's kit to the others, and its health
is theirs together: it falls when the last of them does.
"""

from __future__ import annotations

import math
import random

from .. import config
from ..entities.actor import Actor
from ..entities.effects import Effect
from ..specs import EnemySpec
from ..systems import combat, patterns
from .bosses import Boss

_TAU = math.tau


def _seg_dist(px, py, x0, y0, x1, y1) -> float:
    return patterns.point_segment_distance(px, py, x0, y0, x1, y1)


class Rider(Actor):
    """One of the cavalry's four riders: a body of its own on the shared
    health. The cavalry moves it."""

    faction = "enemy"
    boss = True                       # never sleeps; drawn wherever it is
    spawn_id = None
    level = 1
    damage_mult = 1.0
    haste = 0.0
    kind_key = "cavalry"              # (the bestiary: it's the cavalry)

    def __init__(self, core: "Cavalry", index: int, x: float, y: float) -> None:
        self.part_of = None
        super().__init__(1, config.CAV_HIT_RADIUS)
        self.part_of = core
        self.index = index
        self.espec = core.espec
        self.x, self.y = x, y
        self.half = config.CAV_HIT_RADIUS * config.TILE_PX_W * 0.5
        self.facing = 0.0
        self.vx = self.vy = 0.0
        self.speed = 0.0              # tiles/s just now (its gallop, drawing)
        self.walked = 0.0
        self.ctrl: tuple | None = None   # a move's (x, y, speed) for it; None: the ride
        self.lead = False             # the hymn's lead singer
        self.sung = 0.0               # what it took while leading the hymn
        self.thrown = 0.0             # s thrown out of the hymn
        self.gone = False             # (M29.5: it unveiled into a Horseman)

    # Its health is the cavalry's.
    @property
    def hp(self) -> float:
        return self.part_of.hp if self.part_of is not None else self._hp

    @hp.setter
    def hp(self, value: float) -> None:
        self._hp = value              # (its own is never used)

    @property
    def max_hp(self):
        return self.part_of.max_hp if self.part_of is not None else self._max

    @max_hp.setter
    def max_hp(self, value) -> None:
        self._max = value

    @property
    def alive(self) -> bool:
        return self.part_of.alive and not self.gone

    @property
    def hittable(self) -> bool:
        return self.alive and self.part_of.form == 1    # (not while it unveils)

    def take_damage(self, amount, source, from_angle):
        if self.status is not None:
            amount *= self.status.vulnerability
        dealt = self.part_of.hurt(amount, source, from_angle, self)
        if dealt > 0:
            self.hurt_flash = 0.12
        return dealt

    def heal(self, amount: float) -> float:
        return 0.0

    def think(self, ctx, dt: float) -> None:
        pass                          # the cavalry rides it

    def hear(self, x: float, y: float) -> None:
        pass

    def scale_to_level(self, level: int) -> None:
        pass

    def facing_left(self) -> bool:
        return math.cos(self.facing) < 0


class Cavalry(Boss):
    """The Serene Cavalry (see the module's docstring)."""

    def __init__(self, spec: EnemySpec, x: float, y: float, rng: random.Random,
                 spawn_id=None) -> None:
        self.form = 1                     # 1, "unveiling", 2: the Four Horsemen (M29.5)
        self.horsemen: list = []
        super().__init__(spec, x, y, rng, spawn_id, hit_radius=config.CAV_HIT_RADIUS)
        self.shots = config.CAV_SHOTS
        self.riders = [Rider(self, i, x + math.cos(i * _TAU / 4) * 4,
                             y + math.sin(i * _TAU / 4) * 3) for i in range(4)]
        self.parts = self.riders          # (the quest puts them with the enemies)
        self.mid = (x, y)                 # the middle of the ride
        self.pattern = "circle"
        self.pattern_t = 0.0
        self.ride_t = 0.0
        self.slow = 1.0                   # x the ride's speed (a move slows it)
        self.trampled: dict = {}          # (rider, hero) -> clock of its last trample
        # What the moves show (render/cavalry.py):
        self.lanes: list = []             # formation: [x0, y0, x1, y1] each rider's lane
        self.charging = False
        self.line: tuple | None = None    # trample: (x0, y0, x1, y1)
        self.ring: tuple | None = None    # carousel: (x, y, radius)
        self.marks: list = []             # halo rain: [x, y, radius]
        self.lances: list = []            # in the air: [x0, y0, x1, y1, s, of s]
        self.cages: list = []             # [{"pillars": [...], "stung": {}}]
        self.hymn: dict | None = None     # {"lead": rider, "together": bool}
        self.winds: dict | None = None    # {"corners", "calm", "gust", "next"}
        self.bar_label = spec.name
        # M29.5: form 2.
        self.unveil_t = 0.0               # s of the unveiling left
        self.inherited: list[str] = []    # the fallen Horsemen's kits (the others have them)
        self.players_n = 1
        self.banner_req: tuple | None = None   # (title, sub): the quest shows it
        self.strife_t = config.STRIFE[0] * 0.5
        self.watch: dict = {}             # the dead rising: id -> (enemy, x, y) in the court

    # --- Being the cavalry ----------------------------------------------------------

    # Its health: its own while it's the cavalry; then the four Horsemen's
    # together (it falls when they all have).
    @property
    def hp(self) -> float:
        if getattr(self, "form", 1) == 2:
            return sum(max(0.0, h.hp) for h in self.horsemen)
        return self._hp

    @hp.setter
    def hp(self, value: float) -> None:
        if getattr(self, "form", 1) != 2:
            self._hp = value

    @property
    def max_hp(self):
        if getattr(self, "form", 1) == 2:
            return sum(h.max_hp for h in self.horsemen)
        return self._max

    @max_hp.setter
    def max_hp(self, value) -> None:
        if getattr(self, "form", 1) != 2:
            self._max = value

    @property
    def hittable(self) -> bool:
        return False                      # (only its riders are)

    def hurt(self, amount: float, source, from_angle, rider: Rider) -> float:
        """A rider was hit: the cavalry takes it (less while the hymn's
        chord holds). At 0 it doesn't fall: it unveils (M29.5)."""
        if self.form != 1:
            return 0.0
        if self.hymn is not None and self.hymn["together"]:
            amount *= config.CAV_HYMN[1]
        dealt = super().take_damage(amount, source, from_angle)
        if self.hymn is not None and rider.lead:
            rider.sung += dealt
        if self._hp <= 0:
            self._hp = 1.0
            self._unveil()
        return dealt

    @property
    def defeat_title(self) -> str:
        return "THE FOUR HORSEMEN ARE DEFEATED" if self.form == 2 else \
            "THE SERENE CAVALRY IS DEFEATED"

    def bars(self) -> list | None:
        """The boss bar's parts: each Horseman's health (form 2)."""
        if self.form != 2:
            return None
        return [(h.espec.name, h.frac if h.alive else 0.0) for h in self.horsemen]

    def take_damage(self, amount, source, from_angle):
        """Hurt as such (a retaliation...): the rider nearest the source
        takes it."""
        ref = source if source is not None else self
        r = min(self.riders, key=lambda q: (q.x - ref.x) ** 2 + (q.y - ref.y) ** 2)
        return r.take_damage(amount, source, from_angle)

    def scale_for(self, players: int) -> None:
        super().scale_for(players)
        self.players_n = players

    def shove_heroes(self, extra: float = 0.3) -> None:
        pass                              # (the riders trample instead: _gallop)

    def on_phase(self, phase: int, ctx) -> None:
        label = {1: "THE RIDERS RAISE THEIR LANCES", 2: "THE RIDERS BEGIN TO SING",
                 3: "THE FOUR WINDS RISE"}.get(phase)
        if label:
            ctx.effects.append(Effect("toast", self.x, self.y - 3, label=label))

    def _others(self) -> list:
        """Who its blasts can hurt: everyone but its own riders."""
        return [a for a in self.ctx.actors if getattr(a, "part_of", None) is not self]

    def think(self, ctx, dt: float) -> None:
        self.ctx = ctx
        if self.form == 1:
            self._ride(dt)
            super().think(ctx, dt)
            self._gallop(ctx)
        else:
            self.dt = dt
            self.time += dt
            if self.form == "unveiling":
                self.unveil_t -= dt
                self.slow = 0.3
                self._ride(dt)
                if self.unveil_t <= 0:
                    self._become_horsemen(ctx)
            else:
                self.riders = [h for h in self.horsemen if h.alive]
                if not self.riders:
                    return
                self.slow = 1.0
                self._ride(dt)
                self._gallop(ctx)
                self._strife(ctx, dt)
                self._risen(ctx)
        self._fly_lances(dt)
        self._fences(ctx, dt)
        n = len(self.riders)
        if n:
            self.x = sum(r.x for r in self.riders) / n
            self.y = sum(r.y for r in self.riders) / n

    # --- Form 2: the Four Horsemen (M29.5, ai/horsemen.py) ------------------------

    def _unveil(self) -> None:
        """Its health is gone: the cavalry unveils (HORSEMEN_UNVEIL s, its
        riders flickering), whatever it was doing."""
        self.form = "unveiling"
        self.unveil_t = config.HORSEMEN_UNVEIL
        self._gen = None
        self.move = None
        self.tell = None
        self.lanes, self.line, self.ring, self.marks = [], None, None, []
        self.charging = False
        self.hymn = self.winds = None
        for r in self.riders:
            r.ctrl, r.lead, r.thrown = None, False, 0.0
        self._clear_cages()
        self.banner_req = ("THE FOUR HORSEMEN", "the cavalry unveils")
        if self.ctx is not None:
            for r in self.riders:
                self.ctx.effects.append(Effect("unveil", r.x, r.y, size=2.5))
            self.ctx.events.append("hex")

    def _clear_cages(self) -> None:
        for c in self.cages:
            for p in c["pillars"]:
                if p.alive:
                    p.hp = 0.0
                    p.last_hit_by = None
        self.cages = []
        self.lances = []

    def _become_horsemen(self, ctx) -> None:
        from . import make_enemy
        from .horsemen import ORDER
        for r, key in zip(self.riders, ORDER):
            h = self.recruit(key, r.x, r.y) if self.recruit is not None else None
            if h is None:
                h = make_enemy(key, r.x, r.y, random.Random(self.rng.random()))
                h.scale_to_level(self.level)
                ctx.spawned.append(h)
            h.scale_for(self.players_n)
            h.cavalry = self
            h.lair = self.lair
            h.recruit = self.recruit
            h.facing = r.facing
            h.alert = True
            self.horsemen.append(h)
            r.gone = True
            ctx.effects.append(Effect("gore", r.x, r.y, size=2.0))
        self.riders = list(self.horsemen)
        self.form = 2
        self.bar_label = "The Four Horsemen"
        ctx.events.append(combat.BREAK)

    def fallen(self, h, ctx) -> None:
        """A Horseman fell: its kit passes to the others; with the dead
        rising, it rises as a pale rider for SHADE_LIFE s."""
        self.inherited.append(h.kit)
        alive = [o for o in self.horsemen if o.alive and o is not h]
        if not alive:
            return
        ctx.effects.append(Effect("toast", h.x, h.y - 3,
                                  label=f"{h.espec.name.upper()} FALLS - ITS POWER PASSES ON"))
        for o in alive:
            ctx.effects.append(Effect("unveil", o.x, o.y, size=2.0))
        if any(o.has("risen") for o in alive):
            ctx.spawned.append(("pale_rider", h.x, h.y))

    def _strife(self, ctx, dt: float) -> None:
        """War's strife (and whoever has it now): waves of unveiled angels
        into the court."""
        if not any(h.has("strife") for h in self.riders) or self.recruit is None:
            return
        self.strife_t -= dt
        if self.strife_t > 0:
            return
        self.strife_t = config.STRIFE[0]
        t = self.drift_target()
        if t is None:
            return
        about = sum(1 for e in ctx.actors if getattr(e, "strife", False) and e.alive)
        for k in range(min(config.STRIFE[1], config.STRIFE[2] - about)):
            a = self.rng.uniform(0, _TAU)
            x, y = self.clamp_to_lair(t.x + math.cos(a) * 14, t.y + math.sin(a) * 10, 3.0)
            e = self.recruit(self.rng.choice(config.SEVEN_SEAL_ANGELS), x, y)
            if e is not None:
                e.alert = True
                e.strife = True
                if hasattr(e, "unveil"):
                    e.unveil()
                ctx.effects.append(Effect("unveil", x, y, size=1.5))
        ctx.events.append("hex")

    def _risen(self, ctx) -> None:
        """Death's power (and whoever has it now): anything slain in the
        court rises once as a pale shade."""
        if not any(h.has("risen") for h in self.riders):
            self.watch.clear()
            return
        from .horsemen import ConquestBanner, Horseman, PaleShade
        from .paradise import LightPillar
        skip = (Horseman, Rider, Cavalry, PaleShade, LightPillar, ConquestBanner)
        for e in ctx.actors:
            if getattr(e, "faction", "") != "enemy" or isinstance(e, skip) or not e.alive:
                continue
            if self.lair is None or self.lair.inside(e.x, e.y):
                self.watch[id(e)] = (e, e.x, e.y)
        up = sum(1 for e in ctx.actors if isinstance(e, PaleShade) and e.alive)
        for k, (e, x, y) in list(self.watch.items()):
            if e.alive:
                continue
            del self.watch[k]
            if e.last_hit_by is not None and up < config.SHADES_MOST:   # (slain, not faded)
                up += 1
                ctx.spawned.append(("pale_shade", x, y))
                ctx.effects.append(Effect("unveil", x, y, size=1.2))

    # --- Always riding --------------------------------------------------------------

    def _slot(self, i: int) -> tuple[float, float]:
        """Rider i's place in the ride now."""
        rx, ry = config.CAV_RIDE[4]
        t = self.ride_t
        mx, my = self.mid
        if self.pattern == "eight":
            f = t * 0.55 + i * _TAU / 4
            return mx + rx * math.sin(f), my + ry * math.sin(f) * math.cos(f) * 2.0
        if self.pattern == "lanes":
            a = (0.45 if i < 2 else -0.45)
            s = math.sin(t * 0.7 + (i % 2) * math.pi + (0.6 if i >= 2 else 0.0))
            return mx + math.cos(a) * rx * s, my + math.sin(a) * rx * s * 0.8
        f = t * 0.7 + i * _TAU / 4
        return mx + rx * math.cos(f), my + ry * math.sin(f)

    def _ride(self, dt: float) -> None:
        speed, _, follow, every, (rx, ry) = config.CAV_RIDE
        self.ride_t += dt
        self.pattern_t += dt
        if self.pattern_t >= every:
            self.pattern_t = 0.0
            self.pattern = self.rng.choice([p for p in ("circle", "eight", "lanes")
                                            if p != self.pattern])
        t = self.drift_target() if self.ctx is not None else None
        if t is not None:
            mx, my = self.mid
            dx, dy = t.x - mx, t.y - my
            d = math.hypot(dx, dy)
            if d > 0.1:
                step = min(d, follow * dt)
                mx, my = mx + dx / d * step, my + dy / d * step
            self.mid = self.clamp_to_lair(mx, my, max(rx, ry) + 3)
        for r in self.riders:
            if r.ctrl is not None:
                gx, gy, v = r.ctrl
            else:
                (gx, gy), v = self._slot(r.index), speed * self.slow
            self._steer(r, gx, gy, v, dt)

    def _steer(self, r: Rider, gx: float, gy: float, v: float, dt: float) -> None:
        dx, dy = gx - r.x, gy - r.y
        d = math.hypot(dx, dy)
        step = min(d, v * dt)
        if d > 1e-6:
            r.x, r.y = r.x + dx / d * step, r.y + dy / d * step
            r.x, r.y = self.clamp_to_lair(r.x, r.y, 1.5)
            if step > 1e-4:
                r.facing = math.atan2(dy, dx)
        r.speed = step / dt if dt > 0 else 0.0
        r.vx, r.vy = math.cos(r.facing) * r.speed, math.sin(r.facing) * r.speed
        r.walked += step

    def _gallop(self, ctx) -> None:
        """A rider running into a hero tramples it (CAV_GALLOP)."""
        damage, push, every = config.CAV_GALLOP
        for r in self.riders:
            for h in ctx.players:
                if not h.alive or combat.drafting(h):
                    continue
                dx, dy = h.x - r.x, h.y - r.y
                d = math.hypot(dx, dy)
                room = r.hit_radius + h.hit_radius
                if d >= room:
                    continue
                key = (r.index, id(h))
                if self.time - self.trampled.get(key, -99.0) >= every:
                    self.trampled[key] = self.time
                    combat.strike(h, damage * self.damage_mult, self, r.facing, ctx.effects)
                if d < 1e-6:
                    dx, dy, d = math.cos(r.facing + math.pi / 2), math.sin(r.facing + math.pi / 2), 1.0
                combat.push(h, ctx.world, dx / d * (room - d + push * 0.3),
                            dy / d * (room - d + push * 0.3), full=True)

    def _hit_line(self, r: Rider, hit: set, damage: float, push: float) -> None:
        """A charging rider runs through whoever's on its way (once each)."""
        for h in self.ctx.players:
            if not h.alive or id(h) in hit or combat.drafting(h):
                continue
            if math.hypot(h.x - r.x, h.y - r.y) <= r.hit_radius + h.hit_radius + 0.3:
                hit.add(id(h))
                combat.strike(h, damage * self.damage_mult, self, r.facing, self.ctx.effects)
                side = r.facing + (math.pi / 2 if math.sin(math.atan2(h.y - r.y, h.x - r.x)
                                                           - r.facing) > 0 else -math.pi / 2)
                combat.push(h, self.ctx.world, math.cos(side) * push, math.sin(side) * push)

    # --- Signature 1: the formation charge -----------------------------------------

    def m_formation(self):
        show, speed, length, gap, damage, push = config.CAV_FORMATION
        t = self.target_now()
        if t is None:
            return
        shape = self.rng.choice(("line", "wedge", "cross"))
        a = math.atan2(t.y - self.mid[1], t.x - self.mid[0]) + self.rng.uniform(-0.4, 0.4)
        lanes = []
        for i in range(4):
            if shape == "cross":
                b = a + i * _TAU / 4
                off = gap * 0.55
            else:
                b = a
                off = (i - 1.5) * gap
            ux, uy = math.cos(b), math.sin(b)
            px, py = -uy, ux
            back = length / 2 + (abs(i - 1.5) * gap * 0.9 if shape == "wedge" else 0.0)
            x0, y0 = t.x - ux * back + px * off, t.y - uy * back + py * off
            x1, y1 = x0 + ux * length, y0 + uy * length
            x0, y0 = self.clamp_to_lair(x0, y0, 2.0)
            x1, y1 = self.clamp_to_lair(x1, y1, 2.0)
            lanes.append([x0, y0, x1, y1])
        self.lanes = lanes
        self.tell = ("formation", shape)
        for r, (x0, y0, _, _) in zip(self.riders, lanes):
            r.ctrl = (x0, y0, speed * 1.8)               # (to its lane's start, fast)
        yield self.tell_s(show)
        self.charging = True
        self.ctx.events.append("boulder")
        hits = [set() for _ in self.riders]
        for r, lane in zip(self.riders, lanes):
            r.x, r.y = lane[0], lane[1]                    # (the lanes shown are the truth)
            r.facing = math.atan2(lane[3] - lane[1], lane[2] - lane[0])
            r.ctrl = (lane[2], lane[3], speed)
        t0 = self.time
        while any(math.hypot(r.x - lane[2], r.y - lane[3]) > 0.6
                  for r, lane in zip(self.riders, lanes)) \
                and self.time - t0 < length / speed + 1.0:
            for r, lane, hit in zip(self.riders, lanes, hits):
                r.ctrl = (lane[2], lane[3], speed)
                self._hit_line(r, hit, damage, push)
            yield 0
        self.charging = False
        self.lanes = []
        for r in self.riders:
            r.ctrl = None
        yield 0.3

    # --- Signature 2: light lances --------------------------------------------------

    def _throw_cage(self, cx: float, cy: float, hw: float, hh: float) -> None:
        corners = [(cx - hw, cy - hh), (cx + hw, cy - hh), (cx + hw, cy + hh), (cx - hw, cy + hh)]
        corners = [self.clamp_to_lair(x, y, 2.0) for x, y in corners]
        air = config.CAV_LANCES[0]
        for r, (x, y) in zip(self.riders, corners):
            self.lances.append([r.x, r.y, x, y, 0.0, air])
        self.ctx.events.append("bow")

    def _fly_lances(self, dt: float) -> None:
        landed = []
        for b in self.lances:
            b[4] += dt
            if b[4] >= b[5]:
                landed.append((b[2], b[3]))
        self.lances = [b for b in self.lances if b[4] < b[5]]
        if not landed:
            return
        pillars = []
        for x, y in landed:
            p = self.recruit("light_pillar", x, y) if self.recruit is not None else None
            if p is None:
                from . import make_enemy
                p = make_enemy("light_pillar", x, y, random.Random(self.rng.random()))
                self.ctx.spawned.append(p)
            p.alert = True
            pillars.append(p)
            self.ctx.effects.append(Effect("unveil", x, y, size=1.2))
        self.cages.append({"pillars": pillars, "stung": {}})

    def fences(self) -> list[tuple[float, float, float, float]]:
        """The fences of light now: between each cage's neighbouring
        pillars while both stand."""
        out = []
        for c in self.cages:
            ps = c["pillars"]
            for a, b in zip(ps, ps[1:] + ps[:1]):
                if a is not b and a.alive and b.alive:
                    out.append((a.x, a.y, b.x, b.y))
        return out

    def _fences(self, ctx, dt: float) -> None:
        """Fences sting whoever touches them and throw them back the way
        they came (into the cage, or out of it)."""
        _, _, _, _, sting, every, push = config.CAV_LANCES
        self.cages = [c for c in self.cages if any(p.alive for p in c["pillars"])]
        for c in self.cages:
            ps = c["pillars"]
            alive = [p for p in ps if p.alive]
            cx = sum(p.x for p in alive) / len(alive)
            cy = sum(p.y for p in alive) / len(alive)
            for a, b in zip(ps, ps[1:] + ps[:1]):
                if a is b or not (a.alive and b.alive):
                    continue
                sx, sy = b.x - a.x, b.y - a.y
                ln = math.hypot(sx, sy) or 1.0
                nx, ny = -sy / ln, sx / ln               # (a normal)
                if (cx - a.x) * nx + (cy - a.y) * ny < 0:
                    nx, ny = -nx, -ny                   # (pointing into the cage)
                for h in ctx.players:
                    if not h.alive:
                        continue
                    if _seg_dist(h.x, h.y, a.x, a.y, b.x, b.y) > 0.45 + h.hit_radius:
                        continue
                    side = 1.0 if (h.x - a.x) * nx + (h.y - a.y) * ny >= 0 else -1.0
                    combat.push(h, ctx.world, nx * side * push, ny * side * push, full=True)
                    if self.time - c["stung"].get(id(h), -99.0) >= every:
                        c["stung"][id(h)] = self.time
                        combat.strike(h, sting * self.damage_mult, self, None, ctx.effects)

    def m_lances(self):
        _, hw, hh = config.CAV_LANCES[:3]
        t = self.target_now()
        if t is None:
            return
        self.tell = ("lances",)
        self.slow = config.CAV_RIDE[1]
        self._throw_cage(t.x, t.y, hw, hh)
        yield config.CAV_LANCES[0] + 0.4
        self.slow = 1.0

    # --- Signature 3: the hymn ------------------------------------------------------

    def m_hymn(self):
        secs, _, heal, close, brk, pull, thrown = config.CAV_HYMN
        lead = self.rng.choice(self.riders)
        lead.lead, lead.sung = True, 0.0
        self.hymn = {"lead": lead, "together": False}
        self.tell = ("hymn",)
        self.ctx.events.append("chime")
        t0 = self.time
        broken = None
        gx, gy = self.mid
        while self.time - t0 < secs and broken is None:
            t = self.drift_target()
            if t is not None:                            # (they drift away from you)
                d = math.hypot(gx - t.x, gy - t.y) or 1.0
                gx, gy = self.clamp_to_lair(gx + (gx - t.x) / d * 1.5 * self.dt,
                                            gy + (gy - t.y) / d * 1.5 * self.dt, 6.0)
            for r in self.riders:
                if r.thrown > 0:
                    continue
                a = (self.time - t0) * 1.2 + r.index * _TAU / 4
                r.ctrl = (gx + math.cos(a) * 2.2, gy + math.sin(a) * 1.6, 9.0)
                near = min((h for h in self.ctx.players if h.alive),
                           key=lambda h: math.hypot(h.x - r.x, h.y - r.y), default=None)
                if near is not None and math.hypot(near.x - r.x, near.y - r.y) <= pull:
                    r.ctrl = (near.x, near.y, 14.0)     # (pulled away: it breaks off at you)
                    broken = "pulled"
            n = len(self.riders)
            mx = sum(r.x for r in self.riders) / n
            my = sum(r.y for r in self.riders) / n
            together = all(math.hypot(r.x - mx, r.y - my) <= close for r in self.riders)
            self.hymn["together"] = together
            if together and not (self.status is not None and self.status.wounded):
                self.hp = min(float(self.max_hp), self.hp + self.max_hp * heal * self.dt)
            if lead.sung >= brk * self.max_hp:
                broken = "lead"
            yield 0
        if broken is not None:
            self.ctx.effects.append(Effect("toast", self.x, self.y - 3, label="THE CHORD BREAKS!"))
            self.ctx.events.append("hex")
            if broken == "lead":
                a = self.rng.uniform(0, _TAU)
                lead.ctrl = (lead.x + math.cos(a) * 12, lead.y + math.sin(a) * 8, 12.0)
                lead.thrown = thrown
        self.hymn = None
        lead.lead = False
        t1 = self.time
        while lead.thrown > 0 and self.time - t1 < thrown:
            lead.thrown -= self.dt
            yield 0
        lead.thrown = 0.0
        for r in self.riders:
            r.ctrl = None
        yield 0.2

    # --- Signature 4: the four winds ------------------------------------------------

    def m_winds(self):
        gusts, each, ahead, push, calm_n, calm_r, (cx, cy) = config.CAV_WINDS
        _, hw, hh = config.CAV_LANCES[:3]
        t = self.target_now()
        if t is None:
            return
        ox, oy = t.x, t.y
        self.tell = ("winds",)
        self._throw_cage(ox, oy, hw, hh)
        corners = [(ox - cx, oy - cy), (ox + cx, oy - cy), (ox + cx, oy + cy), (ox - cx, oy + cy)]
        corners = [self.clamp_to_lair(x, y, 2.0) for x, y in corners]
        calm = []
        for _ in range(calm_n):
            calm.append((ox + self.rng.uniform(-hw * 0.6, hw * 0.6),
                         oy + self.rng.uniform(-hh * 0.6, hh * 0.6)))
        self.winds = {"corners": corners, "calm": calm, "gust": None, "next": None,
                      "centre": (ox, oy)}
        k = self.rng.randrange(4)
        t0 = self.time
        while self.time - t0 < config.CAV_LANCES[0] + 0.2:
            self._hold_corners(corners)
            yield 0
        for g in range(gusts):
            corner = (k + g) % 4
            self.winds["next"] = corner
            t1 = self.time
            while self.time - t1 < self.tell_s(ahead):
                self._hold_corners(corners)
                yield 0
            self.winds["next"] = None
            self.winds["gust"] = corner
            self.ctx.events.append("orb")
            wx, wy = corners[corner]
            t1 = self.time
            while self.time - t1 < each:
                self._hold_corners(corners)
                for h in self.ctx.players:
                    if not h.alive or not self.in_arena(h):
                        continue
                    if any(math.hypot(h.x - x, h.y - y) <= calm_r for x, y in calm):
                        continue                         # (a calm spot)
                    dx, dy = ox - wx, oy - wy
                    d = math.hypot(dx, dy) or 1.0
                    combat.push(h, self.ctx.world, dx / d * push * self.dt,
                                dy / d * push * self.dt)
                yield 0
            self.winds["gust"] = None
        self.winds = None
        for r in self.riders:
            r.ctrl = None
        yield 0.3

    def _hold_corners(self, corners) -> None:
        for r, (x, y) in zip(self.riders, corners):
            a = self.time * 2.5 + r.index
            r.ctrl = (x + math.cos(a) * 1.5, y + math.sin(a) * 1.0, 10.0)

    # --- Moves ------------------------------------------------------------------------

    def m_carousel(self):
        secs, r0, r1, every = config.CAV_CAROUSEL
        t = self.target_now()
        if t is None:
            return
        cx, cy = t.x, t.y
        self.tell = ("carousel",)
        t0 = self.time
        next_shot = [self.time + every * (i / 4) for i in range(4)]
        shell = self.shots["light"]
        while self.time - t0 < secs:
            f = (self.time - t0) / secs
            r = r0 + (r1 - r0) * f
            self.ring = (cx, cy, r)
            for rd in self.riders:
                a = (self.time - t0) * 1.4 + rd.index * _TAU / 4
                rd.ctrl = (cx + math.cos(a) * r, cy + math.sin(a) * r, 28.0)
                if self.time >= next_shot[rd.index] and self.room_for_shots():
                    next_shot[rd.index] = self.time + every
                    aim = math.atan2(cy - rd.y, cx - rd.x)
                    patterns.shoot(self, rd.x, rd.y, aim, shell, self.ctx.projectiles)
            yield 0
        self.ring = None
        for rd in self.riders:
            rd.ctrl = None
        self.ctx.events.append("orb")
        yield 0.2

    def m_hoofs(self):
        secs, every, n = config.CAV_HOOFS
        self.tell = ("hoofs",)
        shell = self.shots["hoof"]
        t0 = self.time
        nxt = self.time
        while self.time - t0 < secs:
            if self.time >= nxt:
                nxt = self.time + every
                for r in self.riders:
                    if self.room_for_shots():
                        patterns.radial(self, r.x, r.y, n, shell, self.ctx.projectiles,
                                        turn=self.rng.uniform(0, _TAU / n))
                self.ctx.events.append("orb")
            yield 0
        yield 0.2

    def m_halos(self):
        marked, n, rad, volleys, gap, damage = config.CAV_HALOS
        for _ in range(volleys):
            t = self.target_now()
            if t is None:
                return
            marks = [[t.x, t.y, rad]]
            for _ in range(n - 1):
                a, d = self.rng.uniform(0, _TAU), self.rng.uniform(2.5, 7.0)
                marks.append([t.x + math.cos(a) * d, t.y + math.sin(a) * d * 0.8, rad])
            self.marks = marks
            self.tell = ("halos",)
            self.slow = config.CAV_RIDE[1]
            yield self.tell_s(marked)
            others = self._others()
            for x, y, r in marks:
                combat.blast(x, y, r, damage * self.damage_mult, self, others,
                             effects=self.ctx.effects)
                self.ctx.effects.append(Effect("unveil", x, y, size=r))
            self.ctx.events.append(combat.BREAK)
            self.marks = []
            self.slow = 1.0
            yield gap

    def m_trample(self):
        show, speed, length, damage, push = config.CAV_TRAMPLE
        t = self.target_now()
        if t is None:
            return
        r = min(self.riders, key=lambda q: math.hypot(q.x - t.x, q.y - t.y))
        a = math.atan2(t.y - r.y, t.x - r.x)
        x1, y1 = self.clamp_to_lair(r.x + math.cos(a) * length, r.y + math.sin(a) * length, 2.0)
        self.line = (r.x, r.y, x1, y1)
        self.tell = ("trample",)
        t0 = self.time
        while self.time - t0 < self.tell_s(show):
            r.ctrl = (self.line[0], self.line[1], 3.0)   # (it wheels round on the spot)
            r.facing = a
            yield 0
        hit: set = set()
        self.ctx.events.append("boulder")
        t0 = self.time
        while math.hypot(r.x - x1, r.y - y1) > 0.6 and self.time - t0 < length / speed + 1.0:
            r.ctrl = (x1, y1, speed)
            self._hit_line(r, hit, damage, push)
            yield 0
        r.ctrl = None
        self.line = None
        yield 0.2

    def on_death(self, ctx) -> None:
        for r in self.riders:
            ctx.effects.append(Effect("explosion", r.x, r.y))
            ctx.effects.append(Effect("feathers", r.x, r.y, size=1.5))
        ctx.events.append(combat.BREAK)
        self._clear_cages()
        from .horsemen import ConquestBanner
        for e in ctx.actors:                       # (their banners fall with them)
            if isinstance(e, ConquestBanner) and e.alive:
                e.hp = 0.0
                e.last_hit_by = None
