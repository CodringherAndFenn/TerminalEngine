"""P12 (playtest pass, 2026-10-11): the mushroom biome's new enemies --
sporelings, fungus gnats, shroomlings, mold zombies, myconid shaman,
cordyceps hunter, fungal brute, rootweaver, giant snail, pillbug, mantis,
fairy ring, mold core."""

import math
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.render.characters import ART
from ascii_adventurers.render import mushroom_art  # noqa: F401
from ascii_adventurers.systems.zones import update_zones
from ascii_adventurers.tests.test_m16 import game
from ascii_adventurers.tests.test_m17 import step
from ascii_adventurers.tests.test_p7 import Arena, enemy

NEW = ("sporeling", "fungus_gnat", "shroomling", "mold_zombie", "myconid", "cordyceps",
       "fungal_brute", "rootweaver", "giant_snail", "pillbug", "mantis", "fairy_ring",
       "mold_core")


def kinds(a, key):
    return [e for e in a.enemies if getattr(e, "kind_key", "") == key]


def run_zones(a, seconds):
    for _ in range(round(seconds * 60)):
        a.run(1 / 60)
        update_zones(a.zones, a.actors(), a.effects, 1 / 60, a.world)


class CatalogTest(unittest.TestCase):
    def test_every_new_enemy_lives_in_the_mushroom_biome_and_has_its_page(self):
        for key in NEW:
            spec = config.ENEMIES[key]
            self.assertIn("mushroom", spec.biomes, key)
            self.assertIn(key, config.BESTIARY, key)
            sprite = spec.sprite or config.BODIES[spec.body].sprite
            self.assertIn(sprite, ART, key)
            self.assertTrue(all(len(r) == 14 for r in ART[sprite]) and len(ART[sprite]) == 18)

    def test_the_mushroom_biome_now_has_sixteen_kinds(self):
        shrooms = [k for k, s in config.ENEMIES.items() if "mushroom" in s.biomes]
        self.assertEqual(len(shrooms), 3 + len(NEW))
        self.assertEqual({k for k in NEW if config.ENEMIES[k].elite}, {"fungal_brute", "mantis"})

    def test_no_red_caps(self):
        # (red caps with white spots are kept for the Mycelium bosses): no
        # sprite's top three drawn rows -- where a cap would be -- use red.
        for name, rows in mushroom_art.MUSHROOM_ART.items():
            drawn = [r for r in rows if r.strip(".")]
            self.assertFalse(any(c in "rR" for r in drawn[:3] for c in r), name)


class ChaserTest(unittest.TestCase):
    def test_simple_chasers_reach_and_bite(self):
        for key in ("sporeling", "fungus_gnat", "shroomling", "mold_zombie"):
            a = Arena(enemy(key, 24.5, 15.5))
            a.run(5.0)
            self.assertLess(a.hero.hp, a.hero.max_hp, key)


class FolkTest(unittest.TestCase):
    def test_myconid_pollen_heals_enemies_not_heroes(self):
        m = enemy("myconid", 10.5, 15.5)
        hurt = enemy("mold_zombie", 13.5, 15.5)
        hurt.hp = 10
        hurt.alert = False
        a = Arena(m, hurt, hero_at=(50.5, 15.5))
        a.hero.hp = 50
        m.timer = 0.1
        run_zones(a, 1.0)
        self.assertTrue(any(z.kind == "pollen" for z in a.zones))
        self.assertGreater(hurt.hp, 10)
        self.assertEqual(a.hero.hp, 50)

    def test_cordyceps_hunter_bursts_into_sporelings(self):
        c = enemy("cordyceps", 20.5, 15.5)
        a = Arena(c, hero_at=(50.5, 15.5))
        c.hp = 0
        a.run(1 / 60)
        self.assertEqual(len(kinds(a, "sporeling")), 2)

    def test_fungal_brute_regrows_unless_you_keep_hitting(self):
        b = enemy("fungal_brute", 10.5, 15.5)
        a = Arena(b, hero_at=(50.5, 15.5))
        b.take_damage(100, a.hero, 0.0)
        hp = b.hp
        a.run(config.REGROW[0] - 0.5)
        self.assertEqual(b.hp, hp)                         # (hit recently: not yet)
        a.run(2.0)
        self.assertGreater(b.hp, hp)

    def test_rootweaver_roots_run_at_you_and_burst(self):
        r = enemy("rootweaver", 21.5, 15.5)
        r.timer = 0.1
        a = Arena(r)
        cracked = False
        for _ in range(240):
            a.run(1 / 60)
            cracked = cracked or bool(r.roots)
        self.assertTrue(cracked)
        self.assertLess(a.hero.hp, a.hero.max_hp)


