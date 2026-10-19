"""M28.2i: the princess's and the bard's main hands' +3 / +6 / +9 tricks
(design/GEAR.md 17.9)."""

import math
import os
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.entities.effects import Effect
from ascii_adventurers.entities.projectile import Projectile
from ascii_adventurers.players import gear
from ascii_adventurers.render.ascii_fx import draw_effects, draw_projectiles
from ascii_adventurers.render.spell_fx import draw_statuses
from ascii_adventurers.systems import combat
from ascii_adventurers.systems.statuses import inflict, statuses_of
from ascii_adventurers.systems.zones import update_zones
from ascii_adventurers.tests.test_m28_2a import foe
from ascii_adventurers.tests.test_m28_2c import DT, _Case
from ascii_adventurers.tests.test_m28_2h import movable, victims

BASE = 1000.0
STRIKE = "ascii_adventurers.systems.combat.strike"
BARD = ("crescendo", "lullaby", "syncopation", "dissonance", "grand_finale", "sheet_music")


class _Main(_Case):
    def setup(self, key, level, walls=()):
        hero = "bard" if key in BARD else "princess"
        s, h = super().setup(key, level, hero, walls)
        h.time = 100.0
        return s, h

    def color(self, variant=0, group=None, x=None, y=None, angle=0.0, damage=8.0):
        h = self.h
        p = Projectile(h.x + 1.0 if x is None else x, h.y if y is None else y, angle,
                       config.WEAPONS["rainbow"].shell, owner=h, damage=damage)
        p.tags, p.variant, p.group = ("projectile", "arcane"), variant, group
        return p

    def hit(self, p, victim, spawned=None):
        s = self.s
        return combat._hit_actor(p, victim, victim.x, victim.y, s.world, s._actors(), s.effects,
                                 [] if spawned is None else spawned, s.zones, s.projectiles)

    def fly(self, shots, seconds):
        s = self.s
        for _ in range(round(seconds * 60)):
            self.h.time += DT
            combat.update_projectiles(shots, s.world, s.effects, DT, s._actors(), s.zones)
            update_zones(s.zones, s._actors(), s.effects, DT, s.world)

    def fan(self, n=5, spread=34.0):
        """The princess's fan, fired from her hand along her aim."""
        s, h = self.s, self.h
        before = len(s.projectiles)
        combat.volley(h, s.world, s.projectiles, s.effects, h.aim_angle, n, spread,
                      config.WEAPONS["rainbow"].shell, ("projectile", "arcane"),
                      actors=s._actors())
        return s.projectiles[before:]

    def beat(self, mult=1.0, reach_mult=1.0):
        s, h = self.s, self.h
        h.attacks += 1
        return combat.pulse(h, s.world, s._actors(), s.effects, mult, reach_mult)

    def extra(self, p, victim):
        """Bucket A the hit got (what _hit_actor passed strike)."""
        with mock.patch(STRIKE, return_value=0.0) as hit:
            self.hit(p, victim)
        return hit.call_args.kwargs["extra"]


class FrameworkTest(unittest.TestCase):
    def test_every_princess_and_bard_main_hand_has_three_tricks(self):
        keys = [k for k, g in config.GEAR.items() if g.slot == "main"
                and config.CARDS[k].heroes in (("princess",), ("bard",))]
        self.assertEqual(len(keys), 12)
        for key in keys:
            self.assertEqual([t for t, _, _ in gear.tricks(key)], [3, 6, 9], key)
            for _, name, text in gear.tricks(key):
                self.assertTrue(name and text and text.isascii(), key)

    def test_all_100_pieces_have_their_300_tricks(self):
        self.assertEqual(set(config.GEAR_TRICKS), set(config.GEAR))
        self.assertEqual(sum(len(gear.tricks(k)) for k in config.GEAR), 300)


