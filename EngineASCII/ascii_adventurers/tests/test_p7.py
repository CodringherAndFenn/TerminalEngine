"""P7 (playtest pass, 2026-10-10): the plains' new enemies -- simple
chasers (field rats, farmhands, geese; mole rats and crows), hounds, hawk,
molehill, bull, bandit slinger, lancer, shieldbearer, priest, straw golem,
scarecrow, war drummer."""

import math
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.ai import make_enemy
from ascii_adventurers.ai.brain import AIContext
from ascii_adventurers.ai.plains import drum_haste, tick_drum
from ascii_adventurers.render.characters import ART
from ascii_adventurers.render import plains_art  # noqa: F401
from ascii_adventurers.systems.spawner import PACK_ID
from ascii_adventurers.tests.test_m16 import game
from ascii_adventurers.tests.test_m17 import step, world
from ascii_adventurers.tests.test_weapons import Dummy, hero, open_map

NEW = ("field_rat", "farmhand", "goose", "hound", "hawk", "molehill", "bull", "slinger",
       "lancer", "shieldbearer", "priest", "straw_golem", "scarecrow", "drummer")


def enemy(key, x, y, seed=1):
    e = make_enemy(key, x, y, random.Random(seed))
    e.alert = True
    return e


class Arena:
    """A hero (or several) and some enemies on open ground, stepped like the game."""

    def __init__(self, *enemies, w=60, h=30, walls=(), hero_at=(30.5, 15.5)):
        self.world = open_map(w=w, h=h, walls=walls)
        self.hero = hero("wizard", *hero_at)
        self.enemies = list(enemies)
        self.effects, self.projectiles, self.zones = [], [], []

    def actors(self):
        return [self.hero] + [e for e in self.enemies if e.alive]

    def run(self, seconds, dt=1 / 60):
        for _ in range(round(seconds / dt)):
            ctx = AIContext(self.world, [self.hero], self.actors(), self.projectiles,
                            self.effects, zones=self.zones)
            for e in list(self.enemies):
                if e.alive:
                    tick_drum(e, dt)
                    e.think(ctx, dt * (1 + drum_haste(e)))
            for key, x, y in ctx.spawned:
                self.enemies.append(enemy(key, x, y, len(self.enemies)))
            for e in self.enemies:
                if not e.alive and not getattr(e, "_gone", False):
                    e._gone = True
                    hook = getattr(e, "on_death", None)
                    if hook:
                        hook(ctx)
            from ascii_adventurers.systems import combat
            combat.update_projectiles(self.projectiles, self.world, self.effects, dt,
                                      self.actors(), self.zones)


class CatalogTest(unittest.TestCase):
    def test_every_new_enemy_lives_in_the_plains_and_has_its_page(self):
        for key in NEW:
            spec = config.ENEMIES[key]
            self.assertIn("plains", spec.biomes, key)
            self.assertIn(key, config.BESTIARY, key)
            sprite = spec.sprite or config.BODIES[spec.body].sprite
            self.assertIn(sprite, ART, key)
            self.assertEqual(len(ART[sprite]), 18)
            self.assertTrue(all(len(r) == 14 for r in ART[sprite]), key)
        for key in ("mole_rat", "crow"):                # (sent out, never spawned)
            self.assertEqual(config.ENEMIES[key].biomes, ())
            self.assertIn(key, config.BESTIARY)

    def test_the_elites(self):
        self.assertEqual({k for k, s in config.ENEMIES.items() if s.elite},
                         {"bull", "shieldbearer"})

    def test_the_plains_now_have_nineteen_kinds(self):
        plains = [k for k, s in config.ENEMIES.items() if "plains" in s.biomes]
        self.assertEqual(len(plains), 5 + len(NEW))


class PackTest(unittest.TestCase):
    def test_rats_and_geese_and_hounds_come_in_packs(self):
        w = world(31)
        from ascii_adventurers.systems.spawner import Spawner
        sp = Spawner(w, 31)
        packs = {}
        r = w.layout.plains_radius * 0.8
        for cx in range(-int(r / 32), int(r / 32)):
            for cy in range(-int(r / 32), int(r / 32)):
                for sid, key, x, y in sp.roster(cx, cy):
                    if key in ("field_rat", "goose", "hound"):
                        packs.setdefault((cx, cy, sid[2] % PACK_ID // 16 if sid[2] >= PACK_ID
                                          else sid[2], key), []).append((x, y))
        self.assertTrue(packs)
        for (cx, cy, k, key), members in packs.items():
            lo, hi = config.ENEMIES[key].group
            self.assertLessEqual(len(members), hi, key)
            x0, y0 = members[0]
            for x, y in members[1:]:
                self.assertLessEqual(math.hypot(x - x0, y - y0), 2.6, key)


