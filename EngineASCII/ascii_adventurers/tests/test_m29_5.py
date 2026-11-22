"""M29.5: Paradise's boss, form 2 -- the Four Horsemen (design/OCEAN.md
6.2): the cavalry's unveiling, each Horseman's kit, the inheritance."""

import math
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.ai import make_enemy
from ascii_adventurers.ai.horsemen import ConquestBanner, Horseman, KITS, PaleShade, _quarter_of
from ascii_adventurers.systems import combat
from ascii_adventurers.systems.zones import update_zones
from ascii_adventurers.tests.test_m29_2 import arena, run
from ascii_adventurers.tests.test_m29_4 import cavalry
from ascii_adventurers.tests.test_m28_5 import _Relic, mover
from ascii_adventurers.systems import relics
from types import SimpleNamespace
from ascii_adventurers.world import tiles


def horseman(kit, x=30.5, y=15.5, hero_at=(36.5, 15.5)):
    """One Horseman on its own (no cavalry: its own kit only), with a
    recruiter that adds what it calls straight into the arena."""
    h = make_enemy(kit, x, y, random.Random(4))
    a = arena(h, hero_at=hero_at)
    rng = random.Random(9)

    def recruit(key, rx, ry):
        e = make_enemy(key, rx, ry, random.Random(rng.random()))
        a.enemies.append(e)
        return e
    h.recruit = recruit
    h._rest = 99.0
    run(a, 1 / 60)
    return h, a


def force(h, a, move, seconds=0.0):
    h._gen = None
    h._start(move)
    h._wait = 0.0
    h._rest = 99.0
    if seconds:
        steps(a, seconds)


def steps(a, seconds):
    for _ in range(round(seconds * 60)):
        run(a, 1 / 60)
        update_zones(a.zones, a.actors(), a.effects, 1 / 60, a.world)
        a.hero.time += 1 / 60


class UnveilingTest(unittest.TestCase):
    def test_at_nought_the_cavalry_unveils_into_four(self):
        c, a = cavalry()
        c.riders[0].take_damage(c.hp + 50, a.hero, 0.0)
        self.assertTrue(c.alive)
        self.assertEqual(c.form, "unveiling")
        self.assertEqual(c.banner_req[0], "THE FOUR HORSEMEN")
        self.assertFalse(any(r.hittable for r in c.riders))
        self.assertEqual(c.riders[1].take_damage(100, a.hero, 0.0), 0.0)
        run(a, config.HORSEMEN_UNVEIL + 0.1)
        self.assertEqual(c.form, 2)
        self.assertEqual([h.kit for h in c.horsemen], ["conquest", "war", "famine", "death"])
        self.assertTrue(all(h in a.enemies for h in c.horsemen))
        self.assertTrue(all(h.max_hp == config.ENEMIES[h.kit].max_hp for h in c.horsemen))
        self.assertEqual(c.max_hp, 4 * 6000)
        self.assertEqual(c.hp, sum(h.hp for h in c.horsemen))
        self.assertEqual(c.bar_label, "The Four Horsemen")
        self.assertEqual(len(c.bars()), 4)
        run(a, 0.1)
        self.assertFalse(any(e.__class__.__name__ == "Rider" for e in a.enemies if e.alive))

    def test_a_fallen_horsemans_kit_passes_on_and_the_last_ends_it(self):
        c, a = cavalry()
        c.riders[0].take_damage(c.hp + 50, a.hero, 0.0)
        run(a, config.HORSEMEN_UNVEIL + 0.1)
        war = c.horsemen[1]
        war.take_damage(war.hp + 1, a.hero, 0.0)
        run(a, 0.1)
        self.assertIn("war", c.inherited)
        for h in c.horsemen:
            if h.alive:
                self.assertIn("war", h.kits)
                self.assertTrue(h.has("strife"))
        self.assertTrue(any(isinstance(e, PaleShade) for e in a.enemies))   # (Death's power)
        for h in c.horsemen:
            if h.alive:
                h.take_damage(h.hp + 1, a.hero, 0.0)
        self.assertFalse(c.alive)

    def test_the_last_one_standing_has_all_four_kits(self):
        c, a = cavalry()
        c.riders[0].take_damage(c.hp + 50, a.hero, 0.0)
        run(a, config.HORSEMEN_UNVEIL + 0.1)
        for h in c.horsemen[:3]:
            h.take_damage(h.hp + 1, a.hero, 0.0)
            run(a, 1 / 60)
        self.assertEqual(c.horsemen[3].kits, set(KITS))


