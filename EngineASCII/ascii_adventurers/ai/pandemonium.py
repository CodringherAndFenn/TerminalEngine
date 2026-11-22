"""
ai/pandemonium.py -- Pandemonium's revellers (M30.2, design/OCEAN.md 14-15):
the first eight of its sixteen enemies.

THE TRANCE (Reveller). They live in groups -- round a banquet table, at a
bandstand, along the endless banquet, in the hall of mirrors -- and in the
trance they feast, drink, dance and play, ignoring you. A group frenzies as
one, and for good (the user's one-way frenzy): once a hero comes within
REVEL[0] tiles of any of them (half that where the music plays) or anyone
hits one, they all freeze and turn on you (a tell of REVEL[3] s), then come
at full speed. A bandstand group's frenzy carries to every group within
REVEL[2] tiles. The skill is choosing which group to wake, and where.
Frenzied and badly hurt, they drink at the wine fountains to heal (FONT,
like Paradise's blood fonts). Their trance and their turn are Paradise's
unveiling (ai/paradise.Angel: serene = the trance, unveiled = frenzied),
shared by the group.

  glutton      stuffing itself; frenzied it lumbers after you and
               belly-slams a shockwave ring; badly hurt, it gorges at any
               banquet table it passes, healing
  drunkard     swaying; frenzied it weaves, hard to predict, and hurls
               bottles that shatter into wine puddles (they slow you and
               fill your temptation)
  toastmaster  (elite) goblet raised; frenzied it calls toasts: a burst of
               speed for every frenzied reveller near, and a wave of wine
  ravenous     never full; frenzied they sprint in and latch on, biting and
               slowing you until a roll throws them off
  dancer       twirling in pairs; frenzied it dances steps that repeat --
               circling you one way, a dash through you, circling back, a
               dash -- slashing with ribbon blades
  masked dancer a masquerade guest; frenzied it swaps places with another
               dancer in a flash, then stabs from where it lands
  band drummer drums at a bandstand; frenzied every beat sends a shockwave
               ring out on a steady rhythm (roll through on the beat)
  piper        (elite) leads the tune; frenzied its song fills your
               temptation fast in a cone, and every few seconds it plays the
               frenzy on to the next group in the trance

M30.3, the other eight. The vain and the greedy gather at the gilded
statues (in the trance like the rest):
  vain         admiring itself in a hand mirror; frenzied its mirror flashes
               (the cone is marked first): you're dazzled, and your shots in
               it turn back at you
  gilded reveller  posing as a second statue; frenzied, a gold shell soaks
               hits until it cracks off; slow, heavy slams
  hoarder      counting coins; frenzied it throws fistfuls that hurt where
               they land and lie there, tripping you
  beloved      (elite) the centre of admiration; its admirers (its group's
               Vain) circle it and take its hits, and while it lives its
               group is faster; frenzied it throws fans of glitter
The demon hosts are never in the trance -- always alert, at their posts by
the groups (Host):
  cupbearer    refills the hurt revellers (heals them) and throws wine that
               tempts you
  carver       lunging cleaves; cleavers thrown out that curve back to it
  bouncer      charges along a shown line; caught, you're thrown at the
               nearest group still in the trance
  master of revels  (elite) rings its bell: every group near it frenzies,
               and every entranced hero snaps out; fireworks on marked
               circles

Their pictures: render/pandemonium_art.py; their tells: render/pandemonium.py.
"""

from __future__ import annotations

import math
import random

from .. import config
from ..entities.effects import Effect
from ..systems import patterns
from ..systems.statuses import wounded
from ..systems.zones import Zone
from ..world import tiles
from ..world.rng import hash_coords
from .brain import AIContext
from .creatures import _numbered_hit
from .paradise import Angel
from .plains import PlainsCreature

_FEASTERS = ("glutton", "drunkard", "toastmaster", "ravenous")
_DANCERS = ("dancer", "masked_dancer")


# --- The revel: its groups, their homes, the music ----------------------------------------


def _plan(world):
    layout = getattr(world, "layout", None)
    zone = layout.zone("pandemonium") if hasattr(layout, "zone") else None
    if zone is None:
        return None
    from ..world.zones import plan_of
    return plan_of(layout, zone)


def _cached(world, name: str, make):
    """world.<name>, worked out once (a test map may set it)."""
    got = getattr(world, name, None)
    if got is None:
        got = make()
        try:
            setattr(world, name, got)
        except AttributeError:
            pass
    return got


def sites(world) -> dict:
    """Where the groups live: home -> (x, y, kind), kind "table", "band",
    "banquet" or "mirrors"."""
    def make():
        out = {}
        p = _plan(world)
        if p is not None:
            for i, (x, y) in enumerate(p.tables):
                out[("table", i)] = (x + 0.5, float(y), "table")
            for i, (x, y) in enumerate(p.bandstands):
                out[("band", i)] = (x + 0.5, y + 0.5, "band")
            if p.banquet is not None:
                out[("banquet", 0)] = (p.banquet[0] + 0.5, float(p.banquet[1]), "banquet")
            if p.mirrors is not None:
                out[("mirrors", 0)] = (p.mirrors[0] + 0.5, p.mirrors[1] + 0.5, "mirrors")
            for i, (x, y) in enumerate(p.statues):
                out[("statue", i)] = (x + 0.5, y + 0.5, "statue")
        return out
    return _cached(world, "revel_sites", make)


def fountains(world) -> list[tuple[float, float]]:
    """The middles of Pandemonium's wine fountains."""
    def make():
        p = _plan(world)
        return [(fx + 0.5, float(fy)) for fx, fy in p.fountains] if p is not None else []
    return _cached(world, "wine_fountains", make)


def lures(world) -> list[tuple[float, float]]:
    """What tempts a hero (systems/temptation.py): the banquet tables, the
    bandstands, the wine fountains, and every few tiles along the endless
    banquet's table."""
    def make():
        out = [(x, y) for x, y, kind in sites(world).values() if kind in ("table", "band")]
        out += fountains(world)
        for x, y, kind in sites(world).values():
            if kind == "banquet":
                out += [(x + k, y) for k in range(-28, 29, 7)]
        return out
    return _cached(world, "lures", make)


def _revels(world) -> dict:
    return _cached(world, "revels", dict)


def frenzied(world, home) -> bool:
    return home in _revels(world)


def frenzy(world, home) -> list:
    """Wake a group, for good; a bandstand's frenzy carries to every group
    within REVEL[2] tiles of it. The homes newly woken."""
    g = _revels(world)
    if home in g:
        return []
    g[home] = True
    woke = [home]
    here = sites(world).get(home)
    if here is not None and here[2] == "band":
        for other, (x, y, _) in sites(world).items():
            if other not in g and math.hypot(x - here[0], y - here[1]) <= config.REVEL[2]:
                g[other] = True
                woke.append(other)
    return woke


