"""M22: boss pools (one quest per biome per run, picked by the seed) and
the swamp's second boss, the Leech Swarm, with the leech doctor's quest."""

import math
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from ascii_adventurers import config
from ascii_adventurers.ai import make_enemy
from ascii_adventurers.ai.bosses import LeechPart, LeechSwarm
from ascii_adventurers.ai.brain import AIContext
from ascii_adventurers.players.controls import PlayerInput
from ascii_adventurers.systems import roll
from ascii_adventurers.tests.test_m14 import carded
from ascii_adventurers.tests.test_weapons import open_map
from ascii_adventurers.world import tiles
from ascii_adventurers.world.chunked import ChunkedWorld
from ascii_adventurers.world.landmarks import quest_marks

DT = 1 / 60


class PoolTest(unittest.TestCase):
    def tearDown(self):
        config.QUEST_FOCUS = None

    def test_every_quest_is_built_in_its_skin(self):
        # M22.5: all of the swamp's quests, every run (the seed no longer picks one).
        w = ChunkedWorld(31)
        names = {m.name for m in w.layout.landmarks if m.kind != "spot"}
        self.assertTrue({"LEECH DOCTOR", "THE BLOOD MIRE", "SMOKE KEEPER",
                         "THE STAGNANT COURT"} <= names)
        _, lair = quest_marks(w.layout, "leech_doctor")
        flat = [t for row in lair.rows for t in row if t is not None]
        self.assertIn(tiles.BLOOD_POOL, flat)
        self.assertNotIn(tiles.POND, flat)
        self.assertNotIn(tiles.LILY_PADS, flat)

    def test_run_py_boss_flag(self):
        from ascii_adventurers.run import force_boss
        force_boss("leech_swarm")
        self.assertEqual(config.QUEST_FOCUS, "leech_doctor")
        with self.assertRaises(SystemExit):
            force_boss("nobody")


def swarm_at(x=40.0, y=15.0, level=1):
    b = make_enemy("leech_swarm", x, y, random.Random(3))
    b.scale_to_level(level)
    return b


def ctx_for(heroes, b, world=None):
    return AIContext(world or open_map(w=80), heroes, list(heroes) + [b] + b.parts, [], [])


class SwarmTest(unittest.TestCase):
    def test_health_is_the_leeches(self):
        b = swarm_at()
        self.assertEqual(len(b.parts), config.LEECHES)
        self.assertAlmostEqual(sum(p.max_hp for p in b.parts), b.max_hp)
        self.assertFalse(b.hittable)
        p = b.parts[0]
        p.take_damage(p.max_hp + 50, None, None)
        self.assertFalse(p.alive)
        self.assertAlmostEqual(b.hp, b.max_hp * (1 - 1 / config.LEECHES))
        for q in b.parts:
            q.take_damage(10 ** 6, None, None)
        self.assertFalse(b.alive)

    def test_its_own_drops_pass_its_leeches(self):
        from ascii_adventurers.systems.combat import _may_hurt
        b = swarm_at()
        self.assertFalse(_may_hurt(b, b.parts[0]))
        h = carded("wizard")
        self.assertTrue(_may_hurt(b, h))
        self.assertTrue(_may_hurt(None, h))          # (ownerless shots still hurt)

    def test_latch_drain_and_roll_off(self):
        h = carded("bard", x=40.0, y=15.0)
        b = swarm_at(41.0, 15.0)
        ctx = ctx_for([h], b)
        for _ in range(30):
            b.think(ctx, DT)
        on = [p for p in b.parts if p.latched is h]
        self.assertTrue(0 < len(on) <= config.LATCH_MAX)
        before = h.hp
        for _ in range(60):
            b.think(ctx, DT)
        self.assertLess(h.hp, before)
        h.roll_t = config.ROLL_TIME                 # a roll throws them all off
        b.think(ctx, DT)
        self.assertFalse(any(p.latched is h for p in b.parts))
        self.assertTrue(any(p.stun > 0 for p in on))
        self.assertTrue(any(e.kind == "toast" and e.label == "SHAKEN OFF!" for e in ctx.effects))
        for _ in range(20):                         # mid-roll nothing latches
            b.think(ctx, DT)
            h.roll_t = 0.2
        self.assertFalse(any(p.latched is h for p in b.parts))

    def test_every_move_runs(self):
        h = carded("bard", x=40.0, y=15.0)
        h.invulnerable = True
        b = swarm_at(55.0, 15.0)
        ctx = ctx_for([h], b)
        for phase in range(3):
            for name, _ in config.BOSSES["leech_swarm"].phases[phase].moves:
                b.phase = phase
                b.ctx = ctx
                b._start(name)
                b._wait = 0.0
                for _ in range(60 * 8):
                    b.think(ctx, DT)
                    if b.move is None:
                        break
                self.assertIsNone(b.move, name)
        self.assertTrue(any(p.owner is b for p in ctx.projectiles))   # spit / nest drops

    def test_bloated_leech_bursts_into_leechlings(self):
        e = make_enemy("bloated_leech", 10.0, 10.0, random.Random(1))
        ctx = AIContext(open_map(), [], [e], [], [])
        e.hp = 0
        e.on_death(ctx)
        self.assertEqual([k for k, _, _ in ctx.spawned], ["leechling"] * config.LEECH_BROOD)


