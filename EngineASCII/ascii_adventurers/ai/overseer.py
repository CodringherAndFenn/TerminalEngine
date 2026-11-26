"""
ai/overseer.py -- Panopticon's boss, form 1: THE OVERSEER, the eye (M32.4,
design/OCEAN.md 39, 39.1, 39.3). The tower's mind: a great eye-machine
ringed by camera arms, hanging from a ring rail in the hall of cells'
ceiling, running the room round you. The blast doors open when the seventh
eye goes dark.

Always moving: it slides round its rail (OVERSEER_RAIL), reversing now
and then, turning to watch you. The shock drop brings it down low --
planted, and easier to hit (x OVERSEER_RAIL[3]) -- with a clear tell.

Four phases (12,000 HP, 3,000 a phase), a signature joining in each and
keeping on (all of the fight, not moves):
  1. THE GAZE: its searchlight swings across you. While it sees you (the
     pillars hide you) the fight's own alert fills; SEARCH makes its moves
     faster, LOCKDOWN faster still and opens every cell at once. Out of its
     sight it cools. The alert shows under its health bar.
  2. THE CELLS: cell doors round the hall open and the watch comes out
     (sentry drones, riot robots). And a move, the cell: laser bars close
     round you unless you roll out before they shut.
  3. THE LASER GRID: patterns of beams across the floor, like the city's --
     lines sweeping across the hall, a turning cross, a closing box -- each
     shown first.
  4. THE RECORDINGS: it has recorded you. Copies of you walk your path of
     a few seconds ago, firing your own shots back; fragile.
Its moves (every phase): the laser sweep (an arc shown, then its beam
sweeps it, walls and pillars stop it), the missile salvo (marked spots
round you, struck in a quick chain), the shock drop (low and planted: an
electric ring, then arcs to the hall's four pylons) and the floor scan
(lit squares struck from above; the dark ones are safe).

At 0 the eye tears out of the ceiling and builds itself a body out of the
hall: form 2, the walking city (M32.5, ai/walking_city.WalkingCity, a
mix-in: one body, two forms). Its pictures: render/panopticon_art.py; the
rail, the gaze and the rest: render/overseer.py (form 2:
render/walking_city.py).
"""

from __future__ import annotations

import math
import random
from collections import deque

from .. import config
from ..entities.effects import Effect
from ..specs import EnemySpec
from ..systems import combat, patterns
from ..systems.alert import CALM, LOCKDOWN, NAMES, SEARCH
from ..systems.raycast import first_hit
from ..world import tiles
from .bosses import Boss
from .creatures import _numbered_hit
from .panopticon import _beam_end, _raise_ring, _ring_tiles
from .pangaea import _wrap
from .plains import PlainsCreature
from .walking_city import SIGNATURES as CITY_SIGNATURES
from .walking_city import SIGNATURE_LINES as CITY_LINES
from .walking_city import WalkingCity

_TAU = 2.0 * math.pi
SIGNATURES = ("THE GAZE", "THE CELLS", "THE LASER GRID", "THE RECORDINGS")
SIGNATURE_LINES = ("hide from its searchlight", "the watch comes out of the cells",
                   "read the beams and slip through", "it has recorded you")


def _seg_dist(x, y, ax, ay, bx, by) -> float:
    dx, dy = bx - ax, by - ay
    ll = dx * dx + dy * dy
    f = 0.0 if ll <= 0 else max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / ll))
    return math.hypot(x - ax - dx * f, y - ay - dy * f)


