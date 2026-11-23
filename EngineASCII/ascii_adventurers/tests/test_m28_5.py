"""M28.5: the boss uniques (design/GEAR.md 21). 5a: the framework and the
swamp's eight relics; 5b: the desert's six and the ruins' eight; 5c: the
forest's seven, Mycelium's six and the necromancer's three."""

import math
import os
import unittest
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from ascii_adventurers import config
from ascii_adventurers.entities.projectile import Projectile
from ascii_adventurers.meta.guild import Guild
from ascii_adventurers.players import gear
from ascii_adventurers.players.gear import Equipment, draw_drop, draw_offer, eligible, unique_piece
from ascii_adventurers.players.stats import HeroStats
from ascii_adventurers.ai.brain import AIContext, Brain
from ascii_adventurers.systems import combat, relics, roll, statuses
from ascii_adventurers.systems.zones import update_zones
from ascii_adventurers.world import tiles
from ascii_adventurers.systems.statuses import inflict
from ascii_adventurers.tests.test_m16 import game
from ascii_adventurers.tests.test_m28_2a import foe, wear
from ascii_adventurers.tests.test_m28_2c import DT, _Case
from ascii_adventurers.tests.test_players import make_manager
from ascii_adventurers.ui.gear_screen import piece_lines
from ascii_adventurers.ui.guild_panel import SHELVES, GuildPanel

SWAMP = {"froggy": ("tongue_lasher", "bubble_belt", "frogskin_boots"),
         "leech_swamp": (), "leech_swarm": ("leechskin", "latch_hood", "bloated_charm"),
         "proboscia": ("proboscis_ring", "engorged_mantle")}
DESERT_RUINS = {"khepri": ("dung_ball", "scarab_carapace"),
                "ol_spitter": ("spittoon", "hump_pack"),
                "nameless_magus": ("hourglass_ring", "sand_slippers"),
                "fallout_king": ("lead_apron", "geiger_ring", "rod_of_fission"),
                "snow_king": ("black_ice_crown", "hermits_furs"),
                "fragile": ("parasol", "mr_buttons", "bat_form")}
LAST = {"nettle": ("shrinking_dust", "blight_thorn_ring"),
        "love_cuddles": ("cleaver_of_cuddles", "acorn_bandolier", "tripwire_boots"),
        "the_fallen": ("rootbound_boots", "heartwood_ring"),
        "mycelium_amanita": ("mycelial_ring", "fly_agaric_cap"),
        "mycelium_inkcap": ("inkwell_charm", "lawyers_wig"),
        "mycelium_puffball": ("puffball_sandals", "spore_wind_band"),
        "necromancer": ("phylactery", "lichs_gaze", "corpse_candle")}
WIZ = config.WEAPONS[config.HEROES["wizard"].weapon]
BASE = 1000.0


def uniques():
    return [k for k, g in config.GEAR.items() if g.unique is not None]


def mover(x, y, hp=BASE):
    """A Dummy that combat.push can move (a body and a walking speed)."""
    d = foe(x, y, hp)
    d.half = 8.0
    d.espec = SimpleNamespace(speed=3.0, elite=False, xp=1, name="dummy")
    return d


class FrameworkTest(unittest.TestCase):
    def test_the_swamp_relics_are_defined(self):
        self.assertEqual(config.BOSS_UNIQUES["froggy"], SWAMP["froggy"])
        self.assertEqual(config.BOSS_UNIQUES["leech_swarm"], SWAMP["leech_swarm"])
        self.assertEqual(config.BOSS_UNIQUES["proboscia"], SWAMP["proboscia"])
        for key in uniques():
            g, c = config.GEAR[key], config.CARDS[key]
            self.assertEqual(c.rarity, "legendary", key)
            self.assertEqual(c.unlock, f"U:{g.unique}", key)
            self.assertIn(g.unique, config.BOSSES, key)
            self.assertNotEqual(g.slot, "main", key)
            self.assertEqual(len(g.affixes), 3, key)
            self.assertEqual(len(set(g.affixes)), 3, key)
            for a in g.affixes:
                self.assertIn(a, config.AFFIXES, (key, a))
                self.assertTrue(gear.affix_text(a, "legendary"), (key, a))
            self.assertIn((key, "flag", 1), c.mods)
            self.assertTrue(any(op == "power" for _, op, _ in c.mods), key)
            self.assertEqual(c.max_stacks, 1)
            self.assertTrue(gear.is_unique(key))
        self.assertFalse(gear.is_unique("seeker"))
        slots = {}
        for key in uniques():                          # different slots per boss
            g = config.GEAR[key]
            self.assertNotIn(g.slot, slots.setdefault(g.unique, set()), key)
            slots[g.unique].add(g.slot)

    def test_never_offered_never_dropped(self):
        eq = Equipment()
        pool = eligible("wizard", WIZ, eq, HeroStats(), level=30)
        for key in uniques():
            self.assertNotIn(key, pool)
        seen = set()
        for n in range(1, 120):
            seen.update(o.key for o in draw_offer("wizard", WIZ, eq, 9, 0, n, HeroStats(), level=20))
            p = draw_drop("wizard", WIZ, eq, 9, 0, 0xD000 + n, HeroStats(), luck=50)
            seen.add(p.key)
        self.assertFalse(seen & set(uniques()))
        g = Guild()
        for key in uniques():
            self.assertFalse(g.unlocked(key))
            self.assertNotIn(key, g.unlocked_cards())

    def test_the_piece_its_numbers_and_its_card(self):
        p = unique_piece("tongue_lasher")
        self.assertEqual((p.rarity, p.level, p.affixes), ("legendary", 0, ("long_reach", "quick_hands", "brutal")))
        steps = gear.power_steps("tongue_lasher", 3, "legendary")
        self.assertIn(("tongue_lasher", "flag", 1), steps)
        power = [v for st, op, v in steps if op == "power"][0]
        self.assertAlmostEqual(power, 7.0 * 1.3)             # (+10% a level, no rarity x)
        self.assertIn("(power +30%)", gear.power_text("tongue_lasher", 3, "legendary"))
        self.assertNotIn("power", gear.power_text("tongue_lasher", 0, "legendary"))
        self.assertEqual(gear.next_level_text("tongue_lasher", 0, "legendary"), "power +10%")
        self.assertEqual(gear.boss_of("leechskin"), config.BOSSES["leech_swarm"].name)
        lines = [ln for ln, _ in piece_lines("bubble_belt", "legendary", 0, p.affixes, 40)]
        self.assertIn("UNIQUE: Froggy McFrogface", lines)
        self.assertFalse(any("LEGENDARY" in ln for ln in lines[3:]))   # (no extra trick)
        eq = Equipment()
        eq.stash(p)
        st = HeroStats()
        st = __import__("ascii_adventurers.players.stats", fromlist=["apply_mods"]).apply_mods(
            st, gear.power_steps("tongue_lasher", 1, "legendary"))
        self.assertTrue(st.has("tongue_lasher"))
        self.assertAlmostEqual(st.uniques["tongue_lasher"], 7.7)

    def test_the_guild_remembers_and_the_shelf_shows(self):
        g = Guild()
        g.uniques.add("leechskin")
        g.uniques.add("not_a_key")
        path = os.path.join(os.environ.get("TMPDIR", "/tmp"), "m28_5_guild_test.json")
        g.save(path)
        back = Guild.load(path)
        self.assertEqual(back.uniques, {"leechskin"})
        os.remove(path)
        self.assertIn("relics", SHELVES)
        m = make_manager()
        panel = GuildPanel(m, back, "archive", "wizard")
        panel.shelf = SHELVES.index("relics")
        rows = {r.key: r for r in panel.rows()}
        self.assertEqual(set(rows), set(uniques()))
        self.assertEqual(rows["leechskin"].state, "FOUND")
        self.assertEqual(rows["leechskin"].name, "Leechskin")
        self.assertEqual(rows["tongue_lasher"].name, "???")
        self.assertFalse(panel.buy(list(rows).index("leechskin")))
        panel.draw(m.text) if hasattr(panel, "draw") else None


