"""M33.2: the Fossil Angel's form 2, the first angel unveils (design/FINALS.md
9.2): the unveiling (its bones fall, it can't be hit while its flesh grows
back, 18,000 of 15,000), its four signatures (eyes in the flesh, life from
its blood, red amber, six wings) and its four moves (claw rake, the first
word, blood rain, halo wheels)."""

import math
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.ai import KINDS
from ascii_adventurers.ai.first_angel import AngelEye, BloodDrop
from ascii_adventurers.ai.fossil_angel import FossilAngel
from ascii_adventurers.render import finals_art  # noqa: F401
from ascii_adventurers.render.characters import ART
from ascii_adventurers.tests.test_m33_1 import DT, angel, force, run, until
from ascii_adventurers.tests.test_p7 import Arena, enemy
from ascii_adventurers.world import tiles


def unveiled(a, ar):
    """Fell its bones and wait out the unveiling: the first angel."""
    a.take_damage(a.hp + 10, ar.hero, 0.0)
    run(ar, config.FOSSIL_UNVEIL + DT * 3)
    a._rest = 99.0


def recruiter(ar, made):
    def recruit(key, x, y):
        e = enemy(key, x, y, len(ar.enemies))
        ar.enemies.append(e)
        made.append(e)
        return e
    return recruit


class CatalogTest(unittest.TestCase):
    def test_form_2(self):
        b = config.BOSSES["fossil_angel_unveiled"]
        self.assertEqual([ph.below for ph in b.phases], [1.0, 0.75, 0.5, 0.25])
        moves = [{m for m, _ in ph.moves} for ph in b.phases]
        for ph in moves:
            self.assertTrue({"rake", "word", "rain", "wheels", "feathers"} <= ph)
        self.assertNotIn("walls", moves[1])
        self.assertIn("walls", moves[2])
        self.assertEqual(round(15000 * config.FOSSIL_UNVEILED_HP), 18000)    # (user)
        keys = list(config.BOSSES)                          # (the relic seeds stay)
        self.assertEqual(keys.index("fossil_angel_unveiled"), keys.index("fossil_angel") + 1)
        pages = config.BOSSES["fossil_angel"].pages
        for key in ("angel_eye", "blood_drop"):
            self.assertIn(key, config.BESTIARY)
            self.assertIn(key, pages)
        self.assertIs(KINDS["blood_drop"], BloodDrop)
        for name in ("fossil_angel_flesh", "fossil_angel_flesh_beat", "flesh_wing", "flesh_wing_up",
                     "blood_drop"):
            self.assertEqual(len(ART[name]), 18, name)
            self.assertTrue(all(len(r) == 14 for r in ART[name]), name)
        self.assertTrue(tiles.RED_AMBER.solid and tiles.RED_AMBER.blocks_shots)
        self.assertFalse(tiles.RED_RESIN.solid)
        self.assertNotIn("~", "".join(tiles.RESIN.glyphs))    # (VT323 draws "~" like "N")

    def test_its_eyes_stand_out_past_its_body(self):
        r = config.FOSSIL_UNVEILED_HIT_RADIUS
        for dx, dy in config.FOSSIL_EYE_SLOTS:               # (else a shot meets the body first)
            self.assertGreater(math.hypot(dx, dy), r + 0.3)