class CritterTest(unittest.TestCase):
    def test_snail_shell_and_slime(self):
        s = enemy("giant_snail", 20.5, 15.5)
        s.facing = 0.0
        self.assertAlmostEqual(s.take_damage(40, None, 0.0), 40 * config.SNAIL[0])   # from behind
        self.assertAlmostEqual(s.take_damage(40, None, math.pi), 40)                 # its face
        s2 = enemy("giant_snail", 20.5, 15.5)
        a = Arena(s2)
        run_zones(a, 2.0)
        slime = [z for z in a.zones if z.kind == "slime"]
        self.assertTrue(slime)
        a.hero.x, a.hero.y = slime[0].x, slime[0].y
        update_zones(a.zones, a.actors(), a.effects, 0.2, a.world)
        self.assertAlmostEqual(a.hero.slow_mult, config.SNAIL[2])

    def test_pillbug_rolls_hard_to_hurt_then_rests(self):
        p = enemy("pillbug", 22.5, 15.5)
        p.timer = 0.1
        a = Arena(p)
        states = set()
        for _ in range(360):
            a.run(1 / 60)
            states.add(p.state)
            if p.state == "roll":
                self.assertAlmostEqual(p.take_damage(10, None, 0.0), 10 * config.PILLBUG[3])
                p.hp = p.max_hp
        self.assertTrue({"rest", "curl", "roll"} <= states)
        self.assertLess(a.hero.hp, a.hero.max_hp)

    def test_mantis_leaps_then_x_slashes(self):
        m = enemy("mantis", 23.5, 15.5)
        a = Arena(m)
        states = set()
        for _ in range(240):
            a.run(1 / 60)
            states.add(m.state)
        self.assertTrue({"crouch", "leap", "scythes", "slash"} <= states)
        self.assertLess(a.hero.hp, a.hero.max_hp)


class GrowthTest(unittest.TestCase):
    def test_fairy_ring_raises_sporelings_until_three_caps_break(self):
        r = enemy("fairy_ring", 30.5, 15.5)
        a = Arena(r)
        a.hero.invulnerable = True
        a.run(config.FAIRY[3] + 1.5)
        caps = kinds(a, "fairy_cap")
        self.assertEqual(len(caps), config.FAIRY[0])
        self.assertTrue(kinds(a, "sporeling"))
        self.assertFalse(r.hittable)                       # (its caps are what you break)
        for c in caps[:config.FAIRY[2]]:
            c.hp = 0
            c.last_hit_by = a.hero
        a.run(2 / 60)
        self.assertFalse(r.alive)
        self.assertIs(r.last_hit_by, a.hero)               # (the kill counts)
        self.assertFalse(any(c.alive for c in caps))

    def test_mold_core_patches_hurt_and_wither_with_it(self):
        m = enemy("mold_core", 30.5, 15.5)
        a = Arena(m, hero_at=(50.5, 15.5))
        run_zones(a, config.MOLD[0] * 2 + 0.2)
        patches = [z for z in a.zones if z.kind == "mold"]
        self.assertGreaterEqual(len(patches), 2)
        a.hero.x, a.hero.y = patches[0].x, patches[0].y
        hp = a.hero.hp
        update_zones(a.zones, a.actors(), a.effects, 1.0, a.world)
        self.assertLess(a.hero.hp, hp)
        m.hp = 0
        a.run(1 / 60)
        update_zones(a.zones, a.actors(), a.effects, 1 / 60, a.world)
        self.assertFalse(any(z.kind == "mold" for z in a.zones))


class GameTest(unittest.TestCase):
    def test_all_of_them_in_a_real_game(self):
        m, s = game("wizard")
        h = s.hero
        h.invulnerable = True
        for i, k in enumerate(NEW):
            a = i * math.tau / len(NEW)
            e = s.spawner.wake(k, h.x + math.cos(a) * 9, h.y + math.sin(a) * 6, None,
                               random.Random(i))
            e.alert = True
            s.enemies.append(e)
        for f in range(300):
            step(s)
            if f % 60 == 0:
                s.draw(m.text)
        self.assertTrue(any(getattr(e, "kind_key", "") in NEW for e in s.enemies))


if __name__ == "__main__":
    unittest.main()
