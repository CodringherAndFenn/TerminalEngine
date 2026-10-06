"""M23.2: the desert's second boss, Ol' Spitter, the Unmannered One (a
camel whose humps hold his spit: dry, he drinks at a trough -- smash it and
he chokes; and his ricochet loogie), the caravan master's "collect" quest
(cargo guarded by mangy camels), the mirages, and the caravanserai."""

import math
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.ai import make_enemy
from ascii_adventurers.ai.bosses import OlSpitter
from ascii_adventurers.ai.brain import AIContext
from ascii_adventurers.systems.quests import QUEST_SID
from ascii_adventurers.tests.test_m17 import game, step, teleport, world
from ascii_adventurers.tests.test_m22_5 import finish
from ascii_adventurers.tests.test_weapons import hero, open_map
from ascii_adventurers.world import tiles
from ascii_adventurers.world.landmarks import Landmark, quest_marks, trough_tiles
from ascii_adventurers.world.test_map import LEGEND, TestMap

DT = 1 / 60


def spitter_at(x=30.0, y=20.0):
    b = make_enemy("ol_spitter", x, y, random.Random(4))
    b.scale_to_level(1)
    return b


def yard(w=120, h=40, troughs=((20, 10), (90, 30)), walls=()):
    """An open map with water troughs (6 x 1 tiles from (x, y)) and a lair
    over all of it, its spots: the middle, then the troughs' middles."""
    rows = [["."] * w for _ in range(h)]
    for x, y in troughs:
        for k in range(6):
            rows[y][x + k] = "="
    for x, y in walls:
        rows[y][x] = "#"
    m = TestMap(["".join(r) for r in rows], dict(LEGEND, **{"=": tiles.TROUGH}))
    spots = [(w / 2, h / 2)] + [(x + 3.0, y + 0.5) for x, y in troughs]
    lair = Landmark("caravanserai", "lair", "desert", "YARD", 0, 0, [], cx=w / 2, cy=h / 2,
                    spots=spots, radii=(w / 2 - 1, h / 2 - 1))
    return m, lair


def think(b, h, w, seconds, shots=None, actors=None):
    shots = [] if shots is None else shots
    for _ in range(round(seconds * 60)):
        b.think(AIContext(w, [h], actors if actors is not None else [h, b], shots, []), DT)
    return shots


class CaravanseraiTest(unittest.TestCase):
    def test_camp_and_caravanserai_in_the_desert(self):
        for seed in (1, 2, 31, 999):
            w = world(seed)
            camp, lair = quest_marks(w.layout, "caravan_master")
            self.assertEqual((camp.key, lair.key), ("oasis_camp", "caravanserai"), seed)
            for m in (camp, lair):
                self.assertEqual(w.layout.biome_at(m.cx, m.cy).name, "desert", seed)
            self.assertIs(lair.floor, tiles.FLAGSTONE)
            self.assertEqual(len(lair.spots), 1 + config.CARAVAN_TROUGHS)
            for x, y in camp.spots:
                self.assertEqual(w.layout.biome_at(x, y).name, "desert", seed)

    def test_its_yard_troughs_arches_and_posts(self):
        w = world(31)
        camp, lair = quest_marks(w.layout, "caravan_master")
        flat = {t for row in lair.rows for t in row if t is not None}
        self.assertTrue({tiles.MUDBRICK, tiles.FLAGSTONE, tiles.ARCH, tiles.TROUGH,
                         tiles.TETHER_POST, tiles.HAY} <= flat)
        self.assertNotIn(tiles.SANDSTONE, flat)
        x, y = lair.spots[0]                         # he sleeps in the open middle
        self.assertFalse(w.tile_at(math.floor(x), math.floor(y)).solid)
        for s in lair.spots[1:]:
            self.assertTrue(all(w.tile_at(tx, ty) is tiles.TROUGH for tx, ty in trough_tiles(*s)))
        # The camp has crates instead of the collector's stalls, and the
        # cargo sits in sandy clearings.
        cflat = {t for row in camp.rows for t in row if t is not None}
        self.assertIn(tiles.CRATES, cflat)
        self.assertNotIn(tiles.STALL, cflat)
        x, y = camp.spots[0]
        self.assertIs(w.tile_at(math.floor(x), math.floor(y)), tiles.CARGO)

    def test_new_tiles_have_map_colors(self):
        from ascii_adventurers import palette
        for t in (tiles.MUDBRICK, tiles.FLAGSTONE, tiles.ARCH, tiles.TROUGH, tiles.TROUGH_BROKEN,
                  tiles.TETHER_POST, tiles.HAY, tiles.CARGO, tiles.CRATES):
            self.assertTrue(t.name in palette.MAP_TILE or t.name in palette.MAP_TILE_BIOME, t.name)
            self.assertNotIn("~", "".join(t.glyphs), t.name)  # (VT323's "~" looks like an N)

    def test_a_trough_can_be_smashed(self):
        m, _ = yard()
        self.assertTrue(tiles.TROUGH.destructible)
        m.damage_tile(20, 10, config.TROUGH_HP)
        self.assertIs(m.tile_at(20, 10), tiles.TROUGH_BROKEN)
        self.assertFalse(tiles.TROUGH_BROKEN.solid)


