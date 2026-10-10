"""M16: catalog rev 2 (101 cards), Guild Hall rev 2, archivist shelves, pacts."""

import math
import os
import random
import unittest
from collections import Counter

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from ascii_adventurers import config
from ascii_adventurers.meta.guild import Guild
from ascii_adventurers.players import cards
from ascii_adventurers.players.stats import HeroStats
from ascii_adventurers.systems import combat, statuses
from ascii_adventurers.systems.spells import SpellState, update_spells
from ascii_adventurers.systems.statuses import inflict
from ascii_adventurers.systems.zones import update_zones
from ascii_adventurers.tests.test_m14 import carded, run_statuses
from ascii_adventurers.tests.test_weapons import Dummy, open_map


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, unicode="", mod=0)


def fly(shots, actors, world=None, steps=90, zones=None):
    world = world or open_map()
    effects = []
    for _ in range(steps):
        combat.update_projectiles(shots, world, effects, 1 / 60, actors, zones)
    return effects


def game(hero="wizard", guild=None, seed=31):
    from ascii_adventurers.tests.test_players import make_manager, start_game
    m = make_manager()
    if guild is not None:
        m.app.guild = guild
    s = start_game(m, seed=seed, hero=hero)
    s.mouse.left_held = lambda: False
    return m, s


def take(s, *taken):
    for k, r in taken:
        s.me.progress.take(k, r)
    s._apply_loadout(s.me)


class StatusChanceTest(unittest.TestCase):
    def test_each_status_rolls_its_base_chance_plus_affliction(self):
        h = carded("wizard", ("kindling", "uncommon"))
        h.rng.seed(5)
        burned = sum(1 for _ in range(1000)
                     if (d := Dummy(12, 10.5)) and combat.strike(d, 1, h, 0.0, []) is not None
                     and d.status is not None)
        self.assertAlmostEqual(burned / 1000, config.STATUS_BASE_CHANCE, delta=0.03)
        h = carded("wizard", ("kindling", "uncommon"), ("affliction", "legendary"))
        h.rng.seed(5)
        burned = 0
        for _ in range(1000):
            d = Dummy(12, 10.5)
            combat.strike(d, 1, h, 0.0, [])
            burned += d.status is not None
        self.assertAlmostEqual(burned / 1000, config.STATUS_BASE_CHANCE + 0.20, delta=0.04)


class HeroCardRev2Test(unittest.TestCase):
    def test_ricochet_bounces_on(self):
        h = carded("dwarf", ("ricochet", "rare"), x=5.5, y=10.5)
        world = open_map(walls=[(9, y) for y in range(30)])
        shots = []
        combat.fire(h, world, shots, [])
        fly(shots, [h], world, steps=12)
        self.assertEqual(shots[0].bounces, 1)
        self.assertFalse(shots[0].returning)               # flies on instead of home
        self.assertLess(shots[0].dir_x, 0)

    def test_homeward_fury(self):
        h = carded("dwarf", ("homeward_fury", "common"))
        p = combat.Projectile(12, 10.5, 0.0, h.weapon.spec.shell, owner=h, damage=20)
        p.returning = True
        d = Dummy(12, 10.5)
        combat._hit_actor(p, d, 12, 10.5, open_map(), [h, d], [])
        self.assertAlmostEqual(500 - d.hp, 30)

    def test_prism_colors_boost_each_other(self):
        h = carded("princess", ("prism", "rare"))
        d = Dummy(13, 10.5, hp=5000)
        d.hit_radius = 2.0
        shots = []
        combat.fire(h, open_map(), shots, [])
        fly(shots, [h, d])
        n = config.WEAPONS["rainbow"].pellets
        expected = sum(8 * (1 + 0.2 * k) for k in range(n))
        self.assertAlmostEqual(5000 - d.hp, expected)

    def test_crescendo_and_lullaby(self):
        h = carded("bard", ("crescendo", "common"), ("lullaby", "rare"))
        h.hp = 50
        foes = [Dummy(12 + i * 0.3, 10.5, hp=10000) for i in range(3)]
        world = open_map()
        dealt = []
        for _ in range(7):
            before = foes[0].hp
            combat.pulse(h, world, [h] + foes, [])
            dealt.append(before - foes[0].hp)
        base = config.WEAPONS["lute"].damage
        self.assertAlmostEqual(dealt[0], base)
        self.assertAlmostEqual(dealt[1], base * 1.1)
        self.assertAlmostEqual(dealt[6], base * 1.5)               # capped at +50%
        self.assertEqual(h.hp, 50 + 3 * 7)                          # 1 HP per enemy per beat
        combat.pulse(h, world, [h], [])                             # a beat that hits nothing
        self.assertEqual(h.streak, 0)

    def test_syncopation_and_grand_finale(self):
        m, s = game("bard")
        take(s, ("syncopation", "uncommon"), ("grand_finale", "legendary"))
        mods = [s.rules.attack_mods(s.me) for _ in range(8)]
        self.assertEqual((mods[0]["reach_mult"], mods[0]["mult"]), config.SYNCOPATION[1])
        self.assertEqual((mods[1]["reach_mult"], mods[1]["mult"]), config.SYNCOPATION[0])
        self.assertAlmostEqual(mods[7]["mult"], config.SYNCOPATION[0][1] * 4)
        self.assertAlmostEqual(mods[7]["reach_mult"], config.SYNCOPATION[0][0] * 2)
        pygame.mouse.set_visible(True)


