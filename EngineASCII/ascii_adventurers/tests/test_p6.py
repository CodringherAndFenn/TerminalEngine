"""P6 (playtest pass, 2026-10-10): mounts. Q (gamepad Y) whistles for the
hero's own mount; a second later they ride, 75% faster. Travel only:
attacking or rolling hops off, a hit throws you off (10 s before it comes
again), and there's no riding in a boss arena. The Stable (guild) makes it
faster and back sooner."""

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from ascii_adventurers import config
from ascii_adventurers.meta.guild import Guild
from ascii_adventurers.players.controls import PlayerInput
from ascii_adventurers.render import mounts
from ascii_adventurers.systems import mount
from ascii_adventurers.tests.test_m16 import game
from ascii_adventurers.tests.test_m17 import step, teleport


def press(s, k=pygame.K_q):
    s.handle_event(pygame.event.Event(pygame.KEYDOWN, key=k, unicode="", mod=0))


def ride(s):
    press(s)
    step(s, round(config.MOUNT_CALL_TIME * 60) + 2)
    return s.hero.mount


def drive(s, **kw):
    """From now on the player's input is this (PlayerInput keywords)."""
    s.me.controls.read = lambda *a, **k: PlayerInput(**kw)


class CallTest(unittest.TestCase):
    def test_every_hero_has_their_own(self):
        self.assertEqual(config.HERO_MOUNTS, {"wizard": "carpet", "dwarf": "ram",
                                              "bard": "donkey", "princess": "pony",
                                              "huntress": "stag"})
        for hero, kind in config.HERO_MOUNTS.items():
            m, s = game(hero)
            self.assertEqual(ride(s), kind, hero)
        pygame.mouse.set_visible(True)

    def test_a_second_after_the_whistle(self):
        m, s = game("princess")
        press(s)
        step(s, 30)
        self.assertEqual(s.hero.mount, "")
        self.assertGreater(s.hero.mount_call, 0)
        self.assertEqual(s._meter(s.hero)[0], "MNT")              # the HUD shows the wait
        step(s, 32)
        self.assertEqual(s.hero.mount, "pony")
        self.assertIsNone(s._meter(s.hero))

    def test_seventy_five_percent_faster(self):
        m, s = game("princess")
        ride(s)
        self.assertAlmostEqual(s.hero.mount_mult, 1.75)
        from ascii_adventurers.tests.test_weapons import open_map
        world, h = open_map(w=200), s.hero
        h.x, h.y = 5.5, 10.5
        for _ in range(60):                                      # (open ground: no walls)
            h.move(1.0, 0.0, 1 / 60, world)
        self.assertAlmostEqual(h.vx, config.HEROES["princess"].max_speed * 1.75, places=3)

    def test_the_key_again_hops_off_and_it_comes_straight_back(self):
        m, s = game("huntress")
        ride(s)
        press(s)
        step(s)
        self.assertEqual(s.hero.mount, "")
        self.assertEqual(s.hero.mount_cd, 0.0)
        self.assertEqual(ride(s), "stag")


class TravelOnlyTest(unittest.TestCase):
    def test_attacking_hops_off_and_the_attack_happens(self):
        m, s = game("huntress")
        ride(s)
        drive(s, fire=True)
        step(s)
        self.assertEqual(s.hero.mount, "")
        self.assertTrue(s.projectiles)
        self.assertEqual(s.hero.mount_cd, 0.0)

    def test_rolling_hops_off_and_rolls(self):
        m, s = game("dwarf")
        ride(s)
        drive(s, move_x=1.0, roll=True)
        step(s)
        self.assertEqual(s.hero.mount, "")
        self.assertTrue(s.hero.rolling)

    def test_the_bard_rides_quietly(self):
        m, s = game("bard")
        ride(s)
        beats = s.hero.attacks
        step(s, 120)
        self.assertEqual(s.hero.mount, "donkey")
        self.assertEqual(s.hero.attacks, beats)

    def test_a_hit_throws_you_off(self):
        m, s = game("wizard")
        ride(s)
        s.hero.take_damage(5, None, None)
        step(s)
        self.assertEqual(s.hero.mount, "")
        self.assertAlmostEqual(s.hero.mount_cd, config.MOUNT_THROWN, delta=0.05)
        self.assertEqual(s._meter(s.hero)[0], "MNT")
        press(s)
        step(s, 70)
        self.assertEqual(s.hero.mount, "")                       # not yet
        step(s, round(config.MOUNT_THROWN * 60))
        self.assertEqual(ride(s), "carpet")

    def test_a_hit_while_whistling_calls_it_off(self):
        m, s = game("wizard")
        press(s)
        step(s, 10)
        s.hero.take_damage(5, None, None)
        step(s, 80)
        self.assertEqual(s.hero.mount, "")
        self.assertGreater(s.hero.mount_cd, 0)

    def test_no_riding_in_an_arena(self):
        m, s = game("princess")
        ride(s)
        st = s.quests.states["bad_trip"]
        teleport(s, st.lair.cx, st.lair.cy)
        step(s)
        self.assertEqual(s.hero.mount, "")
        self.assertEqual(ride(s), "")                            # can't call it in here


class SwitchTest(unittest.TestCase):
    def test_mounts_can_be_switched_off(self):
        config.MOUNTS_ON = False
        try:
            m, s = game("princess")
            self.assertEqual(ride(s), "")
        finally:
            config.MOUNTS_ON = True


class StableTest(unittest.TestCase):
    def test_the_stable(self):
        spec = config.GUILD_UPGRADES["stable"]
        self.assertEqual(spec.max_level, 5)
        g = Guild()
        g.guild["stable"] = 5
        m, s = game("princess", guild=g)
        ride(s)
        self.assertAlmostEqual(s.hero.mount_mult, 1.75 + 0.25)
        s.hero.take_damage(5, None, None)
        step(s)
        self.assertAlmostEqual(s.hero.mount_cd, config.MOUNT_MIN_COOLDOWN, delta=0.05)


class DrawTest(unittest.TestCase):
    def test_every_rider_draws_both_ways(self):
        for hero, kind in config.HERO_MOUNTS.items():
            m, s = game(hero)
            ride(s)
            for left in (False, True):
                s.hero.mount_left = left
                s.draw(m.text)
            for frame in (0, 1):
                img = mounts.rider_picture(hero, kind, frame, hurt=frame == 1)
                self.assertEqual(img.get_width(), mounts.MOUNT_W)
        pygame.mouse.set_visible(True)

    def test_it_faces_the_way_it_goes_not_the_aim(self):
        m, s = game("huntress")
        ride(s)
        drive(s, move_x=-1.0, aim=(s.hero.x + 20, s.hero.y))
        step(s, 10)
        self.assertTrue(s.hero.mount_left)
        self.assertFalse(s.hero.facing_left)                     # (she still aims right)

    def test_the_rider_shows_head_and_body(self):
        img = mounts.rider_picture("princess", "pony", 1, False)
        # Her crown (row 0 of her picture) isn't cut off by the bob.
        crown = pygame.Color(*config_color("y"))
        self.assertTrue(any(img.get_at((x, 0)) == crown or img.get_at((x, 1)) == crown
                            for x in range(img.get_width())))


def config_color(letter):
    from ascii_adventurers import palette
    return palette.SPRITE_COLORS[letter]


if __name__ == "__main__":
    unittest.main()
