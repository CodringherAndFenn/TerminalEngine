"""
render/mosquito.py -- Lady Proboscia, her mosquitoes, and the smoke
keeper's braziers (M22.2).

A mosquito is drawn top-down along its heading (baked per angle bucket by
the SpriteBank): a striped thorax and legs, translucent beating wings, a
long proboscis and an abdomen that swells and reddens with each gulp of
blood. The Lady flies: she's drawn above her shadow, low only while she
sips at a pool or lies stunned after a pop.

Her tells, in the telegraph red nothing else uses (design/BOSSES.md 5.3):
  * bite: a dotted line along the dive, an "x" where it ends;
  * needles: a ring of dots closing on her as her proboscis heats up;
  * buzz: "z"s spinning round her (the rings of pulses then hang a moment
    before they close -- that's their own tell);
  * call: a pulsing ring;
  * engorged: her belly blinks, with a bar under her -- how close she is
    to popping;
  * fever clouds: patches of sickly green on the ground, fading out.

Braziers: a cold one is a tile (world/tiles.BRAZIER); one being lit shows
its heat as a bar above it, and a lit one smokes for good.
"""

from __future__ import annotations

import math

import pygame

from .. import config, palette
from ..engine_ext.camera import Camera
from .ascii_fx import _Batch, _ring
from .sprites import SpriteBank

LADY_SCALE = 1.3             # her body: ~100 px nose to tail
BROOD_SCALE = 0.32
LIFT_PX = 26                 # how high she flies over her shadow
_C = palette.MOSQUITO


def _paint_mosquito(scale: float, belly: int, glow: bool, hurt: bool, flap: int, low: bool):
    """A mosquito facing +x (rotated per bucket). `belly`: gulps of blood
    (0..ENGORGE_FULL), `glow`: engorged and blinking, `flap`: wing frame,
    `low`: on the ground (wings folded back)."""
    def for_angle(a):
        ca, sa = math.cos(a), math.sin(a)

        def paint(surf, to_px):
            def P(u, v):
                u, v = u * scale, v * scale
                x, y = to_px(u * ca - v * sa, u * sa + v * ca)
                return round(x), round(y)

            def oval(u0, v0, ru, rv, color, n=14):
                pts = [P(u0 + math.cos(t) * ru, v0 + math.sin(t) * rv)
                       for t in (k * math.tau / n for k in range(n))]
                pygame.draw.polygon(surf, color, pts)

            body = palette.HIT_FLASH if hurt else _C["body"]
            stripe = palette.HIT_FLASH if hurt else _C["stripe"]
            # Legs: three pairs, bent, striped (black and white, like the
            # real thing).
            for side in (-1, 1):
                for u0, out, back in ((8, 14, 10), (2, 18, -2), (-4, 16, -16)):
                    knee = P(u0 + back * 0.5, side * out)
                    foot = P(u0 + back, side * (out + 8))
                    root = P(u0, side * 3)
                    pygame.draw.line(surf, body, root, knee, max(1, round(scale)))
                    pygame.draw.line(surf, stripe, knee, foot, max(1, round(scale)))
            # Wings (translucent, beating unless she's down).
            if scale > 0.5 or not low:
                spread = 0.25 if low else (0.55 if flap else 0.95)
                for side in (-1, 1):
                    tip_a = math.pi - spread
                    u1, v1 = 4 + math.cos(tip_a) * 30, side * math.sin(tip_a) * 30
                    pts = [P(4, side * 2), P(4 + math.cos(tip_a - 0.25) * 22,
                                             side * math.sin(tip_a - 0.25) * 22),
                           P(u1, v1), P(4 + math.cos(tip_a + 0.3) * 18,
                                        side * math.sin(tip_a + 0.3) * 18)]
                    pygame.draw.polygon(surf, _C["wing"], pts)
                    pygame.draw.lines(surf, _C["wing_edge"], True, pts, 1)
            # Abdomen: swells and reddens with each gulp.
            k = max(0, min(belly, len(_C["belly"]) - 1))
            belly_c = _C["glow"] if glow else _C["belly"][k]
            if hurt:
                belly_c = palette.HIT_FLASH
            oval(-14 - belly * 2.5, 0, 13 + belly * 3.5, 6 + belly * 2.6, body)
            oval(-14 - belly * 2.5, 0, 11 + belly * 3.5, 4.5 + belly * 2.6, belly_c)
            for s in range(3):                      # segment stripes
                u = -8 - s * (5 + belly * 1.6)
                pygame.draw.line(surf, stripe if belly == 0 else body,
                                 P(u, -3 - belly * 1.5), P(u, 3 + belly * 1.5), 1)
            # Thorax and head.
            oval(4, 0, 7, 6, body)
            pygame.draw.line(surf, stripe, P(1, 0), P(8, 0), 1)
            oval(12, 0, 4, 4, body)
            for side in (-1, 1):
                pygame.draw.circle(surf, _C["eye"], P(13, side * 2.5), max(1, round(1.5 * scale)))
            # Proboscis.
            pygame.draw.line(surf, _C["nose"], P(15, 0), P(36, 0), max(1, round(1.5 * scale)))
        return paint
    return for_angle


