"""M24.1: the ruins' first boss, the Fallout King (a signature a phase:
rads and decontamination showers, fallout patches and isotope rods, the
meltdown core with its valves and lead walls), the hazmat scavenger's
"escort" quest, his creatures, and the reactor vault."""

import math
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.ai import make_enemy
from ascii_adventurers.ai.bosses import FalloutKing
from ascii_adventurers.ai.brain import AIContext
from ascii_adventurers.systems import roll
from ascii_adventurers.tests.test_m17 import game, step, teleport, world
from ascii_adventurers.tests.test_m22_5 import finish
from ascii_adventurers.tests.test_weapons import hero
from ascii_adventurers.world import tiles
from ascii_adventurers.world.landmarks import Landmark, quest_marks
from ascii_adventurers.world.test_map import LEGEND, TestMap

DT = 1 / 60
W, H = 140, 44


def vault(walls=()):
    """An open map with the vault's fixtures and a lair over it: showers
    at (10, 5) and (130, 38) (2 x 2), valves at (10, 38), (130, 5), (70, 3),
    (70, 41), grates at (40, 22) and (100, 22), a lead wall 4 x 2 at
    (80, 10)."""
    rows = [["."] * W for _ in range(H)]
    for x, y in ((10, 5), (130, 38)):
        for dx in (0, 1):
            for dy in (0, 1):
                rows[y + dy][x + dx] = "S"
    for x, y in ((10, 38), (130, 5), (70, 3), (70, 41)):
        rows[y][x] = "V"
    for x, y in ((40, 22), (100, 22)):
        rows[y][x] = rows[y][x + 1] = "G"
    for dx in range(4):
        for dy in range(2):
            rows[10 + dy][80 + dx] = "L"
    for x, y in walls:
        rows[y][x] = "#"
    m = TestMap(["".join(r) for r in rows],
                dict(LEGEND, S=tiles.SHOWER, V=tiles.VALVE, G=tiles.GRATE, L=tiles.LEAD))
    props = {"showers": [(11.0, 6.0), (131.0, 39.0)],
             "valves": [(10.5, 38.5), (130.5, 5.5), (70.5, 3.5), (70.5, 41.5)],
             "grates": [(41.0, 22.5), (101.0, 22.5)], "leads": [(82.0, 11.0)]}
    lair = Landmark("reactor_vault", "lair", "ruins", "VAULT", 0, 0, [], cx=W / 2, cy=H / 2,
                    spots=[(W / 2, H / 2)], radii=(W / 2 - 1, H / 2 - 1), props=props)
    return m, lair


class Fight:
    def __init__(self, walls=(), hx=90.0, hy=22.0, bx=60.0, by=22.0, lair=True):
        self.w, self.lair = vault(walls)
        self.b = make_enemy("fallout_king", bx, by, random.Random(4))
        self.b.scale_to_level(1)
        self.b._rest = 99.0
        self.b.lair = self.lair if lair else None
        self.h = hero("wizard", hx, hy)
        self.h.max_hp = self.h.hp = 10 ** 6
        self.adds, self.shots, self.effects = [], [], []

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
            ctx = self.ctx()
            self.b.think(ctx, DT)
            for a in list(self.adds):
                if a.alive:
                    a.think(ctx, DT)
                elif not getattr(a, "_gone", False):
                    a._gone = True
                    on_death = getattr(a, "on_death", None)
                    if on_death is not None:
                        on_death(ctx)
            if move is not None and self.b.last_move == move:
                self.b._rest = 99.0
                self.b._pick_move = lambda: "emp"
                move = None


