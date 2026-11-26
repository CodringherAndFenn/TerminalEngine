"""M31.5: the Ancestor's second form, the first life (design/OCEAN.md 28.2-28.3):
at 0 the giant insect's skin splits and the caldera floods; the tide rises
and falls (the deep you wade, the rocks and husks above it); life crawling
out of the sea and evolving if left alone; the husks waking as echoes of
the ages; tentacles; the tidal wave; dive and surface, whirlpool, boiling
bubbles, arm lash; all of it echoing."""

import math
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.ai import KINDS, make_enemy
from ascii_adventurers.ai.first_life import FirstBlob, FirstCrawler, Lash, Sweep, Wave, Whirl
from ascii_adventurers.render import pangaea_art  # noqa: F401
from ascii_adventurers.render.ascii_fx import SHOT_LOOKS
from ascii_adventurers.render.characters import ART
from ascii_adventurers.tests.test_m31_2 import run
from ascii_adventurers.tests.test_m31_4 import ancestor, force
from ascii_adventurers.world import tiles

DT = 1 / 60
MOVES = ("dive", "whirlpool", "bubbles", "lash", "tentacles", "wave")


def first_life(hero_at=(40.5, 40.5), x=40.5, y=30.5):
    """The Ancestor already in its second form (no lair: no sea), resting."""
    b, a = ancestor(hero_at=hero_at, x=x, y=y)
    b.take_damage(b.hp + 5, a.hero, 0.0)
    run(a, config.FIRST_LIFE_RISE + 0.1)
    b._rest = 99.0
    b._swim = lambda dt: None
    b.life_t = 999.0                                  # (nothing crawls out unless a test wants it)
    return b, a


def recruits(b, a):
    def recruit(key, x, y):
        e = make_enemy(key, x, y, random.Random(len(a.enemies)))
        a.enemies.append(e)
        return e
    b.recruit = recruit


class CatalogTest(unittest.TestCase):
    def test_form_two_its_moves_its_life_and_their_looks(self):
        spec = config.BOSSES["ancestor_first_life"]
        self.assertEqual([p.below for p in spec.phases], [1.0, 0.75, 0.5, 0.25])
        keys = config.BOSS_KEYS                          # (added after every boss before it:
        self.assertEqual(keys.index("ancestor_first_life"), keys.index("ancestor") + 1)   # seeds stay;
        self.assertLess(keys.index("ancestor_first_life"), keys.index("overseer"))    # M32.4's after)
        moves = {m for p in spec.phases for m, _ in p.moves}
        self.assertEqual(moves, set(MOVES))
        b, _ = ancestor()
        for m in moves:
            self.assertTrue(callable(getattr(b, "m_" + m)), m)
        self.assertIn("tentacles", dict(spec.phases[2].moves))
        self.assertNotIn("tentacles", dict(spec.phases[1].moves))
        self.assertIn("wave", dict(spec.phases[3].moves))
        self.assertAlmostEqual(config.FIRST_LIFE_HP * 12000, 14000)
        self.assertIs(KINDS["first_blob"], FirstBlob)
        self.assertIs(KINDS["first_crawler"], FirstCrawler)
        for key in config.LIFE_STAGES + config.LIFE_BEASTS:
            self.assertIn(key, config.ENEMIES)
        for key in config.LIFE_STAGES + ("sabre_cub",):
            self.assertEqual(config.ENEMIES[key].biomes, ())  # (never rolled)
        self.assertLess(config.ENEMIES["sabre_cub"].scale, config.ENEMIES["sabre_tooth"].scale)
        for key in ("first_blob", "first_crawler"):
            self.assertIn(key, config.BESTIARY)
            self.assertIn(key, config.BOSSES["ancestor"].pages)
        for pic in ("first_life", "first_life_open", "first_blob", "first_crawler"):
            self.assertEqual(len(ART[pic]), 18)
            self.assertTrue(all(len(r) == 14 for r in ART[pic]), pic)
        for k in ("spray", "spray_echo"):
            self.assertIn(config.PANGAEA_SHOTS[k].look, SHOT_LOOKS)
        for t in (tiles.TIDE_SHALLOWS, tiles.TIDE_SEA, tiles.TIDE_ROCK):
            self.assertFalse(t.solid or t.blocks_shots, t.name)      # (walkable, all of it)


