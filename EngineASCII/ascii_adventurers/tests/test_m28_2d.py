"""M28.2d: the chest's +3 / +6 / +9 tricks (design/GEAR.md 17.4)."""

import math
import os
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.entities.projectile import Projectile
from ascii_adventurers.players import gear
from ascii_adventurers.render import characters
from ascii_adventurers.systems import combat
from ascii_adventurers.tests.test_m28_2a import foe
from ascii_adventurers.tests.test_m28_2c import DT, SHOT, _Case

BASE = 1000.0


class _Chest(_Case):
    def tick(self, seconds=DT):
        for _ in range(max(1, round(seconds * 60))):
            self.s.rules.tick(self.s.me, DT)

    def hurt(self, amount, source=None, stay=False):
        if stay:                                  # (Recoil threw the hero off: back in reach)
            self.h.x, self.h.y = 20.5, 20.5
        return self.h.take_damage(amount, source or self.attacker, None)

    def setup(self, key, level, hero="wizard", walls=()):
        s, h = super().setup(key, level, hero, walls)
        h.vx = h.vy = 0.0
        self.attacker = self.place(foe(19.5, 20.5, BASE))[0]
        return s, h


class FrameworkTest(unittest.TestCase):
    def test_every_chest_piece_has_three_tricks(self):
        chest = [k for k, g in config.GEAR.items() if g.slot == "chest"]
        self.assertEqual(len(chest), 11)
        for key in chest:
            self.assertEqual([t for t, _, _ in gear.tricks(key)], [3, 6, 9], key)
            for _, name, text in gear.tricks(key):
                self.assertTrue(name and text and text.isascii(), key)

    def test_the_slots_built_so_far(self):
        built = {config.GEAR[k].slot for k in config.GEAR_TRICKS}
        self.assertTrue({"off", "head", "feet", "chest"} <= built)


class BrambleguardTest(_Chest):
    def test_barbs(self):
        s, h = self.setup("thorn_mail", 3)
        self.hurt(10)
        self.assertEqual(self.attacker.status.stacks("bleed"), config.BARBS)

    def test_overgrowth(self):
        s, h = self.setup("thorn_mail", 6)
        near, far = self.place(foe(21.5, 20.5, BASE), foe(25, 20.5, BASE))
        self.tick(config.OVERGROWTH[0] - 0.1)
        self.assertEqual(near.hp, BASE)
        self.tick(0.7)
        self.assertLess(near.hp, BASE)
        self.assertEqual(far.hp, BASE)

    def test_wild_hedge(self):
        s, h = self.setup("thorn_mail", 9)
        by, far = self.place(foe(19.5, 21.5, BASE), foe(19.5, 25, BASE))
        self.hurt(10)
        self.tick()
        self.assertAlmostEqual(BASE - by.hp, BASE - self.attacker.hp)
        self.assertEqual(far.hp, BASE)
        self.assertEqual(by.status.stacks("bleed"), config.BARBS)     # (Barbs on those too)


class WardweaveTest(_Chest):
    def test_static_weave(self):
        s, h = self.setup("ward_charm", 3)
        h.shield = h.stats.shield
        near = self.place(foe(21.5, 20.5, BASE))[0]
        self.hurt(h.shield + 5)
        self.tick()
        self.assertTrue(near.status.has("shock"))
        self.assertTrue(self.attacker.status.has("shock"))

    def test_overcharge(self):
        s, h = self.setup("ward_charm", 6)
        h.shield = h.stats.shield
        self.assertAlmostEqual(s.rules.attack_mods(s.me)["mult"], 1 + config.OVERCHARGE)
        self.hurt(5)
        self.assertAlmostEqual(s.rules.attack_mods(s.me)["mult"], 1.0)

    def test_second_ward(self):
        s, h = self.setup("ward_charm", 9)
        h.shield = h.stats.shield
        self.tick(config.SECOND_WARD[0] + 0.1)
        self.assertAlmostEqual(h.shield, h.stats.shield * (1 + config.SECOND_WARD[1]))


class AnvilTest(_Chest):
    def test_tempered(self):
        s, h = self.setup("heavy_plate", 3)
        self.hurt(1000)
        self.assertEqual(len(h.temper), 1)
        h.hp = h.max_hp
        small = self.hurt(5)
        self.assertLess(small, 5)                                   # (+1 armor)
        self.tick(config.TEMPERED[1] + 0.1)
        self.assertFalse(h.temper)

    def test_lighter_steel(self):
        moves = lambda lv: [v for st, op, v in gear.power_steps("heavy_plate", lv) if st == "move"]
        self.assertEqual(moves(5), [-0.15])
        self.assertEqual(moves(6), [])

    def test_anvil_stance(self):
        s, h = self.setup("heavy_plate", 9)
        self.assertAlmostEqual(self.hurt(1000), h.max_hp * 0.10)
        h.hp = h.max_hp
        h.temper = []
        self.tick(config.ANVIL_STANCE[0] + 0.05)
        self.assertAlmostEqual(self.hurt(1000), h.max_hp * config.ANVIL_STANCE[1])


