"""M24.5: the Snow King glides round his hall and Fragile circles you,
between moves and (slower) during most of them, instead of standing
still."""

import math
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.tests import test_m24_2, test_m24_3


def watch(f, seconds):
    """Run the fight with no moves; the boss's distance from the hero each
    step, and how far round the hero it went (radians, either way)."""
    dists, turned = [], 0.0
    a0 = math.atan2(f.b.y - f.h.y, f.b.x - f.h.x)
    for _ in range(round(seconds * 60)):
        f.b.think(f.ctx(), 1 / 60)
        dists.append(math.hypot(f.b.x - f.h.x, f.b.y - f.h.y))
        a = math.atan2(f.b.y - f.h.y, f.b.x - f.h.x)
        turned += abs((a - a0 + math.pi) % math.tau - math.pi)   # (either way round)
        a0 = a
    return dists, turned


class SnowGlideTest(unittest.TestCase):
    def test_he_glides_round_you_between_moves(self):
        f = test_m24_2.Fight(hx=70.0, hy=22.0, bx=60.0, by=22.0)
        dists, turned = watch(f, 10.0)
        self.assertGreater(f.b.walked, 25.0)              # he keeps moving
        self.assertGreater(turned, 1.0)                   # round you, not just away
        late = dists[180:]
        near, far = config.SNOW_GLIDE[1], config.SNOW_GLIDE[2]
        self.assertGreater(min(late), near - 3.0)
        self.assertLess(max(late), far + 3.0)
        self.assertTrue(f.lair.inside(f.b.x, f.b.y))

    def test_he_stays_off_walls_and_leaves_frost(self):
        walls = [(x, 14) for x in range(40, 100)]
        f = test_m24_2.Fight(hx=70.0, hy=22.0, bx=60.0, by=20.0, walls=walls)
        for _ in range(600):
            f.b.think(f.ctx(), 1 / 60)
            self.assertFalse(f.b._solid(f.b.x, f.b.y))
        self.assertTrue(f.b.trail)
        self.assertTrue(all(age < config.SNOW_TRAIL[1] for _, _, age in f.b.trail))

    def test_his_ice_speeds_him_up(self):
        f = test_m24_2.Fight(hx=70.0, hy=22.0, bx=60.0, by=22.0)
        f.run(0.5)
        start = f.b.walked
        f.run(1.0)
        dry = f.b.walked - start
        f.b.sheets = [{"x": f.b.x, "y": f.b.y, "age": 10.0, "r": 60.0}]
        f.b.on_ice = lambda x, y: True
        start = f.b.walked
        f.run(1.0)
        self.assertGreater(f.b.walked - start, dry * 1.3)

    def test_he_stands_still_while_crownless_dazed_or_in_a_move(self):
        f = test_m24_2.Fight(hx=70.0, hy=22.0, bx=60.0, by=22.0)
        f.b.dazed = 2.0
        x, y = f.b.x, f.b.y
        f.run(1.0)
        self.assertEqual((f.b.x, f.b.y), (x, y))

    def test_he_casts_on_the_move_and_walks_his_breath_at_you(self):
        f = test_m24_2.Fight(hx=75.0, hy=22.0, bx=60.0, by=22.0)
        f.b._rest = 0.0
        f.b._pick_move = lambda: "shards"
        x, y = f.b.x, f.b.y
        for _ in range(30):
            f.b.think(f.ctx(), 1 / 60)
        self.assertEqual(f.b.move, "shards")
        self.assertGreater(math.hypot(f.b.x - x, f.b.y - y), 0.5)   # gliding while he casts
        f = test_m24_2.Fight(hx=80.0, hy=22.0, bx=60.0, by=22.0)
        f.b._rest = 0.0
        f.b._pick_move = lambda: "breath"
        d0 = math.hypot(f.h.x - f.b.x, f.h.y - f.b.y)
        for _ in range(60):
            f.b.think(f.ctx(), 1 / 60)
        self.assertEqual(f.b.move, "breath")
        d1 = math.hypot(f.h.x - f.b.x, f.h.y - f.b.y)
        self.assertAlmostEqual(d0 - d1, config.SNOW_ADVANCE[0], delta=0.3)   # straight at you


class FragileCircleTest(unittest.TestCase):
    def test_she_casts_on_the_move_but_holds_still_to_gaze(self):
        f = test_m24_3.Fight(hx=70.0, hy=22.0, bx=60.0, by=22.0)
        f.b._rest = 0.0
        f.b._pick_move = lambda: "petals"
        x, y = f.b.x, f.b.y
        for _ in range(30):
            f.b.think(f.ctx(), 1 / 60)
        self.assertEqual(f.b.move, "petals")
        self.assertGreater(math.hypot(f.b.x - x, f.b.y - y), 0.5)
        f = test_m24_3.Fight(hx=70.0, hy=22.0, bx=60.0, by=22.0)
        f.b._rest = 0.0
        f.b._pick_move = lambda: "gaze"
        f.b.think(f.ctx(), 1 / 60)
        x, y = f.b.x, f.b.y
        for _ in range(30):
            f.b.think(f.ctx(), 1 / 60)
        self.assertEqual(f.b.move, "gaze")
        self.assertEqual((f.b.x, f.b.y), (x, y))

    def test_she_circles_you_between_moves(self):
        f = test_m24_3.Fight(hx=70.0, hy=22.0, bx=60.0, by=22.0)
        dists, turned = watch(f, 10.0)
        self.assertGreater(f.b.walked, 25.0)
        self.assertGreater(turned, 1.5)
        near, far = config.FRAGILE_CIRCLE[0], config.FRAGILE_CIRCLE[1]
        late = dists[180:]
        self.assertGreater(min(late), near - 3.0)
        self.assertLess(max(late), far + 3.0)

    def test_she_keeps_out_of_the_sun_while_circling(self):
        f = test_m24_3.Fight(hx=40.5, hy=20.0, bx=30.0, by=20.0)
        f.b.open[0] = 60.0                                 # the shaft down from (41, 1)
        for _ in range(600):
            f.b.think(f.ctx(), 1 / 60)
            self.assertFalse(f.b.in_sun(f.b.x, f.b.y, 0.0) and f.b.dazed <= 0)

    def test_she_turns_about_now_and_then(self):
        f = test_m24_3.Fight(hx=70.0, hy=22.0, bx=60.0, by=22.0)
        seen = set()
        for _ in range(60 * 20):
            f.b.think(f.ctx(), 1 / 60)
            seen.add(f.b.circle_dir)
        self.assertEqual(seen, {1, -1})


if __name__ == "__main__":
    unittest.main()
