"""M29.4: Paradise's quest -- the seven seals, the fallen angel, the summit
court -- and form 1 of its boss, the Serene Cavalry (design/OCEAN.md 5, 6.1)."""

import math
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from ascii_adventurers import config
from ascii_adventurers.ai import make_enemy
from ascii_adventurers.ai.cavalry import Cavalry, Rider
from ascii_adventurers.systems.quests import QUEST_SID
from ascii_adventurers.systems.spawner import Spawner
from ascii_adventurers.tests.test_m29_2 import arena, paradise_map, run
from ascii_adventurers.world import tiles
from ascii_adventurers.world.chunked import ChunkedWorld
from ascii_adventurers.world.landmarks import quest_marks
from ascii_adventurers.world.paradise import plan_of


def cavalry(x=30.5, y=15.5, hero_at=(30.5, 20.5)):
    """A cavalry and its riders in an open arena (no lair: anywhere goes)."""
    c = make_enemy("cavalry", x, y, random.Random(3))
    a = arena(c, *c.riders, hero_at=hero_at)
    c._rest = 99.0                                   # (no move of its own unless asked)
    run(a, 1 / 60)                                   # (a first step: it knows the arena)
    return c, a


def force(c, a, move, seconds=0.0):
    c._gen = None
    c._start(move)
    c._wait = 0.0
    c._rest = 99.0
    if seconds:
        run(a, seconds)


class QuestPlacementTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = ChunkedWorld(31)
        cls.z = cls.w.layout.zone("paradise")
        cls.p = plan_of(cls.w.layout, cls.z)

    def test_the_quest_is_a_seals_quest_on_paradise(self):
        q = config.QUESTS["seven_seals"]
        self.assertEqual((q.biome, q.kind, q.count, q.boss), ("paradise", "seals", 7, "cavalry"))
        camp, lair = quest_marks(self.w.layout, "seven_seals")
        self.assertEqual((camp.key, lair.key), ("paradise_stairway", "paradise_court"))
        self.assertEqual(len(camp.spots), 7)
        self.assertIsNotNone(camp.npc)
        self.assertIs(lair.props["seal"], tiles.GATE_BARS)

    def test_seven_seals_far_apart_each_in_its_clearing(self):
        camp, _ = quest_marks(self.w.layout, "seven_seals")
        for i, (x, y) in enumerate(camp.spots):
            for x2, y2 in camp.spots[i + 1:]:
                self.assertGreaterEqual(math.hypot(x - x2, y - y2), config.SEVEN_SEAL_GAP - 1)
            self.assertTrue(self.z.inside(x, y))
            self.w.ensure_ready(int(x) - 7, int(y) - 7, int(x) + 7, int(y) + 7)
            self.assertIs(self.w.tile_at(math.floor(x), math.floor(y)), tiles.SEVEN_SEAL)
        seals = [m for m in self.w.layout.landmarks if m.key == "paradise_seal"]
        self.assertEqual(len(seals), 7)

    def test_the_ring_quests_are_placed_as_before(self):
        # (the zone's quest comes from its plan, not the ring biomes' placer)
        camps = [m for m in self.w.layout.landmarks if m.kind == "camp"]
        self.assertTrue(all(m.biome != "paradise" or m.key == "paradise_stairway" for m in camps))
        for key, q in config.QUESTS.items():
            if q.biome in config.ZONE_PLACES or q.kind == "finale":
                continue
            camp, lair = quest_marks(self.w.layout, key)
            self.assertIsNotNone(lair, key)


