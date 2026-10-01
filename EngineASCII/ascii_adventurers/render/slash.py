"""
render/slash.py -- a sword slash (the knight's, before the dwarf replaced him): a classic white crescent.

The crescent follows the swing's arc at its reach: thickest in the middle,
tapering to points at both ends, a white core inside a pale blue glow. It
plays in FRAMES steps over the effect's short life -- the blade sweeping
across the arc, then the whole crescent, then a thinner fading afterimage.

Painted as a picture (render/sprites.py SpriteBank, baked per angle bucket
and frame, cached) rather than text glyphs, so the curve is smooth.
"""

from __future__ import annotations

import math

import pygame

from .. import config
from ..engine_ext.camera import Camera
from ..entities.effects import Effect
from .sprites import SpriteBank

ANGLE_STEPS = 32
FRAMES = 4
# Per frame: (start, end) of the arc shown (0 = where the swing begins,
# 1 = where it ends), thickness scale, and opacity.
# The ending thins out rather than turning see-through (translucent white
# reads as grey over dark ground).
_FRAME_SHAPE = ((0.0, 0.45, 0.8, 255), (0.0, 0.85, 1.0, 255),
                (0.1, 1.0, 1.0, 255), (0.45, 1.0, 0.4, 230))
GLOW = (170, 210, 255)
CORE = (255, 255, 255)
RADIUS = 0.85   # of the reach: the blade passes through what it hits, not past it


def _reach_px(reach_tiles: float) -> float:
    # Tiles are 20 x 24 px; a round slash uses their average size.
    return reach_tiles * (config.TILE_PX_W + config.TILE_PX_H) / 2


def _crescent(to_px, angle, radius, arc, s0, s1, width, inset=0.0):
    """Polygon points of the crescent between arc fractions s0..s1: outer
    edge on the circle, inner edge `width` in at the middle of the full
    arc, tapering to nothing at its ends."""
    steps = 24
    outer, inner = [], []
    for i in range(steps + 1):
        s = s0 + (s1 - s0) * i / steps
        a = angle - arc / 2 + arc * s               # sweeps from one side to the other
        w = width * math.sin(math.pi * s)           # taper at the ends
        r_out = radius - inset
        r_in = radius - inset - max(0.0, w - 2 * inset)
        outer.append(to_px(math.cos(a) * r_out, math.sin(a) * r_out))
        inner.append(to_px(math.cos(a) * r_in, math.sin(a) * r_in))
    return outer + inner[::-1]


def _painter(frame: int, reach_px: float, arc: float):
    s0, s1, thick, alpha = _FRAME_SHAPE[frame]

    def for_angle(angle):
        def paint(surf, to_px):
            width = max(6.0, reach_px * 0.28) * thick
            r = reach_px * RADIUS
            glow = _crescent(to_px, angle, r, arc, s0, s1, width)
            core = _crescent(to_px, angle, r, arc, s0, s1, width, inset=width * 0.18)
            # Drawn straight onto the (transparent) sprite: pygame.draw
            # writes the RGBA as-is, so a faded frame stays white, not grey.
            if len(glow) >= 3:
                pygame.draw.polygon(surf, (*GLOW, alpha), glow)
            if len(core) >= 3:
                pygame.draw.polygon(surf, (*CORE, alpha), core)
        return paint
    return for_angle


def draw_slashes(bank: SpriteBank, camera: Camera, effects: list[Effect]) -> None:
    for e in effects:
        if e.kind != "swing":
            continue
        frame = min(FRAMES - 1, int(e.progress * FRAMES))
        reach = _reach_px(e.size)
        arc = math.radians(e.value or 150)
        key = ("slash", frame, round(reach), e.value)
        sprite = bank.rotated(key, e.angle, ANGLE_STEPS, _painter(frame, reach, arc), reach + 4)
        bank.draw(sprite, *camera.world_to_px(e.x, e.y))
