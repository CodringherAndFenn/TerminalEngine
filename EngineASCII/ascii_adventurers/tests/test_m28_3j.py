"""M28.3j: the wizard's main hand's legendary tricks (design/GEAR.md 19.8)."""

import math
import os
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.ai.brain import AIContext
from ascii_adventurers.players import gear
from ascii_adventurers.render.spell_fx import draw_possessed
from ascii_adventurers.systems import combat, statuses
from ascii_adventurers.systems.statuses import inflict
from ascii_adventurers.tests.test_m28_2a import foe
from ascii_adventurers.tests.test_m28_2c import DT
from ascii_adventurers.tests.test_m28_2g import STRIKE, _Staff, movable, victims
from ascii_adventurers.tests.test_m28_3c import BASE, _Legend
from ascii_adventurers.tests.test_players import make

STAFFS = ("storm_caller", "conductor", "supercell", "ball_lightning", "phase_darts", "seeker",
          "resonance", "implosion", "orbiting_darts")
LIGHTNING = ("storm_caller", "conductor", "supercell", "ball_lightning")


class _Wand(_Legend):
    dart, bolt, hit, chain = _Staff.dart, _Staff.bolt, _Staff.hit, _Staff.chain

    def setup(self, key, rarity="legendary", *more, hero=None):
        if key in LIGHTNING:
            more = more + (("chain_lightning", 0),)          # (they need the Chainbolt Charm)
        return super().setup(key, rarity, *more, hero=hero)

    def ctx(self):
        s = self.s
        return AIContext(s.world, [p.hero for p in s.players], s._actors(), s.projectiles,
                         s.effects, zones=s.zones, gems=s.gems)


class FrameworkTest(unittest.TestCase):
    def test_every_wizard_main_hand_has_its_legendary_trick(self):
        staffs = [k for k, g in config.GEAR.items()
                  if g.slot == "main" and config.CARDS[k].heroes == ("wizard",)]
        self.assertEqual(sorted(staffs), sorted(STAFFS + ("arcane_storm",)))
        for key in STAFFS:
            name, text = gear.legendary_trick(key)
            self.assertTrue(name and text and text.isascii(), key)


class ForkedLightningTest(_Wand):
    def forks(self, rarity, jumps=2):
        s, h = self.setup("storm_caller", rarity)
        first, a, b, a2, b2 = self.place(foe(24.0, 20.5, BASE), foe(26.0, 19.5, BASE),
                                         foe(26.0, 21.6, BASE), foe(28.0, 18.5, BASE),
                                         foe(28.0, 22.7, BASE))
        hit = self.chain(first, jumps=jumps)
        return [s.enemies.index(v) for v in victims(hit)], [c.args[1] for c in hit.call_args_list]

    def test_the_first_jump_forks_and_both_go_on(self):
        fade = config.SPELL_SHELLS["chain"].chain_falloff
        who, damage = self.forks("legendary")
        self.assertEqual(who, [1, 2, 3, 4])
        self.assertEqual(damage, [100.0 * fade] * 2 + [100.0 * fade * fade] * 2)

    def test_one_line_without_the_trick(self):
        who, _ = self.forks("epic")
        self.assertEqual(len(who), 2)

    def test_the_branches_hit_each_enemy_once(self):
        who, _ = self.forks("legendary", jumps=6)
        self.assertEqual(sorted(who), [1, 2, 3, 4])


class LongLineTest(_Wand):
    def jump(self, rarity, gap, box=(20.5, 20.5, 40.0, 15.0)):
        s, h = self.setup("conductor", rarity)
        h.view_box = box
        reach = config.SPELL_SHELLS["chain"].chain_range * (1 + h.stats.chain_range)
        first, far = self.place(foe(24.0, 20.5, BASE), foe(24.0 + reach + gap, 20.5, BASE))
        return victims(self.chain(first, jumps=1)), far

    def test_it_reaches_the_nearest_on_screen(self):
        hit, far = self.jump("legendary", 10.0)
        self.assertEqual(hit, [far])

    def test_not_off_screen_nor_without_the_trick(self):
        self.assertEqual(self.jump("legendary", 10.0, box=(20.5, 20.5, 12.0, 8.0))[0], [])
        self.assertEqual(self.jump("epic", 10.0)[0], [])

    def test_a_long_jump_isnt_overcurrent(self):
        s, h = self.setup("conductor", "legendary")
        h.stats.flags.add("conductor+6")
        h.view_box = (20.5, 20.5, 40.0, 15.0)
        first, far = self.place(foe(24.0, 20.5, BASE), foe(50.0, 20.5, BASE))
        hit = self.chain(first, jumps=1)
        self.assertEqual(victims(hit), [far])
        self.assertEqual(hit.call_args.kwargs["extra"], 0.0)


