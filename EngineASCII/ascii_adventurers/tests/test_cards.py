import os
import unittest
from collections import Counter

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from ascii_adventurers import config
from ascii_adventurers.players import cards
from ascii_adventurers.players.stats import HeroStats
from ascii_adventurers.ui import card_picker

OPS = ("add", "mul", "flag", "status", "source", "spell")


def weapon_of(hero):
    return config.WEAPONS[config.HEROES[hero].weapon]


def stats_with(*taken):
    return cards.hero_stats(list(taken))


class CardDataTest(unittest.TestCase):
    def test_every_card_is_well_formed_and_fits_the_tray(self):
        narrow = (80 - 4 - 2 * card_picker.GAP) // 3 - 4    # 3 cards on an 80-column screen
        fields = set(HeroStats.__dataclass_fields__)
        for key, c in config.CARDS.items():
            self.assertTrue(set(c.heroes) <= set(config.HEROES), key)
            self.assertTrue(set(c.kinds) <= {"shot", "melee", "pulse"}, key)
            self.assertGreater(c.max_stacks, 0, key)
            if c.tiered:
                self.assertEqual(len(c.tiers), len(config.RARITIES), key)
                self.assertIn("{X}", c.text, key)
            else:
                self.assertIn(c.rarity, config.RARITIES, key)
            for stat, op, val in c.mods:
                self.assertIn(op, OPS, key)
                if op in ("add", "mul"):
                    self.assertTrue(stat in fields or stat.startswith("tag:"), (key, stat))
                if op in ("status", "source"):
                    self.assertIn(stat, config.STATUSES, key)
                if op == "spell":
                    self.assertIn(stat, config.SPELLS, key)
                self.assertTrue(val == "X" or isinstance(val, (int, float)), key)
            # Every rarity it can show at, and (spells) every level: nothing cut.
            for rarity in cards.rarities_of(c):
                levels = range(config.SPELL_MAX_LEVEL) if cards.spell_of(c) else (0,)
                for lv in levels:
                    spells = {cards.spell_of(c): lv} if lv else {}
                    name, text = cards.card_text(key, rarity, spells)
                    self.assertEqual(" ".join(card_picker.wrap(text, narrow)), text, (key, lv))
                    self.assertLessEqual(len(name), narrow, key)

    def test_the_whole_catalog(self):
        """design/CARDS.md rev 2: 101 cards."""
        codes = [c.code for c in config.CARDS.values()]
        self.assertEqual(len(codes), 101)
        self.assertEqual(len(set(codes)), 101)
        for prefix, n in (("G", 21), ("T", 14), ("S", 12), ("C", 8), ("X", 6), ("R", 6),
                          ("E", 3), ("K", 6)):
            self.assertEqual(sum(c.startswith(prefix) for c in codes), n, prefix)
        for hero in config.HEROES:
            own = [k for k, c in config.CARDS.items() if c.heroes == (hero,)]
            self.assertEqual(len(own), 5, hero)
            capstone = [k for k in own if config.CARDS[k].rarity == "legendary"]
            self.assertEqual(len(capstone), 1, hero)

    def test_no_plain_stat_is_sold_twice(self):
        """The no-repeats rule: every "add" to a plain stat (not hero-card
        or conditional numbers) belongs to one card."""
        seen = {}
        plain = {"damage", "attack_speed", "max_hp", "move", "range", "crit_chance",
                 "crit_damage", "area", "duration", "armor", "dodge", "regen", "lifesteal",
                 "pickup", "xp", "luck", "pierce", "pellets", "status_power", "status_chance",
                 "spell_cooldown", "loot", "shot_speed"}
        for key, c in config.CARDS.items():
            for stat, op, val in c.mods:
                if op == "add" and stat in plain and (val == "X" or val > 0):
                    self.assertNotIn(stat, seen, (key, seen.get(stat)))
                    seen[stat] = key

    def test_rarity_multipliers_are_rare_or_better(self):
        """Catalog rule: every "xN damage" card is rare+."""
        for key, c in config.CARDS.items():
            if any(stat == "damage_mult" for stat, _, _ in c.mods):
                self.assertGreaterEqual(config.RARITIES.index(c.rarity), 2, key)

    def test_tier_values_grow(self):
        for key, c in config.CARDS.items():
            if c.tiered:
                vals = [v for v in c.tiers if v is not None]
                self.assertEqual(vals, sorted(vals), key)
        self.assertEqual(cards.card_text("sharpened", "epic")[1], "+30% damage")
        self.assertEqual(cards.rarities_of(config.CARDS["vampiric"])[0], "uncommon")