class CapstoneTest(unittest.TestCase):
    def test_refraction_splits_once(self):
        h = carded("princess", ("refraction", "legendary"))
        d = Dummy(12, 10.5)
        shots = []
        combat.fire(h, open_map(), shots, [])
        shots[:] = shots[:1]
        fly(shots, [h, d], steps=3)
        kids = [p for p in shots if p.child]
        self.assertEqual(len(kids), config.REFRACTION_SPLIT)
        self.assertTrue(all(abs(k.damage - 8 * config.REFRACTION_DAMAGE) < 1e-9 for k in kids))

    def test_deadeye_crits_pierce_and_fly_far(self):
        h = carded("huntress", ("deadeye", "legendary"))
        h.stats.crit_chance = 1.0
        foes = [Dummy(12 + i, 10.5) for i in range(6)]
        shots = []
        combat.fire(h, open_map(w=120), shots, [])
        fly(shots, [h] + foes, open_map(w=120), steps=200)
        self.assertTrue(all(f.hp < 500 for f in foes))             # through all six

    def test_cyclone_rethrows_a_caught_axe(self):
        h = carded("dwarf", ("cyclone", "legendary"))
        far = Dummy(10.5, 16)
        p = combat.Projectile(11, 10.5, 0.0, h.weapon.spec.shell, owner=h, damage=22)
        p.returning = True
        shots = [p]
        fly(shots, [h, far], steps=3)
        self.assertEqual(len(shots), 1)
        self.assertTrue(shots[0].child)
        self.assertGreater(shots[0].dir_y, 0.9)                     # off toward the enemy

    def test_ball_lightning_leaves_a_crackle(self):
        from ascii_adventurers.tests.test_weapons import shock
        h = shock(carded("wizard", ("ball_lightning", "epic")))
        d, near = Dummy(13, 10.5, hp=5000), Dummy(13, 11.5, hp=5000)
        zones, shots = [], []
        combat.fire(h, open_map(), shots, [])
        fly(shots, [h, d], zones=zones, steps=10)
        self.assertEqual(len(zones), 1)
        before = near.hp
        for _ in range(60):
            update_zones(zones, [h, d, near], [], 1 / 60)
        self.assertLess(near.hp, before)
        for _ in range(120):
            update_zones(zones, [h, d, near], [], 1 / 60)
        self.assertEqual(zones, [])

    def test_overflow_and_juggernaut(self):
        st = cards.hero_stats([("keen_eye", "legendary")] * 9 + [("overflow", "legendary")])
        self.assertEqual(st.crit_chance, 1.0)
        self.assertAlmostEqual(st.crit_damage, config.BASE_CRIT_DAMAGE + 2 * (0.05 + 9 * 0.14 - 1))
        st = cards.hero_stats([("nimble", "legendary"), ("juggernaut", "legendary")])
        self.assertEqual(st.evasion, 0.0)

    def test_aegis_overheal_becomes_shield(self):
        h = carded("bard", ("aegis", "legendary"))
        h.hp = h.max_hp - 5
        h.heal(30)
        self.assertEqual(h.hp, h.max_hp)
        self.assertAlmostEqual(h.shield, 25)
        h.take_damage(20, None, None)
        self.assertEqual(h.hp, h.max_hp)                            # the shield took it

    def test_phoenix_then_second_chance(self):
        g = Guild(loot=10 ** 6)
        g.buy_upgrade("second_chance")
        m, s = game("bard", g)
        take(s, ("phoenix", "legendary"))
        for frac in (config.PHOENIX[0], config.SECOND_CHANCE_HP):
            s.hero.invulnerable = False
            s.hero.take_damage(10 ** 6, None, None)
            s.update(1 / 60)
            self.assertTrue(s.me.alive)
            self.assertAlmostEqual(s.hero.hp, s.hero.max_hp * frac, delta=1.0)
        s.hero.take_damage(10 ** 6, None, None)
        s.update(1 / 60)
        self.assertFalse(s.me.alive)
        pygame.mouse.set_visible(True)


