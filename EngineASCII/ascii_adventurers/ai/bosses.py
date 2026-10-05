"""
ai/bosses.py -- bosses (M17, design/BOSSES.md).

A boss is an enemy (Brain + Actor: it's hit, takes statuses, gives XP and
loot like any other) with a fight on top:

  * phases: config.BOSSES[kind].phases. Each starts once health drops
    below its threshold and has its own moves (with weights) and rest
    between moves. Entering a phase says so (a toast over the boss).
  * moves: each move is a generator method `m_<name>` that does the move
    step by step, yielding how many seconds to wait before it continues
    (0 = the next step). One runs at a time; between moves the boss rests
    for the phase's `rest`. Moves are picked by weight, never the same one
    twice in a row, from the phase's list.
  * shots come from systems/patterns.py; line attacks and blasts are done
    here. Everything is telegraphed (`tell` says what the renderer should
    show, render/bosses.py) at least ~0.5 s ahead.
  * it never sleeps (the spawner keeps it), always thinks during its fight
    (scenes/game.py), and chill/freeze can at most halve its clock
    (BOSS_MIN_TIME_SCALE).
  * it lives in its lair (`lair`, world/landmarks.Landmark) and picks a
    target among the heroes in the lair, at random each move (design rule
    8: never every player at once).

Everything is driven by the boss's own seeded dice and the step's dt, so a
fight replays exactly from the same inputs.

Froggy McFrogface (swamp): a giant frog in a pond. Signature: the pools --
it dives into one and comes up out of another (ripples show which), and
it belly-flops across the arena, sitting dazed after each landing (the
melee window). Phase 1: tadpole fans, bubble streams, tongue lash, belly
flop. Phase 2
adds bubble spirals, dives and a croak that calls bog toads. Phase 3
("psychedelic"): rainbow rain and closing rings, faster.

The Leech Swarm (swamp, M22): LEECHES leech bodies (LeechPart, real
enemies you hit one by one) sharing one health bar -- the swarm's health is
the sum of theirs, so it thins out as it's hurt, and area hits are strong
against it. The swarm itself (the "core") is a point at their middle that
can't be hit; it drives them. Signature: leeches that reach you latch on
and drain you (healing themselves) until a dodge roll shakes them off.
Phase 1: the flock drifts after its target, surges along a telegraphed line,
splits into three groups that circle and close in. Phase 2 adds rings of
blood drops and nesting (into one pool, out of the one nearest you).
Phase 3: frenzy (faster) and the whirlpool -- a ring of leeches round you
that tightens, with a gap to escape through (or roll through the ring).

Lady Proboscia (swamp, M22.2): a giant mosquito who flies over everything,
circling her target between moves. Signature: ENGORGE -- bites that land
and sips at the pools fill her belly; full, she slows and glows, and enough
damage before it's digested POPS her (a big hit, a ring of blood, stunned
on the ground). Phase 1: dive bites, needle fans, sips. Phase 2 adds buzz
rings (closing, with a gap) and calls for mosquitoes. Phase 3: faster,
three dives in a row, each leaving fever clouds.

Khepri the Dung Emperor (desert, M23.1): a giant dung beetle and his dung
ball, which grows as he rolls it at you. Signature: bait the ball into a
sandstone pillar and it shatters, leaving him stunned. Phase 1: rolls,
horn charges with a fan of kicked sand, burrow eruptions. Phase 2 adds a
dust storm and a call for scarabs. Phase 3: faster rolls, two in a row.
"""

from __future__ import annotations

import math
import random

from .. import config
from ..entities.actor import Actor
from ..entities.effects import Effect
from ..specs import EnemySpec
from ..systems import combat, patterns
from .brain import AIContext, Brain


class Boss(Brain, Actor):
    boss = True

    def __init__(self, spec: EnemySpec, x: float, y: float, rng: random.Random,
                 spawn_id=None, hit_radius: float = 2.0) -> None:
        Actor.__init__(self, round(spec.max_hp * config.BOSS_HP_MULT), hit_radius)
        self.x, self.y = x, y
        self.facing = 0.0
        self.half = spec.size_px / 2
        self.init_brain(spec, rng, spawn_id)
        self.damage_mult *= config.BOSS_DMG_MULT
        self.bspec = config.BOSSES[spec.kind]
        self.lair = None                  # world/landmarks.Landmark (set by the quest)
        self.recruit = None               # callable(enemy key, x, y): call in an add
        self.phase = 0
        self.time = 0.0                   # seconds of its own (scaled) clock
        self.dt = 0.0                     # this step's dt (for the moves)
        self.ctx: AIContext | None = None
        self.move: str | None = None
        self._gen = None
        self._wait = 0.0
        self._rest = 1.5                  # a breath before the first move
        self.last_move: str | None = None
        self.tell: tuple | None = None    # what's being telegraphed (render/bosses.py)
        self.airborne = 0.0               # > 0: in the air (this high, 0..1); can't be hit
        self.submerged = False            # under water: can't be hit
        self.dazed = 0.0                  # seconds left sitting stunned
        self.tgt = None                   # this move's target hero
        self.combo = 0                    # moves chained since the last rest

    # --- Being a boss ----------------------------------------------------------------

    @property
    def hittable(self) -> bool:
        return self.alive and self.airborne <= 0 and not self.submerged

    def scale_to_level(self, level: int) -> None:
        super().scale_to_level(level)
        self.damage_mult *= config.BOSS_DMG_MULT    # (BOSS_HP_MULT is in max_hp already)

    def scale_for(self, players: int) -> None:
        """More health for every extra player (after scale_to_level)."""
        self.max_hp = round(self.max_hp * (1 + self.bspec.coop_hp * max(0, players - 1)))
        self.hp = float(self.max_hp)

    @property
    def frac(self) -> float:
        return self.hp / self.max_hp if self.max_hp else 0.0

    def think(self, ctx: AIContext, dt: float) -> None:
        self.ctx = ctx
        self.dt = dt
        self.time += dt
        self.dazed = max(0.0, self.dazed - dt)
        self.shove_heroes(0.0)
        self._check_phase(ctx)
        if self._gen is None:
            self._rest -= dt
            if self._rest > 0:
                return
            self._start(self._pick_move())
            self._wait = 0.0
        self._wait -= dt
        while self._gen is not None and self._wait <= 0:
            try:
                w = next(self._gen)
            except StopIteration:
                self._end_move()
                break
            if not w:                     # 0: carry on next step
                self._wait = 0.0
                break
            self._wait += w

    def _start(self, name: str) -> None:
        self.move = name
        self.tgt = self.pick_target()
        self._gen = getattr(self, "m_" + name)()

    def _end_move(self) -> None:
        self.last_move = self.move
        self.move = None
        self._gen = None
        self.tell = None
        # A combo: straight into the next move (its own tell still shows),
        # the first move's shots still flying. The rest comes after it.
        chance, most = config.BOSS_COMBO[min(self.phase, len(config.BOSS_COMBO) - 1)]
        if self.combo < most and self.rng.random() < chance:
            self.combo += 1
            self._rest = config.BOSS_COMBO_GAP
            return
        self.combo = 0
        scale = config.BOSS_REST_SCALE[min(self.phase, len(config.BOSS_REST_SCALE) - 1)]
        self._rest = self.bspec.phases[self.phase].rest * scale

    def tell_s(self, seconds: float) -> float:
        """A tell's length in this phase: shorter as the fight goes on, but
        never under BOSS_MIN_TELL (nor longer than it was)."""
        scale = config.BOSS_TELL_SCALE[min(self.phase, len(config.BOSS_TELL_SCALE) - 1)]
        return min(seconds, max(config.BOSS_MIN_TELL, seconds * scale))

    def lead(self, t, ox: float, oy: float, speed: float = 0.0,
             secs: float | None = None) -> tuple[float, float]:
        """Where to aim at hero `t` from (ox, oy): where it'll be if it keeps
        moving the way it is. Ahead by the shot's flight time (distance /
        `speed`) or by `secs`, x BOSS_LEAD, at most BOSS_LEAD_MAX tiles."""
        if secs is None:
            secs = math.hypot(t.x - ox, t.y - oy) / speed if speed > 0 else 0.0
        k = secs * config.BOSS_LEAD
        dx, dy = getattr(t, "vx", 0.0) * k, getattr(t, "vy", 0.0) * k
        d = math.hypot(dx, dy)
        if d > config.BOSS_LEAD_MAX:
            dx, dy = dx / d * config.BOSS_LEAD_MAX, dy / d * config.BOSS_LEAD_MAX
        return t.x + dx, t.y + dy

    def aim(self, t, ox: float, oy: float, speed: float = 0.0, secs: float | None = None,
            lead: bool = True) -> float:
        """The angle from (ox, oy) at hero `t` -- leading it, or (lead=False)
        straight at where it is now."""
        x, y = self.lead(t, ox, oy, speed, secs) if lead else (t.x, t.y)
        return math.atan2(y - oy, x - ox)

    def _check_phase(self, ctx: AIContext) -> None:
        f = self.frac
        phase = self.phase
        for i, ph in enumerate(self.bspec.phases):
            if f <= ph.below:
                phase = max(phase, i)
        if phase != self.phase:
            self.phase = phase
            self.on_phase(phase, ctx)

    def on_phase(self, phase: int, ctx: AIContext) -> None:
        """A new phase begins (a toast over the boss by default)."""
        ctx.effects.append(Effect("toast", self.x, self.y - self.hit_radius - 1,
                                  label=f"{self.espec.name.upper()} GETS ANGRY!"))

    def _pick_move(self) -> str:
        moves = [(m, w) for m, w in self.bspec.phases[self.phase].moves if m != self.last_move]
        if not moves:
            moves = list(self.bspec.phases[self.phase].moves)
        total = sum(w for _, w in moves)
        r = self.rng.uniform(0, total)
        for m, w in moves:
            r -= w
            if r <= 0:
                return m
        return moves[-1][0]

    def heroes(self) -> list:
        """The living heroes in the arena (all living heroes if none are)."""
        alive = [h for h in self.ctx.players if h.alive]
        if self.lair is None:
            return alive
        inside = [h for h in alive if self.lair.inside(h.x, h.y)]
        return inside or alive

    def pick_target(self):
        heroes = self.heroes()
        return self.rng.choice(heroes) if heroes else None

    def target_now(self):
        """This move's target, or a new one if it fell."""
        if self.tgt is None or not self.tgt.alive:
            self.tgt = self.pick_target()
        return self.tgt

    def clamp_to_lair(self, x: float, y: float, shrink: float) -> tuple[float, float]:
        """(x, y) pulled inside the arena (by `shrink` tiles from the stones)."""
        lair = self.lair
        if lair is None or lair.inside(x, y, shrink):
            return x, y
        a, b = lair.radii[0] - shrink, lair.radii[1] - shrink
        dx, dy = x - lair.cx, y - lair.cy
        k = 1.0 / math.sqrt((dx / a) ** 2 + (dy / b) ** 2)
        return lair.cx + dx * k * 0.98, lair.cy + dy * k * 0.98

    def shove_heroes(self, extra: float = 0.3) -> None:
        """Push heroes out of its body (it's big and solid when it's on the
        ground: landing on you knocks you aside rather than swallowing you)."""
        if self.airborne > 0 or self.submerged:
            return
        for h in self.ctx.players:
            if not h.alive:
                continue
            dx, dy = h.x - self.x, h.y - self.y
            d = math.hypot(dx, dy)
            room = self.hit_radius + h.hit_radius + extra
            if d >= room:
                continue
            if d < 1e-6:
                dx, dy, d = math.cos(self.facing + math.pi), math.sin(self.facing + math.pi), 1.0
            combat.push(h, self.ctx.world, dx / d * (room - d), dy / d * (room - d))

    def shots_alive(self) -> int:
        return sum(1 for p in self.ctx.projectiles if p.owner is self)

    def room_for_shots(self) -> bool:
        """Under the bullets-alive budget (per player in the arena)."""
        return self.shots_alive() < config.BOSS_MAX_SHOTS * max(1, len(self.heroes()))

    def on_death(self, ctx: AIContext) -> None:
        for k in range(6):
            a = k * math.tau / 6
            ctx.effects.append(Effect("explosion", self.x + math.cos(a) * 1.8,
                                      self.y + math.sin(a) * 1.1))
        ctx.effects.append(Effect("explosion", self.x, self.y))
        ctx.events.append(combat.BREAK)


