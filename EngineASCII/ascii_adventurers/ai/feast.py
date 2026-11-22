"""
ai/feast.py -- Pandemonium's boss, form 1: THE HOST OF THE FEAST, the
gracious host (M30.4, design/OCEAN.md 17.1). A vast demon prince, all
smiles, who throws the endless party: every attack is hospitality.

HE DANCES (user): a waltz the whole fight (HOST_WALTZ: a round whose
middle follows his partner across the hall, turning as he goes, reversing
now and then; far off, he glides over fast). Only the toast and the beckoning plant him, with a clear tell; the
grand spin carries him across the hall instead.

HIS CHARM (user): within HOST_CHARM[0] tiles your temptation fills
(systems/temptation.py asks charm_at); full, you're swept into his dance:
drifting at him -- reach him before you roll out and he spins you away with
a free hit.

A HALL THAT CHANGES (user): each phase is a room (100-67-33%), and each
room brings a signature that keeps going in the rooms after it:
  0 the banquet   a long table down the middle. COURSES SERVED: dishes
                  sent sliding down the table and across the floor, each a
                  hazard read by its look -- soup (a spreading scald pool),
                  the roast (bursts into a ring of bones), jellies (blobs
                  hopping at you), the cake tower (topples along a line).
                  In the later rooms demon waiters bring them in.
  1 the ballroom  a dance floor, mirrors round the wall. THE DANCE FLOOR:
                  its squares light a step pattern a beat ahead; when the
                  beat lands every unlit square burns.
  2 the vault     heaps of gold. THE VAULT'S GOLD: heaps sliding across
                  like walls, coins pouring onto marked circles, and gold
                  tossed to you -- catch a coin for a burst of damage, but
                  each one fills your temptation.
TOASTS in every room: he raises his glass, a wave of wine floods out from
him (roll through it), and every guest in the hall frenzies.
Moves (dance figures, every room): grand spin (a spinning glide flinging
rings of cutlery), the beckoning (a bow; you're pulled at him; a sweeping
slash), carving set (fans of knives curving across each other), chandeliers
(dropped on marked spots, leaving broken glass that cuts).

THE GUESTS (user): a group at each room's edges, in the trance (Pandemonium's
revellers, home ("room", k)): feasters, then dancers, then hoarders. They
wake if you go near, or at his toast; each room's group leaves with the room
(mine) and a new one sits down.

Form 2, the hunger, is M30.5. Drawn by render/feast.py.
"""

from __future__ import annotations

import math
import random

from .. import config
from ..entities.effects import Effect
from ..specs import EnemySpec
from ..systems import combat, patterns
from ..systems.zones import Zone
from ..world import tiles
from . import pandemonium as pand
from .bosses import Boss
from .creatures import _numbered_hit

_TAU = math.tau
ROOMS = ("THE BANQUET", "THE BALLROOM", "THE VAULT")
ROOM_LINES = ("", "the hall becomes a ballroom -- follow the lit steps",
              "the hall becomes a vault -- heaps of gold")
DISHES = ("soup", "roast", "jelly", "cake")


def _seg_dist(px: float, py: float, x0: float, y0: float, x1: float, y1: float) -> float:
    dx, dy = x1 - x0, y1 - y0
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 < 1e-9 else max(0.0, min(1.0, ((px - x0) * dx + (py - y0) * dy) / L2))
    return math.hypot(px - (x0 + dx * t), py - (y0 + dy * t))


def _in_cone(x0, y0, aim, half, reach, x, y) -> bool:
    d = math.hypot(x - x0, y - y0)
    if d > reach:
        return False
    if d < 1e-6:
        return True
    off = (math.atan2(y - y0, x - x0) - aim + math.pi) % _TAU - math.pi
    return abs(off) <= half


