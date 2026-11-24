"""M31.2: Pangaea's echoes and the shore ring's eight (design/OCEAN.md 25-26,
28.3): every enemy attack plays again 3 s later at full damage, killing the
enemy cancels its echoes, an echo never echoes; the great mammals and the
early hunters; fire in the ferns, stuck spears, traps; each on its ring."""

import math
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.ai import KINDS
from ascii_adventurers.ai.brain import AIContext
from ascii_adventurers.ai.pangaea import Beast, inside
from ascii_adventurers.render import pangaea_art  # noqa: F401
from ascii_adventurers.render.characters import ART
from ascii_adventurers.systems import pangaea as land_sys
from ascii_adventurers.systems.spawner import Spawner
from ascii_adventurers.systems.zones import update_zones
from ascii_adventurers.tests.test_p7 import Arena, enemy
from ascii_adventurers.world import tiles
from ascii_adventurers.world.chunked import ChunkedWorld
from ascii_adventurers.world.test_map import TestMap
from ascii_adventurers.world.zones import plan_of

NEW = ("mammoth", "sabre_tooth", "woolly_rhino", "cave_bear",
       "spear_hunter", "trapper", "fire_bearer", "shaman")
DT = 1 / 60


def fern_map(w=60, h=30, legend=tiles.FERN_MEADOW, patches=()):
    """Fern meadow (it burns), with `patches`: {(x, y): tile}."""
    rows = [["."] * w for _ in range(h)]
    extra = {}
    for k, ((x, y), tile) in enumerate(patches.items() if isinstance(patches, dict) else patches):
        ch = chr(ord("A") + k % 26)
        rows[y][x] = ch
        extra[ch] = tile
    return TestMap(["".join(r) for r in rows], legend={".": legend, **extra})


class _Scene:
    """What systems/pangaea.Land.step looks at."""

    def __init__(self, a):
        self.a, self.world, self.effects, self.zones = a, a.world, a.effects, a.zones
        self._sounds = []

    @property
    def enemies(self):
        return self.a.enemies


def arena(*enemies, hero_at=(30.5, 15.5), tough=True, world=None):
    a = Arena(*enemies, hero_at=hero_at)
    a.world = world or fern_map()
    if tough:
        a.hero.hp = a.hero.max_hp = 100000
    a.scene = _Scene(a)
    return a


def run(a, seconds, every=None):
    for _ in range(round(seconds * 60)):
        a.run(DT)
        update_zones(a.zones, a.actors(), a.effects, DT, a.world)
        g = getattr(a.world, "pangaea_land", None)
        if g is not None and g.busy:
            g.step(a.scene, [a.hero], DT)
        if every is not None:
            every()


def until(a, cond, seconds=2.0):
    """Step until `cond()` holds (an enemy notices you on its next look round)."""
    for _ in range(round(seconds * 60)):
        if cond():
            return True
        run(a, DT)
    return cond()


def ctx_of(a):
    return AIContext(a.world, [a.hero], a.actors(), a.projectiles, a.effects, zones=a.zones)


def still(e):
    """An enemy that only plays its echoes (it does nothing of its own)."""
    e.turn = lambda ctx, dt: None
    return e


class CatalogTest(unittest.TestCase):
    def test_eight_on_the_shore_ring_each_with_its_picture_and_page(self):
        for key in NEW:
            spec = config.ENEMIES[key]
            self.assertEqual(spec.biomes, ("pangaea",), key)
            self.assertIn(spec.kind, KINDS)
            self.assertTrue(issubclass(KINDS[spec.kind], Beast), key)
            self.assertIn(key, config.BESTIARY)
            self.assertEqual(config.PANGAEA_RING_OF[key], 2, key)
            self.assertIn(spec.sprite, ART)
            self.assertEqual(len(ART[spec.sprite]), 18)
            self.assertTrue(all(len(r) == 14 for r in ART[spec.sprite]), key)
        for name in ("mammoth_trumpet", "sabre_tooth_pounce", "sabre_tooth_eyes", "cave_bear_rear",
                     "shaman_paint"):
            self.assertIn(name, ART)
        self.assertEqual({k for k in NEW if config.ENEMIES[k].elite}, {"mammoth", "shaman"})
        self.assertGreater(config.BIOME_ENEMY_DENSITY["pangaea"], 0)


