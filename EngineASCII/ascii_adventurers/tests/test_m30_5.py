"""M30.5: the Host of the Feast's second form, THE HUNGER (design/OCEAN.md
17.2): the mask cracking, the hall in the wine, devour and growth, the maw,
teeth in the floor, spilled feast, his four moves, his demon waiters."""

import math
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.ai import KINDS, make_enemy
from ascii_adventurers.ai import pandemonium as pand
from ascii_adventurers.ai.hunger import Waiter
from ascii_adventurers.entities.projectile import Projectile
from ascii_adventurers.render import plains  # noqa: F401  (adds the pictures to ART)
from ascii_adventurers.render.characters import ART
from ascii_adventurers.systems.zones import update_zones
from ascii_adventurers.systems import combat, relics
from ascii_adventurers.tests.test_m28_5 import BASE, _Relic, mover
from ascii_adventurers.tests.test_p7 import Arena, enemy
from types import SimpleNamespace
from ascii_adventurers.world import tiles
from ascii_adventurers.world.test_map import TestMap


def _map(w=80, h=60):
    return TestMap(["." * w] * h, legend={".": tiles.HALL_FLOOR})


def run(a, seconds):
    for _ in range(round(seconds * 60)):
        a.run(1 / 60)
        update_zones(a.zones, a.actors(), a.effects, 1 / 60, a.world)
        a.hero.time += 1 / 60


def gracious(hero_at=(40.5, 42.0), x=40.5, y=30.0):
    """The Host, form 1, in an open hall (no lair: round where he stands),
    guests through a recruiter."""
    h = make_enemy("host_of_feast", x, y, random.Random(3))
    a = Arena(h, hero_at=hero_at)
    a.world = _map()
    a.hero.hp = a.hero.max_hp = 100000

    def recruit(key, gx, gy):
        e = enemy(key, gx, gy, len(a.enemies))
        a.enemies.append(e)
        return e
    h.recruit = recruit
    h._rest = 99.0
    run(a, 1 / 60)
    return h, a


def hunger(hero_at=(40.5, 42.0), bare=True):
    """The Host cracked into the hunger, resting unless a move is forced;
    `bare`: nothing about to eat (no scraps, no guests, no waiters soon)."""
    h, a = gracious(hero_at)
    h.take_damage(h.hp + 1, a.hero, 0.0)
    run(a, config.HUNGER_CRACK + 0.1)
    h._rest = 99.0
    if bare:
        for e in h.guests:
            e.left = True
            e.hp = 0.0
        h.guests, h.scraps = [], []
        h.serve_t = 999.0
        run(a, 1 / 60)
    return h, a


def force(h, a, move, seconds=0.0):
    h._gen = None
    h._start(move)
    h._wait = 0.0
    h._rest = 99.0
    if seconds:
        run(a, seconds)


class CatalogTest(unittest.TestCase):
    def test_four_phases_a_signature_added_in_each(self):
        spec = config.BOSSES["host_hunger"]
        self.assertEqual([p.below for p in spec.phases], [1.0, 0.75, 0.5, 0.25])
        moves = [{m for m, _ in p.moves} for p in spec.phases]
        for m in moves:
            self.assertTrue({"lunge", "tongue", "quake", "bones"} <= m)
        self.assertNotIn("maw", moves[0])
        self.assertIn("maw", moves[1])
        self.assertNotIn("teeth", moves[1])
        self.assertIn("teeth", moves[2])
        self.assertNotIn("spill", moves[2])
        self.assertIn("spill", moves[3])
        self.assertEqual(spec.loot, 0)                      # (the reward is form 1's)
        # (the relic seeds stay put: added after every boss before it; M31.4's
        # Ancestor comes after it)
        keys = config.BOSS_KEYS
        self.assertEqual(keys[keys.index("host_hunger") - 1], "host_of_feast")
        self.assertLess(keys.index("host_hunger"), keys.index("ancestor"))

    def test_the_waiter_and_the_pictures(self):
        self.assertIn("feast_waiter", KINDS)
        self.assertIn("feast_waiter", config.BESTIARY)
        self.assertIn("feast_waiter", config.BOSSES["host_of_feast"].pages)
        for name in ("host_hunger", "host_hunger_maw", "host_of_feast_crack", "feast_waiter"):
            self.assertIn(name, ART)
            self.assertEqual(len(ART[name]), 18)
            self.assertTrue(all(len(r) == 14 for r in ART[name]), name)
        for t in (tiles.HALL_WINE, tiles.TABLE_WRECK):
            self.assertFalse(t.solid)                       # (wade it; stand on it)