class SplitTest(unittest.TestCase):
    def test_at_zero_the_insect_splits_and_the_first_life_rises(self):
        b, a = ancestor()
        for frac in (0.6, 0.3):
            b.hp = b.max_hp * frac
            run(a, config.ANCESTOR_MOULT[0] + DT)
        self.assertEqual(b.age, 2)
        old = b.max_hp
        b.take_damage(b.hp + 50, a.hero, 0.0)
        self.assertEqual((b.form, b.hp), ("rising", 1.0))
        self.assertTrue(b.alive)
        self.assertFalse(b.hittable)
        self.assertEqual(b.take_damage(500, a.hero, 0.0), 0.0)   # (it can't be hurt as it rises)
        self.assertEqual([h.age for h in b.husks], [0, 1, 2])  # (the insect's skin, split)
        self.assertEqual(b.banner_req[0], "THE FIRST LIFE RISES")
        self.assertEqual(b.bar_label, "The Ancestor -- the first life")
        run(a, config.FIRST_LIFE_RISE + DT)
        self.assertEqual(b.form, 2)
        self.assertEqual(b.max_hp, round(old * config.FIRST_LIFE_HP))
        self.assertEqual(b.hp, b.max_hp)
        self.assertTrue(b.hittable)
        self.assertEqual((b.bspec.name, b.phase), ("The First Life", 0))
        self.assertEqual(b.hit_radius, config.FIRST_LIFE_HIT_RADIUS)
        self.assertEqual(b.sprite_now(), "first_life")
        self.assertEqual(b.banner_req[0], "THE FIRST LIFE")

    def test_its_phases_wake_the_husks_and_bring_its_arms_and_the_wave(self):
        b, a = first_life()
        b.hp = b.max_hp * 0.7
        run(a, DT)
        self.assertEqual(b.phase, 1)
        self.assertEqual(sorted(h.age for h in b.husks if h.awake), [0, 1, 2])   # (every age's)
        for h in b.husks:
            self.assertFalse(h.crumbled)
            self.assertTrue(h.stamped)
        b.hp = b.max_hp * 0.2
        run(a, DT)
        self.assertEqual(b.phase, 3)


