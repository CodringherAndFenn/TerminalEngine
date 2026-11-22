"""M29.2: Paradise's first eight enemies and the unveiling (design/OCEAN.md 4):
serene -> unveiled, the blood they leave, the fonts, the zone's toughness."""

import math
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.ai import KINDS, make_enemy
from ascii_adventurers.ai.paradise import Angel, Dove, fonts, pool, stain
from ascii_adventurers.render import paradise_art  # noqa: F401
from ascii_adventurers.render.characters import ART
from ascii_adventurers.systems.spawner import PACK_ID, Spawner
from ascii_adventurers.systems.zones import update_zones
from ascii_adventurers.tests.test_p7 import Arena, enemy
from ascii_adventurers.world import biomes, tiles
from ascii_adventurers.world.chunked import ChunkedWorld
from ascii_adventurers.world.paradise import plan_of
from ascii_adventurers.world.test_map import TestMap

NEW = ("cherub", "seraph", "ophan", "watcher", "lamb", "dove", "locust", "halo")


def paradise_map(w=60, h=30, walls=()):
    """Cloud ground (it stains), columns at `walls`, no fonts."""
    rows = [["."] * w for _ in range(h)]
    for x, y in walls:
        rows[y][x] = "#"
    m = TestMap(["".join(r) for r in rows], legend={".": tiles.CLOUD, "#": tiles.MARBLE_COLUMN})
    m.fonts = []
    return m


def arena(*enemies, hero_at=(30.5, 15.5), walls=(), tough=True):
    a = Arena(*enemies, hero_at=hero_at)
    a.world = paradise_map(walls=walls)
    if tough:
        a.hero.hp = a.hero.max_hp = 100000
    return a


def run(a, seconds):
    for _ in range(round(seconds * 60)):
        a.run(1 / 60)
        update_zones(a.zones, a.actors(), a.effects, 1 / 60, a.world)


def stained(world, w=60, h=30):
    return sum(1 for y in range(h) for x in range(w)
               if world.tile_at(x, y).name in ("stained cloud", "soaked cloud"))


def unveiled(key, x, y, seed=1):
    e = enemy(key, x, y, seed)
    e.state = "unveiled"
    return e


class CatalogTest(unittest.TestCase):
    def test_eight_on_paradise_each_with_two_looks_and_a_page(self):
        for key in NEW:
            spec = config.ENEMIES[key]
            self.assertEqual(spec.biomes, ("paradise",), key)
            self.assertIn(spec.kind, KINDS)
            self.assertIn(key, config.BESTIARY)
            for name in (spec.sprite, spec.sprite + "_unveiled"):
                self.assertIn(name, ART, name)
                self.assertEqual(len(ART[name]), 18)
                self.assertTrue(all(len(r) == 14 for r in ART[name]), name)
        for name in ("ophan_unveiled2", "halo_unveiled2"):
            self.assertIn(name, ART)
        self.assertEqual({k for k in NEW if config.ENEMIES[k].elite}, {"seraph"})

    def test_paradise_has_enemies_now(self):
        self.assertGreater(config.BIOME_ENEMY_DENSITY["paradise"], 0)
        here = [k for k, s in config.ENEMIES.items() if "paradise" in s.biomes]
        self.assertTrue(set(NEW) <= set(here))                # (M29.3 adds more)


