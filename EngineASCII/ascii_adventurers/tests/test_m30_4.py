"""M30.4: Pandemonium's quest -- silencing the seven bandstands, the sober
man, the palace -- and form 1 of its boss, the Host of the Feast
(design/OCEAN.md 16, 17.1)."""

import math
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.ai import KINDS, make_enemy
from ascii_adventurers.ai import pandemonium as pand
from ascii_adventurers.ai.feast import FeastHost
from ascii_adventurers.players.controls import PlayerInput
from ascii_adventurers.render import plains  # noqa: F401  (adds the pictures to ART)
from ascii_adventurers.render.characters import ART
from ascii_adventurers.systems import temptation
from ascii_adventurers.tests.test_m30_2 import BAND, TABLE, arena, run
from ascii_adventurers.tests.test_p7 import enemy
from ascii_adventurers.world import tiles
from ascii_adventurers.world.chunked import ChunkedWorld
from ascii_adventurers.world.landmarks import quest_marks
from ascii_adventurers.world.zones import plan_of


def host(hero_at=(30.5, 22.0), x=30.5, y=12.0):
    """The Host in an open arena (no lair: round where he stands), resting
    unless a move is forced; guests come through a recruiter."""
    h = make_enemy("host_of_feast", x, y, random.Random(3))
    a = arena(h, hero_at=hero_at)

    def recruit(key, gx, gy):
        e = enemy(key, gx, gy, len(a.enemies))
        a.enemies.append(e)
        return e
    h.recruit = recruit
    h._rest = 99.0
    run(a, 1 / 60)
    return h, a


def force(h, a, move, seconds=0.0):
    h._gen = None
    h._start(move)
    h._wait = 0.0
    h._rest = 99.0
    if seconds:
        run(a, seconds)


class CatalogTest(unittest.TestCase):
    def test_the_quest_the_boss_and_their_looks(self):
        q = config.QUESTS["silence_bandstands"]
        self.assertEqual((q.biome, q.kind, q.count, q.boss),
                         ("pandemonium", "bandstands", 7, "host_of_feast"))
        self.assertIn("host_of_feast", KINDS)
        self.assertIn("host_of_feast", config.BESTIARY)
        self.assertIn("host_of_feast", config.ACHIEVEMENTS)
        self.assertEqual(config.ENEMIES["host_of_feast"].max_hp, 12000)   # (OCEAN.md 17.3)
        self.assertEqual(len(config.BOSSES["host_of_feast"].phases), 3)    # (three rooms)
        for name in ("sober_man", "host_of_feast", "host_of_feast_toast", "host_of_feast_bow",
                     "host_of_feast_spin"):
            self.assertIn(name, ART)
        self.assertFalse(tiles.INSTRUMENT.destructible)   # (only standing on the stage smashes them)


class PlacementTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = ChunkedWorld(31)
        cls.z = cls.w.layout.zone("pandemonium")
        cls.p = plan_of(cls.w.layout, cls.z)

    def test_the_pier_is_the_camp_and_the_palace_the_lair(self):
        camp, lair = quest_marks(self.w.layout, "silence_bandstands")
        self.assertEqual((camp.key, lair.key), ("pandemonium_pier", "pandemonium_hall"))
        self.assertEqual(camp.spots, [(x + 0.5, y + 0.5) for x, y in self.p.bandstands])
        self.assertEqual(len(camp.spots), 7)
        self.assertIs(lair.props["seal"], tiles.PALACE_GATE)
        self.assertTrue(lair.props["barred"])
        x, y = camp.npc                                    # (beside the jetty, on the beach)
        self.w.ensure_ready(int(x) - 2, int(y) - 2, int(x) + 2, int(y) + 2)
        self.assertFalse(self.w.tile_at(math.floor(x), math.floor(y)).solid)
        self.assertLess(math.hypot(x - camp.cx, y - camp.cy), 4.0)


