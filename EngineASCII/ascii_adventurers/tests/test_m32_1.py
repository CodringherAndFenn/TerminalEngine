"""M32.1: Panopticon's land, the east zone (design/OCEAN.md 35-40): the
machine city -- the watchtower and its hall of cells, wedge districts round
it (street grids, walls and gates), the sea wall, the factory, the
scrapyard, the kept homes, the seven masts; laser fences, belts and
presses, live power, the cleaning."""

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
from ascii_adventurers.world.panopticon import DOCKS, FACTORY, HOMES, SCRAPYARD, TOWER
from ascii_adventurers.world.zones import _farthest_land, plan_of

SEEDS = (31, 7, 12)


def tiles_in(world, x0, y0, x1, y1):
    world.ensure_ready(x0, y0, x1, y1)
    return {(x, y): world.tile_at(x, y) for y in range(y0, y1) for x in range(x0, x1)}


def pan(seed=31):
    lay = IslandLayout(seed)
    return lay, lay.zone("panopticon"), plan_of(lay, lay.zone("panopticon"))


class PlacementTest(unittest.TestCase):
    def test_panopticon_is_due_east_a_minute_off_the_coast(self):
        for seed in SEEDS:
            lay, z, _ = pan(seed)
            self.assertEqual([q.key for q in lay.zones],
                             ["paradise", "pandemonium", "pangaea", "panopticon"])
            self.assertEqual((z.place, z.cy), ("E", 0))
            self.assertGreater(z.cx, lay.max_land_radius)
            zones, lay.zones = lay.zones, ()
            far = _farthest_land(lay, 0.0)
            lay.zones = zones
            self.assertGreaterEqual(z.cx - z.max_radius - far, config.ZONE_GAP - 1, seed)
            self.assertIs(lay.biome_at(z.cx, z.cy), biomes.PANOPTICON)
            self.assertIs(lay.biome_at(z.cx + z.max_radius + 5, z.cy), biomes.OCEAN)
            self.assertEqual(z.facing, (-1.0, 0.0))          # (toward the main island)
            self.assertEqual(config.ZONE_ARRIVAL["panopticon"], "where nothing goes unseen")