def wake_reach(world, home) -> float:
    """How close a hero may come before a group wakes: REVEL[0], x REVEL[1]
    where the music plays (a bandstand's group, or near a bandstand)."""
    def make():
        out = {}
        s = sites(world)
        bands = [(x, y) for x, y, kind in s.values() if kind == "band"]
        for h, (x, y, kind) in s.items():
            music = any(math.hypot(x - bx, y - by) <= config.REVEL[2] for bx, by in bands)
            out[h] = config.REVEL[0] * (config.REVEL[1] if music else 1.0)
        return out
    return _cached(world, "revel_reach", make).get(home, config.REVEL[0])


def residents(layout, zone) -> list[tuple[str, float, float]]:
    """Pandemonium's revellers, (key, x, y), at their homes (rostered with
    their chunks by systems/spawner): feasters and drinkers seated round
    each banquet table (a toastmaster at every REVEL_TABLE[2]-th), each
    bandstand's band on its stage (the piper in front, drummers behind the
    drums, dancers round them), the endless banquet's guests along both
    sides of its table, dancers in the hall of mirrors. Worked out once."""
    if zone.key != "pandemonium":
        return []
    from ..world.zones import plan_of
    p = plan_of(layout, zone)
    if getattr(p, "revellers", None) is None:
        p.revellers = _seat(p, random.Random(hash_coords(layout.seed, 0xFEA5, zone.salt)))
        p.revel_homes = {(round(x, 2), round(y, 2)): home for _, x, y, home in p.revellers}
    return [r[:3] for r in p.revellers]


def _seat(p, rng: random.Random) -> list:
    out = []
    keys, weights = list(config.REVEL_FEAST), list(config.REVEL_FEAST.values())
    lo, hi, every = config.REVEL_TABLE
    for i, (x, y) in enumerate(p.tables):
        seats = [(x + dx + 0.5, y + side) for side in (-1.6, 1.6) for dx in (-4, -2, 0, 2, 4)]
        rng.shuffle(seats)
        for k in range(rng.randint(lo, hi)):
            key = "toastmaster" if k == 0 and i % every == 0 else rng.choices(keys, weights)[0]
            out.append((key, *seats[k], ("table", i)))
    drummers, pairs, masked = config.REVEL_BAND
    for i, (x, y) in enumerate(p.bandstands):
        home, cx, cy = ("band", i), x + 0.5, y + 0.5
        out.append(("piper", cx, cy + 3.0, home))
        for k in range(drummers):
            out.append(("band_drummer", cx - 1.5 + 3.0 * k, cy - 2.6, home))
        spots = [(cx + math.cos(a) * 4.6, cy + math.sin(a) * 4.0) for a in (0.0, math.pi, 3.9, 5.5)]
        for k in range(pairs):
            out += [("dancer", *spots[k], home)] * 2           # (a pair: one spot, two dancers)
        for k in range(masked):
            out.append(("masked_dancer", *spots[pairs + k], home))
    if p.banquet is not None:
        sx, sy = p.banquet
        n, toasts = config.REVEL_BANQUET
        seats = [(sx - 26 + 52 * k / (n - 1) + 0.5, sy + side) for side in (-1.6, 1.6)
                 for k in range(n)]
        toasting = set(rng.sample(range(len(seats)), toasts))
        for k, (x, y) in enumerate(seats):
            key = "toastmaster" if k in toasting else rng.choices(keys, weights)[0]
            out.append((key, x, y, ("banquet", 0)))
    if p.mirrors is not None:
        mx, my = p.mirrors
        pairs, masked = config.REVEL_MIRRORS
        for k in range(pairs + masked):
            x, y = mx + rng.uniform(-15, 15) + 0.5, my + rng.uniform(-7, 7) + 0.5
            out += [("dancer", x, y, ("mirrors", 0))] * 2 if k < pairs \
                else [("masked_dancer", x, y, ("mirrors", 0))]
        # (M30.3: the Beloved, admired by the Vain, in the middle of it all)
        out.append(("beloved", mx + 0.5, my + 0.5, ("mirrors", 0)))
        for k in range(config.REVEL_STATUE[3]):
            a = k * math.tau / config.REVEL_STATUE[3]
            out.append(("vain", mx + 0.5 + math.cos(a) * 3.0, my + 0.5 + math.sin(a) * 2.0,
                        ("mirrors", 0)))
    out += _statues(p)
    out += _hosts(p)
    return out


def _statues(p) -> list:
    """M30.3: the vain and the greedy at the gilded statues (their plinths)."""
    out = []
    vains, gilded, beloved, admirers = config.REVEL_STATUE
    for i, (x, y) in enumerate(p.statues):
        home = ("statue", i)
        if i % beloved == 0:
            out.append(("beloved", x + 0.5, y + 1.9, home))
            for sx, sy in ((x - 1.5, y + 1.5), (x + 3.5, y + 1.5), (x + 0.5, y - 1.5))[:admirers]:
                out.append(("vain", sx, sy, home))
        else:
            out += [("vain", x - 1.5, y + 1.5, home)] * min(vains, 1)
            out.append(("hoarder", x + 2.5, y + 1.5, home))
        if i % gilded == 0:
            out.append(("gilded_reveller", x - 2.5, y + 0.5, home))
    return out


def _hosts(p) -> list:
    """M30.3: the demon hosts at their posts by the groups."""
    out = []
    cup, carve, bounce, master = config.REVEL_HOSTS
    for i, (x, y) in enumerate(p.tables):
        home = ("table", i)
        if i % cup == 0:
            out.append(("cupbearer", x + 5.5, y + 2.5, home))
        if i % carve == 1:
            out.append(("carver", x - 4.5, y + 2.5, home))
        if i % bounce == 2:
            out.append(("bouncer", x + 0.5, y - 2.5, home))
    for i, (x, y) in enumerate(p.bandstands):
        if i % master == 0:
            out.append(("master_of_revels", x - 2.5, y + 3.5, ("band", i)))
    if p.banquet is not None:
        sx, sy = p.banquet
        out.append(("bouncer", sx - 30.5, sy - 5.5, ("banquet", 0)))
        out += [("carver", sx - 28.5, sy + 4.5, ("banquet", 0)),
                ("carver", sx + 28.5, sy + 4.5, ("banquet", 0))]
    if p.mirrors is not None:
        out.append(("bouncer", p.mirrors[0] - 18.5, p.mirrors[1] + 0.5, ("mirrors", 0)))
    return out


