"""M28.3e: the head's legendary tricks (design/GEAR.md 19.3)."""

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.players import gear
from ascii_adventurers.systems import combat, statuses
from ascii_adventurers.systems.statuses import inflict
from ascii_adventurers.tests.test_m28_2c import DT
from ascii_adventurers.tests.test_m28_3c import BASE, _Legend, plain

HEAD = ("kindling", "wildfire", "venom", "virulence", "frostbite", "shatter", "static",
        "serrated", "hemorrhage", "thermal_shock", "toxic_current")


class _Head(_Legend):
    def tick(self, seconds, actors=None):
        s = self.s
        for _ in range(round(seconds * 60)):
            self.h.time += DT
            statuses.update_statuses(actors if actors is not None else s.enemies, DT,
                                     s.effects, s.world)

    def ticked(self, rarity, key, name, stacks, seconds=1.0, rng=0.99):
        """Damage `stacks` of `name` deal in `seconds`, from a hero wearing `key`."""
        s, h = self.setup(key, rarity)
        h.rng.random = lambda: rng
        e = self.place(plain(30.0, 30.5))[0]
        inflict(e, name, h, stacks)
        self.tick(seconds)
        return BASE - e.hp


class FrameworkTest(unittest.TestCase):
    def test_every_head_piece_has_its_legendary_trick(self):
        heads = [k for k, g in config.GEAR.items() if g.slot == "head"]
        self.assertEqual(sorted(heads), sorted(HEAD))
        for key in HEAD:
            name, text = gear.legendary_trick(key)
            self.assertTrue(name and text and text.isascii(), key)


class BrushfireTest(_Head):
    def walk(self, rarity):
        s, h = self.setup("kindling", rarity)
        e = self.place(plain(30.5, 30.5))[0]
        inflict(e, "burn", h, 2)
        for k in range(4):
            e.x += 1.0
            self.tick(DT)
            s.rules.resolve_combos()
        return [z for z in s.zones if z.kind == "trail" and z.source is h]

    def test_a_burning_enemy_lights_its_way(self):
        lit = self.walk("legendary")
        self.assertEqual(len(lit), 4)                     # (each tile it stepped onto)
        self.assertTrue(all(z.inflicts == "burn" and z.life == config.BRUSHFIRE for z in lit))

    def test_not_without_the_trick(self):
        self.assertEqual(self.walk("epic"), [])


class RadiantHeatTest(_Head):
    def bonus(self, rarity, gap):
        s, h = self.setup("wildfire", rarity)
        hot, near = self.place(plain(30.0, 30.5), plain(30.0 + gap, 30.5))
        inflict(hot, "burn", h, 1)
        self.tick(DT)
        return combat.situational_bonus(h.stats, h, near)

    def test_near_a_burning_enemy_counts_as_burning(self):
        s, h = self.setup("wildfire")
        base = combat.situational_bonus(h.stats, h, plain(60.0, 60.5))
        self.assertAlmostEqual(self.bonus("legendary", 1.5) - base, self.h.stats.wildfire)
        self.assertAlmostEqual(self.bonus("legendary", config.RADIANT_HEAT + 2.0), base)

    def test_not_without_the_trick(self):
        s, h = self.setup("wildfire", "epic")
        base = combat.situational_bonus(h.stats, h, plain(60.0, 60.5))
        self.assertAlmostEqual(self.bonus("epic", 1.5), base)


class VenomSacsTest(_Head):
    def test_poison_ticks_crit(self):
        plain_dot = self.ticked("legendary", "venom", "poison", 2, rng=0.99)
        crit_dot = self.ticked("legendary", "venom", "poison", 2, rng=0.0)
        self.assertAlmostEqual(crit_dot / plain_dot, self.h.stats.crit_damage, places=4)
        self.assertAlmostEqual(self.ticked("epic", "venom", "poison", 2, rng=0.0), plain_dot)


class PestilenceTest(_Head):
    def test_no_cap_and_half_past_ten(self):
        ten = self.ticked("legendary", "virulence", "poison", 10)
        fifteen = self.ticked("legendary", "virulence", "poison", 15)
        self.assertEqual(self.s.enemies[0].status.stacks("poison"), 15)
        self.assertAlmostEqual(fifteen / ten, (10 + 5 * config.PESTILENCE) / 10, places=4)

    def test_capped_without_the_trick(self):
        self.ticked("epic", "virulence", "poison", 15)
        self.assertEqual(self.s.enemies[0].status.stacks("poison"), config.VIRULENCE[0])


