"""M30.2: Pandemonium's trance, temptation and its first eight revellers
(design/OCEAN.md 14-15)."""

import math
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from types import SimpleNamespace

from ascii_adventurers import config
from ascii_adventurers.ai import KINDS
from ascii_adventurers.ai import pandemonium as pand
from ascii_adventurers.ai.pandemonium import Reveller
from ascii_adventurers.players.controls import PlayerInput
from ascii_adventurers.render import plains  # noqa: F401  (adds the pictures to ART)
from ascii_adventurers.render.characters import ART
from ascii_adventurers.systems import temptation
from ascii_adventurers.systems.zones import Zone, update_zones
from ascii_adventurers.tests.test_p7 import Arena, enemy
from ascii_adventurers.world import tiles
from ascii_adventurers.world.layout import IslandLayout
from ascii_adventurers.world.test_map import TestMap
from ascii_adventurers.world.zones import plan_of

NEW = ("glutton", "drunkard", "toastmaster", "ravenous", "dancer", "masked_dancer",
       "band_drummer", "piper")
TABLE = (30.5, 8.0)            # the test arena's one banquet table (a lure)
BAND = (10.5, 25.5)


def revel_map(w=60, h=30, table=True):
    rows = [["."] * w for _ in range(h)]
    if table:
        for x in range(26, 35):
            rows[7][x] = rows[8][x] = "T"
    m = TestMap(["".join(r) for r in rows], legend={".": tiles.OBSIDIAN, "T": tiles.BANQUET_TABLE})
    m.revel_sites = {("table", 0): (*TABLE, "table"), ("band", 0): (*BAND, "band"),
                     ("table", 1): (50.5, 20.0, "table")}
    m.wine_fountains = [(55.5, 5.0)]
    m.lures = [TABLE, BAND, (55.5, 5.0)]
    return m


def arena(*enemies, hero_at=(30.5, 22.5), tough=True, table=True):
    a = Arena(*enemies, hero_at=hero_at)
    a.world = revel_map(table=table)
    if tough:
        a.hero.hp = a.hero.max_hp = 100000
    return a


def run(a, seconds):
    for _ in range(round(seconds * 60)):
        a.run(1 / 60)
        update_zones(a.zones, a.actors(), a.effects, 1 / 60, a.world)
        a.hero.time += 1 / 60


def reveller(key, x, y, home=("table", 0), state="serene", seed=1):
    e = enemy(key, x, y, seed)
    e.home = home
    e.state = state
    return e


class CatalogTest(unittest.TestCase):
    def test_eight_revellers_each_with_two_looks_and_a_page(self):
        for key in NEW:
            spec = config.ENEMIES[key]
            self.assertEqual(spec.biomes, (), key)          # (residents only, never rolled)
            self.assertIn(spec.kind, KINDS)
            self.assertIn(key, config.BESTIARY)
            for name in (spec.sprite, spec.sprite + "_frenzied"):
                self.assertIn(name, ART, name)
                self.assertEqual(len(ART[name]), 18)
                self.assertTrue(all(len(r) == 14 for r in ART[name]), name)
        self.assertTrue(config.ENEMIES["toastmaster"].elite and config.ENEMIES["piper"].elite)


class ResidentsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lay = IslandLayout(31)
        cls.z = cls.lay.zone("pandemonium")
        cls.p = plan_of(cls.lay, cls.z)
        cls.res = pand.residents(cls.lay, cls.z)

    def test_every_group_has_its_people(self):
        homes = {}
        for _, x, y, home in self.p.revellers:
            homes.setdefault(home, []).append(_)
        lo, hi, every = config.REVEL_TABLE
        hosts = {"cupbearer", "carver", "bouncer", "master_of_revels"}   # (M30.3: posted there)
        for i in range(len(self.p.tables)):
            group = [k for k in homes[("table", i)] if k not in hosts]
            self.assertTrue(lo <= len(group) <= hi, group)
            self.assertTrue(set(group) <= {"glutton", "drunkard", "toastmaster", "ravenous"})
            self.assertEqual("toastmaster" in group, i % every == 0, i)
        for i in range(len(self.p.bandstands)):
            group = homes[("band", i)]
            self.assertEqual(group.count("piper"), 1)
            self.assertEqual(group.count("band_drummer"), config.REVEL_BAND[0])
            self.assertEqual(group.count("dancer"), 2 * config.REVEL_BAND[1])
        self.assertEqual(len([k for k in homes[("banquet", 0)] if k not in hosts]),
                         2 * config.REVEL_BANQUET[0])
        self.assertIn("dancer", homes[("mirrors", 0)])

    def test_they_stand_on_open_ground_and_know_their_homes(self):
        from ascii_adventurers.world.chunked import ChunkedWorld
        w = ChunkedWorld(31)
        for key, x, y in self.res[::7]:
            w.ensure_ready(int(x) - 1, int(y) - 1, int(x) + 1, int(y) + 1)
            self.assertFalse(w.tile_at(math.floor(x), math.floor(y)).solid, (key, x, y))
        key, x, y = self.res[0]
        self.assertEqual(pand.home_of(w, x, y), self.p.revellers[0][3])

    def test_the_spawner_rosters_them_and_none_roam(self):
        from ascii_adventurers.systems.spawner import Spawner
        from ascii_adventurers.world.chunked import ChunkedWorld
        w = ChunkedWorld(31)
        sp = Spawner(w, 31)
        x, y = self.p.tables[0]
        n = config.CHUNK_SIZE
        got = [r[1] for r in sp.roster(x // n, y // n)]
        self.assertTrue(set(got) & {"glutton", "drunkard", "toastmaster", "ravenous"})
        self.assertEqual(config.BIOME_ENEMY_DENSITY.get("pandemonium", 0.0), 0.0)


class TranceTest(unittest.TestCase):
    def test_in_the_trance_they_ignore_a_hero_out_of_reach(self):
        g = reveller("glutton", 28.5, 10.0)
        a = arena(g, hero_at=(30.5, 22.5))
        run(a, 2.0)
        self.assertTrue(g.serene)
        self.assertLess(math.hypot(g.x - 28.5, g.y - 10.0), 0.1)

    def test_coming_close_wakes_the_whole_group_after_a_tell(self):
        group = [reveller("glutton", 28.5, 10.0), reveller("drunkard", 32.5, 10.0),
                 reveller("ravenous", 34.5, 6.0)]
        other = reveller("drunkard", 50.5, 22.0, home=("table", 1))
        a = arena(*group, other, hero_at=(28.5, 15.5))         # (5.5 from the glutton)
        run(a, 0.1)
        self.assertTrue(all(e.unveiling for e in group))
        self.assertTrue(other.serene)                         # (another group sleeps on)
        run(a, config.REVEL[3])
        self.assertTrue(all(e.frenzied for e in group))
        self.assertTrue(pand.frenzied(a.world, ("table", 0)))

    def test_a_hit_wakes_them_and_it_never_ends(self):
        g, d = reveller("glutton", 28.5, 10.0), reveller("drunkard", 32.5, 10.0)
        a = arena(g, d, hero_at=(30.5, 25.5))
        d.take_damage(1, a.hero, 0.0)
        run(a, config.REVEL[3] + 0.2)
        self.assertTrue(g.frenzied and d.frenzied)
        a.hero.x, a.hero.y = 5.5, 28.5                       # (gone far away)
        run(a, 3.0)
        self.assertTrue(g.frenzied)

    def test_killed_in_the_trance_its_group_still_turns(self):
        g, d = reveller("glutton", 28.5, 10.0), reveller("drunkard", 32.5, 10.0)
        a = arena(g, d, hero_at=(30.5, 25.5))
        d.hp = 0.0
        d.on_death(SimpleNamespace(effects=a.effects, world=a.world))
        run(a, config.REVEL[3] + 0.2)
        self.assertTrue(g.frenzied)

    def test_music_halves_the_reach_and_carries_the_frenzy(self):
        w = revel_map()
        self.assertEqual(pand.wake_reach(w, ("band", 0)), config.REVEL[0] * config.REVEL[1])
        self.assertEqual(pand.wake_reach(w, ("table", 0)), config.REVEL[0])
        w.revel_sites[("table", 2)] = (BAND[0] + 10, BAND[1] - 5, "table")
        w.revel_reach = None
        self.assertEqual(sorted(pand.frenzy(w, ("band", 0))), [("band", 0), ("table", 2)])
        self.assertTrue(pand.frenzied(w, ("table", 2)))
        self.assertFalse(pand.frenzied(w, ("table", 0)))      # (too far from the music)

    def test_frenzied_they_drink_at_the_wine_fountains(self):
        g = reveller("glutton", 50.5, 8.0, state="unveiled")
        a = arena(g, hero_at=(5.5, 25.5), table=False)
        g.hp = g.max_hp * 0.3
        run(a, 3.0)
        self.assertLess(math.hypot(g.x - 55.5, g.y - 5.0), config.FONT[2] + 0.5)
        self.assertGreater(g.hp, g.max_hp * 0.3)


class TemptationTest(unittest.TestCase):
    def scene(self, at):
        a = arena(hero_at=at)
        p = SimpleNamespace(hero=a.hero)
        return a, p, SimpleNamespace(world=a.world, effects=a.effects)

    def steps(self, scene, p, seconds, roll=False):
        inp = None
        for _ in range(round(seconds * 60)):
            inp = PlayerInput(0.0, 0.0, None, False, roll=roll)
            temptation.step(scene, p, inp, 1 / 60)
            p.hero.time += 1 / 60
        return inp

    def test_it_fills_near_a_lure_and_entrances(self):
        a, p, scene = self.scene((TABLE[0], TABLE[1] + 2.0))
        full, reach, fill = config.TEMPT[:3]
        self.steps(scene, p, fill * 0.5)
        self.assertGreater(p.hero.temptation, 0.0)
        for _ in range(round(fill * 2 * 60)):
            self.steps(scene, p, 1 / 60)
            if p.hero.entranced > 0:
                break
        self.assertGreater(p.hero.entranced, 0.0)
        inp = self.steps(scene, p, 0.2)
        self.assertLess(inp.move_y, 0.0)                     # (drifting to the table)
        inp = self.steps(scene, p, 1 / 60, roll=True)        # (a roll snaps you out)
        self.assertEqual(p.hero.entranced, 0.0)

    def test_it_drains_away_from_lures_faster_while_fighting(self):
        a, p, scene = self.scene((5.5, 15.5))
        p.hero.temptation = 60.0
        self.steps(scene, p, 0.5)
        calm = 60.0 - p.hero.temptation
        p.hero.temptation = 60.0
        p.hero.struck_at = 1e9                               # (hitting something just now)
        self.steps(scene, p, 0.5)
        self.assertAlmostEqual(60.0 - p.hero.temptation, calm * config.TEMPT[4], delta=1.0)

    def test_nothing_far_from_pandemonium(self):
        a, p, scene = self.scene((5.5, 15.5))
        a.world.lures = []
        self.steps(scene, p, 3.0)
        self.assertEqual(p.hero.temptation, 0.0)


class RevellerTest(unittest.TestCase):
    def test_the_glutton_slams_a_ring_and_gorges_at_a_table(self):
        g = reveller("glutton", 30.5, 12.0, state="unveiled")
        a = arena(g, hero_at=(30.5, 14.5))
        hp = a.hero.hp
        run(a, 1.0 + config.ENEMIES["glutton"].windup + 0.6)    # (its first cooldown, the tell)
        self.assertLess(a.hero.hp, hp)
        self.assertIn("belly_slam", [e.kind for e in a.effects])
        g.hp = g.max_hp * 0.5
        g.x, g.y = 30.5, 10.0                                # (beside the table)
        g.gorge_cd, g.windup, g.cooldown = 0.0, 0.0, 9.0
        before = g.hp
        run(a, config.GLUTTON[5])
        self.assertGreater(g.hp, before)

    def test_a_roll_passes_through_a_ring(self):
        g = reveller("band_drummer", 30.5, 12.0, state="unveiled")
        a = arena(g, hero_at=(30.5, 16.5))
        a.hero.roll_t = 5.0                                  # (mid-roll the whole time)
        hp = a.hero.hp
        run(a, config.BEAT[0] * 2)
        self.assertEqual(a.hero.hp, hp)

    def test_the_drunkards_bottles_leave_wine_that_slows_and_tempts(self):
        d = reveller("drunkard", 30.5, 16.0, state="unveiled")
        a = arena(d, hero_at=(30.5, 21.5), table=False)
        a.world.lures = []
        run(a, 2.5)
        pools = [z for z in a.zones if z.kind == "wine_puddle"]
        self.assertTrue(pools)
        z = pools[0]
        a.hero.x, a.hero.y = z.x, z.y
        before = a.hero.temptation
        run(a, 1.0)
        self.assertGreater(a.hero.temptation, before)
        self.assertLess(a.hero.slow_mult, 1.0)

    def test_a_toast_speeds_up_the_frenzied(self):
        t = reveller("toastmaster", 30.5, 14.0, state="unveiled")
        g = reveller("glutton", 33.5, 14.0, state="unveiled")
        a = arena(t, g, hero_at=(30.5, 22.0))
        t.cooldown = 0.0
        speed = g.speed
        run(a, config.ENEMIES["toastmaster"].windup + 0.1)
        self.assertGreater(g.toasted, 0.0)
        self.assertAlmostEqual(g.speed, speed * config.TOAST[3])

    def test_the_ravenous_latches_on_and_a_roll_throws_it_off(self):
        r = reveller("ravenous", 30.5, 18.0, state="unveiled")
        a = arena(r, hero_at=(30.5, 20.0))
        run(a, 1.0)
        self.assertIs(r.latched, a.hero)
        self.assertLess(a.hero.slow_mult, 1.0)
        a.hero.roll_t = 0.3
        run(a, 0.05)
        self.assertIsNone(r.latched)
        self.assertGreater(r.dazed, 0.0)

    def test_the_dancers_steps_repeat(self):
        d = reveller("dancer", 30.5, 14.0, state="unveiled")
        a = arena(d, hero_at=(30.5, 20.0))
        d.on_unveil(SimpleNamespace())
        seen = []
        for _ in range(int(4 * 60)):
            run(a, 1 / 60)
            if not seen or seen[-1] != d.step:
                seen.append(d.step)
        self.assertGreaterEqual(len(seen), 4)
        self.assertEqual(seen[:4], [0, 1, 2, 3])

    def test_the_masked_dancer_swaps_places(self):
        m = reveller("masked_dancer", 30.5, 14.0, state="unveiled")
        o = reveller("dancer", 40.5, 14.0)
        a = arena(m, o, hero_at=(30.5, 18.0))
        m.cooldown = 0.0
        run(a, 1 / 60)
        self.assertEqual((round(m.x), round(o.x)), (40, 30))
        self.assertIn("mask_swap", [e.kind for e in a.effects])

    def test_the_pipers_song_tempts_and_carries_the_frenzy(self):
        p = reveller("piper", 22.5, 15.0, state="unveiled")
        a = arena(p, hero_at=(28.5, 15.0), table=False)
        a.world.lures = []
        p.song = 0.01
        run(a, 1.5)
        self.assertGreater(a.hero.temptation, 0.0)
        p.spread = 0.0
        run(a, 1 / 60)
        self.assertTrue(any(pand.frenzied(a.world, h) for h in a.world.revel_sites))


class GameTest(unittest.TestCase):
    def test_entranced_heroes_cant_attack_and_the_hud_says_so(self):
        from ascii_adventurers.scenes.game import GameScene
        from ascii_adventurers.tests.test_m16 import game
        m, s = game("wizard", seed=31)
        s.hero.entranced = 1.0
        self.assertEqual(GameScene._meter(s.hero)[0], "TMP")
        self.assertTrue(GameScene._meter(s.hero)[2])
        s.draw(m.text)


if __name__ == "__main__":
    unittest.main()
