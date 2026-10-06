"""
ai/creatures.py -- enemies without weapons: fallen warrior, spore puffer,
burrower, and (M12) thornback boar and dust devil; (M22-M23) the quest
and boss creatures: leeches, mosquitoes, scarabs, camels, the Nameless
Magus's sand elementals, golems, sigils and hourglass, and the Fallout
King's ghouls, isotope rods and toxic barrels; the frost wraiths.

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


class Leech(Creature):
    """Bloated leech and leechling (M22, the leech doctor's quest): a
    worm that crawls at you, rears up (wind-up) and bites what's in front.
    A bloated one, popped, bursts into LEECH_BROOD leechlings (they come
    out through AIContext.spawned)."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.windup = 0.0
        self.cooldown = 0.0
        self.wriggle = self.rng.uniform(0, math.tau)
        self.burst_done = False

    def think(self, ctx: AIContext, dt: float) -> None:
        self.sense(ctx, dt)
        self.cooldown = max(0.0, self.cooldown - dt)
        self.wriggle += dt * 6.0
        t = self.target
        if self.windup > 0:
            self.windup -= dt
            if self.windup <= 0:
                self._bite(ctx)
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
        self.walk(ctx, *goal, dt, self.espec.speed)

    def _bite(self, ctx: AIContext) -> None:
        cx = self.x + math.cos(self.facing) * 0.6
        cy = self.y + math.sin(self.facing) * 0.6
        combat.blast(cx, cy, self.espec.attack_radius * 0.7, self.espec.damage * self.damage_mult,
                     self, ctx.actors, effects=ctx.effects)
        ctx.events.append(combat.HIT)
        self.cooldown = self.espec.cooldown

    def on_death(self, ctx: AIContext) -> None:
        ctx.effects.append(Effect("explosion", self.x, self.y))
        if getattr(self, "kind_key", None) != "bloated_leech" or self.burst_done:
            return
        self.burst_done = True
        for k in range(config.LEECH_BROOD):
            a = self.rng.uniform(0, math.tau)
            ctx.spawned.append(("leechling", self.x + math.cos(a) * 0.8,
                                self.y + math.sin(a) * 0.8))


class Mosquito(Creature):
    """Mosquito (M22.2: the smoke keeper's braziers, Lady Proboscia's
    calls): flies over everything, buzzing at its target on a wobbly line.
    In reach it hovers still a moment (the tell), stings what's in front,
    then darts off sideways before coming back for more."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.windup = 0.0
        self.cooldown = 0.0
        self.dart = 0.0               # > 0 while darting off after a sting
        self.dart_angle = 0.0
        self.phase = self.rng.uniform(0, math.tau)
        self.summoner = None

    def think(self, ctx: AIContext, dt: float) -> None:
        self.sense(ctx, dt)
        self.cooldown = max(0.0, self.cooldown - dt)
        self.phase += dt * 9.0
        t = self.target
        if self.windup > 0:
            self.windup -= dt
            if self.windup <= 0:
                self._sting(ctx)
            return
        speed = self.espec.speed
        if self.dart > 0:
            self.dart -= dt
            a = self.dart_angle
        else:
            if t is None or not self.alert:
                gx, gy = self.wander_goal(dt)
                speed *= 0.5
            else:
                gx, gy = (t.x, t.y) if self.sees_target else (self.last_known or (t.x, t.y))
                reach = self.espec.attack_radius + t.hit_radius
                if self.sees_target and self.dist_to(t) <= reach and self.cooldown <= 0:
                    self.facing = self.angle_to(t.x, t.y)
                    self.windup = self.espec.windup
                    return
            a = self.angle_to(gx, gy) + math.sin(self.phase * 0.5) * 0.7
        # Straight through the air (no collision), on a wobbly line.
        self.facing = a
        self.x += math.cos(a) * speed * dt
        self.y += math.sin(a) * speed * dt

    def _sting(self, ctx: AIContext) -> None:
        cx = self.x + math.cos(self.facing) * 0.5
        cy = self.y + math.sin(self.facing) * 0.5
        # Only heroes: a cloud of them stinging round you would otherwise
        # sting each other to death.
        for h in ctx.players:
            if h.hittable and math.hypot(h.x - cx, h.y - cy) <= self.espec.attack_radius * 0.8 + h.hit_radius:
                combat.strike(h, self.espec.damage * self.damage_mult, self, self.facing, ctx.effects)
        ctx.events.append(combat.HIT)
        self.cooldown = self.espec.cooldown
        self.dart = 0.45
        self.dart_angle = self.facing + math.pi + self.rng.choice((-1, 1)) * self.rng.uniform(0.6, 1.2)


class Scarab(Leech):
    """Scarab (M23.1, Khepri's call): scuttles out of the sand at you and
    nips -- a leech's crawl, wind-up and bite on six legs."""


class GoldenScarab(Creature):
    """Golden scarab (M23.1, the scarab collector's quest): harmless and
    skittish. It potters about its home spot; once a hero comes within
    GOLDEN_SCARAB[0] tiles it runs away from the nearest one, jinking from
    side to side. Still being chased GOLDEN_SCARAB[1] s later, it digs in
    (GOLDEN_SCARAB[2] s: dust flies, and it can still be hit -- the last
    chance) and is gone; GOLDEN_SCARAB[3] s later it comes up again at its
    home spot. So you catch one by cornering it or shooting fast."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.home = (self.x, self.y)
        self.state = "idle"           # idle -> flee -> dig -> gone -> idle
        self.timer = 0.0
        self.jink = 0.0
        self.jink_dir = 1
        self.phase = self.rng.uniform(0, math.tau)

    @property
    def hittable(self) -> bool:
        return self.alive and self.state != "gone"

    def think(self, ctx: AIContext, dt: float) -> None:
        self.sense(ctx, dt)
        self.phase += dt * 10.0
        spook, run, dig, hide = config.GOLDEN_SCARAB
        if self.state == "gone":
            self.timer -= dt
            if self.timer <= 0:
                self.x, self.y = self.home
                self.state = "idle"
                ctx.effects.append(Effect("burrow", self.x, self.y))
            return
        if self.state == "dig":
            self.timer -= dt
            if int(self.timer * 10) % 2 == 0:
                ctx.effects.append(Effect("burrow", self.x, self.y))
            if self.timer <= 0:
                self.state, self.timer = "gone", hide
                ctx.effects.append(Effect("eruption", self.x, self.y))
            return
        near = [h for h in ctx.players if h.alive and math.hypot(h.x - self.x, h.y - self.y) < spook]
        if not near:
            if self.state == "flee":
                self.state = "idle"
            gx, gy = self.wander_goal(dt)
            if math.hypot(gx - self.home[0], gy - self.home[1]) > 8:
                gx, gy = self.home
            self.walk(ctx, gx, gy, dt, self.espec.speed * 0.25)
            return
        if self.state == "idle":
            self.state, self.timer = "flee", run
        self.timer -= dt
        if self.timer <= 0:
            self.state, self.timer = "dig", dig
            return
        h = min(near, key=lambda o: math.hypot(o.x - self.x, o.y - self.y))
        self.jink -= dt
        if self.jink <= 0:
            self.jink = self.rng.uniform(0.3, 0.7)
            self.jink_dir = -self.jink_dir
        a = math.atan2(self.y - h.y, self.x - h.x) + self.jink_dir * 0.6
        self.walk(ctx, self.x + math.cos(a) * 4, self.y + math.sin(a) * 4, dt, self.espec.speed)


class Camel(Creature):
    """Mangy camel (M23.2, the caravan master's quest) and mirage (Ol'
    Spitter's heat-haze double). A camel keeps its distance from its
    target (somewhere in preferred_range, drifting round it), and every
    `cooldown` s stops, rears its head back (`rear`: the tell, `windup`
    s) and spits a little fan of globs (CAMEL_FAN of CAMEL_SPIT) at you.
    A mangy one guards a bundle of cargo: with nobody to chase it stays
    within CAMEL_LEASH tiles of where it was put. A mirage pops at the
    first hit, whatever it was."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.home = (self.x, self.y)
        self.rear = 0.0               # > 0: head back, about to spit
        self.cooldown = self.rng.uniform(0.6, 1.6)
        self.phase = self.rng.uniform(0, math.tau)   # walk cycle (drawing)
        self.side = self.rng.choice((-1, 1))
        self.side_t = self.rng.uniform(1.5, 3.0)
        self.summoner = None

    @property
    def mirage(self) -> bool:
        return getattr(self, "kind_key", "") == "mirage"

    def take_damage(self, amount, source, from_angle):
        if self.mirage and amount > 0 and self.hittable:
            amount = max(amount, self.hp)            # one touch and it's gone
        return super().take_damage(amount, source, from_angle)

    def think(self, ctx: AIContext, dt: float) -> None:
        self.sense(ctx, dt)
        self.cooldown = max(0.0, self.cooldown - dt)
        t = self.target
        if self.rear > 0:
            if t is not None:
                self.facing = self.angle_to(t.x, t.y)
            self.rear -= dt
            if self.rear <= 0:
                self._spit(ctx)
            return
        if t is None or not (self.alert or self.mirage):
            gx, gy = self.wander_goal(dt)
            if math.hypot(gx - self.home[0], gy - self.home[1]) > config.CAMEL_LEASH \
                    and not self.mirage:
                gx, gy = self.home
            if self.walk(ctx, gx, gy, dt, self.espec.speed * 0.3) is False:
                self.phase += dt * 4.0
            return
        if self.sees_target and self.cooldown <= 0:
            self.facing = self.angle_to(t.x, t.y)
            self.rear = self.espec.windup
            return
        gx, gy = (t.x, t.y) if self.sees_target else (self.last_known or (t.x, t.y))
        self.side_t -= dt
        if self.side_t <= 0:
            self.side = -self.side
            self.side_t = self.rng.uniform(1.5, 3.0)
        lo, hi = self.espec.preferred_range
        d = math.hypot(self.x - gx, self.y - gy)
        away = math.atan2(self.y - gy, self.x - gx)
        r = max(lo, min(hi, d))
        a = away + self.side * math.radians(30)
        if self.walk(ctx, gx + math.cos(a) * r, gy + math.sin(a) * r, dt, self.espec.speed) is False:
            self.phase += dt * 8.0
        if self.sees_target:
            self.facing = self.angle_to(t.x, t.y)

    def _spit(self, ctx: AIContext) -> None:
        t = self.target
        self.cooldown = self.espec.cooldown * self.rng.uniform(0.85, 1.15)
        if t is None:
            return
        from ..systems import patterns
        n, spread = config.CAMEL_FAN
        mx = self.x + math.cos(self.facing) * self.hit_radius
        my = self.y + math.sin(self.facing) * self.hit_radius
        lead = math.hypot(t.x - mx, t.y - my) / config.CAMEL_SPIT.speed * 0.5
        aim = math.atan2(t.y + getattr(t, "vy", 0.0) * lead - my,
                         t.x + getattr(t, "vx", 0.0) * lead - mx)
        patterns.fan(self, mx, my, aim, n, spread, config.CAMEL_SPIT, ctx.projectiles)
        ctx.events.append("fizzle")


class SandElemental(Creature):
    """Sand elemental (M23.3: rises round a star circle being broken, and
    serves the Magus). Keeps its distance; every `cooldown` s it draws back
    (`windup`: the tell, eyes flaring) and throws a sand bolt at you. Now
    and then it blinks: gone in a swirl for ELEMENTAL_BLINK[0] s (can't be
    hit), and back a few tiles off to one side."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.windup = 0.0
        self.cooldown = self.rng.uniform(0.8, 1.6)
        self.blink_cd = self.rng.uniform(2.0, 4.0)
        self.gone = 0.0
        self.dest: tuple[float, float] | None = None
        self.phase = self.rng.uniform(0, math.tau)    # its swirl (drawing)
        self.summoner = None

    @property
    def hittable(self) -> bool:
        return self.alive and self.gone <= 0

    def think(self, ctx: AIContext, dt: float) -> None:
        self.sense(ctx, dt)
        self.phase += dt * 6.0
        self.cooldown = max(0.0, self.cooldown - dt)
        self.blink_cd -= dt
        if self.gone > 0:
            self.gone -= dt
            if self.gone <= 0 and self.dest is not None:
                self.x, self.y = self.dest
                ctx.effects.append(Effect("eruption", self.x, self.y))
            return
        t = self.target
        if self.windup > 0:
            if t is not None:
                self.facing = self.angle_to(t.x, t.y)
            self.windup -= dt
            if self.windup <= 0 and t is not None:
                from ..systems import patterns
                shell = config.ELEMENTAL_BOLT
                lead = self.dist_to(t) / shell.speed * 0.6
                a = math.atan2(t.y + getattr(t, "vy", 0.0) * lead - self.y,
                               t.x + getattr(t, "vx", 0.0) * lead - self.x)
                patterns.shoot(self, self.x, self.y, a, shell, ctx.projectiles)
                ctx.events.append("fizzle")
                self.cooldown = self.espec.cooldown * self.rng.uniform(0.85, 1.2)
            return
        if t is None:
            self.walk(ctx, *self.wander_goal(dt), dt, self.espec.speed * 0.4)
            return
        if self.blink_cd <= 0 and self.sees_target:
            self._blink(ctx, t)
            return
        if self.sees_target and self.cooldown <= 0:
            self.windup = self.espec.windup
            return
        lo, hi = self.espec.preferred_range
        d = self.dist_to(t)
        away = math.atan2(self.y - t.y, self.x - t.x)
        r = max(lo, min(hi, d))
        self.walk(ctx, t.x + math.cos(away + 0.4) * r, t.y + math.sin(away + 0.4) * r, dt,
                  self.espec.speed)

    def _blink(self, ctx: AIContext, t) -> None:
        _, lo, hi = config.ELEMENTAL_BLINK
        self.blink_cd = self.rng.uniform(2.5, 4.5)
        for _ in range(8):
            a = math.atan2(self.y - t.y, self.x - t.x) + self.rng.choice((-1, 1)) * \
                self.rng.uniform(0.6, 1.4)
            r = self.rng.uniform(lo, hi)
            x, y = self.x + math.cos(a) * r, self.y + math.sin(a) * r
            if not hull_hits_solid(ctx.world, x, y, 0.0, self.half, self.half):
                self.dest = (x, y)
                self.gone = config.ELEMENTAL_BLINK[0]
                ctx.effects.append(Effect("burrow", self.x, self.y))
                return


class SandGolem(Creature):
    """Sand golem (M23.3, out of the Magus's golem runes): plods at you;
    in reach it raises its fists (`windup`: the tell) and slams the ground
    -- a blast of `attack_radius` round where it stands."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.windup = 0.0
        self.cooldown = 0.5
        self.phase = 0.0
        self.summoner = None

    def think(self, ctx: AIContext, dt: float) -> None:
        self.sense(ctx, dt)
        self.cooldown = max(0.0, self.cooldown - dt)
        t = self.target
        if self.windup > 0:
            self.windup -= dt
            if self.windup <= 0:
                combat.blast(self.x, self.y, self.espec.attack_radius,
                             self.espec.damage * self.damage_mult, self,
                             [a for a in ctx.actors if getattr(a, "faction", "") == "player"],
                             effects=ctx.effects)
                ctx.effects.append(Effect("nova", self.x, self.y, size=self.espec.attack_radius))
                ctx.events.append(combat.BREAK)
                self.cooldown = self.espec.cooldown
            return
        if t is None:
            return
        if self.dist_to(t) <= self.espec.attack_radius + t.hit_radius and self.cooldown <= 0:
            self.windup = self.espec.windup
            return
        if not self.walk(ctx, t.x, t.y, dt, self.espec.speed):
            self.phase += dt * 5.0


class Sigil(Creature):
    """A sand sigil (M23.3, the Magus's): a glowing glyph that drifts after
    its target through everything, and bursts on touch (heroes only). One
    hit of anything pops it; it fades after SIGIL_LIFE s."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.age = 0.0
        self.phase = self.rng.uniform(0, math.tau)
        self.summoner = None

    def take_damage(self, amount, source, from_angle):
        if amount > 0 and self.hittable:
            amount = max(amount, self.hp)
        return super().take_damage(amount, source, from_angle)

    def think(self, ctx: AIContext, dt: float) -> None:
        self.sense(ctx, dt)
        self.age += dt
        self.phase += dt * 5.0
        if self.age >= config.SIGIL_LIFE:
            self.hp = 0.0
            self.last_hit_by = None
            return
        heroes = [h for h in ctx.players if h.hittable]
        if not heroes:
            return
        t = min(heroes, key=lambda h: math.hypot(h.x - self.x, h.y - self.y))
        d = math.hypot(t.x - self.x, t.y - self.y)
        if d <= self.espec.attack_radius + t.hit_radius:
            combat.strike(t, self.espec.damage * self.damage_mult, self,
                          math.atan2(t.y - self.y, t.x - self.x), ctx.effects)
            ctx.effects.append(Effect("nova", self.x, self.y, size=1.2))
            self.hp = 0.0
            self.last_hit_by = None
            return
        want = math.atan2(t.y - self.y, t.x - self.x)
        turn = (want - self.facing + math.pi) % math.tau - math.pi
        self.facing += max(-2.0 * dt, min(2.0 * dt, turn))
        self.x += math.cos(self.facing) * self.espec.speed * dt
        self.y += math.sin(self.facing) * self.espec.speed * dt


class Hourglass(Creature):
    """The Magus's hourglass (M23.3): it stands where he plants it while
    its sand runs (`sand`: 1 full .. 0 run out; the Magus keeps the time).
    Shatter it and he's stunned."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.sand = 1.0
        self.summoner = None

    def think(self, ctx: AIContext, dt: float) -> None:
        pass


class Ghoul(Leech):
    """Glowing ghoul (M24.1: the scavenger's escort, the Fallout King's
    call): a leech's rush, wind-up and bite on two legs -- and when it dies
    it bursts green (GHOUL_BURST: heroes only)."""

    def on_death(self, ctx: AIContext) -> None:
        radius, damage = config.GHOUL_BURST
        combat.blast(self.x, self.y, radius, damage * self.damage_mult, self,
                     [a for a in ctx.players if a.hittable], effects=ctx.effects)
        ctx.effects.append(Effect("nova", self.x, self.y, size=radius))
        ctx.events.append(combat.BREAK)


class IsotopeRod(Creature):
    """An isotope rod (M24.1) standing in a patch of the Fallout King's
    fallout: it doesn't move or fight; smash it and its patch clears."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.phase = self.rng.uniform(0, math.tau)
        self.summoner = None

    def think(self, ctx: AIContext, dt: float) -> None:
        self.phase += dt * 4.0


class ToxicBarrel(Creature):
    """A toxic barrel the Fallout King hurls (M24.1): it arcs from where it
    was thrown to `target` over `flight` s (`height` 0..1 for drawing).
    Nothing can hit it in the air (the user, 2026-10-06: harder, on
    purpose) -- shots fly under it. Landed, it's gone (`landed`): the King
    leaves a goo puddle there."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.start = (self.x, self.y)
        self.target = (self.x, self.y)
        self.flight = 1.0
        self.t = 0.0
        self.landed = False
        self.height = 0.0
        self.summoner = None

    @property
    def hittable(self) -> bool:
        return False

    def take_damage(self, amount, source, from_angle):
        return 0.0

    def think(self, ctx: AIContext, dt: float) -> None:
        self.t = min(self.flight, self.t + dt)
        f = self.t / self.flight if self.flight > 0 else 1.0
        (x0, y0), (x1, y1) = self.start, self.target
        self.x, self.y = x0 + (x1 - x0) * f, y0 + (y1 - y0) * f
        self.height = 4 * f * (1 - f)
        if f >= 1.0:
            self.landed = True
            self.hp = 0.0
            self.last_hit_by = None


class FrostWraith(Creature):
    """Frost wraith (M24.2, the searching sister's rescue): a cold ghost
    that drifts through walls. Sent at a thawing captive (`goal_pos`) it
    makes for them and, touching them, sets `touched` (the quest knocks the
    thaw back and it fades). Otherwise it drifts at you and chills you with
    a touch (`damage` every `cooldown` s)."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.goal_pos: tuple[float, float] | None = None
        self.touched = False
        self.cooldown = 0.0
        self.phase = self.rng.uniform(0, math.tau)
        self.summoner = None

    def think(self, ctx: AIContext, dt: float) -> None:
        self.sense(ctx, dt)
        self.phase += dt * 3.0
        self.cooldown = max(0.0, self.cooldown - dt)
        if self.goal_pos is not None:
            gx, gy = self.goal_pos
            if math.hypot(gx - self.x, gy - self.y) <= 1.0:
                self.touched = True
                return
        else:
            t = self.target
            if t is None:
                return
            gx, gy = t.x, t.y
            if math.hypot(gx - self.x, gy - self.y) <= self.espec.attack_radius + t.hit_radius:
                if self.cooldown <= 0 and t.hittable:
                    combat.strike(t, self.espec.damage * self.damage_mult, self,
                                  self.angle_to(gx, gy), ctx.effects)
                    self.cooldown = 1.0
                return
        a = math.atan2(gy - self.y, gx - self.x) + math.sin(self.phase) * 0.4
        self.facing = a
        self.x += math.cos(a) * self.espec.speed * dt
        self.y += math.sin(a) * self.espec.speed * dt
