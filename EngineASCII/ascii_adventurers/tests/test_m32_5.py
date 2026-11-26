"""M32.5: the Overseer's second form, the walking city (design/OCEAN.md 39.2,
39.3): the eye tearing free and the hall's walls coming down (wider, ringed
with rubble, the junctions' live cables); it builds itself (armour plates
that take the hits on their side, bigger and stronger with each), power
from the grid (a shield while it's plugged in; cut the junctions), a
hundred eyes (laser strikes on what they see), the city answering (the
watch through the breaches, turrets on its body); its four moves."""

import math
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.ai import KINDS
from ascii_adventurers.ai.overseer import Overseer
from ascii_adventurers.ai.walking_city import WalkerEye
from ascii_adventurers.render import panopticon_art  # noqa: F401
from ascii_adventurers.render.characters import ART
from ascii_adventurers.tests.test_m32_4 import DT, _eye, _game, run, until
from ascii_adventurers.world import tiles


def _city(**kw):
    """An Overseer already torn free: the walking city (in a test's open hall)."""
    o, a = _eye(**kw)
    run(a, DT)
    o.take_damage(o.hp + 10.0, a.hero, 0.0)
    run(a, config.WALKER_TEAR + 0.1)
    o._rest = 99.0
    return o, a


def _front(o, a):
    """The angle a hit from the hero travels in, and the slot it lands on."""
    ang = math.atan2(o.y - a.hero.y, o.x - a.hero.x)
    return ang, o.slot_of(ang + math.pi)


class CatalogTest(unittest.TestCase):
    def test_the_walking_city_its_eyes_its_pictures_and_tiles(self):
        spec = config.BOSSES["overseer_city"]
        self.assertEqual(spec.name, "The Walking City")
        self.assertEqual(len(spec.phases), 4)
        self.assertEqual({m for m, _ in spec.phases[0].moves}, {"stomp", "beam", "throw", "swing"})
        keys = list(config.BOSSES)
        self.assertGreater(keys.index("overseer_city"), keys.index("overseer"))   # (relic seeds stay)
        self.assertIs(KINDS["walker_eye"], WalkerEye)
        self.assertIn("walker_eye", config.BESTIARY)
        for pic in ("walking_city", "walking_city_beam", "plate_door", "plate_screen", "plate_pillar",
                    "plate_rubble", "walker_eye"):
            self.assertIn(pic, ART)
        for t in (tiles.BROKEN_FLOOR, tiles.BROKEN_CELL, tiles.BROKEN_PILLAR, tiles.RUBBLE_HEAP,
                  tiles.BREACH, tiles.JUNCTION, tiles.DEAD_JUNCTION):
            self.assertIsNotNone(t)
        self.assertTrue(tiles.JUNCTION.destructible)
        self.assertIs(tiles.JUNCTION.becomes, tiles.DEAD_JUNCTION)
        self.assertFalse(tiles.RUBBLE_HEAP.destructible)


