"""M28.4: drops -- ground pieces, elite drops, chests, mimics, Saddlebags
(design/GEAR.md 4.2, 4.3, 10 and 20)."""

import math
import os
import random
import unittest
from collections import Counter

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from ascii_adventurers import config
from ascii_adventurers.entities.drops import GearDrop, update_drops
from ascii_adventurers.players import gear
from ascii_adventurers.players.gear import Equipment, Offer, Piece, draw_drop, offer_for
from ascii_adventurers.players.stats import HeroStats
from ascii_adventurers.ai import make_enemy
from ascii_adventurers.ai.mimic import Mimic
from ascii_adventurers.render.characters import ART
from ascii_adventurers.render.chests import MIMIC_ART
from ascii_adventurers.systems.chests import CHEST_SID
from ascii_adventurers.tests.test_m17 import game, step, teleport, world
from ascii_adventurers.tests.test_p7 import Arena, enemy
from ascii_adventurers.world import tiles
from ascii_adventurers.world.landmarks import chest_marks
from ascii_adventurers.ui.drop_panel import DropPanel
from ascii_adventurers.ui.gear_picker import GearPicker
from ascii_adventurers.ui.gear_screen import GearScreen

WIZ = config.WEAPONS[config.HEROES["wizard"].weapon]
RANK = {r: i for i, r in enumerate(config.RARITIES)}


def key(s, k):
    s.handle_event(pygame.event.Event(pygame.KEYDOWN, key=k, unicode="", mod=0))


class FakeElite:
    """What _elite_drop reads off a dead enemy."""

    def __init__(self, key_, sid, x=10.0, y=10.0):
        self.espec = config.ENEMIES[key_]
        self.spawn_id = sid
        self.x, self.y = x, y


# --- 20.1 M28.4a: ground pieces and elite drops ------------------------------------------


class DropRollTest(unittest.TestCase):
    def test_a_drop_is_a_new_piece_never_a_worn_base(self):
        eq = Equipment()
        eq.take(Offer("seeker", "common", (), "new"))
        eq.take(Offer("ember_aura", "uncommon", (), "new"))
        for n in range(1, 60):
            p = draw_drop("wizard", WIZ, eq, 31, 0, 0xD000 + n, HeroStats(), level=5)
            self.assertIsNotNone(p)
            self.assertIsInstance(p, Piece)
            self.assertIsNone(eq.wearing(p.key), p.key)
            self.assertEqual(p.level, 0)

    def test_the_roll_is_seeded(self):
        a = draw_drop("dwarf", config.WEAPONS[config.HEROES["dwarf"].weapon], Equipment(), 7, 0,
                      0xD001, HeroStats(), level=3)
        b = draw_drop("dwarf", config.WEAPONS[config.HEROES["dwarf"].weapon], Equipment(), 7, 0,
                      0xD001, HeroStats(), level=3)
        self.assertEqual((a.key, a.rarity, a.affixes), (b.key, b.rarity, b.affixes))

    def test_a_floor_and_luck_lift_the_rarity(self):
        plain = Counter()
        lucky = Counter()
        for n in range(1, 200):
            plain[draw_drop("wizard", WIZ, Equipment(), 5, 0, 0xD000 + n, HeroStats()).rarity] += 1
            lucky[draw_drop("wizard", WIZ, Equipment(), 5, 0, 0xD000 + n, HeroStats(),
                            luck=config.CHEST_LUCK if hasattr(config, "CHEST_LUCK") else 10).rarity] += 1
        mean = lambda c: sum(RANK[r] * k for r, k in c.items()) / sum(c.values())   # noqa: E731
        self.assertGreater(mean(lucky), mean(plain))
        for n in range(1, 40):
            p = draw_drop("wizard", WIZ, Equipment(), 5, 0, 0xD000 + n, HeroStats(),
                          min_rarity_="epic")
            self.assertGreaterEqual(RANK[p.rarity], RANK["epic"], p)

    def test_offer_for_reads_the_slot_as_it_stands(self):
        eq = Equipment()
        piece = Piece("seeker", "rare", 0, ("sharpened",))
        self.assertEqual(offer_for(piece, eq).kind, "new")
        eq.take(Offer("ember_aura", "common", (), "new"))
        eq.take(Offer("frost_nova", "common", (), "new"))
        eq.take(Offer("rune_trap", "common", (), "new"))        # (3 trinkets: now full)
        self.assertEqual(offer_for(Piece("poison_flask", "rare"), eq).kind, "swap")
        self.assertEqual(offer_for(Piece("ember_aura", "epic"), eq).kind, "plus")

    def test_stash_with_a_drop_index(self):
        eq = Equipment()
        for i in range(eq.bag_size):
            self.assertEqual(eq.stash(Piece("seeker", "common", i)), [])
        out = eq.stash(Piece("seeker", "epic"), 0)                # salvage the oldest
        self.assertEqual([p.level for p in out], [0])
        self.assertEqual(eq.bag[-1].rarity, "epic")
        self.assertEqual(len(eq.bag), eq.bag_size)


