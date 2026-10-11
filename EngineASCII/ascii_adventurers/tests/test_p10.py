"""P10 (playtest pass, 2026-10-11): the ruins' new enemies -- gnolls, stone
imps, crawling hands, lost soldiers, gargoyle, clockwork sentry, colossus,
rubble crab, gem thief, crossbow sniper, flail brute, rune mine, haunted
blades, bell ghost."""

import math
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.ai.brain import AIContext
from ascii_adventurers.entities.gems import Gem
from ascii_adventurers.render.characters import ART
from ascii_adventurers.render import ruins_art  # noqa: F401
from ascii_adventurers.tests.test_m16 import game
from ascii_adventurers.tests.test_m17 import step
from ascii_adventurers.tests.test_p7 import Arena, enemy

NEW = ("gnoll", "stone_imp", "crawling_hand", "lost_soldier", "gargoyle", "clockwork",
       "colossus", "rubble_crab", "gem_thief", "sniper", "flail_brute", "rune_mine",
       "haunted_blade", "bell_ghost")


class GemArena(Arena):
    """An arena whose enemies can see XP gems (the gem thief's)."""

    def __init__(self, *a, gems=(), **kw):
        super().__init__(*a, **kw)
        self.gems = list(gems)

    def run(self, seconds, dt=1 / 60):
        from ascii_adventurers.ai.plains import drum_haste, tick_drum
        for _ in range(round(seconds / dt)):
            ctx = AIContext(self.world, [self.hero], self.actors(), self.projectiles,
                            self.effects, zones=self.zones, gems=self.gems)
            for e in list(self.enemies):
                if e.alive:
                    e.think(ctx, dt)
            for e in self.enemies:
                if not e.alive and not getattr(e, "_gone", False):
                    e._gone = True
                    e.on_death(ctx)
            self.gems = [g for g in self.gems if g.alive]


class CatalogTest(unittest.TestCase):
    def test_every_new_enemy_lives_in_the_ruins_and_has_its_page(self):
        for key in NEW:
            spec = config.ENEMIES[key]
            self.assertIn("ruins", spec.biomes, key)
            self.assertIn(key, config.BESTIARY, key)
            self.assertIn(spec.sprite, ART, key)
            self.assertTrue(all(len(r) == 14 for r in ART[spec.sprite])
                            and len(ART[spec.sprite]) == 18)

    def test_the_ruins_now_have_nineteen_kinds(self):
        ruins = [k for k, s in config.ENEMIES.items() if "ruins" in s.biomes]
        self.assertEqual(len(ruins), 5 + len(NEW))
        self.assertEqual({k for k in NEW if config.ENEMIES[k].elite}, {"colossus", "flail_brute"})


class ChaserTest(unittest.TestCase):
    def test_simple_chasers_reach_and_bite(self):
        for key in ("gnoll", "stone_imp", "crawling_hand", "lost_soldier"):
            a = Arena(enemy(key, 24.5, 15.5))
            a.run(5.0)
            self.assertLess(a.hero.hp, a.hero.max_hp, key)


class ConstructTest(unittest.TestCase):
    def test_gargoyle_waits_dives_then_is_stone(self):
        g = enemy("gargoyle", 24.5, 15.5)
        a = Arena(g, hero_at=(40.5, 15.5))
        a.run(1.0)
        self.assertEqual(g.state, "perch")                # nobody near
        a.hero.x = 28.5
        states = set()
        for _ in range(240):
            a.run(1 / 60)
            states.add(g.state)
            if g.stone:
                self.assertEqual(g.take_damage(50, a.hero, 0.0), 0.0)
                self.assertEqual(g.sprite_now(), "gargoyle_stone")
        self.assertTrue({"mark", "dive", "stone"} <= states)

    def test_clockwork_sweeps_five_bolts(self):
        c = enemy("clockwork", 22.5, 15.5)
        c.timer = 0.1
        a = Arena(c)
        bolts = []
        for _ in range(150):
            a.run(1 / 60)
            bolts += [p for p in a.projectiles if p.spec.look == "clock_bolt" and p not in bolts]
        self.assertEqual(len(bolts), config.CLOCK_SWEEP[0])
        spread = max(p.angle for p in bolts) - min(p.angle for p in bolts)
        self.assertAlmostEqual(math.degrees(spread), config.CLOCK_SWEEP[1], delta=1)

    def test_colossus_ring_hits_once_and_a_roll_gets_through(self):
        for rolling in (False, True):
            c = enemy("colossus", 26.5, 15.5)
            a = Arena(c)
            c.windup = 0.01
            if rolling:
                a.hero.roll_t = 5.0                       # (i-frames through the ring)
            a.run(2.0)
            took = a.hero.max_hp - a.hero.hp
            if rolling:
                self.assertEqual(took, 0)
            else:
                expected = config.ENEMIES["colossus"].damage * config.ENEMY_DAMAGE_MULTIPLIER
                self.assertAlmostEqual(took, expected)  # one ring, one hit

    def test_rubble_crab_shell_first_then_it_runs(self):
        c = enemy("rubble_crab", 26.5, 15.5)
        a = Arena(c)
        took = c.take_damage(50, a.hero, 0.0)
        self.assertEqual((took, c.hp), (50, c.max_hp))    # the shell took it
        c.take_damage(50, a.hero, 0.0)
        self.assertEqual(c.shell, 0)
        self.assertEqual(c.sprite_now(), "crab_bare")
        d0 = c.dist_to(a.hero)
        a.run(1.0)
        self.assertGreater(c.dist_to(a.hero), d0)          # panics


