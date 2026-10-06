"""M24.4: the painted figures (the Frost Hermit, Fragile, Mr. Buttons) and
Mr. Buttons riding on his carrier's head."""

import math
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from ascii_adventurers import config
from ascii_adventurers.ai import make_enemy
from ascii_adventurers.render import painted
from ascii_adventurers.render.characters import ART
from ascii_adventurers.render.sprites import _paint_full
from ascii_adventurers.tests.test_m17 import game, step, teleport
from ascii_adventurers.tests.test_m22_5 import finish

POSES = {"snow_king": ("", "cast", "down"), "fragile": ("", "twirl", "raise", "bare"),
         "fragile_wolf": ("", "howl"), "fragile_crying": ("", "hug"), "fragile_hugging": ("",),
         "mr_buttons": ("",), "nettle": ("", "cast", "dive")}            # (M25.1)


def paint(name, scale, flip=False, frame=0, hurt=False, pose=""):
    """The figure painted on its sprite canvas, and the canvas' reach box."""
    reach = painted.PAINTED[name].reach * scale
    surf, span_c, span_r = _paint_full(painted.painter(name, scale, flip, frame, hurt, pose),
                                       reach, 10, 24)
    return surf


class PaintedFigureTest(unittest.TestCase):
    def test_every_pose_paints_inside_its_reach(self):
        # Nothing is cut off at the sprite's edge, in any pose, frame or facing.
        self.assertEqual(set(POSES), set(painted.PAINTED))
        for name, poses in POSES.items():
            for pose in poses:
                for frame in range(4):
                    for flip in (False, True):
                        surf = paint(name, 6, flip, frame, False, pose)
                        r = surf.get_bounding_rect()
                        self.assertGreater(r.w * r.h, 100, (name, pose))
                        w, h = surf.get_size()
                        self.assertTrue(r.left > 0 and r.top > 0 and r.right < w and r.bottom < h,
                                        (name, pose, frame, flip, r, (w, h)))

    def test_facing_left_is_the_mirror_image(self):
        a = paint("snow_king", 6, False)
        b = paint("snow_king", 6, True)
        ra, rb = a.get_bounding_rect(), b.get_bounding_rect()
        self.assertEqual((ra.w, ra.h), (rb.w, rb.h))
        cx = a.get_width() / 2
        self.assertAlmostEqual(ra.centerx - cx, -(rb.centerx - cx), delta=2)

    def test_a_hit_washes_it_white(self):
        def light(surf):
            r = surf.get_bounding_rect()
            px = [surf.get_at((x, y)) for x in range(r.left, r.right, 2)
                  for y in range(r.top, r.bottom, 2)]
            px = [p for p in px if p.a > 200]
            return sum(p.r + p.g + p.b for p in px) / len(px)
        self.assertGreater(light(paint("fragile", 6, hurt=True)), light(paint("fragile", 6)) + 60)

    def test_the_old_pictures_are_gone(self):
        for name in ("snow_king", "fragile", "fragile_crying", "fragile_wolf"):
            self.assertNotIn(name, ART)

    def test_the_crown_still_comes_off_and_draws(self):
        m, s = game(seed=31)
        b = make_enemy("snow_king", s.hero.x + 6, s.hero.y, random.Random(1))
        s.enemies.append(b)
        b.crown_on = False
        b.crown[:4] = [b.x - 3, b.y + 2, 0.0, 0.0]
        s.draw(m.text)
        b.crown_on = True
        b.tell = ("cast",)
        s.draw(m.text)


class WalkedTest(unittest.TestCase):
    def test_a_boss_counts_the_tiles_it_moves(self):
        m, s = game(seed=31)
        b = make_enemy("fragile", s.hero.x + 8, s.hero.y, random.Random(1))
        s.enemies.append(b)
        self.assertEqual(b.walked, 0.0)
        step(s, 1)
        before = b.walked
        b.x += 1.5
        step(s, 1)
        self.assertAlmostEqual(b.walked - before, 1.5, delta=0.6)


class BearRiderTest(unittest.TestCase):
    def head_pixels(self, m, s):
        """The canvas just above the hero's head (where the bear sits)."""
        x, y = s.me.camera.world_to_px(s.hero.x, s.hero.y)
        canvas = m.display.canvas
        top = y - ART_TOP_PX - 22
        return [tuple(canvas.get_at((round(x) + dx, round(top) + dy)))
                for dx in range(-8, 9, 2) for dy in range(0, 18, 2)]

    def test_the_bear_sits_on_his_carriers_head(self):
        m, s = game(seed=31)
        st = s.quests.states["pawn_dealer"]
        st.stage = "awake"
        s.hero.invulnerable = True
        st.bear = None
        s.draw(m.text)
        bare = self.head_pixels(m, s)
        st.bear = s.me.index
        s.draw(m.text)
        worn = self.head_pixels(m, s)
        self.assertNotEqual(bare, worn)
        fur = config_color("fur")
        self.assertTrue(any(_near(p[:3], fur) for p in worn))
        self.assertFalse(any(_near(p[:3], fur) for p in bare))

    def test_she_hugs_him_once_he_is_given_back(self):
        m, s = game(seed=31)
        q = s.quests
        st = q.states["pawn_dealer"]
        finish(q, "pawn_dealer")
        st.bear = s.me.index
        s.hero.invulnerable = True
        teleport(s, st.lair.cx + 20, st.lair.cy + 6)
        step(s, 2)
        st.boss.hp = 0.0
        st.boss.last_hit_by = s.hero
        step(s, 2)
        self.assertEqual(st.crying.sprite, "fragile_crying")
        q.talk(st.crying, s.me)
        self.assertTrue(st.gifted)
        self.assertEqual(st.crying.sprite, "fragile_hugging")
        s.draw(m.text)                                     # (and she draws)


def config_color(key):
    from ascii_adventurers import palette
    return palette.MR_BUTTONS[key]


def _near(a, b, tol=12):
    return all(abs(x - y) <= tol for x, y in zip(a, b))


# The wizard's picture reaches this far above his centre (its first row).
ART_TOP_PX = (9 - next(r for r, row in enumerate(ART["wizard"]) if row.strip("."))) * 3


if __name__ == "__main__":
    unittest.main()