class ConditionalTest(unittest.TestCase):
    def test_bonuses(self):
        d = Dummy(12, 10.5)
        h = carded("wizard", ("untouched", "uncommon"))
        self.assertAlmostEqual(combat.situational_bonus(h.stats, h, d), 0.3)
        h.hp = h.max_hp * 0.5
        self.assertAlmostEqual(combat.situational_bonus(h.stats, h, d), 0.0)
        h = carded("wizard", ("berserker", "rare"))
        h.hp = h.max_hp * 0.25
        self.assertAlmostEqual(combat.situational_bonus(h.stats, h, d), 0.75)
        h = carded("wizard", ("giant_slayer", "uncommon"), ("veteran", "rare"))
        h.level = 20
        self.assertAlmostEqual(combat.situational_bonus(h.stats, h, d), 0.4 + 0.2)
        h = carded("wizard", ("golden_hoard", "rare"))
        h.run_loot = 1000
        self.assertAlmostEqual(combat.situational_bonus(h.stats, h, d), 0.2)
        h.run_loot = 10 ** 6
        self.assertAlmostEqual(combat.situational_bonus(h.stats, h, d), 0.5)
        h = carded("wizard", ("wildfire", "uncommon"))
        inflict(d, "burn", None)
        self.assertAlmostEqual(combat.situational_bonus(h.stats, h, d), 0.3)

    def test_bestiary_bonus(self):
        h = carded("wizard")
        d = Dummy(12, 10.5)
        d.kind_key = "toad"
        self.assertEqual(combat.situational_bonus(h.stats, h, d), 0.0)
        h.bestiary = {"toad"}
        self.assertAlmostEqual(combat.situational_bonus(h.stats, h, d), config.BESTIARY_BONUS)


