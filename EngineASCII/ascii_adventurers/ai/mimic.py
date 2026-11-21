"""
ai/mimic.py -- the mimic (M28.4c, design/GEAR.md 4.2): a chest with teeth.

An elite that only a chest wakes (systems/chests.py; never rostered). It
hops after you in short bounds (MIMIC_HOP), and off each cooldown
(MIMIC_COOLDOWNS: lunge, tongue, spit):
  lunge   crouches (the line shows), then springs MIMIC_LUNGE tiles along
          it, biting the first thing it meets once; walls stop it;
  tongue  a "!", then a tongue lashes out MIMIC_TONGUE tiles along a line
          that showed: whoever's on it is bitten and dragged toward it;
  spit    when you're MIMIC_SPIT_RANGE off: a fan of coins (shots).
Letter-art body per biome (render/chests.py MIMIC_ART; `sprite_now`).
Friendly fire applies, like every enemy's.
"""

from __future__ import annotations

import math

from .. import config
from ..entities.effects import Effect
from ..entities.projectile import Projectile
from ..systems import combat
from ..systems.collision import move_hull
from .brain import AIContext
from .creatures import _numbered_hit
from .plains import PlainsCreature


class Mimic(PlainsCreature):
    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.biome = "forest"            # (systems/chests.py sets the chest's)
        self.state = "hop"               # hop | crouch | lunge | lash | spit
        self.timer = 0.0
        self.hop_t = 0.0                 # the hop's clock (moving while < MIMIC_HOP[0])
        self.aim = self.facing
        self.ran = 0.0
        self.bit = False                 # this lunge already bit someone
        self.tongue_t = 0.0              # >0: the tongue is out (drawn)
        self.tongue_end = (self.x, self.y)
        self.cds = [0.0, 0.0, 0.0]       # lunge, tongue, spit

    def sprite_now(self) -> str:
        return f"mimic_{self.biome}"

    def think(self, ctx: AIContext, dt: float) -> None:
        super().think(ctx, dt)
        self.sense(ctx, dt)
        self.cds = [max(0.0, c - dt) for c in self.cds]
        self.tongue_t = max(0.0, self.tongue_t - dt)
        t = self.target
        if self.state in ("crouch", "lash", "spit"):
            self.timer -= dt
            self.tell = self.timer if self.state != "crouch" else 0.0
            if t is not None and self.state != "crouch":
                self.aim = self.angle_to(t.x, t.y)       # (the lunge's line is set)
            if self.timer > 0:
                return
            self.tell = 0.0
            if self.state == "crouch":
                self.state, self.ran, self.bit = "lunge", 0.0, False
            elif self.state == "lash":
                self._lash(ctx)
                self.state = "hop"
            else:
                self._spit(ctx)
                self.state = "hop"
            return
        if self.state == "lunge":
            self._lunge(ctx, dt)
            return
        if t is None or not self.alert:
            self.go(ctx, *self.wander_goal(dt), dt, self.espec.speed * 0.3)
            return
        dist = self.dist_to(t)
        if self.sees_target:
            lunge, tongue, spit = config.MIMIC_LUNGE, config.MIMIC_TONGUE, config.MIMIC_SPIT
            if dist <= lunge[2] * 0.9 and self.cds[0] <= 0:
                self.aim = self.facing = self.angle_to(t.x, t.y)
                self.state, self.timer = "crouch", lunge[0]
                self.cds[0] = config.MIMIC_COOLDOWNS[0]
                return
            if 2.0 <= dist <= tongue[1] and self.cds[1] <= 0:
                self.aim = self.facing = self.angle_to(t.x, t.y)
                self.state, self.timer = "lash", tongue[0]
                self.cds[1] = config.MIMIC_COOLDOWNS[1]
                return
            lo, hi = config.MIMIC_SPIT_RANGE
            if lo <= dist <= hi and self.cds[2] <= 0:
                self.aim = self.facing = self.angle_to(t.x, t.y)
                self.state, self.timer = "spit", spit[0]
                self.cds[2] = config.MIMIC_COOLDOWNS[2]
                return
        goal = (t.x, t.y) if self.sees_target else self.last_known
        if goal is None:
            return
        # Hops: it moves for MIMIC_HOP[0] s, sits for MIMIC_HOP[1].
        self.hop_t = (self.hop_t + dt) % (config.MIMIC_HOP[0] + config.MIMIC_HOP[1])
        if self.hop_t < config.MIMIC_HOP[0]:
            self.go(ctx, *goal, dt, self.espec.speed)
        else:
            self.facing = self.angle_to(*goal)

    # --- Attacks --------------------------------------------------------------------

    def _lunge(self, ctx: AIContext, dt: float) -> None:
        tell, speed, length, mult = config.MIMIC_LUNGE
        step = speed * dt
        dx, dy = math.cos(self.aim) * step, math.sin(self.aim) * step
        x0, y0 = self.x, self.y
        self.x, self.y, bx, by = move_hull(ctx.world, self.x, self.y, 0.0, self.half, self.half,
                                           dx, dy)
        moved = math.hypot(self.x - x0, self.y - y0)
        self._moved = moved
        self.walked += moved
        self.ran += moved
        if not self.bit:
            for a in ctx.actors:
                if a is self or not a.hittable:
                    continue
                if math.hypot(a.x - self.x, a.y - self.y) <= self.hit_radius + a.hit_radius:
                    self.bit = True
                    _numbered_hit(a, self.espec.damage * self.damage_mult * mult, self, self.aim,
                                  ctx)
                    combat.push(a, ctx.world, math.cos(self.aim) * 1.2, math.sin(self.aim) * 1.2)
                    break
        if (bx or by) or self.ran >= length or self.bit:
            self.state = "hop"
            self.cooldown = self.espec.cooldown

    def _lash(self, ctx: AIContext) -> None:
        """The tongue: everyone on its line is bitten and dragged in."""
        tell, reach, pull, mult = config.MIMIC_TONGUE
        ca, sa = math.cos(self.aim), math.sin(self.aim)
        self.tongue_t = 0.3
        self.tongue_end = (self.x + ca * reach, self.y + sa * reach)
        for a in ctx.actors:
            if a is self or not a.hittable:
                continue
            rx, ry = a.x - self.x, a.y - self.y
            along = rx * ca + ry * sa
            if along < 0.5 or along > reach:
                continue
            off = abs(-rx * sa + ry * ca)
            if off > 0.9 + a.hit_radius:
                continue
            _numbered_hit(a, self.espec.damage * self.damage_mult * mult, self, self.aim + math.pi,
                          ctx)
            d = min(pull, max(0.0, along - 1.2))
            combat.push(a, ctx.world, -ca * d, -sa * d)
        ctx.effects.append(Effect("arc", self.x, self.y, x2=self.tongue_end[0],
                                  y2=self.tongue_end[1]))

    def _spit(self, ctx: AIContext) -> None:
        tell, n, fan = config.MIMIC_SPIT
        shell = config.WEAPONS["mimic_coins"].shell
        spread = math.radians(fan)
        for k in range(n):
            a = self.aim + (k - (n - 1) / 2) * (spread / max(1, n - 1))
            ctx.projectiles.append(Projectile(self.x + math.cos(a) * 0.8, self.y + math.sin(a) * 0.8,
                                              a, shell, owner=self,
                                              damage=shell.damage * self.damage_mult))
        ctx.events.append(shell.sound)

    def on_death(self, ctx: AIContext) -> None:
        ctx.effects.append(Effect("explosion", self.x, self.y))
        ctx.effects.append(Effect("debris", self.x, self.y))
        ctx.events.append(combat.BREAK)
