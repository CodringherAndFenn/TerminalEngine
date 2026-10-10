"""
ai/plains.py -- the plains' new enemies (P7, design/BOSSES.md 24.5).

All are letter-art creatures (render/plains_art.py). Every attack has a
tell -- a wind-up shown with a "!" over the head, or a charge line -- and
hits an area, so friendly fire applies, like every enemy.

  simple chasers  field rats (packs of 4-6), the shambling farmhand, angry
                  geese (gaggles of 3), the molehill's mole rats, the
                  scarecrow's crows (they fly): straight at you, a short
                  wind-up, a bite. No tricks.
  hound           packs of 3: they circle you and take turns darting in to
                  bite, one at a time, from different sides.
  hawk            flies over everything, circles, lines up (its line shows),
                  dives straight through, climbs away.
  molehill        never moves; sends out a mole rat every few seconds while
                  it sees a hero, up to a few at a time.
  bull (elite)    scrapes, then charges, trampling bushes, fences and
                  anything that breaks, and wheels round for more passes;
                  stopped dazed only by what doesn't break.
  lancer          a bandit on horseback: rides wide, lowers the lance (the
                  line shows), and gallops straight through; again and again.
  priest          keeps back and heals the most hurt enemy near it.
  straw golem     slow, swings hard; dies in a burst of burning straw.
  scarecrow       shuffles along and lets loose crows.
  drummer         keeps away from heroes and near its allies: everyone in
                  its ring moves and attacks faster and hits harder.

The bandit slinger and the shieldbearer (elite) are Characters (ai/shooters.py).
"""

from __future__ import annotations

import math

from .. import config
from ..entities.effects import Effect
from ..systems import combat
from ..systems.collision import move_hull
from ..systems.zones import Zone
from .brain import AIContext
from .creatures import Creature, _numbered_hit
from .shooters import Shooter


class PlainsCreature(Creature):
    """A letter-art creature: counts the distance it walks (for its walk
    frames) and has a wind-up / cooldown."""

    flies = False

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.walked = 0.0
        self._moved = 0.0
        self.windup = 0.0
        self.cooldown = self.rng.uniform(0.3, 1.0)
        self.tell = 0.0              # >0: draw the "!" (seconds of wind-up left)

    @property
    def moving(self) -> bool:
        return self._moved > 1e-6

    def go(self, ctx: AIContext, gx: float, gy: float, dt: float, speed: float) -> bool:
        """Walk (or fly, straight over everything) toward (gx, gy)."""
        x0, y0 = self.x, self.y
        if self.flies:
            d = math.hypot(gx - self.x, gy - self.y)
            done = d < 0.4
            if not done:
                step = min(d, speed * dt)
                self.facing = math.atan2(gy - self.y, gx - self.x)
                self.x += math.cos(self.facing) * step
                self.y += math.sin(self.facing) * step
        else:
            done = self.walk(ctx, gx, gy, dt, speed)
        self._moved = math.hypot(self.x - x0, self.y - y0)
        self.walked += self._moved
        return done

    def think(self, ctx: AIContext, dt: float) -> None:
        self._moved = 0.0
        self.cooldown = max(0.0, self.cooldown - dt)

    def bite(self, ctx: AIContext, reach_mult: float = 0.7) -> None:
        cx = self.x + math.cos(self.facing) * 0.6
        cy = self.y + math.sin(self.facing) * 0.6
        combat.blast(cx, cy, self.espec.attack_radius * reach_mult,
                     self.espec.damage * self.damage_mult, self, ctx.actors, effects=ctx.effects)
        ctx.events.append(combat.HIT)
        self.cooldown = self.espec.cooldown

    def facing_left(self) -> bool:
        return math.cos(self.facing) < 0


# --- Simple chasers -------------------------------------------------------------------


