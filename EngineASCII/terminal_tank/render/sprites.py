"""
render/sprites.py -- rotated, shape-accurate sprites sliced into grid cells.

Why: a text cell is 10x24 px, and the finest the engine's block glyphs go is a
10x12 half-block. A tank hull rotated 45 degrees collapses to a few of those
blocks, and a text '/' has one fixed slope, so neither the hull nor the
barrel can look right at arbitrary angles using characters alone.

How: each sprite is painted as a small picture -- polygons in screen-pixel
space, rotated to the exact on-screen angle -- then cut into cell-sized
tiles. Each non-empty tile becomes one custom glyph, drawn with transparent
background so terrain shows around the shape, and placed at exact pixel
positions with the engine's put_px.

Chunky look: pictures are painted at a reduced resolution of
config.SPRITE_PIXEL (w, h) screen pixels per sprite pixel, then scaled up
with nearest-neighbor -- so the tank has the same hard-edged retro pixels as
the synthesized block glyphs instead of looking like modern vector art.

Angles are quantized into buckets (config.*_ANGLE_STEPS) and each bucket is
baked once, lazily, then reused. The pieces reach the
screen through the engine's TextRenderer.register_glyph() (see
ENGINE_CHANGES.md), so they go through the normal put()/glyph-cache path.
"""

from __future__ import annotations

import math
from collections import OrderedDict
from typing import Callable

import pygame

from engine import TextRenderer

from .. import config, palette
from ..specs import TankSpec

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


