"""M28.2b: the head's +3 / +6 / +9 tricks (design/GEAR.md 17.2)."""

import math
import os
import unittest
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from ascii_adventurers import config
from ascii_adventurers.ai.brain import AIContext
from ascii_adventurers.entities.projectile import Projectile
from ascii_adventurers.players import gear
from ascii_adventurers.systems import combat, statuses
from ascii_adventurers.systems.statuses import inflict, update_statuses
from ascii_adventurers.systems.zones import Zone, update_zones
from ascii_adventurers.tests.test_m16 import fly, game
from ascii_adventurers.tests.test_m28_2a import foe, wear
from ascii_adventurers.tests.test_weapons import open_map
from ascii_adventurers.world import tiles

DT = 1 / 60


def walker(x, y, hp=500, speed=3.0):
    """A foe that can be pushed and has a walking speed."""
    d = foe(x, y, hp)
    d.half = 0.3
    d.espec = SimpleNamespace(speed=speed)
    return d


def run(actors, seconds, world=None):
    effects = []
    for _ in range(round(seconds * 60)):
        update_statuses(actors, DT, effects, world)
    return effects


class _Case(unittest.TestCase):
    def setup(self, key, level, hero="wizard"):
        m, s = game(hero)
        wear(s, key, level)
        s.enemies.clear()
        s.projectiles.clear()
        statuses.combos.clear()
        h = s.hero
        h.rng.random = lambda: 0.99          # no crits, no status rolls of its own
        self.s, self.h = s, h
        return s, h

    def tearDown(self):
        statuses.combos.clear()
        if pygame.display.get_init():
            pygame.mouse.set_visible(True)

    def place(self, *foes):
        self.s.enemies.extend(foes)
        return foes

    def hit(self, victim, base=1.0, **kw):
        return combat.strike(victim, base, self.h, 0.0, self.s.effects, **kw)


class FrameworkTest(unittest.TestCase):
    def test_every_head_piece_has_three_tricks(self):
        head = [k for k, g in config.GEAR.items() if g.slot == "head"]
        self.assertEqual(len(head), 11)
        for key in head:
            self.assertEqual([t for t, _, _ in gear.tricks(key)], [3, 6, 9], key)
            for _, name, text in gear.tricks(key):
                self.assertTrue(name and text and text.isascii(), key)

    def test_the_slots_built_so_far(self):
        built = {config.GEAR[k].slot for k in config.GEAR_TRICKS}
        self.assertTrue({"off", "head"} <= built)      # (later steps add the rest)


class CinderveilTest(_Case):
    def test_kindle_burns_the_fourth_hit_in_a_row(self):
        s, h = self.setup("kindling", 3)
        a, b = self.place(foe(12, 10), foe(14, 10))
        for _ in range(3):
            self.hit(a)
        self.assertIsNone(a.status)
        self.hit(a)
        self.assertEqual(a.status.stacks("burn"), 1)
        # A hit on another enemy breaks the run.
        for _ in range(3):
            self.hit(b)
        self.hit(a)
        self.hit(b)
        self.assertIsNone(b.status)

    def test_smoke_hides_you_from_burning_enemies(self):
        from ascii_adventurers.tests.test_players import make
        s, h = self.setup("kindling", 6)
        h.x, h.y = 10.5, 10.5
        e = make("goblin_archer", h.x + 8, h.y)
        ctx = AIContext(open_map(), [h], [h, e], [], [])

        def sees():
            e._sense_timer = 0.0
            e.sense(ctx, DT)
            return e.sees_target

        self.assertTrue(sees())
        inflict(e, "burn", h)
        self.assertFalse(sees())
        e.x = h.x + config.SMOKE - 1
        self.assertTrue(sees())

    def test_pyre_burns_twice_as_fast(self):
        s, h = self.setup("kindling", 9)
        a, b = foe(12, 10, 5000), foe(14, 10, 5000)
        inflict(a, "burn", h, 5)
        self.assertGreater(a.status.active["burn"].pyre, 0)
        inflict(b, "burn", h, 4)
        inflict(b, "burn", h, 1)                  # (reaching 5 later counts too)
        b.status.active["burn"].pyre = 0.0        # but this one burns plain, to compare
        run([a, b], 1.0)
        self.assertAlmostEqual((5000 - a.hp) / (5000 - b.hp), config.PYRE[0], delta=0.05)


