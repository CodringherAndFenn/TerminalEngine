"""P11 (playtest pass, 2026-10-11): the swamp's new enemies -- bog zombies,
newts, gator hatchlings, mudskippers, bog crocodile, snapping turtle,
heron, swamp hag, lizardman javelineers, marsh lights, bloated corpse,
sludge."""

import math
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.entities.projectile import Projectile
from ascii_adventurers.render.characters import ART
from ascii_adventurers.render import swamp_art  # noqa: F401
from ascii_adventurers.systems import combat
from ascii_adventurers.systems.zones import update_zones
from ascii_adventurers.tests.test_m16 import game
from ascii_adventurers.tests.test_m17 import step
from ascii_adventurers.tests.test_p7 import Arena, enemy
from ascii_adventurers.tests.test_weapons import open_map
from ascii_adventurers.world import tiles

NEW = ("bog_zombie", "newt", "gator_hatchling", "mudskipper", "crocodile", "turtle", "heron",
       "swamp_hag", "lizardman", "marsh_light", "bloated_corpse", "sludge")


def kinds(a, key):
    return [e for e in a.enemies if getattr(e, "kind_key", "") == key]


def run_zones(a, seconds):
    for _ in range(round(seconds * 60)):
        a.run(1 / 60)
        update_zones(a.zones, a.actors(), a.effects, 1 / 60, a.world)


class CatalogTest(unittest.TestCase):
    def test_every_new_enemy_lives_in_the_swamp_and_has_its_page(self):
        for key in NEW:
            spec = config.ENEMIES[key]
            self.assertIn("swamp", spec.biomes, key)
            self.assertIn(key, config.BESTIARY, key)
            sprite = spec.sprite or config.BODIES[spec.body].sprite
            self.assertIn(sprite, ART, key)
            self.assertTrue(all(len(r) == 14 for r in ART[sprite]) and len(ART[sprite]) == 18)

    def test_the_swamp_now_has_fifteen_kinds(self):
        swamp = [k for k, s in config.ENEMIES.items() if "swamp" in s.biomes]
        self.assertEqual(len(swamp), 3 + len(NEW))
        self.assertEqual({k for k in NEW if config.ENEMIES[k].elite}, {"crocodile"})


class ChaserTest(unittest.TestCase):
    def test_simple_chasers_reach_and_bite(self):
        for key in ("bog_zombie", "newt", "gator_hatchling"):
            a = Arena(enemy(key, 24.5, 15.5))
            a.run(5.0)
            self.assertLess(a.hero.hp, a.hero.max_hp, key)

    def test_mudskippers_hop_at_you(self):
        a = Arena(enemy("mudskipper", 24.5, 15.5))
        a.run(5.0)
        self.assertLess(a.hero.hp, a.hero.max_hp)


class BeastTest(unittest.TestCase):
    def test_crocodile_lurks_lunges_clamps_and_drags(self):
        c = enemy("crocodile", 26.5, 15.5)
        a = Arena(c)
        self.assertEqual(c.sprite_now(), "croc_lurk")
        x0 = a.hero.x
        clamped = held = 0
        for _ in range(180):
            a.run(1 / 60)
            if c.state == "clamp":
                clamped += 1
                held += a.hero.petrified > 0                     # held: no walking
        self.assertGreater(clamped, 10)
        self.assertGreaterEqual(held, clamped - 1)               # (from its first bite on)
        self.assertLess(a.hero.hp, a.hero.max_hp)
        self.assertLess(a.hero.x, x0)                           # dragged toward where it came from

    def test_a_roll_breaks_the_crocodiles_hold(self):
        c = enemy("crocodile", 26.5, 15.5)
        a = Arena(c)
        for _ in range(180):
            a.run(1 / 60)
            if c.state == "clamp":
                break
        self.assertEqual(c.state, "clamp")
        a.hero.roll_t = 0.25
        a.run(1 / 60)
        self.assertNotEqual(c.state, "clamp")

    def test_turtle_hides_in_its_shell(self):
        t = enemy("turtle", 20.5, 15.5)
        a = Arena(t, hero_at=(50.5, 15.5))
        t.take_damage(t.max_hp * 0.35, a.hero, 0.0)
        self.assertTrue(t.hiding)
        self.assertEqual(t.sprite_now(), "turtle_shell")
        self.assertEqual(t.take_damage(50, a.hero, 0.0), 0.0)
        a.run(config.TURTLE[1] + 0.1)
        self.assertFalse(t.hiding)
        self.assertGreater(t.take_damage(5, a.hero, 0.0), 0.0)

    def test_heron_stabs_from_range_and_flaps_off(self):
        h = enemy("heron", 27.0, 15.5)
        a = Arena(h)
        a.run(3.0)
        self.assertLess(a.hero.hp, a.hero.max_hp)
        h2 = enemy("heron", 31.5, 15.5)
        b = Arena(h2)
        b.run(0.5)
        self.assertGreater(h2.dist_to(b.hero), 2.0)             # too close: off it went


