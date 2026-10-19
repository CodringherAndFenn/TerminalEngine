"""M28.2e: the rings' +3 / +6 / +9 tricks (design/GEAR.md 17.5)."""

import math
import os
import random
import unittest
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from ascii_adventurers import config
from ascii_adventurers.ai import make_enemy
from ascii_adventurers.ai.brain import AIContext
from ascii_adventurers.players import gear
from ascii_adventurers.systems import combat, spells, statuses
from ascii_adventurers.systems.run_rules import Chain
from ascii_adventurers.tests.test_m16 import game
from ascii_adventurers.tests.test_m28_2a import foe, wear
from ascii_adventurers.tests.test_m28_2c import DT, _Case

BASE = 1000.0
STRIKE = "ascii_adventurers.systems.run_rules.strike"


def elite(x, y, hp=BASE):
    d = foe(x, y, hp)
    d.espec = SimpleNamespace(elite=True, xp=10, name="elite")
    return d


def plain(x, y, hp=BASE):
    d = foe(x, y, hp)
    d.espec = SimpleNamespace(elite=False, xp=10, name="plain")
    return d


def dead(d, hit=50.0):
    """Killed by a hit of `hit`."""
    d.last_damage = hit
    d.hp = 0.0
    return d


class _Ring(_Case):
    def setup(self, *worn, hero="wizard"):
        """worn: (key, level) pairs."""
        (key, level), rest = worn[0], worn[1:]
        s, h = super().setup(key, level, hero)
        for k, lv in rest:
            wear(s, k, lv)
        h.rng.random = lambda: 0.99
        return s, h

    def tick(self, seconds=DT):
        for _ in range(max(1, round(seconds * 60))):
            self.s.rules.tick(self.s.me, DT)

    def kill(self, d, hit=50.0):
        self.s.rules.on_kill(self.s.me, dead(d, hit))


class FrameworkTest(unittest.TestCase):
    def test_every_ring_has_three_tricks(self):
        rings = [k for k, g in config.GEAR.items() if g.slot == "ring"]
        self.assertEqual(len(rings), 14)
        for key in rings:
            self.assertEqual([t for t, _, _ in gear.tricks(key)], [3, 6, 9], key)
            for _, name, text in gear.tricks(key):
                self.assertTrue(name and text and text.isascii(), key)

    def test_the_slots_built_so_far(self):
        built = {config.GEAR[k].slot for k in config.GEAR_TRICKS}
        self.assertTrue({"off", "head", "feet", "chest", "ring"} <= built)


class PowderkegTest(_Ring):
    def test_big_bang(self):
        s, h = self.setup(("volatile", 3))
        by = self.place(foe(21.5, 21.0, BASE))[0]
        self.kill(plain(21.0, 21.0))
        self.assertEqual(by.hp, BASE)                    # (no luck: no bang)
        self.kill(elite(21.0, 21.0))
        self.assertLess(by.hp, BASE)

    def test_short_fuse(self):
        s, h = self.setup(("volatile", 6))
        p = s.me
        self.kill(plain(21.0, 21.0))
        self.assertAlmostEqual(p.fuse, config.SHORT_FUSE)
        by = self.place(foe(21.5, 21.0, BASE))[0]
        h.rng.random = lambda: config.VOLATILE_CHANCE + config.SHORT_FUSE / 2
        self.kill(plain(21.0, 21.0))
        self.assertLess(by.hp, BASE)
        self.assertEqual(p.fuse, 0.0)

    def test_powder_keg(self):
        s, h = self.setup(("volatile", 9))
        self.place(foe(21.5, 21.0, BASE))
        body = dead(plain(21.0, 21.0, 500.0), hit=100.0)
        with mock.patch(STRIKE) as hit:
            s.rules._explode(h, body)
        base = hit.call_args[0][1]
        self.assertAlmostEqual(base, 100.0 * config.VOLATILE_DAMAGE + 500.0 * config.POWDER_KEG)


