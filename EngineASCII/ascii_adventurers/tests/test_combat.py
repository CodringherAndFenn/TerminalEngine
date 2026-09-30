import math
import random
import unittest

from ascii_adventurers import config
from ascii_adventurers.entities.projectile import Projectile
from ascii_adventurers.entities.character import Character
from ascii_adventurers.entities.weapon import Weapon
from ascii_adventurers.specs import ShellSpec, WeaponSpec
from ascii_adventurers.systems import combat
from ascii_adventurers.systems.raycast import first_hit
from ascii_adventurers.world import tiles
from ascii_adventurers.world.test_map import TestMap
from ascii_adventurers.world.tiles import Damage

SPEC = config.HEROES[config.START_HERO]
SPEC_DAMAGE = config.WEAPONS[SPEC.weapon].shell.damage


def _map(*rows):
    return TestMap(list(rows))


def brute_first_hit(world, x0, y0, x1, y1, samples=20000):
    """Reference answer: sample the segment very finely."""
    for i in range(samples + 1):
        t = i / samples
        tx, ty = math.floor(x0 + (x1 - x0) * t), math.floor(y0 + (y1 - y0) * t)
        if world.tile_at(tx, ty).blocks_shots:
            return tx, ty
    return None


class RaycastTest(unittest.TestCase):
    def test_matches_brute_force_on_random_segments(self):
        rng = random.Random(99)
        rows = ["".join("#" if rng.random() < 0.15 else "." for _ in range(40)) for _ in range(40)]
        world = _map(*rows)
        for _ in range(400):
            x0, y0 = rng.uniform(1, 39), rng.uniform(1, 39)
            if world.tile_at(math.floor(x0), math.floor(y0)).blocks_shots:
                continue
            x1, y1 = rng.uniform(1, 39), rng.uniform(1, 39)
            hit = first_hit(world.tile_at, x0, y0, x1, y1)
            want = brute_first_hit(world, x0, y0, x1, y1)
            self.assertEqual((hit.tx, hit.ty) if hit else None, want, (x0, y0, x1, y1))

    def test_fast_shell_cannot_skip_a_thin_wall(self):
        world = _map(*(["." * 30] * 3 + ["....#" + "." * 25] + ["." * 30] * 3))
        # One huge step that starts before and ends after the one-tile wall.
        hit = first_hit(world.tile_at, 0.5, 3.5, 20.5, 3.5)
        self.assertEqual((hit.tx, hit.ty), (4, 3))
        self.assertAlmostEqual(hit.x, 4.0)       # entered at the wall's face

    def test_exact_corner_between_two_walls_is_blocked(self):
        # Walls at (1,0) and (0,1) touch only at a corner. A shot aimed
        # exactly through that corner mustn't squeeze between them.
        world = _map(".#.", "#..", "...")
        hit = first_hit(world.tile_at, 0.5, 0.5, 1.5, 1.5)
        self.assertIsNotNone(hit)

    def test_water_does_not_stop_shells(self):
        world = _map("..~~~~..#.")
        hit = first_hit(world.tile_at, 0.5, 0.5, 9.5, 0.5)
        self.assertEqual((hit.tx, hit.ty), (8, 0))


class WeaponTest(unittest.TestCase):
    def test_click_fires_immediately_and_hold_keeps_exact_cadence(self):
        w = Weapon(WeaponSpec("t", fire_interval=0.25, shell=ShellSpec(10, 1, 10)))
        dt = 1 / 60
        shots = [f for f in range(600) if w.update(dt, True)]
        self.assertEqual(shots[0], 0)                        # instant on click
        self.assertEqual(len(shots), round(600 * dt / 0.25))  # 40 in 10 s: no drift

    def test_idle_time_does_not_bank_shots(self):
        w = Weapon(WeaponSpec("t", fire_interval=0.25, shell=ShellSpec(10, 1, 10)))
        for _ in range(300):
            w.update(1 / 60, False)
        fired = [w.update(1 / 60, True) for _ in range(5)]
        self.assertEqual(fired, [True, False, False, False, False])


class DestructionTest(unittest.TestCase):
    def test_wall_wears_then_becomes_passable_rubble(self):
        world = _map(".#.")
        glyphs = [world.glyph_at(1, 0)]
        results = [world.damage_tile(1, 0, 1) for _ in range(config.WALL_HP)]
        self.assertEqual(results[:-1], [Damage.DAMAGED] * (config.WALL_HP - 1))
        self.assertEqual(results[-1], Damage.DESTROYED)
        tile = world.tile_at(1, 0)
        self.assertIs(tile, tiles.RUBBLE)
        self.assertFalse(tile.solid or tile.blocks_shots)
        # The glyph changed as it wore down (stages drawn differently).
        world2 = _map(".#.")
        world2.damage_tile(1, 0, 1)
        glyphs.append(world2.glyph_at(1, 0))
        world2.damage_tile(1, 0, config.WALL_HP - 2)
        glyphs.append(world2.glyph_at(1, 0))
        self.assertEqual(len(set(glyphs)), 3)

    def test_trees_leave_splinters(self):
        world = _map(".T.")
        world.damage_tile(1, 0, config.TREE_HP)
        self.assertIs(world.tile_at(1, 0), tiles.SPLINTERS)
        self.assertFalse(world.tile_at(1, 0).solid)

    def test_rock_and_void_are_indestructible(self):
        world = _map(".R.")
        self.assertEqual(world.damage_tile(1, 0, 99), Damage.NONE)
        self.assertIs(world.tile_at(1, 0), tiles.ROCK)
        self.assertEqual(world.damage_tile(-3, -3, 99), Damage.NONE)


