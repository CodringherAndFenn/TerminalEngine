"""M31.4: the great hunt and the Ancestor's first form (design/OCEAN.md 27-28.1):
seven named great beasts out on the island's rings, each kill painted on the
painted caves' deepest wall, the old painter by the fire, the seventh parting
the caldera's curtain of fire; the Ancestor, the ages: the great mammal, the
tyrant lizard, the giant insect, moulting into husks that echo; the stampede,
the roar, the swarm; the charge, the spit fan, the eruption, the sweep; all
of it echoing 3 s later."""

import math
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.ai import KINDS, make_enemy
from ascii_adventurers.ai.ancestor import AGE_BANNERS, Ancestor, River
from ascii_adventurers.ai.brain import AIContext
from ascii_adventurers.render import pangaea_art  # noqa: F401
from ascii_adventurers.render.ascii_fx import SHOT_LOOKS
from ascii_adventurers.render.characters import ART
from ascii_adventurers.systems.quests import QUEST_SID
from ascii_adventurers.tests.test_m31_1 import pang
from ascii_adventurers.tests.test_m31_2 import arena, run
from ascii_adventurers.world import tiles
from ascii_adventurers.world.test_map import TestMap

DT = 1 / 60
MOVES = ("stampede", "roar", "swarm", "charge", "spit", "eruption", "sweep")


def ancestor(hero_at=(40.5, 40.5), x=40.5, y=30.5, still=True):
    """The Ancestor on an open caldera floor (no lair: its arena is an oval
    round where it woke), resting unless a move is forced; `still`: it
    doesn't move between moves."""
    w = TestMap(["." * 80 for _ in range(60)], legend={".": tiles.CALDERA_FLOOR})
    b = make_enemy("ancestor", x, y, random.Random(3))
    a = arena(b, hero_at=hero_at, world=w)
    b._rest = 99.0
    end = b._end_move

    def ended():                                      # (and it rests after a forced move)
        end()
        b._rest = 99.0
    b._end_move = ended
    if still:
        b._move_like_its_age = lambda dt: None
    run(a, DT)
    return b, a


def force(b, a, move, seconds=0.0):
    b._gen = None
    b._start(move)
    b._wait = 0.0
    b._rest = 99.0
    if seconds:
        run(a, seconds)


def toasts(a, label):
    return sum(1 for e in a.effects if e.kind == "toast" and getattr(e, "label", "") == label)


class CatalogTest(unittest.TestCase):
    def test_the_quest_the_beasts_the_boss_and_their_looks(self):
        q = config.QUESTS["great_hunt"]
        self.assertEqual((q.biome, q.kind, q.boss, q.count, q.giver), ("pangaea", "hunt", "ancestor",
                                                                       7, "old painter"))
        self.assertEqual(q.targets, tuple(k for k, *_ in config.GREAT_BEASTS))
        self.assertEqual(len(set(q.targets)), 7)
        self.assertIn(q.giver_sprite, ART)
        for key, name, base, ring in config.GREAT_BEASTS:
            g, b = config.ENEMIES[key], config.ENEMIES[base]
            self.assertEqual((g.name, g.kind, g.sprite), (name, b.kind, b.sprite))
            self.assertGreater(g.max_hp, b.max_hp)
            self.assertGreater(g.scale, b.scale)           # (bigger than the rest of its kind)
            self.assertGreater(g.size_px, b.size_px)
            self.assertEqual(g.biomes, ())                 # (quest-only, never rolled)
            self.assertTrue(g.elite)
            self.assertIn(ring, (0, 1, 2))
        self.assertEqual({r for *_, r in config.GREAT_BEASTS}, {0, 1, 2})   # (every ring has some)
        spec = config.ENEMIES["ancestor"]
        self.assertIs(KINDS[spec.kind], Ancestor)
        self.assertEqual(spec.max_hp, 12000)
        self.assertIn("ancestor", config.BESTIARY)
        self.assertIn("ancestor", config.ACHIEVEMENTS)
        self.assertEqual(len(config.BOSSES["ancestor"].phases), 3)
        for name in ("ancestor_mammal", "ancestor_lizard", "ancestor_insect"):
            for pic in (name, name + "_open"):
                self.assertEqual(len(ART[pic]), 18)
                self.assertTrue(all(len(r) == 14 for r in ART[pic]), pic)
        for shot, *_ in config.ANCESTOR_SPIT:
            for k in (shot, shot + "_echo"):
                self.assertIn(k, config.PANGAEA_SHOTS)
                self.assertIn(config.PANGAEA_SHOTS[k].look, SHOT_LOOKS)


