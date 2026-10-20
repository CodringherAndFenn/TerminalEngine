"""M28.3f: the feet's legendary tricks (design/GEAR.md 19.4)."""

import math
import os
import unittest
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.entities.projectile import Projectile
from ascii_adventurers.players import gear
from ascii_adventurers.players.controls import PlayerInput
from ascii_adventurers.systems import combat, roll
from ascii_adventurers.systems.collision import hull_hits_solid
from ascii_adventurers.tests.test_m28_2a import foe
from ascii_adventurers.tests.test_m28_2b import walker
from ascii_adventurers.tests.test_m28_2c import DT, SHOT, press
from ascii_adventurers.tests.test_m28_3c import BASE, _Legend, plain

FEET = ("riposte", "slipstream", "close_call", "scorched_trail", "momentum", "fleet_strike",
        "blink", "shoulder_charge", "backflip", "pirouette", "drop_the_beat")
HERO = {"blink": "wizard", "shoulder_charge": "dwarf", "backflip": "huntress",
        "pirouette": "princess", "drop_the_beat": "bard"}
R = config.HEROES["wizard"].size_px / 2 / config.TILE_PX_W + 0.15   # (the hero's hit radius)


class _Feet(_Legend):
    def setup(self, key, rarity="legendary", *more, hero=None, walls=()):
        s, h = super().setup(key, rarity, *more, hero=hero or HERO.get(key, "wizard"))
        if walls:
            from ascii_adventurers.tests.test_weapons import open_map
            s.world = open_map(80, 40, walls)
        return s, h

    def mine(self):
        return [q for q in self.s.projectiles if q.owner is self.h]


class FrameworkTest(unittest.TestCase):
    def test_every_feet_piece_has_its_legendary_trick(self):
        feet = [k for k, g in config.GEAR.items() if g.slot == "feet"]
        self.assertEqual(sorted(feet), sorted(FEET))
        for key in FEET:
            name, text = gear.legendary_trick(key)
            self.assertTrue(name and text and text.isascii(), key)


class CounterattackTest(_Feet):
    def test_a_hit_readies_a_riposte(self):
        s, h = self.setup("riposte")
        e = foe(26, 20.5, BASE)
        self.assertNotIn("sure_crit", s.rules.attack_mods(s.me))
        h.take_damage(10, e, None)
        self.assertTrue(s.rules.attack_mods(s.me).get("sure_crit"))
        self.assertNotIn("sure_crit", s.rules.attack_mods(s.me))     # (just the one)
        h.time += config.COUNTERATTACK / 2
        h.take_damage(10, e, None)                                    # (too soon)
        self.assertNotIn("sure_crit", s.rules.attack_mods(s.me))
        h.time += config.COUNTERATTACK / 2
        h.take_damage(10, e, None)
        self.assertTrue(s.rules.attack_mods(s.me).get("sure_crit"))

    def test_not_without_the_trick(self):
        s, h = self.setup("riposte", "epic")
        h.take_damage(10, foe(26, 20.5, BASE), None)
        self.assertNotIn("sure_crit", s.rules.attack_mods(s.me))


class TailwindTest(_Feet):
    def test_the_slipstreams_speed_is_attack_speed(self):
        s, h = self.setup("slipstream")
        h.stats.move = 0.2
        h.slipstream, h.speed_mult = 1.0, 1 + config.SLIPSTREAM[0]
        self.assertAlmostEqual(s.rules.weapon_dt(s.me, DT), DT * (1 + 0.2 + config.SLIPSTREAM[0]))
        h.slipstream, h.speed_mult = 0.0, 1.0
        self.assertAlmostEqual(s.rules.weapon_dt(s.me, DT), DT)

    def test_not_without_the_trick(self):
        s, h = self.setup("slipstream", "epic")
        h.slipstream, h.speed_mult = 1.0, 1 + config.SLIPSTREAM[0]
        self.assertAlmostEqual(s.rules.weapon_dt(s.me, DT), DT)


