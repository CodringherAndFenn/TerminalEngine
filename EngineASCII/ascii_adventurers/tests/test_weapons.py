import math
import unittest
from dataclasses import replace

from ascii_adventurers import config
from ascii_adventurers.entities.actor import Actor
from ascii_adventurers.entities.character import Character
from ascii_adventurers.systems import combat
from ascii_adventurers.world import tiles
from ascii_adventurers.world.test_map import TestMap

STEP = 1 / 60


class Dummy(Actor):
    """A target that just stands there."""
    faction = "enemy"

    def __init__(self, x, y, hp=500):
        super().__init__(hp, 0.45)
        self.x, self.y = x, y


def open_map(w=60, h=30, walls=()):
    rows = [["."] * w for _ in range(h)]
    for x, y in walls:
        rows[y][x] = "#"
    return TestMap(["".join(r) for r in rows])


def hero(name, x=10.5, y=10.5, aim=0.0):
    if name == "swordsman":     # no hero carries the sword since the dwarf came
        spec = replace(config.HEROES["dwarf"], weapon="sword")
    else:
        spec = config.HEROES[name]
    h = Character(spec, x, y)
    h.aim_angle = aim
    return h


def fly(projectiles, world, actors, effects, seconds=2.0):
    events = []
    for _ in range(int(seconds / STEP)):
        events += combat.update_projectiles(projectiles, world, effects, STEP, actors)
    return events


class WeaponDataTest(unittest.TestCase):
    def test_each_hero_has_the_planned_weapon(self):
        kinds = {h: config.WEAPONS[s.weapon] for h, s in config.HEROES.items()}
        self.assertEqual(kinds["wizard"].shell.chain, 2)
        self.assertGreater(kinds["huntress"].shell.pierce, 0)
        self.assertEqual(kinds["princess"].pellets, 5)
        self.assertTrue(kinds["dwarf"].shell.returns)
        self.assertEqual(kinds["bard"].kind, "pulse")
        self.assertTrue(kinds["bard"].auto)


class RainbowTest(unittest.TestCase):
    def test_five_colors_fanned_evenly_around_the_aim(self):
        world, h, shots = open_map(), hero("princess", aim=0.3), []
        combat.fire(h, world, shots, [])
        spec = config.WEAPONS["rainbow"]
        self.assertEqual(len(shots), 5)
        self.assertEqual([p.variant for p in shots], [0, 1, 2, 3, 4])
        angles = [p.angle for p in shots]
        self.assertAlmostEqual(angles[2], 0.3)                          # middle on the aim
        self.assertAlmostEqual(angles[-1] - angles[0], math.radians(spec.spread_deg))
        gaps = [b - a for a, b in zip(angles, angles[1:])]
        self.assertAlmostEqual(max(gaps), min(gaps))

    def test_short_range(self):
        world, h, shots = open_map(), hero("princess"), []
        combat.fire(h, world, shots, [])
        far = Dummy(10.5 + config.WEAPONS["rainbow"].shell.max_range + 3, 10.5)
        fly(shots, world, [far], [])
        self.assertEqual(far.hp, far.max_hp)


class LongbowTest(unittest.TestCase):
    def test_arrow_pierces_two_and_stops_at_the_third(self):
        world, h, shots = open_map(), hero("huntress"), []
        line = [Dummy(15.5 + 3 * i, 10.5) for i in range(4)]
        combat.fire(h, world, shots, [])
        fly(shots, world, [h] + line, [])
        dmg = config.WEAPONS["longbow"].shell.damage
        self.assertEqual([d.max_hp - d.hp for d in line], [dmg, dmg, dmg, 0])
        self.assertEqual(shots, [])

    def test_each_enemy_is_hit_once(self):
        world, h, shots = open_map(), hero("huntress"), []
        big = Dummy(16.5, 10.5)
        big.hit_radius = 2.0                     # the arrow stays inside it a while
        combat.fire(h, world, shots, [])
        fly(shots, world, [big], [])
        self.assertEqual(big.max_hp - big.hp, config.WEAPONS["longbow"].shell.damage)


