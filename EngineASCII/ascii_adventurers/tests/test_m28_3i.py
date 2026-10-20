"""M28.3i: the trinkets' legendary tricks (design/GEAR.md 19.7)."""

import math
import os
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.players import gear
from ascii_adventurers.systems import combat, spells
from ascii_adventurers.systems.zones import Zone, update_zones
from ascii_adventurers.tests.test_m28_2c import DT
from ascii_adventurers.tests.test_m28_3c import BASE, _Legend, plain

TRINKETS = ("chain_lightning", "daggers", "ember_aura", "frost_nova", "spirit_wolf", "rune_trap",
            "poison_flask", "storm_cloud", "healing_totem", "fire_wand", "bone_turret")


class _Trinket(_Legend):
    def spell(self, key):
        return self.s.me.spells[key]

    def step(self, seconds, zones=True):
        s, h = self.s, self.h
        for _ in range(max(1, round(seconds * 60))):
            h.time += DT
            spells.update_spells(h, s.me.spells, s.world, s._actors(), s.effects, DT,
                                 s.projectiles, s.zones)
            combat.update_projectiles(s.projectiles, s.world, s.effects, DT, s._actors(), s.zones)
            if zones:
                update_zones(s.zones, s._actors(), s.effects, DT, s.world)
            s.rules.resolve_combos()


class FrameworkTest(unittest.TestCase):
    def test_every_trinket_has_its_legendary_trick(self):
        trinkets = [k for k, g in config.GEAR.items() if g.slot == "trinket"]
        self.assertEqual(sorted(trinkets), sorted(TRINKETS))
        for key in TRINKETS:
            name, text = gear.legendary_trick(key)
            self.assertTrue(name and text and text.isascii(), key)


class ConduitTest(_Trinket):
    def crits(self, rarity, n, other=True):
        s, h = self.setup("chain_lightning", rarity)
        self.spell("chain_lightning").timer = 99.0          # (its own casts out of the way)
        hit = self.place(plain(24.0, 20.5))[0]
        if other:
            self.place(plain(27.0, 20.5))
        for _ in range(n):
            combat.strike(hit, 1, h, 0.0, s.effects, sure_crit=True)
            s.rules.resolve_combos()
        return [q for q in s.projectiles if q.charm]

    def test_a_crit_casts_a_bolt_from_its_enemy(self):
        bolts = self.crits("legendary", 1)
        self.assertEqual(len(bolts), 1)
        self.assertAlmostEqual(bolts[0].x, 24.0)
        self.assertEqual(len(self.crits("legendary", 5)), config.CONDUIT)   # (3 a second)

    def test_nobody_to_bolt_nor_without_the_trick(self):
        self.assertEqual(self.crits("legendary", 1, other=False), [])
        self.assertEqual(self.crits("epic", 1), [])


class SatelliteTest(_Trinket):
    def test_the_daggers_circle_your_last_target(self):
        s, h = self.setup("daggers")
        e = self.place(plain(30.0, 20.5))[0]
        combat.strike(e, 1, h, 0.0, s.effects)
        self.assertEqual(spells.satellite_centre(h), (30.0, 20.5))
        r = e.hit_radius + config.SATELLITE[1]                # (tight round it)
        for x, y, _ in self.spell("daggers").dagger_positions(h):
            self.assertAlmostEqual(math.hypot(x - 30.0, y - 20.5), r, places=4)
        t = h.satellite[1]
        self.step(1.0)
        self.assertLess(e.hp, BASE - 1)                       # (they cut it)
        self.assertEqual(h.satellite[1], t)                   # (their hits don't count)
        h.time = t + config.SATELLITE[0] + 0.1
        self.assertEqual(spells.satellite_centre(h), (h.x, h.y))

    def test_back_to_you_when_it_dies_nor_without_the_trick(self):
        s, h = self.setup("daggers")
        e = self.place(plain(30.0, 20.5))[0]
        combat.strike(e, 1, h, 0.0, s.effects)
        e.hp = 0.0
        self.assertEqual(spells.satellite_centre(h), (h.x, h.y))
        s, h = self.setup("daggers", "epic")
        combat.strike(self.place(plain(30.0, 20.5))[0], 1, h, 0.0, s.effects)
        self.assertEqual(spells.satellite_centre(h), (h.x, h.y))


