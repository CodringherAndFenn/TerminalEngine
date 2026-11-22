"""
ai/horsemen.py -- Paradise's boss, form 2: THE FOUR HORSEMEN (M29.5,
design/OCEAN.md 6.2). At 0 the Serene Cavalry (ai/cavalry.py) unveils into
four Horsemen, each with its own health bar and kit. When one dies, the
others take its power -- its kit joins theirs -- so the last one standing
has all four. They're still always riding (the cavalry rides them); only
the banner and the duel plant them, with a clear tell.

  CONQUEST (the white horse, crowned, a bow)
    crowning arrows  a volley of gold arrows: a hit crowns you -- while
                     crowned you're "conquered" and deal half damage; a
                     roll knocks the crown off
    arrow fans       (passive) fans of arrows while it gallops
    banners          plants a banner: its ground burns heroes and keeps
                     spreading until the banner is broken
    victor's lap     a lap round you at full speed, volleys inward-ahead;
                     the safe lane is right behind it
  WAR (the red horse, a great sword)
    sweeping blade   wide crescent slashes, each sending a wave of blood on
    blood charge     along a shown line, turn, again (up to 3), leaving a
                     burning river of blood
    strife           (passive) calls unveiled angels into the court in waves
    duel ring        plants its sword; a ring of blood closes round you and
                     it: inside you both deal double damage, for HM_DUEL[2] s or
                     until you break out (it stings)
  FAMINE (the black horse, the scales)
    the scales       (passive) every few seconds it weighs you against
                     itself: whoever has more health, as a share of max,
                     loses some to the other
    hunger           (passive) within HUNGER tiles no healing works
    weights          heavy black weights, marked first, crush where they
                     land and stay as obstacles
    locust plague    locusts pour from its saddlebags
  DEATH (the pale horse, Hades following)
    Hades follows    (passive) a pool of darkness trails it and lingers:
                     inside you can't heal and are pulled to its middle
    a fourth of the earth  four quarters round you, one at a time darkened,
                     then struck
    reaping          wide spinning scythe arcs as it rides
    the dead rise    (passive) anything slain in the court rises once as a
                     pale shade for SHADE_LIFE s -- a fallen Horseman too

The cavalry keeps the fight's own business (the riding, strife and the
dead rising, the inheritance); each Horseman runs its moves like any boss
(ai/bosses.Boss), picking among its own kit's and its fallen brothers'.
"""

from __future__ import annotations

import math
import random

from .. import config
from ..entities.effects import Effect
from ..systems import combat, patterns
from ..systems.zones import Zone
from ..world import tiles
from .bosses import Boss
from .brain import AIContext
from .paradise import _wrap
from .plains import Chaser, PlainsCreature

_TAU = math.tau

KITS = {
    "conquest": {"moves": ("crown", "banner", "lap"), "passives": ("fans",)},
    "war": {"moves": ("sweep", "bloodcharge", "duel"), "passives": ("strife",)},
    "famine": {"moves": ("weights", "locusts"), "passives": ("scales", "hunger")},
    "death": {"moves": ("quarter", "reap"), "passives": ("hades", "risen")},
}
ORDER = ("conquest", "war", "famine", "death")


def crown(victim, source) -> None:
    """A crowning arrow hit `victim`: crowned (half damage) until a roll."""
    if getattr(victim, "faction", "") != "player" or not victim.alive:
        return
    if not getattr(victim, "crowned", False):
        victim.crowned = True
        if source is not None and getattr(source, "ctx", None) is not None:
            source.ctx.effects.append(Effect("toast", victim.x, victim.y - 2, label="CROWNED!"))


