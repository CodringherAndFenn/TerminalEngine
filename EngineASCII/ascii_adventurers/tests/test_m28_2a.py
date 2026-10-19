"""M28.2a: the off-hand's +3 / +6 / +9 tricks (design/GEAR.md 17.1)."""

import math
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from ascii_adventurers import config
from ascii_adventurers.entities.projectile import Projectile
from ascii_adventurers.players import gear
from ascii_adventurers.players.gear import Offer
from ascii_adventurers.systems import combat
from ascii_adventurers.tests.test_m16 import fly, game
from ascii_adventurers.tests.test_weapons import Dummy, open_map


def wear(s, key, level, rarity=None, player=None):
    p = player or s.me
    p.progress.gear.take(Offer(key, rarity or config.CARDS[key].rarity, (), "new"))
    p.progress.gear.worn[p.progress.gear.wearing(key)].level = level
    s._apply_loadout(p)


def foe(x, y, hp=500):
    """A Dummy that can stand in the scene's enemy list."""
    d = Dummy(x, y, hp)
    d.hear = lambda *a: None
    return d


def mine(s):
    return [q for q in s.projectiles if q.owner is s.hero]


def degrees(shots):
    return sorted(round(math.degrees(q.angle)) % 360 for q in shots)


class _Case(unittest.TestCase):
    def setup(self, hero, key, level):
        m, s = game(hero)
        wear(s, key, level)
        s.enemies.clear()
        s.hero.aim_angle = 0.0
        s.projectiles.clear()
        self.s = s
        return s

    def tearDown(self):
        if pygame.display.get_init():
            pygame.mouse.set_visible(True)

    def attack(self, times=1, clear=True):
        s = self.s
        if clear:
            s.projectiles.clear()
        for _ in range(times):
            s._attack(s.me)
        return mine(s)


class FrameworkTest(unittest.TestCase):
    def test_flags_come_at_their_levels(self):
        for lv, want in ((2, []), (3, ["cross_fire+3"]), (6, ["cross_fire+3", "cross_fire+6"]),
                         (9, ["cross_fire+3", "cross_fire+6", "cross_fire+9"])):
            self.assertEqual([f for f, _, _ in gear.trick_flags("cross_fire", lv)], want)
        self.assertEqual(gear.trick_flags("no_such_piece", 9), [])   # (no tricks: no flags)

    def test_every_offhand_piece_has_three_tricks(self):
        # (M28.2b added the head: tests/test_m28_2b.py checks the slots built so far.)
        offhand = [k for k, g in config.GEAR.items() if g.slot == "off"]
        self.assertTrue(set(offhand) <= set(config.GEAR_TRICKS))
        for key in offhand:
            self.assertEqual([t for t, _, _ in gear.tricks(key)], [3, 6, 9])
            for _, name, text in gear.tricks(key):
                self.assertTrue(name and text and text.isascii(), key)

    def test_the_next_plus_one_names_its_trick(self):
        self.assertIn("NEEDLE", gear.next_level_text("cross_fire", 2))
        self.assertNotIn("NEEDLE", gear.next_level_text("cross_fire", 3))
        self.assertEqual(gear.next_trick("cross_fire", 3)[1], "North star")
        self.assertIsNone(gear.next_trick("cross_fire", 9))

    def test_downsides_go_at_nine(self):
        for key in ("frenzy", "spray_and_pray"):
            ranges = lambda lv: [v for st, op, v in gear.power_steps(key, lv) if st == "range"]
            self.assertTrue(ranges(8), key)
            self.assertEqual(ranges(9), [], key)

    def test_the_gear_screen_shows_the_tricks(self):
        from ascii_adventurers.ui.gear_screen import piece_lines
        lines = [t for t, _ in piece_lines("cross_fire", "uncommon", 4, (), 30, full=True)]
        text = " ".join(lines)
        self.assertIn("+3 NEEDLE", text)
        self.assertIn("at +6: North star", text)
        short = " ".join(t for t, _ in piece_lines("cross_fire", "uncommon", 6, (), 30))
        self.assertIn("+3 Needle, +6 North star", short)


