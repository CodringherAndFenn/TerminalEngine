"""M28.6: worn gear on the hero sprites (design/GEAR.md 22): the head's
shape and tint, the chest's colours, the main hand's accent, the legendary
glint, and the hero on the gear screen."""

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from ascii_adventurers import config, palette
from ascii_adventurers.players.gear import Equipment, Piece
from ascii_adventurers.render import characters, gear_looks
from ascii_adventurers.render.characters import ART, ART_H, ART_W, draw_sparkles
from ascii_adventurers.render.gear_looks import (BODY, CHEST_LOOKS, HEAD_LOOKS, HEADGEAR,
                                                 MAIN_LOOKS, SPARKLE, WEAPON, Look,
                                                 axe_head_color, dress, look_of)
from ascii_adventurers.render.mounts import rider_picture
from ascii_adventurers.tests.test_m16 import game

HEROES = ("wizard", "dwarf", "bard", "princess", "huntress")


def worn(**slots) -> Equipment:
    eq = Equipment()
    for slot, piece in slots.items():
        eq.worn[slot] = piece
    return eq


def in_box(box, x, y):
    x0, y0, x1, y1 = box
    return x0 <= x <= x1 and y0 <= y <= y1


class DataTest(unittest.TestCase):
    def test_every_head_chest_and_main_piece_has_a_look(self):
        for table, slot in ((HEAD_LOOKS, "head"), (CHEST_LOOKS, "chest"), (MAIN_LOOKS, "main")):
            keys = {k for k, g in config.GEAR.items() if g.slot == slot}
            self.assertEqual(set(table), keys, slot)

    def test_every_colour_is_a_sprite_colour(self):
        letters = set(palette.SPRITE_COLORS)
        for spec in HEAD_LOOKS.values():
            self.assertLessEqual(set(spec[1:]) - {" "}, letters, spec)
        for spec in list(CHEST_LOOKS.values()) + list(MAIN_LOOKS.values()):
            self.assertLessEqual(set(spec), letters, spec)

    def test_every_hero_draws_every_shape(self):
        shapes = {spec[0] for spec in HEAD_LOOKS.values()}
        for hero in HEROES:
            self.assertEqual(set(HEADGEAR[hero]), shapes, hero)
            self.assertIn(hero, BODY)
            self.assertIn(hero, WEAPON)
            self.assertEqual(set(SPARKLE[hero]), {"head", "chest", "main"})

    def test_drawings_fit_the_sprite(self):
        for hero in HEROES:
            for shape, (top, rows) in HEADGEAR[hero].items():
                self.assertLessEqual(top + len(rows), ART_H, (hero, shape))
                for line in rows:
                    self.assertEqual(len(line), ART_W, (hero, shape, line))

    def test_main_accents_never_match_the_heros_own(self):
        """A main-hand piece always shows: its colours aren't the weapon's own."""
        for key, colours in MAIN_LOOKS.items():
            for hero in config.CARDS[key].heroes or ():
                own = set(WEAPON[hero][1])
                self.assertFalse(set(colours) <= own, (key, hero))


