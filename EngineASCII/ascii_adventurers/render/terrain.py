"""
render/terrain.py -- draws the visible part of the world through the camera.

Terrain is drawn from a cache of pre-drawn blocks: square pieces of the
world, TERRAIN_BLOCK_TILES tiles on a side, each drawn once into its own
Surface. A frame is then ~20 block blits instead of ~5,000 glyph blits
(one per character), which is what used to make terrain ~85% of the frame.

  * A block is drawn the first time it touches the view, one blit per tile
    from pre-rendered tile images (render/glyphs.py: one per glyph +
    colors, pixel-identical to the engine's put_px).
  * Blocks are kept least-recently-used, up to TERRAIN_CACHE_BLOCKS. Blocks
    near the view stay hot; far ones are evicted and redrawn if revisited.
  * A few blocks in the ring just outside the view are pre-drawn each
    frame (TERRAIN_PREFETCH_BLOCKS), so new ground scrolling in is ready.
  * Tiles that change (damage wear, destroyed walls) are reported by the
    world (drain_changed) and repainted in their cached block.

Blocks are blitted at the camera's pixel offset, so the map still scrolls
smoothly one canvas pixel at a time. Drawing is clipped to the viewport so
blocks never spill into the HUD rows.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Protocol

import pygame

from engine import TextRenderer

from .. import config
from ..engine_ext.camera import Camera
from ..world.tiles import TileType
from .glyphs import images_for


class DrawableWorld(Protocol):
    def tile_at(self, tx: int, ty: int) -> TileType: ...
    def glyph_at(self, tx: int, ty: int) -> str: ...


class TerrainRenderer:
    def __init__(self, text: TextRenderer) -> None:
        self.text = text
        self.block = config.TERRAIN_BLOCK_TILES
        self._blocks: OrderedDict[tuple[int, int], pygame.Surface] = OrderedDict()
        self._tile_size = (0, 0)
        self.blocks_drawn = 0   # blocks drawn from scratch (for stats/tests)

    # --- Blocks ---------------------------------------------------------------------

    def _draw_block(self, world: DrawableWorld, bx: int, by: int) -> pygame.Surface:
        n = self.block
        tw, th = self._tile_size
        surf = pygame.Surface((n * tw, n * th))
        tile_at, glyph_at, image = world.tile_at, world.glyph_at, images_for(self.text).get
        x0, y0 = bx * n, by * n
        blits = []
        for j in range(n):
            ty = y0 + j
            for i in range(n):
                tile = tile_at(x0 + i, ty)
                blits.append((image(glyph_at(x0 + i, ty), tile.fg, tile.bg), (i * tw, j * th)))
        surf.fblits(blits)
        self.blocks_drawn += 1
        return surf

    def _repaint_changed(self, world) -> None:
        drain = getattr(world, "drain_changed", None)
        if drain is None:
            return
        n = self.block
        tw, th = self._tile_size
        for tx, ty in drain():
            surf = self._blocks.get((tx // n, ty // n))
            if surf is not None:
                tile = world.tile_at(tx, ty)
                surf.blit(images_for(self.text).get(world.glyph_at(tx, ty), tile.fg, tile.bg),
                          ((tx % n) * tw, (ty % n) * th))

    def _block(self, world: DrawableWorld, key: tuple[int, int]) -> pygame.Surface:
        surf = self._blocks.get(key)
        if surf is not None:
            self._blocks.move_to_end(key)
            return surf
        surf = self._blocks[key] = self._draw_block(world, *key)
        return surf

    def clear(self) -> None:
        """Forget every cached block (e.g. a different world)."""
        self._blocks.clear()

    # --- Frame ----------------------------------------------------------------------

    def draw(self, world: DrawableWorld, camera: Camera) -> None:
        """Draw every block touching the viewport, clipped to it."""
        size = (camera.tile_w, camera.tile_h)
        if size != self._tile_size:     # cell size changed: nothing is valid
            self._tile_size = size
            self._blocks.clear()
        self._repaint_changed(world)

        n = self.block
        tx0, ty0, tx1, ty1 = camera.visible_tiles()
        keys = [(bx, by) for by in range(ty0 // n, ty1 // n + 1)
                for bx in range(tx0 // n, tx1 // n + 1)]
        canvas = self.text.display.canvas
        old_clip = canvas.get_clip()
        canvas.set_clip(pygame.Rect(0, 0, camera.view_w, camera.view_h))
        canvas.fblits([(self._block(world, k), camera.tile_to_px(k[0] * n, k[1] * n))
                       for k in keys])
        canvas.set_clip(old_clip)

        # Pre-draw a few of the blocks just outside the view, so scrolling
        # into new ground doesn't draw a whole row of blocks in one frame.
        # Only blocks whose chunk is generated: drawing an ungenerated one
        # would force the chunk to be built on the spot.
        bx0, by0, bx1, by1 = tx0 // n - 1, ty0 // n - 1, tx1 // n + 1, ty1 // n + 1
        ready = getattr(world, "is_generated", None)
        missing = [(bx, by) for by in range(by0, by1 + 1) for bx in range(bx0, bx1 + 1)
                   if (bx, by) not in self._blocks
                   and (ready is None or ready(bx * n, by * n))]
        if missing:
            mx, my = (bx0 + bx1) / 2, (by0 + by1) / 2
            missing.sort(key=lambda k: (k[0] - mx) ** 2 + (k[1] - my) ** 2)
            for key in missing[:config.TERRAIN_PREFETCH_BLOCKS]:
                self._blocks[key] = self._draw_block(world, *key)

        # Keep at least two screens' worth (plus the ring), so blocks just
        # scrolled off aren't redrawn when the player turns around.
        ring = (bx1 - bx0 + 1) * (by1 - by0 + 1)
        limit = max(config.TERRAIN_CACHE_BLOCKS, 2 * ring)
        while len(self._blocks) > limit:
            self._blocks.popitem(last=False)
