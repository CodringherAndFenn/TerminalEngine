"""
ai/vehicles.py -- enemy tanks: tankette, sniper, heavy tank, turret.

They are real Tanks (same driving, rotated-hull collision, turret traverse,
armor and sprites as the player) with a Brain on top. The brain decides a
goal point and an aim; the tank body does the rest.

Shared firing rules: only with a clear shot, after a short reaction delay
on first spotting the target, once the (slow-turning) turret is on target,
with a little random aim error -- so they're dangerous but beatable.
"""

from __future__ import annotations

import math
import random

from .. import config
from ..entities.tank import Tank, wrap_angle
from ..specs import EnemySpec
from ..systems import combat
from ..systems.collision import hull_hits_solid
from ..systems.raycast import first_hit
from .brain import AIContext, Brain

ON_TARGET = math.radians(5)


class Vehicle(Brain, Tank):
    def __init__(self, spec: EnemySpec, x: float, y: float, difficulty: float,
                 rng: random.Random, spawn_id=None) -> None:
        tspec = config.TANKS[spec.tank]
        hp = round(spec.max_hp * (1 + config.ENEMY_HP_SCALING * difficulty))
        Tank.__init__(self, tspec, x, y, max_hp=hp)
        self.hull_angle = self.turret_angle = rng.uniform(-math.pi, math.pi)
        self.init_brain(spec, difficulty, rng, spawn_id)

    # --- Helpers ----------------------------------------------------------------------

    def passable(self, world):
        def check(px, py, heading):
            return not hull_hits_solid(world, px, py, heading, self.half_len, self.half_wid)
        return check

    # Light vehicles back away when that's quicker than turning around;
    # the heavy tank always turns to keep its armored front forward.
    allow_reverse = True

    def drive_to(self, ctx: AIContext, gx: float, gy: float, dt: float,
                 arrive: float = 1.0) -> bool:
        """Steer toward (gx, gy); returns True once within `arrive` tiles."""
        if math.hypot(gx - self.x, gy - self.y) <= arrive:
            self.steering.note_intent(False)
            self.drive(0, 0, dt, ctx.world, mode="direct")
            return True
        self.steering.note_intent(True)
        dx, dy = self.steering.direction(self.x, self.y, gx, gy, self.passable(ctx.world), dt,
                                         world=ctx.world, clearance=self.clearance)
        self.drive(dx, dy, dt, ctx.world, mode="direct", allow_reverse=self.allow_reverse)
        return False

    @property
    def clearance(self) -> int:
        """Free tiles needed around the center for local path planning."""
        half = max(self.half_len / config.TILE_PX_W, self.half_wid / config.TILE_PX_H)
        return max(1, round(half - 0.25))

    def hold(self, ctx, dt) -> None:
        self.steering.note_intent(False)
        self.drive(0, 0, dt, ctx.world, mode="direct")

    def clear_shot(self, world, target) -> bool:
        return first_hit(world.tile_at, self.x, self.y, target.x, target.y) is None

    def aim_and_fire(self, ctx: AIContext, dt: float, can_shoot: bool) -> None:
        """Track the target with the turret; fire when allowed and on target.
        Aim leads a moving target a little (imperfectly)."""
        t = self.target
        if t is None:
            return
        lead = self.dist_to(t) / self.weapon.spec.shell.speed
        vx = getattr(t, "speed", 0.0) * math.cos(getattr(t, "hull_angle", 0.0))
        vy = getattr(t, "speed", 0.0) * math.sin(getattr(t, "hull_angle", 0.0))
        k = self.rng.uniform(0.3, 0.9)   # they never lead perfectly
        aim = self.angle_to(t.x + vx * lead * k, t.y + vy * lead * k)
        self.aim_angle_toward(aim, dt)
        trigger = can_shoot and self.reaction <= 0 and self.turret_on_target(aim, ON_TARGET)
        if self.weapon.update(dt, trigger):
            err = self.rng.gauss(0, config.AIM_ERROR)
            ctx.events += combat.fire(
                self, ctx.world, ctx.projectiles, ctx.effects,
                angle=self.turret_angle + err,
                damage=self.weapon.spec.shell.damage * self.damage_mult,
            )

    def wander(self, ctx, dt) -> None:
        self.aim_angle_toward(self.hull_angle, dt)
        self.drive_to(ctx, *self.wander_goal(dt), dt, arrive=1.5)

    def search(self, ctx, dt) -> None:
        """Go to where the target was last seen/heard and look around."""
        if self.drive_to(ctx, *self.last_known, dt, arrive=2.0):
            self.aim_angle_toward(self.turret_angle + 1.5, dt)   # sweep the turret
        else:
            self.aim_angle_toward(self.angle_to(*self.last_known), dt)


