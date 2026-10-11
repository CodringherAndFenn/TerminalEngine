"""P8 (playtest pass, 2026-10-11): the haunted forest's new enemies --
skeletons (bone piles), rotting woodsmen, spiderlings, bats, banshee,
phantom, grave digger, headless knight, giant centipede, giant spider,
ghost woodcutter, cultist, witch's apprentice, wendigo."""

import math
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.entities.projectile import Projectile
from ascii_adventurers.render.characters import ART
from ascii_adventurers.render import forest_art  # noqa: F401
from ascii_adventurers.systems import combat
from ascii_adventurers.tests.test_m16 import game
from ascii_adventurers.tests.test_m17 import step
from ascii_adventurers.tests.test_p7 import Arena, enemy
from ascii_adventurers.tests.test_weapons import Dummy, hero, open_map

NEW = ("skeleton", "woodsman", "spiderling", "bat", "banshee", "phantom", "grave_digger",
       "headless_knight", "centipede", "giant_spider", "woodcutter", "cultist", "apprentice",
       "wendigo")


def kinds(a, key):
    return [e for e in a.enemies if getattr(e, "kind_key", "") == key]


class CatalogTest(unittest.TestCase):
    def test_every_new_enemy_lives_in_the_forest_and_has_its_page(self):
        for key in NEW:
            spec = config.ENEMIES[key]
            self.assertIn("forest", spec.biomes, key)
            self.assertIn(key, config.BESTIARY, key)
            sprite = spec.sprite or config.BODIES[spec.body].sprite
            self.assertIn(sprite, ART, key)
            self.assertTrue(all(len(r) == 14 for r in ART[sprite]) and len(ART[sprite]) == 18)
        for key in ("risen_skeleton", "bone_pile", "knight_head", "candle"):
            self.assertEqual(config.ENEMIES[key].biomes, ())   # (parts: never spawned alone)

    def test_the_forest_now_has_eighteen_kinds(self):
        forest = [k for k, s in config.ENEMIES.items() if "forest" in s.biomes]
        self.assertEqual(len(forest), 4 + len(NEW))
        self.assertEqual({k for k in NEW if config.ENEMIES[k].elite},
                         {"headless_knight", "wendigo"})


class ChaserTest(unittest.TestCase):
    def test_simple_chasers_reach_and_bite(self):
        for key in ("skeleton", "woodsman", "spiderling", "bat"):
            a = Arena(enemy(key, 24.5, 15.5))
            a.run(4.0)
            self.assertLess(a.hero.hp, a.hero.max_hp, key)

    def test_a_skeleton_pulls_itself_together_once(self):
        s = enemy("skeleton", 10.5, 15.5)
        a = Arena(s, hero_at=(55.5, 15.5))
        s.hp = 0
        a.run(1 / 60)
        piles = kinds(a, "bone_pile")
        self.assertEqual(len(piles), 1)
        a.run(config.BONE_REBUILD + 0.1)
        risen = kinds(a, "risen_skeleton")
        self.assertEqual(len(risen), 1)
        risen[0].hp = 0                                   # down again: for good
        a.run(1 / 60)
        self.assertEqual(len(kinds(a, "bone_pile")), 1)

    def test_breaking_the_pile_ends_it(self):
        s = enemy("skeleton", 10.5, 15.5)
        a = Arena(s, hero_at=(55.5, 15.5))
        s.hp = 0
        a.run(1 / 60)
        kinds(a, "bone_pile")[0].hp = 0
        a.run(config.BONE_REBUILD + 0.5)
        self.assertEqual(kinds(a, "risen_skeleton"), [])

    def test_bats_fly_over_walls(self):
        walls = [(27, y) for y in range(30)]
        a = Arena(enemy("bat", 24.5, 15.5), walls=walls)
        a.run(3.0)
        self.assertLess(a.hero.hp, a.hero.max_hp)


