"""
ai/panopticon.py -- Panopticon's machines (M32.2, design/OCEAN.md 36-37): the
city's eyes, the watch and the workers.

THE ALERT (systems/alert.py). Every machine can see you, and whatever sees a
hero fills the city's alert meter (ALERT_EYES: a camera or the watch fast,
the spotter fastest, any other machine slowly). In SEARCH a machine that
sees you calls every machine near it to where you are; the turrets wake.
`Machine` is the shared part: it reports what it sees, makes the calls,
lobs things, and knows the city's patterns (the land's dangers never touch
it; the belts carry it like anyone: systems/panopticon._carry).

The eyes (they live at fixed places: `residents`):
  camera       on a pole at a street corner, panning across the crossing;
               seeing you, it stops and follows you. A few hits break it
  turret       on the pavement against a block's wall, shut until the city
               searches; then it fires bursts at whoever it sees (an
               assembler's turrets are always open)
The watch (the docks; drones and spotters patrol every district, more of
them nearer the tower):
  sentry drone hovers up and down a street, its searchlight swinging ahead:
               it sees only what's in the light. Caught in it, the alert
               rises fast and it fires short bursts. Fragile
  spotter      a camera on three long legs: never fights, keeps its distance
               where it can see you (the alert rises fastest), runs to hide
               behind a block when you come near or hurt it
  riot robot   a shield in front blocks every hit from there; it turns
               slowly, shoves you back with the shield, lobs stun charges
               that daze you a moment. Get round behind it
  warden       (elite) marks you (TARGET MARKED): lockdown while it lives;
               calls in drones, sweeps a slow beam across you, fires a
               tether that chains you to a spot until you roll free
The workers (the factory; they work until you come near, then treat you as
material; the factory's half-built robots start moving when you come close):
  welder       rushes in and drags its torch across you; leaves burning slag
  hauler       charges along a shown line carrying a crate, then throws it:
               shrapnel, and the broken crate is left as cover
  assembler    builds a turret where it stands (kill it before it's done),
               then runs to a new spot and starts again
  foreman      (elite) orders overtime (the workers near it go faster),
               calls presses down on marked spots, barks a shockwave ring

Their pictures: render/panopticon_art.py; their tells: render/panopticon.py.
"""

from __future__ import annotations

import math

from .. import config
from ..entities.effects import Effect
from ..systems import alert, combat, patterns
from ..systems.raycast import first_hit
from ..systems.zones import Zone
from ..world import tiles
from .brain import AIContext
from .creatures import _numbered_hit
from .desert import _dash
from .pangaea import _wrap, inside
from .plains import PlainsCreature


def _heroes(ctx: AIContext) -> list:
    return [h for h in ctx.players if h.alive]


def _clear(world, x0: float, y0: float, x1: float, y1: float) -> bool:
    return first_hit(world.tile_at, x0, y0, x1, y1) is None


def _daze(ctx: AIContext, h, seconds: float) -> None:
    """Dazed a moment (a riot robot's stun charge): rooted, aim wavering."""
    h.slowed(0.0, seconds)
    h.dazzled = max(getattr(h, "dazzled", 0.0), seconds)
    ctx.effects.append(Effect("toast", h.x, h.y - 1.5, label="DAZED!"))


def _beam_end(world, x: float, y: float, angle: float, length: float) -> float:
    """How far a beam from (x, y) along `angle` reaches before a wall."""
    step, d = 0.5, 0.5
    ca, sa = math.cos(angle), math.sin(angle)
    while d < length:
        t = world.tile_at(math.floor(x + ca * d), math.floor(y + sa * d))
        if t.blocks_shots:
            return d
        d += step
    return length