class EligibilityTest(unittest.TestCase):
    def test_hero_and_weapon_restrictions(self):
        bard = cards.eligible("bard", weapon_of("bard"), Counter())
        self.assertIn("crescendo", bard)
        self.assertNotIn("piercing", bard)            # the lute doesn't shoot
        self.assertNotIn("storm_caller", bard)        # the wizard's
        dwarf = cards.eligible("dwarf", weapon_of("dwarf"), Counter())
        self.assertIn("ricochet", dwarf)
        self.assertNotIn("piercing", dwarf)           # axes pierce everything already
        self.assertNotIn("volley", dwarf)             # the huntress's
        self.assertIn("multishot", dwarf)             # rev 2: everyone who shoots
        self.assertNotIn("multishot", bard)
        wizard = cards.eligible("wizard", weapon_of("wizard"), Counter())
        self.assertIn("storm_caller", wizard)
        self.assertIn("piercing", wizard)
        self.assertNotIn("prism", wizard)

    def test_maxed_and_banished_cards_are_not_offered(self):
        taken = Counter(sharpened=config.CARDS["sharpened"].max_stacks)
        self.assertNotIn("sharpened", cards.eligible("bard", weapon_of("bard"), taken))
        self.assertNotIn("brutal", cards.eligible("bard", weapon_of("bard"), Counter(),
                                                  banished={"brutal"}))

    def test_gates(self):
        w = weapon_of("wizard")
        bare = cards.eligible("wizard", w, Counter(), HeroStats())
        self.assertNotIn("potency", bare)             # no status source yet
        self.assertNotIn("quickened", bare)           # no spell yet
        burning = stats_with(("kindling", "uncommon"))
        self.assertIn("potency", cards.eligible("wizard", w, Counter(), burning))
        caster = stats_with(("daggers", "uncommon"))
        self.assertIn("quickened", cards.eligible("wizard", w, Counter(), caster))
        # A spell's own status counts as a source.
        self.assertIn("potency", cards.eligible("wizard", w, Counter(),
                                                stats_with(("ember_aura", "uncommon"))))

    def test_spell_slots(self):
        w = weapon_of("bard")
        full = stats_with(("daggers", "uncommon"), ("ember_aura", "uncommon"))
        self.assertIn("frost_nova", cards.eligible("bard", w, Counter(), full))
        full.spell_slots = 2
        pool = cards.eligible("bard", w, Counter(daggers=1, ember_aura=1), full)
        self.assertNotIn("frost_nova", pool)          # slots full: no new spells...
        self.assertIn("daggers", pool)                # ...but level-ups still come


