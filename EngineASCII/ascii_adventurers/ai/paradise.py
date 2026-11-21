"""
ai/paradise.py -- Paradise's enemies (M29.2, design/OCEAN.md 4): the first
eight of its sixteen.

THE UNVEILING (Angel). Every one of them starts serene -- white, a gold
halo, slow hymn-like attacks -- and unveils on its own once it's hurt below
UNVEIL[0] of its max HP or a hero comes within UNVEIL[1] tiles: a tell of
UNVEIL[2] s (it flickers between its two looks; nothing stops it and it
can't be undone), then the horror: faster, deadlier, bleeding. Killing
them before they unveil is the skill. Unveiled:
  * it bleeds: a stain every few tiles it moves, some where it's hit, a
    pool where it dies (`stain`: the stains stay, so the island gets redder
    the more you fight on it);
  * under FONT[0] of its max HP it goes to the nearest blood font (within
    FONT[1] tiles) and drinks there, healing until it's back to FONT[4]:
    fight them away from the fonts.

  cherub     serene: a putto plinking a lyre (runs of slow notes), keeping
             back; unveiled: four faces on eyed wings -- it lunges and
             bites, and roars a short cone that pushes you back
  seraph     (elite) serene: hidden in six wings, slow rings of light;
             unveiled: a burning, eyed core spinning spirals of blood and
             fire
  ophan      serene: a gold halo rolling gently at you; unveiled: wheels
             within wheels, racing in straight lines, bouncing off walls,
             leaving a slick of blood that slows
  watcher    never moves. serene: a veiled pillar, slow orbs; unveiled: a
             hundred eyes, a gaze beam (its line shows first) that sweeps
  lamb       serene: a lamb that butts; unveiled: seven horns and seven
             eyes, charging straight at you along a shown line
  dove       a flock; serene they peck lazily; unveiled: bloody beaks,
             circling you and diving one after another
  locust     a swarm; serene it drifts and stings now and then; unveiled it
             swarms fast
  halo       serene: a halo drifting at you; unveiled: a buzzsaw that hunts
             you, turning wide (step aside and it overshoots)

Their serene attacks use config.PARADISE_SHOTS; drawn by render/plains.py
(their pictures: render/paradise_art.py; their tells: render/paradise.py).
"""

from __future__ import annotations

import math

from .. import config
from ..entities.effects import Effect
from ..systems import combat, patterns
from ..systems.collision import move_hull
from ..systems.raycast import first_hit
from ..systems.statuses import wounded
from ..systems.zones import Zone
from ..world import tiles
from .brain import AIContext
from .creatures import _numbered_hit
from .desert import _dash
from .plains import Bull, PlainsCreature


# --- Blood on the ground ------------------------------------------------------------------


def stain(world, x: float, y: float) -> bool:
    """Bloody the ground tile at (x, y) for good (world/tiles.STAINS: cloud
    and marble; stained cloud soaks). False if that ground doesn't stain."""
    set_tile = getattr(world, "set_tile", None)
    if set_tile is None:
        return False
    tx, ty = math.floor(x), math.floor(y)
    to = tiles.STAINS.get(world.tile_at(tx, ty).name)
    if to is None:
        return False
    set_tile(tx, ty, to)
    return True


def pool(world, x: float, y: float, radius: float) -> int:
    """A pool of stains round (x, y): every ground tile within `radius`."""
    n = 0
    r = math.ceil(radius)
    for ty in range(math.floor(y) - r, math.floor(y) + r + 1):
        for tx in range(math.floor(x) - r, math.floor(x) + r + 1):
            if math.hypot(tx + 0.5 - x, ty + 0.5 - y) <= radius:
                n += stain(world, tx + 0.5, ty + 0.5)
    return n


def fonts(world) -> list[tuple[float, float]]:
    """The middles of the world's blood fonts (Paradise's plan; a test map
    may set `world.fonts`). Worked out once per world."""
    pts = getattr(world, "fonts", None)
    if pts is not None:
        return pts
    pts = []
    layout = getattr(world, "layout", None)
    for z in getattr(layout, "zones", ()):
        if z.key == "paradise":
            from ..world.paradise import plan_of
            pts += [(fx + 0.5, float(fy)) for fx, fy in plan_of(layout, z).fonts]
    try:
        world.fonts = pts
    except AttributeError:
        pass
    return pts


def nearest_font(world, x: float, y: float, reach: float) -> tuple[float, float] | None:
    near = [f for f in fonts(world) if math.hypot(f[0] - x, f[1] - y) <= reach]
    return min(near, key=lambda f: math.hypot(f[0] - x, f[1] - y)) if near else None


def _wrap(a: float) -> float:
    return (a + math.pi) % math.tau - math.pi


# --- The unveiling -------------------------------------------------------------------------


