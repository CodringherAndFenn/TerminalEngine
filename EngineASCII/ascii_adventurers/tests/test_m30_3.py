"""M30.3: Pandemonium's other eight -- the vain and the greedy, and the demon
hosts (design/OCEAN.md 15)."""

import math
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from types import SimpleNamespace

from ascii_adventurers import config
from ascii_adventurers.ai import KINDS
from ascii_adventurers.ai import pandemonium as pand
from ascii_adventurers.ai.pandemonium import Host
from ascii_adventurers.entities.projectile import Projectile
from ascii_adventurers.render import plains  # noqa: F401  (adds the pictures to ART)
from ascii_adventurers.render.characters import ART
from ascii_adventurers.tests.test_m30_2 import BAND, TABLE, arena, reveller, run
from ascii_adventurers.world.layout import IslandLayout
from ascii_adventurers.world.zones import plan_of

REVELLERS = ("vain", "gilded_reveller", "hoarder", "beloved")
HOSTS = ("cupbearer", "carver", "bouncer", "master_of_revels")


class CatalogTest(unittest.TestCase):
    def test_eight_more_with_their_looks_and_pages(self):
        for key in REVELLERS + HOSTS:
            spec = config.ENEMIES[key]
            self.assertEqual(spec.biomes, (), key)
            self.assertIn(spec.kind, KINDS)
            self.assertIn(key, config.BESTIARY)
            looks = (spec.sprite,) if key in HOSTS else (spec.sprite, spec.sprite + "_frenzied")
            for name in looks:
                self.assertIn(name, ART, name)
                self.assertTrue(all(len(r) == 14 for r in ART[name]), name)
        self.assertIn("gilded_reveller_cracked", ART)
        self.assertTrue(config.ENEMIES["beloved"].elite and config.ENEMIES["master_of_revels"].elite)


class ResidentsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lay = IslandLayout(31)
        cls.z = cls.lay.zone("pandemonium")
        cls.p = plan_of(cls.lay, cls.z)
        pand.residents(cls.lay, cls.z)

    def group(self, home):
        return [k for k, x, y, h in self.p.revellers if h == home]

    def test_the_vain_and_the_greedy_gather_at_the_statues(self):
        vains, gilded, beloved, admirers = config.REVEL_STATUE
        for i in range(len(self.p.statues)):
            g = self.group(("statue", i))
            if i % beloved == 0:
                self.assertEqual(g.count("beloved"), 1)
                self.assertEqual(g.count("vain"), admirers)
            else:
                self.assertEqual((g.count("vain"), g.count("hoarder")), (vains, 1))
            self.assertEqual(g.count("gilded_reveller"), 1 if i % gilded == 0 else 0)
        self.assertIn("beloved", self.group(("mirrors", 0)))

    def test_the_hosts_guard_the_groups(self):
        cup, carve, bounce, master = config.REVEL_HOSTS
        for i in range(len(self.p.tables)):
            g = self.group(("table", i))
            self.assertEqual("cupbearer" in g, i % cup == 0, i)
            self.assertEqual("carver" in g, i % carve == 1, i)
            self.assertEqual("bouncer" in g, i % bounce == 2, i)
        for i in range(len(self.p.bandstands)):
            self.assertEqual("master_of_revels" in self.group(("band", i)), i % master == 0)
        banquet = self.group(("banquet", 0))
        self.assertEqual((banquet.count("bouncer"), banquet.count("carver")), (1, 2))

    def test_they_all_stand_on_open_ground(self):
        from ascii_adventurers.world.chunked import ChunkedWorld
        w = ChunkedWorld(31)
        new = [r for r in self.p.revellers if r[0] in REVELLERS + HOSTS]
        for key, x, y, _ in new:
            w.ensure_ready(int(x) - 1, int(y) - 1, int(x) + 1, int(y) + 1)
            self.assertFalse(w.tile_at(math.floor(x), math.floor(y)).solid, (key, x, y))

    def test_the_statues_are_homes(self):
        from ascii_adventurers.world.chunked import ChunkedWorld
        s = pand.sites(ChunkedWorld(31))
        self.assertEqual(sum(1 for h in s if h[0] == "statue"), len(self.p.statues))