class EchoTest(unittest.TestCase):
    def test_an_attack_plays_again_three_seconds_later_at_full_damage(self):
        e = still(enemy("cave_bear", 20.5, 15.5))
        a = arena(e)
        hp = a.hero.hp
        e.area(ctx_of(a), "circle", a.hero.x, a.hero.y, 0.0, 1.0, 0.0, 50.0)
        self.assertAlmostEqual(hp - a.hero.hp, 50.0)
        self.assertEqual(len(e.echoes), 1)
        run(a, config.ECHO[0] - 0.1)
        self.assertAlmostEqual(hp - a.hero.hp, 50.0)          # (not yet)
        run(a, 0.2)
        self.assertAlmostEqual(hp - a.hero.hp, 100.0)         # (again, the same)
        self.assertEqual(e.echoes, [])                        # (an echo never echoes)
        run(a, config.ECHO[0] + 0.5)
        self.assertAlmostEqual(hp - a.hero.hp, 100.0)

    def test_its_tell_shows_first_as_long_as_the_windup(self):
        e = still(enemy("cave_bear", 20.5, 15.5))
        a = arena(e)
        e.area(ctx_of(a), "cone", e.x, e.y, 0.0, 3.0, 1.0, 10.0)
        self.assertAlmostEqual(e.echoes[0].tell, config.ENEMIES["cave_bear"].windup)
        e.area(ctx_of(a), "cone", e.x, e.y, 0.0, 3.0, 1.0, 10.0, tell=0.01)
        self.assertAlmostEqual(e.echoes[1].tell, config.ECHO[1])     # (at least)
        e.area(ctx_of(a), "cone", e.x, e.y, 0.0, 3.0, 1.0, 10.0, tell=5.0)
        self.assertAlmostEqual(e.echoes[2].tell, config.ECHO[2])     # (at most)
        ech = e.echoes[0]
        self.assertEqual((ech.x, ech.y, ech.sprite), (e.x, e.y, "cave_bear"))

    def test_killing_the_enemy_cancels_its_echoes(self):
        e = still(enemy("cave_bear", 20.5, 15.5))
        a = arena(e)
        hp = a.hero.hp
        e.area(ctx_of(a), "circle", a.hero.x, a.hero.y, 0.0, 1.0, 0.0, 50.0)
        e.record_run(e.x, e.y, 0.0, 12.0, 10.0, 1.0, 40.0, 0.0)
        run(a, 1.0)
        e.take_damage(e.hp + 10, None, None)
        run(a, config.ECHO[0] + 1)
        self.assertAlmostEqual(hp - a.hero.hp, 50.0)          # (only the first)
        self.assertEqual((e.echoes, e.runners), ([], []))

    def test_shots_echo_as_the_same_shot_faded(self):
        e = still(enemy("spear_hunter", 10.5, 15.5))
        a = arena(e, hero_at=(50.5, 5.5))
        p = e.throw(ctx_of(a), "spear", 0.3)
        self.assertEqual(p.spec.look, "spear")
        a.projectiles.clear()
        run(a, config.ECHO[0] + 0.02)
        echo = [q for q in a.projectiles if q.spec.look == "spear_echo"]
        self.assertEqual(len(echo), 1)
        q = echo[0]
        self.assertAlmostEqual(q.angle, 0.3)
        self.assertAlmostEqual(q.damage, p.damage)
        self.assertTrue(q.echo)
        self.assertEqual(e.echoes, [])

    def test_a_run_echoes_as_a_ghost_running_the_same_line(self):
        e = still(enemy("woolly_rhino", 10.5, 15.5))
        a = arena(e, hero_at=(20.5, 15.5))
        hp = a.hero.hp
        e.record_run(10.5, 15.5, 0.0, 16.0, 13.0, 1.0, 30.0, 0.0)
        run(a, config.ECHO[0] + 0.05)
        self.assertEqual([r.look for r in e.runners], ["ghost"])
        run(a, 1.5)
        self.assertAlmostEqual(hp - a.hero.hp, 30.0)          # (once, as it ran through)
        self.assertEqual(e.runners, [])

    def test_a_torch_echoes_but_the_echo_lights_no_fire(self):
        e = still(enemy("fire_bearer", 10.5, 15.5))
        a = arena(e, hero_at=(50.5, 5.5))
        e.lob(ctx_of(a), 20.5, 15.5, 0.9, "torch")
        run(a, 1.0)
        g = land_sys.land(a.world)
        self.assertGreater(len(g.fires), 0)
        blazes = g.blaze_n
        run(a, config.ECHO[0] + 0.5)
        self.assertEqual(g.blaze_n, blazes)                  # (the fire is the land's)

    def test_being_hit_and_the_land_record_nothing(self):
        bear = still(enemy("cave_bear", 20.5, 15.5))
        fb = still(enemy("fire_bearer", 40.5, 15.5))
        a = arena(bear, fb)
        bear.take_damage(5, a.hero, 0.0)
        land_sys.ignite(a.world, a.hero.x, a.hero.y, 10)
        run(a, 2.0)
        self.assertEqual((bear.echoes, fb.echoes), ([], []))

    def test_shapes(self):
        class Body:
            hit_radius = 0.5

        def at(x, y):
            b = Body()
            b.x, b.y = x, y
            return b

        self.assertTrue(inside(at(2, 0), "circle", 0, 0, 0, 1.6, 0))
        self.assertFalse(inside(at(3, 0), "circle", 0, 0, 0, 1.6, 0))
        self.assertTrue(inside(at(3, 0.5), "cone", 0, 0, 0, 4, 0.3))
        self.assertFalse(inside(at(-3, 0), "cone", 0, 0, 0, 4, 0.3))
        self.assertTrue(inside(at(8, 0.9), "line", 0, 0, 0, 10, 0.5))
        self.assertFalse(inside(at(8, 2.0), "line", 0, 0, 0, 10, 0.5))
        self.assertFalse(inside(at(12, 0), "line", 0, 0, 0, 10, 0.5))


