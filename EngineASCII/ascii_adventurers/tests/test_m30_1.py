"""M30.1: Pandemonium's land, the south zone (design/OCEAN.md 13-14)."""

import math
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import numpy as np

from ascii_adventurers import config, palette
from ascii_adventurers.systems.collision import WaterWalk
from ascii_adventurers.tests.islands import fresh_islands
from ascii_adventurers.ui import maps
from ascii_adventurers.world import biomes, explored, tiles
from ascii_adventurers.world.chunked import ChunkedWorld
from ascii_adventurers.world.layout import IslandLayout
from ascii_adventurers.world.zones import _farthest_land, plan_of

SEEDS = (31, 7, 12)
_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def tiles_in(world, x0, y0, x1, y1):
    world.ensure_ready(x0, y0, x1, y1)
    return {(x, y): world.tile_at(x, y) for y in range(y0, y1) for x in range(x0, x1)}


def pand(seed=31):
    lay = IslandLayout(seed)
    return lay, lay.zone("pandemonium"), plan_of(lay, lay.zone("pandemonium"))


class PlacementTest(unittest.TestCase):
    def test_pandemonium_is_due_south_a_minute_off_the_coast(self):
        for seed in SEEDS:
            lay, z, _ = pand(seed)
            self.assertEqual([q.key for q in lay.zones], ["paradise", "pandemonium"])
            self.assertEqual((z.place, z.cx), ("S", 0))
            self.assertGreater(z.cy, lay.max_land_radius)
            zones, lay.zones = lay.zones, ()      # (measured as placed: before any zone)
            far = _farthest_land(lay, math.pi / 2)
            lay.zones = zones
            self.assertGreaterEqual(z.cy - z.max_radius - far, config.ZONE_GAP - 1, seed)
            self.assertIs(lay.biome_at(z.cx, z.cy), biomes.PANDEMONIUM)
            self.assertIs(lay.biome_at(z.cx, z.cy + z.max_radius + 5), biomes.OCEAN)

    def test_the_main_island_is_unchanged(self):
        # (A zone far out at sea: the ring biomes' landmarks are the same as
        # without it; only the zones' own marks come after them.)
        lay = IslandLayout(31)
        main = [m for m in lay.landmarks if m.biome not in ("paradise", "pandemonium")]
        self.assertTrue(main)
        self.assertTrue(all(math.hypot(m.cx, m.cy) < lay.max_land_radius for m in main))

    def test_chunks_near_it_are_built(self):
        lay, z, _ = pand()
        self.assertFalse(lay.all_ocean(z.cx - 5, z.cy - 5, z.cx + 5, z.cy + 5))
        shore = z.cy + z.shore_along(0, 1)
        self.assertFalse(lay.all_ocean(-16, shore + 2, 16, shore + 10))   # (the wine-dark sea)


