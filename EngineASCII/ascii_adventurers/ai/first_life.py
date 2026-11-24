"""
ai/first_life.py -- Pangaea's boss, form 2: THE FIRST LIFE (M31.5,
design/OCEAN.md 28.2-28.3). A mix-in of ai/ancestor.Ancestor (one body, two
forms, like the Host of the Feast's hunger): at 0 the giant insect's skin
splits too (a third husk), and the first life rises -- the oldest hunter of
the first seas, a vast segmented thing with grasping arms and a round mouth
ringed with teeth.

THE SPLIT: FIRST_LIFE_RISE s in which it can't be hit while the caldera
floods with the first sea, from the rim in; the lava lakes quench into
rocks, and more rocks stand all over it (mine: a jittered grid, TIDE_ROCKS).
Then it's back at full health (x FIRST_LIFE_HP: 14,000 of 12,000).

THE TIDE (user): the sea rises and falls. At low tide it's shallows you walk
like the floor; at high tide it's the deep, and you wade it slowly (TIDE[4];
a roll still carries you its full length) while it swims freely: only the
rocks and the husks stand above it. Mine: a tide every ~20 s, the deep
creeping in from the rim over TIDE[1] s (that's the warning), the middle
last.

SIGNATURES, one added per phase (100-75-50-25%), each kept on after:
  1 LIFE EVOLVES   small first life crawls out of the sea round you; left
                   alone, a blob becomes a crawler, then one of the island's
                   beasts (a raptor, a sabre-tooth cub). Kill them young.
  2 ECHOES OF THE AGES  the three husks wake as echoes (they stand for the
                   rest of the fight) and each replays its age's signature
                   from where it lies: the mammal's stampede, the lizard's
                   roar, the insect's swarm.
  3 TENTACLES      its arms burst out of the sea on marked spots far from
                   its body and sweep along marked arcs: caught, you're held
                   and squeezed until you roll free.
  4 THE TIDAL WAVE it rears up and a great wave rolls across the caldera,
                   hitting and carrying you: roll through it.
Moves: dive and surface (it sinks out of sight; its spot swells under you;
it bursts up with a ring of spray), whirlpool (a spinning current dragging
you round and in: walk or roll out), boiling bubbles (chains of them
bursting through where you are), arm lash (arms lash along shown lines,
then grab you and pull you in to be bitten: roll free).

Everything it does echoes ECHO[0] s later (ai/pangaea.Echoing), the husks'
signatures too -- once: an echo never echoes. Drawn by render/first_life.py.
"""

from __future__ import annotations

import math
import random

import numpy as np

from .. import config
from ..entities.effects import Effect
from ..systems import combat, patterns
from ..systems.pangaea import land as pangaea_land
from ..world import tiles
from .creatures import _numbered_hit
from .pangaea import Biter

_TAU = math.tau
# What the first sea covers, and what quenches into rock (the lava lakes).
SEA_FLOORS = (tiles.CALDERA_FLOOR, tiles.LAVA_CRUST)
WET = (tiles.TIDE_SHALLOWS, tiles.TIDE_SEA)


def _held_by(holders, h) -> bool:
    return any(id(h) in getattr(x, "held", {}) or getattr(x, "grip", None) is h for x in holders)


class Lash:
    """An arm lashing out along a shown line from (x0, y0) (`shown` s
    marked), whipping out at `speed`; it grabs the first hero its tip
    touches (not mid-roll) and drags them in to `keep` tiles from its root,
    then bites. A roll pulls free."""

    __slots__ = ("x0", "y0", "angle", "length", "shown", "speed", "width", "drag", "keep",
                 "bite", "echo", "t", "len", "out", "grip", "done")

    def __init__(self, x0, y0, angle, length, shown, speed, width, drag, keep, bite,
                 echo=False) -> None:
        self.x0, self.y0, self.angle, self.length = x0, y0, angle, length
        self.shown, self.speed, self.width = shown, speed, width
        self.drag, self.keep, self.bite, self.echo = drag, keep, bite, echo
        self.t = 0.0
        self.len = 0.0
        self.out = True
        self.grip = None
        self.done = False

    def params(self) -> dict:
        return dict(x0=self.x0, y0=self.y0, angle=self.angle, length=self.length, shown=0.0,
                    speed=self.speed, width=self.width, drag=self.drag, keep=self.keep,
                    bite=self.bite)

    def tip(self) -> tuple[float, float]:
        return self.x0 + math.cos(self.angle) * self.len, self.y0 + math.sin(self.angle) * self.len