class IonizedTest(_Wand):
    def shocked_after(self, rarity, seconds, by_bolt=True):
        s, h = self.setup("supercell", rarity)
        a = self.place(foe(24.0, 20.5, BASE))[0]
        if by_bolt:
            self.hit(self.bolt(jumps=1), a)
        else:
            inflict(a, "shock", h)
        for _ in range(round(seconds * 60)):
            a.status.update(a, DT, s.effects, s.world)
        return a.status.has("shock")

    def test_a_bolts_shock_never_wears_off(self):
        self.assertTrue(self.shocked_after("legendary", 30.0))

    def test_it_wears_off_without_the_trick_or_not_from_a_bolt(self):
        later = config.STATUSES["shock"].duration * 3
        self.assertFalse(self.shocked_after("epic", later))
        self.assertFalse(self.shocked_after("legendary", later, by_bolt=False))

    def test_jumps_shock_for_good_too(self):
        s, h = self.setup("supercell", "legendary")
        first, b = self.place(foe(24.0, 20.5, BASE), foe(26.0, 20.5, BASE))
        combat.chain_from(first, self.bolt().spec, 100.0, h, s.world, s._actors(), s.effects)
        self.assertTrue(b.status.active["shock"].lasting)


class StaticDartsTest(_Wand):
    def crackles(self, rarity, shot):
        s, h = self.setup("ball_lightning", rarity)
        a = self.place(foe(24.0, 20.5, BASE))[0]
        zones = []
        self.hit(shot() if shot is not None else self.dart(), a, zones=zones)
        return [(z.kind, z.radius, z.life) for z in zones]

    def test_darts_crackle_smaller_and_shorter(self):
        small, life = config.STATIC_DARTS
        self.assertEqual(self.crackles("legendary", None),
                         [("crackle", config.BALL_LIGHTNING_RADIUS * small, life)])
        self.assertEqual(self.crackles("epic", None), [])

    def test_bolts_crackle_as_before(self):
        z = self.crackles("legendary", lambda: self.bolt(jumps=1))
        self.assertEqual(z, [("crackle", config.BALL_LIGHTNING_RADIUS,
                              config.BALL_LIGHTNING_TIME)])


class PossessionTest(_Wand):
    def kill(self, rarity, key="goblin_archer"):
        s, h = self.setup("phase_darts", rarity)
        e = self.place(make(key, 24.0, 20.5))[0]
        e.hp = 1.0
        self.hit(self.dart(damage=50.0), e)
        self.assertFalse(e.alive)
        s._handle_deaths(self.ctx())
        return [x for x in s.enemies if getattr(x, "possessed", None) is not None]

    def test_a_dart_kill_rises_as_a_ghost_on_your_side(self):
        ghosts = self.kill("legendary")
        self.assertEqual(len(ghosts), 1)
        g, h = ghosts[0], self.h
        self.assertEqual((g.kind_key, g.faction, g.hp), ("goblin_archer", "player", g.max_hp))
        self.assertFalse(combat._may_hurt(h, g))             # (your shots pass it)
        hp = h.hp
        self.assertEqual(h.take_damage(30.0, g, None), 0.0)  # (it can't hurt you)
        self.assertEqual(h.hp, hp)
        self.assertTrue(combat._may_hurt(foe(30, 20.5), g))  # (enemies can)

    def test_not_elites_nor_without_the_trick(self):
        self.assertEqual(self.kill("legendary", "bull"), [])
        self.assertEqual(self.kill("epic"), [])

    def test_it_goes_after_5_s_with_no_kill(self):
        g = self.kill("legendary")[0]
        s, h = self.s, self.h
        gems = len(s.gems)
        s.rules.tick(s.me, config.POSSESSION / 2)
        self.assertTrue(g.alive)
        s.rules.tick(s.me, config.POSSESSION / 2)
        self.assertFalse(g.alive)
        s._handle_deaths(self.ctx())
        self.assertNotIn(g, s.enemies)
        self.assertEqual(len(s.gems), gems)                 # (no XP the second time)

    def test_it_fights_the_enemies_and_its_kills_are_yours(self):
        g = self.kill("legendary")[0]
        s, h = self.s, self.h
        other = self.place(make("goblin_archer", 30.0, 20.5, seed=2))[0]
        gctx = s._ghost_ctx(self.ctx())
        self.assertEqual(gctx.players, [other])
        hp = h.hp
        for _ in range(240):
            g.think(gctx, DT)
            combat.update_projectiles(s.projectiles, s.world, s.effects, DT, s._actors(), s.zones)
        self.assertLess(other.hp, other.max_hp)
        self.assertEqual(h.hp, hp)
        gems = len(s.gems)
        other.last_hit_by, other.hp = g, 0.0
        s._handle_deaths(self.ctx())
        self.assertEqual(len(s.gems), gems + 1)

    def test_an_enemy_it_hurts_turns_on_it(self):
        g = self.kill("legendary")[0]
        other = self.place(make("goblin_archer", 30.0, 20.5, seed=2))[0]
        other.take_damage(5.0, g, 0.0)
        self.assertIs(other.grudge, g)

    def test_the_ghost_draws(self):
        self.kill("legendary")
        s = self.s
        for _ in range(12):
            s.steps += 1
            draw_possessed(s.manager.text, s.me.camera, s.enemies, s.steps)


