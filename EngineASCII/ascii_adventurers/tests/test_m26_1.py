"""M26.1: the Mycelium "sever" quest (shared by all three Mycelium), the
fruiting ring, and Mycelium the fly agaric (warts, the mycelial network,
trip spores, the fly lure)."""

import math
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.ai import make_enemy
from ascii_adventurers.ai.bosses import Amanita, MycoPart
from ascii_adventurers.ai.brain import AIContext
from ascii_adventurers.systems.quests import circle_radius, circle_rules
from ascii_adventurers.tests.test_m17 import game, step, teleport, world
from ascii_adventurers.tests.test_weapons import hero
from ascii_adventurers.world import tiles
from ascii_adventurers.world.landmarks import Landmark, quest_marks
from ascii_adventurers.world.test_map import LEGEND, TestMap

DT = 1 / 60
W, H = 160, 50
RINGS = [(80.5, 25.5), (40.5, 25.5), (120.5, 25.5), (80.5, 8.5)]
THREADS = [(0, 1), (0, 2), (0, 3)]


def fruiting_ring():
    """An open map with four ring nodes joined by threads (the middle to
    each), and a lair over all of it."""
    rows = [["."] * W for _ in range(H)]
    for x, y in RINGS:
        rows[int(y)][int(x)] = "N"
    m = TestMap(["".join(r) for r in rows], dict(LEGEND, N=tiles.NET_NODE))
    lair = Landmark("amanita_ring", "lair", "mushroom", "MYCELIUM", 0, 0, [], cx=W / 2, cy=H / 2,
                    spots=[(W / 2, H / 2)], radii=(W / 2 + 2, H / 2 + 2),
                    props={"rings": list(RINGS), "threads": list(THREADS)})
    return m, lair


class Fight:
    def __init__(self, hx=80.0, hy=38.0, bx=60.0, by=38.0, phase=0, warts=True):
        self.w, self.lair = fruiting_ring()
        self.b = make_enemy("mycelium_amanita", bx, by, random.Random(4))
        self.b.scale_to_level(1)
        self.b._rest = 99.0
        self.b.regrow_t = self.b.net_t = self.b.trip_t = self.b.fly_t = 999.0
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
        if not warts:
            self.b.grown = True
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

    def warts(self):
        return [w for w in self.b.warts if w is not None and w.alive]


class RingTest(unittest.TestCase):
    def test_camp_and_fruiting_ring_in_the_mushroom_biome(self):
        for seed in (1, 2, 31, 999):
            w = world(seed)
            camp, lair = quest_marks(w.layout, "truffle_hunter")
            self.assertEqual((camp.key, lair.key), ("spore_camp", "amanita_ring"), seed)
            for m in (camp, lair):
                self.assertEqual(w.layout.biome_at(m.cx, m.cy).name, "mushroom", seed)
            self.assertEqual(len(lair.props["rings"]), config.NET_RINGS, seed)
            self.assertEqual(lair.name, "MYCELIUM")

    def test_rings_nodes_threads_and_cover(self):
        w = world(31)
        _, lair = quest_marks(w.layout, "truffle_hunter")
        flat = {t for row in lair.rows for t in row if t is not None}
        self.assertTrue({tiles.SHROOM_WALL, tiles.MYCELIUM, tiles.NET_NODE, tiles.RING_SHROOMS,
                         tiles.GIANT_SHROOM} <= flat)
        for x, y in lair.props["rings"]:
            self.assertIs(lair.tile_at(math.floor(x), math.floor(y)), tiles.NET_NODE)
        n = config.NET_RINGS
        self.assertEqual(len(lair.props["threads"]), 2 * (n - 1))
        x, y = lair.spots[0]
        self.assertTrue(lair.inside(x, y))

    def test_new_tiles_have_map_colors_and_no_shot_glyphs(self):
        from ascii_adventurers import palette
        from ascii_adventurers.render.ascii_fx import SHOT_LOOKS as _LOOKS
        floors = "".join(g for t in (tiles.MYCELIUM, tiles.RING_SHROOMS, tiles.NET_NODE_DEAD)
                         for g in t.glyphs)
        for look in ("red_spore", "white_spore"):
            head, trail, _ = _LOOKS[look]
            for ch in head + "".join(t for t in trail if t):
                if ch != " ":
                    self.assertNotIn(ch, floors, look)
        for t in (tiles.MYC_NODE, tiles.NODE_SPILL_RED, tiles.SHROOM_WALL, tiles.RING_SHROOMS,
                  tiles.NET_NODE_DEAD, tiles.NET_NODE):
            self.assertTrue(t.name in palette.MAP_TILE or t.name in palette.MAP_TILE_BIOME, t.name)
            self.assertNotIn("~", "".join(t.glyphs), t.name)


