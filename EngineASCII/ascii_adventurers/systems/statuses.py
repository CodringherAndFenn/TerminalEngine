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

The head gear's tricks (M28.2b, design/GEAR.md 17.2) belong to whoever
applied the status (its `source`), except Smoke (the hero being looked
at) and Toxic blood (the hero being hit):
  * on_hero_hit: a hero's hit -- Kindle, Fanned flames, Fang, Cold snap,
    Build-up, Shatterpoint, Battery's shocking attack;
  * inflict: Pyre, Neurotoxin (a root), Tempest and Rend (events into
    `combos`), Geyser's cooldown;
  * Statuses.update: Pyre, Incubation, Black death, Ground fault, the
    cowl's bleed rates (Spurt, Bloodhound);
  * run_rules.RunRules.status_tricks: what needs the other enemies or
    the hero (Permafrost, Panic, Exsanguinate, Geyser).
"""

from __future__ import annotations

from dataclasses import dataclass

import math

from .. import config
from ..entities.effects import Effect

DOT = ("burn", "poison", "bleed")


def has(actor, flag: str) -> bool:
    """Whether a hero (an actor with stats) has a card or trick flag."""
    stats = getattr(actor, "stats", None)
    return stats is not None and stats.has(flag)


@dataclass
class Status:
    stacks: int = 0
    left: float = 0.0          # seconds
    power: float = 1.0         # damage multiplier (bucket S x tag) of the applier
    source: object = None      # the actor credited with the damage
    double_moving: bool = False   # Hemorrhage: ticks x2 while the owner moves
    pyre: float = 0.0          # Cinderveil Hood +9: s left burning twice as fast
    extra: float = 0.0         # Stormvane Helm +3: shock vulnerability built up
    lasting: bool = False      # Thunderhead Rod (L), Ionized: a bolt's shock never wears off


class Statuses:
    def __init__(self) -> None:
        self.active: dict[str, Status] = {}
        self.frozen = 0.0          # seconds left frozen
        self.dazed = 0.0           # seconds left dazed (M28.2: the War Drum's beat): like frozen, no ice
        self.asleep = 0.0          # s left asleep (M28.2i: Cradlesong +3): dazed until hit
        self._tick = config.STATUS_TICK
        self._owed: dict[str, float] = {}   # DoT damage accumulated since the last tick
        self._last_pos: tuple[float, float] | None = None
        # The head gear's tricks (M28.2b): who froze it (Rime Hood), s left
        # rooted (Viper Mask), s left running from `scared_from` (Bloodtrail
        # Cowl), trick cooldowns (s), the s left on each recent shock
        # (Tempest), Permafrost's clock and how fast it moved last step.
        self.frozen_by = None
        self.rooted = 0.0
        self.scared = 0.0
        self.scared_from = None
        self.cooldowns: dict[str, float] = {}
        self.shocks: list[float] = []
        self.perma = 0.0
        self.pace = 0.0
        # The legendary tricks (M28.3e): the tile Brushfire last lit, and the
        # chill a boss has taken since it was last free of it (Deep freeze).
        self.brush_tile: tuple | None = None
        self.deep = 0

    def stacks(self, name: str) -> int:
        s = self.active.get(name)
        return s.stacks if s is not None else 0

    def has(self, name: str) -> bool:
        return name in self.active

    @property
    def empty(self) -> bool:
        return (not self.active and self.frozen <= 0 and self.dazed <= 0 and self.rooted <= 0
                and self.asleep <= 0 and self.scared <= 0 and not self.cooldowns
                and not self.shocks)

    @property
    def vulnerability(self) -> float:
        """Damage taken multiplier (shock, and Build-up's extra)."""
        s = self.active.get("shock")
        if s is None:
            return 1.0
        return 1 + config.STATUSES["shock"].vulnerability + s.extra

    @property
    def wounded(self) -> bool:
        """Thornhelm +6 (Open wounds): bleeding, it can't heal."""
        s = self.active.get("bleed")
        return s is not None and has(s.source, "serrated+6")

    def walls(self) -> bool:
        """Rime Hood +6 (Hoarfrost): frozen, it can't be pushed and stops
        enemy shots."""
        return self.frozen > 0 and has(self.frozen_by, "frostbite+6")

    @property
    def time_scale(self) -> float:
        """How fast the actor's clock runs (chill, freeze)."""
        if self.frozen > 0 or self.dazed > 0 or self.asleep > 0:
            return 0.0
        chill = self.stacks("chill")
        return max(0.1, 1 - config.STATUSES["chill"].slow * chill)

    def daze(self, seconds: float) -> None:
        """Dazed: the actor's clock stops for a moment (it can't move or act)."""
        self.dazed = max(self.dazed, seconds)

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
            self.frozen_by = source

    def update(self, owner, dt: float, effects: list[Effect], world=None) -> None:
        """Count down; deal damage over time every STATUS_TICK seconds."""
        self.frozen = max(0.0, self.frozen - dt)
        self.dazed = max(0.0, self.dazed - dt)
        self.asleep = max(0.0, self.asleep - dt)
        self.rooted = max(0.0, self.rooted - dt)
        self.scared = max(0.0, self.scared - dt)
        for k in list(self.cooldowns):
            self.cooldowns[k] -= dt
            if self.cooldowns[k] <= 0:
                del self.cooldowns[k]
        self.shocks = [t - dt for t in self.shocks if t - dt > 0]
        pos = (owner.x, owner.y)
        moving = self._last_pos is not None and pos != self._last_pos
        if self._last_pos is not None and dt > 0:
            self.pace = math.hypot(pos[0] - self._last_pos[0], pos[1] - self._last_pos[1]) / dt
        self._last_pos = pos
        burn = self.active.get("burn")
        if burn is not None and has(burn.source, "kindling+L"):          # Brushfire
            tile = (math.floor(owner.x), math.floor(owner.y))
            if tile != self.brush_tile:
                combos.append(("brushfire", owner, burn.source, tile))
                self.brush_tile = tile
        for name in list(self.active):
            s = self.active[name]
            if name in DOT:
                spec = config.STATUSES[name]
                rate = self._rate(owner, name, s, moving)
                n = s.stacks
                if name == "poison" and n > config.VIRULENCE[0]:        # (Pestilence)
                    n = config.VIRULENCE[0] + (n - config.VIRULENCE[0]) * config.PESTILENCE
                self._owed[name] = (self._owed.get(name, 0.0)
                                    + spec.dps * n * s.power * rate * dt)
                if name == "poison" and has(s.source, "virulence+9") \
                        and s.stacks >= config.BLACK_DEATH[0]:          # Black death
                    share = config.BLACK_DEATH[2 if getattr(owner, "boss", False) else 1]
                    self._owed[name] += owner.hp * share * dt
            elif name == "shock" and world is not None and has(s.source, "static+6") \
                    and _wet(world, owner):                              # Ground fault
                self._owed["shock"] = (self._owed.get("shock", 0.0)
                                       + config.GROUND_FAULT * s.power * dt)
            s.pyre = max(0.0, s.pyre - dt)
            if not s.lasting:
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
            tone = name
            if name == "poison" and has(source, "venom+L") and source.rng.random() \
                    < _crit_chance(source):                              # Venom sacs
                amount *= source.stats.crit_damage
                tone = "crit"
            dealt = owner.take_damage(amount, source, None)
            if dealt > 0:
                effects.append(Effect("number", owner.x, owner.y - owner.hit_radius, 0.0,
                                      value=max(1, round(dealt)), tone=tone))
                if name == "bleed" and has(source, "serrated+L"):
                    _bloodletting(source)
        self._owed.clear()

    def _rate(self, owner, name: str, s: Status, moving: bool) -> float:
        """How fast a damage-over-time status ticks right now."""
        rate = 1.0
        if name == "burn" and s.pyre > 0:                                  # Pyre
            rate = config.PYRE[0]
        elif name == "poison" and s.stacks >= config.INCUBATION[0] \
                and has(s.source, "virulence+3"):                          # Incubation
            rate = config.INCUBATION[1]
        elif name == "bleed":
            if s.double_moving and moving:                                 # Hemorrhage
                rate = config.BLOODHOUND if has(s.source, "hemorrhage+9") else 2.0
            if has(s.source, "hemorrhage+L") \
                    and getattr(s.source, "speed", 0.0) >= config.STILL_SPEED:
                rate *= config.BLOOD_RUSH                                  # Blood rush
            walk = getattr(getattr(owner, "espec", None), "speed", 0.0)
            if walk > 0 and self.pace > walk * config.SPURT[1] \
                    and has(s.source, "hemorrhage+6"):                     # Spurt
                rate = max(rate, config.SPURT[0])
        return rate


def _wet(world, actor) -> bool:
    """Ground fault: whether any tile under the actor is water, bog, mud...
    or it stands in a Downpour puddle (Stormjar +3)."""
    z = getattr(actor, "wet", None)
    if z is not None and z.age < z.life \
            and math.hypot(actor.x - z.x, actor.y - z.y) <= z.radius + actor.hit_radius:
        return True
    r = max(0.3, actor.hit_radius)
    for tx in range(math.floor(actor.x - r), math.floor(actor.x + r) + 1):
        for ty in range(math.floor(actor.y - r), math.floor(actor.y + r) + 1):
            if world.tile_at(tx, ty).name in config.WET_TILES:
                return True
    return False


def statuses_of(actor) -> Statuses:
    s = actor.status
    if s is None:
        s = actor.status = Statuses()
    return s


# Status combos waiting for the game to resolve them: (kind, victim, source).
combos: list[tuple[str, object, object]] = []


def inflict(victim, name: str, source, stacks: int = 1, chain: bool = True) -> None:
    """Put `stacks` of a status on `victim`, as applied by `source` (whose
    stats, if it's a hero, set its strength and duration). `chain` False:
    it can't set off a combo (Live wire's shock, so a spread can't spread
    itself round a crowd for ever)."""
    stats = getattr(source, "stats", None)
    power = stats.status_scale(config.STATUSES[name].tag) if stats is not None else 1.0
    if stats is not None and getattr(source, "spelling", False) and stats.has("crescendo+L"):
        power *= 1 + config.CRESCENDO_STEP * getattr(source, "streak", 0)   # (M28.3l: Tutti)
    duration = stats.duration_scale if stats is not None else 1.0
    cap = None
    if stats is not None and name == "poison" and stats.has("virulence"):
        cap, duration = config.VIRULENCE[0], duration * config.VIRULENCE[1]
        if stats.has("virulence+L"):
            cap = 10 ** 6                        # (Plaguebeak (L): Pestilence, no cap)
    hemorrhage = stats is not None and name == "bleed" and stats.has("hemorrhage")
    st = statuses_of(victim)
    before = st.stacks(name)
    if name == "chill" and before == 0:
        st.deep = 0                              # (Deep freeze: free of chill, it starts over)
    st.apply(victim, name, source, stacks, power, duration, cap, hemorrhage)
    if stats is None or not victim.alive:
        return
    _tricks(victim, st, name, before, source, stats)
    if name == "chill" and getattr(victim, "boss", False) and stats.has("frostbite+L"):
        _deep_freeze(victim, st, stacks, source)
    if not chain:
        return
    mix = stats.has("thermal_shock+L") and len(st.active) >= 2           # (Volatile mix)
    if stats.has("thermal_shock") and "geyser" not in st.cooldowns \
            and (mix or (name in ("burn", "chill") and st.has("burn") and st.has("chill"))):
        combos.append(("thermal_shock", victim, source))
    if stats.has("toxic_current") and name == "shock" and (
            st.has("poison") or (stats.has("toxic_current+L") and len(st.active) >= 2)):
        combos.append(("toxic_current", victim, source))


def _deep_freeze(victim, st: Statuses, stacks: int, source) -> None:
    """Rime Hood (L), Deep freeze: a boss that has taken DEEP_FREEZE[0]
    chill stacks (since it was last free of chill) freezes for [1] s, at
    most once every [2] s."""
    most, seconds, gap = config.DEEP_FREEZE
    st.deep += stacks
    if st.deep < most or "deep_freeze" in st.cooldowns:
        return
    st.deep = 0
    st.frozen = max(st.frozen, seconds)
    st.frozen_by = source
    st.cooldowns["deep_freeze"] = gap


def _crit_chance(hero) -> float:
    from .combat import crit_chance
    return crit_chance(hero.stats, hero)


def _bloodletting(hero) -> None:
    """Thornhelm (L): a bleed tick heals its hero BLOODLETTING[0] HP, at
    most [1] ticks' worth a second."""
    heal, most = config.BLOODLETTING
    now = getattr(hero, "time", 0.0)
    recent = [t for t in getattr(hero, "letting", []) if t > now - 1.0]
    if len(recent) >= most:
        hero.letting = recent
        return
    hero.letting = recent + [now]
    hero.heal(heal)


def _tricks(victim, st: Statuses, name: str, before: int, source, stats) -> None:
    """The head tricks set off by a status landing (M28.2b)."""
    boss = getattr(victim, "boss", False)
    now = st.stacks(name)
    full = config.STATUSES[name].max_stacks
    if name == "burn" and before < full <= now and stats.has("kindling+9"):
        st.active["burn"].pyre = config.PYRE[1]                          # Pyre
    elif name == "poison" and stats.has("venom+9") and now >= config.NEUROTOXIN[0] \
            and not boss and "neurotoxin" not in st.cooldowns:           # Neurotoxin
        st.rooted = max(st.rooted, config.NEUROTOXIN[1])
        st.cooldowns["neurotoxin"] = config.NEUROTOXIN[2]
    elif name == "bleed" and before < config.REND[0] <= now and stats.has("serrated+3") \
            and not getattr(victim, "rended", False):                    # Rend
        victim.rended = True
        combos.append(("rend", victim, source))
    elif name == "shock" and stats.has("static+9"):                      # Tempest
        st.shocks.append(config.TEMPEST[1])
        if len(st.shocks) >= config.TEMPEST[0]:
            st.shocks.clear()
            combos.append(("tempest", victim, source))


def on_hero_hit(victim, source, stats, crit: bool) -> None:
    """A hero's hit (one that may apply statuses) landed: the head tricks
    that act on hits (M28.2b). Statuses roll after this (roll_on_hit)."""
    st = victim.status
    if stats.has("kindling+3"):                                          # Kindle
        last, n = getattr(source, "kindle", (None, 0))
        n = n + 1 if last is victim else 1
        if n >= config.KINDLE:
            n = 0
            inflict(victim, "burn", source)
        source.kindle = (victim, n)
    if stats.has("frostbite+3"):                                         # Cold snap
        snapped = victim.__dict__.setdefault("cold_snapped", set())
        if id(source) not in snapped:
            snapped.add(id(source))
            inflict(victim, "chill", source)
    if crit and stats.has("venom+3") and victim.alive:                   # Fang
        inflict(victim, "poison", source, config.FANG)
    if getattr(source, "shocking", False) and victim.alive:              # Battery's attack
        inflict(victim, "shock", source)
    st = victim.status
    if st is None or not victim.alive:
        return
    burn = st.active.get("burn")
    if burn is not None and stats.has("wildfire+3"):                     # Fanned flames
        burn.left = max(burn.left, config.STATUSES["burn"].duration * stats.duration_scale)
    shock = st.active.get("shock")
    if shock is not None and stats.has("static+3"):                      # Build-up
        per, most = config.BUILD_UP
        shock.extra = min(most, shock.extra + per)


def daze(victim, seconds: float) -> bool:
    """Daze an enemy (M28.2, the War Drum): it stands still and can't act
    for a moment. Bosses aren't dazed."""
    if getattr(victim, "boss", False) or not victim.alive:
        return False
    statuses_of(victim).daze(seconds)
    return True


def roll_on_hit(victim, source, stats) -> None:
    """A hero's hit: each status their cards give rolls STATUS_BASE_CHANCE
    plus their status chance (Affliction)."""
    chance = config.STATUS_BASE_CHANCE + stats.status_chance
    for name in sorted(stats.statuses):
        if victim.alive and source.rng.random() < chance:
            inflict(victim, name, source)


def wounded(actor) -> bool:
    """Thornhelm +6 (Open wounds): a bleeding enemy can't heal."""
    return actor.status is not None and actor.status.wounded


# Where enemies burn right now, as (x, y, burn stacks): Blazecrown (L),
# Radiant heat (combat.situational_bonus). Refreshed each update_statuses.
burning: list[tuple[float, float, int]] = []


def update_statuses(actors, dt: float, effects: list[Effect], world=None) -> None:
    burning[:] = [(a.x, a.y, a.status.stacks("burn")) for a in actors
                  if a.alive and a.status is not None and a.status.has("burn")]
    for a in actors:
        s = a.status
        if s is not None and a.alive:
            s.update(a, dt, effects, world)
            if s.empty:
                a.status = None