class TearTest(unittest.TestCase):
    def test_at_zero_the_eye_tears_free_and_the_walking_city_stands(self):
        o, a = _eye()
        run(a, DT)
        o.meter = 80.0
        hp = o.max_hp
        o.take_damage(o.hp + 10.0, a.hero, 0.0)
        self.assertEqual(o.form, "tearing")
        self.assertTrue(o.alive)
        self.assertFalse(o.hittable)
        self.assertEqual(o.take_damage(500.0, a.hero, 0.0), 0.0)
        self.assertEqual(o.meter, 0.0)                         # (the fight's alert is gone)
        self.assertEqual(o.banner_req[0], "THE EYE TEARS FREE")
        run(a, config.WALKER_TEAR + 0.1)
        self.assertEqual(o.form, 2)
        self.assertIs(o.bspec, config.BOSSES["overseer_city"])
        self.assertEqual(o.max_hp, round(hp * config.WALKER_HP))
        self.assertEqual(o.hp, o.max_hp)
        self.assertEqual(o.plated, config.WALKER_PLATES[1])
        self.assertEqual(o.bar_label, "The Walking City")
        self.assertTrue(o.bars()[0][0].startswith("ARMOUR"))
        self.assertEqual(o.sprite_now(), "walking_city")
        self.assertEqual(len(o.junctions), config.WALKER_ARENA[3])
        self.assertTrue(all(a.world.tile_at(*j) is tiles.JUNCTION for j in o.junctions))
        self.assertTrue(any(a.world.tile_at(*q) is tiles.CABLE for run_ in o.cable_tiles for q in run_))
        self.assertTrue(any(a.world.tile_at(*p) is tiles.BROKEN_CELL for pc in o.pieces for p in pc[3]))

    def test_it_walks_round_the_hall_turning_slowly_its_legs_stepping(self):
        o, a = _city()
        x0, y0 = o.x, o.y
        feet = [(f.x, f.y) for f in o.feet]
        a.hero.x, a.hero.y = o.x - 10.0, o.y              # (behind it: it turns, slowly)
        f0 = o.facing
        run(a, 1.0)
        self.assertLessEqual(abs(o.facing - f0), config.WALKER_BODY[5] * 1.0 + 0.05)
        run(a, 3.0)
        self.assertGreater(math.hypot(o.x - x0, o.y - y0), 4.0)
        self.assertTrue(any(math.hypot(f.x - x, f.y - y) > 1.0 for f, (x, y) in zip(o.feet, feet)))


class WallsTest(unittest.TestCase):
    def test_the_walls_come_down_wider_ringed_with_rubble_and_open_when_won(self):
        from ascii_adventurers.tests.test_m17 import step, teleport
        m, s = _game()
        q = s.quests.states["blind_the_eyes"]
        s.quests.dev_key = "blind_the_eyes"
        s.quests.dev_finish_hunt()
        lair = q.lair
        a, b = lair.radii
        wall = config.PANOPTICON_TOWER_WALL
        teleport(s, lair.cx - a * 0.4, lair.cy)
        s.hero.hp = s.hero.max_hp = 10 ** 6
        step(s, 3)
        self.assertEqual(q.stage, "fight")
        o = q.boss
        gx, gy = lair.props["facing"]
        old_gate = list(lair.gate)
        o.take_damage(o.hp + 10.0, s.hero, 0.0)
        step(s, round((config.WALKER_TEAR + 0.5) * 60))
        self.assertEqual(o.form, 2)
        self.assertEqual(q.stage, "fight")
        out, thick = config.WALKER_ARENA[0], config.WALKER_ARENA[1]
        self.assertEqual(lair.radii, (a + wall + out - 1.0, b + wall + out - 1.0))   # (wider for good)
        w = s.world
        mid = (math.floor(lair.cx - (a + 1.5)), math.floor(lair.cy))      # (where the wall stood)
        self.assertIn(w.tile_at(*mid), (tiles.BROKEN_FLOOR, tiles.BROKEN_CELL, tiles.CABLE, tiles.JUNCTION))
        ux, uy = -gy, gx                                       # (beside the gate, not in it)
        A, B = a + wall + out + thick / 2, b + wall + out + thick / 2
        r = 1.0 / math.sqrt((ux / A) ** 2 + (uy / B) ** 2)
        rim = (math.floor(lair.cx + ux * r), math.floor(lair.cy + uy * r))
        self.assertIn(w.tile_at(*rim), (tiles.RUBBLE_HEAP, tiles.BREACH))
        self.assertTrue(all(w.tile_at(*t) is not tiles.BLAST_DOOR for t in old_gate))
        self.assertTrue(lair.gate and all(w.tile_at(*t) is tiles.RUBBLE_HEAP for t in lair.gate))
        self.assertTrue(all((t[0] + 0.5 - lair.cx) * gx + (t[1] + 0.5 - lair.cy) * gy > 0 for t in lair.gate))
        self.assertEqual(sum(1 for j in o.junctions if w.tile_at(*j) is tiles.JUNCTION), 6)
        o.hp = 0
        step(s, 2)
        self.assertEqual(q.stage, "cleared")
        self.assertTrue(all(w.tile_at(*t) is tiles.CELL_FLOOR for t in lair.gate))   # (the way out)
        self.assertIn(w.tile_at(*rim), (tiles.RUBBLE_HEAP, tiles.BREACH))          # (the walls stay down)


