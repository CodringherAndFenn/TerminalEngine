"""
ai/ancestor.py -- Pangaea's boss, form 1: THE ANCESTOR, the ages (M31.4,
design/OCEAN.md 28-28.1). The beast all beasts come from, asleep in the
caldera until the seventh great beast falls. It walks back in time as you
hurt it, like the island's rings.

THE AGES (user): a third of its health each (100-67-33%): the great mammal,
the tyrant lizard, the giant insect. Each age brings a signature that keeps
going in the ages after it:
  1 the stampede  it bellows, and spirit herds (mammoths, rhinos, in ochre)
                  stampede across the caldera down lanes shown first, with
                  gaps to stand in;
  2 the roar      a huge roar in a wide cone roots you in fear unless you
                  roll, and shakes the rim: rocks fall onto marked spots all
                  over the caldera;
  3 the swarm     rivers of small insects pour across the caldera, drifting
                  and swaying; they sting what they pass through: move with
                  the gaps.
Moves, each age its own way: the charge (tusks, a lunging bite, a dive)
along a marked line; a spit fan (bone shards, boiling spit, acid); the
eruption (it stomps and lava bombs fall onto marked circles round you); the
sweep (a wide arc behind it: a hind kick, a tail sweep, a stinger -- it
backs up to you first).

IT MOULTS (user): at each third the older shape bursts out of the last
one's skin (ANCESTOR_MOULT[0] s: it can't be hurt) and leaves the old body
lying there as a husk: cover (HUSK tiles), and for a while it echoes the old
shape's attacks on its own (its charge, its spit fan, from where it lies),
until it crumbles (MOULT[5] s after; the old tiles come back).

ITS ECHOES (user): everything it does echoes ECHO[0] s later at full damage,
like everything on Pangaea (ai/pangaea.Echoing): a faded ghost of it where it
stood, the shape shown again first. An echo never echoes. Its patterns are
sparser than other tier III bosses' (longer rests, its own combo chances,
ANCESTOR_COMBO), so the echo doubles them into a fair, dense fight.

MOVEMENT (user): always moving like its age -- the mammal gallops round you,
the lizard stalks and lunges (a lunge only moves it), the insect flits and
hovers. Only the roar and the eruption plant it, with a clear tell. Like the
Host of the Feast it glides over the caldera's floor (lava, husks and all);
it never leaves the caldera.

At 0 the ages end (M31.4: it dies; M31.5 brings form 2, the first life).
Drawn by render/ancestor.py.
"""

from __future__ import annotations

import math
import random

from .. import config
from ..entities.effects import Effect
from ..specs import EnemySpec
from ..world import tiles
from .bosses import Boss
from .creatures import _numbered_hit
from .pangaea import Echo, Echoing, Runner, _wrap

_TAU = math.tau
# Each age's look (render/ancestor.py's pictures): its own, and with its
# mouth open (bellowing, roaring, spitting; the insect's wings spread).
SPRITES = (("ancestor_mammal", "ancestor_mammal_open"),
           ("ancestor_lizard", "ancestor_lizard_open"),
           ("ancestor_insect", "ancestor_insect_open"))
AGE_BANNERS = (("THE GREAT MAMMAL", ""),
               ("THE TYRANT LIZARD", "it bursts out of its skin -- the old body still remembers"),
               ("THE GIANT INSECT", "older still -- mind the husks"))
SPIRITS = ("mammoth", "woolly_rhino")        # the stampede's spirit herd


class Husk:
    """The old body it moulted (`age`'s), lying at (x, y): cover while it
    stands (the tiles it covered in `stamped`), echoing that age's attacks
    every MOULT[3] s; it crumbles MOULT[5] s after the moult."""

    __slots__ = ("age", "x", "y", "facing", "t", "cd", "k", "stamped", "crumbled")

    def __init__(self, age: int, x: float, y: float, facing: float) -> None:
        self.age, self.x, self.y, self.facing = age, x, y, facing
        self.t = 0.0
        self.cd = config.ANCESTOR_MOULT[3] * 0.6
        self.k = 0                        # which of its attacks it echoes next
        self.stamped: dict = {}
        self.crumbled = False

    @property
    def sprite(self) -> str:
        return SPRITES[self.age][0]


