"""M28.2f: the trinkets' +3 / +6 / +9 tricks (design/GEAR.md 17.6)."""

import math
import os
from dataclasses import replace
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from ascii_adventurers import config
from ascii_adventurers.players import gear
from ascii_adventurers.render.spell_fx import draw_spells, draw_summons
from ascii_adventurers.systems import combat, spells, statuses
from ascii_adventurers.systems.zones import Zone, update_zones
from ascii_adventurers.tests.test_m28_2a import foe, wear
from ascii_adventurers.tests.test_m28_2e import dead, plain
from ascii_adventurers.tests.test_m28_2c import DT, _Case

BASE = 1000.0
STRIKE = "ascii_adventurers.systems.spells.strike"
CHAIN_STRIKE = "ascii_adventurers.systems.combat.strike"


class _Trinket(_Case):
    def setup(self, key, level, hero="wizard", walls=()):
        s, h = super().setup(key, level, hero, walls)
        self.st = s.me.spells[key]
        return s, h

    def cast(self, seconds=DT):
        """Run the hero's spells (their part of GameScene._step)."""
        s = self.s
        for _ in range(max(1, round(seconds * 60))):
            s.hero.time += DT
            spells.update_spells(s.hero, s.me.spells, s.world, s._actors(), s.effects, DT,
                                 s.projectiles, s.zones)

    def now(self):
        """The spell's timer runs out on the next step."""
        self.st.timer = 0.0

    def hold(self):
        """No more casts of its own (a test sets them off with now())."""
        self.st.params = dict(self.st.params, interval=1000.0)
        self.st.timer = 1000.0


def victims(hit):
    return [c.args[0] for c in hit.call_args_list]


class FrameworkTest(unittest.TestCase):
    def test_every_trinket_has_three_tricks(self):
        trinkets = [k for k, g in config.GEAR.items() if g.slot == "trinket"]
        self.assertEqual(len(trinkets), 11)
        for key in trinkets:
            self.assertEqual([t for t, _, _ in gear.tricks(key)], [3, 6, 9], key)
            for _, name, text in gear.tricks(key):
                self.assertTrue(name and text and text.isascii(), key)

    def test_the_slots_built_so_far(self):
        built = {config.GEAR[k].slot for k in config.GEAR_TRICKS}
        self.assertTrue({"off", "head", "feet", "chest", "ring", "trinket"} <= built)



class DrawTest(_Trinket):
    def test_every_trick_draws(self):
        """Every trinket at +9, three at a time (the slots), on show."""
        for keys in (("daggers", "ember_aura", "spirit_wolf"),
                     ("rune_trap", "storm_cloud", "healing_totem"),
                     ("bone_turret", "poison_flask", "fire_wand")):
            s, h = self.setup(keys[0], 9)
            for key in keys[1:]:
                wear(s, key, 9)
            self.assertEqual(sorted(s.me.spells), sorted(keys))
            self.place(foe(23.0, 20.5, BASE), foe(18.0, 22.0, BASE), foe(21.0, 23.0, BASE))
            self.cast(4.0)
            h.rolls += 1
            self.cast(0.2)
            s.zones.append(Zone("wisp", 22.0, 21.0, 1.5, 3.0, 0.5, 0.0, h, (), "burn"))
            for _ in range(30):                        # (every frame of the animations)
                s.steps += 1
                draw_spells(s.manager.text, s.me.camera, s.players, s.steps)
                draw_summons(s.manager.text, s.me.camera, s.players, s.zones, s.steps)


