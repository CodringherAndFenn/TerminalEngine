"""
ai/ruins.py -- the ruins' new enemies (P10, design/BOSSES.md 24.8).

Letter-art creatures on the plains' base (ai/plains.PlainsCreature), drawn
by render/plains.py with their tells from render/ruins.py.

  gnolls (packs), stone imps, crawling hands (swarms), lost soldiers:
                  simple chasers
  gargoyle        perches until you come near; swoops; then sits as stone a
                  moment (nothing hurts it), and swoops again
  clockwork sentry stops, winds its key, sweeps five bolts across you
  colossus (elite) slow; its stomp rolls a ring out along the ground
  rubble crab     a shell of rubble takes the hits first; bare, it panics
                  and runs
  gem thief       goes for the heroes' XP gems, not the heroes; kill it and
                  they spill back out, let it get away and they're gone
  crossbow sniper keeps far back; a long aiming line, then a bolt through
                  everything in it
  flail brute (elite) a spinning flail whose ring grows as he winds up; then
                  he throws it along a line and has to pull it back
  rune mine       drifts at you; in its ring it glows, then blows
  haunted blades  three swords circling you, thrusting one at a time (the
                  hounds' pack rules, flying)
  bell ghost      keeps away and rings: wakes every enemy around, and the
                  toll knocks heroes back
"""

from __future__ import annotations

import math

from .. import config
from ..entities.effects import Effect
from ..entities.projectile import Projectile
from ..systems import combat
from .brain import AIContext
from .creatures import _numbered_hit
from .desert import _on_line, _reach
from .forest import _keep_range, _roam, _vanish
from .plains import Chaser, Hound, PlainsCreature


class Gargoyle(PlainsCreature):
    """Perches where it was put until a hero comes within GARGOYLE[0] (it
    can be seen and shot there); then lines up (the windup; the line
    shows) and dives GARGOYLE[1] tiles at GARGOYLE[2] tiles/s, over
    everything, hitting the first body it meets. After a dive it sits as
    stone for GARGOYLE[3] s: nothing hurts it. Then it dives again."""

    flies = True

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.state = "perch"
        self.timer = 0.0
        self.aim = 0.0
        self.dived = 0.0
        self.struck = False

    @property
    def stone(self) -> bool:
        return self.state == "stone"

    def sprite_now(self) -> str:
        return "gargoyle_stone" if self.stone else "gargoyle"

    def can_see(self, world, other) -> bool:
        return math.hypot(other.x - self.x, other.y - self.y) <= self.espec.sight

    def take_damage(self, amount, source, from_angle):
        if self.stone:
            return 0.0
        return super().take_damage(amount, source, from_angle)

    def think(self, ctx: AIContext, dt: float) -> None:
        super().think(ctx, dt)
        self.sense(ctx, dt)
        wake, length, speed, stone = config.GARGOYLE
        t = self.target
        if self.state == "perch":
            if t is not None and self.dist_to(t) <= wake:
                self._line_up(t)
            return
        if self.state == "mark":
            self.timer -= dt
            self.tell = self.timer
            if self.timer <= 0:
                self.state, self.dived, self.struck, self.tell = "dive", 0.0, False, 0.0
            return
        if self.state == "dive":
            step = speed * dt
            self.x += math.cos(self.aim) * step
            self.y += math.sin(self.aim) * step
            self._moved = step
            self.walked += step
            self.dived += step
            if not self.struck:
                for a in ctx.actors:
                    if a is not self and a.hittable and \
                            math.hypot(a.x - self.x, a.y - self.y) <= self.hit_radius + a.hit_radius:
                        _numbered_hit(a, self.espec.damage * self.damage_mult, self, self.aim, ctx)
                        self.struck = True
                        break
            if self.dived >= length:
                self.state, self.timer = "stone", stone
            return
        if self.state == "stone":
            self.timer -= dt
            if self.timer <= 0:
                if t is not None and self.sees_target:
                    self._line_up(t)
                else:
                    self.state = "perch"

    def _line_up(self, t) -> None:
        self.state, self.timer = "mark", self.espec.windup
        self.aim = self.facing = self.angle_to(t.x, t.y)


