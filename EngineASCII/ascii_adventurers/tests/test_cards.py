import os
import unittest
from collections import Counter

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from ascii_adventurers import config
from ascii_adventurers.players import cards
from ascii_adventurers.players.stats import HeroStats
from ascii_adventurers.ui import gear_screen

OPS = ("add", "mul", "flag", "status", "source", "spell")
GAP = 3                       # (ui/gear_picker.GAP)


def weapon_of(hero):
    return config.WEAPONS[config.HEROES[hero].weapon]


def stats_with(*taken):
    return cards.hero_stats(list(taken))


class CardDataTest(unittest.TestCase):
    def test_every_card_is_well_formed_and_fits_the_tray(self):
        narrow = (80 - 4 - 2 * GAP) // 3 - 4                # 3 cards on an 80-column screen
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
                    self.assertEqual(" ".join(gear_screen.wrap(text, narrow)), text, (key, lv))
                    self.assertLessEqual(len(name), narrow, key)

    def test_the_whole_catalog(self):
        """design/CARDS.md rev 2: 101 cards."""
        codes = [c.code for c in config.CARDS.values()]
        # + 11 dodge roll cards (M18), + 5 patterns and 4 hero cards (M19)
        # + 6 wizard cards (M20), - Arcane Mastery and Weapons Master (M28.1)
        self.assertEqual(len(codes), 125)
        self.assertEqual(len(set(codes)), 125)
        for prefix, n in (("G", 21), ("T", 12), ("S", 12), ("C", 8), ("X", 6), ("R", 6),
                          ("E", 3), ("K", 6), ("V", 6), ("M", 5)):
            self.assertEqual(sum(c.startswith(prefix) for c in codes), n, prefix)
        for hero in config.HEROES:
            own = [k for k, c in config.CARDS.items() if c.heroes == (hero,)]
            self.assertEqual(len(own), 12 if hero == "wizard" else 7, hero)   # + lightning
            capstone = [k for k in own if config.CARDS[k].rarity == "legendary"]
            self.assertEqual(len(capstone), 1, hero)

    def test_no_plain_stat_is_sold_twice(self):
        """The no-repeats rule: every "add" to a plain stat (not hero-card
        or conditional numbers) belongs to one card."""
        seen = {}
        plain = {"damage", "attack_speed", "max_hp", "move", "range", "crit_chance",
                 "crit_damage", "area", "duration", "armor", "evasion", "regen", "lifesteal",
                 "pickup", "xp", "luck", "pierce", "pellets", "status_power", "status_chance",
                 "spell_cooldown", "loot", "shot_speed", "roll_cooldown", "roll_charges"}
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


class RarityWeightsTest(unittest.TestCase):
    def test_luck(self):
        w = cards.rarity_weights(20)
        self.assertAlmostEqual(w[2] / config.CARD_RARITY_WEIGHT["rare"], 1.2 ** 2)


class StatsTest(unittest.TestCase):
    def test_no_cards_is_the_base_hero(self):
        for hero, spec in config.HEROES.items():
            lo = cards.build_loadout(hero, [])
            self.assertEqual(lo.body, spec)
            self.assertEqual(lo.weapon, config.WEAPONS[spec.weapon])
            self.assertEqual((lo.regen, lo.lifesteal), (0.0, 0.0))
            self.assertEqual(lo.stats.crit_chance, config.BASE_CRIT_CHANCE)

    def test_tiered_values_and_buckets(self):
        st = stats_with(("sharpened", "common"), ("sharpened", "legendary"),
                        ("glass_cannon", "rare"), ("glass_cannon", "rare"))
        self.assertAlmostEqual(st.damage, 0.10 + 0.40)            # bucket A adds
        self.assertAlmostEqual(st.damage_mult, 1.4 ** 2)          # "x" cards multiply
        self.assertAlmostEqual(st.max_hp_mult, 0.7 ** 2)

    def test_order_does_not_matter(self):
        a = [("sharpened", "rare"), ("focus", "common"), ("prism", "rare"), ("iron_skin", "epic")]
        self.assertEqual(cards.build_loadout("princess", a), cards.build_loadout("princess", a[::-1]))

    def test_weapon_and_body(self):
        base = weapon_of("wizard")
        lo = cards.build_loadout("wizard", [("storm_caller", "rare"), ("multishot", "rare"),
                                            ("long_reach", "rare"), ("quick_hands", "legendary")])
        self.assertEqual(lo.weapon.shell.chain, 0)     # (Storm Caller's jumps are the spell's, M28.2g)
        self.assertEqual(lo.weapon.pellets, base.pellets + 1)
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
        self.assertEqual(st.evasion, config.MAX_EVASION)
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
