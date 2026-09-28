"""
systems/combat.py -- firing, shell flight, and hitting terrain.

Aiming math: the shell starts at the barrel tip and flies along the turret's
true world angle. The tip is BARREL_LENGTH_PX out along the turret's
*on-screen* direction; converting that pixel offset back to tiles
(dx / TILE_PX_W, dy / TILE_PX_H) lands exactly on the world ray from the
tank center at the turret angle, because the screen angle was derived from
the world angle with the same per-axis scale. So the shell passes through
the exact world point under the reticle.

Each frame a shell's movement is a segment walked tile by tile
(systems/raycast.py), so fast shells can't skip thin walls.
"""

from __future__ import annotations

import math

from .. import config
from ..entities.effects import Effect
from ..entities.projectile import Projectile
from ..entities.tank import Tank
from ..world.tiles import Damage
from .collision import screen_angle
from .raycast import RayHit, first_hit

# Sound events returned to the scene (it owns the audio).
SHOT, HIT, BREAK, FIZZLE = "shot", "hit", "break", "fizzle"


def muzzle_point(tank: Tank) -> tuple[float, float]:
    """World position of the barrel tip."""
    s = screen_angle(tank.turret_angle)
    length = tank.spec.barrel_length_px
    return (
        tank.x + math.cos(s) * length / config.TILE_PX_W,
        tank.y + math.sin(s) * length / config.TILE_PX_H,
    )


def fire(tank: Tank, world, projectiles: list[Projectile], effects: list[Effect]) -> list[str]:
    """Fire the tank's weapon. Returns sound events."""
    mx, my = muzzle_point(tank)
    effects.append(Effect("muzzle", mx, my, tank.turret_angle))
    shell = tank.weapon.spec.shell
    # If the barrel is poking into (or through) a wall, the shot lands there
    # instead of spawning on the far side.
    hit = first_hit(world.tile_at, tank.x, tank.y, mx, my)
    if hit is not None:
        return [SHOT, _impact(world, hit, shell.damage, tank.turret_angle, effects)]
    projectiles.append(Projectile(mx, my, tank.turret_angle, shell))
    return [SHOT]


def update_projectiles(
    projectiles: list[Projectile], world, effects: list[Effect], dt: float
) -> list[str]:
    """Move every shell, resolve hits and range. Returns sound events."""
    events: list[str] = []
    for p in projectiles:
        step = p.spec.speed * dt
        remaining = p.spec.max_range - p.travelled
        last_leg = step >= remaining
        if last_leg:
            step = remaining
        nx, ny = p.x + p.dir_x * step, p.y + p.dir_y * step
        hit = first_hit(world.tile_at, p.x, p.y, nx, ny)
        if hit is not None:
            events.append(_impact(world, hit, p.spec.damage, p.angle, effects))
            p.alive = False
            continue
        p.x, p.y = nx, ny
        p.travelled += step
        if last_leg:
            effects.append(Effect("fizzle", p.x, p.y))
            events.append(FIZZLE)
            p.alive = False
    projectiles[:] = [p for p in projectiles if p.alive]
    return events


def _impact(world, hit: RayHit, damage: int, angle: float, effects: list[Effect]) -> str:
    """Apply a shell hit to a tile and spawn the matching effects."""
    # Pull the spark back a hair so it sits on the tile's face, not inside.
    back = 0.05
    ex, ey = hit.x - math.cos(angle) * back, hit.y - math.sin(angle) * back
    effects.append(Effect("impact", ex, ey, angle))
    result = world.damage_tile(hit.tx, hit.ty, damage)
    if result is Damage.DESTROYED:
        effects.append(Effect("debris", hit.tx + 0.5, hit.ty + 0.5))
        return BREAK
    effects.append(Effect("tile_flash", hit.tx, hit.ty))
    return HIT
