"""
ai/fossil_angel.py -- THE FOSSIL ANGEL, the final of heaven and the past
(M33.1, design/FINALS.md 8-9): an angel that fell on the first day and has
lain in the rock ever since, a vast skeleton of stone feathers and bone in
amber. Form 1 here: ITS BONES WALK, wrapped in jungle and fire, under a
halo of lava. (Form 2, the first angel unveiling, is M33.2.)

It hunts you across the whole map like every final (ai/finals.Final: the
walk, the leap, its trail of cloud, marble, ash and ferns, the cherubs and
raptors crawling out of it). Its fight, four phases (100-75-50-25%), a
signature added in each:
  1 stone feathers  it beats its stone wings (the lines shown) and feathers
                    rain down along a fan of lines at you; they stick in
                    the ground as stone spikes for a while: cover for you,
                    walls it smashes through;
  2 the lava halo   its halo lifts off and rolls out as a burning wheel (a
                    LavaHalo, hittable) circling it at a growing radius and
                    leaving fire behind: slip through the gap, or hit the
                    wheel until it cools to stone and falls (a boulder);
  3 echoes          Pangaea's twist (ai/pangaea.Echoing): from here on its
                    attacks replay ECHO[0] s later from where it stood, at
                    full damage; it keeps walking, so each echo comes from a
                    spot it has already left;
  4 amber           it weeps resin that runs out in rivers (flowing, shown
                    as it comes) and hardens into amber walls; caught in
                    running resin you're held until you roll free.
Moves (it keeps walking through most of them): the wing sweep (a wide arc,
a wing raised first), the stone dive (its line shown, a hop, a dive along
it, a shower of stone where it lands), ash breath (a cone; embers keep
burning in it), falling stars (chains of marked circles round you).

Drawn by render/fossil_angel.py.
"""

from __future__ import annotations

import math
import random

from .. import config
from ..entities.actor import Actor
from ..entities.effects import Effect
from ..specs import EnemySpec
from ..systems import combat
from ..systems.collision import WATERY
from ..systems.zones import Zone
from ..world import tiles
from .bosses import Boss
from .finals import Final
from .pangaea import Echoing

_TAU = math.tau
PHASE_BANNERS = {
    1: ("ITS HALO KINDLES", "it rolls out as a burning wheel -- hit the wheel and it cools to stone"),
    2: ("IT REMEMBERS", "from now on, everything it does echoes"),
    3: ("IT WEEPS AMBER", "the resin holds you -- roll free"),
}
# Its own: what its trail and moves never stamp over, and what's left of it.
FIXTURES = frozenset((tiles.FEATHER_SPIKE, tiles.RESIN, tiles.AMBER_WALL))


class LavaHalo(Actor):
    """Its halo rolled out as a burning wheel (FOSSIL_HALO): a body you can
    hit (its own health, not the angel's), circling the angel at a growing
    radius. The angel moves it (FossilAngel._tick_halo); at 0 it cools to
    stone and falls. Gone at the end of its roll (`gone`), it isn't a kill."""

    faction = "enemy"
    boss = True                       # never sleeps; drawn wherever it is
    spawn_id = None
    level = 1
    damage_mult = 1.0
    haste = 0.0

    def __init__(self, angel: "FossilAngel", angle: float) -> None:
        h = config.FOSSIL_HALO
        spec = config.ENEMIES["lava_halo"]
        own = config.ENEMIES[angel.espec.kind].max_hp
        super().__init__(max(1, round(h[12] * angel.max_hp / own)), h[5])
        self.part_of = angel
        self.espec = spec
        self.angle = angle            # round the angel
        self.dir = angel.rng.choice((-1, 1))
        self.t = 0.0
        self.rolled = 0.0             # tiles rolled since the last fire
        self.hit_ids: set[int] = set()
        self.lap = 0
        self.gone = False
        self.facing = 0.0
        self.vx = self.vy = 0.0
        self.half = spec.size_px / 2
        self.radius_now = h[1]
        self.x = angel.x + math.cos(angle) * h[1]
        self.y = angel.y + math.sin(angle) * h[1] * 0.8

    def think(self, ctx, dt: float) -> None:
        pass                          # the angel rolls it

    def hear(self, x: float, y: float) -> None:
        pass