class Chaser(PlainsCreature):
    """Straight at its target, a short wind-up in reach, a bite. Wanders
    when it has nobody."""

    def think(self, ctx: AIContext, dt: float) -> None:
        super().think(ctx, dt)
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
            self.go(ctx, *self.wander_goal(dt), dt, self.espec.speed * 0.4)
            return
        goal = (t.x, t.y) if self.sees_target else self.last_known
        if goal is None:
            return
        reach = self.espec.attack_radius + (t.hit_radius if self.sees_target else 0)
        if self.sees_target and self.dist_to(t) <= reach and self.cooldown <= 0:
            self.facing = self.angle_to(t.x, t.y)
            self.windup = self.espec.windup
            return
        self.go(ctx, *goal, dt, self.espec.speed)


class Crow(Chaser):
    """The scarecrow's crow: flies over everything, and after CROW_LIFE s
    it's had enough and flaps off (gone, no reward)."""

    flies = True

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.life = config.CROW_LIFE
        self.alert = True

    def can_see(self, world, other) -> bool:          # (up in the air)
        return math.hypot(other.x - self.x, other.y - self.y) <= self.espec.sight

    def think(self, ctx: AIContext, dt: float) -> None:
        self.life -= dt
        if self.life <= 0:
            self.hp = 0.0
            self.last_hit_by = None
            return
        super().think(ctx, dt)

    def on_death(self, ctx: AIContext) -> None:
        ctx.effects.append(Effect("roll_dust", self.x, self.y))


# --- Beasts ----------------------------------------------------------------------------


class Hound(PlainsCreature):
    """A pack hunter: circles its target at HOUND_ORBIT tiles, each hound
    at its own angle, and darts in to bite when it's its turn -- one hound
    of the pack per target at a time (Hound._turns)."""

    _turns: dict = {}             # id(target) -> the hound darting at it

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.slot = self.rng.uniform(0, math.tau)
        self.dash = 0.0
        self.wait = self.rng.uniform(*config.HOUND_WAIT)

    def think(self, ctx: AIContext, dt: float) -> None:
        super().think(ctx, dt)
        self.sense(ctx, dt)
        t = self.target
        if t is None or not self.alert:
            self._release()
            self.go(ctx, *self.wander_goal(dt), dt, self.espec.speed * 0.4)
            return
        if not self.sees_target:
            self._release()
            if self.last_known is not None:
                self.go(ctx, *self.last_known, dt, self.espec.speed)
            return
        if self.dash > 0:                           # darting in
            self.dash -= dt
            self.facing = self.angle_to(t.x, t.y)
            self.go(ctx, t.x, t.y, dt, self.espec.speed * config.HOUND_DASH)
            if self.dist_to(t) <= self.espec.attack_radius + t.hit_radius:
                self.bite(ctx)
                self.dash = 0.0
            if self.dash <= 0:
                self._release()
                self.wait = self.rng.uniform(*config.HOUND_WAIT)
            return
        self.slot += dt * 0.6                       # circle round
        gx = t.x + math.cos(self.slot) * config.HOUND_ORBIT
        gy = t.y + math.sin(self.slot) * config.HOUND_ORBIT
        self.go(ctx, gx, gy, dt, self.espec.speed)
        self.wait -= dt
        turn = Hound._turns.get(id(t))
        free = (turn is None or not turn.alive or turn.dash <= 0
                or not any(a is turn for a in ctx.actors))      # (asleep: not about)
        if self.wait <= 0 and self.cooldown <= 0 and free:
            Hound._turns[id(t)] = self
            self.dash = config.HOUND_DASH_TIME

    def _release(self) -> None:
        for k, h in list(Hound._turns.items()):
            if h is self:
                del Hound._turns[k]

    def on_death(self, ctx: AIContext) -> None:
        self._release()
        ctx.effects.append(Effect("explosion", self.x, self.y))


