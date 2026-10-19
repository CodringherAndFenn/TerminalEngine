"""M28.1: the cards became gear (design/GEAR.md section 15)."""

import os
import unittest
from collections import Counter

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from ascii_adventurers import config
from ascii_adventurers.players import cards, gear
from ascii_adventurers.players.gear import Equipment, Offer, Piece
from ascii_adventurers.players.stats import HeroStats, spell_params
from ascii_adventurers.ui import gear_picker, gear_screen


def weapon_of(hero):
    return config.WEAPONS[config.HEROES[hero].weapon]


def stats_of(eq, hero="wizard", meta=()):
    return cards.loadout_from_steps(hero, eq.steps(), meta).stats


def wearing(*pieces, trinkets=3):
    eq = Equipment(trinkets=trinkets)
    for p in pieces:
        eq.take(Offer(p.key, p.rarity, p.affixes, "new"))
        eq.worn[eq.wearing(p.key)].level = p.level
    return eq


class DataTest(unittest.TestCase):
    def test_every_card_has_one_home(self):
        bases, affixes = set(config.GEAR), set(config.AFFIXES)
        self.assertEqual(len(bases), 100)
        self.assertEqual(len(affixes), 25)
        self.assertFalse(bases & affixes)
        self.assertEqual(bases | affixes, set(config.CARDS))
        self.assertNotIn("arcane_mastery", config.CARDS)          # cut (GEAR.md 8)
        self.assertNotIn("weapons_master", config.CARDS)
        homes = Counter(g.slot for g in config.GEAR.values())
        self.assertEqual(homes, {"main": 34, "off": 8, "head": 11, "chest": 11, "feet": 11,
                                 "ring": 14, "trinket": 11})
        for key, g in config.GEAR.items():
            self.assertIn(g.slot, config.GEAR_SLOTS, key)
            self.assertLessEqual(len(g.name), 16, key)            # fits a narrow card
        # Every main-hand piece belongs to one hero; affixes are plain stats.
        for key, g in config.GEAR.items():
            if g.slot == "main":
                self.assertEqual(len(config.CARDS[key].heroes), 1, key)

    def test_no_power_needs_a_piece_of_its_own_slot_only(self):
        """A gate only a piece in the same slot could open would never let
        the piece come up (M28.1 moved Chain Lightning to the trinkets and
        gave the cowl its own bleed for this)."""
        sources = {}
        for k, c in config.CARDS.items():
            for st, op, _ in c.mods + (config.GEAR[k].mods if k in config.GEAR else ()):
                if op in ("status", "source"):
                    sources.setdefault(st, set()).add(k)
        for k, s in config.SPELLS.items():
            if s.base.get("inflicts"):
                sources.setdefault(s.base["inflicts"], set()).add(k)
        for key, g in config.GEAR.items():
            needs = g.needs if g.needs is not None else config.CARDS[key].needs
            for n in needs:
                if n in config.GEAR:
                    other = config.GEAR[n].slot
                    self.assertTrue(other != g.slot or g.slot in ("ring", "trinket"), (key, n))
                elif n in sources:
                    self.assertTrue(any(x not in config.GEAR or config.GEAR[x].slot != g.slot
                                        for x in sources[n]), (key, n))


