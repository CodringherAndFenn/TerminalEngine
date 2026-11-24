"""M31.1: Pangaea's land, the west zone (design/OCEAN.md 24-29): deep time,
the rings of ages, the volcano, lava, tar, amber, bones and nests."""

import math
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import numpy as np

from ascii_adventurers import config
from ascii_adventurers.systems.collision import WaterWalk
from ascii_adventurers.tests.islands import fresh_islands
from ascii_adventurers.ui import maps
from ascii_adventurers.world import biomes, explored, tiles
from ascii_adventurers.world.chunked import ChunkedWorld
from ascii_adventurers.world.layout import IslandLayout
from ascii_adventurers.world.pangaea import HEART, MIDDLE, SHORE
from ascii_adventurers.world.zones import _farthest_land, plan_of

SEEDS = (31, 7, 12)


def tiles_in(world, x0, y0, x1, y1):
    world.ensure_ready(x0, y0, x1, y1)
    return {(x, y): world.tile_at(x, y) for y in range(y0, y1) for x in range(x0, x1)}


def pang(seed=31):
    lay = IslandLayout(seed)
    return lay, lay.zone("pangaea"), plan_of(lay, lay.zone("pangaea"))


def along(line, every=2):
    """Tile points every `every` tiles along a polyline."""
    out = []
    for (ax, ay), (bx, by) in zip(line, line[1:]):
        n = max(1, int(math.hypot(bx - ax, by - ay)))
        for k in range(0, n, every):
            out.append((math.floor(ax + (bx - ax) * k / n), math.floor(ay + (by - ay) * k / n)))
    return out


class PlacementTest(unittest.TestCase):
    def test_pangaea_is_due_west_a_minute_off_the_coast(self):
        for seed in SEEDS:
            lay, z, _ = pang(seed)
            self.assertEqual([q.key for q in lay.zones], ["paradise", "pandemonium", "pangaea"])
            self.assertEqual((z.place, z.cy), ("W", 0))
            self.assertLess(z.cx, -lay.max_land_radius)
            zones, lay.zones = lay.zones, ()
            far = _farthest_land(lay, math.pi)
            lay.zones = zones
            self.assertGreaterEqual(abs(z.cx) - z.max_radius - far, config.ZONE_GAP - 1, seed)
            self.assertIs(lay.biome_at(z.cx, z.cy), biomes.PANGAEA)
            self.assertIs(lay.biome_at(z.cx - z.max_radius - 5, z.cy), biomes.OCEAN)
            self.assertEqual(z.facing, (1.0, 0.0))           # (toward the main island)

    def test_only_the_east_stays_open_sea(self):
        lay = IslandLayout(31)
        x, y = lay.cardinal_sites()["E"]
        self.assertTrue(lay.all_ocean(x - 200, y - 200, x + 200, y + 200))