class DressTest(unittest.TestCase):
    def test_no_look_changes_nothing(self):
        for hero in HEROES:
            self.assertEqual(dress(hero, ART[hero], None), ART[hero])
        self.assertEqual(dress("goblin", ART["goblin"], Look("kindling")), ART["goblin"])

    def test_dressed_rows_are_whole_pictures(self):
        letters = set(palette.SPRITE_COLORS) | {"."}
        for hero in HEROES:
            for k in HEAD_LOOKS:
                rows = dress(hero, ART[hero], Look(k, "phoenix", None))
                self.assertEqual(len(rows), ART_H)
                for row in rows:
                    self.assertEqual(len(row), ART_W)
                    self.assertLessEqual(set(row), letters, (hero, k, row))

    def test_every_head_piece_shows_on_every_hero(self):
        for hero in HEROES:
            seen = set()
            for k in HEAD_LOOKS:
                rows = tuple(dress(hero, ART[hero], Look(head=k)))
                self.assertNotEqual(list(rows), ART[hero], (hero, k))
                seen.add(rows)
            self.assertEqual(len(seen), len(HEAD_LOOKS), hero)     # no two look the same

    def test_head_pieces_keep_the_weapon(self):
        for hero in HEROES:
            box = WEAPON[hero][0]
            for k in HEAD_LOOKS:
                rows = dress(hero, ART[hero], Look(head=k))
                for y, row in enumerate(ART[hero]):
                    for x, ch in enumerate(row):
                        if in_box(box, x, y) and ch != ".":
                            self.assertEqual(rows[y][x], ch, (hero, k, x, y))

    def test_chest_pieces_recolour_the_body_only(self):
        for hero in HEROES:
            light, dark, first = BODY[hero]
            for k, (cl, cd) in CHEST_LOOKS.items():
                rows = dress(hero, ART[hero], Look(chest=k))
                self.assertEqual(rows[:first], ART[hero][:first], (hero, k))
                for y in range(first, ART_H):
                    for x, ch in enumerate(ART[hero][y]):
                        want = cl if ch == light else cd if ch == dark else ch
                        self.assertEqual(rows[y][x], want, (hero, k, x, y))
                if (cl, cd) != (light, dark):
                    self.assertNotEqual(rows, ART[hero], (hero, k))

    def test_main_pieces_recolour_the_weapon(self):
        for key, (light, dark) in MAIN_LOOKS.items():
            for hero in config.CARDS[key].heroes or ():
                box, accent = WEAPON[hero]
                rows = dress(hero, ART[hero], Look(main=key))
                for y, row in enumerate(ART[hero]):
                    for x, ch in enumerate(row):
                        if in_box(box, x, y) and ch in accent:
                            want = light if accent[ch] == "1" else dark
                            self.assertEqual(rows[y][x], want, (key, hero, x, y))
                        else:
                            self.assertEqual(rows[y][x], ch, (key, hero, x, y))

    def test_the_dwarf_and_princess_hold_their_weapons(self):
        """M28.6 drew the dwarf's axe and the princess's wand: the accent
        letters must be there to recolour."""
        for hero in ("dwarf", "princess"):
            box, accent = WEAPON[hero]
            found = [ch for y, row in enumerate(ART[hero]) for x, ch in enumerate(row)
                     if in_box(box, x, y) and ch in accent]
            self.assertTrue(found, hero)


class LookTest(unittest.TestCase):
    def test_look_of_reads_head_chest_and_main(self):
        eq = worn(head=Piece("frostbite", "legendary"), chest=Piece("aegis", "rare"),
                  main=Piece("seeker", "common"), ring1=Piece("volatile", "legendary"))
        look = look_of(eq)
        self.assertEqual((look.head, look.chest, look.main), ("frostbite", "aegis", "seeker"))
        self.assertEqual(look.legend, ("head",))
        self.assertEqual(look.key, "frostbite|aegis|seeker")

    def test_nothing_shown_is_none(self):
        self.assertIsNone(look_of(Equipment()))
        self.assertIsNone(look_of(worn(ring1=Piece("volatile", "rare"))))

    def test_relics_show(self):
        look = look_of(worn(head=Piece("fly_agaric_cap", "legendary"),
                            chest=Piece("lead_apron", "legendary")))
        self.assertEqual((look.head, look.chest, look.legend),
                         ("fly_agaric_cap", "lead_apron", ("head", "chest")))

    def test_the_thrown_axe_takes_the_main_hands_colour(self):
        class Owner:
            look = Look(main="homeward_fury")
        self.assertEqual(axe_head_color(Owner(), (1, 2, 3)), palette.SPRITE_COLORS["r"])
        self.assertEqual(axe_head_color(object(), (1, 2, 3)), (1, 2, 3))
        self.assertEqual(axe_head_color(None, (1, 2, 3)), (1, 2, 3))

    def test_the_rider_wears_it_too(self):
        plain = rider_picture("wizard", "horse", 0, False)
        dressed = rider_picture("wizard", "horse", 0, False, look=Look("kindling"))
        self.assertNotEqual(pygame.image.tobytes(plain, "RGBA"),
                            pygame.image.tobytes(dressed, "RGBA"))