class River:
    """A river of insects (the swarm): a band `half` tiles either side of a
    line through (x0, y0) along `angle`, across the arena; after `shown` s
    it stings for the rest of its `life`, drifting sideways (`drift` tiles/s)
    and swaying (`sway` tiles). An echo's is the same river again."""

    __slots__ = ("x0", "y0", "angle", "drift", "sway", "phase", "shown", "life", "half",
                 "damage", "every", "echo", "t", "cds")

    def __init__(self, x0, y0, angle, drift, sway, phase, shown, life, half, damage, every,
                 echo=False) -> None:
        self.x0, self.y0, self.angle = x0, y0, angle
        self.drift, self.sway, self.phase = drift, sway, phase
        self.shown, self.life, self.half = shown, life, half
        self.damage, self.every, self.echo = damage, every, echo
        self.t = 0.0
        self.cds: dict[int, float] = {}

    def params(self) -> dict:
        return dict(x0=self.x0, y0=self.y0, angle=self.angle, drift=self.drift, sway=self.sway,
                    phase=self.phase, shown=self.shown, life=self.life, half=self.half,
                    damage=self.damage, every=self.every)

    @property
    def stinging(self) -> bool:
        return self.t >= self.shown

    def offset(self, t: float | None = None) -> float:
        """How far its line has moved sideways (tiles), `t` s into its life."""
        u = max(0.0, (self.t if t is None else t) - self.shown)
        return self.drift * u + self.sway * math.sin(u * 1.3 + self.phase) - self.sway * math.sin(
            self.phase)

    def across(self, x: float, y: float, t: float | None = None) -> float:
        """(x, y)'s distance from its line, sideways (signed)."""
        ca, sa = math.cos(self.angle), math.sin(self.angle)
        return (x - self.x0) * -sa + (y - self.y0) * ca - self.offset(t)


