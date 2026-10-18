"""M26.3: Mycelium the giant puffball (minefield, bounding, spore wind,
split), its field, and its giver for the shared "sever" quest."""

import math
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.ai import make_enemy
from ascii_adventurers.ai.bosses import MycoPart, PuffHalf, Puffball
from ascii_adventurers.ai.brain import AIContext
from ascii_adventurers.systems.quests import circle_rules
from ascii_adventurers.tests.test_m17 import game, step, teleport, world
from ascii_adventurers.tests.test_weapons import hero
from ascii_adventurers.world import tiles
from ascii_adventurers.world.landmarks import Landmark, quest_marks
from ascii_adventurers.world.test_map import LEGEND, TestMap

DT = 1 / 60
W, H = 160, 50


def field(rocks=()):
    rows = [["."] * W for _ in range(H)]
    for x, y in rocks:
        rows[y][x] = "R"
    m = TestMap(["".join(r) for r in rows], dict(LEGEND))
    lair = Landmark("puffball_field", "lair", "mushroom", "MYCELIUM", 0, 0, [], cx=W / 2,
                    cy=H / 2, spots=[(W / 2, H / 2)], radii=(W / 2 + 2, H / 2 + 2), props={})
    return m, lair


class Fight:
    def __init__(self, hx=80.0, hy=25.0, bx=70.0, by=25.0, phase=0, rocks=()):
        self.w, self.lair = field(rocks)
        self.b = make_enemy("mycelium_puffball", bx, by, random.Random(4))
        self.b.scale_to_level(1)
        self.b._rest = 99.0
        self.b.mine_t = self.b.bound_t = self.b.breath_t = self.b.split_t = 999.0
        self.b.lair = self.lair
        self.b.hp = self.b.max_hp * (1.0, 0.5, 0.2)[phase]
        self.h = hero("wizard", hx, hy)
        self.h.max_hp = self.h.hp = 10 ** 6
        self.adds, self.shots, self.effects = [], [], []

        def recruit(k, x, y):
            e = make_enemy(k, x, y, random.Random(len(self.adds)))
            self.adds.append(e)
            return e
        self.b.recruit = recruit
        self.b.ctx = self.ctx()
        self.b._check_phase(self.b.ctx)

    def ctx(self):
        return AIContext(self.w, [self.h], [self.h, self.b] + self.adds, self.shots, self.effects)

    def run(self, seconds, move=None, until=None):
        if move is not None:
            self.b._rest = 0.0
            self.b.last_move = None
            self.b._pick_move = lambda m=move: m
        for _ in range(round(seconds * 60)):
            self.b.think(self.ctx(), DT)
            if move is not None and self.b.last_move == move:
                self.b._rest = 99.0
                self.b._pick_move = lambda: "rings"
                move = None
            if until is not None and until():
                return True
        return False

    def sign(self, name):
        self.b._start(name)
        self.b._wait = 0.0

    def mine(self, x, y):
        m = make_enemy("puff_mine", x, y, random.Random(len(self.adds)))
        m.part_of = self.b
        m.rooted = True
        self.adds.append(m)
        self.b.mines.append(m)
        return m


class FieldTest(unittest.TestCase):
    def test_camp_and_field_in_the_mushroom_biome(self):
        for seed in (1, 2, 31, 999):
            w = world(seed)
            camp, lair = quest_marks(w.layout, "forager")
            self.assertEqual((camp.key, lair.key), ("spore_camp", "puffball_field"), seed)
            for m in (camp, lair):
                self.assertEqual(w.layout.biome_at(m.cx, m.cy).name, "mushroom", seed)
            self.assertEqual(lair.name, "MYCELIUM")

    def test_dust_boulders_and_mushrooms(self):
        w = world(31)
        _, lair = quest_marks(w.layout, "forager")
        flat = {t for row in lair.rows for t in row if t is not None}
        self.assertTrue({tiles.SHROOM_WALL, tiles.MYCELIUM, tiles.SPORE_DUST, tiles.ROCK,
                         tiles.GIANT_SHROOM} <= flat)

    def test_new_tiles_and_shot_glyphs(self):
        from ascii_adventurers import palette
        from ascii_adventurers.render.ascii_fx import SHOT_LOOKS as _LOOKS
        floors = "".join(g for t in (tiles.MYCELIUM, tiles.SPORE_DUST) for g in t.glyphs)
        for look in ("puff", "dust_spore"):
            head, trail, _ = _LOOKS[look]
            for ch in head + "".join(t for t in trail if t):
                if ch != " ":
                    self.assertNotIn(ch, floors, look)
        for t in (tiles.NODE_SPILL_DUST, tiles.SPORE_DUST):
            self.assertTrue(t.name in palette.MAP_TILE or t.name in palette.MAP_TILE_BIOME, t.name)
            self.assertNotIn("~", "".join(t.glyphs), t.name)