class DropTest(unittest.TestCase):
    def test_a_boss_drops_one_relic_once_a_run(self):
        m, s = game("wizard", seed=31)
        p = s.me
        h = s.hero
        d = s._drop_unique(p, "froggy", h.x + 2, h.y)
        self.assertIsNotNone(d)
        self.assertIn(d.piece.key, SWAMP["froggy"])
        self.assertEqual(d.piece.rarity, "legendary")
        self.assertEqual(d.piece.affixes, config.GEAR[d.piece.key].affixes)
        self.assertIsNone(s._drop_unique(p, "froggy", h.x + 2, h.y))
        self.assertIsNotNone(s._drop_unique(p, "proboscia", h.x + 2, h.y))
        m2, s2 = game("wizard", seed=31)
        d2 = s2._drop_unique(s2.me, "froggy", h.x + 2, h.y)
        self.assertEqual(d2.piece.key, d.piece.key)             # (seeded)
        self.assertTrue(any(e.kind == "toast" and e.label.startswith("RELIC") for e in s.effects))
        # Picking it up records it for the archive's relics shelf.
        s._found_action(p, ("found", d.id, "take", None, None))
        self.assertIn(d.piece.key, m.app.guild.uniques)
        self.assertIsNotNone(p.progress.gear.wearing(d.piece.key))
        self.assertTrue(s.hero.stats.has(d.piece.key))

    def test_a_win_lays_the_relic_by_the_body(self):
        m, s = game("wizard", seed=31)
        st = next(q for q in s.quests.states.values() if q.spec.boss == "froggy")
        h = s.hero
        st.stage = "fight"
        st.fight_time = 12.0
        st.boss = SimpleNamespace(x=h.x + 3, y=h.y, espec=config.ENEMIES["froggy"], alive=False,
                                  max_hp=100, level=1)
        s.quests._win(st, s.me)
        self.assertEqual(len(s.drops), 1)
        self.assertIn(s.drops[0].piece.key, SWAMP["froggy"])
        self.assertIn("froggy", s.me.uniques_dropped)


class _Relic(_Case):
    def setup(self, key, hero="wizard", walls=()):
        s, h = super().setup(key, 0, hero, walls)
        self.assertEqual(s.me.progress.gear.worn[s.me.progress.gear.wearing(key)].rarity, "legendary")
        self.assertTrue(h.stats.has(key))
        h.time = 100.0
        return s, h


