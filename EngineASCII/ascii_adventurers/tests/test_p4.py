"""P4 (playtest pass, 2026-10-10): the card dedupe. Eight hero cards that
did what a general card does were cut, each replaced in its slot by a card
only that hero could have: Hang Time, Tether and Splitting Axe (dwarf),
Converge and Pirouette (princess), Arrow Rain (huntress), Phase Darts and
Implosion (wizard)."""

import json
import math
import os
import random
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.meta.guild import VERSION, Guild
from ascii_adventurers.systems import combat
from ascii_adventurers.tests.test_m14 import carded
from ascii_adventurers.tests.test_m16 import fly, game, take
from ascii_adventurers.tests.test_m18 import _Scene, press
from ascii_adventurers.tests.test_m20 import cast
from ascii_adventurers.tests.test_weapons import Dummy, open_map

CUT = ("heavy_axe", "cleave", "twin_axes", "double_rainbow", "prism_dash", "volley",
       "overload", "mana_burst")
NEW = {"hang_time": ("dwarf", "D2"), "tether": ("dwarf", "D4"),
       "splitting_axe": ("dwarf", "D7"), "converge": ("princess", "P7"),
       "pirouette": ("princess", "P6"), "arrow_rain": ("huntress", "H1"),
       "phase_darts": ("wizard", "W4"), "implosion": ("wizard", "W10")}


def throw(h, world, actors, seconds):
    """The dwarf throws once (aiming +x); then `seconds` of flight."""
    shots = []
    combat.fire(h, world, shots, [])
    fly(shots, actors, world, steps=round(seconds * 60))
    return shots


class CatalogTest(unittest.TestCase):
    def test_the_doubles_are_gone_and_their_slots_filled(self):
        for key in CUT:
            self.assertNotIn(key, config.CARDS)
        for key, (hero, code) in NEW.items():
            c = config.CARDS[key]
            self.assertEqual((c.heroes, c.code), ((hero,), code), key)
        codes = [c.code for c in config.CARDS.values() if c.code]
        self.assertEqual(len(codes), len(set(codes)))       # one card per code

    def test_every_hero_keeps_as_many_cards(self):
        # (One replacement per cut: the wizard has 12 since M20, the rest 7.)
        for hero in config.HEROES:
            own = [k for k, c in config.CARDS.items() if c.heroes == (hero,)]
            self.assertEqual(len(own), 12 if hero == "wizard" else 7, (hero, own))

    def test_archetypes_follow_the_new_cards(self):
        a = config.ARCHETYPES
        self.assertNotIn("W4", a["crit"])                  # Phase Darts isn't a crit card
        self.assertNotIn("D4", a["bleed"])                 # Tether doesn't bleed
        self.assertNotIn("D2", a["sniper"])
        for code in ("D2", "D4", "H1", "W10"):
            self.assertIn(code, a["area"])
        known = {c.code for c in config.CARDS.values()}
        for name, codes in a.items():
            self.assertTrue(set(codes) <= known, name)

    def test_a_bought_overload_becomes_phase_darts(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "guild.json")
            with open(path, "w") as f:
                json.dump({"version": VERSION, "loot": 5, "cards": ["overload"]}, f)
            g = Guild.load(path)
        self.assertEqual(g.cards, {"phase_darts"})
        self.assertTrue(g.unlocked("phase_darts"))
        self.assertEqual(config.CARDS["phase_darts"].unlock, "L:2000")   # Overload's price