class CamelTest(unittest.TestCase):
    def test_a_camel_rears_then_spits_a_fan(self):
        w = open_map(w=80, h=40)
        e = make_enemy("mangy_camel", 40.0, 20.0, random.Random(1))
        h = hero("wizard", 32.0, 20.0)
        shots = []
        reared = False
        for _ in range(60 * 4):
            e.think(AIContext(w, [h], [h, e], shots, []), DT)
            reared |= e.rear > 0
            if shots:
                break
        self.assertTrue(reared)                              # the tell came first
        self.assertEqual(len(shots), config.CAMEL_FAN[0])
        self.assertTrue(all(p.owner is e for p in shots))

    def test_a_mangy_camel_stays_by_its_cargo(self):
        w = open_map(w=80, h=40)
        e = make_enemy("mangy_camel", 40.0, 20.0, random.Random(1))
        h = hero("wizard", 2.0, 2.0)
        for _ in range(60 * 20):
            e.think(AIContext(w, [h], [h, e], [], []), DT)
        self.assertLess(math.hypot(e.x - 40, e.y - 20), config.CAMEL_LEASH + 2)

    def test_a_mirage_pops_at_a_touch(self):
        e = make_enemy("mirage", 40.0, 20.0, random.Random(1))
        e.scale_to_level(20)
        e.take_damage(1, None, 0.0)
        self.assertFalse(e.alive)
        m = make_enemy("mangy_camel", 40.0, 20.0, random.Random(1))
        m.take_damage(1, None, 0.0)
        self.assertTrue(m.alive)