class SwampTest(_Relic):
    def test_tongue_lasher_pulls_the_first_enemy_on_the_line(self):
        s, h = self.setup("tongue_lasher")
        near = mover(26.5, 20.5)
        far = mover(24.5, 26.0)                        # (off the line)
        self.place(near, far)
        s.rules._tongue(s.me, 0.0)
        self.assertLess(near.x, 23.0)
        self.assertEqual(far.y, 26.0)
        self.assertTrue(any(e.kind == "arc" for e in s.effects))
        # Every 6th attack, through patterns().
        near.x = 26.5
        h.attacks = 3                                    # (attack_mods counts the attack)
        s.rules.patterns(s.me, s.rules.attack_mods(s.me))
        self.assertEqual(near.x, 26.5)
        h.attacks = 5
        s.rules.patterns(s.me, s.rules.attack_mods(s.me))
        self.assertLess(near.x, 23.0)

    def test_bubble_belt_bounces_shots_back(self):
        s, h = self.setup("bubble_belt")
        e = self.place(foe(26.5, 20.5, BASE))[0]
        hp = h.hp
        h.take_damage(10, e, math.pi)
        self.assertLess(h.hp, hp)
        self.assertAlmostEqual(h.bubble, 1.0)
        shell = config.WEAPONS["cactus_spines"].shell
        q = Projectile(h.x + 1.0, h.y, math.pi, shell, owner=e, damage=10)
        s.projectiles.append(q)
        hp = h.hp
        self.go(0.2)
        self.assertEqual(h.hp, hp)                      # (bounced off)
        self.assertIs(q.owner, h)
        self.assertGreater(q.dir_x, 0)
        s.rules.tick(s.me, 1.1)
        self.assertEqual(h.bubble, 0.0)
        h.take_damage(10, e, math.pi)                  # (within 8 s: no new bubble)
        self.assertEqual(h.bubble, 0.0)
        h.time += config.U_BUBBLE
        h.take_damage(10, e, math.pi)
        self.assertGreater(h.bubble, 0)

    def test_frogskin_boots_leap_and_splash(self):
        s, h = self.setup("frogskin_boots")
        e = self.place(mover(22.0, 20.5))[0]
        roll.start(s, s.me, 1.0, 0.0)
        self.assertAlmostEqual(h.roll_speed, config.ROLL_DISTANCE / config.ROLL_TIME * 1.5)
        h.roll_t = 0.0
        roll._ended(s, s.me)
        self.assertGreater(e.x, 22.5)
        self.assertTrue(any(ef.kind == "nova" for ef in s.effects))

    def test_leechskin_drinks_a_fifth_back(self):
        s, h = self.setup("leechskin")
        e = self.place(foe(30.5, 20.5, BASE))[0]
        h.hp = h.max_hp
        h.take_damage(50, e, None)
        after = h.hp
        self.assertAlmostEqual(h.leech[0], 10.0)
        for _ in range(60):
            s.rules.tick(s.me, DT)
        self.assertAlmostEqual(h.hp, after + 2.0, delta=0.3)
        h.take_damage(20, e, None)                      # (a new hit: the old leeches let go)
        self.assertAlmostEqual(h.leech[0], 4.0)
        for _ in range(600):
            s.rules.tick(s.me, DT)
        self.assertIsNone(h.leech)

    def test_latch_hood_bleeds_the_fifth_hit_in_a_row(self):
        s, h = self.setup("latch_hood")
        a = self.place(foe(24.5, 20.5, BASE))[0]
        b = self.place(foe(24.5, 23.5, BASE))[0]
        for _ in range(4):
            combat.strike(a, 10, h, 0.0, s.effects)
        self.assertIsNone(getattr(a, "latched", None))
        combat.strike(b, 10, h, 0.0, s.effects)        # (another enemy: the row restarts)
        for _ in range(4):
            combat.strike(a, 10, h, 0.0, s.effects)
        self.assertIsNone(getattr(a, "latched", None))
        combat.strike(a, 10, h, 0.0, s.effects)
        self.assertIs(a.latched, h)
        hp = a.hp
        for _ in range(72):                              # (bites at 0.5 and 1.0 s)
            s.rules.status_tricks(DT)
        self.assertAlmostEqual(hp - a.hp, 30.0, delta=2.0)   # 3% of 1000 a second
        a.x = 60.5                                       # out of sight
        s.rules.status_tricks(DT)
        self.assertIsNone(a.latched)

    def test_bloated_charm_drains_the_last_enemy_hit(self):
        s, h = self.setup("bloated_charm")
        e = self.place(foe(24.5, 20.5, BASE))[0]
        combat.strike(e, 10, h, 0.0, s.effects)
        self.assertIs(h.leech_target, e)
        h.hp = 50.0
        hp = e.hp
        for _ in range(72):                              # (bites at 0.5 and 1.0 s)
            s.rules.tick(s.me, DT)
        self.assertAlmostEqual(hp - e.hp, 20.0, delta=2.0)   # 2% of 1000 a second
        self.assertAlmostEqual(h.hp, 60.0, delta=1.2)
        e.hp = 0
        s.rules.tick(s.me, DT)
        self.assertIsNone(h.leech_target)

    def test_proboscis_ring_sips_bleeding_enemies(self):
        s, h = self.setup("proboscis_ring")
        e = self.place(foe(24.5, 20.5, BASE))[0]
        h.hp = 50.0
        combat.strike(e, 10, h, 0.0, s.effects)
        self.assertEqual(h.hp, 50.0)                    # (not bleeding)
        inflict(e, "bleed", h)
        combat.strike(e, 10, h, 0.0, s.effects)
        self.assertEqual(h.hp, 51.0)
        combat.strike(e, 10, h, 0.0, s.effects)
        self.assertEqual(h.hp, 51.0)                    # (once a second)
        h.time += 1.0
        combat.strike(e, 10, h, 0.0, s.effects)
        self.assertEqual(h.hp, 52.0)

    def test_engorged_mantle_grows_with_healing_and_bleeds_out(self):
        s, h = self.setup("engorged_mantle")
        e = self.place(foe(24.5, 20.5, BASE))[0]
        h.hp = 20.0
        h.heal(25.0)
        self.assertAlmostEqual(h.engorged, 0.05)
        self.assertGreaterEqual(combat.situational_bonus(h.stats, h, e), 0.05)
        for _ in range(10):
            h.hp = 20.0
            h.heal(50.0)
        self.assertAlmostEqual(h.engorged, 0.30)         # (the cap)
        h.take_damage(5, e, None)
        self.assertEqual(h.engorged, 0.0)

    def test_the_marks_draw(self):
        s, h = self.setup("bubble_belt")
        wear(s, "bloated_charm", 0)
        e = self.place(foe(24.5, 20.5, BASE))[0]
        h.bubble = 1.0
        h.leech_target = e
        s.players[0].minimap = None                      # (an open test map: no island maps)
        s.draw(s.manager.text)