class PlacementTest(unittest.TestCase):
    def test_each_great_beast_lives_on_its_ring_and_deep_claw_in_a_pool(self):
        for seed in (31, 7, 1234):
            _, _, p = pang(seed)
            self.assertEqual(len(p.hunt), 7, seed)
            for (x, y), (key, _, base, ring) in zip(p.hunt, config.GREAT_BEASTS):
                if base == "sea_scorpion":
                    self.assertTrue(any(math.hypot(x - px - 0.5, y - py - 0.5) < 0.1
                                        for px, py, _ in p.pools), seed)
                    continue
                self.assertEqual(p.ring_at(x, y), ring, (seed, key))
                self.assertFalse(p.in_caldera(x, y, p.cone), (seed, key))
            land = [s for s, (_, _, base, _) in zip(p.hunt, config.GREAT_BEASTS)
                    if base != "sea_scorpion"]
            gaps = [math.hypot(a[0] - b[0], a[1] - b[1]) for i, a in enumerate(land)
                    for b in land[i + 1:]]
            self.assertGreater(min(gaps), 20, seed)          # (they don't share a fight)

    def test_the_caves_are_the_camp_and_the_caldera_the_lair(self):
        _, _, p = pang()
        caves = next(m for m in p.marks if m.key == "pangaea_caves")
        self.assertEqual((caves.kind, caves.quest), ("camp", "great_hunt"))
        self.assertEqual(caves.spots, p.hunt)
        self.assertIsNotNone(caves.npc)
        groups = caves.props["hunt_wall"]
        self.assertEqual(len(groups), 7)
        for g in groups:
            self.assertTrue(g)
            for tx, ty in g:
                self.assertIs(caves.tile_at(tx, ty), tiles.PAINTED_WALL)
        star = caves.props["star_wall"]
        self.assertTrue(star)                                 # (the end of the age, painted already)
        for tx, ty in star:
            self.assertIs(caves.tile_at(tx, ty), tiles.STAR_MURAL)
        cal = next(m for m in p.marks if m.key == "pangaea_caldera")
        self.assertEqual((cal.kind, cal.quest), ("lair", "great_hunt"))
        self.assertEqual(cal.spots, [(cal.cx, cal.cy)])
        dens = [m for m in p.marks if m.key == "pangaea_den"]
        self.assertEqual(len(dens), 6)                       # (Deep Claw's is its pool)
        self.assertTrue(all(m.kind == "spot" for m in dens))


