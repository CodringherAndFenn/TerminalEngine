import math
import os
import time
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import numpy as np
import pygame

from ascii_adventurers import config, palette
from ascii_adventurers.world import biomes, tiles
from ascii_adventurers.world.chunked import ChunkedWorld
from ascii_adventurers.world.explored import MAP_TILES, UNSEEN, ExploredMap
from ascii_adventurers.ui import maps

HALF = (43.0, 13.5)   # ultrawide view half-size, tiles


def explored_world(seed=42):
    w = ChunkedWorld(seed)
    w.update(*w.spawn_point(), *HALF, budget_ms=1e9)
    return w


class ExploredTest(unittest.TestCase):
    def test_every_tile_type_has_a_map_color(self):
        for t in MAP_TILES:
            self.assertEqual(len(maps._tile_color(t)), 3, t.name)

    def test_sample_matches_the_real_tiles(self):
        w = explored_world()
        sx, sy = map(int, w.spawn_point())
        xs, ys = np.arange(sx - 60, sx + 60), np.arange(sy - 30, sy + 30)
        cls = w.explored.sample(xs[None, :], ys[:, None])
        for j in range(0, 60, 7):
            for i in range(0, 120, 11):
                self.assertIs(MAP_TILES[cls[j, i]], w.tile_at(xs[i], ys[j]))

    def test_unexplored_is_unseen(self):
        w = explored_world()
        self.assertEqual(int(w.explored.sample(1500, 1500)), UNSEEN)
        self.assertEqual(int(ExploredMap().sample(0, 0)), UNSEEN)

    def test_remembered_after_unload_and_updated_by_damage(self):
        w = ChunkedWorld(42)
        sx, sy = w.spawn_point()
        w.update(sx, sy, *HALF, budget_ms=1e9)
        target = next((tx, ty) for ty in range(int(sy) - 40, int(sy) + 40)
                      for tx in range(int(sx) - 60, int(sx) + 60)
                      if w.tile_at(tx, ty).destructible)
        debris = w.tile_at(*target).becomes or tiles.RUBBLE
        w.damage_tile(*target, 999)
        for x in range(0, 1200, 40):                    # drive far away
            w.update(sx + x, sy, *HALF, budget_ms=1e9)
        self.assertNotIn((target[0] >> 5, target[1] >> 5), w._chunks)
        self.assertIs(MAP_TILES[int(w.explored.sample(*target))], debris)


class PixelTest(unittest.TestCase):
    def test_explored_shows_tiles_unexplored_shows_dim_biome(self):
        w = explored_world()
        sx, sy = w.spawn_point()
        idx = maps.map_pixels(w, sx, sy, 1.0, 20, 10)
        tx, ty = math.floor(sx - 10 + 0.5), math.floor(sy - 5 + 0.5)
        self.assertEqual(maps._COLORS[idx[0, 0]], maps._tile_color(w.tile_at(tx, ty)))
        # Far away, unexplored: the layout's biome, dimmed (ocean undimmed).
        far = maps.map_pixels(w, 0.0, 0.0, 400.0, 16, 16)
        lay = w.layout
        for j in range(0, 16, 5):
            for i in range(0, 16, 5):
                x, y = (i - 8 + 0.5) * 400, (j - 8 + 0.5) * 400
                if w.explored.is_explored(math.floor(x), math.floor(y)):
                    continue
                b = lay.biome_at(math.floor(x) + 0.5, math.floor(y) + 0.5)
                want = palette.MAP_BIOME["ocean"] if b is biomes.OCEAN else maps._dim(palette.MAP_BIOME[b.name])
                # The pixel uses the smooth (unjittered) layout; allow borders.
                if lay.biome_ids(math.floor(x) + 0.5, math.floor(y) + 0.5, jitter=False) == b.id:
                    self.assertEqual(maps._COLORS[far[j, i]], want)


class DisplayCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from engine import Display, TextRenderer
        from ascii_adventurers.render.sprites import SpriteBank
        cls.display = Display(172, 30)
        cls.text = TextRenderer(cls.display)
        cls.bank = SpriteBank(cls.text, config.CELLS_PER_TILE)