class UnveilTest(unittest.TestCase):
    def setUp(self):
        self.a = angel(30.5, 20.5)
        self.ar = Arena(self.a, w=80, h=44, hero_at=(40.5, 20.5))
        self.ar.hero.invulnerable = True
        self.a._rest = 99.0

    def test_its_bones_fall_and_the_first_angel_unveils(self):
        a, ar = self.a, self.ar
        force(a, ar, "halo", phase=2)
        self.assertTrue(until(ar, lambda: a.wheel is not None, 2.0))
        a.echoes.append(object())                           # (an echo waiting)
        hp0 = a.max_hp
        a.take_damage(a.hp + 10, ar.hero, 0.0)
        self.assertTrue(a.alive)
        self.assertEqual(a.form, "unveiling")
        self.assertFalse(a.hittable)
        self.assertEqual(a.take_damage(500, ar.hero, 0.0), 0.0)
        self.assertIsNone(a.wheel)                          # (its wheel rolls back up)
        self.assertEqual(a.echoes, [])                      # (form 2 doesn't echo)
        self.assertIsNone(a.move)
        self.assertEqual(a.banner_req[0], "THE FIRST ANGEL UNVEILS")
        x, y = a.x, a.y
        run(ar, config.FOSSIL_UNVEIL - 0.2)
        self.assertEqual((a.x, a.y), (x, y))                # (it stands where it is)
        self.assertIn(a.sprite_now(), ("fossil_angel", "fossil_angel_flesh"))
        run(ar, 0.3)
        self.assertEqual(a.form, 2)
        self.assertTrue(a.hittable)
        self.assertEqual(a.max_hp, round(hp0 * config.FOSSIL_UNVEILED_HP))
        self.assertEqual(a.hp, a.max_hp)
        self.assertEqual(a.phase, 0)
        self.assertIs(a.bspec, config.BOSSES["fossil_angel_unveiled"])
        self.assertEqual(sum(1 for e in a.eyes if e is not None), config.FOSSIL_EYES[0])
        self.assertTrue(all(e in ar.enemies for e in a.eyes if e is not None))
        self.assertEqual(a.bar_label, "The First Angel -- unveiled")
        self.assertTrue(a.sprite_now().startswith("fossil_angel_flesh"))
        a.phase = 2
        self.assertFalse(a.echoing)                         # (not even in its third phase)

    def test_form_2s_banners_and_its_brood(self):
        a, ar = self.a, self.ar
        self.assertEqual(a.brood_every(), config.FINAL_BROOD[0])
        unveiled(a, ar)
        self.assertEqual(a.brood_every(), config.FINAL_BROOD[0] * config.FOSSIL_BROOD_SLOWER)
        for frac, phase, title in ((0.7, 1, "ITS BLOOD CRAWLS"), (0.45, 2, "ITS BLOOD HARDENS"),
                                   (0.2, 3, "SIX WINGS")):
            a._rest = 0.0
            a.hp = a.max_hp * frac
            run(ar, DT * 2)
            self.assertEqual(a.phase, phase)
            self.assertEqual(a.banner_req[0], title)
            a._rest = 99.0

    def test_it_falls_for_good_in_form_2(self):
        a, ar = self.a, self.ar
        unveiled(a, ar)
        a.phase = 2
        force(a, ar, "rain", phase=2)
        self.assertTrue(until(ar, lambda: a.red, 3.0))
        key = next(iter(a.red))
        old = a.red[key][2]
        eyes = [e for e in a.eyes if e is not None]
        a.take_damage(a.hp + 10, ar.hero, 0.0)
        self.assertFalse(a.alive)
        a.on_death(a.ctx)
        self.assertIs(ar.world.tile_at(*key), old)          # (its red amber melts away)
        for e in eyes:
            self.assertFalse(e.alive)
            self.assertTrue(e.left)                         # (no kill)


