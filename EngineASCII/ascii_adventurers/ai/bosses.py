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
        Actor.__init__(self, spec.max_hp, hit_radius)
        self.x, self.y = x, y
        self.facing = 0.0
        self.half = spec.size_px / 2
        self.init_brain(spec, rng, spawn_id)
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

    # --- Being a boss ----------------------------------------------------------------

    @property
    def hittable(self) -> bool:
        return self.alive and self.airborne <= 0 and not self.submerged

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
        self._rest = self.bspec.phases[self.phase].rest

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
        yield config.FROGGY_TELL
        for _ in range(volleys):
            t = self.target_now()
            if t is None:
                break
            if self.room_for_shots():
                mx, my = self.mouth
                patterns.fan(self, mx, my, math.atan2(t.y - my, t.x - mx), n, spread,
                             self.shots["tadpole"], self.ctx.projectiles, self._tint())
                self.ctx.events.append("orb")
            yield gap
        self.mouth_open = False

    def m_stream(self):
        """P3 (one at a time): a stream of bubbles, each aimed at where the
        target is now -- keep moving and they trail behind you, stand still
        and they all land."""
        n, gap = config.FROGGY_STREAM
        self.tell = ("mouth",)
        self.mouth_open = True
        yield config.FROGGY_TELL
        for _ in range(n):
            t = self.target_now()
            if t is None:
                break
            if self.room_for_shots():
                mx, my = self.mouth
                patterns.shoot(self, mx, my, math.atan2(t.y - my, t.x - mx),
                               self.shots["stream"], self.ctx.projectiles, self._tint())
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
        a = math.atan2(t.y - self.y, t.x - self.x)
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
        dx, dy = t.x - self.x, t.y - self.y
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
        yield config.FROGGY_TELL
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
        yield tell
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
        yield config.FROGGY_TELL
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
        yield config.FROGGY_TELL
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
        yield config.FROGGY_TELL * 0.6
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
        keeping a little apart from its neighbours, inside the arena.
        Leeches swim over everything (no walls for them)."""
        spacing = config.LEECH_FLOCK[1]
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
                d = math.hypot(dx, dy)
                top = speed * (4.0 if self.mode == "whirl" else 1.6 if self.mode == "rush" else 1.0)
                k = min(top, d * 4.0) / d if d > 1e-6 else 0.0
                vx, vy = dx * k, dy * k
            else:
                vx = vy = 0.0
            p.vx, p.vy = vx, vy
        # Separation (a soft push apart, so the swarm reads as many leeches).
        for i, p in enumerate(free):
            for q in free[i + 1:]:
                dx, dy = q.x - p.x, q.y - p.y
                d2 = dx * dx + dy * dy
                if 1e-9 < d2 < spacing * spacing:
                    d = math.sqrt(d2)
                    push = (spacing - d) / d * 0.5 * 6.0
                    p.vx -= dx * push
                    p.vy -= dy * push
                    q.vx += dx * push
                    q.vy += dy * push
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
        a = math.atan2(t.y - self.y, t.x - self.x)
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
        yield tell
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
        yield tell
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
