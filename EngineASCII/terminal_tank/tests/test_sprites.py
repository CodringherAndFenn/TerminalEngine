import math
import unittest

import pygame

from engine import Display, TextRenderer

from terminal_tank import config, palette
from terminal_tank.render import sprites

SPEC = config.TANKS[config.START_TANK]


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


class SpriteShapeTest(unittest.TestCase):
    CW, CH = 10, 24

    def setUp(self):
        self._px = config.SPRITE_PIXEL
        config.SPRITE_PIXEL = (1, 1)

    def tearDown(self):
        config.SPRITE_PIXEL = self._px

    def test_barrel_is_straight_at_any_angle(self):
        # Every point along the true aim line, between the dome and the
        # muzzle, must be barrel-colored: no staircase, no gaps.
        for deg in range(0, 360, 7):
            a = math.radians(deg)
            pieces = sprites.bake(sprites.paint_turret(a, SPEC), 60, self.CW, self.CH)
            surf, (cx, cy) = _composite(pieces, self.CW, self.CH)
            for dist in range(SPEC.turret_radius_px + 3, SPEC.barrel_length_px - 6, 3):
                px = surf.get_at((int(cx + math.cos(a) * dist), int(cy + math.sin(a) * dist)))
                self.assertEqual(tuple(px)[:3], palette.TANK_BARREL, f"{deg} deg at {dist}px")

    def test_hull_keeps_its_area_when_rotated(self):
        # The old half-block hull lost most of its area on diagonals. A
        # rotated rectangle should cover about the same pixels at any angle.
        def area(deg):
            pieces = sprites.bake(sprites.paint_hull(math.radians(deg), SPEC), 40, self.CW, self.CH)
            surf, _ = _composite(pieces, self.CW, self.CH)
            return sum(
                1 for x in range(surf.get_width()) for y in range(surf.get_height())
                if surf.get_at((x, y)).a
            )

        base = area(0)
        for deg in (22.5, 45, 67.5, 90, 135, 200, 315):
            self.assertAlmostEqual(area(deg) / base, 1.0, delta=0.08, msg=f"{deg} deg")

    def test_screen_angle_accounts_for_non_square_tiles(self):
        # World 45 deg = 1 tile right, 1 tile down = 20 px right, 24 px down.
        a = sprites.screen_angle(math.radians(45), 10, 24, 2)
        self.assertAlmostEqual(a, math.atan2(24, 20))


if __name__ == "__main__":
    unittest.main()
