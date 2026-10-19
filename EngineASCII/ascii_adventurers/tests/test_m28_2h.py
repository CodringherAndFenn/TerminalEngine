"""M28.2h: the dwarf's and the huntress's main hands' +3 / +6 / +9 tricks
(design/GEAR.md 17.8)."""

import math
import os
from types import SimpleNamespace
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.entities.projectile import Projectile
from ascii_adventurers.players import gear
from ascii_adventurers.render.ascii_fx import draw_projectiles
from ascii_adventurers.render.spell_fx import draw_statuses, draw_summons
from ascii_adventurers.systems import combat
from ascii_adventurers.systems.zones import Zone, update_zones
from ascii_adventurers.tests.test_m28_2a import foe
from ascii_adventurers.tests.test_m28_2c import DT, _Case
from ascii_adventurers.tests.test_m28_2e import dead

BASE = 1000.0
STRIKE = "ascii_adventurers.systems.combat.strike"
DWARF = ("ricochet", "hang_time", "homeward_fury", "tether", "cyclone", "splitting_axe")


def movable(x, y, hp=BASE):
    d = foe(x, y, hp)
    d.half = 0.4
    d.espec = SimpleNamespace(speed=3.0, elite=False, xp=10, name="movable")
    return d


def elite(x, y, hp=BASE):
    d = foe(x, y, hp)
    d.espec = SimpleNamespace(speed=3.0, elite=True, xp=10, name="elite")
    return d


def victims(hit):
    return [c.args[0] for c in hit.call_args_list]


class _Main(_Case):
    def setup(self, key, level, walls=()):
        hero = "dwarf" if key in DWARF else "huntress"
        s, h = super().setup(key, level, hero, walls)
        h.time = 100.0
        return s, h

    def shot(self, x=None, y=None, angle=0.0, damage=20.0):
        h = self.h
        p = Projectile(h.x + 1.0 if x is None else x, h.y if y is None else y, angle,
                       h.weapon.spec.shell, owner=h, damage=damage)
        p.tags = h.weapon.spec.tags
        return p

    def hit(self, p, victim):
        s = self.s
        return combat._hit_actor(p, victim, victim.x, victim.y, s.world, s._actors(), s.effects,
                                 [], s.zones, s.projectiles)

    def fly(self, shots, seconds):
        s = self.s
        for _ in range(round(seconds * 60)):
            self.h.time += DT
            combat.update_projectiles(shots, s.world, s.effects, DT, s._actors(), s.zones)
            update_zones(s.zones, s._actors(), s.effects, DT, s.world)


class FrameworkTest(unittest.TestCase):
    def test_every_dwarf_and_huntress_main_hand_has_three_tricks(self):
        keys = [k for k, g in config.GEAR.items() if g.slot == "main"
                and config.CARDS[k].heroes in (("dwarf",), ("huntress",))]
        self.assertEqual(len(keys), 12)
        for key in keys:
            self.assertEqual([t for t, _, _ in gear.tricks(key)], [3, 6, 9], key)
            for _, name, text in gear.tricks(key):
                self.assertTrue(name and text and text.isascii(), key)

    def test_no_config_name_is_defined_twice(self):
        path = os.path.join(os.path.dirname(config.__file__), "config.py")
        with open(path) as src:
            names = [line.split("=")[0].strip() for line in src
                     if line[:1].isupper() and " = " in line and not line.startswith(" ")]
        self.assertEqual(sorted({n for n in names if names.count(n) > 1}), [])


class DrawTest(_Main):
    def test_every_trick_draws(self):
        s, h = self.setup("tether", 9)
        a = self.place(foe(24.0, 20.5, BASE))[0]
        h.marked, h.marks = a, [(foe(26.0, 22.0), h.time + 2)]
        p = self.shot()
        p.flail, p.flail_r, p.flail_a = 3.0, 4.0, 0.0
        s.projectiles.append(p)
        s.zones.append(Zone("thorns", 22.0, 21.0, 1.0, 2.0, 0.5, 5.0, h))
        for _ in range(30):
            s.steps += 1
            draw_summons(s.manager.text, s.me.camera, s.players, s.zones, s.steps)
            draw_projectiles(s.manager.text, s.me.camera, s.projectiles)
            draw_statuses(s.manager.text, s.me.camera, s.enemies, [a] + [m for m, _ in h.marks])


