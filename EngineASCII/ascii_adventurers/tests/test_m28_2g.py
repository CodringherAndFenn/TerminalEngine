"""M28.2g: the wizard's main hand's +3 / +6 / +9 tricks (design/GEAR.md 17.7)."""

import math
import os
from dataclasses import replace
from types import SimpleNamespace
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.entities.character import Character
from ascii_adventurers.entities.projectile import Projectile
from ascii_adventurers.players import gear
from ascii_adventurers.render.spell_fx import draw_ghost_sight, draw_summons
from ascii_adventurers.systems import combat, spells
from ascii_adventurers.systems.statuses import inflict
from ascii_adventurers.systems.zones import Zone, along, update_zones
from ascii_adventurers.tests.test_m28_2a import foe, wear
from ascii_adventurers.tests.test_m28_2c import DT, _Case
from ascii_adventurers.tests.test_m28_2e import dead

BASE = 1000.0
STRIKE = "ascii_adventurers.systems.combat.strike"
LIGHTNING = ("storm_caller", "conductor", "supercell", "ball_lightning")


def movable(x, y, hp=BASE):
    """A foe that can be pushed about (combat.push)."""
    d = foe(x, y, hp)
    d.half = 0.4
    d.espec = SimpleNamespace(speed=3.0, elite=False, xp=10, name="movable")
    return d


def victims(hit):
    return [c.args[0] for c in hit.call_args_list]


class _Staff(_Case):
    def setup(self, key, level, walls=()):
        s, h = super().setup(key, level, "wizard", walls)
        if key in LIGHTNING:
            wear(s, "chain_lightning", 0)                 # (they need the Chainbolt Charm)
            h.rng.random = lambda: 0.99
        h.time = 100.0
        self.world = s.world
        return s, h

    def dart(self, x=None, y=None, angle=0.0, damage=10.0):
        h = self.h
        p = Projectile(h.x + 1.0 if x is None else x, h.y if y is None else y, angle,
                       h.weapon.spec.shell, owner=h, damage=damage)
        p.tags = h.weapon.spec.tags
        p.group = {}
        return p

    def bolt(self, x=None, y=None, angle=0.0, damage=100.0, jumps=2):
        h = self.h
        shell = replace(config.SPELL_SHELLS["chain"], chain=jumps)
        p = Projectile(h.x + 1.0 if x is None else x, h.y if y is None else y, angle, shell,
                       owner=h, damage=damage)
        p.tags = config.SPELLS["chain_lightning"].tags
        return p

    def hit(self, p, victim, **kw):
        s = self.s
        return combat._hit_actor(p, victim, victim.x, victim.y, s.world, s._actors(), s.effects,
                                 kw.get("spawned", []), kw.get("zones", s.zones),
                                 kw.get("shots", s.projectiles))

    def chain(self, first, jumps=5, damage=100.0, zones=None):
        shell = replace(config.SPELL_SHELLS["chain"], chain=jumps)
        with mock.patch(STRIKE) as hit:
            combat.chain_from(first, shell, damage, self.h, self.s.world, self.s._actors(),
                              self.s.effects, zones=zones)
        return hit

    def fly(self, shots, seconds):
        s = self.s
        for _ in range(round(seconds * 60)):
            self.h.time += DT
            combat.update_projectiles(shots, s.world, s.effects, DT, s._actors(), s.zones)
            update_zones(s.zones, s._actors(), s.effects, DT, s.world)

    def cast(self, times=1):
        """Chain Lightning goes off `times` times (its own timer held)."""
        s, st = self.s, self.s.me.spells["chain_lightning"]
        st.params = dict(st.params, interval=1000.0)
        for _ in range(times):
            st.timer = 0.0
            self.h.time += DT
            spells.update_spells(self.h, s.me.spells, s.world, s._actors(), s.effects, DT,
                                 s.projectiles, s.zones)


class FrameworkTest(unittest.TestCase):
    def test_every_wizard_main_hand_has_three_tricks(self):
        staffs = [k for k, g in config.GEAR.items()
                  if g.slot == "main" and config.CARDS[k].heroes == ("wizard",)]
        self.assertEqual(len(staffs), 10)
        for key in staffs:
            self.assertIn(key, config.GEAR_TRICKS)
            self.assertEqual([t for t, _, _ in gear.tricks(key)], [3, 6, 9], key)
            for _, name, text in gear.tricks(key):
                self.assertTrue(name and text and text.isascii(), key)


