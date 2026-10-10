"""M22.2: the swamp's third boss, Lady Proboscia (a giant mosquito: the
engorge / pop signature), her mosquitoes, and the smoke keeper's "light"
quest (stand by braziers until they catch)."""

import math
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from ascii_adventurers import config
from ascii_adventurers.ai import make_enemy
from ascii_adventurers.ai.bosses import Proboscia
from ascii_adventurers.ai.brain import AIContext
from ascii_adventurers.systems import patterns
from ascii_adventurers.tests.test_m14 import carded
from ascii_adventurers.tests.test_m17 import step, teleport
from ascii_adventurers.tests.test_weapons import open_map
from ascii_adventurers.world import tiles
from ascii_adventurers.world.chunked import ChunkedWorld
from ascii_adventurers.world import landmarks
from ascii_adventurers.world.landmarks import quest_marks

DT = 1 / 60


def lady_at(x=40.0, y=15.0, level=1):
    b = make_enemy("proboscia", x, y, random.Random(3))
    b.scale_to_level(level)
    return b


def ctx_for(heroes, b, world=None):
    ctx = AIContext(world or open_map(w=80), heroes, list(heroes) + [b], [], [])
    b.ctx = ctx
    return ctx


def run(b, ctx, seconds):
    for _ in range(round(seconds * 60)):
        b.think(ctx, DT)


class PoolTest(unittest.TestCase):
    def tearDown(self):
        config.QUEST_FOCUS = None

    def test_stagnant_landmarks_and_braziers(self):
        w = ChunkedWorld(31)
        camp, lair = quest_marks(w.layout, "smoke_keeper")
        self.assertEqual((camp.name, lair.name), ("SMOKE KEEPER", "THE STAGNANT COURT"))
        flat = [t for row in lair.rows for t in row if t is not None]
        self.assertIn(tiles.STAGNANT, flat)
        self.assertNotIn(tiles.POND, flat)
        self.assertEqual(len(camp.spots),
                         landmarks.spot_count(config.QUESTS["smoke_keeper"]))
        x, y = camp.spots[0]
        w.ensure_ready(int(x) - 4, int(y) - 4, int(x) + 4, int(y) + 4)
        self.assertIs(w.tile_at(math.floor(x), math.floor(y)), tiles.BRAZIER)

    def test_run_py_boss_flag(self):
        from ascii_adventurers.run import force_boss
        force_boss("proboscia")
        self.assertEqual(config.QUEST_FOCUS, "smoke_keeper")


class RingGapTest(unittest.TestCase):
    def test_ring_in_leaves_a_gap(self):
        shots = []
        shell = config.PROBOSCIA_SHOTS["buzz"]
        patterns.ring_in(None, 0.0, 0.0, 10.0, 24, shell, shots, 0.5, gap_deg=50, gap_at=0.0)
        self.assertEqual(len(shots), 24 - 3)              # the ones at 0 and +-15 degrees
        for p in shots:
            self.assertGreaterEqual(abs(math.atan2(p.y, p.x)), math.radians(25))