class ReboundTest(_Main):
    def test_bank_shot(self):
        s, h = self.setup("ricochet", 3)
        p = self.shot()
        p.bounces, p.pinballed = 2, True
        self.assertAlmostEqual(combat._axe_bonus(p, h.stats), config.BANK_SHOT * 3)
        s, h = self.setup("ricochet", 2)
        self.assertEqual(combat._axe_bonus(p, h.stats), 0.0)

    def test_pinball(self):
        for level, back in ((6, True), (3, False)):
            s, h = self.setup("ricochet", level)
            big = self.place(elite(24.0, 20.5))[0]
            p = self.shot()
            with mock.patch(STRIKE):
                self.fly([p], 0.15)
            self.assertEqual(p.dir_x < 0, back, level)
            self.assertEqual(p.pinballed, back)
        s, h = self.setup("ricochet", 6)
        self.place(foe(24.0, 20.5, BASE))                 # (not a big one: straight through)
        p = self.shot()
        with mock.patch(STRIKE):
            self.fly([p], 0.15)
        self.assertGreater(p.dir_x, 0)

    def test_carom(self):
        walls = [(x, y) for x in (18, 23) for y in range(15, 26)]
        for level, most in ((9, config.CAROM), (6, config.RICOCHET_BOUNCES)):
            s, h = self.setup("ricochet", level, walls=walls)
            p = self.shot()
            p.max_range = 100.0
            for _ in range(240):
                combat.update_projectiles([p], s.world, s.effects, DT, s._actors(), s.zones)
                if p.returning:
                    break
            self.assertTrue(p.returning, level)
            self.assertEqual(p.bounces, most, level)


class HoverheadTest(_Main):
    def hovering(self, level):
        s, h = self.setup("hang_time", level)
        p = self.shot(x=25.0)
        p.hang, p.hung, p.hang_tick = 0.05, True, 1.0
        return s, h, p

    def test_saw(self):
        s, h, p = self.hovering(3)
        self.assertEqual([round(combat._axe_bonus(p, h.stats), 6) for _ in range(3)],
                         [0.0, config.SAW, 2 * config.SAW])
        p.hang = 0.0                                       # (not hovering: no saw)
        self.assertEqual(combat._axe_bonus(p, h.stats), 0.0)

    def test_hold_it_there(self):
        s, h, p = self.hovering(6)
        h.trigger = True
        self.fly([p], 1.0)
        self.assertGreater(p.hang, 0)
        self.assertFalse(p.returning)
        self.fly([p], config.HOLD_IT)
        self.assertTrue(p.returning)                       # (2 s at most)
        s, h, p = self.hovering(6)
        h.trigger = False
        self.fly([p], 0.2)
        self.assertTrue(p.returning)
        s, h, p = self.hovering(3)
        h.trigger = True
        self.fly([p], 0.2)
        self.assertTrue(p.returning)

    def test_buzzsaw(self):
        for level, reached in ((9, True), (6, False)):
            s, h, p = self.hovering(level)
            p.hang, p.hang_tick = 0.5, 0.0
            near = self.place(foe(25.0, 21.7, BASE))[0]    # (1.2 tiles off)
            with mock.patch(STRIKE) as hit:
                self.fly([p], DT)
            self.assertEqual(near in victims(hit), reached, level)


class HomesickTest(_Main):
    def test_homing(self):
        for level, bends in ((3, True), (0, False)):
            s, h = self.setup("homeward_fury", level)
            off = self.place(foe(26.0, 22.3, BASE))[0]
            p = self.shot(x=31.0)
            p.returning = True
            with mock.patch(STRIKE) as hit:
                self.fly([p], 0.6)
            self.assertEqual(off in victims(hit), bends, level)
            self.assertFalse(p.alive)                     # (caught all the same)

    def test_welcome_home(self):
        s, h = self.setup("homeward_fury", 6)
        for _ in range(5):
            p = self.shot(x=h.x + 0.5)
            p.returning = True
            self.fly([p], DT)
        _, seconds, most = config.WELCOME_HOME
        self.assertEqual(len(h.welcome), most)
        self.assertAlmostEqual(s.rules.weapon_dt(s.me, 1.0), 1 + config.WELCOME_HOME[0] * most)
        s.rules.tick(s.me, seconds + 0.1)
        self.assertEqual(h.welcome, [])

    def test_hearth(self):
        s, h = self.setup("homeward_fury", 9)
        a = self.place(foe(24.0, 20.5, BASE))[0]
        for returning in (True, False):
            p = self.shot()
            p.returning = returning
            with mock.patch(STRIKE) as hit:
                self.hit(p, a)
            self.assertEqual(hit.call_args.kwargs["sure_crit"], returning)