class MammalTest(unittest.TestCase):
    def test_a_herd_takes_parallel_lanes_and_stampedes(self):
        herd = [enemy("mammoth", 14.5, 13.5 + 2.5 * k, seed=k) for k in range(3)]
        a = arena(*herd, hero_at=(30.5, 16.0))
        lead = herd[1]
        for m in herd:
            m.trumpet_cd = 99.0
        lead.trumpet_cd = 0.0
        lead.cooldown = 99.0
        self.assertTrue(until(a, lambda: lead.state == "trumpet"))
        run(a, config.MAMMOTH[1] + DT)
        self.assertEqual([m.state for m in herd], ["lane"] * 3)
        aims = {round(m.aim, 6) for m in herd}
        self.assertEqual(len(aims), 1)                        # (parallel)
        a_ = herd[0].aim
        px, py = -math.sin(a_), math.cos(a_)
        offs = sorted(round(((m.lane_to or (m.x, m.y))[0] - lead.x) * px
                            + ((m.lane_to or (m.x, m.y))[1] - lead.y) * py, 2) for m in herd)
        self.assertAlmostEqual(offs[1] - offs[0], config.MAMMOTH[7], places=1)
        self.assertAlmostEqual(offs[2] - offs[1], config.MAMMOTH[7], places=1)
        run(a, config.MAMMOTH[8] + 0.1)
        self.assertTrue(all(m.state == "stampede" for m in herd))
        run(a, 2.5)
        self.assertTrue(all(m.state != "stampede" for m in herd))
        self.assertTrue(all(any(ech.kind == "run" for ech in m.echoes) for m in herd))

    def test_the_trumpet_pushes_you_back(self):
        m = enemy("mammoth", 24.5, 15.5)
        a = arena(m, hero_at=(28.5, 15.5))
        m.trumpet_cd, m.cooldown = 0.0, 99.0
        self.assertTrue(until(a, lambda: m.state == "trumpet"))
        run(a, config.MAMMOTH[1] + 0.1)
        self.assertGreater(a.hero.x, 28.5 + config.MAMMOTH[4] * 0.6)

    def test_the_sabre_tooth_hides_in_ferns_pounces_and_pins_until_you_roll(self):
        patches = {(x, y): tiles.TALL_FERNS for x in range(8, 14) for y in range(13, 18)}
        s = enemy("sabre_tooth", 10.5, 15.5)
        a = arena(s, hero_at=(19.5, 15.5), world=fern_map(patches=patches))
        s.cooldown = 99.0
        run(a, 0.3)
        self.assertEqual(s.sprite_now(), "sabre_tooth_eyes")
        self.assertTrue(s.hittable)                           # (no ambushers: it can be shot)
        s.cooldown = 0.0
        run(a, config.ENEMIES["sabre_tooth"].windup + 1.0)
        self.assertEqual(s.state, "pin")
        hp = a.hero.hp
        x0 = a.hero.x
        for _ in range(60):
            a.hero.move(1.0, 0.0, DT, a.world)
            run(a, DT)
        self.assertLess(abs(a.hero.x - x0), 0.2)              # (pinned: it can't walk)
        self.assertLess(a.hero.hp, hp)                        # (bitten)
        a.hero.roll_t = 0.3
        run(a, DT * 2)
        self.assertEqual(s.state, "dazed")
        self.assertIn("ROLLED FREE!", [fx.label for fx in a.effects if fx.kind == "toast"])

    def test_the_rhinos_front_shrugs_off_hits(self):
        r = enemy("woolly_rhino", 20.5, 15.5)
        r.facing = 0.0
        hp = r.hp
        r.take_damage(100, None, math.pi)                     # (from in front)
        self.assertAlmostEqual(hp - r.hp, 100 * config.RHINO[1])
        hp = r.hp
        r.take_damage(100, None, math.pi / 2)                 # (from the side)
        self.assertAlmostEqual(hp - r.hp, 100)

    def test_the_rhino_charges_skids_and_turns_slowly(self):
        r = enemy("woolly_rhino", 10.5, 15.5)
        a = arena(r, hero_at=(20.5, 15.5))
        r.cooldown = 0.0
        seen, facings = set(), []

        def watch():
            seen.add(r.state)
            if r.state == "turn":
                facings.append(r.facing)
        run(a, 4.0, watch)
        self.assertTrue({"scrape", "charge", "skid", "turn"} <= seen)
        steps = [abs((b - a_ + math.pi) % math.tau - math.pi) for a_, b in zip(facings, facings[1:])]
        self.assertTrue(steps and max(steps) <= config.RHINO[5] * DT + 1e-6)

    def test_the_bear_rears_swipes_twice_and_slams(self):
        b = enemy("cave_bear", 20.5, 15.5)
        a = arena(b, hero_at=(22.5, 15.5))
        b.roared, b.roar_cd, b.cooldown = True, 99.0, 0.0
        hits = []
        hp = [a.hero.hp]

        def watch():
            if a.hero.hp < hp[0]:
                hits.append(round(hp[0] - a.hero.hp))
            hp[0] = a.hero.hp
        self.assertTrue(until(a, lambda: b.state == "rear"))
        self.assertEqual(b.sprite_now(), "cave_bear_rear")
        run(a, config.ENEMIES["cave_bear"].windup + 1.2, watch)
        self.assertGreaterEqual(len(hits), 3)                 # (two swipes and the slam)
        self.assertGreater(hits[2], hits[0])                  # (the slam hits harder)

    def test_the_bears_roar_wakes_the_beasts_near_it(self):
        b = enemy("cave_bear", 20.5, 15.5)
        near = enemy("woolly_rhino", 34.5, 25.5)
        near.alert, near.last_known = False, None
        a = arena(b, near, hero_at=(24.5, 15.5))
        near.think = lambda ctx, dt: None
        run(a, 0.5)
        self.assertTrue(near.alert)
        self.assertEqual(near.last_known, (a.hero.x, a.hero.y))


