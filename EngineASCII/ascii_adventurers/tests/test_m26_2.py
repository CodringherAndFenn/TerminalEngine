"""M26.2: Mycelium the shaggy ink cap (ink pools, ink blots, scrawl, ink-cap
clusters), its ring, and its giver for the shared "sever" quest."""

import math
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.ai import make_enemy
from ascii_adventurers.ai.bosses import InkCap, MycoPart
from ascii_adventurers.ai.brain import AIContext
from ascii_adventurers.systems.quests import circle_rules
from ascii_adventurers.tests.test_m17 import game, step, teleport, world
from ascii_adventurers.tests.test_weapons import hero
from ascii_adventurers.world import tiles
from ascii_adventurers.world.landmarks import Landmark, quest_marks
from ascii_adventurers.world.test_map import LEGEND, TestMap

DT = 1 / 60
W, H = 160, 50


def ring():
    rows = ["." * W for _ in range(H)]
    m = TestMap(rows, dict(LEGEND))
    lair = Landmark("inkcap_ring", "lair", "mushroom", "MYCELIUM", 0, 0, [], cx=W / 2, cy=H / 2,
                    spots=[(W / 2, H / 2)], radii=(W / 2 + 2, H / 2 + 2), props={})
    return m, lair


class Fight:
    def __init__(self, hx=80.0, hy=25.0, bx=70.0, by=25.0, phase=0):
        self.w, self.lair = ring()
        self.b = make_enemy("mycelium_inkcap", bx, by, random.Random(4))
        self.b.scale_to_level(1)
        self.b._rest = 99.0
        self.b.pool_t = self.b.blot_t = self.b.scrawl_t = self.b.cluster_t = 999.0
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
                self.b._pick_move = lambda: "scales"
                move = None
            if until is not None and until():
                return True
        return False

    def sign(self, name):
        self.b._start(name)
        self.b._wait = 0.0


class RingTest(unittest.TestCase):
    def test_camp_and_ring_in_the_mushroom_biome(self):
        for seed in (1, 2, 31, 999):
            w = world(seed)
            camp, lair = quest_marks(w.layout, "mycologist")
            self.assertEqual((camp.key, lair.key), ("spore_camp", "inkcap_ring"), seed)
            for m in (camp, lair):
                self.assertEqual(w.layout.biome_at(m.cx, m.cy).name, "mushroom", seed)
            self.assertEqual(lair.name, "MYCELIUM")

    def test_paving_stains_and_cover(self):
        w = world(31)
        _, lair = quest_marks(w.layout, "mycologist")
        flat = {t for row in lair.rows for t in row if t is not None}
        self.assertTrue({tiles.SHROOM_WALL, tiles.MYCELIUM, tiles.OLD_PAVING, tiles.INK_STAIN,
                         tiles.GIANT_SHROOM} <= flat)

    def test_new_tiles_and_shot_glyphs(self):
        from ascii_adventurers import palette
        from ascii_adventurers.render.ascii_fx import SHOT_LOOKS as _LOOKS
        floors = "".join(g for t in (tiles.MYCELIUM, tiles.OLD_PAVING, tiles.INK_STAIN)
                         for g in t.glyphs)
        for look in ("scale", "ink_drop"):
            head, trail, _ = _LOOKS[look]
            for ch in head + "".join(t for t in trail if t):
                if ch != " ":
                    self.assertNotIn(ch, floors, look)
        for t in (tiles.NODE_SPILL_INK, tiles.OLD_PAVING, tiles.INK_STAIN):
            self.assertTrue(t.name in palette.MAP_TILE or t.name in palette.MAP_TILE_BIOME, t.name)
            self.assertNotIn("~", "".join(t.glyphs), t.name)


