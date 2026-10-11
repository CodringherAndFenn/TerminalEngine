"""
ai/forest.py -- the haunted forest's new enemies (P8, design/BOSSES.md 24.6).

Letter-art creatures like the plains' (ai/plains.PlainsCreature: walk
frames, a wind-up `tell`, flying), drawn by render/plains.py with their
own tells from render/forest.py. Parts and things they send out come back
through AIContext.spawned, as (key, x, y) or as ready-made actors.

  skeleton        straight at you; falls into a bone pile that pulls itself
                  back together once (BONE_REBUILD s) unless you break it
  woodsman, spiderlings (swarms), bats (wobbly, flying): simple chasers
  banshee         floats close, breathes in, screams in a cone that hurts
                  and pushes back, drifts off
  phantom         drifts through everything; solid (hittable) and faded in
                  turn; its touch hurts and slows
  grave digger    keeps back; the ground cracks where he's about to dig up
                  a skeleton
  headless knight (elite) three wide swings in a row; its head circles it:
                  hits on the head hurt it more and stagger it
  centipede       a head and its body segments, each a body you can shoot;
                  shot apart, the rest crawls on as its own centipede
  giant spider    keeps back, spits webs: sticky patches that slow
  cultist         plants a ring of candles; skeletons rise in it while any
                  candle burns
  wendigo (elite) pairs of fast lunges; rears up and howls (slows you)

The ghost woodcutter (a returning axe) and the witch's apprentice (an orb
that splits) are archers with their own bodies (config.BODIES); the shots'
endings are systems/combat._shot_ends.
"""

from __future__ import annotations

import math

from .. import config
from ..entities.effects import Effect
from ..entities.projectile import Projectile
from .brain import AIContext
from .creatures import _numbered_hit
from .plains import Chaser, PlainsCreature


def _near(ctx: AIContext, key: str, x: float, y: float, reach: float) -> int:
    return sum(1 for a in ctx.actors if getattr(a, "kind_key", "") == key and a.alive
               and math.hypot(a.x - x, a.y - y) <= reach)


def _skeletons_near(ctx: AIContext, x: float, y: float, reach: float) -> int:
    return _near(ctx, "skeleton", x, y, reach) + _near(ctx, "risen_skeleton", x, y, reach)


def _vanish(e) -> None:
    """Gone without anyone killing it (no reward)."""
    e.hp = 0.0
    e.last_hit_by = None


def _keep_range(e, ctx: AIContext, t, lo: float, hi: float, dt: float) -> None:
    """Back off inside `lo`, close in beyond `hi`, hold between."""
    d = e.dist_to(t)
    if d < lo:
        a = e.angle_to(t.x, t.y) + math.pi
        e.go(ctx, e.x + math.cos(a) * 3, e.y + math.sin(a) * 3, dt, e.espec.speed)
    elif d > hi:
        e.go(ctx, t.x, t.y, dt, e.espec.speed * 0.7)
    e.facing = e.angle_to(t.x, t.y)


def _roam(e, ctx: AIContext, dt: float) -> None:
    if e.alert and e.last_known is not None:
        e.go(ctx, *e.last_known, dt, e.espec.speed * 0.7)
    else:
        e.go(ctx, *e.wander_goal(dt), dt, e.espec.speed * 0.4)


# --- Simple chasers -------------------------------------------------------------------


class Skeleton(Chaser):
    """A chaser that falls into a bone pile (unless it already rose once)."""

    def on_death(self, ctx: AIContext) -> None:
        ctx.effects.append(Effect("debris", self.x, self.y))
        if getattr(self, "kind_key", "") == "skeleton":
            ctx.spawned.append(("bone_pile", self.x, self.y))