class HunterTest(unittest.TestCase):
    def test_a_spear_that_misses_sticks_then_comes_out(self):
        h = enemy("spear_hunter", 10.5, 15.5)
        a = arena(h, hero_at=(20.5, 15.5))
        a.hero.untouchable = 99.0                             # (the spear flies on past)
        h.cooldown = 0.0
        stuck = []

        def watch():
            g = getattr(a.world, "pangaea_land", None)
            if g is not None and g.spears:
                stuck.extend(g.spears)
        run(a, 1.6, watch)
        self.assertTrue(stuck)
        tx, ty = stuck[0]
        self.assertIs(a.world.tile_at(tx, ty), tiles.STUCK_SPEAR)
        self.assertTrue(tiles.STUCK_SPEAR.solid and not tiles.STUCK_SPEAR.blocks_shots)
        h.cooldown = 99.0
        h.think = lambda ctx, dt: None
        run(a, config.SPEAR[3] + 0.2)
        self.assertIs(a.world.tile_at(tx, ty), tiles.FERN_MEADOW)

    def test_a_spear_never_sticks_into_someone(self):
        a = arena()
        self.assertFalse(land_sys.stick_spear(a.world, a.hero.x, a.hero.y, a.actors()))

    def test_traps_hold_you_but_a_roll_carries_you_over(self):
        t = enemy("trapper", 40.5, 15.5)
        a = arena(t, hero_at=(20.5, 15.5))
        t.think = lambda ctx, dt: None
        land_sys.lay_trap(a.world, 21.5, 15.5, "snare", t)
        a.hero.roll_t, a.hero.x = 0.3, 21.5
        run(a, DT)
        self.assertEqual(len(land_sys.land(a.world).traps), 1)       # (rolled over it)
        a.hero.roll_t = 0.0
        run(a, DT)
        self.assertEqual(land_sys.land(a.world).traps, [])
        self.assertEqual(a.hero.slow_mult, 0.0)               # (held)
        hp = a.hero.hp
        land_sys.lay_trap(a.world, 21.5, 15.5, "pit", t)
        a.hero.slow_t = 0.0
        run(a, DT)
        self.assertLess(a.hero.hp, hp)                         # (a pit hurts too)

    def test_traps_catch_beasts_not_hunters(self):
        r = still(enemy("woolly_rhino", 30.5, 10.5))
        h = still(enemy("spear_hunter", 30.5, 20.5))
        a = arena(r, h, hero_at=(5.5, 5.5))
        land_sys.lay_trap(a.world, 30.5, 10.5, "snare", h)
        land_sys.lay_trap(a.world, 30.5, 20.5, "snare", h)
        run(a, DT)
        self.assertGreater(r.status.rooted, 0)
        self.assertEqual(len(land_sys.land(a.world).traps), 1)

    def test_the_trapper_lays_traps_and_throws_bolas(self):
        t = enemy("trapper", 12.5, 15.5)
        a = arena(t, hero_at=(20.5, 15.5))
        t.cooldown = 0.0
        run(a, 0.1)
        g = land_sys.land(a.world)
        self.assertEqual(len(g.traps), config.TRAPPER[6])     # (round its home)
        run(a, 1.2)
        self.assertLessEqual(a.hero.slow_mult, config.TRAPPER[10] + 1e-9)   # (tangled)

    def test_a_torch_sets_the_ferns_alight_and_the_fire_spreads_then_burns_out(self):
        f = enemy("fire_bearer", 14.5, 15.5)
        a = arena(f, hero_at=(22.5, 15.5))
        f.cooldown, f.beat_cd, f.swing_cd = 0.0, 99.0, 99.0
        g = land_sys.land(a.world)
        most = [0]

        def watch():
            most[0] = max(most[0], len(g.fires))
        run(a, 3.0, watch)
        self.assertGreater(most[0], 5)
        self.assertLessEqual(most[0], config.FIREB[4] * 3)
        hp = a.hero.hp
        a.hero.x, a.hero.y = next((x + 0.5, y + 0.5) for x, y in g.fires)
        f.think = lambda ctx, dt: None
        run(a, 0.5)
        self.assertLess(a.hero.hp, hp)                        # (it burns)
        run(a, config.FIRE[0] * 3)
        self.assertEqual(g.fires, {})
        scorched = sum(1 for y in range(30) for x in range(60)
                       if a.world.tile_at(x, y) is tiles.SCORCHED)
        self.assertGreater(scorched, 5)

    def test_fire_never_burns_the_fire_bearer(self):
        f = still(enemy("fire_bearer", 20.5, 15.5))
        a = arena(f, hero_at=(40.5, 15.5))
        land_sys.ignite(a.world, f.x, f.y, 10)
        hp = f.hp
        run(a, 1.0)
        self.assertEqual(f.hp, hp)

    def test_the_beat_drives_the_beasts_at_you(self):
        f = enemy("fire_bearer", 20.5, 15.5)
        b = still(enemy("woolly_rhino", 26.5, 20.5))
        a = arena(f, b, hero_at=(30.5, 15.5))
        f.beat_cd, f.cooldown, f.swing_cd = 0.0, 99.0, 99.0
        run(a, 0.3)
        self.assertGreater(b.driven, 0)
        self.assertAlmostEqual(b.speed, config.ENEMIES["woolly_rhino"].speed * config.FIREB[8])

    def test_the_shaman_paints_a_spirit_that_charges_once(self):
        s = enemy("shaman", 12.5, 15.5)
        a = arena(s, hero_at=(21.5, 15.5))
        s.cooldown = 0.0
        hp = a.hero.hp
        spirits = []

        def watch():
            spirits.extend(r for r in s.runners if r.look == "ochre" and r not in spirits)
        run(a, config.ENEMIES["shaman"].windup + 1.5, watch)
        self.assertEqual(len(spirits), 1)
        self.assertLess(a.hero.hp, hp)
        self.assertTrue(any(ech.kind == "run" for ech in s.echoes))

    def test_no_fire_near_a_living_shaman_goes_out(self):
        s = still(enemy("shaman", 20.5, 15.5))
        a = arena(s, hero_at=(40.5, 15.5))
        land_sys.ignite(a.world, 24.5, 15.5, 1)
        g = land_sys.land(a.world)
        run(a, config.FIRE[0] + 1)
        self.assertIn((24, 15), g.fires)
        s.take_damage(s.hp + 1, None, None)
        run(a, config.FIRE[0] + 1)
        self.assertNotIn((24, 15), g.fires)

    def test_a_fire_far_from_everyone_goes_out(self):
        a = arena(hero_at=(5.5, 5.5))
        land_sys.ignite(a.world, 50.5, 25.5, 5)
        g = land_sys.land(a.world)
        far = config.FIRE[4]
        a.hero.x = 50.5 - far - 2
        run(a, DT * 2)
        self.assertEqual(g.fires, {})


