"""
ai/pangaea.py -- Pangaea's enemies (M31.2, design/OCEAN.md 25-26): the shore
ring's eight, the great mammals and the early hunters.

THE ECHOES (Beast). The past repeats: ECHO[0] s after one of them attacks,
a faded echo of it plays the same attack again from the same spot, at full
damage -- you saw it once, so you can read it, but you dodge everything
twice. The echo shows the attack's tell again first (as long as its own
windup, within ECHO[1]-[2] s): a ghost of the enemy where it stood, the
shape of what's coming (the cone, the circle, the line, where the shot
goes). What echoes is whatever hurts:
  * a hit on an area (a swipe, a slam, a bite, a trumpet's cone): `area`;
  * shots (a spear, bolas): `throw`, played again as the same shot, faded;
  * a body's run (a charge, a stampede, a pounce, a painted spirit's
    charge): `record_run`, played again as a ghost running the same line
    (a `Runner`), hurting what it touches;
  * something thrown in an arc (a torch): `lob`, coming down again where
    the first did (an echoed torch burns no ferns: the fire is the land's).
An echo never echoes (`replaying`). Killing the enemy cancels every echo it
still has, waiting or running (they're its own: they go with it). Only
enemies echo -- not the players, not the land (lava bombs, tar, fire), and
not what the hunters leave lying (stuck spears, traps).

The great mammals (`beast`: the fire-bearer drives them at you; traps catch
them):
  mammoth      (elite) walks in herds; trumpets (a cone that pushes you
               back), then the whole herd stampedes in parallel lanes shown
               first: stand in a gap, or roll through. Close in, a tusk sweep
  sabre-tooth  stalks you; in the tall ferns only its eyes show (it can
               still be shot). Pounces from far off along a marked line and
               pins you, biting, until you roll free
  woolly rhino its armoured front shrugs off hits; it charges, skids and
               turns slowly, so you hit it from the side or behind
  cave bear    rears up on its hind legs (the tell), swipes twice in a wide
               arc and slams down; its roar wakes the enemies near it
The early hunters:
  spear hunter keeps its distance and throws spears, fast and far; one that
               lands on open ground sticks there a few seconds, fencing lanes
  trapper      lays snares and covered pits, only faintly marked (they hold
               you; a roll carries you over); throws bolas that tangle you
  fire-bearer  throws torches that set the ferns alight (the fire spreads);
               swings its torch close in; beats the bush, driving every beast
               near it at you
  shaman       (elite) paints beasts that come alive as flat ochre spirits
               and charge once along a shown line, then fade; while it lives,
               no fire near it goes out

Their pictures: render/pangaea_art.py; their tells and ghosts:
render/pangaea.py; what they leave on the ground: systems/pangaea.py.
"""

from __future__ import annotations

import math

from .. import config
from ..entities.effects import Effect
from ..systems import combat, patterns
from ..world import tiles
from .brain import AIContext
from .creatures import _numbered_hit
from .desert import _dash
from .plains import Bull, PlainsCreature

# Where a sabre-tooth hides (only its eyes show).
FERN_COVER = frozenset((tiles.TALL_FERNS, tiles.TALL_JUNGLE_FERNS, tiles.HORSETAILS))


def _wrap(a: float) -> float:
    return (a + math.pi) % math.tau - math.pi


def inside(a, shape: str, x: float, y: float, angle: float, reach: float, half: float) -> bool:
    """Does actor `a`'s body touch the shape? A "circle" of `reach` round
    (x, y); a "cone" out to `reach` along `angle`, `half` radians either
    side; a "line" from (x, y) along `angle`, `reach` long, `half` tiles
    either side."""
    dx, dy = a.x - x, a.y - y
    r = a.hit_radius
    d = math.hypot(dx, dy)
    if shape == "circle":
        return d <= reach + r
    if shape == "cone":
        if d > reach + r:
            return False
        if d <= r + 0.3:
            return True
        return abs(_wrap(math.atan2(dy, dx) - angle)) <= half + math.asin(min(1.0, r / d))
    ca, sa = math.cos(angle), math.sin(angle)
    along = dx * ca + dy * sa
    return -r <= along <= reach + r and abs(-dx * sa + dy * ca) <= half + r


# --- The echoes ---------------------------------------------------------------------------


class Echo:
    """One attack waiting to play again: what it was (`kind`: "area",
    "shots", "run", "lob") and how (`data`), s until it plays (`t`), how long
    its tell shows before that (`tell`), and the ghost drawn meanwhile (where
    the enemy stood, which way it faced, its picture then)."""

    __slots__ = ("kind", "t", "tell", "x", "y", "facing", "sprite", "data")

    def __init__(self, kind: str, tell: float, x: float, y: float, facing: float,
                 sprite: str, data: dict) -> None:
        self.kind, self.t, self.tell = kind, config.ECHO[0], tell
        self.x, self.y, self.facing, self.sprite = x, y, facing, sprite
        self.data = data


