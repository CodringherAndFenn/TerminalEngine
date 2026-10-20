"""M28.3k: the dwarf's and the huntress's main hands' legendary tricks
(design/GEAR.md 19.9)."""

import math
import os
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.players import gear
from ascii_adventurers.render.ascii_fx import draw_projectiles
from ascii_adventurers.render.spell_fx import draw_overcast
from ascii_adventurers.systems import combat
from ascii_adventurers.tests.test_m28_2a import foe
from ascii_adventurers.tests.test_m28_2c import DT
from ascii_adventurers.tests.test_m28_2h import DWARF, STRIKE, _Main, victims
from ascii_adventurers.tests.test_m28_3c import BASE, _Legend
from ascii_adventurers.tests.test_weapons import open_map

PIECES = ("ricochet", "hang_time", "homeward_fury", "tether", "splitting_axe", "arrow_rain",
          "broadhead", "hunters_mark", "steady_aim", "split_arrow")


class _Hand(_Legend):
    shot, hit, fly = _Main.shot, _Main.hit, _Main.fly

    def setup(self, key, rarity="legendary", *more, walls=()):
        s, h = super().setup(key, rarity, *more, hero="dwarf" if key in DWARF else "huntress")
        if walls:
            s.world = open_map(80, 40, walls)
        return s, h


class FrameworkTest(unittest.TestCase):
    def test_every_dwarf_and_huntress_main_hand_has_its_legendary_trick(self):
        hands = [k for k, g in config.GEAR.items() if g.slot == "main"
                 and config.CARDS[k].heroes in (("dwarf",), ("huntress",))]
        self.assertEqual(sorted(hands), sorted(PIECES + ("cyclone", "deadeye")))
        for key in PIECES:
            name, text = gear.legendary_trick(key)
            self.assertTrue(name and text and text.isascii(), key)


class TrickShotTest(_Hand):
    def bounce(self, rarity):
        s, h = self.setup("ricochet", rarity, walls=[(24, y) for y in range(10, 31)])
        target = self.place(foe(21.5, 25.0, BASE))[0]
        p = self.shot()
        p.max_range = 100.0
        with mock.patch(STRIKE) as hit:
            self.fly([p], 0.6)
        return p, target, victims(hit)

    def test_a_bounce_goes_for_the_nearest_enemy(self):
        p, target, hit = self.bounce("legendary")
        self.assertEqual(p.bounces, 1)
        self.assertIn(target, hit)

    def test_off_the_mirror_angle_without_the_trick(self):
        p, target, hit = self.bounce("epic")
        self.assertNotIn(target, hit)

    def test_with_nobody_in_sight_it_glances_as_before(self):
        walls = [(24, y) for y in range(10, 31)] + [(x, 23) for x in range(19, 24)]
        s, h = self.setup("ricochet", walls=walls)
        self.place(foe(21.5, 25.0, BASE))                         # (behind a wall)
        p = self.shot()
        p.max_range = 100.0
        for _ in range(30):
            self.fly([p], DT)
            if p.bounces:
                break
        self.assertEqual(p.bounces, 1)
        self.assertAlmostEqual(p.dir_x, -1.0)


class DriftingSawTest(_Hand):
    def drift(self, rarity, seconds=1.0):
        s, h = self.setup("hang_time", rarity)
        p = self.shot(x=25.0)
        p.hang, p.hung, p.hang_tick = 5.0, True, 1.0
        e = self.place(foe(25.0, 26.0, BASE))[0]
        with mock.patch(STRIKE):
            self.fly([p], seconds)
        return p, e

    def test_the_hovering_axe_drifts_after_the_nearest_enemy(self):
        p, e = self.drift("legendary")
        self.assertAlmostEqual(p.y - 20.5, config.DRIFTING_SAW, places=2)
        self.assertAlmostEqual(p.x, 25.0)

    def test_it_stops_at_its_body_and_stays_put_without_the_trick(self):
        p, e = self.drift("legendary", seconds=4.0)
        self.assertAlmostEqual(e.y - p.y, e.hit_radius, places=2)
        p, e = self.drift("epic")
        self.assertEqual((p.x, p.y), (25.0, 20.5))


class SteeredTest(_Hand):
    def back(self, rarity, aim=(26.0, 26.0)):
        s, h = self.setup("homeward_fury", rarity)
        h.aim_point = aim
        p = self.shot(x=30.0)
        combat._turn_back(p, [])
        passed = math.inf
        for _ in range(120):
            self.fly([p], DT)
            passed = min(passed, math.hypot(p.x - aim[0], p.y - aim[1]))
            if not p.alive:
                break
        return p, passed

    def test_the_way_back_goes_through_your_aim(self):
        p, passed = self.back("legendary")
        self.assertLessEqual(passed, config.STEERED + 0.4)
        self.assertFalse(p.alive)                          # (and on home, caught)

    def test_straight_home_without_the_trick(self):
        p, passed = self.back("epic")
        self.assertGreater(passed, 4.0)
        self.assertFalse(p.alive)

    def test_it_never_steers_for_ever(self):
        s, h = self.setup("homeward_fury")
        p = self.shot(x=30.0)
        combat._turn_back(p, [])
        for k in range(600):
            h.aim_point = (30.0 + 10 * math.cos(k * 0.05), 20.5 + 10 * math.sin(k * 0.05))
            self.fly([p], DT)
            if not p.alive:
                break
        self.assertFalse(p.alive)
        self.assertLess(p.travelled, p.max_range * config.RETURN_GIVE_UP)   # (caught, not lost)


