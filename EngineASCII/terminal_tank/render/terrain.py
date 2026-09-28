"""
render/terrain.py -- draws the visible part of the world through the camera.

Tiles are drawn with the engine's pixel-positioned put_px at the camera's
pixel offset, so the map scrolls smoothly one canvas pixel at a time instead
of jumping a whole cell.

Performance note: this is the hot path (~2,400 tiles per frame on the
ultrawide grid). Rather than one call per tile, each row is split into runs
of tiles that share colors and every run is drawn with a single put_px().
The glyph for each tile comes precomputed from the world.
"""

from __future__ import annotations

from typing import Protocol

from engine import TextRenderer

from ..engine_ext.camera import Camera
from ..world.tiles import TileType


class DrawableWorld(Protocol):
    def tile_at(self, tx: int, ty: int) -> TileType: ...
    def glyph_at(self, tx: int, ty: int) -> str: ...


def draw_terrain(text: TextRenderer, world: DrawableWorld, camera: Camera) -> None:
    """Draw every tile touching the viewport. Partial tiles at the edges are
    clipped by the canvas; any spill below the viewport lands in the HUD
    rows, which the HUD clears before drawing."""
    tx0, ty0, tx1, ty1 = camera.visible_tiles()
    tile_at, glyph_at = world.tile_at, world.glyph_at
    for ty in range(ty0, ty1 + 1):
        x, y = camera.tile_to_px(tx0, ty)
        run: list[str] = []
        run_x = x
        run_colors = None
        for tx in range(tx0, tx1 + 1):
            tile = tile_at(tx, ty)
            colors = (tile.fg, tile.bg)
            if colors != run_colors:
                if run:
                    text.put_px(run_x, y, "".join(run), *run_colors)
                run, run_x, run_colors = [], x, colors
            run.append(glyph_at(tx, ty))
            x += camera.tile_w
        if run:
            text.put_px(run_x, y, "".join(run), *run_colors)
