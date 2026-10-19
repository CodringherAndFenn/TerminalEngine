"""M28.2c: the feet's +3 / +6 / +9 tricks (design/GEAR.md 17.3)."""

import math
import os
import unittest
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from ascii_adventurers import config
from ascii_adventurers.ai.bosses import Boss
from ascii_adventurers.ai.brain import AIContext
from ascii_adventurers.entities.projectile import Projectile
from ascii_adventurers.players import gear
from ascii_adventurers.players.controls import PlayerInput
from ascii_adventurers.systems import combat, roll, statuses
from ascii_adventurers.systems.zones import Zone, update_zones
from ascii_adventurers.tests.test_m16 import game
from ascii_adventurers.tests.test_m28_2a import foe, wear
from ascii_adventurers.tests.test_m28_2b import walker
from ascii_adventurers.tests.test_weapons import open_map

DT = 1 / 60
SHOT = config.SNOW_SHOTS["shard"]


def press(mx=0.0, my=0.0):
    return PlayerInput(mx, my, roll=True)


class _Case(unittest.TestCase):
    def setup(self, key, level, hero="wizard", walls=()):
        m, s = game(hero)
        wear(s, key, level)
        s.enemies.clear()
        s.projectiles.clear()
        s.zones.clear()
        statuses.combos.clear()
        s.world = open_map(80, 40, walls)
        h = s.hero
        h.x, h.y = 20.5, 20.5
        h.aim_angle = 0.0
        h.rng.random = lambda: 0.99          # no crits of its own, no status rolls
        self.s, self.h = s, h
        return s, h

    def tearDown(self):
        statuses.combos.clear()
        if pygame.display.get_init():
            pygame.mouse.set_visible(True)

    def place(self, *foes):
        self.s.enemies.extend(foes)
        return foes

    def go(self, seconds, inp=None, first=None):
        """Step the roll, the hero, shots and zones (systems/roll.py's part
        of GameScene._step)."""
        s, h = self.s, self.h
        for i in range(round(seconds * 60)):
            now = first if (i == 0 and first is not None) else (inp or PlayerInput())
            s.rules.tick(s.me, DT)
            roll.step(s, s.me, now, DT)
            rolling, x0, y0 = h.rolling, h.x, h.y
            h.move(now.move_x, now.move_y, DT, s.world)
            roll.after_move(s, s.me, rolling, x0, y0)
            combat.update_projectiles(s.projectiles, s.world, s.effects, DT, s._actors(), s.zones)
            roll.close_calls([s.me], s.projectiles, DT)
            update_zones(s.zones, s._actors(), s.effects, DT, s.world)
            s.rules.feet_tricks(DT)

    def roll(self, mx=1.0, my=0.0, seconds=0.3):
        self.go(seconds, first=press(mx, my))

    def shots_through(self, n, owner):
        """`n` enemy shots flying at the hero from ahead (+x), just short of
        them: a roll to +x goes through them."""
        h = self.h
        out = []
        for k in range(n):
            q = Projectile(h.x + 1.2 + 0.2 * k, h.y - 0.2 + 0.1 * k, math.pi, SHOT, owner=owner,
                           damage=10)
            out.append(q)
        self.s.projectiles.extend(out)
        return out


class FrameworkTest(unittest.TestCase):
    def test_every_feet_piece_has_three_tricks(self):
        feet = [k for k, g in config.GEAR.items() if g.slot == "feet"]
        self.assertEqual(len(feet), 11)
        for key in feet:
            self.assertEqual([t for t, _, _ in gear.tricks(key)], [3, 6, 9], key)
            for _, name, text in gear.tricks(key):
                self.assertTrue(name and text and text.isascii(), key)

    def test_the_slots_built_so_far(self):
        built = {config.GEAR[k].slot for k in config.GEAR_TRICKS}
        self.assertTrue({"off", "head", "feet"} <= built)    # (later steps add the rest)


