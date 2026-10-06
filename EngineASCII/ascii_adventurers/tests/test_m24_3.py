"""M24.3: the ruins' third boss, Fragile, The Misunderstood (a signature a
phase: sunlight through the shutters, shapeshifting, on the beat), the pawn
dealer's "fetch" quest (Mr. Buttons' pieces, sewn, carried into the fight,
given back after it), and the ruined ballroom."""

import math
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.ai import make_enemy
from ascii_adventurers.ai.bosses import Fragile
from ascii_adventurers.ai.brain import AIContext
from ascii_adventurers.systems.quests import QUEST_SID
from ascii_adventurers.tests.test_m17 import game, step, teleport, world
from ascii_adventurers.tests.test_m22_5 import finish
from ascii_adventurers.tests.test_weapons import hero
from ascii_adventurers.world import tiles
from ascii_adventurers.world.landmarks import Landmark, quest_marks
from ascii_adventurers.world.test_map import LEGEND, TestMap

DT = 1 / 60
W, H = 140, 44


def ballroom(walls=()):
    """An open map: a window at (40, 1) shining straight down (its lever at
    (40.5, 4.5)), another at (100, 1); coffins at (130, 20) and (130, 26);
    two chandeliers; a lair over all of it."""
    rows = [["."] * W for _ in range(H)]
    for x, y in ((40, 1), (41, 1), (100, 1), (101, 1)):
        rows[y][x] = "S"
    for x, y in ((130, 20), (130, 26)):
        rows[y][x] = "C"
    for x, y in walls:
        rows[y][x] = "#"
    m = TestMap(["".join(r) for r in rows], dict(LEGEND, S=tiles.SHUTTER, C=tiles.COFFIN))
    props = {"windows": [(41.0, 1.5, 0.0, 1.0), (101.0, 1.5, 0.0, 1.0)],
             "levers": [(40.5, 4.5), (100.5, 4.5)],
             "coffins": [(130.5, 20.5), (130.5, 26.5)],
             "chandeliers": [(60.0, 22.0), (80.0, 22.0)]}
    lair = Landmark("ballroom", "lair", "ruins", "BALLROOM", 0, 0, [], cx=W / 2, cy=H / 2,
                    spots=[(W / 2, H / 2)], radii=(W / 2 + 2, H / 2 + 2), props=props)
    return m, lair


class Fight:
    def __init__(self, hx=90.0, hy=22.0, bx=60.0, by=22.0):
        self.w, self.lair = ballroom()
        self.b = make_enemy("fragile", bx, by, random.Random(4))
        self.b.scale_to_level(1)
        self.b._rest = 99.0
        self.b.lair = self.lair
        self.h = hero("wizard", hx, hy)
        self.h.max_hp = self.h.hp = 10 ** 6
        self.adds, self.shots, self.effects = [], [], []

        def recruit(k, x, y):
            e = make_enemy(k, x, y, random.Random(len(self.adds)))
            self.adds.append(e)
            return e
        self.b.recruit = recruit
        self.b.ctx = self.ctx()

    def ctx(self):
        return AIContext(self.w, [self.h], [self.h, self.b] + self.adds, self.shots, self.effects)

    def run(self, seconds, move=None):
        if move is not None:
            self.b._rest = 0.0
            self.b._pick_move = lambda: move
        for _ in range(round(seconds * 60)):
            self.b.think(self.ctx(), DT)
            if move is not None and self.b.last_move == move:
                self.b._rest = 99.0
                self.b._pick_move = lambda: "riff"
                move = None


