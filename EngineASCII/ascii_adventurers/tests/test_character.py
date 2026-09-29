import math
import random
import unittest

from ascii_adventurers import config
from ascii_adventurers.entities.character import Character, wrap_angle
from ascii_adventurers.systems.collision import hull_hits_solid
from ascii_adventurers.world.rng import hash_coords
from ascii_adventurers.world.test_map import TestMap

SPEC = config.HEROES[config.START_HERO]


def _map(*rows):
    return TestMap(list(rows))


OPEN = _map(*["." * 40] * 40)


def run(hero, world, ax, ay, seconds, dt=1 / 60):
    for _ in range(int(seconds / dt)):
        hero.move(ax, ay, dt, world)


def overlaps(hero, world):
    return hull_hits_solid(world, hero.x, hero.y, 0.0, hero.half, hero.half)


class AngleTest(unittest.TestCase):
    def test_wrap(self):
        self.assertAlmostEqual(wrap_angle(3 * math.pi), math.pi)
        self.assertAlmostEqual(wrap_angle(-math.pi / 2 + 4 * math.pi), -math.pi / 2)
        self.assertAlmostEqual(wrap_angle(0.1), 0.1)


class HeroesTest(unittest.TestCase):
    def test_all_five_heroes_exist_and_the_wizard_is_default(self):
        self.assertEqual(set(config.HEROES), {"wizard", "knight", "bard", "princess", "huntress"})
        self.assertEqual(config.START_HERO, "wizard")
        for spec in config.HEROES.values():
            self.assertEqual(spec.weapon, "magic_bolt")   # shared placeholder attack


class AimTest(unittest.TestCase):
    def test_aim_uses_true_angle_not_8_way(self):
        hero = Character(SPEC, 10.0, 10.0)
        hero.aim_at(13.0, 11.0, 1 / 60)  # ~18.4 degrees below east
        self.assertAlmostEqual(hero.aim_angle, math.atan2(1.0, 3.0))

    def test_faces_its_aim(self):
        hero = Character(SPEC, 10.0, 10.0)
        hero.aim_at(5.0, 10.0, 1 / 60)
        self.assertTrue(hero.facing_left)
        hero.aim_at(15.0, 9.0, 1 / 60)
        self.assertFalse(hero.facing_left)


class WalkTest(unittest.TestCase):
    def test_walks_in_all_eight_directions_at_the_same_speed(self):
        for ax in (-1, 0, 1):
            for ay in (-1, 0, 1):
                if ax == ay == 0:
                    continue
                hero = Character(SPEC, 20.0, 20.0)
                run(hero, OPEN, ax, ay, 1.0)
                self.assertAlmostEqual(hero.speed, SPEC.max_speed, places=6)
                self.assertAlmostEqual(math.atan2(hero.y - 20, hero.x - 20), math.atan2(ay, ax))

    def test_stops_when_input_stops(self):
        hero = Character(SPEC, 20.0, 20.0)
        run(hero, OPEN, 1, 0, 0.5)
        run(hero, OPEN, 0, 0, 0.5)
        self.assertEqual(hero.speed, 0.0)

    def test_walking_advances_the_animation_distance(self):
        hero = Character(SPEC, 20.0, 20.0)
        run(hero, OPEN, 1, 0, 1.0)
        self.assertAlmostEqual(hero.walked, hero.x - 20.0)


class CollisionTest(unittest.TestCase):
    def test_wall_stops_hero_flush(self):
        world = _map(*(["." * 30] * 5 + ["#" * 30] + ["." * 30] * 10))
        hero = Character(SPEC, 15.0, 12.0)            # wall above
        run(hero, world, 0, -1, 3.0)
        self.assertFalse(overlaps(hero, world))
        # Stopped against the wall (bottom edge y = 6), within a pixel.
        top = hero.y - hero.half / config.TILE_PX_H
        self.assertLess(top - 6.0, 1.0 / config.TILE_PX_H)
        self.assertEqual(hero.vy, 0.0)

    def test_slides_along_wall(self):
        world = _map(*(["." * 40] * 5 + ["#" * 40] + ["." * 40] * 20))
        hero = Character(SPEC, 10.0, 8.5)
        run(hero, world, 1, -1, 1.0)
        self.assertGreater(hero.x, 14.0)              # kept moving east
        self.assertFalse(overlaps(hero, world))

    def test_random_walking_on_test_map_never_overlaps(self):
        # Fuzz: 30 s of random input on the real test map, at the largest
        # allowed dt now and then.
        world = TestMap.load(config.TEST_MAP_FILE)
        rng = random.Random(1234)
        hero = Character(SPEC, *world.spawn_point())
        axes = (0, 0)
        for i in range(1800):
            if i % 20 == 0:
                axes = (rng.choice((-1, 0, 1)), rng.choice((-1, 0, 1)))
            hero.move(*axes, config.MAX_DT if i % 7 == 0 else 1 / 60, world)
            self.assertFalse(overlaps(hero, world), f"frame {i}")


class TestMapFileTest(unittest.TestCase):
    def test_spawn_is_clear(self):
        world = TestMap.load(config.TEST_MAP_FILE)
        hero = Character(SPEC, *world.spawn_point())
        self.assertFalse(overlaps(hero, world))

    def test_outside_is_solid(self):
        world = TestMap.load(config.TEST_MAP_FILE)
        self.assertTrue(world.tile_at(-5, -5).solid)


class RngTest(unittest.TestCase):
    def test_deterministic_and_spread(self):
        self.assertEqual(hash_coords(1, 2, 3), hash_coords(1, 2, 3))
        self.assertNotEqual(hash_coords(1, 2, 3), hash_coords(1, 3, 2))
        self.assertGreater(len({hash_coords(0, x, 0) % 1000 for x in range(200)}), 150)


if __name__ == "__main__":
    unittest.main()
