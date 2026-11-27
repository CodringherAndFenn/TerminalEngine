"""
ai/finals.py -- what every final boss does (M33, design/FINALS.md 3-6): it
HUNTS you across the whole map.

A final wakes the moment the fourth ocean boss falls (systems/quests.py,
systems/finals.py picks which), comes ashore on the main island's coast
between its two realms and stands there FINAL_WAKE_GRACE s. There's no
arena and no walls: its "lair" is systems/finals.Roaming, wherever it is,
so every hero is always in its fight. Then:

  THE WALK    it walks at the nearest hero (FINAL_WALK: about half your
              pace, slower while a move is on), circling once it's close.
              It walks over water and through everything: what's solid in
              its way is smashed.
  THE LEAP    once the nearest hero is more than FINAL_LEAP[0] tiles off
              (you ran, or it's just come ashore) it crouches (the tell),
              takes off, and lands near that hero: the landing is marked
              FINAL_LEAP[2] s before it comes down, and the impact is a
              ring you roll through or get out of. Over water too, so it
              follows you out to the ocean zones. It never stops hunting.
  ITS TRAIL   the ground it walks turns to its two realms' land (`GROUNDS`,
              patches of each), never on water; each landing leaves a crater
              of it. The scar stays for the rest of the run (the world
              remembers set tiles). Its realms' creatures (FINAL_BROODS)
              crawl out of the trail behind it, endgame tough like on their
              islands, every so often while few are about.
  FRIENDLY FIRE  its blows hurt the island's own monsters too, and any of
              them it hurts turns on it at once (ai/brain.py) -- leading it
              through a biome's monsters is a tactic. Its own creatures it
              never hurts (systems/combat._may_hurt), and they never turn on
              it.

A final's fight -- its moves, its phases, its two forms -- is its own class
on top of this (ai/fossil_angel.py, M33.1). Everything is driven by its own
seeded dice and the step's dt, so a hunt replays exactly.
"""

from __future__ import annotations

import math
import random

from .. import config
from ..entities.effects import Effect
from ..specs import EnemySpec
from ..systems import combat
from ..systems.collision import WATERY
from ..world.rng import hash_coords
from .bosses import Boss
from .creatures import _numbered_hit

_TAU = math.tau