class PowerTest(unittest.TestCase):
    def test_level_zero_is_the_card(self):
        for key in config.GEAR:
            c = config.CARDS[key]
            if cards.spell_of(c) is None:
                expect = cards.card_steps(key, c.rarity) + list(config.GEAR[key].mods)
                self.assertEqual(gear.power_steps(key, 0), expect, key)

    def test_plus_one_grows_the_main_number(self):
        # (x the rarity's power too since M28.3a: tests/test_m28_3a.py)
        r = config.GEAR_RARITY_POWER
        eq = wearing(Piece("broadhead", "uncommon", 4))
        st = stats_of(eq, "huntress")
        self.assertAlmostEqual(st.broadhead, 0.15 * 1.4 * r["uncommon"])
        eq = wearing(Piece("glass_cannon", "rare", 5))
        st = stats_of(eq, "bard")
        self.assertAlmostEqual(st.damage_mult, 1 + 0.4 * 1.5 * r["rare"])   # a "x" grows its distance from 1
        self.assertAlmostEqual(st.max_hp_mult, 0.7)               # ...and the downside stays
        eq = wearing(Piece("focus", "common", 2))
        self.assertAlmostEqual(stats_of(eq, "princess").spread_mult, 1 - 0.3 * 1.2)

    def test_powers_with_no_number_grow_damage(self):
        for key in ("seeker", "heavy_plate", "phoenix", "fortune"):
            eq = wearing(Piece(key, config.CARDS[key].rarity, 3))
            hero = (config.CARDS[key].heroes or ("wizard",))[0]
            st = stats_of(eq, hero)
            rarity = (config.GEAR_RARITY_POWER[config.CARDS[key].rarity] - 1) * config.GEAR_RARITY_FLAT
            self.assertAlmostEqual(st.damage, 0.15 + rarity, msg=key)
        self.assertEqual(stats_of(wearing(Piece("phoenix", "legendary", 9))).phoenix, 1)
        self.assertEqual(stats_of(wearing(Piece("fortune", "epic", 9))).offer_size, 1)
        # Heavy Plate's -15% move is the downside, not its number (it doesn't
        # grow); from +6 Lighter steel drops it (M28.2d).
        self.assertAlmostEqual(stats_of(wearing(Piece("heavy_plate", "uncommon", 5))).move, -0.15)
        self.assertAlmostEqual(stats_of(wearing(Piece("heavy_plate", "uncommon", 9))).move, 0.0)

    def test_a_trinket_at_four_is_the_spell_at_five(self):
        for key in ("daggers", "ember_aura", "ward_charm", "chain_lightning"):
            eq = wearing(Piece(key, "uncommon", 4))
            st = stats_of(eq)
            self.assertEqual(st.spells[key], config.SPELL_MAX_LEVEL, key)
            # (only the rarity's boost, M28.3a)
            self.assertAlmostEqual(st.spell_boost.get(key, 0.0), gear.spell_boost(key, 4, "uncommon"),
                                   msg=key)
            self.assertEqual(st.spells, cards.hero_stats([(key, "uncommon")] * 5).spells)

    def test_past_four_the_spell_grows(self):
        eq = wearing(Piece("daggers", "common", 9))
        st = stats_of(eq)
        self.assertAlmostEqual(st.spell_boost["daggers"], 0.5)
        five = spell_params("daggers", 5)
        self.assertAlmostEqual(spell_params("daggers", 5, 0.5)["damage"], five["damage"] * 1.5)
        ward = stats_of(wearing(Piece("ward_charm", "common", 7)))
        self.assertAlmostEqual(ward.shield, spell_params("ward_charm", 5)["shield"] * 1.3)

    def test_the_cowl_brings_its_bleed(self):
        st = stats_of(wearing(Piece("hemorrhage", "rare")))
        self.assertIn("bleed", st.statuses)
        self.assertIn("hemorrhage", st.flags)
        self.assertIn("bleed", gear.power_text("hemorrhage"))