class BallroomTest(unittest.TestCase):
    def test_camp_and_ballroom_in_the_ruins(self):
        for seed in (1, 2, 31, 999):
            w = world(seed)
            camp, lair = quest_marks(w.layout, "pawn_dealer")
            self.assertEqual((camp.key, lair.key), ("scrap_camp", "ballroom"), seed)
            for m in (camp, lair):
                self.assertEqual(w.layout.biome_at(m.cx, m.cy).name, "ruins", seed)
            self.assertGreaterEqual(len(lair.props["windows"]), 4, seed)
            self.assertEqual(len(lair.props["windows"]), len(lair.props["levers"]), seed)
            self.assertEqual(len(lair.props["coffins"]), config.BALLROOM_COFFINS, seed)

    def test_its_windows_levers_coffins_and_pillars(self):
        w = world(31)
        camp, lair = quest_marks(w.layout, "pawn_dealer")
        flat = {t for row in lair.rows for t in row if t is not None}
        self.assertTrue({tiles.CASTLE_WALL, tiles.PARQUET, tiles.SHUTTER, tiles.LEVER, tiles.MARBLE,
                         tiles.COFFIN, tiles.VELVET_THRONE, tiles.MIRROR} <= flat)
        for lx, ly in lair.props["levers"]:
            self.assertIs(w.tile_at(math.floor(lx), math.floor(ly)), tiles.LEVER)
        for wx, wy, dx, dy in lair.props["windows"]:
            self.assertIs(w.tile_at(math.floor(wx), math.floor(wy)), tiles.SHUTTER)
            self.assertTrue(lair.inside(wx + dx * 8, wy + dy * 8))   # (the sun falls inward)
        x, y = lair.spots[0]
        self.assertFalse(w.tile_at(math.floor(x), math.floor(y)).solid)
        x, y = camp.spots[0]
        self.assertIs(w.tile_at(math.floor(x), math.floor(y)), tiles.BEAR_PIECE)

    def test_new_tiles_have_map_colors(self):
        from ascii_adventurers import palette
        for t in (tiles.CASTLE_WALL, tiles.PARQUET, tiles.SHUTTER, tiles.WINDOW_OPEN, tiles.LEVER,
                  tiles.MARBLE, tiles.COFFIN, tiles.COFFIN_STAKED, tiles.VELVET_THRONE,
                  tiles.MIRROR, tiles.CHANDELIER_RUBBLE, tiles.BEAR_PIECE):
            self.assertTrue(t.name in palette.MAP_TILE or t.name in palette.MAP_TILE_BIOME, t.name)
            self.assertNotIn("~", "".join(t.glyphs), t.name)


class SunTest(unittest.TestCase):
    def test_a_lever_opens_the_shutter_and_she_burns(self):
        f = Fight(hx=40.5, hy=5.0, bx=41.0, by=20.0)
        f.run(config.LEVER_TIME + 0.1)
        self.assertIn(0, f.b.open)
        self.assertIs(f.w.tile_at(40, 1), tiles.WINDOW_OPEN)
        self.assertTrue(f.b.in_sun(41.0, 20.0))
        self.assertGreater(f.b.dazed, 0)                    # caught in it: stunned
        hp = f.b.hp
        f.b.take_damage(100, None, 0.0)
        self.assertAlmostEqual(hp - f.b.hp, 100 * config.SUN_VULN)
        self.assertIn("SUN", "".join(k.upper() for _, _, k, _ in f.b.map_marks()))

    def test_the_sun_goes_out_and_she_slams_shutters(self):
        f = Fight(hx=40.5, hy=5.0, bx=90.0, by=30.0)
        f.run(config.LEVER_TIME + 0.1)
        f.h.x = 70.0
        self.assertIn(0, f.b.open)
        f.b.slam_t = 0.0
        f.b._rest = 99.0
        f.run(config.SLAM_TELL + 0.6)
        self.assertNotIn(0, f.b.open)
        self.assertIs(f.w.tile_at(40, 1), tiles.SHUTTER)

    def test_her_gaze_pulls_you_but_not_in_the_sun(self):
        f = Fight(hx=72.0, hy=22.0, bx=60.0, by=22.0)
        x0 = f.h.x
        f.run(4.0, "gaze")
        self.assertLess(f.h.x, x0 - 1.0)
        g = Fight(hx=41.0, hy=10.0, bx=41.0, by=26.0)
        g.b.open[0] = 99.0
        y0 = g.h.y
        g.run(4.0, "gaze")
        self.assertAlmostEqual(g.h.y, y0, delta=0.1)


