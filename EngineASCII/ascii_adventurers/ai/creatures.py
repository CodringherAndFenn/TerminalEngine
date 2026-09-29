"""
ai/creatures.py -- enemies without weapons: fallen warrior, spore puffer,
burrower.

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
        combat.blast(cx, cy, self.espec.attack_radius * 0.75, self.espec.damage,
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
        combat.blast(self.x, self.y, self.espec.attack_radius, self.espec.damage,
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
                             self.espec.damage, self, ctx.actors, effects=ctx.effects)
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