class FencerTest(_Case):
    def test_disarm(self):
        s, h = self.setup("riposte", 3, "huntress")
        a = self.place(foe(26, 20.5, 5000))[0]
        a.rng = h.rng
        h.riposting = True
        combat.strike(a, 1, h, 0.0, s.effects)
        h.riposting = False
        self.assertEqual(a.disarmed, config.DISARM)
        q = Projectile(a.x, a.y, math.pi, SHOT, owner=a)
        s.projectiles.append(q)
        s.rules.enemy_shots([q])
        self.assertFalse(q.alive)
        self.assertEqual(a.disarmed, 0.0)
        # A wind-up under way stops instead.
        b = foe(26, 22, 5000)
        b.windup, b.tell = 0.6, 0.6
        h.riposting = True
        combat.strike(b, 1, h, 0.0, s.effects)
        h.riposting = False
        self.assertEqual((b.windup, getattr(b, "disarmed", 0)), (0.0, 0))
        # Its next hit on a hero does nothing.
        c = foe(26, 24, 5000)
        c.disarmed = 1.0
        hp = h.hp
        h.take_damage(10, c, None)
        self.assertEqual(h.hp, hp)

    def test_a_riposte_attack_marks_its_shots(self):
        s, h = self.setup("riposte", 3, "huntress")
        self.roll()
        s._attack(s.me)
        shots = [q for q in s.projectiles if q.owner is h]
        self.assertTrue(shots and all(q.riposte for q in shots))
        s.projectiles.clear()
        s._attack(s.me)
        self.assertFalse(any(q.riposte for q in s.projectiles))

    def test_second_thrust(self):
        s, h = self.setup("riposte", 6)
        self.roll()
        crits = [s.rules.attack_mods(s.me).get("sure_crit", False) for _ in range(3)]
        self.assertEqual(crits, [True, True, False])

    def test_en_garde(self):
        s, h = self.setup("riposte", 9)
        a = foe(26, 20.5, 1)
        h.roll_charges = 0
        h.riposting = True
        combat.strike(a, 50, h, 0.0, s.effects, sure_crit=True)
        h.riposting = False
        self.assertEqual(h.roll_charges, 1)


class WindrunnersTest(_Case):
    def test_draft(self):
        s, h = self.setup("slipstream", 3)
        boss = SimpleNamespace(airborne=0, submerged=False, x=h.x + 0.5, y=h.y, hit_radius=1.5,
                               facing=0.0, ctx=SimpleNamespace(players=[h], world=s.world))
        h.slipstream = 1.0
        Boss.shove_heroes(boss)
        self.assertEqual((h.x, h.y), (20.5, 20.5))
        h.slipstream = 0.0
        Boss.shove_heroes(boss)
        self.assertLess(h.x, 20.5)

    def test_afterimage(self):
        from ascii_adventurers.tests.test_players import make
        s, h = self.setup("slipstream", 6)
        self.roll()
        self.assertEqual(len(h.images), 1)
        im = h.images[0]
        self.assertEqual((im.x, im.y), (20.5, 20.5))
        self.assertIn(im, s._actors())
        e = make("goblin_archer", 30, 20.5)
        ctx = AIContext(s.world, [h], s._actors() + [e], [], [], decoys=s._images())
        self.assertIs(e._pick_player(ctx), im)
        # Enemy shots stop on it, harmlessly.
        q = Projectile(im.x - 2, im.y, 0.0, SHOT, owner=e)
        shots = [q]
        for _ in range(20):
            combat.update_projectiles(shots, s.world, [], DT, [im])
        self.assertFalse(shots)
        self.go(config.AFTERIMAGE)
        self.assertFalse(h.images)

    def test_jet_stream(self):
        s, h = self.setup("slipstream", 9)
        self.roll()
        self.go(3.0, PlayerInput(0, 1))
        self.assertGreater(h.slipstream, 0)
        self.go(config.JET_STREAM + 0.05)
        self.assertEqual(h.slipstream, 0.0)