class Tankette(Vehicle):
    """The basic enemy. Circles the target at mid range, repositions after
    shooting, flips its orbit direction now and then, and retreats when
    badly hurt."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.orbit = self.rng.choice((-1, 1))
        self.orbit_timer = self.rng.uniform(2, 4)
        self.radius = self.rng.uniform(*self.espec.preferred_range)

    def think(self, ctx: AIContext, dt: float) -> None:
        self.sense(ctx, dt)
        t = self.target
        if t is not None and self.sees_target:
            fleeing = self.hp < config.FLEE_HP_FRACTION * self.max_hp
            self.orbit_timer -= dt
            if self.orbit_timer <= 0:
                self.orbit = self.rng.choice((-1, 1))
                self.orbit_timer = self.rng.uniform(2, 4)
                self.radius = self.rng.uniform(*self.espec.preferred_range)
            # Goal: a point on a circle around the target, a bit further
            # round in the orbit direction (or well away when fleeing).
            away = math.atan2(self.y - t.y, self.x - t.x)
            r = self.radius * (1.8 if fleeing else 1.0)
            a = away + self.orbit * math.radians(35)
            self.drive_to(ctx, t.x + math.cos(a) * r, t.y + math.sin(a) * r, dt)
            fired_before = self.weapon.cooldown
            self.aim_and_fire(ctx, dt, self.clear_shot(ctx.world, t))
            if self.weapon.cooldown > fired_before:      # just fired: reposition
                self.orbit_timer = min(self.orbit_timer, self.rng.uniform(0.2, 1.0))
        elif self.last_known is not None:
            self.weapon.update(dt, False)
            self.search(ctx, dt)
        else:
            self.weapon.update(dt, False)
            self.wander(ctx, dt)


class Sniper(Vehicle):
    """Keeps far away. Aims with a visible laser for `windup` seconds while
    the target stays in sight, fires one hard shot, then relocates sideways.
    Runs if the target gets close."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.laser = 0.0              # seconds the laser has been on target
        self.relocate: tuple[float, float] | None = None
        self.relocate_timer = 0.0

    @property
    def laser_on(self) -> bool:
        return self.laser > 0

    def think(self, ctx: AIContext, dt: float) -> None:
        self.sense(ctx, dt)
        self.weapon.update(dt, False)   # cadence only; shots are fired below
        t = self.target
        lo, hi = self.espec.preferred_range
        if self.relocate is not None:
            self.laser = 0.0
            self.relocate_timer -= dt
            if self.drive_to(ctx, *self.relocate, dt, arrive=1.5) or self.relocate_timer <= 0:
                self.relocate = None
            if t is not None:
                self.aim_angle_toward(self.angle_to(t.x, t.y), dt)
            return
        if t is None or not self.sees_target:
            self.laser = 0.0
            if self.last_known is not None:
                self.search(ctx, dt)
            else:
                self.wander(ctx, dt)
            return

        d = self.dist_to(t)
        away = math.atan2(self.y - t.y, self.x - t.x)
        if d < lo * 0.6 or self.hp < config.FLEE_HP_FRACTION * self.max_hp:
            self.laser = 0.0          # too close: run
            self.drive_to(ctx, t.x + math.cos(away) * hi, t.y + math.sin(away) * hi, dt)
            self.aim_angle_toward(self.angle_to(t.x, t.y), dt)
            return
        if d > hi:
            self.drive_to(ctx, t.x + math.cos(away) * hi * 0.9, t.y + math.sin(away) * hi * 0.9, dt)
        else:
            self.hold(ctx, dt)
        # Laser: track the target; the shot comes after `windup` seconds of
        # continuous lock (and only when the cooldown allows).
        aim = self.angle_to(t.x, t.y)
        self.aim_angle_toward(aim, dt)
        if self.turret_on_target(aim, math.radians(3)) and self.clear_shot(ctx.world, t):
            self.laser += dt
        else:
            self.laser = max(0.0, self.laser - dt * 2)
        if self.laser >= self.espec.windup and self.weapon.cooldown <= 0:
            self.weapon.cooldown = self.weapon.spec.fire_interval
            ctx.events += combat.fire(
                self, ctx.world, ctx.projectiles, ctx.effects,
                damage=self.weapon.spec.shell.damage * self.damage_mult,
            )
            self.laser = 0.0
            side = self.rng.choice((-1, 1))
            a = away + side * math.radians(self.rng.uniform(40, 70))
            r = self.rng.uniform(lo, hi)
            self.relocate = (t.x + math.cos(a) * r, t.y + math.sin(a) * r)
            self.relocate_timer = 4.0