class Froggy(Boss):
    def __init__(self, spec: EnemySpec, x: float, y: float, rng: random.Random,
                 spawn_id=None) -> None:
        super().__init__(spec, x, y, rng, spawn_id, hit_radius=config.FROGGY_HIT_RADIUS)
        self.shots = config.FROGGY_SHOTS
        self.mouth_open = False
        self.tongue: tuple | None = None  # (angle, reach, out) while lashing
        self.landing: tuple | None = None # (x, y, radius) while in the air
        self.ripples: tuple | None = None # (x, y) where it'll come up
        self.hue = 0.0                    # the psychedelic phase's color cycle

    @property
    def psychedelic(self) -> bool:
        return self.phase >= 2

    def think(self, ctx: AIContext, dt: float) -> None:
        self.hue += dt * (6.0 if self.psychedelic else 0.0)
        t = self.tgt if self.tgt is not None and self.tgt.alive else None
        if t is not None and self.airborne <= 0 and not self.submerged:
            self.facing = math.atan2(t.y - self.y, t.x - self.x)
        super().think(ctx, dt)

    def on_phase(self, phase: int, ctx: AIContext) -> None:
        label = ("FROGGY GETS ANGRY!", "THE POND STARTS TO GLOW...")[min(phase, 2) - 1] \
            if phase else ""
        if label:
            ctx.effects.append(Effect("toast", self.x, self.y - self.hit_radius - 1, label=label))

    def _pick_move(self) -> str:
        t = self.target_now()
        if t is not None and math.hypot(t.x - self.x, t.y - self.y) > config.FROGGY_FAR \
                and self.last_move != "flop":
            return "flop"                 # too far: leap closer first
        return super()._pick_move()

    @property
    def mouth(self) -> tuple[float, float]:
        """Where its shots come from: the front of its face."""
        return self.x + math.cos(self.facing) * 1.2, self.y + math.sin(self.facing) * 0.6

    def _tint(self) -> int:
        return int(self.hue) if self.psychedelic else 0

    # --- Moves --------------------------------------------------------------------------

    def m_fan(self):
        """P3: tadpole fans at the target, a few volleys."""
        n, spread, volleys, gap = config.FROGGY_FAN
        self.tell = ("mouth",)
        self.mouth_open = True
        yield self.tell_s(config.FROGGY_TELL)
        for k in range(volleys):
            t = self.target_now()
            if t is None:
                break
            if self.room_for_shots():
                mx, my = self.mouth
                shell = self.shots["tadpole"]       # the first volley at you, the rest lead you
                patterns.fan(self, mx, my, self.aim(t, mx, my, shell.speed, lead=k > 0), n,
                             spread, shell, self.ctx.projectiles, self._tint())
                self.ctx.events.append("orb")
            yield gap
        self.mouth_open = False

    def m_stream(self):
        """P3 (one at a time): a stream of bubbles, every other one aimed at
        where the target is now, the rest leading it -- run straight and the
        leading ones meet you, stand still and the others land."""
        n, gap = config.FROGGY_STREAM
        self.tell = ("mouth",)
        self.mouth_open = True
        yield self.tell_s(config.FROGGY_TELL)
        for k in range(n):
            t = self.target_now()
            if t is None:
                break
            if self.room_for_shots():
                mx, my = self.mouth
                shell = self.shots["stream"]
                patterns.shoot(self, mx, my, self.aim(t, mx, my, shell.speed, lead=k % 2 == 1),
                               shell, self.ctx.projectiles, self._tint())
                self.ctx.events.append("fizzle")
            yield gap
        self.mouth_open = False

    def m_tongue(self):
        """P7-like: an aim line, then the tongue lashes out along it, hurting
        and pulling in whoever it catches."""
        aim_time, reach, width, damage, pull = config.FROGGY_TONGUE
        t = self.target_now()
        if t is None:
            return
        aim_time = self.tell_s(aim_time)
        a = self.aim(t, self.x, self.y, secs=aim_time)   # at where you'll be when it lashes
        self.facing = a
        self.tell = ("tongue", a, reach)
        yield aim_time
        self.tell = None
        self.tongue = (a, reach, 1.0)
        x1, y1 = self.x + math.cos(a) * reach, self.y + math.sin(a) * reach
        for h in self.ctx.players:
            if not h.hittable:                  # (rolling through it dodges the pull too)
                continue
            d = patterns.point_segment_distance(h.x, h.y, self.x, self.y, x1, y1)
            if d <= width + h.hit_radius:
                combat.strike(h, damage * self.damage_mult, self, a, self.ctx.effects)
                back = math.atan2(self.y - h.y, self.x - h.x)
                dist = max(0.0, min(pull, math.hypot(self.x - h.x, self.y - h.y)
                                    - self.hit_radius - 1.5))
                combat.push(h, self.ctx.world, math.cos(back) * dist, math.sin(back) * dist)
        self.ctx.events.append("hex")
        yield 0.3
        self.tongue = None
        yield 0.3

    def m_flop(self):
        """B1: a leap at the target (its landing ring shows the whole time
        it's in the air), a blast and a ring of ripples where it lands,
        then it sits dazed -- the moment to hit it up close."""
        flight, leap, radius, damage, n, daze = config.FROGGY_FLOP
        t = self.target_now()
        if t is None:
            return
        tx, ty = self.lead(t, self.x, self.y, secs=flight)   # lands where you'll be
        dx, dy = tx - self.x, ty - self.y
        d = math.hypot(dx, dy)
        if d > leap:
            dx, dy = dx / d * leap, dy / d * leap
        lx, ly = self.clamp_to_lair(self.x + dx, self.y + dy, 5.0)
        x0, y0 = self.x, self.y
        self.landing = (lx, ly, radius)
        self.tell = ("flop",)
        tt = 0.0
        while tt < flight:
            tt = min(flight, tt + self.dt)
            f = tt / flight
            self.x, self.y = x0 + (lx - x0) * f, y0 + (ly - y0) * f
            self.airborne = max(0.01, 4 * f * (1 - f))
            yield 0
        self.airborne = 0.0
        self.landing = None
        self.tell = None
        combat.blast(lx, ly, radius, damage * self.damage_mult, self, self.ctx.actors,
                     effects=self.ctx.effects)
        self.ctx.effects.append(Effect("explosion", lx, ly))
        self.ctx.effects.append(Effect("nova", lx, ly, size=radius))
        self.ctx.events.append("boulder")
        self.shove_heroes(1.0)
        if self.room_for_shots():
            patterns.radial(self, lx, ly, n, self.shots["ripple"], self.ctx.projectiles,
                            self.rng.uniform(0, math.tau), self._tint())
        self.dazed = daze
        yield daze

    def m_spiral(self):
        """P2: bubbles in turning arms (three in the last phase)."""
        dur, every, spin = config.FROGGY_SPIRAL
        arms = 3 if self.psychedelic else 2
        self.tell = ("mouth",)
        self.mouth_open = True
        yield self.tell_s(config.FROGGY_TELL)
        turn = self.rng.uniform(0, math.tau)
        way = self.rng.choice((-1, 1))
        tt = 0.0
        while tt < dur:
            if self.room_for_shots():
                patterns.radial(self, self.x, self.y, arms, self.shots["bubble"],
                                self.ctx.projectiles, turn, self._tint())
            turn += way * spin * every
            tt += every
            yield every
        self.mouth_open = False

    def m_dive(self):
        """The signature: a hop into the nearest pool, under, then ripples
        on the pool nearest the target -- and up it comes there, in a ring
        of ripples (two rings, staggered)."""
        hop, under, tell, n = config.FROGGY_DIVE
        pools = self.lair.spots if self.lair is not None else []
        if not pools:
            return
        px, py = min(pools, key=lambda p: math.hypot(p[0] - self.x, p[1] - self.y))
        x0, y0 = self.x, self.y
        tt = 0.0
        while tt < hop:
            tt = min(hop, tt + self.dt)
            f = tt / hop
            self.x, self.y = x0 + (px - x0) * f, y0 + (py - y0) * f
            self.airborne = max(0.01, 2 * f * (1 - f))
            yield 0
        self.airborne = 0.0
        self.submerged = True
        self.ctx.effects.append(Effect("nova", px, py, size=3.0))
        self.ctx.events.append("fizzle")
        yield under
        t = self.target_now()
        others = [p for p in pools if p != (px, py)] or pools
        if t is not None:
            dest = min(others, key=lambda p: math.hypot(p[0] - t.x, p[1] - t.y))
        else:
            dest = self.rng.choice(others)
        self.ripples = dest
        self.tell = ("ripples",)
        yield self.tell_s(tell)
        self.x, self.y = dest
        self.submerged = False
        self.ripples = None
        self.tell = None
        self.ctx.effects.append(Effect("explosion", self.x, self.y))
        self.ctx.events.append("boulder")
        self.shove_heroes(1.0)
        turn = self.rng.uniform(0, math.tau)
        for k in range(2):
            if self.room_for_shots():
                patterns.radial(self, self.x, self.y, n, self.shots["ripple"],
                                self.ctx.projectiles, turn + k * math.pi / n, self._tint())
            yield 0.4

    def m_summon(self):
        """B2: a croak, and bog toads hop out of the mud round it (never
        more than a few alive at once)."""
        k, cap = config.FROGGY_SUMMON
        self.tell = ("mouth",)
        self.mouth_open = True
        yield self.tell_s(config.FROGGY_TELL)
        alive = sum(1 for a in self.ctx.actors if getattr(a, "summoner", None) is self and a.alive)
        for i in range(min(k, cap - alive)):
            if self.recruit is None:
                break
            a = self.rng.uniform(0, math.tau)
            r = self.rng.uniform(4.0, 6.5)
            x, y = self.clamp_to_lair(self.x + math.cos(a) * r, self.y + math.sin(a) * r, 4.0)
            add = self.recruit("toad", x, y)
            if add is not None:
                add.summoner = self
                self.ctx.effects.append(Effect("explosion", x, y))
        self.ctx.events.append("orb")
        self.mouth_open = False
        yield 0.4

    def m_rain(self):
        """P10: rainbow rain -- rows of shots from one side of where the
        target stood, 2 x half tiles wide, a hole drifting along the rows to
        weave through (or run out to the side)."""
        dur, every, gap, hole, half = config.FROGGY_RAIN
        heading = self.rng.choice((0.0, math.pi / 2, math.pi, -math.pi / 2))
        self.tell = ("mouth",)
        self.mouth_open = True
        yield self.tell_s(config.FROGGY_TELL)
        tt = 0.0
        phase = self.rng.uniform(0, math.tau)
        t = self.target_now()
        if t is None:
            return
        cx, cy = t.x, t.y                 # the curtain comes down over where they stood
        while tt < dur:
            hole_at = math.sin(phase + tt * 0.9) * half * 0.6
            if self.room_for_shots():
                patterns.curtain(self, cx, cy, heading, 18.0, half, gap, hole_at, hole,
                                 self.shots["rain"], self.ctx.projectiles, int(tt / every))
            tt += every
            yield every
        self.mouth_open = False

    def m_ring(self):
        """P5: rings round the target that hang for a moment, then close."""
        n, radius, hold, rings, between = config.FROGGY_RING
        self.tell = ("mouth",)
        self.mouth_open = True
        yield self.tell_s(config.FROGGY_TELL * 0.6)
        self.mouth_open = False
        for k in range(rings):
            t = self.target_now()
            if t is None:
                break
            patterns.ring_in(self, t.x, t.y, radius, n, self.shots["ring"], self.ctx.projectiles,
                             hold, turn=k * math.pi / n, tint=k)
            self.ctx.events.append("orb")
            yield between