class FiringTest(unittest.TestCase):
    def test_shell_passes_through_the_aimed_point(self):
        world = _map(*["." * 60] * 40)
        hero = Character(SPEC, 20.0, 20.0)
        target = (31.3, 13.7)
        hero.aim_at(*target, 1 / 60)
        projectiles, effects = [], []
        combat.fire(hero, world, projectiles, effects)
        p = projectiles[0]
        # Distance from the target to the shell's line of flight.
        vx, vy = target[0] - p.x, target[1] - p.y
        off_line = abs(vx * p.dir_y - vy * p.dir_x)
        self.assertLess(off_line, 1e-9)
        self.assertGreater(vx * p.dir_x + vy * p.dir_y, 0)   # target ahead

    def test_shell_breaks_wall_after_enough_hits(self):
        rows = ["." * 40] * 20
        rows[10] = "." * 30 + "#" + "." * 9
        world = _map(*rows)
        hero = Character(SPEC, 20.0, 10.5)
        hero.aim_at(35.0, 10.5, 1 / 60)
        projectiles, effects = [], []
        events = []
        for _ in range(math.ceil(config.WALL_HP / SPEC_DAMAGE)):
            events += combat.fire(hero, world, projectiles, effects)
            for _ in range(60):
                events += combat.update_projectiles(projectiles, world, effects, 1 / 60)
        self.assertIs(world.tile_at(30, 10), tiles.RUBBLE)
        self.assertIn(combat.BREAK, events)
        self.assertEqual(projectiles, [])

    def test_shell_fizzles_at_max_range(self):
        world = _map(*["." * 200] * 5)
        shell = ShellSpec(speed=30.0, damage=1, max_range=10.0)
        p = Projectile(5.0, 2.5, 0.0, shell)
        effects, projectiles = [], [p]
        events = []
        for _ in range(120):
            events += combat.update_projectiles(projectiles, world, effects, 1 / 60)
        self.assertEqual(projectiles, [])
        self.assertAlmostEqual(p.x, 15.0)                     # exactly max_range
        self.assertIn(combat.FIZZLE, events)

    def test_shot_starting_inside_a_wall_hits_that_wall(self):
        rows = ["." * 20] * 10
        rows[5] = "." * 12 + "#" + "." * 7
        world = _map(*rows)
        # Hero right next to the wall: the shot's start point is inside it.
        hero = Character(SPEC, 11.3, 5.5)
        hero.aim_at(15.0, 5.5, 1 / 60)
        projectiles, effects = [], []
        combat.fire(hero, world, projectiles, effects)
        self.assertEqual(projectiles, [])
        self.assertEqual(world.hp_at(12, 5), config.WALL_HP - SPEC_DAMAGE)


class ActorGridTest(unittest.TestCase):
    def test_near_finds_every_actor_a_segment_touches(self):
        from ascii_adventurers.entities.actor import Actor
        rng = random.Random(3)
        actors = []
        for _ in range(300):
            a = Actor(10, rng.choice((0.3, 0.45, 0.8, 1.4)))
            a.x, a.y = rng.uniform(-30, 30), rng.uniform(-30, 30)
            actors.append(a)
        actors[7].hp = 0                                  # dead: never returned
        grid = combat.ActorGrid(actors)
        for _ in range(3000):
            x0, y0 = rng.uniform(-32, 32), rng.uniform(-32, 32)
            dx, dy = rng.uniform(-3, 3), rng.uniform(-3, 3)
            near = grid.near(x0, y0, x0 + dx, y0 + dy)
            idx = [i for i, _ in near]
            self.assertEqual(idx, sorted(set(idx)))       # once each, in order
            got = set(idx)
            for i, a in enumerate(actors):
                if a.hittable and combat.segment_circle_t(x0, y0, dx, dy, a.x, a.y, a.hit_radius) is not None:
                    self.assertIn(i, got)
            self.assertNotIn(7, got)


class SfxTest(unittest.TestCase):
    def test_builds_all_sounds_and_is_silent_without_audio(self):
        from engine import Audio
        from ascii_adventurers.engine_ext.sfx import Sfx

        from ascii_adventurers.engine_ext import sfx as sfx_mod

        needed = {"hit", "break", "fizzle", "zap", "swing", "pulse", "ui"}
        needed |= {w.shell.sound for w in config.WEAPONS.values() if w.shell is not None}
        audio = Audio()
        if audio.init(volume=0.0):          # dummy SDL audio driver in tests
            sfx = Sfx(audio)
            self.assertLessEqual(needed, set(sfx._sounds))
            for name, variants in sfx._sounds.items():
                self.assertEqual(len(variants), len(sfx_mod.VARIANTS), name)
            for name in needed | {"shot", "thud"}:
                sfx.play(name)
            audio.quit()
        silent = Sfx(Audio())               # never initialized: unavailable
        silent.play("shot")                 # must be a no-op, not an error
        self.assertEqual(silent._sounds, {})

    def test_levels_follow_the_mix_table(self):
        from ascii_adventurers.engine_ext import sfx as sfx_mod

        for name, variants in sfx_mod.mixed(22050).items():
            base = variants[sfx_mod.VARIANTS.index(1.0)]
            rms = math.sqrt(sum(v * v for v in base) / len(base))
            peak = max(abs(v) for v in base)
            self.assertLessEqual(peak, 0.99, name)                     # never clips
            # Levelled to its MIX loudness (a little under, if it would clip).
            self.assertLessEqual(rms, sfx_mod.TARGET_RMS * sfx_mod.MIX[name] + 1e-9, name)
            self.assertGreater(rms, sfx_mod.TARGET_RMS * sfx_mod.MIX[name] * 0.6, name)
            self.assertNotEqual(len(variants[0]), len(variants[-1]), name)   # pitched apart


if __name__ == "__main__":
    unittest.main()
