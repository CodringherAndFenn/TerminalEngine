"""
ai/desert.py -- the desert's new enemies (P9, design/BOSSES.md 24.7).

Letter-art creatures on the plains' base (ai/plains.PlainsCreature), drawn
by render/plains.py with their tells from render/desert.py.

  fire ants (swarms), dried husks, desert jackals: simple chasers
  sand imp        a chaser that comes in hops
  scorpion (elite) armoured in front; two pincer snaps, then the tail rises
                  and stabs a long line
  vulture         circles high (a hawk's dive), but only dives at heroes
                  under VULTURE_HUNGRY of their HP
  basilisk        darts about; flares its frill and stares down a line:
                  heroes in it are turned to stone for a moment
  rattlesnake     lies coiled; rattles when you're close, strikes, slithers
                  off
  mummy (elite)   its bandages lash out along a line and drag the first hero
                  in for a heavy blow (a roll breaks free)
  fire dancer     closes in weaving, leaving burning patches; breathes a cone
                  of flame
  dune raider     hit and run: waits at range, dashes in, slashes twice,
                  dashes back out
  tumbleweed      rolls with the wind in a straight line, bouncing off walls,
                  hurting what it bumps into
  cactus golem    a slow chaser; every hit it takes, it shoots spines all
                  round (a volley at most every CACTUS[1] s)
  djinn lamp      floats at range; its sand vortex drags heroes toward it,
                  and it zaps those close

The glass mage is an archer with its own body: its shards glance off
walls (ShellSpec.bounces).
"""

from __future__ import annotations

import math

from .. import config
from ..entities.effects import Effect
from ..entities.projectile import Projectile
from ..systems import combat
from ..systems.collision import move_hull
from ..systems.raycast import first_hit
from ..systems.zones import Zone
from .brain import AIContext
from .creatures import _numbered_hit
from .forest import _keep_range, _roam
from .plains import Chaser, Hawk, PlainsCreature


def _on_line(a, x0: float, y0: float, angle: float, length: float, width: float) -> bool:
    """Is actor `a` within `width` (+ its body) of the segment from (x0, y0)?"""
    dx, dy = math.cos(angle), math.sin(angle)
    t = max(0.0, min(length, (a.x - x0) * dx + (a.y - y0) * dy))
    return math.hypot(a.x - (x0 + dx * t), a.y - (y0 + dy * t)) <= width + a.hit_radius


def _reach(ctx: AIContext, x0: float, y0: float, angle: float, length: float) -> float:
    """How far a line from (x0, y0) gets before a wall (tiles)."""
    hit = first_hit(ctx.world.tile_at, x0, y0, x0 + math.cos(angle) * length,
                    y0 + math.sin(angle) * length)
    return length if hit is None else length * hit.t


def _dash(e, ctx: AIContext, angle: float, speed: float, dt: float) -> tuple[float, bool]:
    """Move straight along `angle`; returns (distance moved, blocked)."""
    step = speed * dt
    x0, y0 = e.x, e.y
    e.x, e.y, bx, by = move_hull(ctx.world, e.x, e.y, 0.0, e.half, e.half,
                                 math.cos(angle) * step, math.sin(angle) * step)
    moved = math.hypot(e.x - x0, e.y - y0)
    e._moved = moved
    e.walked += moved
    return moved, bx or by


# --- Simple chasers -------------------------------------------------------------------