# --- The Leech Swarm (M22) ---------------------------------------------------------------


class LeechPart(Actor):
    """One leech of the swarm: a real enemy body (hit, statuses, numbers)
    holding its share of the swarm's health. The swarm moves it."""

    faction = "enemy"
    boss = True                       # never sleeps; thinks with its boss

    def __init__(self, core: "LeechSwarm", x: float, y: float, index: int) -> None:
        super().__init__(1, config.LEECH_RADIUS)
        self.part_of = core
        self.index = index
        self.x, self.y = x, y
        self.half = 5                 # px (push() leaves bosses alone anyway)
        self.facing = 0.0
        self.vx = self.vy = 0.0
        self.goal: tuple[float, float] | None = None
        self.latched = None           # the hero it's sucking on
        self.offset = (0.0, 0.0)
        self.drain = 0.0              # seconds toward the next drain tick
        self.stun = 0.0               # thrown off by a roll: lies there a moment
        self.submerged = False        # nesting in a pool: can't be hit
        self.group = index % config.LEECH_SPLIT[0]
        self.espec = core.espec       # (for anything that asks what it is)

    @property
    def hittable(self) -> bool:
        return self.alive and not self.submerged

    def take_damage(self, amount, source, from_angle):
        dealt = super().take_damage(amount, source, from_angle)
        core = self.part_of
        if source is not None and dealt > 0:
            core.last_hit_by = source
        core.recount()
        if dealt > 0:
            core.hurt_flash = 0.12
        return dealt

    # The rest of what the game asks of an enemy.
    spawn_id = None
    level = 1
    damage_mult = 1.0
    haste = 0.0

    def think(self, ctx, dt: float) -> None:
        pass                          # the swarm moves its leeches

    def hear(self, x: float, y: float) -> None:
        pass