class FormTest(unittest.TestCase):
    def test_she_shifts_forms_from_phase_two(self):
        f = Fight()
        f.run(config.FORM_TIME + 1.0)
        self.assertEqual(f.b.form, "girl")
        f.b.phase = 1
        f.b.form_t = 0.0
        f.run(config.FORM_TELL + 0.1)
        self.assertIn(f.b.form, ("bat", "wolf"))
        self.assertIsNone(f.b.tell)

    def test_bats_take_half_except_from_the_pulse(self):
        f = Fight()
        f.b.form = "bat"
        hp = f.b.hp
        f.b.take_damage(100, f.h, 0.0)
        self.assertAlmostEqual(hp - f.b.hp, 100 * config.BAT_ARMOR)
        bard = hero("bard", 50.0, 22.0)
        hp = f.b.hp
        f.b.take_damage(100, bard, 0.0)
        self.assertAlmostEqual(hp - f.b.hp, 100)

    def test_a_wolf_charging_into_the_sun_is_stunned(self):
        f = Fight(hx=41.0, hy=34.0, bx=41.0, by=12.0)
        f.b.form = "wolf"
        f.b.form_t = 99.0
        f.b.phase = 1
        f.b.open[0] = 99.0
        f.b.caught.add(0)
        f.b.x = 30.0
        f.h.x, f.h.y = 55.0, 12.0
        f.run(3.0, "charge")
        self.assertTrue(f.b.dazed > 0 or f.b.last_move == "charge")


class BeatTest(unittest.TestCase):
    def test_tells_end_on_the_beat(self):
        f = Fight()
        f.b.phase = 2
        f.b.beat0 = 0.3
        f.b.time = 1.0
        s = f.b.tell_s(0.6)
        land = (f.b.time - f.b.beat0 + s) % f.b.period
        self.assertTrue(land < 1e-6 or abs(land - f.b.period) < 1e-6)

    def test_a_roll_on_the_beat_stuns_her(self):
        f = Fight()
        f.b.phase = 2
        f.b.beat0 = f.b.time
        f.run(DT)
        p = f.b.period
        while f.b.beat_phase() > p - 2 * DT or f.b.beat_phase() > config.BEAT_PERFECT:
            f.run(DT)
        f.h.roll_t = 0.3
        f.run(DT)
        self.assertGreater(f.b.dazed, 0)


class MoveTest(unittest.TestCase):
    def test_the_axe_goes_out_and_comes_back(self):
        f = Fight(hx=75.0)
        f.run(1.5, "axe")
        f.run(0.2)
        self.assertIsNotNone(f.b.axe)
        f.run(4.0)
        self.assertIsNone(f.b.axe)

    def test_mist_step_leaves_slowing_mist(self):
        f = Fight()
        f.run(2.0, "mist")
        self.assertTrue(f.b.mist)
        m = f.b.mist[0]
        f.h.x, f.h.y = m[0], m[1]
        f.run(DT)
        self.assertEqual(f.h.time_mult, config.FRAGILE_MIST[4])

    def test_thralls_and_a_staked_coffin_stays_shut(self):
        f = Fight(hx=129.0, hy=20.5)
        f.run(config.STAKE_TIME + 0.2)
        self.assertIn(0, f.b.staked)
        self.assertIs(f.w.tile_at(130, 20), tiles.COFFIN_STAKED)
        f.h.x, f.h.y = 90.0, 22.0
        f.run(2.0, "thralls")
        self.assertTrue(f.adds)
        self.assertTrue(all(a.kind_key == "thrall" for a in f.adds))
        self.assertTrue(all(a.y > 24 for a in f.adds))          # (only the unstaked coffin)

    def test_a_chandelier_crashes_and_stays_as_cover(self):
        f = Fight(hx=60.0, hy=22.0)
        f.b.phase = 1
        f.run(2.0, "chandeliers")
        self.assertIn(0, f.b.fallen)
        self.assertIs(f.w.tile_at(59, 21), tiles.CHANDELIER_RUBBLE)
        self.assertLess(f.h.hp, 10 ** 6)

    def test_every_move_runs_to_the_end(self):
        girl = {m for ph in config.BOSSES["fragile"].phases for m, _ in ph.moves}
        forms = {(form, m) for form, ms in config.FRAGILE_FORM_MOVES.items() for m, _ in ms}
        for phase in (0, 2):
            for form, name in sorted({("girl", m) for m in girl} | forms):
                f = Fight(hx=100.0)
                f.h.invulnerable = True
                f.b.phase = phase
                f.b.form = form
                f.b.form_t = 99.0
                f.run(10.0, name)
                self.assertEqual(f.b.last_move, name, (phase, form, name))
                self.assertIsNone(f.b.gaze, name)
                self.assertFalse(f.b.dashing, name)


