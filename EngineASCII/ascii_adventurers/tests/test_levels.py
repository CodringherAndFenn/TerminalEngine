import random
import unittest

from ascii_adventurers import config
from ascii_adventurers.ai import make_enemy
from ascii_adventurers.players.progress import Progress, xp_for_level


class EnemyScalingTest(unittest.TestCase):
    def test_hp_and_damage_grow_with_the_level(self):
        base = make_enemy("goblin_archer", 5.5, 5.5, random.Random(1))
        self.assertEqual(base.damage_mult, config.ENEMY_DAMAGE_MULTIPLIER)
        e = make_enemy("goblin_archer", 5.5, 5.5, random.Random(1))
        e.scale_to_level(51)
        hp = config.ENEMIES["goblin_archer"].max_hp
        self.assertEqual(e.max_hp, round(hp * (1 + 50 * config.ENEMY_HP_PER_LEVEL)))
        self.assertEqual(e.hp, e.max_hp)
        self.assertAlmostEqual(e.damage_mult, config.ENEMY_DAMAGE_MULTIPLIER
                               * (1 + 50 * config.ENEMY_DAMAGE_PER_LEVEL))
        top = make_enemy("ogre", 5.5, 5.5, random.Random(1))
        top.scale_to_level(10_000)                          # capped at MAX_LEVEL
        self.assertEqual(top.level, config.MAX_LEVEL)

    def test_scaled_damage_reaches_the_player(self):
        from ascii_adventurers.entities.character import Character
        from ascii_adventurers.systems import combat
        from ascii_adventurers.tests.test_weapons import open_map, fly
        world = open_map()
        hero = Character(config.HEROES["wizard"], 20.5, 10.5)
        archer = make_enemy("goblin_archer", 10.5, 10.5, random.Random(1))
        archer.scale_to_level(51)
        archer.aim_angle = 0.0
        shots = []
        combat.fire(archer, world, shots, [],
                    damage=archer.weapon.spec.shell.damage * archer.damage_mult)
        fly(shots, world, [hero], [], seconds=3.0)
        dmg = (config.WEAPONS["goblin_bow"].shell.damage * config.ENEMY_DAMAGE_MULTIPLIER
               * (1 + 50 * config.ENEMY_DAMAGE_PER_LEVEL))
        self.assertAlmostEqual(hero.max_hp - hero.hp, dmg)


class MaxLevelTest(unittest.TestCase):
    def test_levels_stop_at_the_cap(self):
        p = Progress()
        total = sum(xp_for_level(n) for n in range(1, config.MAX_LEVEL))
        gained = p.add(total + 10_000)
        self.assertEqual(p.level, config.MAX_LEVEL)
        self.assertEqual(gained, config.MAX_LEVEL - 1)
        self.assertEqual(p.picks, config.MAX_LEVEL - 1)
        self.assertEqual(p.add(10_000), 0)
        self.assertEqual(p.frac, 1.0)                       # the bar shows full


class SpawnerLevelTest(unittest.TestCase):
    def test_woken_enemies_follow_the_highest_human_level(self):
        import os
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        from ascii_adventurers.tests.test_players import make_manager, start_game
        m = make_manager(ghosts=1)
        s = start_game(m, seed=77, hero="dwarf")
        s.players[1].progress.level = 60                    # a ghost: doesn't count
        s.me.progress.level = 20
        s.update(1 / 60)
        self.assertEqual(s.spawner.level, 20)
        import pygame
        pygame.mouse.set_visible(True)


if __name__ == "__main__":
    unittest.main()
