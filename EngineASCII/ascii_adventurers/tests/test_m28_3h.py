"""M28.3h: the rings' legendary tricks (design/GEAR.md 19.6)."""

import os
import unittest
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from ascii_adventurers import config
from ascii_adventurers.players import gear
from ascii_adventurers.systems import combat
from ascii_adventurers.tests.test_m16 import game
from ascii_adventurers.tests.test_m28_2c import DT
from ascii_adventurers.tests.test_m28_2e import dead, elite
from ascii_adventurers.tests.test_m28_3c import BASE, _Legend, plain

RINGS = ("volatile", "chain_reaction", "soul_harvest", "surge", "bloodlust", "giant_slayer",
         "veteran", "golden_hoard", "bounty", "beacon", "fortune")
ALWAYS = ("overflow", "pandemic", "pack_leader")         # (batch 1: always legendary)


class _Ring(_Legend):
    def tick(self, seconds=DT):
        for _ in range(max(1, round(seconds * 60))):
            self.s.rules.tick(self.s.me, DT)

    def kill(self, d, hit=50.0):
        self.s.rules.on_kill(self.s.me, dead(d, hit))


class FrameworkTest(unittest.TestCase):
    def test_every_ring_has_its_legendary_trick(self):
        rings = [k for k, g in config.GEAR.items() if g.slot == "ring"]
        self.assertEqual(sorted(rings), sorted(RINGS + ALWAYS))
        for key in RINGS + ALWAYS:
            name, text = gear.legendary_trick(key)
            self.assertTrue(name and text and text.isascii(), key)


class PrimedTest(_Ring):
    def hits(self, rarity, n, on_hit=True):
        s, h = self.setup("volatile", rarity)
        e, by = self.place(plain(24.0, 20.5), plain(24.8, 20.5))
        for _ in range(n):
            combat.strike(e, 10, h, 0.0, s.effects, on_hit=on_hit)
        s.rules.resolve_combos()
        return e, by

    def test_the_tenth_hit_sets_it_off_alive(self):
        e, by = self.hits("legendary", config.PRIMED - 1)
        self.assertEqual(by.hp, BASE)
        e, by = self.hits("legendary", config.PRIMED)
        self.assertLess(by.hp, BASE)
        self.assertTrue(e.alive)
        self.assertLess(e.hp, BASE - config.PRIMED * 10)          # (it took the blast too)

    def test_blasts_dont_count_nor_without_the_trick(self):
        self.assertEqual(self.hits("legendary", config.PRIMED, on_hit=False)[1].hp, BASE)
        self.assertEqual(self.hits("epic", config.PRIMED)[1].hp, BASE)


class FirecrackerTest(_Ring):
    def blast(self, rarity, weak=False):
        s, h = self.setup("chain_reaction", rarity, ("volatile", 0))
        far = self.place(plain(23.5, 21.0))[0]                    # (2.5 tiles off)
        if weak:
            self.place(plain(21.5, 21.0, 1.0))
        s.rules._explode(h, dead(plain(21.0, 21.0)))
        return far

    def test_a_blast_that_kills_nothing_jumps(self):
        self.assertLess(self.blast("legendary").hp, BASE)
        self.assertEqual(self.blast("epic").hp, BASE)

    def test_not_when_it_killed(self):
        self.assertEqual(self.blast("legendary", weak=True).hp, BASE)


class HarvestTest(_Ring):
    def test_every_tenth_kill_is_max_hp(self):
        s, h = self.setup("soul_harvest")
        most = h.max_hp
        for k in range(2 * config.REAPERS_HARVEST):
            self.kill(plain(30, 20.5))
        self.assertEqual(h.max_hp, most + 2)
        s._apply_loadout(s.me)                                  # (it stays)
        self.assertEqual(h.max_hp, most + 2)

    def test_not_without_the_trick(self):
        s, h = self.setup("soul_harvest", "epic")
        most = h.max_hp
        for k in range(config.REAPERS_HARVEST):
            self.kill(plain(30, 20.5))
        self.assertEqual(h.max_hp, most)


class AscentTest(_Ring):
    def surges(self, rarity, share):
        s, h = self.setup("surge", rarity)
        with mock.patch.object(s.rules, "surge", wraps=s.rules.surge) as surge:
            s._gain_xp(s.me, s.me.progress.needed * share)
        return [c.args[1] if len(c.args) > 1 else 1.0 for c in surge.call_args_list]

    def test_a_half_surge_at_each_quarter(self):
        self.assertEqual(self.surges("legendary", 0.2), [])
        self.assertEqual(self.surges("legendary", 0.8), [config.ASCENT[1]] * 3)
        self.assertEqual(self.surges("epic", 0.8), [])

    def test_the_level_up_is_the_whole_one(self):
        got = self.surges("legendary", 1.0)
        self.assertEqual(got, [config.ASCENT[1]] * 3 + [1.0])

    def test_half_the_heal(self):
        s, h = self.setup("surge")
        h.hp = 10.0
        s.rules.surge(s.me, config.ASCENT[1])
        self.assertAlmostEqual(h.hp, 10.0 + h.max_hp * config.SURGE_HEAL * config.ASCENT[1])