class DrawTest(_Staff):
    def test_every_trick_draws(self):
        s, h = self.setup("phase_darts", 9, walls=[(23, y) for y in range(18, 24)])
        self.place(foe(26.0, 20.5, BASE), foe(18.0, 20.5, BASE))
        s.zones += [Zone("ball", 22.0, 21.0, 2.5, 3.0, 0.25, 1.0, h, path=[(20, 20), (25, 22)]),
                    Zone("well", 18.0, 19.0, 2.5, 1.5, 999.0, 0.0, h, pull=2.0),
                    Zone("crackle", 19.0, 22.0, 1.5, 2.0, 0.25, 1.0, h, follow=s.enemies[1])]
        for _ in range(30):
            s.steps += 1
            draw_ghost_sight(s.manager.text, s.me.camera, s.world, s.players, s.enemies, s.steps)
            draw_summons(s.manager.text, s.me.camera, s.players, s.zones, s.steps)


class StormcallerTest(_Staff):
    def test_conducting_darts(self):
        s, h = self.setup("storm_caller", 3)
        a, b = self.place(foe(24.0, 20.5, BASE), foe(26.0, 20.5, BASE))
        combat._bolted(a, h)                              # (your bolt hit it)
        with mock.patch(STRIKE) as hit:
            self.hit(self.dart(), a)
        self.assertEqual(victims(hit), [a, b])
        self.assertAlmostEqual(hit.call_args.args[1], 10.0 * config.CONDUCTING[1])
        self.assertEqual(hit.call_args.args[5], config.SPELLS["chain_lightning"].tags)
        h.time += config.CONDUCTING[0] + 0.1              # (too long ago)
        with mock.patch(STRIKE) as hit:
            self.hit(self.dart(), a)
        self.assertEqual(victims(hit), [a])

    def test_a_bolt_marks_what_it_hits(self):
        s, h = self.setup("storm_caller", 3)
        a, b = self.place(foe(24.0, 20.5, BASE), foe(26.0, 20.5, BASE))
        self.chain(a, jumps=1)
        self.assertEqual(a.bolted[id(h)], h.time)
        self.assertEqual(b.bolted[id(h)], h.time)

    def test_through_walls(self):
        for level, want in ((3, 0), (6, 1)):
            s, h = self.setup("storm_caller", level, walls=[(26, 20)])
            a, b = self.place(foe(24.5, 20.5, BASE), foe(27.5, 20.5, BASE))
            hit = self.chain(a, jumps=1)
            self.assertEqual(victims(hit), [b] * want, level)

    def test_thunderlord(self):
        s, h = self.setup("storm_caller", 9)
        self.place(foe(24.0, 20.5, BASE))
        self.cast()
        nine = s.projectiles[-1].spec.chain
        s, h = self.setup("storm_caller", 6)
        self.place(foe(24.0, 20.5, BASE))
        self.cast()
        self.assertEqual(nine, s.projectiles[-1].spec.chain + config.THUNDERLORD[0])
        s, h = self.setup("storm_caller", 9)
        line = self.place(*(foe(24.0 + 2 * i, 20.5, BASE) for i in range(6)))
        hit = self.chain(line[0], jumps=5)
        again = hit.call_args_list[5:]
        self.assertEqual([c.args[0] for c in again], list(line))
        for c in again:
            self.assertAlmostEqual(c.args[1], 100.0 * config.THUNDERLORD[2])
        hit = self.chain(line[0], jumps=4)                # (4 jumps: no strike again)
        self.assertEqual(hit.call_count, 4)


class CopperwireTest(_Staff):
    def jumps(self, level, gap=2.0, n=3):
        s, h = self.setup("conductor", level)
        line = self.place(*(foe(24.0 + gap * i, 20.5, BASE) for i in range(n)))
        return self.chain(line[0], jumps=n - 1)

    def test_resistor(self):
        fade = config.SPELL_SHELLS["chain"].chain_falloff
        damage = [c.args[1] for c in self.jumps(3).call_args_list]
        self.assertEqual(damage, [100.0, 100.0 * fade])
        damage = [c.args[1] for c in self.jumps(2).call_args_list]
        self.assertEqual(damage, [100.0 * fade, 100.0 * fade * fade])

    def test_overcurrent(self):
        far = config.SPELL_SHELLS["chain"].chain_range * 0.9
        extra = [c.kwargs["extra"] for c in self.jumps(6, gap=far).call_args_list]
        self.assertEqual(extra, [config.OVERCURRENT[1]] * 2)
        extra = [c.kwargs["extra"] for c in self.jumps(6, gap=2.0).call_args_list]
        self.assertEqual(extra, [0.0, 0.0])
        extra = [c.kwargs["extra"] for c in self.jumps(3, gap=far).call_args_list]
        self.assertEqual(extra, [0.0, 0.0])

    def test_superconductor(self):
        damage = [c.args[1] for c in self.jumps(9, n=4).call_args_list]
        self.assertEqual(damage, [100.0] * 3)