class UnveilingTest(unittest.TestCase):
    def test_serene_until_a_hero_comes_close(self):
        e = enemy("cherub", 10.5, 15.5)
        a = arena(e, hero_at=(30.5, 15.5))
        run(a, 0.5)
        self.assertTrue(e.serene)
        a.hero.x = e.x + config.UNVEIL[1] - 0.5
        run(a, 0.1)
        self.assertTrue(e.unveiling)
        run(a, config.UNVEIL[2])
        self.assertTrue(e.unveiled)
        self.assertTrue(any(f.kind == "unveil" for f in a.effects))

    def test_hurt_below_seventy_percent_it_unveils(self):
        e = enemy("watcher", 10.5, 15.5)
        a = arena(e, hero_at=(40.5, 15.5))
        e.take_damage(e.max_hp * 0.25, a.hero, 0.0)
        self.assertTrue(e.serene)                          # (75% left)
        e.take_damage(e.max_hp * 0.1, a.hero, 0.0)
        self.assertTrue(e.unveiling)
        run(a, config.UNVEIL[2] + 0.05)
        self.assertTrue(e.unveiled)

    def test_the_unveiling_cannot_be_stopped_or_undone(self):
        e = enemy("cherub", 10.5, 15.5)
        a = arena(e, hero_at=(13.5, 15.5))
        run(a, 0.1)
        self.assertTrue(e.unveiling)
        a.hero.x = 50.5                                     # (walking away: it goes on)
        e.hp = e.max_hp
        run(a, config.UNVEIL[2])
        self.assertTrue(e.unveiled)
        run(a, 2.0)
        self.assertTrue(e.unveiled)
        self.assertEqual(e.sprite_now(), "cherub_unveiled")

    def test_killed_serene_it_dies_clean(self):
        e = enemy("lamb", 10.5, 15.5)
        a = arena(e, hero_at=(40.5, 15.5))
        e.take_damage(e.max_hp * 2, a.hero, 0.0)
        e.on_death(_ctx(a))
        self.assertTrue(any(f.kind == "feathers" for f in a.effects))
        self.assertEqual(stained(a.world), 0)
        self.assertFalse(e.unveiled)

    def test_serene_is_slower(self):
        e = enemy("lamb", 10.5, 15.5)
        self.assertAlmostEqual(e.speed, e.espec.speed * config.UNVEIL[3])
        e.state = "unveiled"
        self.assertEqual(e.speed, e.espec.speed)

    def test_no_attack_during_the_tell(self):
        e = enemy("cherub", 10.5, 15.5)
        a = arena(e, hero_at=(11.8, 15.5))
        run(a, config.UNVEIL[2] * 0.8)
        self.assertTrue(e.unveiling)
        self.assertEqual(a.hero.hp, a.hero.max_hp)


def _ctx(a):
    from ascii_adventurers.ai.brain import AIContext
    return AIContext(a.world, [a.hero], a.actors(), a.projectiles, a.effects, zones=a.zones)


