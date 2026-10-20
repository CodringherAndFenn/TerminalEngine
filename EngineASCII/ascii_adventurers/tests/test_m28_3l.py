"""M28.3l: the princess's and the bard's main hands' legendary tricks
(design/GEAR.md 19.10). With these, all 100 pieces have one."""

import math
import os
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.players import gear
from ascii_adventurers.render.ascii_fx import draw_projectiles
from ascii_adventurers.render.spell_fx import draw_summons
from ascii_adventurers.systems import combat, spells
from ascii_adventurers.systems.zones import Zone, update_zones
from ascii_adventurers.tests.test_m28_2a import foe
from ascii_adventurers.tests.test_m28_2c import DT
from ascii_adventurers.tests.test_m28_2h import movable, victims
from ascii_adventurers.tests.test_m28_2i import BARD, STRIKE, _Main
from ascii_adventurers.tests.test_m28_3c import BASE, _Legend

PIECES = ("prism", "focus", "spectrum", "point_blank", "converge", "crescendo", "lullaby",
          "syncopation", "dissonance", "sheet_music")


class _Hand(_Legend):
    color, hit, fly, fan, beat, extra = (_Main.color, _Main.hit, _Main.fly, _Main.fan,
                                         _Main.beat, _Main.extra)

    def setup(self, key, rarity="legendary", *more):
        return super().setup(key, rarity, *more, hero="bard" if key in BARD else "princess")

    def fire(self):
        s, h = self.s, self.h
        before = len(s.projectiles)
        combat.fire(h, s.world, s.projectiles, s.effects, actors=s._actors())
        return s.projectiles[before:]


class FrameworkTest(unittest.TestCase):
    def test_every_princess_and_bard_main_hand_has_its_legendary_trick(self):
        hands = [k for k, g in config.GEAR.items() if g.slot == "main"
                 and config.CARDS[k].heroes in (("princess",), ("bard",))]
        self.assertEqual(sorted(hands), sorted(PIECES + ("refraction", "grand_finale")))
        for key in PIECES:
            name, text = gear.legendary_trick(key)
            self.assertTrue(name and text and text.isascii(), key)

    def test_all_100_pieces_have_their_legendary_trick(self):
        self.assertEqual(set(config.GEAR_LEGENDARY), set(config.GEAR))
        for key in config.GEAR:
            flags = [f for f, _, _ in gear.trick_flags(key, 0, "legendary")]
            self.assertIn(f"{key}+L", flags, key)


class OverlapTest(_Hand):
    def test_a_split_piece_counts_and_gets_the_bonus(self):
        for rarity, counts in (("legendary", True), ("epic", False)):
            s, h = self.setup("prism", rarity)
            a = self.place(foe(24.0, 20.5, BASE))[0]
            group = {}
            self.hit(self.color(0, group), a)
            piece = combat._child(self.color(1, group), 24.0, 20.5, 0.0, 0.5)
            self.assertEqual(piece.group is group, counts, rarity)
            if counts:
                self.assertAlmostEqual(self.extra(piece, a), h.stats.prism * 1)

    def test_all_the_shots_of_one_attack_count_together(self):
        s, h = self.setup("prism")
        first = self.fan()
        more = self.fan()                                 # (a pattern's volley, say)
        s.rules.overlap(s.me, first + more)
        self.assertTrue(all(q.group is first[0].group for q in first + more))
        a = self.place(foe(24.0, 20.5, BASE))[0]
        self.hit(first[0], a)
        self.assertAlmostEqual(self.extra(more[0], a), h.stats.prism)   # (the other volley's)
        s, h = self.setup("prism", "epic")
        first, more = self.fan(), self.fan()
        s.rules.overlap(s.me, first + more)
        self.assertIsNot(first[0].group, more[0].group)


class AutofocusTest(_Hand):
    def width(self, rarity, *foes):
        s, h = self.setup("focus", rarity)
        self.place(*foes)
        shots = self.fire()
        angles = [q.angle for q in shots]
        return max(angles) - min(angles), h

    def test_one_enemy_in_front_is_a_line(self):
        w, _ = self.width("legendary", foe(26.0, 20.5, BASE))
        self.assertAlmostEqual(w, 0.0)

    def test_a_crowd_opens_it_to_its_full_width(self):
        crowd = [foe(26.0, 20.5 + k * 0.8, BASE) for k in (-1, 0, 1)]
        w, h = self.width("legendary", *crowd)
        full = math.radians(h.weapon.spec.spread_deg / h.stats.spread_mult)
        self.assertAlmostEqual(w, full)
        focused, _ = self.width("legendary")                   # (nobody: Focus's width)
        self.assertAlmostEqual(focused, math.radians(h.weapon.spec.spread_deg))

    def test_not_behind_you_nor_without_the_trick(self):
        w, h = self.width("legendary", foe(14.0, 20.5, BASE))
        self.assertAlmostEqual(w, math.radians(h.weapon.spec.spread_deg))
        w, h = self.width("epic", foe(26.0, 20.5, BASE))
        self.assertAlmostEqual(w, math.radians(h.weapon.spec.spread_deg))