class SpawnTest(unittest.TestCase):
    def test_each_on_its_own_ring_and_endgame_tough(self):
        w = ChunkedWorld(31)
        z = w.layout.zone("pangaea")
        p = plan_of(w.layout, z)
        sp = Spawner(w, 31)
        n = config.CHUNK_SIZE
        got = []
        rng = random.Random(4)
        tries = 0
        while len(got) < 25 and tries < 400:
            tries += 1
            a, r = rng.uniform(0, math.tau), rng.uniform(0, z.radius)
            cx = math.floor((z.cx + math.cos(a) * r) / n)
            cy = math.floor((z.cy + math.sin(a) * r) / n)
            if w.biome_at(cx * n + n // 2, cy * n + n // 2).name != "pangaea":
                continue
            ring = p.ring_at(cx * n + n / 2, cy * n + n / 2)
            roster = sp.roster(cx, cy)
            if ring < 2:
                self.assertEqual(roster, [])                  # (M31.3 brings theirs)
            for _, key, x, y in roster:
                self.assertEqual(config.PANGAEA_RING_OF[key], 2)
                if not key.startswith(("mammoth", "spear")):  # (packs stand round the first)
                    self.assertEqual(p.ring_at(x, y), 2)
                got.append((key, x, y))
        self.assertGreaterEqual(len(got), 25)
        key, x, y = got[0]
        e = sp.wake(key, x, y, (0, 0, 0))
        self.assertTrue(e.zone_tough)


class GameTest(unittest.TestCase):
    def test_a_fight_on_the_shore_steps_and_draws(self):
        from ascii_adventurers.tests.test_m31_1 import _game
        m, s = _game()
        for _ in range(3):
            s._dev_zone()
        s.quests.banner = None
        s.hero.hp = s.hero.max_hp = 10 ** 6
        s.enemies.clear()
        for k, key in enumerate(NEW):
            a = k * math.tau / len(NEW)
            e = s.spawner.wake(key, s.hero.x + math.cos(a) * 9, s.hero.y + math.sin(a) * 6,
                               rng=random.Random(k))
            e.alert = True
            s.enemies.append(e)
        echoed = False
        for _ in range(60 * 6):
            s._step(1 / 60)
            s.hero.hp = s.hero.max_hp
            echoed = echoed or any(isinstance(e, Beast) and e.echoes for e in s.enemies)
        s.quests.banner = None
        s.draw(m.text)
        self.assertTrue(echoed)


if __name__ == "__main__":
    unittest.main()
