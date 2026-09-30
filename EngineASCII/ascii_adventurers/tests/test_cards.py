import math
import os
import unittest
from collections import Counter

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from ascii_adventurers import config
from ascii_adventurers.players import cards
from ascii_adventurers.ui import card_picker

STATS = {"damage", "interval", "range", "pellets", "spread", "pierce", "chain", "chain_range",
         "chain_falloff", "shot_speed", "arc", "max_hp", "move", "regen", "lifesteal"}


def weapon_of(hero):
    return config.WEAPONS[config.HEROES[hero].weapon]


class CardDataTest(unittest.TestCase):
    def test_every_card_is_well_formed_and_fits_the_tray(self):
        for key, c in config.CARDS.items():
            self.assertIn(c.rarity, config.CARD_RARITY_WEIGHT, key)
            self.assertTrue(set(c.heroes) <= set(config.HEROES), key)
            self.assertTrue(set(c.kinds) <= {"shot", "melee", "pulse"}, key)
            self.assertGreater(c.max_stacks, 0, key)
            for stat, op, _ in c.mods:
                self.assertIn(stat, STATS, key)
                self.assertIn(op, ("add", "mul"), key)
            # Fits the narrowest card (3 cards on an 80-column screen).
            narrow = (80 - 4 - 2 * card_picker.GAP) // 3 - 4
            self.assertEqual(" ".join(card_picker.wrap(c.text, narrow)), c.text, key)   # nothing cut
            self.assertLessEqual(len(c.name), narrow, key)

    def test_every_hero_has_cards_of_their_own(self):
        for hero in config.HEROES:
            own = [k for k, c in config.CARDS.items() if hero in c.heroes]
            self.assertTrue(own, hero)


class EligibilityTest(unittest.TestCase):
    def test_hero_and_weapon_restrictions(self):
        knight = cards.eligible("knight", weapon_of("knight"), Counter())
        self.assertIn("whirlwind", knight)
        self.assertNotIn("piercing", knight)          # swords don't shoot
        self.assertNotIn("storm_caller", knight)      # the wizard's
        wizard = cards.eligible("wizard", weapon_of("wizard"), Counter())
        self.assertIn("storm_caller", wizard)
        self.assertIn("piercing", wizard)
        self.assertNotIn("prism", wizard)

    def test_maxed_cards_are_not_offered(self):
        taken = Counter(sharpened=config.CARDS["sharpened"].max_stacks)
        self.assertNotIn("sharpened", cards.eligible("bard", weapon_of("bard"), taken))


class OfferTest(unittest.TestCase):
    def test_three_different_cards_same_every_time(self):
        a = cards.draw_offer("huntress", weapon_of("huntress"), Counter(), 99, 0, 5)
        b = cards.draw_offer("huntress", weapon_of("huntress"), Counter(), 99, 0, 5)
        self.assertEqual(a, b)
        self.assertEqual(len(a), config.CARD_OFFER_SIZE)
        self.assertEqual(len(set(a)), len(a))
        other = [cards.draw_offer("huntress", weapon_of("huntress"), Counter(), 99, 0, n)
                 for n in range(20)]
        self.assertGreater(len({tuple(o) for o in other}), 5)   # offers vary

    def test_rarity_weights(self):
        seen = Counter()
        for n in range(600):
            for k in cards.draw_offer("wizard", weapon_of("wizard"), Counter(), 7, 0, n):
                seen[config.CARDS[k].rarity] += 1
        self.assertGreater(seen["common"], seen["rare"])