class QuestFlowTest(unittest.TestCase):
    def setUp(self):
        from ascii_adventurers.tests.test_m16 import game
        self.m, self.s = game("wizard", seed=31)
        self.s.app.dev = True
        self.q = self.s.quests.states["great_hunt"]

    def kill(self, i):
        s, q = self.s, self.q
        sid = (QUEST_SID, q.qid, i, 0)
        key, x, y = s.spawner.fixed[sid]
        e = s.spawner.wake(key, x, y, sid)
        s.enemies.append(e)
        e.hp = 0.0
        e.last_hit_by = s.me
        for _ in range(3):
            s._step(DT)
        return e

    def test_each_spot_holds_its_great_beast_and_each_kill_is_painted(self):
        s, q = self.s, self.q
        s.world.found_zones.add("pangaea")                    # (pinned once it's found)
        self.assertEqual(q.npc.name, "old painter")
        for i, (key, *_) in enumerate(config.GREAT_BEASTS):
            self.assertEqual(s.spawner.fixed[(QUEST_SID, q.qid, i, 0)][0], key)
        e = self.kill(3)                                      # (Thunderfoot; nobody took the quest)
        self.assertEqual(e.espec.name, "Thunderfoot")
        self.assertTrue(getattr(e, "zone_tough", False))
        self.assertEqual(q.found, 1)
        walls = q.camp.props["hunt_wall"]
        for i, g in enumerate(walls):
            want = tiles.HUNT_MURAL if i == 3 else tiles.PAINTED_WALL
            for tx, ty in g:
                self.assertIs(s.world.tile_at(tx, ty), want, i)
        s.quests.talk(q.npc, s.me)                            # (taken: the pins by name)
        x, y = q.camp.spots[0]
        pins = s.quests.pins(near=(x, y))
        self.assertIn((x, y, "target", "OLD TUSK"), pins)
        self.assertFalse(any(p[3] == "THUNDERFOOT" for p in pins))      # (dead: no pin)

    def test_the_seventh_parts_the_curtain_and_the_ancestor_wakes_in_the_caldera(self):
        s, q = self.s, self.q
        for i in range(7):
            self.kill(i)
        self.assertEqual(q.stage, "awake")
        self.assertEqual(s.quests.banner.title, "THE LAST GREAT BEAST FALLS")
        L = q.lair
        for tx, ty in L.gate:
            self.assertIs(s.world.tile_at(tx, ty), tiles.CALDERA_FLOOR)
        h = s.hero
        h.max_hp = h.hp = 1e9
        s.world.ensure_ready(int(L.cx) - 50, int(L.cy) - 35, int(L.cx) + 50, int(L.cy) + 35)
        h.x, h.y = L.cx, L.cy - 12
        for _ in range(5):
            s._step(DT)
        self.assertEqual(q.stage, "fight")
        self.assertEqual(s.quests.banner.sub, "in the heart of the volcano")
        b = q.boss
        self.assertIsInstance(b, Ancestor)
        self.assertIs(b.lair, L)
        for _ in range(60):
            s._step(DT)
        self.assertTrue(all(s.world.tile_at(tx, ty) is tiles.FIRE_CURTAIN for tx, ty in L.gate))
        # Every age, every move, drawn: it never leaves the caldera.
        for age, frac in enumerate((1.0, 0.6, 0.3)):
            b.hp = b.max_hp * frac
            for move in MOVES:
                b._gen = None
                b._start(move)
                b._wait = 0.0
                for _ in range(50):
                    s._step(DT)
                    h.hp = h.max_hp
                    self.assertTrue(L.inside(b.x, b.y), (age, move))
                s.me.camera.center_on(h.x, h.y)
                s.draw(self.m.text)
            self.assertEqual(b.age, age)
        self.assertEqual(len(b.husks), 2)
        b.hp = 0.0
        b.last_hit_by = s.me
        for _ in range(3):
            s._step(DT)
        self.assertEqual(q.stage, "cleared")
        self.assertTrue(all(h.crumbled for h in b.husks))
        self.assertFalse(any(s.world.tile_at(tx, ty) is tiles.HUSK
                             for hk in b.husks for tx, ty in [(math.floor(hk.x), math.floor(hk.y))]))
        for tx, ty in L.gate:
            self.assertIs(s.world.tile_at(tx, ty), tiles.CALDERA_FLOOR)


