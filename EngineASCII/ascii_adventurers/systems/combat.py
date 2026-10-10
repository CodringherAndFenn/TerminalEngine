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

from .. import config
from ..entities.actor import Actor
from ..entities.effects import Effect
from ..entities.projectile import Projectile
from ..entities.character import Character, wrap_angle
from ..specs import CharacterSpec
from ..world.tiles import Damage
from .collision import move_hull, screen_angle
from .raycast import RayHit, first_hit
from .statuses import inflict, roll_on_hit

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
                sure_crit=sure_crit)


# --- Hero damage ---------------------------------------------------------------------


def strike(victim: Actor, base: float, source: Actor | None, angle: float | None,
           effects: list[Effect], tags=(), extra: float = 0.0, mult: float = 1.0,
           on_hit: bool = True, can_crit: bool = True, sure_crit: bool = False) -> float:
    """One hit of `base` damage on `victim`. From a hero (an actor with
    `stats`) it goes through the damage buckets and may crit and apply the
    hero's on-hit statuses; from anyone else it's plain damage. `extra`
    adds to bucket A (conditionals), `mult` is a per-hit "xN". Summons'
    hits pass on_hit / can_crit False (unless Pack Leader); `sure_crit`
    makes a hit that may crit always crit (Riposte). Returns the
    damage dealt; whether it crit is left in source.last_crit."""
    if getattr(source, "shrunk", 0) > 0:              # tiny (Nettle's dust, M25.1)
        mult *= config.SHRINK[2]
    stats = getattr(source, "stats", None)
    if stats is None:
        dealt = victim.take_damage(base * mult, source, angle)
        _number(effects, victim, dealt)
        return dealt
    a = stats.damage + extra + situational_bonus(stats, source, victim)
    m = stats.damage_mult * mult
    if victim is getattr(source, "marked", None):
        m *= config.MARK_MULT
    st = victim.status
    if stats.has("shatter") and st is not None and st.frozen > 0:
        m *= config.SHATTER[0]
    crit = can_crit and (sure_crit or source.rng.random() < crit_chance(stats, source))
    source.last_crit = crit
    amount = base * (1 + a) * (1 + stats.tag_bonus(tags)) * m
    if crit:
        amount *= stats.crit_damage
    dealt = victim.take_damage(amount, source, angle)
    _number(effects, victim, dealt, "crit" if crit else "")
    if on_hit and dealt > 0 and stats.statuses:
        roll_on_hit(victim, source, stats)
    return dealt


def situational_bonus(stats, source: Actor, victim: Actor) -> float:
    """Bucket A from the cards that depend on the moment (catalog 6.5,
    Point Blank, Wildfire, Golden Hoard, Juggernaut, the bestiary)."""
    a = 0.0
    if stats.point_blank and math.hypot(victim.x - source.x, victim.y - source.y) \
            <= config.POINT_BLANK_RANGE:
        a += stats.point_blank
    hp = source.hp / source.max_hp if source.max_hp else 0.0
    if stats.untouched and hp >= config.UNTOUCHED_HP:
        a += stats.untouched
    flags = stats.flags
    if flags:
        if "berserker" in flags:
            a += max(0.0, 1 - hp)
        if "bulwark" in flags:
            a += source.max_hp / 10 * 0.01
        if "momentum" in flags:
            a += max(0.0, stats.move) / 2
        if "bloodlust" in flags:
            a += len(getattr(source, "bloodlust", ())) * 0.01
        if "giant_slayer" in flags and victim.max_hp > source.max_hp:
            a += config.GIANT_SLAYER
        if "veteran" in flags:
            a += getattr(source, "level", 1) * 0.01
        if "golden_hoard" in flags:
            per, cap = config.GOLDEN_HOARD
            a += min(cap, getattr(source, "run_loot", 0.0) / per * 0.01)
        if "juggernaut" in flags:
            a += max(0.0, stats.armor) * config.JUGGERNAUT
    if stats.wildfire and victim.status is not None and victim.status.has("burn"):
        a += stats.wildfire
    kind = getattr(victim, "kind_key", None)
    if kind is not None and kind in getattr(source, "bestiary", ()):
        a += config.BESTIARY_BONUS
    return a


def crit_chance(stats, source: Actor) -> float:
    chance = stats.crit_chance
    if stats.steady_crit and source.speed < config.STEADY_SPEED:
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


