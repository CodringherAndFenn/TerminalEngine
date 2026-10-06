"""M25.1: the hedge witch's "cleanse" quest, the withered glade, and Nettle,
the Blighted (glamour copies, shrinking dust, blight seeds)."""

import math
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.ai import make_enemy
from ascii_adventurers.ai.bosses import Glamour, Nettle
from ascii_adventurers.ai.brain import AIContext
from ascii_adventurers.systems import combat
from ascii_adventurers.systems.quests import circle_radius
from ascii_adventurers.tests.test_m17 import game, step, teleport, world
from ascii_adventurers.tests.test_m22_5 import finish
from ascii_adventurers.tests.test_weapons import Dummy, hero
from ascii_adventurers.world import tiles
from ascii_adventurers.world.landmarks import Landmark, quest_marks
from ascii_adventurers.world.test_map import LEGEND, TestMap

DT = 1 / 60
W, H = 140, 44
CAPS = [(20.5, 10.5), (120.5, 34.5)]


def glade(walls=()):
    """An open map with growcaps at (20, 10) and (120, 34), and a lair over
    all of it."""
    rows = [["."] * W for _ in range(H)]
    for x, y in CAPS:
        rows[int(y)][int(x)] = "G"
    for x, y in walls:
        rows[y][x] = "#"
    m = TestMap(["".join(r) for r in rows], dict(LEGEND, G=tiles.GROWCAP))
    lair = Landmark("glade", "lair", "forest", "GLADE", 0, 0, [], cx=W / 2, cy=H / 2,
                    spots=[(W / 2, H / 2)], radii=(W / 2 + 2, H / 2 + 2),
                    props={"growcaps": list(CAPS)})
    return m, lair


class Fight:
    def __init__(self, hx=90.0, hy=22.0, bx=60.0, by=22.0, walls=()):
        self.w, self.lair = glade(walls)
        self.b = make_enemy("nettle", bx, by, random.Random(4))
        self.b.scale_to_level(1)
        self.b._rest = 99.0
        self.b.decoy_t = 999.0
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
            self.b.last_move = None
            self.b._pick_move = lambda m=move: m
        for _ in range(round(seconds * 60)):
            self.b.think(self.ctx(), DT)
            if move is not None and self.b.last_move == move:
                self.b._rest = 99.0
                move = None


class GladeTest(unittest.TestCase):
    def test_camp_and_glade_in_the_forest(self):
        for seed in (1, 2, 31, 999):
            w = world(seed)
            camp, lair = quest_marks(w.layout, "hedge_witch")
            self.assertEqual((camp.key, lair.key), ("witch_camp", "glade"), seed)
            for m in (camp, lair):
                self.assertEqual(w.layout.biome_at(m.cx, m.cy).name, "forest", seed)
            self.assertEqual(len(lair.props["growcaps"]), config.GLADE_GROWCAPS, seed)
            self.assertGreaterEqual(len(camp.spots), config.QUESTS["hedge_witch"].count)

    def test_its_tree_toadstools_growcaps_and_stumps(self):
        w = world(31)
        camp, lair = quest_marks(w.layout, "hedge_witch")
        flat = {t for row in lair.rows for t in row if t is not None}
        self.assertTrue({tiles.BRAMBLE_WALL, tiles.DEAD_LEAVES, tiles.HOLLOW_TREE, tiles.TOADSTOOL,
                         tiles.GROWCAP, tiles.STUMP, tiles.FOG} <= flat)
        x, y = lair.spots[0]
        self.assertTrue(lair.inside(x, y))
        self.assertFalse(lair.tile_at(math.floor(x), math.floor(y)).solid)
        for gx, gy in lair.props["growcaps"]:
            self.assertIs(lair.tile_at(math.floor(gx), math.floor(gy)), tiles.GROWCAP)
        toadstools = sum(t is tiles.TOADSTOOL for row in lair.rows for t in row)
        self.assertGreater(toadstools, config.GLADE_TOADSTOOLS)   # (2 tiles each)

    def test_new_tiles_have_map_colors_and_no_shot_glyphs(self):
        from ascii_adventurers import palette
        from ascii_adventurers.render.ascii_fx import SHOT_LOOKS as _LOOKS
        floors = "".join(g for t in (tiles.DEAD_LEAVES, tiles.FOG, tiles.BARK) for g in t.glyphs)
        for look in ("glitter", "thorn"):
            head, trail, _ = _LOOKS[look]
            for ch in head + "".join(trail):
                if ch != " ":
                    self.assertNotIn(ch, floors, look)
        for t in (tiles.SHRINE, tiles.SHRINE_CLEAN, tiles.ROT_RING, tiles.BRAMBLE_WALL,
                  tiles.TOADSTOOL, tiles.HOLLOW_TREE, tiles.GROWCAP, tiles.GROWCAP_SPENT):
            self.assertTrue(t.name in palette.MAP_TILE or t.name in palette.MAP_TILE_BIOME, t.name)
            self.assertNotIn("~", "".join(t.glyphs), t.name)