class Machine(PlainsCreature):
    """Every machine of Panopticon (see the module's docstring). Subclasses
    write `turn`; `can_see` is what they see by (a camera's cone, a drone's
    light), and whatever they see feeds the alert."""

    group = "machine"          # "eye" | "watch" | "workers"
    eye = "machine"            # its config.ALERT_EYES key
    hovers = False             # (a drone: the belts don't carry it)
    worker = False             # works until you come near

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.clock = 0.0
        self.working = self.worker
        self.dormant = False          # a half-built robot on the line (settle)
        self.rouse = False            # (called while it lay there: it gets up)
        self.chassis: list[tuple[int, int]] = []
        self.waking = 0.0
        self.call_t = self.rng.uniform(0.0, config.PANOPTICON_ALERT[7])
        self.overtime = 0.0           # s left on a foreman's overtime
        self.seeing = None            # the hero it sees just now (drawn: an eye on it)
        self.lobs: list[list] = []    # [x0, y0, x1, y1, s, of s, what]
        self.flashes: list[list] = [] # [(shape, x, y, angle, reach, half), s left]
        self.hunter = False           # sent at lockdown (systems/alert._send_squad)

    @property
    def hittable(self) -> bool:
        return self.alive and not self.dormant

    def settle(self, world) -> None:
        """Woken on a half-built robot on the factory's line (its tiles under
        it): it lies there as the robot until someone comes close."""
        if not self.worker:
            return
        tx, ty = math.floor(self.x), math.floor(self.y)
        cells = [(tx + i, ty + j) for j in (-1, 0) for i in (-1, 0)
                 if world.tile_at(tx + i, ty + j) is tiles.CHASSIS]
        if cells:
            self.dormant, self.chassis, self.working = True, cells, False

    def hurt(self, base: float) -> float:
        return base * self.damage_mult

    def sprite_now(self) -> str:
        return self.espec.sprite

    # --- Its turn ---------------------------------------------------------------------

    def think(self, ctx: AIContext, dt: float) -> None:
        if self.overtime > 0:                   # (a foreman's overtime: its whole clock)
            self.overtime = max(0.0, self.overtime - dt)
            dt *= config.FOREMAN[4]
        super().think(ctx, dt)                  # (_moved, the cooldown)
        self.clock += dt
        if self.dormant:
            if self.rouse or any(math.hypot(h.x - self.x, h.y - self.y) <= config.WORKER_NOTICE[1]
                                 for h in _heroes(ctx)):
                self.wake_up(ctx)
            return
        if self.waking > 0:
            self.waking -= dt
            self.tell = max(self.waking, 0.0)
            return
        self.sense(ctx, dt)
        self.call_t -= dt
        self.seeing = self.watching(ctx)
        if self.seeing is not None:
            alert.seen(ctx.world, config.ALERT_EYES[self.eye])
            self._call(ctx, self.seeing)
        if self.working:
            near = self._notice(ctx)
            if near is not None:                # (close enough: you're material now)
                self.called_to(near)
        self._fly_lobs(ctx, dt)
        for f in self.flashes:
            f[1] -= dt
        self.flashes = [f for f in self.flashes if f[1] > 0]
        self.turn(ctx, dt)

    def turn(self, ctx: AIContext, dt: float) -> None:
        self.roam(ctx, dt)

    def watching(self, ctx: AIContext):
        """The hero it sees just now, or None."""
        t = self.target
        if t is not None and self.sees_target and t.alive and getattr(t, "faction", "") == "player":
            return t
        return None

    def _notice(self, ctx: AIContext):
        """The hero come within WORKER_NOTICE[0] tiles of it, or None."""
        reach = config.WORKER_NOTICE[0]
        return next((h for h in _heroes(ctx) if math.hypot(h.x - self.x, h.y - self.y) <= reach), None)

    def _call(self, ctx: AIContext, h) -> None:
        """In SEARCH or LOCKDOWN: every machine near it learns where you are."""
        if self.call_t > 0 or alert.level_of(ctx.world) < alert.SEARCH:
            return
        self.call_t = config.PANOPTICON_ALERT[7]
        reach = config.PANOPTICON_ALERT[6]
        for m in ctx.actors:
            if m is not self and isinstance(m, Machine) and m.alive and m.group != "eye" \
                    and math.hypot(m.x - self.x, m.y - self.y) <= reach:
                m.called_to(h)

    def called_to(self, h) -> None:
        """Told where a hero is (a call, the hunter squad)."""
        self.alert = True
        self.last_known = (h.x, h.y)
        self.forget_timer = config.FORGET_TIME
        self.working = False
        if self.dormant:
            self.rouse = True

    def take_damage(self, amount, source, from_angle):
        dealt = super().take_damage(amount, source, from_angle)
        if source is not None and getattr(source, "faction", "") == "player":
            self.working = False
        return dealt

    def wake_up(self, ctx: AIContext) -> None:
        """A half-built robot starts moving: its tiles are floor now."""
        self.dormant = False
        self.waking = 0.6
        self.working = False
        for tx, ty in self.chassis:
            if ctx.world.tile_at(tx, ty) is tiles.CHASSIS:
                ctx.world.set_tile(tx, ty, tiles.FACTORY_FLOOR)
        self.chassis = []
        ctx.effects.append(Effect("spark_burst", self.x, self.y, size=1.4))
        ctx.events.append("zap")

    def roam(self, ctx: AIContext, dt: float) -> None:
        """No one in sight: to where you were last seen (or called to), or
        back to work, or wander."""
        if self.alert and self.last_known is not None:
            if self.go(ctx, *self.last_known, dt, self.speed * 0.8):
                self.last_known = None
            return
        if self.worker:
            hx, hy = self.home
            if math.hypot(hx - self.x, hy - self.y) < 1.0:
                self.working = True
                return
            self.go(ctx, hx, hy, dt, self.speed * 0.6)
            return
        self.go(ctx, *self.wander_goal(dt), dt, self.speed * 0.4)

    @property
    def speed(self) -> float:
        return self.espec.speed

    def keep(self, ctx: AIContext, t, lo: float, hi: float, dt: float) -> None:
        """Back off inside `lo`, close in beyond `hi`, hold between."""
        d = self.dist_to(t)
        if d < lo:
            a = self.angle_to(t.x, t.y) + math.pi
            self.go(ctx, self.x + math.cos(a) * 3, self.y + math.sin(a) * 3, dt, self.speed)
        elif d > hi or not self.sees_target:
            self.go(ctx, t.x, t.y, dt, self.speed * 0.8)
        self.facing = self.angle_to(t.x, t.y)

    def turn_to(self, want: float, rate: float, dt: float) -> bool:
        diff = _wrap(want - self.facing)
        step = rate * dt
        self.facing = _wrap(self.facing + max(-step, min(step, diff)))
        return abs(diff) <= step

    # --- Hitting --------------------------------------------------------------------

    def hit_area(self, ctx: AIContext, shape: str, x: float, y: float, angle: float,
                 reach: float, half: float, damage: float, push: float = 0.0) -> list:
        """Hit every hero whose body touches the shape (ai/pangaea.inside)."""
        hit = []
        for h in _heroes(ctx):
            if not h.hittable or not inside(h, shape, x, y, angle, reach, half):
                continue
            ang = angle if shape == "line" else math.atan2(h.y - y, h.x - x)
            if damage > 0:
                _numbered_hit(h, damage, self, ang, ctx)
            if push:
                combat.push(h, ctx.world, math.cos(ang) * push, math.sin(ang) * push)
            hit.append(h)
        self.flashes.append([(shape, x, y, angle, reach, half), 0.25])
        return hit

    def shoot(self, ctx: AIContext, shot: str, angle: float, x=None, y=None, on_hit=None):
        shell = config.PANOPTICON_SHOTS[shot]
        p = patterns.shoot(self, self.x if x is None else x, self.y if y is None else y, angle,
                           shell, ctx.projectiles)
        p.on_hit = on_hit
        ctx.events.append(shell.sound)
        return p

    def lob(self, x1: float, y1: float, flight: float, what: str) -> None:
        """Throw something in an arc to (x1, y1), landing `flight` s later
        (`landed`); where it'll land shows meanwhile."""
        self.lobs.append([self.x, self.y, x1, y1, 0.0, flight, what])

    def _fly_lobs(self, ctx: AIContext, dt: float) -> None:
        if not self.lobs:
            return
        for b in self.lobs:
            b[4] += dt
            if b[4] >= b[5]:
                self.landed(ctx, b[2], b[3], b[6])
        self.lobs = [b for b in self.lobs if b[4] < b[5]]

    def landed(self, ctx: AIContext, x: float, y: float, what: str) -> None:
        """Something it threw came down at (x, y)."""

    def on_death(self, ctx: AIContext) -> None:
        for b in self.lobs:                     # (what's in the air still comes down)
            self.landed(ctx, b[2], b[3], b[6])
        self.lobs = []
        ctx.effects.append(Effect("spark_burst", self.x, self.y, size=1.2))
        ctx.effects.append(Effect("debris", self.x, self.y))
        ctx.events.append("break")


