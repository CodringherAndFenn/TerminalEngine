"""M33.1: the kill order and the final bosses' framework, and the Fossil
Angel's first form (design/FINALS.md 1-9): the pairs (the one killed last
in each pair wins), the final waking when the fourth ocean boss falls,
coming ashore between its realms, hunting you across the map (the walk, the
leap, its trail, its creatures, island monsters turning on it), the true
victory (the screen, the journal's kill orders, the trophies), and the
Fossil Angel's four signatures and four moves."""

import itertools
import math
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.ai import KINDS, make_enemy
from ascii_adventurers.ai.finals import Final
from ascii_adventurers.ai.fossil_angel import FossilAngel, LavaHalo
from ascii_adventurers.meta.guild import Guild, _journal
from ascii_adventurers.render import finals_art  # noqa: F401
from ascii_adventurers.render.characters import ART
from ascii_adventurers.systems import finals
from ascii_adventurers.systems.zones import update_zones
from ascii_adventurers.tests.test_p7 import Arena, enemy
from ascii_adventurers.tests.test_weapons import open_map
from ascii_adventurers.world import tiles
from ascii_adventurers.world.layout import IslandLayout

DT = 1 / 60
ZONES = ("paradise", "pandemonium", "pangaea", "panopticon")


def angel(x=30.5, y=15.5, seed=3):
    a = make_enemy("fossil_angel", x, y, random.Random(seed))
    a.grace = 0.0
    return a


def run(a, seconds):
    for _ in range(round(seconds * 60)):
        a.run(DT)
        update_zones(a.zones, a.actors(), a.effects, DT, a.world)


def until(a, cond, seconds=3.0):
    for _ in range(round(seconds * 60)):
        if cond():
            return True
        run(a, DT)
    return cond()


def force(a, ar, move, phase=None):
    """Start move `move` now (in `phase`), and keep it from picking others."""
    if phase is not None:
        a.phase = phase
    ar.run(DT)
    a._start(move)
    a._wait = 0.0


class CatalogTest(unittest.TestCase):
    def test_the_pairs_and_the_four_finals(self):
        self.assertEqual(config.FINAL_PAIRS, (("paradise", "pandemonium"), ("pangaea", "panopticon")))
        self.assertEqual(set(config.FINAL_OF), set(itertools.product(*config.FINAL_PAIRS)))
        self.assertEqual(set(config.FINAL_OF.values()), set(config.FINAL_NAMES))
        self.assertEqual(config.FINAL_OF[("paradise", "pangaea")], "fossil_angel")
        self.assertEqual(config.FINAL_OF[("pandemonium", "panopticon")], "the_feed")
        q = config.FINALS["fossil_angel"]
        self.assertEqual((q.kind, q.boss, q.biome), ("final", "fossil_angel", "final"))
        self.assertEqual(config.FINAL_STAND_IN, "fossil_angel")

    def test_the_fossil_angel(self):
        spec = config.ENEMIES["fossil_angel"]
        self.assertIs(KINDS[spec.kind], FossilAngel)
        self.assertTrue(issubclass(FossilAngel, Final))
        self.assertEqual(spec.max_hp, 15000)                       # (user: 15,000 + 18,000)
        for key in ("fossil_angel", "lava_halo"):
            self.assertIn(key, config.BESTIARY)
        self.assertIn("fossil_angel", config.ACHIEVEMENTS)
        b = config.BOSSES["fossil_angel"]
        self.assertEqual([ph.below for ph in b.phases], [1.0, 0.75, 0.5, 0.25])
        moves = [{m for m, _ in ph.moves} for ph in b.phases]
        for ph in moves:
            self.assertTrue({"feathers", "sweep", "dive", "breath", "stars"} <= ph)
        self.assertNotIn("halo", moves[0])
        self.assertIn("halo", moves[1])
        self.assertNotIn("amber", moves[2])
        self.assertIn("amber", moves[3])
        self.assertEqual(config.FOSSIL_ECHO_PHASE, 2)
        keys = list(config.BOSSES)                                  # (the relic seeds stay)
        self.assertEqual(keys.index("fossil_angel"), keys.index("overseer_city") + 1)
        for name in ("fossil_angel", "fossil_angel_beat", "fossil_wing", "fossil_wing_up",
                     "trophy_fossil_angel"):
            self.assertEqual(len(ART[name]), 18, name)
            self.assertTrue(all(len(r) == 14 for r in ART[name]), name)

    def test_what_it_leaves(self):
        self.assertTrue(tiles.FEATHER_SPIKE.solid and tiles.FEATHER_SPIKE.blocks_shots)
        self.assertTrue(tiles.AMBER_WALL.solid and tiles.AMBER_WALL.destructible)
        self.assertFalse(tiles.RESIN.solid)
        self.assertNotIn(tiles.AMBER_WALL, tiles.REPORT_BREAKS)    # (nothing frozen in these)