class PlatesTest(unittest.TestCase):
    def test_a_plate_takes_the_hits_on_its_side_until_its_shot_off(self):
        o, a = _city()
        ang, k = _front(o, a)
        for j in range(len(o.plates)):
            o.plates[j] = None
        o._resize()
        hp = o.hp
        o.take_damage(100.0, a.hero, ang)                      # (no plate: the body)
        self.assertAlmostEqual(hp - o.hp, 100.0, delta=0.5)
        from ascii_adventurers.ai.walking_city import Plate
        o.plates[k] = Plate("door", 150.0)
        o._resize()
        self.assertAlmostEqual(o.hit_radius, config.WALKER_BODY[0] * (1 + config.WALKER_PLATES[5]))
        self.assertAlmostEqual(o.strength(), 1 + config.WALKER_PLATES[6])
        hp = o.hp
        self.assertEqual(o.take_damage(100.0, a.hero, ang), 100.0)
        self.assertEqual(o.hp, hp)                             # (the plate took it)
        self.assertEqual(o.plates[k].hp, 50.0)
        o.take_damage(100.0, a.hero, ang + math.pi)            # (from behind: no plate there)
        self.assertLess(o.hp, hp)
        o.take_damage(60.0, a.hero, ang)
        self.assertIsNone(o.plates[k])                         # (shot off)
        self.assertEqual(o.size, 1.0)
        self.assertTrue(any(e.label == "PLATE OFF!" for e in a.effects if e.kind == "toast"))
        self.assertTrue(any(pc[2] == "door" and any(a.world.tile_at(*p) is tiles.BROKEN_CELL for p in pc[3])
                            for pc in o.pieces))               # (it fell: cover)

    def test_it_builds_itself_out_of_the_hall_on_your_side(self):
        o, a = _city()
        ang, k = _front(o, a)
        for j in range(len(o.plates)):
            o.plates[j] = None
        o._resize()
        pc = min(o.pieces, key=lambda p: math.hypot(p[0] - o.x, p[1] - o.y))
        pc[0], pc[1] = o.x + 6.0, o.y                          # (one in reach)
        o.build_t = 0.0
        run(a, 0.9)
        self.assertIsNotNone(o.plates[k])                      # (bolted on where you are)
        self.assertEqual(o.plated, 1)
        self.assertGreater(o.size, 1.0)
        self.assertTrue(all(a.world.tile_at(*p) is not tiles.BROKEN_CELL for p in pc[3]))   # (torn out)


class GridTest(unittest.TestCase):
    def test_plugged_in_its_shielded_and_mends_cut_the_junctions(self):
        o, a = _city()
        o.hp = o.max_hp * 0.7
        o.x, o.y = o.junction_spot(0)[0] - 6.0, o.junction_spot(0)[1]
        run(a, 0.5)
        self.assertEqual(o.phase, 1)
        self.assertTrue(o.cables)
        self.assertTrue(o.shielded)
        self.assertEqual(o.bars()[1][0], "SHIELD")
        hp = o.hp
        run(a, 1.0)
        self.assertGreater(o.hp, hp)                           # (it mends)
        for k in range(len(o.plates)):
            o.plates[k] = None
        hp = o.hp
        o.take_damage(100.0, None, None)
        self.assertAlmostEqual(hp - o.hp, 100.0 * config.WALKER_GRID[2], delta=0.5)
        for j in list(o.cables):
            tx, ty = o.junctions[j]
            while a.world.tile_at(tx, ty) is tiles.JUNCTION:
                a.world.damage_tile(tx, ty, 50)
        run(a, DT * 2)
        self.assertFalse(o.cables)
        self.assertTrue(any(e.label == "SHIELD DOWN!" for e in a.effects if e.kind == "toast"))
        self.assertTrue(all(a.world.tile_at(*q) is tiles.DEAD_CABLE for j in o.power_back
                            for q in o.cable_tiles[j]))
        run(a, config.WALKER_GRID[5] * 0.5)
        self.assertFalse(o.cables)                             # (down a while)
        run(a, config.WALKER_GRID[6] + 1.0)
        self.assertTrue(all(a.world.tile_at(*j) is tiles.JUNCTION for j in o.junctions))   # (power back)