class SharedQuestTest(unittest.TestCase):
    def test_same_quest_word_for_word_only_the_giver_and_spill_differ(self):
        a, b = config.QUESTS["truffle_hunter"], config.QUESTS["mycologist"]
        for f in ("title", "biome", "camp", "target", "count", "goal", "kind", "lair_name",
                  "lines"):
            self.assertEqual(getattr(a, f), getattr(b, f), f)
        self.assertNotEqual(a.giver, b.giver)
        self.assertEqual(config.ENEMIES[b.boss].name, "Mycelium")
        self.assertIs(circle_rules("sever", b.skin)["done"], tiles.NODE_SPILL_INK)
        self.assertIsNot(circle_rules("sever", a.skin)["done"], tiles.NODE_SPILL_INK)

    def test_its_nodes_spill_ink(self):
        config.QUEST_FOCUS = "mycologist"
        try:
            m, s = game(seed=31)
            self.assertTrue(s.quests.dev_finish_hunt())
            st = s.quests.states["mycologist"]
            x, y = st.camp.spots[0]
            teleport(s, x + 4, y)
            self.assertIs(s.world.tile_at(math.floor(x), math.floor(y)), tiles.NODE_SPILL_INK)
        finally:
            config.QUEST_FOCUS = None


class PoolTest(unittest.TestCase):
    def test_it_melts_flows_and_reforms_where_it_bubbled(self):
        f = Fight()
        f.sign("melt")
        f.run(DT)
        spot = f.b.reform
        self.assertIsNotNone(spot)
        lo, hi = config.POOL_AWAY
        self.assertLessEqual(math.hypot(spot[0] - f.h.x, spot[1] - f.h.y), hi + 0.1)
        self.assertTrue(f.run(config.POOL_TELL + 0.2, until=lambda: f.b.pooling))
        self.assertFalse(f.b.hittable)
        self.assertTrue(f.run(6.0, until=lambda: not f.b.pooling))
        self.assertAlmostEqual(f.b.x, spot[0], places=3)
        self.assertTrue(f.b.hittable)
        self.assertIsNone(f.b.reform)
        self.assertTrue(f.b.puddles)
        self.assertTrue(any(p.spec.look == "ink_drop" for p in f.shots))

    def test_ink_slows_and_stings(self):
        f = Fight()
        f.b.puddles.append([f.h.x, f.h.y, 1.4, 0.0, 8.0, 0.0])
        hp = f.h.hp
        f.run(1.0)
        self.assertAlmostEqual(f.h.slow_mult, config.INK_SLOW)
        self.assertLess(f.h.hp, hp)


class BlotTest(unittest.TestCase):
    def test_a_blot_blinds_you_and_a_roll_wipes_it_off(self):
        f = Fight(phase=1)
        f.b.blot_t = 0.0
        f.run(config.BLOT_TELL + config.BLOT_FLIGHT + 0.3)
        self.assertEqual(len(f.b.blots), config.BLOTS)
        b = f.b.blots[0]
        f.h.x, f.h.y = b[0], b[1]
        f.run(DT)
        self.assertTrue(f.b.blind(f.h))
        f.h.x, f.h.y = b[0] + 20, b[1]
        f.run(config.INKED * 0.5)
        self.assertTrue(f.b.blind(f.h))                  # (it lingers)
        f.h.roll_t = 0.2
        f.run(DT)
        self.assertFalse(f.b.blind(f.h))

    def test_blots_only_from_phase_two(self):
        f = Fight()
        f.b.blot_t = 0.0
        f.run(2.0)
        self.assertEqual(f.b.blots, [])