class ChainlinkTest(_Main):
    def test_taut(self):
        for x, share in ((20.5 + 10.0, config.TAUT[1]), (23.0, config.TETHER[2])):
            s, h = self.setup("tether", 3)
            self.place(foe(22.0, 20.5, BASE))
            p = self.shot(x=x)
            p.max_range = 11.0
            with mock.patch(STRIKE) as hit:
                combat._tether(p, s._actors(), s.effects, DT, s.world)
            self.assertAlmostEqual(hit.call_args.args[1], p.damage * share)

    def test_shackle(self):
        s, h = self.setup("tether", 6)
        a, b = self.place(movable(22.0, 20.5), movable(23.0, 20.6))
        p = self.shot(x=24.0)
        with mock.patch(STRIKE):
            combat._tether(p, s._actors(), s.effects, DT, s.world)
        self.assertIs(p.shackle[0], a)                    # (the first one cut)
        p.x += 1.0
        combat._tether(p, s._actors(), s.effects, DT, s.world)
        self.assertAlmostEqual(a.x, 23.0)
        self.assertAlmostEqual(b.x, 23.0)                 # (the other isn't dragged)
        h.time += config.SHACKLE + 0.1
        p.x += 1.0
        combat._tether(p, s._actors(), s.effects, DT, s.world)
        self.assertAlmostEqual(a.x, 23.0)

    def test_flail(self):
        s, h = self.setup("tether", 9)
        on_circle = self.place(foe(20.5, 20.5 + 6.0, BASE))[0]
        p = self.shot(x=20.5 + 6.0)
        combat._end_throw(p, [])
        self.assertAlmostEqual(p.flail, math.tau)
        with mock.patch(STRIKE) as hit:
            for _ in range(240):
                combat.update_projectiles([p], s.world, s.effects, DT, s._actors(), s.zones)
                if p.returning:
                    break
        self.assertTrue(p.returning)
        self.assertIn(on_circle, victims(hit))
        s, h = self.setup("tether", 6)
        p = self.shot(x=20.5 + 6.0)
        combat._end_throw(p, [])
        self.assertTrue(p.returning)


class WhirlwindTest(_Main):
    def test_spin_cycle(self):
        for level, want in ((3, "tough"), (0, "near")):
            s, h = self.setup("cyclone", level)
            near, tough = self.place(foe(23.0, 20.5, 100.0), foe(20.5, 26.0, BASE))
            spawned = []
            combat._cyclone(self.shot(), h, s._actors(), spawned, h.stats)
            t = tough if want == "tough" else near
            self.assertAlmostEqual(spawned[0].angle, math.atan2(t.y - h.y, t.x - h.x))

    def test_gale_force(self):
        for level, again in ((6, 1), (3, 0)):
            s, h = self.setup("cyclone", level)
            self.place(foe(24.0, 20.5, BASE))
            p = self.shot(x=h.x + 0.5)
            p.returning, p.child, p.spins = True, True, 1     # (a rethrown axe)
            spawned = []
            combat._fly_back(p, combat.ActorGrid([]), s.world, s.effects, DT, s._actors(),
                             spawned)
            self.assertEqual(len(spawned), again, level)

    def test_eye_of_the_cyclone(self):
        s, h = self.setup("cyclone", 9)
        a, b = self.place(foe(23.0, 20.5, 300.0), foe(20.5, 25.0, 200.0))
        spawned = []
        combat._cyclone(self.shot(), h, s._actors(), spawned, h.stats)
        self.assertEqual(len(spawned), 2)
        self.assertAlmostEqual(spawned[1].angle, math.atan2(b.y - h.y, b.x - h.x))
        self.assertEqual([c.spins for c in spawned], [1, 99])


