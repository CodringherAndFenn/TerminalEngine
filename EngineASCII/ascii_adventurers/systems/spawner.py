"""
systems/spawner.py -- which enemies exist where, and waking/sleeping them.

Deterministic placement: each chunk's enemy roster is a pure function of
(seed, chunk x, chunk y) -- how many (BIOME_ENEMY_DENSITY for the biome at
the chunk's centre, times ENEMY_DENSITY_MULTIPLIER), which types
(config.ENEMIES weights for that biome) and where (random tiles that suit
the type: spell towers next to ruined walls, burrowers in sand, bodies that
fit). The config.py section "How many enemies, and which" explains the
numbers. Each enemy gets a stable spawn id (cx, cy, k).

Life cycle (update_views, once per simulation step):
  * a chunk's roster is worked out the first time a player comes near
    enough for it to matter, and forgotten when everyone is far away;
  * every rostered enemy that is asleep and has come within
    ENEMY_WAKE_MARGIN of a player's view wakes at its spawn point (skipping ids
    that were killed);
  * an awake enemy that ends up beyond ENEMY_DESPAWN_MARGIN is put to
    sleep (removed); it wakes fresh at its spawn point when you come back;
  * an enemy dies -> its id is remembered forever, so kills stay killed.
No enemies spawn within ENEMY_FREE_RADIUS of the spawn point, nor inside
any player's view (so nothing pops into existence in front of anyone), nor
on a landmark (world/landmarks.py: quest camps and boss lairs stay quiet).

Fixed spawns (M17): the quest system adds its own enemies (the
psychedelic frogs) with `place`; they wake, sleep and stay dead like
rostered ones, except that they may wake inside a view (marked `fresh`,
so the quest can show them appearing). Bosses (`boss` set) are never put
to sleep.
"""

from __future__ import annotations

import math
import random

from .. import config
from ..ai import make_enemy
from ..world.rng import hash_coords
from .collision import hull_hits_solid


PACK_ID = 1000      # a pack's other members' roster ids start here (a chunk's own are < it)


