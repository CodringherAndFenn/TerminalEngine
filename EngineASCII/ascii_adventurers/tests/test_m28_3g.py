"""M28.3g: the chest's legendary tricks (design/GEAR.md 19.5)."""

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.players import gear
from ascii_adventurers.systems import combat
from ascii_adventurers.tests.test_m28_2a import foe
from ascii_adventurers.tests.test_m28_2b import walker
from ascii_adventurers.tests.test_m28_2c import DT
from ascii_adventurers.tests.test_m28_3c import BASE, _Legend, plain

CHEST = ("thorn_mail", "ward_charm", "heavy_plate", "glass_cannon", "retaliation", "untouched",
         "berserker", "bulwark")
ALWAYS = ("juggernaut", "aegis", "phoenix")              # (batch 1: always legendary)


class _Chest(_Legend):
    def tick(self, seconds):
        s = self.s
        for _ in range(round(seconds * 60)):
            s.rules.tick(s.me, DT)


class FrameworkTest(unittest.TestCase):
    def test_every_chest_piece_has_its_legendary_trick(self):
        chests = [k for k, g in config.GEAR.items() if g.slot == "chest"]
        self.assertEqual(sorted(chests), sorted(CHEST + ALWAYS))
        for key in CHEST + ALWAYS:
            name, text = gear.legendary_trick(key)
            self.assertTrue(name and text and text.isascii(), key)


class BrambleWallTest(_Chest):
    def pressed(self, rarity, gap=0.5, seconds=0.5):
        s, h = self.setup("thorn_mail", rarity)
        a = self.place(plain(h.x + h.hit_radius + gap, h.y))[0]
        a.espec.damage = 20
        self.tick(seconds)
        return BASE - a.hp

    def test_what_presses_close_takes_your_thorns(self):
        lost = self.pressed("legendary")
        flat, share = self.h.stats.thorns
        self.assertAlmostEqual(lost, flat + share * 20)
        self.assertAlmostEqual(self.pressed("legendary", seconds=1.5), 2 * (flat + share * 20))

    def test_not_farther_nor_without_the_trick(self):
        self.assertEqual(self.pressed("legendary", gap=config.BRAMBLE_WALL[0] + 1.0), 0.0)
        self.assertEqual(self.pressed("epic"), 0.0)

    def test_a_shooters_own_hit_is_its_shot(self):
        from ascii_adventurers.systems.run_rules import _own_hit
        from ascii_adventurers.tests.test_players import make
        e = make("goblin_archer", 0, 0)
        self.assertAlmostEqual(_own_hit(e), e.weapon.spec.shell.damage * e.damage_mult)


class LastThreadTest(_Chest):
    def hurt(self, rarity, shield, hit):
        s, h = self.setup("ward_charm", rarity)
        h.stats.armor = 0.0
        h.shield = shield
        hp = h.hp
        h.take_damage(hit, foe(26, 20.5), None)
        return hp - h.hp, h.shield

    def test_the_shield_takes_the_whole_hit(self):
        self.assertEqual(self.hurt("legendary", 5.0, 50.0), (0.0, 0.0))
        self.assertEqual(self.hurt("legendary", 0.0, 50.0)[0], 50.0)   # (broken: no shield)
        lost, left = self.hurt("epic", 5.0, 50.0)
        self.assertAlmostEqual(lost, 45.0)


class AnvilTest(_Chest):
    def test_at_most_a_fifth_of_your_hp_a_second(self):
        s, h = self.setup("heavy_plate")
        h.stats.armor = 0.0
        hp = h.hp
        e = foe(26, 20.5)
        for _ in range(10):
            h.take_damage(h.max_hp * 0.08, e, None)
            h.time += 0.05
        share, seconds = config.ANVIL
        self.assertAlmostEqual(hp - h.hp, h.max_hp * share)
        h.time += seconds
        hp = h.hp
        h.take_damage(h.max_hp * 0.08, e, None)
        self.assertAlmostEqual(hp - h.hp, h.max_hp * 0.08)

    def test_not_without_the_trick(self):
        s, h = self.setup("heavy_plate", "epic")
        h.stats.armor = 0.0
        hp = h.hp
        for _ in range(10):
            h.take_damage(h.max_hp * 0.08, foe(26, 20.5), None)
        self.assertGreater(hp - h.hp, h.max_hp * config.ANVIL[0] * 2)


class LightweightTest(_Chest):
    def test_the_lost_hp_is_speed(self):
        s, h = self.setup("glass_cannon")
        light = (h.stats.move, h.stats.attack_speed)
        s, h = self.setup("glass_cannon", "epic")
        heavy = (h.stats.move, h.stats.attack_speed)
        self.assertAlmostEqual(light[0] - heavy[0], 0.3)
        self.assertAlmostEqual(light[1] - heavy[1], 0.3)