class HairsbreadthTest(_Case):
    def test_graze(self):
        s, h = self.setup("close_call", 3)
        h.hp = h.max_hp - 10
        shooter = foe(40, 20.5)
        self.shots_through(3, shooter)
        self.go(0.25, first=press(1, 0))
        self.assertEqual(h.hp, h.max_hp - 10 + 3 * config.GRAZE)

    def test_deflect(self):
        s, h = self.setup("close_call", 6)
        shooter = self.place(foe(32, 20.5, 500))[0]
        q = self.shots_through(1, shooter)[0]
        self.go(0.1, first=press(1, 0))
        self.assertIs(q.owner, h)
        self.assertTrue(q.plain)
        self.go(1.5)
        self.assertAlmostEqual(500 - shooter.hp, 10 * config.DEFLECT)

    def test_untouchable(self):
        s, h = self.setup("close_call", 9)
        shooter = foe(40, 20.5)
        self.shots_through(config.UNTOUCHABLE[0], shooter)
        self.go(0.27, first=press(1, 0))
        self.assertGreater(h.untouchable, 0)
        self.assertFalse(h.hittable)
        self.assertEqual(h.take_damage(10, shooter, None), 0.0)
        self.go(config.UNTOUCHABLE[1])
        self.assertTrue(h.hittable)


class AshwalkersTest(_Case):
    def test_creeping_fire(self):
        s, h = self.setup("scorched_trail", 3)
        self.place(foe(20.5, 26))
        self.roll()
        n = len(s.zones)
        self.go(config.CREEPING_FIRE[0] + 0.1)
        crept = [z for z in s.zones if getattr(z, "crept", False) is True and z.y > 20.6]
        self.assertTrue(crept)
        self.assertEqual(len(s.zones), 2 * n)                # (each patch once)
        self.go(1.0)
        self.assertEqual(len(s.zones), 2 * n)

    def test_bellows(self):
        s, h = self.setup("scorched_trail", 6)
        self.roll(1, 0)
        a = self.place(foe(22.5, 20.5, 5000))[0]
        h.roll_charges = 1
        hp = a.hp
        self.roll(-1, 0)
        self.assertGreaterEqual(hp - a.hp, config.BELLOWS)

    def test_firewalk(self):
        s, h = self.setup("scorched_trail", 9)
        self.roll(seconds=config.ROLL_TIME)
        self.assertAlmostEqual(h.x - 20.5, config.ROLL_DISTANCE * config.FIREWALK[0], delta=0.3)
        self.assertTrue(all(abs(z.life - config.FIREWALK[1] * h.stats.duration_scale) < 1e-9
                            for z in s.zones))


class GallopersTest(_Case):
    def test_charge(self):
        s, h = self.setup("momentum", 3)
        h.vx = 3.0
        for _ in range(round(config.CHARGE[0] * 60) + 2):
            s.rules.tick(s.me, DT)
        self.assertTrue(h.charged)
        kw = s.rules.attack_mods(s.me)
        self.assertAlmostEqual(kw["mult"], 1 + config.CHARGE[1])
        self.assertFalse(h.charged)
        h.vx = 0.0
        s.rules.tick(s.me, DT)
        self.assertEqual(h.walk_t, 0.0)

    def test_hoofbeats(self):
        s, h = self.setup("momentum", 6)
        near, far = self.place(foe(24, 20.5, 500), foe(40, 20.5, 500))
        h.walked = h.hoof
        s.rules.tick(s.me, DT)
        self.assertLess(near.hp, 500)
        self.assertEqual(far.hp, 500)
        hp = near.hp
        s.rules.tick(s.me, DT)
        self.assertEqual(near.hp, hp)                         # (next one 10 tiles on)

    def test_full_gallop(self):
        s, h = self.setup("momentum", 9)
        st = h.stats
        st.move = 0.2
        a = foe(24, 20.5)
        base = combat.situational_bonus(st, h, a)
        st.flags.discard("momentum+9")
        self.assertAlmostEqual(base - combat.situational_bonus(st, h, a), 0.1)
        st.flags.add("momentum+9")
        h.mount = "camel"
        self.assertAlmostEqual(combat.situational_bonus(st, h, a) - base, config.FULL_GALLOP)