class FeastHost(Boss):
    """The Host of the Feast, form 1 (see the module's docstring)."""

    def __init__(self, spec: EnemySpec, x: float, y: float, rng: random.Random,
                 spawn_id=None) -> None:
        super().__init__(spec, x, y, rng, spawn_id, hit_radius=config.HOST_HIT_RADIUS)
        self.shots = config.FEAST_SHOTS
        self.room = -1                    # 0 the banquet, 1 the ballroom, 2 the vault
        self.hall: tuple | None = None    # (cx, cy, a, b, gx, gy)
        self.mid = (x, y)                 # the waltz: its round's middle,
        self.round_a = math.pi / 2        # where on its round
        self.round_dir = 1
        self.round_t = 0.0
        self.planted = False              # the toast, the beckoning: standing still
        self.gliding = False              # the grand spin: carried across the hall
        self.spin = 0.0                   # how far he's turned (drawing)
        self.pose = ""                    # "toast", "bow", "spin" (drawing)
        self.stamped: dict = {}           # (tx, ty) -> the tile the room covered
        self.table: list = []             # the banquet's table: [(x, y)] along it
        self.guests: list = []
        self.guest_home = None
        # What his moves put on the floor (render/feast.py):
        self.dishes: list = []            # [kind, x, y, vx, vy, s left, waiter]
        self.jellies: list = []           # [x, y, hops left, s to the next, x0, y0, x1, y1]
        self.cakes: list = []             # toppling: [x0, y0, x1, y1, s left]
        self.marks: list = []             # [x, y, radius, s left, kind] chandeliers, coins
        self.walls: list = []             # sliding gold: [x0, y0, x1, y1, vx, vy, s left, hit]
        self.coins: list = []             # tossed to you: [x, y, s left]
        self.floor: dict | None = None    # the dance floor (see m_dance)
        self.cone: tuple | None = None    # the beckoning's slash: (angle, reach, half)
        self.pulling = False
        self.carve: float | None = None   # the carving set's aim, while it's shown
        self.waves: list = []             # toasts: [x, y, r, reach, speed, damage, tempt, hit]
        self.banner_req: tuple | None = None   # (title, sub): the quest shows it

    # --- The hall --------------------------------------------------------------------

    def _hall(self) -> tuple:
        if self.hall is None:
            lair = self.lair
            if lair is not None:
                a, b = lair.radii
                gx, gy = lair.props.get("facing", (0.0, -1.0))
                self.hall = (lair.cx, lair.cy, float(a), float(b), gx, gy)
            else:                                     # (a test arena: round where he stands)
                self.hall = (self.x, self.y, 20.0, 14.0, 0.0, -1.0)
        return self.hall

    def _stamp(self, tx: int, ty: int, tile) -> None:
        w = self.ctx.world
        if not hasattr(w, "set_tile"):
            return
        if (tx, ty) not in self.stamped:
            self.stamped[(tx, ty)] = w.tile_at(tx, ty)
        w.set_tile(tx, ty, tile)

    def _clear_room(self) -> None:
        w = self.ctx.world
        if hasattr(w, "set_tile"):
            for (tx, ty), t in self.stamped.items():
                w.set_tile(tx, ty, t)
        self.stamped = {}
        self.table = []

    def _heroes_near(self, tx: int, ty: int, r: float = 1.6) -> bool:
        return any(h.alive and math.hypot(h.x - tx - 0.5, h.y - ty - 0.5) < r
                   for h in self.ctx.players)

    def _enter_room(self, k: int) -> None:
        """The hall becomes room k: its fixtures (only in a real lair), and a
        new group of guests sits down (the last one leaves)."""
        self.room = k
        cx, cy, a, b, gx, gy = self._hall()
        ux, uy = -gy, gx                                  # across the carpet
        self._clear_room()
        if self.lair is not None:
            w = self.ctx.world
            if k == 0:                                    # a long table down the middle
                reach = 0.62 / math.hypot(ux / a, uy / b)
                gap = reach * 0.5
                for s in range(-int(reach), int(reach) + 1):
                    if abs(s) <= 2 or abs(abs(s) - gap) <= 1:
                        continue                          # (gaps to cross: the carpet, two more)
                    tx, ty = math.floor(cx + ux * s), math.floor(cy + uy * s)
                    if not self._heroes_near(tx, ty):
                        self._stamp(tx, ty, tiles.HOST_TABLE)
                        self.table.append((tx + 0.5, ty + 0.5))
            elif k == 1:                                  # the dance floor, mirrors round it
                fa, fb = config.HOST_DANCE[3]
                for j in range(-math.ceil(b), math.ceil(b) + 1):
                    for i in range(-math.ceil(a), math.ceil(a) + 1):
                        tx, ty = math.floor(cx) + i, math.floor(cy) + j
                        t = w.tile_at(tx, ty)
                        if t is tiles.GILT_FLOOR:
                            self._stamp(tx, ty, tiles.MIRROR_PANEL)
                        elif t in (tiles.HALL_FLOOR, tiles.CARPET) \
                                and abs(tx + 0.5 - cx) <= a * fa and abs(ty + 0.5 - cy) <= b * fb:
                            self._stamp(tx, ty, tiles.DANCE_FLOOR)
            else:                                         # heaps of gold
                for n in range(8):
                    ang = (n + 0.5) * _TAU / 8
                    hx, hy = cx + math.cos(ang) * a * 0.55, cy + math.sin(ang) * b * 0.55
                    for i, j in ((0, 0), (1, 0), (0, 1), (1, 1), (-1, 0)):
                        tx, ty = math.floor(hx) + i, math.floor(hy) + j
                        if w.tile_at(tx, ty) is tiles.HALL_FLOOR and not self._heroes_near(tx, ty, 2.2):
                            self._stamp(tx, ty, tiles.COIN_HEAP)
        self._seat_guests(k)
        self.ctx.effects.append(Effect("room_change", self.x, self.y, size=12.0))
        if k > 0:                                         # (the quest shows it as a banner)
            self.banner_req = (ROOMS[k], ROOM_LINES[k])

    def _seat_guests(self, k: int) -> None:
        for e in self.guests:                             # (the last room's group leaves)
            if e.alive:
                e.left = True
                e.hp = 0.0
                e.last_hit_by = None
        self.guests = []
        if self.recruit is None:
            return
        cx, cy, a, b, gx, gy = self._hall()
        home = ("room", k)
        self.guest_home = home
        pand.sites(self.ctx.world)[home] = (cx, cy, "room")
        keys = config.HOST_GUESTS[k]
        n = len(keys)
        side = math.atan2(gy, gx)
        for i, key in enumerate(keys):
            # Along the two long sides, clear of the gate and of his seat.
            half = i % 2
            frac = (i // 2 + 0.5) / ((n + 1) // 2)
            ang = side + math.pi / 2 + (frac - 0.5) * 1.6 + (math.pi if half else 0.0)
            x, y = cx + math.cos(ang) * a * 0.8, cy + math.sin(ang) * b * 0.8
            e = self.recruit(key, x, y)
            if e is None:
                continue
            e.home = home
            e.spawn_pt = (e.x, e.y)
            if hasattr(e, "state"):
                e.state = "serene"
            self.guests.append(e)

    # --- Being the host ----------------------------------------------------------------

    def charm_at(self, h) -> float:
        """How strongly his charm pulls at hero h (0 out of reach .. 1 at
        his side): systems/temptation.py."""
        if not self.alive or not h.alive or not self.in_arena(h):
            return 0.0
        reach = config.HOST_CHARM[0]
        d = math.hypot(h.x - self.x, h.y - self.y)
        if d >= reach:
            return 0.0
        return min(1.0, max(0.0, 1.0 - (d - self.hit_radius) / (reach - self.hit_radius)))

    def on_phase(self, phase: int, ctx) -> None:
        if phase != self.room:
            self._enter_room(min(phase, len(ROOMS) - 1))

    def _settle(self) -> None:
        """Nothing of a move left standing (it ended, or another began)."""
        self.planted = self.gliding = self.pulling = False
        self.pose = ""
        self.cone = None
        self.carve = None
        self.floor = None

    def _start(self, name: str) -> None:
        self._settle()
        super()._start(name)

    def _end_move(self) -> None:
        self._settle()
        super()._end_move()

    def think(self, ctx, dt: float) -> None:
        self.ctx = ctx
        if self.room < 0:
            self._enter_room(0)
        try:
            ctx.world.charmer = self
        except AttributeError:
            pass
        if not (self.planted or self.gliding) and self.dazed <= 0:
            self._waltz(dt)
        super().think(ctx, dt)
        t = self.drift_target()
        if t is not None and not self.gliding:
            self.facing = self.angle_to(t.x, t.y)
        self._free_hit(ctx)
        self._slide_dishes(ctx, dt)
        self._hop_jellies(ctx, dt)
        self._topple(ctx, dt)
        self._drop_marks(ctx, dt)
        self._slide_walls(ctx, dt)
        self._lie_coins(ctx, dt)
        self._tick_waves(ctx, dt)

    def _waltz(self, dt: float) -> None:
        """A waltz round his partner: a round whose middle follows them
        (fast while they're far), turning as he goes, reversing every
        HOST_WALTZ[4] s."""
        speed, (ra, rb), turn_r, turns, flip, follow, catch = config.HOST_WALTZ
        self.round_t += dt
        if self.round_t >= flip:
            self.round_t = 0.0
            self.round_dir = -self.round_dir
        mx, my = self.mid
        t = self.drift_target()
        if t is not None:
            d = math.hypot(t.x - mx, t.y - my)
            if d > 1e-6:
                step = min(d, (follow + catch * max(0.0, d - ra)) * dt)
                mx, my = mx + (t.x - mx) / d * step, my + (t.y - my) / d * step
        self.mid = self.clamp_to_lair(mx, my, rb + self.hit_radius + 1.0)
        mx, my = self.mid
        self.round_a += self.round_dir * speed / ((ra + rb) / 2) * dt
        whirl = self.time * turns * _TAU
        px = mx + math.cos(self.round_a) * ra + math.cos(whirl) * turn_r
        py = my + math.sin(self.round_a) * rb + math.sin(whirl) * turn_r
        far = math.hypot(px - self.x, py - self.y)
        self._glide_to(px, py, max(speed * 1.6, far * 1.5), dt)

    def _glide_to(self, x: float, y: float, v: float, dt: float) -> None:
        dx, dy = x - self.x, y - self.y
        d = math.hypot(dx, dy)
        step = min(d, v * dt)
        if d > 1e-6:
            nx, ny = self.x + dx / d * step, self.y + dy / d * step
            self.x, self.y = self.clamp_to_lair(nx, ny, self.hit_radius + 1.0)

    def _free_hit(self, ctx) -> None:
        """A hero swept into his dance who reaches him is spun away, hurt."""
        _, _, damage, throw = config.HOST_CHARM
        for h in ctx.players:
            if not h.alive or getattr(h, "swept", None) is not self or h.entranced <= 0:
                continue
            d = math.hypot(h.x - self.x, h.y - self.y)
            if d > self.hit_radius + h.hit_radius + 0.8:
                continue
            a = math.atan2(h.y - self.y, h.x - self.x)
            if h.hittable:
                _numbered_hit(h, damage * self.damage_mult, self, a, ctx)
            combat.push(h, ctx.world, math.cos(a) * throw, math.sin(a) * throw)
            h.entranced = 0.0
            h.swept = None
            ctx.effects.append(Effect("toast", h.x, h.y - 1.5, label="SPUN AWAY!"))
            ctx.effects.append(Effect("swing", self.x, self.y, angle=a, size=self.hit_radius + 2.0,
                                      value=160))
            ctx.events.append("swing")

    def _hit(self, h, damage: float, x: float, y: float) -> None:
        if h.hittable:
            _numbered_hit(h, damage * self.damage_mult, self, math.atan2(h.y - y, h.x - x), self.ctx)

    def on_death(self, ctx) -> None:
        super().on_death(ctx)
        if getattr(ctx.world, "charmer", None) is self:
            ctx.world.charmer = None
        for h in ctx.players:
            if getattr(h, "swept", None) is self:
                h.swept = None
                h.entranced = 0.0
        self.dishes, self.jellies, self.cakes, self.marks = [], [], [], []
        self.walls, self.coins, self.waves, self.floor = [], [], [], None

    # --- Signature 1: courses served ----------------------------------------------------

    def m_courses(self):
        n, every, speed, most, _, out = config.HOST_COURSES
        self.tell = ("courses",)
        self.ctx.effects.append(Effect("toast", self.x, self.y - 4, label="DINNER IS SERVED!"))
        yield self.tell_s(0.5)
        for k in range(n):
            t = self.target_now()
            if t is None:
                return
            kind = self.rng.choice(DISHES)
            waiter = self.room > 0 or not self.table
            if waiter:                                # (a demon waiter brings it in)
                ang = self.rng.uniform(0, _TAU)
                x0, y0 = self.clamp_to_lair(t.x + math.cos(ang) * out, t.y + math.sin(ang) * out,
                                            2.0)
            else:                                     # (sent sliding down the table toward you)
                near = sorted(self.table, key=lambda q: math.hypot(q[0] - t.x, q[1] - t.y))[:12]
                x0, y0 = self.rng.choice(near)
            tx, ty = self.lead(t, x0, y0, speed)
            d = math.hypot(tx - x0, ty - y0) or 1.0
            secs = min(most, d / speed)
            self.dishes.append([kind, x0, y0, (tx - x0) / d * speed, (ty - y0) / d * speed, secs,
                                waiter])
            self.ctx.events.append("swing")
            yield every

    def _slide_dishes(self, ctx, dt: float) -> None:
        dmg = config.HOST_COURSES[4]
        keep = []
        for d in self.dishes:
            d[1] += d[3] * dt
            d[2] += d[4] * dt
            d[5] -= dt
            for h in ctx.players:                     # (one running into you)
                if h.alive and math.hypot(h.x - d[1], h.y - d[2]) <= h.hit_radius + 0.6:
                    self._hit(h, dmg, d[1] - d[3], d[2] - d[4])
                    d[5] = 0.0
            if d[5] > 0:
                keep.append(d)
            else:
                self._serve(ctx, d[0], d[1], d[2])
        self.dishes = keep

    def _serve(self, ctx, kind: str, x: float, y: float) -> None:
        """A dish comes to rest and does what it does."""
        if kind == "soup":
            r0, grow, life, every, damage = config.HOST_SOUP
            if ctx.zones is not None:
                ctx.zones.append(Zone("scald", x, y, r0, life, every, damage * self.damage_mult,
                                      self, grow=grow))
        elif kind == "roast":
            patterns.radial(self, x, y, config.HOST_ROAST, self.shots["bone"], ctx.projectiles,
                            turn=self.rng.uniform(0, _TAU))
            ctx.effects.append(Effect("explosion", x, y))
        elif kind == "jelly":
            n, hops, every, *_ = config.HOST_JELLY
            for k in range(n):
                self.jellies.append([x + math.cos(k * _TAU / n) * 0.6,
                                     y + math.sin(k * _TAU / n) * 0.6, hops, every * (1 + k * 0.3),
                                     x, y, x, y])
        elif kind == "cake":
            length, shown, *_ = config.HOST_CAKE
            t = self.drift_target()
            a = math.atan2(t.y - y, t.x - x) if t is not None else self.rng.uniform(0, _TAU)
            self.cakes.append([x, y, x + math.cos(a) * length, y + math.sin(a) * length, shown])

    def _hop_jellies(self, ctx, dt: float) -> None:
        _, _, every, far, radius, damage = config.HOST_JELLY
        keep = []
        for j in self.jellies:
            j[3] -= dt
            if j[3] <= 0:                             # (lands where its shadow was)
                j[0], j[1] = j[6], j[7]
                for h in ctx.players:
                    if h.alive and math.hypot(h.x - j[0], h.y - j[1]) <= radius + h.hit_radius:
                        self._hit(h, damage, j[0], j[1])
                j[2] -= 1
                if j[2] <= 0:
                    ctx.effects.append(Effect("jelly_splat", j[0], j[1], size=radius))
                    continue
                t = min((h for h in ctx.players if h.alive),
                        key=lambda h: math.hypot(h.x - j[0], h.y - j[1]), default=None)
                j[4], j[5] = j[0], j[1]
                if t is not None:
                    d = math.hypot(t.x - j[0], t.y - j[1]) or 1.0
                    hop = min(far, d)
                    j[6], j[7] = self.clamp_to_lair(j[0] + (t.x - j[0]) / d * hop,
                                                    j[1] + (t.y - j[1]) / d * hop, 1.0)
                j[3] = every
            keep.append(j)
        self.jellies = keep

    def _topple(self, ctx, dt: float) -> None:
        _, _, half, damage = config.HOST_CAKE
        keep = []
        for c in self.cakes:
            c[4] -= dt
            if c[4] > 0:
                keep.append(c)
                continue
            for h in ctx.players:
                if h.alive and _seg_dist(h.x, h.y, *c[:4]) <= half + h.hit_radius:
                    self._hit(h, damage, c[0], c[1])
            ctx.effects.append(Effect("cake_fall", c[0], c[1], x2=c[2], y2=c[3]))
            ctx.events.append("boulder")
        self.cakes = keep

    # --- Signature 2: the dance floor --------------------------------------------------

    def floor_rect(self) -> tuple[float, float, float, float]:
        """The dance floor: (x0, y0, x1, y1) in world tiles."""
        cx, cy, a, b, _, _ = self._hall()
        fa, fb = config.HOST_DANCE[3]
        return cx - a * fa, cy - b * fb, cx + a * fa, cy + b * fb

    def square_of(self, x: float, y: float) -> tuple[int, int] | None:
        x0, y0, x1, y1 = self.floor_rect()
        if not (x0 <= x < x1 and y0 <= y < y1):
            return None
        size = config.HOST_DANCE[2]
        return int((x - x0) // size), int((y - y0) // size)

    def _steps(self, pattern: str, beat: int) -> set:
        """Which squares are lit on this beat of this pattern."""
        x0, y0, x1, y1 = self.floor_rect()
        size = config.HOST_DANCE[2]
        nx, ny = math.ceil((x1 - x0) / size), math.ceil((y1 - y0) / size)
        lit = set()
        hx, hy = self.square_of(self.x, self.y) or (nx // 2, ny // 2)
        for j in range(ny):
            for i in range(nx):
                if pattern == "checker":
                    on = (i + j + beat) % 2 == 0
                elif pattern == "rows":
                    on = (j + beat) % 2 == 0
                elif pattern == "cols":
                    on = (i + beat) % 2 == 0
                else:                                 # "rings" round him
                    on = (max(abs(i - hx), abs(j - hy)) + beat) % 2 == 0
                if on:
                    lit.add((i, j))
        return lit

    def m_dance(self):
        beats, every, *_ = config.HOST_DANCE
        damage = config.HOST_DANCE[4]
        pattern = self.rng.choice(("checker", "rows", "cols", "rings"))
        self.tell = ("dance",)
        self.ctx.effects.append(Effect("toast", self.x, self.y - 4, label="SHALL WE DANCE?"))
        self.floor = {"now": set(), "next": self._steps(pattern, 0), "beat": every, "every": every,
                      "pattern": pattern, "landed": 0}
        yield self.tell_s(every)
        for k in range(beats):
            fl = self.floor
            fl["now"] = fl["next"]
            fl["next"] = self._steps(pattern, k + 1) if k + 1 < beats else set()
            for h in self.heroes():                   # (the beat lands: unlit squares burn)
                sq = self.square_of(h.x, h.y)
                if sq is not None and sq not in fl["now"]:
                    self._hit(h, damage, h.x, h.y - 1)
            fl["landed"] += 1
            self.ctx.effects.append(Effect("beat", self.x, self.y, size=3.0))
            self.ctx.events.append("hit")
            fl["beat"] = every
            left = every
            while left > 0:
                left -= self.dt
                fl["beat"] = left
                yield 0
        self.floor = None

    # --- Signature 3: the vault's gold -------------------------------------------------

    def m_gold(self):
        heaps, length, speed, _, _, out = config.HOST_WALLS
        circles, shown, radius, _ = config.HOST_POUR
        coins, life, *_ = config.HOST_TOSS
        t = self.target_now()
        if t is None:
            return
        self.tell = ("gold",)
        self.ctx.effects.append(Effect("toast", self.x, self.y - 4, label="HAVE SOME GOLD!"))
        # Heaps sliding in from both sides at once, closing a lane on you.
        ang = self.rng.choice((0.0, math.pi / 2))
        ux, uy = math.cos(ang), math.sin(ang)             # the way they slide
        vx, vy = -uy, ux                                  # along a heap
        for k in range(heaps):
            side = -1 if k % 2 == 0 else 1
            off = (k // 2) * length * side
            sx, sy = t.x + ux * side * out + vx * off, t.y + uy * side * out + vy * off
            self.walls.append([sx - vx * length / 2, sy - vy * length / 2,
                               sx + vx * length / 2, sy + vy * length / 2,
                               -ux * side * speed, -uy * side * speed, 2 * out / speed, set()])
        yield 0.6
        # Coins pouring onto marked circles, one on you.
        spots = [(t.x, t.y)]
        for _ in range(circles - 1):
            r = self.rng.uniform(3.0, 9.0)
            q = self.rng.uniform(0, _TAU)
            spots.append(self.clamp_to_lair(t.x + math.cos(q) * r, t.y + math.sin(q) * r, 2.0))
        for x, y in spots:
            self.marks.append([x, y, radius, shown, "coins"])
        yield 0.6
        # And gold tossed to you, lying there to be caught.
        for k in range(coins):
            q = self.rng.uniform(0, _TAU)
            r = self.rng.uniform(2.5, 5.0)
            x, y = self.clamp_to_lair(t.x + math.cos(q) * r, t.y + math.sin(q) * r, 2.0)
            self.coins.append([x, y, life])
        self.ctx.events.append("chime")
        yield 0.5

    def _slide_walls(self, ctx, dt: float) -> None:
        _, _, _, half, damage, _ = config.HOST_WALLS
        keep = []
        for w in self.walls:
            for k in (0, 2):
                w[k] += w[4] * dt
                w[k + 1] += w[5] * dt
            w[6] -= dt
            for h in ctx.players:
                if not h.alive or combat.drafting(h):
                    continue
                if _seg_dist(h.x, h.y, *w[:4]) > half + h.hit_radius:
                    continue
                v = math.hypot(w[4], w[5]) or 1.0
                combat.push(h, ctx.world, w[4] / v * (v * dt + 0.2), w[5] / v * (v * dt + 0.2),
                            full=True)
                if id(h) not in w[7]:
                    w[7].add(id(h))
                    self._hit(h, damage, h.x - w[4], h.y - w[5])
            if w[6] > 0:
                keep.append(w)
        self.walls = keep

    def _lie_coins(self, ctx, dt: float) -> None:
        from ..systems import temptation
        _, _, gilt, _, tempt = config.HOST_TOSS
        keep = []
        for c in self.coins:
            c[2] -= dt
            caught = next((h for h in ctx.players
                           if h.alive and math.hypot(h.x - c[0], h.y - c[1]) <= h.hit_radius + 0.7),
                          None)
            if caught is not None:
                caught.gilt_until = getattr(caught, "time", 0.0) + gilt
                temptation.add(caught, tempt)
                ctx.effects.append(Effect("toast", caught.x, caught.y - 1.5, label="GILDED!"))
                ctx.events.append("chime")
                continue
            if c[2] > 0:
                keep.append(c)
        self.coins = keep

    # --- Toasts (every room) ------------------------------------------------------------

    def m_toast(self):
        raised, reach, speed, damage, tempt = config.HOST_TOAST
        self.planted = True
        self.pose = "toast"
        self.tell = ("toast",)
        self.ctx.effects.append(Effect("toast", self.x, self.y - 4, label="A TOAST!"))
        yield self.tell_s(raised)
        self.waves.append([self.x, self.y, 0.0, reach, speed, damage, tempt, set()])
        self.ctx.effects.append(Effect("host_toast", self.x, self.y, size=reach))
        self.ctx.events.append("hex")
        if self.guest_home is not None:
            pand.frenzy(self.ctx.world, self.guest_home)   # (every guest in the hall)
        self.pose = ""
        yield 0.4

    def _tick_waves(self, ctx, dt: float) -> None:
        from ..systems import temptation
        for w in self.waves:
            w[2] += w[4] * dt
            for h in ctx.players:
                if id(h) in w[7] or not h.alive:
                    continue
                if math.hypot(h.x - w[0], h.y - w[1]) - h.hit_radius > w[2]:
                    continue
                w[7].add(id(h))
                if h.hittable:                        # (mid-roll, it washes past)
                    self._hit(h, w[5], w[0], w[1])
                    temptation.add(h, w[6])
        self.waves = [w for w in self.waves if w[2] < w[3]]

    # --- The dance figures ---------------------------------------------------------------

    def m_spin(self):
        secs, speed, every, n = config.HOST_SPIN
        t = self.target_now()
        if t is None:
            return
        self.tell = ("spin",)
        self.pose = "spin"
        yield self.tell_s(0.5)
        self.gliding = True
        a = self.angle_to(t.x, t.y)
        left, nxt, turn = secs, 0.0, 0.0
        while left > 0:
            dt = self.dt
            nx, ny = self.x + math.cos(a) * speed * dt, self.y + math.sin(a) * speed * dt
            x, y = self.clamp_to_lair(nx, ny, self.hit_radius + 1.0)
            if abs(x - nx) + abs(y - ny) > 1e-6:      # (the wall: off toward his partner again)
                tt = self.target_now()
                if tt is not None:
                    a = self.angle_to(tt.x, tt.y) + self.rng.uniform(-0.4, 0.4)
            self.x, self.y = x, y
            self.spin += dt * 14.0
            self.facing = self.spin
            nxt -= dt
            if nxt <= 0 and self.room_for_shots():
                patterns.radial(self, self.x, self.y, n, self.shots["cutlery"], self.ctx.projectiles,
                                turn=turn)
                turn += math.pi / n
                nxt = every
                self.ctx.events.append("axe")
            left -= dt
            yield 0

    def m_beckon(self):
        bow, pull, reach, speed, slash, half_deg, damage = config.HOST_BECKON
        t = self.target_now()
        if t is None:
            return
        half = math.radians(half_deg)
        self.planted = True
        self.pose = "bow"
        self.tell = ("beckon",)
        self.cone = (self.angle_to(t.x, t.y), slash, half)
        self.ctx.effects.append(Effect("toast", self.x, self.y - 4, label="MAY I HAVE THIS DANCE?"))
        yield self.tell_s(bow)
        self.pulling = True
        left = pull
        while left > 0:
            dt = self.dt
            for h in self.heroes():
                d = math.hypot(self.x - h.x, self.y - h.y)
                if d > reach or d < self.hit_radius + h.hit_radius + 0.5 or combat.drafting(h):
                    continue
                combat.push(h, self.ctx.world, (self.x - h.x) / d * speed * dt,
                            (self.y - h.y) / d * speed * dt, full=True)
            tt = self.target_now()
            if tt is not None:
                self.cone = (self.angle_to(tt.x, tt.y), slash, half)
            left -= dt
            yield 0
        self.pulling = False
        a, r, half = self.cone
        for h in self.heroes():
            if _in_cone(self.x, self.y, a, half, r + h.hit_radius, h.x, h.y):
                self._hit(h, damage, self.x, self.y)
        self.ctx.effects.append(Effect("swing", self.x, self.y, angle=a, size=r,
                                       value=round(math.degrees(half) * 2)))
        self.ctx.events.append("swing")
        self.cone = None
        self.pose = ""
        yield 0.35

    def m_carving(self):
        volleys, n, spread_deg, curve, every = config.HOST_CARVING
        shell = self.shots["carving"]
        spread = math.radians(spread_deg)
        for v in range(volleys):
            t = self.target_now()
            if t is None:
                return
            a = self.aim(t, self.x, self.y, shell.speed)
            self.carve = a
            self.tell = ("carve",)
            yield self.tell_s(0.45)
            for side in (-1, 1):                      # (two fans, curving across each other)
                for k in range(n):
                    b = a - side * spread * 0.3 + spread * 0.5 * (k / (n - 1) - 0.5)
                    p = patterns.shoot(self, self.x, self.y, b, shell, self.ctx.projectiles)
                    p.curve = side * curve
                    p.curve_left = spread * 0.6
            self.carve = None
            self.ctx.events.append("swing")
            yield every

    def m_chandeliers(self):
        n, shown, radius, *_ = config.HOST_CHANDELIERS
        t = self.target_now()
        if t is None:
            return
        self.tell = ("chandeliers",)
        spots = [(t.x, t.y)]
        for _ in range(n - 1):
            r = self.rng.uniform(3.5, 10.0)
            q = self.rng.uniform(0, _TAU)
            spots.append(self.clamp_to_lair(t.x + math.cos(q) * r, t.y + math.sin(q) * r, 2.0))
        for x, y in spots:
            self.marks.append([x, y, radius, shown, "chandelier"])
        yield self.tell_s(0.4)

    def _drop_marks(self, ctx, dt: float) -> None:
        _, _, _, c_damage, glass, life, every, g_damage = config.HOST_CHANDELIERS
        p_damage = config.HOST_POUR[3]
        keep = []
        for m in self.marks:
            m[3] -= dt
            if m[3] > 0:
                keep.append(m)
                continue
            x, y, r, _, kind = m
            for h in ctx.players:
                if h.alive and math.hypot(h.x - x, h.y - y) <= r + h.hit_radius:
                    self._hit(h, c_damage if kind == "chandelier" else p_damage, x, y)
            if kind == "chandelier":
                ctx.effects.append(Effect("chandelier_crash", x, y, size=r))
                if ctx.zones is not None:
                    ctx.zones.append(Zone("broken_glass", x, y, glass, life, every,
                                          g_damage * self.damage_mult, self))
                ctx.events.append("break")
            else:
                ctx.effects.append(Effect("coin_burst", x, y, size=r))
        self.marks = keep
