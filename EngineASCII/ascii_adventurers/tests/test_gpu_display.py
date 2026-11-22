"""The approved engine change of 2026-11-22: Display's GPU path (sharp
bilinear scaling on the graphics chip) and its fallbacks to the CPU path.
The tests run headless, so the GPU side is faked: a window, a renderer that
logs what is drawn where, and textures."""

import os
import unittest
from unittest import mock

import pygame

from engine import Display, DisplayMode


class FakeWindow:
    made: list = []

    def __init__(self, title="", size=(640, 480), position=None, **kw):
        self.title, self.size, self.position, self.kw = title, tuple(size), position, kw
        self.destroyed = False
        FakeWindow.made.append(self)

    def destroy(self):
        self.destroyed = True


class FakeRenderer:
    wait = 0.0          # how long a present takes (0: vsync ignored)

    def __init__(self, window, accelerated=-1, vsync=False):
        self.window, self.accelerated, self.vsync = window, accelerated, vsync
        self.target = None
        self.draw_color = (0, 0, 0, 255)
        self.log = []

    def get_viewport(self):
        return pygame.Rect(0, 0, *self.window.size)

    def clear(self):
        self.log.append(("clear", self.target))

    def present(self):
        self.log.append(("present",))
        if FakeRenderer.wait:
            import time
            time.sleep(FakeRenderer.wait)


class FakeTexture:
    def __init__(self, renderer, size, streaming=False, target=False, **kw):
        self.renderer, self.width, self.height = renderer, *size
        self.target = target
        self.filter = os.environ.get("SDL_RENDER_SCALE_QUALITY")
        self.uploads = 0

    def update(self, surface):
        self.uploads += 1

    def draw(self, dstrect=None):
        self.renderer.log.append(("draw", self, self.renderer.target, tuple(dstrect)))


