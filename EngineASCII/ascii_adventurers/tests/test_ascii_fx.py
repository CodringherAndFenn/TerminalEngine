import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from engine import Display, TextRenderer

from ascii_adventurers import config
from ascii_adventurers.engine_ext.camera import Camera
from ascii_adventurers.entities.character import Character
from ascii_adventurers.entities.effects import DURATIONS, Effect
from ascii_adventurers.entities.projectile import Projectile
from ascii_adventurers.render import ascii_fx
from ascii_adventurers.systems import combat
from ascii_adventurers.world.test_map import TestMap


class AsciiFxTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.display = Display(60, 20)
        cls.text = TextRenderer(cls.display)
        cls.camera = Camera(60, 17, cls.display.cell_w, cls.display.cell_h)
        cls.camera.center_on(15.0, 8.0)
        cls.world = TestMap(["." * 40] * 20)

    def test_every_weapon_has_a_shot_look(self):
        for name, w in config.WEAPONS.items():
            self.assertIn(w.shell.look, ascii_fx.SHOT_LOOKS, name)

    def test_shots_draw_in_every_direction(self):
        for name, w in config.WEAPONS.items():
            for k in range(16):
                p = Projectile(15.0, 8.0, k * 3.14159 / 8, w.shell)
                p.travelled = 2.0
                ascii_fx.draw_projectiles(self.text, self.camera, [p])

    def test_every_effect_kind_draws_through_its_life(self):
        for kind in DURATIONS:
            for t in (0.0, 0.3, 0.6, 0.99):
                e = Effect(kind, 15.0, 8.0, 0.7, t=t * DURATIONS[kind], value=12)
                ascii_fx.draw_effects(self.text, self.camera, self.world, [e])

    def test_hits_spawn_damage_numbers(self):
        hero = Character(config.HEROES[config.START_HERO], 20.5, 5.5)
        p = Projectile(10.5, 5.5, 0.0, config.WEAPONS["goblin_bow"].shell)
        effects = []
        combat.update_projectiles([p], self.world, effects, 1.0, [hero])
        numbers = [e for e in effects if e.kind == "number"]
        self.assertEqual(len(numbers), 1)
        self.assertEqual(numbers[0].value, config.WEAPONS["goblin_bow"].shell.damage)
        self.assertTrue(numbers[0].player)

    def test_hp_bar(self):
        for frac in (1.0, 0.6, 0.01):
            ascii_fx.draw_hp_bar(self.text, 100, 100, frac)


if __name__ == "__main__":
    unittest.main()