# --- The eyes -----------------------------------------------------------------------------


class Camera(Machine):
    """On a pole at a street corner (PANOPTICON_CAMERAS): it watches a cone,
    panning across the crossing; seeing you, it stops and follows you."""

    group = "eye"
    eye = "camera"

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.base: float | None = None
        self.phase = self.rng.uniform(0.0, math.tau)

    def _face(self, world) -> None:
        """Which way it faces: the corner's diagonal with the most open ground."""
        best, most = 0.0, -1
        for k in range(4):
            a = math.pi / 4 + k * math.pi / 2
            n = sum(not world.tile_at(math.floor(self.x + math.cos(a) * r),
                                      math.floor(self.y + math.sin(a) * r)).solid
                    for r in (1.0, 2.0, 3.0, 4.5))
            if n > most:
                best, most = a, n
        self.base = self.facing = best

    def can_see(self, world, other) -> bool:
        reach, cone = config.PANOPTICON_CAMERAS[3], math.radians(config.PANOPTICON_CAMERAS[2]) / 2
        d = math.hypot(other.x - self.x, other.y - self.y)
        if d > reach:
            return False
        if not self.sees_target and abs(_wrap(math.atan2(other.y - self.y, other.x - self.x)
                                              - self.facing)) > cone:
            return False
        return _clear(world, self.x, self.y, other.x, other.y)

    def turn(self, ctx: AIContext, dt: float) -> None:
        if self.base is None:
            self._face(ctx.world)
        h = self.seeing
        if h is not None:
            self.turn_to(self.angle_to(h.x, h.y), 4.0, dt)
            return
        sweep, period = math.radians(config.PANOPTICON_CAMERAS[4]), config.PANOPTICON_CAMERAS[5]
        self.turn_to(self.base + sweep * math.sin(math.tau * self.clock / period + self.phase), 1.6, dt)

    def facing_left(self) -> bool:
        return math.cos(self.facing) < 0


class Turret(Machine):
    """Shut against a block's wall until the city searches (an assembler's
    are always open); open, bursts of PANOPTICON_TURRETS[2] shots at whoever
    it sees."""

    group = "eye"

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.armed = False            # (open: the city searches, or it's an assembler's)
        self.burst = 0
        self.burst_t = 0.0

    @property
    def built(self) -> bool:
        return getattr(self, "kind_key", "") == "built_turret"

    def sprite_now(self) -> str:
        if self.built:
            return "built_turret"
        return "turret" if self.armed else "turret_shut"

    def can_see(self, world, other) -> bool:
        if not self.armed:
            return False
        return super().can_see(world, other)

    def turn(self, ctx: AIContext, dt: float) -> None:
        self.armed = self.built or alert.level_of(ctx.world) >= alert.SEARCH
        h = self.seeing
        if not self.armed or h is None:
            self.burst, self.windup, self.tell = 0, 0.0, 0.0
            return
        self.facing = self.angle_to(h.x, h.y)
        n, gap = config.PANOPTICON_TURRETS[2], config.PANOPTICON_TURRETS[3]
        if self.burst > 0:
            self.burst_t -= dt
            if self.burst_t <= 0:
                self.burst -= 1
                self.burst_t = gap
                self.shoot(ctx, "turret_bolt", self.facing + self.rng.uniform(-0.05, 0.05))
        elif self.windup > 0:
            self.windup -= dt
            self.tell = max(self.windup, 0.0)
            if self.windup <= 0:
                self.burst, self.burst_t = n, 0.0
        elif self.cooldown <= 0:
            self.windup, self.cooldown = self.espec.windup, self.espec.cooldown


# --- The watch ---------------------------------------------------------------------------


class SentryDrone(Machine):
    """Up and down a street (DRONE), its searchlight swinging ahead: it sees
    only what's in the light. Seeing you, it keeps its distance with the
    light on you and fires bursts."""

    group = "watch"
    eye = "watch"
    hovers = True

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.route: list[tuple[float, float]] | None = None
        self.leg = 0
        self.leg_t = 0.0
        self.heading = self.rng.uniform(0.0, math.tau)
        self.sway = 0.0
        self.lost = 0.0
        self.prey = None
        self.burst = 0
        self.burst_t = 0.0

    @property
    def light(self) -> float:
        """Which way its searchlight points."""
        return self.heading + self.sway

    def can_see(self, world, other) -> bool:
        reach, cone = config.DRONE[2], math.radians(config.DRONE[1]) / 2
        d = math.hypot(other.x - self.x, other.y - self.y)
        if d > reach:
            return False
        if abs(_wrap(math.atan2(other.y - self.y, other.x - self.x) - self.light)) > cone:
            return False
        return _clear(world, self.x, self.y, other.x, other.y)

    def _route(self, ctx: AIContext) -> None:
        """Its beat: along the street it woke on, DRONE[0] either way."""
        ux, uy = math.cos(self.heading), math.sin(self.heading)
        layout = getattr(ctx.world, "layout", None)
        z = layout.zone("panopticon") if hasattr(layout, "zone") else None
        if z is not None:
            from ..world.zones import plan_of
            lanes = plan_of(layout, z).lanes_near(*self.home)
            if lanes:
                ux, uy = lanes[self.rng.randrange(len(lanes))][2:4]
        r = config.DRONE[0]
        hx, hy = self.home
        self.route = [(hx - ux * r, hy - uy * r), (hx + ux * r, hy + uy * r)]

    def _fly(self, ctx: AIContext, gx: float, gy: float, dt: float, speed: float) -> bool:
        x0, y0 = self.x, self.y
        done = self.go(ctx, gx, gy, dt, speed)
        if math.hypot(self.x - x0, self.y - y0) > 1e-4:
            self.turn_to_heading(math.atan2(self.y - y0, self.x - x0), 3.0, dt)
        return done

    def turn_to_heading(self, want: float, rate: float, dt: float) -> None:
        diff = _wrap(want - self.heading)
        self.heading = _wrap(self.heading + max(-rate * dt, min(rate * dt, diff)))

    def turn(self, ctx: AIContext, dt: float) -> None:
        if self.route is None:
            self._route(ctx)
        h = self.seeing
        if h is not None:
            self.prey, self.lost = h, config.DRONE[9]
        elif self.prey is not None:
            self.lost -= dt
            if self.lost <= 0 or not self.prey.alive:
                self.prey = None
        if self.prey is not None:
            t = self.prey
            self.sway = 0.0
            self.turn_to_heading(self.angle_to(t.x, t.y), 5.0, dt)
            d = self.dist_to(t)
            lo, hi = config.DRONE[5], config.DRONE[6]
            if d < lo:
                a = self.angle_to(t.x, t.y) + math.pi
                self.go(ctx, self.x + math.cos(a) * 3, self.y + math.sin(a) * 3, dt, self.speed)
            elif d > hi:
                self.go(ctx, t.x, t.y, dt, self.speed)
            self.facing = self.heading
            self._fire(ctx, t, dt)
            return
        self.burst, self.windup, self.tell = 0, 0.0, 0.0
        self.sway = math.radians(config.DRONE[3]) * math.sin(math.tau * self.clock / config.DRONE[4])
        if self.alert and self.last_known is not None:
            if self._fly(ctx, *self.last_known, dt, self.speed):
                self.last_known = None
            self.facing = self.heading
            return
        self.leg_t += dt
        if self._fly(ctx, *self.route[self.leg], dt, self.speed * 0.6) or self.leg_t > 8.0:
            self.leg ^= 1
            self.leg_t = 0.0
        self.facing = self.heading

    def _fire(self, ctx: AIContext, t, dt: float) -> None:
        n, gap = config.DRONE[7], config.DRONE[8]
        if self.burst > 0:
            self.burst_t -= dt
            if self.burst_t <= 0:
                self.burst -= 1
                self.burst_t = gap
                self.shoot(ctx, "drone_bolt", self.angle_to(t.x, t.y) + self.rng.uniform(-0.06, 0.06))
        elif self.windup > 0:
            self.windup -= dt
            self.tell = max(self.windup, 0.0)
            if self.windup <= 0:
                self.burst, self.burst_t = n, 0.0
        elif self.cooldown <= 0 and self.sees_target:
            self.windup, self.cooldown = self.espec.windup, self.espec.cooldown

    def facing_left(self) -> bool:
        return math.cos(self.heading) < 0