class DrawTest(_Main):
    def test_every_trick_draws(self):
        s, h = self.setup("lullaby", 3)
        a, b = self.place(foe(24.0, 20.5, BASE), foe(26.0, 22.0, BASE))
        statuses_of(a).asleep = 2.0
        h.duelist = b
        s.effects.append(Effect("beam", h.x, h.y, 0.0, x2=h.x + 12, y2=h.y + 3))
        s.projectiles.append(self.color())
        for _ in range(15):
            s.steps += 1
            for e in s.effects:
                e.t += DT
            draw_projectiles(s.manager.text, s.me.camera, s.projectiles)
            draw_effects(s.manager.text, s.me.camera, s.world, s.effects)
            draw_statuses(s.manager.text, s.me.camera, s.enemies, [], [b])


class PrismaticTest(_Main):
    def test_full_spectrum(self):
        s, h = self.setup("prism", 3)
        self.assertEqual(self.fan()[0].group["colors"], 5)
        a = self.place(foe(24.0, 20.5, BASE))[0]
        group = {"colors": 5}
        crits = []
        for v in range(5):
            with mock.patch(STRIKE, return_value=0.0) as hit:
                self.hit(self.color(v, group), a)
            crits.append(hit.call_args.kwargs["sure_crit"])
        self.assertEqual(crits, [False] * 4 + [True])
        s, h = self.setup("prism", 2)
        self.assertNotIn("colors", self.fan()[0].group)
        self.assertEqual(self.fan(n=3)[0].group, {})

    def test_afterglow(self):
        s, h = self.setup("prism", 6)
        a = self.place(foe(24.0, 20.5, BASE))[0]
        first, second = {}, {}
        for v in range(5):
            self.extra(self.color(v, first), a)
        bonus = self.extra(self.color(0, second), a)
        self.assertAlmostEqual(bonus, h.stats.prism * 4, places=6)
        self.assertAlmostEqual(self.extra(self.color(1, second), a), bonus)
        h.time += config.AFTERGLOW + 0.1                  # (gone after a second)
        self.assertAlmostEqual(self.extra(self.color(0, {}), a), 0.0)
        s, h = self.setup("prism", 3)
        a = self.place(foe(24.0, 20.5, BASE))[0]
        for v in range(5):
            self.extra(self.color(v, first), a)
        self.assertAlmostEqual(self.extra(self.color(0, {}), a), 0.0)

    def test_rainbows_end(self):
        for level, per in ((9, config.RAINBOWS_END), (6, 1.0)):
            s, h = self.setup("prism", level)
            a = self.place(foe(24.0, 20.5, BASE))[0]
            g = {}
            self.extra(self.color(0, g), a)
            got = self.extra(self.color(1, g), a)
            self.assertAlmostEqual(got, h.stats.prism * per, places=6)


class SpyglassTest(_Main):
    def test_lens(self):
        s, h = self.setup("focus", 3)
        self.assertEqual([q.middle for q in self.fan()], [False, False, True, False, False])
        a = self.place(foe(24.0, 20.5, BASE))[0]
        middle = self.color()
        middle.middle = True
        self.assertAlmostEqual(self.extra(middle, a) - self.extra(self.color(), a), config.LENS)
        s, h = self.setup("focus", 2)
        self.assertFalse(any(q.middle for q in self.fan()))

    def test_pinpoint(self):
        s, h = self.setup("focus", 6)
        shell = h.weapon.spec.shell
        for still, x in ((0.0, 1.0), (1.0, 0.75), (5.0, config.PINPOINT[1])):
            h.still_t = still
            self.assertAlmostEqual(combat._pinpoint(h, shell), x)
        s, h = self.setup("focus", 3)
        h.still_t = 5.0
        self.assertEqual(combat._pinpoint(h, h.weapon.spec.shell), 1.0)

    def test_beam(self):
        for level, still, beam in ((9, 1.0, True), (9, 0.5, False), (6, 3.0, False)):
            s, h = self.setup("focus", level)
            h.still_t = still
            foes = self.place(*(foe(23.0 + 2 * k, 20.5, BASE) for k in range(3)))
            combat.attack(h, s.world, s.projectiles, s.effects, s._actors())
            shots = list(s.projectiles)
            self.assertEqual(len(shots), 5)
            self.assertEqual(all(q.beam for q in shots), beam, (level, still))
            self.assertEqual(any(e.kind == "beam" for e in s.effects), beam)
            if not beam:
                continue
            self.assertTrue(all(q.angle == h.aim_angle for q in shots))
            with mock.patch(STRIKE, return_value=0.0) as hit:
                self.fly(shots, 0.1)
            for a in foes:                               # every color on every one
                self.assertEqual(victims(hit).count(a), 5)


