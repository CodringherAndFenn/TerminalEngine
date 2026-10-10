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
  resolve_combos  Thermal Shock and Toxic Current (systems/statuses.combos);
  pacts         what the dungeon gate's pacts do to the run.
"""

from __future__ import annotations

import math

from .. import config
from ..entities.effects import Effect
from . import statuses
from ..entities.projectile import Projectile
from .combat import _may_hurt, push, shot_origin, strike, volley
from .raycast import first_hit
from .statuses import inflict


class RunRules:
    def __init__(self, scene) -> None:
        self.scene = scene
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
            # turn, so it doesn't fly in the first one's line (M19).
            kw["angle_offset"] = math.radians(config.ECHO_ANGLE) * (1 if n % 2 else -1)
        if st is None:
            return kw
        flags = st.flags
        if st.quiver:
            every = max(2, config.QUIVER_EVERY - (round(st.quiver) - 1))
            if n % every == 0:
                kw["extra_pellets"] += 1
                kw["spread_add"] += 4.0
        if "grand_finale" in flags and n % config.GRAND_FINALE[0] == 0:
            kw["mult"] *= config.GRAND_FINALE[1]
            kw["reach_mult"] *= config.GRAND_FINALE[2]
        if "syncopation" in flags:
            reach, dmg = config.SYNCOPATION[n % 2]
            kw["mult"] *= dmg
            kw["reach_mult"] *= reach
        if st.capacitor and hero.idle >= config.CAPACITOR_IDLE:
            kw["mult"] *= 1 + st.capacitor
        if st.opening_act and hero.time < st.opening_act:
            kw["mult"] *= 2.0
        if hero.riposte > 0:                       # Riposte: just rolled
            kw["sure_crit"] = True
            hero.riposte = 0.0
        if "echo" in flags and not echo and n % config.ECHO_EVERY == 0:
            p.echo_timer = config.ECHO_DELAY
        hero.idle = 0.0
        return kw

    def patterns(self, p, kw: dict) -> list[str]:
        """The extra shots the pattern cards add to the attack just made
        (with its keywords `kw`: damage, Riposte's crit). They're shots of
        the hero's own weapon, or Sheet Music's notes for the bard, and go
        off around the aim (the bard's: toward the nearest enemy)."""
        hero, st = p.hero, p.hero.stats
        if st is None:
            return []
        flags = st.flags
        spec = hero.weapon.spec
        notes = "sheet_music" in flags and spec.shell is None
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
            return []
        scene = self.scene
        n = hero.attacks
        sounds: list[str] = []

        def shoot(angle, count=1, fan=0.0, mult=1.0):
            sounds.extend(volley(hero, scene.world, scene.projectiles, scene.effects, angle,
                                 count, fan, shell, tags, damage, mult=kw["mult"] * mult,
                                 extra_chain=kw["extra_chain"],
                                 sure_crit=kw.get("sure_crit", False),
                                 origin=origin))

        if notes:
            # Sheet Music: one note at each of the nearest enemies; spare
            # notes (and all of them with nobody near) spread all round.
            count = config.SHEET_MUSIC + round(st.pellets)
            for i in range(count):
                if i < len(targets):
                    t = targets[i]
                    shoot(math.atan2(t.y - hero.y, t.x - hero.x))
                else:
                    shoot(aim + math.tau * i / count)
        if "cross_fire" in flags and n % config.CROSS_FIRE_EVERY == 0:
            for k in (1, 2, 3):
                shoot(aim + k * math.pi / 2, pellets, spread)
        every, rays = config.STARBURST
        if "starburst" in flags and n % every == 0:
            for k in range(rays):
                shoot(aim + k * math.tau / rays)
        if "rear_guard" in flags:
            shoot(aim + math.pi, mult=config.REAR_GUARD)
        if "spiral" in flags:
            hero.spiral += 1
            shoot(aim + math.radians(config.SPIRAL_STEP) * hero.spiral)
        if "arrow_rain" in flags and not notes and n % config.ARROW_RAIN[0] == 0:
            sounds += self._arrow_rain(hero, kw)
        return list(dict.fromkeys(sounds))

    def _arrow_rain(self, hero, kw: dict) -> list[str]:
        """Arrow Rain (P4): ARROW_RAIN[1] arrows (+1 per extra projectile)
        lobbed up from the bow, each coming down at a random spot within
        ARROW_RAIN[2] tiles of the aim point (no farther than the bow
        reaches), a little apart in time."""
        every, count, radius, share = config.ARROW_RAIN
        shell = hero.weapon.spec.shell
        rain = config.SPELL_SHELLS["rain_arrow"]
        aim = getattr(hero, "aim_point", None) or (
            hero.x + math.cos(hero.aim_angle) * shell.max_range / 2,
            hero.y + math.sin(hero.aim_angle) * shell.max_range / 2)
        mx, my = shot_origin(hero)
        rng = hero.rng
        for _ in range(count + round(hero.stats.pellets)):
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
            self.scene.projectiles.append(arrow)
        return [rain.sound]

    def _note_targets(self, hero) -> list:
        """Enemies Sheet Music aims at: in sight within reach, nearest first."""
        reach = config.SHEET_MUSIC_REACH
        world = self.scene.world
        near = []
        for a in self.scene._actors():
            if not a.hittable or not _may_hurt(hero, a):
                continue
            d = math.hypot(a.x - hero.x, a.y - hero.y)
            if d <= reach and first_hit(world.tile_at, hero.x, hero.y, a.x, a.y) is None:
                near.append((d, a))
        near.sort(key=lambda da: da[0])
        return [a for _, a in near]

    def weapon_dt(self, p, dt: float) -> float:
        """Frenzy: the weapon's clock runs double for a while after a kill."""
        return dt * 2 if p.frenzy > 0 else dt

    # --- Every step ---------------------------------------------------------------------

    def tick(self, p, dt: float) -> None:
        hero, st = p.hero, p.hero.stats
        hero.time += dt
        hero.idle += dt
        hero.level = p.progress.level
        hero.run_loot = p.stats.loot
        hero.since_hit += dt
        if st is None:
            return
        if st.shield > 0 and hero.shield < st.shield \
                and hero.since_hit >= config.SHIELD_RECHARGE_DELAY:
            hero.shield = min(st.shield, hero.shield + st.shield * config.SHIELD_RECHARGE_RATE * dt)
        if hero.bloodlust:
            hero.bloodlust = [t for t in hero.bloodlust if t > hero.time]
        p.frenzy = max(0.0, p.frenzy - dt)
        p.retaliate_cd = max(0.0, p.retaliate_cd - dt)
        if hero.retaliate:
            hero.retaliate = False
            if st.has("retaliation") and p.retaliate_cd <= 0:
                self._retaliate(p)
        if p.echo_timer > 0:
            p.echo_timer -= dt
            if p.echo_timer <= 0:
                self.scene._attack(p, echo=True)

    def _retaliate(self, p) -> None:
        damage, radius, cooldown, shove = config.RETALIATION
        hero = p.hero
        p.retaliate_cd = cooldown
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
        if "bloodlust" in flags:
            hero.bloodlust.append(hero.time + config.BLOODLUST_TIME)
            del hero.bloodlust[:-config.BLOODLUST_MAX]
        if "frenzy" in flags:
            p.frenzy = config.FRENZY_TIME
        if st.soul_harvest:
            hero.heal(st.soul_harvest)
        if "bounty" in flags:
            p.bounty += 1
            if p.bounty % config.BOUNTY_EVERY == 0:
                scene._loot(p, enemy, times=config.BOUNTY_EVERY)
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
        boom = "volatile" in flags and (
            hero.rng.random() < config.VOLATILE_CHANCE
            or (getattr(enemy, "blasted", False) and "chain_reaction" in flags))
        if boom:
            self._explode(hero, enemy)

    def _explode(self, hero, enemy) -> None:
        """Volatile: the body bursts for part of the hit that killed it.
        With Chain Reaction, what that kills bursts too (each body once)."""
        damage = getattr(enemy, "last_damage", 0.0) * config.VOLATILE_DAMAGE
        self.scene.effects.append(Effect("explosion", enemy.x, enemy.y))
        self.scene._sounds.append("break")
        for a in list(self._enemies_near(enemy.x, enemy.y, config.VOLATILE_RADIUS, hero)):
            strike(a, damage, hero, None, self.scene.effects, ("area",), on_hit=False)
            if not a.alive:
                a.blasted = True

    def _pandemic(self, hero, enemy) -> None:
        n, reach = config.PANDEMIC
        others = sorted((a for a in self._enemies_near(enemy.x, enemy.y, reach, hero)
                         if a is not enemy),
                        key=lambda a: math.hypot(a.x - enemy.x, a.y - enemy.y))[:n]
        for name, s in sorted(enemy.status.active.items()):
            for a in others:
                inflict(a, name, hero, s.stacks)

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

    def on_level_up(self, p) -> None:
        hero, st = p.hero, p.hero.stats
        if p.progress.level >= 30:
            self.award(p, "level_30")
        if st is None or not st.has("surge"):
            return
        hero.heal(hero.max_hp * config.SURGE_HEAL)
        reach, shove = config.SURGE_PUSH
        self.scene.effects.append(Effect("pulse", hero.x, hero.y, size=reach))
        for a in list(self._enemies_near(hero.x, hero.y, reach, hero)):
            angle = math.atan2(a.y - hero.y, a.x - hero.x)
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
        if st is None:
            return False
        scene = self.scene
        if st.phoenix > p.phoenix_used:
            p.phoenix_used += 1
            frac, radius, damage = config.PHOENIX
            hero.hp = hero.max_hp * frac
            scene.effects.append(Effect("explosion", hero.x, hero.y))
            scene.effects.append(Effect("nova", hero.x, hero.y, size=radius))
            for a in list(self._enemies_near(hero.x, hero.y, radius, hero)):
                strike(a, damage, hero, None, scene.effects, ("fire",), on_hit=False)
                if a.alive:
                    inflict(a, "burn", hero, 3)
        elif st.revives > p.revives_used:
            p.revives_used += 1
            hero.hp = hero.max_hp * config.SECOND_CHANCE_HP
        else:
            return False
        scene.effects.append(Effect("toast", hero.x, hero.y, label="RISE AGAIN!"))
        if p.local:
            scene._sounds.append("chime")
        return True

    # --- Status combos ------------------------------------------------------------------

    def resolve_combos(self) -> None:
        pending, statuses.combos[:] = list(statuses.combos), []
        for kind, victim, source in pending:
            st = victim.status
            if st is None or not victim.alive:
                continue
            if kind == "thermal_shock" and st.has("burn") and st.has("chill"):
                per, radius = config.THERMAL_SHOCK
                damage = per * st.stacks("burn") * source.stats.status_scale("fire")
                st.active.pop("chill", None)
                self.scene.effects.append(Effect("explosion", victim.x, victim.y))
                for a in list(self._enemies_near(victim.x, victim.y, radius, source)):
                    dealt = a.take_damage(damage, source, None)
                    if dealt > 0:
                        self.scene.effects.append(Effect(
                            "number", a.x, a.y - a.hit_radius, value=max(1, round(dealt)),
                            tone="burn"))
            elif kind == "toxic_current" and st.has("poison"):
                n, reach = config.TOXIC_CURRENT
                stacks = st.stacks("poison")
                others = sorted((a for a in self._enemies_near(victim.x, victim.y, reach, source)
                                 if a is not victim),
                                key=lambda a: math.hypot(a.x - victim.x, a.y - victim.y))[:n]
                for a in others:
                    self.scene.effects.append(Effect("arc", victim.x, victim.y, x2=a.x, y2=a.y))
                    inflict(a, "poison", source, stacks)


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
