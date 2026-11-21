"""M29.1: the ocean zones' framework and Paradise's land (design/OCEAN.md 2-3)."""

import math
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import numpy as np
import pygame

from ascii_adventurers import config
from ascii_adventurers.systems.collision import WaterWalk
from ascii_adventurers.ui import maps
from ascii_adventurers.world import biomes, tiles
from ascii_adventurers.world.chunked import ChunkedWorld
from ascii_adventurers.world.layout import IslandLayout
from ascii_adventurers.world.paradise import plan_of
from ascii_adventurers.world.zones import _farthest_land

SEEDS = (31, 7, 12)


def tiles_in(world, x0, y0, x1, y1):
    world.ensure_ready(x0, y0, x1, y1)
    return {(x, y): world.tile_at(x, y) for y in range(y0, y1) for x in range(x0, x1)}


class PlacementTest(unittest.TestCase):
    def test_paradise_is_due_north_a_minute_off_the_coast(self):
        for seed in SEEDS:
            lay = IslandLayout(seed)
            self.assertEqual([z.key for z in lay.zones], list(config.OCEAN_ZONES))
            z = lay.zone("paradise")
            self.assertEqual((z.place, z.cx), ("N", 0))
            self.assertLess(z.cy, -lay.max_land_radius)
            far = _farthest_land(lay, -math.pi / 2)
            self.assertGreaterEqual(abs(z.cy) - z.max_radius - far, config.ZONE_GAP - 1, seed)
            self.assertIs(lay.biome_at(z.cx, z.cy), biomes.PARADISE)
            self.assertIs(lay.biome_at(z.cx, z.cy - z.max_radius - 5), biomes.OCEAN)

    def test_the_other_places_stay_open_sea(self):
        lay = IslandLayout(31)
        for place in ("E", "S", "W"):
            x, y = lay.cardinal_sites()[place]
            self.assertTrue(lay.all_ocean(x - 200, y - 200, x + 200, y + 200), place)
            self.assertIsNone(lay.zone_at(x, y, 300))

    def test_the_island_is_not_a_circle(self):
        z = IslandLayout(7).zone("paradise")
        shores = [z.shore_along(math.cos(a), math.sin(a)) for a in np.linspace(0, 2 * math.pi, 32)]
        self.assertGreater(max(shores) - min(shores), z.radius * config.ZONE_COAST_AMPLITUDE * 0.5)
        self.assertLessEqual(max(shores), z.max_radius)

    def test_chunks_near_it_are_not_skipped_as_open_sea(self):
        lay = IslandLayout(31)
        z = lay.zone("paradise")
        shore = z.cy - z.shore_along(0, -1)
        self.assertFalse(lay.all_ocean(-16, shore - 10, 16, shore - 2))   # (the cloud bank)
        self.assertFalse(lay.all_ocean(z.cx - 5, z.cy - 5, z.cx + 5, z.cy + 5))

    def test_layout_and_tiles_agree_on_paradise(self):
        w = ChunkedWorld(12)
        z = w.layout.zone("paradise")
        for dx, dy in ((0, 0), (200, 50), (-180, -120), (int(z.radius), 0), (0, -int(z.radius))):
            tx, ty = z.cx + dx, z.cy + dy
            self.assertIs(w.layout.biome_at(tx + 0.5, ty + 0.5), w.biome_at(tx, ty), (dx, dy))