class Hawk(PlainsCreature):
    """Circles its target over everything; then hovers, lined up (the line
    shows: `aim`), dives straight along it hitting the first body it meets
    (once per dive), and climbs away before circling again."""

    flies = True

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.state = "circle"
        self.timer = self.rng.uniform(*config.HAWK_CIRCLE)
        self.orbit = self.rng.uniform(0, math.tau)
        self.aim = 0.0
        self.dived = 0.0
        self.struck = False

    def can_see(self, world, other) -> bool:
        return math.hypot(other.x - self.x, other.y - self.y) <= self.espec.sight

    def think(self, ctx: AIContext, dt: float) -> None:
        super().think(ctx, dt)
        self.sense(ctx, dt)
        t = self.target
        if self.state == "mark":
            self.timer -= dt
            self.tell = self.timer
            if self.timer <= 0:
                self.state, self.dived, self.struck, self.tell = "dive", 0.0, False, 0.0
            return
        if self.state == "dive":
            step = config.HAWK_DIVE_SPEED * dt
            self.x += math.cos(self.aim) * step
            self.y += math.sin(self.aim) * step
            self._moved = step
            self.walked += step
            self.dived += step
            if not self.struck:
                for a in ctx.actors:
                    if a is self or not a.hittable:
                        continue
                    if math.hypot(a.x - self.x, a.y - self.y) <= self.hit_radius + a.hit_radius:
                        _numbered_hit(a, self.espec.damage * self.damage_mult, self, self.aim, ctx)
                        self.struck = True
                        break
            if self.dived >= config.HAWK_DIVE_LENGTH:
                self.state, self.timer = "climb", config.HAWK_CLIMB
            return
        if self.state == "climb":
            self.timer -= dt
            self.go(ctx, self.x + math.cos(self.aim) * 5, self.y + math.sin(self.aim) * 5, dt,
                    self.espec.speed)
            if self.timer <= 0:
                self.state, self.timer = "circle", self.rng.uniform(*config.HAWK_CIRCLE)
            return
        if t is None or not self.alert:
            self.go(ctx, *self.wander_goal(dt), dt, self.espec.speed * 0.5)
            return
        self.orbit += dt * 0.7
        r = config.HAWK_ORBIT
        self.go(ctx, t.x + math.cos(self.orbit) * r, t.y + math.sin(self.orbit) * r, dt,
                self.espec.speed)
        self.timer -= dt
        if self.timer <= 0 and self.sees_target:
            self.state, self.timer = "mark", self.espec.windup
            self.aim = self.facing = self.angle_to(t.x, t.y)
            ctx.events.append("swing")