class QuestTest(unittest.TestCase):
    def setUp(self):
        config.QUEST_FOCUS = "leech_doctor"            # (the dev keys' quest)

    def tearDown(self):
        config.QUEST_FOCUS = None
        pygame.mouse.set_visible(True)

    def test_the_whole_fight(self):
        from ascii_adventurers.tests.test_m16 import game
        from ascii_adventurers.systems.quests import free_spot
        m, s = game("wizard", seed=31)
        st = s.quests.states["leech_doctor"]
        self.assertEqual(st.spec.boss, "leech_swarm")
        s.quests.dev_finish_hunt()
        lair = st.lair
        h = s.hero
        h.invulnerable = True
        s.world.ensure_ready(int(lair.cx) - 130, int(lair.cy) - 55, int(lair.cx) + 130,
                             int(lair.cy) + 55)
        h.x, h.y = free_spot(s.world, lair.cx + 20, lair.cy + 10, h.half)
        h.prev_pos = (h.x, h.y)
        s.update(DT)
        self.assertEqual(st.stage, "fight")
        b = st.boss
        self.assertIsInstance(b, LeechSwarm)
        self.assertEqual(sum(isinstance(e, LeechPart) for e in s.enemies), config.LEECHES)
        kills = s.stats.total_kills
        for p in b.parts[:-1]:
            p.take_damage(10 ** 6, h, 0.0)
        s.update(DT)
        self.assertEqual(s.stats.total_kills, kills)        # leeches aren't kills...
        self.assertEqual(st.stage, "fight")
        b.parts[-1].take_damage(10 ** 6, h, 0.0)
        s.update(DT)
        self.assertEqual(st.stage, "cleared")                # ...the swarm is
        self.assertEqual(s.stats.total_kills, kills + 1)
        self.assertIn("leech_swarm", s.app.guild.achievements)
        s.draw(m.text)

    def test_leechlings_wake(self):
        from ascii_adventurers.tests.test_m16 import game
        m, s = game("bard", seed=31)
        h = s.hero
        e = make_enemy("bloated_leech", h.x + 6, h.y, random.Random(1))
        s.enemies.append(e)
        e.take_damage(10 ** 6, h, 0.0)
        s.update(DT)
        self.assertEqual(sum(getattr(x, "kind_key", "") == "leechling" for x in s.enemies),
                         config.LEECH_BROOD)
        s.draw(m.text)


if __name__ == "__main__":
    unittest.main()
