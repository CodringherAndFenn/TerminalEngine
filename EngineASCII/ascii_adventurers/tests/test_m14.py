"""M14: the stat layer, damage buckets, statuses, hero cards, spells, XP gems."""

import math
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from ascii_adventurers import config
from ascii_adventurers.entities.gems import Gem, drop, update_gems
from ascii_adventurers.entities.projectile import Projectile
from ascii_adventurers.players import cards
from ascii_adventurers.systems import combat
from ascii_adventurers.systems.spells import SpellState, update_spells
from ascii_adventurers.systems.statuses import inflict, update_statuses
from ascii_adventurers.tests.test_weapons import Dummy, hero, open_map


def carded(name, *taken, x=10.5, y=10.5, aim=0.0):
    """A hero with these (card, rarity) taken, and no crits unless asked."""
    h = hero(name, x, y, aim)
    lo = cards.build_loadout(name, list(taken))
    h.spec, h.weapon.spec, h.stats = lo.body, lo.weapon, lo.stats
    h.max_hp = h.hp = lo.body.max_hp
    h.stats.crit_chance = 0.0
    return h


def run_statuses(actors, seconds, effects=None):
    effects = [] if effects is None else effects
    for _ in range(round(seconds * 60)):
        update_statuses(actors, 1 / 60, effects)
    return effects


class StrikeTest(unittest.TestCase):
    def test_plain_source_is_plain_damage(self):
        d = Dummy(12, 10.5)
        self.assertEqual(combat.strike(d, 20, None, 0.0, []), 20)
        self.assertEqual(d.hp, 480)

    def test_buckets(self):
        h = carded("dwarf", ("sharpened", "common"), ("sharpened", "rare"), ("glass_cannon", "rare"))
        h.stats.tag_damage["physical"] = 0.5
        d = Dummy(12, 10.5)
        dealt = combat.strike(d, 100, h, 0.0, [], tags=("physical",), extra=0.1, mult=2.0)
        # (1 + A) x (1 + T) x M: A = 0.10 + 0.22 + 0.10 extra, T = 0.5, M = 1.4 x 2.
        self.assertAlmostEqual(dealt, 100 * 1.42 * 1.5 * 1.4 * 2.0)

    def test_crits(self):
        h = carded("wizard", ("brutal", "common"))
        h.stats.crit_chance = 1.0
        effects = []
        d = Dummy(12, 10.5)
        self.assertAlmostEqual(combat.strike(d, 10, h, 0.0, effects), 10 * (1.5 + 0.15))
        self.assertEqual(effects[-1].tone, "crit")

    def test_crits_replay_with_the_same_seed(self):
        def rolls():
            h = carded("wizard")
            h.stats.crit_chance = 0.5
            h.rng.seed(42)
            return [combat.strike(Dummy(12, 10.5), 10, h, 0.0, []) for _ in range(30)]
        a = rolls()
        self.assertEqual(a, rolls())
        self.assertEqual(set(a), {10, 15})

    def test_steady_aim_and_point_blank(self):
        h = carded("huntress", ("steady_aim", "uncommon"))
        h.rng.seed(1)
        still = sum(combat.strike(Dummy(12, 10.5), 10, h, 0.0, []) > 10 for _ in range(400))
        h.vx = 5.0                                       # walking: no bonus
        moving = sum(combat.strike(Dummy(12, 10.5), 10, h, 0.0, []) > 10 for _ in range(400))
        self.assertGreater(still, 60)
        self.assertEqual(moving, 0)
        p = carded("princess", ("point_blank", "uncommon"))
        self.assertAlmostEqual(combat.strike(Dummy(13, 10.5), 10, p, 0.0, []), 14)
        self.assertAlmostEqual(combat.strike(Dummy(20, 10.5), 10, p, 0.0, []), 10)

    def test_hunters_mark(self):
        h = carded("huntress", ("hunters_mark", "rare"))
        a, b = Dummy(12, 10.5), Dummy(13, 10.5)
        h.marked = a
        self.assertEqual(combat.strike(a, 10, h, 0.0, []), 20)
        self.assertEqual(combat.strike(b, 10, h, 0.0, []), 10)

    def test_on_hit_statuses(self):
        h = carded("wizard", ("kindling", "uncommon"), ("venom", "uncommon"))
        h.stats.status_chance = 1.0
        d = Dummy(12, 10.5)
        combat.strike(d, 1, h, 0.0, [])
        self.assertEqual((d.status.stacks("burn"), d.status.stacks("poison")), (1, 1))
        h.stats.status_chance = 0.0
        d2 = Dummy(12, 10.5)
        combat.strike(d2, 1, h, 0.0, [])
        self.assertIsNone(d2.status)