class BonePile(PlainsCreature):
    """Lies there BONE_REBUILD s, then is a skeleton again (once). Break it
    first and that's the end of it."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.timer = config.BONE_REBUILD
        self.rose = False

    def think(self, ctx: AIContext, dt: float) -> None:
        super().think(ctx, dt)
        self.timer -= dt
        self.tell = self.timer if self.timer < 1.0 else 0.0
        if self.timer <= 0 and not self.rose:
            self.rose = True
            _vanish(self)
            ctx.spawned.append(("risen_skeleton", self.x, self.y))
            ctx.effects.append(Effect("burrow", self.x, self.y))

    def on_death(self, ctx: AIContext) -> None:
        if not self.rose:
            ctx.effects.append(Effect("debris", self.x, self.y))


class Bat(Chaser):
    flies = True
    wobble = config.BAT_WOBBLE

    def can_see(self, world, other) -> bool:
        return math.hypot(other.x - self.x, other.y - self.y) <= self.espec.sight


# --- Spirits and the restless dead ----------------------------------------------------


class Banshee(PlainsCreature):
    """Floats in to BANSHEE[0] tiles, breathes in (the wind-up: it glows),
    then screams: everything in a BANSHEE[1]-degree cone out to the
    spec's attack_radius is hurt and pushed BANSHEE[2] tiles. Then it
    drifts off for BANSHEE[3] s."""

    flies = True

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.drift = 0.0

    def can_see(self, world, other) -> bool:
        return math.hypot(other.x - self.x, other.y - self.y) <= self.espec.sight

    def think(self, ctx: AIContext, dt: float) -> None:
        super().think(ctx, dt)
        self.sense(ctx, dt)
        close, cone, push, drift = config.BANSHEE
        t = self.target
        if self.windup > 0:
            self.windup -= dt
            self.tell = self.windup
            if t is not None:
                self.facing = self.angle_to(t.x, t.y)
            if self.windup <= 0:
                self.tell = 0.0
                self._scream(ctx, math.radians(cone) / 2, push)
                self.drift = drift
            return
        if self.drift > 0:
            self.drift -= dt
            if t is not None:
                a = self.angle_to(t.x, t.y) + math.pi * 0.75
                self.go(ctx, self.x + math.cos(a) * 3, self.y + math.sin(a) * 3, dt,
                        self.espec.speed)
            return
        if t is None or not self.sees_target:
            _roam(self, ctx, dt)
            return
        if self.dist_to(t) > close:
            self.go(ctx, t.x, t.y, dt, self.espec.speed)
        elif self.cooldown <= 0:
            self.facing = self.angle_to(t.x, t.y)
            self.windup = self.espec.windup

    def _scream(self, ctx: AIContext, half: float, push: float) -> None:
        reach = self.espec.attack_radius
        ctx.effects.append(Effect("scream", self.x, self.y, self.facing, size=reach))
        ctx.events.append("hex")
        for a in ctx.actors:
            if a is self or not a.hittable:
                continue
            d = math.hypot(a.x - self.x, a.y - self.y)
            if d > reach + a.hit_radius:
                continue
            ang = math.atan2(a.y - self.y, a.x - self.x)
            off = abs((ang - self.facing + math.pi) % math.tau - math.pi)
            if d > a.hit_radius and off > half:
                continue
            _numbered_hit(a, self.espec.damage * self.damage_mult, self, ang, ctx)
            from ..systems import combat
            combat.push(a, ctx.world, math.cos(ang) * push, math.sin(ang) * push)
        self.cooldown = self.espec.cooldown


class Phantom(PlainsCreature):
    """Drifts at you through everything. Solid for PHANTOM[0] s (hittable,
    and its touch hurts and slows you to x PHANTOM[2] for PHANTOM[3] s),
    then faded for PHANTOM[1] s (nothing touches it, it touches nothing;
    you still see it)."""

    flies = True

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.phase = self.rng.uniform(0, sum(config.PHANTOM[:2]))

    @property
    def solid(self) -> bool:
        return self.phase < config.PHANTOM[0]

    @property
    def hittable(self) -> bool:
        return self.alive and self.solid

    def sprite_now(self) -> str:
        return "phantom" if self.solid else "phantom_faded"

    def can_see(self, world, other) -> bool:
        return math.hypot(other.x - self.x, other.y - self.y) <= self.espec.sight

    def think(self, ctx: AIContext, dt: float) -> None:
        super().think(ctx, dt)
        self.sense(ctx, dt)
        solid_t, faded_t, slow, slow_t = config.PHANTOM
        self.phase = (self.phase + dt) % (solid_t + faded_t)
        t = self.target
        if t is None or not self.alert:
            _roam(self, ctx, dt)
            return
        self.go(ctx, t.x, t.y, dt, self.espec.speed)
        if self.solid and self.cooldown <= 0 and t.hittable \
                and self.dist_to(t) <= self.hit_radius + t.hit_radius + self.espec.attack_radius:
            _numbered_hit(t, self.espec.damage * self.damage_mult, self, self.facing, ctx)
            if hasattr(t, "slowed"):
                t.slowed(slow, slow_t)
            self.cooldown = self.espec.cooldown


class GraveDigger(PlainsCreature):
    """Keeps DIGGER[3] tiles back. Every DIGGER[0] s, while fewer than
    DIGGER[2] skeletons are about, he picks a spot DIGGER[1] tiles toward
    you: the ground there cracks for the spec's windup (the tell, `dig`),
    then a skeleton climbs out."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.timer = self.rng.uniform(2.0, config.DIGGER[0])
        self.dig: list | None = None              # [x, y, s left]

    def think(self, ctx: AIContext, dt: float) -> None:
        super().think(ctx, dt)
        self.sense(ctx, dt)
        every, ahead, most, keep = config.DIGGER
        if self.dig is not None:
            self.dig[2] -= dt
            if self.dig[2] <= 0:
                x, y, _ = self.dig
                self.dig = None
                ctx.spawned.append(("risen_skeleton", x, y))
                ctx.effects.append(Effect("eruption", x, y))
            return
        t = self.target
        if t is None or not self.sees_target:
            _roam(self, ctx, dt)
            return
        _keep_range(self, ctx, t, keep * 0.7, keep * 1.3, dt)
        self.timer -= dt
        if self.timer <= 0:
            self.timer = every
            if _skeletons_near(ctx, self.x, self.y, 16) < most:
                a = self.angle_to(t.x, t.y)
                self.dig = [self.x + math.cos(a) * ahead, self.y + math.sin(a) * ahead,
                            self.espec.windup]