class EliteDropTest(unittest.TestCase):
    def test_elites_drop_about_fifteen_percent_of_the_time(self):
        m, s = game(seed=31)
        p = s.me
        for n in range(600):
            s._elite_drop(p, FakeElite("bull", (n, 7, 3), s.hero.x + 2, s.hero.y))
        rate = len(s.drops) / 600
        self.assertAlmostEqual(rate, config.ELITE_DROP, delta=0.05, msg=rate)
        self.assertEqual(len({d.id for d in s.drops}), len(s.drops))
        for d in s.drops:
            self.assertIsNone(p.progress.gear.wearing(d.piece.key))

    def test_the_roll_follows_the_kill(self):
        m, s = game(seed=31)
        m2, s2 = game(seed=31)
        for n in range(80):
            s._elite_drop(s.me, FakeElite("headless_knight", (n, 2, 1)))
            s2._elite_drop(s2.me, FakeElite("headless_knight", (n, 2, 1)))
        self.assertEqual([(d.piece.key, d.piece.rarity) for d in s.drops],
                         [(d.piece.key, d.piece.rarity) for d in s2.drops])
        self.assertGreater(len(s.drops), 0)

    def test_plain_enemies_never_drop(self):
        m, s = game(seed=31)
        for n in range(200):
            s._elite_drop(s.me, FakeElite("field_rat", (n, 1, 1)))
        self.assertEqual(s.drops, [])


