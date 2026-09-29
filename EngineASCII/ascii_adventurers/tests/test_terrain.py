import os
import time
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from engine import Display, TextRenderer

from ascii_adventurers import config, palette
from ascii_adventurers.engine_ext.camera import Camera
from ascii_adventurers.render.terrain import TerrainRenderer
from ascii_adventurers.world.chunked import ChunkedWorld
from ascii_adventurers.world.tiles import Damage


def reference_draw(text, world, camera):
    """The old uncached renderer: every tile's glyph drawn with put_px."""
    canvas = text.display.canvas
    canvas.set_clip(pygame.Rect(0, 0, camera.view_w, camera.view_h))
    tx0, ty0, tx1, ty1 = camera.visible_tiles()
    for ty in range(ty0, ty1 + 1):
        for tx in range(tx0, tx1 + 1):
            tile = world.tile_at(tx, ty)
            text.put_px(*camera.tile_to_px(tx, ty), world.glyph_at(tx, ty), tile.fg, tile.bg)
    canvas.set_clip(None)


class TerrainCacheTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.display = Display(128, 30)
        cls.text = TextRenderer(cls.display)
        d = cls.display
        cls.world = ChunkedWorld(7)

    def setUp(self):
        d = self.display
        self.camera = Camera(d.cols, d.rows - config.HUD_ROWS, d.cell_w, d.cell_h)
        self.terrain = TerrainRenderer(self.text)

    def frames(self):
        """(cached, reference) canvas copies for the current camera."""
        self.text.clear(palette.BACKGROUND)
        self.terrain.draw(self.world, self.camera)
        cached = self.display.canvas.copy()
        self.text.clear(palette.BACKGROUND)
        reference_draw(self.text, self.world, self.camera)
        return cached, self.display.canvas.copy()

    def assertSamePixels(self, a, b):
        self.assertEqual(pygame.image.tobytes(a, "RGB"), pygame.image.tobytes(b, "RGB"))

    def test_matches_per_glyph_drawing_at_any_offset(self):
        sx, sy = self.world.spawn_point()
        # Includes sub-tile offsets and negative tile coordinates.
        for dx, dy in ((0, 0), (0.37, 0.81), (-sx - 3.3, -sy - 5.6), (17.05, -9.5)):
            self.camera.center_on(sx + dx, sy + dy)
            self.assertSamePixels(*self.frames())

    def test_damaged_and_destroyed_tiles_are_repainted(self):
        self.camera.center_on(*self.world.spawn_point())
        tx0, ty0, tx1, ty1 = self.camera.visible_tiles()
        targets = [(tx, ty) for ty in range(ty0 + 1, ty1) for tx in range(tx0 + 1, tx1)
                   if self.world.tile_at(tx, ty).destructible]
        self.assertTrue(targets, "no destructible tile in view")
        self.frames()                                   # blocks now cached
        tx, ty = targets[0]
        hp = self.world.tile_at(tx, ty).hp
        self.assertEqual(self.world.damage_tile(tx, ty, 1), Damage.DAMAGED)
        self.assertSamePixels(*self.frames())
        self.assertEqual(self.world.damage_tile(tx, ty, hp), Damage.DESTROYED)
        self.assertSamePixels(*self.frames())

    def test_never_draws_into_the_hud_rows(self):
        self.camera.center_on(*self.world.spawn_point())
        self.display.canvas.fill((1, 2, 3))
        self.terrain.draw(self.world, self.camera)
        hud_top = self.camera.view_h
        self.assertEqual(self.display.canvas.get_at((5, hud_top + 1))[:3], (1, 2, 3))
        self.assertEqual(self.display.canvas.get_clip(), self.display.canvas.get_rect())

    def test_cache_is_bounded_and_reused(self):
        x, y = self.world.spawn_point()
        for i in range(300):
            self.camera.center_on(x + i * 2.0, y + i * 0.5)
            self.terrain.draw(self.world, self.camera)
        # 300 frames of travel pass ~600 blocks; the cache keeps two rings.
        tx0, ty0, tx1, ty1 = self.camera.visible_tiles()
        n = config.TERRAIN_BLOCK_TILES
        ring = (tx1 // n - tx0 // n + 3) * (ty1 // n - ty0 // n + 3)
        self.assertLessEqual(len(self.terrain._blocks), max(config.TERRAIN_CACHE_BLOCKS, 2 * ring))
        drawn = self.terrain.blocks_drawn
        self.terrain.draw(self.world, self.camera)          # same view again
        self.assertEqual(self.terrain.blocks_drawn, drawn)

    def test_ring_is_predrawn_so_scrolling_in_draws_nothing_new(self):
        x, y = self.world.spawn_point()
        self.camera.center_on(x, y)
        for _ in range(40):                      # a few blocks per frame
            self.terrain.draw(self.world, self.camera)
        n = config.TERRAIN_BLOCK_TILES
        self.camera.center_on(x + n, y + n)      # one block over, diagonally
        tx0, ty0, tx1, ty1 = self.camera.visible_tiles()
        visible = {(bx, by) for by in range(ty0 // n, ty1 // n + 1)
                   for bx in range(tx0 // n, tx1 // n + 1)}
        self.assertTrue(visible <= set(self.terrain._blocks))

    def test_prefetch_never_builds_chunks_on_the_spot(self):
        w = ChunkedWorld(11)
        x, y = w.spawn_point()
        self.camera.center_on(x, y)
        w.ensure_ready(*self.camera.visible_tiles())   # only the view is built
        before = w.sync_builds
        for _ in range(40):
            self.terrain.draw(w, self.camera)
        self.assertEqual(w.sync_builds, before)

    def test_steady_frame_is_fast(self):
        self.camera.center_on(*self.world.spawn_point())
        self.terrain.draw(self.world, self.camera)
        t = time.perf_counter()
        for _ in range(50):
            self.terrain.draw(self.world, self.camera)
        self.assertLess((time.perf_counter() - t) / 50 * 1000, 2.0)


class GlyphRedefineTest(unittest.TestCase):
    """Engine change B2: redefining a custom glyph drops only its images."""

    def test_register_replaces_and_unregister_restores(self):
        d = Display(20, 5)
        text = TextRenderer(d)
        ch = ""

        def solid(color):
            return lambda cell, fg: cell.fill(color)

        text.register_glyph(ch, solid((255, 0, 0)))
        text.put(0, 0, ch, (9, 9, 9), None)
        text.put(1, 0, "A", (9, 9, 9), (0, 0, 0))
        self.assertEqual(d.canvas.get_at((1, 1))[:3], (255, 0, 0))
        text.register_glyph(ch, solid((0, 255, 0)))
        text.put(0, 0, ch, (9, 9, 9), None)
        self.assertEqual(d.canvas.get_at((1, 1))[:3], (0, 255, 0))
        self.assertIn(("A", (9, 9, 9), (0, 0, 0)), text._glyph_cache)   # untouched
        text.unregister_glyph(ch)
        self.assertNotIn(ch, text._keys_by_char)
        self.assertFalse([k for k in text._glyph_cache if k[0] == ch])


if __name__ == "__main__":
    unittest.main()
