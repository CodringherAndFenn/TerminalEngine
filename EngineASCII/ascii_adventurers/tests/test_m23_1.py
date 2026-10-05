"""M23.1: the desert's first boss, Khepri the Dung Emperor (a dung beetle
whose ball grows as it rolls and shatters on pillars), the golden scarab
hunt, scarab adds, and the desert's camp and arena."""

import math
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.ai import make_enemy
from ascii_adventurers.ai.bosses import Khepri
from ascii_adventurers.ai.brain import AIContext
from ascii_adventurers.tests.test_m17 import game, step, teleport, world
from ascii_adventurers.tests.test_m22_5 import finish
from ascii_adventurers.tests.test_weapons import hero, open_map
from ascii_adventurers.world import tiles
from ascii_adventurers.world.landmarks import quest_marks

DT = 1 / 60


def khepri_at(x=20.0, y=15.0, world_map=None):
    b = make_enemy("khepri", x, y, random.Random(4))
    b.scale_to_level(1)
    return b


def run(b, h, w, seconds, shots=None):
    shots = [] if shots is None else shots
    for _ in range(round(seconds * 60)):
        b.think(AIContext(w, [h], [h, b], shots, []), DT)
    return shots


class DesertLandmarkTest(unittest.TestCase):
    def test_camp_and_pit_in_the_desert(self):
        for seed in (1, 2, 31, 999):
            w = world(seed)
            camp, lair = quest_marks(w.layout, "scarab_collector")
            self.assertEqual((camp.key, lair.key), ("oasis_camp", "sand_lair"))
            for m in (camp, lair):
                self.assertEqual(w.layout.biome_at(m.cx, m.cy).name, "desert", seed)
            self.assertIs(lair.floor, tiles.SAND)
            for x, y in camp.spots:
                self.assertEqual(w.layout.biome_at(x, y).name, "desert", seed)

    def test_the_pit_is_sandstone_and_sand(self):
        w = world(31)
        camp, lair = quest_marks(w.layout, "scarab_collector")
        nx, ny = camp.npc
        self.assertIs(w.tile_at(math.floor(nx), math.floor(ny)), tiles.NOMAD_POST)
        flat = {t for row in lair.rows for t in row if t is not None}
        self.assertTrue({tiles.SANDSTONE, tiles.SAND, tiles.SAND_PIT} <= flat)
        self.assertNotIn(tiles.MUD, flat)
        self.assertNotIn(tiles.POND, flat)
        for px, py in lair.spots:
            self.assertIs(w.tile_at(math.floor(px), math.floor(py)), tiles.SAND_PIT)
        x, y = camp.spots[0]                                  # a sandy clearing
        self.assertIs(w.tile_at(math.floor(x), math.floor(y)), tiles.SAND)

    def test_new_tiles_have_map_colors(self):
        from ascii_adventurers import palette
        for t in (tiles.SANDSTONE, tiles.SAND_PIT, tiles.OASIS, tiles.PALM, tiles.TENT,
                  tiles.RUG, tiles.STALL, tiles.NOMAD_POST):
            self.assertTrue(t.name in palette.MAP_TILE or t.name in palette.MAP_TILE_BIOME, t.name)
            self.assertNotIn("~", "".join(t.glyphs), t.name)  # (VT323's "~" looks like an N)


