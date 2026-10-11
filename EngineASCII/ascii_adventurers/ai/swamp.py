"""
ai/swamp.py -- the swamp's new enemies (P11, design/BOSSES.md 24.9).

Letter-art creatures on the plains' base (ai/plains.PlainsCreature), drawn
by render/plains.py with their tells from render/swamp.py.

  bog zombies, newts (swarms), gator hatchlings (packs): simple chasers;
  mudskippers hop (ai/desert.Hopper)
  bog crocodile (elite) lies with its eyes above the bog; lunges, clamps
                  on and drags you back with it, biting (a roll breaks free)
  snapping turtle a slow snapper; hurt enough, it hides in its shell a moment
  heron           keeps 3 tiles off and stabs a line with its beak; flaps
                  off if you close in
  swamp hag       keeps back and curses the ground under you: a puddle grows,
                  and whoever's still in it is rooted
  marsh lights    three lights that zap; only one is real -- shoot it and the
                  other two go out (the two illusions can't be hit)
  bloated corpse  shambles at you and bursts into a toxic cloud (when it
                  reaches you, or dies)
  sludge          splits in two when it dies, and again (three sizes)

The lizardman javelineer is an archer with its own body; its javelins
stick in the ground (systems/combat._shot_ends).
"""

from __future__ import annotations

import math

from .. import config
from ..entities.effects import Effect
from ..systems import combat
from ..systems.zones import Zone
from .brain import AIContext
from .creatures import _numbered_hit
from .desert import _dash, _on_line, _reach
from .forest import _keep_range, _roam, _vanish
from .plains import Chaser, PlainsCreature


class Crocodile(PlainsCreature):
    """Elite. Lurks (only its eyes and snout up: `croc_lurk`, but it can be
    seen and shot) until a hero is within attack_radius; then a short
    windup and a lunge CROC[1] tiles at CROC[0] tiles/s. A hero it reaches
    is clamped for CROC[2] s: it backs off CROC[3] tiles dragging them,
    biting every CROC[4] s; the hero can't walk or attack, but a roll
    breaks free. Then it settles to lurk again."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.state = "lurk"
        self.timer = 0.0
        self.aim = 0.0
        self.ran = 0.0
        self.held = None
        self.bite_t = 0.0

    def sprite_now(self) -> str:
        return "croc_lurk" if self.state == "lurk" else "crocodile"

    def think(self, ctx: AIContext, dt: float) -> None:
        super().think(ctx, dt)
        self.sense(ctx, dt)
        speed, length, hold, drag, every = config.CROC
        t = self.target
        if self.state == "crouch":
            self.timer -= dt
            self.tell = self.timer
            if self.timer <= 0:
                self.state, self.ran, self.tell = "lunge", 0.0, 0.0
            return
        if self.state == "lunge":
            moved, blocked = _dash(self, ctx, self.aim, speed, dt)
            self.ran += moved
            for h in ctx.players:
                if h.alive and h.hittable and \
                        math.hypot(h.x - self.x, h.y - self.y) <= self.hit_radius + h.hit_radius:
                    self.state, self.held, self.timer, self.bite_t = "clamp", h, hold, 0.0
                    ctx.effects.append(Effect("toast", h.x, h.y - 2, label="CLAMPED!"))
                    return
            if blocked or self.ran >= length:
                self.state, self.timer = "back", 1.0
            return
        if self.state == "clamp":
            h = self.held
            self.timer -= dt
            if h is None or not h.alive or getattr(h, "rolling", False) or self.timer <= 0:
                self.held = None
                self.state, self.timer = "back", 1.0
                self.cooldown = self.espec.cooldown
                return
            back = self.aim + math.pi
            x0, y0 = self.x, self.y
            _dash(self, ctx, back, drag / hold, dt)
            combat.push(h, ctx.world, self.x - x0, self.y - y0)
            if hasattr(h, "petrify"):
                h.petrify(dt * 1.5)                      # (held: no walking, no attacking)
            self.bite_t -= dt
            if self.bite_t <= 0:
                self.bite_t = every
                _numbered_hit(h, self.espec.damage * self.damage_mult, self, self.aim, ctx)
            return
        if self.state == "back":
            self.timer -= dt
            if t is not None:
                a = self.angle_to(t.x, t.y) + math.pi
                self.go(ctx, self.x + math.cos(a) * 3, self.y + math.sin(a) * 3, dt,
                        self.espec.speed)
            if self.timer <= 0:
                self.state = "lurk"
            return
        # Lurking.
        if t is not None and self.sees_target and self.cooldown <= 0 \
                and self.dist_to(t) <= self.espec.attack_radius:
            self.aim = self.facing = self.angle_to(t.x, t.y)
            self.state, self.timer = "crouch", self.espec.windup
        elif t is not None and self.sees_target and self.dist_to(t) > self.espec.attack_radius * 2:
            self.go(ctx, t.x, t.y, dt, self.espec.speed * 0.5)   # (creeps closer)


class Turtle(Chaser):
    """A slow chaser with a hard snap. For every TURTLE[0] of its max HP it
    loses, it pulls into its shell for TURTLE[1] s: nothing hurts it then."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.shelled = 0.0
        self.mark = float(self.max_hp)

    @property
    def hiding(self) -> bool:
        return self.shelled > 0

    def sprite_now(self) -> str:
        return "turtle_shell" if self.hiding else "turtle"

    def take_damage(self, amount, source, from_angle):
        if self.hiding:
            return 0.0
        dealt = super().take_damage(amount, source, from_angle)
        if self.alive and self.mark - self.hp >= self.max_hp * config.TURTLE[0]:
            self.mark = self.hp
            self.shelled = config.TURTLE[1]
            self.windup = self.tell = 0.0
        return dealt

    def think(self, ctx: AIContext, dt: float) -> None:
        if self.hiding:
            PlainsCreature.think(self, ctx, dt)
            self.shelled -= dt
            return
        super().think(ctx, dt)