class SeverTest(unittest.TestCase):
    def test_every_mycelium_is_just_mycelium(self):
        q = config.QUESTS["truffle_hunter"]
        self.assertEqual(config.ENEMIES[q.boss].name, "Mycelium")
        self.assertEqual(config.BOSSES[q.boss].name, "Mycelium")
        self.assertIs(q.lines, config.MYCELIUM_LINES)
        self.assertEqual(q.lair_name, "MYCELIUM")
        text = " ".join(" ".join(lines) for _, lines in q.lines).lower()
        for word in ("agaric", "amanita", "red", "wart", "fly", "ink", "puffball"):
            self.assertNotIn(word, text)

    def test_the_rules_and_the_spill(self):
        r = circle_rules("sever", "amanita")
        self.assertEqual(r["time"], config.SEVER_TIME)
        self.assertIs(r["done"], tiles.NODE_SPILL_RED)
        self.assertEqual(circle_radius("sever", 5.0), config.SEVER_RADIUS)

    def test_stand_on_a_node_to_sever_it_while_sporelings_crawl_up(self):
        m, s = game(seed=31)
        q = s.quests
        st = q.states["truffle_hunter"]
        self.assertEqual(st.spec.kind, "sever")
        x, y = st.camp.spots[0]
        self.assertIs(s.world.tile_at(math.floor(x), math.floor(y)), tiles.MYC_NODE)
        teleport(s, x + 0.5, y + 0.5)
        s.hero.invulnerable = True
        step(s, round(config.SEVER_TIME * 0.6 * 60))
        crawlers = [e for e in s.enemies if getattr(e, "kind_key", "") == "sporeling"]
        self.assertGreaterEqual(len(crawlers), config.SEVER_WAVE_SIZE[0])
        step(s, round(config.SEVER_TIME * 0.5 * 60))
        self.assertIn(0, st.lit)
        self.assertEqual(st.found, 1)
        self.assertIs(s.world.tile_at(math.floor(x), math.floor(y)), tiles.NODE_SPILL_RED)


