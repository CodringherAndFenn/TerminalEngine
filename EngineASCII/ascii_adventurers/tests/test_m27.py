"""M27: the plains boss -- More than Life, the necromancer, who rises again
as More than Death, the lich -- his necropolis at the island's centre (the
start outside its gate), the main quest's last step, Adventurer's Glory, the
victory and water walking."""

import math
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.ai import make_enemy
from ascii_adventurers.ai.bosses import LegionPart, MycoPart, Necromancer
from ascii_adventurers.ai.brain import AIContext
from ascii_adventurers.tests.test_m17 import game, step, teleport, world
from ascii_adventurers.tests.test_weapons import hero
from ascii_adventurers.world import tiles
from ascii_adventurers.world.landmarks import Landmark, quest_marks
from ascii_adventurers.world.test_map import LEGEND, TestMap

DT = 1 / 60
W, H = 200, 80
GRAVES = [(60.5, 40.5), (64.5, 40.5), (68.5, 40.5)]


def necropolis(row=()):
    rows = [["."] * W for _ in range(H)]
    for x, y in list(GRAVES) + list(row):
        rows[int(y)][int(x)] = "G"
    m = TestMap(["".join(r) for r in rows], dict(LEGEND, G=tiles.GRAVESTONE))
    lair = Landmark("necropolis", "lair", "plains", "THE NECROPOLIS", 0, 0, [], cx=W / 2,
                    cy=H / 2, spots=[(W / 2, H / 2)], radii=(W / 2 + 2, H / 2 + 2),
                    props={"graves": list(GRAVES), "corpses": []})
    return m, lair


class Fight:
    def __init__(self, hx=100.0, hy=30.0, bx=100.0, by=45.0, phase=0, lich=False, row=()):
        self.w, self.lair = necropolis(row)
        self.b = make_enemy("necromancer", bx, by, random.Random(4))
        self.b.scale_to_level(1)
        self.b._rest = 99.0
        b = self.b
        b.raise_t = b.blast_t = b.wall_t = b.gaze_t = b.legion_t = 999.0
        b.storm_t = b.possess_t = b.cage_t = 999.0
        b.lair = self.lair
        if lich:
            b.life = 2
            b.bspec = config.BOSSES["necromancer_lich"]
        b.hp = b.max_hp * (1.0, 0.5, 0.2)[phase]
        self.h = hero("wizard", hx, hy)
        self.h.max_hp = self.h.hp = 10 ** 6
        self.adds, self.shots, self.effects = [], [], []

        def recruit(k, x, y):
            e = make_enemy(k, x, y, random.Random(len(self.adds)))
            self.adds.append(e)
            return e
        b.recruit = recruit
        b.ctx = self.ctx()
        b._check_phase(b.ctx)

    def ctx(self):
        return AIContext(self.w, [self.h], [self.h, self.b] + self.adds, self.shots, self.effects)

    def run(self, seconds, move=None, until=None):
        if move is not None:
            self.b._rest = 0.0
            self.b.last_move = None
            self.b._pick_move = lambda m=move: m
        for _ in range(round(seconds * 60)):
            self.b.think(self.ctx(), DT)
            if move is not None and self.b.last_move == move:
                self.b._rest = 99.0
                self.b._pick_move = lambda: "spears"
                move = None
            if until is not None and until():
                return True
        return False

    def sign(self, name):
        self.b._start(name)
        self.b._wait = 0.0