class BigMapTest(DisplayCase):
    def setUp(self):
        self.w = explored_world()
        self.m = maps.BigMap(self.w)
        self.player = self.w.spawn_point()
        self.m.open(*self.player)
        self.m.draw(self.text, self.bank, 27, self.player, 0.0)

    def test_opens_on_the_whole_island(self):
        w, h = self.m._size
        self.assertAlmostEqual(self.m.k * min(w, h), 2 * self.w.layout.max_land_radius * 1.04)

    def test_wheel_zooms_around_the_cursor(self):
        cw, ch = self.display.cell_w, self.display.cell_h
        cursor = (400.0, 200.0)
        before = self.m._pixel_to_world(*self.m._canvas_to_pixel(*cursor, cw, ch))
        self.m.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=3), cursor, cw, ch, self.player)
        after = self.m._pixel_to_world(*self.m._canvas_to_pixel(*cursor, cw, ch))
        self.assertLess(self.m.k, self.m._fit_k())
        self.assertAlmostEqual(before[0], after[0], places=6)
        self.assertAlmostEqual(before[1], after[1], places=6)

    def test_zoom_and_pan_are_limited(self):
        cw, ch = self.display.cell_w, self.display.cell_h
        for _ in range(60):
            self.m.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=1), (300.0, 300.0), cw, ch, self.player)
        self.assertEqual(self.m.k, config.MAP_MIN_TILES_PER_PIXEL)
        for _ in range(600):
            self.m.pan(1, 1, 0.1)
        lim = self.w.layout.max_land_radius
        self.assertLessEqual(self.m.cx, lim)
        self.assertLessEqual(self.m.cy, lim)
        self.m.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_c), None, cw, ch, self.player)
        self.assertEqual((self.m.cx, self.m.cy), self.player)

    def test_drag_pans(self):
        cw, ch = self.display.cell_w, self.display.cell_h
        cx = self.m.cx
        self.m.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(0, 0)), (500.0, 300.0), cw, ch, self.player)
        self.m.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=(0, 0)), (400.0, 300.0), cw, ch, self.player)
        self.assertAlmostEqual(self.m.cx - cx, 10 * self.m.k)   # dragged 10 cells left

    def test_labels_sit_in_their_biomes(self):
        lay = self.w.layout
        for name, x, y in self.m._labels:
            self.assertEqual(lay.biome_at(x, y).title.upper(), name)


class MinimapTest(DisplayCase):
    def test_only_recomputed_when_needed_and_cheap(self):
        w = explored_world()
        mm = maps.Minimap()
        calls = []
        orig = maps.map_pixels
        maps.map_pixels = lambda *a: calls.append(1) or orig(*a)
        try:
            x, y = w.spawn_point()
            k = config.MINIMAP_TILES_PER_PIXEL
            x = (math.floor(x / k) + 0.1) * k
            mm.draw(self.text, self.bank, w, x, y, 0.0)
            t = time.perf_counter()
            for i in range(30):   # moving within one map pixel
                mm.draw(self.text, self.bank, w, x + i * k * 0.02, y, 0.0)
            per_frame = (time.perf_counter() - t) / 30 * 1000
            self.assertEqual(len(calls), 1)
            mm.draw(self.text, self.bank, w, x + k, y, 0.0)   # next pixel
            self.assertEqual(len(calls), 2)
        finally:
            maps.map_pixels = orig
        self.assertLess(per_frame, 4.0)


class SmoothMinimapTest(DisplayCase):
    def _inner(self, mm, w, x, y):
        self.display.canvas.fill((0, 0, 0))
        mm.draw(self.text, self.bank, w, x, y, 0.0)
        cols, rows = config.MINIMAP_COLS, config.MINIMAP_ROWS
        cw, ch = self.display.cell_w, self.display.cell_h
        left = self.display.cols - cols - 2 - config.MINIMAP_MARGIN
        r = pygame.Rect((left + 1) * cw, (config.MINIMAP_MARGIN_TOP + 1) * ch, cols * cw, rows * ch)
        return self.display.canvas.subsurface(r).copy()

    def test_map_slides_pixel_by_pixel_and_fills_the_box(self):
        w = explored_world()
        mm = maps.Minimap()
        k = config.MINIMAP_TILES_PER_PIXEL
        cw = self.display.cell_w
        x, y = w.spawn_point()
        x = (math.floor(x / k) + 0.3) * k
        real_arrow = maps.draw_arrow
        maps.draw_arrow = lambda *a: None          # compare the map only
        try:
            a = self._inner(mm, w, x, y)
            # Half a map pixel east: the picture moves cw/2 px west, even
            # though the player is still inside the same map pixel.
            b = self._inner(mm, w, x + k / 2, y)
            shift = cw // 2
            aw, ah = a.get_size()
            same = pygame.Rect(shift, 0, aw - shift, ah)
            self.assertEqual(pygame.image.tobytes(a.subsurface(same), "RGB"),
                             pygame.image.tobytes(b.subsurface(same.move(-shift, 0)), "RGB"))
            # No black gaps anywhere in the box, at any offset.
            for f in (0.0, 0.25, 0.5, 0.99):
                img = self._inner(mm, w, x + f * k, y + f * k)
                for corner in ((0, 0), (aw - 1, 0), (0, ah - 1), (aw - 1, ah - 1)):
                    self.assertNotEqual(tuple(img.get_at(corner))[:3], (0, 0, 0), (f, corner))
        finally:
            maps.draw_arrow = real_arrow


class SceneMapTest(unittest.TestCase):
    def test_m_pauses_and_esc_closes_the_map_not_the_game(self):
        from engine import Audio, Display, SceneManager, Settings
        import ascii_adventurers.scenes.game as game

        d = Display(128, 30)
        m = SceneManager(d, Settings(), Audio())
        quit_called = []
        m.quit = lambda: quit_called.append(1)
        s = game.GameScene()
        s.manager = m
        s.on_enter()
        s.mouse.left_held = lambda: False
        s.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_m))
        self.assertTrue(s.map_open)
        s.hero.vx = 5.0
        pos = (s.hero.x, s.hero.y)
        for _ in range(10):
            s.update(1 / 60)
        s.draw(m.text)
        self.assertEqual((s.hero.x, s.hero.y), pos)       # paused
        s.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        self.assertFalse(s.map_open)
        self.assertEqual(quit_called, [])
        s.on_exit()


if __name__ == "__main__":
    unittest.main()