class ChainLightningTest(unittest.TestCase):
    def test_jumps_to_two_more_with_falling_damage(self):
        world, h, shots, effects = open_map(), hero("wizard"), [], []
        first = Dummy(18.5, 10.5)
        second = Dummy(18.5, 13.5)               # 3 tiles from the first
        third = Dummy(21.5, 14.5)                # ~3.2 from the second
        fourth = Dummy(24.5, 16.5)               # the chain ends before this one
        combat.fire(h, world, shots, effects)
        events = fly(shots, world, [h, first, second, third, fourth], effects)
        s = config.WEAPONS["shock_bolt"].shell
        taken = [d.max_hp - d.hp for d in (first, second, third, fourth)]
        self.assertAlmostEqual(taken[0], s.damage)
        self.assertAlmostEqual(taken[1], s.damage * s.chain_falloff)
        self.assertAlmostEqual(taken[2], s.damage * s.chain_falloff ** 2)
        self.assertEqual(taken[3], 0)
        self.assertEqual(sum(e.kind == "arc" for e in effects), 2)
        self.assertEqual(events.count("zap"), 2)

    def test_no_jump_through_walls_or_out_of_range(self):
        wall = [(20, y) for y in range(5, 16)]
        world, h, shots = open_map(walls=wall), hero("wizard"), []
        first = Dummy(18.5, 10.5)
        behind_wall = Dummy(22.5, 10.5)
        too_far = Dummy(18.5, 10.5 + config.WEAPONS["shock_bolt"].shell.chain_range + 1)
        combat.fire(h, world, shots, [])
        fly(shots, world, [first, behind_wall, too_far], [])
        self.assertLess(first.hp, first.max_hp)
        self.assertEqual(behind_wall.hp, behind_wall.max_hp)
        self.assertEqual(too_far.hp, too_far.max_hp)


class SwordTest(unittest.TestCase):
    def test_hits_everything_in_the_arc_but_not_behind(self):
        world, h, effects = open_map(w=80), hero("swordsman", x=30.5, y=15.5, aim=0.0), []
        reach = config.WEAPONS["sword"].reach    # (positions follow the tuning)
        front = Dummy(30.5 + reach * 0.8, 15.5)
        a = math.radians(55)                     # ~55 degrees off the aim
        front_side = Dummy(30.5 + math.cos(a) * reach * 0.7, 15.5 + math.sin(a) * reach * 0.7)
        behind = Dummy(30.5 - reach * 0.8, 15.5)
        out_of_reach = Dummy(30.5 + reach + 1.5, 15.5)
        events = combat.attack(h, world, [], effects, [h, front, front_side, behind, out_of_reach])
        dmg = config.WEAPONS["sword"].damage
        self.assertEqual(front.max_hp - front.hp, dmg)
        self.assertEqual(front_side.max_hp - front_side.hp, dmg)
        self.assertEqual(behind.hp, behind.max_hp)
        self.assertEqual(out_of_reach.hp, out_of_reach.max_hp)
        self.assertEqual(h.hp, h.max_hp)
        self.assertIn("swing", events)
        self.assertTrue(any(e.kind == "swing" for e in effects))

    def test_chops_the_tree_in_front(self):
        rows = ["." * 30 for _ in range(20)]
        rows[10] = "." * 11 + "T" + "." * 18
        world, h = TestMap(rows), hero("swordsman", x=10.5, y=10.5, aim=0.0)
        for _ in range(10):
            combat.attack(h, world, [], [], [h])
        self.assertIsNot(world.tile_at(11, 10), tiles.TREE)


class ThrowingAxeTest(unittest.TestCase):
    def test_flies_out_comes_back_and_hits_on_both_legs(self):
        world, h, effects = open_map(w=80), hero("dwarf", x=10.5, y=15.5, aim=0.0), []
        shell = config.WEAPONS["throwing_axe"].shell
        near = Dummy(10.5 + shell.max_range * 0.5, 15.5)
        behind = Dummy(10.5 + shell.max_range * 0.7, 15.5)   # same line: axes pass through
        shots = []
        combat.fire(h, world, shots, effects)
        axe = shots[0]
        furthest = 0.0
        for _ in range(int(3.0 / STEP)):
            combat.update_projectiles(shots, world, effects, STEP, [h, near, behind])
            if shots:
                furthest = max(furthest, axe.x - h.x)
        self.assertEqual(shots, [], "caught")
        self.assertAlmostEqual(furthest, shell.max_range, delta=1.0)
        for d in (near, behind):
            self.assertEqual(d.max_hp - d.hp, 2 * shell.damage)    # out and back
        self.assertEqual(h.hp, h.max_hp)
        self.assertFalse(any(e.kind == "fizzle" for e in effects))

    def test_homes_on_a_thrower_who_moved(self):
        world, h = open_map(w=80), hero("dwarf", x=10.5, y=15.5, aim=0.0)
        shots = []
        combat.fire(h, world, shots, [])
        h.y = 22.5
        fly(shots, world, [h], [], seconds=3.0)
        self.assertEqual(shots, [])

    def test_bounces_off_a_wall_and_hurts_it(self):
        world = open_map(w=80, walls=[(15, y) for y in range(10, 20)])
        h = hero("dwarf", x=10.5, y=15.5, aim=0.0)
        shots = []
        combat.fire(h, world, shots, [])
        events = combat.update_projectiles(shots, world, [], STEP, [h])
        for _ in range(int(0.5 / STEP)):
            events += combat.update_projectiles(shots, world, [], STEP, [h])
        self.assertTrue(shots and shots[0].returning or not shots)
        self.assertIn(combat.HIT, events)          # the wall took the blow
        fly(shots, world, [h], [], seconds=2.0)
        self.assertEqual(shots, [])

    def test_drops_when_the_thrower_dies(self):
        world, h, effects = open_map(w=80), hero("dwarf", x=10.5, y=15.5, aim=0.0), []
        shots = []
        combat.fire(h, world, shots, effects)
        h.hp = 0
        fly(shots, world, [h], effects, seconds=3.0)
        self.assertEqual(shots, [])
        self.assertTrue(any(e.kind == "fizzle" for e in effects))