class _GPU(unittest.TestCase):
    """A Display on the faked GPU path, as if a real video driver were up."""

    def setUp(self):
        FakeWindow.made = []
        FakeRenderer.wait = 0.0
        self.patches = [mock.patch("pygame.display.get_driver", return_value="x11"),
                        mock.patch("pygame.Window", FakeWindow),
                        mock.patch("pygame._sdl2.video.Renderer", FakeRenderer),
                        mock.patch("pygame._sdl2.video.Texture", FakeTexture)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()

    def draws(self, d):
        return [e for e in d._renderer.log if e[0] == "draw"]


class FallbackTest(unittest.TestCase):
    def test_headless_drivers_keep_the_cpu_path(self):
        d = Display(20, 5)
        self.assertFalse(d.gpu)
        self.assertEqual(d.window_size(), d.canvas.get_size())
        d.present()                                     # (and it draws)

    def test_gpu_false_keeps_the_cpu_path(self):
        with mock.patch("pygame.display.get_driver", return_value="x11"), \
                mock.patch("pygame.Window", side_effect=AssertionError("no GPU window")):
            self.assertFalse(Display(20, 5, gpu=False).gpu)


class GPUPathTest(_GPU):
    def test_opens_a_gpu_window_with_a_hardware_renderer(self):
        d = Display(20, 5, vsync=True)
        self.assertTrue(d.gpu)
        self.assertIsNone(d._screen)
        self.assertEqual(d._renderer.accelerated, 1)    # never SDL's software renderer
        self.assertTrue(d._renderer.vsync)
        self.assertEqual(d.window_size(), d.canvas.get_size())

    def test_no_hardware_renderer_falls_back_for_good(self):
        with mock.patch("pygame._sdl2.video.Renderer", side_effect=pygame.error("no accel")):
            d = Display(20, 5)
        self.assertFalse(d.gpu)
        self.assertTrue(FakeWindow.made[0].destroyed)   # the GPU window went away
        self.assertIsNotNone(d._screen)
        d.set_mode(DisplayMode.BORDERLESS)              # mode changes don't try again
        d.set_mode(DisplayMode.WINDOWED)
        self.assertEqual(len(FakeWindow.made), 1)
        self.assertFalse(d.gpu)
        d.present()

    def test_modes_make_the_matching_window(self):
        d = Display(20, 5)
        desktop = pygame.display.get_desktop_sizes()[0]
        d.set_mode(DisplayMode.BORDERLESS)
        self.assertEqual(FakeWindow.made[-1].size, desktop)
        self.assertTrue(FakeWindow.made[-1].kw.get("borderless"))
        d.set_mode(DisplayMode.FULLSCREEN)
        self.assertTrue(FakeWindow.made[-1].kw.get("fullscreen"))
        d.set_mode(DisplayMode.WINDOWED)
        self.assertTrue(FakeWindow.made[-1].kw.get("resizable"))
        self.assertTrue(all(w.destroyed for w in FakeWindow.made[:-1]))

    def test_whole_number_scales_are_plain_nearest(self):
        d = Display(20, 5)
        cw, ch = d.canvas.get_size()
        d._window.size = (cw * 2, ch * 2)
        d.present()
        (draw,) = self.draws(d)
        tex = draw[1]
        self.assertEqual(tex.filter, "nearest")
        self.assertIsNone(draw[2])                       # straight to the window
        self.assertEqual(draw[3], (0, 0, cw * 2, ch * 2))
        self.assertIsNone(d._big)

    def test_a_fractional_scale_is_sharp_bilinear(self):
        d = Display(20, 5)
        cw, ch = d.canvas.get_size()
        d._window.size = (cw * 3 // 2, ch * 3 // 2 + 40)   # 1.5x, with bars top and bottom
        d.present()
        up, down = self.draws(d)
        self.assertEqual(up[1].filter, "nearest")         # the canvas, 2x into the target...
        self.assertIs(up[2], d._big)
        self.assertEqual(up[3], (0, 0, cw * 2, ch * 2))
        self.assertEqual((d._big.width, d._big.height), (cw * 2, ch * 2))
        self.assertEqual(d._big.filter, "linear")         # ...smoothed down to the window
        self.assertIs(down[1], d._big)
        self.assertIsNone(down[2])
        self.assertEqual(down[3], (0, 20, cw * 3 // 2, ch * 3 // 2))
        self.assertNotIn("SDL_RENDER_SCALE_QUALITY", os.environ)   # (put back)
        # The mouse maps through the same fit.
        self.assertEqual(d.window_to_cell(0, 19), None)
        self.assertEqual(d.window_to_cell(0, 20), (0, 0))
        self.assertEqual(d.window_to_cell(cw * 3 // 2 - 1, 20 + ch * 3 // 2 - 1), (19, 4))

    def test_textures_are_kept_and_made_again_when_needed(self):
        d = Display(20, 5)
        cw, ch = d.canvas.get_size()
        d._window.size = (cw * 3 // 2, ch * 3 // 2)
        d.present()
        tex, big = d._tex, d._big
        d.present()
        self.assertIs(d._tex, tex)
        self.assertIs(d._big, big)
        self.assertEqual(tex.uploads, 2)                  # the canvas goes up every frame
        d.set_grid(30, 5)                                 # a new canvas size: new textures
        d._window.size = (d.canvas.get_width() * 3 // 2, ch * 3 // 2)
        d.present()
        self.assertEqual(d._tex.width, d.canvas.get_width())
        d.handle_event(pygame.event.Event(pygame.RENDER_DEVICE_RESET))
        self.assertIsNone(d._tex)
        d.present()
        self.assertIsNotNone(d._tex)

    def test_ignored_vsync_is_reported_so_the_loop_caps_itself(self):
        self.assertFalse(Display(20, 5, vsync=True).vsync)   # presents came back at once
        FakeRenderer.wait = 0.004
        self.assertTrue(Display(20, 5, vsync=True).vsync)

    def test_a_gpu_failure_mid_game_moves_to_the_cpu_path(self):
        d = Display(20, 5)
        d.present()
        with mock.patch.object(FakeTexture, "update", side_effect=pygame.error("device lost")):
            d.present()
        self.assertFalse(d.gpu)
        self.assertIsNotNone(d._screen)
        self.assertTrue(FakeWindow.made[0].destroyed)
        d.present()                                       # (the CPU path draws)


if __name__ == "__main__":
    unittest.main()