class AffixTest(unittest.TestCase):
    def test_counts_and_values(self):
        eq = wearing(Piece("seeker", "epic", 0, ("sharpened", "iron_skin", "keen_eye")))
        st = stats_of(eq)
        seeker = (config.GEAR_RARITY_POWER["epic"] - 1) * config.GEAR_RARITY_FLAT   # (M28.3a)
        self.assertAlmostEqual(st.damage, 0.30 + seeker)           # Sharpened's epic tier
        self.assertEqual(cards.loadout_from_steps("wizard", eq.steps()).body.max_hp,
                         config.HEROES["wizard"].max_hp + 50)
        self.assertEqual(gear.affix_text("sharpened", "epic"), "+30% damage")

    def test_pool_gates_and_rarities(self):
        w = weapon_of("wizard")
        bare = gear.affix_pool("seeker", "rare", "wizard", w, HeroStats())
        self.assertNotIn("potency", bare)              # no status source
        self.assertNotIn("quickened", bare)            # no spell
        self.assertNotIn("elementalist", bare)         # no element (arcane missiles)
        self.assertNotIn("quick_recovery", bare)       # boots only
        self.assertIn("multishot", bare)               # rare+
        self.assertIn("piercing", bare)
        unc = gear.affix_pool("seeker", "uncommon", "wizard", w, HeroStats())
        self.assertNotIn("multishot", unc)
        self.assertIn("vampiric", unc)
        com = gear.affix_pool("seeker", "common", "wizard", w, HeroStats())
        self.assertNotIn("vampiric", com)              # no common tier
        boots = gear.affix_pool("riposte", "rare", "wizard", w, HeroStats())
        self.assertIn("quick_recovery", boots)
        self.assertIn("extra_roll", boots)
        self.assertNotIn("piercing", gear.affix_pool("hang_time", "rare", "dwarf",
                                                     weapon_of("dwarf"), HeroStats()))
        burning = cards.hero_stats([("kindling", "uncommon")])
        self.assertIn("potency", gear.affix_pool("seeker", "rare", "wizard", w, burning))

    def test_caps(self):
        pieces = [Piece(k, "uncommon", 0, ("multishot",))
                  for k in ("seeker", "cross_fire", "kindling", "untouched")]
        eq = wearing(*pieces)
        self.assertEqual(len(eq.capped()), 1)          # the 4th +1 projectile does nothing
        self.assertEqual(stats_of(eq).pellets, config.CARDS["multishot"].max_stacks)