class TradeOffAndTriggerTest(unittest.TestCase):
    def test_glass_cannon_and_heavy_plate(self):
        lo = cards.build_loadout("bard", [("glass_cannon", "rare")])
        self.assertEqual(lo.body.max_hp, 70)
        h = carded("bard", ("heavy_plate", "uncommon"))
        self.assertAlmostEqual(h.take_damage(80, None, None), h.max_hp * 0.10)

    def test_spray_and_pray_splits_once(self):
        h = carded("huntress", ("spray_and_pray", "rare"))   # (one arrow; M20 wizard has 3)
        shots = []
        combat.fire(h, open_map(w=80), shots, [])
        fly(shots, [h], open_map(w=80), steps=25)
        self.assertEqual(len(shots), 2)
        self.assertTrue(all(p.child and abs(p.damage - 16 * config.SPLIT_DAMAGE) < 1e-9
                            for p in shots))

    def test_kill_triggers(self):
        from ascii_adventurers.ai import make_enemy
        m, s = game("bard")
        take(s, ("bloodlust", "uncommon"), ("frenzy", "uncommon"), ("soul_harvest", "common"),
             ("volatile", "uncommon"), ("chain_reaction", "rare"))
        s.hero.rng.random = lambda: 0.0                             # every kill explodes
        s.hero.hp = 50
        e = make_enemy("warrior", s.hero.x + 4, s.hero.y, random.Random(1))
        near = make_enemy("warrior", s.hero.x + 4.5, s.hero.y, random.Random(2))
        near.hp = 1
        s.enemies += [e, near]
        e.take_damage(10 ** 4, s.hero, 0.0)
        s.update(1 / 60)
        self.assertFalse(near.alive)                                # blown up
        self.assertEqual(s.stats.total_kills, 2)
        self.assertEqual(len(s.hero.bloodlust), 2)
        self.assertGreater(s.me.frenzy, 0)
        self.assertGreaterEqual(s.hero.hp, 52 - 0.1)
        pygame.mouse.set_visible(True)

    def test_bounty_cache(self):
        from ascii_adventurers.ai import make_enemy
        m, s = game("bard")
        take(s, ("bounty", "rare"))
        for i in range(config.BOUNTY_EVERY):
            e = make_enemy("toad", s.hero.x + 5, s.hero.y, random.Random(i))
            s.enemies.append(e)
            e.take_damage(10 ** 4, s.hero, 0.0)
            s.update(1 / 60)
        per = config.ENEMIES["toad"].xp * config.LOOT_PER_XP
        self.assertAlmostEqual(s.stats.loot, per * config.BOUNTY_EVERY * 2)
        self.assertAlmostEqual(s.spawner.haste, config.HASTE_BOUNTY)
        pygame.mouse.set_visible(True)

    def test_retaliation_surge_echo(self):
        from ascii_adventurers.ai import make_enemy
        m, s = game("bard")
        take(s, ("retaliation", "uncommon"), ("surge", "uncommon"), ("echo", "uncommon"))
        e = make_enemy("warrior", s.hero.x + 1.5, s.hero.y, random.Random(1))
        s.enemies.append(e)
        x0 = e.x
        s.hero.take_damage(5, e, 0.0)
        s.update(1 / 60)
        self.assertGreater(e.x, x0 + 1.0)                           # shoved
        self.assertLess(e.hp, e.max_hp)
        s.hero.hp = 10
        s._gain_xp(s.me, s.me.progress.needed)                      # level-up: Surge
        self.assertAlmostEqual(s.hero.hp, 10 + s.hero.max_hp * config.SURGE_HEAL)
        s.hero.attacks, s.me.echo_timer = 0, 0.0
        for _ in range(config.ECHO_EVERY - 1):
            s.rules.attack_mods(s.me)
        self.assertEqual(s.me.echo_timer, 0)
        s.rules.attack_mods(s.me)
        self.assertGreater(s.me.echo_timer, 0)
        pygame.mouse.set_visible(True)


class StatusCardTest(unittest.TestCase):
    def setUp(self):
        statuses.combos.clear()

    def test_virulence_and_hemorrhage(self):
        h = carded("wizard", ("virulence", "rare"), ("hemorrhage", "rare"))
        d = Dummy(12, 10.5)
        for _ in range(12):
            inflict(d, "poison", h)
        self.assertEqual(d.status.stacks("poison"), config.VIRULENCE[0])
        still, moving = Dummy(12, 10.5), Dummy(14, 10.5)
        inflict(still, "bleed", h)
        inflict(moving, "bleed", h)
        for _ in range(60):
            moving.x += 0.01
            update = statuses.update_statuses
            update([still, moving], 1 / 60, [])
        self.assertAlmostEqual(500 - moving.hp, 2 * (500 - still.hp), delta=0.5)

    def test_thermal_shock_and_toxic_current(self):
        m, s = game("wizard")
        take(s, ("thermal_shock", "epic"), ("toxic_current", "epic"))
        a, b = Dummy(s.hero.x + 5, s.hero.y, 1000), Dummy(s.hero.x + 5.5, s.hero.y, 1000)
        s.enemies += [a, b]
        inflict(a, "burn", s.hero, 3)
        inflict(a, "chill", s.hero)
        s.rules.resolve_combos()
        self.assertFalse(a.status.has("chill"))                     # used up
        self.assertAlmostEqual(1000 - b.hp, 30, delta=0.01)          # 10 x 3 stacks
        inflict(a, "poison", s.hero, 4)
        inflict(a, "shock", s.hero)
        s.rules.resolve_combos()
        self.assertEqual(b.status.stacks("poison"), 4)
        pygame.mouse.set_visible(True)