def _paint_shadow(rx: float, ry: float):
    def paint(surf, to_px):
        (x0, y0), (x1, y1) = to_px(-rx, -ry), to_px(rx, ry)
        pygame.draw.ellipse(surf, (14, 16, 10), pygame.Rect(round(x0), round(y0),
                                                            round(x1 - x0), round(y1 - y0)))
    return paint


def _sprite(bank: SpriteBank, key: str, facing: float, scale: float, belly: int, glow: bool,
            hurt: bool, flap: int, low: bool):
    reach = 40 * scale + 4
    return bank.rotated((key, belly, glow, hurt, flap, low), facing, 32,
                        _paint_mosquito(scale, belly, glow, hurt, flap, low), reach)


def draw_mosquito(bank: SpriteBank, camera: Camera, e) -> None:
    """One of the brood (hovering still -- wings blurred -- before a sting)."""
    x, y = camera.world_to_px(e.x, e.y)
    flap = int(e.phase * 2) % 2 if e.windup <= 0 else int(e.phase * 5) % 2
    bank.draw(_sprite(bank, "mosq", e.facing, BROOD_SCALE, 0, False, e.hurt_flash > 0, flap,
                      False), x, y - 6)


def draw_proboscia(text, bank: SpriteBank, camera: Camera, boss) -> None:
    """The Lady, her shadow, her tells, and her fever clouds."""
    batch = _Batch(text)
    blink = int(boss.time * 8) % 2
    tw, th = config.TILE_PX_W, config.TILE_PX_H
    # Fever clouds on the ground.
    if boss.clouds:
        radius, life = config.FEVER_CLOUD[0], config.FEVER_CLOUD[1]
        for i, (cx, cy, age) in enumerate(boss.clouds):
            px, py = camera.world_to_px(cx, cy)
            fade = age / life
            col = palette.FEVER[0 if fade < 0.7 else 1]
            n = 9
            for k in range(n):
                a = k * math.tau / n + i * 0.7 + boss.time * 0.6
                r = radius * (0.35 + 0.55 * ((k * 37 + i) % 5) / 4)
                batch.put_c(px + math.cos(a) * r * tw, py + math.sin(a) * r * th * 0.8,
                            "░" if (k + blink) % 3 else "o", col)
    tell = boss.tell
    if tell is not None and tell[0] == "bite":
        _, x0, y0, x1, y1 = tell
        col = palette.MOSQUITO_TELL[blink]
        length = math.hypot(x1 - x0, y1 - y0)
        d = 1.5
        while d < length:
            f = d / length
            px, py = camera.world_to_px(x0 + (x1 - x0) * f, y0 + (y1 - y0) * f)
            batch.put_c(px, py, ">" if int(d) % 4 == 0 else ".", col)
            d += 0.8
        px, py = camera.world_to_px(x1, y1)
        batch.put_c(px, py, "x", col)
    batch.flush()

    x, y = camera.world_to_px(boss.x, boss.y)
    low = boss.grounded
    lift = 4 if low else LIFT_PX + math.sin(boss.time * 3.0) * 3
    if not low:
        bank.draw(bank.static("lady_shadow", _paint_shadow(34, 11), 38), x, y + 8)
    glow = boss.engorged > 0 and blink == 1
    flap = int(boss.wings) % 2
    bank.draw(_sprite(bank, "lady", boss.facing, LADY_SCALE, boss.belly, glow,
                      boss.hurt_flash > 0, flap, low), x, y - lift)

    batch = _Batch(text)
    if tell is not None and tell[0] == "needle":
        col = palette.MOSQUITO_TELL[blink]
        r = 16 + 30 * (1 - (boss.time * 2.0) % 1.0)
        for dx, dy, glyph, c in _ring(10, r, ".", col, boss.time * 2):
            batch.put_c(x + dx, y - lift + dy * 0.8, glyph, c)
        nx, ny = camera.world_to_px(*boss.nose)
        batch.put_c(nx, ny - lift, "*", palette.MOSQUITO["nose_hot"])
    elif tell is not None and tell[0] == "buzz":
        for dx, dy, glyph, c in _ring(6, 40, "z", palette.SHOT_BUZZ[0], boss.time * 5):
            batch.put_c(x + dx, y - lift + dy * 0.6, glyph, c)
    elif tell is not None and tell[0] == "call":
        r = 24 + (boss.time * 70) % 30
        for dx, dy, glyph, c in _ring(14, r, "o", palette.MOSQUITO_TELL[blink], boss.time):
            batch.put_c(x + dx, y - lift + dy * 0.8, glyph, c)
    if boss.engorged > 0:
        # How close she is to popping, under her.
        width = 12
        filled = round(boss.pop_frac * width)
        cw = text.display.cell_w
        bx = x - (width + 2) * cw / 2
        by = y + 26
        batch.put_px(bx, by, "[", palette.POP_BAR[0], palette.HUD_PANEL)
        batch.put_px(bx + cw, by, "█" * filled, palette.POP_BAR[0], palette.HUD_PANEL)
        if width - filled:
            batch.put_px(bx + (1 + filled) * cw, by, "░" * (width - filled), palette.POP_BAR[1],
                         palette.HUD_PANEL)
        batch.put_px(bx + (1 + width) * cw, by, "]", palette.POP_BAR[0], palette.HUD_PANEL)
    if boss.dazed > 0:
        for k in range(3):
            a = boss.time * 4 + k * math.tau / 3
            batch.put_c(x + math.cos(a) * 22, y - lift - 30 + math.sin(a) * 5, "*", palette.TOAST)
    batch.flush()