class OfferTest(unittest.TestCase):
    def test_same_every_time_and_different_bases(self):
        w = weapon_of("huntress")
        a = gear.draw_offer("huntress", w, Equipment(), 99, 0, 5)
        b = gear.draw_offer("huntress", w, Equipment(), 99, 0, 5)
        self.assertEqual(a, b)
        self.assertEqual(len(a), config.CARD_OFFER_SIZE)
        self.assertEqual(len({o.key for o in a}), len(a))
        other = {tuple(gear.draw_offer("huntress", w, Equipment(), 99, 0, n)) for n in range(20)}
        self.assertGreater(len(other), 5)

    def test_the_first_offer_holds_a_main_hand_piece(self):
        for hero in config.HEROES:
            for seed in range(20):
                off = gear.draw_offer(hero, weapon_of(hero), Equipment(), seed, 0, 0)
                self.assertTrue(any(config.GEAR[o.key].slot == "main" for o in off), (hero, seed))
                for o in off:
                    heroes = config.CARDS[o.key].heroes
                    self.assertTrue(not heroes or hero in heroes, (hero, o.key))

    def test_rarity_is_at_least_the_cards(self):
        rank = {r: i for i, r in enumerate(config.RARITIES)}
        seen = Counter()
        for n in range(400):
            for o in gear.draw_offer("princess", weapon_of("princess"), Equipment(), 3, 0, n,
                                     level=20):
                self.assertGreaterEqual(rank[o.rarity], rank[config.CARDS[o.key].rarity], o)
                self.assertEqual(len(o.affixes), len(set(o.affixes)))
                self.assertLessEqual(len(o.affixes), config.GEAR_AFFIXES[o.rarity])
                seen[o.rarity] += 1
        self.assertGreater(seen["uncommon"], seen["rare"])
        self.assertGreater(seen["rare"], seen["epic"])
        self.assertGreater(seen["epic"], seen["legendary"])
        self.assertLess(seen["legendary"], sum(seen.values()) * 0.05)

    def test_kinds_new_plus_swap(self):
        eq = wearing(Piece("seeker", "common"))
        self.assertEqual(gear.kind_of(eq, "seeker"), "plus")
        self.assertEqual(gear.kind_of(eq, "resonance"), "swap")     # main hand is full
        self.assertEqual(gear.kind_of(eq, "kindling"), "new")
        found = Counter()
        for n in range(100):
            for o in gear.draw_offer("wizard", weapon_of("wizard"), eq, 5, 0, n):
                found[o.kind] += 1
                if o.kind == "plus":
                    self.assertEqual((o.key, o.rarity), ("seeker", "common"))
        self.assertTrue(all(found[k] for k in ("new", "plus", "swap")), found)

    def test_eligibility(self):
        w = weapon_of("wizard")
        pool = gear.eligible("wizard", w, Equipment())
        self.assertIn("chain_lightning", pool)
        self.assertNotIn("storm_caller", pool)          # needs Chain Lightning (a trinket now)
        lit = wearing(Piece("chain_lightning", "uncommon"))
        self.assertIn("storm_caller", gear.eligible("wizard", w, lit, stats_of(lit)))
        self.assertIn("hemorrhage", pool)               # brings its own bleed
        self.assertNotIn("crescendo", pool)             # the bard's
        self.assertNotIn("sharpened", pool)             # an affix, not a piece
        self.assertNotIn("seeker", gear.eligible("wizard", w, Equipment(), banished={"seeker"}))
        maxed = wearing(Piece("seeker", "common", config.GEAR_MAX_LEVEL))
        self.assertNotIn("seeker", gear.eligible("wizard", w, maxed))
        self.assertNotIn("arcane_storm", gear.eligible("wizard", w, Equipment(), level=14))
        self.assertIn("arcane_storm", gear.eligible("wizard", w, Equipment(), level=15))

    def test_royal_decree_floor_leaves_out_plus_ones(self):
        eq = wearing(Piece("seeker", "common"))
        for n in range(50):
            for o in gear.draw_offer("wizard", weapon_of("wizard"), eq, 1, 0, n, min_rarity_="rare"):
                self.assertNotEqual(o.kind, "plus")
                self.assertIn(o.rarity, ("rare", "epic", "legendary"))

    def test_late_swaps_lean(self):
        eq = wearing(*[Piece(k, config.CARDS[k].rarity) for k in
                       ("seeker", "cross_fire", "kindling", "untouched", "riposte", "volatile")])
        self.assertGreaterEqual(eq.filled, config.GEAR_LEAN_FILLED)
        kinds = Counter(o.kind for n in range(300)
                        for o in gear.draw_offer("wizard", weapon_of("wizard"), eq, 8, 0, n))
        self.assertGreater(kinds["swap"], kinds["plus"])