class DominoTest(_Ring):
    def test_fuse_line(self):
        s, h = self.setup(("volatile", 0), ("chain_reaction", 3))
        by = self.place(foe(21.5, 21.0, BASE))[0]
        chain = Chain(10)
        chain.n = 1
        body = plain(21.0, 21.0)
        body.blasted = chain
        self.kill(body, hit=100.0)
        self.assertEqual(by.hp, BASE)                    # waits its turn...
        self.assertEqual(len(s.me.fuses), 1)
        with mock.patch(STRIKE) as hit:
            self.tick(config.FUSE_LINE[0] + DT)
        self.assertEqual(s.me.fuses, [])
        grow = 1 + config.FUSE_LINE[1]                   # ...and goes off bigger
        self.assertAlmostEqual(hit.call_args[0][1], 100.0 * config.VOLATILE_DAMAGE * grow)

    def test_clean_sweep(self):
        s, h = self.setup(("volatile", 0), ("chain_reaction", 6))
        chain = Chain(12)
        chain.n = config.CLEAN_SWEEP[0] - 2
        s.gems.clear()
        s.rules._explode(h, dead(plain(21.0, 21.0)), chain)
        self.assertEqual(s.gems, [])
        s.rules._explode(h, dead(plain(21.0, 21.0)), chain)
        self.assertEqual([g.value for g in s.gems], [12 * config.CLEAN_SWEEP[1]])
        s.rules._explode(h, dead(plain(21.0, 21.0)), chain)
        self.assertEqual(len(s.gems), 1)                 # (once a chain)

    def test_domino_effect(self):
        s, h = self.setup(("volatile", 0), ("chain_reaction", 9))
        mid, far = self.place(foe(22.0, 21.0, BASE), foe(23.4, 21.0, BASE))
        chain = Chain(10)
        s.rules._explode(h, dead(plain(21.0, 21.0)), chain)
        self.assertEqual(far.hp, BASE)
        s.rules._explode(h, dead(plain(21.0, 21.0)), chain)     # mid's second: it bursts
        self.tick(config.FUSE_LINE[0] + DT)                       # (after Fuse line's wait)
        self.assertTrue(mid.alive)
        self.assertLess(far.hp, BASE)
        self.assertIn(id(mid), chain.burst)


class ReapersBandTest(_Ring):
    def hurt(self):
        self.h.hp = 10.0

    def test_reap(self):
        s, h = self.setup(("soul_harvest", 3))
        self.hurt()
        self.kill(elite(25, 25))
        self.assertAlmostEqual(h.hp, 10.0 + config.REAP * h.stats.soul_harvest)

    def test_grim(self):
        s, h = self.setup(("soul_harvest", 6))
        self.hurt()
        self.kill(plain(25, 25))
        once = h.hp - 10.0
        self.tick(0.5)
        self.kill(plain(25, 25))
        self.assertAlmostEqual(h.hp - 10.0 - once, once * config.GRIM[1])

    def test_reaper(self):
        s, h = self.setup(("soul_harvest", 9))
        h.max_hp = 300
        self.hurt()
        self.kill(plain(25, 25))
        self.assertAlmostEqual(h.hp, 10.0 + 3.0 * h.stats.soul_harvest)


class AscendantTest(_Ring):
    def test_rising(self):
        s, h = self.setup(("surge", 3))
        self.place(foe(22.5, 20.5, BASE))
        s.me.progress.level = 7
        with mock.patch(STRIKE) as hit:
            s.rules.on_level_up(s.me)
        self.assertAlmostEqual(hit.call_args[0][1], config.RISING * 7)

    def test_ascend(self):
        s, h = self.setup(("surge", 6))
        prog = s.me.progress
        prog.picks = 1
        s._cards(s.me, None)
        with mock.patch.object(s.rules, "surge") as surge:
            s._cards(s.me, ("upgrade", prog.gear.wearing("surge")))
        surge.assert_called_once_with(s.me)

    def test_apotheosis(self):
        s, h = self.setup(("surge", 9))
        prog = s.me.progress
        prog.level, prog.picks = 4, 0
        s.rules.on_level_up(s.me)
        self.assertEqual(prog.picks, 0)
        prog.level = 6
        s.rules.on_level_up(s.me, 2)                    # (two at once: the 5th counts)
        self.assertEqual(prog.picks, 1)