class DesertTest(_Relic):
    def test_the_desert_and_ruins_relics_are_defined(self):
        for boss, keys in DESERT_RUINS.items():
            self.assertEqual(config.BOSS_UNIQUES[boss], keys)
        self.assertEqual(config.WEAPONS["spittoon_glob"].shell.bounces, config.U_SPITTOON[2])

    def test_dung_ball_rolls_flattens_grows_and_bursts(self):
        s, h = self.setup("dung_ball", walls=[(34, y) for y in range(10, 30)])
        weak = self.place(foe(24.5, 20.5, 5))[0]
        tough = self.place(foe(28.5, 20.5, BASE))[0]
        s.rules.tick(s.me, DT)
        b = h.ball
        self.assertIsNotNone(b)
        self.assertAlmostEqual(b.angle, 0.0)
        for _ in range(60):
            s.rules.tick(s.me, DT)
        self.assertFalse(weak.alive)
        self.assertAlmostEqual(b.damage, 10.0 + config.U_DUNG_BALL[2])     # (it grew)
        self.assertAlmostEqual(b.radius, config.U_DUNG_BALL[1] + config.U_DUNG_BALL[3])
        for _ in range(60):
            s.rules.tick(s.me, DT)
        self.assertLess(tough.hp, BASE)
        for _ in range(120):
            s.rules.tick(s.me, DT)
        self.assertFalse(b.alive)                                    # (the wall)
        self.assertLess(b.x, 34.0)
        self.assertGreater(h.ball_t, 0)
        for _ in range(round(config.U_DUNG_BALL[7] * 60) + 2):
            s.rules.tick(s.me, DT)
        self.assertIsNot(h.ball, b)                                  # (a new one)

    def test_scarab_carapace_halves_hits_from_behind(self):
        s, h = self.setup("scarab_carapace")
        e = self.place(foe(18.5, 20.5, BASE))[0]
        front = h.take_damage(20, e, math.pi)          # (flying -x: from ahead)
        back = h.take_damage(20, e, 0.0)               # (flying +x: from behind)
        self.assertAlmostEqual(back, front * 0.5)

    def test_spittoon_spits_a_ricocheting_glob(self):
        s, h = self.setup("spittoon")
        s.rules.tick(s.me, DT)
        self.assertEqual(s.projectiles, [])             # (nobody near)
        e = self.place(foe(25.5, 20.5, BASE))[0]
        s.rules.tick(s.me, DT)
        q = s.projectiles[-1]
        self.assertIs(q.owner, h)
        self.assertEqual(q.spec.bounces, 3)
        self.assertEqual(q.damage, 20.0)
        self.assertAlmostEqual(q.angle, 0.0, places=3)
        n = len(s.projectiles)
        s.rules.tick(s.me, DT)
        self.assertEqual(len(s.projectiles), n)         # (every 4 s)

    def test_hump_pack_fires_two_bouncing_shots_behind(self):
        s, h = self.setup("hump_pack", hero="huntress", walls=[(15, y) for y in range(10, 30)])
        h.attacks = 3                                    # (attack_mods counts the attack)
        s.rules.patterns(s.me, s.rules.attack_mods(s.me))
        self.assertFalse(any(q.free_bounces for q in s.projectiles))
        h.attacks = 9
        s.rules.patterns(s.me, s.rules.attack_mods(s.me))
        back = [q for q in s.projectiles if q.free_bounces]
        self.assertEqual(len(back), 2)
        for q in back:
            self.assertGreater(abs(math.cos(q.angle) + 1), -1e-9)
            self.assertLess(math.cos(q.angle), -0.9)            # (behind: -x)
        s.projectiles[:] = back
        for _ in range(60):
            combat.update_projectiles(s.projectiles, s.world, s.effects, DT, s._actors(), s.zones)
        self.assertTrue(all(q.bounces == 1 for q in back))
        self.assertTrue(all(q.dir_x > 0 for q in back if q.alive))

    def test_hourglass_ring_slows_enemy_shots_near(self):
        s, h = self.setup("hourglass_ring")
        e = self.place(foe(40.5, 20.5, BASE))[0]
        s.rules.tick(s.me, DT)
        self.assertEqual(h.hourglass_t, 0.0)            # (waits for a shot near)
        near = Projectile(h.x + 4.0, h.y, math.pi, config.WEAPONS["cactus_spines"].shell, owner=e)
        mine = Projectile(h.x + 1.0, h.y, 0.0, config.WEAPONS["cactus_spines"].shell, owner=h)
        s.projectiles += [near, mine]
        s.rules.tick(s.me, DT)
        s.rules.tick(s.me, DT)
        self.assertGreater(h.hourglass_t, 1.9)
        self.assertAlmostEqual(near.time_scale, config.U_HOURGLASS[2])
        self.assertEqual(mine.time_scale, 1.0)
        for _ in range(130):
            s.rules.tick(s.me, DT)
        self.assertEqual(near.time_scale, 1.0)
        self.assertGreater(h.hourglass_cd, config.U_HOURGLASS[0] - 2.5)

    def test_sand_slippers_raise_a_dune_that_stops_shots(self):
        s, h = self.setup("sand_slippers")
        roll.start(s, s.me, 1.0, 0.0)
        heaps = [(tx, ty) for tx in range(18, 23) for ty in range(17, 24)
                 if s.world.tile_at(tx, ty) is tiles.SAND_HEAP]
        self.assertEqual(sorted(heaps), [(20, 19), (20, 20), (20, 21)])
        self.assertFalse(tiles.SAND_HEAP.solid)
        e = self.place(foe(15.5, 20.5, BASE))[0]
        q = Projectile(17.0, 20.5, 0.0, config.WEAPONS["cactus_spines"].shell, owner=e)
        s.projectiles.append(q)
        for _ in range(20):
            combat.update_projectiles(s.projectiles, s.world, s.effects, DT, s._actors(), s.zones)
        self.assertFalse(q.alive)
        self.assertLess(q.x, 20.5)
        for _ in range(round(2.0 * 60) + 2):
            s.rules.tick(s.me, DT)
        self.assertIsNot(s.world.tile_at(20, 20), tiles.SAND_HEAP)
        self.assertEqual(h.dunes, [])


