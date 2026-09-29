import unittest

from ascii_adventurers import config
from ascii_adventurers.engine_ext.camera import Camera


class CameraTest(unittest.TestCase):
    def setUp(self):
        # Ultrawide viewport minus a 3-row HUD, 10x24 px cells.
        self.cam = Camera(172, 27, 10, 24)
        self._rate = config.CAMERA_FOLLOW_RATE

    def tearDown(self):
        config.CAMERA_FOLLOW_RATE = self._rate

    def test_centered_point_is_at_viewport_center(self):
        for x, y in [(0.0, 0.0), (70.3, 34.9), (-12.77, 5.5), (1000.49, -3.01)]:
            self.cam.center_on(x, y)
            px, py = self.cam.world_to_px(x, y)
            self.assertAlmostEqual(px, self.cam.view_w / 2, delta=0.5)
            self.assertAlmostEqual(py, self.cam.view_h / 2, delta=0.5)

    def test_canvas_to_world_inverts_world_to_px(self):
        self.cam.center_on(70.3, 34.9)
        for px, py in [(0.0, 0.0), (805.5, 311.2), (1719.9, 647.9), (43.0, 600.0)]:
            wx, wy = self.cam.canvas_to_world(px, py)
            bx, by = self.cam.world_to_px(wx, wy)
            self.assertAlmostEqual(bx, px, places=6)
            self.assertAlmostEqual(by, py, places=6)

    def test_scrolls_one_pixel_at_a_time_vertically(self):
        # The old cell camera could only move 24 px per step vertically.
        # Moving the target by one pixel's worth must move the view 1 px.
        self.cam.center_on(10.0, 10.0)
        _, oy0 = self.cam.origin_px
        self.cam.center_on(10.0, 10.0 + 1 / 24)
        _, oy1 = self.cam.origin_px
        self.assertEqual(oy1 - oy0, 1)

    def test_origin_is_whole_pixels(self):
        self.cam.center_on(3.3333, 7.777)
        self.assertTrue(all(isinstance(v, int) for v in self.cam.origin_px))

    def test_follow_eases_and_is_frame_rate_independent(self):
        config.CAMERA_FOLLOW_RATE = 8.0
        a, b = Camera(172, 27, 10, 24), Camera(172, 27, 10, 24)
        for _ in range(30):            # 0.5 s at 60 fps
            a.follow(2.0, 0.0, 1 / 60)
        for _ in range(15):            # 0.5 s at 30 fps
            b.follow(2.0, 0.0, 1 / 30)
        self.assertGreater(a.x, 0.0)
        self.assertLess(a.x, 2.0)      # eased, not snapped
        self.assertAlmostEqual(a.x, b.x, places=6)

    def test_follow_never_lags_too_far(self):
        config.CAMERA_FOLLOW_RATE = 0.5
        self.cam.center_on(0.0, 0.0)
        self.cam.follow(100.0, 0.0, 1 / 60)
        self.assertGreaterEqual(self.cam.x, 100.0 - config.CAMERA_MAX_LAG_TILES)

    def test_zero_rate_locks_on(self):
        config.CAMERA_FOLLOW_RATE = 0
        self.cam.follow(12.5, 7.25, 1 / 60)
        self.assertEqual((self.cam.x, self.cam.y), (12.5, 7.25))

    def test_visible_tiles_cover_viewport(self):
        self.cam.center_on(50.25, 20.4)
        tx0, ty0, tx1, ty1 = self.cam.visible_tiles()
        x0, y0 = self.cam.tile_to_px(tx0, ty0)
        x1, y1 = self.cam.tile_to_px(tx1 + 1, ty1 + 1)
        self.assertLessEqual((x0, y0), (0, 0))
        self.assertGreaterEqual(x1, self.cam.view_w)
        self.assertGreaterEqual(y1, self.cam.view_h)


if __name__ == "__main__":
    unittest.main()
