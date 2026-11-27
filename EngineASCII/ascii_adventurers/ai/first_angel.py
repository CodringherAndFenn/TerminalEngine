"""
ai/first_angel.py -- THE FOSSIL ANGEL, form 2: THE FIRST ANGEL UNVEILS
(M33.2, design/FINALS.md 9.2). A mix-in of ai/fossil_angel.FossilAngel (one
body, two forms, like the Ancestor's first life): at 0 its flesh grows back,
red and raw, and the first angel unveils.

THE UNVEILING: FOSSIL_UNVEIL s where it stands, not to be hit, its bones
flickering into flesh. Whatever it was doing stops: its wheel rolls back
up, its resin stops running, its echoes go (form 2 doesn't echo: mine;
what's in the air still comes down). Then it's back at full health (x
FOSSIL_UNVEILED_HP: 18,000 of 15,000) and hunts on (ai/finals.Final: the
walk, the leap, the trail and its creatures go on as before).

SIGNATURES, one joining per phase (100-75-50-25%), each kept after:
  1 EYES IN THE FLESH  eyes open across its flesh (AngelEye: small bodies you
                  can hit, riding on it); now and then each sweeps a gaze beam
                  across where you are (its line shown first; cut short by
                  anything that stops shots). Hit one to close it: the angel
                  flinches (a share of its health). A closed eye opens again
                  a while later.
  2 LIFE FROM ITS BLOOD  its blood drips and crawls at you (BloodDrop: it
                  can't hurt you); left alone, a drop grows into a small
                  unveiled angel (a cherub, a dove). Kill the drops early.
  3 RED AMBER     its blood hardens like resin: its pools (RED_RESIN, the
                  blood rain's) hold you until you roll free, and walls of
                  it (RED_AMBER) rise across your path (the move "walls": one
                  ahead of you, one between you and it).
  4 SIX WINGS     six wings of raw flesh and feathers beat in turn, each
                  beat (the wing raised first) a push wave at you and a
                  volley of bloody feathers.
Moves: claw rake (three raking lines, shown; stand between them or roll),
the first word (it speaks, and a ring of white light spreads across the
land: caught in the open it hurts a lot; behind anything that stops shots
-- its feather spikes, red amber walls, a rock, a tree -- you're sheltered;
stone feathers fall round you first when there's no cover near), blood rain
(marked circles round you; they leave pools), halo wheels (its halo splits
into burning wheels that race out in straight lines, bounce off what's
solid and leave fire). Its stone feathers (form 1's) still fall now and
then: the cover the word needs.

Drawn by render/fossil_angel.py (form 2: render/first_angel.py).
"""

from __future__ import annotations

import math

from .. import config
from ..entities.actor import Actor
from ..entities.effects import Effect
from ..systems import combat
from ..systems.collision import WATERY
from ..systems.raycast import first_hit
from ..systems.zones import Zone
from ..world import tiles
from .bosses import Boss
from .first_life import FirstBlob
from .pangaea import inside

_TAU = math.tau
RED = (tiles.RED_RESIN, tiles.RED_AMBER)
PHASE_BANNERS_2 = {
    1: ("ITS BLOOD CRAWLS", "kill the drops before they grow into angels"),
    2: ("ITS BLOOD HARDENS", "red amber holds you -- roll free"),
    3: ("SIX WINGS", "they beat in turn"),
}
# Its six wings, in the order they beat: (side, tiles down from its middle).
WINGS = ((-1, -1.5), (1, -1.5), (-1, 0.0), (1, 0.0), (-1, 1.4), (1, 1.4))
WING_OUT = 3.4                     # tiles out from its middle a wing beats from