class Spotter(Machine):
    """Never fights (SPOTTER): it keeps its distance where it can see you
    (the alert rises fastest), and runs to hide behind a block when you
    come close or hurt it."""

    group = "watch"
    eye = "spotter"

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.state = "look"           # look | hide
        self.hide_at: tuple[float, float] | None = None
        self.hide_t = 0.0
        self.spooked = False

    def take_damage(self, amount, source, from_angle):
        dealt = super().take_damage(amount, source, from_angle)
        if dealt > 0:
            self.spooked = True
        return dealt

    def _hide_spot(self, ctx: AIContext, t) -> tuple[float, float]:
        """A spot SPOTTER[4]-[5] tiles off, away from you, out of your sight."""
        from ..systems.collision import hull_hits_solid
        away = self.angle_to(t.x, t.y) + math.pi
        lo, hi = config.SPOTTER[4], config.SPOTTER[5]
        best, best_d = None, math.inf
        for k in range(12):
            a = away + self.rng.uniform(-1.3, 1.3)
            r = self.rng.uniform(lo, hi)
            x, y = self.x + math.cos(a) * r, self.y + math.sin(a) * r
            if hull_hits_solid(ctx.world, x, y, 0.0, self.half, self.half):
                continue
            if _clear(ctx.world, t.x, t.y, x, y):
                continue
            d = math.hypot(x - self.x, y - self.y)
            if d < best_d:
                best, best_d = (x, y), d
        if best is None:
            best = (self.x + math.cos(away) * hi, self.y + math.sin(away) * hi)
        return best

    def turn(self, ctx: AIContext, dt: float) -> None:
        t = self.target
        if self.state == "hide":
            self.hide_t -= dt
            if self.hide_at is not None and self.go(ctx, *self.hide_at, dt, self.speed * 1.2):
                self.hide_at = None
            if self.hide_t <= 0:
                self.state = "look"
            return
        if t is None or not self.alert:
            self.roam(ctx, dt)
            return
        d = self.dist_to(t)
        if self.spooked or (d < config.SPOTTER[2] and self.sees_target):
            self.spooked = False
            self.state, self.hide_t = "hide", config.SPOTTER[3]
            self.hide_at = self._hide_spot(ctx, t)
            ctx.events.append("ui")
            return
        if self.sees_target:
            self.keep(ctx, t, config.SPOTTER[0], config.SPOTTER[1], dt)
        elif self.last_known is not None:
            self.go(ctx, *self.last_known, dt, self.speed * 0.8)


class RiotRobot(Machine):
    """A shield in front blocks every hit from there (RIOT); it turns
    slowly, shoves you back with the shield and lobs stun charges."""

    group = "watch"
    eye = "watch"

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.state = "walk"           # walk | shove
        self.timer = 0.0
        self.charge_t = self.rng.uniform(1.0, config.RIOT[6])
        self.blocked = 0.0

    def take_damage(self, amount, source, from_angle):
        if from_angle is not None and abs(_wrap(from_angle + math.pi - self.facing)) \
                < math.radians(config.RIOT[0]):
            amount = 0.0                         # (the shield takes it)
            self.blocked = 0.25
        return super().take_damage(amount, source, from_angle)

    def turn(self, ctx: AIContext, dt: float) -> None:
        self.blocked = max(0.0, self.blocked - dt)
        self.charge_t -= dt
        t = self.target
        if self.state == "shove":
            self.timer -= dt
            self.tell = max(self.timer, 0.0)
            if self.timer <= 0:
                self.tell = 0.0
                self.hit_area(ctx, "cone", self.x, self.y, self.facing, self.espec.attack_radius,
                              math.radians(config.RIOT[2]) / 2, self.hurt(self.espec.damage),
                              config.RIOT[3])
                ctx.events.append("hit")
                self.state, self.cooldown = "walk", self.espec.cooldown
            return
        if t is None or not self.alert:
            self.roam(ctx, dt)
            return
        want = self.angle_to(t.x, t.y)
        faced = self.turn_to(want, config.RIOT[1], dt)
        d = self.dist_to(t)
        if self.cooldown <= 0 and d <= self.espec.attack_radius + t.hit_radius \
                and abs(_wrap(want - self.facing)) < 0.6:
            self.state, self.timer = "shove", self.espec.windup
            return
        if self.charge_t <= 0 and config.RIOT[4] <= d <= config.RIOT[5] and self.sees_target:
            self.charge_t = config.RIOT[6]
            self.lob(t.x, t.y, config.RIOT[7], "stun")
            ctx.events.append("swing")
        if d > self.espec.attack_radius * 0.8 and (faced or abs(_wrap(want - self.facing)) < 0.9):
            moved, blocked = _dash(self, ctx, self.facing, self.speed, dt)
            if blocked:
                self.go(ctx, t.x, t.y, dt, self.speed)

    def landed(self, ctx: AIContext, x: float, y: float, what: str) -> None:
        _, _, _, _, _, _, _, _, wide, damage, daze = config.RIOT
        ctx.effects.append(Effect("spark_burst", x, y, size=wide))
        ctx.events.append("zap")
        for h in _heroes(ctx):
            if h.hittable and math.hypot(h.x - x, h.y - y) <= wide + h.hit_radius:
                _numbered_hit(h, self.hurt(damage), self, math.atan2(h.y - y, h.x - x), ctx)
                _daze(ctx, h, daze)

    def facing_left(self) -> bool:
        return math.cos(self.facing) < 0