class KillOrderTest(unittest.TestCase):
    def test_in_each_pair_the_last_wins(self):
        seen = {}
        for order in itertools.permutations(ZONES):
            order = list(order)
            heaven = "paradise" if order.index("paradise") > order.index("pandemonium") \
                else "pandemonium"
            time_ = "pangaea" if order.index("pangaea") > order.index("panopticon") else "panopticon"
            key = finals.final_for(order)
            self.assertEqual(key, config.FINAL_OF[(heaven, time_)], order)
            seen[key] = seen.get(key, 0) + 1
        self.assertEqual(seen, {k: 6 for k in config.FINAL_OF.values()})   # (six orders each)
        # The doc's example: N, W, S, E -- hell + the future.
        self.assertEqual(finals.final_for(["paradise", "pangaea", "pandemonium", "panopticon"]),
                         "the_feed")

    def test_a_pair_is_settled_by_its_first_kill(self):
        self.assertEqual(finals.pair_winners([]), (None, None))
        self.assertEqual(finals.pair_winners(["paradise"]), ("pandemonium", None))
        self.assertEqual(finals.pair_winners(["panopticon", "pandemonium"]), ("paradise", "pangaea"))
        self.assertIsNone(finals.final_for(["paradise", "pangaea", "pandemonium"]))
        for key in config.FINAL_OF.values():
            self.assertEqual(finals.final_for(finals.order_for(key)), key)
        self.assertEqual(finals.built("the_feed"), config.FINAL_STAND_IN)   # (not built yet)
        self.assertEqual(finals.built("fossil_angel"), "fossil_angel")
        self.assertEqual(finals.order_text(["paradise", "pangaea"]), "Paradise, Pangaea")

    def test_it_comes_ashore_between_its_realms(self):
        for seed in (31, 7):
            lay = IslandLayout(seed)
            x, y = finals.ashore(lay, "fossil_angel")
            self.assertLess(x, 0)                              # (north-west: heaven and the past)
            self.assertLess(y, 0)
            self.assertNotEqual(lay.biome_at(x, y).name, "ocean", seed)
            r = math.hypot(x, y)
            self.assertGreater(r, lay.radius * 0.6, seed)      # (on the coast, not inland)
            self.assertEqual(lay.biome_at(x * 1.15, y * 1.15).name, "ocean", seed)