class EquipmentTest(unittest.TestCase):
    def test_slots(self):
        eq = Equipment(trinkets=4)
        self.assertEqual(eq.slot_ids(), ["main", "off", "head", "chest", "feet", "ring1", "ring2",
                                         "trinket1", "trinket2", "trinket3", "trinket4"])

    def test_take_new_plus_and_swap_to_the_bag(self):
        eq = Equipment()
        eq.take(Offer("seeker", "common", (), "new"))
        self.assertEqual(eq.worn["main"].key, "seeker")
        eq.take(Offer("seeker", "common", (), "plus"))
        self.assertEqual(eq.worn["main"].level, 1)
        lost = eq.take(Offer("resonance", "rare", ("sharpened", "keen_eye"), "swap"))
        self.assertEqual(lost, [])
        self.assertEqual(eq.worn["main"].key, "resonance")
        self.assertEqual([(p.key, p.level) for p in eq.bag], [("seeker", 1)])

    def test_rings_choose_which_and_default_to_the_weakest(self):
        eq = wearing(Piece("volatile", "rare", 2), Piece("surge", "uncommon", 0))
        eq.take(Offer("bloodlust", "rare", (), "swap"), "ring1")
        self.assertEqual((eq.worn["ring1"].key, eq.worn["ring2"].key), ("bloodlust", "surge"))
        eq.take(Offer("veteran", "rare", (), "swap"))               # nobody chose
        self.assertEqual(eq.worn["ring2"].key, "veteran")           # surge was the weakest

    def test_a_full_bag_salvages_the_chosen_piece(self):
        eq = wearing(Piece("seeker", "common"))
        eq.bag = [Piece("resonance", "rare"), Piece("implosion", "rare"), Piece("orbiting_darts", "rare")]
        lost = eq.take(Offer("phase_darts", "rare", (), "swap"), "main", 1)
        self.assertEqual([p.key for p in lost], ["implosion"])
        self.assertEqual([p.key for p in eq.bag], ["resonance", "orbiting_darts", "seeker"])
        lost = eq.take(Offer("conductor", "common", (), "swap"), "main")    # no choice: the old one
        self.assertEqual([p.key for p in lost], ["phase_darts"])

    def test_wear_from_the_bag_and_salvage(self):
        eq = wearing(Piece("seeker", "common", 3))
        eq.bag = [Piece("resonance", "rare", 1)]
        self.assertFalse(eq.can_wear(0, "head"))                    # not its slot
        self.assertTrue(eq.wear(0, "main"))
        self.assertEqual((eq.worn["main"].key, eq.bag[0].key), ("resonance", "seeker"))
        rings = wearing(Piece("volatile", "rare"))
        rings.bag = [Piece("volatile", "rare")]
        self.assertFalse(rings.can_wear(0, "ring2"))               # one of each base worn
        p = eq.salvage("bag", 0)
        self.assertEqual(gear.salvage_value(p), round(20 * (1 + 0.5 * 3)))
        self.assertIsNone(eq.salvage("bag", 5))
        self.assertEqual(eq.salvage("worn", "main").key, "resonance")
        self.assertEqual(eq.filled, 0)

    def test_upgrade(self):
        eq = wearing(Piece("seeker", "common", config.GEAR_MAX_LEVEL - 1))
        self.assertTrue(eq.upgrade("main"))
        self.assertFalse(eq.upgrade("main"))                        # +9 is the top
        self.assertFalse(eq.upgrade("head"))                        # nothing there


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
        s.update(1 / 60)
        s.update(1 / 60)
        self.assertIsInstance(s.overlay, gear_picker.GearPicker)
        return list(s.me.progress.offer)

    def test_start_with_nothing_worn_and_level_up_pauses(self):
        s = self.s
        self.assertEqual(s.me.progress.gear.filled, 0)
        s.me.progress.add(config.LEVEL_XP_BASE)
        s.update(1 / 60)
        s.update(1 / 60)
        self.assertIsInstance(s.overlay, gear_picker.GearPicker)
        steps = s.steps
        for _ in range(20):
            s.update(1 / 60)
        self.assertEqual(s.steps, steps)                 # paused in single player
        s.draw(self.m.text)

    def test_take_a_piece(self):
        s = self.s
        offer = self.offer_up()
        self.key(pygame.K_RIGHT)
        self.key(pygame.K_RETURN)
        o = offer[1]
        slot = s.me.progress.gear.wearing(o.key)
        self.assertIsNotNone(slot)
        self.assertEqual(s.me.progress.gear.worn[slot].rarity, o.rarity)
        self.assertEqual(s.me.progress.picks, 0)
        self.assertIsNone(s.overlay)
        self.assertEqual(s.stats.cards, [o.key])
        expected = cards.loadout_from_steps("wizard", s.me.progress.gear.steps(), s.me.meta,
                                            s.me.progress.level)
        self.assertEqual(s.hero.stats, expected.stats)

    def test_upgrade_screen(self):
        s = self.s
        s.me.progress.gear.take(Offer("seeker", "common", (), "new"))
        s._apply_loadout(s.me)
        self.offer_up()
        self.key(pygame.K_u)
        self.assertIsNotNone(s.overlay.sub)
        self.assertEqual(s.overlay.sub.mode, "upgrade")
        s.draw(self.m.text)
        self.key(pygame.K_ESCAPE)                        # back to the offer
        self.assertIsNone(s.overlay.sub)
        self.key(pygame.K_u)
        self.key(pygame.K_RETURN)                        # the main hand (the only piece)
        self.assertEqual(s.me.progress.gear.worn["main"].level, 1)
        self.assertEqual(s.me.progress.picks, 0)

    def test_ring_swap_asks_which(self):
        s = self.s
        prog = s.me.progress
        for k in ("volatile", "surge"):
            prog.gear.take(Offer(k, "uncommon", (), "new"))
        prog.picks = 1
        prog.offer = [Offer("bloodlust", "uncommon", (), "swap")]
        s.update(1 / 60)
        picker = s.overlay
        self.key(pygame.K_RETURN)
        self.assertEqual(picker.sub.mode, "slot")
        self.key(pygame.K_RIGHT)                         # ring1 -> ring2
        self.key(pygame.K_RETURN)
        self.assertEqual((prog.gear.worn["ring1"].key, prog.gear.worn["ring2"].key),
                         ("volatile", "bloodlust"))
        self.assertEqual([p.key for p in prog.gear.bag], ["surge"])

    def test_full_bag_asks_what_to_salvage(self):
        s = self.s
        prog = s.me.progress
        prog.gear.take(Offer("seeker", "common", (), "new"))
        prog.gear.bag = [Piece("resonance", "rare"), Piece("implosion", "rare"),
                         Piece("orbiting_darts", "rare")]
        prog.picks = 1
        prog.offer = [Offer("phase_darts", "rare", (), "swap")]
        s.update(1 / 60)
        loot = s.stats.loot
        self.key(pygame.K_RETURN)
        self.assertEqual(s.overlay.sub.mode, "drop")
        s.draw(self.m.text)
        self.key(pygame.K_RETURN)                        # the first bag piece
        self.assertEqual(prog.gear.worn["main"].key, "phase_darts")
        self.assertEqual([p.key for p in prog.gear.bag], ["implosion", "orbiting_darts", "seeker"])
        self.assertEqual(s.stats.loot, loot + 80)        # a rare +0

    def test_reroll_skip_banish(self):
        s = self.s
        offer = self.offer_up(picks=3)
        self.key(pygame.K_r)
        prog = s.me.progress
        self.assertEqual(prog.rerolls, config.CARD_REROLLS - 1)
        self.assertNotEqual(prog.offer, offer)
        prog.banishes = 1
        s.overlay.refresh(prog)
        gone = prog.offer[0].key
        self.key(pygame.K_b)
        self.assertIn(gone, prog.banished)
        s.hero.hp = 50
        self.key(pygame.K_x)
        self.assertAlmostEqual(s.hero.hp, 50 + config.SKIP_HEAL * s.hero.max_hp)
        self.assertEqual(prog.picks, 2)

    def test_tab_opens_the_gear_screen_wear_and_salvage(self):
        s = self.s
        prog = s.me.progress
        prog.gear.take(Offer("seeker", "common", (), "new"))
        prog.gear.bag = [Piece("resonance", "rare", 2)]
        s._apply_loadout(s.me)
        self.key(pygame.K_TAB)
        screen = s.overlay
        self.assertIsInstance(screen, gear_screen.GearScreen)
        s.draw(self.m.text)
        screen.focus = screen.cells().index(("bag", 0))
        self.key(pygame.K_RETURN)                        # wear it
        self.assertEqual(prog.gear.worn["main"].key, "resonance")
        self.assertEqual(s.hero.stats.has("resonance"), True)
        loot = s.stats.loot
        screen.focus = screen.cells().index(("bag", 0))
        self.key(pygame.K_x)                             # asks first...
        self.assertEqual(len(prog.gear.bag), 1)
        self.key(pygame.K_x)                             # ...then salvages
        self.assertEqual(prog.gear.bag, [])
        self.assertEqual(s.stats.loot, loot + 20)
        self.key(pygame.K_TAB)
        self.assertIsNone(s.overlay)

    def test_no_wearing_inside_an_arena(self):
        from ascii_adventurers.systems import mount
        s = self.s
        prog = s.me.progress
        prog.gear.bag = [Piece("seeker", "common")]
        orig = mount.in_arena
        mount.in_arena = lambda scene, hero: True
        try:
            s._cards(s.me, ("wear", 0, "main"))
        finally:
            mount.in_arena = orig
        self.assertNotIn("main", prog.gear.worn)
        s._cards(s.me, ("wear", 0, "main"))
        self.assertEqual(prog.gear.worn["main"].key, "seeker")

    def test_hud_row_and_the_run_end_salvages_the_bag(self):
        s = self.s
        prog = s.me.progress
        prog.gear.take(Offer("seeker", "rare", (), "new"))
        prog.gear.worn["main"].level = 3
        prog.gear.bag = [Piece("resonance", "epic", 1)]
        row = s._gear_row(s.me)
        self.assertEqual(row[0], ("M", 3, "rare"))
        self.assertEqual(row[1], ("O", None, None))
        self.assertEqual(len(row), 10)
        loot = s.stats.loot
        s._end_run()
        self.assertEqual(s.stats.loot, loot + 240)      # epic 160 x 1.5
        self.assertEqual(s.stats.gear, ["Wyrmseeker Staff +3"])