class Heavy(Vehicle):
    """Slow, armored at the front, big gun that breaks terrain. It closes
    in and shoots through (or grinds through) anything destructible in the
    way."""

    allow_reverse = False

    def think(self, ctx: AIContext, dt: float) -> None:
        self.sense(ctx, dt)
        t = self.target
        if t is not None and (self.sees_target or self._sees_through_cover(ctx, t)):
            lo, hi = self.espec.preferred_range
            d = self.dist_to(t)
            if d > hi * 0.8:
                self._advance(ctx, t.x, t.y, dt)
            else:
                self.hold(ctx, dt)
            # Its shells break walls, so it fires even through cover.
            self.aim_and_fire(ctx, dt, d <= hi + 4)
        elif self.last_known is not None:
            self.weapon.update(dt, False)
            self._advance(ctx, *self.last_known, dt)
            self.aim_angle_toward(self.hull_angle, dt)
        else:
            self.weapon.update(dt, False)
            self.wander(ctx, dt)

    def _sees_through_cover(self, ctx, t) -> bool:
        """Line to the target blocked only by things its shells can break."""
        if self.dist_to(t) > self.espec.sight:
            return False
        return first_hit(ctx.world.tile_at, self.x, self.y, t.x, t.y,
                         blocks=lambda tile: tile.blocks_shots and not tile.destructible) is None

    def _advance(self, ctx, gx, gy, dt) -> None:
        """Drive straight at the goal; if destructible terrain blocks the way,
        grind through it instead of steering around. Only when something it
        can't break is in the way does it fall back to normal steering."""
        self.steering.note_intent(True)
        a = math.atan2(gy - self.y, gx - self.x)
        self.drive(math.cos(a), math.sin(a), dt, ctx.world, mode="direct", allow_reverse=False)
        if not self.last_blocked:
            return  # moving (or still turning to face the goal): fine
        facing_it = abs(wrap_angle(a - self.hull_angle)) < math.radians(35)
        if not (facing_it and self._crush_ahead(ctx, dt)):
            self.drive_to(ctx, gx, gy, dt)

    def _crush_ahead(self, ctx, dt) -> bool:
        """Damage destructible tiles just ahead of the hull's front."""
        ca, sa = math.cos(self.hull_angle), math.sin(self.hull_angle)
        reach = self.half_len / config.TILE_PX_W + 0.4
        crushed = False
        for side in (-0.6, 0.0, 0.6):
            px = self.x + ca * reach - sa * side
            py = self.y + sa * reach + ca * side
            tx, ty = math.floor(px), math.floor(py)
            tile = ctx.world.tile_at(tx, ty)
            if tile.destructible:
                crushed = True
                ev = combat.crush_tile(ctx.world, tx, ty, config.HEAVY_CRUSH_DPS * dt, ctx.effects)
                if ev:
                    ctx.events.append(ev)
        return crushed


class Turret(Vehicle):
    """Fixed emplacement: sweeps slowly while idle, traverses slowly toward
    the target (flank it!), fires bursts when it has a clear shot."""

    def think(self, ctx: AIContext, dt: float) -> None:
        self.sense(ctx, dt)
        t = self.target
        if t is not None and self.sees_target:
            self.aim_and_fire(ctx, dt, True)
        else:
            self.weapon.update(dt, False)
            if self.last_known is not None:
                self.aim_angle_toward(self.angle_to(*self.last_known), dt)
            else:  # idle sweep
                self.aim_angle_toward(wrap_angle(self.turret_angle + 0.6), dt * 0.4)
