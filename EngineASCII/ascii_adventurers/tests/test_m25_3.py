"""M25.3: the lumberjack's "fell" quest (marked trees, some of them mimic
saplings), the still grove, and The Fallen (which tree?, root web, swallow
and spit)."""

import math
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.ai import make_enemy
from ascii_adventurers.ai.bosses import TheFallen
from ascii_adventurers.ai.brain import AIContext
from ascii_adventurers.entities.projectile import Projectile
from ascii_adventurers.systems.quests import QUEST_SID
from ascii_adventurers.tests.test_m17 import game, step, teleport, world
from ascii_adventurers.tests.test_weapons import hero
from ascii_adventurers.world import tiles
from ascii_adventurers.world.landmarks import Landmark, quest_marks
from ascii_adventurers.world.test_map import LEGEND, TestMap

DT = 1 / 60
W, H = 140, 50
TREES = [(40.5, 15.5), (52.5, 15.5), (64.5, 15.5), (76.5, 15.5), (88.5, 15.5)]
FIRES = [(100.5, 40.5)]


def grove():
    """An open map with a row of grove trees (trunks 2 below each), a fire
    bowl, and a lair over all of it."""
    rows = [["."] * W for _ in range(H)]
    for x, y in TREES:
        rows[int(y) + 2][int(x)] = "K"
    for x, y in FIRES:
        rows[int(y)][int(x)] = "F"
    m = TestMap(["".join(r) for r in rows], dict(LEGEND, K=tiles.GROVE_TRUNK, F=tiles.GROVE_FIRE))
    lair = Landmark("still_grove", "lair", "forest", "GROVE", 0, 0, [], cx=W / 2, cy=H / 2,
                    spots=[(W / 2, H / 2)], radii=(W / 2 + 2, H / 2 + 2),
                    props={"trees": list(TREES), "fires": list(FIRES)})
    return m, lair


class Fight:
    def __init__(self, hx=64.0, hy=30.0, bx=64.0, by=40.0, phase=0):
        self.w, self.lair = grove()
        self.b = make_enemy("the_fallen", bx, by, random.Random(4))
        self.b.scale_to_level(1)
        self.b._rest = 99.0
        self.b.hide_t = self.b.root_t = self.b.maw_t = 999.0
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
                move = None
            if until is not None and until():
                return True
        return False

    def sign(self, name):
        self.b._start(name)
        self.b._wait = 0.0

    def shoot_at(self, x, y, owner=None):
        """A hero's shot right in front of (x, y), flying at it."""
        p = Projectile(x - 0.3, y, 0.0, config.LOVE_SHOTS["acorn"], owner=owner or self.h,
                       damage=10)
        self.shots.append(p)
        return p