class BlazecrownTest(_Case):
    def test_fanned_flames_restart_the_burn(self):
        s, h = self.setup("wildfire", 3)
        a = foe(12, 10)
        inflict(a, "burn", h)
        a.status.active["burn"].left = 0.5
        self.hit(a)
        self.assertGreater(a.status.active["burn"].left, 2.0)

    def test_heat_haze_slows_a_burning_enemys_shots(self):
        s, h = self.setup("wildfire", 6)
        a, b = foe(12, 10), foe(12, 14)
        inflict(a, "burn", h)
        spec = config.SNOW_SHOTS["shard"]
        qa, qb = Projectile(a.x, a.y, 0.0, spec, owner=a), Projectile(b.x, b.y, 0.0, spec, owner=b)
        s.rules.enemy_shots([qa, qb])
        self.assertEqual((qa.pace, qb.pace), (config.HEAT_HAZE, 1.0))
        shots = [qa, qb]
        fly(shots, [], steps=30)
        self.assertAlmostEqual(qa.travelled / qb.travelled, config.HEAT_HAZE, places=3)

    def test_bonfire_grows_with_the_stacks(self):
        s, h = self.setup("wildfire", 9)
        a = foe(12, 10)
        st = h.stats
        grow = st.wildfire / config.WILDFIRE
        base = combat.situational_bonus(st, h, a)
        for n, want in ((1, 0.10), (3, 0.30), (5, 0.50)):
            a.status = None
            inflict(a, "burn", h, n)
            got = combat.situational_bonus(st, h, a) - base
            self.assertAlmostEqual(got, want * grow, places=6)


class ViperTest(_Case):
    def test_fang_crits_poison_twice(self):
        s, h = self.setup("venom", 3)
        a = foe(12, 10)
        self.hit(a)
        self.assertIsNone(a.status)
        self.hit(a, sure_crit=True)
        self.assertEqual(a.status.stacks("poison"), config.FANG)

    def test_toxic_blood_poisons_who_hits_you(self):
        s, h = self.setup("venom", 6)
        a = foe(12, 10)
        h.take_damage(3, a, None)
        self.assertEqual(a.status.stacks("poison"), config.TOXIC_BLOOD)

    def test_neurotoxin_roots(self):
        s, h = self.setup("venom", 9)
        a = foe(h.x + 2, h.y)
        inflict(a, "poison", h, 4)
        self.assertEqual(a.status.rooted, 0.0)
        inflict(a, "poison", h, 1)
        self.assertEqual(a.status.rooted, config.NEUROTOXIN[1])
        run([a], 1.5)
        inflict(a, "poison", h, 1)                # (still on its cooldown)
        self.assertEqual(a.status.rooted, 0.0)
        boss = foe(20, 10)
        boss.boss = True
        inflict(boss, "poison", h, 5)
        self.assertEqual(boss.status.rooted, 0.0)

    def test_a_rooted_enemy_acts_but_stays_put(self):
        from ascii_adventurers.tests.test_m17 import step
        s, h = self.setup("venom", 9)
        a = foe(h.x + 2, h.y, 5000)
        moved = []
        a.think = lambda ctx, dt: (moved.append(1), setattr(a, "x", a.x + 0.1))
        self.place(a)
        step(s)
        self.assertTrue(moved)
        x = a.x
        inflict(a, "poison", h, 5)
        step(s, 10)
        self.assertEqual(a.x, x)
        self.assertGreater(len(moved), 5)


class PlaguebeakTest(_Case):
    def test_incubation_ticks_faster_at_eight(self):
        s, h = self.setup("virulence", 3)
        a = foe(12, 10)
        inflict(a, "poison", h, 7)
        st = a.status
        self.assertEqual(st._rate(a, "poison", st.active["poison"], False), 1.0)
        inflict(a, "poison", h, 1)
        self.assertEqual(st._rate(a, "poison", st.active["poison"], False), config.INCUBATION[1])

    def test_plague_doctor_toxic_ground(self):
        from ascii_adventurers.ai.bosses import FalloutKing
        s, h = self.setup("virulence", 6)
        corpse = foe(30, 10)
        hp = h.hp
        gas = Zone("gas", h.x, h.y, 2.0, 5.0, 0.5, 4.0, corpse)
        update_zones([gas], [h], [], DT)
        self.assertEqual(h.hp, hp)
        king = SimpleNamespace(goo=[[h.x, h.y, 0.0]])
        self.assertFalse(FalloutKing._in_goo(king, h))
        wear(s, "virulence", 5)                   # (below +6: it hurts)
        update_zones([Zone("gas", h.x, h.y, 2.0, 5.0, 0.5, 4.0, corpse)], [h], [], DT)
        self.assertLess(h.hp, hp)
        self.assertTrue(FalloutKing._in_goo(king, h))

    def test_black_death(self):
        s, h = self.setup("virulence", 9)
        a = foe(12, 10, 1000)
        inflict(a, "poison", h, 10)
        power = a.status.active["poison"].power
        run([a], 1.0)
        dot = 2.0 * 10 * power * config.INCUBATION[1]
        self.assertGreater(1000 - a.hp, dot + 0.045 * 1000)
        self.assertLess(1000 - a.hp, dot + 0.05 * 1000 + 1)
        boss = foe(14, 10, 1000)
        boss.boss = True
        inflict(boss, "poison", h, 10)
        run([boss], 1.0)
        self.assertLess(1000 - boss.hp, dot / 2 + 0.01 * 1000 + 1)


