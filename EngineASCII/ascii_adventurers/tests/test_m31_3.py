"""M31.3: Pangaea's middle ring and heart (design/OCEAN.md 24, 26): the
dinosaurs (raptors, the Tyrant, club-tails, pterosaurs), the giant insects
and the earliest life (dragonflies, bombardier beetles, ant mounds and their
ants, sea scorpions in the pools), nests (hatchlings and the parent) and
amber (what's frozen in it)."""

import math
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.ai import KINDS
from ascii_adventurers.ai.pangaea import Beast, GiantAnt, Hatchling, residents
from ascii_adventurers.render import pangaea_art  # noqa: F401
from ascii_adventurers.render.characters import ART
from ascii_adventurers.systems import pangaea as land_sys
from ascii_adventurers.systems.spawner import Spawner
from ascii_adventurers.tests.test_m31_2 import DT, arena, ctx_of, run, still, until
from ascii_adventurers.tests.test_p7 import enemy
from ascii_adventurers.world import tiles
from ascii_adventurers.world.tiles import Damage
from ascii_adventurers.world.chunked import ChunkedWorld
from ascii_adventurers.world.test_map import TestMap
from ascii_adventurers.world.zones import plan_of

MIDDLE = ("raptor", "tyrant", "club_tail", "pterosaur")
HEART = ("dragonfly", "bombardier_beetle", "ant_mound")
OTHERS = ("giant_ant", "sea_scorpion", "hatchling")


def ash_map(w=60, h=30, pool=None, patches=()):
    """Ash, a steaming pool (x, y, r) and `patches` {(x, y): tile}."""
    rows = [["."] * w for _ in range(h)]
    legend = {".": tiles.ASH, "~": tiles.HOT_SPRING}
    if pool:
        px, py, r = pool
        for y in range(h):
            for x in range(w):
                if math.hypot(x + 0.5 - px, y + 0.5 - py) <= r:
                    rows[y][x] = "~"
    for k, ((x, y), tile) in enumerate(dict(patches).items()):
        ch = chr(ord("A") + k % 26)
        rows[y][x] = ch
        legend[ch] = tile
    return TestMap(["".join(r) for r in rows], legend=legend)


class _P:
    def __init__(self, hero):
        self.hero, self.alive, self.index = hero, True, 0


class _BreakScene:
    """What systems/pangaea.breaks looks at."""

    def __init__(self, a):
        self.a, self.world, self.effects = a, a.world, a.effects
        self.gems, self.zones, self._sounds = [], a.zones, []
        self.players = [_P(a.hero)]
        self.spawner = None

    @property
    def enemies(self):
        return self.a.enemies


def angle_off(a, b):
    return abs((a - b + math.pi) % math.tau - math.pi)


class CatalogTest(unittest.TestCase):
    def test_eight_more_each_on_its_ring_with_its_picture_and_page(self):
        for key in MIDDLE + HEART + OTHERS:
            spec = config.ENEMIES[key]
            self.assertIn(spec.kind, KINDS)
            self.assertTrue(issubclass(KINDS[spec.kind], Beast), key)
            self.assertIn(key, config.BESTIARY)
            self.assertIn(spec.sprite, ART)
            self.assertEqual(len(ART[spec.sprite]), 18)
            self.assertTrue(all(len(r) == 14 for r in ART[spec.sprite]), key)
        for key in MIDDLE:
            self.assertEqual((config.ENEMIES[key].biomes, config.PANGAEA_RING_OF[key]), (("pangaea",), 1))
        for key in HEART:
            self.assertEqual((config.ENEMIES[key].biomes, config.PANGAEA_RING_OF[key]), (("pangaea",), 0))
        for key in OTHERS:                                   # (sent out, hatched or living in the pools)
            self.assertEqual(config.ENEMIES[key].biomes, ())
        for name in ("raptor_leap", "tyrant_roar", "pterosaur_swoop"):
            self.assertIn(name, ART)
        self.assertEqual({k for k in MIDDLE + HEART + OTHERS if config.ENEMIES[k].elite},
                         {"tyrant", "sea_scorpion"})