class LeechSwarm(Boss):
    def __init__(self, spec: EnemySpec, x: float, y: float, rng: random.Random,
                 spawn_id=None) -> None:
        super().__init__(spec, x, y, rng, spawn_id, hit_radius=1.0)
        self.shots = config.LEECH_SHOTS
        self.parts: list[LeechPart] = []
        n = config.LEECHES
        for i in range(n):
            a = i * 2.39996                       # golden angle: an even blob
            r = 2.5 * math.sqrt((i + 0.5) / n)
            self.parts.append(LeechPart(self, x + math.cos(a) * r, y + math.sin(a) * r * 0.6, i))
        self._share()
        self.mode = "flock"
        self.dash = (1.0, 0.0)
        self.whirl: tuple | None = None   # (cx, cy, radius, turn, gap angle)
        self.nest_at: tuple | None = None # where it'll burst out (ripples)

    # --- Health: the leeches' ---------------------------------------------------------

    def _share(self) -> None:
        """Split the swarm's max HP evenly over its leeches (all full)."""
        each = self.max_hp / len(self.parts)
        for p in self.parts:
            p.max_hp = each
            p.hp = each
        self.hp = float(self.max_hp)

    def scale_to_level(self, level: int) -> None:
        super().scale_to_level(level)
        self._share()

    def scale_for(self, players: int) -> None:
        super().scale_for(players)
        self._share()

    def recount(self) -> None:
        self.hp = sum(p.hp for p in self.parts if p.alive)

    @property
    def hittable(self) -> bool:
        return False                  # only its leeches can be hit

    def take_damage(self, amount, source, from_angle):
        """Hurt the swarm as such (thorns, a retaliation...): the leech
        nearest the source takes it."""
        alive = [p for p in self.parts if p.hittable]
        if not alive:
            return 0.0
        ref = source if source is not None else self
        p = min(alive, key=lambda q: (q.x - ref.x) ** 2 + (q.y - ref.y) ** 2)
        return p.take_damage(amount, source, from_angle)

    def living(self) -> list[LeechPart]:
        return [p for p in self.parts if p.alive]

    def free(self) -> list[LeechPart]:
        """Leeches it can steer: alive, not latched, not lying stunned."""
        return [p for p in self.parts if p.alive and p.latched is None and p.stun <= 0]

    # --- Every step ---------------------------------------------------------------------

    def think(self, ctx: AIContext, dt: float) -> None:
        self.ctx = ctx
        self._centre()
        super().think(ctx, dt)
        self._flock_goals()
        self._move(dt)
        self._latch(dt)
        self.recount()
        self._centre()

    def shove_heroes(self, extra: float = 0.3) -> None:
        pass                          # a swarm has no body to shove with

    @property
    def speed(self) -> float:
        return config.LEECH_FLOCK[0] * (config.LEECH_FRENZY if self.phase >= 2 else 1.0)

    def _centre(self) -> None:
        live = [p for p in self.parts if p.alive and p.latched is None] or self.living()
        if live:
            self.x = sum(p.x for p in live) / len(live)
            self.y = sum(p.y for p in live) / len(live)

    def _flock_goals(self) -> None:
        """Between moves (mode "flock"), every free leech heads for its own
        place in a loose blob round the target."""
        if self.mode != "flock":
            return
        t = self.target_now()
        if t is None:
            return
        spread = config.LEECH_FLOCK[2]
        n = len(self.parts)
        for p in self.free():
            a = p.index * 2.39996 + self.time * 0.4
            r = spread * math.sqrt((p.index + 0.5) / n) + 1.0
            p.goal = (t.x + math.cos(a) * r, t.y + math.sin(a) * r * 0.7)

    def _move(self, dt: float) -> None:
        """Steer every free leech toward its goal (or along the surge),
        inside the arena. Leeches swim over everything (no walls for them)
        and crawl over each other: no pushing apart, just a little wander
        round each one's goal (LEECH_FLOCK[1] tiles) so they don't stack."""
        wander = config.LEECH_FLOCK[1]
        free = self.free()
        speed = self.speed
        for p in self.parts:
            if p.alive and p.stun > 0:
                p.stun -= dt
        for p in free:
            if p.submerged:
                continue
            if self.mode == "dash":
                vx, vy = self.dash[0] * config.LEECH_SURGE[1], self.dash[1] * config.LEECH_SURGE[1]
            elif p.goal is not None:
                dx, dy = p.goal[0] - p.x, p.goal[1] - p.y
                if self.mode != "whirl":      # (the whirlpool's ring stays clean)
                    j = p.index * 2.39996 + self.time * 1.3
                    dx += math.cos(j) * wander
                    dy += math.sin(j * 1.7) * wander * 0.7
                d = math.hypot(dx, dy)
                top = speed * (4.0 if self.mode == "whirl" else 1.6 if self.mode == "rush" else 1.0)
                k = min(top, d * 4.0) / d if d > 1e-6 else 0.0
                vx, vy = dx * k, dy * k
            else:
                vx = vy = 0.0
            p.vx, p.vy = vx, vy
        for p in free:
            if p.submerged:
                continue
            p.x += p.vx * dt
            p.y += p.vy * dt
            if p.vx or p.vy:
                p.facing = math.atan2(p.vy, p.vx)
            p.x, p.y = self.clamp_to_lair(p.x, p.y, 2.0)

    def _latch(self, dt: float) -> None:
        """Leeches that touch a hero latch on; latched ones ride along and
        drain; a hero who rolls throws all of theirs off."""
        ctx = self.ctx
        heroes = [h for h in ctx.players if h.alive]
        on = {id(h): 0 for h in heroes}
        for p in self.parts:
            if p.alive and p.latched is not None and id(p.latched) in on:
                on[id(p.latched)] += 1
        shaken = set()
        for p in self.parts:
            if not p.alive:
                continue
            h = p.latched
            if h is not None:
                if not h.alive or h.rolling:
                    self._shake(p, h)
                    shaken.add(id(h))
                    continue
                p.x, p.y = h.x + p.offset[0], h.y + p.offset[1]
                p.drain += dt
                if p.drain >= config.LATCH_TICK:
                    p.drain -= config.LATCH_TICK
                    dealt = h.take_damage(config.LATCH_DPS * config.LATCH_TICK * self.damage_mult,
                                          self, None)
                    if dealt > 0:
                        p.heal(dealt * config.LATCH_HEAL)
                        ctx.effects.append(Effect("number", h.x, h.y - h.hit_radius,
                                                  value=round(dealt), player=True))
                continue
            if p.stun > 0 or p.submerged:
                continue
            for h in heroes:
                if not h.hittable or on[id(h)] >= config.LATCH_MAX:
                    continue
                if math.hypot(h.x - p.x, h.y - p.y) <= h.hit_radius + config.LEECH_RADIUS:
                    p.latched = h
                    a = self.rng.uniform(0, math.tau)
                    p.offset = (math.cos(a) * h.hit_radius * 0.7, math.sin(a) * h.hit_radius * 0.5)
                    p.drain = 0.0
                    on[id(h)] += 1
                    ctx.events.append("hit")
                    break
        for h in heroes:
            if id(h) in shaken:
                ctx.effects.append(Effect("toast", h.x, h.y - 1, label="SHAKEN OFF!"))

    def _shake(self, p: LeechPart, h) -> None:
        dx, dy = p.x - h.x, p.y - h.y
        d = math.hypot(dx, dy) or 1.0
        fling = config.LATCH_SHAKE[0]
        p.latched = None
        p.stun = config.LATCH_SHAKE[1]
        p.x, p.y = self.clamp_to_lair(p.x + dx / d * fling, p.y + dy / d * fling, 2.0)

    def on_phase(self, phase: int, ctx: AIContext) -> None:
        label = ("THE SWARM GROWS HUNGRY!", "FRENZY!")[min(phase, 2) - 1] if phase else ""
        if label:
            ctx.effects.append(Effect("toast", self.x, self.y - 2, label=label))

    def on_death(self, ctx: AIContext) -> None:
        for k in range(5):
            a = k * math.tau / 5
            ctx.effects.append(Effect("explosion", self.x + math.cos(a) * 1.5,
                                      self.y + math.sin(a) * 1.0))
        ctx.events.append(combat.BREAK)

    # --- Moves --------------------------------------------------------------------------

    def m_surge(self):
        """A red line from the swarm through the target (the tell), then
        every free leech dashes along it."""
        tell, _, dash_t, length = config.LEECH_SURGE
        t = self.target_now()
        if t is None:
            return
        tell = self.tell_s(tell)
        a = self.aim(t, self.x, self.y, secs=tell)    # through where you'll be
        self.dash = (math.cos(a), math.sin(a))
        self.mode = "hold"
        for p in self.free():
            p.goal = (p.x, p.y)
        self.tell = ("line", self.x, self.y, self.x + self.dash[0] * length,
                     self.y + self.dash[1] * length)
        yield tell
        self.tell = None
        self.mode = "dash"
        self.ctx.events.append("swing")
        yield dash_t
        self.mode = "flock"

    def m_split(self):
        """Three groups circle the target, then all close in at once."""
        groups, radius, circle_t, close_t = config.LEECH_SPLIT
        self.mode = "rush"
        t0 = self.time
        while self.time - t0 < circle_t:
            t = self.target_now()
            if t is None:
                break
            spin = (self.time - t0) * 1.6
            for p in self.free():
                a = p.group * math.tau / groups + spin + (p.index % 5) * 0.12
                p.goal = (t.x + math.cos(a) * radius, t.y + math.sin(a) * radius * 0.7)
            yield 0
        t0 = self.time
        while self.time - t0 < close_t:
            t = self.target_now()
            if t is None:
                break
            for p in self.free():
                p.goal = (t.x, t.y)
            yield 0
        self.mode = "flock"

    def m_spit(self):
        """The swarm bunches up and swells (the tell), then spits rings of
        blood drops."""
        tell, rings, drops, between = config.LEECH_SPIT
        self.mode = "hold"
        for p in self.free():
            p.goal = (self.x, self.y)
        self.tell = ("swell",)
        yield self.tell_s(tell)
        self.tell = None
        turn = self.rng.uniform(0, math.tau)
        for k in range(rings):
            if self.room_for_shots():
                patterns.radial(self, self.x, self.y, drops, self.shots["blood"],
                                self.ctx.projectiles, turn + k * math.pi / drops)
                self.ctx.events.append("fizzle")
            yield between
        self.mode = "flock"

    def m_nest(self):
        """Into the nearest pool, under (can't be hit), ripples on the pool
        nearest the target, and out of that one -- with a ring of drops."""
        swim, tell, drops = config.LEECH_NEST
        pools = self.lair.spots if self.lair is not None else []
        if not pools:
            return
        px, py = min(pools, key=lambda q: math.hypot(q[0] - self.x, q[1] - self.y))
        self.mode = "rush"
        for p in self.free():
            p.goal = (px, py)
        yield swim
        diving = self.free()
        for p in diving:
            p.submerged = True
            p.x, p.y = px, py
        self.ctx.effects.append(Effect("nova", px, py, size=3.0))
        self.ctx.events.append("fizzle")
        t = self.target_now()
        others = [q for q in pools if q != (px, py)] or pools
        dest = min(others, key=lambda q: math.hypot(q[0] - t.x, q[1] - t.y)) if t is not None \
            else self.rng.choice(others)
        self.nest_at = dest
        self.tell = ("ripples", dest[0], dest[1])
        yield self.tell_s(tell)
        self.tell = None
        self.nest_at = None
        n = max(1, len(diving))
        for i, p in enumerate(diving):
            a = i * math.tau / n
            p.submerged = False
            p.x, p.y = dest[0] + math.cos(a) * 0.5, dest[1] + math.sin(a) * 0.3
            p.goal = (dest[0] + math.cos(a) * 5.0, dest[1] + math.sin(a) * 3.5)
        self.ctx.effects.append(Effect("explosion", dest[0], dest[1]))
        self.ctx.events.append("boulder")
        if self.room_for_shots():
            patterns.radial(self, dest[0], dest[1], drops, self.shots["blood"],
                            self.ctx.projectiles, self.rng.uniform(0, math.tau))
        self.mode = "rush"
        yield 0.6
        self.mode = "flock"

    def m_whirlpool(self):
        """The leeches ring the target and the ring tightens, turning, with a
        gap in it: get out through the gap, or roll through the ring."""
        radius, inner, dur, gap = config.LEECH_WHIRL
        t = self.target_now()
        if t is None:
            return
        cx, cy = t.x, t.y
        gap_at = self.rng.uniform(0, math.tau)
        way = self.rng.choice((-1, 1))
        self.mode = "whirl"
        t0 = self.time
        while self.time - t0 < dur:
            f = (self.time - t0) / dur
            r = radius + (inner - radius) * f
            turn = gap_at + way * f * 2.0
            self.whirl = (cx, cy, r, turn, math.radians(gap))
            free = self.free()
            span = math.tau - math.radians(gap)
            for i, p in enumerate(free):
                a = turn + math.radians(gap) / 2 + span * (i + 0.5) / max(1, len(free))
                p.goal = (cx + math.cos(a) * r, cy + math.sin(a) * r * 0.7)
            yield 0
        self.whirl = None
        self.mode = "flock"


