"""
ai/walking_city.py -- Panopticon's boss, form 2: THE WALKING CITY (M32.5,
design/OCEAN.md 39.2-39.3). A mix-in of ai/overseer.Overseer (one body, two
forms, like the hunger and the first life): at 0 the eye tears out of the
ceiling and builds itself a giant out of the hall -- cell doors, pillars,
screens: a towering four-legged walker with the eye in its chest.

THE WALLS COME DOWN: for WALKER_TEAR s it can't be hit while the hall's
walls are torn apart, from the middle out. Where they stood is torn floor,
broken cells lying in it (cover), the grid's junctions with their live
cables sparking; the floor reaches out over the plaza to a rim of rubble
with breaches in it (WALKER_ARENA). The arena is wider for good (the lair's
radii and its gate move out to the rim). Then it's back at full health (x
WALKER_HP), the boss bar reading "The Walking City". The fight's alert is
gone: the hundred eyes are its sight now.

It always walks (WALKER_BODY): round a loop about the hall's middle, its
four legs stepping, turning slowly to face you (so you can get round it).

SIGNATURES, one added per phase (100-75-50-25%), each kept on after:
  1 IT BUILDS ITSELF    armour plates, one slot a side of its body: a plate
                        takes every hit on its side until it's shot off (it
                        falls as broken cells: cover). It tears pieces out of
                        the hall -- pillars, broken cells, what it threw -- and
                        bolts them on on its target's side. Each plate makes
                        it bigger and stronger (like the hunger's meals).
  2 POWER FROM THE GRID it plugs into the junctions in the broken walls:
                        plugged in, it's shielded and mends. Cut the
                        junctions (shoot them) to drop the shield; it walks
                        over to plug in again. A cut junction's power comes
                        back in a while.
  3 A HUNDRED EYES      small eyes open on its body and round the hall, each
                        watching a cone (WalkerEye): what one sees, it calls
                        a laser strike onto a beat later. Shoot them out, or
                        keep out of their sight.
  4 THE CITY ANSWERS    the watch pours in through the breaches in the
                        rubble, and turrets open on its body.
Moves: stomp (it strides at you, each foot slamming down on a marked spot:
a shock ring), the great beam (planted, the clear tell: the eye charges
along a shown line, fires, and drags the beam across the hall; while it's
planted a hit on its front goes into the eye, past the plates), grab and
throw (you, if you're near: held and thrown; else a piece of the hall,
thrown along a shown line, breaking into cover where it lands), arm swing
(an arm of chained cell doors swung along an arc shown first: roll under
it or get out of reach).

Drawn by render/walking_city.py.
"""

from __future__ import annotations

import math
import random

import numpy as np

from .. import config
from ..entities.effects import Effect
from ..systems import combat, patterns
from ..systems.alert import CALM
from ..systems.raycast import first_hit
from ..world import tiles
from .creatures import _numbered_hit
from .panopticon import _beam_end, _overlaps
from .pangaea import _wrap
from .plains import PlainsCreature

_TAU = math.tau
SIGNATURES = ("IT BUILDS ITSELF", "POWER FROM THE GRID", "A HUNDRED EYES", "THE CITY ANSWERS")
SIGNATURE_LINES = ("shoot its armour plates off", "cut the junctions to drop its shield",
                   "shoot out the eyes or keep out of their sight",
                   "the watch pours in through the breaches")
# What it can tear out of the hall (a piece's tiles), and the plate each makes.
PIECE_TILES = {tiles.HALL_PILLAR: "pillar", tiles.BROKEN_CELL: "door", tiles.BROKEN_PILLAR: "pillar"}
# Its first plates, torn from the walls as it rises (slot: 0 its front).
FIRST_PLATES = ((0, "door"), (1, "screen"), (-1, "door"))   # (WALKER_PLATES[1] of them)
# Its four legs: each hip's place (tiles from its middle, x its size): upper
# left, upper right, lower left, lower right; a foot rests FEET_OUT further
# out. Diagonal pairs step together (0 and 3, then 1 and 2).
HIPS = ((-2.3, -0.7), (2.3, -0.7), (-2.7, 1.3), (2.7, 1.3))
FEET_OUT = 1.6
PAIRS = ((0, 3), (1, 2))
STRIDE = 1.6               # a foot steps once it's this far (x its size) behind
STEP_S = 0.3
# Where its body's turrets open (THE CITY ANSWERS): angles from its front.
TURRET_SLOTS = (math.radians(40), -math.radians(40), math.radians(140), -math.radians(140))


class Plate:
    """An armour plate bolted onto the walking city: what it was in the
    hall, its HP, and (drawing) its hit flash, how fresh it is."""

    __slots__ = ("kind", "hp", "max_hp", "flash", "fresh")

    def __init__(self, kind: str, hp: float) -> None:
        self.kind = kind
        self.hp = self.max_hp = hp
        self.flash = 0.0
        self.fresh = 0.5


class Foot:
    """One of its feet: planted where it is, or stepping (t 0..1) from
    (x0, y0) to (x1, y1)."""

    __slots__ = ("x", "y", "x0", "y0", "x1", "y1", "t", "dur")

    def __init__(self, x: float, y: float) -> None:
        self.x, self.y = x, y
        self.x0 = self.x1 = x
        self.y0 = self.y1 = y
        self.t = -1.0
        self.dur = STEP_S

    @property
    def up(self) -> bool:
        return self.t >= 0.0

    @property
    def lift(self) -> float:
        return math.sin(math.pi * self.t) if self.t >= 0.0 else 0.0

    def start(self, x: float, y: float, dur: float) -> None:
        self.x0, self.y0, self.x1, self.y1 = self.x, self.y, x, y
        self.t = 0.0
        self.dur = max(0.05, dur)

    def step(self, dt: float) -> bool:
        """Carry on stepping; True the step it lands."""
        if self.t < 0.0:
            return False
        self.t = min(1.0, self.t + dt / self.dur)
        self.x = self.x0 + (self.x1 - self.x0) * self.t
        self.y = self.y0 + (self.y1 - self.y0) * self.t
        if self.t >= 1.0:
            self.t = -1.0
            return True
        return False