class SpellRev2Test(unittest.TestCase):
    def run_spell(self, h, key, actors, seconds, world=None, level=1):
        s = SpellState(key, level)
        shots, zones, effects = [], [], []
        world = world or open_map()
        for _ in range(round(seconds * 60)):
            update_spells(h, {key: s}, world, actors, effects, 1 / 60, shots, zones)
            combat.update_projectiles(shots, world, effects, 1 / 60, actors, zones)
            update_zones(zones, actors, effects, 1 / 60)
        return s, shots, zones

    def test_wolf_hunts_and_bites(self):
        h = carded("bard")
        d = Dummy(18, 10.5)
        s, _, _ = self.run_spell(h, "spirit_wolf", [h, d], 3)
        self.assertLess(d.hp, 500)
        self.assertEqual(len(s.things), 1)

    def test_rune_trap(self):
        h = carded("bard")
        d = Dummy(30, 10.5)
        s, _, _ = self.run_spell(h, "rune_trap", [h, d], 2)
        self.assertEqual(len(s.things), 1)
        d.x, d.y = h.x, h.y
        self.run_spell(h, "rune_trap", [h, d], 2)
        self.assertLess(d.hp, 500)

    def test_poison_flask(self):
        h = carded("bard")
        d = Dummy(15, 10.5)
        self.run_spell(h, "poison_flask", [h, d], 3)
        self.assertTrue(d.status is not None and d.status.has("poison"))

    def test_storm_cloud(self):
        h = carded("wizard")
        d = Dummy(15, 10.5)
        self.run_spell(h, "storm_cloud", [h, d], 1.0)
        self.assertLess(d.hp, 500)
        self.assertTrue(d.status.has("shock"))

    def test_healing_totem(self):
        h = carded("bard")
        h.hp = 10
        self.run_spell(h, "healing_totem", [h], 12.1)
        self.assertGreater(h.hp, 10 + 3 * 6 - 0.5)                  # planted at 6 s, 6 s of 3 HP/s

    def test_fire_wand_and_turret(self):
        h = carded("wizard")
        h.stats.crit_chance = 1.0
        d = Dummy(16, 10.5, hp=5000)
        self.run_spell(h, "fire_wand", [h, d], 2)
        self.assertTrue(d.status.has("burn"))
        d2 = Dummy(16, 10.5, hp=5000)
        self.run_spell(h, "bone_turret", [h, d2], 6)
        hits = 5000 - d2.hp
        self.assertGreater(hits, 0)
        self.assertAlmostEqual(hits % 8, 0, places=6)               # summons never crit

    def test_ward_and_thorns(self):
        m, s = game("bard")
        take(s, ("ward_charm", "uncommon"), ("thorn_mail", "uncommon"))
        self.assertEqual(s.hero.shield, 25)
        from ascii_adventurers.ai import make_enemy
        e = make_enemy("warrior", s.hero.x + 3, s.hero.y, random.Random(1))
        s.hero.take_damage(10, e, 0.0)
        self.assertEqual((s.hero.hp, s.hero.shield), (s.hero.max_hp, 15))
        self.assertAlmostEqual(e.max_hp - e.hp, 5 + 0.3 * 0)          # all absorbed: flat only
        s.hero.since_hit = config.SHIELD_RECHARGE_DELAY
        for _ in range(120):
            s.rules.tick(s.me, 1 / 60)
        self.assertEqual(s.hero.shield, 25)
        pygame.mouse.set_visible(True)


class GateTest(unittest.TestCase):
    def test_capstones_wait_for_level_15(self):
        w = config.WEAPONS["arcane_missiles"]
        self.assertNotIn("arcane_storm", cards.eligible("wizard", w, Counter(), level=14))
        self.assertIn("arcane_storm", cards.eligible("wizard", w, Counter(), level=15))

    def test_card_and_stat_gates(self):
        w = config.WEAPONS["lute"]
        self.assertNotIn("chain_reaction", cards.eligible("bard", w, Counter()))
        self.assertIn("chain_reaction", cards.eligible("bard", w, Counter(volatile=1)))
        self.assertNotIn("juggernaut", cards.eligible("bard", w, Counter(), level=20))
        armored = cards.hero_stats([("thick_hide", "common")])
        self.assertIn("juggernaut", cards.eligible("bard", w, Counter(), armored, level=20))
        self.assertNotIn("elementalist", cards.eligible("bard", w, Counter()))
        fiery = cards.hero_stats([("kindling", "uncommon")])
        self.assertIn("elementalist", cards.eligible("bard", w, Counter(), fiery))

    def test_achievement_cards(self):
        g = Guild()
        self.assertFalse(g.unlocked("phoenix"))
        g.achievements.add("level_30")
        self.assertTrue(g.unlocked("phoenix"))