class Runner:
    """A body running a straight line, hurting what it touches (each at most
    once): an echo of a charge or a pounce (`look` "ghost"), or a shaman's
    painted spirit (`look` "ochre"). It goes through everything: it runs a
    line already run, or it's a spirit."""

    __slots__ = ("x0", "y0", "angle", "length", "speed", "radius", "damage", "push",
                 "sprite", "look", "done", "hit")

    def __init__(self, x0, y0, angle, length, speed, radius, damage, push, sprite, look) -> None:
        self.x0, self.y0, self.angle, self.length, self.speed = x0, y0, angle, length, speed
        self.radius, self.damage, self.push = radius, damage, push
        self.sprite, self.look = sprite, look
        self.done = 0.0                       # tiles run so far
        self.hit: set[int] = set()

    @property
    def x(self) -> float:
        return self.x0 + math.cos(self.angle) * self.done

    @property
    def y(self) -> float:
        return self.y0 + math.sin(self.angle) * self.done


class Beast(PlainsCreature):
    """Every Pangaean enemy: its attacks echo (see the module's docstring).
    Subclasses write `turn`; they attack through `area`, `throw`,
    `record_run`/`ram` and `lob`, so what they do is what echoes."""

    beast = True              # a beast (not a hunter): driven by fire-bearers, caught in traps
    fire_proof = False        # the fire in the ferns doesn't burn it (the fire-bearer, the shaman)

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.clock = 0.0
        self.echoes: list[Echo] = []
        self.runners: list[Runner] = []
        self.flashes: list[list] = []     # [(shape, x, y, angle, reach, half), s left, an echo's?]
        self.lobs: list[list] = []        # [x0, y0, x1, y1, s, of s, what, an echo's?]
        self.replaying = False            # playing an echo now: what it does doesn't echo
        self.driven = 0.0                 # s left driven at you by a fire-bearer
        self.glanced = 0.0                # s left showing a hit glancing off (the rhino)

    @property
    def speed(self) -> float:
        return self.espec.speed * (config.FIREB[8] if self.driven > 0 else 1.0)

    def hurt(self, base: float) -> float:
        """`base` damage as hard as this one hits."""
        return base * self.damage_mult

    def sprite_now(self) -> str:
        return self.espec.sprite

    # --- Its turn ---------------------------------------------------------------------

    def think(self, ctx: AIContext, dt: float) -> None:
        super().think(ctx, dt)                 # (_moved, the cooldown)
        self.sense(ctx, dt)
        self.clock += dt
        self.driven = max(0.0, self.driven - dt)
        self.glanced = max(0.0, self.glanced - dt)
        self.play_echoes(ctx, dt)
        self.turn(ctx, dt)

    def turn(self, ctx: AIContext, dt: float) -> None:
        self.roam(ctx, dt)

    def roam(self, ctx: AIContext, dt: float) -> None:
        """No target in sight: to where it was last seen, or wander."""
        if self.alert and self.last_known is not None:
            self.go(ctx, *self.last_known, dt, self.speed * 0.7)
        else:
            self.go(ctx, *self.wander_goal(dt), dt, self.speed * 0.4)

    def keep(self, ctx: AIContext, t, lo: float, hi: float, dt: float) -> None:
        """Back off inside `lo`, close in beyond `hi`, hold between."""
        d = self.dist_to(t)
        if d < lo:
            a = self.angle_to(t.x, t.y) + math.pi
            self.go(ctx, self.x + math.cos(a) * 3, self.y + math.sin(a) * 3, dt, self.speed)
        elif d > hi:
            self.go(ctx, t.x, t.y, dt, self.speed * 0.8)
        self.facing = self.angle_to(t.x, t.y)

    # --- Attacks (each one echoes) ----------------------------------------------------

    def _record(self, kind: str, tell: float | None, data: dict) -> None:
        if self.replaying:                      # (an echo never echoes)
            return
        lo, hi = config.ECHO[1], config.ECHO[2]
        tell = self.espec.windup if tell is None else tell
        self.echoes.append(Echo(kind, min(hi, max(lo, tell)), self.x, self.y, self.facing,
                                self.sprite_now(), data))

    def area(self, ctx: AIContext, shape: str, x: float, y: float, angle: float, reach: float,
             half: float, damage: float, push: float = 0.0, tell: float | None = None,
             record: bool = True) -> list:
        """Hit everyone whose body touches the shape (see `inside`) for
        `damage`, pushing them `push` tiles away (along `angle` for a
        line). It echoes (unless `record` is False: part of something that
        echoes as a whole, a torch's burst). Returns who it hit."""
        hit = []
        for a in ctx.actors:
            if a is self or not a.hittable or not inside(a, shape, x, y, angle, reach, half):
                continue
            ang = angle if shape == "line" else math.atan2(a.y - y, a.x - x)
            _numbered_hit(a, damage, self, ang, ctx)
            if push:
                combat.push(a, ctx.world, math.cos(ang) * push, math.sin(ang) * push)
            hit.append(a)
        self.flashes.append([(shape, x, y, angle, reach, half), 0.25, self.replaying])
        if record:
            self._record("area", tell, dict(shape=shape, x=x, y=y, angle=angle, reach=reach,
                                            half=half, damage=damage, push=push))
        return hit

    def throw(self, ctx: AIContext, shot: str, angle: float, on_hit=None, tell: float | None = None):
        """A shot (config.PANGAEA_SHOTS) from where it stands; it echoes as
        the same shot again (its "_echo" look)."""
        shell = config.PANGAEA_SHOTS[shot]
        p = patterns.shoot(self, self.x, self.y, angle, shell, ctx.projectiles)
        p.on_hit = on_hit
        ctx.events.append(shell.sound)
        self._record("shots", tell, dict(shots=[(self.x, self.y, angle, shot, p.damage, on_hit)]))
        return p

    def ram(self, ctx: AIContext, x: float, y: float, radius: float, damage: float, push: float,
            angle: float, hit: set) -> list:
        """A running body at (x, y) hits whoever it touches (each once: `hit`
        holds who it has), pushing them along `angle`. Returns who it hit now."""
        caught = []
        for a in ctx.actors:
            if a is self or not a.hittable or id(a) in hit or combat.drafting(a):
                continue
            if math.hypot(a.x - x, a.y - y) <= radius + a.hit_radius:
                hit.add(id(a))
                _numbered_hit(a, damage, self, angle, ctx)
                if push:
                    combat.push(a, ctx.world, math.cos(angle) * push, math.sin(angle) * push)
                caught.append(a)
        return caught

    def record_run(self, x0: float, y0: float, angle: float, length: float, speed: float,
                   radius: float, damage: float, push: float, tell: float | None = None,
                   sprite: str | None = None) -> None:
        """A run it made (or a spirit's it set going): it echoes as a ghost
        running the same line."""
        if length > 0.2:
            self._record("run", tell, dict(x0=x0, y0=y0, angle=angle, length=length, speed=speed,
                                           radius=radius, damage=damage, push=push,
                                           sprite=sprite or self.sprite_now()))

    def lob(self, ctx: AIContext, x1: float, y1: float, flight: float, what: str,
            tell: float | None = None) -> None:
        """Throw something in an arc to (x1, y1), landing `flight` s later
        (`landed`); where it'll land shows meanwhile. It echoes."""
        self.lobs.append([self.x, self.y, x1, y1, 0.0, flight, what, self.replaying])
        self._record("lob", tell, dict(x0=self.x, y0=self.y, x1=x1, y1=y1, flight=flight,
                                       what=what))

    def landed(self, ctx: AIContext, x: float, y: float, what: str, echo: bool) -> None:
        """Something it threw came down at (x, y) (`echo`: an echo's)."""

    # --- Playing the echoes -----------------------------------------------------------

    def play_echoes(self, ctx: AIContext, dt: float) -> None:
        for f in self.flashes:
            f[1] -= dt
        self.flashes = [f for f in self.flashes if f[1] > 0]
        due = []
        for e in self.echoes:
            e.t -= dt
            if e.t <= 0:
                due.append(e)
        if due:
            self.echoes = [e for e in self.echoes if e.t > 0]
            self.replaying = True
            try:
                for e in due:
                    self._play(ctx, e)
            finally:
                self.replaying = False
        self._run_runners(ctx, dt)
        self._fly_lobs(ctx, dt)

    def _play(self, ctx: AIContext, e: Echo) -> None:
        d = e.data
        if e.kind == "area":
            self.area(ctx, **d)
            ctx.events.append("hit")
        elif e.kind == "shots":
            for x, y, angle, shot, damage, on_hit in d["shots"]:
                p = patterns.shoot(self, x, y, angle, config.PANGAEA_SHOTS[shot + "_echo"],
                                   ctx.projectiles)
                p.damage = damage
                p.on_hit = on_hit
                p.echo = True
            ctx.events.append(config.PANGAEA_SHOTS[d["shots"][0][3]].sound)
        elif e.kind == "run":
            self.runners.append(Runner(d["x0"], d["y0"], d["angle"], d["length"], d["speed"],
                                       d["radius"], d["damage"], d["push"], d["sprite"], "ghost"))
        elif e.kind == "lob":
            self.lobs.append([d["x0"], d["y0"], d["x1"], d["y1"], 0.0, d["flight"], d["what"], True])

    def _run_runners(self, ctx: AIContext, dt: float) -> None:
        for r in self.runners:
            r.done = min(r.length, r.done + r.speed * dt)
            self.ram(ctx, r.x, r.y, r.radius, r.damage, r.push, r.angle, r.hit)
        self.runners = [r for r in self.runners if r.done < r.length]

    def _fly_lobs(self, ctx: AIContext, dt: float) -> None:
        for b in self.lobs:
            b[4] += dt
            if b[4] >= b[5]:
                self.landed(ctx, b[2], b[3], b[6], b[7])
        self.lobs = [b for b in self.lobs if b[4] < b[5]]

    def on_death(self, ctx: AIContext) -> None:
        """Its echoes die with it (waiting or running); what's already in
        the air still comes down."""
        for b in self.lobs:
            self.landed(ctx, b[2], b[3], b[6], b[7])
        self.lobs, self.echoes, self.runners = [], [], []
        ctx.effects.append(Effect("debris", self.x, self.y))


