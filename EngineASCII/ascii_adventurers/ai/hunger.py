"""
ai/hunger.py -- Pandemonium's boss, form 2: THE HUNGER (M30.5,
design/OCEAN.md 17.2). At 0 the gracious host's mask cracks, the table
collapses, and he becomes a devouring thing that eats the feast and the
guests to grow. A mix-in of ai/feast.FeastHost (one body, two forms, like
the necromancer's two lives); drawn by render/feast.py.

THE MASK CRACKS: HUNGER_CRACK s in which he can't be hit while the hall
falls into the wine round him, the middle first: islands of table, floor and
gold (mine: a jittered grid of round islands, HUNGER_ISLANDS) in spilt wine
that heroes wade slowly; he moves through it freely. Then he's back at full
health (x HUNGER_HP: 14,000 of 12,000) with four phases (100-75-50-25%), a
signature added in each:
  1 DEVOUR         he eats whatever he reaches: his guests, scraps of the
                   feast, his own demon waiters. Each meal heals him and
                   makes him bigger and stronger (the count shows on his
                   bar), up to HUNGER_DEVOUR[3] meals. Clear the food first.
  2 THE MAW        a cone shown, then he inhales: a pull across it (on meals
                   too). Reach his mouth and you're swallowed: chewed, then
                   spat out across the hall.
  3 TEETH          rows of teeth burst up and snap shut along marked lines
                   crossing near you, wave after wave, turned each time.
  4 SPILLED FEAST  half-eaten feast heaved in arcs onto marked spots: rotting
                   pools that slow and burn, fill your temptation, and frenzy
                   the guests near them.
Moves: lunge bite (a marked line, a lunge along it, a bite), tongue lash (it
catches you and drags you in unless you roll free), belly quake (shockwave
rings), bone scraps (fans of bones that stay on the floor as clutter you
trip over). No charm (user): his danger is his hunger.

What there is to eat (mine): the feast scattered when the table collapsed
(walk into a scrap or shoot it to knock it into the wine), the guests
feasting on the islands in pairs (Pandemonium's revellers, in the trance
until you come near, they're hit, or a rotting pool lands by them), and
demon waiters bringing him a course every HUNGER_FEAST[3] s. He prowls round
his prey, unless a meal is near: then he goes for it.
"""

from __future__ import annotations

import math
import random

from .. import config
from ..entities.effects import Effect
from ..systems import combat, patterns
from ..systems.zones import Zone
from ..world import tiles
from . import pandemonium as pand
from .bosses import Boss
from .creatures import _numbered_hit
from .plains import PlainsCreature

_TAU = math.tau
SCRAPS = ("soup", "roast", "jelly", "cake")
# The hall's floor: what falls into the wine (his seat and the walls stay).
FLOORS = (tiles.HALL_FLOOR, tiles.CARPET, tiles.GILT_FLOOR)
ISLES = {"table": tiles.TABLE_WRECK, "gold": tiles.COINS}   # (a floor island stays floor)


def _in_cone(x0, y0, aim, half, reach, x, y) -> bool:
    d = math.hypot(x - x0, y - y0)
    if d > reach:
        return False
    if d < 1e-6:
        return True
    off = (math.atan2(y - y0, x - x0) - aim + math.pi) % _TAU - math.pi
    return abs(off) <= half