class ConquestTest(unittest.TestCase):
    def test_crowning_arrows_halve_your_damage_until_you_roll(self):
        h, a = horseman("conquest")
        force(h, a, "crown", config.CROWN[0] + 0.8)
        self.assertTrue(a.hero.crowned)
        crowned = combat.strike(make_enemy("watcher", 40.5, 15.5, random.Random(1)), 40,
                                a.hero, 0.0, [], can_crit=False)
        a.hero.crowned = False
        bare = combat.strike(make_enemy("watcher", 40.5, 15.5, random.Random(1)), 40,
                             a.hero, 0.0, [], can_crit=False)
        self.assertAlmostEqual(crowned, bare * config.CROWN_MULT)

    def test_a_roll_knocks_the_crown_off(self):
        from ascii_adventurers.systems import roll
        from ascii_adventurers.tests.test_m16 import game
        m, s = game("wizard", seed=31)
        s.hero.crowned = True
        roll.start(s, s.me, 1.0, 0.0)
        self.assertFalse(s.hero.crowned)

    def test_banners_spread_burn_and_stand_two_at_most(self):
        h, a = horseman("conquest", hero_at=(33.5, 15.5))
        for _ in range(3):
            force(h, a, "banner", 4.2)       # (it rides to its spot -- up to 3 s -- then plants)
        banners = [e for e in a.enemies if isinstance(e, ConquestBanner) and e.alive]
        self.assertEqual(len(banners), config.BANNER[6])
        b = banners[-1]
        r0 = b.radius
        a.hero.x, a.hero.y = b.x + 0.5, b.y
        hp = a.hero.hp
        steps(a, 1.5)
        self.assertGreater(b.radius, r0)
        self.assertLess(a.hero.hp, hp)

    def test_victors_lap_circles_you_firing_inward(self):
        h, a = horseman("conquest")
        force(h, a, "lap", 1.5)
        self.assertTrue(any(p.owner is h for p in a.projectiles))
        self.assertIsNotNone(h.ctrl)

    def test_arrow_fans_while_galloping(self):
        h, a = horseman("conquest")
        h.fans_t = 0.0
        steps(a, 0.1)
        self.assertEqual(sum(1 for p in a.projectiles if p.owner is h), config.FANS[1])


class WarTest(unittest.TestCase):
    def test_sweeping_blade_and_its_wave_of_blood(self):
        h, a = horseman("war", hero_at=(33.5, 15.5))
        hp = a.hero.hp
        force(h, a, "sweep", config.SWEEP[0] + 0.1)
        self.assertLess(a.hero.hp, hp)
        self.assertTrue(any(p.spec.look == "blood" for p in a.projectiles))

    def test_blood_charge_leaves_a_burning_river(self):
        h, a = horseman("war", hero_at=(42.5, 15.5))
        force(h, a, "bloodcharge", config.BLOOD_CHARGE[0] + 1.0)
        self.assertTrue(any(z.kind == "blood_fire" for z in a.zones))

    def test_the_duel_doubles_both_ways_and_breaking_out_stings(self):
        h, a = horseman("war", hero_at=(34.5, 15.5))
        force(h, a, "duel", config.HM_DUEL[0] + 0.1)
        self.assertIs(a.hero.duel, h)
        self.assertTrue(h.planted)
        hp = a.hero.hp
        dealt = combat.strike(a.hero, 10, h, 0.0, [])         # (it hits you twice as hard...)
        self.assertAlmostEqual(dealt, 10 * config.HM_DUEL[3])
        a.hero.hp = hp
        hp = a.hero.hp
        cx, cy, r, _ = h.ring
        a.hero.x = cx + r + 2.0
        steps(a, 0.1)
        self.assertLess(a.hero.hp, hp)
        self.assertIsNone(a.hero.duel)

    def test_strife_sends_unveiled_angels_capped(self):
        c, a = cavalry()
        c.riders[0].take_damage(c.hp + 50, a.hero, 0.0)
        run(a, config.HORSEMEN_UNVEIL + 0.1)
        rng = random.Random(2)

        def recruit(key, x, y):
            e = make_enemy(key, x, y, random.Random(rng.random()))
            a.enemies.append(e)
            return e
        c.recruit = recruit
        for _ in range(4):
            c.strife_t = 0.0
            run(a, 1 / 60)
        strife = [e for e in a.enemies if getattr(e, "strife", False)]
        self.assertEqual(len(strife), config.STRIFE[2])
        self.assertTrue(all(e.state in ("unveiling", "unveiled") for e in strife))