# --- Lady Proboscia (M22.2) --------------------------------------------------------------


class Proboscia(Boss):
    """A giant mosquito. She flies over everything (walls, pillars, pools),
    hovering at a distance from her target between moves -- circling it,
    and always facing it.

    Signature, ENGORGE: every bite that lands and every sip at a pool puts
    a gulp of blood in her belly (a bite heals her too). With a full belly
    she's engorged for a while: slower, glowing, a bar under her showing
    how much more it takes -- deal that and she POPS (a big chunk of her
    health, a ring of blood drops, and she drops to the ground stunned:
    the melee window). If the time runs out she digests it and heals."""

    def __init__(self, spec: EnemySpec, x: float, y: float, rng: random.Random,
                 spawn_id=None) -> None:
        super().__init__(spec, x, y, rng, spawn_id, hit_radius=config.PROBOSCIA_HIT_RADIUS)
        self.shots = config.PROBOSCIA_SHOTS
        self.hover = True                 # between moves (and during some): circling the target
        self.orbit = rng.uniform(0, math.tau)
        self.orbit_way = rng.choice((-1, 1))
        self.belly = 0                    # gulps of blood (0..ENGORGE_FULL)
        self.engorged = 0.0               # seconds left engorged
        self.pop_dmg = 0.0                # damage taken while engorged
        self.sip_dmg = 0.0                # damage taken while sipping
        self.sipping = False              # landed at a pool, drinking (low, easy to reach)
        self.dashing = False
        self.clouds: list[list[float]] = []   # fever clouds: [x, y, age]
        self._cloud_tick = 0.0
        self.wings = 0.0                  # wing beat (drawing)

    # --- State -------------------------------------------------------------------------

    @property
    def speed_mult(self) -> float:
        m = config.PROBOSCIA_FRENZY[0] if self.phase >= 2 else 1.0
        return m * (config.ENGORGE_SLOW if self.engorged > 0 else 1.0)

    @property
    def grounded(self) -> bool:
        """Down low: sipping or stunned after a pop (drawn on the ground)."""
        return self.sipping or self.dazed > 0

    @property
    def pop_frac(self) -> float:
        """How close an engorged belly is to popping (0..1)."""
        need = config.ENGORGE_POP * self.max_hp
        return min(1.0, self.pop_dmg / need) if need > 0 else 1.0

    def take_damage(self, amount, source, from_angle):
        dealt = super().take_damage(amount, source, from_angle)
        if self.engorged > 0:
            self.pop_dmg += dealt
        if self.sipping:
            self.sip_dmg += dealt
        return dealt

    def shove_heroes(self, extra: float = 0.3) -> None:
        pass                              # she flies: nothing to bump into

    def gulp(self, n: int = 1) -> None:
        """Blood in the belly; a full one engorges her."""
        if self.engorged > 0:
            return
        self.belly = min(config.ENGORGE_FULL, self.belly + n)
        if self.belly >= config.ENGORGE_FULL:
            self.engorged = config.ENGORGE_WINDOW
            self.pop_dmg = 0.0
            self.ctx.effects.append(Effect("toast", self.x, self.y - 3, label="ENGORGED! POP HER!"))
            self.ctx.events.append("chime")

    # --- Every step ---------------------------------------------------------------------

    def think(self, ctx: AIContext, dt: float) -> None:
        self.ctx = ctx
        self.wings += dt * (30.0 if not self.grounded else 4.0)
        self._clouds(dt)
        if self.engorged > 0:
            if self.pop_frac >= 1.0:
                self._pop()
            else:
                self.engorged -= dt
                if self.engorged <= 0:
                    self._digest()
        if self.dazed > 0:                # popped: lying there, nothing else
            self.time += dt
            self.dt = dt
            self.dazed = max(0.0, self.dazed - dt)
            if self.dazed <= 0:
                self.hover = True         # up again
            self._check_phase(ctx)
            return
        t = self.target_now() if self.ctx is not None else None
        if self.hover:
            self._hover(dt)
        elif t is not None and not self.dashing and not self.sipping:
            self.facing = math.atan2(t.y - self.y, t.x - self.x)
        super().think(ctx, dt)

    def _hover(self, dt: float) -> None:
        """Circle the target at a distance, facing it."""
        t = self.target_now()
        if t is None:
            return
        speed, dist, orbit = config.PROBOSCIA_HOVER
        self.orbit += self.orbit_way * orbit * dt
        gx = t.x + math.cos(self.orbit) * dist
        gy = t.y + math.sin(self.orbit) * dist * 0.7
        gx, gy = self.clamp_to_lair(gx, gy, 3.0)
        self._fly_to(gx, gy, speed * self.speed_mult, dt)
        self.facing = math.atan2(t.y - self.y, t.x - self.x)

    def _fly_to(self, gx: float, gy: float, speed: float, dt: float) -> bool:
        """A step toward (gx, gy) through the air; True once there."""
        dx, dy = gx - self.x, gy - self.y
        d = math.hypot(dx, dy)
        step = speed * dt
        if d <= step or d < 1e-6:
            self.x, self.y = gx, gy
            return True
        self.x += dx / d * step
        self.y += dy / d * step
        return False

    def _clouds(self, dt: float) -> None:
        """Fever clouds age, and hurt the heroes in them every tick."""
        if not self.clouds:
            return
        radius, life, tick, damage, _ = config.FEVER_CLOUD
        for c in self.clouds:
            c[2] += dt
        self.clouds = [c for c in self.clouds if c[2] < life]
        self._cloud_tick -= dt
        if self._cloud_tick > 0:
            return
        self._cloud_tick += tick
        for h in self.ctx.players:
            if not h.hittable:
                continue
            if any(math.hypot(h.x - c[0], h.y - c[1]) <= radius + h.hit_radius for c in self.clouds):
                combat.strike(h, damage * self.damage_mult, self, None, self.ctx.effects)

    def _abort_move(self) -> None:
        if self._gen is not None:
            self._gen.close()
        self.move = None
        self._gen = None
        self.tell = None
        self.dashing = False
        self.sipping = False

    def _pop(self) -> None:
        """Burst: a big hit of her own blood, a ring of drops, and down she goes."""
        ctx = self.ctx
        self._abort_move()
        self.engorged = 0.0
        self.belly = 0
        bonus = config.ENGORGE_BONUS * self.max_hp
        self.hp = max(0.0, self.hp - bonus)
        self.hurt_flash = 0.2
        ctx.effects.append(Effect("number", self.x, self.y - self.hit_radius, value=round(bonus)))
        ctx.effects.append(Effect("toast", self.x, self.y - 3, label="POP!"))
        ctx.effects.append(Effect("explosion", self.x, self.y))
        ctx.effects.append(Effect("nova", self.x, self.y, size=3.0))
        ctx.events.append(combat.BREAK)
        if self.room_for_shots():
            patterns.radial(self, self.x, self.y, config.ENGORGE_RING, self.shots["pop"],
                            ctx.projectiles, self.rng.uniform(0, math.tau))
        self.dazed = config.ENGORGE_STUN
        self.hover = False
        self.combo = 0
        self._rest = 0.4                  # a breath once she's up again

    def _digest(self) -> None:
        self.engorged = 0.0
        self.belly = 0
        self.heal(config.ENGORGE_DIGEST * self.max_hp)
        self.ctx.effects.append(Effect("toast", self.x, self.y - 3, label="SHE DIGESTS..."))

    def _end_move(self) -> None:
        super()._end_move()
        self.hover = True
        self.dashing = False
        self.sipping = False

    def _pick_move(self) -> str:
        """Not a sip with a full belly (or no pools), not a call with the
        air already full of her brood."""
        skip = {self.last_move}
        if self.belly >= config.ENGORGE_FULL or self.engorged > 0 or not self._pools():
            skip.add("sip")
        if self._brood() >= config.PROBOSCIA_CALL[2]:
            skip.add("call")
        moves = [(m, w) for m, w in self.bspec.phases[self.phase].moves if m not in skip]
        if not moves:
            return "bite"
        total = sum(w for _, w in moves)
        r = self.rng.uniform(0, total)
        for m, w in moves:
            r -= w
            if r <= 0:
                return m
        return moves[-1][0]

    def _pools(self) -> list:
        return self.lair.spots if self.lair is not None else []

    def _brood(self) -> int:
        return sum(1 for a in self.ctx.actors if getattr(a, "summoner", None) is self and a.alive)

    def on_phase(self, phase: int, ctx: AIContext) -> None:
        label = ("HER LADYSHIP IS THIRSTY!", "FEVER!")[min(phase, 2) - 1] if phase else ""
        if label:
            ctx.effects.append(Effect("toast", self.x, self.y - 3, label=label))

    @property
    def nose(self) -> tuple[float, float]:
        """The tip of her proboscis (where needles come from)."""
        r = self.hit_radius * 0.95
        return self.x + math.cos(self.facing) * r, self.y + math.sin(self.facing) * r * 0.67

    # --- Moves --------------------------------------------------------------------------

    def m_bite(self):
        """The dive: an aim line through the target, then she lunges along
        it; whoever she passes through is bitten (she drinks: heals, and a
        gulp in the belly). Then she hangs there a moment. Last phase: three
        dives in a row, leaving fever clouds along each."""
        tell, speed, longest, width, damage, after = config.PROBOSCIA_BITE
        frenzy = self.phase >= 2
        dives = config.PROBOSCIA_FRENZY[1] if frenzy else 1
        for k in range(dives):
            t = self.target_now()
            if t is None:
                break
            self.hover = False
            wait = self.tell_s(tell if k == 0 else config.PROBOSCIA_FRENZY[2])
            # Aimed at where you'll be when she gets there (the tell, then the dive).
            reach = math.hypot(t.x - self.x, t.y - self.y)
            tx, ty = self.lead(t, self.x, self.y, secs=wait + reach / (speed * self.speed_mult))
            a = math.atan2(ty - self.y, tx - self.x)
            self.facing = a
            length = min(longest, math.hypot(tx - self.x, ty - self.y) + 6.0)
            x0, y0 = self.x, self.y
            x1, y1 = self.clamp_to_lair(x0 + math.cos(a) * length, y0 + math.sin(a) * length, 3.0)
            self.tell = ("bite", x0, y0, x1, y1)
            yield wait
            self.tell = None
            self.dashing = True
            self.ctx.events.append("swing")
            bitten = set()
            spacing = config.FEVER_CLOUD[4]
            next_cloud = spacing
            gone = 0.0
            total = math.hypot(x1 - x0, y1 - y0)
            while gone < total:
                step = min(total - gone, speed * self.speed_mult * self.dt)
                gone += step
                f = gone / total if total > 0 else 1.0
                self.x, self.y = x0 + (x1 - x0) * f, y0 + (y1 - y0) * f
                for h in self.ctx.players:
                    if id(h) in bitten or not h.hittable:
                        continue
                    if math.hypot(h.x - self.x, h.y - self.y) <= width + h.hit_radius:
                        bitten.add(id(h))
                        dealt = combat.strike(h, damage * self.damage_mult, self, a,
                                              self.ctx.effects)
                        if dealt > 0:
                            self.heal(dealt * config.PROBOSCIA_DRINK)
                            self.gulp()
                            self.ctx.events.append("hit")
                if frenzy and gone >= next_cloud:
                    self.clouds.append([self.x, self.y, 0.0])
                    next_cloud += spacing
                yield 0
            self.dashing = False
            yield after

    def m_fan(self):
        """P3: she stops, wings blurring and her proboscis glowing (the
        tell), then fans of needles at the target, moving between volleys."""
        tell, n, spread, volleys, gap = config.PROBOSCIA_FAN
        self.hover = False
        self.tell = ("needle",)
        yield self.tell_s(tell)
        self.tell = None
        for k in range(volleys):
            t = self.target_now()
            if t is None:
                break
            if self.room_for_shots():
                nx, ny = self.nose
                shell = self.shots["needle"]        # the first volley at you, the rest lead you
                patterns.fan(self, nx, ny, self.aim(t, nx, ny, shell.speed, lead=k > 0), n,
                             spread, shell, self.ctx.projectiles)
                self.ctx.events.append("bow")
            self.hover = True
            yield gap
        self.hover = True

    def m_buzz(self):
        """P5 with a gap: a whine (the tell), then rings of sound pulses
        round the target that hang a moment, then close. Out through the gap,
        or roll through the ring."""
        whine, n, radius, hold, gap, rings, between = config.PROBOSCIA_BUZZ
        self.tell = ("buzz",)
        self.ctx.events.append("hex")
        yield self.tell_s(whine)
        gap_at = self.rng.uniform(0, math.tau)
        for k in range(rings):
            t = self.target_now()
            if t is None:
                break
            patterns.ring_in(self, t.x, t.y, radius, n, self.shots["buzz"], self.ctx.projectiles,
                             hold, turn=k * math.pi / n, gap_deg=gap, gap_at=gap_at)
            self.ctx.events.append("orb")
            gap_at += self.rng.choice((-1, 1)) * self.rng.uniform(1.6, 2.6)
            yield between
        self.tell = None

    def m_call(self):
        """B2: a shrill call (a pulsing ring), and mosquitoes come out of the
        air round her (never more than a dozen at once)."""
        tell, k, cap = config.PROBOSCIA_CALL
        self.tell = ("call",)
        yield self.tell_s(tell)
        self.tell = None
        for _ in range(min(k, cap - self._brood())):
            if self.recruit is None:
                break
            a = self.rng.uniform(0, math.tau)
            r = self.rng.uniform(3.0, 6.0)
            x, y = self.clamp_to_lair(self.x + math.cos(a) * r, self.y + math.sin(a) * r, 3.0)
            add = self.recruit("mosquito", x, y)
            if add is not None:
                add.summoner = self
                add.alert = True
                self.ctx.effects.append(Effect("impact", x, y))
        self.ctx.events.append("orb")
        yield 0.3

    def m_sip(self):
        """She flies down to the nearest pool and drinks: low, still, easy
        to reach. Hurt her enough and she's shooed off without her gulp."""
        drink, shoo, fly = config.PROBOSCIA_SIP
        pools = self._pools()
        if not pools:
            return
        px, py = min(pools, key=lambda p: math.hypot(p[0] - self.x, p[1] - self.y))
        self.hover = False
        t0 = self.time
        while not self._fly_to(px, py, fly * self.speed_mult, self.dt):
            self.facing = math.atan2(py - self.y, px - self.x)
            if self.time - t0 > 6.0:
                break
            yield 0
        self.sipping = True
        self.sip_dmg = 0.0
        self.tell = ("sip",)
        t0 = self.time
        while self.time - t0 < drink:
            if self.sip_dmg >= shoo * self.max_hp:
                self.ctx.effects.append(Effect("toast", self.x, self.y - 3, label="SHOO!"))
                self.sipping = False
                self.tell = None
                return
            yield 0
        self.sipping = False
        self.tell = None
        self.ctx.effects.append(Effect("toast", self.x, self.y - 3, label="SLURP"))
        self.gulp()
        yield 0.2