class NecropolisTest(unittest.TestCase):
    def test_at_the_centre_twice_as_big_gate_south_sealed(self):
        for seed in (1, 2, 31, 999):
            w = world(seed)
            camp, lair = quest_marks(w.layout, "necropolis")
            self.assertIsNone(camp)
            self.assertEqual((lair.cx, lair.cy), (0, 0))
            self.assertEqual(lair.radii, tuple(float(r) for r in config.NECRO_RADII))
            self.assertEqual(config.NECRO_RADII, (2 * config.LAIR_RADII[0], 2 * config.LAIR_RADII[1]))
            self.assertEqual(w.layout.biome_at(0, 0).name, "plains")
            gy = sum(t[1] for t in lair.gate) / len(lair.gate)
            self.assertGreater(gy, config.NECRO_RADII[1] - 2)          # (south)
            for tx, ty in lair.gate:
                self.assertIs(lair.tile_at(tx, ty), tiles.SEALED_GATE)

    def test_runs_start_outside_his_gate(self):
        for seed in (1, 2, 31, 999, 11, 16):
            w = world(seed)
            _, lair = quest_marks(w.layout, "necropolis")
            sx, sy = w.layout.spawn
            self.assertFalse(lair.inside(sx, sy, -config.LAIR_WALL))
            self.assertGreater(sy, 0)
            self.assertLess(math.hypot(sx, sy - config.NECRO_RADII[1]), 60, seed)

    def test_graves_tombs_corpses_and_the_ring(self):
        w = world(31)
        _, lair = quest_marks(w.layout, "necropolis")
        flat = {t for row in lair.rows for t in row if t is not None}
        self.assertTrue({tiles.CRYPT_WALL, tiles.GRAVE_SOIL, tiles.BONE_LITTER, tiles.GRAVESTONE,
                         tiles.MAUSOLEUM, tiles.RITUAL_RING} <= flat)
        self.assertEqual(len(lair.props["corpses"]), config.NECRO_CORPSES)
        for gx, gy in lair.props["graves"]:
            self.assertIs(lair.tile_at(math.floor(gx), math.floor(gy)), tiles.GRAVESTONE)

    def test_new_tiles_and_shot_glyphs(self):
        from ascii_adventurers import palette
        from ascii_adventurers.render.ascii_fx import SHOT_LOOKS as _LOOKS
        floors = "".join(g for t in (tiles.GRAVE_SOIL, tiles.BONE_LITTER, tiles.RITUAL_RING)
                         for g in t.glyphs)
        for look in ("bone_spear", "soul"):
            head, trail, _ = _LOOKS[look]
            for ch in head + "".join(t for t in trail if t):
                if ch != " ":
                    self.assertNotIn(ch, floors, look)
        for t in (tiles.GRAVE_SOIL, tiles.BONE_LITTER, tiles.RITUAL_RING, tiles.GRAVESTONE,
                  tiles.MAUSOLEUM, tiles.CRYPT_WALL, tiles.SEALED_GATE, tiles.BONE_WALL):
            self.assertTrue(t.name in palette.MAP_TILE or t.name in palette.MAP_TILE_BIOME, t.name)
            self.assertNotIn("~", "".join(t.glyphs), t.name)


def win_guardians(s):
    """A boss beaten in each ring biome (one quest of each)."""
    done = set()
    for st in s.quests.states.values():
        if st.spec.kind != "finale" and st.biome not in done:
            st.stage = "cleared"
            done.add(st.biome)
    return done


class FinaleTest(unittest.TestCase):
    def test_sealed_until_the_guardians_fall_then_it_opens(self):
        m, s = game(seed=31)
        q = s.quests
        st = q.states["necropolis"]
        self.assertIsNone(st.npc)
        self.assertNotIn(None, q.npcs)
        self.assertEqual(st.stage, "hunt")
        _, lair = st.camp, st.lair
        teleport(s, *s.spawn)
        gx, gy = lair.gate[0]
        self.assertIs(s.world.tile_at(gx, gy), tiles.SEALED_GATE)
        self.assertEqual(q.log()[0], ("GLORY", f"guardians 0/{config.GUARDIANS}", False))
        biomes = win_guardians(s)
        self.assertEqual(len(biomes), config.GUARDIANS)
        self.assertEqual(q.guardians, config.GUARDIANS)
        step(s)
        self.assertEqual(st.stage, "awake")
        self.assertIs(s.world.tile_at(gx, gy), lair.floor)
        self.assertIn("defeat More than Life", q.log()[0][1])
        self.assertTrue(any(k == "lair" and lbl == "THE NECROPOLIS" for _, _, k, lbl in q.pins()))

    def test_the_plains_boss_doesnt_count_as_a_guardian(self):
        m, s = game(seed=31)
        s.quests.states["necropolis"].stage = "cleared"
        self.assertEqual(s.quests.guardians, 0)


