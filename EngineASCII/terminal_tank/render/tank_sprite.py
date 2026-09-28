"""
render/tank_sprite.py -- draws the player tank.

The hull and the turret+barrel are two rotated sprites from
render/sprites.py, both centered on the tank's exact canvas-pixel position
(so the tank moves smoothly, not cell by cell):

  * hull   -- rotated to the hull's true heading (baked in
              config.HULL_ANGLE_STEPS steps), treads along the heading and a
              lighter front plate so forward is readable even when reversing.
  * turret -- a round dome with a straight barrel along the true aim angle
              (config.TURRET_ANGLE_STEPS steps), drawn over the hull.
"""

from __future__ import annotations

from ..engine_ext.camera import Camera
from ..entities.tank import Tank
from .sprites import SpriteBank


def draw_tank(bank: SpriteBank, camera: Camera, tank: Tank) -> None:
    x, y = camera.world_to_px(tank.x, tank.y)
    bank.draw(bank.hull(tank.hull_angle), x, y)
    bank.draw(bank.turret(tank.turret_angle), x, y)
