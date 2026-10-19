"""M28.3a: rarity makes the power stronger, the legendary look, and the
gear screen's STATS page (design/GEAR.md 7-9, 18)."""

import math
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from ascii_adventurers import config
from ascii_adventurers.engine_ext import gamepads
from ascii_adventurers.players import gear
from ascii_adventurers.players.gear import Offer, Piece
from ascii_adventurers.systems import combat
from ascii_adventurers.tests.test_m28_1 import DrawTest, wearing
from ascii_adventurers.tests.test_m28_2a import foe, wear
from ascii_adventurers.tests.test_m16 import game
from ascii_adventurers.ui import frame, gear_picker, gear_screen, gear_stats


def stat(key, level, rarity, name):
    return [v for st, op, v in gear.power_steps(key, level, rarity) if st == name]


class RarityPowerTest(unittest.TestCase):
    def test_the_main_number_grows_by_rarity_and_level(self):
        for rarity, mult in config.GEAR_RARITY_POWER.items():
            self.assertAlmostEqual(stat("point_blank", 0, rarity, "point_blank")[0], 0.4 * mult)
        self.assertAlmostEqual(stat("point_blank", 9, "epic", "point_blank")[0], 0.4 * 1.9 * 1.5)
        self.assertEqual(stat("point_blank", 0, "common", "point_blank"), [0.4])   # (as before)

    def test_a_power_with_no_number_gets_damage(self):
        self.assertEqual(stat("phase_darts", 0, "common", "damage"), [])
        self.assertAlmostEqual(stat("phase_darts", 0, "legendary", "damage")[0],
                               (2.0 - 1) * config.GEAR_RARITY_FLAT)
        self.assertAlmostEqual(stat("phase_darts", 3, "uncommon", "damage")[0],
                               3 * config.GEAR_FLAT_GROWTH + 0.15 * config.GEAR_RARITY_FLAT)

    def test_spells_grow_their_number(self):
        self.assertAlmostEqual(gear.spell_boost("daggers", 0, "legendary"), 1.0)
        self.assertAlmostEqual(gear.spell_boost("daggers", 6, "epic"), 1.2 * 1.5 - 1)
        self.assertAlmostEqual(gear.spell_boost("ember_aura", 0, "legendary"), math.sqrt(2) - 1)
        self.assertEqual(gear.spell_boost("daggers", 4, "common"), 0.0)
        steps = gear.power_steps("daggers", 0, "rare")
        self.assertIn(("daggers", "spell_boost", 0.30000000000000004), steps)

    def test_a_shrinking_multiplier_has_a_floor(self):
        self.assertAlmostEqual(stat("focus", 9, "legendary", "spread_mult")[0], config.GEAR_MUL_FLOOR)
        self.assertAlmostEqual(stat("focus", 3, "rare", "spread_mult")[0], 1 - 0.3 * 1.3 * 1.3)

    def test_downsides_and_tricks_do_not_grow(self):
        self.assertEqual(stat("frenzy", 0, "legendary", "range"), [-0.2])
        flags = [st for st, op, v in gear.power_steps("frenzy", 6, "legendary") if op == "flag"]
        self.assertIn("frenzy+6", flags)

    def test_what_you_wear_counts_its_rarity(self):
        m, s = game("princess")
        wear(s, "point_blank", 0, "legendary")
        self.assertAlmostEqual(s.hero.stats.point_blank, 0.8)
        m, s = game("princess")
        wear(s, "point_blank", 0, "uncommon")
        self.assertAlmostEqual(s.hero.stats.point_blank, 0.46)

    def test_texts(self):
        self.assertIn("(power +100%)", gear.power_text("point_blank", 0, "legendary"))
        self.assertNotIn("power", gear.power_text("point_blank", 0, "common"))
        self.assertIn("+50% damage", gear.power_text("phase_darts", 0, "legendary"))
        self.assertIn("power +20%", gear.next_level_text("point_blank", 4, "legendary"))
        self.assertIn("+5% damage", gear.next_level_text("phase_darts", 4, "legendary"))
        self.assertIn("+100% damage", gear.power_text("daggers", 0, "legendary"))
        self.assertIn("+15% damage", gear.next_level_text("daggers", 5, "epic"))


