"""M24.2: the ruins' second boss, the Snow King, King of Loneliness (a
signature a phase: knock off his crown, black ice and fire braziers, flash
freeze), the searching sister's "rescue" quest, the frost wraiths, and the
frozen throne hall."""

import math
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.ai import make_enemy
from ascii_adventurers.ai.bosses import SnowKing
from ascii_adventurers.ai.brain import AIContext
from ascii_adventurers.entities.projectile import Projectile
from ascii_adventurers.players.controls import PlayerInput
from ascii_adventurers.systems import roll
from ascii_adventurers.tests.test_m17 import game, step, teleport, world
from ascii_adventurers.tests.test_m22_5 import finish
from ascii_adventurers.tests.test_weapons import hero
from ascii_adventurers.world import tiles
from ascii_adventurers.world.landmarks import Landmark, quest_marks
from ascii_adventurers.world.test_map import LEGEND, TestMap

DT = 1 / 60
W, H = 140, 44


def hall(walls=()):
    """An open map with fire braziers at (20, 10) and (120, 34), an ice
    pillar (2 x 2) at (60, 30), and a lair over all of it."""
    rows = [["."] * W for _ in range(H)]
    for x, y in ((20, 10), (120, 34)):
        rows[y][x] = "F"
    for dx in (0, 1):
        for dy in (0, 1):
            rows[30 + dy][60 + dx] = "P"
    for x, y in walls:
        rows[y][x] = "#"
    m = TestMap(["".join(r) for r in rows],
                dict(LEGEND, F=tiles.FIRE_BOWL, P=tiles.ICE_PILLAR))
    props = {"braziers": [(20.5, 10.5), (120.5, 34.5)], "pillars": [(60, 30)]}
    lair = Landmark("throne_hall", "lair", "ruins", "HALL", 0, 0, [], cx=W / 2, cy=H / 2,
                    spots=[(W / 2, H / 2)], radii=(W / 2 - 1, H / 2 - 1), props=props)
    return m, lair


class Fight:
    def __init__(self, hx=90.0, hy=22.0, bx=60.0, by=22.0, walls=()):
        self.w, self.lair = hall(walls)
        self.b = make_enemy("snow_king", bx, by, random.Random(4))
        self.b.scale_to_level(1)
        self.b._rest = 99.0
        self.b.lair = self.lair
        self.h = hero("wizard", hx, hy)
        self.h.max_hp = self.h.hp = 10 ** 6
        self.shots, self.effects = [], []
        self.b.ctx = self.ctx()

    def ctx(self):
        return AIContext(self.w, [self.h], [self.h, self.b], self.shots, self.effects)

    def run(self, seconds, move=None):
        if move is not None:
            self.b._rest = 0.0
            self.b._pick_move = lambda: move
        for _ in range(round(seconds * 60)):
            self.b.think(self.ctx(), DT)
            if move is not None and self.b.last_move == move:
                self.b._rest = 99.0
                self.b._pick_move = lambda: "shards"
                move = None


class HallTest(unittest.TestCase):
    def test_camp_and_hall_in_the_ruins(self):
        for seed in (1, 2, 31, 999):
            w = world(seed)
            camp, lair = quest_marks(w.layout, "searching_sister")
            self.assertEqual((camp.key, lair.key), ("scrap_camp", "throne_hall"), seed)
            for m in (camp, lair):
                self.assertEqual(w.layout.biome_at(m.cx, m.cy).name, "ruins", seed)
            self.assertEqual(len(lair.props["braziers"]), 4, seed)
            self.assertGreater(len(lair.props["pillars"]), 15, seed)

    def test_its_throne_pillars_braziers_and_statues(self):
        w = world(31)
        camp, lair = quest_marks(w.layout, "searching_sister")
        flat = {t for row in lair.rows for t in row if t is not None}
        self.assertTrue({tiles.ICE_WALL, tiles.FROST_STONE, tiles.THRONE, tiles.ICE_PILLAR,
                         tiles.FIRE_BOWL, tiles.STATUE, tiles.SNOWDRIFT} <= flat)
        x, y = lair.spots[0]
        self.assertFalse(w.tile_at(math.floor(x), math.floor(y)).solid)
        for bx, by in lair.props["braziers"]:
            self.assertIs(w.tile_at(math.floor(bx), math.floor(by)), tiles.FIRE_BOWL)
        cflat = {t for row in camp.rows for t in row if t is not None}
        self.assertIn(tiles.FROZEN_POND, cflat)
        self.assertNotIn(tiles.SLUDGE, cflat)
        x, y = camp.spots[0]
        self.assertIs(w.tile_at(math.floor(x), math.floor(y)), tiles.ICE_BLOCK)

    def test_new_tiles_have_map_colors(self):
        from ascii_adventurers import palette
        for t in (tiles.ICE_WALL, tiles.FROST_STONE, tiles.THRONE, tiles.ICE_PILLAR,
                  tiles.FIRE_BOWL, tiles.FIRE_BOWL_LIT, tiles.STATUE, tiles.SNOWDRIFT,
                  tiles.SLUSH, tiles.ICE_BLOCK, tiles.FROZEN_POND):
            self.assertTrue(t.name in palette.MAP_TILE or t.name in palette.MAP_TILE_BIOME, t.name)
            self.assertNotIn("~", "".join(t.glyphs), t.name)

    def test_the_floor_never_looks_like_his_shards(self):
        shard = "*"
        self.assertNotIn(shard, "".join(tiles.FROST_STONE.glyphs))