class DefenseTest(unittest.TestCase):
    def test_armor(self):
        h = carded("bard")
        h.stats.armor = 40
        self.assertAlmostEqual(h.take_damage(20, None, None), 10)
        h.stats.armor = -40
        self.assertAlmostEqual(h.take_damage(20, None, None), 30)

    def test_evasion(self):
        h = carded("bard", *[("nimble", "legendary")] * 10)
        h.hp = 1e9
        h.rng.seed(3)
        evaded = sum(h.take_damage(1, None, None) == 0 for _ in range(500))
        self.assertAlmostEqual(evaded / 500, config.MAX_EVASION, delta=0.07)
        self.assertEqual(h.evaded, evaded)


class StatusTest(unittest.TestCase):
    def test_burn_ticks_stacks_and_expires(self):
        h = carded("wizard")
        d = Dummy(12, 10.5)
        for _ in range(7):
            inflict(d, "burn", h)
        self.assertEqual(d.status.stacks("burn"), 5)           # capped
        effects = run_statuses([d], 1.0)
        self.assertAlmostEqual(500 - d.hp, 5 * 4.0, delta=0.5)
        self.assertTrue(all(e.tone == "burn" for e in effects))
        self.assertIs(d.last_hit_by, h)                        # kill credit
        run_statuses([d], 3.0)
        self.assertIsNone(d.status)                            # burnt out (3 s)

    def test_status_power(self):
        h = carded("wizard", ("potency", "legendary"))
        d = Dummy(12, 10.5)
        inflict(d, "poison", h)
        run_statuses([d], 1.0)
        self.assertAlmostEqual(500 - d.hp, 2.0 * 1.4, delta=0.1)

    def test_lingering_lengthens_statuses(self):
        h = carded("wizard", ("lingering", "legendary"))
        d = Dummy(12, 10.5)
        inflict(d, "shock", h)
        run_statuses([d], 2.5)
        self.assertTrue(d.status.has("shock"))                 # 2 s x 1.4

    def test_shock_vulnerability(self):
        d = Dummy(12, 10.5)
        inflict(d, "shock", None)
        self.assertAlmostEqual(d.take_damage(100, None, None), 115)

    def test_chill_slows_then_freezes(self):
        d = Dummy(12, 10.5)
        inflict(d, "chill", None, 2)
        self.assertAlmostEqual(d.status.time_scale, 0.8)
        inflict(d, "chill", None, 3)
        self.assertEqual(d.status.time_scale, 0.0)             # frozen
        self.assertFalse(d.status.has("chill"))                # the chill is used up
        run_statuses([d], config.FREEZE_TIME + 0.05)
        self.assertIsNone(d.status)

    def test_bosses_take_half_and_never_freeze(self):
        d = Dummy(12, 10.5)
        d.boss = True
        inflict(d, "chill", None, 9)
        self.assertGreater(d.status.time_scale, 0)
        inflict(d, "burn", None, 1)
        run_statuses([d], 1.0)
        self.assertAlmostEqual(500 - d.hp, 2.0, delta=0.3)

    def test_frozen_enemies_dont_act_in_game(self):
        from ascii_adventurers.ai import make_enemy
        from ascii_adventurers.tests.test_players import make_manager, start_game
        s = start_game(make_manager(), seed=31, hero="wizard")
        s.mouse.left_held = lambda: False
        e = make_enemy("goblin_archer", s.hero.x + 5, s.hero.y, random.Random(1))
        s.enemies.append(e)
        calls = []
        e.think = lambda ctx, dt: calls.append(dt)
        inflict(e, "chill", None, 2)
        s.update(1 / 60)
        self.assertAlmostEqual(calls[-1], 0.8 / 60)            # slowed clock
        inflict(e, "chill", None, 5)
        n = len(calls)
        for _ in range(10):
            s.update(1 / 60)
        self.assertEqual(len(calls), n)                        # frozen
        pygame.mouse.set_visible(True)


