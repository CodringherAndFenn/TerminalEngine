"""
systems/spawner.py -- which enemies exist where, and waking/sleeping them.

Deterministic placement: each chunk's enemy roster is a pure function of
(seed, chunk x, chunk y) -- how many (BIOME_ENEMY_DENSITY for the biome at
the chunk's centre, times ENEMY_DENSITY_MULTIPLIER), which types
(config.ENEMIES weights for that biome) and where (random tiles that suit
the type: spell towers next to ruined walls, burrowers in sand, bodies that
fit). The config.py section "How many enemies, and which" explains the
numbers. Each enemy gets a stable spawn id (cx, cy, k).

Life cycle:
  * a chunk loads -> its roster is remembered;
  * each frame, every rostered enemy that is asleep and has come within
    ENEMY_WAKE_MARGIN of the view wakes at its spawn point (skipping ids
    that were killed);
  * an awake enemy that ends up beyond ENEMY_DESPAWN_MARGIN is put to
    sleep (removed); it wakes fresh at its spawn point when you come back;
  * an enemy dies -> its id is remembered forever, so kills stay killed.
No enemies spawn within ENEMY_FREE_RADIUS of the spawn point, nor inside the
current view (so nothing pops into existence in front of you).
"""

from __future__ import annotations

import math
import random

from .. import config
from ..ai import make_enemy
from ..world.rng import hash_coords
from .collision import hull_hits_solid


class Spawner:
    def __init__(self, world, seed: int) -> None:
        self.world = world
        self.seed = seed
        self.dead: set = set()
        self.awake: dict = {}          # spawn id -> enemy
        self.rosters: dict = {}        # loaded chunk -> its roster

    def roster(self, cx: int, cy: int) -> list[tuple[tuple, str, float, float]]:
        """[(spawn id, enemy key, x, y)] for one chunk. Deterministic."""
        n = config.CHUNK_SIZE
        rng = random.Random(hash_coords(self.seed, 0xE7, cx, cy))
        mx, my = cx * n + n / 2, cy * n + n / 2
        sx, sy = self.world.spawn_point()
        if math.hypot(mx - sx, my - sy) < config.ENEMY_FREE_RADIUS:
            return []
        biome = self.world.biome_at(math.floor(mx), math.floor(my)).name
        expected = config.BIOME_ENEMY_DENSITY.get(biome, 0.0) * config.ENEMY_DENSITY_MULTIPLIER
        count = int(expected) + (rng.random() < expected - int(expected))
        choices = [(k, s.weight) for k, s in config.ENEMIES.items() if biome in s.biomes]
        out = []
        for k in range(count):
            if not choices:
                break
            key = rng.choices([c[0] for c in choices], [c[1] for c in choices])[0]
            pos = self._place(key, cx, cy, rng)
            if pos is not None:
                out.append(((cx, cy, k), key, *pos))
        return out

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
            if spec.kind == "tower" and not self._near_wall(tx, ty):
                continue
            if spec.kind in ("puffer", "burrower"):
                return x, y           # they float / tunnel: no footprint needed
            half = self._half_size(spec)
            if not hull_hits_solid(self.world, x, y, 0.0, half, half):
                return x, y
        return None

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
        """Remember a newly generated chunk's roster (spawned later, by
        distance, in update())."""
        self.rosters[(cx, cy)] = self.roster(cx, cy)

    def update(self, enemies: list, cx: float, cy: float, half_w: float, half_h: float) -> None:
        """Wake and sleep enemies by their own distance from the view
        centered at (cx, cy) with half-size (half_w, half_h) tiles.

          * asleep, spawn point within ENEMY_WAKE_MARGIN of the view (but not
            inside it) -> woken at its spawn point;
          * awake and farther than ENEMY_DESPAWN_MARGIN -> put to sleep.
        The gap between the two margins stops an enemy flickering between
        states at the boundary. Decisions are per enemy, not per chunk: a
        chunk is generated when its *near* edge approaches, so its far half
        is still far away then.
        """
        sleep_m = config.ENEMY_DESPAWN_MARGIN
        keep = []
        for e in enemies:
            if abs(e.x - cx) > half_w + sleep_m or abs(e.y - cy) > half_h + sleep_m:
                self.awake.pop(e.spawn_id, None)
            else:
                keep.append(e)
        enemies[:] = keep

        wake_m = config.ENEMY_WAKE_MARGIN
        forget_m = config.UNLOAD_MARGIN + config.CHUNK_SIZE
        n = config.CHUNK_SIZE
        for key in list(self.rosters):
            kx, ky = key[0] * n + n / 2, key[1] * n + n / 2
            if abs(kx - cx) > half_w + forget_m or abs(ky - cy) > half_h + forget_m:
                del self.rosters[key]   # chunk long gone; reloaded chunks re-register
                continue
            for sid, name, x, y in self.rosters[key]:
                if sid in self.dead or sid in self.awake:
                    continue
                dx, dy = abs(x - cx), abs(y - cy)
                if dx > half_w + wake_m or dy > half_h + wake_m:
                    continue
                if dx <= half_w + 2 and dy <= half_h + 2:
                    continue            # never pop into existence on screen
                e = make_enemy(name, x, y,
                               random.Random(hash_coords(self.seed, 0xA1, *sid)), sid)
                self.awake[sid] = e
                enemies.append(e)

    def killed(self, enemy) -> None:
        self.awake.pop(enemy.spawn_id, None)
        if enemy.spawn_id is not None:
            self.dead.add(enemy.spawn_id)
