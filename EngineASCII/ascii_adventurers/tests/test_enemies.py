import math
import random
import unittest

from ascii_adventurers import config
from ascii_adventurers.ai import make_enemy
from ascii_adventurers.ai.brain import AIContext
from ascii_adventurers.entities.effects import Effect
from ascii_adventurers.entities.projectile import Projectile
from ascii_adventurers.entities.character import Character
from ascii_adventurers.entities.weapon import Weapon
from ascii_adventurers.systems import combat
from ascii_adventurers.systems.spawner import Spawner
from ascii_adventurers.world import biomes, tiles
from ascii_adventurers.world.chunked import ChunkedWorld
from ascii_adventurers.world.test_map import TestMap

PLAYER = config.HEROES[config.START_HERO]
DT = 1 / 60


def arena(*rows, w=80, h=50):
    if rows:
        return TestMap(list(rows))
    return TestMap(["." * w for _ in range(h)])


def player_at(x, y):
    return Character(PLAYER, x, y)


def ctx_for(world, player, enemies, projectiles=None, effects=None):
    return AIContext(world, player, [player] + list(enemies),
                     projectiles if projectiles is not None else [],
                     effects if effects is not None else [])


def run(world, player, enemies, seconds, projectiles=None, effects=None):
    """Tiny game loop: enemies think, shells fly (friendly fire on)."""
    projectiles = [] if projectiles is None else projectiles
    effects = [] if effects is None else effects
    done = set()
    for _ in range(int(seconds / DT)):
        ctx = ctx_for(world, player, [e for e in enemies if e.alive], projectiles, effects)
        for e in enemies:
            if e.alive:
                e.think(ctx, DT)
        combat.update_projectiles(projectiles, world, effects, DT,
                                  [player] + [e for e in enemies if e.alive])
        # Like the game scene: death hooks run (a killed puffer still bursts).
        for e in enemies:
            if not e.alive and id(e) not in done:
                done.add(id(e))
                if hasattr(e, "on_death"):
                    e.on_death(ctx_for(world, player, [o for o in enemies if o.alive]))
    return projectiles, effects


def enemy(key, x, y, seed=1):
    return make_enemy(key, x, y, random.Random(seed))


class DamageTest(unittest.TestCase):
    def test_player_bolts_kill_a_goblin_archer_in_two_hits(self):
        world = arena()
        e = enemy("goblin_archer", 30.5, 20.5)
        for i in range(2):
            p = Projectile(20.5, 20.5, 0.0, config.WEAPONS["magic_bolt"].shell, owner=player_at(0, 0))
            combat.update_projectiles([p], world, [], 1.0, [e])
            self.assertEqual(e.alive, i == 0)   # alive after one hit, dead after two

    def test_only_ogre_rocks_and_player_bolts_hurt_terrain(self):
        for weapon, hurts in (("goblin_bow", False), ("hex", False),
                              ("tower_orbs", False), ("boulder", True), ("magic_bolt", True)):
            world = arena("." * 10 + "#" + "." * 9)
            p = Projectile(1.5, 0.5, 0.0, config.WEAPONS[weapon].shell)
            combat.update_projectiles([p], world, [], 1.0, [])
            self.assertEqual(world.hp_at(10, 0) is not None, hurts, weapon)

    def test_ogre_front_armor(self):
        ogre = enemy("ogre", 20.5, 20.5)
        ogre.aim_angle = 0.0                          # facing east
        front = ogre.take_damage(20, None, math.pi)   # shot flying west: hits its front
        back = ogre.take_damage(20, None, 0.0)        # shot flying east: hits its back
        self.assertAlmostEqual(front, 20 * config.BODIES["ogre"].front_armor)
        self.assertEqual(back, 20)


class InfightingTest(unittest.TestCase):
    def test_friendly_fire_hurts_but_small_amounts_are_forgiven(self):
        a, b = enemy("goblin_archer", 10.5, 10.5), enemy("goblin_archer", 15.5, 10.5, seed=2)
        a.take_damage(5, b, 0.0)                     # a stray round
        self.assertLess(a.hp, a.max_hp)
        self.assertIsNone(a.grudge)
        a.take_damage(config.INFIGHT_AGGRO_FRACTION * a.max_hp, b, 0.0)
        self.assertIs(a.grudge, b)                   # that's too much

    def test_grudge_changes_target(self):
        world = arena()
        player = player_at(70.5, 40.5)               # far away and unseen
        a, b = enemy("goblin_archer", 10.5, 10.5), enemy("goblin_archer", 16.5, 10.5, seed=2)
        a.take_damage(a.max_hp * 0.5, b, 0.0)
        a.think(ctx_for(world, player, [a, b]), DT)
        self.assertIs(a.target, b)

    def test_player_damage_always_alerts(self):
        e = enemy("goblin_archer", 10.5, 10.5)
        e.take_damage(1, player_at(40.5, 40.5), 0.0)
        self.assertTrue(e.alert)
        self.assertEqual(e.last_known, (40.5, 40.5))