def push(actor: Actor, world, dx: float, dy: float) -> None:
    """Shove an actor (tiles), stopping at walls. Things that never move
    (towers, spitters) and bosses stay put."""
    if getattr(actor, "half", None) is None or getattr(actor, "boss", False):
        return
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
    return volley(shooter, world, projectiles, effects, angle, n, spec.spread_deg + spread_add,
                  shell, spec.tags, dmg, mult=mult, extra_chain=extra_chain, sure_crit=sure_crit)


def volley(shooter: Character, world, projectiles: list[Projectile], effects: list[Effect],
           angle: float, n: int, spread_deg: float, shell, tags=(), damage: float | None = None,
           mult: float = 1.0, extra_chain: int = 0, sure_crit: bool = False,
           hold: float = 0.0, origin: tuple[float, float] | None = None) -> list[str]:
    """`n` shots of `shell` fanned evenly over `spread_deg` around `angle`,
    from the shooter's hand (or `origin`). The weapon's own fire and the
    pattern cards (systems/run_rules.patterns) both come through here.
    Twin Lanes (a card) turns each shot into two side by side; Converge
    (P4) bends the princess's fan to cross at the aim point. `hold`: the
    shots wait this long before flying."""
    mx, my = origin if origin is not None else shot_origin(shooter)
    effects.append(Effect("muzzle", mx, my, angle))
    dmg = shell.damage if damage is None else damage
    # Standing against a wall: the shot lands on it instead of spawning on
    # the far side.
    hit = first_hit(world.tile_at, shooter.x, shooter.y, mx, my)
    if hit is not None:
        return [shell.sound, _terrain_impact(world, hit, outgoing(shooter, dmg, tags) * mult,
                                             shell.damages_terrain, angle, effects)]
    spread = math.radians(spread_deg)
    stats = getattr(shooter, "stats", None)
    size = stats.shot_size * config.SHOT_SIZE_PX / config.TILE_PX_W if stats is not None else 0.0
    lanes = (0.0,)
    lane_mult = 1.0
    if stats is not None and stats.has("twin_lanes"):
        gap, lane_mult = config.TWIN_LANES
        lanes = (-gap / 2, gap / 2)
    group: dict = {}                  # Prism: which colors of this shot hit whom
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
    for i in range(n):
        a = angle + (spread * (i / (n - 1) - 0.5) if n > 1 else 0.0)
        for side in lanes:
            # Lanes sit side by side, across the shot's own heading.
            ox, oy = -math.sin(a) * side, math.cos(a) * side
            p = Projectile(mx + ox, my + oy, a, shell, owner=shooter, damage=dmg)
            p.variant = i
            p.tags = tags
            p.mult = mult * lane_mult
            p.extra_chain = extra_chain
            p.sure_crit = sure_crit
            p.size = size
            p.group = group
            p.hold = hold
            p.seek_point = seek_point
            if meet is not None:
                _converge(p, wrap_angle(a - angle), meet)
            projectiles.append(p)
    return [shell.sound]


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
          mult: float = 1.0, reach_mult: float = 1.0, sure_crit: bool = False) -> list[str]:
    """A burst all around: everything within `reach` tiles that isn't
    behind a wall is hit, and destructible terrain in reach is worn down at
    PULSE_TERRAIN_FACTOR of the damage. Cards: Dissonance (each one hit is
    pushed back and chilled), Crescendo (beats in a row that hit grow
    stronger), Lullaby (heal per enemy hit)."""
    spec = shooter.weapon.spec
    reach = spec.reach * reach_mult
    effects.append(Effect("pulse", shooter.x, shooter.y, size=reach))
    events = ["pulse"]
    stats = getattr(shooter, "stats", None)
    dissonance = stats is not None and stats.has("dissonance")
    crescendo = stats is not None and stats.has("crescendo")
    extra = config.CRESCENDO_STEP * getattr(shooter, "streak", 0) if crescendo else 0.0
    hits = 0
    for a in actors:
        if not a.hittable or not _may_hurt(shooter, a):
            continue
        if math.hypot(a.x - shooter.x, a.y - shooter.y) > reach + a.hit_radius:
            continue
        if first_hit(world.tile_at, shooter.x, shooter.y, a.x, a.y) is not None:
            continue
        angle = math.atan2(a.y - shooter.y, a.x - shooter.x)
        strike(a, spec.damage, shooter, angle, effects, spec.tags, extra=extra, mult=mult,
               sure_crit=sure_crit)
        hits += 1
        if dissonance and a.alive:
            inflict(a, "chill", shooter)
            push(a, world, math.cos(angle) * config.DISSONANCE_PUSH,
                 math.sin(angle) * config.DISSONANCE_PUSH)
        events.append(HIT)
    # Walls, trees...: every destructible tile in reach whose way from the
    # shooter isn't blocked by another tile, at a fraction of the damage.
    if crescendo:
        shooter.streak = min(config.CRESCENDO_MAX, shooter.streak + 1) if hits else 0
    if hits and stats is not None and stats.has("lullaby"):
        per, most = config.LULLABY_HEAL
        shooter.heal(per * min(most, hits))
    wear = outgoing(shooter, spec.damage, spec.tags) * mult * config.PULSE_TERRAIN_FACTOR
    if wear > 0:
        r = reach
        for ty in range(math.floor(shooter.y - r), math.floor(shooter.y + r) + 1):
            for tx in range(math.floor(shooter.x - r), math.floor(shooter.x + r) + 1):
                cx, cy = tx + 0.5, ty + 0.5
                if math.hypot(cx - shooter.x, cy - shooter.y) > r:
                    continue
                if not world.tile_at(tx, ty).destructible:
                    continue
                block = first_hit(world.tile_at, shooter.x, shooter.y, cx, cy)
                if block is not None and (block.tx, block.ty) != (tx, ty):
                    continue                   # hidden behind another tile
                result = world.damage_tile(tx, ty, wear)
                if result is Damage.DESTROYED:
                    effects.append(Effect("debris", cx, cy))
                    events.append(BREAK)
                elif result is Damage.DAMAGED:
                    effects.append(Effect("tile_flash", tx, ty))
    return events