class WartTest(unittest.TestCase):
    def test_warts_go_on_and_armour_it(self):
        f = Fight()
        f.run(DT)
        self.assertEqual(len(f.warts()), len(config.WART_SPOTS))
        self.assertTrue(all(isinstance(w, MycoPart) and w.part_of is f.b for w in f.warts()))
        self.assertAlmostEqual(f.b.armour(), config.WART_ARMOR)
        self.assertAlmostEqual(f.b.take_damage(100, f.h, 0.0), 100 * config.WART_ARMOR)
        for w in f.warts():
            w.hp = 0
        f.run(DT)
        self.assertEqual(f.b.armour(), 1.0)
        self.assertAlmostEqual(f.b.take_damage(100, f.h, 0.0), 100)

    def test_warts_sit_on_its_cap_and_follow_it(self):
        f = Fight()
        f.run(DT)
        f.b.x += 5.0
        f.run(DT)
        for w in f.warts():
            dx, dy = config.WART_SPOTS[w.slot]
            self.assertAlmostEqual(w.x, f.b.x + dx, places=3)
            self.assertAlmostEqual(w.y, f.b.y + dy, places=3)

    def test_a_wart_shot_off_sprouts_a_toadstool_that_puffs(self):
        f = Fight(hx=60.0, hy=40.5)
        f.run(DT)
        f.warts()[0].hp = 0
        f.run(DT)
        self.assertEqual(len(f.b.sprouts), 1)
        f.h.x, f.h.y = f.b.sprouts[0][0], f.b.sprouts[0][1]
        hp = f.h.hp
        f.run(config.WART_SPROUT[0] + 0.1)
        self.assertEqual(f.b.sprouts, [])
        self.assertLess(f.h.hp, hp)

    def test_it_drinks_and_regrows_warts(self):
        f = Fight()
        f.run(DT)
        for w in f.warts()[:5]:
            w.hp = 0
        f.run(DT)
        self.assertEqual(len(f.warts()), 3)
        f.b.regrow_t = 0.0
        f.run(config.WART_REGROW[1] + 0.5)
        self.assertEqual(len(f.warts()), 3 + config.WART_REGROW[2])

    def test_warts_scale_with_its_health(self):
        f = Fight()
        f.b.max_hp *= 2
        f.run(DT)
        self.assertAlmostEqual(f.warts()[0].max_hp, config.WART_HP * 2)


class NetworkTest(unittest.TestCase):
    def test_it_travels_the_threads_to_the_ring_nearest_you(self):
        f = Fight(hx=120.5, hy=30.0, bx=40.5, by=30.0, phase=1, warts=False)
        f.sign("network")
        f.run(DT)
        self.assertEqual(f.b.lit[1:], [RINGS[1], RINGS[0], RINGS[2]])   # (by the middle)
        self.assertTrue(f.run(config.NET_TELL + 0.2, until=lambda: f.b.submerged))
        self.assertFalse(f.b.hittable)
        self.assertTrue(f.run(10.0, until=lambda: not f.b.submerged))
        self.assertLess(math.hypot(f.b.x - RINGS[2][0], f.b.y - RINGS[2][1]), 4.0)
        self.assertTrue(f.b.hittable)

    def test_a_lit_thread_burns(self):
        f = Fight(hx=60.5, hy=25.5, bx=40.5, by=30.0, phase=1, warts=False)
        f.b.lit = [RINGS[1], RINGS[0]]
        f.b.lit_t = 2.0
        hp = f.h.hp
        f.run(0.6)
        self.assertLess(f.h.hp, hp)

    def test_break_a_node_and_its_ring_is_cut_out_then_regrows(self):
        f = Fight(hx=120.5, hy=30.0, bx=40.5, by=30.0, phase=1, warts=False)
        f.w.damage_tile(math.floor(RINGS[0][0]), math.floor(RINGS[0][1]), config.NODE_HP)
        f.run(DT)
        self.assertNotIn(0, f.b.live_rings())
        self.assertIsNone(f.b._route(1, 2, f.b.live_rings()))       # (no way through)
        f.run(config.NODE_REGROW + 0.2)
        self.assertIn(0, f.b.live_rings())

    def test_only_from_phase_two(self):
        f = Fight(warts=False)
        f.b.net_t = 0.0
        f.run(0.5)
        self.assertNotEqual(f.b.move, "network")