class ThirstTest(unittest.TestCase):
    def setUp(self):
        self.h = hero("wizard", 110.0, 3.0)
        self.h.invulnerable = True

    def spitter(self, w, lair, x=50.0, y=20.0):
        b = spitter_at(x, y)
        b.lair = lair
        b._rest = 0.0
        b.ctx = AIContext(w, [self.h], [self.h, b], [], [])
        return b

    def test_spitting_empties_his_humps(self):
        w, lair = yard()
        b = self.spitter(w, lair)
        b._pick_move = lambda: "fan"
        full = b.water
        think(b, self.h, w, 3.0)
        self.assertEqual(b.water, full - config.HUMP_COST["fan"])
        self.assertLess(b.hump_frac[0], 1.0)

    def test_dry_he_drinks_kneeling_and_gets_up_full(self):
        w, lair = yard()
        b = self.spitter(w, lair)
        b.water = 0.0
        self.assertEqual(b._pick_move(), "drink")
        knelt = False
        for _ in range(60 * 14):
            b.think(AIContext(w, [self.h], [self.h, b], [], []), DT)
            if b.kneeling and not knelt:
                knelt = True
                hp = b.hp
                b.take_damage(100, None, 0.0)
                self.assertAlmostEqual(hp - b.hp, 100 * config.DRINK[1])   # the melee window
            if b.last_move == "drink":
                break
        self.assertTrue(knelt)
        self.assertEqual(b.water, config.HUMP_WATER)
        self.assertLess(math.hypot(b.x - 23.0, b.y - 10.5), 5.0)    # at the nearer trough

    def test_smash_the_trough_and_he_chokes(self):
        w, lair = yard()
        b = self.spitter(w, lair)
        b.water = 0.0
        b._pick_move = lambda: "drink"
        effects = []
        for _ in range(60 * 10):
            b.think(AIContext(w, [self.h], [self.h, b], [], effects), DT)
            if b.kneeling:
                break
        self.assertTrue(b.kneeling)
        tx, ty = trough_tiles(*b.drinking_at)[2]
        w.damage_tile(tx, ty, config.TROUGH_HP)
        b.think(AIContext(w, [self.h], [self.h, b], [], effects), DT)
        self.assertFalse(b.kneeling)
        self.assertGreater(b.dazed, config.CHOKE_STUN - 0.1)
        self.assertLess(b.water, config.HUMP_WATER)
        self.assertTrue(any(e.kind == "toast" and "CHOKES" in e.label for e in effects))

    def test_no_troughs_left_and_hes_parched(self):
        w, lair = yard()
        b = self.spitter(w, lair)
        self.assertFalse(b.parched)
        for s in lair.spots[1:]:
            tx, ty = trough_tiles(*s)[0]
            w.damage_tile(tx, ty, config.TROUGH_HP)
        self.assertTrue(b.parched)
        b.water = 0.0
        self.assertEqual(b._cost("loogie"), 0)
        for _ in range(30):
            self.assertNotEqual(b._pick_move(), "drink")
        self.assertLess(b.speed_mult, 1.0)                  # slower...
        b._end_move()
        self.assertLess(b._rest, config.BOSSES["ol_spitter"].phases[0].rest)   # ...but angrier