class Horseman(Boss):
    """One of the Four Horsemen (see the module's docstring). `kit` is its
    own (its spec's kind); `kits` its own and those it has inherited."""

    def __init__(self, spec, x: float, y: float, rng: random.Random, spawn_id=None) -> None:
        super().__init__(spec, x, y, rng, spawn_id, hit_radius=config.HORSEMEN[0])
        self.kit = spec.kind
        self.cavalry = None               # the cavalry it unveiled from (it rides it)
        self.index = ORDER.index(self.kit)
        self.shots = config.HORSEMEN_SHOTS
        self.ctrl: tuple | None = None    # a move's (x, y, speed); None: the ride
        self.speed = 0.0
        self.vx = self.vy = 0.0
        self.planted = False              # (the banner, the duel: it stops)
        self._rest = 1.0 + self.index * 0.6
        self.fans_t = self.rng.uniform(1.0, config.FANS[0])
        self.scales_t = config.SCALES[0]
        self.hades_t = 0.0
        # What its moves show (render/horsemen.py):
        self.aim_line: tuple | None = None    # (x0, y0, x1, y1): an arrow volley's, a charge's
        self.arc: tuple | None = None         # a slash: (angle, reach, half-angle)
        self.ring: tuple | None = None        # the duel: (x, y, radius, s of the tell left)
        self.duelist = None                   # the hero in its duel ring
        self.weights: list = []               # [x, y, s left] marked
        self.quarter: tuple | None = None     # (x, y, radius, quarter 0-3, s darkened left)
        self.scythe: float | None = None      # reaping: the scythe's angle
        self.weighed: tuple | None = None     # the scales just now: (hero, it lost, s shown)

    # --- Its kits ---------------------------------------------------------------------

    @property
    def kits(self) -> set[str]:
        c = self.cavalry
        return {self.kit} | (set(c.inherited) if c is not None else set())

    def has(self, passive: str) -> bool:
        return any(passive in KITS[k]["passives"] for k in self.kits)

    def _pick_move(self) -> str:
        moves = [m for k in sorted(self.kits) for m in KITS[k]["moves"]]
        pick = [m for m in moves if m != self.last_move] or moves
        own = set(KITS[self.kit]["moves"])
        weights = [2.0 if m in own else 1.2 for m in pick]
        return self.rng.choices(pick, weights)[0]

    def on_phase(self, phase: int, ctx) -> None:
        pass                              # (its brothers falling is what changes it)

    def facing_left(self) -> bool:
        return math.cos(self.facing) < 0

    def heroes_near(self, reach: float) -> list:
        return [h for h in self.ctx.players if h.alive
                and math.hypot(h.x - self.x, h.y - self.y) <= reach]

    def _others(self) -> list:
        """Who its blasts can hurt: everyone but the Horsemen."""
        return [a for a in self.ctx.actors if not isinstance(a, Horseman)]

    # --- Every step -------------------------------------------------------------------

    def think(self, ctx: AIContext, dt: float) -> None:
        self.ctx = ctx
        super().think(ctx, dt)
        self._passives(ctx, dt)

    def _passives(self, ctx: AIContext, dt: float) -> None:
        if self.has("fans") and not self.planted:
            self.fans_t -= dt
            if self.fans_t <= 0:
                self.fans_t = config.FANS[0]
                t = min(self.heroes_near(config.FANS[3]),
                        key=lambda h: math.hypot(h.x - self.x, h.y - self.y), default=None)
                if t is not None and self.room_for_shots():
                    patterns.fan(self, self.x, self.y, self.aim(t, self.x, self.y,
                                                                 self.shots["arrow"].speed),
                                 config.FANS[1], config.FANS[2], self.shots["arrow"],
                                 ctx.projectiles)
                    ctx.events.append("bow")
        if self.has("scales"):
            self.scales_t -= dt
            if self.scales_t <= 0:
                self.scales_t = config.SCALES[0]
                self._weigh(ctx)
        if self.weighed is not None:
            h, lost, left = self.weighed
            self.weighed = (h, lost, left - dt) if left > dt else None
        if self.has("hunger"):
            for h in self.heroes_near(config.HUNGER):
                h.starved_until = getattr(h, "time", 0.0) + 0.3
        if self.has("hades") and ctx.zones is not None:
            for z in ctx.zones:                        # (no healing in its darkness)
                if z.kind == "hades" and z.source is self:
                    for h in ctx.players:
                        if h.alive and math.hypot(h.x - z.x, h.y - z.y) <= z.radius + h.hit_radius:
                            h.starved_until = getattr(h, "time", 0.0) + 0.3
            self.hades_t -= dt
            if self.hades_t <= 0 and self.speed > 1.0:
                self.hades_t = config.HADES[0]
                radius, life, pull = config.HADES[1:]
                ctx.zones.append(Zone("hades", self.x - math.cos(self.facing) * 2.0,
                                      self.y - math.sin(self.facing) * 2.0, radius, life, 0.25,
                                      0.0, self, pull=pull))

    def _weigh(self, ctx: AIContext) -> None:
        """The scales: the target against itself, by share of max health;
        the one found wanting -- the lighter, less health as a share --
        loses SCALES[1] of its own max to the other (who gains just that).
        Keep it hurt (lighter than you) and you're safe. (OCEAN.md 6.2's
        "whoever has more health loses" contradicts its own "keep it hurt
        and you're safe"; this follows the second: see section 12.)"""
        t = min(self.heroes_near(config.SCALES[2]),
                key=lambda h: math.hypot(h.x - self.x, h.y - self.y), default=None)
        if t is None:
            return
        share = config.SCALES[1]
        mine, theirs = self.frac, t.hp / t.max_hp if t.max_hp else 0.0
        if theirs < mine:
            dealt = combat.strike(t, t.max_hp * share, self, None, ctx.effects)
            self.hp = min(float(self.max_hp), self.hp + dealt)      # (what you lost, it gains)
            self.weighed = (t, True, 1.2)
            if dealt > 0:
                ctx.effects.append(Effect("toast", t.x, t.y - 2, label="WEIGHED!"))
        else:
            lost = self.take_damage(self.max_hp * share, None, None)
            t.heal(lost)                                             # (what it lost, you gain:
            self.weighed = (t, False, 1.2)                           # unless it starves you)
            ctx.effects.append(Effect("toast", self.x, self.y - 3, label="FOUND WANTING!"))
        ctx.events.append("chime")

    # --- Conquest ---------------------------------------------------------------------

    def m_crown(self):
        tell, n, spread = config.CROWN[:3]
        t = self.target_now()
        if t is None:
            return
        shell = self.shots["crown"]
        a = self.aim(t, self.x, self.y, shell.speed)
        self.aim_line = (self.x, self.y, self.x + math.cos(a) * 18, self.y + math.sin(a) * 18)
        self.tell = ("crown",)
        yield self.tell_s(tell)
        self.aim_line = None
        a = self.aim(t, self.x, self.y, shell.speed)
        for k in range(n):
            off = (k - (n - 1) / 2) * math.radians(spread) / max(1, n - 1)
            p = patterns.shoot(self, self.x, self.y, a + off, shell, self.ctx.projectiles)
            p.on_hit = crown
        self.ctx.events.append("bow")
        yield 0.4

    def m_banner(self):
        tell = config.BANNER[0]
        t = self.target_now()
        if t is None:
            return
        a = self.rng.uniform(0, _TAU)
        x, y = self.clamp_to_lair(t.x + math.cos(a) * 6, t.y + math.sin(a) * 4, 4.0)
        t0 = self.time
        while math.hypot(self.x - x, self.y - y) > 1.5 and self.time - t0 < 3.0:
            self.ctrl = (x, y, config.CAV_RIDE[0] * 1.4)
            yield 0
        self.planted = True
        self.ctrl = (self.x, self.y, 0.0)
        self.tell = ("banner",)
        yield self.tell_s(tell)
        mine = [e for e in self.ctx.actors if isinstance(e, ConquestBanner) and e.alive]
        if len(mine) >= config.BANNER[6]:                 # (the oldest falls for the new one)
            mine[0].hp = 0.0
            mine[0].last_hit_by = None
        b = self.recruit("conquest_banner", self.x + 1.0, self.y) if self.recruit else None
        if b is not None:
            b.owner = self
            b.damage_mult = self.damage_mult
        self.ctx.events.append("boulder")
        self.planted = False
        self.ctrl = None
        yield 0.3

    def m_lap(self):
        secs, radius, speed, every, n = config.LAP
        t = self.target_now()
        if t is None:
            return
        cx, cy = t.x, t.y
        a0 = math.atan2(self.y - cy, self.x - cx)
        self.tell = ("lap",)
        t0 = self.time
        nxt = self.time + 0.4
        shell = self.shots["arrow"]
        way = self.rng.choice((-1.0, 1.0))
        while self.time - t0 < secs:
            a = a0 + way * (self.time - t0) * speed / radius
            self.ctrl = self.clamp_to_lair(cx + math.cos(a) * radius, cy + math.sin(a) * radius,
                                           2.0) + (speed * 1.3,)
            if self.time >= nxt and self.room_for_shots():
                nxt = self.time + every
                inward = math.atan2(cy - self.y, cx - self.x) + way * math.radians(25)
                patterns.fan(self, self.x, self.y, inward, n, 24.0, shell, self.ctx.projectiles)
            yield 0
        self.ctrl = None
        yield 0.3

    # --- War --------------------------------------------------------------------------

    def _slash(self, angle: float, reach: float, half: float, damage: float) -> None:
        for h in self.ctx.players:
            if not h.alive:
                continue
            d = math.hypot(h.x - self.x, h.y - self.y)
            if d > reach + h.hit_radius:
                continue
            if d > h.hit_radius and abs(_wrap(math.atan2(h.y - self.y, h.x - self.x) - angle)) > half:
                continue
            combat.strike(h, damage * self._duel_mult(h), self, angle, self.ctx.effects)
        self.ctx.effects.append(Effect("slash", self.x + math.cos(angle) * 1.5,
                                       self.y + math.sin(angle) * 1.5, angle))
        self.ctx.events.append(combat.HIT)

    def _duel_mult(self, h) -> float:
        return config.HM_DUEL[3] if self.duelist is h and getattr(h, "duel", None) is self else 1.0

    def m_sweep(self):
        tell, slashes, reach, arc, damage, wave_n = config.SWEEP
        shell = self.shots["wave"]
        for _ in range(slashes):
            t = self.target_now()
            if t is None:
                return
            a = math.atan2(t.y - self.y, t.x - self.x)
            self.arc = (a, reach, math.radians(arc) / 2)
            self.tell = ("sweep",)
            self.facing = a
            yield self.tell_s(tell)
            self._slash(a, reach, math.radians(arc) / 2, damage * self.damage_mult)
            if self.room_for_shots():                    # (the wave of blood rolling on)
                patterns.fan(self, self.x, self.y, a, wave_n, arc * 0.9, shell,
                             self.ctx.projectiles)
            self.arc = None
            yield 0.25

    def m_bloodcharge(self):
        tell, speed, length, turns, damage, push, every, life = config.BLOOD_CHARGE
        for _ in range(turns):
            t = self.target_now()
            if t is None:
                break
            a = math.atan2(t.y - self.y, t.x - self.x)
            x1, y1 = self.clamp_to_lair(self.x + math.cos(a) * length,
                                        self.y + math.sin(a) * length, 2.0)
            self.aim_line = (self.x, self.y, x1, y1)
            self.tell = ("bloodcharge",)
            self.ctrl = (self.x, self.y, 2.0)
            self.facing = a
            yield self.tell_s(tell)
            self.aim_line = None
            hit: set = set()
            drop = 0.0
            t0 = self.time
            self.ctx.events.append("boulder")
            while math.hypot(self.x - x1, self.y - y1) > 0.6 and self.time - t0 < length / speed + 1:
                self.ctrl = (x1, y1, speed)
                for h in self.ctx.players:
                    if h.alive and id(h) not in hit \
                            and math.hypot(h.x - self.x, h.y - self.y) <= self.hit_radius + h.hit_radius:
                        hit.add(id(h))
                        combat.strike(h, damage * self.damage_mult, self, a, self.ctx.effects)
                        combat.push(h, self.ctx.world, -math.sin(a) * push, math.cos(a) * push)
                drop -= self.dt
                if drop <= 0 and self.ctx.zones is not None:
                    drop = every
                    dmg, tick = config.FIRE_PATCH
                    self.ctx.zones.append(Zone("blood_fire", self.x, self.y, 1.0, life, tick,
                                               dmg * self.damage_mult, self))
                yield 0
            self.ctrl = None
            yield 0.2

    def m_duel(self):
        tell, radius, secs, _, sting, slash_every = config.HM_DUEL
        t = self.target_now()
        if t is None:
            return
        self.planted = True
        self.ctrl = (self.x, self.y, 0.0)
        cx, cy = (self.x + t.x) / 2, (self.y + t.y) / 2
        r = max(radius, math.hypot(t.x - self.x, t.y - self.y) / 2 + 2.5)
        self.ring = (cx, cy, r, self.tell_s(tell))
        self.tell = ("duel",)
        t0 = self.time
        while self.time - t0 < self.tell_s(tell):
            self.ring = (cx, cy, r, self.tell_s(tell) - (self.time - t0))
            yield 0
        self.ring = (cx, cy, r, 0.0)
        inside = math.hypot(t.x - cx, t.y - cy) <= r
        if inside:
            self.duelist, t.duel = t, self
            self.ctx.effects.append(Effect("toast", t.x, t.y - 2, label="DUEL!"))
        t0 = self.time
        nxt = self.time + 0.8
        while self.time - t0 < secs and self.duelist is not None and t.alive:
            if math.hypot(t.x - cx, t.y - cy) > r:          # (you broke out: it stings)
                combat.strike(t, sting * self.damage_mult, self, None, self.ctx.effects)
                self.ctx.effects.append(Effect("toast", t.x, t.y - 2, label="BROKE OUT!"))
                break
            if self.time >= nxt:
                nxt = self.time + slash_every
                a = math.atan2(t.y - self.y, t.x - self.x)
                self.arc = (a, config.SWEEP[2], math.radians(config.SWEEP[3]) / 2)
                yield self.tell_s(0.35)
                self._slash(a, config.SWEEP[2], math.radians(config.SWEEP[3]) / 2,
                            config.SWEEP[4] * self.damage_mult)
                self.arc = None
            yield 0
        self._end_duel(t)
        self.planted = False
        self.ctrl = None
        yield 0.3

    def _end_duel(self, t=None) -> None:
        for h in (t, self.duelist):
            if h is not None and getattr(h, "duel", None) is self:
                h.duel = None
        self.duelist = None
        self.ring = None

    # --- Famine -----------------------------------------------------------------------

    def m_weights(self):
        tell, n, spread, radius, damage = config.WEIGHTS
        t = self.target_now()
        if t is None:
            return
        marks = [[t.x, t.y]]
        for _ in range(n - 1):
            a, d = self.rng.uniform(0, _TAU), self.rng.uniform(2.0, spread)
            marks.append([t.x + math.cos(a) * d, t.y + math.sin(a) * d * 0.8])
        self.weights = marks
        self.tell = ("weights",)
        yield self.tell_s(tell)
        others = self._others()
        world = self.ctx.world
        for x, y in marks:
            combat.blast(x, y, radius, damage * self.damage_mult, self, others,
                         effects=self.ctx.effects)
            self.ctx.effects.append(Effect("debris", x, y))
            tx, ty = math.floor(x), math.floor(y)
            if hasattr(world, "set_tile") and not world.tile_at(tx, ty).solid:
                world.set_tile(tx, ty, tiles.WEIGHT)       # (it stays where it fell)
                for h in self.ctx.players:                  # (out from under it)
                    if math.floor(h.x) == tx and math.floor(h.y) == ty:
                        combat.push(h, world, 1.2, 0.0, full=True)
        self.ctx.events.append(combat.BREAK)
        self.weights = []
        yield 0.3

    def m_locusts(self):
        tell, n, most = config.HM_PLAGUE
        alive = sum(1 for e in self.ctx.actors if getattr(e, "kind_key", "") == "locust")
        if alive >= most or self.recruit is None:
            yield 0.2
            return
        self.tell = ("locusts",)
        yield self.tell_s(tell)
        for k in range(min(n, most - alive)):
            a = k * _TAU / n
            e = self.recruit("locust", self.x + math.cos(a) * 1.5, self.y + math.sin(a) * 1.0)
            if e is not None:
                e.state, e.alert = "unveiled", True
        self.ctx.effects.append(Effect("unveil", self.x, self.y, size=2.0))
        self.ctx.events.append("hex")
        yield 0.3

    # --- Death ------------------------------------------------------------------------

    def m_quarter(self):
        dark, radius, damage = config.QUARTER
        t = self.target_now()
        if t is None:
            return
        cx, cy = t.x, t.y
        order = list(range(4))
        self.rng.shuffle(order)
        self.tell = ("quarter",)
        for q in order:
            t0 = self.time
            span = self.tell_s(dark)
            while self.time - t0 < span:
                self.quarter = (cx, cy, radius, q, span - (self.time - t0))
                yield 0
            for h in self.ctx.players:                     # (struck: whoever's in it)
                if not h.alive:
                    continue
                d = math.hypot(h.x - cx, h.y - cy)
                if d > radius + h.hit_radius:
                    continue
                if _quarter_of(h.x - cx, h.y - cy) == q:
                    combat.strike(h, damage * self.damage_mult, self, None, self.ctx.effects)
            self.ctx.effects.append(Effect("quarter_wave", cx, cy, float(q), size=radius))
            self.ctx.events.append(combat.BREAK)
        self.quarter = None
        yield 0.3

    def m_reap(self):
        secs, spin, reach, damage, every, crescents = config.HM_REAP
        t0 = self.time
        self.scythe = self.facing
        last: dict = {}
        shell = self.shots["scythe"]
        turned = 0.0
        self.tell = ("reap",)
        while self.time - t0 < secs:
            self.scythe += spin * self.dt
            turned += spin * self.dt
            for h in self.ctx.players:
                if not h.alive:
                    continue
                d = math.hypot(h.x - self.x, h.y - self.y)
                if d > reach + h.hit_radius:
                    continue
                if abs(_wrap(math.atan2(h.y - self.y, h.x - self.x) - self.scythe)) > 0.45 \
                        and d > h.hit_radius:
                    continue
                if self.time - last.get(id(h), -99.0) >= every:
                    last[id(h)] = self.time
                    combat.strike(h, damage * self.damage_mult, self, self.scythe, self.ctx.effects)
            if turned >= math.pi:                          # (a crescent off each half-turn)
                turned -= math.pi
                if self.room_for_shots():
                    patterns.fan(self, self.x, self.y, self.scythe, crescents, 30.0, shell,
                                 self.ctx.projectiles)
            yield 0
        self.scythe = None
        yield 0.3

    def on_death(self, ctx) -> None:
        self._end_duel()
        ctx.effects.append(Effect("gore", self.x, self.y, size=2.0))
        ctx.effects.append(Effect("explosion", self.x, self.y))
        ctx.events.append(combat.BREAK)
        if self.cavalry is not None:
            self.cavalry.fallen(self, ctx)