class CrackTest(unittest.TestCase):
    def test_at_nothing_the_mask_cracks_instead(self):
        h, a = gracious(hero_at=(40.5, 34.0))
        h.dishes.append(["soup", 40.0, 35.0, 0.0, 0.0, 5.0, False])
        h.take_damage(h.hp + 50, a.hero, 0.0)
        self.assertTrue(h.alive)
        self.assertEqual(h.form, "cracking")
        self.assertFalse(h.hittable)
        self.assertEqual(h.take_damage(500, a.hero, 0.0), 0.0)
        self.assertEqual(h.banner_req[0], "THE MASK CRACKS")
        self.assertEqual(h.dishes, [])                      # (his hospitality cleared away)
        self.assertEqual(h.charm_at(a.hero), 0.0)
        old = list(h.guests)
        run(a, config.HUNGER_CRACK + 0.1)
        self.assertEqual(h.form, 2)
        self.assertEqual(h.max_hp, 14000)                    # (OCEAN.md 17.3)
        self.assertEqual(h.hp, h.max_hp)
        self.assertIs(h.bspec, config.BOSSES["host_hunger"])
        self.assertEqual(h.banner_req[0], "THE HUNGER")
        self.assertEqual(h.bar_label, "The Hunger")
        self.assertTrue(all(getattr(e, "left", False) for e in old))
        self.assertEqual(sorted(e.kind_key for e in h.guests), sorted(config.HUNGER_GUESTS))
        self.assertEqual({e.home for e in h.guests}, {("feast", i) for i in range(3)})
        self.assertTrue(all(e.state == "serene" for e in h.guests))
        self.assertGreaterEqual(len(h.scraps), config.HUNGER_FEAST[0])
        self.assertEqual(h.charm_at(a.hero), 0.0)            # (no charm, user)


class DevourTest(unittest.TestCase):
    def test_a_meal_heals_him_and_makes_him_bigger_and_stronger(self):
        h, a = hunger()
        h.hp = h.max_hp * 0.5
        r, mult = h.hit_radius, h.damage_mult
        h.scraps = [[h.x + 1.0, h.y, "roast"], [h.x - 1.0, h.y, "cake"]]
        run(a, 1 / 60)
        self.assertEqual((h.meals, len(h.scraps)), (1, 1))  # (one mouthful at a time)
        self.assertAlmostEqual(h.hp, h.max_hp * (0.5 + config.HUNGER_DEVOUR[1]), delta=1.0)
        self.assertAlmostEqual(h.hit_radius, r * (1 + config.HUNGER_DEVOUR[2]))
        self.assertAlmostEqual(h.damage_mult, mult * (1 + config.HUNGER_DEVOUR[2]))
        self.assertEqual(h.bar_label, "The Hunger - fed 1")
        run(a, config.HUNGER_DEVOUR[4] + 0.1)
        self.assertEqual(h.meals, 2)

    def test_growth_stops_at_ten_meals(self):
        h, a = hunger()
        h.meals = config.HUNGER_DEVOUR[3]
        r = h.hit_radius
        h.scraps = [[h.x + 1.0, h.y, "soup"]]
        run(a, 1 / 60)
        self.assertEqual(h.scraps, [])
        self.assertEqual(h.meals, config.HUNGER_DEVOUR[3])
        self.assertEqual(h.hit_radius, r)

    def test_he_goes_for_a_meal_he_smells_and_eats_a_guest(self):
        h, a = hunger()
        g = enemy("glutton", h.x + 9.0, h.y, 7)
        g.home, g.state = ("feast", 0), "serene"
        a.enemies.append(g)
        h.guests = [g]
        a.hero.x, a.hero.y = h.x, h.y + 30.0
        run(a, 4.0)
        self.assertFalse(g.alive)
        self.assertTrue(g.left)                             # (eaten: no kill)
        self.assertEqual(h.meals, 1)

    def test_walk_into_a_scrap_or_shoot_it_and_it_goes_in_the_wine(self):
        h, a = hunger()
        h.scraps = [[a.hero.x, a.hero.y, "jelly"], [20.0, 42.0, "soup"]]
        run(a, 1 / 60)
        self.assertEqual(len(h.scraps), 1)
        shell = config.WEAPONS[config.HEROES["wizard"].weapon].shell
        p = Projectile(19.6, 42.0, 0.0, shell, owner=a.hero)
        a.projectiles.append(p)
        run(a, 1 / 60)
        self.assertEqual(h.scraps, [])
        self.assertFalse(p.alive)

    def test_heroes_wade_the_wine_slowly(self):
        h, a = hunger(hero_at=(20.5, 42.5))
        a.world.set_tile(20, 42, tiles.HALL_WINE)
        run(a, 1 / 60)
        self.assertEqual(a.hero.slow_mult, config.HUNGER_ISLANDS[3])
        self.assertGreater(a.hero.slow_t, 0.0)