class PlanTest(unittest.TestCase):
    def test_every_landmark_is_placed(self):
        for seed in SEEDS:
            lay, z, p = pang(seed)
            for name in ("caves", "great_nest", "crater"):
                self.assertIsNotNone(getattr(p, name), (seed, name))
            self.assertEqual(len(p.nests), config.PANGAEA_NESTS, seed)
            self.assertEqual(len(p.bones), config.PANGAEA_BONES, seed)
            self.assertEqual(len(p.tar_pits), config.PANGAEA_TAR_PITS, seed)
            self.assertEqual(len(p.pools), config.PANGAEA_POOLS, seed)
            self.assertEqual(len(p.rivers), config.PANGAEA_LAVA_RIVERS, seed)
            keys = [m.key for m in p.marks]
            for key in ("pangaea_caldera", "pangaea_skeleton", "pangaea_caves",
                        "pangaea_great_nest", "pangaea_crater"):
                self.assertEqual(keys.count(key), 1, (seed, key))
            self.assertEqual(keys.count("pangaea_nest"), config.PANGAEA_NESTS)
            for m in p.marks:
                self.assertTrue(z.inside(m.cx, m.cy), (seed, m.key))
                self.assertEqual(m.biome, "pangaea")
            self.assertIs(p, plan_of(lay, z))                # built once
            self.assertTrue(all(m in lay.landmarks for m in p.marks))

    def test_the_rings_of_ages(self):
        for seed in SEEDS:
            _, z, p = pang(seed)
            self.assertEqual(p.ring_at(z.cx, z.cy), HEART)
            x = z.cx + z.shore_along(1, 0) - 6
            self.assertEqual(p.ring_at(x, z.cy), SHORE)
            self.assertEqual(p.ring_at(*p.caves), SHORE)
            self.assertEqual(p.ring_at(*p.great_nest), MIDDLE)
            self.assertEqual(p.ring_at(*p.crater), MIDDLE)
            self.assertTrue(all(p.ring_at(x, y) == HEART for x, y, _ in p.pools))
            self.assertTrue(all(p.ring_at(x, y) == MIDDLE for x, y in p.nests))
            u = p.depth(np.array([z.cx, x]), np.array([z.cy, z.cy]))
            self.assertLess(u[0], 0.05)
            self.assertGreater(u[1], config.PANGAEA_RINGS[1])

    def test_sites_keep_apart(self):
        _, _, p = pang()
        small = [m for m in p.marks if m.key not in ("pangaea_caldera", "pangaea_skeleton",
                                                     "pangaea_bones")]
        for i, m in enumerate(small):
            for n in small[i + 1:]:
                apart = (m.x0 + m.w <= n.x0 or n.x0 + n.w <= m.x0
                         or m.y0 + m.h <= n.y0 or n.y0 + n.h <= m.y0)
                self.assertTrue(apart, (m.key, n.key))

    def test_the_same_seed_gives_the_same_pangaea(self):
        with fresh_islands():
            a, b = pang(7)[2], pang(7)[2]
        self.assertEqual((a.gate, a.caves, a.great_nest, a.crater, a.nests, a.bones, a.tar_pits,
                          a.pools, a.fields),
                         (b.gate, b.caves, b.great_nest, b.crater, b.nests, b.bones, b.tar_pits,
                          b.pools, b.fields))
        self.assertEqual((a.trails, a.rivers), (b.trails, b.rivers))

    def test_the_caldera_is_sealed_by_fire_and_faces_the_skeleton(self):
        _, _, p = pang()
        cal = next(m for m in p.marks if m.key == "pangaea_caldera")
        self.assertEqual(cal.kind, "lair")                   # (the quest's lair, M31.4)
        self.assertGreaterEqual(len(cal.gate), config.PANGAEA_CALDERA_GATE)
        gx, gy = p.facing
        for tx, ty in cal.gate:
            self.assertIs(cal.tile_at(tx, ty), tiles.FIRE_CURTAIN)
            self.assertGreater((tx + 0.5 - cal.cx) * gx + (ty + 0.5 - cal.cy) * gy, 0)
        self.assertTrue(cal.inside(cal.cx, cal.cy))
        self.assertTrue(cal.props["barred"])
        self.assertIs(cal.props["seal"], tiles.FIRE_CURTAIN)
        self.assertEqual(len(cal.props["lakes"]), config.PANGAEA_CALDERA_LAKES[0])
        flat = {t for row in cal.rows for t in row if t is not None}
        self.assertTrue({tiles.CALDERA_RIM, tiles.CALDERA_FLOOR, tiles.LAVA, tiles.LAVA_CRUST} <= flat)
        self.assertIs(cal.tile_at(math.floor(cal.cx), math.floor(cal.cy)), tiles.CALDERA_FLOOR)

    def test_landmarks_have_their_furniture(self):
        _, _, p = pang()
        want = {"pangaea_skeleton": {tiles.GIANT_BONE, tiles.SPINE},
                "pangaea_caves": {tiles.CAVE_ROCK, tiles.PAINTED_WALL, tiles.CAVE_FLOOR, tiles.FIRE_PIT},
                "pangaea_great_nest": {tiles.CRAG, tiles.CRAG_TOP, tiles.NEST, tiles.GIANT_EGG},
                "pangaea_crater": {tiles.CRATER_RIM, tiles.IMPACT_GLASS, tiles.STAR_STONE},
                "pangaea_nest": {tiles.NEST, tiles.EGG, tiles.TWIGS},
                "pangaea_bones": {tiles.GIANT_BONE}}
        for m in p.marks:
            if m.key in want:
                flat = {t for row in m.rows for t in row if t is not None}
                self.assertTrue(want[m.key] <= flat, m.key)
        caves = next(m for m in p.marks if m.key == "pangaea_caves")
        self.assertTrue(caves.props["deep_wall"])
        self.assertIs(caves.tile_at(*caves.props["hunt_wall"][0][0]), tiles.PAINTED_WALL)
        self.assertIsNotNone(caves.npc)
        self.assertIs(caves.tile_at(math.floor(caves.npc[0]), math.floor(caves.npc[1])), tiles.CAVE_FLOOR)

    def test_the_rivers_start_on_the_cone_and_the_first_reaches_the_sea(self):
        _, z, p = pang()
        for line in p.rivers:
            x, y = line[0]
            self.assertLess(p._ellipse(x, y, p.cone), 1.0)       # (a vent on the cone)
            self.assertGreater(p._ellipse(x, y, 0), 1.0)         # (outside the rim)
        mx, my = p.mouth
        self.assertLess(abs(math.hypot(mx - z.cx, my - z.cy) - z.coast(np.array([mx]), np.array([my]))[0]), 3)
        self.assertEqual(len(p.fields), len(p.rivers) - 1)


class TilesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = ChunkedWorld(31)
        cls.z = cls.w.layout.zone("pangaea")
        cls.p = plan_of(cls.w.layout, cls.z)

    def test_each_ring_grows_its_own_ground(self):
        p, z = self.p, self.z
        rings = {HEART: set(), MIDDLE: set(), SHORE: set()}
        rng = random.Random(3)
        got = 0
        while got < 120:
            a, r = rng.uniform(0, math.tau), rng.uniform(0, z.radius * 0.95)
            x, y = math.floor(z.cx + math.cos(a) * r), math.floor(z.cy + math.sin(a) * r)
            if p._ellipse(x, y, p.cone + 2) < 1.0 or self.w.layout.biome_at(x + 0.5, y + 0.5) is not biomes.PANGAEA:
                continue
            got += 1
            rings[p.ring_at(x + 0.5, y + 0.5)] |= set(tiles_in(self.w, x - 3, y - 3, x + 4, y + 4).values())
        self.assertIn(tiles.ASH, rings[HEART])
        self.assertTrue(rings[HEART] & {tiles.HORSETAILS, tiles.SCALE_TREE})
        self.assertIn(tiles.JUNGLE_FLOOR, rings[MIDDLE])
        self.assertTrue(rings[MIDDLE] & {tiles.GIANT_FERN, tiles.JUNGLE_TREE, tiles.TALL_JUNGLE_FERNS})
        self.assertIn(tiles.FERN_MEADOW, rings[SHORE])
        self.assertNotIn(tiles.ASH, rings[SHORE])
        self.assertNotIn(tiles.FERN_MEADOW, rings[HEART])

    def test_the_cone_and_the_curtain(self):
        cx, cy, a, b = self.p.caldera
        gx, gy = self.p.facing
        x = math.floor(cx + a + self.p.RIM + 6)
        row = tiles_in(self.w, x, math.floor(cy) - 12, x + 1, math.floor(cy) + 12)
        self.assertTrue(set(row.values()) & {tiles.CINDERS, tiles.GAME_TRAIL})
        tx, ty = map(math.floor, self.p.curtain)
        self.assertIs(tiles_in(self.w, tx, ty, tx + 1, ty + 1)[(tx, ty)], tiles.FIRE_CURTAIN)

    def test_lava_burns_down_to_the_sea_and_is_crossed_by_cooled_rock(self):
        seen = set()
        for x, y in along(self.p.rivers[0], 6):
            if self.w.layout.biome_at(x + 0.5, y + 0.5) is biomes.PANGAEA:
                seen |= set(tiles_in(self.w, x - 4, y - 4, x + 5, y + 5).values())
        self.assertTrue({tiles.LAVA, tiles.LAVA_CRUST} <= seen)
        ring_trail = set()
        for x, y in along(self.p.trails[1], 1):
            ring_trail.add(tiles_in(self.w, x, y, x + 1, y + 1)[(x, y)])
        self.assertIn(tiles.LAVA_CROSSING, ring_trail)       # (every river crosses the ring trail)
        self.assertNotIn(tiles.LAVA, ring_trail)
        mx, my = map(math.floor, self.p.mouth)
        near = set(tiles_in(self.w, mx - 10, my - 10, mx + 11, my + 11).values())
        self.assertIn(tiles.STEAMING_SEA, near)
        self.assertIn(tiles.BLACK_SAND, near)

    def test_tar_pits_pools_and_basalt(self):
        x, y, _ = self.p.tar_pits[0]
        self.assertIs(tiles_in(self.w, x, y, x + 1, y + 1)[(x, y)] in (tiles.TAR, tiles.GIANT_BONE), True)
        x, y, _ = self.p.pools[0]
        self.assertIs(tiles_in(self.w, x, y, x + 1, y + 1)[(x, y)], tiles.HOT_SPRING)
        fx, fy, _ = self.p.fields[0]
        x, y = math.floor(fx), math.floor(fy)
        self.assertTrue(set(tiles_in(self.w, x - 2, y - 2, x + 3, y + 3).values())
                        & {tiles.BASALT, tiles.BASALT_BOULDER})

    def lava_tile(self):
        for x, y in along(self.p.rivers[0], 3):
            if tiles_in(self.w, x, y, x + 1, y + 1)[(x, y)] is tiles.LAVA:
                return x, y
        self.fail("no lava along the first river")

    def test_who_walks_where(self):
        ww = WaterWalk(self.w)
        x, y, _ = self.p.pools[0]
        self.assertFalse(ww.tile_at(x, y).solid)             # (water walkers cross the springs)
        self.assertTrue(tiles.LAVA.solid)
        self.assertFalse(tiles.LAVA.blocks_shots)            # (shots fly over it)
        self.assertTrue(ww.tile_at(*self.lava_tile()).solid)  # (nor walk the lava)
        for t in (tiles.LAVA_CRUST, tiles.LAVA_CROSSING, tiles.TAR, tiles.GAME_TRAIL, tiles.SPINE,
                  tiles.TALL_FERNS, tiles.HORSETAILS, tiles.CALDERA_FLOOR, tiles.IMPACT_GLASS):
            self.assertFalse(t.solid, t.name)
        for t, left in ((tiles.GIANT_FERN, tiles.TRAMPLED_FERNS), (tiles.CYCAD, tiles.TRAMPLED_FERNS),
                        (tiles.EGG, tiles.EGGSHELL), (tiles.GIANT_EGG, tiles.EGGSHELL),
                        (tiles.AMBER, tiles.AMBER_SHARDS), (tiles.NEST, tiles.TWIGS),
                        (tiles.SCALE_TREE, tiles.ASH_DEBRIS)):
            self.assertTrue(t.destructible, t.name)
            self.assertIs(t.becomes, left)
        for t in (tiles.GIANT_BONE, tiles.STAR_STONE, tiles.CALDERA_RIM, tiles.CAVE_ROCK, tiles.CRAG):
            self.assertFalse(t.destructible, t.name)
            self.assertTrue(t.blocks_shots, t.name)

    def test_somebody_lives_here_now(self):
        # (M31.2: the beasts and the hunters; it was "nobody lives here yet")
        self.assertGreater(config.BIOME_ENEMY_DENSITY.get("pangaea", 0.0), 0.0)
        self.assertTrue([k for k, s in config.ENEMIES.items() if "pangaea" in s.biomes])


