"""
systems/combat.py -- firing, shot flight, hits on actors and terrain, blasts.

Aiming math: a shot starts `hold_px` out from the shooter's centre along its
aim and flies along the true world aim angle. The start point is hold_px
out along the aim's *on-screen* direction; converting that pixel offset
back to tiles (dx / TILE_PX_W, dy / TILE_PX_H) lands exactly on the world
ray from the centre at the aim angle, because the screen angle was derived
from the world angle with the same per-axis scale. So the shot passes
through the exact world point under the reticle.

Every hit on an actor spawns a floating damage number (an Effect).

Hits: each frame a shot's movement is a segment. Terrain along it is found
by walking the tiles it crosses (systems/raycast.py); actors by
segment-vs-circle intersection. Whichever comes first along the segment is
hit. Friendly fire is on: any actor except the shooter can be hit --
except that heroes never hurt each other (co-op).

Hero weapons (M10) come in kinds (specs.WeaponSpec): shots (with pellets
fanned over a spread, arrows that pierce, lightning that chains from
enemy to enemy, axes that fly out and come back), melee swings over an
arc, and pulses all around.
attack() picks the right one.

Hero hits (M14) go through strike(): the damage buckets of
players/stats.py (bonus %, tag %, crits, "xN" multipliers), then the
on-hit statuses (status chance) and the hero cards that change what a hit
does (Supercell, Cleave, Spectrum, Point Blank, Broadhead, Hunter's Mark,
Dissonance, Overload). Enemies' hits are plain take_damage.
"""

from __future__ import annotations

import math
from dataclasses import replace

from .. import config
from ..entities.actor import Actor
from ..entities.effects import Effect
from ..entities.projectile import Projectile
from ..entities.character import Character, wrap_angle
from ..specs import CharacterSpec
from ..world.tiles import Damage
from .collision import move_hull, screen_angle
from .raycast import RayHit, first_hit
from .statuses import burning, combos, inflict, on_hero_hit, roll_on_hit, statuses_of

# Sound events returned to the scene (it owns the audio).
SHOT, HIT, BREAK, FIZZLE, THUD = "shot", "hit", "break", "fizzle", "thud"


def shot_origin(shooter: Character) -> tuple[float, float]:
    """World position a shot leaves from: hold_px out along the aim."""
    s = screen_angle(shooter.aim_angle)
    length = shooter.spec.hold_px
    return (
        shooter.x + math.cos(s) * length / config.TILE_PX_W,
        shooter.y + math.sin(s) * length / config.TILE_PX_H,
    )


def attack(
    shooter: Character, world, projectiles: list[Projectile], effects: list[Effect],
    actors: list[Actor] = (), mult: float = 1.0, extra_chain: int = 0, extra_pellets: int = 0,
    spread_add: float = 0.0, reach_mult: float = 1.0, sure_crit: bool = False,
    angle_offset: float = 0.0,
) -> list[str]:
    """Use the shooter's weapon, whatever its kind (see specs.WeaponSpec).
    The keywords are one attack's changes (cards that work every Nth
    attack, see systems/run_rules.attack_mods): x damage, + lightning
    jumps, + projectiles over + degrees of fan, x pulse reach, whether
    its hits always crit (Riposte), and a turn off the aim in radians
    (Echo). Returns sound events."""
    kind = shooter.weapon.spec.kind
    if kind == "melee":
        return swing(shooter, world, actors, effects, mult, sure_crit)
    if kind == "pulse":
        return pulse(shooter, world, actors, effects, mult, reach_mult, sure_crit)
    return fire(shooter, world, projectiles, effects,
                angle=shooter.aim_angle + angle_offset if angle_offset else None, mult=mult,
                extra_chain=extra_chain, extra_pellets=extra_pellets, spread_add=spread_add,
                sure_crit=sure_crit, actors=actors)


# --- Hero damage ---------------------------------------------------------------------


def strike(victim: Actor, base: float, source: Actor | None, angle: float | None,
           effects: list[Effect], tags=(), extra: float = 0.0, mult: float = 1.0,
           on_hit: bool = True, can_crit: bool = True, sure_crit: bool = False,
           crit_x: float = 1.0, pet: bool = False) -> float:
    """One hit of `base` damage on `victim`. From a hero (an actor with
    `stats`) it goes through the damage buckets and may crit and apply the
    hero's on-hit statuses; from anyone else it's plain damage. `extra`
    adds to bucket A (conditionals), `mult` is a per-hit "xN". Summons'
    hits pass on_hit / can_crit False (unless Pack Leader); `sure_crit`
    makes a hit that may crit always crit (Riposte); `crit_x` scales its
    crit chance (Tumbler Boots +6); `pet`: a summon's hit (a wolf's bite,
    a turret's bolt: Packmaster +3). Returns the damage dealt; whether it
    crit is left in source.last_crit."""
    if getattr(source, "shrunk", 0) > 0:              # tiny (Nettle's dust, M25.1)
        mult *= config.SHRINK[2]
    if victim.status is not None and victim.status.asleep > 0 \
            and not getattr(source, "lulling", False):
        victim.status.asleep = 0.0                    # (Cradlesong +3: a hit wakes it)
    stats = getattr(source, "stats", None)
    if stats is None:
        dealt = victim.take_damage(base * mult, source, angle)
        _number(effects, victim, dealt)
        return dealt
    a = stats.damage + extra + situational_bonus(stats, source, victim)
    if (pet or getattr(source, "spelling", False)) and stats.has("crescendo+L"):
        a += config.CRESCENDO_STEP * getattr(source, "streak", 0)   # (Fortissimo Lute (L): Tutti)
    if not pet and stats.has("spirit_wolf+3"):
        source.scent = victim                       # Wolfcall Whistle +3 (Scent)
    if stats.has("pack_leader+3"):                  # Packmaster +3 (Alpha)
        marks = victim.__dict__.setdefault("alpha", {})
        if not pet:
            marks[id(source)] = source.time
        elif source.time - marks.get(id(source), -1e9) <= config.ALPHA[0]:
            a += config.ALPHA[1]
    m = stats.damage_mult * mult
    if marked(source, victim):
        m *= config.MARK_MULT
    st = victim.status
    frozen = st is not None and st.frozen > 0
    if stats.has("shatter") and frozen:
        m *= config.SHATTER[0]
    elif st is not None and stats.has("shatter+3") and st.has("chill"):
        m *= config.BRITTLE                         # Glassfrost Helm +3 (Brittle)
    if stats.has("glass_cannon+9") and getattr(source, "since_hit", 0.0) >= config.DIAMOND[0]:
        m *= config.DIAMOND[1]                      # Shattercoat +9 (Diamond)
    chance = crit_chance(stats, source)
    lit = getattr(victim, "lit", None)
    if lit and lit.get(id(source), -1e9) > source.time:
        chance += config.GLOW[0]                    # Firefly Lantern +3 (Glow)
    crit = can_crit and (sure_crit or source.rng.random() < chance * crit_x)
    if can_crit and not crit and stats.has("fleet_strike+L") \
            and getattr(source, "speed", 0.0) >= config.STILL_SPEED:
        crit = source.rng.random() < chance * crit_x   # (Wingheel Sandals (L): Blur)
    source.last_crit = crit
    amount = base * (1 + a) * (1 + stats.tag_bonus(tags)) * m
    if crit:
        boost = stats.crit_damage + len(getattr(source, "deluge", ())) * config.DELUGE[0]
        if stats.has("steady_aim+6") and getattr(source, "still_t", 0.0) >= config.ZEN[0]:
            boost += config.ZEN[1]                  # Stillwater Bow +6 (Zen)
        amount *= boost
        if stats.has("overflow+3") and victim.hp >= victim.max_hp * config.BRIM_HP:
            amount *= boost                         # Brimful Ring +3 (Brim)
        if stats.has("overflow+9"):                 # Deluge
            per, seconds, most = config.DELUGE
            source.deluge = (source.deluge + [source.time + seconds])[-round(most / per):]
    before = victim.hp
    dealt = victim.take_damage(amount, source, angle)
    _number(effects, victim, dealt, "crit" if crit else "")
    if crit and dealt > before > 0 and not victim.alive and stats.has("overflow+L"):
        combos.append(("spill", victim, source, dealt - before))   # Brimful Ring (L)
    if dealt > 0 and stats.point_blank:
        _duel(victim, source, stats)
    if crit and dealt > 0 and stats.has("overflow+6"):
        combos.append(("splash", victim, source, dealt))   # Brimful Ring +6 (run_rules)
    if on_hit and dealt > 0 and victim.alive and stats.has("bloodlust+9") \
            and len(getattr(source, "bloodlust", ())) >= config.APEX[0]:
        inflict(victim, "bleed", source, config.APEX[1])   # Fang Ring +9 (Apex)
    if on_hit and dealt > 0:
        if frozen and stats.has("shatter+9") and victim.alive:
            # Glassfrost Helm +9 (Shatterpoint): the freeze ends in a
            # shatter -- the hit again, and its shards (run_rules).
            st.frozen = 0.0
            _number(effects, victim, victim.take_damage(amount, source, angle), "chill")
            combos.append(("shatterpoint", victim, source))
        on_hero_hit(victim, source, stats, crit)
        if stats.statuses:
            roll_on_hit(victim, source, stats)
    if dealt > 0:
        _feet_on_hit(victim, source, stats, crit)
        if not pet and victim.alive and stats.has("daggers+L") \
                and not getattr(source, "orbiting", False):
            source.satellite = (victim, source.time)    # (Bladewheel Charm (L): Satellite)
        if crit and stats.has("chain_lightning+L"):
            combos.append(("conduit", victim, source))  # (Chainbolt Charm (L): Conduit)
        if "volatile+L" in stats.flags or "bloodlust+L" in stats.flags:
            _ring_on_hit(victim, source, stats, dealt, on_hit)
    link = getattr(victim, "link", None)
    if link is not None and dealt > 0:             # Twinned Quiver +3: linked enemies
        other, until = link
        if until > getattr(source, "time", 0.0) and other.alive and other is not victim:
            shared = other.take_damage(dealt * config.LINKED[1], source, None)
            _number(effects, other, shared)
        else:
            victim.link = None
    return dealt


def _feet_on_hit(victim, source, stats, crit: bool) -> None:
    """The feet tricks a hero's hit sets off (M28.2c)."""
    if getattr(source, "riposting", False):
        if stats.has("riposte+3") and victim.alive:                 # Disarm
            if getattr(victim, "windup", 0) > 0 and not getattr(victim, "boss", False):
                victim.windup = 0.0                                 # (the wind-up stops)
                if hasattr(victim, "tell"):
                    victim.tell = 0.0
            else:
                victim.disarmed = config.DISARM
        if crit and not victim.alive and stats.has("riposte+9"):    # En garde
            source.roll_charges = min(stats.max_rolls, source.roll_charges + 1)
    if crit and stats.has("fleet_strike+3"):                        # Quickstep
        _, seconds, most = config.QUICKSTEP
        source.quick = (source.quick + [seconds])[-most:]


