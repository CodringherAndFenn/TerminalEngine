"""Boss framework rules (2026-10-05, design/BOSSES.md 5.6): predictive aim,
combos, per-phase tells and rests, the global health/damage knobs, the
bigger Lady Proboscia and the 3x leech swarm."""

import math
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.ai import make_enemy
from ascii_adventurers.ai.brain import AIContext
from ascii_adventurers.tests.test_m14 import carded
from ascii_adventurers.tests.test_weapons import open_map


def boss(key="froggy", level=1):
    b = make_enemy(key, 40.0, 15.0, random.Random(3))
    b.scale_to_level(level)
    return b


class LeadTest(unittest.TestCase):
    def test_leads_a_moving_hero_and_not_a_still_one(self):
        b = boss()
        h = carded("bard", x=20.0, y=15.0)
        self.assertEqual(b.lead(h, b.x, b.y, secs=1.0), (h.x, h.y))
        h.vx, h.vy = 0.0, 5.0
        x, y = b.lead(h, b.x, b.y, secs=1.0)
        self.assertAlmostEqual(x, h.x)
        self.assertAlmostEqual(y, h.y + 5.0 * config.BOSS_LEAD)
        # By the shot's flight time: 20 tiles at 10 tiles/s is 2 s.
        x, y = b.lead(h, b.x, b.y, speed=10.0)
        self.assertAlmostEqual(y, h.y + 10.0 * config.BOSS_LEAD)
        # Never more than BOSS_LEAD_MAX tiles ahead.
        x, y = b.lead(h, b.x, b.y, secs=100.0)
        self.assertAlmostEqual(y - h.y, config.BOSS_LEAD_MAX)
        self.assertAlmostEqual(b.aim(h, b.x, b.y, lead=False), math.pi)

    def test_fan_volleys_after_the_first_lead(self):
        b = boss()
        h = carded("bard", x=20.0, y=15.0)
        h.vx, h.vy = 0.0, 6.0
        ctx = AIContext(open_map(w=80), [h], [h, b], [], [])
        b.ctx = ctx
        b._start("fan")
        b.tgt = h
        angles = []
        for _ in range(400):
            n = len(ctx.projectiles)
            b.think(ctx, 1 / 60)
            if len(ctx.projectiles) > n:
                shots = ctx.projectiles[n:]
                angles.append(sum(p.angle for p in shots) / len(shots))
            if b.move is None:
                break
        self.assertEqual(len(angles), config.FROGGY_FAN[2])
        self.assertAlmostEqual(angles[0] % math.tau, b.aim(h, *b.mouth, lead=False) % math.tau,
                               delta=0.2)
        self.assertNotAlmostEqual(angles[1], angles[0], delta=0.05)   # led down the hero's path


class PaceTest(unittest.TestCase):
    def test_tells_shrink_by_phase_with_a_floor(self):
        b = boss()
        self.assertEqual(b.tell_s(0.6), 0.6)
        b.phase = 2
        self.assertAlmostEqual(b.tell_s(1.0), 1.0 * config.BOSS_TELL_SCALE[2])
        self.assertEqual(b.tell_s(0.35), config.BOSS_MIN_TELL)
        self.assertEqual(b.tell_s(0.2), 0.2)            # never made longer

    def test_rests_and_combos(self):
        b = boss()
        b.move = "fan"
        b._end_move()
        self.assertEqual(b._rest, b.bspec.phases[0].rest)   # phase 1: no combos
        b.phase = 2
        chance, most = config.BOSS_COMBO[2]
        b.rng.random = lambda: 0.0                          # always combo...
        for k in range(most):
            b.move = "fan"
            b._end_move()
            self.assertEqual(b._rest, config.BOSS_COMBO_GAP)
            self.assertEqual(b.combo, k + 1)
        b.move = "fan"
        b._end_move()                                       # ...but at most `most` in a row
        self.assertEqual(b.combo, 0)
        self.assertAlmostEqual(b._rest, b.bspec.phases[2].rest * config.BOSS_REST_SCALE[2])


class KnobTest(unittest.TestCase):
    def tearDown(self):
        config.BOSS_HP_MULT, config.BOSS_DMG_MULT = self.saved

    def setUp(self):
        self.saved = config.BOSS_HP_MULT, config.BOSS_DMG_MULT

    def test_health_and_damage_knobs(self):
        config.BOSS_HP_MULT, config.BOSS_DMG_MULT = 1.0, 1.0
        plain = boss(level=5)
        config.BOSS_HP_MULT, config.BOSS_DMG_MULT = 2.0, 1.5
        tough = boss(level=5)
        self.assertAlmostEqual(tough.max_hp / plain.max_hp, 2.0, delta=0.01)
        self.assertAlmostEqual(tough.damage_mult / plain.damage_mult, 1.5)
        swarm = boss("leech_swarm", level=5)
        self.assertAlmostEqual(sum(p.max_hp for p in swarm.parts), swarm.max_hp)


class BodyTest(unittest.TestCase):
    def test_the_lady_is_big(self):
        b = boss("proboscia")
        self.assertEqual(b.hit_radius, config.PROBOSCIA_HIT_RADIUS)
        self.assertGreater(math.hypot(b.nose[0] - b.x, b.nose[1] - b.y), 2.5)

    def test_leeches_crawl_over_each_other(self):
        b = boss("leech_swarm")
        self.assertEqual(len(b.parts), 120)
        h = carded("bard", x=10.0, y=15.0)
        ctx = AIContext(open_map(w=80), [h], [h, b] + b.parts, [], [])
        b.ctx = ctx
        a, c = b.parts[0], b.parts[1]
        a.x, a.y = c.x, c.y = 40.0, 15.0
        a.goal = c.goal = (40.0, 15.0)
        b.mode = "whirl"                                    # (no wander in the whirlpool)
        b._move(1 / 60)
        self.assertAlmostEqual(a.x, c.x)                    # nothing pushes them apart
        self.assertAlmostEqual(a.y, c.y)


if __name__ == "__main__":
    unittest.main()