class Warden(Machine):
    """Elite (WARDEN). Seeing you WARDEN_MARK s, it marks you: lockdown while it lives. It
    calls in drones, sweeps a slow beam across you, and fires a tether that
    chains you to a spot until you roll free."""

    group = "watch"
    eye = "watch"

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.state = "walk"           # walk | aim | beam | backhand
        self.timer = 0.0
        self.marked: set[int] = set()
        self.marking = None           # the hero its eye is on, marking (mark_t s so far)
        self.mark_t = 0.0
        self.drone_t = self.rng.uniform(2.0, config.WARDEN[0])
        self.tether_t = self.rng.uniform(2.0, config.WARDEN[9])
        self.cooldown = self.rng.uniform(2.0, self.espec.cooldown)
        self.beam_from = self.beam_to = 0.0
        self.beam_len = 0.0
        self.burns: dict[int, float] = {}
        self.chained: list | None = None     # [hero, anchor x, anchor y, s held]

    @property
    def beam_angle(self) -> float:
        f = min(1.0, max(0.0, self.timer / config.WARDEN[5]))
        return self.beam_from + (self.beam_to - self.beam_from) * f

    def turn(self, ctx: AIContext, dt: float) -> None:
        h = self.seeing
        if h is not None and id(h) not in self.marked:
            if self.marking is not h:                # (its eye on you WARDEN_MARK s first)
                self.marking, self.mark_t = h, 0.0
            self.mark_t += dt
            if self.mark_t >= config.WARDEN_MARK:
                self.marked.add(id(h))
                self.marking = None
                ctx.effects.append(Effect("toast", h.x, h.y - 2.0, label="TARGET MARKED"))
                ctx.events.append("whistle")
        elif h is None:
            self.marking = None
        if self.marked:
            alert.hold(ctx.world)
        self._hold_chain(ctx, dt)
        self.drone_t -= dt
        self.tether_t -= dt
        t = self.target
        if self.state == "aim":
            self.timer -= dt
            self.tell = max(self.timer, 0.0)
            if self.timer <= 0:
                self.tell = 0.0
                self.state, self.timer = "beam", 0.0
                self.burns = {}
            return
        if self.state == "beam":
            self.timer += dt
            self._beam(ctx, dt)
            if self.timer >= config.WARDEN[5]:
                self.state, self.cooldown, self.timer = "walk", self.espec.cooldown, 0.0
            return
        if self.state == "backhand":
            self.timer -= dt
            self.tell = max(self.timer, 0.0)
            if self.timer <= 0:
                self.tell = 0.0
                self.hit_area(ctx, "cone", self.x, self.y, self.facing, self.espec.attack_radius,
                              math.radians(config.WARDEN[13]) / 2, self.hurt(self.espec.damage),
                              config.WARDEN[14])
                ctx.events.append("hit")
                self.state = "walk"
            return
        if t is None or not self.alert:
            self.roam(ctx, dt)
            return
        d = self.dist_to(t)
        if self.drone_t <= 0:
            self.drone_t = config.WARDEN[0]
            self._drones(ctx)
        if self.sees_target and d <= self.espec.attack_radius + t.hit_radius and self.cooldown > 1.0:
            self.state, self.timer = "backhand", 0.5
            self.facing = self.angle_to(t.x, t.y)
            return
        if self.sees_target and self.cooldown <= 0 and d <= config.WARDEN[6]:
            arc = math.radians(config.WARDEN[4]) / 2
            side = self.rng.choice((-1, 1))
            aim = self.angle_to(t.x, t.y)
            self.beam_from, self.beam_to = aim - side * arc, aim + side * arc
            self.state, self.timer = "aim", self.espec.windup
            self.facing = aim
            ctx.events.append("hex")
            return
        if self.sees_target and self.tether_t <= 0 and d <= config.WARDEN[10] and self.chained is None:
            self.tether_t = config.WARDEN[9]
            self.shoot(ctx, "tether", self.angle_to(t.x, t.y), on_hit=self._chain)
        self.keep(ctx, t, 6.0, 10.0, dt)

    def _beam(self, ctx: AIContext, dt: float) -> None:
        """Its beam this step: from its eye along beam_angle to the first wall."""
        a = self.beam_angle
        self.facing = a
        length = config.WARDEN[6]
        self.beam_len = _beam_end(ctx.world, self.x, self.y, a, length)
        bx, by = self.x + math.cos(a) * self.beam_len, self.y + math.sin(a) * self.beam_len
        from ..systems.panopticon import _seg_dist
        for h in _heroes(ctx):
            if not h.hittable:
                continue
            if _seg_dist(h.x, h.y, self.x, self.y, bx, by) > 0.45 + h.hit_radius:
                continue
            left = self.burns.get(id(h), 0.0) - dt
            if left <= 0:
                left = config.WARDEN[8]
                _numbered_hit(h, self.hurt(config.WARDEN[7]), self, a, ctx)
                ctx.events.append("fizzle")
            self.burns[id(h)] = left

    def _drones(self, ctx: AIContext) -> None:
        """Calls in WARDEN[1] sentry drones, WARDEN[2] tiles off (not while
        WARDEN[3] are near it)."""
        from ..systems.collision import hull_hits_solid
        near = sum(1 for m in ctx.actors if isinstance(m, SentryDrone) and m.alive
                   and math.hypot(m.x - self.x, m.y - self.y) <= 20.0)
        if near >= config.WARDEN[3]:
            return
        r = config.WARDEN[2]
        made = 0
        for k in range(12):
            if made >= config.WARDEN[1]:
                break
            a = self.rng.uniform(0.0, math.tau)
            x, y = self.x + math.cos(a) * r, self.y + math.sin(a) * r
            if hull_hits_solid(ctx.world, x, y, 0.0, 0.6, 0.6):
                continue
            ctx.spawned.append(("sentry_drone", x, y))
            ctx.effects.append(Effect("spark_burst", x, y, size=1.0))
            made += 1
        if made:
            ctx.events.append("whistle")

    def _chain(self, victim, owner) -> None:
        if getattr(victim, "faction", "") != "player" or not victim.alive:
            return
        self.chained = [victim, victim.x, victim.y, 0.0]

    def _hold_chain(self, ctx: AIContext, dt: float) -> None:
        if self.chained is None:
            return
        h, ax, ay, held = self.chained
        if not h.alive:
            self.chained = None
            return
        if h.rolling:
            self.chained = None
            ctx.effects.append(Effect("toast", h.x, h.y - 1.5, label="ROLLED FREE!"))
            return
        held += dt
        if held >= config.WARDEN[12]:
            self.chained = None
            return
        self.chained[3] = held
        slack = config.WARDEN[11]
        d = math.hypot(h.x - ax, h.y - ay)
        if d > slack:
            pull = d - slack
            combat.push(h, ctx.world, (ax - h.x) / d * pull, (ay - h.y) / d * pull)

    def on_death(self, ctx: AIContext) -> None:
        self.chained = None
        super().on_death(ctx)