class CleanseTest(unittest.TestCase):
    def test_the_ring_tightens_as_it_cleans(self):
        r0, r1 = config.CLEANSE_RADIUS
        self.assertAlmostEqual(circle_radius("cleanse", 0.0), r0)
        self.assertAlmostEqual(circle_radius("cleanse", config.CLEANSE_TIME), r1)
        self.assertLess(circle_radius("cleanse", config.CLEANSE_TIME / 2), r0)
        self.assertEqual(circle_radius("survive", 99.0), config.SEAL_RADIUS)

    def test_stand_in_a_shrine_to_cleanse_it_while_sprites_rise(self):
        m, s = game(seed=31)
        q = s.quests
        st = q.states["hedge_witch"]
        self.assertEqual(st.spec.kind, "cleanse")
        x, y = st.camp.spots[0]
        self.assertIs(s.world.tile_at(math.floor(x), math.floor(y)), tiles.SHRINE)
        teleport(s, x + 0.5, y + 0.5)
        s.hero.invulnerable = True
        step(s, round(config.CLEANSE_TIME * 0.5 * 60))
        self.assertGreater(st.heat.get(0, 0.0), config.CLEANSE_TIME * 0.4)
        sprites = [e for e in s.enemies if getattr(e, "kind_key", "") == "blighted_sprite"]
        self.assertGreaterEqual(len(sprites), config.CLEANSE_WAVE_SIZE[0] * 2)
        step(s, round(config.CLEANSE_TIME * 0.55 * 60))
        self.assertIn(0, st.lit)
        self.assertIs(s.world.tile_at(math.floor(x), math.floor(y)), tiles.SHRINE_CLEAN)
        self.assertEqual(st.found, 1)

    def test_leave_and_it_slides_back(self):
        m, s = game(seed=31)
        st = s.quests.states["hedge_witch"]
        x, y = st.camp.spots[1]
        teleport(s, x + 0.5, y + 0.5)
        s.hero.invulnerable = True
        step(s, 120)
        worn = st.heat[1]
        teleport(s, x + 15, y)
        step(s, 60)
        self.assertLess(st.heat[1], worn)

    def test_four_shrines_wake_her_and_she_falls(self):
        m, s = game(seed=31)
        q = s.quests
        st = finish(q, "hedge_witch")
        self.assertEqual(st.stage, "awake")
        s.hero.invulnerable = True
        teleport(s, st.lair.cx + 20, st.lair.cy + 6)
        step(s, 2)
        self.assertEqual(st.stage, "fight")
        b = st.boss
        self.assertIsInstance(b, Nettle)
        step(s, 300)
        s.draw(m.text)
        b.hp = 0.0
        b.last_hit_by = s.hero
        step(s, 2)
        self.assertEqual(st.stage, "cleared")
        self.assertIn("nettle", m.app.guild.achievements)
        self.assertTrue(all(not d.alive for d in s.enemies if isinstance(d, Glamour)))