class NearMissTest(_Feet):
    def pass_by(self, rarity, gap, rolling=False):
        """A shot flying past the hero, `gap` from their middle; the
        recharge it gave."""
        s, h = self.setup("close_call", rarity)
        shooter = foe(40, 20.5)
        if rolling:
            q = Projectile(h.x + 1.2, h.y + gap, math.pi, SHOT, owner=shooter, damage=10)
            s.projectiles.append(q)
            self.go(0.25, first=press(1, 0))
            return h.roll_grazes
        h.roll_charges = 0
        q = Projectile(h.x + 3.0, h.y + gap, math.pi, SHOT, owner=shooter, damage=10)
        s.projectiles.append(q)
        self.go(1.0)
        moved = h.roll_recharge
        return moved - 1.0                                   # (less the second's own)

    def test_a_shot_passing_near_counts(self):
        near = self.pass_by("legendary", R + 0.7)
        self.assertAlmostEqual(near, config.CLOSE_CALL, delta=0.02)
        far = self.pass_by("legendary", R + config.NEAR_MISS + 0.5)
        self.assertAlmostEqual(far, 0.0, delta=0.02)

    def test_counted_once(self):
        self.pass_by("legendary", R + 0.7)
        self.assertEqual(len(self.h.near_missed), 1)
        self.go(0.5)
        self.assertAlmostEqual(self.h.roll_recharge, 1.5 + config.CLOSE_CALL, delta=0.02)

    def test_rolling_too(self):
        gap = R + 0.7
        self.assertEqual(self.pass_by("legendary", gap, rolling=True), 1)
        self.assertEqual(self.pass_by("epic", gap, rolling=True), 0)

    def test_not_without_the_trick(self):
        self.assertAlmostEqual(self.pass_by("epic", R + 0.7), 0.0, delta=0.02)


class FireWallTest(_Feet):
    def burnt(self, rarity, lob=False):
        s, h = self.setup("scorched_trail", rarity)
        self.roll()
        z = min((z for z in s.zones if z.kind == "trail"), key=lambda z: z.x)
        shell = config.SNOW_SHOTS["shard"]
        q = Projectile(z.x, z.y - 2.5, math.pi / 2, shell, owner=foe(z.x, 10.0), damage=10)
        s.projectiles.append(q)
        self.go(0.5)
        return q

    def test_enemy_shots_burn_up_over_your_fire(self):
        q = self.burnt("legendary")
        self.assertFalse(q.alive)
        self.assertTrue(any(e.kind == "fizzle" for e in self.s.effects))

    def test_not_without_the_trick(self):
        self.assertTrue(self.burnt("epic").alive)


class IronHoovesTest(_Feet):
    def hurt(self, rarity, move):
        s, h = self.setup("momentum", rarity)
        h.stats.move = move
        h.stats.armor = 0.0
        hp = h.hp
        h.take_damage(100.0, foe(26, 20.5), None)
        return hp - h.hp

    def test_the_bonus_cuts_the_damage_you_take(self):
        self.assertAlmostEqual(self.hurt("legendary", 0.4), 100.0 * (1 - 0.2))
        self.assertAlmostEqual(self.hurt("legendary", 2.0), 100.0 * (1 - config.IRON_HOOVES))
        self.assertAlmostEqual(self.hurt("epic", 0.4), 100.0)


class BlurTest(_Feet):
    def crit(self, rarity, moving):
        s, h = self.setup("fleet_strike", rarity)
        rolls = iter([0.99, 0.0])
        h.rng.random = lambda: next(rolls, 0.99)
        h.vx = 3.0 if moving else 0.0
        combat.strike(plain(24, 20.5), 1, h, 0.0, s.effects, on_hit=False)
        return h.last_crit

    def test_moving_a_hit_rolls_twice(self):
        self.assertTrue(self.crit("legendary", True))
        self.assertFalse(self.crit("legendary", False))
        self.assertFalse(self.crit("epic", True))


class MindsEyeTest(_Feet):
    def blink(self, rarity, aim):
        s, h = self.setup("blink", rarity)
        h.aim_point = (h.x + aim[0], h.y + aim[1])
        h.aim_angle = math.atan2(aim[1], aim[0])
        self.roll(1, 0, seconds=DT)
        return h.x - 20.5, h.y - 20.5

    def test_the_blink_goes_where_you_aim(self):
        x, y = self.blink("legendary", (0.0, 3.0))
        self.assertAlmostEqual(x, 0.0, delta=0.05)
        self.assertAlmostEqual(y, 3.0, delta=0.05)
        x, y = self.blink("legendary", (8.0, 8.0))                     # (8 tiles at most)
        self.assertAlmostEqual(math.hypot(x, y), config.MINDS_EYE, delta=0.05)
        self.assertAlmostEqual(x, y, delta=0.05)

    def test_where_you_move_without_the_trick(self):
        x, y = self.blink("epic", (0.0, 3.0))
        self.assertAlmostEqual(x, config.BLINK[0], delta=0.05)
        self.assertAlmostEqual(y, 0.0, delta=0.05)


