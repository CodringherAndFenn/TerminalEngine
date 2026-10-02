"""M19: multiple projectiles for every hero -- fans, pattern cards, Sheet
Music, Split Arrow, Double Rainbow, Twin Axes, Multishot on spells."""

import math
import os
import unittest
from collections import Counter

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from ascii_adventurers import config
from ascii_adventurers.players import cards
from ascii_adventurers.systems import combat
from ascii_adventurers.tests.test_m14 import carded
from ascii_adventurers.tests.test_m16 import SpellRev2Test, fly, game, take
from ascii_adventurers.tests.test_weapons import Dummy, open_map


def angles(shots):
    return sorted(round(math.degrees(p.angle), 3) for p in shots)


def weapon(hero):
    return config.WEAPONS[config.HEROES[hero].weapon]


class _GameCase(unittest.TestCase):
    def tearDown(self):
        if pygame.display.get_init():
            pygame.mouse.set_visible(True)

    def attack(self, hero, *taken, times=1, clear=True):
        m, s = game(hero)
        take(s, *taken)
        s.enemies.clear()
        s.hero.aim_angle = 0.0
        return s, self.again(s, times, clear)

    def again(self, s, times=1, clear=True):
        if clear:
            s.projectiles.clear()
        for _ in range(times):
            s._attack(s.me)
        return [p for p in s.projectiles if p.owner is s.hero]


class FanTest(unittest.TestCase):
    def test_extra_projectiles_fan_out(self):
        h = carded("wizard", ("multishot", "rare"))
        shots = []
        combat.fire(h, open_map(), shots, [])
        a = angles(shots)
        self.assertEqual(len(a), 2)
        self.assertAlmostEqual(a[1] - a[0], config.MIN_PELLET_GAP)

    def test_a_weapons_own_fan_is_kept(self):
        lo = cards.build_loadout("princess", [])
        self.assertEqual(lo.weapon.spread_deg, weapon("princess").spread_deg)
        lo = cards.build_loadout("princess", [("multishot", "rare")])
        self.assertEqual(lo.weapon.spread_deg, weapon("princess").spread_deg + config.MIN_PELLET_GAP)

    def test_per_attack_pellets_fan_too(self):
        h = carded("huntress")
        shots = []
        combat.fire(h, open_map(), shots, [], extra_pellets=4, spread_add=4.0)
        a = angles(shots)
        self.assertGreaterEqual(min(b - c for b, c in zip(a[1:], a)), config.MIN_PELLET_GAP - 1e-6)


class PatternTest(_GameCase):
    def test_echo_repeat_is_turned(self):
        s, _ = self.attack("huntress", ("echo", "uncommon"))
        kw = s.rules.attack_mods(s.me, echo=True)
        self.assertAlmostEqual(abs(kw["angle_offset"]), math.radians(config.ECHO_ANGLE))

    def test_cross_fire(self):
        s, shots = self.attack("huntress", ("cross_fire", "uncommon"),
                               times=config.CROSS_FIRE_EVERY)
        self.assertEqual(len(shots), config.CROSS_FIRE_EVERY + 3)
        dirs = {round(math.degrees(p.angle)) % 360 for p in shots}
        self.assertEqual(dirs, {0, 90, 180, 270})

    def test_starburst(self):
        s, shots = self.attack("huntress", ("starburst", "rare"), times=config.STARBURST[0])
        self.assertEqual(len(shots), config.STARBURST[0] + config.STARBURST[1])

    def test_rear_guard(self):
        s, shots = self.attack("huntress", ("rear_guard", "uncommon"))
        back = [p for p in shots if math.cos(p.angle) < -0.99]
        self.assertEqual(len(back), 1)
        self.assertAlmostEqual(back[0].mult, config.REAR_GUARD)

    def test_spiral_turns(self):
        s, first = self.attack("huntress", ("spiral", "uncommon"))
        second = self.again(s)
        extra = lambda shots: [p.angle for p in shots if abs(p.angle) > 1e-6][0]
        self.assertAlmostEqual(extra(second) - extra(first), math.radians(config.SPIRAL_STEP))

    def test_twin_lanes(self):
        s, shots = self.attack("huntress", ("twin_lanes", "rare"))
        self.assertEqual(len(shots), 2)
        self.assertAlmostEqual(abs(shots[0].y - shots[1].y), config.TWIN_LANES[0])
        self.assertTrue(all(p.mult == config.TWIN_LANES[1] for p in shots))

    def test_patterns_follow_the_weapon(self):
        """The rainbow's Cross Fire goes off as whole fans; the axe's come home."""
        s, shots = self.attack("princess", ("cross_fire", "uncommon"),
                               times=config.CROSS_FIRE_EVERY)
        self.assertEqual(len(shots), 5 * (config.CROSS_FIRE_EVERY + 3))
        s, shots = self.attack("dwarf", ("rear_guard", "uncommon"))
        self.assertTrue(all(p.spec.returns for p in shots))


