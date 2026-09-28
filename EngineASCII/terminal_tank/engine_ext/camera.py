"""
engine_ext/camera.py -- the smooth-scrolling top-down camera.

Maps between two coordinate spaces:

  world   continuous (x, y) in tiles. y grows downward (screen convention).
  canvas  pixels on the engine's canvas (what Display.window_to_canvas gives,
          and what TextRenderer.put_px draws at).

A world tile is CELLS_PER_TILE cells wide and 1 row tall (20 x 24 px).

The camera tracks a world point (`self.x`, `self.y`) that sits at the center
of the viewport, and derives `origin_px`: the world-pixel coordinate of the
viewport's top-left corner. The origin is rounded to whole canvas pixels, so
everything drawn with it moves in lockstep and nothing shimmers. Scrolling
resolution is therefore 1 canvas pixel in every direction -- the old camera
was limited to whole cells (10 px across, 24 px down), which made vertical
and diagonal motion jumpy.

Smooth follow: instead of snapping to its target, the camera closes a fixed
fraction of the remaining distance each second (exponential smoothing,
frame-rate independent), and is never allowed to trail by more than
CAMERA_MAX_LAG_TILES.
"""

from __future__ import annotations

import math

from .. import config


class Camera:
    def __init__(self, view_cols: int, view_rows: int, cell_w: int, cell_h: int) -> None:
        self.cell_w = cell_w
        self.cell_h = cell_h
        self.cpt = config.CELLS_PER_TILE
        self.tile_w = self.cpt * cell_w   # tile size in canvas pixels
        self.tile_h = cell_h
        self.x = 0.0                      # world point at the viewport center
        self.y = 0.0
        self._tx = 0.0                    # the point being followed
        self._ty = 0.0
        self.origin_px = (0, 0)
        self.resize(view_cols, view_rows)

    def resize(self, view_cols: int, view_rows: int) -> None:
        """Set the viewport size in cells (call when the grid changes)."""
        self.view_cols = view_cols
        self.view_rows = view_rows
        self.view_w = view_cols * self.cell_w
        self.view_h = view_rows * self.cell_h
        self._update_origin()

    # --- Movement ------------------------------------------------------------------

    def center_on(self, x: float, y: float) -> None:
        """Jump straight to world point (x, y), no smoothing."""
        self.x, self.y = x, y
        self._tx, self._ty = x, y
        self._update_origin()

    def follow(self, x: float, y: float, dt: float) -> None:
        """Ease toward world point (x, y).

        k = 1 - e^(-rate * dt) is the fraction of the gap closed this frame;
        using the exponential (rather than rate * dt) makes the motion
        identical at any frame rate.
        """
        self._tx, self._ty = x, y
        rate = config.CAMERA_FOLLOW_RATE
        if rate <= 0:
            self.center_on(x, y)
            return
        k = 1.0 - math.exp(-rate * dt)
        self.x += (x - self.x) * k
        self.y += (y - self.y) * k
        # Never let a fast target drag the camera too far behind.
        lag = config.CAMERA_MAX_LAG_TILES
        self.x = min(max(self.x, x - lag), x + lag)
        self.y = min(max(self.y, y - lag), y + lag)
        self._update_origin()

    def _update_origin(self) -> None:
        """Pick the whole-pixel origin.

        Naively rounding the camera position on its own makes the followed
        object wobble by 1 px on screen: while the camera trails it, the two
        are rounded independently and their rounding errors alternate frame
        to frame. Instead, the origin is built from the *target's* rounded
        pixel position minus the rounded on-screen offset the target should
        have (screen center + camera lag). The target's screen position is
        then exactly that rounded offset, which only changes when the lag
        itself changes -- the tank sits still on screen while the world
        scrolls under it.
        """
        self.origin_px = (
            self._axis_origin(self._tx, self.x, self.tile_w, self.view_w),
            self._axis_origin(self._ty, self.y, self.tile_h, self.view_h),
        )

    @staticmethod
    def _axis_origin(target: float, cam: float, tile_px: int, view_px: int) -> int:
        target_px = target * tile_px
        screen_offset = view_px / 2 + (target_px - cam * tile_px)
        return round(target_px) - round(screen_offset)

    # --- world <-> canvas -------------------------------------------------------------

    def world_to_px(self, x: float, y: float) -> tuple[float, float]:
        """Canvas pixel of world point (x, y). May be off-screen."""
        ox, oy = self.origin_px
        return (x * self.tile_w - ox, y * self.tile_h - oy)

    def tile_to_px(self, tx: int, ty: int) -> tuple[int, int]:
        """Canvas pixel of world tile (tx, ty)'s top-left corner."""
        ox, oy = self.origin_px
        return (tx * self.tile_w - ox, ty * self.tile_h - oy)

    def canvas_to_world(self, px: float, py: float) -> tuple[float, float]:
        """World point under canvas pixel (px, py) -- the exact inverse of
        world_to_px, so the aimed point is exactly the point under the
        mouse."""
        ox, oy = self.origin_px
        return ((px + ox) / self.tile_w, (py + oy) / self.tile_h)

    def visible_tiles(self) -> tuple[int, int, int, int]:
        """Inclusive tile range (tx0, ty0, tx1, ty1) touching the viewport."""
        ox, oy = self.origin_px
        return (
            math.floor(ox / self.tile_w),
            math.floor(oy / self.tile_h),
            math.floor((ox + self.view_w - 1) / self.tile_w),
            math.floor((oy + self.view_h - 1) / self.tile_h),
        )
