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
            if w.kind == "shot":
                self.assertIn(w.shell.look, ascii_fx.SHOT_LOOKS, name)
            else:
                self.assertIsNone(w.shell, name)

    def test_shots_draw_in_every_direction(self):
        for name, w in config.WEAPONS.items():
            if w.shell is None:
                continue
            for k in range(16):
                p = Projectile(15.0, 8.0, k * 3.14159 / 8, w.shell)
                p.travelled = 2.0
                p.variant = k                    # every rainbow color too
                ascii_fx.draw_projectiles(self.text, self.camera, [p])

    def test_every_effect_kind_draws_through_its_life(self):
        for kind in DURATIONS:
            for t in (0.0, 0.3, 0.6, 0.99):
                e = Effect(kind, 15.0, 8.0, 0.7, t=t * DURATIONS[kind], value=12,
                           x2=19.0, y2=10.0, size=3.0)
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


class SlashTest(unittest.TestCase):
    def test_every_frame_draws_at_every_angle_and_is_cached(self):
        import math as _m
        from engine import Display, TextRenderer
        from ascii_adventurers.engine_ext.camera import Camera
        from ascii_adventurers.render import slash
        from ascii_adventurers.render.sprites import SpriteBank

        d = Display(128, 30)
        text = TextRenderer(d)
        bank = SpriteBank(text, config.CELLS_PER_TILE)
        cam = Camera(128, 27, d.cell_w, d.cell_h)
        cam.center_on(20.0, 10.0)
        spec = config.WEAPONS["sword"]
        for k in range(slash.ANGLE_STEPS):
            for f in range(slash.FRAMES):
                e = Effect("swing", 20.0, 10.0, k * _m.tau / slash.ANGLE_STEPS,
                           t=(f + 0.5) / slash.FRAMES * DURATIONS["swing"],
                           size=spec.reach, value=round(spec.arc_deg))
                d.canvas.fill((0, 0, 0))
                slash.draw_slashes(bank, cam, [e])
                self.assertGreater(d.canvas.get_bounding_rect(min_alpha=0).width, 0)
                self.assertGreater(len(set(d.canvas.get_at((x, y))[:3] for x in range(0, 1280, 7)
                                           for y in range(0, 720, 7))), 1)   # something drawn
        cached = bank.sprites_cached
        slash.draw_slashes(bank, cam, [e])                   # same again: no new bake
        self.assertEqual(bank.sprites_cached, cached)