class ScavengerTest(unittest.TestCase):
    def test_gem_thief_scoops_and_spills(self):
        t = enemy("gem_thief", 15.5, 15.5)
        gems = [Gem(18.5, 15.5, 10), Gem(19.5, 16.5, 10)]
        a = GemArena(t, gems=gems, hero_at=(45.5, 15.5))
        a.run(2.0)
        self.assertEqual(t.sack, 20)
        self.assertEqual(a.gems, [])
        t.hp = 0
        a.run(1 / 60)
        self.assertAlmostEqual(sum(g.value for g in a.gems), 20)

    def test_gem_thief_gets_away(self):
        t = enemy("gem_thief", 15.5, 15.5)
        a = GemArena(t, gems=[Gem(16.0, 15.5, 10)], hero_at=(8.5, 15.5), w=200)   # (room east)
        a.run(config.THIEF[3] + 8.0)
        self.assertFalse(t.alive)
        self.assertTrue(t.escaped)
        self.assertEqual(a.gems, [])                       # gone with the lot

    def test_sniper_bolt_goes_through_everyone(self):
        s = enemy("sniper", 15.5, 15.5)
        s.timer = 0.1
        mid = enemy("lost_soldier", 22.5, 15.5)
        mid.alert = False
        a = Arena(s, mid, hero_at=(29.5, 15.5))
        hp_mid = mid.hp
        a.run(3.0)
        self.assertLess(mid.hp, hp_mid)
        self.assertLess(a.hero.hp, a.hero.max_hp)

    def test_flail_brute_spins_then_throws(self):
        f = enemy("flail_brute", 26.5, 15.5)
        a = Arena(f)
        rings = []
        for _ in range(240):
            a.run(1 / 60)
            if f.spin > 0:
                rings.append(f.ring)
        self.assertTrue(rings and rings[-1] > rings[0])    # the ring grows
        self.assertLess(a.hero.hp, a.hero.max_hp)


class HauntTest(unittest.TestCase):
    def test_rune_mine_glows_then_blows(self):
        m = enemy("rune_mine", 27.5, 15.5)
        a = Arena(m)
        a.run(3.0)
        self.assertFalse(m.alive)
        self.assertLess(a.hero.hp, a.hero.max_hp)
        self.assertTrue(any(e.kind == "rune_burst" for e in a.effects))

    def test_haunted_blades_thrust_one_at_a_time(self):
        blades = [enemy("haunted_blade", 30.5 + dx, 10.5, i) for i, dx in enumerate((-1, 0, 1))]
        a = Arena(*blades)
        most = 0
        for _ in range(240):
            a.run(1 / 60)
            most = max(most, sum(1 for b in blades if b.dash > 0))
        self.assertEqual(most, 1)
        self.assertLess(a.hero.hp, a.hero.max_hp)

    def test_blades_and_hounds_keep_their_own_turns(self):
        from ascii_adventurers.ai.plains import Hound
        from ascii_adventurers.ai.ruins import HauntedBlade
        self.assertIsNot(HauntedBlade._turns, Hound._turns)

    def test_bell_ghost_wakes_the_ruins_and_knocks_you_back(self):
        b = enemy("bell_ghost", 26.5, 15.5)
        b.timer = 0.1
        sleeper = enemy("gnoll", 10.5, 5.5)
        sleeper.alert, sleeper.last_known = False, None
        a = Arena(b, sleeper, hero_at=(30.5, 15.5))
        x0 = a.hero.x
        a.run(1.0)
        self.assertTrue(sleeper.alert)
        self.assertIsNotNone(sleeper.last_known)
        self.assertGreater(a.hero.x, x0)


class GameTest(unittest.TestCase):
    def test_all_of_them_in_a_real_game(self):
        m, s = game("wizard")
        h = s.hero
        h.invulnerable = True
        for i, k in enumerate(NEW):
            a = i * math.tau / len(NEW)
            e = s.spawner.wake(k, h.x + math.cos(a) * 9, h.y + math.sin(a) * 6, None,
                               random.Random(i))
            e.alert = True
            s.enemies.append(e)
        for f in range(300):
            step(s)
            if f % 60 == 0:
                s.draw(m.text)
        self.assertTrue(any(getattr(e, "kind_key", "") in NEW for e in s.enemies))


if __name__ == "__main__":
    unittest.main()
