import math
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from engine import Audio, Display, SceneManager

from ascii_adventurers import config
from ascii_adventurers.app import App
from ascii_adventurers.engine_ext import gamepads
from ascii_adventurers.engine_ext.gamepads import Gamepads, Pad
from ascii_adventurers.meta.records import Records
from ascii_adventurers.meta.settings import GameSettings
from ascii_adventurers.players.controls import AutoControls, Controls, PadControls, PlayerInput

STEP = 1 / config.SIM_HZ


class FakeDevice:
    """Stands in for an SDL controller: axes (-32767..32767) and buttons."""

    def __init__(self):
        self.axes = {}
        self.buttons = set()

    def get_axis(self, a):
        return self.axes.get(a, 0)

    def get_button(self, b):
        return b in self.buttons


class Scripted(Controls):
    """Deterministic input from the step number alone."""

    def __init__(self):
        super().__init__()
        self.n = 0

    def read(self, hero, camera, world, enemies=()):
        self.n += 1
        a = self.n * 0.01
        return PlayerInput(math.cos(a), math.sin(a * 0.7),
                           (hero.x + math.cos(a * 3), hero.y + math.sin(a * 3)), self.n % 40 < 25)


def make(key, x, y, seed=1):
    import random
    from ascii_adventurers.ai import make_enemy
    return make_enemy(key, x, y, random.Random(seed))


def make_manager(ghosts=0):
    d = Display(128, 30)
    m = SceneManager(d, GameSettings(), Audio())
    m.app = App(m.audio, GameSettings(), Records(), persist=False, ghosts=ghosts)
    m.app.records.save = lambda *a: None
    m.switch_to = lambda scene, **kw: m._set_scene(scene)
    return m


def start_game(m, seed=321, hero="wizard"):
    from ascii_adventurers.scenes.game import GameScene
    s = GameScene(hero, seed)
    m._set_scene(s)
    return s


class FixedClockTest(unittest.TestCase):
    def tearDown(self):
        pygame.mouse.set_visible(True)

    def run_with(self, frame_times, steps):
        m = make_manager()
        s = start_game(m)
        s.me.controls = Scripted()
        for dt in frame_times:
            if s.steps >= steps:
                break
            s.update(dt)
        self.assertEqual(s.steps, steps)
        h = s.hero
        foes = sorted((e.spawn_id, round(e.x, 9), round(e.y, 9), round(e.hp, 6)) for e in s.enemies)
        self.woke = max(getattr(self, "woke", 0), len(foes))
        return (round(h.x, 9), round(h.y, 9), round(h.aim_angle, 9), round(h.hp, 6),
                len(s.projectiles), s.stats.total_kills, foes)

    def test_same_inputs_same_game_at_any_frame_rate(self):
        n = 1200  # twenty seconds: far enough out that enemies wake and fight
        at60 = self.run_with([1 / 60] * 2 * n, n)
        at144 = self.run_with([1 / 144] * 4 * n, n)
        jitter = self.run_with([(1 / 60) * f for f in (0.4, 1.9, 1.0, 0.7, 1.3, 1.1)] * n, n)
        self.assertGreater(self.woke, 0, "the test run never met an enemy")
        self.assertEqual(at60, at144)
        self.assertEqual(at60, jitter)

    def test_steps_follow_real_time_and_hitches_are_capped(self):
        m = make_manager()
        s = start_game(m)
        for _ in range(144):
            s.update(1 / 144)            # one second at 144 Hz
        self.assertAlmostEqual(s.steps, config.SIM_HZ, delta=1)
        before = s.steps
        s.update(2.0)                    # a 2 s hitch
        self.assertEqual(s.steps - before, config.MAX_STEPS_PER_FRAME)

    def test_drawing_blends_between_steps_and_restores_positions(self):
        m = make_manager()
        s = start_game(m)
        s.hero.vx = 0.0
        s.me.controls = Scripted()
        s.update(STEP)
        s.update(STEP * 0.5)            # half a step pending
        self.assertAlmostEqual(s.alpha, 0.5, places=6)
        prev, cur = s.hero.prev_pos, (s.hero.x, s.hero.y)
        seen = []
        orig = s._draw
        s._draw = lambda text: (seen.append((s.hero.x, s.hero.y)), orig(text))
        s.draw(m.text)
        mid = ((prev[0] + cur[0]) / 2, (prev[1] + cur[1]) / 2)
        self.assertAlmostEqual(seen[0][0], mid[0], places=9)
        self.assertAlmostEqual(seen[0][1], mid[1], places=9)
        self.assertEqual((s.hero.x, s.hero.y), cur)     # restored after drawing