class UltravioletTest(_Hand):
    def test_a_sixth_color_that_bleeds(self):
        s, h = self.setup("spectrum")
        shots = self.fire()
        self.assertEqual(len(shots), 6)
        self.assertEqual([q.violet for q in shots], [False] * 5 + [True])
        a = self.place(foe(24.0, 20.5, BASE))[0]
        h.rng.random = lambda: 0.0                             # (every status roll lands)
        self.hit(shots[-1], a)
        self.assertTrue(a.status.has("bleed"))
        draw_projectiles(s.manager.text, s.me.camera, shots)

    def test_five_without_the_trick(self):
        s, h = self.setup("spectrum", "epic")
        self.assertEqual(len(self.fire()), 5)


class LungeTest(_Hand):
    def lunge(self, rarity, x=26.0):
        s, h = self.setup("point_blank", rarity)
        e = self.place(foe(x, 20.5, BASE))[0]
        h.aim_point = (e.x, e.y)
        s.rules.lunge(s.me)
        return h, e

    def test_an_attack_carries_you_toward_the_aimed_enemy(self):
        h, e = self.lunge("legendary")
        self.assertAlmostEqual(h.x - 20.5, config.LUNGE[0], places=3)

    def test_never_into_it_nor_without_the_trick(self):
        s, h = self.setup("point_blank")
        gap = foe(0, 0).hit_radius + h.hit_radius + config.LUNGE[1]
        h, e = self.lunge("legendary", x=20.5 + gap + 0.2)            # (only 0.2 to go)
        self.assertAlmostEqual(e.x - h.x, gap, places=3)
        h, e = self.lunge("epic")
        self.assertEqual(h.x, 20.5)


class BurnInTest(_Hand):
    def cross(self, rarity):
        s, h = self.setup("converge", rarity)
        h.aim_point = (26.0, 20.5)
        shots = self.fan()
        self.fly(shots, 0.4)
        return s, h, [z for z in s.zones if z.kind == "burn_in"]

    def test_the_crossing_glows(self):
        s, h, glows = self.cross("legendary")
        self.assertEqual(len(glows), 1)                       # (once a shot)
        z = glows[0]
        self.assertAlmostEqual(z.x, 26.0, places=1)
        life, every, share = config.BURN_IN
        self.assertEqual((z.life, z.every), (life, every))
        shell = config.WEAPONS["rainbow"].shell
        self.assertAlmostEqual(z.damage, shell.damage * 5 * share)
        draw_summons(s.manager.text, s.me.camera, s.players, s.zones, 3)

    def test_it_burns_what_stands_there(self):
        s, h = self.setup("converge")
        a = self.place(foe(26.0, 20.5, BASE))[0]
        s.zones.append(Zone("burn_in", 26.0, 20.5, config.FOCAL_POINT[0], config.BURN_IN[0],
                            config.BURN_IN[1], 8.0, h))
        with mock.patch(STRIKE) as hit:
            for _ in range(round(config.BURN_IN[0] * 60) + 10):
                update_zones(s.zones, s._actors(), s.effects, DT, s.world)
        # (a zone ticks as it's laid, then every BURN_IN[1] s to its end)
        self.assertEqual(victims(hit), [a] * (round(config.BURN_IN[0] / config.BURN_IN[1]) + 1))

    def test_not_without_the_trick(self):
        self.assertEqual(self.cross("epic")[2], [])


class TuttiTest(_Hand):
    def bonus(self, rarity, **kw):
        s, h = self.setup("crescendo", rarity)
        h.streak = 3
        a = self.place(foe(24.0, 20.5, BASE))[0]
        h.spelling = kw.get("spelling", False)
        before = a.hp
        combat.strike(a, 10.0, h, 0.0, s.effects, pet=kw.get("pet", False), can_crit=False)
        h.spelling = False
        return before - a.hp

    def test_spells_and_summons_get_the_crescendo(self):
        plain = self.bonus("legendary")
        self.assertGreater(self.bonus("legendary", spelling=True), plain)
        self.assertGreater(self.bonus("legendary", pet=True), self.bonus("epic", pet=True))
        self.assertAlmostEqual(self.bonus("epic", spelling=True), self.bonus("epic"))

    def test_a_spells_statuses_are_stronger_too(self):
        from ascii_adventurers.systems.statuses import inflict
        powers = []
        for spelling in (True, False):
            s, h = self.setup("crescendo")
            h.streak, h.spelling = 3, spelling
            a = self.place(foe(24.0, 20.5, BASE))[0]
            inflict(a, "burn", h)
            h.spelling = False
            powers.append(a.status.active["burn"].power)
        self.assertAlmostEqual(powers[0] / powers[1], 1 + 3 * config.CRESCENDO_STEP)

    def test_a_spells_shots_and_ground_are_marked(self):
        s, h = self.setup("crescendo", "legendary", ("fire_wand", 0))
        st = s.me.spells["fire_wand"]
        self.place(foe(24.0, 20.5, BASE))
        st.timer = 0.0
        spells.update_spells(h, s.me.spells, s.world, s._actors(), s.effects, DT, s.projectiles,
                             s.zones)
        bolts = [q for q in s.projectiles if q.owner is h]
        self.assertTrue(bolts and all(q.spell for q in bolts))
        self.assertFalse(h.spelling)