class MountainMoverTest(_Feet):
    def charge(self, rarity, boss=True):
        s, h = self.setup("shoulder_charge", rarity)
        b = self.place(walker(22.0, 20.5, BASE))[0]
        b.boss = boss
        self.roll()
        return BASE - b.hp, b.x - 22.0

    def test_bosses_are_shoved_and_take_double(self):
        lost, moved = self.charge("legendary")
        self.assertAlmostEqual(moved, config.MOUNTAIN_MOVER[0], delta=0.05)
        plain_lost, plain_moved = self.charge("legendary", boss=False)   # (others as before)
        self.assertAlmostEqual(plain_moved, config.SHOULDER_CHARGE[2], delta=0.05)
        self.assertAlmostEqual(lost, plain_lost * config.MOUNTAIN_MOVER[1])

    def test_bosses_dont_budge_without_the_trick(self):
        lost, moved = self.charge("epic")
        self.assertEqual(moved, 0.0)


class VaultTest(_Feet):
    WALL = [(x, y) for x in (22, 23) for y in range(15, 26)]

    def vault(self, rarity, walls=None, lair=None):
        s, h = self.setup("backflip", rarity, walls=self.WALL if walls is None else walls)
        h.aim_angle = math.pi / 2                       # (the arrows go elsewhere)
        if lair is not None:
            s.quests = SimpleNamespace(states={"q": SimpleNamespace(lair=lair)})
        self.roll(1, 0, seconds=0.6)
        self.assertFalse(h.rolling)
        self.assertFalse(hull_hits_solid(s.world, h.x, h.y, 0.0, h.half, h.half))
        return h.x

    def test_over_a_wall(self):
        self.assertGreater(self.vault("legendary"), 24.0)

    def test_on_past_it_to_land_clear(self):
        thick = [(x, y) for x in range(22, 25) for y in range(15, 26)]
        self.assertGreater(self.vault("legendary", walls=thick), 25.0)

    def test_an_ordinary_roll_with_nowhere_to_land(self):
        thick = [(x, y) for x in range(22, 30) for y in range(15, 26)]
        self.assertLess(self.vault("legendary", walls=thick), 22.0)

    def test_never_out_of_a_lair(self):
        lair = SimpleNamespace(inside=lambda x, y: x < 23.5)
        self.assertLess(self.vault("legendary", lair=lair), 22.0)

    def test_walls_stop_it_without_the_trick(self):
        self.assertLess(self.vault("epic"), 22.0)


class BalletTest(_Feet):
    def test_standing_still_spins_the_ring(self):
        s, h = self.setup("pirouette")
        self.go(config.BALLET - 0.1)
        self.assertEqual(self.mine(), [])
        self.go(0.15)
        self.assertEqual(len(self.mine()), config.PIROUETTE[0])
        with mock.patch.object(roll, "_pirouette", wraps=roll._pirouette) as spun:
            self.go(config.BALLET)
        self.assertEqual(spun.call_count, 1)                           # (every 2 s)

    def test_not_while_moving(self):
        s, h = self.setup("pirouette")
        self.go(config.BALLET * 2, PlayerInput(1, 0))
        self.assertEqual(self.mine(), [])

    def test_not_without_the_trick(self):
        s, h = self.setup("pirouette", "epic")
        self.go(config.BALLET + 0.1)
        self.assertEqual(self.mine(), [])


class GroundWaveTest(_Feet):
    def wave(self, rarity):
        s, h = self.setup("drop_the_beat", rarity)
        reach = h.weapon.spec.reach
        end = 20.5 + config.ROLL_DISTANCE
        on, past, aside = self.place(plain(end + reach + 3.0, 20.5), plain(end + reach + 7.0, 20.5),
                                     plain(end + reach + 3.0, 24.0))
        with mock.patch.object(combat, "first_hit", return_value=None):
            self.roll(seconds=1.0)
        return on, past, aside

    def test_the_beat_runs_on_as_a_wave(self):
        on, past, aside = self.wave("legendary")
        self.assertLess(on.hp, BASE)
        self.assertEqual(past.hp, BASE)                  # (5 tiles past the beat)
        self.assertEqual(aside.hp, BASE)                 # (along the roll's line)
        self.assertEqual(self.h.waves, [])

    def test_a_wall_stops_it(self):
        s, h = self.setup("drop_the_beat")
        reach = h.weapon.spec.reach
        end = 20.5 + config.ROLL_DISTANCE
        from ascii_adventurers.tests.test_weapons import open_map
        s.world = open_map(80, 40, [(round(end + reach + 1), 20)])
        on = self.place(plain(end + reach + 3.0, 20.5))[0]
        self.roll(seconds=1.0)
        self.assertEqual(on.hp, BASE)

    def test_not_without_the_trick(self):
        on, past, aside = self.wave("epic")
        self.assertEqual(on.hp, BASE)


if __name__ == "__main__":
    unittest.main()