class FangRingTest(_Ring):
    def test_feeding_frenzy(self):
        s, h = self.setup(("bloodlust", 3))
        one = plain(21.5, 20.5, 10.0)
        combat.strike(one, 1000.0, h, None, s.effects)
        s.rules.on_kill(s.me, one)
        self.assertEqual(len(h.bloodlust), 2)
        two = plain(21.5, 20.5, 10.0)
        two.hp = 5.0                                     # (already hurt)
        combat.strike(two, 1000.0, h, None, s.effects)
        s.rules.on_kill(s.me, two)
        self.assertEqual(len(h.bloodlust), 3)

    def test_slow_fade(self):
        s, h = self.setup(("bloodlust", 6))
        for _ in range(3):
            self.kill(plain(25, 25))
        self.tick(config.BLOODLUST_TIME + 0.05)
        self.assertEqual(len(h.bloodlust), 2)
        self.tick(config.SLOW_FADE)
        self.assertEqual(len(h.bloodlust), 1)

    def test_apex(self):
        s, h = self.setup(("bloodlust", 9))
        for _ in range(config.APEX[0] + 5):
            self.kill(plain(25, 25))
        self.assertEqual(len(h.bloodlust), config.APEX[0])
        a = self.place(foe(21.5, 20.5, BASE))[0]
        combat.strike(a, 10.0, h, None, s.effects)
        self.assertEqual(a.status.stacks("bleed"), config.APEX[1])
        h.bloodlust.pop()
        b = self.place(foe(21.5, 20.5, BASE))[0]
        combat.strike(b, 10.0, h, None, s.effects)
        self.assertTrue(b.status is None or not b.status.has("bleed"))


class SlingstoneTest(_Ring):
    def bonus(self, victim):
        return combat.situational_bonus(self.h.stats, self.h, victim)

    def test_long_odds(self):
        s, h = self.setup(("giant_slayer", 3))
        small = foe(25, 25, h.max_hp)
        big = foe(25, 25, h.max_hp + 1000)
        huge = foe(25, 25, h.max_hp + 10000)
        self.assertAlmostEqual(self.bonus(big) - self.bonus(small), config.GIANT_SLAYER + 0.10)
        self.assertAlmostEqual(self.bonus(huge) - self.bonus(small),
                               config.GIANT_SLAYER + config.LONG_ODDS[2])

    def test_toppled_giant(self):
        s, h = self.setup(("giant_slayer", 6))
        with mock.patch.object(s, "_loot") as loot:
            self.kill(plain(25, 25, h.max_hp))
            loot.assert_not_called()
            self.kill(plain(25, 25, h.max_hp + 1))
        self.assertEqual(loot.call_args[1]["times"], config.TOPPLED_GIANT)

    def test_goliaths_bane(self):
        s, h = self.setup(("giant_slayer", 9))
        brute, boss = foe(25, 25, h.max_hp + 100), foe(25, 25, h.max_hp + 100)
        boss.boss = True
        self.assertAlmostEqual(self.bonus(boss) - self.bonus(brute),
                               config.GIANT_SLAYER * (config.GOLIATH - 1))


class GrizzledTest(_Ring):
    def test_hard_won(self):
        s, h = self.setup(("veteran", 3))
        a = foe(25, 25)
        h.level = 10
        ten = combat.situational_bonus(h.stats, h, a)
        h.level = 25
        self.assertAlmostEqual(combat.situational_bonus(h.stats, h, a) - ten, (15 + 6) * 0.01)

    def test_drilled(self):
        s, h = self.setup(("veteran", 6))
        prog = s.me.progress
        prog.level, prog.picks = 10, 1
        s.rules.on_level_up(s.me)
        self.assertEqual(prog.free_upgrades, 1)
        s._cards(s.me, None)
        s._cards(s.me, ("upgrade", prog.gear.wearing("veteran")))
        self.assertEqual((prog.picks, prog.free_upgrades), (1, 0))    # the pick's still there
        self.assertEqual(prog.gear.worn[prog.gear.wearing("veteran")].level, 7)
        s._cards(s.me, ("upgrade", prog.gear.wearing("veteran")))
        self.assertEqual(prog.picks, 0)

    def test_legend(self):
        s, h = self.setup(("veteran", 8))
        s.me.progress.level = 10
        s._apply_loadout(s.me)
        plain_hp = h.max_hp
        wear(s, "veteran", 9)
        self.assertAlmostEqual(h.max_hp, plain_hp * (1 + config.LEGEND * 10), delta=1)