class LifeTest(unittest.TestCase):
    def test_the_killing_blow_only_fells_him_then_he_rises_as_the_lich(self):
        f = Fight()
        f.b.corpses = [[90.0, 45.0, 0.0], [110.0, 45.0, 0.0]]
        f.b.seeded = True
        f.b.take_damage(f.b.hp + 100, f.h, 0.0)
        self.assertTrue(f.b.alive)
        self.assertEqual(f.b.hp, 1.0)
        self.assertTrue(f.b.reviving)
        self.assertFalse(f.b.hittable)
        self.assertEqual(f.b.take_damage(500, f.h, 0.0), 0.0)
        self.assertTrue(f.run(config.NECRO_RITUAL + 1.0, until=lambda: not f.b.reviving))
        self.assertTrue(f.b.lich)
        self.assertEqual(f.b.hp, f.b.max_hp)
        self.assertEqual(f.b.name_now, "More than Death")
        self.assertIn("MORE THAN DEATH", f.b.bar_label)
        self.assertEqual(f.b.corpses, [])                       # (every corpse raised)
        self.assertEqual(len(f.b.minions), 2)
        f.b.take_damage(f.b.hp + 100, f.h, 0.0)
        self.assertFalse(f.b.alive)                             # (the second time, for good)

    def test_twice_as_long(self):
        b = make_enemy("necromancer", 0, 0, random.Random(1))
        self.assertEqual(b.max_hp, round(8000 * config.BOSS_HP_MULT * config.NECRO_HP_LIVES))
        self.assertEqual(config.NECRO_HP_LIVES, 1.0)            # (two whole lives of a ring boss)


class DeadTest(unittest.TestCase):
    def test_his_dead_leave_corpses_that_glow_and_rise(self):
        f = Fight()
        f.b.seeded = True
        f.b.corpses = [[95.0, 45.0, 0.0], [105.0, 45.0, 0.0]]
        f.b.raise_t = 0.0
        f.run(DT * 2)
        self.assertGreater(f.b.raise_glow, 0)
        f.run(config.RAISE_TELL + 0.1)
        risen = [m for m in f.b.minions if m.kind_key == "risen_dead"]
        self.assertGreaterEqual(len(risen), 2)
        risen[0].hp = 0
        f.run(DT)
        self.assertEqual(len(f.b.corpses), 1)

    def test_stand_on_a_corpse_to_crush_it(self):
        f = Fight()
        f.b.seeded = True
        f.b.corpses = [[f.h.x, f.h.y, 0.0]]
        f.run(config.CORPSE_STOMP[1] + 0.1)
        self.assertEqual(f.b.corpses, [])

    def test_corpses_near_you_glow_red_and_burst(self):
        f = Fight()
        f.b.seeded = True
        f.b.corpses = [[f.h.x + 3.0, f.h.y, 0.0]]
        f.b.blast_t = 0.0
        hp = f.h.hp
        f.run(DT * 2)
        self.assertTrue(f.b.blasting)
        f.run(config.BLAST_TELL + 0.1)
        self.assertEqual(f.b.corpses, [])
        self.assertLess(f.h.hp, hp)


class WallGazeTest(unittest.TestCase):
    def test_bone_walls_rise_round_you_and_crumble(self):
        f = Fight(phase=1)
        f.b.wall_t = 0.0
        f.run(DT * 2)
        self.assertTrue(f.b.cracks)
        f.run(config.WALL_TELL + 0.1)
        self.assertTrue(f.b.walls)
        tx, ty = f.b.walls[0][:2]
        self.assertIs(f.w.tile_at(tx, ty), tiles.BONE_WALL)
        self.assertFalse(any(abs(f.h.x - w[0] - 0.5) < 1.0 and abs(f.h.y - w[1] - 0.5) < 1.0
                             for w in f.b.walls))               # (never on you)
        f.run(config.WALL_LIFE + 0.2)
        self.assertIsNot(f.w.tile_at(tx, ty), tiles.BONE_WALL)

    def test_walls_and_gaze_only_from_phase_two(self):
        f = Fight()
        f.b.wall_t = f.b.gaze_t = 0.0
        f.run(1.0)
        self.assertEqual(f.b.cracks, [])
        self.assertNotEqual(f.b.move, "gaze")

    def test_the_gaze_burns_you_in_the_open(self):
        f = Fight(phase=1, hx=100.0, hy=30.0)
        hp = f.h.hp
        f.sign("gaze")
        f.run(config.GAZE_TELL + 0.6)
        self.assertLess(f.h.hp, hp)

    def test_a_grave_stops_the_gaze(self):
        f = Fight(phase=1, hx=64.5, hy=38.5, bx=64.5, by=50.0,
                  row=[(x + 0.5, 40.5) for x in range(58, 72)])   # (a row of graves)
        hp = f.h.hp
        f.sign("gaze")
        f.run(config.GAZE_TELL + 0.5)
        self.assertEqual(f.h.hp, hp)                            # (behind the grave)
        self.assertLess(f.b.gaze_end[1], 41.5)