class Molehill(PlainsCreature):
    """Never moves. While it sees a hero it sends out a mole rat every
    MOLEHILL[0] s, up to MOLEHILL[1] of them about at once."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.timer = self.rng.uniform(1.0, config.MOLEHILL[0])

    def think(self, ctx: AIContext, dt: float) -> None:
        super().think(ctx, dt)
        self.sense(ctx, dt)
        if not self.sees_target:
            return
        self.timer -= dt
        if self.timer > 0:
            return
        every, most, reach = config.MOLEHILL
        self.timer = every
        near = sum(1 for a in ctx.actors if getattr(a, "kind_key", "") == "mole_rat" and a.alive
                   and math.hypot(a.x - self.x, a.y - self.y) <= reach)
        if near >= most:
            return
        a = self.rng.uniform(0, math.tau)
        ctx.spawned.append(("mole_rat", self.x + math.cos(a) * 1.2, self.y + math.sin(a) * 1.2))
        ctx.effects.append(Effect("burrow", self.x, self.y))


class Bull(PlainsCreature):
    """Elite. Ambles until it sees you, scrapes (the charge line shows),
    then charges BULL_CHARGE tiles: breakable things in the way are
    trampled flat and it keeps going; anyone it runs into is gored once
    per charge. It wheels round for BULL_PASSES charges in all, then rests.
    Only what doesn't break stops it -- dazed."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.state = "roam"
        self.timer = 0.0
        self.ran = 0.0
        self.passes = 0
        self.gored: set[int] = set()

    def think(self, ctx: AIContext, dt: float) -> None:
        super().think(ctx, dt)
        self.sense(ctx, dt)
        t = self.target
        if self.state in ("scrape", "dazed", "turn"):
            self.timer -= dt
            if self.state == "turn" and t is not None:
                self.facing = self.angle_to(t.x, t.y)
            if self.timer <= 0:
                if self.state == "scrape":
                    self.state, self.ran, self.gored = "charge", 0.0, set()
                elif self.state == "turn":
                    self.state, self.timer = "scrape", self.espec.windup * 0.6
                else:
                    self.state = "roam"
            return
        if self.state == "charge":
            self._charge(ctx, dt)
            return
        if t is not None and self.sees_target:
            if self.dist_to(t) <= self.espec.attack_radius and self.cooldown <= 0:
                self.facing = self.angle_to(t.x, t.y)
                self.state, self.timer, self.passes = "scrape", self.espec.windup, 0
                return
            self.go(ctx, t.x, t.y, dt, self.espec.speed)
        elif self.last_known is not None:
            self.go(ctx, *self.last_known, dt, self.espec.speed)
        else:
            self.go(ctx, *self.wander_goal(dt), dt, self.espec.speed * 0.5)

    def _trample(self, ctx: AIContext) -> bool:
        """What blocks it, along the whole front of its body (its middle
        and both sides): breakable things are trampled. Returns False if
        something that doesn't break is there (it's stopped)."""
        ca, sa = math.cos(self.facing), math.sin(self.facing)
        ahead = self.hit_radius + 0.4
        side = self.half / config.TILE_PX_W
        free = True
        seen = set()
        for v in (-side, 0.0, side):
            tx = math.floor(self.x + ca * ahead - sa * v)
            ty = math.floor(self.y + sa * ahead + ca * v)
            if (tx, ty) in seen:
                continue
            seen.add((tx, ty))
            tile = ctx.world.tile_at(tx, ty)
            if not tile.solid:
                continue
            if tile.destructible:
                ev = combat.crush_tile(ctx.world, tx, ty, config.BULL_TRAMPLE, ctx.effects)
                if ev:
                    ctx.events.append(ev)
            else:
                free = False
        return free

    def _charge(self, ctx: AIContext, dt: float) -> None:
        step = config.BULL_CHARGE_SPEED * dt
        dx, dy = math.cos(self.facing) * step, math.sin(self.facing) * step
        x0, y0 = self.x, self.y
        self.x, self.y, bx, by = move_hull(ctx.world, self.x, self.y, 0.0, self.half, self.half,
                                           dx, dy)
        if bx or by:                                 # something in the way: break it?
            if not self._trample(ctx):
                ctx.events.append(combat.BREAK)
                ctx.effects.append(Effect("debris", self.x + math.cos(self.facing),
                                          self.y + math.sin(self.facing)))
                self.state, self.timer = "dazed", config.BULL_DAZE
                self.cooldown = self.espec.cooldown
                return
        moved = math.hypot(self.x - x0, self.y - y0)
        self._moved = moved
        self.walked += moved
        self.ran += moved
        for a in ctx.actors:
            if a is self or not a.hittable or id(a) in self.gored:
                continue
            if math.hypot(a.x - self.x, a.y - self.y) <= self.hit_radius + a.hit_radius:
                self.gored.add(id(a))
                _numbered_hit(a, self.espec.damage * self.damage_mult, self, self.facing, ctx)
                combat.push(a, ctx.world, math.cos(self.facing) * 1.5, math.sin(self.facing) * 1.5)
        if self.ran >= config.BULL_CHARGE:
            self.passes += 1
            if self.passes < config.BULL_PASSES:
                self.state, self.timer = "turn", config.BULL_TURN
            else:
                self.state = "roam"
                self.cooldown = self.espec.cooldown


# --- Bandits and folk ------------------------------------------------------------------