class HoardersTest(_Ring):
    def test_miser(self):
        s, h = self.setup(("golden_hoard", 3))
        s.me.stats.loot = 300.0
        s.me.salvaged = 100.0
        self.tick()
        self.assertAlmostEqual(h.run_loot, 300.0 + 100.0 * (config.MISER - 1))

    def test_golden_armor(self):
        s, h = self.setup(("golden_hoard", 6))
        s.me.stats.loot = 1600.0
        self.tick()
        self.assertEqual(h.hoard_armor, 3)
        self.assertLess(h.take_damage(50.0, None, None), 50.0)
        s.me.stats.loot = 1e6
        self.tick()
        self.assertEqual(h.hoard_armor, config.GOLDEN_ARMOR[1])

    def test_dragons_hoard(self):
        s, h = self.setup(("golden_hoard", 9))
        a = foe(25, 25)
        h.run_loot = 0.0
        base = combat.situational_bonus(h.stats, h, a)
        h.run_loot = 5000.0
        self.assertAlmostEqual(combat.situational_bonus(h.stats, h, a) - base, 1.0)


class BountymarkTest(_Ring):
    def test_big_game(self):
        s, h = self.setup(("bounty", 3))
        s.me.bounty = config.BOUNTY_EVERY - 1
        with mock.patch.object(s, "_loot") as loot:
            self.kill(elite(25, 25))
        self.assertEqual(loot.call_args[1]["times"], config.BOUNTY_EVERY * config.BIG_GAME)

    def test_hunters_pay(self):
        s, h = self.setup(("bounty", 6))
        bag = s.me.progress.gear.bag
        s.me.bounty = config.BOUNTY_EVERY - 1
        self.kill(plain(25, 25))
        self.assertEqual(bag, [])                        # (no luck)
        h.rng.random = lambda: config.HUNTERS_PAY / 2
        s.me.bounty = config.BOUNTY_EVERY - 1
        self.kill(plain(25, 25))
        self.assertEqual(len(bag), 1)
        bag[:] = [bag[0]] * config.GEAR_BAG               # full: the next is salvaged
        before = s.me.stats.loot
        s._bag_piece(s.me)
        self.assertEqual(len(bag), config.GEAR_BAG)
        self.assertGreater(s.me.stats.loot, before)

    def test_dead_or_alive(self):
        m, s = game("wizard")
        wear(s, "bounty", 8)
        s._update_spawner()
        self.assertAlmostEqual(s.spawner.haste, config.HASTE_BOUNTY)
        s.me.progress.gear.worn[s.me.progress.gear.wearing("bounty")].level = 9
        s._apply_loadout(s.me)
        s._update_spawner()
        self.assertAlmostEqual(s.spawner.haste, 0.0)


class BeckoningTest(_Ring):
    def test_the_extra_enemies(self):
        m, s = game("wizard")
        sp = s.spawner
        n = 0
        for cx in range(-6, 7):
            for cy in range(-6, 7):
                n += len(sp.roster(cx, cy))
        self.assertEqual(sp.beckoned, set())
        sp.beckon = config.BEACON_SPAWNS
        sp.density *= 1 + sp.beckon
        more = sum(len(sp.roster(cx, cy)) for cx in range(-6, 7) for cy in range(-6, 7))
        self.assertGreater(len(sp.beckoned), 0)
        self.assertLess(len(sp.beckoned), more)
        self.assertGreater(more, n)

    def test_rally(self):
        s, h = self.setup(("beacon", 3))
        e = make_enemy("goblin_archer", 25.0, 25.0, random.Random(1))
        e.beckoned = True
        e.hp, e.last_hit_by = 0.0, h
        s.enemies.append(e)
        s.gems.clear()
        s._handle_deaths(AIContext(s.world, [h], s._actors(), s.projectiles, s.effects))
        self.assertAlmostEqual(s.gems[0].value, e.espec.xp * config.RALLY)

    def test_moth_to_flame(self):
        s, h = self.setup(("beacon", 6))
        e = make_enemy("goblin_archer", 40.0, 30.0, random.Random(1))
        other = make_enemy("goblin_archer", 40.0, 31.0, random.Random(2))
        e.beckoned = True
        s.enemies += [e, other]
        s.rules.beacon_tricks()
        self.assertIs(e.drawn_to, h)
        self.assertEqual(e.espec.preferred_range, config.MOTH)
        self.assertIsNone(getattr(other, "drawn_to", None))
        self.assertNotEqual(other.espec.preferred_range, config.MOTH)
        e.sense(AIContext(s.world, [h], s._actors(), s.projectiles, s.effects), DT)
        self.assertIs(e.target, h)
        self.assertEqual(e.last_known, (h.x, h.y))       # (out of its sight, it knows)

    def test_lighthouse(self):
        m, s = game("wizard")
        wear(s, "beacon", 9)
        p = s.me
        prog = p.progress
        prog.picks = 0
        p.lighthouse_t = config.LIGHTHOUSE[0] - DT / 2
        before = len(s.enemies)
        s.rules.tick(p, DT)
        wave = p.wave[1]
        self.assertEqual(len(wave), config.LIGHTHOUSE[2])
        self.assertEqual(len(s.enemies), before + len(wave))
        self.assertTrue(all(e.drawn_to is p.hero for e in wave))
        for e in wave:
            e.hp = 0.0
        s.rules.tick(p, DT)
        self.assertEqual((prog.picks, p.wave), (1, None))

    def test_lighthouse_too_slow(self):
        m, s = game("wizard")
        wear(s, "beacon", 9)
        p = s.me
        p.progress.picks = 0
        p.lighthouse_t = config.LIGHTHOUSE[0] - DT / 2
        s.rules.tick(p, DT)
        wave = p.wave[1]
        for _ in range(round(config.LIGHTHOUSE[1] * 60) + 2):
            s.rules.tick(p, DT)
        for e in wave:
            e.hp = 0.0
        s.rules.tick(p, DT)
        self.assertEqual(p.progress.picks, 0)


