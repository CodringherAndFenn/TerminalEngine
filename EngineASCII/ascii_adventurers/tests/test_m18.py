"""M18: the dodge roll, its cards, evasion, the Lingering gate, the spell
level-ups that replaced "lasts longer", and the archetype lean in offers."""

import math
import os
import unittest
from collections import Counter

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from ascii_adventurers import config
from ascii_adventurers.entities.projectile import Projectile
from ascii_adventurers.players import cards
from ascii_adventurers.players.controls import PlayerInput
from ascii_adventurers.players.stats import HeroStats
from ascii_adventurers.systems import combat, roll
from ascii_adventurers.systems.zones import update_zones
from ascii_adventurers.tests.test_m14 import carded
from ascii_adventurers.tests.test_m16 import SpellRev2Test, game, key, take
from ascii_adventurers.tests.test_weapons import Dummy, open_map

DT = 1 / 60


class _P:
    """Just enough of a Player for systems/roll.py."""

    def __init__(self, hero):
        self.hero = hero
        self.local = True
        self.alive = True


class _Scene:
    """Just enough of the game scene for systems/roll.py."""

    def __init__(self, hero, world=None, others=()):
        self.world = world or open_map()
        self.effects, self.projectiles, self.zones, self._sounds = [], [], [], []
        self.others = list(others)
        self.p = _P(hero)

    def _actors(self):
        return [self.p.hero] + [a for a in self.others if a.alive]

    def run(self, seconds, inp=None, first=None):
        """Step the roll and the hero; `first` is the first step's input
        (e.g. the roll press), `inp` every other step's."""
        h = self.p.hero
        for i in range(round(seconds * 60)):
            now = first if (i == 0 and first is not None) else (inp or PlayerInput())
            roll.step(self, self.p, now, DT)
            rolling, x0, y0 = h.rolling, h.x, h.y
            h.move(now.move_x, now.move_y, DT, self.world)
            roll.after_move(self, self.p, rolling, x0, y0)
            combat.update_projectiles(self.projectiles, self.world, self.effects, DT,
                                      self._actors(), self.zones)
            roll.close_calls([self.p], self.projectiles, DT)
            update_zones(self.zones, self._actors(), self.effects, DT)


def press(mx=0.0, my=0.0):
    return PlayerInput(mx, my, roll=True)


class RollTest(unittest.TestCase):
    def test_rolls_about_four_tiles_in_a_quarter_second(self):
        h = carded("bard")
        sc = _Scene(h)
        sc.run(config.ROLL_TIME, first=press(1, 0))
        self.assertAlmostEqual(h.x - 10.5, config.ROLL_DISTANCE, delta=0.1)
        self.assertFalse(h.rolling)
        self.assertGreater(h.vx, 0)                 # comes out walking, not stopped dead

    def test_standing_still_rolls_toward_the_aim(self):
        h = carded("bard", aim=math.pi / 2)
        sc = _Scene(h)
        sc.run(config.ROLL_TIME, first=press())
        self.assertAlmostEqual(h.y - 10.5, config.ROLL_DISTANCE, delta=0.1)
        self.assertAlmostEqual(h.x, 10.5, delta=0.01)

    def test_walls_stop_a_roll(self):
        h = carded("bard")
        sc = _Scene(h, open_map(walls=[(12, y) for y in range(30)]))
        sc.run(config.ROLL_TIME, first=press(1, 0))
        self.assertLess(h.x, 12)

    def test_iframes_let_shots_through(self):
        h = carded("bard")
        sc = _Scene(h)
        h.roll_t = 1.0
        h.roll_speed = 0.0
        enemy = Dummy(20, 10.5)
        shot = Projectile(16, 10.5, math.pi, config.WEAPONS["goblin_bow"].shell, owner=enemy,
                          damage=10)
        sc.projectiles.append(shot)
        for _ in range(30):
            combat.update_projectiles(sc.projectiles, sc.world, [], DT, [h, enemy])
        self.assertEqual(h.hp, h.max_hp)
        self.assertLess(shot.x, h.x)                # it flew on past
        self.assertFalse(h.hittable)
        self.assertEqual(h.take_damage(50, enemy, 0.0), 0.0)
        h.roll_t = 0.0
        self.assertTrue(h.hittable)

    def test_cooldown_and_charges(self):
        h = carded("bard")
        sc = _Scene(h)
        sc.run(0.5, first=press(1, 0))
        self.assertEqual(h.roll_charges, 0)
        x = h.x
        sc.run(0.5, first=press(1, 0))              # no charge: no roll
        self.assertLess(h.x - x, 0.5)
        sc.run(config.ROLL_COOLDOWN - 1.0 + 0.05)
        self.assertEqual(h.roll_charges, 1)
        self.assertEqual(roll.recharge_frac(h), 1.0)

    def test_quick_recovery_and_extra_roll(self):
        h = carded("bard", ("quick_recovery", "legendary"), ("extra_roll", "rare"))
        self.assertEqual(h.stats.max_rolls, 2)
        self.assertAlmostEqual(h.stats.roll_recharge, config.ROLL_COOLDOWN * 0.75)
        st = cards.hero_stats([("quick_recovery", "legendary")] * 5)
        self.assertEqual(st.roll_cooldown, config.MAX_ROLL_COOLDOWN)
        sc = _Scene(h)
        h.roll_charges = 2
        sc.run(0.3, first=press(1, 0))
        sc.run(0.3, first=press(1, 0))
        self.assertEqual(h.roll_charges, 0)
        self.assertGreater(h.x - 10.5, 2 * config.ROLL_DISTANCE - 0.3)


