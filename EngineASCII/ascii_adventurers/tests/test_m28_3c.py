"""M28.3c: the legendary tricks' framework and batch 1, the 11 pieces that
only come as legendaries (design/GEAR.md 19.1)."""

import math
import os
import unittest
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config
from ascii_adventurers.entities.projectile import Projectile
from ascii_adventurers.players import gear
from ascii_adventurers.players.gear import Offer
from ascii_adventurers.systems import combat, spells, statuses
from ascii_adventurers.systems.zones import update_zones
from ascii_adventurers.tests.test_m16 import game
from ascii_adventurers.tests.test_m28_1 import DrawTest
from ascii_adventurers.tests.test_m28_2a import foe, wear
from ascii_adventurers.tests.test_m28_2c import DT, _Case
from ascii_adventurers.ui import gear_picker
from ascii_adventurers.ui.gear_screen import piece_lines

BASE = 1000.0
BATCH_1 = ("overflow", "pandemic", "pack_leader", "juggernaut", "aegis", "phoenix",
           "arcane_storm", "cyclone", "deadeye", "refraction", "grand_finale")
HERO = {"arcane_storm": "wizard", "cyclone": "dwarf", "deadeye": "huntress",
        "refraction": "princess", "grand_finale": "bard"}


def plain(x, y, hp=BASE):
    d = foe(x, y, hp)
    d.espec = SimpleNamespace(elite=False, xp=10, name="plain")
    return d


def h_x(dx):
    return 20.5 + dx                                   # (_Case puts the hero at 20.5, 20.5)


class _Legend(_Case):
    def setup(self, key, rarity="legendary", *more, hero=None):
        """`key` worn at +0 and `rarity`; `more`: (key, level) worn too."""
        s, h = super().setup(key, 0, hero or HERO.get(key, "wizard"))
        g = s.me.progress.gear
        g.worn[g.wearing(key)].rarity = rarity
        for k, lv in more:
            wear(s, k, lv)
        s._apply_loadout(s.me)
        h.time = 100.0
        h.rng.random = lambda: 0.99
        return s, h

    def fly(self, shots, seconds):
        s = self.s
        for _ in range(round(seconds * 60)):
            self.h.time += DT
            combat.update_projectiles(shots, s.world, s.effects, DT, s._actors(), s.zones)
            update_zones(s.zones, s._actors(), s.effects, DT, s.world)

    def shot(self, x=None, y=None, angle=0.0, damage=20.0):
        h = self.h
        p = Projectile(h.x + 1.0 if x is None else x, h.y if y is None else y, angle,
                       h.weapon.spec.shell, owner=h, damage=damage)
        p.tags = h.weapon.spec.tags
        return p


class FrameworkTest(unittest.TestCase):
    def test_batch_1_is_built(self):
        for key in BATCH_1:
            name, text = gear.legendary_trick(key)
            self.assertTrue(name and text and text.isascii(), key)
            self.assertEqual(config.CARDS[key].rarity, "legendary", key)   # (always legendary)
        self.assertTrue(set(BATCH_1) <= set(config.GEAR_LEGENDARY))

    def test_the_flag_comes_with_a_legendary_from_plus_0(self):
        flags = [f for f, _, _ in gear.trick_flags("overflow", 0, "legendary")]
        self.assertEqual(flags, ["overflow+L"])
        self.assertIn("overflow+L", [f for f, _, _ in gear.power_steps("overflow", 0, "legendary")])
        self.assertEqual(gear.trick_flags("overflow", 9, "epic")[-1][0], "overflow+9")
        self.assertNotIn("overflow+L", [f for f, _, _ in gear.trick_flags("overflow", 9, "epic")])
        # (M28.3l: every piece has its legendary trick now -- see test_m28_3l)
        self.assertEqual(gear.trick_flags("no_such_piece", 9, "legendary"), [])

    def test_wearing_it_turns_it_on(self):
        m, s = game("wizard")
        wear(s, "overflow", 0)
        self.assertTrue(s.hero.stats.has("overflow+L"))
        s.me.progress.gear.worn[s.me.progress.gear.wearing("overflow")].rarity = "epic"
        s._apply_loadout(s.me)
        self.assertFalse(s.hero.stats.has("overflow+L"))

    def test_the_card_shows_it(self):
        text = " ".join(t for t, _ in piece_lines("overflow", "legendary", 0, (), 30))
        self.assertIn("LEGENDARY SPILLOVER:", text)
        text = " ".join(t for t, _ in piece_lines("overflow", "epic", 0, (), 30))
        self.assertNotIn("SPILLOVER", text)