class FourleafTest(_Ring):
    def test_clover(self):
        m, s = game("wizard")
        st = s.hero.stats
        w = config.WEAPONS[config.HEROES["wizard"].weapon]
        eq = gear.Equipment()
        rank = {r: i for i, r in enumerate(config.RARITIES)}
        lucky = without = 0
        for n in range(1, 60):
            got = gear.draw_offer("wizard", w, eq, 5, 0, n, st, one_rare=True)
            lucky += any(rank[o.rarity] >= rank["rare"] for o in got)
            got = gear.draw_offer("wizard", w, eq, 5, 0, n, st)
            without += any(rank[o.rarity] >= rank["rare"] for o in got)
        self.assertEqual(lucky, 59)
        self.assertLess(without, 59)

    def test_charmed(self):
        s, h = self.setup(("fortune", 6))
        prog = s.me.progress
        before = prog.rerolls
        prog.level = 9
        s.rules.on_level_up(s.me)
        self.assertEqual(prog.rerolls, before)
        prog.level = 10
        s.rules.on_level_up(s.me)
        self.assertEqual(prog.rerolls, before + 1)

    def test_four_leaves(self):
        for level, size in ((8, 4), (9, 5)):
            s, h = self.setup(("fortune", level))
            prog = s.me.progress
            prog.picks = 1
            s._cards(s.me, None)
            self.assertEqual(len(prog.offer), size)


class BrimfulTest(_Ring):
    def crit(self, victim):
        return combat.strike(victim, 10.0, self.h, None, self.s.effects, sure_crit=True)

    def test_brim(self):
        s, h = self.setup(("overflow", 3))
        full, hurt = foe(21.5, 20.5, BASE), foe(21.5, 20.5, BASE)
        hurt.hp = BASE - 1
        cd = h.stats.crit_damage
        self.assertAlmostEqual(self.crit(full) / self.crit(hurt), cd)

    def test_splash(self):
        s, h = self.setup(("overflow", 6))
        target, near, far = self.place(foe(22.0, 20.5, BASE), foe(22.8, 20.5, BASE),
                                       foe(25.0, 20.5, BASE))
        dealt = self.crit(target)
        s.rules.resolve_combos()
        self.assertAlmostEqual(BASE - near.hp, dealt * config.SPLASH[0])
        self.assertEqual(far.hp, BASE)
        self.assertEqual(target.hp, BASE - dealt)

    def test_deluge(self):
        s, h = self.setup(("overflow", 9))
        a = foe(21.5, 20.5, 1e6)
        a.hp -= 1                                        # (not at full HP: no Brim)
        first = self.crit(a)
        self.crit(a)
        third = self.crit(a)
        cd = h.stats.crit_damage
        self.assertAlmostEqual(third / first, (cd + 2 * config.DELUGE[0]) / cd)
        per, seconds, most = config.DELUGE
        for _ in range(40):
            self.crit(a)
        self.assertEqual(len(h.deluge), round(most / per))
        self.tick(seconds + 0.1)
        self.assertEqual(h.deluge, [])