class QuestFlowTest(unittest.TestCase):
    def setUp(self):
        from ascii_adventurers.tests.test_m16 import game
        self.m, self.s = game("wizard", seed=31)
        self.s.app.dev = True
        self.q = self.s.quests.states["silence_bandstands"]

    def test_hidden_on_the_maps_until_pandemonium_is_found(self):
        def mine():
            return [p for p in self.s.quests.pins() if p[3] == "THE SOBER MAN"]
        self.assertEqual(mine(), [])
        self.s.world.found_zones.add("pandemonium")
        self.assertEqual(len(mine()), 1)

    def test_smashing_a_stage_wakes_its_band_and_silences_it(self):
        s, q = self.s, self.q
        x, y = q.camp.spots[0]
        h = s.hero
        h.max_hp = h.hp = 1e9
        s.world.ensure_ready(int(x) - 30, int(y) - 30, int(x) + 30, int(y) + 30)
        lures = len(pand.lures(s.world))
        for _ in range(round(1.0 * 60)):
            h.x, h.y = x + 0.5, y + 1.5
            s._step(1 / 60)
        self.assertTrue(pand.frenzied(s.world, ("band", 0)))         # (its band turns on you)
        self.assertEqual(len(pand.lures(s.world)), lures - 1)        # (the song falters)
        self.assertEqual(h.entranced, 0.0)
        worn = q.heat[0]
        h.x, h.y = x + 12.0, y                                       # (step off: it pauses)
        for _ in range(60):
            s._step(1 / 60)
        self.assertAlmostEqual(q.heat[0], worn)
        for _ in range(round((config.BANDSTAND_TIME - worn + 0.3) * 60)):
            h.x, h.y = x + 0.5, y + 1.5
            s._step(1 / 60)
            h.hp = h.max_hp
        self.assertIn(0, q.lit)
        self.assertEqual(s.quests.broken_seals("pandemonium"), 1)
        self.assertEqual(pand.silenced(s.world), {0})
        tx, ty = math.floor(x), math.floor(y)
        near = [s.world.tile_at(tx + i, ty + j) for j in range(-8, 9) for i in range(-8, 9)]
        self.assertNotIn(tiles.INSTRUMENT, near)
        self.assertEqual(near.count(tiles.SMASHED_INSTRUMENT), 5)
        self.assertNotIn(tiles.LANTERN, [t for k, t in enumerate(near)
                                         if math.hypot(k % 17 - 8, k // 17 - 8) <= 8.5])

    def test_the_seventh_silence_opens_the_palace_and_its_gate_closes_behind_you(self):
        s, q = self.s, self.q
        s.quests.dev_key = "silence_bandstands"
        self.assertTrue(s.quests.dev_finish_hunt())
        self.assertEqual(q.stage, "awake")
        self.assertEqual(pand.silenced(s.world), set(range(7)))
        L = q.lair
        gx, gy = L.gate[0]
        s.world.ensure_ready(int(L.cx) - 50, int(L.cy) - 35, int(L.cx) + 50, int(L.cy) + 35)
        self.assertIs(s.world.tile_at(gx, gy), tiles.HALL_FLOOR)
        h = s.hero
        h.max_hp = h.hp = 1e9
        h.x, h.y = L.cx, L.cy - 10
        for _ in range(5):
            s._step(1 / 60)
        self.assertEqual(q.stage, "fight")
        b = q.boss
        self.assertIsInstance(b, FeastHost)
        self.assertEqual(b.max_hp, config.ENEMIES["host_of_feast"].max_hp)   # (no zone toughness)
        self.assertEqual(b.room, 0)
        self.assertEqual(len(b.guests), len(config.HOST_GUESTS[0]))
        self.assertTrue(all(e.home == ("room", 0) and e.state == "serene" for e in b.guests))
        self.assertGreater(len(b.table), 20)                        # (the banquet's long table)
        self.assertIs(s.world.charmer, b)
        for _ in range(60):
            s._step(1 / 60)
        self.assertTrue(all(s.world.tile_at(tx, ty) is tiles.PALACE_GATE for tx, ty in L.gate))
        b.take_damage(b.hp + 1, h, 0.0)
        for _ in range(3):
            s._step(1 / 60)
        self.assertEqual(q.stage, "cleared")
        self.assertIs(s.world.tile_at(gx, gy), tiles.HALL_FLOOR)
        self.assertIsNone(s.world.charmer)


class MusicTest(unittest.TestCase):
    def test_a_silenced_band_stops_tempting_carrying_and_doubling(self):
        a = arena(hero_at=(30.5, 22.5))
        w = a.world
        near = pand.wake_reach(w, ("band", 0))
        self.assertIn(BAND, pand.lures(w))
        pand.silence(w, 0)
        self.assertNotIn(BAND, pand.lures(w))
        self.assertGreater(pand.wake_reach(w, ("band", 0)), near)   # (no music: the usual reach)
        self.assertEqual(pand.frenzy(w, ("band", 0)), [("band", 0)])   # (it carries no further)

    def test_every_silenced_band_slows_your_temptation(self):
        def filled(quiet):
            a = arena(hero_at=(TABLE[0], TABLE[1] + 3.0))
            for i in range(quiet):
                pand.silence(a.world, 10 + i)
            scene = type("S", (), {"world": a.world, "effects": a.effects})()
            p = type("P", (), {"hero": a.hero})()
            for _ in range(60):
                temptation.step(scene, p, PlayerInput(), 1 / 60)
                a.hero.time += 1 / 60
            return a.hero.temptation
        self.assertAlmostEqual(filled(3) / filled(0), 1 - 3 * config.SILENCE_TEMPT, places=3)


class HostTest(unittest.TestCase):
    def test_he_never_stops_dancing_and_keeps_near_his_partner(self):
        h, a = host()
        spots = []
        for _ in range(8):
            run(a, 0.5)
            spots.append((h.x, h.y))
        self.assertTrue(all(math.hypot(p[0] - q[0], p[1] - q[1]) > 0.5
                            for p, q in zip(spots, spots[1:])))
        rx, ry = config.HOST_WALTZ[1]
        self.assertLess(max(math.hypot(x - a.hero.x, y - a.hero.y) for x, y in spots), rx * 2 + 4)

    def test_his_charm_sweeps_you_into_his_dance_and_he_spins_you_away(self):
        h, a = host(hero_at=(30.5, 15.5))
        hero = a.hero
        self.assertGreater(h.charm_at(hero), 0.0)
        a.world.charmer = h
        scene = type("S", (), {"world": a.world, "effects": a.effects})()
        p = type("P", (), {"hero": hero})()
        for _ in range(round(config.HOST_CHARM[1] * 3 * 60)):
            hero.x, hero.y = h.x, h.y + 3.0
            temptation.step(scene, p, PlayerInput(), 1 / 60)
            if hero.entranced > 0:
                break
        self.assertGreater(hero.entranced, 0.0)
        self.assertIs(hero.swept, h)
        inp = PlayerInput()
        temptation.step(scene, p, inp, 1 / 60)
        self.assertLess(inp.move_y, 0.0)                     # (drifting at him)
        hp = hero.hp
        hero.x, hero.y = h.x, h.y + h.hit_radius + 0.5
        run(a, 1 / 60)
        self.assertLess(hero.hp, hp)
        self.assertEqual(hero.entranced, 0.0)
        self.assertIsNone(hero.swept)
        self.assertGreater(math.hypot(hero.x - h.x, hero.y - h.y), h.hit_radius + 2.0)

    def test_three_rooms_each_with_its_guests(self):
        h, a = host()
        self.assertEqual(h.room, 0)
        first = list(h.guests)
        self.assertEqual([e.kind_key for e in first], list(config.HOST_GUESTS[0]))
        h.hp = h.max_hp * 0.6
        run(a, 1 / 60)
        self.assertEqual(h.room, 1)
        self.assertEqual(h.banner_req[0], "THE BALLROOM")
        self.assertTrue(all(getattr(e, "left", False) and not e.alive for e in first))
        self.assertEqual({e.kind_key for e in h.guests}, set(config.HOST_GUESTS[1]))
        h.hp = h.max_hp * 0.3
        run(a, 1 / 60)
        self.assertEqual(h.room, 2)
        self.assertTrue(all(e.home == ("room", 2) for e in h.guests))

    def test_a_toast_plants_him_floods_wine_and_frenzies_the_hall(self):
        h, a = host(hero_at=(30.5, 20.0))
        force(h, a, "toast", 0.2)
        self.assertTrue(h.planted)
        x = h.x
        hp, tmp = a.hero.hp, a.hero.temptation
        run(a, config.HOST_TOAST[0] - 0.3)
        self.assertAlmostEqual(h.x, x)                       # (planted while the glass is raised)
        run(a, 1.3)
        self.assertLess(a.hero.hp, hp)
        self.assertGreater(a.hero.temptation, tmp)
        self.assertTrue(pand.frenzied(a.world, ("room", 0)))

    def test_courses_served(self):
        h, a = host(hero_at=(30.5, 25.0))
        ctx = type("C", (), {"zones": a.zones, "projectiles": a.projectiles,
                             "effects": a.effects, "players": [a.hero], "events": [],
                             "world": a.world})()
        h._serve(ctx, "soup", 30.5, 20.0)
        self.assertEqual(a.zones[-1].kind, "scald")
        h._serve(ctx, "roast", 30.5, 20.0)
        self.assertEqual(sum(1 for p in a.projectiles if p.owner is h), config.HOST_ROAST)
        h._serve(ctx, "jelly", 30.5, 20.0)
        self.assertEqual(len(h.jellies), config.HOST_JELLY[0])
        h._serve(ctx, "cake", 30.5, 20.0)
        self.assertEqual(len(h.cakes), 1)
        hp = a.hero.hp
        run(a, config.HOST_CAKE[1] + config.HOST_JELLY[2] * config.HOST_JELLY[1] * 2)
        self.assertLess(a.hero.hp, hp)
        self.assertEqual((h.cakes, h.jellies), ([], []))
        force(h, a, "courses", config.HOST_COURSES[1] * 2)
        self.assertTrue(h.dishes)

    def test_the_dance_floor_burns_the_unlit_squares(self):
        h, a = host(hero_at=(30.5, 22.0))
        force(h, a, "dance", 0.1)
        fl = h.floor
        self.assertIsNotNone(fl)
        x0, y0, _, _ = h.floor_rect()
        size = config.HOST_DANCE[2]

        h.dazed = 99.0                                       # (he stays put: no shove)

        def stand(lit):
            want = fl["next"]
            for j in range(4, 10):
                for i in range(2, 9):
                    if ((i, j) in want) == lit:
                        a.hero.x, a.hero.y = x0 + (i + 0.5) * size, y0 + (j + 0.5) * size
                        return

        def to_beat(n):
            for _ in range(240):
                if fl["landed"] >= n:
                    return
                run(a, 1 / 60)
        stand(True)
        hp = a.hero.hp
        to_beat(1)
        self.assertEqual(a.hero.hp, hp)                      # (on the steps: safe)
        stand(False)
        to_beat(2)
        self.assertLess(a.hero.hp, hp)                       # (off them: it burns)

    def test_the_vaults_gold_walls_coins_and_a_coin_caught(self):
        h, a = host(hero_at=(30.5, 18.0))
        force(h, a, "gold", 0.65)
        self.assertEqual(len(h.walls), config.HOST_WALLS[0])
        run(a, 0.7)
        self.assertEqual(sum(1 for m in h.marks if m[4] == "coins"), config.HOST_POUR[0])
        run(a, 0.6)
        self.assertEqual(len(h.coins), config.HOST_TOSS[0])
        c = h.coins[0]
        tmp = a.hero.temptation
        a.hero.x, a.hero.y = c[0], c[1]
        run(a, 1 / 60)
        self.assertGreater(a.hero.gilt_until, a.hero.time)
        self.assertAlmostEqual(a.hero.temptation, min(100.0, tmp + config.HOST_TOSS[4]), places=3)
        from ascii_adventurers.systems import combat
        target = enemy("glutton", 40.5, 18.0)
        dealt = combat.strike(target, 10.0, a.hero, 0.0, a.effects, can_crit=False)
        self.assertGreater(dealt, 10.0 * 1.2)

    def test_the_beckoning_pulls_you_then_slashes(self):
        h, a = host(hero_at=(30.5, 21.0))
        force(h, a, "beckon", config.HOST_BECKON[0] + 0.5)
        self.assertTrue(h.pulling)
        self.assertLess(a.hero.y, 21.0)                      # (drawn toward him)
        hp = a.hero.hp
        run(a, config.HOST_BECKON[1])
        self.assertLess(a.hero.hp, hp)

    def test_the_carving_set_curves_across_itself(self):
        h, a = host()
        force(h, a, "carving", 0.6)
        knives = [p for p in a.projectiles if p.owner is h]
        self.assertEqual(len(knives), 2 * config.HOST_CARVING[1])
        self.assertEqual({math.copysign(1, p.curve) for p in knives}, {-1.0, 1.0})

    def test_chandeliers_fall_on_marked_spots_and_leave_glass(self):
        h, a = host(hero_at=(30.5, 22.0))
        force(h, a, "chandeliers", 0.1)
        self.assertEqual(len(h.marks), config.HOST_CHANDELIERS[0])
        hp = a.hero.hp
        run(a, config.HOST_CHANDELIERS[1] + 0.1)
        self.assertLess(a.hero.hp, hp)                       # (one on you)
        self.assertEqual(sum(1 for z in a.zones if z.kind == "broken_glass"),
                         config.HOST_CHANDELIERS[0])

    def test_the_grand_spin_glides_and_flings_cutlery(self):
        h, a = host()
        x, y = h.x, h.y
        force(h, a, "spin", 1.5)
        self.assertTrue(h.gliding)
        self.assertGreater(math.hypot(h.x - x, h.y - y), 4.0)
        self.assertGreater(sum(1 for p in a.projectiles if p.spec.look == "cutlery"), 10)


class GameTest(unittest.TestCase):
    def test_the_fight_draws_in_every_room_through_every_move(self):
        from ascii_adventurers.tests.test_m16 import game
        m, s = game("wizard", seed=31)
        s.app.dev = True
        q = s.quests.states["silence_bandstands"]
        s.quests.dev_key = "silence_bandstands"
        s.quests.dev_finish_hunt()
        L = q.lair
        h = s.hero
        h.max_hp = h.hp = 1e9
        s.world.ensure_ready(int(L.cx) - 50, int(L.cy) - 35, int(L.cx) + 50, int(L.cy) + 35)
        h.x, h.y = L.cx, L.cy - 10
        for _ in range(5):
            s._step(1 / 60)
        b = q.boss
        for room, frac in enumerate((1.0, 0.6, 0.3)):
            b.hp = b.max_hp * frac
            for move in ("courses", "toast", "spin", "beckon", "carving", "chandeliers", "dance",
                         "gold"):
                b._gen = None
                b._start(move)
                b._wait = 0.0
                for _ in range(50):
                    s._step(1 / 60)
                    h.hp = h.max_hp
                s.me.camera.center_on(h.x, h.y)
                s.draw(m.text)
            self.assertEqual(b.room, room)
        self.assertEqual(q.stage, "fight")
        self.assertTrue(any(s.world.tile_at(tx, ty) is tiles.COIN_HEAP
                            for tx, ty in b.stamped))       # (the vault's heaps)


if __name__ == "__main__":
    unittest.main()
