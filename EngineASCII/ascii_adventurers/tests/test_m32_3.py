"""M32.3: Panopticon's other eight (design/OCEAN.md 37): the housekeepers
(butler, scrubber, gardener, nanny), polite until you make a mess in the
kept homes; the scrap (junker and its pieces, magnet, rust swarm, scrap
colossus), the junkers lying among the wrecks as wrecks."""

import math
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.ai import KINDS
from ascii_adventurers.ai import panopticon as P
from ascii_adventurers.render import panopticon_art  # noqa: F401
from ascii_adventurers.render.characters import ART
from ascii_adventurers.systems.zones import update_zones
from ascii_adventurers.tests.test_p7 import Arena, enemy
from ascii_adventurers.world import tiles
from ascii_adventurers.world.chunked import ChunkedWorld
from ascii_adventurers.world.panopticon import HOMES, SCRAPYARD
from ascii_adventurers.world.test_map import TestMap
from ascii_adventurers.world.zones import plan_of

KEEPERS = ("butler", "scrubber", "gardener", "nanny")
SCRAP = ("junker", "magnet", "rust_swarm", "scrap_colossus")
DT = 1 / 60


def arena(*enemies, hero_at=(30.5, 15.5), walls=()):
    a = Arena(*enemies, hero_at=hero_at, walls=walls)
    a.hero.hp = a.hero.max_hp = 100000
    return a


def run(a, seconds):
    for _ in range(round(seconds * 60)):
        a.run(DT)
        update_zones(a.zones, a.actors(), a.effects, DT, a.world)


def until(a, cond, seconds=2.0):
    for _ in range(round(seconds * 60)):
        if cond():
            return True
        run(a, DT)
    return cond()


def awake(key, x, y, seed=1):
    """One that's already fighting (not keeping house, not lying there)."""
    e = enemy(key, x, y, seed)
    e.working = False
    return e


class CatalogTest(unittest.TestCase):
    def test_the_other_eight_each_with_its_picture_page_and_district(self):
        for key in KEEPERS + SCRAP + ("junk_bit",):
            spec = config.ENEMIES[key]
            self.assertIn(spec.kind, KINDS, key)
            self.assertTrue(issubclass(KINDS[spec.kind], P.Machine), key)
            self.assertIn(key, config.BESTIARY, key)
            self.assertIn(spec.sprite, ART, key)
            self.assertTrue(all(len(r) == 14 for r in ART[spec.sprite]), key)
        for key in KEEPERS:
            self.assertEqual(config.ENEMIES[key].biomes, ("panopticon",))
            self.assertEqual(config.PANOPTICON_DISTRICT_OF[key], (HOMES,))
            self.assertTrue(issubclass(KINDS[key], P.Keeper))
            self.assertEqual(KINDS[key].group, "keepers")
        for key in SCRAP:
            self.assertEqual(config.PANOPTICON_DISTRICT_OF[key], (SCRAPYARD,))
            self.assertEqual(KINDS[key].group, "scrap")
        self.assertEqual(config.ENEMIES["junk_bit"].biomes, ())     # (a junker's pieces)
        self.assertEqual({k for k in KEEPERS + SCRAP if config.ENEMIES[k].elite},
                         {"nanny", "scrap_colossus"})
        for name in ("butler_bow", "nanny_reach", "junker_heap"):
            self.assertIn(name, ART)
        # (all sixteen now, four in each group)
        groups = {}
        for k, spec in config.ENEMIES.items():
            if spec.biomes == ("panopticon",):
                groups.setdefault(KINDS[spec.kind].group, []).append(k)
        self.assertEqual({g: len(v) for g, v in groups.items()},
                         {"watch": 4, "workers": 4, "keepers": 4, "scrap": 4})


class PlanTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = ChunkedWorld(31)
        cls.z = cls.w.layout.zone("panopticon")
        cls.p = plan_of(cls.w.layout, cls.z)

    def test_the_kept_homes_staff_and_the_scrapyard_s_wrecks(self):
        p, w = self.p, self.w
        res = P.residents(w.layout, self.z)
        keys = [k for k, _, _ in res]
        homes = next(m for m in p.marks if m.key == "panopticon_homes")
        self.assertEqual(len(homes.props["rooms"]), 10)
        self.assertEqual(len(homes.props["lawns"]), 10)
        self.assertEqual((keys.count("butler"), keys.count("gardener"), keys.count("scrubber"),
                          keys.count("nanny")), (5, 3, 6, 1))
        hx, hy = p.homes
        w.ensure_ready(hx - 30, hy - 18, hx + 30, hy + 18)
        for x, y in homes.props["rooms"]:
            self.assertIs(w.tile_at(math.floor(x), math.floor(y)), tiles.HOME_FLOOR)
        for x, y in homes.props["lawns"]:
            self.assertIs(w.tile_at(math.floor(x), math.floor(y)), tiles.LAWN)
        for k, x, y in res:
            if k in KEEPERS:
                self.assertFalse(w.tile_at(math.floor(x), math.floor(y)).solid, (k, x, y))
                self.assertEqual(p.district_at(x, y), HOMES)
        yard = next(m for m in p.marks if m.key == "panopticon_scrapyard")
        self.assertEqual(keys.count("junker"), len(yard.props["wrecks"]))
        self.assertEqual(keys.count("scrap_colossus"), 1)
        sx, sy = p.scrapyard
        w.ensure_ready(sx - 40, sy - 30, sx + 40, sy + 30)
        for x, y in yard.props["wrecks"]:                   # (each junker on its wreck)
            self.assertIs(w.tile_at(math.floor(x), math.floor(y)), tiles.WRECK)
        self.assertIs(w.tile_at(sx, sy), tiles.YARD_DIRT)

    def test_a_junker_on_its_wreck_lies_there_as_that_wreck(self):
        from ascii_adventurers.systems.spawner import Spawner
        w = ChunkedWorld(31)                                # (its own: this changes the tiles)
        p = plan_of(w.layout, w.layout.zone("panopticon"))
        yard = next(m for m in p.marks if m.key == "panopticon_scrapyard")
        x, y = yard.props["wrecks"][0]
        w.ensure_ready(math.floor(x) - 20, math.floor(y) - 20, math.floor(x) + 20, math.floor(y) + 20)
        e = Spawner(w, 31).wake("junker", x, y, (0, 0, 5000))
        self.assertTrue(e.dormant)
        self.assertTrue(e.hittable)                         # (a heap you can shoot)
        self.assertEqual(e.sprite_now(), "junker_heap")
        for tx in (math.floor(x) - 1, math.floor(x)):
            self.assertIs(w.tile_at(tx, math.floor(y)), tiles.YARD_DIRT)
        shed = Spawner(w, 31).wake("junker", x + 5, y, None, random.Random(1))   # (shed by a colossus)
        self.assertFalse(shed.dormant)


def _game():
    from ascii_adventurers.tests.test_m16 import game
    m, s = game("wizard", seed=31)
    s.app.dev = True
    for _ in range(4):
        s._dev_zone()
    return m, s


class HomesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m, cls.s = _game()
        lay = cls.s.world.layout
        cls.p = plan_of(lay, lay.zone("panopticon"))
        cls.s.spawner.update_views = lambda *a, **kw: None

    def setUp(self):
        from ascii_adventurers.systems import alert
        s = self.s
        s.enemies.clear()
        s.zones.clear()
        s.world.city_alert = alert.Alert()
        s.hero.hp = s.hero.max_hp = 100000

    def step(self, secs):
        from ascii_adventurers.tests.test_m17 import step
        step(self.s, round(secs * 60))

    def test_polite_until_you_make_a_mess(self):
        from ascii_adventurers.tests.test_m17 import teleport
        s, p = self.s, self.p
        homes = next(m for m in p.marks if m.key == "panopticon_homes")
        rx, ry = homes.props["rooms"][0]
        teleport(s, rx + 2.0, ry)
        b = s.spawner.wake("butler", rx, ry, None, random.Random(1))
        far = s.spawner.wake("butler", rx + config.MESS_REACH + 20, ry, None, random.Random(2))
        s.enemies[:] = [b, far]
        self.assertTrue(b.working)
        s.hero.x, s.hero.y = b.x + 2.0, b.y
        self.step(1.0)
        self.assertTrue(b.working)                          # (you came near: still polite)
        table = next((x, y) for y in range(math.floor(ry) - 4, math.floor(ry) + 5)
                     for x in range(math.floor(rx) - 4, math.floor(rx) + 9)
                     if s.world.tile_at(x, y) is tiles.SET_TABLE)
        while s.world.tile_at(*table) is tiles.SET_TABLE:
            s.world.damage_tile(*table, 50)
        self.assertIs(s.world.tile_at(*table), tiles.A_MESS)
        self.step(0.1)
        self.assertFalse(b.working)                         # (A MESS!: it comes for you)
        self.assertTrue(b.alert)
        self.assertTrue(far.working)                        # (too far to mind)
        self.assertTrue(any(getattr(e, "label", "") == "A MESS!" for e in s.effects))
        self.assertEqual([q for q in s.world.broke if q[2] in (tiles.SET_TABLE, tiles.MADE_BED)], [])

    def test_soap_slides_you(self):
        from ascii_adventurers.systems.zones import Zone
        from ascii_adventurers.tests.test_m17 import teleport
        s, p = self.s, self.p
        hx, hy = p.homes
        teleport(s, hx + 0.5, hy + 0.5)
        h = s.hero
        s.zones.append(Zone("soap", h.x, h.y, 0.8, 6.0, 999.0, 0.0, None))
        self.step(DT * 2)
        self.assertEqual(h.traction, config.SCRUBBER[5])
        s.zones.clear()
        self.step(DT * 2)
        self.assertEqual(h.traction, 1.0)

    def test_rust_eats_your_armour(self):
        h = self.s.hero
        h.rust_until = -1.0
        hp = h.hp
        h.take_damage(100.0, None, None)
        plain = hp - h.hp
        h.hp = hp
        h.rust_until = h.time + 5.0
        h.take_damage(100.0, None, None)
        self.assertGreater(hp - h.hp, plain * 1.1)
        h.rust_until = -1.0

    def test_draws_them_all(self):
        from ascii_adventurers.tests.test_m17 import teleport
        s, p = self.s, self.p
        hx, hy = p.homes
        teleport(s, hx + 0.5, hy + 0.5)
        h = s.hero
        for k, key in enumerate(KEEPERS + SCRAP + ("junk_bit",)):
            a = k * math.tau / 9
            e = s.spawner.wake(key, h.x + math.cos(a) * 6, h.y + math.sin(a) * 3, (9, 9, k),
                               random.Random(k))
            s.enemies.append(e)
        s.draw(self.m.text)                                 # (lying, keeping house)
        for e in s.enemies:
            e.called_to(h)
        self.step(2.0)
        s.draw(self.m.text)