class HeroCardTest(unittest.TestCase):
    def fly(self, shots, actors, world=None, steps=60):
        world = world or open_map()
        effects = []
        for _ in range(steps):
            combat.update_projectiles(shots, world, effects, 1 / 60, actors)
        return effects

    def test_supercell_shocks_and_jumps_prefer_shocked(self):
        from ascii_adventurers.tests.test_weapons import shock
        h = shock(carded("wizard", ("supercell", "uncommon")))
        world = open_map()
        first, near, far = Dummy(14, 10.5), Dummy(14, 12.0), Dummy(14, 13.5)
        inflict(far, "shock", None)
        shots = []
        combat.fire(h, world, shots, [])
        self.fly(shots, [h, first, near, far], world)
        self.assertTrue(first.status.has("shock"))
        # The first jump went to the shocked one, though it's farther.
        jumped = 20 * config.WEAPONS["shock_bolt"].shell.chain_falloff
        self.assertAlmostEqual(500 - far.hp, jumped * 1.25 * 1.15, delta=0.01)

    def test_spectrum(self):
        h = carded("princess", ("spectrum", "rare"))
        world = open_map()
        h.rng.random = lambda: 0.0                             # every color lands its status
        d = Dummy(13, 10.5, hp=5000)
        d.hit_radius = 2.0                                     # catches the whole fan
        shots = []
        combat.fire(h, world, shots, [])
        self.fly(shots, [h, d], world)
        self.assertEqual(set(d.status.active) - {"chill"}, {"burn", "shock", "poison"})
        self.assertGreater(d.status.frozen + d.status.stacks("chill"), 0)

    def test_broadhead(self):
        h = carded("huntress", ("broadhead", "uncommon"))
        a, b = Dummy(13, 10.5), Dummy(15, 10.5)
        shots = []
        combat.fire(h, open_map(), shots, [])
        self.fly(shots, [h, a, b])
        self.assertAlmostEqual(500 - a.hp, 16)
        self.assertAlmostEqual(500 - b.hp, 16 * 1.15)

    def test_dissonance_pushes_and_chills(self):
        from ascii_adventurers.ai import make_enemy
        h = carded("bard", ("dissonance", "uncommon"))
        e = make_enemy("warrior", 14, 10.5, random.Random(1))
        combat.pulse(h, open_map(), [h, e], [])
        self.assertAlmostEqual(e.x, 14 + config.DISSONANCE_PUSH, delta=0.01)
        self.assertEqual(e.status.stacks("chill"), 1)

    def test_hunters_mark_picks_the_toughest_in_view(self):
        from ascii_adventurers.ai import make_enemy
        from ascii_adventurers.tests.test_players import make_manager, start_game
        s = start_game(make_manager(), seed=31, hero="huntress")
        s.mouse.left_held = lambda: False
        s.me.progress.take("hunters_mark", "rare")
        s._apply_loadout(s.me)
        small = make_enemy("goblin_archer", s.hero.x + 3, s.hero.y, random.Random(1))
        big = make_enemy("ogre", s.hero.x + 8, s.hero.y, random.Random(2))
        s.enemies += [small, big]
        s.update(1 / 60)
        self.assertIs(s.hero.marked, big)
        s.draw(s.manager.text)
        pygame.mouse.set_visible(True)