# --- The great mammals ----------------------------------------------------------------------


class Mammoth(Beast):
    """Elite, in herds (MAMMOTH). Every MAMMOTH[0] s it trumpets: a cone
    that pushes you back; then its whole herd takes parallel lanes, shown
    first, and stampedes down them. Close in, a tusk sweep."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.state = "roam"           # roam | trumpet | tusk | lane | stampede | dazed
        self.timer = 0.0
        self.aim = 0.0
        self.lane_to: tuple[float, float] | None = None
        self.ran = 0.0
        self.run_from = (self.x, self.y)
        self.gored: set[int] = set()
        self.trumpet_cd = self.rng.uniform(2.0, config.MAMMOTH[0])

    def sprite_now(self) -> str:
        return "mammoth_trumpet" if self.state == "trumpet" else "mammoth"

    def turn(self, ctx: AIContext, dt: float) -> None:
        (every, windup, cone, reach, push, mult, _, _, _, speed, _, arc,
         shove) = config.MAMMOTH
        self.trumpet_cd = max(0.0, self.trumpet_cd - dt)
        t = self.target
        if self.state == "trumpet":
            self.timer -= dt
            self.tell = max(self.timer, 1e-3)
            if t is not None:
                self.facing = self.aim = self.angle_to(t.x, t.y)
            if self.timer <= 0:
                self.tell = 0.0
                self.area(ctx, "cone", self.x, self.y, self.facing, reach, math.radians(cone) / 2,
                          self.hurt(self.espec.damage * mult), push, tell=windup)
                ctx.effects.append(Effect("scream", self.x, self.y, self.facing, size=reach))
                ctx.events.append("hex")
                self._call_herd(ctx)
            return
        if self.state == "tusk":
            self.timer -= dt
            self.tell = max(self.timer, 1e-3)
            if self.timer <= 0:
                self.tell = 0.0
                self.area(ctx, "cone", self.x, self.y, self.facing, self.espec.attack_radius,
                          math.radians(arc) / 2, self.hurt(self.espec.damage), shove)
                ctx.events.append("hit")
                self.state, self.cooldown = "roam", self.espec.cooldown
            return
        if self.state == "lane":
            self.timer -= dt
            self.tell = max(self.timer, 1e-3)
            if self.lane_to is not None:
                if self.go(ctx, *self.lane_to, dt, speed * 0.6):
                    self.lane_to = None
            self.facing = self.aim
            if self.timer <= 0:
                self.tell = 0.0
                self.state, self.ran, self.run_from = "stampede", 0.0, (self.x, self.y)
                self.gored = set()
            return
        if self.state == "stampede":
            self._stampede(ctx, dt)
            return
        if self.state == "dazed":
            self.timer -= dt
            if self.timer <= 0:
                self.state = "roam"
            return
        if t is None or not self.sees_target:
            self.roam(ctx, dt)
            return
        d = self.dist_to(t)
        if self.trumpet_cd <= 0 and d <= reach * 1.6:
            self.state, self.timer, self.trumpet_cd = "trumpet", windup, every
            self.facing = self.aim = self.angle_to(t.x, t.y)
            return
        if self.cooldown <= 0 and d <= self.espec.attack_radius + t.hit_radius:
            self.state, self.timer = "tusk", self.espec.windup
            self.facing = self.angle_to(t.x, t.y)
            return
        self.go(ctx, t.x, t.y, dt, self.speed)

    def _call_herd(self, ctx: AIContext) -> None:
        """Its herd (every mammoth within MAMMOTH[6] tiles that's free, and
        itself) takes parallel lanes along its aim, MAMMOTH[7] apart: it
        keeps the middle one (through you), the others go to either side."""
        _, _, _, _, _, _, herd_reach, gap, shown, _, _, _, _ = config.MAMMOTH
        a = self.aim
        ca, sa = math.cos(a), math.sin(a)
        px, py = -sa, ca
        herd = [m for m in ctx.actors if isinstance(m, Mammoth) and m is not self and m.alive
                and m.state in ("roam", "tusk") and self.dist_to(m) <= herd_reach]
        sides = {-1: 0, 1: 0}
        for m in sorted(herd, key=lambda m: abs((m.x - self.x) * px + (m.y - self.y) * py)):
            across = (m.x - self.x) * px + (m.y - self.y) * py
            side = -1 if across < 0 else 1
            sides[side] += 1
            off = side * sides[side] * gap
            along = max(-3.0, min(1.0, (m.x - self.x) * ca + (m.y - self.y) * sa))
            m.lane(a, (self.x + px * off + ca * along, self.y + py * off + sa * along), shown)
        self.lane(a, None, shown)

    def lane(self, angle: float, to, shown: float) -> None:
        self.state, self.timer, self.aim, self.lane_to = "lane", shown, angle, to
        self.facing = angle
        self.tell = shown

    def _stampede(self, ctx: AIContext, dt: float) -> None:
        speed, length = config.MAMMOTH[9], config.MAMMOTH[10]
        self.facing = self.aim
        moved, blocked = _dash(self, ctx, self.aim, speed, dt)
        if blocked and not Bull._trample(self, ctx):          # (the bull's trampling)
            ctx.events.append(combat.BREAK)
            ctx.effects.append(Effect("debris", self.x + math.cos(self.aim), self.y + math.sin(self.aim)))
            self._end_run(stop=True)
            return
        self.ran += moved
        self.ram(ctx, self.x, self.y, self.hit_radius, self.hurt(self.espec.damage), 2.0,
                 self.aim, self.gored)
        if self.ran >= length:
            self._end_run(stop=False)

    def _end_run(self, stop: bool) -> None:
        self.record_run(*self.run_from, self.aim, self.ran, config.MAMMOTH[9], self.hit_radius,
                        self.hurt(self.espec.damage), 2.0, tell=config.MAMMOTH[8],
                        sprite="mammoth")
        self.state = "dazed" if stop else "roam"
        self.timer = config.BULL_DAZE if stop else 0.0          # (a wall dazes it like the bull)
        self.cooldown = self.espec.cooldown


class SabreTooth(Beast):
    """Stalks you (SABRE); in tall ferns only its eyes show. From SABRE[1]-
    [2] tiles it crouches (its line shows) and pounces; caught, you're
    pinned and bitten until you roll free."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.state = "stalk"          # stalk | crouch | pounce | pin | dazed
        self.timer = 0.0
        self.aim = 0.0
        self.length = 0.0
        self.ran = 0.0
        self.run_from = (self.x, self.y)
        self.pinned = None
        self.pin_t = 0.0
        self.bite_t = 0.0
        self.offset = (0.0, 0.0)
        self.hidden = False
        self.side = self.rng.choice((-1, 1))
        self.mauled: set[int] = set()

    def sprite_now(self) -> str:
        if self.hidden:
            return "sabre_tooth_eyes"
        return "sabre_tooth_pounce" if self.state in ("pounce", "pin") else "sabre_tooth"

    def turn(self, ctx: AIContext, dt: float) -> None:
        slow, lo, hi, speed, bite, every, most, daze = config.SABRE
        tile = ctx.world.tile_at(math.floor(self.x), math.floor(self.y))
        self.hidden = tile in FERN_COVER and self.state in ("stalk", "crouch") \
            and self.hurt_flash <= 0
        t = self.target
        if self.state == "pin":
            h = self.pinned
            self.pin_t += dt
            if h is None or not h.alive or h.rolling or self.pin_t >= most:
                self._let_go(ctx, rolled=h is not None and h.alive and h.rolling)
                return
            self.x, self.y = h.x + self.offset[0], h.y + self.offset[1]
            self.facing = self.angle_to(h.x, h.y)
            h.slowed(0.0, 0.25)
            self.bite_t -= dt
            if self.bite_t <= 0:
                self.bite_t = every
                self.area(ctx, "circle", h.x, h.y, 0.0, 0.3, 0.0, self.hurt(bite), tell=0.35)
            return
        if self.state == "crouch":
            self.timer -= dt
            self.tell = max(self.timer, 1e-3)
            self.facing = self.aim
            if self.timer <= 0:
                self.tell = 0.0
                self.state, self.ran, self.run_from = "pounce", 0.0, (self.x, self.y)
                self.mauled = set()
            return
        if self.state == "pounce":
            self.facing = self.aim
            moved, blocked = _dash(self, ctx, self.aim, speed, dt)
            self.ran += moved
            for a in self.ram(ctx, self.x, self.y, self.hit_radius, self.hurt(self.espec.damage),
                              0.0, self.aim, self.mauled):
                if getattr(a, "faction", "") == "player" and a.alive and not a.rolling:
                    self._end_pounce()
                    self._pin(a)
                    return
            if blocked or self.ran >= self.length:
                self._end_pounce()
                self.state, self.timer = "dazed", 0.4
            return
        if self.state == "dazed":
            self.timer -= dt
            if self.timer <= 0:
                self.state = "stalk"
            return
        if t is None or not self.sees_target:
            self.roam(ctx, dt)
            return
        d = self.dist_to(t)
        if self.cooldown <= 0 and lo <= d <= hi:
            self.state, self.timer = "crouch", self.espec.windup
            self.aim = self.facing = self.angle_to(t.x, t.y)
            self.length = min(hi + 1.5, d + 1.5)
            return
        if d > hi * 0.8:
            self.go(ctx, t.x, t.y, dt, self.speed * slow)
        elif d < lo:
            a = self.angle_to(t.x, t.y) + math.pi
            self.go(ctx, self.x + math.cos(a) * 3, self.y + math.sin(a) * 3, dt, self.speed * slow)
        else:                                  # (circling, waiting for its moment)
            a = self.angle_to(t.x, t.y) + math.pi + self.side * 0.6
            gx, gy = t.x + math.cos(a) * d, t.y + math.sin(a) * d
            self.go(ctx, gx, gy, dt, self.speed * slow * 0.6)
        self.facing = self.angle_to(t.x, t.y)

    def _end_pounce(self) -> None:
        self.record_run(*self.run_from, self.aim, self.ran, config.SABRE[3], self.hit_radius,
                        self.hurt(self.espec.damage), 1.0, sprite="sabre_tooth_pounce")
        self.cooldown = self.espec.cooldown

    def _pin(self, h) -> None:
        a = self.rng.uniform(0.0, math.tau)
        self.state, self.pinned, self.pin_t, self.bite_t = "pin", h, 0.0, 0.25
        self.offset = (math.cos(a) * h.hit_radius * 0.8, math.sin(a) * h.hit_radius * 0.6)

    def _let_go(self, ctx: AIContext, rolled: bool) -> None:
        h, self.pinned = self.pinned, None
        self.state, self.timer = "dazed", config.SABRE[7]
        self.cooldown = self.espec.cooldown
        if h is None:
            return
        dx, dy = self.x - h.x, self.y - h.y
        d = math.hypot(dx, dy) or 1.0
        combat.push(self, ctx.world, dx / d * 2.0, dy / d * 2.0)
        if rolled:
            ctx.effects.append(Effect("toast", h.x, h.y - 1.5, label="ROLLED FREE!"))


