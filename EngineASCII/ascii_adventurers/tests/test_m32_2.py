"""M32.2: Panopticon's alert and its first eight machines (design/OCEAN.md
36-37): the city-wide meter and its three levels (calls, turrets waking,
gates sealing, the hunter squad, the cleaning on your street), the cameras
and turrets, the watch (sentry drone, spotter, riot robot, warden) and the
workers (welder, hauler, assembler, foreman); each in its own district."""

import math
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.ai import KINDS
from ascii_adventurers.ai import panopticon as P
from ascii_adventurers.ai.brain import AIContext
from ascii_adventurers.render import panopticon_art  # noqa: F401
from ascii_adventurers.render.characters import ART
from ascii_adventurers.systems import alert
from ascii_adventurers.systems.zones import update_zones
from ascii_adventurers.tests.test_p7 import Arena, enemy
from ascii_adventurers.world import tiles
from ascii_adventurers.world.chunked import ChunkedWorld
from ascii_adventurers.world.layout import IslandLayout
from ascii_adventurers.world.panopticon import DOCKS, FACTORY, HOMES, SCRAPYARD, TOWER
from ascii_adventurers.world.zones import plan_of

WATCH = ("sentry_drone", "spotter", "riot_robot", "warden")
WORKERS = ("welder", "hauler", "assembler", "foreman")
EYES = ("camera", "turret", "built_turret")
DT = 1 / 60


def pan(seed=31):
    lay = IslandLayout(seed)
    return lay, lay.zone("panopticon"), plan_of(lay, lay.zone("panopticon"))


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


def ctx_of(a):
    return AIContext(a.world, [a.hero], a.actors(), a.projectiles, a.effects, zones=a.zones)


def level(a, lv):
    alert.alert_of(a.world).level = lv


class CatalogTest(unittest.TestCase):
    def test_the_eight_and_the_eyes_each_with_its_picture_and_page(self):
        for key in WATCH + WORKERS + EYES:
            spec = config.ENEMIES[key]
            self.assertIn(spec.kind, KINDS, key)
            self.assertTrue(issubclass(KINDS[spec.kind], P.Machine), key)
            self.assertIn(key, config.BESTIARY, key)
            self.assertIn(spec.sprite, ART, key)
            self.assertEqual(len(ART[spec.sprite]), 18)
            self.assertTrue(all(len(r) == 14 for r in ART[spec.sprite]), key)
        for key in WATCH + WORKERS:
            self.assertEqual(config.ENEMIES[key].biomes, ("panopticon",), key)
        for key in EYES:                                    # (they live at fixed places)
            self.assertEqual(config.ENEMIES[key].biomes, (), key)
        for name in ("turret_shut", "hauler_empty", "foreman_shout"):
            self.assertIn(name, ART)
        self.assertEqual({k for k in WATCH + WORKERS if config.ENEMIES[k].elite}, {"warden", "foreman"})
        self.assertGreater(config.BIOME_ENEMY_DENSITY["panopticon"], 0)
        groups = {k: KINDS[config.ENEMIES[k].kind].group for k in WATCH + WORKERS}
        self.assertEqual({groups[k] for k in WATCH}, {"watch"})
        self.assertEqual({groups[k] for k in WORKERS}, {"workers"})
        self.assertTrue(all(KINDS[config.ENEMIES[k].kind].worker for k in WORKERS))

    def test_the_eyes_fill_it_fastest(self):
        eyes = config.ALERT_EYES
        self.assertEqual(KINDS["camera"].eye, "camera")
        self.assertEqual(KINDS["spotter"].eye, "spotter")
        self.assertEqual(KINDS["riot_robot"].eye, "watch")
        self.assertEqual(KINDS["welder"].eye, "machine")
        self.assertGreater(eyes["spotter"], eyes["watch"])
        self.assertGreater(eyes["watch"], eyes["machine"])
        self.assertEqual((eyes["camera"], eyes["machine"]), (20.0, 6.0))   # (the draft's ~20 and ~6)


class PlanTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = ChunkedWorld(31)
        cls.z = cls.w.layout.zone("panopticon")
        cls.p = plan_of(cls.w.layout, cls.z)

    def test_cameras_at_street_corners_more_near_the_tower(self):
        p, z, w = self.p, self.z, self.w
        cams = p.camera_spots()
        self.assertGreater(len(cams), 60)
        self.assertIs(cams, p.camera_spots())               # (worked out once)
        for x, y, fx, fy in cams[::9]:
            w.ensure_ready(math.floor(x) - 2, math.floor(y) - 2, math.floor(x) + 3, math.floor(y) + 3)
            t = w.tile_at(math.floor(x), math.floor(y))
            self.assertFalse(t.solid, (x, y, t.name))
            self.assertIn(t, (tiles.STREET, tiles.PAVEMENT, tiles.LANE_LINE), (x, y, t.name))
            self.assertAlmostEqual(math.hypot(fx, fy), 1.0, places=6)
            self.assertNotEqual(p.district_at(x, y), TOWER)
        cx, cy, a, b = p.hall
        mid = (p.plaza + (a + b) / 2 + z.radius) / 2
        inner = [c for c in cams if math.hypot(c[0] - cx, c[1] - cy) < mid]
        outer = [c for c in cams if math.hypot(c[0] - cx, c[1] - cy) >= mid]
        r0 = p.plaza + (a + b) / 2
        area_in = math.pi * (mid ** 2 - r0 ** 2)
        area_out = math.pi * (z.radius ** 2 - mid ** 2)
        self.assertGreater(len(inner) / area_in, 1.5 * len(outer) / area_out)

    def test_turrets_against_the_blocks_walls(self):
        p, w = self.p, self.w
        spots = p.turret_spots()
        self.assertGreater(len(spots), 40)
        for x, y, fx, fy in spots[::7]:
            tx, ty = math.floor(x), math.floor(y)
            w.ensure_ready(tx - 3, ty - 3, tx + 4, ty + 4)
            self.assertFalse(w.tile_at(tx, ty).solid, (x, y))
            behind = w.tile_at(math.floor(x - fx), math.floor(y - fy))
            self.assertTrue(behind.solid, (x, y, behind.name))   # (its block's wall)

    def test_each_district_its_six_gates(self):
        p = self.p
        seen = {}
        for name in (DOCKS, FACTORY, SCRAPYARD, HOMES):
            gates = p.district_gates(name)
            self.assertEqual(len(gates), 6, name)
            for i in gates:
                self.assertEqual(p.fences[i].kind, "blink")
                seen.setdefault(i, []).append(name)
        self.assertEqual(len(seen), 12)
        self.assertTrue(all(len(v) == 2 for v in seen.values()))   # (each wall's: both sides')
        self.assertEqual(p.district_gates(TOWER), [])

    def test_the_cameras_turrets_and_the_factory_s_crew_live_there(self):
        p, w = self.p, self.w
        res = P.residents(w.layout, self.z)
        keys = [k for k, _, _ in res]
        self.assertGreater(keys.count("camera"), len(p.camera_spots()) * 0.9)
        self.assertGreater(keys.count("turret"), len(p.turret_spots()) * 0.9)
        quiet = [m for m in p.marks if m.key in config.ZONE_QUIET_MARKS]
        self.assertEqual(len(quiet), 2)
        for k, x, y in res:                                 # (none by the sea wall or the tower)
            self.assertFalse(any(m.contains(x, y, config.LANDMARK_QUIET) for m in quiet), (k, x, y))
        self.assertEqual(keys.count("foreman"), 1)
        fac = next(m for m in p.marks if m.key == "panopticon_factory")
        chassis = fac.props["chassis"]
        self.assertEqual(len(chassis), 9)
        w.ensure_ready(p.factory[0] - 40, p.factory[1] - 24, p.factory[0] + 40, p.factory[1] + 24)
        on = [(k, x, y) for k, x, y in res
              if w.tile_at(math.floor(x), math.floor(y)) is tiles.CHASSIS]
        self.assertEqual(len(on), 9)
        self.assertTrue(all(k in WORKERS for k, _, _ in on))
        for x, y in fac.props["arms"]:                      # (a welder's spot by each arm: floor)
            self.assertIs(w.tile_at(math.floor(x), math.floor(y)), tiles.FACTORY_FLOOR)
        self.assertEqual(P.residents(w.layout, w.layout.zone("pangaea")), [])