class DeepFreezeTest(_Head):
    def boss(self, rarity):
        s, h = self.setup("frostbite", rarity)
        b = self.place(plain(30.0, 30.5))[0]
        b.boss = True
        return s, h, b

    def test_ten_chill_stacks_freeze_a_boss(self):
        s, h, b = self.boss("legendary")
        most, seconds, gap = config.DEEP_FREEZE
        for _ in range(most - 1):
            inflict(b, "chill", h)
        self.assertEqual(b.status.frozen, 0.0)
        inflict(b, "chill", h)
        self.assertAlmostEqual(b.status.frozen, seconds)
        for _ in range(most):                             # (not again so soon)
            inflict(b, "chill", h)
        self.tick(seconds + 0.1, [b])
        self.assertEqual(b.status.frozen, 0.0)

    def test_the_game_stops_a_frozen_boss(self):
        s, h, b = self.boss("legendary")
        thought = []
        b.think = lambda ctx, dt: thought.append(dt)
        b.tick_flash = lambda dt: None
        b.hear = lambda *a: None
        for _ in range(config.DEEP_FREEZE[0]):
            inflict(b, "chill", h)
        s._step(DT)
        self.assertEqual(thought, [])

    def test_never_without_the_trick(self):
        s, h, b = self.boss("epic")
        for _ in range(20):
            inflict(b, "chill", h)
        self.assertEqual(b.status.frozen, 0.0)


class FlashFreezeTest(_Head):
    def died_chilled(self, rarity):
        s, h = self.setup("shatter", rarity)
        dying, near = self.place(plain(30.0, 30.5), plain(30.8, 30.5))
        inflict(dying, "chill", h)
        dying.hp = 0.0
        s.rules.on_kill(s.me, dying)
        return near

    def test_a_chilled_death_shatters(self):
        self.assertLess(self.died_chilled("legendary").hp, BASE)

    def test_not_without_the_trick(self):
        self.assertEqual(self.died_chilled("epic").hp, BASE)


class ShortCircuitTest(_Head):
    def hits(self, rarity, boss=False):
        s, h = self.setup("static", rarity)
        e = self.place(plain(21.5, 20.5))[0]
        e.boss = boss
        inflict(e, "shock", h)
        h.stats.armor = 0.0
        return [h.take_damage(10.0, e, None) > 0 for _ in range(4)]

    def test_every_other_hit_fizzles(self):
        self.assertEqual(self.hits("legendary"), [True, False, True, False])

    def test_not_bosses_nor_without_the_trick(self):
        self.assertEqual(self.hits("legendary", boss=True), [True] * 4)
        self.assertEqual(self.hits("epic"), [True] * 4)


class BloodlettingTest(_Head):
    def test_bleed_ticks_heal_you_up_to_five_a_second(self):
        s, h = self.setup("serrated")
        h.hp = h.max_hp - 50
        foes = self.place(*[plain(30.0 + k, 30.5) for k in range(10)])
        for e in foes:
            inflict(e, "bleed", h)
        hp = h.hp
        self.tick(1.0)
        healed = h.hp - hp
        heal, most = config.BLOODLETTING
        self.assertGreater(healed, 0)
        self.assertLessEqual(healed, heal * most + 1e-9)

    def test_not_without_the_trick(self):
        s, h = self.setup("serrated", "epic")
        h.hp = h.max_hp - 50
        inflict(self.place(plain(30.0, 30.5))[0], "bleed", h)
        hp = h.hp
        self.tick(1.0)
        self.assertEqual(h.hp, hp)


class BloodRushTest(_Head):
    def rate(self, rarity, moving):
        s, h = self.setup("hemorrhage", rarity)
        e = self.place(plain(30.0, 30.5))[0]
        inflict(e, "bleed", h)
        h.vx = 3.0 if moving else 0.0
        h.vy = 0.0
        return e.status._rate(e, "bleed", e.status.active["bleed"], False)

    def test_your_moving_counts(self):
        self.assertAlmostEqual(self.rate("legendary", True), config.BLOOD_RUSH)
        self.assertAlmostEqual(self.rate("legendary", False), 1.0)
        self.assertAlmostEqual(self.rate("epic", True), 1.0)


class VolatileMixTest(_Head):
    def mix(self, rarity):
        s, h = self.setup("thermal_shock", rarity)
        sick, near = self.place(plain(30.0, 30.5), plain(30.8, 30.5))
        inflict(sick, "poison", h, 3)
        inflict(sick, "bleed", h, 1)
        s.rules.resolve_combos()
        return sick, near

    def test_any_two_statuses_burst(self):
        sick, near = self.mix("legendary")
        self.assertLess(near.hp, BASE)
        self.assertEqual(sorted(sick.status.active), ["poison"])   # (the fewer stacks went)

    def test_not_without_the_trick(self):
        sick, near = self.mix("epic")
        self.assertEqual(near.hp, BASE)


class FullCurrentTest(_Head):
    def current(self, rarity):
        s, h = self.setup("toxic_current", rarity)
        sick, near = self.place(plain(30.0, 30.5), plain(31.0, 30.5))
        inflict(sick, "burn", h, 2)
        inflict(sick, "bleed", h, 1)
        inflict(sick, "shock", h)
        s.rules.resolve_combos()
        return near

    def test_shocking_spreads_every_status(self):
        near = self.current("legendary")
        self.assertEqual(near.status.stacks("burn"), 2)
        self.assertEqual(near.status.stacks("bleed"), 1)
        self.assertFalse(near.status.has("shock"))

    def test_only_poison_without_the_trick(self):
        self.assertIsNone(self.current("epic").status)


if __name__ == "__main__":
    unittest.main()