class GlamourTest(unittest.TestCase):
    def test_she_splits_into_copies(self):
        f = Fight()
        f.run(1.6, "glamour")
        self.assertEqual(len(f.b.decoys), config.DECOYS[0])
        for d in f.b.decoys:
            self.assertIsInstance(d, Glamour)
            self.assertIs(d.part_of, f.b)
        f.b.phase = 2
        f.run(1.6, "glamour")
        self.assertEqual(len(f.b.decoys), config.DECOYS[2])

    def test_a_hit_pops_a_copy_into_dust_and_spares_her(self):
        f = Fight()
        f.run(1.6, "glamour")
        d = f.b.decoys[0]
        hp = f.b.hp
        shots = len(f.shots)
        combat.strike(d, 50, f.h, 0.0, f.effects)
        self.assertFalse(d.alive)
        f.run(0.05)
        self.assertNotIn(d, f.b.decoys)
        self.assertEqual(f.b.hp, hp)
        self.assertGreaterEqual(len(f.shots) - shots, config.DECOY_POP)
        self.assertFalse(combat._may_hurt(f.b, f.b.decoys[0]))   # her shots pass her copies

    def test_copies_fade_on_their_own(self):
        f = Fight()
        f.run(1.6, "glamour")
        shots = len(f.shots)
        for d in f.b.decoys:
            d.age = config.DECOY_LIFE
        f.run(0.05)
        f.run(0.05)
        self.assertEqual(f.b.decoys, [])
        self.assertEqual(len(f.shots), shots)               # no dust when they fade

    def test_copies_cast_too_and_keep_apart(self):
        f = Fight()
        f.run(1.6, "glamour")
        f.run(3.0)
        bodies = f.b.emitters()
        for i, p in enumerate(bodies):
            for q in bodies[i + 1:]:
                self.assertGreater(math.hypot(p.x - q.x, p.y - q.y), config.DECOY_SPREAD * 0.4)
        f.run(1.0, "sparks")
        starts = {(round(m[0]), round(m[1])) for m in f.b.homers}
        self.assertGreater(len(f.b.homers), config.NETTLE_SPARKS[1])
        self.assertGreater(len(starts), 1)

    def test_the_timer_splits_her(self):
        f = Fight()
        f.b.decoy_t = 0.1
        f.run(2.0)
        self.assertEqual(len(f.b.decoys), config.DECOYS[0])


class ShrinkTest(unittest.TestCase):
    def test_a_moment_in_her_dust_shrinks_you(self):
        f = Fight(hx=70.0, hy=22.0, bx=60.0, by=22.0)
        f.b.phase = 1
        f.b.clouds = [[f.h.x, f.h.y, 0.0]]
        f.run(config.DUST_SHRINK + 0.1)
        self.assertGreater(f.h.shrunk, 0)

    def test_tiny_is_faster_and_weaker_and_gets_knocked_about(self):
        h = hero("wizard", 10.0, 10.0)
        w, _ = glade()
        h.move(1.0, 0.0, 1.0, w)
        full = h.speed
        h2 = hero("wizard", 10.0, 20.0)
        h2.shrunk = 5.0
        h2.move(1.0, 0.0, 1.0, w)
        self.assertAlmostEqual(h2.speed, full * config.SHRINK[1], places=3)
        d1, d2 = Dummy(30.0, 10.0), Dummy(30.0, 20.0)
        a = combat.strike(d1, 100, h, 0.0, [], can_crit=False)
        b = combat.strike(d2, 100, h2, 0.0, [], can_crit=False)
        self.assertAlmostEqual(b, a * config.SHRINK[2], places=3)
        f = Fight(hx=70.0, hy=22.0)
        f.h.shrunk = 5.0
        x = f.h.x
        f.b._hit(f.h, 5, 0.0)
        self.assertAlmostEqual(f.h.x - x, config.SHRINK[3], delta=0.2)

    def test_a_growcap_grows_you_back_then_regrows(self):
        f = Fight(hx=CAPS[0][0], hy=CAPS[0][1])
        f.h.shrunk = 20.0
        f.run(config.GROWCAP_TIME + 0.1)
        self.assertEqual(f.h.shrunk, 0.0)
        self.assertIn(0, f.b.spent)
        self.assertIs(f.w.tile_at(20, 10), tiles.GROWCAP_SPENT)
        self.assertIn(("growcap", "GROWCAP"), {(k, l) for _, _, k, l in f.b.map_marks()})
        f.h.shrunk = 20.0
        f.run(0.5)
        self.assertGreater(f.h.shrunk, 0)                   # spent: nothing
        f.b.spent[0] = 0.01
        f.run(config.GROWCAP_TIME + 0.2)
        self.assertIs(f.w.tile_at(20, 10), tiles.GROWCAP_SPENT)   # regrew, and used again
        self.assertEqual(f.h.shrunk, 0.0)

    def test_it_wears_off(self):
        f = Fight(hx=70.0, hy=22.0)
        f.h.shrunk = 0.5
        f.run(0.6)
        self.assertEqual(f.h.shrunk, 0.0)

    def test_her_dives_trail_dust_from_phase_two(self):
        f = Fight(hx=90.0, hy=22.0, bx=60.0, by=22.0)
        f.run(4.0, "dive")
        self.assertEqual(f.b.clouds, [])
        f = Fight(hx=90.0, hy=22.0, bx=60.0, by=22.0)
        f.b.phase = 1
        f.run(4.0, "dive")
        self.assertTrue(f.b.clouds)