class DrawTest(unittest.TestCase):
    def fits(self, overlay_for, rows=30):
        from engine import Display
        for cols in (80, 115, 128, 172):
            d = Display(cols, rows)
            calls = []

            class Rec:
                display = d

                def put(self, col, row, s, *a, **k):
                    calls.append((col, row, s))

            class M:
                display = d

            overlay_for(M()).draw(Rec())
            self.assertLessEqual(max(c + len(s) for c, _, s in calls), cols, cols)
            self.assertGreaterEqual(min(c for c, _, _ in calls), 0, cols)
            self.assertLess(max(r for _, r, _ in calls), rows, cols)
            yield " ".join(s for _, _, s in calls)

    def test_picker_fits_every_screen(self):
        from ascii_adventurers.players.progress import Progress
        prog = Progress(picks=3)
        prog.gear.take(Offer("seeker", "common", (), "new"))
        prog.offer = [Offer("kindling", "epic", ("sharpened", "iron_skin", "keen_eye"), "new"),
                      Offer("resonance", "rare", ("quick_hands",), "swap"),
                      Offer("seeker", "common", (), "plus")]
        for text in self.fits(lambda m: gear_picker.GearPicker(m, prog, lambda a: None)):
            for s in ("(+2 more)", "EPIC", "UPGRADE", "REROLL 3", "BANISH 0", "SKIP", "wearing:",
                      "EMPTY", "+0 -> +1"):
                self.assertIn(s, text)

    def test_gear_screen_fits_every_screen(self):
        from ascii_adventurers.players.progress import Progress
        prog = Progress()
        prog.gear = wearing(Piece("seeker", "rare", 3, ("sharpened", "keen_eye")),
                            Piece("volatile", "uncommon"), Piece("daggers", "epic", 5), trinkets=4)
        prog.gear.bag = [Piece("resonance", "rare")]
        for mode in ("browse", "upgrade", "drop"):
            for text in self.fits(lambda m: gear_screen.GearScreen(
                    m, prog, mode, outgoing=prog.gear.worn["main"]), rows=24):
                self.assertIn("RING", text)
