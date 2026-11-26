"""M32.4: blinding the seven eyes and the Overseer's first form (design/OCEAN.md
38, 39.1, 39.3): the camera masts shielded by their pylons, lockdown when
one is exposed, the city going dark round the blinded ones, the voice in
the screens; the tower's hall opening and sealing; the eye on its ceiling
rail -- the gaze, the cells, the laser grid, the recordings and its four
moves."""

import math
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.ai import KINDS, make_enemy
from ascii_adventurers.ai import panopticon as P
from ascii_adventurers.ai.overseer import Overseer, Recording
from ascii_adventurers.render import panopticon_art  # noqa: F401
from ascii_adventurers.render.characters import ART
from ascii_adventurers.systems import alert
from ascii_adventurers.systems.quests import QUEST_SID
from ascii_adventurers.systems.zones import update_zones
from ascii_adventurers.tests.test_p7 import Arena, enemy
from ascii_adventurers.world import tiles
from ascii_adventurers.world.landmarks import quest_marks
from ascii_adventurers.world.layout import IslandLayout
from ascii_adventurers.world.zones import plan_of

DT = 1 / 60


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


class CatalogTest(unittest.TestCase):
    def test_the_quest_the_masts_and_the_overseer(self):
        q = config.QUESTS["blind_the_eyes"]
        self.assertEqual((q.biome, q.kind, q.count, q.boss, q.target),
                         ("panopticon", "masts", 7, "overseer", "camera_mast"))
        self.assertEqual(q.giver, "the voice")
        for key in ("camera_mast", "overseer", "recording"):
            self.assertIn(config.ENEMIES[key].kind, KINDS)
            self.assertIn(key, config.BESTIARY)
            self.assertEqual(config.ENEMIES[key].biomes, ())
        self.assertTrue(issubclass(KINDS["camera_mast"], P.Machine))
        self.assertEqual(config.ENEMIES["overseer"].max_hp, 12000)
        b = config.BOSSES["overseer"]
        self.assertEqual(list(config.BOSSES)[-1], "overseer")      # (last: the relic seeds stay)
        self.assertEqual([ph.below for ph in b.phases], [1.0, 0.75, 0.5, 0.25])
        for ph in b.phases:
            moves = {m for m, _ in ph.moves}
            self.assertTrue({"sweep", "salvo", "drop", "scan"} <= moves)
        self.assertNotIn("cell", {m for m, _ in b.phases[0].moves})
        self.assertIn("overseer", config.ACHIEVEMENTS)
        for name in ("camera_mast", "voice_screen", "overseer", "overseer_low"):
            self.assertIn(name, ART)
            self.assertTrue(all(len(r) == 14 for r in ART[name]), name)


class PlanTest(unittest.TestCase):
    def test_the_sea_wall_is_the_camp_and_the_tower_the_lair(self):
        for seed in (31, 7, 12):
            lay = IslandLayout(seed)
            z = lay.zone("panopticon")
            p = plan_of(lay, z)
            camp, lair = quest_marks(lay, "blind_the_eyes")
            self.assertEqual((camp.key, lair.key), ("panopticon_sea_wall", "panopticon_tower"))
            self.assertEqual(camp.npc, camp.props["screen"])
            self.assertEqual(camp.spots, [(x + 0.5, y + 0.5) for x, y, _ in p.masts])
            self.assertEqual(len(camp.spots), 7)
            self.assertTrue(lair.props["barred"])
            self.assertIs(lair.props["seal"], tiles.BLAST_DOOR)
            pyl = lair.props["pylons"]
            self.assertEqual(len(pyl), 4)
            for x, y in pyl:
                self.assertIs(lair.tile_at(math.floor(x), math.floor(y)), tiles.HALL_PYLON)
                self.assertTrue(lair.inside(x, y))
            self.assertEqual(len(p.mast_pylons), 7)
            for (mx, my, _), mine in zip(p.masts, p.mast_pylons):
                self.assertEqual(len(mine), 3)
                for t in mine:
                    self.assertIn(t, p.pylon_at)
                    self.assertAlmostEqual(math.hypot(t[0] - mx, t[1] - my),
                                           config.PANOPTICON_MAST_PYLONS, delta=1.0)


