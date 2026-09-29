"""
render/enemies_sprite.py -- drawing enemies, their tells, and health bars.

Readability rules (few, dangerous enemies must be *readable*):
  * every attack has a visible tell: the warlock's aiming beam (flickering
    as the hex nears), the warrior's raised blade, the puffer swelling up,
    the burrower's ground cracking before it bursts out;
  * a small "==--" health bar appears over any damaged enemy.
Shooting enemies are pixel-art characters (render/characters.py); the
creatures are shapes baked by render/sprites.py; tells and bars are glyphs
(render/ascii_fx.py). Everything is drawn at pixel positions.
"""

from __future__ import annotations

import math

import pygame

from .. import config, palette
from ..ai.creatures import Burrower, Puffer, Warrior
from ..ai.shooters import Shooter, Warlock
from ..engine_ext.camera import Camera
from .ascii_fx import draw_beam, draw_hp_bar
from .characters import draw_body
from .sprites import SpriteBank, quad


def _circle(surf, to_px, color, x, y, r, width=0):
    (x0, y0), (x1, y1) = to_px(x - r, y - r), to_px(x + r, y + r)
    rect = pygame.Rect(round(x0), round(y0), max(1, round(x1 - x0)), max(1, round(y1 - y0)))
    pygame.draw.ellipse(surf, color, rect, width)


# --- Painters ---------------------------------------------------------------------------


def _paint_warrior(pose: str, hurt: bool, size_px: int):
    """Top-down armored figure: shoulders, helmet with glowing eyes, and a
    blade -- held low, raised back (wind-up), or swept forward (swing).
    Drawn on a 16 px design grid, scaled to the spec's size."""
    armor = palette.HIT_FLASH if hurt else palette.WARRIOR_ARMOR
    k = size_px / 16

    def for_angle(a):
        def paint(surf, to_px_raw):
            def to_px(u, v):
                return to_px_raw(u * k, v * k)

            def rot(u, v):
                return (u * math.cos(a) - v * math.sin(a), u * math.sin(a) + v * math.cos(a))

            pygame.draw.polygon(surf, palette.WARRIOR_DARK, quad(to_px, a, -5, 4, -9, 9))
            pygame.draw.polygon(surf, armor, quad(to_px, a, -4, 3, -8, 8))
            _circle(surf, to_px, palette.WARRIOR_DARK, *rot(1, 0), 5)
            _circle(surf, to_px, armor, *rot(1, 0), 4)
            for v in (-2, 2):
                _circle(surf, to_px, palette.WARRIOR_EYES, *rot(4, v), 1)
            if pose == "windup":      # blade raised back over the shoulder
                p0, p1 = rot(-2, 8), rot(-14, 12)
            elif pose == "swing":     # blade swept out in front
                p0, p1 = rot(3, 8), rot(17, -4)
            else:                     # held at the side, pointing ahead
                p0, p1 = rot(0, 9), rot(13, 10)
            pygame.draw.line(surf, palette.WARRIOR_BLADE, to_px(*p0), to_px(*p1), 2)
        return paint
    return for_angle


def _paint_puffer(swell_step: int):
    """A round spotted fungus; bigger and paler as it swells to burst."""
    r = 6 + swell_step * 2.2

    def paint(surf, to_px):
        _circle(surf, to_px, palette.PUFFER_DARK, 0, 0, r + 1)
        _circle(surf, to_px, palette.PUFFER_BODY if swell_step < 3 else palette.PUFFER_SPOTS, 0, 0, r)
        for k in range(5):
            a = k * math.tau / 5
            _circle(surf, to_px, palette.PUFFER_SPOTS, math.cos(a) * r * 0.5, math.sin(a) * r * 0.5, 1.5)
    return paint


def _paint_mound(frame: int):
    """What you see of a burrower underground: a moving hump of sand."""
    def paint(surf, to_px):
        c0, c1 = palette.BURROW_DUST
        for dx, dy, r in ((-3, 1, 5), (3, -1, 5), (0, 0, 6)):
            _circle(surf, to_px, c1 if frame else c0, dx, dy, r)
        _circle(surf, to_px, c0 if frame else c1, 1, -1, 3)
    return paint


def _paint_rumble(frame: int):
    """The ground cracking open: the burrower is about to burst out here."""
    def paint(surf, to_px):
        r = 12 + frame * 5
        c0, c1 = palette.BURROW_DUST
        _circle(surf, to_px, c1, 0, 0, r, 2)
        for k in range(6):
            a = k * math.tau / 6 + frame * 0.4
            pygame.draw.line(surf, c0, to_px(math.cos(a) * 4, math.sin(a) * 4),
                             to_px(math.cos(a) * (r - 1), math.sin(a) * (r - 1)))
    return paint


def _paint_worm(hurt: bool):
    """Surfaced burrower: a segmented worm head rearing out of a hole, jaws
    toward its target."""
    body = palette.HIT_FLASH if hurt else palette.WORM_BODY

    def for_angle(a):
        def paint(surf, to_px):
            def rot(u, v):
                return (u * math.cos(a) - v * math.sin(a), u * math.sin(a) + v * math.cos(a))
            _circle(surf, to_px, palette.BURROW_DUST[1], 0, 0, 13)          # the hole
            for u, r in ((-6, 7), (0, 8), (6, 7)):
                _circle(surf, to_px, palette.WORM_DARK, *rot(u, 0), r + 1)
                _circle(surf, to_px, body, *rot(u, 0), r)
            for v in (-4, 4):                                               # jaws
                pygame.draw.line(surf, palette.WORM_MOUTH, to_px(*rot(10, v * 0.6)),
                                 to_px(*rot(16, v * 1.4)), 2)
        return paint
    return for_angle


# --- Drawing ----------------------------------------------------------------------------


def draw_enemy(text, bank: SpriteBank, camera: Camera, world, e) -> None:
    x, y = camera.world_to_px(e.x, e.y)
    if isinstance(e, Shooter):
        if isinstance(e, Warlock) and e.beam_on:
            draw_beam(text, camera, world, e)
        draw_body(bank, camera, e)
    elif isinstance(e, Warrior):
        pose = "windup" if e.windup > 0 else "swing" if e.swing > 0 else "idle"
        size = e.espec.size_px
        pieces = bank.rotated(("warrior", pose, e.hurt_flash > 0, size), e.facing, 72,
                              _paint_warrior(pose, e.hurt_flash > 0, size), 20 * size / 16)
        bank.draw(pieces, x, y)
    elif isinstance(e, Puffer):
        step = min(3, int(e.swelling * 4))
        bob = math.sin(e.phase * 1.7) * 2
        bank.draw(bank.static(f"puffer{step}", _paint_puffer(step), 16), x, y + bob)
    elif isinstance(e, Burrower):
        if e.state == "under":
            frame = int((e.x + e.y) * 3) % 2   # the hump shimmers as it moves
            bank.draw(bank.static(f"mound{frame}", _paint_mound(frame), 9), x, y)
        elif e.state == "rumble":
            frame = min(2, int((1 - e.timer / e.espec.windup) * 3))
            bank.draw(bank.static(f"rumble{frame}", _paint_rumble(frame), 24), x, y)
        else:
            pieces = bank.rotated(("worm", e.hurt_flash > 0), e.facing, 36,
                                  _paint_worm(e.hurt_flash > 0), 18)
            bank.draw(pieces, x, y)
    if e.hp < e.max_hp and e.hittable:
        top = e.spec.sprite_scale * 9 if isinstance(e, Shooter) else e.hit_radius * config.TILE_PX_H
        draw_hp_bar(text, x, y - top - 6, e.hp / e.max_hp)