class HeadlessKnight(PlainsCreature):
    """Elite. Walks you down; in reach it winds up, then swings
    KNIGHT_COMBO[0] times, KNIGHT_COMBO[1] s apart, each a wide blow in
    front. Its head (KnightHead) circles it; hits on the head hurt the
    knight more and stagger it."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.head = None
        self.swings = 0
        self.gap = 0.0
        self.stagger = 0.0
        self.stagger_cd = 0.0

    def think(self, ctx: AIContext, dt: float) -> None:
        super().think(ctx, dt)
        if self.head is None:                         # its head, the first time it stirs
            from . import make_enemy
            self.head = make_enemy("knight_head", self.x, self.y - 1.5, self.rng)
            self.head.knight = self
            self.head.part_of = self
            ctx.spawned.append(self.head)
        self.sense(ctx, dt)
        self.stagger_cd = max(0.0, self.stagger_cd - dt)
        if self.stagger > 0:
            self.stagger -= dt
            self.swings, self.windup, self.tell = 0, 0.0, 0.0
            return
        if self.swings > 0:
            self.gap -= dt
            if self.gap <= 0:
                self._swing(ctx)
            return
        if self.windup > 0:
            self.windup -= dt
            self.tell = self.windup
            if self.windup <= 0:
                self.tell = 0.0
                self.swings = config.KNIGHT_COMBO[0]
                self._swing(ctx)
            return
        t = self.target
        if t is None or not self.sees_target:
            _roam(self, ctx, dt)
            return
        if self.dist_to(t) <= self.espec.attack_radius + t.hit_radius and self.cooldown <= 0:
            self.facing = self.angle_to(t.x, t.y)
            self.windup = self.espec.windup
            return
        self.go(ctx, t.x, t.y, dt, self.espec.speed)

    def _swing(self, ctx: AIContext) -> None:
        from ..systems import combat
        t = self.target
        if t is not None:
            self.facing = self.angle_to(t.x, t.y)
        cx = self.x + math.cos(self.facing) * 1.2
        cy = self.y + math.sin(self.facing) * 1.2
        combat.blast(cx, cy, self.espec.attack_radius * 0.8, self.espec.damage * self.damage_mult,
                     self, ctx.actors, effects=ctx.effects)
        ctx.effects.append(Effect("slash", cx, cy, self.facing))
        ctx.events.append(combat.HIT)
        self.swings -= 1
        self.gap = config.KNIGHT_COMBO[1]
        if self.swings <= 0:
            self.cooldown = self.espec.cooldown

    def hit_on_head(self, amount: float, source, angle) -> float:
        _, mult, stagger, cd = config.KNIGHT_HEAD
        dealt = self.take_damage(amount * mult, source, angle)
        if dealt > 0 and self.stagger_cd <= 0:
            self.stagger, self.stagger_cd = stagger, cd
        return dealt

    def on_death(self, ctx: AIContext) -> None:
        ctx.effects.append(Effect("explosion", self.x, self.y))
        if self.head is not None and self.head.alive:
            _vanish(self.head)


class KnightHead(PlainsCreature):
    """The headless knight's head: a lantern circling it, KNIGHT_HEAD[0]
    tiles out. It can't be killed itself; what hits it goes to the knight
    (HeadlessKnight.hit_on_head)."""

    flies = True

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.knight = None
        self.turn = self.rng.uniform(0, math.tau)

    def think(self, ctx: AIContext, dt: float) -> None:
        super().think(ctx, dt)
        k = self.knight
        if k is None or not k.alive or not any(a is k for a in ctx.actors):
            _vanish(self)                             # (dead, or gone to sleep)
            return
        self.turn += dt * config.KNIGHT_HEAD_TURN
        r = config.KNIGHT_HEAD[0]
        self.x = k.x + math.cos(self.turn) * r
        self.y = k.y + math.sin(self.turn) * r * 0.7 - 0.6
        self.facing = k.facing

    def take_damage(self, amount, source, from_angle):
        k = self.knight
        if k is None or not k.alive or source is k:
            return 0.0
        return k.hit_on_head(amount, source, from_angle)


# --- Beasts ----------------------------------------------------------------------------


class Centipede(PlainsCreature):
    """One segment of a centipede. A head (no `leader`) crawls at you on a
    wobbly line and bites; a body segment follows the one ahead,
    CENTIPEDE[1] tiles behind. The spawned head grows its body on its
    first turn (CENTIPEDE[0] segments in all). A segment whose leader is
    gone becomes a head: shot apart, both halves crawl on."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.leader = None
        self.grown = False
        self.wobble = config.CENTIPEDE[2]

    def sprite_now(self) -> str:
        return "centipede_head" if self.leader is None else "centipede_body"

    def think(self, ctx: AIContext, dt: float) -> None:
        super().think(ctx, dt)
        if not self.grown:
            self.grown = True
            self._grow(ctx)
        if self.leader is not None and not self.leader.alive:
            self.leader = None                        # the one ahead is gone: lead on
            self.alert = True
        if self.leader is not None:
            self._follow(dt)
            return
        # A head: a chaser that bites.
        self.sense(ctx, dt)
        if self.windup > 0:
            self.windup -= dt
            self.tell = self.windup
            if self.windup <= 0:
                self.tell = 0.0
                self.bite(ctx)
            return
        t = self.target
        if t is None or not self.alert:
            self.go(ctx, *self.wander_goal(dt), dt, self.espec.speed * 0.5)
            return
        goal = (t.x, t.y) if self.sees_target else self.last_known
        if goal is None:
            return
        if self.sees_target and self.dist_to(t) <= self.espec.attack_radius + t.hit_radius \
                and self.cooldown <= 0:
            self.facing = self.angle_to(t.x, t.y)
            self.windup = self.espec.windup
            return
        self.go(ctx, *goal, dt, self.espec.speed)

    def _grow(self, ctx: AIContext) -> None:
        if getattr(self, "kind_key", "") != "centipede" or self.leader is not None:
            return
        from . import make_enemy
        ahead = self
        gap = config.CENTIPEDE[1]
        for k in range(1, config.CENTIPEDE[0]):
            seg = make_enemy("centipede", self.x - gap * k, self.y, self.rng)
            seg.leader, seg.grown, seg.alert = ahead, True, self.alert
            ctx.spawned.append(seg)
            ahead = seg

    def _follow(self, dt: float) -> None:
        """Stay CENTIPEDE[1] tiles behind the one ahead (crawling over what
        the head went round)."""
        lead = self.leader
        d = math.hypot(lead.x - self.x, lead.y - self.y)
        gap = config.CENTIPEDE[1]
        self.facing = math.atan2(lead.y - self.y, lead.x - self.x)
        if d > gap:
            step = d - gap
            self.x += math.cos(self.facing) * step
            self.y += math.sin(self.facing) * step
            self._moved = step
            self.walked += step


