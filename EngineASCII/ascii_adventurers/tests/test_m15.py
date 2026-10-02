"""M15: loot, the guild (meta progression) and the walkable Guild Hall."""

import os
import random
import tempfile
import unittest
from collections import Counter

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from ascii_adventurers import config
from ascii_adventurers.meta.guild import Guild, card_price
from ascii_adventurers.meta.run_stats import RunStats
from ascii_adventurers.players import cards


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, unicode="", mod=0)


class GuildTest(unittest.TestCase):
    def test_prices_grow_and_buying(self):
        spec = config.GUILD_UPGRADES["whetstone"]
        self.assertEqual([spec.cost(n) for n in range(3)],
                         [spec.base_cost, round(spec.base_cost * spec.growth),
                          round(spec.base_cost * spec.growth ** 2)])
        g = Guild(loot=spec.cost(0) + spec.cost(1) - 1)
        self.assertTrue(g.buy_upgrade("whetstone"))
        self.assertFalse(g.buy_upgrade("whetstone"))           # can't afford the next
        self.assertEqual((g.level("whetstone"), g.loot), (1, spec.cost(1) - 1))

    def test_max_level(self):
        g = Guild(loot=10 ** 6)
        while g.buy_upgrade("arcane_wing"):
            pass
        self.assertEqual(g.level("arcane_wing"), 1)
        self.assertIsNone(g.next_cost("arcane_wing"))

    def test_hero_upgrades_are_per_hero(self):
        g = Guild(loot=10 ** 6)
        g.buy_upgrade("strong_arm", "dwarf")
        self.assertEqual(g.level("strong_arm", "dwarf"), 1)
        self.assertEqual(g.level("strong_arm", "wizard"), 0)
        self.assertIn(("range", "add", 0.06), g.meta_steps("dwarf"))
        self.assertEqual(g.meta_steps("wizard"), [])

    def test_card_unlocks(self):
        g = Guild(loot=3000)
        self.assertTrue(g.unlocked("sharpened"))                # start card
        self.assertFalse(g.unlocked("berserker"))
        self.assertNotIn("berserker", g.unlocked_cards())
        self.assertTrue(g.buy_card("berserker"))
        self.assertEqual(g.loot, 3000 - card_price("berserker"))
        self.assertTrue(g.unlocked("berserker"))
        self.assertFalse(g.buy_card("berserker"))               # owned already
        self.assertTrue(g.unlocked("multishot"))                # a start card since M19
        self.assertFalse(g.buy_card("sharpened"))               # never for sale

    def test_meta_steps_stack_with_cards(self):
        g = Guild(loot=10 ** 6)
        for _ in range(2):
            g.buy_upgrade("whetstone")
        g.buy_upgrade("arcane_wing")
        g.buy_upgrade("infirmary")
        lo = cards.build_loadout("bard", [("sharpened", "common")], g.meta_steps("bard"))
        self.assertAlmostEqual(lo.stats.damage, 0.04 + 0.10)
        self.assertEqual(lo.stats.spell_slots, config.SPELL_SLOTS + 1)
        self.assertEqual(lo.body.max_hp, config.HEROES["bard"].max_hp + 5)

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "guild.json")
            g = Guild(loot=500, total_loot=900)
            g.guild = {"whetstone": 2}
            g.heroes = {"bard": {"soothing_strings": 1}}
            g.pacts, g.active_pacts, g.pages = {"blood", "horde"}, {"blood"}, {"toad"}
            g.kills = {"toad": 7}
            g.cards = {"overload"}
            g.achievements = {"level_30"}
            self.assertTrue(g.save(path))
            self.assertEqual(Guild.load(path), g)

    def test_load_is_forgiving(self):
        import json
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "guild.json")
            with open(path, "w") as f:
                json.dump({"version": 2, "loot": -5, "total_loot": "lots",
                           "guild": {"whetstone": 99, "nope": 2, "armory": "x"},
                           "heroes": {"bard": {"soothing_strings": 2}, "knight": {}},
                           "cards": ["overload", "no_such_card", 3],
                           "pacts": ["glass", "nope"], "active_pacts": ["glass", "blood"],
                           "kills": {"toad": 3, "dragon": 9, "boar": -1}}, f)
            g = Guild.load(path)
            self.assertEqual((g.loot, g.total_loot), (0, 0))
            self.assertEqual(g.guild, {"whetstone": config.GUILD_UPGRADES["whetstone"].max_level})
            self.assertEqual(g.heroes, {"bard": {"soothing_strings": 2}})
            self.assertEqual((g.pacts, g.active_pacts), ({"glass"}, {"glass"}))
            self.assertEqual(g.kills, {"toad": 3})
            self.assertEqual(g.cards, {"overload"})
            self.assertEqual(Guild.load(os.path.join(d, "missing.json")), Guild())

    def test_bank_run(self):
        g = Guild(loot=10)
        run = RunStats("bard", 1, (0, 0))
        run.loot = 41.7
        self.assertEqual(g.bank_run(run), 41)
        self.assertEqual((g.loot, g.total_loot), (51, 41))


