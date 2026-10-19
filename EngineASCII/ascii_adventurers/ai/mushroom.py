"""
ai/mushroom.py -- the mushroom biome's new enemies (P12, design/BOSSES.md
24.10). No red caps with white spots, ink pools or big spore bursts: those
belong to the Mycelium bosses.

Letter-art creatures on the plains' base (ai/plains.PlainsCreature), drawn
by render/plains.py with their tells from render/mushroom.py.

  sporelings (swarms), shroomlings (small groups), mold zombies: simple
                  chasers; fungus gnats fly in clouds (ai/forest.Bat)
  myconid shaman  keeps back; puffs pollen clouds where its allies are --
                  enemies in a cloud heal
  cordyceps hunter an archer with spore darts; dead, it bursts into two
                  sporelings
  fungal brute (elite) a heavy hitter that regrows fast unless it was hit in
                  the last few seconds
  rootweaver      keeps back; sends a line of cracks racing at you, roots
                  bursting up along it
  giant snail     slow; its shell takes half of what hits it from behind; it
                  leaves a slime trail that slows
  pillbug         rests, then rolls up and rolls at you (barely hurt while
                  rolled), bouncing off walls
  mantis (elite)  leaps to you, raises both scythes, X-slashes
  fairy ring      a ring of little caps: a hero inside and sporelings rise;
                  break three caps to undo it
  mold core       spreads mold patches that hurt; break it and they wither
"""

from __future__ import annotations

import math

from .. import config
from ..entities.effects import Effect
from ..systems import combat
from ..systems.collision import move_hull
from ..systems.zones import Zone
from .brain import AIContext
from .creatures import _numbered_hit
from .desert import _dash
from .forest import _keep_range, _roam, _vanish
from .plains import Chaser, PlainsCreature
from .shooters import Archer


class Myconid(PlainsCreature):
    """Keeps POLLEN[0] from the heroes. Every cooldown, with hurt allies
    about, it puffs a pollen cloud (a "pollen" zone: POLLEN[1] tiles,
    POLLEN[2] s) on the most hurt one: enemies in it heal POLLEN[3] of
    their max HP every POLLEN[4] s."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.timer = self.rng.uniform(1.0, self.espec.cooldown)

    def think(self, ctx: AIContext, dt: float) -> None:
        super().think(ctx, dt)
        self.sense(ctx, dt)
        keep, radius, life, share, every = config.POLLEN
        t = self.target
        if t is not None and self.sees_target:
            _keep_range(self, ctx, t, keep * 0.8, keep * 1.3, dt)
        else:
            _roam(self, ctx, dt)
        self.timer -= dt
        if self.timer > 0 or ctx.zones is None:
            return
        hurt = [a for a in ctx.actors if getattr(a, "faction", "") == "enemy" and a.alive
                and a.hp < a.max_hp and not getattr(a, "boss", False)
                and math.hypot(a.x - self.x, a.y - self.y) <= 12]
        if not hurt:
            return
        self.timer = self.espec.cooldown
        w = min(hurt, key=lambda a: a.hp / a.max_hp)
        ctx.zones.append(Zone("pollen", w.x, w.y, radius, life, every, 0.0, self, heal=share))
        ctx.events.append("chime")


class CordycepsHunter(Archer):
    """An archer with spore darts; dead, its stalk bursts: two sporelings."""

    def on_death(self, ctx: AIContext) -> None:
        ctx.effects.append(Effect("explosion", self.x, self.y))
        for side in (-1, 1):
            ctx.spawned.append(("sporeling", self.x + side * 0.7, self.y + 0.3))


class FungalBrute(Chaser):
    """Elite. A heavy chaser that regrows REGROW[1] of its max HP a second
    once REGROW[0] s have passed since it was last hit."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.unhit = 0.0

    @property
    def regrowing(self) -> bool:
        return self.unhit >= config.REGROW[0] and self.hp < self.max_hp

    def take_damage(self, amount, source, from_angle):
        dealt = super().take_damage(amount, source, from_angle)
        if dealt > 0:
            self.unhit = 0.0
        return dealt

    def think(self, ctx: AIContext, dt: float) -> None:
        self.unhit += dt
        if self.regrowing and not (self.status is not None and self.status.wounded):
            self.hp = min(float(self.max_hp), self.hp + self.max_hp * config.REGROW[1] * dt)
        super().think(ctx, dt)


