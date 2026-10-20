"""M28.3d: the off-hand's legendary tricks (design/GEAR.md 19.2)."""

import math
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.players import gear
from ascii_adventurers.systems import combat, roll, spells
from ascii_adventurers.tests.test_m28_2c import DT
from ascii_adventurers.tests.test_m28_3c import BASE, _Legend, plain

OFF = ("cross_fire", "starburst", "rear_guard", "spiral", "twin_lanes", "echo", "frenzy",
       "spray_and_pray")


class _Off(_Legend):
    def setup(self, key, rarity="legendary", *more, hero="huntress"):
        s, h = super().setup(key, rarity, *more, hero=hero)
        h.aim_angle = 0.0
        h.aim_point = (h.x + 6.0, h.y)
        return s, h

    def attack(self):
        s = self.s
        before = len(s.projectiles)
        s._attack(s.me)
        return s.projectiles[before:]

    def step(self, seconds):
        s = self.s
        for _ in range(round(seconds * 60)):
            self.h.time += DT
            combat.update_projectiles(s.projectiles, s.world, s.effects, DT, s._actors(), s.zones)
            s.rules.resolve_combos()


class FrameworkTest(unittest.TestCase):
    def test_every_offhand_piece_has_its_legendary_trick(self):
        offs = [k for k, g in config.GEAR.items() if g.slot == "off"]
        self.assertEqual(sorted(offs), sorted(OFF))
        for key in OFF:
            name, text = gear.legendary_trick(key)
            self.assertTrue(name and text and text.isascii(), key)


class WindRoseTest(_Off):
    def test_the_cross_fires_on_its_own(self):
        s, h = self.setup("cross_fire")
        for _ in range(round(config.WIND_ROSE * 60) + 1):
            s.rules.tick(s.me, DT)
        shots = [q for q in s.projectiles if q.owner is h]
        got = sorted(round(math.degrees(q.angle)) % 360 for q in shots)
        self.assertEqual(got, [90, 180, 270])

    def test_not_without_the_trick(self):
        s, h = self.setup("cross_fire", "epic")
        for _ in range(round(config.WIND_ROSE * 60) + 1):
            s.rules.tick(s.me, DT)
        self.assertEqual([q for q in s.projectiles if q.owner is h], [])


class SunspotTest(_Off):
    def test_the_burst_goes_off_from_the_first_enemy_hit(self):
        s, h = self.setup("starburst")
        target = self.place(plain(h.x + 5.0, h.y))[0]
        s.me.burst_meter = config.STARBURST[0] - 1
        shots = self.attack()
        self.assertEqual(len(shots), 1)                   # (no ring from you)
        self.assertIsNotNone(shots[0].sunspot)
        before = list(s.projectiles)
        self.step(0.5)
        ring = [q for q in s.projectiles if q not in before and id(target) in q.hit]
        self.assertEqual(len(ring), config.STARBURST[1])
        self.assertTrue(self.flash_near(target.x, target.y))

    def flash_near(self, x, y):
        return any(e.kind == "nova" and math.hypot(e.x - x, e.y - y) < 1.0 for e in self.s.effects)

    def test_or_where_the_shot_ends(self):
        s, h = self.setup("starburst")
        s.me.burst_meter = config.STARBURST[0] - 1
        arrow = self.attack()[0]
        self.step(3.0)
        self.assertFalse(arrow.alive)
        self.assertTrue(arrow.sunspot["done"])
        self.assertTrue(self.flash_near(arrow.x, arrow.y))

    def test_a_beat_bursts_from_the_nearest_enemy(self):
        s, h = self.setup("starburst", "legendary", ("sheet_music", 0), hero="bard")
        target = self.place(plain(h.x + 1.5, h.y))[0]
        s.me.burst_meter = config.STARBURST[0] - 1
        self.attack()
        ring = [q for q in s.projectiles if q.owner is h and id(target) in q.hit]
        self.assertEqual(len(ring), config.STARBURST[1])

    def test_from_you_without_the_trick(self):
        s, h = self.setup("starburst", "epic")
        s.me.burst_meter = config.STARBURST[0] - 1
        self.assertEqual(len(self.attack()), 1 + config.STARBURST[1])


class FlankingTest(_Off):
    def test_the_rear_shot_comes_from_behind_the_enemy(self):
        s, h = self.setup("rear_guard")
        target = self.place(plain(h.x + 5.0, h.y))[0]
        shots = self.attack()
        back = [q for q in shots if math.cos(q.angle) < -0.5]
        self.assertEqual(len(back), 1)
        self.assertAlmostEqual(back[0].x, target.x + config.FLANKING, places=4)
        self.assertAlmostEqual(back[0].mult, config.REAR_GUARD)

    def test_short_of_a_wall(self):
        s, h = self.setup("rear_guard")
        from ascii_adventurers.tests.test_weapons import open_map
        s.world = open_map(80, 40, [(27, 20)])          # (a wall 1.5 tiles past it)
        self.place(plain(25.5, 20.5))
        back = [q for q in self.attack() if math.cos(q.angle) < -0.5][0]
        self.assertLess(back.x, 27.0)
        self.assertGreater(back.x, 25.5)

    def test_behind_you_with_nobody_there(self):
        s, h = self.setup("rear_guard")
        back = [q for q in self.attack() if math.cos(q.angle) < -0.5][0]
        self.assertLess(math.hypot(back.x - h.x, back.y - h.y), 1.5)

    def test_not_without_the_trick(self):
        s, h = self.setup("rear_guard", "epic")
        self.place(plain(h.x + 5.0, h.y))
        back = [q for q in self.attack() if math.cos(q.angle) < -0.5][0]
        self.assertLess(math.hypot(back.x - h.x, back.y - h.y), 1.5)


