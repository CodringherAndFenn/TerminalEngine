"""M29.3: Paradise's other eight enemies (design/OCEAN.md 4): the heralds
(trumpeter, censer-bearer, bowl-bearer, chorister) and the saints and
beasts (weeping saint, martyr, behemoth, leviathan); the residents."""

import math
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.ai import KINDS
from ascii_adventurers.ai.paradise import Angel, _Line, residents
from ascii_adventurers.render.characters import ART
from ascii_adventurers.systems.spawner import RESIDENT_ID, Spawner
from ascii_adventurers.tests.test_m29_2 import _ctx, arena, run, stained, unveiled
from ascii_adventurers.tests.test_p7 import enemy
from ascii_adventurers.world import tiles
from ascii_adventurers.world.chunked import ChunkedWorld
from ascii_adventurers.world.paradise import plan_of

NEW = ("trumpeter", "censer_bearer", "bowl_bearer", "chorister", "weeping_saint", "martyr",
       "behemoth", "leviathan")
RIVER = [(2.0, 22.0), (30.0, 20.0), (58.0, 22.0)]


def until(a, done, limit=5.0):
    """Step the arena until done() (at most `limit` s)."""
    for _ in range(round(limit * 60)):
        if done():
            return True
        run(a, 1 / 60)
    return done()


class CatalogTest(unittest.TestCase):
    def test_eight_more_each_with_two_looks_and_a_page(self):
        for key in NEW:
            spec = config.ENEMIES[key]
            self.assertIn(spec.kind, KINDS)
            self.assertIn(key, config.BESTIARY)
            for name in (spec.sprite, spec.sprite + "_unveiled"):
                self.assertIn(name, ART, name)
                self.assertEqual(len(ART[name]), 18)
                self.assertTrue(all(len(r) == 14 for r in ART[name]), name)
        self.assertEqual({k for k in NEW if config.ENEMIES[k].elite},
                         {"trumpeter", "behemoth", "leviathan"})

    def test_paradise_has_all_sixteen(self):
        rolled = {k for k, s in config.ENEMIES.items() if "paradise" in s.biomes}
        self.assertEqual(len(rolled), 14)
        self.assertEqual(config.ENEMIES["chorister"].biomes, ())     # (residents only)
        self.assertEqual(config.ENEMIES["leviathan"].biomes, ())
        self.assertEqual(len(rolled | {"chorister", "leviathan"}), 16)


class HeraldsTest(unittest.TestCase):
    def test_the_trumpeter_serene_pushes_without_hurting(self):
        e = enemy("trumpeter", 22.5, 15.5)
        a = arena(e, hero_at=(27.0, 15.5))
        e.cooldown, e.state = 0.0, "serene"
        e.unveil = lambda: None                               # (stay serene for this)
        x = a.hero.x
        run(a, 0.2)
        self.assertGreater(a.hero.x, x + 0.5)
        self.assertEqual(a.hero.hp, a.hero.max_hp)

    def test_the_trumpeters_plague_is_marked_then_falls(self):
        e = unveiled("trumpeter", 20.5, 15.5)
        a = arena(e, hero_at=(29.5, 15.5))
        e.cooldown = 0.0
        self.assertTrue(until(a, lambda: e.plague is not None))
        px, py = e.plague[:2]
        self.assertEqual(a.hero.hp, a.hero.max_hp)            # (only marked so far)
        run(a, config.TRUMPET[5] + config.TRUMPET[7] + 0.2)
        self.assertIsNone(e.plague)
        self.assertTrue(any(z.kind == "trail" and z.inflicts == "burn" for z in a.zones))
        self.assertGreater(stained(a.world), 0)
        self.assertTrue(all(math.hypot(z.x - px, z.y - py) <= config.TRUMPET[4] + 0.01
                            for z in a.zones if z.kind == "trail"))

    def test_the_censer_serene_is_harmless_unveiled_its_coals_burn(self):
        e = enemy("censer_bearer", 18.5, 15.5)
        a = arena(e, hero_at=(30.5, 15.5))
        run(a, 2.0)
        self.assertTrue(e.serene)
        self.assertTrue(any(z.kind == "incense" for z in a.zones))
        self.assertEqual(a.hero.hp, a.hero.max_hp)
        e.state, e.cooldown = "unveiled", 0.0
        a.hero.x = 26.5
        self.assertTrue(until(a, lambda: e.lobs))
        self.assertEqual(len(e.lobs), config.CENSER[2])
        run(a, config.CENSER[3] + 0.1)
        self.assertTrue(any(z.kind == "trail" and z.inflicts == "burn" for z in a.zones))
        self.assertLess(a.hero.hp, a.hero.max_hp)

    def test_the_bowl_pours_where_you_stood(self):
        e = unveiled("bowl_bearer", 22.5, 15.5)
        a = arena(e, hero_at=(27.5, 15.5))
        e.cooldown = 0.0
        self.assertTrue(until(a, lambda: e.mark is not None))
        self.assertEqual(e.mark, (a.hero.x, a.hero.y))
        run(a, config.ENEMIES["bowl_bearer"].windup)
        pool = next(z for z in a.zones if z.kind == "blood_pool")
        self.assertEqual((pool.x, pool.y), (27.5, 15.5))
        self.assertEqual(pool.slow, config.BOWL[4])
        r0 = pool.radius
        run(a, 2.0)
        self.assertGreater(pool.radius, r0)
        self.assertLess(a.hero.hp, a.hero.max_hp)
        self.assertGreater(stained(a.world), 3)

    def test_the_choristers_hymn_heals_angels(self):
        c = enemy("chorister", 10.5, 15.5)
        hurt = enemy("watcher", 13.5, 15.5)
        hurt.state = "unveiled"
        hurt.hp = hurt.max_hp * 0.5
        a = arena(c, hurt, hero_at=(55.5, 5.5))
        a.hero.hp = 500
        c.hp = c.max_hp * 0.8
        hp = hurt.hp
        run(a, 2.0)
        self.assertGreater(hurt.hp, hp)
        self.assertAlmostEqual(c.hp, c.max_hp * 0.8)          # (not itself)
        self.assertEqual(a.hero.hp, 500)

    def test_the_chorister_unveiled_shrieks_in_rings(self):
        c = unveiled("chorister", 20.5, 15.5)
        a = arena(c, hero_at=(26.5, 15.5))
        c.cooldown = 0.0
        run(a, config.ENEMIES["chorister"].windup + config.CHORISTER[5] * 2 + 0.1)
        shrieks = [p for p in a.projectiles if p.spec.look == "shriek"]
        self.assertGreaterEqual(len(shrieks), config.CHORISTER[4] * 2)