class ShattercoatTest(_Chest):
    def test_crystal_clear(self):
        s, h = self.setup("glass_cannon", 3)
        s.projectiles[:] = [Projectile(25, 20.5, math.pi, SHOT, owner=self.attacker),
                            Projectile(21, 20.5, 0.0, SHOT, owner=h)]
        with mock.patch.object(characters.pygame.draw, "line") as line:
            characters.draw_chest_marks(s.manager.text, s.me.camera, s.me, s.projectiles, 0)
        self.assertEqual(line.call_count, 1)

    def test_prism_skin(self):
        s, h = self.setup("glass_cannon", 6)
        h.since_hit = config.PRISM_SKIN
        self.assertEqual(self.hurt(20), 0.0)
        self.assertEqual(h.blocked, 1)
        self.assertGreater(self.hurt(20), 0)

    def test_diamond(self):
        s, h = self.setup("glass_cannon", 9)
        a = foe(25, 20.5, 5000)
        h.since_hit = 0.0
        plain = combat.strike(a, 10, h, 0.0, [])
        h.since_hit = config.DIAMOND[0]
        self.assertAlmostEqual(combat.strike(a, 10, h, 0.0, []) / plain, config.DIAMOND[1])


class GrudgeTest(_Chest):
    def test_recoil(self):
        s, h = self.setup("retaliation", 3)
        self.hurt(5)
        self.tick()
        self.assertAlmostEqual(h.x, 20.5 + config.RECOIL, places=3)

    def test_rising_grudge(self):
        s, h = self.setup("retaliation", 6)
        self.hurt(1, stay=True)
        self.tick()
        self.assertGreater(s.me.retaliate_cd, 0)
        self.hurt(1, stay=True)
        self.hurt(1, stay=True)
        self.tick()
        self.assertEqual(h.grudge, 2 * config.RISING_GRUDGE[0])
        s.me.retaliate_cd = 0.0
        hp = self.attacker.hp
        self.hurt(1, stay=True)
        self.tick()
        self.assertEqual(h.grudge, 0.0)
        self.assertGreater(hp - self.attacker.hp, config.RETALIATION[0])

    def test_seething(self):
        s, h = self.setup("retaliation", 9)
        hp = self.attacker.hp
        self.hurt(config.SEETHING / 2, stay=True)
        self.tick()
        self.assertEqual(self.attacker.hp, hp)
        self.hurt(config.SEETHING * 2, stay=True)
        self.tick()
        hp = self.attacker.hp
        self.assertLess(hp, BASE)
        self.hurt(config.SEETHING * 2, stay=True)                               # (no cooldown)
        self.tick()
        self.assertLess(self.attacker.hp, hp)


class SpotlessTest(_Chest):
    def test_clean_getaway(self):
        s, h = self.setup("untouched", 3)
        self.tick()
        h.hp = h.max_hp * 0.85
        self.tick()
        self.assertEqual(h.getaway, config.CLEAN_GETAWAY[1] - 0.0)
        self.go(DT)
        self.assertAlmostEqual(h.speed_mult, 1 + config.CLEAN_GETAWAY[0])
        self.go(config.CLEAN_GETAWAY[1])
        self.assertEqual(h.speed_mult, 1.0)

    def test_dress_code(self):
        s, h = self.setup("untouched", 6)
        self.assertEqual(combat.ground_cut(h), config.DRESS_CODE)
        full = combat.blast(h.x, h.y, 2.0, 20, self.attacker, [h], ground=True)
        self.assertTrue(full)
        self.assertAlmostEqual(h.max_hp - h.hp, 20 * config.DRESS_CODE)
        h.hp = h.max_hp * 0.5
        self.assertEqual(combat.ground_cut(h), 1.0)

    def test_immaculate(self):
        s, h = self.setup("untouched", 9)
        st, a = h.stats, foe(25, 20.5)
        bonus = lambda: combat.situational_bonus(st, h, a)
        h.hp = h.max_hp * 0.4
        low = bonus()
        h.hp = h.max_hp * 0.7
        self.assertAlmostEqual(bonus() - low, st.untouched / 2)
        h.hp = h.max_hp
        self.assertAlmostEqual(bonus() - low, st.untouched)


class WolfpeltTest(_Chest):
    def test_thick_fur(self):
        s, h = self.setup("berserker", 3)
        h.hp = h.max_hp * 0.6
        high = self.hurt(10)
        h.hp = h.max_hp * 0.4
        self.assertAlmostEqual(self.hurt(10) / high, config.THICK_FUR[1])

    def test_bloodrage(self):
        s, h = self.setup("berserker", 6)
        self.assertEqual(s.rules.weapon_dt(s.me, DT), DT)
        h.hp = h.max_hp * 0.2
        self.assertAlmostEqual(s.rules.weapon_dt(s.me, DT), DT * config.BLOODRAGE[1])

    def test_last_stand(self):
        s, h = self.setup("berserker", 9)
        h.hp = h.max_hp * 0.2
        self.hurt(1000)
        self.assertEqual(h.hp, 1.0)
        self.hurt(1000)
        self.assertEqual(h.hp, 1.0)
        self.tick(config.LAST_STAND[1] + 0.1)
        self.hurt(1000)
        self.assertFalse(h.alive)                                   # (once every 30 s)


