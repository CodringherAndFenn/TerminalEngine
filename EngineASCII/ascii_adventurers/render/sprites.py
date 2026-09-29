"""
render/sprites.py -- small pictures drawn at exact pixel positions.

Why: a text cell is 10x24 px, and the finest the engine's block glyphs go is
a 10x12 half-block -- too coarse for characters, creatures, the reticle or
a rotated shape. So those are painted as small pictures (pixel art, or
polygons in screen-pixel space rotated to the exact on-screen angle) and
blitted straight onto the canvas with a transparent background, so terrain
shows around the shape.

Chunky look: pictures are painted at a reduced resolution of
config.SPRITE_PIXEL (w, h) screen pixels per sprite pixel, then scaled up
with nearest-neighbor.

Rotating sprites have their angles quantized into buckets and each bucket
is baked once, lazily, then reused.

History: until M7 every sprite was cut into cell-sized pieces registered as
custom engine glyphs (TextRenderer.register_glyph, see ENGINE_CHANGES.md)
and drawn one piece per put_px call. Drawing each sprite as one cropped
image is the same pixels at a fraction of the cost (one blit instead of
~6-15 Python calls per sprite), which matters with hundreds of enemies.
bake() still slices into cells for tests and tools.
"""

from __future__ import annotations

import math
from collections import OrderedDict
from typing import Callable

import pygame

from engine import TextRenderer

from .. import config, palette

TAU = 2 * math.pi

# (dc, dr, surface): a cell offset from the sprite's anchor cell, and that
# cell's cell_w x cell_h image (SRCALPHA; transparent where empty).
CellPiece = tuple[int, int, pygame.Surface]


def screen_angle(world_angle: float, cell_w: int, cell_h: int, cpt: int) -> float:
    """Convert a world angle to the angle the same direction has on screen.

    A world tile is cpt*cell_w x cell_h pixels (20x24), not square, so e.g.
    world 45 degrees is ~50 degrees on screen. Sprites are painted in screen
    pixels, so they need the on-screen angle to point where the world does.
    """
    return math.atan2(math.sin(world_angle) * cell_h, math.cos(world_angle) * cell_w * cpt)


def angle_bucket(angle: float, steps: int) -> int:
    """Nearest of `steps` evenly spaced angles (bucket 0 = east)."""
    return round(angle / TAU * steps) % steps


# --- Baking ------------------------------------------------------------------------

Painter = Callable[[pygame.Surface, Callable[[float, float], tuple[float, float]]], None]