class WoollyRhino(Beast):
    """Its armoured front shrugs off hits (RHINO[0], x RHINO[1]). It scrapes
    (its line shows), charges, skids, and turns slowly back toward you."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.state = "roam"           # roam | scrape | charge | skid | turn | dazed
        self.timer = 0.0
        self.aim = 0.0
        self.ran = 0.0
        self.run_from = (self.x, self.y)
        self.gored: set[int] = set()

    def take_damage(self, amount, source, from_angle):
        if from_angle is not None:
            came_from = from_angle + math.pi
            if abs(_wrap(came_from - self.facing)) < math.radians(config.RHINO[0]):
                amount *= config.RHINO[1]
                self.glanced = 0.25
        return super().take_damage(amount, source, from_angle)

    def turn(self, ctx: AIContext, dt: float) -> None:
        _, _, speed, length, skid, rate, toss, daze = config.RHINO
        t = self.target
        if self.state == "scrape":
            self.timer -= dt
            self.tell = max(self.timer, 1e-3)
            self.facing = self.aim
            if self.timer <= 0:
                self.tell = 0.0
                self.state, self.ran, self.run_from = "charge", 0.0, (self.x, self.y)
                self.gored = set()
            return
        if self.state in ("charge", "skid"):
            v = speed
            if self.state == "skid":
                self.timer -= dt
                v = speed * max(0.0, self.timer) / skid
            self.facing = self.aim
            moved, blocked = _dash(self, ctx, self.aim, v, dt)
            if blocked and not Bull._trample(self, ctx):
                ctx.events.append(combat.BREAK)
                self._end_run()
                self.state, self.timer = "dazed", daze
                return
            self.ran += moved
            self.ram(ctx, self.x, self.y, self.hit_radius, self.hurt(self.espec.damage), toss,
                     self.aim, self.gored)
            if self.state == "charge" and self.ran >= length:
                self.state, self.timer = "skid", skid
            elif self.state == "skid" and self.timer <= 0:
                self._end_run()
                self.state = "turn"
            return
        if self.state == "dazed":
            self.timer -= dt
            if self.timer <= 0:
                self.state = "turn"
            return
        if t is None or not self.sees_target:
            self.state = "roam"
            self.roam(ctx, dt)
            return
        want = self.angle_to(t.x, t.y)
        if self.state == "turn":                 # (slowly round: hit it from the side)
            diff = _wrap(want - self.facing)
            step = rate * dt
            self.facing = _wrap(self.facing + max(-step, min(step, diff)))
            if abs(diff) > step:
                return
        if self.cooldown <= 0:
            self.state, self.timer = "scrape", self.espec.windup
            self.aim = self.facing = want
            return
        self.state = "roam"
        self.go(ctx, t.x, t.y, dt, self.speed)

    def _end_run(self) -> None:
        self.record_run(*self.run_from, self.aim, self.ran, config.RHINO[2], self.hit_radius,
                        self.hurt(self.espec.damage), config.RHINO[6], sprite="woolly_rhino")
        self.cooldown = self.espec.cooldown


class CaveBear(Beast):
    """It rears up (the windup), swipes twice in a wide arc and slams down
    (BEAR); its roar (on first sight, then every BEAR[6] s) wakes every
    enemy within BEAR[7] tiles and sends them at you."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.state = "roam"           # roam | rear | swipe | slam | open
        self.timer = 0.0
        self.swipes = 0
        self.roar_cd = 0.0
        self.roared = False

    def sprite_now(self) -> str:
        return "cave_bear_rear" if self.state in ("rear", "swipe", "slam") else "cave_bear"

    def turn(self, ctx: AIContext, dt: float) -> None:
        arc, gap, ahead, slam_r, slam_x, rest, roar_every, _ = config.BEAR
        self.roar_cd = max(0.0, self.roar_cd - dt)
        t = self.target
        if t is not None and self.sees_target and (not self.roared or self.roar_cd <= 0) \
                and self.state == "roam":
            self._roar(ctx, t)
        if self.state == "rear":
            self.timer -= dt
            self.tell = max(self.timer, 1e-3)
            if t is not None and self.timer > 0.25:
                self.facing = self.angle_to(t.x, t.y)
            if self.timer <= 0:
                self.tell = 0.0
                self._swipe(ctx, arc, self.espec.windup)
                self.state, self.timer, self.swipes = "swipe", gap, 1
            return
        if self.state == "swipe":
            self.timer -= dt
            if self.timer <= 0:
                if self.swipes < 2:
                    self._swipe(ctx, arc, gap)
                    self.swipes, self.timer = 2, gap
                else:
                    self.state, self.timer = "slam", 0.0
            return
        if self.state == "slam":
            x = self.x + math.cos(self.facing) * ahead
            y = self.y + math.sin(self.facing) * ahead
            self.area(ctx, "circle", x, y, self.facing, slam_r, 0.0,
                      self.hurt(self.espec.damage * slam_x), 1.0, tell=gap)
            ctx.effects.append(Effect("debris", x, y))
            ctx.events.append(combat.BREAK)
            self.state, self.timer = "open", rest
            return
        if self.state == "open":
            self.timer -= dt
            if self.timer <= 0:
                self.state, self.cooldown = "roam", self.espec.cooldown
            return
        if t is None or not self.sees_target:
            self.roam(ctx, dt)
            return
        if self.cooldown <= 0 and self.dist_to(t) <= self.espec.attack_radius + t.hit_radius:
            self.state, self.timer = "rear", self.espec.windup
            self.facing = self.angle_to(t.x, t.y)
            return
        self.go(ctx, t.x, t.y, dt, self.speed)

    def _swipe(self, ctx: AIContext, arc: float, tell: float) -> None:
        self.area(ctx, "cone", self.x, self.y, self.facing, self.espec.attack_radius,
                  math.radians(arc) / 2, self.hurt(self.espec.damage), 1.2, tell=tell)
        ctx.events.append("hit")

    def _roar(self, ctx: AIContext, t) -> None:
        """Every enemy within BEAR[7] tiles knows where you are now."""
        self.roared, self.roar_cd = True, config.BEAR[6]
        reach = config.BEAR[7]
        ctx.effects.append(Effect("beast_roar", self.x, self.y, size=6.0))
        ctx.events.append("hex")
        for e in ctx.actors:
            if e is self or getattr(e, "faction", "") != "enemy" or not hasattr(e, "last_known"):
                continue
            if math.hypot(e.x - self.x, e.y - self.y) <= reach:
                e.alert = True
                e.last_known = (t.x, t.y)
                e.forget_timer = config.FORGET_TIME