class WaiterTest(unittest.TestCase):
    def test_waiters_bring_a_course_and_he_eats_them(self):
        h, a = hunger()
        h.planted = True                                     # (standing, for the count)
        h.serve_t = 0.01
        run(a, 0.1)
        ws = [e for e in a.enemies if isinstance(e, Waiter)]
        self.assertEqual(len(ws), config.HUNGER_FEAST[4])
        self.assertTrue(all(w.master is h for w in ws))
        d0 = [math.hypot(w.x - h.x, w.y - h.y) for w in ws]
        run(a, 2.0)
        d1 = [math.hypot(w.x - h.x, w.y - h.y) if w.alive else 0.0 for w in ws]
        self.assertTrue(all(b < c for b, c in zip(d1, d0)))  # (coming to him)
        h.planted = False
        run(a, 12.0)
        self.assertTrue(all(not w.alive and w.left for w in ws))
        self.assertEqual(h.meals, 2)


class MawTest(unittest.TestCase):
    def test_his_maw_pulls_you_in_swallows_you_and_spits_you_out(self):
        h, a = hunger(hero_at=(40.5, 40.0))
        hero = a.hero
        force(h, a, "maw", 0.5)
        self.assertIsNotNone(h.maw)
        self.assertFalse(h.maw["on"])                        # (shown first)
        d0 = math.hypot(hero.x - h.x, hero.y - h.y)
        hp = hero.hp
        swallowed = False
        for _ in range(240):
            run(a, 1 / 60)
            if hero.swallowed is h:
                swallowed = True
                self.assertEqual((hero.x, hero.y), (h.x, h.y))
                break
        self.assertTrue(swallowed)
        self.assertLess(0.0, d0)
        run(a, config.HUNGER_MAW[7] + config.HUNGER_SPAT + 0.1)
        self.assertIsNone(hero.swallowed)
        self.assertLess(hero.hp, hp - config.HUNGER_MAW[5] * config.HUNGER_MAW[6] * 0.5)
        self.assertGreater(math.hypot(hero.x - h.x, hero.y - h.y), config.HUNGER_MAW[8] * 0.6)

    def test_the_maw_draws_the_feast_in_too(self):
        h, a = hunger(hero_at=(10.5, 10.0))
        h.scraps = [[h.x, h.y + 9.0, "roast"]]
        h.facing = math.pi / 2
        h.tgt = None
        a.hero.x, a.hero.y = h.x, h.y + 16.0
        force(h, a, "maw", config.HUNGER_MAW[0] + config.HUNGER_MAW[1])
        self.assertEqual(h.scraps, [])                       # (pulled in and eaten)
        self.assertEqual(h.meals, 1)


class TeethTest(unittest.TestCase):
    def test_teeth_snap_shut_along_marked_lines(self):
        h, a = hunger(hero_at=(40.5, 40.0))
        hp = a.hero.hp
        force(h, a, "teeth", 0.2)
        self.assertEqual(len(h.teeth), config.HUNGER_TEETH[1])
        self.assertEqual(a.hero.hp, hp)                      # (marked: nothing yet)
        run(a, config.HUNGER_TEETH[3])
        self.assertLess(a.hero.hp, hp)                       # (one line ran right through you)

    def test_a_roll_dodges_the_bite(self):
        h, a = hunger(hero_at=(40.5, 40.0))
        hp = a.hero.hp
        force(h, a, "teeth", 0.2)
        a.hero.roll_t = 5.0
        a.hero.roll_speed = 0.0
        a.hero.roll_dir = (1.0, 0.0)
        run(a, config.HUNGER_TEETH[3])
        self.assertEqual(a.hero.hp, hp)