class FolkTest(unittest.TestCase):
    def test_hag_curse_roots_who_stays_in_it(self):
        hag = enemy("swamp_hag", 21.5, 15.5)
        hag.timer = 0.1
        a = Arena(hag)
        run_zones(a, 0.3)
        curses = [z for z in a.zones if z.kind == "curse"]
        self.assertEqual(len(curses), 1)
        run_zones(a, config.HAG[2])
        self.assertGreater(a.hero.slow_t, 0)
        self.assertEqual(a.hero.slow_mult, 0.0)                  # rooted

    def test_stepping_out_of_the_curse_saves_you(self):
        hag = enemy("swamp_hag", 21.5, 15.5)
        hag.timer = 0.1
        a = Arena(hag)
        run_zones(a, 0.3)
        a.hero.x += 3.0
        run_zones(a, config.HAG[2])
        self.assertEqual(a.hero.slow_t, 0)

    def test_javelins_stick_in_the_ground_then_go(self):
        liz = enemy("lizardman", 10.5, 15.5)
        world = open_map()
        zones = []
        shell = config.WEAPONS["javelin"].shell
        shots = [Projectile(11.5, 15.5, 0.0, shell, owner=liz, damage=9)]
        for _ in range(90):
            combat.update_projectiles(shots, world, [], 1 / 60, [liz], zones)
        self.assertEqual(shots, [])
        stuck = [(x, y) for y in range(30) for x in range(60)
                 if world.tile_at(x, y) is tiles.STUCK_JAVELIN]
        self.assertEqual(len(stuck), 1)
        self.assertTrue(world.tile_at(*stuck[0]).solid)
        for _ in range(round(config.JAVELIN_STUCK * 60) + 2):
            update_zones(zones, [liz], [], 1 / 60, world)
        self.assertIs(world.tile_at(*stuck[0]), tiles.GROUND)    # the ground again

    def test_marsh_lights_one_real_two_illusions(self):
        light = enemy("marsh_light", 22.5, 15.5)
        a = Arena(light)
        a.run(1 / 60)
        fakes = kinds(a, "marsh_light_fake")
        self.assertEqual(len(fakes), config.MARSH_LIGHTS[0] - 1)
        self.assertTrue(light.hittable)
        self.assertFalse(any(f.hittable for f in fakes))
        a.run(3.0)
        self.assertLess(a.hero.hp, a.hero.max_hp)
        light.hp = 0
        a.run(2 / 60)
        self.assertFalse(any(f.alive for f in fakes))           # they go out with it


class RotTest(unittest.TestCase):
    def test_bloated_corpse_bursts_into_a_cloud(self):
        c = enemy("bloated_corpse", 27.5, 15.5)
        a = Arena(c)
        run_zones(a, 3.0)
        self.assertFalse(c.alive)
        self.assertTrue(any(z.kind == "gas" for z in a.zones))
        self.assertLess(a.hero.hp, a.hero.max_hp)

    def test_sludge_splits_twice(self):
        s = enemy("sludge", 20.5, 15.5)
        a = Arena(s, hero_at=(50.5, 15.5))
        s.hp = 0
        a.run(1 / 60)
        mids = kinds(a, "sludge_mid")
        self.assertEqual(len(mids), 2)
        for m in mids:
            m.hp = 0
        a.run(1 / 60)
        smalls = kinds(a, "sludge_small")
        self.assertEqual(len(smalls), 4)
        for sm in smalls:
            sm.hp = 0
        a.run(1 / 60)
        self.assertEqual(len(kinds(a, "sludge_small")), 4)       # the smallest don't split


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