class CompassOrbTest(_Case):
    def test_needle_turns_every_other_cross(self):
        self.setup("huntress", "cross_fire", 3)
        every = config.CROSS_FIRE_EVERY
        first = self.attack(every)
        second = self.attack(every)
        self.assertEqual(degrees(first), [0, 0, 0, 0, 90, 180, 270])
        self.assertEqual(degrees(second), [0, 0, 0, 0, 135, 225, 315])

    def test_north_star_cuts_an_enemy_shot(self):
        s = self.setup("huntress", "cross_fire", 6)
        shots = self.attack(config.CROSS_FIRE_EVERY)
        up = next(q for q in shots if round(math.degrees(q.angle)) % 360 == 90)
        self.assertTrue(up.cancels)
        shooter = foe(s.hero.x + 20, s.hero.y)
        bad = Projectile(up.x, up.y + 3.0, -math.pi / 2, config.SPELL_SHELLS["note"], owner=shooter)
        group = [up, bad]
        fly(group, [], s.world, steps=30)
        self.assertNotIn(bad, group)                     # destroyed
        self.assertFalse(up.cancels)                     # only the first one

    def test_cardinal_every_second_attack(self):
        self.setup("huntress", "cross_fire", 9)
        self.assertEqual(len(self.attack(config.CARDINAL_EVERY)), config.CARDINAL_EVERY + 3)


class SunwheelTest(_Case):
    def test_the_meter_keeps_the_old_rhythm(self):
        self.setup("huntress", "starburst", 0)
        every, rays = config.STARBURST
        self.assertEqual(len(self.attack(every)), every + rays)

    def test_pinwheel_curves(self):
        self.setup("huntress", "starburst", 3)
        shots = self.attack(config.STARBURST[0])
        ring = [q for q in shots if q.curve]
        self.assertEqual(len(ring), config.STARBURST[1])

    def test_pain_turns_the_wheel(self):
        s = self.setup("huntress", "starburst", 6)
        s.me.hits_seen = s.hero.hits_taken
        before = s.me.burst_meter
        s.hero.take_damage(1, Dummy(s.hero.x + 2, s.hero.y), 0.0)
        s.rules.tick(s.me, 1 / 60)
        self.assertEqual(s.me.burst_meter, before + config.PAIN_WHEEL)

    def test_corona_second_ring(self):
        s = self.setup("huntress", "starburst", 9)
        every, rays = config.STARBURST
        self.attack(every)
        self.assertIsNotNone(s.me.corona)
        s.projectiles.clear()
        for _ in range(round(config.CORONA * 60) + 2):
            s.rules.tick(s.me, 1 / 60)
        ring = mine(s)
        self.assertEqual(len(ring), rays)
        step = 360 / rays
        self.assertAlmostEqual(degrees(ring)[0] % step, step / 2, delta=1)


class HindsightOrbTest(_Case):
    def test_over_the_shoulder(self):
        s = self.setup("huntress", "rear_guard", 3)
        s.enemies.append(foe(s.hero.x - 6, s.hero.y + 3))
        shots = self.attack()
        back = [q for q in shots if math.cos(q.angle) < 0]
        self.assertEqual(len(back), 1)
        self.assertAlmostEqual(back[0].angle % math.tau, math.atan2(3, -6) % math.tau, delta=0.05)

    def test_watchful(self):
        s = self.setup("huntress", "rear_guard", 6)
        s.enemies.append(foe(s.hero.x - 1.5, s.hero.y))
        s.rules.tick(s.me, 1 / 60)
        self.assertEqual(len(mine(s)), 1)                 # shot at once
        s.rules.tick(s.me, 1 / 60)
        self.assertEqual(len(mine(s)), 1)                 # then waits
        self.assertGreater(s.me.watch_cd, 0)

    def test_eyes_in_the_back(self):
        s = self.setup("princess", "rear_guard", 9)
        shots = self.attack()
        back = [q for q in shots if math.cos(q.angle) < -0.5]
        self.assertEqual(len(back), s.hero.weapon.spec.pellets)
        self.assertTrue(all(q.mult == 1.0 for q in back))