class ChromaTest(_Main):
    def test_saturated(self):
        for level, burns in ((3, True), (2, False)):
            s, h = self.setup("spectrum", level)
            a = self.place(foe(24.0, 20.5, BASE))[0]
            h.rng.random = lambda: 0.25
            combat._card_effects(self.color(0), a, h, h.stats)
            self.assertEqual(a.status is not None and a.status.has("burn"), burns, level)

    def test_color_theory(self):
        for level, two, bonus in ((6, True, config.COLOR_THEORY[1]), (6, False, 0.0),
                                  (3, True, 0.0)):
            s, h = self.setup("spectrum", level)
            a = self.place(foe(30.0, 20.5, BASE))[0]
            inflict(a, "burn", h)
            if two:
                inflict(a, "poison", h)
            got = combat.situational_bonus(h.stats, h, a)
            self.assertAlmostEqual(got, bonus, msg=(level, two))
        s, h = self.setup("spectrum", 6)
        a = self.place(foe(30.0, 20.5, BASE))[0]
        inflict(a, "burn", h)
        statuses_of(a).frozen, statuses_of(a).frozen_by = 1.0, h     # (frozen counts as chill)
        self.assertEqual(combat._colors_on(a, h), 2)

    def test_chromatic(self):
        for level, stacks in ((9, config.CHROMATIC), (6, 1)):
            s, h = self.setup("spectrum", level)
            a = self.place(foe(24.0, 20.5, BASE))[0]
            h.rng.random = lambda: 0.0
            combat._card_effects(self.color(0), a, h, h.stats)
            self.assertEqual(a.status.stacks("burn"), stacks)


class DuelistTest(_Main):
    def test_face_to_face(self):
        s, h = self.setup("point_blank", 3)
        near, mid = foe(22.0, 20.5), foe(23.5, 20.5)
        pb = h.stats.point_blank
        self.assertAlmostEqual(combat._point_blank(h.stats, h, near), pb + config.FACE_TO_FACE[1])
        self.assertAlmostEqual(combat._point_blank(h.stats, h, mid), pb)
        s, h = self.setup("point_blank", 2)
        self.assertAlmostEqual(combat._point_blank(h.stats, h, near), h.stats.point_blank)

    def test_duel(self):
        s, h = self.setup("point_blank", 6)
        far, near, other = self.place(foe(30.0, 20.5, BASE), foe(23.0, 20.5, BASE),
                                      foe(22.0, 21.5, BASE))
        combat.strike(far, 10.0, h, 0.0, [])
        self.assertIsNone(h.duelist)                      # (not up close)
        combat.strike(near, 10.0, h, 0.0, [])
        combat.strike(other, 10.0, h, 0.0, [])
        self.assertIs(h.duelist, near)                    # (the first one)
        near.x = 35.0                                     # (wherever it goes)
        self.assertAlmostEqual(combat._point_blank(h.stats, h, near), config.DUEL[0])
        h.hp = h.max_hp
        mine = h.take_damage(20.0, near, None)
        h.hp = h.max_hp
        theirs = h.take_damage(20.0, other, None)
        self.assertAlmostEqual(mine / theirs, config.DUEL[1])
        near.hp = 0.0
        s.rules.tick(s.me, DT)
        self.assertIsNone(h.duelist)
        combat.strike(other, 10.0, h, 0.0, [])
        self.assertIs(h.duelist, other)                   # (a new duel)
        s, h = self.setup("point_blank", 3)
        a = self.place(foe(23.0, 20.5, BASE))[0]
        combat.strike(a, 10.0, h, 0.0, [])
        self.assertIsNone(h.duelist)

    def test_bladework(self):
        for level, bonus in ((9, config.BLADEWORK[1]), (6, 0.0)):
            s, h = self.setup("point_blank", level)
            a = foe(25.5, 20.5)                           # (5 tiles off)
            got = combat._point_blank(h.stats, h, a)
            self.assertAlmostEqual(got, h.stats.point_blank * bonus, msg=level)


