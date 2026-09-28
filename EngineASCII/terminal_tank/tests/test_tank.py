import math
import random
import unittest

from terminal_tank import config
from terminal_tank.entities.tank import Tank, wrap_angle
from terminal_tank.systems.collision import hull_hits_solid
from terminal_tank.world.rng import hash_coords
from terminal_tank.world.test_map import TestMap

SPEC = config.TANKS[config.START_TANK]


def _map(*rows):
    return TestMap(list(rows))


OPEN = _map(*["." * 40] * 40)


def run(tank, world, ax, ay, seconds, dt=1 / 60):
    for _ in range(int(seconds / dt)):
        tank.drive(ax, ay, dt, world)


def overlaps(tank, world):
    return hull_hits_solid(world, tank.x, tank.y, tank.hull_angle, tank.half_len, tank.half_wid)


class AngleTest(unittest.TestCase):
    def test_wrap(self):
        self.assertAlmostEqual(wrap_angle(3 * math.pi), math.pi)
        self.assertAlmostEqual(wrap_angle(-math.pi / 2 + 4 * math.pi), -math.pi / 2)
        self.assertAlmostEqual(wrap_angle(0.1), 0.1)


class AimTest(unittest.TestCase):
    def test_aim_uses_true_angle_not_8_way(self):
        tank = Tank(SPEC, 10.0, 10.0)
        tank.aim_at(13.0, 11.0, 1 / 60)  # ~18.4 degrees below east
        self.assertAlmostEqual(tank.turret_angle, math.atan2(1.0, 3.0))


class DriveTest(unittest.TestCase):
    def setUp(self):
        self._mode = config.DRIVE_MODE
        config.DRIVE_MODE = "direct"

    def tearDown(self):
        config.DRIVE_MODE = self._mode

    def test_drives_north(self):
        tank = Tank(SPEC, 20.0, 20.0)
        run(tank, OPEN, 0, -1, 1.0)
        self.assertLess(tank.y, 15.0)
        self.assertAlmostEqual(tank.x, 20.0, places=3)

    def test_backs_up_instead_of_spinning(self):
        tank = Tank(SPEC, 20.0, 20.0)  # facing north
        run(tank, OPEN, 0, 1, 1.0)
        self.assertGreater(tank.y, 22.0)
        self.assertLess(tank.speed, 0)            # reversing
        self.assertEqual(tank.hull_dir8, 6)       # still facing north

    def test_turns_toward_side_direction(self):
        tank = Tank(SPEC, 20.0, 20.0)
        run(tank, OPEN, 1, 0, 1.0)
        self.assertEqual(tank.hull_dir8, 0)       # now facing east
        self.assertGreater(tank.x, 22.0)

    def test_tank_mode(self):
        config.DRIVE_MODE = "tank"
        tank = Tank(SPEC, 20.0, 20.0)
        run(tank, OPEN, 0, -1, 0.5)               # W = forward (north)
        self.assertLess(tank.y, 20.0)


class RotatedCollisionTest(unittest.TestCase):
    def test_wall_stops_tank_flush(self):
        world = _map(*(["." * 30] * 5 + ["#" * 30] + ["." * 30] * 10))
        tank = Tank(SPEC, 15.0, 12.0)             # facing north, wall above
        run(tank, world, 0, -1, 3.0)
        self.assertFalse(overlaps(tank, world))
        # Stopped against the wall (bottom edge y = 6): the hull's front
        # (half its length, in tiles) reaches within a pixel of it.
        front = tank.y - tank.half_len / config.TILE_PX_H
        self.assertLess(front - 6.0, 1.0 / config.TILE_PX_H)

    def test_diagonal_corners_never_enter_walls(self):
        # The old axis-aligned box let a 45-degree hull's corners poke into
        # walls. Drive diagonally into a corner pocket and check the true
        # rotated shape stays clear.
        rows = ["#" * 30] + ["#" + "." * 28 + "#"] * 20 + ["#" * 30]
        world = _map(*rows)
        tank = Tank(SPEC, 15.0, 10.0)
        for ax, ay in ((1, -1), (-1, -1), (1, 1), (-1, 1)):
            run(tank, world, ax, ay, 2.0)
            self.assertFalse(overlaps(tank, world), (ax, ay))

    def test_slides_along_wall(self):
        world = _map(*(["." * 40] * 5 + ["#" * 40] + ["." * 40] * 20))
        tank = Tank(SPEC, 10.0, 8.5)
        tank.hull_angle = -math.pi / 4            # facing NE
        run(tank, world, 1, -1, 1.0)
        self.assertGreater(tank.x, 12.0)          # kept moving east
        self.assertFalse(overlaps(tank, world))

    def test_turning_next_to_wall_nudges_instead_of_overlapping(self):
        world = _map(*(["." * 30] * 5 + ["#" * 30] + ["." * 30] * 10))
        tank = Tank(SPEC, 15.0, 12.0)
        tank.hull_angle = 0.0                     # facing east
        # Park flush under the wall, then ask it to turn north.
        run(tank, world, 0, -1, 0.05)
        for _ in range(120):
            tank.drive(0, -1, 1 / 60, world)
            self.assertFalse(overlaps(tank, world))

    def test_random_driving_on_test_map_never_overlaps(self):
        # Fuzz: 30 s of random input on the real test map, at the largest
        # allowed dt, in both drive modes.
        world = TestMap.load(config.TEST_MAP_FILE)
        rng = random.Random(1234)
        for mode in ("direct", "tank"):
            config.DRIVE_MODE = mode
            tank = Tank(SPEC, *world.spawn_point())
            axes = (0, 0)
            for i in range(1800):
                if i % 20 == 0:
                    axes = (rng.choice((-1, 0, 1)), rng.choice((-1, 0, 1)))
                tank.drive(*axes, config.MAX_DT if i % 7 == 0 else 1 / 60, world)
                self.assertFalse(overlaps(tank, world), f"{mode} frame {i}")
        config.DRIVE_MODE = "direct"


class TestMapFileTest(unittest.TestCase):
    def test_spawn_is_clear(self):
        world = TestMap.load(config.TEST_MAP_FILE)
        tank = Tank(SPEC, *world.spawn_point())
        self.assertFalse(overlaps(tank, world))

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