class Clockwork(PlainsCreature):
    """Walks to mid range; every cooldown it stops, winds its key (the
    windup) and sweeps CLOCK_SWEEP[0] bolts across its target, over
    CLOCK_SWEEP[1] degrees, CLOCK_SWEEP[2] s apart."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.timer = self.rng.uniform(1.0, self.espec.cooldown)
        self.sweep: list | None = None           # [next bolt, its angle, angle step, s to it]

    def think(self, ctx: AIContext, dt: float) -> None:
        super().think(ctx, dt)
        self.sense(ctx, dt)
        n, spread, gap = config.CLOCK_SWEEP
        t = self.target
        if self.sweep is not None:
            self.sweep[3] -= dt
            if self.sweep[3] <= 0:
                k, a, da, _ = self.sweep
                shell = config.WEAPONS["clock_bolts"].shell
                ctx.projectiles.append(Projectile(self.x, self.y, a, shell, owner=self,
                                                  damage=shell.damage * self.damage_mult))
                ctx.events.append(shell.sound)
                self.sweep = [k + 1, a + da, da, gap] if k + 1 < n else None
            return
        if self.windup > 0:
            self.windup -= dt
            self.tell = self.windup
            if self.windup <= 0:
                self.tell = 0.0
                if t is not None:
                    half = math.radians(spread) / 2
                    side = self.rng.choice((-1, 1))
                    a0 = self.angle_to(t.x, t.y) - side * half
                    self.sweep = [0, a0, side * 2 * half / (n - 1), 0.0]
            return
        if t is None or not self.sees_target:
            _roam(self, ctx, dt)
            return
        _keep_range(self, ctx, t, 6.0, 10.0, dt)
        self.timer -= dt
        if self.timer <= 0:
            self.timer = self.espec.cooldown
            self.windup = self.espec.windup


class Colossus(PlainsCreature):
    """Elite. Walks you down slowly. Within attack_radius it raises a foot
    (the windup) and stomps: a ring rolls out along the ground to
    COLOSSUS_RING[0] tiles at COLOSSUS_RING[1] tiles/s, COLOSSUS_RING[2]
    thick, hitting each body it passes once (a roll's i-frames get you
    through it)."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.rings: list[list] = []              # [radius, ids already hit]

    def think(self, ctx: AIContext, dt: float) -> None:
        super().think(ctx, dt)
        self.sense(ctx, dt)
        reach, speed, thick = config.COLOSSUS_RING
        for ring in self.rings:
            ring[0] += speed * dt
            for a in ctx.actors:
                if a is self or not a.hittable or id(a) in ring[1]:
                    continue
                d = math.hypot(a.x - self.x, a.y - self.y)
                if abs(d - ring[0]) <= thick / 2 + a.hit_radius:
                    ring[1].add(id(a))
                    _numbered_hit(a, self.espec.damage * self.damage_mult, self,
                                  math.atan2(a.y - self.y, a.x - self.x), ctx)
        self.rings = [r for r in self.rings if r[0] < reach]
        if self.windup > 0:
            self.windup -= dt
            self.tell = self.windup
            if self.windup <= 0:
                self.tell = 0.0
                self.rings.append([0.5, set()])
                ctx.effects.append(Effect("debris", self.x, self.y + 0.8))
                ctx.events.append(combat.BREAK)
                self.cooldown = self.espec.cooldown
            return
        t = self.target
        if t is None or not self.sees_target:
            _roam(self, ctx, dt)
            return
        if self.dist_to(t) <= self.espec.attack_radius and self.cooldown <= 0:
            self.windup = self.espec.windup
            return
        self.go(ctx, t.x, t.y, dt, self.espec.speed)