class HungerForm:
    """Form 2 of ai/feast.FeastHost (see the module's docstring)."""

    def _init_hunger(self) -> None:
        self.crack_t = 0.0                # s of the mask cracking left
        self.crack_rows: list = []        # the hall's rows still to fall (the middle last in)
        self.crack_plan = None            # (islands by cell, cell size)
        self.meals = 0                    # meals that made him grow (his bar shows it)
        self.eaten = 0                    # everything he's eaten
        self.scraps: list = []            # the feast lying about: [x, y, kind]
        self.waiters: list = []
        self.serve_t = 0.0
        self.prowl_dir = 1
        self.prowl_t = 0.0
        # What his moves show (render/feast.py):
        self.lunge: tuple | None = None   # the lunge's marked line (x0, y0, x1, y1)
        self.tongue: dict | None = None   # {"a", "len", "aiming", "held", "meal"}
        self.maw: dict | None = None      # {"a", "reach", "half", "on"}
        self.swallowed: dict = {}         # id -> [hero, s left, s to the next bite, bites left]
        self.spat: dict = {}              # id -> [hero, vx, vy, s left]
        self.teeth: list = []             # [x0, y0, x1, y1, s to the snap, s since it]
        self.teeth_hit: dict = {}         # hero id -> clock of its last bite (one a snap)
        self.globs: list = []             # spilled feast in the air: [x0, y0, x1, y1, s left, of]
        self.quakes: list = []            # rings: [x, y, r, reach, speed, damage, hit]
        self.bones: list = []             # bone scraps in flight (they land as clutter)
        self.rot_t = 0.0
        self.chew_t = 0.0                 # s still chewing his last meal (he stands there)

    # --- Being the hunger ---------------------------------------------------------------

    @property
    def bar_label(self) -> str | None:
        if getattr(self, "form", 1) != 2:
            return None                   # (the HUD's own: his name)
        return "The Hunger" + (f" - fed {self.meals}" if self.meals else "")

    @property
    def hittable(self) -> bool:
        return Boss.hittable.fget(self) and getattr(self, "form", 1) != "cracking"

    def growth(self) -> float:
        """x his size and damage: HUNGER_DEVOUR[2] more a meal."""
        return 1.0 + config.HUNGER_DEVOUR[2] * self.meals if self.form == 2 else 1.0

    def take_damage(self, amount, source, from_angle):
        if self.form == "cracking":
            return 0.0
        dealt = super().take_damage(amount, source, from_angle)
        if self.form == 1 and self.hp <= 0:           # (the first time: the mask cracks)
            self.hp = 1.0
            self._crack()
        return dealt

    def shove_heroes(self, extra: float = 0.3) -> None:
        """His body pushes heroes out -- not those inside him, or flying."""
        if self.airborne > 0 or self.submerged:
            return
        held = set(self.swallowed) | set(self.spat)
        if self.tongue is not None and self.tongue["held"] is not None:
            held.add(id(self.tongue["held"]))
        for h in self.ctx.players:
            if not h.alive or combat.drafting(h) or id(h) in held:
                continue
            dx, dy = h.x - self.x, h.y - self.y
            d = math.hypot(dx, dy)
            room = self.hit_radius + h.hit_radius + extra
            if d >= room:
                continue
            if d < 1e-6:
                dx, dy, d = math.cos(self.facing + math.pi), math.sin(self.facing + math.pi), 1.0
            combat.push(h, self.ctx.world, dx / d * (room - d), dy / d * (room - d), full=True)

    def _hunger_phase(self, phase: int, ctx) -> None:
        label = {1: "HE OPENS HIS MAW", 2: "THE FLOOR GROWS TEETH",
                 3: "HE HEAVES UP THE FEAST"}.get(phase)
        if label:
            ctx.effects.append(Effect("toast", self.x, self.y - self.hit_radius - 3, label=label))

    def _settle_hunger(self) -> None:
        self.lunge = None
        self.tongue = None
        self.maw = None

    # --- The mask cracks ----------------------------------------------------------------

    def _crack(self) -> None:
        """His health is gone the first time: whatever he was doing stops,
        his hospitality is cleared away, and the hall starts to fall."""
        ctx = self.ctx
        self.form = "cracking"
        self.crack_t = config.HUNGER_CRACK
        self._gen = None
        self.move = None
        self.tell = None
        self._settle()
        self.pose = "crack"
        self.dishes, self.jellies, self.cakes, self.marks = [], [], [], []
        self.walls, self.coins, self.waves = [], [], []
        self.banner_req = ("THE MASK CRACKS", "the hall falls into the wine")
        if ctx is None:
            return
        if getattr(ctx.world, "charmer", None) is self:
            ctx.world.charmer = None
        for h in ctx.players:
            if getattr(h, "swept", None) is self:
                h.swept = None
                h.entranced = 0.0
        ctx.effects.append(Effect("gold_crack", self.x, self.y - 2, size=6.0))
        ctx.effects.append(Effect("room_change", self.x, self.y, size=14.0))
        ctx.events.append(combat.BREAK)
        self._plan_islands()

    def _plan_islands(self) -> None:
        """Where the islands will be: a jittered grid of round ones (only in
        a real lair), each table, floor or gold."""
        self._clear_room()
        self.crack_rows = []
        if self.lair is None or not hasattr(self.ctx.world, "set_tile"):
            return
        cx, cy, a, b, _, _ = self._hall()
        sp, jit, (r0, r1), _ = config.HUNGER_ISLANDS
        rng = random.Random(self.rng.random())
        cells: dict = {}
        rows, cols = math.ceil(b / (sp * 0.87)) + 1, math.ceil(a / sp) + 1
        for j in range(-rows, rows + 1):
            for i in range(-cols, cols + 1):
                x = cx + (i + (0.5 if j % 2 else 0.0)) * sp + rng.uniform(-jit, jit)
                y = cy + j * sp * 0.87 + rng.uniform(-jit, jit)
                if ((x - cx) / a) ** 2 + ((y - cy) / b) ** 2 > 1.0:
                    continue
                isle = (x, y, rng.uniform(r0, r1), rng.choice(("table", "floor", "floor", "gold")))
                cells.setdefault((math.floor(x / sp), math.floor(y / sp)), []).append(isle)
        self.crack_plan = (cells, sp)
        y0, y1 = math.floor(cy - b), math.ceil(cy + b)
        # (popped from the end: the rows nearest the middle fall first)
        self.crack_rows = sorted(range(y0, y1 + 1), key=lambda ty: -abs(ty + 0.5 - cy))

    def _island_at(self, x: float, y: float):
        cells, sp = self.crack_plan
        ci, cj = math.floor(x / sp), math.floor(y / sp)
        for i in (ci - 1, ci, ci + 1):
            for j in (cj - 1, cj, cj + 1):
                for isle in cells.get((i, j), ()):
                    if (x - isle[0]) ** 2 + (y - isle[1]) ** 2 <= isle[2] ** 2:
                        return isle
        return None

    def _sink_row(self, ty: int) -> None:
        cx, cy, a, b, _, _ = self._hall()
        w = self.ctx.world
        k = 1.0 - ((ty + 0.5 - cy) / b) ** 2
        if k <= 0:
            return
        half = a * math.sqrt(k)
        for tx in range(math.floor(cx - half), math.ceil(cx + half) + 1):
            if w.tile_at(tx, ty) not in FLOORS:
                continue
            isle = self._island_at(tx + 0.5, ty + 0.5)
            if isle is None:
                self._stamp(tx, ty, tiles.HALL_WINE)
            elif isle[3] in ISLES:
                self._stamp(tx, ty, ISLES[isle[3]])

    def _crack_step(self, ctx, dt: float) -> None:
        """The hall falling, a few rows a step, over the crack."""
        self.crack_t -= dt
        steps = max(1, round(self.crack_t / max(dt, 1e-6)))
        n = len(self.crack_rows) if self.crack_t <= 0 else math.ceil(len(self.crack_rows) / steps)
        for _ in range(n):
            self._sink_row(self.crack_rows.pop())
        if int(self.time * 5) != int((self.time - dt) * 5):
            a = self.rng.uniform(0, _TAU)
            r = self.rng.uniform(3.0, 14.0)
            ctx.effects.append(Effect("spill", self.x + math.cos(a) * r, self.y + math.sin(a) * r,
                                      size=1.5))
        if self.crack_t <= 0:
            self._become_hunger(ctx)

    def _become_hunger(self, ctx) -> None:
        while self.crack_rows:
            self._sink_row(self.crack_rows.pop())
        self.form = 2
        self.pose = ""
        self.bspec = config.BOSSES["host_hunger"]
        self.phase = 0
        self.max_hp = round(self.max_hp * config.HUNGER_HP)
        self.hp = float(self.max_hp)
        self.hit_radius = config.HUNGER_HIT_RADIUS
        self.meals = 0
        self.serve_t = config.HUNGER_FEAST[3] * 0.5
        self._rest = 1.5
        self.combo = 0
        self.last_move = None
        self._scatter_scraps(ctx)
        self._seat_hungry(ctx)
        self.banner_req = ("THE HUNGER", "kill his guests and clear the food before he eats them")
        ctx.effects.append(Effect("nova", self.x, self.y, size=8.0))
        ctx.events.append("boulder")

    def _land(self, x: float, y: float) -> bool:
        t = self.ctx.world.tile_at(math.floor(x), math.floor(y))
        return not t.solid and t is not tiles.HALL_WINE

    def _open_spot(self, x: float, y: float, land: bool = False) -> tuple[float, float]:
        """The nearest open ground to (x, y) (an island's, for `land`)."""
        w = self.ctx.world
        for r in range(0, 7):
            n = max(1, r * 6)
            for k in range(n):
                px = x + math.cos(k * _TAU / n) * r
                py = y + math.sin(k * _TAU / n) * r
                if self.lair is not None and not self.lair.inside(px, py, 2.0):
                    continue
                t = w.tile_at(math.floor(px), math.floor(py))
                if not t.solid and not (land and t is tiles.HALL_WINE):
                    return px, py
        return x, y

    def _scatter_scraps(self, ctx) -> None:
        """The table collapsed: its feast lies scattered on the islands."""
        n, near = config.HUNGER_FEAST[:2]
        for _ in range(n):
            x, y = self.x, self.y
            for _ in range(30):
                a, r = self.rng.uniform(0, _TAU), self.rng.uniform(6.0, near)
                x, y = self.clamp_to_lair(self.x + math.cos(a) * r, self.y + math.sin(a) * r, 2.0)
                if self._land(x, y) and not any(
                        math.hypot(h.x - x, h.y - y) < 3.0 for h in ctx.players if h.alive):
                    break
            self.scraps.append([x, y, self.rng.choice(SCRAPS)])

    def _seat_hungry(self, ctx) -> None:
        """The last room's guests leave; HUNGER_GUESTS sit down in pairs on
        the islands round him, still feasting (each pair a group of its own,
        a scrap in front of it)."""
        for e in self.guests:
            if e.alive:
                e.left = True
                e.hp = 0.0
                e.last_hit_by = None
        self.guests = []
        self.guest_home = None
        if self.recruit is None:
            return
        keys = config.HUNGER_GUESTS
        lo, hi = config.HUNGER_FEAST[2]
        pairs = math.ceil(len(keys) / 2)
        turn = self.rng.uniform(0, _TAU)
        for p in range(pairs):
            a = turn + p * _TAU / pairs + self.rng.uniform(-0.3, 0.3)
            r = self.rng.uniform(lo, hi)
            x, y = self.clamp_to_lair(self.x + math.cos(a) * r, self.y + math.sin(a) * r, 3.0)
            x, y = self._open_spot(x, y, land=True)
            home = ("feast", p)
            pand.sites(ctx.world)[home] = (x, y + 1.0, "feast")
            for k, key in enumerate(keys[p * 2:p * 2 + 2]):
                e = self.recruit(key, x + (k - 0.5) * 1.8, y)
                if e is None:
                    continue
                e.home = home
                e.spawn_pt = (e.x, e.y)
                if hasattr(e, "state"):
                    e.state = "serene"
                self.guests.append(e)
            self.scraps.append([x, y + 1.0, self.rng.choice(SCRAPS)])

    # --- Each step ----------------------------------------------------------------------

    def _hunger_think(self, ctx, dt: float) -> None:
        if self.form == "cracking":
            self.dt = dt
            self.time += dt
            self._crack_step(ctx, dt)
            return
        self.chew_t = max(0.0, self.chew_t - dt)
        if not (self.planted or self.gliding or self.chew_t > 0) and self.dazed <= 0:
            self._prowl(dt)
        Boss.think(self, ctx, dt)
        t = self.drift_target()
        if t is not None and not self.gliding and self.maw is None and self.tongue is None:
            self.facing = self.angle_to(t.x, t.y)
        self._wade(ctx)
        self._devour(ctx)
        self._clear_scraps(ctx)
        self._bring_course(ctx, dt)
        self._digest(ctx, dt)
        self._fly_spat(ctx, dt)
        self._snap_teeth(ctx, dt)
        self._fly_globs(ctx, dt)
        self._rot(ctx, dt)
        self._tick_quakes(ctx, dt)
        self._land_bones(ctx)
        self.waiters = [w for w in self.waiters if w.alive]

    def _meals(self) -> list:
        """What he could eat now: (thing, x, y)."""
        out = [(s, s[0], s[1]) for s in self.scraps]
        out += [(e, e.x, e.y) for e in self.guests if e.alive]
        out += [(e, e.x, e.y) for e in self.waiters if e.alive]
        return out

    def _prowl(self, dt: float) -> None:
        """Round his prey at HUNGER_PROWL[1] tiles, turning about now and
        then -- unless there's a meal near: then straight for it."""
        speed, keep, smell, rush = config.HUNGER_PROWL
        near = [(math.hypot(x - self.x, y - self.y), x, y) for _, x, y in self._meals()]
        near = [m for m in near if m[0] <= smell]
        if near:
            _, x, y = min(near)
            self._glide_to(x, y, rush, dt)
            self.facing = self.angle_to(x, y)
            return
        t = self.drift_target()
        if t is None:
            return
        self.prowl_t -= dt
        if self.prowl_t <= 0:
            self.prowl_dir = -self.prowl_dir
            self.prowl_t = self.rng.uniform(4.0, 7.0)
        d = math.hypot(t.x - self.x, t.y - self.y)
        out = math.atan2(self.y - t.y, self.x - t.x)
        if d > keep * 2.5:                            # (far off: straight at them, fast)
            self._glide_to(t.x, t.y, speed * 1.6, dt)
            return
        bend = 0.7 if d < keep - 1.5 else (-0.7 if d > keep + 1.5 else 0.0)
        a = out + self.prowl_dir * (math.pi / 2 - bend)
        self.x, self.y = self.clamp_to_lair(self.x + math.cos(a) * speed * dt,
                                            self.y + math.sin(a) * speed * dt, self.hit_radius + 1.0)

    def _wade(self, ctx) -> None:
        """Heroes in the spilt wine wade it slowly (a roll still carries)."""
        slow = config.HUNGER_ISLANDS[3]
        w = ctx.world
        for h in ctx.players:
            if h.alive and h.roll_t <= 0 and self.in_arena(h) \
                    and w.tile_at(math.floor(h.x), math.floor(h.y)) is tiles.HALL_WINE:
                h.slowed(slow, 0.15)

    def _devour(self, ctx) -> None:
        if self.chew_t > 0:                           # (one mouthful at a time)
            return
        reach = self.hit_radius + config.HUNGER_DEVOUR[0]
        for thing, x, y in self._meals():
            r = reach + (0.3 if isinstance(thing, list) else thing.hit_radius)
            if math.hypot(x - self.x, y - self.y) <= r:
                self._eat(ctx, thing, x, y)
                return

    def _eat(self, ctx, thing, x: float, y: float) -> None:
        """A meal: gone, and (up to HUNGER_DEVOUR[3]) he heals and grows."""
        if isinstance(thing, list):
            self.scraps = [s for s in self.scraps if s is not thing]
        else:
            if not thing.alive:
                return
            thing.left = True                         # (no kill: he ate it)
            thing.hp = 0.0
            thing.last_hit_by = None
        self.eaten += 1
        ctx.effects.append(Effect("gore", x, y, size=1.4))
        ctx.events.append(combat.HIT)
        _, heal, grow, most, chew = config.HUNGER_DEVOUR
        self.chew_t = chew
        if self.meals >= most:
            return
        g0 = self.growth()
        self.meals += 1
        g = self.growth()
        self.hit_radius *= g / g0
        self.damage_mult *= g / g0
        self.hp = min(float(self.max_hp), self.hp + self.max_hp * heal)
        ctx.effects.append(Effect("toast", self.x, self.y - self.hit_radius - 3,
                                  label=f"HE GROWS! ({self.meals})"))

    def _clear_scraps(self, ctx) -> None:
        """A hero walking into a scrap, or a hero's shot, knocks it into the wine."""
        if not self.scraps:
            return
        shots = [p for p in ctx.projectiles
                 if p.alive and getattr(p.owner, "faction", "") == "player"]
        keep = []
        for s in self.scraps:
            gone = any(h.alive and math.hypot(h.x - s[0], h.y - s[1]) <= h.hit_radius + 0.7
                       for h in ctx.players)
            if not gone:
                for p in shots:
                    if abs(p.x - s[0]) <= 0.8 and abs(p.y - s[1]) <= 0.8:
                        gone = True
                        if not p.spec.returns:
                            p.alive = False
                        break
            if gone:
                ctx.effects.append(Effect("spill", s[0], s[1], size=0.8))
            else:
                keep.append(s)
        self.scraps = keep

    def _bring_course(self, ctx, dt: float) -> None:
        """Every HUNGER_FEAST[3] s, "MORE!": demon waiters come in from the
        edge of the fight carrying a course to him."""
        _, _, _, every, n, out = config.HUNGER_FEAST
        self.serve_t -= dt
        if self.serve_t > 0 or self.recruit is None:
            return
        self.serve_t = every
        brought = 0
        for _ in range(n):
            a = self.rng.uniform(0, _TAU)
            x, y = self.clamp_to_lair(self.x + math.cos(a) * out, self.y + math.sin(a) * out, 3.0)
            x, y = self._open_spot(x, y)
            e = self.recruit("feast_waiter", x, y)
            if e is None:
                continue
            e.master = self
            self.waiters.append(e)
            brought += 1
            ctx.effects.append(Effect("unveil", e.x, e.y, size=1.5))
        if brought:
            ctx.effects.append(Effect("toast", self.x, self.y - self.hit_radius - 3, label="MORE!"))

    # --- Signature 2: the maw (and being swallowed) ------------------------------------

    def m_maw(self):
        shown, inhale, reach, half_deg, pull = config.HUNGER_MAW[:5]
        t = self.target_now()
        if t is None:
            return
        half = math.radians(half_deg)
        self.planted = True
        self.pose = "maw"
        self.tell = ("maw",)
        self.maw = {"a": self.angle_to(t.x, t.y), "reach": reach, "half": half, "on": False}
        self.facing = self.maw["a"]
        self.ctx.effects.append(Effect("toast", self.x, self.y - self.hit_radius - 3,
                                       label="HE OPENS HIS MAW!"))
        yield self.tell_s(shown)
        self.maw["on"] = True
        self.ctx.events.append("hex")
        left = inhale
        while left > 0:
            dt = self.dt
            a = self.maw["a"]
            for h in self.heroes():
                if id(h) in self.swallowed or id(h) in self.spat or combat.drafting(h) \
                        or not _in_cone(self.x, self.y, a, half, reach + h.hit_radius, h.x, h.y):
                    continue
                d = math.hypot(self.x - h.x, self.y - h.y)
                if d <= self.hit_radius + h.hit_radius + 0.6:
                    if h.hittable:
                        self._swallow(h)
                    continue
                combat.push(h, self.ctx.world, (self.x - h.x) / d * pull * dt,
                            (self.y - h.y) / d * pull * dt, full=True)
            for thing, x, y in self._meals():          # (the feast drawn in too)
                if not _in_cone(self.x, self.y, a, half, reach, x, y):
                    continue
                d = math.hypot(self.x - x, self.y - y) or 1.0
                dx, dy = (self.x - x) / d * pull * dt, (self.y - y) / d * pull * dt
                if isinstance(thing, list):
                    thing[0] += dx
                    thing[1] += dy
                else:
                    combat.push(thing, self.ctx.world, dx, dy)
            left -= dt
            yield 0
        self.maw = None
        self.pose = ""
        yield 0.4

    def _swallow(self, h) -> None:
        _, _, _, _, _, bites, _, held = config.HUNGER_MAW[:8]
        self.swallowed[id(h)] = [h, held, held / bites, bites]
        h.swallowed = self
        h.entranced = 0.0
        self.ctx.effects.append(Effect("toast", h.x, h.y - 2, label="SWALLOWED!"))
        self.ctx.events.append("hex")

    def _digest(self, ctx, dt: float) -> None:
        """Inside him: chewed (a bite every so often), then spat out."""
        if not self.swallowed:
            return
        _, _, _, _, _, bites, damage, held, spit = config.HUNGER_MAW
        for k, v in list(self.swallowed.items()):
            h = v[0]
            if not h.alive:
                self._let_out(h)
                continue
            h.x, h.y = self.x, self.y
            h.vx = h.vy = 0.0
            h.slowed(0.0, 0.1)
            v[1] -= dt
            v[2] -= dt
            if v[2] <= 0 and v[3] > 0:
                v[3] -= 1
                v[2] += held / bites
                _numbered_hit(h, damage * self.damage_mult, self, self.facing, ctx)
                ctx.events.append(combat.HIT)
            if v[1] <= 0 and h.alive:
                self._let_out(h)
                a = self._spit_angle()
                v_spit = spit / config.HUNGER_SPAT
                self.spat[k] = [h, math.cos(a) * v_spit, math.sin(a) * v_spit, config.HUNGER_SPAT]
                ctx.effects.append(Effect("toast", h.x, h.y - 2, label="SPAT OUT!"))
                ctx.effects.append(Effect("spill", h.x, h.y, size=2.0))
                ctx.events.append("boulder")

    def _spit_angle(self) -> float:
        """Across the hall: toward its middle, give or take."""
        cx, cy = self._hall()[:2]
        if math.hypot(cx - self.x, cy - self.y) > 6.0:
            return math.atan2(cy - self.y, cx - self.x) + self.rng.uniform(-0.8, 0.8)
        return self.rng.uniform(0, _TAU)

    def _let_out(self, h) -> None:
        self.swallowed.pop(id(h), None)
        if getattr(h, "swallowed", None) is self:
            h.swallowed = None

    def _fly_spat(self, ctx, dt: float) -> None:
        for k, v in list(self.spat.items()):
            h = v[0]
            v[3] -= dt
            if h.alive:
                combat.push(h, ctx.world, v[1] * dt, v[2] * dt, full=True)
                h.slowed(0.0, 0.05)
            if v[3] <= 0 or not h.alive:
                self.spat.pop(k)

    # --- Signature 3: teeth in the floor ------------------------------------------------

    def m_teeth(self):
        waves, n, length, shown, _, _, gap = config.HUNGER_TEETH
        for w in range(waves):
            t = self.target_now()
            if t is None:
                return
            px, py = self.lead(t, self.x, self.y, secs=shown)
            base = self.rng.uniform(0, math.pi)
            for k in range(n):
                a = base + k * math.pi / n
                off = 0.0 if k == 0 else self.rng.uniform(-3.5, 3.5)   # (one right through you)
                mx, my = px + math.cos(a + math.pi / 2) * off, py + math.sin(a + math.pi / 2) * off
                ux, uy = math.cos(a) * length / 2, math.sin(a) * length / 2
                self.teeth.append([mx - ux, my - uy, mx + ux, my + uy, self.tell_s(shown), 0.0])
            self.tell = ("teeth",)
            if w == 0:
                self.ctx.effects.append(Effect("toast", self.x, self.y - self.hit_radius - 3,
                                               label="TEETH!"))
            yield gap

    def _snap_teeth(self, ctx, dt: float) -> None:
        _, _, _, _, damage, width, _ = config.HUNGER_TEETH
        keep = []
        for th in self.teeth:
            if th[4] > 0:
                th[4] -= dt
                if th[4] <= 0:
                    for h in ctx.players:
                        if not h.hittable or combat.skims(h) or not self.in_arena(h):
                            continue
                        if self.teeth_hit.get(id(h), -9.0) > self.time - 0.25:
                            continue                  # (two lines crossing bite once)
                        if patterns.point_segment_distance(h.x, h.y, *th[:4]) <= width + h.hit_radius:
                            self.teeth_hit[id(h)] = self.time
                            self._hit(h, damage * combat.ground_cut(h), h.x, h.y + 1.0)
                    ctx.events.append("break")
            else:
                th[5] += dt
            if th[4] > 0 or th[5] < 0.4:
                keep.append(th)
        self.teeth = keep

    # --- Signature 4: spilled feast -----------------------------------------------------

    def m_spill(self):
        n, flight = config.HUNGER_SPILL[:2]
        t = self.target_now()
        if t is None:
            return
        self.planted = True
        self.pose = "maw"
        self.tell = ("spill",)
        yield self.tell_s(0.6)
        spots = [self.lead(t, self.x, self.y, secs=flight)]
        for _ in range(n - 1):
            a, r = self.rng.uniform(0, _TAU), self.rng.uniform(3.0, 9.0)
            spots.append((t.x + math.cos(a) * r, t.y + math.sin(a) * r))
        for x, y in spots:
            x, y = self.clamp_to_lair(x, y, 2.0)
            self.globs.append([self.x, self.y, x, y, flight, flight])
        self.ctx.events.append("hex")
        yield 0.5
        self.pose = ""

    def _fly_globs(self, ctx, dt: float) -> None:
        _, _, radius, life, slow, damage, every, tempt, _ = config.HUNGER_SPILL
        keep = []
        for g in self.globs:
            g[4] -= dt
            if g[4] > 0:
                keep.append(g)
                continue
            if ctx.zones is not None:
                ctx.zones.append(Zone("rot", g[2], g[3], radius, life, every,
                                      damage * self.damage_mult, self, slow=slow, tempt=tempt))
            ctx.effects.append(Effect("spill", g[2], g[3], size=radius))
            ctx.events.append("fizzle")
            self._frenzy_near(ctx, g[2], g[3], radius)
        self.globs = keep

    def _frenzy_near(self, ctx, x: float, y: float, radius: float) -> None:
        reach = radius + config.HUNGER_SPILL[8]
        for e in self.guests:
            if e.alive and e.home is not None and math.hypot(e.x - x, e.y - y) <= reach:
                pand.frenzy(ctx.world, e.home)

    def _rot(self, ctx, dt: float) -> None:
        """A rotting pool keeps frenzying the guests who come near it."""
        self.rot_t -= dt
        if self.rot_t > 0 or ctx.zones is None:
            return
        self.rot_t = 0.5
        for z in ctx.zones:
            if z.kind == "rot" and z.source is self:
                self._frenzy_near(ctx, z.x, z.y, z.radius)

    # --- His moves ----------------------------------------------------------------------

    def m_lunge(self):
        shown, speed, most, width, bite, line_dmg, bite_dmg = config.HUNGER_LUNGE
        t = self.target_now()
        if t is None:
            return
        self.planted = True
        a = self.aim(t, self.x, self.y, speed)
        length = min(most, math.hypot(t.x - self.x, t.y - self.y) + 2.0)
        x1, y1 = self.clamp_to_lair(self.x + math.cos(a) * length, self.y + math.sin(a) * length,
                                    self.hit_radius + 1.0)
        self.lunge = (self.x, self.y, x1, y1)
        self.facing = a
        self.tell = ("lunge",)
        yield self.tell_s(shown)
        self.planted = False
        self.gliding = True
        hit = set()
        while True:
            d = math.hypot(x1 - self.x, y1 - self.y)
            step = min(d, speed * self.dt)
            x0, y0 = self.x, self.y
            if d > 1e-6:
                self.x += (x1 - self.x) / d * step
                self.y += (y1 - self.y) / d * step
            for h in self.heroes():
                if id(h) not in hit and patterns.point_segment_distance(
                        h.x, h.y, x0, y0, self.x, self.y) <= width + h.hit_radius:
                    hit.add(id(h))
                    self._hit(h, line_dmg, x0, y0)
            if d <= step + 1e-6:
                break
            yield 0
        mx, my = self.x + math.cos(a) * self.hit_radius * 0.6, self.y + math.sin(a) * self.hit_radius * 0.6
        for h in self.heroes():
            if math.hypot(h.x - mx, h.y - my) <= bite + h.hit_radius:
                self._hit(h, bite_dmg, self.x, self.y)
        self.ctx.effects.append(Effect("swing", self.x, self.y, angle=a, size=bite + 1.0, value=150))
        self.ctx.events.append("swing")
        self.lunge = None
        self.gliding = False
        yield 0.4

    def m_tongue(self):
        shown, speed, reach, drag, damage, width = config.HUNGER_TONGUE
        t = self.target_now()
        if t is None:
            return
        self.planted = True
        self.pose = "maw"
        a = self.aim(t, self.x, self.y, speed)
        self.facing = a
        self.tongue = {"a": a, "len": 0.0, "aiming": True, "held": None, "meal": None}
        self.tell = ("tongue",)
        yield self.tell_s(shown)
        tg = self.tongue
        tg["aiming"] = False
        self.ctx.events.append("swing")
        while tg["len"] < reach and tg["held"] is None and tg["meal"] is None:   # (out)
            tg["len"] = min(reach, tg["len"] + speed * self.dt)
            x, y = self.tongue_tip()
            for h in self.heroes():
                if h.hittable and id(h) not in self.swallowed \
                        and math.hypot(h.x - x, h.y - y) <= width + h.hit_radius:
                    tg["held"] = h
                    self.ctx.effects.append(Effect("toast", h.x, h.y - 2, label="CAUGHT!"))
                    break
            if tg["held"] is None:
                for thing, mx, my in self._meals():
                    if math.hypot(mx - x, my - y) <= width + 0.4:
                        tg["meal"] = thing
                        break
            yield 0
        while tg["len"] > 0:                                                    # (back)
            caught = tg["held"] is not None or tg["meal"] is not None
            tg["len"] = max(0.0, tg["len"] - (drag if caught else speed * 1.5) * self.dt)
            x, y = self.tongue_tip()
            h = tg["held"]
            if h is not None:
                if h.roll_t > 0 or not h.alive:                                  # (rolled free)
                    tg["held"] = None
                    if h.alive:
                        self.ctx.effects.append(Effect("toast", h.x, h.y - 2, label="PULLED FREE!"))
                else:
                    combat.push(h, self.ctx.world, x - h.x, y - h.y, full=True)
                    h.slowed(0.0, 0.1)
            m = tg["meal"]
            if m is not None:
                if isinstance(m, list):
                    m[0], m[1] = x, y
                elif m.alive:
                    m.x, m.y = x, y
            yield 0
        h = tg["held"]
        if h is not None and h.alive:                                           # (bitten)
            self._hit(h, damage, self.x, self.y)
            out = self.angle_to(h.x, h.y) if math.hypot(h.x - self.x, h.y - self.y) > 0.1 else a
            combat.push(h, self.ctx.world, math.cos(out) * 3.0, math.sin(out) * 3.0, full=True)
            self.ctx.effects.append(Effect("toast", h.x, h.y - 2, label="CHOMP!"))
        self.tongue = None
        self.pose = ""
        yield 0.3

    def tongue_tip(self) -> tuple[float, float]:
        tg = self.tongue
        r = self.hit_radius * 0.6 + tg["len"]
        return self.x + math.cos(tg["a"]) * r, self.y + math.sin(tg["a"]) * r

    def m_quake(self):
        planted, rings, gap, speed, reach, damage = config.HUNGER_QUAKE
        self.planted = True
        self.pose = "maw"
        self.tell = ("quake",)
        yield self.tell_s(planted)
        self.pose = ""
        for _ in range(rings):
            self.quakes.append([self.x, self.y, 0.0, reach, speed, damage, set()])
            self.ctx.effects.append(Effect("belly_quake", self.x, self.y, size=reach))
            self.ctx.events.append("boulder")
            yield gap
        self.planted = False

    def _tick_quakes(self, ctx, dt: float) -> None:
        for q in self.quakes:
            q[2] += q[4] * dt
            for h in ctx.players:
                if id(h) in q[6] or not h.alive:
                    continue
                if math.hypot(h.x - q[0], h.y - q[1]) - h.hit_radius > q[2]:
                    continue
                q[6].add(id(h))
                if h.hittable and not combat.skims(h):    # (mid-roll, it rolls past)
                    self._hit(h, q[5] * combat.ground_cut(h), q[0], q[1])
        self.quakes = [q for q in self.quakes if q[2] < q[3]]

    def m_bones(self):
        fans, n, spread_deg, gap = config.HUNGER_BONES[:4]
        shell = self.shots["scrap"]
        spread = math.radians(spread_deg)
        for _ in range(fans):
            t = self.target_now()
            if t is None:
                return
            a = self.aim(t, self.x, self.y, shell.speed)
            self.tell = ("bones",)
            if self.room_for_shots():
                for k in range(n):
                    b = a + spread * (k / (n - 1) - 0.5)
                    self.bones.append(patterns.shoot(self, self.x, self.y, b, shell,
                                                     self.ctx.projectiles))
            self.ctx.events.append("axe")
            yield gap

    def _land_bones(self, ctx) -> None:
        """A bone that's come down lies there: clutter you trip over."""
        if not self.bones:
            return
        _, _, _, _, radius, life, slow = config.HUNGER_BONES
        keep = []
        lying = sum(1 for z in ctx.zones or () if z.kind == "bone_clutter")
        for p in self.bones:
            if p.alive:
                keep.append(p)
            elif ctx.zones is not None and lying < config.HUNGER_CLUTTER:
                ctx.zones.append(Zone("bone_clutter", p.x, p.y, radius, life, 0.25, 0.0, self,
                                      slow=slow))
                lying += 1
        self.bones = keep

    def _hunger_gone(self, ctx) -> None:
        """He's beaten: whoever's inside comes out, his waiters and guests
        leave, the wine drains from the hall."""
        for k, v in list(self.swallowed.items()):
            self._let_out(v[0])
        self.swallowed, self.spat = {}, {}
        for e in self.waiters + self.guests:
            if e.alive:
                e.left = True
                e.hp = 0.0
                e.last_hit_by = None
        self.waiters, self.guests = [], []
        self.scraps, self.teeth, self.globs, self.quakes, self.bones = [], [], [], [], []
        self.lunge = self.tongue = self.maw = None
        self.crack_rows = []
        self._clear_room()


class Waiter(PlainsCreature):
    """A demon waiter (form 2): carrying the Host a course on a tray,
    straight to him through the wine. It never fights; kill it before he
    eats it. Drawn like the plains' creatures."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.master = None
        self.alert = True

    def think(self, ctx, dt: float) -> None:
        super().think(ctx, dt)
        m = self.master
        if m is None or not m.alive or getattr(m, "form", 2) != 2:
            return
        if math.hypot(m.x - self.x, m.y - self.y) > m.hit_radius * 0.5:
            self.go(ctx, m.x, m.y, dt, self.espec.speed)
