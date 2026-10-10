"""P5 (playtest pass, 2026-10-10): difficulty levels. Wanderer (the game as
it was), Knight, Folk Hero, Hero of Legend I-VIII: each level multiplies
enemy (and boss) HP by 1.3 and damage by 1.15, and adds 20% enemies and 40%
loot. Picked on the hero select; beating a boss on a level opens the next."""

import json
import os
import random
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from ascii_adventurers import config
from ascii_adventurers.meta.guild import VERSION, Guild
from ascii_adventurers.meta.settings import GameSettings
from ascii_adventurers.systems.run_rules import difficulty_totals
from ascii_adventurers.systems.spawner import Spawner
from ascii_adventurers.tests.test_m17 import step, teleport
from ascii_adventurers.tests.test_menus import key
from ascii_adventurers.tests.test_players import make_manager
from ascii_adventurers.tests.test_weapons import Dummy


def game(difficulty=None, opened=0, dev=False, hero="wizard", seed=31):
    from ascii_adventurers.scenes.game import GameScene
    m = make_manager()
    m.app.guild.difficulty_open = opened
    m.app.dev = dev
    s = GameScene(hero, seed, difficulty)
    m._set_scene(s)
    s.mouse.left_held = lambda: False
    return m, s


class LevelsTest(unittest.TestCase):
    def test_the_users_names(self):
        self.assertEqual(config.DIFFICULTIES[:3], ("Wanderer", "Knight", "Folk Hero"))
        self.assertEqual(config.DIFFICULTIES[3], "Hero of Legend I")
        self.assertEqual(config.DIFFICULTIES[-1], "Hero of Legend VIII")
        self.assertEqual(len(config.DIFFICULTIES), 11)

    def test_the_steep_table(self):
        t = difficulty_totals(0)
        self.assertEqual((t["hp"], t["damage"], t["enemies"], t["loot"]), (1.0, 1.0, 0.0, 0.0))
        t = difficulty_totals(1)
        self.assertAlmostEqual(t["hp"], 1.3)
        self.assertAlmostEqual(t["damage"], 1.15)
        self.assertAlmostEqual(t["enemies"], 0.2)
        self.assertAlmostEqual(t["loot"], 0.4)
        t = difficulty_totals(10)
        self.assertAlmostEqual(t["hp"], 13.79, places=2)           # compounding
        self.assertAlmostEqual(t["damage"], 4.05, places=2)
        self.assertAlmostEqual(t["enemies"], 2.0)                  # x3 as many
        self.assertAlmostEqual(t["loot"], 4.0)                     # +400%
        self.assertEqual(difficulty_totals(99)["name"], "Hero of Legend VIII")


class EnemiesTest(unittest.TestCase):
    def wake(self, level, name="warrior"):
        sp = Spawner(None, 31)
        t = difficulty_totals(level)
        sp.hp_mult, sp.damage_mult = t["hp"], t["damage"]
        return sp.wake(name, 10.5, 10.5, None, random.Random(1))

    def test_enemies_wake_tougher(self):
        base, hard = self.wake(0), self.wake(3)
        self.assertEqual(hard.max_hp, round(base.max_hp * 1.3 ** 3))
        self.assertEqual(hard.hp, hard.max_hp)
        self.assertAlmostEqual(hard.damage_mult, base.damage_mult * 1.15 ** 3)

    def test_bosses_too(self):
        base, hard = self.wake(0, "froggy"), self.wake(2, "froggy")
        self.assertEqual(hard.max_hp, round(base.max_hp * 1.3 ** 2))
        self.assertAlmostEqual(hard.damage_mult, base.damage_mult * 1.15 ** 2)

    def test_a_swarm_shares_its_tougher_health(self):
        hard = self.wake(2, "leech_swarm")
        self.assertAlmostEqual(sum(p.max_hp for p in hard.parts), hard.max_hp)
        self.assertEqual(hard.max_hp, round(round(self.wake(0, "leech_swarm").max_hp) * 1.69))