class ThirstTest(_Ring):
    def stacks(self, rarity, big=True):
        s, h = self.setup("bloodlust", rarity)
        e = self.place(elite(24.0, 20.5) if big else plain(24.0, 20.5))[0]
        dealt = sum(combat.strike(e, 10, h, 0.0, s.effects) for _ in range(5))
        return len(h.bloodlust), dealt

    def test_elites_build_stacks_by_damage(self):
        n, dealt = self.stacks("legendary")
        self.assertEqual(n, int(dealt // (BASE * config.THIRST)))
        self.assertGreater(n, 0)
        self.assertEqual(self.stacks("legendary", big=False)[0], 0)
        self.assertEqual(self.stacks("epic")[0], 0)


class OutnumberedTest(_Ring):
    def bonus(self, rarity, crowd):
        s, h = self.setup("giant_slayer", rarity)
        small = plain(24.0, 20.5, 10.0)
        self.place(*[plain(20.5 + 3 * (k % 2), 21.5 + k * 0.5) for k in range(crowd)])
        self.tick()
        return combat.situational_bonus(h.stats, h, small)

    def test_a_crowd_counts_as_giants(self):
        base = self.bonus("legendary", config.OUTNUMBERED[0] - 1)
        self.assertAlmostEqual(self.bonus("legendary", config.OUTNUMBERED[0]) - base,
                               config.GIANT_SLAYER)
        epic = self.bonus("epic", config.OUTNUMBERED[0] - 1)
        self.assertAlmostEqual(self.bonus("epic", config.OUTNUMBERED[0]), epic)


class BattleScarredTest(_Ring):
    def test_living_through_low_hp_is_damage(self):
        s, h = self.setup("veteran")
        e = plain(30, 20.5)
        before = combat.situational_bonus(h.stats, h, e)
        low, live, every, more = config.BATTLE_SCARRED
        h.hp = h.max_hp * (low - 0.05)
        self.tick(live + DT)
        self.assertEqual(h.battle_scars, 1)
        self.assertAlmostEqual(combat.situational_bonus(h.stats, h, e) - before, more)
        self.tick(live + DT)                                    # (not again so soon)
        self.assertEqual(h.battle_scars, 1)
        self.tick(every)
        self.assertEqual(h.battle_scars, 2)

    def test_a_fall_ends_it(self):
        s, h = self.setup("veteran")
        h.hp = h.max_hp * 0.1
        self.tick()
        self.assertIsNotNone(h.brink_t)
        s.rules.revive(s.me)
        self.tick(config.BATTLE_SCARRED[1])
        self.assertEqual(h.battle_scars, 0)

    def test_not_without_the_trick(self):
        s, h = self.setup("veteran", "epic")
        h.hp = h.max_hp * 0.1
        self.tick(config.BATTLE_SCARRED[1] + DT)
        self.assertEqual(h.battle_scars, 0)


class OldGoldTest(_Ring):
    def bonus(self, rarity, purse):
        s, h = self.setup("golden_hoard", rarity)
        s.app.guild.loot = purse
        h.run_loot = 0.0
        self.tick()
        h.run_loot = 0.0
        return combat.situational_bonus(h.stats, h, plain(30, 20.5))

    def test_the_purse_counts(self):
        none = self.bonus("legendary", 0)
        self.assertAlmostEqual(self.bonus("legendary", 20 * config.OLD_GOLD) - none, 0.20)
        self.assertAlmostEqual(self.bonus("legendary", 10 ** 7) - none, config.GOLDEN_HOARD[1])
        self.assertAlmostEqual(self.bonus("epic", 20 * config.OLD_GOLD), self.bonus("epic", 0))


class WantedTest(_Ring):
    def scene(self, rarity="legendary"):
        s, h = self.setup("bounty", rarity)
        small, big = self.place(plain(23.0, 20.5), plain(24.0, 21.5, 5000.0))
        self.tick()
        return s, h, small, big

    def test_the_toughest_is_wanted(self):
        s, h, small, big = self.scene()
        self.assertIs(s.me.wanted, big)
        loot = s.me.stats.loot
        self.kill(big)
        self.assertGreater(s.me.stats.loot, loot)               # (a cache)
        self.assertIsNone(s.me.wanted)

    def test_too_late(self):
        s, h, small, big = self.scene()
        self.tick(config.WANTED[1] + 0.1)
        self.assertIsNone(s.me.wanted)
        loot = s.me.stats.loot
        self.kill(big)
        self.assertEqual(s.me.stats.loot, loot)

    def test_every_minute(self):
        s, h, small, big = self.scene()
        self.kill(big)
        self.tick(config.WANTED[0] - 1.0)
        self.assertIsNone(s.me.wanted)
        self.tick(1.1)
        self.assertIs(s.me.wanted, small)

    def test_not_without_the_trick(self):
        s, h, small, big = self.scene("epic")
        self.assertIsNone(s.me.wanted)


class BrightBeaconTest(unittest.TestCase):
    def extras(self, bright):
        m, s = game("wizard")
        sp = s.spawner
        sp.beckon = config.BEACON_SPAWNS
        sp.density *= 1 + sp.beckon
        sp.bright = bright
        got = plain_got = 0
        for cx in range(-8, 9):
            for cy in range(-8, 9):
                for sid, key, x, y in sp.roster(cx, cy):
                    if sid in sp.beckoned:
                        got += config.ENEMIES[key].elite
                    else:
                        plain_got += config.ENEMIES[key].elite
        return got, plain_got, len(sp.beckoned)

    def test_some_extras_come_as_elites(self):
        dim, dim_plain, n = self.extras(False)
        bright, bright_plain, n2 = self.extras(True)
        self.assertGreater(bright, dim)
        self.assertEqual(bright_plain, dim_plain)               # (the others stay)


class ForesightTest(_Ring):
    def foresee(self, rarity="legendary"):
        s, h = self.setup("fortune", rarity)
        prog = s.me.progress
        prog.picks, prog.offer = 0, []
        s._cards(s.me, None)
        return s, prog

    def level_up(self, s, prog):
        prog.picks += 1
        s._cards(s.me, None)

    def test_the_next_offer_is_seen_early(self):
        s, prog = self.foresee()
        seen = list(prog.next_offer)
        self.assertTrue(seen)
        self.assertEqual(prog.offer, [])
        self.level_up(s, prog)
        self.assertEqual([o.key for o in prog.offer], [o.key for o in seen])
        self.assertEqual(prog.next_offer, [])

    def test_the_kept_piece_stays_through_rerolls(self):
        s, prog = self.foresee()
        s._cards(s.me, ("keep", 1))
        self.assertEqual(prog.kept, 1)
        key = prog.next_offer[1].key
        self.level_up(s, prog)
        prog.rerolls = 3
        for _ in range(3):
            s._cards(s.me, "reroll")
            self.assertEqual(prog.offer[1].key, key)
        s._cards(s.me, "skip")                                  # (the pick is over)
        self.assertIsNone(prog.keep)
        self.assertTrue(prog.next_offer)                        # (and the next is seen)

    def test_unkeep(self):
        s, prog = self.foresee()
        s._cards(s.me, ("keep", 0))
        s._cards(s.me, ("keep", 0))
        self.assertIsNone(prog.kept)

    def test_a_piece_that_no_longer_fits_is_redrawn(self):
        from ascii_adventurers.players.gear import Offer, foresee
        s, prog = self.foresee()
        worn = next(iter(prog.gear.worn.values()))
        stale = [Offer(worn.key, "epic", (), "new"), prog.next_offer[0]]   # (a new one of a worn base)
        fresh = [Offer("kindling", "rare", (), "new")]
        got = foresee(stale, fresh, prog.gear, {worn.key, prog.next_offer[0].key, "kindling"})
        self.assertEqual([o.key for o in got], ["kindling", prog.next_offer[0].key])

    def test_not_without_the_trick(self):
        s, prog = self.foresee("epic")
        self.assertEqual(prog.next_offer, [])

    def test_the_gear_screen_shows_it(self):
        from ascii_adventurers.tests.test_m28_1 import DrawTest
        from ascii_adventurers.ui import gear_screen
        s, prog = self.foresee()
        s._cards(s.me, ("keep", 0))
        scr = gear_screen.GearScreen(SimpleNamespace(display=SimpleNamespace(cols=128, rows=30)),
                                     prog, "browse", act=lambda a: s._cards(s.me, a))
        scr.handle_event(SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_n))
        self.assertEqual(scr.page, "next")
        scr.handle_event(SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RIGHT))
        scr.handle_event(SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertEqual(prog.kept, 1)
        scr.refresh(prog)
        lines = gear_screen.next_lines(scr.next_offer, scr.kept, scr.next_focus)
        self.assertTrue(lines[1][0].startswith("> [*]"))
        d = DrawTest()
        for text in d.fits(lambda m: self._next_page(gear_screen, m, prog), rows=24):
            self.assertIn("NEXT OFFER", text)

    def test_the_picker_says_which_is_kept(self):
        from ascii_adventurers.ui import gear_picker
        s, prog = self.foresee()
        s._cards(s.me, ("keep", 1))
        self.level_up(s, prog)
        pk = gear_picker.GearPicker(SimpleNamespace(display=SimpleNamespace(cols=128, rows=30)),
                                    prog, lambda a: None)
        self.assertTrue(pk._raw(1, True)[0][0].endswith("KEPT"))
        self.assertFalse(pk._raw(0, True)[0][0].endswith("KEPT"))

    @staticmethod
    def _next_page(gear_screen, m, prog):
        scr = gear_screen.GearScreen(m, prog, "browse")
        scr.page = "next"
        return scr


if __name__ == "__main__":
    unittest.main()
