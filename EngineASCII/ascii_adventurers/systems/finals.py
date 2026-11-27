"""
systems/finals.py -- the kill order and the final bosses (M33,
design/FINALS.md 1-7).

THE KILL ORDER. The four ocean zones make two pairs (config.FINAL_PAIRS):
Paradise (heaven) against Pandemonium (hell), Pangaea (the past) against
Panopticon (the future). In each pair the one whose boss falls LAST wins:
it outlived its rival, so it holds that balance. The final is the two
winners fused (config.FINAL_OF): heaven + the past, the Fossil Angel;
heaven + the future, the Recording Angel; hell + the past, the Golden
Calf; hell + the future, the Feed. A pair is settled by its first kill
(the rival is then sure to fall last). The rule is hidden (user): nothing
in the game spells it out; the victory screen and the journal record the
order that led to each final, so players can work it out over runs.

The quests (systems/quests.py) keep the order (`Quests.order`) and wake the
final when the fourth ocean boss falls; a final has no arena -- its "lair"
is a `Roaming` one that goes wherever its boss is -- and hunts you across
the whole map (ai/finals.py).

RELICS FOR LATER RUNS (FINALS.md 14, M33.2). Every final has relics like
every boss (config.GEAR, unique=its boss key), but beating it ends the run,
so it doesn't drop them: beating it UNLOCKS them (the Guild's journal has
it). In later runs each of the four ocean bosses' drop is then one of its
own relics or one of the unlocked finals' (`relics_open`,
scenes/game.GameScene._drop_unique); the archivist's relics shelf lists the
finals' relics, ??? until their final is beaten.
"""

from __future__ import annotations

import math

import numpy as np

from .. import config


def pair_winners(order) -> tuple:
    """Each pair's winner so far: the one that falls last -- once one of a
    pair has fallen, the other (it's sure to fall after it); None for a
    pair untouched."""
    out = []
    for a, b in config.FINAL_PAIRS:
        if a in order and b in order:
            out.append(a if order.index(a) > order.index(b) else b)
        elif a in order:
            out.append(b)
        elif b in order:
            out.append(a)
        else:
            out.append(None)
    return tuple(out)


def final_for(order) -> str | None:
    """The final a kill order picks (a config.FINAL_OF key), once every
    ocean boss has fallen; None before."""
    if not all(z in order for pair in config.FINAL_PAIRS for z in pair):
        return None
    return config.FINAL_OF[pair_winners(order)]


def built(key: str | None) -> str | None:
    """The final that wakes for `key`: itself once it's built
    (config.FINALS), else FINAL_STAND_IN (M33.1: only the Fossil Angel)."""
    if key is None:
        return None
    return key if key in config.FINALS else config.FINAL_STAND_IN


def order_for(key: str) -> list[str]:
    """A kill order that leads to final `key` (dev mode, tests): each pair's
    loser first, then the winners."""
    winners = next(w for w, k in config.FINAL_OF.items() if k == key)
    losers = [b if w == a else a for (a, b), w in zip(config.FINAL_PAIRS, winners)]
    return losers + list(winners)


def order_text(order) -> str:
    """The kill order in words: "Paradise, Pangaea, Pandemonium, Panopticon"."""
    return ", ".join(z.capitalize() for z in order)


def ashore(layout, key: str) -> tuple[float, float]:
    """Where final `key` comes ashore: on the main island's coast between
    its two realms (config.FINAL_ASHORE: a direction), a few tiles inland."""
    dx, dy = config.FINAL_ASHORE.get(key, (0.0, -1.0))
    d = math.hypot(dx, dy) or 1.0
    ux, uy = dx / d, dy / d
    r = np.arange(0.0, layout.max_land_radius, 4.0)
    ids = layout.biome_ids(r * ux, r * uy, jitter=False)
    from ..world import biomes
    land = np.nonzero(ids != biomes.OCEAN.id)[0]
    edge = float(r[land[-1]]) if len(land) else layout.radius
    inland = max(0.0, edge - 14.0)
    return inland * ux, inland * uy


class Roaming:
    """A final's "lair": no arena, no walls -- wherever its boss is (the map
    pin, the boss bar, the world kept loaded round it), and every hero is
    always in it. It answers what the quests and the bosses ask of a lair
    (world/landmarks.Landmark)."""

    key = "roaming"
    kind = "lair"
    floor = None
    quest = ""
    npc = None
    x0 = y0 = w = h = 0
    rows: list = []

    def __init__(self, name: str, x: float = 0.0, y: float = 0.0) -> None:
        self.name = name
        self.boss = None
        self._at = (x, y)
        self.gate: list = []
        self.spots: list = []
        self.props: dict = {}
        self.radii = (0.0, 0.0)

    @property
    def cx(self) -> float:
        return self.boss.x if self.boss is not None else self._at[0]

    @property
    def cy(self) -> float:
        return self.boss.y if self.boss is not None else self._at[1]

    def inside(self, x: float, y: float, shrink: float = 0.0) -> bool:
        """Everywhere, while its boss hunts (so, like in any boss's arena:
        no mounts, no changing gear); nowhere before it wakes or once it's
        beaten."""
        return self.boss is not None and self.boss.alive

    def contains(self, x: float, y: float, margin: float = 0.0) -> bool:
        return False

    def tile_at(self, tx: int, ty: int):
        return None


def ocean_bosses() -> frozenset:
    """The four ocean zones' bosses (their quests' bosses): the ones that
    drop the unlocked finals' relics."""
    return frozenset(q.boss for q in config.QUESTS.values() if q.biome in config.ZONE_PLACES)


def final_bosses() -> frozenset:
    """The built finals' bosses (their relics are the finals' relics)."""
    return frozenset(q.boss for q in config.FINALS.values())


def beaten(guild, key: str) -> bool:
    """Has this guild beaten final `key` (a config.FINALS key) in any run?"""
    e = getattr(guild, "journal", {}).get(key) if guild is not None else None
    return bool(e) and e.get("wins", 0) > 0


def relics_open(guild) -> tuple:
    """The finals' relics this guild has unlocked: every relic of each final
    it has beaten, in a fixed order (the drop's seed picks by index)."""
    out: list = []
    for key, q in config.FINALS.items():
        if beaten(guild, key):
            out.extend(config.BOSS_UNIQUES.get(q.boss, ()))
    return tuple(out)


def is_final(s) -> bool:
    """Is quest state `s` a final's (M33)?"""
    return getattr(s.spec, "kind", "") == "final"
