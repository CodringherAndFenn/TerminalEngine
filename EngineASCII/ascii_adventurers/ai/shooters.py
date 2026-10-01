"""
ai/shooters.py -- enemies that shoot: goblin archer, warlock, ogre, spell
tower; and (M12) sentry wisp, bog toad, spore spitter.

They are real Characters (the same walking, box collision, aiming, armor
and sprite drawing as the hero) with a Brain on top. The brain decides a
goal point and an aim; the body does the rest.

Shared firing rules: only with a clear shot, after a short reaction delay
on first spotting the target, once the (slow-turning) aim is on target,
with a little random aim error -- so they're dangerous but beatable.
"""

from __future__ import annotations

import math
import random

from .. import config
from ..entities.character import Character, wrap_angle
from ..specs import EnemySpec
from ..systems import combat
from ..systems.collision import hull_hits_solid
from ..systems.raycast import first_hit
from .brain import AIContext, Brain

ON_TARGET = math.radians(5)


class Shooter(Brain, Character):
    faction = "enemy"

    def __init__(self, spec: EnemySpec, x: float, y: float,
                 rng: random.Random, spawn_id=None) -> None:
        Character.__init__(self, config.BODIES[spec.body], x, y, max_hp=spec.max_hp)
        self.aim_angle = self.heading = rng.uniform(-math.pi, math.pi)
        self.init_brain(spec, rng, spawn_id)

    # --- Helpers ----------------------------------------------------------------------

    def passable(self, world):
        def check(px, py, heading):
            return not hull_hits_solid(world, px, py, 0.0, self.half, self.half)
        return check

    def drive_to(self, ctx: AIContext, gx: float, gy: float, dt: float,
                 arrive: float = 1.0) -> bool:
        """Walk toward (gx, gy); returns True once within `arrive` tiles."""
        if math.hypot(gx - self.x, gy - self.y) <= arrive:
            self.steering.note_intent(False)
            self.move(0, 0, dt, ctx.world)
            return True
        self.steering.note_intent(True)
        dx, dy = self.steering.direction(self.x, self.y, gx, gy, self.passable(ctx.world), dt,
                                         world=ctx.world, clearance=self.clearance)
        self.move(dx, dy, dt, ctx.world)
        return False

    @property
    def clearance(self) -> int:
        """Free tiles needed around the center for local path planning."""
        return max(1, round(self.half / config.TILE_PX_W - 0.25))

    def hold(self, ctx, dt) -> None:
        self.steering.note_intent(False)
        self.move(0, 0, dt, ctx.world)

    def clear_shot(self, world, target) -> bool:
        return first_hit(world.tile_at, self.x, self.y, target.x, target.y) is None

    def aim_and_fire(self, ctx: AIContext, dt: float, can_shoot: bool) -> None:
        """Track the target with the aim; fire when allowed and on target.
        Aim leads a moving target a little (imperfectly)."""
        t = self.target
        if t is None:
            return
        lead = self.dist_to(t) / self.weapon.spec.shell.speed
        vx, vy = getattr(t, "vx", 0.0), getattr(t, "vy", 0.0)
        k = self.rng.uniform(0.3, 0.9)   # they never lead perfectly
        aim = self.angle_to(t.x + vx * lead * k, t.y + vy * lead * k)
        self.aim_angle_toward(aim, dt)
        trigger = can_shoot and self.reaction <= 0 and self.aim_on_target(aim, ON_TARGET)
        if self.weapon.update(dt, trigger):
            err = self.rng.gauss(0, config.AIM_ERROR)
            ctx.events += combat.fire(
                self, ctx.world, ctx.projectiles, ctx.effects,
                angle=self.aim_angle + err,
                damage=self.weapon.spec.shell.damage * self.damage_mult,
            )

    def wander(self, ctx, dt) -> None:
        self.aim_angle_toward(self.heading, dt)
        self.drive_to(ctx, *self.wander_goal(dt), dt, arrive=1.5)

    def search(self, ctx, dt) -> None:
        """Go to where the target was last seen/heard and look around."""
        if self.drive_to(ctx, *self.last_known, dt, arrive=2.0):
            self.aim_angle_toward(self.aim_angle + 1.5, dt)   # look around
        else:
            self.aim_angle_toward(self.angle_to(*self.last_known), dt)


class Archer(Shooter):
    """Goblin archer, the basic enemy. Circles the target at mid range,
    repositions after shooting, flips its orbit direction now and then, and
    retreats when badly hurt."""

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


