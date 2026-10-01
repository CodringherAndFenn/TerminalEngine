import math
import os
import random
import unittest
from collections import Counter

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ascii_adventurers import config, palette
from ascii_adventurers.ai import KINDS, make_enemy
from ascii_adventurers.ai.brain import AIContext
from ascii_adventurers.entities.character import Character
from ascii_adventurers.render.characters import ART, ART_H, ART_W
from ascii_adventurers.systems import combat
from ascii_adventurers.world import tiles
from ascii_adventurers.world.layout import IslandLayout
from ascii_adventurers.tests.test_weapons import Dummy, fly, open_map

STEP = 1 / 60
NEW = ("dust_devil", "wisp", "toad", "spitter", "boar")


def enemy(key, x, y, seed=3):
    e = make_enemy(key, x, y, random.Random(seed))
    e.reaction = 0.0
    return e


def run(e, hero, world, seconds, others=()):
    """Let `e` think for a while against `hero`; returns (shots, effects, events)."""
    shots, effects = [], []
    actors = [hero, e, *others]
    events = []
    for _ in range(int(seconds / STEP)):
        ctx = AIContext(world, [hero], [a for a in actors if a.alive], shots, effects)
        e.think(ctx, STEP)
        events += ctx.events
        events += combat.update_projectiles(shots, world, effects, STEP,
                                            [a for a in actors if a.alive])
    return shots, effects, events


class RosterTest(unittest.TestCase):
    def test_new_enemies_are_registered_and_every_biome_has_three_or_more(self):
        for key in NEW:
            self.assertIn(config.ENEMIES[key].kind, KINDS)
        per_biome = Counter(b for s in config.ENEMIES.values() for b in s.biomes)
        for biome in ("plains", "forest", "desert", "ruins", "swamp", "mushroom"):
            self.assertGreaterEqual(per_biome[biome], 3, biome)

    def test_new_sprites_are_well_formed(self):
        for name in ("wisp", "toad", "spitter"):
            art = ART[name]
            self.assertEqual(len(art), ART_H, name)
            for row in art:
                self.assertEqual(len(row), ART_W, name)
                self.assertTrue(set(row) <= set(palette.SPRITE_COLORS) | {"."}, name)


class PlainsTest(unittest.TestCase):
    def test_plains_have_twice_the_area_and_the_ring_kept_its_width(self):
        lay = IslandLayout(11)
        self.assertAlmostEqual((lay.plains_radius / 510) ** 2, 2.0, delta=0.02)
        self.assertAlmostEqual(lay.radius - lay.plains_radius, 2550 - 510, delta=3)


class BombTest(unittest.TestCase):
    """Lobbed shells (kept for bosses; no regular enemy lobs since the
    bombardier was removed)."""

    def thrower(self):
        from ascii_adventurers.specs import ShellSpec, WeaponSpec
        c = Character(config.HEROES["wizard"], 10.5, 10.5)
        c.faction = "enemy"
        c.weapon.spec = WeaponSpec(name="test bomb", fire_interval=1.0, shell=ShellSpec(
            speed=13.0, damage=22, max_range=20.0, look="bomb", lob=True, blast_radius=1.8))
        return c

    def test_lands_on_target_over_a_wall_and_bursts(self):
        world = open_map(walls=[(15, y) for y in range(5, 16)])
        thrower = self.thrower()
        near = Dummy(20.5, 10.8)
        far = Dummy(25.5, 10.5)
        shots, effects = [], []
        combat.fire(thrower, world, shots, effects, target=(20.5, 10.5))
        self.assertTrue(shots[0].spec.lob)
        events = fly(shots, world, [thrower, near, far], effects, seconds=3.0)
        self.assertEqual(near.max_hp - near.hp, 22)          # the wall didn't stop it
        self.assertEqual(far.hp, far.max_hp)
        self.assertEqual(thrower.hp, thrower.max_hp)
        self.assertIn(combat.BREAK, events)
        self.assertEqual(shots, [])

    def test_breaks_walls_where_it_lands(self):
        world = open_map(walls=[(20, 10)])
        thrower = self.thrower()
        shots = []
        combat.fire(thrower, world, shots, [], target=(20.5, 10.5))
        fly(shots, world, [thrower], [], seconds=3.0)
        self.assertLess(world.hp_at(20, 10) or 0, tiles.WALL.hp)

    def test_no_regular_enemy_lobs(self):
        self.assertNotIn("bombardier", config.ENEMIES)
        for key, spec in config.ENEMIES.items():
            if spec.body:
                weapon = config.WEAPONS[config.BODIES[spec.body].weapon]
                self.assertFalse(weapon.shell and weapon.shell.lob, key)