class RuinsTest(_Relic):
    def test_lead_apron_braces_you_standing_still(self):
        s, h = self.setup("lead_apron")
        e = self.place(foe(24.5, 20.5, BASE))[0]
        h.still_t = 0.0
        moving = h.take_damage(20, e, None)
        h.still_t = 1.0
        braced = h.take_damage(20, e, None)
        self.assertAlmostEqual(braced, moving * 0.6)

    def test_geiger_ring_irradiates_enemies_near(self):
        s, h = self.setup("geiger_ring")
        near = self.place(foe(23.5, 20.5, BASE))[0]
        far = self.place(foe(30.5, 20.5, BASE))[0]
        for _ in range(61):                            # (dealt every 0.5 s)
            s.rules.tick(s.me, DT)
        self.assertAlmostEqual(BASE - near.hp, 10.0, delta=0.5)        # 1% a second
        self.assertEqual(far.hp, BASE)
        boss = self.place(foe(22.5, 21.5, BASE))[0]
        boss.boss = True
        for _ in range(60):
            s.rules.tick(s.me, DT)
        self.assertAlmostEqual(BASE - boss.hp, 2.0, delta=0.4)         # 0.2% for bosses

    def test_rod_of_fission_pulses_and_irradiates(self):
        s, h = self.setup("rod_of_fission")
        e = self.place(foe(22.5, 20.5, BASE))[0]
        other = self.place(foe(40.5, 20.5, BASE))[0]
        s.rules.tick(s.me, DT)
        self.assertEqual(h.rod[:2], [h.x, h.y])
        for _ in range(round(config.U_FISSION[0] * 60) + 1):
            s.rules.tick(s.me, DT)
        self.assertLess(e.hp, BASE)
        self.assertEqual(other.hp, BASE)
        self.assertGreater(e.fissioned, h.time)
        a = combat.strike(e, 100, h, 0.0, s.effects)
        b = combat.strike(other, 100, h, 0.0, s.effects)
        self.assertAlmostEqual(a, b * 1.1)
        h.x += 9.0
        s.rules.tick(s.me, DT)
        self.assertAlmostEqual(h.rod[0], h.x)                         # (replanted)

    def test_crown_of_black_ice_leaves_ice_that_chills(self):
        s, h = self.setup("black_ice_crown")
        self.assertIn(("chill", "status", 1), config.GEAR["black_ice_crown"].mods)
        e = self.place(foe(24.5, 20.5, BASE))[0]
        inflict(e, "chill", h)
        s.rules.tick(s.me, DT)
        e.x += 0.6
        s.rules.tick(s.me, DT)
        ice = [z for z in s.zones if z.kind == "black_ice"]
        self.assertEqual(len(ice), 1)
        self.assertAlmostEqual(ice[0].life, 3.0)
        other = self.place(foe(ice[0].x, ice[0].y, BASE))[0]
        for _ in range(61):
            update_zones(s.zones, s._actors(), s.effects, DT, s.world)
        self.assertTrue(other.status is not None and other.status.has("chill"))
        for _ in range(60):                            # (a long walk: the oldest melt)
            e.x += 0.6
            s.rules.tick(s.me, DT)
            update_zones(s.zones, s._actors(), s.effects, 0.0, s.world)
        self.assertLessEqual(len([z for z in s.zones if z.kind == "black_ice"]), config.U_BLACK_ICE[3])

    def test_hermits_furs_freeze_the_next_attacker(self):
        s, h = self.setup("hermits_furs")
        e = self.place(foe(22.5, 20.5, BASE))[0]
        for _ in range(60):
            s.rules.tick(s.me, DT)
        self.assertFalse(h.frost)
        for _ in range(62):
            s.rules.tick(s.me, DT)
        self.assertTrue(h.frost)
        h.take_damage(5, e, None)
        self.assertAlmostEqual(e.status.frozen, 3.0)
        self.assertFalse(h.frost)
        boss = self.place(foe(22.5, 22.5, BASE))[0]
        boss.boss = True
        h.frost = True
        h.take_damage(5, boss, None)
        self.assertAlmostEqual(boss.status.frozen, config.U_HERMITS_FURS[1])

    def test_lace_parasol_blocks_shots_from_ahead_while_attacking(self):
        s, h = self.setup("parasol")
        e = self.place(foe(30.5, 20.5, BASE))[0]
        shell = config.WEAPONS["cactus_spines"].shell

        def shot(x, angle):
            s.projectiles[:] = [Projectile(x, h.y, angle, shell, owner=e, damage=10)]
            hp = h.hp
            for _ in range(20):
                combat.update_projectiles(s.projectiles, s.world, s.effects, DT, s._actors(), s.zones)
            return hp - h.hp

        h.trigger = True
        self.assertEqual(shot(h.x + 1.5, math.pi), 0.0)              # (from ahead: blocked)
        self.assertGreater(shot(h.x - 1.5, 0.0), 0.0)                # (from behind: hits)
        h.trigger = False
        self.assertGreater(shot(h.x + 1.5, math.pi), 0.0)            # (not held up)

    def test_mr_buttons_follows_draws_fire_and_gets_up(self):
        s, h = self.setup("mr_buttons")
        s.rules.tick(s.me, DT)
        b = h.bear
        self.assertEqual(b.max_hp, 200)
        self.assertIn(b, s._images())
        self.assertIn(b, s._actors())
        ctx = AIContext(world=s.world, actors=s._actors(), projectiles=[], effects=[], players=[h],
                        decoys=s._images())
        me = SimpleNamespace(x=h.x + 5, y=h.y, espec=SimpleNamespace(sight=30.0), target=None)
        me.dist_to = lambda o: math.hypot(o.x - me.x, o.y - me.y)
        self.assertIs(Brain._pick_player(me, ctx), b)
        me.boss = True
        self.assertIs(Brain._pick_player(me, ctx), h)               # (bosses pass him by)
        h.x += 4.0
        for _ in range(120):
            s.rules.tick(s.me, DT)
        self.assertLess(math.hypot(b.x - h.x, b.y - h.y), 2.5)       # (at your heels)
        e = self.place(foe(30.5, 20.5, BASE))[0]
        b.take_damage(50, e, None)
        for _ in range(60):
            s.rules.tick(s.me, DT)
        self.assertLess(b.hp, 200)                     # (no mending for 1 s)
        for _ in range(120):
            s.rules.tick(s.me, DT)
        self.assertGreater(b.hp, 160)
        b.take_damage(500, e, None)
        self.assertFalse(b.alive)
        self.assertNotIn(b, s._images())
        for _ in range(round(config.U_BUTTONS[2] * 60) + 2):
            s.rules.tick(s.me, DT)
        self.assertTrue(b.alive)
        self.assertEqual(b.hp, 200)

    def test_bat_form_rolls_over_walls_as_bats(self):
        s, h = self.setup("bat_form", walls=[(22, y) for y in range(10, 30)])
        roll.start(s, s.me, 1.0, 0.0)
        self.assertTrue(h.bats)
        self.assertAlmostEqual(h.roll_speed, config.ROLL_DISTANCE / config.ROLL_TIME * 1.5)
        self.assertIsNotNone(h.vault)
        self.go(0.5)
        self.assertGreater(h.x, 23.0)                  # (over the wall)
        self.assertFalse(h.bats)

    def test_the_world_marks_draw(self):
        s, h = self.setup("dung_ball")
        for key in ("rod_of_fission", "mr_buttons", "parasol", "hourglass_ring", "hermits_furs",
                    "black_ice_crown"):
            wear(s, key, 0)
        e = self.place(foe(24.5, 20.5, BASE))[0]
        inflict(e, "chill", h)
        s.rules.tick(s.me, DT)
        e.x += 0.6
        s.rules.tick(s.me, DT)
        h.bear.hp = 120.0
        h.trigger = True
        h.hourglass_t = 1.0
        h.frost = True
        s.players[0].minimap = None
        s.draw(s.manager.text)
        h.bats = True
        h.bear.hp = 0.0
        s.draw(s.manager.text)


