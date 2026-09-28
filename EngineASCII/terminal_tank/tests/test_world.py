import math
import time
import unittest
from collections import Counter, deque

from terminal_tank import config
from terminal_tank.entities.tank import Tank
from terminal_tank.systems.collision import hull_hits_solid
from terminal_tank.world import biomes, tiles
from terminal_tank.world.chunked import ChunkedWorld
from terminal_tank.world.generator import build_chunk, sample_biome
from terminal_tank.world.noise import value_noise_at, value_noise_grid
from terminal_tank.world.tiles import Damage

N = config.CHUNK_SIZE


def finish(gen):
    try:
        while True:
            next(gen)
    except StopIteration as done:
        return done.value


class NoiseTest(unittest.TestCase):
    def test_grid_matches_point_sampling_across_chunk_edges(self):
        # Two neighbouring chunks' grids must agree with the single global
        # field -- that's what makes chunk seams invisible.
        for x0 in (-N, 0, N):
            g = value_noise_grid(9, 3, x0, 5, N, N, 13.0)
            for y in (0, N - 1):
                for x in (0, N - 1):
                    self.assertAlmostEqual(g[y][x], value_noise_at(9, 3, x0 + x + 0.5, 5 + y + 0.5, 13.0))

    def test_smooth(self):
        g = value_noise_grid(1, 1, 0, 0, 64, 1, 20.0)[0]
        self.assertLess(max(abs(a - b) for a, b in zip(g, g[1:])), 0.2)


class DeterminismTest(unittest.TestCase):
    def test_same_seed_same_chunk_regardless_of_order(self):
        keys = [(0, 0), (3, -2), (-5, 7), (1, 1)]
        a = {k: finish(build_chunk(123, *k)) for k in keys}
        b = {k: finish(build_chunk(123, *k)) for k in reversed(keys)}
        for k in keys:
            self.assertEqual(a[k].tiles, b[k].tiles, k)
            self.assertEqual(a[k].glyphs, b[k].glyphs, k)

    def test_different_seeds_differ(self):
        self.assertNotEqual(finish(build_chunk(1, 9, 9)).tiles, finish(build_chunk(2, 9, 9)).tiles)

    def test_world_order_independent(self):
        w1, w2 = ChunkedWorld(77), ChunkedWorld(77)
        pts = [(-100, 40), (300, -250), (5, 5), (-700, -700)]
        first = [w1.tile_at(*p) for p in pts]
        second = [w2.tile_at(*p) for p in reversed(pts)][::-1]
        self.assertEqual(first, second)


class SeamTest(unittest.TestCase):
    def test_biomes_continue_across_chunk_edges(self):
        # Biomes change over tens of tiles; a seam would show up as many
        # mismatches exactly on chunk borders. Compare mismatch rate on
        # border-crossing pairs vs. pairs inside chunks.
        w = ChunkedWorld(5)
        border = inside = border_diff = inside_diff = 0
        for ty in range(-300, 300, 3):
            for tx in range(-300, 300):
                same = w.biome_at(tx, ty) is w.biome_at(tx + 1, ty)
                if (tx + 1) % N == 0:
                    border += 1
                    border_diff += not same
                else:
                    inside += 1
                    inside_diff += not same
        self.assertLess(border_diff / border, inside_diff / inside * 3 + 0.01)


class SpawnTest(unittest.TestCase):
    def test_spawn_is_clear_open_plains_for_many_seeds(self):
        spec = config.TANKS[config.START_TANK]
        for seed in range(1, 21):
            w = ChunkedWorld(seed)
            x, y = w.spawn_point()
            tank = Tank(spec, x, y)
            self.assertFalse(
                hull_hits_solid(w, x, y, tank.hull_angle, tank.half_len, tank.half_wid), seed
            )
            self.assertIs(w.biome_at(0, 0), biomes.PLAINS, seed)
            r = config.SPAWN_CLEAR_RADIUS - 1
            for ty in range(-r, r + 1):
                for tx in range(-r, r + 1):
                    if tx * tx + ty * ty < r * r:
                        self.assertFalse(w.tile_at(tx, ty).solid, (seed, tx, ty))


class VarietyTest(unittest.TestCase):
    def test_sample_biome_matches_generated_chunks(self):
        # sample_biome skips only the small border wobble, so away from
        # borders it must agree with the real generated tiles.
        w = ChunkedWorld(42)
        agree = total = 0
        for ty in range(-400, 400, 37):
            for tx in range(-400, 400, 37):
                total += 1
                agree += sample_biome(42, tx, ty) is w.biome_at(tx, ty)
        self.assertGreater(agree / total, 0.85)

    def test_all_six_biomes_appear_near_spawn(self):
        for seed in (1, 42, 777, 2024):
            seen = Counter(
                sample_biome(seed, tx, ty)
                for ty in range(-1000, 1000, 20) for tx in range(-1000, 1000, 20)
            )
            self.assertEqual(set(seen), set(biomes.BY_ID), seed)
            self.assertGreater(seen[biomes.PLAINS] / sum(seen.values()), 0.15, seed)

    def test_ruins_have_buildings(self):
        # Find a ruins district, then generate just the area around it.
        cx, cy = next(
            (tx, ty) for ty in range(-1000, 1000, 16) for tx in range(-1000, 1000, 16)
            if all(sample_biome(42, tx + dx, ty + dy) is biomes.RUINS
                   for dx in (-48, 48) for dy in (-48, 48))
        )
        w = ChunkedWorld(42)
        walls = sum(
            w.tile_at(tx, ty) is tiles.WALL
            for ty in range(cy - 48, cy + 48) for tx in range(cx - 48, cx + 48)
        )
        self.assertGreater(walls, 60)