class ThunderheadTest(_Staff):
    def test_charged_air(self):
        s, h = self.setup("supercell", 3)
        a = self.place(foe(24.0, 20.5, BASE))[0]
        self.assertEqual(combat._dart_bonus(self.dart(), a, h.stats), 0.0)
        inflict(a, "shock", h)
        self.assertAlmostEqual(combat._dart_bonus(self.dart(), a, h.stats), config.CHARGED_AIR)
        with mock.patch(STRIKE) as hit:
            self.hit(self.dart(), a)
        self.assertGreaterEqual(hit.call_args.kwargs["extra"], config.CHARGED_AIR)

    def test_downdraft(self):
        for shocked, bolts in ((3, 2), (2, 1)):
            s, h = self.setup("supercell", 6)
            near = self.place(*(foe(22.0 + i, 22.0, BASE) for i in range(3)))
            for a in near[:shocked]:
                inflict(a, "shock", h)
            self.cast()
            shots = [q for q in s.projectiles if q.owner is h]
            self.assertEqual(len(shots), bolts, shocked)
            if bolts == 2:                                # (at two different enemies)
                self.assertNotAlmostEqual(shots[0].angle, shots[1].angle)

    def test_superstorm(self):
        s, h = self.setup("supercell", 9)
        a, b, c = self.place(foe(24.0, 20.5, BASE), foe(25.2, 20.5, BASE),
                             foe(28.0, 20.5, BASE))
        with mock.patch("ascii_adventurers.systems.combat.chain_from", return_value=[]), \
                mock.patch(STRIKE):
            self.hit(self.bolt(), a)
        self.assertTrue(b.status is not None and b.status.has("shock"))
        self.assertTrue(c.status is None or not c.status.has("shock"))
        s, h = self.setup("supercell", 9)
        c, d, e = self.place(foe(28.0, 20.5, BASE), foe(30.0, 20.5, BASE),
                             foe(31.0, 20.5, BASE))
        self.chain(c, jumps=1)                            # (a jump to d shocks e by it)
        self.assertTrue(e.status is not None and e.status.has("shock"))


class CrackleTest(_Staff):
    def test_sticky(self):
        for level, sticks in ((3, True), (0, False)):
            s, h = self.setup("ball_lightning", level)
            a = self.place(foe(24.0, 20.5, BASE))[0]
            with mock.patch("ascii_adventurers.systems.combat.chain_from", return_value=[]), \
                    mock.patch(STRIKE):
                self.hit(self.bolt(), a)
            z = s.zones[-1]
            self.assertEqual(z.kind, "crackle")
            a.x += 3.0
            update_zones(s.zones, s._actors(), s.effects, DT, s.world)
            self.assertEqual((z.x, z.y) == (a.x, a.y), sticks, level)

    def test_crackling_chain(self):
        for level, want in ((6, 2), (3, 0)):
            s, h = self.setup("ball_lightning", level)
            line = self.place(*(foe(24.0 + 2 * i, 20.5, BASE) for i in range(3)))
            zones = []
            self.chain(line[0], jumps=2, zones=zones)
            self.assertEqual(len(zones), want, level)
            if want:
                self.assertEqual([(z.x, z.y) for z in zones], [(a.x, a.y) for a in line[1:]])

    def test_thunderball(self):
        s, h = self.setup("ball_lightning", 9)
        a, b = self.place(foe(26.0, 20.5, BASE), foe(28.0, 20.5, BASE))
        balls = []
        for i in range(config.THUNDERBALL[0] * 2):
            s.projectiles.clear()
            self.cast()
            balls.append(s.projectiles[-1].ball is not None)
        every = config.THUNDERBALL[0]
        self.assertEqual(balls, [(i + 1) % every == 0 for i in range(every * 2)])
        start = s.projectiles[-1].ball[0]
        with mock.patch(STRIKE):
            self.fly(s.projectiles, 0.5)
        ball = [z for z in s.zones if z.kind == "ball"]
        self.assertEqual(len(ball), 1)
        path = ball[0].path
        self.assertEqual(path[0], start)
        self.assertEqual(path[-1], (b.x, b.y))            # (through the jump to b)
        self.assertEqual(along([(0, 0), (4, 0), (4, 4)], 0.75), (4.0, 2.0))

    def test_a_ball_on_a_miss(self):
        s, h = self.setup("ball_lightning", 9)
        p = self.bolt()
        p.ball = [(h.x, h.y)]
        p.x, p.alive = 30.0, False
        combat._shot_ends([p], [], s.zones)
        self.assertEqual(s.zones[-1].kind, "ball")
        self.assertEqual(s.zones[-1].path, [(h.x, h.y), (30.0, p.y)])