class SpellTest(unittest.TestCase):
    def test_levels(self):
        s = SpellState("daggers", 1)
        self.assertEqual(s.params["count"], 2)
        s.set_level(5)
        self.assertEqual(s.params["count"], 4)
        self.assertAlmostEqual(s.params["damage"], 12 * 1.3)

    def test_daggers_hit_and_rehit(self):
        h = carded("dwarf")
        s = SpellState("daggers", 1)
        d = Dummy(10.5 + 2.2, 10.5)                            # on the orbit
        spells, world, effects = {"daggers": s}, open_map(), []
        hits = []
        for _ in range(60):
            hp = d.hp
            update_spells(h, spells, world, [h, d], effects, 1 / 60)
            if d.hp < hp:
                hits.append(round(s.clock, 3))
        self.assertTrue(hits)
        self.assertTrue(all(b - a >= 0.49 for a, b in zip(hits, hits[1:])))
        self.assertEqual(h.hp, h.max_hp)                       # never the hero

    def test_ember_aura_burns_what_is_near(self):
        h = carded("bard")
        s = SpellState("ember_aura", 1)
        near, far = Dummy(12, 10.5), Dummy(16, 10.5)
        for _ in range(60):
            update_spells(h, {"a": s}, open_map(), [h, near, far], [], 1 / 60)
        self.assertGreaterEqual(near.status.stacks("burn"), 2)
        self.assertIsNone(far.status)

    def test_area_grows_the_aura(self):
        h = carded("bard", *[("broad_strokes", "legendary")] * 2)
        s = SpellState("ember_aura", 1)
        d = Dummy(14, 10.5)
        for _ in range(60):
            update_spells(h, {"a": s}, open_map(), [h, d], [], 1 / 60)
        self.assertIsNotNone(d.status)

    def test_frost_nova_chills_and_walls_block_it(self):
        h = carded("wizard")
        s = SpellState("frost_nova", 1)
        world = open_map(walls=[(12, 13)])
        seen, hidden = Dummy(13, 10.5), Dummy(12.5, 14.5)
        effects = []
        for _ in range(round(2.1 * 60)):                       # the first nova comes at half time
            update_spells(h, {"n": s}, world, [h, seen, hidden], effects, 1 / 60)
        self.assertEqual(seen.status.stacks("chill"), 2)
        self.assertEqual(500 - seen.hp, 8)
        self.assertIsNone(hidden.status)
        self.assertTrue(any(e.kind == "nova" for e in effects))

    def test_spells_in_game(self):
        from ascii_adventurers.tests.test_players import make_manager, start_game
        s = start_game(make_manager(), seed=31, hero="bard")
        s.mouse.left_held = lambda: False
        for key in ("daggers", "ember_aura", "frost_nova", "daggers"):
            s.me.progress.take(key, "uncommon")
        s._apply_loadout(s.me)
        self.assertEqual({k: v.level for k, v in s.me.spells.items()},
                         {"daggers": 2, "ember_aura": 1, "frost_nova": 1})
        for _ in range(120):
            s.update(1 / 60)
        s.draw(s.manager.text)
        pygame.mouse.set_visible(True)


class GemTest(unittest.TestCase):
    class P:
        def __init__(self, h):
            self.hero, self.alive = h, True

    def test_pull_and_collect(self):
        h = carded("wizard", ("scholar", "legendary"))
        p = self.P(h)
        gems = []
        drop(gems, 11.5, 10.5, 10)                             # 1 tile away: in reach
        drop(gems, 14.5, 10.5, 10)                             # out of reach
        got = []
        for _ in range(60):
            got += update_gems(gems, [p], 1 / 60)
        self.assertEqual(len(got), 1)
        self.assertAlmostEqual(got[0][1], 13)                  # +30% XP
        self.assertEqual(len(gems), 1)

    def test_magnet(self):
        h = carded("wizard", ("magnet", "legendary"), ("magnet", "legendary"))
        p = self.P(h)
        gems = []
        drop(gems, 14.0, 10.5, 5)                              # 3.5 tiles: 1.5 x 2.6 reaches
        got = []
        for _ in range(60):
            got += update_gems(gems, [p], 1 / 60)
        self.assertEqual(len(got), 1)

    def test_cap_merges_and_lifetime(self):
        gems = []
        for i in range(config.GEM_MAX + 5):
            drop(gems, i, 0, 1)
        self.assertEqual(len(gems), config.GEM_MAX)
        self.assertEqual(sum(g.value for g in gems), config.GEM_MAX + 5)   # no XP lost
        update_gems(gems, [], config.GEM_LIFETIME + 1)
        self.assertEqual(gems, [])

    def test_tiers(self):
        self.assertEqual([Gem(0, 0, v).tier for v in (5, 12, 40)], [0, 1, 2])


if __name__ == "__main__":
    unittest.main()
