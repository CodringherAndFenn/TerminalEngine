import unittest

from ascii_adventurers import config
from ascii_adventurers.engine_ext.screen import fitted_cols


class FittedColsTest(unittest.TestCase):
    def test_common_screens_fill_without_bars(self):
        rows, cw, ch = config.GRID_ROWS, 10, 24
        for (w, h), want in {
            (1920, 1080): 128,   # 16:9 laptop / monitor
            (3440, 1440): 172,   # 21:9 ultrawide (matches the old preset)
            (2560, 1440): 128,
            (1920, 1200): 115,   # 16:10
        }.items():
            cols = fitted_cols(w, h, rows, cw, ch)
            self.assertEqual(cols, want, (w, h))
            # Leftover bar thinner than one cell after scaling to the screen.
            scale = h / (rows * ch)
            self.assertLess(abs(w - cols * cw * scale), cw * scale, (w, h))

    def test_never_narrower_than_minimum(self):
        self.assertEqual(fitted_cols(600, 1000, config.GRID_ROWS, 10, 24), config.MIN_GRID_COLS)


if __name__ == "__main__":
    unittest.main()