class Heron(PlainsCreature):
    """Keeps HERON[0] tiles off its target; in line, it draws its neck back
    (the windup; the line shows) and stabs attack_radius tiles along it.
    A hero within HERON[1] tiles: it flaps HERON[2] tiles away."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.aim = 0.0
        self.flap = 0.0

    def think(self, ctx: AIContext, dt: float) -> None:
        super().think(ctx, dt)
        self.sense(ctx, dt)
        keep, close, away = config.HERON
        t = self.target
        if self.flap > 0:
            self.flap -= dt
            a = self.aim + math.pi
            _dash(self, ctx, a, 9.0, dt)
            return
        if self.windup > 0:
            self.windup -= dt
            self.tell = self.windup
            if self.windup <= 0:
                self.tell = 0.0
                length = _reach(ctx, self.x, self.y, self.aim, self.espec.attack_radius)
                for a in ctx.actors:
                    if a is not self and a.hittable and _on_line(a, self.x, self.y, self.aim,
                                                                 length, 0.3):
                        _numbered_hit(a, self.espec.damage * self.damage_mult, self, self.aim, ctx)
                ctx.effects.append(Effect("impact", self.x + math.cos(self.aim) * length,
                                          self.y + math.sin(self.aim) * length, self.aim))
                self.cooldown = self.espec.cooldown
            return
        if t is None or not self.sees_target:
            _roam(self, ctx, dt)
            return
        d = self.dist_to(t)
        if d < close:
            self.aim = self.angle_to(t.x, t.y)
            self.flap = away / 9.0
            return
        _keep_range(self, ctx, t, keep - 0.5, keep + 0.5, dt)
        if self.cooldown <= 0 and d <= self.espec.attack_radius + t.hit_radius:
            self.aim = self.facing = self.angle_to(t.x, t.y)
            self.windup = self.espec.windup


class SwampHag(PlainsCreature):
    """Keeps HAG[0] tiles back. Every cooldown she curses the ground under
    her target: a puddle (a "curse" zone, HAG[1] tiles) grows for HAG[2] s
    (the tell); whoever is still in it then is rooted HAG[3] s (can't walk;
    can still attack and roll out)."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.timer = self.rng.uniform(1.5, self.espec.cooldown)

    def think(self, ctx: AIContext, dt: float) -> None:
        super().think(ctx, dt)
        self.sense(ctx, dt)
        keep, radius, grow, root = config.HAG
        t = self.target
        if t is None or not self.sees_target:
            _roam(self, ctx, dt)
            return
        _keep_range(self, ctx, t, keep * 0.8, keep * 1.3, dt)
        self.timer -= dt
        if self.timer <= 0 and ctx.zones is not None:
            self.timer = self.espec.cooldown
            ctx.zones.append(Zone("curse", t.x, t.y, radius, grow, 999.0, 0.0, self, root=root))
            ctx.events.append("hex")