class GroveTest(unittest.TestCase):
    def test_camp_and_still_grove_in_the_forest(self):
        for seed in (1, 2, 31, 999):
            w = world(seed)
            camp, lair = quest_marks(w.layout, "lumberjack")
            self.assertEqual((camp.key, lair.key), ("lumber_camp", "still_grove"), seed)
            for m in (camp, lair):
                self.assertEqual(w.layout.biome_at(m.cx, m.cy).name, "forest", seed)
            self.assertEqual(len(lair.props["trees"]), config.GROVE_TREES, seed)
            self.assertEqual(len(lair.props["fires"]), config.GROVE_FIRES, seed)

    def test_its_trees_fires_trunk_and_stumps(self):
        w = world(31)
        _, lair = quest_marks(w.layout, "lumberjack")
        flat = {t for row in lair.rows for t in row if t is not None}
        self.assertTrue({tiles.THICKET, tiles.DEAD_LEAVES, tiles.FALLEN_TRUNK, tiles.GROVE_TRUNK,
                         tiles.GROVE_FIRE, tiles.STUMP} <= flat)
        x, y = lair.spots[0]
        self.assertTrue(lair.inside(x, y))
        trees = lair.props["trees"]
        for i, (tx, ty) in enumerate(trees):
            self.assertIs(lair.tile_at(math.floor(tx), math.floor(ty) + 2), tiles.GROVE_TRUNK)
            for ux, uy in trees[i + 1:]:
                self.assertGreaterEqual(math.hypot(tx - ux, ty - uy), config.GROVE_TREE_GAP)
        for fx, fy in lair.props["fires"]:
            self.assertIs(lair.tile_at(math.floor(fx), math.floor(fy)), tiles.GROVE_FIRE)

    def test_new_tiles_have_map_colors_and_no_shot_glyphs(self):
        from ascii_adventurers import palette
        from ascii_adventurers.render.ascii_fx import SHOT_LOOKS as _LOOKS
        floors = "".join(g for t in (tiles.DEAD_LEAVES, tiles.FOG, tiles.BARK) for g in t.glyphs)
        for look in ("leaf", "sap_spit", "splinter"):
            head, trail, _ = _LOOKS[look]
            for ch in head + "".join(t for t in trail if t):
                if ch != " ":
                    self.assertNotIn(ch, floors, look)
        for t in (tiles.FELLED, tiles.MARKED_TREE, tiles.SAWHORSE, tiles.THICKET,
                  tiles.GROVE_TRUNK, tiles.FALLEN_TRUNK, tiles.GROVE_FIRE):
            self.assertTrue(t.name in palette.MAP_TILE or t.name in palette.MAP_TILE_BIOME, t.name)
            self.assertNotIn("~", "".join(t.glyphs), t.name)


class FellTest(unittest.TestCase):
    def test_fell_a_marked_tree_and_it_counts_or_rips_free(self):
        m, s = game(seed=31)
        q = s.quests
        st = q.states["lumberjack"]
        self.assertEqual(st.spec.kind, "fell")
        plain = next(i for i in range(len(st.camp.spots)) if not q.is_sapling(st, i))
        sap = next(i for i in range(len(st.camp.spots)) if q.is_sapling(st, i))
        s.hero.invulnerable = True
        # A plain one: felled, it counts.
        x, y = st.camp.spots[plain]
        teleport(s, x + 4, y + 0.5)
        self.assertIs(s.world.tile_at(math.floor(x), math.floor(y)), tiles.MARKED_TREE)
        s.world.damage_tile(math.floor(x), math.floor(y), tiles.MARKED_TREE.hp)
        step(s)
        self.assertIs(s.world.tile_at(math.floor(x), math.floor(y)), tiles.FELLED)
        self.assertEqual(st.found, 1)
        # A sapling: it rips free, and counts once it's dead.
        x, y = st.camp.spots[sap]
        teleport(s, x + 4, y + 0.5)
        s.world.damage_tile(math.floor(x), math.floor(y), tiles.MARKED_TREE.hp)
        step(s, 3)
        self.assertEqual(st.found, 1)
        self.assertIn(sap, st.opened)
        sapling = next(e for e in s.enemies if e.spawn_id == (QUEST_SID, st.qid, sap, 1))
        self.assertEqual(sapling.kind_key, "mimic_sapling")
        sapling.hp = 0
        sapling.last_hit_by = None
        step(s, 3)
        self.assertEqual(st.found, 2)
        self.assertIn(sap, st.lit)

    def test_about_one_in_three_are_saplings(self):
        m, s = game(seed=31)
        st = s.quests.states["lumberjack"]
        n = sum(s.quests.is_sapling(st, i) for i in range(len(st.camp.spots)))
        self.assertTrue(2 <= n <= 10, n)

    def test_dev_finish_fells_them_all(self):
        config.QUEST_FOCUS = "lumberjack"
        try:
            m, s = game(seed=31)
            self.assertTrue(s.quests.dev_finish_hunt())
            st = s.quests.states["lumberjack"]
            self.assertEqual(st.stage, "awake")
            x, y = st.camp.spots[0]
            teleport(s, x + 4, y)
            self.assertIs(s.world.tile_at(math.floor(x), math.floor(y)), tiles.FELLED)
        finally:
            config.QUEST_FOCUS = None


