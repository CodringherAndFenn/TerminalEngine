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

Ol' Spitter, the Unmannered One (desert, M23.2): a two-humped camel in
his caravanserai. Signature: his humps hold his spit; dry, he kneels at a
water trough to drink (the melee window) -- smash it while he drinks and
he chokes. And his ricochet loogie, which bounces off walls, arches and
posts, splitting as it goes. Phase 1: spit fans, mortar loogies, ricochet
loogies, gallops that churn up stinging sand, and a kick for anyone
behind him. Phase 2 adds a stampede of ghost camels. Phase 3: mirages
(decoys) and a spray spiral; the stampede comes from two sides.

The Nameless Magus, Holder of Time (desert, M23.3): a sand wizard in his
sunken observatory, a signature a phase, each kept: sand runes you scuff
out (a whole batch scuffed drains him), then shifting dunes (walls of sand
and quicksand), then the hourglass (time zones; shatter it before the sand
runs out). Between them: the sun lance, sigils with a blade fan, blinks,
the vortex and the sand serpent.

The Fallout King (ruins, M24.1): an irradiated monster in his reactor
vault, a signature a phase, each kept: rads (a meter on every hero;
decontamination showers wipe it), then fallout (patches with isotope rods
to smash), then the meltdown core (shut four valves to expose it, or hide
behind lead when it blows). Between them: the gamma cross, toxic barrels,
ghouls, EMP rings, homing skulls and grate dives.