class RelentlessTest(_Wand):
    def reaches(self, rarity):
        s, h = self.setup("seeker", rarity)
        p = self.dart()
        far = self.place(foe(p.x + p.max_range + 6.0, 20.5, BASE))[0]
        p.seek = far
        with mock.patch(STRIKE) as hit:
            self.fly([p], 3.0)
        return victims(hit) == [far]

    def test_a_dart_with_a_target_flies_on_until_it_hits(self):
        self.assertTrue(self.reaches("legendary"))
        self.assertFalse(self.reaches("epic"))

    def test_with_its_target_lost_its_range_counts_again(self):
        s, h = self.setup("seeker", "legendary")
        p = self.dart()
        far = self.place(foe(p.x + p.max_range + 6.0, 20.5, BASE))[0]
        p.seek = far
        self.fly([p], 0.3)
        left = p.max_range - p.travelled
        far.hp = 0.0
        shots = [p]
        self.fly(shots, 3.0)
        self.assertFalse(p.alive)
        self.assertGreater(left, 0.0)


class HarmonicsTest(_Wand):
    def counts(self, rarity, gap=2.0):
        s, h = self.setup("resonance", rarity)
        a, b = self.place(foe(24.0, 20.5, BASE), foe(24.0 + gap, 20.5, BASE))
        out = []
        for v in (a, b, a, b):
            h.time += 0.1
            out.append(round(combat._resonance(v, h, s._actors()), 6))
        return out

    def test_enemies_close_together_share_the_count(self):
        per = config.RESONANCE[1]
        self.assertEqual(self.counts("legendary"), [round(per * k, 6) for k in range(4)])

    def test_not_farther_apart_nor_without_the_trick(self):
        per = config.RESONANCE[1]
        self.assertEqual(self.counts("legendary", gap=config.HARMONICS + 1.0),
                         [0.0, 0.0, per, per])
        self.assertEqual(self.counts("epic"), [0.0, 0.0, per, per])


class GatherTest(_Wand):
    def dragged(self, rarity):
        s, h = self.setup("implosion", rarity)
        a, b = self.place(movable(25.0, 20.5), movable(26.5, 20.5))
        h.aim_point = (25.0, 26.0)
        with mock.patch(STRIKE):
            self.hit(self.dart(), a)
        return (a.x, a.y), (b.x, b.y)

    def test_the_drag_goes_toward_your_aim(self):
        (ax, ay), (bx, by) = self.dragged("legendary")
        pull = config.IMPLOSION[1]
        self.assertAlmostEqual(ay - 20.5, pull, places=2)       # (the one hit, too)
        before = math.hypot(26.5 - 25.0, 20.5 - 26.0)
        self.assertAlmostEqual(before - math.hypot(bx - 25.0, by - 26.0), pull, places=2)

    def test_toward_the_hit_without_the_trick(self):
        (ax, ay), (bx, by) = self.dragged("epic")
        self.assertEqual((ax, ay), (25.0, 20.5))
        self.assertAlmostEqual(bx, 26.5 - config.IMPLOSION[1], places=2)
        self.assertAlmostEqual(by, 20.5)


class ClockworkTest(_Wand):
    def miss(self, rarity, n=1):
        s, h = self.setup("orbiting_darts", rarity)
        shots = [self.dart(angle=0.1 * k - 0.3) for k in range(n)]   # (clear of the edge)
        darts = list(shots)
        self.fly(shots, 3.0)                    # (drops the ones that end)
        return darts

    def test_a_missed_dart_stays_in_orbit_round_you(self):
        p = self.miss("legendary")[0]
        h = self.h
        self.assertTrue(p.alive)
        self.assertIsNotNone(p.parked)
        self.assertAlmostEqual(math.hypot(p.x - h.x, p.y - h.y), config.CLOCKWORK[2])
        a0 = p.parked
        self.fly([p], 1.0)
        self.assertAlmostEqual(p.parked - a0, config.CLOCKWORK[3], places=6)

    def test_at_most_6_and_none_without_the_trick(self):
        shots = self.miss("legendary", n=config.CLOCKWORK[0] + 1)
        self.assertEqual(sum(1 for p in shots if p.alive), config.CLOCKWORK[0])
        self.assertFalse(self.miss("epic")[0].alive)

    def test_an_enemy_close_sets_them_off(self):
        shots = self.miss("legendary", n=3)
        far = self.place(foe(20.5 + config.CLOCKWORK[1] + 2.0, 20.5, BASE))[0]
        self.fly(shots, 0.5)
        self.assertTrue(all(p.parked is not None for p in shots))
        far.x = 20.5 + config.CLOCKWORK[1] - 0.5
        with mock.patch(STRIKE) as hit:
            self.fly(shots, 1.5)
        self.assertEqual(victims(hit), [far] * 3)

    def test_kept_darts_go_with_you(self):
        shots = self.miss("legendary")
        self.h.hp = 0.0
        self.fly(list(shots), DT)
        self.assertFalse(shots[0].alive)


if __name__ == "__main__":
    unittest.main()
