"""M22.6: the Guild hall journal -- the archivist's last shelf lists every
quest whose boss you've beaten (story, boss, wins, fastest fight, heroes),
"???" for the rest."""

import json
import os
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from ascii_adventurers import config
from ascii_adventurers.meta.guild import Guild
from ascii_adventurers.tests import test_m16
from ascii_adventurers.tests.test_m16 import key
from ascii_adventurers.tests.test_m17 import game, step, teleport
from ascii_adventurers.tests.test_m22_5 import finish
from ascii_adventurers.ui.guild_panel import SHELVES


class JournalSaveTest(unittest.TestCase):
    def test_record_and_reload(self):
        g = Guild()
        g.record_quest("bad_trip", ["wizard"], 130.04)
        g.record_quest("bad_trip", ["bard", "wizard"], 95.0)      # co-op: one win
        g.record_quest("bad_trip", ["dwarf"], 200.0)
        self.assertEqual(g.journal["bad_trip"],
                         {"wins": 3, "best": 95.0, "heroes": ["bard", "dwarf", "wizard"]})
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "guild.json")
            g.save(path)
            self.assertEqual(Guild.load(path).journal, g.journal)

    def test_a_bad_save_never_breaks(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "guild.json")
            with open(path, "w") as f:
                json.dump({"version": 2, "journal": {
                    "bad_trip": {"wins": 2, "best": "fast", "heroes": ["wizard", "nobody", 3]},
                    "no_such_quest": {"wins": 1},
                    "leech_doctor": {"wins": 0},
                    "smoke_keeper": "oops"}}, f)
            g = Guild.load(path)
        self.assertEqual(g.journal, {"bad_trip": {"wins": 2, "best": None, "heroes": ["wizard"]}})


class JournalFightTest(unittest.TestCase):
    def test_beating_a_boss_writes_the_journal(self):
        m, s = game()
        s.hero.invulnerable = True
        st = finish(s.quests, "bad_trip")
        teleport(s, st.lair.cx, st.lair.cy + st.lair.radii[1] * 0.5)
        step(s, 60)
        st.boss.hp = 0.0
        st.boss.last_hit_by = s.hero
        step(s)
        e = m.app.guild.journal["bad_trip"]
        self.assertEqual(e["wins"], 1)
        self.assertEqual(e["heroes"], [s.me.stats.hero])
        self.assertAlmostEqual(e["best"], st.fight_time, delta=0.1)
        self.assertNotIn("leech_doctor", m.app.guild.journal)   # only beaten bosses


class JournalShelfTest(unittest.TestCase):
    # (The archive UI test's hall, without re-running its tests.)
    setUp = test_m16.ArchiveUiTest.setUp
    tearDown = test_m16.ArchiveUiTest.tearDown
    open = test_m16.ArchiveUiTest.open

    def test_the_journal_shelf(self):
        g = self.m.app.guild
        g.record_quest("leech_doctor", ["bard"], 125.0)
        panel = self.open("cards")
        while SHELVES[panel.shelf] != "journal":
            self.s.handle_event(key(pygame.K_RIGHT))
        rows = panel.rows()
        self.assertEqual([r.key for r in rows], list(config.QUESTS))
        known = {r.key: r for r in rows}["leech_doctor"]
        self.assertEqual(known.name, "Bad Blood")
        self.assertEqual(known.state, "x1")
        self.assertIn("The Leech Swarm", known.info)
        self.assertIn("2:05", known.info)
        self.assertIn("BARD", known.describe)
        self.assertIn("leech doctor", known.describe)
        unknown = {r.key: r for r in rows}["bad_trip"]
        self.assertEqual((unknown.name, unknown.info), ("???", "???"))
        self.assertEqual(unknown.column, "SWAMP")
        loot = g.loot
        self.s.handle_event(key(pygame.K_RETURN))               # nothing to buy
        self.assertEqual(g.loot, loot)
        panel.index = list(config.QUESTS).index("leech_doctor")
        self.s.draw(self.m.text)


if __name__ == "__main__":
    unittest.main()
