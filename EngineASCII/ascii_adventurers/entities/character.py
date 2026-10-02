"""
entities/character.py -- a walking body with a weapon: the hero, and the
enemies that shoot (goblin archer, warlock, ogre, spell tower).

Movement is free in 8 directions: the input (or the AI) gives a direction,
and the velocity eases toward direction * max_speed at `accel` (or down to
zero at `brake` when there's no input). Collision is a square box of
`size_px` against the tile grid, resolved one axis at a time so walking
diagonally into a wall slides along it (systems/collision.py).

Aiming is separate from walking: `aim_angle` is where the weapon points
(the hero: straight at the mouse; enemies turn it at `aim_turn_speed`).
Characters face left or right toward their aim -- that's how the sprite is
drawn.

Heroes can dodge-roll (M18, systems/roll.py): while `roll_t` runs the body
slides along `roll_dir` at the roll's speed instead of walking, and it
can't be hit at all (not hittable, so shots, blasts and bodies pass
through).

Angles are in radians in WORLD space, measured with atan2(dy, dx) where +y
points DOWN the screen. So 0 = east, +pi/2 = south, -pi/2 = north.
"""

from __future__ import annotations

import math
import random

from .. import config
from ..specs import CharacterSpec
from ..systems.collision import TileSource, move_hull
from .actor import Actor
from .weapon import Weapon

# A hit counts as "on the front" when it comes from within this angle of
# where the character faces (its aim) -- used for front_armor (the ogre).
FRONT_ARC = math.radians(55)

TAU = 2 * math.pi


def wrap_angle(a: float) -> float:
    """Wrap an angle to (-pi, pi]."""
    a = math.fmod(a + math.pi, TAU)
    if a <= 0:
        a += TAU
    return a - math.pi


def rotate_toward(current: float, target: float, max_step: float) -> float:
    """Turn `current` toward `target` by at most `max_step`, the short way."""
    err = wrap_angle(target - current)
    if abs(err) <= max_step:
        return target
    return current + math.copysign(max_step, err)


def _approach(v: float, target: float, rate: float) -> float:
    if abs(target - v) <= rate:
        return target
    return v + math.copysign(rate, target - v)