class AngelEye(Actor):
    """One of the eyes in its flesh (FOSSIL_EYES): a body you can hit (its
    own health, scaled like the angel's), riding on the angel (it puts it
    where its slot is each step). The angel sweeps its gaze (`gaze`); hit to
    0 it closes (the angel flinches). Closed by the angel (its fall), `gone`:
    no kill."""

    faction = "enemy"
    boss = True                       # never sleeps; drawn with the angel
    spawn_id = None
    level = 1
    damage_mult = 1.0
    haste = 0.0
    kind_key = "angel_eye"

    def __init__(self, angel, slot: int) -> None:
        e = config.FOSSIL_EYES
        spec = config.ENEMIES["angel_eye"]
        super().__init__(max(1, round(e[3] * angel.hp_scale())), 0.6)
        self.part_of = angel
        self.espec = spec
        self.slot = slot
        self.rest = angel.rng.uniform(e[4], e[5]) * 0.6
        self.gaze: dict | None = None     # a, turn, t, tell, hit, length
        self.facing = 0.0
        self.vx = self.vy = 0.0
        self.half = spec.size_px / 2
        self.gone = False
        self.left = False
        self.t = 0.0
        self.x, self.y = angel.eye_at(slot)

    @property
    def hittable(self) -> bool:
        return self.alive and self.part_of.hittable

    def think(self, ctx, dt: float) -> None:
        pass                          # the angel moves it and sweeps its gaze

    def hear(self, x: float, y: float) -> None:
        pass


class BloodDrop(FirstBlob):
    """A drop of its blood (FOSSIL_DROPS): it crawls at you and can't hurt
    you; left alone, the angel grows it into a small angel (`grow_t`)."""


class Wheel:
    """One of the halo's burning wheels (FOSSIL_WHEELS): racing along
    (vx, vy), bouncing off what's solid, `bounces` left, gone after `life`
    s; `hits`: id -> s before it can hit that body again."""

    __slots__ = ("x", "y", "vx", "vy", "t", "life", "bounces", "radius", "damage", "push",
                 "rolled", "hits", "spin")

    def __init__(self, x, y, angle, speed, life, bounces, radius, damage, push) -> None:
        self.x, self.y = x, y
        self.vx, self.vy = math.cos(angle) * speed, math.sin(angle) * speed
        self.t, self.life, self.bounces = 0.0, life, bounces
        self.radius, self.damage, self.push = radius, damage, push
        self.rolled = 0.0
        self.hits: dict[int, float] = {}
        self.spin = 0.0