class SensesTest(unittest.TestCase):
    def test_walls_block_sight_water_does_not(self):
        e = enemy("goblin_archer", 5.5, 5.5)
        p = player_at(12.5, 5.5)
        self.assertTrue(e.can_see(arena(*["." * 20] * 10), p))
        self.assertFalse(e.can_see(arena(*(["." * 8 + "#" + "." * 11] * 10)), p))
        self.assertTrue(e.can_see(arena(*(["." * 8 + "~" + "." * 11] * 10)), p))

    def test_out_of_sight_range(self):
        e = enemy("goblin_archer", 5.5, 5.5)
        self.assertFalse(e.can_see(arena(w=80), player_at(5.5 + e.espec.sight + 2, 5.5)))

    def test_hearing_reveals_roughly_where(self):
        e = enemy("goblin_archer", 10.5, 10.5)
        e.hear(20.5, 10.5)
        self.assertTrue(e.alert)
        self.assertLess(math.dist(e.last_known, (20.5, 10.5)), 3)
        far = enemy("goblin_archer", 10.5, 10.5)
        far.hear(10.5 + config.HEARING_RADIUS + 5, 10.5)
        self.assertFalse(far.alert)


class SteeringTest(unittest.TestCase):
    def test_gets_around_a_wall_to_its_goal(self):
        # A long wall between the enemy and the goal: no pathfinding, but the
        # commit-to-a-side steering should slide round the end of it.
        rows = ["." * 60 for _ in range(40)]
        rows[20] = "." * 10 + "#" * 30 + "." * 20
        world = arena(*rows)
        for seed in range(5):
            e = enemy("goblin_archer", 25.5, 26.5, seed=seed)
            for _ in range(int(25 / DT)):
                e.drive_to(ctx_for(world, player_at(0, 0), [e]), 25.5, 12.5, DT)
                if math.hypot(e.x - 25.5, e.y - 12.5) < 2:
                    break
            self.assertLess(math.hypot(e.x - 25.5, e.y - 12.5), 2, seed)

    def test_recovers_when_stuck_in_a_pocket(self):
        # U-shaped pocket opening away from the goal.
        rows = ["." * 40 for _ in range(30)]
        for y in range(8, 20):
            rows[y] = "." * 12 + "#" + "." * 10 + "#" + "." * 16
        rows[8] = "." * 12 + "#" * 12 + "." * 16
        world = arena(*rows)
        escaped = 0
        for seed in range(6):
            e = enemy("warrior", 18.5, 14.5, seed=seed)
            for _ in range(int(40 / DT)):
                e.walk(ctx_for(world, player_at(0, 0), [e]), 18.5, 3.5, DT, e.espec.speed)
                if e.y < 7:
                    escaped += 1
                    break
        # Clumsy on purpose (no pathfinding), but frustration detours must
        # get it out most of the time.
        self.assertGreaterEqual(escaped, 5)