def _paint_full(painter: Painter, reach_px: float, cell_w: int, cell_h: int):
    """Paint a sprite around the anchor cell's center onto a canvas whole
    cells in size. Returns (surface, span_c, span_r): the surface spans
    span_c cells left/right and span_r cells up/down of the anchor cell.

    `painter(surface, to_px)` draws onto a low-res SRCALPHA surface; `to_px`
    maps screen-pixel offsets from the anchor center to that surface's
    coordinates. `reach_px` is how far from the center the sprite may extend,
    which sizes the canvas.
    """
    pw, ph = config.SPRITE_PIXEL
    span_c = max(0, math.ceil((reach_px - cell_w / 2) / cell_w))
    span_r = max(0, math.ceil((reach_px - cell_h / 2) / cell_h))
    full_w = (2 * span_c + 1) * cell_w
    full_h = (2 * span_r + 1) * cell_h

    low = pygame.Surface((full_w // pw, full_h // ph), pygame.SRCALPHA)
    cx = (span_c * cell_w + cell_w / 2) / pw
    cy = (span_r * cell_h + cell_h / 2) / ph

    def to_px(x: float, y: float) -> tuple[float, float]:
        return (cx + x / pw, cy + y / ph)

    painter(low, to_px)
    return pygame.transform.scale(low, (full_w, full_h)), span_c, span_r  # nearest-neighbor


def bake(painter: Painter, reach_px: float, cell_w: int, cell_h: int) -> list[CellPiece]:
    """Paint a sprite (see _paint_full) and slice it into non-empty cells."""
    full, span_c, span_r = _paint_full(painter, reach_px, cell_w, cell_h)
    pieces: list[CellPiece] = []
    for r in range(2 * span_r + 1):
        for c in range(2 * span_c + 1):
            tile = full.subsurface((c * cell_w, r * cell_h, cell_w, cell_h))
            if tile.get_bounding_rect().width:
                pieces.append((c - span_c, r - span_r, tile.copy()))
    return pieces


# A baked sprite: its image cropped to what was painted, and that image's
# top-left offset in pixels from the anchor cell's top-left.
Sprite = tuple[pygame.Surface, int, int]


def bake_sprite(painter: Painter, reach_px: float, cell_w: int, cell_h: int) -> Sprite:
    """Paint a sprite (see _paint_full) as one image cropped to its pixels."""
    full, span_c, span_r = _paint_full(painter, reach_px, cell_w, cell_h)
    rect = full.get_bounding_rect()
    if not rect.width:
        rect = pygame.Rect(0, 0, 1, 1)   # nothing painted: one clear pixel
    return full.subsurface(rect).copy(), rect.x - span_c * cell_w, rect.y - span_r * cell_h


def quad(to_px, angle: float, u0: float, u1: float, v0: float, v1: float):
    """Corners of a rectangle given in the sprite's own frame -- u along the
    heading, v across it -- rotated by `angle` and mapped to the surface."""
    ca, sa = math.cos(angle), math.sin(angle)
    pts = ((u0, v0), (u1, v0), (u1, v1), (u0, v1))
    return [to_px(u * ca - v * sa, u * sa + v * ca) for u, v in pts]


def paint_reticle(surf, to_px) -> None:
    """Crosshair ring with four ticks, centered on the aim point. A dark
    shadow pass underneath keeps it readable over bright terrain."""
    for color, grow in ((palette.RETICLE_SHADOW, 1), (palette.RETICLE, 0)):
        (x0, y0), (x1, y1) = to_px(-7 - grow, -7 - grow), to_px(7 + grow, 7 + grow)
        ring = pygame.Rect(round(x0), round(y0), round(x1 - x0), round(y1 - y0))
        pygame.draw.ellipse(surf, color, ring, 1 + grow)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            a, b = to_px(dx * 4, dy * 4), to_px(dx * 11, dy * 11)
            pygame.draw.line(surf, color, a, b, 1 + grow)


def paint_tile_marker(tile_w: int, tile_h: int) -> Painter:
    """Corner brackets around one world tile (centered on the tile)."""

    def paint(surf, to_px):
        hw, hh, arm = tile_w / 2, tile_h / 2, 5
        for sx in (-1, 1):
            for sy in (-1, 1):
                cx, cy = sx * hw - (sx > 0), sy * hh - (sy > 0)  # inside the tile
                pygame.draw.line(surf, palette.TILE_MARKER, to_px(cx, cy), to_px(cx - sx * arm, cy))
                pygame.draw.line(surf, palette.TILE_MARKER, to_px(cx, cy), to_px(cx, cy - sy * arm))

    return paint


class SpriteBank:
    """Lazily bakes sprites (per angle bucket, for rotating ones) and draws
    them onto the canvas.

    Rotated sprites can use many angle steps, too many to keep them all, so
    they live in an LRU cache capped at config.SPRITE_CACHE_SIZE sprites:
    the least recently drawn angles are evicted. Only the handful of angles
    near the current ones are ever hot, so eviction almost never touches
    anything on screen.
    """

    def __init__(self, text: TextRenderer, cpt: int) -> None:
        self.text = text
        self.cell_w, self.cell_h = text.display.cell_w, text.display.cell_h
        self.cpt = cpt
        # Rotated sprites, least recently used first: (kind, bucket) -> sprite.
        self._lru: OrderedDict[tuple, Sprite] = OrderedDict()
        # Never-evicted sprites (characters, reticle, markers): name -> sprite.
        self._static: dict[str, Sprite] = {}

    @property
    def sprites_cached(self) -> int:
        return len(self._lru) + len(self._static)

    def _bake(self, painter: Painter, reach: float) -> Sprite:
        return bake_sprite(painter, reach, self.cell_w, self.cell_h)

    def rotated(self, key, world_angle: float, steps: int, painter_for, reach: float) -> Sprite:
        """A sprite drawn at `world_angle`, baked per angle bucket.

        `painter_for(screen_angle)` returns the Painter for one bucket's
        exact angle; `key` names the sprite (include anything else that
        changes its look, e.g. the creature type).
        """
        a = screen_angle(world_angle, self.cell_w, self.cell_h, self.cpt)
        bucket = angle_bucket(a, steps)
        full_key = (key, bucket)
        sprite = self._lru.get(full_key)
        if sprite is not None:
            self._lru.move_to_end(full_key)
            return sprite
        while len(self._lru) >= config.SPRITE_CACHE_SIZE:
            self._lru.popitem(last=False)
        sprite = self._lru[full_key] = self._bake(painter_for(bucket * TAU / steps), reach)
        return sprite

    def static(self, name: str, painter: Painter, reach: float) -> Sprite:
        """A sprite that doesn't rotate (characters, reticle, markers), baked once."""
        sprite = self._static.get(name)
        if sprite is None:
            sprite = self._static[name] = self._bake(painter, reach)
        return sprite

    def draw(self, sprite: Sprite, x: float, y: float) -> None:
        """Draw a sprite centered on canvas pixel (x, y).

        The sprite was painted around an anchor cell whose center is the
        sprite's center, so the anchor's top-left is half a cell up-left of
        (x, y), rounded to a whole pixel (sprites move smoothly, pixel by
        pixel, like everything drawn with put_px).
        """
        surf, ox, oy = sprite
        self.text.display.canvas.blit(
            surf, (round(x - self.cell_w / 2) + ox, round(y - self.cell_h / 2) + oy))