class RimeHoodTest(_Case):
    def test_cold_snap_chills_the_first_hit(self):
        s, h = self.setup("frostbite", 3)
        a = foe(12, 10)
        self.hit(a)
        self.assertEqual(a.status.stacks("chill"), 1)
        self.hit(a)
        self.assertEqual(a.status.stacks("chill"), 1)

    def test_hoarfrost(self):
        s, h = self.setup("frostbite", 6)
        a, shooter = walker(14, 10.5), foe(8, 10.5)
        world = open_map()
        combat.push(a, world, 1.0, 0.0)
        self.assertAlmostEqual(a.x, 15.0)
        inflict(a, "chill", h, 5)
        self.assertGreater(a.status.frozen, 0)
        combat.push(a, world, 1.0, 0.0)
        self.assertAlmostEqual(a.x, 15.0)
        hp = a.hp
        shot = Projectile(shooter.x + 0.6, shooter.y, 0.0, config.SNOW_SHOTS["shard"], owner=shooter)
        shots = [shot]
        fly(shots, [a, shooter], world, steps=60)
        self.assertEqual(a.hp, hp)
        self.assertFalse(shots)

    def test_permafrost_chills_what_touches(self):
        s, h = self.setup("frostbite", 9)
        a, b, far = self.place(foe(12, 10), foe(12.9, 10), foe(16, 10))
        inflict(a, "chill", h, 5)
        s.rules.status_tricks(DT)
        self.assertEqual(b.status.stacks("chill"), 1)
        self.assertIsNone(far.status)
        for _ in range(60):
            s.rules.status_tricks(DT)
        self.assertEqual(b.status.stacks("chill"), 2)


class GlassfrostTest(_Case):
    def test_brittle(self):
        s, h = self.setup("shatter", 3)
        a, b = foe(12, 10), foe(14, 10)
        inflict(a, "chill", h)
        self.assertAlmostEqual(self.hit(a, 10) / self.hit(b, 10), config.BRITTLE)

    def test_splinters_throw_shards(self):
        s, h = self.setup("shatter", 6)
        a = foe(12, 10, 1)
        inflict(a, "chill", h, 5)
        a.hp = 0
        s.rules.on_kill(s.me, a)
        shards = [q for q in s.projectiles if q.spec is config.ICE_SHARD_SHOT]
        self.assertEqual(len(shards), config.SPLINTERS[0])
        self.assertTrue(all(q.max_range == config.SPLINTERS[1] and q.inflicts == ("chill", 1)
                            for q in shards))
        b = foe(12 + 2.0 * math.cos(shards[0].angle), 10 + 2.0 * math.sin(shards[0].angle))
        fly(shards, [b], steps=30)
        self.assertEqual(b.status.stacks("chill"), 1)

    def test_shatterpoint(self):
        s, h = self.setup("shatter", 9)
        a = self.place(foe(12, 10, 5000))[0]
        inflict(a, "chill", h, 5)
        self.hit(a, 10)
        self.assertEqual(a.status.frozen, 0.0)
        one = 10 * config.SHATTER[0] * (1 + h.stats.damage) * h.stats.damage_mult
        self.assertAlmostEqual(5000 - a.hp, 2 * one, delta=0.5)
        s.rules.resolve_combos()
        self.assertEqual(sum(q.spec is config.ICE_SHARD_SHOT for q in s.projectiles),
                         config.SPLINTERS[0])