class DustDevilTest(unittest.TestCase):
    def test_circles_close_flings_spirals_and_stings(self):
        world = open_map(w=60, h=40)
        hero = Character(config.HEROES["wizard"], 30.5, 20.5)
        d = enemy("dust_devil", 22.5, 20.5)
        shots, effects = [], []
        flings = []
        closest = 99.0
        for _ in range(int(6.0 / STEP)):
            ctx = AIContext(world, [hero], [hero, d], shots, effects)
            before = len(shots)
            d.think(ctx, STEP)
            if len(shots) > before:
                flings.append([p.angle for p in shots[before:]])
            closest = min(closest, math.hypot(hero.x - d.x, hero.y - d.y))
            combat.update_projectiles(shots, world, effects, STEP, [hero, d])
        self.assertLess(closest, config.DEVIL_ORBIT + 1.5)          # it comes close
        self.assertGreaterEqual(len(flings), 2)
        for f in flings:
            self.assertEqual(len(f), config.DEVIL_PELLETS)
        self.assertNotAlmostEqual(flings[0][0] % math.tau, flings[1][0] % math.tau, places=3)
        self.assertLess(hero.hp, hero.max_hp)

    def test_fragile_and_always_hittable(self):
        d = enemy("dust_devil", 5.5, 5.5)
        self.assertTrue(d.hittable)
        self.assertLessEqual(config.ENEMIES["dust_devil"].max_hp, 50)


class DifficultyTest(unittest.TestCase):
    def test_enemy_damage_is_scaled_down(self):
        self.assertLess(config.ENEMY_DAMAGE_MULTIPLIER, 1.0)
        e = enemy("goblin_archer", 5.5, 5.5)
        self.assertAlmostEqual(e.damage_mult, config.ENEMY_DAMAGE_MULTIPLIER)


class WispTest(unittest.TestCase):
    def shots_fired(self, lit_always: bool) -> int:
        world = open_map(w=80, h=40)
        hero = Character(config.HEROES["dwarf"], 40.5, 20.5)
        hero.invulnerable = True
        w = enemy("wisp", 31.5, 20.5)
        count = 0
        orig = combat.fire

        def counting(*a, **k):
            nonlocal count
            count += 1
            return orig(*a, **k)
        combat.fire = counting
        try:
            if not lit_always:
                config_cone, config.WISP_CONE_DEG = config.WISP_CONE_DEG, 0.0   # never lit
            run(w, hero, world, 4.0)
        finally:
            combat.fire = orig
            if not lit_always:
                config.WISP_CONE_DEG = config_cone
        return count

    def test_fires_without_the_light_and_much_faster_with_it(self):
        dark = self.shots_fired(False)
        lit = self.shots_fired(True)
        self.assertGreaterEqual(dark, 2)             # attacks normally, light or not
        self.assertGreater(lit, dark)


class ToadTest(unittest.TestCase):
    def test_hops_and_spits_a_fan(self):
        world = open_map()
        hero = Character(config.HEROES["bard"], 22.5, 10.5)
        hero.invulnerable = True
        t = enemy("toad", 15.5, 10.5)
        positions = []
        shots, effects = [], []
        fans = []
        for _ in range(int(4.0 / STEP)):
            ctx = AIContext(world, [hero], [hero, t], shots, effects)
            before = len(shots)
            t.think(ctx, STEP)
            if len(shots) > before:
                fans.append(len(shots) - before)
            positions.append((t.x, t.y))
            combat.update_projectiles(shots, world, effects, STEP, [hero, t])
        moved = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(positions, positions[1:])]
        self.assertTrue(any(m > 0.05 for m in moved))              # leaps...
        self.assertTrue(any(m < 1e-6 for m in moved))              # ...and sits
        self.assertTrue(fans)
        self.assertTrue(all(n == config.WEAPONS["acid_spit"].pellets for n in fans))


