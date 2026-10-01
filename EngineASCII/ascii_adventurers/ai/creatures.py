"""
ai/creatures.py -- enemies without weapons: fallen warrior, spore puffer,
burrower, and (M12) thornback boar and dust devil.

Every attack is telegraphed (a wind-up the player can see) and hits an
area, so friendly fire applies: a puffer bursting next to a warrior hurts
the warrior too.
"""

from __future__ import annotations

import math
import random

from .. import config
from ..entities.actor import Actor
from ..entities.effects import Effect
from ..entities.projectile import Projectile
from ..specs import EnemySpec
from ..systems import combat
from ..systems.collision import hull_hits_solid, move_hull
from .brain import AIContext, Brain


class Creature(Brain, Actor):
    def __init__(self, spec: EnemySpec, x: float, y: float,
                 rng: random.Random, spawn_id=None) -> None:
        Actor.__init__(self, spec.max_hp, spec.size_px / 2 / config.TILE_PX_W + 0.15)
        self.x, self.y = x, y
        self.facing = rng.uniform(-math.pi, math.pi)   # world angle it looks at
        self.half = spec.size_px / 2                    # collision half-size, px
        self.init_brain(spec, rng, spawn_id)

    def walk(self, ctx: AIContext, gx: float, gy: float, dt: float, speed: float) -> bool:
        """Walk toward a goal with the clumsy steering; True once there."""
        if math.hypot(gx - self.x, gy - self.y) < 0.6:
            self.steering.note_intent(False)
            return True
        self.steering.note_intent(True)
        world = ctx.world

        def passable(px, py, heading):
            return not hull_hits_solid(world, px, py, 0.0, self.half, self.half)

        dx, dy = self.steering.direction(self.x, self.y, gx, gy, passable, dt,
                                         world=world, clearance=1)
        self.facing = math.atan2(dy, dx)
        self.x, self.y, _, _ = move_hull(
            world, self.x, self.y, 0.0, self.half, self.half, dx * speed * dt, dy * speed * dt
        )
        return False