class SpillTest(unittest.TestCase):
    def test_spilled_feast_rots_slows_tempts_and_frenzies_guests(self):
        h, a = hunger(hero_at=(40.5, 40.0))
        g = enemy("glutton", 43.5, 40.0, 9)
        g.home, g.state = ("feast", 5), "serene"
        a.enemies.append(g)
        h.guests = [g]
        h.chew_t = 999.0                                     # (not eating it just now)
        force(h, a, "spill", 0.7 + config.HUNGER_SPILL[1] + 0.1)
        rot = [z for z in a.zones if z.kind == "rot"]
        self.assertEqual(len(rot), config.HUNGER_SPILL[0])
        self.assertTrue(pand.frenzied(a.world, ("feast", 5)))
        z = rot[0]
        a.hero.x, a.hero.y = z.x, z.y
        tmp = a.hero.temptation
        run(a, 1.0)
        self.assertGreater(a.hero.temptation, tmp)
        self.assertLessEqual(a.hero.slow_mult, config.HUNGER_SPILL[4])


class MovesTest(unittest.TestCase):
    def test_lunge_bite_along_a_marked_line(self):
        h, a = hunger(hero_at=(40.5, 42.0))
        hp = a.hero.hp
        force(h, a, "lunge", 0.3)
        self.assertIsNotNone(h.lunge)
        x1, y1 = h.lunge[2:]
        run(a, 1.2)
        self.assertLess(math.hypot(h.x - x1, h.y - y1), 3.0)
        self.assertLess(a.hero.hp, hp)

    def test_tongue_catches_drags_and_bites(self):
        h, a = hunger(hero_at=(40.5, 41.0))
        hp = a.hero.hp
        force(h, a, "tongue", 0.65)
        caught = False
        for _ in range(60):
            run(a, 1 / 60)
            if h.tongue is not None and h.tongue["held"] is a.hero:
                caught = True
                break
        self.assertTrue(caught)
        d = math.hypot(a.hero.x - h.x, a.hero.y - h.y)
        run(a, 0.3)
        self.assertLess(math.hypot(a.hero.x - h.x, a.hero.y - h.y), d)
        run(a, 2.0)
        self.assertLess(a.hero.hp, hp)

    def test_a_roll_pulls_you_free_of_the_tongue(self):
        h, a = hunger(hero_at=(40.5, 41.0))
        force(h, a, "tongue", 0.65)
        for _ in range(60):
            run(a, 1 / 60)
            if h.tongue is not None and h.tongue["held"] is a.hero:
                break
        a.hero.roll_t, a.hero.roll_speed, a.hero.roll_dir = 0.3, 0.0, (0.0, 1.0)
        run(a, 1 / 60)
        self.assertIsNone(h.tongue["held"] if h.tongue else None)

    def test_belly_quake_rings_roll_out(self):
        h, a = hunger(hero_at=(40.5, 42.0))
        hp = a.hero.hp
        force(h, a, "quake", 0.95)
        self.assertTrue(h.planted)
        run(a, 3.0)
        self.assertLess(a.hero.hp, hp)
        self.assertIn("belly_quake", [e.kind for e in a.effects])

    def test_bone_scraps_lie_where_they_land_and_trip_you(self):
        h, a = hunger(hero_at=(40.5, 42.0))
        force(h, a, "bones", 4.0)
        clutter = [z for z in a.zones if z.kind == "bone_clutter"]
        self.assertGreater(len(clutter), 10)
        z = clutter[0]
        a.hero.x, a.hero.y = z.x, z.y
        run(a, 0.3)
        self.assertLessEqual(a.hero.slow_mult, config.HUNGER_BONES[6])


