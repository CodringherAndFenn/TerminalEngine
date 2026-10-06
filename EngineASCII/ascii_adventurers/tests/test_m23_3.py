"""M23.3: the desert's third boss, the Nameless Magus, Holder of Time (a
signature a phase: sand runes you scuff out, shifting dunes, the
hourglass and its time zones), the runaway apprentice's "survive" quest
(star circles held while sand elementals rise), his creatures, and the
sunken observatory."""

import math
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.ai import make_enemy
from ascii_adventurers.ai.bosses import Magus
from ascii_adventurers.ai.brain import AIContext
from ascii_adventurers.entities.projectile import Projectile
from ascii_adventurers.tests.test_m17 import game, step, teleport, world
from ascii_adventurers.tests.test_m22_5 import finish
from ascii_adventurers.tests.test_weapons import hero, open_map
from ascii_adventurers.world import tiles
from ascii_adventurers.world.landmarks import quest_marks

DT = 1 / 60


def magus_at(x=30.0, y=20.0):
    b = make_enemy("nameless_magus", x, y, random.Random(4))
    b.scale_to_level(1)
    b._rest = 99.0
    return b


class Fight:
    """A Magus on an open map with one hero and his adds (recruited)."""

    def __init__(self, w=120, h=40, walls=(), hx=60.0, hy=20.0, bx=30.0, by=20.0):
        self.w = open_map(w=w, h=h, walls=walls)
        self.b = magus_at(bx, by)
        self.h = hero("wizard", hx, hy)
        self.h.max_hp = self.h.hp = 10 ** 6
        self.adds = []
        self.shots = []
        self.effects = []

        def recruit(k, x, y):
            e = make_enemy(k, x, y, random.Random(len(self.adds)))
            self.adds.append(e)
            return e
        self.b.recruit = recruit
        self.b.ctx = self.ctx()

    def ctx(self):
        return AIContext(self.w, [self.h], [self.h, self.b] + [a for a in self.adds if a.alive],
                         self.shots, self.effects)

    def run(self, seconds, move=None):
        if move is not None:
            self.b._rest = 0.0
            self.b._pick_move = lambda: move
        for _ in range(round(seconds * 60)):
            self.b.think(self.ctx(), DT)
            if move is not None and self.b.last_move == move:
                self.b._rest = 99.0
                self.b._pick_move = lambda: "blink"
                move = None


class ObservatoryTest(unittest.TestCase):
    def test_camp_and_observatory_in_the_desert(self):
        for seed in (1, 2, 31, 999):
            w = world(seed)
            camp, lair = quest_marks(w.layout, "runaway_apprentice")
            self.assertEqual((camp.key, lair.key), ("oasis_camp", "observatory"), seed)
            for m in (camp, lair):
                self.assertEqual(w.layout.biome_at(m.cx, m.cy).name, "desert", seed)
            self.assertIs(lair.floor, tiles.SLABS)

    def test_its_star_chart_columns_and_telescope(self):
        w = world(31)
        camp, lair = quest_marks(w.layout, "runaway_apprentice")
        flat = {t for row in lair.rows for t in row if t is not None}
        self.assertTrue({tiles.GLAZED, tiles.SLABS, tiles.STAR_CHART, tiles.COLUMN, tiles.BRASS,
                         tiles.DRIFT} <= flat)
        x, y = lair.spots[0]
        self.assertIs(w.tile_at(math.floor(x), math.floor(y)), tiles.STAR_CHART)
        cflat = {t for row in camp.rows for t in row if t is not None}
        self.assertIn(tiles.SCROLLS, cflat)
        x, y = camp.spots[0]                        # a sealed star circle
        self.assertIs(w.tile_at(math.floor(x), math.floor(y)), tiles.SEAL)
        spot = next(m for m in w.layout.landmarks if m.kind == "spot" and m.quest ==
                    "runaway_apprentice")
        self.assertIn(tiles.STAR_RING, {t for row in spot.rows for t in row})

    def test_new_tiles_have_map_colors(self):
        from ascii_adventurers import palette
        for t in (tiles.GLAZED, tiles.SLABS, tiles.STAR_CHART, tiles.COLUMN, tiles.BROKEN_COLUMN,
                  tiles.BRASS, tiles.DRIFT, tiles.STAR_RING, tiles.SEAL, tiles.SEAL_BROKEN,
                  tiles.DUNE_WALL, tiles.SCROLLS):
            self.assertTrue(t.name in palette.MAP_TILE or t.name in palette.MAP_TILE_BIOME, t.name)
            self.assertNotIn("~", "".join(t.glyphs), t.name)