class ChainGangTest(_Hand):
    def gang(self, rarity):
        s, h = self.setup("tether", rarity)
        a, b = self.shot(x=26.0, y=17.0), self.shot(x=26.0, y=24.0)
        a.dir_x = b.dir_x = 0.0                            # (hold them still in the air)
        a.spec = b.spec = h.weapon.spec.shell
        between = self.place(foe(26.0, 20.5, BASE))[0]
        shots = [a, b]
        with mock.patch.object(combat, "_tether"), mock.patch(STRIKE) as hit:
            combat._chain_gang(shots, s._actors(), s.effects, DT)
        return between, victims(hit), hit

    def test_a_chain_between_two_axes_cuts_what_it_crosses(self):
        between, hit, call = self.gang("legendary")
        self.assertEqual(hit, [between])
        self.assertAlmostEqual(call.call_args.args[1], 20.0 * config.TETHER[2])
        self.assertFalse(call.call_args.kwargs["on_hit"])

    def test_not_without_the_trick(self):
        self.assertEqual(self.gang("epic")[1], [])

    def test_the_chains_draw(self):
        s, h = self.setup("tether")
        shots = [self.shot(x=26.0, y=17.0), self.shot(x=26.0, y=24.0)]
        self.assertEqual(len(combat.chain_links(shots)), 1)
        draw_projectiles(s.manager.text, s.me.camera, shots)


class WideArcTest(_Hand):
    def widest(self, rarity, level=0):
        s, h = self.setup("splitting_axe", rarity, *((("splitting_axe", level),) if level else ()))
        p = self.shot(x=31.5, damage=100.0)
        pieces = []
        combat._turn_back(p, pieces)
        for q in pieces:
            q.pieces = None
        most = [0.0] * len(pieces)
        for _ in range(90):
            self.fly(list(pieces), DT)
            for i, q in enumerate(pieces):
                if q.alive:
                    most[i] = max(most[i], abs(q.y - h.y))
        return most, pieces

    def test_the_halves_swing_out_wide(self):
        most, pieces = self.widest("legendary")
        for m in most:
            self.assertAlmostEqual(m, config.WIDE_ARC, delta=0.3)
        self.assertFalse(any(q.alive for q in pieces))     # (home all the same)

    def test_straight_home_without_the_trick(self):
        most, _ = self.widest("epic")
        self.assertLess(max(most), config.SPLITTING_AXE[1])


class OvercastTest(_Hand):
    def test_where_it_rained_it_keeps_raining(self):
        s, h = self.setup("arrow_rain")
        h.aim_point = (30.0, 20.5)
        s.rules._arrow_rain(h, {"mult": 1.0})
        first = len(s.projectiles)
        s.projectiles.clear()
        for _ in range(round(config.OVERCAST[0] * 60) + 30):
            s.rules.tick(s.me, DT)
        seconds, rate = config.OVERCAST
        self.assertEqual(len(s.projectiles), round(seconds * rate))
        for q in s.projectiles:
            self.assertLessEqual(math.hypot(q.target[0] - 30.0, q.target[1] - 20.5),
                                 config.ARROW_RAIN[2] + 1e-6)
        self.assertEqual(h.overcast, [])
        self.assertGreater(first, 0)

    def test_once_without_the_trick_and_not_twice_with_squall_line(self):
        s, h = self.setup("arrow_rain", "epic")
        s.rules._arrow_rain(h, {"mult": 1.0})
        self.assertEqual(h.overcast, [])
        s, h = self.setup("arrow_rain")
        s.rules._arrow_rain(h, {"mult": 1.0})
        s.rules._arrow_rain(h, {"mult": 1.0}, hold=0.4)
        self.assertEqual(len(h.overcast), 1)

    def test_the_cloud_draws(self):
        s, h = self.setup("arrow_rain")
        s.rules._arrow_rain(h, {"mult": 1.0})
        draw_overcast(s.manager.text, s.me.camera, s.players, 3)