class ForestTest(_Relic):
    def test_every_boss_has_its_relics(self):
        for boss, keys in LAST.items():
            self.assertEqual(config.BOSS_UNIQUES[boss], keys)
        self.assertEqual(len(uniques()), 46)                  # (M29.5: +4, M30.5: +4)
        # (the Four Horsemen are the Serene Cavalry's form 2: they drop as it;
        # the hunger is the Host of the Feast's second form: he drops them)
        self.assertEqual(set(config.BOSS_UNIQUES) | {"necromancer_lich", "conquest", "war",
                                                     "famine", "death", "host_hunger"},
                         set(config.BOSSES))

    def test_shrinking_dust_shrinks_you_on_a_roll(self):
        s, h = self.setup("shrinking_dust")
        r = h.hit_radius
        roll.start(s, s.me, 1.0, 0.0)
        self.assertAlmostEqual(h.dusted, 2.0)
        self.assertAlmostEqual(h.hit_radius, r * config.U_SHRINKING_DUST[1])
        h.roll_t = 0.0
        h.vx = h.vy = 0.0
        x = h.x
        h.move(1.0, 0.0, 1.0, s.world)                 # (a full second of walking)
        fast = h.x - x
        for _ in range(130):
            s.rules.tick(s.me, DT)
        self.assertEqual(h.hit_radius, r)
        h.vx = h.vy = 0.0
        x = h.x
        h.move(1.0, 0.0, 1.0, s.world)
        self.assertGreater(fast, (h.x - x) * 1.2)

    def test_blight_thorn_ring_blights_who_hurts_you(self):
        s, h = self.setup("blight_thorn_ring")
        e = self.place(foe(24.5, 20.5, BASE))[0]
        other = self.place(foe(24.5, 23.5, BASE))[0]
        h.take_damage(10, e, None)
        self.assertGreater(e.blighted[0], h.time)
        a = combat.strike(e, 100, h, 0.0, s.effects)
        b = combat.strike(other, 100, h, 0.0, s.effects)
        self.assertAlmostEqual(a, b * 1.25)
        h.time += 4.1
        self.assertAlmostEqual(combat.strike(e, 100, h, 0.0, s.effects), b)

    def test_cleaver_of_cuddles_orbits_cuts_and_spins_up(self):
        s, h = self.setup("cleaver_of_cuddles")
        s.rules.tick(s.me, DT)
        c = h.cleaver
        self.assertEqual(c[1], 1.0)
        from ascii_adventurers.systems.relics import cleaver_spot, on_kill
        bx, by = cleaver_spot(h)
        self.assertAlmostEqual(math.hypot(bx - h.x, by - h.y), config.U_CLEAVER[0])
        e = self.place(foe(h.x, h.y - config.U_CLEAVER[0], BASE))[0]
        for _ in range(180):
            s.rules.tick(s.me, DT)
        self.assertLess(e.hp, BASE)
        for _ in range(30):
            on_kill(s, s.me, e)
        self.assertEqual(c[1], config.U_CLEAVER[3])                  # (the most: x2)
        for _ in range(round(config.U_CLEAVER[4] * 60) + 2):
            s.rules.tick(s.me, DT)
        self.assertEqual(c[1], 1.0)                                  # (slowed back)

    def test_acorn_bandolier_lobs_acorns_every_4th_attack(self):
        s, h = self.setup("acorn_bandolier", hero="huntress")
        h.attacks = 2
        s.rules.patterns(s.me, s.rules.attack_mods(s.me))
        self.assertFalse([q for q in s.projectiles if q.spec.look == "acorn"])
        h.attacks = 7
        s.rules.patterns(s.me, s.rules.attack_mods(s.me))
        nuts = [q for q in s.projectiles if q.spec.look == "acorn"]
        self.assertEqual(len(nuts), 3)
        self.assertTrue(all(q.spec.lob and q.flight == config.U_ACORNS[2] for q in nuts))
        e = self.place(foe(h.x + 6.0, h.y, BASE))[0]
        s.projectiles[:] = nuts
        for _ in range(60):
            combat.update_projectiles(s.projectiles, s.world, s.effects, DT, s._actors(), s.zones)
        self.assertLess(e.hp, BASE)

    def test_a_bard_lobs_acorns_and_lashes_too(self):
        s, h = self.setup("acorn_bandolier", hero="bard")
        self.assertIsNone(h.weapon.spec.shell)
        h.attacks = 3
        s.rules.patterns(s.me, s.rules.attack_mods(s.me))
        self.assertEqual(len([q for q in s.projectiles if q.spec.look == "acorn"]), 3)
        s, h = self.setup("tongue_lasher", hero="bard")   # (both off-hand: one at a time)
        near = self.place(mover(26.5, 20.5))[0]
        h.attacks = 5
        s.rules.patterns(s.me, s.rules.attack_mods(s.me))
        self.assertLess(near.x, 23.0)

    def test_tripwire_boots_trip_the_first_to_cross(self):
        s, h = self.setup("tripwire_boots")
        self.roll(1.0, 0.0)
        self.assertEqual(len(h.wires), 1)
        w = h.wires[0]
        self.assertAlmostEqual(w[0], 20.5)
        a = self.place(mover((w[0] + w[2]) / 2, 22.5))[0]
        s.rules.tick(s.me, DT)
        self.assertEqual(len(h.wires), 1)
        a.y = 20.6                                       # (it walks onto the wire)
        s.rules.tick(s.me, DT)
        self.assertEqual(h.wires, [])
        self.assertGreater(a.status.dazed, 1.0)

    def test_rootbound_boots_grow_a_shield_and_fade(self):
        s, h = self.setup("rootbound_boots")
        h.shield = 0.0
        for _ in range(60 * 30):
            s.rules.tick(s.me, DT)
        self.assertAlmostEqual(h.shield, h.max_hp * config.U_ROOTBOUND[0], delta=0.5)
        h.vx = 5.0                                        # (walking)
        s.rules.tick(s.me, DT)
        before = h.shield
        for _ in range(60):
            s.rules.tick(s.me, DT)
        self.assertLess(h.shield, before)
        for _ in range(60 * 3):
            s.rules.tick(s.me, DT)
        self.assertAlmostEqual(h.shield, 0.0, delta=0.01)

    def test_heartwood_ring_heals_by_trees(self):
        s, h = self.setup("heartwood_ring")
        h.hp = 50.0
        for _ in range(60):
            s.rules.tick(s.me, DT)
        self.assertLess(h.hp, 51.0)                      # (no trees on the open map)
        s.world.set_tile(22, 20, tiles.TREE)
        for _ in range(60):
            s.rules.tick(s.me, DT)
        self.assertGreater(h.hp, 51.0)