class CreatureTest(unittest.TestCase):
    def test_an_elemental_throws_sand_and_blinks(self):
        w = open_map(w=80, h=40)
        e = make_enemy("sand_elemental", 40.0, 20.0, random.Random(1))
        h = hero("wizard", 32.0, 20.0)
        shots = []
        gone = False
        for _ in range(60 * 8):
            e.think(AIContext(w, [h], [h, e], shots, []), DT)
            gone |= not e.hittable
        self.assertTrue(shots)
        self.assertTrue(gone)                          # it blinked at least once
        self.assertTrue(e.hittable)

    def test_a_golem_raises_its_fists_then_slams(self):
        w = open_map(w=80, h=40)
        e = make_enemy("sand_golem", 40.0, 20.0, random.Random(1))
        h = hero("wizard", 41.5, 20.0)
        h.max_hp = h.hp = 10 ** 6
        raised = False
        for _ in range(60 * 3):
            e.think(AIContext(w, [h], [h, e], [], []), DT)
            raised |= e.windup > 0
        self.assertTrue(raised)
        self.assertLess(h.hp, 10 ** 6)

    def test_a_sigil_drifts_after_you_and_pops(self):
        w = open_map(w=80, h=40)
        e = make_enemy("sigil", 30.0, 20.0, random.Random(1))
        h = hero("wizard", 40.0, 20.0)
        h.max_hp = h.hp = 10 ** 6
        for _ in range(60 * 4):
            e.think(AIContext(w, [h], [h, e], [], []), DT)
            if not e.alive:
                break
        self.assertFalse(e.alive)
        self.assertLess(h.hp, 10 ** 6)
        s = make_enemy("sigil", 30.0, 20.0, random.Random(1))
        s.scale_to_level(20)
        s.take_damage(1, None, 0.0)                    # one hit of anything
        self.assertFalse(s.alive)


class RuneTest(unittest.TestCase):
    def test_a_rune_charges_and_fires(self):
        f = Fight(hx=60.0)
        f.run(1.5, "runes")
        self.assertEqual(len(f.b.runes), config.RUNE_BATCH[0])
        for r in f.b.runes:
            r["kind"] = "fire"
            self.assertGreaterEqual(math.hypot(r["x"] - f.h.x, r["y"] - f.h.y),
                                    config.RUNE_RANGE[0] - 0.1)
        f.h.x, f.h.y = 5.0, 3.0                        # (out of them all)
        f.run(config.RUNE_CHARGE)
        self.assertEqual(f.b.runes, [])
        self.assertTrue(any(p.owner is f.b for p in f.shots))
        self.assertEqual(f.b.dazed, 0.0)               # fired: no drain

    def test_scuff_a_whole_batch_and_hes_drained(self):
        f = Fight()
        f.run(1.5, "runes")
        runes = list(f.b.runes)
        self.assertTrue(runes)
        for r in runes:
            f.h.x, f.h.y = r["x"], r["y"]
            f.run(config.RUNE_SCUFF + 0.1)
        self.assertEqual(f.b.runes, [])
        self.assertTrue(f.b.drained)
        self.assertGreater(f.b.dazed, config.RUNE_DRAIN - 1.0)
        self.assertTrue(f.b.hittable)

    def test_rolling_through_one_scuffs_it(self):
        f = Fight()
        f.run(1.5, "runes")
        r = f.b.runes[0]
        f.h.x, f.h.y = r["x"], r["y"]
        f.h.roll_t = 0.2
        f.run(DT)
        self.assertNotIn(r, f.b.runes)