class SpitterTest(unittest.TestCase):
    def setUp(self):
        self.h = hero("wizard", 5.0, 3.0)
        self.h.invulnerable = True

    def test_a_loogie_bounces_and_splits(self):
        w = open_map(w=90, h=30, walls=[(60, y) for y in range(30)])
        b = spitter_at(20.0, 15.0)
        b._rest = 99.0
        b.ctx = AIContext(w, [self.h], [self.h, b], [], [])
        b.loogies.append([40.0, 15.0, config.LOOGIE_SPEED, 0.0, config.LOOGIE_RADIUS, 0, 0.0,
                          set()])
        think(b, self.h, w, 2.0)
        self.assertGreaterEqual(len(b.loogies), 2)
        self.assertTrue(all(g[5] >= 1 for g in b.loogies))           # a new generation
        self.assertTrue(all(g[2] < 0 for g in b.loogies))            # off the wall, back
        self.assertTrue(all(g[4] < config.LOOGIE_RADIUS for g in b.loogies))
        think(b, self.h, w, config.LOOGIE_LIFE)
        self.assertEqual(b.loogies, [])

    def test_a_loogie_hits_and_pops(self):
        w = open_map(w=90, h=30)
        b = spitter_at(20.0, 15.0)
        b._rest = 99.0
        h = hero("wizard", 50.0, 15.0)
        h.max_hp = h.hp = 10 ** 6
        b.loogies.append([40.0, 15.0, config.LOOGIE_SPEED, 0.0, config.LOOGIE_RADIUS, 0, 0.0,
                          set()])
        think(b, h, w, 1.5)
        self.assertLess(h.hp, 10 ** 6)
        self.assertEqual(b.loogies, [])

    def test_the_loogie_tell_traces_its_bounces(self):
        w = open_map(w=90, h=30, walls=[(60, y) for y in range(30)])
        b = spitter_at(20.0, 15.0)
        b.ctx = AIContext(w, [self.h], [self.h, b], [], [])
        pts = b._trace(30.0, 15.0, 0.0)
        self.assertGreaterEqual(len(pts), 3)
        self.assertAlmostEqual(pts[1][0], 60.0, delta=1.0)           # the first bounce

    def test_linger_behind_him_and_he_kicks(self):
        w = open_map(w=90, h=30)
        b = spitter_at(40.0, 15.0)
        b.facing = 0.0
        b._rest = 1.5
        h = hero("dwarf", 35.5, 15.0)                                 # right behind him
        h.max_hp = h.hp = 10 ** 6
        x0 = h.x
        for _ in range(60 * 3):
            b.think(AIContext(w, [h], [h, b], [], []), DT)
            if b.last_move == "kick":
                break
        self.assertEqual(b.last_move, "kick")
        self.assertLess(h.hp, 10 ** 6)
        self.assertLess(h.x, x0 - 2.0)                                # thrown back

    def test_he_cant_spit_over_his_back(self):
        b = spitter_at()
        b.facing = 0.0
        self.assertAlmostEqual(b.spit_angle(2.8), math.radians(config.SPITTER_SPIT_ARC))
        self.assertAlmostEqual(b.spit_angle(-2.8), -math.radians(config.SPITTER_SPIT_ARC))
        self.assertAlmostEqual(b.spit_angle(0.3), 0.3)

    def test_a_gallop_churns_sand_and_a_wall_dazes_him(self):
        w = open_map(w=90, h=30, walls=[(x, y) for x in (56, 57) for y in range(30)])
        b = spitter_at(20.0, 15.0)
        b._rest = 0.0
        b._pick_move = lambda: "gallop"
        h = hero("wizard", 70.0, 15.0)
        h.invulnerable = True
        dazed = False
        for _ in range(60 * 4):
            b.think(AIContext(w, [h], [h, b], [], []), DT)
            dazed |= b.dazed > 0
        self.assertTrue(dazed)
        self.assertLess(b.x, 56)
        self.assertTrue(b.trail or dazed)

    def test_the_stampede_runs_rows_with_a_gap(self):
        w = open_map(w=120, h=40, walls=[(70, y) for y in range(40)])
        b = spitter_at(10.0, 20.0)
        b._rest = 0.0
        b._pick_move = lambda: "stampede"
        h = hero("wizard", 60.0, 20.0)
        h.invulnerable = True
        _, rows, _, _, half, spacing, gap, *_ = config.SPITTER_STAMPEDE
        most = 0
        for _ in range(60 * 6):
            b.think(AIContext(w, [h], [h, b], [], []), DT)
            most = max(most, len(b.ghosts))
            if b.last_move == "stampede":
                break
        b._rest = 99.0
        full_row = int(2 * half / spacing) + 1
        self.assertGreater(most, 0)
        self.assertLess(most, rows * full_row)                       # gaps
        think(b, h, w, 6.0)
        self.assertEqual(b.ghosts, [])                               # they run off and fade

    def test_mirages_are_capped(self):
        w = open_map(w=90, h=30)
        b = spitter_at()
        adds = []

        def recruit(k, x, y):
            e = make_enemy(k, x, y, random.Random(len(adds)))
            adds.append(e)
            return e
        b.recruit = recruit
        b._rest = 0.0
        b._pick_move = lambda: "mirage"
        for _ in range(60 * 8):
            b.think(AIContext(w, [self.h], [self.h, b] + adds, [], []), DT)
        self.assertEqual(len(adds), config.SPITTER_MIRAGE[2])
        self.assertTrue(all(a.kind_key == "mirage" for a in adds))

    def test_every_move_runs_to_the_end(self):
        names = {m for ph in config.BOSSES["ol_spitter"].phases for m, _ in ph.moves}
        names |= {"kick", "drink"}
        for phase in (0, 2):
            for name in sorted(names):
                w, lair = yard()
                b = spitter_at(50.0, 20.0)
                b.lair = lair
                b.phase = phase
                b.recruit = lambda k, x, y: make_enemy(k, x, y, random.Random(2))
                b._rest = 0.0
                b._pick_move = lambda name=name: name
                done = False
                for _ in range(60 * 20):
                    b.think(AIContext(w, [self.h], [self.h, b], [], []), DT)
                    if b.last_move == name:
                        done = True
                        break
                self.assertTrue(done, (phase, name))
                self.assertTrue(b.hittable, name)
                self.assertFalse(b.rear or b.kneeling or b.galloping or b.kicking or b.spinning,
                                 name)