class FamineTest(unittest.TestCase):
    def test_the_scales_take_from_the_lighter_and_give_it_over(self):
        h, a = horseman("famine", hero_at=(34.5, 15.5))
        a.hero.max_hp, a.hero.hp = 200, 60.0                  # (you: 30%, it: full)
        h.scales_t = 0.0
        hp = a.hero.hp
        steps(a, 0.05)
        lost = hp - a.hero.hp
        self.assertGreater(lost, 0)
        h.hp = h.max_hp * 0.1                                 # (now it's the lighter)
        a.hero.hp = 180.0
        a.hero.time = 100.0
        a.hero.starved_until = -1.0
        h.scales_t = 0.0
        before = h.hp
        a.hero.x = h.x + config.HUNGER + 4                    # (out of its hunger)
        steps(a, 0.05)
        self.assertLess(h.hp, before)

    def test_hunger_blocks_healing_near_it(self):
        h, a = horseman("famine", hero_at=(33.5, 15.5))
        a.hero.hp = a.hero.max_hp * 0.5
        steps(a, 0.1)
        self.assertEqual(a.hero.heal(20), 0.0)
        a.hero.x = h.x + config.HUNGER + 6
        steps(a, 0.5)
        self.assertGreater(a.hero.heal(20), 0.0)

    def test_weights_are_marked_crush_and_stay(self):
        h, a = horseman("famine", hero_at=(36.5, 15.5))
        force(h, a, "weights", 0.1)
        self.assertEqual(len(h.weights), config.WEIGHTS[1])
        x, y = h.weights[0]
        hp = a.hero.hp
        steps(a, config.WEIGHTS[0])
        self.assertLess(a.hero.hp, hp)
        self.assertIs(a.world.tile_at(math.floor(x), math.floor(y)), tiles.WEIGHT)
        self.assertTrue(tiles.WEIGHT.solid)

    def test_locusts_pour_from_its_saddlebags(self):
        h, a = horseman("famine")
        force(h, a, "locusts", config.HM_PLAGUE[0] + 0.1)
        locusts = [e for e in a.enemies if getattr(e, "kind_key", "") == "locust"]
        self.assertEqual(len(locusts), config.HM_PLAGUE[1])
        self.assertTrue(all(e.unveiled for e in locusts))