class MastTest(unittest.TestCase):
    def setUp(self):
        self.a = Arena(hero_at=(30.5, 15.5))
        self.a.hero.hp = self.a.hero.max_hp = 100000
        w = self.a.world
        self.pylons = [(14, 15), (26, 15), (20, 9)]
        for tx, ty in self.pylons:
            w.set_tile(tx, ty, tiles.PYLON)
        for j in (-1, 0, 1):
            for i in (-1, 0, 1):
                w.set_tile(20 + i, 15 + j, tiles.MAST_BASE)
        self.m = enemy("camera_mast", 20.5, 15.5)
        self.m.pylons = list(self.pylons)
        self.a.enemies.append(self.m)

    def test_shielded_by_its_pylons_then_exposed_to_lockdown(self):
        a, m = self.a, self.m
        run(a, DT)
        self.assertTrue(m.shield)
        hp = m.hp
        m.take_damage(500.0, a.hero, 0.0)
        self.assertEqual(m.hp, hp)                           # (SHIELDED)
        for tx, ty in self.pylons[:2]:
            a.world.set_tile(tx, ty, tiles.PYLON_STUMP)
        run(a, DT)
        self.assertTrue(m.shield)                            # (one still stands)
        a.world.set_tile(*self.pylons[2], tiles.PYLON_STUMP)
        run(a, DT)
        self.assertFalse(m.shield)
        self.assertEqual(alert.alert_of(a.world).meter, config.PANOPTICON_ALERT[0])
        self.assertTrue(any(getattr(e, "label", "") == "THE EYE IS EXPOSED" for e in a.effects))
        m.take_damage(500.0, a.hero, 0.0)
        self.assertLess(m.hp, hp)

    def test_blinded_its_part_of_the_city_goes_dark(self):
        a, m = self.a, self.m
        m.pylons = []
        run(a, DT)
        m.hp = 0
        run(a, DT)
        self.assertIs(a.world.tile_at(20, 15), tiles.MAST_STUMP)
        self.assertTrue(alert.dark_at(a.world, 25.0, 20.0))
        self.assertFalse(alert.dark_at(a.world, 20.5 + config.MAST_DARK[0] + 5, 15.5))
        g = alert.alert_of(a.world)
        g.rate = 0.0
        alert.seen(a.world, 20.0, 22.0, 15.0)
        self.assertEqual(g.rate, 20.0 * config.MAST_DARK[1])   # (half as fast here)
        cam = enemy("camera", 26.5, 15.5)
        cam.base = cam.facing = 0.0
        b = Arena(cam, hero_at=(32.5, 15.5))
        b.world = a.world
        run(b, 1.0)
        self.assertIsNone(cam.seeing)                        # (a dark camera sees nothing)
        self.assertTrue(cam.dark)


def _game():
    from ascii_adventurers.tests.test_m16 import game
    m, s = game("wizard", seed=31)
    s.app.dev = True
    for _ in range(4):
        s._dev_zone()
    return m, s


