"""
ai/brain.py -- what every enemy knows and remembers.

Senses (checked a few times a second, staggered so enemies don't all think
on the same frame):
  * sight  -- the target is within `spec.sight` tiles and the straight line
              to it isn't blocked (same tile walk shells use; water and bog
              don't block sight, walls/trees/rocks do).
  * hearing -- the player's gunfire within HEARING_RADIUS reveals roughly
              where they are, even without line of sight.
  * pain   -- being hit reveals the attacker.

Memory: the last place the target was seen/heard. When sight is lost the
enemy goes there and looks around; after FORGET_TIME it gives up and
wanders again.

Aggro / infighting: shots hurt everyone, but an enemy only switches its
target to another enemy once it has taken INFIGHT_AGGRO_FRACTION of its max
hp from that enemy -- a stray round or two is forgiven.

Brain is a mixin: the enemy classes combine it with a body (a Character
for shooters, a Creature body otherwise).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from .. import config
from ..entities.actor import Actor
from ..specs import EnemySpec
from ..systems.raycast import first_hit
from .steering import Steering

SENSE_INTERVAL = 0.2


@dataclass
class AIContext:
    """Everything an enemy may look at or touch during its turn."""

    world: object
    players: list           # the players' heroes (a single hero is accepted too)
    actors: list            # heroes + all active enemies
    projectiles: list
    effects: list
    events: list = field(default_factory=list)   # sound events to play

    def __post_init__(self) -> None:
        if not isinstance(self.players, (list, tuple)):
            self.players = [self.players]

    @property
    def player(self) -> Actor:
        """The first hero (single-player code and tests)."""
        return self.players[0]


class Brain:
    faction = "enemy"

    def init_brain(self, spec: EnemySpec, rng: random.Random, spawn_id) -> None:
        self.espec = spec
        self.spawn_id = spawn_id
        self.level = 1                        # the level it was woken at (scale_to_level)
        self.damage_mult = config.ENEMY_DAMAGE_MULTIPLIER   # grows with that level
        self.haste = 0.0                      # +fraction faster (pacts, Bounty)
        self.rng = rng
        self.home = (self.x, self.y)
        self.target: Actor | None = None
        self.grudge: Actor | None = None      # another enemy we've turned on
        self.hurt_by: dict[int, float] = {}   # id(attacker) -> damage taken
        self.sees_target = False
        self.last_known: tuple[float, float] | None = None
        self.forget_timer = 0.0
        self.alert = False
        self.reaction = 0.0                   # time left before first shot after spotting
        self._sense_timer = rng.uniform(0, SENSE_INTERVAL)
        self._wander_goal: tuple[float, float] | None = None
        self._wander_timer = 0.0
        self.steering = Steering(rng)

    def scale_to_level(self, level: int) -> None:
        """Toughen a freshly woken enemy for the players' level: +HP and
        +damage per level above 1 (config ENEMY_*_PER_LEVEL)."""
        level = max(1, min(config.MAX_LEVEL, level))
        self.level = level
        self.max_hp = round(self.max_hp * (1 + config.ENEMY_HP_PER_LEVEL * (level - 1)))
        self.hp = float(self.max_hp)
        self.damage_mult = config.ENEMY_DAMAGE_MULTIPLIER * (
            1 + config.ENEMY_DAMAGE_PER_LEVEL * (level - 1))

    # --- Senses ---------------------------------------------------------------------

    def sense(self, ctx: AIContext, dt: float) -> None:
        """Update target, sight and memory (throttled to SENSE_INTERVAL)."""
        if self.grudge is not None and not self.grudge.alive:
            self.grudge = None
        self.target = self.grudge if self.grudge is not None else self._pick_player(ctx)
        if self.forget_timer > 0:
            self.forget_timer -= dt
            if self.forget_timer <= 0:
                self.last_known = None
                self.alert = False
        self.reaction = max(0.0, self.reaction - dt)

        self._sense_timer -= dt
        if self._sense_timer > 0:
            return
        self._sense_timer += SENSE_INTERVAL
        was_seeing = self.sees_target
        self.sees_target = self.target is not None and self.can_see(ctx.world, self.target)
        if self.sees_target:
            if not was_seeing and not self.alert:
                self.reaction = config.REACTION_TIME
            self.alert = True
            self.last_known = (self.target.x, self.target.y)
            self.forget_timer = config.FORGET_TIME

    def _pick_player(self, ctx: AIContext) -> Actor | None:
        """Which hero to go after. Stay on the current one while it's alive
        and not much farther than another (no flip-flopping between two
        players at similar range); otherwise the nearest living hero."""
        alive = [p for p in ctx.players if p.alive]
        if not alive:
            return None
        nearest = min(alive, key=lambda p: math.hypot(p.x - self.x, p.y - self.y))
        cur = self.target
        if cur is not None and cur is not nearest and any(cur is p for p in alive):
            d_cur = math.hypot(cur.x - self.x, cur.y - self.y)
            d_near = math.hypot(nearest.x - self.x, nearest.y - self.y)
            if d_cur <= d_near + config.TARGET_SWITCH_MARGIN:
                return cur
        return nearest

    def can_see(self, world, other: Actor) -> bool:
        if math.hypot(other.x - self.x, other.y - self.y) > self.espec.sight:
            return False
        return first_hit(world.tile_at, self.x, self.y, other.x, other.y) is None

    def hear(self, x: float, y: float) -> None:
        """Gunfire at (x, y)."""
        if math.hypot(x - self.x, y - self.y) > config.HEARING_RADIUS or self.sees_target:
            return
        # Hearing is vague: remember a spot a couple of tiles off.
        self.last_known = (x + self.rng.uniform(-2, 2), y + self.rng.uniform(-2, 2))
        self.forget_timer = config.FORGET_TIME
        self.alert = True

    def take_damage(self, amount, source, from_angle):
        dealt = super().take_damage(amount, source, from_angle)
        if source is None or source is self:
            return dealt
        if source.faction == "player":
            self.alert = True
            self.target = source          # whoever hurts us gets our attention
            self.last_known = (source.x, source.y)
            self.forget_timer = config.FORGET_TIME
        else:
            # Friendly fire: hold a grudge only past the threshold.
            total = self.hurt_by.get(id(source), 0.0) + dealt
            self.hurt_by[id(source)] = total
            if total >= config.INFIGHT_AGGRO_FRACTION * self.max_hp and source.alive:
                self.grudge = source
                self.alert = True
                self.last_known = (source.x, source.y)
                self.forget_timer = config.FORGET_TIME
        return dealt

    # --- Goals ------------------------------------------------------------------------

    def wander_goal(self, dt: float) -> tuple[float, float]:
        """Aimless patrol near home: a new random nearby spot every few s."""
        self._wander_timer -= dt
        if self._wander_goal is None or self._wander_timer <= 0:
            hx, hy = self.home
            a = self.rng.uniform(-math.pi, math.pi)
            r = self.rng.uniform(3, 9)
            self._wander_goal = (hx + math.cos(a) * r, hy + math.sin(a) * r)
            self._wander_timer = self.rng.uniform(3, 7)
        return self._wander_goal

    def dist_to(self, other) -> float:
        return math.hypot(other.x - self.x, other.y - self.y)

    def angle_to(self, x: float, y: float) -> float:
        return math.atan2(y - self.y, x - self.x)