class AgesTest(unittest.TestCase):
    def test_it_moults_into_each_older_age_leaving_a_husk(self):
        b, a = ancestor()
        self.assertEqual((b.age, b.sprite_now()), (0, "ancestor_mammal"))
        b.hp = b.max_hp * 0.6
        run(a, DT)
        self.assertEqual(b.age, 1)
        self.assertGreater(b.moulting, 0)
        self.assertFalse(b.hittable)                          # (bursting out: it can't be hurt)
        self.assertEqual(b.banner_req, AGE_BANNERS[1])
        self.assertEqual(b.hit_radius, config.ANCESTOR_HIT_RADIUS[1])
        h = b.husks[0]
        self.assertEqual((h.age, h.sprite), (0, "ancestor_mammal"))
        self.assertTrue(h.stamped)
        for tx, ty in h.stamped:
            self.assertIs(a.world.tile_at(tx, ty), tiles.HUSK)     # (cover)
        self.assertTrue(tiles.HUSK.solid and tiles.HUSK.blocks_shots)
        run(a, config.ANCESTOR_MOULT[0])
        self.assertTrue(b.hittable)
        self.assertEqual(b.sprite_now(), "ancestor_lizard")
        b.hp = b.max_hp * 0.3
        run(a, DT)
        self.assertEqual((b.age, len(b.husks)), (2, 2))
        self.assertEqual(b.husks[1].sprite, "ancestor_lizard")

    def test_a_husk_echoes_its_age_then_crumbles(self):
        b, a = ancestor()
        b.hp = b.max_hp * 0.6
        run(a, DT)
        h = b.husks[0]
        cells = dict(h.stamped)
        mine = []
        for _ in range(round(config.ANCESTOR_MOULT[3] * 60)):
            run(a, DT)
            mine = [e for e in b.echoes if (e.x, e.y) == (h.x, h.y)]
            if mine:
                break
        self.assertTrue(mine)                                 # (its charge, from where it lies)
        self.assertEqual((mine[0].kind, mine[0].sprite), ("run", "ancestor_mammal"))
        self.assertLessEqual(mine[0].t, config.ANCESTOR_MOULT[4])  # (its tell shows now)
        run(a, config.ANCESTOR_MOULT[5])
        self.assertTrue(h.crumbled)
        for (tx, ty), t in cells.items():
            self.assertIs(a.world.tile_at(tx, ty), t)         # (the floor comes back)

    def test_it_moves_like_its_age(self):
        b, a = ancestor(still=False)
        moved = []
        for age, frac in enumerate((1.0, 0.6, 0.3)):
            b.hp = b.max_hp * frac
            run(a, config.ANCESTOR_MOULT[0] + 0.2)
            x, y, went = b.x, b.y, 0.0
            for _ in range(180):
                run(a, DT)
                went += math.hypot(b.x - x, b.y - y)
                x, y = b.x, b.y
            moved.append(went)
        self.assertTrue(all(d > 3.0 for d in moved), moved)   # (always moving)
        self.assertGreater(moved[0], moved[1])                # (the mammal gallops, the lizard stalks)