def chain_from(first: Actor, shell, damage: float, source: Actor | None, world,
               actors: list[Actor], effects: list[Effect], tags=(), extra_jumps: int = 0,
               mult: float = 1.0) -> list[str]:
    """Lightning jumping on from `first` (already hit) to up to shell.chain
    (+ extra_jumps) more enemies: each jump goes to the nearest one within
    chain_range with a clear line, not hit yet, for chain_falloff of the
    previous damage. Supercell (a card): shocked enemies in range are
    picked first, and take SUPERCELL_BONUS more."""
    stats = getattr(source, "stats", None)
    supercell = stats is not None and stats.has("supercell")
    events = []
    current, hit = first, {id(first)}
    for _ in range(shell.chain + extra_jumps):
        damage *= shell.chain_falloff
        best, best_key = None, None
        for a in actors:
            if id(a) in hit or not a.hittable or not _may_hurt(source, a):
                continue
            d = math.hypot(a.x - current.x, a.y - current.y)
            if d > shell.chain_range:
                continue
            key = (not (supercell and _shocked(a)), d)
            if (best_key is None or key < best_key) \
                    and first_hit(world.tile_at, current.x, current.y, a.x, a.y) is None:
                best, best_key = a, key
        if best is None:
            break
        effects.append(Effect("arc", current.x, current.y, x2=best.x, y2=best.y))
        angle = math.atan2(best.y - current.y, best.x - current.x)
        extra = config.SUPERCELL_BONUS if supercell and _shocked(best) else 0.0
        strike(best, damage, source, angle, effects, tags, extra=extra, mult=mult)
        if supercell and best.alive:
            inflict(best, "shock", source)
        hit.add(id(best))
        current = best
        events.append("zap")
    return events


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
            events += _fly_lobbed(p, world, effects, dt, actors)
            continue
        if p.spec.returns:
            _tether(p, actors, effects, dt)
        if p.hang > 0:
            events += _hover(p, grid, world, effects, dt, actors, spawned, zones)
            continue
        if p.returning:
            events += _fly_back(p, grid, world, effects, dt, actors, spawned, zones)
            continue
        if p.hold > 0:                    # waiting to fly (harmless until then)
            p.hold -= dt
            continue
        if p.spec.wobble:
            _weave(p)
        if p.seek_turn > 0:
            _home(p, actors, dt)
        step = p.spec.speed * dt * p.time_scale
        if p.curve:
            _bend(p, step)
        remaining = p.max_range - p.travelled
        last_leg = step >= remaining
        if last_leg:
            step = remaining
        dx, dy = p.dir_x * step, p.dir_y * step

        tile_hit = first_hit(world.tile_at, p.x, p.y, p.x + dx, p.y + dy)
        if tile_hit is not None and p.seek_turn > 0 and _phases(p):
            tile_hit = None                   # Phase Darts: through walls and trees
        best_t = tile_hit.t if tile_hit is not None else math.inf
        best_t, victim = _first_actor(grid, p, dx, dy, best_t)

        if victim is not None:
            hx, hy = p.x + dx * best_t, p.y + dy * best_t
            events += _hit_actor(p, victim, hx, hy, world, actors, effects, spawned, zones)
            if p.spec.returns or p.pierce_left > 0:
                # Through it: carry on from the hit point next step (the
                # rest of this step's distance is dropped -- a fraction of
                # a tile). Boomerangs pass through everything.
                if not p.spec.returns:
                    p.pierce_left -= 1
                p.hit.add(id(victim))
                p.x, p.y = hx, hy
                p.travelled += step * best_t
                continue
            p.alive = False
            continue
        if tile_hit is not None:
            events.append(_terrain_impact(
                world, tile_hit, outgoing(p.owner, p.damage, p.tags) * p.mult,
                p.spec.damages_terrain, p.angle, effects
            ))
            if p.spec.returns:
                # Bounces off the wall: on (Ricochet) or home.
                p.travelled += step * tile_hit.t
                p.x = tile_hit.x - p.dir_x * 0.05
                p.y = tile_hit.y - p.dir_y * 0.05
                if not _ricochet(p, tile_hit) and not _hang(p):
                    _turn_back(p, spawned)
                continue
            p.alive = False
            continue
        p.x += dx
        p.y += dy
        p.travelled += step
        if _split(p, spawned):
            continue
        if last_leg:
            if p.spec.returns:
                if not _hang(p):
                    _turn_back(p, spawned)
                continue
            if _orbit_again(p, actors):
                continue
            effects.append(Effect("fizzle", p.x, p.y))
            events.append(FIZZLE)
            p.alive = False
    projectiles[:] = [p for p in projectiles if p.alive] + spawned
    return events