class FirstAngel:
    """Form 2 of ai/fossil_angel.FossilAngel (see the module's docstring)."""

    def _init_first_angel(self) -> None:
        n = config.FOSSIL_EYES[1]
        self.form = 1                     # 1 its bones walk, "unveiling", 2 the first angel
        self.unveil_t = 0.0
        self.eyes: list = [None] * n      # AngelEye (open) or None (closed), a slot each
        self.eye_shut = [0.0] * n         # s until a closed one opens again
        self.drops: list = []             # its blood crawling, and what grew of it
        self.drop_t = 0.0
        self.red: dict = {}               # (tx, ty) -> [state "pool"|"rising"|"wall", s left, the tile before]
        self.red_cd: dict = {}            # id(hero) -> s before red amber can hold them again
        self.wing = 0                     # the next of its six wings to beat
        self.wing_t = 0.0                 # s to that beat
        self.beating: tuple | None = None # (the wing, s left raised)
        self.word: dict | None = None     # the first word's ring of light, spreading
        self.wheels: list[Wheel] = []
        self._vic: list = []

    # --- Being the first angel --------------------------------------------------------------

    @property
    def unveiled(self) -> bool:
        return self.form == 2

    @property
    def hittable(self) -> bool:
        return Boss.hittable.fget(self) and self.form != "unveiling"

    def take_damage(self, amount, source, from_angle):
        if self.form == "unveiling":
            return 0.0
        dealt = super().take_damage(amount, source, from_angle)
        if self.form == 1 and self.hp <= 0:            # (its bones fall: the first angel)
            self.hp = 1.0
            self._unveil()
        return dealt

    def brood_every(self) -> float:
        """Its trail's creatures, fewer in form 2 (its blood brings its own)."""
        slower = config.FOSSIL_BROOD_SLOWER if self.form == 2 else 1.0
        return config.FINAL_BROOD[0] * slower

    def hp_scale(self) -> float:
        """Its health against its base (a form's), so what's part of it (a
        wheel, an eye) scales with it (level, difficulty, co-op)."""
        base = config.ENEMIES[self.espec.kind].max_hp
        if self.form == 2:
            base *= config.FOSSIL_UNVEILED_HP
        return self.max_hp / base

    def place_eyes(self) -> None:
        for i, eye in enumerate(self.eyes):
            if eye is not None:
                eye.x, eye.y = self.eye_at(i)

    def eye_at(self, slot: int) -> tuple[float, float]:
        dx, dy = config.FOSSIL_EYE_SLOTS[slot]
        return self.x + dx, self.y + dy

    def wing_at(self, i: int) -> tuple[float, float]:
        side, dy = WINGS[i]
        return self.x + side * WING_OUT, self.y + dy

    @property
    def six_wings(self) -> bool:
        """Its fourth signature: its six wings, from its last phase."""
        return self.form == 2 and self.phase >= 3

    # --- The unveiling ------------------------------------------------------------------

    def _unveil(self) -> None:
        """Its bones fall: whatever it was doing stops, its echoes go (form 2
        doesn't echo), and its flesh starts growing back where it stands."""
        ctx = self.ctx
        self.form = "unveiling"
        self.unveil_t = config.FOSSIL_UNVEIL
        self.abort_move()
        self.leap, self.mark = None, None
        self.recovering = 0.0
        self.airborne = 0.0
        self.on_leap()                    # (its wheel rolls back up, its resin stops)
        self.halo_lost = 0.0
        if ctx is not None:
            self.drop_echoes(ctx)
        self.runners, self.flashes = [], []
        self.banner_req = ("THE FIRST ANGEL UNVEILS", "its flesh grows back, red and raw")
        if ctx is not None:
            ctx.effects.append(Effect("explosion", self.x, self.y))
            ctx.effects.append(Effect("gore", self.x, self.y))
            ctx.effects.append(Effect("toast", self.x, self.y - self.hit_radius - 2,
                                      label="ITS FLESH GROWS BACK!"))
            ctx.events.append("boulder")

    def _unveil_step(self, ctx, dt: float) -> None:
        self.dt = dt
        self.time += dt
        self.unveil_t -= dt
        self._tick_spikes(ctx, dt)
        self._tick_amber(ctx, dt)
        if int(self.time * 6) != int((self.time - dt) * 6):
            a, r = self.rng.uniform(0, _TAU), self.rng.uniform(1.0, 3.5)
            ctx.effects.append(Effect("gore", self.x + math.cos(a) * r, self.y + math.sin(a) * r * 0.8))
        if self.unveil_t <= 0:
            self._become_first_angel(ctx)

    def _become_first_angel(self, ctx) -> None:
        self.form = 2
        self.pose = ""
        self.bspec = config.BOSSES["fossil_angel_unveiled"]
        self.phase = 0
        self.max_hp = round(self.max_hp * config.FOSSIL_UNVEILED_HP)
        self.hp = float(self.max_hp)
        self.hit_radius = config.FOSSIL_UNVEILED_HIT_RADIUS
        self._rest = 1.5
        self.combo = 0
        self.last_move = None
        n_open, n, again = config.FOSSIL_EYES[0], config.FOSSIL_EYES[1], config.FOSSIL_EYES[2]
        opened = set(self.rng.sample(range(n), n_open))
        for i in range(n):
            if i in opened:
                self._open_eye(ctx, i)
            else:
                self.eye_shut[i] = again * self.rng.uniform(0.3, 1.0)
        self.drop_t = config.FOSSIL_DROPS[0]
        self.wing_t = config.FOSSIL_WINGS[0]
        self.banner_req = ("THE FIRST ANGEL", "eyes open in its flesh -- hit them to close them")
        ctx.effects.append(Effect("unveil", self.x, self.y, size=self.hit_radius + 2.0))
        ctx.events.append("hex")

    # --- Each step -------------------------------------------------------------------------

    def _first_angel_step(self, ctx, dt: float) -> None:
        self._vic = self.victims(ctx)
        self._tick_eyes(ctx, dt)
        if self.phase >= 1:
            self._drip(ctx, dt)
        self._tick_drops(ctx, dt)
        self._tick_red(ctx, dt)
        if self.six_wings:
            self._tick_wings(ctx, dt)
        self._tick_word(ctx, dt)
        self._tick_wheels(ctx, dt)

    def on_death(self, ctx) -> None:
        """It's beaten: its eyes close, its red amber melts away, its wheels
        and its word are gone."""
        for i, eye in enumerate(self.eyes):
            if eye is not None and eye.alive:
                eye.gone = eye.left = True
                eye.hp = 0.0
                eye.last_hit_by = None
            self.eyes[i] = None
        w = ctx.world
        if hasattr(w, "set_tile"):
            for key, (_, _, old) in self.red.items():
                if w.tile_at(*key) in RED:
                    w.set_tile(key[0], key[1], old)
        self.red = {}
        self.wheels, self.word, self.beating = [], None, None
        super().on_death(ctx)

    # --- Signature 1: eyes in the flesh -----------------------------------------------------

    def _open_eye(self, ctx, i: int) -> None:
        eye = AngelEye(self, i)
        self.eyes[i] = eye
        ctx.spawned.append(eye)
        ctx.effects.append(Effect("gore", eye.x, eye.y))

    def _tick_eyes(self, ctx, dt: float) -> None:
        again = config.FOSSIL_EYES[2]
        for i, eye in enumerate(self.eyes):
            if eye is not None and not eye.alive:
                self.eyes[i] = None
                self.eye_shut[i] = again
                if not eye.gone:
                    self._eye_closed(ctx, eye)
                continue
            if eye is None:
                self.eye_shut[i] -= dt
                if self.eye_shut[i] <= 0 and self.leap is None:
                    self._open_eye(ctx, i)
                continue
            eye.x, eye.y = self.eye_at(i)
            eye.t += dt
            self._gaze(ctx, eye, dt)

    def _gaze(self, ctx, eye: AngelEye, dt: float) -> None:
        """An eye's gaze: resting, shown (its line where it starts), then
        sweeping across where you are; whoever it touches is hurt once."""
        _, _, _, _, lo, hi, tell, arc, sweep, reach, half, dmg, _ = config.FOSSIL_EYES
        if not self.hittable or self.leap is not None or self.recovering > 0:
            eye.gaze = None                           # (up in the air, getting up: it blinks)
            return
        g = eye.gaze
        if g is None:
            eye.rest -= dt
            if eye.rest > 0:
                return
            t = self.nearest()
            if t is None or math.hypot(t.x - eye.x, t.y - eye.y) > reach + 4.0:
                eye.rest = 0.5
                return
            to = math.atan2(t.y - eye.y, t.x - eye.x)
            turn = self.rng.choice((-1.0, 1.0)) * math.radians(arc)
            eye.gaze = g = dict(a0=to - turn / 2, turn=turn, t=0.0, tell=self.tell_s(tell),
                                hit=set(), length=reach)
        else:
            g["t"] += dt
        u = (g["t"] - g["tell"]) / sweep
        a = g["a0"] + g["turn"] * min(1.0, max(0.0, u))
        eye.facing = a
        x1, y1 = eye.x + math.cos(a) * reach, eye.y + math.sin(a) * reach
        stop = first_hit(ctx.world.tile_at, eye.x, eye.y, x1, y1)
        g["length"] = reach if stop is None else max(0.5, stop.t * reach)
        if u < 0:
            return
        for v in self._vic:
            if id(v) in g["hit"] or not v.hittable or combat.drafting(v):
                continue
            if inside(v, "line", eye.x, eye.y, a, g["length"], half):
                g["hit"].add(id(v))
                self.hit(v, self.hurt(dmg), a)
        if u >= 1.0:
            eye.gaze = None
            eye.rest = self.rng.uniform(lo, hi)

    def _eye_closed(self, ctx, eye: AngelEye) -> None:
        """An eye hit to 0 closes, and the angel flinches."""
        burst = config.FOSSIL_EYES[12] * self.max_hp
        ctx.effects.append(Effect("gore", eye.x, eye.y))
        ctx.effects.append(Effect("toast", eye.x, eye.y - 1.5, label="AN EYE CLOSES!"))
        ctx.events.append("hit")
        self.take_damage(burst, eye.last_hit_by, None)

    # --- Signature 2: life from its blood ---------------------------------------------------

    def _drip(self, ctx, dt: float) -> None:
        every, n, lo, hi, most, grow = config.FOSSIL_DROPS
        self.drop_t -= dt
        if self.drop_t > 0 or self.recruit is None or self.leap is not None:
            return
        self.drop_t = every
        self.drops = [e for e in self.drops if e.alive]
        world = ctx.world
        came = 0
        for _ in range(min(n, most - len(self.drops))):
            for _ in range(8):
                a, r = self.rng.uniform(0, _TAU), self.rng.uniform(lo, hi)
                x, y = self.x + math.cos(a) * r, self.y + math.sin(a) * r * 0.8
                t = world.tile_at(math.floor(x), math.floor(y))
                if t is not None and not t.solid and t.name not in WATERY:
                    break
            else:
                continue
            e = self.recruit("blood_drop", x, y)
            if e is None:
                continue
            e.grow_t = grow
            e.final_own = self
            e.alert = True
            self.drops.append(e)
            ctx.effects.append(Effect("gore", x, y))
            came += 1
        if came and not getattr(self, "_drops_told", False):
            self._drops_told = True
            ctx.effects.append(Effect("toast", self.x, self.y - self.hit_radius - 3,
                                      label="ITS BLOOD CRAWLS"))

    def _tick_drops(self, ctx, dt: float) -> None:
        for e in list(self.drops):
            g = getattr(e, "grow_t", None)
            if g is None or not e.alive:
                continue
            e.grow_t = g - dt
            if e.grow_t <= 0:
                self._grow_angel(ctx, e)
        self.drops = [e for e in self.drops if e.alive]

    def _grow_angel(self, ctx, e) -> None:
        """A drop left alone grows into a small angel, unveiled at once."""
        key = self.rng.choice(config.FOSSIL_DROP_ANGELS)
        e2 = self.recruit(key, e.x, e.y) if self.recruit is not None else None
        e.left = True                     # (it became something else: no kill)
        e.hp = 0.0
        e.last_hit_by = None
        if e2 is None:
            return
        if hasattr(e2, "unveil"):
            e2.unveil()
            e2.timer = min(getattr(e2, "timer", 0.0), 0.05)
        e2.final_own = self
        e2.alert = True
        e2.grow_t = None
        self.drops.append(e2)
        ctx.effects.append(Effect("unveil", e.x, e.y, size=1.2))
        ctx.effects.append(Effect("toast", e.x, e.y - 1.5, label="IT GROWS INTO AN ANGEL!"))
        ctx.events.append("hex")

    # --- Signature 3: red amber ------------------------------------------------------------

    def _red_tile(self, world, tx: int, ty: int, state: str, secs: float, heroes=()) -> bool:
        """Its red resin ("pool", "rising") or amber ("wall") on tile (tx, ty),
        where it can go: open ground (not water, not solid, not its own
        stone), or its own red already; a wall never on anyone."""
        key = (tx, ty)
        entry = self.red.get(key)
        if entry is None:
            cur = world.tile_at(tx, ty)
            if cur is None or cur.solid or cur.name in WATERY or cur in self.FIXTURES:
                return False
            old = cur
        else:
            if entry[0] == "wall" and state != "wall":
                return False                          # (a wall stays a wall)
            old = entry[2]
        if state == "wall" and any(abs(h.x - tx - 0.5) < h.hit_radius + 0.5
                                   and abs(h.y - ty - 0.5) < h.hit_radius + 0.5 for h in heroes):
            return False
        world.set_tile(tx, ty, tiles.RED_AMBER if state == "wall" else tiles.RED_RESIN)
        if entry is not None and entry[0] == state:
            secs = max(secs, entry[1])
        self.red[key] = [state, secs, old]
        return True

    def _tick_red(self, ctx, dt: float) -> None:
        """Its red resin: running walls hardening, pools and walls going;
        heroes in its pools slowed -- or, from its third phase, held."""
        hold, dmg, again, slow = config.FOSSIL_RED_AMBER
        stand = config.FOSSIL_WALLS[4]
        world = ctx.world
        can = hasattr(world, "set_tile")
        heroes = [h for h in ctx.players if h.alive]
        done = []
        for key, v in self.red.items():
            v[1] -= dt
            if v[1] > 0:
                continue
            if v[0] == "rising" and can:
                if world.tile_at(*key) is tiles.RED_RESIN and self._red_tile(world, key[0], key[1],
                                                                            "wall", stand, heroes):
                    continue
            done.append(key)
        for key in done:
            _, _, old = self.red.pop(key)
            if can and world.tile_at(*key) in RED:
                world.set_tile(key[0], key[1], old)
        for k in list(self.red_cd):
            self.red_cd[k] -= dt
            if self.red_cd[k] <= 0:
                del self.red_cd[k]
        if not self.red:
            return
        for h in heroes:
            if h.rolling or combat.drafting(h) or id(h) in self.held:
                continue
            if world.tile_at(math.floor(h.x), math.floor(h.y)) is not tiles.RED_RESIN:
                continue
            if self.phase >= 2 and id(h) not in self.red_cd:
                self._hold_hero(ctx, h, hold, dmg, "CAUGHT IN RED AMBER!")
                self.red_cd[id(h)] = hold + again
            else:
                h.slowed(slow, 0.2)

    def m_walls(self):
        """Red amber walls rise across your path: one ahead of you, one
        between you and it (the resin running first, then hardening)."""
        t = self.target_now()
        if t is None:
            return
        tell, n, length, ahead, _ = config.FOSSIL_WALLS
        tell = self.tell_s(tell)
        self.pose, self.tell = "weep", ("walls",)
        world = self.ctx.world
        to = math.atan2(t.y - self.y, t.x - self.x)
        vx, vy = getattr(t, "vx", 0.0), getattr(t, "vy", 0.0)
        way = math.atan2(vy, vx) if math.hypot(vx, vy) > 1.0 else to
        segs = [(t.x + math.cos(way) * ahead, t.y + math.sin(way) * ahead, way + math.pi / 2)]
        if n > 1:                                     # (cover from the first word)
            segs.append((t.x - math.cos(to) * 3.0, t.y - math.sin(to) * 3.0, to + math.pi / 2))
        if hasattr(world, "set_tile"):
            for cx, cy, a in segs[:n]:
                ca, sa = math.cos(a), math.sin(a)
                k = -length / 2
                while k <= length / 2:
                    self._red_tile(world, math.floor(cx + ca * k), math.floor(cy + sa * k),
                                   "rising", tell)
                    k += 0.5
                self.ctx.effects.append(Effect("gore", cx, cy))
        self.ctx.events.append("orb")
        yield tell
        self.pose = ""
        yield 0.4

    # --- Signature 4: six wings ----------------------------------------------------------

    def _tick_wings(self, ctx, dt: float) -> None:
        every, raised = config.FOSSIL_WINGS[0], config.FOSSIL_WINGS[1]
        if self.leap is not None or self.recovering > 0:
            self.beating = None
            return
        if self.beating is not None:
            i, left = self.beating
            left -= dt
            if left > 0:
                self.beating = (i, left)
                return
            self.beating = None
            self._beat(ctx, i)
            return
        self.wing_t -= dt
        if self.wing_t <= 0:
            self.wing_t = every
            self.beating = (self.wing, raised)
            self.wing = (self.wing + 1) % len(WINGS)

    def _beat(self, ctx, i: int) -> None:
        """A wing beats: a push wave at you, a volley of bloody feathers."""
        _, _, arc, reach, dmg, push, n, spread = config.FOSSIL_WINGS
        x, y = self.wing_at(i)
        t = self.nearest()
        a = math.atan2(t.y - y, t.x - x) if t is not None else (0.0 if WINGS[i][0] > 0 else math.pi)
        self.area(ctx, "cone", x, y, a, reach, math.radians(arc) / 2, self.hurt(dmg), push,
                  record=False)
        sp = math.radians(spread)
        self.fan(ctx, "blood_feather", [a + sp * (k / max(1, n - 1) - 0.5) for k in range(n)], x, y)
        ctx.effects.append(Effect("feathers", x, y))
        ctx.events.append("hit")

    # --- The moves ---------------------------------------------------------------------------

    def m_rake(self):
        """Three raking lines, shown: stand between them, or roll."""
        t = self.target_now()
        if t is None:
            return
        tell, n, length, gap, half, dmg, push = config.FOSSIL_RAKE
        tell = self.tell_s(tell)
        a = self.aim(t, self.x, self.y, secs=tell)
        px, py = -math.sin(a), math.cos(a)
        x0, y0 = self.x, self.y
        self.pose, self.tell = "rake", ("rake",)
        self.lines = [(x0 + px * off, y0 + py * off, a, length, half)
                      for off in ((k - (n - 1) / 2) * gap for k in range(n))]
        yield tell
        ctx = self.ctx
        for x, y, aa, L, hw in self.lines:
            self.area(ctx, "line", x, y, aa, L, hw, self.hurt(dmg), push, tell=tell)
            ctx.effects.append(Effect("gore", x + math.cos(aa) * L * 0.5, y + math.sin(aa) * L * 0.5))
        ctx.events.append("hit")
        self.lines, self.pose = [], ""
        yield 0.3

    def m_word(self):
        """It speaks: a ring of white light spreads across the land. Behind
        anything that stops shots you're sheltered; in the open it hurts."""
        tell, speed, reach, dmg, covers, near, lo, hi = config.FOSSIL_WORD
        ctx = self.ctx
        self.planted, self.pose, self.tell = True, "word", ("word",)
        ctx.effects.append(Effect("toast", self.x, self.y - self.hit_radius - 3,
                                  label="THE FIRST WORD -- HIDE!"))
        world = ctx.world
        if hasattr(world, "set_tile"):
            for h in [h for h in ctx.players if h.alive]:
                if not self._cover_near(world, h, near):
                    self._drop_cover(ctx, h, covers, lo, hi)
        ctx.events.append("hex")
        yield self.tell_s(tell)
        self.word = dict(x=self.x, y=self.y, r=self.hit_radius, speed=speed, reach=reach,
                         dmg=self.hurt(dmg), passed=set())
        self.planted, self.pose = False, ""
        ctx.effects.append(Effect("nova", self.x, self.y, size=6.0))
        ctx.events.append("boulder")
        yield 0.5

    def _cover_near(self, world, h, near: float) -> bool:
        """Anything that stops shots within `near` tiles of hero h?"""
        cx, cy = math.floor(h.x), math.floor(h.y)
        k = math.ceil(near)
        for j in range(-k, k + 1):
            for i in range(-k, k + 1):
                if i * i + j * j > near * near:
                    continue
                t = world.tile_at(cx + i, cy + j)
                if t is not None and t.blocks_shots:
                    return True
        return False

    def _drop_cover(self, ctx, h, n: int, lo: float, hi: float) -> None:
        """Stone feathers fall round hero h (two spikes wide each, across
        the way to the angel): cover from the word."""
        world = ctx.world
        life = config.FOSSIL_FEATHERS[7]
        heroes = [x for x in ctx.players if x.alive]
        base = self.rng.uniform(0, _TAU)
        for k in range(n):
            a = base + k * _TAU / n + self.rng.uniform(-0.4, 0.4)
            r = self.rng.uniform(lo, hi)
            cx, cy = h.x + math.cos(a) * r, h.y + math.sin(a) * r * 0.8
            to = math.atan2(cy - self.y, cx - self.x) + math.pi / 2
            for off in (-0.5, 0.5):
                tx, ty = math.floor(cx + math.cos(to) * off), math.floor(cy + math.sin(to) * off)
                if self._free(world, tx, ty, heroes):
                    self.spikes.append([tx, ty, world.tile_at(tx, ty), life])
                    world.set_tile(tx, ty, tiles.FEATHER_SPIKE)
            ctx.effects.append(Effect("debris", cx, cy))

    def _tick_word(self, ctx, dt: float) -> None:
        w = self.word
        if w is None:
            return
        w["r"] = min(w["reach"], w["r"] + w["speed"] * dt)
        for v in self._vic:
            if id(v) in w["passed"]:
                continue
            d = math.hypot(v.x - w["x"], v.y - w["y"])
            if d > w["r"] + v.hit_radius:
                continue
            w["passed"].add(id(v))
            if not v.hittable or combat.drafting(v):
                continue
            hero = getattr(v, "faction", "") == "player"
            if first_hit(ctx.world.tile_at, w["x"], w["y"], v.x, v.y) is not None:
                if hero:
                    ctx.effects.append(Effect("toast", v.x, v.y - 1.5, label="SHELTERED"))
                continue
            self.hit(v, w["dmg"], math.atan2(v.y - w["y"], v.x - w["x"]))
        if w["r"] >= w["reach"]:
            self.word = None

    def m_rain(self):
        """It shakes its wings: blood falls on marked circles round you,
        leaving pools."""
        t = self.target_now()
        if t is None:
            return
        tell, n, near, flight, *_ = config.FOSSIL_RAIN
        self.pose, self.tell = "beat", ("rain",)
        yield self.tell_s(tell)
        self.pose = ""
        lx, ly = self.lead(t, self.x, self.y, secs=flight)
        spots = [(lx, ly, lx, ly)]
        for _ in range(n - 1):
            a, r = self.rng.uniform(0, _TAU), near * math.sqrt(self.rng.random())
            x, y = t.x + math.cos(a) * r, t.y + math.sin(a) * r * 0.8
            spots.append((x, y, x, y))
        self.lob_many(self.ctx, spots, flight, "blood", tell=flight)
        self.ctx.events.append("orb")
        yield 0.4

    def _blood_landed(self, ctx, x: float, y: float) -> None:
        _, _, _, _, rad, dmg, pool_r, pool_life = config.FOSSIL_RAIN
        self.area(ctx, "circle", x, y, 0.0, rad, 0.0, self.hurt(dmg), record=False)
        world = ctx.world
        if hasattr(world, "set_tile"):
            k = math.ceil(pool_r)
            for j in range(-k, k + 1):
                for i in range(-k, k + 1):
                    tx, ty = math.floor(x) + i, math.floor(y) + j
                    if math.hypot(tx + 0.5 - x, (ty + 0.5 - y) * 1.1) <= pool_r:
                        self._red_tile(world, tx, ty, "pool", pool_life)
        ctx.effects.append(Effect("gore", x, y))
        ctx.events.append("fizzle")

    def m_wheels(self):
        """Its halo splits into burning wheels that race out in straight
        lines and bounce off what's solid."""
        t = self.target_now()
        if t is None or self.wheels:
            yield 0.1
            return
        tell, n, speed, rad, life, bounces, dmg, push, *_ = config.FOSSIL_WHEELS
        self.pose, self.tell = "halo", ("wheels",)
        yield self.tell_s(tell)
        a0 = self.aim(t, self.x, self.y, speed=speed)
        for k in range(n):
            a = a0 + k * _TAU / n
            self.wheels.append(Wheel(self.x + math.cos(a) * 1.5, self.y + math.sin(a) * 1.2, a, speed,
                                     life, bounces, rad, self.hurt(dmg), push))
        self.ctx.effects.append(Effect("explosion", self.x, self.y - 2.0))
        self.ctx.events.append("boulder")
        self.pose = ""
        yield 0.3

    def _wall_at(self, world, x: float, y: float) -> bool:
        t = world.tile_at(math.floor(x), math.floor(y))
        return t is None or t.solid

    def _tick_wheels(self, ctx, dt: float) -> None:
        if not self.wheels:
            return
        again, every, fire_s, fire_dmg = config.FOSSIL_WHEELS[8:12]
        fire_r = config.FOSSIL_HALO[11]
        world = ctx.world
        kept = []
        for w in self.wheels:
            w.t += dt
            w.spin += dt * 9.0
            speed = math.hypot(w.vx, w.vy)
            steps = max(1, math.ceil(speed * dt / 0.4))
            h = dt / steps
            for _ in range(steps):
                nx, ny = w.x + w.vx * h, w.y + w.vy * h
                lead = w.radius * 0.6
                if self._wall_at(world, nx + math.copysign(lead, w.vx), w.y):
                    w.vx, nx = -w.vx, w.x
                    w.bounces -= 1
                if self._wall_at(world, nx, ny + math.copysign(lead, w.vy)):
                    w.vy, ny = -w.vy, w.y
                    w.bounces -= 1
                w.x, w.y = nx, ny
            for key in list(w.hits):
                w.hits[key] -= dt
                if w.hits[key] <= 0:
                    del w.hits[key]
            for v in self._vic:
                if id(v) in w.hits or not v.hittable or combat.drafting(v):
                    continue
                if math.hypot(v.x - w.x, v.y - w.y) <= w.radius + v.hit_radius:
                    w.hits[id(v)] = again
                    self.hit(v, w.damage, math.atan2(w.vy, w.vx), w.push)
            w.rolled += speed * dt
            if w.rolled >= every:
                w.rolled = 0.0
                ctx.zones.append(Zone("lava_splash", w.x, w.y, fire_r, fire_s, 0.5,
                                      self.hurt(fire_dmg), self))
            if w.t < w.life and w.bounces >= 0:
                kept.append(w)
            else:
                ctx.effects.append(Effect("fizzle", w.x, w.y))
        self.wheels = kept