class EyesTest(unittest.TestCase):
    def test_a_hundred_eyes_open_and_call_laser_strikes(self):
        o, a = _city()
        o.hp = o.max_hp * 0.45
        run(a, 0.2)
        self.assertEqual(o.phase, 2)
        body = [e for e in o.eyes if e.on_body]
        self.assertEqual(len(body), config.WALKER_EYES[0])
        self.assertGreater(len(o.eyes), len(body))
        e = body[0]
        o.x += 2.0
        run(a, DT)
        bx, by = o.body_point(e.slot, 0.92)
        self.assertAlmostEqual(e.x, bx, delta=0.1)             # (it rides on its body)
        self.assertIs(e.part_of, o)
        for other in o.eyes:                                   # (only this one looks at you)
            if other is not e:
                other.hp = 0.0
        a.hero.x, a.hero.y = e.x + math.cos(e.facing) * 8.0, e.y + math.sin(e.facing) * 8.0
        o.turn = 0.0
        self.assertTrue(until(a, lambda: o.strikes, 2.0))
        h = o.strikes[0][0]
        self.assertIs(h, a.hero)
        hp = a.hero.hp
        run(a, config.WALKER_EYES[11] + config.WALKER_EYES[12] + 0.1)
        self.assertLess(a.hero.hp, hp)


class CityTest(unittest.TestCase):
    def test_the_city_answers_through_the_breaches_and_its_turrets_open(self):
        o, a = _city()
        o.hp = o.max_hp * 0.2
        n = len(a.enemies)
        run(a, 1.5)
        self.assertEqual(o.phase, 3)
        watch = [e for e in o.adds if e.alive]
        self.assertEqual(len(watch), config.WALKER_CITY[1])
        self.assertTrue(all(e.kind_key in config.WALKER_CITY_WATCH for e in watch))
        self.assertGreater(len(a.enemies), n)
        a.hero.x, a.hero.y = o.x + math.cos(o.facing) * 8, o.y + math.sin(o.facing) * 8   # (in front)
        self.assertTrue(until(a, lambda: any(p.owner is o for p in a.projectiles),
                              config.WALKER_CITY[6] + 1.0))     # (its body's turrets)