class HuntTest(unittest.TestCase):
    def test_it_walks_at_you_at_half_your_pace(self):
        a = angel(20.5, 15.5)
        ar = Arena(a, w=90, h=30, hero_at=(60.5, 15.5))
        ar.hero.invulnerable = True
        a._rest = 99.0                                  # (no moves: just the walk)
        x0 = a.x
        run(ar, 2.0)
        v = (a.x - x0) / 2.0
        self.assertAlmostEqual(v, config.FINAL_WALK[0], delta=0.3)
        run(ar, 10.0)                                   # (close: it circles, keeping its distance)
        d = math.hypot(a.x - ar.hero.x, a.y - ar.hero.y)
        self.assertLess(d, config.FINAL_WALK[1] + 3.0)
        self.assertGreater(d, config.FINAL_WALK[1] - 4.0)

    def test_it_comes_ashore_first(self):
        a = make_enemy("fossil_angel", 20.5, 15.5, random.Random(1))
        ar = Arena(a, w=60, h=30, hero_at=(40.5, 15.5))
        self.assertEqual(a.grace, config.FINAL_WAKE_GRACE)
        run(ar, 2.0)
        self.assertEqual((a.x, a.y), (20.5, 15.5))
        self.assertFalse(a.hunting)

    def test_it_leaps_when_you_get_away(self):
        far, crouch, flight, lo, hi, radius, damage, push, up = config.FINAL_LEAP
        a = angel(10.5, 30.5)
        ar = Arena(a, w=150, h=60, hero_at=(10.5 + far + 20, 30.5))
        a._rest = 99.0
        run(ar, DT * 2)
        self.assertEqual(a.leap[0], "crouch")
        self.assertTrue(a.hittable)
        run(ar, crouch + 0.05)
        self.assertEqual(a.leap[0], "air")
        self.assertFalse(a.hittable)                    # (up in the air)
        mx, my = a.mark
        d = math.hypot(mx - ar.hero.x, my - ar.hero.y)
        self.assertGreaterEqual(d, lo * 0.8 - 0.01)
        self.assertLessEqual(d, hi + 0.01)
        hp = ar.hero.hp
        ar.hero.x, ar.hero.y = mx + 2.0, my             # (stand in the ring)
        run(ar, flight)
        self.assertIsNone(a.leap)
        self.assertEqual(a.leaps, 1)
        self.assertAlmostEqual(a.x, mx, delta=0.01)
        self.assertLess(ar.hero.hp, hp)                 # (the impact)
        self.assertGreater(ar.hero.x, mx + 2.5)         # (pushed out)

    def test_it_leaps_over_water(self):
        rows = ["~" * 120 for _ in range(40)]
        for y in range(15, 25):
            rows[y] = "." * 10 + "~" * 100 + "." * 10
        from ascii_adventurers.world.test_map import TestMap
        a = angel(5.5, 20.5)
        ar = Arena(a, w=120, h=40, hero_at=(115.5, 20.5))
        ar.world = TestMap(rows)
        ar.hero.invulnerable = True
        a._rest = 99.0
        run(ar, config.FINAL_LEAP[1] + config.FINAL_LEAP[2] + 0.2)
        self.assertEqual(a.leaps, 1)
        self.assertLess(math.hypot(a.x - ar.hero.x, a.y - ar.hero.y), config.FINAL_LEAP[4] + 0.5)

    def test_its_trail_turns_the_land_but_not_the_water(self):
        walls = [(x, y) for x in range(28, 32) for y in range(10, 21)]
        a = angel(18.5, 15.5)
        ar = Arena(a, w=90, h=30, walls=walls, hero_at=(70.5, 15.5))
        for x in range(40, 44):                         # (a pond on its way)
            for y in range(13, 18):
                ar.world.set_tile(x, y, tiles.WATER)
        ar.hero.invulnerable = True
        a._rest = 99.0
        run(ar, 7.0)
        lands = {t for realm in FossilAngel.GROUNDS for t in realm}
        self.assertIn(ar.world.tile_at(24, 15), lands)
        self.assertIn(ar.world.tile_at(30, 15), lands)    # (the wall in its way: smashed)
        self.assertIs(ar.world.tile_at(42, 15), tiles.WATER)
        realms = [{ar.world.tile_at(x, y) in FossilAngel.GROUNDS[k]
                   for x in range(20, 40) for y in range(13, 18)} for k in (0, 1)]
        self.assertTrue(realms[0] == {True, False} and realms[1] == {True, False})  # (patches of each)
        self.assertGreater(len(a.path), 10)

    def test_its_creatures_crawl_out_of_the_trail(self):
        a = angel(8.5, 15.5)
        ar = Arena(a, w=120, h=30, hero_at=(60.5, 15.5))
        ar.hero.invulnerable = True
        a._rest = 99.0
        made = []
        apart = []

        def recruit(key, x, y):
            e = enemy(key, x, y, len(ar.enemies))
            ar.enemies.append(e)
            made.append(e)
            apart.append(math.hypot(x - ar.hero.x, y - ar.hero.y))
            return e
        a.recruit = recruit
        run(ar, config.FINAL_BROOD[0] * 2 + 0.5)
        self.assertTrue(made)
        for e in made:
            self.assertIn(e.kind_key, config.FINAL_BROODS["fossil_angel"])
            self.assertIs(e.final_own, a)
            self.assertTrue(e.zone_tough)
        for d in apart:                                 # (never crawling out on top of you)
            self.assertGreaterEqual(d, config.FINAL_BROOD[3] - 2.5)
        self.assertLessEqual(len([e for e in made if e.alive]), config.FINAL_BROOD[1])
        # Its blows never hurt them; an island monster it hurts turns on it.
        own = made[0]
        goblin = enemy("goblin_archer", a.x + 3.0, a.y)
        ar.enemies.append(goblin)
        own.x, own.y = a.x - 3.0, a.y
        from ascii_adventurers.ai.brain import AIContext
        ctx = AIContext(ar.world, [ar.hero], ar.actors(), ar.projectiles, ar.effects, zones=ar.zones)
        a.ctx = ctx
        hp = own.hp
        a.area(ctx, "circle", a.x, a.y, 0.0, 6.0, 0.0, 20.0)
        self.assertEqual(own.hp, hp)
        self.assertLess(goblin.hp, goblin.max_hp)
        self.assertIs(goblin.grudge, a)