class DinosaurTest(unittest.TestCase):
    def test_raptors_take_turns_leaping_from_behind_you(self):
        pack = [enemy("raptor", 20.5 + k * 2, 8.5, seed=k) for k in range(4)]
        a = arena(*pack, hero_at=(30.5, 15.5))
        a.hero.aim_angle = 0.0                                # (looking east: behind is west)
        busy, starts = [], []

        def watch():
            busy.append(sum(1 for r in pack if r.state in ("set", "crouch", "leap")))
            for r in pack:
                if r.state == "leap" and r.ran == 0.0:
                    starts.append(r.run_from)
        run(a, 10.0, watch)
        self.assertLessEqual(max(busy), 1)                    # (one at a time)
        self.assertGreaterEqual(len(starts), 2)
        behind = sum(1 for x, _ in starts if x < a.hero.x)
        self.assertGreater(behind, len(starts) / 2)
        self.assertTrue(any(ech.kind == "run" for r in pack for ech in r.echoes)
                        or any(r.runners for r in pack))

    def test_the_tyrants_roar_roots_you_unless_you_roll(self):
        t = enemy("tyrant", 20.5, 15.5)
        t.facing, t.cooldown = 0.0, 99.0
        a = arena(t, hero_at=(27.5, 15.5))
        t.roar_cd = 0.0
        self.assertTrue(until(a, lambda: t.state == "roar"))
        run(a, config.TYRANT[2] + DT)
        self.assertEqual(a.hero.slow_mult, 0.0)
        self.assertIn("FEAR!", [fx.label for fx in a.effects if fx.kind == "toast"])
        a.hero.slow_t = 0.0
        t.roar_cd, t.state = 0.0, "roam"
        a.hero.roll_t = 5.0                                   # (mid-roll: it can't touch you)
        self.assertTrue(until(a, lambda: t.state == "roar"))
        run(a, config.TYRANT[2] + DT)
        self.assertGreater(a.hero.slow_mult if a.hero.slow_t > 0 else 1.0, 0.0)

    def test_the_tyrant_sweeps_its_tail_at_whats_behind_it(self):
        t = enemy("tyrant", 20.5, 15.5)
        t.facing, t.roar_cd, t.cooldown = 0.0, 99.0, 0.0
        t.turn_to = lambda want, rate, dt: False              # (it can't turn round in time)
        a = arena(t, hero_at=(17.5, 15.5))
        hp = a.hero.hp
        self.assertTrue(until(a, lambda: t.state == "tail"))
        run(a, config.TYRANT[11] + DT)
        self.assertLess(a.hero.hp, hp)
        self.assertLess(a.hero.x, 17.5 - config.TYRANT[10] * 0.5)   # (thrown)

    def test_the_tyrant_turns_slowly_and_the_ground_shakes_harmlessly(self):
        t = enemy("tyrant", 10.5, 15.5)
        t.facing, t.roar_cd, t.cooldown = math.pi, 99.0, 99.0
        a = arena(t, hero_at=(40.5, 15.5))
        facings, slows = [], []

        def watch():
            facings.append(t.facing)
            if a.hero.slow_t > 0:
                slows.append(a.hero.slow_mult)
        run(a, 1.0, watch)
        steps = [angle_off(x, y) for x, y in zip(facings, facings[1:])]
        self.assertLessEqual(max(steps), config.TYRANT[0] * DT + 1e-6)
        hp = a.hero.hp
        t.x, t.y = a.hero.x - 2.5, a.hero.y
        t.stepped = config.TYRANT[12]
        run(a, DT)
        self.assertEqual(a.hero.slow_mult, config.TYRANT[14])
        self.assertEqual(a.hero.hp, hp)
        self.assertFalse(any(ech.kind == "area" and ech.data["damage"] == 0 for ech in t.echoes))

    def test_the_club_tails_back_shrugs_off_hits_and_its_tail_throws_you(self):
        c = enemy("club_tail", 20.5, 15.5)
        c.facing = 0.0
        hp = c.hp
        c.take_damage(100, None, math.pi)                     # (at its head)
        self.assertAlmostEqual(hp - c.hp, 100)
        hp = c.hp
        c.take_damage(100, None, 0.0)                         # (from behind)
        self.assertAlmostEqual(hp - c.hp, 100 * config.CLUB[1])
        c = enemy("club_tail", 20.5, 15.5)
        a = arena(c, hero_at=(24.5, 15.5))
        hp = a.hero.hp
        run(a, 6.0)
        self.assertLess(a.hero.hp, hp)
        self.assertGreater(abs(a.hero.x - 24.5) + abs(a.hero.y - 15.5), 1.5)   # (thrown)

    def test_the_pterosaur_carries_you_off_and_drops_you(self):
        p = enemy("pterosaur", 20.5, 8.5)
        a = arena(p, hero_at=(30.5, 15.5))
        p.cooldown = 0.0
        caught = []

        def watch():
            if p.state == "carry" and not caught:
                caught.append((a.hero.x, a.hero.y))
        run(a, 4.0, watch)
        self.assertTrue(caught)
        self.assertIn("DROPPED!", [fx.label for fx in a.effects if fx.kind == "toast"])
        x, y = caught[0]                                     # (it snaps you to its feet first)
        self.assertGreater(math.hypot(a.hero.x - x, a.hero.y - y), config.PTERO[3] * 0.5)
        self.assertTrue(p.flies)

    def test_a_drop_never_leaves_you_in_rock(self):
        rock = {(x, y): tiles.BASALT_BOULDER for x in range(30, 36) for y in range(12, 19)}
        p = enemy("pterosaur", 20.5, 15.5)
        a = arena(p, hero_at=(28.5, 15.5), world=ash_map(patches=rock))
        p.aim, p.state, p.caught, p.carried = 0.0, "carry", a.hero, 0.0
        run(a, 1.0)
        self.assertFalse(a.world.tile_at(math.floor(a.hero.x), math.floor(a.hero.y)).solid)