class MyceliumTest(_Relic):
    def test_mycelial_ring_leaves_a_spore_patch(self):
        s, h = self.setup("mycelial_ring")
        e = self.place(foe(24.5, 20.5, 5))[0]
        combat.strike(e, 100, h, 0.0, s.effects)
        s.rules.on_kill(s.me, e)
        pools = [z for z in s.zones if z.kind == "pool" and z.source is h]
        self.assertEqual(len(pools), 1)
        self.assertEqual((pools[0].inflicts, pools[0].life, pools[0].radius), ("poison", 5.0, 2.0))
        other = self.place(foe(24.5, 21.0, BASE))[0]
        for _ in range(61):
            update_zones(s.zones, s._actors(), s.effects, DT, s.world)
        self.assertTrue(other.status.has("poison"))

    def test_fly_agaric_cap_trips_enemies(self):
        s, h = self.setup("fly_agaric_cap")
        e = self.place(mover(24.5, 20.5))[0]
        combat.strike(e, 10, h, 0.0, s.effects)
        self.assertTrue(e.status is None or e.status.wander == 0)
        h.rng.random = lambda: 0.05
        combat.strike(e, 10, h, 0.0, s.effects)
        self.assertAlmostEqual(e.status.wander, 2.0)
        x, y = e.x, e.y
        e.rng = h.rng
        for _ in range(30):
            self.assertTrue(relics.wander(s, e, DT))
        self.assertGreater(math.hypot(e.x - x, e.y - y), 0.3)
        boss = self.place(mover(24.5, 24.5))[0]
        boss.boss = True
        combat.strike(boss, 10, h, 0.0, s.effects)
        self.assertAlmostEqual(boss.status.bound, config.U_FLY_AGARIC[1])
        self.assertFalse(relics.wander(s, boss, DT))
        boss.status.bound = 0.0
        combat.strike(boss, 10, h, 0.0, s.effects)
        self.assertEqual(boss.status.bound, 0.0)        # (not again for 4 s)

    def test_inkwell_charm_blots_the_nearest(self):
        s, h = self.setup("inkwell_charm")
        e = self.place(foe(25.5, 20.5, BASE))[0]
        e.status = None
        far = self.place(foe(28.5, 20.5, BASE))[0]
        s.rules.tick(s.me, DT)
        self.assertLess(e.hp, BASE)
        self.assertEqual(far.hp, BASE)
        self.assertIs(e.ink_blot[0], h)
        from ascii_adventurers.ai.brain import Brain
        self.assertTrue(Brain.smoked(e, h))
        h.time += 2.1
        self.assertFalse(Brain.smoked(e, h))
        hp = e.hp
        s.rules.tick(s.me, DT)
        self.assertEqual(e.hp, hp)                       # (every 5 s)

    def test_lawyers_wig_binds_the_fifth_scrawl(self):
        s, h = self.setup("lawyers_wig")
        e = self.place(foe(24.5, 20.5, BASE))[0]
        for _ in range(4):
            combat.strike(e, 10, h, 0.0, s.effects)
        self.assertTrue(e.status is None or e.status.bound == 0)
        combat.strike(e, 10, h, 0.0, s.effects)
        self.assertAlmostEqual(e.status.bound, 2.0)
        boss = self.place(foe(24.5, 24.5, BASE))[0]
        boss.boss = True
        for _ in range(5):
            combat.strike(boss, 10, h, 0.0, s.effects)
        self.assertAlmostEqual(boss.status.bound, config.U_WIG[1])

    def test_the_ink_cap_boss_keeps_its_own_ink(self):
        """The ink cap boss has its own `inked` and `scrawls`: the relics'
        marks must not trip over them."""
        s, h = self.setup("lawyers_wig")
        e = self.place(foe(24.5, 20.5, BASE))[0]
        e.inked, e.scrawls = {}, 3
        for _ in range(5):
            combat.strike(e, 10, h, 0.0, s.effects)
        self.assertGreater(e.status.bound, 0)
        self.assertEqual((e.inked, e.scrawls), ({}, 3))
        from ascii_adventurers.ai.brain import Brain
        self.assertFalse(Brain.smoked(e, h))
        s.players[0].minimap = None
        s.draw(s.manager.text)

    def test_puffball_sandals_burst_spores(self):
        s, h = self.setup("puffball_sandals")
        e = self.place(foe(21.5, 20.5, BASE))[0]
        far = self.place(foe(26.5, 20.5, BASE))[0]
        roll.start(s, s.me, 1.0, 0.0)
        self.assertLess(e.hp, BASE)
        self.assertTrue(e.status.has("poison"))
        self.assertEqual(far.hp, BASE)

    def test_spore_wind_band_gusts(self):
        s, h = self.setup("spore_wind_band")
        e = self.place(mover(22.5, 20.5))[0]
        inflict(e, "poison", h)
        left = e.status.active["poison"].left
        s.rules.tick(s.me, DT)
        self.assertGreater(e.x, 25.0)
        self.assertGreater(e.status.active["poison"].left, left + 1.9)
        self.assertGreater(h.gust_t, 11.0)