class RelicsTest(_Relic):
    """The Host of the Feast's relics (user's picks, 2026-11-23): one per
    pleasure he plays on -- feast, wine, dance, gold."""

    def test_four_relics_in_four_slots(self):
        keys = config.BOSS_UNIQUES["host_of_feast"]
        self.assertEqual(set(keys), {"gluttons_bib", "hosts_goblet", "dancing_shoes",
                                     "gilded_ring"})
        self.assertEqual(sorted(config.GEAR[k].slot for k in keys),
                         ["chest", "feet", "ring", "trinket"])
        for k in keys:
            self.assertEqual(config.CARDS[k].rarity, "legendary")
            self.assertEqual(config.CARDS[k].unlock, "U:host_of_feast")
            self.assertLessEqual(len(config.GEAR[k].name), 16)

    def test_gluttons_bib_eat_your_kills_scraps(self):
        s, h = self.setup("gluttons_bib")
        relics.on_kill(s, s.me, mover(22.5, 20.5))
        self.assertEqual(len(h.bib_scraps), 1)
        other = mover(30.5, 25.5)
        base = combat.strike(other, 10, h, 0.0, s.effects, can_crit=False)
        h.hp = h.max_hp * 0.5
        h.x = 22.5
        self.go(0.05)
        self.assertEqual(h.bib_scraps, [])
        self.assertAlmostEqual(h.hp, h.max_hp * (0.5 + config.U_BIB[0]), delta=1.0)
        self.assertEqual(len(h.feasted), 1)
        fed = combat.strike(other, 10, h, 0.0, s.effects, can_crit=False)
        self.assertAlmostEqual(fed / base, 1 + h.stats.uniques["gluttons_bib"], places=3)
        h.time += config.U_BIB[1] + 0.1
        self.go(0.05)
        self.assertEqual(h.feasted, [])                      # (worn off)
        for k in range(8):                                   # (five at most)
            relics.on_kill(s, s.me, mover(h.x, h.y))
            self.go(0.02)
        self.assertEqual(len(h.feasted), config.U_BIB[2])

    def test_a_scrap_left_lying_goes_off(self):
        s, h = self.setup("gluttons_bib")
        relics.on_kill(s, s.me, mover(30.5, 20.5))
        self.go(config.U_BIB[3] + 0.1)
        self.assertEqual(h.bib_scraps, [])

    def test_the_hosts_goblet_toasts_and_makes_them_drunk(self):
        s, h = self.setup("hosts_goblet")
        d = mover(25.5, 20.5)
        far = mover(40.5, 20.5)
        self.place(d, far)
        h.goblet_t = 0.0
        self.go(0.6)
        self.assertLess(d.hp, BASE)
        self.assertGreater(d.x, 25.5)                        # (pushed out)
        self.assertGreater(d.status.drunk, 0.0)
        self.assertEqual(far.hp, BASE)                       # (beyond the wave)
        self.assertAlmostEqual(d.status.time_scale, config.U_GOBLET[4])
        self.assertIn("goblet_wave", [e.kind for e in s.effects])
        h.rng.random = lambda: 0.1                           # (it reels: a miss)
        hp = h.hp
        self.assertEqual(h.take_damage(20, d, math.pi), 0.0)
        h.rng.random = lambda: 0.99
        self.assertGreater(h.take_damage(20, d, math.pi), 0.0)
        self.assertLess(h.hp, hp)

    def test_the_goblet_waits_for_someone_to_toast(self):
        s, h = self.setup("hosts_goblet")
        h.goblet_t = 0.0
        self.go(0.1)
        self.assertEqual(h.goblet_waves, [])
        self.assertGreater(h.goblet_t, 0.5)                  # (nobody near: soon again)
        self.place(mover(24.5, 20.5))
        self.go(1.2)
        self.assertEqual([e.kind for e in s.effects].count("goblet_wave"), 1)
        self.assertGreater(h.goblet_t, config.U_GOBLET[0] - 1.0)

    def test_dancing_shoes_end_a_roll_in_a_ring_of_cutlery(self):
        s, h = self.setup("dancing_shoes")
        self.roll(1.0, 0.0, seconds=config.ROLL_TIME + 0.05)
        mine = [q for q in s.projectiles if q.owner is h and q.spec.look == "cutlery"]
        self.assertEqual(len(mine), config.U_SHOES)

    def test_the_gilded_ring_tosses_coins_from_elites(self):
        s, h = self.setup("gilded_ring")
        d = mover(26.5, 20.5)
        plain = mover(24.5, 24.5)
        self.place(d, plain)
        combat.strike(plain, 10, h, 0.0, s.effects)
        self.assertEqual(h.ring_coins, [])                   # (not an elite)
        d.espec = SimpleNamespace(speed=3.0, elite=True, xp=1, name="elite")
        combat.strike(d, 10, h, 0.0, s.effects)
        combat.strike(d, 10, h, 0.0, s.effects)
        self.assertEqual(len(h.ring_coins), 1)               # (one every 6 s)
        base = combat.strike(plain, 10, h, 0.0, s.effects, can_crit=False)
        h.x, h.y = h.ring_coins[0][0], h.ring_coins[0][1]
        self.go(0.05)
        self.assertEqual(h.ring_coins, [])
        gilt = combat.strike(plain, 10, h, 0.0, s.effects, can_crit=False)
        self.assertAlmostEqual(gilt / base, 1.25, places=3)
        h.time += config.U_GILDED[1] + 0.1
        self.assertAlmostEqual(combat.strike(plain, 10, h, 0.0, s.effects, can_crit=False), base)

    def test_their_things_draw(self):
        s, h = self.setup("hosts_goblet")
        d = mover(24.5, 20.5)
        self.place(d)
        h.goblet_t = 0.0
        self.go(0.45)
        h.bib_scraps = [[22.5, 21.5, 5.0], [23.5, 19.5, 1.0]]
        h.ring_coins = [[21.5, 22.5, 4.0]]
        h.ring_gilt_until = h.time + 2.0
        s.me.camera.center_on(h.x, h.y)
        s.me.minimap = None                                  # (a test map has no explored layer)
        s.draw(s.manager.text)
        self.assertGreater(d.status.drunk, 0.0)

    def test_the_host_drops_one_of_them(self):
        self.assertIn("host_of_feast", config.BOSS_UNIQUES)
        self.assertNotIn("host_hunger", config.BOSS_UNIQUES)     # (his second form is him)


