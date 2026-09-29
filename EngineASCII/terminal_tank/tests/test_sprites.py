import math
import unittest

import pygame

from engine import Display, TextRenderer

from terminal_tank import config, palette
from terminal_tank.render import characters, sprites

def _composite(pieces, cell_w, cell_h, span=8):
    """Blit baked (dc, dr, surf) pieces onto one surface centered on the
    anchor cell; returns (surface, center_px)."""
    w, h = (2 * span + 1) * cell_w, (2 * span + 1) * cell_h
    out = pygame.Surface((w, h), pygame.SRCALPHA)
    for dc, dr, surf in pieces:
        out.blit(surf, ((span + dc) * cell_w, (span + dr) * cell_h))
    return out, ((span + 0.5) * cell_w, (span + 0.5) * cell_h)


class RegisterGlyphTest(unittest.TestCase):
    """The approved engine hook: TextRenderer.register_glyph."""

    @classmethod
    def setUpClass(cls):
        cls.display = Display(20, 5)

    def test_custom_glyph_is_painted_and_replaceable(self):
        text = TextRenderer(self.display)
        text.register_glyph("", lambda cell, fg: cell.fill((1, 2, 3)))
        text.put(0, 0, "", (9, 9, 9), None)
        self.assertEqual(tuple(self.display.canvas.get_at((3, 3)))[:3], (1, 2, 3))
        # Re-registering must not serve the stale cached image.
        text.register_glyph("", lambda cell, fg: cell.fill((7, 8, 9)))
        text.put(0, 0, "", (9, 9, 9), None)
        self.assertEqual(tuple(self.display.canvas.get_at((3, 3)))[:3], (7, 8, 9))
        text.unregister_glyph("")
        text.put(1, 0, "A", (9, 9, 9))  # normal text still works


class PutPxTest(unittest.TestCase):
    """The approved engine hook: TextRenderer.put_px."""

    @classmethod
    def setUpClass(cls):
        cls.display = Display(20, 5)

    def test_draws_off_grid_and_clips_at_edges(self):
        text = TextRenderer(self.display)
        text.clear((0, 0, 0))
        text.register_glyph("\ue001", lambda cell, fg: cell.fill((50, 60, 70)))
        cw, ch = self.display.cell_w, self.display.cell_h
        text.put_px(13, 7, "\ue001", (9, 9, 9), None)
        get = lambda x, y: tuple(self.display.canvas.get_at((x, y)))[:3]
        self.assertEqual(get(13, 7), (50, 60, 70))              # starts at the pixel
        self.assertEqual(get(13 + cw - 1, 7 + ch - 1), (50, 60, 70))
        self.assertEqual(get(12, 7), (0, 0, 0))                 # not snapped left
        # Straddling the top-left corner: the visible part is drawn.
        text.put_px(-4, -5, "\ue001", (9, 9, 9), None)
        self.assertEqual(get(0, 0), (50, 60, 70))
        # Entirely off-canvas: no error, nothing drawn.
        text.put_px(-500, 9999, "abc")


class CharacterArtTest(unittest.TestCase):
    CW, CH = 10, 24

    def setUp(self):
        self._px = config.SPRITE_PIXEL
        config.SPRITE_PIXEL = (1, 1)

    def tearDown(self):
        config.SPRITE_PIXEL = self._px

    def _render(self, name, flip=False, frame=0, hurt=False, scale=3):
        pieces = sprites.bake(characters._painter(name, scale, flip, frame, hurt), 40,
                              self.CW, self.CH)
        surf, _ = _composite(pieces, self.CW, self.CH)
        return surf

    def test_every_sprite_is_14x18_with_known_colors(self):
        for name, rows in characters.ART.items():
            self.assertEqual(len(rows), characters.ART_H, name)
            for row in rows:
                self.assertEqual(len(row), characters.ART_W, name)
                for ch in row:
                    self.assertTrue(ch == "." or ch in palette.SPRITE_COLORS, (name, ch))

    def test_every_hero_and_body_has_art(self):
        for spec in list(config.HEROES.values()) + list(config.BODIES.values()):
            self.assertIn(spec.sprite, characters.ART, spec.name)

    def test_facing_left_is_a_mirror_image(self):
        right, left = self._render("wizard"), self._render("wizard", flip=True)
        w = right.get_width()
        for x in range(0, w, 3):
            for y in range(0, right.get_height(), 3):
                self.assertEqual(right.get_at((x, y)), left.get_at((w - 1 - x, y)))

    def test_walk_frames_and_hit_flash_change_the_picture(self):
        base = pygame.image.tobytes(self._render("knight"), "RGBA")
        for kw in ({"frame": 1}, {"frame": 3}, {"hurt": True}):
            self.assertNotEqual(pygame.image.tobytes(self._render("knight", **kw), "RGBA"), base, kw)
        # Frames 0 and 2 are both "standing".
        self.assertEqual(pygame.image.tobytes(self._render("knight", frame=2), "RGBA"), base)

    def test_screen_angle_accounts_for_non_square_tiles(self):
        # World 45 deg = 1 tile right, 1 tile down = 20 px right, 24 px down.
        a = sprites.screen_angle(math.radians(45), 10, 24, 2)
        self.assertAlmostEqual(a, math.atan2(24, 20))


if __name__ == "__main__":
    unittest.main()