class PickupTest(unittest.TestCase):
    def setUp(self):
        self.m, self.s = game(seed=31)
        self.p = self.s.me
        self.h = self.s.hero

    def lay(self, piece=None, dx=0.6):
        s = self.s
        if piece is None:
            d = s._drop_piece(self.p, self.h.x + dx, self.h.y)
        else:
            s._drop_ids += 1
            d = GearDrop(self.h.x + dx, self.h.y, piece, s._drop_ids)
            s.drops.append(d)
        return d

    def panel(self):
        step(self.s)
        ov = self.s.overlay
        self.assertIsInstance(ov, DropPanel)
        return ov

    def test_walking_up_opens_the_panel_and_wear_puts_it_on(self):
        d = self.lay()
        ov = self.panel()
        self.assertEqual(ov.offer[0].key, d.piece.key)
        self.assertEqual(ov.offer[0].kind, "new")
        self.assertEqual(ov.buttons, ("wear", "bag", "salvage", "leave"))
        key(self.s, pygame.K_w)
        gear_ = self.p.progress.gear
        self.assertIsNotNone(gear_.wearing(d.piece.key))
        self.assertEqual(self.s.drops, [])
        self.assertIsNone(self.s.overlay)
        self.assertIn(d.piece.key, self.p.stats.cards)

    def test_a_worn_base_gets_plus_one(self):
        gear_ = self.p.progress.gear
        gear_.take(Offer("seeker", "common", (), "new"))
        self.s._apply_loadout(self.p)
        self.lay(Piece("seeker", "rare"))
        ov = self.panel()
        self.assertEqual(ov.offer[0].kind, "plus")
        self.assertIn("+1 TO WORN", ov._labels()[0])
        key(self.s, pygame.K_w)
        self.assertEqual(gear_.worn[gear_.wearing("seeker")].level, 1)
        self.assertEqual(self.s.drops, [])

    def test_a_swap_asks_which_ring_and_bags_the_old_one(self):
        gear_ = self.p.progress.gear
        gear_.take(Offer("volatile", "common", (), "new"))
        gear_.take(Offer("bounty", "common", (), "new"))
        self.s._apply_loadout(self.p)
        self.lay(Piece("fortune", "rare"))
        ov = self.panel()
        self.assertEqual(ov.offer[0].kind, "swap")
        key(self.s, pygame.K_w)
        self.assertIsInstance(ov.sub, GearScreen)          # which ring?
        self.assertEqual(ov.sub.mode, "slot")
        ov._send(0, "ring1", None)
        self.assertIsNotNone(gear_.wearing("fortune"))
        self.assertEqual([p.key for p in gear_.bag], ["volatile"])
        self.assertEqual(self.s.drops, [])

    def test_bag_it(self):
        d = self.lay()
        self.panel()
        key(self.s, pygame.K_b)
        self.assertEqual([p.key for p in self.p.progress.gear.bag], [d.piece.key])
        self.assertEqual(self.s.drops, [])

    def test_a_full_bag_asks_which_to_salvage(self):
        gear_ = self.p.progress.gear
        for i in range(gear_.bag_size):
            gear_.stash(Piece("seeker", "common", i))
        d = self.lay(Piece("fortune", "epic"))
        ov = self.panel()
        loot = self.p.stats.loot
        key(self.s, pygame.K_b)
        self.assertIsInstance(ov.sub, GearScreen)
        self.assertEqual(ov.sub.mode, "drop")
        ov._bagged(0)                                       # salvage the first bagged piece
        self.assertEqual([p.key for p in gear_.bag][-1], "fortune")
        self.assertEqual(len(gear_.bag), gear_.bag_size)
        self.assertGreater(self.p.stats.loot, loot)
        self.assertEqual(self.s.drops, [])

    def test_salvage(self):
        d = self.lay()
        self.panel()
        loot = self.p.stats.loot
        key(self.s, pygame.K_x)
        self.assertEqual(self.p.stats.loot, loot + gear.salvage_value(d.piece))
        self.assertEqual(self.s.drops, [])
        self.assertIsNone(self.s.overlay)

    def test_leave_keeps_it_until_you_come_back(self):
        d = self.lay()
        self.panel()
        key(self.s, pygame.K_ESCAPE)
        self.assertIsNone(self.s.overlay)
        self.assertEqual(self.s.drops, [d])
        self.assertIn(self.p.index, d.cooled)
        step(self.s, 5)
        self.assertIsNone(self.s.overlay)                   # standing there: it stays shut
        x0, y0 = self.h.x, self.h.y
        self.h.x += 5.0
        step(self.s, 2)
        self.assertNotIn(self.p.index, d.cooled)
        self.h.x, self.h.y = x0, y0
        self.panel()

    def test_seen_drops_are_pinned_and_drawn(self):
        d = self.lay(dx=12.0)
        self.assertFalse(d.seen)
        step(self.s)
        self.assertTrue(d.seen)
        pins = self.s._drop_pins()
        self.assertEqual(len(pins), 1)
        self.assertEqual(pins[0][2], f"gear_{d.piece.rarity}")
        self.assertEqual(pins[0][3], d.name.upper())
        self.s.draw(self.m.text)
        far = self.lay(dx=60.0)
        step(self.s)
        self.assertFalse(far.seen)
        self.assertEqual(len(self.s._drop_pins()), 1)

    def test_a_legendary_drop_draws_its_spark(self):
        self.lay(Piece("seeker", "legendary", 0, ("sharpened",)), dx=3.0)
        self.s.draw(self.m.text)
        self.panel() if False else None

    def test_ghosts_ignore_drops(self):
        class Ghost:
            alive, ghost, index = True, True, 1
            hero = self.h
        d = self.lay()
        self.assertEqual(update_drops([d], [Ghost()], 1 / 60), [])

    def test_the_panel_draws(self):
        self.lay()
        self.panel()
        self.s.draw(self.m.text)
        key(self.s, pygame.K_DOWN)
        key(self.s, pygame.K_RIGHT)
        self.s.draw(self.m.text)


