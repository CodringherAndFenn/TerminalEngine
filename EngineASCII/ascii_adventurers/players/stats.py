"""
players/stats.py -- the stat layer: every number cards can change.

A hero's HeroStats are rebuilt from scratch after every card taken (from
the hero's base plus every card, see players/cards.build_loadout), never
nudged in place, so stacking is exact and order-independent: all "add"
steps sum, all "mul" steps multiply, then the caps apply.

Damage buckets (catalog section 1.1). A hit from a hero is

    base x (1 + A) x (1 + T) x crit x M1 x M2 ... x vulnerability

  A  every "+X% damage" card plus conditionals (Point Blank, Broadhead...);
     they add up, so each one is worth a little less than the last;
  T  "+X% <tag> damage" for the hit's tags (fire, physical...);
  crit  crit_damage when the hit crits (chance: crit_chance);
  M  every "xN damage" card is its own multiplier (damage_mult here, plus
     per-hit ones such as Overload or Hunter's Mark);
  vulnerability  the victim's (shock: +15%).

Status damage is its own bucket: status base x (1 + status_power) x
(1 + T); no crit, no A (systems/statuses.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .. import config


@dataclass
class HeroStats:
    # Offense
    damage: float = 0.0              # bucket A (fraction: 0.2 = +20%)
    damage_mult: float = 1.0         # every "xN damage" card, multiplied
    tag_damage: dict = field(default_factory=dict)   # bucket T: tag -> fraction
    attack_speed: float = 0.0        # fraction: interval / (1 + attack_speed)
    interval_mult: float = 1.0       # "attacks 10% slower" (x1.1), "beats come sooner" (x0.85)
    crit_chance: float = config.BASE_CRIT_CHANCE
    crit_damage: float = config.BASE_CRIT_DAMAGE
    pellets: float = 0.0             # extra projectiles
    spread: float = 0.0              # extra fan width, degrees
    spread_mult: float = 1.0
    pierce: float = 0.0
    range: float = 0.0               # fraction: shot range, pulse reach
    shot_speed: float = 0.0          # fraction
    area: float = 0.0                # fraction: pulses, auras, novas, explosions
    duration: float = 0.0            # fraction: statuses, spells
    chain: float = 0.0               # extra lightning jumps
    chain_range: float = 0.0         # fraction
    chain_falloff: float = 0.0       # added to the weapon's falloff (less fade)
    # Statuses
    status_power: float = 0.0        # bucket S
    status_chance: float = 0.0       # chance per hit to apply `statuses`
    statuses: set = field(default_factory=set)   # what a status-chance roll applies
    sources: set = field(default_factory=set)    # every status you can inflict at all
    # Spells
    spell_cooldown: float = 0.0      # fraction faster
    spells: dict = field(default_factory=dict)   # spell key -> level
    spell_slots: float = config.SPELL_SLOTS
    # Card picks (Guild upgrades): extra rerolls / banishes each run
    rerolls: float = 0.0
    banishes: float = 0.0
    # Defense
    max_hp: float = 0.0              # added to the body's
    armor: float = 0.0
    dodge: float = 0.0
    regen: float = 0.0               # HP per second
    lifesteal: float = 0.0
    move: float = 0.0                # fraction
    # Economy
    pickup: float = 0.0              # fraction of PICKUP_RADIUS
    xp: float = 0.0
    loot: float = 0.0
    luck: float = 0.0
    # Hero-card numbers and rule changes
    steady_crit: float = 0.0         # Steady Aim: crit chance while standing still
    point_blank: float = 0.0         # Point Blank: bucket A within POINT_BLANK_RANGE
    broadhead: float = 0.0           # Broadhead: bucket A per enemy already passed
    flags: set = field(default_factory=set)

    # --- Derived numbers -------------------------------------------------------------

    def interval(self, base: float) -> float:
        return max(config.MIN_ATTACK_INTERVAL, base / (1 + self.attack_speed) * self.interval_mult)

    @property
    def area_scale(self) -> float:
        return 1 + self.area

    @property
    def duration_scale(self) -> float:
        return 1 + self.duration

    @property
    def cooldown_scale(self) -> float:
        return 1 - self.spell_cooldown

    @property
    def pickup_radius(self) -> float:
        return config.PICKUP_RADIUS * (1 + self.pickup)

    def tag_bonus(self, tags) -> float:
        """Bucket T for a hit with these tags (the bonuses add up)."""
        return sum(self.tag_damage.get(t, 0.0) for t in tags)

    def status_scale(self, tag: str) -> float:
        """Status damage multiplier for a status of this tag."""
        return (1 + self.status_power) * (1 + self.tag_damage.get(tag, 0.0))

    def has(self, flag: str) -> bool:
        return flag in self.flags

    def clamp(self) -> None:
        self.crit_chance = max(0.0, min(1.0, self.crit_chance))
        self.dodge = max(0.0, min(config.MAX_DODGE, self.dodge))
        self.lifesteal = max(0.0, min(config.MAX_LIFESTEAL, self.lifesteal))
        self.move = max(-0.9, min(config.MAX_MOVE_BONUS, self.move))
        self.area = max(-0.9, min(config.MAX_AREA_BONUS, self.area))
        self.spell_cooldown = max(0.0, min(config.MAX_SPELL_COOLDOWN, self.spell_cooldown))
        self.status_chance = max(0.0, min(1.0, self.status_chance))


def apply_mods(stats: HeroStats, steps: list[tuple[str, str, float]]) -> HeroStats:
    """Apply (stat, op, value) steps: adds and muls are order-free, then
    the caps."""
    for stat, op, val in steps:
        if op == "add":
            if stat.startswith("tag:"):
                tag = stat[4:]
                stats.tag_damage[tag] = stats.tag_damage.get(tag, 0.0) + val
            else:
                setattr(stats, stat, getattr(stats, stat) + val)
        elif op == "mul":
            setattr(stats, stat, getattr(stats, stat) * val)
        elif op == "flag":
            stats.flags.add(stat)
        elif op == "status":
            stats.statuses.add(stat)
            stats.sources.add(stat)
        elif op == "source":
            stats.sources.add(stat)
        elif op == "spell":
            stats.spells[stat] = min(config.SPELL_MAX_LEVEL, stats.spells.get(stat, 0) + 1)
        else:
            raise ValueError(f"unknown card op {op!r}")
    for key in stats.spells:
        inflicts = config.SPELLS[key].base.get("inflicts")
        if inflicts:
            stats.sources.add(inflicts)
    stats.clamp()
    return stats
