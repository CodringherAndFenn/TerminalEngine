import json
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from engine import Audio, Display, SceneManager

from ascii_adventurers import config
from ascii_adventurers.app import App, app_of
from ascii_adventurers.meta.records import Records
from ascii_adventurers.meta.run_stats import RunStats, format_time
from ascii_adventurers.meta.settings import GameSettings
from ascii_adventurers.ui import logo

DT = 1 / 60


def key(k, unicode=""):
    return pygame.event.Event(pygame.KEYDOWN, key=k, unicode=unicode)


class SettingsFileTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = Path(self.dir.name) / "save" / "settings.json"

    def tearDown(self):
        self.dir.cleanup()

    def test_defaults_are_portable(self):
        s = GameSettings.load(self.path)          # no file yet
        self.assertEqual(s.monitor, 0)
        self.assertIsNone(s.audio_device)         # follow the OS default
        self.assertIsNone(s.window_size)          # fit the window to the screen
        self.assertIsNone(s.seed)

    def test_round_trip(self):
        s = GameSettings(window_mode="borderless", monitor=1, window_size=(1600, 900),
                         vsync=False, volume=0.3, sfx_volume=0.9, audio_device="Headset",
                         show_fps=False, hero="bard", seed=4242)
        self.assertTrue(s.save(self.path))
        self.assertEqual(GameSettings.load(self.path), s)

    def test_bad_values_fall_back_one_by_one(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text(json.dumps({
            "window_mode": "sideways", "monitor": -1, "window_size": [5, "x"],
            "vsync": "yes", "volume": 7, "sfx_volume": True, "audio_device": 3,
            "show_fps": False, "hero": "dragon", "seed": -5,
        }))
        s = GameSettings.load(self.path)
        d = GameSettings()
        self.assertEqual((s.window_mode, s.monitor, s.window_size, s.vsync),
                         (d.window_mode, d.monitor, d.window_size, d.vsync))
        self.assertEqual(s.volume, 1.0)           # clamped
        self.assertEqual(s.sfx_volume, d.sfx_volume)
        self.assertIsNone(s.audio_device)
        self.assertFalse(s.show_fps)              # the one good value is kept
        self.assertEqual((s.hero, s.seed), (d.hero, None))

    def test_corrupt_file_gives_defaults(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text("{not json")
        self.assertEqual(GameSettings.load(self.path), GameSettings())


class RecordsTest(unittest.TestCase):
    def run_with(self, time=0.0, kills=0, furthest=0.0, biomes=()):
        r = RunStats("wizard", 1, (0.0, 0.0))
        r.time, r.furthest, r.biomes = time, furthest, list(biomes)
        for _ in range(kills):
            r.killed("ogre")
        return r

    def test_first_run_sets_records_quietly_then_breaks_them(self):
        rec = Records()
        self.assertEqual(rec.add_run(self.run_with(60, 3, 100, ["plains"])), set())
        self.assertEqual((rec.runs, rec.most_kills, rec.longest_time), (1, 3, 60.0))
        broken = rec.add_run(self.run_with(30, 5, 100, ["plains", "forest"]))
        self.assertEqual(broken, {"most_kills", "most_biomes"})
        self.assertEqual((rec.runs, rec.total_kills, rec.longest_time), (2, 8, 60.0))

    def test_round_trip_and_forgiving_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "records.json"
            rec = Records(runs=3, total_kills=40, longest_time=321.5, most_kills=20,
                          furthest=900.0, most_biomes=4)
            rec.save(path)
            self.assertEqual(Records.load(path), rec)
            path.write_text(json.dumps({"runs": -2, "most_kills": "lots", "furthest": 12}))
            loaded = Records.load(path)
            self.assertEqual((loaded.runs, loaded.most_kills, loaded.furthest), (0, 0, 12.0))


class RunStatsTest(unittest.TestCase):
    def test_tracks_time_distance_biomes_and_kills(self):
        r = RunStats("dwarf", 7, (10.0, 10.0))
        r.tick(0.5, 13.0, 14.0, 5.0, "plains")
        r.tick(0.5, 11.0, 10.0, 8.0, "forest")
        r.tick(0.5, 11.0, 10.0, 8.0, "plains")
        r.killed("ogre"); r.killed("ogre"); r.killed("warlock")
        self.assertAlmostEqual(r.time, 1.5)
        self.assertAlmostEqual(r.furthest, 5.0)
        self.assertEqual(r.biomes, ["plains", "forest"])
        self.assertEqual(r.total_kills, 3)
        self.assertEqual(format_time(125.9), "2:05")


class HudTest(unittest.TestCase):
    """The corners HUD (ui/hud.py)."""

    def draw(self, cols, **kw):
        from ascii_adventurers.ui import hud
        d = Display(cols, 30)
        calls = []

        class Rec:
            display = d

            def put(self, col, row, s, *a, **k):
                calls.append((col, row, s))

        info = dict(hp=72, max_hp=100, level=4, xp_frac=0.6, kills=12, time=125.0, fps=59.7)
        info.update(kw)
        hud._cache["key"] = None
        hud.draw_hud(Rec(), hud.HudInfo(**info))
        return calls

    def test_fits_every_screen_and_leaves_the_minimap_corner_free(self):
        for cols in (80, 115, 128, 172):
            calls = self.draw(cols, time=10.0)
            self.assertLessEqual(max(c + len(s) for c, _, s in calls), cols, cols)
            minimap_left = cols - config.MINIMAP_COLS - 2 - config.MINIMAP_MARGIN
            top_rows = [(c, s) for c, r, s in calls if r <= config.MINIMAP_ROWS + 1]
            self.assertTrue(all(c + len(s) <= minimap_left for c, s in top_rows), cols)

    def test_shows_hp_level_kills_and_clock(self):
        texts = " ".join(s for _, _, s in self.draw(128))
        for part in ("HP", " 72", "LV", "  4", "KILLS 12", "2:05"):
            self.assertIn(part, texts)

    def test_fps_is_optional(self):
        self.assertTrue(any("FPS" in s for _, _, s in self.draw(128)))
        self.assertFalse(any("FPS" in s for _, _, s in self.draw(128, fps=None)))

    def test_no_controls_hint(self):
        texts = " ".join(s for _, _, s in self.draw(128, time=5.0))
        self.assertNotIn("walk", texts)

    def test_only_aiming_weapons_show_a_reticle(self):
        self.assertFalse(config.WEAPONS[config.HEROES["bard"].weapon].aims)
        for hero in ("wizard", "dwarf", "princess", "huntress"):
            self.assertTrue(config.WEAPONS[config.HEROES[hero].weapon].aims, hero)

    def test_boss_bar_only_in_a_boss_fight(self):
        self.assertFalse(any("OGRE KING" in s for _, _, s in self.draw(128)))
        self.assertTrue(any("OGRE KING" in s for _, _, s in self.draw(128, boss=("ogre king", 0.5))))


class ProgressTest(unittest.TestCase):
    def test_levels_need_more_xp_each_time_and_bank_card_picks(self):
        from ascii_adventurers.players.progress import Progress, xp_for_level
        needs = [xp_for_level(n) for n in range(1, 6)]
        self.assertEqual(needs, sorted(needs))
        self.assertEqual(needs[0], config.LEVEL_XP_BASE)
        p = Progress()
        self.assertEqual(p.add(needs[0] - 1), 0)
        self.assertEqual(p.add(1 + needs[1] + 2), 2)             # two levels at once
        self.assertEqual((p.level, p.xp, p.picks), (3, 2, 2))
        self.assertAlmostEqual(p.frac, 2 / needs[2])

    def test_kills_drop_a_gem_that_gives_xp_when_picked_up(self):
        import random
        from ascii_adventurers.ai import make_enemy
        from ascii_adventurers.scenes.game import GameScene
        d = Display(128, 30)
        m = SceneManager(d, GameSettings(), Audio())
        m.app = App(m.audio, GameSettings(), Records(), persist=False)
        s = GameScene("wizard", 5)
        m._set_scene(s)
        e = make_enemy("ogre", s.hero.x + 4, s.hero.y, random.Random(1))
        s.enemies.append(e)
        e.take_damage(9999, s.hero, 0.0)
        s.update(1 / 60)
        xp = config.ENEMIES["ogre"].xp
        self.assertEqual((s.me.progress.level, s.me.progress.xp), (1, 0))   # not yet: a gem
        self.assertEqual([g.value for g in s.gems], [xp])
        s.gems[0].x, s.gems[0].y = s.hero.x + 1, s.hero.y       # within pickup reach
        for _ in range(30):
            s.update(1 / 60)
        self.assertEqual(s.gems, [])
        self.assertEqual((s.me.progress.level, s.me.progress.xp), (1 + (xp >= config.LEVEL_XP_BASE),
                                                                   xp % config.LEVEL_XP_BASE))
        self.assertEqual(any(ef.kind == "levelup" for ef in s.effects), xp >= config.LEVEL_XP_BASE)
        pygame.mouse.set_visible(True)


class LogoTest(unittest.TestCase):
    def test_every_letter_has_a_bitmap(self):
        for ch in "ASCII ADVENTURERS":
            self.assertEqual(len(logo._FONT[ch]), logo.LETTER_H)


class SceneFlowTest(unittest.TestCase):
    """Title -> new run -> game -> pause -> abandon, headless, saving nothing."""

    def setUp(self):
        self.display = Display(128, 30)
        self.m = SceneManager(self.display, GameSettings(), Audio())
        self.m.app = App(self.m.audio, GameSettings(), Records(), persist=False)
        self.m.app.settings.save = lambda *a: self.fail("tried to write settings")
        self.m.app.records.save = lambda *a: self.fail("tried to write records")
        self.m.switch_to = lambda scene, **kw: self.m._set_scene(scene)

    def tearDown(self):
        pygame.mouse.set_visible(True)

    def frame(self, n=1):
        for _ in range(n):
            self.m.scene.update(DT)
            self.m.scene.draw(self.m.text)

    def test_full_flow(self):
        from ascii_adventurers.scenes.game import GameScene
        from ascii_adventurers.scenes.new_run import NewRunScene
        from ascii_adventurers.scenes.title import TitleScene
        from ascii_adventurers.ui.overlays import PauseMenu

        self.m._set_scene(TitleScene())
        self.frame(2)
        self.m.scene.handle_event(key(pygame.K_RETURN))          # New run
        self.assertIsInstance(self.m.scene, NewRunScene)
        self.frame(2)
        self.m.scene.handle_event(key(pygame.K_RIGHT))           # next hero
        for ch in "0412":                                        # leading 0 dropped
            self.m.scene.handle_event(key(getattr(pygame, f"K_{ch}"), ch))
        self.frame()
        self.m.scene.handle_event(key(pygame.K_RETURN))          # start
        game = self.m.scene
        self.assertIsInstance(game, GameScene)
        heroes = list(config.HEROES)
        self.assertEqual(game.hero_key, heroes[(heroes.index(config.START_HERO) + 1) % len(heroes)])
        self.assertEqual(game.world.seed, 412)
        self.assertEqual(self.m.app.settings.seed, 412)          # remembered
        game.mouse.left_held = lambda: False
        self.frame(3)

        game.handle_event(key(pygame.K_ESCAPE))                  # pause
        self.assertIsInstance(game.overlay, PauseMenu)
        t = game.stats.time
        game.hero.vx = 5.0
        pos = (game.hero.x, game.hero.y)
        self.frame(10)
        self.assertEqual((game.hero.x, game.hero.y), pos)        # frozen
        self.assertEqual(game.stats.time, t)
        game.handle_event(key(pygame.K_ESCAPE))                  # resume
        self.assertIsNone(game.overlay)
        self.frame()
        self.assertGreater(game.stats.time, t)

        game.handle_event(key(pygame.K_ESCAPE))
        game.handle_event(key(pygame.K_DOWN))                    # Settings
        game.handle_event(key(pygame.K_RETURN))
        from ascii_adventurers.ui.settings_panel import SettingsPanel
        self.assertIsInstance(game.overlay, SettingsPanel)
        self.frame()
        game.handle_event(key(pygame.K_ESCAPE))                  # back to pause
        self.assertIsInstance(game.overlay, PauseMenu)
        game.handle_event(key(pygame.K_DOWN))                    # Abandon run
        game.handle_event(key(pygame.K_RETURN))
        self.assertIsInstance(self.m.scene, TitleScene)
        self.assertEqual(self.m.app.records.runs, 1)
        self.frame()                                             # title shows records

    def test_death_shows_game_over_records_once_and_r_goes_again(self):
        from ascii_adventurers.scenes.game import GameScene
        from ascii_adventurers.ui.overlays import GameOverPanel

        self.m.app.records = Records(runs=1, most_kills=0)       # so breaking is visible
        self.m.app.records.save = lambda *a: None
        self.m._set_scene(GameScene(hero="huntress", seed=99))
        game = self.m.scene
        game.mouse.left_held = lambda: False
        self.frame(2)
        game.stats.killed("ogre")
        game.hero.take_damage(999, None, None)
        self.frame(int(1.2 / DT))
        self.assertIsInstance(game.overlay, GameOverPanel)
        self.assertEqual(self.m.app.records.runs, 2)
        self.assertIn("most_kills", game.broken)
        self.frame(5)
        self.assertEqual(self.m.app.records.runs, 2)             # counted once
        game.handle_event(key(pygame.K_r))
        again = self.m.scene
        self.assertIsNot(again, game)
        self.assertEqual((again.hero_key, again.world.seed), ("huntress", 99))


class SettingsPanelTest(unittest.TestCase):
    def setUp(self):
        self.display = Display(128, 30)
        self.m = SceneManager(self.display, GameSettings(), Audio())
        self.saves = []
        app = app_of(self.m)          # persist=False
        app.save_settings = lambda: self.saves.append(1)
        from ascii_adventurers.ui.settings_panel import SettingsPanel
        self.back = []
        self.panel = SettingsPanel(self.m, lambda: self.back.append(1))
        self.app = app

    def focus(self, label):
        ui = self.panel._ensure()
        for i, w in enumerate(ui.widgets):
            if getattr(w, "label", None) == label:
                ui.index = i
                return w
        self.fail(label)

    def test_changes_apply_and_save(self):
        self.panel.draw(self.m.text)
        self.focus("Effects volume")
        self.panel.handle_event(key(pygame.K_LEFT))
        self.assertAlmostEqual(self.app.settings.sfx_volume, config.SFX_VOLUME - 0.05)
        self.assertAlmostEqual(self.app.sfx.volume, self.app.settings.sfx_volume)
        self.focus("Show FPS")
        self.panel.handle_event(key(pygame.K_RIGHT))
        self.assertFalse(self.app.settings.show_fps)
        self.focus("Vsync")
        self.panel.handle_event(key(pygame.K_RIGHT))
        self.assertNotEqual(self.app.settings.vsync, config.VSYNC)
        self.assertGreaterEqual(len(self.saves), 3)
        self.panel.draw(self.m.text)
        self.panel.handle_event(key(pygame.K_ESCAPE))
        self.assertEqual(self.back, [1])

    def test_window_size_only_in_windowed_mode(self):
        self.assertTrue(self.focus("Window size").enabled)


if __name__ == "__main__":
    unittest.main()
