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
enemy to enemy), melee swings over an arc, and pulses all around.
attack() picks the right one.
"""

from __future__ import annotations

import math

from .. import config
from ..entities.actor import Actor
from ..entities.effects import Effect
from ..entities.projectile import Projectile
from ..entities.character import Character
from ..world.tiles import Damage
from .collision import screen_angle
from .raycast import RayHit, first_hit

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
    actors: list[Actor] = (),
) -> list[str]:
    """Use the shooter's weapon, whatever its kind (see specs.WeaponSpec).
    Returns sound events."""
    kind = shooter.weapon.spec.kind
    if kind == "melee":
        return swing(shooter, world, actors, effects)
    if kind == "pulse":
        return pulse(shooter, world, actors, effects)
    return fire(shooter, world, projectiles, effects)


def fire(
    shooter: Character, world, projectiles: list[Projectile], effects: list[Effect],
    angle: float | None = None, damage: float | None = None,
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
    # Standing against a wall: the shot lands on it instead of spawning on
    # the far side.
    hit = first_hit(world.tile_at, shooter.x, shooter.y, mx, my)
    if hit is not None:
        return [shell.sound, _terrain_impact(world, hit, dmg, shell.damages_terrain, angle, effects)]
    n = max(1, spec.pellets)
    spread = math.radians(spec.spread_deg)
    for i in range(n):
        a = angle + (spread * (i / (n - 1) - 0.5) if n > 1 else 0.0)
        p = Projectile(mx, my, a, shell, owner=shooter, damage=dmg)
        p.variant = i
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


def swing(shooter: Character, world, actors: list[Actor], effects: list[Effect]) -> list[str]:
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
        dealt = a.take_damage(spec.damage, shooter, shooter.aim_angle)
        _number(effects, a, dealt)
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
            result = world.damage_tile(tx, ty, spec.damage)
            if result is Damage.DESTROYED:
                effects.append(Effect("debris", cx, cy))
                events.append(BREAK)
            elif result is Damage.DAMAGED:
                effects.append(Effect("tile_flash", tx, ty))
    return events


def pulse(shooter: Character, world, actors: list[Actor], effects: list[Effect]) -> list[str]:
    """A burst all around: everything within `reach` tiles that isn't
    behind a wall is hit."""
    spec = shooter.weapon.spec
    effects.append(Effect("pulse", shooter.x, shooter.y, size=spec.reach))
    events = ["pulse"]
    for a in actors:
        if not a.hittable or not _may_hurt(shooter, a):
            continue
        if math.hypot(a.x - shooter.x, a.y - shooter.y) > spec.reach + a.hit_radius:
            continue
        if first_hit(world.tile_at, shooter.x, shooter.y, a.x, a.y) is not None:
            continue
        angle = math.atan2(a.y - shooter.y, a.x - shooter.x)
        dealt = a.take_damage(spec.damage, shooter, angle)
        _number(effects, a, dealt)
        events.append(HIT)
    return events


def chain_from(first: Actor, shell, damage: float, source: Actor | None, world,
               actors: list[Actor], effects: list[Effect]) -> list[str]:
    """Lightning jumping on from `first` (already hit) to up to shell.chain
    more enemies: each jump goes to the nearest one within chain_range with
    a clear line, not hit yet, for chain_falloff of the previous damage."""
    events = []
    current, hit = first, {id(first)}
    for _ in range(shell.chain):
        damage *= shell.chain_falloff
        best, best_d = None, shell.chain_range
        for a in actors:
            if id(a) in hit or not a.hittable or not _may_hurt(source, a):
                continue
            d = math.hypot(a.x - current.x, a.y - current.y)
            if d <= best_d and first_hit(world.tile_at, current.x, current.y, a.x, a.y) is None:
                best, best_d = a, d
        if best is None:
            break
        effects.append(Effect("arc", current.x, current.y, x2=best.x, y2=best.y))
        angle = math.atan2(best.y - current.y, best.x - current.x)
        _number(effects, best, best.take_damage(damage, source, angle))
        hit.add(id(best))
        current = best
        events.append("zap")
    return events


def _number(effects: list[Effect], victim: Actor, dealt: float) -> None:
    """A floating damage number over whoever got hurt."""
    if dealt > 0:
        effects.append(Effect("number", victim.x, victim.y - victim.hit_radius, 0.0,
                              value=max(1, round(dealt)), player=victim.faction == "player"))


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
    actors: list[Actor] = (),
) -> list[str]:
    """Move every shell and resolve hits and range. Returns sound events."""
    events: list[str] = []
    grid = ActorGrid(actors)
    for p in projectiles:
        step = p.spec.speed * dt
        remaining = p.spec.max_range - p.travelled
        last_leg = step >= remaining
        if last_leg:
            step = remaining
        dx, dy = p.dir_x * step, p.dir_y * step

        tile_hit = first_hit(world.tile_at, p.x, p.y, p.x + dx, p.y + dy)
        best_t = tile_hit.t if tile_hit is not None else math.inf
        victim, victim_i = None, -1
        for i, a in grid.near(p.x, p.y, p.x + dx, p.y + dy):
            if not a.hittable or id(a) in p.hit or not _may_hurt(p.owner, a):
                continue
            t = segment_circle_t(p.x, p.y, dx, dy, a.x, a.y, a.hit_radius)
            # Ties go to the actor earliest in `actors`, as a plain scan would.
            if t is not None and (t < best_t or (t == best_t and victim is not None and i < victim_i)):
                best_t, victim, victim_i = t, a, i

        if victim is not None:
            hx, hy = p.x + dx * best_t, p.y + dy * best_t
            dealt = victim.take_damage(p.damage, p.owner, p.angle)
            effects.append(Effect("impact", hx, hy, p.angle))
            _number(effects, victim, dealt)
            events.append(HIT)
            if p.spec.chain:
                events += chain_from(victim, p.spec, p.damage, p.owner, world, actors, effects)
            if p.pierce_left > 0:
                # Through it: carry on from the hit point next step (the
                # rest of this step's distance is dropped -- a fraction of
                # a tile).
                p.pierce_left -= 1
                p.hit.add(id(victim))
                p.x, p.y = hx, hy
                p.travelled += step * best_t
                continue
            p.alive = False
            continue
        if tile_hit is not None:
            events.append(_terrain_impact(
                world, tile_hit, p.damage, p.spec.damages_terrain, p.angle, effects
            ))
            p.alive = False
            continue
        p.x += dx
        p.y += dy
        p.travelled += step
        if last_leg:
            effects.append(Effect("fizzle", p.x, p.y))
            events.append(FIZZLE)
            p.alive = False
    projectiles[:] = [p for p in projectiles if p.alive]
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