class HeartTest(unittest.TestCase):
    def test_dragonflies_show_each_dart_then_dart_straight(self):
        d = enemy("dragonfly", 20.5, 15.5)
        a = arena(d, hero_at=(30.5, 15.5))
        aims = []

        def watch():
            if d.state == "dart" and d.ran == 0.0:
                aims.append(d.aim)
        self.assertTrue(until(a, lambda: d.state == "hover" and d.aimed and d.tell > 0))
        shown = d.aim
        run(a, 3.0, watch)
        self.assertAlmostEqual(aims[0], shown)
        self.assertGreaterEqual(len(aims), 3)
        self.assertTrue(d.echoes or d.runners)

    def test_the_beetle_sprays_out_of_its_back_so_its_front_is_safe(self):
        b = enemy("bombardier_beetle", 20.5, 15.5)
        a = arena(b, hero_at=(23.5, 15.5))
        hp = a.hero.hp
        self.assertTrue(until(a, lambda: b.state == "aim", 4.0))
        self.assertLess(angle_off(b.angle_to(a.hero.x, a.hero.y), b.facing + math.pi), 0.4)
        run(a, config.ENEMIES["bombardier_beetle"].windup + DT)
        self.assertLess(a.hero.hp, hp)
        b2 = still(enemy("bombardier_beetle", 20.5, 15.5))
        a2 = arena(b2, hero_at=(23.5, 15.5))
        b2.facing = 0.0                                       # (facing you)
        hp = a2.hero.hp
        b2.area(ctx_of(a2), "cone", b2.x, b2.y, b2.facing + math.pi, config.BEETLE[4],
                math.radians(config.BEETLE[3]) / 2, 50.0)
        self.assertEqual(a2.hero.hp, hp)

    def test_ants_march_in_a_column_until_its_broken_then_swarm(self):
        m = enemy("ant_mound", 12.5, 15.5)
        a = arena(m, hero_at=(29.5, 15.5))
        m.send_t = 0.0

        def ants_now():
            return [e for e in a.enemies if isinstance(e, GiantAnt)]
        self.assertTrue(until(a, lambda: len(ants_now()) >= 3, config.ANTS[0] * 5))
        m.send_t = 99.0                                       # (three's a column)
        run(a, 2.0)
        ants = sorted(ants_now(), key=lambda x: x.order)
        for ahead, behind in zip(ants, ants[1:]):             # (each close behind the one before)
            self.assertLess(math.hypot(behind.x - ahead.x, behind.y - ahead.y), config.ANTS[2] + 1.5)
            self.assertLess(ahead.dist_to(a.hero), behind.dist_to(a.hero))
        self.assertTrue(all(x.mound is m and not x.swarming for x in ants))
        self.assertEqual(sorted(x.order for x in ants), list(range(len(ants))))
        ants[-1].take_damage(1, a.hero, 0.0)
        run(a, DT * 2)
        self.assertTrue(all(x.swarming for x in ants if x.alive))

    def test_at_most_so_many_ants_and_none_once_the_mound_falls(self):
        m = enemy("ant_mound", 12.5, 15.5)
        a = arena(m, hero_at=(28.5, 15.5))
        a.hero.untouchable = 999.0                            # (they never reach it: the column holds)
        run(a, config.ANTS[0] * (config.ANTS[1] + 3))
        ants = [e for e in a.enemies if isinstance(e, GiantAnt) and e.alive]
        self.assertLessEqual(len(ants), config.ANTS[1])
        m.take_damage(m.hp + 1, a.hero, 0.0)
        n = len(a.enemies)
        run(a, config.ANTS[0] * 2)
        self.assertEqual(len(a.enemies), n)
        self.assertTrue(all(x.swarming for x in ants if x.alive))

    def test_the_sea_scorpion_never_leaves_its_pool(self):
        s = enemy("sea_scorpion", 18.5, 15.5)
        a = arena(s, hero_at=(26.5, 8.5), world=ash_map(pool=(18.5, 15.5, 4.0)))
        a.hero.water_walk = True
        spots = []
        run(a, 6.0, lambda: spots.append((s.x, s.y)))
        self.assertTrue(all(a.world.tile_at(math.floor(x), math.floor(y)) is tiles.HOT_SPRING
                            for x, y in spots))
        self.assertGreater(max(y for _, y in spots) - min(y for _, y in spots) + 0.0
                           + max(x for x, _ in spots) - min(x for x, _ in spots), 1.0)

    def test_its_claws_drag_you_into_the_scalding_water_until_you_roll(self):
        s = enemy("sea_scorpion", 18.5, 15.5)
        a = arena(s, hero_at=(23.5, 15.5), world=ash_map(pool=(18.5, 15.5, 4.0)))
        a.hero.water_walk = True
        s.sting_cd = 99.0
        self.assertTrue(until(a, lambda: s.state == "drag", 3.0))
        run(a, config.SEA_SCORPION[2] + 0.1)
        self.assertIs(a.world.tile_at(math.floor(a.hero.x), math.floor(a.hero.y)), tiles.HOT_SPRING)
        self.assertEqual(a.hero.slow_mult, 0.0)
        a.hero.roll_t = 0.3
        run(a, DT * 2)
        self.assertEqual(s.state, "lurk")
        self.assertIsNone(s.held)

    def test_its_tail_spike_stabs_a_marked_spot(self):
        s = enemy("sea_scorpion", 18.5, 15.5)
        a = arena(s, hero_at=(26.5, 15.5), world=ash_map(pool=(18.5, 15.5, 4.0)))
        s.sting_cd, s.cooldown = 0.0, 99.0
        hp = a.hero.hp
        self.assertTrue(until(a, lambda: s.state == "sting", 2.0))
        mark = s.sting_at
        self.assertEqual(mark, (a.hero.x, a.hero.y))
        run(a, config.SEA_SCORPION[6] + DT)
        self.assertLess(a.hero.hp, hp)

    def test_the_pools_scald(self):
        a = arena(world=ash_map(pool=(30.5, 15.5, 3.0)))
        sc = _BreakScene(a)
        hp = a.hero.hp
        for _ in range(30):
            land_sys._underfoot(sc, a.hero, tiles.HOT_SPRING, DT)
        self.assertLess(a.hero.hp, hp)