def _nearest_foe(x: float, y: float, radius: float, actors, owner, skip=None):
    """The hittable actor `owner` may hurt nearest (x, y), within `radius`
    (plus its body), or None."""
    best, best_d = None, math.inf
    for a in actors:
        if a is skip or not a.hittable or not _may_hurt(owner, a):
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
        else:
            p.seek = t = False
    if t is None:
        cx, cy = p.seek_point if p.seek_point is not None else (p.x, p.y)
        t = p.seek = _nearest_foe(cx, cy, p.spec.seek_radius, actors, p.owner) or False
    if t is False:
        return
    want = math.atan2(t.y - p.y, t.x - p.x)
    turn = wrap_angle(want - p.angle)
    most = p.seek_turn * dt
    p.angle += max(-most, min(most, turn))
    p.dir_x, p.dir_y = math.cos(p.angle), math.sin(p.angle)


def _orbit_again(p: Projectile, actors) -> bool:
    """Orbiting Darts (a card): a dart that reaches the end of its flight
    without hitting anything swings round toward the enemy nearest its
    owner (within ORBIT_REACH) and gets its range again -- enough to reach
    that enemy at least -- once."""
    stats = _stats_of(p)
    if p.seek_turn <= 0 or p.orbits or p.hit or stats is None \
            or not stats.has("orbiting_darts") or p.owner is None:
        return False
    t = _nearest_foe(p.owner.x, p.owner.y, config.ORBIT_REACH, actors, p.owner)
    if t is None:
        return False
    p.orbits += 1
    p.seek = t
    p.travelled = 0.0
    # Enough to turn round (half a circle at its turn rate) and reach it.
    turning = math.pi * p.spec.speed / p.seek_turn
    p.max_range = max(p.max_range, math.hypot(t.x - p.x, t.y - p.y) + turning + 2.0)
    return True


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
    c.max_range = p.max_range
    c.hit = set(p.hit)
    c.pierce_left = p.pierce_left
    return c