class Rootweaver(PlainsCreature):
    """Keeps ROOTS[0] back. Every cooldown it sends roots at its target: a
    crack runs along the ground from it toward where the target is, out to
    ROOTS[1] tiles at ROOTS[2] tiles/s (stopped by walls); every ROOTS[3]
    tiles of it a root bursts up ROOTS[4] s after the crack gets there,
    hurting what's within ROOTS[5] of it."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.timer = self.rng.uniform(1.5, self.espec.cooldown)
        self.roots: list[list] = []        # [x, y, s to the crack, s to the burst]

    def think(self, ctx: AIContext, dt: float) -> None:
        super().think(ctx, dt)
        self.sense(ctx, dt)
        keep, length, speed, gap, delay, width = config.ROOTS
        for r in self.roots:
            r[2] -= dt
            r[3] -= dt
            if r[3] <= 0 < r[3] + dt:
                combat.blast(r[0], r[1], width, self.espec.damage * self.damage_mult, self,
                             ctx.actors, effects=ctx.effects, ground=True)
                ctx.effects.append(Effect("eruption", r[0], r[1]))
        self.roots = [r for r in self.roots if r[3] > -0.4]
        t = self.target
        if t is None or not self.sees_target:
            _roam(self, ctx, dt)
            return
        _keep_range(self, ctx, t, keep * 0.8, keep * 1.3, dt)
        self.timer -= dt
        if self.timer <= 0 and not self.roots:
            self.timer = self.espec.cooldown
            a = self.angle_to(t.x, t.y)
            from .desert import _reach
            reach = _reach(ctx, self.x, self.y, a, length)
            k = 1
            while k * gap <= reach:
                d = k * gap
                self.roots.append([self.x + math.cos(a) * d, self.y + math.sin(a) * d,
                                   d / speed, d / speed + delay])
                k += 1
            ctx.events.append("zap")


class GiantSnail(Chaser):
    """A slow chaser. Hits from behind land on its shell: x SNAIL[0]. While
    it moves it leaves slime (a zone every SNAIL[1] s that slows to x
    SNAIL[2] for SNAIL[3] s)."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.slime = self.rng.uniform(0.2, config.SNAIL[1])

    def take_damage(self, amount, source, from_angle):
        if from_angle is not None:
            came_from = from_angle + math.pi
            if abs((came_from - self.facing + math.pi) % math.tau - math.pi) > math.pi / 2:
                amount *= config.SNAIL[0]                 # (from behind: the shell)
        return super().take_damage(amount, source, from_angle)

    def think(self, ctx: AIContext, dt: float) -> None:
        super().think(ctx, dt)
        shell, every, slow, life = config.SNAIL
        if self.moving and ctx.zones is not None:
            self.slime -= dt
            if self.slime <= 0:
                self.slime = every
                ctx.zones.append(Zone("slime", self.x, self.y, 0.9, life, 0.1, 0.0, self,
                                      slow=slow))