# --- The workers ------------------------------------------------------------------------


class Welder(Machine):
    """Rushes in (WELDER) and drags its torch across you; the slag it
    leaves burns."""

    group = "workers"
    worker = True

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.state = "walk"           # walk | flare | drag
        self.timer = 0.0
        self.scorched: set[int] = set()

    @property
    def torch(self) -> float:
        """Where the torch points mid-drag."""
        half = math.radians(config.WELDER[1]) / 2
        f = min(1.0, max(0.0, self.timer / config.WELDER[2]))
        return self.facing - half + 2 * half * f

    def turn(self, ctx: AIContext, dt: float) -> None:
        if self.working:
            return
        t = self.target
        if self.state == "flare":
            self.timer -= dt
            self.tell = max(self.timer, 0.0)
            if self.timer <= 0:
                self.tell = 0.0
                self.state, self.timer, self.scorched = "drag", 0.0, set()
                ctx.events.append("fizzle")
            return
        if self.state == "drag":
            self.timer += dt
            a = self.torch
            for h in _heroes(ctx):
                if h.hittable and id(h) not in self.scorched and inside(
                        h, "line", self.x, self.y, a, self.espec.attack_radius, 0.35):
                    self.scorched.add(id(h))
                    _numbered_hit(h, self.hurt(self.espec.damage), self, a, ctx)
            if self.timer >= config.WELDER[2]:
                self._slag(ctx)
                self.state, self.cooldown = "walk", self.espec.cooldown
            return
        if t is None or not self.alert:
            self.roam(ctx, dt)
            return
        d = self.dist_to(t)
        if self.cooldown <= 0 and d <= self.espec.attack_radius + t.hit_radius * 0.5:
            self.state, self.timer = "flare", self.espec.windup
            self.facing = self.angle_to(t.x, t.y)
            return
        self.go(ctx, t.x, t.y, dt, self.speed * (config.WELDER[0] if d > 3 else 1.0))
        self.facing = self.angle_to(t.x, t.y)

    def _slag(self, ctx: AIContext) -> None:
        if ctx.zones is None:
            return
        _, arc, _, n, wide, life, burn, every = config.WELDER
        half = math.radians(arc) / 2
        for k in range(n):
            a = self.facing - half + 2 * half * (k + 0.5) / n
            r = self.espec.attack_radius * 0.7
            ctx.zones.append(Zone("slag", self.x + math.cos(a) * r, self.y + math.sin(a) * r,
                                  wide, life, every, self.hurt(burn), self))