def _ricochet(p: Projectile, hit: RayHit) -> bool:
    """Ricochet (a card): an axe glances off the wall it hit and flies on,
    RICOCHET_BOUNCES times per throw. The face it hit is the one the
    entry point is closest to; the motion across that face flips."""
    stats = _stats_of(p)
    if stats is None or not stats.has("ricochet") or p.bounces >= config.RICOCHET_BOUNCES:
        return False
    fx, fy = hit.x - hit.tx, hit.y - hit.ty
    if min(fx, 1 - fx) < min(fy, 1 - fy):
        p.dir_x = -p.dir_x
    else:
        p.dir_y = -p.dir_y
    p.angle = math.atan2(p.dir_y, p.dir_x)
    p.bounces += 1
    p.hit.clear()
    return True


def _split(p: Projectile, spawned: list[Projectile]) -> bool:
    """Spray and Pray (a card): half way along its range a shot splits in
    two, each SPLIT_DAMAGE of it, SPLIT_SPREAD degrees apart."""
    stats = _stats_of(p)
    if stats is None or not stats.has("split") or p.child or p.spec.returns \
            or p.travelled < p.max_range / 2:
        return False
    half = math.radians(config.SPLIT_SPREAD) / 2
    for side in (-1, 1):
        spawned.append(_child(p, p.x, p.y, p.angle + side * half, config.SPLIT_DAMAGE))
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
               zones: list | None = None) -> list[str]:
    owner = p.owner
    stats = getattr(owner, "stats", None)
    extra = 0.0
    if stats is not None:
        # Broadhead: more damage for every enemy this arrow has already passed.
        extra += stats.broadhead * len(p.hit)
        if p.returning:
            extra += stats.homeward                # Homeward Fury / Homecoming
        if stats.prism and p.group is not None:    # Prism: colors on one enemy
            seen = p.group.get(id(victim), 0)
            extra += stats.prism * seen
            p.group[id(victim)] = seen + 1
    dart = p.spec.seek_turn > 0 and stats is not None and not p.summon
    if dart and stats.has("resonance"):
        extra += _resonance(victim, owner)
    full = not p.summon or (stats is not None and stats.has("pack_leader"))
    dealt = strike(victim, p.damage, owner, p.angle, effects, p.tags, extra=extra, mult=p.mult,
                   on_hit=full, can_crit=full, sure_crit=p.sure_crit)
    hook = getattr(owner, "on_shot_hit", None)      # (M24.1: the Fallout King's rads)
    if hook is not None and dealt:
        hook(victim, dealt)
    if dart:
        _dart_hit(p, victim, hx, hy, owner, stats, world, actors, effects, spawned)
    effects.append(Effect("impact", hx, hy, p.angle))
    if p.inflicts is not None and victim.alive:
        inflict(victim, p.inflicts[0], owner, p.inflicts[1])
    if stats is not None and not p.summon:
        if victim.alive:
            _card_effects(p, victim, owner, stats)
        _capstones(p, victim, hx, hy, owner, stats, spawned, zones)
        if stats.arrow_split and spawned is not None:
            _split_arrow(p, victim, hx, hy, stats, spawned)
    events = [HIT]
    if p.spec.chain or p.extra_chain:
        events += chain_from(victim, p.spec, p.damage, owner, world, actors, effects, p.tags,
                             p.extra_chain, p.mult)
    return events


def _card_effects(p: Projectile, victim: Actor, owner: Actor, stats) -> None:
    """Hero cards that make a shot's hit inflict a status."""
    if stats.has("supercell") and p.spec.chain:
        inflict(victim, "shock", owner)              # the wizard's bolts shock
    if stats.has("spectrum") and p.spec.look == "prism":
        name = config.SPECTRUM_STATUS[p.variant % len(config.SPECTRUM_STATUS)]
        if name is not None and owner.rng.random() < config.SPECTRUM_CHANCE:
            inflict(victim, name, owner)