class SpawnTest(unittest.TestCase):
    def test_each_in_its_own_district_the_patrols_everywhere(self):
        from ascii_adventurers.systems.spawner import Spawner
        w = ChunkedWorld(31)
        p = plan_of(w.layout, w.layout.zone("panopticon"))
        sp = Spawner(w, 31)
        n = config.CHUNK_SIZE
        got = {name: set() for name in (DOCKS, FACTORY, SCRAPYARD, HOMES)}
        for k, name in enumerate(p.names):
            ax, ay = p.axes[k]
            for r in range(130, 290, 32):
                for side in (-1, 0, 1):
                    x = p.cx + ax * r - ay * side * 40
                    y = p.cy + ay * r + ax * side * 40
                    for sid, key, ex, ey in sp.roster(math.floor(x) // n, math.floor(y) // n):
                        if key in config.PANOPTICON_DISTRICT_OF:
                            self.assertIn(p.district_at(ex, ey), config.PANOPTICON_DISTRICT_OF[key],
                                          (key, ex, ey))
                        got[p.district_at(ex, ey)].add(key) if p.district_at(ex, ey) in got else None
        self.assertTrue({"riot_robot", "sentry_drone"} <= got[DOCKS], got[DOCKS])
        self.assertTrue({"welder"} <= got[FACTORY], got[FACTORY])
        for name in (SCRAPYARD, HOMES):                     # (M32.3: their own groups)
            self.assertTrue(got[name] & {"sentry_drone", "spotter"}, name)
            self.assertFalse(got[name] & set(config.PANOPTICON_DISTRICT_OF), name)

    def test_a_half_built_robot_lies_there_until_you_come_close(self):
        w = ChunkedWorld(31)
        p = plan_of(w.layout, w.layout.zone("panopticon"))
        fac = next(m for m in p.marks if m.key == "panopticon_factory")
        x, y = fac.props["chassis"][0]
        w.ensure_ready(math.floor(x) - 20, math.floor(y) - 20, math.floor(x) + 20, math.floor(y) + 20)
        from ascii_adventurers.systems.spawner import Spawner
        e = Spawner(w, 31).wake("hauler", x, y, (0, 0, 5000))
        self.assertTrue(e.dormant)
        self.assertFalse(e.hittable)
        self.assertEqual(len(e.chassis), 4)
        a = Arena(e)
        a.world = w
        a.hero.x, a.hero.y = x + 12, y
        a.hero.hp = a.hero.max_hp = 100000
        run(a, 0.5)
        self.assertTrue(e.dormant)                          # (too far yet)
        a.hero.x = x + config.WORKER_NOTICE[1] - 0.5
        run(a, 0.2)
        self.assertFalse(e.dormant)
        self.assertTrue(e.hittable)
        self.assertTrue(all(w.tile_at(tx, ty) is tiles.FACTORY_FLOOR
                            for tx, ty in ((math.floor(x) - 1, math.floor(y) - 1),
                                           (math.floor(x), math.floor(y)))))
        e2 = Spawner(w, 31).wake("hauler", x, y, (0, 0, 5001))   # (woken again later: no robot left)
        self.assertFalse(e2.dormant)


def _game():
    from ascii_adventurers.tests.test_m16 import game
    m, s = game("wizard", seed=31)
    s.app.dev = True
    for _ in range(4):                                       # (to Panopticon)
        s._dev_zone()
    return m, s


class AlertTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m, cls.s = _game()
        lay = cls.s.world.layout
        cls.p = plan_of(lay, lay.zone("panopticon"))
        cls.s.spawner.update_views = lambda *a, **kw: None  # (only what the tests put there)

    def setUp(self):
        s = self.s
        s.enemies.clear()
        s.projectiles.clear()
        s.city.sweeps.clear()
        s.city.next.clear()
        s.world.city_alert = alert.Alert()
        s.hero.hp = s.hero.max_hp = 100000
        s.quests.banner = None

    def go_docks(self):
        """To a docks street, off the plaza (a turret's pavement spot)."""
        from ascii_adventurers.tests.test_m17 import teleport
        p = self.p
        spots = sorted((c for c in p.turret_spots() if p.district_at(c[0], c[1]) == DOCKS),
                       key=lambda c: math.hypot(c[0] - p.cx, c[1] - p.cy))
        x, y, fx, fy = spots[len(spots) // 2]
        teleport(self.s, x + fx, y + fy)
        return self.s.hero

    def step(self, secs, see=0.0):
        from ascii_adventurers.tests.test_m17 import step
        for _ in range(round(secs * 60)):
            if see:
                alert.seen(self.s.world, see)
            step(self.s)

    def test_seen_it_rises_by_the_fastest_eye_and_cools_after_quiet(self):
        s = self.s
        self.go_docks()
        a = alert.alert_of(s.world)
        self.step(1.0, see=20.0)
        self.assertAlmostEqual(a.meter, 20.0, delta=1.0)
        self.assertEqual(a.level, alert.CALM)
        alert.seen(s.world, 6.0)
        alert.seen(s.world, 20.0)                          # (the fastest eye counts, not the sum)
        self.assertEqual(a.rate, 20.0)
        self.step(0.6, see=20.0)
        self.assertEqual(a.level, alert.SEARCH)
        m = a.meter
        self.step(2.8)                                      # (quiet, but not long enough yet)
        self.assertAlmostEqual(a.meter, m, delta=0.01)
        self.step(1.0)
        self.assertAlmostEqual(a.meter, m - config.PANOPTICON_ALERT[3] * 0.8, delta=1.5)
        self.step(3.0)
        self.assertEqual(a.level, alert.CALM)
        self.assertEqual(s.hero.alert_hud[0], alert.CALM)

    def test_lockdown_seals_your_gates_sends_hunters_and_cleans_your_street(self):
        s, p = self.s, self.p
        h = self.go_docks()
        a = alert.alert_of(s.world)
        self.step(0.2, see=1000.0)
        self.assertEqual(a.level, alert.LOCKDOWN)
        self.assertEqual(a.lockdowns, 1)
        self.assertEqual(set(a.sealed), set(p.district_gates(DOCKS)))
        kinds = sorted(e.kind_key for e in a.hunters)
        self.assertEqual(kinds, sorted(config.PANOPTICON_SQUAD[1]))
        for e in a.hunters:
            self.assertIn(e, s.enemies)
            self.assertTrue(e.alert and e.hunter)
            self.assertAlmostEqual(math.hypot(e.x - h.x, e.y - h.y), config.PANOPTICON_SQUAD[0], delta=4.0)
            self.assertTrue(e.zone_tough)
        self.assertEqual(len(s.city.sweeps), 1)            # (the cleaning, on your street)
        s.enemies.clear()                                   # (nothing sees you now)
        self.step(config.PANOPTICON_ALERT[4] - 0.5)
        self.assertEqual(a.level, alert.LOCKDOWN)           # (it holds, full)
        self.assertEqual(a.meter, config.PANOPTICON_ALERT[0])
        self.step(0.5 + config.PANOPTICON_ALERT[2] + 1.0)
        self.assertEqual(a.level, alert.SEARCH)
        self.step(config.PANOPTICON_ALERT[5])
        self.assertEqual(a.sealed, {})                      # (the gates open again)
        self.step(0.1, see=1000.0)
        self.assertEqual(a.lockdowns, 2)

    def test_a_sealed_gate_bars_the_way(self):
        from ascii_adventurers.systems import panopticon as pc
        from ascii_adventurers.tests.test_m17 import teleport
        s, p = self.s, self.p
        i = p.district_gates(DOCKS)[0]
        f = p.fences[i]
        mx, my = (f.x0 + f.x1) / 2, (f.y0 + f.y1) / 2
        teleport(s, mx, my)
        h = s.hero
        dx, dy = f.x1 - f.x0, f.y1 - f.y0
        ll = math.hypot(dx, dy)
        nx, ny = -dy / ll, dx / ll
        sealed = {i: 10.0}
        for side in (-1, 1):
            h.x, h.y = mx + nx * side * 0.3, my + ny * side * 0.3
            hp = h.hp
            h.laser_t = 0.0
            pc._lasers(s, p, h, s.city.clock, DT, sealed)
            off = (h.x - mx) * nx + (h.y - my) * ny
            self.assertGreaterEqual(off * side, 0.74)       # (put back on its own side)
            self.assertLess(h.hp, hp)                       # (and burnt)
        self.assertEqual(pc.fence_state(p, i, 0.0, sealed)[0], "sealed")
        self.assertNotEqual(pc.fence_state(p, i, 0.0, {})[0], "sealed")

    def test_the_hud_shows_it_by_level_and_lockdown_pulses_the_edge(self):
        import pygame
        from ascii_adventurers.render.panopticon import draw_lockdown
        from ascii_adventurers.ui.hud import HudInfo, draw_hud
        s = self.s
        self.go_docks()
        self.step(2.0, see=20.0)
        meter = s._meter(s.hero)
        self.assertEqual(meter[0], "ALR")
        self.assertEqual(meter[3], "SEARCH")
        self.assertAlmostEqual(meter[1], 0.4, delta=0.02)
        draw_hud(self.m.text, HudInfo(hp=10, max_hp=10, level=1, xp_frac=0, kills=0, time=0, meter=meter))
        canvas = self.m.display.canvas
        canvas.fill((0, 0, 0))
        draw_lockdown(canvas, s, s.hero)
        self.assertEqual(canvas.get_at((0, canvas.get_height() // 2))[:3], (0, 0, 0))   # (not yet)
        self.step(0.2, see=1000.0)
        canvas.fill((0, 0, 0))
        draw_lockdown(canvas, s, s.hero)
        self.assertNotEqual(canvas.get_at((0, canvas.get_height() // 2))[:3], (0, 0, 0))
        self.assertEqual(s._meter(s.hero)[3], "LOCKDOWN")
        from ascii_adventurers.tests.test_m17 import teleport
        teleport(s, 0.5, 0.5)                               # (off the island: no meter)
        self.step(0.1)
        self.assertIsNone(s.hero.alert_hud)

    def test_the_belts_carry_the_machines_but_not_the_drones(self):
        from ascii_adventurers.systems import panopticon as pc
        s, p = self.s, self.p
        found = None
        x0, y0 = p.factory
        s.world.ensure_ready(x0 - 40, y0 - 24, x0 + 40, y0 + 24)
        for y in range(y0 - 18, y0 + 18):
            for x in range(x0 - 30, x0 + 30):
                if s.world.tile_at(x, y) in tiles.BELTS:
                    found = (x, y)
                    break
            if found:
                break
        from ascii_adventurers.tests.test_m17 import teleport
        teleport(s, found[0] + 0.5, found[1] + 6.5)
        r = enemy("riot_robot", found[0] + 0.5, found[1] + 0.5)
        d = enemy("sentry_drone", found[0] + 0.5, found[1] + 0.5)
        s.enemies[:] = [r, d]
        pc._carry(s, 0.5)
        bx, by = tiles.BELTS[s.world.tile_at(*found)]
        self.assertGreater((r.x - found[0] - 0.5) * bx + (r.y - found[1] - 0.5) * by, 1.0)
        self.assertEqual((d.x, d.y), (found[0] + 0.5, found[1] + 0.5))

    def test_draws_the_machines_and_their_tells(self):
        s = self.s
        h = self.go_docks()
        sp = s.spawner
        for k, key in enumerate(WATCH + WORKERS + EYES):
            a = k * math.tau / 11
            e = sp.wake(key, h.x + math.cos(a) * 6, h.y + math.sin(a) * 4, None, random.Random(k))
            s.enemies.append(e)
        self.step(1.0, see=40.0)
        s.draw(self.m.text)
        self.step(0.5, see=1000.0)
        s.draw(self.m.text)


class EyesTest(unittest.TestCase):
    def test_a_camera_sees_its_cone_then_follows_you(self):
        cam = enemy("camera", 20.5, 15.5)
        cam.base = cam.facing = 0.0
        a = arena(cam, hero_at=(27.5, 15.5))
        self.assertTrue(until(a, lambda: cam.seeing is a.hero, 0.5))
        self.assertGreaterEqual(alert.alert_of(a.world).rate, config.ALERT_EYES["camera"])
        a.hero.x, a.hero.y = 25.5, 21.5                    # (out of its cone, still in reach)
        run(a, 0.5)
        self.assertIs(cam.seeing, a.hero)                   # (it follows you)
        self.assertGreater(cam.facing, 0.3)
        a.hero.x, a.hero.y = 45.5, 15.5                    # (out of reach)
        run(a, 0.5)
        self.assertIsNone(cam.seeing)
        cam2 = enemy("camera", 20.5, 15.5)
        cam2.base = cam2.facing = math.pi                   # (facing away)
        b = arena(cam2, hero_at=(27.5, 15.5))
        run(b, 1.0)
        self.assertIsNone(cam2.seeing)

    def test_turrets_sleep_until_the_city_searches(self):
        t = enemy("turret", 20.5, 15.5)
        a = arena(t, hero_at=(28.5, 15.5))
        run(a, 3.0)
        self.assertFalse(t.armed)
        self.assertEqual(a.projectiles, [])
        level(a, alert.SEARCH)
        run(a, 1.5)
        self.assertTrue(t.armed)
        self.assertTrue(any(p.spec is config.PANOPTICON_SHOTS["turret_bolt"] for p in a.projectiles)
                        or a.hero.hp < a.hero.max_hp)
        b = arena(enemy("built_turret", 20.5, 15.5), hero_at=(28.5, 15.5))
        run(b, 1.5)                                         # (an assembler's: always open)
        self.assertTrue(b.projectiles or b.hero.hp < b.hero.max_hp)


class WatchTest(unittest.TestCase):
    def test_a_drone_sees_only_what_s_in_its_light_and_fires_bursts(self):
        d = enemy("sentry_drone", 20.5, 15.5)
        d.heading = math.pi                                 # (its light away from you)
        d.route = [(20.5, 15.5), (20.5, 15.5)]
        a = arena(d, hero_at=(27.5, 15.5))
        a.hero.hp = a.hero.max_hp = 100000
        d.turn_to_heading = lambda *x: None                 # (held facing away)
        run(a, 1.0)
        self.assertIsNone(d.prey)
        del d.turn_to_heading
        d.heading = 0.0
        self.assertTrue(until(a, lambda: d.prey is a.hero, 1.0))
        self.assertGreaterEqual(alert.alert_of(a.world).rate, config.ALERT_EYES["watch"])
        run(a, 2.5)
        bolts = [p for p in a.projectiles if p.spec is config.PANOPTICON_SHOTS["drone_bolt"]] \
            or a.hero.hp < a.hero.max_hp
        self.assertTrue(bolts)

    def test_the_spotter_watches_from_afar_and_hides_when_you_come(self):
        walls = [(x, 10) for x in range(14, 27)] + [(x, 20) for x in range(14, 27)]
        sp = enemy("spotter", 18.5, 15.5)
        a = arena(sp, hero_at=(30.5, 15.5), walls=walls)
        self.assertTrue(until(a, lambda: sp.seeing is a.hero, 1.0))
        self.assertEqual(alert.alert_of(a.world).rate, config.ALERT_EYES["spotter"])
        self.assertEqual(config.ENEMIES["spotter"].damage, 0)
        a.hero.x = sp.x + 4.0
        self.assertTrue(until(a, lambda: sp.state == "hide", 1.0))
        from ascii_adventurers.ai.panopticon import _clear
        self.assertIsNotNone(sp.hide_at)
        self.assertFalse(_clear(a.world, a.hero.x, a.hero.y, *sp.hide_at))   # (out of your sight)

    def test_the_riot_shield_blocks_the_front_and_its_charges_daze(self):
        r = enemy("riot_robot", 20.5, 15.5)
        r.facing = 0.0
        a = arena(r, hero_at=(28.5, 15.5))
        hp = r.hp
        r.take_damage(50.0, a.hero, math.pi)                # (from the front: it travels west)
        self.assertEqual(r.hp, hp)
        r.take_damage(50.0, a.hero, 0.0)                    # (from behind)
        self.assertLess(r.hp, hp)
        r.charge_t = 0.0
        r.facing = 0.0
        self.assertTrue(until(a, lambda: bool(r.lobs), 1.0))
        run(a, config.RIOT[7] + 0.1)
        self.assertGreater(a.hero.slow_t, 0.0)              # (dazed: rooted...)
        self.assertGreater(a.hero.dazzled, 0.0)             # (...aim wavering)
        self.assertLess(a.hero.hp, a.hero.max_hp)

    def test_the_warden_marks_you_holds_lockdown_and_tethers(self):
        w = enemy("warden", 20.5, 15.5)
        a = arena(w, hero_at=(30.5, 15.5))
        run(a, 0.5)
        self.assertFalse(w.marked)                          # (its eye on you first)
        self.assertIs(w.marking, a.hero)
        run(a, config.WARDEN_MARK)
        self.assertTrue(w.marked)
        self.assertTrue(any(getattr(e, "label", "") == "TARGET MARKED" for e in a.effects))
        self.assertGreater(alert.alert_of(a.world).held, 0.0)
        w.state, w.timer = "beam", config.WARDEN[5]          # (a beam ending: back to its walk)
        run(a, DT)
        self.assertEqual((w.state, w.timer), ("walk", 0.0))
        w._chain(a.hero, w)
        a.hero.x += 4.0
        run(a, DT)
        ax, ay = w.chained[1], w.chained[2]
        self.assertLessEqual(math.hypot(a.hero.x - ax, a.hero.y - ay), config.WARDEN[11] + 0.05)
        a.hero.roll_t = 0.3                                 # (a roll frees you)
        run(a, DT)
        self.assertIsNone(w.chained)
        w.hp = 0
        run(a, DT)
        g = alert.alert_of(a.world)
        g.held = 0.0
        run(a, 0.2)
        self.assertEqual(g.held, 0.0)                       # (dead: it holds nothing)

    def test_the_warden_s_beam_burns_and_walls_stop_it(self):
        from ascii_adventurers.ai.panopticon import _beam_end
        a = arena(hero_at=(30.5, 15.5), walls=[(26, y) for y in range(10, 21)])
        self.assertAlmostEqual(_beam_end(a.world, 20.5, 15.5, 0.0, 14.0), 5.5, delta=0.6)
        self.assertEqual(_beam_end(a.world, 20.5, 15.5, math.pi, 14.0), 14.0)
        w = enemy("warden", 22.5, 15.5)
        b = arena(w, hero_at=(30.5, 15.5))
        w.state, w.timer = "beam", 0.0
        w.beam_from = w.beam_to = 0.0
        run(b, 0.6)
        self.assertLess(b.hero.hp, b.hero.max_hp)

    def test_machines_call_each_other_in_search(self):
        cam = enemy("camera", 20.5, 15.5)
        cam.base = cam.facing = 0.0
        r = enemy("riot_robot", 10.5, 25.5)
        r.alert = False
        a = arena(cam, r, hero_at=(27.5, 15.5))
        run(a, 0.6)
        self.assertFalse(r.alert)                           # (calm: no calls)
        level(a, alert.SEARCH)
        cam.call_t = 0.0
        self.assertTrue(until(a, lambda: r.alert, 1.0))
        self.assertAlmostEqual(r.last_known[0], a.hero.x, delta=1.0)


class WorkersTest(unittest.TestCase):
    def test_workers_work_until_you_come_near(self):
        e = enemy("welder", 20.5, 15.5)
        e.alert = False
        self.assertTrue(e.working)
        a = arena(e, hero_at=(34.5, 15.5))
        run(a, 1.0)
        self.assertTrue(e.working)
        a.hero.x = 20.5 + config.WORKER_NOTICE[0] - 1.0
        run(a, 0.2)
        self.assertFalse(e.working)
        self.assertTrue(e.alert)

    def test_the_welder_drags_its_torch_across_you_and_leaves_slag(self):
        e = enemy("welder", 20.5, 15.5)
        e.working = False
        a = arena(e, hero_at=(22.5, 15.5))
        self.assertTrue(until(a, lambda: e.state == "drag", 2.0))
        run(a, config.WELDER[2] + 0.05)
        self.assertLess(a.hero.hp, a.hero.max_hp)
        slag = [z for z in a.zones if z.kind == "slag"]
        self.assertEqual(len(slag), config.WELDER[3])
        self.assertTrue(all(z.source is e for z in slag))

    def test_the_hauler_charges_throws_its_crate_and_leaves_cover(self):
        e = enemy("hauler", 15.5, 15.5)
        e.working = False
        a = arena(e, hero_at=(26.5, 15.5))
        self.assertTrue(until(a, lambda: e.state == "line", 2.0))
        self.assertTrue(until(a, lambda: e.state == "charge", 2.0))
        self.assertTrue(until(a, lambda: not e.crate, 3.0))
        x1, y1 = e.lobs[0][2], e.lobs[0][3]
        a.hero.x, a.hero.y = 45.5, 25.5                     # (out of the way)
        run(a, config.HAULER[6] + 0.1)
        self.assertIs(a.world.tile_at(math.floor(x1), math.floor(y1)), tiles.BROKEN_CRATE)
        self.assertTrue(tiles.BROKEN_CRATE.solid and tiles.BROKEN_CRATE.blocks_shots
                        and tiles.BROKEN_CRATE.destructible)
        self.assertTrue(any(p.spec is config.PANOPTICON_SHOTS["shrapnel"] for p in a.projectiles))
        run(a, config.HAULER[10] + 0.2)
        self.assertTrue(e.crate)                            # (it fetched another)

    def test_the_assembler_builds_a_turret_unless_you_kill_it_first(self):
        e = enemy("assembler", 20.5, 15.5)
        e.working = False
        a = arena(e, hero_at=(28.5, 15.5))
        self.assertTrue(until(a, lambda: e.state == "build", 1.0))
        run(a, config.ENEMIES["assembler"].windup + 0.1)
        built = [m for m in a.enemies if isinstance(m, P.Turret) and m.built]
        self.assertEqual(len(built), 1)
        f = enemy("assembler", 20.5, 15.5)
        f.working = False
        b = arena(f, hero_at=(28.5, 15.5))
        self.assertTrue(until(b, lambda: f.state == "build", 1.0))
        run(b, 2.0)
        f.hp = 0
        run(b, 3.0)
        self.assertFalse([m for m in b.enemies if isinstance(m, P.Turret)])

    def test_the_foreman_orders_overtime_calls_presses_and_barks(self):
        fm = enemy("foreman", 20.5, 15.5)
        fm.working = False
        wd = enemy("welder", 16.5, 15.5)
        wd.working = False
        a = arena(fm, wd, hero_at=(27.5, 15.5))
        fm.overtime_t = 0.0
        run(a, 0.1)
        self.assertGreater(wd.overtime, 0.0)
        self.assertTrue(any(getattr(e, "label", "") == "OVERTIME!" for e in a.effects))
        fm.cooldown = 0.0
        self.assertTrue(until(a, lambda: bool(fm.drops), 1.5))
        self.assertEqual(len(fm.drops), config.FOREMAN[6])
        hx, hy = a.hero.x, a.hero.y
        self.assertTrue(any(math.hypot(x - hx, y - hy) < 0.5 for x, y, _ in fm.drops))   # (one on you)
        hp = a.hero.hp
        run(a, config.FOREMAN[8] + 0.05)
        self.assertLess(a.hero.hp, hp)
        g = enemy("foreman", 20.5, 15.5)
        g.working = False
        b = arena(g, hero_at=(23.5, 15.5))
        g.cooldown = 99.0
        self.assertTrue(until(b, lambda: bool(g.rings), 1.5))
        hp = b.hero.hp
        run(b, 0.6)
        self.assertLess(b.hero.hp, hp)


if __name__ == "__main__":
    unittest.main()