class BehaviourTest(unittest.TestCase):
    def test_warlock_telegraphs_before_firing(self):
        world = arena()
        player = player_at(20.5, 20.5)
        s = enemy("warlock", 42.5, 20.5)
        projectiles = []
        first_shot = None
        beam_seen = 0.0
        for f in range(int(8 / DT)):
            beam_seen = max(beam_seen, s.beam)
            before = len(projectiles)
            s.think(ctx_for(world, player, [s], projectiles), DT)
            if len(projectiles) > before and first_shot is None:
                first_shot = f
                break
        self.assertIsNotNone(first_shot)
        self.assertGreaterEqual(beam_seen + 1e-6, s.espec.windup - DT)

    def test_warrior_winds_up_before_it_hurts(self):
        world = arena()
        player = player_at(20.5, 20.5)
        w = enemy("warrior", 22.0, 20.5)
        hp_at_windup = None
        for _ in range(int(3 / DT)):
            w.think(ctx_for(world, player, [w]), DT)
            if w.windup > 0 and hp_at_windup is None:
                hp_at_windup = player.hp
        self.assertEqual(hp_at_windup, player.max_hp)   # no damage before the swing
        self.assertLess(player.hp, player.max_hp)

    def test_puffer_burst_hurts_everyone_nearby(self):
        world = arena()
        player = player_at(20.5, 20.5)
        puff = enemy("puffer", 22.0, 20.5)
        bystander = enemy("warrior", 21.5, 22.0, seed=4)
        run(world, player, [puff, bystander], 2.0)
        self.assertFalse(puff.alive)
        self.assertLess(player.hp, player.max_hp)
        self.assertLess(bystander.hp, bystander.max_hp)   # friendly fire

    def test_shooting_a_puffer_pops_it_on_the_spot(self):
        world = arena()
        player = player_at(20.5, 20.5)
        puff = enemy("puffer", 30.5, 20.5)
        neighbour = enemy("goblin_archer", 31.5, 21.5, seed=5)
        p = Projectile(22.5, 20.5, 0.0, config.WEAPONS["magic_bolt"].shell, owner=player)
        combat.update_projectiles([p], world, [], 1.0, [puff, neighbour])
        self.assertFalse(puff.alive)
        ctx = ctx_for(world, player, [neighbour])
        puff.on_death(ctx)
        self.assertLess(neighbour.hp, neighbour.max_hp)
        self.assertEqual(player.hp, player.max_hp)         # player was far away

    def test_burrower_cannot_be_hit_underground(self):
        world = arena()
        b = enemy("burrower", 30.5, 20.5)
        self.assertFalse(b.hittable)
        p = Projectile(22.5, 20.5, 0.0, config.WEAPONS["magic_bolt"].shell)
        combat.update_projectiles([p], world, [], 1.0, [b])
        self.assertEqual(b.hp, b.max_hp)

    def test_burrower_surfaces_attacks_and_is_vulnerable(self):
        world = arena()
        player = player_at(20.5, 20.5)
        b = enemy("burrower", 28.5, 20.5)
        states = set()
        for _ in range(int(6 / DT)):
            b.think(ctx_for(world, player, [b]), DT)
            states.add(b.state)
            if b.state == "up":
                self.assertTrue(b.hittable)
        self.assertTrue({"under", "rumble", "up"} <= states)
        self.assertLess(player.hp, player.max_hp)

    def test_burrower_stays_in_the_desert(self):
        class HalfDesert(TestMap):
            def biome_at(self, tx, ty):
                return biomes.DESERT if tx < 40 else biomes.PLAINS

        world = HalfDesert(["." * 80 for _ in range(40)])
        player = player_at(60.5, 20.5)          # out on the plains
        b = enemy("burrower", 35.5, 20.5)
        b.alert, b.last_known = True, (60.5, 20.5)
        for _ in range(int(8 / DT)):
            b.think(ctx_for(world, player, [b]), DT)
            self.assertLess(b.x, 40.0)

    def test_tower_fires_bursts(self):
        w = Weapon(config.WEAPONS["tower_orbs"])
        shots = [f for f in range(int(3 / DT)) if w.update(DT, True)]
        burst = config.WEAPONS["tower_orbs"].burst
        self.assertEqual(len(shots), 2 * burst)            # two pulls in 3 s
        self.assertLess(shots[burst - 1] - shots[0], 30)   # a burst is quick

    def test_archer_fights_player(self):
        world = arena()
        player = player_at(20.5, 20.5)
        t = enemy("goblin_archer", 30.5, 24.5)
        run(world, player, [t], 10.0)
        self.assertLess(player.hp, player.max_hp)

    def test_ogre_smashes_through_walls(self):
        rows = ["." * 60 for _ in range(30)]
        for y in range(5, 25):
            rows[y] = "." * 30 + "#" + "." * 29
        world = arena(*rows)
        player = player_at(45.5, 15.5)
        h = enemy("ogre", 15.5, 15.5)
        h.alert, h.last_known = True, (45.5, 15.5)   # it heard the player
        run(world, player, [h], 20.0)
        broken = sum(world.tile_at(30, y) is tiles.RUBBLE for y in range(5, 25))
        self.assertGreater(broken, 0)


