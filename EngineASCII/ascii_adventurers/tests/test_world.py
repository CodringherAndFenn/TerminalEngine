import math
import time
import unittest
from collections import Counter, deque

from ascii_adventurers import config
from ascii_adventurers.entities.character import Character
from ascii_adventurers.systems.collision import hull_hits_solid
from ascii_adventurers.world import biomes, tiles
from ascii_adventurers.world.chunked import ChunkedWorld
from ascii_adventurers.world.generator import build_chunk
from ascii_adventurers.world.layout import IslandLayout
from ascii_adventurers.world.noise import lattice, value_noise_at, value_noise_grid
from ascii_adventurers.world.rng import hash_unit
from ascii_adventurers.world.tiles import Damage

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

    def test_numpy_hash_matches_python_hash(self):
        for ix, iy in ((0, 0), (-3, 12), (10**6, -10**6), (-1, -1)):
            self.assertEqual(float(lattice(5, 7, ix, iy)), hash_unit(5, 7, ix, iy))

    def test_sparse_points_match_dense_grid(self):
        # Far-apart points take the direct-hash path; it must give the same
        # field as the lattice-box path a chunk uses.
        import numpy as np
        from ascii_adventurers.world.noise import value_noise
        xs = np.array([-9000.5, 0.5, 7000.5])
        ys = np.array([4000.5, -0.5, -8000.5])
        sparse = value_noise(3, 9, xs, ys, 5.0)
        for x, y, v in zip(xs, ys, sparse):
            self.assertAlmostEqual(v, value_noise_grid(3, 9, int(x - 0.5), int(y - 0.5), 1, 1, 5.0)[0][0])


class DeterminismTest(unittest.TestCase):
    def test_same_seed_same_chunk_regardless_of_order(self):
        keys = [(0, 0), (3, -2), (-5, 7), (1, 1)]
        a = {k: finish(build_chunk(IslandLayout(123), *k)) for k in keys}
        b = {k: finish(build_chunk(IslandLayout(123), *k)) for k in reversed(keys)}
        for k in keys:
            self.assertEqual(a[k].tiles, b[k].tiles, k)
            self.assertEqual(a[k].glyphs, b[k].glyphs, k)

    def test_different_seeds_differ(self):
        self.assertNotEqual(finish(build_chunk(IslandLayout(1), 9, 9)).tiles,
                            finish(build_chunk(IslandLayout(2), 9, 9)).tiles)

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
        # Around the edge of the central plains, where biomes change.
        w = ChunkedWorld(5)
        ox = int(w.layout.plains_radius)
        border = inside = border_diff = inside_diff = 0
        for ty in range(-300, 300, 3):
            for tx in range(ox - 300, ox + 300):
                same = w.biome_at(tx, ty) is w.biome_at(tx + 1, ty)
                if (tx + 1) % N == 0:
                    border += 1
                    border_diff += not same
                else:
                    inside += 1
                    inside_diff += not same
        self.assertGreater(inside_diff, 0)   # there really is a border here
        self.assertLess(border_diff / border, inside_diff / inside * 3 + 0.01)


class SpawnTest(unittest.TestCase):
    def test_spawn_is_clear_open_plains_for_many_seeds(self):
        spec = config.HEROES[config.START_HERO]
        for seed in range(1, 21):
            w = ChunkedWorld(seed)
            x, y = w.spawn_point()
            hero = Character(spec, x, y)
            self.assertFalse(
                hull_hits_solid(w, x, y, 0.0, hero.half, hero.half), seed
            )
            sx, sy = w.layout.spawn
            self.assertIs(w.biome_at(sx, sy), biomes.PLAINS, seed)
            r = config.SPAWN_CLEAR_RADIUS - 1
            for ty in range(-r, r + 1):
                for tx in range(-r, r + 1):
                    if tx * tx + ty * ty < r * r:
                        self.assertFalse(w.tile_at(sx + tx, sy + ty).solid, (seed, tx, ty))

    def test_never_trapped_by_a_lake(self):
        # Regression: ~20% of seeds have a lake over the island's centre; the
        # old spawn cleared a dry islet in it and you couldn't leave. These
        # seeds all have a lake at (0, 0). Flood-fill the real tiles over
        # everything drivable or shootable: it must get well away.
        permanent = {tiles.ROCK, tiles.MESA, tiles.WATER, tiles.BOG, tiles.VOID}
        for seed in (1, 11, 12, 16, 24, 26, 27, 29):
            w = ChunkedWorld(seed)
            self.assertIs(w.tile_at(0, 0), tiles.WATER, seed)   # the trap is real
            sx, sy = w.layout.spawn
            R = config.SPAWN_ESCAPE_RADIUS
            seen = {(sx, sy)}
            q = deque([(sx, sy)])
            escaped = False
            while q and not escaped:
                x, y = q.popleft()
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if (nx, ny) not in seen and w.tile_at(nx, ny) not in permanent:
                        if max(abs(nx - sx), abs(ny - sy)) >= R:
                            escaped = True
                        seen.add((nx, ny))
                        q.append((nx, ny))
            self.assertTrue(escaped, seed)

    def test_spawn_stays_near_the_centre(self):
        for seed in range(1, 41):
            sx, sy = IslandLayout(seed).spawn
            self.assertLess(math.hypot(sx, sy), 200, seed)