class KaleidoTest(_Main):
    def test_shards_of_light(self):
        for level, aimed in ((3, True), (2, False)):
            s, h = self.setup("refraction", level)
            a, b, c = self.place(foe(24.0, 20.5, BASE), foe(26.0, 24.5, BASE),
                                 foe(25.0, 16.5, BASE))
            spawned = []
            with mock.patch(STRIKE, return_value=0.0):
                self.hit(self.color(), a, spawned)
            self.assertEqual(len(spawned), config.REFRACTION_SPLIT)
            want = sorted(round(math.atan2(e.y - a.y, e.x - a.x), 3) for e in (b, c))
            got = sorted(round(q.angle, 3) for q in spawned)
            self.assertEqual(all(w in got for w in want), aimed, level)

    def test_radiant_split(self):
        for level, grow in ((6, config.RADIANT_SPLIT), (3, 0.0)):
            s, h = self.setup("refraction", level)
            a = self.place(foe(24.0, 20.5, BASE))[0]
            p, spawned = self.color(), []
            p.size = 0.1
            with mock.patch(STRIKE, return_value=0.0):
                self.hit(p, a, spawned)
            self.assertTrue(all(abs(q.size - 0.1 - grow) < 1e-9 for q in spawned), level)

    def test_infinite_mirror(self):
        for level, refracted, pieces in ((9, 1, 2), (9, 3, 2), (9, 4, 0), (6, 1, 0)):
            s, h = self.setup("refraction", level)
            a = self.place(foe(24.0, 20.5, BASE))[0]
            p, spawned = self.color(), []
            p.child, p.refracted = True, refracted
            with mock.patch(STRIKE, return_value=0.0):
                self.hit(p, a, spawned)
            self.assertEqual(len(spawned), pieces, (level, refracted))
            self.assertTrue(all(q.refracted == refracted + 1 for q in spawned))


class CrossbeamTest(_Main):
    def setup(self, key, level, walls=()):
        s, h = super().setup(key, level, walls)
        h.aim_point = (25.5, 20.5)
        return s, h

    def test_focal_point(self):
        s, h = self.setup("converge", 3)
        shots = self.fan()
        self.assertTrue(all(q.focal and abs(q.focal[0][0] - 25.5) < 0.6 for q in shots))
        at, off = self.place(foe(25.5, 20.5, BASE), foe(29.0, 20.5, BASE))
        p = shots[0]
        self.assertAlmostEqual(self.extra(p, at) - self.extra(p, off), config.FOCAL_POINT[1])
        s, h = self.setup("converge", 2)
        p = self.fan()[0]
        at = self.place(foe(25.5, 20.5, BASE))[0]
        self.assertAlmostEqual(self.extra(p, at), 0.0)

    def crossings(self, level):
        s, h = self.setup("converge", level)
        p = self.fan()[0]                                 # (an outer color)
        my = p.origin[1]
        side, xs = None, []
        for _ in range(40):
            x0, y0 = p.x, p.y
            combat.update_projectiles([p], s.world, s.effects, DT, [], s.zones)
            now = math.copysign(1, p.y - my)
            if side is None:
                side = now                                # (it leaves from on the line)
            elif now != side:                             # (where along the step it crossed)
                xs.append(x0 + (p.x - x0) * (my - y0) / (p.y - y0) - p.origin[0])
                side = now
            if not p.alive:
                break
        return xs

    def test_second_crossing(self):
        first = self.crossings(3)
        self.assertEqual(len(first), 1)
        twice = self.crossings(6)
        self.assertEqual(len(twice), 2)
        # (within a step of flight: Converge's bend turns a step at a time)
        self.assertAlmostEqual(twice[1] - twice[0], config.SECOND_CROSSING, delta=0.6)

    def test_lockstep(self):
        hits = {}
        for level in (9, 6):
            s, h = self.setup("converge", level)
            a = self.place(foe(26.0, 22.3, BASE))[0]      # (off the aim line, nearest it)
            shots = self.fan()
            self.assertEqual(shots[0].lock is a, level == 9)
            with mock.patch(STRIKE, return_value=0.0) as hit:
                self.fly(shots, 0.6)
            hits[level] = victims(hit).count(a)
        self.assertEqual(hits[9], 5)
        self.assertLess(hits[6], 5)