class Spawner:
    def __init__(self, world, seed: int) -> None:
        self.world = world
        self.seed = seed
        self.dead: set = set()
        self.awake: dict = {}          # spawn id -> enemy
        self.rosters: dict = {}        # loaded chunk -> its roster
        self.fixed: dict = {}          # spawn id -> (enemy key, x, y): placed by quests
        self.level = 1                 # the players' level: enemies wake this tough
        # Pacts and cards (systems/run_rules.py): more enemies, tougher,
        # harder-hitting, faster.
        self.density = 1.0
        self.level_bonus = 0
        self.damage_bonus = 0.0
        self.haste = 0.0
        # The run's difficulty level (P5): x max HP and x damage, bosses too.
        self.hp_mult = 1.0
        self.damage_mult = 1.0

    def roster(self, cx: int, cy: int) -> list[tuple[tuple, str, float, float]]:
        """[(spawn id, enemy key, x, y)] for one chunk. Deterministic."""
        n = config.CHUNK_SIZE
        rng = random.Random(hash_coords(self.seed, 0xE7, cx, cy))
        mx, my = cx * n + n / 2, cy * n + n / 2
        sx, sy = self.world.spawn_point()
        if math.hypot(mx - sx, my - sy) < config.ENEMY_FREE_RADIUS:
            return []
        biome = self.world.biome_at(math.floor(mx), math.floor(my)).name
        expected = (config.BIOME_ENEMY_DENSITY.get(biome, 0.0) * config.ENEMY_DENSITY_MULTIPLIER
                    * self.density)
        count = int(expected) + (rng.random() < expected - int(expected))
        choices = [(k, s.weight) for k, s in config.ENEMIES.items() if biome in s.biomes]
        out = []
        for k in range(count):
            if not choices:
                break
            key = rng.choices([c[0] for c in choices], [c[1] for c in choices])[0]
            pos = self._place(key, cx, cy, rng)
            if pos is None:
                continue
            out.append(((cx, cy, k), key, *pos))
            # A pack (P7: rats, geese, hounds): the rest round the first, on
            # free ground, each with its own id (cx, cy, PACK_ID + 16 k + j).
            lo, hi = config.ENEMIES[key].group
            if hi <= 1:
                continue                     # (no extra dice: other rosters stay as they were)
            for j in range(1, rng.randint(lo, hi)):
                spot = self._near(key, *pos, rng)
                if spot is not None:
                    out.append(((cx, cy, PACK_ID + 16 * k + j), key, *spot))
        return out

    def _near(self, key, x: float, y: float, rng) -> tuple[float, float] | None:
        """A free spot within 2.5 tiles of (x, y) for one more of a pack."""
        half = self._half_size(config.ENEMIES[key])
        for _ in range(8):
            a, r = rng.uniform(0, math.tau), rng.uniform(1.0, 2.5)
            px, py = x + math.cos(a) * r, y + math.sin(a) * r
            if not hull_hits_solid(self.world, px, py, 0.0, half, half):
                return px, py
        return None

    def _place(self, key, cx, cy, rng) -> tuple[float, float] | None:
        """A random spot in the chunk that suits this enemy (a few tries)."""
        n = config.CHUNK_SIZE
        spec = config.ENEMIES[key]
        for _ in range(12):
            # 4 tiles in from the edges: the fit/wall checks below then never
            # touch a neighbouring chunk that may not be generated yet.
            tx = cx * n + rng.randrange(4, n - 4)
            ty = cy * n + rng.randrange(4, n - 4)
            sx, sy = self.world.spawn_point()
            if math.hypot(tx + 0.5 - sx, ty + 0.5 - sy) < config.ENEMY_FREE_RADIUS:
                continue
            biome = self.world.biome_at(tx, ty).name
            if biome not in spec.biomes:
                continue
            x, y = tx + 0.5, ty + 0.5
            if any(m.contains(x, y, config.LANDMARK_QUIET) for m in self._landmarks):
                continue
            if spec.kind == "tower" and not self._near_wall(tx, ty):
                continue
            if spec.kind in ("puffer", "burrower"):
                return x, y           # they float / tunnel: no footprint needed
            half = self._half_size(spec)
            if not hull_hits_solid(self.world, x, y, 0.0, half, half):
                return x, y
        return None

    @property
    def _landmarks(self) -> list:
        return getattr(self.world, "landmarks", ())

    def place(self, sid, key: str, x: float, y: float) -> None:
        """Add one fixed enemy (a quest's): it wakes and sleeps at (x, y)
        like any other, and once killed stays dead. `sid`: a tuple of ints
        that no chunk roster uses (those are (cx, cy, k))."""
        self.fixed[sid] = (key, x, y)

    def _near_wall(self, tx, ty) -> bool:
        from ..world import tiles
        return any(self.world.tile_at(tx + dx, ty + dy) is tiles.WALL
                   for dx in (-3, -2, 2, 3) for dy in (-2, 0, 2))

    @staticmethod
    def _half_size(spec) -> float:
        if spec.body:
            return config.BODIES[spec.body].size_px / 2 + 2
        return spec.size_px / 2 + 1

    # --- Life cycle -----------------------------------------------------------------

    def chunk_loaded(self, cx: int, cy: int) -> None:
        """Work out a chunk's roster ahead of time (optional: update_views
        does it on demand)."""
        self.rosters[(cx, cy)] = self.roster(cx, cy)

    def update(self, enemies: list, cx: float, cy: float, half_w: float, half_h: float) -> None:
        """Wake and sleep enemies around one view (see update_views)."""
        self.update_views(enemies, [(cx, cy, half_w, half_h)])

    def update_views(self, enemies: list, views) -> None:
        """Wake and sleep enemies by their own distance from the views --
        one per player, each (x, y, half_w, half_h) in tiles:

          * asleep, spawn point within ENEMY_WAKE_MARGIN of some view (but
            not inside any view) -> woken at its spawn point;
          * awake and farther than ENEMY_DESPAWN_MARGIN from every view ->
            put to sleep.
        The gap between the two margins stops an enemy flickering between
        states at the boundary. Decisions are per enemy, not per chunk: a
        chunk is generated when its *near* edge approaches, so its far half
        is still far away then.
        """
        views = list(views)

        def near(x, y, margin):
            return any(abs(x - vx) <= hw + margin and abs(y - vy) <= hh + margin
                       for vx, vy, hw, hh in views)

        sleep_m = config.ENEMY_DESPAWN_MARGIN
        keep = []
        for e in enemies:
            if getattr(e, "boss", False) or near(e.x, e.y, sleep_m):
                keep.append(e)
            else:
                self.awake.pop(e.spawn_id, None)
        enemies[:] = keep

        wake_m = config.ENEMY_WAKE_MARGIN
        forget_m = config.UNLOAD_MARGIN + config.CHUNK_SIZE
        n = config.CHUNK_SIZE
        for key in list(self.rosters):
            if not near(key[0] * n + n / 2, key[1] * n + n / 2, forget_m):
                del self.rosters[key]   # far away now; recomputed if we come back
        # Every chunk that could hold an enemy close enough to wake. Rosters
        # are computed here when first needed (not when the chunk happens to
        # finish loading), so who wakes when depends only on where the
        # players are -- the same on every machine and at any frame rate.
        wanted = set()
        for vx, vy, hw, hh in views:
            kx0, kx1 = math.floor((vx - hw - wake_m) / n), math.floor((vx + hw + wake_m) / n)
            ky0, ky1 = math.floor((vy - hh - wake_m) / n), math.floor((vy + hh + wake_m) / n)
            wanted.update((kx, ky) for ky in range(ky0, ky1 + 1) for kx in range(kx0, kx1 + 1))
        rosters = []
        for key in sorted(wanted):
            roster = self.rosters.get(key)
            if roster is None:
                roster = self.rosters[key] = self.roster(*key)
            rosters.append(roster)
        for roster in rosters:
            for sid, name, x, y in roster:
                if sid in self.dead or sid in self.awake:
                    continue
                if not near(x, y, wake_m) or near(x, y, 2):
                    continue            # too far, or would pop into existence on screen
                enemies.append(self.wake(name, x, y, sid))
        # Quest enemies may appear in view (you're often standing at their
        # spot when you take the quest); `fresh` lets the quest show it.
        for sid, (name, x, y) in self.fixed.items():
            if sid in self.dead or sid in self.awake or not near(x, y, wake_m):
                continue
            e = self.wake(name, x, y, sid)
            e.fresh = True
            enemies.append(e)

    def wake(self, name: str, x: float, y: float, sid=None, rng: random.Random | None = None):
        """A new enemy of kind `name` at (x, y), as tough as the players'
        level (and the pacts, and the difficulty) make it. With a spawn id (a tuple of ints)
        it's tracked as awake and its dice come from that id; bosses' adds
        have none and bring their own dice."""
        if rng is None:
            rng = random.Random(hash_coords(self.seed, 0xA1, *sid))
        e = make_enemy(name, x, y, rng, sid)
        e.scale_to_level(self.level + self.level_bonus)
        if self.hp_mult != 1.0 and hasattr(e, "toughen"):
            e.toughen(self.hp_mult)
        e.damage_mult *= (1 + self.damage_bonus) * self.damage_mult
        e.haste = self.haste
        if sid is not None:
            self.awake[sid] = e
        return e

    def killed(self, enemy) -> None:
        self.awake.pop(enemy.spawn_id, None)
        if enemy.spawn_id is not None:
            self.dead.add(enemy.spawn_id)