class GhostwoodTest(_Staff):
    def test_haunt(self):
        for walls, want in (([(23, 20)], config.HAUNT), ((), 0.0)):
            s, h = self.setup("phase_darts", 3, walls=walls)
            a = self.place(foe(27.0, 20.5, BASE))[0]
            with mock.patch(STRIKE) as hit:
                self.fly([self.dart()], 0.5)
            self.assertEqual(victims(hit), [a])
            self.assertAlmostEqual(hit.call_args.kwargs["extra"], want)

    def test_spectral(self):
        shield = Character(config.BODIES["shieldbearer"], 24.0, 20.5)
        shield.aim_angle = math.pi                        # (facing the hero)
        s, h = self.setup("phase_darts", 6)
        self.assertEqual(shield.take_damage(10.0, h, 0.0), 0.0)
        h.spectral = True
        self.assertEqual(shield.take_damage(10.0, h, 0.0), 10.0)
        h.spectral = False
        seen = []
        with mock.patch(STRIKE, side_effect=lambda *a, **k: seen.append(h.spectral) or 0.0):
            self.hit(self.dart(), self.place(foe(24.0, 20.5, BASE))[0])
        self.assertEqual(seen, [True])
        self.assertFalse(h.spectral)

    def test_ghost_sight(self):
        for level, found in ((9, True), (6, False)):
            s, h = self.setup("phase_darts", level, walls=[(22, 22)])
            a = self.place(foe(22.5, 24.0, BASE))[0]       # (behind a wall, off the aim)
            p = self.dart()
            p.seek_point = (40.0, 20.5)
            p.travelled = 5.0
            combat._home(p, s._actors(), DT)
            self.assertEqual(p.seek is a, found, level)


class WyrmseekerTest(_Staff):
    def test_persistence(self):
        s, h = self.setup("seeker", 3)
        a = dead(self.place(foe(24.0, 20.5, BASE))[0])
        p = self.dart()
        p.seek = a
        combat._home(p, s._actors(), DT)
        self.assertAlmostEqual(p.pace, config.PERSISTENCE)
        p.seek = a
        combat._home(p, s._actors(), DT)
        self.assertAlmostEqual(p.pace, config.PERSISTENCE)  # (once)

    def test_hunter_seeker(self):
        for level, low in ((6, True), (3, False)):
            s, h = self.setup("seeker", level)
            near, weak = self.place(foe(25.0, 20.5, BASE), foe(27.0, 21.5, BASE))
            weak.hp = 10.0
            p = self.dart()
            p.seek_point, p.travelled = (25.0, 20.5), 5.0
            combat._home(p, s._actors(), DT)
            self.assertIs(p.seek, weak if low else near, level)

    def test_endless_hunt(self):
        s, h = self.setup("seeker", 9)
        line = self.place(*(foe(24.5 + 3 * i, 20.5, BASE) for i in range(4)))
        p = self.dart()
        with mock.patch(STRIKE) as hit:
            self.fly([p], 1.5)
        self.assertEqual(victims(hit), list(line[:config.ENDLESS_HUNT[0]]))
        mults = [c.kwargs["mult"] for c in hit.call_args_list]
        share = config.ENDLESS_HUNT[1]
        self.assertEqual(mults, [1.0, share, share])
        s, h = self.setup("seeker", 6)
        line = self.place(*(foe(24.5 + 3 * i, 20.5, BASE) for i in range(4)))
        with mock.patch(STRIKE) as hit:
            self.fly([self.dart()], 1.5)
        self.assertEqual(victims(hit), [line[0]])