def _capstones(p: Projectile, victim: Actor, hx: float, hy: float, owner: Actor, stats,
               spawned, zones) -> None:
    """Capstone cards that change what a shot does once it hits."""
    if stats.has("deadeye") and getattr(owner, "last_crit", False):
        p.pierce_left = 10 ** 6                      # Deadeye: through everything...
        p.max_range = max(p.max_range, p.spec.max_range * 2)   # ...and twice as far
    if stats.has("refraction") and p.spec.look == "prism" and not p.child \
            and spawned is not None:
        n, spread = config.REFRACTION_SPLIT, math.radians(config.REFRACTION_SPREAD)
        for i in range(n):
            a = p.angle + spread * (i / (n - 1) - 0.5)
            c = _child(p, hx, hy, a, config.REFRACTION_DAMAGE)
            c.hit.add(id(victim))
            c.max_range = max(1.0, p.max_range - p.travelled)
            spawned.append(c)
    if stats.has("ball_lightning") and p.spec.chain and zones is not None:
        from .zones import Zone
        zones.append(Zone("crackle", hx, hy, config.BALL_LIGHTNING_RADIUS,
                          config.BALL_LIGHTNING_TIME, config.BALL_LIGHTNING_EVERY,
                          p.damage * config.BALL_LIGHTNING_DAMAGE, owner, p.tags))


def _resonance(victim: Actor, owner) -> float:
    """Resonance (a card): each earlier dart of this hero on the same enemy
    within the last RESONANCE[0] s adds to this one (bucket A), up to
    RESONANCE[2] darts' worth."""
    window, per, most = config.RESONANCE
    now = getattr(owner, "time", 0.0)
    marks = getattr(victim, "resonance", None)
    if marks is None:
        marks = victim.resonance = {}
    last, count = marks.get(id(owner), (-math.inf, -1))
    count = min(most, count + 1) if now - last <= window else 0
    marks[id(owner)] = (now, count)
    return per * count


def _dart_hit(p: Projectile, victim: Actor, hx: float, hy: float, owner, stats, world,
              actors, effects: list[Effect], spawned: list | None) -> None:
    """The wizard's dart cards, once a dart has hit: Implosion (P4: enemies
    round the hit are dragged toward it; bosses and things that never move
    stay put, see push) and Arcane Storm (a kill sends a new dart at the
    next enemy, ARCANE_STORM[0] per cast)."""
    if stats.has("implosion"):
        radius, pull = config.IMPLOSION
        effects.append(Effect("implode", hx, hy, size=radius))
        for a in actors:
            if not a.hittable or not _may_hurt(owner, a):
                continue
            d = math.hypot(a.x - hx, a.y - hy)
            if 0.3 < d <= radius + a.hit_radius:
                step = min(pull, d - 0.3)       # (never past the middle)
                push(a, world, (hx - a.x) / d * step, (hy - a.y) / d * step)
    if stats.has("arcane_storm") and not victim.alive and spawned is not None \
            and p.group is not None:
        most, reach = config.ARCANE_STORM
        if p.group.get("storm", 0) >= most:
            return
        t = _nearest_foe(hx, hy, reach, actors, owner, skip=victim)
        if t is None:
            return
        p.group["storm"] = p.group.get("storm", 0) + 1
        c = _child(p, hx, hy, math.atan2(t.y - hy, t.x - hx), 1.0)
        c.group = p.group
        c.seek = t
        c.max_range = p.spec.max_range
        c.travelled = 0.0
        spawned.append(c)


def _split_arrow(p: Projectile, victim: Actor, hx: float, hy: float, stats,
                 spawned: list) -> None:
    """Split Arrow (the huntress's power): on its first hit (on every
    enemy it passes, from level IV) an arrow throws off a fan of `count`
    arrows at `damage` x its own, centred on its flight, that fly the rest
    of its range. They don't split again."""
    count, spread_deg, factor, every = stats.arrow_split
    if p.child or (p.hit and not every):
        return
    spread = math.radians(spread_deg)
    for i in range(count):
        a = p.angle + (spread * (i / (count - 1) - 0.5) if count > 1 else 0.0)
        c = _child(p, hx, hy, a, factor)
        c.hit.add(id(victim))
        c.max_range = max(1.0, p.max_range - p.travelled)
        spawned.append(c)


def _turn_back(p: Projectile, spawned: list | None = None) -> None:
    """A boomerang at the end of its throw: everything may be hit again.
    Splitting Axe (P4): it comes home as two halves instead."""
    p.returning = True
    p.hit.clear()
    stats = _stats_of(p)
    if (stats is not None and stats.has("splitting_axe") and not p.halved and not p.summon
            and spawned is not None):
        _split_axe(p, spawned)