class SpiritTest(unittest.TestCase):
    def test_banshee_screams_in_a_cone_and_pushes(self):
        b = enemy("banshee", 25.5, 15.5)
        a = Arena(b)
        x0 = a.hero.x
        a.run(3.0)
        self.assertLess(a.hero.hp, a.hero.max_hp)
        self.assertTrue(any(e.kind == "scream" for e in a.effects))
        self.assertGreater(a.hero.x, x0 + 0.5)            # pushed away from it

    def test_phantom_only_solid_part_of_the_time(self):
        p = enemy("phantom", 10.5, 15.5)
        a = Arena(p, hero_at=(55.5, 15.5))
        seen = set()
        for _ in range(240):
            a.run(1 / 60)
            seen.add(p.hittable)
        self.assertEqual(seen, {True, False})
        p.phase = config.PHANTOM[0] + 0.1                # faded: shots pass
        self.assertFalse(p.hittable)
        self.assertEqual(p.sprite_now(), "phantom_faded")

    def test_phantom_touch_hurts_and_slows(self):
        p = enemy("phantom", 29.0, 15.5)
        p.phase = 0.0
        a = Arena(p)
        a.run(1.0)
        self.assertLess(a.hero.hp, a.hero.max_hp)
        self.assertGreater(a.hero.slow_t, 0)

    def test_grave_digger_digs_up_skeletons_where_the_ground_cracks(self):
        g = enemy("grave_digger", 20.5, 15.5)
        g.timer = 0.1
        a = Arena(g)
        a.hero.invulnerable = True
        cracked = False
        for _ in range(200):
            a.run(1 / 60)
            cracked = cracked or g.dig is not None
        self.assertTrue(cracked)
        self.assertTrue(kinds(a, "risen_skeleton"))

    def test_headless_knight_swings_three_times(self):
        k = enemy("headless_knight", 28.5, 15.5)
        a = Arena(k)
        hp0 = a.hero.hp
        slashes = 0
        for _ in range(240):
            before = sum(1 for e in a.effects if e.kind == "slash")
            a.run(1 / 60)
            slashes += sum(1 for e in a.effects if e.kind == "slash") - before
        self.assertGreaterEqual(slashes, 3)
        self.assertLess(a.hero.hp, hp0)

    def test_hitting_the_head_hurts_the_knight_and_staggers_it(self):
        k = enemy("headless_knight", 20.5, 15.5)
        a = Arena(k, hero_at=(55.5, 15.5))
        a.run(1 / 60)
        heads = kinds(a, "knight_head")
        self.assertEqual(len(heads), 1)
        head = heads[0]
        hp = k.hp
        head.take_damage(20, a.hero, 0.0)
        self.assertAlmostEqual(hp - k.hp, 20 * config.KNIGHT_HEAD[1])
        self.assertGreater(k.stagger, 0)
        self.assertEqual(head.hp, head.max_hp)            # the head itself never dies
        k.hp = 0
        a.run(2 / 60)
        self.assertFalse(head.alive)                      # gone with the knight


class BeastTest(unittest.TestCase):
    def test_centipede_grows_and_splits(self):
        c = enemy("centipede", 10.5, 15.5)
        a = Arena(c, hero_at=(55.5, 15.5))
        a.run(1 / 60)
        segs = kinds(a, "centipede")
        self.assertEqual(len(segs), config.CENTIPEDE[0])
        heads = [s for s in segs if s.leader is None]
        self.assertEqual(heads, [c])
        segs[3].hp = 0                                    # shot in the middle
        a.run(2 / 60)
        alive = [s for s in segs if s.alive]
        self.assertEqual(len([s for s in alive if s.leader is None]), 2)   # two centipedes now
        self.assertEqual(segs[4].sprite_now(), "centipede_head")

    def test_centipede_body_follows(self):
        c = enemy("centipede", 10.5, 15.5)
        a = Arena(c)
        a.run(2.0)
        segs = [s for s in kinds(a, "centipede") if s.alive]
        for s in segs:
            if s.leader is not None:
                self.assertLessEqual(math.hypot(s.x - s.leader.x, s.y - s.leader.y),
                                     config.CENTIPEDE[1] + 0.05)

    def test_giant_spider_webs_slow_you(self):
        sp = enemy("giant_spider", 22.5, 15.5)
        sp.timer = 0.1
        a = Arena(sp)
        for _ in range(240):
            a.run(1 / 60)
            from ascii_adventurers.systems.zones import update_zones
            update_zones(a.zones, a.actors(), a.effects, 1 / 60)
        self.assertTrue(any(z.kind == "web" for z in a.zones))
        web = next(z for z in a.zones if z.kind == "web")
        a.hero.x, a.hero.y = web.x, web.y
        update_zones(a.zones, a.actors(), a.effects, 0.2)
        self.assertGreater(a.hero.slow_t, 0)
        self.assertAlmostEqual(a.hero.slow_mult, config.WEB[2])