class AfterburnTest(_Trinket):
    def left_behind(self, rarity):
        s, h = self.setup("ember_aura", rarity)
        e = self.place(plain(20.5, 21.0))[0]
        self.step(DT)
        h.roll_from = (h.x, h.y)
        h.rolls += 1
        h.x += 8.0
        self.step(1.0)
        return e, self.spell("ember_aura")

    def test_the_aura_stays_where_you_rolled(self):
        e, s = self.left_behind("legendary")
        self.assertEqual(len(s.left), 1)
        self.assertGreater(e.status.stacks("burn"), 0)
        self.step(config.AFTERBURN)
        self.assertEqual(s.left, [])

    def test_not_without_the_trick(self):
        e, s = self.left_behind("epic")
        self.assertEqual(s.left, [])
        self.assertTrue(e.status is None or not e.status.has("burn"))


class BlackIceTest(_Trinket):
    def iced(self, rarity):
        s, h = self.setup("frost_nova", rarity)
        self.spell("frost_nova").timer = 0.0
        self.step(DT)
        self.spell("frost_nova").timer = 99.0                 # (just the one nova)
        return [z for z in s.zones if z.kind == "ice"]

    def test_the_ring_stays_icy(self):
        ice = self.iced("legendary")
        self.assertEqual(len(ice), 1)
        late = self.place(plain(22.0, 20.5))[0]               # (walks in after the nova)
        self.step(config.BLACK_ICE[1] + DT)
        self.assertEqual(late.status.stacks("chill"), 1)
        self.step(config.BLACK_ICE[0] * self.h.stats.duration_scale)
        self.assertEqual([z for z in self.s.zones if z.kind == "ice"], [])

    def test_not_without_the_trick(self):
        self.assertEqual(self.iced("epic"), [])


class SpiritPackTest(_Trinket):
    def chase(self, rarity):
        s, h = self.setup("spirit_wolf", rarity)
        from ascii_adventurers.tests.test_weapons import open_map
        s.world = open_map(80, 40, [(23, y) for y in range(10, 31)])
        self.place(plain(27.0, 20.5))
        self.step(1.0)
        return self.spell("spirit_wolf").things[0]["x"]

    def test_wolves_run_through_walls(self):
        self.assertGreater(self.chase("legendary"), 24.0)
        self.assertLess(self.chase("epic"), 23.0)


class RekindledTest(_Trinket):
    def test_a_burst_rune_comes_back_once(self):
        s, h = self.setup("rune_trap")
        st = self.spell("rune_trap")
        st.timer = 99.0
        st.things.append({"x": 25.0, "y": 20.5, "age": 0.0, "n": 1})
        e = self.place(plain(25.0, 20.5, 10 ** 6))[0]
        self.step(DT)
        self.assertEqual(st.things, [])
        e.x = 40.0                                            # (it moves off)
        self.step(config.REKINDLED)
        self.assertEqual(len(st.things), 1)
        self.assertEqual((st.things[0]["x"], st.things[0]["y"]), (25.0, 20.5))
        e.x = 25.0
        self.step(DT)                                         # (bursts again)
        self.assertEqual(st.things, [])
        e.x = 40.0
        self.step(config.REKINDLED + 0.5)
        self.assertEqual(st.things, [])                       # (and that's it)

    def test_not_without_the_trick(self):
        s, h = self.setup("rune_trap", "epic")
        st = self.spell("rune_trap")
        st.timer = 99.0
        st.things.append({"x": 25.0, "y": 20.5, "age": 0.0, "n": 1})
        self.place(plain(25.0, 20.5, 10 ** 6))
        self.step(config.REKINDLED + 0.1)
        self.assertEqual(st.things, [])


class LingeringTest(_Trinket):
    def pool(self, rarity):
        s, h = self.setup("poison_flask", rarity)
        self.spell("poison_flask").timer = 99.0
        z = Zone("pool", 25.0, 20.5, 1.0, 3.0, 0.5, 0.0, h, (), "poison", 1)
        z.flask, z.linger = True, rarity == "legendary"
        s.zones.append(z)
        return z

    def test_a_pool_lasts_while_an_enemy_stands_in_it(self):
        z = self.pool("legendary")
        e = self.place(plain(25.0, 20.5, 10 ** 6))[0]
        self.step(6.0)
        self.assertIn(z, self.s.zones)
        e.x = 40.0                                            # (it leaves)
        self.step(config.LINGERING[1] + 0.1)
        self.assertNotIn(z, self.s.zones)

    def test_ten_seconds_at_most(self):
        z = self.pool("legendary")
        self.place(plain(25.0, 20.5, 10 ** 6))
        self.step(config.LINGERING[0] + 0.1)
        self.assertNotIn(z, self.s.zones)

    def test_not_without_the_trick(self):
        z = self.pool("epic")
        self.place(plain(25.0, 20.5, 10 ** 6))
        self.step(3.1)
        self.assertNotIn(z, self.s.zones)