class Lancer(PlainsCreature):
    """A bandit on horseback. Rides out to one side of its target, wheels
    round, lowers the lance (the line shows) and gallops straight through
    where the target is and LANCER_OVERRUN tiles past, the lance hitting
    whatever it passes once per run. Then again."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.state = "wheel"
        self.side = self.rng.choice((-1, 1))
        self.aim = 0.0
        self.timer = 0.0
        self.ran = 0.0
        self.length = 0.0
        self.hit: set[int] = set()

    def think(self, ctx: AIContext, dt: float) -> None:
        super().think(ctx, dt)
        self.sense(ctx, dt)
        t = self.target
        if self.state == "lower":
            self.timer -= dt
            self.tell = self.timer
            if self.timer <= 0:
                self.state, self.ran, self.hit, self.tell = "joust", 0.0, set(), 0.0
            return
        if self.state == "joust":
            self._joust(ctx, dt)
            return
        if t is None or not self.alert or not self.sees_target:
            goal = self.last_known if (self.alert and self.last_known) else self.wander_goal(dt)
            self.go(ctx, *goal, dt, self.espec.speed * 0.5)
            return
        # Wheel out to a start point beside the target, then turn in (or
        # after LANCER_WHEEL s, wherever it got to).
        away = self.angle_to(t.x, t.y) + math.pi + self.side * 0.9
        sx = t.x + math.cos(away) * config.LANCER_START
        sy = t.y + math.sin(away) * config.LANCER_START
        self.timer += dt
        if self.go(ctx, sx, sy, dt, self.espec.speed * 0.8) or self.timer > config.LANCER_WHEEL \
                or (self.cooldown <= 0 and abs(self.dist_to(t) - config.LANCER_START) < 1.5):
            self.aim = self.facing = self.angle_to(t.x, t.y)
            self.length = self.dist_to(t) + config.LANCER_OVERRUN
            self.state, self.timer = "lower", self.espec.windup
            self.side = -self.side

    def _joust(self, ctx: AIContext, dt: float) -> None:
        step = self.espec.speed * dt
        x0, y0 = self.x, self.y
        self.x, self.y, bx, by = move_hull(ctx.world, self.x, self.y, 0.0, self.half, self.half,
                                           math.cos(self.aim) * step, math.sin(self.aim) * step)
        moved = math.hypot(self.x - x0, self.y - y0)
        self._moved = moved
        self.walked += moved
        self.ran += moved
        tip_x = self.x + math.cos(self.aim) * config.LANCER_REACH
        tip_y = self.y + math.sin(self.aim) * config.LANCER_REACH
        for a in ctx.actors:
            if a is self or not a.hittable or id(a) in self.hit:
                continue
            if math.hypot(a.x - tip_x, a.y - tip_y) <= a.hit_radius + 0.6:
                self.hit.add(id(a))
                _numbered_hit(a, self.espec.damage * self.damage_mult, self, self.aim, ctx)
        if bx or by or self.ran >= self.length:
            self.state, self.timer = "wheel", 0.0
            self.cooldown = self.espec.cooldown


class Priest(PlainsCreature):
    """Doesn't attack. Keeps PRIEST_RANGE from the heroes and, every
    PRIEST[0] s, heals the most hurt enemy within PRIEST[1] tiles that it
    can see by PRIEST[2] of its max HP (a green beam shows who)."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.timer = self.rng.uniform(0.5, config.PRIEST[0])

    def think(self, ctx: AIContext, dt: float) -> None:
        super().think(ctx, dt)
        self.sense(ctx, dt)
        t = self.target
        if t is not None and self.sees_target:
            d = self.dist_to(t)
            lo, hi = config.PRIEST_RANGE
            if d < lo:                                   # too close: back off
                a = self.angle_to(t.x, t.y) + math.pi
                self.go(ctx, self.x + math.cos(a) * 3, self.y + math.sin(a) * 3, dt,
                        self.espec.speed)
            elif d > hi:
                self.go(ctx, t.x, t.y, dt, self.espec.speed * 0.6)
            self.facing = self.angle_to(t.x, t.y)
        elif self.last_known is not None and self.alert:
            self.go(ctx, *self.last_known, dt, self.espec.speed * 0.6)
        else:
            self.go(ctx, *self.wander_goal(dt), dt, self.espec.speed * 0.4)
        self.timer -= dt
        if self.timer <= 0:
            self.timer = config.PRIEST[0]
            self._heal(ctx)

    def _heal(self, ctx: AIContext) -> None:
        every, reach, share = config.PRIEST
        best, worst = None, 1.0
        for a in ctx.actors:
            if a is self or not a.alive or getattr(a, "faction", "") != "enemy" \
                    or getattr(a, "boss", False) or a.hp >= a.max_hp:
                continue
            if math.hypot(a.x - self.x, a.y - self.y) > reach or not self.can_see(ctx.world, a):
                continue
            frac = a.hp / a.max_hp
            if frac < worst:
                best, worst = a, frac
        if best is None:
            return
        best.hp = min(float(best.max_hp), best.hp + best.max_hp * share)
        ctx.effects.append(Effect("heal_beam", self.x, self.y, x2=best.x, y2=best.y))
        ctx.events.append("chime")