# --- The smoke keeper's braziers ----------------------------------------------------------


def draw_braziers(text, camera: Camera, quests, time: float) -> None:
    """Smoke over the lit braziers; the heat of one being lit as a bar."""
    batch = _Batch(text)
    x0, y0 = camera.canvas_to_world(0, 0)
    x1, y1 = camera.canvas_to_world(camera.view_w, camera.view_h)
    cw = text.display.cell_w
    for s in quests.states.values():
        if s.spec.kind != "light" or s.stage == "offered":
            continue
        for i, (bx, by) in enumerate(s.camp.spots):
            if not (x0 - 4 <= bx <= x1 + 4 and y0 - 8 <= by <= y1 + 4):
                continue
            px, py = camera.world_to_px(bx, by)
            if i in s.lit:
                # A column of smoke drifting up and off to one side.
                for k in range(9):
                    f = (time * 0.5 + k / 9) % 1.0
                    sx = px + math.sin(f * 5 + i) * 6 + f * 14
                    sy = py - 14 - f * 70
                    col = palette.SMOKE[min(2, int(f * 3))]
                    batch.put_c(sx, sy, "o" if f < 0.4 else ".", col)
                batch.put_c(px, py - 12, "*", palette.FLAME[int(time * 6 + i) % 2])
                continue
            heat = s.heat.get(i, 0.0)
            if heat <= 0:
                continue
            frac = min(1.0, heat / config.BRAZIER_LIGHT_TIME)
            width = 8
            filled = round(frac * width)
            left = px - (width + 2) * cw / 2
            top = py - 40
            batch.put_px(left, top, "[" + "█" * filled, palette.HEAT_BAR[0], palette.HUD_PANEL)
            batch.put_px(left + (1 + filled) * cw, top, "░" * (width - filled) + "]",
                         palette.HEAT_BAR[1], palette.HUD_PANEL)
            if int(time * 10) % 2:
                batch.put_c(px + math.sin(time * 9) * 5, py - 14, "'", palette.FLAME[1])
    batch.flush()