class Angel(PlainsCreature):
    """Serene -> unveiling (UNVEIL[2] s) -> unveiled; see the module's
    docstring. Subclasses write `serene_turn` and `unveiled_turn`; the font
    and the bleeding come with it. Its pictures are its sprite and
    sprite + "_unveiled"."""

    bleed = 1.0                     # x how often it stains (small fliers less)
    drinks = True                   # goes to the fonts to heal (not the watcher or leviathan)

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.lobs: list[list] = []   # things it threw, in the air: [x0, y0, x1, y1, s, of s, what]
        self.state = "serene"
        self.timer = 0.0            # the unveiling's tell left
        self.clock = 0.0
        self.bled = 0.0             # tiles moved since its last stain
        self.sprays = 0             # hits taken since its last turn (stains by it)
        self.font: tuple[float, float] | None = None   # the font it's off to drink at
        self.font_wait = 0.0        # s before it looks for a font again
        self.font_time = 0.0        # s on the way to this one
        self.drinking = False

    # --- Its state ----------------------------------------------------------------------

    @property
    def serene(self) -> bool:
        return self.state == "serene"

    @property
    def unveiling(self) -> bool:
        return self.state == "unveiling"

    @property
    def unveiled(self) -> bool:
        return self.state == "unveiled"

    @property
    def speed(self) -> float:
        return self.espec.speed * (1.0 if self.unveiled else config.UNVEIL[3])

    def sprite_now(self) -> str:
        base = self.espec.sprite
        if self.unveiling:                 # flickering, faster as it comes
            left = self.timer / config.UNVEIL[2]
            rate = 6.0 + 20.0 * (1.0 - left)
            return base + "_unveiled" if int(self.clock * rate) % 2 else base
        return base + "_unveiled" if self.unveiled else base

    def unveil(self) -> None:
        """Start the unveiling (once)."""
        if self.state != "serene":
            return
        self.state, self.timer = "unveiling", config.UNVEIL[2]
        self.windup = 0.0
        self.alert = True

    def take_damage(self, amount, source, from_angle):
        dealt = super().take_damage(amount, source, from_angle)
        if dealt > 0 and self.alive:
            if self.unveiled:
                self.sprays = min(self.sprays + 1, 4)
            elif self.serene and self.hp < self.max_hp * config.UNVEIL[0]:
                self.unveil()
        return dealt

    # --- Its turn -----------------------------------------------------------------------

    def can_see(self, world, other) -> bool:
        if self.flies:                         # (up in the air)
            return math.hypot(other.x - self.x, other.y - self.y) <= self.espec.sight
        return super().can_see(world, other)

    def think(self, ctx: AIContext, dt: float) -> None:
        super().think(ctx, dt)                 # (_moved, the cooldown)
        self.sense(ctx, dt)
        self.clock += dt
        self._fly_lobs(ctx, dt)
        self.always(ctx, dt)
        if self.serene and any(p.alive and math.hypot(p.x - self.x, p.y - self.y) <= config.UNVEIL[1]
                               for p in ctx.players):
            self.unveil()
        if self.unveiling:
            self.timer -= dt
            self.tell = max(self.timer, 1e-3)
            t = self.target
            if t is not None:
                self.facing = self.angle_to(t.x, t.y)
            if self.timer <= 0:
                self.tell = 0.0
                self.state = "unveiled"
                self.cooldown = max(self.cooldown, 0.3)
                ctx.effects.append(Effect("unveil", self.x, self.y, size=self.hit_radius + 1.5))
                ctx.events.append("hex")
                self.sprays = 2
                self.on_unveil(ctx)
            return
        if self.serene:
            self.serene_turn(ctx, dt)
            return
        if not self._drink(ctx, dt):
            self.drinking = False
            self.unveiled_turn(ctx, dt)
        self._bleed(ctx)

    def serene_turn(self, ctx: AIContext, dt: float) -> None:
        self.roam(ctx, dt)

    def unveiled_turn(self, ctx: AIContext, dt: float) -> None:
        self.roam(ctx, dt)

    def on_unveil(self, ctx: AIContext) -> None:
        """What it does the moment it's unveiled (most: nothing more)."""

    def always(self, ctx: AIContext, dt: float) -> None:
        """Every turn, whatever its state (what it set going plays out)."""

    # --- Shared moves -------------------------------------------------------------------

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

    def shoot(self, ctx: AIContext, angle: float, shot: str):
        shell = config.PARADISE_SHOTS[shot]
        ctx.events.append(shell.sound)
        return patterns.shoot(self, self.x, self.y, angle, shell, ctx.projectiles)

    def touch(self, ctx: AIContext, damage: float, every: float, angle: float | None = None) -> None:
        """Hurt every body it's touching, each at most once every `every` s
        (bumping heroes who slip through bodies pass, Draft)."""
        hits = self.__dict__.setdefault("_touched", {})
        for a in ctx.actors:
            if a is self or not a.hittable or combat.drafting(a):
                continue
            if math.hypot(a.x - self.x, a.y - self.y) <= self.hit_radius + a.hit_radius \
                    and self.clock - hits.get(id(a), -99.0) >= every:
                hits[id(a)] = self.clock
                _numbered_hit(a, damage * self.damage_mult, self,
                              self.angle_to(a.x, a.y) if angle is None else angle, ctx)

    # --- Things thrown in an arc (coals, tears) ------------------------------------------

    def lob(self, x1: float, y1: float, flight: float, what: str) -> None:
        """Throw something in an arc to (x1, y1): it lands `flight` s later
        (`landed`); where it'll land shows meanwhile (render/paradise.py)."""
        self.lobs.append([self.x, self.y, x1, y1, 0.0, flight, what])

    def _fly_lobs(self, ctx: AIContext, dt: float) -> None:
        for b in self.lobs:
            b[4] += dt
            if b[4] >= b[5]:
                self.landed(ctx, b[2], b[3], b[6])
        self.lobs = [b for b in self.lobs if b[4] < b[5]]

    def landed(self, ctx: AIContext, x: float, y: float, what: str) -> None:
        """Something it threw came down at (x, y)."""

    # --- The fonts and the blood --------------------------------------------------------

    def _drink(self, ctx: AIContext, dt: float) -> bool:
        """Under FONT[0] of its max HP: off to the nearest font and drinking
        there (True while it's busy with that)."""
        low, reach, near, rate, until, patience = config.FONT
        self.font_wait = max(0.0, self.font_wait - dt)
        if self.font is None:
            if self.hp >= self.max_hp * low or self.font_wait > 0 or self.espec.speed <= 0 \
                    or not self.drinks:
                return False
            self.font = nearest_font(ctx.world, self.x, self.y, reach)
            self.font_time = 0.0
            if self.font is None:
                self.font_wait = 2.0
                return False
        if self.hp >= self.max_hp * until:
            self.font = None
            return False
        fx, fy = self.font
        if math.hypot(fx - self.x, fy - self.y) > near:
            self.drinking = False
            self.font_time += dt
            if self.font_time > patience:            # (can't get there: forget it a while)
                self.font, self.font_wait = None, patience
                return False
            self.go(ctx, fx, fy, dt, self.speed)
            return True
        self.drinking = True
        self.facing = math.atan2(fy - self.y, fx - self.x)
        if not wounded(self):
            self.hp = min(float(self.max_hp), self.hp + self.max_hp * rate * dt)
        return True

    def _bleed(self, ctx: AIContext) -> None:
        every, chance, hit_chance, _ = config.STAIN
        self.bled += self._moved
        if self.bled >= every / self.bleed:
            self.bled = 0.0
            if self.rng.random() < chance:
                stain(ctx.world, self.x, self.y + self.hit_radius * 0.5)
        while self.sprays > 0:
            self.sprays -= 1
            if self.rng.random() < hit_chance * min(1.0, self.bleed):
                a, r = self.rng.uniform(0, math.tau), self.rng.uniform(0.4, 1.6)
                stain(ctx.world, self.x + math.cos(a) * r, self.y + math.sin(a) * r)

    def on_death(self, ctx: AIContext) -> None:
        for b in self.lobs:                    # (what's in the air still comes down)
            self.landed(ctx, b[2], b[3], b[6])
        self.lobs = []
        if self.unveiled:
            ctx.effects.append(Effect("gore", self.x, self.y, size=self.hit_radius))
            pool(ctx.world, self.x, self.y + self.hit_radius * 0.3,
                 config.STAIN[3] + self.hit_radius * 0.5)
        else:
            ctx.effects.append(Effect("feathers", self.x, self.y, size=self.hit_radius))


# --- Angels -------------------------------------------------------------------------------


