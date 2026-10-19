"""
systems/run_rules.py -- the cards and Guild Hall upgrades that react to
what happens in a run, rather than just changing a number.

The game scene (scenes/game.py) calls these hooks from its simulation
step; everything here stays deterministic (randomness comes from each
hero's seeded dice, time from the hero's run clock).

  attack_mods   before an attack: cards that act on every Nth attack
                (Quiver, Grand Finale, Syncopation, Echo) or on timing
                (Capacitor, Opening Act, Riposte);
  patterns      after an attack: the extra shots of the projectile pattern
                cards (Cross Fire, Starburst, Rear Guard, Spiral, Arrow
                Rain) and Sheet Music's notes;
  tick          every step, per living player: run clock, shield refill,
                Bloodlust / Frenzy timers, Retaliation, Echo's late attack;
  on_kill       a player's kill: Bloodlust, Frenzy, Soul Harvest, Bounty,
                Volatile / Chain Reaction, Pandemic, Shatter, the bestiary,
                the "15 kills in a second" achievement;
  on_level_up   Surge, the "level 30" achievement;
  revive        a hero falling: Phoenix, then the Guild's Second Chance;
  status_tricks / flee / enemy_shots  the head gear's tricks that need the
                other enemies (M28.2b: Permafrost, Panic, Exsanguinate,
                Geyser, Heat haze);
  resolve_combos  Thermal Shock and Toxic Current (systems/statuses.combos),
                and the head tricks' events (Rend, Tempest, Shatterpoint);
  pacts         what the dungeon gate's pacts do to the run.
"""

from __future__ import annotations

import heapq
import math
import random
from dataclasses import replace

from .. import config
from ..entities.effects import Effect
from ..entities.gems import drop
from . import statuses
from ..entities.projectile import Projectile
from .combat import _may_hurt, pulse, push, shot_origin, strike, volley
from .raycast import first_hit
from .statuses import daze, has, inflict
from .zones import Zone
from ..entities.character import wrap_angle


def _elite(enemy) -> bool:
    """An elite or bigger (a boss): the rings' "elite kills"."""
    spec = getattr(enemy, "espec", None)
    return bool(getattr(enemy, "boss", False) or (spec is not None and spec.elite))


class Chain:
    """One Volatile explosion and the ones it sets off (Domino Ring, M28.2e):
    how many went off, who burst, how often each enemy was hit (Domino
    effect), the first body's XP (Clean sweep), when the last one went off
    (Fuse line)."""

    def __init__(self, xp: float) -> None:
        self.n = 0
        self.burst: set = set()
        self.hits: dict = {}
        self.xp = xp
        self.swept = False
        self.last = -1e9


def _flood(world, x: float, y: float, limit: float) -> tuple[dict, dict]:
    """Birdsong: how far (tiles, by the shortest way round walls; diagonal
    steps only past open corners) each tile is from (x, y), out to
    `limit`, and the tile each was reached from."""
    start = (math.floor(x), math.floor(y))
    dist, parent = {start: 0.0}, {start: None}
    heap = [(0.0, start)]
    blocks = lambda tx, ty: world.tile_at(tx, ty).blocks_shots
    while heap:
        d, (tx, ty) = heapq.heappop(heap)
        if d > dist.get((tx, ty), math.inf):
            continue
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            nx, ny = tx + dx, ty + dy
            if blocks(nx, ny) or (dx and dy and (blocks(tx + dx, ty) or blocks(tx, ty + dy))):
                continue
            nd = d + (1.4142 if dx and dy else 1.0)
            if nd <= limit and nd < dist.get((nx, ny), math.inf):
                dist[(nx, ny)], parent[(nx, ny)] = nd, (tx, ty)
                heapq.heappush(heap, (nd, (nx, ny)))
    return dist, parent


def _tiles_to(parent: dict, tile) -> list:
    """The tiles from the flood's start to `tile` (start excluded)."""
    out = []
    while parent.get(tile) is not None:
        out.append(tile)
        tile = parent[tile]
    return out[::-1]


def _corners(world, hero, tiles: list, target) -> list:
    """A way along `tiles` cut down to the corners: from each point, on to
    the farthest tile centre (or the target) in a straight clear line."""
    points = [(tx + 0.5, ty + 0.5) for tx, ty in tiles] + [(target.x, target.y)]
    way, at, i = [], (hero.x, hero.y), 0
    while i < len(points):
        j = len(points) - 1
        while j > i and first_hit(world.tile_at, at[0], at[1], *points[j]) is not None:
            j -= 1
        at = points[j]
        way.append(at)
        i = j + 1
    return way


def _length(hero, way: list) -> float:
    pts = [(hero.x, hero.y)] + list(way)
    return sum(math.hypot(x1 - x0, y1 - y0) for (x0, y0), (x1, y1) in zip(pts, pts[1:]))