class DuneTest(unittest.TestCase):
    def test_walls_rise_block_and_collapse(self):
        f = Fight()
        f.b.phase = 1
        f.run(2.0, "dunes")
        self.assertTrue(f.b.walls)
        placed = [(tx, ty) for w in f.b.walls for tx, ty, _ in w["tiles"]]
        self.assertTrue(all(f.w.tile_at(tx, ty) is tiles.DUNE_WALL for tx, ty in placed))
        self.assertTrue(tiles.DUNE_WALL.blocks_shots and tiles.DUNE_WALL.destructible)
        self.assertEqual(len(f.b.quicksand), config.DUNE_PITS)
        f.run(config.DUNE_LIFE)
        self.assertEqual(f.b.walls, [])
        self.assertTrue(all(f.w.tile_at(tx, ty) is not tiles.DUNE_WALL for tx, ty in placed))
        self.assertTrue(any(p.owner is f.b for p in f.shots))       # sand thrown out

    def test_quicksand_slows_and_drags(self):
        f = Fight()
        f.b.quicksand.append([60.0, 20.0, 0.0])
        f.h.x = 62.0
        f.run(0.5)
        self.assertEqual(f.h.time_mult, config.QUICKSAND[1])
        self.assertLess(f.h.x, 62.0)
        f.h.x = 80.0
        f.run(DT)
        self.assertEqual(f.h.time_mult, 1.0)


class HourglassTest(unittest.TestCase):
    def plant(self):
        f = Fight(w=140, hx=70.0)
        f.b.phase = 2
        f.run(1.5, "hourglass")
        self.assertIsNotNone(f.b.glass)
        self.assertGreaterEqual(len(f.b.zones), 2)
        self.assertEqual({k for _, _, k in f.b.zones}, {"slow", "fast"})
        return f

    def test_time_zones_bend_walking_shots_and_adds(self):
        f = self.plant()
        zx, zy, _ = next(z for z in f.b.zones if z[2] == "slow")
        f.h.x, f.h.y = zx, zy
        p = Projectile(zx, zy, 0.0, config.MAGUS_SHOTS["sand"], owner=f.b)
        f.shots.append(p)
        add = make_enemy("sand_elemental", zx + 1, zy, random.Random(3))
        f.adds.append(add)
        f.run(DT)
        self.assertEqual(f.h.time_mult, config.TIME_SLOW)
        self.assertEqual(p.time_scale, config.TIME_SLOW)
        self.assertEqual(add.time_mult, config.TIME_SLOW)
        fx, fy, _ = next(z for z in f.b.zones if z[2] == "fast")
        f.h.x, f.h.y = fx, fy
        f.run(DT)
        self.assertEqual(f.h.time_mult, config.TIME_FAST_HERO)
        self.assertFalse(hasattr(f.b, "time_mult") and f.b.time_mult != 1.0)   # never him

    def test_shatter_it_and_he_is_stunned(self):
        f = self.plant()
        f.b.glass.hp = 0.0
        f.run(DT)
        self.assertIsNone(f.b.glass)
        self.assertEqual(f.b.zones, [])
        self.assertGreater(f.b.dazed, config.HOURGLASS[2] - 0.1)

    def test_times_up_rings_and_every_rune_fires(self):
        f = self.plant()
        f.b.runes.append(dict(x=10.0, y=10.0, kind="fire", charge=0.0, scuff=0.0, batch=99))
        f.h.x, f.h.y = 130.0, 38.0
        glass = f.b.glass
        f.run(config.HOURGLASS[0] + config.TIMES_UP_RING[2] * config.HOURGLASS[3] + 0.2)
        self.assertIsNone(f.b.glass)
        self.assertFalse(glass.alive)
        self.assertEqual(f.b.dazed, 0.0)
        self.assertEqual(f.b.runes, [])
        self.assertEqual(f.b.zones, [])
        time_shots = [p for p in f.shots if p.spec is config.MAGUS_SHOTS["time"]]
        self.assertGreater(len(time_shots), config.TIMES_UP_RING[0] * 2)