class WideningTest(_Hand):
    def test_each_enemy_passed_widens_it(self):
        s, h = self.setup("broadhead")
        self.place(foe(24.0, 20.5, BASE), foe(27.0, 20.5, BASE))
        p = self.shot()
        p.pierce_left = 4
        with mock.patch(STRIKE):
            self.fly([p], 0.2)
        self.assertAlmostEqual(p.size, 2 * config.WIDENING)
        draw_projectiles(s.manager.text, s.me.camera, [p])

    def test_wider_it_hits_what_it_would_have_missed(self):
        for rarity, reached in (("legendary", True), ("epic", False)):
            s, h = self.setup("broadhead", rarity)
            line = self.place(foe(24.0, 20.5, BASE), foe(26.0, 20.5, BASE),
                              foe(29.0, 20.5 + 0.45 + 0.4, BASE))   # (just off its path)
            p = self.shot()
            p.pierce_left = 4
            with mock.patch(STRIKE) as hit:
                self.fly([p], 0.3)
            self.assertEqual(line[2] in victims(hit), reached, rarity)


class CalledShotTest(_Hand):
    def test_a_roll_marks_the_enemy_nearest_your_aim(self):
        s, h = self.setup("hunters_mark")
        tough, aimed = self.place(foe(26.0, 22.0, 900.0), foe(24.0, 18.0, 100.0))
        h.aim_point = (24.5, 18.0)
        s.me.mark_timer = 5.0
        h.marked = tough
        h.rolls += 1
        s._hunters_mark(s.me, DT)
        self.assertIs(h.marked, aimed)
        self.assertAlmostEqual(s.me.mark_timer, config.MARK_INTERVAL)   # (the next mark)
        s._hunters_mark(s.me, DT)                          # (once a roll)
        self.assertIs(h.marked, aimed)

    def test_not_without_the_trick(self):
        s, h = self.setup("hunters_mark", "epic")
        tough, aimed = self.place(foe(26.0, 22.0, 900.0), foe(24.0, 18.0, 100.0))
        h.aim_point = (24.5, 18.0)
        s.me.mark_timer = 5.0
        h.marked = tough
        h.rolls += 1
        s._hunters_mark(s.me, DT)
        self.assertIs(h.marked, tough)


class CurrentTest(_Hand):
    def walk(self, rarity, seconds, turn=0.0):
        s, h = self.setup("steady_aim", rarity)
        for k in range(round(seconds * 60)):
            a = turn * k * DT
            h.vx, h.vy = 5.0 * math.cos(a), 5.0 * math.sin(a)
            s.rules.tick(s.me, DT)
        return combat.steady(h)

    def test_a_straight_line_counts_as_standing_still(self):
        self.assertFalse(self.walk("legendary", config.STILL_CURRENT[0] - 0.2))
        self.assertTrue(self.walk("legendary", config.STILL_CURRENT[0] + 0.1))

    def test_not_turning_nor_without_the_trick(self):
        self.assertFalse(self.walk("legendary", 3.0, turn=1.0))     # (a circle: 57 deg/s)
        self.assertFalse(self.walk("epic", 3.0))


class RecurveTest(_Hand):
    def split(self, rarity):
        s, h = self.setup("split_arrow", rarity)
        p = self.shot(x=24.0)
        victim = self.place(foe(24.0, 20.5, BASE))[0]
        spawned = []
        combat._split_arrow(p, victim, 24.0, 20.5, h.stats, spawned, s._actors())
        return s, h, spawned, victim

    def test_split_arrows_come_back_toward_you(self):
        s, h, spawned, _ = self.split("legendary")
        far = [0.0] * len(spawned)
        shots = list(spawned)
        for _ in range(60):
            self.fly(shots, DT)
            for i, c in enumerate(spawned):
                far[i] = max(far[i], math.hypot(c.x - h.x, c.y - h.y))
        self.assertFalse(any(c.alive for c in spawned))       # (they reached you)
        for c, f in zip(spawned, far):
            self.assertLess(f, 3.5 + config.RECURVE[0] + 2 * math.pi * 45 / config.RECURVE[1])
            self.assertLessEqual(math.hypot(c.x - h.x, c.y - h.y), config.RECURVE[2] + 1.0)

    def test_sweeping_the_way_back(self):
        s, h, spawned, victim = self.split("legendary")
        c = spawned[0]
        spot = None
        for _ in range(60):                                    # (where it flies on the way back)
            self.fly([c], DT)
            if c.recurve == "back" and spot is None and math.hypot(c.x - h.x, c.y - h.y) < 2.5:
                spot = (c.x, c.y)
        s, h, spawned, victim = self.split("legendary")
        back = self.place(foe(spot[0], spot[1], BASE))[0]
        with mock.patch(STRIKE) as hit:
            self.fly([spawned[0]], 1.0)
        self.assertIn(back, victims(hit))

    def test_outward_without_the_trick(self):
        s, h, spawned, _ = self.split("epic")
        self.fly(list(spawned), 0.3)
        self.assertTrue(all(math.hypot(c.x - h.x, c.y - h.y) > 8.0 or not c.alive
                            for c in spawned))
        self.assertTrue(all(c.recurve is False for c in spawned))


if __name__ == "__main__":
    unittest.main()
