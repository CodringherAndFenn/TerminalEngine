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
from ..entities.character import Character
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
    spread_add: float = 0.0, reach_mult: float = 1.0,
) -> list[str]:
    """Use the shooter's weapon, whatever its kind (see specs.WeaponSpec).
    The keywords are one attack's changes (cards that work every Nth
    attack, see scenes/game.py _attack_mods): x damage, + lightning jumps,
    + projectiles over + degrees of fan, x pulse reach. Returns sound
    events."""
    kind = shooter.weapon.spec.kind
    if kind == "melee":
        return swing(shooter, world, actors, effects, mult)
    if kind == "pulse":
        return pulse(shooter, world, actors, effects, mult, reach_mult)
    return fire(shooter, world, projectiles, effects, mult=mult, extra_chain=extra_chain,
                extra_pellets=extra_pellets, spread_add=spread_add)


# --- Hero damage ---------------------------------------------------------------------


def strike(victim: Actor, base: float, source: Actor | None, angle: float | None,
           effects: list[Effect], tags=(), extra: float = 0.0, mult: float = 1.0,
           on_hit: bool = True, can_crit: bool = True) -> float:
    """One hit of `base` damage on `victim`. From a hero (an actor with
    `stats`) it goes through the damage buckets and may crit and apply the
    hero's on-hit statuses; from anyone else it's plain damage. `extra`
    adds to bucket A (conditionals), `mult` is a per-hit "xN". Summons'
    hits pass on_hit / can_crit False (unless Pack Leader). Returns the
    damage dealt; whether it crit is left in source.last_crit."""
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
    crit = can_crit and source.rng.random() < crit_chance(stats, source)
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
    extra_pellets: int = 0, spread_add: float = 0.0,
) -> list[str]:
    """Fire the shooter's weapon along its aim (or `angle`, for aim error).
    A weapon with several pellets fans them evenly over its spread, the
    middle of the fan on the aim. Returns sound events."""
    mx, my = shot_origin(shooter)
    angle = shooter.aim_angle if angle is None else angle
    effects.append(Effect("muzzle", mx, my, angle))
    spec = shooter.weapon.spec
    shell = spec.shell
    dmg = shell.damage if damage is None else damage
    if shell.lob:
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
    # Standing against a wall: the shot lands on it instead of spawning on
    # the far side.
    hit = first_hit(world.tile_at, shooter.x, shooter.y, mx, my)
    if hit is not None:
        return [shell.sound, _terrain_impact(world, hit, outgoing(shooter, dmg, spec.tags) * mult,
                                             shell.damages_terrain, angle, effects)]
    n = max(1, spec.pellets + extra_pellets)
    spread = math.radians(spec.spread_deg + spread_add)
    stats = getattr(shooter, "stats", None)
    size = stats.shot_size * config.SHOT_SIZE_PX / config.TILE_PX_W if stats is not None else 0.0
    group: dict = {}                  # Prism: which colors of this shot hit whom
    for i in range(n):
        a = angle + (spread * (i / (n - 1) - 0.5) if n > 1 else 0.0)
        p = Projectile(mx, my, a, shell, owner=shooter, damage=dmg)
        p.variant = i
        p.tags = spec.tags
        p.mult = mult
        p.extra_chain = extra_chain
        p.size = size
        p.group = group
        projectiles.append(p)
    return [shell.sound]


def _may_hurt(source: Actor | None, target: Actor) -> bool:
    """Friendly fire is on -- except between players: heroes never hurt
    each other (co-op). Nothing hurts its own source."""
    if target is source:
        return False
    return not (source is not None and source.faction == "player" and target.faction == "player")


def _aim_offset(shooter: Character, x: float, y: float) -> float:
    """Angle between the shooter's aim and the direction to (x, y), measured
    on screen (so a swing's arc looks as wide as it is)."""
    to = screen_angle(math.atan2(y - shooter.y, x - shooter.x))
    diff = to - screen_angle(shooter.aim_angle)
    return abs((diff + math.pi) % math.tau - math.pi)


def swing(shooter: Character, world, actors: list[Actor], effects: list[Effect],
          mult: float = 1.0) -> list[str]:
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
        strike(a, spec.damage, shooter, shooter.aim_angle, effects, spec.tags, mult=mult)
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
          mult: float = 1.0, reach_mult: float = 1.0) -> list[str]:
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
        strike(a, spec.damage, shooter, angle, effects, spec.tags, extra=extra, mult=mult)
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
        if p.returning:
            events += _fly_back(p, grid, world, effects, dt, actors, spawned, zones)
            continue
        step = p.spec.speed * dt
        remaining = p.max_range - p.travelled
        last_leg = step >= remaining
        if last_leg:
            step = remaining
        dx, dy = p.dir_x * step, p.dir_y * step

        tile_hit = first_hit(world.tile_at, p.x, p.y, p.x + dx, p.y + dy)
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
                if not _ricochet(p, tile_hit):
                    _turn_back(p)
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
                _turn_back(p)
                continue
            effects.append(Effect("fizzle", p.x, p.y))
            events.append(FIZZLE)
            p.alive = False
    projectiles[:] = [p for p in projectiles if p.alive] + spawned
    return events


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
    full = not p.summon or (stats is not None and stats.has("pack_leader"))
    strike(victim, p.damage, owner, p.angle, effects, p.tags, extra=extra, mult=p.mult,
           on_hit=full, can_crit=full)
    effects.append(Effect("impact", hx, hy, p.angle))
    if p.inflicts is not None and victim.alive:
        inflict(victim, p.inflicts[0], owner, p.inflicts[1])
    if stats is not None and not p.summon:
        if victim.alive:
            _card_effects(p, victim, owner, stats)
        _capstones(p, victim, hx, hy, owner, stats, spawned, zones)
    events = [HIT]
    if p.spec.chain or p.extra_chain:
        events += chain_from(victim, p.spec, p.damage, owner, world, actors, effects, p.tags,
                             p.extra_chain, p.mult)
    return events


def _card_effects(p: Projectile, victim: Actor, owner: Actor, stats) -> None:
    """Hero cards that make a shot's hit inflict a status."""
    if stats.has("supercell") and p.spec.chain:
        inflict(victim, "shock", owner)              # the wizard's bolts shock
    if stats.has("cleave") and p.spec.returns:
        inflict(victim, "bleed", owner)              # the dwarf's axes bleed
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


def _turn_back(p: Projectile) -> None:
    """A boomerang at the end of its throw: everything may be hit again."""
    p.returning = True
    p.hit.clear()


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
    step = min(p.spec.speed * dt, p.flight - p.travelled)
    p.x += p.dir_x * step
    p.y += p.dir_y * step
    p.travelled += step
    if p.travelled < p.flight - 1e-9:
        return []
    p.alive = False
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