class Sweep:
    """A tentacle: it bursts out of the sea at (bx, by) after `shown` s (its
    spot rippling, its arc marked), then sweeps from `a0` through `arc`
    radians, `length` long, in `sweep` s; whoever it passes (not mid-roll)
    is held where it caught them, carried with it and squeezed until they
    roll free or it lets go (`hold` s)."""

    __slots__ = ("bx", "by", "a0", "arc", "length", "shown", "sweep", "burst_r", "burst_dmg",
                 "hold", "squeeze", "squeezes", "echo", "t", "burst", "held", "caught")

    def __init__(self, bx, by, a0, arc, length, shown, sweep, burst_r, burst_dmg, hold, squeeze,
                 squeezes, echo=False) -> None:
        self.bx, self.by, self.a0, self.arc, self.length = bx, by, a0, arc, length
        self.shown, self.sweep = shown, sweep
        self.burst_r, self.burst_dmg = burst_r, burst_dmg
        self.hold, self.squeeze, self.squeezes, self.echo = hold, squeeze, squeezes, echo
        self.t = 0.0
        self.burst = False
        self.held: dict = {}              # id -> [hero, s left, s to the next squeeze, left, along]
        self.caught: set = set()

    def params(self) -> dict:
        return dict(bx=self.bx, by=self.by, a0=self.a0, arc=self.arc, length=self.length,
                    shown=0.0, sweep=self.sweep, burst_r=self.burst_r, burst_dmg=self.burst_dmg,
                    hold=self.hold, squeeze=self.squeeze, squeezes=self.squeezes)

    @property
    def angle(self) -> float:
        u = min(1.0, max(0.0, (self.t - self.shown) / self.sweep))
        return self.a0 + self.arc * u

    @property
    def up(self) -> bool:
        return self.t >= self.shown

    @property
    def over(self) -> bool:
        return self.t >= self.shown + self.sweep and not self.held


class Whirl:
    """A whirlpool at (x, y): shown `shown` s, then spinning `spin` s,
    `radius` round, dragging heroes round (`swirl` tiles/s, `turn` +-1) and
    in (`pull`); in its eye (`core`) it hurts `damage` every `every` s."""

    __slots__ = ("x", "y", "shown", "spin", "radius", "swirl", "pull", "core", "damage", "every",
                 "turn", "echo", "t", "cds")

    def __init__(self, x, y, shown, spin, radius, swirl, pull, core, damage, every, turn,
                 echo=False) -> None:
        self.x, self.y, self.shown, self.spin, self.radius = x, y, shown, spin, radius
        self.swirl, self.pull, self.core, self.damage, self.every = swirl, pull, core, damage, every
        self.turn, self.echo = turn, echo
        self.t = 0.0
        self.cds: dict[int, float] = {}

    def params(self) -> dict:
        return dict(x=self.x, y=self.y, shown=0.0, spin=self.spin, radius=self.radius,
                    swirl=self.swirl, pull=self.pull, core=self.core, damage=self.damage,
                    every=self.every, turn=self.turn)

    @property
    def spinning(self) -> bool:
        return self.t >= self.shown


class Wave:
    """The tidal wave: a front across the whole caldera, starting through
    (x0, y0) square to `angle` and rolling `length` tiles along it at
    `speed`; it hits each hero once and carries them `carry` s -- unless
    they roll through it."""

    __slots__ = ("x0", "y0", "angle", "length", "speed", "damage", "carry", "echo", "done",
                 "carried", "passed")

    def __init__(self, x0, y0, angle, length, speed, damage, carry, echo=False) -> None:
        self.x0, self.y0, self.angle, self.length = x0, y0, angle, length
        self.speed, self.damage, self.carry, self.echo = speed, damage, carry, echo
        self.done = 0.0
        self.carried: dict = {}           # id -> [hero, s left]
        self.passed: set = set()

    def params(self) -> dict:
        return dict(x0=self.x0, y0=self.y0, angle=self.angle, length=self.length,
                    speed=self.speed, damage=self.damage, carry=self.carry)

    @property
    def front(self) -> tuple[float, float]:
        return (self.x0 + math.cos(self.angle) * self.done,
                self.y0 + math.sin(self.angle) * self.done)


# --- The first life crawling out of the sea --------------------------------------------------