class FitTest(DrawTest):
    def test_legendary_cards_fit_every_screen(self):
        from ascii_adventurers.players.progress import Progress
        prog = Progress(picks=1)
        prog.offer = [Offer("grand_finale", "legendary", ("sharpened", "iron_skin", "keen_eye"), "new"),
                      Offer("overflow", "legendary", ("sharpened", "keen_eye", "brutal"), "new"),
                      Offer("crescendo", "rare", ("sharpened",), "new")]
        for rows in (24, 30):
            for text in self.fits(lambda m: gear_picker.GearPicker(m, prog, lambda a: None),
                                  rows=rows):
                self.assertIn("LEGENDARY SPILLOVER", text)
                self.assertIn("SKIP", text)                # (the buttons stay on the screen)
                self.assertIn("wearing:", text)
        for text in self.fits(lambda m: gear_picker.GearPicker(m, prog, lambda a: None), rows=30):
            if "the damage left over" not in text:
                break
        else:
            self.fail("the wide screens should spell the trick out")


class SpilloverTest(_Legend):
    def crit_kill(self, victim, base=100.0):
        h = self.h
        h.rng.random = lambda: 0.0                     # (every roll crits)
        return combat.strike(victim, base, h, 0.0, self.s.effects)

    def test_a_killing_crit_spills_on(self):
        s, h = self.setup("overflow")
        weak, near, far = self.place(plain(22.0, 20.5, 10.0), plain(23.0, 20.5),
                                     plain(22.0 + config.SPILLOVER + 1.5, 20.5))
        dealt = self.crit_kill(weak)
        s.rules.resolve_combos()
        left = dealt - 10.0
        self.assertAlmostEqual(BASE - near.hp, left * h.stats.crit_damage)   # (it crit again)
        self.assertEqual(far.hp, BASE)

    def test_a_spill_that_crits_and_kills_spills_again(self):
        s, h = self.setup("overflow")
        weak, second, third = self.place(plain(22.0, 20.5, 10.0), plain(23.0, 20.5, 20.0),
                                         plain(24.5, 20.5))
        dealt = self.crit_kill(weak)
        s.rules.resolve_combos()
        cd = h.stats.crit_damage
        self.assertFalse(second.alive)
        self.assertAlmostEqual(BASE - third.hp, ((dealt - 10.0) * cd - 20.0) * cd)

    def test_a_spill_that_doesnt_crit_stops(self):
        s, h = self.setup("overflow")
        weak, second, third = self.place(plain(22.0, 20.5, 10.0), plain(23.0, 20.5, 20.0),
                                         plain(24.5, 20.5))
        self.crit_kill(weak)
        h.rng.random = lambda: 0.99
        s.rules.resolve_combos()
        self.assertFalse(second.alive)                 # (killed by a plain spill...)
        self.assertEqual(third.hp, BASE)               # (...which doesn't spill)

    def test_not_without_the_trick_nor_on_a_plain_kill(self):
        s, h = self.setup("overflow", "epic")
        weak, near = self.place(plain(22.0, 20.5, 10.0), plain(23.0, 20.5))
        self.crit_kill(weak)
        s.rules.resolve_combos()
        self.assertEqual(near.hp, BASE)
        s, h = self.setup("overflow")
        weak, near = self.place(plain(22.0, 20.5, 10.0), plain(23.0, 20.5))
        combat.strike(weak, 100.0, h, 0.0, s.effects)  # (no crit)
        s.rules.resolve_combos()
        self.assertEqual(near.hp, BASE)