class GuildRev2Test(unittest.TestCase):
    def test_rev1_saves_are_refunded(self):
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "guild.json")
            with open(path, "w") as f:
                json.dump({"loot": 10, "guild": {"whetstone": 2, "arcane_wing": 1},
                           "heroes": {"bard": {"mastery": 1, "lullaby": 2}},
                           "cards": ["overload"]}, f)
            g = Guild.load(path)
        refund = (80 + 128) + 1500 + 60 + (100 + 160)
        self.assertEqual(g.loot, 10 + refund)
        self.assertEqual((g.guild, g.heroes, g.cards), ({}, {}, {"phase_darts"}))   # (P4 rename)

    def test_pacts_and_pages(self):
        g = Guild(loot=10 ** 5)
        self.assertFalse(g.toggle_pact("blood"))                    # not owned
        self.assertTrue(g.buy_pact("blood"))
        self.assertTrue(g.toggle_pact("blood"))
        self.assertEqual(g.active_pacts, {"blood"})
        self.assertFalse(g.known("toad"))
        g.kills["toad"] = config.BESTIARY_KILLS
        self.assertTrue(g.known("toad"))
        self.assertFalse(g.buy_page("toad"))                        # already yours
        self.assertTrue(g.buy_page("ogre"))

    def test_pacts_in_a_run(self):
        g = Guild(loot=10 ** 6)
        for k in config.PACTS:
            g.buy_pact(k)
            g.toggle_pact(k)
        m, s = game("bard", g)
        self.assertEqual(s.hero.max_hp, round(100 * 0.6))
        sp = s.spawner
        self.assertAlmostEqual(sp.density, 1.3)
        self.assertEqual(sp.level_bonus, 10)
        self.assertAlmostEqual(sp.damage_bonus, 0.25)
        self.assertAlmostEqual(sp.haste, 0.15)
        s.hero.hp = 10
        for _ in range(60):
            s.update(1 / 60)
        self.assertEqual(s.hero.hp, 10)                             # Famine: no regen
        self.assertAlmostEqual(s.pacts["loot"], sum(p.loot for p in config.PACTS.values()))
        pygame.mouse.set_visible(True)

    def test_recruits_kit_and_royal_decree(self):
        g = Guild(loot=10 ** 6)
        g.buy_upgrade("recruits_kit")
        g.buy_upgrade("royal_decree", "princess")
        m, s = game("princess", g)
        prog = s.me.progress
        self.assertEqual((prog.level, prog.picks), (2, 2))
        s.update(1 / 60)
        self.assertTrue(all(config.RARITIES.index(r) >= 2 for _, r in prog.offer))
        s._choose_card(0)
        self.assertIsNone(prog.decree)
        pygame.mouse.set_visible(True)

    def test_encore_tour_and_fortune(self):
        g = Guild(loot=10 ** 6)
        g.buy_upgrade("encore_tour", "bard")
        m, s = game("bard", g)
        prog = s.me.progress
        sizes = []
        for _ in range(5):
            prog.picks, prog.offer = 1, []
            s._cards(s.me, None)
            sizes.append(len(prog.offer))
            s._cards(s.me, 0)
        self.assertEqual(sizes, [3, 3, 3, 3, 4])
        take(s, ("fortune", "epic"))
        prog.picks, prog.offer = 1, []
        s._cards(s.me, None)
        self.assertEqual(len(prog.offer), 4)
        s.update(1 / 60)
        s.draw(m.text)                                              # four cards fit
        pygame.mouse.set_visible(True)

    def test_achievements(self):
        m, s = game("bard")
        s.me.progress.level = 29
        s._gain_xp(s.me, s.me.progress.needed)
        self.assertIn("level_30", m.app.guild.achievements)
        take(s, *[("keen_eye", "legendary")] * 6)
        s.rules.check_build(s.me)
        self.assertIn("crit_75", m.app.guild.achievements)
        pygame.mouse.set_visible(True)

    def test_bestiary_counts_kills(self):
        from ascii_adventurers.ai import make_enemy
        g = Guild()
        g.kills["toad"] = config.BESTIARY_KILLS - 1
        m, s = game("bard", g)
        e = make_enemy("toad", s.hero.x + 5, s.hero.y, random.Random(1))
        s.enemies.append(e)
        e.take_damage(10 ** 4, s.hero, 0.0)
        s.update(1 / 60)
        self.assertEqual(g.kills["toad"], config.BESTIARY_KILLS)
        self.assertIn("toad", s.hero.bestiary)
        pygame.mouse.set_visible(True)