class MultiPlayerWorldTest(unittest.TestCase):
    def tearDown(self):
        pygame.mouse.set_visible(True)

    def test_world_and_enemies_live_around_a_far_away_player(self):
        m = make_manager(ghosts=1)
        s = start_game(m)
        self.assertEqual(len(s.players), 2)
        ghost = s.players[1]
        self.assertTrue(ghost.ghost and ghost.hero.invulnerable)
        # Send the ghost far off into the ring (it'll stream its own area).
        lay = s.world.layout
        gx, gy = (lay.plains_radius + 300) * 0.8, 0.0
        ghost.hero.x, ghost.hero.y = gx, gy
        ghost.camera.center_on(gx, gy)
        for _ in range(240):
            s.update(STEP)
        n = config.CHUNK_SIZE
        self.assertTrue(s.world.is_generated(math.floor(ghost.hero.x), math.floor(ghost.hero.y)))
        self.assertTrue(s.world.is_generated(math.floor(s.hero.x), math.floor(s.hero.y)))
        near_ghost = [e for e in s.enemies
                      if math.hypot(e.x - ghost.hero.x, e.y - ghost.hero.y) < 80]
        self.assertTrue(near_ghost, "no enemies woke around the far-away player")
        s.draw(m.text)                   # minimap / markers with two players

    def test_enemies_target_the_nearest_hero_and_stick_to_it(self):
        from ascii_adventurers.ai.brain import AIContext
        from ascii_adventurers.entities.character import Character
        from ascii_adventurers.tests.test_enemies import arena

        world = arena()
        a = Character(config.HEROES["wizard"], 10.5, 10.5)
        b = Character(config.HEROES["bard"], 30.5, 10.5)
        e = make("goblin_archer", 25.5, 10.5)
        ctx = AIContext(world, [a, b], [a, b, e], [], [])
        e.sense(ctx, 0.01)
        self.assertIs(e.target, b)                  # nearest
        e.x = 19.0                                  # now a is a bit closer...
        e.sense(ctx, 0.01)
        self.assertIs(e.target, b)                  # ...but not enough to switch
        e.x = 12.0
        e.sense(ctx, 0.01)
        self.assertIs(e.target, a)
        b.hp = 0
        a.hp = 0
        e.sense(ctx, 0.01)
        self.assertIsNone(e.target)

    def test_kill_goes_to_the_player_who_hit_last(self):
        m = make_manager(ghosts=1)
        s = start_game(m)
        e = make("goblin_archer", s.hero.x + 3, s.hero.y)
        s.enemies.append(e)
        e.take_damage(999, s.players[1].hero, 0.0)   # the ghost lands the blow
        s.update(STEP)
        self.assertEqual(s.players[1].stats.total_kills, 1)
        self.assertEqual(s.stats.total_kills, 0)

    def test_game_over_only_when_every_human_has_fallen(self):
        m = make_manager(ghosts=1)
        s = start_game(m)
        s.hero.take_damage(999, None, None)
        for _ in range(int(1.2 / STEP)):
            s.update(STEP)
        self.assertTrue(s.player_dead)
        self.assertGreaterEqual(s.game_over_for, 1.0)   # the ghost doesn't count
        self.assertIsNotNone(s.overlay)