class DoublebitTest(_Main):
    def split(self, level):
        s, h = self.setup("splitting_axe", level)
        p = self.shot(x=31.5, damage=100.0)
        spawned = []
        combat._turn_back(p, spawned)
        return s, h, spawned

    def test_reunite(self):
        s, h, pieces = self.split(3)
        self.fly(pieces, 0.4)
        alive = [q for q in pieces if q.alive]
        self.assertEqual(len(alive), 1)
        self.assertTrue(alive[0].reunited)
        self.assertAlmostEqual(alive[0].damage, 100.0 * config.SPLITTING_AXE[0] * 2)
        self.assertAlmostEqual(combat._axe_bonus(alive[0], h.stats), config.REUNITE[1])
        s, h, pieces = self.split(2)
        self.fly(pieces, 0.4)
        self.assertEqual(len([q for q in pieces if q.alive]), 2)

    def test_crossing(self):
        s, h, pieces = self.split(6)
        a, b = pieces
        self.assertAlmostEqual(abs(a.y - b.y), config.CROSSING)
        for q in pieces:
            q.pieces = None                               # (no Reunite: watch them cross)
        side = a.y < h.y
        crossed = False
        for _ in range(30):
            self.fly(pieces, DT)
            if a.alive and abs(a.y - h.y) > 0.3 and (a.y < h.y) != side:
                crossed = True
        self.assertTrue(crossed)
        s, h, pieces = self.split(6)                      # (with Reunite they fuse crossing)
        self.fly(pieces, 0.3)
        self.assertEqual(len([q for q in pieces if q.alive]), 1)

    def test_quartering(self):
        s, h, pieces = self.split(9)
        n, share = config.QUARTERING
        self.assertEqual(len(pieces), n)
        for q in pieces:
            self.assertAlmostEqual(q.damage, 100.0 * share)
        self.assertEqual([q.child for q in pieces], [False, True, True, True])


class CloudburstTest(_Main):
    def rain(self, level, aim=(30.0, 20.5), hold=0.0):
        s, h = self.setup("arrow_rain", level)
        h.aim_point = aim
        return s, h

    def test_monsoon(self):
        for level, centre in ((3, (27.0, 25.0)), (0, (30.0, 20.5))):
            s, h = self.rain(level)
            self.place(foe(27.0, 25.0, BASE))
            s.rules._arrow_rain(h, {"mult": 1.0})
            for q in s.projectiles:
                self.assertLessEqual(math.hypot(q.target[0] - centre[0], q.target[1] - centre[1]),
                                     config.ARROW_RAIN[2] + 1e-6, level)

    def test_thunder_rain(self):
        for level, mult in ((6, 1 + config.THUNDER_RAIN[1] * (config.ARROW_RAIN[1] - 1)),
                            (3, 1.0)):
            s, h = self.rain(level)                       # (rng 0.99: all land on one spot)
            s.rules._arrow_rain(h, {"mult": 1.0})
            self.assertEqual(len(s.projectiles), config.ARROW_RAIN[1])
            for q in s.projectiles:
                self.assertAlmostEqual(q.mult, mult, msg=level)

    def test_squall_line(self):
        for level, rains in ((9, 2), (6, 1)):
            s, h = self.rain(level)
            h.attacks = config.ARROW_RAIN[0] - 1
            s._attack(s.me)
            rain = [q for q in s.projectiles if q.spec.look == "rain_arrow"]
            self.assertEqual(len(rain), config.ARROW_RAIN[1] * rains, level)
            held = [q for q in rain if q.hold > 0]
            self.assertEqual(len(held), config.ARROW_RAIN[1] * (rains - 1))
            x0 = held[0].x if held else None
            self.fly(held, config.SQUALL_LINE * 0.9)
            if held:
                self.assertEqual(held[0].x, x0)           # (still waiting)


