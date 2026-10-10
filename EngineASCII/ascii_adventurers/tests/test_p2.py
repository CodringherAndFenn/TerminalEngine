"""P1 + P2 (playtest pass, 2026-10-10): a smaller island (radius -20%),
4x the quest targets, every quest giver pinned from the start (round, in
its biome's colour), and the dev keys F5 (next quest) / F9 (to a target)."""

import math
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from ascii_adventurers import config, palette
from ascii_adventurers.systems.quests import QUEST_SID
from ascii_adventurers.tests.test_m17 import game, step, teleport, world
from ascii_adventurers.tests.test_m22_5 import finish
from ascii_adventurers.tests.test_weapons import Dummy
from ascii_adventurers.ui import maps
from ascii_adventurers.world.landmarks import spot_count

SEEDS = (31, 7, 12)


def key(s, k):
    s.handle_event(pygame.event.Event(pygame.KEYDOWN, key=k, unicode="", mod=0))


class IslandTest(unittest.TestCase):
    def test_the_island_is_a_fifth_smaller(self):
        self.assertEqual(config.WORLD_RADIUS, 2209)
        lay = world(31).layout
        self.assertEqual(lay.radius, 2209)
        # Beyond every wobble of the coast it's all ocean.
        r = lay.max_land_radius + 1
        for a in range(0, 360, 15):
            x, y = math.cos(math.radians(a)) * r, math.sin(math.radians(a)) * r
            self.assertEqual(lay.biome_at(x, y).name, "ocean")


class TargetsTest(unittest.TestCase):
    def test_every_quest_gets_four_times_its_count(self):
        for seed in SEEDS:
            lay = world(seed).layout
            for k, q in config.QUESTS.items():
                camp = next((m for m in lay.landmarks if m.quest == k and m.kind == "camp"), None)
                if camp is None:
                    continue
                self.assertEqual(len(camp.spots), q.count * 4, (seed, k))
                self.assertEqual(spot_count(q), q.count * 4)
                for x, y in camp.spots:
                    self.assertEqual(lay.biome_at(x, y).name, q.biome, (seed, k))
                gaps = [math.hypot(a[0] - b[0], a[1] - b[1])
                        for i, a in enumerate(camp.spots) for b in camp.spots[i + 1:]]
                self.assertGreater(min(gaps), 150, (seed, k))   # still screens apart

    def test_any_count_of_them_finishes_it(self):
        m, s = game()
        q = s.quests
        st = q.states["bad_trip"]
        for i in range(len(st.camp.spots) - st.spec.count, len(st.camp.spots)):  # the LAST ones
            frog = Dummy(*st.camp.spots[i])
            frog.spawn_id = (QUEST_SID, st.qid, i, 0)
            q.on_death(frog, None)
        self.assertEqual(st.stage, "awake")


class GiverPinTest(unittest.TestCase):
    def test_every_giver_is_pinned_in_its_biome_colour(self):
        m, s = game()
        q = s.quests
        pins = {(x, y): (k, label) for x, y, k, label in q.pins((s.hero.x, s.hero.y))}
        for st in q.states.values():
            kind, label = pins[(st.npc.x, st.npc.y)]
            self.assertEqual(kind, f"giver_{st.biome}")
            self.assertEqual(label, st.spec.camp_name)
            self.assertEqual(maps._PIN_COLORS[kind], palette.PIN_GIVER[st.biome])
        # Five different colours, none of them the "done" grey or a target's violet.
        fills = {palette.PIN_GIVER[b][0] for b in config.BIOME_RING}
        self.assertEqual(len(fills), 5)
        self.assertNotIn(palette.PIN_DONE[0], fills)
        self.assertNotIn(palette.PIN_TARGET[0], fills)

    def test_grey_once_its_boss_is_beaten(self):
        m, s = game()
        q = s.quests
        st = q.states["bad_trip"]
        st.stage = "cleared"
        kinds = {(x, y): k for x, y, k, _ in q.pins()}
        self.assertEqual(kinds[(st.npc.x, st.npc.y)], "giver_done")

    def test_the_pin_follows_a_walking_giver(self):
        m, s = game()
        q = s.quests
        st = next(st for st in q.states.values() if st.spec.kind == "escort")
        st.npc.x += 30.0
        self.assertIn((st.npc.x, st.npc.y), [(x, y) for x, y, k, _ in q.pins()
                                             if k.startswith("giver_")])

    def test_round_pins_draw(self):
        m, s = game()
        for kind in [f"giver_{b}" for b in palette.PIN_GIVER] + ["giver_done", "lair", "target"]:
            maps.draw_pin(s.sprites, kind, 100, 100)
        key(s, pygame.K_m)                                  # the big map
        self.assertTrue(s.map_open)
        s.draw(m.text)
        key(s, pygame.K_m)
        s.draw(m.text)                                      # (the minimap)