class VaultTest(unittest.TestCase):
    def test_camp_and_vault_in_the_ruins(self):
        for seed in (1, 2, 31, 999):
            w = world(seed)
            camp, lair = quest_marks(w.layout, "hazmat_scavenger")
            self.assertEqual((camp.key, lair.key), ("scrap_camp", "reactor_vault"), seed)
            for m in (camp, lair):
                self.assertEqual(w.layout.biome_at(m.cx, m.cy).name, "ruins", seed)
            self.assertEqual({k: len(v) for k, v in lair.props.items()},
                             {"valves": 4, "showers": 4, "leads": 4, "grates": 6}, seed)

    def test_its_reactor_fixtures_and_pillars(self):
        w = world(31)
        camp, lair = quest_marks(w.layout, "hazmat_scavenger")
        flat = {t for row in lair.rows for t in row if t is not None}
        self.assertTrue({tiles.VAULT_WALL, tiles.CONCRETE, tiles.REACTOR, tiles.CONC_PILLAR,
                         tiles.PIPE, tiles.VALVE, tiles.SHOWER, tiles.LEAD, tiles.GRATE} <= flat)
        for vx, vy in lair.props["valves"]:
            self.assertIs(w.tile_at(math.floor(vx), math.floor(vy)), tiles.VALVE)
        for gx, gy in lair.props["grates"]:
            self.assertIs(w.tile_at(math.floor(gx), math.floor(gy)), tiles.GRATE)
        x, y = lair.spots[0]
        self.assertFalse(w.tile_at(math.floor(x), math.floor(y)).solid)
        cflat = {t for row in camp.rows for t in row if t is not None}
        self.assertTrue({tiles.SLUDGE, tiles.SCRAP_WALL, tiles.PLATES} <= cflat)
        x, y = camp.spots[0]
        self.assertIs(w.tile_at(math.floor(x), math.floor(y)), tiles.BEACON_SITE)

    def test_new_tiles_have_map_colors(self):
        from ascii_adventurers import palette
        for t in (tiles.VAULT_WALL, tiles.REACTOR, tiles.CONC_PILLAR, tiles.PIPE, tiles.VALVE,
                  tiles.VALVE_SHUT, tiles.SHOWER, tiles.SHOWER_OFF, tiles.LEAD, tiles.GRATE,
                  tiles.BEACON_SITE, tiles.BEACON, tiles.SLUDGE, tiles.PLATES, tiles.SCRAP_WALL,
                  tiles.SCRAP_POST):
            self.assertTrue(t.name in palette.MAP_TILE or t.name in palette.MAP_TILE_BIOME, t.name)
            self.assertNotIn("~", "".join(t.glyphs), t.name)


class CreatureTest(unittest.TestCase):
    def test_a_ghoul_bursts_when_it_dies(self):
        f = Fight(hx=100.0)
        g = make_enemy("glowing_ghoul", 100.8, 22.0, random.Random(1))
        g.hp = 0.0
        g.on_death(f.ctx())
        self.assertLess(f.h.hp, 10 ** 6)

    def test_a_barrel_cant_be_stopped_and_lands_as_goo(self):
        f = Fight(hx=100.0)
        f.run(3.0, "barrels")
        self.assertTrue(f.b.goo)                    # landed: goo
        f = Fight(hx=100.0)
        f.b._rest = 0.0
        f.b._pick_move = lambda: "barrels"
        f.run(0.7)
        flying = [a for a in f.adds if a.kind_key == "toxic_barrel" and a.alive]
        self.assertTrue(flying)
        for a in flying:                            # nothing hits one in the air
            self.assertFalse(a.hittable)
            self.assertEqual(a.take_damage(10 ** 6, f.h, 0.0), 0.0)
            self.assertTrue(a.alive)


class RadsTest(unittest.TestCase):
    def test_his_glow_fills_your_rads_and_they_drain_away(self):
        f = Fight(hx=65.0)
        f.run(2.0)
        self.assertAlmostEqual(f.h.rads, config.RADS_GLOW * 2.0, delta=1.0)
        f.h.x = 120.0
        before = f.h.rads
        f.run(2.0)
        self.assertAlmostEqual(f.h.rads, before - config.RADS_DRAIN * 2.0, delta=0.5)

    def test_full_and_youre_irradiated(self):
        f = Fight(hx=100.0)
        f.h.rads = config.RADS_FULL
        f.run(DT)
        self.assertGreater(f.h.irradiated, 0)
        hp = f.h.hp
        f.run(2.0)
        self.assertLess(f.h.hp, hp)                 # it burns
        f.h.roll_charges = 0
        f.h.roll_recharge = 0.0
        roll.recharge(f.h, 1.0)
        self.assertAlmostEqual(f.h.roll_recharge, config.IRRADIATED[3])
        f.run(config.IRRADIATED[0])
        self.assertEqual(f.h.irradiated, 0.0)
        self.assertLessEqual(f.h.rads, config.IRRADIATED[4])

    def test_a_shower_cleans_you_then_runs_dry(self):
        f = Fight(hx=11.0, hy=6.0)
        f.h.rads = 80.0
        f.run(config.SHOWER[0] + 0.1)
        self.assertEqual(f.h.rads, 0.0)
        self.assertIs(f.w.tile_at(10, 5), tiles.SHOWER_OFF)
        f.h.rads = 80.0
        f.run(1.0)
        self.assertGreater(f.h.rads, 0.0)           # dry now
        f.run(config.SHOWER[1])
        self.assertIs(f.w.tile_at(10, 5), tiles.SHOWER)

    def test_goo_slows_you_and_his_shots_add_rads(self):
        f = Fight(hx=100.0)
        f.b.goo.append([100.0, 22.0, 0.0])
        f.run(DT)
        self.assertEqual(f.h.time_mult, config.KING_BARRELS[6])
        f.b.goo = []
        f.run(DT)
        self.assertEqual(f.h.time_mult, 1.0)
        r = f.h.rads
        f.b.on_shot_hit(f.h, 5.0)
        self.assertEqual(f.h.rads, r + config.RADS_HIT)