class SharedQuestTest(unittest.TestCase):
    def test_three_givers_one_quest(self):
        qs = [config.QUESTS[k] for k in ("truffle_hunter", "mycologist", "forager")]
        for f in ("title", "camp", "target", "count", "goal", "kind", "lair_name", "lines"):
            self.assertEqual(len({repr(getattr(q, f)) for q in qs}), 1, f)
        self.assertEqual(len({q.giver for q in qs}), 3)
        self.assertEqual({config.ENEMIES[q.boss].name for q in qs}, {"Mycelium"})
        spills = {circle_rules("sever", q.skin)["done"] for q in qs}
        self.assertEqual(spills, {tiles.NODE_SPILL_RED, tiles.NODE_SPILL_INK,
                                  tiles.NODE_SPILL_DUST})


class MineTest(unittest.TestCase):
    def test_it_scatters_mines_round_you(self):
        f = Fight()
        f.b.mine_t = 0.0
        f.run(config.MINE_TELL + 0.2)
        self.assertEqual(len(f.b.mines), config.MINES)
        self.assertTrue(all(isinstance(m, MycoPart) and m.rooted for m in f.b.mines))

    def test_walk_near_one_and_its_fuse_lights(self):
        f = Fight(hx=40.0)
        m = f.mine(40.5, 25.0)
        hp = f.h.hp
        f.run(DT)
        self.assertGreater(m.age, 0)
        f.run(config.MINE_FUSE + 0.1)
        self.assertFalse(m.alive)
        self.assertLess(f.h.hp, hp)

    def test_a_shot_mine_pops_and_chains(self):
        f = Fight(hx=20.0)
        a = f.mine(40.0, 25.0)
        b = f.mine(42.5, 25.0)
        c = f.mine(45.0, 25.0)
        far = f.mine(60.0, 25.0)
        a.hp = 0
        f.run(DT)
        self.assertFalse(b.alive)
        f.run(config.MINE_GAP * 3)
        self.assertFalse(c.alive)
        self.assertTrue(far.alive)

    def test_a_pop_next_to_it_hurts_and_staggers_it(self):
        f = Fight(hx=20.0)
        m = f.mine(f.b.x + 2.0, f.b.y)
        hp = f.b.hp
        m.hp = 0
        f.run(DT)
        self.assertAlmostEqual(f.b.hp, hp - config.MINE_HURT * f.b.max_hp)
        self.assertGreater(f.b.dazed, 0)
        self.assertIn("STAGGERED", f.b.bar_label)


class BoundTest(unittest.TestCase):
    def test_it_bounds_between_moves_from_phase_two(self):
        f = Fight()
        f.b.bound_t = 0.0
        f.run(1.0)
        self.assertNotEqual(f.b.last_move, "bound")
        f = Fight(phase=1)
        f.b.bound_t = 0.0
        f.b._rest = 99.0
        hp = f.h.hp
        self.assertTrue(f.run(0.2, until=lambda: f.b.landing is not None))
        self.assertFalse(f.b.hittable)
        land = f.b.landing
        self.assertTrue(f.run(1.5, until=lambda: f.b.airborne <= 0))
        self.assertAlmostEqual(f.b.x, land[0], places=3)
        lo, hi = config.BOUND_NEAR
        self.assertLessEqual(math.hypot(land[0] - f.h.x, land[1] - f.h.y), hi + 0.5)