class NautilusShellTest(_Case):
    def test_growing_shell(self):
        s = self.setup("huntress", "spiral", 3)
        shots = self.attack()
        grown = [q for q in shots if q.grow]
        self.assertEqual(len(grown), 1)
        shell = s.hero.weapon.spec.shell
        far = shell.max_range * 0.95
        dealt = []
        for grow in (False, True):
            q = Projectile(0.5, 5.5, 0.0, shell, owner=s.hero)
            q.grow = grow
            d = Dummy(0.5 + far, 5.5, 5000)
            s.hero.rng = random.Random(4)
            fly([q], [d], open_map(80, 12), steps=120)
            dealt.append(5000 - d.hp)
        self.assertGreater(dealt[1], dealt[0] * 1.2)

    def test_double_helix(self):
        self.setup("huntress", "spiral", 6)
        extra = [q.angle for q in self.attack() if abs(q.angle) > 1e-6]
        self.assertEqual(len(extra), 2)
        self.assertAlmostEqual(extra[0], -extra[1])

    def test_golden_angle_and_more_shots(self):
        s = self.setup("huntress", "spiral", 9)
        for k in range(6):
            s.enemies.append(foe(s.hero.x + 3, s.hero.y - 3 + k))
        extra = [q for q in self.attack() if abs(q.angle) > 1e-6]
        self.assertEqual(len(extra), 2 * (1 + 2))         # 6 enemies: +2 (6 // 3), each mirrored (+6)
        self.assertEqual(s.hero.spiral, 3)


class TwinnedQuiverTest(_Case):
    def test_linked(self):
        s = self.setup("huntress", "twin_lanes", 3)
        shots = self.attack()
        gap = config.TWIN_LANES[0]
        a, b = Dummy(s.hero.x + 4, s.hero.y - gap / 2, 5000), Dummy(s.hero.x + 4, s.hero.y + gap / 2, 5000)
        a.hit_radius = b.hit_radius = 0.2
        fly(shots, [a, b], s.world, steps=40)
        self.assertIs(a.link[0], b)
        hp = b.hp
        dealt = combat.strike(a, 100, s.hero, None, [], can_crit=False, on_hit=False)
        self.assertAlmostEqual(hp - b.hp, dealt * config.LINKED[1], delta=0.01)
        s.hero.time += config.LINKED[0] + 0.1                  # the link runs out
        hp = b.hp
        combat.strike(a, 100, s.hero, None, [], can_crit=False, on_hit=False)
        self.assertEqual(b.hp, hp)

    def test_drift_apart(self):
        s = self.setup("huntress", "twin_lanes", 6)
        shots = self.attack()
        twins = list(shots)
        last = {}
        for _ in range(200):
            combat.update_projectiles(shots, s.world, [], 1 / 60, [])
            for q in twins:
                if q.alive:
                    last[id(q)] = q.y
        ys = sorted(last.values())
        self.assertAlmostEqual(ys[1] - ys[0], config.DRIFT_APART, delta=0.15)

    def test_triplets(self):
        self.setup("huntress", "twin_lanes", 9)
        self.assertEqual(len(self.attack()), 3)


class CanyonHornTest(_Case):
    def test_reverb_goes_at_another_enemy(self):
        s = self.setup("huntress", "echo", 3)
        aimed = foe(s.hero.x + 6, s.hero.y)
        other = foe(s.hero.x, s.hero.y + 4)
        s.enemies += [aimed, other]
        s.hero.aim_point = (aimed.x, aimed.y)
        kw = s.rules.attack_mods(s.me, echo=True)
        self.assertAlmostEqual(s.hero.aim_angle + kw["angle_offset"], math.pi / 2, delta=0.01)

    def test_rolling_echo(self):
        s = self.setup("huntress", "echo", 6)
        e = Dummy(s.hero.x + 3, s.hero.y)
        e.echo_kill = True
        e.espec = config.ENEMIES["goblin_archer"]
        count = s.me.echo_count
        s.rules.on_kill(s.me, e)
        self.assertEqual(s.me.echo_count, count + 1)

    def test_canyon_three_times(self):
        s = self.setup("huntress", "echo", 9)
        self.attack(config.ECHO_EVERY)
        self.assertEqual(s.me.echo_stage, 1)
        fired = []
        orig = s._attack
        s._attack = lambda p, echo=False: (fired.append(p.echo_mult), orig(p, echo))
        for _ in range(60):
            s.rules.tick(s.me, 1 / 60)
        self.assertEqual(fired, [1.0, config.ECHO_THIRD])
        self.assertEqual(s.me.echo_stage, 0)