class RollCardTest(unittest.TestCase):
    def test_riposte_crits_the_next_attack_only(self):
        m, s = game("huntress")
        take(s, ("riposte", "uncommon"))
        s.hero.stats.crit_chance = 0.0
        s.hero.roll_charges = 1
        roll.start(s, s.me, 1, 0)
        self.assertGreater(s.hero.riposte, 0)
        self.assertTrue(s.rules.attack_mods(s.me).get("sure_crit"))
        self.assertFalse(s.rules.attack_mods(s.me).get("sure_crit"))
        d = Dummy(0, 0)
        combat.strike(d, 10, s.hero, 0.0, [], sure_crit=True)
        self.assertTrue(s.hero.last_crit)
        pygame.mouse.set_visible(True)

    def test_slipstream(self):
        h = carded("bard", ("slipstream", "uncommon"))
        sc = _Scene(h)
        sc.run(config.ROLL_TIME + DT, first=press(1, 0))
        self.assertGreater(h.slipstream, 0)
        sc.run(1.0, PlayerInput(0, 1))
        self.assertAlmostEqual(h.vy, h.spec.max_speed * (1 + config.SLIPSTREAM[0]), delta=0.01)
        sc.run(config.SLIPSTREAM[1])
        self.assertEqual(h.speed_mult, 1.0)

    def test_close_call(self):
        h = carded("bard", ("close_call", "uncommon"))
        sc = _Scene(h)
        enemy = Dummy(40, 10.5)
        sc.others.append(enemy)
        for i in range(3):
            sc.projectiles.append(Projectile(13 + i, 10.5, math.pi,
                                             config.WEAPONS["goblin_bow"].shell, owner=enemy))
        sc.run(config.ROLL_TIME, first=press(1, 0))
        self.assertEqual(h.hp, h.max_hp)
        self.assertAlmostEqual(h.roll_recharge, config.ROLL_TIME + 3 * config.CLOSE_CALL,
                               delta=0.02)

    def test_scorched_trail_burns(self):
        h = carded("bard", ("scorched_trail", "uncommon"))
        self.assertIn("burn", h.stats.sources)
        d = Dummy(12.5, 10.5, hp=5000)
        sc = _Scene(h, others=[d])
        sc.run(1.0, first=press(1, 0))
        trail = [z for z in sc.zones if z.kind == "trail"]
        self.assertGreaterEqual(len(trail), 4)
        self.assertTrue(d.status is not None and d.status.has("burn"))

    def test_prism_dash_mixes_statuses(self):
        h = carded("princess", ("prism_dash", "uncommon"))
        sc = _Scene(h)
        for _ in range(4):
            h.roll_charges = 1
            sc.run(0.3, first=press(1, 0))
            h.x = 10.5
        self.assertGreater(len({z.inflicts for z in sc.zones}), 1)

    def test_blink_teleports_but_not_through_walls(self):
        h = carded("wizard", ("blink", "uncommon"))
        d = Dummy(15.5, 10.5)
        sc = _Scene(h, others=[d])
        sc.run(DT, first=press(1, 0))
        self.assertAlmostEqual(h.x, 10.5 + config.BLINK[0], delta=0.3)
        self.assertTrue(h.rolling)                  # still has its i-frames
        self.assertLess(d.hp, 500)
        self.assertTrue(d.status.has("shock"))
        h2 = carded("wizard", ("blink", "uncommon"))
        sc2 = _Scene(h2, open_map(walls=[(13, y) for y in range(30)]))
        sc2.run(DT, first=press(1, 0))
        self.assertLess(h2.x, 13)

    def test_backflip_looses_arrows(self):
        h = carded("huntress", ("backflip", "uncommon"), aim=math.pi)
        sc = _Scene(h)
        roll.start(sc, sc.p, 1, 0)
        self.assertEqual(len(sc.projectiles), config.BACKFLIP[0])
        self.assertTrue(all(math.cos(p.angle) < 0 for p in sc.projectiles))   # at the aim

    def test_shoulder_charge(self):
        h = carded("dwarf", ("shoulder_charge", "uncommon"))
        from ascii_adventurers.tests.test_players import make
        e = make("goblin_archer", 12.5, 10.5)
        e.hp = e.max_hp = 500
        sc = _Scene(h, others=[e])
        sc.run(config.ROLL_TIME, first=press(1, 0))
        self.assertLess(e.hp, 500)
        self.assertGreater(e.x, 13.5)               # shoved along the roll

    def test_drop_the_beat(self):
        h = carded("bard", ("drop_the_beat", "uncommon"))
        d = Dummy(16, 10.5)
        sc = _Scene(h, others=[d])
        sc.run(config.ROLL_TIME + DT, first=press(1, 0))
        self.assertLess(d.hp, 500)
        self.assertTrue(any(e.kind == "pulse" for e in sc.effects))

    def test_hero_roll_cards_are_their_own(self):
        for hero, k in (("wizard", "blink"), ("dwarf", "shoulder_charge"),
                        ("huntress", "backflip"), ("princess", "prism_dash"),
                        ("bard", "drop_the_beat")):
            w = config.WEAPONS[config.HEROES[hero].weapon]
            self.assertIn(k, cards.eligible(hero, w, Counter()))
            other = "bard" if hero != "bard" else "wizard"
            self.assertNotIn(k, cards.eligible(other, config.WEAPONS[config.HEROES[other].weapon],
                                               Counter()))