# --- Haunted farmland and odd ones -------------------------------------------------------


class StrawGolem(Chaser):
    """A walking haystack: slow, a long wind-up and a heavy swing. When it
    dies it bursts into GOLEM_FIRE[0] patches of burning straw round where
    it fell, each burning whoever stands in it for GOLEM_FIRE[1] s."""

    def on_death(self, ctx: AIContext) -> None:
        ctx.effects.append(Effect("explosion", self.x, self.y))
        if ctx.zones is None:
            return
        n, life, radius, spread = config.GOLEM_FIRE
        for k in range(n):
            a = k * math.tau / n + self.rng.uniform(-0.3, 0.3)
            r = spread * (0.4 + 0.6 * self.rng.random()) if k else 0.0
            ctx.zones.append(Zone("trail", self.x + math.cos(a) * r, self.y + math.sin(a) * r,
                                  radius, life, config.TRAIL_EVERY, 0.0, self,
                                  (config.STATUSES["burn"].tag,), "burn"))


class Scarecrow(PlainsCreature):
    """Shuffles toward its target to SCARECROW[2] tiles; every SCARECROW[0]
    s it lets loose crows (SCARECROW[1], while fewer than SCARECROW[3] are
    about)."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.timer = self.rng.uniform(1.5, config.SCARECROW[0])

    def think(self, ctx: AIContext, dt: float) -> None:
        super().think(ctx, dt)
        self.sense(ctx, dt)
        every, flock, keep, most = config.SCARECROW
        t = self.target
        if t is not None and self.sees_target:
            if self.dist_to(t) > keep:
                self.go(ctx, t.x, t.y, dt, self.espec.speed)
            self.facing = self.angle_to(t.x, t.y)
            self.timer -= dt
            if self.timer <= 0:
                self.timer = every
                crows = sum(1 for a in ctx.actors if getattr(a, "kind_key", "") == "crow"
                            and math.hypot(a.x - self.x, a.y - self.y) < 20)
                for k in range(max(0, min(flock, most - crows))):
                    a = self.facing + (k - (flock - 1) / 2) * 0.8
                    ctx.spawned.append(("crow", self.x + math.cos(a) * 1.0,
                                        self.y + math.sin(a) * 1.0 - 0.8))
                if crows < most:
                    ctx.effects.append(Effect("roll_dust", self.x, self.y - 1.0))
        elif self.last_known is not None and self.alert:
            self.go(ctx, *self.last_known, dt, self.espec.speed)
        else:
            self.go(ctx, *self.wander_goal(dt), dt, self.espec.speed * 0.6)


class Drummer(PlainsCreature):
    """Doesn't attack. Keeps DRUM_KEEP tiles from the heroes and stays with
    its allies; every enemy within DRUM_RADIUS (not itself, not bosses)
    is drummed: faster (DRUM_HASTE) and harder-hitting (DRUM_DAMAGE) while
    in the ring (tick_drum)."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.beat = 0.0

    def think(self, ctx: AIContext, dt: float) -> None:
        super().think(ctx, dt)
        self.sense(ctx, dt)
        self.beat += dt
        allies = [a for a in ctx.actors if a is not self and a.alive
                  and getattr(a, "faction", "") == "enemy" and not getattr(a, "boss", False)
                  and math.hypot(a.x - self.x, a.y - self.y) <= config.DRUM_RADIUS]
        for a in allies:
            a.drummed = config.DRUM_TIME
        t = self.target
        if t is not None and self.sees_target and self.dist_to(t) < config.DRUM_KEEP:
            a = self.angle_to(t.x, t.y) + math.pi
            self.go(ctx, self.x + math.cos(a) * 3, self.y + math.sin(a) * 3, dt, self.espec.speed)
        elif allies:
            cx = sum(a.x for a in allies) / len(allies)
            cy = sum(a.y for a in allies) / len(allies)
            if math.hypot(cx - self.x, cy - self.y) > 2.0:
                self.go(ctx, cx, cy, dt, self.espec.speed * 0.6)
        elif t is not None and self.alert and self.last_known is not None:
            self.go(ctx, *self.last_known, dt, self.espec.speed * 0.6)
        else:
            self.go(ctx, *self.wander_goal(dt), dt, self.espec.speed * 0.4)
        if t is not None:
            self.facing = self.angle_to(t.x, t.y)