class WingheelTest(_Case):
    def test_quickstep(self):
        s, h = self.setup("fleet_strike", 3)
        a = foe(24, 20.5, 5000)
        for _ in range(5):
            combat.strike(a, 1, h, 0.0, s.effects, sure_crit=True)
        self.assertEqual(len(h.quick), config.QUICKSTEP[2])
        self.go(DT)
        self.assertAlmostEqual(h.speed_mult, 1 + config.QUICKSTEP[0] * config.QUICKSTEP[2])
        self.go(config.QUICKSTEP[1])
        self.assertEqual(h.speed_mult, 1.0)

    def test_featherweight(self):
        s, h = self.setup("fleet_strike", 6)
        combat.push(h, s.world, 1.0, 0.0)
        self.assertAlmostEqual(h.x, 20.5 + config.FEATHERWEIGHT)
        combat.push(h, s.world, 1.0, 0.0, full=True)
        self.assertAlmostEqual(h.x, 21.5 + config.FEATHERWEIGHT)

    def test_air_step(self):
        s, h = self.setup("fleet_strike", 9)
        h.stats.move = config.AIR_STEP - 0.1
        self.assertFalse(combat.skims(h))
        h.slipstream, h.speed_mult = 1.0, 1 + config.SLIPSTREAM[0]    # (the moment counts)
        self.assertTrue(combat.skims(h))
        h.speed_mult = 1.0
        h.stats.move = config.AIR_STEP
        self.assertTrue(combat.skims(h))
        hp = h.hp
        corpse = foe(40, 20.5)
        update_zones([Zone("gas", h.x, h.y, 2.0, 5.0, 0.5, 4.0, corpse)], [h], [], DT)
        combat.blast(h.x, h.y, 2.0, 10, corpse, [h], ground=True)
        self.assertEqual(h.hp, hp)
        combat.blast(h.x, h.y, 2.0, 10, corpse, [h])          # (not out of the ground)
        self.assertLess(h.hp, hp)


class PhasewalkersTest(_Case):
    def test_displacement(self):
        s, h = self.setup("blink", 3)
        left = self.place(foe(20.5, 21.5, 5000))[0]
        self.roll()
        self.assertLess(left.hp, 5000)

    def test_swap(self):
        s, h = self.setup("blink", 6)
        e = self.place(foe(20.5 + config.BLINK[0] + 0.5, 20.5, 5000))[0]
        ex = e.x
        self.roll(seconds=DT)
        self.assertAlmostEqual(h.x, ex)
        self.assertAlmostEqual(e.x, 20.5)

    def test_blink_storm(self):
        s, h = self.setup("blink", 9)
        self.roll()
        self.assertEqual(h.roll_charges, 0)
        x = h.x
        for _ in range(config.BLINK_STORM[0] - 1):
            self.roll()
        self.assertGreater(h.x - x, config.BLINK[0] * (config.BLINK_STORM[0] - 1) - 0.1)
        self.assertEqual(h.roll_recharge, 0.0)               # (paused for the storm)
        x = h.x
        self.roll()                                          # (the storm is spent)
        self.assertLess(h.x - x, 1.0)


class RamhornTest(_Case):
    def test_bowling(self):
        s, h = self.setup("shoulder_charge", 3, "dwarf")
        a, b = self.place(walker(22.0, 20.5, 5000), walker(22.0 + config.SHOULDER_CHARGE[2] + 0.8,
                                                          20.5, 5000))
        bx = b.x
        self.roll()
        self.assertLess(b.hp, 5000)
        self.assertGreater(b.x, bx)

    def test_battering_ram(self):
        s, h = self.setup("shoulder_charge", 6, "dwarf", walls=[(23, 20), (23, 21)])
        self.assertTrue(s.world.tile_at(23, 20).solid)
        self.roll()
        self.assertFalse(s.world.tile_at(23, 20).solid)
        self.assertGreater(h.x, 23.0)

    def test_rampage(self):
        s, h = self.setup("shoulder_charge", 9, "dwarf")
        self.place(walker(21.5, 20.5, 5000), walker(22.5, 22.5, 5000))
        self.place(walker(22.0, 18.6, 5000))
        self.roll(seconds=0.5)
        self.assertGreaterEqual(h.rampage, 1)
        self.assertGreater(h.x - 20.5, config.ROLL_DISTANCE + 0.8 * config.RAMPAGE[0] * h.rampage)