class SpitterTest(unittest.TestCase):
    def test_rings_of_eight_turning_each_volley(self):
        world = open_map()
        hero = Character(config.HEROES["wizard"], 18.5, 10.5)
        hero.invulnerable = True
        s = enemy("spitter", 12.5, 10.5)
        shots, effects = [], []
        rings = []
        for _ in range(int(5.0 / STEP)):
            ctx = AIContext(world, [hero], [hero, s], shots, effects)
            before = len(shots)
            s.think(ctx, STEP)
            if len(shots) > before:
                rings.append(sorted(p.angle % math.tau for p in shots[before:]))
        self.assertGreaterEqual(len(rings), 2)
        first = rings[0]
        self.assertEqual(len(first), 8)
        gaps = [(b - a) for a, b in zip(first, first[1:])]
        for g in gaps:
            self.assertAlmostEqual(g, math.tau / 8, places=6)
        turn = (rings[1][0] - rings[0][0]) % (math.tau / 8)
        self.assertAlmostEqual(turn, math.radians(config.SPITTER_RING_TURN_DEG), places=6)
        self.assertEqual((s.x, s.y), (12.5, 10.5))                 # never moves


class BoarTest(unittest.TestCase):
    def test_scrapes_then_charges_and_gores_once(self):
        world = open_map(w=80)
        hero = Character(config.HEROES["dwarf"], 18.5, 10.5)
        b = enemy("boar", 12.5, 10.5)
        states = []
        shots, effects = [], []
        for _ in range(int(2.5 / STEP)):
            ctx = AIContext(world, [hero], [hero, b], shots, effects)
            b.think(ctx, STEP)
            states.append(b.state)
        self.assertIn("scrape", states)
        self.assertIn("charge", states)
        self.assertLess(states.index("scrape"), states.index("charge"))
        self.assertAlmostEqual(hero.max_hp - hero.hp,
                               config.ENEMIES["boar"].damage * config.ENEMY_DAMAGE_MULTIPLIER)  # once

    def test_slamming_into_a_wall_hurts_the_wall_and_dazes_it(self):
        world = open_map(w=80, walls=[(24, y) for y in range(5, 16)])
        hero = Character(config.HEROES["dwarf"], 20.5, 10.5)
        hero.invulnerable = True
        b = enemy("boar", 13.5, 10.5)
        seen_dazed = False
        shots, effects = [], []
        for _ in range(int(4.0 / STEP)):
            ctx = AIContext(world, [hero], [hero, b], shots, effects)
            b.think(ctx, STEP)
            if b.state == "dazed":
                seen_dazed = True
                break
        self.assertTrue(seen_dazed)
        self.assertTrue(any(world.hp_at(24, y) is not None or world.tile_at(24, y) is not tiles.WALL
                            for y in range(5, 16)))


class DrawTest(unittest.TestCase):
    def test_every_new_enemy_draws_in_every_state(self):
        from engine import Display, TextRenderer
        from ascii_adventurers.engine_ext.camera import Camera
        from ascii_adventurers.render.ascii_fx import draw_projectiles
        from ascii_adventurers.render.enemies_sprite import draw_enemy
        from ascii_adventurers.render.sprites import SpriteBank
        d = Display(128, 30)
        text = TextRenderer(d)
        bank = SpriteBank(text, config.CELLS_PER_TILE)
        cam = Camera(128, 30, d.cell_w, d.cell_h)
        cam.center_on(15.0, 10.0)
        world = open_map()
        for key in NEW:
            e = enemy(key, 15.5, 10.5)
            e.hp = e.max_hp / 2
            for state in ("roam", "scrape", "charge", "dazed"):
                if key == "boar":
                    e.state, e.timer = state, 0.3
                if key == "wisp":
                    e.lit = state == "charge"
                draw_enemy(text, bank, cam, world, e)
        thrower = BombTest().thrower()
        shots = []
        combat.fire(thrower, world, shots, [], target=(18.5, 12.5))
        for k in range(6):
            shots[0].travelled = shots[0].flight * k / 6
            draw_projectiles(text, cam, shots)


if __name__ == "__main__":
    unittest.main()