class MoveTest(unittest.TestCase):
    def test_the_lance_burns_but_a_wall_blocks_it(self):
        f = Fight(walls=[(45, y) for y in range(40)], hx=60.0)
        f.run(3.0, "lance")
        self.assertEqual(f.h.hp, 10 ** 6)              # behind the wall
        f = Fight(hx=40.0)
        f.run(3.0, "lance")
        self.assertLess(f.h.hp, 10 ** 6)

    def test_the_vortex_pulls_you_in(self):
        f = Fight(hx=60.0)
        f.b.phase = 1
        x0 = f.h.x
        seen = None
        for _ in range(60 * 6):
            f.b._rest = 0.0 if f.b.last_move != "vortex" else 99.0
            f.b._pick_move = lambda: "vortex"
            f.b.think(f.ctx(), DT)
            if f.b.vortex is not None and seen is None:
                seen = f.b.vortex
        self.assertIsNotNone(seen)
        self.assertLess(math.hypot(f.h.x - seen[0], f.h.y - seen[1]),
                        math.hypot(x0 - seen[0], 20.0 - seen[1]))

    def test_the_serpent_bursts_along_its_line(self):
        f = Fight(hx=60.0)
        f.run(4.0, "serpent")
        self.assertLess(f.h.hp, 10 ** 6)

    def test_sigils_are_capped(self):
        f = Fight()
        for _ in range(3):
            f.run(1.5, "sigils")
            f.b.last_move = None
        sigils = [a for a in f.adds if a.kind_key == "sigil"]
        self.assertLessEqual(len(sigils), config.MAGUS_SIGILS[2])

    def test_every_move_runs_to_the_end(self):
        names = {m for ph in config.BOSSES["nameless_magus"].phases for m, _ in ph.moves}
        for phase in (0, 2):
            for name in sorted(names):
                f = Fight(w=140, hx=70.0)
                f.b.phase = phase
                f.run(14.0, name)
                self.assertEqual(f.b.last_move, name, (phase, name))
                self.assertTrue(f.b.hittable, name)
                self.assertIsNone(f.b.beam, name)
                self.assertIsNone(f.b.vortex, name)

    def test_his_death_clears_the_field(self):
        f = Fight(w=140, hx=70.0)
        f.b.phase = 2
        f.run(2.0, "dunes")
        f.run(1.5, "hourglass")
        f.h.time_mult = 0.5
        f.b.on_death(f.ctx())
        self.assertEqual(f.b.walls, [])
        self.assertEqual(f.h.time_mult, 1.0)
        self.assertFalse(f.b.glass.alive)


class QuestTest(unittest.TestCase):
    def tearDown(self):
        config.QUEST_FOCUS = None

    def test_hold_a_circle_while_the_sand_rises(self):
        m, s = game(seed=31)
        q = s.quests
        st = q.states["runaway_apprentice"]
        self.assertEqual(st.spec.kind, "survive")
        s.hero.invulnerable = True
        x, y = st.camp.spots[0]
        teleport(s, x + 1.0, y)
        step(s, 60)
        self.assertGreater(st.heat.get(0, 0.0), 0.9)
        risen = [e for e in s.enemies if getattr(e, "kind_key", "") == "sand_elemental"]
        self.assertTrue(config.SEAL_WAVE_SIZE[0] <= len(risen) <= config.SEAL_WAVE_SIZE[1])
        s.draw(m.text)
        teleport(s, x + 20.0, y)                       # out: it heals
        worn = st.heat[0]
        step(s, 60)
        self.assertLess(st.heat[0], worn)
        teleport(s, x + 1.0, y)
        st.heat[0] = config.SEAL_TIME - 0.2
        step(s, 30)
        self.assertIn(0, st.lit)
        self.assertEqual(st.found, 1)
        self.assertIs(s.world.tile_at(math.floor(x), math.floor(y)), tiles.SEAL_BROKEN)

    def test_the_whole_fight(self):
        m, s = game(seed=31)
        q = s.quests
        st = q.states["runaway_apprentice"]
        finish(q, "runaway_apprentice")
        self.assertEqual(st.stage, "awake")
        s.hero.invulnerable = True
        lair = st.lair
        teleport(s, lair.cx + 20, lair.cy + 6)
        step(s, 1)
        self.assertEqual(st.stage, "fight")
        b = st.boss
        self.assertIsInstance(b, Magus)
        step(s, 300)
        s.draw(m.text)
        b.hp = 0.0
        b.last_hit_by = s.hero
        step(s)
        self.assertEqual(st.stage, "cleared")
        self.assertIn("nameless_magus", m.app.guild.achievements)
        self.assertEqual(m.app.guild.journal["runaway_apprentice"]["wins"], 1)
        self.assertTrue(all(s.world.tile_at(*t) is tiles.SLABS for t in lair.gate))
        self.assertEqual(s.hero.time_mult, 1.0)

    def test_dev_finish_breaks_the_seals(self):
        m, s = game(seed=31)
        config.QUEST_FOCUS = "runaway_apprentice"
        st = s.quests.states["runaway_apprentice"]
        self.assertTrue(s.quests.dev_finish_hunt())
        x, y = st.camp.spots[0]
        self.assertIs(s.world.tile_at(math.floor(x), math.floor(y)), tiles.SEAL_BROKEN)


if __name__ == "__main__":
    unittest.main()