class ChainboltTest(_Trinket):
    def bolt(self, first, others=(), jumps=5):
        shell = replace(config.SPELL_SHELLS["chain"], chain=jumps)
        self.place(first, *others)
        with mock.patch(CHAIN_STRIKE) as hit:
            combat.chain_from(first, shell, 100.0, self.h, self.s.world, self.s._actors(),
                              self.s.effects, charm=True)
        return hit

    def test_grounding(self):
        s, h = self.setup("chain_lightning", 3)
        alone = foe(24.0, 20.5, BASE)
        hit = self.bolt(alone)
        self.assertEqual(victims(hit), [alone])           # the ground by it bursts...
        self.assertAlmostEqual(hit.call_args.args[1], 100.0 * config.GROUNDING[1])
        s.enemies.clear()
        shell = config.SPELL_SHELLS["chain"]
        with mock.patch(CHAIN_STRIKE) as hit:             # ...only a Chainbolt Charm bolt
            combat.chain_from(alone, shell, 100.0, h, s.world, [alone], s.effects)
        self.assertEqual(hit.call_count, 0)

    def test_overload(self):
        s, h = self.setup("chain_lightning", 6)
        self.place(foe(24.0, 20.5, BASE))
        self.hold()
        jumps = []
        for _ in range(config.OVERLOAD * 2):
            self.now()
            self.cast()
            jumps.append(s.projectiles[-1].spec.chain)
            self.assertTrue(s.projectiles[-1].charm)
        plain = jumps[0]
        want = [plain * 2 if (i + 1) % config.OVERLOAD == 0 else plain for i in range(len(jumps))]
        self.assertEqual(jumps, want)

    def test_eternal_arc(self):
        s, h = self.setup("chain_lightning", 9)
        a, b = foe(24.0, 20.5, BASE), foe(26.0, 20.5, BASE)
        hit = self.bolt(a, (b,))
        self.assertEqual(victims(hit), [b, a, b, b])      # back once each, then grounded by b
        self.setup("chain_lightning", 3)
        a, b = foe(24.0, 20.5, BASE), foe(26.0, 20.5, BASE)
        hit = self.bolt(a, (b,))
        self.assertEqual(victims(hit), [b, b])            # (no going back below +9)


class BladewheelTest(_Trinket):
    def centre(self):
        dots = self.st.dagger_positions(self.h)
        return (sum(x for x, _, _ in dots) / len(dots), sum(y for _, y, _ in dots) / len(dots))

    def test_fling(self):
        s, h = self.setup("daggers", 3)
        self.cast()
        h.roll_dir = (1.0, 0.0)
        h.rolls += 1
        self.cast(config.FLING[1] / 2)
        x, _ = self.centre()
        self.assertGreater(x - h.x, config.FLING[0] * 0.9)   # out along the roll...
        self.cast(config.FLING[1] / 2 + DT)
        x, _ = self.centre()
        self.assertAlmostEqual(x, h.x, places=6)             # ...and back

    def test_breathing_ring(self):
        s, h = self.setup("daggers", 6)
        every, swell, most = config.BREATHING
        r = self.st.params["radius"] * h.stats.area_scale
        for clock, want in ((swell / 2, r * most), (swell + 0.5, r)):
            self.st.clock = clock
            x, y, _ = self.st.dagger_positions(h)[0]
            self.assertAlmostEqual(math.hypot(x - h.x, y - h.y), want, places=6)

    def test_blade_storm(self):
        s, h = self.setup("daggers", 9)
        self.st.clock = config.BREATHING[0] - 0.5            # (no swell)
        dots = self.st.dagger_positions(h)
        self.assertEqual(len(dots), int(self.st.params["count"]) + config.BLADE_STORM[0])
        radii = sorted({round(math.hypot(x - h.x, y - h.y), 6) for x, y, _ in dots})
        self.assertEqual(len(radii), 2)
        self.assertAlmostEqual(radii[1] / radii[0], config.BLADE_STORM[1])
        a1, a2 = self.st.angle, self.st.angle2
        self.cast()
        self.assertGreater((self.st.angle - a1) % math.tau, 0)
        self.assertGreater((a2 - self.st.angle2) % math.tau, 0)   # the other way