def tick_drum(e, dt: float) -> None:
    """The drummer's beat on one enemy (the game calls it every step):
    while `drummed` it hits DRUM_DAMAGE harder (its damage_mult, given and
    taken back), and the game runs its clock DRUM_HASTE faster."""
    left = getattr(e, "drummed", 0.0)
    on = getattr(e, "drum_on", False)
    if left > 0 and not on:
        e.damage_mult *= 1 + config.DRUM_DAMAGE
        e.drum_on = True
    elif left <= 0 and on:
        e.damage_mult /= 1 + config.DRUM_DAMAGE
        e.drum_on = False
    if left > 0:
        e.drummed = left - dt


def drum_haste(e) -> float:
    return config.DRUM_HASTE if getattr(e, "drummed", 0.0) > 0 else 0.0


class Shieldbearer(Shooter):
    """Elite. A big round shield takes every hit from the front (its body's
    front_armor 0) -- and anything walking behind it is covered too. It
    walks you down slowly; in reach it raises the shield (the wind-up)
    and bashes, shoving you back, then stands open for SHIELD_OPEN s: its
    front takes hits like anywhere else."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.windup = 0.0
        self.open = 0.0
        self.tell = 0.0
        self.guarded = self.spec
        from dataclasses import replace
        self.exposed = replace(self.spec, front_armor=1.0)

    def think(self, ctx: AIContext, dt: float) -> None:
        self.sense(ctx, dt)
        self.weapon.update(dt, False)
        t = self.target
        if self.open > 0:
            self.open -= dt
            self.hold(ctx, dt)
            if self.open <= 0:
                self.spec = self.guarded
            return
        if self.windup > 0:
            self.windup -= dt
            self.tell = self.windup
            self.hold(ctx, dt)
            if t is not None:                          # (keeps turning to face you)
                self.aim_angle_toward(self.angle_to(t.x, t.y), dt)
            if self.windup <= 0:
                self.tell = 0.0
                self._bash(ctx)
            return
        if t is None or not self.sees_target:
            if self.last_known is not None:
                self.search(ctx, dt)
            else:
                self.wander(ctx, dt)
            return
        aim = self.angle_to(t.x, t.y)
        self.aim_angle_toward(aim, dt)
        if (self.dist_to(t) <= self.weapon.spec.reach + t.hit_radius and self.weapon.cooldown <= 0
                and self.aim_on_target(aim, math.radians(25))):
            self.windup = config.SHIELD_WINDUP
            return
        self.drive_to(ctx, t.x, t.y, dt, arrive=self.weapon.spec.reach * 0.8)

    def _bash(self, ctx: AIContext) -> None:
        self.weapon.cooldown = self.weapon.spec.fire_interval
        hits_before = [a for a in ctx.actors if a is not self and a.alive]
        hp = {id(a): a.hp for a in hits_before}
        ctx.events += combat.swing(self, ctx.world, ctx.actors, ctx.effects,
                                   mult=self.damage_mult)
        for a in hits_before:
            if a.hp < hp[id(a)]:                       # it was hit: shoved back
                ang = self.angle_to(a.x, a.y)
                combat.push(a, ctx.world, math.cos(ang) * config.SHIELD_SHOVE,
                            math.sin(ang) * config.SHIELD_SHOVE)
        self.open = config.SHIELD_OPEN
        self.spec = self.exposed