class SpawnerTest(unittest.TestCase):
    def test_deterministic_and_enemy_free_start(self):
        w1, w2 = ChunkedWorld(42), ChunkedWorld(42)
        s1, s2 = Spawner(w1, 42), Spawner(w2, 42)
        for cx in range(-8, 9):
            for cy in range(-8, 9):
                r1, r2 = s1.roster(cx, cy), s2.roster(cx, cy)
                self.assertEqual(r1, r2)
                sx, sy = w1.spawn_point()
                for _, _, x, y in r1:
                    self.assertGreaterEqual(math.hypot(x - sx, y - sy), config.ENEMY_FREE_RADIUS)

    def test_enemies_only_spawn_in_their_biomes(self):
        # Sample the central plains and a band of the biome ring.
        world = ChunkedWorld(7)
        sp = Spawner(world, 7)
        ring = int(world.layout.radius * 0.5) // config.CHUNK_SIZE
        keys = [(cx, cy) for cx in range(-10, 11, 2) for cy in range(-10, 11, 2)]
        keys += [(round(ring * math.cos(a / 10)), round(ring * math.sin(a / 10)))
                 for a in range(63)]
        count = 0
        seen = set()
        for cx, cy in keys:
            for _, key, x, y in sp.roster(cx, cy):
                seen.add(key)
                count += 1
                biome = world.biome_at(math.floor(x), math.floor(y)).name
                self.assertIn(biome, config.ENEMIES[key].biomes, key)
        self.assertGreater(count, 5)
        self.assertGreaterEqual(len(seen), 5)   # the ring brings in biome specialists

    HALF = (32.0, 13.5)   # a 16:9 view's half-size in tiles

    def _first_populated(self, sp):
        return next((cx, cy) for cx in range(4, 20) for cy in range(-3, 4) if sp.roster(cx, cy))

    def _view_beside(self, x, y):
        """A view center that puts (x, y) just outside the view (to its right),
        well within the wake margin."""
        return x - self.HALF[0] - 6, y

    def test_kills_stay_dead(self):
        world = ChunkedWorld(42)
        sp = Spawner(world, 42)
        key = self._first_populated(sp)
        sp.chunk_loaded(*key)
        sid, name, x, y = sp.rosters[key][0]
        enemies = []
        sp.update(enemies, *self._view_beside(x, y), *self.HALF)
        target = next(e for e in enemies if e.spawn_id == sid)
        target.hp = 0
        enemies.remove(target)
        sp.killed(target)
        sp.update(enemies, 99999, 99999, *self.HALF)      # everything sleeps...
        sp.chunk_loaded(*key)
        sp.update(enemies, *self._view_beside(x, y), *self.HALF)   # ...then back
        self.assertNotIn(sid, [e.spawn_id for e in enemies])

    def test_nothing_spawns_in_view(self):
        world = ChunkedWorld(42)
        sp = Spawner(world, 42)
        key = self._first_populated(sp)
        sp.chunk_loaded(*key)
        _, _, x, y = sp.rosters[key][0]
        enemies = []
        sp.update(enemies, x, y, *self.HALF)               # standing right on it
        hw, hh = self.HALF
        inside = [e for e in enemies if abs(e.x - x) <= hw + 2 and abs(e.y - y) <= hh + 2]
        self.assertEqual(inside, [])                       # (ones beside the view may wake)

    def test_far_half_of_a_chunk_wakes_when_approached(self):
        # Regression: a chunk is generated when its near edge is ~32 tiles
        # out, so enemies in its far half start out beyond the sleep margin.
        # They must still wake once you get close -- previously they were
        # put to sleep immediately and never came back.
        world = ChunkedWorld(42)
        sp = Spawner(world, 42)
        n = config.CHUNK_SIZE
        key = next((cx, 0) for cx in range(4, 40)
                   if any(x - cx * n > n / 2 for _, _, x, _ in sp.roster(cx, 0)))
        sid, _, x, y = next(r for r in sp.roster(*key) if r[2] - key[0] * n > n / 2)
        # View approaching from the west: chunk's near edge at LOAD_MARGIN.
        vx = key[0] * n - self.HALF[0] - config.LOAD_MARGIN
        enemies = []
        sp.chunk_loaded(*key)
        sp.update(enemies, vx, y, *self.HALF)
        while vx < x - self.HALF[0] - 3:                   # drive east
            vx += 0.5
            sp.update(enemies, vx, y, *self.HALF)
        self.assertIn(sid, [e.spawn_id for e in enemies])


class PlayerDeathTest(unittest.TestCase):
    def test_scene_notices_death_and_restarts(self):
        import os
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        from engine import Audio, Display, SceneManager, Settings
        import ascii_adventurers.scenes.game as game

        d = Display(128, 30)
        m = SceneManager(d, Settings(), Audio())
        orig = game.make_world
        game.make_world = lambda seed=None: arena()
        try:
            s = game.GameScene()
            s.manager = m
            s.on_enter()
            s.mouse.left_held = lambda: False
            s.hero.take_damage(999, None, None)
            s.update(DT)
            self.assertTrue(s.player_dead)
            restarted = []
            m.switch_to = lambda scene, **kw: restarted.append(scene)
            import pygame
            s.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_r))
            self.assertEqual(len(restarted), 1)
        finally:
            game.make_world = orig


if __name__ == "__main__":
    unittest.main()