class StormvaneTest(_Case):
    def test_build_up(self):
        s, h = self.setup("static", 3)
        a = foe(12, 10)
        inflict(a, "shock", h)
        base = a.status.vulnerability
        self.hit(a)
        self.assertAlmostEqual(a.status.vulnerability, base + config.BUILD_UP[0])
        for _ in range(20):
            self.hit(a)
        self.assertAlmostEqual(a.status.vulnerability, base + config.BUILD_UP[1])

    def test_ground_fault_in_water(self):
        s, h = self.setup("static", 6)
        wet = SimpleNamespace(tile_at=lambda x, y: tiles.WATER)
        dry = SimpleNamespace(tile_at=lambda x, y: tiles.GROUND)
        a, b = foe(12, 10, 1000), foe(14, 10, 1000)
        inflict(a, "shock", h)
        inflict(b, "shock", h)
        power = a.status.active["shock"].power * a.status.vulnerability   # (it's shocked)
        run([a], 1.0, wet)
        run([b], 1.0, dry)
        self.assertEqual(b.hp, 1000)
        self.assertAlmostEqual(1000 - a.hp, config.GROUND_FAULT * power, delta=1.0)

    def test_tempest(self):
        s, h = self.setup("static", 9)
        a, near, far = self.place(foe(12, 10, 5000), foe(13, 10, 5000), foe(16, 10, 5000))
        for _ in range(2):
            inflict(a, "shock", h)
        self.assertFalse(statuses.combos)
        inflict(a, "shock", h)
        s.rules.resolve_combos()
        self.assertLess(a.hp, 5000)
        self.assertLess(near.hp, 5000)
        self.assertEqual(far.hp, 5000)
        # Shocks older than the window don't count.
        b = self.place(foe(30, 10, 5000))[0]
        inflict(b, "shock", h)
        inflict(b, "shock", h)
        run([b], config.TEMPEST[1] + 0.1)
        inflict(b, "shock", h)
        self.assertFalse(statuses.combos)


class ThornhelmTest(_Case):
    def test_rend_once(self):
        s, h = self.setup("serrated", 3)
        a = self.place(foe(12, 10, 5000))[0]
        inflict(a, "bleed", h, 5)
        s.rules.resolve_combos()
        dmg = config.REND[1] * h.stats.status_scale("physical")
        self.assertAlmostEqual(5000 - a.hp, dmg)
        a.status = None
        inflict(a, "bleed", h, 5)
        s.rules.resolve_combos()
        self.assertAlmostEqual(5000 - a.hp, dmg)

    def test_open_wounds(self):
        s, h = self.setup("serrated", 6)
        a = foe(12, 10, 100)
        a.hp = 50
        self.assertEqual(a.heal(10), 10.0)
        a.hp = 50
        inflict(a, "bleed", h)
        self.assertEqual(a.heal(10), 0.0)
        pollen = Zone("pollen", a.x, a.y, 2.0, 5.0, 0.5, 0.0, foe(30, 10), heal=0.1)
        update_zones([pollen], [a], [], DT)
        self.assertEqual(a.hp, 50)
        a.status = None
        self.assertEqual(a.heal(10), 10.0)

    def test_exsanguinate(self):
        s, h = self.setup("serrated", 9)
        a, boss = self.place(foe(12, 10, 1000), foe(14, 10, 10000))
        boss.boss = True
        a.hp, boss.hp = 140, 1000
        inflict(a, "bleed", h)
        inflict(boss, "bleed", h)
        s.rules.status_tricks(DT)
        self.assertFalse(a.alive)
        self.assertEqual(boss.hp, 1000 - config.EXSANGUINATE[1])
        s.rules.status_tricks(DT)
        self.assertEqual(boss.hp, 1000 - config.EXSANGUINATE[1])     # (once every 10 s)


