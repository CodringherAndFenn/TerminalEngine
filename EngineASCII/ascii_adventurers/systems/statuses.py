"""
systems/statuses.py -- burn, poison, bleed, chill and shock on enemies.

Every actor can carry a Statuses (created on the first status it gets).
A status has stacks (up to its max) and one timer; a new stack refreshes
the timer. Specs: config.STATUSES.

  burn / poison / bleed  damage over time: dps per stack, dealt every
         STATUS_TICK s as one hit (so damage numbers don't spam), credited
         to whoever applied it last. Its strength is that applier's status
         multiplier (bucket S x their tag bonus) at the moment of applying;
         a stronger applier upgrades it, a weaker one only adds a stack.
  chill  slows: the actor's whole clock runs (1 - slow x stacks) as fast
         (time_scale; the game scales its think() dt, so walking, aiming
         and cooldowns all slow alike). The 5th stack freezes it solid
         for FREEZE_TIME (time_scale 0) and uses up the chill.
  shock  vulnerability: the actor takes that much more damage from
         everything while it lasts (Actor.take_damage).

Status damage never crits and never uses bucket A. Bosses (an actor with
`boss = True`) take statuses at half strength and are slowed instead of
frozen.

Cards that bend the rules (design/CARDS.md):
  * Virulence: poison from that hero stacks to VIRULENCE[0], lasts longer;
  * Hemorrhage: their bleeds hurt twice as fast while the victim moves;
  * Thermal Shock / Toxic Current: when a status lands that completes the
    combo, an event goes into `combos`; the game resolves those each step
    (they need the nearby enemies, which this module doesn't know).
"""

from __future__ import annotations

from dataclasses import dataclass

from .. import config
from ..entities.effects import Effect

DOT = ("burn", "poison", "bleed")


@dataclass
class Status:
    stacks: int = 0
    left: float = 0.0          # seconds
    power: float = 1.0         # damage multiplier (bucket S x tag) of the applier
    source: object = None      # the actor credited with the damage
    double_moving: bool = False   # Hemorrhage: ticks x2 while the owner moves


class Statuses:
    def __init__(self) -> None:
        self.active: dict[str, Status] = {}
        self.frozen = 0.0          # seconds left frozen
        self._tick = config.STATUS_TICK
        self._owed: dict[str, float] = {}   # DoT damage accumulated since the last tick
        self._last_pos: tuple[float, float] | None = None

    def stacks(self, name: str) -> int:
        s = self.active.get(name)
        return s.stacks if s is not None else 0

    def has(self, name: str) -> bool:
        return name in self.active

    @property
    def empty(self) -> bool:
        return not self.active and self.frozen <= 0

    @property
    def vulnerability(self) -> float:
        """Damage taken multiplier (shock)."""
        if "shock" not in self.active:
            return 1.0
        return 1 + config.STATUSES["shock"].vulnerability

    @property
    def time_scale(self) -> float:
        """How fast the actor's clock runs (chill, freeze)."""
        if self.frozen > 0:
            return 0.0
        chill = self.stacks("chill")
        return max(0.1, 1 - config.STATUSES["chill"].slow * chill)

    def apply(self, owner, name: str, source, stacks: int = 1, power: float = 1.0,
              duration_scale: float = 1.0, cap: int | None = None,
              double_moving: bool = False) -> None:
        spec = config.STATUSES[name]
        boss = getattr(owner, "boss", False)
        if boss:
            power *= 0.5
        cap = max(spec.max_stacks, cap or 0)
        s = self.active.get(name)
        if s is None:
            s = self.active[name] = Status(power=power)
        s.stacks = min(cap, s.stacks + stacks)
        s.left = max(s.left, spec.duration * duration_scale)
        s.power = max(s.power, power)
        s.double_moving = s.double_moving or double_moving
        if source is not None:
            s.source = source
        if name == "chill" and s.stacks >= spec.max_stacks and not boss:
            del self.active["chill"]
            self.frozen = config.FREEZE_TIME * duration_scale

    def update(self, owner, dt: float, effects: list[Effect]) -> None:
        """Count down; deal damage over time every STATUS_TICK seconds."""
        self.frozen = max(0.0, self.frozen - dt)
        pos = (owner.x, owner.y)
        moving = self._last_pos is not None and pos != self._last_pos
        self._last_pos = pos
        for name in list(self.active):
            s = self.active[name]
            if name in DOT:
                spec = config.STATUSES[name]
                rate = 2.0 if s.double_moving and moving else 1.0
                self._owed[name] = (self._owed.get(name, 0.0)
                                    + spec.dps * s.stacks * s.power * rate * dt)
            s.left -= dt
            if s.left <= 0:
                del self.active[name]
        self._tick -= dt
        if self._tick > 1e-9:          # (float steps of 1/60 don't sum to exactly 0.5)
            return
        self._tick += config.STATUS_TICK
        for name, amount in list(self._owed.items()):
            if amount <= 0 or not owner.alive:
                continue
            source = self.active[name].source if name in self.active else None
            dealt = owner.take_damage(amount, source, None)
            if dealt > 0:
                effects.append(Effect("number", owner.x, owner.y - owner.hit_radius, 0.0,
                                      value=max(1, round(dealt)), tone=name))
        self._owed.clear()


def statuses_of(actor) -> Statuses:
    s = actor.status
    if s is None:
        s = actor.status = Statuses()
    return s


# Status combos waiting for the game to resolve them: (kind, victim, source).
combos: list[tuple[str, object, object]] = []


def inflict(victim, name: str, source, stacks: int = 1) -> None:
    """Put `stacks` of a status on `victim`, as applied by `source` (whose
    stats, if it's a hero, set its strength and duration)."""
    stats = getattr(source, "stats", None)
    power = stats.status_scale(config.STATUSES[name].tag) if stats is not None else 1.0
    duration = stats.duration_scale if stats is not None else 1.0
    cap = None
    if stats is not None and name == "poison" and stats.has("virulence"):
        cap, duration = config.VIRULENCE[0], duration * config.VIRULENCE[1]
    hemorrhage = stats is not None and name == "bleed" and stats.has("hemorrhage")
    st = statuses_of(victim)
    st.apply(victim, name, source, stacks, power, duration, cap, hemorrhage)
    if stats is None or not victim.alive:
        return
    if stats.has("thermal_shock") and name in ("burn", "chill") \
            and st.has("burn") and st.has("chill"):
        combos.append(("thermal_shock", victim, source))
    if stats.has("toxic_current") and name == "shock" and st.has("poison"):
        combos.append(("toxic_current", victim, source))


def roll_on_hit(victim, source, stats) -> None:
    """A hero's hit: each status their cards give rolls STATUS_BASE_CHANCE
    plus their status chance (Affliction)."""
    chance = config.STATUS_BASE_CHANCE + stats.status_chance
    for name in sorted(stats.statuses):
        if victim.alive and source.rng.random() < chance:
            inflict(victim, name, source)


def update_statuses(actors, dt: float, effects: list[Effect]) -> None:
    for a in actors:
        s = a.status
        if s is not None and a.alive:
            s.update(a, dt, effects)
            if s.empty:
                a.status = None