def _ring_on_hit(victim, source, stats, dealt: float, on_hit: bool) -> None:
    """The rings' legendary tricks a hero's hit sets off (M28.3h).
    Powderkeg Ring (L), Primed: every PRIMED-th of your hits on one enemy
    (attacks and spells: hits that roll statuses, not blasts) makes it
    explode, alive (run_rules). Fang Ring (L), Thirst: damage to an elite
    or a boss builds Bloodlust, a stack for every THIRST of its max HP."""
    if on_hit and victim.alive and stats.has("volatile+L") \
            and getattr(victim, "faction", None) == "enemy":
        count = victim.__dict__.setdefault("primed", {})
        count[id(source)] = count.get(id(source), 0) + 1
        if count[id(source)] % config.PRIMED == 0:
            combos.append(("primed", victim, source, dealt))
    if stats.has("bloodlust+L") and victim.max_hp > 0 and (
            getattr(victim, "boss", False) or getattr(getattr(victim, "espec", None), "elite", False)):
        per = victim.max_hp * config.THIRST
        got = victim.__dict__.setdefault("thirst", {})
        total = got.get(id(source), 0.0) + dealt
        n = int(total // per)
        got[id(source)] = total - n * per
        if n:
            add_bloodlust(source, stats, n)


def add_bloodlust(hero, stats, n: int = 1) -> None:
    """`n` Bloodlust stacks, each for BLOODLUST_TIME s, up to the cap (Fang
    Ring +9, Apex: a higher one)."""
    most = config.APEX[0] if stats.has("bloodlust+9") else config.BLOODLUST_MAX
    hero.bloodlust += [hero.time + config.BLOODLUST_TIME] * n
    del hero.bloodlust[:-most]


def move_bonus(hero) -> float:
    """A hero's move speed bonus right now: the stat plus what's on for a
    moment (Slipstream, Quickstep)."""
    st = getattr(hero, "stats", None)
    return (st.move if st is not None else 0.0) + getattr(hero, "speed_mult", 1.0) - 1.0


def drafting(actor) -> bool:
    """Windrunners +3 (Draft): slipstreaming, a hero slips through bodies --
    a boss's doesn't shove them, bumping enemies pass through them."""
    st = getattr(actor, "stats", None)
    return st is not None and getattr(actor, "slipstream", 0) > 0 and st.has("slipstream+3")


def skims(actor) -> bool:
    """Wingheel Sandals +9 (Air step): a hero fast enough skims over the
    ground -- ground attacks and hazards miss them."""
    st = getattr(actor, "stats", None)
    return st is not None and st.has("fleet_strike+9") and move_bonus(actor) >= config.AIR_STEP - 1e-9


def ground_cut(actor) -> float:
    """Spotless Tunic +6 (Dress code): x the damage a hero above
    UNTOUCHED_HP takes from the ground -- the hazards and attacks Air step
    skims (zones, stomps, eruptions...)."""
    st = getattr(actor, "stats", None)
    if st is None or not st.has("untouched+6") or not actor.max_hp \
            or actor.hp / actor.max_hp < config.UNTOUCHED_HP:
        return 1.0
    return config.DRESS_CODE


def bonus_armor(hero) -> float:
    """Armor a hero has on top of the stat right now: Anvil Plate +3
    (Tempered), Hoarder's Ring +6 (Golden armor) and Bastion Plate (L)
    (Ramparts: a point for every RAMPARTS max HP)."""
    armor = len(getattr(hero, "temper", ())) + getattr(hero, "hoard_armor", 0)
    st = getattr(hero, "stats", None)
    if st is not None and st.has("bulwark+L"):
        armor += hero.max_hp // config.RAMPARTS
    return armor


def _radiant_heat(victim: Actor) -> int:
    """Blazecrown (L), Radiant heat: an enemy within RADIANT_HEAT tiles of a
    burning one counts as burning, with the most burn stacks round it (for
    Bonfire); 0 if none (statuses.burning, refreshed each step)."""
    best = 0
    for x, y, stacks in burning:
        if math.hypot(x - victim.x, y - victim.y) <= config.RADIANT_HEAT + victim.hit_radius:
            best = max(best, stacks)
    return best


def situational_bonus(stats, source: Actor, victim: Actor) -> float:
    """Bucket A from the cards that depend on the moment (catalog 6.5,
    Point Blank, Wildfire, Golden Hoard, Juggernaut, the bestiary)."""
    a = 0.0
    if stats.point_blank:
        a += _point_blank(stats, source, victim)
    hp = source.hp / source.max_hp if source.max_hp else 0.0
    if stats.untouched and hp >= config.UNTOUCHED_HP:
        a += stats.untouched
    elif stats.untouched and hp >= config.IMMACULATE and stats.has("untouched+9"):
        a += stats.untouched / 2                    # (Spotless Tunic +9: Immaculate)
    flags = stats.flags
    if flags:
        if "berserker" in flags:
            a += max(0.0, 1 - hp, getattr(source, "scar", 0.0) if "berserker+L" in flags else 0.0)
        if "bulwark" in flags:
            body = source.max_hp + (getattr(source, "shield", 0.0) if "bulwark+9" in flags else 0.0)
            a += body / 10 * 0.01                  # (Bastion Plate +9, Citadel: the shield too)
            if "bulwark+6" in flags and getattr(source, "near_wall", False):
                a += config.GARRISON[1]            # Bastion Plate +6 (Garrison)
        if "momentum" in flags:
            a += momentum(stats, source)
        if "bloodlust" in flags:
            a += len(getattr(source, "bloodlust", ())) * 0.01
        if "giant_slayer" in flags and (victim.max_hp > source.max_hp or (
                "giant_slayer+L" in flags and getattr(source, "outnumbered", False))):
            slayer = config.GIANT_SLAYER
            if "giant_slayer+9" in flags and getattr(victim, "boss", False):
                slayer *= config.GOLIATH                # Slingstone Ring +9 (Goliath's bane)
            if "giant_slayer+3" in flags:               # Long odds
                per, each, most = config.LONG_ODDS
                slayer += min(most, max(0.0, victim.max_hp - source.max_hp) / per * each)
            a += slayer
        if "veteran" in flags:
            a += stats.veteran_levels(getattr(source, "level", 1)) * 0.01   # (+3: Hard-won)
            if "veteran+L" in flags:                    # Grizzled Signet (L): Battle-scarred
                a += getattr(source, "battle_scars", 0) * config.BATTLE_SCARRED[3]
        if "golden_hoard" in flags:
            per, cap = config.GOLDEN_HOARD
            hoard = getattr(source, "run_loot", 0.0) / per * 0.01
            if "golden_hoard+L" in flags:               # Hoarder's Ring (L): Old gold
                hoard += getattr(source, "purse", 0) / config.OLD_GOLD * 0.01
            a += hoard if "golden_hoard+9" in flags else min(cap, hoard)   # (+9: Dragon's hoard)
        if "juggernaut" in flags:
            armor = max(0.0, stats.armor + bonus_armor(source))
            a += armor * config.JUGGERNAUT * (2 if "juggernaut+9" in flags else 1)   # (Peak)
        if "spectrum+6" in flags and _colors_on(victim, source) >= config.COLOR_THEORY[0]:
            a += config.COLOR_THEORY[1]                 # Chroma Wand +6 (Color theory)
    burn = victim.status.stacks("burn") if victim.status is not None else 0
    if stats.wildfire and not burn and "wildfire+L" in flags:
        burn = _radiant_heat(victim)                 # Blazecrown (L): Radiant heat
    if stats.wildfire and burn:
        if "wildfire+9" in flags:                    # Blazecrown +9 (Bonfire): by the stack
            per, most = config.BONFIRE
            grow = stats.wildfire / config.WILDFIRE  # (the piece's +10% a level)
            a += min(most, per * burn) * grow
        else:
            a += stats.wildfire
    kind = getattr(victim, "kind_key", None)
    if kind is not None and kind in getattr(source, "bestiary", ()):
        a += config.BESTIARY_BONUS
    return a


def momentum(stats, source) -> float:
    """Momentum (Gallopers): half the move speed bonus -- +9 (Full gallop)
    all of it, and a mount counts as FULL_GALLOP. (L), Iron hooves: as
    much off the damage taken (Character.take_damage)."""
    if "momentum+9" in stats.flags:
        return max(0.0, stats.move) + (config.FULL_GALLOP if getattr(source, "mount", "") else 0.0)
    return max(0.0, stats.move) / 2


def point_blank_range(stats) -> float:
    """Point Blank's reach (Duelist's Wand +9, Bladework: farther)."""
    return config.BLADEWORK[0] if stats.has("point_blank+9") else config.POINT_BLANK_RANGE


def _point_blank(stats, source, victim) -> float:
    """Point Blank (a card): bucket A up close. The Duelist's Wand: +3 (Face
    to face) more yet within FACE_TO_FACE[0] tiles; +6 (Duel) on the
    duelist, wherever it is; +9 (Bladework) farther, and more."""
    a = 0.0
    d = math.hypot(victim.x - source.x, victim.y - source.y)
    if d <= point_blank_range(stats):
        a += stats.point_blank * (config.BLADEWORK[1] if stats.has("point_blank+9") else 1)
        if d <= config.FACE_TO_FACE[0] and stats.has("point_blank+3"):
            a += config.FACE_TO_FACE[1]
    if victim is getattr(source, "duelist", None) and stats.has("point_blank+6"):
        a += config.DUEL[0]
    return a


def _duel(victim, source, stats) -> None:
    """Duelist's Wand +6 (Duel): the first enemy hit up close, while there's
    no duelist, becomes it -- until one of them falls."""
    if not stats.has("point_blank+6") or not victim.alive:
        return
    duelist = getattr(source, "duelist", None)
    if duelist is not None and duelist.alive:
        return
    if math.hypot(victim.x - source.x, victim.y - source.y) <= point_blank_range(stats):
        source.duelist = victim


def _colors_on(victim, source) -> int:
    """How many of the princess's colors' statuses (Spectrum) of hers the
    enemy carries; frozen counts as chilled."""
    st = victim.status
    if st is None:
        return 0
    n = 0
    for name in config.SPECTRUM_STATUS:
        s = st.active.get(name) if name is not None else None
        if s is not None and s.source is source:
            n += 1
        elif name == "chill" and st.frozen > 0 and st.frozen_by is source:
            n += 1
    return n


def marked(source, victim) -> bool:
    """Whether `victim` bears `source`'s Hunter's Mark: the mark, or one of
    the Bloodhound Bow's others (Old scent, Pack hunt) still on."""
    if victim is getattr(source, "marked", None):
        return True
    marks = getattr(source, "marks", None)
    return bool(marks) and any(e is victim and until > source.time for e, until in marks)


def steady(source) -> bool:
    """Standing still for Steady Aim -- or, Stillwater Bow +9 (Still
    waters), not moving for longer than STILL_WATERS yet; (L) Current,
    moving in a straight line for STILL_CURRENT[0] s."""
    if source.speed < config.STEADY_SPEED:
        return True
    st = getattr(source, "stats", None)
    if st is not None and st.has("steady_aim+L") \
            and getattr(source, "straight_t", 0.0) >= config.STILL_CURRENT[0] - 1e-9:
        return True                                 # (Stillwater Bow (L): Current)
    return st is not None and st.has("steady_aim+9") \
        and source.time - getattr(source, "calm", -math.inf) <= config.STILL_WATERS


def crit_chance(stats, source: Actor) -> float:
    chance = stats.crit_chance
    if stats.steady_crit and steady(source):
        chance += stats.steady_crit
    if stats.has("fleet_strike"):
        chance += max(0.0, stats.move) / 4
    return chance


def outgoing(source: Actor | None, base: float, tags=()) -> float:
    """What a hero's hit is worth against terrain: the steady buckets only
    (no crits or conditionals)."""
    stats = getattr(source, "stats", None)
    if stats is None:
        return base
    return base * (1 + stats.damage) * (1 + stats.tag_bonus(tags)) * stats.damage_mult


def push(actor: Actor, world, dx: float, dy: float, full: bool = False,
         boss: bool = False) -> None:
    """Shove an actor (tiles), stopping at walls. Things that never move
    (towers, spitters) and bosses stay put -- but for `boss` (Ramhorn Boots
    (L), Mountain mover). A hero with Wingheel Sandals +6 (Featherweight)
    is moved half as far -- unless `full` (a boss's body putting them back
    outside it)."""
    if getattr(actor, "half", None) is None or (getattr(actor, "boss", False) and not boss):
        return
    st = getattr(actor, "stats", None)
    if not full and st is not None and st.has("fleet_strike+6"):
        dx, dy = dx * config.FEATHERWEIGHT, dy * config.FEATHERWEIGHT
    if actor.status is not None and actor.status.walls():
        return                                        # (Rime Hood +6: frozen fast)
    spec = getattr(actor, "spec", None)
    speed = spec.max_speed if isinstance(spec, CharacterSpec) else \
        getattr(getattr(actor, "espec", None), "speed", 0.0)
    if speed <= 0:
        return
    actor.x, actor.y, _, _ = move_hull(world, actor.x, actor.y, 0.0, actor.half, actor.half,
                                       dx, dy)


def fire(
    shooter: Character, world, projectiles: list[Projectile], effects: list[Effect],
    angle: float | None = None, damage: float | None = None,
    target: tuple[float, float] | None = None, mult: float = 1.0, extra_chain: int = 0,
    extra_pellets: int = 0, spread_add: float = 0.0, sure_crit: bool = False,
    actors=(),
) -> list[str]:
    """Fire the shooter's weapon along its aim (or `angle`, for aim error).
    A weapon with several pellets fans them evenly over its spread, the
    middle of the fan on the aim; pellets added for this attack only
    (`extra_pellets`) widen it by at least MIN_PELLET_GAP each. Returns
    sound events."""
    mx, my = shot_origin(shooter)
    angle = shooter.aim_angle if angle is None else angle
    spec = shooter.weapon.spec
    shell = spec.shell
    dmg = shell.damage if damage is None else damage
    if shell.lob:
        effects.append(Effect("muzzle", mx, my, angle))
        # Lobbed: arcs over walls and everything else to the target point
        # (or as far as its range allows toward it).
        tx, ty = target if target is not None else (
            mx + math.cos(angle) * shell.max_range, my + math.sin(angle) * shell.max_range)
        a = math.atan2(ty - my, tx - mx)
        p = Projectile(mx, my, a, shell, owner=shooter, damage=dmg)
        p.flight = min(shell.max_range, math.hypot(tx - mx, ty - my))
        p.target = (mx + math.cos(a) * p.flight, my + math.sin(a) * p.flight)
        projectiles.append(p)
        return [shell.sound]
    n = max(1, spec.pellets + extra_pellets)
    if extra_pellets > 0:
        spread_add = max(spread_add, config.MIN_PELLET_GAP * extra_pellets)
    spread = spec.spread_deg + spread_add
    beam = _beaming(shooter, shell)
    if beam:
        spread = 0.0                                  # (Spyglass Wand +9: one beam)
    else:
        spread *= _pinpoint(shooter, shell) * _autofocus(shooter, shell, angle, spread, actors)
    stats = getattr(shooter, "stats", None)
    violet = shell.look == "prism" and stats is not None and stats.has("spectrum+L")
    if violet:
        n += 1                                        # (Chroma Wand (L): Ultraviolet)
    before = len(projectiles)
    events = volley(shooter, world, projectiles, effects, angle, n, spread,
                    shell, spec.tags, dmg, mult=mult, extra_chain=extra_chain, sure_crit=sure_crit,
                    actors=actors, violet=violet)
    if beam:
        _beam(shooter, world, projectiles[before:], effects)
    return events


def _pinpoint(shooter, shell) -> float:
    """Spyglass Wand +6 (Pinpoint): x the princess's fan -- it narrows
    while she stands still, down to PINPOINT[1] after PINPOINT[0] s."""
    stats = getattr(shooter, "stats", None)
    if stats is None or shell.look != "prism" or not stats.has("focus+6"):
        return 1.0
    full, least = config.PINPOINT
    return 1 - (1 - least) * min(1.0, getattr(shooter, "still_t", 0.0) / full)


def _autofocus(shooter, shell, angle: float, spread: float, actors) -> float:
    """Spyglass Wand (L), Autofocus: x the princess's fan, by the enemies
    in front of her (within her colors' reach, AUTOFOCUS[1] degrees either
    side of the aim, or inside the fan): one -> a line (0); AUTOFOCUS[0] or
    more -> its full width, without Focus's narrowing; else as it is."""
    stats = getattr(shooter, "stats", None)
    if stats is None or shell.look != "prism" or not stats.has("focus+L"):
        return 1.0
    crowd, side = config.AUTOFOCUS
    half = max(math.radians(side), math.radians(spread / max(stats.spread_mult, 1e-6)) / 2)
    n = 0
    for a in actors:
        if not a.hittable or not _may_hurt(shooter, a):
            continue
        d = math.hypot(a.x - shooter.x, a.y - shooter.y)
        if d <= shell.max_range + a.hit_radius \
                and abs(wrap_angle(math.atan2(a.y - shooter.y, a.x - shooter.x) - angle)) <= half:
            n += 1
    if n == 1:
        return 0.0
    if n >= crowd:
        return 1 / max(stats.spread_mult, 1e-6)
    return 1.0


def _beaming(shooter, shell) -> bool:
    """Spyglass Wand +9 (Beam): still for BEAM[0] s, the fan is a beam."""
    stats = getattr(shooter, "stats", None)
    return stats is not None and shell.look == "prism" and stats.has("focus+9") \
        and getattr(shooter, "still_t", 0.0) >= config.BEAM[0] - 1e-9


def _beam(shooter, world, shots: list[Projectile], effects: list[Effect]) -> None:
    """The colors as one beam: all on the aim's line, through every enemy,
    across their reach in one frame (only walls stop it)."""
    if not shots:
        return
    for p in shots:
        p.angle = p.base_angle = shooter.aim_angle
        p.dir_x, p.dir_y = math.cos(p.angle), math.sin(p.angle)
        p.curve = p.curve_left = 0.0                  # (no Converge bend: it's straight)
        p.lock, p.focal, p.crossings = None, None, 0
        p.pierce_left = 10 ** 6
        p.pace = max(1.0, p.max_range / (p.spec.speed / 60.0))
        p.beam = True
    p = shots[0]
    ex, ey = p.x + p.dir_x * p.max_range, p.y + p.dir_y * p.max_range
    hit = first_hit(world.tile_at, p.x, p.y, ex, ey)
    if hit is not None:
        ex, ey = hit.x, hit.y
    effects.append(Effect("beam", p.x, p.y, p.angle, x2=ex, y2=ey))


def volley(shooter: Character, world, projectiles: list[Projectile], effects: list[Effect],
           angle: float, n: int, spread_deg: float, shell, tags=(), damage: float | None = None,
           mult: float = 1.0, extra_chain: int = 0, sure_crit: bool = False,
           hold: float = 0.0, origin: tuple[float, float] | None = None,
           actors=(), violet: bool = False) -> list[str]:
    """`n` shots of `shell` fanned evenly over `spread_deg` around `angle`,
    from the shooter's hand (or `origin`). The weapon's own fire and the
    pattern cards (systems/run_rules.patterns) both come through here.
    Twin Lanes (a card) turns each shot into two side by side; Converge
    (P4) bends the princess's fan to cross at the aim point. `hold`: the
    shots wait this long before flying. `actors`: who Lockstep may
    follow (Crossbeam Wand +9). `violet`: the last of the fan is violet
    (Chroma Wand (L), Ultraviolet)."""
    mx, my = origin if origin is not None else shot_origin(shooter)
    effects.append(Effect("muzzle", mx, my, angle))
    dmg = shell.damage if damage is None else damage
    # Standing against a wall: the shot lands on it instead of spawning on
    # the far side. (Shots from an `origin` start where that is: a turret
    # firing your attack, Packmaster Ring (L).)
    hit = first_hit(world.tile_at, shooter.x, shooter.y, mx, my) if origin is None else None
    if hit is not None:
        return [shell.sound, _terrain_impact(world, hit, outgoing(shooter, dmg, tags) * mult,
                                             shell.damages_terrain, angle, effects)]
    spread = math.radians(spread_deg)
    stats = getattr(shooter, "stats", None)
    size = stats.shot_size * config.SHOT_SIZE_PX / config.TILE_PX_W if stats is not None else 0.0
    lanes = (0.0,)
    lane_mult = 1.0
    linked = drift = False
    if stats is not None and stats.has("twin_lanes"):
        gap, lane_mult = config.TWIN_LANES
        if stats.has("twin_lanes+L"):
            lane_mult = config.PERFECT_PAIR        # (Twinned Quiver (L): Perfect pair)
        lanes = (-gap, 0.0, gap) if stats.has("twin_lanes+9") else (-gap / 2, gap / 2)   # Triplets
        linked, drift = stats.has("twin_lanes+3"), stats.has("twin_lanes+6")
    group: dict = {}                  # Prism: which colors of this shot hit whom
    if stats is not None and shell.seek_turn > 0 and stats.has("implosion+9") \
            and shooter.attacks and shooter.attacks % config.SINGULARITY[0] == 0:
        group["well"] = True          # (Gravewell Staff +9: this cast's first hit)
    seek_point = None
    if shell.seek_turn > 0:
        # Homing shots look round the aim point when they go off roughly
        # toward it; shots sent elsewhere (Rear Guard...) look round the
        # point as far out along their own way.
        aim = getattr(shooter, "aim_point", None)
        if aim is not None and abs(wrap_angle(angle - shooter.aim_angle)) <= math.radians(60):
            seek_point = aim
        else:
            reach = math.hypot(aim[0] - mx, aim[1] - my) if aim is not None else shell.max_range / 2
            seek_point = (mx + math.cos(angle) * reach, my + math.sin(angle) * reach)
    meet = _converge_distance(shooter, shell, angle, n, spread_deg, mx, my)
    prism = stats is not None and shell.look == "prism"
    lens = prism and stats.has("focus+3")
    if prism and stats.has("converge+L"):
        group["n"] = n                # (Crossbeam Wand (L), Burn-in: the shot's colors)
    if prism and stats.has("prism+3"):
        group["colors"] = min(config.FULL_SPECTRUM, n)   # (Prismatic Wand +3: Full spectrum)
    lock = None
    if meet is not None and stats.has("converge+9"):
        lock = _lockstep_target(shooter, shell, mx, my, actors)
        if lock is not None:                          # (Crossbeam Wand +9: Lockstep)
            angle = math.atan2(lock.y - my, lock.x - mx)
            meet = max(config.CONVERGE_MIN, math.hypot(lock.x - mx, lock.y - my))
    for i in range(n):
        a = angle + (spread * (i / (n - 1) - 0.5) if n > 1 else 0.0)
        pair: dict | None = {} if linked else None        # Linked: who each twin hit
        for side in lanes:
            # Lanes sit side by side, across the shot's own heading.
            ox, oy = -math.sin(a) * side, math.cos(a) * side
            p = Projectile(mx + ox, my + oy, a, shell, owner=shooter, damage=dmg)
            p.variant = i
            p.violet = violet and i == n - 1
            p.tags = tags
            p.mult = mult * lane_mult
            p.extra_chain = extra_chain
            p.sure_crit = sure_crit
            p.size = size
            p.group = group
            p.hold = hold
            p.seek_point = seek_point
            p.twin = pair
            if drift and side:                             # Drift: apart as they fly
                room = max(0.0, config.DRIFT_APART / 2 - abs(side))
                p.drift = math.copysign(room / max(1.0, shell.max_range), side)
                p.drift_left = room
            if lens and abs(i - (n - 1) / 2) < 0.6:
                p.middle = True                            # (Spyglass Wand +3: Lens)
            if meet is not None:
                _converge(p, wrap_angle(a - angle), meet)
                p.mid, p.origin = angle, (mx, my)
                p.focal = [(mx + math.cos(angle) * meet, my + math.sin(angle) * meet)]
                p.lock = lock
                p.crossings = 1 if stats.has("converge+6") else 0
            projectiles.append(p)
    return [shell.sound]


def _lockstep_target(shooter, shell, mx: float, my: float, actors):
    """Crossbeam Wand +9 (Lockstep): the enemy nearest the aim point among
    those within the colors' reach -- the crossing follows it."""
    aim = getattr(shooter, "aim_point", None)
    if aim is None:
        return None
    best, best_d = None, math.inf
    for a in actors:
        if not a.alive or not a.hittable or not _may_hurt(shooter, a) \
                or math.hypot(a.x - mx, a.y - my) > shell.max_range * 0.9:
            continue
        d = math.hypot(a.x - aim[0], a.y - aim[1])
        if d < best_d:
            best, best_d = a, d
    return best


def _burn_in(p: Projectile, zones) -> None:
    """Crossbeam Wand (L), Burn-in: where the colors cross (the first of
    them to get there), the spot glows BURN_IN[0] s, hitting everything
    within FOCAL_POINT[0] tiles every BURN_IN[1] s for BURN_IN[2] x the
    whole shot (all its colors). Once a shot, at its first crossing."""
    stats = _stats_of(p)
    if zones is None or p.summon or stats is None or not stats.has("converge+L") \
            or p.group is None or p.group.get("burned_in") or not p.focal:
        return
    from .zones import Zone
    p.group["burned_in"] = True
    life, every, share = config.BURN_IN
    colors = p.group.get("n", 1)
    x, y = p.focal[0]
    zones.append(Zone("burn_in", x, y, config.FOCAL_POINT[0], life, every,
                      p.damage * colors * share, p.owner, p.tags))


def _cross_again(p: Projectile) -> None:
    """Where a converged color has crossed: Lockstep stops following, and
    Crossbeam +6 (Second crossing) bends it back to cross the middle line
    again SECOND_CROSSING tiles on."""
    if p.lock is not None:
        ox, oy = p.origin
        p.focal = [(p.lock.x, p.lock.y)]          # (where it crossed)
        p.mid = math.atan2(p.lock.y - oy, p.lock.x - ox)
        p.lock = None
    if p.crossings <= 0:
        return
    p.crossings -= 1
    off = wrap_angle(p.angle - p.mid)
    dist = config.SECOND_CROSSING
    _converge(p, off, dist)
    fx, fy = p.focal[-1]
    p.focal.append((fx + math.cos(p.mid) * dist, fy + math.sin(p.mid) * dist))


def _follow(p: Projectile) -> None:
    """Lockstep: bend this step for the arc through where the enemy is now
    (an arc from the shot's heading meeting a point d tiles off, at an angle
    th to that heading, turns 2*sin(th)/d radians a tile, 2*th in all)."""
    t = p.lock
    if not t.alive:
        p.lock = None
        return
    d = math.hypot(t.x - p.x, t.y - p.y)
    th = wrap_angle(math.atan2(t.y - p.y, t.x - p.x) - p.angle)
    if d < 0.5 or abs(th) > math.pi / 2:
        p.curve = 0.0
        p.curve_left = 0.0
        _cross_again(p)
        return
    p.curve = 2.0 * math.sin(th) / d
    p.curve_left = 2.0 * abs(th)


def _converge_distance(shooter, shell, angle: float, n: int, spread_deg: float,
                       mx: float, my: float):
    """Converge (P4): how far off the princess's colors should cross -- at
    her aim point (at least CONVERGE_MIN, within reach) -- or None: not her
    fan, a ring (Pirouette), or not fired toward the aim (Cross Fire's side
    shots...)."""
    stats = getattr(shooter, "stats", None)
    aim = getattr(shooter, "aim_point", None)
    if (stats is None or not stats.has("converge") or shell.look != "prism" or n < 2
            or spread_deg >= 180.0 or aim is None
            or abs(wrap_angle(angle - shooter.aim_angle)) > math.radians(30)):
        return None
    d = math.hypot(aim[0] - mx, aim[1] - my)
    return max(config.CONVERGE_MIN, min(d, shell.max_range * 0.9))


def _converge(p: Projectile, off: float, dist: float) -> None:
    """Bend a shot `off` radians off the middle of its fan along the arc
    of the circle that meets the middle line `dist` tiles out: such an arc
    turns 2*off in all, at 2*sin(off)/dist radians per tile flown. Then it
    flies on straight, spreading out again past the crossing."""
    if abs(off) < 1e-6:
        return
    p.curve = -2.0 * math.sin(off) / dist
    p.curve_left = 2.0 * abs(off)


def _may_hurt(source: Actor | None, target: Actor) -> bool:
    """Friendly fire is on -- except between players: heroes never hurt
    each other (co-op). Nothing hurts its own source."""
    if target is source:
        return False
    if source is not None and getattr(target, "part_of", None) is source:
        return False                                  # a swarm's own shots pass its bodies
    return not (source is not None and source.faction == "player" and target.faction == "player")


def _aim_offset(shooter: Character, x: float, y: float) -> float:
    """Angle between the shooter's aim and the direction to (x, y), measured
    on screen (so a swing's arc looks as wide as it is)."""
    to = screen_angle(math.atan2(y - shooter.y, x - shooter.x))
    diff = to - screen_angle(shooter.aim_angle)
    return abs((diff + math.pi) % math.tau - math.pi)


def swing(shooter: Character, world, actors: list[Actor], effects: list[Effect],
          mult: float = 1.0, sure_crit: bool = False) -> list[str]:
    """A melee sweep: everything whose body is within `reach` tiles and
    inside the arc in front of the aim is hit, and destructible terrain
    close in front is chopped."""
    spec = shooter.weapon.spec
    half = math.radians(spec.arc_deg) / 2
    effects.append(Effect("swing", shooter.x, shooter.y, shooter.aim_angle, size=spec.reach,
                          value=round(spec.arc_deg)))
    events = ["swing"]
    for a in actors:
        if not a.hittable or not _may_hurt(shooter, a):
            continue
        d = math.hypot(a.x - shooter.x, a.y - shooter.y)
        if d > spec.reach + a.hit_radius:
            continue
        if d > a.hit_radius and _aim_offset(shooter, a.x, a.y) > half:
            continue
        strike(a, spec.damage, shooter, shooter.aim_angle, effects, spec.tags, mult=mult,
               sure_crit=sure_crit)
        effects.append(Effect("impact", a.x, a.y, shooter.aim_angle))
        events.append(HIT)
    # Chop what's right in front (trees, walls): tiles whose centre is in
    # the inner part of the arc.
    r = spec.reach * config.MELEE_TERRAIN_REACH
    for ty in range(math.floor(shooter.y - r), math.floor(shooter.y + r) + 1):
        for tx in range(math.floor(shooter.x - r), math.floor(shooter.x + r) + 1):
            cx, cy = tx + 0.5, ty + 0.5
            if math.hypot(cx - shooter.x, cy - shooter.y) > r or _aim_offset(shooter, cx, cy) > half:
                continue
            result = world.damage_tile(tx, ty, outgoing(shooter, spec.damage, spec.tags) * mult)
            if result is Damage.DESTROYED:
                effects.append(Effect("debris", cx, cy))
                events.append(BREAK)
            elif result is Damage.DAMAGED:
                effects.append(Effect("tile_flash", tx, ty))
    return events


def pulse(shooter: Character, world, actors: list[Actor], effects: list[Effect],
          mult: float = 1.0, reach_mult: float = 1.0, sure_crit: bool = False,
          origin: tuple[float, float] | None = None) -> list[str]:
    """A burst all around: everything within `reach` tiles that isn't
    behind a wall is hit, and destructible terrain in reach is worn down at
    PULSE_TERRAIN_FACTOR of the damage. Cards: Dissonance (each one hit is
    pushed back and chilled), Crescendo (beats in a row that hit grow
    stronger), Lullaby (heal per enemy hit). `origin`: it goes off there
    instead (Stompers +9: an amp), without Crescendo's or Lullaby's count."""
    spec = shooter.weapon.spec
    reach = spec.reach * reach_mult
    ox, oy = origin if origin is not None else (shooter.x, shooter.y)
    effects.append(Effect("pulse", ox, oy, size=reach))
    events = ["pulse"]
    stats = getattr(shooter, "stats", None)
    has = stats.has if stats is not None else (lambda flag: False)
    dissonance = has("dissonance")
    crescendo = has("crescendo")
    streak = getattr(shooter, "streak", 0)
    extra = config.CRESCENDO_STEP * streak if crescendo else 0.0
    if crescendo and has("crescendo+6") and streak >= config.CRESCENDO_MAX:
        reach *= config.CLIMAX                        # (Fortissimo Lute +6: Climax)
    if origin is None and has("lullaby+6"):
        extra += config.NOTHING_WASTED * shooter.unspent   # (Cradlesong +6: Nothing wasted)
        shooter.unspent = 0.0
    shooter.lulling = has("lullaby+3")                # (Cradlesong +3: beats don't wake)
    finale = origin is None and getattr(shooter, "finale_now", False)
    if origin is None:
        shooter.finale_now = False
    banking = origin is None and has("grand_finale+L")  # (Showstopper Lute (L): Big finish)
    # Sourstring Lute (L), Undertow: every UNDERTOW-th beat pulls instead.
    pull = dissonance and has("dissonance+L") and shooter.attacks % config.UNDERTOW == 0
    dealt_all = 0.0
    struck = []
    hits = 0
    for a in actors:
        if not a.hittable or not _may_hurt(shooter, a):
            continue
        if math.hypot(a.x - ox, a.y - oy) > reach + a.hit_radius:
            continue
        if first_hit(world.tile_at, ox, oy, a.x, a.y) is not None:
            continue
        angle = math.atan2(a.y - oy, a.x - ox)
        chilled = a.status is not None and (a.status.has("chill") or a.status.frozen > 0)
        dealt_all += strike(a, spec.damage, shooter, angle, effects, spec.tags, extra=extra,
                            mult=mult * earworm(a, shooter), sure_crit=sure_crit)
        struck.append(a)
        hits += 1
        if dissonance and a.alive:
            _dissonance(a, shooter, world, angle, chilled, effects, has, pull, (ox, oy))
        if origin is None and has("lullaby+3"):
            _lull(a, shooter)
        events.append(HIT)
    shooter.lulling = False
    if banking:
        _big_finish(shooter, struck, finale, dealt_all, effects)
    if origin is None and stats is not None:
        heard = hits
        if has("lullaby+L"):                          # (Cradlesong Lute (L): Serenade)
            far = reach * config.SERENADE
            heard = len(struck) + sum(
                1 for a in actors if a not in struck and a.hittable and _may_hurt(shooter, a)
                and math.hypot(a.x - ox, a.y - oy) <= far + a.hit_radius)
        _beat_done(shooter, stats, hits, heard)
    wear = outgoing(shooter, spec.damage, spec.tags) * mult * config.PULSE_TERRAIN_FACTOR
    if wear > 0:
        r = reach
        for ty in range(math.floor(oy - r), math.floor(oy + r) + 1):
            for tx in range(math.floor(ox - r), math.floor(ox + r) + 1):
                cx, cy = tx + 0.5, ty + 0.5
                if math.hypot(cx - ox, cy - oy) > r:
                    continue
                if not world.tile_at(tx, ty).destructible:
                    continue
                block = first_hit(world.tile_at, ox, oy, cx, cy)
                if block is not None and (block.tx, block.ty) != (tx, ty):
                    continue                   # hidden behind another tile
                result = world.damage_tile(tx, ty, wear)
                if result is Damage.DESTROYED:
                    effects.append(Effect("debris", cx, cy))
                    events.append(BREAK)
                elif result is Damage.DAMAGED:
                    effects.append(Effect("tile_flash", tx, ty))
    return events


def _big_finish(shooter, struck: list, finale: bool, dealt: float,
                effects: list[Effect]) -> None:
    """Showstopper Lute (L), Big finish: a beat banks BIG_FINISH of what it
    dealt (shooter.bank); a finale that hits something lets the bank go,
    shared out over the enemies it hit that still stand."""
    if not finale:
        shooter.bank = getattr(shooter, "bank", 0.0) + dealt * config.BIG_FINISH
        return
    bank = getattr(shooter, "bank", 0.0)
    standing = [a for a in struck if a.alive]
    if bank <= 0 or not standing:
        return
    shooter.bank = 0.0
    for a in standing:
        _number(effects, a, a.take_damage(bank / len(standing), shooter, None), "crit")


def _dissonance(a, shooter, world, angle: float, chilled: bool, effects: list[Effect],
                has, pull: bool = False, at=None) -> None:
    """Dissonance (a card): a beat pushes the enemy back and chills it. The
    Sourstring Lute: +3 (Clash) pushed into a wall, it takes CLASH; +6
    (Tritone) chilled already, it's pushed TRITONE x as far; +9 (Shriek)
    two stacks. `pull` ((L) Undertow): toward the beat's middle `at`
    instead, never past the bard's body."""
    inflict(a, "chill", shooter, config.SHRIEK if has("dissonance+9") else 1)
    push_by = config.DISSONANCE_PUSH * (config.TRITONE if chilled and has("dissonance+6") else 1)
    x, y = a.x, a.y
    if pull and at is not None:
        room = math.hypot(a.x - at[0], a.y - at[1]) - a.hit_radius - shooter.hit_radius
        push_by = min(push_by, max(0.0, room))
        if push_by <= 0:
            return
        angle += math.pi
    push(a, world, math.cos(angle) * push_by, math.sin(angle) * push_by)
    moved = math.hypot(a.x - x, a.y - y)
    if has("dissonance+3") and moved < push_by * 0.9 and _pushable(a) and a.alive:
        strike(a, config.CLASH, shooter, angle, effects, ("physical",), on_hit=False)


def _earworm(victim, owner) -> None:
    """Songbird Lute (L), Earworm: a note's hit adds EARWORM[0] to what the
    enemy takes from this bard's beats, for EARWORM[1] s (each note starts
    it over), EARWORM[2] notes' worth at most."""
    per, seconds, most = config.EARWORM
    worms = victim.__dict__.setdefault("earworm", {})
    n, until = worms.get(id(owner), (0, -math.inf))
    n = min(most, (n if owner.time < until else 0) + 1)
    worms[id(owner)] = (n, owner.time + seconds)


def earworm(victim, owner) -> float:
    """x a beat's damage on `victim`: Earworm's notes on it (1.0 without)."""
    worms = getattr(victim, "earworm", None)
    if not worms or id(owner) not in worms:
        return 1.0
    n, until = worms[id(owner)]
    return 1 + config.EARWORM[0] * n if owner.time < until else 1.0


def _pushable(a) -> bool:
    """Whether combat.push moves this actor at all (not a boss, a thing
    that never moves, or one frozen fast)."""
    if getattr(a, "half", None) is None or getattr(a, "boss", False):
        return False
    if a.status is not None and a.status.walls():
        return False
    spec = getattr(a, "spec", None)
    speed = spec.max_speed if isinstance(spec, CharacterSpec) else \
        getattr(getattr(a, "espec", None), "speed", 0.0)
    return speed > 0


def _lull(a, shooter) -> None:
    """Cradlesong Lute +3 (Lullabied): an enemy hit by LULLABIED[0] beats in
    a row falls asleep (not a boss), until something other than a beat
    hits it, LULLABIED[1] s at most. Asleep, its beats don't count."""
    if not a.alive or getattr(a, "boss", False):
        return
    st = statuses_of(a)
    if st.asleep > 0:
        return
    beats, most = config.LULLABIED
    lull = a.__dict__.setdefault("lull", {})
    n, count = lull.get(id(shooter), (-2, 0))
    count = count + 1 if n == shooter.attacks - 1 else 1
    if count >= beats:
        st.asleep = most
        count = 0
    lull[id(shooter)] = (shooter.attacks, count)


def _beat_done(shooter, stats, hits: int, heard: int | None = None) -> None:
    """After a beat of the hero's own (not an amp's): Crescendo's count
    (Fortissimo Lute +3 Fermata: a miss drops one; +9 Forte: a higher
    cap), Lullaby's heal (Cradlesong +9 Mother's song: more; +6 Nothing
    wasted: what it can't heal is kept for the next beat) and when a beat
    last hit (Showstopper +3, Overture). `heard`: the enemies the heal
    counts, if not those hit (Cradlesong (L), Serenade)."""
    heard = hits if heard is None else heard
    if hits:
        shooter.beat_hit = shooter.time
    if stats.has("crescendo"):
        cap = config.FORTE if stats.has("crescendo+9") else config.CRESCENDO_MAX
        if hits:
            shooter.streak = min(cap, shooter.streak + 1)
        else:
            shooter.streak = max(0, shooter.streak - 1) if stats.has("crescendo+3") else 0
    if heard and stats.has("lullaby"):
        per, most = config.MOTHERS_SONG if stats.has("lullaby+9") else config.LULLABY_HEAL
        amount = min(most, per * heard)
        healed = shooter.heal(amount)
        if stats.has("lullaby+6"):
            shooter.unspent = max(0.0, amount - healed)


def chain_from(first: Actor, shell, damage: float, source: Actor | None, world,
               actors: list[Actor], effects: list[Effect], tags=(), extra_jumps: int = 0,
               mult: float = 1.0, charm: bool = False, zones: list | None = None,
               path: list | None = None) -> list[str]:
    """Lightning jumping on from `first` (already hit) to up to shell.chain
    (+ extra_jumps) more enemies: each jump goes to the nearest one within
    chain_range with a clear line, not hit yet, for chain_falloff of the
    previous damage. Supercell (a card): shocked enemies in range are
    picked first, and take SUPERCELL_BONUS more. `charm`: a Chainbolt Charm
    bolt -- +9 (Eternal arc) it may jump back to an enemy it hit, once
    each (new ones first); +3 (Grounding) when nobody's left to jump to, it
    strikes the ground by the last one: GROUNDING[1] of its damage round it.
    The main hand's tricks (M28.2g): Stormcaller +6 (jumps through walls)
    and +9 (Thunderlord: a long chain strikes all it hit again), the
    Copperwire Staff's fading (+3, +9) and far jumps (+6), Superstorm,
    Crackling chain (a crackle where each jump lands, into `zones`).
    `path`: where the bolt went, for a Thunderball (Crackle Staff +9).
    The legendary tricks (M28.3j): Forked lightning (the first jump forks),
    Long line (with nobody in reach, the nearest on screen) and Ionized
    (bolt_shock)."""
    stats = getattr(source, "stats", None)
    has = stats.has if stats is not None else (lambda flag: False)
    supercell = has("supercell")
    arc = charm and has("chain_lightning+9")
    walls = not has("storm_caller+6")                        # (Through walls)
    fade = 1.0 if has("conductor+9") else shell.chain_falloff   # (Superconductor)
    box = getattr(source, "view_box", None) if has("conductor+L") else None
    events = []
    hit = {id(first): 1}
    order, links = [first], []
    start = damage
    jumps = 0
    _bolted(first, source)

    def pick(current, far: bool):
        """The enemy a jump from `current` goes to (and its key), or None.
        `far`: Copperwire Staff (L), Long line -- anywhere on screen."""
        best, best_key = None, None
        for a in actors:
            times = hit.get(id(a), 0)
            if times >= (2 if arc else 1) or a is current or not a.hittable \
                    or not _may_hurt(source, a):
                continue
            d = math.hypot(a.x - current.x, a.y - current.y)
            if far:
                if box is not None and (abs(a.x - box[0]) > box[2] or abs(a.y - box[1]) > box[3]):
                    continue
            elif d > shell.chain_range:
                continue
            key = (times, not (supercell and _shocked(a)), d)
            if (best_key is None or key < best_key) and \
                    (not walls or first_hit(world.tile_at, current.x, current.y, a.x, a.y) is None):
                best, best_key = a, key
        return best, best_key

    # Each head is a bolt going on: [where it is, its damage]. Stormcaller
    # Rod (L), Forked lightning: the first jump forks to FORKED_LIGHTNING
    # enemies, and each goes on with the rest of the jumps.
    heads = [[first, damage]]
    for n in range(shell.chain + extra_jumps):
        if not heads:
            break
        fork = n == 0 and has("storm_caller+L")
        going = []
        for k, (current, before) in enumerate(heads):
            damage = before
            if not (n == 0 and has("conductor+3")):             # (Resistor: the 1st doesn't)
                damage *= fade
            for _ in range(config.FORKED_LIGHTNING if fork else 1):
                best, best_key = pick(current, False)
                long_jump = best is None and has("conductor+L")
                if long_jump:
                    best, best_key = pick(current, True)        # (Long line)
                if best is None:
                    if charm and has("chain_lightning+3") and not (fork and going):
                        _grounding(current, before, source, actors, effects, tags, mult)
                    break
                effects.append(Effect("arc", current.x, current.y, x2=best.x, y2=best.y))
                links.append((current, best))
                angle = math.atan2(best.y - current.y, best.x - current.x)
                extra = config.SUPERCELL_BONUS if supercell and _shocked(best) else 0.0
                far, more = config.OVERCURRENT
                if has("conductor+6") and not long_jump and best_key[2] >= shell.chain_range * far:
                    extra += more                                # (Overcurrent)
                strike(best, damage, source, angle, effects, tags, extra=extra, mult=mult)
                _bolted(best, source)
                if supercell and best.alive:
                    bolt_shock(best, source)
                if has("supercell+9"):
                    _superstorm(best, source, actors)
                if zones is not None and has("ball_lightning+6"):
                    _crackle(zones, best, damage, source, tags)  # (Crackling chain)
                if path is not None and k == 0 and not going:
                    path.append((best.x, best.y))
                if id(best) not in hit:
                    order.append(best)
                hit[id(best)] = hit.get(id(best), 0) + 1
                going.append([best, damage])
                jumps += 1
                events.append("zap")
        heads = going
    _, most, share = config.THUNDERLORD
    if jumps >= most and has("storm_caller+9"):                  # Thunderlord
        for a, b in links:
            effects.append(Effect("arc", a.x, a.y, x2=b.x, y2=b.y))
        for a in order:
            if a.alive and a.hittable:
                strike(a, start * share, source, None, effects, tags, mult=mult, on_hit=False)
        events.append("zap")
    return events


def bolt_shock(victim: Actor, source) -> None:
    """A bolt's shock (Supercell). Thunderhead Rod (L), Ionized: it never
    wears off."""
    inflict(victim, "shock", source)
    stats = getattr(source, "stats", None)
    st = victim.status
    if stats is not None and stats.has("supercell+L") and st is not None and "shock" in st.active:
        st.active["shock"].lasting = True


def _bolted(victim: Actor, source) -> None:
    """Stormcaller Rod +3 (Conducting darts): when `source`'s bolt hit it."""
    stats = getattr(source, "stats", None)
    if stats is not None and stats.has("storm_caller+3"):
        victim.__dict__.setdefault("bolted", {})[id(source)] = source.time


def _superstorm(at: Actor, source, actors) -> None:
    """Thunderhead Rod +9 (Superstorm): everything round a bolt's hit is shocked."""
    radius = config.SUPERSTORM
    for a in actors:
        if a is not at and a.alive and a.hittable and _may_hurt(source, a) \
                and math.hypot(a.x - at.x, a.y - at.y) <= radius + a.hit_radius:
            bolt_shock(a, source)


def _crackle(zones: list, at: Actor, damage: float, source, tags, x=None, y=None,
             dart: bool = False) -> None:
    """Ball Lightning's crackle where a bolt hit `at` (at x, y if given);
    Crackle Staff +3 (Sticky): it moves with `at`. `dart`: Crackle Staff
    (L), Static darts -- a dart's, smaller and shorter (never sticky)."""
    from .zones import Zone
    sticky = source.stats.has("ball_lightning+3") and not dart
    radius, life = config.BALL_LIGHTNING_RADIUS, config.BALL_LIGHTNING_TIME
    if dart:
        radius, life = radius * config.STATIC_DARTS[0], config.STATIC_DARTS[1]
    zones.append(Zone("crackle", at.x if x is None else x, at.y if y is None else y,
                      radius, life, config.BALL_LIGHTNING_EVERY,
                      damage * config.BALL_LIGHTNING_DAMAGE, source,
                      tags, follow=at if sticky and at.alive else None))


def _grounding(at: Actor, damage: float, source, actors, effects: list[Effect], tags,
               mult: float) -> None:
    """Grounding (Chainbolt Charm +3): the bolt strikes the ground by `at`."""
    radius, share = config.GROUNDING
    radius *= source.stats.area_scale
    effects.append(Effect("pulse", at.x, at.y, size=radius))
    for a in list(actors):
        if a.hittable and _may_hurt(source, a) \
                and math.hypot(a.x - at.x, a.y - at.y) <= radius + a.hit_radius:
            strike(a, damage * share, source, math.atan2(a.y - at.y, a.x - at.x), effects, tags,
                   mult=mult)


def _shocked(a: Actor) -> bool:
    return a.status is not None and a.status.has("shock")


def _number(effects: list[Effect], victim: Actor, dealt: float, tone: str = "") -> None:
    """A floating damage number over whoever got hurt."""
    if dealt > 0:
        effects.append(Effect("number", victim.x, victim.y - victim.hit_radius, 0.0,
                              value=max(1, round(dealt)), player=victim.faction == "player",
                              tone=tone))


def segment_circle_t(x0, y0, dx, dy, cx, cy, r) -> float | None:
    """Smallest t in [0, 1] where the segment (x0,y0)+t*(dx,dy) enters the
    circle (cx, cy, r), or None. Solves |p0 + t*d - c|^2 = r^2 for t."""
    fx, fy = x0 - cx, y0 - cy
    a = dx * dx + dy * dy
    c = fx * fx + fy * fy - r * r
    if c <= 0:
        return 0.0  # starts inside
    if a == 0:
        return None
    b = 2 * (fx * dx + fy * dy)
    disc = b * b - 4 * a * c
    if disc < 0:
        return None
    t = (-b - math.sqrt(disc)) / (2 * a)
    return t if 0.0 <= t <= 1.0 else None


class ActorGrid:
    """Hittable actors bucketed on a coarse grid, so each shot only tests
    the actors near its path instead of all of them (hundreds of enemies x
    hundreds of shots would otherwise be tens of thousands of tests a frame).

    An actor is filed under every bucket its hit circle overlaps; near()
    returns (index in the original list, actor) for the buckets a segment's
    bounding box touches, each actor once, in list order.
    """

    CELL = 4.0   # tiles; well above any hit radius or per-frame shot step

    def __init__(self, actors) -> None:
        self._buckets: dict[tuple[int, int], list[tuple[int, Actor]]] = {}
        cell = self.CELL
        for i, a in enumerate(actors):
            if not a.hittable:
                continue
            r = a.hit_radius
            for by in range(math.floor((a.y - r) / cell), math.floor((a.y + r) / cell) + 1):
                for bx in range(math.floor((a.x - r) / cell), math.floor((a.x + r) / cell) + 1):
                    self._buckets.setdefault((bx, by), []).append((i, a))

    def near(self, x0: float, y0: float, x1: float, y1: float) -> list[tuple[int, Actor]]:
        cell, buckets = self.CELL, self._buckets
        bx0, bx1 = math.floor(min(x0, x1) / cell), math.floor(max(x0, x1) / cell)
        by0, by1 = math.floor(min(y0, y1) / cell), math.floor(max(y0, y1) / cell)
        if bx0 == bx1 and by0 == by1:
            return buckets.get((bx0, by0), ())
        found: dict[int, Actor] = {}
        for by in range(by0, by1 + 1):
            for bx in range(bx0, bx1 + 1):
                for i, a in buckets.get((bx, by), ()):
                    found[i] = a
        return sorted(found.items())


def update_projectiles(
    projectiles: list[Projectile], world, effects: list[Effect], dt: float,
    actors: list[Actor] = (), zones: list | None = None,
) -> list[str]:
    """Move every shell and resolve hits and range. Returns sound events.
    Shots may split or spawn more (Refraction, Spray and Pray, Cyclone);
    Ball Lightning leaves its crackle in `zones` (systems/zones.py)."""
    events: list[str] = []
    grid = ActorGrid(actors)
    spawned: list[Projectile] = []
    for p in projectiles:
        if p.spec.lob:
            if p.hold > 0:                # (Cloudburst Bow +9: the second rain waits)
                p.hold -= dt
                continue
            events += _fly_lobbed(p, world, effects, dt, actors)
            continue
        if p.spec.returns:
            _tether(p, actors, effects, dt, world)
        if p.hang > 0:
            events += _hover(p, grid, world, effects, dt, actors, spawned, zones)
            continue
        if p.flail > 0:                   # (Chainlink Axe +9: round you on its chain)
            events += _swing_round(p, grid, world, effects, dt, actors, spawned, zones)
            continue
        if p.returning:
            events += _fly_back(p, grid, world, effects, dt, actors, spawned, zones)
            continue
        if p.hold > 0:                    # waiting to fly (harmless until then)
            p.hold -= dt
            continue
        if p.parked is not None:          # (Orrery Staff (L): kept in orbit, harmless)
            _clockwork(p, actors, dt)
            continue
        if p.spec.wobble:
            _weave(p)
        if p.seek_turn > 0:
            _home(p, actors, dt)
        if p.recurve and _recurve(p, dt):
            continue
        step = p.spec.speed * dt * p.time_scale * p.pace
        if p.seek_turn > 0 and _relentless(p):
            p.max_range += step               # (Wyrmseeker Staff (L): no range while it hunts)
        if p.lock is not None:                # (Crossbeam Wand +9: Lockstep)
            _follow(p)
        if p.path:                            # (Songbird Lute +3: Birdsong)
            _walk_path(p, step)
        if p.curve:
            _bend(p, step)
            if not p.curve and p.mid is not None and p.lock is None:
                _burn_in(p, zones)            # (Crossbeam Wand (L): the crossing glows)
                _cross_again(p)               # (Crossbeam Wand +6: Second crossing)
        remaining = p.max_range - p.travelled
        last_leg = step >= remaining
        if last_leg:
            step = remaining
        dx, dy = p.dir_x * step, p.dir_y * step
        if p.drift_left > 0:                  # (Twinned Quiver +6: drifting apart)
            side = min(abs(p.drift) * step, p.drift_left)
            p.drift_left -= side
            side = math.copysign(side, p.drift)
            dx, dy = dx - p.dir_y * side, dy + p.dir_x * side

        tile_hit = first_hit(world.tile_at, p.x, p.y, p.x + dx, p.y + dy)
        if tile_hit is not None and p.seek_turn > 0 and _phases(p):
            tile_hit = None                   # Phase Darts: through walls and trees
            p.haunted = True                  # (Ghostwood Staff +3: Haunt)
        best_t = tile_hit.t if tile_hit is not None else math.inf
        best_t, victim = _first_actor(grid, p, dx, dy, best_t)

        if victim is not None and _ice_wall(p, victim):
            # Rime Hood +6 (Hoarfrost): a frozen enemy stops enemy shots.
            effects.append(Effect("fizzle", p.x + dx * best_t, p.y + dy * best_t))
            p.alive = False
            continue
        if victim is not None:
            hx, hy = p.x + dx * best_t, p.y + dy * best_t
            planet = _planet(p, victim)
            events += _hit_actor(p, victim, hx, hy, world, actors, effects, spawned, zones,
                                 projectiles)
            through = p.spec.returns or planet
            if not through and p.pierce_left > 0:
                p.pierce_left -= 1
                through = True
                _passing(p, victim)
            if p.spec.returns and not p.returning:
                _pinball(p, victim, hx, hy)
            if through or _hunt_on(p, victim):
                # Through it: carry on from the hit point next step (the
                # rest of this step's distance is dropped -- a fraction of
                # a tile). Boomerangs pass through everything; a swinging
                # dart past what isn't its target (Planets); a dart hunting
                # on (Endless hunt).
                if planet:
                    p.passed.add(id(victim))
                p.hit.add(id(victim))
                p.x, p.y = hx, hy
                p.travelled += step * best_t
                continue
            p.hit.add(id(victim))
            if _run_through(p, hx, hy, step * best_t, victim):
                continue
            p.alive = False
            continue
        if tile_hit is not None:
            events.append(_terrain_impact(
                world, tile_hit, outgoing(p.owner, p.damage, p.tags) * p.mult,
                p.spec.damages_terrain, p.angle, effects
            ))
            if p.bounces < p.spec.bounces:    # (P9: glass shards glance off walls)
                p.travelled += step * tile_hit.t
                p.x = tile_hit.x - p.dir_x * 0.05
                p.y = tile_hit.y - p.dir_y * 0.05
                _reflect(p, tile_hit)
                p.bounces += 1
                continue
            if p.spec.returns:
                # Bounces off the wall: on (Ricochet) or home.
                p.travelled += step * tile_hit.t
                p.x = tile_hit.x - p.dir_x * 0.05
                p.y = tile_hit.y - p.dir_y * 0.05
                if not _ricochet(p, tile_hit, actors, world):
                    _end_throw(p, spawned)
                elif _carom_home(p):
                    _turn_back(p, spawned)
                continue
            wx, wy = tile_hit.x - p.dir_x * 0.05, tile_hit.y - p.dir_y * 0.05
            _split_on_wall(p, wx, wy, tile_hit, spawned, actors, zones)
            _aria(p, wx, wy, actors, effects)
            if _run_through(p, wx, wy, step * tile_hit.t):
                continue
            p.alive = False
            continue
        if p.cancels:
            _cut_shot(p, projectiles, effects, dx, dy, dt)
        elif _warding(p) and _prism_ward(p, projectiles, effects, dx, dy, dt, spawned):
            continue
        p.x += dx
        p.y += dy
        p.travelled += step
        if _split(p, spawned, actors, effects):
            continue
        if last_leg:
            if p.spec.returns:
                _end_throw(p, spawned)
                continue
            if _orbit_again(p, actors) or _park(p, projectiles) or _run_through(p, p.x, p.y, 0.0):
                continue
            _aria(p, p.x, p.y, actors, effects)
            effects.append(Effect("fizzle", p.x, p.y))
            events.append(FIZZLE)
            p.alive = False
    _chain_gang(projectiles, actors, effects, dt)   # (M28.3k: Chainlink Axe (L))
    _reunite(projectiles)
    _shot_ends([p for p in projectiles if not p.alive], spawned, zones, world, actors)
    projectiles[:] = [p for p in projectiles if p.alive] + spawned
    return events


def _big(a) -> bool:
    """An elite or a boss (Rebound Axe +6, Pinball)."""
    spec = getattr(a, "espec", None)
    return bool(getattr(a, "boss", False) or getattr(spec, "elite", False))


def _passing(p: Projectile, victim: Actor) -> None:
    """A shot piercing through an enemy: Broadleaf +3 (Gathering speed)
    speeds it up; Farsight +3 (Follow-through) readies the next arrow once
    a crit has gone through FOLLOW_THROUGH enemies."""
    p.pierced += 1
    stats = _stats_of(p)
    if stats is None or p.summon:
        return
    if stats.has("broadhead+3"):
        p.pace *= config.GATHERING_SPEED
    if stats.has("broadhead+L"):
        p.size += config.WIDENING                   # (Broadleaf Bow (L): Widening)
        p.widened += 1
    if p.deadeye and not p.followed and p.pierced >= config.FOLLOW_THROUGH \
            and stats.has("deadeye+3") and getattr(p.owner, "weapon", None) is not None:
        p.followed = True
        p.owner.weapon.cooldown = min(p.owner.weapon.cooldown, 0.0)


def _run_through(p: Projectile, x: float, y: float, moved: float, victim=None) -> bool:
    """Broadleaf Bow +6 (Run-through): an arrow that went through
    RUN_THROUGH or more enemies turns round where it stops (an enemy, a
    wall, the end of its range) and flies back along its path, once, as
    far as it came, through what it passed."""
    stats = _stats_of(p)
    if p.came_back or p.spec.returns or p.summon or stats is None \
            or not stats.has("broadhead+6") or p.pierced < config.RUN_THROUGH:
        return False
    p.came_back = True
    p.travelled += moved
    p.x, p.y = x, y
    p.dir_x, p.dir_y = -p.dir_x, -p.dir_y
    p.angle = math.atan2(p.dir_y, p.dir_x)
    p.pierce_left = max(p.pierce_left, p.pierced)
    p.max_range = p.travelled * 2
    p.hit = {id(victim)} if victim is not None else set()
    return True


def _pinball(p: Projectile, victim: Actor, hx: float, hy: float) -> None:
    """Rebound Axe +6 (Pinball): an axe on its way out glances off an elite
    or a boss, once a throw, as off a wall (round its body)."""
    stats = _stats_of(p)
    if p.pinballed or p.summon or stats is None or not stats.has("ricochet+6") \
            or not _big(victim):
        return
    nx, ny = hx - victim.x, hy - victim.y
    n = math.hypot(nx, ny)
    if n < 1e-6:
        nx, ny, n = -p.dir_x, -p.dir_y, 1.0
    nx, ny = nx / n, ny / n
    dot = p.dir_x * nx + p.dir_y * ny
    if dot < 0:
        p.dir_x -= 2 * dot * nx
        p.dir_y -= 2 * dot * ny
    else:                                       # (struck from inside: straight back)
        p.dir_x, p.dir_y = -p.dir_x, -p.dir_y
    p.angle = math.atan2(p.dir_y, p.dir_x)
    p.pinballed = True
    p.hit.clear()


def _carom_home(p: Projectile) -> bool:
    """Rebound Axe +9 (Carom): after its last bounce the axe flies home."""
    stats = _stats_of(p)
    return stats is not None and stats.has("ricochet+9") and p.bounces >= config.CAROM


def _end_throw(p: Projectile, spawned) -> None:
    """Where an axe's throw ends (full range, or a wall it doesn't bounce
    off): it hangs (Hang Time), swings round (Flail) or turns home."""
    if not _hang(p) and not _flail(p):
        _turn_back(p, spawned)


def _flail(p: Projectile) -> bool:
    """Chainlink Axe +9 (Flail): at the end of its throw the axe swings once
    round its thrower on its chain, at its distance, before coming back."""
    stats = _stats_of(p)
    owner = p.owner
    if p.flailed or p.summon or p.halved or stats is None or not stats.has("tether+9") \
            or owner is None:
        return False
    r = math.hypot(p.x - owner.x, p.y - owner.y)
    if r < 1.0:
        return False
    p.flailed = True
    p.flail, p.flail_r = math.tau, r
    p.flail_a = math.atan2(p.y - owner.y, p.x - owner.x)
    p.hit.clear()
    return True


def _swing_round(p: Projectile, grid: ActorGrid, world, effects: list[Effect], dt: float,
                 actors: list[Actor], spawned, zones) -> list[str]:
    """A flailing axe this step: round its thrower, hitting what it meets
    (each once a swing), over walls (it's on a chain); then home."""
    owner = p.owner
    if owner is None or not owner.alive:
        p.flail = 0.0
        _turn_back(p, spawned)
        return []
    turn = min(p.flail, p.spec.speed * dt / p.flail_r)
    p.flail -= turn
    p.flail_a += turn
    nx = owner.x + math.cos(p.flail_a) * p.flail_r
    ny = owner.y + math.sin(p.flail_a) * p.flail_r
    dx, dy = nx - p.x, ny - p.y
    p.spin += p.spec.speed * dt
    events: list[str] = []
    while True:
        t, victim = _first_actor(grid, p, dx, dy, math.inf)
        if victim is None:
            break
        p.hit.add(id(victim))
        events += _hit_actor(p, victim, p.x + dx * t, p.y + dy * t, world, actors, effects,
                             spawned, zones)
    p.x, p.y = nx, ny
    p.angle = p.flail_a + math.pi / 2
    p.dir_x, p.dir_y = math.cos(p.angle), math.sin(p.angle)
    if p.flail <= 1e-9:
        p.flail = 0.0
        _turn_back(p, spawned)
    return events


def _reunite(projectiles: list[Projectile]) -> None:
    """Doublebit Axe +3 (Reunite): two pieces of one axe that meet on the
    way back (within REUNITE[0] tiles) become one: their damage added, and
    +REUNITE[1] on its hits (see _hit_actor)."""
    groups: dict[int, list[Projectile]] = {}
    for q in projectiles:
        if q.alive and q.pieces is not None and q.returning:
            groups.setdefault(id(q.pieces), []).append(q)
    for qs in groups.values():
        for i, a in enumerate(qs):
            if not a.alive:
                continue
            for b in qs[i + 1:]:
                if b.alive and math.hypot(a.x - b.x, a.y - b.y) <= config.REUNITE[0]:
                    a.damage += b.damage
                    a.reunited = True
                    a.hit |= b.hit
                    a.child = a.child and b.child
                    a.cross = None
                    b.alive = False


def _ice_wall(p: Projectile, victim: Actor) -> bool:
    owner = p.owner
    return (victim.status is not None and owner is not None
            and getattr(owner, "faction", None) != "player" and victim.status.walls())


def _cut_shot(p: Projectile, projectiles: list[Projectile], effects: list[Effect],
              dx: float, dy: float, dt: float) -> None:
    """Compass Orb +6 (North star): the first enemy shot this one touches
    along this step (dx, dy) is destroyed -- the reach grows by how far the
    other shot moves in a step, so two fast shots can't pass through each
    other between frames. Lobbed ones are in the air, out of reach."""
    for q in projectiles:
        if q is p or not q.alive or q.spec.lob or q.owner is None \
                or getattr(q.owner, "faction", None) == "player":
            continue
        reach = config.NORTH_STAR_RADIUS + p.size + q.spec.speed * dt * q.time_scale
        if segment_circle_t(p.x, p.y, dx, dy, q.x, q.y, reach) is not None \
                or math.hypot(q.x - p.x, q.y - p.y) <= reach:
            q.alive = False
            p.cancels = False
            effects.append(Effect("fizzle", q.x, q.y))
            return


def _warding(p: Projectile) -> bool:
    """Kaleido Scepter (L), Prism ward: the princess's own colours (not the
    pieces split off them) hit enemy shots."""
    if p.spec.look != "prism" or p.summon or p.refracted or p.child:
        return False
    stats = _stats_of(p)
    return stats is not None and stats.has("refraction+L")


def _prism_ward(p: Projectile, projectiles: list[Projectile], effects: list[Effect],
                dx: float, dy: float, dt: float, spawned: list) -> bool:
    """Prism ward: the first enemy shot this colour touches along this step
    (as North star finds it) is split into PRISM_WARD of the princess's
    colours, fanned on along the colour's way like Refraction's pieces.
    The colour is spent (a beam goes on). True if it was."""
    for q in projectiles:
        if q is p or not q.alive or q.spec.lob or q.owner is None \
                or getattr(q.owner, "faction", None) == "player":
            continue
        reach = config.NORTH_STAR_RADIUS + p.size + q.spec.speed * dt * q.time_scale
        if segment_circle_t(p.x, p.y, dx, dy, q.x, q.y, reach) is None \
                and math.hypot(q.x - p.x, q.y - p.y) > reach:
            continue
        q.alive = False
        effects.append(Effect("fizzle", q.x, q.y))
        n, spread = config.PRISM_WARD, math.radians(config.REFRACTION_SPREAD)
        colors = len(config.SPECTRUM_STATUS)
        for k in range(n):
            c = _child(p, q.x, q.y, p.angle + spread * (k / (n - 1) - 0.5),
                       config.REFRACTION_DAMAGE)
            c.variant = (p.variant + k) % colors
            c.max_range = max(1.0, p.max_range - p.travelled)
            c.refracted = 1
            c.hit = set()
            spawned.append(c)
        if p.beam:
            return False
        p.alive = False
        return True
    return False


def _sunspot(p: Projectile, x: float, y: float, victim=None) -> None:
    """Sunwheel (L), Sunspot: the first of the 10th attack's shots to hit
    an enemy (or to end) sets the burst off there (run_rules._sunspot)."""
    token = p.sunspot
    if token is None or token["done"]:
        return
    token["done"] = True
    combos.append(("sunspot", victim, p.owner, (x, y, token)))


def _shot_ends(ended: list[Projectile], spawned: list[Projectile], zones, world=None,
               actors=()) -> None:
    """Shots that leave something where they stop, whatever stopped them
    (P8): a giant spider's web blob leaves a sticky patch (a zone that
    slows to WEB[2]); a witch's apprentice's cursed orb splits into
    CURSE_SPLIT[0] smaller ones, all round. P11: a lizardman's javelin
    sticks in the ground where it stops -- a solid tile for JAVELIN_STUCK s
    (not on a body, not on what's already solid), then the ground again."""
    for p in ended:
        _sunspot(p, p.x, p.y)                         # (M28.3d: Sunwheel (L))
        look = p.spec.look
        if p.ball is not None:                        # (Crackle Staff +9: it missed)
            p.ball.append((p.x, p.y))
            _roll_ball(p, zones)
        if p.wisp and zones is not None and getattr(p.owner, "stats", None) is not None:
            from .zones import Zone                   # (Firefly Lantern +9: Will-o'-wisps)
            _, life, radius = config.WISPS
            zones.append(Zone("wisp", p.x, p.y, radius * p.owner.stats.area_scale, life, 0.5,
                              0.0, p.owner, p.tags, "burn", 1))
            continue
        if look == "javelin" and zones is not None and world is not None \
                and hasattr(world, "set_tile"):
            from ..world import tiles
            from .zones import Zone
            tx, ty = math.floor(p.x), math.floor(p.y)
            old = world.tile_at(tx, ty)
            if not old.solid and not any(math.hypot(a.x - tx - 0.5, a.y - ty - 0.5)
                                         < a.hit_radius + 0.8 for a in actors):
                world.set_tile(tx, ty, tiles.STUCK_JAVELIN)
                zones.append(Zone("stake", tx + 0.5, ty + 0.5, 0.0, config.JAVELIN_STUCK, 999.0,
                                  0.0, None, restore=(tx, ty, old)))
            continue
        if look == "web" and zones is not None:
            from .zones import Zone
            radius, life, slow = config.WEB
            zones.append(Zone("web", p.x, p.y, radius, life, 0.1, 0.0, p.owner, slow=slow))
        elif look == "curse_orb" and not p.child:
            n, share, speed = config.CURSE_SPLIT
            shell = replace(p.spec, look="curse_bit", speed=speed, max_range=6.0)
            for k in range(n):
                a = p.angle + math.pi / n + k * math.tau / n
                c = Projectile(p.x - p.dir_x * 0.3, p.y - p.dir_y * 0.3, a, shell,
                               owner=p.owner, damage=p.damage * share)
                c.child = True
                spawned.append(c)


def _nearest_foe(x: float, y: float, radius: float, actors, owner, skip=None, skip_ids=()):
    """The hittable actor `owner` may hurt nearest (x, y), within `radius`
    (plus its body), or None. Not `skip`, nor any whose id is in `skip_ids`."""
    best, best_d = None, math.inf
    for a in actors:
        if a is skip or not a.hittable or not _may_hurt(owner, a) or id(a) in skip_ids:
            continue
        d = math.hypot(a.x - x, a.y - y)
        if d <= radius + a.hit_radius and d < best_d:
            best, best_d = a, d
    return best


def _home(p: Projectile, actors, dt: float) -> None:
    """A homing shot (the wizard's darts): straight for its first
    seek_after tiles, then it picks the enemy nearest its seek point (the
    aim point; or itself, once it's lost one with Seeker) and turns toward
    it at up to seek_turn rad/s. A target that dies or vanishes is lost:
    the dart flies on straight, unless Seeker lets it look again."""
    t = p.seek
    if t is None and p.travelled < p.spec.seek_after:
        return
    if t is not None and t is not False and not t.hittable:
        stats = _stats_of(p)
        if stats is not None and stats.has("seeker"):
            p.seek, p.seek_point, t = None, None, None
            if stats.has("seeker+3") and not p.persisted:     # Wyrmseeker +3 (Persistence)
                p.persisted = True
                p.pace *= config.PERSISTENCE
        else:
            p.seek = t = False
    if t is None:
        t = p.seek = _seek(p, actors) or False
    if t is False:
        return
    want = math.atan2(t.y - p.y, t.x - p.x)
    turn = wrap_angle(want - p.angle)
    most = p.seek_turn * dt
    p.angle += max(-most, min(most, turn))
    p.dir_x, p.dir_y = math.cos(p.angle), math.sin(p.angle)


def _seek(p: Projectile, actors):
    """Who a homing dart goes for: the enemy nearest its seek point (or
    itself), not one it already hit hunting on (Endless hunt). The
    wizard's main hand: Wyrmseeker +6 (Hunter-seeker) the one with the
    least HP there instead; Ghostwood +9 (Ghost sight) with nobody there,
    the nearest within GHOSTWOOD_SIGHT of its owner, walls or not."""
    stats = _stats_of(p)
    has = stats.has if stats is not None and not p.summon else (lambda flag: False)
    cx, cy = p.seek_point if p.seek_point is not None else (p.x, p.y)
    skip = p.hit if p.hunts else ()
    radius = p.spec.seek_radius
    if has("seeker+6"):
        t = None
        for a in actors:
            if a.hittable and _may_hurt(p.owner, a) and id(a) not in skip \
                    and math.hypot(a.x - cx, a.y - cy) <= radius + a.hit_radius \
                    and (t is None or a.hp < t.hp):
                t = a
    else:
        t = _nearest_foe(cx, cy, radius, actors, p.owner, skip_ids=skip)
    if t is None and has("phase_darts+9") and p.owner is not None:
        t = _nearest_foe(p.owner.x, p.owner.y, config.GHOSTWOOD_SIGHT, actors, p.owner, skip_ids=skip)
    return t


def _planet(p: Projectile, victim: Actor) -> bool:
    """Orrery Staff +3 (Planets): a dart swinging round toward its target
    hits what it passes on the way and flies on."""
    stats = _stats_of(p)
    t = p.seek
    return (p.orbits > 0 and t is not None and t is not False and t is not victim
            and stats is not None and not p.summon and stats.has("orbiting_darts+3"))


def _hunt_on(p: Projectile, victim: Actor) -> bool:
    """Wyrmseeker Staff +9 (Endless hunt): after its hit a dart looks for a
    new target and flies on, ENDLESS_HUNT[0] hits in all, the ones after the
    first at ENDLESS_HUNT[1]; it gets ENDLESS_HUNT[2] tiles more flight."""
    stats = _stats_of(p)
    most, share, more = config.ENDLESS_HUNT
    if p.seek_turn <= 0 or p.summon or stats is None or not stats.has("seeker+9") \
            or p.hunts + 1 >= most:
        return False
    if p.hunts == 0:
        p.mult *= share
    p.hunts += 1
    p.seek, p.seek_point = None, None
    p.max_range = max(p.max_range, p.travelled + more)
    return True


def _orbit_again(p: Projectile, actors) -> bool:
    """Orbiting Darts (a card): a dart that reaches the end of its flight
    without hitting anything swings round toward the enemy nearest its
    owner (within ORBIT_REACH) and gets its range again -- enough to reach
    that enemy at least -- once. Orrery Staff +6 (Epicycle): twice; +9
    (Gravity assist): it comes back faster (and harder, see _hit_actor)."""
    stats = _stats_of(p)
    if p.seek_turn <= 0 or stats is None or not stats.has("orbiting_darts") or p.owner is None:
        return False
    if p.orbits >= (config.EPICYCLE if stats.has("orbiting_darts+6") else 1) \
            or p.hit - p.passed:
        return False
    t = _nearest_foe(p.owner.x, p.owner.y, config.ORBIT_REACH, actors, p.owner)
    if t is None:
        return False
    p.orbits += 1
    if p.orbits == 1 and stats.has("orbiting_darts+9"):
        p.pace *= config.GRAVITY_ASSIST[0]
    p.seek = t
    p.travelled = 0.0
    # Enough to turn round (half a circle at its turn rate) and reach it.
    turning = math.pi * p.spec.speed / p.seek_turn
    p.max_range = max(p.max_range, math.hypot(t.x - p.x, t.y - p.y) + turning + 2.0)
    return True


def _recurve(p: Projectile, dt: float) -> bool:
    """Splitbranch Bow (L), Recurve: a split arrow, RECURVE[0] tiles out,
    curves round (RECURVE[1] rad/s) back toward its owner, sweeping the way
    back -- what it hit going out may be hit again -- and ends when it
    reaches them (RECURVE[2] tiles). Returns True once it has ended."""
    out, turn, near = config.RECURVE
    owner = p.owner
    if owner is None or not owner.alive:
        p.recurve = False
        return False
    if p.recurve is True:
        if p.travelled < out:
            return False
        p.recurve = "back"
        p.hit.clear()
        # Enough range to turn round (half a circle) and reach its owner.
        p.max_range = p.travelled + math.hypot(owner.x - p.x, owner.y - p.y) \
            + math.pi * p.spec.speed / turn + 2.0
    d = math.hypot(owner.x - p.x, owner.y - p.y)
    if d <= near:
        p.alive = False
        return True
    want = math.atan2(owner.y - p.y, owner.x - p.x)
    most = turn * dt
    p.angle += max(-most, min(most, wrap_angle(want - p.angle)))
    p.dir_x, p.dir_y = math.cos(p.angle), math.sin(p.angle)
    p.max_range = max(p.max_range, p.travelled + d)
    return False


def _relentless(p: Projectile) -> bool:
    """Wyrmseeker Staff (L), Relentless: a dart with a target doesn't use
    up its range -- it flies on until it hits (or loses it)."""
    t, stats = p.seek, _stats_of(p)
    return (t is not None and t is not False and t.hittable and not p.summon
            and stats is not None and stats.has("seeker+L"))


def _park(p: Projectile, projectiles) -> bool:
    """Orrery Staff (L), Clockwork: a dart that ends its flight without a
    hit (its swings round you used up, or nobody to swing at) is kept in
    orbit round its owner, CLOCKWORK[0] at most."""
    stats = _stats_of(p)
    if p.seek_turn <= 0 or p.summon or stats is None or not stats.has("orbiting_darts+L") \
            or p.owner is None or not p.owner.alive or p.hit - p.passed:
        return False
    kept = sum(1 for q in projectiles if q.alive and q.parked is not None and q.owner is p.owner)
    if kept >= config.CLOCKWORK[0]:
        return False
    p.parked = math.atan2(p.y - p.owner.y, p.x - p.owner.x)
    _orbit_spot(p)
    return True


def _orbit_spot(p: Projectile) -> None:
    """Where a kept dart is: CLOCKWORK[2] tiles from its owner, at its angle,
    heading round."""
    radius = config.CLOCKWORK[2]
    o = p.owner
    p.x, p.y = o.x + math.cos(p.parked) * radius, o.y + math.sin(p.parked) * radius
    p.angle = p.parked + math.pi / 2
    p.dir_x, p.dir_y = math.cos(p.angle), math.sin(p.angle)


def _clockwork(p: Projectile, actors, dt: float) -> None:
    """A kept dart circles its owner until an enemy comes within
    CLOCKWORK[1] tiles of them, then flies at it (a fresh flight, enough to
    reach it). It goes when its owner does."""
    _, reach, _, speed = config.CLOCKWORK
    o = p.owner
    if o is None or not o.alive:
        p.alive = False
        return
    p.parked += speed * dt
    _orbit_spot(p)
    t = _nearest_foe(o.x, o.y, reach, actors, o)
    if t is None:
        return
    p.parked = None
    p.seek, p.seek_point = t, None
    p.angle = math.atan2(t.y - p.y, t.x - p.x)
    p.dir_x, p.dir_y = math.cos(p.angle), math.sin(p.angle)
    p.travelled = 0.0
    p.max_range = max(p.spec.max_range, math.hypot(t.x - p.x, t.y - p.y) + 2.0)
    p.hit, p.passed = set(), set()


def _weave(p: Projectile) -> None:
    """A weaving shot: its heading swings to either side of its aim, a
    full swing every spec.wobble_tiles tiles flown."""
    a = p.base_angle + p.spec.wobble * math.sin(p.travelled / p.spec.wobble_tiles * math.tau)
    p.angle = a
    p.dir_x, p.dir_y = math.cos(a), math.sin(a)


def _bend(p: Projectile, step: float) -> None:
    """Converge: turn by the shot's curve for this step's tiles, until its
    turn is used up."""
    turn = p.curve * step
    if abs(turn) >= p.curve_left:
        turn = math.copysign(p.curve_left, turn)
        p.curve = 0.0
    p.curve_left -= abs(turn)
    p.angle += turn
    p.dir_x, p.dir_y = math.cos(p.angle), math.sin(p.angle)


def _walk_path(p: Projectile, step: float) -> None:
    """Birdsong: a note heads for the next corner of its way round the
    walls, and on once it's there."""
    while p.path:
        wx, wy = p.path[0]
        if math.hypot(wx - p.x, wy - p.y) > max(step, 0.3):
            break
        p.path.pop(0)
    if p.path:
        wx, wy = p.path[0]
    elif p.bird is not None and p.bird.alive:
        wx, wy = p.bird.x, p.bird.y
    else:
        return
    p.angle = math.atan2(wy - p.y, wx - p.x)
    p.dir_x, p.dir_y = math.cos(p.angle), math.sin(p.angle)


def _phases(p: Projectile) -> bool:
    """Phase Darts (P4): the wizard's darts fly through walls and trees."""
    stats = _stats_of(p)
    return stats is not None and not p.summon and stats.has("phase_darts")


def _stats_of(p: Projectile):
    return getattr(p.owner, "stats", None)


def _child(p: Projectile, x: float, y: float, angle: float, factor: float) -> Projectile:
    """A shot split off `p` (it can't split again)."""
    c = Projectile(x, y, angle, p.spec, owner=p.owner, damage=p.damage * factor)
    for name in ("variant", "tags", "mult", "size", "summon", "inflicts"):
        setattr(c, name, getattr(p, name))
    c.child = True
    c.gen = p.gen + 1
    c.family = p.family
    c.violet = p.violet
    st = _stats_of(p)
    if p.spec.look == "prism" and p.group is not None and st is not None and st.has("prism+L"):
        c.group = p.group                     # (Prismatic Wand (L): Overlap, pieces count)
    c.echo = p.echo
    c.max_range = p.max_range
    c.hit = set(p.hit)
    c.pierce_left = p.pierce_left
    return c


def _ricochet(p: Projectile, hit: RayHit, actors=(), world=None) -> bool:
    """Ricochet (a card): an axe glances off the wall it hit and flies on,
    RICOCHET_BOUNCES times per throw. The face it hit is the one the
    entry point is closest to; the motion across that face flips. Rebound
    Axe (L), Trick shot: it goes for the nearest enemy in sight within the
    axe's reach instead (off the mirror angle if there's none)."""
    stats = _stats_of(p)
    most = config.CAROM if stats is not None and stats.has("ricochet+9") else config.RICOCHET_BOUNCES
    if stats is None or not stats.has("ricochet") or p.bounces >= most:
        return False
    _reflect(p, hit)
    if stats.has("ricochet+L") and not p.summon and world is not None:
        t = _nearest_in_sight(p.x, p.y, p.spec.max_range, actors, p.owner, world)
        if t is not None:
            p.angle = math.atan2(t.y - p.y, t.x - p.x)
            p.dir_x, p.dir_y = math.cos(p.angle), math.sin(p.angle)
    p.bounces += 1
    p.hit.clear()
    return True


def _nearest_in_sight(x: float, y: float, radius: float, actors, owner, world):
    """The enemy nearest (x, y) within `radius` with a clear line to it."""
    best, best_d = None, math.inf
    for a in actors:
        if not a.hittable or not _may_hurt(owner, a):
            continue
        d = math.hypot(a.x - x, a.y - y)
        if d <= radius + a.hit_radius and d < best_d \
                and first_hit(world.tile_at, x, y, a.x, a.y) is None:
            best, best_d = a, d
    return best


def _reflect(p: Projectile, hit: RayHit) -> None:
    """Turn a shot off the wall it hit: the face is the one the entry point
    is closest to; the motion across that face flips."""
    if _side_face(hit):
        p.dir_x = -p.dir_x
    else:
        p.dir_y = -p.dir_y
    p.angle = math.atan2(p.dir_y, p.dir_x)


def _side_face(hit: RayHit) -> bool:
    """Whether the face a shot hit is a tile's left or right side."""
    fx, fy = hit.x - hit.tx, hit.y - hit.ty
    return min(fx, 1 - fx) < min(fy, 1 - fy)


def _reflected(p: Projectile, hit: RayHit) -> float:
    """The heading a shot would turn to off the wall it hit (see _reflect)."""
    if _side_face(hit):
        return math.atan2(p.dir_y, -p.dir_x)
    return math.atan2(-p.dir_y, p.dir_x)


def split_now(p: Projectile, spawned: list[Projectile], actors=(), effects=None) -> bool:
    """Pepperbox (L), Hair trigger: split `p` now, wherever it is -- a whole
    shot or a piece of one, down to HAIR_TRIGGER splits deep. (Every hero
    weapon's shots reach half range within about one attack, so whole
    shots alone would hardly ever still be flying; a split's pieces fly
    their range over again.)"""
    return _split(p, spawned, actors, effects, now=True)


def _split(p: Projectile, spawned: list[Projectile], actors=(), effects=None,
           now: bool = False) -> bool:
    """Spray and Pray (a card): half way along its range a shot splits in
    two, each SPLIT_DAMAGE of it, SPLIT_SPREAD degrees apart. The Pepperbox's
    tricks (M28.2a): +3 the halves split once more at three-quarter range;
    +6 each split flashes (POWDER_FLASH); +9 a shot's pieces are one family
    (Buckshot, see _hit_actor). `now`: whatever its range (Hair trigger)."""
    stats = _stats_of(p)
    if stats is None or not stats.has("split") or p.spec.returns or p.spec.lob:
        return False
    if now:
        if p.gen >= config.HAIR_TRIGGER:
            return False
    elif p.gen == 0:
        if p.travelled < p.max_range / 2:
            return False
    elif not (p.gen == 1 and stats.has("spray_and_pray+3") and p.travelled >= p.max_range * 0.25):
        # (a half's own flight starts over at the split, half way: three
        # quarters of the shot's range is a quarter into the half's)
        return False
    if p.family is None and stats.has("spray_and_pray+9"):
        p.family = {}
    half = math.radians(config.SPLIT_SPREAD) / 2
    for side in (-1, 1):
        spawned.append(_child(p, p.x, p.y, p.angle + side * half, config.SPLIT_DAMAGE))
    if stats.has("spray_and_pray+6") and effects is not None:      # Powder flash
        radius, share = config.POWDER_FLASH
        effects.append(Effect("pulse", p.x, p.y, size=radius))
        for a in actors:
            if a.alive and a.hittable and _may_hurt(p.owner, a) and id(a) not in p.hit \
                    and math.hypot(a.x - p.x, a.y - p.y) <= radius + a.hit_radius:
                strike(a, p.damage * share, p.owner, None, effects, p.tags, mult=p.mult,
                       on_hit=False)
    p.alive = False
    return True


def _first_actor(grid: ActorGrid, p: Projectile, dx: float, dy: float,
                 best_t: float) -> tuple[float, Actor | None]:
    """The first actor the shot's segment (p.x, p.y) + t*(dx, dy) enters
    before `best_t` (that it may hurt and hasn't hit yet), and where."""
    victim, victim_i = None, -1
    for i, a in grid.near(p.x, p.y, p.x + dx, p.y + dy):
        if not a.hittable or id(a) in p.hit or not _may_hurt(p.owner, a):
            continue
        t = segment_circle_t(p.x, p.y, dx, dy, a.x, a.y, a.hit_radius + p.size)
        # Ties go to the actor earliest in `actors`, as a plain scan would.
        if t is not None and (t < best_t or (t == best_t and victim is not None and i < victim_i)):
            best_t, victim, victim_i = t, a, i
    return best_t, victim


def _hit_actor(p: Projectile, victim: Actor, hx: float, hy: float, world,
               actors: list[Actor], effects: list[Effect], spawned: list | None = None,
               zones: list | None = None, shots: list | None = None) -> list[str]:
    owner = p.owner
    stats = getattr(owner, "stats", None)
    _sunspot(p, hx, hy, victim)
    extra = 0.0
    whole = False                                  # (Prismatic Wand +3: Full spectrum)
    if stats is not None:
        # Broadhead: more damage for every enemy this arrow has already passed.
        extra += stats.broadhead * len(p.hit) * (2 if stats.has("broadhead+9") else 1)
        if p.returning:
            extra += stats.homeward                # Homeward Fury / Homecoming
        if p.spec.returns and not p.summon:
            extra += _axe_bonus(p, stats)
        if stats.prism and p.group is not None:    # Prism: colors on one enemy
            bonus, whole = _prism(p, victim, owner, stats)
            extra += bonus
        if p.middle:
            extra += config.LENS                   # (Spyglass Wand +3: Lens)
        if p.focal and stats.has("converge+3") and _at_focus(p, victim):
            extra += config.FOCAL_POINT[1]         # (Crossbeam Wand +3: Focal point)
    dart = p.spec.seek_turn > 0 and stats is not None and not p.summon
    hum = 0.0
    if dart and stats.has("resonance"):
        hum = _resonance(victim, owner, actors)
        extra += hum
    if dart:
        extra += _dart_bonus(p, victim, stats)
    mult = p.mult
    if p.grow:                                     # Nautilus Shell +3: bigger further out
        mult *= 1 + config.GROWING_SHELL[1] * min(1.0, p.travelled / max(0.1, p.max_range))
    if p.family is not None:                       # Pepperbox +9 (Buckshot)
        if p.family.get(id(victim)):
            mult *= 1 + config.BUCKSHOT
        p.family[id(victim)] = p.family.get(id(victim), 0) + 1
    vst = getattr(victim, "stats", None)
    if vst is not None and vst.has("juggernaut+3") and getattr(owner, "faction", None) != "player":
        armor = max(0.0, vst.armor + bonus_armor(victim))          # Mountainhide +3 (Glance)
        if victim.rng.random() < min(config.GLANCE[1], config.GLANCE[0] * armor):
            victim.blocked += 1
            effects.append(Effect("impact", hx, hy, p.angle))
            return []
    if p.plain:                                    # (Hairsbreadth +6: a shot thrown back)
        dealt = victim.take_damage(p.damage * mult, owner, p.angle)
        _number(effects, victim, dealt)
        effects.append(Effect("impact", hx, hy, p.angle))
        return [HIT]
    full = not p.summon or (stats is not None and stats.has("pack_leader"))
    if p.riposte:                                  # (Fencer's Boots: a riposte's shot)
        owner.riposting = True
    spectral = dart and stats.has("phase_darts+6")
    if spectral:                                   # (Ghostwood Staff +6: through fronts)
        owner.spectral = True
    hearth = p.returning and full and stats is not None and stats.has("homeward_fury+9")
    if p.spell:
        owner.spelling = True                      # (Fortissimo Lute (L): Tutti)
    dealt = strike(victim, p.damage, owner, p.angle, effects, p.tags, extra=extra, mult=mult,
                   on_hit=full, can_crit=full, sure_crit=p.sure_crit or hearth or whole,
                   crit_x=p.crit_x, pet=p.summon and not p.child)
    if p.spell:
        owner.spelling = False
    if p.riposte:
        owner.riposting = False
    if spectral:
        owner.spectral = False
    if hum >= config.RESONANCE[1] * config.RESONANCE[2] - 1e-9 and stats.has("resonance+6"):
        _resonant_ring(victim, owner, actors, effects, p.tags)
    if p.dizzy and victim.alive and not getattr(victim, "boss", False):
        victim.dizzy = config.DIZZY[1]             # (Dancing Slippers +6)
    if p.echo and not victim.alive:                # (Canyon Horn +6: an echo's kill)
        victim.echo_kill = True
    if p.twin is not None and victim.alive:        # Twinned Quiver +3 (Linked)
        _link_twins(p.twin, victim, owner)
    hook = getattr(owner, "on_shot_hit", None)      # (M24.1: the Fallout King's rads)
    if hook is not None and dealt:
        hook(victim, dealt)
    if dart:
        _dart_hit(p, victim, hx, hy, owner, stats, world, actors, effects, spawned, zones, shots)
    _aria(p, hx, hy, actors, effects, victim)
    effects.append(Effect("impact", hx, hy, p.angle))
    if p.inflicts is not None and victim.alive:
        inflict(victim, p.inflicts[0], owner, p.inflicts[1])
    if p.spec.look == "note" and not p.summon and victim.alive and stats is not None \
            and stats.has("sheet_music+L"):
        _earworm(victim, owner)                    # (Songbird Lute (L): Earworm)
    if p.glow and victim.alive:                    # (Firefly Lantern +3: Glow)
        victim.__dict__.setdefault("lit", {})[id(owner)] = owner.time + config.GLOW[1]
    if p.firefly and victim.alive and p.inflicts is not None:   # (Firefly Lantern (L))
        owner.fireflies.append([victim, config.FIREFLY[0], config.FIREFLY[1], p.inflicts])
    if p.shocks and victim.alive:                  # (Galvanic Mask +6: Battery's attack)
        inflict(victim, "shock", owner)
    if stats is not None and not p.summon:
        if victim.alive:
            _card_effects(p, victim, owner, stats)
        if p.spec.chain and stats.has("supercell+9"):
            _superstorm(victim, owner, actors)     # (Thunderhead Rod +9)
        _capstones(p, victim, hx, hy, owner, stats, spawned, zones, actors)
        if stats.arrow_split and spawned is not None:
            _split_arrow(p, victim, hx, hy, stats, spawned, actors, zones)
    events = [HIT]
    if p.spec.chain or p.extra_chain:
        if p.ball is not None:
            p.ball.append((hx, hy))
        events += chain_from(victim, p.spec, p.damage, owner, world, actors, effects, p.tags,
                             p.extra_chain, p.mult, charm=p.charm, zones=zones, path=p.ball)
        _roll_ball(p, zones)
    return events


def _aria(p: Projectile, x: float, y: float, actors, effects: list[Effect],
          victim=None) -> None:
    """Songbird Lute +9 (Aria): where a note lands (an enemy, a wall, the
    end of its flight) it hits everything else within ARIA tiles."""
    stats = _stats_of(p)
    if p.spec.look != "note" or p.summon or stats is None or not stats.has("sheet_music+9"):
        return
    effects.append(Effect("pulse", x, y, size=config.ARIA))
    for a in list(actors):
        if a is victim or not a.alive or not a.hittable or not _may_hurt(p.owner, a) \
                or math.hypot(a.x - x, a.y - y) > config.ARIA + a.hit_radius:
            continue
        strike(a, p.damage, p.owner, math.atan2(a.y - y, a.x - x), effects, p.tags,
               mult=p.mult, on_hit=False)


def _prism(p: Projectile, victim: Actor, owner, stats) -> tuple[float, bool]:
    """Prism (a card): +stats.prism for each other color of this shot that
    hit this enemy before (bucket A), and whether this hit must crit:
    Prismatic Wand +3 (Full spectrum), the color that makes it every color
    of the shot (FULL_SPECTRUM at most); +6 (Afterglow): the bonus the last shot reached on this
    enemy holds AFTERGLOW s for the next; +9 (Rainbow's end): x RAINBOWS_END."""
    seen = p.group.get(id(victim), 0)
    p.group[id(victim)] = seen + 1
    full = False
    colors = p.group.get("colors")
    if colors is not None:
        got = p.group.setdefault(("got", id(victim)), set())
        got.add(p.variant % len(config.SPECTRUM_STATUS))
        if len(got) >= colors and not p.group.get(("full", id(victim))):
            p.group[("full", id(victim))] = full = True
    if stats.has("prism+6"):
        glow = victim.__dict__.setdefault("afterglow", {})
        last = glow.get(id(owner))
        held = last[1] if last is not None and (last[0] is p.group or last[2] > owner.time) else 0
        seen = max(seen, held)
        glow[id(owner)] = (p.group, seen, owner.time + config.AFTERGLOW)
    bonus = stats.prism * seen
    return (bonus * config.RAINBOWS_END if stats.has("prism+9") else bonus), full


def _at_focus(p: Projectile, victim: Actor) -> bool:
    """Focal point: the enemy is at a crossing of the colors (or is what
    Lockstep follows)."""
    if p.lock is not None and victim is p.lock:
        return True
    r = config.FOCAL_POINT[0]
    return any(math.hypot(victim.x - fx, victim.y - fy) <= r + victim.hit_radius
               for fx, fy in p.focal)


def _roll_ball(p: Projectile, zones) -> None:
    """Crackle Staff +9 (Thunderball): the ball rolls the bolt's way, from
    where it was cast through each enemy it jumped to."""
    if p.ball is not None and zones is not None:
        from .zones import Zone
        _, life, radius = config.THUNDERBALL
        (x, y) = p.ball[0]
        zones.append(Zone("ball", x, y, radius, life, config.BALL_LIGHTNING_EVERY,
                          p.damage * config.BALL_LIGHTNING_DAMAGE, p.owner, p.tags,
                          path=list(p.ball)))
    p.ball = None


def _link_twins(pair: dict, victim: Actor, owner) -> None:
    """Linked: once the twins of one shot have hit two different enemies,
    those two are linked for LINKED[0] s (see strike)."""
    hit = pair.setdefault("hit", [])
    if victim in hit:
        return
    hit.append(victim)
    if len(hit) == 2:
        a, b = hit
        until = getattr(owner, "time", 0.0) + config.LINKED[0]
        a.link, b.link = (b, until), (a, until)


def _card_effects(p: Projectile, victim: Actor, owner: Actor, stats) -> None:
    """Hero cards that make a shot's hit inflict a status."""
    if stats.has("supercell") and p.spec.chain:
        bolt_shock(victim, owner)                    # the wizard's bolts shock
    if stats.has("spectrum") and p.spec.look == "prism":
        # Chroma Wand +3 (Saturated): a likelier status; +9 (Chromatic): two.
        name = "bleed" if p.violet else config.SPECTRUM_STATUS[p.variant % len(config.SPECTRUM_STATUS)]
        chance = config.SATURATED if stats.has("spectrum+3") else config.SPECTRUM_CHANCE
        if name is not None and owner.rng.random() < chance:
            inflict(victim, name, owner, config.CHROMATIC if stats.has("spectrum+9") else 1)


def _capstones(p: Projectile, victim: Actor, hx: float, hy: float, owner: Actor, stats,
               spawned, zones, actors=()) -> None:
    """Capstone cards that change what a shot does once it hits."""
    if stats.has("deadeye") and getattr(owner, "last_crit", False):
        p.deadeye = True                             # (Farsight Bow +3: Follow-through)
        p.pierce_left = 10 ** 6                      # Deadeye: through everything...
        p.max_range = max(p.max_range, p.spec.max_range * 2)   # ...and twice as far
        box = getattr(owner, "view_box", None)
        if box is not None and stats.has("deadeye+L"):          # (Farsight Bow (L): Farsight)
            p.max_range = max(p.max_range, p.travelled + _to_edge(hx, hy, p.dir_x, p.dir_y, box))
    if stats.has("refraction") and p.spec.look == "prism" and spawned is not None:
        _refract(p, victim, hx, hy, owner, stats, spawned, actors)
    if stats.has("ball_lightning") and p.spec.chain and zones is not None:
        _crackle(zones, victim, p.damage, owner, p.tags, hx, hy)


def farsight_lean(hero, view_w: float, view_h: float) -> tuple[float, float]:
    """Farsight Bow (L): how far (tiles) the camera leans from the hero
    toward its aim -- FARSIGHT[1] of the way to the aim point, at most
    FARSIGHT[0] of the view each way (view_w, view_h: the view in tiles)."""
    st = getattr(hero, "stats", None)
    if st is None or not st.has("deadeye+L"):
        return 0.0, 0.0
    most, share = config.FARSIGHT
    aim = getattr(hero, "aim_point", None)
    if aim is not None:
        dx, dy = (aim[0] - hero.x) * share, (aim[1] - hero.y) * share
    else:
        dx, dy = math.cos(hero.aim_angle) * view_w, math.sin(hero.aim_angle) * view_h
    return (max(-most * view_w, min(most * view_w, dx)),
            max(-most * view_h, min(most * view_h, dy)))


def _to_edge(x: float, y: float, dx: float, dy: float, box) -> float:
    """Tiles from (x, y) along (dx, dy) to the edge of `box` (cx, cy, half
    width, half height), 0 if it's outside."""
    cx, cy, hw, hh = box
    if abs(x - cx) > hw or abs(y - cy) > hh:
        return 0.0
    t = math.inf
    for p0, d, c, h in ((x, dx, cx, hw), (y, dy, cy, hh)):
        if abs(d) > 1e-9:
            t = min(t, ((c + h if d > 0 else c - h) - p0) / d)
    return 0.0 if t == math.inf else t


def _refract(p: Projectile, victim: Actor, hx: float, hy: float, owner, stats, spawned,
             actors) -> None:
    """Refraction: a color that hits splits into REFRACTION_SPLIT pieces
    (a beam only on its first enemy). The Kaleido Scepter: +3 (Shards of
    light) as many pieces as there are enemies in reach go for the nearest
    ones; +6 (Radiant split) pieces hit from farther; +9 (Infinite mirror)
    a piece that hits splits again into 2, up to 3 times."""
    if p.beam and p.pierced:
        return
    if p.refracted:
        pieces, times, fan = config.INFINITE_MIRROR
        if not stats.has("refraction+9") or p.refracted > times:
            return
        n, spread = pieces, math.radians(fan)
    elif p.child:
        return
    else:
        n, spread = config.REFRACTION_SPLIT, math.radians(config.REFRACTION_SPREAD)
    reach = max(1.0, p.max_range - p.travelled)
    aims = []
    if stats.has("refraction+3"):
        near = sorted((math.hypot(a.x - hx, a.y - hy), i, a) for i, a in enumerate(actors)
                      if a is not victim and a.alive and a.hittable and _may_hurt(owner, a)
                      and math.hypot(a.x - hx, a.y - hy) <= reach)
        aims = [math.atan2(a.y - hy, a.x - hx) for _, _, a in near[:n]]
    for i in range(n):
        a = aims[i] if i < len(aims) else p.angle + spread * (i / (n - 1) - 0.5)
        c = _child(p, hx, hy, a, config.REFRACTION_DAMAGE)
        c.hit.add(id(victim))
        c.max_range = reach
        c.refracted = p.refracted + 1
        if p.beam:
            c.pierce_left = p.spec.pierce              # (a piece of the beam is a plain color)
        if stats.has("refraction+6") and p.refracted == 0:
            c.size += config.RADIANT_SPLIT
        spawned.append(c)


def _axe_bonus(p: Projectile, stats) -> float:
    """Bucket A an axe gets from the dwarf's main hand: Rebound Axe +3 (Bank
    shot: a bounce, Pinball's too), Hoverhead +3 (Saw: each hit so far
    while hovering), Doublebit +3 (Reunite)."""
    a = 0.0
    if stats.has("ricochet+3"):
        a += config.BANK_SHOT * (p.bounces + p.pinballed)
    if p.hang > 0 and stats.has("hang_time+3"):
        a += config.SAW * p.saws
        p.saws += 1
    if p.reunited:
        a += config.REUNITE[1]
    return a


def _dart_bonus(p: Projectile, victim: Actor, stats) -> float:
    """Bucket A a dart gets from the main hand's tricks: Thunderhead +3
    (Charged air: shocked enemies), Ghostwood +3 (Haunt: through a wall
    first), Orrery +9 (Gravity assist: after a swing round you)."""
    a = 0.0
    if stats.has("supercell+3") and _shocked(victim):
        a += config.CHARGED_AIR
    if p.haunted and stats.has("phase_darts+3"):
        a += config.HAUNT
    if p.orbits and stats.has("orbiting_darts+9"):
        a += config.GRAVITY_ASSIST[1]
    return a


def _resonant_ring(victim: Actor, owner, actors, effects: list[Effect], tags) -> None:
    """Humming Staff +6 (Resonant ring): an enemy hit at +60% gives off a
    ring, everything within RESONANT_RING[1] tiles (x area) taking
    RESONANT_RING[0] -- at most once each RESONANT_RING[2] s an enemy."""
    damage, radius, gap = config.RESONANT_RING
    rung = victim.__dict__.setdefault("rung", {})
    if owner.time - rung.get(id(owner), -math.inf) < gap - 1e-9:
        return
    rung[id(owner)] = owner.time
    radius *= owner.stats.area_scale
    effects.append(Effect("pulse", victim.x, victim.y, size=radius))
    for a in list(actors):
        if a.alive and a.hittable and _may_hurt(owner, a) \
                and math.hypot(a.x - victim.x, a.y - victim.y) <= radius + a.hit_radius:
            strike(a, damage, owner, math.atan2(a.y - victim.y, a.x - victim.x), effects, tags,
                   on_hit=False)


def _resonance(victim: Actor, owner, actors=()) -> float:
    """Resonance (a card): each earlier dart of this hero on the same enemy
    within the last RESONANCE[0] s adds to this one (bucket A), up to
    RESONANCE[2] darts' worth. Humming Staff +3 (Sustain): a longer
    window; +9 (Perfect pitch): more darts counted; (L) Harmonics: the
    count goes on from the freshest one on any enemy within HARMONICS tiles
    of this one."""
    window, per, most = config.RESONANCE
    stats = owner.stats
    if stats.has("resonance+3"):
        window = config.SUSTAIN
    if stats.has("resonance+9"):
        most = config.PERFECT_PITCH
    now = getattr(owner, "time", 0.0)
    marks = getattr(victim, "resonance", None)
    if marks is None:
        marks = victim.resonance = {}
    last, count = marks.get(id(owner), (-math.inf, -1))
    if stats.has("resonance+L"):
        for a in actors:
            m = getattr(a, "resonance", None)
            if a is victim or not m or id(owner) not in m or not a.alive \
                    or math.hypot(a.x - victim.x, a.y - victim.y) > config.HARMONICS:
                continue
            t, n = m[id(owner)]
            if now - t <= window and (now - last > window or n > count):
                last, count = t, n
    count = min(most, count + 1) if now - last <= window else 0
    marks[id(owner)] = (now, count)
    return per * count


def _dart_hit(p: Projectile, victim: Actor, hx: float, hy: float, owner, stats, world,
              actors, effects: list[Effect], spawned: list | None, zones: list | None = None,
              shots: list | None = None) -> None:
    """The wizard's dart cards, once a dart has hit: Implosion (P4: enemies
    round the hit are dragged toward it; bosses and things that never move
    stay put, see push) and Arcane Storm (a kill sends a new dart at the
    next enemy, ARCANE_STORM[0] per cast). And the main hand's tricks
    (M28.2g): Conducting darts, Crush, Event horizon, Singularity, Squall,
    Tempest, Maelstrom."""
    seconds, share = config.CONDUCTING
    if stats.has("storm_caller+3") \
            and owner.time - getattr(victim, "bolted", {}).get(id(owner), -math.inf) <= seconds:
        _conduct(p, victim, owner, stats, world, actors, effects, share)
    if stats.has("implosion"):
        radius, pull = config.IMPLOSION
        effects.append(Effect("implode", hx, hy, size=radius))
        # Gravewell Staff (L), Gather: toward where you aim instead.
        aim = getattr(owner, "aim_point", None) if stats.has("implosion+L") else None
        cx, cy = aim if aim is not None else (hx, hy)
        dragged = []
        for a in actors:
            if not a.hittable or not _may_hurt(owner, a):
                continue
            d = math.hypot(a.x - hx, a.y - hy)
            to = math.hypot(a.x - cx, a.y - cy)
            if d <= radius + a.hit_radius and 0.3 < to:
                step = min(pull, to - 0.3)      # (never past the middle)
                x0, y0 = a.x, a.y
                push(a, world, (cx - a.x) / to * step, (cy - a.y) / to * step)
                if (a.x, a.y) != (x0, y0):
                    dragged.append(a)
        if dragged and stats.has("implosion+3"):
            _crush(dragged, victim, owner, effects, p.tags)
        if shots is not None and stats.has("implosion+6"):
            _event_horizon(shots, hx, hy, pull)
        if p.group is not None and p.group.get("well") and zones is not None:
            from .zones import Zone                 # Singularity (+9)
            p.group["well"] = False
            _, life, speed = config.SINGULARITY
            zones.append(Zone("well", hx, hy, radius, life, 999.0, 0.0, owner, pull=speed))
    if stats.has("ball_lightning+L") and zones is not None:
        _crackle(zones, victim, p.damage, owner, p.tags, hx, hy, dart=True)   # (Static darts)
    if stats.has("phase_darts+L") and not victim.alive:
        victim.possessor = owner                    # (Ghostwood Staff (L): Possession)
    if stats.has("arcane_storm+L") and p.group is not None:
        # Stormheart Staff (L), Storm's mark: whatever kills it in the next
        # STORMS_MARK s, it fires a new dart (storm_dart from the game's
        # deaths). A dart's own kill is Arcane Storm's, just below.
        victim.storm_mark = (p, owner.time) if victim.alive else None
    if stats.has("arcane_storm") and not victim.alive and spawned is not None \
            and p.group is not None:
        storm_dart(p, victim, hx, hy, owner, stats, actors, spawned)


def storm_dart(p: Projectile, victim: Actor, hx: float, hy: float, owner, stats, actors,
               spawned: list) -> None:
    """Arcane Storm: a new dart from where `victim` died at the next enemy,
    ARCANE_STORM[0] per cast (the cast's darts share p.group)."""
    most, reach = config.ARCANE_STORM
    if stats.has("arcane_storm+6"):
        most = config.STORM_TEMPEST                 # (Tempest)
    maelstrom = stats.has("arcane_storm+9")
    if not maelstrom and p.group.get("storm", 0) >= most:
        return
    t = None
    if stats.has("arcane_storm+3"):                 # Squall: the one nearest you
        t = _nearest_foe(owner.x, owner.y, reach, actors, owner, skip=victim)
    if t is None:
        t = _nearest_foe(hx, hy, reach, actors, owner, skip=victim)
    if t is None:
        return
    p.group["storm"] = p.group.get("storm", 0) + 1
    c = _child(p, hx, hy, math.atan2(t.y - hy, t.x - hx),
               config.MAELSTROM if maelstrom else 1.0)
    c.group = p.group
    c.seek = t
    c.max_range = p.spec.max_range
    c.travelled = 0.0
    spawned.append(c)


def _conduct(p: Projectile, victim: Actor, owner, stats, world, actors,
             effects: list[Effect], share: float) -> None:
    """Stormcaller Rod +3 (Conducting darts): the dart's hit jumps on once,
    as Chain Lightning's jumps do (their reach, clear line unless +6)."""
    reach = config.SPELL_SHELLS["chain"].chain_range * (1 + stats.chain_range)
    walls = not stats.has("storm_caller+6")
    best, best_d = None, math.inf
    for a in actors:
        if a is victim or not a.hittable or not _may_hurt(owner, a):
            continue
        d = math.hypot(a.x - victim.x, a.y - victim.y)
        if d <= reach and d < best_d and \
                (not walls or first_hit(world.tile_at, victim.x, victim.y, a.x, a.y) is None):
            best, best_d = a, d
    if best is None:
        return
    effects.append(Effect("arc", victim.x, victim.y, x2=best.x, y2=best.y))
    strike(best, p.damage * share, owner, math.atan2(best.y - victim.y, best.x - victim.x),
           effects, config.SPELLS["chain_lightning"].tags, mult=p.mult)


def _crush(dragged: list, victim: Actor, owner, effects: list[Effect], tags) -> None:
    """Gravewell Staff +3 (Crush): enemies dragged into another body (each
    other, or the one the dart hit) take CRUSH, each once."""
    bodies = dragged + ([victim] if victim.alive and victim not in dragged else [])
    crushed = []
    for a in dragged:
        for b in bodies:
            if b is not a and math.hypot(a.x - b.x, a.y - b.y) < a.hit_radius + b.hit_radius:
                crushed += [x for x in (a, b) if x not in crushed]
    for a in crushed:
        if a.alive:
            strike(a, config.CRUSH, owner, None, effects, tags, on_hit=False)


def _event_horizon(shots: list, x: float, y: float, pull: float) -> None:
    """Gravewell Staff +6 (Event horizon): enemy shots near the hit are
    dragged toward it too (not lobbed ones: they're up in the air)."""
    for q in shots:
        if not q.alive or q.spec.lob or q.owner is None \
                or getattr(q.owner, "faction", None) == "player":
            continue
        d = math.hypot(q.x - x, q.y - y)
        if 0 < d <= config.EVENT_HORIZON:
            step = min(pull, d)
            q.x += (x - q.x) / d * step
            q.y += (y - q.y) / d * step


def _split_arrow(p: Projectile, victim: Actor | None, hx: float, hy: float, stats,
                 spawned: list, actors=(), zones: list | None = None,
                 angle: float | None = None) -> None:
    """Split Arrow (the huntress's power): on its first hit (on every
    enemy it passes, from level IV) an arrow throws off a fan of `count`
    arrows at `damage` x its own, centred on its flight, that fly the rest
    of its range. They don't split again. The Splitbranch Bow: +3 (Canopy)
    they go for the nearest enemies instead; +6 (Bough) on walls too
    (`victim` None, the fan centred on `angle`); +9 (Seed storm) seeds."""
    count, spread_deg, factor, every = stats.arrow_split
    if p.child or (p.hit and not every):
        return
    centre = p.angle if angle is None else angle
    spread = math.radians(spread_deg)
    angles = [centre + (spread * (i / (count - 1) - 0.5) if count > 1 else 0.0)
              for i in range(count)]
    reach = max(1.0, p.max_range - p.travelled)
    if stats.has("split_arrow+3"):                    # Canopy: the nearest enemies
        near = sorted((a for a in actors if a is not victim and a.hittable
                       and _may_hurt(p.owner, a)
                       and math.hypot(a.x - hx, a.y - hy) <= reach),
                      key=lambda a: math.hypot(a.x - hx, a.y - hy))
        for i, a in enumerate(near[:count]):
            angles[i] = math.atan2(a.y - hy, a.x - hx)
    recurve = stats.has("split_arrow+L") and not p.summon
    for a in angles:
        c = _child(p, hx, hy, a, factor)
        if victim is not None:
            c.hit.add(id(victim))
        c.max_range = reach
        c.recurve = recurve                           # (Splitbranch Bow (L): Recurve)
        spawned.append(c)
    if zones is not None and stats.has("split_arrow+9"):
        from .zones import Zone                        # Seed storm
        n, life, radius, dps, throw = config.SEED_STORM
        tick = 0.5
        for k in range(n):                          # (evenly round, so they don't overlap)
            a = centre + k * math.tau / n
            zones.append(Zone("thorns", hx + math.cos(a) * throw, hy + math.sin(a) * throw,
                              radius, life, tick, dps * tick, p.owner, p.tags))


def _split_on_wall(p: Projectile, x: float, y: float, hit: RayHit, spawned: list, actors,
                   zones) -> None:
    """Splitbranch Bow +6 (Bough): an arrow splits on the wall that stops
    it too, the fan turned off the wall."""
    stats = _stats_of(p)
    if stats is None or p.summon or p.spec.returns or not stats.arrow_split \
            or not stats.has("split_arrow+6"):
        return
    _split_arrow(p, None, x, y, stats, spawned, actors, zones, angle=_reflected(p, hit))


def _turn_back(p: Projectile, spawned: list | None = None) -> None:
    """A boomerang at the end of its throw: everything may be hit again.
    Splitting Axe (P4): it comes home as two halves instead."""
    p.returning = True
    p.out_hit = set(p.hit)                  # (Dust devil: who it hit on the way out)
    p.hit.clear()
    stats = _stats_of(p)
    if stats is not None and not p.summon and stats.has("homeward_fury+L"):
        p.steer = p.max_range               # (Homesick Axe (L): Steered, this far at most)
    if (stats is not None and stats.has("splitting_axe") and not p.halved and not p.summon
            and spawned is not None):
        _split_axe(p, spawned)


def _split_axe(p: Projectile, spawned: list) -> None:
    """Splitting Axe: two halves (SPLITTING_AXE[0] of the damage each)
    start SPLITTING_AXE[1] tiles apart across the way home and both home on
    the dwarf, so they come back either side of the axe's path and meet in
    his hand. The first half may still Cyclone; neither splits again.
    Doublebit Axe: +3 (Reunite) pieces that meet merge (_reunite); +6
    (Crossing) they start CROSSING apart and aim at the far side first,
    crossing over half way, then home; +9 (Quartering) four quarters.
    (L) Wide arc: each swings out WIDE_ARC tiles to its side (the far side
    with Crossing) half way home, then home."""
    share, gap = config.SPLITTING_AXE
    stats = _stats_of(p)
    n = 2
    if stats.has("splitting_axe+9"):
        n, share = config.QUARTERING
    cross = stats.has("splitting_axe+6")
    if cross:
        gap = config.CROSSING
    wide = stats.has("splitting_axe+L")
    owner = p.owner
    home = math.atan2(owner.y - p.y, owner.x - p.x) if owner is not None else p.angle + math.pi
    far = math.hypot(owner.x - p.x, owner.y - p.y) if owner is not None else 0.0
    nx, ny = -math.sin(home), math.cos(home)
    pieces: list | None = [] if stats.has("splitting_axe+3") else None
    for k in range(n):
        side = k / (n - 1) - 0.5
        c = _child(p, p.x + nx * side * gap, p.y + ny * side * gap, home, share)
        c.returning = True
        c.hit = set()
        c.travelled = p.travelled
        c.max_range = p.max_range
        c.bounces = p.bounces
        c.halved = True
        c.child = k != 0
        c.pieces = pieces
        if pieces is not None:
            pieces.append(c)
        if wide and owner is not None:     # (Wide arc: out to its side, half way home)
            out = side * 2 * config.WIDE_ARC * (-1 if cross else 1)
            c.arc_to = ((p.x + owner.x) / 2 + nx * out, (p.y + owner.y) / 2 + ny * out)
        elif cross and owner is not None:
            c.cross = (-nx * side * gap, -ny * side * gap, far / 4)
        spawned.append(c)
    p.alive = False


def _hang(p: Projectile) -> bool:
    """Hang Time (P4): where its throw ends -- at full range, or at a wall
    it doesn't Ricochet off -- an axe hovers HANG_TIME[0] s, + HANG_TIME[1]
    per copy past the first, before it turns home (once per throw).
    Returns whether it hangs."""
    stats = _stats_of(p)
    if p.hung or p.summon or stats is None or stats.hang_time <= 0:
        return False
    first, per, every = config.HANG_TIME
    p.hang = first + per * (round(stats.hang_time) - 1)
    p.hung = True
    p.hang_tick = every              # (what it hit arriving isn't hit again at once)
    return True


def _hover(p: Projectile, grid: ActorGrid, world, effects: list[Effect], dt: float,
           actors: list[Actor], spawned: list | None, zones: list | None) -> list[str]:
    """A hanging axe spins where it is; every HANG_TIME[2] s everything it
    touches is hit again. Then it turns home (and may split)."""
    p.hang -= dt
    p.spin += p.spec.speed * dt          # (drawing: it keeps spinning)
    p.hang_tick -= dt
    events: list[str] = []
    stats = _stats_of(p)
    if stats is not None and stats.has("hang_time+L") and not p.summon:
        _drift_saw(p, actors, world, dt)            # (Hoverhead Axe (L): Drifting saw)
    if p.hang_tick <= 0:
        p.hang_tick += config.HANG_TIME[2]
        p.hit.clear()
        reach = p.size + 0.4
        if stats is not None and stats.has("hang_time+9"):
            reach = config.BUZZSAW                  # Hoverhead Axe +9 (Buzzsaw)
        for _, a in grid.near(p.x - reach, p.y - reach, p.x + reach, p.y + reach):
            if not a.hittable or id(a) in p.hit or not _may_hurt(p.owner, a):
                continue
            if math.hypot(a.x - p.x, a.y - p.y) <= a.hit_radius + reach:
                p.hit.add(id(a))
                events += _hit_actor(p, a, p.x, p.y, world, actors, effects, spawned, zones)
    if p.hang <= 0 and stats is not None and stats.has("hang_time+6") \
            and getattr(p.owner, "trigger", False) and p.held < config.HOLD_IT:
        p.held += dt                                # Hoverhead +6 (Hold it there)
        p.hang = 1e-9
    if p.hang <= 0:
        p.hang = 0.0
        _turn_back(p, spawned)
    return events


def _drift_saw(p: Projectile, actors, world, dt: float) -> None:
    """Hoverhead Axe (L), Drifting saw: the hovering axe drifts after the
    nearest enemy within the axe's reach, DRIFTING_SAW tiles a second, up
    to its body. Walls stop it."""
    t = _nearest_foe(p.x, p.y, p.spec.max_range, actors, p.owner)
    if t is None:
        return
    d = math.hypot(t.x - p.x, t.y - p.y)
    step = min(config.DRIFTING_SAW * dt, max(0.0, d - t.hit_radius))
    if step <= 0:
        return
    nx, ny = p.x + (t.x - p.x) / d * step, p.y + (t.y - p.y) / d * step
    if world is not None and first_hit(world.tile_at, p.x, p.y, nx, ny) is not None:
        return
    p.x, p.y = nx, ny


def _chain_gang(projectiles: list[Projectile], actors, effects: list[Effect], dt: float) -> None:
    """Chainlink Axe (L), Chain gang: a chain between every two of a
    dwarf's axes in flight cuts all it crosses, as the Tether's chain does
    (every TETHER[0] s, TETHER[2] x the smaller axe's damage)."""
    every, width, share = config.TETHER
    gangs: dict[int, list[Projectile]] = {}
    for p in projectiles:
        stats = _stats_of(p)
        if p.alive and p.spec.returns and not p.summon and stats is not None \
                and stats.has("tether+L") and p.owner.alive:
            gangs.setdefault(id(p.owner), []).append(p)
    for axes in gangs.values():
        owner = axes[0].owner
        owner.gang_t -= dt
        if owner.gang_t > 0:
            continue
        owner.gang_t += every
        if owner.gang_t <= 0:
            owner.gang_t = every
        for i, a in enumerate(axes):
            for b in axes[i + 1:]:
                _cut_along(a.x, a.y, b.x, b.y, width, min(a.damage, b.damage) * share, owner,
                           actors, effects, a.tags, max(a.mult, b.mult))


def chain_links(projectiles) -> list[tuple]:
    """Chain gang's chains to draw: (axe, axe) for every two of one
    dwarf's axes in flight."""
    gangs: dict[int, list[Projectile]] = {}
    for p in projectiles:
        stats = _stats_of(p)
        if p.alive and p.spec.returns and not p.summon and stats is not None \
                and stats.has("tether+L"):
            gangs.setdefault(id(p.owner), []).append(p)
    return [(a, b) for axes in gangs.values() for i, a in enumerate(axes) for b in axes[i + 1:]]


def _cut_along(x0: float, y0: float, x1: float, y1: float, width: float, damage: float, owner,
               actors, effects: list[Effect], tags, mult: float) -> None:
    """Everything within `width` tiles of the line (x0, y0)-(x1, y1) takes
    `damage` (no on-hit cards: a chain, not an axe)."""
    dx, dy = x1 - x0, y1 - y0
    length2 = dx * dx + dy * dy
    if length2 < 1e-6:
        return
    angle = math.atan2(dy, dx)
    for a in actors:
        if not a.hittable or not _may_hurt(owner, a):
            continue
        t = max(0.0, min(1.0, ((a.x - x0) * dx + (a.y - y0) * dy) / length2))
        if math.hypot(a.x - (x0 + dx * t), a.y - (y0 + dy * t)) <= width + a.hit_radius:
            strike(a, damage, owner, angle, effects, tags, mult=mult, on_hit=False)


def _tether(p: Projectile, actors: list[Actor], effects: list[Effect], dt: float,
            world=None) -> None:
    """Tether (P4): every TETHER[0] s, everything within TETHER[1] tiles of
    the chain -- the line from the dwarf to this axe -- takes TETHER[2] x
    the axe's damage (no on-hit cards: it's the chain, not the axe).
    Chainlink Axe +3 (Taut): more with the axe near full range; +6
    (Shackle): the first enemy it cuts each throw is dragged with the axe."""
    owner = p.owner
    stats = _stats_of(p)
    if stats is None or p.summon or not stats.has("tether") or owner is None \
            or not owner.alive:
        return
    if p.shackle is not None:
        e, until, (lx, ly) = p.shackle
        if e.alive and owner.time < until and world is not None:
            push(e, world, p.x - lx, p.y - ly)
            p.shackle = (e, until, (p.x, p.y))
        else:
            p.shackle = None
    p.tether_t -= dt
    if p.tether_t > 0:
        return
    every, width, share = config.TETHER
    p.tether_t += every
    x0, y0 = owner.x, owner.y
    dx, dy = p.x - x0, p.y - y0
    length2 = dx * dx + dy * dy
    if length2 < 1e-6:
        return
    angle = math.atan2(dy, dx)
    far, taut = config.TAUT
    if stats.has("tether+3") and math.sqrt(length2) >= p.max_range * far:
        share = taut                                # (Taut)
    for a in actors:
        if not a.hittable or not _may_hurt(owner, a):
            continue
        t = max(0.0, min(1.0, ((a.x - x0) * dx + (a.y - y0) * dy) / length2))
        if math.hypot(a.x - (x0 + dx * t), a.y - (y0 + dy * t)) <= width + a.hit_radius:
            strike(a, p.damage * share, owner, angle, effects, p.tags, mult=p.mult,
                   on_hit=False)
            if not p.shackled and stats.has("tether+6"):   # (Shackle)
                p.shackled = True
                p.shackle = (a, owner.time + config.SHACKLE, (p.x, p.y))


def _fly_back(p: Projectile, grid: ActorGrid, world, effects: list[Effect], dt: float,
              actors: list[Actor], spawned: list | None = None,
              zones: list | None = None) -> list[str]:
    """A boomerang flying home: it homes on the thrower wherever they've
    gone, over walls (it never gets stuck), still hitting enemies on the
    way, and is caught within RETURN_CATCH_RADIUS. It drops if the thrower
    died or it's flown RETURN_GIVE_UP x its range in all. Quick Catch flies
    it home faster and catches it from farther; Cyclone throws a caught
    axe straight back out."""
    owner = p.owner
    if (owner is None or not owner.alive
            or p.travelled > p.max_range * config.RETURN_GIVE_UP):
        effects.append(Effect("fizzle", p.x, p.y))
        p.alive = False
        return [FIZZLE]
    stats = getattr(owner, "stats", None)
    quick = stats.return_speed if stats is not None else 0.0
    tx, ty = owner.x, owner.y
    if not p.leapt:
        p.leapt = True
        if stats is not None and not p.summon and not p.halved and stats.has("cyclone+L"):
            # The nearest it didn't just hit on the way out, if there is one.
            p.devil = _nearest_foe(p.x, p.y, config.DUST_DEVIL, actors, owner,
                                   skip_ids=p.out_hit) \
                or _nearest_foe(p.x, p.y, config.DUST_DEVIL, actors, owner)
    if p.devil is not None:                     # (Whirlwind Axe (L): Dust devil)
        if p.devil.alive and p.devil.hittable and id(p.devil) not in p.hit:
            tx, ty = p.devil.x, p.devil.y
        else:
            p.devil = None
    if p.cross is not None:                     # (Doublebit Axe +6: Crossing)
        ox, oy, until = p.cross
        if math.hypot(owner.x - p.x, owner.y - p.y) > until:
            tx, ty = owner.x + ox, owner.y + oy
        else:
            p.cross = None
    if p.arc_to is not None:                    # (Doublebit Axe (L): Wide arc)
        if math.hypot(p.arc_to[0] - p.x, p.arc_to[1] - p.y) > config.STEERED:
            tx, ty = p.arc_to
        else:
            p.arc_to = None
    aim = getattr(owner, "aim_point", None)
    if p.steer is not None:                     # (Homesick Axe (L): Steered)
        if aim is None or p.steer <= 0 or math.hypot(aim[0] - p.x, aim[1] - p.y) <= config.STEERED:
            p.steer = None
        elif (tx, ty) == (owner.x, owner.y):
            tx, ty = aim
            p.steer -= p.spec.speed * (1 + quick) * dt
    bend = _bend_home(p, owner, actors) if stats is not None and not p.summon \
        and stats.has("homeward_fury+3") else None
    if bend is not None:                        # (Homesick Axe +3: Homing)
        tx, ty = bend.x, bend.y
    to_x, to_y = tx - p.x, ty - p.y
    dist = math.hypot(to_x, to_y)
    step = p.spec.speed * (1 + quick) * dt
    if dist > 0:
        p.dir_x, p.dir_y = to_x / dist, to_y / dist
        p.angle = math.atan2(to_y, to_x)
    home = (tx, ty) == (owner.x, owner.y)
    caught = home and dist - step <= config.RETURN_CATCH_RADIUS * (1 + 2 * quick)
    if home:
        step = min(step, dist)
    dx, dy = p.dir_x * step, p.dir_y * step
    events: list[str] = []
    while True:     # every enemy along this step (each only once per leg)
        t, victim = _first_actor(grid, p, dx, dy, math.inf)
        if victim is None:
            break
        p.hit.add(id(victim))
        events += _hit_actor(p, victim, p.x + dx * t, p.y + dy * t, world, actors, effects,
                             spawned, zones)
    p.x += dx
    p.y += dy
    p.travelled += step
    if caught:
        p.alive = False
        if stats is not None and not p.summon and stats.has("homeward_fury+6"):
            _, seconds, most = config.WELCOME_HOME          # (Homesick Axe +6)
            owner.welcome = (owner.welcome + [seconds])[-most:]
        if stats is not None and stats.has("cyclone") and spawned is not None:
            most = config.GALE_FORCE if stats.has("cyclone+6") else 1
            if (not p.child or p.spins > 0) and p.spins < most:
                _cyclone(p, owner, actors, spawned, stats)
    return events


def _bend_home(p: Projectile, owner, actors):
    """Homesick Axe +3 (Homing): the enemy (not hit yet this leg) the axe
    bends for on its way home: within HOMING_BACK tiles of its line to
    the thrower, the first along it."""
    x0, y0 = p.x, p.y
    dx, dy = owner.x - x0, owner.y - y0
    length2 = dx * dx + dy * dy
    if length2 < 1e-6:
        return None
    best, best_t = None, math.inf
    for a in actors:
        if not a.hittable or id(a) in p.hit or not _may_hurt(owner, a):
            continue
        t = ((a.x - x0) * dx + (a.y - y0) * dy) / length2
        if 0.0 < t < 1.0 and t < best_t and math.hypot(a.x - (x0 + dx * t), a.y - (y0 + dy * t)) \
                <= config.HOMING_BACK + a.hit_radius:
            best, best_t = a, t
    return best


def _cyclone(p: Projectile, owner: Actor, actors: list[Actor], spawned: list, stats=None) -> None:
    """Cyclone (a card): the caught axe flies straight back out at the
    nearest enemy in reach (once per throw). Whirlwind Axe +3 (Spin
    cycle): at the one with the most HP; +6 (Gale force): a rethrown axe
    may go again; +9 (Eye of the cyclone): a second axe at the next one."""
    has = stats.has if stats is not None else (lambda flag: False)
    reach = p.spec.max_range
    near = [a for a in actors if a.hittable and _may_hurt(owner, a)
            and math.hypot(a.x - owner.x, a.y - owner.y) < reach]
    if has("cyclone+3"):
        near.sort(key=lambda a: -a.hp)
    else:
        near.sort(key=lambda a: math.hypot(a.x - owner.x, a.y - owner.y))
    for i, best in enumerate(near[:2 if has("cyclone+9") else 1]):
        c = _child(p, owner.x, owner.y, math.atan2(best.y - owner.y, best.x - owner.x), 1.0)
        c.max_range = p.spec.max_range
        c.hit = set()
        c.spins = p.spins + 1 if i == 0 else 99    # (the second axe doesn't go again)
        spawned.append(c)


def _fly_lobbed(p: Projectile, world, effects: list[Effect], dt: float,
                actors: list[Actor]) -> list[str]:
    """A lobbed shell: up and over (nothing stops it), bursting when it
    comes down at its target."""
    step = min(p.spec.speed * dt * p.time_scale, p.flight - p.travelled)
    p.x += p.dir_x * step
    p.y += p.dir_y * step
    p.travelled += step
    if p.travelled < p.flight - 1e-9:
        return []
    p.alive = False
    if p.spec.look == "rain_arrow":                  # (P4: Arrow Rain)
        effects.append(Effect("impact", p.x, p.y, p.angle))
        hit = False
        for a in actors:
            if a.hittable and _may_hurt(p.owner, a) \
                    and math.hypot(a.x - p.x, a.y - p.y) <= p.spec.blast_radius + a.hit_radius:
                strike(a, p.damage, p.owner, p.angle, effects, p.tags, mult=p.mult)
                hit = True
        return [HIT] if hit else []
    return burst(p.x, p.y, p.spec.blast_radius, p.damage, p.owner, actors, world, effects,
                 p.spec.damages_terrain)


def burst(x: float, y: float, radius: float, damage: float, source: Actor | None,
          actors: list[Actor], world, effects: list[Effect], damages_terrain: bool) -> list[str]:
    """An explosion: hurts every actor its circle touches (friendly fire:
    the thrower's friends too, but not the thrower) and, if allowed, every
    destructible tile inside it."""
    effects.append(Effect("explosion", x, y))
    blast(x, y, radius, damage, source, actors, effects=effects)
    events = [BREAK]
    if damages_terrain:
        for ty in range(math.floor(y - radius), math.floor(y + radius) + 1):
            for tx in range(math.floor(x - radius), math.floor(x + radius) + 1):
                if math.hypot(tx + 0.5 - x, ty + 0.5 - y) > radius:
                    continue
                if world.damage_tile(tx, ty, damage) is Damage.DESTROYED:
                    effects.append(Effect("debris", tx + 0.5, ty + 0.5))
    return events


def blast(
    x: float, y: float, radius: float, damage: float, source: Actor | None,
    actors: list[Actor], hurt_source: bool = False, effects: list[Effect] | None = None,
    ground: bool = False,
) -> list[Actor]:
    """Damage every hittable actor whose body touches a circle of `radius`
    around (x, y) -- spore clouds, a burrower bursting up, a sword swing.
    Returns the actors hit. Friendly fire applies. Pass `effects` to get
    damage numbers. `ground`: it comes out of the ground (a hero skimming
    over it, Wingheel Sandals +9, is missed)."""
    hit = []
    for a in actors:
        if not a.hittable or (a is source and not hurt_source):
            continue
        if ground and skims(a):
            continue
        if math.hypot(a.x - x, a.y - y) <= radius + a.hit_radius:
            dealt = a.take_damage(damage * (ground_cut(a) if ground else 1.0), source, None)
            if effects is not None:
                _number(effects, a, dealt)
            hit.append(a)
    return hit


def crush_tile(world, tx: int, ty: int, amount: float, effects: list[Effect]) -> str | None:
    """Ogres smashing through terrain. Returns a sound event if the
    tile broke."""
    if world.damage_tile(tx, ty, amount) is Damage.DESTROYED:
        effects.append(Effect("debris", tx + 0.5, ty + 0.5))
        return BREAK
    return None


def _terrain_impact(
    world, hit: RayHit, damage: float, damages_terrain: bool, angle: float,
    effects: list[Effect],
) -> str:
    """A shot hitting a tile: sparks, and damage if the shot is allowed to
    hurt terrain (only the player's bolts and ogres' rocks are)."""
    # Pull the spark back a hair so it sits on the tile's face, not inside.
    back = 0.05
    ex, ey = hit.x - math.cos(angle) * back, hit.y - math.sin(angle) * back
    effects.append(Effect("impact", ex, ey, angle))
    if not damages_terrain:
        return THUD
    result = world.damage_tile(hit.tx, hit.ty, damage)
    if result is Damage.DESTROYED:
        effects.append(Effect("debris", hit.tx + 0.5, hit.ty + 0.5))
        return BREAK
    effects.append(Effect("tile_flash", hit.tx, hit.ty))
    return HIT