class FossilAngelTest(unittest.TestCase):
    def setUp(self):
        self.a = angel(30.5, 20.5)
        self.ar = Arena(self.a, w=80, h=44, hero_at=(40.5, 20.5))
        self.ar.hero.invulnerable = True
        self.a._rest = 99.0

    def test_stone_feathers_leave_spikes_that_crumble(self):
        a, ar = self.a, self.ar
        ar.hero.invulnerable = False
        hp = ar.hero.hp
        force(a, ar, "feathers")
        run(ar, DT)
        self.assertEqual(len(a.lines), config.FOSSIL_FEATHERS[1])
        self.assertTrue(until(ar, lambda: a.spikes, 2.0))
        self.assertLess(ar.hero.hp, hp)                 # (the middle line was at you)
        tx, ty, old, _ = a.spikes[0]
        self.assertIs(ar.world.tile_at(tx, ty), tiles.FEATHER_SPIKE)
        for sx, sy, *_ in a.spikes:                     # (never on a hero)
            self.assertGreater(math.hypot(sx + 0.5 - ar.hero.x, sy + 0.5 - ar.hero.y), 1.0)
        a._rest = 99.0
        for s in a.spikes:
            s[3] = 0.01
        run(ar, 0.1)
        self.assertEqual(a.spikes, [])
        self.assertIs(ar.world.tile_at(tx, ty), old)

    def test_the_lava_halo_rolls_out_burns_and_cools_to_stone(self):
        a, ar = self.a, self.ar
        self.assertTrue(a.has_halo)
        force(a, ar, "halo", phase=1)
        self.assertTrue(until(ar, lambda: a.wheel is not None, 2.0))
        w = a.wheel
        self.assertIsInstance(w, LavaHalo)
        self.assertFalse(a.has_halo)
        self.assertIs(w.part_of, a)
        r0 = math.hypot(w.x - a.x, (w.y - a.y) / 0.8)
        run(ar, 3.0)
        self.assertGreater(math.hypot(w.x - a.x, (w.y - a.y) / 0.8), r0 + 2.0)   # (growing)
        self.assertTrue(any(z.kind == "lava_splash" and z.source is a for z in ar.zones))
        w.take_damage(w.hp + 1, ar.hero, 0.0)           # (hit enough: it cools to stone)
        tx, ty = math.floor(w.x), math.floor(w.y)
        run(ar, DT * 2)
        self.assertIsNone(a.wheel)
        self.assertIs(ar.world.tile_at(tx, ty), tiles.BASALT_BOULDER)
        self.assertFalse(a.has_halo)                    # (it grows back after a while)
        run(ar, 8.1)
        self.assertTrue(a.has_halo)

    def test_the_wheel_hits_what_it_rolls_over(self):
        a, ar = self.a, self.ar
        ar.hero.invulnerable = False
        force(a, ar, "halo", phase=1)
        until(ar, lambda: a.wheel is not None, 2.0)
        w = a.wheel
        hp = ar.hero.hp
        for _ in range(240):
            ar.hero.x, ar.hero.y = w.x, w.y
            run(ar, DT)
            if ar.hero.hp < hp:
                break
        self.assertLess(ar.hero.hp, hp)

    def test_its_attacks_echo_only_from_the_third_phase(self):
        a, ar = self.a, self.ar
        force(a, ar, "sweep", phase=1)
        run(ar, 1.2)
        self.assertEqual(a.echoes, [])
        self.assertFalse(a.echoing)
        a._rest = 99.0
        force(a, ar, "sweep", phase=2)
        self.assertTrue(a.echoing)
        self.assertTrue(until(ar, lambda: a.echoes, 2.0))
        e = a.echoes[0]
        self.assertEqual(e.kind, "area")
        hp = ar.hero.hp
        ar.hero.invulnerable = False
        ar.hero.x, ar.hero.y = e.data["x"] + 2.0, e.data["y"]   # (where it hit before)
        run(ar, config.ECHO[0] + 0.1)
        self.assertLess(ar.hero.hp, hp)                 # (it came again)

    def test_amber_holds_you_until_you_roll_and_hardens_into_walls(self):
        a, ar = self.a, self.ar
        h = ar.hero
        h.x, h.y = a.x + 8.0, a.y
        a.facing = 0.0
        force(a, ar, "amber", phase=3)
        self.assertTrue(until(ar, lambda: id(h) in a.held, 3.0))
        self.assertEqual(h.slow_mult, 0.0)
        self.assertGreater(h.slow_t, 0.0)
        self.assertTrue(a.resin)
        h.roll_t = 0.3                                  # (a roll: free)
        run(ar, DT)
        self.assertNotIn(id(h), a.held)
        self.assertEqual(h.slow_t, 0.0)
        h.roll_t = 0.0
        h.x, h.y = a.x, a.y + 15.0
        run(ar, config.FOSSIL_AMBER[7] + 1.5)
        self.assertTrue(a.walls)
        tx, ty, old, _ = a.walls[0]
        self.assertIs(ar.world.tile_at(tx, ty), tiles.AMBER_WALL)
        for w in a.walls:
            w[3] = 0.01
        run(ar, 0.1)
        self.assertIs(ar.world.tile_at(tx, ty), old)

    def test_amber_never_hardens_round_you(self):
        a, ar = self.a, self.ar
        h = ar.hero
        h.x, h.y = a.x + 8.0, a.y
        force(a, ar, "amber", phase=3)
        run(ar, config.FOSSIL_AMBER[0] + config.FOSSIL_AMBER[7] + 2.5)
        for tx, ty, *_ in a.walls:
            self.assertFalse(abs(h.x - tx - 0.5) < h.hit_radius + 0.5
                             and abs(h.y - ty - 0.5) < h.hit_radius + 0.5)

    def test_the_moves(self):
        a, ar = self.a, self.ar
        ar.hero.invulnerable = False
        ar.hero.max_hp = 10 ** 5                        # (alive through all of them)
        for move in ("sweep", "dive", "breath", "stars"):
            a.x, a.y = 30.5, 20.5
            ar.hero.x, ar.hero.y = 38.5, 20.5
            ar.hero.hp = ar.hero.max_hp
            before = len(ar.zones)
            fell = []
            a.landed = lambda ctx, x, y, what, echo, _f=FossilAngel.landed: (
                fell.append(what), _f(a, ctx, x, y, what, echo))
            force(a, ar, move)
            x0 = a.x
            self.assertTrue(until(ar, lambda: a.move is None, 6.0), move)
            a._rest = 99.0
            run(ar, 1.0)
            if move == "dive":
                self.assertGreater(abs(a.x - x0), config.FOSSIL_DIVE[2] * 0.8)
            if move == "breath":
                self.assertGreater(len(ar.zones), before)
            if move == "stars":                         # (they fall round you, not always on you)
                self.assertEqual(fell, ["star"] * (config.FOSSIL_STARS[1] * config.FOSSIL_STARS[2]))
                continue
            self.assertLess(ar.hero.hp, ar.hero.max_hp, move)

    def test_four_phases_banners(self):
        a, ar = self.a, self.ar
        for frac, phase in ((0.7, 1), (0.45, 2), (0.2, 3)):
            a._rest = 0.0
            a.hp = a.max_hp * frac
            run(ar, DT * 2)
            self.assertEqual(a.phase, phase)
            self.assertIsNotNone(a.banner_req)
            a.banner_req = None