class CrownTest(unittest.TestCase):
    def test_a_burst_knocks_it_off_and_he_chases_it(self):
        f = Fight()
        f.b.take_damage(f.b.max_hp * 0.03, f.h, 0.0)
        self.assertTrue(f.b.crown_on)
        f.b.take_damage(f.b.max_hp * 0.035, f.h, 0.0)
        self.assertTrue(f.b.crownless)
        self.assertIn("CROWNLESS", f.b.bar_label)
        hp = f.b.hp
        f.b.take_damage(100, None, 0.0)
        self.assertAlmostEqual(hp - f.b.hp, 100 * config.CROWN_VULN)
        x0 = f.b.x
        f.run(0.5)
        self.assertNotEqual(f.b.x, x0)                  # waddling after it
        for _ in range(60 * 15):
            f.run(DT)
            if f.b.crown_on:
                break
        self.assertTrue(f.b.crown_on)                   # back on...
        self.assertGreater(f.b.crown_cd, 0)             # ...and stuck on a while
        self.assertTrue(any(p.owner is f.b for p in f.shots))   # (furious)

    def test_slow_damage_doesnt_knock_it(self):
        f = Fight()
        for _ in range(10):
            f.b.take_damage(f.b.max_hp * 0.01, f.h, 0.0)
            f.run(config.CROWN_KNOCK[1])
        self.assertTrue(f.b.crown_on)

    def test_kick_the_crown_away(self):
        f = Fight()
        f.b._knock_off(None)
        f.run(1.5)                                      # (it skids to a stop)
        cx, cy = f.b.crown[:2]
        f.h.x, f.h.y = cx - 0.8, cy
        f.run(1.0)
        self.assertGreater(f.b.crown[0], cx + 5)        # kicked on, away from the hero
        self.assertTrue(f.b.crownless)


class IceTest(unittest.TestCase):
    def test_black_ice_makes_you_slide(self):
        f = Fight()
        f.b.phase = 1
        f.run(2.0, "freeze")
        self.assertTrue(f.b.sheets)
        s = f.b.sheets[0]
        f.h.x, f.h.y = s["x"], s["y"]
        f.run(DT)
        self.assertEqual(f.h.traction, config.ICE_TRACTION)
        self.assertEqual(f.h.time_mult, config.ICE_TOP)
        f.h.x, f.h.y = 70.0, 40.0                       # (off the ice, still in the hall)
        f.run(DT)
        self.assertEqual(f.h.traction, 1.0)

    def test_a_lit_fire_melts_the_ice_near_it(self):
        f = Fight(hx=20.5, hy=12.0)
        f.b.sheets.append(dict(x=24.0, y=14.0, age=5.0))
        f.b.sheets.append(dict(x=90.0, y=30.0, age=5.0))
        f.run(config.BRAZIER_KINDLE + 0.2)
        self.assertIn(0, f.b.lit)
        self.assertIs(f.w.tile_at(20, 10), tiles.FIRE_BOWL_LIT)
        self.assertEqual([(s["x"], s["y"]) for s in f.b.sheets], [(90.0, 30.0)])
        f.h.x = 60.0
        f.run(config.FIRE_BURN)
        self.assertIs(f.w.tile_at(20, 10), tiles.FIRE_BOWL)

    def test_a_shattered_pillar_grows_back(self):
        f = Fight()
        f.w.damage_tile(60, 30, config.ICE_PILLAR_HP)
        self.assertIs(f.w.tile_at(60, 30), tiles.FROST_STONE)
        f.run(config.ICE_PILLAR_REGROW + 1.0)
        self.assertIs(f.w.tile_at(60, 30), tiles.ICE_PILLAR)


class FreezeTest(unittest.TestCase):
    def test_standing_still_chills_you_moving_warms_you(self):
        f = Fight()
        f.b.phase = 2
        f.run(2.0)
        self.assertAlmostEqual(f.h.chill, config.CHILL_STILL * 2.0, delta=0.5)
        f.h.vx = 5.0                                    # (moving)
        f.run(1.0)
        self.assertLess(f.h.chill, config.CHILL_STILL * 2.0)

    def test_full_chill_encases_you_and_rolls_break_out(self):
        f = Fight()
        f.b.phase = 2
        f.h.chill = config.CHILL_FULL
        f.run(DT)
        self.assertGreater(f.h.encased, 0)
        x0 = f.h.x
        f.h.move(1.0, 0.0, 0.5, f.w)
        self.assertEqual(f.h.x, x0)                     # can't move
        hp = f.h.hp
        f.b._hit(f.h, 10, 0.0)
        self.assertAlmostEqual(hp - f.h.hp, 10 * f.b.damage_mult * config.ENCASE[3], delta=0.5)
        class P:                                        # (just enough of a player for roll.step)
            pass
        p = P()
        p.hero = f.h
        for _ in range(config.ENCASE[1]):
            roll.step(None, p, PlayerInput(roll=True), DT)
        f.run(DT)
        self.assertEqual(f.h.encased, 0.0)
        self.assertLess(f.h.chill, config.CHILL_FULL)

    def test_a_partners_shots_break_the_ice(self):
        f = Fight()
        f.b.phase = 2
        mate = hero("huntress", 80.0, 22.0)
        f.h.chill = config.CHILL_FULL
        f.run(DT)
        for _ in range(4):
            f.shots.append(Projectile(f.h.x, f.h.y, 0.0, config.SNOW_SHOTS["shard"], owner=mate,
                                      damage=20))
        f.run(DT)
        self.assertEqual(f.h.encased, 0.0)