class PlanTest(unittest.TestCase):
    def test_every_landmark_is_placed(self):
        for seed in SEEDS:
            lay, z, p = pan(seed)
            for name in ("factory", "scrapyard", "homes"):
                self.assertIsNotNone(getattr(p, name), (seed, name))
            keys = [m.key for m in p.marks]
            for key in ("panopticon_tower", "panopticon_sea_wall", "panopticon_factory",
                        "panopticon_scrapyard", "panopticon_homes"):
                self.assertEqual(keys.count(key), 1, (seed, key))
            for m in p.marks:
                self.assertTrue(z.inside(m.cx, m.cy), (seed, m.key))
                self.assertEqual(m.biome, "panopticon")
            self.assertIs(p, plan_of(lay, z))                # built once
            self.assertTrue(all(m in lay.landmarks for m in p.marks))

    def test_wedges_round_the_tower(self):
        for seed in SEEDS:
            _, z, p = pan(seed)
            self.assertEqual(sorted(p.names), sorted((DOCKS, FACTORY, SCRAPYARD, HOMES)))
            self.assertEqual(p.names[0], DOCKS)              # (facing the main island)
            self.assertEqual(p.names[2], SCRAPYARD)          # (behind the tower)
            self.assertEqual(p.district_at(z.cx, z.cy), TOWER)
            gx, gy = p.facing
            self.assertEqual(p.district_at(*p.gate), DOCKS)
            self.assertEqual(p.district_at(z.cx - gx * 200, z.cy), SCRAPYARD)
            self.assertEqual(p.district_at(*p.factory), FACTORY)
            self.assertEqual(p.district_at(*p.scrapyard), SCRAPYARD)
            self.assertEqual(p.district_at(*p.homes), HOMES)
            self.assertEqual(len(p.walls), 4)
            for wx, wy, r0, r1, gates in p.walls:
                self.assertEqual(len(gates), len(config.PANOPTICON_WALL_GATES))
                self.assertTrue(all(r0 < g < r1 for g in gates))

    def test_seven_masts_in_every_district(self):
        for seed in SEEDS:
            _, _, p = pan(seed)
            self.assertEqual(len(p.masts), config.PANOPTICON_MASTS, seed)
            self.assertEqual({d for _, _, d in p.masts}, {DOCKS, FACTORY, SCRAPYARD, HOMES})
            for i, (x, y, d) in enumerate(p.masts):
                self.assertEqual(p.district_at(x + 0.5, y + 0.5), d)
                for qx, qy, _ in p.masts[i + 1:]:
                    self.assertGreaterEqual(math.hypot(x - qx, y - qy), config.PANOPTICON_MAST_GAP - 1)
            # (three pylons round each, cabled to it)
            mast_spans = [s for s in p.spans if s[1] < 0]
            self.assertEqual(len(mast_spans), 3 * len(p.masts))

    def test_the_same_seed_gives_the_same_panopticon(self):
        with fresh_islands():
            a, b = pan(7)[2], pan(7)[2]
        self.assertEqual((a.gate, a.names, a.factory, a.scrapyard, a.homes, a.masts, a.pylons,
                          a.presses), (b.gate, b.names, b.factory, b.scrapyard, b.homes, b.masts,
                                       b.pylons, b.presses))
        self.assertEqual([(f.kind, f.x0, f.y0) for f in a.fences], [(f.kind, f.x0, f.y0) for f in b.fences])

    def test_the_tower_is_sealed_by_blast_doors_facing_the_sea_wall(self):
        _, _, p = pan()
        tower = next(m for m in p.marks if m.key == "panopticon_tower")
        self.assertEqual(tower.kind, "lair")                 # (the quest's lair since M32.4)
        self.assertGreaterEqual(len(tower.gate), config.PANOPTICON_HALL_GATE)
        gx, gy = p.facing
        for tx, ty in tower.gate:
            self.assertIs(tower.tile_at(tx, ty), tiles.BLAST_DOOR)
            self.assertGreater((tx + 0.5 - tower.cx) * gx + (ty + 0.5 - tower.cy) * gy, 0)
        self.assertTrue(tower.props["barred"])
        self.assertIs(tower.props["seal"], tiles.BLAST_DOOR)
        self.assertEqual(len(tower.props["pillars"]), config.PANOPTICON_HALL_PILLARS)
        flat = {t for row in tower.rows for t in row if t is not None}
        self.assertTrue({tiles.TOWER_WALL, tiles.CELL_DOOR, tiles.CELL_SCREEN, tiles.CELL_FLOOR,
                         tiles.HALL_PILLAR} <= flat)
        self.assertIs(tower.tile_at(math.floor(tower.cx), math.floor(tower.cy)), tiles.CELL_FLOOR)

    def test_landmarks_have_their_furniture(self):
        _, _, p = pan()
        want = {"panopticon_sea_wall": {tiles.SEA_WALL, tiles.LOCK_FLOOR, tiles.VOICE_SCREEN},
                "panopticon_factory": {tiles.SHED_WALL, tiles.FACTORY_FLOOR, tiles.BELT_E, tiles.BELT_W,
                                       tiles.PRESS_BED, tiles.PRESS_FRAME, tiles.ROBOT_ARM, tiles.CHASSIS},
                "panopticon_scrapyard": {tiles.CHAIN_FENCE, tiles.YARD_DIRT, tiles.SCRAP_HEAP,
                                         tiles.LOOSE_SCRAP, tiles.WRECK},
                "panopticon_homes": {tiles.HOME_WALL, tiles.HOME_FLOOR, tiles.SET_TABLE, tiles.MADE_BED,
                                     tiles.HEDGE, tiles.LAWN}}
        for m in p.marks:
            if m.key in want:
                flat = {t for row in m.rows for t in row if t is not None}
                self.assertTrue(want[m.key] <= flat, m.key)
        wall = next(m for m in p.marks if m.key == "panopticon_sea_wall")
        sx, sy = wall.props["screen"]
        self.assertIs(wall.tile_at(math.floor(sx), math.floor(sy)), tiles.LOCK_FLOOR)
        self.assertIs(wall.tile_at(*p.gate), tiles.LOCK_FLOOR)
        homes = next(m for m in p.marks if m.key == "panopticon_homes")
        self.assertEqual(len(homes.props["homes"]), 10)
        # (the factory's presses are the city's presses too)
        fac = next(m for m in p.marks if m.key == "panopticon_factory")
        beds = [t for t, i in p.press_at.items() if fac.tile_at(*t) is tiles.PRESS_BED]
        self.assertEqual(len(beds), 4 * 4 * 6)

    def test_fences_belts_presses_and_power(self):
        for seed in SEEDS:
            _, _, p = pan(seed)
            kinds = [f.kind for f in p.fences]
            self.assertGreaterEqual(kinds.count("blink"), 4 * len(config.PANOPTICON_WALL_GATES))
            self.assertGreaterEqual(kinds.count("sweep"), 8)
            # (the street presses only in the factory district)
            for x, y, _ in p.presses:
                self.assertEqual(p.district_at(x, y), FACTORY)
            self.assertGreater(len(p.presses), 16)
            # (every span joins a pylon, and every pylon is on a span)
            for i, j, *_ in p.spans:
                self.assertIn(p.pylons[i], p.pylon_at)
            self.assertEqual(set(p.pylon_spans), set(range(len(p.pylons))))
            self.assertGreater(len(p.spans), 100)


class TilesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = ChunkedWorld(31)
        cls.z = cls.w.layout.zone("panopticon")
        cls.p = plan_of(cls.w.layout, cls.z)

    def test_each_district_its_own_blocks(self):
        p, z = self.p, self.z
        style = {DOCKS: {tiles.WAREHOUSE_WALL, tiles.WAREHOUSE_ROOF},
                 FACTORY: {tiles.SHED_WALL, tiles.SHED_ROOF},
                 HOMES: {tiles.FLAT_WALL, tiles.FLAT_ROOF},
                 SCRAPYARD: {tiles.SCRAP_HEAP, tiles.LOOSE_SCRAP}}
        for k, name in enumerate(p.names):
            ax, ay = p.axes[k]
            r = (p.u0[k] + p.shore_u[k]) / 2
            x, y = math.floor(z.cx + ax * r - ay * 30), math.floor(z.cy + ay * r + ax * 30)
            got = set(tiles_in(self.w, x - 15, y - 15, x + 16, y + 16).values())
            self.assertTrue(style[name] & got, name)
            for other, ts in style.items():
                if other != name:
                    self.assertFalse(ts & got - {tiles.NEON_SIGN}, (name, other))
            self.assertTrue({tiles.STREET, tiles.LANE_LINE, tiles.PAVEMENT} <= got, name)

    def test_the_plaza_and_the_walls_with_their_gates(self):
        p = self.p
        cx, cy = p.cx + 0.5, p.cy + 0.5
        wx, wy, r0, r1, gates = p.walls[0]
        g = gates[1]
        at = lambda d: tiles_in(self.w, math.floor(cx + wx * d), math.floor(cy + wy * d),
                                math.floor(cx + wx * d) + 1, math.floor(cy + wy * d) + 1).popitem()[1]
        self.assertIs(at((gates[0] + gates[1]) / 2), tiles.CITY_WALL)
        self.assertFalse(at(g).solid)                        # (the gate's open: its fence's track)
        a, b = p.hall[2], p.hall[3]
        gx, gy = p.facing
        t = tiles_in(self.w, math.floor(cx + gx * (a + 10)), math.floor(cy), math.floor(cx + gx * (a + 10)) + 1,
                     math.floor(cy) + 1).popitem()[1]
        self.assertIs(t, tiles.PLAZA)

    def test_the_quay_and_the_oily_sea(self):
        z = self.z
        x = math.floor(z.cx + z.shore_along(0, 1) * 0 + 40)
        y = math.floor(z.cy + z.shore_along(0, 1))
        near = set(tiles_in(self.w, x - 6, y - 8, x + 7, y + 12).values())
        self.assertIn(tiles.QUAY, near)
        self.assertIn(tiles.OILY_SEA, near)

    def test_belts_presses_pylons_and_cables_on_the_ground(self):
        p = self.p
        x, y, _ = p.presses[0]
        got = set(tiles_in(self.w, math.floor(x) - 3, math.floor(y) - 3,
                           math.floor(x) + 4, math.floor(y) + 4).values())
        self.assertIn(tiles.PRESS_BED, got)
        self.assertIn(tiles.PRESS_FRAME, got)
        self.assertTrue(got & set(tiles.BELTS))
        s = next(s for s in range(len(p.spans)) if len(p.span_tiles[s]) > 4)
        tx, ty = p.pylons[p.spans[s][0]]
        self.assertIs(tiles_in(self.w, tx, ty, tx + 1, ty + 1)[(tx, ty)], tiles.PYLON)
        cx_, cy_ = p.span_tiles[s][0]
        self.assertIn(tiles_in(self.w, cx_, cy_, cx_ + 1, cy_ + 1)[(cx_, cy_)], (tiles.CABLE, tiles.PUDDLE))
        mx, my, _ = p.masts[0]
        self.assertIs(tiles_in(self.w, mx, my, mx + 1, my + 1)[(mx, my)], tiles.MAST_BASE)

    def test_who_walks_where(self):
        ww = WaterWalk(self.w)
        z = self.z
        y = math.floor(z.cy + z.shore_along(0, 1)) + 5
        sea = [(x, yy) for (x, yy), t in tiles_in(self.w, math.floor(z.cx) + 30, y - 3,
                                                   math.floor(z.cx) + 50, y + 10).items()
               if t is tiles.OILY_SEA]
        self.assertTrue(sea)
        self.assertFalse(ww.tile_at(*sea[0]).solid)          # (water walkers cross the oily sea)
        for t in (tiles.STREET, tiles.LANE_LINE, tiles.PAVEMENT, tiles.PLAZA, tiles.LOT, tiles.QUAY,
                  tiles.LASER_TRACK, tiles.BELT_E, tiles.PRESS_BED, tiles.CABLE, tiles.PUDDLE,
                  tiles.LOCK_FLOOR, tiles.CELL_FLOOR, tiles.FACTORY_FLOOR, tiles.YARD_DIRT,
                  tiles.HOME_FLOOR, tiles.LAWN, tiles.MAST_PAD):
            self.assertFalse(t.solid, t.name)
        for t in (tiles.WAREHOUSE_WALL, tiles.SHED_ROOF, tiles.FLAT_WALL, tiles.SCRAP_HEAP,
                  tiles.CITY_WALL, tiles.TOWER_WALL, tiles.BLAST_DOOR, tiles.SEA_WALL, tiles.MAST_BASE,
                  tiles.CELL_DOOR, tiles.HALL_PILLAR):
            self.assertTrue(t.solid and t.blocks_shots, t.name)
            self.assertFalse(t.destructible, t.name)
        for t in (tiles.LASER_POST, tiles.CHAIN_FENCE, tiles.ROBOT_ARM):
            self.assertTrue(t.solid and not t.blocks_shots, t.name)      # (they stop you, not shots)
        for t, left in ((tiles.PYLON, tiles.PYLON_STUMP), (tiles.LOOSE_SCRAP, tiles.SCRAP_BITS),
                        (tiles.SET_TABLE, tiles.A_MESS), (tiles.MADE_BED, tiles.A_MESS),
                        (tiles.HEDGE, tiles.LAWN)):
            self.assertTrue(t.destructible, t.name)
            self.assertIs(t.becomes, left)
        self.assertIn(tiles.PYLON, tiles.REPORT_BREAKS)

    def test_somebody_lives_here_now(self):
        # (M32.2: the machines; test_m32_2)
        self.assertGreater(config.BIOME_ENEMY_DENSITY.get("panopticon", 0.0), 0.0)