def home_of(world, x: float, y: float):
    """The group of the reveller that was rostered at (x, y); one made some
    other way belongs to the nearest group within 14 tiles (or None)."""
    p = _plan(world)
    if p is not None:
        residents(world.layout, p.zone)
        h = p.revel_homes.get((round(x, 2), round(y, 2)))
        if h is not None:
            return h
    near = [(math.hypot(sx - x, sy - y), h) for h, (sx, sy, _) in sites(world).items()]
    near = [n for n in near if n[0] <= 14.0]
    return min(near)[1] if near else None


def _table_near(world, x: float, y: float, reach: float) -> bool:
    r = math.ceil(reach)
    tx, ty = math.floor(x), math.floor(y)
    return any(world.tile_at(tx + i, ty + j) is tiles.BANQUET_TABLE
               for j in range(-r, r + 1) for i in range(-r, r + 1)
               if math.hypot(i, j) <= reach)


def _free(world, x: float, y: float) -> bool:
    return not world.tile_at(math.floor(x), math.floor(y)).solid


# --- The trance ----------------------------------------------------------------------------


class Reveller(Angel):
    """In the trance -> turning (REVEL[3] s) -> frenzied, shared by its
    group; see the module's docstring. Subclasses write `trance_turn` and
    `frenzied_turn`. Its pictures are its sprite and sprite + "_frenzied".
    It never bleeds (Paradise's stains), and drinks at the wine fountains."""

    revel = True                     # (render/paradise.py leaves these to render/pandemonium.py)
    bleed = 0.0

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.spawn_pt = (self.x, self.y)
        self.home = None              # its group (worked out on its first turn)
        self.provoked = False         # hit in the trance: its group wakes
        self.toasted = 0.0            # s of a toast's burst of speed left
        self.adored = 0.0             # s its group's Beloved still lives (it keeps this up)
        self.waves: list[list] = []   # rings going out: [x, y, r, reach, speed, damage, tempt, hit]
        self.phase = self.rng.uniform(0.0, math.tau)

    @property
    def frenzied(self) -> bool:
        return self.unveiled

    @property
    def speed(self) -> float:
        s = self.espec.speed * (1.0 if self.unveiled else config.REVEL[4])
        s *= config.BELOVED[6] if self.adored > 0 and self.unveiled else 1.0
        return s * (config.TOAST[3] if self.toasted > 0 else 1.0)

    def sprite_now(self) -> str:
        base = self.espec.sprite
        if self.unveiling:                       # (heads snapping round: flickering)
            return base + "_frenzied" if int(self.clock * 14) % 2 else base
        return base + "_frenzied" if self.unveiled else base

    def take_damage(self, amount, source, from_angle):
        dealt = super(Angel, self).take_damage(amount, source, from_angle)
        if dealt > 0 and self.serene:
            self.provoked = True
        return dealt

    def find_font(self, world, reach: float):
        near = [f for f in fountains(world) if math.hypot(f[0] - self.x, f[1] - self.y) <= reach]
        return min(near, key=lambda f: math.hypot(f[0] - self.x, f[1] - self.y)) if near else None

    def _bleed(self, ctx: AIContext) -> None:
        pass

    def _near(self, ctx: AIContext) -> bool:
        reach = wake_reach(ctx.world, self.home)
        return any(p.alive and math.hypot(p.x - self.x, p.y - self.y) <= reach for p in ctx.players)

    def turn(self) -> None:
        """Start its turn (once)."""
        if self.state == "serene":
            self.state, self.timer = "unveiling", config.REVEL[3]
            self.windup = 0.0
            self.alert = True

    def think(self, ctx: AIContext, dt: float) -> None:
        PlainsCreature.think(self, ctx, dt)      # (_moved, the cooldown)
        self.sense(ctx, dt)
        self.clock += dt
        self.toasted = max(0.0, self.toasted - dt)
        self.adored = max(0.0, self.adored - dt)
        self._fly_lobs(ctx, dt)
        self._tick_waves(ctx, dt)
        self.always(ctx, dt)
        if self.home is None:
            self.home = home_of(ctx.world, *self.spawn_pt) or ("alone", id(self))
        if self.serene:
            if not (self.provoked or frenzied(ctx.world, self.home) or self._near(ctx)):
                self.trance_turn(ctx, dt)
                return
            frenzy(ctx.world, self.home)
            self.turn()
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
                ctx.effects.append(Effect("frenzy", self.x, self.y, size=self.hit_radius + 1.0))
                ctx.events.append("hex")
                self.on_unveil(ctx)
            return
        if not self._drink(ctx, dt):
            self.drinking = False
            self.frenzied_turn(ctx, dt)

    def unveiled_turn(self, ctx: AIContext, dt: float) -> None:
        self.frenzied_turn(ctx, dt)

    def trance_turn(self, ctx: AIContext, dt: float) -> None:
        """Feasting where it sits, facing its table."""
        here = sites(ctx.world).get(self.home)
        if here is not None:
            self.facing = self.angle_to(here[0], here[1])

    def frenzied_turn(self, ctx: AIContext, dt: float) -> None:
        t = self.target
        if t is None:
            self.roam(ctx, dt)
            return
        self.go(ctx, t.x, t.y, dt, self.speed)

    def twirl(self, ctx: AIContext, dt: float, radius: float = 0.7, rate: float = 2.2) -> None:
        """A dancer's trance: round and round its spot (a pair's two dancers
        opposite each other)."""
        a = self.clock * rate + self.phase
        sx, sy = self.spawn_pt
        self.go(ctx, sx + math.cos(a) * radius, sy + math.sin(a) * radius, dt,
                max(self.speed, 1.5))
        self.facing = a + math.pi / 2

    # --- Rings going out (a belly-slam, a drumbeat, a wave of wine) ----------------------

    def wave(self, ctx: AIContext, reach: float, speed: float, damage: float, kind: str,
             tempt: float = 0.0) -> None:
        """A ring going out from it at `speed` tiles/s to `reach`: each hero
        it reaches is hit once -- unless mid-roll just then (drawn: effect
        `kind`, which lasts reach / speed s)."""
        self.waves.append([self.x, self.y, 0.0, reach, speed, damage, tempt, set()])
        ctx.effects.append(Effect(kind, self.x, self.y, size=reach))

    def _tick_waves(self, ctx: AIContext, dt: float) -> None:
        from ..systems import temptation
        for w in self.waves:
            w[2] += w[4] * dt
            for h in ctx.players:
                if id(h) in w[7] or not h.alive:
                    continue
                d = math.hypot(h.x - w[0], h.y - w[1])
                if d - h.hit_radius > w[2]:
                    continue                      # (not there yet)
                w[7].add(id(h))
                if h.hittable:
                    _numbered_hit(h, w[5] * self.damage_mult, self,
                                  math.atan2(h.y - w[1], h.x - w[0]), ctx)
                    if w[6]:
                        temptation.add(h, w[6])
        self.waves = [w for w in self.waves if w[2] < w[3]]

    def on_death(self, ctx: AIContext) -> None:
        for b in self.lobs:                      # (what's in the air still comes down)
            self.landed(ctx, b[2], b[3], b[6])
        self.lobs = []
        if not self.unveiled and self.home is not None:
            frenzy(ctx.world, self.home)         # (killed in the trance: its group turns)
        ctx.effects.append(Effect("spill", self.x, self.y, size=self.hit_radius))