class LegionTest(unittest.TestCase):
    def test_volley_then_phalanx(self):
        f = Fight(phase=2)
        f.b.legion_t = 0.0
        hp = f.h.hp
        f.run(DT * 2)
        self.assertEqual(len(f.b.volley), config.VOLLEY[0])
        f.run(config.VOLLEY[2] + 0.1)
        self.assertLess(f.h.hp, hp)
        f.b.legion_t = 0.0
        f.run(DT * 2)
        self.assertIsNotNone(f.b.phalanx)
        n, _, holes, _, _, _ = config.PHALANX
        self.assertEqual(len(f.b.shields), n - holes)
        self.assertTrue(all(isinstance(s, LegionPart) for s in f.b.shields))

    def test_shields_take_no_harm_from_in_front(self):
        s = make_enemy("legion_shield", 0, 0, random.Random(1))
        s.march = 0.0                                           # (marching east)
        self.assertEqual(s.take_damage(10, None, math.pi), 0.0)  # (a shot from the east)
        self.assertGreater(s.take_damage(10, None, 0.0), 0.0)     # (from behind)

    def test_the_phalanx_marches_through_you(self):
        f = Fight(phase=2)
        f.b.legion_turn = 1
        f.b.legion_t = 0.0
        hp = f.h.hp
        f.run(config.PHALANX[4] / config.PHALANX[3] + 1.0)
        self.assertLess(f.h.hp, hp)
        self.assertIsNone(f.b.phalanx)


class LichTest(unittest.TestCase):
    def test_soul_storm_drags_you_in(self):
        f = Fight(lich=True, hx=100.0, hy=33.0)
        f.sign("storm")
        d0 = math.hypot(f.h.x - f.b.x, f.h.y - f.b.y)
        f.run(config.STORM_TELL + 2.0)
        self.assertLess(math.hypot(f.h.x - f.b.x, f.h.y - f.b.y), d0)

    def test_soul_harvest_powers_his_next_move(self):
        f = Fight(lich=True, hx=100.0, hy=40.0)
        f.b._hit(f.h, 5, None)
        self.assertEqual(len(f.b.wisps), 1)
        f.h.x, f.h.y = 160.0, 10.0                              # (out of grabbing reach)
        f.run(3.0)
        self.assertEqual(f.b.souls, 1)
        mult = f.b.damage_mult
        f.sign("spears")
        self.assertAlmostEqual(f.b.damage_mult, mult * (1 + config.HARVEST_POWER))
        self.assertEqual(f.b.souls, 0)

    def test_grab_a_soul_first(self):
        f = Fight(lich=True, hx=100.0, hy=40.0)
        f.h.hp = 100.0
        f.b._hit(f.h, 5, None)
        f.run(DT)
        self.assertEqual(f.b.wisps, [])
        self.assertEqual(f.b.souls, 0)

    def test_possession_find_the_host(self):
        f = Fight(lich=True, phase=1)
        f.sign("possess")
        self.assertTrue(f.run(config.POSSESS_TELL + 0.2, until=lambda: f.b.host is not None))
        self.assertFalse(f.b.hittable)
        self.assertEqual(f.b.take_damage(100, f.h, 0.0), 0.0)
        self.assertGreaterEqual(len(f.b.minions), config.POSSESS_HOSTS)
        hp = f.b.hp
        f.b.host.hp = 0
        f.run(DT * 2)
        self.assertIsNone(f.b.host)
        self.assertGreater(f.b.dazed, 0)
        self.assertAlmostEqual(f.b.hp, hp - config.POSSESS_HURT * f.b.max_hp)

    def test_bone_cage_roots_then_crushes_unless_broken(self):
        f = Fight(lich=True, phase=2)
        f.b.cage_t = 0.0
        self.assertTrue(f.run(config.CAGE_TELL + 0.2, until=lambda: f.b.caged is not None))
        self.assertEqual(len(f.b.ribs), config.CAGE_RIBS)
        f.run(DT)
        self.assertEqual(f.h.slow_mult, 0.0)
        f.b.ribs[0].hp = 0
        f.run(DT)
        self.assertIsNone(f.b.caged)
        g = Fight(lich=True, phase=2)
        g.b.cage_t = 0.0
        g.run(config.CAGE_TELL + 0.2, until=lambda: g.b.caged is not None)
        hp = g.h.hp
        g.run(config.CAGE_TIME + 0.2)
        self.assertLess(g.h.hp, hp)
        self.assertIsNone(g.b.caged)

    def test_the_lich_keeps_his_first_lifes_signatures_slower(self):
        f = Fight(lich=True)
        self.assertEqual(f.b.slow(), config.NECRO_LICH_SLOW)
        f.b.wall_t = 0.0
        f.run(DT * 2)
        self.assertTrue(f.b.cracks)
        self.assertGreater(f.b.wall_t, config.WALL_EVERY)