def ring_point(layout: IslandLayout, biome, frac: float = 0.55) -> tuple[int, int]:
    """A tile well inside `biome`'s slice of the ring, frac of the way out."""
    r = layout.radius * frac
    for k in range(720):
        a = k / 720 * 2 * math.pi
        x, y = r * math.cos(a), r * math.sin(a)
        if all(layout.biome_at(x + dx, y + dy) is biome
               for dx in (-60, 0, 60) for dy in (-60, 0, 60)):
            return int(x), int(y)
    raise AssertionError(f"no {biome.name} found")


class LayoutTest(unittest.TestCase):
    SEEDS = (1, 42, 777, 2024)

    def test_plains_in_the_middle_ocean_outside(self):
        import numpy as np
        rng = np.random.default_rng(0)
        for seed in self.SEEDS:
            lay = IslandLayout(seed)
            a = rng.uniform(0, 2 * math.pi, 4000)
            # Inside the smallest the plains' wobble can make them: plains.
            border = config.BORDER_WOBBLE + config.BIOME_BORDER_JITTER + 1
            r = rng.uniform(0, lay.plains_radius * (1 - config.PLAINS_EDGE_AMPLITUDE) - border, 4000)
            ids = lay.biome_ids(r * np.cos(a), r * np.sin(a))
            self.assertTrue((ids == biomes.PLAINS.id).all(), seed)
            # Past the farthest the coast can reach: ocean.
            r = rng.uniform(lay.max_land_radius, lay.max_land_radius * 2, 4000)
            ids = lay.biome_ids(r * np.cos(a), r * np.sin(a))
            self.assertTrue((ids == biomes.OCEAN.id).all(), seed)
            # Inside the nearest the coast can come: land.
            r = rng.uniform(0, lay.radius * (1 - config.COAST_AMPLITUDE) - border, 4000)
            ids = lay.biome_ids(r * np.cos(a), r * np.sin(a))
            self.assertFalse((ids == biomes.OCEAN.id).any(), seed)

    def test_ring_slices_are_equal_and_all_present(self):
        import numpy as np
        for seed in self.SEEDS:
            lay = IslandLayout(seed)
            a = np.linspace(0, 2 * math.pi, 5000, endpoint=False)
            counts = Counter()
            for frac in (0.35, 0.5, 0.65, 0.8):
                r = lay.radius * frac
                counts.update(lay.biome_ids(r * np.cos(a), r * np.sin(a)).tolist())
            ring = {b.id for b in lay.ring}
            self.assertEqual(ring, {biomes.BY_NAME[n].id for n in config.BIOME_RING})
            total = sum(counts[i] for i in ring)
            for i in ring:
                self.assertAlmostEqual(counts[i] / total, 1 / len(ring), delta=0.07, msg=(seed, i))

    def test_layout_rotates_per_seed(self):
        layouts = [IslandLayout(s) for s in range(1, 9)]
        self.assertGreater(len({lay.ring for lay in layouts}), 1)
        self.assertGreater(len({round(lay.rotation, 3) for lay in layouts}), 1)

    def test_layout_can_be_fixed(self):
        from unittest import mock
        with mock.patch.object(config, "BIOME_RING_SHUFFLE", False), \
                mock.patch.object(config, "BIOME_RING_ROTATE", False):
            a, b = IslandLayout(1), IslandLayout(99)
        self.assertEqual(a.ring, b.ring)
        self.assertEqual([x.name for x in a.ring], list(config.BIOME_RING))
        self.assertEqual(a.rotation, b.rotation)

    def test_coast_is_not_a_circle(self):
        # The coast radius per direction should wander by a good fraction of
        # its amplitude, and differ between seeds.
        lay = IslandLayout(42)
        radii = []
        for k in range(64):
            a = k / 64 * 2 * math.pi
            lo, hi = 0.0, lay.max_land_radius
            for _ in range(30):             # outermost land along this ray
                mid = (lo + hi) / 2
                if lay.biome_at(mid * math.cos(a), mid * math.sin(a)) is biomes.OCEAN:
                    hi = mid
                else:
                    lo = mid
            radii.append(lo)
        spread = (max(radii) - min(radii)) / lay.radius
        self.assertGreater(spread, config.COAST_AMPLITUDE * 0.5)

    def test_cardinal_sites_are_open_ocean(self):
        lay = IslandLayout(3)
        for x, y in lay.cardinal_sites().values():
            self.assertIs(lay.biome_at(x, y), biomes.OCEAN)
            self.assertTrue(lay.all_ocean(x - 200, y - 200, x + 200, y + 200))

    def test_layout_matches_generated_tiles_exactly(self):
        w = ChunkedWorld(42)
        pts = [(tx, ty) for tx in range(-7000, 7000, 997) for ty in range(-7000, 7000, 1231)]
        pts += [(int(w.layout.plains_radius) + d, 3) for d in range(-40, 40)]
        for tx, ty in pts:
            self.assertIs(w.layout.biome_at(tx + 0.5, ty + 0.5), w.biome_at(tx, ty), (tx, ty))