class RunRules:
    def __init__(self, scene) -> None:
        self.scene = scene
        self._ways: dict = {}          # (Songbird Lute +3: Birdsong, _note_targets)
        statuses.combos.clear()

    # --- Helpers ------------------------------------------------------------------------

    def _enemies_near(self, x: float, y: float, radius: float, source):
        for a in self.scene._actors():
            if a.hittable and _may_hurt(source, a) \
                    and math.hypot(a.x - x, a.y - y) <= radius + a.hit_radius:
                yield a

    def award(self, p, name: str) -> None:
        """An achievement (it may unlock cards in the archive)."""
        if p.ghost:
            return
        guild = self.scene.app.guild
        if name in guild.achievements:
            return
        guild.achievements.add(name)
        self.scene.app.save_guild()
        self.scene.effects.append(Effect("toast", p.hero.x, p.hero.y,
                                         label="ACHIEVEMENT: " + config.ACHIEVEMENTS[name]))
        if p.local:
            self.scene._sounds.append("chime")

    # --- Attacks ------------------------------------------------------------------------

    def attack_mods(self, p, echo: bool = False) -> dict:
        """This attack's changes (see combat.attack's keywords)."""
        hero, st = p.hero, p.hero.stats
        hero.attacks += 1
        n = hero.attacks
        kw = {"mult": 1.0, "extra_chain": 0, "extra_pellets": 0, "spread_add": 0.0,
              "reach_mult": 1.0}
        if echo:
            # Echo's repeat comes out turned off the aim, left and right in
            # turn, so it doesn't fly in the first one's line (M19). Canyon
            # Horn +3 (Reverb) sends it at another enemy; +9 (Canyon) makes
            # the echo's echo weaker (p.echo_mult).
            kw["angle_offset"] = math.radians(config.ECHO_ANGLE) * (1 if n % 2 else -1)
            kw["mult"] *= p.echo_mult
            if st is not None and st.has("echo+3"):
                other = self._reverb_target(hero)
                if other is not None:
                    kw["angle_offset"] = wrap_angle(
                        math.atan2(other.y - hero.y, other.x - hero.x) - hero.aim_angle)
        if st is None:
            return kw
        flags = st.flags
        if st.quiver:
            every = max(2, config.QUIVER_EVERY - (round(st.quiver) - 1))
            if n % every == 0:
                kw["extra_pellets"] += 1
                kw["spread_add"] += 4.0
        if "grand_finale" in flags:
            # Showstopper Lute +9 (Magnum opus): more often; +3 (Overture):
            # the first beat after a while without hitting anything.
            every = config.MAGNUM_OPUS if "grand_finale+9" in flags else config.GRAND_FINALE[0]
            if n % every == 0 or ("grand_finale+3" in flags and not echo
                                  and hero.time - hero.beat_hit >= config.OVERTURE - 1e-9):
                kw["mult"] *= config.GRAND_FINALE[1]
                kw["reach_mult"] *= config.GRAND_FINALE[2]
        if "syncopation" in flags:
            reach, dmg = self._syncopation(st, n)
            kw["mult"] *= dmg
            kw["reach_mult"] *= reach
            if n % 2 and "syncopation+3" in flags and not echo:   # (Offbeat Lute +3: Swing)
                hero.weapon.cooldown -= hero.weapon.spec.fire_interval * config.SWING_BEAT
        if st.capacitor and hero.idle >= config.CAPACITOR_IDLE:
            kw["mult"] *= 1 + st.capacitor
        if st.opening_act and hero.time < st.opening_act:
            kw["mult"] *= 2.0
        if st.has("deadeye+6") and n % config.SECOND_SIGHT == 0:
            kw["sure_crit"] = True                  # Farsight Bow +6 (Second sight)
        if hero.riposte > 0 and hero.riposte_left > 0:   # Riposte: just rolled
            kw["sure_crit"] = True
            hero.riposte_now = True                 # (Fencer's Boots: its hits, _attack)
            hero.riposte_left -= 1                  # (+6, Second thrust: two of them)
            if hero.riposte_left <= 0:
                hero.riposte = 0.0
        if st.has("ward_charm+6") and st.shield > 0 and hero.shield >= st.shield - 1e-6:
            kw["mult"] *= 1 + config.OVERCHARGE     # Wardweave Robe +6 (Overcharge)
        if hero.charged:                            # Gallopers +3 (Charge)
            kw["mult"] *= 1 + config.CHARGE[1]
            hero.charged, hero.walk_t = False, 0.0
        if "echo" in flags:
            # Every ECHO_EVERY attacks (echoes count, as before M28.2); Canyon
            # Horn +6 (Rolling echo): an echo's kill adds one (on_kill).
            p.echo_count += 1
            if not echo and p.echo_count >= config.ECHO_EVERY:
                p.echo_count = 0
                p.echo_timer, p.echo_stage, p.echo_mult = config.ECHO_DELAY, 1, 1.0
        hero.idle = 0.0
        return kw

    @staticmethod
    def _syncopation(st, n: int) -> tuple[float, float]:
        """Syncopation: beat n's (reach, damage) -- loud and short, soft and
        wide in turn (Offbeat Lute +9, The drop: a louder loud beat)."""
        reach, dmg = config.SYNCOPATION[n % 2]
        if n % 2 == 0 and st.has("syncopation+9"):
            dmg = config.THE_DROP
        return reach, dmg

    def beats(self, p, kw: dict) -> list[str]:
        """Offbeat Lute +6 (Polyrhythm): every POLYRHYTHM-th beat is both --
        the other kind of beat goes off with it (not counted as a beat of
        its own: Crescendo, Lullaby)."""
        hero, st = p.hero, p.hero.stats
        if st is None or hero.weapon.spec.kind != "pulse" or not st.has("syncopation+6") \
                or hero.attacks % config.POLYRHYTHM:
            return []
        n = hero.attacks
        reach, dmg = self._syncopation(st, n)
        other_reach, other_dmg = self._syncopation(st, n + 1)
        scene = self.scene
        return pulse(hero, scene.world, scene._actors(), scene.effects,
                            mult=kw["mult"] / dmg * other_dmg,
                            reach_mult=kw["reach_mult"] / reach * other_reach,
                            sure_crit=kw.get("sure_crit", False), origin=(hero.x, hero.y))

    def curtain_call(self, p) -> None:
        """Showstopper Lute +6 (Curtain call): dropping below CURTAIN_CALL[0]
        of max HP sets off a finale at once, every CURTAIN_CALL[1] s at most."""
        hero, st = p.hero, p.hero.stats
        low = hero.hp < hero.max_hp * config.CURTAIN_CALL[0]
        dropped = low and not hero.low
        hero.low = low
        if not dropped or not st.has("grand_finale+6") or hero.weapon.spec.kind != "pulse" \
                or hero.time - hero.curtain_t < config.CURTAIN_CALL[1] or not hero.alive:
            return
        hero.curtain_t = hero.time
        scene = self.scene
        sounds = pulse(hero, scene.world, scene._actors(), scene.effects,
                              mult=config.GRAND_FINALE[1], reach_mult=config.GRAND_FINALE[2],
                              origin=(hero.x, hero.y))
        if p.local:
            scene._sounds.extend(sounds)

    def _reverb_target(self, hero):
        """Canyon Horn +3: the nearest enemy that isn't the one aimed at
        (the one nearest the aim point)."""
        aim = getattr(hero, "aim_point", None)
        foes = [a for a in self.scene._actors() if a.hittable and a.alive and _may_hurt(hero, a)]
        aimed = None
        if aim is not None and foes:
            aimed = min(foes, key=lambda a: math.hypot(a.x - aim[0], a.y - aim[1]))
        others = [a for a in foes if a is not aimed]
        if not others:
            return None
        return min(others, key=lambda a: math.hypot(a.x - hero.x, a.y - hero.y))

    def _shooter(self, p, kw: dict):
        """What the pattern shots fire: (shoot, aim, pellets, spread, notes,
        targets), or None (no shots to fire). `shoot(angle, count, fan,
        mult)` fires a volley of the hero's own shots (or Sheet Music's
        notes) and returns the shots it made, sounds going to `sounds`."""
        hero, st = p.hero, p.hero.stats
        if st is None:
            return None
        spec = hero.weapon.spec
        notes = "sheet_music" in st.flags and spec.shell is None
        targets = []
        if spec.shell is not None:
            shell, damage, tags = spec.shell, spec.shell.damage, spec.tags
            pellets, spread, aim = spec.pellets, spec.spread_deg, hero.aim_angle
            origin = None
        elif notes:
            shell, damage = config.SPELL_SHELLS["note"], config.SHEET_MUSIC_DAMAGE
            tags = ("arcane", "projectile")
            pellets, spread, origin = 1, 0.0, (hero.x, hero.y)
            targets = self._note_targets(hero)
            aim = math.atan2(targets[0].y - hero.y, targets[0].x - hero.x) if targets \
                else hero.aim_angle
        else:
            return None
        scene = self.scene
        sounds: list[str] = []

        def shoot(angle, count=1, fan=0.0, mult=1.0) -> list[Projectile]:
            before = len(scene.projectiles)
            sounds.extend(volley(hero, scene.world, scene.projectiles, scene.effects, angle,
                                 count, fan, shell, tags, damage, mult=kw["mult"] * mult,
                                 extra_chain=kw.get("extra_chain", 0),
                                 sure_crit=kw.get("sure_crit", False),
                                 origin=origin))
            return scene.projectiles[before:]

        shoot.sounds = sounds
        return shoot, aim, pellets, spread, notes, targets

    def patterns(self, p, kw: dict) -> list[str]:
        """The extra shots the pattern cards add to the attack just made
        (with its keywords `kw`: damage, Riposte's crit). They're shots of
        the hero's own weapon, or Sheet Music's notes for the bard, and go
        off around the aim (the bard's: toward the nearest enemy). The
        off-hand's tricks (M28.2a, design/GEAR.md 17.1) change them."""
        hero, st = p.hero, p.hero.stats
        got = self._shooter(p, kw)
        if got is None:
            return []
        shoot, aim, pellets, spread, notes, targets = got
        flags = st.flags
        n = hero.attacks
        sounds = shoot.sounds

        if notes:
            # Sheet Music: one note at each of the nearest enemies; spare
            # notes (and all of them with nobody near) spread all round.
            # Songbird Lute +6 (Chorus): every so often each goes twice;
            # +3 (Birdsong): round walls (targets' ways from _note_targets).
            count = config.SHEET_MUSIC + round(st.pellets)
            twice = st.has("sheet_music+6") and n % config.CHORUS[0] == 0
            for _ in range(config.CHORUS[1] if twice else 1):
                for i in range(count):
                    if i < len(targets):
                        t = targets[i]
                        way = self._ways.get(id(t))
                        x, y = way[0] if way else (t.x, t.y)
                        for q in shoot(math.atan2(y - hero.y, x - hero.x)):
                            if way:
                                q.path, q.bird = list(way), t
                                q.max_range = max(q.max_range, _length(hero, way) + 1.0)
                    else:
                        shoot(aim + math.tau * i / count)
        every = config.CARDINAL_EVERY if st.has("cross_fire+9") else config.CROSS_FIRE_EVERY
        if "cross_fire" in flags and n % every == 0:
            # Compass Orb: +3 Needle turns every other cross 45 degrees; +6
            # North star's shots cut enemy shots; +9 Cardinal: every 2nd.
            turn = math.radians(config.NEEDLE_TURN) if st.has("cross_fire+3") and p.crosses % 2 \
                else 0.0
            p.crosses += 1
            for k in (1, 2, 3):
                for q in shoot(aim + turn + k * math.pi / 2, pellets, spread):
                    q.cancels = st.has("cross_fire+6")
        if "starburst" in flags:
            # Every STARBURST[0] attacks (a meter: Sunwheel +6 adds hits taken).
            p.burst_meter += 1
            if p.burst_meter >= config.STARBURST[0]:
                p.burst_meter -= config.STARBURST[0]
                self._ring(p, shoot, aim, kw)
        if "rear_guard" in flags:
            self._rear(p, shoot, aim, pellets, spread)
        if "spiral" in flags:
            self._spiral(p, shoot, aim)
        if "arrow_rain" in flags and not notes and n % config.ARROW_RAIN[0] == 0:
            sounds += self._arrow_rain(hero, kw)
            if st.has("arrow_rain+9"):               # Cloudburst Bow +9 (Squall line)
                self._arrow_rain(hero, kw, hold=config.SQUALL_LINE)
        return list(dict.fromkeys(sounds))

    def _ring(self, p, shoot, angle: float, kw: dict, second: bool = False) -> None:
        """Starburst's ring. Sunwheel +3 (Pinwheel): its shots curve as they
        fly; +9 (Corona): a second ring CORONA s later, between the first's."""
        st = p.hero.stats
        rays = config.STARBURST[1]
        for k in range(rays):
            for q in shoot(angle + k * math.tau / rays):
                if st.has("starburst+3"):
                    q.curve, q.curve_left = config.PINWHEEL_TURN, 1e9
        if st.has("starburst+9") and not second:
            p.corona = (config.CORONA, angle + math.pi / rays, dict(kw))

    def _rear(self, p, shoot, aim: float, pellets: int, spread: float, at=None) -> None:
        """Rear Guard's shot behind you. Hindsight Orb +3 (Over the
        shoulder): at the nearest enemy in your back half; +9 (Eyes in the
        back): a full copy of the attack at 100%. `at`: shoot at this enemy
        (Watchful)."""
        hero, st = p.hero, p.hero.stats
        angle = aim + math.pi
        target = at if at is not None else (self._behind(hero, self._reach(hero))
                                            if st.has("rear_guard+3") else None)
        if target is not None:
            angle = math.atan2(target.y - hero.y, target.x - hero.x)
        if st.has("rear_guard+9"):
            shoot(angle, pellets, spread)
        else:
            shoot(angle, mult=config.REAR_GUARD)

    @staticmethod
    def _reach(hero) -> float:
        shell = hero.weapon.spec.shell
        return shell.max_range if shell is not None else config.SHEET_MUSIC_REACH

    def _behind(self, hero, reach: float):
        """The nearest enemy within `reach` in the hero's back half (more
        than 90 degrees off the aim)."""
        best, best_d = None, reach
        for a in self.scene._actors():
            if not a.hittable or not a.alive or not _may_hurt(hero, a):
                continue
            d = math.hypot(a.x - hero.x, a.y - hero.y)
            off = abs(wrap_angle(math.atan2(a.y - hero.y, a.x - hero.x) - hero.aim_angle))
            if d <= best_d and off > math.pi / 2:
                best, best_d = a, d
        return best

    def _spiral(self, p, shoot, aim: float) -> None:
        """Spiral's extra shot. Nautilus Shell +3 (Growing shell): it grows as
        it flies; +6 (Double helix): a second one turning the other way; +9
        (Golden angle): 137.5 degrees a shot, and +1 for every 3 enemies
        within 8 tiles (up to +3)."""
        hero, st = p.hero, p.hero.stats
        golden = st.has("spiral+9")
        step = math.radians(config.GOLDEN_ANGLE if golden else config.SPIRAL_STEP)
        count = 1
        if golden:
            per, radius, most = config.GOLDEN_EXTRA
            near = sum(1 for _ in self._enemies_near(hero.x, hero.y, radius, hero))
            count += min(most, near // per)
        for _ in range(count):
            hero.spiral += 1
            shots = shoot(aim + step * hero.spiral)
            if st.has("spiral+6"):
                shots += shoot(aim - step * hero.spiral)
            if st.has("spiral+3"):
                for q in shots:
                    q.grow = True

    def bow_shots(self, p, shots) -> None:
        """The arrows an attack just let fly (M28.2h). Stillwater Bow +3
        (Held breath): after HELD_BREATH[0] s still, they fly x HELD_BREATH[1]
        as fast (then the breath starts over). Farsight Bow +9 (Lightning
        arrow): whether each crits is rolled now; a crit crosses its range
        at once, the rest can't crit."""
        hero, st = p.hero, p.hero.stats
        if st is None:
            return
        shell = hero.weapon.spec.shell
        mine = [q for q in shots if q.spec is shell and q.owner is hero]
        if not mine:
            return
        still, fast = config.HELD_BREATH
        if st.has("steady_aim+3") and hero.breath >= still:
            hero.breath = 0.0
            for q in mine:
                q.pace *= fast
        if st.has("deadeye+9"):
            from .combat import crit_chance
            for q in mine:
                if q.sure_crit or hero.rng.random() < crit_chance(st, hero) * q.crit_x:
                    q.sure_crit = True
                    q.pace *= config.LIGHTNING_ARROW
                else:
                    q.crit_x = 0.0

    def _arrow_rain(self, hero, kw: dict, hold: float = 0.0) -> list[str]:
        """Arrow Rain (P4): ARROW_RAIN[1] arrows (+1 per extra projectile)
        lobbed up from the bow, each coming down at a random spot within
        ARROW_RAIN[2] tiles of the aim point (no farther than the bow
        reaches), a little apart in time. The Cloudburst Bow: +3 (Monsoon)
        round the enemy nearest the aim point instead; +6 (Thunder rain)
        arrows landing close together hit harder; +9 a second rain `hold`
        s later (Squall line)."""
        every, count, radius, share = config.ARROW_RAIN
        st = hero.stats
        shell = hero.weapon.spec.shell
        rain = config.SPELL_SHELLS["rain_arrow"]
        aim = getattr(hero, "aim_point", None) or (
            hero.x + math.cos(hero.aim_angle) * shell.max_range / 2,
            hero.y + math.sin(hero.aim_angle) * shell.max_range / 2)
        if st.has("arrow_rain+3"):                   # Monsoon
            near = [a for a in self._enemies_near(hero.x, hero.y, shell.max_range, hero)]
            if near:
                t = min(near, key=lambda a: math.hypot(a.x - aim[0], a.y - aim[1]))
                aim = (t.x, t.y)
        mx, my = shot_origin(hero)
        rng = hero.rng
        arrows = []
        for _ in range(count + round(st.pellets)):
            r, a = radius * math.sqrt(rng.random()), math.tau * rng.random()
            tx, ty = aim[0] + math.cos(a) * r, aim[1] + math.sin(a) * r
            angle = math.atan2(ty - my, tx - mx)
            arrow = Projectile(mx, my, angle, rain, owner=hero, damage=shell.damage * share)
            arrow.flight = max(0.5, min(math.hypot(tx - mx, ty - my), shell.max_range))
            arrow.target = (mx + math.cos(angle) * arrow.flight,
                            my + math.sin(angle) * arrow.flight)
            arrow.tags = hero.weapon.spec.tags
            arrow.mult = kw["mult"]
            arrow.time_scale = 0.8 + 0.4 * rng.random()     # (they come down one by one)
            arrow.hold = hold
            arrows.append(arrow)
        if st.has("arrow_rain+6"):                   # Thunder rain
            close, more = config.THUNDER_RAIN
            for q in arrows:
                n = sum(1 for o in arrows if o is not q and
                        math.hypot(o.target[0] - q.target[0], o.target[1] - q.target[1]) <= close)
                q.mult *= 1 + more * n
        self.scene.projectiles.extend(arrows)
        return [rain.sound]

    def _note_targets(self, hero) -> list:
        """Enemies Sheet Music aims at: in sight within reach, nearest first.
        Songbird Lute +3 (Birdsong): ones behind walls too, if a note can fly
        round to them within BIRDSONG tiles (nearest by that way); their ways
        (corners, then the enemy) go in self._ways."""
        reach = config.SHEET_MUSIC_REACH
        world = self.scene.world
        self._ways = {}
        birdsong = hero.stats is not None and hero.stats.has("sheet_music+3")
        dist = parent = None
        near = []
        for i, a in enumerate(self.scene._actors()):
            if not a.hittable or not _may_hurt(hero, a):
                continue
            d = math.hypot(a.x - hero.x, a.y - hero.y)
            if d > reach:
                continue
            if first_hit(world.tile_at, hero.x, hero.y, a.x, a.y) is None:
                near.append((d, i, a))
            elif birdsong:
                if dist is None:
                    dist, parent = _flood(world, hero.x, hero.y, config.BIRDSONG)
                tile = (math.floor(a.x), math.floor(a.y))
                if tile in dist:
                    way = _corners(world, hero, _tiles_to(parent, tile), a)
                    if _length(hero, way) <= config.BIRDSONG:
                        self._ways[id(a)] = way
                        near.append((dist[tile], i, a))
        near.sort(key=lambda d: d[:2])
        return [a for _, _, a in near]

    def weapon_dt(self, p, dt: float) -> float:
        """Frenzy: the weapon's clock runs double for a while after a kill.
        Tumbler Boots +9 (Aerial): double again while rolling and just after."""
        hero = p.hero
        if hero.stats is not None and hero.stats.has("backflip+9") \
                and (hero.rolling or hero.aerial > 0):
            dt *= config.AERIAL[0]
        if hero.stats is not None and hero.stats.has("berserker+6") \
                and hero.hp < hero.max_hp * config.BLOODRAGE[0]:
            dt *= config.BLOODRAGE[1]               # Wolfpelt +6 (Bloodrage)
        dt *= 1 + config.WELCOME_HOME[0] * len(hero.welcome)   # Homesick Axe +6 (Welcome home)
        return dt * 2 if p.frenzy > 0 else dt

    # --- Every step ---------------------------------------------------------------------

    def tick(self, p, dt: float) -> None:
        hero, st = p.hero, p.hero.stats
        hero.time += dt
        hero.idle += dt
        hero.level = p.progress.level
        hero.run_loot = p.stats.loot
        hero.since_hit += dt
        hero.welcome = [t - dt for t in hero.welcome if t - dt > 0]   # (Homesick Axe +6)
        if hero.speed < config.STEADY_SPEED:
            hero.calm = hero.time                    # (Stillwater Bow +9: Still waters)
        hero.breath = hero.breath + dt if hero.speed < config.STILL_SPEED else 0.0
        if st is None:
            return
        if st.has("golden_hoard+3"):                 # Hoarder's Ring +3 (Miser)
            hero.run_loot += p.salvaged * (config.MISER - 1)
        if st.shield > 0 and hero.shield < st.shield \
                and hero.since_hit >= config.SHIELD_RECHARGE_DELAY:
            hero.shield = min(st.shield, hero.shield + st.shield * config.SHIELD_RECHARGE_RATE * dt)
        if hero.bloodlust:
            if st.has("bloodlust+6"):                # Fang Ring +6 (Slow fade)
                hero.fade_t = max(0.0, hero.fade_t - dt)
                if hero.fade_t <= 0 and hero.bloodlust[0] <= hero.time:
                    hero.bloodlust.pop(0)
                    hero.fade_t = config.SLOW_FADE
            else:
                hero.bloodlust = [t for t in hero.bloodlust if t > hero.time]
        p.frenzy = max(0.0, p.frenzy - dt)
        hero.unshaken = p.frenzy > 0 and st.has("frenzy+6")       # War Drum +6
        self._offhand_tick(p, dt)
        self._feet_tick(p, dt)
        self._chest_tick(p, dt)
        self._ring_tick(p, dt)
        if st.has("grand_finale+6"):
            self.curtain_call(p)                     # (Showstopper Lute +6)
        if hero.duelist is not None and not hero.duelist.alive:
            hero.duelist = None                      # (Duelist's Wand +6: it fell)
        p.retaliate_cd = max(0.0, p.retaliate_cd - dt)
        if hero.retaliate:
            hero.retaliate = False
            hits, big = hero.retaliate_hits, hero.retaliate_big
            hero.retaliate_hits, hero.retaliate_big = 0, 0.0
            if st.has("retaliation+9"):                              # Seething
                if big >= config.SEETHING:
                    self._retaliate(p)
            elif st.has("retaliation") and p.retaliate_cd <= 0:
                self._retaliate(p)
            elif st.has("retaliation+6"):                            # Rising grudge
                per, most = config.RISING_GRUDGE
                hero.grudge = min(most, hero.grudge + per * hits)
        if p.echo_timer > 0:
            p.echo_timer -= dt
            if p.echo_timer <= 0:
                self.scene._attack(p, echo=True)
                if p.echo_stage == 1 and st.has("echo+9"):          # Canyon: once more
                    p.echo_stage, p.echo_mult = 2, config.ECHO_THIRD
                    p.echo_timer = config.ECHO_DELAY
                else:
                    p.echo_stage, p.echo_mult = 0, 1.0

    def _ring_tick(self, p, dt: float) -> None:
        """The rings' tricks on the clock (M28.2e): Deluge's crits running
        out, Golden armor, Fuse line's waiting explosions, Lighthouse."""
        hero, st = p.hero, p.hero.stats
        if hero.deluge:
            hero.deluge = [t for t in hero.deluge if t > hero.time]
        if st.has("golden_hoard+6"):                 # Hoarder's Ring +6 (Golden armor)
            per, most = config.GOLDEN_ARMOR
            hero.hoard_armor = min(most, int(hero.run_loot // per))
        else:
            hero.hoard_armor = 0
        if p.fuses:
            due = [f for f in p.fuses if f[0] <= hero.time + 1e-9]
            p.fuses = [f for f in p.fuses if f[0] > hero.time + 1e-9]
            for _, enemy, chain in due:
                self._explode(hero, enemy, chain)
        if st.has("beacon+9"):
            self._lighthouse(p, dt)

    def _lighthouse(self, p, dt: float) -> None:
        """Beckoning Ring +9: every LIGHTHOUSE[0] s a wave comes for the
        hero; all of it dead within LIGHTHOUSE[1] s gives a gear pick."""
        hero = p.hero
        every, window, _, _ = config.LIGHTHOUSE
        if p.wave is not None:
            until, wave = p.wave
            if all(not e.alive for e in wave):
                p.wave = None
                if hero.time <= until + 1e-9:
                    p.progress.picks += 1
                    self._toast(p, "LIGHTHOUSE: +1 gear pick")
            elif hero.time > until:
                p.wave = None
        p.lighthouse_t += dt
        if p.lighthouse_t >= every:
            p.lighthouse_t -= every
            self._wave(p)

    def _wave(self, p) -> None:
        """Lighthouse's wave: LIGHTHOUSE[2] of the biome's enemies round the
        hero, coming for them (none in a boss arena)."""
        from . import mount
        from .quests import free_spot
        scene, hero = self.scene, p.hero
        sp = scene.spawner
        biome_at = getattr(scene.world, "biome_at", None)
        if sp is None or biome_at is None or mount.in_arena(scene, hero):
            return
        biome = biome_at(math.floor(hero.x), math.floor(hero.y)).name
        choices = [(k, e.weight) for k, e in config.ENEMIES.items()
                   if biome in e.biomes and e.weight > 0 and e.kind != "tower"]
        if not choices:
            return
        _, window, size, (lo, hi) = config.LIGHTHOUSE
        rng = hero.rng
        wave = []
        for _ in range(size):
            key = rng.choices([c[0] for c in choices], [c[1] for c in choices])[0]
            a, r = rng.uniform(0, math.tau), rng.uniform(lo, hi)
            ex, ey = free_spot(scene.world, hero.x + math.cos(a) * r, hero.y + math.sin(a) * r, 9.0)
            e = sp.wake(key, ex, ey, None, random.Random(rng.random()))
            e.alert = True
            e.drawn_to = hero
            scene.enemies.append(e)
            scene.effects.append(Effect("eruption", ex, ey))
            wave.append(e)
        p.wave = (hero.time + window, wave)
        self._toast(p, "LIGHTHOUSE: a wave comes")

    def _toast(self, p, label: str) -> None:
        self.scene.effects.append(Effect("toast", p.hero.x, p.hero.y, label=label))
        if p.local:
            self.scene._sounds.append("chime")

    def beacon_tricks(self) -> None:
        """Every step: Beckoning Ring +6 (Moth to flame) -- the extra
        enemies Beacon brings (spawner `beckoned`) are drawn to the nearest
        hero wearing it, and keep MOTH tiles from them (archers too)."""
        heroes = [p.hero for p in self.scene.players if p.hero.alive and has(p.hero, "beacon+6")]
        if not heroes:
            return
        for e in self.scene.enemies:
            if getattr(e, "beckoned", False) and getattr(e, "drawn_to", None) is None \
                    and e.alive and not getattr(e, "boss", False):
                e.drawn_to = min(heroes, key=lambda h: math.hypot(h.x - e.x, h.y - e.y))
                if hasattr(e.espec, "preferred_range"):
                    e.espec = replace(e.espec, preferred_range=config.MOTH)

    def _chest_tick(self, p, dt: float) -> None:
        """The chest's tricks on the clock (M28.2d): standing still, the
        timers, Clean getaway, Fortify, Garrison, the auras (Overgrowth,
        Tremor, Radiant), the shields (Second ward, Eternal day; Static
        weave and Corona burst when one breaks) and Wild hedge."""
        hero, st = p.hero, p.hero.stats
        scene = self.scene
        hero.still_t = hero.still_t + dt if hero.speed < config.STILL_SPEED else 0.0
        hero.temper = [t - dt for t in hero.temper if t - dt > 0]
        hero.last_stand = max(0.0, hero.last_stand - dt)
        hero.stand_cd = max(0.0, hero.stand_cd - dt)
        hero.getaway = max(0.0, hero.getaway - dt)
        above = hero.hp >= hero.max_hp * config.UNTOUCHED_HP
        if hero.above90 and not above and st.has("untouched+3"):
            hero.getaway = config.CLEAN_GETAWAY[1]                    # Clean getaway
        hero.above90 = above
        if st.has("bulwark+3") and not scene.pacts["famine"] and hero.irradiated <= 0:
            extra = hero.max_hp - config.HEROES[p.stats.hero].max_hp
            if extra > 0:
                hero.heal(extra / 10 * config.FORTIFY * dt)           # Fortify
        if st.has("bulwark+6"):
            hero.near_wall = self._near_wall(hero, config.GARRISON[0])   # Garrison
        if st.has("thorn_mail+6") and hero.still_t >= config.OVERGROWTH[0]:   # Overgrowth
            hero.bramble_t = self._aura(hero, hero.bramble_t, dt, config.OVERGROWTH[1],
                                        config.OVERGROWTH[2], ("physical",))
        else:
            hero.bramble_t = 0.0
        if st.has("juggernaut+6") and hero.speed > 0.5:              # Tremor
            hero.tremor_t = self._aura(hero, hero.tremor_t, dt, config.TREMOR[1],
                                       config.TREMOR[0], ("physical",))
        if st.has("aegis+3") and hero.shield > 0:                     # Radiant
            hero.radiant_t -= dt
            if hero.radiant_t <= 0:
                hero.radiant_t += config.RADIANT[1]
                for a in list(self._enemies_near(hero.x, hero.y, config.RADIANT[0], hero)):
                    inflict(a, "burn", hero)
        else:
            hero.radiant_t = 0.0
        if st.has("ward_charm+9") and st.shield > 0:                 # Second ward
            full = hero.shield >= st.shield - 1e-6
            hero.ward_full_t = hero.ward_full_t + dt if full else 0.0
            if hero.ward_full_t >= config.SECOND_WARD[0]:
                hero.shield = max(hero.shield, st.shield * (1 + config.SECOND_WARD[1]))
        if st.has("aegis+9"):                                         # Eternal day
            rate, most = config.ETERNAL_DAY
            if hero.shield < hero.max_hp * most:
                hero.shield = min(hero.max_hp * most, hero.shield + hero.max_hp * rate * dt)
        if hero.shield_broke > 0:
            size, hero.shield_broke = hero.shield_broke, 0.0
            if st.has("ward_charm+3"):                                # Static weave
                scene.effects.append(Effect("pulse", hero.x, hero.y, size=config.STATIC_WEAVE))
                for a in list(self._enemies_near(hero.x, hero.y, config.STATIC_WEAVE, hero)):
                    inflict(a, "shock", hero)
            if st.has("aegis+6"):                                     # Corona burst
                scene.effects.append(Effect("nova", hero.x, hero.y, size=config.CORONA_BURST))
                for a in list(self._enemies_near(hero.x, hero.y, config.CORONA_BURST, hero)):
                    self._number(a, a.take_damage(size, hero, None), "burn")
        if hero.hedge:                                                # Wild hedge
            for src, dealt in hero.hedge:
                for a in list(self._enemies_near(src.x, src.y, config.WILD_HEDGE, hero)):
                    if a is src:
                        continue
                    self._number(a, a.take_damage(dealt, hero, None), "")
                    if a.alive and st.has("thorn_mail+3"):
                        inflict(a, "bleed", hero, config.BARBS)
            hero.hedge = []

    def _aura(self, hero, clock: float, dt: float, radius: float, dps: float, tags) -> float:
        """An aura round the hero: every half second, half its damage a
        second to the enemies in it. Returns the clock."""
        clock -= dt
        if clock <= 0:
            clock += 0.5
            for a in list(self._enemies_near(hero.x, hero.y, radius, hero)):
                strike(a, dps * 0.5, hero, None, self.scene.effects, tags, on_hit=False)
        return clock

    def _near_wall(self, hero, reach: float) -> bool:
        """Garrison: a wall (anything solid that stops shots) within
        `reach` tiles."""
        tile_at = self.scene.world.tile_at
        for ty in range(math.floor(hero.y - reach), math.floor(hero.y + reach) + 1):
            for tx in range(math.floor(hero.x - reach), math.floor(hero.x + reach) + 1):
                cx = min(max(hero.x, tx), tx + 1)
                cy = min(max(hero.y, ty), ty + 1)
                if math.hypot(cx - hero.x, cy - hero.y) > reach:
                    continue
                t = tile_at(tx, ty)
                if t.solid and t.blocks_shots:
                    return True
        return False

    def _feet_tick(self, p, dt: float) -> None:
        """The feet's tricks on the clock (M28.2c): Gallopers +3 (Charge:
        2 s walking without stopping) and +6 (Hoofbeats every 10 tiles)."""
        hero, st = p.hero, p.hero.stats
        if not st.has("momentum"):
            return
        hero.walk_t = hero.walk_t + dt if hero.speed > 0.5 else 0.0
        if st.has("momentum+3") and hero.walk_t >= config.CHARGE[0]:
            hero.charged = True
        if st.has("momentum+6") and hero.walked >= hero.hoof:
            every, reach, damage = config.HOOFBEATS
            hero.hoof = hero.walked + every
            foes = [a for a in self._enemies_near(hero.x, hero.y, reach, hero) if a.alive]
            if foes:
                a = min(foes, key=lambda a: math.hypot(a.x - hero.x, a.y - hero.y))
                self.scene.effects.append(Effect("eruption", a.x, a.y))
                strike(a, damage, hero, None, self.scene.effects, ("physical",), on_hit=False)
                if p.local:
                    self.scene._sounds.append("break")

    def feet_tricks(self, dt: float) -> None:
        """Every step: the feet tricks that act on enemies and zones --
        Disarm's and Dizzy's clocks, Ashwalkers +3 (Creeping fire)."""
        for e in self.scene.enemies:
            if getattr(e, "disarmed", 0) > 0:
                e.disarmed = max(0.0, e.disarmed - dt)
            if getattr(e, "dizzy", 0) > 0:
                e.dizzy = max(0.0, e.dizzy - dt)
        wait, reach = config.CREEPING_FIRE
        for z in list(self.scene.zones):
            if z.kind != "trail" or getattr(z, "crept", True) is not False \
                    or z.age < wait or not has(z.source, "scorched_trail+3"):
                continue
            z.crept = True
            foes = [a for a in self._enemies_near(z.x, z.y, reach, z.source) if a.alive]
            if not foes:
                continue
            a = min(foes, key=lambda a: math.hypot(a.x - z.x, a.y - z.y))
            ang = math.atan2(a.y - z.y, a.x - z.x)
            step = z.radius * 1.6
            c = type(z)("trail", z.x + math.cos(ang) * step, z.y + math.sin(ang) * step, z.radius,
                        z.life, z.every, z.damage, z.source, z.tags, z.inflicts, z.stacks)
            c.roll, c.crept = getattr(z, "roll", 0), True        # (it creeps once)
            self.scene.zones.append(c)

    def _offhand_tick(self, p, dt: float) -> None:
        """The off-hand's tricks that run on the clock (M28.2a): Sunwheel +6
        counts hits taken toward the burst, +9's second ring; Hindsight Orb
        +6 (Watchful) shoots what comes up behind you."""
        hero, st = p.hero, p.hero.stats
        taken = hero.hits_taken - p.hits_seen
        p.hits_seen = hero.hits_taken
        if taken > 0 and st.has("starburst") and st.has("starburst+6"):
            p.burst_meter += config.PAIN_WHEEL * taken
        if p.corona is not None:
            left, angle, kw = p.corona
            left -= dt
            p.corona = (left, angle, kw) if left > 0 else None
            if left <= 0:
                got = self._shooter(p, kw)
                if got is not None:
                    self._ring(p, got[0], angle, kw, second=True)
        p.watch_cd = max(0.0, p.watch_cd - dt)
        if st.has("rear_guard") and st.has("rear_guard+6") and p.watch_cd <= 0 and hero.alive:
            close = self._behind(hero, config.WATCHFUL[0])
            if close is not None:
                kw = {"mult": 1.0}
                got = self._shooter(p, kw)
                if got is not None:
                    shoot, aim, pellets, spread = got[:4]
                    self._rear(p, shoot, aim, pellets, spread, at=close)
                    p.watch_cd = config.WATCHFUL[1]

    def _retaliate(self, p) -> None:
        damage, radius, cooldown, shove = config.RETALIATION
        hero = p.hero
        p.retaliate_cd = cooldown
        damage += hero.grudge                       # (Grudge Mail +6: Rising grudge)
        hero.grudge = 0.0
        if hero.stats.has("retaliation+3") and hero.retaliate_from is not None:   # Recoil
            fx, fy = hero.retaliate_from
            away = math.atan2(hero.y - fy, hero.x - fx)
            push(hero, self.scene.world, math.cos(away) * config.RECOIL,
                 math.sin(away) * config.RECOIL, full=True)
        self.scene.effects.append(Effect("pulse", hero.x, hero.y, size=radius))
        for a in list(self._enemies_near(hero.x, hero.y, radius, hero)):
            angle = math.atan2(a.y - hero.y, a.x - hero.x)
            strike(a, damage, hero, angle, self.scene.effects, ("physical",), on_hit=False)
            push(a, self.scene.world, math.cos(angle) * shove, math.sin(angle) * shove)

    # --- Kills --------------------------------------------------------------------------

    def on_kill(self, p, enemy) -> None:
        hero, st = p.hero, p.hero.stats
        scene = self.scene
        self._bestiary(p, enemy)
        p.kill_times = [t for t in p.kill_times if t > hero.time - config.ACHIEVEMENT_BURST[1]]
        p.kill_times.append(hero.time)
        if len(p.kill_times) >= config.ACHIEVEMENT_BURST[0]:
            self.award(p, "chain_reaction")
        if st is None:
            return
        flags = st.flags
        last, p.last_kill = p.last_kill, hero.time
        hero.kill_spot = (enemy.x, enemy.y)                 # (Skull Sentry +3: Ossuary)
        elite = _elite(enemy)
        if "bloodlust" in flags:
            most = config.APEX[0] if "bloodlust+9" in flags else config.BLOODLUST_MAX   # (Apex)
            n = 2 if "bloodlust+3" in flags and getattr(enemy, "one_hit", False) else 1
            hero.bloodlust += [hero.time + config.BLOODLUST_TIME] * n   # (+3: Feeding frenzy)
            del hero.bloodlust[:-most]
        if "frenzy" in flags:
            # War Drum: +3 (Drumroll) a kill in a frenzy adds to it; +9 (War
            # dance) each new frenzy dazes what's round you.
            starting = p.frenzy <= 0
            if st.has("frenzy+3") and not starting:
                add, most = config.DRUMROLL
                p.frenzy = max(config.FRENZY_TIME, min(most, p.frenzy + add))
            else:
                p.frenzy = config.FRENZY_TIME
            if starting and st.has("frenzy+9"):
                radius, seconds = config.WAR_DANCE
                scene.effects.append(Effect("pulse", hero.x, hero.y, size=radius))
                for a in list(self._enemies_near(hero.x, hero.y, radius, hero)):
                    daze(a, seconds)
        if "echo" in flags and st.has("echo+6") and getattr(enemy, "echo_kill", False):
            p.echo_count += 1                                      # Rolling echo
        if st.soul_harvest:
            # Reaper's Band: +3 (Reap) elites heal REAP, +9 (Reaper) 1% of
            # max HP if that's more, +6 (Grim) double soon after a kill; the
            # power's +10% a level on top.
            heal = config.REAP if "soul_harvest+3" in flags and elite else 1.0
            if "soul_harvest+9" in flags:
                heal = max(heal, hero.max_hp * config.REAPER)
            if "soul_harvest+6" in flags and hero.time - last <= config.GRIM[0]:
                heal *= config.GRIM[1]
            hero.heal(st.soul_harvest * heal)
        if "bounty" in flags:
            p.bounty += 1
            if p.bounty % config.BOUNTY_EVERY == 0:
                big = config.BIG_GAME if "bounty+3" in flags and elite else 1   # (Big game)
                scene._loot(p, enemy, times=config.BOUNTY_EVERY * big)
                if "bounty+6" in flags and hero.rng.random() < config.HUNTERS_PAY:
                    scene._bag_piece(p)                                 # (Hunter's pay)
        if "giant_slayer+6" in flags and enemy.max_hp > hero.max_hp:
            scene._loot(p, enemy, times=config.TOPPLED_GIANT)          # Slingstone +6
        st_e = enemy.status
        if "pandemic" in flags and st_e is not None:
            self._pandemic(hero, enemy)
        if "shatter" in flags and st_e is not None and st_e.frozen > 0:
            radius, damage = config.SHATTER[1], config.SHATTER[2]
            scene.effects.append(Effect("nova", enemy.x, enemy.y, size=radius))
            for a in list(self._enemies_near(enemy.x, enemy.y, radius, hero)):
                strike(a, damage, hero, None, scene.effects, ("frost",), on_hit=False)
                if a.alive:
                    inflict(a, "chill", hero)
            if st.has("shatter+6"):
                self._shards(hero, enemy)                   # Glassfrost Helm +6 (Splinters)
        if "volatile" in flags:
            blasted = getattr(enemy, "blasted", False)
            chain = blasted if isinstance(blasted, Chain) else None
            chained = bool(blasted) and "chain_reaction" in flags and (
                chain is None or id(enemy) not in chain.burst)
            roll = hero.rng.random() < config.VOLATILE_CHANCE + p.fuse
            boom = roll or chained or ("volatile+3" in flags and elite)   # (+3: Big bang)
            if "volatile+6" in flags:                                  # Short fuse
                p.fuse = 0.0 if boom else p.fuse + config.SHORT_FUSE
            if boom:
                self._boom(p, enemy, chain if chained else None)

    def _shards(self, hero, enemy) -> None:
        """Splinters: SPLINTERS[0] ice shards fly out of a shattered enemy,
        all round, each hitting once and chilling (they don't crit or roll
        your statuses, like the burst)."""
        n, reach = config.SPLINTERS
        turn = hero.rng.uniform(0, math.tau / n)
        for k in range(n):
            q = Projectile(enemy.x, enemy.y, turn + k * math.tau / n, config.ICE_SHARD_SHOT,
                           owner=hero, damage=config.SHATTER[2])
            q.max_range = reach
            q.tags, q.inflicts, q.summon, q.child = ("frost",), ("chill", 1), True, True
            q.hit.add(id(enemy))
            self.scene.projectiles.append(q)

    def _boom(self, p, enemy, chain) -> None:
        """An explosion now, or -- one of a chain, with Domino Ring +3 (Fuse
        line) -- FUSE_LINE[0] s after the chain's last one."""
        hero = p.hero
        if chain is not None and hero.stats.has("chain_reaction+3"):
            chain.last = max(hero.time, chain.last) + config.FUSE_LINE[0]
            p.fuses.append((chain.last, enemy, chain))
        else:
            self._explode(hero, enemy, chain)

    def _explode(self, hero, enemy, chain: Chain | None = None) -> None:
        """Volatile: the body bursts for part of the hit that killed it.
        With Chain Reaction, what that kills bursts too (each body once).
        The Powderkeg and Domino tricks: +9 Powder keg (+ of its max HP),
        Fuse line (each of a chain bigger), Clean sweep (a gem for a long
        chain), Domino effect (hit twice by one chain: it bursts, alive)."""
        st = hero.stats
        if chain is None:
            spec = getattr(enemy, "espec", None)
            chain = Chain(spec.xp if spec is not None else 0.0)
        chain.n += 1
        chain.burst.add(id(enemy))
        damage = getattr(enemy, "last_damage", 0.0) * config.VOLATILE_DAMAGE
        if st.has("volatile+9"):
            damage += enemy.max_hp * config.POWDER_KEG
        radius = config.VOLATILE_RADIUS
        if st.has("chain_reaction+3"):
            size = (1 + config.FUSE_LINE[1]) ** (chain.n - 1)
            damage, radius = damage * size, radius * size
        self.scene.effects.append(Effect("explosion", enemy.x, enemy.y))
        if radius > config.VOLATILE_RADIUS + 1e-9:
            self.scene.effects.append(Effect("nova", enemy.x, enemy.y, size=radius))
        self.scene._sounds.append("break")
        domino = []
        for a in list(self._enemies_near(enemy.x, enemy.y, radius, hero)):
            if a is enemy:
                continue
            strike(a, damage, hero, None, self.scene.effects, ("area",), on_hit=False)
            chain.hits[id(a)] = chain.hits.get(id(a), 0) + 1
            if not a.alive:
                a.blasted = chain
            elif st.has("chain_reaction+9") and chain.hits[id(a)] >= 2 \
                    and id(a) not in chain.burst:
                domino.append(a)
        if st.has("chain_reaction+6") and chain.n >= config.CLEAN_SWEEP[0] and not chain.swept:
            chain.swept = True                       # Domino Ring +6 (Clean sweep)
            drop(self.scene.gems, enemy.x, enemy.y, chain.xp * config.CLEAN_SWEEP[1])
        p = self.scene._player_of(hero)
        for a in domino:                             # Domino effect
            if p is not None:
                self._boom(p, a, chain)
            else:
                self._explode(hero, a, chain)

    def _pandemic(self, hero, enemy, n: int | None = None, names=None) -> None:
        """A dying enemy's statuses spread to the n nearest. Contagion Ring:
        +3 (Airborne) farther, +6 (Mutation) a stack more, +9 (Plague) from
        the living too (status_tricks: `names`, the ones that are the
        hero's)."""
        st = hero.stats
        reach = config.AIRBORNE if st.has("pandemic+3") else config.PANDEMIC[1]
        n = config.PANDEMIC[0] if n is None else n
        add = config.MUTATION if st.has("pandemic+6") else 0
        others = sorted((a for a in self._enemies_near(enemy.x, enemy.y, reach, hero)
                         if a is not enemy),
                        key=lambda a: math.hypot(a.x - enemy.x, a.y - enemy.y))[:n]
        for name, s in sorted(enemy.status.active.items()):
            if names is not None and name not in names:
                continue
            for a in others:
                inflict(a, name, hero, s.stacks + add)

    def _bestiary(self, p, enemy) -> None:
        if p.ghost:
            return
        kind = getattr(enemy, "kind_key", None)
        if kind is None:
            return
        guild = self.scene.app.guild
        guild.kills[kind] = guild.kills.get(kind, 0) + 1
        if guild.known(kind):
            p.hero.bestiary.add(kind)

    # --- Levels -------------------------------------------------------------------------

    def on_level_up(self, p, gained: int = 1) -> None:
        """`gained` levels just came. The rings' every-Nth-level tricks:
        Ascendant Band +9 (Apotheosis: a gear pick), Grizzled Signet +6
        (Drilled: a free UPGRADE), Fourleaf Ring +6 (Charmed: a reroll)."""
        hero, st = p.hero, p.hero.stats
        prog = p.progress
        if prog.level >= 30:
            self.award(p, "level_30")
        if st is None:
            return
        for level in range(prog.level - gained + 1, prog.level + 1):
            if st.has("surge+9") and level % config.APOTHEOSIS == 0:
                prog.picks += 1
                self._toast(p, "APOTHEOSIS: +1 gear pick")
            if st.has("veteran+6") and level % config.DRILLED == 0:
                prog.free_upgrades += 1
                self._toast(p, "DRILLED: a free UPGRADE")
            if st.has("fortune+6") and level % config.CHARMED == 0:
                prog.rerolls += 1
        if st.has("surge"):
            self.surge(p)

    def on_upgrade(self, p) -> None:
        """An UPGRADE pick was used: Ascendant Band +6 (Ascend)."""
        if has(p.hero, "surge") and has(p.hero, "surge+6"):
            self.surge(p)

    def surge(self, p) -> None:
        """Surge: heal SURGE_HEAL and blast what's round you away; Ascendant
        Band +3 (Rising): the blast hits for RISING per level."""
        hero, st = p.hero, p.hero.stats
        hero.heal(hero.max_hp * config.SURGE_HEAL)
        reach, shove = config.SURGE_PUSH
        self.scene.effects.append(Effect("pulse", hero.x, hero.y, size=reach))
        for a in list(self._enemies_near(hero.x, hero.y, reach, hero)):
            angle = math.atan2(a.y - hero.y, a.x - hero.x)
            if st.has("surge+3"):
                strike(a, config.RISING * p.progress.level, hero, angle, self.scene.effects,
                       ("area",), on_hit=False)
            if a.alive:
                push(a, self.scene.world, math.cos(angle) * shove, math.sin(angle) * shove)

    def check_build(self, p) -> None:
        """After the hero's build changes: build achievements."""
        st = p.hero.stats
        if st is not None and st.crit_chance >= 0.75:
            self.award(p, "crit_75")

    # --- Falling ------------------------------------------------------------------------

    def revive(self, p) -> bool:
        """A hero at 0 HP: Phoenix (a card), then Second Chance (the Guild)."""
        hero, st = p.hero, p.hero.stats
        hero.duelist = None                         # (Duelist's Wand +6: the duel is over)
        if st is None:
            return False
        scene = self.scene
        rises = st.phoenix + (1 if st.phoenix and st.has("phoenix+9") else 0)   # (Undying flame)
        if rises > p.phoenix_used:
            p.phoenix_used += 1
            frac, radius, damage = config.PHOENIX
            hero.hp = hero.max_hp * frac
            scene.effects.append(Effect("explosion", hero.x, hero.y))
            scene.effects.append(Effect("nova", hero.x, hero.y, size=radius))
            for a in list(self._enemies_near(hero.x, hero.y, radius, hero)):
                strike(a, damage, hero, None, scene.effects, ("fire",), on_hit=False)
                if a.alive:
                    inflict(a, "burn", hero, 3)
            if st.has("phoenix+3"):                                   # Ashes
                n, ring, life = config.ASHES
                for k in range(n):
                    ang = k * math.tau / n
                    scene.zones.append(Zone("trail", hero.x + math.cos(ang) * ring,
                                            hero.y + math.sin(ang) * ring, config.TRAIL_RADIUS,
                                            life, config.TRAIL_EVERY, 0.0, hero,
                                            (config.STATUSES["burn"].tag,), "burn"))
            if st.has("phoenix+6"):
                hero.untouchable = max(hero.untouchable, config.REBIRTH)   # Rebirth
        elif st.revives > p.revives_used:
            p.revives_used += 1
            hero.hp = hero.max_hp * config.SECOND_CHANCE_HP
        else:
            return False
        scene.effects.append(Effect("toast", hero.x, hero.y, label="RISE AGAIN!"))
        if p.local:
            scene._sounds.append("chime")
        return True

    # --- The head gear's tricks (M28.2b) ----------------------------------------------

    def status_tricks(self, dt: float) -> None:
        """Every step: the head tricks that need the other enemies or a
        clock (Permafrost, Panic, Exsanguinate, Geyser)."""
        enemies = self.scene.enemies
        for e in enemies:
            st = e.status
            if st is None or not e.alive:
                continue
            boss = getattr(e, "boss", False)
            if st.frozen > 0 and has(st.frozen_by, "frostbite+9"):     # Permafrost
                st.perma -= dt
                if st.perma <= 0:
                    st.perma += config.PERMAFROST[0]
                    for a in enemies:
                        if a is not e and a.alive and a.hittable and math.hypot(
                                a.x - e.x, a.y - e.y) <= e.hit_radius + a.hit_radius \
                                + config.PERMAFROST[1]:
                            inflict(a, "chill", st.frozen_by)
            else:
                st.perma = 0.0
            bleed = st.active.get("bleed")
            if bleed is not None:
                src, frac = bleed.source, e.hp / max(1, e.max_hp)
                if frac < config.PANIC[0] and has(src, "hemorrhage+3") and not boss \
                        and not getattr(e, "panicked", False):            # Panic
                    e.panicked = True
                    st.scared, st.scared_from = config.PANIC[1], src
                if frac < config.EXSANGUINATE[0] and has(src, "serrated+9"):   # Exsanguinate
                    if not boss:
                        self._number(e, e.take_damage(e.max_hp, src, None), "bleed")
                    elif "exsanguinate" not in st.cooldowns:
                        st.cooldowns["exsanguinate"] = config.EXSANGUINATE[2]
                        self._number(e, e.take_damage(config.EXSANGUINATE[1], src, None), "bleed")
            if e.alive and st.active:                                     # Plague
                spread = {}
                for name, s in st.active.items():
                    if has(s.source, "pandemic") and has(s.source, "pandemic+9"):
                        spread.setdefault(s.source, set()).add(name)
                if spread:
                    e.plague_t = getattr(e, "plague_t", config.PLAGUE[0]) - dt
                    if e.plague_t <= 1e-9:
                        e.plague_t += config.PLAGUE[0]
                        for src, names in spread.items():
                            self._pandemic(src, e, config.PLAGUE[1], names)
            if e.alive and st.has("burn") and st.has("chill") and "geyser" not in st.cooldowns:
                src = next((s.source for s in (st.active["burn"], st.active["chill"])
                            if has(s.source, "thermal_shock+9")), None)
                if src is not None:                                       # Geyser
                    statuses.combos.append(("thermal_shock", e, src))

    def flee(self, e, dt: float) -> bool:
        """Bloodtrail Cowl +3 (Panic): a scared enemy runs straight away from
        the hero instead of thinking. Bosses and things that can't walk
        don't run."""
        st = e.status
        if st is None or st.scared <= 0 or st.scared_from is None or getattr(e, "boss", False):
            return False
        espec = getattr(e, "espec", None)
        speed = getattr(espec, "speed", 0.0)
        if speed <= 0:
            return False
        src = st.scared_from
        a = math.atan2(e.y - src.y, e.x - src.x)
        step = speed * dt * st.time_scale
        push(e, self.scene.world, math.cos(a) * step, math.sin(a) * step)
        return True

    def enemy_shots(self, shots) -> None:
        """Blazecrown +6 (Heat haze): shots a burning enemy just fired fly
        slower."""
        disarmed, dizzy = set(), {}
        for q in shots:
            o = q.owner
            if getattr(o, "faction", None) != "enemy":
                continue
            if getattr(o, "disarmed", 0) > 0 or id(o) in disarmed:     # Fencer's Boots +3
                disarmed.add(id(o))
                q.alive = False
                self.scene.effects.append(Effect("fizzle", q.x, q.y))
                continue
            if getattr(o, "dizzy", 0) > 0 or id(o) in dizzy:           # Dancing Slippers +6
                turn = dizzy.setdefault(id(o), math.radians(config.DIZZY[0])
                                        * (1 if o.rng.random() < 0.5 else -1))
                q.angle = q.base_angle = q.angle + turn
                q.dir_x, q.dir_y = math.cos(q.angle), math.sin(q.angle)
            st = o.status
            if st is None:
                continue
            burn = st.active.get("burn")
            if burn is not None and has(burn.source, "wildfire+6"):
                q.pace *= config.HEAT_HAZE
        for e in self.scene.enemies:
            if id(e) in disarmed:
                e.disarmed = 0.0
            if id(e) in dizzy:
                e.dizzy = 0.0

    def _splash(self, victim, source, dealt: float) -> None:
        """Brimful Ring +6 (Splash): a crit splashes SPLASH[0] of what it
        dealt onto the enemies within SPLASH[1] tiles of its victim."""
        share, reach = config.SPLASH
        for a in list(self._enemies_near(victim.x, victim.y, reach, source)):
            if a is not victim:
                self._number(a, a.take_damage(dealt * share, source, None), "")

    def _number(self, a, dealt: float, tone: str) -> None:
        if dealt > 0:
            self.scene.effects.append(Effect("number", a.x, a.y - a.hit_radius,
                                             value=max(1, round(dealt)), tone=tone))

    # --- Status combos ------------------------------------------------------------------

    def resolve_combos(self) -> None:
        pending, statuses.combos[:] = list(statuses.combos), []
        for item in pending:
            kind, victim, source = item[:3]
            if kind == "splash":                                        # Brimful Ring +6
                self._splash(victim, source, item[3])
                continue
            st = victim.status
            if st is None or not victim.alive:
                continue
            if kind == "thermal_shock" and st.has("burn") and st.has("chill") \
                    and "geyser" not in st.cooldowns:
                per, radius = config.THERMAL_SHOCK
                burn = st.stacks("burn")
                damage = per * burn * source.stats.status_scale("fire")
                if has(source, "thermal_shock+6"):                     # Pressure
                    radius += config.PRESSURE * burn
                if has(source, "thermal_shock+9"):                     # Geyser
                    st.cooldowns["geyser"] = config.GEYSER
                else:
                    st.active.pop("chill", None)
                self.scene.effects.append(Effect("explosion", victim.x, victim.y))
                if radius > config.THERMAL_SHOCK[1]:
                    self.scene.effects.append(Effect("nova", victim.x, victim.y, size=radius))
                for a in list(self._enemies_near(victim.x, victim.y, radius, source)):
                    self._number(a, a.take_damage(damage, source, None), "burn")
                    if a.alive and has(source, "thermal_shock+3"):     # Scald
                        inflict(a, "burn", source, config.SCALD)
            elif kind == "toxic_current" and st.has("poison"):
                n, reach = config.TOXIC_CURRENT
                galvanize = has(source, "toxic_current+9")
                if galvanize:                                           # Galvanize
                    reach = config.GALVANIZE
                stacks = st.stacks("poison")
                others = sorted((a for a in self._enemies_near(victim.x, victim.y, reach, source)
                                 if a is not victim),
                                key=lambda a: math.hypot(a.x - victim.x, a.y - victim.y))
                if not galvanize:
                    others = others[:n]
                for a in others:
                    self.scene.effects.append(Effect("arc", victim.x, victim.y, x2=a.x, y2=a.y))
                    inflict(a, "poison", source, stacks)
                    if a.alive and has(source, "toxic_current+3"):     # Live wire
                        inflict(a, "shock", source, chain=False)
                if others and has(source, "toxic_current+6"):          # Battery
                    source.battery = min(config.BATTERY, source.battery + 1)
            elif kind == "rend":                                        # Thornhelm +3
                damage = config.REND[1] * source.stats.status_scale("physical")
                self._number(victim, victim.take_damage(damage, source, None), "bleed")
            elif kind == "tempest":                                     # Stormvane Helm +9
                _, _, damage, radius = config.TEMPEST
                self.scene.effects.append(Effect("arc", victim.x, victim.y - 8.0,
                                                 x2=victim.x, y2=victim.y))
                self.scene.effects.append(Effect("explosion", victim.x, victim.y))
                self.scene._sounds.append("zap")
                for a in list(self._enemies_near(victim.x, victim.y, radius, source)):
                    strike(a, damage, source, None, self.scene.effects, ("lightning",),
                           on_hit=False)
            elif kind == "shatterpoint":                                # Glassfrost Helm +9
                self.scene.effects.append(Effect("nova", victim.x, victim.y, size=1.0))
                self._shards(source, victim)


# --- Pacts and difficulty ----------------------------------------------------------------


def difficulty_totals(level: int) -> dict:
    """What difficulty `level` (P5, an index into config.DIFFICULTIES) does:
    x enemy max HP and x damage (compounding per level), and + fractions of
    enemies and loot (adding up per level)."""
    n = max(0, min(len(config.DIFFICULTIES) - 1, level))
    return {"name": config.DIFFICULTIES[n], "hp": config.DIFFICULTY_HP ** n,
            "damage": config.DIFFICULTY_DAMAGE ** n, "enemies": config.DIFFICULTY_ENEMIES * n,
            "loot": config.DIFFICULTY_LOOT * n}


def pact_totals(keys) -> dict:
    """What a set of pacts adds up to."""
    out = {"loot": 0.0, "enemy_damage": 0.0, "enemy_count": 0.0, "enemy_haste": 0.0,
           "enemy_levels": 0, "hero_hp": 0.0, "famine": False}
    for k in sorted(keys):
        pact = config.PACTS[k]
        for name in out:
            v = getattr(pact, name)
            out[name] = (out[name] or v) if name == "famine" else out[name] + v
    return out