class SignatureTest(unittest.TestCase):
    def setUp(self):
        self.a = angel(30.5, 20.5)
        self.ar = Arena(self.a, w=80, h=44, hero_at=(40.5, 20.5))
        self.ar.hero.invulnerable = True
        self.a._rest = 99.0
        unveiled(self.a, self.ar)

    def test_an_eye_gazes_and_closes_when_hit(self):
        a, ar = self.a, self.ar
        h = ar.hero
        h.invulnerable = False
        h.max_hp = h.hp = 10 ** 5
        i, eye = next((i, e) for i, e in enumerate(a.eyes) if e is not None)
        for e in a.eyes:
            if e is not None and e is not eye:
                e.rest = 99.0
        ex, ey = a.eye_at(i)
        self.assertAlmostEqual(eye.x, ex)
        eye.rest = 0.0
        run(ar, DT * 2)
        self.assertIsNotNone(eye.gaze)
        _, _, _, _, _, _, tell, _, sweep, *_ = config.FOSSIL_EYES
        hp = h.hp
        run(ar, tell + sweep + 0.1)
        self.assertLess(h.hp, hp)                           # (its gaze swept across you)
        self.assertIsNone(eye.gaze)
        hp = a.hp
        eye.take_damage(eye.hp + 1, h, 0.0)
        run(ar, DT * 2)
        self.assertIsNone(a.eyes[i])
        self.assertAlmostEqual(hp - a.hp, config.FOSSIL_EYES[12] * a.max_hp, delta=1.0)
        self.assertIs(a.last_hit_by, h)
        run(ar, config.FOSSIL_EYES[2] + 0.1)
        self.assertIsNotNone(a.eyes[i])                     # (it opens again)

    def test_a_gaze_is_stopped_by_what_stops_shots(self):
        a, ar = self.a, self.ar
        h = ar.hero
        h.invulnerable = False
        h.max_hp = h.hp = 10 ** 5
        for x in range(36, 38):                             # (a wall between it and you)
            for y in range(8, 34):
                ar.world.set_tile(x, y, tiles.RED_AMBER)
        h.x, h.y = 42.5, 20.5
        for e in a.eyes:
            if e is not None:
                e.rest = 0.0
        a.x, a.y = 30.5, 20.5
        a.planted = True                                    # (else it walks into the wall: smashed)
        hp = h.hp
        run(ar, 3.0)
        self.assertEqual(h.hp, hp)

    def test_its_blood_crawls_and_grows_into_angels(self):
        a, ar = self.a, self.ar
        made = []
        a.recruit = recruiter(ar, made)
        a.phase = 0
        run(ar, config.FOSSIL_DROPS[0] + 0.5)
        self.assertEqual(made, [])                          # (not in its first phase)
        a.phase = 1
        a.drop_t = 0.0
        run(ar, DT * 2)
        drops = [e for e in made if isinstance(e, BloodDrop)]
        self.assertEqual(len(drops), config.FOSSIL_DROPS[1])
        for d in drops:
            self.assertIs(d.final_own, a)
            self.assertGreaterEqual(math.hypot(d.x - a.x, d.y - a.y), config.FOSSIL_DROPS[2] * 0.75)
        drops[0].take_damage(drops[0].hp + 1, ar.hero, 0.0)    # (killed young: it never grows)
        run(ar, config.FOSSIL_DROPS[5] + 0.2)
        grown = [e for e in made if e.kind_key in config.FOSSIL_DROP_ANGELS]
        self.assertEqual(len(grown), 1)
        self.assertIn(grown[0].state, ("unveiling", "unveiled"))
        self.assertIs(grown[0].final_own, a)
        self.assertFalse(drops[1].alive)
        self.assertTrue(drops[1].left)                      # (it became the angel: no kill)

    def test_its_pools_slow_you_then_hold_you(self):
        a, ar = self.a, self.ar
        h = ar.hero
        tx, ty = math.floor(h.x), math.floor(h.y)
        a.phase = 1
        self.assertTrue(a._red_tile(ar.world, tx, ty, "pool", 5.0))
        self.assertIs(ar.world.tile_at(tx, ty), tiles.RED_RESIN)
        run(ar, DT * 2)
        self.assertNotIn(id(h), a.held)
        self.assertEqual(h.slow_mult, config.FOSSIL_RED_AMBER[3])
        a.phase = 2                                         # (red amber: it holds you)
        h.slow_t = 0.0
        run(ar, DT * 2)
        self.assertIn(id(h), a.held)
        self.assertEqual(h.slow_mult, 0.0)
        h.roll_t = 0.3
        run(ar, DT)
        self.assertNotIn(id(h), a.held)
        h.roll_t = 0.0
        run(ar, DT * 2)
        self.assertNotIn(id(h), a.held)                     # (not again at once)
        a.red[(tx, ty)][1] = 0.01
        run(ar, DT * 2)
        self.assertIsNot(ar.world.tile_at(tx, ty), tiles.RED_RESIN)

    def test_red_amber_walls_rise_across_your_path(self):
        a, ar = self.a, self.ar
        h = ar.hero
        h.vx, h.vy = 8.0, 0.0
        force(a, ar, "walls", phase=2)
        run(ar, DT * 2)
        rising = [k for k, v in a.red.items() if v[0] == "rising"]
        self.assertTrue(rising)
        xs = {k[0] for k in rising}
        self.assertTrue(all(x > h.x for x in xs))           # (ahead of you, across your way)
        run(ar, config.FOSSIL_WALLS[0] + 0.2)
        walls = [k for k, v in a.red.items() if v[0] == "wall"]
        self.assertTrue(walls)
        for k in walls:
            self.assertIs(ar.world.tile_at(*k), tiles.RED_AMBER)
            self.assertFalse(abs(h.x - k[0] - 0.5) < h.hit_radius + 0.5
                             and abs(h.y - k[1] - 0.5) < h.hit_radius + 0.5)
        for k in walls:
            a.red[k][1] = 0.01
        run(ar, DT * 2)
        self.assertNotIn(tiles.RED_AMBER, {ar.world.tile_at(*k) for k in walls})

    def test_six_wings_beat_in_turn(self):
        a, ar = self.a, self.ar
        h = ar.hero
        h.invulnerable = False
        h.max_hp = h.hp = 10 ** 5
        a.phase = 2
        run(ar, config.FOSSIL_WINGS[0] + 0.5)
        self.assertIsNone(a.beating)                        # (not before its last phase)
        a.phase = 3
        self.assertTrue(a.six_wings)
        a.wing_t = 0.0
        run(ar, DT * 2)
        self.assertEqual(a.beating[0], 0)
        run(ar, config.FOSSIL_WINGS[1] + 0.1)
        self.assertIsNone(a.beating)
        self.assertEqual(a.wing, 1)
        self.assertTrue(any(p.owner is a for p in ar.projectiles))   # (a volley of feathers)