class Cherub(Angel):
    """Serene: keeps CHERUB[0] back and plinks runs of slow notes.
    Unveiled: chases; in reach it crouches (the windup) and lunges up to
    CHERUB[5] tiles, biting at the end; close by, now and then it roars a
    CHERUB[9]-degree cone that hurts and pushes you CHERUB[10] tiles."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.notes = 0              # notes of a run still to plink
        self.note_t = 0.0
        self.move = ""              # the windup's: "lunge" or "roar"
        self.aim = 0.0
        self.lunge = 0.0            # tiles of the lunge left
        self.roar_cd = self.rng.uniform(1.0, config.CHERUB[6])

    def serene_turn(self, ctx: AIContext, dt: float) -> None:
        keep, every, run, gap = config.CHERUB[:4]
        t = self.target
        if self.notes > 0:
            self.note_t -= dt
            if self.note_t <= 0 and t is not None:
                self.notes -= 1
                self.note_t = gap
                off = (self.notes - (run - 1) / 2) * 0.12
                self.shoot(ctx, self.angle_to(t.x, t.y) + off, "note")
        if t is None or not self.sees_target:
            self.roam(ctx, dt)
            return
        self.keep(ctx, t, keep * 0.8, keep * 1.25, dt)
        if self.cooldown <= 0 and self.notes == 0:
            self.notes, self.note_t, self.cooldown = run, 0.0, every

    def unveiled_turn(self, ctx: AIContext, dt: float) -> None:
        _, _, _, _, speed, longest, roar_every, roar_windup, roar_reach, cone, push = config.CHERUB
        self.roar_cd = max(0.0, self.roar_cd - dt)
        t = self.target
        if self.windup > 0:
            self.windup -= dt
            self.tell = self.windup
            if self.move == "roar" and t is not None:
                self.facing = self.angle_to(t.x, t.y)
            if self.windup <= 0:
                self.tell = 0.0
                if self.move == "roar":
                    self._roar(ctx, math.radians(cone) / 2, roar_reach, push)
                else:
                    self.lunge = longest
            return
        if self.lunge > 0:
            moved, blocked = _dash(self, ctx, self.aim, speed, dt)
            self.facing = self.aim
            self.lunge -= max(moved, speed * dt * 0.5)
            close = t is not None and self.dist_to(t) <= self.espec.attack_radius * 0.6 + t.hit_radius
            if close or blocked or self.lunge <= 0:
                self.lunge = 0.0
                self.bite(ctx)
            return
        if t is None or not self.sees_target:
            self.roam(ctx, dt)
            return
        d = self.dist_to(t)
        if self.roar_cd <= 0 and d <= roar_reach * 0.9:
            self.move, self.windup, self.roar_cd = "roar", roar_windup, roar_every
            self.facing = self.angle_to(t.x, t.y)
            return
        if self.cooldown <= 0 and d <= longest + t.hit_radius:
            self.move, self.windup = "lunge", self.espec.windup
            self.aim = self.facing = self.angle_to(t.x, t.y)
            return
        self.go(ctx, t.x, t.y, dt, self.speed)

    def _roar(self, ctx: AIContext, half: float, reach: float, push: float) -> None:
        ctx.effects.append(Effect("scream", self.x, self.y, self.facing, size=reach))
        ctx.events.append("hex")
        for a in ctx.actors:
            if a is self or not a.hittable:
                continue
            d = math.hypot(a.x - self.x, a.y - self.y)
            if d > reach + a.hit_radius:
                continue
            ang = math.atan2(a.y - self.y, a.x - self.x)
            if d > a.hit_radius and abs(_wrap(ang - self.facing)) > half:
                continue
            _numbered_hit(a, self.espec.damage * 0.7 * self.damage_mult, self, ang, ctx)
            combat.push(a, ctx.world, math.cos(ang) * push, math.sin(ang) * push)
        self.cooldown = max(self.cooldown, 0.6)


class Seraph(Angel):
    """Elite. Serene: keeps SERAPH[0] back, a slow ring of SERAPH[2] shots
    of light every SERAPH[1] s. Unveiled: keeps SERAPH[3] back; every
    cooldown its wings flare (the windup) and it spins a spiral for SERAPH[4]
    s -- a burst of SERAPH[6] shots every SERAPH[5] s, turning SERAPH[7]
    each time, blood and fire in turn."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.cooldown = self.rng.uniform(1.0, config.SERAPH[1])
        self.spin = 0.0             # s of spiral left
        self.burst = 0.0
        self.turn = 0.0
        self.bursts = 0

    def serene_turn(self, ctx: AIContext, dt: float) -> None:
        keep, every, n = config.SERAPH[:3]
        t = self.target
        if t is None or not self.sees_target:
            self.roam(ctx, dt)
            return
        self.keep(ctx, t, keep * 0.8, keep * 1.25, dt)
        if self.cooldown <= 0:
            self.cooldown = every
            shell = config.PARADISE_SHOTS["light"]
            patterns.radial(self, self.x, self.y, n, shell, ctx.projectiles,
                            turn=self.rng.uniform(0, math.tau / n))
            ctx.events.append(shell.sound)

    def unveiled_turn(self, ctx: AIContext, dt: float) -> None:
        _, _, _, keep, length, gap, n, turn = config.SERAPH
        t = self.target
        if self.windup > 0:
            self.windup -= dt
            self.tell = self.windup
            if self.windup <= 0:
                self.tell = 0.0
                self.spin, self.burst, self.bursts = length, 0.0, 0
                self.turn = self.rng.uniform(0, math.tau)
            return
        if self.spin > 0:
            self.spin -= dt
            self.burst -= dt
            if self.burst <= 0:
                self.burst += gap
                self.bursts += 1
                self.turn += turn
                shell = config.PARADISE_SHOTS["blood" if self.bursts % 2 else "fire"]
                patterns.radial(self, self.x, self.y, n, shell, ctx.projectiles, turn=self.turn)
                if self.bursts % 3 == 1:
                    ctx.events.append(shell.sound)
            if self.spin <= 0:
                self.cooldown = self.espec.cooldown
            return
        if t is None or not self.sees_target:
            self.roam(ctx, dt)
            return
        self.keep(ctx, t, keep * 0.8, keep * 1.3, dt)
        if self.cooldown <= 0:
            self.windup = self.espec.windup


class Ophan(Angel):
    """Serene: rolls gently at you, bumping (OPHAN[0] every OPHAN[1] s).
    Unveiled: rests OPHAN[4] s, lines up (the windup; its line shows), then
    races straight at OPHAN[2] tiles/s for OPHAN[3] s, bouncing off walls,
    hurting whatever it runs through (each at most every OPHAN[5] s) and
    leaving a slick of blood that slows (to x OPHAN[6], a patch every
    OPHAN[8] s, lasting OPHAN[7] s)."""

    bleed = 1.5

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.rolling = "rest"       # unveiled: rest -> aim -> race
        self.aim = 0.0
        self.slick = 0.0

    def sprite_now(self) -> str:
        name = super().sprite_now()
        if name.endswith("_unveiled") and int(self.walked * 1.5) % 2:
            return name + "2"                       # (its wheels turning)
        return name

    def serene_turn(self, ctx: AIContext, dt: float) -> None:
        bump, every = config.OPHAN[:2]
        t = self.target
        if t is None or not self.sees_target:
            self.roam(ctx, dt)
        else:
            self.go(ctx, t.x, t.y, dt, self.speed)
        self.touch(ctx, bump, every)

    def unveiled_turn(self, ctx: AIContext, dt: float) -> None:
        _, _, speed, race, rest, every, slow, life, patch = config.OPHAN
        t = self.target
        if self.rolling == "rest":
            self.timer -= dt
            if t is not None and self.sees_target:
                self.facing = self.angle_to(t.x, t.y)
                if self.timer <= 0:
                    self.rolling, self.windup = "aim", self.espec.windup
            else:
                self.roam(ctx, dt)
            return
        if self.rolling == "aim":
            self.windup -= dt
            self.tell = self.windup
            if t is not None and self.windup > 0.15:
                self.aim = self.facing = self.angle_to(t.x, t.y)
            if self.windup <= 0:
                self.tell = 0.0
                self.rolling, self.timer, self.slick = "race", race, 0.0
            return
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
        self.touch(ctx, self.espec.damage, every, self.aim)
        self.slick -= dt
        if self.slick <= 0 and ctx.zones is not None:
            self.slick = patch
            ctx.zones.append(Zone("blood_slick", self.x, self.y, 0.9, life, 0.1, 0.0, self,
                                  slow=slow))
        if self.timer <= 0:
            self.rolling, self.timer = "rest", rest