class LoadoutTest(unittest.TestCase):
    def test_no_cards_is_the_base_hero(self):
        for hero, spec in config.HEROES.items():
            lo = cards.build_loadout(hero, Counter())
            self.assertEqual(lo.body, spec)
            self.assertEqual(lo.weapon, config.WEAPONS[spec.weapon])
            self.assertEqual((lo.regen, lo.lifesteal), (0.0, 0.0))

    def test_stacking_is_exact_and_limited(self):
        base = weapon_of("wizard")
        lo = cards.build_loadout("wizard", Counter(sharpened=2, storm_caller=1, twin_shot=1))
        self.assertEqual(lo.weapon.shell.damage, round(base.shell.damage * 1.2 * 1.2))
        self.assertEqual(lo.weapon.shell.chain, base.shell.chain + 1)
        self.assertEqual(lo.weapon.pellets, 2)
        self.assertGreater(lo.weapon.spread_deg, 0)
        fast = cards.build_loadout("wizard", Counter(quick_hands=50))
        self.assertEqual(fast.weapon.fire_interval, cards.MIN_INTERVAL)
        wide = cards.build_loadout("knight", Counter(whirlwind=10))
        self.assertEqual(wide.weapon.arc_deg, 360.0)
        tank = cards.build_loadout("bard", Counter(iron_skin=2, vampiric=1, second_wind=1))
        self.assertEqual(tank.body.max_hp, config.HEROES["bard"].max_hp + 40)
        self.assertAlmostEqual(tank.lifesteal, 0.05)
        self.assertAlmostEqual(tank.regen, 1.0)

    def test_range_means_reach_for_swords_and_pulses(self):
        lo = cards.build_loadout("knight", Counter(long_reach=1))
        self.assertAlmostEqual(lo.weapon.reach, weapon_of("knight").reach * 1.2)
        lo = cards.build_loadout("princess", Counter(focus=1))
        self.assertAlmostEqual(lo.weapon.shell.max_range, weapon_of("princess").shell.max_range * 1.25)