class QuestTest(unittest.TestCase):
    def setUp(self):
        self.m, self.s = _game()
        self.q = self.s.quests.states["blind_the_eyes"]

    def test_seven_masts_out_from_the_start_the_seventh_opens_the_tower(self):
        s, q = self.s, self.q
        sp = s.spawner
        masts = [(sid, v) for sid, v in sp.fixed.items() if sid[:2] == (QUEST_SID, q.qid)]
        self.assertEqual(len(masts), 7)
        self.assertTrue(all(v[0] == "camera_mast" for _, v in masts))
        self.assertEqual(q.stage, "hunt")
        self.assertIs(s.world.tile_at(*q.lair.gate[0]), tiles.BLAST_DOOR)
        q.taken = True
        for i, (x, y) in enumerate(q.camp.spots):
            e = make_enemy("camera_mast", x, y, random.Random(i), (QUEST_SID, q.qid, i, 0))
            s.quests.on_death(e, s.me)
            if i == 0:
                self.assertEqual(q.found, 1)
                self.assertTrue(s.quests.screens)            # (the voice, on a screen near you)
                self.assertIn("6 still watch", s.quests.screens[0].line)
        self.assertEqual(q.stage, "awake")
        self.assertEqual(s.quests.banner.title, "THE TOWER IS BLIND")
        self.assertIs(s.world.tile_at(*q.lair.gate[0]), tiles.CELL_FLOOR)   # (the doors open)

    def test_the_fight_seals_the_hall_and_winning_opens_it(self):
        from ascii_adventurers.tests.test_m17 import step, teleport
        s, q = self.s, self.q
        s.quests.dev_key = "blind_the_eyes"
        self.assertTrue(s.quests.dev_finish_hunt())
        self.assertEqual(q.stage, "awake")
        self.assertTrue(alert.dark_at(s.world, *q.camp.spots[0]))
        lair = q.lair
        teleport(s, lair.cx - lair.radii[0] * 0.4, lair.cy)
        s.hero.hp = s.hero.max_hp = 10 ** 6
        step(s, 3)
        self.assertEqual(q.stage, "fight")
        self.assertIsInstance(q.boss, Overseer)
        self.assertEqual(s.quests.banner.sub, "in the hall of cells")
        step(s, 30)
        self.assertTrue(all(s.world.tile_at(*t) is tiles.BLAST_DOOR for t in lair.gate))
        b = q.boss
        self.assertTrue(lair.inside(b.x, b.y))
        b.hp = 0
        step(s, 2)
        self.assertEqual(q.stage, "cleared")
        self.assertIs(s.world.tile_at(*lair.gate[0]), tiles.CELL_FLOOR)
        self.assertIn("overseer", s.app.guild.pages)


def _eye(**kw):
    """An Overseer in an open hall (no lair: an oval round where it woke)."""
    o = make_enemy("overseer", 40.5, 30.5, random.Random(kw.pop("seed", 1)))
    a = Arena(o, w=82, h=62, hero_at=kw.pop("hero_at", (40.5, 36.5)), walls=kw.pop("walls", ()))
    a.hero.hp = a.hero.max_hp = 10 ** 6
    o._rest = 99.0                                       # (no moves unless a test starts one)

    def recruit(key, x, y):
        e = enemy(key, x, y, len(a.enemies))
        a.enemies.append(e)
        return e
    o.recruit = recruit
    return o, a