class KeepersTest(unittest.TestCase):
    def test_the_butler_bows_and_its_tray_loops_back(self):
        b = awake("butler", 22.5, 15.5)
        a = arena(b, hero_at=(28.5, 15.5))
        self.assertTrue(until(a, lambda: b.state == "bow", 2.0))
        self.assertTrue(until(a, lambda: bool(b.trays), 2.0))
        tr = b.trays[0]
        far = 0.0
        hp = a.hero.hp
        for _ in range(round(config.BUTLER[4] * 60) - 2):
            run(a, DT)
            far = max(far, math.hypot(tr.x - b.x, tr.y - b.y))
        self.assertAlmostEqual(far, config.BUTLER[2], delta=1.0)    # (out its length...)
        self.assertLess(math.hypot(tr.x - b.x, tr.y - b.y), 1.0)     # (...and back to it)
        self.assertLess(a.hero.hp, hp)
        self.assertEqual(len(tr.hit), 1)                             # (once a throw)

    def test_two_butlers_throw_crossing_trays(self):
        b1 = awake("butler", 22.5, 13.5)
        b2 = awake("butler", 22.5, 17.5, seed=2)
        a = arena(b1, b2, hero_at=(28.5, 15.5))
        self.assertTrue(until(a, lambda: b1.state == "bow" or b2.state == "bow", 2.0))
        self.assertEqual({b1.state, b2.state}, {"bow"})
        self.assertEqual(b1.side * b2.side, -1)

    def test_the_scrubber_bounces_off_walls_and_leaves_soap(self):
        sc = awake("scrubber", 20.5, 15.5)
        a = arena(sc, hero_at=(24.5, 15.5), walls=[(27, y) for y in range(5, 26)])
        self.assertTrue(until(a, lambda: sc.state == "run", 2.0))
        d0 = math.cos(sc.dir)
        self.assertTrue(until(a, lambda: math.cos(sc.dir) * d0 < 0, 1.5))   # (it bounced)
        run(a, 0.5)
        self.assertGreater(len([z for z in a.zones if z.kind == "soap"]), 2)
        self.assertLess(a.hero.hp, a.hero.max_hp)

    def test_the_gardener_snips_twice_and_walls_you_in_with_wire(self):
        g = awake("gardener", 25.5, 15.5)
        a = arena(g, hero_at=(28.0, 15.5))
        g.wire_t = 99.0
        hits = []
        orig = a.hero.take_damage

        def counted(amount, source, ang):
            hits.append(amount)
            return orig(amount, source, ang)
        a.hero.take_damage = counted
        self.assertTrue(until(a, lambda: g.state == "lunge", 2.0))
        run(a, config.ENEMIES["gardener"].windup + config.GARDENER[2] + 0.1)
        self.assertGreaterEqual(len(hits), 2)               # (the snip, and the second)
        a.hero.take_damage = orig
        h = enemy("gardener", 20.5, 15.5)
        h.working = False
        b = arena(h, hero_at=(26.5, 15.5))
        h.wire_t, h.cooldown = 0.0, 99.0
        self.assertTrue(until(b, lambda: h.state == "grow", 1.0))
        run(b, 0.7)
        hx, hy = b.hero.x, b.hero.y
        wire = [(x, y) for y in range(10, 22) for x in range(20, 34)
                if b.world.tile_at(x, y) is tiles.THORN_WIRE]
        self.assertGreater(len(wire), 10)
        gx, gy = math.floor(h.grow_at[0]) if h.grow_at else math.floor(hx), math.floor(hy)
        for x, y in wire:                                    # (a closed ring round you)
            self.assertEqual(max(abs(x - math.floor(hx)), abs(y - math.floor(hy))), config.GARDENER[5])
        self.assertTrue(tiles.THORN_WIRE.solid and tiles.THORN_WIRE.destructible)
        self.assertIs(tiles.THORN_WIRE.becomes, tiles.CUT_WIRE)
        h.hp = 0
        run(b, config.GARDENER[6] + 0.2)                     # (it withers)
        self.assertFalse(any(b.world.tile_at(x, y) is tiles.THORN_WIRE for x, y in wire))

    def test_the_nanny_pens_you_sings_and_mends(self):
        n = awake("nanny", 25.5, 15.5)
        hurt = awake("butler", 22.5, 19.5, seed=3)
        hurt.hp = hurt.max_hp * 0.5
        a = arena(n, hurt, hero_at=(28.5, 15.5))
        n.song_t = 99.0
        hurt.cooldown = 99.0
        n.mend_t = 0.0
        run(a, DT * 2)
        self.assertGreater(hurt.hp, hurt.max_hp * 0.5)       # (mended)
        self.assertTrue(until(a, lambda: n.state == "reach", 2.0))
        run(a, n.espec.windup + 0.05)
        hx, hy = math.floor(a.hero.x) + 0.5, math.floor(a.hero.y) + 0.5
        pen = [(x, y) for y in range(10, 22) for x in range(20, 36)
               if a.world.tile_at(x, y) is tiles.PLAYPEN]
        self.assertGreater(len(pen), 8)
        for x, y in pen:                                     # (a closed ring round you)
            self.assertEqual(max(abs(x - math.floor(hx)), abs(y - math.floor(hy))), config.NANNY[0])
        self.assertTrue(any(getattr(e, "label", "") == "TIME OUT!" for e in a.effects))
        m = awake("nanny", 25.5, 15.5)
        b = arena(m, hero_at=(28.5, 15.5))
        m.cooldown, m.song_t = 99.0, 0.0
        self.assertTrue(until(b, lambda: m.state == "sing", 1.0))
        run(b, 0.2)
        self.assertGreater(b.hero.slow_t, 0.0)
        self.assertEqual(b.hero.slow_mult, config.NANNY[5])