class InGameRollTest(unittest.TestCase):
    def tearDown(self):
        pygame.mouse.set_visible(True)

    def test_shift_rolls_and_hud_shows_it(self):
        m, s = game("bard")
        h = s.hero
        x, y = h.x, h.y
        s.handle_event(key(pygame.K_LSHIFT))
        for _ in range(3):
            s.update(DT)
        self.assertTrue(h.rolling or math.hypot(h.x - x, h.y - y) > 0.5)
        self.assertEqual(h.roll_charges, 0)
        s.draw(m.text)
        for _ in range(20):
            s.update(DT)
        self.assertFalse(h.rolling)
        self.assertGreater(math.hypot(h.x - x, h.y - y), 1.0)

    def test_pad_b_queues_a_roll(self):
        from ascii_adventurers.engine_ext.gamepads import BUTTON_B, EV_BUTTON
        m, s = game("bard")
        s.handle_event(pygame.event.Event(EV_BUTTON, button=BUTTON_B, instance_id=0))
        self.assertTrue(s.me.controls.take_roll())


class EvasionTest(unittest.TestCase):
    def test_renamed(self):
        self.assertFalse(hasattr(HeroStats(), "dodge"))
        st = cards.hero_stats([("nimble", "legendary")])
        self.assertAlmostEqual(st.evasion, 0.12)
        self.assertIn("evasion", config.CARDS["nimble"].label("common"))