class QuestFlowTest(unittest.TestCase):
    def setUp(self):
        from ascii_adventurers.tests.test_m16 import game
        self.m, self.s = game("wizard", seed=31)
        self.s.app.dev = True
        self.q = self.s.quests.states["seven_seals"]

    def test_guards_stand_round_every_seal(self):
        sids = [sid for sid in self.s.spawner.fixed if sid[0] == QUEST_SID and sid[1] == self.q.qid]
        self.assertEqual(len(sids), 7 * config.SEVEN_SEAL_GUARDS)
        for sid in sids:
            self.assertIn(self.s.spawner.fixed[sid][0], config.SEVEN_SEAL_GUARD_ANGELS)

    def test_hidden_on_the_maps_until_paradise_is_found(self):
        def mine():
            return [p for p in self.s.quests.pins() if p[3] == "THE FALLEN ANGEL"]
        self.assertEqual(mine(), [])
        self.s.world.found_zones.add("paradise")
        self.assertEqual(len(mine()), 1)

    def test_holding_a_seal_breaks_it_while_angels_come_unveiling(self):
        s, q = self.s, self.q
        s._dev_zone()
        x, y = q.camp.spots[0]
        h = s.hero
        h.max_hp = h.hp = 1e9
        s.world.ensure_ready(int(x) - 30, int(y) - 20, int(x) + 30, int(y) + 20)
        h.x, h.y = x + 1.0, y
        before = len(s.enemies)
        for _ in range(round((config.SEVEN_SEAL_TIME + 0.5) * 60)):
            h.x, h.y = x + 1.0, y
            s._step(1 / 60)
            h.hp = h.max_hp
        self.assertIn(0, q.lit)
        self.assertEqual(q.found, 1)
        self.assertIs(s.world.tile_at(math.floor(x), math.floor(y)), tiles.SEVEN_SEAL_BROKEN)
        risen = [e for e in s.enemies[before:] if getattr(e, "state", "") in ("unveiling", "unveiled")]
        self.assertGreater(len(risen), 0)
        self.assertEqual(s.quests.broken_seals("paradise"), 1)

    def test_a_seal_mends_with_nobody_there(self):
        s, q = self.s, self.q
        q.heat[0] = 4.0
        s._step(1.0)
        self.assertLess(q.heat[0], 4.0)

    def test_the_sky_reddens_seal_by_seal(self):
        s, q = self.s, self.q
        s._dev_zone()
        s.quests.banner = None

        def green():
            s.draw(self.m.text)
            c = self.m.display.canvas
            w, h = c.get_size()
            return sum(c.get_at((x, y))[1] for x in range(40, w - 40, 97)
                       for y in range(200, h - 60, 53))

        g0 = green()
        q.found = 3
        g3 = green()
        q.found = 6
        g6 = green()
        self.assertLess(g3, g0)
        self.assertLess(g6, g3)

    def test_the_seventh_seal_opens_the_court_and_its_bars_close_behind_you(self):
        s, q = self.s, self.q
        s.quests.dev_key = "seven_seals"
        self.assertTrue(s.quests.dev_finish_hunt())
        self.assertEqual(q.stage, "awake")
        gx, gy = q.lair.gate[0]
        s.world.ensure_ready(gx - 2, gy - 2, gx + 2, gy + 2)
        self.assertIs(s.world.tile_at(gx, gy), tiles.MARBLE_FLOOR)
        h = s.hero
        h.max_hp = h.hp = 1e9
        h.water_walk = True
        s.world.ensure_ready(int(q.lair.cx) - 50, int(q.lair.cy) - 30,
                             int(q.lair.cx) + 50, int(q.lair.cy) + 30)
        h.x, h.y = q.lair.cx, q.lair.cy + 20
        for _ in range(5):
            s._step(1 / 60)
        self.assertEqual(q.stage, "fight")
        self.assertIsInstance(q.boss, Cavalry)
        self.assertTrue(all(r in s.enemies for r in q.boss.riders))
        self.assertEqual(q.boss.max_hp, config.ENEMIES["cavalry"].max_hp)   # (no zone toughness)
        for _ in range(30):
            s._step(1 / 60)
        self.assertTrue(all(s.world.tile_at(tx, ty) is tiles.GATE_BARS for tx, ty in q.lair.gate))
        self.assertEqual(s.quests.guardians, 0)
        q.boss.hp = 1.0
        q.boss.riders[0].take_damage(10, h, 0.0)
        for _ in range(round((config.HORSEMEN_UNVEIL + 0.2) * 60)):   # (M29.5: it unveils...)
            s._step(1 / 60)
        self.assertEqual(q.stage, "fight")
        for hm in q.boss.horsemen:                                 # (...and they fall too)
            hm.take_damage(hm.hp + 1, h, 0.0)
        for _ in range(3):
            s._step(1 / 60)
        self.assertEqual(q.stage, "cleared")
        self.assertEqual(s.quests.guardians, 0)                # (Paradise's isn't a guardian)
        self.assertIs(s.world.tile_at(gx, gy), tiles.MARBLE_FLOOR)
        self.assertFalse(any(isinstance(e, Rider) for e in s.enemies))