class GameTest(unittest.TestCase):
    def test_the_hall_falls_into_the_wine_and_drains_when_hes_beaten(self):
        from ascii_adventurers.tests.test_m16 import game
        m, s = game("wizard", seed=31)
        q = s.quests.states["silence_bandstands"]
        s.quests.dev_key = "silence_bandstands"
        s.quests.dev_finish_hunt()
        L = q.lair
        h = s.hero
        h.max_hp = h.hp = 1e9
        s.world.ensure_ready(int(L.cx) - 80, int(L.cy) - 55, int(L.cx) + 80, int(L.cy) + 55)
        h.x, h.y = L.cx, L.cy - 10
        for _ in range(5):
            s._step(1 / 60)
        b = q.boss
        b.take_damage(b.hp + 1, h, 0.0)
        for _ in range(round((config.HUNGER_CRACK + 0.2) * 60)):
            s._step(1 / 60)
            h.hp = h.max_hp
        self.assertEqual(b.form, 2)
        self.assertEqual(q.stage, "fight")
        kinds = {s.world.tile_at(tx, ty) for tx, ty in b.stamped}
        self.assertEqual(kinds, {tiles.HALL_WINE, tiles.TABLE_WRECK, tiles.COINS})
        wine = sum(1 for t in b.stamped if s.world.tile_at(*t) is tiles.HALL_WINE)
        self.assertGreater(wine, 2000)
        self.assertLess(wine, len(b.stamped) * 0.85)        # (islands to stand on)
        for move in ("lunge", "tongue", "quake", "bones", "maw", "teeth", "spill"):
            b._gen = None
            b._start(move)
            b._wait = 0.0
            for _ in range(60):
                s._step(1 / 60)
                h.hp = h.max_hp
            s.me.camera.center_on(h.x, h.y)
            s.draw(m.text)
        b._let_out(h)
        b.take_damage(b.hp + 1, h, 0.0)
        for _ in range(3):
            s._step(1 / 60)
        self.assertEqual(q.stage, "cleared")
        self.assertEqual(b.stamped, {})
        self.assertFalse(any(s.world.tile_at(int(L.cx) + i, int(L.cy)) is tiles.HALL_WINE
                             for i in range(-70, 71)))
        self.assertIsNone(h.swallowed)

    def test_a_swallowed_hero_is_hidden_and_cant_attack_or_roll(self):
        from ascii_adventurers.players.controls import Controls, PlayerInput
        from ascii_adventurers.tests.test_m16 import game
        m, s = game("wizard", seed=31)
        hero = s.hero
        hero.swallowed = object()

        class Mash(Controls):
            def read(self, *a):
                return PlayerInput(0, 0, (hero.x + 5, hero.y), True, roll=True)
        s.me.controls = Mash()
        shots = len(s.projectiles)
        for _ in range(30):
            s._step(1 / 60)
        self.assertEqual(len([p for p in s.projectiles if p.owner is hero]), 0)
        self.assertLessEqual(len(s.projectiles), shots)
        self.assertEqual(hero.roll_t, 0.0)
        s.draw(m.text)


if __name__ == "__main__":
    unittest.main()