class SparkleTest(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.canvas = pygame.Surface((200, 200))

    def lit(self, look, clock):
        self.canvas.fill((0, 0, 0))
        draw_sparkles(self.canvas, 100, 100, "wizard", 3, False, 0, look, clock)
        ax, ay = SPARKLE["wizard"]["head"]
        x = round(100 - ART_W * 3 / 2 + (ax + 0.5) * 3)
        y = round(100 - ART_H * 3 / 2 + (ay + 0.5) * 3)
        return self.canvas.get_at((x, y))[:3] == characters.SPARKLE_COLOR

    def test_a_legendary_blinks(self):
        look = Look(head="kindling", legend=("head",))
        self.assertTrue(self.lit(look, 0.0))
        self.assertFalse(self.lit(look, characters.SPARKLE_PERIOD / 2))
        self.assertTrue(self.lit(look, characters.SPARKLE_PERIOD * 3))

    def test_no_legendary_no_glint(self):
        self.assertFalse(self.lit(Look(head="kindling"), 0.0))


class GameTest(unittest.TestCase):
    def setUp(self):
        self.m, self.s = game("dwarf")
        self.p = self.s.me

    def test_loadout_sets_the_look(self):
        self.assertIsNone(self.p.hero.look)
        self.p.progress.gear.worn["head"] = Piece("shatter", "legendary")
        self.s._apply_loadout(self.p)
        self.assertEqual(self.p.hero.look, Look(head="shatter", legend=("head",)))
        del self.p.progress.gear.worn["head"]
        self.s._apply_loadout(self.p)
        self.assertIsNone(self.p.hero.look)

    def test_the_world_draws_the_dressed_hero(self):
        self.p.progress.gear.worn["main"] = Piece("cyclone", "legendary")
        self.s._apply_loadout(self.p)
        self.s.quests.banner = None
        self.s.draw(self.m.text)
        self.assertTrue(any(":||cyclone:" in k for k in self.s.sprites._static))

    def test_the_gear_screen_draws_the_hero(self):
        from engine.display import GRID_CLASSIC, GRID_ULTRAWIDE, GRID_WIDE
        self.p.progress.gear.worn["head"] = Piece("lawyers_wig", "legendary")
        self.s._apply_loadout(self.p)
        for grid in (GRID_ULTRAWIDE, GRID_WIDE, GRID_CLASSIC):
            self.m.display.set_grid(*grid)
            self.s._open_gear()
            scr = self.s.overlay
            self.s.draw(self.m.text)
            self.assertTrue(scr._figures, grid)
            col, row, w, h = scr.figure_area()
            for cell, (c, r, bw) in scr._cell_rects().items():
                overlaps = c < col + w and col < c + bw and r < row + h and row < r + 3
                self.assertFalse(overlaps, (grid, cell))
            self.s._set_overlay(None)


class LayoutTest(unittest.TestCase):
    def setUp(self):
        self.m, self.s = game("wizard")
        self.s._open_gear()
        self.scr = self.s.overlay

    def go(self, start, *keys):
        scr = self.scr
        scr.focus = scr.cells().index(start)
        for k in keys:
            scr.handle_event(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=""))
        return scr.cells()[scr.focus]

    def test_the_doll_round_the_hero(self):
        self.assertEqual(self.scr.rows()[:3], [["head", "main"], ["chest", "off"], ["feet"]])
        rects = self.scr._cell_rects()
        self.assertEqual(rects["head"][0], rects["chest"][0])
        self.assertEqual(rects["chest"][0], rects["feet"][0])
        self.assertEqual(rects["main"][0], rects["off"][0])
        self.assertGreater(rects["main"][0], rects["head"][0])

    def test_up_and_down_go_to_the_nearest_box(self):
        self.assertEqual(self.go("head", pygame.K_DOWN), "chest")
        self.assertEqual(self.go("main", pygame.K_DOWN), "off")
        self.assertEqual(self.go("off", pygame.K_DOWN), "feet")
        self.assertEqual(self.go("feet", pygame.K_UP), "chest")
        self.assertEqual(self.go("head", pygame.K_RIGHT), "main")
        self.assertEqual(self.go("feet", pygame.K_DOWN), "ring1")


if __name__ == "__main__":
    unittest.main()