class GiantSpider(PlainsCreature):
    """Keeps SPIDER_RANGE from its target and every SPIDER_EVERY s spits a
    web blob at it (a short wind-up first); where the blob stops it leaves
    a sticky web patch (systems/combat._shot_ends)."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.timer = self.rng.uniform(1.0, config.SPIDER_EVERY)

    def think(self, ctx: AIContext, dt: float) -> None:
        super().think(ctx, dt)
        self.sense(ctx, dt)
        t = self.target
        if self.windup > 0:
            self.windup -= dt
            self.tell = self.windup
            if self.windup <= 0:
                self.tell = 0.0
                if t is not None:
                    self._spit(ctx, t)
            return
        if t is None or not self.sees_target:
            _roam(self, ctx, dt)
            return
        _keep_range(self, ctx, t, *config.SPIDER_RANGE, dt)
        self.timer -= dt
        if self.timer <= 0:
            self.timer = config.SPIDER_EVERY
            self.windup = self.espec.windup

    def _spit(self, ctx: AIContext, t) -> None:
        shell = config.WEAPONS["web_spit"].shell
        a = self.angle_to(t.x, t.y)
        ctx.projectiles.append(Projectile(self.x, self.y, a, shell, owner=self,
                                          damage=shell.damage * self.damage_mult))
        ctx.events.append(shell.sound)


# --- Folk of the dark wood --------------------------------------------------------------


class Cultist(PlainsCreature):
    """Keeps CULTIST[5] from the heroes. With no candles burning it winds
    up (the spec's windup) and plants CULTIST[0] candles in a ring of
    CULTIST[1] tiles, 3 tiles toward its target; every CULTIST[2] s while
    any burns, a skeleton rises in the middle (at most CULTIST[3] about).
    All candles out: a new ring after CULTIST[4] s."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.candles: list = []
        self.ring: tuple[float, float] | None = None
        self.timer = 0.0
        self.again = 0.0

    @property
    def burning(self) -> list:
        return [c for c in self.candles if c.alive]

    def think(self, ctx: AIContext, dt: float) -> None:
        super().think(ctx, dt)
        self.sense(ctx, dt)
        n, radius, every, most, again, (lo, hi) = config.CULTIST
        t = self.target
        if self.windup > 0:
            self.windup -= dt
            self.tell = self.windup
            if self.windup <= 0:
                self.tell = 0.0
                if t is not None:
                    self._plant(ctx, t, n, radius)
            return
        if self.burning:
            self.timer -= dt
            if self.timer <= 0:
                self.timer = every
                cx, cy = self.ring
                if _skeletons_near(ctx, cx, cy, radius + 6) < most:
                    ctx.spawned.append(("risen_skeleton", cx, cy))
                    ctx.effects.append(Effect("eruption", cx, cy))
        elif self.ring is not None:
            self.ring, self.candles, self.again = None, [], again
        self.again = max(0.0, self.again - dt)
        if t is None or not self.sees_target:
            _roam(self, ctx, dt)
            return
        _keep_range(self, ctx, t, lo, hi, dt)
        if self.ring is None and self.again <= 0:
            self.windup = self.espec.windup

    def _plant(self, ctx: AIContext, t, n: int, radius: float) -> None:
        from . import make_enemy
        a = self.angle_to(t.x, t.y)
        cx, cy = self.x + math.cos(a) * 3, self.y + math.sin(a) * 3
        self.ring, self.timer = (cx, cy), 1.0
        self.candles = []
        for k in range(n):
            b = k * math.tau / n
            c = make_enemy("candle", cx + math.cos(b) * radius, cy + math.sin(b) * radius * 0.8,
                           self.rng)
            c.part_of = self
            self.candles.append(c)
            ctx.spawned.append(c)
        ctx.events.append("chime")

    def on_death(self, ctx: AIContext) -> None:
        ctx.effects.append(Effect("explosion", self.x, self.y))
        for c in self.burning:                    # its candles go out with it
            _vanish(c)


class Candle(PlainsCreature):
    """A cultist's candle: never moves; shoot it out."""

    def on_death(self, ctx: AIContext) -> None:
        ctx.effects.append(Effect("fizzle", self.x, self.y))


class Wendigo(PlainsCreature):
    """Elite. Pairs of lunges: crouch (the spec's windup), lunge
    WENDIGO_LUNGE[0] tiles at WENDIGO_LUNGE[1] tiles/s hitting the first
    body it meets, WENDIGO_LUNGE[2] s, then again, re-aimed. Every
    WENDIGO_HOWL[0] s with a hero within WENDIGO_HOWL[1] tiles it rears up
    (WENDIGO_HOWL[2] s) and howls: heroes that close are slowed to x
    WENDIGO_HOWL[3] for WENDIGO_HOWL[4] s."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.state = "stalk"
        self.timer = 0.0
        self.lunges = 0
        self.aim = 0.0
        self.ran = 0.0
        self.struck = False
        self.howl_cd = self.rng.uniform(3.0, config.WENDIGO_HOWL[0])

    def think(self, ctx: AIContext, dt: float) -> None:
        super().think(ctx, dt)
        self.sense(ctx, dt)
        self.howl_cd = max(0.0, self.howl_cd - dt)
        t = self.target
        length, speed, pause = config.WENDIGO_LUNGE
        every, reach, rear, slow, slow_t = config.WENDIGO_HOWL
        if self.state in ("crouch", "rear", "pause"):
            self.timer -= dt
            self.tell = self.timer if self.state in ("crouch", "rear") else 0.0
            if self.state == "crouch" and t is not None:
                self.aim = self.facing = self.angle_to(t.x, t.y)
            if self.timer <= 0:
                self.tell = 0.0
                if self.state == "rear":
                    self._howl(ctx, reach, slow, slow_t)
                    self.state = "stalk"
                elif self.state == "pause":
                    self.state, self.timer = "crouch", self.espec.windup * 0.5
                else:
                    self.state, self.ran, self.struck = "lunge", 0.0, False
            return
        if self.state == "lunge":
            self._lunge(ctx, dt, length, speed, pause)
            return
        if t is None or not self.sees_target:
            _roam(self, ctx, dt)
            return
        d = self.dist_to(t)
        if self.howl_cd <= 0 and d <= reach:
            self.state, self.timer, self.howl_cd = "rear", rear, every
            return
        if d <= self.espec.attack_radius and self.cooldown <= 0:
            self.state, self.timer, self.lunges = "crouch", self.espec.windup, 2
            return
        self.go(ctx, t.x, t.y, dt, self.espec.speed * 0.6)

    def _lunge(self, ctx: AIContext, dt: float, length: float, speed: float,
               pause: float) -> None:
        from ..systems.collision import move_hull
        step = speed * dt
        x0, y0 = self.x, self.y
        self.x, self.y, bx, by = move_hull(ctx.world, self.x, self.y, 0.0, self.half, self.half,
                                           math.cos(self.aim) * step, math.sin(self.aim) * step)
        moved = math.hypot(self.x - x0, self.y - y0)
        self._moved = moved
        self.walked += moved
        self.ran += moved
        if not self.struck:
            for a in ctx.actors:
                if a is self or not a.hittable:
                    continue
                if math.hypot(a.x - self.x, a.y - self.y) <= self.hit_radius + a.hit_radius:
                    _numbered_hit(a, self.espec.damage * self.damage_mult, self, self.aim, ctx)
                    self.struck = True
                    break
        if bx or by or self.ran >= length:
            self.lunges -= 1
            if self.lunges > 0:
                self.state, self.timer = "pause", pause
            else:
                self.state = "stalk"
                self.cooldown = self.espec.cooldown

    def _howl(self, ctx: AIContext, reach: float, slow: float, slow_t: float) -> None:
        ctx.effects.append(Effect("howl", self.x, self.y, size=reach))
        ctx.events.append("hex")
        for h in ctx.players:
            if h.alive and math.hypot(h.x - self.x, h.y - self.y) <= reach \
                    and hasattr(h, "slowed"):
                h.slowed(slow, slow_t)
