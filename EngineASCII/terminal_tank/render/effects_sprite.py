"""
render/effects_sprite.py -- shells, trails, muzzle flashes, impacts.

Everything here is a baked sprite (render/sprites.py) drawn at exact pixel
positions, like the tank. Animated effects are a few fixed frames picked by
the effect's progress, each painted from the fixed palette colors -- no
per-frame computed colors, so the engine's glyph cache stays bounded.
"""

from __future__ import annotations

import math

import pygame

from engine import TextRenderer

from .. import config, palette
from ..engine_ext.camera import Camera
from ..entities.effects import Effect
from ..entities.projectile import Projectile
from .sprites import SpriteBank, quad

# --- Painters ------------------------------------------------------------------------


def _circle(surf, to_px, color, x, y, r, width=0):
    (x0, y0), (x1, y1) = to_px(x - r, y - r), to_px(x + r, y + r)
    rect = pygame.Rect(round(x0), round(y0), max(1, round(x1 - x0)), max(1, round(y1 - y0)))
    pygame.draw.ellipse(surf, color, rect, width)


def paint_shell(length: int, width: int):
    """A glowing slug pointing along the screen angle."""

    def for_angle(a):
        def paint(surf, to_px):
            hl, hw = length / 2, width / 2
            pygame.draw.polygon(surf, palette.SHELL_GLOW, quad(to_px, a, -hl, hl, -hw, hw))
            pygame.draw.polygon(
                surf, palette.SHELL_CORE, quad(to_px, a, -hl + 2, hl, -hw + 1, hw - 1)
            )

        return paint

    return for_angle


def paint_trail_dot(k: int):
    radius = (2.5, 2.0, 1.5)[k]

    def paint(surf, to_px):
        _circle(surf, to_px, palette.TRAIL[k], 0, 0, radius)

    return paint


def paint_muzzle(frame: int):
    """Frame 0: a bright cone bursting out of the barrel; frame 1: fading."""

    def for_angle(a):
        def paint(surf, to_px):
            if frame == 0:
                pygame.draw.polygon(surf, palette.FLASH_EDGE, quad(to_px, a, -2, 16, -6, 6))
                pygame.draw.polygon(surf, palette.FLASH, quad(to_px, a, 0, 12, -4, 4))
                _circle(surf, to_px, palette.FLASH_HOT, 0, 0, 5)
            else:
                pygame.draw.polygon(surf, palette.FLASH_EDGE, quad(to_px, a, 0, 9, -3, 3))
                _circle(surf, to_px, palette.FLASH, 0, 0, 3)

        return paint

    return for_angle


def paint_impact(frame: int):
    """Spark burst -> expanding ring with flying bits -> settling dust."""

    def paint(surf, to_px):
        if frame == 0:
            for k in range(8):
                a = k * math.pi / 4 + 0.2
                pygame.draw.line(
                    surf, palette.SPARK, to_px(0, 0), to_px(math.cos(a) * 10, math.sin(a) * 10)
                )
            _circle(surf, to_px, palette.SPARK_HOT, 0, 0, 5)
        elif frame == 1:
            _circle(surf, to_px, palette.SPARK, 0, 0, 8, 1)
            for k in range(6):
                a = k * math.pi / 3 + 0.5
                _circle(surf, to_px, palette.DEBRIS, math.cos(a) * 11, math.sin(a) * 11, 1.5)
        else:
            for dx, dy, r in ((-4, -2, 3), (3, -3, 2.5), (1, 3, 3)):
                _circle(surf, to_px, palette.DUST[1], dx, dy, r)

    return paint


def paint_debris(frame: int):
    """A tile being destroyed: chunks flying out, then a dust cloud."""

    def paint(surf, to_px):
        if frame == 0:
            _circle(surf, to_px, palette.DUST[0], 0, 0, 8)
            for k in range(6):
                a = k * math.pi / 3
                _circle(surf, to_px, palette.DEBRIS, math.cos(a) * 11, math.sin(a) * 11, 2.5)
        elif frame == 1:
            for k in range(8):
                a = k * math.pi / 4 + 0.3
                _circle(surf, to_px, palette.DUST[0], math.cos(a) * 12, math.sin(a) * 12, 3.5)
        else:
            for k in range(6):
                a = k * math.pi / 3 + 0.6
                _circle(surf, to_px, palette.DUST[1], math.cos(a) * 15, math.sin(a) * 15, 2.5)

    return paint


def paint_fizzle(frame: int):
    """A spent shell dropping into the dirt."""

    def paint(surf, to_px):
        if frame == 0:
            _circle(surf, to_px, palette.DUST[0], -2, 0, 3)
            _circle(surf, to_px, palette.DUST[0], 3, 1, 2.5)
        else:
            _circle(surf, to_px, palette.DUST[1], -4, -1, 3)
            _circle(surf, to_px, palette.DUST[1], 4, 2, 3)

    return paint