class ChaserTest(unittest.TestCase):
    def test_straight_at_you_and_bites(self):
        for key in ("field_rat", "farmhand", "goose"):
            e = enemy(key, 24.5, 15.5)
            a = Arena(e)
            a.run(4.0)
            self.assertLess(a.hero.hp, a.hero.max_hp, key)

    def test_a_crow_flies_over_walls_and_leaves(self):
        walls = [(27, y) for y in range(30)]
        c = enemy("crow", 24.5, 15.5)
        a = Arena(c, walls=walls)
        a.run(3.0)
        self.assertLess(a.hero.hp, a.hero.max_hp)                # (over the wall)
        a.run(config.CROW_LIFE)
        self.assertFalse(c.alive)


class BeastTest(unittest.TestCase):
    def test_hounds_take_turns(self):
        hounds = [enemy("hound", 30.5 + dx, 10.5, i) for i, dx in enumerate((-2, 0, 2))]
        a = Arena(*hounds)
        most = 0
        for _ in range(240):
            a.run(1 / 60)
            most = max(most, sum(1 for h in hounds if h.dash > 0))
        self.assertEqual(most, 1)
        self.assertLess(a.hero.hp, a.hero.max_hp)

    def test_hawk_lines_up_dives_and_hits_once(self):
        h = enemy("hawk", 22.5, 15.5)
        h.timer = 0.1
        a = Arena(h)
        seen = set()
        for _ in range(400):
            a.run(1 / 60)
            seen.add(h.state)
        self.assertTrue({"circle", "mark", "dive", "climb"} <= seen)
        self.assertLess(a.hero.hp, a.hero.max_hp)

    def test_molehill_sends_rats_up_to_its_limit(self):
        m = enemy("molehill", 26.5, 15.5)
        a = Arena(m)
        a.hero.invulnerable = True
        a.run(30.0)
        rats = [e for e in a.enemies if getattr(e, "kind_key", "") == "mole_rat"]
        self.assertGreater(len(rats), 0)
        self.assertLessEqual(len([r for r in rats if r.alive]), config.MOLEHILL[1])
        self.assertEqual((m.x, m.y), (26.5, 15.5))              # never moves

    def test_bull_tramples_what_breaks_and_comes_again(self):
        from ascii_adventurers.world import tiles
        b = enemy("bull", 15.5, 15.5)
        a = Arena(b, w=80)
        for y in (14, 16):                           # pines either side of its line of sight,
            a.world.set_tile(22, y, tiles.PINE)       # in the way of its wide body
        a.hero.invulnerable = True
        passes, states = set(), set()
        for _ in range(900):
            a.run(1 / 60)
            states.add(b.state)
            if b.state == "charge":
                passes.add(b.passes)
        self.assertGreaterEqual(len(passes), 2)                  # it came again
        self.assertNotIn("dazed", states)                        # pines don't stop it...
        self.assertTrue(any(a.world.tile_at(22, y) is not tiles.PINE for y in (14, 16)))

    def test_bull_is_dazed_by_what_doesnt_break(self):
        from ascii_adventurers.world import tiles
        b = enemy("bull", 33.5, 15.5)
        a = Arena(b, w=60, hero_at=(36.5, 15.5))
        for x in (40, 41):                            # rock doesn't break (a wall would)
            for y in range(30):
                a.world.set_tile(x, y, tiles.ROCK)
        a.hero.invulnerable = True
        states = set()
        for _ in range(400):
            a.run(1 / 60)
            states.add(b.state)
        self.assertIn("dazed", states)