class Hopper(Chaser):
    """A chaser that comes in hops: HOP[0] s moving, HOP[1] s still."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.hop = self.rng.uniform(0, sum(config.HOP))

    def go(self, ctx, gx, gy, dt, speed):
        self.hop = (self.hop + dt) % sum(config.HOP)
        if self.hop > config.HOP[0]:
            self._moved = 0.0
            return False
        return super().go(ctx, gx, gy, dt, speed)


# --- Beasts ----------------------------------------------------------------------------


class Scorpion(PlainsCreature):
    """Elite. Hits on its front do x SCORPION[0]. In reach: SCORPION[1]
    pincer snaps (the spec's windup each, SCORPION[2] s apart), then the
    tail rises SCORPION[3] s (its line shows) and stabs SCORPION[4] tiles
    ahead."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.snaps = 0
        self.gap = 0.0
        self.tail = 0.0

    def take_damage(self, amount, source, from_angle):
        if from_angle is not None and not getattr(source, "spectral", False):
            came_from = from_angle + math.pi            # (Ghostwood +6: darts go through)
            if abs((came_from - self.facing + math.pi) % math.tau - math.pi) < math.pi / 2:
                amount *= config.SCORPION[0]
        return super().take_damage(amount, source, from_angle)

    def think(self, ctx: AIContext, dt: float) -> None:
        super().think(ctx, dt)
        self.sense(ctx, dt)
        front, snaps, gap, rise, reach = config.SCORPION
        if self.tail > 0:
            self.tail -= dt
            self.tell = self.tail
            if self.tail <= 0:
                self.tell = 0.0
                self._stab(ctx, reach)
            return
        if self.snaps > 0:
            self.gap -= dt
            if self.gap <= 0:
                self._snap(ctx)
                self.snaps -= 1
                self.gap = gap
                if self.snaps == 0:
                    self.tail = rise
            return
        if self.windup > 0:
            self.windup -= dt
            self.tell = self.windup
            if self.windup <= 0:
                self.tell = 0.0
                self.snaps = snaps
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

    def _snap(self, ctx: AIContext) -> None:
        cx = self.x + math.cos(self.facing) * 1.1
        cy = self.y + math.sin(self.facing) * 1.1
        combat.blast(cx, cy, 1.1, self.espec.damage * self.damage_mult, self, ctx.actors,
                     effects=ctx.effects)
        ctx.effects.append(Effect("slash", cx, cy, self.facing))
        ctx.events.append(combat.HIT)

    def _stab(self, ctx: AIContext, reach: float) -> None:
        length = _reach(ctx, self.x, self.y, self.facing, reach)
        for a in ctx.actors:
            if a is self or not a.hittable:
                continue
            if _on_line(a, self.x, self.y, self.facing, length, 0.4):
                _numbered_hit(a, self.espec.damage * 1.6 * self.damage_mult, self, self.facing,
                              ctx)
        ctx.effects.append(Effect("impact", self.x + math.cos(self.facing) * length,
                                  self.y + math.sin(self.facing) * length, self.facing))
        self.cooldown = self.espec.cooldown


class Vulture(Hawk):
    """A hawk that waits: it circles high until its target is under
    VULTURE_HUNGRY of its HP, and only then lines up and dives."""

    def think(self, ctx: AIContext, dt: float) -> None:
        t = self.target
        hungry = t is not None and t.max_hp and t.hp / t.max_hp < config.VULTURE_HUNGRY
        if self.state == "circle" and not hungry:
            self.timer = max(self.timer, 0.3)           # (keeps circling)
        super().think(ctx, dt)


class Basilisk(PlainsCreature):
    """Darts about at BASILISK[2] tiles from its target, to a new spot every
    BASILISK[1] s. Every cooldown it stops, flares its frill (the windup;
    the line shows) and stares down the line (attack_radius, to a wall):
    heroes in it take its damage and are stone for BASILISK[0] s."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.aim = 0.0
        self.spot = None
        self.dart = 0.0
        self.gaze_t = self.rng.uniform(1.5, self.espec.cooldown)

    def think(self, ctx: AIContext, dt: float) -> None:
        super().think(ctx, dt)
        self.sense(ctx, dt)
        stone, every, keep = config.BASILISK
        if self.windup > 0:
            self.windup -= dt
            self.tell = self.windup
            if self.windup <= 0:
                self.tell = 0.0
                self._gaze(ctx, stone)
            return
        t = self.target
        if t is None or not self.sees_target:
            _roam(self, ctx, dt)
            return
        self.gaze_t -= dt
        if self.gaze_t <= 0:
            self.gaze_t = self.espec.cooldown
            self.aim = self.facing = self.angle_to(t.x, t.y)
            self.windup = self.espec.windup
            return
        self.dart -= dt
        if self.spot is None or self.dart <= 0:
            a = self.rng.uniform(0, math.tau)
            self.spot = (t.x + math.cos(a) * keep, t.y + math.sin(a) * keep)
            self.dart = every
        self.go(ctx, *self.spot, dt, self.espec.speed)

    def _gaze(self, ctx: AIContext, stone: float) -> None:
        length = _reach(ctx, self.x, self.y, self.aim, self.espec.attack_radius)
        ctx.effects.append(Effect("gaze", self.x, self.y, x2=self.x + math.cos(self.aim) * length,
                                  y2=self.y + math.sin(self.aim) * length))
        for h in ctx.players:
            if h.alive and _on_line(h, self.x, self.y, self.aim, length, 0.3):
                _numbered_hit(h, self.espec.damage * self.damage_mult, self, self.aim, ctx)
                if hasattr(h, "petrify"):
                    h.petrify(stone)
                    ctx.effects.append(Effect("toast", h.x, h.y - 2, label="STONE!"))
                    ctx.effects.append(Effect("stone", h.x, h.y))


class Rattlesnake(PlainsCreature):
    """Lies coiled. A hero within attack_radius it can see: it rattles (the
    windup), strikes SNAKE[0] tiles at SNAKE[1] tiles/s (once per strike),
    then slithers off SNAKE[2] s before coiling again."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.state = "coiled"
        self.timer = 0.0
        self.aim = 0.0
        self.ran = 0.0
        self.struck = False

    def think(self, ctx: AIContext, dt: float) -> None:
        super().think(ctx, dt)
        self.sense(ctx, dt)
        length, speed, away = config.SNAKE
        t = self.target
        if self.state == "rattle":
            self.timer -= dt
            self.tell = self.timer
            if t is not None:
                self.aim = self.facing = self.angle_to(t.x, t.y)
            if self.timer <= 0:
                self.state, self.ran, self.struck, self.tell = "strike", 0.0, False, 0.0
            return
        if self.state == "strike":
            moved, blocked = _dash(self, ctx, self.aim, speed, dt)
            self.ran += moved
            if not self.struck:
                for a in ctx.actors:
                    if a is not self and a.hittable and \
                            math.hypot(a.x - self.x, a.y - self.y) <= self.hit_radius + a.hit_radius:
                        _numbered_hit(a, self.espec.damage * self.damage_mult, self, self.aim, ctx)
                        self.struck = True
                        break
            if blocked or self.ran >= length:
                self.state, self.timer = "away", away
            return
        if self.state == "away":
            self.timer -= dt
            a = self.aim + math.pi
            self.go(ctx, self.x + math.cos(a) * 3, self.y + math.sin(a) * 3, dt, self.espec.speed)
            if self.timer <= 0:
                self.state = "coiled"
                self.cooldown = self.espec.cooldown
            return
        if t is not None and self.sees_target and self.cooldown <= 0 \
                and self.dist_to(t) <= self.espec.attack_radius:
            self.state, self.timer = "rattle", self.espec.windup
            ctx.events.append("zap")


# --- Folk ---------------------------------------------------------------------------


class Mummy(PlainsCreature):
    """Elite. Walks you down slowly. Within attack_radius it unwinds its
    bandages (the windup; the line shows) and lashes them out along the
    line (to a wall): the first hero on it is dragged toward it at
    MUMMY[0] tiles/s (at most MUMMY[1] s, until within MUMMY[2] tiles, or
    until the hero rolls free), then MUMMY[3] s later a blow of MUMMY[4]
    tiles round it."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.aim = 0.0
        self.pulling = None
        self.pull_t = 0.0
        self.blow = 0.0

    def think(self, ctx: AIContext, dt: float) -> None:
        super().think(ctx, dt)
        self.sense(ctx, dt)
        speed, longest, close, delay, radius = config.MUMMY
        if self.blow > 0:
            self.blow -= dt
            self.tell = self.blow
            if self.blow <= 0:
                self.tell = 0.0
                combat.blast(self.x, self.y, radius, self.espec.damage * self.damage_mult, self,
                             ctx.actors, effects=ctx.effects)
                ctx.effects.append(Effect("slash", self.x, self.y, self.facing))
                ctx.events.append(combat.HIT)
                self.cooldown = self.espec.cooldown
            return
        if self.pulling is not None:
            h = self.pulling
            self.pull_t -= dt
            d = self.dist_to(h)
            if not h.alive or getattr(h, "rolling", False) or self.pull_t <= 0 or d <= close:
                self.pulling = None
                self.blow = delay
                return
            step = min(d - close, speed * dt)
            combat.push(h, ctx.world, (self.x - h.x) / d * step, (self.y - h.y) / d * step)
            self.facing = self.angle_to(h.x, h.y)
            return
        if self.windup > 0:
            self.windup -= dt
            self.tell = self.windup
            if self.windup <= 0:
                self.tell = 0.0
                self._lash(ctx, longest)
            return
        t = self.target
        if t is None or not self.sees_target:
            _roam(self, ctx, dt)
            return
        if self.dist_to(t) <= self.espec.attack_radius and self.cooldown <= 0:
            self.aim = self.facing = self.angle_to(t.x, t.y)
            self.windup = self.espec.windup
            return
        self.go(ctx, t.x, t.y, dt, self.espec.speed)

    def _lash(self, ctx: AIContext, longest: float) -> None:
        length = _reach(ctx, self.x, self.y, self.aim, self.espec.attack_radius)
        ctx.effects.append(Effect("gaze", self.x, self.y, x2=self.x + math.cos(self.aim) * length,
                                  y2=self.y + math.sin(self.aim) * length, value=1))
        caught = [h for h in ctx.players if h.alive and h.hittable
                  and _on_line(h, self.x, self.y, self.aim, length, 0.35)]
        if caught:
            self.pulling = min(caught, key=lambda h: self.dist_to(h))
            self.pull_t = longest
        else:
            self.cooldown = self.espec.cooldown * 0.5


class FireDancer(PlainsCreature):
    """Closes in to DANCER[0] tiles, weaving, and drops a burning patch every
    DANCER[1] s on the way (FIRE_PATCH; DANCER[3] s each). In range it
    breathes in (the windup) and breathes a DANCER[2]-degree cone of
    flame out to attack_radius."""

    wobble = 0.5

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.patch = self.rng.uniform(0.3, config.DANCER[1])

    def think(self, ctx: AIContext, dt: float) -> None:
        super().think(ctx, dt)
        self.sense(ctx, dt)
        close, every, cone, life = config.DANCER
        t = self.target
        if self.windup > 0:
            self.windup -= dt
            self.tell = self.windup
            if t is not None:
                self.facing = self.angle_to(t.x, t.y)
            if self.windup <= 0:
                self.tell = 0.0
                self._breathe(ctx, math.radians(cone) / 2)
            return
        if t is None or not self.sees_target:
            _roam(self, ctx, dt)
            return
        if self.dist_to(t) > close:
            self.go(ctx, t.x, t.y, dt, self.espec.speed)
            self.patch -= dt
            if self.patch <= 0 and ctx.zones is not None:
                self.patch = every
                damage, tick = config.FIRE_PATCH
                ctx.zones.append(Zone("trail", self.x, self.y, 0.9, life, tick, damage, self,
                                      (config.STATUSES["burn"].tag,), "burn"))
        elif self.cooldown <= 0:
            self.facing = self.angle_to(t.x, t.y)
            self.windup = self.espec.windup

    def _breathe(self, ctx: AIContext, half: float) -> None:
        reach = self.espec.attack_radius
        ctx.effects.append(Effect("flames", self.x, self.y, self.facing, size=reach))
        ctx.events.append("hex")
        for a in ctx.actors:
            if a is self or not a.hittable:
                continue
            d = math.hypot(a.x - self.x, a.y - self.y)
            ang = math.atan2(a.y - self.y, a.x - self.x)
            off = abs((ang - self.facing + math.pi) % math.tau - math.pi)
            if d <= reach + a.hit_radius and (d <= a.hit_radius or off <= half):
                _numbered_hit(a, self.espec.damage * self.damage_mult, self, ang, ctx)
        self.cooldown = self.espec.cooldown


class DuneRaider(PlainsCreature):
    """Hit and run: waits at RAIDER[0] tiles for RAIDER[1] s (circling a
    little), dashes in at RAIDER[2] tiles/s, slashes twice (RAIDER[3] s
    apart; a short windup first), then dashes back out to RAIDER[0]."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.state = "wait"
        self.timer = self.rng.uniform(0.5, config.RAIDER[1])
        self.slashes = 0
        self.side = self.rng.choice((-1, 1))

    def think(self, ctx: AIContext, dt: float) -> None:
        super().think(ctx, dt)
        self.sense(ctx, dt)
        keep, wait, dash, gap = config.RAIDER
        t = self.target
        if t is None or not self.sees_target:
            self.state = "wait"
            _roam(self, ctx, dt)
            return
        if self.state == "wait":
            a = self.angle_to(t.x, t.y) + math.pi + self.side * 0.4
            self.go(ctx, t.x + math.cos(a) * keep, t.y + math.sin(a) * keep, dt,
                    self.espec.speed * 0.6)
            self.timer -= dt
            if self.timer <= 0:
                self.state = "in"
        elif self.state == "in":
            self.facing = self.angle_to(t.x, t.y)
            _, blocked = _dash(self, ctx, self.facing, dash, dt)
            if self.dist_to(t) <= self.espec.attack_radius + t.hit_radius:
                self.state, self.windup, self.slashes = "slash", self.espec.windup, 2
            elif blocked:
                self.state, self.timer = "wait", wait
        elif self.state == "slash":
            self.windup -= dt
            self.tell = max(0.0, self.windup)
            if self.windup <= 0:
                cx = self.x + math.cos(self.facing) * 0.8
                cy = self.y + math.sin(self.facing) * 0.8
                combat.blast(cx, cy, self.espec.attack_radius * 0.7,
                             self.espec.damage * self.damage_mult, self, ctx.actors,
                             effects=ctx.effects)
                ctx.effects.append(Effect("slash", cx, cy, self.facing))
                ctx.events.append(combat.HIT)
                self.slashes -= 1
                self.windup = gap
                if self.slashes <= 0:
                    self.state, self.tell = "out", 0.0
        elif self.state == "out":
            a = self.angle_to(t.x, t.y) + math.pi
            _, blocked = _dash(self, ctx, a, dash * 0.85, dt)
            self.facing = a
            if blocked or self.dist_to(t) >= keep:
                self.state, self.timer = "wait", wait
                self.side = -self.side


# --- Odd ones ---------------------------------------------------------------------------


class Tumbleweed(PlainsCreature):
    """Rolls with the wind (TUMBLE_WIND, +- a little each), bouncing off
    walls, hurting any body it bumps into (once per TUMBLE_EVERY s each).
    It pays no attention to anyone."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.facing = config.TUMBLE_WIND + self.rng.uniform(-0.35, 0.35)
        self.bumped: dict[int, float] = {}
        self.clock = 0.0

    def think(self, ctx: AIContext, dt: float) -> None:
        super().think(ctx, dt)
        self.clock += dt
        step = self.espec.speed * dt
        x0, y0 = self.x, self.y
        self.x, self.y, bx, by = move_hull(ctx.world, self.x, self.y, 0.0, self.half, self.half,
                                           math.cos(self.facing) * step,
                                           math.sin(self.facing) * step)
        if bx:
            self.facing = math.pi - self.facing
        if by:
            self.facing = -self.facing
        self._moved = math.hypot(self.x - x0, self.y - y0)
        self.walked += self._moved
        for a in ctx.actors:
            if a is self or not a.hittable or getattr(a, "kind_key", "") == "tumbleweed" \
                    or combat.drafting(a):
                continue
            if math.hypot(a.x - self.x, a.y - self.y) <= self.hit_radius + a.hit_radius \
                    and self.clock - self.bumped.get(id(a), -99.0) >= config.TUMBLE_EVERY:
                self.bumped[id(a)] = self.clock
                _numbered_hit(a, self.espec.damage * self.damage_mult, self, self.facing, ctx)


class CactusGolem(Chaser):
    """A slow chaser whose every hit taken makes it shoot CACTUS[0] spines
    all round (at most a volley every CACTUS[1] s)."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.spines_due = False
        self.spine_cd = 0.0

    def take_damage(self, amount, source, from_angle):
        dealt = super().take_damage(amount, source, from_angle)
        if dealt > 0:
            self.spines_due = True
        return dealt

    def think(self, ctx: AIContext, dt: float) -> None:
        self.spine_cd = max(0.0, self.spine_cd - dt)
        if self.spines_due and self.spine_cd <= 0:
            self.spines_due = False
            self.spine_cd = config.CACTUS[1]
            shell = config.WEAPONS["cactus_spines"].shell
            n = config.CACTUS[0]
            turn = self.rng.uniform(0, math.tau / n)
            for k in range(n):
                ctx.projectiles.append(Projectile(self.x, self.y, turn + k * math.tau / n, shell,
                                                  owner=self,
                                                  damage=shell.damage * self.damage_mult))
            ctx.events.append(shell.sound)
        super().think(ctx, dt)


class DjinnLamp(PlainsCreature):
    """Floats at LAMP[0] tiles from its target. Heroes within LAMP[1] are
    dragged toward it at LAMP[2] tiles/s; within LAMP[3] it zaps them
    (its damage, every LAMP[4] s)."""

    flies = True

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.spin = 0.0
        self.zap = 0.0

    def can_see(self, world, other) -> bool:
        return math.hypot(other.x - self.x, other.y - self.y) <= self.espec.sight

    def think(self, ctx: AIContext, dt: float) -> None:
        super().think(ctx, dt)
        self.sense(ctx, dt)
        keep, radius, pull, reach, every = config.LAMP
        self.spin += dt
        self.zap = max(0.0, self.zap - dt)
        t = self.target
        if t is None or not self.alert:
            _roam(self, ctx, dt)
        elif self.dist_to(t) > keep:
            self.go(ctx, t.x, t.y, dt, self.espec.speed)
        for h in ctx.players:
            if not h.alive or getattr(h, "rolling", False):
                continue
            d = math.hypot(h.x - self.x, h.y - self.y)
            if d <= radius and d > 0.6:
                step = min(d - 0.6, pull * dt)
                combat.push(h, ctx.world, (self.x - h.x) / d * step, (self.y - h.y) / d * step)
            if d <= reach and self.zap <= 0:
                self.zap = every
                _numbered_hit(h, self.espec.damage * self.damage_mult, self,
                              math.atan2(h.y - self.y, h.x - self.x), ctx)
                ctx.effects.append(Effect("arc", self.x, self.y, x2=h.x, y2=h.y))
                ctx.events.append("zap")