class FalloutTest(unittest.TestCase):
    def test_the_stomp_leaves_fallout_with_rods_and_a_rod_clears_it(self):
        f = Fight(hx=100.0)
        f.b.phase = 1
        f.run(2.0, "stomp")
        self.assertGreaterEqual(len(f.b.patches), config.FALLOUT_PATCHES[0])
        p = f.b.patches[0]
        self.assertIsNotNone(p["rod"])
        f.h.x, f.h.y = p["x"], p["y"]
        rads, hp = f.h.rads, f.h.hp
        f.run(1.0)
        self.assertGreater(f.h.rads, rads)
        self.assertLess(f.h.hp, hp)
        p["rod"].hp = 0.0
        f.run(DT)
        self.assertNotIn(p, f.b.patches)


class CoreTest(unittest.TestCase):
    def test_the_core_heats_in_phase_three_only(self):
        f = Fight(hx=100.0)
        f.run(2.0)
        self.assertEqual(f.b.heat, 0.0)
        f.b.phase = 2
        f.run(3.5)
        self.assertAlmostEqual(f.b.heat, 10.0, delta=0.5)
        self.assertIn("CORE", f.b.bar_label)

    def test_shut_every_valve_and_the_core_is_exposed(self):
        f = Fight(hx=100.0)
        f.b.phase = 2
        for vx, vy in f.lair.props["valves"]:
            f.h.x, f.h.y = vx + 1.5, vy
            f.run(config.VALVE_TIME + 0.1)
        self.assertGreater(f.b.exposed, 0)
        self.assertEqual(f.b.heat, 0.0)
        hp = f.b.hp
        f.b.take_damage(100, None, 0.0)
        self.assertAlmostEqual(hp - f.b.hp, 100 * config.CORE_EXPOSED[1])
        f.run(config.CORE_EXPOSED[0] + 0.1)
        self.assertEqual(f.b.exposed, 0.0)
        self.assertEqual(f.b.shut, set())
        vx, vy = f.lair.props["valves"][0]
        self.assertIs(f.w.tile_at(math.floor(vx), math.floor(vy)), tiles.VALVE)

    def test_meltdown_hits_all_but_who_hides_behind_lead(self):
        f = Fight(hx=82.0, hy=7.0, bx=82.0, by=22.0)   # the lead wall between (y 10..11)
        exposed = hero("dwarf", 100.0, 22.0)
        exposed.max_hp = exposed.hp = 10 ** 6
        f.b.phase = 2
        f.b.heat = 99.9
        for _ in range(round((config.MELTDOWN[0] + 1.0) * 60)):
            f.b.think(AIContext(f.w, [f.h, exposed], [f.h, exposed, f.b], f.shots, f.effects), DT)
        self.assertEqual(f.h.hp, 10 ** 6)           # shielded
        self.assertLess(exposed.hp, 10 ** 6)
        self.assertLess(f.b.heat, 5.0)              # (it starts climbing again)


class MoveTest(unittest.TestCase):
    def test_the_gamma_cross_burns_but_a_pillar_blocks_it(self):
        f = Fight(hx=80.0, hy=22.0, walls=[(70, y) for y in range(15, 30)])
        f.b.facing = 0.0
        f.run(4.5, "gamma")
        # (the cross starts 45 degrees off the target and turns: it may or
        # may not cross him -- but never through the wall)
        g = Fight(hx=60.0, hy=30.0)
        g.run(4.5, "gamma")
        self.assertTrue(g.h.rads > 0)
        self.assertEqual(f.h.hp, 10 ** 6)

    def test_grate_dive_comes_up_by_you(self):
        f = Fight(hx=98.0, hy=24.0, bx=42.0, by=22.0)
        f.b._rest = 0.0
        f.b._pick_move = lambda: "grate"
        under = False
        for _ in range(60 * 3):
            f.b.think(f.ctx(), DT)
            under |= f.b.submerged and not f.b.hittable
            if f.b.last_move == "grate":
                break
        self.assertTrue(under)
        self.assertEqual((f.b.x, f.b.y), (101.0, 22.5))
        self.assertLess(f.h.hp, 10 ** 6)

    def test_emp_rings_have_a_gap(self):
        f = Fight()
        f.run(2.5, "emp")
        emp = [p for p in f.shots if p.spec is config.KING_SHOTS["emp"]]
        _, n, _, rings = config.KING_EMP
        self.assertLess(len(emp), n * rings)
        self.assertGreater(len(emp), n * rings * 0.7)

    def test_ghouls_and_skulls_are_capped(self):
        f = Fight(hx=130.0)
        for move in ("ghouls", "ghouls", "ghouls", "skulls", "skulls", "skulls"):
            f.run(1.5, move)
            f.b.last_move = None
        ghouls = [a for a in f.adds if a.kind_key == "glowing_ghoul"]
        skulls = [a for a in f.adds if a.kind_key == "gamma_skull"]
        self.assertLessEqual(len(ghouls), config.KING_GHOULS[2])
        self.assertLessEqual(len(skulls), config.KING_SKULLS[2])

    def test_every_move_runs_to_the_end(self):
        names = {m for ph in config.BOSSES["fallout_king"].phases for m, _ in ph.moves}
        for phase in (0, 2):
            for name in sorted(names):
                f = Fight(hx=100.0)
                f.h.invulnerable = True
                f.b.phase = phase
                f.run(10.0, name)
                self.assertEqual(f.b.last_move, name, (phase, name))
                self.assertFalse(f.b.submerged, name)
                self.assertEqual(f.b.beams, [], name)

    def test_his_death_clears_your_rads(self):
        f = Fight(hx=65.0)
        f.b.phase = 1
        f.run(2.0, "stomp")
        f.h.rads, f.h.irradiated, f.h.time_mult = 90.0, 2.0, 0.6
        f.b.on_death(f.ctx())
        self.assertEqual((f.h.rads, f.h.irradiated, f.h.time_mult), (0.0, 0.0, 1.0))
        self.assertEqual(f.b.patches, [])