class OfferTest(unittest.TestCase):
    def test_three_different_cards_same_every_time(self):
        a = cards.draw_offer("huntress", weapon_of("huntress"), Counter(), 99, 0, 5)
        b = cards.draw_offer("huntress", weapon_of("huntress"), Counter(), 99, 0, 5)
        self.assertEqual(a, b)
        self.assertEqual(len(a), config.CARD_OFFER_SIZE)
        self.assertEqual(len({k for k, _ in a}), len(a))
        other = [cards.draw_offer("huntress", weapon_of("huntress"), Counter(), 99, 0, n)
                 for n in range(20)]
        self.assertGreater(len({tuple(o) for o in other}), 5)   # offers vary

    def test_every_offered_rarity_is_one_the_card_has(self):
        for n in range(200):
            for k, r in cards.draw_offer("princess", weapon_of("princess"), Counter(), 3, 0, n):
                self.assertIn(r, cards.rarities_of(config.CARDS[k]))

    def seen(self, luck, n=1500):
        stats = HeroStats(luck=luck)
        seen = Counter()
        for i in range(n):
            for _, r in cards.draw_offer("wizard", weapon_of("wizard"), Counter(), 7, 0, i, stats):
                seen[r] += 1
        return seen

    def test_rarity_weights_and_luck(self):
        plain = self.seen(0)
        self.assertGreater(plain["common"], plain["uncommon"])
        self.assertGreater(plain["uncommon"], plain["rare"])
        self.assertGreater(plain["rare"], plain["epic"])
        self.assertGreater(plain["legendary"], 0)
        lucky = self.seen(100)
        self.assertGreater(lucky["legendary"], plain["legendary"] * 2)
        self.assertLess(lucky["common"], plain["common"])
        w = cards.rarity_weights(20)
        self.assertAlmostEqual(w[2] / config.CARD_RARITY_WEIGHT["rare"], 1.2 ** 2)

    def test_synergy_weighting(self):
        """Frost cards come up more once the build has frost."""
        def frost_share(stats):
            n = 0
            for i in range(2000):
                n += sum(k == "frostbite" for k, _ in
                         cards.draw_offer("wizard", weapon_of("wizard"), Counter(), 11, 0, i, stats))
            return n
        self.assertGreater(frost_share(stats_with(("frost_nova", "uncommon"))),
                           frost_share(HeroStats()) * 1.2)