# --- Feasters and drinkers -----------------------------------------------------------------


class Glutton(Reveller):
    """Lumbers after you and belly-slams (GLUTTON); gorges at tables."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.gorging = 0.0
        self.gorge_cd = 0.0

    def frenzied_turn(self, ctx: AIContext, dt: float) -> None:
        reach, ring, speed, low, table_reach, eat, heal, every = config.GLUTTON
        self.gorge_cd = max(0.0, self.gorge_cd - dt)
        if self.gorging > 0:
            self.gorging -= dt
            if not wounded(self):
                self.hp = min(float(self.max_hp), self.hp + self.max_hp * heal / eat * dt)
            return
        if self.windup > 0:
            self.windup -= dt
            self.tell = max(self.windup, 1e-3)
            if self.windup <= 0:
                self.tell = 0.0
                self.wave(ctx, ring, speed, self.espec.damage, "belly_slam")
                self.cooldown = self.espec.cooldown
                ctx.events.append("boulder")
            return
        if self.hp < self.max_hp * low and self.gorge_cd <= 0 \
                and _table_near(ctx.world, self.x, self.y, table_reach):
            self.gorging, self.gorge_cd = eat, every
            ctx.effects.append(Effect("toast", self.x, self.y - 2.0, label="GORGING"))
            return
        t = self.target
        if t is None:
            self.roam(ctx, dt)
            return
        self.go(ctx, t.x, t.y, dt, self.speed)
        self.facing = self.angle_to(t.x, t.y)
        if self.cooldown <= 0 and self.dist_to(t) <= reach:
            self.windup = self.espec.windup


class Drunkard(Reveller):
    """Weaves at a distance, lobbing bottles that leave wine puddles."""

    def frenzied_turn(self, ctx: AIContext, dt: float) -> None:
        amp, period, lo, hi, flight, wide, life, slow, tempt = config.DRUNKARD
        t = self.target
        if t is None:
            self.roam(ctx, dt)
            return
        d = self.dist_to(t)
        a = self.angle_to(t.x, t.y)
        step = 2.0 if d > hi else -2.0 if d < lo else 0.0
        sway = math.sin(self.clock * math.tau / period + self.phase) * amp \
            + math.sin(self.clock * 4.3 + self.phase * 2) * amp * 0.4    # (a stagger on top)
        gx = self.x + math.cos(a) * step - math.sin(a) * sway
        gy = self.y + math.sin(a) * step + math.cos(a) * sway
        self.go(ctx, gx, gy, dt, self.speed)
        self.facing = a
        if self.cooldown <= 0 and d <= hi + 3:
            spread = self.rng.uniform(0.0, 1.2)
            b = self.rng.uniform(0.0, math.tau)
            self.lob(t.x + math.cos(b) * spread, t.y + math.sin(b) * spread, flight, "bottle")
            self.cooldown = self.espec.cooldown
            ctx.events.append("swing")

    def landed(self, ctx: AIContext, x: float, y: float, what: str) -> None:
        _, _, _, _, _, wide, life, slow, tempt = config.DRUNKARD
        ctx.events.append("fizzle")
        for h in ctx.players:
            if h.hittable and math.hypot(h.x - x, h.y - y) <= 0.8 + h.hit_radius:
                _numbered_hit(h, self.espec.damage * self.damage_mult, self,
                              math.atan2(h.y - y, h.x - x), ctx)
        if ctx.zones is not None:
            ctx.zones.append(Zone("wine_puddle", x, y, wide, life, 0.5, 0.0, self,
                                  slow=slow, tempt=tempt * 0.5))


class Toastmaster(Reveller):
    """Keeps back and calls toasts (TOAST): a burst of speed for the
    revellers round it, a wave of wine rolling out."""

    def frenzied_turn(self, ctx: AIContext, dt: float) -> None:
        lo, hi, reach, fast, burst, ring, speed, tempt = config.TOAST
        t = self.target
        if self.windup > 0:
            self.windup -= dt
            self.tell = max(self.windup, 1e-3)
            if self.windup <= 0:
                self.tell = 0.0
                for e in ctx.actors:
                    if isinstance(e, Reveller) and e.alive and e.unveiled \
                            and math.hypot(e.x - self.x, e.y - self.y) <= reach:
                        e.toasted = burst
                self.wave(ctx, ring, speed, self.espec.damage, "wine_wave", tempt)
                ctx.effects.append(Effect("toast", self.x, self.y - 2.5, label="A TOAST!"))
                ctx.events.append("chime")
                self.cooldown = self.espec.cooldown
            return
        if t is None:
            self.roam(ctx, dt)
            return
        self.keep(ctx, t, lo, hi, dt)
        if self.cooldown <= 0 and self.dist_to(t) <= hi + 4:
            self.windup = self.espec.windup


class Ravenous(Reveller):
    """Sprints in and latches on (RAVENOUS); a roll throws it off."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.latched = None
        self.offset = (0.0, 0.0)
        self.bite_t = 0.0
        self.dazed = 0.0

    def frenzied_turn(self, ctx: AIContext, dt: float) -> None:
        every, slow, most, fling, daze = config.RAVENOUS
        h = self.latched
        if h is not None:
            if not h.alive or h.rolling:
                self.shake(ctx)
                return
            self.x, self.y = h.x + self.offset[0], h.y + self.offset[1]
            self.facing = self.angle_to(h.x, h.y)
            h.slowed(slow, 0.3)
            self.bite_t -= dt
            if self.bite_t <= 0:
                self.bite_t = every
                _numbered_hit(h, self.espec.damage * self.damage_mult, self, self.facing, ctx)
                ctx.events.append("hit")
            return
        if self.dazed > 0:
            self.dazed -= dt
            return
        t = self.target
        if t is None:
            self.roam(ctx, dt)
            return
        self.go(ctx, t.x, t.y, dt, self.speed)
        reach = self.hit_radius + t.hit_radius + self.espec.attack_radius * 0.5
        if getattr(t, "hittable", False) and self.dist_to(t) <= reach and getattr(t, "faction", "") == "player":
            on = sum(1 for e in ctx.actors if isinstance(e, Ravenous) and e.latched is t)
            if on < most:
                a = self.rng.uniform(0.0, math.tau)
                self.latched = t
                self.offset = (math.cos(a) * t.hit_radius * 0.8, math.sin(a) * t.hit_radius * 0.6)
                self.bite_t = 0.2

    def shake(self, ctx: AIContext) -> None:
        """Thrown off (its hero rolled, or fell)."""
        h, self.latched = self.latched, None
        _, _, _, fling, daze = config.RAVENOUS
        dx, dy = self.x - h.x, self.y - h.y
        d = math.hypot(dx, dy) or 1.0
        x, y = self.x + dx / d * fling, self.y + dy / d * fling
        if _free(ctx.world, x, y):
            self.x, self.y = x, y
        self.dazed = daze
        if h.alive:
            ctx.effects.append(Effect("toast", h.x, h.y - 1.5, label="SHAKEN OFF!"))