class NestAndAmberTest(unittest.TestCase):
    def test_an_egg_hatches_and_the_parent_comes_once(self):
        eggs = {(30, 10): tiles.EGG, (31, 10): tiles.EGG}
        a = arena(hero_at=(30.5, 15.5), world=ash_map(patches=eggs))
        sc = _BreakScene(a)
        while a.world.damage_tile(30, 10, 50) is not Damage.DESTROYED:
            pass
        self.assertEqual([(x, y, t) for x, y, t in a.world.broke], [(30, 10, tiles.EGG)])
        land_sys.breaks(sc, a.world.broke)
        a.world.broke.clear()
        hatch = [e for e in a.enemies if isinstance(e, Hatchling)]
        parents = [e for e in a.enemies if e.kind_key in config.NEST_PARENTS]
        self.assertEqual(len(hatch), config.NEST_HATCH[0])
        self.assertEqual(len(parents), 1)
        self.assertGreater(parents[0].driven, 0)
        self.assertIn("THE PARENT COMES!", [fx.label for fx in a.effects if fx.kind == "toast"])
        while a.world.damage_tile(31, 10, 50) is not Damage.DESTROYED:
            pass
        land_sys.breaks(sc, a.world.broke)
        self.assertEqual(len([e for e in a.enemies if isinstance(e, Hatchling)]), 2 * config.NEST_HATCH[0])
        self.assertEqual(len([e for e in a.enemies if e.kind_key in config.NEST_PARENTS]), 1)

    def test_amber_frees_loot_or_a_fight_once_an_outcrop(self):
        outcomes = set()
        for k in range(12):
            ox, oy = 5 + (k % 6) * 9, 5 + (k // 6) * 12
            amber = {(ox + i, oy + j): tiles.AMBER for i in range(2) for j in range(2)}
            a = arena(hero_at=(55.5, 28.5), world=ash_map(patches=amber))
            sc = _BreakScene(a)
            for i, j in ((0, 0), (1, 0)):
                while a.world.damage_tile(ox + i, oy + j, 10 ** 6) is not Damage.DESTROYED:
                    pass
            land_sys.breaks(sc, a.world.broke)
            freed = [e for e in a.enemies if e.alive]
            if freed:
                outcomes.add("fight")
                names = {e.kind_key for e in freed}
                self.assertTrue(names <= {n for n, _ in config.AMBER_FIGHTS[0]}, names)
                self.assertIn(len(freed), [n for _, n in config.AMBER_FIGHTS[0]])  # (once: one lot)
            if sc.gems:
                outcomes.add("loot")
                self.assertAlmostEqual(sum(g.value for g in sc.gems), config.AMBER_FREE[1])
            self.assertFalse(freed and sc.gems)
        self.assertEqual(outcomes, {"loot", "fight"})


class WorldTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = ChunkedWorld(31)
        cls.z = cls.w.layout.zone("pangaea")
        cls.p = plan_of(cls.w.layout, cls.z)

    def test_sea_scorpions_live_in_every_other_pool(self):
        got = residents(self.w.layout, self.z)
        self.assertEqual(len(got), len(self.p.pools[::config.SEA_SCORPION[0]]))
        for key, x, y in got:
            self.assertEqual(key, "sea_scorpion")
            self.w.ensure_ready(math.floor(x) - 2, math.floor(y) - 2, math.floor(x) + 2, math.floor(y) + 2)
            self.assertIs(self.w.tile_at(math.floor(x), math.floor(y)), tiles.HOT_SPRING)

    def test_every_ring_gets_its_own(self):
        sp = Spawner(self.w, 31)
        z, p = self.z, self.p
        n = config.CHUNK_SIZE
        rng = random.Random(9)
        seen = {0: set(), 1: set(), 2: set()}
        tries = 0
        while tries < 500 and not all(len(v) >= 2 for v in seen.values()):
            tries += 1
            a, r = rng.uniform(0, math.tau), rng.uniform(0, z.radius)
            cx = math.floor((z.cx + math.cos(a) * r) / n)
            cy = math.floor((z.cy + math.sin(a) * r) / n)
            if self.w.biome_at(cx * n + n // 2, cy * n + n // 2).name != "pangaea":
                continue
            for _, key, x, y in sp.roster(cx, cy):
                if key in config.PANGAEA_RING_OF:
                    seen[config.PANGAEA_RING_OF[key]].add(key)
                    ring = p.ring_at(cx * n + n / 2, cy * n + n / 2)
                    self.assertEqual(config.PANGAEA_RING_OF[key], ring, key)
        for ring, keys in seen.items():
            self.assertGreaterEqual(len(keys), 2, (ring, keys))

    def test_breaking_reports_eggs_and_amber_only(self):
        w = ChunkedWorld(31)
        self.assertEqual(w.broke, [])
        self.assertEqual(tiles.REPORT_BREAKS, {tiles.EGG, tiles.GIANT_EGG, tiles.AMBER})


class GameTest(unittest.TestCase):
    def test_a_fight_in_the_heart_steps_and_draws(self):
        from ascii_adventurers.tests.test_m31_1 import _game
        m, s = _game()
        for _ in range(3):
            s._dev_zone()
        s.quests.banner = None
        s.hero.hp = s.hero.max_hp = 10 ** 6
        s.enemies.clear()
        for k, key in enumerate(MIDDLE + HEART + ("hatchling",)):
            a = k * math.tau / 8
            e = s.spawner.wake(key, s.hero.x + math.cos(a) * 9, s.hero.y + math.sin(a) * 6,
                               rng=random.Random(k))
            e.alert = True
            s.enemies.append(e)
        for _ in range(60 * 5):
            s._step(1 / 60)
            s.hero.hp = s.hero.max_hp
        s.quests.banner = None
        s.draw(m.text)
        self.assertTrue(any(isinstance(e, Beast) and (e.echoes or e.runners) for e in s.enemies))


if __name__ == "__main__":
    unittest.main()
