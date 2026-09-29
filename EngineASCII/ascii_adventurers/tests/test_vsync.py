import unittest
from unittest import mock

import pygame

from engine import Display, DisplayMode


class VsyncTest(unittest.TestCase):
    """The approved engine hook: Display(vsync=...) with safe fallback."""

    def test_off_by_default(self):
        self.assertFalse(Display(20, 5).vsync)

    def test_falls_back_when_refused(self):
        real = pygame.display.set_mode

        def refuse_vsync(*args, vsync=0, **kwargs):
            if vsync:
                raise pygame.error("vsync not supported")
            return real(*args, **kwargs)

        with mock.patch("pygame.display.set_mode", side_effect=refuse_vsync):
            d = Display(20, 5, vsync=True)
            self.assertFalse(d.vsync)                  # fell back, window opened
            d.set_mode(DisplayMode.BORDERLESS)         # rebuilds keep working
            d.set_mode(DisplayMode.WINDOWED)
            self.assertFalse(d.vsync)

    def test_granted_vsync_is_reported(self):
        real = pygame.display.set_mode

        def accept(*args, vsync=0, **kwargs):
            return real(*args, **kwargs)

        with mock.patch("pygame.display.set_mode", side_effect=accept) as sm:
            d = Display(20, 5, vsync=True)
            self.assertTrue(d.vsync)
            self.assertEqual(sm.call_args.kwargs["vsync"], 1)


if __name__ == "__main__":
    unittest.main()