class LadyTest(unittest.TestCase):
    def test_engorge_then_pop(self):
        h = carded("bard", x=20.0, y=15.0)
        b = lady_at()
        ctx = ctx_for([h], b)
        for _ in range(config.ENGORGE_FULL):
            b.gulp()
        self.assertGreater(b.engorged, 0)
        self.assertTrue(any(e.kind == "toast" and "POP" in e.label for e in ctx.effects))
        need = config.ENGORGE_POP * b.max_hp
        b.take_damage(need * 0.5, h, 0.0)
        b.think(ctx, DT)
        self.assertGreater(b.engorged, 0)                  # not yet
        hp = b.hp
        b.take_damage(need * 0.6, h, 0.0)
        b.think(ctx, DT)
        self.assertEqual(b.engorged, 0.0)
        self.assertEqual(b.belly, 0)
        self.assertAlmostEqual(hp - need * 0.6 - b.hp, config.ENGORGE_BONUS * b.max_hp, places=3)
        self.assertGreater(b.dazed, 0)
        self.assertTrue(b.grounded)
        self.assertEqual(sum(1 for p in ctx.projectiles if p.owner is b), config.ENGORGE_RING)
        x, y = b.x, b.y
        run(b, ctx, config.ENGORGE_STUN * 0.9)            # down: doesn't move
        self.assertEqual((b.x, b.y), (x, y))
        run(b, ctx, 1.0)
        self.assertFalse(b.grounded)

    def test_unpopped_she_digests(self):
        h = carded("bard", x=20.0, y=15.0)
        b = lady_at()
        ctx = ctx_for([h], b)
        b.hp = b.max_hp * 0.5
        b.gulp(config.ENGORGE_FULL)
        hp = b.hp
        b._rest = 99.0                                     # (no moves meanwhile)
        run(b, ctx, config.ENGORGE_WINDOW + 0.1)
        self.assertEqual(b.engorged, 0.0)
        self.assertAlmostEqual(b.hp - hp, config.ENGORGE_DIGEST * b.max_hp, places=3)

    def test_a_bite_drinks(self):
        h = carded("bard", x=30.0, y=15.0)
        b = lady_at(45.0, 15.0)
        ctx = ctx_for([h], b)
        b.hp = b.max_hp * 0.5
        hp, hero_hp = b.hp, h.hp
        b._start("bite")
        b._wait = 0.0
        run(b, ctx, 2.5)
        self.assertLess(h.hp, hero_hp)
        self.assertEqual(b.belly, 1)
        self.assertGreater(b.hp, hp)

    def test_rolling_through_a_bite(self):
        h = carded("bard", x=30.0, y=15.0)
        b = lady_at(45.0, 15.0)
        ctx = ctx_for([h], b)
        hero_hp = h.hp
        b._start("bite")
        b._wait = 0.0
        for _ in range(150):
            h.roll_t = 0.2                                # rolling the whole time
            b.think(ctx, DT)
        self.assertEqual(h.hp, hero_hp)
        self.assertEqual(b.belly, 0)

    def test_a_sip_fills_her_unless_shooed(self):
        h = carded("bard", x=10.0, y=15.0)
        b = lady_at()

        class Lair:
            spots = [(40.0, 20.0)]
            radii = (60.0, 30.0)
            cx, cy = 40.0, 15.0

            def inside(self, x, y, shrink=0.0):
                return True
        b.lair = Lair()
        ctx = ctx_for([h], b)
        def sip():
            b._start("sip")
            b._wait = 0.0
            for _ in range(60 * 10):
                b.think(ctx, DT)
                if b.move is None or b.sipping:
                    break
        sip()
        self.assertTrue(b.sipping)
        self.assertLess(math.hypot(b.x - 40.0, b.y - 20.0), 0.01)
        while b.move == "sip":
            b.think(ctx, DT)
        self.assertEqual(b.belly, 1)
        b.x = 10.0
        sip()
        self.assertTrue(b.sipping)
        b.take_damage(config.PROBOSCIA_SIP[1] * b.max_hp + 1, h, 0.0)
        while b.move == "sip":
            b.think(ctx, DT)
        self.assertEqual(b.belly, 1)                       # shooed: no gulp

    def test_fever_clouds_in_the_last_phase(self):
        h = carded("bard", x=30.0, y=15.0)
        h.invulnerable = False
        b = lady_at(50.0, 15.0)
        ctx = ctx_for([h], b)
        b.phase = 2
        b._start("bite")
        b._wait = 0.0
        run(b, ctx, 0.9)
        self.assertTrue(b.clouds)
        cx, cy, _ = b.clouds[0]
        h.x, h.y = cx, cy
        hp = h.hp
        b._rest = 99.0
        b._abort_move()
        run(b, ctx, 1.1)
        self.assertLess(h.hp, hp)
        run(b, ctx, config.FEVER_CLOUD[1])
        self.assertFalse(b.clouds)

    def test_every_move_runs(self):
        h = carded("bard", x=40.0, y=15.0)
        h.invulnerable = True
        b = lady_at(55.0, 15.0)
        ctx = ctx_for([h], b)
        called = []
        b.recruit = lambda key, x, y: called.append(key) or make_enemy(key, x, y, random.Random(1))
        for phase in range(3):
            for name, _ in config.BOSSES["proboscia"].phases[phase].moves:
                if name == "sip":
                    continue                              # (needs pools: test above)
                b.phase = phase
                b._start(name)
                b._wait = 0.0
                for _ in range(60 * 10):
                    b.think(ctx, DT)
                    if b.move is None:
                        break
                self.assertIsNone(b.move, name)
        self.assertIn("mosquito", called)
        looks = {p.spec.look for p in ctx.projectiles if p.owner is b}
        self.assertTrue({"needle", "buzz"} <= looks)

    def test_she_hovers_at_her_distance(self):
        h = carded("bard", x=10.5, y=10.5)
        b = lady_at(30.0, 10.5)
        world = open_map(w=60)
        ctx = ctx_for([h], b, world)
        b._rest = 99.0
        run(b, ctx, 3.0)
        d = math.hypot(b.x - h.x, b.y - h.y)
        self.assertLess(abs(d - config.PROBOSCIA_HOVER[1]), 3.0)   # hovering at her distance