class LingeringGateTest(unittest.TestCase):
    def test_only_with_something_that_lasts(self):
        w = config.WEAPONS[config.HEROES["bard"].weapon]
        self.assertNotIn("lingering", cards.eligible("bard", w, Counter()))
        for taken in ([("kindling", "uncommon")], [("poison_flask", "uncommon")],
                      [("bone_turret", "rare")]):
            st = cards.hero_stats(taken)
            self.assertIn("lingering", cards.eligible("bard", w, Counter(), st), taken)
        st = cards.hero_stats([("daggers", "uncommon")])
        self.assertNotIn("lingering", cards.eligible("bard", w, Counter(), st))


class SpellLevelTest(unittest.TestCase):
    run_spell = SpellRev2Test.run_spell

    def test_no_lasts_longer_levels_left(self):
        for k, s in config.SPELLS.items():
            for text, changes in s.levels:
                self.assertNotIn("longer", text, k)

    def test_two_flasks(self):
        h = carded("bard")
        a, b = Dummy(15, 10.5), Dummy(10.5, 16)
        s, _, zones = self.run_spell(h, "poison_flask", [h, a, b], 2.4, level=3)
        self.assertEqual(len({(round(z.x), round(z.y)) for z in zones}), 2)
        self.assertTrue(a.status.has("poison") and b.status.has("poison"))

    def test_totem_chills(self):
        h = carded("bard")
        d = Dummy(11.5, 10.5)
        self.run_spell(h, "healing_totem", [h, d], 7.5, level=3)
        self.assertTrue(d.status is not None and d.status.has("chill"))
        self.assertIn("chill", cards.hero_stats([("healing_totem", "rare")] * 3).sources)

    def test_turret_bolts_pierce(self):
        h = carded("wizard")
        a, b = Dummy(14, 10.5, hp=5000), Dummy(16, 10.5, hp=5000)
        self.run_spell(h, "bone_turret", [h, a, b], 6, level=3)
        self.assertLess(a.hp, 5000)
        self.assertLess(b.hp, 5000)


class ArchetypeLeanTest(unittest.TestCase):
    def test_leading_archetype(self):
        self.assertIsNone(cards.leading_archetype(Counter({"spirit_wolf": 1})))
        self.assertEqual(cards.leading_archetype(Counter({"spirit_wolf": 2})), "summoner")
        self.assertEqual(cards.leading_archetype(Counter({"riposte": 1, "slipstream": 1})), "roll")

    def test_every_archetype_code_is_a_card(self):
        codes = {c.code for c in config.CARDS.values()}
        for name, members in config.ARCHETYPES.items():
            self.assertTrue(set(members) <= codes, name)

    def test_a_summoner_always_sees_a_summoner_card(self):
        w = config.WEAPONS[config.HEROES["bard"].weapon]
        taken = [("spirit_wolf", "uncommon"), ("spirit_wolf", "uncommon")]
        st = cards.hero_stats(taken)
        counts = Counter(k for k, _ in taken)
        lean = cards.ARCHETYPE_CARDS["summoner"]
        hits = 0
        for n in range(200):
            offer = cards.draw_offer("bard", w, counts, 7, 0, n, st)
            self.assertEqual(len(offer), config.CARD_OFFER_SIZE)
            self.assertEqual(len({k for k, _ in offer}), len(offer))
            hits += any(k in lean for k, _ in offer)
        self.assertEqual(hits, 200)
        # Without a lean, offers draw the same as before M18 (no extra dice).
        plain = cards.draw_offer("bard", w, Counter(), 7, 0, 0)
        self.assertEqual(len(plain), config.CARD_OFFER_SIZE)


if __name__ == "__main__":
    unittest.main()