class DeathTest(unittest.TestCase):
    def test_hades_follows_pulling_and_starving(self):
        h, a = horseman("death")
        h.speed = 10.0
        h.hades_t = 0.0
        h._passives(_ctx(a), 1 / 60)
        pool = next(z for z in a.zones if z.kind == "hades")
        self.assertGreater(pool.pull, 0)
        a.hero.x, a.hero.y = pool.x + pool.radius * 0.8, pool.y
        x0 = a.hero.x
        steps(a, 0.5)
        self.assertLess(abs(a.hero.x - pool.x), abs(x0 - pool.x))
        self.assertLess(a.hero.time, a.hero.starved_until)

    def test_a_fourth_of_the_earth_strikes_quarter_by_quarter(self):
        h, a = horseman("death", hero_at=(36.5, 15.5))
        force(h, a, "quarter", 0.05)
        cx, cy, r, q, _ = h.quarter
        hp = a.hero.hp
        a.hero.x = cx + math.cos(q * math.tau / 4 + math.pi / 4) * 4
        a.hero.y = cy + math.sin(q * math.tau / 4 + math.pi / 4) * 4
        self.assertEqual(_quarter_of(a.hero.x - cx, a.hero.y - cy), q)
        x, y = a.hero.x, a.hero.y
        for _ in range(round(config.QUARTER[0] * 60) + 5):
            a.hero.x, a.hero.y = x, y
            steps(a, 1 / 60)
        self.assertLess(a.hero.hp, hp)

    def test_reaping_spins_the_scythe(self):
        h, a = horseman("death", hero_at=(33.0, 15.5))
        hp = a.hero.hp
        force(h, a, "reap", 1.5)
        self.assertIsNotNone(h.scythe)
        self.assertLess(a.hero.hp, hp)

    def test_the_dead_rise_once_as_pale_shades(self):
        c, a = cavalry()
        c.riders[0].take_damage(c.hp + 50, a.hero, 0.0)
        run(a, config.HORSEMEN_UNVEIL + 0.1)
        e = make_enemy("cherub", 25.5, 20.5, random.Random(3))
        a.enemies.append(e)
        run(a, 1 / 60)
        e.take_damage(e.hp + 1, a.hero, 0.0)
        run(a, 2 / 60)
        shades = [s for s in a.enemies if isinstance(s, PaleShade)]
        self.assertEqual(len(shades), 1)
        s = shades[0]
        s.take_damage(s.hp + 1, a.hero, 0.0)
        run(a, 2 / 60)
        self.assertEqual(len([s for s in a.enemies if isinstance(s, PaleShade)]), 1)  # (once)


def _ctx(a):
    from ascii_adventurers.ai.brain import AIContext
    return AIContext(a.world, [a.hero], a.actors(), a.projectiles, a.effects, zones=a.zones)