class EchoTest(unittest.TestCase):
    def test_everything_it_does_echoes_and_its_death_cancels_them(self):
        for move in MOVES:
            b, a = ancestor()
            force(b, a, move, 2.5)
            self.assertTrue(b.echoes, move)
            for e in b.echoes:
                self.assertLessEqual(e.t, config.ECHO[0])
            b.hp = 0.0
            run(a, DT)
            self.assertEqual((b.echoes, b.runners, b.rivers), ([], [], []), move)

    def test_the_roar_roots_you_and_plays_again_three_seconds_on(self):
        b, a = ancestor()
        b.facing = b.angle_to(a.hero.x, a.hero.y)
        force(b, a, "roar", config.ANCESTOR_ROAR[0] + 0.1)
        self.assertEqual(toasts(a, "FEAR!"), 1)
        echo = next(e for e in b.echoes if e.kind == "area")
        self.assertEqual(echo.data["damage"], b.hurt(config.ANCESTOR_ROAR[4]))    # (full damage)
        self.assertEqual(echo.data["root"], config.ANCESTOR_ROAR[3])
        self.assertTrue(any(e.kind == "lobs" and e.data["what"] == "rock" for e in b.echoes))
        run(a, config.ECHO[0])
        self.assertEqual(toasts(a, "FEAR!"), 2)               # (the echo roars again)

    def test_mid_roll_the_roar_cant_touch_you(self):
        b, a = ancestor()
        force(b, a, "roar", config.ANCESTOR_ROAR[0] - 0.1)
        a.hero.roll_t = 5.0
        run(a, 0.3)
        self.assertEqual(toasts(a, "FEAR!"), 0)

    def test_the_stampede_leaves_gaps_to_stand_in(self):
        hurt = []
        for in_gap in (True, False):
            b, a = ancestor()
            force(b, a, "stampede", config.ANCESTOR_STAMPEDE[0] + 0.05)
            lanes = b.lanes
            self.assertEqual(len(lanes), config.ANCESTOR_STAMPEDE[2])
            ang = lanes[0][2]
            px, py = -math.sin(ang), math.cos(ang)
            offs = sorted((x0 - a.hero.x) * px + (y0 - a.hero.y) * py for x0, y0, *_ in lanes)
            k = len(offs) // 2
            to = (offs[k - 1] + offs[k]) / 2 if in_gap else offs[k]
            a.hero.x += px * to
            a.hero.y += py * to
            hp = a.hero.hp
            run(a, 7.0)                                       # (the herd, then its echo)
            hurt.append(hp - a.hero.hp)
            self.assertTrue(all(r.look in ("ochre", "ghost") for r in b.runners))
        self.assertEqual(hurt[0], 0.0)
        self.assertGreater(hurt[1], 0.0)

    def test_the_swarm_stings_only_inside_its_river(self):
        b, a = ancestor()
        h = a.hero
        n, shown, stings, half, drift, sway, dmg, every = config.ANCESTOR_SWARM
        b.rivers.append(River(h.x, h.y + 6.0, 0.0, 0.0, 0.0, 0.0, 0.0, 3.0, half, 9.0, every))
        hp = h.hp
        run(a, 1.0)
        self.assertEqual(h.hp, hp)                            # (6 tiles off its line)
        b.rivers.append(River(h.x, h.y, 0.0, 0.0, 0.0, 0.0, 0.0, 3.0, half, 9.0, every))
        run(a, 1.0)
        self.assertLess(h.hp, hp)
        force(b, a, "swarm", 0.1)
        self.assertGreaterEqual(len(b.rivers), n)
        self.assertEqual(sum(1 for e in b.echoes if e.kind == "river"), n)

    def test_the_charge_runs_its_line_and_a_ghost_runs_it_again(self):
        b, a = ancestor()
        hp = a.hero.hp
        force(b, a, "charge", 2.5)
        self.assertLess(a.hero.hp, hp)
        echo = next(e for e in b.echoes if e.kind == "run")
        run(a, echo.t + DT)
        self.assertTrue(any(r.look == "ghost" for r in b.runners))

    def test_the_spit_fan_is_its_ages_shots_and_echoes_faded(self):
        for age, frac in enumerate((1.0, 0.6, 0.3)):
            b, a = ancestor()
            b.hp = b.max_hp * frac
            run(a, config.ANCESTOR_MOULT[0] + 0.1)
            shot, n, spread, shown = config.ANCESTOR_SPIT[age]
            force(b, a, "spit", shown + 0.05)
            mine = [p for p in a.projectiles if p.owner is b]
            self.assertEqual(len(mine), n, age)
            self.assertTrue(all(p.spec.look == shot for p in mine))
            run(a, config.ECHO[0])
            echoed = [p for p in a.projectiles if getattr(p, "echo", False)]
            self.assertTrue(echoed, age)
            self.assertTrue(all(p.spec.look == shot + "_echo" for p in echoed))

    def test_the_eruption_drops_bombs_round_you(self):
        b, a = ancestor()
        stomp, n, marked, radius, dmg, spread = config.ANCESTOR_ERUPTION
        force(b, a, "eruption", stomp + 0.05)
        bombs = [l for l in b.lobs if l[6] == "bomb"]
        self.assertEqual(len(bombs), n)
        for l in bombs:
            self.assertLessEqual(math.hypot(l[2] - a.hero.x, l[3] - a.hero.y), spread + 3.0)
        hp = a.hero.hp
        run(a, marked)
        self.assertLess(a.hero.hp, hp)                        # (one on where you were going)

    def test_the_sweep_backs_up_to_you_and_strikes_behind_it(self):
        b, a = ancestor(hero_at=(40.5, 36.5))
        hp = a.hero.hp
        deg, reach, dmg, push, shown = config.ANCESTOR_SWEEP[0]
        force(b, a, "sweep", 0.2)
        to = b.angle_to(a.hero.x, a.hero.y)
        self.assertLess(abs((b.facing - to - math.pi + math.pi) % math.tau - math.pi), 0.3)
        run(a, shown + 0.1)
        self.assertLess(a.hero.hp, hp)


if __name__ == "__main__":
    unittest.main()