class HummingTest(_Staff):
    def counts(self, level, gaps):
        s, h = self.setup("resonance", level)
        a = self.place(foe(24.0, 20.5, BASE))[0]
        out = []
        for gap in gaps:
            h.time += gap
            out.append(round(combat._resonance(a, h), 6))
        return out

    def test_sustain(self):
        per = config.RESONANCE[1]
        self.assertEqual(self.counts(3, (0, 1.5, 0.9)), [0.0, per, 2 * per])
        self.assertEqual(self.counts(0, (0, 1.5, 0.9)), [0.0, 0.0, per])

    def test_perfect_pitch(self):
        per = config.RESONANCE[1]
        self.assertAlmostEqual(self.counts(9, [0.1] * 12)[-1], per * config.PERFECT_PITCH)
        self.assertAlmostEqual(self.counts(6, [0.1] * 12)[-1], per * config.RESONANCE[2])

    def test_resonant_ring(self):
        s, h = self.setup("resonance", 6)
        a, b, c = self.place(foe(24.0, 20.5, BASE), foe(25.5, 20.5, BASE),
                             foe(28.0, 20.5, BASE))
        rings = []
        for i in range(9):
            h.time += 0.1
            with mock.patch(STRIKE) as hit:
                self.hit(self.dart(), a)
            rings.append([v for v, call in zip(victims(hit), hit.call_args_list)
                          if call.args[1] == config.RESONANT_RING[0]])
        # (the 5th dart is at +60%; then nothing until a second has passed)
        self.assertEqual(rings[:4], [[]] * 4)
        self.assertEqual(rings[4], [a, b])
        self.assertEqual(rings[5:], [[]] * 4)
        h.time += 0.6
        with mock.patch(STRIKE) as hit:
            self.hit(self.dart(), a)
        self.assertEqual(victims(hit)[1:], [a, b])
        self.assertFalse(hit.call_args.kwargs["on_hit"])


class GravewellTest(_Staff):
    def test_crush(self):
        for level, want in ((3, 2), (0, 0)):
            s, h = self.setup("implosion", level)
            a, b = self.place(movable(25.0, 20.5), movable(26.3, 20.5))
            far = self.place(movable(25.0, 22.4))[0]       # (dragged, but into nobody)
            with mock.patch(STRIKE) as hit:
                self.hit(self.dart(damage=7.0), a)
            crushed = [c.args[0] for c in hit.call_args_list if c.args[1] == config.CRUSH]
            self.assertEqual(sorted(map(id, crushed)), sorted(map(id, [a, b][:want])), level)
            self.assertNotIn(far, crushed)

    def test_event_horizon(self):
        s, h = self.setup("implosion", 6)
        a = self.place(movable(25.0, 20.5))[0]
        enemy = foe(40.0, 40.0)
        shell = config.WEAPONS["sling"].shell if "sling" in config.WEAPONS else \
            config.SPELL_SHELLS["wand"]
        theirs = Projectile(26.0, 20.5, math.pi, shell, owner=enemy)
        ours = Projectile(25.0, 21.5, math.pi, shell, owner=h)
        lobbed = Projectile(25.0, 19.5, math.pi, replace(shell, lob=True), owner=enemy)
        far = Projectile(27.0, 20.5, math.pi, shell, owner=enemy)
        shots = [theirs, ours, lobbed, far]
        with mock.patch(STRIKE):
            self.hit(self.dart(), a, shots=shots)
        self.assertAlmostEqual(theirs.x, 26.0 - config.IMPLOSION[1])
        self.assertEqual((ours.x, ours.y), (25.0, 21.5))
        self.assertEqual((lobbed.x, lobbed.y), (25.0, 19.5))
        self.assertEqual((far.x, far.y), (27.0, 20.5))

    def test_singularity(self):
        s, h = self.setup("implosion", 9)
        every = config.SINGULARITY[0]
        a, b = self.place(movable(30.0, 20.5), movable(31.5, 22.0))
        boss = self.place(movable(29.0, 19.0))[0]
        boss.boss = True
        for attacks, wells in ((every - 1, 0), (every, 1)):
            s.projectiles.clear()
            s.zones.clear()
            h.attacks = attacks
            combat.volley(h, s.world, s.projectiles, s.effects, 0.0, 3, 50.0,
                          h.weapon.spec.shell, h.weapon.spec.tags)
            group = s.projectiles[0].group
            with mock.patch(STRIKE):
                self.hit(s.projectiles[0], a)
                self.hit(s.projectiles[1], a)             # (the cast's first hit only)
            self.assertEqual(len([z for z in s.zones if z.kind == "well"]), wells, attacks)
        well = s.zones[-1]
        b.x, b.y = 31.5, 22.0                             # (back from the darts' own drag)
        bx, by, ox, oy = b.x, b.y, boss.x, boss.y
        update_zones(s.zones, s._actors(), s.effects, 0.5, s.world)
        self.assertLess(math.hypot(b.x - well.x, b.y - well.y), math.hypot(bx - well.x, by - well.y))
        self.assertEqual((boss.x, boss.y), (ox, oy))
        self.assertFalse(group.get("well"))