class MiasmaTest(_Legend):
    def test_a_dying_enemy_leaves_a_cloud(self):
        s, h = self.setup("pandemic")
        radius, life, every = config.MIASMA
        sick = plain(30.0, 30.5)
        statuses.inflict(sick, "burn", h, 2)
        statuses.inflict(sick, "poison", h, 1)
        inside, outside = self.place(plain(30.0, 30.5), plain(36.0, 30.5))
        sick.x, sick.y = 30.0, 30.5
        s.rules._pandemic = lambda *a, **k: None       # (only the cloud)
        sick.hp = 0.0
        s.rules.on_kill(s.me, sick)
        clouds = [z for z in s.zones if z.kind == "miasma"]
        self.assertEqual(sorted(z.inflicts for z in clouds), ["burn", "poison"])
        for _ in range(round(1.5 * 60)):
            update_zones(s.zones, s._actors(), s.effects, DT, s.world)
        self.assertEqual(inside.status.stacks("burn"), 2)        # (one now, one a second on)
        self.assertTrue(inside.status.has("poison"))
        self.assertIsNone(outside.status)
        for _ in range(round(life * 60)):
            update_zones(s.zones, s._actors(), s.effects, DT, s.world)
        self.assertEqual([z for z in s.zones if z.kind == "miasma"], [])

    def test_not_without_the_trick(self):
        s, h = self.setup("pandemic", "epic")
        sick = plain(30.0, 30.5)
        statuses.inflict(sick, "burn", h, 2)
        sick.hp = 0.0
        s.rules.on_kill(s.me, sick)
        self.assertEqual([z for z in s.zones if z.kind == "miasma"], [])


class InMyImageTest(_Legend):
    def run_turret(self, hero, at=26.0):
        s, h = self.setup("pack_leader", "legendary", ("bone_turret", 0), hero=hero)
        st = s.me.spells["bone_turret"]
        st.timer = 0.0
        st.params = dict(st.params, interval=1000.0)
        target = self.place(plain(at, 20.5))[0]
        for _ in range(3):
            spells.update_spells(h, s.me.spells, s.world, s._actors(), s.effects, DT,
                                 s.projectiles, s.zones)
        return s, h, target

    def test_turrets_fire_your_attack(self):
        s, h, target = self.run_turret("huntress")
        spec = h.weapon.spec
        shots = [q for q in s.projectiles if q.owner is h]
        self.assertTrue(shots)
        q = shots[0]
        self.assertIs(q.spec, spec.shell)                          # (an arrow, not bone)
        self.assertAlmostEqual(q.mult, config.IN_MY_IMAGE)
        self.assertFalse(q.summon)                                  # (your tricks ride on it)

    def test_a_turret_beats_for_the_bard(self):
        s, h, target = self.run_turret("bard", at=h_x(1.5))
        self.assertLess(target.hp, BASE)
        self.assertEqual(s.projectiles, [])               # (beats, no bone)

    def test_wolves_bite_for_your_hit_when_its_more(self):
        s, h = self.setup("pack_leader", "legendary", hero="dwarf")
        axe = h.weapon.spec.shell.damage
        self.assertEqual(spells.image_bite(h, 1.0), axe)
        self.assertEqual(spells.image_bite(h, axe + 50), axe + 50)
        s, h = self.setup("pack_leader", "epic", hero="dwarf")
        self.assertEqual(spells.image_bite(h, 1.0), 1.0)

    def test_plain_turrets_without_it(self):
        s, h = self.setup("pack_leader", "epic", ("bone_turret", 0), hero="huntress")
        st = s.me.spells["bone_turret"]
        st.timer = 0.0
        self.place(plain(26.0, 20.5))
        for _ in range(3):
            spells.update_spells(h, s.me.spells, s.world, s._actors(), s.effects, DT,
                                 s.projectiles, s.zones)
        self.assertTrue(all(q.spec is config.SPELL_SHELLS["turret"] for q in s.projectiles))


class StoneskinTest(_Legend):
    def test_small_hits_do_nothing(self):
        s, h = self.setup("juggernaut")
        h.stats.armor = 20.0
        bad = plain(22.0, 20.5)
        hp = h.hp
        self.assertEqual(h.take_damage(20.0 * config.STONESKIN, bad, None), 0.0)
        self.assertEqual(h.hp, hp)
        self.assertEqual(h.blocked, 1)
        self.assertGreater(h.take_damage(20.0 * config.STONESKIN + 1, bad, None), 0.0)

    def test_not_without_the_trick(self):
        s, h = self.setup("juggernaut", "epic")
        h.stats.armor = 20.0
        self.assertGreater(h.take_damage(5.0, plain(22.0, 20.5), None), 0.0)