class Warlock(Shooter):
    """Keeps far away. Locks on with a visible red aiming beam for `windup`
    seconds while the target stays in sight, casts one hard hex, then
    relocates sideways. Runs if the target gets close."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.beam = 0.0               # seconds the aiming beam has been on target
        self.relocate: tuple[float, float] | None = None
        self.relocate_timer = 0.0

    @property
    def beam_on(self) -> bool:
        return self.beam > 0

    def think(self, ctx: AIContext, dt: float) -> None:
        self.sense(ctx, dt)
        self.weapon.update(dt, False)   # cadence only; shots are fired below
        t = self.target
        lo, hi = self.espec.preferred_range
        if self.relocate is not None:
            self.beam = 0.0
            self.relocate_timer -= dt
            if self.drive_to(ctx, *self.relocate, dt, arrive=1.5) or self.relocate_timer <= 0:
                self.relocate = None
            if t is not None:
                self.aim_angle_toward(self.angle_to(t.x, t.y), dt)
            return
        if t is None or not self.sees_target:
            self.beam = 0.0
            if self.last_known is not None:
                self.search(ctx, dt)
            else:
                self.wander(ctx, dt)
            return

        d = self.dist_to(t)
        away = math.atan2(self.y - t.y, self.x - t.x)
        if d < lo * 0.6 or self.hp < config.FLEE_HP_FRACTION * self.max_hp:
            self.beam = 0.0          # too close: run
            self.drive_to(ctx, t.x + math.cos(away) * hi, t.y + math.sin(away) * hi, dt)
            self.aim_angle_toward(self.angle_to(t.x, t.y), dt)
            return
        if d > hi:
            self.drive_to(ctx, t.x + math.cos(away) * hi * 0.9, t.y + math.sin(away) * hi * 0.9, dt)
        else:
            self.hold(ctx, dt)
        # Beam: track the target; the hex comes after `windup` seconds of
        # continuous lock (and only when the cooldown allows).
        aim = self.angle_to(t.x, t.y)
        self.aim_angle_toward(aim, dt)
        if self.aim_on_target(aim, math.radians(3)) and self.clear_shot(ctx.world, t):
            self.beam += dt
        else:
            self.beam = max(0.0, self.beam - dt * 2)
        if self.beam >= self.espec.windup and self.weapon.cooldown <= 0:
            self.weapon.cooldown = self.weapon.spec.fire_interval
            ctx.events += combat.fire(
                self, ctx.world, ctx.projectiles, ctx.effects,
                damage=self.weapon.spec.shell.damage * self.damage_mult,
            )
            self.beam = 0.0
            side = self.rng.choice((-1, 1))
            a = away + side * math.radians(self.rng.uniform(40, 70))
            r = self.rng.uniform(lo, hi)
            self.relocate = (t.x + math.cos(a) * r, t.y + math.sin(a) * r)
            self.relocate_timer = 4.0


class Ogre(Shooter):
    """Slow and tough, armored on the side it faces, throws rocks that
    break terrain. It closes in and throws through (or smashes through)
    anything destructible in the way."""

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
            # Its rocks break walls, so it throws even through cover.
            self.aim_and_fire(ctx, dt, d <= hi + 4)
        elif self.last_known is not None:
            self.weapon.update(dt, False)
            self._advance(ctx, *self.last_known, dt)
            self.aim_angle_toward(self.heading, dt)
        else:
            self.weapon.update(dt, False)
            self.wander(ctx, dt)

    def _sees_through_cover(self, ctx, t) -> bool:
        """Line to the target blocked only by things its rocks can break."""
        if self.dist_to(t) > self.espec.sight:
            return False
        return first_hit(ctx.world.tile_at, self.x, self.y, t.x, t.y,
                         blocks=lambda tile: tile.blocks_shots and not tile.destructible) is None

    def _advance(self, ctx, gx, gy, dt) -> None:
        """Walk straight at the goal; if destructible terrain blocks the way,
        smash through it instead of going around. Only when something it
        can't break is in the way does it fall back to normal steering."""
        self.steering.note_intent(True)
        a = math.atan2(gy - self.y, gx - self.x)
        self.move(math.cos(a), math.sin(a), dt, ctx.world)
        if not self.last_blocked:
            return
        if not self._smash_ahead(ctx, a, dt):
            self.drive_to(ctx, gx, gy, dt)

    def _smash_ahead(self, ctx, a: float, dt: float) -> bool:
        """Damage destructible tiles just ahead in direction `a`."""
        ca, sa = math.cos(a), math.sin(a)
        reach = self.half / config.TILE_PX_W + 0.4
        smashed = False
        for side in (-0.6, 0.0, 0.6):
            px = self.x + ca * reach - sa * side
            py = self.y + sa * reach + ca * side
            tx, ty = math.floor(px), math.floor(py)
            tile = ctx.world.tile_at(tx, ty)
            if tile.destructible:
                smashed = True
                ev = combat.crush_tile(ctx.world, tx, ty, config.OGRE_CRUSH_DPS * dt, ctx.effects)
                if ev:
                    ctx.events.append(ev)
        return smashed


class Tower(Shooter):
    """Spell tower: doesn't move. Sweeps slowly while idle, turns slowly
    toward the target (flank it!), fires bursts of orbs when it has a clear
    shot."""

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
                self.aim_angle_toward(wrap_angle(self.aim_angle + 0.6), dt * 0.4)


# --- M12 --------------------------------------------------------------------------------