class TrainerTest(unittest.TestCase):
    def test_quick_catch_capacitor_quiver_bright_colors(self):
        st = cards.hero_stats([], [("return_speed", "add", 0.5), ("shot_size", "add", 0.5)])
        self.assertEqual((st.return_speed, st.shot_size), (0.5, 0.5))
        g = Guild(loot=10 ** 6)
        for _ in range(3):
            g.buy_upgrade("quiver", "huntress")
        m, s = game("huntress", g)
        extra = [s.rules.attack_mods(s.me)["extra_pellets"] for _ in range(12)]
        every = config.QUIVER_EVERY - 2
        self.assertEqual([i + 1 for i, x in enumerate(extra) if x], [every, every * 2])
        pygame.mouse.set_visible(True)
        g = Guild(loot=10 ** 6)
        g.buy_upgrade("capacitor", "wizard")
        m, s = game("wizard", g)
        s.hero.idle = config.CAPACITOR_IDLE
        self.assertAlmostEqual(s.rules.attack_mods(s.me)["mult"], 1.5)
        self.assertAlmostEqual(s.rules.attack_mods(s.me)["mult"], 1.0)
        pygame.mouse.set_visible(True)

    def test_opening_act(self):
        g = Guild(loot=10 ** 6)
        g.buy_upgrade("opening_act", "bard")
        m, s = game("bard", g)
        self.assertEqual(s.rules.attack_mods(s.me)["mult"], 2.0)
        s.hero.time = 61
        self.assertEqual(s.rules.attack_mods(s.me)["mult"], 1.0)
        pygame.mouse.set_visible(True)


class ArchiveUiTest(unittest.TestCase):
    def setUp(self):
        from ascii_adventurers.scenes.guild_hall import GuildHallScene
        from ascii_adventurers.tests.test_players import make_manager
        self.m = make_manager()
        self.m.app.guild = Guild(loot=10 ** 6)
        self.s = GuildHallScene("bard")
        self.m._set_scene(self.s)
        self.s.update(1 / 60)

    def tearDown(self):
        pygame.mouse.set_visible(True)

    def open(self, kind):
        st = next(x for x in self.s.stations if x.kind == kind)
        self.s.hero.x, self.s.hero.y = st.x, st.y + 2
        self.s.update(1 / 60)
        self.s.interact(self.s.near)
        return self.s.panel

    def test_shelves(self):
        panel = self.open("cards")
        self.assertEqual(panel.mode, "archive")
        from ascii_adventurers.ui.guild_panel import SHELVES
        seen = []
        for _ in range(len(SHELVES)):
            seen.append(len(panel.rows()))
            self.s.draw(self.m.text)
            self.s.handle_event(key(pygame.K_RIGHT))
        self.assertEqual(seen[2], len(config.PACTS))
        self.assertEqual(seen[3], len(config.BESTIARY))
        self.assertGreater(seen[0], 20)                              # cards (scrolls)
        self.assertEqual(panel.shelf, 0)                              # round to cards again
        for _ in range(seen[0] - 1):
            self.s.handle_event(key(pygame.K_DOWN))
        self.assertGreater(panel.top, 0)
        self.s.draw(self.m.text)

    def test_buy_a_pact_then_switch_it_on_at_the_gate(self):
        panel = self.open("cards")
        panel.shelf = 2
        self.s.handle_event(key(pygame.K_RETURN))
        g = self.m.app.guild
        first = list(config.PACTS)[0]
        self.assertIn(first, g.pacts)
        self.s.panel = None
        gate = self.open("gate")
        self.assertEqual([r.key for r in gate.rows()], ["enter", first])
        self.s.handle_event(key(pygame.K_DOWN))
        self.s.handle_event(key(pygame.K_RETURN))
        self.assertEqual(g.active_pacts, {first})
        self.s.draw(self.m.text)

    def test_bestiary_page(self):
        panel = self.open("cards")
        panel.shelf = 3
        self.s.handle_event(key(pygame.K_RETURN))
        self.assertIn(list(config.BESTIARY)[0], self.m.app.guild.pages)
        self.s.draw(self.m.text)


if __name__ == "__main__":
    unittest.main()
