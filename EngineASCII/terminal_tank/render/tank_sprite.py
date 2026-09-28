"""
render/tank_sprite.py -- draws any tank: the player and enemy vehicles.

The hull and the turret+barrel are two rotated sprites from
render/sprites.py, both centered on the tank's exact canvas-pixel position
(so tanks move smoothly, not cell by cell):

  * hull   -- rotated to the hull's true heading, treads along the heading
              and a lighter front plate so forward is readable even when
              reversing (bunkers: a fixed octagonal block).
  * turret -- a round dome with a straight barrel along the true aim angle.

Colors come from the TankSpec's scheme (player green, enemies rust / sand /
steel / concrete); for a moment after being hit a tank blinks bright.
"""

from __future__ import annotations

from .. import config
from ..engine_ext.camera import Camera
from ..entities.tank import Tank
from .sprites import SpriteBank


def draw_tank(bank: SpriteBank, camera: Camera, tank: Tank) -> None:
    x, y = camera.world_to_px(tank.x, tank.y)
    scheme = "hit" if tank.hurt_flash > 0 else None
    if tank.faction == "player":
        hull_steps, turret_steps = config.HULL_ANGLE_STEPS, config.TURRET_ANGLE_STEPS
    else:
        hull_steps, turret_steps = config.ENEMY_HULL_ANGLE_STEPS, config.ENEMY_TURRET_ANGLE_STEPS
    bank.draw(bank.hull(tank.spec, tank.hull_angle, scheme, hull_steps), x, y)
    bank.draw(bank.turret(tank.spec, tank.turret_angle, scheme, turret_steps), x, y)