# --- 20.1 M28.4b/c: chests and mimics ------------------------------------------------------


def chest_of(s, guarded=None, mimic=None):
    """A chest state of the game matching the flags, nearest the spawn."""
    picks = [c for c in s.chests.states
             if (guarded is None or c.guarded == guarded) and (mimic is None or c.mimic == mimic)]
    return min(picks, key=lambda c: math.hypot(c.x - s.spawn[0], c.y - s.spawn[1]))


def walk_up(s, c):
    teleport(s, c.x, c.y + 1.4)
    s.hero.x, s.hero.y = c.x, c.y + 1.4          # (right by it, whatever free_spot said)


class ChestPlacementTest(unittest.TestCase):
    def test_six_to_eight_a_ring_biome_half_guarded_some_mimics(self):
        for seed in (31, 7):
            w = world(seed)
            chests = chest_marks(w.layout)
            per = Counter(m.biome for m in chests)
            self.assertEqual(set(per), set(config.BIOME_RING), seed)
            for biome, n in per.items():
                lo, hi = config.CHESTS_PER_BIOME
                self.assertTrue(lo <= n <= hi, (seed, biome, n))
                guarded = sum(1 for m in chests if m.biome == biome and m.props["guarded"])
                self.assertEqual(guarded, round(n * config.CHEST_GUARDED), (seed, biome))
                for m in chests:
                    if m.biome == biome:
                        self.assertIn(m.props["guard"], config.CHEST_GUARD_KINDS[biome])
            self.assertGreaterEqual(sum(m.props["mimic"] for m in chests), 1, seed)
            self.assertLess(sum(m.props["mimic"] for m in chests), len(chests) * 0.3, seed)
            self.assertEqual([m.props["n"] for m in chests], list(range(len(chests))))
            # Clear of every quest spot, camp and lair, and of each other.
            others = [m for m in w.layout.landmarks if m.kind != "chest"]
            for c in chests:
                for o in others:
                    self.assertFalse(o.contains(c.cx, c.cy, 4), (seed, o.key))
                for d in chests:
                    if d is not c:
                        self.assertGreater(math.hypot(c.cx - d.cx, c.cy - d.cy), 50, seed)

    def test_the_tile_is_a_chest(self):
        w = world(31)
        for m in chest_marks(w.layout)[:4]:
            tx, ty = math.floor(m.cx), math.floor(m.cy)
            w.ensure_ready(tx - 8, ty - 8, tx + 8, ty + 8)
            self.assertIs(w.tile_at(tx, ty), tiles.CHEST)
            self.assertTrue(tiles.CHEST.solid)
            self.assertFalse(tiles.CHEST.blocks_shots)

    def test_the_guards_are_placed_as_fixed_spawns(self):
        m, s = game(seed=31)
        c = chest_of(s, guarded=True)
        sids = [(CHEST_SID, c.n, k + 1) for k in range(config.CHEST_GUARDS)]
        for sid in sids:
            self.assertIn(sid, s.spawner.fixed)
            self.assertEqual(s.spawner.fixed[sid][0], c.guard)
        self.assertEqual(s.chests.guards_left(c), config.CHEST_GUARDS)
        open_ = chest_of(s, guarded=False)
        self.assertEqual(s.chests.guards_left(open_), 0)