def game(seed=31):
    from ascii_adventurers.tests.test_m16 import game as g
    m, s = g("wizard", seed=seed)
    return m, s


def step(s, n=1):
    for _ in range(n):
        s._remember_positions()
        s._step(DT)


class WakeTest(unittest.TestCase):
    def test_hidden_until_the_fourth_falls_then_it_wakes(self):
        m, s = game()
        q = s.quests
        f = q.states["fossil_angel"]
        self.assertEqual((f.stage, f.npc), ("hunt", None))
        self.assertIsNone(q.final)
        self.assertNotIn("FINAL", [label for label, *_ in q.log()])
        self.assertFalse([p for p in q.pins() if p[3] == f.lair.name])
        from ascii_adventurers.systems import mount
        self.assertFalse(mount.in_arena(s, s.hero))
        order = finals.order_for("fossil_angel")
        for z in order:
            st = next(x for x in q.states.values() if x.biome == z)
            st.boss = make_enemy(st.spec.boss, 0.0, 0.0, random.Random(1))
            st.stage = "fight"
            q._win(st, None)
            if z != order[-1]:
                self.assertIsNone(q.final)
        self.assertEqual(q.order, order)
        self.assertIs(q.final, f)
        self.assertEqual(f.stage, "fight")
        b = f.boss
        self.assertIsInstance(b, FossilAngel)
        self.assertIn(b, s.enemies)
        self.assertEqual(b.order, order)
        self.assertEqual(q.banner.title, "THE FOSSIL ANGEL")
        self.assertIn("north-west", q.banner.sub)
        self.assertLess(b.x, 0)
        self.assertLess(b.y, 0)
        self.assertEqual(q.log()[-1], ("FINAL", "defeat The Fossil Angel", False))
        self.assertTrue([p for p in q.pins() if p[3] == f.lair.name and p[2] == "lair"])
        self.assertIs(q.fight_for(s.hero), f)
        self.assertEqual(q.stream_views(), [])          # (coming ashore: nothing loaded there)
        self.assertTrue(mount.in_arena(s, s.hero))      # (everywhere is its battlefield)
        self.assertEqual(q.guardians, 0)
        s.hero.invulnerable = True
        step(s, round((config.FINAL_WAKE_GRACE + 0.2) * 60))
        self.assertTrue(b.leap is not None or b.leaps)  # (then it leaps to you)
        step(s, round((config.FINAL_LEAP[1] + config.FINAL_LEAP[2] + 0.2) * 60))
        self.assertEqual(b.leaps, 1)
        self.assertLess(math.hypot(b.x - s.hero.x, b.y - s.hero.y), config.FINAL_LEAP[4] + 3.0)
        view = q.stream_views()[0]
        self.assertAlmostEqual(view[0], b.x)

    def test_an_order_picking_an_unbuilt_final_wakes_the_stand_in(self):
        m, s = game()
        q = s.quests
        for z in finals.order_for("the_feed"):
            st = next(x for x in q.states.values() if x.biome == z)
            st.boss = make_enemy(st.spec.boss, 0.0, 0.0, random.Random(1))
            st.stage = "fight"
            q._win(st, None)
        self.assertEqual(finals.final_for(q.order), "the_feed")
        self.assertEqual(q.final.key, config.FINAL_STAND_IN)

    def test_dev_wakes_it_next_to_you_and_the_victory(self):
        m, s = game()
        q = s.quests
        q.dev_key = "fossil_angel"
        s.app.dev = True
        self.assertTrue(q.dev_finish_hunt())
        f = q.final
        b = f.boss
        self.assertEqual(finals.final_for(q.order), "fossil_angel")
        self.assertLess(math.hypot(b.x - s.hero.x, b.y - s.hero.y), 30.0)
        self.assertLessEqual(b.grace, 2.0)
        self.assertIsNotNone(q.dev_spot("lair"))
        s.app.dev = False
        loot = s.stats.loot
        s.hero.invulnerable = True
        b.take_damage(b.hp + 5, s.hero, 0.0)
        step(s, 2)
        self.assertEqual(f.stage, "cleared")
        self.assertTrue(s.stats.victory)
        self.assertEqual(s.stats.final, "fossil_angel")
        self.assertEqual(s.stats.order, q.order)
        self.assertGreater(s.stats.loot, loot + 30000)
        e = s.app.guild.journal["fossil_angel"]
        self.assertEqual(e["wins"], 1)
        self.assertEqual(e["orders"], [q.order])
        self.assertIn("fossil_angel", s.app.guild.achievements)
        self.assertEqual(q.banner.title, "THE FOSSIL ANGEL FALLS")
        self.assertIsNone(s.overlay)                    # (the fall is seen first...)
        step(s, round(config.FINAL_VICTORY_DELAY * 60) + 2)
        s.update(DT)
        from ascii_adventurers.ui.overlays import FinalVictoryPanel
        self.assertIsInstance(s.overlay, FinalVictoryPanel)   # (...then the true victory)
        self.assertIn("THE FOSSIL ANGEL", s.overlay.heading[0])
        s.draw(m.text)
        self.assertFalse(q.final.lair.inside(s.hero.x, s.hero.y))   # (no arena any more)