class PlanTest(unittest.TestCase):
    def test_every_landmark_is_placed_on_the_island(self):
        for seed in SEEDS:
            lay = IslandLayout(seed)
            z = lay.zone("paradise")
            p = plan_of(lay, z)
            self.assertIsNotNone(p.cathedral, seed)
            self.assertIsNotNone(p.stair, seed)
            self.assertEqual(len(p.choirs), config.PARADISE_CHOIRS, seed)
            self.assertEqual(len(p.fonts), config.PARADISE_FONTS, seed)
            self.assertEqual(len(p.statues), config.PARADISE_STATUES, seed)
            for m in p.marks:
                self.assertTrue(z.inside(m.cx, m.cy), (seed, m.key))
            keys = [m.key for m in p.marks]
            for key in ("paradise_court", "paradise_gate", "paradise_cathedral",
                        "paradise_stairway"):
                self.assertIn(key, keys)
            self.assertIs(p, plan_of(lay, z))                 # built once

    def test_the_same_seed_gives_the_same_paradise(self):
        a = plan_of(*(lambda L: (L, L.zone("paradise")))(IslandLayout(7)))
        b = plan_of(*(lambda L: (L, L.zone("paradise")))(IslandLayout(7)))
        self.assertEqual((a.gate, a.cathedral, a.stair, a.choirs, a.fonts, a.statues),
                         (b.gate, b.cathedral, b.stair, b.choirs, b.fonts, b.statues))
        self.assertEqual(a.roads, b.roads)
        self.assertEqual(a.river, b.river)

    def test_sites_keep_apart(self):
        lay = IslandLayout(31)
        p = plan_of(lay, lay.zone("paradise"))
        small = [m for m in p.marks if m.key not in ("paradise_court", "paradise_gate")]
        for i, m in enumerate(small):
            for n in small[i + 1:]:
                apart = (m.x0 + m.w <= n.x0 or n.x0 + n.w <= m.x0
                         or m.y0 + m.h <= n.y0 or n.y0 + n.h <= m.y0)
                self.assertTrue(apart, (m.key, n.key))

    def test_the_court_is_sealed_and_faces_the_gate(self):
        lay = IslandLayout(31)
        p = plan_of(lay, lay.zone("paradise"))
        court = next(m for m in p.marks if m.key == "paradise_court")
        self.assertEqual(court.kind, "court")
        self.assertGreaterEqual(len(court.gate), config.PARADISE_COURT_GATE)
        gx, gy = p.facing
        for tx, ty in court.gate:
            self.assertIs(court.tile_at(tx, ty), tiles.GATE_BARS)
            self.assertGreater((tx + 0.5 - court.cx) * gx + (ty + 0.5 - court.cy) * gy, 0)
        self.assertTrue(court.inside(court.cx, court.cy))
        self.assertIn("throne", court.props)


class TilesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = ChunkedWorld(31)
        cls.z = cls.w.layout.zone("paradise")
        cls.p = plan_of(cls.w.layout, cls.z)

    def test_the_gate_on_the_shore(self):
        gx, gy = self.p.gate
        got = set(tiles_in(self.w, gx - 8, gy - 8, gx + 8, gy + 8).values())
        for t in (tiles.GATE_PILLAR, tiles.GATE_BARS, tiles.MARBLE_ROAD):
            self.assertIn(t, got)

    def test_roads_posts_river_and_bridges(self):
        seen = set()
        line = self.p.river
        for (ax, ay), (bx, by) in zip(line, line[1:]):
            mx, my = int((ax + bx) / 2), int((ay + by) / 2)
            seen |= set(tiles_in(self.w, mx - 3, my - 3, mx + 3, my + 3).values())
        self.assertIn(tiles.BLOOD_RIVER, seen)
        x, y = (int(v) for v in self.p.roads[0][3])
        near = set(tiles_in(self.w, x - 6, y - 6, x + 6, y + 6).values())
        self.assertIn(tiles.MARBLE_ROAD, near)
        posts = [pt for pts in self.p.posts.values() for pt in pts]
        self.assertGreater(len(posts), 100)
        tx, ty = posts[len(posts) // 2]
        got = tiles_in(self.w, tx, ty, tx + 1, ty + 1)[(tx, ty)]
        self.assertIn(got, (tiles.GOLD_POST, tiles.MARBLE_ROAD, tiles.BLOOD_RIVER,
                            tiles.MARBLE_BRIDGE))

    def test_the_sea_turns_to_cloud_bank(self):
        z = self.z
        sx = z.cx + int(z.shore_along(1, 0))
        row = tiles_in(self.w, sx + 1, z.cy, sx + 8, z.cy + 1)
        self.assertIn(tiles.CLOUD_BANK, set(row.values()))
        far = tiles_in(self.w, sx + config.PARADISE_CLOUD_BANK + 4, z.cy,
                       sx + config.PARADISE_CLOUD_BANK + 8, z.cy + 1)
        self.assertEqual(set(far.values()), {tiles.WATER})

    def test_terraces_round_the_court(self):
        cx, cy, a, b = self.p.court
        gx, gy = self.p.facing
        top = int(cy - gy * (b + self.p.WALL))             # the court's far side
        col = tiles_in(self.w, int(cx) + 3, top - 40, int(cx) + 4, top)
        steps = sum(t is tiles.STEP for t in col.values())
        self.assertGreaterEqual(steps, len(config.PARADISE_TERRACES) - 1)

    def test_water_walkers_cross_the_blood_and_the_clouds(self):
        ww = WaterWalk(self.w)
        sx = self.z.cx + int(self.z.shore_along(1, 0))
        for (x, y), t in tiles_in(self.w, sx + 1, self.z.cy, sx + 8, self.z.cy + 1).items():
            if t is tiles.CLOUD_BANK:
                self.assertTrue(t.solid)
                self.assertFalse(ww.tile_at(x, y).solid)
        for t in (tiles.BLOOD_RIVER, tiles.BLOOD_FONT, tiles.CLOUD_BANK):
            self.assertTrue(t.solid)

    def test_no_enemies_yet(self):
        self.assertEqual(config.BIOME_ENEMY_DENSITY.get("paradise", 0.0), 0.0)


class MapTest(unittest.TestCase):
    def setUp(self):
        self.w = ChunkedWorld(31)
        self.z = self.w.layout.zone("paradise")

    def pixels(self):
        return maps.map_pixels(self.w, self.z.cx, self.z.cy, 8.0, 40, 40)

    def test_hidden_until_found(self):
        dim = maps._DIM_OFFSET + biomes.PARADISE.id
        self.assertFalse((self.pixels() == dim).any())
        self.w.found_zones.add("paradise")
        self.assertTrue((self.pixels() == dim).any())

    def test_the_big_map_reaches_it_once_found(self):
        lay = self.w.layout
        self.assertEqual(lay.view_radius(), lay.max_land_radius)
        self.assertEqual(lay.view_radius(set()), lay.max_land_radius)
        self.assertGreater(lay.view_radius({"paradise"}), abs(self.z.cy) + self.z.radius)


class GameTest(unittest.TestCase):
    def setUp(self):
        from ascii_adventurers.tests.test_m16 import game
        self.m, self.s = game("wizard", seed=31)
        self.s.app.dev = True

    def test_dev_jump_lands_on_paradise_walking_on_water(self):
        s = self.s
        s._dev_zone()
        h = s.hero
        self.assertTrue(h.water_walk)
        self.assertIs(s.world.biome_at(math.floor(h.x), math.floor(h.y)), biomes.PARADISE)

    def test_found_on_approach_and_a_banner_on_arrival(self):
        s = self.s
        s._dev_zone()
        s.world.found_zones.clear()
        s.arrived.clear()
        s.quests.banner = None
        s._step(1 / 60)
        self.assertIn("paradise", s.world.found_zones)
        self.assertEqual(s.quests.banner.title, "PARADISE")
        s.quests.banner = None
        s._step(1 / 60)
        self.assertIsNone(s.quests.banner)                   # once only

    def test_far_away_nothing_is_found(self):
        s = self.s
        for _ in range(3):
            s._step(1 / 60)
        self.assertEqual(s.world.found_zones, set())
        self.assertEqual(s.arrived, set())

    def test_draws_on_paradise(self):
        s = self.s
        s._dev_zone()
        s.quests.banner = None
        s.draw(self.m.text)
        s.big_map.open(s.hero.x, s.hero.y)
        self.assertTrue(s.map_open)
        s.draw(self.m.text)


if __name__ == "__main__":
    unittest.main()
