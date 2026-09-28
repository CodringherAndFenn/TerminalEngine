"""
systems/combat.py -- firing, shell flight, hits on actors and terrain, blasts.

Aiming math: the shell starts at the barrel tip and flies along the turret's
true world angle. The tip is barrel_length_px out along the turret's
*on-screen* direction; converting that pixel offset back to tiles
(dx / TILE_PX_W, dy / TILE_PX_H) lands exactly on the world ray from the
tank center at the turret angle, because the screen angle was derived from
the world angle with the same per-axis scale. So the shell passes through
the exact world point under the reticle.

Hits: each frame a shell's movement is a segment. Terrain along it is found
by walking the tiles it crosses (systems/raycast.py); actors by
segment-vs-circle intersection. Whichever comes first along the segment is
hit. Friendly fire is on: any actor except the shooter can be hit.
"""

from __future__ import annotations

import math

from .. import config
from ..entities.actor import Actor
from ..entities.effects import Effect
from ..entities.projectile import Projectile
from ..entities.tank import Tank
from ..world.tiles import Damage
from .collision import screen_angle
from .raycast import RayHit, first_hit

# Sound events returned to the scene (it owns the audio).
SHOT, HIT, BREAK, FIZZLE, THUD = "shot", "hit", "break", "fizzle", "thud"


def muzzle_point(tank: Tank) -> tuple[float, float]:
    """World position of the barrel tip."""
    s = screen_angle(tank.turret_angle)
    length = tank.spec.barrel_length_px
    return (
        tank.x + math.cos(s) * length / config.TILE_PX_W,
        tank.y + math.sin(s) * length / config.TILE_PX_H,
    )


def fire(
    tank: Tank, world, projectiles: list[Projectile], effects: list[Effect],
    angle: float | None = None, damage: float | None = None,
) -> list[str]:
    """Fire the tank's weapon along its turret (or `angle`, for aim error).
    Returns sound events."""
    mx, my = muzzle_point(tank)
    angle = tank.turret_angle if angle is None else angle
    effects.append(Effect("muzzle", mx, my, angle))
    shell = tank.weapon.spec.shell
    dmg = shell.damage if damage is None else damage
    # If the barrel is poking into (or through) a wall, the shot lands there
    # instead of spawning on the far side.
    hit = first_hit(world.tile_at, tank.x, tank.y, mx, my)
    if hit is not None:
        return [SHOT, _terrain_impact(world, hit, dmg, shell.damages_terrain, angle, effects)]
    projectiles.append(Projectile(mx, my, angle, shell, owner=tank, damage=dmg))
    return [SHOT]


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


def update_projectiles(
    projectiles: list[Projectile], world, effects: list[Effect], dt: float,
    actors: list[Actor] = (),
) -> list[str]:
    """Move every shell and resolve hits and range. Returns sound events."""
    events: list[str] = []
    for p in projectiles:
        step = p.spec.speed * dt
        remaining = p.spec.max_range - p.travelled
        last_leg = step >= remaining
        if last_leg:
            step = remaining
        dx, dy = p.dir_x * step, p.dir_y * step

        tile_hit = first_hit(world.tile_at, p.x, p.y, p.x + dx, p.y + dy)
        best_t = tile_hit.t if tile_hit is not None else math.inf
        victim = None
        for a in actors:
            if a is p.owner or not a.hittable:
                continue
            t = segment_circle_t(p.x, p.y, dx, dy, a.x, a.y, a.hit_radius)
            if t is not None and t < best_t:
                best_t, victim = t, a

        if victim is not None:
            hx, hy = p.x + dx * best_t, p.y + dy * best_t
            victim.take_damage(p.damage, p.owner, p.angle)
            effects.append(Effect("impact", hx, hy, p.angle))
            events.append(HIT)
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
    actors: list[Actor], hurt_source: bool = False,
) -> list[Actor]:
    """Damage every hittable actor whose body touches a circle of `radius`
    around (x, y) -- spore clouds, a burrower bursting up, a sword swing.
    Returns the actors hit. Friendly fire applies."""
    hit = []
    for a in actors:
        if not a.hittable or (a is source and not hurt_source):
            continue
        if math.hypot(a.x - x, a.y - y) <= radius + a.hit_radius:
            a.take_damage(damage, source, None)
            hit.append(a)
    return hit


def crush_tile(world, tx: int, ty: int, amount: float, effects: list[Effect]) -> str | None:
    """Heavy tanks grinding through terrain. Returns a sound event if the
    tile broke."""
    if world.damage_tile(tx, ty, amount) is Damage.DESTROYED:
        effects.append(Effect("debris", tx + 0.5, ty + 0.5))
        return BREAK
    return None


def _terrain_impact(
    world, hit: RayHit, damage: float, damages_terrain: bool, angle: float,
    effects: list[Effect],
) -> str:
    """A shell hitting a tile: sparks, and damage if the shell is allowed to
    hurt terrain (only the player's and heavy tanks' shells are)."""
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
