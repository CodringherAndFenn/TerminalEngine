"""M20: the wizard's arcane missiles, his redone cards, Chain Lightning as
his spell, and the trainer's lightning ladders refunded."""

import json
import math
import os
import tempfile
import unittest
from collections import Counter

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.meta.guild import VERSION, Guild
from ascii_adventurers.players import cards
from ascii_adventurers.systems import combat
from ascii_adventurers.tests.test_m14 import carded
from ascii_adventurers.tests.test_m16 import SpellRev2Test, fly
from ascii_adventurers.tests.test_weapons import Dummy, open_map


def cast(h, aim, world=None):
    """The wizard aims at world point `aim` and casts once."""
    h.aim_at(*aim, 1 / 60)
    shots = []
    combat.fire(h, world or open_map(), shots, [])
    return shots


class MissileTest(unittest.TestCase):
    def test_three_darts_fan_then_home_on_the_reticle(self):
        h = carded("wizard")
        target = Dummy(22, 10.5, hp=5000)
        decoy = Dummy(14, 16.5, hp=5000)            # nearer the wizard, far from the aim
        shots = cast(h, (22, 10.5))
        self.assertEqual(len(shots), 3)
        self.assertGreater(max(p.angle for p in shots) - min(p.angle for p in shots), 0.5)
        fly(shots, [h, target, decoy], steps=90)
        self.assertAlmostEqual(5000 - target.hp, 3 * 9)
        self.assertEqual(decoy.hp, 5000)

    def test_no_target_near_the_aim_flies_straight(self):
        h = carded("wizard")
        shots = cast(h, (30, 10.5))
        before = [p.angle for p in shots]
        fly(shots, [h], steps=20)
        self.assertEqual([p.angle for p in shots], before)

    def test_a_lost_target_is_found_again_with_seeker(self):
        for seeker, expect in ((False, 5000), (True, None)):
            h = carded("wizard", *([("seeker", "common")] if seeker else []))
            first = Dummy(22, 10.5, hp=5000)
            other = Dummy(16, 13.5, hp=5000)
            shots = cast(h, (22, 10.5))
            fly(shots, [h, first, other], steps=8)      # they've picked the first by now
            first.hp = 0                                 # ...which dies
            fly(shots, [h, first, other], steps=90)
            if expect is None:
                self.assertLess(other.hp, 5000)
            else:
                self.assertEqual(other.hp, 5000)

    def test_tracking_and_seeker_turn_faster(self):
        base = config.WEAPONS["arcane_missiles"].shell.seek_turn
        lo = cards.build_loadout("wizard", [("seeker", "common")],
                                 [("seek_turn", "add", 0.2)])
        self.assertAlmostEqual(lo.weapon.shell.seek_turn, base * 1.2 * config.SEEKER)


class DartCardTest(unittest.TestCase):
    def test_resonance(self):
        h = carded("wizard", ("resonance", "uncommon"))
        d = Dummy(22, 10.5, hp=5000)
        fly(cast(h, (22, 10.5)), [h, d], steps=90)
        per = config.RESONANCE[1]
        self.assertAlmostEqual(5000 - d.hp, 9 * (1 + (1 + per) + (1 + 2 * per)))

    def test_mana_burst(self):
        h = carded("wizard", ("mana_burst", "rare"))
        d, near = Dummy(22, 10.5, hp=5000), Dummy(22, 11.3, hp=5000)
        near.hit_radius = 0.1                        # the darts fly past it
        fly(cast(h, (22, 10.5)), [h, d, near], steps=90)
        self.assertLess(near.hp, 5000)

    def test_arcane_storm_three_per_cast(self):
        h = carded("wizard", ("arcane_storm", "legendary"))
        first = Dummy(22, 10.5, hp=1)
        rest = [Dummy(22 + 2 * i, 13.5, hp=1) for i in range(6)]
        shots = cast(h, (22, 10.5))
        fly(shots, [h, first, *rest], steps=200)
        self.assertEqual(sum(not d.alive for d in rest), config.ARCANE_STORM[0])

    def test_orbiting_darts_try_again(self):
        h = carded("wizard", ("orbiting_darts", "rare"))
        behind = Dummy(4, 10.5, hp=5000)             # far from the aim, near the wizard
        fly(cast(h, (40, 10.5), open_map(w=80)), [h, behind], open_map(w=80), steps=200)
        self.assertLess(behind.hp, 5000)
        h = carded("wizard")
        behind = Dummy(4, 10.5, hp=5000)
        fly(cast(h, (40, 10.5), open_map(w=80)), [h, behind], open_map(w=80), steps=200)
        self.assertEqual(behind.hp, 5000)

    def test_overload_has_no_jumps_now(self):
        self.assertFalse(hasattr(config, "OVERLOAD_CHAIN"))
        self.assertEqual(config.CARDS["overload"].text, "every 5th cast: x3 damage")


class ChainLightningTest(unittest.TestCase):
    run_spell = SpellRev2Test.run_spell

    def test_spell_jumps(self):
        h = carded("wizard")
        a, b, c = Dummy(15, 10.5), Dummy(15, 13.5), Dummy(18, 14.5)
        self.run_spell(h, "chain_lightning", [h, a, b, c], 1.2)
        self.assertTrue(all(d.hp < 500 for d in (a, b, c)))

    def test_lightning_cards_need_it(self):
        w = config.WEAPONS["arcane_missiles"]
        plain = cards.eligible("wizard", w, Counter())
        for k in ("storm_caller", "conductor", "supercell", "ball_lightning"):
            self.assertNotIn(k, plain)
        lit = cards.eligible("wizard", w, Counter({"chain_lightning": 1}),
                             cards.hero_stats([("chain_lightning", "uncommon")]))
        for k in ("storm_caller", "conductor", "supercell", "ball_lightning"):
            self.assertIn(k, lit)
        self.assertNotIn("chain_lightning", cards.eligible("bard", config.WEAPONS["lute"],
                                                           Counter()))

    def test_storm_caller_adds_a_jump_to_the_spell(self):
        h = carded("wizard", ("chain_lightning", "uncommon"), ("storm_caller", "rare"))
        dummies = [Dummy(15 + 3 * i, 10.5 + 2 * i) for i in range(5)]
        self.run_spell(h, "chain_lightning", [h, *dummies], 1.2)
        self.assertEqual(sum(d.hp < 500 for d in dummies), 1 + 2 + 1)


class TrainerTest(unittest.TestCase):
    def test_lightning_ladders_are_refunded_once(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "guild.json")
            with open(path, "w") as f:
                json.dump({"version": VERSION, "loot": 100,
                           "heroes": {"wizard": {"forked_bolt": 1, "long_arc": 2,
                                                 "capacitor": 1}}}, f)
            g = Guild.load(path)
            self.assertTrue(g.migrated)
            self.assertEqual(g.loot, 100 + 1200 + 150 + round(150 * 1.3))
            self.assertEqual(g.heroes, {"wizard": {"capacitor": 1}})
            g.save(path)
            again = Guild.load(path)
            self.assertFalse(again.migrated)
            self.assertEqual(again.loot, g.loot)

    def test_extra_dart(self):
        g = Guild(loot=10 ** 6)
        g.buy_upgrade("extra_dart", "wizard")
        lo = cards.build_loadout("wizard", [], g.meta_steps("wizard"))
        self.assertEqual(lo.weapon.pellets, 4)


if __name__ == "__main__":
    unittest.main()