class DaybreakTest(_Legend):
    def test_healing_while_hurt_fills_the_shield(self):
        s, h = self.setup("aegis")
        h.shield = 0.0
        h.hp = h.max_hp - 30
        h.heal(10.0)
        self.assertAlmostEqual(h.shield, 10.0 * config.DAYBREAK)
        self.assertAlmostEqual(h.hp, h.max_hp - 20)
        h.heal(1000.0)                                  # (past full: Aegis, up to its cap)
        self.assertAlmostEqual(h.shield, h.max_hp * config.AEGIS_MAX)

    def test_not_without_the_trick(self):
        s, h = self.setup("aegis", "epic")
        h.shield = 0.0
        h.hp = h.max_hp - 30
        h.heal(10.0)
        self.assertEqual(h.shield, 0.0)


class EverBurningTest(_Legend):
    def test_a_used_rise_comes_back(self):
        s, h = self.setup("phoenix")
        p = s.me
        h.hp = 0.0
        self.assertTrue(s.rules.revive(p))
        self.assertEqual(p.phoenix_used, 1)
        self.assertEqual(s._meter(h)[0], "PHX")          # (the HUD shows it coming back)
        for i in range(config.EVER_BURNING - 1):
            s.rules.on_kill(p, plain(30.0, 30.5))
        self.assertEqual(p.phoenix_used, 1)
        self.assertAlmostEqual(s._meter(h)[1], (config.EVER_BURNING - 1) / config.EVER_BURNING)
        s.rules.on_kill(p, plain(30.0, 30.5))
        self.assertEqual(p.phoenix_used, 0)
        self.assertIsNone(s._meter(h))
        h.hp = 0.0
        self.assertTrue(s.rules.revive(p))               # (it rises again)

    def test_once_without_it(self):
        s, h = self.setup("phoenix", "epic")
        p = s.me
        h.hp = 0.0
        s.rules.revive(p)
        for i in range(config.EVER_BURNING + 5):
            s.rules.on_kill(p, plain(30.0, 30.5))
        self.assertEqual(p.phoenix_used, 1)


class StormsMarkTest(_Legend):
    def dart(self):
        p = self.shot(damage=5.0)
        p.group = {}
        return p

    def test_a_marked_enemy_fires_a_dart_whatever_kills_it(self):
        s, h = self.setup("arcane_storm")
        marked, next_one = self.place(plain(23.0, 20.5), plain(26.0, 20.5))
        combat._hit_actor(self.dart(), marked, marked.x, marked.y, s.world, s._actors(),
                          s.effects, [], s.zones, s.projectiles)
        self.assertTrue(marked.alive)
        s.projectiles.clear()
        marked.hp = 0.0                                  # (a burn, a wolf...)
        s.rules.on_death(marked)
        self.assertEqual(len(s.projectiles), 1)
        self.assertIs(s.projectiles[0].seek, next_one)

    def test_the_mark_wears_off(self):
        s, h = self.setup("arcane_storm")
        marked = self.place(plain(23.0, 20.5), plain(26.0, 20.5))[0]
        combat._hit_actor(self.dart(), marked, marked.x, marked.y, s.world, s._actors(),
                          s.effects, [], s.zones, s.projectiles)
        s.projectiles.clear()
        h.time += config.STORMS_MARK + 0.1
        marked.hp = 0.0
        s.rules.on_death(marked)
        self.assertEqual(s.projectiles, [])

    def test_a_darts_own_kill_isnt_counted_twice(self):
        s, h = self.setup("arcane_storm")
        marked = self.place(plain(23.0, 20.5, 3.0), plain(26.0, 20.5))[0]
        spawned = []
        combat._hit_actor(self.dart(), marked, marked.x, marked.y, s.world, s._actors(),
                          s.effects, spawned, s.zones, s.projectiles)
        self.assertEqual(len(spawned), 1)                # (Arcane Storm's own)
        s.projectiles.clear()
        s.rules.on_death(marked)
        self.assertEqual(s.projectiles, [])

    def test_not_without_the_trick(self):
        s, h = self.setup("arcane_storm", "epic")
        marked = self.place(plain(23.0, 20.5), plain(26.0, 20.5))[0]
        combat._hit_actor(self.dart(), marked, marked.x, marked.y, s.world, s._actors(),
                          s.effects, [], s.zones, s.projectiles)
        s.projectiles.clear()
        marked.hp = 0.0
        s.rules.on_death(marked)
        self.assertEqual(s.projectiles, [])