class Watcher(Angel):
    """Never moves. Serene: an orb of light at you every WATCHER[0] s.
    Unveiled: every cooldown it fixes its gaze (the windup: its line
    follows you until WATCHER[4] s before), then the beam burns WATCHER[3]
    s, sweeping WATCHER[2] degrees the way you were going, out to
    WATCHER[1] tiles or the first thing that blocks shots; it hurts each
    body once a sweep."""

    drinks = False

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.cooldown = self.rng.uniform(1.0, config.WATCHER[0])
        self.aim = self.facing
        self.way = 1.0
        self.burn = 0.0             # s of beam left
        self.beam: tuple[float, float, float, float] | None = None   # (x0, y0, x1, y1)
        self.aim_end: tuple[float, float] | None = None   # where its aim line stops (drawing)
        self.seared: set[int] = set()

    def go(self, ctx, gx, gy, dt, speed) -> bool:       # (it never moves)
        self._moved = 0.0
        return False

    def serene_turn(self, ctx: AIContext, dt: float) -> None:
        t = self.target
        if t is None or not self.sees_target:
            return
        self.facing = self.angle_to(t.x, t.y)
        if self.cooldown <= 0:
            self.cooldown = config.WATCHER[0]
            self.shoot(ctx, self.facing, "orb")

    def ray(self, world, a: float) -> tuple[float, float]:
        """Where the gaze along `a` stops."""
        reach = config.WATCHER[1]
        x1, y1 = self.x + math.cos(a) * reach, self.y + math.sin(a) * reach
        hit = first_hit(world.tile_at, self.x, self.y, x1, y1)
        return (hit.x, hit.y) if hit is not None else (x1, y1)

    def unveiled_turn(self, ctx: AIContext, dt: float) -> None:
        _, reach, sweep, burn, settle, half = config.WATCHER
        t = self.target
        if self.burn > 0:
            self.burn -= dt
            self.aim += self.way * math.radians(sweep) / burn * dt
            self.facing = self.aim
            x1, y1 = self.ray(ctx.world, self.aim)
            self.beam = (self.x, self.y, x1, y1)
            for a in ctx.actors:
                if a is self or not a.hittable or id(a) in self.seared:
                    continue
                if patterns.point_segment_distance(a.x, a.y, self.x, self.y, x1, y1) \
                        <= half + a.hit_radius:
                    self.seared.add(id(a))
                    _numbered_hit(a, self.espec.damage * self.damage_mult, self, self.aim, ctx)
            if self.burn <= 0:
                self.beam = None
                self.cooldown = self.espec.cooldown
            return
        if self.windup > 0:
            self.windup -= dt
            self.tell = self.windup
            if t is not None and self.windup > settle:
                a = self.angle_to(t.x, t.y)
                side = math.sin(math.atan2(getattr(t, "vy", 0.0), getattr(t, "vx", 0.0)) - a)
                if abs(side) > 0.1:
                    self.way = 1.0 if side > 0 else -1.0
                self.aim = a - self.way * math.radians(sweep) * 0.3   # (it starts a little behind)
            self.facing = self.aim
            self.aim_end = self.ray(ctx.world, self.aim)
            if self.windup <= 0:
                self.tell = 0.0
                self.burn, self.seared = burn, set()
                ctx.events.append("hex")
            return
        if t is None or not self.sees_target:
            return
        self.facing = self.angle_to(t.x, t.y)
        if self.cooldown <= 0 and self.dist_to(t) <= reach:
            self.windup = self.espec.windup
            if self.rng.random() < 0.5:
                self.way = -self.way


# --- Chasers -------------------------------------------------------------------------------