class BloodTest(unittest.TestCase):
    def test_unveiled_ones_leave_a_trail(self):
        e = unveiled("lamb", 8.5, 15.5)
        a = arena(e, hero_at=(21.5, 15.5))
        run(a, 4.0)
        self.assertGreater(stained(a.world), 2)

    def test_a_pool_where_an_unveiled_one_dies_and_stains_soak(self):
        e = unveiled("cherub", 20.5, 15.5)
        a = arena(e, hero_at=(45.5, 15.5))
        e.hp = 0.0
        e.on_death(_ctx(a))
        self.assertGreaterEqual(stained(a.world), 4)
        self.assertTrue(any(f.kind == "gore" for f in a.effects))
        self.assertIs(a.world.tile_at(20, 15), tiles.STAINED_CLOUD)
        stain(a.world, 20.5, 15.5)
        self.assertIs(a.world.tile_at(20, 15), tiles.SOAKED_CLOUD)
        self.assertFalse(stain(a.world, 20.5, 15.5))        # (soaked: as red as it gets)

    def test_only_paradise_ground_stains(self):
        a = Arena(hero_at=(5.5, 5.5))                       # (plain ground)
        self.assertFalse(stain(a.world, 10.5, 10.5))
        m = paradise_map(walls=[(10, 10)])
        self.assertFalse(stain(m, 10.5, 10.5))               # (a column)
        for ground, to in ((tiles.MARBLE_ROAD, tiles.STAINED_ROAD),
                           (tiles.MARBLE_FLOOR, tiles.STAINED_FLOOR),
                           (tiles.STEP, tiles.STAINED_STEP), (tiles.PETALS, tiles.STAINED_CLOUD)):
            m.set_tile(3, 3, ground)
            self.assertTrue(stain(m, 3.5, 3.5))
            self.assertIs(m.tile_at(3, 3), to)

    def test_stains_stay_on_the_island(self):
        w = ChunkedWorld(31)
        z = w.layout.zone("paradise")
        x, y = z.cx + 30, z.cy + 140
        w.ensure_ready(x - 4, y - 4, x + 4, y + 4)
        n = pool(w, x + 0.5, y + 0.5, 2.0)
        self.assertGreater(n, 0)
        got = {w.tile_at(x + dx, y + dy).name for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
        self.assertTrue(got & {"stained cloud", "soaked cloud", "stained marble", "stained step"})
        key = (x >> 5, y >> 5)
        self.assertIn(key, w._changes)                       # (re-applied if it reloads)


class FontTest(unittest.TestCase):
    def test_hurt_and_unveiled_it_goes_to_drink_and_heals(self):
        e = unveiled("cherub", 10.5, 15.5)
        a = arena(e, hero_at=(55.5, 5.5))
        a.world.fonts = [(30.5, 15.0)]
        e.hp = e.max_hp * 0.3
        run(a, 5.0)
        self.assertLess(math.hypot(e.x - 30.5, e.y - 15.0), config.FONT[2] + 0.5)
        self.assertTrue(e.drinking)
        run(a, 9.0)
        self.assertGreaterEqual(e.hp, e.max_hp * (config.FONT[4] - 0.02))

    def test_no_font_near_no_drinking(self):
        e = unveiled("cherub", 10.5, 15.5)
        a = arena(e, hero_at=(55.5, 25.5))
        a.world.fonts = [(10.5 + config.FONT[1] + 5, 15.0)]
        e.hp = e.max_hp * 0.3
        run(a, 2.0)
        self.assertIsNone(e.font)
        self.assertLessEqual(e.hp, e.max_hp * 0.3 + 1e-6)

    def test_paradise_knows_its_fonts(self):
        w = ChunkedWorld(31)
        p = plan_of(w.layout, w.layout.zone("paradise"))
        self.assertEqual(len(fonts(w)), len(p.fonts))
        fx, fy = fonts(w)[0]
        w.ensure_ready(int(fx) - 3, int(fy) - 3, int(fx) + 3, int(fy) + 3)
        self.assertIs(w.tile_at(math.floor(fx), math.floor(fy)), tiles.BLOOD_FONT)


class AngelsTest(unittest.TestCase):
    def test_cherub_plinks_notes_then_lunges_and_roars(self):
        e = enemy("cherub", 18.5, 15.5)
        a = arena(e, hero_at=(30.5, 15.5))
        run(a, 3.0)
        self.assertTrue(e.serene)
        self.assertTrue(any(p.spec.look == "lyre" for p in a.projectiles))
        e.state = "unveiled"
        hp = a.hero.hp
        run(a, 4.0)
        self.assertLess(a.hero.hp, hp)

    def test_seraph_rings_of_light_then_spirals_of_blood_and_fire(self):
        e = enemy("seraph", 21.5, 15.5)
        a = arena(e, hero_at=(32.5, 15.5))
        e.cooldown = 0.0
        run(a, 0.3)
        light = [p for p in a.projectiles if p.spec.look == "light"]
        self.assertEqual(len(light), config.SERAPH[2])
        a.projectiles.clear()
        e.state, e.cooldown = "unveiled", 0.0
        run(a, 2.5)
        looks = {p.spec.look for p in a.projectiles}
        self.assertEqual(looks, {"blood", "ember"})

    def test_ophan_races_bounces_and_leaves_a_slick(self):
        walls = [(x, 5) for x in range(60)] + [(x, 25) for x in range(60)]
        e = unveiled("ophan", 20.5, 15.5)
        a = arena(e, hero_at=(30.5, 15.5), walls=walls)
        e.timer = 0.0
        aims = set()
        for _ in range(240):
            run(a, 1 / 60)
            if e.rolling == "race":
                aims.add(round(e.aim, 2))
        self.assertTrue(any(z.kind == "blood_slick" for z in a.zones))
        self.assertLess(a.hero.hp, a.hero.max_hp)
        slick = next(z for z in a.zones if z.kind == "blood_slick")
        self.assertEqual(slick.slow, config.OPHAN[6])

    def test_watcher_never_moves_and_its_gaze_is_stopped_by_columns(self):
        e = unveiled("watcher", 20.5, 15.5)
        a = arena(e, hero_at=(28.5, 15.5))
        e.cooldown = 0.0
        run(a, 3.0)
        self.assertEqual((e.x, e.y), (20.5, 15.5))
        self.assertLess(a.hero.hp, a.hero.max_hp)
        hit = a.hero.max_hp - a.hero.hp
        e2 = unveiled("watcher", 20.5, 15.5)
        b = arena(e2, hero_at=(28.5, 15.5), walls=[(24, y) for y in range(8, 23)])
        e2.cooldown = 0.0
        run(b, 3.0)
        self.assertEqual(b.hero.hp, b.hero.max_hp)
        self.assertGreater(hit, 0)


class ChasersTest(unittest.TestCase):
    def test_the_lamb_shows_its_line_then_charges(self):
        e = unveiled("lamb", 20.5, 15.5)
        a = arena(e, hero_at=(28.5, 15.5))
        states = set()
        for _ in range(150):
            run(a, 1 / 60)
            states.add(e.charging)
        self.assertTrue({"scrape", "charge"} <= states)
        self.assertLess(a.hero.hp, a.hero.max_hp)

    def test_the_lamb_is_dazed_by_a_column(self):
        e = unveiled("lamb", 20.5, 15.5)
        a = arena(e, hero_at=(28.5, 15.5), walls=[(25, y) for y in range(10, 21)])
        e.facing = 0.0
        e.charging, e.timer, e.ran = "charge", 0.0, 0.0
        for _ in range(60):
            run(a, 1 / 60)
            if e.charging == "dazed":
                break
        self.assertEqual(e.charging, "dazed")

    def test_doves_dive_one_at_a_time(self):
        doves = [unveiled("dove", 30.5 + 5 * math.cos(k), 15.5 + 4 * math.sin(k), seed=k)
                 for k in range(6)]
        a = arena(*doves, hero_at=(30.5, 15.5))
        most = 0
        for _ in range(360):
            run(a, 1 / 60)
            most = max(most, sum(d.dive > 0 for d in doves))
        self.assertEqual(most, 1)
        self.assertLess(a.hero.hp, a.hero.max_hp)

    def test_locusts_swarm_and_sting(self):
        swarm = [enemy("locust", 22.5 + k * 0.4, 15.5, seed=k) for k in range(5)]
        a = arena(*swarm, hero_at=(30.5, 15.5))
        run(a, 5.0)
        self.assertTrue(all(l.unveiled for l in swarm))
        self.assertLess(a.hero.hp, a.hero.max_hp)

    def test_the_halo_turns_wide_and_saws(self):
        e = unveiled("halo", 20.5, 15.5)
        a = arena(e, hero_at=(30.5, 15.5))
        e.heading = math.pi                                  # (facing away)
        run(a, 0.2)
        self.assertGreater(abs(math.remainder(e.heading - math.pi, math.tau)), 0)
        self.assertLess(abs(math.remainder(e.heading - math.pi, math.tau)), 1.0)  # (turning, slowly)
        run(a, 4.0)
        self.assertLess(a.hero.hp, a.hero.max_hp)
        self.assertIn(e.sprite_now(), ("halo_unveiled", "halo_unveiled2"))


class ZoneToughTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = ChunkedWorld(31)
        cls.z = cls.w.layout.zone("paradise")

    def test_endgame_tough_on_the_zone_only(self):
        s = Spawner(self.w, 31)
        x, y = self.z.cx + 40.5, self.z.cy + 150.5
        self.w.ensure_ready(int(x) - 2, int(y) - 2, int(x) + 2, int(y) + 2)
        on = s.wake("cherub", x, y, rng=random.Random(1))
        self.assertTrue(getattr(on, "zone_tough", False))
        base = config.ENEMIES["cherub"].max_hp
        self.assertEqual(on.max_hp, round(base * config.ZONE_TOUGH[0]))
        self.assertAlmostEqual(on.damage_mult, config.ENEMY_DAMAGE_MULTIPLIER * config.ZONE_TOUGH[1])
        sx, sy = self.w.spawn_point()
        off = s.wake("cherub", sx, sy, rng=random.Random(1))
        self.assertEqual(off.max_hp, base)
        self.assertFalse(getattr(off, "zone_tough", False))

    def test_paradise_chunks_roll_angels_in_bigger_packs(self):
        s = Spawner(self.w, 31)
        n = config.CHUNK_SIZE
        keys, packs = set(), {}
        for cy in range(int(self.z.cy // n) + 3, int(self.z.cy // n) + 9):
            for cx in range(int(self.z.cx // n) - 5, int(self.z.cx // n) + 5):
                for sid, key, x, y in s.roster(cx, cy):
                    keys.add(key)
                    self.assertIs(self.w.biome_at(math.floor(x), math.floor(y)), biomes.PARADISE)
                    k = sid[2] if sid[2] < PACK_ID else (sid[2] - PACK_ID) // 16
                    packs.setdefault((cx, cy, k), []).append(key)
        paradise = {k for k, sp in config.ENEMIES.items() if "paradise" in sp.biomes}
        self.assertTrue(keys <= paradise | {"chorister", "leviathan"})   # (M29.3's residents)
        self.assertGreaterEqual(len(keys), 5)
        doves = [len(v) for v in packs.values() if v[0] == "dove"]
        lo, hi = config.ENEMIES["dove"].group
        if doves:
            self.assertGreater(max(doves), hi)

    def test_angels_gather_at_fonts_but_not_at_the_gate(self):
        s = Spawner(self.w, 31)
        quiet = {m.key for m in s._quiet if m.biome == "paradise"}
        self.assertIn("paradise_gate", quiet)
        self.assertIn("paradise_court", quiet)
        self.assertNotIn("paradise_font", quiet)
        self.assertNotIn("paradise_choir", quiet)
        self.assertTrue(any(m.kind == "lair" for m in s._quiet))   # (the ring's lairs still)


class GameTest(unittest.TestCase):
    def test_they_draw_in_every_state(self):
        from ascii_adventurers.tests.test_m16 import game
        m, s = game("wizard", seed=31)
        s.app.dev = True
        s._dev_zone()
        s.quests.banner = None
        h = s.hero
        out = []
        for k, key in enumerate(NEW):
            e = s.spawner.wake(key, h.x + 3 + (k % 4) * 3, h.y - 4 + (k // 4) * 6,
                               rng=random.Random(k))
            out.append(e)
        s.enemies += out
        s.draw(m.text)
        for e in out:
            e.unveil()
            e.timer = 0.2
        s.draw(m.text)
        for e in out:
            e.state = "unveiled"
            if hasattr(e, "beam"):
                e.beam = (e.x, e.y, e.x + 5, e.y)
        s.draw(m.text)
        for _ in range(30):
            s._step(1 / 60)
        s.draw(m.text)
        self.assertTrue(all(isinstance(e, Angel) for e in out))


if __name__ == "__main__":
    unittest.main()
