"""
ui/crosshair.py -- the aiming reticle.

The OS cursor is hidden during play. Two things replace it:
  * corner brackets on the world tile under the mouse (the tile a shell
    aimed there would reach), moving with the map as it scrolls;
  * a ring exactly at the mouse point -- the true aim point.

Both are drawn only over the world viewport, not over the HUD, though aiming
keeps working when the pointer is over the HUD.
"""

from __future__ import annotations

import math

from ..engine_ext.camera import Camera
from ..render.sprites import SpriteBank, paint_reticle, paint_tile_marker


def draw_crosshair(bank: SpriteBank, camera: Camera, mouse_px: tuple[float, float]) -> None:
    mx, my = mouse_px
    if not (0 <= my < camera.view_h):
        return

    wx, wy = camera.canvas_to_world(mx, my)
    tx, ty = math.floor(wx), math.floor(wy)
    x, y = camera.tile_to_px(tx, ty)
    marker = bank.static(
        "tile_marker", paint_tile_marker(camera.tile_w, camera.tile_h), camera.tile_w
    )
    bank.draw(marker, x + camera.tile_w / 2, y + camera.tile_h / 2)

    bank.draw(bank.static("reticle", paint_reticle, 14), mx, my)