# --- The early hunters ------------------------------------------------------------------------


class Hunter(Beast):
    """The tribe: not beasts (no fire-bearer drives them, their own traps
    don't catch them)."""

    beast = False


class SpearHunter(Hunter):
    """Keeps SPEAR[0]-[1] off; a spear every cooldown, leading you. One that
    lands on open ground sticks there (systems/pangaea.stick_spear)."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.spears: list = []        # its spears in flight (to stick where they land)

    def turn(self, ctx: AIContext, dt: float) -> None:
        from ..systems.pangaea import stick_spear
        lo, hi, lead, _ = config.SPEAR
        for p in self.spears:
            if not p.alive and not p.hit:
                stick_spear(ctx.world, p.x - p.dir_x * 0.3, p.y - p.dir_y * 0.3, ctx.actors)
        self.spears = [p for p in self.spears if p.alive]
        t = self.target
        if self.windup > 0:
            self.windup -= dt
            self.tell = max(self.windup, 1e-3)
            if t is not None:
                self.facing = self.angle_to(t.x, t.y)
            if self.windup <= 0:
                self.tell = 0.0
                if t is not None:
                    shell = config.PANGAEA_SHOTS["spear"]
                    fly = self.dist_to(t) / shell.speed * lead
                    gx = t.x + getattr(t, "vx", 0.0) * fly
                    gy = t.y + getattr(t, "vy", 0.0) * fly
                    self.spears.append(self.throw(ctx, "spear", math.atan2(gy - self.y, gx - self.x)))
                self.cooldown = self.espec.cooldown
            return
        if t is None or not self.sees_target:
            self.roam(ctx, dt)
            return
        self.keep(ctx, t, lo, hi, dt)
        if self.cooldown <= 0 and self.dist_to(t) <= config.PANGAEA_SHOTS["spear"].max_range:
            self.windup = self.espec.windup


def tangle(victim, owner) -> None:
    """Bolas round your legs (a trapper's, or its echo's)."""
    if getattr(victim, "faction", "") == "player":
        victim.slowed(config.TRAPPER[10], config.TRAPPER[11])


class Trapper(Hunter):
    """Keeps TRAPPER[0]-[1] off, laying a snare or a pit where it stands
    every TRAPPER[2] s (they don't echo: a trap is laid, not thrown); bolas
    every cooldown (they tangle you)."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.lay_t = self.rng.uniform(1.0, config.TRAPPER[2])
        self.set_home = False

    def turn(self, ctx: AIContext, dt: float) -> None:
        from ..systems.pangaea import land, lay_trap
        lo, hi, every, most, _, pits, home = config.TRAPPER[:7]
        if not self.set_home:                    # (its traps round home, to start with)
            self.set_home = True
            for _ in range(home):
                a, r = self.rng.uniform(0, math.tau), self.rng.uniform(1.5, 4.0)
                x, y = self.home[0] + math.cos(a) * r, self.home[1] + math.sin(a) * r
                if not ctx.world.tile_at(math.floor(x), math.floor(y)).solid:
                    lay_trap(ctx.world, x, y, "pit" if self.rng.random() < pits else "snare", self)
        t = self.target
        if self.windup > 0:
            self.windup -= dt
            self.tell = max(self.windup, 1e-3)
            if t is not None:
                self.facing = self.angle_to(t.x, t.y)
            if self.windup <= 0:
                self.tell = 0.0
                if t is not None:
                    self.throw(ctx, "bolas", self.angle_to(t.x, t.y), on_hit=tangle)
                self.cooldown = self.espec.cooldown
            return
        if t is None or not self.sees_target:
            self.roam(ctx, dt)
            return
        self.keep(ctx, t, lo, hi, dt)
        self.lay_t -= dt
        if self.lay_t <= 0:
            self.lay_t = every
            mine = sum(1 for tr in land(ctx.world).traps if tr[4] == id(self))
            if mine < most and self.dist_to(t) > 2.5:
                lay_trap(ctx.world, self.x, self.y, "pit" if self.rng.random() < pits else "snare",
                         self)
        if self.cooldown <= 0 and self.dist_to(t) <= config.PANGAEA_SHOTS["bolas"].max_range * 0.9:
            self.windup = self.espec.windup


class FireBearer(Hunter):
    """Keeps FIREB[0]-[1] off; throws torches (marked where they land) that
    burst and set the ferns alight; swings its torch close in; every
    FIREB[6] s beats the bush: every beast within FIREB[7] comes for you."""

    fire_proof = True

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.move = ""                # the windup's: "torch" or "swing"
        self.swing_cd = 0.0
        self.beat_cd = self.rng.uniform(2.0, config.FIREB[6])

    def turn(self, ctx: AIContext, dt: float) -> None:
        lo, hi, flight, _, _, arc, beat_every, _, _, _ = config.FIREB
        self.swing_cd = max(0.0, self.swing_cd - dt)
        self.beat_cd = max(0.0, self.beat_cd - dt)
        t = self.target
        if self.windup > 0:
            self.windup -= dt
            self.tell = max(self.windup, 1e-3)
            if t is not None:
                self.facing = self.angle_to(t.x, t.y)
            if self.windup <= 0:
                self.tell = 0.0
                if self.move == "swing":
                    self.area(ctx, "cone", self.x, self.y, self.facing, self.espec.attack_radius,
                              math.radians(arc) / 2, self.hurt(self.espec.damage), 0.8)
                    ctx.events.append("hit")
                    self.swing_cd = 1.6
                elif t is not None:
                    a, r = self.rng.uniform(0, math.tau), self.rng.uniform(0.0, 1.0)
                    self.lob(ctx, t.x + math.cos(a) * r, t.y + math.sin(a) * r, flight, "torch")
                    ctx.events.append("bow")
                    self.cooldown = self.espec.cooldown
            return
        if t is None or not self.sees_target:
            self.roam(ctx, dt)
            return
        if self.beat_cd <= 0:
            self._beat(ctx, t)
        d = self.dist_to(t)
        if self.swing_cd <= 0 and d <= self.espec.attack_radius + t.hit_radius:
            self.move, self.windup = "swing", 0.45
            return
        self.keep(ctx, t, lo, hi, dt)
        if self.cooldown <= 0 and d <= hi + 4:
            self.move, self.windup = "torch", self.espec.windup

    def landed(self, ctx: AIContext, x: float, y: float, what: str, echo: bool) -> None:
        from ..systems.pangaea import ignite
        self.area(ctx, "circle", x, y, 0.0, config.FIREB[3], 0.0, self.hurt(self.espec.damage),
                  record=False)
        ctx.effects.append(Effect("lava_burst", x, y, size=config.FIREB[3]))
        if not echo:                             # (the fire is the land's: an echo lights none)
            ignite(ctx.world, x, y, config.FIREB[4])

    def _beat(self, ctx: AIContext, t) -> None:
        """Beating the bush: every beast within FIREB[7] tiles is driven at you."""
        self.beat_cd = config.FIREB[6]
        reach, _, secs = config.FIREB[7:]
        ctx.effects.append(Effect("beast_roar", self.x, self.y, size=4.0))
        for e in ctx.actors:
            if isinstance(e, Beast) and e.beast and e.alive \
                    and math.hypot(e.x - self.x, e.y - self.y) <= reach:
                e.driven = secs
                e.alert = True
                e.last_known = (t.x, t.y)
                e.forget_timer = config.FORGET_TIME


class Shaman(Hunter):
    """Elite. Keeps SHAMAN[0]-[1] off; every cooldown it paints (the
    windup; the spirit's line shows) a mammoth or a sabre-tooth that comes
    alive as a flat ochre spirit, charges once along the line and fades.
    While it lives no fire near it goes out (systems/pangaea.Land)."""

    fire_proof = True

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.painting = ""            # "mammoth" / "sabre" while it paints
        self.spot = (self.x, self.y)  # where the spirit is painted
        self.aim = 0.0

    def sprite_now(self) -> str:
        return "shaman_paint" if self.painting else "shaman"

    def turn(self, ctx: AIContext, dt: float) -> None:
        lo, hi, m_speed, m_rad, m_dmg, s_speed, s_rad, s_dmg, length, _ = config.SHAMAN
        t = self.target
        if self.painting:
            self.windup -= dt
            self.tell = max(self.windup, 1e-3)
            if t is not None and self.windup > 0.3:
                self.aim = math.atan2(t.y - self.spot[1], t.x - self.spot[0])
                self.facing = self.angle_to(t.x, t.y)
            if self.windup <= 0:
                self.tell = 0.0
                big = self.painting == "mammoth"
                speed, rad, dmg = (m_speed, m_rad, m_dmg) if big else (s_speed, s_rad, s_dmg)
                sprite = "mammoth" if big else "sabre_tooth_pounce"
                self.runners.append(Runner(*self.spot, self.aim, length, speed, rad, self.hurt(dmg),
                                           1.5, sprite, "ochre"))
                self.record_run(*self.spot, self.aim, length, speed, rad, self.hurt(dmg), 1.5,
                                sprite=sprite)
                ctx.events.append("hex")
                self.painting, self.cooldown = "", self.espec.cooldown
            return
        if t is None or not self.sees_target:
            self.roam(ctx, dt)
            return
        self.keep(ctx, t, lo, hi, dt)
        if self.cooldown <= 0:
            self.painting = "mammoth" if self.rng.random() < 0.5 else "sabre"
            self.windup = self.espec.windup
            side = self.rng.choice((-1, 1))
            a = self.angle_to(t.x, t.y) + side * math.pi / 2
            self.spot = (self.x + math.cos(a) * 1.8, self.y + math.sin(a) * 1.8)
            self.aim = math.atan2(t.y - self.spot[1], t.x - self.spot[0])