class BastionTest(_Chest):
    def test_fortify(self):
        s, h = self.setup("bulwark", 3)
        h.max_hp = config.HEROES[s.me.stats.hero].max_hp + 50
        h.hp = 10.0
        self.tick(1.0)
        self.assertAlmostEqual(h.hp - 10.0, 5 * config.FORTIFY, places=2)

    def test_garrison(self):
        s, h = self.setup("bulwark", 6, walls=[(22, 20)])
        st, a = h.stats, foe(25, 20.5)
        self.tick()
        self.assertTrue(h.near_wall)
        near = combat.situational_bonus(st, h, a)
        h.x = 10.5
        self.tick()
        self.assertFalse(h.near_wall)
        self.assertAlmostEqual(near - combat.situational_bonus(st, h, a), config.GARRISON[1])

    def test_citadel(self):
        s, h = self.setup("bulwark", 9)
        st, a = h.stats, foe(25, 20.5)
        h.shield = 0.0
        bare = combat.situational_bonus(st, h, a)
        h.shield = 50.0
        self.assertAlmostEqual(combat.situational_bonus(st, h, a) - bare, 0.05)


class MountainhideTest(_Chest):
    def shot(self):
        q = Projectile(h_x := self.h.x - 0.5, self.h.y, 0.0, SHOT, owner=self.attacker, damage=10)
        return combat._hit_actor(q, self.h, h_x, self.h.y, self.s.world, [], [])

    def test_glance(self):
        s, h = self.setup("juggernaut", 3)
        h.stats.flags.discard("juggernaut+L")     # (M28.3c: not Stoneskin, which blocks it too)
        h.stats.armor = 40
        h.rng.random = lambda: config.GLANCE[1] - 0.01
        self.assertEqual(self.shot(), [])
        self.assertEqual(h.hp, h.max_hp)
        h.rng.random = lambda: config.GLANCE[1] + 0.01
        self.shot()
        self.assertLess(h.hp, h.max_hp)

    def test_tremor(self):
        s, h = self.setup("juggernaut", 6)
        near = self.place(foe(21.5, 20.5, BASE))[0]
        self.tick(1.0)
        self.assertEqual(near.hp, BASE)                              # (standing still)
        h.vx = 3.0
        self.tick(1.0)
        self.assertLess(near.hp, BASE)

    def test_peak(self):
        s, h = self.setup("juggernaut", 9)
        st, a = h.stats, foe(25, 20.5)
        st.armor = 0
        bare = combat.situational_bonus(st, h, a)
        st.armor = 10
        self.assertAlmostEqual(combat.situational_bonus(st, h, a) - bare, 10 * config.JUGGERNAUT * 2)


class AegisTest(_Chest):
    def test_radiant(self):
        s, h = self.setup("aegis", 3)
        near = self.place(foe(21.5, 20.5, BASE))[0]
        self.tick()
        self.assertIsNone(near.status)
        h.shield = 20.0
        self.tick(0.1)
        self.assertTrue(near.status.has("burn"))

    def test_corona_burst(self):
        s, h = self.setup("aegis", 6)
        near = self.place(foe(22.5, 20.5, BASE))[0]
        h.shield = 20.0
        self.hurt(30)
        self.tick()
        self.assertAlmostEqual(BASE - near.hp, 20.0)

    def test_eternal_day(self):
        s, h = self.setup("aegis", 9)
        h.shield = 0.0
        self.tick(1.0)
        self.assertAlmostEqual(h.shield, h.max_hp * config.ETERNAL_DAY[0], delta=0.05)
        self.tick(30.0)
        self.assertAlmostEqual(h.shield, h.max_hp * config.ETERNAL_DAY[1])


class PhoenixTest(_Chest):
    def rise(self):
        h = self.h
        h.hp = 0.0
        return self.s.rules.revive(self.s.me)

    def test_ashes(self):
        s, h = self.setup("phoenix", 3)
        self.assertTrue(self.rise())
        ring = [z for z in s.zones if z.kind == "trail" and z.source is h]
        self.assertEqual(len(ring), config.ASHES[0])
        self.assertTrue(all(z.life == config.ASHES[2] for z in ring))

    def test_rebirth(self):
        s, h = self.setup("phoenix", 6)
        self.assertTrue(self.rise())
        self.assertEqual(h.untouchable, config.REBIRTH)

    def test_undying_flame(self):
        s, h = self.setup("phoenix", 9)
        s.me.hero.stats.revives = 0
        self.assertTrue(self.rise())
        self.assertTrue(self.rise())
        self.assertFalse(self.rise())


if __name__ == "__main__":
    unittest.main()