class VainAndGreedyTest(unittest.TestCase):
    def test_the_vains_mirror_dazzles_and_turns_shots_back(self):
        v = reveller("vain", 30.5, 15.0, state="unveiled")
        a = arena(v, hero_at=(30.5, 20.0))
        shot = Projectile(30.5, 18.0, -math.pi / 2, config.PANDEMONIUM_SHOTS["glitter"], owner=a.hero)
        a.projectiles.append(shot)
        v.aim = v.angle_to(a.hero.x, a.hero.y)
        v.flash(SimpleNamespace(players=[a.hero], projectiles=a.projectiles, effects=a.effects,
                                events=[]))
        self.assertGreater(a.hero.dazzled, 0.0)
        self.assertIs(shot.owner, v)
        self.assertGreater(shot.dir_y, 0.0)                  # (back the way it came)
        self.assertIn("mirror_flash", [e.kind for e in a.effects])

    def test_a_vain_with_a_beloved_circles_it_and_shields_it(self):
        b = reveller("beloved", 30.5, 12.0, home=("statue", 0), state="unveiled")
        vs = [reveller("vain", 30.5 + dx, 12.0, home=("statue", 0), state="unveiled", seed=k)
              for k, dx in enumerate((-2.0, 2.0))]
        a = arena(b, *vs, hero_at=(30.5, 24.0))
        a.world.revel_sites[("statue", 0)] = (30.5, 12.0, "statue")
        run(a, 1.0)
        self.assertTrue(all(v.admires is b for v in vs))
        self.assertTrue(all(math.hypot(v.x - b.x, v.y - b.y) < config.BELOVED[5] for v in vs))
        hp, shields = b.hp, sum(v.hp for v in vs)
        b.take_damage(20, a.hero, 0.0)
        self.assertEqual(b.hp, hp)                           # (an admirer took it)
        self.assertLess(sum(v.hp for v in vs), shields)
        self.assertGreater(vs[0].adored, 0.0)                # (its group is faster while it lives)
        for v in vs:
            v.hp = 0.0
        b.take_damage(20, a.hero, 0.0)
        self.assertLess(b.hp, hp)                            # (the ring broken)

    def test_the_gilded_revellers_shell_soaks_hits_then_cracks(self):
        g = reveller("gilded_reveller", 30.5, 12.0)
        a = arena(g, hero_at=(30.5, 25.0))
        self.assertEqual(g.sprite_now(), "gilded_reveller")   # (a statue, to the eye)
        run(a, 0.1)
        shell = g.shell
        g.take_damage(shell * 0.5, a.hero, 0.0)
        self.assertEqual(g.hp, g.max_hp)
        self.assertTrue(g.provoked)
        g.take_damage(shell, a.hero, 0.0)
        run(a, config.REVEL[3] + 0.2)
        self.assertEqual(g.sprite_now(), "gilded_reveller_cracked")
        self.assertIn("gold_crack", [e.kind for e in a.effects])
        g.take_damage(10, a.hero, 0.0)
        self.assertLess(g.hp, g.max_hp)

    def test_the_hoarders_coins_lie_there_and_trip_you(self):
        h = reveller("hoarder", 30.5, 15.0, state="unveiled")
        a = arena(h, hero_at=(30.5, 20.5), table=False)
        a.world.lures = []
        run(a, 2.0)
        coins = [z for z in a.zones if z.kind == "loose_coins"]
        self.assertGreaterEqual(len(coins), config.HOARD[2] - 1)
        a.hero.x, a.hero.y = coins[0].x, coins[0].y
        run(a, 0.3)
        self.assertLessEqual(a.hero.slow_mult, config.HOARD[7])