class MoveTest(unittest.TestCase):
    def test_bone_spears(self):
        f = Fight()
        f.run(config.NECRO_SPEARS[0] + 0.5, move="spears")
        self.assertTrue(any(p.spec.look == "bone_spear" for p in f.shots))

    def test_skull_fire_circles_then_dives(self):
        f = Fight(hx=100.0, hy=35.0)
        hp = f.h.hp
        f.run(config.NECRO_SKULLS[0] + 0.3, move="skulls")
        self.assertEqual(len(f.b.homers), config.NECRO_SKULLS[1])
        self.assertTrue(all(m[3] > 0 for m in f.b.homers))       # (circling first)
        f.run(4.0)
        self.assertLess(f.h.hp, hp)

    def test_grasping_hands_root_you(self):
        f = Fight()
        hp = f.h.hp
        f.run(config.NECRO_HANDS[0] + 0.2, move="hands")
        self.assertLess(f.h.hp, hp)
        self.assertEqual(f.h.slow_mult, 0.0)

    def test_the_reap_blinks_beside_you(self):
        f = Fight()
        hp = f.h.hp
        f.run(config.NECRO_REAP[0] + config.NECRO_REAP[1] + 0.2, move="reap")
        self.assertLess(math.hypot(f.b.x - f.h.x, f.b.y - f.h.y), 4.5)
        self.assertLess(f.h.hp, hp)


class GloryTest(unittest.TestCase):
    def test_glory_victory_and_water_walking(self):
        config.QUEST_FOCUS = "necropolis"
        try:
            m, s = game(seed=31)
            q = s.quests
            st = q.states["necropolis"]
            q.dev_finish_hunt()
            self.assertEqual(st.stage, "awake")
            teleport(s, st.lair.cx, st.lair.cy + 14)
            s.hero.invulnerable = True
            step(s, 3)
            self.assertEqual(st.stage, "fight")
            b = st.boss
            self.assertIsInstance(b, Necromancer)
            for f in range(600):
                step(s)
                if f % 60 == 0:
                    s.draw(m.text)
            b.take_damage(b.hp + 1, s.hero, 0.0)              # (life 1 ends)
            self.assertTrue(b.alive)
            step(s, round((config.NECRO_RITUAL + 1) * 60))
            self.assertTrue(b.lich)
            for f in range(300):
                step(s)
                if f % 60 == 0:
                    s.draw(m.text)
            b.hp = 0
            b.last_hit_by = s.hero
            step(s, 3)
            self.assertEqual(st.stage, "cleared")
            self.assertTrue(q.glory)
            self.assertTrue(s.me.glory)
            self.assertTrue(s.me.hero.water_walk)
            self.assertTrue(s.stats.victory)
            self.assertEqual(q.log()[0][2], True)
            self.assertFalse(any(isinstance(e, MycoPart) and e.alive for e in s.enemies))
            # The pause menu now has the victory; it ends the run.
            s._pause()
            labels = [b_[0] for b_ in s.overlay.buttons]
            self.assertIn("End run (victory)", labels)
            s._victory()
            from ascii_adventurers.ui.overlays import VictoryPanel
            self.assertIsInstance(s.overlay, VictoryPanel)
            s.draw(m.text)
        finally:
            config.QUEST_FOCUS = None

    def test_water_walkers_cross_lakes(self):
        from ascii_adventurers.entities.character import Character
        rows = ["." * 20, "." * 6 + "~" * 4 + "." * 10, "." * 20]
        w = TestMap(rows, dict(LEGEND))
        h = Character(config.HEROES["wizard"], 4.5, 1.5)
        for walker in (False, True):
            h.x, h.y = 4.5, 1.5
            h.water_walk = walker
            h.vx = h.vy = 0.0
            for _ in range(120):
                h.move(1.0, 0.0, 1 / 60, w)
            self.assertEqual(h.x > 11, walker, walker)


if __name__ == "__main__":
    unittest.main()