class Ancestor(Echoing, Boss):
    """The Ancestor, form 1 (see the module's docstring)."""

    def __init__(self, spec: EnemySpec, x: float, y: float, rng: random.Random,
                 spawn_id=None) -> None:
        super().__init__(spec, x, y, rng, spawn_id, hit_radius=config.ANCESTOR_HIT_RADIUS[0])
        self.init_echoes()
        self.age = 0                      # 0 the great mammal, 1 the tyrant lizard, 2 the insect
        self.moulting = 0.0               # s left bursting out of its skin (it can't be hurt)
        self.husks: list[Husk] = []
        self.rivers: list[River] = []
        self.pose = ""                    # "open" (bellowing, roaring, spitting), "charge", "stomp"
        self.planted = False              # the roar, the eruption: standing still
        self.busy = False                 # a move is moving it (a charge, backing up to sweep)
        # What it's showing before a move (render/ancestor.py):
        self.lanes: list[tuple] = []      # the stampede: [(x0, y0, angle, length, half)]
        self.cone: tuple | None = None    # the roar's, the sweep's: (x, y, angle, reach, half)
        self.line: tuple | None = None    # a charge's: (x0, y0, angle, length, half)
        self.fans: list[float] = []       # a spit fan's angles
        # Its gait:
        self.round_a = rng.uniform(0, _TAU)    # the mammal's gallop round you
        self.round_dir = 1
        self.round_t = 0.0
        self.lunge_cd = config.ANCESTOR_STALK[2]   # the lizard's
        self.lunge: list | None = None    # [vx, vy, s left]
        self.hover = 0.0                  # the insect's: s left hovering
        self.flit_to: tuple | None = None
        self.banner_req: tuple | None = None   # (title, sub): the quest shows it

    # --- Being the Ancestor --------------------------------------------------------------

    @property
    def hittable(self) -> bool:
        return Boss.hittable.fget(self) and self.moulting <= 0

    @property
    def bar_label(self) -> str:
        return f"The Ancestor -- {config.ANCESTOR_AGES[self.age]}"

    def victims(self, ctx) -> list:
        return [h for h in ctx.players if h.alive]

    def sprite_now(self) -> str:
        return SPRITES[self.age][1 if self.pose in ("open", "stomp") else 0]

    def hurt(self, base: float) -> float:
        return base * self.damage_mult

    def _arena(self) -> tuple[float, float, float, float]:
        """(cx, cy, a, b): its arena's oval (without a lair, a test's: round
        where it woke)."""
        lair = self.lair
        if lair is not None:
            return lair.cx, lair.cy, float(lair.radii[0]), float(lair.radii[1])
        return self.home[0], self.home[1], 30.0, 22.0

    def _chord(self, x: float, y: float, angle: float, grow: float = 0.0):
        """Where the line through (x, y) along `angle` crosses the arena:
        (start x, start y, length), or None if it misses."""
        cx, cy, a, b = self._arena()
        a, b = a + grow, b + grow
        ux, uy = math.cos(angle), math.sin(angle)
        dx, dy = x - cx, y - cy
        qa = (ux / a) ** 2 + (uy / b) ** 2
        qb = 2 * (dx * ux / a ** 2 + dy * uy / b ** 2)
        qc = (dx / a) ** 2 + (dy / b) ** 2 - 1.0
        disc = qb * qb - 4 * qa * qc
        if disc <= 0:
            return None
        r = math.sqrt(disc)
        s0, s1 = (-qb - r) / (2 * qa), (-qb + r) / (2 * qa)
        return x + ux * s0, y + uy * s0, s1 - s0

    def _inside(self, x: float, y: float, shrink: float = 0.0) -> bool:
        cx, cy, a, b = self._arena()
        return ((x - cx) / max(1.0, a - shrink)) ** 2 + ((y - cy) / max(1.0, b - shrink)) ** 2 < 1.0

    def _room_ahead(self, x: float, y: float, angle: float, want: float) -> float:
        """How far it can run from (x, y) along `angle` (at most `want`)
        before its body would leave the arena."""
        shrink = self.hit_radius + 1.0
        step, d = 0.5, 0.0
        while d + step <= want and self._inside(x + math.cos(angle) * (d + step),
                                                y + math.sin(angle) * (d + step), shrink):
            d += step
        return d

    def _random_spot(self, shrink: float = 3.0) -> tuple[float, float]:
        cx, cy, a, b = self._arena()
        r, ang = math.sqrt(self.rng.random()), self.rng.uniform(0, _TAU)
        return (cx + math.cos(ang) * r * max(1.0, a - shrink),
                cy + math.sin(ang) * r * max(1.0, b - shrink))

    # --- Its turn --------------------------------------------------------------------------

    def think(self, ctx, dt: float) -> None:
        self.ctx = ctx
        self.play_echoes(ctx, dt)                      # (its echoes and the husks' play on)
        self._tick_husks(ctx, dt)
        self._tick_rivers(ctx, dt)
        if self.moulting > 0:
            self.moulting = max(0.0, self.moulting - dt)
            self.time += dt
            return
        if not (self.planted or self.busy) and self.dazed <= 0:
            self._move_like_its_age(dt)
        super().think(ctx, dt)

    def _end_move(self) -> None:
        """As any boss's, but with its own, smaller, combo chances (its
        echoes double everything)."""
        self._settle()
        self.last_move = self.move
        self.move, self._gen, self.tell = None, None, None
        chance, most = config.ANCESTOR_COMBO[min(self.phase, len(config.ANCESTOR_COMBO) - 1)]
        if self.combo < most and self.rng.random() < chance:
            self.combo += 1
            self._rest = config.BOSS_COMBO_GAP
            return
        self.combo = 0
        scale = config.BOSS_REST_SCALE[min(self.phase, len(config.BOSS_REST_SCALE) - 1)]
        self._rest = self.bspec.phases[self.phase].rest * scale

    def _start(self, name: str) -> None:
        self._settle()
        Boss._start(self, name)

    def _settle(self) -> None:
        """Nothing of a move left standing (it ended, or another began)."""
        self.planted = self.busy = False
        self.pose = ""
        self.lanes, self.cone, self.line, self.fans = [], None, None, []
        self.airborne = 0.0

    # --- Moving like its age -----------------------------------------------------------

    def _glide(self, gx: float, gy: float, v: float, dt: float) -> None:
        dx, dy = gx - self.x, gy - self.y
        d = math.hypot(dx, dy)
        if d < 1e-6:
            return
        step = min(d, v * dt)
        self.x, self.y = self.clamp_to_lair(self.x + dx / d * step, self.y + dy / d * step,
                                            self.hit_radius + 1.0)

    def _move_like_its_age(self, dt: float) -> None:
        t = self.drift_target()
        if t is None:
            return
        if self.age == 0:
            self._gallop(t, dt)
        elif self.age == 1:
            self._stalk(t, dt)
        else:
            self._flit(t, dt)

    def _gallop(self, t, dt: float) -> None:
        """The great mammal gallops round you: a round of ANCESTOR_GALLOP[1]
        tiles about you, turning at most [2] rad/s, now and then reversing."""
        speed, r, rate = config.ANCESTOR_GALLOP
        self.round_t += dt
        if self.round_t >= 7.0:
            self.round_t = 0.0
            self.round_dir = -self.round_dir
        self.round_a += self.round_dir * speed / r * dt
        gx, gy = t.x + math.cos(self.round_a) * r, t.y + math.sin(self.round_a) * r * 0.8
        gx, gy = self.clamp_to_lair(gx, gy, self.hit_radius + 2.0)
        want = math.atan2(gy - self.y, gx - self.x)
        diff = _wrap(want - self.facing)
        step = rate * dt
        self.facing = _wrap(self.facing + max(-step, min(step, diff)))
        far = math.hypot(gx - self.x, gy - self.y)
        v = speed * (1.3 if far > r else 1.0)
        self._glide(self.x + math.cos(self.facing) * v * dt * 4,
                    self.y + math.sin(self.facing) * v * dt * 4, v, dt)

    def _stalk(self, t, dt: float) -> None:
        """The tyrant lizard stalks you at ANCESTOR_STALK[1] tiles, and
        lunges [3] tiles every [2] s (a lunge only moves it)."""
        speed, keep, every, length, fast = config.ANCESTOR_STALK
        d = math.hypot(t.x - self.x, t.y - self.y)
        to = math.atan2(t.y - self.y, t.x - self.x)
        self.facing = to
        if self.lunge is not None:
            vx, vy, left = self.lunge
            self._glide(self.x + vx, self.y + vy, fast, dt)
            self.lunge[2] -= dt
            if self.lunge[2] <= 0:
                self.lunge = None
            return
        self.lunge_cd -= dt
        if self.lunge_cd <= 0 and d > keep * 0.6:
            self.lunge_cd = every * self.rng.uniform(0.8, 1.2)
            side = self.rng.choice((-0.6, 0.6))
            a = to + side
            self.lunge = [math.cos(a) * length, math.sin(a) * length, length / fast]
            return
        if d > keep + 1.5:
            self._glide(t.x, t.y, speed, dt)
        elif d < keep - 1.5:
            self._glide(self.x - math.cos(to) * 3, self.y - math.sin(to) * 3, speed * 0.8, dt)
        else:                                            # (circling you, step by step)
            a = to + math.pi / 2 * self.round_dir
            self._glide(self.x + math.cos(a) * 3, self.y + math.sin(a) * 3, speed * 0.8, dt)

    def _flit(self, t, dt: float) -> None:
        """The giant insect hovers ANCESTOR_FLIT[0] s, then flits fast to a
        new spot [2] tiles from you (at most [3] tiles off)."""
        hover, fast, keep, most = config.ANCESTOR_FLIT
        if self.flit_to is not None:
            self._glide(*self.flit_to, fast, dt)
            if math.hypot(self.flit_to[0] - self.x, self.flit_to[1] - self.y) < 0.4:
                self.flit_to = None
                self.hover = hover * self.rng.uniform(0.8, 1.2)
            return
        self.facing = math.atan2(t.y - self.y, t.x - self.x)
        self.hover -= dt
        if self.hover > 0:
            return
        for _ in range(8):
            a = self.rng.uniform(0, _TAU)
            gx, gy = t.x + math.cos(a) * keep, t.y + math.sin(a) * keep * 0.8
            if 4.0 <= math.hypot(gx - self.x, gy - self.y) <= most:
                break
        else:
            d = math.hypot(gx - self.x, gy - self.y) or 1.0
            gx, gy = self.x + (gx - self.x) / d * most, self.y + (gy - self.y) / d * most
        self.flit_to = self.clamp_to_lair(gx, gy, self.hit_radius + 1.5)

    # --- The ages and the moults ----------------------------------------------------------

    def on_phase(self, phase: int, ctx) -> None:
        age = min(phase, len(SPRITES) - 1)
        if age <= self.age:
            return
        old = self.age
        if self._gen is not None:                       # (the move it was in stops)
            self.move, self._gen, self.tell = None, None, None
        self._settle()
        self.lunge, self.flit_to = None, None
        self.age = age
        self.hit_radius = config.ANCESTOR_HIT_RADIUS[age]
        self.moulting = config.ANCESTOR_MOULT[0]
        self._rest = 0.8
        self._leave_husk(old, ctx)
        # (the new shape bursts out of the old skin toward you, clear of it)
        t = self.drift_target()
        a = self.angle_to(t.x, t.y) if t is not None else self.facing
        out = config.ANCESTOR_MOULT[1] + self.hit_radius + 0.5
        self.x, self.y = self.clamp_to_lair(self.x + math.cos(a) * out, self.y + math.sin(a) * out,
                                            self.hit_radius + 1.0)
        self.facing = a
        self.banner_req = AGE_BANNERS[age]
        for k in range(8):
            a = k * _TAU / 8
            ctx.effects.append(Effect("debris", self.x + math.cos(a) * 2.0, self.y + math.sin(a) * 1.4))
        ctx.effects.append(Effect("explosion", self.x, self.y))
        ctx.effects.append(Effect("toast", self.x, self.y - self.hit_radius - 2, label="IT MOULTS!"))
        ctx.events.append("boulder")

    def _leave_husk(self, age: int, ctx) -> None:
        """The old body, lying where it moulted: an oval of HUSK tiles
        (not where a hero stands), cover until it crumbles."""
        h = Husk(age, self.x, self.y, self.facing)
        _, ra, rb, *_ = config.ANCESTOR_MOULT
        w = ctx.world
        if hasattr(w, "set_tile"):
            for j in range(-math.ceil(rb), math.ceil(rb) + 1):
                for i in range(-math.ceil(ra), math.ceil(ra) + 1):
                    if (i / ra) ** 2 + (j / rb) ** 2 >= 1.0:
                        continue
                    tx, ty = math.floor(h.x) + i, math.floor(h.y) + j
                    if any(p.alive and math.hypot(p.x - tx - 0.5, p.y - ty - 0.5) < p.hit_radius + 1.0
                           for p in ctx.players):
                        continue
                    t = w.tile_at(tx, ty)
                    if t is None or t.solid:
                        continue
                    h.stamped[(tx, ty)] = t
                    w.set_tile(tx, ty, tiles.HUSK)
        self.husks.append(h)

    def _crumble(self, h: Husk, ctx) -> None:
        h.crumbled = True
        w = ctx.world
        if hasattr(w, "set_tile"):
            for (tx, ty), t in h.stamped.items():
                w.set_tile(tx, ty, t)
        h.stamped = {}
        ctx.effects.append(Effect("debris", h.x, h.y))
        ctx.effects.append(Effect("toast", h.x, h.y - 2, label="THE HUSK CRUMBLES"))

    def _tick_husks(self, ctx, dt: float) -> None:
        _, _, _, every, tell, lasts = config.ANCESTOR_MOULT
        for h in self.husks:
            if h.crumbled:
                continue
            h.t += dt
            if h.t >= lasts:
                self._crumble(h, ctx)
                continue
            h.cd -= dt
            if h.cd <= 0:
                h.cd = every
                self._husk_echo(h, tell)

    def _husk_echo(self, h: Husk, tell: float) -> None:
        """The husk echoes one of its age's attacks from where it lies (its
        charge, then its spit fan, in turn) at the hero nearest it."""
        heroes = [p for p in self.victims(self.ctx) if self.in_arena(p)]
        if not heroes:
            return
        t = min(heroes, key=lambda p: math.hypot(p.x - h.x, p.y - h.y))
        a = math.atan2(t.y - h.y, t.x - h.x)
        h.facing = a
        if h.k % 2 == 0:
            _, length, speed, half, dmg, push = config.ANCESTOR_CHARGE[h.age]
            data = dict(x0=h.x, y0=h.y, angle=a, length=length, speed=speed, radius=half,
                        damage=self.hurt(dmg), push=push, sprite=h.sprite)
            kind = "run"
        else:
            shot, n, spread, _ = config.ANCESTOR_SPIT[h.age]
            dmg = config.PANGAEA_SHOTS[shot].damage * self.damage_mult
            data = dict(shots=[(h.x, h.y, a2, shot, dmg, None) for a2 in self._fan_angles(a, n, spread)])
            kind = "shots"
        h.k += 1
        e = Echo(kind, tell, h.x, h.y, a, h.sprite, data)
        e.t = tell                                        # (its tell shows now)
        self.echoes.append(e)

    # --- Signature 1: the stampede ----------------------------------------------------------

    def m_stampede(self):
        bellow, shown, n, gap, half, speed, dmg, push, stagger = config.ANCESTOR_STAMPEDE
        t = self.target_now()
        if t is None:
            return
        self.planted = True
        self.pose = "open"
        self.facing = self.angle_to(t.x, t.y)
        self.tell = ("stampede",)
        self.ctx.effects.append(Effect("beast_roar", self.x, self.y, size=6.0))
        self.ctx.events.append("roar")
        yield self.tell_s(bellow)
        self.pose = ""
        self.planted = False
        a = self.rng.uniform(0, _TAU)
        px, py = -math.sin(a), math.cos(a)
        phase = self.rng.uniform(-gap / 2, gap / 2)
        lanes = []
        reach = config.ANCESTOR_STAMPEDE_REACH
        ux, uy = math.cos(a), math.sin(a)
        for k in range(n):
            off = (k - (n - 1) / 2) * gap + phase
            mx, my = t.x + px * off, t.y + py * off
            c = self._chord(mx, my, a, grow=2.0)
            if c is None:
                continue
            # (across the caldera, but from at most `reach` tiles before your
            # line to at most `reach` past it: the herd's on you in a breath)
            s0 = max((c[0] - mx) * ux + (c[1] - my) * uy, -reach)
            s1 = min((c[0] - mx) * ux + (c[1] - my) * uy + c[2], reach)
            if s1 - s0 > 4:
                lanes.append((mx + ux * s0, my + uy * s0, a, s1 - s0, half))
        self.lanes = lanes
        wait = self.tell_s(shown)
        yield wait
        self.lanes = []
        for k, (x0, y0, ang, length, hw) in enumerate(lanes):
            sprite = SPIRITS[k % len(SPIRITS)]
            r = Runner(x0, y0, ang, length, speed, hw, self.hurt(dmg), push, sprite, "ochre")
            r.done = -self.rng.uniform(0.0, stagger) * speed     # (a herd: not all at once)
            self.runners.append(r)
            self.record_run(x0, y0, ang, length, speed, hw, self.hurt(dmg), push, tell=wait,
                            sprite=sprite)
        self.ctx.events.append("boulder")
        yield 0.3

    # --- Signature 2: the roar --------------------------------------------------------------

    def m_roar(self):
        shown, cone, reach, fear, dmg = config.ANCESTOR_ROAR
        n, near, marked, radius, _, spread = config.ANCESTOR_ROCKS
        t = self.target_now()
        if t is None:
            return
        self.planted = True
        self.pose = "open"
        self.facing = self.angle_to(t.x, t.y)
        half = math.radians(cone) / 2
        self.cone = (self.x, self.y, self.facing, reach, half)
        self.tell = ("roar",)
        wait = self.tell_s(shown)
        yield wait
        self.cone = None
        self.area(self.ctx, "cone", self.x, self.y, self.facing, reach, half, self.hurt(dmg),
                  tell=wait, root=fear)
        self.ctx.effects.append(Effect("beast_roar", self.x, self.y, size=reach))
        self.ctx.events.append("roar")
        # (it shakes the rim: rocks fall on marked spots all over the caldera)
        spots = []
        for h in self.victims(self.ctx):
            if not self.in_arena(h):
                continue
            for k in range(near):
                r, ang = (0.0 if k == 0 else self.rng.uniform(2.0, spread)), self.rng.uniform(0, _TAU)
                spots.append(self.clamp_to_lair(h.x + math.cos(ang) * r, h.y + math.sin(ang) * r, 1.0))
        while len(spots) < n:
            spots.append(self._random_spot())
        self.lob_many(self.ctx, [(x, y - 0.01, x, y) for x, y in spots], self.tell_s(marked), "rock",
                      tell=marked)
        yield 0.5

    # --- Signature 3: the swarm -------------------------------------------------------------

    def m_swarm(self):
        n, shown, stings, half, drift, sway, dmg, every = config.ANCESTOR_SWARM
        t = self.target_now()
        if t is None:
            return
        self.pose = "open"
        self.tell = ("swarm",)
        self.ctx.effects.append(Effect("toast", self.x, self.y - self.hit_radius - 2,
                                       label="THE SWARM POURS OUT"))
        base = self.rng.uniform(0, _TAU)
        wait = self.tell_s(shown)
        for k in range(n):
            a = base + k * math.pi / n + self.rng.uniform(-0.2, 0.2)
            px, py = -math.sin(a), math.cos(a)
            off = self.rng.uniform(-5.0, 5.0)
            d = self.rng.choice((-1.0, 1.0)) * drift * self.rng.uniform(0.6, 1.0)
            river = River(t.x + px * off, t.y + py * off, a, d, sway, self.rng.uniform(0, _TAU),
                          wait, wait + stings, half, self.hurt(dmg), every)
            self.rivers.append(river)
            data = river.params()
            data["shown"] = 0.0
            data["life"] = stings
            self._record("river", wait, data)
        yield 0.6
        self.pose = ""

    def _tick_rivers(self, ctx, dt: float) -> None:
        for r in self.rivers:
            r.t += dt
            for k in list(r.cds):
                r.cds[k] -= dt
            if not r.stinging:
                continue
            for h in self.victims(ctx):
                if not h.hittable or r.cds.get(id(h), 0.0) > 0:
                    continue
                if abs(r.across(h.x, h.y)) <= r.half + h.hit_radius and self._inside(h.x, h.y, -2.0):
                    r.cds[id(h)] = r.every
                    _numbered_hit(h, r.damage, self, r.angle + math.pi / 2, ctx)
        self.rivers = [r for r in self.rivers if r.t < r.life]

    def _play(self, ctx, e: Echo) -> None:
        if e.kind == "river":
            self.rivers.append(River(**e.data, echo=True))
        else:
            super()._play(ctx, e)

    # --- The charge ---------------------------------------------------------------------------

    def m_charge(self):
        age = self.age
        shown, length, speed, half, dmg, push = config.ANCESTOR_CHARGE[age]
        half = max(half, self.hit_radius)              # (its whole body runs the line)
        t = self.target_now()
        if t is None:
            return
        self.busy = True
        a = self.aim(t, self.x, self.y, speed)
        self.facing = a
        run = self._room_ahead(self.x, self.y, a, length)
        if run < 2.0:                                  # (no room: it turns and goes the other way)
            a = self.angle_to(*self._arena()[:2])
            self.facing = a
            run = self._room_ahead(self.x, self.y, a, length)
        self.line = (self.x, self.y, a, run, half)
        self.pose = "charge"
        self.tell = ("charge",)
        if age == 2:
            self.airborne = 1.0                        # (the insect rises before it dives)
        wait = self.tell_s(shown)
        yield wait
        self.line = None
        self.airborne = 0.0
        self.record_run(self.x, self.y, a, run, speed, half, self.hurt(dmg), push, tell=wait)
        hit: set[int] = set()
        ran = 0.0
        while ran < run:
            step = min(run - ran, speed * self.dt)
            ran += step
            self.x += math.cos(a) * step
            self.y += math.sin(a) * step
            self.ram(self.ctx, self.x, self.y, half, self.hurt(dmg), push, a, hit)
            yield 0
        if age == 1:                                   # (the lunge ends in a bite)
            deg, reach = config.ANCESTOR_BITE
            self.pose = "open"
            self.area(self.ctx, "cone", self.x, self.y, a, reach, math.radians(deg) / 2,
                      self.hurt(dmg), push, tell=wait)
            self.ctx.events.append("hit")
        yield 0.45

    # --- The spit fan --------------------------------------------------------------------------

    @staticmethod
    def _fan_angles(a: float, n: int, spread: float) -> list[float]:
        s = math.radians(spread)
        return [a + (s * (k / (n - 1) - 0.5) if n > 1 else 0.0) for k in range(n)]

    def m_spit(self):
        shot, n, spread, shown = config.ANCESTOR_SPIT[self.age]
        t = self.target_now()
        if t is None:
            return
        a = self.aim(t, self.x, self.y, config.PANGAEA_SHOTS[shot].speed)
        self.facing = a
        self.pose = "open"
        self.fans = self._fan_angles(a, n, spread)
        self.tell = ("spit",)
        wait = self.tell_s(shown)
        yield wait
        angles, self.fans = self.fans, []
        self.fan(self.ctx, shot, angles, tell=wait)
        yield 0.35

    # --- The eruption --------------------------------------------------------------------------

    def m_eruption(self):
        stomp, n, marked, radius, dmg, spread = config.ANCESTOR_ERUPTION
        if self.target_now() is None:
            return
        self.planted = True
        self.pose = "stomp"
        self.tell = ("eruption",)
        yield self.tell_s(stomp)
        self.ctx.effects.append(Effect("explosion", self.x, self.y))
        self.ctx.events.append("boulder")
        spots = []
        for h in self.victims(self.ctx):
            if not self.in_arena(h):
                continue
            x, y = self.lead(h, h.x, h.y, secs=marked)
            spots.append(self.clamp_to_lair(x, y, 1.0))
            for k in range(n - 1):
                r, ang = self.rng.uniform(2.5, spread), k * _TAU / (n - 1) + self.rng.uniform(-0.3, 0.3)
                spots.append(self.clamp_to_lair(h.x + math.cos(ang) * r, h.y + math.sin(ang) * r, 1.0))
        wait = self.tell_s(marked)
        self.lob_many(self.ctx, [(x, y - 0.01, x, y) for x, y in spots], wait, "bomb", tell=wait)
        yield 0.5

    # --- The sweep -----------------------------------------------------------------------------

    def m_sweep(self):
        deg, reach, dmg, push, shown = config.ANCESTOR_SWEEP[self.age]
        most, fast = config.ANCESTOR_SWEEP_CLOSE
        t = self.target_now()
        if t is None:
            return
        self.busy = True
        took = 0.0
        while took < most and math.hypot(t.x - self.x, t.y - self.y) > reach * 0.7 + t.hit_radius:
            a = math.atan2(self.y - t.y, self.x - t.x)          # (backing up to it)
            self._glide(t.x + math.cos(a) * reach * 0.5, t.y + math.sin(a) * reach * 0.5,
                        config.ANCESTOR_GALLOP[0] * fast, self.dt)
            self.facing = a
            took += self.dt
            yield 0
            if not t.alive:
                return
        at = self.angle_to(t.x, t.y)
        self.facing = at + math.pi                              # (its back to you)
        half = math.radians(deg) / 2
        self.cone = (self.x, self.y, at, reach, half)
        self.tell = ("sweep",)
        wait = self.tell_s(shown)
        yield wait
        self.cone = None
        self.area(self.ctx, "cone", self.x, self.y, at, reach, half, self.hurt(dmg), push, tell=wait)
        self.ctx.effects.append(Effect("swing", self.x, self.y, angle=at, size=reach, value=deg))
        self.ctx.events.append("swing")
        yield 0.4

    # --- What lands -----------------------------------------------------------------------------

    def landed(self, ctx, x: float, y: float, what: str, echo: bool) -> None:
        if what == "rock":
            _, _, _, radius, dmg, _ = config.ANCESTOR_ROCKS
            ctx.effects.append(Effect("debris", x, y))
        else:
            _, _, _, radius, dmg, _ = config.ANCESTOR_ERUPTION
            ctx.effects.append(Effect("lava_burst", x, y, size=radius))
        self.area(ctx, "circle", x, y, 0.0, radius, 0.0, self.hurt(dmg), record=False)
        ctx.events.append("boulder")

    def on_death(self, ctx) -> None:
        super().on_death(ctx)
        self.drop_echoes(ctx)
        self.rivers = []
        for h in self.husks:
            if not h.crumbled:
                self._crumble(h, ctx)