class DwarfTest(unittest.TestCase):
    def test_hang_time_hovers_and_hits_again(self):
        world = open_map()
        dealt = {}
        for card in ((), (("hang_time", "rare"),)):
            h = carded("dwarf", *card)
            d = Dummy(21.4, 10.5, hp=5000)
            d.hit_radius = 0.8
            shots = throw(h, world, [h, d], 1.6)
            dealt[bool(card)] = 5000 - d.hp
            self.assertEqual(shots, [])                     # it came home
        self.assertGreaterEqual(dealt[True], dealt[False] + 2 * 22 - 1e-6)

    def test_hang_time_longer_with_copies(self):
        h = carded("dwarf", *[("hang_time", "rare")] * 3)
        shots = throw(h, open_map(), [h], 0.55)
        self.assertEqual(len(shots), 1)
        self.assertTrue(shots[0].hung)
        self.assertAlmostEqual(shots[0].hang + 0.55 - 0.5, 0.8, delta=0.06)
        x = shots[0].x
        fly(shots, [h], steps=20)
        self.assertEqual(shots[0].x, x)                     # still hovering

    def test_hang_time_hovers_at_a_wall_too(self):
        world = open_map(walls=[(16, y) for y in range(30)])
        h = carded("dwarf", ("hang_time", "rare"))
        shots = throw(h, world, [h], 0.35)
        self.assertEqual(len(shots), 1)
        self.assertTrue(shots[0].hung and shots[0].hang > 0)
        self.assertLess(shots[0].x, 16.0)                   # in front of the wall

    def test_tether_cuts_what_the_chain_crosses(self):
        world = open_map()
        dealt = {}
        for card in ((), (("tether", "uncommon"),)):
            h = carded("dwarf", *card)
            d = Dummy(13.0, 10.5, hp=5000)
            throw(h, world, [h, d], 1.6)
            dealt[bool(card)] = 5000 - d.hp
            self.assertEqual(h.hp, h.max_hp)                # (never the dwarf himself)
        self.assertGreater(dealt[True], dealt[False])

    def test_splitting_axe_comes_home_in_two(self):
        h = carded("dwarf", ("splitting_axe", "rare"))
        shots = throw(h, open_map(), [h], 0.55)
        self.assertEqual(len(shots), 2)
        self.assertTrue(all(p.returning and p.halved for p in shots))
        damage = config.WEAPONS["throwing_axe"].shell.damage * config.SPLITTING_AXE[0]
        self.assertTrue(all(abs(p.damage - damage) < 1e-6 for p in shots))
        a, b = shots
        self.assertAlmostEqual(math.hypot(a.x - b.x, a.y - b.y), config.SPLITTING_AXE[1],
                               delta=0.5)
        fly(shots, [h], steps=90)
        self.assertEqual(shots, [])                         # both caught


class PrincessTest(unittest.TestCase):
    def test_converge_crosses_at_the_aim(self):
        target = (19.5, 10.5)
        for card, closest in (((), 1.0), ((("converge", "rare"),), 0.35)):
            h = carded("princess", *card)
            h.aim_at(*target, 1 / 60)
            shots = []
            combat.fire(h, open_map(), shots, [])
            near = {id(p): math.inf for p in shots}
            for _ in range(40):
                combat.update_projectiles(shots, open_map(), [], 1 / 60, [h])
                for p in shots:
                    near[id(p)] = min(near[id(p)], math.hypot(p.x - target[0], p.y - target[1]))
            if card:
                self.assertLess(max(near.values()), closest)        # every color passes there
            else:
                self.assertGreater(max(near.values()), closest)     # the edges miss wide

    def test_converge_puts_every_color_on_one_enemy(self):
        h = carded("princess", ("converge", "rare"))
        d = Dummy(19.5, 10.5, hp=5000)
        h.aim_at(d.x, d.y, 1 / 60)
        shots = []
        combat.fire(h, open_map(), shots, [])
        fly(shots, [h, d], steps=60)
        self.assertAlmostEqual(5000 - d.hp, 5 * 8)

    def test_pirouette_spins_a_ring(self):
        h = carded("princess", ("pirouette", "uncommon"))
        sc = _Scene(h)
        sc.run(1 / 60, first=press(1, 0))
        n = config.PIROUETTE[0]
        self.assertEqual(len(sc.projectiles), n)
        angles = sorted((p.angle - h.aim_angle) % math.tau for p in sc.projectiles)
        gaps = [b - a for a, b in zip(angles, angles[1:])]
        self.assertTrue(all(abs(g - math.tau / n) < 1e-6 for g in gaps))
        self.assertEqual({p.variant % 5 for p in sc.projectiles}, set(range(5)))   # all colors


