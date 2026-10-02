"""M21: the haunted forest -- open ground, big gnarled trees that only
block at the trunk, seamless across chunk edges, stumps, logs, fog and wisp
lights."""

import math
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.tests.test_world import ring_point
from ascii_adventurers.world import biomes, tiles
from ascii_adventurers.world.chunked import ChunkedWorld

SEED = 31


class HauntedForestTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = ChunkedWorld(SEED)
        cls.cx, cls.cy = ring_point(cls.w.layout, biomes.FOREST)
        n = config.CHUNK_SIZE
        # A window spanning several chunk edges.
        cls.box = (cls.cx - 2 * n, cls.cy - n, cls.cx + 2 * n, cls.cy + n)
        x0, y0, x1, y1 = cls.box
        cls.w.ensure_ready(x0 - 4, y0 - 4, x1 + 4, y1 + 4)

    def forest_tiles(self):
        x0, y0, x1, y1 = self.box
        for ty in range(y0, y1):
            for tx in range(x0, x1):
                if self.w.biome_at(tx, ty) is biomes.FOREST:
                    yield tx, ty, self.w.tile_at(tx, ty)

    def test_mostly_open(self):
        found = list(self.forest_tiles())
        self.assertGreater(len(found), 2000)
        # What grows there (lakes are their own thing and didn't change).
        land = [t for _, _, t in found if t is not tiles.WATER]
        solid = sum(t.solid for t in land) / len(land)
        self.assertLess(solid, 0.06)                     # the pine thickets were ~46%
        names = {t.name for _, _, t in found}
        self.assertTrue({"gnarled tree", "branches", "dead leaves", "stump"} <= names)
        self.assertNotIn("pine", names)

    def test_trees_stand_apart_and_wear_whole_crowns(self):
        trunks = [(x, y) for x, y, t in self.forest_tiles() if t is tiles.GNARLED_TRUNK]
        self.assertGreater(len(trunks), 20)
        for i, (ax, ay) in enumerate(trunks):
            for bx, by in trunks[i + 1:]:
                self.assertGreaterEqual(max(abs(ax - bx), abs(ay - by)), 3)
        # Crowns are whole even where a chunk edge cuts through them.
        n = config.CHUNK_SIZE
        cut = [(x, y) for x, y in trunks if any((x + dx) // n != x // n or (y + dy) // n != y // n
                                                for dx, dy in tiles.CROWN)]
        self.assertTrue(cut)
        for x, y in trunks:
            for (dx, dy), piece in tiles.CROWN.items():
                got = self.w.tile_at(x + dx, y + dy)
                if self.w.biome_at(x + dx, y + dy) is biomes.FOREST and not got.solid \
                        and got is not tiles.WATER:
                    self.assertIs(got, piece, (x, y, dx, dy))

    def test_only_the_trunk_blocks(self):
        for piece in tiles.CROWN.values():
            self.assertFalse(piece.solid or piece.blocks_shots)
        self.assertTrue(tiles.GNARLED_TRUNK.solid and tiles.GNARLED_TRUNK.blocks_shots)
        self.assertFalse(tiles.GNARLED_TRUNK.destructible)
        for t in (tiles.STUMP, tiles.LOG_LEFT, tiles.LOG_MID, tiles.LOG_RIGHT):
            self.assertTrue(t.solid and t.destructible)
            self.assertIs(t.becomes, tiles.BARK)
        self.assertFalse(tiles.FOG.solid)

    def test_logs_are_whole(self):
        x0, y0, x1, y1 = self.box
        logs = 0
        for ty in range(y0, y1):
            for tx in range(x0, x1):
                if self.w.tile_at(tx, ty) is tiles.LOG_LEFT:
                    logs += 1
                    k = 1
                    while self.w.tile_at(tx + k, ty) is tiles.LOG_MID:
                        k += 1
                    self.assertIs(self.w.tile_at(tx + k, ty), tiles.LOG_RIGHT)
        self.assertGreater(logs, 0)

    def test_wisp_lights(self):
        x0, y0, x1, y1 = self.box
        lights = self.w.lights_in(x0, y0, x1, y1)
        self.assertTrue(lights)
        for x, y in lights:
            self.assertIs(self.w.biome_at(math.floor(x), math.floor(y)), biomes.FOREST)

    def test_same_world_any_order(self):
        other = ChunkedWorld(SEED)
        x0, y0, x1, y1 = self.box
        pts = [(x, y) for y in range(y1 - 1, y0, -7) for x in range(x1 - 1, x0, -5)]
        self.assertEqual([other.tile_at(*p) for p in pts], [self.w.tile_at(*p) for p in pts])

    def test_players_see_its_name(self):
        self.assertEqual(biomes.FOREST.name, "forest")            # tables and records
        self.assertEqual(biomes.FOREST.title, "haunted forest")
        self.assertIn("forest", config.ENEMIES["boar"].biomes)   # the boar carries over


if __name__ == "__main__":
    unittest.main()
