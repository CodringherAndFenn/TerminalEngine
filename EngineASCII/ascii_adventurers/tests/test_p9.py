"""P9 (playtest pass, 2026-10-11): the desert's new enemies -- fire ants,
dried husks, sand imps, desert jackals, giant scorpion, vultures, basilisk,
rattlesnake, mummy, fire dancer, glass mage, dune raider, tumbleweed,
cactus golem, djinn lamp. Also: burning patches hurt heroes (a P7 fix)."""

import math
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.entities.projectile import Projectile
from ascii_adventurers.render.characters import ART
from ascii_adventurers.render import desert_art  # noqa: F401
from ascii_adventurers.systems import combat
from ascii_adventurers.systems.zones import update_zones
from ascii_adventurers.tests.test_m16 import game
from ascii_adventurers.tests.test_m17 import step
from ascii_adventurers.tests.test_p7 import Arena, enemy
from ascii_adventurers.tests.test_weapons import hero, open_map

NEW = ("fire_ant", "husk", "sand_imp", "jackal", "scorpion", "vulture", "basilisk",
       "rattlesnake", "mummy", "fire_dancer", "glass_mage", "dune_raider", "tumbleweed",
       "cactus_golem", "djinn_lamp")


def run_zones(a, seconds):
    for _ in range(round(seconds * 60)):
        a.run(1 / 60)
        update_zones(a.zones, a.actors(), a.effects, 1 / 60)


class CatalogTest(unittest.TestCase):
    def test_every_new_enemy_lives_in_the_desert_and_has_its_page(self):
        for key in NEW:
            spec = config.ENEMIES[key]
            self.assertIn("desert", spec.biomes, key)
            self.assertIn(key, config.BESTIARY, key)
            sprite = spec.sprite or config.BODIES[spec.body].sprite
            self.assertIn(sprite, ART, key)
            self.assertTrue(all(len(r) == 14 for r in ART[sprite]) and len(ART[sprite]) == 18)

    def test_the_desert_now_has_twenty_kinds(self):
        desert = [k for k, s in config.ENEMIES.items() if "desert" in s.biomes]
        self.assertEqual(len(desert), 5 + len(NEW))
        self.assertEqual({k for k in NEW if config.ENEMIES[k].elite}, {"scorpion", "mummy"})


class ChaserTest(unittest.TestCase):
    def test_simple_chasers_reach_and_bite(self):
        for key in ("fire_ant", "husk", "sand_imp", "jackal"):
            a = Arena(enemy(key, 24.5, 15.5))
            a.run(5.0)
            self.assertLess(a.hero.hp, a.hero.max_hp, key)

    def test_sand_imps_hop(self):
        imp = enemy("sand_imp", 10.5, 15.5)
        a = Arena(imp, hero_at=(22.5, 15.5), w=80)       # (in sight, a way off)
        still = moving = 0
        for _ in range(60):
            a.run(1 / 60)
            if imp.moving:
                moving += 1
            else:
                still += 1
        self.assertGreater(still, 15)
        self.assertGreater(moving, 15)


class BeastTest(unittest.TestCase):
    def test_scorpion_is_armoured_in_front(self):
        s = enemy("scorpion", 20.5, 15.5)
        s.facing = 0.0
        front = s.take_damage(40, None, math.pi)          # flying -x: hits its front
        back = s.take_damage(40, None, 0.0)
        self.assertAlmostEqual(front, 40 * config.SCORPION[0])
        self.assertAlmostEqual(back, 40)

    def test_scorpion_snaps_then_stabs(self):
        s = enemy("scorpion", 28.5, 15.5)
        a = Arena(s)
        tailed = False
        for _ in range(240):
            a.run(1 / 60)
            tailed = tailed or s.tail > 0
        self.assertTrue(tailed)
        self.assertLess(a.hero.hp, a.hero.max_hp)

    def test_vultures_wait_until_you_are_hurt(self):
        v = enemy("vulture", 22.5, 15.5)
        v.timer = 0.1
        a = Arena(v)
        states = set()
        for _ in range(240):
            a.run(1 / 60)
            states.add(v.state)
        self.assertEqual(states, {"circle"})              # healthy: it only circles
        a.hero.hp = a.hero.max_hp * 0.4
        for _ in range(400):
            a.run(1 / 60)
            states.add(v.state)
        self.assertIn("dive", states)

    def test_basilisk_turns_you_to_stone(self):
        b = enemy("basilisk", 24.5, 15.5)
        b.gaze_t = 0.1
        a = Arena(b)
        stoned = False
        for _ in range(120):
            a.run(1 / 60)
            stoned = stoned or a.hero.petrified > 0
        self.assertTrue(stoned)
        x = a.hero.x
        a.hero.petrify(1.0)
        a.hero.move(1.0, 0.0, 1 / 60, a.world)
        self.assertEqual(a.hero.x, x)                     # can't move

    def test_rattlesnake_strikes_when_close_and_slithers_off(self):
        r = enemy("rattlesnake", 27.5, 15.5)
        a = Arena(r)
        states = set()
        for _ in range(240):
            a.run(1 / 60)
            states.add(r.state)
        self.assertTrue({"rattle", "strike", "away"} <= states)
        self.assertLess(a.hero.hp, a.hero.max_hp)

    def test_rattlesnake_leaves_you_alone_at_range(self):
        r = enemy("rattlesnake", 20.5, 15.5)
        a = Arena(r)
        a.run(3.0)
        self.assertEqual(r.state, "coiled")


