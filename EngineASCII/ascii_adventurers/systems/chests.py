"""
systems/chests.py -- the chests of gear in the ring biomes (M28.4b/c;
design/GEAR.md 4.2 and 20).

Every chest is a landmark (world/landmarks._chests): a small clearing with
a CHEST tile in the middle, CHESTS_PER_BIOME per ring biome. A living hero
within CHEST_RADIUS of one opens it: the tile becomes CHEST_OPEN and a
piece of gear rolled for them (CHEST_LUCK extra luck) lies in front of it
(scenes/game.py _drop_piece, the pickup panel).
  * Guarded chests have CHEST_GUARDS of a biome enemy standing round them
    (fixed spawns, systems/spawner.place; ids (CHEST_SID, chest, 1..n)); a
    counter shows over the chest until they're dead, and walking up warns.
  * Mimics (CHEST_MIMIC of the chests) look like any chest: touched, the
    tile vanishes and a `mimic` (ai/mimic.py, an elite) bites; killed, it
    drops an epic or better piece (on_death).
Chests are only looked at within CHEST_LOOK of a hero (their chunks are
loaded) and pinned on the maps once a hero came within CHEST_SEEN.
"""

from __future__ import annotations

import math
import random

from .. import config
from ..entities.effects import Effect
from ..world import tiles
from ..world.rng import hash_coords
from .quests import free_spot

CHEST_SID = 0xC4E5          # fixed spawn ids: (CHEST_SID, chest n, 0 the mimic / 1.. guards)


class ChestState:
    def __init__(self, mark) -> None:
        self.mark = mark
        self.n: int = mark.props["n"]
        self.x, self.y = mark.cx, mark.cy
        self.biome: str = mark.biome
        self.guarded: bool = bool(mark.props.get("guarded"))
        self.mimic: bool = bool(mark.props.get("mimic"))
        self.guard: str | None = mark.props.get("guard")
        self.opened = False          # opened, or sprung (a mimic)
        self.seen = False
        self.warned = False          # the "guarded" reminder shown since someone walked up
        self.sprung = None           # the mimic enemy, once it bit

    @property
    def done(self) -> bool:
        return self.opened


class Chests:
    def __init__(self, scene) -> None:
        self.scene = scene
        self.world = scene.world
        self.states: list[ChestState] = []
        layout = getattr(self.world, "layout", None)
        if layout is None:
            return
        from ..world.landmarks import chest_marks
        for mark in chest_marks(layout):
            s = ChestState(mark)
            self.states.append(s)
            self._place_guards(s)

    # --- Guards ---------------------------------------------------------------------

    def _place_guards(self, s: ChestState) -> None:
        sp = self.scene.spawner
        if sp is None or not s.guarded or s.guard is None:
            return
        n = config.CHEST_GUARDS
        for k in range(n):
            a = s.n * 0.9 + k * math.tau / n
            r = config.CHEST_GUARD_RING
            sp.place((CHEST_SID, s.n, k + 1), s.guard,
                     s.x + math.cos(a) * r, s.y + math.sin(a) * r * 0.75)

    def guards_left(self, s: ChestState) -> int:
        sp = self.scene.spawner
        if sp is None or not s.guarded or s.guard is None:
            return 0
        return sum(1 for k in range(config.CHEST_GUARDS) if (CHEST_SID, s.n, k + 1) not in sp.dead)

    # --- Queries ----------------------------------------------------------------------

    def near(self, x: float, y: float, within: float) -> list[ChestState]:
        return [s for s in self.states if math.hypot(s.x - x, s.y - y) <= within]

    def pins(self) -> list[tuple[float, float, str, str]]:
        """Map pins: every chest seen, grey once opened (a mimic's spot too)."""
        return [(s.x, s.y, "chest_done" if s.done else "chest", "CHEST")
                for s in self.states if s.seen]

    # --- Simulation step ----------------------------------------------------------------

    def step(self, dt: float, players) -> None:
        heroes = [p for p in players if p.alive and not p.ghost]
        if not heroes:
            return
        for s in self.states:
            if s.done:
                continue
            best = min(heroes, key=lambda p: math.hypot(p.hero.x - s.x, p.hero.y - s.y))
            dist = math.hypot(best.hero.x - s.x, best.hero.y - s.y)
            if dist <= config.CHEST_SEEN:
                s.seen = True
            if dist > config.CHEST_RADIUS + best.hero.hit_radius:
                s.warned = False
                continue
            if self.guards_left(s):
                if not s.warned:
                    s.warned = True
                    self.scene.effects.append(Effect("toast", s.x, s.y - 1.5,
                                                     label="IT'S GUARDED!"))
                continue
            if s.mimic:
                self._spring(s, best)
            else:
                self._open(s, best)

    def _open(self, s: ChestState, p) -> None:
        s.opened = True
        if hasattr(self.world, "set_tile"):
            self.world.set_tile(math.floor(s.x), math.floor(s.y), tiles.CHEST_OPEN)
        self.scene.effects.append(Effect("nova", s.x, s.y, size=1.5))
        self.scene.effects.append(Effect("toast", s.x, s.y - 2, label="CHEST OPENED"))
        self.scene._drop_piece(p, s.x, s.y + 1.0, luck=config.CHEST_LUCK)

    def _spring(self, s: ChestState, p) -> None:
        """A mimic: the chest tile goes, and the mimic bites."""
        s.opened = True
        if hasattr(self.world, "set_tile"):
            from ..world.landmarks import CLEARING
            self.world.set_tile(math.floor(s.x), math.floor(s.y),
                                CLEARING.get(s.biome, tiles.MUD))
        sp = self.scene.spawner
        rng = random.Random(hash_coords(getattr(self.world, "seed", 0) or 0, 0xC4E6, s.n))
        if sp is not None:
            e = sp.wake("mimic", s.x, s.y, (CHEST_SID, s.n, 0), rng)
        else:
            from ..ai import make_enemy
            e = make_enemy("mimic", s.x, s.y, rng, (CHEST_SID, s.n, 0))
        e.biome = s.biome
        e.alert = True
        e.target = p.hero
        e.last_known = (p.hero.x, p.hero.y)
        s.sprung = e
        self.scene.enemies.append(e)
        self.scene.effects.append(Effect("debris", s.x, s.y))
        self.scene.effects.append(Effect("toast", s.x, s.y - 2, label="A MIMIC!"))
        self.scene._sounds.append("chime")

    def on_death(self, enemy, killer) -> None:
        """A mimic killed: an epic or better piece for its killer (the local
        player if nobody gets the credit)."""
        sid = getattr(enemy, "spawn_id", None)
        if not (isinstance(sid, tuple) and len(sid) == 3 and sid[0] == CHEST_SID and sid[2] == 0):
            return
        s = next((c for c in self.states if c.n == sid[1]), None)
        if s is None or s.sprung is not enemy:
            return
        s.sprung = None
        p = killer if killer is not None else next(
            (q for q in self.scene.players if not q.ghost and q.alive), None)
        if p is None:
            return
        x, y = free_spot(self.world, enemy.x, enemy.y, config.TILE_PX_W * 0.4)
        self.scene._drop_piece(p, x, y, min_rarity_="epic")

    # --- Dev -------------------------------------------------------------------------

    def nearest_shut(self, x: float, y: float) -> ChestState | None:
        shut = [s for s in self.states if not s.done]
        return min(shut, key=lambda s: math.hypot(s.x - x, s.y - y)) if shut else None