class ChestTest(unittest.TestCase):
    def test_walking_up_opens_a_chest_and_a_piece_lies_in_front(self):
        m, s = game(seed=31)
        c = chest_of(s, guarded=False, mimic=False)
        walk_up(s, c)
        self.assertFalse(c.done)
        step(s)
        self.assertTrue(c.done)
        self.assertIs(s.world.tile_at(math.floor(c.x), math.floor(c.y)), tiles.CHEST_OPEN)
        self.assertEqual(len(s.drops), 1)
        d = s.drops[0]
        self.assertLess(math.hypot(d.x - c.x, d.y - c.y), 3.0)
        self.assertTrue(any(e.kind == "toast" and e.label == "CHEST OPENED" for e in s.effects))
        s.hero.x, s.hero.y = d.x, d.y
        step(s)
        self.assertIsInstance(s.overlay, DropPanel)
        self.assertEqual(s.chests.pins()[0][2], "chest_done")
        step(s, 3)
        self.assertEqual(len(s.drops), 1)                  # (opened once)

    def test_a_guarded_chest_waits_for_its_guards(self):
        m, s = game(seed=31)
        c = chest_of(s, guarded=True, mimic=False)
        walk_up(s, c)
        step(s, 2)
        self.assertFalse(c.done)
        self.assertTrue(any(e.kind == "toast" and "GUARDED" in e.label for e in s.effects))
        guards = [e for e in s.enemies if isinstance(e.spawn_id, tuple) and e.spawn_id[:2] == (CHEST_SID, c.n)]
        self.assertEqual(len(guards), config.CHEST_GUARDS)
        self.assertEqual({e.kind_key for e in guards}, {c.guard})
        for e in guards:
            e.hp = 0
            e.last_hit_by = s.hero
        step(s)
        self.assertEqual(s.chests.guards_left(c), 0)
        step(s)
        self.assertTrue(c.done)
        self.assertEqual(len(s.drops), 1)

    def test_a_mimic_bites_and_coughs_up_an_epic(self):
        m, s = game(seed=31)
        c = chest_of(s, mimic=True)
        for sid in list(s.spawner.fixed):                 # (its guards, if any: gone)
            if sid[:2] == (CHEST_SID, c.n):
                s.spawner.dead.add(sid)
        walk_up(s, c)
        step(s)
        self.assertTrue(c.done)
        self.assertIsNot(s.world.tile_at(math.floor(c.x), math.floor(c.y)), tiles.CHEST)
        mimics = [e for e in s.enemies if isinstance(e, Mimic)]
        self.assertEqual(len(mimics), 1)
        e = mimics[0]
        self.assertEqual(e.biome, c.biome)
        self.assertEqual(e.spawn_id, (CHEST_SID, c.n, 0))
        self.assertIn(e.sprite_now(), ART)
        self.assertTrue(e.espec.elite)
        self.assertEqual(s.drops, [])
        self.assertTrue(any(e_.kind == "toast" and "MIMIC" in e_.label for e_ in s.effects))
        s.draw(m.text)
        e.hp = 0
        e.last_hit_by = s.hero
        step(s)
        self.assertEqual(len(s.drops), 1)
        self.assertGreaterEqual(RANK[s.drops[0].piece.rarity], RANK["epic"])
        self.assertEqual(s.chests.pins()[0][2], "chest_done")

    def test_chests_are_pinned_once_seen(self):
        m, s = game(seed=31)
        c = chest_of(s, guarded=False)
        self.assertEqual(s.chests.pins(), [])
        teleport(s, c.x + config.CHEST_SEEN - 2, c.y)
        step(s)
        pins = s.chests.pins()
        self.assertEqual(len(pins), 1)
        self.assertEqual(pins[0][2:], ("chest", "CHEST"))
        s.draw(m.text)

    def test_the_draw_with_a_chest_in_view(self):
        m, s = game(seed=31)
        c = chest_of(s, guarded=True)
        teleport(s, c.x + 4, c.y)
        step(s)
        s.draw(m.text)
        m.app.dev = True
        s.dev_targets = True
        s._toggle_map()
        s.draw(m.text)