class Character(Actor):
    faction = "player"

    def __init__(self, spec: CharacterSpec, x: float, y: float, max_hp: int | None = None) -> None:
        # Hit circle: a bit bigger than half the box, in tiles.
        super().__init__(max_hp if max_hp is not None else spec.max_hp,
                         spec.size_px / 2 / config.TILE_PX_W + 0.15)
        self.spec = spec
        self.x, self.y = x, y
        self.vx = self.vy = 0.0          # tiles/s (enemies lead their shots with this)
        self.aim_angle = 0.0
        self.aim_point: tuple[float, float] | None = None   # the world point aimed at
        self.heading = 0.0               # direction of the last movement
        self.walked = 0.0                # tiles walked in total (walk animation)
        self.last_blocked = False
        self.half = spec.size_px / 2     # collision half-size, px
        self.weapon = Weapon(config.WEAPONS[spec.weapon])
        # Heroes (M14): their card stats (players/stats.HeroStats; None for
        # enemies), the dice for crits / evasions / status rolls (the game
        # seeds it per player so runs replay), Hunter's Mark's target,
        # attacks made (Overload) and hits evaded (for the "evade" pop-up).
        self.stats = None
        self.rng = random.Random(0)
        self.marked = None
        self.attacks = 0
        self.evaded = 0
        # More hero card state (M16), kept up by the game scene: shield HP and
        # seconds since last hurt, a hit that wants Retaliation, Crescendo's
        # streak, Bloodlust's kill timers, the hero's level / run loot / run
        # clock, whether the last strike crit, bestiary kinds known.
        self.shield = 0.0
        self.since_hit = 0.0
        self.retaliate = False
        self.streak = 0
        self.bloodlust: list[float] = []
        self.level = 1
        self.run_loot = 0.0
        self.time = 0.0
        self.last_crit = False
        self.bestiary: set[str] = set()
        self.idle = 0.0                   # seconds since the last attack (Capacitor)
        # The dodge roll (systems/roll.py): seconds of roll left and its
        # direction (unit vector) and speed (tiles/s; 0 for Blink, which has
        # already arrived), charges ready and seconds toward the next one,
        # plus what roll cards keep: Riposte's and Slipstream's timers,
        # enemy shots already rolled through (Close Call) / shouldered aside
        # this roll, distance to the next trail patch, steps rolled.
        self.roll_t = 0.0
        self.roll_dir = (1.0, 0.0)
        self.roll_speed = 0.0
        self.roll_charges = config.ROLL_CHARGES
        self.roll_recharge = 0.0
        self.riposte = 0.0
        self.slipstream = 0.0
        self.roll_passed: set[int] = set()
        self.roll_trail = 0.0
        self.roll_steps = 0
        self.speed_mult = 1.0             # Slipstream
        self.spiral = 0                   # Spiral: how far round its extra shot has turned

    @property
    def rolling(self) -> bool:
        return self.roll_t > 0

    @property
    def hittable(self) -> bool:
        """Mid-roll, nothing can touch a hero."""
        return self.alive and self.roll_t <= 0

    @property
    def facing_left(self) -> bool:
        return math.cos(self.aim_angle) < 0

    @property
    def speed(self) -> float:
        return math.hypot(self.vx, self.vy)

    # --- Damage ------------------------------------------------------------------------

    def take_damage(self, amount, source, from_angle):
        """Armor: a hit coming from the side the character faces (its aim)
        is scaled by the spec's front_armor. A hero's evasion may make
        the hit miss outright, and armor `a` scales it by 1 - a / (|a| + ARMOR_K)
        (40 armor halves it; negative armor makes hits hurt more)."""
        if from_angle is not None and self.spec.front_armor != 1.0:
            came_from = from_angle + math.pi     # a hit comes *from* opposite its travel
            if abs(wrap_angle(came_from - self.aim_angle)) < FRONT_ARC:
                amount *= self.spec.front_armor
        st = self.stats
        if self.roll_t > 0:                             # i-frames
            return 0.0
        if st is None or not self.alive or self.invulnerable:
            return super().take_damage(amount, source, from_angle)
        if st.evasion > 0 and self.rng.random() < st.evasion:
            self.evaded += 1
            return 0.0
        if st.armor:
            amount *= 1 - st.armor / (abs(st.armor) + config.ARMOR_K)
        if st.has("hit_cap"):                           # Heavy Plate
            amount = min(amount, self.max_hp * 0.10)
        self.since_hit = 0.0
        if self.shield > 0:                             # Ward Charm, Aegis
            absorbed = min(self.shield, amount)
            self.shield -= absorbed
            amount -= absorbed
        if st.has("retaliation"):
            self.retaliate = True
        flat, share = st.thorns                         # Thorn Mail
        if (flat or share) and source is not None and source is not self \
                and source.faction != "player" and source.alive:
            source.take_damage(flat + share * amount, self, None)
        if amount <= 0:
            self.hurt_flash = 0.12
            return 0.0
        return super().take_damage(amount, source, from_angle)

    def heal(self, amount: float) -> float:
        """Aegis (a card): healing past full HP becomes shield, up to
        AEGIS_MAX of max HP."""
        if not self.alive or amount <= 0:
            return 0.0
        room = self.max_hp - self.hp
        healed = super().heal(amount)
        st = self.stats
        if st is not None and st.has("aegis") and amount > room:
            cap = max(self.shield, self.max_hp * config.AEGIS_MAX)
            self.shield = min(cap, self.shield + amount - room)
        return healed

    # --- Moving -------------------------------------------------------------------------

    def move(self, ax: float, ay: float, dt: float, world: TileSource) -> None:
        """One frame of walking toward direction (ax, ay) (any length; zero
        = stop), with collision."""
        self.last_blocked = False
        spec = self.spec
        if spec.max_speed <= 0:
            return   # towers don't walk
        if self.roll_t > 0:
            self._roll_move(dt, world)
            return
        n = math.hypot(ax, ay)
        top = spec.max_speed * self.speed_mult
        if n > 0:
            tx, ty = ax / n * top, ay / n * top
            rate = spec.accel * dt
        else:
            tx = ty = 0.0
            rate = spec.brake * dt
        self.vx = _approach(self.vx, tx, rate)
        self.vy = _approach(self.vy, ty, rate)
        if self.vx == 0.0 and self.vy == 0.0:
            return
        dx, dy = self.vx * dt, self.vy * dt
        x0, y0 = self.x, self.y
        self.x, self.y, bx, by = move_hull(world, self.x, self.y, 0.0, self.half, self.half, dx, dy)
        if bx:
            self.vx = 0.0
        if by:
            self.vy = 0.0
        self.last_blocked = bx or by
        moved = math.hypot(self.x - x0, self.y - y0)
        if moved > 1e-9:
            self.heading = math.atan2(self.y - y0, self.x - x0)
            self.walked += moved

    def _roll_move(self, dt: float, world: TileSource) -> None:
        """One step of a roll: a straight slide at the roll's speed, stopped
        by walls like walking. It comes out of the roll at walking speed
        the same way, so the hero doesn't stop dead."""
        step = min(dt, self.roll_t)
        self.roll_t -= dt
        dx, dy = self.roll_dir
        if self.roll_speed > 0:
            x0, y0 = self.x, self.y
            self.x, self.y, bx, by = move_hull(world, self.x, self.y, 0.0, self.half, self.half,
                                               dx * self.roll_speed * step,
                                               dy * self.roll_speed * step)
            self.last_blocked = bx or by
            moved = math.hypot(self.x - x0, self.y - y0)
            if moved > 1e-9:
                self.heading = math.atan2(self.y - y0, self.x - x0)
                self.walked += moved
        top = self.spec.max_speed * self.speed_mult
        self.vx, self.vy = dx * top, dy * top
        if self.roll_t <= 1e-9:                      # (float leftovers of n steps)
            self.roll_t = 0.0

    # --- Aiming ---------------------------------------------------------------------------

    def aim_at(self, wx: float, wy: float, dt: float) -> None:
        """Point the weapon at world point (wx, wy): the true angle, so shots
        travel exactly through it."""
        self.aim_point = (wx, wy)
        if wx == self.x and wy == self.y:
            return
        self.aim_angle_toward(math.atan2(wy - self.y, wx - self.x), dt)

    def aim_angle_toward(self, target: float, dt: float) -> None:
        """Turn the aim toward a world angle at the spec's speed (instantly
        if it's 0, as for the player)."""
        speed = self.spec.aim_turn_speed
        if speed <= 0:
            self.aim_angle = target
        else:
            self.aim_angle = wrap_angle(rotate_toward(self.aim_angle, target, speed * dt))

    def aim_on_target(self, target: float, tolerance: float) -> bool:
        return abs(wrap_angle(target - self.aim_angle)) <= tolerance