class SerenadeTest(_Hand):
    def healed(self, rarity, far):
        s, h = self.setup("lullaby", rarity)
        self.place(foe(20.5 + h.weapon.spec.reach * far, 20.5, BASE))
        h.hp = h.max_hp / 2
        hp = h.hp
        self.beat()
        return h.hp - hp

    def test_enemies_near_the_beat_count_hit_or_not(self):
        per = config.LULLABY_HEAL[0]
        self.assertAlmostEqual(self.healed("legendary", 1.6), per)      # (out of the beat's reach)
        self.assertAlmostEqual(self.healed("legendary", config.SERENADE + 0.5), 0.0)
        self.assertAlmostEqual(self.healed("epic", 1.6), 0.0)


class RubatoTest(_Hand):
    def beats(self, rarity, held):
        s, h = self.setup("syncopation", rarity)
        h.trigger = held
        return [s.rules.attack_mods(s.me)["mult"] for _ in range(4)]

    def test_held_is_loud_and_let_go_is_soft(self):
        loud, soft = config.SYNCOPATION[0][1], config.SYNCOPATION[1][1]
        self.assertEqual(self.beats("legendary", True), [loud] * 4)
        self.assertEqual(self.beats("legendary", False), [soft] * 4)

    def test_in_turn_without_the_trick(self):
        self.assertEqual(len(set(self.beats("epic", True))), 2)


class UndertowTest(_Hand):
    def moved(self, rarity, beat):
        s, h = self.setup("dissonance", rarity)
        a = self.place(movable(24.0, 20.5))[0]
        h.attacks = beat - 1
        with mock.patch(STRIKE):
            self.beat()
        return a.x - 24.0, a

    def test_every_3rd_beat_pulls_in_and_chills(self):
        dx, a = self.moved("legendary", config.UNDERTOW)
        self.assertAlmostEqual(dx, -config.DISSONANCE_PUSH, places=2)
        self.assertTrue(a.status.has("chill"))
        dx, _ = self.moved("legendary", config.UNDERTOW + 1)
        self.assertGreater(dx, 0)

    def test_it_pushes_without_the_trick(self):
        self.assertGreater(self.moved("epic", config.UNDERTOW)[0], 0)

    def test_never_past_the_bard(self):
        s, h = self.setup("dissonance")
        touch = movable(0, 0).hit_radius + h.hit_radius
        a = self.place(movable(20.5 + touch + 0.1, 20.5))[0]          # (0.1 from touching)
        h.attacks = config.UNDERTOW - 1
        with mock.patch(STRIKE):
            self.beat()
        self.assertAlmostEqual(a.x - h.x, touch, places=3)


class EarwormTest(_Hand):
    def note(self, rarity, n=1):
        s, h = self.setup("sheet_music", rarity)
        a = self.place(foe(24.0, 20.5, BASE))[0]
        for _ in range(n):
            p = self.color()
            p.spec = config.SPELL_SHELLS["note"]
            with mock.patch(STRIKE, return_value=0.0):
                self.hit(p, a)
        return a, h

    def test_notes_soften_the_enemy_for_your_beats(self):
        per, seconds, most = config.EARWORM
        a, h = self.note("legendary", 2)
        self.assertAlmostEqual(combat.earworm(a, h), 1 + 2 * per)
        a, h = self.note("legendary", most + 3)
        self.assertAlmostEqual(combat.earworm(a, h), 1 + most * per)
        h.time += seconds + 0.1
        self.assertEqual(combat.earworm(a, h), 1.0)

    def test_the_beat_hits_harder(self):
        a, h = self.note("legendary", 2)
        with mock.patch(STRIKE, return_value=0.0) as hit:
            self.beat()
        self.assertAlmostEqual(hit.call_args.kwargs["mult"], 1 + 2 * config.EARWORM[0])

    def test_not_without_the_trick(self):
        a, h = self.note("epic", 2)
        self.assertEqual(combat.earworm(a, h), 1.0)


if __name__ == "__main__":
    unittest.main()