class WalkerEye(PlainsCreature):
    """One of the hundred eyes (A HUNDRED EYES): on the walking city's body
    (it rides there, looking out) or round the hall (on the floor by the
    rim, panning across it). Seeing a hero WALKER_EYES[9] s, it calls a
    laser strike onto them. When the city falls they close (no kill)."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.city = None
        self.on_body = False
        self.slot = 0.0               # on the body: its angle there, from the city's front
        self.base = 0.0               # round the hall: the way it faces
        self.sway = self.rng.uniform(0.0, _TAU)
        self.watch = 0.0              # s it has seen whoever it sees
        self.cd = 0.0
        self.seeing = None
        self.t = 0.0

    @property
    def reach(self) -> float:
        return config.WALKER_EYES[7] if self.on_body else config.WALKER_EYES[8]

    def think(self, ctx, dt: float) -> None:
        c = self.city
        self.t += dt
        if c is None or not c.alive or c.form != 2:
            self.left = True                       # (it closes: no kill)
            self.hp = 0.0
            return
        if self.on_body:
            self.x, self.y = c.body_point(self.slot, 0.92)
            self.facing = c.facing + self.slot
        else:
            self.facing = self.base + math.radians(35) * math.sin(_TAU * self.t / 5.0 + self.sway)
        self.cd = max(0.0, self.cd - dt)
        self.seeing = c.eye_sees(self, ctx)
        if self.seeing is None:
            self.watch = 0.0
            return
        self.watch += dt
        if self.watch >= config.WALKER_EYES[9] and self.cd <= 0:
            if c.call_strike(ctx, self.seeing):
                self.cd = config.WALKER_EYES[10]
            self.watch = 0.0

    def facing_left(self) -> bool:
        return math.cos(self.facing) < 0


class WalkingCity:
    """Form 2 of ai/overseer.Overseer (see the module's docstring)."""

    def _init_city(self) -> None:
        self.form = 1                     # 1 the eye, "tearing", 2 the walking city
        self.tear_t = 0.0
        # The walls coming down: every tile that changes, in order (from the
        # middle out), and how many are done; solid ones waiting for someone
        # to step off their tile.
        self.tear: list = []              # [((tx, ty), tile)]
        self.torn = 0
        self.waiting: list = []
        self.wide: tuple | None = None    # the new floor's radii (the lair's, once it stands)
        self.rim_gate: list = []          # the rim's tiles where the gate was (they open when it's won)
        self.junctions: list = []         # [(tx, ty)]
        self.cable_tiles: list = []       # each junction's live cables: [[(tx, ty)]]
        self.power_back: dict = {}        # junction -> s until its power comes back
        self.breaches: list = []          # [(x, y)] just inside each breach
        self.pieces: list = []            # what it can tear out: [x, y, kind, [(tx, ty)]]
        # Its body.
        self.plates: list = [None] * config.WALKER_PLATES[0]
        self.size = 1.0
        self.feet: list[Foot] = []
        self.vx = self.vy = 0.0
        self.walk_a = 0.0
        self.walk_dir = 1
        self.walk_t = 0.0
        self.striding: tuple | None = None    # the stomp: walk at this spot
        self.plug_to: tuple | None = None     # the grid: walk to this junction's spot
        self.stomping = False
        self.pose = ""                        # "beam": the eye charging and firing
        # The signatures.
        self.build_t = 0.0
        self.building: list | None = None     # [x, y, kind, s, slot, piece]: an arm tearing a piece out
        self.cables: list[int] = []           # the junctions it's plugged into
        self.unplug_t = 0.0
        self.eyes: list[WalkerEye] = []
        self.eye_t = 0.0
        self.strikes: list = []               # [hero, x, y, s so far]
        self.city_t = 0.0
        self.turret_t: list[float] = []
        self.turret_q: list[int] = []
        self.turret_g: list[float] = []
        self.turret_aim: list = []
        self.turret_fired: list[float] = []   # (drawing: a muzzle flash)
        # What its moves show (render/walking_city.py).
        self.stomp_marks: list = []           # [x, y, s left, leg]
        self.shocks: list = []                # [x, y, radius, {hit}]
        self.great_beam: list | None = None   # [angle, t (< 0 charging, 0..1 dragging), length]
        self.arm: list | None = None          # [x, y, s, of, kind]: its arm reaching (grab, reach, hold)
        self.grabbed: list | None = None      # [hero, s left, angle, how far]
        self.flung: list | None = None        # [hero, angle, s left, damage]
        self.lifted: str | None = None        # the piece held over its body
        self.thrown: list | None = None       # [x0, y0, x1, y1, s, of, kind]
        self.throw_line: tuple | None = None  # (x0, y0, x1, y1)
        self.arm_swing: tuple | None = None   # (a0, a1, f (< 0 shown), length)

    # --- Being the walking city ---------------------------------------------------------

    @property
    def plated(self) -> int:
        return sum(1 for p in self.plates if p is not None)

    def strength(self) -> float:
        return 1.0 + config.WALKER_PLATES[6] * self.plated

    def _resize(self) -> None:
        self.size = 1.0 + config.WALKER_PLATES[5] * self.plated
        self.hit_radius = config.WALKER_BODY[0] * self.size

    def plate_hp(self) -> float:
        return self.max_hp * config.WALKER_PLATES[4]

    def slot_angle(self, k: int) -> float:
        """Slot k's angle from its front."""
        return _wrap(k * _TAU / len(self.plates))

    def slot_of(self, side: float) -> int:
        n = len(self.plates)
        return round(_wrap(side - self.facing) / (_TAU / n)) % n

    def body_point(self, rel: float, k: float = 1.0) -> tuple[float, float]:
        """The point on its body `rel` from its front (k x its radius out)."""
        a = self.facing + rel
        r = self.hit_radius * k
        return self.x + math.cos(a) * r, self.y + math.sin(a) * r

    def foot_rest(self, i: int) -> tuple[float, float]:
        hx, hy = HIPS[i]
        s = self.size * FEET_OUT
        return self.x + hx * s, self.y + hy * s

    @property
    def shielded(self) -> bool:
        return bool(self.cables)

    def _side_hit(self, source, from_angle) -> float | None:
        """Which way from its middle a hit struck it (None: no telling)."""
        if from_angle is not None:
            return from_angle + math.pi
        if source is not None and source is not self and hasattr(source, "x"):
            return math.atan2(source.y - self.y, source.x - self.x)
        return None

    def _city_takes(self, amount: float, source, from_angle) -> tuple[float, int | None]:
        """A hit on the walking city: (what its body takes, or the slot of the
        plate that took it all instead)."""
        side = self._side_hit(source, from_angle)
        if side is not None:
            rel = _wrap(side - self.facing)
            if self.pose == "beam" and abs(rel) <= math.radians(config.WALKER_BEAM[8]):
                amount *= config.WALKER_BEAM[9]        # (planted: into the eye, past the plates)
            else:
                k = self.slot_of(side)
                if self.plates[k] is not None:
                    return 0.0, k
        if self.cables:
            amount *= config.WALKER_GRID[2]            # (plugged in: shielded)
        return amount, None

    def _hit_plate(self, k: int, amount: float, source) -> float:
        p = self.plates[k]
        dealt = min(amount, p.hp)
        p.hp -= amount
        p.flash = 0.12
        if source is not None:
            self.last_hit_by = source
        if p.hp <= 0:
            self._plate_off(k)
        return dealt

    def _plate_off(self, k: int) -> None:
        """A plate shot off: it falls beside it, broken cells (cover it can
        tear out again)."""
        ctx = self.ctx
        self.plates[k] = None
        self._resize()
        if ctx is None:
            return
        x, y = self.body_point(self.slot_angle(k), 1.0)
        ctx.effects.append(Effect("toast", x, y - 1.5, label="PLATE OFF!"))
        ctx.effects.append(Effect("debris", x, y))
        ctx.events.append("break")
        fx, fy = self.body_point(self.slot_angle(k), 1.0 + 1.6 / max(1.0, self.hit_radius))
        self._drop_cover(fx, fy, tiles.BROKEN_CELL, "door", ((0, 0), (1, 0), (0, 1)))

    def _drop_cover(self, x: float, y: float, tile, kind: str, shape) -> None:
        """Lay a clump of `tile` round (x, y) (not on anyone, not on anything
        solid, not off the floor): a piece of the hall again."""
        w = self.ctx.world
        if not hasattr(w, "set_tile"):
            return
        ox, oy = math.floor(x), math.floor(y)
        laid = []
        for dx, dy in shape:
            tx, ty = ox + dx, oy + dy
            if w.tile_at(tx, ty).solid or not self.inside(tx + 0.5, ty + 0.5, 1.5):
                continue
            if any(a.alive and _overlaps(a, tx, ty) for a in self.ctx.actors):
                continue
            w.set_tile(tx, ty, tile)
            laid.append((tx, ty))
        if laid:
            self.pieces.append([ox + 0.5, oy + 0.5, kind, laid])

    def eye_sees(self, e: WalkerEye, ctx):
        """The hero eye `e` sees (in its cone, in reach, nothing between), or None."""
        half = math.radians(config.WALKER_EYES[6]) / 2
        reach = e.reach
        for h in ctx.players:
            if not h.alive or not self.in_arena(h):
                continue
            if math.hypot(h.x - e.x, h.y - e.y) > reach:
                continue
            if abs(_wrap(math.atan2(h.y - e.y, h.x - e.x) - e.facing)) > half:
                continue
            if first_hit(ctx.world.tile_at, e.x, e.y, h.x, h.y) is None:
                return h
        return None

    def call_strike(self, ctx, h) -> bool:
        """An eye calls a laser strike onto hero h (not past WALKER_EYES[15]
        marks on them at once)."""
        if sum(1 for s in self.strikes if s[0] is h) >= config.WALKER_EYES[15]:
            return False
        self.strikes.append([h, h.x, h.y, 0.0])
        ctx.events.append("hex")
        return True

    # --- The walls come down -------------------------------------------------------------

    def _tear(self) -> None:
        """At 0 the eye tears out of the ceiling: whatever it was doing stops,
        the fight's alert is gone, the watch out of the cells is pulled into
        it (no kill), and the hall's walls start coming down."""
        ctx = self.ctx
        self.form = "tearing"
        self.tear_t = config.WALKER_TEAR
        self.move, self._gen, self.tell = None, None, None
        self.sweep = self.lock = self.grid = self.scan = self.ring = None
        self.missiles = []
        self.arcs = 0.0
        self.seeing = None
        self.meter, self.level, self.lock_t, self.quiet = 0.0, CALM, 0.0, 0.0
        self.planted = False
        for c in self.copies:                           # (its recordings stop)
            if c.alive:
                c.left = True
                c.hp = 0.0
        self.copies = []
        if ctx is None:
            return
        for e in self.adds:                             # (the machines in the cells: part of it now)
            if e.alive:
                ctx.effects.append(Effect("spark_burst", e.x, e.y, size=1.2))
                e.left = True
                e.hp = 0.0
                e.last_hit_by = None
        self.adds = []
        self.banner_req = ("THE EYE TEARS FREE", "it builds itself a body out of the hall")
        ctx.effects.append(Effect("explosion", self.x, self.y))
        ctx.effects.append(Effect("toast", self.x, self.y - 4.0, label="IT TEARS FREE!"))
        ctx.events.append("boulder")
        self._plan_tear()

    def _plan_tear(self) -> None:
        """What the walls coming down leave, in the order it happens (from
        the middle out; the rim of rubble last): torn floor where the walls
        and the plaza were, broken cells (cover), the junctions and their
        live cables, the rim and its breaches. Without a lair (a test's open
        hall) nothing comes down: the junctions and broken cells are laid
        just inside its edge."""
        ctx = self.ctx
        self.tear, self.torn, self.waiting = [], 0, []
        self.junctions, self.cable_tiles, self.breaches, self.pieces = [], [], [], []
        w = ctx.world
        if not hasattr(w, "set_tile"):
            return
        rng = random.Random(self.rng.random())
        out, thick, clumps, n_j, cable, n_b = config.WALKER_ARENA
        cx, cy, a, b = self.arena()
        lair = self.lair
        changes: dict = {}
        order: dict = {}
        if lair is not None:
            wall = config.PANOPTICON_TOWER_WALL
            A, B = a + wall + out, b + wall + out
            ia, ib = a, b                                   # (the hall's edge: d counts from here)
            d0, d1, dj = 1.5, wall + out - 2.0, wall / 2 + 0.5
            gx, gy = lair.props.get("facing", (1.0, 0.0))
            x0, x1 = math.floor(cx - A - thick - 1), math.ceil(cx + A + thick + 1)
            y0, y1 = math.floor(cy - B - thick - 1), math.ceil(cy + B + thick + 1)
            X = np.arange(x0, x1 + 1)[None, :] + 0.5
            Y = np.arange(y0, y1 + 1)[:, None] + 0.5
            e_hall = ((X - cx) / a) ** 2 + ((Y - cy) / b) ** 2
            e_floor = ((X - cx) / A) ** 2 + ((Y - cy) / B) ** 2
            e_rim = ((X - cx) / (A + thick)) ** 2 + ((Y - cy) / (B + thick)) ** 2
            band = (e_hall >= 1.0) & (e_floor < 1.0)
            rim = (e_floor >= 1.0) & (e_rim < 1.0)
            across = np.abs((X - cx) * -gy + (Y - cy) * gx)
            along = (X - cx) * gx + (Y - cy) * gy
            gate = rim & (across <= config.PANOPTICON_HALL_GATE / 2) & (along > 0)
            r = np.sqrt(e_hall)
            for mask, tile in ((band, tiles.BROKEN_FLOOR), (rim, tiles.RUBBLE_HEAP)):
                js, is_ = np.nonzero(mask)
                for j, i, rr in zip(js.tolist(), is_.tolist(), r[js, is_].tolist()):
                    p = (x0 + i, y0 + j)
                    changes[p] = tile
                    order[p] = rr + (10.0 if tile is tiles.RUBBLE_HEAP else 0.0)
            js, is_ = np.nonzero(gate)
            self.rim_gate = [(x0 + i, y0 + j) for j, i in zip(js.tolist(), is_.tolist())]
            phi = math.atan2(gy, gx)
            for k in range(n_b):                            # (breaches: away from the gate)
                t = phi + math.pi / 4 + k * _TAU / n_b
                bx, by = cx + math.cos(t) * (A + thick / 2), cy + math.sin(t) * (B + thick / 2)
                for p in [q for q, tl in changes.items() if tl is tiles.RUBBLE_HEAP
                          and math.hypot(q[0] + 0.5 - bx, q[1] + 0.5 - by) <= 1.8]:
                    changes[p] = tiles.BREACH
                self.breaches.append((cx + math.cos(t) * (A - 2.5), cy + math.sin(t) * (B - 2.5)))
            self.wide = (A - 1.0, B - 1.0)
        else:
            ia, ib = a - 6.0, b - 6.0
            d0, d1, dj = 1.0, 4.0, 3.0
            phi = 0.0
            for k in range(n_b):
                t = math.pi / 4 + k * _TAU / n_b
                self.breaches.append((cx + math.cos(t) * (a - 2.5), cy + math.sin(t) * (b - 2.5)))

        def at(t: float, d: float) -> tuple[int, int]:
            return (math.floor(cx + math.cos(t) * (ia + d)), math.floor(cy + math.sin(t) * (ib + d)))

        # The grid's junctions in the old wall, their live cables along it.
        for k in range(n_j):
            t = phi + (k + 0.5) * _TAU / n_j
            p = at(t, dj)
            changes[p] = tiles.JUNCTION
            order.setdefault(p, 1.0)
            self.junctions.append(p)
            run = []
            rad = (ia + ib) / 2 + dj
            for s in np.arange(-cable, cable + 0.01, 0.5).tolist():
                q = at(t + s / rad, dj)
                if q == p or q in run:
                    continue
                if lair is not None:
                    if changes.get(q) is not tiles.BROKEN_FLOOR:      # (only on the torn floor)
                        continue
                elif q in changes or w.tile_at(*q).solid:
                    continue
                changes[q] = tiles.CABLE
                order.setdefault(q, 1.0)
                run.append(q)
            self.cable_tiles.append(run)
        # Broken cells lying in the torn walls (cover), away from the junctions
        # and the gate's way out.
        spots = []
        for _ in range(clumps * 6):
            if len(spots) >= clumps:
                break
            t = rng.uniform(0.0, _TAU)
            if abs(_wrap(t - phi)) < 0.22 and lair is not None:
                continue
            if any(abs(_wrap(t - (phi + (k + 0.5) * _TAU / n_j))) < 0.16 for k in range(n_j)):
                continue
            if any(abs(_wrap(t - s)) < 0.17 for s, _ in spots):
                continue
            spots.append((t, rng.uniform(d0, d1)))
        for t, d in spots:
            ox, oy = at(t, d)
            wide = rng.choice((2, 3))
            laid = []
            for dy in range(2):
                for dx in range(wide):
                    p = (ox + dx, oy + dy)
                    if changes.get(p, tiles.BROKEN_FLOOR) is not tiles.BROKEN_FLOOR:
                        continue
                    if lair is None and w.tile_at(*p).solid:
                        continue
                    changes[p] = tiles.BROKEN_CELL
                    order.setdefault(p, 1.0)
                    laid.append(p)
            if laid:
                self.pieces.append([ox + wide / 2, oy + 1.0, "door", laid])
        # The hall's pillars: pieces too (it tears them out to build itself).
        for px, py in (lair.props.get("pillars", ()) if lair is not None else ()):
            laid = [(math.floor(px) + dx, math.floor(py) + dy) for dy in (-1, 0, 1) for dx in (-1, 0, 1)]
            self.pieces.append([px, py, "pillar", laid])
        self.tear = sorted(changes.items(), key=lambda kv: order.get(kv[0], 1.0))

    def _lay(self, p, tile) -> None:
        """One tile of the walls coming down -- a solid one not on anyone
        (it waits: torn floor till then)."""
        w = self.ctx.world
        if tile.solid and any(a.alive and a is not self and _overlaps(a, *p) for a in self.ctx.actors):
            self.waiting.append((p, tile))
            if not w.tile_at(*p).solid:
                return
            tile = tiles.BROKEN_FLOOR
        w.set_tile(p[0], p[1], tile)

    def _tear_to(self, n: int) -> None:
        for p, tile in self.tear[self.torn:n]:
            self._lay(p, tile)
        self.torn = max(self.torn, n)

    def _settle_waiting(self) -> None:
        if not self.waiting:
            return
        still = self.waiting
        self.waiting = []
        for p, tile in still:
            self._lay(p, tile)

    def _tear_step(self, ctx, dt: float) -> None:
        """The walls coming down, a slice a step; it can't be hit."""
        self.dt = dt
        self.time += dt
        self.tear_t -= dt
        q = 1.0 - max(0.0, self.tear_t) / config.WALKER_TEAR
        before = self.torn
        self._tear_to(round(len(self.tear) * q))
        self.low = min(1.0, self.low + dt * 1.5)          # (the eye comes down)
        if int(self.time * 8) != int((self.time - dt) * 8):
            fresh = self.tear[before:self.torn]
            if fresh:
                (tx, ty), _ = fresh[self.rng.randrange(len(fresh))]
                ctx.effects.append(Effect("debris", tx + 0.5, ty + 0.5))
            a, r = self.rng.uniform(0, _TAU), self.rng.uniform(1.0, 3.0)
            ctx.effects.append(Effect("spark_burst", self.x + math.cos(a) * r, self.y + math.sin(a) * r,
                                      size=1.4))
        if int(self.time * 2) != int((self.time - dt) * 2):
            ctx.events.append("boulder")
        if self.tear_t <= 0:
            self._become_city(ctx)

    def _become_city(self, ctx) -> None:
        self._tear_to(len(self.tear))
        lair = self.lair
        if lair is not None and self.wide is not None:   # (the arena is wider for good)
            lair.radii = self.wide
            if self.rim_gate:
                lair.gate = list(self.rim_gate)
        self.form = 2
        self.low = 0.0
        self.planted = False
        self.bspec = config.BOSSES["overseer_city"]
        self.phase = 0
        self.max_hp = round(self.max_hp * config.WALKER_HP)
        self.hp = float(self.max_hp)
        n = len(self.plates)
        self.plates = [None] * n
        for k, kind in FIRST_PLATES[:config.WALKER_PLATES[1]]:
            self.plates[k % n] = Plate(kind, self.plate_hp())
        self._resize()
        cx, cy, ra, rb = self.arena()
        self.walk_a = math.atan2((self.y - cy) / max(1.0, rb), (self.x - cx) / max(1.0, ra))
        self.feet = [Foot(*self.foot_rest(i)) for i in range(4)]
        t = self.drift_target()
        if t is not None:
            self.facing = math.atan2(t.y - self.y, t.x - self.x)
        self._rest = 1.5
        self.combo = 0
        self.last_move = None
        self.build_t = config.WALKER_PLATES[2] * 0.6
        self.banner_req = ("THE WALKING CITY", "shoot its armour plates off -- get round it")
        ctx.effects.append(Effect("explosion", self.x, self.y))
        for k in range(6):
            a = k * _TAU / 6
            ctx.effects.append(Effect("debris", self.x + math.cos(a) * 3.0, self.y + math.sin(a) * 2.4))
        ctx.events.append("boulder")

    # --- Each step ---------------------------------------------------------------------

    def _city_step(self, ctx, dt: float) -> None:
        self._settle_waiting()
        self._walk(dt)
        self._gait(dt)
        for p in self.plates:
            if p is not None:
                p.flash = max(0.0, p.flash - dt)
                p.fresh = max(0.0, p.fresh - dt)
        for k in range(len(self.turret_fired)):
            self.turret_fired[k] = max(0.0, self.turret_fired[k] - dt)
        self._build(ctx, dt)
        self._power(ctx, dt)
        if self.phase >= 2:
            self._open_eyes(ctx, dt)
        for e in self.eyes:                              # (they ride on its body)
            if e.on_body and e.alive:
                e.x, e.y = self.body_point(e.slot, 0.92)
                e.facing = self.facing + e.slot
        self._tick_strikes(ctx, dt)
        if self.phase >= 3:
            self._answer(ctx, dt)
            self._turrets(ctx, dt)
        self._tick_stomp(ctx, dt)
        self._tick_shocks(ctx, dt)
        self._tick_held(ctx, dt)
        self._tick_thrown(ctx, dt)

    def _walk(self, dt: float) -> None:
        """Round its loop (or where a move or the grid sends it), turning
        slowly to face its target."""
        t = self.drift_target()
        if t is not None and self.pose != "beam":
            want = math.atan2(t.y - self.y, t.x - self.x)
            turn = config.WALKER_BODY[5] * dt
            self.facing += max(-turn, min(turn, _wrap(want - self.facing)))
        x0, y0 = self.x, self.y
        if not self.planted and self.dazed <= 0 and self.grabbed is None:
            speed = config.WALKER_BODY[2]
            if self.striding is not None:
                gx, gy = self.striding
                speed = config.WALKER_STOMP[0]
            elif self.plug_to is not None:
                gx, gy = self.plug_to
            else:
                cx, cy, ra, rb = self.arena()
                k = config.WALKER_BODY[3]
                gx, gy = cx + math.cos(self.walk_a) * ra * k, cy + math.sin(self.walk_a) * rb * k
                if math.hypot(gx - self.x, gy - self.y) < 3.0:   # (on its loop: on round it)
                    self.walk_t += dt
                    if self.walk_t >= config.WALKER_BODY[4]:
                        self.walk_t = self.rng.uniform(-3.0, 3.0)
                        self.walk_dir = -self.walk_dir
                    r = max(4.0, (ra + rb) / 2 * k)
                    self.walk_a = (self.walk_a + self.walk_dir * speed / r * dt) % _TAU
                    gx, gy = cx + math.cos(self.walk_a) * ra * k, cy + math.sin(self.walk_a) * rb * k
            dx, dy = gx - self.x, gy - self.y
            d = math.hypot(dx, dy)
            if d > 0.05:
                s = min(d, speed * dt)
                self.x += dx / d * s
                self.y += dy / d * s
            self.x, self.y = self.clamp_to_lair(self.x, self.y, self.hit_radius + 1.0)
        self.vx = (self.x - x0) / dt if dt > 0 else 0.0
        self.vy = (self.y - y0) / dt if dt > 0 else 0.0

    def _gait(self, dt: float) -> None:
        """Its legs: a diagonal pair steps when its feet fall behind (a stomp
        steps its feet itself)."""
        if not self.feet:
            self.feet = [Foot(*self.foot_rest(i)) for i in range(4)]
        for f in self.feet:
            f.step(dt)
        if self.stomping:
            return
        if any(f.up for f in self.feet):
            return
        stride = STRIDE * self.size
        lead = 0.3
        for pair in PAIRS:
            far = False
            for i in pair:
                rx, ry = self.foot_rest(i)
                f = self.feet[i]
                if math.hypot(f.x - rx - self.vx * lead, f.y - ry - self.vy * lead) > stride * 0.5 \
                        and math.hypot(f.x - rx, f.y - ry) > stride * 0.5:
                    far = True
            if far:
                for i in pair:
                    rx, ry = self.foot_rest(i)
                    self.feet[i].start(rx + self.vx * lead, ry + self.vy * lead, STEP_S)
                break

    # --- 1. It builds itself --------------------------------------------------------------

    def _nearest_piece(self, reach: float):
        """The nearest piece of the hall still standing within `reach`
        (forgetting the ones gone)."""
        w = self.ctx.world
        best, bd = None, reach
        keep = []
        for pc in self.pieces:
            if not any(w.tile_at(*p) in PIECE_TILES for p in pc[3]):
                continue
            keep.append(pc)
            d = math.hypot(pc[0] - self.x, pc[1] - self.y)
            if d < bd:
                best, bd = pc, d
        self.pieces = keep
        return best

    def _tear_out(self, pc) -> None:
        w = self.ctx.world
        for p in pc[3]:
            if w.tile_at(*p) in PIECE_TILES:
                w.set_tile(p[0], p[1], tiles.BROKEN_FLOOR)
        if pc in self.pieces:
            self.pieces.remove(pc)
        self.ctx.effects.append(Effect("debris", pc[0], pc[1]))
        self.ctx.events.append("break")

    def _build(self, ctx, dt: float) -> None:
        """IT BUILDS ITSELF: every WALKER_PLATES[2] s an arm tears a piece out
        of the hall (or the floor, with nothing in reach) and bolts it on on
        its target's side."""
        if self.building is not None:
            b = self.building
            b[3] += dt
            if b[3] >= 0.35 and b[4] is None:            # (torn out: on its way)
                pc = b[5]
                if pc is not None:
                    self._tear_out(pc)
                b[4] = self._free_slot()
                if b[4] is None:
                    self.building = None
                    return
            if b[3] >= 0.7:
                k = b[4]
                if k is not None and self.plates[k] is None:
                    hp = self.plate_hp() * (0.6 if b[2] == "rubble" else 1.0)
                    self.plates[k] = Plate(b[2], hp)
                    self._resize()
                    x, y = self.body_point(self.slot_angle(k), 1.0)
                    ctx.effects.append(Effect("spark_burst", x, y, size=1.4))
                    ctx.effects.append(Effect("toast", x, y - 1.5, label="BOLTED ON!"))
                    ctx.events.append("zap")
                self.building = None
            return
        self.build_t -= dt
        if self.build_t > 0:
            return
        self.build_t = config.WALKER_PLATES[2]
        if self._free_slot() is None:
            return
        pc = self._nearest_piece(config.WALKER_PLATES[3])
        if pc is not None:
            self.building = [pc[0], pc[1], PIECE_KINDS.get(pc[2], pc[2]), 0.0, None, pc]
        else:                                            # (nothing in reach: it tears up the floor)
            a = self.facing + self.rng.uniform(-1.0, 1.0)
            x, y = self.x + math.cos(a) * (self.hit_radius + 2.5), self.y + math.sin(a) * (self.hit_radius + 2.5)
            self.building = [x, y, "rubble", 0.0, None, None]
            ctx.effects.append(Effect("debris", x, y))

    def _free_slot(self) -> int | None:
        """The empty slot nearest its target's side."""
        empty = [k for k, p in enumerate(self.plates) if p is None]
        if not empty:
            return None
        t = self.drift_target()
        side = math.atan2(t.y - self.y, t.x - self.x) if t is not None else self.facing
        return min(empty, key=lambda k: abs(_wrap(self.slot_angle(k) + self.facing - side)))

    # --- 2. Power from the grid ----------------------------------------------------------

    def junction_spot(self, j: int) -> tuple[float, float]:
        tx, ty = self.junctions[j]
        return tx + 0.5, ty + 0.5

    def _power(self, ctx, dt: float) -> None:
        """The junctions: cut ones (their cables go dead) and their power
        coming back; from the second phase, plugging in, shielded and mending
        while plugged."""
        w = ctx.world
        n, reach, _, mend, most, down, back = config.WALKER_GRID
        for j in list(self.power_back):
            self.power_back[j] -= dt
            if self.power_back[j] <= 0:
                del self.power_back[j]
                tx, ty = self.junctions[j]
                if w.tile_at(tx, ty) is tiles.DEAD_JUNCTION:
                    w.set_tile(tx, ty, tiles.JUNCTION)
                for q in self.cable_tiles[j]:
                    if w.tile_at(*q) is tiles.DEAD_CABLE:
                        w.set_tile(q[0], q[1], tiles.CABLE)
                ctx.effects.append(Effect("spark_burst", tx + 0.5, ty + 0.5, size=1.2))
        for j, (tx, ty) in enumerate(self.junctions):
            if j not in self.power_back and w.tile_at(tx, ty) is not tiles.JUNCTION:
                self._cut(ctx, j)
        if self.phase < 1:
            return
        for j in list(self.cables):
            x, y = self.junction_spot(j)
            if math.hypot(x - self.x, y - self.y) > most:   # (it walked too far: it pops loose)
                self.cables.remove(j)
        if self.cables:
            self.plug_to = None
            self.heal(self.max_hp * mend * dt)
            return
        if self.unplug_t > 0:
            self.unplug_t -= dt
            return
        live = [j for j in range(len(self.junctions)) if j not in self.power_back]
        if not live:
            self.plug_to = None
            return
        dist = {j: math.hypot(self.junction_spot(j)[0] - self.x, self.junction_spot(j)[1] - self.y)
                for j in live}
        live.sort(key=dist.get)
        if dist[live[0]] <= reach:
            self.cables = [j for j in live[:n] if dist[j] <= reach]
            self.plug_to = None
            ctx.effects.append(Effect("toast", self.x, self.y - self.hit_radius - 2.0, label="PLUGGED IN"))
            ctx.events.append("zap")
        else:                                            # (it walks over to plug in)
            x, y = self.junction_spot(live[0])
            d = dist[live[0]]
            k = (d - reach + 3.0) / d
            self.plug_to = self.clamp_to_lair(self.x + (x - self.x) * k, self.y + (y - self.y) * k,
                                              self.hit_radius + 1.0)

    def _cut(self, ctx, j: int) -> None:
        """Junction j is cut: its cables go dead (and out of it, if plugged in)."""
        w = ctx.world
        self.power_back[j] = config.WALKER_GRID[6]
        for q in self.cable_tiles[j]:
            if w.tile_at(*q) is tiles.CABLE:
                w.set_tile(q[0], q[1], tiles.DEAD_CABLE)
        x, y = self.junction_spot(j)
        ctx.effects.append(Effect("spark_burst", x, y, size=1.6))
        if j in self.cables:
            self.cables.remove(j)
            ctx.effects.append(Effect("toast", x, y - 1.5, label="CABLE CUT!"))
            ctx.events.append("zap")
            if not self.cables:
                self.unplug_t = config.WALKER_GRID[5]
                ctx.effects.append(Effect("toast", self.x, self.y - self.hit_radius - 2.0,
                                          label="SHIELD DOWN!"))
                ctx.events.append("break")

    # --- 3. A hundred eyes ----------------------------------------------------------------

    def _open_eyes(self, ctx, dt: float) -> None:
        self.eyes = [e for e in self.eyes if e.alive]
        self.eye_t -= dt
        if self.eye_t > 0 or self.recruit is None:
            return
        first, more, every, most_body, most_hall = (config.WALKER_EYES[0], config.WALKER_EYES[2],
                                                    config.WALKER_EYES[3], config.WALKER_EYES[4],
                                                    config.WALKER_EYES[5])
        opened = getattr(self, "eyes_opened", False)
        self.eyes_opened = True
        self.eye_t = every
        body = sum(1 for e in self.eyes if e.on_body)
        hall = len(self.eyes) - body
        nb = min(first if not opened else more, most_body - body)
        nh = min(config.WALKER_EYES[1] if not opened else more, most_hall - hall)
        cx, cy, ra, rb = self.arena()
        base = self.rng.uniform(0.0, _TAU)
        for k in range(max(0, nb)):
            rel = _wrap(base + k * _TAU / max(1, nb) + self.rng.uniform(-0.25, 0.25))
            x, y = self.body_point(rel, 0.92)
            e = self.recruit("walker_eye", x, y)
            if e is None:
                continue
            e.city, e.on_body, e.slot = self, True, rel
            self._eye_joins(ctx, e)
        for k in range(max(0, nh)):
            t = self.rng.uniform(0.0, _TAU)
            x, y = cx + math.cos(t) * (ra - 2.0), cy + math.sin(t) * (rb - 2.0)
            if ctx.world.tile_at(math.floor(x), math.floor(y)).solid:
                continue
            e = self.recruit("walker_eye", x, y)
            if e is None:
                continue
            e.city, e.on_body = self, False
            e.base = e.facing = math.atan2(cy - y, cx - x)
            self._eye_joins(ctx, e)
        ctx.events.append("hex")

    def _eye_joins(self, ctx, e) -> None:
        e.part_of = self                                # (its own shots pass them)
        e.alert = True
        self.eyes.append(e)
        ctx.effects.append(Effect("spark_burst", e.x, e.y, size=0.8))

    def _tick_strikes(self, ctx, dt: float) -> None:
        if not self.strikes:
            return
        follow, hold, radius, damage = (config.WALKER_EYES[11], config.WALKER_EYES[12],
                                        config.WALKER_EYES[13], config.WALKER_EYES[14])
        keep = []
        for s in self.strikes:
            s[3] += dt
            h = s[0]
            if s[3] < follow and h.alive:
                s[1], s[2] = h.x, h.y
            if s[3] < follow + hold:
                keep.append(s)
                continue
            for o in ctx.players:
                if o.alive and o.hittable and math.hypot(o.x - s[1], o.y - s[2]) <= radius + o.hit_radius:
                    _numbered_hit(o, self.hurt(damage), self, None, ctx)
            ctx.effects.append(Effect("spark_burst", s[1], s[2], size=radius))
            ctx.events.append("zap")
        self.strikes = keep

    # --- 4. The city answers --------------------------------------------------------------

    def _answer(self, ctx, dt: float) -> None:
        """The watch pours in through the breaches (not past WALKER_CITY[2] out)."""
        self.city_t -= dt
        if self.city_t > 0 or self.recruit is None:
            return
        every, n, most = config.WALKER_CITY[0], config.WALKER_CITY[1], config.WALKER_CITY[2]
        self.city_t = every
        self.adds = [e for e in self.adds if e.alive]
        room = most - len(self.adds)
        if room <= 0 or not self.breaches:
            return
        t = self.drift_target()
        spots = sorted(self.breaches, key=lambda p: math.hypot(p[0] - t.x, p[1] - t.y)) if t else \
            list(self.breaches)
        keys = config.WALKER_CITY_WATCH
        for k in range(min(n, room)):
            bx, by = spots[k % min(2, len(spots))]
            x, y = bx + self.rng.uniform(-1.5, 1.5), by + self.rng.uniform(-1.5, 1.5)
            e = self.recruit(keys[k % len(keys)], x, y)
            if e is None:
                continue
            e.alert = True
            if t is not None and hasattr(e, "called_to"):
                e.called_to(t)
            self.adds.append(e)
            ctx.effects.append(Effect("spark_burst", x, y, size=1.6))
        ctx.events.append("whistle")

    def _turrets(self, ctx, dt: float) -> None:
        """The turrets open on its body: each a burst at whoever is in front
        of it, now and then."""
        _, _, _, n, burst, gap, every, arc, reach = config.WALKER_CITY
        if len(self.turret_t) != n:
            self.turret_t = [every * (0.3 + k / n) for k in range(n)]
            self.turret_q = [0] * n
            self.turret_g = [0.0] * n
            self.turret_aim = [None] * n
            self.turret_fired = [0.0] * n
        shell = config.PANOPTICON_SHOTS["turret_bolt"]
        half = math.radians(arc) / 2
        for k in range(n):
            rel = TURRET_SLOTS[k % len(TURRET_SLOTS)]
            x, y = self.body_point(rel, 1.0)
            if self.turret_q[k] > 0:
                self.turret_g[k] -= dt
                h = self.turret_aim[k]
                if self.turret_g[k] <= 0 and h is not None and h.alive:
                    self.turret_g[k] = gap
                    self.turret_q[k] -= 1
                    q = patterns.shoot(self, x, y, math.atan2(h.y - y, h.x - x), shell, ctx.projectiles)
                    q.damage *= self.strength()
                    self.turret_fired[k] = 0.1
                elif h is None or not h.alive:
                    self.turret_q[k] = 0
                continue
            self.turret_t[k] -= dt
            if self.turret_t[k] > 0:
                continue
            self.turret_t[k] = every
            if not self.room_for_shots():
                continue
            face = self.facing + rel
            best = None
            for h in self.heroes():                     # (its sector, from its middle)
                d = math.hypot(h.x - x, h.y - y)
                if d > reach or abs(_wrap(math.atan2(h.y - self.y, h.x - self.x) - face)) > half:
                    continue
                if first_hit(ctx.world.tile_at, x, y, h.x, h.y) is not None:
                    continue
                if best is None or d < best[0]:
                    best = (d, h)
            if best is not None:
                self.turret_aim[k] = best[1]
                self.turret_q[k] = burst
                self.turret_g[k] = 0.0

    # --- Its moves ------------------------------------------------------------------------

    def m_stomp(self):
        """Stomp: it strides at you, each foot slamming down on a marked spot
        (a shock ring)."""
        t = self.target_now()
        if t is None:
            return
        speed, steps, gap, shown, _, _, _ = config.WALKER_STOMP
        shown = self.tell_s(shown)
        self.stomping = True
        legs = (0, 3, 1, 2)
        for i in range(steps):
            t = self.target_now()
            if t is None:
                break
            a = math.atan2(t.y - self.y, t.x - self.x)
            d = math.hypot(t.x - self.x, t.y - self.y)
            self.striding = (t.x, t.y)
            travel = min(speed * shown, max(0.0, d - self.hit_radius - 1.0))
            bx, by = self.x + math.cos(a) * travel, self.y + math.sin(a) * travel
            leg = legs[i % 4]
            hx, hy = HIPS[leg]
            s = self.size * FEET_OUT
            fx, fy = self.clamp_to_lair(bx + hx * s, by + hy * s, 1.0)
            self.stomp_marks.append([fx, fy, shown, leg])
            if i == 0:
                self.ctx.events.append("hex")
            yield gap
        self.striding = None
        while self.stomp_marks:
            yield 0
        self.stomping = False

    def _tick_stomp(self, ctx, dt: float) -> None:
        if not self.stomp_marks:
            return
        keep = []
        for m in self.stomp_marks:
            m[2] -= dt
            f = self.feet[m[3]] if self.feet else None
            if f is not None and m[2] <= STEP_S and m[2] > 0 and not (f.up and f.x1 == m[0] and f.y1 == m[1]):
                f.start(m[0], m[1], m[2])
            if m[2] > 0:
                keep.append(m)
                continue
            if f is not None:                            # (it lands: a shock ring)
                f.x, f.y, f.t = m[0], m[1], -1.0
            self.shocks.append([m[0], m[1], 0.0, set()])
            ctx.effects.append(Effect("debris", m[0], m[1]))
            ctx.events.append("boulder")
        self.stomp_marks = keep

    def _tick_shocks(self, ctx, dt: float) -> None:
        if not self.shocks:
            return
        reach, speed, damage = config.WALKER_STOMP[4], config.WALKER_STOMP[5], config.WALKER_STOMP[6]
        for s in self.shocks:
            s[2] += speed * dt
            for h in ctx.players:
                if not h.alive or not h.hittable or id(h) in s[3]:
                    continue
                if abs(math.hypot(h.x - s[0], h.y - s[1]) - s[2]) <= 0.6 + h.hit_radius:
                    s[3].add(id(h))
                    _numbered_hit(h, self.hurt(damage), self, None, ctx)
        self.shocks = [s for s in self.shocks if s[2] < reach]

    def m_beam(self):
        """The great beam: planted, the eye charges along a shown line, fires,
        then drags the beam across the hall (walls and pillars stop it)."""
        t = self.target_now()
        if t is None:
            return
        charge, half, blast, drag, secs, burn, every, after, _, _ = config.WALKER_BEAM
        cx, cy, ra, rb = self.arena()
        reach = 2.2 * max(ra, rb)
        self.planted = True
        self.pose = "beam"
        a = math.atan2(t.y - self.y, t.x - self.x)
        self.facing = a
        charge = self.tell_s(charge)
        w = self.ctx.world
        self.great_beam = [a, -charge, _beam_end(w, self.x, self.y, a, reach)]
        self.ctx.events.append("hex")
        k = 0.0
        while k < charge:
            k += self.dt
            self.great_beam = [a, min(-1e-3, k - charge), _beam_end(w, self.x, self.y, a, reach)]
            yield 0
        length = _beam_end(w, self.x, self.y, a, reach)
        for h in self.heroes():
            if h.hittable and _seg(h.x, h.y, self.x, self.y, a, length) <= half + h.hit_radius:
                _numbered_hit(h, self.hurt(blast), self, a, self.ctx)
        self.ctx.events.append("zap")
        t = self.target_now()
        side = 1.0
        if t is not None:
            off = _wrap(math.atan2(t.y - self.y, t.x - self.x) - a)
            side = 1.0 if off > 0.02 else -1.0 if off < -0.02 else self.rng.choice((-1.0, 1.0))
        burns: dict[int, float] = {}
        f = 0.0
        while f < 1.0:
            f = min(1.0, f + self.dt / secs)
            ang = a + side * math.radians(drag) * f
            length = _beam_end(w, self.x, self.y, ang, reach)
            self.great_beam = [ang, f, length]
            self.facing = ang
            for h in self.heroes():
                if not h.hittable or _seg(h.x, h.y, self.x, self.y, ang, length) > half + h.hit_radius:
                    continue
                left = burns.get(id(h), 0.0) - self.dt
                if left <= 0:
                    left = every
                    _numbered_hit(h, self.hurt(burn), self, ang, self.ctx)
                    self.ctx.events.append("fizzle")
                burns[id(h)] = left
            yield 0
        self.great_beam = None
        yield after
        self.planted = False
        self.pose = ""

    def m_throw(self):
        """Grab and throw: you, if you're near (held, then thrown along a
        shown line; roll free while held); else a piece of the hall, thrown
        at you along a shown line, breaking into cover where it lands."""
        t = self.target_now()
        if t is None:
            return
        if math.hypot(t.x - self.x, t.y - self.y) <= config.WALKER_GRAB[0] + self.hit_radius:
            yield from self._grab(t)
        else:
            yield from self._hurl(t)

    def _grab(self, t):
        _, tell, hand, hold, far, _, _, _, _, _, _ = config.WALKER_GRAB
        tell = self.tell_s(tell)
        hx, hy = t.x, t.y
        self.arm = [hx, hy, 0.0, tell, "grab"]
        self.ctx.events.append("hex")
        k = 0.0
        while k < tell:
            k += self.dt
            self.arm[2] = k
            yield 0
        caught = [h for h in self.heroes()
                  if h.hittable and math.hypot(h.x - hx, h.y - hy) <= hand + h.hit_radius]
        if not caught:
            self.arm = None
            yield 0.3
            return
        h = min(caught, key=lambda o: math.hypot(o.x - hx, o.y - hy))
        self.ctx.effects.append(Effect("toast", h.x, h.y - 2.0, label="GRABBED!"))
        self.ctx.events.append("hit")
        out = math.atan2(h.y - self.y, h.x - self.x)
        ang = out
        for k in range(13):                             # (away from it, kept on the floor)
            for s in (1, -1):
                g = out + s * k * math.radians(15)
                if self.inside(h.x + math.cos(g) * far, h.y + math.sin(g) * far, 3.0):
                    ang = g
                    break
            else:
                continue
            break
        self.grabbed = [h, hold, ang, far]
        self.arm = [h.x, h.y, tell, tell, "hold"]
        self.throw_line = (h.x, h.y, h.x + math.cos(ang) * far, h.y + math.sin(ang) * far)
        while self.grabbed is not None and self.grabbed[1] > 0:
            yield 0
        g = self.grabbed
        self.grabbed = None
        self.arm = None
        if g is None:                                   # (it rolled free)
            self.throw_line = None
            return
        h = g[0]
        self.flung = [h, ang, far / config.WALKER_GRAB[5], config.WALKER_GRAB[6]]
        self.ctx.effects.append(Effect("toast", h.x, h.y - 2.0, label="THROWN!"))
        self.ctx.events.append("boulder")
        yield 0.4
        self.throw_line = None

    def _hurl(self, t):
        reach, line_s = config.WALKER_GRAB[7], config.WALKER_GRAB[8]
        pc = self._nearest_piece(reach)
        if pc is not None:
            px, py, kind = pc[0], pc[1], PIECE_KINDS.get(pc[2], pc[2])
        else:
            a = self.facing + self.rng.uniform(-1.2, 1.2)
            px = self.x + math.cos(a) * (self.hit_radius + 2.0)
            py = self.y + math.sin(a) * (self.hit_radius + 2.0)
            kind = "rubble"
        self.arm = [px, py, 0.0, 0.4, "reach"]
        k = 0.0
        while k < 0.4:
            k += self.dt
            self.arm[2] = k
            yield 0
        if pc is not None:
            self._tear_out(pc)
        else:
            self.ctx.effects.append(Effect("debris", px, py))
        self.arm = None
        self.lifted = kind
        line_s = self.tell_s(line_s)
        lx, ly = self.lead(t, self.x, self.y, secs=line_s + 0.6)
        d = math.hypot(lx - self.x, ly - self.y)
        most = 22.0
        if d > most:
            lx, ly = self.x + (lx - self.x) / d * most, self.y + (ly - self.y) / d * most
        lx, ly = self.clamp_to_lair(lx, ly, 2.0)
        self.throw_line = (self.x, self.y, lx, ly)
        self.ctx.events.append("hex")
        yield line_s
        self.thrown = [self.x, self.y, lx, ly, 0.0, 0.6, kind]
        self.lifted = None
        self.ctx.events.append("whistle")
        yield 0.65
        self.throw_line = None

    def _tick_held(self, ctx, dt: float) -> None:
        g = self.grabbed
        if g is not None:
            h = g[0]
            if not h.alive or h.roll_t > 0:              # (rolled free)
                self.grabbed = None
                if h.alive:
                    ctx.effects.append(Effect("toast", h.x, h.y - 2.0, label="FREE!"))
            else:
                hx, hy = self.body_point(math.atan2(h.y - self.y, h.x - self.x) - self.facing,
                                         1.0 + 1.4 / max(1.0, self.hit_radius))
                self._hold_at(h, hx, hy)
                h.slowed(0.0, 0.1)
                g[1] -= dt
                if self.arm is not None:
                    self.arm[0], self.arm[1] = h.x, h.y
        f = self.flung
        if f is not None:
            h, ang, left, damage = f
            v = config.WALKER_GRAB[5]
            x0, y0 = h.x, h.y
            step = min(0.5, v * dt)
            combat.push(h, ctx.world, math.cos(ang) * step, math.sin(ang) * step, full=True)
            h.slowed(0.0, 0.1)
            f[2] -= dt
            stuck = math.hypot(h.x - x0, h.y - y0) < step * 0.3 or not self.inside(h.x, h.y, 1.5)
            if f[2] <= 0 or stuck or not h.alive:
                self.flung = None
                if h.alive and h.hittable:
                    _numbered_hit(h, self.hurt(damage), self, ang, ctx)
                ctx.effects.append(Effect("debris", h.x, h.y))
                ctx.events.append("boulder")

    def _hold_at(self, h, x: float, y: float) -> None:
        """Pull a held hero toward (x, y), kept on the floor, at most half a
        tile a step (one long shove could jump them through the rim)."""
        x, y = self.clamp_to_lair(x, y, 1.0)
        dx, dy = x - h.x, y - h.y
        d = math.hypot(dx, dy)
        if d > 0.5:
            dx, dy = dx / d * 0.5, dy / d * 0.5
        combat.push(h, self.ctx.world, dx, dy, full=True)

    def _tick_thrown(self, ctx, dt: float) -> None:
        th = self.thrown
        if th is None:
            return
        th[4] += dt
        if th[4] < th[5]:
            return
        self.thrown = None
        x, y = th[2], th[3]
        wide, damage = config.WALKER_GRAB[9], config.WALKER_GRAB[10]
        for h in ctx.players:
            if h.alive and h.hittable and math.hypot(h.x - x, h.y - y) <= wide + h.hit_radius:
                _numbered_hit(h, self.hurt(damage), self, None, ctx)
        ctx.effects.append(Effect("explosion", x, y))
        ctx.events.append("boulder")
        if hasattr(ctx.world, "set_tile"):                # (it breaks into cover)
            self._drop_cover(x, y, tiles.BROKEN_PILLAR, "pillar",
                             ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)))

    def m_swing(self):
        """Arm swing: an arm of chained cell doors swung along an arc shown
        first (roll under it or get out of reach)."""
        t = self.target_now()
        if t is None:
            return
        arc, length, shown, secs, damage, half, knock = config.WALKER_SWING
        aim = math.atan2(t.y - self.y, t.x - self.x)
        side = self.rng.choice((-1, 1))
        a0 = aim - side * math.radians(arc) / 2
        a1 = aim + side * math.radians(arc) / 2
        shown = self.tell_s(shown)
        self.arm_swing = (a0, a1, -1.0, length)
        self.ctx.events.append("hex")
        yield shown
        hit: set[int] = set()
        f = 0.0
        while f < 1.0:
            f = min(1.0, f + self.dt / secs)
            a = a0 + (a1 - a0) * f
            self.arm_swing = (a0, a1, f, length)
            for h in self.heroes():
                if not h.hittable or id(h) in hit:
                    continue
                if _seg(h.x, h.y, self.x, self.y, a, length) <= half + h.hit_radius:
                    hit.add(id(h))
                    push = a + side * math.pi / 2
                    _numbered_hit(h, self.hurt(damage), self, push, self.ctx)
                    combat.push(h, self.ctx.world, math.cos(push) * knock, math.sin(push) * knock)
                    self.ctx.events.append("hit")
            yield 0
        self.arm_swing = None

    def _city_settle(self) -> None:
        """Nothing of a move left standing (it ended)."""
        self.planted = False
        self.pose = ""
        self.great_beam = None
        self.arm_swing = None
        self.striding = None
        self.stomping = False
        self.lifted = None
        if self.grabbed is None:
            self.arm = None

    def _city_gone(self, ctx) -> None:
        """It falls: its eyes close, its moves and its arms are gone (the
        walls stay down)."""
        for e in self.eyes:
            if e.alive:
                e.left = True
                e.hp = 0.0
                e.last_hit_by = None
        self.eyes = []
        self.strikes, self.shocks, self.stomp_marks = [], [], []
        self.great_beam = self.arm_swing = self.arm = None
        self.grabbed = self.flung = self.thrown = None
        self.throw_line = self.lifted = self.building = None
        self.cables = []
        self.plug_to = self.striding = None
        for k in range(len(self.plates)):
            if self.plates[k] is not None:
                x, y = self.body_point(self.slot_angle(k), 1.0)
                ctx.effects.append(Effect("debris", x, y))


# A piece's kind -> the plate it makes.
PIECE_KINDS = {"pillar": "pillar", "door": "door", "screen": "screen", "rubble": "rubble"}


def _seg(x: float, y: float, ox: float, oy: float, angle: float, length: float) -> float:
    """How far (x, y) is from the segment from (ox, oy) along `angle`."""
    ux, uy = math.cos(angle), math.sin(angle)
    f = max(0.0, min(length, (x - ox) * ux + (y - oy) * uy))
    return math.hypot(x - ox - ux * f, y - oy - uy * f)