The Snow King, King of Loneliness (ruins, M24.2): a lonely frost
wizard-king in his throne hall, a signature a phase, each kept: his crown
(knock it off with a burst of damage, kick it away; crownless he can't
attack), then black ice (sheets you slide on; fire braziers melt it), then
flash freeze (a chill meter; full, you're encased). Between them: shard
fans, spike rings, penguin squads, frost breath, icicles, blizzards and
snowballs.

Fragile, The Misunderstood (ruins, M24.3): a vampire with a bass-axe in
her ruined ballroom, a signature a phase, each kept: sunlight (open the
shutters: she burns in the shafts), then shapeshifting (bats, a wolf,
herself), then on the beat (roll on a beat to stun her). Beaten, she sits
down and cries: give her back Mr. Buttons.
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
        self.walked = 0.0                 # tiles moved, all told (drawing: the walk cycle)
        self._was_at = (x, y)

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
        self.walked += min(2.0, math.hypot(self.x - self._was_at[0], self.y - self._was_at[1]))
        self._was_at = (self.x, self.y)
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

    def in_arena(self, h) -> bool:
        """Is hero h in this boss's arena (always, without a lair)? Bosses
        that change heroes' state (walking speed, rads) touch only theirs:
        another boss may be fighting in another arena."""
        return self.lair is None or self.lair.inside(h.x, h.y)

    def pick_target(self):
        heroes = self.heroes()
        return self.rng.choice(heroes) if heroes else None

    def drift_target(self):
        """Who to keep moving round between moves: this move's target, else
        the nearest hero (without picking one: no dice rolled)."""
        if self.tgt is not None and self.tgt.alive:
            return self.tgt
        heroes = self.heroes()
        return min(heroes, key=lambda h: math.hypot(h.x - self.x, h.y - self.y), default=None)

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


# --- Ol' Spitter, the Unmannered One (M23.2) ---------------------------------------------


class OlSpitter(Boss):
    """A two-humped camel with no manners, in his caravanserai.

    Signature, HUMPS AND THIRST: `water` (0..HUMP_WATER) is his spit, half
    in each hump (drawn shrinking as he spends it). Each spitting move costs
    HUMP_COST. When he can't afford another he goes to the nearest unbroken
    water trough (the lair's spots[1:]) and kneels to drink: still, taking
    DRINK[1] x damage -- the melee window -- and up again full. Smash the
    trough while he drinks and he CHOKES (stunned CHOKE_STUN s, with only
    what he'd drunk). With no trough left he's PARCHED: spit costs nothing,
    and he's slower but angrier -- he rests less between moves (PARCHED).

    And the RICOCHET LOOGIE (`loogies`: [x, y, vx, vy, radius, generation,
    age, hit]): an aim line showing its first bounces, then a big gob that
    bounces off anything solid, splitting in two at each of its first
    LOOGIE_SPLITS bounces. Arches and posts are cover, and also what it
    bounces off.

    Phase 1: spit fans, mortar loogies (lobbed, a ring of spit where they
    land), ricochet loogies, gallops (a ">" line, then a run that churns
    the sand behind him: `trail` patches that sting). Stand behind him and
    he KICKS (hind legs flash, then a cone behind him). Phase 2 adds the
    stampede: rows of ghost camels (`ghosts`) charging across where you
    stood, each row with a gap. Phase 3: mirages (decoy camels) and the
    spray spiral, and the stampede's rows come from two sides."""

    def __init__(self, spec: EnemySpec, x: float, y: float, rng: random.Random,
                 spawn_id=None) -> None:
        super().__init__(spec, x, y, rng, spawn_id, hit_radius=config.SPITTER_HIT_RADIUS)
        self.shots = config.SPITTER_SHOTS
        self.water = float(config.HUMP_WATER)
        self.rear = False                 # head back: about to spit (the tell)
        self.kneeling = False             # drinking at a trough (the melee window)
        self.drinking_at: tuple | None = None   # the trough's middle
        self.galloping = False
        self.kicking = False              # hind legs flashing: the kick's tell
        self.spinning = False             # the spray spiral
        self.legs = 0.0                   # walk cycle (drawing)
        self.loogies: list[list] = []
        self.trail: list[list[float]] = []    # churned sand: [x, y, age]
        self._trail_tick = 0.0
        self.ghosts: list[list] = []      # stampede: [x, y, vx, vy, age, life, hit]
        self.lobs: list = []              # mortar loogies in the air (their landing splash)
        self.behind = 0.0                 # s someone has stood behind him
        self._was_parched = False

    # --- Thirst -----------------------------------------------------------------------

    def troughs(self) -> list[tuple[float, float]]:
        """The middles of his lair's troughs that are still whole."""
        if self.lair is None or self.ctx is None:
            return []
        from ..world import tiles
        from ..world.landmarks import trough_tiles
        world = self.ctx.world
        return [s for s in self.lair.spots[1:]
                if all(world.tile_at(tx, ty) is tiles.TROUGH for tx, ty in trough_tiles(*s))]

    @property
    def thirsty(self) -> bool:
        """Does spitting cost him water? (Only in a lair with troughs.)"""
        return self.lair is not None and len(self.lair.spots) > 1

    @property
    def parched(self) -> bool:
        return self.thirsty and self.ctx is not None and not self.troughs()

    @property
    def hump_frac(self) -> tuple[float, float]:
        """How full each hump is (front, back), 0..1: the back one empties last."""
        half = config.HUMP_WATER / 2
        return (max(0.0, min(1.0, (self.water - half) / half)),
                max(0.0, min(1.0, self.water / half)))

    def _cost(self, move: str) -> float:
        if not self.thirsty or self.parched:
            return 0.0
        return config.HUMP_COST.get(move, 0)

    def _spend(self, move: str) -> None:
        self.water = max(0.0, self.water - self._cost(move))

    @property
    def speed_mult(self) -> float:
        return config.PARCHED[0] if self.parched else 1.0

    def take_damage(self, amount, source, from_angle):
        if self.kneeling:
            amount *= config.DRINK[1]
        return super().take_damage(amount, source, from_angle)

    # --- Every step ---------------------------------------------------------------------

    def think(self, ctx: AIContext, dt: float) -> None:
        self.ctx = ctx
        if self.galloping:
            self.legs += dt * 16.0
        self._fly_loogies(dt)
        self._sting_trail(dt)
        self._run_ghosts(dt)
        self._land_lobs()
        self._watch_back(dt)
        if self.thirsty and not self._was_parched and self.parched:
            self._was_parched = True
            ctx.effects.append(Effect("toast", self.x, self.y - 3,
                                      label="NO WATER LEFT! HE'S PARCHED!"))
        t = self.tgt if self.tgt is not None and self.tgt.alive else None
        if (t is not None and self.dazed <= 0 and not (self.galloping or self.kneeling
                                                       or self.spinning or self.kicking)
                and self.move not in ("drink", "kick", "gallop", "spiral", "loogie")):
            # He turns to face his target, but slowly (a camel): get round
            # behind him and he can't spit at you -- linger and he kicks.
            want = math.atan2(t.y - self.y, t.x - self.x)
            turn = (want - self.facing + math.pi) % math.tau - math.pi
            most = config.SPITTER_TURN * dt
            self.facing += max(-most, min(most, turn))
        super().think(ctx, dt)

    def on_phase(self, phase: int, ctx: AIContext) -> None:
        label = ("HE BELLOWS FOR THE CARAVAN!", "THE HEAT HAZE RISES...")[min(phase, 2) - 1] \
            if phase else ""
        if label:
            ctx.effects.append(Effect("toast", self.x, self.y - 3, label=label))

    def _end_move(self) -> None:
        super()._end_move()
        self.rear = self.kneeling = self.galloping = self.kicking = self.spinning = False
        self.drinking_at = None
        if self.parched and self.combo == 0:
            self._rest *= config.PARCHED[1]

    def _pick_move(self) -> str:
        """A kick if someone's been behind him; a drink when he can't
        afford a spit; a gallop if the target's far; else by weight, among
        the moves he can afford (and no mirage with his decoys all out)."""
        if self.behind >= config.SPITTER_KICK[0]:
            return "kick"
        moves = [(m, w) for m, w in self.bspec.phases[self.phase].moves if m != self.last_move]
        afford = [(m, w) for m, w in moves if self._cost(m) <= self.water]
        if self.thirsty and not self.parched and not any(self._cost(m) > 0 for m, _ in afford) \
                and self.water < max(config.HUMP_COST.values()):
            return "drink"
        t = self.target_now()
        if t is not None and math.hypot(t.x - self.x, t.y - self.y) > 30 \
                and self.last_move != "gallop":
            return "gallop"
        if self._decoys() >= config.SPITTER_MIRAGE[2]:
            afford = [(m, w) for m, w in afford if m != "mirage"]
        if not afford:
            return "gallop"
        total = sum(w for _, w in afford)
        r = self.rng.uniform(0, total)
        for m, w in afford:
            r -= w
            if r <= 0:
                return m
        return afford[-1][0]

    def _decoys(self) -> int:
        return sum(1 for a in self.ctx.actors if getattr(a, "summoner", None) is self and a.alive)

    @property
    def mouth(self) -> tuple[float, float]:
        d = self.hit_radius + 1.0
        return self.x + math.cos(self.facing) * d, self.y + math.sin(self.facing) * d

    def spit_angle(self, a: float) -> float:
        """An aim, kept within SPITTER_SPIT_ARC of where his head points
        (he can't spit over his own back)."""
        lim = math.radians(config.SPITTER_SPIT_ARC)
        off = (a - self.facing + math.pi) % math.tau - math.pi
        return self.facing + max(-lim, min(lim, off))

    def _solid(self, x: float, y: float) -> bool:
        world = self.ctx.world if self.ctx is not None else None
        if world is None:
            return False
        if self.lair is not None and not self.lair.inside(x, y):
            return True                   # (past the ring of the arena)
        t = world.tile_at(math.floor(x), math.floor(y))
        return t is not None and t.solid

    def _body_blocked(self, a: float) -> bool:
        r = self.hit_radius * 0.9
        return any(self._solid(self.x + math.cos(a + d) * r, self.y + math.sin(a + d) * r)
                   for d in (-0.5, 0.0, 0.5))

    def _step_to(self, gx: float, gy: float, speed: float) -> bool:
        """A walking step toward (gx, gy), sliding round what's in the way
        (straight, else up to 70 degrees either side). True once there."""
        dx, dy = gx - self.x, gy - self.y
        d = math.hypot(dx, dy)
        step = speed * self.dt
        if d <= max(step, 0.3):
            self.x, self.y = gx, gy
            return True
        a = math.atan2(dy, dx)
        for turn in (0.0, 0.6, -0.6, 1.2, -1.2):
            if not self._body_blocked(a + turn):
                self.facing = a + turn
                self.x += math.cos(a + turn) * step
                self.y += math.sin(a + turn) * step
                self.legs += self.dt * 9.0
                return False
        return False

    def _watch_back(self, dt: float) -> None:
        """How long someone has stood in the cone behind him (the kick)."""
        notice, reach, half, *_ = config.SPITTER_KICK
        back = self.facing + math.pi
        lim = math.radians(half)
        near = False
        if self.dazed <= 0 and not self.kneeling and not self.galloping:
            for h in self.ctx.players:
                if not h.hittable:
                    continue
                d = math.hypot(h.x - self.x, h.y - self.y)
                if d > reach + h.hit_radius + self.hit_radius:
                    continue
                off = (math.atan2(h.y - self.y, h.x - self.x) - back + math.pi) % math.tau - math.pi
                if abs(off) <= lim:
                    near = True
                    break
        self.behind = self.behind + dt if near else max(0.0, self.behind - dt * 2)
        if self.behind >= notice and self._gen is None and self.dazed <= 0:
            self._rest = min(self._rest, 0.0)     # (no waiting out the rest)

    # --- What he leaves flying ----------------------------------------------------------

    def _fly_loogies(self, dt: float) -> None:
        """Move the ricochet loogies in small steps: one that touches
        something solid bounces off it (the motion across the face flips)
        and splits in two (or, past LOOGIE_SPLITS, pops); one that touches
        a hero hits and pops."""
        if not self.loogies:
            return
        out = []
        for g in self.loogies:
            g[6] += dt
            if g[6] >= config.LOOGIE_LIFE:
                self.ctx.effects.append(Effect("fizzle", g[0], g[1]))
                continue
            out.extend(self._fly_one(g, dt))
        self.loogies = out

    def _fly_one(self, g: list, dt: float) -> list:
        x, y, vx, vy, r, gen, age, hit = g
        speed = math.hypot(vx, vy) or 1.0
        n = max(1, math.ceil(speed * dt / 0.25))
        h = dt / n
        for _ in range(n):
            ux, uy = vx / speed, vy / speed
            nx, ny = x + vx * h, y + vy * h
            lead = r * 0.6
            if self._solid(nx + ux * lead, ny + uy * lead):
                bx = self._solid(nx + ux * lead, y + uy * lead)
                by = self._solid(x + ux * lead, ny + uy * lead)
                if bx:
                    vx = -vx
                if by:
                    vy = -vy
                if not bx and not by:
                    vx, vy = -vx, -vy
                self.ctx.effects.append(Effect("impact", x + ux * r, y + uy * r))
                self.ctx.events.append("fizzle")
                if gen >= config.LOOGIE_SPLITS:
                    self.ctx.effects.append(Effect("nova", x, y, size=r + 0.5))
                    return []
                a = math.atan2(vy, vx)
                half = math.radians(config.LOOGIE_SPREAD) / 2
                kids = []
                for side in (-1, 1):
                    ka = a + side * half
                    kids.append([x, y, math.cos(ka) * speed, math.sin(ka) * speed,
                                 r * config.LOOGIE_SHRINK, gen + 1, age, set(hit)])
                return kids
            x, y = nx, ny
            for hero in self.ctx.players:
                if id(hero) in hit or not hero.hittable:
                    continue
                if math.hypot(hero.x - x, hero.y - y) <= r + hero.hit_radius:
                    dmg = config.LOOGIE_DAMAGE[min(gen, len(config.LOOGIE_DAMAGE) - 1)]
                    combat.strike(hero, dmg * self.damage_mult, self, math.atan2(vy, vx),
                                  self.ctx.effects)
                    self.ctx.effects.append(Effect("nova", x, y, size=r + 0.3))
                    self.ctx.events.append("hit")
                    return []
        return [[x, y, vx, vy, r, gen, age, hit]]

    def _sting_trail(self, dt: float) -> None:
        """The gallop's churned sand ages, and stings the heroes in it."""
        if not self.trail:
            return
        radius, life, tick, damage, _ = config.SPITTER_TRAIL
        for c in self.trail:
            c[2] += dt
        self.trail = [c for c in self.trail if c[2] < life]
        self._trail_tick -= dt
        if self._trail_tick > 0:
            return
        self._trail_tick += tick
        for h in self.ctx.players:
            if h.hittable and any(math.hypot(h.x - c[0], h.y - c[1]) <= radius + h.hit_radius
                                  for c in self.trail):
                combat.strike(h, damage * self.damage_mult, self, None, self.ctx.effects)

    def _run_ghosts(self, dt: float) -> None:
        """Stampede ghosts run straight through everything, each trampling
        a hero once (knocked along the way they run); they fade in harmless
        for their first 0.35 s."""
        if not self.ghosts:
            return
        *_, damage, radius, _ = config.SPITTER_STAMPEDE
        out = []
        for g in self.ghosts:
            g[0] += g[2] * dt
            g[1] += g[3] * dt
            g[4] += dt
            if g[4] >= g[5]:
                continue
            out.append(g)
            if g[4] < 0.35:
                continue
            for h in self.ctx.players:
                if id(h) in g[6] or not h.hittable:
                    continue
                if math.hypot(h.x - g[0], h.y - g[1]) <= radius + h.hit_radius:
                    g[6].add(id(h))
                    a = math.atan2(g[3], g[2])
                    combat.strike(h, damage * self.damage_mult, self, a, self.ctx.effects)
                    combat.push(h, self.ctx.world, math.cos(a) * 2.0, math.sin(a) * 2.0)
                    self.ctx.events.append("hit")
        self.ghosts = out

    def _land_lobs(self) -> None:
        """A mortar loogie that came down splashes a ring of spit, flying
        out from the edge of its blast (so standing on the mark costs the
        blast, not the ring as well)."""
        if not self.lobs:
            return
        still = []
        for p in self.lobs:
            if p.alive:
                still.append(p)
                continue
            if self.room_for_shots():
                x, y = p.target
                n = config.SPITTER_MORTAR[3]
                r = p.spec.blast_radius
                turn = self.rng.uniform(0, math.tau)
                for k in range(n):
                    a = turn + k * math.tau / n
                    patterns.shoot(self, x + math.cos(a) * r, y + math.sin(a) * r, a,
                                   self.shots["splash"], self.ctx.projectiles)
        self.lobs = still

    def _trace(self, x: float, y: float, a: float, bounces: int = 2,
               longest: float = 70.0) -> list[tuple[float, float]]:
        """Where a loogie fired from (x, y) along `a` would go: the start,
        each bounce (up to `bounces`), and where the trace stops."""
        pts = [(x, y)]
        vx, vy = math.cos(a), math.sin(a)
        gone = 0.0
        step = 0.3
        while gone < longest:
            nx, ny = x + vx * step, y + vy * step
            if self._solid(nx, ny):
                bx, by = self._solid(nx, y), self._solid(x, ny)
                if bx:
                    vx = -vx
                if by:
                    vy = -vy
                if not bx and not by:
                    vx, vy = -vx, -vy
                pts.append((x, y))
                if len(pts) > bounces + 1:
                    return pts
                continue
            x, y = nx, ny
            gone += step
        pts.append((x, y))
        return pts

    # --- Moves --------------------------------------------------------------------------

    def m_fan(self):
        """P3: head back (the tell), then fans of spit at the target -- the
        first at you, the rest leading you."""
        tell, n, spread, volleys, gap = config.SPITTER_FAN
        self.rear = True
        self.tell = ("rear",)
        yield self.tell_s(tell)
        self.rear = False
        self.tell = None
        self._spend("fan")
        for k in range(volleys):
            t = self.target_now()
            if t is None:
                break
            if self.room_for_shots():
                mx, my = self.mouth
                shell = self.shots["spit"]
                a = self.spit_angle(self.aim(t, mx, my, shell.speed, lead=k > 0))
                patterns.fan(self, mx, my, a, n, spread, shell, self.ctx.projectiles)
                self.ctx.events.append("fizzle")
            yield gap

    def m_mortar(self):
        """P8: lobbed loogies, one after another, each landing where you'll
        be (a blinking ring shows where) and splashing a ring of spit."""
        tell, n, between, _ = config.SPITTER_MORTAR
        self.rear = True
        self.tell = ("rear",)
        yield self.tell_s(tell)
        self.rear = False
        self.tell = None
        self._spend("mortar")
        shell = self.shots["lob"]
        for k in range(n):
            t = self.target_now()
            if t is None:
                break
            mx, my = self.mouth
            tx, ty = self.lead(t, mx, my, shell.speed) if k else (t.x, t.y)
            a = self.spit_angle(math.atan2(ty - my, tx - mx))
            p = patterns.shoot(self, mx, my, a, shell, self.ctx.projectiles)
            p.flight = min(shell.max_range, math.hypot(tx - mx, ty - my))
            p.target = (mx + math.cos(a) * p.flight, my + math.sin(a) * p.flight)
            self.lobs.append(p)
            self.ctx.events.append("fizzle")
            yield between

    def m_loogie(self):
        """The ricochet loogie: an aim line through its first bounces (the
        tell), then the gob."""
        t = self.target_now()
        if t is None:
            return
        self.rear = True
        mx, my = self.mouth
        a = self.aim(t, mx, my, config.LOOGIE_SPEED, secs=config.LOOGIE_TELL)
        self.facing = a
        mx, my = self.mouth
        self.tell = ("loogie", self._trace(mx, my, a))
        yield self.tell_s(config.LOOGIE_TELL)
        self.tell = None
        self.rear = False
        self._spend("loogie")
        mx, my = self.mouth
        s = config.LOOGIE_SPEED
        self.loogies.append([mx, my, math.cos(a) * s, math.sin(a) * s, config.LOOGIE_RADIUS,
                             0, 0.0, set()])
        self.ctx.events.append("boulder")
        yield 0.4

    def m_gallop(self):
        """B1 + B3: a ">" line (the tell), then he gallops along it through
        where you'll be, trampling (and shoving aside) whoever's in the way
        and churning up stinging sand behind him. Into a wall, an arch or a
        post, he's dazed a moment."""
        tell, speed, longest, damage, daze = config.SPITTER_GALLOP
        speed *= self.speed_mult
        t = self.target_now()
        if t is None:
            return
        wait = self.tell_s(tell)
        tx, ty = self.lead(t, self.x, self.y,
                           secs=wait + math.hypot(t.x - self.x, t.y - self.y) / speed)
        a = math.atan2(ty - self.y, tx - self.x)
        self.facing = a
        length = min(longest, math.hypot(tx - self.x, ty - self.y) + 6.0)
        self.tell = ("gallop", self.x, self.y, self.x + math.cos(a) * length,
                     self.y + math.sin(a) * length)
        yield wait
        self.tell = None
        self.galloping = True
        self.ctx.events.append("swing")
        hit = set()
        gone = 0.0
        spacing = config.SPITTER_TRAIL[4]
        next_patch = spacing
        while gone < length:
            if self._body_blocked(a):
                self.galloping = False
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
            if gone >= next_patch:
                bx = self.x - math.cos(a) * self.hit_radius
                by = self.y - math.sin(a) * self.hit_radius
                self.trail.append([bx, by, 0.0])
                next_patch += spacing
            for h in self.ctx.players:
                if id(h) in hit or not h.hittable:
                    continue
                if math.hypot(h.x - self.x, h.y - self.y) <= self.hit_radius + h.hit_radius:
                    hit.add(id(h))
                    combat.strike(h, damage * self.damage_mult, self, a, self.ctx.effects)
                    side = math.copysign(1.0, math.sin(math.atan2(h.y - self.y, h.x - self.x) - a))
                    pa = a + side * math.pi / 2
                    combat.push(h, self.ctx.world, math.cos(pa) * 3.0, math.sin(pa) * 3.0)
            yield 0
        self.galloping = False
        yield 0.3

    def m_kick(self):
        """Someone's lingered behind him: his hind legs flash (the tell),
        then he bucks -- a cone behind him that hurts and throws you back."""
        _, reach, half, tell, damage, push = config.SPITTER_KICK
        self.kicking = True
        self.tell = ("kick",)
        yield self.tell_s(tell)
        self.tell = None
        back = self.facing + math.pi
        lim = math.radians(half)
        for h in self.ctx.players:
            if not h.hittable:
                continue
            d = math.hypot(h.x - self.x, h.y - self.y)
            if d > reach + h.hit_radius + self.hit_radius:
                continue
            a = math.atan2(h.y - self.y, h.x - self.x)
            if abs((a - back + math.pi) % math.tau - math.pi) > lim:
                continue
            combat.strike(h, damage * self.damage_mult, self, a, self.ctx.effects)
            combat.push(h, self.ctx.world, math.cos(a) * push, math.sin(a) * push)
        self.ctx.effects.append(Effect("debris", self.x + math.cos(back) * (self.hit_radius + 1),
                                       self.y + math.sin(back) * (self.hit_radius + 1)))
        self.ctx.events.append("boulder")
        self.behind = 0.0
        yield 0.35
        self.kicking = False

    def _stand_at(self, trough: tuple[float, float]) -> tuple[float, float]:
        """Where he stands to drink from a trough: beside it, on his side."""
        tx, ty = trough
        off = 0.5 + self.hit_radius + 0.6
        sides = [(tx, ty - off), (tx, ty + off)]
        sides.sort(key=lambda p: math.hypot(p[0] - self.x, p[1] - self.y))
        for p in sides:
            if not self._solid(*p):
                return p
        return sides[0]

    def m_drink(self):
        """The signature: humps empty, he goes to the nearest whole trough
        and kneels to drink (the melee window: he takes DRINK[1] x damage),
        getting up full. If the trough breaks while he drinks, he chokes."""
        dur, _, walk, longest = config.DRINK
        tried: set = set()
        trough = None
        while True:
            left = [s for s in self.troughs() if s not in tried]
            if not left:
                break
            trough = min(left, key=lambda s: math.hypot(s[0] - self.x, s[1] - self.y))
            gx, gy = self._stand_at(trough)
            t0 = self.time
            arrived = False
            while self.time - t0 < longest:
                if trough not in self.troughs():
                    break                         # smashed on the way: another one
                if self._step_to(gx, gy, walk * self.speed_mult):
                    arrived = True
                    break
                yield 0
            if arrived:
                break
            tried.add(trough)
            trough = None
        if trough is None:
            left = self.troughs()
            if not left:
                return                            # (parched now: nothing to drink)
            trough = min(left, key=lambda s: math.hypot(s[0] - self.x, s[1] - self.y))
        self.facing = math.atan2(trough[1] - self.y, trough[0] - self.x)
        self.kneeling = True
        self.drinking_at = trough
        self.tell = ("drink",)
        self.ctx.effects.append(Effect("toast", self.x, self.y - 3, label="HE STOPS TO DRINK!"))
        start = self.water
        t0 = self.time
        while self.time - t0 < dur:
            f = (self.time - t0) / dur
            if trough not in self.troughs():
                self.kneeling = False
                self.drinking_at = None
                self.tell = None
                self.water = start + (config.HUMP_WATER - start) * f
                self.dazed = config.CHOKE_STUN
                self.ctx.effects.append(Effect("toast", self.x, self.y - 3,
                                               label="HE CHOKES! HIT HIM!"))
                self.ctx.effects.append(Effect("nova", self.x, self.y, size=3.0))
                self.ctx.events.append(combat.BREAK)
                yield config.CHOKE_STUN
                return
            self.water = start + (config.HUMP_WATER - start) * f
            yield 0
        self.water = float(config.HUMP_WATER)
        self.kneeling = False
        self.drinking_at = None
        self.tell = None
        yield 0.3

    def m_stampede(self):
        """P4 with bodies: a bellow (the tell), then rows of ghost camels
        charge across where the target stood, each row with a gap to stand
        in. In the last phase every other row comes from the side."""
        tell, rows, between, speed, half, spacing, gap, *_, back = config.SPITTER_STAMPEDE
        self.tell = ("bellow",)
        yield self.tell_s(tell)
        self.tell = None
        t = self.target_now()
        if t is None:
            return
        cx, cy = t.x, t.y
        heading = self.rng.choice((0.0, math.pi))
        cross = self.rng.choice((math.pi / 2, -math.pi / 2))
        for k in range(rows):
            h = heading if self.phase < 2 or k % 2 == 0 else cross
            vertical = abs(math.sin(h)) > 0.5
            dist = back * (0.5 if vertical else 1.0)   # (rows from above start on screen)
            width = half * (1.6 if vertical else 1.0)
            hx, hy = math.cos(h), math.sin(h)
            sx, sy = -hy, hx
            hole = self.rng.uniform(-width * 0.5, width * 0.5)
            s = -width
            while s <= width + 1e-9:
                if abs(s - hole) > gap / 2:
                    self.ghosts.append([cx - hx * dist + sx * s, cy - hy * dist + sy * s,
                                        hx * speed, hy * speed, 0.0, 2 * dist / speed, set()])
                s += spacing
            self.ctx.events.append("swing")
            yield between

    def m_mirage(self):
        """B7: he shimmers (the tell), and heat-haze doubles of him walk out
        of the air nearby; they spit like camels and pop at a touch."""
        tell, n, cap = config.SPITTER_MIRAGE
        self.tell = ("shimmer",)
        yield self.tell_s(tell)
        self.tell = None
        for _ in range(min(n, cap - self._decoys())):
            if self.recruit is None:
                break
            a = self.rng.uniform(0, math.tau)
            r = self.rng.uniform(5.0, 8.0)
            x, y = self.clamp_to_lair(self.x + math.cos(a) * r, self.y + math.sin(a) * r, 4.0)
            add = self.recruit("mirage", x, y)
            if add is not None:
                add.summoner = self
                add.alert = True
                self.ctx.effects.append(Effect("nova", x, y, size=2.0))
        self.ctx.events.append("orb")
        yield 0.3

    def m_spiral(self):
        """P2: he rears up (the tell) and spins, spraying spit in turning
        arms all round. Circle with it."""
        tell, dur, every, spin, arms = config.SPITTER_SPIRAL
        self.rear = True
        self.tell = ("rear",)
        yield self.tell_s(tell)
        self.tell = None
        self._spend("spiral")
        self.spinning = True
        turn = self.rng.uniform(0, math.tau)
        way = self.rng.choice((-1, 1))
        tt = 0.0
        while tt < dur:
            if self.room_for_shots():
                patterns.radial(self, self.x, self.y, arms, self.shots["spit"],
                                self.ctx.projectiles, turn)
            self.facing = turn
            turn += way * spin * every
            tt += every
            yield every
        self.spinning = False
        self.rear = False


# --- The Nameless Magus, Holder of Time (M23.3) ------------------------------------------


class Magus(Boss):
    """A robed sand wizard in his sunken observatory, one signature a phase,
    each kept as the next comes (the user's curve):

    1. SAND RUNES: he draws rune circles round his target (`runes`); each
       charges, then fires (a firestorm, a ring of blades, a sand golem). A
       hero standing in one a moment -- or rolling through it -- scuffs it
       out. Scuff a whole batch and he's DRAINED, kneeling (the melee
       window).
    2. SHIFTING DUNES (phase 2+): walls of sand rise near the target
       (`walls`: real tiles you can shoot through) with quicksand pits
       (`quicksand`); later they collapse, throwing sand.
    3. THE HOURGLASS (phase 3): he plants it (`glass`, an enemy you can hit);
       while its sand runs, time zones (`zones`) slow or speed everything
       inside -- heroes' walking, every shot, his adds -- but never him.
       Shatter it and he's stunned; if the sand runs out, TIME'S UP: rings
       of shots from the glass, and every rune on the field fires at once.

    Between them: the sun lance (an aim line, then a beam that sweeps the
    way you're going; columns and walls block it), sigils (homing glyphs
    that pop at a touch) with a blade fan, a blink (a shimmer marks where
    he'll be), the vortex (phase 2+: it pulls you in, spraying a spiral)
    and the sand serpent (a marked line through you, then it bursts along
    it)."""

    def __init__(self, spec: EnemySpec, x: float, y: float, rng: random.Random,
                 spawn_id=None) -> None:
        super().__init__(spec, x, y, rng, spawn_id, hit_radius=config.MAGUS_HIT_RADIUS)
        self.shots = config.MAGUS_SHOTS
        self.runes: list[dict] = []       # {x, y, kind, charge, scuff, batch}
        self.batches: dict[int, list] = {}   # batch -> [runes left, runes fired]
        self._batch = 0
        self.walls: list[dict] = []       # {tiles: [(tx, ty, was)], age}
        self.quicksand: list[list[float]] = []   # [x, y, age]
        self.glass = None                 # the hourglass (an enemy) while it stands
        self.glass_left = 0.0
        self.zones: list[tuple] = []      # (x, y, "slow" | "fast")
        self.beam: tuple | None = None    # the sun lance while it burns: (x0, y0, x1, y1)
        self.vortex: tuple | None = None  # (x, y) while it pulls
        self.serpent: tuple | None = None # (x0, y0, x1, y1, how far its head is)
        self.casting = False              # staff raised (drawing)
        self.drained = False              # kneeling, drained (drawing)
        self.pending: list[list] = []     # [when, callable]: things later in time
        self.sway = 0.0                   # robe sway (drawing)

    # --- Every step ---------------------------------------------------------------------

    def think(self, ctx: AIContext, dt: float) -> None:
        self.ctx = ctx
        self.dt = dt
        self.sway += dt
        due = [p for p in self.pending if p[0] <= self.time]
        self.pending = [p for p in self.pending if p[0] > self.time]
        for _, fn in due:
            fn()
        self._tick_runes(dt)
        self._tick_walls(dt)
        self._tick_glass(dt)
        self._tick_time(dt)
        if self.dazed > 0:                # drained or stunned: nothing else
            self.time += dt
            self.dazed = max(0.0, self.dazed - dt)
            if self.dazed <= 0:
                self.drained = False
            self._check_phase(ctx)
            return
        t = self.tgt if self.tgt is not None and self.tgt.alive else None
        if t is not None:
            self.facing = math.atan2(t.y - self.y, t.x - self.x)
        super().think(ctx, dt)

    def on_phase(self, phase: int, ctx: AIContext) -> None:
        label = ("THE DUNES ANSWER HIM!", "HE TURNS THE HOURGLASS...")[min(phase, 2) - 1] \
            if phase else ""
        if label:
            ctx.effects.append(Effect("toast", self.x, self.y - 3, label=label))

    def _abort_move(self) -> None:
        if self._gen is not None:
            self._gen.close()
        self.move = None
        self._gen = None
        self.tell = None
        self.beam = self.vortex = self.serpent = None
        self.casting = False
        self.combo = 0

    def _stun(self, seconds: float, label: str) -> None:
        self._abort_move()
        self.dazed = seconds
        self._rest = 0.5
        self.ctx.effects.append(Effect("toast", self.x, self.y - 3, label=label))
        self.ctx.effects.append(Effect("nova", self.x, self.y, size=3.0))
        self.ctx.events.append(combat.BREAK)

    def _end_move(self) -> None:
        super()._end_move()
        self.casting = False
        self.beam = self.vortex = self.serpent = None

    def _pick_move(self) -> str:
        skip = {self.last_move}
        if self.glass is not None:
            skip.add("hourglass")
        if self._brood("sigil") >= config.MAGUS_SIGILS[2]:
            skip.add("sigils")
        moves = [(m, w) for m, w in self.bspec.phases[self.phase].moves if m not in skip]
        if not moves:
            return "blink"
        total = sum(w for _, w in moves)
        r = self.rng.uniform(0, total)
        for m, w in moves:
            r -= w
            if r <= 0:
                return m
        return moves[-1][0]

    def _brood(self, key: str) -> int:
        return sum(1 for a in self.ctx.actors if getattr(a, "summoner", None) is self
                   and a.alive and getattr(a, "kind_key", "") == key)

    def _open(self, x: float, y: float, shrink: float = 3.0) -> bool:
        """Open floor inside the arena at (x, y)."""
        if self.lair is not None and not self.lair.inside(x, y, shrink):
            return False
        t = self.ctx.world.tile_at(math.floor(x), math.floor(y))
        return t is not None and not t.solid

    def _spot_near(self, x: float, y: float, lo: float, hi: float, shrink: float = 4.0,
                   avoid=(), gap: float = 0.0) -> tuple[float, float] | None:
        """A random open spot lo..hi tiles from (x, y), `gap` from `avoid`."""
        for _ in range(40):
            a = self.rng.uniform(0, math.tau)
            r = self.rng.uniform(lo, hi)
            px, py = x + math.cos(a) * r, y + math.sin(a) * r
            if self._open(px, py, shrink) and all(math.hypot(px - qx, py - qy) >= gap
                                                  for qx, qy in avoid):
                return px, py
        return None

    def _heroes_hit(self) -> list:
        return [h for h in self.ctx.players if h.hittable]

    # --- Runes --------------------------------------------------------------------------

    def _tick_runes(self, dt: float) -> None:
        """Runes charge; a hero in one a moment (or rolling through it)
        scuffs it out; a charged one fires. A batch scuffed out to the last
        rune drains him."""
        if not self.runes:
            return
        keep = []
        for r in self.runes:
            inside = [h for h in self.ctx.players if h.alive
                      and math.hypot(h.x - r["x"], h.y - r["y"]) <= config.RUNE_RADIUS]
            if inside:
                r["scuff"] += dt
                if any(h.rolling for h in inside) or r["scuff"] >= config.RUNE_SCUFF:
                    self._scuffed(r)
                    continue
            r["charge"] += dt
            if r["charge"] >= config.RUNE_CHARGE:
                self._fire_rune(r)
                continue
            keep.append(r)
        self.runes = keep

    def _scuffed(self, r: dict) -> None:
        self.ctx.effects.append(Effect("burrow", r["x"], r["y"]))
        self.ctx.effects.append(Effect("toast", r["x"], r["y"] - 1.5, label="SCUFFED!"))
        self.ctx.events.append("fizzle")
        b = self.batches.get(r["batch"])
        if b is None:
            return
        b[0] -= 1
        if b[0] <= 0:
            del self.batches[r["batch"]]
            if b[1] == 0:                 # every rune of it scuffed out: drained
                self.drained = True
                self._stun(config.RUNE_DRAIN, "HE'S DRAINED! HIT HIM!")

    def _fire_rune(self, r: dict) -> None:
        b = self.batches.get(r["batch"])
        if b is not None:
            b[0] -= 1
            b[1] += 1
            if b[0] <= 0:
                del self.batches[r["batch"]]
        x, y, kind = r["x"], r["y"], r["kind"]
        ctx = self.ctx
        if kind == "golem" and self.recruit is not None \
                and self._brood("sand_golem") < config.RUNE_GOLEMS:
            add = self.recruit("sand_golem", x, y)
            if add is not None:
                add.summoner = self
                add.alert = True
            ctx.effects.append(Effect("eruption", x, y))
            ctx.events.append("boulder")
            return
        if kind == "blades":
            n, rings, between = config.RUNE_BLADES
            turn = self.rng.uniform(0, math.tau)
            for k in range(rings):
                def ring(k=k):
                    patterns.radial(self, x, y, n, self.shots["blade"], self.ctx.projectiles,
                                    turn + k * math.pi / n)
                if k == 0:
                    ring()
                else:
                    self.pending.append([self.time + between * k, ring])
            ctx.effects.append(Effect("nova", x, y, size=config.RUNE_RADIUS))
            ctx.events.append("swing")
            return
        radius, damage, n = config.RUNE_FIRE
        combat.blast(x, y, radius, damage * self.damage_mult, self, self._heroes_hit(),
                     effects=ctx.effects)
        ctx.effects.append(Effect("explosion", x, y))
        ctx.effects.append(Effect("nova", x, y, size=radius))
        if self.room_for_shots():
            patterns.radial(self, x, y, n, self.shots["sand"], ctx.projectiles,
                            self.rng.uniform(0, math.tau))
        ctx.events.append("boulder")

    def m_runes(self):
        """The signature: staff raised (the tell), and a batch of runes
        appears round the target -- they charge while he does other things."""
        self.casting = True
        self.tell = ("cast",)
        yield self.tell_s(config.RUNE_DRAW)
        self.casting = False
        self.tell = None
        t = self.target_now()
        if t is None:
            return
        n = config.RUNE_BATCH[min(self.phase, len(config.RUNE_BATCH) - 1)]
        self._batch += 1
        placed = [(r["x"], r["y"]) for r in self.runes]
        made = 0
        for _ in range(n):
            spot = self._spot_near(t.x, t.y, *config.RUNE_RANGE, avoid=placed,
                                   gap=config.RUNE_GAP)
            if spot is None:
                continue
            placed.append(spot)
            kind = self.rng.choices(("fire", "blades", "golem"), (0.45, 0.35, 0.2))[0]
            self.runes.append(dict(x=spot[0], y=spot[1], kind=kind, charge=0.0, scuff=0.0,
                                   batch=self._batch))
            self.ctx.effects.append(Effect("nova", spot[0], spot[1], size=config.RUNE_RADIUS))
            made += 1
        if made:
            self.batches[self._batch] = [made, 0]
        self.ctx.events.append("hex")
        yield 0.3

    # --- Dunes and quicksand ------------------------------------------------------------

    def _tick_walls(self, dt: float) -> None:
        for w in self.walls:
            w["age"] += dt
        for w in [w for w in self.walls if w["age"] >= config.DUNE_LIFE]:
            self._collapse(w)
        for q in self.quicksand:
            q[2] += dt
        self.quicksand = [q for q in self.quicksand if q[2] < config.DUNE_LIFE]

    def _collapse(self, w: dict) -> None:
        """A wall falls: sand thrown out both ways along it, the floor back."""
        from ..world import tiles
        world = self.ctx.world
        line = w["line"]
        for k, (x, y, nx, ny) in enumerate(line):
            if k % 3 == 1 and self.room_for_shots():
                for side in (-1, 1):
                    patterns.shoot(self, x + nx * side * 1.5, y + ny * side * 1.5,
                                   math.atan2(ny * side, nx * side), self.shots["sand"],
                                   self.ctx.projectiles)
        hp = getattr(world, "_hp", None)
        for tx, ty, was in w["tiles"]:
            if world.tile_at(tx, ty) is tiles.DUNE_WALL and hasattr(world, "set_tile"):
                world.set_tile(tx, ty, was)
            if hp is not None:
                hp.pop((tx, ty), None)
        self.ctx.effects.append(Effect("debris", *line[len(line) // 2][:2]))
        self.walls.remove(w)

    def _wall_line(self, t) -> list[tuple[float, float, float, float]]:
        """A wall's middle line (x, y, normal x, normal y), across the way
        from the target to its middle, DUNE_LEN tiles long."""
        spot = self._spot_near(t.x, t.y, *config.DUNE_RANGE)
        if spot is None:
            return []
        cx, cy = spot
        to = math.atan2(cy - t.y, cx - t.x)
        nx, ny = math.cos(to), math.sin(to)          # the wall's normal: facing the target
        ax, ay = -ny, nx                             # along the wall
        n = self.rng.randint(*config.DUNE_LEN)
        return [(cx + ax * (k - n / 2), cy + ay * (k - n / 2), nx, ny) for k in range(n)]

    def m_dunes(self):
        """Signature 2: the sand ripples along lines (the tell), and walls
        of sand rise there, with quicksand pits near the target. The walls
        he raised before collapse first."""
        from ..world import tiles
        for w in list(self.walls):
            self._collapse(w)
        t = self.target_now()
        if t is None:
            return
        lines = [ln for ln in (self._wall_line(t) for _ in range(self.rng.randint(*config.DUNE_WALLS)))
                 if ln]
        self.casting = True
        self.tell = ("dunes", lines)
        yield self.tell_s(config.DUNE_TELL)
        self.casting = False
        self.tell = None
        world = self.ctx.world
        bodies = [a for a in self.ctx.actors if a.alive]
        gate = set(self.lair.gate) if self.lair is not None else set()
        for line in lines:
            done: dict = {}
            for x, y, nx, ny in line:
                for off in (0.0, 1.0):
                    tx, ty = math.floor(x + nx * off), math.floor(y + ny * off)
                    if (tx, ty) in done or (tx, ty) in gate:
                        continue
                    if not self._open(tx + 0.5, ty + 0.5, 2.0):
                        continue
                    if any(math.hypot(b.x - tx - 0.5, b.y - ty - 0.5) < b.hit_radius + 1.2
                           for b in bodies):
                        continue
                    was = world.tile_at(tx, ty)
                    if hasattr(world, "set_tile"):
                        world.set_tile(tx, ty, tiles.DUNE_WALL)
                        done[(tx, ty)] = was
            if done:
                self.walls.append(dict(tiles=[(tx, ty, was) for (tx, ty), was in done.items()],
                                       line=line, age=0.0))
                mx, my = line[len(line) // 2][:2]
                self.ctx.effects.append(Effect("eruption", mx, my))
        for _ in range(config.DUNE_PITS):
            spot = self._spot_near(t.x, t.y, 4.0, 10.0)
            if spot is not None:
                self.quicksand.append([spot[0], spot[1], 0.0])
        self.ctx.events.append("boulder")
        yield 0.3

    # --- The hourglass and time ---------------------------------------------------------

    def _tick_glass(self, dt: float) -> None:
        g = self.glass
        if g is None:
            return
        if not g.alive:                   # shattered
            self.glass = None
            self.zones = []
            self._stun(config.HOURGLASS[2], "TIME STANDS STILL! HIT HIM!")
            return
        self.glass_left -= dt
        g.sand = max(0.0, self.glass_left / config.HOURGLASS[0])
        if self.glass_left <= 0:
            self._times_up()

    def _times_up(self) -> None:
        """The sand ran out: rings of shots from the glass (each with a
        gap), and every rune on the field fires at once."""
        g = self.glass
        gx, gy = g.x, g.y
        self.glass = None
        self.zones = []
        g.hp = 0.0                        # (it crumbles: nobody's kill)
        g.last_hit_by = None
        g.expired = True
        n, gap, between = config.TIMES_UP_RING
        self.ctx.effects.append(Effect("toast", gx, gy - 3, label="TIME'S UP!"))
        self.ctx.events.append(combat.BREAK)
        for k in range(config.HOURGLASS[3]):
            gap_at = self.rng.uniform(0, math.tau)

            def ring(gap_at=gap_at, k=k):
                half = math.radians(gap) / 2
                for i in range(n):
                    a = k * 0.2 + i * math.tau / n
                    if abs((a - gap_at + math.pi) % math.tau - math.pi) < half:
                        continue
                    patterns.shoot(self, gx, gy, a, self.shots["time"], self.ctx.projectiles)
            self.pending.append([self.time + between * k, ring])
        for r in list(self.runes):
            self._fire_rune(r)
        self.runes = []

    def _zone_at(self, x: float, y: float) -> str | None:
        for zx, zy, kind in self.zones:
            if math.hypot(x - zx, y - zy) <= config.TIME_ZONE_RADIUS:
                return kind
        return None

    def _tick_time(self, dt: float) -> None:
        """Time zones and quicksand: how fast each hero walks, each shot
        flies and each of his adds acts (never him), and quicksand's drag."""
        ctx = self.ctx
        zoned = bool(self.zones)
        for h in ctx.players:
            if not self.in_arena(h):
                continue
            m = 1.0
            if zoned:
                kind = self._zone_at(h.x, h.y)
                m = config.TIME_SLOW if kind == "slow" else \
                    config.TIME_FAST_HERO if kind == "fast" else 1.0
            if h.alive and not h.rolling:
                for qx, qy, _ in self.quicksand:
                    d = math.hypot(h.x - qx, h.y - qy)
                    if d <= config.QUICKSAND[0] + h.hit_radius:
                        m *= config.QUICKSAND[1]
                        if d > 0.3:
                            pull = min(d, config.QUICKSAND[2] * dt)
                            combat.push(h, ctx.world, (qx - h.x) / d * pull, (qy - h.y) / d * pull)
                        break
            h.time_mult = m
        for p in ctx.projectiles:
            kind = self._zone_at(p.x, p.y) if zoned else None
            p.time_scale = config.TIME_SLOW if kind == "slow" else \
                config.TIME_FAST if kind == "fast" else 1.0
        for a in ctx.actors:
            if a is self or getattr(a, "faction", "") == "player":
                continue
            kind = self._zone_at(a.x, a.y) if zoned else None
            if kind is not None or getattr(a, "time_mult", 1.0) != 1.0:
                a.time_mult = config.TIME_SLOW if kind == "slow" else \
                    config.TIME_FAST if kind == "fast" else 1.0

    def m_hourglass(self):
        """Signature 3: staff raised (the tell), and he plants the hourglass
        near the target; time zones open round it."""
        self.casting = True
        self.tell = ("cast",)
        yield self.tell_s(0.8)
        self.casting = False
        self.tell = None
        t = self.target_now()
        if t is None or self.recruit is None:
            return
        # Beside the target rather than above or below it (the screen is far
        # wider than it is tall: it must be in sight).
        d = config.HOURGLASS[1]
        spot = None
        for _ in range(40):
            a = self.rng.choice((0.0, math.pi)) + self.rng.uniform(-0.45, 0.45)
            r = self.rng.uniform(d * 0.7, d * 1.2)
            x, y = t.x + math.cos(a) * r, t.y + math.sin(a) * r
            if self._open(x, y, 6.0):
                spot = (x, y)
                break
        if spot is None:
            return
        g = self.recruit("hourglass", *spot)
        if g is None:
            return
        g.summoner = self
        self.glass = g
        self.glass_left = config.HOURGLASS[0]
        self.ctx.effects.append(Effect("explosion", *spot))
        self.zones = []
        n = self.rng.randint(*config.TIME_ZONES)
        placed: list = []
        for k in range(n):
            z = self._spot_near(t.x, t.y, 4.0, 18.0, shrink=4.0, avoid=placed,
                                gap=config.TIME_ZONE_RADIUS * 2.2)
            if z is None:
                continue
            placed.append(z)
            kind = ("slow", "fast")[k % 2] if k < 2 else self.rng.choice(("slow", "fast"))
            self.zones.append((z[0], z[1], kind))
        self.ctx.events.append("chime")
        yield 0.3

    def on_death(self, ctx: AIContext) -> None:
        self.ctx = ctx
        for w in list(self.walls):
            self._collapse(w)
        self.runes = []
        self.zones = []
        self.quicksand = []
        if self.glass is not None and self.glass.alive:
            self.glass.hp = 0.0
            self.glass.last_hit_by = None
        for h in ctx.players:
            h.time_mult = 1.0
        for p in ctx.projectiles:
            p.time_scale = 1.0
        for a in ctx.actors:
            if hasattr(a, "time_mult") and getattr(a, "faction", "") != "player":
                a.time_mult = 1.0
        super().on_death(ctx)

    # --- Supporting moves ---------------------------------------------------------------

    @property
    def staff(self) -> tuple[float, float]:
        """The lens at the top of his staff (where beams and bolts start)."""
        return self.x + math.cos(self.facing) * 1.4, self.y + math.sin(self.facing) * 1.4

    def _ray(self, x0: float, y0: float, a: float, longest: float) -> tuple[float, float]:
        """Where a beam from (x0, y0) along `a` stops: the first tile that
        blocks shots, the arena's edge, or `longest` tiles."""
        world = self.ctx.world
        d = 0.0
        x, y = x0, y0
        while d < longest:
            nx, ny = x0 + math.cos(a) * (d + 0.4), y0 + math.sin(a) * (d + 0.4)
            if self.lair is not None and not self.lair.inside(nx, ny):
                break
            tile = world.tile_at(math.floor(nx), math.floor(ny))
            if tile is not None and tile.blocks_shots:
                break
            x, y = nx, ny
            d += 0.4
        return x, y

    def m_lance(self):
        """P7: the sun lance. An aim line (the tell), then a beam that burns
        for a moment, sweeping the way the target was going; walls and
        columns block it. It hits each hero once."""
        tell, burn, sweep, longest, damage, half = config.MAGUS_LANCE
        t = self.target_now()
        if t is None:
            return
        x0, y0 = self.staff
        a0 = math.atan2(t.y - y0, t.x - x0)
        side = math.sin(math.atan2(getattr(t, "vy", 0.0), getattr(t, "vx", 0.0)) - a0)
        way = 1.0 if side > 0.1 else -1.0 if side < -0.1 else self.rng.choice((-1.0, 1.0))
        a0 -= way * math.radians(sweep) * 0.25          # (it starts a little behind you)
        wait = self.tell_s(tell)
        self.casting = True
        self.tell = ("lance", x0, y0, *self._ray(x0, y0, a0, longest))
        yield wait
        self.tell = None
        hit = set()
        t0 = self.time
        self.ctx.events.append("hex")
        while self.time - t0 < burn:
            f = (self.time - t0) / burn
            a = a0 + way * math.radians(sweep) * f
            x1, y1 = self._ray(x0, y0, a, longest)
            self.beam = (x0, y0, x1, y1)
            self.facing = a
            for h in self._heroes_hit():
                if id(h) in hit:
                    continue
                if patterns.point_segment_distance(h.x, h.y, x0, y0, x1, y1) <= half + h.hit_radius:
                    hit.add(id(h))
                    combat.strike(h, damage * self.damage_mult, self, a, self.ctx.effects)
            yield 0
        self.beam = None
        self.casting = False

    def m_sigils(self):
        """P6 + P3: sigils drift out round him (slow homing glyphs that pop
        at a touch), and a fan of spinning blades at the target."""
        tell, n, cap, blades, spread = config.MAGUS_SIGILS
        self.casting = True
        self.tell = ("cast",)
        yield self.tell_s(tell)
        self.casting = False
        self.tell = None
        for k in range(min(n, cap - self._brood("sigil"))):
            if self.recruit is None:
                break
            a = self.facing + (k - (n - 1) / 2) * 0.7
            add = self.recruit("sigil", self.x + math.cos(a) * 2.0, self.y + math.sin(a) * 2.0)
            if add is not None:
                add.summoner = self
                add.facing = a
        t = self.target_now()
        if t is not None and self.room_for_shots():
            x0, y0 = self.staff
            shell = self.shots["blade"]
            patterns.fan(self, x0, y0, self.aim(t, x0, y0, shell.speed), blades, spread, shell,
                         self.ctx.projectiles)
        self.ctx.events.append("orb")
        yield 0.3

    def m_blink(self):
        """B7: a shimmer where he's going (the tell), then he's there, in a
        puff of sand."""
        tell, lo, hi, n = config.MAGUS_BLINK
        t = self.target_now()
        ref = t if t is not None else self
        spot = None
        for _ in range(3):
            spot = self._spot_near(self.x, self.y, lo, hi, shrink=6.0)
            if spot is not None and math.hypot(spot[0] - ref.x, spot[1] - ref.y) >= 7.0:
                break
        if spot is None:
            return
        self.tell = ("blink", *spot)
        yield self.tell_s(tell)
        self.tell = None
        self.ctx.effects.append(Effect("burrow", self.x, self.y))
        self.x, self.y = spot
        self.ctx.effects.append(Effect("eruption", self.x, self.y))
        if self.room_for_shots():
            patterns.radial(self, self.x, self.y, n, self.shots["sand"], self.ctx.projectiles,
                            self.rng.uniform(0, math.tau))
        self.ctx.events.append("fizzle")
        yield 0.2

    def m_vortex(self):
        """B8 + P2 (phase 2+): a whirl marked near the target (the tell),
        then a sandstorm vortex there pulls heroes in (a roll breaks free
        for its length) while spraying a spiral."""
        tell, dur, radius, pull, every, spin = config.MAGUS_VORTEX
        t = self.target_now()
        if t is None:
            return
        spot = self._spot_near(t.x, t.y, 6.0, 9.0) or (t.x + 7.0, t.y)
        self.casting = True
        self.tell = ("vortex", *spot)
        yield self.tell_s(tell)
        self.tell = None
        self.vortex = spot
        vx, vy = spot
        turn = self.rng.uniform(0, math.tau)
        way = self.rng.choice((-1, 1))
        t0 = self.time
        next_shot = 0.0
        while self.time - t0 < dur:
            for h in self.ctx.players:
                if not h.alive or h.rolling:
                    continue
                d = math.hypot(h.x - vx, h.y - vy)
                if 0.5 < d <= radius:
                    step = min(d - 0.5, pull * self.dt)
                    combat.push(h, self.ctx.world, (vx - h.x) / d * step, (vy - h.y) / d * step)
            el = self.time - t0
            if el >= next_shot:
                next_shot += every
                if self.room_for_shots():
                    patterns.radial(self, vx, vy, 2, self.shots["sand"], self.ctx.projectiles,
                                    turn + way * spin * el)
            yield 0
        self.vortex = None
        self.casting = False

    def m_serpent(self):
        """P7-like: a line marked through the target from the arena's edge
        side (the tell), then a sand serpent bursts out along it, hitting
        whoever's on it once."""
        tell, speed, half, damage, length = config.MAGUS_SERPENT
        t = self.target_now()
        if t is None:
            return
        a = self.rng.uniform(0, math.tau)
        x0, y0 = t.x - math.cos(a) * length / 2, t.y - math.sin(a) * length / 2
        x0, y0 = self.clamp_to_lair(x0, y0, 3.0)
        x1, y1 = self.clamp_to_lair(t.x + math.cos(a) * length / 2,
                                    t.y + math.sin(a) * length / 2, 3.0)
        self.casting = True
        self.tell = ("serpent", x0, y0, x1, y1)
        yield self.tell_s(tell)
        self.tell = None
        self.casting = False
        total = math.hypot(x1 - x0, y1 - y0) or 1.0
        gone = 0.0
        hit = set()
        self.ctx.events.append("boulder")
        while gone < total:
            gone = min(total, gone + speed * self.dt)
            f = gone / total
            hx, hy = x0 + (x1 - x0) * f, y0 + (y1 - y0) * f
            self.serpent = (x0, y0, x1, y1, gone)
            for h in self._heroes_hit():
                if id(h) not in hit and math.hypot(h.x - hx, h.y - hy) <= half + h.hit_radius:
                    hit.add(id(h))
                    combat.strike(h, damage * self.damage_mult, self, a, self.ctx.effects)
            if int(gone) % 3 == 0:
                self.ctx.effects.append(Effect("burrow", hx, hy))
            yield 0
        self.serpent = None
        yield 0.2



# --- The Fallout King (M24.1) ------------------------------------------------------------


class FalloutKing(Boss):
    """A hulking irradiated monster in his reactor vault, one signature a
    phase, each kept:

    1. RADS: every hero's meter (Character.rads) fills near his glow, from
       his hits, in goo and in fallout. Full, you're IRRADIATED (a burn, no
       regen, a slow roll recharge) until it runs out. A decontamination
       shower (the lair's props["showers"]) wipes it, then is dry a while.
    2. FALLOUT (phase 2+): his stomp throws patches of fallout round the
       target (`patches`), growing, burning, adding rads -- each with an
       isotope rod in the middle: smash the rod, clear the patch.
    3. THE MELTDOWN CORE (phase 3): `heat` climbs to 100. Shut all four
       coolant valves (props["valves"]) and his core is EXPOSED (it takes
       CORE_EXPOSED[1] x damage); let it reach 100 and it's MELTDOWN after a
       countdown -- everyone in the vault not behind a lead wall is hit.

    Between them: the gamma cross (four turning beams; pillars block them),
    toxic barrels (they can't be stopped in the air: they leave goo that slows you),
    a ghoul horde, an EMP ring with a gap, homing skulls, and grate dives
    (into one sewer grate, out of the one nearest you)."""

    def __init__(self, spec: EnemySpec, x: float, y: float, rng: random.Random,
                 spawn_id=None) -> None:
        super().__init__(spec, x, y, rng, spawn_id, hit_radius=config.KING_HIT_RADIUS)
        self.shots = config.KING_SHOTS
        self.patches: list[dict] = []     # {x, y, age, rod}
        self.goo: list[list[float]] = []  # [x, y, age]
        self.barrels: list = []           # toxic barrels in the air
        self.beams: list[tuple] = []      # the gamma cross while it burns: (x0, y0, x1, y1)
        self.heat = 0.0                   # the core (phase 3)
        self.exposed = 0.0                # s left with the core exposed
        self.meltdown = 0.0               # > 0: the countdown
        self.shut: set[int] = set()       # valves shut this cycle
        self.valve_t: dict[int, float] = {}
        self.dry: dict[int, float] = {}   # shower -> s until it runs again
        self.under: dict = {}             # (hero id, shower) -> s under it
        self.burn_t: dict[int, float] = {}
        self._fallout_tick = 0.0
        self.rising = None                # grate dive: the grate he'll burst from
        self.pulse = 0.0                  # his glow (drawing)
        self.wave: list | None = None     # a meltdown's wave: [x, y, radius, reach, heroes hit]

    # --- Helpers ------------------------------------------------------------------------

    @property
    def props(self) -> dict:
        return self.lair.props if self.lair is not None else {}

    @property
    def bar_label(self) -> str:
        """The boss bar's label (the HUD): the core's state from phase 3, so
        a meltdown warning reaches everyone wherever he is."""
        if self.phase < 2:
            return self.espec.name
        if self.meltdown > 0:
            return f"MELTDOWN IN {math.ceil(self.meltdown)} - HIDE BEHIND LEAD!"
        if self.exposed > 0:
            return "CORE EXPOSED - HIT HIM NOW!"
        valves = len(self.props.get("valves", []))
        return f"CORE {round(self.heat)}% - SHUT THE VALVES {len(self.shut)}/{valves}"

    def map_marks(self) -> list[tuple[float, float, str, str]]:
        """His vault's fixtures as map pins during the fight (systems/quests
        .pins): the showers (dry ones grey), and from phase 3 the valves
        still open, the lead walls while the meltdown counts down, and him
        while his core is exposed."""
        out = []
        for i, (x, y) in enumerate(self.props.get("showers", [])):
            dry = self.dry.get(i, 0.0) > 0
            out.append((x, y, "dry" if dry else "shower", "DRY" if dry else "SHOWER"))
        if self.phase >= 2:
            if self.meltdown > 0:
                out += [(x, y, "lead", "LEAD") for x, y in self.props.get("leads", [])]
            elif self.exposed > 0:
                out.append((self.x, self.y, "core", "CORE!"))
            else:
                out += [(x, y, "valve", "VALVE")
                        for i, (x, y) in enumerate(self.props.get("valves", []))
                        if i not in self.shut]
        return out

    def take_damage(self, amount, source, from_angle):
        if self.exposed > 0:
            amount *= config.CORE_EXPOSED[1]
        return super().take_damage(amount, source, from_angle)

    def _hit(self, h, damage: float, angle) -> float:
        """One of his hits: damage, and rads with it."""
        dealt = combat.strike(h, damage * self.damage_mult, self, angle, self.ctx.effects)
        if dealt:
            h.rads = min(config.RADS_FULL, h.rads + config.RADS_HIT)
        return dealt or 0.0

    def on_shot_hit(self, victim, dealt: float) -> None:
        if getattr(victim, "faction", "") == "player":
            victim.rads = min(config.RADS_FULL, victim.rads + config.RADS_HIT)

    def _patch_radius(self, p: dict) -> float:
        r0, r1 = config.FALLOUT_RADIUS
        return r0 + (r1 - r0) * min(1.0, p["age"] / config.FALLOUT_GROW)

    def _set(self, x: float, y: float, tile) -> None:
        world = self.ctx.world
        if hasattr(world, "set_tile"):
            world.set_tile(math.floor(x), math.floor(y), tile)

    # --- Every step ---------------------------------------------------------------------

    def think(self, ctx: AIContext, dt: float) -> None:
        self.ctx = ctx
        self.pulse += dt
        self._tick_barrels()
        self._tick_ground(dt)
        self._tick_rads(dt)
        self._tick_showers(dt)
        self._tick_core(dt)
        self._tick_wave(dt)
        t = self.tgt if self.tgt is not None and self.tgt.alive else None
        if t is not None and not self.submerged and not self.beams:
            self.facing = math.atan2(t.y - self.y, t.x - self.x)
        super().think(ctx, dt)

    def on_phase(self, phase: int, ctx: AIContext) -> None:
        label = ("FALLOUT RAINS DOWN!", "HIS CORE IS GOING CRITICAL!")[min(phase, 2) - 1] \
            if phase else ""
        if label:
            ctx.effects.append(Effect("toast", self.x, self.y - 3, label=label))

    def _end_move(self) -> None:
        super()._end_move()
        self.beams = []

    def _tick_barrels(self) -> None:
        """A barrel that landed leaves a goo puddle (one cleared away
        without landing -- his death -- just bursts)."""
        if not self.barrels:
            return
        still = []
        for b in self.barrels:
            if b.alive:
                still.append(b)
            elif getattr(b, "landed", False):
                self.goo.append([b.target[0], b.target[1], 0.0])
                self.ctx.effects.append(Effect("nova", *b.target, size=config.KING_BARRELS[4]))
                self.ctx.events.append("fizzle")
            else:
                self.ctx.effects.append(Effect("impact", b.x, b.y))
        self.barrels = still

    def _tick_ground(self, dt: float) -> None:
        """Goo and fallout age; a patch whose rod is smashed clears; heroes
        in fallout burn."""
        for g in self.goo:
            g[2] += dt
        self.goo = [g for g in self.goo if g[2] < config.KING_BARRELS[5]]
        keep = []
        for p in self.patches:
            p["age"] += dt
            rod = p["rod"]
            if (rod is not None and not rod.alive) or (rod is None and p["age"] > 20.0):
                self.ctx.effects.append(Effect("nova", p["x"], p["y"], size=self._patch_radius(p)))
                if rod is not None:
                    self.ctx.effects.append(Effect("toast", p["x"], p["y"] - 2,
                                                   label="FALLOUT CLEARED!"))
                continue
            keep.append(p)
        self.patches = keep
        self._fallout_tick -= dt
        if self._fallout_tick <= 0 and self.patches:
            self._fallout_tick += 0.5
            for h in self.ctx.players:
                if h.hittable and self.in_arena(h) and self._in_fallout(h):
                    combat.strike(h, config.FALLOUT_BURN * 0.5 * self.damage_mult, self, None,
                                  self.ctx.effects)

    def _in_fallout(self, h) -> bool:
        return any(math.hypot(h.x - p["x"], h.y - p["y"]) <= self._patch_radius(p)
                   for p in self.patches)

    def _in_goo(self, h) -> bool:
        r = config.KING_BARRELS[4]
        return any(math.hypot(h.x - g[0], h.y - g[1]) <= r for g in self.goo)

    def _tick_rads(self, dt: float) -> None:
        """Each hero's rads, the goo's slow, and being irradiated."""
        for h in self.ctx.players:
            if not self.in_arena(h):
                continue
            if not h.alive:
                h.time_mult = 1.0
                continue
            gain = 0.0
            if not self.submerged and math.hypot(h.x - self.x, h.y - self.y) <= \
                    config.RADS_GLOW_RANGE + self.hit_radius:
                gain += config.RADS_GLOW
            goo = self._in_goo(h)
            if goo:
                gain += config.RADS_GOO
            if self._in_fallout(h):
                gain += config.RADS_FALLOUT
            h.time_mult = config.KING_BARRELS[6] if goo and not h.rolling else 1.0
            if h.irradiated > 0:
                h.irradiated -= dt
                t = self.burn_t.get(id(h), 0.0) - dt
                if t <= 0:
                    t += config.IRRADIATED[2]
                    combat.strike(h, config.IRRADIATED[1] * self.damage_mult, self, None,
                                  self.ctx.effects)
                self.burn_t[id(h)] = t
                if h.irradiated <= 0:
                    h.irradiated = 0.0
                    h.rads = config.IRRADIATED[4]
                continue
            full = h.rads >= config.RADS_FULL     # (a hit can fill it between steps)
            h.rads = max(0.0, min(config.RADS_FULL, h.rads + gain * dt if gain
                                  else h.rads - config.RADS_DRAIN * dt))
            if full or h.rads >= config.RADS_FULL:
                h.rads = config.RADS_FULL
                h.irradiated = config.IRRADIATED[0]
                self.burn_t[id(h)] = 0.0
                self.ctx.effects.append(Effect("toast", h.x, h.y - 2,
                                               label="IRRADIATED! FIND A SHOWER!"))
                self.ctx.events.append("hex")

    def _tick_showers(self, dt: float) -> None:
        """A hero under a running shower long enough is clean; that shower
        then runs dry a while."""
        from ..world import tiles
        showers = self.props.get("showers", [])
        for i, (sx, sy) in enumerate(showers):
            if self.dry.get(i, 0.0) > 0:
                self.dry[i] -= dt
                if self.dry[i] <= 0:
                    self._shower_tiles(sx, sy, tiles.SHOWER)
                continue
            for h in self.ctx.players:
                key = (id(h), i)
                if not h.alive or math.hypot(h.x - sx, h.y - sy) > config.SHOWER[2] \
                        or (h.rads <= 0 and h.irradiated <= 0):
                    self.under.pop(key, None)
                    continue
                self.under[key] = self.under.get(key, 0.0) + dt
                if self.under[key] >= config.SHOWER[0]:
                    h.rads = 0.0
                    h.irradiated = 0.0
                    self.under.pop(key, None)
                    self.dry[i] = config.SHOWER[1]
                    self._shower_tiles(sx, sy, tiles.SHOWER_OFF)
                    self.ctx.effects.append(Effect("toast", h.x, h.y - 2, label="DECONTAMINATED!"))
                    self.ctx.events.append("chime")
                    break

    def _shower_tiles(self, sx: float, sy: float, tile) -> None:
        for dx in (-1, 0):
            for dy in (-1, 0):
                self._set(sx + dx + 0.5, sy + dy + 0.5, tile)

    def _tick_core(self, dt: float) -> None:
        """Phase 3: the core heats; four shut valves expose it; at 100, the
        meltdown countdown, then the blast (lead walls shield)."""
        from ..world import tiles
        if self.exposed > 0:
            self.exposed -= dt
            if self.exposed <= 0:
                self.exposed = 0.0
                for i in self.shut:
                    self._set(*self.props["valves"][i], tiles.VALVE)
                self.shut = set()
            return
        if self.phase < 2:
            return
        if self.meltdown > 0:
            self.meltdown -= dt
            if self.meltdown <= 0:
                self._melt()
            return
        valves = self.props.get("valves", [])
        for i, (vx, vy) in enumerate(valves):
            if i in self.shut:
                continue
            if any(h.alive and math.hypot(h.x - vx, h.y - vy) <= config.VALVE_REACH
                   for h in self.ctx.players):
                self.valve_t[i] = self.valve_t.get(i, 0.0) + dt
                if self.valve_t[i] >= config.VALVE_TIME:
                    self.shut.add(i)
                    self.valve_t.pop(i, None)
                    self._set(vx, vy, tiles.VALVE_SHUT)
                    self.ctx.effects.append(Effect("toast", vx, vy - 2,
                                                   label=f"VALVE SHUT {len(self.shut)}/4"))
                    self.ctx.events.append("chime")
            else:
                self.valve_t.pop(i, None)
        if valves and len(self.shut) >= len(valves):
            self.exposed = config.CORE_EXPOSED[0]
            self.heat = 0.0
            self.ctx.effects.append(Effect("toast", self.x, self.y - 4,
                                           label="CORE EXPOSED! HIT IT!"))
            self.ctx.effects.append(Effect("explosion", self.x, self.y))
            self.ctx.events.append(combat.BREAK)
            return
        self.heat = min(100.0, self.heat + 100.0 / config.CORE_HEAT * dt)
        if self.heat >= 100.0:
            self.meltdown = config.MELTDOWN[0]       # (the boss bar counts it down)
            self.ctx.events.append("hex")

    def shielded(self, h) -> bool:
        """Is a lead wall between him and hero h?"""
        from ..systems.raycast import first_hit
        from ..world import tiles
        hit = first_hit(self.ctx.world.tile_at, self.x, self.y, h.x, h.y)
        return hit is not None and self.ctx.world.tile_at(hit.tx, hit.ty) is tiles.LEAD

    def _melt(self) -> None:
        """MELTDOWN: a wave races out across the vault from where he stands
        (_tick_wave); it hits every hero it reaches who isn't behind lead."""
        self.heat = 0.0
        self.meltdown = 0.0
        reach = max(self.lair.radii) * 2 if self.lair is not None else 80.0
        self.wave = [self.x, self.y, 0.0, reach, set()]
        for k in range(10):
            a = k * math.tau / 10
            self.ctx.effects.append(Effect("explosion", self.x + math.cos(a) * 4,
                                           self.y + math.sin(a) * 2.5))
        # The wave, drawn (render/fallout.draw_meltdown) at the same speed.
        self.ctx.effects.append(Effect("meltdown", self.x, self.y, size=reach))
        self.ctx.effects.append(Effect("nova", self.x, self.y, size=12.0))
        self.ctx.effects.append(Effect("toast", self.x, self.y - 4, label="MELTDOWN!"))
        self.ctx.events.append(combat.BREAK)

    def _tick_wave(self, dt: float) -> None:
        """The meltdown's wave spreads at MELTDOWN_SPEED; a hero is hit when
        it reaches them -- unless, just then, a lead wall stands between them
        and where it started."""
        if self.wave is None:
            return
        from ..systems.raycast import first_hit
        from ..world import tiles
        wx, wy, r, reach, hit = self.wave
        r += config.MELTDOWN_SPEED * dt
        self.wave[2] = r
        _, damage, rads = config.MELTDOWN
        world = self.ctx.world
        for h in self.ctx.players:
            if id(h) in hit or not self.in_arena(h) or math.hypot(h.x - wx, h.y - wy) > r:
                continue
            hit.add(id(h))
            block = first_hit(world.tile_at, wx, wy, h.x, h.y)
            if block is not None and world.tile_at(block.tx, block.ty) is tiles.LEAD:
                self.ctx.effects.append(Effect("toast", h.x, h.y - 2, label="SHIELDED!"))
                continue
            if h.hittable:
                combat.strike(h, damage * self.damage_mult, self, None, self.ctx.effects)
                h.rads = min(config.RADS_FULL, h.rads + rads)
                self.ctx.effects.append(Effect("explosion", h.x, h.y))
        if r >= reach:
            self.wave = None

    def on_death(self, ctx: AIContext) -> None:
        from ..world import tiles
        self.ctx = ctx
        self.wave = None
        for h in ctx.players:
            if self.in_arena(h):
                h.rads = 0.0
                h.irradiated = 0.0
                h.time_mult = 1.0
        for p in self.patches:
            if p["rod"] is not None and p["rod"].alive:
                p["rod"].hp = 0.0
                p["rod"].last_hit_by = None
        for b in self.barrels:
            b.hp = 0.0
            b.last_hit_by = None
        self.patches, self.goo, self.barrels = [], [], []
        for i in list(self.shut):
            self._set(*self.props["valves"][i], tiles.VALVE)
        for i, (sx, sy) in enumerate(self.props.get("showers", [])):
            if self.dry.get(i, 0.0) > 0:
                self._shower_tiles(sx, sy, tiles.SHOWER)
        super().on_death(ctx)

    # --- Moves --------------------------------------------------------------------------

    def _ray(self, x0: float, y0: float, a: float, longest: float) -> tuple[float, float]:
        world = self.ctx.world
        d = 0.0
        x, y = x0, y0
        while d < longest:
            nx, ny = x0 + math.cos(a) * (d + 0.4), y0 + math.sin(a) * (d + 0.4)
            if self.lair is not None and not self.lair.inside(nx, ny):
                break
            tile = world.tile_at(math.floor(nx), math.floor(ny))
            if tile is not None and tile.blocks_shots:
                break
            x, y = nx, ny
            d += 0.4
        return x, y

    def m_gamma(self):
        """A gamma cross: four aim lines from him (the tell), then four beams
        turning slowly (in phase 3, one way then back), burning whoever's
        on them every tick; pillars and walls stop them."""
        tell, burn, turn, longest, damage, tick, half = config.KING_GAMMA
        t = self.target_now()
        a0 = math.atan2(t.y - self.y, t.x - self.x) + math.pi / 4 if t is not None else 0.0
        way = self.rng.choice((-1, 1))

        def lines(a):
            return [(self.x, self.y, *self._ray(self.x, self.y, a + k * math.pi / 2, longest))
                    for k in range(4)]
        self.tell = ("gamma", lines(a0))
        yield self.tell_s(tell)
        self.tell = None
        self.ctx.events.append("hex")
        t0 = self.time
        next_tick = 0.0
        while self.time - t0 < burn:
            el = self.time - t0
            spin = way * turn * (el if self.phase < 2 or el < burn / 2 else burn - el)
            self.beams = lines(a0 + spin)
            if el >= next_tick:
                next_tick += tick
                for h in self.ctx.players:
                    if not h.hittable:
                        continue
                    for x0, y0, x1, y1 in self.beams:
                        if patterns.point_segment_distance(h.x, h.y, x0, y0, x1, y1) \
                                <= half + h.hit_radius:
                            self._hit(h, damage, math.atan2(y1 - y0, x1 - x0))
                            break
            yield 0
        self.beams = []

    def m_barrels(self):
        """P8: he heaves (the tell) and hurls leaking barrels at the target,
        one after another, each landing where it'll be (a ring shows where).
        Nothing stops one in the air; landed, it's goo."""
        tell, n, between, flight, *_ = config.KING_BARRELS
        self.tell = ("heave",)
        yield self.tell_s(tell)
        self.tell = None
        for k in range(n):
            t = self.target_now()
            if t is None or self.recruit is None:
                break
            tx, ty = self.lead(t, self.x, self.y, secs=flight) if k else (t.x, t.y)
            tx, ty = self.clamp_to_lair(tx, ty, 3.0)
            b = self.recruit("toxic_barrel", self.x, self.y)
            if b is not None:
                b.summoner = self
                b.start = (self.x, self.y)
                b.target = (tx, ty)
                b.flight = flight
                self.barrels.append(b)
            self.ctx.events.append("swing")
            yield between

    def m_ghouls(self):
        """B2: a roar (the tell), and glowing ghouls claw up round him."""
        tell, n, cap = config.KING_GHOULS
        self.tell = ("roar",)
        yield self.tell_s(tell)
        self.tell = None
        alive = sum(1 for a in self.ctx.actors if getattr(a, "summoner", None) is self
                    and a.alive and getattr(a, "kind_key", "") == "glowing_ghoul")
        for _ in range(max(0, min(n, cap - alive))):
            if self.recruit is None:
                break
            a = self.rng.uniform(0, math.tau)
            r = self.rng.uniform(4.0, 7.0)
            x, y = self.clamp_to_lair(self.x + math.cos(a) * r, self.y + math.sin(a) * r, 4.0)
            add = self.recruit("glowing_ghoul", x, y)
            if add is not None:
                add.summoner = self
                add.alert = True
                self.ctx.effects.append(Effect("eruption", x, y))
        self.ctx.events.append("orb")
        yield 0.3

    def m_emp(self):
        """P1 with a gap: he crackles (the tell), then shockwave rings
        expand from him, each with a gap -- or roll through."""
        tell, n, gap, rings = config.KING_EMP
        self.tell = ("emp",)
        yield self.tell_s(tell)
        self.tell = None
        half = math.radians(gap) / 2
        for k in range(rings):
            t = self.target_now()
            gap_at = (math.atan2(t.y - self.y, t.x - self.x) if t is not None else 0.0) \
                + self.rng.uniform(-1.2, 1.2)
            for i in range(n):
                a = i * math.tau / n + k * 0.08
                if abs((a - gap_at + math.pi) % math.tau - math.pi) < half:
                    continue
                patterns.shoot(self, self.x, self.y, a, self.shots["emp"], self.ctx.projectiles)
            self.ctx.events.append("hex")
            yield 0.5

    def m_skulls(self):
        """P6: green skulls drift out of him and home in (one hit pops one)."""
        tell, n, cap = config.KING_SKULLS
        self.tell = ("roar",)
        yield self.tell_s(tell)
        self.tell = None
        alive = sum(1 for a in self.ctx.actors if getattr(a, "summoner", None) is self
                    and a.alive and getattr(a, "kind_key", "") == "gamma_skull")
        for k in range(max(0, min(n, cap - alive))):
            if self.recruit is None:
                break
            a = self.facing + (k - (n - 1) / 2) * 0.5
            add = self.recruit("gamma_skull", self.x + math.cos(a) * 2.5,
                               self.y + math.sin(a) * 2.5)
            if add is not None:
                add.summoner = self
                add.facing = a
        self.ctx.events.append("orb")
        yield 0.3

    def m_grate(self):
        """He melts into the nearest sewer grate (can't be hit), the grate
        nearest the target rattles (the tell), and he bursts out of it: a
        blast and a ring of glow."""
        sink, rattle, radius, damage, ring = config.KING_GRATE
        grates = self.props.get("grates", [])
        if not grates:
            return
        gx, gy = min(grates, key=lambda g: math.hypot(g[0] - self.x, g[1] - self.y))
        self.tell = ("sink",)
        yield self.tell_s(sink)
        self.x, self.y = gx, gy
        self.submerged = True
        self.ctx.effects.append(Effect("nova", gx, gy, size=2.5))
        t = self.target_now()
        others = [g for g in grates if g != (gx, gy)] or grates
        dest = min(others, key=lambda g: math.hypot(g[0] - t.x, g[1] - t.y)) if t is not None \
            else self.rng.choice(others)
        self.rising = dest
        self.tell = ("rattle", *dest)
        yield self.tell_s(rattle)
        self.tell = None
        self.rising = None
        self.x, self.y = dest
        self.submerged = False
        for h in self.ctx.players:
            if h.hittable and math.hypot(h.x - self.x, h.y - self.y) <= radius + h.hit_radius:
                self._hit(h, damage, math.atan2(h.y - self.y, h.x - self.x))
        self.ctx.effects.append(Effect("explosion", self.x, self.y))
        self.shove_heroes(1.0)
        if self.room_for_shots():
            patterns.radial(self, self.x, self.y, ring, self.shots["glow"], self.ctx.projectiles,
                            self.rng.uniform(0, math.tau))
        self.ctx.events.append("boulder")
        yield 0.5

    def m_stomp(self):
        """Signature 2 (phase 2+): rings mark where it'll land round the
        target (the tell), then he stomps and fallout bursts out there --
        a blast, and a patch with an isotope rod in it."""
        tell, lo, hi, radius, damage = config.FALLOUT_STOMP
        t = self.target_now()
        if t is None:
            return
        spots = []
        for _ in range(self.rng.randint(*config.FALLOUT_PATCHES)):
            for _ in range(30):
                a = self.rng.uniform(0, math.tau)
                r = self.rng.uniform(lo, hi) if spots else self.rng.uniform(1.0, 4.0)
                x, y = self.clamp_to_lair(t.x + math.cos(a) * r, t.y + math.sin(a) * r, 4.0)
                tile = self.ctx.world.tile_at(math.floor(x), math.floor(y))
                if tile is not None and not tile.solid and \
                        all(math.hypot(x - sx, y - sy) > 7.0 for sx, sy in spots):
                    spots.append((x, y))
                    break
        self.tell = ("stomp", spots)
        yield self.tell_s(tell)
        self.tell = None
        for x, y in spots:
            for h in self.ctx.players:
                if h.hittable and math.hypot(h.x - x, h.y - y) <= radius + h.hit_radius:
                    self._hit(h, damage, None)
            rod = self.recruit("isotope_rod", x, y) if self.recruit is not None else None
            if rod is not None:
                rod.summoner = self
            self.patches.append(dict(x=x, y=y, age=0.0, rod=rod))
            self.ctx.effects.append(Effect("explosion", x, y))
        while len(self.patches) > config.FALLOUT_MOST:
            old = self.patches.pop(0)
            if old["rod"] is not None and old["rod"].alive:
                old["rod"].hp = 0.0
                old["rod"].last_hit_by = None
        self.ctx.events.append("boulder")
        yield 0.4


# --- The Snow King, King of Loneliness (M24.2) -------------------------------------------


class SnowKing(Boss):
    """A lonely frost wizard-king in his throne hall, one signature a
    phase, each kept:

    1. THE CROWN: deal enough damage quickly (CROWN_KNOCK) and it flies
       off. Crownless, he can't attack, waddles after it and takes more
       damage; kick it (touch it) to send it further. Back on, he's furious
       (a ring of shards) and it's stuck on for a while.
    2. BLACK ICE (phase 2+): his freeze lays ice sheets (`sheets`) where
       heroes slide (Character.traction). The hall's fire braziers
       (props["braziers"]: stand at one to light it) melt the ice near them.
    3. FLASH FREEZE (phase 3): each hero's chill (Character.chill) fills
       from his frost and from standing still, and drains moving and by a
       fire; full, you're ENCASED in ice (roll to break out, or a partner
       shoots you free) and his hits on you are harder.

    Between them: shard fans, a closing ring of ice spikes, a penguin
    squad sliding across in rows, sweeping frost breath, icicle rain, and
    (phase 2+) a blizzard wind and rolling snowballs. He regrows his ice
    pillars when they're shattered."""

    def __init__(self, spec: EnemySpec, x: float, y: float, rng: random.Random,
                 spawn_id=None) -> None:
        super().__init__(spec, x, y, rng, spawn_id, hit_radius=config.SNOW_HIT_RADIUS)
        self.shots = config.SNOW_SHOTS
        self.crown_on = True
        self.crown = [x, y, 0.0, 0.0]     # loose: x, y, vx, vy
        self.crown_cd = 0.0               # s before it can be knocked off again
        self.donning = 0.0                # putting it back on
        self.dmg_log: list[tuple[float, float]] = []
        self.kick_cd: dict[int, float] = {}
        self.sheets: list[dict] = []      # black ice: {x, y, age}
        self.lit: dict[int, float] = {}   # brazier -> s it burns on
        self.kindle: dict[int, float] = {}
        self.regrow: dict[tuple, float] = {}
        self._regrow_check = 0.0
        self.penguins: list[list] = []    # [x, y, vx, vy, slide left, hit]
        self.snowballs: list[list] = []   # [x, y, vx, vy, radius, age, hit]
        self.icicles: list[tuple] = []    # shadows (the tell): (x, y)
        self.breath: tuple | None = None  # (angle, cone) while breathing
        self.wind: float | None = None    # blizzard heading
        self.ice_hp: dict[int, float] = {}
        self.slow: dict[int, float] = {}  # hero id -> s slowed by breath
        self.waddle = 0.0                 # (drawing)
        self.glide_a = 0.0                # the way he's gliding (M24.5)
        self.glide_dir = 1                # round the target: +1 / -1
        self.glide_t = 0.0                # s before he turns about
        self.trail: list[list[float]] = []   # frost left behind him: [x, y, age]
        self._trail_at = 0.0

    # --- Helpers ------------------------------------------------------------------------

    @property
    def props(self) -> dict:
        return self.lair.props if self.lair is not None else {}

    @property
    def crownless(self) -> bool:
        return not self.crown_on

    @property
    def knock_frac(self) -> float:
        need = config.CROWN_KNOCK[0] * self.max_hp
        recent = sum(a for t, a in self.dmg_log if self.time - t <= config.CROWN_KNOCK[1])
        return min(1.0, recent / need) if need > 0 else 0.0

    def take_damage(self, amount, source, from_angle):
        if self.crownless:
            amount *= config.CROWN_VULN
        dealt = super().take_damage(amount, source, from_angle)
        if dealt and self.crown_on and self.crown_cd <= 0 and self.donning <= 0 and self.ctx:
            self.dmg_log.append((self.time, dealt))
            if self.knock_frac >= 1.0:
                self._knock_off(source)
        return dealt

    def _knock_off(self, source) -> None:
        """The crown flies off his head, away from whoever knocked it."""
        if self._gen is not None:
            self._gen.close()
        self.move = None
        self._gen = None
        self.tell = None
        self.breath = self.wind = None
        self.icicles = []
        self.combo = 0
        self.crown_on = False
        self.dmg_log = []
        if source is not None:
            a = math.atan2(self.y - source.y, self.x - source.x) + self.rng.uniform(-0.6, 0.6)
        else:
            a = self.rng.uniform(0, math.tau)
        self.crown = [self.x, self.y - 1.0, math.cos(a) * config.CROWN_FLY,
                      math.sin(a) * config.CROWN_FLY]
        self.ctx.effects.append(Effect("toast", self.x, self.y - 4,
                                       label="HIS CROWN! KICK IT AWAY!"))
        self.ctx.effects.append(Effect("explosion", self.x, self.y - 1))
        self.ctx.events.append(combat.BREAK)

    def _hit(self, h, damage: float, angle, chill: float | None = None) -> float:
        """One of his hits: harder on an encased hero; chill from phase 3."""
        mult = config.ENCASE[3] if h.encased > 0 else 1.0
        dealt = combat.strike(h, damage * self.damage_mult * mult, self, angle, self.ctx.effects)
        if dealt and self.phase >= 2:
            h.chill = min(config.CHILL_FULL, h.chill + (config.CHILL_HIT if chill is None else chill))
        return dealt or 0.0

    def on_shot_hit(self, victim, dealt: float) -> None:
        if getattr(victim, "faction", "") == "player" and self.phase >= 2:
            victim.chill = min(config.CHILL_FULL, victim.chill + config.CHILL_HIT)

    def _solid(self, x: float, y: float) -> bool:
        if self.lair is not None and not self.lair.inside(x, y):
            return True
        t = self.ctx.world.tile_at(math.floor(x), math.floor(y))
        return t is not None and t.solid

    def on_ice(self, x: float, y: float) -> bool:
        return any(math.hypot(x - s["x"], y - s["y"]) <= self._sheet_r(s) for s in self.sheets)

    @staticmethod
    def _sheet_r(s: dict) -> float:
        r0, r1 = config.ICE_RADIUS
        return r0 + (r1 - r0) * min(1.0, s["age"] / config.ICE_GROW)

    def _set(self, x: float, y: float, tile) -> None:
        world = self.ctx.world
        if hasattr(world, "set_tile"):
            world.set_tile(math.floor(x), math.floor(y), tile)

    # --- Every step ---------------------------------------------------------------------

    def think(self, ctx: AIContext, dt: float) -> None:
        self.ctx = ctx
        self.crown_cd = max(0.0, self.crown_cd - dt)
        self._tick_fires(dt)
        self._tick_sheets(dt)
        self._tick_heroes(dt)
        self._tick_pillars(dt)
        self._tick_penguins(dt)
        self._tick_snowballs(dt)
        if not self.crown_on:
            self.time += dt
            self.dt = dt
            self._tick_crown(dt)
            self._check_phase(ctx)
            return
        t = self.tgt if self.tgt is not None and self.tgt.alive else None
        if t is not None and self.breath is None:
            self.facing = math.atan2(t.y - self.y, t.x - self.x)
        g = self.drift_target()
        if g is not None and self.dazed <= 0:
            if self._gen is None:
                self._glide(g, dt)
            elif self.move == "breath":             # he walks his breath at you
                self._advance(g, dt)
            else:                                   # casting on the move, slower
                self._glide(g, dt, config.SNOW_IN_MOVE)
        self._tick_trail(dt)
        super().think(ctx, dt)

    def _glide(self, t, dt: float, mult: float = 1.0) -> None:
        """Between moves, and slower (`mult`) during most of them (M24.5):
        he skates round the hall, circling the
        target at SNOW_GLIDE[1]..[2] tiles in long curves (his heading turns
        at most SNOW_GLIDE[4] rad/s toward where he wants to go), turning
        about every so often or when something's in his way. His own black
        ice speeds him up."""
        speed, near, far, every, turn, ice = config.SNOW_GLIDE
        self.glide_t -= dt
        if self.glide_t <= 0:
            self.glide_dir = -self.glide_dir
            self.glide_t = self.rng.uniform(*every)
        d = math.hypot(t.x - self.x, t.y - self.y)
        out = math.atan2(self.y - t.y, self.x - t.x)     # from the target out to him
        # Round the target (a quarter turn off "out"), bent outward when
        # he's too close and inward when too far.
        bend = 0.7 if d < near else (-0.7 if d > far else 0.0)
        want = out + self.glide_dir * (math.pi / 2 - bend)
        diff = (want - self.glide_a + math.pi) % math.tau - math.pi
        self.glide_a += max(-turn * dt, min(turn * dt, diff))
        step = speed * mult * (ice if self.on_ice(self.x, self.y) else 1.0) * dt
        for k in (0.0, 0.6, -0.6, 1.2, -1.2):
            a = self.glide_a + k
            nx, ny = self.x + math.cos(a) * step, self.y + math.sin(a) * step
            r = self.hit_radius * 0.9
            if not any(self._solid(nx + math.cos(a + e) * r, ny + math.sin(a + e) * r)
                       for e in (-0.6, 0.0, 0.6)):
                self.x, self.y = nx, ny
                self.glide_a = a
                return
        self.glide_dir = -self.glide_dir                   # boxed in: turn about
        self.glide_a += math.pi * 0.5 * self.glide_dir

    def _advance(self, t, dt: float) -> None:
        """During his frost breath: a slow walk at the target (to
        SNOW_ADVANCE[1] tiles away), the cone coming with him."""
        speed, closest = config.SNOW_ADVANCE
        d = math.hypot(t.x - self.x, t.y - self.y)
        if d <= closest:
            return
        a = math.atan2(t.y - self.y, t.x - self.x)
        nx, ny = self.x + math.cos(a) * speed * dt, self.y + math.sin(a) * speed * dt
        if not self._solid(nx + math.cos(a) * self.hit_radius * 0.9,
                           ny + math.sin(a) * self.hit_radius * 0.9):
            self.x, self.y = nx, ny

    def _tick_trail(self, dt: float) -> None:
        """A short trail of frost where he's glided (drawing only)."""
        for p in self.trail:
            p[2] += dt
        self.trail = [p for p in self.trail if p[2] < config.SNOW_TRAIL[1]]
        if self.walked - self._trail_at >= config.SNOW_TRAIL[0]:
            self._trail_at = self.walked
            self.trail.append([self.x, self.y + self.hit_radius * 0.6, 0.0])

    def on_phase(self, phase: int, ctx: AIContext) -> None:
        label = ("THE FLOOR FREEZES OVER!", "THE COLD GETS INTO YOUR BONES...")[min(phase, 2) - 1] \
            if phase else ""
        if label:
            ctx.effects.append(Effect("toast", self.x, self.y - 4, label=label))

    def _end_move(self) -> None:
        super()._end_move()
        self.breath = self.wind = None
        self.icicles = []

    def _tick_crown(self, dt: float) -> None:
        """The loose crown skids (and bounces off walls); heroes touching it
        kick it on; he waddles after it and puts it back on."""
        cx, cy, vx, vy = self.crown
        sp = math.hypot(vx, vy)
        if sp > 0:
            k = max(0.0, sp - config.CROWN_FRICTION * dt) / sp
            vx, vy = vx * k, vy * k
            nx, ny = cx + vx * dt, cy + vy * dt
            if self._solid(nx, cy):
                vx = -vx
                nx = cx
            if self._solid(nx, ny):
                vy = -vy
                ny = cy
            cx, cy = nx, ny
        for k_ in list(self.kick_cd):
            self.kick_cd[k_] -= dt
        for h in self.ctx.players:
            if not h.alive or self.kick_cd.get(id(h), 0.0) > 0:
                continue
            d = math.hypot(cx - h.x, cy - h.y)
            if d <= h.hit_radius + 0.9:
                a = math.atan2(cy - h.y, cx - h.x) if d > 1e-6 else self.rng.uniform(0, math.tau)
                vx, vy = math.cos(a) * config.CROWN_KICK, math.sin(a) * config.CROWN_KICK
                self.kick_cd[id(h)] = config.CROWN_KICK_EVERY
                self.ctx.effects.append(Effect("toast", cx, cy - 1.5, label="KICKED!"))
                self.ctx.events.append("swing")
        self.crown = [cx, cy, vx, vy]
        if self.donning > 0:
            self.donning -= dt
            if self.donning <= 0:
                self._don()
            return
        d = math.hypot(cx - self.x, cy - self.y)
        if d <= self.hit_radius + 0.6 and math.hypot(vx, vy) < 3.0:
            self.donning = config.CROWN_DON
            return
        a = math.atan2(cy - self.y, cx - self.x)
        step = config.CROWN_CHASE * dt
        for turn in (0.0, 0.6, -0.6, 1.2, -1.2):
            r = self.hit_radius * 0.9
            ta = a + turn
            if not any(self._solid(self.x + math.cos(ta + e) * r, self.y + math.sin(ta + e) * r)
                       for e in (-0.5, 0.0, 0.5)):
                self.x += math.cos(ta) * step
                self.y += math.sin(ta) * step
                self.facing = ta
                self.waddle += dt * 10
                break

    def _don(self) -> None:
        """The crown back on: furious -- a ring of shards -- and it's stuck
        on for a while."""
        self.crown_on = True
        self.crown_cd = config.CROWN_COOLDOWN
        self.dmg_log = []
        self._rest = 0.6
        self.ctx.effects.append(Effect("toast", self.x, self.y - 4, label="HOW DARE YOU!"))
        if self.room_for_shots():
            patterns.radial(self, self.x, self.y, config.CROWN_RAGE, self.shots["shard"],
                            self.ctx.projectiles, self.rng.uniform(0, math.tau))
        self.ctx.events.append("hex")

    def _tick_fires(self, dt: float) -> None:
        """A hero at an unlit brazier lights it in BRAZIER_KINDLE s; it burns
        FIRE_BURN s, melting the ice near it."""
        from ..world import tiles
        for i, (bx, by) in enumerate(self.props.get("braziers", [])):
            if self.lit.get(i, 0.0) > 0:
                self.lit[i] -= dt
                if self.lit[i] <= 0:
                    self._set(bx, by, tiles.FIRE_BOWL)
                    self.lit.pop(i)
                continue
            if any(h.alive and math.hypot(h.x - bx, h.y - by) <= config.FIRE_REACH
                   for h in self.ctx.players):
                self.kindle[i] = self.kindle.get(i, 0.0) + dt
                if self.kindle[i] >= config.BRAZIER_KINDLE:
                    self.kindle.pop(i)
                    self.lit[i] = config.FIRE_BURN
                    self._set(bx, by, tiles.FIRE_BOWL_LIT)
                    self.ctx.effects.append(Effect("toast", bx, by - 2, label="THE FIRE CATCHES!"))
                    self.ctx.effects.append(Effect("explosion", bx, by))
                    self.ctx.events.append("chime")
            else:
                self.kindle.pop(i, None)

    def _fires_lit(self) -> list[tuple[float, float]]:
        braziers = self.props.get("braziers", [])
        return [braziers[i] for i in self.lit]

    def _tick_sheets(self, dt: float) -> None:
        fires = self._fires_lit()
        keep = []
        for s in self.sheets:
            s["age"] += dt
            if s["age"] >= config.ICE_LIFE:
                continue
            if any(math.hypot(s["x"] - fx, s["y"] - fy) <= config.FIRE_MELT for fx, fy in fires):
                self.ctx.effects.append(Effect("nova", s["x"], s["y"], size=self._sheet_r(s)))
                continue
            keep.append(s)
        self.sheets = keep

    def _tick_heroes(self, dt: float) -> None:
        """Ice under each hero in his hall (traction, speed), the breath's
        slow, and from phase 3 chill and encasement."""
        fires = self._fires_lit()
        for h in self.ctx.players:
            if not self.in_arena(h):
                continue
            if not h.alive:
                h.traction, h.time_mult = 1.0, 1.0
                continue
            ice = self.on_ice(h.x, h.y) and not h.rolling
            h.traction = config.ICE_TRACTION if ice else 1.0
            m = config.ICE_TOP if ice else 1.0
            slow = self.slow.get(id(h), 0.0)
            if slow > 0:
                self.slow[id(h)] = slow - dt
                m *= config.SNOW_BREATH[8]
            h.time_mult = m
            if self.phase < 2:
                continue
            if h.encased > 0:
                h.encased -= dt
                hp = self.ice_hp.get(id(h), config.ENCASE[2])
                for p in self.ctx.projectiles:      # a partner's shots chip the ice
                    if p.alive and p.owner is not h and getattr(p.owner, "faction", "") == "player" \
                            and math.hypot(p.x - h.x, p.y - h.y) <= h.hit_radius + 0.6:
                        hp -= p.damage
                        p.alive = False
                self.ice_hp[id(h)] = hp
                if h.encased <= 0 or h.encase_breaks >= config.ENCASE[1] or hp <= 0:
                    h.encased = 0.0
                    h.chill = config.CHILL_FULL * 0.4
                    self.ctx.effects.append(Effect("explosion", h.x, h.y))
                    self.ctx.effects.append(Effect("toast", h.x, h.y - 2, label="BROKE FREE!"))
                    self.ctx.events.append(combat.BREAK)
                continue
            warm = any(math.hypot(h.x - fx, h.y - fy) <= config.FIRE_MELT * 0.6 for fx, fy in fires)
            moving = h.speed > 1.0
            c = h.chill
            if warm:
                c -= config.CHILL_FIRE * dt
            elif moving:
                c -= config.CHILL_MOVING * dt
            else:
                c += config.CHILL_STILL * dt
            h.chill = max(0.0, min(config.CHILL_FULL, c))
            if h.chill >= config.CHILL_FULL:
                h.encased = config.ENCASE[0]
                h.encase_breaks = 0
                self.ice_hp[id(h)] = config.ENCASE[2]
                h.vx = h.vy = 0.0
                self.ctx.effects.append(Effect("toast", h.x, h.y - 2,
                                               label="FROZEN SOLID! ROLL TO BREAK OUT!"))
                self.ctx.events.append("hex")

    def _tick_pillars(self, dt: float) -> None:
        """He regrows a shattered ice pillar ICE_PILLAR_REGROW s later (if
        nobody's standing in it)."""
        from ..world import tiles
        self._regrow_check -= dt
        if self._regrow_check > 0:
            return
        self._regrow_check = 0.5
        world = self.ctx.world
        bodies = [a for a in self.ctx.actors if a.alive]
        for px, py in self.props.get("pillars", []):
            cells = [(px + i, py + j) for i in (0, 1) for j in (0, 1)]
            whole = all(world.tile_at(x, y) is tiles.ICE_PILLAR for x, y in cells)
            if whole:
                self.regrow.pop((px, py), None)
                continue
            t = self.regrow.get((px, py), config.ICE_PILLAR_REGROW) - 0.5
            self.regrow[(px, py)] = t
            if t <= 0 and not any(abs(b.x - px - 1) < 2.5 and abs(b.y - py - 1) < 2.5 for b in bodies):
                for x, y in cells:
                    self._set(x + 0.5, y + 0.5, tiles.ICE_PILLAR)
                self.regrow.pop((px, py), None)
                self.ctx.effects.append(Effect("nova", px + 1, py + 1, size=2.0))

    def _tick_penguins(self, dt: float) -> None:
        if not self.penguins:
            return
        *_, damage, radius = config.SNOW_PENGUINS
        keep = []
        for p in self.penguins:
            step = math.hypot(p[2], p[3]) * dt
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[4] -= step * (0.5 if self.on_ice(p[0], p[1]) else 1.0)   # (twice as far on ice)
            if p[4] <= 0:
                continue
            keep.append(p)
            for h in self.ctx.players:
                if id(h) in p[5] or not h.hittable:
                    continue
                if math.hypot(h.x - p[0], h.y - p[1]) <= radius + h.hit_radius:
                    p[5].add(id(h))
                    a = math.atan2(p[3], p[2])
                    self._hit(h, damage, a)
                    combat.push(h, self.ctx.world, math.cos(a) * 2.5, math.sin(a) * 2.5)
        self.penguins = keep

    def _tick_snowballs(self, dt: float) -> None:
        if not self.snowballs:
            return
        *_, (r0, r1), (d0, d1), life, ice_mult = config.SNOW_SNOWBALLS
        keep = []
        for b in self.snowballs:
            b[5] += dt
            f = min(1.0, b[5] / life)
            b[4] = r0 + (r1 - r0) * f
            m = ice_mult if self.on_ice(b[0], b[1]) else 1.0
            nx, ny = b[0] + b[2] * m * dt, b[1] + b[3] * m * dt
            burst = b[5] >= life or self._solid(nx + b[2] / (abs(b[2]) + abs(b[3]) + 1e-6) * b[4],
                                                ny + b[3] / (abs(b[2]) + abs(b[3]) + 1e-6) * b[4])
            b[0], b[1] = nx, ny
            for h in self.ctx.players:
                if h.hittable and math.hypot(h.x - nx, h.y - ny) <= b[4] + h.hit_radius:
                    a = math.atan2(b[3], b[2])
                    self._hit(h, d0 + (d1 - d0) * f, a)
                    combat.push(h, self.ctx.world, math.cos(a) * 3.0, math.sin(a) * 3.0)
                    burst = True
                    break
            if burst:
                self.ctx.effects.append(Effect("nova", nx, ny, size=b[4] + 0.5))
                if self.room_for_shots():
                    patterns.radial(self, nx, ny, 6, self.shots["shard"], self.ctx.projectiles,
                                    self.rng.uniform(0, math.tau))
                continue
            keep.append(b)
        self.snowballs = keep

    @property
    def bar_label(self) -> str:
        """The boss bar: the crown's state."""
        if self.donning > 0:
            return "HE'S PUTTING HIS CROWN BACK ON!"
        if self.crownless:
            return "CROWNLESS - HIT HIM! KICK THE CROWN AWAY!"
        if self.crown_cd > 0:
            return self.espec.name
        return f"{self.espec.name} - CROWN {round(self.knock_frac * 100)}%"

    def map_marks(self) -> list[tuple[float, float, str, str]]:
        """Map pins: the braziers (lit ones bright), and the loose crown."""
        out = []
        for i, (x, y) in enumerate(self.props.get("braziers", [])):
            lit = i in self.lit
            out.append((x, y, "fire_lit" if lit else "fire", "FIRE" if lit else "FIRE?"))
        if self.crownless:
            out.append((self.crown[0], self.crown[1], "crown", "CROWN"))
        return out

    def on_death(self, ctx: AIContext) -> None:
        from ..world import tiles
        self.ctx = ctx
        for h in ctx.players:
            if self.in_arena(h):
                h.traction, h.time_mult, h.chill, h.encased = 1.0, 1.0, 0.0, 0.0
        for i in list(self.lit):
            self._set(*self.props["braziers"][i], tiles.FIRE_BOWL)
        self.lit = {}
        self.sheets, self.penguins, self.snowballs = [], [], []
        super().on_death(ctx)

    # --- Moves --------------------------------------------------------------------------

    def m_shards(self):
        """P3: he raises his staff (the tell), then fans of ice shards."""
        tell, n, spread, volleys, gap = config.SNOW_SHARDS
        self.tell = ("cast",)
        yield self.tell_s(tell)
        self.tell = None
        for k in range(volleys):
            t = self.target_now()
            if t is None:
                break
            if self.room_for_shots():
                shell = self.shots["shard"]
                patterns.fan(self, self.x, self.y, self.aim(t, self.x, self.y, shell.speed,
                                                            lead=k > 0),
                             n, spread, shell, self.ctx.projectiles)
                self.ctx.events.append("fizzle")
            yield gap

    def m_spikes(self):
        """P5 with a gap: ice spikes burst out of the ground round you, hang
        a moment, then close in."""
        tell, n, radius, hold, gap = config.SNOW_SPIKES
        self.tell = ("cast",)
        yield self.tell_s(tell)
        self.tell = None
        t = self.target_now()
        if t is None:
            return
        patterns.ring_in(self, t.x, t.y, radius, n, self.shots["spike"], self.ctx.projectiles,
                         hold, gap_deg=gap, gap_at=self.rng.uniform(0, math.tau))
        self.ctx.events.append("orb")
        yield 0.3

    def m_penguins(self):
        """P4 with bodies: a whistle (the tell), then a row of penguins
        belly-slides across where you stood, with a gap to step into."""
        tell, n, spacing, gap, speed, slide, *_ = config.SNOW_PENGUINS
        self.tell = ("whistle",)
        yield self.tell_s(tell)
        self.tell = None
        t = self.target_now()
        if t is None:
            return
        h = self.rng.choice((0.0, math.pi))
        hx, hy = math.cos(h), math.sin(h)
        sx, sy = -hy, hx
        back = 24.0
        half = (n - 1) / 2 * spacing
        hole = self.rng.uniform(-half * 0.6, half * 0.6)
        for k in range(n):
            s = -half + k * spacing
            if abs(s - hole) <= gap / 2:
                continue
            self.penguins.append([t.x - hx * back + sx * s, t.y - hy * back + sy * s,
                                  hx * speed, hy * speed, slide, set()])
        self.ctx.events.append("swing")
        yield 0.4

    def m_breath(self):
        """A frost-breath cone: a wedge aimed at you (the tell), then it
        sweeps the way you were going, hitting, slowing and chilling."""
        tell, burn, cone, sweep, reach, tick, damage, chill, _ = config.SNOW_BREATH
        t = self.target_now()
        if t is None:
            return
        a0 = math.atan2(t.y - self.y, t.x - self.x)
        side = math.sin(math.atan2(getattr(t, "vy", 0.0), getattr(t, "vx", 0.0)) - a0)
        way = 1.0 if side > 0.1 else -1.0 if side < -0.1 else self.rng.choice((-1.0, 1.0))
        a0 -= way * math.radians(sweep) * 0.3
        self.facing = a0
        self.tell = ("wedge", a0, math.radians(cone), reach)
        yield self.tell_s(tell)
        self.tell = None
        self.ctx.events.append("hex")
        t0 = self.time
        next_tick = 0.0
        while self.time - t0 < burn:
            el = self.time - t0
            a = a0 + way * math.radians(sweep) * (el / burn)
            self.facing = a
            self.breath = (a, math.radians(cone), reach)
            if el >= next_tick:
                next_tick += tick
                for h in self.ctx.players:
                    if not h.hittable:
                        continue
                    d = math.hypot(h.x - self.x, h.y - self.y)
                    off = (math.atan2(h.y - self.y, h.x - self.x) - a + math.pi) % math.tau - math.pi
                    if d <= reach + h.hit_radius and abs(off) <= math.radians(cone) / 2:
                        self._hit(h, damage, a, chill=chill)
                        self.slow[id(h)] = 1.0
            yield 0
        self.breath = None

    def m_icicles(self):
        """P8: shadows on the ground (the tell: one on you, one on every
        hero frozen solid), then icicles fall and shatter into shards."""
        tell, n, radius, damage, shards = config.SNOW_ICICLES
        t = self.target_now()
        if t is None:
            return
        spots = [(t.x, t.y)] + [(h.x, h.y) for h in self.ctx.players
                                if h.alive and h.encased > 0 and h is not t]
        for _ in range(n - 1):
            a = self.rng.uniform(0, math.tau)
            r = self.rng.uniform(3.0, 9.0)
            spots.append(self.clamp_to_lair(t.x + math.cos(a) * r, t.y + math.sin(a) * r, 3.0))
        self.icicles = spots
        self.tell = ("icicles",)
        yield self.tell_s(tell)
        self.tell = None
        self.icicles = []
        for x, y in spots:
            for h in self.ctx.players:
                if h.hittable and math.hypot(h.x - x, h.y - y) <= radius + h.hit_radius:
                    self._hit(h, damage, None)
            self.ctx.effects.append(Effect("nova", x, y, size=radius))
            if self.room_for_shots():
                patterns.radial(self, x, y, shards, self.shots["shard"], self.ctx.projectiles,
                                self.rng.uniform(0, math.tau))
        self.ctx.events.append("boulder")
        yield 0.3

    def m_freeze(self):
        """Signature 2 (phase 2+): frost spreads from spots near you (the
        tell), and black ice sheets grow there."""
        t = self.target_now()
        if t is None:
            return
        spots = []
        for k in range(self.rng.randint(*config.ICE_SHEETS)):
            a = self.rng.uniform(0, math.tau)
            r = self.rng.uniform(0.0, 3.0) if k == 0 else self.rng.uniform(8.0, 14.0)
            spots.append(self.clamp_to_lair(t.x + math.cos(a) * r, t.y + math.sin(a) * r, 4.0))
        self.tell = ("freeze", spots)
        yield self.tell_s(config.ICE_TELL)
        self.tell = None
        for x, y in spots:
            self.sheets.append(dict(x=x, y=y, age=0.0))
        while len(self.sheets) > 6:
            self.sheets.pop(0)
        self.ctx.events.append("hex")
        yield 0.3

    def m_blizzard(self):
        """P10 + B8 (phase 2+): a gust (the tell), then a blizzard wind
        shoves everyone one way while rows of snow blow through, a hole
        drifting along them."""
        tell, dur, wind, every, gap, hole, half = config.SNOW_BLIZZARD
        heading = self.rng.choice((0.0, math.pi, math.pi / 2, -math.pi / 2))
        self.tell = ("gust", heading)
        yield self.tell_s(tell)
        self.tell = None
        t = self.target_now()
        if t is None:
            return
        cx, cy = t.x, t.y
        self.wind = heading
        phase = self.rng.uniform(0, math.tau)
        t0 = self.time
        next_row = 0.0
        while self.time - t0 < dur:
            el = self.time - t0
            for h in self.ctx.players:
                if h.alive and not h.rolling and self.in_arena(h):
                    combat.push(h, self.ctx.world, math.cos(heading) * wind * self.dt,
                                math.sin(heading) * wind * self.dt)
            if el >= next_row:
                next_row += every
                if self.room_for_shots():
                    patterns.curtain(self, cx, cy, heading, 20.0, half, gap,
                                     math.sin(phase + el * 0.8) * half * 0.6, hole,
                                     self.shots["snow"], self.ctx.projectiles)
            yield 0
        self.wind = None

    def m_snowballs(self):
        """Phase 2+: he heaves (the tell) and rolls giant snowballs at you;
        they grow as they go, speed up on ice, and burst into shards."""
        tell, n, speed, *_ = config.SNOW_SNOWBALLS
        self.tell = ("cast",)
        yield self.tell_s(tell)
        self.tell = None
        t = self.target_now()
        if t is None:
            return
        base = self.aim(t, self.x, self.y, speed)
        for k in range(n):
            a = base + (k - (n - 1) / 2) * 0.5
            x = self.x + math.cos(a) * (self.hit_radius + 1.5)
            y = self.y + math.sin(a) * (self.hit_radius + 1.5)
            self.snowballs.append([x, y, math.cos(a) * speed, math.sin(a) * speed,
                                   config.SNOW_SNOWBALLS[3][0], 0.0, None])
        self.ctx.events.append("boulder")
        yield 0.4



# --- Fragile, The Misunderstood (M24.3) ---------------------------------------------------


class Fragile(Boss):
    """A vampire with a black lace parasol in her ruined ballroom, one signature a
    phase, each kept:

    1. SUNLIGHT: the ballroom's shuttered windows (props["windows"]) each
       have a lever (props["levers"]): stand at one to open its shutter, and
       a shaft of sun falls across the floor (`open`). In it she takes
       SUN_VULN x damage; caught by one she's stunned. She keeps out of the
       light and slams shutters closed. Heroes in the light are safe from
       her gaze.
    2. SHAPESHIFT (phase 2+): she becomes a bat swarm (fast, flying,
       half damage except from the bard's pulse), a wolf (charges, howls,
       claws) or herself, each with its own moves.
    3. ON THE BEAT (phase 3): a metronome; her tells end on beats; a roll
       started right on a beat is PERFECT and stuns her.

    Her own moves (girl form): rose-petal rings (her parasol twirled), the
    parasol throw (spinning out and back), crescent slashes, the hypnotic gaze (a cone that pulls you in),
    mist step (leaving slowing mist), thralls from her coffins (stake an
    empty coffin to keep it shut) and, from phase 2, chandeliers."""

    def __init__(self, spec: EnemySpec, x: float, y: float, rng: random.Random,
                 spawn_id=None) -> None:
        super().__init__(spec, x, y, rng, spawn_id, hit_radius=config.FRAGILE_HIT_RADIUS)
        self.shots = config.FRAGILE_SHOTS
        self.open: dict[int, float] = {}      # window -> s its shutter stays open
        self.pull: dict[int, float] = {}      # lever -> s a hero has been at it
        self.caught: set[int] = set()         # windows whose opening has stunned her already
        self.slam_t = config.SLAM_EVERY
        self.form = "girl"
        self.form_t = config.FORM_TIME
        self.shifting = 0.0                   # the change's tell
        self.next_form = "girl"
        self.beat0 = 0.0                      # the metronome's start (her clock)
        self.perfect_cd = 0.0
        self.rolling_was: dict[int, bool] = {}
        self.parasol: list | None = None          # [x, y, angle, gone, back?, hit set]
        self.mist: list[list[float]] = []     # [x, y, age]
        self.staked: set[int] = set()
        self.stake_t: dict[int, float] = {}
        self.fallen: set[int] = set()         # chandeliers down
        self.shadows: list = []               # chandeliers about to fall
        self.gaze: tuple | None = None        # (angle, cone, reach) while gazing
        self.dashing = False
        self.sway = 0.0
        self.circle_dir = 1                   # round the target: +1 / -1 (M24.5)
        self.circle_t = 0.0                   # s before she turns about

    # --- Helpers ------------------------------------------------------------------------

    @property
    def props(self) -> dict:
        return self.lair.props if self.lair is not None else {}

    def shaft(self, i: int) -> tuple[float, float, float, float]:
        wx, wy, dx, dy = self.props["windows"][i]
        return wx, wy, wx + dx * config.SHAFT_LEN, wy + dy * config.SHAFT_LEN

    def in_sun(self, x: float, y: float, pad: float = 0.0) -> bool:
        for i in self.open:
            x0, y0, x1, y1 = self.shaft(i)
            if patterns.point_segment_distance(x, y, x0, y0, x1, y1) <= config.SHAFT_WIDTH / 2 + pad:
                return True
        return False

    def take_damage(self, amount, source, from_angle):
        if self.form == "bat":
            pulse = getattr(getattr(getattr(source, "weapon", None), "spec", None), "kind", "")
            if pulse != "pulse":
                amount *= config.BAT_ARMOR
        if self.in_sun(self.x, self.y):
            amount *= config.SUN_VULN
        return super().take_damage(amount, source, from_angle)

    @property
    def period(self) -> float:
        lo, hi = config.BEAT_BPM
        f = 1.0 - max(0.0, min(1.0, self.frac / config.BOSSES["fragile"].phases[2].below))
        return 60.0 / (lo + (hi - lo) * f)

    def beat_phase(self) -> float:
        """Seconds since the last beat."""
        return (self.time - self.beat0) % self.period

    def tell_s(self, seconds: float) -> float:
        """In phase 3 a tell runs on to end exactly on a beat."""
        s = super().tell_s(seconds)
        if self.phase < 2:
            return s
        p = self.period
        land = (self.time - self.beat0 + s) % p
        return s + (p - land if land > 1e-6 else 0.0)

    def _stun(self, seconds: float, label: str, in_move: bool = False) -> None:
        """Stunned: the move she's in is cut short (`in_move`: called from
        inside that move, which then just returns)."""
        if self._gen is not None and not in_move:
            self._gen.close()
            self.move = None
            self._gen = None
        self.tell = None
        self.gaze = None
        self.dashing = False
        self.combo = 0
        self.dazed = max(self.dazed, seconds)
        self._rest = 0.4
        self.ctx.effects.append(Effect("toast", self.x, self.y - 3, label=label))
        self.ctx.effects.append(Effect("nova", self.x, self.y, size=2.5))
        self.ctx.events.append(combat.BREAK)

    def _solid(self, x: float, y: float) -> bool:
        if self.lair is not None and not self.lair.inside(x, y):
            return True
        t = self.ctx.world.tile_at(math.floor(x), math.floor(y))
        return t is not None and t.solid

    def _set(self, x: float, y: float, tile) -> None:
        world = self.ctx.world
        if hasattr(world, "set_tile"):
            world.set_tile(math.floor(x), math.floor(y), tile)

    # --- Every step ---------------------------------------------------------------------

    def think(self, ctx: AIContext, dt: float) -> None:
        self.ctx = ctx
        self.sway += dt
        self.perfect_cd = max(0.0, self.perfect_cd - dt)
        self._tick_sun(dt)
        self._tick_coffins(dt)
        self._tick_mist(dt)
        self._tick_parasol(dt)
        self._tick_beat()
        if self.dazed > 0:
            self.time += dt
            self.dt = dt
            self.dazed = max(0.0, self.dazed - dt)
            self._check_phase(ctx)
            return
        if self._tick_form(dt):
            self.time += dt
            self.dt = dt
            return
        t = self.tgt if self.tgt is not None and self.tgt.alive else None
        if t is not None and not self.dashing and self.gaze is None:
            self.facing = math.atan2(t.y - self.y, t.x - self.x)
        g = self.drift_target()
        if g is not None:
            if self._gen is None:
                self._drift(g, dt)
            elif self.move not in config.FRAGILE_PLANTED and not self.dashing \
                    and self.gaze is None:
                self._drift(g, dt, config.FRAGILE_IN_MOVE)   # casting on the move, slower
        super().think(ctx, dt)

    def on_phase(self, phase: int, ctx: AIContext) -> None:
        if phase == 2:
            self.beat0 = self.time
        label = ("SHE CHANGES...", "SHE PLAYS. FEEL THE BEAT!")[min(phase, 2) - 1] if phase else ""
        if label:
            ctx.effects.append(Effect("toast", self.x, self.y - 3, label=label))

    def _end_move(self) -> None:
        super()._end_move()
        self.gaze = None
        self.dashing = False

    def _drift(self, t, dt: float, mult: float = 1.0) -> None:
        """Between moves, and slower (`mult`) during most of them (M24.5):
        she circles the target at
        FRAGILE_CIRCLE[0]..[1] tiles, out of the light, turning about every
        so often or when the way round is blocked (a wall, a sun shaft)."""
        near, far, every, _ = config.FRAGILE_CIRCLE
        self.circle_t -= dt
        if self.circle_t <= 0:
            self.circle_dir = -self.circle_dir
            self.circle_t = self.rng.uniform(*every)
        d = math.hypot(t.x - self.x, t.y - self.y)
        out = math.atan2(self.y - t.y, self.x - t.x)
        bend = 0.8 if d < near else (-0.8 if d > far else 0.0)
        a = out + self.circle_dir * (math.pi / 2 - bend)
        speed = config.FORM_SPEED[self.form] * config.FRAGILE_CIRCLE[3] * mult * dt
        for turn in (0.0, 0.5, -0.5, 1.0, -1.0):
            nx, ny = self.x + math.cos(a + turn) * speed, self.y + math.sin(a + turn) * speed
            if self.lair is not None and not self.lair.inside(nx, ny):
                continue
            if (self.form == "bat" or not self._solid(nx, ny)) and not self.in_sun(nx, ny, 0.5):
                self.x, self.y = nx, ny
                return
        self.circle_dir = -self.circle_dir                 # blocked: the other way round

    def _tick_sun(self, dt: float) -> None:
        """Levers open shutters; open shafts run out or get slammed; a shaft
        that catches her stuns her (once per opening)."""
        from ..world import tiles
        windows = self.props.get("windows", [])
        levers = self.props.get("levers", [])
        for i in list(self.open):
            self.open[i] -= dt
            if self.open[i] <= 0:
                self._close(i)
        for i, (lx, ly) in enumerate(levers):
            if i in self.open or i >= len(windows):
                continue
            if any(h.alive and math.hypot(h.x - lx, h.y - ly) <= config.LEVER_REACH
                   for h in self.ctx.players):
                self.pull[i] = self.pull.get(i, 0.0) + dt
                if self.pull[i] >= config.LEVER_TIME:
                    self.pull.pop(i)
                    self.open[i] = config.SHAFT_OPEN
                    self.caught.discard(i)
                    wx, wy, _, _ = windows[i]
                    for dx in (-0.5, 0.5):
                        self._set(wx + dx, wy, tiles.WINDOW_OPEN)
                    self.ctx.effects.append(Effect("toast", lx, ly - 2, label="SUNLIGHT!"))
                    self.ctx.events.append("chime")
            else:
                self.pull.pop(i, None)
        if self.dazed <= 0:
            for i in self.open:
                if i not in self.caught and self.in_sun(self.x, self.y) and self._shaft_has(i):
                    self.caught.add(i)
                    self._stun(config.SUN_STUN, "SHE BURNS! HIT HER!")
                    break
        self.slam_t -= dt
        if self.slam_t <= 0 and self.open and self._gen is None and self.dazed <= 0:
            self.slam_t = config.SLAM_EVERY
            self._start("slam")

    def _shaft_has(self, i: int) -> bool:
        x0, y0, x1, y1 = self.shaft(i)
        return patterns.point_segment_distance(self.x, self.y, x0, y0, x1, y1) <= config.SHAFT_WIDTH / 2

    def _close(self, i: int) -> None:
        from ..world import tiles
        self.open.pop(i, None)
        wx, wy, _, _ = self.props["windows"][i]
        for dx in (-0.5, 0.5):
            self._set(wx + dx, wy, tiles.SHUTTER)

    def _tick_coffins(self, dt: float) -> None:
        """A hero at an unstaked coffin STAKE_TIME s stakes it shut."""
        from ..world import tiles
        for i, (cx, cy) in enumerate(self.props.get("coffins", [])):
            if i in self.staked:
                continue
            if any(h.alive and math.hypot(h.x - cx, h.y - cy) <= 2.2 for h in self.ctx.players):
                self.stake_t[i] = self.stake_t.get(i, 0.0) + dt
                if self.stake_t[i] >= config.STAKE_TIME:
                    self.staked.add(i)
                    self.stake_t.pop(i)
                    self._set(cx, cy, tiles.COFFIN_STAKED)
                    self.ctx.effects.append(Effect("toast", cx, cy - 2, label="STAKED!"))
                    self.ctx.events.append("boulder")
            else:
                self.stake_t.pop(i, None)

    def _tick_mist(self, dt: float) -> None:
        life, slow, radius = config.FRAGILE_MIST[3], config.FRAGILE_MIST[4], config.FRAGILE_MIST[5]
        for m in self.mist:
            m[2] += dt
        self.mist = [m for m in self.mist if m[2] < life]
        for h in self.ctx.players:
            if not self.in_arena(h):
                continue
            inside = h.alive and not h.rolling and any(
                math.hypot(h.x - m[0], h.y - m[1]) <= radius for m in self.mist)
            h.time_mult = slow if inside else 1.0

    def _tick_parasol(self, dt: float) -> None:
        """The thrown parasol, open and spinning: out along its throw,
        curving, then back to her; it hits each hero once a leg."""
        if self.parasol is None:
            return
        _, speed, reach, damage, radius = config.FRAGILE_PARASOL
        ax = self.parasol
        step = speed * dt
        if not ax[4]:
            ax[2] += 1.2 * dt                     # (it curves)
            ax[0] += math.cos(ax[2]) * step
            ax[1] += math.sin(ax[2]) * step
            ax[3] += step
            if ax[3] >= reach:
                ax[4] = True
                ax[5] = set()
        else:
            dx, dy = self.x - ax[0], self.y - ax[1]
            d = math.hypot(dx, dy)
            if d <= step + 0.5:
                self.parasol = None
                return
            ax[0] += dx / d * step
            ax[1] += dy / d * step
        for h in self.ctx.players:
            if h.hittable and id(h) not in ax[5] and \
                    math.hypot(h.x - ax[0], h.y - ax[1]) <= radius + h.hit_radius:
                ax[5].add(id(h))
                combat.strike(h, damage * self.damage_mult, self, ax[2], self.ctx.effects)

    def _tick_beat(self) -> None:
        """Phase 3: a hero who starts a roll right on a beat stuns her."""
        if self.phase < 2:
            return
        ph = self.beat_phase()
        on_beat = min(ph, self.period - ph) <= config.BEAT_PERFECT
        for h in self.ctx.players:
            was = self.rolling_was.get(id(h), False)
            now = h.rolling
            self.rolling_was[id(h)] = now
            if now and not was and on_beat and self.perfect_cd <= 0 and self.in_arena(h):
                self.perfect_cd = config.PERFECT_EVERY
                self.ctx.effects.append(Effect("toast", h.x, h.y - 2, label="PERFECT!"))
                if self.dazed <= 0:
                    self._stun(config.PERFECT_STUN, "ON THE BEAT! SHE STAGGERS!")

    def _tick_form(self, dt: float) -> bool:
        """Phase 2+: every FORM_TIME s she shifts (FORM_TELL s, nothing
        else meanwhile). True while she's shifting."""
        if self.phase < 1:
            return False
        if self.shifting > 0:
            self.shifting -= dt
            if self.shifting <= 0:
                self.tell = None
                self.form = self.next_form
                self.hit_radius = config.FRAGILE_HIT_RADIUS * (1.3 if self.form != "girl" else 1.0)
                self.form_t = config.FORM_TIME
                self.ctx.effects.append(Effect("explosion", self.x, self.y))
                self.ctx.effects.append(Effect(
                    "toast", self.x, self.y - 3,
                    label={"bat": "A SWARM OF BATS!", "wolf": "A WOLF!", "girl": "HERSELF AGAIN"}
                    [self.form]))
            return True
        self.form_t -= dt
        if self.form_t <= 0 and self._gen is None:
            others = [f for f in config.FRAGILE_FORMS if f != self.form]
            self.next_form = self.rng.choice(others)
            self.shifting = config.FORM_TELL
            self.tell = ("shift", self.next_form)
            return True
        return False

    def _pick_move(self) -> str:
        if self.form == "girl":
            moves = [(m, w) for m, w in self.bspec.phases[self.phase].moves if m != self.last_move]
        else:
            moves = [(m, w) for m, w in config.FRAGILE_FORM_MOVES[self.form] if m != self.last_move]
        if self._thralls() >= config.FRAGILE_THRALLS[2] or \
                len(self.staked) >= len(self.props.get("coffins", [])):
            moves = [(m, w) for m, w in moves if m != "thralls"]
        chandeliers = self.props.get("chandeliers", [])
        if len(self.fallen) >= len(chandeliers):
            moves = [(m, w) for m, w in moves if m != "chandeliers"]
        if not moves:
            return "mist"
        total = sum(w for _, w in moves)
        r = self.rng.uniform(0, total)
        for m, w in moves:
            r -= w
            if r <= 0:
                return m
        return moves[-1][0]

    def _thralls(self) -> int:
        return sum(1 for a in self.ctx.actors if getattr(a, "summoner", None) is self and a.alive)

    @property
    def bar_label(self) -> str:
        """The boss bar: her form, and her state."""
        if self.dazed > 0:
            return "SHE'S STUNNED - HIT HER!"
        if self.in_sun(self.x, self.y):
            return "SHE BURNS IN THE SUN!"
        form = {"girl": "", "bat": " - BATS", "wolf": " - WOLF"}[self.form]
        return self.espec.name + form

    def map_marks(self) -> list[tuple[float, float, str, str]]:
        """Map pins: closed shutters' levers, open shafts, unstaked coffins."""
        out = []
        for i, (lx, ly) in enumerate(self.props.get("levers", [])):
            if i in self.open:
                x0, y0, x1, y1 = self.shaft(i)
                out.append(((x0 + x1) / 2, (y0 + y1) / 2, "sun", "SUN"))
            else:
                out.append((lx, ly, "lever", "LEVER"))
        for i, (cx, cy) in enumerate(self.props.get("coffins", [])):
            if i not in self.staked:
                out.append((cx, cy, "coffin", "COFFIN"))
        return out

    def on_death(self, ctx: AIContext) -> None:
        self.ctx = ctx
        for i in list(self.open):
            self._close(i)
        for h in ctx.players:
            if self.in_arena(h):
                h.time_mult = 1.0
        self.mist = []
        self.parasol = None
        # (No explosion: she doesn't die -- she sits down and cries.)
        ctx.effects.append(Effect("nova", self.x, self.y, size=3.0))

    # --- Moves --------------------------------------------------------------------------

    def m_slam(self):
        """She slams the nearest open shutter (a 1 s tell at that window)."""
        if not self.open:
            return
        i = min(self.open, key=lambda k: math.hypot(self.props["windows"][k][0] - self.x,
                                                   self.props["windows"][k][1] - self.y))
        wx, wy, _, _ = self.props["windows"][i]
        self.tell = ("slam", wx, wy)
        yield self.tell_s(config.SLAM_TELL)
        self.tell = None
        if i in self.open:
            self._close(i)
            self.ctx.effects.append(Effect("toast", wx, wy + 2, label="SLAM!"))
            self.ctx.events.append("boulder")
        yield 0.2

    def m_petals(self):
        """P1 with a gap: she twirls her parasol (the tell), then flings rings of
        rose petals."""
        tell, n, gap, rings, between = config.FRAGILE_PETALS
        self.tell = ("twirl",)
        yield self.tell_s(tell)
        self.tell = None
        half = math.radians(gap) / 2
        for k in range(rings):
            t = self.target_now()
            gap_at = (math.atan2(t.y - self.y, t.x - self.x) if t is not None else 0.0) \
                + self.rng.uniform(-1.5, 1.5)
            for i in range(n):
                a = k * 0.13 + i * math.tau / n
                if abs((a - gap_at + math.pi) % math.tau - math.pi) < half:
                    continue
                patterns.shoot(self, self.x, self.y, a, self.shots["petal"], self.ctx.projectiles)
            self.ctx.events.append("orb")
            yield self.tell_s(between) if self.phase >= 2 else between

    def m_parasol(self):
        """She furls her parasol and raises it (the tell), then hurls it open:
        it spins out on a curve and comes back to her, hitting on both legs."""
        tell = config.FRAGILE_PARASOL[0]
        t = self.target_now()
        if t is None or self.parasol is not None:
            return
        self.tell = ("parasol",)
        yield self.tell_s(tell)
        self.tell = None
        a = math.atan2(t.y - self.y, t.x - self.x) - 0.6
        self.parasol = [self.x, self.y, a, 0.0, False, set()]
        self.ctx.events.append("swing")
        yield 0.4

    def m_slashes(self):
        """P3: crescent claw slashes, fans of red arcs."""
        tell, n, spread, volleys, gap = config.FRAGILE_SLASHES
        self.tell = ("claw",)
        yield self.tell_s(tell)
        self.tell = None
        for k in range(volleys):
            t = self.target_now()
            if t is None:
                break
            if self.room_for_shots():
                shell = self.shots["slash"]
                patterns.fan(self, self.x, self.y, self.aim(t, self.x, self.y, shell.speed,
                                                            lead=k > 0),
                             n, spread, shell, self.ctx.projectiles)
                self.ctx.events.append("swing")
            yield gap

    def m_gaze(self):
        """Her hypnotic gaze: a red wedge (the tell), then the cone pulls
        heroes in it toward her -- unless they're behind something that
        blocks sight, rolling, or standing in sunlight."""
        from ..systems.raycast import first_hit
        tell, dur, cone, reach, pull = config.FRAGILE_GAZE
        t = self.target_now()
        if t is None:
            return
        a = math.atan2(t.y - self.y, t.x - self.x)
        self.facing = a
        self.tell = ("wedge", a, math.radians(cone), reach)
        yield self.tell_s(tell)
        self.tell = None
        self.gaze = (a, math.radians(cone), reach)
        t0 = self.time
        while self.time - t0 < dur:
            for h in self.ctx.players:
                if not h.alive or h.rolling or self.in_sun(h.x, h.y):
                    continue
                d = math.hypot(h.x - self.x, h.y - self.y)
                off = (math.atan2(h.y - self.y, h.x - self.x) - a + math.pi) % math.tau - math.pi
                if d > reach + h.hit_radius or abs(off) > math.radians(cone) / 2 or d < 2.5:
                    continue
                if first_hit(self.ctx.world.tile_at, self.x, self.y, h.x, h.y) is not None:
                    continue
                step = min(d - 2.5, pull * self.dt)
                combat.push(h, self.ctx.world, (self.x - h.x) / d * step, (self.y - h.y) / d * step)
            yield 0
        self.gaze = None

    def m_mist(self):
        """She turns to mist: a shimmer where she'll be (the tell), then
        she's there -- leaving a trail of slowing mist behind."""
        tell, lo, hi, *_ = config.FRAGILE_MIST
        spot = None
        for _ in range(30):
            a = self.rng.uniform(0, math.tau)
            r = self.rng.uniform(lo, hi)
            x, y = self.clamp_to_lair(self.x + math.cos(a) * r, self.y + math.sin(a) * r, 5.0)
            if not self._solid(x, y) and not self.in_sun(x, y, 1.0):
                spot = (x, y)
                break
        if spot is None:
            return
        self.tell = ("mist", *spot)
        yield self.tell_s(tell)
        self.tell = None
        x0, y0 = self.x, self.y
        n = max(2, int(math.hypot(spot[0] - x0, spot[1] - y0) / 2.5))
        for k in range(n + 1):
            f = k / n
            self.mist.append([x0 + (spot[0] - x0) * f, y0 + (spot[1] - y0) * f, 0.0])
        self.x, self.y = spot
        self.ctx.events.append("fizzle")
        yield 0.2

    def m_thralls(self):
        """B2: her coffins creak (the tell), and thralls climb out of the
        ones not staked shut."""
        tell, n, cap = config.FRAGILE_THRALLS
        coffins = [c for i, c in enumerate(self.props.get("coffins", [])) if i not in self.staked]
        if not coffins:
            return
        self.tell = ("creak", coffins)
        yield self.tell_s(tell)
        self.tell = None
        for k in range(min(n, cap - self._thralls())):
            if self.recruit is None:
                break
            cx, cy = coffins[k % len(coffins)]
            from ..systems.quests import free_spot
            x, y = free_spot(self.ctx.world, cx, cy + 1.5, 11.0)
            add = self.recruit("thrall", x, y)
            if add is not None:
                add.summoner = self
                add.alert = True
                self.ctx.effects.append(Effect("eruption", x, y))
        self.ctx.events.append("hex")
        yield 0.3

    def m_chandeliers(self):
        """P8: the chandeliers nearest the target sway (their shadows on the
        floor, the tell), then crash down -- a blast, and rubble for cover."""
        from ..world import tiles
        tell, radius, damage = config.FRAGILE_CHANDELIER
        t = self.target_now()
        hang = [(i, c) for i, c in enumerate(self.props.get("chandeliers", []))
                if i not in self.fallen]
        if t is None or not hang:
            return
        hang.sort(key=lambda ic: math.hypot(ic[1][0] - t.x, ic[1][1] - t.y))
        drop = hang[:2]
        self.shadows = [c for _, c in drop]
        self.tell = ("shadows",)
        yield self.tell_s(tell)
        self.tell = None
        self.shadows = []
        for i, (x, y) in drop:
            self.fallen.add(i)
            for h in self.ctx.players:
                if h.hittable and math.hypot(h.x - x, h.y - y) <= radius + h.hit_radius:
                    combat.strike(h, damage * self.damage_mult, self, None, self.ctx.effects)
            for dx in (-1, 0):
                for dy in (-1, 0):
                    tile = self.ctx.world.tile_at(math.floor(x) + dx, math.floor(y) + dy)
                    if tile is not None and not tile.solid:
                        self._set(x + dx + 0.5, y + dy + 0.5, tiles.CHANDELIER_RUBBLE)
            self.ctx.effects.append(Effect("explosion", x, y))
        self.shove_heroes(0.5)
        self.ctx.events.append("boulder")
        yield 0.3

    def m_curtain(self):
        """Bat form, P10: a screech (the tell), then rows of bats sweep across
        where you stood, with a hole drifting along them."""
        tell, dur, every, gap, hole, half = config.FRAGILE_CURTAIN
        self.tell = ("screech",)
        yield self.tell_s(tell)
        self.tell = None
        t = self.target_now()
        if t is None:
            return
        heading = self.rng.choice((0.0, math.pi))
        cx, cy = t.x, t.y
        phase = self.rng.uniform(0, math.tau)
        tt = 0.0
        while tt < dur:
            if self.room_for_shots():
                patterns.curtain(self, cx, cy, heading, 22.0, half, gap,
                                 math.sin(phase + tt) * half * 0.6, hole, self.shots["bat"],
                                 self.ctx.projectiles)
            tt += every
            yield every

    def _dash(self, tell_kind: str, tell: float, speed: float, longest: float, damage: float,
              width: float):
        """A line (the tell), then a dash along it hitting whoever's on it;
        running into sunlight stuns her."""
        t = self.target_now()
        if t is None:
            return
        wait = self.tell_s(tell)
        tx, ty = self.lead(t, self.x, self.y, secs=wait)
        a = math.atan2(ty - self.y, tx - self.x)
        length = min(longest, math.hypot(tx - self.x, ty - self.y) + 5.0)
        x1, y1 = self.clamp_to_lair(self.x + math.cos(a) * length, self.y + math.sin(a) * length, 3.0)
        self.facing = a
        self.tell = (tell_kind, self.x, self.y, x1, y1)
        yield wait
        self.tell = None
        self.dashing = True
        self.ctx.events.append("swing")
        x0, y0 = self.x, self.y
        total = math.hypot(x1 - x0, y1 - y0) or 1.0
        gone = 0.0
        hit = set()
        while gone < total:
            gone = min(total, gone + speed * self.dt)
            nx, ny = x0 + (x1 - x0) * gone / total, y0 + (y1 - y0) * gone / total
            if self.form != "bat" and self._solid(nx, ny):
                break
            self.x, self.y = nx, ny
            for h in self.ctx.players:
                if h.hittable and id(h) not in hit and \
                        math.hypot(h.x - nx, h.y - ny) <= width + h.hit_radius:
                    hit.add(id(h))
                    combat.strike(h, damage * self.damage_mult, self, a, self.ctx.effects)
            if self.in_sun(nx, ny):
                self._stun(config.SUN_STUN, "INTO THE SUN! SHE BURNS!", in_move=True)
                return
            yield 0
        self.dashing = False
        yield 0.3

    def m_swoop(self):
        """Bat form: a dotted line (the tell), then the swarm swoops along it."""
        tell, speed, longest, damage, width = config.FRAGILE_SWOOP
        yield from self._dash("swoop", tell, speed, longest, damage, width)

    def m_charge(self):
        """Wolf form, B1: a line with ">" (the tell), then she charges along
        it. Into sunlight, she's stunned."""
        tell, speed, longest, damage = config.FRAGILE_CHARGE
        yield from self._dash("charge", tell, speed, longest, damage, self.hit_radius)

    def m_howl(self):
        """Wolf form, B8: a howl (the tell): heroes near are thrown back, and
        a ring of shots goes out."""
        tell, radius, push, ring = config.FRAGILE_HOWL
        self.tell = ("howl",)
        yield self.tell_s(tell)
        self.tell = None
        for h in self.ctx.players:
            d = math.hypot(h.x - self.x, h.y - self.y)
            if h.alive and 0 < d <= radius and not h.rolling:
                combat.push(h, self.ctx.world, (h.x - self.x) / d * push, (h.y - self.y) / d * push)
        if self.room_for_shots():
            patterns.radial(self, self.x, self.y, ring, self.shots["slash"], self.ctx.projectiles,
                            self.rng.uniform(0, math.tau))
        self.ctx.events.append("hex")
        yield 0.3

    def m_claws(self):
        """Wolf form: wide fans of claw slashes, close in."""
        tell, n, spread, volleys, gap = config.FRAGILE_CLAWS
        self.tell = ("claw",)
        yield self.tell_s(tell)
        self.tell = None
        for _ in range(volleys):
            t = self.target_now()
            if t is None:
                break
            if self.room_for_shots():
                patterns.fan(self, self.x, self.y, math.atan2(t.y - self.y, t.x - self.x), n,
                             spread, self.shots["slash"], self.ctx.projectiles)
            yield gap


# --- Nettle, the Blighted (M25.1) ---------------------------------------------------------


class Glamour(Actor):
    """One of Nettle's glamour decoys: a copy of her that flies and casts
    with her, but casts no shadow. One hit pops it (Nettle sees it gone and
    bursts it into dust). It's part of her: her shots pass it, it gives
    nothing when it pops, and she moves it."""

    faction = "enemy"
    boss = True                       # never sleeps; flies with her

    def __init__(self, spec: EnemySpec, x: float, y: float, rng: random.Random,
                 spawn_id=None) -> None:
        super().__init__(1, config.NETTLE_HIT_RADIUS)
        self.espec = spec
        self.spawn_id = spawn_id
        self.x, self.y = x, y
        self.half = spec.size_px / 2
        self.facing = 0.0
        self.vx = self.vy = 0.0
        self.part_of = None           # Nettle (set when she makes it)
        self.age = 0.0
        self.faded = False            # gone by itself (no dust)
        self.dir = rng.choice((-1, 1))
        self.walked = 0.0
        self.damage_mult = 1.0
        self.haste = 0.0
        self.level = 1

    def scale_to_level(self, level: int) -> None:
        pass

    def think(self, ctx, dt: float) -> None:
        pass                          # Nettle flies her copies

    def hear(self, x: float, y: float) -> None:
        pass


class Nettle(Boss):
    """A corrupted pixie in her withered glade, one signature a phase, each
    kept (design/BOSSES.md section 23):

    1. GLAMOUR (all fight): every DECOY_EVERY s she shimmers and splits
       into copies (Glamour bodies) -- and may come out as any of them.
       They fly round you with her and cast her spirals and sparks; only
       she casts a shadow. A hit pops a copy into a ring of dust.
    2. SHRINKING DUST (phase 2+): clouds of dust (her "dust" move, and her
       dives' trails); a moment in one shrinks you (Character.shrunk:
       faster, half damage, her hits knock you about) until you stand on
       a growcap (props["growcaps"]; each regrows a while after) or it
       wears off.
    3. BLIGHT (phase 3): every BLIGHT_EVERY s she plants rot seeds; each
       patch spreads, hurts you on it and heals her over it -- between
       moves she flies back to drink. Stand on a seed a moment to pull it.

    Her own moves: dust spirals, hex sparks (homing), thorn lines (the
    ground cracks first), a bramble cage, rot moths, dive-bombs, the
    wisp lure (the forest's lights drift to her and she flings them,
    homing) and nettle rain. She flies -- over toadstools and stumps,
    never out of the glade -- circling her target, and keeps circling
    (slower) through her moves (M24.5)."""

    def __init__(self, spec: EnemySpec, x: float, y: float, rng: random.Random,
                 spawn_id=None) -> None:
        super().__init__(spec, x, y, rng, spawn_id, hit_radius=config.NETTLE_HIT_RADIUS)
        self.shots = config.NETTLE_SHOTS
        self.decoys: list[Glamour] = []
        self.decoy_t = config.DECOY_EVERY * 0.5
        self.clouds: list[list[float]] = []     # [x, y, age]
        self.in_cloud: dict[int, float] = {}    # hero id -> s in a cloud
        self.spent: dict[int, float] = {}       # growcap -> s before it regrows
        self.grow_t: dict[int, float] = {}      # growcap -> s a tiny hero has stood on it
        self.seeds: list[list[float]] = []      # [x, y, age, pulled s]
        self.falling: list[tuple] = []          # seeds about to land (the tell): (x, y)
        self.blight_t = config.BLIGHT_EVERY
        self.blight_hit: dict[int, float] = {}  # hero id -> s toward the next blight tick
        self.healing = False                    # over the blight (drawing, the bar)
        self.homers: list[list] = []            # [x, y, angle, speed, turn, life, damage, look, hit]
        self.gather: list[list[float]] = []     # wisps drifting in (the tell): [x, y]
        self.cracks: list[tuple] = []           # thorn lines' tell: (x, y)
        self.bursts: list[list] = []            # thorns to come: [x, y, s until, hit set]
        self.spikes: list[list[float]] = []     # thorns out (drawing): [x, y, age]
        self.shadows: list[tuple] = []          # nettle rain's tell: (x, y)
        self.dashing = False
        self.circle_dir = 1
        self.circle_t = 0.0
        self.shimmer = 0.0                      # drawing: the split's flash

    # --- Helpers ------------------------------------------------------------------------

    @property
    def props(self) -> dict:
        return self.lair.props if self.lair is not None else {}

    def _air(self, x: float, y: float) -> bool:
        """Somewhere she can fly: anywhere in the glade (over toadstools)."""
        return self.lair is None or self.lair.inside(x, y, 1.5)

    def _solid(self, x: float, y: float) -> bool:
        t = self.ctx.world.tile_at(math.floor(x), math.floor(y))
        return t is not None and t.solid

    def _set(self, x: float, y: float, tile) -> None:
        world = self.ctx.world
        if hasattr(world, "set_tile"):
            world.set_tile(math.floor(x), math.floor(y), tile)

    def emitters(self) -> list:
        """Who casts her spirals and sparks: her, and her copies."""
        return [self] + [d for d in self.decoys if d.alive]

    def _hit(self, h, damage: float, angle) -> float:
        """One of her hits; a tiny hero is knocked about by it."""
        dealt = combat.strike(h, damage * self.damage_mult, self, angle, self.ctx.effects)
        if dealt:
            self.on_shot_hit(h, dealt, angle)
        return dealt or 0.0

    def on_shot_hit(self, victim, dealt: float, angle=None) -> None:
        if getattr(victim, "shrunk", 0) <= 0 or not dealt:
            return
        if angle is None:
            angle = math.atan2(victim.y - self.y, victim.x - self.x)
        push = config.SHRINK[3]
        combat.push(victim, self.ctx.world, math.cos(angle) * push, math.sin(angle) * push)

    def _fly(self, body, t, dt: float, mult: float, way: int) -> int:
        """One step of circling hero `t` at NETTLE_ORBIT's distance (bent
        out when too close, in when too far), staying in the glade. Returns
        the way round (turned about when the way is blocked)."""
        near, far, _, speed, _ = config.NETTLE_ORBIT
        d = math.hypot(t.x - body.x, t.y - body.y)
        out = math.atan2(body.y - t.y, body.x - t.x)
        bend = 0.8 if d < near else (-0.8 if d > far else 0.0)
        a = out + way * (math.pi / 2 - bend)
        step = speed * mult * dt
        for turn in (0.0, 0.5, -0.5, 1.0, -1.0):
            nx, ny = body.x + math.cos(a + turn) * step, body.y + math.sin(a + turn) * step
            if self._air(nx, ny):
                body.walked = getattr(body, "walked", 0.0) + step
                body.x, body.y = nx, ny
                body.facing = math.atan2(t.y - ny, t.x - nx)
                return way
        return -way

    def shove_heroes(self, extra: float = 0.3) -> None:
        pass                                    # (she flies: nothing to bump into)

    def _drink(self, seed, dt: float) -> None:
        """Phase 3, between moves: she flies to a rot seed's patch and hovers
        over it, drinking (healing)."""
        dx, dy = seed[0] - self.x, seed[1] - self.y
        d = math.hypot(dx, dy)
        if d < 1.0:
            return
        step = min(d, config.NETTLE_ORBIT[3] * 1.3 * dt)
        self.x += dx / d * step
        self.y += dy / d * step
        self.walked += step

    def _spread(self, dt: float) -> None:
        """Her and her copies drift apart (DECOY_SPREAD x 0.6 tiles at the
        least), so they don't bunch up on the same ring round you."""
        bodies = self.emitters()
        gap = config.DECOY_SPREAD * 0.6
        for i, p in enumerate(bodies):
            for q in bodies[i + 1:]:
                dx, dy = q.x - p.x, q.y - p.y
                d = math.hypot(dx, dy)
                if d >= gap:
                    continue
                if d < 1e-6:
                    dx, dy, d = 1.0, 0.0, 1.0
                k = config.NETTLE_ORBIT[3] * dt * 0.5
                for body, sgn in ((p, -1), (q, 1)):
                    nx, ny = body.x + sgn * dx / d * k, body.y + sgn * dy / d * k
                    if self._air(nx, ny):
                        body.x, body.y = nx, ny

    # --- Every step ---------------------------------------------------------------------

    def think(self, ctx: AIContext, dt: float) -> None:
        self.ctx = ctx
        self.shimmer = max(0.0, self.shimmer - dt)
        self._tick_decoys(dt)
        self._tick_clouds(dt)
        self._tick_growcaps(dt)
        self._tick_blight(dt)
        self._tick_homers(dt)
        self._tick_bursts(dt)
        g = self.drift_target()
        if g is not None and self.dazed <= 0 and not self.dashing:
            self.circle_t -= dt
            if self.circle_t <= 0:
                self.circle_dir = -self.circle_dir
                self.circle_t = self.rng.uniform(*config.NETTLE_ORBIT[2])
            mult = 1.0 if self._gen is None else config.NETTLE_ORBIT[4]
            seed = min(self.seeds, key=lambda s: math.hypot(s[0] - self.x, s[1] - self.y),
                       default=None)
            if self._gen is None and seed is not None:
                self._drink(seed, dt)              # between moves: back to the blight
            else:
                self.circle_dir = self._fly(self, g, dt, mult, self.circle_dir)
            self.facing = math.atan2(g.y - self.y, g.x - self.x)
            for d in self.decoys:
                if d.alive:
                    d.dir = self._fly(d, g, dt, mult, d.dir)
            self._spread(dt)
        self.decoy_t -= dt                          # (her signatures' timers run on
        if self.phase >= 2:                         # through her moves; each starts
            self.blight_t -= dt                     # once she's free)
        if self._gen is None and self.dazed <= 0:
            if self.decoy_t <= 0:
                self.decoy_t = config.DECOY_EVERY
                self._start("glamour")
            elif self.phase >= 2 and self.blight_t <= 0:
                self.blight_t = config.BLIGHT_EVERY
                self._start("seeds")
        super().think(ctx, dt)

    def on_phase(self, phase: int, ctx: AIContext) -> None:
        label = ("HER DUST... YOU FEEL SMALL", "THE ROT SPREADS!")[min(phase, 2) - 1] \
            if phase else ""
        if label:
            ctx.effects.append(Effect("toast", self.x, self.y - 3, label=label))

    def _end_move(self) -> None:
        super()._end_move()
        self.dashing = False
        self.cracks = []
        self.shadows = []
        self.gather = []
        self.falling = []

    def _tick_decoys(self, dt: float) -> None:
        """Copies age; one popped (hit) bursts into a ring of dust; one too
        old fades."""
        keep = []
        for d in self.decoys:
            d.age += dt
            if not d.alive:
                if not d.faded:
                    self.ctx.effects.append(Effect("nova", d.x, d.y, size=2.0))
                    self.ctx.effects.append(Effect("toast", d.x, d.y - 2, label="POP!"))
                    patterns.radial(self, d.x, d.y, config.DECOY_POP, self.shots["pop"],
                                    self.ctx.projectiles, self.rng.uniform(0, math.tau))
                    self.ctx.events.append("fizzle")
                continue
            if d.age >= config.DECOY_LIFE:
                d.faded = True
                d.hp = 0.0
                continue
            keep.append(d)
        self.decoys = keep

    def _tick_clouds(self, dt: float) -> None:
        """Dust clouds drift out of life; a hero DUST_SHRINK s in one shrinks."""
        life, radius = config.NETTLE_DUST[3], config.NETTLE_DUST[2]
        for c in self.clouds:
            c[2] += dt
        self.clouds = [c for c in self.clouds if c[2] < life]
        for h in self.ctx.players:
            if not h.alive or not self.in_arena(h):
                continue
            inside = not h.rolling and any(math.hypot(h.x - c[0], h.y - c[1]) <= radius
                                           for c in self.clouds)
            if not inside:
                self.in_cloud.pop(id(h), None)
                continue
            self.in_cloud[id(h)] = self.in_cloud.get(id(h), 0.0) + dt
            if self.in_cloud[id(h)] >= config.DUST_SHRINK and h.shrunk <= 0:
                h.shrunk = config.SHRINK[0]
                self.ctx.effects.append(Effect("toast", h.x, h.y - 2, label="YOU SHRINK!"))
                self.ctx.events.append("fizzle")

    def _tick_growcaps(self, dt: float) -> None:
        """Shrinking wears off; a tiny hero GROWCAP_TIME s on a growcap grows
        back (the growcap's spent, and regrows GROWCAP_REGROW s on)."""
        from ..world import tiles
        for h in self.ctx.players:
            if h.shrunk > 0 and self.in_arena(h):
                h.shrunk = max(0.0, h.shrunk - dt)
        for i in list(self.spent):
            self.spent[i] -= dt
            if self.spent[i] <= 0:
                self.spent.pop(i)
                self._set(*self.props["growcaps"][i], tiles.GROWCAP)
        for i, (gx, gy) in enumerate(self.props.get("growcaps", [])):
            if i in self.spent:
                continue
            tiny = [h for h in self.ctx.players if h.alive and h.shrunk > 0
                    and math.hypot(h.x - gx, h.y - gy) <= config.GROWCAP_REACH]
            if not tiny:
                self.grow_t.pop(i, None)
                continue
            self.grow_t[i] = self.grow_t.get(i, 0.0) + dt
            if self.grow_t[i] >= config.GROWCAP_TIME:
                self.grow_t.pop(i)
                for h in tiny:
                    h.shrunk = 0.0
                self.spent[i] = config.GROWCAP_REGROW
                self._set(gx, gy, tiles.GROWCAP_SPENT)
                self.ctx.effects.append(Effect("toast", gx, gy - 2, label="BACK TO SIZE!"))
                self.ctx.events.append("chime")

    def seed_radius(self, seed) -> float:
        return config.BLIGHT_RADIUS * min(1.0, seed[2] / config.BLIGHT_GROW)

    def on_blight(self, x: float, y: float) -> bool:
        return any(math.hypot(x - s[0], y - s[1]) <= self.seed_radius(s) for s in self.seeds)

    def _tick_blight(self, dt: float) -> None:
        """Patches spread; heroes on one are hurt each BLIGHT_TICK; she heals
        over one; a hero at a seed BLIGHT_PULL s pulls it."""
        for s in self.seeds:
            s[2] += dt
        for h in self.ctx.players:
            if not h.alive or not self.in_arena(h):
                continue
            if self.on_blight(h.x, h.y):
                t = self.blight_hit.get(id(h), 0.0) - dt
                if t <= 0:
                    t = config.BLIGHT_TICK
                    self._hit(h, config.BLIGHT_DAMAGE, None)
                self.blight_hit[id(h)] = t
            else:
                self.blight_hit.pop(id(h), None)
        keep = []
        for s in self.seeds:
            by = any(h.alive and math.hypot(h.x - s[0], h.y - s[1]) <= config.BLIGHT_REACH
                     for h in self.ctx.players)
            s[3] = s[3] + dt if by else 0.0
            if s[3] >= config.BLIGHT_PULL:
                self.ctx.effects.append(Effect("toast", s[0], s[1] - 2, label="PULLED!"))
                self.ctx.effects.append(Effect("nova", s[0], s[1], size=2.0))
                self.ctx.events.append("chime")
                continue
            keep.append(s)
        self.seeds = keep
        self.healing = self.alive and self.on_blight(self.x, self.y)
        if self.healing:
            self.hp = min(float(self.max_hp), self.hp + config.BLIGHT_HEAL * dt)

    def _tick_homers(self, dt: float) -> None:
        """Hex sparks and flung wisps: they turn toward the nearest hero in
        the glade, and hit once."""
        keep = []
        heroes = [h for h in self.ctx.players if h.alive and self.in_arena(h)]
        for m in self.homers:
            x, y, a, speed, turn, life, damage, look, hit = m
            life -= dt
            if life <= 0 or hit:
                continue
            t = min(heroes, key=lambda h: math.hypot(h.x - x, h.y - y), default=None)
            if t is not None:
                want = math.atan2(t.y - y, t.x - x)
                diff = (want - a + math.pi) % math.tau - math.pi
                a += max(-turn * dt, min(turn * dt, diff))
            x, y = x + math.cos(a) * speed * dt, y + math.sin(a) * speed * dt
            if self._solid(x, y) or not self._air(x, y):
                self.ctx.effects.append(Effect("impact", x, y))
                continue
            for h in heroes:
                if h.hittable and math.hypot(h.x - x, h.y - y) <= 0.6 + h.hit_radius:
                    self._hit(h, damage, a)
                    self.ctx.effects.append(Effect("impact", x, y))
                    hit = True
                    break
            if not hit:
                keep.append([x, y, a, speed, turn, life, damage, look, False])
        self.homers = keep

    def _tick_bursts(self, dt: float) -> None:
        """Thorns bursting along their lines, one after another."""
        radius, damage = config.NETTLE_THORNS[5], config.NETTLE_THORNS[6]
        keep = []
        for b in self.bursts:
            b[2] -= dt
            if b[2] > 0:
                keep.append(b)
                continue
            self.spikes.append([b[0], b[1], 0.0])
            for h in self.ctx.players:
                if h.hittable and math.hypot(h.x - b[0], h.y - b[1]) <= radius + h.hit_radius:
                    self._hit(h, damage, None)
        self.bursts = keep
        for s in self.spikes:
            s[2] += dt
        self.spikes = [s for s in self.spikes if s[2] < 0.6]

    # --- The bar, the map ---------------------------------------------------------------

    @property
    def bar_label(self) -> str:
        if self.healing:
            return "SHE DRINKS THE BLIGHT - PULL THE SEEDS!"
        n = sum(1 for d in self.decoys if d.alive)
        if n:
            return f"{self.espec.name} - {n + 1} OF HER"
        return self.espec.name

    def map_marks(self) -> list[tuple[float, float, str, str]]:
        """Map pins: growcaps ready to eat, rot seeds to pull."""
        out = [(x, y, "growcap", "GROWCAP")
               for i, (x, y) in enumerate(self.props.get("growcaps", [])) if i not in self.spent]
        out += [(s[0], s[1], "seed", "SEED") for s in self.seeds]
        return out

    def on_death(self, ctx: AIContext) -> None:
        self.ctx = ctx
        for d in self.decoys:
            d.faded = True
            d.hp = 0.0
        self.decoys = []
        self.clouds, self.seeds, self.homers, self.bursts = [], [], [], []
        for h in ctx.players:
            if self.in_arena(h):
                h.shrunk = 0.0
        ctx.effects.append(Effect("explosion", self.x, self.y))
        ctx.effects.append(Effect("nova", self.x, self.y, size=4.0))

    # --- Moves --------------------------------------------------------------------------

    def m_glamour(self):
        """Signature 1: she shimmers (the tell), then splits -- copies all
        round, and she may be any of them."""
        self.tell = ("shimmer",)
        yield self.tell_s(config.DECOY_TELL)
        self.tell = None
        want = config.DECOYS[min(self.phase, len(config.DECOYS) - 1)]
        n = want - sum(1 for d in self.decoys if d.alive)
        if n <= 0 or self.recruit is None:
            return
        spots = [(self.x, self.y)]
        for _ in range(n):
            for _ in range(20):
                a = self.rng.uniform(0, math.tau)
                r = self.rng.uniform(config.DECOY_SPREAD * 0.5, config.DECOY_SPREAD)
                x, y = self.x + math.cos(a) * r, self.y + math.sin(a) * r
                if self._air(x, y):
                    spots.append((x, y))
                    break
        self.rng.shuffle(spots)
        self.x, self.y = spots[0]
        for x, y in spots[1:]:
            d = self.recruit("glamour", x, y)
            if d is None:
                continue
            d.part_of = self
            d.facing = self.facing
            self.decoys.append(d)
        for x, y in spots:
            self.ctx.effects.append(Effect("nova", x, y, size=2.0))
        self.shimmer = 0.4
        self.ctx.events.append("orb")
        yield 0.3

    def m_spiral(self):
        """P2: arms of glitter turning out from her (and every copy)."""
        tell, arms, dur, every, turn = config.NETTLE_SPIRAL
        self.tell = ("cast",)
        yield self.tell_s(tell)
        self.tell = None
        base = self.rng.uniform(0, math.tau)
        way = self.rng.choice((-1, 1))
        tt, k = 0.0, 0
        while tt < dur:
            if self.room_for_shots():
                for j, e in enumerate(self.emitters()):
                    if e is not self and (k + j) % round(1 / config.DECOY_SHARE):
                        continue
                    for arm in range(arms):
                        a = base + arm * math.tau / arms + j * 0.7
                        patterns.shoot(self, e.x, e.y, a, self.shots["glitter"],
                                       self.ctx.projectiles)
            base += way * turn * every
            tt += every
            k += 1
            yield every

    def m_sparks(self):
        """P1: hex sparks fanned at you; they curve after you."""
        tell, n, speed, turn, life, damage, fan = config.NETTLE_SPARKS
        self.tell = ("cast",)
        yield self.tell_s(tell)
        self.tell = None
        t = self.target_now()
        if t is None:
            return
        for e in self.emitters():
            count = n if e is self else max(1, round(n * config.DECOY_SHARE))
            a0 = math.atan2(t.y - e.y, t.x - e.x)
            for i in range(count):
                a = a0 + math.radians(fan) * ((i + 0.5) / count - 0.5)
                self.homers.append([e.x, e.y, a, speed, turn, life, damage, "spark", False])
        self.ctx.events.append("hex")
        yield 0.3

    def m_thorns(self):
        """P4: the ground cracks in lines toward you (the tell), then thorns
        burst along them, one after another, out from her."""
        tell, lines, length, spacing, gap, _, _, spread = config.NETTLE_THORNS
        t = self.target_now()
        if t is None:
            return
        a0 = math.atan2(t.y - self.y, t.x - self.x)
        pts = []
        for k in range(lines):
            a = a0 + math.radians(spread) * (k - (lines - 1) / 2)
            d = 2.0
            while d <= length:
                x, y = self.x + math.cos(a) * d, self.y + math.sin(a) * d
                if self._air(x, y):
                    pts.append((x, y, d))
                d += spacing
        self.cracks = [(x, y) for x, y, _ in pts]
        self.tell = ("cracks",)
        yield self.tell_s(tell)
        self.tell = None
        self.cracks = []
        for x, y, d in pts:
            self.bursts.append([x, y, d / spacing * gap, set()])
        self.ctx.events.append("boulder")
        yield length / spacing * gap

    def m_cage(self):
        """P5 with a gap: a ring of brambles round you, hanging a moment,
        then closing in."""
        tell, n, radius, hold, gap = config.NETTLE_CAGE
        self.tell = ("cast",)
        yield self.tell_s(tell)
        self.tell = None
        t = self.target_now()
        if t is None:
            return
        patterns.ring_in(self, t.x, t.y, radius, n, self.shots["thorn"], self.ctx.projectiles,
                         hold, gap_deg=gap, gap_at=self.rng.uniform(0, math.tau))
        self.ctx.events.append("orb")
        yield 0.3

    def m_moths(self):
        """She calls rot moths (no more than NETTLE_MOTHS[2] out)."""
        tell, n, most = config.NETTLE_MOTHS
        self.tell = ("call",)
        yield self.tell_s(tell)
        self.tell = None
        alive = sum(1 for a in self.ctx.actors if getattr(a, "summoner", None) is self and a.alive)
        for _ in range(min(n, most - alive)):
            if self.recruit is None:
                break
            a = self.rng.uniform(0, math.tau)
            x, y = self.clamp_to_lair(self.x + math.cos(a) * 3, self.y + math.sin(a) * 3, 3.0)
            add = self.recruit("rot_moth", x, y)
            if add is not None:
                add.summoner = self
                add.alert = True
        self.ctx.events.append("orb")
        yield 0.3

    def m_dive(self):
        """B1: dotted lines (the tell), then she zips along them; from phase
        2 her trail leaves shrinking dust."""
        tell, dives, speed, longest, damage, width, trail = config.NETTLE_DIVE
        for _ in range(dives):
            t = self.target_now()
            if t is None:
                return
            wait = self.tell_s(tell)
            tx, ty = self.lead(t, self.x, self.y, secs=wait)
            a = math.atan2(ty - self.y, tx - self.x)
            length = min(longest, math.hypot(tx - self.x, ty - self.y) + 6.0)
            x1, y1 = self.clamp_to_lair(self.x + math.cos(a) * length,
                                        self.y + math.sin(a) * length, 3.0)
            self.facing = a
            self.tell = ("dive", self.x, self.y, x1, y1)
            self.dashing = True                    # (held on the line she's shown you)
            yield wait
            self.tell = None
            self.ctx.events.append("swing")
            x0, y0 = self.x, self.y
            total = math.hypot(x1 - x0, y1 - y0) or 1.0
            gone, dropped = 0.0, 0.0
            hit = set()
            while gone < total:
                gone = min(total, gone + speed * self.dt)
                self.x = x0 + (x1 - x0) * gone / total
                self.y = y0 + (y1 - y0) * gone / total
                if self.phase >= 1 and gone - dropped >= trail:
                    dropped = gone
                    self.clouds.append([self.x, self.y, 0.0])
                for h in self.ctx.players:
                    if h.hittable and id(h) not in hit and \
                            math.hypot(h.x - self.x, h.y - self.y) <= width + h.hit_radius:
                        hit.add(id(h))
                        self._hit(h, damage, a)
                yield 0
            self.dashing = False
            yield 0.25

    def m_wisps(self):
        """The forest's wisps drift in to her (the tell), and she flings
        them at you; they home."""
        tell, n, speed, turn, life, damage, far = config.NETTLE_WISPS
        self.gather = []
        for k in range(n):
            a = k * math.tau / n + self.rng.uniform(-0.3, 0.3)
            self.gather.append([self.x + math.cos(a) * far, self.y + math.sin(a) * far])
        self.tell = ("gather",)
        wait = self.tell_s(tell)
        tt = 0.0
        while tt < wait:
            k = min(1.0, self.dt / max(0.05, wait - tt))
            for w in self.gather:
                w[0] += (self.x - w[0]) * k
                w[1] += (self.y - w[1]) * k
            tt += self.dt
            yield 0
        self.tell = None
        self.gather = []
        t = self.target_now()
        if t is None:
            return
        a0 = math.atan2(t.y - self.y, t.x - self.x)
        for k in range(n):
            a = a0 + (k - (n - 1) / 2) * 0.5
            self.homers.append([self.x, self.y, a, speed, turn, life, damage, "wisp", False])
        self.ctx.events.append("orb")
        yield 0.3

    def m_nettles(self):
        """P8: blinking shadows (one on you), then nettles fall on them."""
        tell, n, radius, damage, spread = config.NETTLE_NETTLES
        t = self.target_now()
        if t is None:
            return
        spots = [(t.x, t.y)]
        for _ in range(n - 1):
            a = self.rng.uniform(0, math.tau)
            r = self.rng.uniform(2.0, spread)
            spots.append(self.clamp_to_lair(t.x + math.cos(a) * r, t.y + math.sin(a) * r, 3.0))
        self.shadows = spots
        self.tell = ("nettles",)
        yield self.tell_s(tell)
        self.tell = None
        self.shadows = []
        for x, y in spots:
            for h in self.ctx.players:
                if h.hittable and math.hypot(h.x - x, h.y - y) <= radius + h.hit_radius:
                    self._hit(h, damage, None)
            self.spikes.append([x, y, 0.0])
        self.ctx.events.append("boulder")
        yield 0.3

    def m_dust(self):
        """Signature 2 (phase 2+): she flings glittering dust: clouds on and
        round you that shrink whoever lingers in them."""
        tell, n, _, _ = config.NETTLE_DUST
        self.tell = ("cast",)
        yield self.tell_s(tell)
        self.tell = None
        t = self.target_now()
        if t is None:
            return
        x, y = self.lead(t, self.x, self.y, secs=0.6)
        self.clouds.append([x, y, 0.0])
        for _ in range(n - 1):
            a = self.rng.uniform(0, math.tau)
            r = self.rng.uniform(4.0, 7.0)
            self.clouds.append([*self.clamp_to_lair(x + math.cos(a) * r, y + math.sin(a) * r, 3.0),
                                0.0])
        self.ctx.events.append("fizzle")
        yield 0.3

    def m_seeds(self):
        """Signature 3 (phase 3): rot seeds fall (the tell: where they'll
        land), then take root and the blight spreads."""
        room = config.BLIGHT_MAX - len(self.seeds)
        if room <= 0:
            return
        t = self.target_now()
        spots = []
        for k in range(min(room, config.BLIGHT_SEEDS)):
            if k == 0 and t is not None:
                a = self.rng.uniform(0, math.tau)
                x, y = t.x + math.cos(a) * 3.0, t.y + math.sin(a) * 3.0
            else:
                lair = self.lair
                cx, cy = (lair.cx, lair.cy) if lair is not None else (self.x, self.y)
                x, y = cx + self.rng.uniform(-0.6, 0.6) * (lair.radii[0] if lair else 30), \
                    cy + self.rng.uniform(-0.6, 0.6) * (lair.radii[1] if lair else 15)
            spots.append(self.clamp_to_lair(x, y, 4.0))
        self.falling = spots
        self.tell = ("seeds",)
        yield self.tell_s(config.BLIGHT_TELL)
        self.tell = None
        self.falling = []
        for x, y in spots:
            self.seeds.append([x, y, 0.0, 0.0])
            self.ctx.effects.append(Effect("nova", x, y, size=1.5))
        self.ctx.events.append("hex")
        yield 0.2