class TideTest(unittest.TestCase):
    """In the real caldera (the flood needs its lair)."""

    @classmethod
    def setUpClass(cls):
        from ascii_adventurers.tests.test_m16 import game
        cls.m, s = game("wizard", seed=31)
        cls.s = s
        s.app.dev = True
        q = s.quests.states["great_hunt"]
        cls.q = q
        s.quests.dev_key = "great_hunt"
        s.quests.dev_finish_hunt()
        L = q.lair
        s.world.ensure_ready(int(L.cx) - 75, int(L.cy) - 55, int(L.cx) + 75, int(L.cy) + 55)
        h = s.hero
        h.max_hp = h.hp = 1e9
        h.x, h.y = L.cx + 2, L.cy - 6
        for _ in range(5):
            s._step(DT)
        cls.b = q.boss
        cls.L = L

    def steps(self, seconds):
        for _ in range(round(seconds * 60)):
            self.s._step(DT)
            self.s.hero.hp = self.s.hero.max_hp

    def test_the_flood_the_tide_wading_and_the_drain(self):
        s, b, L, h = self.s, self.b, self.L, self.s.hero
        w = s.world
        self.assertEqual(self.q.stage, "fight")
        end = b._end_move

        def ended():                                  # (it rests after a move)
            end()
            b._rest = 99.0
        b._end_move = ended
        lakes = L.props["lakes"]
        b.take_damage(b.hp + 10, h, 0.0)
        self.assertEqual(b.form, "rising")
        n = len(b.flood)
        self.assertGreater(n, 5000)
        self.steps(config.FIRST_LIFE_RISE / 2)        # (from the rim in: the rim's wet first)
        rim = next(p for p, _ in b.flood if w.tile_at(*p) is not tiles.HUSK)
        mid = next(p for p, _ in reversed(b.flood) if w.tile_at(*p) is not tiles.HUSK)
        self.assertIn(w.tile_at(*rim), (tiles.TIDE_SHALLOWS, tiles.TIDE_ROCK))
        self.assertIn(w.tile_at(*mid), (tiles.CALDERA_FLOOR, tiles.LAVA, tiles.LAVA_CRUST))
        self.steps(config.FIRST_LIFE_RISE / 2 + 0.1)
        self.assertEqual(b.form, 2)
        names = {}
        for p, t in b.orig.items():
            names[w.tile_at(*p)] = names.get(w.tile_at(*p), 0) + 1
        self.assertEqual(set(names) - {tiles.TIDE_SHALLOWS, tiles.TIDE_ROCK, tiles.HUSK}, set())
        self.assertGreater(names[tiles.TIDE_SHALLOWS], n // 2)
        self.assertGreater(names[tiles.TIDE_ROCK], 500)      # (rocks stand above it)
        for lx, ly, _ in lakes:                               # (the lava lakes quenched)
            self.assertIs(w.tile_at(math.floor(lx), math.floor(ly)), tiles.TIDE_ROCK)
        # The tide: the deep comes in from the rim, the middle last.
        b._rest = 99.0
        b.tide, b.tide_t = "rising", config.TIDE[1]
        self.steps(config.TIDE[1] / 2)
        self.assertIs(w.tile_at(*next(p for p in b.sea if w.tile_at(*p) is not tiles.HUSK)),
                      tiles.TIDE_SEA)
        self.assertIs(w.tile_at(*next(p for p in reversed(b.sea) if w.tile_at(*p) is not tiles.HUSK)),
                      tiles.TIDE_SHALLOWS)
        self.steps(config.TIDE[1] / 2 + 0.1)
        self.assertEqual(b.tide, "high")
        deep = sum(1 for p in b.sea if w.tile_at(*p) is tiles.TIDE_SEA)
        self.assertGreater(deep, len(b.sea) - 300)            # (all but under the husks)
        # In the deep you wade; mid-roll you don't.
        p = next(p for p in b.sea if w.tile_at(*p) is tiles.TIDE_SEA
                 and math.hypot(p[0] - b.x, p[1] - b.y) > 12)
        h.x, h.y = p[0] + 0.5, p[1] + 0.5
        h.slow_t = 0.0
        self.steps(DT * 2)
        self.assertGreater(h.slow_t, 0)
        self.assertAlmostEqual(h.slow_mult, config.TIDE[4])
        rock = next(q for q, t in b.flood if t is tiles.TIDE_ROCK and w.tile_at(*q) is tiles.TIDE_ROCK
                    and math.hypot(q[0] - b.x, q[1] - b.y) > 12)
        h.x, h.y = rock[0] + 0.5, rock[1] + 0.5
        h.slow_t = 0.0
        self.steps(DT * 2)
        self.assertEqual(h.slow_t, 0.0)                       # (on a rock: dry)
        b.tide_t = DT / 2                                     # (and it falls)
        self.steps(config.TIDE[3] + 0.2)
        self.assertEqual(b.tide, "low")
        self.assertFalse(any(w.tile_at(*p) is tiles.TIDE_SEA for p in b.sea))
        # Beaten: the sea drains, the quest is won.
        orig = dict(b.orig)
        b.take_damage(b.hp + 10, h, 0.0)
        self.steps(DT * 3)
        self.assertTrue(w.pangaea_land.draining)              # (it drains over a few steps,
        self.steps(len(orig) / config.DRAIN_PER_STEP / 60 + 0.1)   # the middle first)
        self.assertEqual(self.q.stage, "cleared")
        for p, t in orig.items():
            self.assertIs(w.tile_at(*p), t)
        self.assertFalse(any(e.alive for e in b.life))


class MovesTest(unittest.TestCase):
    def test_dive_it_sinks_its_spot_swells_under_you_and_it_bursts_up(self):
        b, a = first_life()
        h = a.hero
        hp = h.hp
        force(b, a, "dive")
        run(a, config.DIVE[0] + 0.1)
        self.assertTrue(b.submerged)
        self.assertFalse(b.hittable)
        self.assertIsNotNone(b.ripple)
        h.x += 3.0                                            # (it follows you a while)
        hx, hy = h.x, h.y
        run(a, 0.2)
        self.assertAlmostEqual(b.ripple[0], h.x, delta=0.01)
        while b.submerged:
            run(a, DT)
        self.assertLess(math.hypot(b.x - hx, b.y - hy), 1.0)  # (it came up under you)
        self.assertLess(hp - h.hp, config.DIVE[4] * 2)        # (the burst; the spray flies out)
        self.assertLess(h.hp, hp)
        spray = [p for p in a.projectiles if p.spec is config.PANGAEA_SHOTS["spray"]]
        self.assertEqual(len(spray), config.DIVE[5])
        self.assertTrue(all(math.hypot(p.x - b.x, p.y - b.y) >= config.DIVE[3] for p in spray))
        mine = [e.kind for e in b.echoes if (e.kind, round(e.t, 3)) and e.t > 2.0]
        self.assertEqual(sorted(mine), ["area", "shots"])

    def test_whirlpool_drags_you_round_and_in_and_its_eye_hurts(self):
        b, a = first_life()
        h = a.hero
        force(b, a, "whirlpool", DT)
        w = b.whirls[0]
        self.assertLess(math.hypot(w.x - h.x, w.y - h.y), 1.0)    # (on you)
        h.x, h.y = w.x + 5.0, w.y
        run(a, w.shown + 0.5)
        d = math.hypot(h.x - w.x, h.y - w.y)
        self.assertLess(d, 5.0)                               # (drawn in,
        self.assertGreater(abs(h.y - w.y), 0.5)               # and round)
        hp = h.hp
        h.x, h.y = w.x, w.y
        run(a, 0.1)
        self.assertLess(h.hp, hp)
        self.assertEqual(b.echoes[-1].kind, "whirl")

    def test_boiling_bubbles_burst_in_chains_through_where_you_are(self):
        b, a = first_life()
        h = a.hero
        force(b, a, "bubbles", DT)
        chains, per = config.BUBBLES[:2]
        self.assertEqual(len(b.bubbles), chains * per)
        near = min(b.bubbles, key=lambda q: math.hypot(q[0] - h.x, q[1] - h.y))
        self.assertLess(math.hypot(near[0] - h.x, near[1] - h.y), 1.2)
        times = sorted(q[2] for q in b.bubbles)
        self.assertGreater(times[-1] - times[0], 0.4)         # (one after another down a chain)
        hp = h.hp
        run(a, times[-1] + 0.1)
        self.assertLess(h.hp, hp)
        self.assertEqual(b.bubbles, [])

    def test_arm_lash_grabs_you_and_pulls_you_in_to_be_bitten(self):
        b, a = first_life(hero_at=(40.5, 40.5), y=30.5)
        h = a.hero
        hp = h.hp
        force(b, a, "lash", DT)
        self.assertEqual(len(b.lashes), config.ARM_LASH[0])
        caught, near = False, 99.0
        for _ in range(180):
            run(a, DT)
            caught = caught or any(m.grip is h for m in b.lashes)
            near = min(near, math.hypot(h.x - b.x, h.y - b.y))
        self.assertTrue(caught)
        self.assertLess(near, 7.0)                            # (pulled in)
        self.assertLess(h.hp, hp)

    def test_a_roll_pulls_you_free_of_an_arm(self):
        b, a = first_life()
        h = a.hero
        force(b, a, "lash", DT)
        for _ in range(120):
            run(a, DT)
            if any(m.grip is h for m in b.lashes):
                break
        m = next(m for m in b.lashes if m.grip is h)
        h.roll_t = 0.3
        run(a, DT)
        self.assertIsNone(m.grip)

    def test_tentacles_burst_up_round_you_and_sweep_through_where_you_are(self):
        b, a = first_life()
        h = a.hero
        b.hp = b.max_hp * 0.45
        run(a, DT)
        hp = h.hp
        force(b, a, "tentacles", DT)
        self.assertEqual(len(b.sweeps), config.TENTACLES[0])
        lo, hi = config.TENTACLES[2:4]
        for s in b.sweeps:
            self.assertLessEqual(math.hypot(s.bx - h.x, s.by - h.y), hi + 0.01)
        held = False
        for _ in range(150):
            run(a, DT)
            held = held or any(id(h) in s.held for s in b.sweeps)
        self.assertTrue(held)
        self.assertLess(h.hp, hp)

    def test_the_tidal_wave_carries_you_unless_you_roll_through_it(self):
        b, a = first_life()
        h = a.hero
        b.hp = b.max_hp * 0.2
        run(a, DT)
        force(b, a, "wave", DT)
        self.assertIsNotNone(b.wave_tell)
        hp, x0, y0 = h.hp, h.x, h.y
        a0 = b.wave_tell[2]
        run(a, config.TIDAL_WAVE[0] + config.TIDAL_WAVE[1] / config.TIDAL_WAVE[3] + 0.6)
        self.assertLess(h.hp, hp)
        moved = (h.x - x0) * math.cos(a0) + (h.y - y0) * math.sin(a0)
        self.assertGreater(moved, 3.0)                        # (carried along with it)
        # Rolling through its echo: no hit.
        w = Wave(h.x - math.cos(a0) * 2, h.y - math.sin(a0) * 2, a0, 6.0, 12.0, 30, 0.9)
        b.waves = [w]
        hp = h.hp
        for _ in range(20):
            h.roll_t = 0.3
            run(a, DT)
        self.assertEqual(h.hp, hp)


class LifeTest(unittest.TestCase):
    def test_life_crawls_out_of_the_sea_and_evolves_if_left_alone(self):
        b, a = first_life()
        recruits(b, a)
        b.life_t = DT
        run(a, DT * 2)
        n = config.LIFE_EVOLVE[1]
        self.assertEqual([e.kind_key for e in b.life], ["first_blob"] * n)
        lo, hi = config.LIFE_EVOLVE[2]
        for e in b.life:
            self.assertLessEqual(math.hypot(e.x - a.hero.x, e.y - a.hero.y), hi + 0.01)
        b.life_t = 999.0
        killed = b.life[1]
        killed.hp = 0.0                                       # (one killed young)
        run(a, config.LIFE_EVOLVE[4] + 0.1)
        self.assertEqual([e.kind_key for e in b.life], ["first_crawler"])
        old = [e for e in a.enemies if e.kind_key == "first_blob"]
        self.assertTrue(all(getattr(e, "left", False) for e in old if e is not killed))
        run(a, config.LIFE_EVOLVE[4] + 0.1)
        self.assertIn(b.life[0].kind_key, config.LIFE_BEASTS)
        self.assertIsNone(b.life[0].grow_t)                   # (a beast now: it stays one)

    def test_beaten_what_crawled_out_goes_back(self):
        b, a = first_life()
        recruits(b, a)
        b.life_t = DT
        run(a, DT * 2)
        b.hp = 0.0
        run(a, DT * 2)
        self.assertFalse(any(e.alive for e in b.life + a.enemies[1:] if e is not b))


class HusksTest(unittest.TestCase):
    def test_each_awake_husk_replays_its_ages_signature_and_it_echoes_once(self):
        b, a = first_life()
        b.hp = b.max_hp * 0.7
        run(a, DT)
        by = {h.age: h for h in b.husks}
        mam, liz, ins = by[0], by[1], by[2]
        for h in (mam, liz, ins):
            h.sig_cd = 999.0
        mam.sig_cd = DT
        run(a, DT * 2)
        self.assertTrue(b.husk_runs)
        run(a, config.ANCESTOR_STAMPEDE[0] + 0.1)
        self.assertTrue(mam.lanes)                            # (its lanes, shown)
        run(a, config.ANCESTOR_STAMPEDE[1] + 0.1)
        ghosts = [e for e in b.echoes if e.kind == "run"
                  and e.data["sprite"] in ("mammoth", "woolly_rhino")]
        self.assertTrue(ghosts)                               # (the herd, echoing)
        self.assertTrue(all(e.sprite == "ancestor_mammal" for e in ghosts))   # (the husk's ghost)
        liz.sig_cd = DT
        run(a, DT * 2 + config.ANCESTOR_ROAR[0])
        roar = [e for e in b.echoes if e.kind == "area" and (e.x, e.y) == (liz.x, liz.y)]
        self.assertTrue(roar)
        self.assertEqual(roar[0].sprite, "ancestor_lizard")   # (the ghost: the husk's age)
        ins.sig_cd = DT
        run(a, DT * 2)
        self.assertTrue(b.rivers)
        echoes = len(b.echoes)
        run(a, config.ECHO[0] + 0.5)                          # (they play: no echo of an echo)
        self.assertLess(len(b.echoes), echoes)
        self.assertTrue(any(r.echo for r in b.rivers))


class EchoTest(unittest.TestCase):
    def test_its_own_kinds_play_again_as_echoes_once(self):
        for move, kind, attr, after in (("whirlpool", "whirl", "whirls", DT),
                                        ("bubbles", "bubbles", "bubbles", DT),
                                        ("lash", "lashes", "lashes", DT),
                                        ("tentacles", "sweeps", "sweeps", DT),
                                        ("wave", "wave", "waves", config.TIDAL_WAVE[0] + 0.1)):
            b, a = first_life()
            force(b, a, move, after)
            mine = [e for e in b.echoes if e.kind == kind]
            self.assertEqual(len(mine), 1, move)
            mine[0].t = DT / 2                               # (it plays now)
            run(a, DT)
            flags = [(o[3] if isinstance(o, list) else o.echo) for o in getattr(b, attr)]
            self.assertIn(True, flags, move)
            self.assertFalse(any(e.kind == kind for e in b.echoes), move)   # (no echo of it)
        for cls in (Lash, Sweep, Whirl, Wave):
            self.assertIn("params", vars(cls))


if __name__ == "__main__":
    unittest.main()


# --- The Ancestor's relics (user's picks, 2026-11-25) --------------------------------------

from ascii_adventurers.render.gear_looks import HEAD_LOOKS            # noqa: E402
from ascii_adventurers.systems import relics                         # noqa: E402
from ascii_adventurers.tests.test_m28_5 import BASE, _Relic, mover   # noqa: E402


class RelicsTest(_Relic):
    """One per age and one for the first life: Spirit Herd, Tyrant Skull,
    Swarm Ring, Echo Conch."""

    def test_four_relics_in_four_slots(self):
        keys = config.BOSS_UNIQUES["ancestor"]
        self.assertEqual(set(keys), {"spirit_herd", "tyrant_skull", "swarm_ring", "echo_conch"})
        self.assertEqual(sorted(config.GEAR[k].slot for k in keys),
                         ["head", "off", "ring", "trinket"])
        for k in keys:
            self.assertEqual(config.CARDS[k].rarity, "legendary")
            self.assertEqual(config.CARDS[k].unlock, "U:ancestor")
            self.assertLessEqual(len(config.GEAR[k].name), 16)
        self.assertNotIn("ancestor_first_life", config.BOSS_UNIQUES)   # (it's the Ancestor)
        self.assertIn("tyrant_skull", HEAD_LOOKS)

    def test_the_spirit_herd_charges_through_them_and_shoves_them_aside(self):
        s, h = self.setup("spirit_herd")
        on = mover(26.5, 20.8)
        off = mover(26.5, 26.5)
        self.place(on, off)
        h.herd_t = 0.0
        self.go(DT * 2)
        self.assertEqual(len(h.herd), 1)
        self.assertLess(h.herd[0][0], h.x)                    # (from behind you)
        self.go(1.5)
        self.assertLess(on.hp, BASE)
        self.assertGreater(on.y, 21.5)                        # (shoved aside, its side)
        self.assertEqual(off.hp, BASE)
        self.assertEqual(h.herd, [])                          # (it ran its course)
        self.assertGreater(h.herd_t, config.U_HERD[0] - 2.0)

    def test_the_herd_waits_for_an_enemy_in_reach(self):
        s, h = self.setup("spirit_herd")
        self.place(mover(40.5, 20.5))
        h.herd_t = 0.0
        self.go(DT * 2)
        self.assertEqual(h.herd, [])
        self.assertGreater(h.herd_t, 0.5)

    def test_the_tyrant_skull_roars_ahead_and_freezes_them_in_fear(self):
        s, h = self.setup("tyrant_skull")
        ahead = mover(25.5, 21.5)
        behind = mover(16.5, 20.5)
        boss = mover(27.5, 19.5)
        boss.boss = True
        self.place(ahead, behind, boss)
        h.skull_t = 0.0
        self.go(DT * 2)
        self.assertLess(ahead.hp, BASE)
        self.assertGreater(ahead.status.dazed, 1.0)
        self.assertEqual(behind.hp, BASE)
        self.assertTrue(behind.status is None or behind.status.dazed == 0.0)
        self.assertGreater(boss.status.bound, 0.0)            # (a boss is held, briefly)
        self.assertLessEqual(boss.status.bound, config.U_SKULL[5])
        self.assertIn("skull_roar", [e.kind for e in s.effects])

    def test_the_swarm_ring_pours_a_stinging_river_along_your_aim(self):
        s, h = self.setup("swarm_ring")
        on = mover(28.5, 20.5)
        off = mover(28.5, 25.5)
        self.place(on, off)
        h.swarm_t = 0.0
        self.go(DT * 2)                                       # (it pours out, then stings)
        self.assertEqual(len(h.swarms), 1)
        one = BASE - on.hp
        self.assertGreater(one, 0)
        self.go(1.1)                                          # (a sting every 0.5 s)
        self.assertAlmostEqual(BASE - on.hp, one * 3, delta=one * 0.5)
        self.assertEqual(off.hp, BASE)
        self.go(config.U_SWARM[4])
        self.assertEqual(h.swarms, [])

    def test_the_echo_conch_fires_your_attack_again_from_where_you_stood(self):
        s, h = self.setup("echo_conch")
        s._attack(s.me)
        mine = [q for q in s.projectiles if q.owner is h]
        self.assertTrue(mine)
        self.assertEqual(len(h.conch), 1)
        dmg = mine[0].damage
        h.x = 10.5                                            # (you've moved on)
        self.go(config.U_CONCH[0] + DT)
        echoes = [q for q in s.projectiles if q.conch]
        self.assertEqual(len(echoes), len(mine))
        self.assertAlmostEqual(echoes[0].damage, dmg * 0.4)
        self.assertGreater(echoes[0].x, 15.0)                 # (from where you stood)
        self.assertEqual(h.conch, [])
        self.go(config.U_CONCH[0] + 0.1)
        self.assertEqual(h.conch, [])                         # (an echo never echoes)

    def test_a_pulse_echoes_too(self):
        s, h = self.setup("echo_conch", hero="bard")
        d = mover(24.5, 20.5)
        self.place(d)
        s._attack(s.me)
        hit = BASE - d.hp
        self.assertGreater(hit, 0)
        h.x = 50.5
        self.go(config.U_CONCH[0] + DT)
        self.assertAlmostEqual(BASE - d.hp, hit * 1.4, delta=hit * 0.15)

    def test_their_things_draw(self):
        s, h = self.setup("spirit_herd")
        self.place(mover(26.5, 20.5))
        h.herd_t = 0.0
        self.go(0.3)
        h.swarms = [[h.x, h.y, 0.0, 2.0, {}]]
        s.effects.append(relics.Effect("skull_roar", h.x, h.y, angle=0.0, size=8.0, value=100))
        s.me.camera.center_on(h.x, h.y)
        s.me.minimap = None
        s.draw(s.manager.text)
        self.assertTrue(h.herd)