class Pillbug(PlainsCreature):
    """Rests PILLBUG[0] s (uncurled: hit it now), curls up (the windup),
    then rolls at its target at PILLBUG[1] tiles/s for PILLBUG[2] s,
    bouncing off walls, bumping whoever it hits (once per PILLBUG[4] s
    each). Rolled up, hits on it do x PILLBUG[3]."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.state = "rest"
        self.timer = self.rng.uniform(0.5, config.PILLBUG[0])
        self.aim = 0.0
        self.bumped: dict[int, float] = {}
        self.clock = 0.0

    @property
    def rolled(self) -> bool:
        return self.state in ("curl", "roll")

    def sprite_now(self) -> str:
        return "pillbug_ball" if self.rolled else "pillbug"

    def take_damage(self, amount, source, from_angle):
        if self.rolled:
            amount *= config.PILLBUG[3]
        return super().take_damage(amount, source, from_angle)

    def think(self, ctx: AIContext, dt: float) -> None:
        super().think(ctx, dt)
        self.sense(ctx, dt)
        rest, speed, roll, rolled, every = config.PILLBUG
        self.clock += dt
        t = self.target
        if self.state == "rest":
            self.timer -= dt
            if t is not None and self.sees_target:
                self.facing = self.angle_to(t.x, t.y)
                if self.timer <= 0:
                    self.state, self.timer = "curl", self.espec.windup
            else:
                _roam(self, ctx, dt)
            return
        if self.state == "curl":
            self.timer -= dt
            self.tell = self.timer
            if self.timer <= 0:
                self.tell = 0.0
                self.aim = self.angle_to(t.x, t.y) if t is not None else self.facing
                self.state, self.timer = "roll", roll
            return
        # Rolling.
        self.timer -= dt
        step = speed * dt
        x0, y0 = self.x, self.y
        self.x, self.y, bx, by = move_hull(ctx.world, self.x, self.y, 0.0, self.half, self.half,
                                           math.cos(self.aim) * step, math.sin(self.aim) * step)
        if bx:
            self.aim = math.pi - self.aim
        if by:
            self.aim = -self.aim
        self.facing = self.aim
        self._moved = math.hypot(self.x - x0, self.y - y0)
        self.walked += self._moved
        for a in ctx.actors:
            if a is self or not a.hittable or combat.drafting(a):
                continue
            if math.hypot(a.x - self.x, a.y - self.y) <= self.hit_radius + a.hit_radius \
                    and self.clock - self.bumped.get(id(a), -99.0) >= every:
                self.bumped[id(a)] = self.clock
                _numbered_hit(a, self.espec.damage * self.damage_mult, self, self.aim, ctx)
        if self.timer <= 0:
            self.state, self.timer = "rest", rest


class Mantis(PlainsCreature):
    """Elite. Within attack_radius: crouches (the windup; the line shows),
    leaps to where its target was at MANTIS[0] tiles/s, raises both
    scythes MANTIS[1] s (the tell), then slashes twice in an X (radius
    MANTIS[2] in front, MANTIS[3] s apart)."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.state = "stalk"
        self.timer = 0.0
        self.aim = 0.0
        self.goal = (0.0, 0.0)
        self.slashes = 0

    def think(self, ctx: AIContext, dt: float) -> None:
        super().think(ctx, dt)
        self.sense(ctx, dt)
        speed, raise_t, radius, gap = config.MANTIS
        t = self.target
        if self.state == "crouch":
            self.timer -= dt
            self.tell = self.timer
            if self.timer <= 0:
                self.state, self.tell = "leap", 0.0
            return
        if self.state == "leap":
            d = math.hypot(self.goal[0] - self.x, self.goal[1] - self.y)
            _, blocked = _dash(self, ctx, self.aim, speed, dt)
            if blocked or d <= 1.0:
                self.state, self.timer = "scythes", raise_t
            return
        if self.state == "scythes":
            self.timer -= dt
            self.tell = self.timer
            if t is not None:
                self.facing = self.angle_to(t.x, t.y)
            if self.timer <= 0:
                self.state, self.slashes, self.timer, self.tell = "slash", 2, 0.0, 0.0
            return
        if self.state == "slash":
            self.timer -= dt
            if self.timer <= 0:
                cx = self.x + math.cos(self.facing) * 1.0
                cy = self.y + math.sin(self.facing) * 1.0
                combat.blast(cx, cy, radius, self.espec.damage * self.damage_mult, self,
                             ctx.actors, effects=ctx.effects)
                side = 0.6 if self.slashes == 2 else -0.6
                ctx.effects.append(Effect("slash", cx, cy, self.facing + side))
                ctx.events.append(combat.HIT)
                self.slashes -= 1
                self.timer = gap
                if self.slashes <= 0:
                    self.state = "stalk"
                    self.cooldown = self.espec.cooldown
            return
        if t is None or not self.sees_target:
            _roam(self, ctx, dt)
            return
        if self.cooldown <= 0 and self.dist_to(t) <= self.espec.attack_radius:
            self.aim = self.facing = self.angle_to(t.x, t.y)
            self.goal = (t.x, t.y)
            self.state, self.timer = "crouch", self.espec.windup
            return
        self.go(ctx, t.x, t.y, dt, self.espec.speed)