def bake(painter: Painter, reach_px: float, cell_w: int, cell_h: int) -> list[CellPiece]:
    """Paint a sprite around the anchor cell's center and slice it into cells.

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
    full = pygame.transform.scale(low, (full_w, full_h))  # nearest-neighbor

    pieces: list[CellPiece] = []
    for r in range(2 * span_r + 1):
        for c in range(2 * span_c + 1):
            tile = full.subsurface((c * cell_w, r * cell_h, cell_w, cell_h))
            if tile.get_bounding_rect().width:
                pieces.append((c - span_c, r - span_r, tile.copy()))
    return pieces


def quad(to_px, angle: float, u0: float, u1: float, v0: float, v1: float):
    """Corners of a rectangle given in the sprite's own frame -- u along the
    heading, v across it -- rotated by `angle` and mapped to the surface."""
    ca, sa = math.cos(angle), math.sin(angle)
    pts = ((u0, v0), (u1, v0), (u1, v1), (u0, v1))
    return [to_px(u * ca - v * sa, u * sa + v * ca) for u, v in pts]


def paint_hull(angle: float, spec: TankSpec) -> Painter:
    """Hull pointing along screen angle `angle`: two treads down the long
    sides with cross-links, the body between them, a lighter front plate, and
    a dark outline so it separates from any terrain."""
    L, W = spec.hull_length_px, spec.hull_width_px
    T = W * 0.27  # tread width

    def paint(surf, to_px):
        hl, hw = L / 2, W / 2
        for v0, v1 in ((-hw, -hw + T), (hw - T, hw)):
            pygame.draw.polygon(surf, palette.TANK_TREAD, quad(to_px, angle, -hl, hl, v0, v1))
            u = -hl + 3
            while u < hl - 1:  # tread links
                pygame.draw.polygon(
                    surf, palette.TANK_TREAD_DARK, quad(to_px, angle, u, u + 2, v0, v1)
                )
                u += 6
        body = (-hl + 4, hl - 3, -hw + T - 1, hw - T + 1)
        pygame.draw.polygon(surf, palette.TANK_BODY, quad(to_px, angle, *body))
        pygame.draw.polygon(
            surf, palette.TANK_FRONT, quad(to_px, angle, hl - 10, hl - 3, body[2], body[3])
        )
        pygame.draw.polygon(surf, palette.TANK_OUTLINE, quad(to_px, angle, -hl, hl, -hw, hw), 1)

    return paint


def paint_turret(angle: float, spec: TankSpec) -> Painter:
    """Round turret with a straight barrel along screen angle `angle`."""
    R = spec.turret_radius_px
    BL, BW = spec.barrel_length_px, spec.barrel_width_px

    def paint(surf, to_px):
        # Barrel (with a slightly wider muzzle), outlined, then the dome over
        # its base so the barrel appears to come out of the turret.
        barrel = quad(to_px, angle, 0, BL, -BW / 2, BW / 2)
        muzzle = quad(to_px, angle, BL - 5, BL, -BW / 2 - 1, BW / 2 + 1)
        pygame.draw.polygon(surf, palette.TANK_OUTLINE, muzzle)
        pygame.draw.polygon(surf, palette.TANK_BARREL, barrel)
        pygame.draw.polygon(surf, palette.TANK_OUTLINE, barrel, 1)

        (x0, y0), (x1, y1) = to_px(-R, -R), to_px(R, R)
        dome = pygame.Rect(round(x0), round(y0), max(1, round(x1 - x0)), max(1, round(y1 - y0)))
        pygame.draw.ellipse(surf, palette.TANK_TURRET, dome)
        pygame.draw.ellipse(surf, palette.TANK_OUTLINE, dome, 1)

    return paint


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
    """Lazily bakes hull/turret sprites per angle bucket and registers every
    piece as a custom engine glyph (TextRenderer.register_glyph), so drawing
    a sprite is just TextRenderer.put_px() calls with bg=None.

    Each piece gets its own Private Use Area character. Pieces paint their
    own colors, so the fg passed to put_px() is irrelevant; a single constant
    is used so each piece occupies exactly one glyph-cache entry.

    Rotation steps are fine (fractions of a degree for the barrel) so turning
    looks continuous -- coarse steps made the barrel visibly snap as the aim
    angle drifted while driving. That's too many glyphs to keep them all, so
    rotated sprites live in an LRU cache capped at config.SPRITE_GLYPH_BUDGET
    glyphs: the least recently drawn angles are evicted, their characters
    unregistered from the engine (freeing its cached images) and reused.
    Only the handful of angles near the current ones are ever hot, so
    eviction almost never touches anything on screen.
    """

    _FIRST_CHAR = 0xE000
    _LAST_CHAR = 0xF8FF
    FG = (255, 255, 255)

    def __init__(self, text: TextRenderer, cpt: int) -> None:
        self.text = text
        self.cell_w, self.cell_h = text.display.cell_w, text.display.cell_h
        self.cpt = cpt
        self._next_char = self._FIRST_CHAR
        self._free: list[str] = []          # chars released by eviction
        # Rotated sprites, least recently used first: (kind, bucket) -> pieces.
        self._lru: OrderedDict[tuple[str, int], list[tuple[int, int, str]]] = OrderedDict()
        self._lru_glyphs = 0
        # Never-evicted sprites (reticle, markers): name -> pieces.
        self._static: dict[str, list[tuple[int, int, str]]] = {}

    @property
    def glyphs_in_use(self) -> int:
        return (self._next_char - self._FIRST_CHAR) - len(self._free)

    def _register(self, surf: pygame.Surface) -> str:
        if self._free:
            char = self._free.pop()
        elif self._next_char <= self._LAST_CHAR:
            char = chr(self._next_char)
            self._next_char += 1
        else:
            raise RuntimeError("SpriteBank ran out of Private Use Area characters")
        # Re-registering a recycled char also drops the engine's stale images.
        self.text.register_glyph(char, lambda cell, fg, s=surf: cell.blit(s, (0, 0)))
        return char

    def _bake_pieces(self, painter: Painter, reach: float) -> list[tuple[int, int, str]]:
        baked = bake(painter, reach, self.cell_w, self.cell_h)
        return [(dc, dr, self._register(surf)) for dc, dr, surf in baked]

    def rotated(self, key, world_angle: float, steps: int, painter_for, reach: float):
        """A sprite drawn at `world_angle`, baked per angle bucket.

        `painter_for(screen_angle)` returns the Painter for one bucket's
        exact angle; `key` names the sprite (include anything else that
        changes its look, e.g. the tank type).
        """
        a = screen_angle(world_angle, self.cell_w, self.cell_h, self.cpt)
        bucket = angle_bucket(a, steps)
        full_key = (key, bucket)
        pieces = self._lru.get(full_key)
        if pieces is not None:
            self._lru.move_to_end(full_key)
            return pieces
        # Make room first, so evicted chars can be recycled for this bake.
        while self._lru and self._lru_glyphs >= config.SPRITE_GLYPH_BUDGET:
            _, old = self._lru.popitem(last=False)
            self._lru_glyphs -= len(old)
            for _, _, char in old:
                self.text.unregister_glyph(char)
                self._free.append(char)
        pieces = self._bake_pieces(painter_for(bucket * TAU / steps), reach)
        self._lru[full_key] = pieces
        self._lru_glyphs += len(pieces)
        return pieces

    def hull(self, spec: TankSpec, world_angle: float) -> list[tuple[int, int, str]]:
        reach = math.hypot(spec.hull_length_px, spec.hull_width_px) / 2 + 1
        return self.rotated(
            ("hull", spec.name), world_angle, config.HULL_ANGLE_STEPS,
            lambda a: paint_hull(a, spec), reach,
        )

    def turret(self, spec: TankSpec, world_angle: float) -> list[tuple[int, int, str]]:
        reach = max(spec.barrel_length_px, spec.turret_radius_px) + 2
        return self.rotated(
            ("turret", spec.name), world_angle, config.TURRET_ANGLE_STEPS,
            lambda a: paint_turret(a, spec), reach,
        )

    def static(self, name: str, painter: Painter, reach: float) -> list[tuple[int, int, str]]:
        """A sprite that doesn't rotate (reticle, markers), baked once."""
        pieces = self._static.get(name)
        if pieces is None:
            pieces = self._static[name] = self._bake_pieces(painter, reach)
        return pieces

    def draw(self, pieces: list[tuple[int, int, str]], x: float, y: float) -> None:
        """Draw a sprite centered on canvas pixel (x, y).

        Pieces are laid out around an anchor cell whose center is the
        sprite's center, so the anchor's top-left is half a cell up-left of
        (x, y). Drawn with the engine's pixel-positioned put_px, so sprites
        move smoothly instead of snapping cell to cell.
        """
        ax = round(x - self.cell_w / 2)
        ay = round(y - self.cell_h / 2)
        for dc, dr, char in pieces:
            self.text.put_px(ax + dc * self.cell_w, ay + dr * self.cell_h, char, self.FG, None)