class FolkTest(unittest.TestCase):
    def test_woodcutter_axe_comes_back(self):
        w = enemy("woodcutter", 24.5, 15.5)
        a = Arena(w)
        returned = False
        for _ in range(300):
            a.run(1 / 60)
            returned = returned or any(p.returning for p in a.projectiles)
        self.assertTrue(returned)

    def test_cultist_candles_raise_skeletons_until_snuffed(self):
        c = enemy("cultist", 20.5, 15.5)
        a = Arena(c, hero_at=(30.5, 15.5))
        a.hero.invulnerable = True
        for _ in range(60 * 3):
            a.run(1 / 60)
        candles = kinds(a, "candle")
        self.assertEqual(len(candles), config.CULTIST[0])
        a.run(config.CULTIST[2] + 0.5)
        self.assertTrue(kinds(a, "risen_skeleton"))
        for cd in candles:
            cd.hp = 0
        a.run(2 / 60)
        self.assertIsNone(c.ring)

    def test_cultist_death_puts_out_its_candles(self):
        c = enemy("cultist", 20.5, 15.5)
        a = Arena(c, hero_at=(30.5, 15.5))
        a.hero.invulnerable = True
        a.run(3.0)
        candles = kinds(a, "candle")
        c.hp = 0
        a.run(2 / 60)
        self.assertTrue(candles and not any(cd.alive for cd in candles))

    def test_cursed_orb_splits_in_four(self):
        app = enemy("apprentice", 10.5, 15.5)
        shell = config.WEAPONS["curse"].shell
        world = open_map(walls=[(14, y) for y in range(30)])
        shots = [Projectile(11.5, 15.5, 0.0, shell, owner=app, damage=10)]
        for _ in range(60):
            combat.update_projectiles(shots, world, [], 1 / 60, [app])
            if any(p.spec.look == "curse_bit" for p in shots):
                break
        bits = [p for p in shots if p.spec.look == "curse_bit"]
        self.assertEqual(len(bits), config.CURSE_SPLIT[0])
        self.assertTrue(all(p.damage == 10 * config.CURSE_SPLIT[1] for p in bits))

    def test_wendigo_lunges_in_pairs_and_howls(self):
        w = enemy("wendigo", 26.5, 15.5)
        w.howl_cd = 99
        a = Arena(w)
        lunges, prev = 0, None
        for _ in range(240):
            a.run(1 / 60)
            if w.state == "lunge" and prev != "lunge":
                lunges += 1
            prev = w.state
        self.assertGreaterEqual(lunges, 2)
        w.howl_cd, w.state = 0.0, "stalk"
        a.run(1.6)
        self.assertGreater(a.hero.slow_t, 0)
        self.assertAlmostEqual(a.hero.slow_mult, config.WENDIGO_HOWL[3])


class SlowTest(unittest.TestCase):
    def test_a_slow_slows_and_the_stronger_wins(self):
        h = hero("wizard")
        h.slowed(0.6, 3.0)
        h.slowed(0.8, 5.0)                                # weaker: ignored
        self.assertEqual((h.slow_mult, h.slow_t), (0.6, 3.0))
        world = open_map()
        for _ in range(60):
            h.move(1.0, 0.0, 1 / 60, world)
        self.assertAlmostEqual(h.vx, h.spec.max_speed * 0.6, places=3)


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
        self.assertTrue(any(getattr(e, "kind_key", "") == "knight_head" for e in s.enemies))


if __name__ == "__main__":
    unittest.main()
