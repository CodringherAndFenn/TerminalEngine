"""P3 (playtest pass, 2026-10-10): hero pace. The pickup radius is 2.5x
(1.5 -> 3.75 tiles) and the hero gets +1% move speed per level, up to +20%."""

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.players import cards
from ascii_adventurers.players.stats import HeroStats
from ascii_adventurers.tests.test_m17 import game, step


class PickupTest(unittest.TestCase):
    def test_the_base_radius_is_two_and_a_half_times_bigger(self):
        self.assertEqual(config.PICKUP_RADIUS, 3.75)
        self.assertEqual(HeroStats().pickup_radius, 3.75)

    def test_magnet_still_adds_its_share_on_top(self):
        lo = cards.build_loadout("wizard", [("magnet", "common")])
        self.assertAlmostEqual(lo.stats.pickup_radius, 3.75 * 1.20)


class LevelSpeedTest(unittest.TestCase):
    def test_one_percent_a_level_up_to_twenty(self):
        self.assertEqual(cards.level_speed(1), 0.0)
        self.assertAlmostEqual(cards.level_speed(2), 0.01)
        self.assertAlmostEqual(cards.level_speed(12), 0.11)
        self.assertAlmostEqual(cards.level_speed(21), 0.20)
        self.assertAlmostEqual(cards.level_speed(60), 0.20)            # the cap

    def test_it_adds_to_swift_boots(self):
        base = config.HEROES["wizard"].max_speed
        lo = cards.build_loadout("wizard", [("swift_boots", "common")], level=12)
        self.assertAlmostEqual(lo.body.max_speed, base * (1 + 0.05 + 0.11))
        self.assertAlmostEqual(cards.build_loadout("wizard", []).body.max_speed, base)

    def test_the_hero_speeds_up_when_it_levels(self):
        m, s = game()
        p = s.me
        base = config.HEROES["wizard"].max_speed
        self.assertAlmostEqual(s.hero.spec.max_speed, base)
        prog = p.progress
        while prog.level < 12:
            prog.add(prog.needed - prog.xp)
        step(s)                                     # (no card picked: it still applies)
        self.assertEqual(p.loadout_level, 12)
        self.assertAlmostEqual(s.hero.spec.max_speed, base * 1.11)

    def test_a_card_pick_keeps_the_level_speed(self):
        m, s = game()
        p = s.me
        base = config.HEROES["wizard"].max_speed
        prog = p.progress
        prog.add(prog.needed - prog.xp)             # level 2: a pick
        step(s)
        self.assertTrue(prog.offer)
        s._cards(p, 0)                              # (the rebuild for the card)
        no_level = cards.build_loadout("wizard", prog.taken, p.meta)
        self.assertAlmostEqual(s.hero.stats.move, no_level.stats.move + 0.01)
        self.assertAlmostEqual(s.hero.spec.max_speed, base * (1 + s.hero.stats.move))


if __name__ == "__main__":
    unittest.main()