def paint_explosion(frame: int):
    """A vehicle or creature destroyed: white-hot core -> fireball -> smoke."""
    hot, fire, ember = palette.DEATH_FIRE

    def paint(surf, to_px):
        if frame == 0:
            _circle(surf, to_px, fire, 0, 0, 14)
            _circle(surf, to_px, hot, 0, 0, 9)
        elif frame == 1:
            _circle(surf, to_px, ember, 0, 0, 20)
            _circle(surf, to_px, fire, 0, 0, 15)
            for k in range(8):
                a = k * math.pi / 4 + 0.3
                _circle(surf, to_px, hot, math.cos(a) * 17, math.sin(a) * 17, 2.5)
        elif frame == 2:
            _circle(surf, to_px, ember, 0, 0, 18, 3)
            for k in range(6):
                a = k * math.pi / 3
                _circle(surf, to_px, palette.DUST[0], math.cos(a) * 14, math.sin(a) * 14, 5)
        else:
            for k in range(6):
                a = k * math.pi / 3 + 0.5
                _circle(surf, to_px, palette.DUST[1], math.cos(a) * 20, math.sin(a) * 20, 4)

    return paint


def paint_spores(frame: int):
    """Spore cloud expanding to the puffer's blast radius, then thinning."""
    cols = palette.SPORE_CLOUD

    def paint(surf, to_px):
        r = (18, 34, 48)[frame]
        _circle(surf, to_px, cols[frame], 0, 0, r * 0.55)
        for k in range(10):
            a = k * math.tau / 10 + frame * 0.35
            d = r * (0.55 + 0.4 * ((k * 7) % 3) / 2)
            _circle(surf, to_px, cols[min(2, frame + (k % 2))], math.cos(a) * d, math.sin(a) * d,
                    4 - frame)

    return paint


def paint_eruption(frame: int):
    """Sand thrown up where a burrower bursts out."""
    c0, c1 = palette.BURROW_DUST

    def paint(surf, to_px):
        r = (14, 26, 38)[frame]
        for k in range(12):
            a = k * math.tau / 12 + frame * 0.2
            _circle(surf, to_px, c0 if k % 2 else c1, math.cos(a) * r, math.sin(a) * r, 4 - frame)
        if frame == 0:
            _circle(surf, to_px, c1, 0, 0, 10)

    return paint


def paint_burrow(frame: int):
    """Little dust puffs a burrower leaves behind underground."""
    def paint(surf, to_px):
        _circle(surf, to_px, palette.BURROW_DUST[frame], (-2, 2)[frame], (1, -1)[frame], 3 - frame)

    return paint


def paint_slash():
    """The warrior's swing: a bright arc sweeping in front of it."""
    def for_angle(a):
        def paint(surf, to_px):
            pts = []
            for k in range(9):
                t = -1.1 + k * 2.2 / 8
                pts.append(to_px(math.cos(a + t) * 16, math.sin(a + t) * 16))
            pygame.draw.lines(surf, palette.WARRIOR_BLADE, False, pts, 3)
        return paint
    return for_angle


# name -> (frame count, painter factory, reach px)
_FRAMES = {
    "impact": (3, paint_impact, 14),
    "debris": (3, paint_debris, 20),
    "fizzle": (2, paint_fizzle, 9),
    "explosion": (4, paint_explosion, 26),
    "spores": (3, paint_spores, 54),
    "eruption": (3, paint_eruption, 44),
    "burrow": (2, paint_burrow, 6),
}

# --- Drawing -------------------------------------------------------------------------


def draw_projectiles(bank: SpriteBank, camera: Camera, projectiles: list[Projectile]) -> None:
    for p in projectiles:
        # Trail: dots at fixed distances behind the shell, only along the
        # stretch it has actually flown (none trail back into the barrel).
        for k, dist in enumerate(config.SHELL_TRAIL):
            if p.travelled >= dist:
                x, y = camera.world_to_px(p.x - p.dir_x * dist, p.y - p.dir_y * dist)
                bank.draw(bank.static(f"trail{k}", paint_trail_dot(k), 4), x, y)
        s = p.spec
        pieces = bank.rotated(
            ("shell", s.length_px, s.width_px), p.angle, config.SHELL_ANGLE_STEPS,
            paint_shell(s.length_px, s.width_px), s.length_px / 2 + 2,
        )
        bank.draw(pieces, *camera.world_to_px(p.x, p.y))


def draw_effects(
    text: TextRenderer, bank: SpriteBank, camera: Camera, world, effects: list[Effect]
) -> None:
    for e in effects:
        if e.kind == "tile_flash":
            # Redraw the hit tile's own glyph in a hot color for a moment.
            tx, ty = int(e.x), int(e.y)
            tile = world.tile_at(tx, ty)
            x, y = camera.tile_to_px(tx, ty)
            text.put_px(x, y, world.glyph_at(tx, ty), palette.TILE_FLASH_FG, tile.bg)
            continue
        if e.kind == "muzzle":
            frame = min(1, int(e.progress * 2))
            pieces = bank.rotated(
                ("muzzle", frame), e.angle, config.FLASH_ANGLE_STEPS, paint_muzzle(frame), 18
            )
        elif e.kind == "slash":
            pieces = bank.rotated(("slash",), e.angle, 36, paint_slash(), 20)
        else:
            count, factory, reach = _FRAMES[e.kind]
            frame = min(count - 1, int(e.progress * count))
            pieces = bank.static(f"{e.kind}{frame}", factory(frame), reach)
        bank.draw(pieces, *camera.world_to_px(e.x, e.y))