class OverseerTest(unittest.TestCase):
    def test_it_slides_round_its_rail_watching_you(self):
        o, a = _eye()
        cx, cy, ra, rb = o.arena()
        k = config.OVERSEER_RAIL[0]
        seen = []
        for _ in range(4):
            run(a, 0.5)
            seen.append((o.x, o.y))
            self.assertAlmostEqual(((o.x - cx) / (ra * k)) ** 2 + ((o.y - cy) / (rb * k)) ** 2, 1.0,
                                   delta=0.01)
            self.assertAlmostEqual(o.facing, math.atan2(a.hero.y - o.y, a.hero.x - o.x), delta=0.05)
        self.assertGreater(math.hypot(seen[-1][0] - seen[0][0], seen[-1][1] - seen[0][1]), 3.0)

    def test_the_gaze_fills_its_alert_and_the_pillars_hide_you(self):
        o, a = _eye()
        o.gaze_a = 0.0
        run(a, 3.0)
        self.assertGreater(o.meter, 10.0)                    # (out in the open: seen)
        self.assertEqual(o.bars()[0][0][:8], "ALERT --")
        walls = [(x, y) for x in range(30, 52) for y in (33, 34)]
        h, b = _eye(walls=walls)
        run(b, 3.0)
        self.assertEqual(h.meter, 0.0)                        # (a wall between)
        o.meter, o.quiet = 50.0, 0.0
        a.hero.x, a.hero.y = 0.0, 0.0                         # (gone: out of the hall)
        run(a, config.OVERSEER_GAZE[5] - 0.2)
        self.assertAlmostEqual(o.meter, 50.0, delta=0.01)
        run(a, 1.0)
        self.assertLess(o.meter, 50.0)

    def test_lockdown_opens_every_cell_and_hastens_it(self):
        o, a = _eye()
        o.meter = 99.9
        o.seeing = a.hero
        o.gaze_a = math.atan2(a.hero.y - o.y, a.hero.x - o.x)
        run(a, 0.3)
        self.assertEqual(o.level, alert.LOCKDOWN)
        adds = [e for e in a.enemies if e is not o]
        self.assertEqual(len(adds), config.OVERSEER_GAZE[10])
        self.assertEqual(o.gaze_haste, config.OVERSEER_GAZE[9])

    def test_each_phase_a_signature(self):
        o, a = _eye()
        for ph, (frac, name) in enumerate(((0.74, "THE CELLS"), (0.49, "THE LASER GRID"),
                                           (0.24, "THE RECORDINGS")), start=1):
            o.hp = o.max_hp * frac
            run(a, DT * 2)
            self.assertEqual(o.phase, ph)
            self.assertEqual(o.banner_req[0], name)

    def test_the_cells_open_and_lock_you_in(self):
        o, a = _eye()
        o.phase = 1
        o.cell_t = 0.0
        run(a, DT * 2)
        self.assertEqual(len([e for e in a.enemies if e is not o]), config.OVERSEER_CELLS[1])
        o._start("cell")
        o._wait = 0.0
        run(a, DT)
        self.assertIsNotNone(o.lock)
        cx, cy = o.lock[0], o.lock[1]
        run(a, config.OVERSEER_CELLS[4] + 0.1)
        bars = [(x, y) for y in range(25, 45) for x in range(30, 52)
                if a.world.tile_at(x, y) is tiles.CELL_BARS]
        self.assertGreater(len(bars), 6)
        self.assertEqual(len(bars), 16)                      # (every tile round you, closed)
        for x, y in bars:
            self.assertEqual(max(abs(x - math.floor(cx)), abs(y - math.floor(cy))),
                             config.OVERSEER_CELLS[3])
        run(a, config.OVERSEER_CELLS[5] + 0.2)               # (they open again)
        self.assertFalse(any(a.world.tile_at(x, y) is tiles.CELL_BARS for x, y in bars))

    def test_the_laser_grid_burns_where_its_beams_lie(self):
        o, a = _eye()
        o.phase = 2
        for kind in ("sweep", "cross", "box"):
            o.grid = [kind, 0.5, 0.3]
            beams = o.grid_beams()
            self.assertTrue(beams, kind)
            for x0, y0, x1, y1 in beams:
                for x, y in ((x0, y0), (x1, y1)):           # (each ends at the hall's edge)
                    cx, cy, ra, rb = o.arena()
                    self.assertAlmostEqual(((x - cx) / ra) ** 2 + ((y - cy) / rb) ** 2, 1.0, delta=0.02)
        o.grid = ["cross", 0.0, 0.0]
        cx, cy, _, _ = o.arena()
        a.hero.x, a.hero.y = cx + 10.0, cy                   # (on the cross's first beam)
        o.grid[1] = 0.0
        config_rate = config.OVERSEER_GRID[5]
        hp = a.hero.hp
        o._grid(type("C", (), {"players": [a.hero], "events": [], "effects": a.effects,
                               "world": a.world})(), 0.01)
        self.assertLess(a.hero.hp, hp)
        self.assertGreater(config_rate, 0)

    def test_it_records_you_and_your_copy_walks_your_path(self):
        from ascii_adventurers.systems import patterns
        o, a = _eye(hero_at=(30.5, 36.5))
        o.phase = 3
        o.rec_t = 99.0
        for k in range(round(config.OVERSEER_REC[1] * 60) + 10):
            a.hero.x += 0.08
            if k == 30:
                patterns.shoot(a.hero, a.hero.x, a.hero.y, 1.0, config.PANOPTICON_SHOTS["drone_bolt"],
                               a.projectiles)
            run(a, DT)
        o.rec_t = 0.0
        run(a, DT)
        copies = [e for e in a.enemies if isinstance(e, Recording)]
        self.assertEqual(len(copies), 1)
        c = copies[0]
        self.assertIs(c.of, a.hero)
        self.assertLess(c.x, a.hero.x - 3.0)                 # (where you were a while ago)
        self.assertEqual(len(c.shots), 1)
        n = len(a.projectiles)
        x0 = c.x
        run(a, 1.0)
        self.assertGreater(c.x, x0 + 2.0)                    # (walking your path)
        self.assertTrue(any(getattr(p, "recorded", False) and p.owner is o for p in a.projectiles)
                        or len(a.projectiles) > n)
        run(a, config.OVERSEER_REC[1])
        self.assertFalse(c.alive)
        self.assertTrue(c.left)                              # (played out: no kill)

    def test_its_four_moves(self):
        o, a = _eye()
        run(a, DT)
        o._start("sweep")
        o._wait = 0.0
        hp = a.hero.hp
        run(a, config.OVERSEER_SWEEP[1] + config.OVERSEER_SWEEP[2] + 0.2)
        self.assertLess(a.hero.hp, hp)                       # (the arc ran across you)
        o._start("salvo")
        o._wait = 0.0
        run(a, DT)
        self.assertEqual(len(o.missiles), config.OVERSEER_SALVO[0])
        hp = a.hero.hp
        run(a, config.OVERSEER_SALVO[2] + 0.2)
        self.assertLess(a.hero.hp, hp)
        o._start("drop")
        o._wait = 0.0
        a.hero.x, a.hero.y = o.x + 5.0, o.y
        hp = a.hero.hp
        run(a, config.OVERSEER_DROP[0] + 0.2)
        self.assertTrue(o.planted)
        self.assertEqual(o.low, 1.0)
        hp_o = o.hp
        o.take_damage(100.0, a.hero, 0.0)
        self.assertAlmostEqual(hp_o - o.hp, 100.0 * config.OVERSEER_RAIL[3], delta=1.0)   # (low: easier)
        run(a, 1.0)
        self.assertLess(a.hero.hp, hp)                       # (the ring)
        run(a, 4.0)
        self.assertFalse(o.planted)
        self.assertEqual(o.low, 0.0)
        o._start("scan")
        o._wait = 0.0
        run(a, DT)
        squares, _, _ = o.scan
        size = config.OVERSEER_SCAN[0]
        x0, y0 = squares[len(squares) // 2]
        a.hero.x, a.hero.y = x0 + size / 2, y0 + size / 2    # (on a lit square)
        hp = a.hero.hp
        run(a, config.OVERSEER_SCAN[1] + 0.1)
        self.assertLess(a.hero.hp, hp)


class DrawTest(unittest.TestCase):
    def test_draws_the_masts_the_voice_and_the_fight(self):
        from ascii_adventurers.tests.test_m17 import step, teleport
        m, s = _game()
        q = s.quests.states["blind_the_eyes"]
        x, y = q.camp.spots[0]
        teleport(s, x - 8, y)
        e = s.spawner.wake("camera_mast", x, y, (QUEST_SID, q.qid, 0, 0))
        s.enemies.append(e)
        step(s, 2)
        s.draw(m.text)
        s.quests.dev_key = "blind_the_eyes"
        s.quests.dev_finish_hunt()
        lair = q.lair
        teleport(s, lair.cx - lair.radii[0] * 0.3, lair.cy)
        s.hero.hp = s.hero.max_hp = 10 ** 6
        step(s, 3)
        b = q.boss
        b.phase = 3
        b.grid = ["box", 0.5, 0.2]
        b.missiles = [[s.hero.x, s.hero.y, 0.5]]
        b.ring, b.arcs, b.lock = 3.0, 0.3, (s.hero.x, s.hero.y, 0.5)
        b.sweep = (0.0, 1.0, 0.5, 20.0)
        b.scan = ([(s.hero.x - 2, s.hero.y - 2)], 0.2, False)
        b.low = 1.0
        b.seeing = s.hero
        c = s.spawner.wake("recording", s.hero.x + 3, s.hero.y, None, random.Random(1))
        c.setup(s.hero, [(0.0, s.hero.x + 3, s.hero.y, False), (2.0, s.hero.x + 6, s.hero.y, False)],
                [], b)
        s.enemies.append(c)
        s.draw(m.text)
        self.assertEqual(s._meter(s.hero)[0], "ALR")


if __name__ == "__main__":
    unittest.main()