class Final(Boss):
    """A final boss's hunt (see the module's docstring). Subclasses set
    `GROUNDS` (their two realms' ground tiles: a tuple of tiles per realm)
    and `BROOD` (a config.FINAL_BROODS key, default their kind)."""

    final = True                 # (ai/brain.py: a monster it hurts turns on it)
    GROUNDS: tuple = ()

    def __init__(self, spec: EnemySpec, x: float, y: float, rng: random.Random,
                 spawn_id=None, hit_radius: float = 2.0) -> None:
        super().__init__(spec, x, y, rng, spawn_id, hit_radius)
        self.grace = config.FINAL_WAKE_GRACE   # s left coming ashore, before the first leap
        self.leap: list | None = None     # ["crouch" | "air", s in, target, landing, from]
        self.mark: tuple | None = None    # a landing shown: (x, y)
        self.recovering = 0.0             # s getting up after a landing
        self.brood: list = []             # its realms' creatures, out of its trail
        self.brood_cd = config.FINAL_BROOD[0]
        self.path: list = []              # where it stamped its trail (newest last)
        self._stamped_at: tuple | None = None
        self.circle_dir = 1
        self.order: list = []             # the kill order that woke it (the victory screen)
        self.leaps = 0                    # (the dev report, tests)

    # --- Who's about ----------------------------------------------------------------

    def victims(self, ctx) -> list:
        """Everyone its blows hurt: the heroes and the island's monsters,
        never itself, its parts or its own creatures."""
        return [a for a in ctx.actors
                if a is not self and a.alive and getattr(a, "final_own", None) is not self
                and getattr(a, "part_of", None) is not self]

    def nearest(self):
        heroes = [h for h in self.ctx.players if h.alive]
        return min(heroes, key=lambda h: math.hypot(h.x - self.x, h.y - self.y), default=None)

    def hit(self, a, damage: float, angle: float, push: float = 0.0) -> None:
        """One of its blows lands on `a` (a hero or a monster)."""
        _numbered_hit(a, damage, self, angle, self.ctx)
        if push:
            combat.push(a, self.ctx.world, math.cos(angle) * push, math.sin(angle) * push)

    @property
    def hunting(self) -> bool:
        """Out and about (not coming ashore, not in the air): the world
        round it is kept loaded (systems/quests.stream_views)."""
        return self.grace <= 0 and (self.leap is None or self.leap[0] == "crouch")

    # --- Its turn ----------------------------------------------------------------------

    def think(self, ctx, dt: float) -> None:
        self.ctx = ctx
        if self.hunt(ctx, dt):
            self.time += dt
            self.dt = dt
            return
        super().think(ctx, dt)

    def hunt(self, ctx, dt: float) -> bool:
        """Its walk, its leaps, its trail and what crawls out of it. True
        while it can't fight (coming ashore, leaping, getting up)."""
        if self.grace > 0:
            self.grace -= dt
            return True
        if self.leap is not None:
            self._leap_step(ctx, dt)
            return True
        if self.recovering > 0:
            self.recovering -= dt
            return True
        t = self.nearest()
        if t is None:
            return True
        far = config.FINAL_LEAP[0]
        d = math.hypot(t.x - self.x, t.y - self.y)
        if d > far and (self._gen is None or d > far * 1.5):
            self.abort_move()
            self._crouch(t)
            return True
        if not self.planted_now():
            self.walk(t, dt)
        self.lay_trail(ctx)
        self._brood_step(ctx, dt)
        return False

    def planted_now(self) -> bool:
        """A move that holds it in place (subclasses say which)."""
        return False

    def abort_move(self) -> None:
        """The move it was in stops (a leap, a new form)."""
        self.move, self._gen, self.tell = None, None, None
        self.clear_tells()

    def clear_tells(self) -> None:
        """Nothing of a move left standing (subclasses clear their tells)."""

    # --- The walk -----------------------------------------------------------------------

    def walk(self, t, dt: float) -> None:
        """At the nearest hero, circling once within FINAL_WALK[1] tiles;
        through everything (lay_trail smashes what's solid)."""
        speed, keep, slow = config.FINAL_WALK
        v = speed * (slow if self._gen is not None else 1.0)
        dx, dy = t.x - self.x, t.y - self.y
        d = math.hypot(dx, dy) or 1.0
        to = math.atan2(dy, dx)
        if d > keep + 1.0:
            a = to
        elif d < keep - 2.0:
            a = to + math.pi
        else:
            a = to + math.pi / 2 * self.circle_dir
            if self.rng.random() < dt * 0.15:
                self.circle_dir = -self.circle_dir
        self.x += math.cos(a) * v * dt
        self.y += math.sin(a) * v * dt
        self.facing = to

    # --- The trail ------------------------------------------------------------------------

    def ground_at(self, tx: int, ty: int):
        """Its realms' ground for tile (tx, ty): patches of each realm, a
        tile of the realm's own at random within a patch."""
        if not self.GROUNDS:
            return None
        seed = getattr(self.ctx.world, "seed", 0) or 0
        realm = self.GROUNDS[hash_coords(seed, 0xF17A, tx // 3, ty // 3) % len(self.GROUNDS)]
        return realm[hash_coords(seed, 0xF17B, tx, ty) % len(realm)]

    def stamp(self, world, x: float, y: float, r: float) -> int:
        """Its land on every tile within `r` of (x, y) but water (what's
        solid there is smashed). Returns how many tiles changed."""
        if not hasattr(world, "set_tile") or not self.GROUNDS:
            return 0
        n = 0
        cx, cy = math.floor(x), math.floor(y)
        k = math.ceil(r)
        for j in range(-k, k + 1):
            for i in range(-k, k + 1):
                tx, ty = cx + i, cy + j
                if math.hypot(tx + 0.5 - x, ty + 0.5 - y) > r:
                    continue
                old = world.tile_at(tx, ty)
                if old is None or old.name in WATERY:
                    continue
                new = self.ground_at(tx, ty)
                if new is not None and new is not old:
                    world.set_tile(tx, ty, new)
                    n += 1
        return n

    def lay_trail(self, ctx) -> None:
        """A stamp of its land every FINAL_TRAIL[1] tiles it walks."""
        r, every = config.FINAL_TRAIL
        last = self._stamped_at
        if last is not None and math.hypot(self.x - last[0], self.y - last[1]) < every:
            return
        self._stamped_at = (self.x, self.y)
        self.stamp(ctx.world, self.x, self.y, r)
        self.path.append((self.x, self.y))
        if len(self.path) > 240:
            del self.path[:40]

    def _brood_step(self, ctx, dt: float) -> None:
        """Its realms' creatures crawl out of the trail behind it."""
        _, most, at_once, near, far = config.FINAL_BROOD
        self.brood_cd -= dt
        if self.brood_cd > 0 or self.recruit is None:
            return
        self.brood_cd = self.brood_every()
        self.brood = [e for e in self.brood
                      if e.alive and math.hypot(e.x - self.x, e.y - self.y) < 90]
        keys = config.FINAL_BROODS.get(getattr(self, "BROOD", self.espec.kind), ())
        heroes = [h for h in ctx.players if h.alive]
        spots = [p for p in self.path if near <= math.hypot(p[0] - self.x, p[1] - self.y) <= far
                 and all(math.hypot(p[0] - h.x, p[1] - h.y) >= near for h in heroes)]
        if not keys or not spots:
            return
        for _ in range(min(at_once, most - len(self.brood))):
            x, y = self.rng.choice(spots)
            e = self.recruit(self.rng.choice(keys), x + self.rng.uniform(-1.5, 1.5),
                             y + self.rng.uniform(-1.5, 1.5))
            if e is None:
                return
            self.own(e)
            ctx.effects.append(Effect("nova", e.x, e.y, size=2.0))

    def brood_every(self) -> float:
        """s between its creatures crawling out (a form may bring fewer)."""
        return config.FINAL_BROOD[0]

    def own(self, e) -> None:
        """`e` is one of its own creatures: endgame tough (like on its
        realm's island), never hurt by it, never turning on it."""
        if hasattr(e, "toughen") and not getattr(e, "zone_tough", False):
            e.toughen(config.ZONE_TOUGH[0])
            e.damage_mult *= config.ZONE_TOUGH[1]
            e.zone_tough = True
        e.final_own = self
        e.alert = True
        self.brood.append(e)

    # --- The leap ------------------------------------------------------------------------

    def on_leap(self) -> None:
        """It's about to leap (subclasses drop what can't come along)."""

    def _crouch(self, t) -> None:
        self.on_leap()
        self.leap = ["crouch", 0.0, t, None, (self.x, self.y)]
        self.facing = math.atan2(t.y - self.y, t.x - self.x)

    def _landing(self, t) -> tuple[float, float]:
        """Where it'll come down: FINAL_LEAP[3]-[4] tiles from hero `t`."""
        lo, hi = config.FINAL_LEAP[3], config.FINAL_LEAP[4]
        a = self.rng.uniform(0, _TAU)
        r = self.rng.uniform(lo, hi)
        return t.x + math.cos(a) * r, t.y + math.sin(a) * r * 0.8

    def _leap_step(self, ctx, dt: float) -> None:
        crouch, flight = config.FINAL_LEAP[1], config.FINAL_LEAP[2]
        leap = self.leap
        leap[1] += dt
        if leap[0] == "crouch":
            if leap[1] < crouch:
                return
            t = leap[2] if leap[2].alive else self.nearest()
            if t is None:
                self.leap = None
                return
            spot = self._landing(t)
            self.leap = ["air", 0.0, t, spot, (self.x, self.y)]
            self.mark = spot
            self.airborne = 0.05
            ctx.effects.append(Effect("debris", self.x, self.y))
            ctx.events.append("boulder")
            return
        f = min(1.0, leap[1] / flight)
        (x0, y0), (x1, y1) = leap[4], leap[3]
        self.x, self.y = x0 + (x1 - x0) * f, y0 + (y1 - y0) * f
        self.facing = math.atan2(y1 - y0, x1 - x0)
        self.airborne = max(0.05, math.sin(math.pi * f))
        if f >= 1.0:
            self._land(ctx)

    def _land(self, ctx) -> None:
        """It comes down: the impact ring, a crater of its land."""
        _, _, _, _, _, radius, damage, push, up = config.FINAL_LEAP
        self.leap, self.mark = None, None
        self.airborne = 0.0
        self.recovering = up
        self.leaps += 1
        for a in self.victims(ctx):
            if not a.hittable or combat.drafting(a):
                continue
            d = math.hypot(a.x - self.x, a.y - self.y)
            if d <= radius + a.hit_radius:
                ang = math.atan2(a.y - self.y, a.x - self.x) if d > 1e-6 else self.facing
                self.hit(a, damage * self.damage_mult, ang, push)
        self.stamp(ctx.world, self.x, self.y, config.FINAL_CRATER)
        self._stamped_at = (self.x, self.y)
        self.path.append((self.x, self.y))
        ctx.effects.append(Effect("explosion", self.x, self.y))
        ctx.effects.append(Effect("nova", self.x, self.y, size=radius))
        for k in range(8):
            a = k * _TAU / 8
            ctx.effects.append(Effect("debris", self.x + math.cos(a) * radius * 0.7,
                                      self.y + math.sin(a) * radius * 0.5))
        ctx.events.append("boulder")