class MarshLight(PlainsCreature):
    """One of MARSH_LIGHTS[0]: the spawned one is real and, on its first
    turn, brings its illusions (`marsh_light_fake`), then swaps places with
    one at random. All drift about their target and zap it (within
    attack_radius, every cooldown). The illusions can't be hit; when the
    real one dies, they go out."""

    flies = True

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.real = None                 # (an illusion: the real one)
        self.made = False
        self.zap = self.rng.uniform(0.5, self.espec.cooldown)
        self.drift = self.rng.uniform(0, math.tau)

    @property
    def fake(self) -> bool:
        return getattr(self, "kind_key", "") == "marsh_light_fake"

    @property
    def hittable(self) -> bool:
        return self.alive and not self.fake

    def can_see(self, world, other) -> bool:
        return math.hypot(other.x - self.x, other.y - self.y) <= self.espec.sight

    def think(self, ctx: AIContext, dt: float) -> None:
        super().think(ctx, dt)
        if self.fake:
            if self.real is None or not self.real.alive or not any(a is self.real
                                                                   for a in ctx.actors):
                _vanish(self)
                return
        elif not self.made:
            self.made = True
            self._bring(ctx)
        self.sense(ctx, dt)
        t = self.target
        self.drift += dt * 0.9
        if t is None or not self.alert:
            _roam(self, ctx, dt)
            return
        r = 4.0 + math.sin(self.drift * 0.7) * 1.5
        self.go(ctx, t.x + math.cos(self.drift) * r, t.y + math.sin(self.drift) * r, dt,
                self.espec.speed)
        self.zap -= dt
        if self.zap <= 0 and self.dist_to(t) <= self.espec.attack_radius:
            self.zap = self.espec.cooldown
            _numbered_hit(t, self.espec.damage * self.damage_mult, self, self.angle_to(t.x, t.y),
                          ctx)
            ctx.effects.append(Effect("arc", self.x, self.y, x2=t.x, y2=t.y))
            ctx.events.append("zap")

    def _bring(self, ctx: AIContext) -> None:
        from . import make_enemy
        n, apart = config.MARSH_LIGHTS
        spots = [(self.x, self.y)]
        for k in range(1, n):
            a = self.drift + k * math.tau / n
            spots.append((self.x + math.cos(a) * apart, self.y + math.sin(a) * apart))
        self.rng.shuffle(spots)                   # (the real one: any of the three)
        self.x, self.y = spots[0]
        for k, (x, y) in enumerate(spots[1:]):
            f = make_enemy("marsh_light_fake", x, y, self.rng)
            f.real, f.made, f.alert = self, True, self.alert
            f.drift = self.drift + (k + 1) * math.tau / n
            ctx.spawned.append(f)


class BloatedCorpse(Chaser):
    """Shambles at you; when it reaches you (attack_radius) or dies, it
    bursts into a toxic cloud: CORPSE_GAS[0] tiles, CORPSE_GAS[1] s,
    CORPSE_GAS[2] damage every CORPSE_GAS[3] s to anyone in it."""

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.burst = False

    def think(self, ctx: AIContext, dt: float) -> None:
        t = self.target
        if t is not None and self.alert and self.dist_to(t) <= self.espec.attack_radius + t.hit_radius:
            self.hp = 0.0                                # (bursts: no reward for that)
            self.last_hit_by = None
            return
        super().think(ctx, dt)

    def on_death(self, ctx: AIContext) -> None:
        ctx.effects.append(Effect("explosion", self.x, self.y))
        if ctx.zones is None or self.burst:
            return
        self.burst = True
        radius, life, damage, every = config.CORPSE_GAS
        ctx.zones.append(Zone("gas", self.x, self.y, radius, life, every, damage, self))
        ctx.events.append(combat.BREAK)


class Sludge(Chaser):
    """A chaser that splits when it dies: sludge -> two sludge_mid -> two
    sludge_small each."""

    SPLITS = {"sludge": "sludge_mid", "sludge_mid": "sludge_small"}

    def on_death(self, ctx: AIContext) -> None:
        ctx.effects.append(Effect("debris", self.x, self.y))
        child = self.SPLITS.get(getattr(self, "kind_key", ""))
        if child is None:
            return
        for side in (-1, 1):
            a = self.facing + side * math.pi / 2
            ctx.spawned.append((child, self.x + math.cos(a) * 0.7, self.y + math.sin(a) * 0.7))