class FolkTest(unittest.TestCase):
    def test_mummy_drags_you_in_and_hits(self):
        m = enemy("mummy", 25.0, 15.5)
        a = Arena(m)
        d0 = m.dist_to(a.hero)
        pulled = False
        for _ in range(300):
            a.run(1 / 60)
            pulled = pulled or m.pulling is not None
        self.assertTrue(pulled)
        self.assertLess(a.hero.hp, a.hero.max_hp)
        self.assertLess(m.dist_to(a.hero), d0)

    def test_a_roll_breaks_the_mummys_hold(self):
        m = enemy("mummy", 25.0, 15.5)
        a = Arena(m)
        for _ in range(300):
            a.run(1 / 60)
            if m.pulling is not None:
                break
        self.assertIsNotNone(m.pulling)
        a.hero.roll_t = 0.25                              # rolling
        a.run(1 / 60)
        self.assertIsNone(m.pulling)

    def test_fire_dancer_leaves_fire_and_breathes_flame(self):
        f = enemy("fire_dancer", 15.5, 15.5)
        a = Arena(f)
        run_zones(a, 4.0)
        self.assertTrue(any(e.kind == "flames" for e in a.effects) or a.zones)
        self.assertLess(a.hero.hp, a.hero.max_hp)

    def test_burning_ground_hurts_a_hero(self):
        g = enemy("straw_golem", 20.5, 15.5)              # (the P7 fix: the golem's straw too)
        a = Arena(g, hero_at=(20.5, 15.5))
        g.hp = 0
        a.run(1 / 60)
        a.hero.x, a.hero.y = a.zones[0].x, a.zones[0].y
        hp = a.hero.hp
        update_zones(a.zones, a.actors(), a.effects, 1.0)
        self.assertLess(a.hero.hp, hp)

    def test_glass_shards_glance_off_walls(self):
        mage = enemy("glass_mage", 10.5, 15.5)
        shell = config.WEAPONS["glass_shards"].shell
        world = open_map(walls=[(14, y) for y in range(30)])
        shot = Projectile(11.5, 15.5, 0.0, shell, owner=mage, damage=6)
        shots = [shot]
        for _ in range(40):
            combat.update_projectiles(shots, world, [], 1 / 60, [mage])
        self.assertEqual(shot.bounces, 1)
        self.assertTrue(shot.alive)
        self.assertLess(shot.dir_x, 0)                    # coming back off the wall

    def test_dune_raider_hits_and_runs(self):
        r = enemy("dune_raider", 22.5, 15.5)
        r.timer = 0.1
        a = Arena(r)
        states = set()
        for _ in range(360):
            a.run(1 / 60)
            states.add(r.state)
        self.assertTrue({"wait", "in", "slash", "out"} <= states)
        self.assertLess(a.hero.hp, a.hero.max_hp)


class OddTest(unittest.TestCase):
    def test_tumbleweed_rolls_with_the_wind_and_bounces(self):
        t = enemy("tumbleweed", 10.5, 15.5)
        a = Arena(t, hero_at=(55.5, 5.5), walls=[(30, y) for y in range(30)])
        x0 = t.x
        a.run(2.0)
        self.assertGreater(t.x, x0 + 5)                   # east, with the wind
        a.run(4.0)
        self.assertGreater(abs((t.facing + math.pi) % math.tau - math.pi), math.pi / 2)  # back west

    def test_tumbleweed_bumps_once_a_second(self):
        t = enemy("tumbleweed", 29.0, 15.5)
        t.facing = 0.0
        a = Arena(t)
        hp = a.hero.hp
        a.run(0.5)
        self.assertAlmostEqual(hp - a.hero.hp, config.ENEMIES["tumbleweed"].damage
                               * config.ENEMY_DAMAGE_MULTIPLIER)

    def test_cactus_golem_answers_hits_with_spines(self):
        c = enemy("cactus_golem", 20.5, 15.5)
        a = Arena(c, hero_at=(50.5, 15.5))
        c.take_damage(10, a.hero, 0.0)
        a.run(1 / 60)
        spines = [p for p in a.projectiles if p.spec.look == "spine"]
        self.assertEqual(len(spines), config.CACTUS[0])
        c.take_damage(10, a.hero, 0.0)
        a.run(1 / 60)
        self.assertEqual(len([p for p in a.projectiles if p.spec.look == "spine"]),
                         config.CACTUS[0])                # (not again so soon)

    def test_djinn_lamp_drags_you_in_and_zaps(self):
        l = enemy("djinn_lamp", 26.0, 15.5)
        a = Arena(l)
        d0 = math.hypot(a.hero.x - l.x, a.hero.y - l.y)
        a.run(1.5)
        self.assertLess(math.hypot(a.hero.x - l.x, a.hero.y - l.y), d0)
        a.run(2.0)
        self.assertLess(a.hero.hp, a.hero.max_hp)


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