class WarDrumTest(_Case):
    def kill(self, s):
        e = Dummy(s.hero.x + 2, s.hero.y)
        e.espec = config.ENEMIES["goblin_archer"]
        s.rules.on_kill(s.me, e)

    def test_drumroll(self):
        s = self.setup("huntress", "frenzy", 3)
        self.kill(s)
        self.assertEqual(s.me.frenzy, config.FRENZY_TIME)
        self.kill(s)
        self.assertEqual(s.me.frenzy, config.FRENZY_TIME + config.DRUMROLL[0])
        for _ in range(10):
            self.kill(s)
        self.assertEqual(s.me.frenzy, config.DRUMROLL[1])

    def test_unshaken(self):
        s = self.setup("huntress", "frenzy", 6)
        self.kill(s)
        s.rules.tick(s.me, 1 / 60)
        self.assertTrue(s.hero.unshaken)
        s.hero.slowed(0.0, 2.0)                           # rooted
        x = s.hero.x
        for _ in range(20):
            s.hero.move(1, 0, 1 / 60, s.world)
        self.assertGreater(s.hero.x, x)

    def test_war_dance(self):
        from ascii_adventurers.systems.statuses import statuses_of
        s = self.setup("huntress", "frenzy", 9)
        near, boss = foe(s.hero.x + 2, s.hero.y), foe(s.hero.x - 2, s.hero.y)
        boss.boss = True
        s.enemies += [near, boss]
        self.assertEqual(s.hero.stats.range, 0.0)         # the -20% is gone
        self.kill(s)
        self.assertGreater(statuses_of(near).dazed, 0)
        self.assertEqual(statuses_of(near).time_scale, 0.0)
        self.assertIsNone(boss.status)                    # bosses aren't dazed


class PepperboxTest(_Case):
    def test_second_barrel(self):
        s = self.setup("huntress", "spray_and_pray", 3)
        shots = self.attack()
        seen = []
        for _ in range(200):
            combat.update_projectiles(shots, s.world, [], 1 / 60, [])
            seen += [q for q in shots if q not in seen]
        self.assertEqual(sum(1 for q in seen if q.gen == 2), 4)

    def test_powder_flash(self):
        s = self.setup("huntress", "spray_and_pray", 6)
        rng = s.hero.weapon.spec.shell.max_range
        shots = self.attack()
        d = Dummy(shots[0].x + rng / 2, shots[0].y + 0.8, 5000)
        fly(shots, [d], s.world, steps=200)
        self.assertLess(d.hp, 5000)

    def test_buckshot(self):
        s = self.setup("huntress", "spray_and_pray", 9)
        self.assertEqual(s.hero.stats.range, 0.0)          # the -25% is gone
        shell = s.hero.weapon.spec.shell
        fam = {}
        hits = []
        target = Dummy(3.5, 5.5, 5000)
        s.hero.rng = random.Random(1)
        s.hero.stats.crit_chance = 0.0
        for k in range(2):
            q = Projectile(0.5, 5.5, 0.0, shell, owner=s.hero)
            q.family = fam
            hp = target.hp
            fly([q], [target], open_map(40, 12), steps=60)
            hits.append(hp - target.hp)
        self.assertAlmostEqual(hits[1], hits[0] * (1 + config.BUCKSHOT), delta=0.01)


if __name__ == "__main__":
    unittest.main()