class BlightTest(unittest.TestCase):
    def test_seeds_come_in_phase_three(self):
        f = Fight(hx=70.0, hy=22.0)
        f.b.blight_t = 0.1
        f.run(2.0)
        self.assertEqual(f.b.seeds, [])
        f.b.phase = 2
        f.run(2.0)
        self.assertEqual(len(f.b.seeds), config.BLIGHT_SEEDS)

    def test_the_blight_hurts_you_and_heals_her(self):
        f = Fight(hx=70.0, hy=22.0)
        f.b.phase = 2
        f.b.seeds = [[f.h.x, f.h.y + 2.5, config.BLIGHT_GROW, 0.0],
                     [f.b.x, f.b.y, config.BLIGHT_GROW, 0.0]]
        f.b.hp = f.b.max_hp - 1000
        hp_h, hp_b = f.h.hp, f.b.hp
        f.b.circle_dir = 0
        f.b._fly = lambda body, t, dt, mult, way: way      # (held over the blight)
        f.run(1.0)
        self.assertLess(f.h.hp, hp_h)
        self.assertAlmostEqual(f.b.hp - hp_b, config.BLIGHT_HEAL, delta=5)
        self.assertTrue(f.b.healing)
        self.assertIn("BLIGHT", f.b.bar_label)

    def test_stand_on_a_seed_to_pull_it(self):
        f = Fight(hx=70.0, hy=22.0)
        f.b.seeds = [[70.0, 22.0, 1.0, 0.0]]
        self.assertIn(("seed", "SEED"), {(k, l) for _, _, k, l in f.b.map_marks()})
        f.run(config.BLIGHT_PULL + 0.1)
        self.assertEqual(f.b.seeds, [])


class MovesTest(unittest.TestCase):
    def test_every_move_runs(self):
        moves = {m for ph in config.BOSSES["nettle"].phases for m, _ in ph.moves}
        self.assertEqual(moves, {"spiral", "sparks", "thorns", "cage", "moths", "dive", "wisps",
                                 "nettles", "dust"})
        for move in sorted(moves | {"glamour", "seeds"}):
            f = Fight(hx=75.0, hy=22.0)
            f.b.phase = 2
            f.run(5.0, move)
            self.assertEqual(f.b.last_move, move, move)

    def test_her_moves_hurt(self):
        for move in ("sparks", "thorns", "dive", "wisps", "nettles"):
            f = Fight(hx=72.0, hy=22.0)
            hp = f.h.hp
            f.h.vx = f.h.vy = 0.0
            f.run(5.0, move)
            self.assertLess(f.h.hp, hp, move)

    def test_moths_come_and_no_more_than_most(self):
        f = Fight()
        for _ in range(4):
            f.run(2.0, "moths")
        moths = [a for a in f.adds if getattr(a, "kind_key", "") == "rot_moth"]
        self.assertEqual(len(moths), config.NETTLE_MOTHS[2])

    def test_she_circles_you_and_keeps_moving_in_her_moves(self):
        f = Fight(hx=70.0, hy=22.0, bx=60.0, by=22.0)
        f.run(5.0)
        d = math.hypot(f.b.x - f.h.x, f.b.y - f.h.y)
        near, far = config.NETTLE_ORBIT[0], config.NETTLE_ORBIT[1]
        self.assertTrue(near - 3 < d < far + 3, d)
        before = f.b.walked
        f.run(2.0, "spiral")
        self.assertGreater(f.b.walked - before, 2.0)

    def test_her_dive_follows_the_line_she_shows(self):
        f = Fight(hx=85.0, hy=22.0, bx=60.0, by=22.0)
        f.b._rest = 0.0
        f.b.last_move = None
        f.b._pick_move = lambda: "dive"
        while f.b.tell is None or f.b.tell[0] != "dive":
            f.b.think(f.ctx(), DT)
        _, x0, y0, x1, y1 = f.b.tell
        while f.b.tell is not None:
            f.b.think(f.ctx(), DT)
            from ascii_adventurers.systems.patterns import point_segment_distance
            self.assertLess(point_segment_distance(f.b.x, f.b.y, x0, y0, x1, y1), 0.3)

    def test_she_flies_over_toadstools(self):
        walls = [(x, y) for x in range(55, 66) for y in range(15, 30)]
        f = Fight(hx=60.0, hy=10.0, bx=60.0, by=22.0, walls=walls)
        f.run(4.0)
        self.assertTrue(f.lair.inside(f.b.x, f.b.y))


if __name__ == "__main__":
    unittest.main()
