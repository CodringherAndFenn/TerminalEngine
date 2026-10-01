"""M17: landmarks, the quest framework, boss framework, Froggy McFrogface."""

import math
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from ascii_adventurers import config
from ascii_adventurers.ai import make_enemy
from ascii_adventurers.ai.bosses import Froggy
from ascii_adventurers.ai.brain import AIContext
from ascii_adventurers.entities.projectile import Projectile
from ascii_adventurers.systems import combat, patterns
from ascii_adventurers.systems.quests import QUEST_SID, Quests
from ascii_adventurers.systems.spawner import Spawner
from ascii_adventurers.tests.test_weapons import Dummy, hero, open_map
from ascii_adventurers.world import biomes, tiles
from ascii_adventurers.world.chunked import ChunkedWorld

SEEDS = (1, 2, 31, 999)
_worlds: dict = {}


def world(seed=31) -> ChunkedWorld:
    """One island per seed for the whole module (landmarks take ~70 ms)."""
    if seed not in _worlds:
        _worlds[seed] = ChunkedWorld(seed)
    return _worlds[seed]


def game(seed=31, hero_key="wizard"):
    from ascii_adventurers.tests.test_players import make_manager, start_game
    m = make_manager()
    s = start_game(m, seed=seed, hero=hero_key)
    s.mouse.left_held = lambda: False
    return m, s


def step(s, n=1):
    for _ in range(n):
        s._remember_positions()
        s._step(1 / 60)


def teleport(s, x, y):
    from ascii_adventurers.systems.quests import free_spot
    h = s.hero
    s.world.ensure_ready(int(x) - 48, int(y) - 20, int(x) + 48, int(y) + 20)
    h.x, h.y = free_spot(s.world, x, y, h.half)
    s.me.camera.center_on(h.x, h.y)