class HideTest(unittest.TestCase):
    def hidden(self, **kw):
        f = Fight(**kw)
        f.sign("hide")
        self.assertTrue(f.run(config.HIDE_TELL + 0.5, until=lambda: f.b.hidden))
        return f

    def test_it_becomes_one_of_the_trees_near_you(self):
        f = Fight(hx=40.5, hy=28.0)
        f.b.hide_t = 0.0
        self.assertTrue(f.run(config.HIDE_TELL + 0.5, until=lambda: f.b.hidden))
        self.assertIn((f.b.x, f.b.y), TREES)
        self.assertFalse(f.b.hittable)
        self.assertTrue(f.b.among)
        self.assertNotIn("FIND THE EYE", f.b.espec.name)
        self.assertIn("FIND THE EYE", f.b.bar_label)

    def test_never_next_to_a_hero(self):
        f = Fight(hx=64.5, hy=15.5 + 3.0)
        f.sign("hide")
        f.run(config.HIDE_TELL + 0.5)
        self.assertNotEqual((f.b.x, f.b.y), TREES[2])

    def test_its_eye_opens_now_and_then(self):
        f = self.hidden()
        opened = 0
        for _ in range(round(6 * 60)):
            f.run(DT)
            opened += f.b.eye_open > 0
        self.assertGreater(opened, 30)
        self.assertLess(opened, 6 * 60 * 0.4)

    def test_a_shot_into_a_fake_spits_back_at_you(self):
        f = self.hidden()
        fake = next(i for i in f.b.among if i != f.b.hid_at)
        x, y = TREES[fake]
        shot = f.shoot_at(x, y)
        n = len(f.shots)
        f.run(DT)
        self.assertFalse(shot.alive)
        self.assertTrue(f.b.hidden)
        spat = [p for p in f.shots if p.owner is f.b]
        self.assertGreaterEqual(len(spat), config.HIDE_SPIT)
        self.assertGreaterEqual(len(f.shots), n - 1 + config.HIDE_SPIT)

    def test_a_hit_on_its_tree_drags_it_out(self):
        f = self.hidden()
        hp = f.b.hp
        x, y = TREES[f.b.hid_at]
        f.shoot_at(x, y)
        f.run(DT)
        self.assertFalse(f.b.hidden)
        self.assertTrue(f.b.hittable)
        self.assertGreater(f.b.dazed, 0)
        self.assertAlmostEqual(f.b.hp, hp - config.HIDE_FOUND * f.b.max_hp)
        self.assertNotIn((f.b.x, f.b.y), TREES)                  # (stepped out)

    def test_a_blow_on_its_trunk_finds_it_too(self):
        f = self.hidden()
        f.w.damage_tile(*f.b.trunk_tile(f.b.hid_at), 20)
        f.run(DT)
        self.assertFalse(f.b.hidden)

    def test_not_found_it_bursts_out(self):
        f = self.hidden()
        x, y = TREES[f.b.hid_at]
        f.h.x, f.h.y = x + 2.5, y + 1.0
        f.b._last_h = None
        hp = f.h.hp
        self.assertTrue(f.run(config.HIDE_TIME + 1.0, until=lambda: not f.b.hidden))
        f.run(0.2)
        self.assertLess(f.h.hp, hp)
        self.assertEqual(f.b.dazed, 0.0)

    def test_the_trees_lash_out_while_it_hides(self):
        f = self.hidden(hx=52.0, hy=24.0)
        f.run(config.HIDE_LASH * 2.5)
        self.assertTrue(any(p.spec.look == "splinter" for p in f.shots))

    def test_trees_are_cover_when_it_isnt_hiding(self):
        f = Fight()
        shot = f.shoot_at(*TREES[0])
        f.run(DT)
        self.assertFalse(shot.alive)
        self.assertFalse(any(p.owner is f.b for p in f.shots))   # (no spitting back)