class FairyRing(PlainsCreature):
    """A ring of FAIRY[0] little caps (FAIRY[1] tiles round its middle; the
    middle itself is just a place). On its first turn it grows them.
    While a hero is inside, a sporeling rises in the middle every FAIRY[3]
    s (at most FAIRY[4] about). Break FAIRY[2] caps and it's undone: the
    rest wither, and the ring counts as killed by whoever broke the last."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.caps: list = []
        self.grown = False
        self.timer = 1.0

    @property
    def hittable(self) -> bool:
        return False

    def think(self, ctx: AIContext, dt: float) -> None:
        super().think(ctx, dt)
        n, radius, need, every, most = config.FAIRY
        if not self.grown:
            self.grown = True
            from . import make_enemy
            for k in range(n):
                a = k * math.tau / n
                c = make_enemy("fairy_cap", self.x + math.cos(a) * radius,
                               self.y + math.sin(a) * radius * 0.8, self.rng)
                c.part_of = self
                self.caps.append(c)
                ctx.spawned.append(c)
            return
        broken = [c for c in self.caps if not c.alive]
        if len(broken) >= need:
            for c in self.caps:
                if c.alive:
                    _vanish(c)
            self.last_hit_by = broken[-1].last_hit_by
            self.hp = 0.0
            return
        if not any(h.alive and math.hypot(h.x - self.x, h.y - self.y) <= radius
                   for h in ctx.players):
            return
        self.timer -= dt
        if self.timer <= 0:
            self.timer = every
            near = sum(1 for a in ctx.actors if getattr(a, "kind_key", "") == "sporeling"
                       and math.hypot(a.x - self.x, a.y - self.y) <= radius + 6)
            if near < most:
                ctx.spawned.append(("sporeling", self.x, self.y))
                ctx.effects.append(Effect("burrow", self.x, self.y))

    def on_death(self, ctx: AIContext) -> None:
        ctx.effects.append(Effect("toast", self.x, self.y - 1, label="THE RING IS BROKEN"))


class FairyCap(PlainsCreature):
    """One cap of a fairy ring: never moves."""

    def on_death(self, ctx: AIContext) -> None:
        ctx.effects.append(Effect("fizzle", self.x, self.y))


class MoldCore(PlainsCreature):
    """Never moves. Every MOLD[0] s, while it has fewer than MOLD[1], it
    spreads a mold patch within MOLD[2] tiles (a zone of MOLD[3] tiles
    doing MOLD[4] every MOLD[5] s to anyone in it, lasting MOLD_LIFE s --
    so a core gone to sleep doesn't leave them forever). Break it and its
    patches wither."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.timer = 0.5
        self.patches: list = []

    def think(self, ctx: AIContext, dt: float) -> None:
        super().think(ctx, dt)
        self.sense(ctx, dt)
        every, most, reach, radius, damage, tick = config.MOLD
        self.patches = [z for z in self.patches if z.age < z.life]
        self.timer -= dt
        if self.timer > 0 or ctx.zones is None or len(self.patches) >= most:
            return
        self.timer = every
        a = self.rng.uniform(0, math.tau)
        r = self.rng.uniform(1.5, reach)
        z = Zone("mold", self.x + math.cos(a) * r, self.y + math.sin(a) * r, radius,
                 config.MOLD_LIFE, tick, damage, self)
        self.patches.append(z)
        ctx.zones.append(z)

    def on_death(self, ctx: AIContext) -> None:
        ctx.effects.append(Effect("explosion", self.x, self.y))
        for z in self.patches:                      # they wither
            z.life = z.age
        self.patches = []