class StatsPageTest(unittest.TestCase):
    def test_the_breakdown_matches_a_hit(self):
        for hero in ("wizard", "dwarf", "huntress", "princess", "bard"):
            m, s = game(hero)
            g = s.me.progress.gear
            g.take(Offer("kindling", "epic", ("sharpened", "elementalist", "brutal"), "new"))
            s._apply_loadout(s.me)
            h = s.hero
            spec = h.weapon.spec
            base = spec.damage if spec.kind == "pulse" else spec.shell.damage
            value, how = gear_stats.hit(h.stats, base, spec.tags)
            h.rng.random = lambda: 0.99
            dealt = combat.strike(foe(h.x + 30, h.y, 10 ** 6), base, h, 0.0, [], spec.tags,
                                  on_hit=False)
            self.assertAlmostEqual(dealt, value, places=4, msg=hero)
            text = " ".join(t for t, _ in gear_stats.damage_lines(h))
            self.assertIn(f"= {value:.1f}", text)
            self.assertIn("damage)", how)

    def test_spells_and_totals(self):
        m, s = game("wizard")
        g = s.me.progress.gear
        g.take(Offer("frost_nova", "rare", ("quick_hands",), "new"))
        g.take(Offer("ember_aura", "common", (), "new"))
        g.take(Offer("iron_skin" if "iron_skin" in config.GEAR else "thorn_mail", "rare", (), "new"))
        s._apply_loadout(s.me)
        text = [t for t, _ in gear_stats.damage_lines(s.hero)]
        self.assertTrue(any(t.startswith("Frost Nova I,") for t in text))
        self.assertTrue(any(t.startswith("Ember Aura I,") for t in text))
        totals = " ".join(t for t, _ in gear_stats.total_lines(s.hero))
        for word in ("max HP", "armor", "move", "attack speed", "crit", "area", "pickup", "rolls"):
            self.assertIn(word, totals)

    def test_i_flips_the_page(self):
        m, s = game("bard")
        s._open_gear()
        scr = s.overlay
        self.assertEqual(scr.page, "gear")
        key = lambda k: scr.handle_event(pygame.event.Event(pygame.KEYDOWN, key=k, unicode="", mod=0))
        key(pygame.K_i)
        self.assertEqual(scr.page, "stats")
        s.draw(m.text)
        key(pygame.K_DOWN)                            # (scrolls, doesn't move the focus)
        key(pygame.K_i)
        self.assertEqual(scr.page, "gear")
        # Not in the picker's sub-screens (no hero there).
        up = gear_screen.GearScreen(m, s.me.progress, "upgrade")
        up.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_i, unicode="", mod=0))
        self.assertEqual(up.page, "gear")

    def test_pad_y_is_i_in_menus(self):
        if gamepads.BUTTON_Y != -1:
            self.assertEqual(gamepads.BUTTON_KEYS[gamepads.BUTTON_Y], pygame.K_i)


class FitTest(DrawTest):
    def test_stats_page_fits_every_screen(self):
        from ascii_adventurers.players.progress import Progress
        m, s = game("wizard")
        g = s.me.progress.gear
        for key in ("daggers", "frost_nova", "ember_aura", "poison_flask"):
            g.take(Offer(key, "epic", ("quick_hands", "broad_strokes"), "new"))
        g.take(Offer("kindling", "rare", ("sharpened", "potency"), "new"))
        s._apply_loadout(s.me)
        prog = s.me.progress
        for rows in (24, 30):
            def make(m2):
                scr = gear_screen.GearScreen(m2, prog, "browse", hero=s.hero)
                scr.page = "stats"
                return scr
            for text in self.fits(make, rows=rows):
                self.assertIn("DAMAGE", text)

    def test_legendary_glint(self):
        from ascii_adventurers.players.progress import Progress
        prog = Progress(picks=1)
        prog.offer = [Offer("cyclone", "legendary", ("sharpened",), "new"),
                      Offer("kindling", "rare", (), "new")]
        for text in self.fits(lambda m: gear_picker.GearPicker(m, prog, lambda a: None)):
            self.assertIn("*", text)
        prog = Progress()
        prog.gear = wearing(Piece("cyclone", "legendary", 2))
        for text in self.fits(lambda m: gear_screen.GearScreen(m, prog, "browse"), rows=24):
            self.assertIn("*", text)
        calls = []

        class Rec:
            def put(self, col, row, s, fg, bg=None):
                calls.append((col, row, s, fg))
        for t in (0.0, 0.5, 1.0):
            calls.clear()
            frame.glint(Rec(), 0, 0, 10, 5, None, t)
            spark = [c for c in calls if c[3] == frame.palette.LEGEND_GLINT[0]]
            self.assertEqual(len(spark), 1)


if __name__ == "__main__":
    unittest.main()