class TumblerTest(_Case):
    def mine(self):
        return [q for q in self.s.projectiles if q.owner is self.h]

    def test_double_flip(self):
        s, h = self.setup("backflip", 3, "huntress")
        self.go(0.05, first=press(0, 1))
        first = len(self.mine())
        self.assertEqual(first, config.BACKFLIP[0])
        self.go(0.3)
        self.assertEqual(len(self.mine()), 2 * config.BACKFLIP[0])

    def test_quick_draw(self):
        s, h = self.setup("backflip", 6, "huntress")
        self.go(0.05, first=press(0, 1))
        self.assertTrue(all(q.crit_x == config.QUICK_DRAW for q in self.mine()))

    def test_aerial(self):
        s, h = self.setup("backflip", 9, "huntress")
        self.assertEqual(s.rules.weapon_dt(s.me, DT), DT)
        self.go(0.05, first=press(0, 1))
        self.assertEqual(s.rules.weapon_dt(s.me, DT), DT * config.AERIAL[0])
        self.go(0.3)
        self.assertEqual(s.rules.weapon_dt(s.me, DT), DT * config.AERIAL[0])
        self.go(config.AERIAL[1])
        self.assertEqual(s.rules.weapon_dt(s.me, DT), DT)


class SlippersTest(_Case):
    def mine(self):
        return [q for q in self.s.projectiles if q.owner is self.h]

    def test_encore_spin(self):
        s, h = self.setup("pirouette", 3, "princess")
        self.go(0.05, first=press(0, 1))
        n = len(self.mine())
        self.go(0.3)
        self.assertEqual(len(self.mine()), n + config.ENCORE_SPIN)

    def test_dizzy(self):
        s, h = self.setup("pirouette", 6, "princess")
        a = self.place(foe(23, 20.5, 5000))[0]
        a.rng = h.rng
        self.go(0.4, first=press(0, 1))
        self.assertGreater(a.dizzy, 0)
        q = Projectile(a.x, a.y, 0.0, SHOT, owner=a)
        s.rules.enemy_shots([q])
        self.assertAlmostEqual(abs(q.angle), math.radians(config.DIZZY[0]))
        self.assertEqual(a.dizzy, 0.0)

    def test_prima(self):
        s, h = self.setup("pirouette", 9, "princess")
        self.place(*[foe(20.5 + 3 * math.cos(k), 20.5 + 3 * math.sin(k)) for k in range(4)])
        self.place(foe(40, 20.5))
        s.projectiles.clear()
        self.go(DT, first=press(0, 1))
        self.assertEqual(len(self.mine()), config.PIROUETTE[0] + 4)


class StompersTest(_Case):
    def beats(self):
        return [e for e in self.s.effects if e.kind == "pulse"]

    def test_double_drop(self):
        s, h = self.setup("drop_the_beat", 3, "bard")
        self.go(0.05, first=press(0, 1))
        self.assertEqual(len(self.beats()), 1)
        self.go(0.3)
        self.assertEqual(len(self.beats()), 2)

    def test_crowd_surf(self):
        s, h = self.setup("drop_the_beat", 6, "bard")
        self.place(*[foe(21.5 + k, 21.0, 5000) for k in range(3)])
        with mock.patch.object(roll, "attack", wraps=roll.attack) as beat:
            self.roll()
        self.assertEqual(len(h.surfed), 3)
        mult = beat.call_args.kwargs["mult"]
        self.assertAlmostEqual(mult, config.DROP_THE_BEAT * (1 + 3 * config.CROWD_SURF[1]))

    def test_amplifier(self):
        s, h = self.setup("drop_the_beat", 9, "bard")
        self.roll()
        self.assertEqual(len(h.amps), 1)
        ax, ay = h.amps[0][:2]
        h.x += 5
        s.effects.clear()
        s._attack(s.me)
        spots = {(round(e.x, 2), round(e.y, 2)) for e in self.beats()}
        self.assertIn((round(ax, 2), round(ay, 2)), spots)
        self.assertIn((round(h.x, 2), round(h.y, 2)), spots)
        self.go(config.AMPLIFIER[0])
        self.assertFalse(h.amps)


if __name__ == "__main__":
    unittest.main()
