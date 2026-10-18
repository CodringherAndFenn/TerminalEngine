"""M25.2: the forester's "destroy" quest (nut caches at the end of nut-shell
trails), the hollow oak, and Love & Cuddles (the hoard, the treetops,
tripwires and the frenzy)."""

import math
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.ai import make_enemy
from ascii_adventurers.ai.bosses import LoveCuddles, _crosses
from ascii_adventurers.ai.brain import AIContext
from ascii_adventurers.entities.projectile import Projectile
from ascii_adventurers.tests.test_m17 import game, step, teleport, world
from ascii_adventurers.tests.test_weapons import hero
from ascii_adventurers.world import tiles
from ascii_adventurers.world.landmarks import Landmark, quest_marks
from ascii_adventurers.world.test_map import LEGEND, TestMap

DT = 1 / 60
W, H = 140, 44
TREES = [(31.0, 11.0), (101.0, 31.0)]        # trunk middles (2 x 2 trunks round them)
OAK = (66.5, 38.5)


def hollow_oak():
    """An open map with two climbing oaks, and a lair over all of it."""
    rows = [["."] * W for _ in range(H)]
    for x, y in TREES:
        for dy in (-1, 0):
            for dx in (-1, 0):
                rows[int(y) + dy][int(x) + dx] = "K"
    m = TestMap(["".join(r) for r in rows], dict(LEGEND, K=tiles.OAK_TRUNK))
    lair = Landmark("hollow_oak", "lair", "forest", "OAK", 0, 0, [], cx=W / 2, cy=H / 2,
                    spots=[(W / 2, H / 2)], radii=(W / 2 + 2, H / 2 + 2),
                    props={"trees": list(TREES), "oak": OAK})
    return m, lair


class Fight:
    def __init__(self, hx=90.0, hy=22.0, bx=60.0, by=22.0, phase=0):
        self.w, self.lair = hollow_oak()
        self.b = make_enemy("love_cuddles", bx, by, random.Random(4))
        self.b.scale_to_level(1)
        self.b._rest = 99.0
        self.b.hoard_t = self.b.tree_t = self.b.wire_t = 999.0
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
        self.b.madness = 0.0

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
        """Start one of its signature moves now."""
        self.b._start(name)
        self.b._wait = 0.0