class Lamb(Angel):
    """Serene: ambles at you and butts (LAMB[4], a slow windup). Unveiled:
    within attack_radius it scrapes (the windup; the charge line shows),
    then charges LAMB[1] tiles at LAMB[0] tiles/s, goring whoever it runs
    into once a charge; what stops it dazes it LAMB[2] s; after a charge it
    takes LAMB[3] s to get its footing back."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.charging = "walk"      # unveiled: walk -> scrape -> charge -> (dazed) -> walk
        self.ran = 0.0
        self.gored: set[int] = set()

    def serene_turn(self, ctx: AIContext, dt: float) -> None:
        butt = config.LAMB[4]
        t = self.target
        if self.windup > 0:
            self.windup -= dt
            self.tell = self.windup
            if self.windup <= 0:
                self.tell = 0.0
                cx = self.x + math.cos(self.facing) * 0.6
                cy = self.y + math.sin(self.facing) * 0.6
                combat.blast(cx, cy, 0.9, butt * self.damage_mult, self, ctx.actors,
                             effects=ctx.effects)
                self.cooldown = self.espec.cooldown * 2.0
            return
        if t is None or not self.sees_target:
            self.roam(ctx, dt)
            return
        if self.dist_to(t) <= 1.2 + t.hit_radius and self.cooldown <= 0:
            self.facing = self.angle_to(t.x, t.y)
            self.windup = self.espec.windup * 1.5
            return
        self.go(ctx, t.x, t.y, dt, self.speed)

    def unveiled_turn(self, ctx: AIContext, dt: float) -> None:
        speed, length, daze, recover = config.LAMB[:4]
        t = self.target
        if self.charging in ("scrape", "dazed", "recover"):
            self.timer -= dt
            if self.charging == "scrape":
                self.tell = self.timer
            if self.timer <= 0:
                self.tell = 0.0
                if self.charging == "scrape":
                    self.charging, self.ran, self.gored = "charge", 0.0, set()
                else:
                    self.charging = "walk"
                    self.cooldown = self.espec.cooldown
            return
        if self.charging == "charge":
            moved, blocked = _dash(self, ctx, self.facing, speed, dt)
            self.ran += moved
            for a in ctx.actors:
                if a is self or not a.hittable or id(a) in self.gored:
                    continue
                if math.hypot(a.x - self.x, a.y - self.y) <= self.hit_radius + a.hit_radius + 0.2:
                    self.gored.add(id(a))
                    _numbered_hit(a, self.espec.damage * self.damage_mult, self, self.facing, ctx)
                    combat.push(a, ctx.world, math.cos(self.facing) * 1.2,
                                math.sin(self.facing) * 1.2)
            if blocked:
                ctx.events.append(combat.BREAK)
                ctx.effects.append(Effect("debris", self.x + math.cos(self.facing),
                                          self.y + math.sin(self.facing)))
                self.charging, self.timer = "dazed", daze
            elif self.ran >= length:
                self.charging, self.timer = "recover", recover
            return
        if t is None or not self.sees_target:
            self.roam(ctx, dt)
            return
        if self.dist_to(t) <= self.espec.attack_radius and self.cooldown <= 0:
            self.facing = self.angle_to(t.x, t.y)
            self.charging, self.timer = "scrape", self.espec.windup
            return
        self.go(ctx, t.x, t.y, dt, self.speed)


class _Flier(Angel):
    """Flies over everything. Serene, a lazy chaser: at you slowly, a weak
    sting (`serene_hit`) at long intervals."""

    flies = True
    serene_hit = 2

    def chase(self, ctx: AIContext, dt: float, damage: float, cooldown: float) -> None:
        t = self.target
        if self.windup > 0:
            self.windup -= dt
            self.tell = self.windup
            if self.windup <= 0:
                self.tell = 0.0
                cx = self.x + math.cos(self.facing) * 0.6
                cy = self.y + math.sin(self.facing) * 0.6
                combat.blast(cx, cy, self.espec.attack_radius * 0.7, damage * self.damage_mult,
                             self, ctx.actors, effects=ctx.effects)
                ctx.events.append(combat.HIT)
                self.cooldown = cooldown
            return
        if t is None or not self.alert:
            self.roam(ctx, dt)
            return
        goal = (t.x, t.y) if self.sees_target else self.last_known
        if goal is None:
            return
        if self.sees_target and self.dist_to(t) <= self.espec.attack_radius + t.hit_radius \
                and self.cooldown <= 0:
            self.facing = self.angle_to(t.x, t.y)
            self.windup = self.espec.windup
            return
        self.go(ctx, *goal, dt, self.speed)

    def serene_turn(self, ctx: AIContext, dt: float) -> None:
        self.chase(ctx, dt, self.serene_hit, self.espec.cooldown * 2.5)


class Dove(_Flier):
    """Serene: a lazy chaser, pecking (DOVES[4]). Unveiled: circles its
    target DOVES[0] tiles out and dives through it at DOVES[1] tiles/s when
    it's its turn -- one dove per target at a time (like the hounds'
    turns), each waiting DOVES[3] s after its own dive -- pecking as it
    passes, then climbs away DOVES[2] s."""

    _turns: dict = {}               # id(target) -> the dove diving at it

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.slot = self.rng.uniform(0, math.tau)
        self.wait = self.rng.uniform(*config.DOVES[3])
        self.dive = 0.0             # tiles of the dive left
        self.climb = 0.0
        self.aim = 0.0
        self.pecked = False

    @property
    def bleed(self) -> float:
        return config.DOVES[5]

    @property
    def serene_hit(self) -> float:
        return config.DOVES[4]

    def _release(self) -> None:
        for k, d in list(Dove._turns.items()):
            if d is self:
                del Dove._turns[k]

    def unveiled_turn(self, ctx: AIContext, dt: float) -> None:
        orbit, speed, climb, wait = config.DOVES[:4]
        t = self.target
        if self.dive > 0:
            moved, _ = self.go_line(ctx, speed, dt)
            self.dive -= moved
            if not self.pecked and t is not None \
                    and self.dist_to(t) <= self.espec.attack_radius + t.hit_radius:
                self.pecked = True
                _numbered_hit(t, self.espec.damage * self.damage_mult, self, self.aim, ctx)
            if self.dive <= 0:
                self.climb = climb
                self.wait = self.rng.uniform(*wait)
                self._release()
            return
        if self.climb > 0:
            self.climb -= dt
            self.go_line(ctx, self.speed, dt)
            return
        if t is None or not self.sees_target:
            self._release()
            self.roam(ctx, dt)
            return
        self.wait -= dt
        self.slot += dt * 0.9
        gx, gy = t.x + math.cos(self.slot) * orbit, t.y + math.sin(self.slot) * orbit * 0.7
        self.go(ctx, gx, gy, dt, self.speed)
        turn = Dove._turns.get(id(t))
        free = (turn is None or not turn.alive or turn.dive <= 0
                or not any(a is turn for a in ctx.actors))      # (asleep: not about)
        if self.wait <= 0 and free:
            Dove._turns[id(t)] = self
            self.aim = self.facing = self.angle_to(t.x, t.y)
            self.dive = self.dist_to(t) + 3.0
            self.pecked = False

    def go_line(self, ctx: AIContext, speed: float, dt: float) -> tuple[float, bool]:
        """Straight along its aim, over everything."""
        step = speed * dt
        self.x += math.cos(self.aim) * step
        self.y += math.sin(self.aim) * step
        self.facing = self.aim
        self._moved = step
        self.walked += step
        return step, False

    def on_death(self, ctx: AIContext) -> None:
        self._release()
        super().on_death(ctx)


class Locust(_Flier):
    """A swarm. Serene: drifts at you, stinging now and then (LOCUSTS[1]).
    Unveiled: fast, weaving (LOCUSTS[0]), stinging."""

    @property
    def wobble(self) -> float:
        return config.LOCUSTS[0] if self.unveiled else config.LOCUSTS[0] * 0.5

    @property
    def bleed(self) -> float:
        return config.LOCUSTS[2]

    @property
    def serene_hit(self) -> float:
        return config.LOCUSTS[1]

    def unveiled_turn(self, ctx: AIContext, dt: float) -> None:
        self.chase(ctx, dt, self.espec.damage, self.espec.cooldown)


class Halo(Angel):
    """Flies. Serene: drifts at you; touching, it hurts a little (HALO[2]
    every HALO[3] s). Unveiled: a buzzsaw -- flies at full speed, turning
    toward its target at HALO[0] rad/s at most (so it overshoots and comes
    round again), sawing whatever it touches every HALO[1] s."""

    flies = True

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.heading = self.facing

    @property
    def bleed(self) -> float:
        return config.HALO[4]

    def sprite_now(self) -> str:
        name = super().sprite_now()
        if name.endswith("_unveiled") and int(self.clock * 14) % 2:
            return name + "2"                       # (spinning)
        return name

    def serene_turn(self, ctx: AIContext, dt: float) -> None:
        t = self.target
        if t is None or not self.alert:
            self.roam(ctx, dt)
        else:
            goal = (t.x, t.y) if self.sees_target else self.last_known
            if goal is not None:
                self.go(ctx, *goal, dt, self.speed)
        self.heading = self.facing
        self.touch(ctx, config.HALO[2], config.HALO[3])

    def unveiled_turn(self, ctx: AIContext, dt: float) -> None:
        turn, every = config.HALO[:2]
        t = self.target
        goal = None
        if t is not None and self.alert:
            goal = (t.x, t.y) if self.sees_target else self.last_known
        if goal is None:
            goal = self.wander_goal(dt)
        want = math.atan2(goal[1] - self.y, goal[0] - self.x)
        diff = _wrap(want - self.heading)
        self.heading += max(-turn * dt, min(turn * dt, diff))
        step = self.speed * dt
        self.x += math.cos(self.heading) * step
        self.y += math.sin(self.heading) * step
        self.facing = self.heading
        self._moved = step
        self.walked += step
        self.touch(ctx, self.espec.damage, every)


# --- Heralds (M29.3) -----------------------------------------------------------------------


class Trumpeter(Angel):
    """Elite. Keeps TRUMPET[0] back. Serene: a long note every TRUMPET[1] s
    that gently pushes heroes within TRUMPET[2] tiles TRUMPET[3] back.
    Unveiled: every cooldown it raises the trumpet (the windup) and its
    blast calls a plague: a TRUMPET[4]-tile circle round you is marked for
    TRUMPET[5] s, then TRUMPET[6] strikes of fire and blood fall in it over
    TRUMPET[7] s, each hurting what's within TRUMPET[8] -- fire leaves a
    burning patch, blood a stain."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.cooldown = self.rng.uniform(1.0, config.TRUMPET[1])
        self.plague: list | None = None      # [x, y, s of marking left, strikes left, s to the next]

    def _note(self, ctx: AIContext) -> None:
        _, _, reach, push = config.TRUMPET[:4]
        ctx.effects.append(Effect("pulse", self.x, self.y, size=reach))
        ctx.events.append("orb")
        for a in ctx.actors:
            if getattr(a, "faction", "") != "player" or not a.hittable:
                continue
            d = math.hypot(a.x - self.x, a.y - self.y)
            if 0 < d <= reach + a.hit_radius:
                combat.push(a, ctx.world, (a.x - self.x) / d * push, (a.y - self.y) / d * push)

    def serene_turn(self, ctx: AIContext, dt: float) -> None:
        keep, every = config.TRUMPET[:2]
        t = self.target
        if t is None or not self.sees_target:
            self.roam(ctx, dt)
            return
        self.keep(ctx, t, keep * 0.8, keep * 1.25, dt)
        if self.cooldown <= 0:
            self.cooldown = every
            self._note(ctx)

    def unveiled_turn(self, ctx: AIContext, dt: float) -> None:
        keep, _, _, _, _, mark, strikes = config.TRUMPET[:7]
        t = self.target
        if self.windup > 0:
            self.windup -= dt
            self.tell = self.windup
            if self.windup <= 0:
                self.tell = 0.0
                self._note(ctx)
                if t is not None and self.plague is None:
                    self.plague = [t.x, t.y, mark, strikes, 0.0]
                self.cooldown = self.espec.cooldown
            return
        if t is None or not self.sees_target:
            self.roam(ctx, dt)
            return
        self.keep(ctx, t, keep * 0.8, keep * 1.25, dt)
        if self.cooldown <= 0 and self.plague is None:
            self.windup = self.espec.windup

    def always(self, ctx: AIContext, dt: float) -> None:
        """The plague it called falls, whatever it's doing now."""
        p = self.plague
        if p is None:
            return
        radius, _, strikes, over, width = config.TRUMPET[4:]
        if p[2] > 0:
            p[2] -= dt
            return
        p[4] -= dt
        while p[4] <= 0 and p[3] > 0:
            p[4] += over / strikes
            p[3] -= 1
            a, r = self.rng.uniform(0, math.tau), radius * math.sqrt(self.rng.random())
            self._strike(ctx, p[0] + math.cos(a) * r, p[1] + math.sin(a) * r, width,
                         fire=p[3] % 2 == 0)
        if p[3] <= 0:
            self.plague = None

    def _strike(self, ctx: AIContext, x: float, y: float, width: float, fire: bool) -> None:
        combat.blast(x, y, width, self.espec.damage * self.damage_mult, self, ctx.actors,
                     effects=ctx.effects, ground=True)
        ctx.effects.append(Effect("explosion" if fire else "gore", x, y, size=width))
        if fire and ctx.zones is not None:
            damage, tick = config.FIRE_PATCH
            ctx.zones.append(Zone("trail", x, y, width * 0.9, 3.0, tick, damage, self,
                                  (config.STATUSES["burn"].tag,), "burn"))
        elif not fire:
            pool(ctx.world, x, y, width * 0.8)
        ctx.events.append(combat.BREAK)


