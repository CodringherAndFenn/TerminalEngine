"""M22.5: every boss in every run. All of a biome's quests exist at once,
their camps and lairs at random spots in the biome; the quests are hidden
(no pins, no log) unless taken from a giver, and finishing one without its
giver still wakes the boss."""

import math
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.systems.quests import QUEST_SID
from ascii_adventurers.tests.test_m17 import game, step, teleport, world
from ascii_adventurers.tests.test_weapons import Dummy
from ascii_adventurers.world.landmarks import quest_marks

SWAMP = ("bad_trip", "leech_doctor", "smoke_keeper")


def finish(q, key):
    """Every target of a quest done, as if players found them (no giver)."""
    st = q.states[key]
    if st.spec.kind in ("light", "collect", "survive", "escort", "rescue", "fetch"):
        for i in range(st.spec.count):
            st.lit.add(i)
            q._found(st, st.npc)
        return st
    for i in range(st.spec.count):
        frog = Dummy(*st.camp.spots[i])
        frog.spawn_id = (QUEST_SID, st.qid, i, 0)
        q.on_death(frog, None)
    return st


class PlacementTest(unittest.TestCase):
    def test_every_swamp_quest_has_its_camp_and_lair_in_the_swamp(self):
        for seed in (1, 2, 31, 999):
            layout = world(seed).layout
            for key in SWAMP:
                camp, lair = quest_marks(layout, key)
                self.assertIsNotNone(camp, (seed, key))
                self.assertIsNotNone(lair, (seed, key))
                for m in (camp, lair):
                    self.assertEqual(layout.biome_at(m.cx, m.cy).name, "swamp", (seed, key))

    def test_the_lairs_move_from_run_to_run(self):
        spots = {seed: quest_marks(world(seed).layout, "bad_trip")[1] for seed in (1, 2, 31)}
        # Same distance from the centre each run would mean a fixed ring.
        dists = {round(math.hypot(m.cx, m.cy)) for m in spots.values()}
        self.assertEqual(len(dists), 3)

    def test_quests_dont_share_target_spots(self):
        layout = world(31).layout
        spots = [(k, p) for k in SWAMP for p in quest_marks(layout, k)[0].spots]
        for i, (ka, a) in enumerate(spots):
            for kb, b in spots[i + 1:]:
                if ka != kb:
                    self.assertGreaterEqual(math.hypot(a[0] - b[0], a[1] - b[1]),
                                            config.QUEST_SPOT_OTHERS)


class HiddenQuestTest(unittest.TestCase):
    def tearDown(self):
        config.QUEST_FOCUS = None

    def test_every_quest_is_out_and_hidden_from_the_start(self):
        m, s = game()
        q = s.quests
        self.assertTrue(set(SWAMP) <= set(q.states))         # (and the other biomes')
        self.assertTrue(all(st.stage == "hunt" and not st.taken for st in q.states.values()))
        self.assertEqual(q.pins(), [])                      # givers and lairs are found
        self.assertEqual([label for label, _, _ in q.log()], ["GLORY"])
        # Hunt quests' targets are out already, without anyone talking.
        for key in ("bad_trip", "leech_doctor"):
            qid = q.states[key].qid
            self.assertTrue(any(k[0] == QUEST_SID and k[1] == qid for k in s.spawner.fixed))

    def test_no_giver_needed(self):
        m, s = game()
        q = s.quests
        st = q.states["bad_trip"]
        toasts = len([e for e in s.effects if e.kind == "toast"])
        frog = Dummy(*st.camp.spots[0])
        frog.spawn_id = (QUEST_SID, st.qid, 0, 0)
        q.on_death(frog, None)
        self.assertEqual(st.found, 1)                       # it counts...
        self.assertEqual(len([e for e in s.effects if e.kind == "toast"]), toasts)  # ...silently
        finish(q, "bad_trip")
        self.assertEqual(st.stage, "awake")
        self.assertIn("STIRS", q.banner.title)
        self.assertEqual(q.banner.sub, "Froggy's Pond is marked on your map")
        self.assertIn((st.lair.cx, st.lair.cy, "lair", st.lair.name), q.pins())
        self.assertEqual([label for label, _, _ in q.log()], ["GLORY"])   # still not taken

    def test_braziers_light_without_the_giver(self):
        m, s = game()
        q = s.quests
        st = q.states["smoke_keeper"]
        s.hero.invulnerable = True
        x, y = st.camp.spots[0]
        teleport(s, x + 1.5, y)
        step(s, round(config.BRAZIER_LIGHT_TIME * 60) + 10)
        self.assertIn(0, st.lit)
        self.assertEqual(st.found, 1)
        self.assertFalse(st.taken)

    def test_the_giver_after_the_fact(self):
        m, s = game()
        q = s.quests
        st = finish(q, "leech_doctor")
        q.talk(st.npc, s.me)                                # the boss is already up
        self.assertEqual(st.npc.line, st.spec.say("done")[0])
        self.assertEqual(q.log()[1], ("SWAMP", "go to The Blood Mire", False))


class GuardianTest(unittest.TestCase):
    def tearDown(self):
        config.QUEST_FOCUS = None

    def _fight_and_win(self, s, key):
        q = s.quests
        st = q.states[key]
        if st.stage == "hunt":
            finish(q, key)
        lair = st.lair
        teleport(s, lair.cx, lair.cy + lair.radii[1] * 0.5)
        step(s)
        self.assertEqual(st.stage, "fight")
        st.boss.hp = 0.0
        st.boss.last_hit_by = s.hero
        for p in getattr(st.boss, "parts", ()):
            p.hp = 0.0
        step(s)
        self.assertEqual(st.stage, "cleared")
        return st

    def test_one_guardian_per_biome(self):
        m, s = game()
        s.hero.invulnerable = True
        q = s.quests
        self._fight_and_win(s, "bad_trip")
        self.assertEqual(q.guardians, 1)
        loot = s.me.stats.loot
        self._fight_and_win(s, "leech_doctor")
        self.assertEqual(q.guardians, 1)                    # the swamp counts once...
        self.assertIn("bonus", q.banner.sub)
        self.assertIn("leech_swarm", m.app.guild.achievements)   # ...the extra still pays
        self.assertGreaterEqual(s.me.stats.loot - loot, config.BOSSES["leech_swarm"].loot)

    def test_two_fights_at_once(self):
        m, s = game()
        s.hero.invulnerable = True
        q = s.quests
        a, b = q.states["bad_trip"], q.states["smoke_keeper"]
        for st in (a, b):
            finish(q, st.key)
            teleport(s, st.lair.cx, st.lair.cy + st.lair.radii[1] * 0.5)
            step(s)
            self.assertEqual(st.stage, "fight")
        self.assertEqual(len(q.fights), 2)
        self.assertEqual(len(q.stream_views()), 2)
        self.assertIs(q.fight_for(s.hero), b)               # the one you're in
        teleport(s, a.lair.cx, a.lair.cy + a.lair.radii[1] * 0.5)
        self.assertIs(q.fight_for(s.hero), a)
        s.draw(m.text)

    def test_dev_keys_follow_the_focus(self):
        m, s = game()
        q = s.quests
        self.assertEqual(q.dev_quest().key, "bad_trip")     # the first not beaten
        config.QUEST_FOCUS = "smoke_keeper"
        self.assertTrue(q.dev_finish_hunt())
        self.assertEqual(q.states["smoke_keeper"].stage, "awake")
        self.assertEqual(q.states["bad_trip"].stage, "hunt")


if __name__ == "__main__":
    unittest.main()