class Hauler(Machine):
    """Carrying a crate (HAULER): it lines up, charges down a shown line,
    then throws the crate -- shrapnel, and the broken crate left as cover.
    It fetches another; without one, a shove close in."""

    group = "workers"
    worker = True

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.state = "walk"           # walk | line | charge | dazed | shove
        self.timer = 0.0
        self.aim = 0.0
        self.ran = 0.0
        self.rammed: set[int] = set()
        self.crate = True
        self.fetch_t = 0.0

    def sprite_now(self) -> str:
        return "hauler" if self.crate else "hauler_empty"

    def turn(self, ctx: AIContext, dt: float) -> None:
        if not self.crate:
            self.fetch_t -= dt
            if self.fetch_t <= 0:
                self.crate = True
        if self.working:
            return
        t = self.target
        if self.state == "line":
            self.timer -= dt
            self.tell = max(self.timer, 0.0)
            self.facing = self.aim
            if self.timer <= 0:
                self.tell = 0.0
                self.state, self.ran, self.rammed = "charge", 0.0, set()
            return
        if self.state == "charge":
            self._charge(ctx, dt, t)
            return
        if self.state == "dazed":
            self.timer -= dt
            if self.timer <= 0:
                self.state = "walk"
                if self.crate and t is not None:
                    self._throw(ctx, t)
            return
        if self.state == "shove":
            self.timer -= dt
            self.tell = max(self.timer, 0.0)
            if self.timer <= 0:
                self.tell = 0.0
                self.hit_area(ctx, "cone", self.x, self.y, self.facing, self.espec.attack_radius,
                              math.radians(90) / 2, self.hurt(self.espec.damage), 2.0)
                ctx.events.append("hit")
                self.state, self.cooldown = "walk", self.espec.cooldown
            return
        if t is None or not self.alert:
            self.roam(ctx, dt)
            return
        d = self.dist_to(t)
        lo, hi = config.HAULER[0], config.HAULER[1]
        if self.crate and self.sees_target and self.cooldown <= 0:
            if lo <= d <= hi:
                self.state, self.timer = "line", self.espec.windup
                self.aim = self.facing = self.angle_to(t.x, t.y)
                ctx.events.append("swing")
                return
            if d < lo:
                self._throw(ctx, t)
                return
        if not self.crate and self.cooldown <= 0 and d <= self.espec.attack_radius + t.hit_radius:
            self.state, self.timer = "shove", 0.45
            self.facing = self.angle_to(t.x, t.y)
            return
        if self.crate and d < lo * 0.8:
            self.keep(ctx, t, lo, hi, dt)
        else:
            self.go(ctx, t.x, t.y, dt, self.speed)
            self.facing = self.angle_to(t.x, t.y)

    def _charge(self, ctx: AIContext, dt: float, t) -> None:
        length, speed, toss, daze = config.HAULER[2], config.HAULER[3], config.HAULER[4], config.HAULER[5]
        self.facing = self.aim
        moved, blocked = _dash(self, ctx, self.aim, speed, dt)
        self.ran += moved
        for h in _heroes(ctx):
            if h.hittable and id(h) not in self.rammed \
                    and math.hypot(h.x - self.x, h.y - self.y) <= self.hit_radius + h.hit_radius:
                self.rammed.add(id(h))
                _numbered_hit(h, self.hurt(self.espec.damage), self, self.aim, ctx)
                combat.push(h, ctx.world, math.cos(self.aim) * toss, math.sin(self.aim) * toss)
        if blocked:
            ctx.events.append(combat.BREAK)
            ctx.effects.append(Effect("debris", self.x + math.cos(self.aim), self.y + math.sin(self.aim)))
            self.state, self.timer = "dazed", daze
            return
        if self.ran >= length:
            self.state = "walk"
            if t is not None:
                self._throw(ctx, t)

    def _throw(self, ctx: AIContext, t) -> None:
        self.lob(t.x, t.y, config.HAULER[6], "crate")
        self.crate, self.fetch_t = False, config.HAULER[10]
        self.cooldown = self.espec.cooldown
        self.facing = self.angle_to(t.x, t.y)
        ctx.events.append("swing")

    def landed(self, ctx: AIContext, x: float, y: float, what: str) -> None:
        n, wide, mult = config.HAULER[7], config.HAULER[8], config.HAULER[9]
        for h in _heroes(ctx):
            if h.hittable and math.hypot(h.x - x, h.y - y) <= wide + h.hit_radius:
                _numbered_hit(h, self.hurt(self.espec.damage * mult), self,
                              math.atan2(h.y - y, h.x - x), ctx)
        tx, ty = math.floor(x), math.floor(y)
        cx, cy = tx + 0.5, ty + 0.5
        turn = self.rng.uniform(0.0, math.tau)
        for k in range(n):
            a = turn + k * math.tau / n
            self.shoot(ctx, "shrapnel", a, cx + math.cos(a) * 1.0, cy + math.sin(a) * 1.0)
        ctx.effects.append(Effect("debris", cx, cy))
        ctx.events.append("break")
        world = ctx.world
        under = world.tile_at(tx, ty)
        if not under.solid and under not in tiles.BELTS \
                and not any(math.hypot(a.x - cx, a.y - cy) < 1.0 + a.hit_radius
                            for a in ctx.actors if a.alive):
            world.set_tile(tx, ty, tiles.BROKEN_CRATE)


class Assembler(Machine):
    """Fighting, it builds a turret where it stands (ASSEMBLER; spec windup
    s: kill it first), then runs to a new spot to build the next."""

    group = "workers"
    worker = True

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.state = "walk"           # walk | build | move
        self.timer = 0.0
        self.build_at = (self.x, self.y)
        self.dest: tuple[float, float] | None = None

    @property
    def progress(self) -> float:
        return min(1.0, self.timer / self.espec.windup) if self.state == "build" else 0.0

    def turn(self, ctx: AIContext, dt: float) -> None:
        if self.working:
            return
        t = self.target
        if self.state == "build":
            self.timer += dt
            if self.timer >= self.espec.windup:
                ctx.spawned.append(("built_turret", *self.build_at))
                ctx.effects.append(Effect("spark_burst", *self.build_at, size=1.2))
                ctx.events.append("zap")
                self.state, self.timer = "move", 0.0
                self.dest = self._next_spot(ctx, t)
            return
        if self.state == "move":
            self.timer += dt
            if self.dest is None or self.go(ctx, *self.dest, dt, self.speed * 1.2) or self.timer > 4.0:
                self.state, self.dest = "walk", None
            return
        if t is None or not self.alert:
            self.roam(ctx, dt)
            return
        built = sum(1 for m in ctx.actors if isinstance(m, Turret) and m.built and m.alive
                    and math.hypot(m.x - self.x, m.y - self.y) <= 16.0)
        d = self.dist_to(t)
        if built < config.ASSEMBLER[3] and d >= 3.0:
            self.facing = self.angle_to(t.x, t.y)
            self.state, self.timer = "build", 0.0
            self.build_at = self._spot_ahead(ctx)
            ctx.events.append("ui")
            return
        self.keep(ctx, t, config.ASSEMBLER[2], config.ASSEMBLER[2] + 4.0, dt)

    def _spot_ahead(self, ctx: AIContext) -> tuple[float, float]:
        from ..systems.collision import hull_hits_solid
        x, y = self.x + math.cos(self.facing) * 1.3, self.y + math.sin(self.facing) * 1.3
        if hull_hits_solid(ctx.world, x, y, 0.0, 0.6, 0.6):
            return self.x, self.y
        return x, y

    def _next_spot(self, ctx: AIContext, t) -> tuple[float, float] | None:
        from ..systems.collision import hull_hits_solid
        lo, hi, keep = config.ASSEMBLER[0], config.ASSEMBLER[1], config.ASSEMBLER[2]
        for k in range(12):
            a = self.rng.uniform(0.0, math.tau)
            r = self.rng.uniform(lo, hi)
            x, y = self.x + math.cos(a) * r, self.y + math.sin(a) * r
            if t is not None and math.hypot(x - t.x, y - t.y) < keep:
                continue
            if not hull_hits_solid(ctx.world, x, y, 0.0, self.half, self.half):
                return x, y
        return None