class Recording(PlainsCreature):
    """A copy of a hero (M32.4, THE RECORDINGS): it walks the hero's path of
    OVERSEER_REC[1] s ago, from where they stood then, firing their shots
    again (x OVERSEER_REC[3]; hurting heroes). One or two hits shatter it;
    played out, it fizzles (no kill)."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.path: list[tuple[float, float, float, bool]] = []   # (t, x, y, facing left)
        self.shots: list[tuple[float, float, object, float]] = []  # (t, angle, shell, damage)
        self.t = 0.0
        self.span = config.OVERSEER_REC[1]
        self.of = None                    # the hero it's a copy of
        self.sprite = "wizard"
        self.scale = 3
        self.look = None
        self.left_side = False
        self.shooter = None               # who its shots belong to (the eye: they spare it)

    def setup(self, hero, path, shots, shooter) -> None:
        self.of = hero
        self.path, self.shots = path, shots
        self.span = path[-1][0] if path else 0.0
        self.sprite = hero.spec.sprite
        from ..render.characters import body_scale
        self.scale = body_scale(hero)
        self.look = getattr(hero, "look", None)
        self.shooter = shooter
        if path:
            self.x, self.y = path[0][1], path[0][2]

    def think(self, ctx, dt: float) -> None:
        self.t += dt
        if self.t >= self.span or self.of is None:
            self.left = True                      # (played out: it fizzles, no kill)
            self.hp = 0.0
            return
        p = self.path
        k = 0
        while k + 1 < len(p) and p[k + 1][0] <= self.t:
            k += 1
        if k + 1 < len(p):
            t0, x0, y0, l0 = p[k]
            t1, x1, y1, _ = p[k + 1]
            f = 0.0 if t1 <= t0 else (self.t - t0) / (t1 - t0)
            nx, ny = x0 + (x1 - x0) * f, y0 + (y1 - y0) * f
        else:
            _, nx, ny, l0 = p[-1]
        self._moved = math.hypot(nx - self.x, ny - self.y)
        self.walked += self._moved
        self.x, self.y, self.left_side = nx, ny, l0
        mult = config.OVERSEER_REC[3]
        while self.shots and self.shots[0][0] <= self.t:
            _, angle, shell, damage = self.shots.pop(0)
            q = patterns.shoot(self.shooter or self, self.x, self.y, angle, shell, ctx.projectiles)
            q.damage = damage * mult
            q.seek_turn = 0.0
            q.recorded = True
            q.hit.add(id(self))                   # (never the copy that fired it)

    def facing_left(self) -> bool:
        return self.left_side


class Overseer(WalkingCity, Boss):
    """The Overseer: form 1 here, form 2 (the walking city) in
    ai/walking_city.py (see the modules' docstrings)."""

    def __init__(self, spec: EnemySpec, x: float, y: float, rng: random.Random,
                 spawn_id=None) -> None:
        super().__init__(spec, x, y, rng, spawn_id, hit_radius=2.4)
        self.rail_a = rng.uniform(0.0, _TAU)
        self.rail_dir = rng.choice((-1, 1))
        self.rail_t = 0.0
        self.low = 0.0                    # 0 up on its rail, 1 brought down low
        self.planted = False
        # The gaze and the fight's alert.
        self.gaze_a = 0.0
        self.meter = 0.0                  # the fight's alert, 0-100 (not the city's)
        self.real_t = 0.0                 # (its unhasted clock: the recordings' time)
        self.quiet = 0.0
        self.lock_t = 0.0
        self.level = CALM
        self.seeing = None
        # The cells.
        self.cell_t = config.OVERSEER_CELLS[0] * 0.5
        self.adds: list = []
        self.lock: tuple | None = None    # the cell move's ring: (cx, cy, s left shown)
        # The laser grid: [kind, t (from -tell), angle] or None between patterns.
        self.grid: list | None = None
        self.grid_gap = 1.0
        self.burns: dict[int, float] = {}
        # The recordings.
        self.tracks: dict[int, deque] = {}
        self.fired: dict[int, deque] = {}
        self.seen_shots: set[int] = set()
        self.rec_t = config.OVERSEER_REC[0] * 0.5
        self.copies: list = []
        # What its moves show (render/overseer.py).
        self.sweep: tuple | None = None   # (a0, a1, f: -1 shown, 0..1 sweeping, beam length)
        self.missiles: list[list] = []    # [x, y, s left]
        self.ring: float | None = None    # the drop's electric ring's radius
        self.ring_hit: set[int] = set()
        self.arcs = 0.0                   # s left of the arcs to the pylons
        self.scan: tuple | None = None    # (squares lit, s shown, struck?)
        self.banner_req: tuple | None = None
        self.combo_haste = 1.0
        self._init_city()                 # (M32.5: form 2)

    # --- Being the Overseer --------------------------------------------------------------

    @property
    def hittable(self) -> bool:
        return Boss.hittable.fget(self) and self.form != "tearing"

    @property
    def bar_label(self) -> str:
        return "The Walking City" if self.form == 2 else "The Overseer"

    def bars(self) -> list[tuple[str, float]]:
        """Under its health bar: the fight's alert, with its level (form 2:
        its armour plates, and from the second phase its shield)."""
        from .. import palette
        if self.form == "tearing":
            return []
        if self.form == 2:
            n = len(self.plates)
            have = sum(p.hp for p in self.plates if p is not None)
            parts = [(f"ARMOUR {self.plated}/{n}", have / max(1.0, n * self.plate_hp()),
                      palette.WALKER_ARMOUR)]
            if self.phase >= 1:
                parts.append(("SHIELD" if self.cables else "SHIELD DOWN", 1.0 if self.cables else 0.0,
                              palette.WALKER_SHIELD))
            return parts
        return [(f"ALERT -- {NAMES[self.level]}", self.meter / 100.0, palette.ALERT_BAR[self.level])]

    def hurt(self, base: float) -> float:
        return base * self.damage_mult * (self.strength() if self.form == 2 else 1.0)

    def sprite_now(self) -> str:
        if self.form == 2:
            return "walking_city_beam" if self.pose == "beam" else "walking_city"
        return "overseer_low" if self.low > 0.5 else "overseer"

    def take_damage(self, amount, source, from_angle):
        if self.form == "tearing" or not self.alive:
            return 0.0
        if self.form == 2:                        # (M32.5: its plates, its shield, its open eye)
            body, plate = self._city_takes(amount, source, from_angle)
            if plate is not None:                 # (a plate on that side takes it all)
                return self._hit_plate(plate, amount, source)
            amount = body
        elif self.low > 0.5:
            amount *= config.OVERSEER_RAIL[3]     # (down low: easier to hit)
        dealt = super().take_damage(amount, source, from_angle)
        if self.form == 1 and self.hp <= 0:       # (the eye tears free: the walking city)
            self.hp = 1.0
            self._tear()
        return dealt

    def shove_heroes(self, extra: float = 0.3) -> None:
        if self.ctx is None:
            return
        if self.form == 2 or self.low > 0.5:      # (it hangs over you: only low does it push)
            super().shove_heroes(extra)

    def arena(self) -> tuple[float, float, float, float]:
        lair = self.lair
        if lair is not None:
            return lair.cx, lair.cy, float(lair.radii[0]), float(lair.radii[1])
        return self.home[0], self.home[1], 30.0, 22.0

    def rail_point(self, a: float) -> tuple[float, float]:
        cx, cy, ra, rb = self.arena()
        k = config.OVERSEER_RAIL[0]
        return cx + math.cos(a) * ra * k, cy + math.sin(a) * rb * k

    def pylons(self) -> list[tuple[float, float]]:
        """The hall's four live pylons (without a lair: four spots round it)."""
        got = self.lair.props.get("pylons") if self.lair is not None else None
        if got:
            return list(got)
        cx, cy, ra, rb = self.arena()
        return [(cx + math.cos(q * _TAU / 4 + 0.78) * ra * 0.86,
                 cy + math.sin(q * _TAU / 4 + 0.78) * rb * 0.86) for q in range(4)]

    def inside(self, x: float, y: float, shrink: float = 0.0) -> bool:
        cx, cy, ra, rb = self.arena()
        return ((x - cx) / max(1.0, ra - shrink)) ** 2 + ((y - cy) / max(1.0, rb - shrink)) ** 2 < 1.0

    def chord(self, x: float, y: float, ux: float, uy: float):
        """Where the line through (x, y) along (ux, uy) crosses the hall:
        (x0, y0, x1, y1), or None if it misses."""
        cx, cy, ra, rb = self.arena()
        dx, dy = x - cx, y - cy
        qa = (ux / ra) ** 2 + (uy / rb) ** 2
        qb = 2 * (dx * ux / ra ** 2 + dy * uy / rb ** 2)
        qc = (dx / ra) ** 2 + (dy / rb) ** 2 - 1.0
        disc = qb * qb - 4 * qa * qc
        if disc <= 0 or qa <= 0:
            return None
        r = math.sqrt(disc)
        s0, s1 = (-qb - r) / (2 * qa), (-qb + r) / (2 * qa)
        return x + ux * s0, y + uy * s0, x + ux * s1, y + uy * s1

    def _in_hall(self, h) -> bool:
        return self.lair.inside(h.x, h.y) if self.lair is not None else self.inside(h.x, h.y)

    # --- Its turn ------------------------------------------------------------------------

    @property
    def gaze_haste(self) -> float:
        g = config.OVERSEER_GAZE
        return g[9] if self.level == LOCKDOWN else g[8] if self.level == SEARCH else 1.0

    def think(self, ctx, dt: float) -> None:
        self.ctx = ctx
        self.real_t += dt
        if self.form == "tearing":                       # (M32.5: the walls coming down)
            self._tear_step(ctx, dt)
            return
        if self.form == 2:                               # (the walking city)
            self._city_step(ctx, dt)
            super().think(ctx, dt)
            return
        self._record(ctx, dt)
        fast = dt * self.gaze_haste                     # (the gaze's levels: everything faster)
        if not self.planted:
            self._slide(fast)
        self._gaze(ctx, dt)
        if self.phase >= 1:
            self._cells(ctx, fast)
        if self.phase >= 2:
            self._grid(ctx, fast)
        if self.phase >= 3:
            self._recordings(ctx, fast)
        self._tick_missiles(ctx, fast)
        self._tick_ring(ctx, fast)
        if self.lock is not None:
            self._tick_lock(ctx, fast)
        super().think(ctx, fast)

    def _slide(self, dt: float) -> None:
        """Round its rail, turning to watch you."""
        cx, cy, ra, rb = self.arena()
        k = config.OVERSEER_RAIL[0]
        r = max(4.0, (ra + rb) / 2 * k)
        self.rail_t += dt
        if self.rail_t >= config.OVERSEER_RAIL[2]:
            self.rail_t = self.rng.uniform(-2.0, 2.0)
            self.rail_dir = -self.rail_dir
        self.rail_a = (self.rail_a + self.rail_dir * config.OVERSEER_RAIL[1] / r * dt) % _TAU
        self.x, self.y = self.rail_point(self.rail_a)
        t = self.drift_target()
        if t is not None:
            self.facing = math.atan2(t.y - self.y, t.x - self.x)

    def on_phase(self, phase: int, ctx) -> None:
        """A signature joins (and keeps on): its name across the screen."""
        names, lines = (CITY_SIGNATURES, CITY_LINES) if self.form == 2 else (SIGNATURES, SIGNATURE_LINES)
        if 0 < phase < len(names):
            self.banner_req = (names[phase], lines[phase])
            ctx.effects.append(Effect("toast", self.x, self.y - 4.0, label=names[phase]))
            ctx.events.append("whistle")
        if self.form == 2:
            if phase == 2:
                self.eye_t = 0.0                         # (the eyes open now)
            elif phase == 3:
                self.city_t = 1.0                        # (the city answers)

    # --- 1. The gaze ---------------------------------------------------------------------

    def _gaze(self, ctx, dt: float) -> None:
        cone, reach, sweep, period, fill, quiet, drain, search, _, _, cells, hold = config.OVERSEER_GAZE
        t = self.drift_target()
        if t is not None:
            self.gaze_a = math.atan2(t.y - self.y, t.x - self.x) + math.radians(sweep) * math.sin(
                _TAU * self.time / period)
        half = math.radians(cone) / 2
        self.seeing = None
        for h in ctx.players:
            if not h.alive or not self._in_hall(h):
                continue
            d = math.hypot(h.x - self.x, h.y - self.y)
            if d > reach or abs(_wrap(math.atan2(h.y - self.y, h.x - self.x) - self.gaze_a)) > half:
                continue
            if first_hit(ctx.world.tile_at, self.x, self.y, h.x, h.y) is None:
                self.seeing = h
                break
        if self.seeing is not None:
            self.meter = min(100.0, self.meter + fill * dt)
            self.quiet = 0.0
        else:
            self.quiet += dt
        if self.lock_t > 0:
            self.lock_t = max(0.0, self.lock_t - dt)
            self.meter = 100.0
        elif self.quiet >= quiet:
            self.meter = max(0.0, self.meter - drain * dt)
        was = self.level
        self.level = LOCKDOWN if self.meter >= 100.0 else SEARCH if self.meter >= search else CALM
        if self.level == LOCKDOWN and was != LOCKDOWN:
            self.lock_t = hold
            ctx.effects.append(Effect("toast", self.x, self.y - 4.0, label="LOCKDOWN!"))
            ctx.events.append("whistle")
            self._open_cells(ctx, cells)          # (every cell at once)

    # --- 2. The cells --------------------------------------------------------------------

    def _cells(self, ctx, dt: float) -> None:
        self.cell_t -= dt
        if self.cell_t > 0:
            return
        self.cell_t = config.OVERSEER_CELLS[0]
        self._open_cells(ctx, config.OVERSEER_CELLS[1])

    def _open_cells(self, ctx, n: int) -> None:
        """`n` cell doors round the hall open and the watch comes out (not
        while OVERSEER_CELLS[2] are out)."""
        self.adds = [e for e in self.adds if e.alive]
        room = config.OVERSEER_CELLS[2] - len(self.adds)
        if self.recruit is None or room <= 0:
            return
        cx, cy, ra, rb = self.arena()
        keys = config.OVERSEER_CELL_WATCH
        base = self.rng.uniform(0.0, _TAU)
        for k in range(min(n, room)):
            a = base + k * _TAU / max(1, n) + self.rng.uniform(-0.2, 0.2)
            x, y = cx + math.cos(a) * (ra - 2.5), cy + math.sin(a) * (rb - 2.5)
            e = self.recruit(keys[k % len(keys)], x, y)
            if e is None:
                continue
            e.alert = True
            if self.drift_target() is not None and hasattr(e, "called_to"):
                e.called_to(self.drift_target())
            self.adds.append(e)
            ctx.effects.append(Effect("spark_burst", x, y, size=1.6))
        ctx.events.append("break")

    def m_cell(self):
        """Laser bars close round you: the ring shows OVERSEER_CELLS[4] s
        (roll out), then shuts for [5] s."""
        t = self.target_now()
        if t is None:
            return
        cx, cy = math.floor(t.x) + 0.5, math.floor(t.y) + 0.5
        self.lock = (cx, cy, self.tell_s(config.OVERSEER_CELLS[4]))
        self.ctx.events.append("hex")
        yield self.lock[2] + 0.05

    def _tick_lock(self, ctx, dt: float) -> None:
        cx, cy, left = self.lock
        left -= dt
        if left > 0:
            self.lock = (cx, cy, left)
            return
        self.lock = None
        n = config.OVERSEER_CELLS[3]
        ox, oy = math.floor(cx), math.floor(cy)
        from ..systems.collision import hull_hits_solid
        for h in ctx.players:                     # (still in the cell: set in its middle, if it's clear)
            if h.alive and max(abs(math.floor(h.x) - ox), abs(math.floor(h.y) - oy)) < n \
                    and not hull_hits_solid(ctx.world, ox + 0.5, oy + 0.5, 0.0, h.half, h.half):
                h.x, h.y = ox + 0.5, oy + 0.5
        cells = _ring_tiles(ctx.world, cx, cy, n,
                            [a for a in ctx.actors if a is not self])   # (never on anyone)
        _raise_ring(ctx, cells, tiles.CELL_BARS, config.OVERSEER_CELLS[5])
        ctx.events.append("zap")

    # --- 3. The laser grid -------------------------------------------------------------

    def _grid(self, ctx, dt: float) -> None:
        dur, tell, gap = config.OVERSEER_GRID[0], config.OVERSEER_GRID[1], config.OVERSEER_GRID[2]
        if self.grid is None:
            self.grid_gap -= dt
            if self.grid_gap <= 0:
                kind = self.rng.choice(("sweep", "cross", "box"))
                self.grid = [kind, -tell, self.rng.uniform(0.0, math.pi)]
                ctx.events.append("hex")
            return
        self.grid[1] += dt
        if self.grid[1] >= dur:
            self.grid, self.grid_gap = None, gap
            return
        if self.grid[1] < 0:
            return
        burn, every = config.OVERSEER_GRID[3], config.OVERSEER_GRID[4]
        beams = self.grid_beams()
        for h in ctx.players:
            if not h.alive or not h.hittable:
                continue
            if any(_seg_dist(h.x, h.y, *b) < 0.45 + h.hit_radius for b in beams):
                left = self.burns.get(id(h), 0.0) - dt
                if left <= 0:
                    left = every
                    _numbered_hit(h, self.hurt(burn), self, None, ctx)
                    ctx.events.append("fizzle")
                self.burns[id(h)] = left

    def grid_beams(self) -> list[tuple[float, float, float, float]]:
        """The grid's beams now (shown or on): segments across the hall."""
        if self.grid is None:
            return []
        kind, t, a = self.grid
        t = max(0.0, t)
        cx, cy, ra, rb = self.arena()
        r = (ra + rb) / 2
        out = []

        def line(px, py, ang):
            c = self.chord(px, py, math.cos(ang), math.sin(ang))
            if c is not None:
                out.append(c)

        if kind == "sweep":                        # (three lines crossing the hall and back)
            cross = config.OVERSEER_GRID[6]
            s = math.sin(_TAU * t / (2 * cross)) * r * 0.85
            ux, uy = math.cos(a), math.sin(a)
            for k in (-1, 0, 1):
                off = s + k * r * 0.55
                if abs(off) < r:
                    line(cx + ux * off, cy + uy * off, a + math.pi / 2)
        elif kind == "cross":                      # (a cross through the middle, turning)
            b = a + config.OVERSEER_GRID[5] * t
            line(cx, cy, b)
            line(cx, cy, b + math.pi / 2)
        else:                                      # (a box closing on the middle and opening)
            dur = config.OVERSEER_GRID[0]
            hw = r * (0.22 + 0.62 * abs(math.cos(math.pi * t / dur)))
            ux, uy = math.cos(a), math.sin(a)
            vx, vy = -uy, ux
            for s in (-1, 1):
                line(cx + ux * hw * s, cy + uy * hw * s, a + math.pi / 2)
                line(cx + vx * hw * s, cy + vy * hw * s, a)
        return out

    # --- 4. The recordings -------------------------------------------------------------

    def _record(self, ctx, dt: float) -> None:
        """Where each hero in the hall has been, and what they've shot."""
        span = config.OVERSEER_REC[1]
        now = self.real_t
        for h in ctx.players:
            if not h.alive or not self._in_hall(h):
                continue
            tr = self.tracks.setdefault(id(h), deque())
            if not tr or now - tr[-1][0] >= 0.1:
                tr.append((now, h.x, h.y, h.facing_left))
            while tr and now - tr[0][0] > span + 0.2:
                tr.popleft()
            fd = self.fired.setdefault(id(h), deque())
            while fd and now - fd[0][0] > span + 0.2:
                fd.popleft()
        if self.phase < 3:
            return
        live = set()
        heroes = {id(h): h for h in ctx.players}
        for p in ctx.projectiles:
            live.add(id(p))
            if id(p) in self.seen_shots:
                continue
            self.seen_shots.add(id(p))
            o = p.owner
            if id(o) in heroes and p.spec.speed > 0 and not p.spec.lob and not p.spec.returns \
                    and not p.spec.chain:
                self.fired.setdefault(id(o), deque()).append((now, p.angle, p.spec, p.damage))
        self.seen_shots &= live

    def _recordings(self, ctx, dt: float) -> None:
        self.copies = [c for c in self.copies if c.alive]
        self.rec_t -= dt
        if self.rec_t > 0 or self.recruit is None:
            return
        self.rec_t = config.OVERSEER_REC[0]
        span, most, cap = config.OVERSEER_REC[1], config.OVERSEER_REC[2], config.OVERSEER_REC[4]
        for h in ctx.players:
            if not h.alive or not self._in_hall(h):
                continue
            tr = self.tracks.get(id(h))
            if not tr or tr[-1][0] - tr[0][0] < span * 0.8:
                continue
            if sum(1 for c in self.copies if c.of is h) >= most:
                continue
            t0 = tr[0][0]
            path = [(t - t0, x, y, left) for t, x, y, left in tr]
            shots = [(t - t0, a, shell, dmg) for t, a, shell, dmg in self.fired.get(id(h), ())
                     if t >= t0][:cap]
            c = self.recruit("recording", path[0][1], path[0][2])
            if c is None:
                continue
            c.setup(h, path, shots, self)
            self.copies.append(c)
            ctx.effects.append(Effect("spark_burst", c.x, c.y, size=1.2))
        ctx.events.append("zap")

    # --- Its moves -------------------------------------------------------------------------

    def m_sweep(self):
        """The laser sweep: an arc across you shown, then its eye's beam
        sweeps it (and keeps sweeping as it slides)."""
        t = self.target_now()
        if t is None:
            return
        arc, tell, secs, burn, every, reach = config.OVERSEER_SWEEP
        aim = math.atan2(t.y - self.y, t.x - self.x)
        side = self.rng.choice((-1, 1))
        a0, a1 = aim - side * math.radians(arc) / 2, aim + side * math.radians(arc) / 2
        self.sweep = (a0, a1, -1.0, reach)
        self.ctx.events.append("hex")
        yield self.tell_s(tell)
        burns: dict[int, float] = {}
        f = 0.0
        while f < 1.0:
            f = min(1.0, f + self.dt / secs)
            a = a0 + (a1 - a0) * f
            length = _beam_end(self.ctx.world, self.x, self.y, a, reach)
            self.sweep = (a0, a1, f, length)
            bx, by = self.x + math.cos(a) * length, self.y + math.sin(a) * length
            for h in self.heroes():
                if not h.hittable or _seg_dist(h.x, h.y, self.x, self.y, bx, by) > 0.45 + h.hit_radius:
                    continue
                left = burns.get(id(h), 0.0) - self.dt
                if left <= 0:
                    left = every
                    _numbered_hit(h, self.hurt(burn), self, a, self.ctx)
                    self.ctx.events.append("fizzle")
                burns[id(h)] = left
            yield 0
        self.sweep = None

    def m_salvo(self):
        """The missile salvo: spots round you locked on, then struck one
        after another."""
        t = self.target_now()
        if t is None:
            return
        n, spread, lock, gap, wide, damage = config.OVERSEER_SALVO
        spots = [(t.x, t.y)]
        for _ in range(40):
            if len(spots) >= n:
                break
            a, r = self.rng.uniform(0.0, _TAU), self.rng.uniform(1.5, spread)
            x, y = t.x + math.cos(a) * r, t.y + math.sin(a) * r
            if self.inside(x, y, 1.0):
                spots.append((x, y))
        lock = self.tell_s(lock)
        self.missiles = [[x, y, lock + k * gap] for k, (x, y) in enumerate(spots)]
        self.ctx.events.append("whistle")
        yield lock + gap * len(spots) + 0.1

    def _tick_missiles(self, ctx, dt: float) -> None:
        if not self.missiles:
            return
        wide, damage = config.OVERSEER_SALVO[4], config.OVERSEER_SALVO[5]
        keep = []
        for m in self.missiles:
            m[2] -= dt
            if m[2] > 0:
                keep.append(m)
                continue
            for h in ctx.players:
                if h.alive and h.hittable and math.hypot(h.x - m[0], h.y - m[1]) <= wide + h.hit_radius:
                    _numbered_hit(h, self.hurt(damage), self, None, ctx)
            ctx.effects.append(Effect("explosion", m[0], m[1]))
            ctx.events.append("boulder")
        self.missiles = keep

    def m_drop(self):
        """The shock drop: down low on its rail (the tell), planted; an
        electric ring, then arcs to the hall's four pylons; it stays low a
        while (easier to hit), then rises."""
        down, reach, speed, damage, arcs, half, arc_damage, stay = config.OVERSEER_DROP
        self.planted = True
        down = self.tell_s(down)
        k = 0.0
        while k < down:
            k += self.dt
            self.low = min(1.0, k / down)
            yield 0
        self.low = 1.0
        self.ring, self.ring_hit = 0.0, set()
        self.ctx.events.append("zap")
        while self.ring is not None and self.ring < reach:
            yield 0
        self.ring = None
        self.arcs = arcs
        hit: set[int] = set()
        for px, py in self.pylons():
            for h in self.heroes():
                if h.hittable and id(h) not in hit \
                        and _seg_dist(h.x, h.y, self.x, self.y, px, py) <= half + h.hit_radius:
                    hit.add(id(h))
                    _numbered_hit(h, self.hurt(arc_damage), self, None, self.ctx)
        self.ctx.events.append("zap")
        yield arcs + stay
        k = 0.0
        while k < 0.5:
            k += self.dt
            self.low = max(0.0, 1.0 - k / 0.5)
            yield 0
        self.low = 0.0
        self.planted = False

    def _tick_ring(self, ctx, dt: float) -> None:
        if self.arcs > 0:
            self.arcs = max(0.0, self.arcs - dt)
        if self.ring is None:
            return
        reach, speed, damage = config.OVERSEER_DROP[1], config.OVERSEER_DROP[2], config.OVERSEER_DROP[3]
        self.ring += speed * dt
        for h in ctx.players:
            if not h.alive or not h.hittable or id(h) in self.ring_hit:
                continue
            if abs(math.hypot(h.x - self.x, h.y - self.y) - self.ring) <= 0.6 + h.hit_radius:
                self.ring_hit.add(id(h))
                _numbered_hit(h, self.hurt(damage), self, None, ctx)

    def m_scan(self):
        """The floor scan: squares across the hall light up, then the lit
        ones are struck from above."""
        size, shown, damage, lit = config.OVERSEER_SCAN
        cx, cy, ra, rb = self.arena()
        kind = self.rng.choice(("checker", "rows", "cols", "rings"))
        flip = self.rng.random() < 0.5
        squares = []
        n_i, n_j = math.ceil(ra / size), math.ceil(rb / size)
        for j in range(-n_j, n_j):
            for i in range(-n_i, n_i):
                x0, y0 = cx + i * size, cy + j * size
                if not self.inside(x0 + size / 2, y0 + size / 2):
                    continue
                if kind == "checker":
                    on = (i + j) % 2 == 0
                elif kind == "rows":
                    on = j % 2 == 0
                elif kind == "cols":
                    on = i % 2 == 0
                else:
                    on = int(math.hypot(i + 0.5, j + 0.5) * 0.9) % 2 == 0
                if on != flip:
                    squares.append((x0, y0))
        shown = self.tell_s(shown)
        self.scan = (squares, shown, False)
        self.ctx.events.append("hex")
        t = 0.0
        while t < shown:
            t += self.dt
            self.scan = (squares, shown - t, False)
            yield 0
        for h in self.heroes():
            if h.hittable and any(x0 <= h.x < x0 + size and y0 <= h.y < y0 + size for x0, y0 in squares):
                _numbered_hit(h, self.hurt(damage), self, None, self.ctx)
        self.scan = (squares, 0.0, True)
        self.ctx.events.append("boulder")
        yield 0.3
        self.scan = None

    def _end_move(self) -> None:
        self.sweep = None
        if self.scan is not None and not self.scan[2]:
            self.scan = None
        if self.form == 2:
            self._city_settle()
        super()._end_move()

    def on_death(self, ctx) -> None:
        for c in self.copies:                       # (its recordings stop)
            if c.alive:
                c.left = True
                c.hp = 0.0
        self.missiles, self.grid, self.ring, self.lock = [], None, None, None
        if self.form == 2:
            self._city_gone(ctx)                    # (M32.5: its eyes close; the walls stay down)
        super().on_death(ctx)