class Wisp(Shooter):
    """Sentry wisp (ruins): a floating eye circling at mid range, firing
    steady bolts at you whenever it sees you. Its searchlight sweeps back
    and forth around you; while the light is on you it fires much faster --
    so stay out of the beam, don't just hide from the wisp."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.light = self.aim_angle           # where the searchlight points (world)
        self.sweep = self.rng.uniform(0, math.tau)
        self.lit = False                      # the light is on the target now
        self.rapid = 0.0                      # cooldown of the fast (lit) fire
        self.orbit = self.rng.choice((-1, 1))

    def think(self, ctx: AIContext, dt: float) -> None:
        self.sense(ctx, dt)
        self.sweep += dt * config.WISP_SWEEP_SPEED
        self.rapid = max(0.0, self.rapid - dt)
        t = self.target
        if t is None or not self.sees_target:
            self.lit = False
            self.light = wrap_angle(self.light + dt * 0.8)      # idle scan
            self.weapon.update(dt, False)
            if self.last_known is not None:
                self.search(ctx, dt)
            else:
                self.wander(ctx, dt)
            return
        lo, hi = self.espec.preferred_range
        away = math.atan2(self.y - t.y, self.x - t.x)
        r = (lo + hi) / 2
        a = away + self.orbit * math.radians(30)
        self.drive_to(ctx, t.x + math.cos(a) * r, t.y + math.sin(a) * r, dt)
        # The light swings back and forth across the target.
        to_t = self.angle_to(t.x, t.y)
        self.light = to_t + math.sin(self.sweep) * math.radians(config.WISP_SWEEP_DEG)
        self.lit = (abs(wrap_angle(to_t - self.light)) <= math.radians(config.WISP_CONE_DEG) / 2
                    and self.dist_to(t) <= config.WISP_LIGHT_RANGE)
        if self.lit and self.rapid <= 0 and self.clear_shot(ctx.world, t) and self.reaction <= 0:
            self.aim_angle = to_t
            self.rapid = config.WISP_LIT_INTERVAL
            err = self.rng.gauss(0, config.AIM_ERROR)
            ctx.events += combat.fire(self, ctx.world, ctx.projectiles, ctx.effects,
                                      angle=to_t + err,
                                      damage=self.weapon.spec.shell.damage * self.damage_mult)
            self.weapon.update(dt, False)
        else:
            self.aim_and_fire(ctx, dt, self.clear_shot(ctx.world, t))


class Toad(Shooter):
    """Bog toad (swamp): gets around in hops -- a quick leap, then a pause --
    keeping a middling distance, and spits a fan of slow acid globs while
    it sits."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.hop = 0.0                        # >0: mid-leap
        self.rest = self.rng.uniform(0.3, 1.0)

    def think(self, ctx: AIContext, dt: float) -> None:
        self.sense(ctx, dt)
        t = self.target
        if self.hop > 0:
            self.hop -= dt
            self.weapon.update(dt, False)
            self.move(math.cos(self.heading), math.sin(self.heading), dt, ctx.world)
            if self.hop <= 0 or self.last_blocked:
                self.hop = 0.0
                self.rest = self.rng.uniform(*config.TOAD_REST)
            return
        self.hold(ctx, dt)
        self.rest -= dt
        if t is not None and self.sees_target:
            self.aim_and_fire(ctx, dt, self.clear_shot(ctx.world, t))
            goal = t.x, t.y
            lo, hi = self.espec.preferred_range
            d = self.dist_to(t)
            away = math.atan2(self.y - t.y, self.x - t.x)
            side = away + self.rng.choice((-1, 1)) * math.radians(50)
            if d < lo:
                goal = (t.x + math.cos(away) * hi, t.y + math.sin(away) * hi)
            elif d <= hi:
                goal = (t.x + math.cos(side) * d, t.y + math.sin(side) * d)
        else:
            self.weapon.update(dt, False)
            goal = self.last_known or self.wander_goal(dt)
        if self.rest <= 0:                   # leap toward the goal
            self.heading = self.angle_to(*goal)
            self.hop = config.TOAD_HOP_TIME


class Spitter(Shooter):
    """Spore spitter (mushroom): a mushroom that doesn't move. While it sees
    someone it puffs a ring of spores all around, turning the ring a little
    every volley -- a small bullet-hell pattern to weave through."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.spin = self.rng.uniform(0, math.tau)

    def think(self, ctx: AIContext, dt: float) -> None:
        self.sense(ctx, dt)
        t = self.target
        seen = t is not None and self.sees_target
        if self.weapon.update(dt, seen and self.reaction <= 0):
            ctx.events += combat.fire(self, ctx.world, ctx.projectiles, ctx.effects,
                                      angle=self.spin,
                                      damage=self.weapon.spec.shell.damage * self.damage_mult)
            self.spin += math.radians(config.SPITTER_RING_TURN_DEG)
        if seen:
            self.aim_angle = self.angle_to(t.x, t.y)     # (only which way it faces)