class QuestTest(unittest.TestCase):
    def tearDown(self):
        config.QUEST_FOCUS = None

    def take_pieces(self, s, st, n):
        sp = s.spawner
        for i in range(n):
            x, y = st.camp.spots[i]
            teleport(s, x + 2.0, y)
            step(s, 3)
            for k in range(config.CARGO_GUARDS):
                e = sp.awake.get((QUEST_SID, st.qid, i, k + 1))
                if e is not None:
                    e.hp = 0.0
                    e.last_hit_by = s.hero
            step(s, 3)

    def test_carry_the_pieces_sew_the_bear_and_give_it_back(self):
        m, s = game(seed=31)
        q = s.quests
        st = q.states["pawn_dealer"]
        self.assertEqual(st.spec.kind, "fetch")
        s.hero.invulnerable = True
        self.take_pieces(s, st, 4)
        self.assertEqual(st.carry.get(s.me.index), 4)
        self.assertEqual(st.found, 0)                       # not sewn until delivered
        teleport(s, st.npc.x + 2, st.npc.y)
        step(s, 3)
        self.assertEqual(st.found, 4)
        self.assertEqual(st.stage, "awake")
        self.assertEqual(st.bear, s.me.index)               # the bear stays with you
        s.draw(m.text)
        lair = st.lair
        teleport(s, lair.cx + 20, lair.cy + 6)
        step(s, 2)
        self.assertEqual(st.stage, "fight")
        b = st.boss
        self.assertIsInstance(b, Fragile)
        step(s, 200)
        s.draw(m.text)
        b.hp = 0.0
        b.last_hit_by = s.hero
        step(s, 2)
        self.assertEqual(st.stage, "cleared")
        self.assertIsNotNone(st.crying)                     # she sits there crying
        self.assertIn(st.crying, q.npcs)
        self.assertIn(("RUINS", "give Fragile her bear", False), q.log())
        self.assertIn("fragile", m.app.guild.achievements)
        level = s.me.progress.level
        q.talk(st.crying, s.me)
        self.assertTrue(st.gifted)
        self.assertIsNone(st.bear)
        self.assertEqual(s.me.progress.level, level + config.FRAGILE_GIFT_LEVELS)

    def test_no_bear_no_gift(self):
        m, s = game(seed=31)
        q = s.quests
        st = q.states["pawn_dealer"]
        finish(q, "pawn_dealer")
        st.bear = None
        s.hero.invulnerable = True
        teleport(s, st.lair.cx + 20, st.lair.cy + 6)
        step(s, 2)
        st.boss.hp = 0.0
        st.boss.last_hit_by = s.hero
        step(s, 2)
        level = s.me.progress.level
        q.talk(st.crying, s.me)
        self.assertFalse(st.gifted)
        self.assertEqual(s.me.progress.level, level)

    def test_a_fallen_carrier_drops_the_bear(self):
        m, s = game(seed=31)
        q = s.quests
        st = q.states["pawn_dealer"]
        st.stage = "awake"
        st.bear = s.me.index
        s.hero.hp = 0.0
        step(s, 2)
        self.assertIsNone(st.bear)
        self.assertEqual([d[2] for d in st.drops], ["bear"])
        self.assertTrue(any(k == "bear" for _, _, k, _ in q.pins()))

    def test_dev_finish_hands_you_the_bear(self):
        m, s = game(seed=31)
        config.QUEST_FOCUS = "pawn_dealer"
        st = s.quests.states["pawn_dealer"]
        self.assertTrue(s.quests.dev_finish_hunt())
        self.assertEqual(st.bear, s.me.index)


if __name__ == "__main__":
    unittest.main()