class RelicsTest(_Relic):
    """The Four Horsemen's relics (user's picks, 2026-11-22): one each."""

    def test_four_relics_one_per_horseman_in_four_slots(self):
        keys = config.BOSS_UNIQUES["cavalry"]
        self.assertEqual(set(keys), {"crown_of_conquest", "ring_of_blood", "black_scales",
                                     "pale_riders_cloak"})
        self.assertEqual(sorted(config.GEAR[k].slot for k in keys),
                         ["chest", "head", "ring", "trinket"])
        for k in keys:
            self.assertEqual(config.CARDS[k].rarity, "legendary")
            self.assertEqual(config.CARDS[k].unlock, "U:cavalry")

    def test_crown_of_conquest_crowns_what_you_hit(self):
        s, h = self.setup("crown_of_conquest")
        d = mover(24.5, 20.5)
        self.place(d)
        combat.strike(d, 10, h, 0.0, s.effects)
        self.assertIs(d.crowned_by, h)
        self.assertAlmostEqual(d.crown_until, h.time + 4.0)
        hp = h.hp
        dealt = combat.strike(h, 20, d, math.pi, s.effects)
        self.assertAlmostEqual(dealt, 20 * config.U_CONQUEST[1])
        h.hp = hp
        h.time += 2.0
        combat.strike(d, 10, h, 0.0, s.effects)            # (once every 8 s: not renewed)
        self.assertAlmostEqual(d.crown_until, h.time - 2.0 + 4.0)
        h.time += 3.0                                      # (worn off)
        self.assertAlmostEqual(combat.strike(h, 20, d, math.pi, s.effects), 20)

    def test_ring_of_blood_duels_an_elite(self):
        s, h = self.setup("ring_of_blood")
        d = mover(26.5, 20.5)
        d.espec = SimpleNamespace(speed=3.0, elite=True, xp=1, name="elite")
        self.place(d)
        h.blood_ring_t = 0.0
        self.go(0.05)
        self.assertIsNotNone(h.blood_ring)
        self.assertIs(h.duel, d)
        other = mover(30.5, 25.5)
        self.assertAlmostEqual(combat.strike(other, 10, h, 0.0, s.effects, can_crit=False)
                               / 10, config.HM_DUEL[3] * h.stats.damage_mult
                               * (1 + h.stats.damage), places=3)
        h.x = h.blood_ring["x"] + h.blood_ring["r"] + 2.0  # (stepping out ends it)
        self.go(0.05)
        self.assertIsNone(h.blood_ring)
        self.assertIsNone(h.duel)

    def test_the_black_scales_take_from_the_lighter(self):
        s, h = self.setup("black_scales")
        d = mover(24.5, 20.5, hp=1000)
        self.place(d)
        d.hp = 100.0                                        # (it: 10%, you: full)
        h.scales_t = 0.0
        self.go(0.05)
        self.assertAlmostEqual(d.hp, 100.0 - 1000 * 0.03, places=3)
        d.hp = 1000.0
        h.hp = h.max_hp * 0.3                               # (now you're the lighter)
        hp = h.hp
        h.scales_t = 0.0
        self.go(0.05)
        self.assertLess(h.hp, hp)
        self.assertEqual(d.hp, 1000.0)                      # (capped at its max)

    def test_pale_riders_cloak_raises_your_kills(self):
        s, h = self.setup("pale_riders_cloak")
        target = mover(26.5, 20.5, hp=1000)
        self.place(target)
        for k in range(5):
            relics.on_kill(s, s.me, mover(22.5, 20.5 + k * 0.2))
        self.assertEqual(len(h.pale), config.U_PALE[0])
        self.go(2.0)
        self.assertLess(target.hp, 1000)
        self.go(5.0)
        self.assertEqual(h.pale, [])


class GameTest(unittest.TestCase):
    def test_the_whole_fight_to_the_last_horseman(self):
        from ascii_adventurers.tests.test_m16 import game
        m, s = game("wizard", seed=31)
        s.app.dev = True
        q = s.quests.states["seven_seals"]
        s.quests.dev_key = "seven_seals"
        s.quests.dev_finish_hunt()
        h = s.hero
        h.max_hp = h.hp = 1e9
        h.water_walk = True
        s.world.ensure_ready(int(q.lair.cx) - 50, int(q.lair.cy) - 30,
                             int(q.lair.cx) + 50, int(q.lair.cy) + 30)
        h.x, h.y = q.lair.cx, q.lair.cy + 20
        for _ in range(5):
            s._step(1 / 60)
        b = q.boss
        b.riders[0].take_damage(b.hp + 10, h, 0.0)
        for _ in range(round((config.HORSEMEN_UNVEIL + 0.5) * 60)):
            s._step(1 / 60)
            h.hp = h.max_hp
        self.assertEqual(b.form, 2)
        self.assertEqual(s.quests.banner.title if s.quests.banner else "THE FOUR HORSEMEN",
                         "THE FOUR HORSEMEN")
        for hm in b.horsemen:
            for move in KITS[hm.kit]["moves"]:
                hm._gen = None
                hm._start(move)
                hm._wait = 0.0
                for _ in range(40):
                    s._step(1 / 60)
                    h.hp = h.max_hp
                s.me.camera.center_on(h.x, h.y)
                s.draw(m.text)
        for hm in b.horsemen:
            hm.take_damage(hm.hp + 1, h, 0.0)
        for _ in range(3):
            s._step(1 / 60)
        self.assertEqual(q.stage, "cleared")
        self.assertTrue(all(isinstance(x, Horseman) for x in b.horsemen))
        dropped = [d for d in s.drops if d.piece.key in config.BOSS_UNIQUES["cavalry"]]
        self.assertEqual(len(dropped), 1)                   # (one of the four relics)


if __name__ == "__main__":
    unittest.main()