class RubbleCrab(Chaser):
    """A chaser in a shell of rubble: CRAB_SHELL[0] HP of shell take the
    hits first. Bare, it panics: runs from its target at CRAB_SHELL[1]
    tiles/s, and only bites if cornered."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.shell = float(config.CRAB_SHELL[0])

    def sprite_now(self) -> str:
        return "rubble_crab" if self.shell > 0 else "crab_bare"

    def take_damage(self, amount, source, from_angle):
        if self.shell > 0 and amount > 0:
            took = min(self.shell, amount)
            self.shell -= took
            self.hurt_flash = 0.12
            if self.shell <= 0:
                self.alert = True
            return took
        return super().take_damage(amount, source, from_angle)

    def think(self, ctx: AIContext, dt: float) -> None:
        if self.shell > 0:
            super().think(ctx, dt)
            return
        PlainsCreature.think(self, ctx, dt)
        self.sense(ctx, dt)
        t = self.target
        if t is None:
            return
        a = self.angle_to(t.x, t.y) + math.pi
        self.go(ctx, self.x + math.cos(a) * 3, self.y + math.sin(a) * 3, dt,
                config.CRAB_SHELL[1])


class GemThief(PlainsCreature):
    """Pays heroes no mind: goes for the nearest XP gem within THIEF[0]
    tiles and scoops it (within THIEF[1]). With some in its sack and none
    left near, it runs from the heroes; once THIEF[2] tiles from all of
    them after THIEF[3] s running, it's gone with the lot. Killed, it
    spills them back out."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.sack = 0.0
        self.running = 0.0
        self.escaped = False

    def think(self, ctx: AIContext, dt: float) -> None:
        super().think(ctx, dt)
        look, scoop, gone, after = config.THIEF
        gems = [g for g in (ctx.gems or ()) if g.alive and g.target is None
                and math.hypot(g.x - self.x, g.y - self.y) <= look]
        if gems:
            g = min(gems, key=lambda g: math.hypot(g.x - self.x, g.y - self.y))
            if math.hypot(g.x - self.x, g.y - self.y) <= scoop:
                g.alive = False
                self.sack += g.value
            else:
                self.go(ctx, g.x, g.y, dt, self.espec.speed)
            self.running = 0.0
            return
        heroes = [h for h in ctx.players if h.alive]
        if not heroes:
            return
        near = min(heroes, key=lambda h: math.hypot(h.x - self.x, h.y - self.y))
        d = math.hypot(near.x - self.x, near.y - self.y)
        if self.sack <= 0:
            if d < 6:                                     # (nothing to steal: keeps clear)
                a = math.atan2(self.y - near.y, self.x - near.x)
                self.go(ctx, self.x + math.cos(a) * 3, self.y + math.sin(a) * 3, dt,
                        self.espec.speed * 0.7)
            else:
                self.go(ctx, *self.wander_goal(dt), dt, self.espec.speed * 0.4)
            return
        self.running += dt
        a = math.atan2(self.y - near.y, self.x - near.x)
        self.go(ctx, self.x + math.cos(a) * 4, self.y + math.sin(a) * 4, dt, self.espec.speed)
        if self.running >= after and d >= gone:
            self.escaped = True
            _vanish(self)

    def on_death(self, ctx: AIContext) -> None:
        if self.escaped:
            ctx.effects.append(Effect("toast", self.x, self.y - 1.5, label="GONE WITH THE GEMS"))
            return
        ctx.effects.append(Effect("explosion", self.x, self.y))
        if self.sack > 0 and ctx.gems is not None:
            from ..entities.gems import drop
            for k in range(min(6, max(1, int(self.sack // 5)))):   # (spilled in a few)
                a = k * 1.1
                drop(ctx.gems, self.x + math.cos(a) * 0.8, self.y + math.sin(a) * 0.8,
                     self.sack / min(6, max(1, int(self.sack // 5))))


class Sniper(PlainsCreature):
    """Keeps SNIPER[0]-SNIPER[1] tiles back. Every cooldown it kneels and
    aims (the windup; the line shows and follows you until SNIPER[2] s
    before the shot), then looses a heavy bolt that goes through
    everything in its line."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.aim = 0.0
        self.timer = self.rng.uniform(1.5, self.espec.cooldown)

    def think(self, ctx: AIContext, dt: float) -> None:
        super().think(ctx, dt)
        self.sense(ctx, dt)
        lo, hi, lock = config.SNIPER
        t = self.target
        if self.windup > 0:
            self.windup -= dt
            self.tell = self.windup
            if t is not None and self.windup > lock:
                self.aim = self.facing = self.angle_to(t.x, t.y)
            if self.windup <= 0:
                self.tell = 0.0
                shell = config.WEAPONS["heavy_bolt"].shell
                ctx.projectiles.append(Projectile(self.x, self.y, self.aim, shell, owner=self,
                                                  damage=shell.damage * self.damage_mult))
                ctx.events.append(shell.sound)
            return
        if t is None or not self.sees_target:
            _roam(self, ctx, dt)
            return
        _keep_range(self, ctx, t, lo, hi, dt)
        self.timer -= dt
        if self.timer <= 0:
            self.timer = self.espec.cooldown
            self.windup = self.espec.windup
            self.aim = self.angle_to(t.x, t.y)


class FlailBrute(PlainsCreature):
    """Elite. Within attack_radius he starts spinning: a ring from
    FLAIL[0] out to FLAIL[1] tiles as he winds up (the windup), hitting
    whatever is on it every FLAIL[2] s (inside it you're safe). Then he
    throws the flail FLAIL[3] tiles along a line (to a wall) for FLAIL[4],
    and takes FLAIL[5] s to pull it back."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.spin = 0.0
        self.tick = 0.0
        self.recover = 0.0
        self.angle = 0.0

    @property
    def ring(self) -> float:
        lo, hi = config.FLAIL[:2]
        w = self.espec.windup
        return lo + (hi - lo) * min(1.0, (w - self.spin) / w) if self.spin > 0 else 0.0

    def think(self, ctx: AIContext, dt: float) -> None:
        super().think(ctx, dt)
        self.sense(ctx, dt)
        lo, hi, every, length, thrown, back = config.FLAIL
        t = self.target
        if self.recover > 0:
            self.recover -= dt
            return
        if self.spin > 0:
            self.spin -= dt
            self.angle += dt * 9
            self.tick -= dt
            if t is not None:
                self.facing = self.angle_to(t.x, t.y)
            if self.tick <= 0:
                self.tick = every
                r = self.ring
                for a in ctx.actors:
                    if a is self or not a.hittable:
                        continue
                    d = math.hypot(a.x - self.x, a.y - self.y)
                    if abs(d - r) <= 0.5 + a.hit_radius:
                        _numbered_hit(a, self.espec.damage * self.damage_mult, self,
                                      math.atan2(a.y - self.y, a.x - self.x), ctx)
            if self.spin <= 0:
                self._throw(ctx, length, thrown)
                self.recover = back
                self.cooldown = self.espec.cooldown
            return
        if t is None or not self.sees_target:
            _roam(self, ctx, dt)
            return
        if self.dist_to(t) <= self.espec.attack_radius and self.cooldown <= 0:
            self.spin, self.tick = self.espec.windup, every
            return
        self.go(ctx, t.x, t.y, dt, self.espec.speed)

    def _throw(self, ctx: AIContext, length: float, damage: float) -> None:
        reach = _reach(ctx, self.x, self.y, self.facing, length)
        ctx.effects.append(Effect("gaze", self.x, self.y, x2=self.x + math.cos(self.facing) * reach,
                                  y2=self.y + math.sin(self.facing) * reach, value=2))
        ctx.events.append(combat.HIT)
        for a in ctx.actors:
            if a is not self and a.hittable and _on_line(a, self.x, self.y, self.facing, reach, 0.5):
                _numbered_hit(a, damage * self.damage_mult, self, self.facing, ctx)


class RuneMine(PlainsCreature):
    """Drifts at its target over everything. A hero inside its ring
    (attack_radius): it glows for the windup, then blows -- everything in
    the ring is hurt, and the mine is gone (no reward). Shot down first,
    it just pops."""

    flies = True

    def can_see(self, world, other) -> bool:
        return math.hypot(other.x - self.x, other.y - self.y) <= self.espec.sight

    def think(self, ctx: AIContext, dt: float) -> None:
        super().think(ctx, dt)
        self.sense(ctx, dt)
        if self.windup > 0:
            self.windup -= dt
            self.tell = self.windup
            if self.windup <= 0:
                self._blow(ctx)
            return
        t = self.target
        if t is None or not self.alert:
            _roam(self, ctx, dt)
            return
        self.go(ctx, t.x, t.y, dt, self.espec.speed)
        if any(h.alive and math.hypot(h.x - self.x, h.y - self.y) <= self.espec.attack_radius
               for h in ctx.players):
            self.windup = self.espec.windup

    def _blow(self, ctx: AIContext) -> None:
        r = self.espec.attack_radius
        combat.blast(self.x, self.y, r, self.espec.damage * self.damage_mult, self, ctx.actors,
                     effects=ctx.effects)
        ctx.effects.append(Effect("rune_burst", self.x, self.y, size=r))
        ctx.events.append(combat.BREAK)
        _vanish(self)


class HauntedBlade(Hound):
    """One of three floating swords: the hounds' rules (circle, one thrust
    at a time per target), flying, closer in."""

    flies = True
    _turns: dict = {}             # (its own: a hound's dart doesn't hold up a blade)

    @property
    def orbit_radius(self) -> float:
        return config.BLADE_ORBIT

    def can_see(self, world, other) -> bool:
        return math.hypot(other.x - self.x, other.y - self.y) <= self.espec.sight

    def on_death(self, ctx: AIContext) -> None:
        self._release()
        ctx.effects.append(Effect("debris", self.x, self.y))


class BellGhost(PlainsCreature):
    """Keeps BELL[4] tiles from the heroes. Every BELL[0] s (a short wind-up
    first) it rings: every enemy within BELL[1] tiles is woken and comes
    for the nearest hero, and heroes within BELL[2] are hurt a little and
    knocked BELL[3] tiles back."""

    flies = True

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.timer = self.rng.uniform(2.0, config.BELL[0])

    def can_see(self, world, other) -> bool:
        return math.hypot(other.x - self.x, other.y - self.y) <= self.espec.sight

    def think(self, ctx: AIContext, dt: float) -> None:
        super().think(ctx, dt)
        self.sense(ctx, dt)
        every, wake, close, knock, keep = config.BELL
        if self.windup > 0:
            self.windup -= dt
            self.tell = self.windup
            if self.windup <= 0:
                self.tell = 0.0
                self._ring(ctx, wake, close, knock)
            return
        t = self.target
        if t is None or not self.sees_target:
            _roam(self, ctx, dt)
            return
        _keep_range(self, ctx, t, keep * 0.8, keep * 1.3, dt)
        self.timer -= dt
        if self.timer <= 0:
            self.timer = every
            self.windup = 0.5

    def _ring(self, ctx: AIContext, wake: float, close: float, knock: float) -> None:
        ctx.effects.append(Effect("howl", self.x, self.y, size=close))
        ctx.events.append("chime")
        heroes = [h for h in ctx.players if h.alive]
        for e in ctx.actors:
            if getattr(e, "faction", "") != "enemy" or e is self or not hasattr(e, "alert"):
                continue
            if heroes and math.hypot(e.x - self.x, e.y - self.y) <= wake:
                h = min(heroes, key=lambda h: math.hypot(h.x - e.x, h.y - e.y))
                e.alert = True
                e.last_known = (h.x, h.y)
                e.forget_timer = config.FORGET_TIME
        for h in heroes:
            d = math.hypot(h.x - self.x, h.y - self.y)
            if d <= close:
                a = math.atan2(h.y - self.y, h.x - self.x)
                _numbered_hit(h, self.espec.damage * self.damage_mult, self, a, ctx)
                combat.push(h, ctx.world, math.cos(a) * knock, math.sin(a) * knock)