class CenserBearer(Angel):
    """Serene: swings its censer -- harmless puffs of incense every CENSER[1]
    s -- and drifts after you. Unveiled: keeps CENSER[0] back and every
    cooldown hurls CENSER[2] burning coals (the windup) that land CENSER[3]
    s later, CENSER[4] apart round you (where shows first): they hurt and
    leave fire (CENSER[5] s)."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.puff = self.rng.uniform(0.0, config.CENSER[1])

    def serene_turn(self, ctx: AIContext, dt: float) -> None:
        self.puff -= dt
        if self.puff <= 0 and ctx.zones is not None:
            self.puff = config.CENSER[1]
            ctx.zones.append(Zone("incense", self.x, self.y - 0.4, 1.1, 2.5, 99.0, 0.0, self))
        t = self.target
        if t is None or not self.sees_target:
            self.roam(ctx, dt)
        else:
            self.go(ctx, t.x, t.y, dt, self.speed)

    def unveiled_turn(self, ctx: AIContext, dt: float) -> None:
        keep, _, n, flight, spread, _ = config.CENSER
        t = self.target
        if self.windup > 0:
            self.windup -= dt
            self.tell = self.windup
            if self.windup <= 0:
                self.tell = 0.0
                if t is not None:
                    a0 = self.rng.uniform(0, math.tau)
                    for k in range(n):
                        a = a0 + k * math.tau / n
                        r = spread * (0.5 if n > 1 else 0.0)
                        self.lob(t.x + math.cos(a) * r, t.y + math.sin(a) * r, flight, "coal")
                    ctx.events.append("bow")
                self.cooldown = self.espec.cooldown
            return
        if t is None or not self.sees_target:
            self.roam(ctx, dt)
            return
        self.keep(ctx, t, keep * 0.8, keep * 1.25, dt)
        if self.cooldown <= 0:
            self.windup = self.espec.windup

    def landed(self, ctx: AIContext, x: float, y: float, what: str) -> None:
        combat.blast(x, y, 0.9, self.espec.damage * self.damage_mult, self, ctx.actors,
                     effects=ctx.effects, ground=True)
        ctx.effects.append(Effect("explosion", x, y))
        if ctx.zones is not None:
            damage, tick = config.FIRE_PATCH
            ctx.zones.append(Zone("trail", x, y, 1.0, config.CENSER[5], tick, damage, self,
                                  (config.STATUSES["burn"].tag,), "burn"))


class BowlBearer(Angel):
    """Serene: carries its gold bowl after you (harmless). Unveiled: keeps
    BOWL[0] back; every cooldown it marks where you stand (the windup: a
    ring on the ground) and pours: a pool of blood there, BOWL[1] wide and
    spreading x(1 + BOWL[2]) over its BOWL[3] s, that slows (x BOWL[4]) and
    bleeds whoever stands in it (its damage every BOWL[5] s). The ground
    under it stains."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.mark: tuple[float, float] | None = None

    def serene_turn(self, ctx: AIContext, dt: float) -> None:
        t = self.target
        if t is None or not self.sees_target:
            self.roam(ctx, dt)
        else:
            self.go(ctx, t.x, t.y, dt, self.speed)

    def unveiled_turn(self, ctx: AIContext, dt: float) -> None:
        keep, wide, grow, life, slow, every = config.BOWL
        t = self.target
        if self.windup > 0:
            self.windup -= dt
            self.tell = self.windup
            if self.windup <= 0:
                self.tell = 0.0
                x, y = self.mark
                self.mark = None
                if ctx.zones is not None:
                    ctx.zones.append(Zone("blood_pool", x, y, wide, life, every,
                                          self.espec.damage * self.damage_mult, self, slow=slow,
                                          grow=grow))
                pool(ctx.world, x, y, wide + 0.5)
                ctx.events.append("fizzle")
                self.cooldown = self.espec.cooldown
            return
        if t is None or not self.sees_target:
            self.roam(ctx, dt)
            return
        self.keep(ctx, t, keep * 0.8, keep * 1.3, dt)
        if self.cooldown <= 0:
            self.windup, self.mark = self.espec.windup, (t.x, t.y)