class OakTest(unittest.TestCase):
    def test_camp_and_hollow_oak_in_the_forest(self):
        for seed in (1, 2, 31, 999):
            w = world(seed)
            camp, lair = quest_marks(w.layout, "forester")
            self.assertEqual((camp.key, lair.key), ("forester_camp", "hollow_oak"), seed)
            for m in (camp, lair):
                self.assertEqual(w.layout.biome_at(m.cx, m.cy).name, "forest", seed)
            self.assertGreaterEqual(len(lair.props["trees"]), config.OAK_TREES - 2, seed)
            self.assertGreaterEqual(len(camp.spots), config.QUESTS["forester"].count)

    def test_its_oaks_hollow_oak_and_stumps(self):
        w = world(31)
        _, lair = quest_marks(w.layout, "forester")
        flat = {t for row in lair.rows for t in row if t is not None}
        self.assertTrue({tiles.OAK_ROOTS, tiles.DEAD_LEAVES, tiles.HOLLOW_TREE, tiles.OAK_TRUNK,
                         tiles.OAK_CROWN, tiles.STUMP} <= flat)
        x, y = lair.spots[0]
        self.assertTrue(lair.inside(x, y))
        self.assertFalse(lair.tile_at(math.floor(x), math.floor(y)).solid)
        b = make_enemy("love_cuddles", x, y, random.Random(1))
        b.lair = lair
        for i, (tx, ty) in enumerate(lair.props["trees"]):
            self.assertTrue(lair.inside(tx, ty))
            for cx, cy in b.trunk_tiles(i):
                self.assertIs(lair.tile_at(cx, cy), tiles.OAK_TRUNK)
            gx, gy = lair.gate[0]
            self.assertGreater(math.hypot(tx - gx, ty - gy), config.OAK_GATE_GAP - 4)

    def test_new_tiles_have_map_colors_and_no_shot_glyphs(self):
        from ascii_adventurers import palette
        from ascii_adventurers.render.ascii_fx import SHOT_LOOKS as _LOOKS
        floors = "".join(g for t in (tiles.DEAD_LEAVES, tiles.FOG, tiles.BARK, tiles.OAK_CROWN)
                         for g in t.glyphs)
        for look in ("acorn", "splinter", "cleaver"):
            head, trail, _ = _LOOKS[look]
            for ch in head + "".join(t for t in trail if t):
                if ch != " ":
                    self.assertNotIn(ch, floors, look)
        for t in (tiles.NUT_SHELLS, tiles.NUT_SPILL, tiles.NUT_CACHE, tiles.WOODPILE,
                  tiles.OAK_ROOTS, tiles.OAK_TRUNK, tiles.OAK_CROWN):
            self.assertTrue(t.name in palette.MAP_TILE or t.name in palette.MAP_TILE_BIOME, t.name)
            self.assertNotIn("~", "".join(t.glyphs), t.name)

    def test_trails_of_nut_shells_lead_to_the_caches_under_everything(self):
        w = world(31)
        marks = w.layout.landmarks
        camp, _ = quest_marks(w.layout, "forester")
        trails = [m for m in marks if m.key == "nut_trail"]
        self.assertEqual(len(trails), len(camp.spots))
        first_big = min(i for i, m in enumerate(marks) if m.kind != "spot")
        self.assertTrue(all(marks.index(t) < first_big for t in trails))   # (stamped first)
        for t, (x, y) in zip(sorted(trails, key=lambda t: (t.cx, t.cy)),
                             sorted(camp.spots)):
            self.assertEqual((t.cx, t.cy), (x, y))
            shells = sum(c is tiles.NUT_SHELLS for row in t.rows for c in row)
            self.assertGreater(shells, config.CACHE_TRAIL[0] // 3)


class DestroyTest(unittest.TestCase):
    def test_break_a_cache_and_more_squirrels_burst_out(self):
        m, s = game(seed=31)
        q = s.quests
        st = q.states["forester"]
        self.assertEqual(st.spec.kind, "destroy")
        x, y = st.camp.spots[0]
        tx, ty = math.floor(x), math.floor(y)
        teleport(s, x + 4, y + 0.5)
        self.assertIs(s.world.tile_at(tx, ty), tiles.NUT_CACHE)
        self.assertEqual(q.guards_left(st, 0), config.CARGO_GUARDS)
        s.hero.invulnerable = True
        step(s)
        before = sum(1 for e in s.enemies if getattr(e, "kind_key", "") == "rabid_squirrel")
        s.world.damage_tile(tx, ty, tiles.NUT_CACHE.hp // 2)
        step(s)
        self.assertEqual(st.found, 0)                          # (only damaged)
        s.world.damage_tile(tx, ty, tiles.NUT_CACHE.hp)
        step(s)
        self.assertIs(s.world.tile_at(tx, ty), tiles.NUT_SPILL)
        self.assertEqual(st.found, 1)
        self.assertIn(0, st.lit)
        after = sum(1 for e in s.enemies if getattr(e, "kind_key", "") == "rabid_squirrel")
        self.assertEqual(after - before, config.CACHE_BURST)
        self.assertEqual(len(q.open_targets(st)), len(st.camp.spots) - 1)

    def test_dev_finish_spills_the_caches(self):
        config.QUEST_FOCUS = "forester"
        try:
            m, s = game(seed=31)
            self.assertTrue(s.quests.dev_finish_hunt())
            st = s.quests.states["forester"]
            self.assertEqual(st.stage, "awake")
            x, y = st.camp.spots[0]
            teleport(s, x + 4, y)
            self.assertIs(s.world.tile_at(math.floor(x), math.floor(y)), tiles.NUT_SPILL)
        finally:
            config.QUEST_FOCUS = None


class HoardTest(unittest.TestCase):
    def test_it_buries_acorns_round_its_target(self):
        f = Fight()
        f.sign("bury")
        f.run(config.HOARD_TELL + 0.5)
        self.assertEqual(len(f.b.mounds), config.HOARD_MOUNDS)
        for mx, my in f.b.mounds:
            d = math.hypot(mx - f.h.x, (my - f.h.y) / 0.7)
            self.assertLessEqual(d, config.HOARD_NEAR[1] + 0.01)

    def test_it_digs_one_up_and_grows_stronger(self):
        f = Fight(hx=120.0)
        f.b.mounds = [[f.b.x + 3.0, f.b.y]]
        mult, speed = f.b.damage_mult, f.b.speed()
        dug = f.run(3.0 + config.HOARD_DIG, until=lambda: f.b.hoard == 1)
        self.assertTrue(dug)
        self.assertEqual(f.b.mounds, [])
        self.assertAlmostEqual(f.b.damage_mult, mult * (1 + config.HOARD_DMG))
        self.assertGreater(f.b.speed(), speed)
        self.assertIn("HOARD 1", f.b.bar_label)

    def test_digging_holds_its_moves_off(self):
        f = Fight(hx=120.0)
        f.b.mounds = [[f.b.x + 2.0, f.b.y]]
        f.b._rest = 0.0
        f.b._pick_move = lambda: "barrage"
        f.run(0.3)
        self.assertIsNone(f.b.move)
        self.assertGreater(f.b.digging, 0)

    def test_walk_over_a_mound_to_steal_it(self):
        f = Fight()
        f.b.mounds = [[f.h.x + 0.5, f.h.y]]
        f.h.hp = 100.0
        f.run(DT)
        self.assertEqual(f.b.mounds, [])
        self.assertEqual(f.b.hoard, 0)
        self.assertGreater(f.h.hp, 100.0)

    def test_it_spills_half_when_knocked_about(self):
        f = Fight()
        f.b._set_hoard(5)
        mult = f.b.damage_mult
        f.b._spill()
        self.assertEqual(f.b.hoard, 2)
        self.assertAlmostEqual(f.b.damage_mult, mult * (1 + 2 * config.HOARD_DMG)
                               / (1 + 5 * config.HOARD_DMG))
        f.b._set_hoard(99)
        self.assertEqual(f.b.hoard, config.HOARD_MAX)


class TreetopTest(unittest.TestCase):
    def climbed(self, f):
        f.sign("treetop")
        self.assertTrue(f.run(5.0, until=lambda: f.b.up))
        return f.b.tree

    def test_it_climbs_out_of_reach_only_from_phase_two(self):
        f = Fight(bx=40.0, by=16.0)
        f.b.tree_t = 0.0
        f.run(0.5)
        self.assertFalse(f.b.up)                           # (phase 1: no trees)
        f = Fight(bx=40.0, by=16.0, phase=1)
        f.b.tree_t = 0.0
        self.assertTrue(f.run(5.0, until=lambda: f.b.up))
        self.assertEqual(f.b.tree, 0)
        self.assertFalse(f.b.hittable)
        self.assertEqual((f.b.x, f.b.y), TREES[0])
        self.assertTrue(any(k == "oak" for _, _, k, _ in f.b.map_marks()))

    def test_it_pelts_acorns_from_up_there(self):
        f = Fight(bx=40.0, by=16.0, phase=1, hx=40.0, hy=26.0)
        self.climbed(f)
        f.run(config.TREE_PELT[0] * 2.5)
        self.assertGreaterEqual(len([p for p in f.shots if p.spec.look == "acorn"]),
                                config.TREE_PELT[1] * 2)

    def test_hit_the_trunk_and_it_falls_out(self):
        f = Fight(bx=40.0, by=16.0, phase=1, hx=40.0, hy=26.0)
        i = self.climbed(f)
        f.b._set_hoard(4)
        hp = f.b.hp
        need = config.TREE_SHAKE * f.b.max_hp
        tiles_ = f.b.trunk_tiles(i)
        f.w.damage_tile(*tiles_[0], need * 0.6)
        f.run(DT)
        self.assertTrue(f.b.up)
        self.assertAlmostEqual(f.b.shake_frac(), 0.6, places=2)
        f.w.damage_tile(*tiles_[3], need * 0.5)
        self.assertTrue(f.run(0.5, until=lambda: not f.b.up))
        self.assertTrue(f.b.hittable)
        self.assertGreater(f.b.dazed, 0)
        self.assertAlmostEqual(f.b.hp, hp - config.TREE_FALL * f.b.max_hp)
        self.assertEqual(f.b.hoard, 2)
        self.assertFalse(f.b._solid(f.b.x, f.b.y))         # (beside the trunk)
        self.assertIs(f.w.tile_at(*tiles_[0]), tiles.OAK_TRUNK)   # (it never breaks)

    def test_left_alone_it_pounces_down(self):
        f = Fight(bx=40.0, by=16.0, phase=1, hx=40.0, hy=26.0)
        self.climbed(f)
        f.b.shots = dict(f.b.shots)
        self.assertTrue(f.run(config.TREE_STAY + 4.0, until=lambda: not f.b.up))
        self.assertLess(math.hypot(f.b.x - f.h.x, f.b.y - f.h.y), 4.0)

    def test_it_leaps_to_the_oak_nearest_you_still_shaken(self):
        f = Fight(bx=40.0, by=16.0, phase=1, hx=100.0, hy=36.0)
        self.climbed(f)
        f.b.shake = 50.0
        self.assertTrue(f.run(config.TREE_LEAP[0] + 6.0, until=lambda: f.b.tree == 1))
        self.assertEqual((f.b.x, f.b.y), TREES[1])
        self.assertEqual(f.b.shake, 50.0)                  # (the shaking stays with it)

    def test_a_shot_into_its_crown_shakes_the_tree(self):
        f = Fight(bx=40.0, by=16.0, phase=1, hx=40.0, hy=26.0)
        i = self.climbed(f)
        x, y = TREES[i]
        shot = Projectile(x + 2.0, y + 1.0, 0.0, config.LOVE_SHOTS["acorn"], owner=f.h, damage=10)
        f.shots.append(shot)
        f.run(DT)
        self.assertAlmostEqual(f.b.shake, 10.0)
        self.assertFalse(shot.alive)
        f.run(DT)
        self.assertAlmostEqual(f.b.shake, 10.0)            # (counted once)


class WireTest(unittest.TestCase):
    def strung(self, hx=70.0, hy=17.0):
        f = Fight(phase=2, hx=hx, hy=hy)
        f.sign("string")
        f.run(config.WIRE_TELL + 1.0)
        self.assertTrue(f.b.wires)
        return f

    def test_wires_only_from_phase_three_between_oaks(self):
        f = Fight(phase=1)
        f.b.wire_t = 0.0
        f.run(0.5)
        self.assertEqual(f.b.wires, [])
        f = self.strung()
        anchors = set(TREES) | {OAK}
        for w in f.b.wires:
            self.assertIn((w[0], w[1]), anchors)
            self.assertIn((w[2], w[3]), anchors)
        self.assertLessEqual(len(f.b.wires), config.WIRES)

    def test_crossing_one_swings_a_log_down_it(self):
        self.assertTrue(_crosses(0, -1, 0, 1, -5, 0, 5, 0))
        self.assertFalse(_crosses(0, 1, 0, 2, -5, 0, 5, 0))
        f = self.strung()
        w = f.b.wires[0]
        mx, my = (w[0] + w[2]) / 2, (w[1] + w[3]) / 2
        a = math.atan2(w[3] - w[1], w[2] - w[0]) + math.pi / 2
        f.h.x, f.h.y = mx + math.cos(a) * 0.3, my + math.sin(a) * 0.3
        f.b._last = {}                                     # (no step from where it was)
        f.run(DT)
        f.h.x, f.h.y = mx - math.cos(a) * 0.3, my - math.sin(a) * 0.3
        f.run(DT)
        self.assertEqual(len(f.b.logs), 1)
        hp = f.h.hp
        f.run(config.WIRE_LOG[0] + 2.0)
        self.assertLess(f.h.hp, hp)
        self.assertEqual(f.b.logs, [])

    def test_a_roll_hops_a_wire(self):
        f = self.strung()
        w = f.b.wires[0]
        mx, my = (w[0] + w[2]) / 2, (w[1] + w[3]) / 2
        a = math.atan2(w[3] - w[1], w[2] - w[0]) + math.pi / 2
        f.h.x, f.h.y = mx + math.cos(a) * 0.3, my + math.sin(a) * 0.3
        f.b._last = {}
        f.run(DT)
        f.h.roll_t = 0.25
        f.h.x, f.h.y = mx - math.cos(a) * 0.3, my - math.sin(a) * 0.3
        f.run(DT)
        self.assertEqual(f.b.logs, [])

    def test_shoot_a_wire_to_cut_it(self):
        f = self.strung()
        n = len(f.b.wires)
        w = f.b.wires[0]
        mx, my = (w[0] + w[2]) / 2, (w[1] + w[3]) / 2
        f.shots.append(Projectile(mx, my, 0.0, config.LOVE_SHOTS["acorn"], owner=f.h, damage=5))
        f.run(DT)
        self.assertEqual(len(f.b.wires), n - 1)


class FrenzyTest(unittest.TestCase):
    def test_madness_fills_only_in_phase_three(self):
        f = Fight()
        f.b.take_damage(f.b.max_hp * 0.05, f.h, 0.0)
        self.assertEqual(f.b.madness, 0.0)
        f = Fight(phase=2)
        f.b.take_damage(f.b.max_hp * 0.05, f.h, 0.0)
        self.assertAlmostEqual(f.b.madness, config.FRENZY_HURT * 0.05)
        f.b.on_shot_hit(f.h, 5.0)
        self.assertAlmostEqual(f.b.madness, config.FRENZY_HURT * 0.05 + config.FRENZY_HIT)

    def test_full_it_dashes_in_a_zigzag_then_collapses(self):
        f = Fight(phase=2, hx=75.0)
        f.b.madness = 1.0
        hp = f.h.hp
        dashed = panted = False
        for _ in range(round(8.0 * 60)):
            f.run(DT)
            dashed = dashed or f.b.dashing
            if f.b.panting:
                panted = True
                break
        self.assertTrue(dashed and panted)
        self.assertLess(f.h.hp, hp)
        self.assertEqual(f.b.madness, 0.0)
        self.assertGreater(f.b.dazed, 0)
        self.assertIn("PANTING", f.b.bar_label)
        self.assertAlmostEqual(f.b.take_damage(100, f.h, 0.0), 100 * config.FRENZY_VULN)
        f.run(config.FRENZY_PANT + 0.5)
        self.assertFalse(f.b.panting)


class MoveTest(unittest.TestCase):
    def test_cleaver_spin_cuts_and_flings_its_blades(self):
        f = Fight(hx=64.0)
        hp = f.h.hp
        f.run(config.LOVE_SPIN[0] + config.LOVE_SPIN[3] + 0.4, move="spin")
        self.assertLess(f.h.hp, hp)
        self.assertEqual(len([p for p in f.shots if p.spec.look == "cleaver"]),
                         config.LOVE_SPIN[1])

    def test_acorn_barrage_three_fans(self):
        f = Fight()
        tell, fans, n, _, gap, _ = config.LOVE_BARRAGE
        f.run(tell + fans * gap + 0.2, move="barrage")
        self.assertEqual(len([p for p in f.shots if p.spec.look == "acorn"]), fans * n)

    def test_pinecones_land_where_marked_and_burst(self):
        f = Fight(hx=70.0)
        f.run(0.9, move="pinecones")                       # (the move's over; they fly on)
        self.assertEqual(len(f.b.cones), config.LOVE_CONES[1])
        self.assertTrue(any(math.hypot(c[2] - f.h.x, c[3] - f.h.y) < 1.0 for c in f.b.cones))
        hp = f.h.hp
        f.run(config.LOVE_CONES[0] + 1.0)
        self.assertEqual(f.b.cones, [])
        self.assertLess(f.h.hp, hp)
        self.assertTrue(any(p.spec.look == "splinter" for p in f.shots))

    def test_squirrel_gang_from_the_trees(self):
        f = Fight()
        f.run(config.LOVE_GANG[0] + 0.5, move="gang")
        lo, hi = config.LOVE_GANG[1]
        self.assertTrue(lo <= len(f.adds) <= hi)
        self.assertTrue(all(a.kind_key == "rabid_squirrel" and a.summoner is f.b for a in f.adds))
        for _ in range(3):
            f.run(config.LOVE_GANG[0] + 0.5, move="gang")
        self.assertLessEqual(len(f.adds), config.LOVE_GANG[2])

    def test_it_keeps_scuttling_through_its_moves(self):
        f = Fight(hx=75.0)
        x0, y0 = f.b.x, f.b.y
        f.run(config.LOVE_BARRAGE[0], move="barrage")
        self.assertGreater(math.hypot(f.b.x - x0, f.b.y - y0), 0.5)


class GameTest(unittest.TestCase):
    def test_the_fight_in_a_real_game(self):
        config.QUEST_FOCUS = "forester"
        try:
            m, s = game(seed=31)
            q = s.quests
            q.dev_finish_hunt()
            st = q.states["forester"]
            teleport(s, st.lair.cx, st.lair.cy + 12)
            s.hero.invulnerable = True
            step(s, 3)
            self.assertEqual(st.stage, "fight")
            b = st.boss
            self.assertIsInstance(b, LoveCuddles)
            b.hp = b.max_hp * 0.2
            for f in range(600):
                step(s)
                if f % 60 == 0:
                    s.draw(m.text)
            b.madness = 0.0
            b.tree_t = 0.0
            b._rest = 0.0
            self.assertTrue(any(b.up for _ in range(300) if step(s) is None))
            s.draw(m.text)
            self.assertTrue(b.alive)
        finally:
            config.QUEST_FOCUS = None


if __name__ == "__main__":
    unittest.main()