# --- Dancers and musicians -------------------------------------------------------------------


class Dancer(Reveller):
    """Steps that repeat (DANCE_STEPS): circling one way, a dash through
    you, circling back, a dash; its ribbons cut whoever it touches."""

    STEPS = ("round", "dash", "back", "dash")

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.step = 0
        self.step_t = 0.0
        self.aim = 0.0
        self.around = 0.0             # where it is round you (radians)

    def trance_turn(self, ctx: AIContext, dt: float) -> None:
        self.twirl(ctx, dt)

    def on_unveil(self, ctx: AIContext) -> None:
        t = self.target
        self.around = self.angle_to(t.x, t.y) + math.pi if t is not None else 0.0
        self.step, self.step_t = 0, config.DANCE_STEPS[1]

    def frenzied_turn(self, ctx: AIContext, dt: float) -> None:
        radius, circle, tell, dash, fast = config.DANCE_STEPS
        t = self.target
        if t is None:
            self.roam(ctx, dt)
            return
        self.touch(ctx, self.espec.damage, self.espec.cooldown)
        move = self.STEPS[self.step]
        self.step_t -= dt
        if move in ("round", "back"):
            turn = (1.0 if move == "round" else -1.0) * self.speed / radius
            self.around += turn * dt
            self.go(ctx, t.x + math.cos(self.around) * radius, t.y + math.sin(self.around) * radius,
                    dt, self.speed)
            self.facing = self.angle_to(t.x, t.y)
            if self.step_t <= 0:
                self.step = (self.step + 1) % len(self.STEPS)
                self.step_t = tell + dash
                self.aim = self.angle_to(t.x, t.y)
                self.windup = tell
            return
        if self.windup > 0:                       # (its line shows)
            self.windup -= dt
            self.tell = max(self.windup, 1e-3)
            self.aim = self.angle_to(t.x, t.y)
            if self.windup <= 0:
                self.tell = 0.0
                ctx.events.append("swing")
            return
        self.go(ctx, self.x + math.cos(self.aim) * 3, self.y + math.sin(self.aim) * 3, dt, fast)
        self.facing = self.aim
        if self.step_t <= 0:
            self.around = self.angle_to(t.x, t.y) + math.pi
            self.step = (self.step + 1) % len(self.STEPS)
            self.step_t = circle