class RunTest(unittest.TestCase):
    def test_only_opened_levels_unless_dev(self):
        m, s = game(difficulty=5, opened=2)
        self.assertEqual(s.difficulty, 2)                           # clamped to what's open
        m, s = game(difficulty=5, opened=2, dev=True)
        self.assertEqual(s.difficulty, 5)
        m, s = game(opened=4)                                       # None: the settings' pick
        self.assertEqual(s.difficulty, m.app.settings.difficulty)

    def test_more_enemies_and_their_numbers(self):
        m, s = game(difficulty=3, opened=3)
        s._update_spawner()
        sp = s.spawner
        self.assertAlmostEqual(sp.density, 1.6)
        self.assertAlmostEqual(sp.hp_mult, 1.3 ** 3)
        self.assertAlmostEqual(sp.damage_mult, 1.15 ** 3)

    def test_more_loot(self):
        got = {}
        for level in (0, 2):
            m, s = game(difficulty=level, opened=2)
            d = Dummy(s.hero.x + 3, s.hero.y)
            d.espec = config.ENEMIES["warrior"]
            s._loot(s.me, d)
            got[level] = s.me.stats.loot
        self.assertAlmostEqual(got[2], got[0] * 1.8)

    def test_restart_keeps_the_difficulty(self):
        m, s = game(difficulty=1, opened=1)
        s._restart()
        self.assertEqual(m.scene.difficulty, 1)

    def test_shown_in_the_pause_menu(self):
        m, s = game(difficulty=1, opened=1)
        self.assertIn("KNIGHT", s._where())
        self.assertEqual(s.stats.difficulty, 1)


class UnlockTest(unittest.TestCase):
    def test_a_boss_opens_the_next_level(self):
        for level, opened, after in ((0, 0, 1), (1, 1, 2), (0, 3, 3), (10, 10, 10)):
            m, s = game(difficulty=level, opened=opened, dev=level > opened)
            q = s.quests
            st = q.states["bad_trip"]
            q.dev_finish_hunt()
            teleport(s, st.lair.cx, st.lair.cy + st.lair.radii[1] * 0.5)
            step(s, 2)
            self.assertEqual(st.stage, "fight")
            q._win(st, s.hero)
            self.assertEqual(m.app.guild.difficulty_open, after, (level, opened))

    def test_boss_loot_grows_too(self):
        m, s = game(difficulty=2, opened=2)
        q = s.quests
        st = q.states["bad_trip"]
        q.dev_finish_hunt()
        teleport(s, st.lair.cx, st.lair.cy + st.lair.radii[1] * 0.5)
        step(s, 2)
        before = s.me.stats.loot
        q._win(st, s.hero)
        self.assertEqual(s.me.stats.loot - before, round(config.BOSSES["froggy"].loot * 1.8))

    def test_the_guild_keeps_it(self):
        g = Guild()
        self.assertTrue(g.open_difficulty(0))
        self.assertFalse(g.open_difficulty(0))                      # already open
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "guild.json")
            g.save(path)
            self.assertEqual(Guild.load(path).difficulty_open, 1)
            with open(path, "w") as f:
                json.dump({"version": VERSION, "difficulty_open": 99}, f)
            self.assertEqual(Guild.load(path).difficulty_open, len(config.DIFFICULTIES) - 1)
            with open(path, "w") as f:
                json.dump({"version": VERSION, "difficulty_open": "lots"}, f)
            self.assertEqual(Guild.load(path).difficulty_open, 0)

    def test_settings_remember_the_pick(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "settings.json")
            s = GameSettings()
            s.difficulty = 4
            s.save(path)
            self.assertEqual(GameSettings.load(path).difficulty, 4)
            with open(path, "w") as f:
                json.dump({"difficulty": 42}, f)
            self.assertEqual(GameSettings.load(path).difficulty, 0)


class HeroSelectTest(unittest.TestCase):
    def scene(self, opened, dev=False):
        from ascii_adventurers.scenes.new_run import NewRunScene
        m = make_manager()
        m.app.guild.difficulty_open = opened
        m.app.dev = dev
        m.app.save_settings = lambda: None
        sc = NewRunScene()
        m._set_scene(sc)
        sc.update(1 / 60)
        sc.draw(m.text)
        return m, sc

    def test_lists_the_opened_levels(self):
        m, sc = self.scene(2)
        self.assertEqual(sc._difficulty.values, [0, 1, 2])
        m, sc = self.scene(0, dev=True)
        self.assertEqual(len(sc._difficulty.values), len(config.DIFFICULTIES))

    def test_pick_and_start(self):
        m, sc = self.scene(2)
        sc.handle_event(key(pygame.K_DOWN))                         # to the difficulty
        sc.handle_event(key(pygame.K_RIGHT))
        sc.handle_event(key(pygame.K_RIGHT))
        self.assertEqual(sc._difficulty.value, 2)
        what, unlock = sc._difficulty_lines()
        self.assertIn("HP x1.7", what)
        self.assertIn("Hero of Legend I", unlock)                   # how the next one opens
        sc.draw(m.text)
        sc.handle_event(key(pygame.K_RETURN))
        self.assertEqual(m.scene.difficulty, 2)
        self.assertEqual(m.app.settings.difficulty, 2)
        pygame.mouse.set_visible(True)


if __name__ == "__main__":
    unittest.main()