class HuntressTest(unittest.TestCase):
    def test_arrow_rain_every_fifth_shot(self):
        m, s = game("huntress")
        take(s, ("arrow_rain", "epic"))
        h = s.hero
        aim = (h.x + 12, h.y)
        h.aim_at(*aim, 1 / 60)
        every, count, radius, _ = config.ARROW_RAIN
        rained = []
        for n in range(1, 2 * every + 1):
            h.attacks = n
            before = len(s.projectiles)
            s.rules.patterns(s.me, {"mult": 1.0, "extra_chain": 0})
            rained.append(len(s.projectiles) - before)
        self.assertEqual(rained, [0] * (every - 1) + [count] + [0] * (every - 1) + [count])
        for p in s.projectiles:
            self.assertEqual(p.spec.look, "rain_arrow")
            self.assertLessEqual(math.hypot(p.target[0] - aim[0], p.target[1] - aim[1]),
                                 radius + 1e-6)

    def test_rain_lands_on_what_is_under_it(self):
        m, s = game("huntress")
        take(s, ("arrow_rain", "epic"))
        h = s.hero
        h.stats.crit_chance = 0.0
        d = Dummy(h.x + 12, h.y, hp=5000)
        d.hit_radius = config.ARROW_RAIN[2] + 0.5          # under every arrow
        h.aim_at(d.x, d.y, 1 / 60)
        h.attacks = config.ARROW_RAIN[0]
        s.projectiles.clear()
        s.rules.patterns(s.me, {"mult": 1.0, "extra_chain": 0})
        rain = list(s.projectiles)
        fly(rain, [h, d], open_map(w=200, h=200), steps=120)
        self.assertEqual(rain, [])
        per = config.WEAPONS["longbow"].shell.damage * config.ARROW_RAIN[3]
        self.assertAlmostEqual(5000 - d.hp, config.ARROW_RAIN[1] * per, delta=1.0)

    def test_more_projectiles_more_rain(self):
        m, s = game("huntress")
        take(s, ("arrow_rain", "epic"), ("multishot", "common"))
        s.hero.attacks = config.ARROW_RAIN[0]
        s.projectiles.clear()
        s.rules.patterns(s.me, {"mult": 1.0, "extra_chain": 0})
        self.assertEqual(sum(p.spec.look == "rain_arrow" for p in s.projectiles),
                         config.ARROW_RAIN[1] + 1)


class WizardTest(unittest.TestCase):
    def test_phase_darts_fly_through_walls(self):
        world = open_map(w=40, walls=[(16, y) for y in range(30)])
        for card, hurt in (((), False), ((("phase_darts", "rare"),), True)):
            h = carded("wizard", *card)
            d = Dummy(22, 10.5, hp=5000)
            fly(cast(h, (22, 10.5), world), [h, d], world, steps=90)
            self.assertEqual(d.hp < 5000, hurt)

    def test_implosion_drags_enemies_in(self):
        from ascii_adventurers.ai import make_enemy
        h = carded("wizard", ("implosion", "rare"))
        d = Dummy(22, 10.5, hp=5000)
        e = make_enemy("warrior", 22, 12.5, random.Random(1))
        x0, y0 = e.x, e.y
        fly(cast(h, (22, 10.5)), [h, d, e], steps=90)
        self.assertLess(math.hypot(e.x - d.x, e.y - d.y), math.hypot(x0 - d.x, y0 - d.y) - 0.5)

    def test_implosion_leaves_bosses_put(self):
        from ascii_adventurers.ai import make_enemy
        h = carded("wizard", ("implosion", "rare"))
        d = Dummy(22, 10.5, hp=5000)
        e = make_enemy("warrior", 22, 12.5, random.Random(1))
        e.boss = True
        x0, y0 = e.x, e.y
        fly(cast(h, (22, 10.5)), [h, d, e], steps=90)
        self.assertEqual((e.x, e.y), (x0, y0))


if __name__ == "__main__":
    unittest.main()