class RootTest(unittest.TestCase):
    def test_roots_only_from_phase_two_and_one_at_you(self):
        f = Fight()
        f.b.root_t = 0.0
        f.run(0.5)
        self.assertEqual(f.b.roots, [])
        f = Fight(phase=1)
        f.b.root_t = 0.0
        f.run(config.ROOT_TELL + 0.3)
        self.assertEqual(len(f.b.roots), config.ROOT_LINES)
        a = math.atan2(f.h.y - (f.b.y + 1.8), f.h.x - f.b.x)
        self.assertTrue(any(abs((r[2] - a + math.pi) % math.tau - math.pi) < 0.2
                            for r in f.b.roots))

    def test_a_root_grabs_squeezes_and_lets_go(self):
        f = Fight(phase=1, hx=64.0, hy=33.0)
        f.sign("roots")
        hp = f.h.hp
        self.assertTrue(f.run(2.0, until=lambda: f.b.held))
        self.assertEqual(f.h.slow_mult, 0.0)
        f.run(config.ROOT_HOLD + 0.1)
        self.assertEqual(f.b.held, {})
        self.assertLess(f.h.hp, hp)
        self.assertIn(id(f.h), f.b.immune)

    def test_shoot_the_root_holding_you(self):
        f = Fight(phase=1, hx=64.0, hy=33.0)
        f.sign("roots")
        self.assertTrue(f.run(2.0, until=lambda: f.b.held))
        r = next(iter(f.b.held.values()))[0]
        x0, y0, x1, y1 = f.b.root_seg(r)
        f.shoot_at((x0 + x1) / 2, (y0 + y1) / 2)
        f.run(2 * DT)
        self.assertEqual(f.b.held, {})

    def test_a_roll_steps_over_roots(self):
        f = Fight(phase=1, hx=64.0, hy=33.0)
        f.h.roll_t = 5.0
        f.sign("roots")
        f.run(2.0)
        self.assertEqual(f.b.held, {})

    def test_fire_sears_a_root_away(self):
        f = Fight(phase=1, hx=100.5, hy=37.5, bx=88.0, by=34.0)
        f.sign("roots")
        f.run(config.ROOT_TELL + 2.5)
        fx, fy = FIRES[0]
        for r in f.b.roots:
            x0, y0, x1, y1 = f.b.root_seg(r)
            self.assertGreater(math.hypot(x1 - fx, y1 - fy), config.FIRE_SEAR - 0.6)
        self.assertTrue(any(e.label == "SEARED!" for e in f.effects if e.kind == "toast"))


class MawTest(unittest.TestCase):
    def opened(self):
        f = Fight(phase=2)
        f.sign("maw")
        self.assertTrue(f.run(config.MAW_TELL + 0.2, until=lambda: f.b.maw_open))
        return f

    def test_it_swallows_then_spits_them_back(self):
        f = self.opened()
        hp = f.b.hp
        for _ in range(5):
            self.assertEqual(f.b.take_damage(10, f.h, 0.0), 0.0)
        self.assertEqual(f.b.hp, hp)
        self.assertEqual(f.b.swallowed, 5)
        f.run(config.MAW_OPEN + 1.0)
        spat = [p for p in f.shots if p.spec.look == "sap_spit"]
        self.assertGreaterEqual(len(spat), config.MAW_SPIT[0] - 2)
        self.assertFalse(f.b.maw_open)
        self.assertGreater(f.b.take_damage(10, f.h, 0.0), 0.0)

    def test_stuffed_it_chokes(self):
        f = self.opened()
        f.b.take_damage(config.MAW_CHOKE * f.b.max_hp + 1, f.h, 0.0)
        f.run(DT * 2)
        self.assertFalse(f.b.maw_open)
        self.assertGreater(f.b.dazed, 0)
        self.assertIn("DAZED", f.b.bar_label)

    def test_maw_only_in_phase_three(self):
        f = Fight(phase=1)
        f.b.maw_t = 0.0
        f.run(1.5)
        self.assertFalse(f.b.maw_open)
        self.assertNotEqual(f.b.move, "maw")