class EmberTest(_Trinket):
    def ring(self, n, d=1.0):
        return self.place(*[foe(self.h.x + math.cos(k) * d, self.h.y + math.sin(k) * d, BASE)
                            for k in range(n)])

    def test_warmth(self):
        s, h = self.setup("ember_aura", 3)
        self.ring(11)
        h.hp = h.max_hp - 10
        self.hold()
        self.now()
        self.cast()
        self.assertAlmostEqual(h.hp, h.max_hp - 10 + 11 // config.WARMTH)

    def test_flare_up(self):
        s, h = self.setup("ember_aura", 6)
        a, = self.ring(1)
        self.hold()
        self.now()
        self.cast()
        plain = a.status.stacks("burn")
        a.status = None
        self.st.count = config.FLARE_UP[0] - 1
        self.now()
        self.cast()
        self.assertEqual(a.status.stacks("burn"), max(plain, config.FLARE_UP[1]))
        self.assertGreater(config.FLARE_UP[1], plain)

    def test_sunfire(self):
        s, h = self.setup("ember_aura", 9)
        r = spells.aura_radius(h, self.st)
        self.ring(4)
        self.hold()
        self.now()
        self.cast()
        self.assertAlmostEqual(spells.aura_radius(h, self.st), r + 4 * config.SUNFIRE[0])
        self.ring(20)
        self.now()
        self.cast()
        self.assertAlmostEqual(spells.aura_radius(h, self.st), r + config.SUNFIRE[1])


class WinterheartTest(_Trinket):
    def test_cold_heart(self):
        s, h = self.setup("frost_nova", 3)
        self.st.timer = 3.0
        self.cast()
        h.hits_taken += 1
        self.cast()
        self.assertAlmostEqual(self.st.timer, 3.0 - 2 * DT - config.COLD_HEART)
        h.hits_taken += 1                                  # (once a nova)
        self.cast()
        self.assertAlmostEqual(self.st.timer, 3.0 - 3 * DT - config.COLD_HEART)

    def test_ice_armor(self):
        s, h = self.setup("frost_nova", 6)
        self.place(foe(22.0, 20.5, BASE), foe(19.0, 20.5, BASE), foe(20.5, 22.0, BASE))
        self.hold()
        self.now()
        self.cast()
        self.assertAlmostEqual(h.shield, 3 * config.ICE_ARMOR[0])
        self.place(*[foe(20.5 + k * 0.2, 19.0, BASE) for k in range(10)])
        self.now()
        self.cast()
        self.assertAlmostEqual(h.shield, config.ICE_ARMOR[1])

    def test_avalanche(self):
        s, h = self.setup("frost_nova", 9)
        r = self.st.params["radius"] * h.stats.area_scale
        far, boss = foe(20.5 + r * 1.5, 20.5, BASE), foe(20.5, 21.5, BASE)
        boss.boss = True
        self.place(far, boss)
        self.hold()
        self.st.count = config.AVALANCHE[0] - 1
        self.now()
        self.cast()
        self.assertGreater(far.status.frozen, 0)           # twice as wide, frozen at once
        self.assertEqual(boss.status.frozen, 0)            # (not bosses)
        self.assertGreater(boss.status.stacks("chill"), 0)


class WolfcallTest(_Trinket):
    def test_scent(self):
        s, h = self.setup("spirit_wolf", 3)
        near, far = self.place(foe(22.0, 20.5, BASE), foe(28.0, 20.5, BASE))
        combat.strike(far, 1.0, h, None, s.effects)
        self.assertIs(h.scent, far)
        self.cast(0.5)
        self.assertGreater(self.st.things[0]["x"], near.x)  # past the near one, after it

    def test_howl(self):
        s, h = self.setup("spirit_wolf", 6)
        howled, other = self.place(foe(21.5, 20.5, BASE), foe(40.0, 20.5, BASE))
        self.cast()
        self.st.howl = config.HOWL[0] - DT / 2
        self.cast()
        self.assertIsNotNone(getattr(howled, "howled", None))
        self.assertIsNone(getattr(other, "howled", None))
        hp = h.hp
        h.take_damage(10.0, other, None)
        plain = hp - h.hp
        hp = h.hp
        h.take_damage(10.0, howled, None)
        self.assertAlmostEqual((hp - h.hp) / plain, config.HOWL[2])
        h.time += config.HOWL[3] + 0.1                     # (for 3 s)
        hp = h.hp
        h.take_damage(10.0, howled, None)
        self.assertAlmostEqual(hp - h.hp, plain)

    def test_dire_wolves(self):
        s, h = self.setup("spirit_wolf", 9)
        prey, = self.place(foe(21.5, 20.5, BASE))
        with mock.patch(STRIKE) as hit:
            self.cast()                                   # (the wolf comes up next to it)
        self.assertAlmostEqual(hit.call_args.args[1],
                               self.st.params["damage"] * config.DIRE_WOLVES[1])
        self.assertEqual(prey.status.stacks("bleed"), config.DIRE_WOLVES[2] * hit.call_count)
        self.assertEqual(spells.dire(h), config.DIRE_WOLVES[0])


class RunestoneTest(_Trinket):
    def runes(self, *spots):
        self.st.things = [{"x": x, "y": y, "age": 0.0, "n": i + 1} for i, (x, y) in enumerate(spots)]
        self.st.serial = len(spots)

    def test_rune_lines(self):
        s, h = self.setup("rune_trap", 3)
        self.hold()
        self.runes((20.0, 30.0), (23.0, 30.0), (30.0, 30.0))
        on, off = self.place(foe(21.5, 30.0, BASE), foe(26.5, 30.0, BASE))
        self.assertEqual(len(spells.rune_links(h, self.st)), 1)   # (the third is too far)
        with mock.patch(STRIKE) as hit:
            self.cast()
            self.cast(0.5)
        self.assertEqual(victims(hit), [on])                      # once a second
        self.assertEqual(hit.call_args.args[1], config.RUNE_LINES[1])
        self.assertEqual(len(self.st.things), 3)                  # (none tripped)

    def test_seeking_runes(self):
        s, h = self.setup("rune_trap", 6)
        self.hold()
        self.runes((20.0, 30.0), (40.0, 30.0))
        self.place(foe(23.0, 30.0, BASE))
        self.cast(0.5)
        self.assertAlmostEqual(self.st.things[0]["x"], 20.0 + config.SEEKING_RUNES[1] * 0.5,
                               places=1)
        self.assertEqual(self.st.things[1]["x"], 40.0)            # (nothing within 4)

    def test_runeburst(self):
        s, h = self.setup("rune_trap", 9)
        self.hold()
        self.runes((20.0, 30.0), (30.0, 30.0))
        near, = self.place(foe(21.5, 30.0, BASE))
        self.cast()
        self.assertEqual(len(self.st.things), 2)
        h.rolls += 1
        with mock.patch(STRIKE) as hit:
            self.cast()
        self.assertEqual(self.st.things, [])
        self.assertIn(near, victims(hit))


class WitchsFlaskTest(_Trinket):
    def land(self, x, y):
        self.st.things.append({"x0": self.h.x, "y0": self.h.y, "x1": x, "y1": y, "t": 1.0,
                               "flight": 0.6, "brew": "poison"})
        self.cast()
        return [z for z in self.s.zones if z.kind == "pool"]

    def test_bubbling(self):
        s, h = self.setup("poison_flask", 3)
        self.hold()
        pool, = self.land(30.0, 30.0)
        r = pool.radius
        update_zones(s.zones, [], s.effects, pool.life / 2)
        self.assertAlmostEqual(pool.radius, r * (1 + config.BUBBLING / 2))

    def test_witchs_brew(self):
        s, h = self.setup("poison_flask", 6)
        self.place(foe(24.0, 20.5, BASE))
        self.hold()
        self.st.count = config.WITCHS_BREW[0] - int(self.st.params["count"])   # (2 at once)
        self.now()
        self.cast()
        brews = [f["brew"] for f in self.st.things]
        self.assertEqual(brews[-1], "shock")                      # (the dice say 0.99)
        self.assertTrue(all(b == "poison" for b in brews[:-1]))
        self.cast(1.0)
        shock = [z for z in s.zones if z.inflicts == "shock"]
        self.assertEqual(len(shock), 1)
        self.assertEqual(shock[0].tags, ("lightning", "area"))

    def test_cauldron(self):
        s, h = self.setup("poison_flask", 9)
        self.hold()
        first, = self.land(30.0, 30.0)
        r = first.radius
        update_zones(s.zones, [], s.effects, 1.0)
        r1 = first.radius
        pools = self.land(30.0 + r1, 30.0)
        self.assertEqual(len(pools), 1)                           # one...
        self.assertAlmostEqual(pools[0].radius, math.sqrt(r1 ** 2 + r ** 2))   # ...both areas
        self.assertEqual(pools[0].age, 0.0)                       # as long as the newest
        far = self.land(50.0, 30.0)
        self.assertEqual(len(far), 2)                             # (apart: two)


class StormjarTest(_Trinket):
    def test_downpour(self):
        s, h = self.setup("storm_cloud", 3)
        self.hold()
        under, away = self.place(foe(*spells.puddle_spot(h), BASE), foe(40.0, 30.0, BASE))
        self.cast()
        puddle, = [z for z in s.zones if z.kind == "puddle"]
        update_zones(s.zones, s._actors(), s.effects, DT)
        self.assertTrue(statuses._wet(s.world, under))
        self.assertFalse(statuses._wet(s.world, away))
        h.x += 10
        self.cast()
        self.assertEqual(len([z for z in s.zones if z.kind == "puddle"]), 1)   # it moves
        self.assertAlmostEqual(puddle.x, spells.puddle_spot(h)[0])

    def test_thunderhead(self):
        s, h = self.setup("storm_cloud", 6)
        attacker, b, c = self.place(foe(22.0, 20.5, BASE), foe(19.0, 20.5, BASE),
                                    foe(20.5, 22.0, BASE))
        self.hold()
        h.take_damage(5.0, attacker, None)
        self.assertIs(h.struck_by, attacker)
        self.now()
        with mock.patch(STRIKE) as hit:
            self.cast()
        self.assertIs(victims(hit)[0], attacker)

    def test_eye_of_the_storm(self):
        s, h = self.setup("storm_cloud", 9)
        self.place(foe(22.0, 20.5, BASE))
        self.hold()
        self.now()
        with mock.patch(STRIKE) as hit:
            self.cast()
            self.assertEqual(hit.call_count, 1)
            self.cast(config.EYE_OF_THE_STORM[0] - 2 * DT)
            self.assertEqual(hit.call_count, 1)
            self.cast(2 * DT)
            self.assertEqual(hit.call_count, 2)                    # 0.75 s after the first
        arc = [e for e in s.effects if e.kind == "arc"][-1]
        ex, ey = spells.eye_position(h, self.st)
        self.assertAlmostEqual((arc.x, arc.y), (ex, ey), delta=0.2)


class MendersTotemTest(_Trinket):
    def plant(self):
        self.hold()
        self.now()
        self.cast()
        return self.st.things[-1]

    def test_cleansing_light(self):
        s, h = self.setup("healing_totem", 3)
        h.slowed(0.0, 5.0)
        h.petrified, h.rads, h.irradiated, h.chill, h.encased, h.shrunk = 1, 50, 3, 40, 2, 4
        self.plant()
        self.assertEqual((h.slow_t, h.petrified, h.rads, h.irradiated, h.chill, h.encased,
                          h.shrunk), (0, 0, 0, 0, 0, 0, 0))
        h.slowed(0.5, 5.0)
        self.cast()
        self.assertGreater(h.slow_t, 0)                    # stepping in, not standing there
        h.x += 20
        self.cast()
        h.x -= 20
        self.cast()
        self.assertEqual(h.slow_t, 0)

    def test_carried(self):
        s, h = self.setup("healing_totem", 6)
        t = self.plant()
        h.x += 6
        self.cast(1.0)
        self.assertAlmostEqual(t["x"], 20.5 + config.CARRIED, delta=0.1)

    def test_tree_of_life(self):
        s, h = self.setup("healing_totem", 9)
        first = self.plant()
        self.cast(self.st.params["life"] * h.stats.duration_scale + 1.0)
        self.assertEqual(self.st.things, [first])          # stays...
        second = self.plant()
        self.assertEqual(self.st.things, [second])         # ...until the next one


class FireflyTest(_Trinket):
    def bolt(self):
        self.now()
        self.cast()
        return self.s.projectiles[-1]

    def test_glow(self):
        s, h = self.setup("fire_wand", 3)
        lit, other = self.place(foe(24.0, 20.5, BASE), foe(24.0, 30.0, BASE))
        self.hold()
        shot = self.bolt()
        self.assertTrue(shot.glow)
        for _ in range(60):
            combat.update_projectiles(s.projectiles, s.world, s.effects, DT, s._actors(), s.zones)
        self.assertAlmostEqual(lit.lit[id(h)], h.time + config.GLOW[1], places=1)
        base = combat.crit_chance(h.stats, h)
        h.rng.random = lambda: base + config.GLOW[0] / 2
        combat.strike(lit, 1.0, h, None, s.effects)
        self.assertTrue(h.last_crit)
        combat.strike(other, 1.0, h, None, s.effects)
        self.assertFalse(h.last_crit)

    def test_moth(self):
        s, h = self.setup("fire_wand", 6)
        near, burning = self.place(foe(23.0, 20.5, BASE), foe(20.5, 26.0, BASE))
        statuses.inflict(burning, "burn", h)
        self.hold()
        shot = self.bolt()
        self.assertAlmostEqual(shot.angle, math.atan2(burning.y - h.y, burning.x - h.x), places=3)

    def test_will_o_wisps(self):
        s, h = self.setup("fire_wand", 9)
        self.place(foe(24.0, 20.5, BASE))
        self.hold()
        shots = [self.bolt() for _ in range(config.WISPS[0])]
        self.assertEqual([q.wisp for q in shots], [False] * (config.WISPS[0] - 1) + [True])
        shot = shots[-1]
        shot.alive = False
        combat._shot_ends([shot], [], s.zones, s.world, s._actors())
        wisp, = [z for z in s.zones if z.kind == "wisp"]
        self.assertEqual((wisp.inflicts, wisp.life), ("burn", config.WISPS[1]))
        self.assertAlmostEqual(wisp.radius, config.WISPS[2] * h.stats.area_scale)


class SkullSentryTest(_Trinket):
    def plant(self):
        self.now()
        self.cast()
        return self.st.things[-1]

    def test_ossuary(self):
        s, h = self.setup("bone_turret", 3)
        self.hold()
        s.rules.on_kill(s.me, dead(plain(26.0, 24.0)))
        self.assertEqual(h.kill_spot, (26.0, 24.0))
        t = self.plant()
        self.assertEqual((t["x"], t["y"]), (26.0, 24.0))
        h.kill_spot = (20.5 + config.OSSUARY_REACH + 5, 20.5)       # (too far: next to you)
        t = self.plant()
        self.assertEqual((t["x"], t["y"]), (h.x, h.y))

    def test_calcify(self):
        s, h = self.setup("bone_turret", 6)
        self.hold()
        self.plant()
        life = self.st.params["life"] * h.stats.duration_scale
        s.projectiles.clear()
        self.cast(life + 0.1)
        shards = [q for q in s.projectiles if q.damage == config.CALCIFY[1]]
        self.assertEqual(len(shards), config.CALCIFY[0])
        self.assertTrue(all(q.summon for q in shards))
        self.assertEqual(self.st.things, [])

    def test_bone_legion(self):
        s, h = self.setup("bone_turret", 9)
        self.hold()
        most = int(self.st.params["count"]) + config.BONE_LEGION
        for _ in range(most + 1):
            self.plant()
        self.assertEqual(len(self.st.things), most)
        self.cast(self.st.params["life"] * h.stats.duration_scale + 1.0)
        self.assertEqual(len(self.st.things), most)       # they stay until replaced


if __name__ == "__main__":
    unittest.main()