class IslandWorldTest(unittest.TestCase):
    def test_sea_chunks_are_water(self):
        w = ChunkedWorld(8)
        far = int(w.layout.max_land_radius) + 100
        for tx, ty in ((far, 0), (-far, 0), (0, far), (far, far)):
            self.assertIs(w.tile_at(tx, ty), tiles.WATER)
            self.assertTrue(w.tile_at(tx, ty).solid)
            self.assertIs(w.biome_at(tx, ty), biomes.OCEAN)

    def test_land_meets_water_directly(self):
        # No beach: along a ray, the first ocean tile comes straight after
        # the ring biome's own ground.
        w = ChunkedWorld(8)
        for k in range(8):
            a = k / 8 * 2 * math.pi
            r = w.layout.radius * 0.8
            while w.biome_at(round(r * math.cos(a)), round(r * math.sin(a))) is not biomes.OCEAN:
                r += 1
            inner = w.biome_at(round((r - 2) * math.cos(a)), round((r - 2) * math.sin(a)))
            self.assertIn(inner, w.layout.ring)

    def test_ruins_have_buildings(self):
        w = ChunkedWorld(42)
        cx, cy = ring_point(w.layout, biomes.RUINS)
        walls = sum(
            w.tile_at(tx, ty) is tiles.WALL
            for ty in range(cy - 48, cy + 48) for tx in range(cx - 48, cx + 48)
        )
        self.assertGreater(walls, 60)


class ConnectivityTest(unittest.TestCase):
    def test_never_boxed_in_by_indestructible_terrain(self):
        # Flood-fill from the spawn over everything the hero can walk on
        # *or shoot away* (only rock, mesa, water and bog are permanent).
        # It must reach the edge of a big square in every direction.
        # Checked from the spawn and from the middle of every ring biome.
        permanent = {tiles.ROCK, tiles.MESA, tiles.WATER, tiles.BOG, tiles.VOID}
        for seed in (3, 42):
            w = ChunkedWorld(seed)
            starts = [(0, 0)] + [ring_point(w.layout, b) for b in w.layout.ring]
            for ox, oy in starts:
                # Nearest drivable tile to the start point.
                ox, oy = next((ox + dx, oy) for dx in range(200)
                              if w.tile_at(ox + dx, oy) not in permanent)
                R = 120
                seen = {(ox, oy)}
                q = deque([(ox, oy)])
                reached = set()
                while q:
                    x, y = q.popleft()
                    if abs(x - ox) == R or abs(y - oy) == R:
                        reached.add("E" if x - ox == R else "W" if x - ox == -R
                                    else "S" if y - oy == R else "N")
                        continue
                    for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                        if (nx, ny) not in seen and w.tile_at(nx, ny) not in permanent:
                            seen.add((nx, ny))
                            q.append((nx, ny))
                self.assertEqual(reached, {"N", "S", "E", "W"}, (seed, ox, oy))


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
        # Chunks from the plains, the ring, the coast and the open sea.
        lay = IslandLayout(99)
        worst = 0.0
        for frac in (0.0, 0.1, 0.5, 0.9, 1.0, 1.1, 1.5):
            r = lay.radius * frac / N
            gen = build_chunk(lay, round(r * 0.6), round(r * 0.8))
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