class StormheartTest(_Staff):
    def storm(self, kills, hx=26.0):
        s, h = self.s, self.h
        p = self.dart()
        spawned = []
        for i in range(kills):
            victim = dead(foe(hx, 20.5, BASE))
            combat._dart_hit(p, victim, hx, 20.5, h, h.stats, s.world, s._actors(), s.effects,
                             spawned)
        return p, spawned

    def test_squall(self):
        s, h = self.setup("arcane_storm", 3)
        by_me, by_kill = self.place(foe(22.0, 20.5, BASE), foe(30.0, 20.5, BASE))
        spawned = []
        combat._dart_hit(self.dart(), dead(foe(29.0, 20.5)), 29.0, 20.5, h, h.stats, s.world,
                         s._actors(), s.effects, spawned)
        self.assertIs(spawned[0].seek, by_me)
        s, h = self.setup("arcane_storm", 0)
        by_me, by_kill = self.place(foe(22.0, 20.5, BASE), foe(30.0, 20.5, BASE))
        spawned = []
        combat._dart_hit(self.dart(), dead(foe(29.0, 20.5)), 29.0, 20.5, h, h.stats, s.world,
                         s._actors(), s.effects, spawned)
        self.assertIs(spawned[0].seek, by_kill)

    def test_tempest(self):
        for level, most in ((6, config.STORM_TEMPEST), (3, config.ARCANE_STORM[0])):
            s, h = self.setup("arcane_storm", level)
            self.place(foe(28.0, 20.5, BASE))
            p, spawned = self.storm(8)
            self.assertEqual(len(spawned), most, level)

    def test_maelstrom(self):
        s, h = self.setup("arcane_storm", 9)
        self.place(foe(28.0, 20.5, BASE))
        p = self.dart(damage=10.0)
        spawned = []
        for _ in range(12):
            combat._dart_hit(p, dead(foe(26.0, 20.5)), 26.0, 20.5, h, h.stats, s.world,
                             s._actors(), s.effects, spawned)
        self.assertEqual(len(spawned), 12)
        self.assertAlmostEqual(spawned[0].damage, 10.0 * config.MAELSTROM)
        child = spawned[0]
        more = []
        combat._dart_hit(child, dead(foe(26.0, 20.5)), 26.0, 20.5, h, h.stats, s.world,
                         s._actors(), s.effects, more)
        self.assertAlmostEqual(more[0].damage, 10.0 * config.MAELSTROM ** 2)


class OrreryTest(_Staff):
    def test_planets(self):
        for level, passed in ((3, True), (0, False)):
            s, h = self.setup("orbiting_darts", level)
            on_way, target = self.place(foe(24.0, 20.5, BASE), foe(28.0, 20.5, BASE))
            p = self.dart()
            p.orbits, p.seek = 1, target
            with mock.patch(STRIKE) as hit:
                self.fly([p], 0.5)
            self.assertEqual(victims(hit), [on_way, target] if passed else [on_way], level)

    def test_epicycle(self):
        for level, most in ((6, config.EPICYCLE), (3, 1)):
            s, h = self.setup("orbiting_darts", level)
            self.place(foe(20.5, 25.0, BASE))
            p = self.dart()
            swings = 0
            while combat._orbit_again(p, s._actors()):
                swings += 1
            self.assertEqual(swings, most, level)

    def test_gravity_assist(self):
        s, h = self.setup("orbiting_darts", 9)
        a = self.place(foe(20.5, 25.0, BASE))[0]
        p = self.dart()
        self.assertEqual(combat._dart_bonus(p, a, h.stats), 0.0)
        self.assertTrue(combat._orbit_again(p, s._actors()))
        self.assertAlmostEqual(p.pace, config.GRAVITY_ASSIST[0])
        self.assertAlmostEqual(combat._dart_bonus(p, a, h.stats), config.GRAVITY_ASSIST[1])
        s, h = self.setup("orbiting_darts", 6)
        self.place(foe(20.5, 25.0, BASE))
        p = self.dart()
        combat._orbit_again(p, s._actors())
        self.assertEqual(p.pace, 1.0)


if __name__ == "__main__":
    unittest.main()