class ContagionTest(_Ring):
    def dying(self):
        d = plain(21.0, 20.5)
        statuses.inflict(d, "burn", self.h, 2)
        return d

    def test_airborne(self):
        for level, caught in ((2, False), (3, True)):
            s, h = self.setup(("pandemic", level))
            other = self.place(foe(21.0 + config.PANDEMIC[1] + 0.6, 20.5, BASE))[0]
            self.kill(self.dying())
            self.assertEqual(other.status is not None and other.status.has("burn"), caught)

    def test_mutation(self):
        s, h = self.setup(("pandemic", 6))
        other = self.place(foe(22.0, 20.5, BASE))[0]
        self.kill(self.dying())
        self.assertEqual(other.status.stacks("burn"), 2 + config.MUTATION)

    def test_plague(self):
        for level, spread in ((8, False), (9, True)):
            s, h = self.setup(("pandemic", level))
            sick, near = self.place(foe(21.0, 20.5, BASE), foe(22.0, 20.5, BASE))
            statuses.inflict(sick, "poison", h, 3)
            for _ in range(round(config.PLAGUE[0] * 60) + 1):
                s.rules.status_tricks(DT)
            self.assertEqual(near.status is not None and near.status.has("poison"), spread)


class PackmasterTest(_Ring):
    def test_alpha(self):
        s, h = self.setup(("pack_leader", 3))
        hit, other = foe(22.0, 20.5, BASE), foe(22.0, 20.5, BASE)
        combat.strike(hit, 1.0, h, None, s.effects)               # you hit it
        bite = combat.strike(hit, 10.0, h, None, s.effects, pet=True)
        plain_bite = combat.strike(other, 10.0, h, None, s.effects, pet=True)
        a = h.stats.damage + combat.situational_bonus(h.stats, h, other)
        self.assertAlmostEqual(bite / plain_bite, (1 + a + config.ALPHA[1]) / (1 + a))
        self.tick(config.ALPHA[0] + 0.1)
        self.assertAlmostEqual(combat.strike(hit, 10.0, h, None, s.effects, pet=True), plain_bite)

    def test_loyal(self):
        s, h = self.setup(("pack_leader", 6), ("bone_turret", 0))
        st = s.me.spells["bone_turret"]
        life = st.params["life"] * h.stats.duration_scale

        def run(seconds):
            for _ in range(round(seconds * 60)):
                spells.update_spells(h, s.me.spells, s.world, s._actors(), s.effects, DT,
                                     s.projectiles, s.zones)

        st.timer = 0.0
        st.params = dict(st.params, interval=1000.0)    # (one turret, no new ones)
        run(DT * 2)
        self.assertEqual(len(st.things), 1)
        spot = (st.things[0]["x"], st.things[0]["y"])
        run(life)
        self.assertEqual((st.things, len(st.waiting)), ([], 1))
        run(config.LOYAL)
        self.assertEqual([(t["x"], t["y"]) for t in st.things], [spot])
        run(life + config.LOYAL + 0.5)
        self.assertEqual((st.things, st.waiting), ([], []))    # (once)

    def test_the_pack(self):
        s, h = self.setup(("pack_leader", 9), ("spirit_wolf", 0))
        st = s.me.spells["spirit_wolf"]
        attacker, bait = self.place(foe(36.0, 20.5, BASE), foe(22.0, 20.5, BASE))
        spells.update_spells(h, s.me.spells, s.world, s._actors(), s.effects, DT)
        self.assertEqual(len(st.things), int(st.params["count"]) + 2)
        h.take_damage(5.0, attacker, None)
        self.assertIs(spells._rushed(h), attacker)
        x0 = st.things[0]["x"]
        for _ in range(30):
            spells.update_spells(h, s.me.spells, s.world, s._actors(), s.effects, DT)
        self.assertGreater(st.things[0]["x"], bait.x)    # past the near one, after the attacker
        self.assertGreater(st.things[0]["x"], x0)


if __name__ == "__main__":
    unittest.main()