class MoveTest(unittest.TestCase):
    def test_branch_sweep_hits_in_its_arc_not_behind(self):
        f = Fight(hx=64.0, hy=35.0)
        hp = f.h.hp
        f.run(config.FALLEN_SWEEP[0] + config.FALLEN_SWEEP[4] + 0.4, move="sweep")
        self.assertLess(f.h.hp, hp)
        g = Fight(hx=64.0, hy=35.0)
        g.b._pick_move = lambda: "sweep"
        g.b._rest = 0.0
        self.assertTrue(g.run(config.FALLEN_SWEEP[0] + 0.5, until=lambda: g.b.arc is not None
                              and g.b.sweep_at is not None))
        a = g.b.arc[0] + math.pi                          # (now behind it)
        g.h.x, g.h.y = g.b.x + math.cos(a) * 4, g.b.y + math.sin(a) * 4
        hp = g.h.hp
        g.run(config.FALLEN_SWEEP[4] + 0.3)
        self.assertEqual(g.h.hp, hp)

    def test_uproot_charge_and_landing_ring(self):
        f = Fight(hx=64.0, hy=30.0)
        hp = f.h.hp
        f.run(config.FALLEN_CHARGE[0] + 1.5, move="uproot")
        self.assertLess(f.h.hp, hp)
        self.assertTrue(any(p.spec.look == "splinter" for p in f.shots))

    def test_leaf_storm(self):
        f = Fight()
        f.run(config.FALLEN_LEAVES[0] + 1.0, move="leaves")
        self.assertTrue(any(p.spec.look == "leaf" for p in f.shots))

    def test_sap_puddles_slow_and_beetles_crawl_out(self):
        f = Fight(hx=64.0, hy=30.0)
        f.run(config.FALLEN_SAP[0] + 1.2, move="sap")
        self.assertEqual(len(f.b.puddles), config.FALLEN_SAP[1])
        p = f.b.puddles[0]
        f.h.x, f.h.y = p[0], p[1]
        f.run(DT)
        self.assertAlmostEqual(f.h.slow_mult, config.FALLEN_SAP[4])
        lo, hi = config.FALLEN_SAP[6]
        self.assertTrue(lo <= len(f.adds) <= hi)
        self.assertTrue(all(a.kind_key == "bark_beetle" for a in f.adds))

    def test_it_keeps_stalking_through_its_moves(self):
        f = Fight(hx=64.0, hy=22.0)
        x0, y0 = f.b.x, f.b.y
        f.run(config.FALLEN_LEAVES[0], move="leaves")
        self.assertGreater(math.hypot(f.b.x - x0, f.b.y - y0), 0.5)


class GameTest(unittest.TestCase):
    def test_the_fight_in_a_real_game(self):
        config.QUEST_FOCUS = "lumberjack"
        try:
            m, s = game(seed=31)
            q = s.quests
            q.dev_finish_hunt()
            st = q.states["lumberjack"]
            teleport(s, st.lair.cx, st.lair.cy + 12)
            s.hero.invulnerable = True
            step(s, 3)
            self.assertEqual(st.stage, "fight")
            b = st.boss
            self.assertIsInstance(b, TheFallen)
            b.hp = b.max_hp * 0.2
            b.hide_t = 0.0
            for f in range(900):
                step(s)
                if f % 60 == 0:
                    s.draw(m.text)
            self.assertTrue(b.alive)
        finally:
            config.QUEST_FOCUS = None


if __name__ == "__main__":
    unittest.main()