class InGameTest(unittest.TestCase):
    def setUp(self):
        from ascii_adventurers.tests.test_players import make_manager, start_game
        self.m = make_manager()
        self.s = start_game(self.m, seed=31, hero="wizard")
        self.s.mouse.left_held = lambda: False

    def tearDown(self):
        pygame.mouse.set_visible(True)

    def key(self, k):
        self.s.handle_event(pygame.event.Event(pygame.KEYDOWN, key=k, unicode="", mod=0))

    def offer_up(self, picks=1):
        s = self.s
        s.me.progress.picks = picks
        s.update(1 / 60)              # the offer is drawn...
        s.update(1 / 60)              # ...and the cards come up
        self.assertIsInstance(s.overlay, card_picker.CardPicker)
        return list(s.me.progress.offer)

    def test_level_up_brings_up_the_cards_and_pauses_single_player(self):
        s = self.s
        s.me.progress.add(config.LEVEL_XP_BASE)          # one level: one pick
        s.update(1 / 60)
        s.update(1 / 60)
        self.assertIsInstance(s.overlay, card_picker.CardPicker)
        steps, t = s.steps, s.stats.time
        for _ in range(30):
            s.update(1 / 60)
        self.assertEqual((s.steps, s.stats.time), (steps, t))   # paused
        s.draw(self.m.text)

    def test_left_right_and_enter(self):
        s = self.s
        offer = self.offer_up()
        self.key(pygame.K_RIGHT)
        self.key(pygame.K_RIGHT)
        self.key(pygame.K_LEFT)                          # on the second card
        self.key(pygame.K_RETURN)
        self.assertEqual(s.me.progress.cards[offer[1]], 1)
        self.assertEqual(s.me.progress.picks, 0)
        self.assertIsNone(s.overlay)                     # cards gone, game on
        self.assertEqual(s.stats.cards, [offer[1]])
        expected = cards.build_loadout("wizard", Counter({offer[1]: 1}))
        self.assertEqual(s.hero.weapon.spec, expected.weapon)
        self.assertEqual(s.hero.spec, expected.body)
        steps = s.steps
        s.update(1 / 60)
        self.assertEqual(s.steps, steps + 1)             # running again

    def test_mouse_hover_and_click(self):
        s = self.s
        offer = self.offer_up()
        picker = s.overlay
        left, top, w = picker._layout()
        col = left + 2 * (w + card_picker.GAP) + w // 2    # the third card
        cell = (col, top + 5)
        d = self.m.display
        px = ((cell[0] + 0.5) * d.cell_w, (cell[1] + 0.5) * d.cell_h)
        d.window_to_cell = lambda x, y: cell               # headless: no real window
        s.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=px, rel=(0, 0), buttons=(0, 0, 0)))
        self.assertEqual(picker.index, 2)
        s.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=px, button=1))
        self.assertEqual(s.me.progress.cards[offer[2]], 1)

    def test_banked_picks_come_one_offer_after_another(self):
        s = self.s
        self.offer_up(picks=3)
        for n in range(3):
            self.assertIsInstance(s.overlay, card_picker.CardPicker)
            self.assertEqual(s.overlay.waiting, 2 - n)
            self.key(pygame.K_RETURN)
        self.assertEqual(sum(s.me.progress.cards.values()), 3)
        self.assertIsNone(s.overlay)

    def test_gamepad_navigates_like_the_keyboard(self):
        from ascii_adventurers.engine_ext import gamepads
        s = self.s
        offer = self.offer_up()
        right = pygame.event.Event(gamepads.EV_BUTTON, instance_id=0,
                                   button=getattr(pygame, "CONTROLLER_BUTTON_DPAD_RIGHT"))
        a = pygame.event.Event(gamepads.EV_BUTTON, instance_id=0,
                               button=getattr(pygame, "CONTROLLER_BUTTON_A"))
        s.handle_event(right)
        s.handle_event(a)
        self.assertEqual(s.me.progress.cards[offer[1]], 1)

    def test_escape_pauses_and_the_cards_come_back(self):
        from ascii_adventurers.ui.overlays import PauseMenu
        s = self.s
        self.offer_up()
        self.key(pygame.K_ESCAPE)
        self.assertIsInstance(s.overlay, PauseMenu)
        self.key(pygame.K_ESCAPE)                        # resume
        s.update(1 / 60)
        self.assertIsInstance(s.overlay, card_picker.CardPicker)

    def test_max_hp_regen_and_lifesteal_work(self):
        s = self.s
        s.me.progress.cards.update(iron_skin=1, second_wind=1, vampiric=1)
        s._apply_loadout(s.me)
        self.assertEqual(s.hero.max_hp, 120)
        self.assertEqual(s.hero.hp, 120)                  # new max HP comes filled
        s.hero.hp = 50
        for _ in range(60):
            s.update(1 / 60)
        self.assertAlmostEqual(s.hero.hp, 51.0, delta=0.05)   # 1 HP per second
        from ascii_adventurers.tests.test_weapons import Dummy
        d = Dummy(s.hero.x + 3, s.hero.y)
        d.take_damage(40, s.hero, 0.0)
        self.assertAlmostEqual(s.hero.hp, 51.0 + 40 * 0.05, delta=0.05)


class PickerDrawTest(unittest.TestCase):
    def test_fits_every_screen_centred(self):
        from engine import Display
        offer = ["sharpened", "storm_caller", "volley"]
        for cols in (80, 115, 128, 172):
            d = Display(cols, 30)
            calls = []

            class Rec:
                display = d

                def put(self, col, row, s, *a, **k):
                    calls.append((col, row, s))

            class M:
                display = d

            picker = card_picker.CardPicker(M(), offer, 2, lambda i: None)
            picker.draw(Rec())
            self.assertLessEqual(max(c + len(s) for c, _, s in calls), cols, cols)
            self.assertGreaterEqual(min(c for c, _, _ in calls), 0, cols)
            rows = [r for _, r, _ in calls]
            self.assertGreaterEqual(min(rows), 0)
            self.assertLess(max(rows), 30)
            mid = (min(rows) + max(rows)) / 2
            self.assertAlmostEqual(mid, 15, delta=3)          # roughly centred
            text = " ".join(s for _, _, s in calls)
            self.assertIn("(+2 more)", text)
            for k in offer:
                self.assertIn(config.CARDS[k].name.upper(), text)


if __name__ == "__main__":
    unittest.main()