class QuestTest(unittest.TestCase):
    def tearDown(self):
        config.QUEST_FOCUS = None

    def test_cargo_is_guarded_and_taken(self):
        m, s = game(seed=31)
        q = s.quests
        st = q.states["caravan_master"]
        self.assertEqual(st.spec.kind, "collect")
        sp = s.spawner
        guards = [(QUEST_SID, st.qid, 0, k + 1) for k in range(config.CARGO_GUARDS)]
        self.assertTrue(all(g in sp.fixed for g in guards))
        s.hero.invulnerable = True
        x, y = st.camp.spots[0]
        teleport(s, x + 1.5, y + 1.5)
        step(s, 3)
        self.assertEqual(q.guards_left(st, 0), config.CARGO_GUARDS)
        self.assertEqual(st.found, 0)                                # not with them about
        camels = [sp.awake[g] for g in guards if g in sp.awake]
        self.assertEqual(len(camels), config.CARGO_GUARDS)
        s.draw(m.text)
        for e in camels:
            e.hp = 0.0
            e.last_hit_by = s.hero
        step(s, 2)
        self.assertEqual(q.guards_left(st, 0), 0)
        self.assertEqual(st.found, 1)
        self.assertIn(0, st.lit)
        self.assertIs(s.world.tile_at(math.floor(x), math.floor(y)), tiles.SAND)

    def test_the_whole_fight(self):
        m, s = game(seed=31)
        q = s.quests
        st = q.states["caravan_master"]
        finish(q, "caravan_master")
        self.assertEqual(st.stage, "awake")
        s.hero.invulnerable = True
        lair = st.lair
        teleport(s, lair.cx + 20, lair.cy + 6)
        step(s, 1)
        self.assertEqual(st.stage, "fight")
        b = st.boss
        self.assertIsInstance(b, OlSpitter)
        step(s, 1)                                                   # (he's thought once)
        self.assertTrue(b.thirsty)
        self.assertEqual(len(b.troughs()), config.CARAVAN_TROUGHS)
        step(s, 300)
        s.draw(m.text)
        b.hp = 0.0
        b.last_hit_by = s.hero
        step(s)
        self.assertEqual(st.stage, "cleared")
        self.assertIn("ol_spitter", m.app.guild.achievements)
        self.assertEqual(m.app.guild.journal["caravan_master"]["wins"], 1)
        self.assertTrue(all(s.world.tile_at(*t) is tiles.FLAGSTONE for t in lair.gate))

    def test_dev_finish_clears_the_guards_and_cargo(self):
        m, s = game(seed=31)
        config.QUEST_FOCUS = "caravan_master"
        st = s.quests.states["caravan_master"]
        self.assertTrue(s.quests.dev_finish_hunt())
        self.assertEqual(st.stage, "awake")
        self.assertEqual(s.quests.guards_left(st, 0), 0)
        x, y = st.camp.spots[0]
        self.assertIs(s.world.tile_at(math.floor(x), math.floor(y)), tiles.SAND)


if __name__ == "__main__":
    unittest.main()