class GoldenScarabTest(unittest.TestCase):
    def test_runs_digs_in_and_comes_back_home(self):
        w = open_map(w=80, h=40)
        e = make_enemy("golden_scarab", 40.0, 20.0, random.Random(1))
        h = hero("wizard", 33.0, 20.0)
        ctx = AIContext(w, [h], [h, e], [], [])

        def chase(frames, speed=5.0):              # (slower than it: it gets away)
            for _ in range(frames):
                e.think(ctx, DT)
                a = math.atan2(e.y - h.y, e.x - h.x)
                if math.hypot(e.x - h.x, e.y - h.y) > 3:
                    h.x += math.cos(a) * speed * DT
                    h.y += math.sin(a) * speed * DT

        d0 = math.hypot(e.x - h.x, e.y - h.y)
        chase(60)
        self.assertEqual(e.state, "flee")
        self.assertGreater(math.hypot(e.x - h.x, e.y - h.y), d0)   # it runs away
        spook, run_s, dig, hide = config.GOLDEN_SCARAB
        chase(round(run_s * 60) - 60 + 5)          # (the first second counted already)
        self.assertEqual(e.state, "dig")
        self.assertTrue(e.hittable)                       # the last chance
        for _ in range(round(dig * 60) + 2):
            e.think(ctx, DT)
        self.assertEqual(e.state, "gone")
        self.assertFalse(e.hittable)
        h.x = 0.5                                         # (out of its way)
        for _ in range(round(hide * 60) + 2):
            e.think(ctx, DT)
        self.assertEqual(e.state, "idle")
        self.assertLess(math.hypot(e.x - 40.0, e.y - 20.0), 0.5)   # home again

    def test_left_alone_it_stays_home(self):
        w = open_map(w=80, h=40)
        e = make_enemy("golden_scarab", 40.0, 20.0, random.Random(1))
        h = hero("wizard", 5.0, 5.0)
        ctx = AIContext(w, [h], [h, e], [], [])
        for _ in range(600):
            e.think(ctx, DT)
        self.assertEqual(e.state, "idle")
        self.assertLess(math.hypot(e.x - 40, e.y - 20), 10)


class KhepriTest(unittest.TestCase):
    def setUp(self):
        self.h = hero("wizard", 40.0, 15.0)
        self.h.invulnerable = True

    def roll_at(self, w):
        b = khepri_at(20.0, 15.0)
        b._rest = 0.0
        b._pick_move = lambda: "roll"
        return b

    def test_the_ball_grows_and_runs_you_over(self):
        w = open_map(w=90, h=30)
        b = self.roll_at(w)
        self.h.invulnerable = False
        self.h.max_hp = self.h.hp = 10 ** 6
        r0 = b.ball[2]
        hp = self.h.hp
        run(b, self.h, w, 4.0)
        self.assertGreater(b.ball[2], r0)
        self.assertLess(self.h.hp, hp)                     # run over
        self.assertGreater(abs(self.h.y - 15.0), 1.0)      # and knocked aside
        self.assertIsNotNone(b.ball)                       # nothing solid: still whole

    def test_a_pillar_shatters_it_and_stuns_him(self):
        walls = [(x, y) for x in (31, 32) for y in range(10, 21)]   # a pillar between you
        w = open_map(w=90, h=30, walls=walls)
        b = self.roll_at(w)
        shots = []
        for _ in range(60 * 4):
            b.think(AIContext(w, [self.h], [self.h, b], shots, []), DT)
            if b.ball is None:
                break
        self.assertIsNone(b.ball)
        self.assertGreater(b.dazed, 0)
        self.assertTrue(b.hittable)                        # the melee window
        self.assertGreaterEqual(sum(1 for p in shots if p.owner is b), config.DUNG_CLODS[0])
        # Up again, he rolls up a new (small) ball.
        run(b, self.h, w, config.DUNG_STUN + config.DUNG_GATHER + 0.5)
        self.assertIsNotNone(b.ball)
        self.assertLessEqual(b.ball[2], config.DUNG_RADIUS[0] + 0.5)

    def test_bigger_ball_hurts_more(self):
        b = khepri_at()
        b.ball[2] = config.DUNG_RADIUS[1]
        self.assertEqual(b.ball_frac, 1.0)
        b.ball[2] = config.DUNG_RADIUS[0]
        self.assertEqual(b.ball_frac, 0.0)

    def test_burrowed_he_cant_be_hit_and_comes_up_under_you(self):
        w = open_map(w=90, h=30)
        b = khepri_at()
        b._rest = 0.0
        b._pick_move = lambda: "burrow"
        seen_under = False
        for _ in range(60 * 5):
            b.think(AIContext(w, [self.h], [self.h, b], [], []), DT)
            seen_under |= b.submerged and not b.hittable
            if b.last_move == "burrow":
                break
        self.assertTrue(seen_under)
        self.assertFalse(b.submerged)
        self.assertLess(math.hypot(b.x - self.h.x, b.y - self.h.y), 6.0)

    def test_every_move_runs_to_the_end(self):
        names = {m for ph in config.BOSSES["khepri"].phases for m, _ in ph.moves}
        w = open_map(w=90, h=30, walls=[(70, y) for y in range(30)])
        for phase in (0, 2):
            for name in sorted(names):
                b = khepri_at()
                b.phase = phase
                b.recruit = lambda k, x, y: make_enemy(k, x, y, random.Random(2))
                b._rest = 0.0
                b._pick_move = lambda name=name: name
                done = False
                for _ in range(60 * 14):
                    b.think(AIContext(w, [self.h], [self.h, b], [], []), DT)
                    if b.last_move == name:
                        done = True
                        break
                self.assertTrue(done, (phase, name))
                self.assertTrue(b.hittable, name)
                self.assertFalse(b.rolling or b.charging or b.wings, name)

    def test_a_charge_into_a_pillar_dazes_him(self):
        w = open_map(w=90, h=30, walls=[(x, y) for x in (30, 31) for y in range(8, 23)])
        b = khepri_at()
        b._rest = 0.0
        b._pick_move = lambda: "charge"
        dazed = False
        for _ in range(60 * 4):
            b.think(AIContext(w, [self.h], [self.h, b], [], []), DT)
            dazed |= b.dazed > 0
        self.assertTrue(dazed)
        self.assertLess(b.x, 30)                            # he stopped at it

    def test_the_swarm_call_is_capped(self):
        w = open_map(w=90, h=30)
        b = khepri_at()
        adds = []

        def recruit(k, x, y):
            e = make_enemy(k, x, y, random.Random(len(adds)))
            adds.append(e)
            return e
        b.recruit = recruit
        b._rest = 0.0
        b._pick_move = lambda: "swarm"
        actors = [self.h, b]
        for _ in range(60 * 12):
            b.think(AIContext(w, [self.h], actors + adds, [], []), DT)
        self.assertEqual(len(adds), config.KHEPRI_SWARM[2])
        self.assertTrue(all(a.kind_key == "scarab" for a in adds))