class LandmarkTest(unittest.TestCase):
    def test_camp_and_lair_are_in_the_swamp(self):
        for seed in SEEDS:
            w = world(seed)
            camp, lair = w.layout.landmark("frog_camp"), w.layout.landmark("pond_lair")
            self.assertIsNotNone(camp, seed)
            self.assertIsNotNone(lair, seed)
            for m in (camp, lair):
                self.assertEqual(w.layout.biome_at(m.cx, m.cy).name, "swamp", (seed, m.key))

    def test_the_camp_is_near_the_plains_border(self):
        for seed in SEEDS:
            w = world(seed)
            camp = w.layout.landmark("frog_camp")
            past = math.hypot(camp.cx, camp.cy) - w.layout.plains_radius
            self.assertLess(past, 250, seed)       # an early find, not deep in the ring

    def test_lair_spans_several_screens(self):
        lair = world().layout.landmark("pond_lair")
        a, b = lair.radii
        self.assertGreaterEqual(2 * a, 2.5 * 86)   # one screen: ~86 x 30 tiles
        self.assertGreaterEqual(2 * b, 2.5 * 30)
        self.assertEqual(len(lair.spots), config.LAIR_POOLS)
        self.assertGreater(len(lair.gate), 0)

    def test_placement_is_the_same_every_time(self):
        a = ChunkedWorld(77).layout.landmarks
        b = ChunkedWorld(77).layout.landmarks
        self.assertEqual([(m.key, m.x0, m.y0, m.spots, m.gate) for m in a],
                         [(m.key, m.x0, m.y0, m.spots, m.gate) for m in b])

    def test_chunks_carry_the_landmark_tiles(self):
        w = world()
        camp, lair = w.layout.landmark("frog_camp"), w.layout.landmark("pond_lair")
        nx, ny = camp.npc
        self.assertIs(w.tile_at(math.floor(nx), math.floor(ny)), tiles.HUNTER_POST)
        for tx, ty in lair.gate:
            self.assertIs(w.tile_at(tx, ty), tiles.MUD)        # open until a fight
        # The ring of stones: straight out from the centre along the long axis.
        a, _ = lair.radii
        self.assertIs(w.tile_at(math.floor(lair.cx + a + 1), math.floor(lair.cy)),
                      tiles.LAIR_STONE)
        for px, py in lair.spots:                                # pools
            self.assertIs(w.tile_at(math.floor(px), math.floor(py)), tiles.POND)

    def test_frog_spots_are_open_ground(self):
        w = world()
        for x, y in w.layout.landmark("frog_camp").spots:
            self.assertFalse(w.tile_at(math.floor(x), math.floor(y)).solid)

    def test_set_tile_survives_the_chunk_unloading(self):
        w = ChunkedWorld(31)
        gx, gy = w.layout.landmark("pond_lair").gate[0]
        w.set_tile(gx, gy, tiles.THORN_GATE)
        self.assertIs(w.tile_at(gx, gy), tiles.THORN_GATE)
        w._chunks.clear()                                        # unload everything
        self.assertIs(w.tile_at(gx, gy), tiles.THORN_GATE)

    def test_no_random_enemies_on_landmarks(self):
        w = world()
        sp = Spawner(w, w.seed)
        n = config.CHUNK_SIZE
        for m in w.layout.landmarks:
            for cy in range(m.y0 // n, (m.y0 + m.h) // n + 1):
                for cx in range(m.x0 // n, (m.x0 + m.w) // n + 1):
                    for _, _, x, y in sp.roster(cx, cy):
                        self.assertFalse(m.contains(x, y), (m.key, x, y))


class PatternTest(unittest.TestCase):
    def setUp(self):
        self.owner = Dummy(0, 0)
        self.owner.damage_mult = 2.0
        self.shell = config.FROGGY_SHOTS["bubble"]

    def test_radial_is_even_all_round(self):
        shots = []
        patterns.radial(self.owner, 5, 5, 8, self.shell, shots, turn=0.3)
        self.assertEqual(len(shots), 8)
        angles = sorted((p.angle - 0.3) % math.tau for p in shots)
        for k, a in enumerate(angles):
            self.assertAlmostEqual(a, k * math.tau / 8, places=6)
        self.assertEqual(shots[0].damage, self.shell.damage * 2.0)   # level scaling

    def test_fan_is_centred_on_the_aim(self):
        shots = []
        patterns.fan(self.owner, 0, 0, 1.0, 7, 60.0, self.shell, shots)
        self.assertAlmostEqual(sum(p.angle for p in shots) / 7, 1.0, places=6)
        self.assertAlmostEqual(max(p.angle for p in shots) - min(p.angle for p in shots),
                               math.radians(60), places=6)

    def test_closing_ring_waits_then_flies_through_the_centre(self):
        shots = []
        patterns.ring_in(self.owner, 20, 15, 10.0, 12, config.FROGGY_SHOTS["ring"], shots,
                         hold=0.5)
        start = [(p.x, p.y) for p in shots]
        w = open_map()
        for _ in range(29):                                     # < 0.5 s
            combat.update_projectiles(shots, w, [], 1 / 60)
        self.assertEqual(start, [(p.x, p.y) for p in shots])
        for _ in range(60):
            combat.update_projectiles(shots, w, [], 1 / 60)
        for p in shots:                                         # moving inward
            self.assertLess(math.hypot(p.x - 20, p.y - 15), 10.0)

    def test_curtain_leaves_a_hole(self):
        shots = []
        patterns.curtain(self.owner, 0, 0, math.pi / 2, 10.0, 20.0, 2.0, 4.0, 6.0,
                         self.shell, shots)
        # Heading down (+y), "sideways" is -x: the hole is at x = -4 +- 3.
        xs = sorted(p.x for p in shots)
        self.assertFalse(any(-7.0 < x < -1.0 for x in xs))
        self.assertTrue(any(-1.0 <= x <= 1.0 for x in xs))
        self.assertTrue(all(abs(p.angle - math.pi / 2) < 1e-9 for p in shots))
        self.assertTrue(all(abs(p.y + 10.0) < 1e-9 for p in shots))   # 10 tiles back

    def test_weaving_shot_swings_both_ways(self):
        shell = config.WEAPONS["psy_spit"].shell
        p = Projectile(5, 15, 0.0, shell)
        seen = []
        w = open_map()
        for _ in range(60):
            combat.update_projectiles([p], w, [], 1 / 60)
            seen.append(p.angle)
        self.assertGreater(max(seen), 0.3)
        self.assertLess(min(seen), -0.3)


class BossTest(unittest.TestCase):
    def setUp(self):
        self.w = world()
        self.lair = self.w.layout.landmark("pond_lair")
        lx, ly = self.lair.spots[0]
        self.boss = make_enemy("froggy", lx, ly, random.Random(5))
        self.boss.lair = self.lair
        self.h = hero("wizard", lx + 15, ly)
        self.h.invulnerable = True
        self.shots, self.effects = [], []

    def run_boss(self, seconds):
        moves = []
        for _ in range(int(seconds * 60)):
            ctx = AIContext(self.w, [self.h], [self.h, self.boss], self.shots, self.effects)
            self.boss.think(ctx, 1 / 60)
            combat.update_projectiles(self.shots, self.w, self.effects, 1 / 60, [self.h])
            if self.boss.move and (not moves or moves[-1] != self.boss.move):
                moves.append(self.boss.move)
        return moves

    def test_froggy_is_a_boss(self):
        self.assertIsInstance(self.boss, Froggy)
        self.assertTrue(self.boss.boss)
        self.assertEqual(self.boss.kind_key, "froggy")

    def test_moves_come_from_the_phase_and_never_twice_running(self):
        moves = self.run_boss(40)
        allowed = {m for m, _ in config.BOSSES["froggy"].phases[0].moves}
        self.assertGreater(len(moves), 8)
        self.assertTrue(set(moves) <= allowed, moves)
        for a, b in zip(moves, moves[1:]):
            self.assertNotEqual(a, b)

    def test_phases_follow_its_health(self):
        self.boss.hp = self.boss.max_hp * 0.5
        self.run_boss(0.1)
        self.assertEqual(self.boss.phase, 1)
        self.boss.hp = self.boss.max_hp * 0.2
        self.run_boss(0.1)
        self.assertEqual(self.boss.phase, 2)
        self.assertTrue(self.boss.psychedelic)
        self.boss.hp = self.boss.max_hp          # never goes back
        self.run_boss(0.1)
        self.assertEqual(self.boss.phase, 2)

    def test_every_move_runs_to_the_end(self):
        names = {m for ph in config.BOSSES["froggy"].phases for m, _ in ph.moves}
        for name in sorted(names):
            boss = make_enemy("froggy", *self.lair.spots[0], random.Random(1))
            boss.lair = self.lair
            boss.recruit = lambda k, x, y: make_enemy(k, x, y, random.Random(2))
            boss._rest = 0.0
            boss._pick_move = lambda name=name: name
            done = False
            for _ in range(60 * 12):
                ctx = AIContext(self.w, [self.h], [self.h, boss], self.shots, self.effects)
                boss.think(ctx, 1 / 60)
                if boss.last_move == name:
                    done = True
                    break
            self.assertTrue(done, name)
            self.assertTrue(boss.hittable, name)          # back on the ground, above water

    def test_cant_be_hit_in_the_air_or_under_water(self):
        self.boss.airborne = 0.5
        self.assertFalse(self.boss.hittable)
        self.boss.airborne = 0.0
        self.boss.submerged = True
        self.assertFalse(self.boss.hittable)

    def test_its_body_shoves_heroes_out(self):
        self.h.x, self.h.y = self.boss.x + 0.2, self.boss.y
        ctx = AIContext(self.w, [self.h], [self.h, self.boss], [], [])
        self.boss.think(ctx, 1 / 60)
        self.assertGreaterEqual(math.hypot(self.h.x - self.boss.x, self.h.y - self.boss.y),
                                self.boss.hit_radius)

    def test_shots_stay_under_the_budget(self):
        self.run_boss(60)
        self.assertLessEqual(sum(1 for p in self.shots if p.owner is self.boss),
                             config.BOSS_MAX_SHOTS + 30)   # (+ one volley over)

    def test_the_fight_replays_exactly(self):
        def trace(seed):
            boss = make_enemy("froggy", *self.lair.spots[0], random.Random(seed))
            boss.lair = self.lair
            h = hero("wizard", self.lair.spots[0][0] + 15, self.lair.spots[0][1])
            h.invulnerable = True
            shots = []
            out = []
            for _ in range(60 * 20):
                ctx = AIContext(self.w, [h], [h, boss], shots, [])
                boss.think(ctx, 1 / 60)
                combat.update_projectiles(shots, self.w, [], 1 / 60, [h])
                out.append((round(boss.x, 9), round(boss.y, 9), boss.move, len(shots)))
            return out
        self.assertEqual(trace(9), trace(9))

    def test_chill_cannot_freeze_a_boss(self):
        m, s = game()
        lx, ly = self.lair.spots[0]
        boss = s.spawner.wake("froggy", lx, ly, None, random.Random(3))
        boss.lair = self.lair
        s.enemies.append(boss)
        from ascii_adventurers.systems.statuses import Statuses
        boss.status = Statuses()
        boss.status.frozen = 5.0
        t0 = boss.time
        step(s, 30)
        self.assertGreater(boss.time, t0)


class QuestFlowTest(unittest.TestCase):
    def test_the_whole_quest(self):
        m, s = game()
        q = s.quests
        st = q.states["swamp"]
        self.assertEqual(st.stage, "offered")
        self.assertEqual([k for _, _, k, _ in q.pins()], ["quest"])     # pinned from the start
        # Talk: E queues it, the next step delivers it.
        teleport(s, st.npc.x, st.npc.y)
        self.assertIsNotNone(q.npc_near(s.hero))
        s.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e, unicode="e", mod=0))
        step(s)
        self.assertEqual(st.stage, "hunt")
        self.assertEqual(st.npc.line, config.QUESTS["swamp"].say("offer")[0])
        bid = biomes.BY_NAME["swamp"].id
        self.assertEqual(len(s.spawner.fixed), config.QUESTS["swamp"].count)
        # The frogs appear (even on screen), and each one that dies counts.
        step(s)
        frogs = [e for e in s.enemies if getattr(e, "kind_key", "") == "psy_frog"]
        self.assertTrue(frogs)
        for e in frogs[:1]:
            e.hp = 0.0
            e.last_hit_by = s.hero
        step(s)
        self.assertEqual(st.found, 1)
        self.assertEqual(s.spawner.fixed.keys(),
                         {(QUEST_SID, bid, i, 0) for i in range(config.QUESTS["swamp"].count)})
        # The rest (dev shortcut, as F7), then the boss waits.
        self.assertTrue(q.dev_finish_hunt())
        self.assertEqual(st.stage, "awake")
        self.assertIn("lair", [k for _, _, k, _ in q.pins()])
        # Walk in: the gate seals and Froggy rises.
        lair = st.lair
        teleport(s, lair.cx, lair.cy + lair.radii[1] * 0.5)
        step(s)
        self.assertEqual(st.stage, "fight")
        boss = st.boss
        self.assertIn(boss, s.enemies)
        self.assertTrue(all(s.world.tile_at(*t) is tiles.THORN_GATE for t in lair.gate))
        self.assertEqual(q.stream_views()[0][:2], (lair.cx, lair.cy))
        # A boss far from every screen stays awake and keeps fighting.
        s.hero.invulnerable = True
        step(s, 120)
        self.assertIn(boss, s.enemies)
        # Beat it.
        loot0 = s.me.stats.loot
        boss.hp = 0.0
        boss.last_hit_by = s.hero
        step(s)
        self.assertEqual(st.stage, "cleared")
        self.assertEqual(q.guardians, 1)
        self.assertTrue(all(s.world.tile_at(*t) is tiles.MUD for t in lair.gate))
        self.assertGreaterEqual(s.me.stats.loot - loot0, config.BOSSES["froggy"].loot)
        self.assertIn("froggy", m.app.guild.achievements)
        self.assertTrue({"froggy", "psy_frog"} <= m.app.guild.pages)
        self.assertGreaterEqual(s.me.progress.picks, 1)
        self.assertEqual(s.me.progress.decree, config.BOSS_CARD_RARITY)
        self.assertEqual(q.log()[0], ("GLORY", f"guardians 1/{config.GUARDIANS}", False))
        self.assertTrue(q.log()[1][2])

    def test_frogs_wake_on_screen_and_count_whoever_kills_them(self):
        m, s = game()
        q = s.quests
        st = q.states["swamp"]
        teleport(s, st.npc.x, st.npc.y)
        q.talk(st.npc, s.me)
        step(s, 2)
        frogs = [e for e in s.enemies if getattr(e, "kind_key", "") == "psy_frog"]
        self.assertTrue(frogs)
        frogs[0].hp = 0.0
        frogs[0].last_hit_by = None                      # infighting: nobody's kill
        step(s)
        self.assertEqual(st.found, 1)

    def test_talking_again_tells_you_how_many_are_left(self):
        m, s = game()
        st = s.quests.states["swamp"]
        s.quests.talk(st.npc, s.me)
        st.found = 2
        s.quests.talk(st.npc, s.me)
        self.assertEqual(st.npc.line, "3 more of them glowing frogs.")

    def test_nobody_far_away_can_talk(self):
        m, s = game()
        st = s.quests.states["swamp"]
        self.assertIsNone(s.quests.npc_near(s.hero))     # at the start, far away
        s.me.controls.queue_interact()
        step(s)
        self.assertEqual(st.stage, "offered")

    def test_no_quests_on_the_test_map(self):
        class Scene:
            world = open_map()
        self.assertEqual(Quests(Scene()).states, {})


if __name__ == "__main__":
    unittest.main()