class FortissimoTest(_Main):
    def test_fermata(self):
        for level, left in ((3, 2), (2, 0)):
            s, h = self.setup("crescendo", level)
            h.streak = 3
            self.beat()                                   # (nobody near: a miss)
            self.assertEqual(h.streak, left, level)

    def test_climax(self):
        for level, streak, reached in ((6, 5, True), (6, 4, False), (3, 5, False)):
            s, h = self.setup("crescendo", level)
            reach = h.weapon.spec.reach
            a = self.place(foe(h.x + reach * 1.15, 20.5, BASE))[0]
            h.streak = streak
            with mock.patch(STRIKE, return_value=0.0) as hit:
                self.beat()
            self.assertEqual(a in victims(hit), reached, (level, streak))

    def test_forte(self):
        for level, top in ((9, config.FORTE), (6, config.CRESCENDO_MAX)):
            s, h = self.setup("crescendo", level)
            self.place(foe(22.0, 20.5, BASE))
            h.streak = config.FORTE - 1
            self.beat()
            self.assertEqual(h.streak, top, level)


class CradlesongTest(_Main):
    def test_lullabied(self):
        s, h = self.setup("lullaby", 3)
        a = self.place(movable(22.0, 20.5, 10 ** 6))[0]
        for _ in range(config.LULLABIED[0] - 1):
            self.beat()
        self.assertFalse(a.status is not None and a.status.asleep > 0)
        self.beat()
        self.assertAlmostEqual(a.status.asleep, config.LULLABIED[1])
        self.assertEqual(a.status.time_scale, 0.0)
        self.beat()                                       # (a beat doesn't wake it)
        self.assertGreater(a.status.asleep, 0)
        combat.strike(a, 5.0, h, 0.0, [])                 # (anything else does)
        self.assertEqual(a.status.asleep, 0.0)
        # Beats in a row: one missed resets the count.
        s, h = self.setup("lullaby", 3)
        a = self.place(movable(22.0, 20.5, 10 ** 6))[0]
        for k in range(config.LULLABIED[0] + 1):
            if k == 2:
                h.attacks += 1                            # (a beat that missed it)
                continue
            self.beat()
        self.assertEqual(a.status.asleep, 0.0)
        for level, boss in ((2, False), (3, True)):       # (bosses don't sleep)
            s, h = self.setup("lullaby", level)
            a = self.place(movable(22.0, 20.5, 10 ** 6))[0]
            a.boss = boss
            for _ in range(config.LULLABIED[0]):
                self.beat()
            self.assertFalse(a.status is not None and a.status.asleep > 0)

    def test_nothing_wasted(self):
        for level, kept in ((6, 3.0), (3, 0.0)):
            s, h = self.setup("lullaby", level)
            self.place(*(foe(22.0, 19.5 + k, BASE) for k in range(3)))
            h.hp = h.max_hp
            self.beat()
            self.assertEqual(h.unspent, kept, level)
            with mock.patch(STRIKE, return_value=0.0) as hit:
                self.beat()
            self.assertAlmostEqual(hit.call_args.kwargs["extra"], config.NOTHING_WASTED * kept)

    def test_mothers_song(self):
        for level, healed in ((9, config.MOTHERS_SONG[1]), (6, config.LULLABY_HEAL[1])):
            s, h = self.setup("lullaby", level)
            self.place(*(foe(22.0 + k % 4, 19.0 + k // 4, BASE) for k in range(12)))
            h.hp = h.max_hp - 50
            self.beat()
            self.assertAlmostEqual(h.hp, h.max_hp - 50 + healed, msg=level)


class OffbeatTest(_Main):
    def test_swing(self):
        for level, n, cut in ((3, 1, True), (3, 2, False), (2, 1, False)):
            s, h = self.setup("syncopation", level)
            h.attacks = n - 1
            h.weapon.cooldown = 1.0
            s.rules.attack_mods(s.me)
            want = 1.0 - h.weapon.spec.fire_interval * config.SWING_BEAT if cut else 1.0
            self.assertAlmostEqual(h.weapon.cooldown, want, msg=(level, n))

    def test_polyrhythm(self):
        reach = None
        for level, n, rings in ((6, 3, 2), (6, 4, 1), (3, 3, 1)):
            s, h = self.setup("syncopation", level)
            reach = h.weapon.spec.reach
            h.attacks = n - 1
            s._attack(s.me)
            sizes = sorted(round(e.size, 2) for e in s.effects if e.kind == "pulse")
            self.assertEqual(len(sizes), rings, (level, n))
        want = sorted(round(reach * r, 2) for r, _ in config.SYNCOPATION)
        s, h = self.setup("syncopation", 6)
        h.attacks = 2
        s._attack(s.me)
        self.assertEqual(sorted(round(e.size, 2) for e in s.effects if e.kind == "pulse"), want)

    def test_the_drop(self):
        for level, loud in ((9, config.THE_DROP), (6, config.SYNCOPATION[0][1])):
            s, h = self.setup("syncopation", level)
            h.attacks = 1                                 # (beat 2: a loud one)
            self.assertAlmostEqual(s.rules.attack_mods(s.me)["mult"], loud)


class SourstringTest(_Main):
    def test_clash(self):
        walls = [(23, y) for y in range(15, 26)]
        for level, wall, clash in ((3, True, True), (3, False, False), (2, True, False)):
            s, h = self.setup("dissonance", level, walls=walls if wall else ())
            self.place(movable(22.4, 20.5, BASE))
            with mock.patch(STRIKE, return_value=0.0) as hit:
                self.beat()
            bases = [c.args[1] for c in hit.call_args_list]
            self.assertEqual(config.CLASH in bases, clash, (level, wall))

    def test_tritone(self):
        for level, chilled, far in ((6, True, config.TRITONE), (6, False, 1.0), (3, True, 1.0)):
            s, h = self.setup("dissonance", level)
            a = self.place(movable(22.0, 20.5, BASE))[0]
            if chilled:
                inflict(a, "chill", h)
            x = a.x
            with mock.patch(STRIKE, return_value=0.0):
                self.beat()
            self.assertAlmostEqual(a.x - x, config.DISSONANCE_PUSH * far, places=3,
                                   msg=(level, chilled))

    def test_shriek(self):
        for level, stacks in ((9, config.SHRIEK), (6, 1)):
            s, h = self.setup("dissonance", level)
            a = self.place(movable(22.0, 20.5, BASE))[0]
            with mock.patch(STRIKE, return_value=0.0):
                self.beat()
            self.assertEqual(a.status.stacks("chill"), stacks)


class ShowstopperTest(_Main):
    def test_overture(self):
        for level, quiet, finale in ((3, 6.0, True), (3, 1.0, False), (2, 6.0, False)):
            s, h = self.setup("grand_finale", level)
            h.attacks = 0
            h.beat_hit = h.time - quiet
            kw = s.rules.attack_mods(s.me)
            self.assertEqual(kw["mult"] == config.GRAND_FINALE[1], finale, (level, quiet))
        s, h = self.setup("grand_finale", 3)
        self.place(foe(22.0, 20.5, BASE))
        self.beat()
        self.assertEqual(h.beat_hit, h.time)              # (a beat that hit)

    def test_curtain_call(self):
        for level, rings in ((6, 1), (3, 0)):
            s, h = self.setup("grand_finale", level)
            h.hp = h.max_hp
            s.rules.tick(s.me, DT)
            h.hp = h.max_hp * 0.25
            s.rules.tick(s.me, DT)
            pulses = [e for e in s.effects if e.kind == "pulse"]
            self.assertEqual(len(pulses), rings, level)
            if rings:
                self.assertAlmostEqual(pulses[0].size,
                                       h.weapon.spec.reach * config.GRAND_FINALE[2])
                h.hp = h.max_hp                           # (up and down again: too soon)
                s.rules.tick(s.me, DT)
                h.hp = h.max_hp * 0.25
                s.rules.tick(s.me, DT)
                self.assertEqual(len([e for e in s.effects if e.kind == "pulse"]), 1)
                h.time += config.CURTAIN_CALL[1]
                h.hp = h.max_hp
                s.rules.tick(s.me, DT)
                h.hp = h.max_hp * 0.25
                s.rules.tick(s.me, DT)
                self.assertEqual(len([e for e in s.effects if e.kind == "pulse"]), 2)

    def test_magnum_opus(self):
        for level, finale in ((9, True), (6, False)):
            s, h = self.setup("grand_finale", level)
            h.beat_hit = h.time
            h.attacks = config.MAGNUM_OPUS - 1
            kw = s.rules.attack_mods(s.me)
            self.assertEqual(kw["mult"] == config.GRAND_FINALE[1], finale, level)


class SongbirdTest(_Main):
    def notes(self, s):
        return [q for q in s.projectiles if q.spec.look == "note"]

    def test_birdsong(self):
        walls = [(24, y) for y in range(17, 25)]
        for level, found in ((3, True), (2, False)):
            s, h = self.setup("sheet_music", level, walls=walls)
            a = self.place(foe(27.5, 20.5, BASE))[0]      # (behind the wall)
            self.assertEqual(s.rules._note_targets(h) == [a], found, level)
            if not found:
                continue
            way = s.rules._ways[id(a)]
            self.assertGreater(len(way), 1)
            s.rules.patterns(s.me, s.rules.attack_mods(s.me))
            notes = [q for q in self.notes(s) if q.bird is a]
            self.assertTrue(notes)
            with mock.patch(STRIKE, return_value=0.0) as hit:
                self.fly(notes, 1.5)
            self.assertIn(a, victims(hit))

    def test_chorus(self):
        for level, n, twice in ((6, 4, True), (6, 5, False), (3, 4, False)):
            s, h = self.setup("sheet_music", level)
            self.place(foe(24.0, 20.5, BASE))
            h.attacks = n - 1
            s.rules.patterns(s.me, s.rules.attack_mods(s.me))
            count = config.SHEET_MUSIC + round(h.stats.pellets)
            self.assertEqual(len(self.notes(s)), count * (2 if twice else 1), (level, n))

    def test_aria(self):
        for level, splash in ((9, True), (6, False)):
            s, h = self.setup("sheet_music", level)
            a, b = self.place(foe(24.0, 20.5, BASE), foe(24.0, 21.4, BASE))
            p = Projectile(23.0, 20.5, 0.0, config.SPELL_SHELLS["note"], owner=h, damage=9.0)
            with mock.patch(STRIKE, return_value=0.0) as hit:
                self.hit(p, a)
            self.assertEqual(b in victims(hit), splash, level)
        s, h = self.setup("sheet_music", 9, walls=[(25, y) for y in range(15, 26)])
        b = self.place(foe(24.4, 21.0, BASE))[0]
        p = Projectile(23.0, 20.0, 0.0, config.SPELL_SHELLS["note"], owner=h, damage=9.0)
        with mock.patch(STRIKE, return_value=0.0) as hit:
            self.fly([p], 0.3)                            # (on the wall, by b)
        self.assertIn(b, victims(hit))


if __name__ == "__main__":
    unittest.main()