class MaskedDancer(Reveller):
    """Swaps places with another dancer in a flash, then stabs (MASKED)."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.aim = 0.0
        self.stab = 0.0               # s of the stab's dash left

    def trance_turn(self, ctx: AIContext, dt: float) -> None:
        self.twirl(ctx, dt, 0.5, 1.6)

    def frenzied_turn(self, ctx: AIContext, dt: float) -> None:
        reach, tell, length, fast = config.MASKED
        t = self.target
        if self.stab > 0:
            self.stab -= dt
            self.go(ctx, self.x + math.cos(self.aim) * 3, self.y + math.sin(self.aim) * 3, dt, fast)
            self.touch(ctx, self.espec.damage, 1.0)
            return
        if self.windup > 0:
            self.windup -= dt
            self.tell = max(self.windup, 1e-3)
            if self.windup <= 0:
                self.tell = 0.0
                self.stab = length / fast
                ctx.events.append("swing")
            return
        if t is None:
            self.roam(ctx, dt)
            return
        self.keep(ctx, t, 2.0, 5.0, dt)
        if self.cooldown <= 0:
            self.swap(ctx, t)
            self.aim = self.angle_to(t.x, t.y)
            self.windup = tell
            self.cooldown = self.espec.cooldown

    def swap(self, ctx: AIContext, t) -> None:
        """Change places with another dancer (its group's first) in a flash;
        with none near, flash to just behind its hero."""
        others = [e for e in ctx.actors if isinstance(e, (Dancer, MaskedDancer)) and e is not self
                  and e.alive and math.hypot(e.x - self.x, e.y - self.y) <= config.MASKED[0]]
        others.sort(key=lambda e: (e.home != self.home, math.hypot(e.x - t.x, e.y - t.y)))
        x0, y0 = self.x, self.y
        if others:
            o = others[0]
            self.x, self.y, o.x, o.y = o.x, o.y, x0, y0
        else:
            a = math.atan2(t.y - self.y, t.x - self.x)
            x, y = t.x + math.cos(a) * 2.5, t.y + math.sin(a) * 2.5
            if not _free(ctx.world, x, y):
                return
            self.x, self.y = x, y
        ctx.effects.append(Effect("mask_swap", x0, y0, size=1.2))
        ctx.effects.append(Effect("mask_swap", self.x, self.y, size=1.2))
        ctx.events.append("zap")


class BandDrummer(Reveller):
    """Never leaves its drums; frenzied, a ring goes out on every beat."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.beat = 0.0

    def go(self, ctx, gx, gy, dt, speed) -> bool:     # (it never moves)
        return False

    def trance_turn(self, ctx: AIContext, dt: float) -> None:
        self.facing = math.pi / 2                     # (facing out over the stage)

    def frenzied_turn(self, ctx: AIContext, dt: float) -> None:
        every, ring, speed = config.BEAT
        t = self.target
        if t is not None:
            self.facing = self.angle_to(t.x, t.y)
        self.beat += dt
        if self.beat >= every:
            self.beat -= every
            if t is not None:
                self.wave(ctx, ring, speed, self.espec.damage, "beat")
                ctx.events.append("boulder")


class Piper(Reveller):
    """Its song fills your temptation in a cone (PIPER), and it plays the
    frenzy on to the groups round it."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.song = 0.0               # s of singing left (> 0) / of rest left (< 0)
        self.aim = 0.0
        self.spread = config.PIPER[7]

    @property
    def singing(self) -> bool:
        return self.unveiled and self.song > 0

    def frenzied_turn(self, ctx: AIContext, dt: float) -> None:
        from ..systems import temptation
        lo, hi, cone, reach, sing, rest, tempt, every, carry = config.PIPER
        self.spread -= dt
        if self.spread <= 0:
            self.spread = every
            self.carry(ctx, carry)
        t = self.target
        if t is None:
            self.song = 0.0
            self.roam(ctx, dt)
            return
        self.keep(ctx, t, lo, hi, dt)
        want = self.angle_to(t.x, t.y)
        turn = (want - self.aim + math.pi) % math.tau - math.pi
        self.aim += max(-1.2 * dt, min(1.2 * dt, turn))   # (the cone follows you, slowly)
        if self.song > 0:
            self.song -= dt
            if self.song <= 0:
                self.song = -rest
            for h in ctx.players:
                d = math.hypot(h.x - self.x, h.y - self.y)
                off = abs((math.atan2(h.y - self.y, h.x - self.x) - self.aim + math.pi) % math.tau - math.pi)
                if h.alive and d <= reach and off <= math.radians(cone) / 2 \
                        and self.can_see(ctx.world, h):
                    temptation.add(h, tempt * dt)
        else:
            self.song += dt
            if self.song >= 0:
                self.song = sing
                self.aim = want
                ctx.events.append("chime")

    def carry(self, ctx: AIContext, reach: float) -> None:
        """Play the frenzy on to the nearest group still in the trance."""
        here = (self.x, self.y)
        near = [(math.hypot(x - here[0], y - here[1]), h, x, y)
                for h, (x, y, _) in sites(ctx.world).items() if not frenzied(ctx.world, h)]
        near = [n for n in near if n[0] <= reach]
        if not near:
            return
        _, home, x, y = min(near)
        frenzy(ctx.world, home)
        ctx.effects.append(Effect("toast", x, y - 2.5, label="THE SONG CARRIES"))
        ctx.events.append("chime")


# --- The vain and the greedy (M30.3) -------------------------------------------------------


def _in_cone(x0: float, y0: float, aim: float, half: float, reach: float, x: float, y: float) -> bool:
    d = math.hypot(x - x0, y - y0)
    off = abs((math.atan2(y - y0, x - x0) - aim + math.pi) % math.tau - math.pi)
    return d <= reach and off <= half


class Vain(Reveller):
    """Its mirror flashes in a marked cone (VAIN): dazzles, turns shots
    back. With a Beloved to admire, it circles it instead of keeping back."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.aim = 0.0
        self.admires = None           # its group's Beloved (set by the Beloved)
        self.around = self.rng.uniform(0.0, math.tau)

    def frenzied_turn(self, ctx: AIContext, dt: float) -> None:
        lo, hi, cone, reach, dazzle, wobble, back = config.VAIN
        t = self.target
        if self.windup > 0:
            self.windup -= dt
            self.tell = max(self.windup, 1e-3)
            if self.windup <= 0:
                self.tell = 0.0
                self.flash(ctx)
            return
        b = self.admires
        if b is not None and b.alive:
            self.around += dt * 1.6
            r = config.BELOVED[4]
            self.go(ctx, b.x + math.cos(self.around) * r, b.y + math.sin(self.around) * r, dt,
                    max(self.speed, 4.0))
        elif t is not None:
            self.keep(ctx, t, lo, hi, dt)
        else:
            self.roam(ctx, dt)
            return
        if t is not None and self.cooldown <= 0 and self.dist_to(t) <= reach:
            self.aim = self.angle_to(t.x, t.y)
            self.windup = self.espec.windup
            self.cooldown = self.espec.cooldown

    def flash(self, ctx: AIContext) -> None:
        _, _, cone, reach, dazzle, _, back = config.VAIN
        half = math.radians(cone) / 2
        for h in ctx.players:
            if h.alive and _in_cone(self.x, self.y, self.aim, half, reach, h.x, h.y):
                h.dazzled = dazzle
                ctx.effects.append(Effect("toast", h.x, h.y - 1.5, label="DAZZLED!"))
        for p in ctx.projectiles or ():
            owner = getattr(p, "owner", None)
            if p.alive and getattr(owner, "faction", "") == "player" \
                    and _in_cone(self.x, self.y, self.aim, half, reach, p.x, p.y):
                p.angle += math.pi                    # (turned back at its shooter)
                p.dir_x, p.dir_y = -p.dir_x, -p.dir_y
                p.owner = self
                p.damage *= back
                p.travelled = 0.0
        ctx.effects.append(Effect("mirror_flash", self.x, self.y, angle=self.aim, size=reach))
        ctx.events.append("zap")


class GildedReveller(Reveller):
    """Posing as a statue; frenzied, a gold shell (GILDED) soaks its hits
    until it cracks off; slow, heavy slams."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.shell = None             # gold left (worked out on its first turn, once toughened)
        self.facing = math.pi / 2

    @property
    def speed(self) -> float:
        cracked = self.shell is not None and self.shell <= 0
        return super().speed * (config.GILDED[4] if cracked else 1.0)

    def sprite_now(self) -> str:
        base = self.espec.sprite
        if self.serene:
            return base                                   # (a statue, to the eye)
        if self.shell is not None and self.shell <= 0:
            return base + "_cracked"
        return base + "_frenzied"

    def take_damage(self, amount, source, from_angle):
        if self.shell is None:
            self.shell = self.max_hp * config.GILDED[0]
        if self.shell > 0 and amount > 0 and self.alive:
            self.shell -= amount
            self.hurt_flash = 0.12
            if self.serene:
                self.provoked = True
            if self.shell <= 0:
                self.cracked = True
            return amount
        return super().take_damage(amount, source, from_angle)

    def trance_turn(self, ctx: AIContext, dt: float) -> None:
        if self.shell is None:
            self.shell = self.max_hp * config.GILDED[0]

    def frenzied_turn(self, ctx: AIContext, dt: float) -> None:
        _, near, ring, speed, _ = config.GILDED
        if self.shell is None:
            self.shell = self.max_hp * config.GILDED[0]
        if getattr(self, "cracked", False):
            self.cracked = False
            ctx.effects.append(Effect("gold_crack", self.x, self.y, size=self.hit_radius + 1.0))
            ctx.events.append("break")
        if self.windup > 0:
            self.windup -= dt
            self.tell = max(self.windup, 1e-3)
            if self.windup <= 0:
                self.tell = 0.0
                self.wave(ctx, ring, speed, self.espec.damage, "gold_slam")
                self.cooldown = self.espec.cooldown
                ctx.events.append("boulder")
            return
        t = self.target
        if t is None:
            self.roam(ctx, dt)
            return
        self.go(ctx, t.x, t.y, dt, self.speed)
        if self.cooldown <= 0 and self.dist_to(t) <= near:
            self.windup = self.espec.windup


class Hoarder(Reveller):
    """Throws fistfuls of coins (HOARD) that hurt and lie there, tripping."""

    def frenzied_turn(self, ctx: AIContext, dt: float) -> None:
        lo, hi, n, spread, flight, *_ = config.HOARD
        t = self.target
        if t is None:
            self.roam(ctx, dt)
            return
        self.keep(ctx, t, lo, hi, dt)
        if self.cooldown <= 0 and self.dist_to(t) <= hi + 3:
            a0 = self.angle_to(t.x, t.y)
            d = self.dist_to(t)
            for k in range(n):
                a = a0 + math.radians(spread) * (k / (n - 1) - 0.5)
                r = d * self.rng.uniform(0.85, 1.15)
                self.lob(self.x + math.cos(a) * r, self.y + math.sin(a) * r, flight, "coin")
            self.cooldown = self.espec.cooldown
            ctx.events.append("swing")

    def landed(self, ctx: AIContext, x: float, y: float, what: str) -> None:
        _, _, _, _, _, wide, life, trip, _ = config.HOARD
        for h in ctx.players:
            if h.hittable and math.hypot(h.x - x, h.y - y) <= 0.6 + h.hit_radius:
                _numbered_hit(h, self.espec.damage * self.damage_mult, self,
                              math.atan2(h.y - y, h.x - x), ctx)
        if ctx.zones is not None:
            ctx.zones.append(Zone("loose_coins", x, y, wide, life, 0.25, 0.0, self, slow=trip))


class Beloved(Reveller):
    """Its admirers circle it and take its hits (BELOVED); while it lives its
    group is faster. Fans of glitter."""

    def admirers(self, actors) -> list:
        return [e for e in actors if isinstance(e, Vain) and e.alive and e.home == self.home]

    def always(self, ctx: AIContext, dt: float) -> None:
        if self.home is None:
            return
        for e in ctx.actors:
            if isinstance(e, Reveller) and e.alive and e.home == self.home and e is not self:
                e.adored = 0.3
                if isinstance(e, Vain):
                    e.admires = self
        self._actors = ctx.actors

    def take_damage(self, amount, source, from_angle):
        near = [e for e in self.admirers(getattr(self, "_actors", ()))
                if math.hypot(e.x - self.x, e.y - self.y) <= config.BELOVED[5]]
        if near and amount > 0:
            shield = min(near, key=lambda e: math.hypot(e.x - self.x, e.y - self.y))
            if self.serene:
                self.provoked = True
            return shield.take_damage(amount, source, from_angle)
        return super().take_damage(amount, source, from_angle)

    def frenzied_turn(self, ctx: AIContext, dt: float) -> None:
        lo, hi, n, fan, *_ = config.BELOVED
        t = self.target
        if t is None:
            self.roam(ctx, dt)
            return
        self.keep(ctx, t, lo, hi, dt)
        if self.cooldown <= 0 and self.dist_to(t) <= hi + 5:
            a0 = self.angle_to(t.x, t.y)
            shell = config.PANDEMONIUM_SHOTS["glitter"]
            for k in range(n):
                patterns.shoot(self, self.x, self.y,
                               a0 + math.radians(fan) * (k / (n - 1) - 0.5), shell, ctx.projectiles)
            self.cooldown = self.espec.cooldown
            ctx.events.append(shell.sound)


# --- The demon hosts (M30.3) ----------------------------------------------------------------


class Host(Reveller):
    """Never in the trance: alert from the start, at its post by its group
    (back there when nobody's about). One picture. It doesn't drink."""

    drinks = False

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.state = "unveiled"
        self.alert = True

    def sprite_now(self) -> str:
        return self.espec.sprite

    def idle(self, ctx: AIContext, dt: float) -> None:
        sx, sy = self.spawn_pt
        if math.hypot(self.x - sx, self.y - sy) > 0.6:
            self.go(ctx, sx, sy, dt, self.speed * 0.6)


class Cupbearer(Host):
    """Refills the hurt revellers near it; throws tempting wine (CUPBEARER)."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.pouring = 0.0
        self.pour_cd = 0.0
        self.guest = None

    def frenzied_turn(self, ctx: AIContext, dt: float) -> None:
        reach, low, pour, heal, every, lo, hi, tempt = config.CUPBEARER
        self.pour_cd = max(0.0, self.pour_cd - dt)
        g = self.guest
        if g is not None and (not g.alive or g.hp >= g.max_hp * 0.95):
            self.guest = g = None
            self.pouring = 0.0
        if g is None and self.pour_cd <= 0:
            hurt = [e for e in ctx.actors if isinstance(e, Reveller) and not isinstance(e, Host)
                    and e.alive and e.unveiled and e.hp < e.max_hp * low
                    and math.hypot(e.x - self.x, e.y - self.y) <= reach]
            if hurt:
                self.guest = g = min(hurt, key=lambda e: e.hp / e.max_hp)
        if g is not None:
            if math.hypot(g.x - self.x, g.y - self.y) > 1.6:
                self.go(ctx, g.x, g.y, dt, self.speed)
                return
            self.pouring += dt
            self.drinking = True                           # (the "+" over it)
            if not wounded(g):
                g.hp = min(float(g.max_hp), g.hp + g.max_hp * heal / pour * dt)
            if self.pouring >= pour:
                self.guest, self.pouring, self.pour_cd = None, 0.0, every
                self.drinking = False
            return
        self.drinking = False
        t = self.target
        if t is None:
            self.idle(ctx, dt)
            return
        self.keep(ctx, t, lo, hi, dt)
        if self.cooldown <= 0 and self.dist_to(t) <= hi + 3:
            self.lob(t.x, t.y, 0.7, "wine")
            self.cooldown = self.espec.cooldown
            ctx.events.append("swing")

    def landed(self, ctx: AIContext, x: float, y: float, what: str) -> None:
        from ..systems import temptation
        for h in ctx.players:
            if h.hittable and math.hypot(h.x - x, h.y - y) <= 1.0 + h.hit_radius:
                _numbered_hit(h, self.espec.damage * self.damage_mult, self,
                              math.atan2(h.y - y, h.x - x), ctx)
                temptation.add(h, config.CUPBEARER[7])
        ctx.events.append("fizzle")


class Carver(Host):
    """Lunging cleaves; cleavers that fly out curving and come back (CARVER)."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.aim = 0.0
        self.lunge = 0.0
        self.cleavers: list[list] = []   # [x, y, angle, s out, coming back, hit]

    def always(self, ctx: AIContext, dt: float) -> None:
        _, _, _, out, speed, curve = config.CARVER
        for c in self.cleavers:
            if not c[4]:
                c[3] += dt
                c[2] += curve * dt
                c[0] += math.cos(c[2]) * speed * dt
                c[1] += math.sin(c[2]) * speed * dt
                if c[3] >= out:
                    c[4], c[5] = True, set()
            else:
                d = math.hypot(self.x - c[0], self.y - c[1]) or 1.0
                c[0] += (self.x - c[0]) / d * speed * 1.2 * dt
                c[1] += (self.y - c[1]) / d * speed * 1.2 * dt
            for h in ctx.players:
                if id(h) not in c[5] and h.hittable \
                        and math.hypot(h.x - c[0], h.y - c[1]) <= 0.6 + h.hit_radius:
                    c[5].add(id(h))
                    _numbered_hit(h, self.espec.damage * 0.7 * self.damage_mult, self, c[2], ctx)
        self.cleavers = [c for c in self.cleavers
                         if not (c[4] and math.hypot(self.x - c[0], self.y - c[1]) < 0.8)]

    def frenzied_turn(self, ctx: AIContext, dt: float) -> None:
        near, length, fast, *_ = config.CARVER
        if self.lunge > 0:
            self.lunge -= dt
            self.go(ctx, self.x + math.cos(self.aim) * 3, self.y + math.sin(self.aim) * 3, dt, fast)
            self.touch(ctx, self.espec.damage, 1.0)
            return
        if self.windup > 0:
            self.windup -= dt
            self.tell = max(self.windup, 1e-3)
            if self.windup <= 0:
                self.tell = 0.0
                self.lunge = length / fast
                ctx.events.append("swing")
            return
        t = self.target
        if t is None:
            self.idle(ctx, dt)
            return
        self.go(ctx, t.x, t.y, dt, self.speed)
        self.facing = self.angle_to(t.x, t.y)
        if self.cooldown <= 0:
            if self.dist_to(t) <= near:
                self.aim = self.angle_to(t.x, t.y)
                self.windup = self.espec.windup
            elif not self.cleavers:
                side = self.rng.choice((-1.0, 1.0))
                self.cleavers.append([self.x, self.y, self.angle_to(t.x, t.y) - side * 0.6,
                                      0.0, False, set()])
                ctx.events.append("swing")
            self.cooldown = self.espec.cooldown


class Bouncer(Host):
    """Charges along a shown line; throws whoever it catches at the nearest
    group still in the trance (BOUNCER)."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.aim = 0.0
        self.charge = 0.0
        self.dazed = 0.0

    def frenzied_turn(self, ctx: AIContext, dt: float) -> None:
        reach, length, fast, throw, daze = config.BOUNCER
        if self.dazed > 0:
            self.dazed -= dt
            return
        if self.charge > 0:
            self.charge -= dt
            moved = self.go(ctx, self.x + math.cos(self.aim) * 3, self.y + math.sin(self.aim) * 3,
                            dt, fast)
            for h in ctx.players:
                if h.hittable and math.hypot(h.x - self.x, h.y - self.y) <= self.hit_radius + h.hit_radius:
                    self.throw(ctx, h)
                    self.charge = 0.0
                    return
            if self._moved < fast * dt * 0.3:               # (into a wall)
                self.charge, self.dazed = 0.0, daze
            return
        if self.windup > 0:
            self.windup -= dt
            self.tell = max(self.windup, 1e-3)
            if self.windup <= 0:
                self.tell = 0.0
                self.charge = length / fast
                ctx.events.append("boulder")
            return
        t = self.target
        if t is None:
            self.idle(ctx, dt)
            return
        self.go(ctx, t.x, t.y, dt, self.speed)
        if self.cooldown <= 0 and self.dist_to(t) <= reach:
            self.aim = self.angle_to(t.x, t.y)
            self.windup = self.espec.windup
            self.cooldown = self.espec.cooldown

    def throw(self, ctx: AIContext, h) -> None:
        from ..systems.combat import push
        _numbered_hit(h, self.espec.damage * self.damage_mult, self, self.aim, ctx)
        asleep = [(math.hypot(x - h.x, y - h.y), x, y) for home, (x, y, _) in sites(ctx.world).items()
                  if not frenzied(ctx.world, home)]
        if asleep:
            _, x, y = min(asleep)
            a = math.atan2(y - h.y, x - h.x)
        else:
            a = self.aim
        dist = config.BOUNCER[3]
        push(h, ctx.world, math.cos(a) * dist, math.sin(a) * dist, full=True)
        ctx.effects.append(Effect("toast", h.x, h.y - 1.5, label="THROWN!"))


class MasterOfRevels(Host):
    """Its bell wakes every group near it and snaps entranced heroes out;
    fireworks on marked circles (MASTER)."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.bell = 0.0               # s to its next ring
        self.ringing = 0.0            # its bell's tell left
        self.marks: list[list] = []   # fireworks: [x, y, s left]

    def always(self, ctx: AIContext, dt: float) -> None:
        r = config.MASTER[5]
        for m in self.marks:
            m[2] -= dt
            if m[2] <= 0:
                for h in ctx.players:
                    if h.hittable and math.hypot(h.x - m[0], h.y - m[1]) <= r + h.hit_radius:
                        _numbered_hit(h, self.espec.damage * self.damage_mult, self,
                                      math.atan2(h.y - m[1], h.x - m[0]), ctx)
                ctx.effects.append(Effect("fireworks", m[0], m[1], size=r))
                ctx.events.append("boulder")
        self.marks = [m for m in self.marks if m[2] > 0]

    def frenzied_turn(self, ctx: AIContext, dt: float) -> None:
        reach, every, lo, hi, n, r, mark, spread = config.MASTER
        self.bell -= dt
        if self.ringing > 0:
            self.ringing -= dt
            self.tell = max(self.ringing, 1e-3)
            if self.ringing <= 0:
                self.tell = 0.0
                self.ring(ctx)
            return
        t = self.target
        if t is None:
            self.idle(ctx, dt)
            return
        if self.bell <= 0:
            self.ringing, self.bell = self.espec.windup, every
            return
        self.keep(ctx, t, lo, hi, dt)
        if self.cooldown <= 0 and self.dist_to(t) <= hi + 4:
            self.marks.append([t.x, t.y, mark])
            for _ in range(n - 1):
                a = self.rng.uniform(0.0, math.tau)
                d = self.rng.uniform(1.0, spread)
                self.marks.append([t.x + math.cos(a) * d, t.y + math.sin(a) * d, mark])
            self.cooldown = self.espec.cooldown

    def ring(self, ctx: AIContext) -> None:
        """The bell: every group within MASTER[0] frenzies; every entranced
        hero there snaps out (an opening)."""
        reach = config.MASTER[0]
        for home, (x, y, _) in sites(ctx.world).items():
            if math.hypot(x - self.x, y - self.y) <= reach:
                frenzy(ctx.world, home)
        for h in ctx.players:
            if getattr(h, "entranced", 0) > 0 and math.hypot(h.x - self.x, h.y - self.y) <= reach:
                h.entranced, h.temptation = 0.0, 0.0
                ctx.effects.append(Effect("toast", h.x, h.y - 1.5, label="SNAPPED OUT!"))
        ctx.effects.append(Effect("bell", self.x, self.y, size=reach))
        ctx.effects.append(Effect("toast", self.x, self.y - 2.5, label="THE BELL!"))
        ctx.events.append("chime")