class MapTest(unittest.TestCase):
    def test_hidden_until_found(self):
        w = ChunkedWorld(31)
        z = w.layout.zone("panopticon")
        dim = maps._DIM_OFFSET + biomes.PANOPTICON.id
        px = lambda: maps.map_pixels(w, z.cx, z.cy, 8.0, 40, 40)
        self.assertFalse((px() == dim).any())
        w.found_zones.add("panopticon")
        self.assertTrue((px() == dim).any())

    def test_every_tile_has_a_map_colour_and_the_districts_differ(self):
        self.assertEqual(len(maps._COLORS), len(explored.MAP_TILES) + len(biomes.BY_ID))
        self.assertLess(len(explored.MAP_TILES), explored.UNSEEN)
        cls = explored._CLASS
        cols = {maps._COLORS[cls[t]] for t in (tiles.WAREHOUSE_ROOF, tiles.SHED_ROOF, tiles.FLAT_ROOF,
                                               tiles.SCRAP_HEAP)}
        self.assertEqual(len(cols), 4)


def _game():
    from ascii_adventurers.tests.test_m16 import game
    m, s = game("wizard", seed=31)
    s.app.dev = True
    return m, s


class HazardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m, cls.s = _game()
        cls.p = plan_of(cls.s.world.layout, cls.s.world.layout.zone("panopticon"))
        cls.s.spawner.update_views = lambda *a, **kw: None   # (the land alone: no machines, M32.2)

    def setUp(self):
        s = self.s
        s.enemies.clear()
        s.zones.clear()
        s.city.sweeps.clear()
        s.city.next.clear()
        s.hero.hp = s.hero.max_hp = 1000.0
        s.hero.water_walk = True
        s.quests.banner = None
        for k in ("laser_t", "shock_t", "press_hit", "arc_hits"):
            if hasattr(s.hero, k):
                delattr(s.hero, k)

    def go(self, x, y):
        from ascii_adventurers.tests.test_m17 import teleport
        s = self.s
        teleport(s, x, y)
        s.hero.x, s.hero.y = x, y

    def put(self, tile, near):
        s = self.s
        x0, y0 = map(math.floor, near)
        found = tiles_in(s.world, x0 - 40, y0 - 40, x0 + 41, y0 + 41)
        spots = sorted((math.hypot(x - x0, y - y0), x, y) for (x, y), t in found.items() if t is tile)
        self.assertTrue(spots, tile.name)
        _, x, y = spots[0]
        self.go(x + 0.5, y + 0.5)
        return x, y

    def run_for(self, secs):
        from ascii_adventurers.tests.test_m17 import step
        for _ in range(int(secs * 60)):
            step(self.s)

    def test_a_laser_burns_while_it_s_on(self):
        from ascii_adventurers.systems import panopticon as pc
        s, p = self.s, self.p
        f = next(f for f in p.fences if f.kind == "blink")
        self.go((f.x0 + f.x1) / 2, (f.y0 + f.y1) / 2)
        t_on = next(t / 100 for t in range(1000) if pc.fence_now(f, t / 100)[0] == "on")
        t_off = next(t / 100 for t in range(1000) if pc.fence_now(f, t / 100)[0] == "off")
        hp = s.hero.hp
        pc._lasers(s, p, s.hero, t_off, 1 / 60)
        self.assertEqual(s.hero.hp, hp)
        pc._lasers(s, p, s.hero, t_on, 1 / 60)
        self.assertLess(s.hero.hp, hp)
        hp = s.hero.hp
        pc._lasers(s, p, s.hero, t_on, 1 / 60)               # (not again until its beat)
        self.assertEqual(s.hero.hp, hp)
        # A sweeping one is always on, and moves.
        g = next(f for f in p.fences if f.kind == "sweep")
        segs = {round(pc.fence_now(g, t / 10)[1][0], 2) for t in range(40)}
        self.assertGreater(len(segs), 5)
        self.assertTrue(all(pc.fence_now(g, t / 10)[0] == "on" for t in range(40)))
        # A blinking one shows a tell just before it comes on.
        self.assertIn("tell", {pc.fence_now(f, t / 100)[0] for t in range(500)})

    def test_belts_carry_you(self):
        from ascii_adventurers.systems import panopticon as pc
        s, p = self.s, self.p
        x, y, _ = p.presses[0]
        tx, ty = next((tx, ty) for (tx, ty), t in tiles_in(s.world, math.floor(x) - 12, math.floor(y) - 3,
                                                           math.floor(x) + 13, math.floor(y) + 4).items()
                      if t in tiles.BELTS and math.hypot(tx - x, ty - y) > 4)
        self.go(tx + 0.5, ty + 0.5)
        belt = s.world.tile_at(tx, ty)
        dx, dy = tiles.BELTS[belt]
        x0, y0 = s.hero.x, s.hero.y
        pc._underfoot(s, p, s.hero, belt, 0.0, 0.25)
        moved = (s.hero.x - x0) * dx + (s.hero.y - y0) * dy
        self.assertAlmostEqual(moved, config.PANOPTICON_BELT * 0.25, delta=0.05)

    def test_a_press_slams_once_a_slam(self):
        from ascii_adventurers.systems import panopticon as pc
        s, p = self.s, self.p
        press = p.presses[0]
        i = 0
        tx, ty = p.press_beds[i][0]
        self.go(tx + 0.5, ty + 0.5)
        t_down = next(t / 100 for t in range(400) if pc.press_now(press, t / 100)[0] == "down")
        t_up = next(t / 100 for t in range(400) if pc.press_now(press, t / 100)[0] == "up")
        hp = s.hero.hp
        pc._underfoot(s, p, s.hero, tiles.PRESS_BED, t_up, 1 / 60)
        self.assertEqual(s.hero.hp, hp)
        pc._underfoot(s, p, s.hero, tiles.PRESS_BED, t_down, 1 / 60)
        self.assertLess(s.hero.hp, hp)
        hp = s.hero.hp
        pc._underfoot(s, p, s.hero, tiles.PRESS_BED, t_down + 0.05, 1 / 60)
        self.assertEqual(s.hero.hp, hp)
        self.assertIn("shadow", {pc.press_now(press, t / 100)[0] for t in range(300)})

    def test_live_power_shocks_and_arcs(self):
        from ascii_adventurers.systems import panopticon as pc
        s, p = self.s, self.p
        hp = s.hero.hp
        pc._underfoot(s, p, s.hero, tiles.CABLE, 0.0, 1 / 60)
        self.assertLess(s.hero.hp, hp)
        hp = s.hero.hp
        pc._underfoot(s, p, s.hero, tiles.CABLE, 0.0, 1 / 60)
        self.assertEqual(s.hero.hp, hp)                       # (its beat)
        sp = next(k for k in range(len(p.spans)) if p.spans[k][1] >= 0)
        i, j, ax, ay, bx, by = p.spans[sp]
        self.go((ax + bx) / 2, (ay + by) / 2)
        t_arc = next(t / 100 for t in range(1000) if pc.span_now(sp, t / 100)[0] == "arc")
        hp = s.hero.hp
        pc._arcs(s, p, s.hero, t_arc, set())
        self.assertLess(s.hero.hp, hp)
        hp = s.hero.hp
        pc._arcs(s, p, s.hero, t_arc + 0.05, set())
        self.assertEqual(s.hero.hp, hp)                       # (once an arc)
        pc._arcs(s, p, s.hero, t_arc + 30.0, {sp})
        self.assertEqual(s.hero.hp, hp)                       # (a dead span never arcs)

    def test_breaking_a_pylon_kills_its_lines(self):
        from ascii_adventurers.systems import panopticon as pc
        s, p = self.s, self.p
        sp = next(k for k in range(len(p.spans)) if p.spans[k][1] >= 0 and len(p.span_tiles[k]) > 3)
        i = p.spans[sp][0]
        tx, ty = p.pylons[i]
        tiles_in(s.world, tx - 12, ty - 12, tx + 13, ty + 13)
        self.go(tx + 2.5, ty + 0.5)
        for _ in range(20):
            s.world.damage_tile(tx, ty, 50)
        self.assertIs(s.world.tile_at(tx, ty), tiles.PYLON_STUMP)
        pc.step(s, [s.me], 1 / 60)
        dead = pc.dead_spans(s.world)
        self.assertTrue(set(p.pylon_spans[i]) <= dead)
        for x, y in p.span_tiles[sp]:
            self.assertIn(s.world.tile_at(x, y), (tiles.DEAD_CABLE, tiles.DEAD_PUDDLE))
        self.assertFalse([b for b in s.world.broke if b[2] is tiles.PYLON])

    def test_the_cleaning(self):
        from ascii_adventurers.systems import panopticon as pc
        s, p = self.s, self.p
        gx, gy = p.facing
        x, y = self.put(tiles.LANE_LINE, (p.gate[0] - gx * 60, p.gate[1] + 20))
        # A sweeper comes down a street near you on its own...
        s.city.next[s.me.index] = 0.0
        self.run_for(0.1)
        self.assertEqual(len(s.city.sweeps), 1)
        sw = s.city.sweeps[0]
        self.assertGreaterEqual(sw[4], 14)
        self.assertLess(sw[6], 0)                              # (its lane marked first)
        s.draw(self.m.text)
        # ...and sprays whoever's in its lane, once.
        s.city.sweeps = [[s.hero.x - 10, s.hero.y, 1.0, 0.0, 20.0, 2.5, -0.05, set()]]
        hp = s.hero.hp
        self.run_for(0.2)
        s.draw(self.m.text)
        self.run_for(1.5)
        self.assertLess(s.hero.hp, hp)
        self.assertAlmostEqual(hp - s.hero.hp, pc.hazard(s, config.PANOPTICON_SWEEP[5]), places=3)
        self.run_for(2.0)
        self.assertEqual(s.city.sweeps, [])
        # None on the tower's plaza.
        s.city.next[s.me.index] = 0.0
        cx, cy, a, b = p.hall
        self.go(cx - (a + 10), cy + 0.5)
        self.run_for(0.2)
        self.assertEqual(s.city.sweeps, [])

    def test_the_land_hits_like_the_zone_s_enemies(self):
        from ascii_adventurers.systems import panopticon as pc
        s = self.s
        self.assertAlmostEqual(pc.hazard(s, 10.0), 10.0 * config.ENEMY_DAMAGE_MULTIPLIER * config.ZONE_TOUGH[1]
                               * s.spawner.damage_mult * (1 + s.spawner.damage_bonus), delta=1.0)

    def test_each_district_has_its_banner(self):
        s, p = self.s, self.p
        s.arrived.discard("panopticon:factory")
        self.go(p.factory[0] + 0.5, p.factory[1] + 0.5)
        self.run_for(0.5)
        self.assertEqual((s.quests.banner.title, s.quests.banner.sub), config.PANOPTICON_DISTRICTS[FACTORY])
        s.quests.banner = None
        s.arrived.discard("panopticon:tower")
        cx, cy, a, b = p.hall
        self.go(cx - (a + 10), cy + 0.5)
        self.run_for(0.5)
        self.assertEqual(s.quests.banner.title, "THE WATCHTOWER")

    def test_draws_the_dangers(self):
        s, p = self.s, self.p
        f = next(f for f in p.fences if f.kind == "sweep")
        self.go((f.x0 + f.x1) / 2 + 3, (f.y0 + f.y1) / 2)
        for t in (0.0, 0.7, 1.4, 2.1, 2.8):
            s.city.clock = t
            s.draw(self.m.text)


class GameTest(unittest.TestCase):
    def setUp(self):
        self.m, self.s = _game()

    def test_dev_jump_reaches_panopticon_and_a_banner_on_arrival(self):
        s = self.s
        for _ in range(4):                                  # Paradise, Pandemonium, Pangaea, Panopticon
            s._dev_zone()
        h = s.hero
        self.assertTrue(h.water_walk)
        self.assertIs(s.world.biome_at(math.floor(h.x), math.floor(h.y)), biomes.PANOPTICON)
        self.assertFalse(s.world.tile_at(math.floor(h.x), math.floor(h.y)).solid)
        s.arrived.clear()
        s.quests.banner = None
        s._step(1 / 60)
        self.assertIn("panopticon", s.world.found_zones)
        self.assertEqual((s.quests.banner.title, s.quests.banner.sub),
                         ("PANOPTICON", "where nothing goes unseen"))

    def test_draws_on_panopticon(self):
        s = self.s
        for _ in range(4):
            s._dev_zone()
        s.quests.banner = None
        s.draw(self.m.text)
        s.big_map.open(s.hero.x, s.hero.y)
        s.draw(self.m.text)


if __name__ == "__main__":
    unittest.main()