class MovesTest(unittest.TestCase):
    def setUp(self):
        self.a = angel(30.5, 20.5)
        self.ar = Arena(self.a, w=80, h=44, hero_at=(40.5, 20.5))
        self.a._rest = 99.0
        self.ar.hero.invulnerable = True
        unveiled(self.a, self.ar)
        h = self.ar.hero
        h.invulnerable = False
        h.max_hp = h.hp = 10 ** 5
        for e in self.a.eyes:                               # (no gazes in the way)
            if e is not None:
                e.rest = 99.0

    def test_claw_rake_three_lines_with_room_between(self):
        a, ar = self.a, self.ar
        h = ar.hero
        force(a, ar, "rake")
        run(ar, DT)
        self.assertEqual(len(a.lines), config.FOSSIL_RAKE[1])
        x0, y0, ang, _, _ = a.lines[1]                      # (the middle one at you)
        gap = config.FOSSIL_RAKE[3]
        h.x += -math.sin(ang) * gap / 2                     # (between two of them)
        h.y += math.cos(ang) * gap / 2
        hp = h.hp
        self.assertTrue(until(ar, lambda: a.move is None, 3.0))
        self.assertEqual(h.hp, hp)
        a._rest = 99.0
        h.x, h.y = a.x + 8.0, a.y
        force(a, ar, "rake")
        self.assertTrue(until(ar, lambda: a.move is None, 3.0))
        self.assertLess(h.hp, hp)

    def test_the_first_word_hurts_in_the_open_but_not_behind_stone(self):
        a, ar = self.a, self.ar
        h = ar.hero
        hp = h.hp
        force(a, ar, "word")
        run(ar, DT)
        self.assertTrue(a.planted)
        self.assertTrue(a.spikes)                           # (no cover near: stone falls round you)
        near = min(math.hypot(s[0] + 0.5 - h.x, s[1] + 0.5 - h.y) for s in a.spikes)
        self.assertLess(near, config.FOSSIL_WORD[7] + 1.5)
        self.assertTrue(until(ar, lambda: a.word is not None, 3.0))
        self.assertTrue(until(ar, lambda: a.word is None, 5.0))
        self.assertAlmostEqual(hp - h.hp, a.hurt(config.FOSSIL_WORD[3]), delta=2.0)
        # Behind a wall: sheltered.
        a._rest = 99.0
        for y in range(10, 31):
            ar.world.set_tile(37, y, tiles.RED_AMBER)
        a.x, a.y = 30.5, 20.5
        h.x, h.y = 40.5, 20.5
        hp = h.hp
        force(a, ar, "word")
        self.assertTrue(until(ar, lambda: a.word is not None, 3.0))
        self.assertTrue(until(ar, lambda: a.word is None, 5.0))
        self.assertEqual(h.hp, hp)

    def test_blood_rain_leaves_pools(self):
        a, ar = self.a, self.ar
        h = ar.hero
        hp = h.hp
        force(a, ar, "rain")
        self.assertTrue(until(ar, lambda: a.lobs, 2.0))
        self.assertEqual(len(a.lobs), config.FOSSIL_RAIN[1])
        self.assertTrue(all(b[6] == "blood" for b in a.lobs))
        self.assertTrue(until(ar, lambda: not a.lobs, 3.0))
        self.assertTrue(any(v[0] == "pool" for v in a.red.values()))
        self.assertLess(h.hp, hp)                           # (one fell on you)

    def test_halo_wheels_race_out_bounce_and_burn(self):
        a, ar = self.a, self.ar
        for y in range(0, 44):                              # (a wall to bounce off)
            ar.world.set_tile(50, y, tiles.RED_AMBER)
        force(a, ar, "wheels")
        self.assertTrue(until(ar, lambda: a.wheels, 2.0))
        self.assertEqual(len(a.wheels), config.FOSSIL_WHEELS[1])
        self.assertFalse(a.has_halo)
        w = a.wheels[0]                                     # (the one at you: east)
        self.assertGreater(w.vx, 0)
        run(ar, 2.0)
        self.assertLess(w.vx, 0)                            # (it bounced)
        self.assertLess(ar.hero.hp, ar.hero.max_hp)
        self.assertTrue(any(z.kind == "lava_splash" and z.source is a for z in ar.zones))
        run(ar, config.FOSSIL_WHEELS[4])
        self.assertEqual(a.wheels, [])
        self.assertTrue(a.has_halo)