class StatsTest(unittest.TestCase):
    def test_no_cards_is_the_base_hero(self):
        for hero, spec in config.HEROES.items():
            lo = cards.build_loadout(hero, [])
            self.assertEqual(lo.body, spec)
            self.assertEqual(lo.weapon, config.WEAPONS[spec.weapon])
            self.assertEqual((lo.regen, lo.lifesteal), (0.0, 0.0))
            self.assertEqual(lo.stats.crit_chance, config.BASE_CRIT_CHANCE)

    def test_tiered_values_and_buckets(self):
        st = stats_with(("sharpened", "common"), ("sharpened", "legendary"), ("heavy_axe", "rare"),
                        ("heavy_axe", "rare"))
        self.assertAlmostEqual(st.damage, 0.10 + 0.40)            # bucket A adds
        self.assertAlmostEqual(st.damage_mult, 1.35 ** 2)         # "x" cards multiply
        self.assertAlmostEqual(st.interval_mult, 1.1 ** 2)

    def test_order_does_not_matter(self):
        a = [("sharpened", "rare"), ("focus", "common"), ("prism", "rare"), ("iron_skin", "epic")]
        self.assertEqual(cards.build_loadout("princess", a), cards.build_loadout("princess", a[::-1]))

    def test_weapon_and_body(self):
        base = weapon_of("wizard")
        lo = cards.build_loadout("wizard", [("storm_caller", "rare"), ("multishot", "rare"),
                                            ("long_reach", "rare"), ("quick_hands", "legendary")])
        self.assertEqual(lo.weapon.shell.chain, base.shell.chain + 1)
        self.assertEqual(lo.weapon.pellets, 2)
        self.assertGreater(lo.weapon.spread_deg, 0)
        self.assertAlmostEqual(lo.weapon.shell.max_range, base.shell.max_range * 1.2)
        self.assertAlmostEqual(lo.weapon.fire_interval, base.fire_interval / 1.3)
        self.assertEqual(lo.weapon.shell.damage, base.shell.damage)   # scaled per hit instead
        fast = cards.build_loadout("wizard", [("quick_hands", "legendary")] * 50)
        self.assertEqual(fast.weapon.fire_interval, config.MIN_ATTACK_INTERVAL)
        tank = cards.build_loadout("bard", [("iron_skin", "common"), ("iron_skin", "rare"),
                                            ("vampiric", "uncommon"), ("second_wind", "rare")])
        self.assertEqual(tank.body.max_hp, config.HEROES["bard"].max_hp + 15 + 35)
        self.assertAlmostEqual(tank.lifesteal, 0.01)
        self.assertAlmostEqual(tank.regen, 1.0)

    def test_caps(self):
        st = stats_with(*[("nimble", "legendary")] * 10, *[("vampiric", "legendary")] * 10,
                        *[("swift_boots", "legendary")] * 10)
        self.assertEqual(st.dodge, config.MAX_DODGE)
        self.assertEqual(st.lifesteal, config.MAX_LIFESTEAL)
        self.assertEqual(st.move, config.MAX_MOVE_BONUS)

    def test_reach_for_pulses_grows_with_range_and_area(self):
        lo = cards.build_loadout("bard", [("long_reach", "common"), ("broad_strokes", "common")])
        self.assertAlmostEqual(lo.weapon.reach, weapon_of("bard").reach * 1.18)
        lo = cards.build_loadout("princess", [("focus", "common")])
        self.assertAlmostEqual(lo.weapon.spread_deg, weapon_of("princess").spread_deg * 0.7)

    def test_axes_never_get_pierce(self):
        lo = cards.build_loadout("dwarf", Counter(piercing=1))
        self.assertEqual(lo.weapon.shell.pierce, 0)

    def test_spells_level_up(self):
        st = stats_with(("daggers", "uncommon"), ("daggers", "uncommon"))
        self.assertEqual(st.spells, {"daggers": 2})
        st = stats_with(*[("daggers", "uncommon")] * 9)
        self.assertEqual(st.spells["daggers"], config.SPELL_MAX_LEVEL)
        self.assertEqual(cards.card_text("daggers", "uncommon", {"daggers": 2}),
                         ("Daggers III", config.SPELLS["daggers"].levels[1][0]))
        self.assertEqual(cards.card_text("ember_aura", "uncommon", {"ember_aura": 1})[0],
                         "Ember Aura II")


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
        self.assertEqual(s.me.progress.taken, [offer[1]])
        self.assertEqual(s.me.progress.picks, 0)
        self.assertIsNone(s.overlay)                     # cards gone, game on
        self.assertEqual(s.stats.cards, [offer[1][0]])
        expected = cards.build_loadout("wizard", [offer[1]])
        self.assertEqual(s.hero.weapon.spec, expected.weapon)
        self.assertEqual(s.hero.spec, expected.body)
        self.assertEqual(s.hero.stats, expected.stats)
        steps = s.steps
        s.update(1 / 60)
        self.assertEqual(s.steps, steps + 1)             # running again

    def click(self, cell):
        d = self.m.display
        px = ((cell[0] + 0.5) * d.cell_w, (cell[1] + 0.5) * d.cell_h)
        d.window_to_cell = lambda x, y: cell               # headless: no real window
        self.s.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=px, rel=(0, 0),
                                               buttons=(0, 0, 0)))
        self.s.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=px, button=1))

    def test_mouse_hover_and_click(self):
        s = self.s
        offer = self.offer_up()
        picker = s.overlay
        left, top, w = picker._layout()
        self.click((left + 2 * (w + card_picker.GAP) + w // 2, top + 5))   # the third card
        self.assertEqual(s.me.progress.taken, [offer[2]])

    def test_banked_picks_come_one_offer_after_another(self):
        s = self.s
        self.offer_up(picks=3)
        for n in range(3):
            self.assertIsInstance(s.overlay, card_picker.CardPicker)
            self.assertEqual(s.overlay.waiting, 2 - n)
            self.key(pygame.K_RETURN)
        self.assertEqual(len(s.me.progress.taken), 3)
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
        self.assertEqual(s.me.progress.taken, [offer[1]])

    def test_escape_pauses_and_the_cards_come_back(self):
        from ascii_adventurers.ui.overlays import PauseMenu
        s = self.s
        self.offer_up()
        self.key(pygame.K_ESCAPE)
        self.assertIsInstance(s.overlay, PauseMenu)
        self.key(pygame.K_ESCAPE)                        # resume
        s.update(1 / 60)
        self.assertIsInstance(s.overlay, card_picker.CardPicker)

    def test_reroll(self):
        s = self.s
        offer = self.offer_up()
        self.key(pygame.K_r)
        prog = s.me.progress
        self.assertEqual(prog.rerolls, config.CARD_REROLLS - 1)
        self.assertEqual(prog.picks, 1)
        self.assertNotEqual(prog.offer, offer)
        self.assertEqual(s.overlay.offer, prog.offer)    # the picker shows the new offer
        self.assertEqual(s.overlay.rerolls, prog.rerolls)
        prog.rerolls = 0
        s.overlay.refresh(prog)
        before = list(prog.offer)
        self.key(pygame.K_r)                             # none left: nothing happens
        self.assertEqual(prog.offer, before)

    def test_reroll_by_the_button_row(self):
        s = self.s
        offer = self.offer_up()
        self.key(pygame.K_DOWN)                          # to the buttons: REROLL first
        self.key(pygame.K_RETURN)
        self.assertNotEqual(s.me.progress.offer, offer)
        self.assertEqual(s.me.progress.taken, [])

    def test_skip_heals(self):
        s = self.s
        self.offer_up()
        s.hero.hp = 50
        self.key(pygame.K_x)
        self.assertEqual(s.me.progress.picks, 0)
        self.assertEqual(s.me.progress.taken, [])
        self.assertAlmostEqual(s.hero.hp, 50 + config.SKIP_HEAL * s.hero.max_hp)
        self.assertIsNone(s.overlay)

    def test_skip_by_mouse(self):
        s = self.s
        self.offer_up()
        col, row, label = s.overlay._buttons()[2]
        self.click((col + 1, row))
        self.assertEqual(s.me.progress.picks, 0)

    def test_banish(self):
        s = self.s
        offer = self.offer_up()
        self.key(pygame.K_b)                             # none at the start: nothing
        self.assertEqual(s.me.progress.offer, offer)
        s.me.progress.banishes = 1
        s.overlay.refresh(s.me.progress)
        self.key(pygame.K_RIGHT)
        self.key(pygame.K_b)
        prog = s.me.progress
        self.assertEqual(prog.banished, {offer[1][0]})
        self.assertEqual(prog.banishes, 0)
        self.assertNotIn(offer[1][0], [k for k, _ in prog.offer])
        self.assertEqual(prog.picks, 1)

    def test_max_hp_regen_and_lifesteal_work(self):
        s = self.s
        for card in (("iron_skin", "uncommon"), ("second_wind", "rare"), ("vampiric", "legendary")):
            s.me.progress.take(*card)
        s._apply_loadout(s.me)
        self.assertEqual(s.hero.max_hp, 125)
        self.assertEqual(s.hero.hp, 125)                  # new max HP comes filled
        s.hero.hp = 50
        for _ in range(60):
            s.update(1 / 60)
        self.assertAlmostEqual(s.hero.hp, 51.0, delta=0.05)   # 1 HP per second
        from ascii_adventurers.tests.test_weapons import Dummy
        d = Dummy(s.hero.x + 3, s.hero.y)
        d.take_damage(40, s.hero, 0.0)
        self.assertAlmostEqual(s.hero.hp, 51.0 + 40 * 0.04, delta=0.05)


class PickerDrawTest(unittest.TestCase):
    def test_fits_every_screen_centred(self):
        from engine import Display
        from ascii_adventurers.players.progress import Progress
        prog = Progress(picks=3, offer=[("sharpened", "epic"), ("storm_caller", "rare"),
                                        ("daggers", "uncommon")])
        for cols in (80, 115, 128, 172):
            d = Display(cols, 30)
            calls = []

            class Rec:
                display = d

                def put(self, col, row, s, *a, **k):
                    calls.append((col, row, s))

            class M:
                display = d

            picker = card_picker.CardPicker(M(), prog, lambda i: None)
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
            for name in ("SHARPENED", "STORM CALLER", "ORBITING DAGGERS", "+30% damage",
                         "EPIC", "REROLL 3", "BANISH 0", "SKIP"):
                self.assertIn(name, text, cols)


if __name__ == "__main__":
    unittest.main()
