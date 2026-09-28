import math
import unittest

from terminal_tank import config
from terminal_tank.entities.tank import Tank, wrap_angle
from terminal_tank.systems.collision import box_hits_solid
from terminal_tank.world.rng import hash_coords
from terminal_tank.world.test_map import TestMap


def _map(*rows):
    return TestMap(list(rows))


OPEN = _map(*["." * 40] * 40)


def run(tank, world, ax, ay, seconds, dt=1 / 60):
    for _ in range(int(seconds / dt)):
        tank.drive(ax, ay, dt, world)


class AngleTest(unittest.TestCase):
    def test_wrap(self):
        self.assertAlmostEqual(wrap_angle(3 * math.pi), math.pi)
        self.assertAlmostEqual(wrap_angle(-math.pi / 2 + 4 * math.pi), -math.pi / 2)
        self.assertAlmostEqual(wrap_angle(0.1), 0.1)


class AimTest(unittest.TestCase):
    def test_aim_uses_true_angle_not_8_way(self):
        tank = Tank(10.0, 10.0)
        tank.aim_at(13.0, 11.0, 1 / 60)  # ~18.4 degrees below east
        self.assertAlmostEqual(tank.turret_angle, math.atan2(1.0, 3.0))


class DriveTest(unittest.TestCase):
    def setUp(self):
        self._mode = config.DRIVE_MODE
        config.DRIVE_MODE = "direct"

    def tearDown(self):
        config.DRIVE_MODE = self._mode

    def test_drives_north(self):
        tank = Tank(20.0, 20.0)
        run(tank, OPEN, 0, -1, 1.0)
        self.assertLess(tank.y, 15.0)
        self.assertAlmostEqual(tank.x, 20.0, places=3)

    def test_backs_up_instead_of_spinning(self):
        tank = Tank(20.0, 20.0)  # facing north
        run(tank, OPEN, 0, 1, 1.0)
        self.assertGreater(tank.y, 22.0)
        self.assertLess(tank.speed, 0)            # reversing
        self.assertEqual(tank.hull_dir8, 6)       # still facing north

    def test_turns_toward_side_direction(self):
        tank = Tank(20.0, 20.0)
        run(tank, OPEN, 1, 0, 1.0)
        self.assertEqual(tank.hull_dir8, 0)       # now facing east
        self.assertGreater(tank.x, 22.0)

    def test_tank_mode(self):
        config.DRIVE_MODE = "tank"
        tank = Tank(20.0, 20.0)
        run(tank, OPEN, 0, -1, 0.5)               # W = forward (north)
        self.assertLess(tank.y, 20.0)


class CollisionTest(unittest.TestCase):
    def test_wall_stops_tank(self):
        world = _map(*(["." * 30] * 5 + ["#" * 30] + ["." * 30] * 10))
        tank = Tank(15.0, 12.0)
        run(tank, world, 0, -1, 3.0)
        # Wall occupies y in [5, 6): the box top must rest at/below 6.
        self.assertGreaterEqual(tank.y - tank.half_h, 6.0 - 1e-6)
        self.assertLess(tank.y - tank.half_h, 6.01)
        self.assertFalse(box_hits_solid(world, tank.x, tank.y, tank.half_w, tank.half_h))

    def test_slides_along_wall(self):
        world = _map(*(["." * 40] * 5 + ["#" * 40] + ["." * 40] * 20))
        tank = Tank(10.0, 7.5)
        tank.hull_angle = -math.pi / 4            # already facing NE
        run(tank, world, 1, -1, 1.0)
        self.assertGreater(tank.x, 12.0)          # kept moving east
        self.assertFalse(box_hits_solid(world, tank.x, tank.y, tank.half_w, tank.half_h))

    def test_never_enters_solid_at_high_dt(self):
        world = _map(*(["." * 30] * 10 + ["." * 14 + "#" + "." * 15] + ["." * 30] * 10))
        tank = Tank(15.0, 18.0)
        run(tank, world, 0, -1, 3.0, dt=config.MAX_DT)
        self.assertFalse(box_hits_solid(world, tank.x, tank.y, tank.half_w, tank.half_h))
        self.assertGreater(tank.y, 11.0)


class TestMapFileTest(unittest.TestCase):
    def test_spawn_is_clear(self):
        world = TestMap.load(config.TEST_MAP_FILE)
        x, y = world.spawn_point()
        self.assertFalse(box_hits_solid(world, x, y, config.TANK_HALF_W, config.TANK_HALF_H))

    def test_outside_is_solid(self):
        world = TestMap.load(config.TEST_MAP_FILE)
        self.assertTrue(world.tile_at(-5, -5).solid)


class RngTest(unittest.TestCase):
    def test_deterministic_and_spread(self):
        self.assertEqual(hash_coords(1, 2, 3), hash_coords(1, 2, 3))
        self.assertNotEqual(hash_coords(1, 2, 3), hash_coords(1, 3, 2))
        self.assertEqual(len({hash_coords(0, x, 0) % 1000 for x in range(200)}) > 150, True)


if __name__ == "__main__":
    unittest.main()