class ControlsTest(unittest.TestCase):
    def setUp(self):
        self.display = Display(128, 30)
        from ascii_adventurers.engine_ext.camera import Camera
        from ascii_adventurers.entities.character import Character
        from ascii_adventurers.engine_ext.input import Mouse
        self.hero = Character(config.HEROES["dwarf"], 50.0, 50.0)
        self.camera = Camera(128, 27, 10, 24)
        self.camera.center_on(50.0, 50.0)
        self.mouse = Mouse(self.display)

    def pad(self):
        dev = FakeDevice()
        return dev, Pad(dev, 7)

    def test_twin_stick(self):
        dev, pad = self.pad()
        pc = PadControls(pad)
        dev.axes[gamepads.AXIS_LX] = 32767
        inp = pc.read(self.hero, self.camera, None)
        self.assertAlmostEqual(inp.move_x, 1.0)
        self.assertEqual(inp.aim, (50.0 + config.PAD_AIM_DISTANCE, 50.0))  # faces the walk
        dev.axes[gamepads.AXIS_LX] = 0
        dev.axes[gamepads.AXIS_RY] = -32767              # aim up
        inp = pc.read(self.hero, self.camera, None)
        self.assertEqual((inp.move_x, inp.move_y), (0.0, 0.0))
        self.assertAlmostEqual(inp.aim[1], 50.0 - config.PAD_AIM_DISTANCE)
        dev.axes[gamepads.AXIS_RY] = 0                   # let go: keeps aiming up
        self.assertAlmostEqual(pc.read(self.hero, self.camera, None).aim[1],
                               50.0 - config.PAD_AIM_DISTANCE)
        self.assertFalse(pc.read(self.hero, self.camera, None).fire)
        dev.axes[gamepads.AXIS_RT] = 30000
        self.assertTrue(pc.read(self.hero, self.camera, None).fire)

    def test_deadzone(self):
        dev, pad = self.pad()
        dev.axes[gamepads.AXIS_LX] = int(32767 * gamepads.STICK_DEADZONE * 0.9)
        self.assertEqual(pad.left_stick(), (0.0, 0.0))

    def test_fire_blocked_until_released(self):
        dev, pad = self.pad()
        pc = PadControls(pad)
        dev.buttons.add(gamepads.BUTTON_RB)
        pc.block_fire()
        self.assertFalse(pc.read(self.hero, self.camera, None).fire)
        dev.buttons.clear()
        self.assertFalse(pc.read(self.hero, self.camera, None).fire)
        dev.buttons.add(gamepads.BUTTON_RB)
        self.assertTrue(pc.read(self.hero, self.camera, None).fire)

    def test_auto_switches_to_the_pad_when_it_is_used(self):
        pads = Gamepads()
        dev, pad = self.pad()
        pads.pads = [pad]
        auto = AutoControls(self.mouse, pads)
        self.assertTrue(auto.uses_mouse)
        dev.axes[gamepads.AXIS_RX] = 32767
        inp = auto.read(self.hero, self.camera, None)
        self.assertFalse(auto.uses_mouse)
        self.assertEqual(inp.aim, (50.0 + config.PAD_AIM_DISTANCE, 50.0))


class PadMenuTest(unittest.TestCase):
    def test_buttons_and_stick_become_menu_keys(self):
        pads = Gamepads()
        dev = FakeDevice()
        pads.pads = [Pad(dev, 3)]
        ev = pygame.event.Event(gamepads.EV_BUTTON, button=gamepads.BUTTON_START, instance_id=3)
        self.assertEqual([e.key for e in pads.menu_keys(ev)], [pygame.K_ESCAPE])
        a = pygame.event.Event(gamepads.EV_BUTTON,
                               button=getattr(pygame, "CONTROLLER_BUTTON_A"), instance_id=3)
        self.assertEqual([e.key for e in pads.menu_keys(a)], [pygame.K_RETURN])

        def axis(v):
            return pads.menu_keys(pygame.event.Event(gamepads.EV_AXIS, axis=gamepads.AXIS_LY,
                                                     value=int(v * 32767), instance_id=3))
        self.assertEqual([e.key for e in axis(0.9)], [pygame.K_DOWN])
        self.assertEqual(axis(0.95), [])          # held: no repeat
        self.assertEqual(axis(0.1), [])           # back to centre
        self.assertEqual([e.key for e in axis(-0.8)], [pygame.K_UP])

    def test_in_play_only_start_and_back_reach_the_game(self):
        from ascii_adventurers.scenes.common import app_events
        m = make_manager()
        a = pygame.event.Event(gamepads.EV_BUTTON,
                               button=getattr(pygame, "CONTROLLER_BUTTON_A"), instance_id=1)
        start = pygame.event.Event(gamepads.EV_BUTTON, button=gamepads.BUTTON_START, instance_id=1)
        self.assertEqual(app_events(m, a, menu=False), [])
        self.assertEqual([e.key for e in app_events(m, start, menu=False)], [pygame.K_ESCAPE])
        self.assertEqual([e.key for e in app_events(m, a, menu=True)], [pygame.K_RETURN])


if __name__ == "__main__":
    unittest.main()