# --- The Fossil Angel's relics, and relics for later runs (FINALS.md 14) ------------------

from ascii_adventurers.entities.projectile import Projectile          # noqa: E402
from ascii_adventurers.meta.guild import Guild                         # noqa: E402
from ascii_adventurers.render.gear_looks import CHEST_LOOKS, HEAD_LOOKS   # noqa: E402
from ascii_adventurers.systems import combat, finals, relics          # noqa: E402
from ascii_adventurers.tests.test_m28_5 import _Relic, mover           # noqa: E402

KEYS = {"feather_ward", "molten_crown", "amber_heart", "eyes_in_the_flesh"}


class RelicsTest(_Relic):
    """One per thing it does (user's picks: protections and buffs): Feather
    Ward (its stone feathers), Molten Crown (its lava halo), Amber Heart (its
    amber), Eyes in Flesh (the first angel)."""

    def test_four_relics_in_four_slots(self):
        keys = config.BOSS_UNIQUES["fossil_angel"]
        self.assertEqual(set(keys), KEYS)
        self.assertEqual(sorted(config.GEAR[k].slot for k in keys), ["chest", "head", "off", "trinket"])
        for k in keys:
            self.assertEqual(config.CARDS[k].rarity, "legendary")
            self.assertEqual(config.CARDS[k].unlock, "U:fossil_angel")
            self.assertLessEqual(len(config.GEAR[k].name), 16)
        self.assertNotIn("fossil_angel_unveiled", config.BOSS_UNIQUES)   # (it's the Fossil Angel)
        self.assertIn("molten_crown", HEAD_LOOKS)
        self.assertIn("amber_heart", CHEST_LOOKS)

    def test_feather_ward_stops_a_shot_with_a_stone_feather(self):
        s, h = self.setup("feather_ward")
        e = self.place(mover(28.5, 20.5))[0]
        shell = config.WEAPONS["cactus_spines"].shell
        q = Projectile(h.x + 1.0, h.y, math.pi, shell, owner=e, damage=10)
        s.projectiles.append(q)
        hp = h.hp
        self.go(0.2)
        self.assertEqual(h.hp, hp)                          # (stopped)
        self.assertFalse(q.alive)
        self.assertGreater(h.ward_t, config.U_WARD[0] - 1.0)
        tx, ty = math.floor(h.x + config.U_WARD[1]), math.floor(h.y)
        self.assertIs(s.world.tile_at(tx, ty), tiles.FEATHER_SPIKE)   # (between it and you)
        q2 = Projectile(h.x + 1.0, h.y + 0.2, math.pi, shell, owner=e, damage=10)
        s.projectiles.append(q2)
        self.go(0.2)
        self.assertLess(h.hp, hp)                           # (not ready again yet)
        self.go(3.2)                                        # (the power's 3 s)
        self.assertIsNot(s.world.tile_at(tx, ty), tiles.FEATHER_SPIKE)

    def test_molten_crown_burns_who_hurts_you_and_cools_them_to_stone(self):
        s, h = self.setup("molten_crown")
        e = self.place(mover(24.5, 20.5))[0]
        h.take_damage(10.0, e, 0.0)
        self.assertTrue(e.status is not None and e.status.has("burn"))
        e.hp = 0.0
        relics.on_kill(s, s.me, e)
        tx, ty = math.floor(e.x), math.floor(e.y)
        self.assertIs(s.world.tile_at(tx, ty), tiles.BASALT_BOULDER)
        self.go(4.0 + 0.3)                                  # (the power's 4 s)
        self.assertIsNot(s.world.tile_at(tx, ty), tiles.BASALT_BOULDER)
        cold = self.place(mover(26.5, 22.5))[0]             # (not burning: nothing)
        cold.hp = 0.0
        relics.on_kill(s, s.me, cold)
        self.assertIsNot(s.world.tile_at(math.floor(cold.x), math.floor(cold.y)), tiles.BASALT_BOULDER)

    def test_amber_heart_seals_you_instead_of_a_low_blow(self):
        s, h = self.setup("amber_heart")
        e = self.place(mover(h.x + 1.6, h.y))[0]
        h.hp = h.max_hp * 0.5
        self.assertEqual(h.take_damage(h.max_hp * 0.4, e, 0.0), 0.0)   # (it'd take you to 10%)
        self.assertEqual(h.hp, h.max_hp * 0.5)
        self.assertGreater(h.sealed, 0)
        self.assertFalse(h.hittable)                        # (untouchable)
        self.go(config.U_AMBER_HEART[2] + 0.1)
        self.assertAlmostEqual(h.hp, h.max_hp * 0.7, delta=h.max_hp * 0.02)   # (+20%)
        self.assertGreater(e.status.bound, 0.0)             # (it touched the amber: held)
        self.assertTrue(any(ev.kind == "toast" and ev.label == "SEALED IN AMBER!" for ev in s.effects))
        h.hp = h.max_hp * 0.3
        h.take_damage(h.max_hp * 0.2, e, 0.0)               # (once a minute)
        self.assertLess(h.hp, h.max_hp * 0.3)

    def test_eyes_in_flesh_open_while_you_fight_and_close_when_hit(self):
        s, h = self.setup("eyes_in_the_flesh")
        e = self.place(mover(28.5, 20.5))[0]
        base = combat.strike(e, 100.0, h, 0.0, s.effects)
        chance = combat.crit_chance(h.stats, h)
        h.flesh_t = 0.0
        self.go(config.U_FLESH_EYES[0] * 7 + 0.5)
        self.assertEqual(h.flesh_eyes, config.U_FLESH_EYES[1])      # (up to 6)
        e.hp = e.max_hp
        a = combat.strike(e, 100.0, h, 0.0, s.effects)
        self.assertAlmostEqual(a / base, 1 + 0.05 * 6, delta=0.01)
        self.assertAlmostEqual(combat.crit_chance(h.stats, h) - chance, 0.03 * 6, delta=1e-6)
        h.take_damage(5.0, e, 0.0)
        self.assertEqual(h.flesh_eyes, config.U_FLESH_EYES[1] - 1)   # (a hit closes one)