class TripTest(unittest.TestCase):
    def test_linger_in_a_cloud_and_you_trip_and_drift(self):
        f = Fight(phase=2, warts=False)
        f.sign("trip")
        f.run(config.TRIP_TELL + 0.1)
        self.assertEqual(len(f.b.clouds), config.TRIP_CLOUDS)
        c = f.b.clouds[0]
        f.h.x, f.h.y = c[0], c[1]
        f.run(config.TRIP_IN + 0.1)
        self.assertTrue(f.b.tripping(f.h))
        x0, y0 = f.h.x, f.h.y
        f.run(0.5)
        self.assertGreater(math.hypot(f.h.x - x0, f.h.y - y0), 0.3)    # (drifting)

    def test_a_roll_clears_your_head(self):
        f = Fight(phase=2, warts=False)
        f.b.trip[id(f.h)] = 3.0
        f.h.roll_t = 0.2
        f.run(DT)
        self.assertFalse(f.b.tripping(f.h))

    def test_tripping_you_see_fake_shots_that_dont_hurt(self):
        f = Fight(phase=2, warts=False, hx=70.0)
        f.b.trip[id(f.h)] = 5.0
        f.run(config.AMANITA_SPORES[0] + 1.0, move="spores")
        real = [p for p in f.shots if p.owner is f.b]
        self.assertTrue(real)
        self.assertGreaterEqual(len(f.b.fakes), len(real) // 2)


class FlyTest(unittest.TestCase):
    def test_flies_circle_it_and_one_drops_dead_bursting(self):
        f = Fight(phase=2, warts=False)
        f.sign("flies")
        f.run(config.FLY_TELL + 0.2)
        self.assertEqual(len(f.b.flies), config.FLIES)
        for fl in f.b.flies:
            d = math.hypot(fl.x - f.b.x, fl.y - (f.b.y - 1.0))
            self.assertLess(d, config.FLY_ORBIT[0] + 1.0)
        f.run(config.FLY_DROP[0] + 0.1)
        self.assertEqual(len(f.b.flies), config.FLIES - 1)

    def test_flies_soak_shots_and_hide_underground(self):
        f = Fight(phase=2, warts=False)
        f.sign("flies")
        f.run(config.FLY_TELL + 0.2)
        fl = f.b.flies[0]
        self.assertTrue(fl.hittable)
        f.b.submerged = True
        self.assertFalse(fl.hittable)


class MoveTest(unittest.TestCase):
    def test_cap_slam_lands_where_shown(self):
        f = Fight(hx=70.0, warts=False)
        hp = f.h.hp
        f.run(0.2, move="slam")
        self.assertIsNotNone(f.b.slam_at)
        self.assertFalse(f.b.hittable)                    # (up in the air)
        f.run(config.AMANITA_SLAM[0] + 0.8)
        self.assertLess(f.h.hp, hp)
        self.assertTrue(any(p.spec.look == "white_spore" for p in f.shots))

    def test_spore_volleys(self):
        f = Fight(warts=False)
        f.run(config.AMANITA_SPORES[0] + 2.5, move="spores")
        self.assertTrue(any(p.owner is f.b for p in f.shots))

    def test_toadstool_sprouts_pop_along_the_cracks(self):
        f = Fight(hx=70.0, warts=False)
        hp = f.h.hp
        f.run(config.AMANITA_SPROUTS[0] * 0.5, move="sprouts")
        self.assertTrue(f.b.cracks)
        f.b._pick_move = lambda: "spores"                 # (no second round of sprouts)
        f.run(3.0)
        self.assertLess(f.h.hp, hp)
        self.assertEqual(f.b.pending, [])

    def test_stem_spin_glides_at_you(self):
        f = Fight(hx=70.0, warts=False)
        hp = f.h.hp
        d0 = math.hypot(f.h.x - f.b.x, f.h.y - f.b.y)
        f.run(config.AMANITA_SPIN[0] + 1.0, move="spin")
        self.assertLess(math.hypot(f.h.x - f.b.x, f.h.y - f.b.y), d0)
        f.run(2.5)
        self.assertLess(f.h.hp, hp)


class GameTest(unittest.TestCase):
    def test_the_fight_in_a_real_game(self):
        config.QUEST_FOCUS = "truffle_hunter"
        try:
            m, s = game(seed=31)
            q = s.quests
            q.dev_finish_hunt()
            st = q.states["truffle_hunter"]
            teleport(s, st.lair.cx, st.lair.cy + 12)
            s.hero.invulnerable = True
            step(s, 3)
            self.assertEqual(st.stage, "fight")
            b = st.boss
            self.assertIsInstance(b, Amanita)
            step(s, 2)
            self.assertEqual(b.warts_on(), len(config.WART_SPOTS))
            b.hp = b.max_hp * 0.2
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