class LutePulseTest(unittest.TestCase):
    def test_hits_all_around_not_through_walls_and_not_far(self):
        wall = [(x, 7) for x in range(5, 16)]
        world, h = open_map(walls=wall), hero("bard")
        spec = config.WEAPONS["lute"]
        around = [Dummy(10.5 + dx, 10.5 + dy) for dx, dy in ((2, 0), (-2, 1), (0, 2.5), (-1.5, -1.5))]
        behind_wall = Dummy(10.5, 5.5)
        far = Dummy(10.5 + spec.reach + 2, 10.5)
        combat.attack(h, world, [], [], [h] + around + [behind_wall, far])
        for d in around:
            self.assertEqual(d.max_hp - d.hp, spec.damage)
        self.assertEqual(behind_wall.hp, behind_wall.max_hp)
        self.assertEqual(far.hp, far.max_hp)

    def test_plays_on_its_own_in_game(self):
        import os
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        from ascii_adventurers.tests.test_players import make_manager, start_game
        m = make_manager()
        s = start_game(m, hero="bard")
        s.mouse.left_held = lambda: False           # never touches the trigger
        target = Dummy(s.hero.x + 2, s.hero.y)
        target.espec = config.ENEMIES["goblin_archer"]
        target.spawn_id = None
        s.enemies.append(target)
        target.think = lambda ctx, dt: None
        target.hear = lambda x, y: None
        target.tick_flash = lambda dt: None
        for _ in range(int(2.5 / STEP)):
            s.update(STEP)
        beats = (target.max_hp - target.hp) / config.WEAPONS["lute"].damage
        self.assertGreaterEqual(beats, 2)


class NoFriendlyFireBetweenPlayersTest(unittest.TestCase):
    def test_heroes_never_hurt_each_other(self):
        world = open_map()
        for name in config.HEROES:
            a = hero(name, 10.5, 10.5, aim=0.0)
            b = hero("wizard", 12.0, 10.5)
            shots, actors = [], [a, b]
            combat.attack(a, world, shots, [], actors)
            fly(shots, world, actors, [])
            self.assertEqual(b.hp, b.max_hp, name)

    def test_enemies_still_hurt_each_other(self):
        world, shots = open_map(), []
        archer = hero("wizard")
        archer.faction = "enemy"                  # an enemy shooter
        victim = Dummy(15.5, 10.5)
        combat.fire(archer, world, shots, [])
        fly(shots, world, [archer, victim], [])
        self.assertLess(victim.hp, victim.max_hp)


if __name__ == "__main__":
    unittest.main()


class PulseTerrainTest(unittest.TestCase):
    def test_wears_visible_walls_at_a_quarter_of_its_damage(self):
        # A wall ring at distance 3 (inside reach), and a second wall right
        # behind it that the first one hides.
        spec = config.WEAPONS["lute"]
        world = open_map(walls=[(13, 10), (14, 10)])
        h = hero("bard", 10.5, 10.5)
        combat.attack(h, world, [], [], [h])
        wear = spec.damage * config.PULSE_TERRAIN_FACTOR
        self.assertAlmostEqual(tiles.WALL.hp - world.hp_at(13, 10), wear)
        self.assertIsNone(world.hp_at(14, 10))               # hidden behind the first