class MosquitoTest(unittest.TestCase):
    def test_stings_and_darts_off(self):
        h = carded("bard", x=10.5, y=10.5)
        e = make_enemy("mosquito", 14.0, 10.5, random.Random(2))
        e.alert = True
        ctx = AIContext(open_map(), [h], [h, e], [], [])
        hp = h.hp
        for _ in range(180):
            e.think(ctx, DT)
        self.assertLess(h.hp, hp)


class QuestTest(unittest.TestCase):
    def setUp(self):
        config.QUEST_FOCUS = "smoke_keeper"

    def tearDown(self):
        config.QUEST_FOCUS = None
        pygame.mouse.set_visible(True)

    def test_light_the_braziers_then_the_fight(self):
        from ascii_adventurers.tests.test_m16 import game
        from ascii_adventurers.systems.quests import free_spot
        m, s = game("wizard", seed=31)
        q = s.quests
        st = q.states["smoke_keeper"]
        self.assertEqual(st.spec.kind, "light")
        teleport(s, st.npc.x, st.npc.y)
        s.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e, unicode="e", mod=0))
        step(s)
        self.assertTrue(st.taken)
        self.assertFalse(any(k[1] == st.qid for k in s.spawner.fixed))   # nothing to hunt
        h = s.hero
        h.invulnerable = True
        # Stand by a brazier: it heats, the mosquitoes come, it catches.
        x, y = st.camp.spots[0]
        teleport(s, x + 1.5, y)
        self.assertIn("target", [k for _, _, k, _ in q.pins((h.x, h.y))])
        step(s, 60)
        self.assertGreater(st.heat.get(0, 0.0), 0.9)
        mosq = [e for e in s.enemies if getattr(e, "kind_key", "") == "mosquito"]
        self.assertEqual(len(mosq), config.BRAZIER_SWARM_SIZE)
        s.draw(m.text)
        # Walk off: it cools.
        teleport(s, x + 30, y)
        step(s, 60)
        self.assertLess(st.heat.get(0, 0.0), 1.0)
        teleport(s, x + 1.5, y)
        step(s, round(config.BRAZIER_LIGHT_TIME * 60) + 10)
        self.assertIn(0, st.lit)
        self.assertEqual(st.found, 1)
        self.assertIs(s.world.tile_at(math.floor(x), math.floor(y)), tiles.BRAZIER_LIT)
        self.assertNotIn((x, y), [(px, py) for px, py, k, _ in q.pins((h.x, h.y)) if k == "target"])
        self.assertEqual(sum(getattr(e, "kind_key", "") == "mosquito" for e in s.enemies),
                         2 * config.BRAZIER_SWARM_SIZE)   # (invulnerable: they're all still here)
        s.draw(m.text)
        # The rest.
        for i in range(1, st.spec.count):
            teleport(s, st.camp.spots[i][0] + 1.5, st.camp.spots[i][1])
            step(s, round(config.BRAZIER_LIGHT_TIME * 60) + 10)
        self.assertEqual(st.stage, "awake")
        # The fight.
        lair = st.lair
        s.world.ensure_ready(int(lair.cx) - 130, int(lair.cy) - 55, int(lair.cx) + 130,
                             int(lair.cy) + 55)
        h.x, h.y = free_spot(s.world, lair.cx + 20, lair.cy + 10, h.half)
        h.prev_pos = (h.x, h.y)
        s.update(DT)
        self.assertEqual(st.stage, "fight")
        b = st.boss
        self.assertIsInstance(b, Proboscia)
        step(s, 120)
        s.draw(m.text)
        b.take_damage(10 ** 6, h, 0.0)
        s.update(DT)
        self.assertEqual(st.stage, "cleared")
        self.assertIn("proboscia", s.app.guild.achievements)


if __name__ == "__main__":
    unittest.main()