class BroadleafTest(_Main):
    def test_gathering_speed(self):
        s, h = self.setup("broadhead", 3)
        self.place(foe(24.0, 20.5, BASE), foe(27.0, 20.5, BASE))
        p = self.shot()
        with mock.patch(STRIKE):
            self.fly([p], 0.2)
        self.assertAlmostEqual(p.pace, config.GATHERING_SPEED ** 2)

    def test_run_through(self):
        for level, back in ((6, True), (3, False)):
            s, h = self.setup("broadhead", level)
            line = self.place(*(foe(23.0 + 2 * i, 20.5, BASE) for i in range(5)))
            p = self.shot()
            p.pierce_left = 4
            with mock.patch(STRIKE) as hit:
                self.fly([p], 1.5)
            got = victims(hit)
            self.assertEqual(got[:5], list(line))
            self.assertEqual(len(got) > 5, back, level)
            if back:                                      # (back through them, last first)
                self.assertEqual(got[5:], list(reversed(line[:4])))

    def test_broadside(self):
        for level, per in ((9, 2), (6, 1)):
            s, h = self.setup("broadhead", level)
            a = self.place(foe(24.0, 20.5, BASE))[0]
            p = self.shot()
            p.hit = {1, 2}
            with mock.patch(STRIKE) as hit:
                self.hit(p, a)
            self.assertAlmostEqual(hit.call_args.kwargs["extra"], h.stats.broadhead * 2 * per)


class BloodhoundTest(_Main):
    def remark(self):
        self.s.me.mark_timer = 0.0
        self.s._hunters_mark(self.s.me, DT)

    def test_old_scent(self):
        for level, kept in ((3, True), (0, False)):
            s, h = self.setup("hunters_mark", level)
            old = self.place(foe(24.0, 20.5, 500.0))[0]
            h.marked = old
            tough = self.place(foe(26.0, 22.0, 900.0))[0]
            self.remark()
            self.assertIs(h.marked, tough)
            self.assertEqual(combat.marked(h, old), kept, level)
            h.time += config.OLD_SCENT + 0.1
            self.assertFalse(combat.marked(h, old))

    def test_next_quarry(self):
        for level, want in ((6, "near"), (3, "tough")):
            s, h = self.setup("hunters_mark", level)
            gone = dead(self.place(foe(28.0, 20.5, 500.0))[0])
            near, tough = self.place(foe(29.0, 21.0, 100.0), foe(16.0, 20.5, 900.0))
            h.marked = gone
            s.me.mark_timer = 3.0                         # (it fell before its time was up)
            s._hunters_mark(s.me, DT)
            self.assertIs(h.marked, near if want == "near" else tough, level)

    def test_pack_hunt(self):
        for level, packed in ((9, True), (6, False)):
            s, h = self.setup("hunters_mark", level)
            gone = dead(self.place(foe(28.0, 20.5, 500.0))[0])
            pack = self.place(foe(29.5, 21.0), foe(27.0, 22.0))
            far = self.place(foe(16.0, 20.5))[0]
            h.marked = gone
            self.remark()
            for a in pack:
                if a is not h.marked:                     # (Next quarry's new mark is one)
                    self.assertEqual(combat.marked(h, a), packed, level)
            self.assertFalse(combat.marked(h, far) and h.marked is not far)
            h.time += config.PACK_HUNT[1] + 0.1
            others = [a for a in pack if a is not h.marked]
            self.assertFalse(any(combat.marked(h, a) for a in others))


class StillwaterTest(_Main):
    def test_held_breath(self):
        for level, breath, pace in ((3, 1.5, config.HELD_BREATH[1]), (3, 0.5, 1.0),
                                    (0, 1.5, 1.0)):
            s, h = self.setup("steady_aim", level)
            h.breath = breath
            p = self.shot()
            s.rules.bow_shots(s.me, [p])
            self.assertEqual(p.pace, pace, (level, breath))
        self.assertEqual(h.breath, 1.5)                   # (level 0: kept, not used)

    def test_zen(self):
        dealt = {}
        for level, still in ((6, 2.5), (6, 0.0), (3, 2.5)):
            s, h = self.setup("steady_aim", level)
            h.still_t = still
            a = foe(24.0, 20.5, 10 ** 6)
            dealt[(level, still)] = combat.strike(a, 10.0, h, 0.0, [], sure_crit=True)
        crit = h.stats.crit_damage
        self.assertAlmostEqual(dealt[(6, 2.5)] / dealt[(6, 0.0)], (crit + config.ZEN[1]) / crit)
        self.assertAlmostEqual(dealt[(3, 2.5)], dealt[(6, 0.0)])

    def test_still_waters(self):
        for level, holds in ((9, True), (6, False)):
            s, h = self.setup("steady_aim", level)
            h.vx = 5.0
            h.calm = h.time - 0.5
            self.assertEqual(combat.steady(h), holds, level)
            h.calm = h.time - config.STILL_WATERS - 0.1
            self.assertFalse(combat.steady(h))
            s.rules.tick(s.me, DT)                        # (moving: calm stays where it was)
            self.assertLess(h.calm, h.time - 1.0)