class Warrior(Creature):
    """Fallen warrior (plains): an old armored war machine on foot. Charges
    in with occasional sidesteps and hesitations (never a straight line),
    then raises its blade (wind-up) and swings at whatever is in front."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.windup = 0.0        # >0 while the blade is raised
        self.swing = 0.0         # >0 for the moment after a swing (drawing)
        self.cooldown = 0.0
        self.juke = 0.0          # >0 while sidestepping
        self.juke_dir = 1
        self.juke_timer = self.rng.uniform(1.0, 2.5)

    def think(self, ctx: AIContext, dt: float) -> None:
        self.sense(ctx, dt)
        self.cooldown = max(0.0, self.cooldown - dt)
        self.swing = max(0.0, self.swing - dt)
        t = self.target
        if self.windup > 0:                 # committed: finish the swing
            self.windup -= dt
            if self.windup <= 0:
                self._strike(ctx)
            return
        if t is None or not self.alert:
            self.walk(ctx, *self.wander_goal(dt), dt, self.espec.speed * 0.4)
            return
        goal = (t.x, t.y) if self.sees_target else self.last_known
        if goal is None:
            return
        reach = self.espec.attack_radius + (t.hit_radius if self.sees_target else 0)
        if self.sees_target and self.dist_to(t) <= reach and self.cooldown <= 0:
            self.facing = self.angle_to(t.x, t.y)
            self.windup = self.espec.windup
            return
        # Approach with a sidestep now and then (dodgy, a bit erratic).
        self.juke_timer -= dt
        if self.juke > 0:
            self.juke -= dt
            a = self.angle_to(*goal) + self.juke_dir * math.pi / 2
            goal = (self.x + math.cos(a) * 3, self.y + math.sin(a) * 3)
        elif self.juke_timer <= 0:
            self.juke = self.rng.uniform(0.25, 0.5)
            self.juke_dir = self.rng.choice((-1, 1))
            self.juke_timer = self.rng.uniform(1.2, 3.0)
        self.walk(ctx, *goal, dt, self.espec.speed)

    def _strike(self, ctx: AIContext) -> None:
        cx = self.x + math.cos(self.facing) * 0.8
        cy = self.y + math.sin(self.facing) * 0.8
        combat.blast(cx, cy, self.espec.attack_radius * 0.75, self.espec.damage * self.damage_mult,
                     self, ctx.actors, effects=ctx.effects)
        ctx.effects.append(Effect("slash", cx, cy, self.facing))
        ctx.events.append(combat.HIT)
        self.swing = 0.15
        self.cooldown = self.espec.cooldown


class Puffer(Creature):
    """Spore puffer (mushroom): floats over everything, drifting toward the
    target with a lazy wobble. Close enough, it swells up (wind-up) and
    bursts in a spore cloud that hurts everything nearby. Shooting it pops
    it on the spot -- which also hurts anything next to it."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.swell = 0.0
        self.phase = self.rng.uniform(0, math.tau)
        self.burst_done = False

    @property
    def swelling(self) -> float:
        return min(1.0, self.swell / self.espec.windup) if self.swell > 0 else 0.0

    def think(self, ctx: AIContext, dt: float) -> None:
        self.sense(ctx, dt)
        self.phase += dt * 2.0
        t = self.target
        if self.swell > 0:
            self.swell += dt
            if self.swell >= self.espec.windup:
                self.burst(ctx)
            return
        if t is not None and self.sees_target:
            if self.dist_to(t) <= self.espec.attack_radius * 0.85:
                self.swell = 1e-6
                return
            gx, gy = t.x, t.y
            speed = self.espec.speed
        else:
            gx, gy = self.last_known or self.wander_goal(dt)
            speed = self.espec.speed * 0.6
        # Float straight at it (no collision), wobbling sideways.
        a = self.angle_to(gx, gy) + math.sin(self.phase) * 0.9
        self.facing = a
        self.x += math.cos(a) * speed * dt
        self.y += math.sin(a) * speed * dt

    def burst(self, ctx: AIContext) -> None:
        if self.burst_done:
            return
        self.burst_done = True
        combat.blast(self.x, self.y, self.espec.attack_radius, self.espec.damage * self.damage_mult,
                     self, ctx.actors, effects=ctx.effects)
        ctx.effects.append(Effect("spores", self.x, self.y))
        ctx.events.append(combat.BREAK)
        self.hp = 0.0

    def on_death(self, ctx: AIContext) -> None:
        self.burst(ctx)   # popped early: bursts where it is