# --- Khepri the Dung Emperor (M23.1) -----------------------------------------------------


class Khepri(Boss):
    """A giant dung beetle. Signature, the DUNG BALL (`ball`: [x, y, radius],
    None once it's shattered; `held`: it sits in front of him): his roll
    sends it along a telegraphed line, him pushing behind; it grows as it
    rolls and hurts more the bigger it is. If it runs into anything solid
    -- a sandstone pillar, the arena wall -- it shatters into a ring of
    clods and he sits stunned (the melee window), then rolls up a new one.
    So: stand behind a pillar. Phase 1: rolls, charges (a horn charge that
    ends in a fan of kicked sand; into a pillar, he's dazed a moment) and
    burrows (a ripple chases you, then he erupts). Phase 2 adds the dust
    storm (wings out, a curtain of dust from one side) and the scarab call.
    Phase 3: rolls are faster, two in a row."""

    def __init__(self, spec: EnemySpec, x: float, y: float, rng: random.Random,
                 spawn_id=None) -> None:
        super().__init__(spec, x, y, rng, spawn_id, hit_radius=config.KHEPRI_HIT_RADIUS)
        self.shots = config.KHEPRI_SHOTS
        self.ball: list | None = [x, y, config.DUNG_RADIUS[0]]
        self.held = True
        self.spin = 0.0                   # how far the ball has rolled (drawing)
        self.rolling = False
        self.charging = False
        self.ripple: list | None = None   # burrowed: where the sand moves
        self.wings = False                # dust storm: wings out
        self.legs = 0.0                   # walk cycle (drawing)
        self._hold_ball()

    # --- The ball -----------------------------------------------------------------------

    @property
    def ball_frac(self) -> float:
        """How big the ball is, 0 (just rolled up) .. 1 (as big as it gets)."""
        if self.ball is None:
            return 0.0
        r0, r1 = config.DUNG_RADIUS
        return max(0.0, min(1.0, (self.ball[2] - r0) / (r1 - r0)))

    def _front(self, r: float) -> tuple[float, float]:
        """Where a ball of radius r sits in front of him."""
        d = self.hit_radius * 0.8 + r
        return self.x + math.cos(self.facing) * d, self.y + math.sin(self.facing) * d

    def _hold_ball(self) -> None:
        if self.ball is not None and self.held:
            self.ball[0], self.ball[1] = self._front(self.ball[2])

    def _solid(self, x: float, y: float) -> bool:
        world = self.ctx.world if self.ctx is not None else None
        if world is None:
            return False
        if self.lair is not None and not self.lair.inside(x, y):
            return True                   # (past the ring of the arena)
        t = world.tile_at(math.floor(x), math.floor(y))
        return t is not None and t.solid

    def _ball_blocked(self, a: float) -> bool:
        """The front of the rolling ball touches something solid."""
        bx, by, r = self.ball
        return any(self._solid(bx + math.cos(a + d) * r * 0.95, by + math.sin(a + d) * r * 0.95)
                   for d in (-0.7, -0.35, 0.0, 0.35, 0.7))

    def _body_blocked(self, a: float) -> bool:
        r = self.hit_radius * 0.9
        return any(self._solid(self.x + math.cos(a + d) * r, self.y + math.sin(a + d) * r)
                   for d in (-0.5, 0.0, 0.5))

    def _shatter(self) -> None:
        """The ball breaks: clods all round, and he's stunned."""
        bx, by, r = self.ball
        lo, hi = config.DUNG_CLODS
        n = round(lo + (hi - lo) * self.ball_frac)
        if self.room_for_shots():
            patterns.radial(self, bx, by, n, self.shots["clod"], self.ctx.projectiles,
                            self.rng.uniform(0, math.tau))
        ctx = self.ctx
        ctx.effects.append(Effect("explosion", bx, by))
        ctx.effects.append(Effect("nova", bx, by, size=r + 1.0))
        ctx.effects.append(Effect("toast", self.x, self.y - 3, label="SPLAT! HE'S STUNNED!"))
        ctx.events.append(combat.BREAK)
        self.ball = None
        self.held = False
        self.rolling = False
        self.dazed = config.DUNG_STUN

    # --- Every step ---------------------------------------------------------------------

    def think(self, ctx: AIContext, dt: float) -> None:
        self.ctx = ctx
        if self.rolling or self.charging:
            self.legs += dt * 14.0
        t = self.tgt if self.tgt is not None and self.tgt.alive else None
        if (t is not None and not (self.rolling or self.charging or self.submerged)
                and self.dazed <= 0 and self.move not in ("roll", "charge")):
            self.facing = math.atan2(t.y - self.y, t.x - self.x)
        self._hold_ball()
        super().think(ctx, dt)

    def on_phase(self, phase: int, ctx: AIContext) -> None:
        label = ("THE EMPEROR IS ANGRY!", "THE SANDS BOIL!")[min(phase, 2) - 1] if phase else ""
        if label:
            ctx.effects.append(Effect("toast", self.x, self.y - 3, label=label))

    # --- Moves --------------------------------------------------------------------------

    def _fetch_ball(self):
        """Back to the ball he left (or a new one rolled up if it's gone or
        too far to fetch)."""
        if self.ball is not None and not self.held:
            t0 = self.time
            while self.time - t0 < 3.0:
                bx, by, r = self.ball
                a = math.atan2(by - self.y, bx - self.x)
                d = math.hypot(bx - self.x, by - self.y) - (self.hit_radius * 0.8 + r)
                if d <= 0.2:
                    self.facing = a
                    self.held = True
                    break
                self.facing = a
                step = min(d, config.KHEPRI_WALK * self.dt)
                if self._body_blocked(a):
                    break
                self.x += math.cos(a) * step
                self.y += math.sin(a) * step
                self.legs += self.dt * 10.0
                yield 0
            if not self.held:
                self.ball = None
        if self.ball is None:
            self.tell = ("gather",)
            r0 = config.DUNG_RADIUS[0]
            self.ball = [*self._front(0.3), 0.3]
            self.held = True
            t0 = self.time
            while self.time - t0 < config.DUNG_GATHER:
                f = (self.time - t0) / config.DUNG_GATHER
                self.ball[2] = 0.3 + (r0 - 0.3) * f
                self._hold_ball()
                yield 0
            self.ball[2] = r0
            self.tell = None

    def m_roll(self):
        """The signature: an aim line from the ball through where you'll be,
        then he rolls it along the line, pushing behind. It grows as it
        goes; anyone it runs over is hit (harder, the bigger it is) and
        knocked aside; anything solid shatters it and stuns him."""
        tell, speed, longest = config.KHEPRI_ROLL
        frenzy = self.phase >= 2
        if frenzy:
            speed *= config.KHEPRI_FRENZY
        for k in range(2 if frenzy else 1):
            yield from self._fetch_ball()
            t = self.target_now()
            if t is None or self.ball is None:
                return
            wait = self.tell_s(tell if k == 0 else tell * 0.6)
            bx, by, _ = self.ball
            reach = math.hypot(t.x - bx, t.y - by)
            tx, ty = self.lead(t, bx, by, secs=wait + reach / speed)
            a = math.atan2(ty - self.y, tx - self.x)
            self.facing = a
            self._hold_ball()
            bx, by, r = self.ball
            length = min(longest, math.hypot(tx - bx, ty - by) + 8.0)
            self.tell = ("roll", bx, by, bx + math.cos(a) * length, by + math.sin(a) * length, r)
            yield wait
            self.tell = None
            self.rolling = True
            self.ctx.events.append("swing")
            hit = set()
            lo, hi = config.DUNG_DAMAGE
            gone = 0.0
            while gone < length:
                step = min(length - gone, speed * self.dt)
                gone += step
                self.x += math.cos(a) * step
                self.y += math.sin(a) * step
                self.ball[2] = min(config.DUNG_RADIUS[1], self.ball[2] + config.DUNG_GROW * step)
                self.spin += step / max(0.5, self.ball[2])
                self._hold_ball()
                if self._ball_blocked(a):
                    self._shatter()
                    yield config.DUNG_STUN
                    return
                bx, by, r = self.ball
                for h in self.ctx.players:
                    if id(h) in hit or not h.hittable:
                        continue
                    if math.hypot(h.x - bx, h.y - by) <= r + h.hit_radius:
                        hit.add(id(h))
                        damage = (lo + (hi - lo) * self.ball_frac) * self.damage_mult
                        combat.strike(h, damage, self, a, self.ctx.effects)
                        # Knocked aside: off the ball's line, to whichever side you were on.
                        side = math.copysign(1.0, math.sin(math.atan2(h.y - by, h.x - bx) - a))
                        pa = a + side * math.pi / 2
                        combat.push(h, self.ctx.world, math.cos(pa) * config.DUNG_PUSH,
                                    math.sin(pa) * config.DUNG_PUSH)
                        self.ctx.events.append("hit")
                yield 0
            self.rolling = False
            yield 0.35

    def m_charge(self):
        """B1: he leaves the ball, lowers his horn (an aim line), and charges
        through where you'll be; when he stops he kicks a fan of sand at
        you. Into a pillar, he's dazed a moment instead."""
        tell, speed, longest, damage, daze = config.KHEPRI_CHARGE
        t = self.target_now()
        if t is None:
            return
        self.held = False
        wait = self.tell_s(tell)
        tx, ty = self.lead(t, self.x, self.y,
                           secs=wait + math.hypot(t.x - self.x, t.y - self.y) / speed)
        a = math.atan2(ty - self.y, tx - self.x)
        self.facing = a
        length = min(longest, math.hypot(tx - self.x, ty - self.y) + 6.0)
        self.tell = ("charge", self.x, self.y, self.x + math.cos(a) * length,
                     self.y + math.sin(a) * length)
        yield wait
        self.tell = None
        self.charging = True
        self.ctx.events.append("swing")
        hit = set()
        gone = 0.0
        while gone < length:
            if self._body_blocked(a):
                self.charging = False
                self.ctx.effects.append(Effect("explosion", self.x + math.cos(a) * self.hit_radius,
                                               self.y + math.sin(a) * self.hit_radius))
                self.ctx.events.append(combat.BREAK)
                self.dazed = daze
                yield daze
                return
            step = min(length - gone, speed * self.dt)
            gone += step
            self.x += math.cos(a) * step
            self.y += math.sin(a) * step
            for h in self.ctx.players:
                if id(h) in hit or not h.hittable:
                    continue
                if math.hypot(h.x - self.x, h.y - self.y) <= self.hit_radius + h.hit_radius:
                    hit.add(id(h))
                    combat.strike(h, damage * self.damage_mult, self, a, self.ctx.effects)
            yield 0
        self.charging = False
        n, spread = config.KHEPRI_SPRAY
        t = self.target_now()
        if t is not None and self.room_for_shots():
            shell = self.shots["sand"]
            patterns.fan(self, self.x, self.y, self.aim(t, self.x, self.y, shell.speed), n,
                         spread, shell, self.ctx.projectiles)
            self.ctx.events.append("fizzle")
        yield 0.4

    def m_burrow(self):
        """P8 + P1: he digs in (can't be hit; the ball stays where it is), a
        ripple in the sand chases you, stops (the tell: a ring where he'll
        come up), and he erupts there: a blast and a ring of sand."""
        dig, chase, lock, radius, damage, ring = config.KHEPRI_BURROW
        self.held = False
        self.tell = ("dig",)
        yield dig
        self.submerged = True
        self.ctx.effects.append(Effect("eruption", self.x, self.y))
        self.ripple = [self.x, self.y]
        t0 = self.time
        while self.time - t0 < chase:
            t = self.target_now()
            if t is None:
                break
            rx, ry = self.ripple
            a = math.atan2(t.y - ry, t.x - rx)
            d = math.hypot(t.x - rx, t.y - ry)
            step = min(d, 16.0 * self.dt)
            self.ripple = list(self.clamp_to_lair(rx + math.cos(a) * step,
                                                  ry + math.sin(a) * step, 4.0))
            if int(self.time * 10) % 2 == 0:
                self.ctx.effects.append(Effect("burrow", *self.ripple))
            yield 0
        rx, ry = self.ripple
        self.tell = ("erupt", rx, ry, radius)
        yield self.tell_s(lock)
        self.tell = None
        self.x, self.y = rx, ry
        self.ripple = None
        self.submerged = False
        combat.blast(rx, ry, radius, damage * self.damage_mult, self, self.ctx.actors,
                     effects=self.ctx.effects)
        self.ctx.effects.append(Effect("eruption", rx, ry))
        self.ctx.effects.append(Effect("explosion", rx, ry))
        self.ctx.events.append("boulder")
        self.shove_heroes(1.0)
        if self.room_for_shots():
            patterns.radial(self, rx, ry, ring, self.shots["sand"], self.ctx.projectiles,
                            self.rng.uniform(0, math.tau))
        yield 0.6

    def m_storm(self):
        """P10: wings out (the tell), and a storm of dust blows across where
        you stood from one side, row after row, a hole drifting along the
        rows to weave through (or run out to the side)."""
        tell, dur, every, gap, hole, half = config.KHEPRI_STORM
        self.wings = True
        self.tell = ("storm",)
        yield self.tell_s(tell)
        t = self.target_now()
        if t is None:
            self.wings = False
            return
        heading = self.rng.choice((0.0, math.pi / 2, math.pi, -math.pi / 2))
        cx, cy = t.x, t.y
        phase = self.rng.uniform(0, math.tau)
        tt = 0.0
        while tt < dur:
            hole_at = math.sin(phase + tt * 0.8) * half * 0.6
            if self.room_for_shots():
                patterns.curtain(self, cx, cy, heading, 20.0, half, gap, hole_at, hole,
                                 self.shots["dust"], self.ctx.projectiles)
            tt += every
            yield every
        self.wings = False
        self.tell = None

    def m_swarm(self):
        """B2: a clicking call (the tell), and scarabs scuttle out of the
        sand round him (never more than a few alive at once)."""
        tell, k, cap = config.KHEPRI_SWARM
        self.tell = ("click",)
        yield self.tell_s(tell)
        self.tell = None
        alive = sum(1 for a in self.ctx.actors if getattr(a, "summoner", None) is self and a.alive)
        for _ in range(min(k, cap - alive)):
            if self.recruit is None:
                break
            a = self.rng.uniform(0, math.tau)
            r = self.rng.uniform(4.0, 7.0)
            x, y = self.clamp_to_lair(self.x + math.cos(a) * r, self.y + math.sin(a) * r, 4.0)
            add = self.recruit("scarab", x, y)
            if add is not None:
                add.summoner = self
                add.alert = True
                self.ctx.effects.append(Effect("eruption", x, y))
        self.ctx.events.append("orb")
        yield 0.4