class HostsTest(unittest.TestCase):
    def test_hosts_are_never_in_the_trance(self):
        for key in HOSTS:
            e = reveller(key, 30.5, 12.0)
            e.state = "unveiled"
            self.assertIsInstance(e, Host)
        from ascii_adventurers.tests.test_p7 import enemy
        self.assertTrue(enemy("bouncer", 1, 1).unveiled)
        self.assertEqual(enemy("carver", 1, 1).sprite_now(), "carver")

    def test_the_cupbearer_refills_a_hurt_reveller(self):
        from ascii_adventurers.tests.test_p7 import enemy
        c = enemy("cupbearer", 30.5, 12.0)
        g = reveller("glutton", 33.5, 12.0, state="unveiled")
        a = arena(c, g, hero_at=(5.5, 28.0), table=False)
        g.hp = g.max_hp * 0.4
        g.drinks = False
        run(a, 2.0)
        self.assertGreater(g.hp, g.max_hp * 0.4 + g.max_hp * config.CUPBEARER[3] * 0.8)

    def test_the_carvers_cleaver_flies_out_and_comes_back(self):
        from ascii_adventurers.tests.test_p7 import enemy
        c = enemy("carver", 30.5, 12.0)
        a = arena(c, hero_at=(30.5, 19.0))
        c.cooldown = 0.0
        run(a, 0.1)
        self.assertEqual(len(c.cleavers), 1)
        run(a, config.CARVER[3] + 1.5)
        self.assertEqual(c.cleavers, [])                     # (back in its hand)

    def test_the_bouncer_throws_you_at_the_feast(self):
        from ascii_adventurers.tests.test_p7 import enemy
        b = enemy("bouncer", 30.5, 18.0)
        a = arena(b, hero_at=(30.5, 22.0))
        hp = a.hero.hp
        run(a, 2.5)
        self.assertLess(a.hero.hp, hp)
        self.assertLess(a.hero.y, 22.0)                      # (thrown toward the table, north)

    def test_the_bell_wakes_the_groups_and_snaps_you_out(self):
        from ascii_adventurers.tests.test_p7 import enemy
        m = enemy("master_of_revels", 20.5, 15.0)
        a = arena(m, hero_at=(28.5, 15.0))
        a.hero.entranced, a.hero.temptation = 1.5, 40.0
        run(a, config.ENEMIES["master_of_revels"].windup + 0.3)
        self.assertTrue(pand.frenzied(a.world, ("table", 0)))
        self.assertTrue(pand.frenzied(a.world, ("band", 0)))
        self.assertEqual(a.hero.entranced, 0.0)
        self.assertIn("bell", [e.kind for e in a.effects])

    def test_fireworks_are_marked_then_burst(self):
        from ascii_adventurers.tests.test_p7 import enemy
        m = enemy("master_of_revels", 20.5, 15.0)
        a = arena(m, hero_at=(28.5, 15.0))
        m.bell, m.cooldown = 99.0, 0.0
        run(a, 0.1)
        self.assertEqual(len(m.marks), config.MASTER[4])
        hp = a.hero.hp
        run(a, config.MASTER[6] + 0.2)
        self.assertEqual(m.marks, [])                       # (all burst)
        self.assertLess(a.hero.hp, hp)                       # (one fell right on you)
        self.assertIn("fireworks", [e.kind for e in a.effects])


class DazzleTest(unittest.TestCase):
    def test_dazzled_aim_wavers_and_the_totem_clears_it(self):
        from ascii_adventurers.systems.spells import _cleanse
        from ascii_adventurers.tests.test_m16 import game
        m, s = game("wizard", seed=31)
        s.hero.dazzled = 1.0
        s.hero.aim_angle = 0.0
        s._step(1 / 60)
        self.assertNotEqual(s.hero.aim_angle, 0.0)
        self.assertLess(s.hero.dazzled, 1.0)
        _cleanse(s.hero, s.effects)
        self.assertEqual(s.hero.dazzled, 0.0)
        s.draw(m.text)


if __name__ == "__main__":
    unittest.main()