class ScrapTest(unittest.TestCase):
    def test_a_junker_lies_there_then_falls_apart_into_pieces(self):
        j = enemy("junker", 20.5, 15.5)
        j.spawn_id = (0, 0, 1)
        j.settle(TestMap(["." * 4] * 4))
        self.assertTrue(j.dormant)
        a = arena(j, hero_at=(30.5, 15.5))
        run(a, 0.5)
        self.assertTrue(j.dormant)
        self.assertIsNone(j.seeing)                          # (a wreck sees nothing)
        j.take_damage(1.0, a.hero, 0.0)                      # (shot: it gets up)
        run(a, 0.1)
        self.assertFalse(j.dormant)
        j.hp = 0
        run(a, DT)
        bits = [e for e in a.enemies if isinstance(e, P.JunkBit)]
        self.assertIn(len(bits), (2, 3))
        k = enemy("junker", 20.5, 15.5)
        k.spawn_id = (0, 0, 2)
        k.settle(a.world)
        b = arena(k, hero_at=(20.5 + config.WORKER_NOTICE[1] - 0.5, 15.5))
        run(b, 0.1)
        self.assertFalse(k.dormant)                          # (you came near)

    def test_the_magnet_pulls_you_and_bends_your_shots_then_bursts(self):
        from ascii_adventurers.systems import patterns
        m = awake("magnet", 20.5, 15.5)
        a = arena(m, hero_at=(28.5, 15.5))
        self.assertTrue(until(a, lambda: m.state == "pull", 2.0))
        d0 = m.dist_to(a.hero)
        shot = patterns.shoot(a.hero, 24.5, 10.5, 0.0, config.PANOPTICON_SHOTS["drone_bolt"],
                              a.projectiles)
        run(a, 0.5)
        self.assertLess(m.dist_to(a.hero), d0 - 0.5)         # (drawn in)
        self.assertGreater(shot.angle, 0.05)                 # (bent toward it)
        run(a, config.MAGNET[0])
        self.assertEqual(m.state, "walk")
        self.assertTrue(any(p.spec is config.PANOPTICON_SHOTS["shrapnel"] for p in a.projectiles)
                        or a.hero.hp < a.hero.max_hp)

    def test_the_rust_swarm_shrugs_off_single_hits_and_rusts_you(self):
        r = enemy("rust_swarm", 20.5, 15.5)
        a = arena(r, hero_at=(26.5, 15.5))
        hp = r.hp
        r.take_damage(100.0, a.hero, 0.0)
        self.assertAlmostEqual(hp - r.hp, 100.0 * config.RUST[1], delta=0.5)
        hp = r.hp
        r.take_damage(20.0, a.hero, None)                    # (a blast)
        self.assertAlmostEqual(hp - r.hp, 20.0 * config.RUST[2], delta=0.5)
        a.hero.x = r.x + 1.0
        run(a, 0.6)
        self.assertGreater(a.hero.rust_until, a.hero.time)
        self.assertLess(a.hero.hp, a.hero.max_hp)

    def test_the_colossus_throws_wrecks_sheds_junkers_mends_and_slams(self):
        c = awake("scrap_colossus", 15.5, 15.5)
        a = arena(c, hero_at=(26.5, 15.5))
        c.throw_t = 0.0
        self.assertTrue(until(a, lambda: bool(c.lobs), 1.5))
        x1, y1 = c.lobs[0][2], c.lobs[0][3]
        a.hero.x, a.hero.y = 45.5, 25.5
        run(a, config.COLOSSUS[3] + 0.1)
        self.assertIs(a.world.tile_at(math.floor(x1), math.floor(y1)), tiles.LOOSE_SCRAP)
        c.hp = c.max_hp * 0.78
        run(a, DT * 2)
        self.assertTrue(any(isinstance(e, P.Junker) and not e.dormant for e in a.enemies))   # (shed)
        c.hp = c.max_hp * 0.5
        c.mend_cd = 0.0
        tx, ty = math.floor(c.x) + 3, math.floor(c.y)
        a.world.set_tile(tx, ty, tiles.WRECK)
        hp = c.hp
        self.assertTrue(until(a, lambda: c.hp > hp, 4.0))
        self.assertIsNot(a.world.tile_at(tx, ty), tiles.WRECK)
        d = awake("scrap_colossus", 25.5, 15.5)
        b = arena(d, hero_at=(28.5, 15.5))
        d.throw_t = 99.0
        self.assertTrue(until(b, lambda: d.state == "slam", 1.5))
        run(b, d.espec.windup + 0.05)
        self.assertLess(b.hero.hp, b.hero.max_hp)
        self.assertGreater(b.hero.slow_t, 0.0)               # (the ground shook)


if __name__ == "__main__":
    unittest.main()
