"""
render/enemies_sprite.py -- drawing enemies, their tells, and health bars.

Readability rules (few, dangerous enemies must be *readable*):
  * every attack has a visible tell: the sniper's laser (brightening as the
    shot nears), the warrior's raised blade, the puffer swelling up, the
    burrower's ground cracking before it bursts out;
  * enemies are warm/grey colored, the player green;
  * a small health bar appears over any damaged enemy.
All sprites are baked shapes from render/sprites.py, drawn at pixel positions.
"""

from __future__ import annotations

import math

import pygame

from .. import config, palette
from ..ai.creatures import Burrower, Puffer, Warrior
from ..ai.vehicles import Sniper, Vehicle
from ..engine_ext.camera import Camera
from ..systems.raycast import first_hit
from .effects_sprite import _circle
from .sprites import SpriteBank, quad
from .tank_sprite import draw_tank

LASER_SEG_PX = 24


# --- Painters ---------------------------------------------------------------------------


def _paint_hp_bar(frac_steps: int, filled: int):
    def paint(surf, to_px):
        w, h = 30, 3
        (x0, y0), (x1, y1) = to_px(-w / 2, -h / 2), to_px(w / 2, h / 2)
        pygame.draw.rect(surf, palette.HP_BAR_BG, pygame.Rect(round(x0), round(y0), round(x1 - x0), round(y1 - y0)))
        fw = (x1 - x0) * filled / frac_steps
        if fw >= 1:
            pygame.draw.rect(surf, palette.HP_BAR, pygame.Rect(round(x0), round(y0), round(fw), round(y1 - y0)))
    return paint


def _paint_laser(bright: bool):
    """One segment of the sniper's aim line: 2 px, red; the bright version
    has a hot core."""
    color = palette.LASER if bright else palette.LASER_DIM

    def for_angle(a):
        def paint(surf, to_px):
            end = to_px(math.cos(a) * LASER_SEG_PX, math.sin(a) * LASER_SEG_PX)
            pygame.draw.line(surf, color, to_px(0, 0), end, 2)
            if bright:
                pygame.draw.line(surf, palette.LASER_CORE, to_px(0, 0), end, 1)
        return paint
    return for_angle


def _paint_warrior(pose: str, hurt: bool, size_px: int):
    """Top-down armored figure: shoulders, helmet with glowing eyes, and a
    blade -- held low, raised back (wind-up), or swept forward (swing).
    Drawn on a 16 px design grid, scaled to the spec's size."""
    armor = palette.TANK_COLORS["hit"]["body"] if hurt else palette.WARRIOR_ARMOR
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
    body = palette.TANK_COLORS["hit"]["body"] if hurt else palette.WORM_BODY

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
    if isinstance(e, Vehicle):
        if isinstance(e, Sniper) and e.laser_on:
            _draw_laser(bank, camera, world, e)
        draw_tank(bank, camera, e)
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
        steps = 10
        filled = max(1, round(steps * e.hp / e.max_hp))
        bank.draw(bank.static(f"hpbar{filled}", _paint_hp_bar(steps, filled), 16),
                  x, y - e.hit_radius * config.TILE_PX_H - 8)


def _draw_laser(bank: SpriteBank, camera: Camera, world, s: Sniper) -> None:
    """Sniper aim line from the barrel along the turret, stopping at the
    first wall; blinks bright in the last third of the wind-up."""
    t = s.target
    max_len = s.espec.sight if t is None else math.hypot(t.x - s.x, t.y - s.y) + 3
    ex = s.x + math.cos(s.turret_angle) * max_len
    ey = s.y + math.sin(s.turret_angle) * max_len
    hit = first_hit(world.tile_at, s.x, s.y, ex, ey)
    if hit is not None:
        ex, ey = hit.x, hit.y
    x0, y0 = camera.world_to_px(s.x, s.y)
    x1, y1 = camera.world_to_px(ex, ey)
    length = math.hypot(x1 - x0, y1 - y0)
    if length < 1:
        return
    ux, uy = (x1 - x0) / length, (y1 - y0) / length
    # Steady while aiming; blinks in the last third -- the shot is coming.
    final = s.laser >= s.espec.windup * 0.66
    bright = final and int(s.laser * 14) % 2 == 0
    pieces = bank.rotated(("laser", bright), s.turret_angle, 180, _paint_laser(bright), LASER_SEG_PX + 2)
    # Chain fixed-length baked segments end to end (each starts at its
    # sprite center); the last one may overrun the wall by < 1 segment.
    d = 0.0
    while d < length - LASER_SEG_PX / 2:
        bank.draw(pieces, x0 + ux * d, y0 + uy * d)
        d += LASER_SEG_PX