class DevKeysTest(unittest.TestCase):
    def setUp(self):
        config.QUEST_FOCUS = None

    def tearDown(self):
        config.QUEST_FOCUS = None

    def test_f5_cycles_every_quest(self):
        m, s = game()
        s.app.dev = True
        q = s.quests
        keys = list(q.states)
        self.assertEqual(q.dev_quest().key, keys[0])
        seen = []
        for _ in keys:
            key(s, pygame.K_F5)
            seen.append(q.dev_quest().key)
        self.assertEqual(seen, keys[1:] + keys[:1])          # all of them, then round again
        s.draw(m.text)                                      # (the DEV bar names it)

    def test_f5_beats_the_focus(self):
        m, s = game()
        q = s.quests
        config.QUEST_FOCUS = "smoke_keeper"
        self.assertEqual(q.dev_quest().key, "smoke_keeper")
        q.dev_cycle()
        self.assertEqual(q.dev_quest().key, list(q.states)[list(q.states).index("smoke_keeper") + 1])

    def test_f9_jumps_to_the_nearest_target_still_to_do(self):
        m, s = game()
        s.app.dev = True
        q = s.quests
        q.dev_key = "smoke_keeper"
        st = q.states["smoke_keeper"]
        hx, hy = s.hero.x, s.hero.y
        near = min(st.camp.spots, key=lambda p: math.hypot(p[0] - hx, p[1] - hy))
        self.assertEqual(q.dev_spot("target", (hx, hy)), near)
        st.lit.add(st.camp.spots.index(near))               # done: the next nearest
        self.assertNotEqual(q.dev_spot("target", (hx, hy)), near)
        key(s, pygame.K_F9)
        x, y = q.dev_spot("target", (hx, hy))
        self.assertLess(math.hypot(s.hero.x - x, s.hero.y - y), 8.0)

    def test_f9_skips_dead_quarry(self):
        m, s = game()
        q = s.quests
        q.dev_key = "bad_trip"
        st = q.states["bad_trip"]
        first = q.dev_spot("target", (0.0, 0.0))
        i = st.camp.spots.index(first)
        s.spawner.dead.add((QUEST_SID, st.qid, i, 0))
        self.assertNotEqual(q.dev_spot("target", (0.0, 0.0)), first)
        finish(q, "bad_trip")
        self.assertIsNone(q.dev_spot("target", (0.0, 0.0)))   # (not hunting any more)

    def test_dev_big_map_pins_every_target(self):
        m, s = game()
        q = s.quests
        n = sum(len(q.open_targets(st)) for st in q.states.values())
        self.assertEqual([k for *_, k, _ in q.pins((s.hero.x, s.hero.y))].count("target"), 0)
        every = [k for *_, k, _ in q.pins((s.hero.x, s.hero.y), every_target=True)]
        self.assertEqual(every.count("target"), n)
        s.app.dev = True
        self.assertFalse(s.dev_targets)                     # off at first: a normal run's maps
        key(s, pygame.K_m)
        self.assertTrue(s.map_open)
        s.draw(m.text)
        key(s, pygame.K_F4)                                 # on, with the map open
        self.assertTrue(s.dev_targets)
        self.assertTrue(s.map_open)
        s.draw(m.text)
        key(s, pygame.K_m)
        key(s, pygame.K_F4)                                 # and off, with it closed
        self.assertFalse(s.dev_targets)

    def test_f4_does_nothing_outside_dev_mode(self):
        m, s = game()
        s.app.dev = False
        key(s, pygame.K_F4)
        self.assertFalse(s.dev_targets)


class AreaTest(unittest.TestCase):
    def test_targets_show_within_250_tiles_on_both_maps(self):
        self.assertEqual(config.QUEST_TARGET_PIN_RADIUS, 250)
        m, s = game()
        q = s.quests
        st = q.states["bad_trip"]
        st.taken = True
        x, y = st.camp.spots[0]
        def shown(hx, hy):
            return (x, y) in [(px, py) for px, py, k, _ in q.pins((hx, hy)) if k == "target"]
        self.assertTrue(shown(x + 240, y))                  # in its general area
        self.assertFalse(shown(x + 260, y))                 # too far
        st.taken = False
        self.assertFalse(shown(x, y))                       # untaken: hidden, even right there


if __name__ == "__main__":
    unittest.main()