class SpiralArmTest(_Off):
    def spiral_shot(self, rarity="legendary"):
        s, h = self.setup("spiral", rarity)
        return [q for q in self.attack() if abs(q.angle) > 1e-6][0]

    def test_it_sweeps_round_you_and_widens(self):
        q = self.spiral_shot()
        h = self.h
        r0, r1, turns, hits = config.SPIRAL_ARM
        self.assertTrue(q.path)
        self.assertGreaterEqual(q.pierce_left, hits - 1)
        swept, last = 0.0, math.atan2(q.y - h.y, q.x - h.x)
        far = 0.0
        shots = [q]
        for _ in range(600):
            combat.update_projectiles(shots, self.s.world, [], DT, [])
            if not q.alive:
                break
            a = math.atan2(q.y - h.y, q.x - h.x)
            swept += (a - last + math.pi) % math.tau - math.pi
            last = a
            far = max(far, math.hypot(q.x - h.x, q.y - h.y))
        self.assertGreater(abs(swept), turns * math.tau * 0.9)
        self.assertAlmostEqual(far, r1, delta=0.6)

    def test_it_goes_through_three(self):
        q = self.spiral_shot()
        foes = [plain(*q.path[k]) for k in (6, 14, 22, 30)]
        shots = [q]
        for _ in range(600):
            combat.update_projectiles(shots, self.s.world, [], DT, foes)
            if not q.alive:
                break
        self.assertEqual([a.hp < BASE for a in foes], [True, True, True, False])

    def test_straight_without_the_trick(self):
        q = self.spiral_shot("epic")
        self.assertFalse(q.path)


class PerfectPairTest(_Off):
    def test_twins_are_whole(self):
        s, h = self.setup("twin_lanes")
        shots = self.attack()
        self.assertEqual(len(shots), 2)
        self.assertTrue(all(q.mult == config.PERFECT_PAIR for q in shots))
        s, h = self.setup("twin_lanes", "epic")
        self.assertTrue(all(q.mult == config.TWIN_LANES[1] for q in self.attack()))


class LastWordTest(_Off):
    def stacks(self, rarity, echo):
        s, h = self.setup("echo", rarity, ("bloodlust", 0))
        e = plain(h.x + 3, h.y)
        e.espec = config.ENEMIES["goblin_archer"]
        e.echo_kill = echo
        e.hp = 0.0
        s.rules.on_kill(s.me, e)
        return len(h.bloodlust)

    def test_an_echo_kill_counts_twice(self):
        self.assertEqual(self.stacks("legendary", True), config.LAST_WORD)
        self.assertEqual(self.stacks("legendary", False), 1)
        self.assertEqual(self.stacks("epic", True), 1)

    def test_the_bookkeeping_counts_once(self):
        s, h = self.setup("echo")
        e = plain(h.x + 3, h.y)
        e.espec = config.ENEMIES["goblin_archer"]
        e.echo_kill = True
        s.rules.on_kill(s.me, e)
        self.assertEqual(len(s.me.kill_times), 1)


class WarpathTest(_Off):
    def frenzy(self, rarity):
        s, h = self.setup("frenzy", rarity)
        e = plain(h.x + 3, h.y)
        e.espec = config.ENEMIES["goblin_archer"]
        s.rules.on_kill(s.me, e)
        s.rules.tick(s.me, DT)
        return s, h

    def test_spells_summons_and_rolls_run_double(self):
        s, h = self.frenzy("legendary")
        self.assertTrue(h.warpath)
        self.assertEqual(spells.haste(h), config.WARPATH)
        h.roll_charges, h.roll_recharge = 0, 0.0
        roll.recharge(h, 0.5)
        self.assertAlmostEqual(h.roll_recharge, 0.5 * config.WARPATH)
        s.me.frenzy = 0.0
        s.rules.tick(s.me, DT)
        self.assertFalse(h.warpath)                       # (the frenzy's over)

    def test_a_spell_comes_twice_as_often(self):
        s, h = self.frenzy("legendary")
        st = spells.SpellState("fire_wand")
        st.params = {"interval": 1.0}
        st.timer = 1.0
        self.assertFalse(spells._due(h, st, 0.4))
        self.assertTrue(spells._due(h, st, 0.1))           # (0.5 s x 2)

    def test_not_without_the_trick(self):
        s, h = self.frenzy("epic")
        self.assertEqual(spells.haste(h), 1.0)


class HairTriggerTest(_Off):
    def test_an_attack_splits_the_shots_in_flight(self):
        s, h = self.setup("spray_and_pray")
        first = self.attack()[0]
        self.step(0.05)                                   # (not half way yet)
        self.assertTrue(first.alive)
        self.attack()
        self.assertFalse(first.alive)
        halves = [q for q in s.projectiles if q.gen == 1 and q.alive]
        self.assertEqual(len(halves), 2)

    def test_pieces_split_too_down_to_eighths(self):
        s, h = self.setup("spray_and_pray")
        self.attack()
        for _ in range(config.HAIR_TRIGGER + 2):
            self.step(0.02)
            self.attack()
        gens = {q.gen for q in s.projectiles if q.alive}
        self.assertIn(config.HAIR_TRIGGER, gens)
        self.assertLessEqual(max(gens), config.HAIR_TRIGGER)

    def test_not_without_the_trick(self):
        s, h = self.setup("spray_and_pray", "epic")
        first = self.attack()[0]
        self.step(0.05)
        self.attack()
        self.assertTrue(first.alive)


if __name__ == "__main__":
    unittest.main()