class LongMemoryTest(_Chest):
    def shockwave(self, rarity):
        s, h = self.setup("retaliation", rarity)
        archer, near_it = self.place(walker(30.0, 20.5, BASE), walker(31.0, 20.5, BASE))
        h.take_damage(10, archer, None)
        s.rules.tick(s.me, DT)
        return archer, near_it

    def test_it_goes_off_round_the_attacker_too(self):
        archer, near_it = self.shockwave("legendary")
        self.assertLess(archer.hp, BASE)
        self.assertLess(near_it.hp, BASE)
        self.assertEqual(archer.hp, near_it.hp)                       # (each once)

    def test_round_you_only_without_the_trick(self):
        archer, near_it = self.shockwave("epic")
        self.assertEqual((archer.hp, near_it.hp), (BASE, BASE))

    def test_once_each_where_both_reach(self):
        s, h = self.setup("retaliation")
        e = self.place(walker(21.5, 20.5, BASE))[0]
        h.take_damage(10, e, None)
        s.rules.tick(s.me, DT)
        once = BASE - e.hp
        s, h = self.setup("retaliation")
        e2 = self.place(walker(21.5, 20.5, BASE))[0]
        h.take_damage(10, foe(40, 20.5), None)                       # (from far away)
        s.rules.tick(s.me, DT)
        self.assertAlmostEqual(BASE - e2.hp, once)


class CleanSlateTest(_Chest):
    def kill(self, rarity, hp_share):
        s, h = self.setup("untouched", rarity)
        h.hp = h.max_hp * hp_share
        e = plain(30, 20.5)
        e.espec = config.ENEMIES["goblin_archer"]
        e.hp = 0.0
        s.rules.on_kill(s.me, e)
        return h.hp / h.max_hp

    def test_a_kill_heals_you_back_to_the_line(self):
        self.assertAlmostEqual(self.kill("legendary", 0.4), config.UNTOUCHED_HP)
        self.assertAlmostEqual(self.kill("legendary", 0.95), 0.95)
        self.assertAlmostEqual(self.kill("epic", 0.4), 0.4)

    def test_once_every_ten_seconds(self):
        self.kill("legendary", 0.4)
        s, h = self.s, self.h
        e = plain(30, 20.5)
        e.espec = config.ENEMIES["goblin_archer"]
        h.hp = h.max_hp * 0.4
        h.time += config.CLEAN_SLATE / 2
        s.rules.on_kill(s.me, e)
        self.assertAlmostEqual(h.hp / h.max_hp, 0.4)
        h.time += config.CLEAN_SLATE / 2
        s.rules.on_kill(s.me, e)
        self.assertAlmostEqual(h.hp / h.max_hp, config.UNTOUCHED_HP)


class ScarsTest(_Chest):
    def test_the_bonus_falls_slowly_after_a_heal(self):
        s, h = self.setup("berserker")
        e = plain(30, 20.5)
        h.hp = h.max_hp * 0.5
        self.tick(DT)
        low = combat.situational_bonus(h.stats, h, e)
        h.hp = h.max_hp
        self.tick(1.0)
        self.assertAlmostEqual(low - combat.situational_bonus(h.stats, h, e), config.SCARS,
                               places=3)
        self.tick(60.0)
        h.hp = h.max_hp
        self.assertAlmostEqual(h.scar, 0.0)

    def test_it_follows_your_hp_without_the_trick(self):
        s, h = self.setup("berserker", "epic")
        e = plain(30, 20.5)
        h.hp = h.max_hp * 0.5
        self.tick(DT)
        low = combat.situational_bonus(h.stats, h, e)
        h.hp = h.max_hp
        self.tick(DT)
        self.assertAlmostEqual(low - combat.situational_bonus(h.stats, h, e), 0.5)


class RampartsTest(_Chest):
    def test_max_hp_is_armor(self):
        s, h = self.setup("bulwark")
        self.assertEqual(combat.bonus_armor(h), h.max_hp // config.RAMPARTS)
        self.assertGreater(combat.bonus_armor(h), 0)
        h.stats.armor = 0.0
        hp = h.hp
        h.take_damage(100.0, foe(26, 20.5), None)
        armor = h.max_hp // config.RAMPARTS
        self.assertAlmostEqual(hp - h.hp, 100.0 * (1 - armor / (armor + config.ARMOR_K)))

    def test_not_without_the_trick(self):
        s, h = self.setup("bulwark", "epic")
        self.assertEqual(combat.bonus_armor(h), 0)


if __name__ == "__main__":
    unittest.main()