class FirstBlob(Biter):
    """A blob of the first life: it oozes at you (it can't hurt you yet).
    Left alone it evolves (the Ancestor sees to it: `grow_t`)."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.stage = 0
        self.grow_t: float | None = None
        self.alert = True

    def turn(self, ctx, dt: float) -> None:
        t = self.target
        if t is None or not self.sees_target:
            self.roam(ctx, dt)
            return
        self.facing = self.angle_to(t.x, t.y)
        if self.dist_to(t) > t.hit_radius + self.hit_radius + 0.4:
            self.go(ctx, t.x, t.y, dt, self.speed)


class FirstCrawler(FirstBlob):
    """A crawler (a blob left alone): it runs at you and bites."""

    def turn(self, ctx, dt: float) -> None:
        self.chase_bite(ctx, dt, self.speed)


# --- Form 2 ------------------------------------------------------------------------------------


class FirstLife:
    """Form 2 of ai/ancestor.Ancestor (see the module's docstring)."""

    def _init_first_life(self) -> None:
        self.form = 1                     # 1 the ages, "rising", 2 the first life
        self.rise_t = 0.0
        # The flood: every tile it changes, in the order the sea reaches them
        # (from the rim in), what each was, which are the sea's (the tide's).
        self.flood: list = []             # [((tx, ty), becomes)]
        self.flood_at: dict = {}          # (tx, ty) -> its index in `flood`
        self.flooded = 0                  # how many of `flood` are done
        self.orig: dict = {}              # (tx, ty) -> the tile before the flood
        self.sea: list = []               # the sea's tiles, the rim first
        self.sea_at: dict = {}            # (tx, ty) -> its index in `sea`
        self.deep = 0                     # sea[:deep] are the deep now
        self.tide = "low"                 # low | rising | high | falling
        self.tide_t = 0.0
        self.life: list = []              # what crawled out of the sea (alive or not)
        self.life_t = 0.0
        self.lashes: list[Lash] = []
        self.sweeps: list[Sweep] = []
        self.whirls: list[Whirl] = []
        self.bubbles: list = []           # [x, y, s to the burst, echo?, radius, damage]
        self.waves: list[Wave] = []
        self.husk_runs: list = []         # [generator, s to wait, husk]: the husks' signatures
        self.rec_from = None              # a husk: what it does now echoes from there
        self.ripple: list | None = None   # the dive's: [x, y, s so far, of s]
        self.wave_tell: tuple | None = None   # (x0, y0, angle, length) of the wave coming
        self.swim_flip = 6.0

    # --- Being the first life --------------------------------------------------------------

    def take_damage(self, amount, source, from_angle):
        if self.form == "rising":
            return 0.0
        dealt = super().take_damage(amount, source, from_angle)
        if self.form == 1 and self.hp <= 0:            # (the ages are over: the first life)
            self.hp = 1.0
            self._split()
        return dealt

    def _tile(self, x: float, y: float):
        return self.ctx.world.tile_at(math.floor(x), math.floor(y))

    def holders(self) -> list:
        return self.lashes + self.sweeps

    def _drag(self, h, x: float, y: float) -> None:
        """Pull a held hero toward (x, y), kept inside the caldera, at most
        half a tile a step: one long shove could jump them clean through
        the rim (collision looks only at where they'd land)."""
        x, y = self.clamp_to_lair(x, y, 1.0)
        dx, dy = x - h.x, y - h.y
        d = math.hypot(dx, dy)
        if d > 0.5:
            dx, dy = dx / d * 0.5, dy / d * 0.5
        combat.push(h, self.ctx.world, dx, dy, full=True)

    # --- The split, the flood ----------------------------------------------------------------

    def _split(self) -> None:
        """The giant insect's skin splits: whatever it was doing stops, the
        ages' hazards go, its husk is left, and the caldera floods."""
        ctx = self.ctx
        self.form = "rising"
        self.rise_t = config.FIRST_LIFE_RISE
        self.move, self._gen, self.tell = None, None, None
        self._settle()
        self.lunge, self.flit_to = None, None
        self.moulting = 0.0
        self.rivers = []
        self.echoes, self.runners, self.lobs, self.flashes = [], [], [], []
        if ctx is None:
            return
        self._leave_husk(self.age, ctx)
        self.age = 3
        self.pose = "open"
        self.banner_req = ("THE FIRST LIFE RISES", "the insect's skin splits -- the caldera floods")
        ctx.effects.append(Effect("explosion", self.x, self.y))
        ctx.effects.append(Effect("splash", self.x, self.y, size=4.0))
        ctx.effects.append(Effect("toast", self.x, self.y - self.hit_radius - 2,
                                  label="ITS SKIN SPLITS!"))
        ctx.events.append("boulder")
        self._plan_flood()
        for lx, ly, _ in (self.lair.props.get("lakes", ()) if self.lair is not None else ()):
            ctx.effects.append(Effect("steam", lx, ly, size=4.0))

    def _plan_flood(self) -> None:
        """Which tiles the first sea covers and in what order (from the rim
        in, in fingers), and the rocks standing above it (a jittered grid;
        the lava lakes quenched). Only in a real lair."""
        self.flood, self.sea, self.sea_at, self.orig, self.flood_at = [], [], {}, {}, {}
        self.flooded = self.deep = 0
        lair = self.lair
        if lair is None or not hasattr(self.ctx.world, "set_tile"):
            return
        cx, cy, a, b = self._arena()
        rng = random.Random(self.rng.random())
        sp, jit, (r0, r1) = config.TIDE_ROCKS
        rocks = []
        rows, cols = math.ceil(b / (sp * 0.87)) + 1, math.ceil(a / sp) + 1
        for j in range(-rows, rows + 1):
            for i in range(-cols, cols + 1):
                x = cx + (i + (0.5 if j % 2 else 0.0)) * sp + rng.uniform(-jit, jit)
                y = cy + j * sp * 0.87 + rng.uniform(-jit, jit)
                if ((x - cx) / (a - 3)) ** 2 + ((y - cy) / (b - 3)) ** 2 < 1.0:
                    rocks.append((x, y, rng.uniform(r0, r1)))
        for lx, ly, rr in lair.props.get("lakes", ()):
            rocks.append((lx, ly, rr + 1.6))
        ox, oy = lair.x0, lair.y0
        cells, kinds = [], []
        for j, row in enumerate(lair.rows):
            for i, t in enumerate(row):
                if t in SEA_FLOORS or t is tiles.LAVA:
                    cells.append((ox + i, oy + j))
                    kinds.append(t)
        if not cells:
            return
        P = np.array(cells, dtype=np.float64) + 0.5
        X, Y = P[:, 0], P[:, 1]
        r = np.sqrt(((X - cx) / a) ** 2 + ((Y - cy) / b) ** 2)
        s1, s2, s3 = (rng.uniform(0, _TAU) for _ in range(3))
        noise = 0.5 * np.sin(X * 0.23 + s1) * np.sin(Y * 0.29 + s2) + 0.5 * np.sin((X + Y) * 0.11 + s3)
        h = (1.0 - r) + 0.22 * noise
        rock = np.array([t is tiles.LAVA for t in kinds])
        for x, y, rr in rocks:
            rock |= (X - x) ** 2 + ((Y - y) * 1.1) ** 2 < rr * rr
        order = np.argsort(h, kind="stable")
        for k in order.tolist():
            p = cells[k]
            self.orig[p] = kinds[k]
            self.flood_at[p] = len(self.flood)
            if rock[k]:
                self.flood.append((p, tiles.TIDE_ROCK))
            else:
                self.sea_at[p] = len(self.sea)
                self.sea.append(p)
                self.flood.append((p, tiles.TIDE_SHALLOWS))

    def _set(self, p, tile) -> None:
        """A tile of the flood changes -- not under a husk (the husk puts the
        tide's tile back when it crumbles: `_husk_ground`)."""
        w = self.ctx.world
        if w.tile_at(*p) is not tiles.HUSK:
            w.set_tile(p[0], p[1], tile)

    def _husk_ground(self, p, was):
        """What a crumbling husk leaves at p: what the flood made of it (the
        sea as the tide is now, or a rock), if the flood has come this far."""
        i = self.flood_at.get(p)
        if i is None or i >= self.flooded:
            return was
        if self.flood[i][1] is tiles.TIDE_ROCK:
            return tiles.TIDE_ROCK
        return tiles.TIDE_SEA if self.sea_at[p] < self.deep else tiles.TIDE_SHALLOWS

    def _rise_step(self, ctx, dt: float) -> None:
        """The split: the caldera flooding from the rim in, a slice a step."""
        self.dt = dt
        self.time += dt
        self.rise_t -= dt
        self.play_echoes(ctx, dt)                      # (the old husks go on echoing)
        self._tick_husks(ctx, dt)
        q = 1.0 if self.rise_t <= 0 else 1.0 - self.rise_t / config.FIRST_LIFE_RISE
        self._flood_to(round(len(self.flood) * q))
        if int(self.time * 6) != int((self.time - dt) * 6):
            a, r = self.rng.uniform(0, _TAU), self.rng.uniform(2.0, 6.0)
            ctx.effects.append(Effect("splash", self.x + math.cos(a) * r, self.y + math.sin(a) * r,
                                      size=1.5))
        if self.rise_t <= 0:
            self._become_first_life(ctx)

    def _flood_to(self, n: int) -> None:
        for p, tile in self.flood[self.flooded:n]:
            self._set(p, tile)
        self.flooded = max(self.flooded, n)

    def _become_first_life(self, ctx) -> None:
        self._flood_to(len(self.flood))
        self.form = 2
        self.pose = ""
        self.bspec = config.BOSSES["ancestor_first_life"]
        self.phase = 0
        self.max_hp = round(self.max_hp * config.FIRST_LIFE_HP)
        self.hp = float(self.max_hp)
        self.hit_radius = config.FIRST_LIFE_HIT_RADIUS
        self._rest = 1.5
        self.combo = 0
        self.last_move = None
        self.tide, self.tide_t = "low", config.TIDE[0] * 0.5
        self.life_t = 2.0
        self.banner_req = ("THE FIRST LIFE", "climb onto the rocks when the tide comes in")
        ctx.effects.append(Effect("splash", self.x, self.y, size=6.0))
        ctx.events.append("boulder")

    def _drain(self) -> None:
        """It's beaten: the first sea drains away (the middle first), the
        caldera as it was -- over a few steps, by Pangaea's land
        (systems/pangaea.Land.drain), where there is one."""
        w = self.ctx.world if self.ctx is not None else None
        if w is not None and hasattr(w, "set_tile") and self.orig:
            back = [(p, self.orig[p]) for p, _ in reversed(self.flood)]
            ground = pangaea_land(w) if self.lair is not None else None
            if ground is not None:
                ground.draining += back
            else:
                for p, t in back:
                    if w.tile_at(*p) is not tiles.HUSK:
                        w.set_tile(p[0], p[1], t)
        self.flood, self.sea, self.sea_at, self.orig, self.flood_at = [], [], {}, {}, {}
        self.flooded = self.deep = 0

    # --- Each step -------------------------------------------------------------------------

    def _first_life_step(self, ctx, dt: float) -> None:
        self._tide_step(ctx, dt)
        self._wade(ctx)
        self._evolve(ctx, dt)
        self._run_husk_sigs(dt)
        self._tick_lashes(ctx, dt)
        self._tick_sweeps(ctx, dt)
        self._tick_whirls(ctx, dt)
        self._tick_bubbles(ctx, dt)
        self._tick_waves(ctx, dt)

    def _tide_step(self, ctx, dt: float) -> None:
        low, rise, high, fall, _ = config.TIDE
        self.tide_t -= dt
        n = len(self.sea)
        if self.tide == "rising":
            self._deep_to(round(n * (1.0 - max(0.0, self.tide_t) / rise)))
        elif self.tide == "falling":
            self._deep_to(round(n * max(0.0, self.tide_t) / fall))
        if self.tide_t > 0:
            return
        nxt = {"low": ("rising", rise), "rising": ("high", high), "high": ("falling", fall),
               "falling": ("low", low)}[self.tide]
        self.tide, self.tide_t = nxt
        if self.tide == "rising":
            for h in self.victims(ctx):
                if self.in_arena(h):
                    ctx.effects.append(Effect("toast", h.x, h.y - 2.0, label="THE TIDE COMES IN"))
            ctx.events.append("pulse")

    def _deep_to(self, n: int) -> None:
        """sea[:n] the deep, the rest shallows (only what changed is set)."""
        if n > self.deep:
            for p in self.sea[self.deep:n]:
                self._set(p, tiles.TIDE_SEA)
        elif n < self.deep:
            for p in self.sea[n:self.deep]:
                self._set(p, tiles.TIDE_SHALLOWS)
        self.deep = n

    def _wade(self, ctx) -> None:
        """Heroes in the deep wade it slowly (a roll still carries)."""
        slow = config.TIDE[4]
        w = ctx.world
        for h in ctx.players:
            if h.alive and h.roll_t <= 0 and self.in_arena(h) \
                    and w.tile_at(math.floor(h.x), math.floor(h.y)) is tiles.TIDE_SEA:
                h.slowed(slow, 0.15)

    def _swim(self, dt: float) -> None:
        """It swims round you, fast in the deep: the mammal's gallop, but a
        sea-thing's."""
        t = self.drift_target()
        if t is None:
            return
        deep, shallow, keep, rate = config.FIRST_LIFE_SWIM
        v = deep if self._tile(self.x, self.y) is tiles.TIDE_SEA else shallow
        if self._gallop(t, dt, v, keep, rate, flip=self.swim_flip):
            self.swim_flip = self.rng.uniform(5.0, 8.0)

    def _life_phase(self, phase: int, ctx) -> None:
        label = {1: "THE HUSKS WAKE", 2: "ITS ARMS RISE FROM THE SEA",
                 3: "IT REARS UP"}.get(phase)
        if label:
            ctx.effects.append(Effect("toast", self.x, self.y - self.hit_radius - 3, label=label))
        if phase >= 1:
            self._wake_husks(ctx)

    # --- Signature 1: life evolves -----------------------------------------------------------

    def _evolve(self, ctx, dt: float) -> None:
        every, n, (lo, hi), most, stage = config.LIFE_EVOLVE
        self.life = [e for e in self.life if e.alive]
        for e in list(self.life):
            g = getattr(e, "grow_t", None)
            if g is None:
                continue
            e.grow_t = g - dt
            if e.grow_t <= 0:
                self._grow_up(ctx, e)
        self.life_t -= dt
        if self.life_t > 0 or self.recruit is None:
            return
        self.life_t = every
        heroes = [h for h in self.victims(ctx) if self.in_arena(h)]
        if not heroes:
            return
        came = 0
        for _ in range(min(n, most - len(self.life))):
            h = self.rng.choice(heroes)
            for _ in range(20):
                a, r = self.rng.uniform(0, _TAU), self.rng.uniform(lo, hi)
                x, y = self.clamp_to_lair(h.x + math.cos(a) * r, h.y + math.sin(a) * r, 2.0)
                if self._tile(x, y) in WET or self.lair is None:
                    break
            e = self.recruit(config.LIFE_STAGES[0], x, y)
            if e is None:
                continue
            e.stage, e.grow_t = 0, stage
            self.life.append(e)
            ctx.effects.append(Effect("splash", x, y, size=1.0))
            came += 1
        if came and not getattr(self, "_life_told", False):
            self._life_told = True
            ctx.effects.append(Effect("toast", self.x, self.y - self.hit_radius - 3,
                                      label="LIFE CRAWLS OUT OF THE SEA"))

    def _grow_up(self, ctx, e) -> None:
        """Left alone, it evolves: a blob into a crawler, a crawler into a
        beast of the island."""
        stage = e.stage + 1
        key = (config.LIFE_STAGES[stage] if stage < len(config.LIFE_STAGES)
               else self.rng.choice(config.LIFE_BEASTS))
        e2 = self.recruit(key, e.x, e.y) if self.recruit is not None else None
        e.left = True                     # (it became something else: no kill)
        e.hp = 0.0
        e.last_hit_by = None
        self.life = [x for x in self.life if x is not e]
        if e2 is None:
            return
        e2.stage = stage
        e2.grow_t = config.LIFE_EVOLVE[4] if stage < len(config.LIFE_STAGES) else None
        e2.alert = True
        self.life.append(e2)
        ctx.effects.append(Effect("unveil", e.x, e.y, size=1.2))
        ctx.effects.append(Effect("toast", e.x, e.y - 1.5, label="IT EVOLVES!"))
        ctx.events.append("hex")

    # --- Signature 2: the husks wake as echoes of the ages ----------------------------------

    def _wake_husks(self, ctx) -> None:
        """All three husks stand again (where they lay: one for an age that
        left none rises somewhere), awake for the rest of the fight."""
        every, first = config.HUSK_WAKE
        if any(h.awake for h in self.husks):
            return
        have = {h.age: h for h in self.husks}
        for age in range(3):
            h = have.get(age)
            if h is None:
                x, y = self._random_spot(8.0)
                h = self._new_husk(age, x, y, self.rng.uniform(0, _TAU))
            if h.crumbled or not h.stamped:
                h.crumbled = False
                self._stamp_husk(h, ctx)
            h.awake = True
            h.sig_cd = first + age * every / 3
            ctx.effects.append(Effect("unveil", h.x, h.y, size=2.5))

    def _husk_signature(self, h):
        """An awake husk replays its age's signature from where it lies."""
        heroes = [p for p in self.victims(self.ctx) if self.in_arena(p)]
        if not heroes:
            return
        t = min(heroes, key=lambda p: math.hypot(p.x - h.x, p.y - h.y))
        h.facing = math.atan2(t.y - h.y, t.x - h.x)
        if h.age == 0:
            yield from self._stampede(h, t)
        elif h.age == 1:
            yield from self._roar(h, t)
        else:
            yield from self._swarm(h, t)
        h.pose = ""

    def _run_husk_sigs(self, dt: float) -> None:
        keep = []
        for run in self.husk_runs:
            run[1] -= dt
            alive = True
            while run[1] <= 0:
                self.rec_from = run[2]
                try:
                    w = next(run[0])
                except StopIteration:
                    alive = False
                    break
                finally:
                    self.rec_from = None
                if not w:
                    run[1] = 0.0
                    break
                run[1] += w
            if alive:
                keep.append(run)
            else:
                run[2].lanes, run[2].cone = [], None
        self.husk_runs = keep

    # --- Signature 3: tentacles ------------------------------------------------------------

    def m_tentacles(self):
        n, shown, lo, hi, burst_r, burst_dmg, arc_deg, length, sweep, hold, sq, squeezes = \
            config.TENTACLES
        t = self.target_now()
        if t is None:
            return
        self.pose = "open"
        self.tell = ("tentacles",)
        wait = self.tell_s(shown)
        base = self.rng.uniform(0, _TAU)
        made = []
        for k in range(n):
            a = base + k * _TAU / n + self.rng.uniform(-0.4, 0.4)
            r = self.rng.uniform(lo, hi)
            bx, by = self.clamp_to_lair(t.x + math.cos(a) * r, t.y + math.sin(a) * r, 1.5)
            to = math.atan2(t.y - by, t.x - bx)            # (it sweeps through where you are)
            arc = math.radians(arc_deg) * self.rng.choice((-1, 1))
            made.append(Sweep(bx, by, to - arc / 2, arc, length, wait, sweep, burst_r,
                              self.hurt(burst_dmg), hold, self.hurt(sq), squeezes))
        self.sweeps += made
        self._record("sweeps", wait, dict(arms=[s.params() for s in made]))
        self.ctx.events.append("hex")
        yield 0.6
        self.pose = ""

    def _tick_sweeps(self, ctx, dt: float) -> None:
        for s in self.sweeps:
            s.t += dt
            if not s.up:
                continue
            if not s.burst:
                s.burst = True
                self.area(ctx, "circle", s.bx, s.by, 0.0, s.burst_r, 0.0, s.burst_dmg, record=False)
                ctx.effects.append(Effect("splash", s.bx, s.by, size=s.burst_r))
                ctx.events.append("boulder")
            a = s.angle
            ca, sa = math.cos(a), math.sin(a)
            x1, y1 = s.bx + ca * s.length, s.by + sa * s.length
            if s.t < s.shown + s.sweep:
                holders = self.holders()
                for h in self.victims(ctx):
                    k = id(h)
                    if k in s.caught or not h.hittable or h.roll_t > 0 or not self.in_arena(h) \
                            or _held_by(holders, h):
                        continue
                    if patterns.point_segment_distance(h.x, h.y, s.bx, s.by, x1, y1) <= 0.8 + h.hit_radius:
                        along = min(s.length, max(1.0, (h.x - s.bx) * ca + (h.y - s.by) * sa))
                        s.held[k] = [h, s.hold, s.hold / s.squeezes, s.squeezes, along]
                        s.caught.add(k)
                        ctx.effects.append(Effect("toast", h.x, h.y - 2, label="GRABBED!"))
            for k, v in list(s.held.items()):
                h = v[0]
                if not h.alive or h.roll_t > 0:
                    s.held.pop(k)
                    if h.alive:
                        ctx.effects.append(Effect("toast", h.x, h.y - 2, label="PULLED FREE!"))
                    continue
                self._drag(h, s.bx + ca * v[4], s.by + sa * v[4])
                h.slowed(0.0, 0.1)
                v[1] -= dt
                v[2] -= dt
                if v[2] <= 0 and v[3] > 0:
                    v[3] -= 1
                    v[2] += s.hold / s.squeezes
                    if h.hittable:
                        _numbered_hit(h, s.squeeze, self, a, ctx)
                    ctx.events.append("hit")
                if v[1] <= 0:
                    s.held.pop(k)
        self.sweeps = [s for s in self.sweeps if not s.over]

    # --- Signature 4: the tidal wave -------------------------------------------------------

    def m_wave(self):
        rear, before, past, speed, dmg, carry = config.TIDAL_WAVE
        t = self.target_now()
        if t is None:
            return
        self.planted = True
        self.pose = "open"
        self.tell = ("wave",)
        a = self.angle_to(t.x, t.y)                       # (rolling from it through you)
        self.facing = a
        x0, y0 = t.x - math.cos(a) * before, t.y - math.sin(a) * before
        self.wave_tell = (x0, y0, a, before + past)
        self.ctx.effects.append(Effect("toast", self.x, self.y - self.hit_radius - 3,
                                       label="A GREAT WAVE!"))
        wait = self.tell_s(rear)
        yield wait
        self.wave_tell = None
        w = Wave(x0, y0, a, before + past, speed, self.hurt(dmg), carry)
        self.waves.append(w)
        self._record("wave", wait, w.params())
        self.ctx.events.append("swing")
        yield 0.5

    def _tick_waves(self, ctx, dt: float) -> None:
        for w in self.waves:
            w.done += w.speed * dt
            ca, sa = math.cos(w.angle), math.sin(w.angle)
            for h in self.victims(ctx):
                k = id(h)
                if k in w.passed or not self.in_arena(h):
                    continue
                if k in w.carried:
                    w.carried[k] -= dt
                    if h.roll_t > 0 or w.carried[k] <= 0:
                        w.passed.add(k)
                        w.carried.pop(k)
                        continue
                    combat.push(h, ctx.world, ca * w.speed * dt, sa * w.speed * dt, full=True)
                    h.slowed(0.0, 0.1)
                    continue
                along = (h.x - w.x0) * ca + (h.y - w.y0) * sa
                if along < w.done - 1.5:                 # (it went past: rolled through)
                    w.passed.add(k)
                elif along <= w.done + h.hit_radius + 0.3:
                    if h.roll_t > 0 or combat.skims(h) or not h.hittable:
                        w.passed.add(k)
                        continue
                    _numbered_hit(h, w.damage * combat.ground_cut(h), self, w.angle, ctx)
                    w.carried[k] = w.carry
                    ctx.effects.append(Effect("splash", h.x, h.y, size=1.5))
        self.waves = [w for w in self.waves if w.done < w.length]

    # --- Its moves: dive and surface -------------------------------------------------------

    def m_dive(self):
        sink, ripple, follow, radius, dmg, n = config.DIVE
        t = self.target_now()
        if t is None:
            return
        self.busy = True
        self.pose = "dive"
        self.tell = ("dive",)
        self.ctx.effects.append(Effect("splash", self.x, self.y, size=self.hit_radius))
        yield self.tell_s(sink)
        self.submerged = True
        wait = self.tell_s(ripple)
        fol = follow * wait / ripple
        x, y = self.clamp_to_lair(t.x, t.y, self.hit_radius)
        self.ripple = [x, y, 0.0, wait]
        while self.ripple[2] < wait:
            if self.ripple[2] < fol and t.alive:
                self.ripple[0], self.ripple[1] = self.clamp_to_lair(t.x, t.y, self.hit_radius)
            self.ripple[2] += self.dt
            self._glide(self.ripple[0], self.ripple[1], 40.0, self.dt)   # (unseen, under you)
            yield 0
        x, y = self.ripple[:2]
        self.ripple = None
        self.x, self.y = x, y
        self.submerged = False
        self.pose = "open"
        self.area(self.ctx, "circle", x, y, 0.0, radius, 0.0, self.hurt(dmg), 2.0, tell=wait)
        # (a ring of spray from the burst's rim outward: the burst is what
        # hits whoever it came up under; they echo together, as one)
        shell = config.PANGAEA_SHOTS["spray"]
        turn = self.rng.uniform(0, _TAU)
        shots = []
        for k in range(n):
            a = turn + k * _TAU / n
            sx, sy = x + math.cos(a) * radius, y + math.sin(a) * radius
            p = patterns.shoot(self, sx, sy, a, shell, self.ctx.projectiles)
            shots.append((sx, sy, a, "spray", p.damage, None))
        self.ctx.events.append(shell.sound)
        self._record("shots", wait, dict(shots=shots))
        self.ctx.effects.append(Effect("splash", x, y, size=radius))
        self.ctx.events.append("boulder")
        yield 0.5

    # --- Whirlpool --------------------------------------------------------------------------

    def m_whirlpool(self):
        shown, spin, radius, swirl, pull, core, dmg, every = config.WHIRLPOOL
        t = self.target_now()
        if t is None:
            return
        self.pose = "open"
        self.tell = ("whirlpool",)
        wait = self.tell_s(shown)
        x, y = self.clamp_to_lair(*self.lead(t, t.x, t.y, secs=wait), 2.0)
        w = Whirl(x, y, wait, spin, radius, swirl, pull, core, self.hurt(dmg), every,
                  self.rng.choice((-1, 1)))
        self.whirls.append(w)
        self._record("whirl", wait, w.params())
        self.ctx.events.append("pulse")
        yield 0.6
        self.pose = ""

    def _tick_whirls(self, ctx, dt: float) -> None:
        for w in self.whirls:
            w.t += dt
            for k in list(w.cds):
                w.cds[k] -= dt
            if not w.spinning:
                continue
            for h in self.victims(ctx):
                if not self.in_arena(h) or h.roll_t > 0:
                    continue
                dx, dy = h.x - w.x, h.y - w.y
                d = math.hypot(dx, dy)
                if d > w.radius + h.hit_radius:
                    continue
                if d > 1e-6:
                    ux, uy = dx / d, dy / d
                    mx = (-uy * w.turn * w.swirl - ux * w.pull) * dt
                    my = (ux * w.turn * w.swirl - uy * w.pull) * dt
                    if d < w.pull * dt:
                        mx, my = -dx, -dy
                    combat.push(h, ctx.world, mx, my)
                if d <= w.core + h.hit_radius and h.hittable and w.cds.get(id(h), 0.0) <= 0:
                    w.cds[id(h)] = w.every
                    _numbered_hit(h, w.damage, self, math.atan2(dy, dx), ctx)
        self.whirls = [w for w in self.whirls if w.t < w.shown + w.spin]

    # --- Boiling bubbles --------------------------------------------------------------------

    def m_bubbles(self):
        chains, per, off, step, shown, gap, radius, dmg = config.BUBBLES
        t = self.target_now()
        if t is None:
            return
        self.pose = "open"
        self.tell = ("bubbles",)
        wait = self.tell_s(shown)
        px, py = self.lead(t, t.x, t.y, secs=wait)
        base = self.rng.uniform(0, _TAU)
        spots = []
        for c in range(chains):
            a = base + c * _TAU / chains + self.rng.uniform(-0.3, 0.3)
            for k in range(per):
                d = off - k * step                       # (from off to the side, through you)
                x, y = self.clamp_to_lair(px + math.cos(a) * d, py + math.sin(a) * d, 1.0)
                spots.append((x, y, k * gap))
        damage = self.hurt(dmg)
        for x, y, later in spots:
            self.bubbles.append([x, y, wait + later, False, radius, damage])
        self._record("bubbles", wait, dict(spots=spots, radius=radius, damage=damage))
        self.ctx.events.append("fizzle")
        yield 0.5
        self.pose = ""

    def _tick_bubbles(self, ctx, dt: float) -> None:
        keep = []
        for b in self.bubbles:
            b[2] -= dt
            if b[2] > 0:
                keep.append(b)
                continue
            self.area(ctx, "circle", b[0], b[1], 0.0, b[4], 0.0, b[5], record=False)
            ctx.effects.append(Effect("splash", b[0], b[1], size=b[4]))
            ctx.events.append("fizzle")
        self.bubbles = keep

    # --- Arm lash --------------------------------------------------------------------------

    def m_lash(self):
        n, spread, length, shown, speed, width, drag, keep, bite = config.ARM_LASH
        t = self.target_now()
        if t is None:
            return
        self.planted = True
        self.pose = "open"
        self.tell = ("lash",)
        a = self.aim(t, self.x, self.y, speed)
        self.facing = a
        wait = self.tell_s(shown)
        made = []
        for ang in self._fan_angles(a, n, spread):
            x0 = self.x + math.cos(ang) * self.hit_radius * 0.7
            y0 = self.y + math.sin(ang) * self.hit_radius * 0.7
            made.append(Lash(x0, y0, ang, length, wait, speed, width, drag, keep, self.hurt(bite)))
        self.lashes += made
        self._record("lashes", wait, dict(arms=[m.params() for m in made]))
        yield wait
        self.ctx.events.append("swing")
        took = 0.0
        while took < 2.0 and any(not m.done for m in made):
            took += self.dt
            yield 0
        self.planted = False
        yield 0.3

    def _tick_lashes(self, ctx, dt: float) -> None:
        for m in self.lashes:
            m.t += dt
            if m.t < m.shown or m.done:
                continue
            if m.out:
                m.len = min(m.length, m.len + m.speed * dt)
                x, y = m.tip()
                holders = self.holders()
                for h in self.victims(ctx):
                    if h.hittable and h.roll_t <= 0 and self.in_arena(h) and not _held_by(holders, h) \
                            and math.hypot(h.x - x, h.y - y) <= m.width + h.hit_radius:
                        m.grip = h
                        m.out = False
                        ctx.effects.append(Effect("toast", h.x, h.y - 2, label="CAUGHT!"))
                        break
                if m.len >= m.length:
                    m.out = False
                continue
            h = m.grip
            if h is not None and (not h.alive or h.roll_t > 0):
                m.grip = None
                if h.alive:
                    ctx.effects.append(Effect("toast", h.x, h.y - 2, label="PULLED FREE!"))
                h = None
            if h is None:
                m.len -= m.speed * 1.5 * dt
                m.done = m.len <= 0
                continue
            m.len = max(m.keep, m.len - m.drag * dt)
            self._drag(h, *m.tip())
            h.slowed(0.0, 0.1)
            if m.len <= m.keep:                          # (in reach of its mouth: bitten)
                if h.hittable:
                    _numbered_hit(h, m.bite, self, m.angle + math.pi, ctx)
                combat.push(h, ctx.world, math.cos(m.angle) * 2.5, math.sin(m.angle) * 2.5)
                ctx.effects.append(Effect("toast", h.x, h.y - 2, label="BITTEN!"))
                ctx.events.append("hit")
                m.grip = None
                m.done = True
        self.lashes = [m for m in self.lashes if not m.done]

    # --- Its echoes --------------------------------------------------------------------------

    def _play(self, ctx, e) -> None:
        d = e.data
        if e.kind == "whirl":
            self.whirls.append(Whirl(**d, echo=True))
        elif e.kind == "bubbles":
            for x, y, later in d["spots"]:
                self.bubbles.append([x, y, later, True, d["radius"], d["damage"]])
        elif e.kind == "lashes":
            self.lashes += [Lash(**p, echo=True) for p in d["arms"]]
        elif e.kind == "sweeps":
            self.sweeps += [Sweep(**p, echo=True) for p in d["arms"]]
        elif e.kind == "wave":
            self.waves.append(Wave(**d, echo=True))
        else:
            super()._play(ctx, e)

    def _first_life_gone(self, ctx) -> None:
        """It's beaten: what crawled out of the sea goes back, its arms and
        currents are gone, and the sea drains."""
        for e in self.life:
            if e.alive:
                e.left = True
                e.hp = 0.0
                e.last_hit_by = None
        self.life = []
        self.lashes, self.sweeps, self.whirls, self.bubbles, self.waves = [], [], [], [], []
        self.husk_runs = []
        self.ripple = self.wave_tell = None
        self.submerged = False
        self._drain()