class Chorister(Angel):
    """Lives at a choir ring (CHORISTER[2] to a ring: systems/spawner's
    residents). Serene: lingers there singing; its hymn heals every angel
    within CHORISTER[0] (not itself) CHORISTER[1] x max HP a second.
    Unveiled: keeps back and every cooldown shrieks (the windup) --
    CHORISTER[3] rings of CHORISTER[4] shots, CHORISTER[5] s apart, each
    turned half a gap from the last."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.rings = 0
        self.ring_t = 0.0
        self.turn = self.rng.uniform(0, math.tau)
        self.singing = False

    def serene_turn(self, ctx: AIContext, dt: float) -> None:
        reach, share = config.CHORISTER[:2]
        self.go(ctx, *self.wander_goal(dt), dt, self.speed * 0.4)
        self.singing = False
        for a in ctx.actors:
            if a is self or not isinstance(a, Angel) or not a.alive or a.hp >= a.max_hp \
                    or wounded(a) or math.hypot(a.x - self.x, a.y - self.y) > reach:
                continue
            a.hp = min(float(a.max_hp), a.hp + a.max_hp * share * dt)
            self.singing = True

    def unveiled_turn(self, ctx: AIContext, dt: float) -> None:
        _, _, _, rings, n, gap = config.CHORISTER
        t = self.target
        if self.rings > 0:
            self.ring_t -= dt
            if self.ring_t <= 0:
                self.ring_t = gap
                self.rings -= 1
                self.turn += math.pi / n
                shell = config.PARADISE_SHOTS["shriek"]
                patterns.radial(self, self.x, self.y, n, shell, ctx.projectiles, turn=self.turn)
                ctx.events.append(shell.sound)
                if self.rings == 0:
                    self.cooldown = self.espec.cooldown
            return
        if self.windup > 0:
            self.windup -= dt
            self.tell = self.windup
            if self.windup <= 0:
                self.tell = 0.0
                self.rings, self.ring_t = rings, 0.0
            return
        if t is None or not self.sees_target:
            self.roam(ctx, dt)
            return
        self.keep(ctx, t, 4.0, 7.0, dt)
        if self.cooldown <= 0:
            self.windup = self.espec.windup


# --- Saints and beasts (M29.3) -------------------------------------------------------------


class WeepingSaint(Angel):
    """Serene: kneels where it is, praying (harmless). Unveiled: bleeds
    from its eyes; keeps SAINT[0] back and every cooldown lobs SAINT[1]
    tears (the windup) that land SAINT[2] s later, SAINT[3] apart round you
    (where shows first): each hurts and leaves a pool of blood SAINT[4]
    wide for SAINT[5] s that slows (x SAINT[6])."""

    def serene_turn(self, ctx: AIContext, dt: float) -> None:
        t = self.target
        if t is not None:
            self.facing = self.angle_to(t.x, t.y)

    def unveiled_turn(self, ctx: AIContext, dt: float) -> None:
        keep, n, flight, spread = config.SAINT[:4]
        t = self.target
        if self.windup > 0:
            self.windup -= dt
            self.tell = self.windup
            if self.windup <= 0:
                self.tell = 0.0
                if t is not None:
                    a0 = self.rng.uniform(0, math.tau)
                    for k in range(n):
                        a = a0 + k * math.tau / n
                        r = spread * (0 if k == 0 else 1)
                        self.lob(t.x + math.cos(a) * r, t.y + math.sin(a) * r, flight, "tear")
                    ctx.events.append("fizzle")
                self.cooldown = self.espec.cooldown
            return
        if t is None or not self.sees_target:
            self.roam(ctx, dt)
            return
        self.keep(ctx, t, keep * 0.8, keep * 1.25, dt)
        if self.cooldown <= 0:
            self.windup = self.espec.windup

    def landed(self, ctx: AIContext, x: float, y: float, what: str) -> None:
        wide, life, slow = config.SAINT[4:]
        combat.blast(x, y, 0.8, self.espec.damage * self.damage_mult, self, ctx.actors,
                     effects=ctx.effects, ground=True)
        ctx.effects.append(Effect("gore", x, y, size=0.6))
        if ctx.zones is not None:
            ctx.zones.append(Zone("blood_pool", x, y, wide, life, 0.5, 0.0, self, slow=slow))
        stain(ctx.world, x, y)


class Martyr(Angel):
    """Starts pierced with MARTYR[0] arrows; every hit from a hero sticks
    one more in (up to MARTYR[1]). Serene: kneels (harmless). Unveiled:
    keeps MARTYR[4] back and every cooldown, with arrows in it, rips them
    out (the windup) and throws up to MARTYR[2] back in a MARTYR[3]-degree
    fan. Shooting it feeds it."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.arrows = config.MARTYR[0]

    def take_damage(self, amount, source, from_angle):
        dealt = super().take_damage(amount, source, from_angle)
        if dealt > 0 and getattr(source, "faction", "") == "player":
            self.arrows = min(config.MARTYR[1], self.arrows + 1)
        return dealt

    def serene_turn(self, ctx: AIContext, dt: float) -> None:
        t = self.target
        if t is not None:
            self.facing = self.angle_to(t.x, t.y)

    def unveiled_turn(self, ctx: AIContext, dt: float) -> None:
        _, _, per, fan, keep = config.MARTYR
        t = self.target
        if self.windup > 0:
            self.windup -= dt
            self.tell = self.windup
            if self.windup <= 0:
                self.tell = 0.0
                n = min(per, self.arrows)
                if t is not None and n > 0:
                    self.arrows -= n
                    shell = config.PARADISE_SHOTS["arrow"]
                    patterns.fan(self, self.x, self.y, self.angle_to(t.x, t.y), n,
                                 fan * (n - 1) / max(1, per - 1), shell, ctx.projectiles)
                    ctx.events.append(shell.sound)
                self.cooldown = self.espec.cooldown
            return
        if t is None or not self.sees_target:
            self.roam(ctx, dt)
            return
        self.keep(ctx, t, keep * 0.8, keep * 1.25, dt)
        if self.cooldown <= 0 and self.arrows > 0:
            self.windup = self.espec.windup