class HeroCardTest(_GameCase):
    def test_sheet_music_notes_at_the_nearest(self):
        from ascii_adventurers.tests.test_players import make
        m, s = game("bard")
        take(s, ("sheet_music", "uncommon"))
        h = s.hero
        s.enemies[:] = [make("goblin_archer", h.x + 5, h.y), make("goblin_archer", h.x, h.y + 6)]
        for e in s.enemies:
            e.hp = e.max_hp = 5000
        s.projectiles.clear()
        s._attack(s.me)
        notes = [p for p in s.projectiles if p.spec.look == "note"]
        self.assertEqual(len(notes), config.SHEET_MUSIC)
        self.assertIn(0.0, [round(p.angle, 6) for p in notes])               # at the first
        self.assertIn(round(math.pi / 2, 6), [round(p.angle, 6) for p in notes])
        take(s, ("multishot", "rare"))
        s.projectiles.clear()
        s._attack(s.me)
        self.assertEqual(sum(p.spec.look == "note" for p in s.projectiles), config.SHEET_MUSIC + 1)

    def test_bard_patterns_need_sheet_music(self):
        w = weapon("bard")
        self.assertNotIn("cross_fire", cards.eligible("bard", w, Counter()))
        st = cards.hero_stats([("sheet_music", "uncommon")])
        pool = cards.eligible("bard", w, Counter(), st)
        self.assertIn("cross_fire", pool)
        self.assertIn("multishot", pool)
        st = cards.hero_stats([("fire_wand", "uncommon")])
        pool = cards.eligible("bard", w, Counter(), st)
        self.assertIn("multishot", pool)               # wand bolts
        self.assertNotIn("cross_fire", pool)           # but the beat doesn't shoot

    def test_double_rainbow(self):
        s, shots = self.attack("princess", ("double_rainbow", "rare"),
                               times=config.DOUBLE_RAINBOW[0])
        late = [p for p in shots if p.hold > 0]
        self.assertEqual(len(late), 5)
        self.assertEqual(len(shots), 5 * config.DOUBLE_RAINBOW[0] + 5)

    def test_twin_axes(self):
        s, shots = self.attack("dwarf", ("twin_axes", "rare"), times=config.TWIN_AXES[0],
                               clear=True)
        last = shots[-2:]
        self.assertEqual(len(shots), config.TWIN_AXES[0] + 1)
        self.assertGreaterEqual(abs(math.degrees(last[0].angle - last[1].angle)),
                                config.TWIN_AXES[1] - 1e-6)

    def test_split_arrow_is_her_spell(self):
        c = config.CARDS["split_arrow"]
        self.assertEqual(c.heroes, ("huntress",))
        self.assertEqual(cards.spell_of(c), "split_arrow")
        self.assertNotIn("split_arrow", cards.eligible("wizard", weapon("wizard"), Counter()))

    def test_split_arrow_splits_on_the_first_hit(self):
        h = carded("huntress", ("split_arrow", "uncommon"))
        a, b = Dummy(16, 10.5, hp=5000), Dummy(19, 10.5, hp=5000)
        shots = []
        combat.fire(h, open_map(), shots, [])
        fly(shots, [h, a, b], steps=6)
        kids = [p for p in shots if p.child]
        self.assertEqual(len(kids), 3)
        self.assertAlmostEqual(kids[0].damage, weapon("huntress").shell.damage * 0.5)
        # Level IV: every enemy passed splits it again.
        h = carded("huntress", *[("split_arrow", "uncommon")] * 4)
        a, b = Dummy(16, 10.5, hp=5000), Dummy(19, 10.5, hp=5000)
        shots = []
        combat.fire(h, open_map(), shots, [])
        fly(shots, [h, a, b], steps=12)
        self.assertGreaterEqual(sum(p.child for p in shots), 2 * 4)


class SpellMultishotTest(unittest.TestCase):
    run_spell = SpellRev2Test.run_spell

    def test_wand_fires_more_bolts(self):
        h = carded("bard", ("multishot", "rare"))
        d = Dummy(16, 10.5, hp=5000)
        s, shots, _ = self.run_spell(h, "fire_wand", [h, d], 0.62)
        self.assertEqual(len(shots), 2)
        self.assertAlmostEqual(abs(shots[0].angle - shots[1].angle),
                               math.radians(config.MIN_PELLET_GAP))


if __name__ == "__main__":
    unittest.main()
