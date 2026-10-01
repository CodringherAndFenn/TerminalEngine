"""
systems/spells.py -- spells and items that cards grant (config.SPELLS).

A hero has up to SPELL_SLOTS of them. Each works on its own, every
simulation step, around the hero:

  orbit (Orbiting Daggers)  `count` daggers circle the hero at `radius`
         tiles, turning `turn` rad/s; each dagger hits an enemy it touches
         at most once every `rehit` s.
  aura  (Ember Aura)        every `interval` s, every enemy within `radius`
         gets `stacks` of the spell's status (burn).
  nova  (Frost Nova)        every `interval` s, a ring bursts out to
         `radius`: `damage` and `stacks` of its status (chill) to every
         enemy in it that isn't behind a wall.

A spell's numbers are its level-1 `base` with each further level's
change applied (SpellState.params). The hero's stats then scale them
where they're used: area x radius, spell cooldown x interval, and every
hit goes through combat.strike (damage %, tag %, crits, on-hit statuses).

Positions (the daggers' angle) are simulation state, so they replay
exactly; drawing only reads them.
"""

from __future__ import annotations

import math

from .. import config
from ..entities.effects import Effect
from .combat import _may_hurt, strike
from .raycast import first_hit
from .statuses import inflict

DAGGER_HIT_RADIUS = 0.45     # tiles


class SpellState:
    def __init__(self, key: str, level: int = 1) -> None:
        self.key = key
        self.spec = config.SPELLS[key]
        self.level = 0
        self.params: dict = {}
        self.timer = 0.0           # aura / nova: seconds to the next pulse
        self.angle = 0.0           # orbit: where the first dagger is
        self.clock = 0.0
        self._next_hit: dict[tuple[int, int], float] = {}   # (dagger, id(enemy)) -> time
        self.set_level(level)
        self.timer = self.params.get("interval", 0.0) * 0.5   # first pulse comes soon

    def set_level(self, level: int) -> None:
        self.level = level
        p = dict(self.spec.base)
        for _, changes in self.spec.levels[:level - 1]:
            for name, op, val in changes:
                p[name] = p[name] + val if op == "add" else p[name] * val
        self.params = p

    def dagger_positions(self, hero) -> list[tuple[float, float, float]]:
        """(x, y, angle) of each dagger; angle is where it points (along
        its orbit)."""
        p = self.params
        n = int(p["count"])
        r = p["radius"] * _area(hero)
        out = []
        for i in range(n):
            a = self.angle + i * math.tau / n
            out.append((hero.x + math.cos(a) * r, hero.y + math.sin(a) * r, a + math.pi / 2))
        return out


def _area(hero) -> float:
    return hero.stats.area_scale if hero.stats is not None else 1.0


def _cooldown(hero) -> float:
    return hero.stats.cooldown_scale if hero.stats is not None else 1.0


def sync_spells(spells: dict[str, SpellState], levels: dict[str, int]) -> None:
    """Match a player's spell states to their cards (new spells, level-ups)."""
    for key, level in levels.items():
        if key not in spells:
            spells[key] = SpellState(key, level)
        elif spells[key].level != level:
            spells[key].set_level(level)
    for key in [k for k in spells if k not in levels]:
        del spells[key]


def update_spells(hero, spells: dict[str, SpellState], world, actors, effects: list[Effect],
                  dt: float) -> list[str]:
    """Run a hero's spells for one step. Returns sound events."""
    events: list[str] = []
    for s in spells.values():
        s.clock += dt
        kind = s.spec.kind
        if kind == "orbit":
            _orbit(hero, s, actors, effects, dt)
        elif kind == "aura":
            _aura(hero, s, actors, dt)
        elif kind == "nova":
            events += _nova(hero, s, world, actors, effects, dt)
    return events


def _near(hero, actors, reach: float):
    for a in actors:
        if a.hittable and _may_hurt(hero, a) \
                and abs(a.x - hero.x) <= reach + a.hit_radius \
                and abs(a.y - hero.y) <= reach + a.hit_radius:
            yield a


def _orbit(hero, s: SpellState, actors, effects, dt: float) -> None:
    p = s.params
    s.angle = (s.angle + p["turn"] * dt) % math.tau
    daggers = s.dagger_positions(hero)
    reach = p["radius"] * _area(hero) + DAGGER_HIT_RADIUS
    for a in _near(hero, actors, reach):
        for i, (x, y, facing) in enumerate(daggers):
            if math.hypot(a.x - x, a.y - y) > DAGGER_HIT_RADIUS + a.hit_radius:
                continue
            key = (i, id(a))
            if s._next_hit.get(key, -1.0) > s.clock:
                continue
            s._next_hit[key] = s.clock + p["rehit"]
            strike(a, p["damage"], hero, facing, effects, s.spec.tags)
            effects.append(Effect("impact", a.x, a.y, facing))
            if not a.alive:
                break
    if len(s._next_hit) > 256:          # forget enemies long gone
        s._next_hit = {k: t for k, t in s._next_hit.items() if t > s.clock}


def _aura(hero, s: SpellState, actors, dt: float) -> None:
    p = s.params
    s.timer -= dt
    if s.timer > 0:
        return
    s.timer += p["interval"] * _cooldown(hero)
    r = p["radius"] * _area(hero)
    for a in _near(hero, actors, r):
        if math.hypot(a.x - hero.x, a.y - hero.y) <= r + a.hit_radius:
            inflict(a, p["inflicts"], hero, int(p["stacks"]))


def _nova(hero, s: SpellState, world, actors, effects, dt: float) -> list[str]:
    p = s.params
    s.timer -= dt
    if s.timer > 0:
        return []
    s.timer += p["interval"] * _cooldown(hero)
    r = p["radius"] * _area(hero)
    effects.append(Effect("nova", hero.x, hero.y, size=r))
    for a in list(_near(hero, actors, r)):
        if math.hypot(a.x - hero.x, a.y - hero.y) > r + a.hit_radius:
            continue
        if first_hit(world.tile_at, hero.x, hero.y, a.x, a.y) is not None:
            continue
        angle = math.atan2(a.y - hero.y, a.x - hero.x)
        strike(a, p["damage"], hero, angle, effects, s.spec.tags)
        if a.alive:
            inflict(a, p["inflicts"], hero, int(p["stacks"]))
    return ["nova"]