class ScrawlTest(unittest.TestCase):
    def test_it_writes_a_word_through_you_then_the_letters_burst(self):
        f = Fight(phase=2, hx=80.0, hy=25.0)
        f.b.rng.choice = lambda seq: seq[0] if isinstance(seq, tuple) and seq and \
            isinstance(seq[0], str) and len(seq[0]) > 1 else random.choice(seq)
        f.sign("scrawl")
        word = config.SCRAWL_WORDS[0]
        f.run(config.SCRAWL_PEN * len(word) + 0.05)
        self.assertEqual("".join(l[2] for l in f.b.letters), word)
        mid = (f.b.letters[0][0] + f.b.letters[-1][0]) / 2, (f.b.letters[0][1] + f.b.letters[-1][1]) / 2
        self.assertLess(math.hypot(mid[0] - f.h.x, mid[1] - f.h.y), 1.0)
        hp = f.h.hp
        f.run(config.SCRAWL_HOLD + 1.0)
        self.assertEqual(f.b.letters, [])
        self.assertLess(f.h.hp, hp)

    def test_every_other_word_rises_as_ink_imps(self):
        f = Fight(phase=2)
        f.b.scrawls = 1
        f.sign("scrawl")
        f.run(config.SCRAWL_PEN * 9 + config.SCRAWL_HOLD + 0.5)
        imps = [a for a in f.adds if a.kind_key == "ink_imp"]
        self.assertTrue(1 <= len(imps) <= config.SCRAWL_IMPS)
        self.assertTrue(all(a.summoner is f.b for a in imps))


class ClusterTest(unittest.TestCase):
    def test_sprouts_push_up_and_melt_unless_broken(self):
        f = Fight(phase=2)
        f.sign("clusters")
        f.run(config.CLUSTER_TELL + 0.2)
        self.assertEqual(len(f.b.sprouts), config.CLUSTER)
        self.assertTrue(all(isinstance(s, MycoPart) and s.rooted for s in f.b.sprouts))
        f.b.sprouts[0].hp = 0
        f.b.submerged = True
        self.assertTrue(f.b.sprouts[1].hittable)          # (rooted: not hidden with it)
        f.b.submerged = False
        f.run(config.CLUSTER_GROW + 0.2)
        self.assertEqual(f.b.sprouts, [])
        pools = [p for p in f.b.puddles if p[2] == config.CLUSTER_POOL[0]]
        self.assertEqual(len(pools), config.CLUSTER - 1)


class MoveTest(unittest.TestCase):
    def test_scale_volley(self):
        f = Fight()
        f.run(config.INKCAP_SCALES[0] + 1.0, move="scales")
        self.assertTrue(any(p.spec.look == "scale" for p in f.shots))

    def test_ink_spray_splashes_puddles(self):
        f = Fight()
        hp = f.h.hp
        f.run(config.INKCAP_SPRAY[0] + 1.0, move="spray")
        self.assertEqual(len(f.b.puddles), config.INKCAP_SPRAY[1])
        self.assertLess(f.h.hp, hp)

    def test_burst_up_under_you(self):
        f = Fight()
        hp = f.h.hp
        f.run(0.4, move="burst")
        self.assertIsNotNone(f.b.crack_at)
        self.assertFalse(f.b.hittable)
        f.run(config.INKCAP_BURST[0] + 0.5)
        self.assertLess(math.hypot(f.b.x - f.h.x, f.b.y - f.h.y), 3.5)
        self.assertLess(f.h.hp, hp)

    def test_shaggy_shake_rings_with_a_gap(self):
        f = Fight()
        f.run(config.INKCAP_SHAKE[0] + 0.1, move="shake")
        tell, rings, n, gap, _ = config.INKCAP_SHAKE
        ring1 = [p for p in f.shots if p.spec.look == "scale"]
        self.assertTrue(0 < len(ring1) < n)


class GameTest(unittest.TestCase):
    def test_the_fight_in_a_real_game(self):
        config.QUEST_FOCUS = "mycologist"
        try:
            m, s = game(seed=31)
            q = s.quests
            q.dev_finish_hunt()
            st = q.states["mycologist"]
            teleport(s, st.lair.cx, st.lair.cy + 12)
            s.hero.invulnerable = True
            step(s, 3)
            self.assertEqual(st.stage, "fight")
            b = st.boss
            self.assertIsInstance(b, InkCap)
            b.hp = b.max_hp * 0.2
            b.blot_t = 0.0
            for f in range(900):
                step(s)
                if f % 60 == 0:
                    s.draw(m.text)
            b.inked[id(s.hero)] = 2.0
            s.draw(m.text)
            self.assertTrue(b.alive)
        finally:
            config.QUEST_FOCUS = None


if __name__ == "__main__":
    unittest.main()