class ConnectivityTest(unittest.TestCase):
    def test_never_boxed_in_by_indestructible_terrain(self):
        # Flood-fill from the spawn over everything the tank can drive on
        # *or shoot away* (only rock, mesa, water and bog are permanent).
        # It must reach the edge of a big square in every direction.
        permanent = {tiles.ROCK, tiles.MESA, tiles.WATER, tiles.BOG, tiles.VOID}
        for seed in (3, 42, 1001):
            w = ChunkedWorld(seed)
            R = 220
            seen = {(0, 0)}
            q = deque([(0, 0)])
            reached = set()
            while q:
                x, y = q.popleft()
                if abs(x) == R or abs(y) == R:
                    reached.add(("E" if x == R else "W" if x == -R else "S" if y == R else "N"))
                    continue
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if (nx, ny) not in seen and w.tile_at(nx, ny) not in permanent:
                        seen.add((nx, ny))
                        q.append((nx, ny))
            self.assertEqual(reached, {"N", "S", "E", "W"}, seed)


class StreamingTest(unittest.TestCase):
    def test_loads_ahead_and_unloads_behind(self):
        w = ChunkedWorld(8)
        half_w, half_h = 32.0, 13.5
        for _ in range(40):
            w.update(0.0, 0.0, half_w, half_h, budget_ms=1e9)
        near = len(w._chunks)
        self.assertGreater(near, 0)
        self.assertEqual(w.pending_chunks, 0)
        # Drive far east: old chunks go, new ones arrive.
        for x in range(0, 2000, 8):
            w.update(float(x), 0.0, half_w, half_h, budget_ms=1e9)
        keys = set(w._chunks)
        self.assertNotIn((0, 0), keys)
        self.assertIn((2000 // N, 0), keys)
        # Memory stays bounded: roughly the view plus margins.
        self.assertLess(len(keys), near * 3)

    def test_hysteresis_no_thrash_at_a_border(self):
        w = ChunkedWorld(8)
        for _ in range(3):
            w.update(100.0, 0.0, 32, 13, budget_ms=1e9)
        before = set(w._chunks)
        for i in range(50):  # wiggle across a chunk boundary
            w.update(100.0 + (i % 2) * 6, 0.0, 32, 13, budget_ms=1e9)
        self.assertTrue(before <= set(w._chunks))

    def test_budget_is_respected(self):
        w = ChunkedWorld(8)
        worst = 0.0
        for x in range(0, 600, 4):
            t = time.perf_counter()
            w.update(float(x), 0.0, 43, 13.5, budget_ms=3.0)
            worst = max(worst, time.perf_counter() - t)
        # One builder step can overrun the budget slightly (~1.3 ms max).
        self.assertLess(worst * 1000, 3.0 + 4.0)

    def test_damage_persists_after_unload(self):
        w = ChunkedWorld(42)
        # Find a destructible tile away from spawn.
        target = next(
            (tx, ty) for ty in range(40, 200) for tx in range(40, 200)
            if w.tile_at(tx, ty).destructible and w.tile_at(tx, ty).hp > 1
        )
        tile = w.tile_at(*target)
        self.assertEqual(w.damage_tile(*target, 1), Damage.DAMAGED)
        worn_glyph = w.glyph_at(*target)
        # Destroy a neighbour-ish tile completely too.
        other = next(
            (tx, ty) for ty in range(40, 200) for tx in range(40, 200)
            if (tx, ty) != target and w.tile_at(tx, ty).destructible
        )
        debris = w.tile_at(*other).becomes
        self.assertEqual(w.damage_tile(*other, 99), Damage.DESTROYED)
        # Drive far away so both chunks unload, then come back.
        for x in range(0, 3000, 50):
            w.update(float(x), 0.0, 43, 13.5, budget_ms=1e9)
        self.assertNotIn((target[0] // N, target[1] // N), w._chunks)
        self.assertIs(w.tile_at(*target), tile)
        self.assertEqual(w.hp_at(*target), tile.hp - 1)
        self.assertEqual(w.glyph_at(*target), worn_glyph)
        self.assertIs(w.tile_at(*other), debris)
        self.assertFalse(w.tile_at(*other).solid)


class PerformanceTest(unittest.TestCase):
    def test_chunk_build_steps_are_small(self):
        worst = 0.0
        for k in range(6):
            gen = build_chunk(99, k * 7, -k * 3)
            try:
                while True:
                    t = time.perf_counter()
                    next(gen)
                    worst = max(worst, time.perf_counter() - t)
            except StopIteration:
                pass
        # Each resumable step must be small enough to fit in the frame budget.
        self.assertLess(worst * 1000, config.CHUNK_BUILD_BUDGET_MS)


if __name__ == "__main__":
    unittest.main()