class StormFrontTest(_Trinket):
    def front(self, rarity):
        s, h = self.setup("storm_cloud", rarity)
        reach = self.spell("storm_cloud").params["reach"]
        h.aim_point = (h.x + 20.0, h.y)
        e = self.place(plain(h.x + config.STORM_FRONT[0] + reach - 0.5, h.y))[0]
        self.step(2.0)
        return e

    def test_the_cloud_drifts_ahead_and_strikes_from_there(self):
        e = self.front("legendary")
        h = self.h
        self.assertAlmostEqual(h.cloud_front[0] - h.x, config.STORM_FRONT[0], places=4)
        self.assertEqual(spells.cloud_position(h)[0], h.cloud_front[0] + spells.CLOUD_OFFSET[0])
        self.assertLess(e.hp, BASE)

    def test_over_you_without_the_trick(self):
        e = self.front("epic")
        self.assertIsNone(self.h.cloud_front)
        self.assertEqual(e.hp, BASE)


class LifelineTest(_Trinket):
    def healed(self, rarity):
        s, h = self.setup("healing_totem", rarity)
        st = self.spell("healing_totem")
        st.timer = 99.0
        st.things.append({"x": 40.0, "y": 20.5, "age": 0.0, "chill": 0.0, "in": []})
        h.hp = 10.0
        self.step(1.0)
        return h.hp - 10.0, st.params["heal"]

    def test_half_the_healing_from_afar(self):
        got, heal = self.healed("legendary")
        self.assertAlmostEqual(got, heal * config.LIFELINE, places=3)
        self.assertEqual(self.healed("epic")[0], 0.0)


class FireflyTest(_Trinket):
    def burns(self, rarity):
        s, h = self.setup("fire_wand", rarity)
        e = self.place(plain(24.0, 20.5, 10 ** 6))[0]
        st = self.spell("fire_wand")
        st.timer = 0.0
        with mock.patch.object(spells, "inflict", wraps=spells.inflict) as burn:
            self.step(0.4)
            st.timer = 99.0
            self.step(config.FIREFLY[0] + 0.2)
        return burn.call_count, e

    def test_a_bolt_stays_and_burns_on(self):
        n, e = self.burns("legendary")
        self.assertEqual(n, round(config.FIREFLY[0] / config.FIREFLY[1]))
        self.assertEqual(self.h.fireflies, [])                # (gone after 1.5 s)

    def test_not_without_the_trick(self):
        self.assertEqual(self.burns("epic")[0], 0)


class WalkingDeadTest(_Trinket):
    def walked(self, rarity):
        s, h = self.setup("bone_turret", rarity)
        st = self.spell("bone_turret")
        st.timer = 99.0
        st.things.append({"x": 20.5, "y": 20.5, "age": 0.0, "fire": 99.0})
        self.place(plain(28.0, 20.5, 10 ** 6))
        self.step(2.0)
        return st.things[0]["x"] - 20.5

    def test_turrets_walk_after_the_nearest_enemy(self):
        self.assertAlmostEqual(self.walked("legendary"), 2.0 * config.WALKING_DEAD[0], delta=0.05)
        self.assertEqual(self.walked("epic"), 0.0)

    def test_they_stop_short(self):
        s, h = self.setup("bone_turret")
        st = self.spell("bone_turret")
        st.timer = 99.0
        st.things.append({"x": 20.5, "y": 20.5, "age": 0.0, "fire": 99.0})
        e = self.place(plain(22.5, 20.5, 10 ** 6))[0]
        self.step(3.0)
        self.assertAlmostEqual(e.x - st.things[0]["x"], config.WALKING_DEAD[1] + e.hit_radius,
                               delta=0.05)


if __name__ == "__main__":
    unittest.main()