class WindTest(unittest.TestCase):
    def test_breath_clouds_drift_with_the_wind_and_turn(self):
        f = Fight(phase=2)
        f.b.wind = 0.0
        f.sign("breath")
        f.run(config.BREATH_TELL + 0.1)
        self.assertEqual(len(f.b.clouds), config.BREATH_CLOUDS)
        x0 = [c[0] for c in f.b.clouds]
        f.run(1.0)
        for c, x in zip(f.b.clouds, x0):
            self.assertAlmostEqual(c[0] - x, config.WIND_SPEED, delta=0.2)
        f.b.wind_t = 0.0
        f.run(DT)
        self.assertAlmostEqual(abs(f.b.wind), math.radians(config.WIND_TURN))

    def test_a_cloud_stops_at_a_boulder(self):
        f = Fight(phase=2, rocks=[(50, 25)])
        f.b.wind = 0.0
        f.b.clouds = [[48.0, 25.5, 0.0, 9.0, 2.4, 1.0]]
        f.run(2.0)
        self.assertLess(f.b.clouds[0][0], 50.0)

    def test_a_cloud_chokes(self):
        f = Fight()
        f.b.clouds = [[f.h.x, f.h.y, 0.0, 9.0, 2.4, 0.0]]
        hp = f.h.hp
        f.run(1.0)
        self.assertLess(f.h.hp, hp)


class SplitTest(unittest.TestCase):
    def test_it_splits_the_halves_share_its_health_and_rejoin(self):
        f = Fight(phase=2)
        f.sign("split")
        self.assertTrue(f.run(config.SPLIT_TELL + 0.2, until=lambda: f.b.split))
        self.assertEqual(len(f.b.halves), 2)
        self.assertTrue(all(isinstance(h, PuffHalf) for h in f.b.halves))
        self.assertFalse(f.b.hittable)
        hp = f.b.hp
        dealt = f.b.halves[0].take_damage(100, f.h, 0.0)
        self.assertEqual(dealt, 100)
        self.assertEqual(f.b.hp, hp - 100)
        self.assertTrue(f.b.halves[0].alive)
        self.assertTrue(f.run(config.SPLIT_TIME + 6.0, until=lambda: not f.b.split))
        self.assertTrue(f.b.hittable)
        self.assertTrue(all(not a.alive for a in f.adds if isinstance(a, PuffHalf)))

    def test_the_halves_bound_at_you(self):
        f = Fight(phase=2, hx=110.0)
        f.sign("split")
        f.run(config.SPLIT_TELL + 0.2)
        hp = f.h.hp
        f.run(config.SPLIT_TIME * 0.8)
        self.assertLess(f.h.hp, hp)


class MoveTest(unittest.TestCase):
    def test_roll_runs_you_over(self):
        f = Fight(hx=90.0)
        hp = f.h.hp
        f.run(config.PUFF_ROLL[0] + 2.5, move="roll")
        self.assertLess(f.h.hp, hp)

    def test_roll_bounces_off_the_edge(self):
        f = Fight(hx=150.0, hy=25.0, bx=140.0)
        f.run(config.PUFF_ROLL[0] + 3.0, move="roll")
        self.assertLess(f.b.x, 150.0)

    def test_puff_rings_with_a_gap(self):
        f = Fight()
        f.run(config.PUFF_RINGS[0] + 0.1, move="rings")
        n = config.PUFF_RINGS[2]
        ring = [p for p in f.shots if p.spec.look == "puff"]
        self.assertTrue(0 < len(ring) < n)

    def test_mortars_leave_clouds(self):
        f = Fight()
        f.run(0.3 + config.PUFF_MORTARS[0] + 0.8, move="mortars")
        self.assertEqual(len(f.b.clouds), config.PUFF_MORTARS[1])

    def test_squash_springs(self):
        f = Fight(hx=72.0)
        hp = f.h.hp
        f.run(config.PUFF_SQUASH[0] + 0.5, move="squash")
        self.assertLess(f.h.hp, hp)


class GameTest(unittest.TestCase):
    def test_the_fight_in_a_real_game(self):
        config.QUEST_FOCUS = "forager"
        try:
            m, s = game(seed=31)
            q = s.quests
            q.dev_finish_hunt()
            st = q.states["forager"]
            teleport(s, st.lair.cx, st.lair.cy + 12)
            s.hero.invulnerable = True
            step(s, 3)
            self.assertEqual(st.stage, "fight")
            b = st.boss
            self.assertIsInstance(b, Puffball)
            b.hp = b.max_hp * 0.2
            b.split_t = 0.0
            for f in range(900):
                step(s)
                if f % 60 == 0:
                    s.draw(m.text)
            self.assertTrue(b.alive)
            b.hp = 0
            b.last_hit_by = s.hero
            step(s, 3)
            self.assertEqual(st.stage, "cleared")
            self.assertFalse(any(isinstance(e, MycoPart) and e.alive for e in s.enemies))
        finally:
            config.QUEST_FOCUS = None


if __name__ == "__main__":
    unittest.main()