class QuestTest(unittest.TestCase):
    def tearDown(self):
        config.QUEST_FOCUS = None

    def test_the_whole_fight(self):
        m, s = game(seed=31)
        q = s.quests
        st = q.states["scarab_collector"]
        self.assertEqual(st.spec.target, "golden_scarab")
        finish(q, "scarab_collector")
        self.assertEqual(st.stage, "awake")
        s.hero.invulnerable = True
        lair = st.lair
        teleport(s, lair.cx + 20, lair.cy + 10)
        step(s, 1)
        self.assertEqual(st.stage, "fight")
        b = st.boss
        self.assertIsInstance(b, Khepri)
        step(s, 240)
        s.draw(m.text)
        b.hp = 0.0
        b.last_hit_by = s.hero
        step(s)
        self.assertEqual(st.stage, "cleared")
        self.assertIn("khepri", m.app.guild.achievements)
        self.assertEqual(m.app.guild.journal["scarab_collector"]["wins"], 1)
        self.assertTrue(all(s.world.tile_at(*t) is tiles.SAND for t in lair.gate))
        self.assertEqual(q.guardians, 1)

    def test_golden_scarabs_are_out_from_the_start(self):
        m, s = game(seed=31)
        st = s.quests.states["scarab_collector"]
        teleport(s, st.camp.spots[0][0] + 6, st.camp.spots[0][1])
        step(s, 3)
        golden = [e for e in s.enemies if getattr(e, "kind_key", "") == "golden_scarab"]
        self.assertTrue(golden)
        s.draw(m.text)


if __name__ == "__main__":
    unittest.main()