class MoveTest(unittest.TestCase):
    def test_penguins_slide_across_with_a_gap(self):
        f = Fight(hx=90.0)
        f.run(1.5, "penguins")
        n = config.SNOW_PENGUINS[1]
        self.assertTrue(0 < len(f.b.penguins) < n)
        f.run(6.0)
        self.assertEqual(f.b.penguins, [])

    def test_frost_breath_slows_you(self):
        f = Fight(hx=70.0)
        f.run(3.0, "breath")
        self.assertLess(f.h.hp, 10 ** 6)

    def test_every_move_runs_to_the_end(self):
        names = {m for ph in config.BOSSES["snow_king"].phases for m, _ in ph.moves}
        for phase in (0, 2):
            for name in sorted(names):
                f = Fight(hx=100.0)
                f.h.invulnerable = True
                f.b.phase = phase
                f.run(10.0, name)
                self.assertEqual(f.b.last_move, name, (phase, name))
                self.assertIsNone(f.b.breath, name)
                self.assertIsNone(f.b.wind, name)

    def test_his_death_clears_the_cold(self):
        f = Fight()
        f.b.phase = 2
        f.h.chill, f.h.encased, f.h.traction = 50.0, 1.0, 0.15
        f.b.on_death(f.ctx())
        self.assertEqual((f.h.chill, f.h.encased, f.h.traction), (0.0, 0.0, 1.0))


class QuestTest(unittest.TestCase):
    def tearDown(self):
        config.QUEST_FOCUS = None

    def test_shatter_the_block_keep_them_warm_and_free_them(self):
        m, s = game(seed=31)
        q = s.quests
        st = q.states["searching_sister"]
        self.assertEqual(st.spec.kind, "rescue")
        s.hero.invulnerable = True
        x, y = st.camp.spots[0]
        teleport(s, x + 2.0, y)
        step(s, 30)
        self.assertNotIn(0, st.opened)                  # still in the ice
        s.world.damage_tile(math.floor(x), math.floor(y), config.RESCUE_BLOCK_HP)
        step(s, 30)
        self.assertIn(0, st.opened)
        self.assertGreater(st.heat.get(0, 0.0), 0.0)
        self.assertTrue(st.wraiths.get(0))
        s.draw(m.text)
        w = st.wraiths[0][0]
        w.touched = True                                # a wraith reaches her
        before = st.heat[0]
        step(s, 1)
        self.assertLess(st.heat[0], before)
        st.heat[0] = config.RESCUE_THAW - 0.1
        step(s, 10)
        self.assertIn(0, st.lit)
        self.assertEqual(st.found, 1)

    def test_the_whole_fight(self):
        m, s = game(seed=31)
        q = s.quests
        st = q.states["searching_sister"]
        finish(q, "searching_sister")
        self.assertEqual(st.stage, "awake")
        s.hero.invulnerable = True
        lair = st.lair
        teleport(s, lair.cx + 20, lair.cy + 6)
        step(s, 1)
        self.assertEqual(st.stage, "fight")
        b = st.boss
        self.assertIsInstance(b, SnowKing)
        step(s, 300)
        b.phase = 2
        s.hero.chill = 50.0
        step(s, 5)
        s.draw(m.text)
        self.assertTrue(any(k in ("fire", "fire_lit") for _, _, k, _ in q.pins()))
        b.hp = 0.0
        b.last_hit_by = s.hero
        step(s)
        self.assertEqual(st.stage, "cleared")
        self.assertIn("snow_king", m.app.guild.achievements)
        self.assertEqual(m.app.guild.journal["searching_sister"]["wins"], 1)
        self.assertTrue(all(s.world.tile_at(*t) is tiles.FROST_STONE for t in lair.gate))
        self.assertEqual(s.hero.chill, 0.0)

    def test_dev_finish_frees_them(self):
        m, s = game(seed=31)
        config.QUEST_FOCUS = "searching_sister"
        st = s.quests.states["searching_sister"]
        self.assertTrue(s.quests.dev_finish_hunt())
        x, y = st.camp.spots[0]
        self.assertIs(s.world.tile_at(math.floor(x), math.floor(y)), tiles.SLUSH)


if __name__ == "__main__":
    unittest.main()