class Burrower(Creature):
    """Burrower (desert): moves under the sand -- only a dust trail shows
    and it can't be hit. Near its target it stops, the ground rumbles
    (wind-up), then it bursts up hitting everything around, stays surfaced
    (vulnerable) for a moment, and dives again. It never leaves the desert:
    at the biome's edge it turns back."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.state = "under"        # under -> rumble -> up -> under
        self.timer = 0.0
        self.cooldown = 0.0
        self.trail_timer = 0.0

    @property
    def hittable(self) -> bool:
        return self.alive and self.state == "up"

    def think(self, ctx: AIContext, dt: float) -> None:
        self.sense(ctx, dt)
        self.cooldown = max(0.0, self.cooldown - dt)
        t = self.target
        if self.state == "rumble":
            self.timer -= dt
            if self.timer <= 0:
                self.state, self.timer = "up", 1.8
                combat.blast(self.x, self.y, self.espec.attack_radius,
                             self.espec.damage * self.damage_mult, self, ctx.actors, effects=ctx.effects)
                ctx.effects.append(Effect("eruption", self.x, self.y))
                ctx.events.append(combat.BREAK)
            return
        if self.state == "up":
            self.timer -= dt
            if t is not None:
                self.facing = self.angle_to(t.x, t.y)
            if self.timer <= 0:
                self.state = "under"
                self.cooldown = self.espec.cooldown
            return

        # Underground: tunnel toward the target (or last known / wander).
        if t is not None and self.sees_target:
            goal = (t.x, t.y)
            if self.dist_to(t) < 1.8 and self.cooldown <= 0:
                self.state, self.timer = "rumble", self.espec.windup
                return
        else:
            goal = self.last_known or self.wander_goal(dt)
        speed = self.espec.speed if self.alert else self.espec.speed * 0.4
        a = self.angle_to(*goal)
        nx, ny = self.x + math.cos(a) * speed * dt, self.y + math.sin(a) * speed * dt
        if self._in_desert(ctx.world, nx, ny):
            self.x, self.y, self.facing = nx, ny, a
        else:
            self._wander_goal = None   # hit the edge of the sand: pick another way
        self.trail_timer -= dt
        if self.trail_timer <= 0:
            self.trail_timer = 0.12
            ctx.effects.append(Effect("burrow", self.x, self.y))

    def can_see(self, world, other) -> bool:
        # It feels vibrations through the sand: walls don't block it.
        return math.hypot(other.x - self.x, other.y - self.y) <= self.espec.sight

    @staticmethod
    def _in_desert(world, x, y) -> bool:
        biome_at = getattr(world, "biome_at", None)
        if biome_at is None:
            return True
        return biome_at(math.floor(x), math.floor(y)).name == "desert"


class Boar(Creature):
    """Thornback boar (forest): ambles about until it spots you, then lowers
    its head and scrapes the ground (the wind-up: you see the charge coming
    and where it's aimed), and charges in a straight line. Anyone it runs
    into gets gored once per charge. Dodge it and it runs on until it slams
    into something -- a tree or wall takes a beating -- and stands there
    dazed for a moment: that's the time to hit it."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.state = "roam"          # roam -> scrape -> charge -> (dazed) -> roam
        self.timer = 0.0
        self.cooldown = self.rng.uniform(0.5, 1.5)
        self.gored: set[int] = set()

    def think(self, ctx: AIContext, dt: float) -> None:
        self.sense(ctx, dt)
        self.cooldown = max(0.0, self.cooldown - dt)
        t = self.target
        if self.state == "scrape":
            self.timer -= dt
            if self.timer <= 0:
                self.state, self.timer = "charge", config.BOAR_CHARGE_TIME
                self.gored = set()
            return
        if self.state == "charge":
            self._charge(ctx, dt)
            return
        if self.state == "dazed":
            self.timer -= dt
            if self.timer <= 0:
                self.state = "roam"
            return
        # Roaming / closing in.
        if t is not None and self.sees_target:
            d = self.dist_to(t)
            if d <= self.espec.attack_radius and self.cooldown <= 0:
                self.facing = self.angle_to(t.x, t.y)       # locked in: the charge line
                self.state, self.timer = "scrape", self.espec.windup
                return
            self.walk(ctx, t.x, t.y, dt, self.espec.speed * 0.6)
        elif self.last_known is not None:
            self.walk(ctx, *self.last_known, dt, self.espec.speed * 0.6)
        else:
            self.walk(ctx, *self.wander_goal(dt), dt, self.espec.speed * 0.35)

    def _charge(self, ctx: AIContext, dt: float) -> None:
        self.timer -= dt
        speed = config.BOAR_CHARGE_SPEED
        dx, dy = math.cos(self.facing) * speed * dt, math.sin(self.facing) * speed * dt
        self.x, self.y, bx, by = move_hull(ctx.world, self.x, self.y, 0.0, self.half, self.half,
                                           dx, dy)
        # Gore whoever it runs into (each once per charge).
        for a in ctx.actors:
            if a is self or not a.hittable or id(a) in self.gored:
                continue
            if math.hypot(a.x - self.x, a.y - self.y) <= self.hit_radius + a.hit_radius:
                self.gored.add(id(a))
                _numbered_hit(a, self.espec.damage * self.damage_mult, self, self.facing, ctx)
        if bx or by:                       # slammed into something
            ctx.events.append(combat.BREAK)
            ahead_x = self.x + math.cos(self.facing) * (self.hit_radius + 0.6)
            ahead_y = self.y + math.sin(self.facing) * (self.hit_radius + 0.6)
            ev = combat.crush_tile(ctx.world, math.floor(ahead_x), math.floor(ahead_y),
                                   config.BOAR_WALL_DAMAGE, ctx.effects)
            if ev:
                ctx.events.append(ev)
            ctx.effects.append(Effect("debris", ahead_x, ahead_y))
            self.state, self.timer = "dazed", config.BOAR_DAZE_TIME
            self.cooldown = self.espec.cooldown
        elif self.timer <= 0:              # ran out of steam
            self.state = "roam"
            self.cooldown = self.espec.cooldown


def _numbered_hit(victim, amount: float, source, angle: float, ctx: AIContext) -> None:
    dealt = victim.take_damage(amount, source, angle)
    if dealt > 0:
        ctx.effects.append(Effect("number", victim.x, victim.y - victim.hit_radius, 0.0,
                                  value=max(1, round(dealt)),
                                  player=victim.faction == "player"))
        ctx.events.append(combat.HIT)


class DustDevil(Creature):
    """Dust devil (desert, plains): a small whirlwind that drifts at you
    along a wobbly, never-quite-straight path and circles you at a short
    distance, flinging a spiral of sand pellets every few seconds and
    stinging anyone it brushes against. Visible and hittable the whole
    time, and fragile -- it pushes you to keep moving rather than hitting
    hard. (It replaced the goblin bombardier, which was too strong.)"""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.spin = self.rng.uniform(0, math.tau)       # how it's drawn turning
        self.phase = self.rng.uniform(0, math.tau)      # wobble
        self.orbit = self.rng.choice((-1, 1))
        self.fling = self.rng.uniform(0.6, self.espec.cooldown)
        self.sting = 0.0

    def think(self, ctx: AIContext, dt: float) -> None:
        self.sense(ctx, dt)
        self.spin += dt * config.DEVIL_SPIN_SPEED
        self.phase += dt
        self.sting = max(0.0, self.sting - dt)
        t = self.target
        if t is not None and self.sees_target:
            # Aim for a point circling the target, then wobble around it.
            round_ = self.angle_to(t.x, t.y) + math.pi + self.orbit * 0.6
            goal = (t.x + math.cos(round_) * config.DEVIL_ORBIT,
                    t.y + math.sin(round_) * config.DEVIL_ORBIT)
            speed = self.espec.speed
            self.fling -= dt
            if self.fling <= 0:
                self._fling(ctx)
                self.fling = self.espec.cooldown
            if (self.sting <= 0 and math.hypot(t.x - self.x, t.y - self.y)
                    <= self.hit_radius + t.hit_radius + 0.15):
                _numbered_hit(t, self.espec.damage * self.damage_mult, self,
                              self.angle_to(t.x, t.y), ctx)
                self.sting = config.DEVIL_STING_INTERVAL
        else:
            goal = self.last_known or self.wander_goal(dt)
            speed = self.espec.speed * 0.5
        a = self.angle_to(*goal) + math.sin(self.phase * 2.3) * 0.9
        self.facing = a
        self.x, self.y, _, _ = move_hull(ctx.world, self.x, self.y, 0.0, self.half, self.half,
                                         math.cos(a) * speed * dt, math.sin(a) * speed * dt)

    def _fling(self, ctx: AIContext) -> None:
        """A spiral of sand: pellets evenly round, starting where it's
        turned to now (so each fling comes out at a different angle)."""
        shell = config.WEAPONS["sand_fling"].shell
        n = config.DEVIL_PELLETS
        for k in range(n):
            a = self.spin + k * math.tau / n
            ctx.projectiles.append(Projectile(self.x, self.y, a, shell, owner=self,
                                              damage=shell.damage * self.damage_mult))
        ctx.events.append(shell.sound)