class BloodtrailTest(_Case):
    def test_panic(self):
        s, h = self.setup("hemorrhage", 3)
        h.x, h.y = 10.5, 10.5
        a = self.place(walker(12.5, 10.5, 100))[0]
        inflict(a, "bleed", h)
        s.rules.status_tricks(DT)
        self.assertEqual(a.status.scared, 0.0)
        a.hp = 40
        s.rules.status_tricks(DT)
        self.assertEqual(a.status.scared, config.PANIC[1])
        s.world = open_map()
        x = a.x
        self.assertTrue(s.rules.flee(a, 0.5))
        self.assertGreater(a.x, x)
        a.status.scared = 0.0
        s.rules.status_tricks(DT)
        self.assertEqual(a.status.scared, 0.0)                       # (once each)

    def test_spurt_on_a_dash(self):
        s, h = self.setup("hemorrhage", 6)
        a = walker(12, 10, 5000, speed=2.0)
        inflict(a, "bleed", h)
        st = a.status
        st.pace = 2.0
        self.assertEqual(st._rate(a, "bleed", st.active["bleed"], True), 2.0)
        st.pace = 2.0 * config.SPURT[1] + 0.5
        self.assertEqual(st._rate(a, "bleed", st.active["bleed"], True), config.SPURT[0])

    def test_bloodhound(self):
        s, h = self.setup("hemorrhage", 9)
        a = self.place(walker(12, 10, 5000))[0]
        inflict(a, "bleed", h)
        st = a.status
        self.assertEqual(st._rate(a, "bleed", st.active["bleed"], True), config.BLOODHOUND)
        self.assertEqual(st._rate(a, "bleed", st.active["bleed"], False), 1.0)
        self.assertEqual(s._blood_pins(s.me), [(a.x, a.y, "blood", "")])


class SteamcrownTest(_Case):
    def burst(self, victim, burn=1):
        inflict(victim, "burn", self.h, burn)
        inflict(victim, "chill", self.h)
        self.s.rules.resolve_combos()

    def test_scald(self):
        s, h = self.setup("thermal_shock", 3)
        a, b = self.place(foe(12, 10, 5000), foe(13, 10, 5000))
        self.burst(a)
        self.assertEqual(b.status.stacks("burn"), config.SCALD)

    def test_pressure(self):
        s, h = self.setup("thermal_shock", 6)
        a, b = self.place(foe(12, 10, 5000), foe(12 + config.THERMAL_SHOCK[1] + 1.2, 10, 5000))
        self.burst(a, burn=1)
        self.assertEqual(b.hp, 5000)
        a.status = None
        self.burst(a, burn=3)                     # (2 + 1.5 tiles)
        self.assertLess(b.hp, 5000)

    def test_geyser(self):
        s, h = self.setup("thermal_shock", 9)
        a = self.place(foe(12, 10, 5000))[0]
        self.burst(a)
        self.assertTrue(a.status.has("chill"))
        hp = a.hp
        s.rules.status_tricks(DT)
        s.rules.resolve_combos()
        self.assertEqual(a.hp, hp)                # (2 s between bursts)
        a.status.active["burn"].left = a.status.active["chill"].left = 10.0
        run([a], config.GEYSER + 0.05)
        hp = a.hp
        s.rules.status_tricks(DT)
        s.rules.resolve_combos()
        self.assertLess(a.hp, hp)


class GalvanicTest(_Case):
    def spread(self, victim):
        inflict(victim, "poison", self.h, 3)
        inflict(victim, "shock", self.h)
        self.s.rules.resolve_combos()

    def test_live_wire(self):
        s, h = self.setup("toxic_current", 3)
        a, b, c = self.place(foe(12, 10), foe(13, 10), foe(12, 11))
        self.spread(a)
        for o in (b, c):
            self.assertEqual(o.status.stacks("poison"), 3)
            self.assertTrue(o.status.has("shock"))
        self.assertFalse(statuses.combos)          # (its shock doesn't spread again)

    def test_battery(self):
        s, h = self.setup("toxic_current", 6)
        a, b = self.place(foe(12, 10), foe(13, 10))
        for _ in range(config.BATTERY + 2):
            a.status = None
            self.spread(a)
        self.assertEqual(h.battery, config.BATTERY)
        h.aim_angle = 0.0
        s._attack(s.me)
        shots = [q for q in s.projectiles if q.owner is h]
        self.assertTrue(shots and all(q.shocks for q in shots))
        self.assertEqual(h.battery, 0)
        s.projectiles.clear()
        s._attack(s.me)
        self.assertFalse(any(q.shocks for q in s.projectiles))

    def test_galvanize(self):
        s, h = self.setup("toxic_current", 9)
        a = self.place(foe(12, 10))[0]
        ring = self.place(*[foe(12 + 2 * math.cos(k), 10 + 2 * math.sin(k)) for k in range(4)])
        out = self.place(foe(16, 10))[0]
        self.spread(a)
        self.assertTrue(all(o.status.stacks("poison") == 3 for o in ring))
        self.assertIsNone(out.status)


if __name__ == "__main__":
    unittest.main()