class Behemoth(Angel):
    """Elite. Serene: a huge white ox, grazing round where it lives
    (harmless). Unveiled: its hide splits on bone plates (hits from within
    BEHEMOTH[6] degrees of its front do x BEHEMOTH[5]); within attack_radius
    it scrapes (the windup; the line shows) and charges BEHEMOTH[1] tiles at
    BEHEMOTH[0], trampling columns, trees and anything else that breaks (like
    the bull), goring and shoving (BEHEMOTH[7]) whoever it runs into once a
    charge; BEHEMOTH[2] charges in a row (BEHEMOTH[3] s turning between),
    then a rest. What doesn't break dazes it (BEHEMOTH[4] s)."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.charging = "walk"      # unveiled: walk -> scrape -> charge -> turn -> scrape ... | dazed
        self.ran = 0.0
        self.passes = 0
        self.gored: set[int] = set()

    def take_damage(self, amount, source, from_angle):
        if self.unveiled and from_angle is not None:
            came_from = from_angle + math.pi
            if abs(_wrap(came_from - self.facing)) < math.radians(config.BEHEMOTH[6]):
                amount *= config.BEHEMOTH[5]
        return super().take_damage(amount, source, from_angle)

    def serene_turn(self, ctx: AIContext, dt: float) -> None:
        self.go(ctx, *self.wander_goal(dt), dt, self.speed * 0.4)    # (grazing)

    def unveiled_turn(self, ctx: AIContext, dt: float) -> None:
        speed, length, passes, turn, daze, _, _, shove = config.BEHEMOTH
        t = self.target
        if self.charging in ("scrape", "turn", "dazed"):
            self.timer -= dt
            if self.charging == "scrape":
                self.tell = self.timer
            if self.charging == "turn" and t is not None:
                self.facing = self.angle_to(t.x, t.y)
            if self.timer <= 0:
                self.tell = 0.0
                if self.charging == "scrape":
                    self.charging, self.ran, self.gored = "charge", 0.0, set()
                elif self.charging == "turn":
                    self.charging, self.timer = "scrape", self.espec.windup * 0.6
                else:
                    self.charging, self.cooldown = "walk", self.espec.cooldown
            return
        if self.charging == "charge":
            moved, blocked = _dash(self, ctx, self.facing, speed, dt)
            self.ran += moved
            for a in ctx.actors:
                if a is self or not a.hittable or id(a) in self.gored:
                    continue
                if math.hypot(a.x - self.x, a.y - self.y) <= self.hit_radius + a.hit_radius + 0.2:
                    self.gored.add(id(a))
                    _numbered_hit(a, self.espec.damage * self.damage_mult, self, self.facing, ctx)
                    combat.push(a, ctx.world, math.cos(self.facing) * shove,
                                math.sin(self.facing) * shove)
            if blocked and not Bull._trample(self, ctx):
                ctx.events.append(combat.BREAK)
                ctx.effects.append(Effect("debris", self.x + math.cos(self.facing),
                                          self.y + math.sin(self.facing)))
                self.charging, self.timer = "dazed", daze
            elif self.ran >= length:
                self.passes += 1
                if self.passes >= passes:
                    self.charging, self.cooldown = "walk", self.espec.cooldown
                else:
                    self.charging, self.timer = "turn", turn
            return
        if t is None or not self.sees_target:
            self.roam(ctx, dt)
            return
        if self.dist_to(t) <= self.espec.attack_radius and self.cooldown <= 0:
            self.facing = self.angle_to(t.x, t.y)
            self.charging, self.timer, self.passes = "scrape", self.espec.windup, 0
            return
        self.go(ctx, t.x, t.y, dt, self.speed)


def rivers(world) -> list[list[tuple[float, float]]]:
    """The world's rivers of blood, as polylines (Paradise's plan; a test
    map may set `world.rivers`)."""
    lines = getattr(world, "rivers", None)
    if lines is not None:
        return lines
    lines = []
    layout = getattr(world, "layout", None)
    for z in getattr(layout, "zones", ()):
        if z.key == "paradise":
            from ..world.paradise import plan_of
            lines.append(plan_of(layout, z).river)
    try:
        world.rivers = lines
    except AttributeError:
        pass
    return lines


class _Line:
    """A polyline walked by distance along it."""

    def __init__(self, pts) -> None:
        self.pts = list(pts)
        self.at = [0.0]
        for (ax, ay), (bx, by) in zip(self.pts, self.pts[1:]):
            self.at.append(self.at[-1] + math.hypot(bx - ax, by - ay))
        self.length = self.at[-1]

    def point(self, s: float) -> tuple[float, float]:
        s = max(0.0, min(self.length, s))
        for k in range(1, len(self.pts)):
            if s <= self.at[k] or k == len(self.pts) - 1:
                seg = self.at[k] - self.at[k - 1] or 1e-9
                f = (s - self.at[k - 1]) / seg
                (ax, ay), (bx, by) = self.pts[k - 1], self.pts[k]
                return ax + (bx - ax) * f, ay + (by - ay) * f
        return self.pts[-1]

    def project(self, x: float, y: float) -> tuple[float, float]:
        """(distance along it of the point nearest (x, y), how far that is)."""
        best, best_s = math.inf, 0.0
        for k in range(1, len(self.pts)):
            (ax, ay), (bx, by) = self.pts[k - 1], self.pts[k]
            dx, dy = bx - ax, by - ay
            ll = dx * dx + dy * dy or 1e-9
            f = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / ll))
            d = math.hypot(x - (ax + dx * f), y - (ay + dy * f))
            if d < best:
                best, best_s = d, self.at[k - 1] + f * math.sqrt(ll)
        return best_s, best


class Leviathan(Angel):
    """Elite. Lives in the river of blood (LEVIATHAN[0] to a river:
    systems/spawner's residents) and never leaves it: it moves along the
    river's line. Serene: a white serpent swimming lazily within
    LEVIATHAN[2] of where it lives (harmless). Unveiled: surges along the
    river (its speed) to the stretch nearest you, and once within
    LEVIATHAN[6] of it spits (the windup) LEVIATHAN[3] gobs of blood in a
    LEVIATHAN[4]-degree fan every cooldown; whoever stands on it is bitten
    (every LEVIATHAN[5] s). It doesn't go to the fonts."""

    drinks = False

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.line: _Line | None = None
        self.s = 0.0
        self.home_s = 0.0
        self.way = 1.0

    def _river(self, world) -> bool:
        if self.line is None:
            lines = [_Line(p) for p in rivers(world) if len(p) > 1]
            if not lines:
                return False
            self.line = min(lines, key=lambda ln: ln.project(self.x, self.y)[1])
            self.s = self.home_s = self.line.project(self.x, self.y)[0]
        return True

    def _swim(self, ds: float) -> None:
        x0, y0 = self.x, self.y
        self.s = max(0.0, min(self.line.length, self.s + ds))
        self.x, self.y = self.line.point(self.s)
        if math.hypot(self.x - x0, self.y - y0) > 1e-6:
            self.facing = math.atan2(self.y - y0, self.x - x0)
        self._moved = math.hypot(self.x - x0, self.y - y0)
        self.walked += self._moved

    def go(self, ctx, gx, gy, dt, speed) -> bool:          # (only ever along the river)
        if not self._river(ctx.world):
            self._moved = 0.0
            return False
        goal = self.line.project(gx, gy)[0]
        self._swim(max(-speed * dt, min(speed * dt, goal - self.s)))
        return abs(goal - self.s) < 0.5

    def serene_turn(self, ctx: AIContext, dt: float) -> None:
        if not self._river(ctx.world):
            return
        swim, reach = config.LEVIATHAN[1:3]
        if self.s - self.home_s > reach or self.s >= self.line.length:
            self.way = -1.0
        elif self.home_s - self.s > reach or self.s <= 0.0:
            self.way = 1.0
        self._swim(self.way * swim * dt)

    def unveiled_turn(self, ctx: AIContext, dt: float) -> None:
        _, _, _, n, fan, bite, near = config.LEVIATHAN
        if not self._river(ctx.world):
            return
        self.touch(ctx, self.espec.damage, bite)
        t = self.target
        if self.windup > 0:
            self.windup -= dt
            self.tell = self.windup
            if t is not None:
                self.facing = self.angle_to(t.x, t.y)
            if self.windup <= 0:
                self.tell = 0.0
                if t is not None:
                    shell = config.PARADISE_SHOTS["spit"]
                    patterns.fan(self, self.x, self.y, self.angle_to(t.x, t.y), n, fan, shell,
                                 ctx.projectiles)
                    ctx.events.append(shell.sound)
                self.cooldown = self.espec.cooldown
            return
        if t is None or not self.sees_target:
            self.serene_turn(ctx, dt)
            return
        goal = self.line.project(t.x, t.y)[0]
        self.go(ctx, t.x, t.y, dt, self.speed)
        if abs(goal - self.s) <= near and self.cooldown <= 0:
            self.windup = self.espec.windup


def residents(layout, zone) -> list[tuple[str, float, float]]:
    """The enemies that live at fixed places on a zone, (key, x, y): on
    Paradise, CHORISTER[2] choristers round each choir ring (between its
    statues and the middle) and LEVIATHAN[0] leviathans spread along the
    river of blood. systems/spawner rosters them with their chunks."""
    if zone.key != "paradise":
        return []
    from ..world.paradise import plan_of
    plan = plan_of(layout, zone)
    out = []
    singers = config.CHORISTER[2]
    for qx, qy in plan.choirs:
        for k in range(singers):
            a = 0.5 + k * math.tau / singers
            out.append(("chorister", qx + 0.5 + math.cos(a) * 3.6, qy + 0.5 + math.sin(a) * 3.6))
    line = _Line(plan.river)
    n = config.LEVIATHAN[0]
    for k in range(n):
        x, y = line.point(line.length * (k + 0.5) / n)
        out.append(("leviathan", x, y))
    return out