class MapTest(unittest.TestCase):
    def test_hidden_until_found(self):
        w = ChunkedWorld(31)
        z = w.layout.zone("pangaea")
        dim = maps._DIM_OFFSET + biomes.PANGAEA.id
        px = lambda: maps.map_pixels(w, z.cx, z.cy, 8.0, 40, 40)
        self.assertFalse((px() == dim).any())
        w.found_zones.add("pangaea")
        self.assertTrue((px() == dim).any())
        self.assertGreater(w.layout.view_radius({"pangaea"}), abs(z.cx) + z.radius)

    def test_every_tile_has_a_map_colour_and_the_rings_differ(self):
        self.assertEqual(len(maps._COLORS), len(explored.MAP_TILES) + len(biomes.BY_ID))
        self.assertLess(len(explored.MAP_TILES), explored.UNSEEN)
        cls = explored._CLASS
        cols = {maps._COLORS[cls[t]] for t in (tiles.FERN_MEADOW, tiles.JUNGLE_FLOOR, tiles.ASH)}
        self.assertEqual(len(cols), 3)


def _game():
    from ascii_adventurers.tests.test_m16 import game
    m, s = game("wizard", seed=31)
    s.app.dev = True
    return m, s


class HazardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m, cls.s = _game()
        cls.p = plan_of(cls.s.world.layout, cls.s.world.layout.zone("pangaea"))

    def setUp(self):
        s = self.s
        s.enemies.clear()
        s.zones.clear()
        s.volcano.bombs.clear()
        s.volcano.next.clear()
        s.hero.hp = s.hero.max_hp = 1000.0
        s.hero.water_walk = True
        s.quests.banner = None

    def put(self, tile, near):
        """Teleport onto the nearest tile of a kind around `near` (searched
        out to 40 tiles)."""
        from ascii_adventurers.tests.test_m17 import teleport
        s = self.s
        x0, y0 = map(math.floor, near)
        found = tiles_in(s.world, x0 - 40, y0 - 40, x0 + 41, y0 + 41)
        spots = sorted((math.hypot(x - x0, y - y0), x, y) for (x, y), t in found.items() if t is tile)
        self.assertTrue(spots, tile.name)
        _, x, y = spots[0]
        teleport(s, x + 0.5, y + 0.5)
        s.hero.x, s.hero.y = x + 0.5, y + 0.5
        return x, y

    def run_for(self, secs, move=(0.0, 0.0)):
        from ascii_adventurers.tests.test_m17 import step
        s = self.s
        for _ in range(int(secs * 60)):
            step(s)

    def test_the_crust_burns(self):
        x, y = self.put(tiles.LAVA_CRUST, self.p.rivers[0][3])
        hp = self.s.hero.hp
        self.run_for(1.0)
        if self.s.world.tile_at(math.floor(self.s.hero.x), math.floor(self.s.hero.y)) is tiles.LAVA_CRUST:
            self.assertLess(self.s.hero.hp, hp - config.PANGAEA_CRUST[0] * 2)

    def test_the_lava_can_not_be_walked_even_on_water(self):
        from ascii_adventurers.systems.collision import WaterWalk
        x, y = self.put(tiles.LAVA, self.p.rivers[0][3])
        self.assertTrue(WaterWalk(self.s.world).tile_at(x, y).solid)

    def test_tar_holds_you_deeper_the_longer_you_stand(self):
        from ascii_adventurers.systems import pangaea
        h = self.s.hero
        tx, ty, _ = self.p.tar_pits[0]
        self.put(tiles.TAR, (tx, ty))
        pangaea._underfoot(self.s, h, tiles.TAR, 0.05)
        first = h.slow_mult
        self.assertAlmostEqual(first, config.TAR[0], delta=0.03)
        pangaea._underfoot(self.s, h, tiles.TAR, config.TAR[2])
        self.assertAlmostEqual(h.slow_mult, config.TAR[1], places=3)
        pangaea._underfoot(self.s, h, tiles.FERN_MEADOW, 0.05)
        self.assertEqual(h.tar_t, 0.0)

    def test_tar_slows_an_enemy_and_the_crust_burns_it(self):
        from ascii_adventurers.ai import make_enemy
        from ascii_adventurers.systems import pangaea
        e = make_enemy("warrior", 0.0, 0.0, random.Random(1))
        pangaea._enemy_underfoot(self.s, e, tiles.TAR, 1 / 60)
        self.assertAlmostEqual(e.status.time_scale, config.TAR[3])
        hp = e.hp
        pangaea._enemy_underfoot(self.s, e, tiles.LAVA_CRUST, 1 / 60)
        self.assertLess(e.hp, hp)

    def test_lava_bombs_in_the_heart_not_on_the_shore(self):
        s, p = self.s, self.p
        x, y, _ = p.pools[0]
        self.put(tiles.ASH, (x + 7, y))
        seen = False
        for _ in range(int(config.LAVA_BOMB_EVERY[0] + config.LAVA_BOMB_EVERY[2] + 1) * 4):
            self.run_for(0.25)
            seen = seen or bool(s.volcano.bombs)
        self.assertTrue(seen)                            # (a volley came, on its own)
        # A volley: marked, then a blast where the hero stood.
        s.volcano.bombs.clear()
        s.volcano.next[s.me.index] = 0.0
        hp = s.hero.hp
        self.run_for(1 / 60 * 2)
        self.assertEqual(len(s.volcano.bombs), config.LAVA_BOMB[0])
        self.assertAlmostEqual(s.volcano.bombs[0][0], s.hero.x, delta=0.5)
        s.draw(self.m.text)                              # (the marks and the bombs in the air)
        self.run_for(config.LAVA_BOMB[2] + 0.6)
        self.assertLess(s.hero.hp, hp)
        self.assertTrue([z for z in s.zones if z.kind == "lava_splash"])
        s.draw(self.m.text)
        # None on the shore ring.
        s.volcano.bombs.clear()
        s.volcano.next.clear()
        gx, gy = p.facing
        self.put(tiles.FERN_MEADOW, (p.gate[0] - gx * 30, p.gate[1] - gy * 30 + 20))
        self.run_for(config.LAVA_BOMB_EVERY[1] + config.LAVA_BOMB_EVERY[2] + 1)
        self.assertEqual(s.volcano.bombs, [])

    def test_the_land_hits_like_the_zone_s_enemies(self):
        from ascii_adventurers.systems import pangaea
        s = self.s
        base = pangaea.hazard(s, 10.0)
        s.spawner.level += 20
        try:
            self.assertGreater(pangaea.hazard(s, 10.0), base)
        finally:
            s.spawner.level -= 20
        self.assertAlmostEqual(base, 10.0 * config.ENEMY_DAMAGE_MULTIPLIER * config.ZONE_TOUGH[1]
                               * s.spawner.damage_mult * (1 + s.spawner.damage_bonus), delta=1.0)

    def test_each_ring_of_ages_has_its_banner(self):
        s, p = self.s, self.p
        s.arrived.discard("pangaea:1")
        self.put(tiles.JUNGLE_FLOOR, p.great_nest)
        self.run_for(0.5)
        self.assertEqual((s.quests.banner.title, s.quests.banner.sub), config.PANGAEA_AGES[MIDDLE])


class GameTest(unittest.TestCase):
    def setUp(self):
        self.m, self.s = _game()

    def test_dev_jump_reaches_pangaea_and_a_banner_on_arrival(self):
        s = self.s
        for _ in range(3):                                  # Paradise, Pandemonium, Pangaea
            s._dev_zone()
        h = s.hero
        self.assertTrue(h.water_walk)
        self.assertIs(s.world.biome_at(math.floor(h.x), math.floor(h.y)), biomes.PANGAEA)
        s.arrived.clear()
        s.quests.banner = None
        s._step(1 / 60)
        self.assertIn("pangaea", s.world.found_zones)
        self.assertEqual((s.quests.banner.title, s.quests.banner.sub), ("PANGAEA", "where the world began"))

    def test_draws_on_pangaea(self):
        s = self.s
        for _ in range(3):
            s._dev_zone()
        s.quests.banner = None
        s.draw(self.m.text)
        s.big_map.open(s.hero.x, s.hero.y)
        s.draw(self.m.text)


if __name__ == "__main__":
    unittest.main()