class LaterRunsTest(unittest.TestCase):
    """Beating a final unlocks its relics: in later runs the ocean bosses
    drop them too; the archivist's relics shelf shows them."""

    def test_unlocked_by_beating_it(self):
        g = Guild()
        self.assertEqual(finals.relics_open(g), ())
        self.assertFalse(finals.beaten(g, "fossil_angel"))
        g.record_quest("fossil_angel", ["wizard"], 700.0)
        self.assertEqual(set(finals.relics_open(g)), KEYS)
        self.assertEqual(finals.ocean_bosses(), {"cavalry", "host_of_feast", "ancestor", "overseer"})
        self.assertIn("fossil_angel", finals.final_bosses())

    def test_the_ocean_bosses_drop_them_in_later_runs(self):
        from ascii_adventurers.tests.test_m33_1 import game
        seen = {False: set(), True: set()}
        for won in (False, True):
            for seed in (31, 7):
                m, s = game(seed)
                if won:
                    s.app.guild.record_quest("fossil_angel", ["wizard"], 700.0)
                p = s.me
                for boss in ("overseer", "ancestor", "host_of_feast", "cavalry", "froggy"):
                    d = s._drop_unique(p, boss, s.hero.x, s.hero.y)
                    seen[won].add((boss, d.piece.key if d is not None else None))
                    p.uniques_dropped.discard(boss)
                    for k in range(1, 12):                  # (other players' picks too)
                        p.index = k
                        d = s._drop_unique(p, boss, s.hero.x, s.hero.y)
                        seen[won].add((boss, d.piece.key))
                        p.uniques_dropped.discard(boss)
                    p.index = 0
        dropped = {k for _, k in seen[True]}
        self.assertFalse({k for _, k in seen[False]} & KEYS)    # (not before it's beaten)
        self.assertTrue(dropped & KEYS)                         # (after: from the ocean bosses)
        self.assertFalse({k for b, k in seen[True] if b == "froggy"} & KEYS)   # (only theirs)

    def test_the_relics_shelf(self):
        from ascii_adventurers.tests.test_players import make_manager
        from ascii_adventurers.ui.guild_panel import GuildPanel
        m = make_manager()
        g = Guild()
        panel = GuildPanel(m, g, "archive", "wizard")
        rows = {r.key: r for r in panel._relics_rows()}
        for k in KEYS:
            self.assertEqual(rows[k].name, "???")
            self.assertEqual(rows[k].column, "A FINAL")      # (its final unnamed)
        g.record_quest("fossil_angel", ["wizard"], 700.0)
        rows = {r.key: r for r in panel._relics_rows()}
        for k in KEYS:
            self.assertEqual(rows[k].state, "UNLOCKED")
            self.assertEqual(rows[k].name, config.GEAR[k].name)
        g.uniques.add("amber_heart")
        rows = {r.key: r for r in panel._relics_rows()}
        self.assertEqual(rows["amber_heart"].state, "FOUND")


if __name__ == "__main__":
    unittest.main()