class JournalTest(unittest.TestCase):
    def test_the_journal_keeps_each_kill_order_once(self):
        g = Guild()
        order = finals.order_for("fossil_angel")
        g.record_quest("fossil_angel", ["bard"], 400.0)
        g.record_order("fossil_angel", order)
        g.record_order("fossil_angel", order)
        other = ["panopticon", "pandemonium", "paradise", "pangaea"]
        g.record_order("fossil_angel", other)
        self.assertEqual(g.journal["fossil_angel"]["orders"], [order, other])
        back = _journal(g.journal)
        self.assertEqual(back["fossil_angel"]["orders"], [order, other])
        bad = {"fossil_angel": {"wins": 1, "best": 3.0, "heroes": [], "orders": [["x"], order]}}
        self.assertEqual(_journal(bad)["fossil_angel"]["orders"], [order])

    def test_the_trophies_in_the_guild_hall(self):
        from ascii_adventurers.world.hub import load_hub
        _, stations = load_hub()
        trophies = [st for st in stations if st.kind == "trophy"]
        self.assertEqual([st.hero for st in trophies], list(config.FINAL_OF.values()))
        self.assertEqual(trophies[0].sprite, "trophy_fossil_angel")
        from ascii_adventurers.tests.test_players import make_manager
        from ascii_adventurers.scenes.guild_hall import GuildHallScene
        m = make_manager()
        m.app.guild = Guild()
        hall = GuildHallScene("wizard")
        m._set_scene(hall)
        hall.update(DT)
        self.assertFalse(hall.trophy_won("fossil_angel"))
        self.assertEqual(hall._trophy_text("fossil_angel"), "an empty pedestal")
        hall.app.guild.record_quest("fossil_angel", ["wizard"], 300.0)
        self.assertTrue(hall.trophy_won("fossil_angel"))
        self.assertIn("beaten 1 time", hall._trophy_text("fossil_angel"))
        hall.draw(m.text)


if __name__ == "__main__":
    unittest.main()