class QuestTest(unittest.TestCase):
    def tearDown(self):
        config.QUEST_FOCUS = None

    def test_she_follows_plants_and_the_ghouls_come_for_you(self):
        m, s = game(seed=31)
        q = s.quests
        st = q.states["hazmat_scavenger"]
        self.assertEqual(st.spec.kind, "escort")
        s.hero.invulnerable = True
        npc = st.npc
        home = (npc.x, npc.y)
        teleport(s, npc.x + 8, npc.y)
        step(s, 60)
        self.assertEqual((npc.x, npc.y), home)      # not taken: she stays
        q.talk(npc, s.me)
        step(s, 90)
        self.assertLess(math.hypot(npc.x - s.hero.x, npc.y - s.hero.y), config.ESCORT_GAP + 1)
        x, y = st.camp.spots[0]
        teleport(s, x - 2, y)                       # (just past the site: she walks onto it)
        npc.x, npc.y = x + 7, y
        step(s, 90)
        self.assertGreater(st.heat.get(0, 0.0), 0.0)            # planting
        ghouls = [e for e in s.enemies if getattr(e, "kind_key", "") == "glowing_ghoul"]
        self.assertGreaterEqual(len(ghouls), config.ESCORT_WAVE_SIZE)
        self.assertNotIn(npc, s._actors())                      # she can't be hit
        s.draw(m.text)
        st.heat[0] = config.ESCORT_SETUP - 0.1
        step(s, 10)
        self.assertIn(0, st.lit)
        self.assertEqual(st.found, 1)
        self.assertIs(s.world.tile_at(math.floor(x), math.floor(y)), tiles.BEACON)

    def test_the_whole_fight(self):
        m, s = game(seed=31)
        q = s.quests
        st = q.states["hazmat_scavenger"]
        finish(q, "hazmat_scavenger")
        self.assertEqual(st.stage, "awake")
        s.hero.invulnerable = True
        lair = st.lair
        teleport(s, lair.cx + 20, lair.cy + 6)
        step(s, 1)
        self.assertEqual(st.stage, "fight")
        b = st.boss
        self.assertIsInstance(b, FalloutKing)
        step(s, 300)
        self.assertGreater(s.hero.rads, 0.0)
        s.draw(m.text)                               # (the HUD with its RAD meter)
        b.phase = 2
        step(s, 5)
        s.draw(m.text)
        b.hp = 0.0
        b.last_hit_by = s.hero
        step(s)
        self.assertEqual(st.stage, "cleared")
        self.assertIn("fallout_king", m.app.guild.achievements)
        self.assertEqual(m.app.guild.journal["hazmat_scavenger"]["wins"], 1)
        self.assertTrue(all(s.world.tile_at(*t) is tiles.CONCRETE for t in lair.gate))
        self.assertEqual(s.hero.rads, 0.0)

    def test_dev_finish_plants_the_beacons(self):
        m, s = game(seed=31)
        config.QUEST_FOCUS = "hazmat_scavenger"
        st = s.quests.states["hazmat_scavenger"]
        self.assertTrue(s.quests.dev_finish_hunt())
        x, y = st.camp.spots[0]
        self.assertIs(s.world.tile_at(math.floor(x), math.floor(y)), tiles.BEACON)


if __name__ == "__main__":
    unittest.main()