class RunTest(unittest.TestCase):
    def start(self, guild=None, hero="wizard"):
        from ascii_adventurers.tests.test_players import make_manager, start_game
        m = make_manager()
        if guild is not None:
            m.app.guild = guild
        s = start_game(m, seed=31, hero=hero)
        s.mouse.left_held = lambda: False
        self.addCleanup(lambda: pygame.mouse.set_visible(True))
        return m, s

    def test_upgrades_apply_at_the_start(self):
        g = Guild(loot=10 ** 6)
        g.buy_upgrade("infirmary")
        g.buy_upgrade("fortune_teller")
        g.buy_upgrade("extra_dart", "wizard")
        _, s = self.start(g)
        self.assertEqual(s.hero.max_hp, 100 + 5)
        self.assertEqual(s.hero.weapon.spec.pellets, config.WEAPONS["arcane_missiles"].pellets + 1)
        self.assertEqual(s.hero.hp, s.hero.max_hp)
        self.assertEqual(s.me.progress.rerolls, config.CARD_REROLLS + 1)
        self.assertEqual(s.me.progress.banishes, config.CARD_BANISHES)

    def offered(self, s, n=150):
        seen = set()
        prog = s.me.progress
        for _ in range(n):
            prog.picks, prog.offer = 1, []
            s._cards(s.me, None)
            seen.update(k for k, _ in prog.offer)
        return seen

    def test_locked_cards_are_never_offered(self):
        _, s = self.start(hero="huntress")
        self.assertNotIn("hunters_mark", self.offered(s))
        g = Guild(loot=5000)
        g.buy_card("hunters_mark")
        _, s = self.start(g, hero="huntress")
        self.assertIn("hunters_mark", self.offered(s, 400))

    def test_kills_are_worth_loot_at_once(self):
        from ascii_adventurers.ai import make_enemy
        g = Guild(loot=10 ** 6)
        g.buy_upgrade("treasure_map")
        _, s = self.start(g)
        e = make_enemy("ogre", s.hero.x + 4, s.hero.y, random.Random(1))
        s.enemies.append(e)
        e.take_damage(9999, s.hero, 0.0)
        s.update(1 / 60)
        expected = config.ENEMIES["ogre"].xp * config.LOOT_PER_XP * 1.04
        self.assertAlmostEqual(s.stats.loot, expected)
        shard = [ef for ef in s.effects if ef.kind == "loot"]
        self.assertEqual(len(shard), 1)
        self.assertIs(shard[0].target, s.hero)
        s.draw(s.manager.text)

    def test_monster_kills_are_worth_nothing(self):
        from ascii_adventurers.ai import make_enemy
        _, s = self.start()
        e = make_enemy("ogre", s.hero.x + 4, s.hero.y, random.Random(1))
        s.enemies.append(e)
        e.take_damage(9999, None, 0.0)
        s.update(1 / 60)
        self.assertEqual(s.stats.loot, 0)

    def test_loot_is_kept_when_the_run_ends(self):
        m, s = self.start(Guild(loot=7))
        s.stats.loot = 30.4
        s._abandon()
        self.assertEqual(m.app.guild.loot, 37)
        s._end_run()                                              # only once
        self.assertEqual(m.app.guild.loot, 37)

    def test_game_over_offers_the_guild_hall(self):
        from ascii_adventurers.scenes.guild_hall import GuildHallScene
        from ascii_adventurers.ui.overlays import GameOverPanel
        m, s = self.start()
        s.stats.loot = 12
        s.hero.invulnerable = False
        s.hero.take_damage(10 ** 6, None, None)
        for _ in range(90):
            s.update(1 / 60)
        self.assertIsInstance(s.overlay, GameOverPanel)
        labels = [label for label, _ in s.overlay.buttons]
        self.assertIn("Guild Hall", labels)
        s.draw(m.text)
        dict(s.overlay.buttons)["Guild Hall"]()
        self.assertIsInstance(m.scene, GuildHallScene)
        self.assertEqual(m.app.guild.loot, 12)