class DustDevilTest(_Legend):
    def throw(self):
        h = self.h
        axe = self.shot(x=h.x + 6.0)
        axe.travelled = axe.max_range = 6.0
        combat._turn_back(axe, [])
        return axe

    def home(self, axe):
        """Fly the axe until it's caught (before Cyclone's rethrow flies)."""
        s, shots = self.s, [axe]
        for _ in range(240):
            combat.update_projectiles(shots, s.world, s.effects, DT, s._actors(), s.zones)
            if not axe.alive:
                return
        self.fail("the axe never came home")

    def test_the_axe_leaps_before_coming_home(self):
        s, h = self.setup("cyclone")
        aside = self.place(plain(h.x + 6.0, h.y + 3.5))[0]   # (off its way home)
        self.home(self.throw())
        self.assertLess(aside.hp, BASE)

    def test_it_skips_what_it_hit_on_the_way_out(self):
        s, h = self.setup("cyclone")
        hit, other = self.place(plain(h.x + 6.2, h.y), plain(h.x + 6.0, h.y + 4.0))
        axe = self.shot(x=h.x + 6.0)
        axe.travelled = axe.max_range = 6.0
        axe.hit.add(id(hit))
        combat._turn_back(axe, [])
        combat._fly_back(axe, combat.ActorGrid([]), s.world, s.effects, DT, s._actors(), [])
        self.assertIs(axe.devil, other)

    def test_straight_home_without_it(self):
        s, h = self.setup("cyclone", "epic")
        aside = self.place(plain(h.x + 6.0, h.y + 3.5))[0]
        self.home(self.throw())
        self.assertEqual(aside.hp, BASE)


class FarsightTest(_Legend):
    def test_the_view_leans_toward_the_aim(self):
        s, h = self.setup("deadeye")
        h.aim_point = (h.x + 100.0, h.y)
        most, share = config.FARSIGHT
        self.assertEqual(combat.farsight_lean(h, 60.0, 30.0), (most * 60.0, 0.0))
        h.aim_point = (h.x + 10.0, h.y - 4.0)
        lx, ly = combat.farsight_lean(h, 60.0, 30.0)
        self.assertAlmostEqual(lx, 10.0 * share)
        self.assertAlmostEqual(ly, -4.0 * share)
        s, h = self.setup("deadeye", "epic")
        h.aim_point = (h.x + 100.0, h.y)
        self.assertEqual(combat.farsight_lean(h, 60.0, 30.0), (0.0, 0.0))

    def test_the_game_leans_its_camera(self):
        m, s = game("huntress")
        wear(s, "deadeye", 0)
        h = s.hero
        for _ in range(240):
            s.update(1 / 60)                             # (the mouse aims: a corner)
        cam = s.me.camera
        w, hh = cam.view_w / cam.tile_w, cam.view_h / cam.tile_h
        lx, ly = combat.farsight_lean(h, w, hh)
        self.assertGreater(math.hypot(lx, ly), 5.0)
        self.assertAlmostEqual(cam.x, h.x + lx, delta=1.0)
        self.assertAlmostEqual(cam.y, h.y + ly, delta=1.0)
        self.assertEqual(h.view_box[:2], (cam.x, cam.y))

    def test_crit_arrows_fly_to_the_edge_of_the_view(self):
        s, h = self.setup("deadeye")
        h.view_box = (h.x + 60.0, h.y, 70.0, 15.0)       # (the view ends 130 tiles to the right)
        h.last_crit = True
        p = self.shot(x=h.x + 2.0)
        p.travelled = 2.0
        victim = self.place(plain(h.x + 2.0, h.y))[0]
        combat._capstones(p, victim, victim.x, victim.y, h, h.stats, [], s.zones)
        self.assertAlmostEqual(p.max_range, 2.0 + 128.0)
        s, h = self.setup("deadeye", "epic")
        h.view_box = (h.x + 60.0, h.y, 70.0, 15.0)
        h.last_crit = True
        p = self.shot(x=h.x + 2.0)
        combat._capstones(p, victim, victim.x, victim.y, h, h.stats, [], s.zones)
        self.assertAlmostEqual(p.max_range, p.spec.max_range * 2)