class NecromancerTest(_Relic):
    def test_phylactery_a_shade_that_kills_its_way_back(self):
        s, h = self.setup("phylactery")
        h.hp = 0.0
        self.assertTrue(s.rules.revive(s.me))
        self.assertEqual(h.hp, 1.0)
        self.assertGreater(h.shade, 9.9)
        self.assertEqual(h.take_damage(50, None, None), 0.0)          # (untouchable)
        e = self.place(foe(24.5, 20.5, BASE))[0]
        other = foe(24.5, 22.5, BASE)
        h.shade = 0.0
        full = combat.strike(other, 100, h, 0.0, s.effects)
        h.shade = 9.0
        self.assertAlmostEqual(combat.strike(e, 100, h, 0.0, s.effects), full * 0.5)
        for _ in range(10):
            s.rules.on_kill(s.me, foe(30, 30, 1))
        self.assertEqual(h.shade, 0.0)
        self.assertAlmostEqual(h.hp, h.max_hp * 0.3)
        h.hp = 0.0
        self.assertFalse(s.me.phylactery_used is False)
        self.assertFalse(relics.rise_as_shade(s, s.me))                # (once a run)

    def test_a_shade_that_kills_too_few_falls(self):
        s, h = self.setup("phylactery")
        h.hp = 0.0
        s.rules.revive(s.me)
        for _ in range(3):
            s.rules.on_kill(s.me, foe(30, 30, 1))
        for _ in range(round(10 * 60) + 2):
            s.rules.tick(s.me, DT)
        self.assertFalse(h.alive)

    def test_lichs_gaze_marks_what_you_keep_under_aim(self):
        s, h = self.setup("lichs_gaze")
        e = self.place(foe(24.5, 20.5, BASE))[0]
        other = self.place(foe(24.5, 25.5, BASE))[0]
        for _ in range(60):
            s.rules.tick(s.me, DT)
        self.assertNotIn("lich_marks", other.__dict__)
        self.assertFalse(e.__dict__.get("lich_marks"))
        for _ in range(40):
            s.rules.tick(s.me, DT)
        self.assertIn(id(h), e.lich_marks)
        base = combat.strike(other, 100, h, 0.0, s.effects)
        self.assertAlmostEqual(combat.strike(e, 100, h, 0.0, s.effects), base * 2.0)
        self.assertAlmostEqual(combat.strike(e, 100, h, 0.0, s.effects), base)   # (once)

    def test_corpse_candle_burns_and_heals(self):
        s, h = self.setup("corpse_candle")
        dead = foe(22.0, 20.5, 1)
        s.rules.on_kill(s.me, dead)
        c = [z for z in s.zones if z.kind == "candle"]
        self.assertEqual(len(c), 1)
        e = self.place(foe(22.5, 21.5, BASE))[0]
        h.hp = 50.0
        for _ in range(60):
            s.rules.tick(s.me, DT)
            update_zones(s.zones, s._actors(), s.effects, DT, s.world)
        self.assertAlmostEqual(BASE - e.hp, 8.0, delta=4.5)
        self.assertGreater(h.hp, 52.0)
        for _ in range(20):
            s.rules.on_kill(s.me, foe(22.0, 20.5, 1))
        update_zones(s.zones, s._actors(), s.effects, 0.0, s.world)
        self.assertLessEqual(len([z for z in s.zones if z.kind == "candle"]), config.U_CANDLE[4])

    def test_the_last_marks_draw(self):
        s, h = self.setup("cleaver_of_cuddles")
        for key in ("tripwire_boots", "rootbound_boots", "heartwood_ring", "lichs_gaze",
                    "corpse_candle", "phylactery"):
            wear(s, key, 0)
        e = self.place(mover(24.5, 20.5))[0]
        s.rules.tick(s.me, DT)
        h.wires.append([20.5, 20.5, 23.5, 20.5, 4.0])
        h.roots, h.shield, h.still_t, h.near_tree, h.hp = 10.0, 10.0, 1.0, True, 50.0
        h.shade, h.shade_kills = 5.0, 3
        h.gaze, h.gaze_t = e, 0.5
        st = statuses.statuses_of(e)
        st.wander, st.bound = 1.0, 1.0
        e.ink_blot = (h, h.time + 1)
        e.blighted = (h.time + 1, 0.25)
        e.lich_marks = {id(h)}
        s.rules.on_kill(s.me, foe(21.5, 21.5, 1))
        s.players[0].minimap = None
        s.draw(s.manager.text)


if __name__ == "__main__":
    unittest.main()