class DevModeTest(unittest.TestCase):
    def test_full_purse_and_nothing_saved(self):
        from ascii_adventurers.app import App
        from engine import Audio
        g = Guild(loot=5)
        saved = []
        g.save = lambda *a: saved.append(1)
        app = App(Audio(), guild=g, dev=True)
        self.assertEqual(app.guild.loot, config.DEV_LOOT)
        app.records.save = lambda *a: saved.append(1)
        app.save_guild()
        app.save_records()
        self.assertEqual(saved, [])

    def test_l_levels_up_only_in_dev_mode(self):
        from ascii_adventurers.tests.test_players import make_manager, start_game
        for dev in (False, True):
            m = make_manager()
            m.app.dev = dev
            s = start_game(m, seed=31, hero="bard")
            s.mouse.left_held = lambda: False
            s.me.progress.xp = 3
            s.handle_event(key(pygame.K_l))
            s.handle_event(key(pygame.K_l))
            self.assertEqual(s.me.progress.level, 3 if dev else 1)
            self.assertEqual(s.me.progress.picks, 2 if dev else 0)
            s.draw(m.text)
            pygame.mouse.set_visible(True)


class HallTest(unittest.TestCase):
    def setUp(self):
        from ascii_adventurers.scenes.guild_hall import GuildHallScene
        from ascii_adventurers.tests.test_players import make_manager
        self.m = make_manager()
        self.m.app.guild = Guild(loot=100000)
        self.s = GuildHallScene("dwarf")
        self.m._set_scene(self.s)
        self.s.update(1 / 60)

    def tearDown(self):
        pygame.mouse.set_visible(True)

    def go(self, kind, hero=None):
        st = next(s for s in self.s.stations if s.kind == kind and (hero is None or s.hero == hero))
        self.s.hero.x, self.s.hero.y = st.x, st.y + 2       # in front of it
        self.s.update(1 / 60)
        return st

    def test_the_hall(self):
        from ascii_adventurers.world.hub import load_hub
        world, stations = load_hub()
        kinds = Counter(s.kind for s in stations)
        self.assertEqual(kinds, Counter(guild=1, hero=1, cards=1, gate=1, statue=5))
        self.assertEqual({s.hero for s in stations if s.kind == "statue"}, set(config.HEROES))
        sx, sy = world.spawn_point()
        self.assertFalse(world.tile_at(int(sx), int(sy)).solid)
        for s in stations:                                       # people can't be walked through
            if s.kind != "gate":
                self.assertTrue(world.tile_at(int(s.x), int(s.y)).solid, s)

    def test_walls_stop_you(self):
        h = self.s.hero
        h.x, h.y = 2.5, 12.5
        for _ in range(60):
            h.move(-1, 0, 1 / 60, self.s.world)
        self.assertGreater(h.x, 1.0)

    def test_buy_from_the_guildmaster(self):
        self.go("guild")
        self.assertEqual(self.s.near.kind, "guild")
        self.s.handle_event(key(pygame.K_e))
        panel = self.s.panel
        self.assertIsNotNone(panel)
        self.s.handle_event(key(pygame.K_RETURN))                # Whetstone, level 1
        g = self.m.app.guild
        self.assertEqual(g.level("whetstone"), 1)
        self.assertEqual(g.loot, 100000 - config.GUILD_UPGRADES["whetstone"].cost(0))
        self.s.draw(self.m.text)
        self.s.handle_event(key(pygame.K_ESCAPE))
        self.assertIsNone(self.s.panel)

    def test_trainer_switches_heroes(self):
        self.go("hero")
        self.s.interact(self.s.near)
        panel = self.s.panel
        self.assertEqual(panel.hero, "dwarf")
        self.s.handle_event(key(pygame.K_RIGHT))
        self.assertNotEqual(panel.hero, "dwarf")
        hero = panel.hero
        self.s.handle_event(key(pygame.K_RETURN))
        first = list(config.HERO_UPGRADES[hero])[0]
        self.assertEqual(self.m.app.guild.level(first, hero), 1)
        self.s.draw(self.m.text)

    def test_archive(self):
        self.go("cards")
        self.s.interact(self.s.near)
        panel = self.s.panel
        first = panel.keys()[0]
        self.s.handle_event(key(pygame.K_RETURN))
        self.assertTrue(self.m.app.guild.unlocked(first))
        self.assertIsNone(panel.price(first))
        self.s.draw(self.m.text)

    def test_statues_change_the_hero(self):
        self.go("statue", "bard")
        self.assertEqual(self.s.near.hero, "bard")
        self.s.handle_event(key(pygame.K_RETURN))
        self.assertEqual(self.s.hero_key, "bard")
        self.assertEqual(self.s.hero.spec, config.HEROES["bard"])
        self.assertEqual(self.m.app.settings.hero, "bard")
        self.go("statue", "bard")                                # your own pedestal is empty
        self.assertIsNot(self.s.near and self.s.near.hero, "bard")

    def test_gate_and_leaving(self):
        from ascii_adventurers.scenes.new_run import NewRunScene
        from ascii_adventurers.scenes.title import TitleScene
        self.go("gate")
        self.s.handle_event(key(pygame.K_RETURN))                # the gate's panel...
        self.assertEqual(self.s.panel.mode, "gate")
        self.s.draw(self.m.text)
        self.s.handle_event(key(pygame.K_RETURN))                # ..."Enter the dungeon"
        self.assertIsInstance(self.m.scene, NewRunScene)
        self.m._set_scene(self.s)
        self.s.handle_event(key(pygame.K_ESCAPE))
        self.assertIsInstance(self.m.scene, TitleScene)

    def test_draws_on_every_screen(self):
        from engine import Display
        for cols in (80, 128, 172):
            d = Display(cols, 30)
            self.m.display = d
            self.m.text.display = d
            self.s.update(1 / 60)
            self.s.draw(self.m.text)
            x, y = self.s._camera_target()
            view_w = self.s.camera.view_w / config.TILE_PX_W
            if self.s.world.width <= view_w:
                self.assertAlmostEqual(x, self.s.world.width / 2)   # a small hall sits centred
            self.go("guild")
            self.s.interact(self.s.near)
            self.s.draw(self.m.text)
            self.s.panel = None

    def test_title_leads_here(self):
        from ascii_adventurers.scenes.guild_hall import GuildHallScene
        from ascii_adventurers.scenes.title import TitleScene
        t = TitleScene()
        self.m._set_scene(t)
        t.draw(self.m.text)
        t._guild_hall()
        self.assertIsInstance(self.m.scene, GuildHallScene)


if __name__ == "__main__":
    unittest.main()