class PlanTest(unittest.TestCase):
    def test_every_landmark_is_placed(self):
        for seed in SEEDS:
            lay, z, p = pand(seed)
            for name in ("press", "banquet", "mirrors"):
                self.assertIsNotNone(getattr(p, name), (seed, name))
            self.assertEqual(len(p.bandstands), config.PANDEMONIUM_BANDSTANDS, seed)
            self.assertEqual(len(p.tables), config.PANDEMONIUM_TABLES, seed)
            self.assertEqual(len(p.fountains), config.PANDEMONIUM_FOUNTAINS, seed)
            self.assertEqual(len(p.statues), config.PANDEMONIUM_STATUES, seed)
            keys = [m.key for m in p.marks]
            for key in ("pandemonium_hall", "pandemonium_pier", "pandemonium_press",
                        "pandemonium_banquet", "pandemonium_mirrors"):
                self.assertEqual(keys.count(key), 1, (seed, key))
            for m in p.marks:
                if m.key != "pandemonium_pier":              # (its jetty is out at sea)
                    self.assertTrue(z.inside(m.cx, m.cy), (seed, m.key))
                self.assertEqual(m.biome, "pandemonium")
            self.assertIs(p, plan_of(lay, z))                # built once
            self.assertTrue(all(m in lay.landmarks for m in p.marks))

    def test_the_bandstands_keep_well_apart(self):
        for seed in SEEDS:
            _, _, p = pand(seed)
            for i, (ax, ay) in enumerate(p.bandstands):
                for bx, by in p.bandstands[i + 1:]:
                    self.assertGreaterEqual(math.hypot(ax - bx, ay - by),
                                            config.PANDEMONIUM_BANDSTAND_GAP, seed)

    def test_sites_keep_apart(self):
        _, _, p = pand()
        small = [m for m in p.marks if m.key not in ("pandemonium_hall", "pandemonium_pier")]
        for i, m in enumerate(small):
            for n in small[i + 1:]:
                apart = (m.x0 + m.w <= n.x0 or n.x0 + n.w <= m.x0
                         or m.y0 + m.h <= n.y0 or n.y0 + n.h <= m.y0)
                self.assertTrue(apart, (m.key, n.key))

    def test_the_press_is_near_the_rim(self):
        for seed in SEEDS:
            _, z, p = pand(seed)
            last = p.WALL + config.PANDEMONIUM_TERRACES[-1]
            self.assertGreater(p._ellipse(*p.press, last), 1.0, seed)

    def test_the_same_seed_gives_the_same_pandemonium(self):
        with fresh_islands():
            a, b = pand(7)[2], pand(7)[2]
        self.assertEqual((a.gate, a.press, a.banquet, a.mirrors, a.bandstands, a.tables,
                          a.fountains, a.statues),
                         (b.gate, b.press, b.banquet, b.mirrors, b.bandstands, b.tables,
                          b.fountains, b.statues))
        self.assertEqual((a.roads, a.river), (b.roads, b.river))

    def test_the_hall_is_sealed_and_faces_the_pier(self):
        _, _, p = pand()
        hall = next(m for m in p.marks if m.key == "pandemonium_hall")
        self.assertEqual(hall.kind, "court")                # (M30.4: the quest's lair)
        self.assertGreaterEqual(len(hall.gate), config.PANDEMONIUM_HALL_GATE)
        gx, gy = p.facing
        for tx, ty in hall.gate:
            self.assertIs(hall.tile_at(tx, ty), tiles.PALACE_GATE)
            self.assertGreater((tx + 0.5 - hall.cx) * gx + (ty + 0.5 - hall.cy) * gy, 0)
        self.assertTrue(hall.inside(hall.cx, hall.cy))
        self.assertTrue(hall.props["barred"])
        self.assertIs(hall.props["seal"], tiles.PALACE_GATE)
        flat = {t for row in hall.rows for t in row if t is not None}
        self.assertTrue({tiles.PALACE_WALL, tiles.HALL_FLOOR, tiles.HOST_SEAT, tiles.CARPET} <= flat)

    def test_landmarks_have_their_furniture(self):
        _, _, p = pand()
        want = {"pandemonium_pier": {tiles.PIER_DECK, tiles.BARGE, tiles.WELCOME_ARCH, tiles.LANTERN},
                "pandemonium_press": {tiles.VINES, tiles.WINE_PRESS, tiles.VAT, tiles.WINE},
                "pandemonium_banquet": {tiles.BANQUET_TABLE, tiles.CARPET, tiles.PALACE_WALL},
                "pandemonium_mirrors": {tiles.HALL_MIRROR, tiles.BALLROOM_FLOOR, tiles.CHANDELIER},
                "pandemonium_bandstand": {tiles.BANDSTAND, tiles.INSTRUMENT, tiles.LANTERN},
                "pandemonium_table": {tiles.BANQUET_TABLE, tiles.CARPET, tiles.FIRE_BRAZIER},
                "pandemonium_fountain": {tiles.WINE_FOUNTAIN, tiles.FOUNTAIN_RIM},
                "pandemonium_statue": {tiles.GILDED_STATUE}}
        for m in p.marks:
            if m.key in want:
                flat = {t for row in m.rows for t in row if t is not None}
                self.assertTrue(want[m.key] <= flat, m.key)


class TilesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = ChunkedWorld(31)
        cls.z = cls.w.layout.zone("pandemonium")
        cls.p = plan_of(cls.w.layout, cls.z)

    def test_the_pier_reaches_out_over_the_sea(self):
        gx, gy = self.p.facing
        x, y = round(self.p.gate[0] + gx * 26), round(self.p.gate[1] + gy * 26)
        self.assertIs(self.w.layout.biome_at(x + 0.5, y + 0.5), biomes.OCEAN)
        self.assertIs(tiles_in(self.w, x, y, x + 1, y + 1)[(x, y)], tiles.PIER_DECK)

    def test_the_avenue_goes_down_the_terraces_and_over_the_lake(self):
        line = self.p.roads[0]
        seen = set()
        for (ax, ay), (bx, by) in zip(line, line[1:]):
            n = int(math.hypot(bx - ax, by - ay))
            for k in range(0, n, 2):
                x, y = math.floor(ax + (bx - ax) * k / n), math.floor(ay + (by - ay) * k / n)
                seen.add(tiles_in(self.w, x, y, x + 1, y + 1)[(x, y)])
        self.assertIn(tiles.GILT_ROAD, seen)
        self.assertIn(tiles.GILT_BRIDGE, seen)              # the causeway
        self.assertIn(tiles.GOLD_STAIRS, seen)              # down the terraces
        self.assertFalse(seen & {tiles.WINE, tiles.TERRACE_EDGE})

    def test_lanterns_light_the_avenues(self):
        pts = [pt for v in self.p.lanterns.values() for pt in v]
        self.assertGreater(len(pts), 100)
        tx, ty = pts[len(pts) // 3]
        self.assertIn(tiles_in(self.w, tx, ty, tx + 1, ty + 1)[(tx, ty)],
                      (tiles.LANTERN, tiles.GILT_ROAD, tiles.GOLD_STAIRS, tiles.WINE,
                       tiles.GILT_BRIDGE))

    def test_the_pit_terraces_lake_and_river(self):
        cx, cy, a, b = self.p.hall
        gx, gy = self.p.facing
        w = self.p.WALL
        # Down the far side's line from the shore to the hall: every terrace
        # edge crossed, the deep floor inside, then the lake.
        x = int(cx) + 5
        col = tiles_in(self.w, x, int(cy + b + w), x + 1, int(cy + b + w + 170))
        ts = [col[(x, y)] for y in sorted(y for _, y in col)]
        self.assertGreaterEqual(sum(t is tiles.TERRACE_EDGE for t in ts),
                                len(config.PANDEMONIUM_TERRACES) - 1)
        self.assertIn(tiles.WINE, ts[:config.PANDEMONIUM_LAKE])
        self.assertIn(tiles.OBSIDIAN_DEEP, ts[:w + config.PANDEMONIUM_DEEP])
        self.assertNotIn(tiles.OBSIDIAN_DEEP, ts[w + config.PANDEMONIUM_DEEP + 6:])
        seen = set()
        for (ax, ay), (bx, by) in zip(self.p.river, self.p.river[1:]):
            mx, my = int((ax + bx) / 2), int((ay + by) / 2)
            seen |= set(tiles_in(self.w, mx - 3, my - 3, mx + 3, my + 3).values())
        self.assertIn(tiles.WINE, seen)

    def test_the_sea_turns_to_wine_and_the_shore_to_coins(self):
        z = self.z
        sx = z.cx + int(z.shore_along(1, 0))
        near = set(tiles_in(self.w, sx + 1, z.cy, sx + 8, z.cy + 1).values())
        self.assertIn(tiles.WINE_SEA, near)
        far = tiles_in(self.w, sx + config.PANDEMONIUM_WINE_SEA + 4, z.cy,
                       sx + config.PANDEMONIUM_WINE_SEA + 8, z.cy + 1)
        self.assertEqual(set(far.values()), {tiles.WATER})
        beach = set(tiles_in(self.w, sx - config.PANDEMONIUM_BEACH, z.cy - 6, sx + 1, z.cy + 6).values())
        self.assertIn(tiles.COIN_BEACH, beach)

    def test_water_walkers_cross_the_wine(self):
        ww = WaterWalk(self.w)
        sx = self.z.cx + int(self.z.shore_along(1, 0))
        for (x, y), t in tiles_in(self.w, sx + 1, self.z.cy, sx + 8, self.z.cy + 1).items():
            if t is tiles.WINE_SEA:
                self.assertFalse(ww.tile_at(x, y).solid)
        for t in (tiles.WINE, tiles.WINE_FOUNTAIN, tiles.WINE_SEA):
            self.assertTrue(t.solid)

    def test_its_ground(self):
        got = set()
        for dx, dy in ((150, -40), (-150, 60), (90, 160), (-200, -120)):
            x, y = self.z.cx + dx, self.z.cy + dy
            got |= set(tiles_in(self.w, x, y, x + 40, y + 20).values())
        self.assertIn(tiles.OBSIDIAN, got)
        self.assertTrue(got & {tiles.GOLD_VEIN, tiles.COIN_HEAP, tiles.COINS})

    def test_tables_break_into_a_spilled_feast(self):
        t = tiles.BANQUET_TABLE
        self.assertTrue(t.destructible)
        self.assertIs(t.becomes, tiles.SPILLED_FEAST)
        self.assertFalse(t.blocks_shots)
        self.assertIs(tiles.GILDED_STATUE.becomes, tiles.COINS)
        self.assertIs(tiles.COIN_HEAP.becomes, tiles.COINS)

    def test_no_enemies_yet(self):
        self.assertEqual(config.BIOME_ENEMY_DENSITY.get("pandemonium", 0.0), 0.0)   # (M30.2)


class MapTest(unittest.TestCase):
    def test_hidden_until_found(self):
        w = ChunkedWorld(31)
        z = w.layout.zone("pandemonium")
        dim = maps._DIM_OFFSET + biomes.PANDEMONIUM.id
        px = lambda: maps.map_pixels(w, z.cx, z.cy, 8.0, 40, 40)
        self.assertFalse((px() == dim).any())
        w.found_zones.add("pandemonium")
        self.assertTrue((px() == dim).any())
        self.assertGreater(w.layout.view_radius({"pandemonium"}), z.cy + z.radius)

    def test_every_tile_has_a_map_colour_and_a_class(self):
        self.assertEqual(len(maps._COLORS), len(explored.MAP_TILES) + len(biomes.BY_ID))
        self.assertGreater(explored.UNSEEN, 255)            # (16-bit map classes since M30.1)
        self.assertLess(len(explored.MAP_TILES), explored.UNSEEN)
        for t in (tiles.WINE_SEA, tiles.GILDED_STATUE, tiles.OBSIDIAN):
            self.assertIn(t, explored.MAP_TILES)


class DefinedOnceTest(unittest.TestCase):
    """A name defined twice at module level silently replaces the first
    everywhere: Paradise's STATUE, THRONE and COLUMN took over the Snow
    King's hall and the Magus's observatory (fixed M30.1), and several
    colours had done the same."""

    def names(self, rel):
        with open(os.path.join(_HERE, rel)) as src:
            return [line.split("=")[0].strip() for line in src
                    if line[:1].isupper() and " = " in line and not line.startswith(" ")]

    def test_palette_and_tiles_define_each_name_once(self):
        for rel in ("palette.py", os.path.join("world", "tiles.py")):
            names = self.names(rel)
            self.assertEqual(sorted({n for n in names if names.count(n) > 1}), [], rel)

    def test_the_old_lairs_have_their_own_tiles_again(self):
        self.assertEqual(tiles.STATUE.name, "frozen statue")
        self.assertEqual(tiles.THRONE.name, "ice throne")
        self.assertEqual(tiles.COLUMN.name, "column")
        self.assertEqual(tiles.MARBLE_COLUMN.name, "marble column")
        self.assertEqual(len(palette.RUNE), 3)              # (the Magus's runes need three)


class GameTest(unittest.TestCase):
    def setUp(self):
        from ascii_adventurers.tests.test_m16 import game
        self.m, self.s = game("wizard", seed=31)
        self.s.app.dev = True

    def test_dev_jump_reaches_pandemonium_and_a_banner_on_arrival(self):
        s = self.s
        s._dev_zone()                                       # Paradise...
        s._dev_zone()                                       # ...then Pandemonium
        h = s.hero
        self.assertTrue(h.water_walk)
        self.assertIs(s.world.biome_at(math.floor(h.x), math.floor(h.y)), biomes.PANDEMONIUM)
        s.arrived.clear()
        s.quests.banner = None
        s._step(1 / 60)
        self.assertIn("pandemonium", s.world.found_zones)
        self.assertEqual((s.quests.banner.title, s.quests.banner.sub),
                         ("PANDEMONIUM", "where the feast never ends"))

    def test_draws_on_pandemonium(self):
        s = self.s
        s._dev_zone()
        s._dev_zone()
        s.quests.banner = None
        s.draw(self.m.text)
        s.big_map.open(s.hero.x, s.hero.y)
        s.draw(self.m.text)


if __name__ == "__main__":
    unittest.main()