def _split_axe(p: Projectile, spawned: list) -> None:
    """Splitting Axe: two halves (SPLITTING_AXE[0] of the damage each)
    start SPLITTING_AXE[1] tiles apart across the way home and both home on
    the dwarf, so they come back either side of the axe's path and meet in
    his hand. The first half may still Cyclone; neither splits again."""
    share, gap = config.SPLITTING_AXE
    owner = p.owner
    home = math.atan2(owner.y - p.y, owner.x - p.x) if owner is not None else p.angle + math.pi
    nx, ny = -math.sin(home), math.cos(home)
    for k, side in enumerate((-0.5, 0.5)):
        c = _child(p, p.x + nx * side * gap, p.y + ny * side * gap, home, share)
        c.returning = True
        c.hit = set()
        c.travelled = p.travelled
        c.max_range = p.max_range
        c.bounces = p.bounces
        c.halved = True
        c.child = k == 1
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
    if p.hang_tick <= 0:
        p.hang_tick += config.HANG_TIME[2]
        p.hit.clear()
        reach = p.size + 0.4
        for _, a in grid.near(p.x - reach, p.y - reach, p.x + reach, p.y + reach):
            if not a.hittable or id(a) in p.hit or not _may_hurt(p.owner, a):
                continue
            if math.hypot(a.x - p.x, a.y - p.y) <= a.hit_radius + reach:
                p.hit.add(id(a))
                events += _hit_actor(p, a, p.x, p.y, world, actors, effects, spawned, zones)
    if p.hang <= 0:
        p.hang = 0.0
        _turn_back(p, spawned)
    return events


def _tether(p: Projectile, actors: list[Actor], effects: list[Effect], dt: float) -> None:
    """Tether (P4): every TETHER[0] s, everything within TETHER[1] tiles of
    the chain -- the line from the dwarf to this axe -- takes TETHER[2] x
    the axe's damage (no on-hit cards: it's the chain, not the axe)."""
    owner = p.owner
    stats = _stats_of(p)
    if stats is None or p.summon or not stats.has("tether") or owner is None \
            or not owner.alive:
        return
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
    for a in actors:
        if not a.hittable or not _may_hurt(owner, a):
            continue
        t = max(0.0, min(1.0, ((a.x - x0) * dx + (a.y - y0) * dy) / length2))
        if math.hypot(a.x - (x0 + dx * t), a.y - (y0 + dy * t)) <= width + a.hit_radius:
            strike(a, p.damage * share, owner, angle, effects, p.tags, mult=p.mult,
                   on_hit=False)


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
    to_x, to_y = owner.x - p.x, owner.y - p.y
    dist = math.hypot(to_x, to_y)
    step = p.spec.speed * (1 + quick) * dt
    if dist > 0:
        p.dir_x, p.dir_y = to_x / dist, to_y / dist
        p.angle = math.atan2(to_y, to_x)
    caught = dist - step <= config.RETURN_CATCH_RADIUS * (1 + 2 * quick)
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
        if stats is not None and stats.has("cyclone") and not p.child and spawned is not None:
            _cyclone(p, owner, actors, spawned)
    return events


def _cyclone(p: Projectile, owner: Actor, actors: list[Actor], spawned: list) -> None:
    """Cyclone (a card): the caught axe flies straight back out at the
    nearest enemy in reach (once per throw)."""
    best, best_d = None, p.spec.max_range
    for a in actors:
        if a.hittable and _may_hurt(owner, a):
            d = math.hypot(a.x - owner.x, a.y - owner.y)
            if d < best_d:
                best, best_d = a, d
    if best is None:
        return
    c = _child(p, owner.x, owner.y, math.atan2(best.y - owner.y, best.x - owner.x), 1.0)
    c.max_range = p.spec.max_range
    c.hit = set()
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
) -> list[Actor]:
    """Damage every hittable actor whose body touches a circle of `radius`
    around (x, y) -- spore clouds, a burrower bursting up, a sword swing.
    Returns the actors hit. Friendly fire applies. Pass `effects` to get
    damage numbers."""
    hit = []
    for a in actors:
        if not a.hittable or (a is source and not hurt_source):
            continue
        if math.hypot(a.x - x, a.y - y) <= radius + a.hit_radius:
            dealt = a.take_damage(damage, source, None)
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