class CavalryTest(unittest.TestCase):
    def test_four_riders_one_health(self):
        c, a = cavalry()
        self.assertEqual(len(c.riders), 4)
        self.assertFalse(c.hittable)
        hp = c.hp
        dealt = c.riders[2].take_damage(100, a.hero, 0.0)
        self.assertEqual(dealt, 100)
        self.assertEqual(c.hp, hp - 100)
        self.assertEqual(c.riders[0].hp, c.hp)
        c.hp = 0.0
        self.assertFalse(any(r.alive for r in c.riders))

    def test_always_riding(self):
        c, a = cavalry()
        last = [(r.x, r.y) for r in c.riders]
        for _ in range(120):
            run(a, 1 / 60)
            now = [(r.x, r.y) for r in c.riders]
            self.assertTrue(all(p != q for p, q in zip(now, last)))
            last = now
        force(c, a, "halos")
        for _ in range(60):
            run(a, 1 / 60)
            now = [(r.x, r.y) for r in c.riders]
            self.assertTrue(any(p != q for p, q in zip(now, last)))   # (slowed, never stopped)
            last = now

    def test_a_signature_more_each_phase(self):
        phases = config.BOSSES["cavalry"].phases
        self.assertEqual([p.below for p in phases], [1.0, 0.75, 0.5, 0.25])
        names = [{m for m, _ in p.moves} for p in phases]
        moves = {"carousel", "hoofs", "halos", "trample"}
        self.assertEqual(names[0], moves | {"formation"})
        self.assertEqual(names[1], moves | {"formation", "lances"})
        self.assertEqual(names[2], moves | {"formation", "lances", "hymn"})
        self.assertEqual(names[3], moves | {"formation", "lances", "hymn", "winds"})

    def test_the_formation_charge_runs_the_lanes_it_shows(self):
        c, a = cavalry(hero_at=(30.5, 18.5))
        force(c, a, "formation", 0.1)
        self.assertEqual(len(c.lanes), 4)
        lanes = [tuple(l) for l in c.lanes]
        self.assertFalse(c.charging)
        run(a, config.CAV_FORMATION[0])
        self.assertTrue(c.charging)
        for r, (x0, y0, x1, y1) in zip(c.riders, lanes):
            # (on its lane, as shown)
            self.assertLess(math.hypot(r.x - x0, r.y - y0) + math.hypot(r.x - x1, r.y - y1)
                            - math.hypot(x1 - x0, y1 - y0), 1.0)
        run(a, 2.5)
        self.assertEqual(c.lanes, [])

    def test_lances_cage_you_and_a_broken_pillar_opens_it(self):
        c, a = cavalry(hero_at=(30.5, 18.5))
        force(c, a, "lances", config.CAV_LANCES[0] + 0.1)
        self.assertEqual(len(c.cages), 1)
        pillars = c.cages[0]["pillars"]
        self.assertEqual(len(pillars), 4)
        self.assertTrue(all(p in a.enemies for p in pillars))
        self.assertEqual(len(c.fences()), 4)
        hp = a.hero.hp
        a.hero.x = (pillars[0].x + pillars[1].x) / 2
        a.hero.y = pillars[0].y + 0.2                        # (on the top fence)
        run(a, 0.05)
        self.assertLess(a.hero.hp, hp)
        pillars[0].take_damage(1e6, a.hero, 0.0)
        run(a, 0.05)
        self.assertEqual(len(c.fences()), 2)

    def test_the_hymn_shields_and_heals_while_together(self):
        c, a = cavalry(hero_at=(30.5, 40.0))
        a.world = paradise_map(w=60, h=60)
        c.hp = c.max_hp * 0.5
        force(c, a, "hymn", 2.5)
        self.assertIsNotNone(c.hymn)
        self.assertTrue(c.hymn["together"])
        self.assertGreater(c.hp, c.max_hp * 0.5)
        hp = c.hp
        c.riders[1].take_damage(100, a.hero, 0.0)
        self.assertAlmostEqual(hp - c.hp, 100 * config.CAV_HYMN[1])

    def test_the_chord_breaks_when_the_lead_is_hurt(self):
        c, a = cavalry(hero_at=(30.5, 40.0))
        a.world = paradise_map(w=60, h=60)
        force(c, a, "hymn", 2.0)
        lead = c.hymn["lead"]
        lead.take_damage(c.max_hp, a.hero, 0.0)
        c.hp = c.max_hp
        run(a, 0.1)
        self.assertIsNone(c.hymn)
        self.assertTrue(any(f.kind == "toast" and "CHORD" in f.label for f in a.effects))

    def test_the_chord_breaks_when_you_come_close(self):
        c, a = cavalry(hero_at=(30.5, 40.0))
        a.world = paradise_map(w=60, h=60)
        force(c, a, "hymn", 2.0)
        r = c.riders[0]
        a.hero.x, a.hero.y = r.x + 2.0, r.y
        run(a, 0.1)
        self.assertIsNone(c.hymn)

    def test_the_four_winds_push_you_but_not_in_a_calm_spot(self):
        c, a = cavalry(hero_at=(30.5, 15.5))
        force(c, a, "winds", 0.05)
        w = c.winds
        self.assertEqual(len(w["corners"]), 4)
        self.assertEqual(len(w["calm"]), config.CAV_WINDS[4])
        while w["gust"] is None:
            run(a, 1 / 60)
        cx, cy = w["calm"][0]
        a.hero.x, a.hero.y = cx, cy
        run(a, 0.3)
        self.assertLess(math.hypot(a.hero.x - cx, a.hero.y - cy), 0.01)
        a.hero.x, a.hero.y = w["centre"][0] + 3.0, w["centre"][1] + 3.0
        for x, y in w["calm"]:
            if math.hypot(a.hero.x - x, a.hero.y - y) <= config.CAV_WINDS[5]:
                a.hero.x += 6.0
        x0, y0 = a.hero.x, a.hero.y
        run(a, 0.2)
        self.assertGreater(math.hypot(a.hero.x - x0, a.hero.y - y0), 0.3)

    def test_carousel_tightens_and_throws_light_inward(self):
        c, a = cavalry(hero_at=(30.5, 15.5))
        force(c, a, "carousel", 0.5)
        r0 = c.ring[2]
        run(a, 1.5)
        self.assertLess(c.ring[2], r0)
        self.assertTrue(any(p.owner is c and p.spec.look == "light" for p in a.projectiles))

    def test_hoof_rings_and_halo_rain(self):
        c, a = cavalry(hero_at=(30.5, 15.5))
        force(c, a, "hoofs", 0.3)
        self.assertGreaterEqual(len(a.projectiles), 4 * config.CAV_HOOFS[2])
        a.projectiles.clear()
        force(c, a, "halos", 0.2)
        self.assertEqual(len(c.marks), config.CAV_HALOS[1])
        hp = a.hero.hp
        run(a, config.CAV_HALOS[0])
        self.assertLess(a.hero.hp, hp)
        self.assertEqual(c.hp, c.max_hp)                      # (its halos spare its riders)

    def test_trample_shows_its_line_then_one_rider_runs_it(self):
        c, a = cavalry(hero_at=(30.5, 15.5))
        force(c, a, "trample", 0.2)
        self.assertIsNotNone(c.line)
        hp = a.hero.hp
        run(a, config.CAV_TRAMPLE[0] + 1.5)
        self.assertIsNone(c.line)
        self.assertLess(a.hero.hp, hp)

    def test_its_shots_and_blasts_pass_its_riders(self):
        c, a = cavalry()
        force(c, a, "hoofs", 2.0)
        self.assertEqual(c.hp, c.max_hp)


class GameTest(unittest.TestCase):
    def test_the_fight_draws_through_every_move(self):
        from ascii_adventurers.tests.test_m16 import game
        m, s = game("wizard", seed=31)
        s.app.dev = True
        q = s.quests.states["seven_seals"]
        s.quests.dev_key = "seven_seals"
        s.quests.dev_finish_hunt()
        h = s.hero
        h.max_hp = h.hp = 1e9
        h.water_walk = True
        s.world.ensure_ready(int(q.lair.cx) - 50, int(q.lair.cy) - 30,
                             int(q.lair.cx) + 50, int(q.lair.cy) + 30)
        h.x, h.y = q.lair.cx, q.lair.cy + 20
        for _ in range(5):
            s._step(1 / 60)
        b = q.boss
        for move in ("formation", "lances", "hymn", "winds", "carousel", "hoofs", "halos",
                     "trample"):
            b._gen = None
            b._start(move)
            b._wait = 0.0
            for _ in range(70):
                s._step(1 / 60)
                h.hp = h.max_hp
            s.me.camera.center_on(h.x, h.y)
            s.draw(m.text)
        self.assertEqual(q.stage, "fight")


if __name__ == "__main__":
    unittest.main()