def _quarter_of(dx: float, dy: float) -> int:
    """Which quarter round a point (dx, dy) is in: 0 east-south, 1
    south-west, 2 west-north, 3 north-east (by angle)."""
    return int(((math.atan2(dy, dx) % _TAU) / (_TAU / 4))) % 4


class ConquestBanner(PlainsCreature):
    """Conquest's banner (M29.5): planted, it claims a circle of ground
    that burns heroes (its damage every BANNER[4] s) and keeps spreading
    (from BANNER[1] at BANNER[2] tiles/s up to BANNER[3]) until it's
    broken."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.radius = config.BANNER[1]
        self.burn_t = 0.0
        self.owner = None
        self.facing = 0.0
        self.clock = 0.0

    def think(self, ctx: AIContext, dt: float) -> None:
        self._moved = 0.0
        self.clock += dt
        _, _, grow, most, every, damage = config.BANNER[:6]
        self.radius = min(most, self.radius + grow * dt)
        self.burn_t -= dt
        if self.burn_t > 0:
            return
        self.burn_t = every
        for h in ctx.players:
            if h.alive and math.hypot(h.x - self.x, h.y - self.y) <= self.radius + h.hit_radius \
                    and not combat.skims(h):
                combat.strike(h, damage * self.damage_mult, self.owner or self, None, ctx.effects)

    def facing_left(self) -> bool:
        return False

    def on_death(self, ctx: AIContext) -> None:
        ctx.effects.append(Effect("debris", self.x, self.y))
        ctx.events.append(combat.BREAK)


class PaleShade(Chaser):
    """The dead rising (M29.5, Death's power): a pale shade of something
    slain in the court, for SHADE_LIFE s; it can't rise again. A fallen
    Horseman's is a pale rider."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.life = config.SHADE_LIFE
        self.alert = True

    def can_see(self, world, other) -> bool:          # (it sees through everything)
        return math.hypot(other.x - self.x, other.y - self.y) <= self.espec.sight

    def think(self, ctx: AIContext, dt: float) -> None:
        self.life -= dt
        if self.life <= 0:
            self.hp = 0.0
            self.last_hit_by = None
            return
        super().think(ctx, dt)

    def on_death(self, ctx: AIContext) -> None:
        ctx.effects.append(Effect("feathers", self.x, self.y, size=1.2))