class PrismWardTest(_Legend):
    def color(self, variant=0):
        h = self.h
        p = Projectile(h.x + 1.0, h.y, 0.0, config.WEAPONS["rainbow"].shell, owner=h, damage=8.0)
        p.tags, p.variant = ("projectile", "arcane"), variant
        return p

    def enemy_shot(self, x):
        shooter = plain(self.h.x + 20.0, self.h.y)
        return Projectile(x, self.h.y, math.pi, config.SPELL_SHELLS["note"], owner=shooter)

    def test_a_color_splits_an_enemy_shot_into_three(self):
        s, h = self.setup("refraction")
        mine, bad = self.color(variant=1), self.enemy_shot(h.x + 3.0)
        shots = [mine, bad]
        self.fly(shots, 0.2)
        self.assertNotIn(bad, shots)
        self.assertNotIn(mine, shots)                     # (the colour is spent)
        pieces = [q for q in shots if q.owner is h]
        self.assertEqual(len(pieces), config.PRISM_WARD)
        self.assertEqual(sorted(q.variant for q in pieces), [1, 2, 3])
        self.assertTrue(all(q.refracted == 1 for q in pieces))   # (they don't ward again)

    def test_not_without_the_trick(self):
        s, h = self.setup("refraction", "epic")
        mine, bad = self.color(), self.enemy_shot(h.x + 3.0)
        shots = [mine, bad]
        self.fly(shots, 0.2)
        self.assertEqual([q for q in shots if q.owner is h], [mine])   # (no pieces)


class BigFinishTest(_Legend):
    def beat(self, finale=False):
        s, h = self.s, self.h
        kw = {"mult": config.GRAND_FINALE[1], "reach": config.GRAND_FINALE[2]} if finale \
            else {"mult": 1.0, "reach": 1.0}
        h.finale_now = finale
        return combat.pulse(h, s.world, s._actors(), s.effects, kw["mult"], kw["reach"])

    def test_beats_bank_and_the_finale_lets_it_go(self):
        s, h = self.setup("grand_finale")
        a, b = self.place(plain(22.0, 20.5), plain(20.5, 22.0))
        self.beat()
        dealt = (BASE - a.hp) + (BASE - b.hp)
        self.assertAlmostEqual(h.bank, dealt * config.BIG_FINISH)
        self.beat()
        bank = h.bank
        before = a.hp
        self.beat(finale=True)
        got = before - a.hp
        self.assertEqual(h.bank, 0.0)
        # The same finale with nothing banked, on two fresh enemies: each
        # took half the bank more.
        a2, b2 = plain(22.0, 20.5), plain(20.5, 22.0)
        s.enemies[:] = [a2, b2]
        self.beat(finale=True)
        self.assertAlmostEqual(got, (BASE - a2.hp) + bank / 2)

    def test_a_finale_that_hits_nothing_keeps_the_bank(self):
        s, h = self.setup("grand_finale")
        h.bank = 50.0
        self.beat(finale=True)
        self.assertEqual(h.bank, 50.0)

    def test_the_finale_flag_comes_from_the_beat_count(self):
        s, h = self.setup("grand_finale")
        h.attacks = config.GRAND_FINALE[0] - 1
        s.rules.attack_mods(s.me)
        self.assertTrue(h.finale_now)

    def test_not_without_the_trick(self):
        s, h = self.setup("grand_finale", "epic")
        self.place(plain(22.0, 20.5))
        self.beat()
        self.assertEqual(getattr(h, "bank", 0.0), 0.0)


if __name__ == "__main__":
    unittest.main()