class SaintsAndBeastsTest(unittest.TestCase):
    def test_the_weeping_saint_kneels_then_lobs_tears_that_pool(self):
        e = enemy("weeping_saint", 18.5, 15.5)
        a = arena(e, hero_at=(30.5, 15.5))
        run(a, 2.0)
        self.assertEqual((e.x, e.y), (18.5, 15.5))
        self.assertEqual(a.hero.hp, a.hero.max_hp)
        e.state, e.cooldown = "unveiled", 0.0
        self.assertTrue(until(a, lambda: e.lobs))
        self.assertEqual(len(e.lobs), config.SAINT[1])
        run(a, config.SAINT[2] + 0.1)
        pools = [z for z in a.zones if z.kind == "blood_pool"]
        self.assertEqual(len(pools), config.SAINT[1])
        self.assertEqual(pools[0].slow, config.SAINT[6])

    def test_shooting_the_martyr_feeds_it_arrows(self):
        e = enemy("martyr", 20.5, 15.5)
        a = arena(e, hero_at=(40.5, 15.5))
        n = e.arrows
        e.take_damage(1, a.hero, 0.0)
        self.assertEqual(e.arrows, n + 1)
        for _ in range(30):
            e.take_damage(0.01, a.hero, 0.0)
        self.assertEqual(e.arrows, config.MARTYR[1])

    def test_the_martyr_throws_them_back(self):
        e = unveiled("martyr", 20.5, 15.5)
        a = arena(e, hero_at=(27.5, 15.5))
        e.cooldown, e.arrows = 0.0, 7
        self.assertTrue(until(a, lambda: e.windup > 0))
        run(a, config.ENEMIES["martyr"].windup + 0.02)
        thrown = [p for p in a.projectiles if p.spec.look == "arrow"]
        self.assertEqual(len(thrown), config.MARTYR[2])
        self.assertEqual(e.arrows, 2)
        e.arrows = 0
        a.projectiles.clear()
        run(a, 3.0)
        self.assertFalse(any(p.spec.look == "arrow" for p in a.projectiles))

    def test_the_behemoths_bone_plates_guard_its_front(self):
        e = unveiled("behemoth", 20.5, 15.5)
        e.facing = 0.0
        hp = e.hp
        e.take_damage(100, None, math.pi)                     # (flying west: hits its front)
        front = hp - e.hp
        hp = e.hp
        e.take_damage(100, None, 0.0)                         # (from behind)
        back = hp - e.hp
        self.assertAlmostEqual(front, back * config.BEHEMOTH[5])

    def test_the_behemoth_tramples_columns_and_a_wall_dazes_it(self):
        e = unveiled("behemoth", 15.5, 15.5)
        a = arena(e, hero_at=(45.5, 15.5), walls=[(22, 14), (22, 15), (22, 16), (22, 17)])
        e.facing = 0.0
        e.charging, e.timer, e.ran, e.passes = "charge", 0.0, 0.0, 0
        run(a, 0.8)
        self.assertIs(a.world.tile_at(22, 15), tiles.MARBLE_RUBBLE)
        b = arena(unveiled("behemoth", 15.5, 15.5), hero_at=(45.5, 15.5))
        e2 = b.enemies[0]
        for y in range(10, 22):
            b.world.set_tile(22, y, tiles.PEARL_WALL)
        e2.facing = 0.0
        e2.charging, e2.timer, e2.ran, e2.passes = "charge", 0.0, 0.0, 0
        for _ in range(60):
            run(b, 1 / 60)
            if e2.charging == "dazed":
                break
        self.assertEqual(e2.charging, "dazed")

    def test_the_leviathan_keeps_to_the_river_surges_and_spits(self):
        e = enemy("leviathan", 14.0, 21.0)
        a = arena(e, hero_at=(30.5, 15.5))
        a.world.rivers = [RIVER]
        line = _Line(RIVER)
        e.state, e.cooldown = "unveiled", 0.0
        for _ in range(240):
            run(a, 1 / 60)
            self.assertLess(line.project(e.x, e.y)[1], 1e-6)  # (always on the line)
        self.assertLess(abs(e.x - 30.5), 3.0)                 # (it surged to your stretch)
        self.assertTrue(any(p.spec.look == "blood" for p in a.projectiles))
        e.hp = e.max_hp * 0.2
        a.world.fonts = [(e.x, e.y - 3)]
        run(a, 0.5)
        self.assertIsNone(e.font)                              # (it never leaves to drink)

    def test_the_serene_leviathan_swims_near_home(self):
        e = enemy("leviathan", 30.0, 20.0)
        a = arena(e, hero_at=(55.5, 3.5))
        a.world.rivers = [RIVER]
        xs = []
        for _ in range(600):
            run(a, 1 / 60)
            xs.append(e.x)
        self.assertTrue(e.serene)
        self.assertGreater(max(xs) - min(xs), 5.0)
        self.assertLess(max(abs(x - 30.0) for x in xs), config.LEVIATHAN[2] + 1.0)


class ResidentsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = ChunkedWorld(31)
        cls.z = cls.w.layout.zone("paradise")
        cls.p = plan_of(cls.w.layout, cls.z)

    def test_choristers_at_every_choir_ring_and_leviathans_in_the_river(self):
        got = residents(self.w.layout, self.z)
        singers = [(x, y) for k, x, y in got if k == "chorister"]
        self.assertEqual(len(singers), config.CHORISTER[2] * len(self.p.choirs))
        for qx, qy in self.p.choirs:
            near = [s for s in singers if math.hypot(s[0] - qx - 0.5, s[1] - qy - 0.5) < 5]
            self.assertEqual(len(near), config.CHORISTER[2])
        levs = [(x, y) for k, x, y in got if k == "leviathan"]
        self.assertEqual(len(levs), config.LEVIATHAN[0])
        for x, y in levs:
            self.w.ensure_ready(int(x) - 2, int(y) - 2, int(x) + 2, int(y) + 2)
            self.assertIn(self.w.tile_at(math.floor(x), math.floor(y)),
                          (tiles.BLOOD_RIVER, tiles.MARBLE_BRIDGE))

    def test_the_spawner_rosters_them_with_their_chunks(self):
        s = Spawner(self.w, 31)
        n = config.CHUNK_SIZE
        qx, qy = self.p.choirs[0]
        found = []
        for cy in range((qy - 6) // n, (qy + 6) // n + 1):
            for cx in range((qx - 6) // n, (qx + 6) // n + 1):
                found += [(sid, key) for sid, key, x, y in s.roster(cx, cy) if key == "chorister"
                          and math.hypot(x - qx, y - qy) < 6]
        self.assertEqual(len(found), config.CHORISTER[2])
        self.assertTrue(all(sid[2] >= RESIDENT_ID for sid, _ in found))
        self.assertEqual(found, [(sid, key) for sid, key in found])   # (the same every time)
        again = []
        for cy in range((qy - 6) // n, (qy + 6) // n + 1):
            for cx in range((qx - 6) // n, (qx + 6) // n + 1):
                again += [(sid, key) for sid, key, x, y in Spawner(self.w, 31).roster(cx, cy)
                          if key == "chorister" and math.hypot(x - qx, y - qy) < 6]
        self.assertEqual(found, again)


class GameTest(unittest.TestCase):
    def test_they_draw_in_every_state(self):
        from ascii_adventurers.tests.test_m16 import game
        m, s = game("wizard", seed=31)
        s.app.dev = True
        s._dev_zone()
        s.quests.banner = None
        h = s.hero
        out = []
        for k, key in enumerate(NEW):
            e = s.spawner.wake(key, h.x + 3 + (k % 4) * 3, h.y - 4 + (k // 4) * 6,
                               rng=random.Random(k))
            out.append(e)
        s.enemies += out
        s.draw(m.text)
        for e in out:
            e.unveil()
            e.timer = 0.2
        s.draw(m.text)
        for e in out:
            e.state = "unveiled"
            e.lob(h.x, h.y, 0.8, "coal")
        out[0].plague = [h.x, h.y, 0.5, 3, 0.0]
        out[2].mark, out[2].windup = (h.x, h.y), 0.3
        s.draw(m.text)
        for _ in range(60):
            s._step(1 / 60)
        s.draw(m.text)
        self.assertTrue(all(isinstance(e, Angel) for e in out))


if __name__ == "__main__":
    unittest.main()