class MimicTest(unittest.TestCase):
    def test_every_ring_biome_has_a_body(self):
        for biome in config.BIOME_RING:
            art = MIMIC_ART[f"mimic_{biome}"]
            self.assertEqual(len(art), 18)
            self.assertTrue(all(len(r) == 14 for r in art))
        self.assertIn("mimic", config.BESTIARY)
        self.assertEqual(config.ENEMIES["mimic"].biomes, ())
        self.assertTrue(config.ENEMIES["mimic"].elite)

    def test_it_hops_lunges_lashes_and_spits(self):
        e = enemy("mimic", 24.5, 15.5)
        e.biome = "desert"
        a = Arena(e, hero_at=(30.5, 15.5))
        seen = set()
        hp = a.hero.hp
        for _ in range(120):
            a.run(0.05)
            seen.add(e.state)
            if e.tongue_t > 0:
                seen.add("tongue")
            if a.projectiles:
                seen.add("coins")
        self.assertIn("crouch", seen)
        self.assertIn("lunge", seen)
        self.assertTrue({"lash", "spit", "tongue", "coins"} & seen, seen)
        self.assertLess(a.hero.hp, hp)
        # It moves in hops: sometimes still, sometimes not, while chasing.
        a.hero.x = 42.5
        moves = []
        for _ in range(40):
            a.run(0.05)
            moves.append(e.moving)
        self.assertIn(True, moves)
        self.assertIn(False, moves)

    def test_the_tongue_drags_you_in(self):
        e = enemy("mimic", 20.5, 15.5)
        a = Arena(e, hero_at=(25.5, 15.5))
        e.aim = 0.0
        hp = a.hero.hp
        ctx = __import__("ascii_adventurers.ai.brain", fromlist=["AIContext"]).AIContext(
            a.world, [a.hero], a.actors(), a.projectiles, a.effects)
        e._lash(ctx)
        self.assertLess(a.hero.x, 25.5)
        self.assertLess(a.hero.hp, hp)
        self.assertGreater(e.tongue_t, 0)

    def test_coins_are_drawn_as_coins(self):
        from ascii_adventurers.render.ascii_fx import SHOT_LOOKS
        self.assertEqual(SHOT_LOOKS["coin"][0], "$")
        self.assertEqual(config.WEAPONS["mimic_coins"].shell.look, "coin")


# --- 20.1 M28.4d: Saddlebags ----------------------------------------------------------------


class SaddlebagsTest(unittest.TestCase):
    def test_the_ladder_widens_the_bag(self):
        from ascii_adventurers.meta.guild import Guild
        from ascii_adventurers.tests.test_m16 import game as guild_game
        spec = config.GUILD_UPGRADES["saddlebags"]
        self.assertEqual(spec.max_level, 2)
        g = Guild()
        g.loot = 10 ** 6
        self.assertTrue(g.buy_upgrade("saddlebags"))
        self.assertTrue(g.buy_upgrade("saddlebags"))
        self.assertFalse(g.buy_upgrade("saddlebags"))
        m, s = guild_game("wizard", guild=g)
        eq = s.me.progress.gear
        self.assertEqual(eq.bag_size, config.GEAR_BAG + 2)
        for i in range(eq.bag_size):
            self.assertEqual(eq.stash(Piece("seeker", "common", i)), [])
        self.assertEqual(len(eq.stash(Piece("seeker", "common"))), 1)
        m2, s2 = guild_game("wizard")
        self.assertEqual(s2.me.progress.gear.bag_size, config.GEAR_BAG)


if __name__ == "__main__":
    unittest.main()