class Foreman(Machine):
    """Elite (FOREMAN): orders overtime, calls presses down on marked spots
    round you, barks a shockwave ring."""

    group = "workers"
    worker = True

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.state = "walk"           # walk | call | bark
        self.timer = 0.0
        self.overtime_t = self.rng.uniform(1.0, config.FOREMAN[2])
        self.bark_t = 0.0
        self.cooldown = self.rng.uniform(1.5, self.espec.cooldown)
        self.drops: list[list] = []   # [x, y, s since marked]
        self.rings: list[list] = []   # [radius, set(hit)]

    def sprite_now(self) -> str:
        return "foreman_shout" if self.state in ("call", "bark") else "foreman"

    def turn(self, ctx: AIContext, dt: float) -> None:
        self._presses(ctx, dt)
        self._rings(ctx, dt)
        if self.working:
            return
        self.overtime_t -= dt
        self.bark_t -= dt
        t = self.target
        if self.state in ("call", "bark"):
            self.timer -= dt
            self.tell = max(self.timer, 0.0)
            if self.timer <= 0:
                self.tell = 0.0
                if self.state == "bark":
                    self.rings.append([0.0, set()])
                    ctx.events.append("pulse")
                elif t is not None:
                    self._call_presses(ctx, t)
                self.state = "walk"
            return
        if t is None or not self.alert:
            self.roam(ctx, dt)
            return
        if self.overtime_t <= 0:
            self.overtime_t = config.FOREMAN[2]
            self._overtime(ctx)
        d = self.dist_to(t)
        if self.bark_t <= 0 and d <= config.FOREMAN[11]:
            self.state, self.timer, self.bark_t = "bark", self.espec.windup, 4.0
            self.facing = self.angle_to(t.x, t.y)
            return
        if self.cooldown <= 0 and self.sees_target:
            self.state, self.timer, self.cooldown = "call", 0.5, self.espec.cooldown
            self.facing = self.angle_to(t.x, t.y)
            ctx.events.append("hex")
            return
        self.keep(ctx, t, config.FOREMAN[0], config.FOREMAN[1], dt)

    def _overtime(self, ctx: AIContext) -> None:
        reach, _, seconds = config.FOREMAN[3], config.FOREMAN[4], config.FOREMAN[5]
        for m in ctx.actors:
            if isinstance(m, Machine) and m.worker and m.alive and not m.dormant \
                    and math.hypot(m.x - self.x, m.y - self.y) <= reach:
                m.overtime = seconds
        ctx.effects.append(Effect("toast", self.x, self.y - 2.5, label="OVERTIME!"))
        ctx.events.append("whistle")

    def _call_presses(self, ctx: AIContext, t) -> None:
        n, spread = config.FOREMAN[6], config.FOREMAN[7]
        self.drops.append([t.x, t.y, 0.0])
        for k in range(n - 1):
            a = self.rng.uniform(0.0, math.tau)
            r = self.rng.uniform(1.5, spread)
            self.drops.append([t.x + math.cos(a) * r, t.y + math.sin(a) * r, 0.0])

    def _presses(self, ctx: AIContext, dt: float) -> None:
        if not self.drops:
            return
        shown, wide, damage = config.FOREMAN[8], config.FOREMAN[9], config.FOREMAN[10]
        keep = []
        for dr in self.drops:
            dr[2] += dt
            if dr[2] < shown:
                keep.append(dr)
                continue
            x, y = dr[0], dr[1]
            for h in _heroes(ctx):
                if h.hittable and math.hypot(h.x - x, h.y - y) <= wide + h.hit_radius * 0.5:
                    _numbered_hit(h, self.hurt(damage), self, 0.0, ctx)
            ctx.effects.append(Effect("spark_burst", x, y, size=wide))
            ctx.events.append("boulder")
        self.drops = keep

    def _rings(self, ctx: AIContext, dt: float) -> None:
        if not self.rings:
            return
        reach, speed, push = config.FOREMAN[12], config.FOREMAN[13], config.FOREMAN[14]
        for ring in self.rings:
            ring[0] += speed * dt
            for h in _heroes(ctx):
                if not h.hittable or id(h) in ring[1]:
                    continue
                d = math.hypot(h.x - self.x, h.y - self.y)
                if abs(d - ring[0]) <= 0.6 + h.hit_radius:
                    ring[1].add(id(h))
                    a = math.atan2(h.y - self.y, h.x - self.x)
                    _numbered_hit(h, self.hurt(self.espec.damage), self, a, ctx)
                    combat.push(h, ctx.world, math.cos(a) * push, math.sin(a) * push)
        self.rings = [r for r in self.rings if r[0] < reach]


# --- Where they live ----------------------------------------------------------------------


def residents(layout, zone) -> list[tuple[str, float, float]]:
    """Panopticon's machines that live at fixed places (rostered with their
    chunks: systems/spawner): a camera at some street corners and a turret
    against some blocks' walls (world/panopticon.Plan.camera_spots,
    turret_spots; none by the sea wall or the tower: ZONE_QUIET_MARKS), and
    the factory's crew -- a worker on each half-built
    robot on the line (it starts moving when you come close: Machine.settle),
    a welder at every third robot arm, the foreman on the floor."""
    if zone.key != "panopticon":
        return []
    from ..world.zones import plan_of
    p = plan_of(layout, zone)
    quiet = [m for m in p.marks if m.key in config.ZONE_QUIET_MARKS]   # (the sea wall, the tower)

    def clear(x, y):
        return not any(m.contains(x, y, config.LANDMARK_QUIET) for m in quiet)

    out = [("camera", x, y) for x, y, _, _ in p.camera_spots() if clear(x, y)]
    out += [("turret", x, y) for x, y, _, _ in p.turret_spots() if clear(x, y)]
    fac = next((m for m in p.marks if m.key == "panopticon_factory"), None)
    if fac is not None:
        crew = ("hauler", "assembler", "welder")
        for n, (x, y) in enumerate(fac.props.get("chassis", ())):
            out.append((crew[n % 3], x, y))
        fx, fy = p.factory
        for n, (x, y) in enumerate(fac.props.get("arms", ())):
            if n % 3 == 0:
                out.append(("welder", x, y))
        out.append(("foreman", fx + 6.5, fy + 2.5))
    return out