class FossilAngel(Echoing, Final):
    """The Fossil Angel, form 1 (see the module's docstring)."""

    GROUNDS = ((tiles.CLOUD, tiles.CLOUD_DRIFT, tiles.MARBLE_RUBBLE),     # heaven
               (tiles.ASH, tiles.BASALT, tiles.FERN_MEADOW))              # the past

    def __init__(self, spec: EnemySpec, x: float, y: float, rng: random.Random,
                 spawn_id=None) -> None:
        super().__init__(spec, x, y, rng, spawn_id, hit_radius=config.FOSSIL_HIT_RADIUS)
        self.init_echoes()
        self.pose = ""                    # "beat" (wings up), "crouch", "breath", "weep", "halo"
        self.planted = False
        # What it's showing before a move (render/fossil_angel.py):
        self.lines: list[tuple] = []      # feathers' lines: (x0, y0, angle, length, half)
        self.cone: tuple | None = None    # the sweep's, the breath's: (x, y, angle, reach, half)
        self.line: tuple | None = None    # the dive's: (x0, y0, angle, length, half)
        self.wheel: LavaHalo | None = None
        self.halo_lost = 0.0              # s until a cooled halo has grown back
        self.spikes: list[list] = []      # [tx, ty, the tile it stuck in, s left]
        self.rivers: list[dict] = []      # resin running out
        self.resin: dict = {}             # (tx, ty) -> [s until it hardens, the tile it ran over]
        self.walls: list[list] = []       # [tx, ty, the tile under it, s left]
        self.held: dict = {}              # id(hero) -> [hero, s left] (caught in running resin)
        self.banner_req: tuple | None = None

    # --- Being the Fossil Angel ----------------------------------------------------------

    @property
    def bar_label(self) -> str:
        return "The Fossil Angel -- its bones walk"

    @property
    def has_halo(self) -> bool:
        return self.wheel is None and self.halo_lost <= 0

    def victims(self, ctx) -> list:
        return Final.victims(self, ctx)

    def sprite_now(self) -> str:
        return "fossil_angel_beat" if self.pose in ("beat", "halo", "weep") else "fossil_angel"

    def hurt(self, base: float) -> float:
        return base * self.damage_mult

    def planted_now(self) -> bool:
        return self.planted

    @property
    def echoing(self) -> bool:
        """Its third signature: its attacks echo from this phase on."""
        return self.phase >= config.FOSSIL_ECHO_PHASE

    def _record(self, kind: str, tell, data: dict) -> None:
        if self.echoing:
            super()._record(kind, tell, data)

    # --- Its turn ----------------------------------------------------------------------

    def think(self, ctx, dt: float) -> None:
        self.ctx = ctx
        self.play_echoes(ctx, dt)
        self._tick_halo(ctx, dt)
        self._tick_spikes(ctx, dt)
        self._tick_amber(ctx, dt)
        Final.think(self, ctx, dt)

    def clear_tells(self) -> None:
        self.planted = False
        self.pose = ""
        self.lines, self.cone, self.line = [], None, None
        if self.leap is None:
            self.airborne = 0.0

    def on_leap(self) -> None:
        """Off it goes: its wheel rolls back up, its resin stops running."""
        if self.wheel is not None and self.wheel.alive:
            self.wheel.gone = True
            self.wheel.hp = 0.0
        self.wheel = None
        self.rivers = []

    def _start(self, name: str) -> None:
        self.clear_tells()
        Boss._start(self, name)

    def _end_move(self) -> None:
        self.clear_tells()
        Boss._end_move(self)

    def on_phase(self, phase: int, ctx) -> None:
        req = PHASE_BANNERS.get(phase)
        if req is not None:
            self.banner_req = req
        ctx.effects.append(Effect("toast", self.x, self.y - self.hit_radius - 2,
                                  label=req[0] + "!" if req else "IT GROWS ANGRY!"))
        ctx.events.append("boulder")

    def _hold(self, secs: float, each=None):
        """Wait `secs` s a step at a time (it walks on meanwhile), calling
        `each()` every step (a tell that follows it)."""
        t = 0.0
        while t < secs:
            if each is not None:
                each()
            yield 0
            t += self.dt

    def _free(self, world, tx: int, ty: int, heroes) -> bool:
        """Can it stick something in tile (tx, ty)? Open ground (not water,
        not solid, not its own), nobody standing there."""
        t = world.tile_at(tx, ty)
        if t is None or t.solid or t.name in WATERY or t in FIXTURES:
            return False
        return not any(h.alive and abs(h.x - tx - 0.5) < h.hit_radius + 0.6
                       and abs(h.y - ty - 0.5) < h.hit_radius + 0.6 for h in heroes)

    # --- Signature 1: stone feathers ------------------------------------------------------

    def m_feathers(self):
        t = self.target_now()
        if t is None:
            return
        tell, n, spread, length, half, dmg, every, life = config.FOSSIL_FEATHERS
        tell = self.tell_s(tell)
        base = self.aim(t, self.x, self.y, secs=tell)
        sp = math.radians(spread)
        angles = [base + sp * (k / max(1, n - 1) - 0.5) for k in range(n)]
        self.pose, self.tell = "beat", ("feathers",)
        x0, y0 = self.x, self.y
        self.lines = [(x0, y0, a, length, half) for a in angles]
        yield tell
        ctx = self.ctx
        world = ctx.world
        heroes = [h for h in ctx.players if h.alive]
        for x, y, a, L, hw in self.lines:
            self.area(ctx, "line", x, y, a, L, hw, self.hurt(dmg), tell=tell)
            if not hasattr(world, "set_tile"):
                continue
            k = 3.0
            while k <= L:
                tx, ty = math.floor(x + math.cos(a) * k), math.floor(y + math.sin(a) * k)
                if self._free(world, tx, ty, heroes):
                    self.spikes.append([tx, ty, world.tile_at(tx, ty), life])
                    world.set_tile(tx, ty, tiles.FEATHER_SPIKE)
                k += every
            ctx.effects.append(Effect("debris", x + math.cos(a) * L * 0.6, y + math.sin(a) * L * 0.6))
        ctx.events.append("hit")
        self.lines, self.pose = [], ""
        yield 0.3

    def _tick_spikes(self, ctx, dt: float) -> None:
        """A stone feather crumbles when its time is up (the ground it stuck
        in comes back, unless something else is there now)."""
        world = ctx.world
        kept = []
        for s in self.spikes:
            s[3] -= dt
            if s[3] > 0:
                kept.append(s)
                continue
            if hasattr(world, "set_tile") and world.tile_at(s[0], s[1]) is tiles.FEATHER_SPIKE:
                world.set_tile(s[0], s[1], s[2])
        self.spikes = kept

    # --- Signature 2: the lava halo -------------------------------------------------------

    def m_halo(self):
        if not self.has_halo:
            yield 0.1
            return
        t = self.target_now()
        self.pose, self.tell = "halo", ("halo",)
        yield self.tell_s(config.FOSSIL_HALO[0])
        a = self.angle_to(t.x, t.y) if t is not None else self.facing
        w = LavaHalo(self, a)
        self.wheel = w
        self.ctx.spawned.append(w)
        self.ctx.effects.append(Effect("explosion", w.x, w.y))
        self.ctx.events.append("boulder")
        self.pose = ""
        yield 0.3

    def _tick_halo(self, ctx, dt: float) -> None:
        self.halo_lost = max(0.0, self.halo_lost - dt)
        w = self.wheel
        if w is None:
            return
        _, r0, r1, life, lap, rad, dmg, push, every, fire_s, fire_dmg, fire_r, _ = config.FOSSIL_HALO
        if not w.alive:
            self.wheel = None
            if not w.gone:
                self._cooled(ctx, w)
            return
        w.t += dt
        if w.t >= life:                                   # (it rolls back up: the halo again)
            w.gone = True
            w.hp = 0.0
            self.wheel = None
            ctx.effects.append(Effect("fizzle", w.x, w.y))
            return
        x0, y0 = w.x, w.y
        w.radius_now = r0 + (r1 - r0) * (w.t / life)
        w.angle += w.dir * _TAU / lap * dt
        if int(w.t / lap) != w.lap:                       # (a new round: it can hit you again)
            w.lap = int(w.t / lap)
            w.hit_ids.clear()
        w.x = self.x + math.cos(w.angle) * w.radius_now
        w.y = self.y + math.sin(w.angle) * w.radius_now * 0.8
        w.facing += dt * 9.0
        out = w.angle + w.dir * math.pi / 2
        self.ram(ctx, w.x, w.y, rad, self.hurt(dmg), push, out, w.hit_ids)
        w.rolled += math.hypot(w.x - x0, w.y - y0)
        if w.rolled >= every:
            w.rolled = 0.0
            ctx.zones.append(Zone("lava_splash", w.x, w.y, fire_r, fire_s, 0.5,
                                  self.hurt(fire_dmg), self))

    def _cooled(self, ctx, w: LavaHalo) -> None:
        """Its wheel hit to 0: it cools to stone and falls (a boulder: cover)."""
        self.halo_lost = 8.0
        world = ctx.world
        tx, ty = math.floor(w.x), math.floor(w.y)
        if hasattr(world, "set_tile") and self._free(world, tx, ty, [h for h in ctx.players]):
            world.set_tile(tx, ty, tiles.BASALT_BOULDER)
        ctx.effects.append(Effect("debris", w.x, w.y))
        ctx.effects.append(Effect("toast", w.x, w.y - 1.5, label="THE HALO COOLS"))
        ctx.events.append("boulder")

    # --- Signature 4: amber -----------------------------------------------------------------

    def m_amber(self):
        t = self.target_now()
        if t is None:
            return
        tell, n, length, half, speed, *_ = config.FOSSIL_AMBER
        self.planted, self.pose, self.tell = True, "weep", ("amber",)
        yield self.tell_s(tell)
        a0 = self.angle_to(t.x, t.y)
        for k in range(n):
            a = a0 + k * _TAU / n
            self.rivers.append(dict(x0=self.x, y0=self.y, angle=a, length=length, half=half,
                                    speed=speed, done=self.hit_radius * 0.6, caught=set()))
        self.ctx.events.append("orb")
        yield 0.6

    def _tick_amber(self, ctx, dt: float) -> None:
        """Resin running out, holding who it catches; hardening into walls;
        walls crumbling; the held rolling free."""
        _, _, _, _, _, hold, dmg, harden, stand = config.FOSSIL_AMBER
        world = ctx.world
        can = hasattr(world, "set_tile")
        heroes = [h for h in ctx.players if h.alive]
        for r in self.rivers:
            before = r["done"]
            r["done"] = min(r["length"], r["done"] + r["speed"] * dt)
            ca, sa = math.cos(r["angle"]), math.sin(r["angle"])
            k = before
            while can and k <= r["done"]:
                for off in (-r["half"] / 2, r["half"] / 2):
                    tx = math.floor(r["x0"] + ca * k - sa * off)
                    ty = math.floor(r["y0"] + sa * k + ca * off)
                    if (tx, ty) in self.resin:
                        continue
                    old = world.tile_at(tx, ty)
                    if old is None or old.solid or old.name in WATERY or old in FIXTURES:
                        continue
                    self.resin[(tx, ty)] = [harden, old]
                    world.set_tile(tx, ty, tiles.RESIN)
                k += 0.5
            for h in heroes:                              # (the running front catches you)
                if id(h) in r["caught"] or h.rolling or combat.drafting(h):
                    continue
                along = (h.x - r["x0"]) * ca + (h.y - r["y0"]) * sa
                across = abs(-(h.x - r["x0"]) * sa + (h.y - r["y0"]) * ca)
                if 0 <= along <= r["done"] + 0.5 and across <= r["half"] + h.hit_radius \
                        and r["done"] - along < 3.0:
                    r["caught"].add(id(h))
                    self._hold_hero(ctx, h, hold, dmg)
        self.rivers = [r for r in self.rivers if r["done"] < r["length"]]
        hardened = []
        for key, v in self.resin.items():
            v[0] -= dt
            if v[0] <= 0:
                hardened.append(key)
        for key in hardened:
            _, old = self.resin.pop(key)
            if not can or world.tile_at(*key) is not tiles.RESIN:
                continue
            tx, ty = key
            if any(abs(h.x - tx - 0.5) < h.hit_radius + 0.5 and abs(h.y - ty - 0.5) < h.hit_radius + 0.5
                   for h in heroes):
                world.set_tile(tx, ty, old)               # (never round a hero)
                continue
            world.set_tile(tx, ty, tiles.AMBER_WALL)
            self.walls.append([tx, ty, old, stand])
        kept = []
        for w in self.walls:
            w[3] -= dt
            if w[3] > 0:
                kept.append(w)
            elif can and world.tile_at(w[0], w[1]) is tiles.AMBER_WALL:
                world.set_tile(w[0], w[1], w[2])
        self.walls = kept
        for key, (h, left) in list(self.held.items()):
            if not h.alive:
                del self.held[key]
                continue
            if h.rolling:
                h.slow_t = 0.0
                del self.held[key]
                ctx.effects.append(Effect("toast", h.x, h.y - 1.5, label="ROLLED FREE!"))
                continue
            left -= dt
            if left <= 0:
                del self.held[key]
            else:
                self.held[key][1] = left

    def _hold_hero(self, ctx, h, hold: float, dmg: float) -> None:
        h.slowed(0.0, hold)
        self.held[id(h)] = [h, hold]
        if dmg:
            self.hit(h, self.hurt(dmg), self.facing)
        ctx.effects.append(Effect("toast", h.x, h.y - 1.5, label="CAUGHT IN AMBER!"))

    # --- The moves --------------------------------------------------------------------------

    def m_sweep(self):
        """A stone wing rises, then sweeps a wide arc (it walks on)."""
        t = self.target_now()
        if t is None:
            return
        tell, arc, reach, dmg, push = config.FOSSIL_SWEEP
        half = math.radians(arc) / 2
        self.pose, self.tell = "beat", ("sweep",)

        def follow():
            tt = self.target_now()
            a = self.angle_to(tt.x, tt.y) if tt is not None else self.facing
            self.cone = (self.x, self.y, a, reach, half)
        yield from self._hold(self.tell_s(tell), follow)
        x, y, a, _, _ = self.cone
        self.area(self.ctx, "cone", self.x, self.y, a, reach, half, self.hurt(dmg), push, tell=tell)
        self.ctx.events.append("hit")
        self.cone, self.pose = None, ""
        yield 0.3

    def m_dive(self):
        """Its line shown, a hop, a dive along it, a shower of stone."""
        t = self.target_now()
        if t is None:
            return
        hop, shown, length, speed, half, dmg, push, shards = config.FOSSIL_DIVE
        self.planted, self.pose = True, "crouch"
        a = self.aim(t, self.x, self.y, secs=shown + hop)
        self.line = (self.x, self.y, a, length, half)
        self.tell = ("dive",)
        yield self.tell_s(shown)
        self.airborne = 0.6
        yield hop
        self.airborne = 0.0
        self.pose = "dive"
        x0, y0 = self.x, self.y
        hit: set[int] = set()
        gone = 0.0
        while gone < length:
            step = min(length - gone, speed * self.dt)
            gone += step
            self.x, self.y = x0 + math.cos(a) * gone, y0 + math.sin(a) * gone
            self.facing = a
            self.ram(self.ctx, self.x, self.y, max(half, self.hit_radius), self.hurt(dmg), push, a, hit)
            yield 0
        self.record_run(x0, y0, a, length, speed, max(half, self.hit_radius), self.hurt(dmg), push,
                        tell=shown)
        self.line = None
        angles = [a + k * _TAU / shards for k in range(shards)]
        self.fan(self.ctx, "stone_shard", angles, tell=0.5)
        self.ctx.effects.append(Effect("explosion", self.x, self.y))
        self.ctx.events.append("boulder")
        self.pose = ""
        yield 0.4

    def m_breath(self):
        """A cone of ash and embers from its jaw; embers keep burning."""
        t = self.target_now()
        if t is None:
            return
        tell, arc, reach, dmg, embers, rad, life, tick = config.FOSSIL_BREATH
        half = math.radians(arc) / 2
        self.pose, self.tell = "breath", ("breath",)

        def follow():
            tt = self.target_now()
            a = self.angle_to(tt.x, tt.y) if tt is not None else self.facing
            self.cone = (self.x, self.y, a, reach, half)
        yield from self._hold(self.tell_s(tell), follow)
        x, y, a, _, _ = self.cone
        ctx = self.ctx
        self.area(ctx, "cone", self.x, self.y, a, reach, half, self.hurt(dmg), tell=tell)
        for _ in range(embers):
            d = self.rng.uniform(3.0, reach)
            b = a + self.rng.uniform(-half, half) * 0.8
            ctx.zones.append(Zone("lava_splash", self.x + math.cos(b) * d, self.y + math.sin(b) * d,
                                  rad, life, 0.5, self.hurt(tick), self))
        for k in range(5):
            d = reach * (k + 1) / 6
            ctx.effects.append(Effect("debris", self.x + math.cos(a) * d, self.y + math.sin(a) * d))
        ctx.events.append("orb")
        self.cone, self.pose = None, ""
        yield 0.3

    def m_stars(self):
        """Chains of stars falling on marked circles round you."""
        t = self.target_now()
        if t is None:
            return
        tell, chains, n, flight, rad, dmg, near, gap = config.FOSSIL_STARS
        self.pose, self.tell = "beat", ("stars",)
        yield self.tell_s(tell)
        self.pose = ""
        starts = []
        for c in range(chains):
            a = self.rng.uniform(0, _TAU)
            r = self.rng.uniform(0.0, near)
            starts.append((t.x + math.cos(a) * r, t.y + math.sin(a) * r * 0.8,
                           self.rng.uniform(0, _TAU)))
        for k in range(n):
            spots = []
            for x, y, a in starts:
                sx, sy = x + math.cos(a) * k * rad * 1.6, y + math.sin(a) * k * rad * 1.2
                spots.append((sx, sy, sx, sy))
            self.lob_many(self.ctx, spots, flight, "star", tell=flight)
            yield gap
        yield 0.3

    def landed(self, ctx, x: float, y: float, what: str, echo: bool) -> None:
        if what != "star":
            return
        _, _, _, _, rad, dmg, _, _ = config.FOSSIL_STARS
        self.area(ctx, "circle", x, y, 0.0, rad, 0.0, self.hurt(dmg), record=False)
        ctx.effects.append(Effect("explosion", x, y))
        ctx.events.append("boulder")