class MovesTest(unittest.TestCase):
    def test_stomp_marks_its_footsteps_and_each_lands_a_shock_ring(self):
        o, a = _city()
        a.hero.x, a.hero.y = o.x + 9.0, o.y
        o._start("stomp")
        o._wait = 0.0
        run(a, DT)
        self.assertTrue(o.stomp_marks)
        self.assertTrue(o.stomping)
        hp = a.hero.hp
        self.assertTrue(until(a, lambda: o.shocks, 2.0))
        run(a, 2.5)
        self.assertLess(a.hero.hp, hp)
        self.assertFalse(o.stomping)

    def test_the_great_beam_planted_and_its_open_eye(self):
        o, a = _city()
        a.hero.x, a.hero.y = o.x + 12.0, o.y
        o._start("beam")
        o._wait = 0.0
        run(a, DT * 2)
        self.assertTrue(o.planted)
        self.assertEqual(o.pose, "beam")
        self.assertLess(o.great_beam[1], 0)                    # (charging: the line shown)
        self.assertEqual(o.sprite_now(), "walking_city_beam")
        ang, k = _front(o, a)
        hp = o.hp
        o.take_damage(100.0, a.hero, ang)                      # (into the eye, past the plates)
        self.assertAlmostEqual(hp - o.hp, 100.0 * config.WALKER_BEAM[9], delta=0.5)
        hp = a.hero.hp
        run(a, config.WALKER_BEAM[0] + 0.1)
        self.assertLess(a.hero.hp, hp)                         # (it fired)
        run(a, config.WALKER_BEAM[4] + config.WALKER_BEAM[7] + 0.3)
        self.assertFalse(o.planted)
        self.assertIsNone(o.great_beam)

    def test_grab_and_throw_you_and_a_piece_of_the_hall(self):
        o, a = _city()
        a.hero.x, a.hero.y = o.x + o.hit_radius + 3.0, o.y
        o._start("throw")
        o._wait = 0.0
        self.assertTrue(until(a, lambda: o.grabbed is not None, 1.5))
        held = (a.hero.x, a.hero.y)
        self.assertTrue(until(a, lambda: o.flung is not None, 1.5))
        hp = a.hero.hp
        self.assertTrue(until(a, lambda: o.flung is None, 1.5))
        self.assertGreater(math.hypot(a.hero.x - held[0], a.hero.y - held[1]), 4.0)   # (thrown)
        self.assertLess(a.hero.hp, hp)
        run(a, 1.0)
        a.hero.x, a.hero.y = o.x + 16.0, o.y + 2.0             # (out of reach: it throws the hall)
        o._start("throw")
        o._wait = 0.0
        self.assertTrue(until(a, lambda: o.thrown is not None, 2.5))
        x1, y1 = o.thrown[2], o.thrown[3]
        self.assertTrue(until(a, lambda: o.thrown is None, 1.5))
        near = [(math.floor(x1) + dx, math.floor(y1) + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]
        self.assertTrue(any(a.world.tile_at(*p) is tiles.BROKEN_PILLAR for p in near))   # (cover)

    def test_a_grab_lets_go_if_you_roll(self):
        o, a = _city()
        a.hero.x, a.hero.y = o.x + o.hit_radius + 3.0, o.y
        o._start("throw")
        o._wait = 0.0
        self.assertTrue(until(a, lambda: o.grabbed is not None, 1.5))
        a.hero.roll_t = 0.3
        run(a, DT)
        self.assertIsNone(o.grabbed)
        a.hero.roll_t = 0.0
        run(a, 1.0)
        self.assertIsNone(o.flung)

    def test_arm_swing_shown_then_swept(self):
        o, a = _city()
        a.hero.x, a.hero.y = o.x + 8.0, o.y
        o.facing = 0.0
        o._start("swing")
        o._wait = 0.0
        run(a, DT)
        self.assertLess(o.arm_swing[2], 0)                     # (its arc shown)
        hp = a.hero.hp
        x = a.hero.x
        run(a, config.WALKER_SWING[2] + config.WALKER_SWING[3] + 0.1)
        self.assertLess(a.hero.hp, hp)
        self.assertGreater(abs(a.hero.y - o.y) + abs(a.hero.x - x), 1.0)   # (knocked)
        self.assertIsNone(o.arm_swing)


class DeathTest(unittest.TestCase):
    def test_it_falls_its_eyes_close(self):
        o, a = _city()
        o.hp = o.max_hp * 0.45
        run(a, 0.3)
        eyes = list(o.eyes)
        self.assertTrue(eyes)
        o.hp = 0.0
        run(a, 0.1)
        self.assertFalse(o.alive)
        self.assertTrue(all(not e.alive and e.left for e in eyes))   # (no kill)


class DrawTest(unittest.TestCase):
    def test_draws_the_tear_and_every_part_of_the_walking_city(self):
        from ascii_adventurers.tests.test_m17 import step, teleport
        m, s = _game()
        q = s.quests.states["blind_the_eyes"]
        s.quests.dev_key = "blind_the_eyes"
        s.quests.dev_finish_hunt()
        lair = q.lair
        teleport(s, lair.cx - lair.radii[0] * 0.3, lair.cy)
        s.hero.hp = s.hero.max_hp = 10 ** 6
        step(s, 3)
        b = q.boss
        b.take_damage(b.hp + 10.0, s.hero, 0.0)
        step(s, 60)
        s.draw(m.text)                                         # (tearing free)
        step(s, round(config.WALKER_TEAR * 60))
        self.assertIsInstance(b, Overseer)
        self.assertEqual(b.form, 2)
        b.phase = 3
        b.hp = b.max_hp * 0.2
        step(s, 30)
        h = s.hero
        b.stomp_marks = [[h.x, h.y, 0.3, 0]]
        b.shocks = [[h.x, h.y, 2.0, set()]]
        b.strikes = [[h, h.x, h.y, 0.2]]
        b.great_beam = [0.0, -0.5, 20.0]
        b.arm_swing = (0.0, 1.0, -1.0, 12.0)
        b.throw_line = (b.x, b.y, h.x, h.y)
        b.thrown = [b.x, b.y, h.x, h.y, 0.2, 0.6, "pillar"]
        b.arm = [h.x, h.y, 0.2, 0.75, "grab"]
        b.building = [h.x, h.y, "door", 0.2, None, None]
        b.lifted = "door"
        b.cables = [0]
        s.draw(m.text)
        b.great_beam = [0.0, 0.5, 20.0]
        b.arm_swing = (0.0, 1.0, 0.5, 12.0)
        s.draw(m.text)


if __name__ == "__main__":
    unittest.main()


# --- The Overseer's relics (user's picks, 2026-11-26) -------------------------------------

from ascii_adventurers.render.gear_looks import CHEST_LOOKS, HEAD_LOOKS   # noqa: E402
from ascii_adventurers.systems import combat, relics                      # noqa: E402
from ascii_adventurers.tests.test_m28_5 import BASE, _Relic, mover        # noqa: E402


class RelicsTest(_Relic):
    """One per thing it does to you: Overseer's Eye (watching), Cell Key
    (locking up), Black Box (recording), Scrap Plating (building itself)."""

    def test_four_relics_in_four_slots(self):
        keys = config.BOSS_UNIQUES["overseer"]
        self.assertEqual(set(keys), {"overseers_eye", "cell_key", "black_box", "scrap_plating"})
        self.assertEqual(sorted(config.GEAR[k].slot for k in keys), ["chest", "head", "off", "trinket"])
        for k in keys:
            self.assertEqual(config.CARDS[k].rarity, "legendary")
            self.assertEqual(config.CARDS[k].unlock, "U:overseer")
            self.assertLessEqual(len(config.GEAR[k].name), 16)
        self.assertNotIn("overseer_city", config.BOSS_UNIQUES)      # (it's the Overseer)
        self.assertIn("overseers_eye", HEAD_LOOKS)
        self.assertIn("scrap_plating", CHEST_LOOKS)

    def test_the_overseers_eye_sweeps_and_what_it_lights_takes_more(self):
        s, h = self.setup("overseers_eye")
        lit = mover(26.5, 20.5)                               # (along your aim)
        dark = mover(20.5, 27.5)                              # (beside you: not in the light)
        self.place(lit, dark)
        h.eye_t = 0.0
        self.go(DT * 2)
        self.assertGreater(h.eye_sweep, 0)
        self.assertIn(id(h), lit.seen_by)
        self.assertNotIn("seen_by", dark.__dict__)
        a = combat.strike(lit, 100.0, h, 0.0, s.effects)
        b = combat.strike(dark, 100.0, h, 0.0, s.effects)
        self.assertAlmostEqual(a / b, 1.2, delta=0.01)        # (SEEN: +20% from you)
        lit.boss = True
        a = combat.strike(lit, 100.0, h, 0.0, s.effects)
        self.assertAlmostEqual(a / b, 1 + 0.2 * config.U_EYE[6], delta=0.01)
        lit.boss = False
        self.go(config.U_EYE[2] + config.U_EYE[5] + 0.2)      # (the sweep's over, the mark fades)
        h.eye_t = 99.0
        a = combat.strike(lit, 100.0, h, 0.0, s.effects)
        self.assertAlmostEqual(a / b, 1.0, delta=0.01)

    def test_the_cell_key_locks_your_next_hit_in_laser_bars(self):
        s, h = self.setup("cell_key")
        e = mover(28.5, 20.5)
        self.place(e)
        h.cell_t = 0.0
        self.go(DT * 2)
        self.assertTrue(h.cell_ready)
        combat.strike(e, 10.0, h, 0.0, s.effects)
        self.assertFalse(h.cell_ready)
        self.go(DT * 2)
        n = config.U_CELL[1]
        ox, oy = math.floor(e.x), math.floor(e.y)
        ring = [(ox + dx, oy + dy) for dx in range(-n, n + 1) for dy in range(-n, n + 1)
                if max(abs(dx), abs(dy)) == n]
        self.assertTrue(all(s.world.tile_at(*t) is tiles.CELL_BARS for t in ring))   # (closed)
        self.assertTrue(any(ev.kind == "toast" and ev.label == "LOCKED UP!" for ev in s.effects))
        combat.strike(e, 10.0, h, 0.0, s.effects)             # (not ready again yet)
        self.assertIsNone(h.cell_lock)
        self.go(3.0 + 0.3)                                    # (the power's 3 s)
        self.assertTrue(all(s.world.tile_at(*t) is not tiles.CELL_BARS for t in ring))   # (gone)
        boss = mover(32.5, 20.5)
        boss.boss = True
        self.place(boss)
        h.cell_ready = True
        combat.strike(boss, 10.0, h, 0.0, s.effects)
        self.go(DT * 2)
        self.assertGreater(boss.status.bound, 0.0)            # (a boss is held, briefly)
        self.assertLessEqual(boss.status.bound, config.U_CELL[4])

    def test_the_black_box_rewinds_what_hurt_you(self):
        s, h = self.setup("black_box")
        e = self.place(mover(28.5, 20.5))[0]
        h.hp = h.max_hp
        h.box_t = 99.0
        h.take_damage(30.0, e, None)
        lost = h.max_hp - h.hp
        self.assertGreater(lost, 0)
        self.assertEqual(len(h.box_log), 1)
        h.box_t = DT
        self.go(DT * 2)
        self.assertAlmostEqual(h.max_hp - h.hp, lost * (1 - 0.4), delta=0.5)   # (REWIND)
        self.assertEqual(h.box_log, [])
        self.assertGreater(h.box_t, config.U_BOX[0] - 1.0)
        h.box_t = config.U_BOX[0] - config.U_BOX[1] - 0.1     # (5 s since it rewound)
        h.hp = h.max_hp * 0.5                                 # (dropping below 30%: at once)
        h.take_damage(h.max_hp * 0.3, e, None)
        hp = h.hp
        self.assertLess(hp, h.max_hp * config.U_BOX[2])
        self.go(DT * 2)
        self.assertGreater(h.hp, hp)
        h.hp = h.max_hp * 0.35                                # (dropping below again so soon:
        h.take_damage(h.max_hp * 0.1, e, None)                # it waits)
        self.go(1.0)
        self.assertEqual(len(h.box_log), 1)

    def test_scrap_plating_kills_bolt_plates_that_block_a_hit_each(self):
        s, h = self.setup("scrap_plating")
        e = self.place(mover(28.5, 20.5))[0]
        b = combat.strike(e, 100.0, h, 0.0, s.effects)
        for _ in range(config.U_PLATES + 2):
            relics.on_kill(s, s.me, e)
        self.assertEqual(h.scrap_plates, config.U_PLATES)
        a = combat.strike(e, 100.0, h, 0.0, s.effects)
        self.assertAlmostEqual(a / b, 1 + 0.04 * config.U_PLATES, delta=0.01)   # (+4% a plate)
        hp = h.hp
        self.assertEqual(h.take_damage(40.0, e, None), 0.0)  # (a plate takes it)
        self.assertEqual(h.hp, hp)
        self.assertEqual(h.scrap_plates, config.U_PLATES - 1)
        self.go(DT)
        self.assertTrue(any(ev.kind == "toast" and ev.label == "PLATE OFF!" for ev in s.effects))
        h.status_tick = True                                  # (a status tick goes by them)
        h.take_damage(5.0, e, None)
        h.status_tick = False
        self.assertLess(h.hp, hp)
        self.assertEqual(h.scrap_plates, config.U_PLATES - 1)
        h.take_damage(5.0, None, None)                        # (and so does the land)
        self.assertEqual(h.scrap_plates, config.U_PLATES - 1)

    def test_their_things_draw(self):
        s, h = self.setup("overseers_eye")
        e = mover(26.5, 20.5)
        self.place(e)
        h.eye_t = 0.0
        self.go(0.2)
        h.cell_ready, h.box_log, h.scrap_plates = True, [(h.time, 5.0)], 3
        s.me.camera.center_on(h.x, h.y)
        s.me.minimap = None
        s.draw(s.manager.text)
        self.assertGreater(h.eye_sweep, 0)