class FarsightTest(_Main):
    def test_follow_through(self):
        for level, ready in ((3, True), (0, False)):
            s, h = self.setup("deadeye", level)
            h.weapon.cooldown = 0.3
            p = self.shot()
            p.deadeye = True
            for _ in range(config.FOLLOW_THROUGH):
                combat._passing(p, None)
            self.assertEqual(h.weapon.cooldown <= 0, ready, level)

    def test_second_sight(self):
        s, h = self.setup("deadeye", 6)
        sure = []
        for _ in range(config.SECOND_SIGHT * 2):
            sure.append(s.rules.attack_mods(s.me).get("sure_crit", False))
        every = config.SECOND_SIGHT
        self.assertEqual(sure, [(i + 1) % every == 0 for i in range(every * 2)])

    def test_lightning_arrow(self):
        s, h = self.setup("deadeye", 9)
        p = self.shot()
        s.rules.bow_shots(s.me, [p])                      # (rng 0.99: no crit)
        self.assertEqual((p.sure_crit, p.crit_x, p.pace), (False, 0.0, 1.0))
        h.rng.random = lambda: 0.0
        p = self.shot()
        s.rules.bow_shots(s.me, [p])
        self.assertTrue(p.sure_crit)
        self.assertEqual(p.pace, config.LIGHTNING_ARROW)
        a = self.place(foe(40.0, 20.5, BASE))[0]
        with mock.patch(STRIKE) as hit:
            self.fly([p], DT)                             # (20 tiles in one step)
        self.assertEqual(victims(hit), [a])


class SplitbranchTest(_Main):
    def split(self, level, *foes, zones=None):
        s, h = self.setup("split_arrow", level)
        self.place(*foes)
        p = self.shot(x=24.0)
        victim = foe(24.0, 20.5, BASE)
        spawned = []
        combat._split_arrow(p, victim, 24.0, 20.5, h.stats, spawned, s._actors(), zones)
        return s, h, spawned

    def test_canopy(self):
        a, b = foe(24.0, 25.0, BASE), foe(28.0, 17.0, BASE)
        s, h, spawned = self.split(3, a, b)
        angles = sorted(round(c.angle, 6) for c in spawned[:2])
        want = sorted(round(math.atan2(t.y - 20.5, t.x - 24.0), 6) for t in (a, b))
        self.assertEqual(angles, want)
        s, h, spawned = self.split(0, foe(24.0, 25.0, BASE))
        self.assertAlmostEqual(spawned[len(spawned) // 2].angle, 0.0)   # (the fan)

    def test_bough(self):
        for level, splits in ((6, True), (3, False)):
            s, h = self.setup("split_arrow", level, walls=[(26, y) for y in range(15, 26)])
            p = self.shot()
            shots = [p]
            self.fly(shots, 0.3)
            kids = [q for q in shots if q.child]
            self.assertEqual(bool(kids), splits, level)
            for q in kids:
                self.assertLess(q.dir_x, 0)               # (turned off the wall)

    def test_seed_storm(self):
        zones = []
        s, h, spawned = self.split(9, zones=zones)
        n, life, radius, dps, throw = config.SEED_STORM
        self.assertEqual([z.kind for z in zones], ["thorns"] * n)
        z = zones[0]
        a = self.place(foe(z.x, z.y, BASE))[0]
        with mock.patch("ascii_adventurers.systems.zones.strike", create=True) as hit, \
                mock.patch(STRIKE) as hit2:
            for _ in range(60):
                update_zones(zones, s._actors(), s.effects, DT, s.world)
        total = sum(c.args[1] for c in hit2.call_args_list if c.args[0] is a)
        self.assertAlmostEqual(total, dps, delta=dps * 0.51)
        zones = []
        self.split(6, zones=zones)
        self.assertEqual(zones, [])


if __name__ == "__main__":
    unittest.main()