class FolkTest(unittest.TestCase):
    def test_slinger_slings_three(self):
        s = enemy("slinger", 22.5, 15.5)
        a = Arena(s)
        shots = []
        for _ in range(180):
            a.run(1 / 60)
            shots += [p for p in a.projectiles if p.spec.look == "pebble" and p not in shots]
        self.assertGreaterEqual(len(shots), 3)                   # a burst of three

    def test_lancer_runs_through_you(self):
        l = enemy("lancer", 18.5, 15.5)
        a = Arena(l, w=80)
        states = set()
        for _ in range(600):
            a.run(1 / 60)
            states.add(l.state)
        self.assertIn("joust", states)
        self.assertLess(a.hero.hp, a.hero.max_hp)

    def test_shield_takes_every_hit_from_the_front(self):
        from ascii_adventurers.tests.test_weapons import hero as mk
        sb = enemy("shieldbearer", 20.5, 15.5)
        sb.aim_angle = 0.0                                   # facing +x
        front = sb.take_damage(50, None, math.pi)            # a shot flying -x hits its front
        self.assertEqual(front, 0.0)
        back = sb.take_damage(50, None, 0.0)                 # one flying +x hits its back
        self.assertGreater(back, 0.0)

    def test_after_a_bash_it_is_open(self):
        sb = enemy("shieldbearer", 29.0, 15.5)
        a = Arena(sb)
        hp0 = a.hero.hp
        x0 = a.hero.x
        for _ in range(300):
            a.run(1 / 60)
            if sb.open > 0:
                break
        self.assertGreater(sb.open, 0)
        self.assertLess(a.hero.hp, hp0)
        self.assertGreater(abs(a.hero.x - x0), 0.5)          # shoved
        self.assertGreater(sb.take_damage(50, None, math.pi), 0)   # front open

    def test_priest_heals_the_most_hurt(self):
        p = enemy("priest", 20.5, 15.5)
        hurt = enemy("farmhand", 22.5, 15.5)
        hurt.hp = 10
        a = Arena(p, hurt, hero_at=(50.5, 15.5))
        a.run(config.PRIEST[0] + 0.2)
        self.assertGreater(hurt.hp, 10)
        self.assertTrue(any(e.kind == "heal_beam" for e in a.effects))


class OddOnesTest(unittest.TestCase):
    def test_straw_golem_dies_in_fire(self):
        g = enemy("straw_golem", 20.5, 15.5)
        a = Arena(g)
        g.hp = 0
        a.run(1 / 60)
        self.assertEqual(len(a.zones), config.GOLEM_FIRE[0])
        self.assertTrue(all(z.inflicts == "burn" for z in a.zones))

    def test_scarecrow_lets_loose_crows(self):
        sc = enemy("scarecrow", 22.5, 15.5)
        a = Arena(sc)
        a.hero.invulnerable = True
        a.run(config.SCARECROW[0] + 1.0)
        crows = [e for e in a.enemies if getattr(e, "kind_key", "") == "crow"]
        self.assertGreaterEqual(len(crows), 3)
        self.assertLessEqual(len(crows), config.SCARECROW[3])

    def test_drummer_speeds_and_strengthens_its_ring(self):
        d = enemy("drummer", 10.5, 15.5)
        ally = enemy("farmhand", 12.5, 15.5)
        base = ally.damage_mult
        a = Arena(d, ally, hero_at=(55.5, 15.5))
        a.run(0.2)
        self.assertGreater(drum_haste(ally), 0)
        self.assertAlmostEqual(ally.damage_mult, base * (1 + config.DRUM_DAMAGE))
        d.hp = 0                                             # the drum stops
        a.run(1.0)
        self.assertEqual(drum_haste(ally), 0)
        self.assertAlmostEqual(ally.damage_mult, base)       # given back exactly


class GameTest(unittest.TestCase):
    def test_all_of_them_in_a_real_game(self):
        m, s = game("wizard")
        h = s.hero
        h.invulnerable = True
        for i, k in enumerate(NEW):
            a = i * math.tau / len(NEW)
            e = s.spawner.wake(k, h.x + math.cos(a) * 9, h.y + math.sin(a) * 6, None,
                               random.Random(i))
            e.alert = True
            s.enemies.append(e)
        for f in range(240):
            step(s)
            if f % 60 == 0:
                s.draw(m.text)
        self.assertTrue(any(getattr(e, "kind_key", "") in NEW for e in s.enemies))


if __name__ == "__main__":
    unittest.main()
