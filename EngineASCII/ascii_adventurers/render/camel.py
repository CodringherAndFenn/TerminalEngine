"""
render/camel.py -- Ol' Spitter, the Unmannered One, his loogies, his ghost
stampede, and the camels (M23.2).

Camels are drawn top-down along their heading (baked per angle bucket by
the SpriteBank): a long body, a hump (two for Ol' Spitter, each shrinking
as he spends the spit in it), a long neck and head, four legs that walk,
and a tufted tail. Poses: "walk", "rear" (head pulled back: about to spit),
"kneel" (legs folded, head down at the trough) and "kick" (hind legs out
and flashing). A mangy camel has bald patches; a mirage and the stampede's
ghosts are see-through blue.

His tells, readable over the yard (design/BOSSES.md 5.3):
  * spitting: his head back, green drool at his mouth;
  * ricochet loogie: a green dotted line through its first bounces ("o"
    at each);
  * gallop: a red dotted line with ">" along it;
  * kick: his hind legs red, a blinking cone of "x" behind him;
  * stampede: a bellow (pulsing rings), then the ghost rows fade in;
  * mirage: a shimmer round him;
  * drinking: splashes at his mouth; stars over his head when he chokes or
    is dazed (the time to hit him).
The gallop's churned sand shows as patches of ":" until it settles.
"""

from __future__ import annotations

import math

import pygame

from .. import config, palette
from ..engine_ext.camera import Camera
from .ascii_fx import _Batch, _ring
from .sprites import SpriteBank

SPITTER_SCALE = 2.2          # his body: ~130 px nose to tail
CAMEL_SCALE = 1.2            # a mangy camel: ~70 px
MIRAGE_SCALE = 1.4           # a mirage: a smaller double of him
GHOST_SCALE = 1.3
_HUMP_STEPS = 4              # hump sizes baked (per hump)


def _paint_camel(colors: dict, scale: float, frame: int, hurt: bool, humps: tuple,
                 pose: str = "walk"):
    """A camel facing +x. `humps`: each hump's fullness 0..1 (front, back),
    or a single one; `frame`: the walk cycle's leg pose (0 / 1)."""
    def for_angle(a):
        ca, sa = math.cos(a), math.sin(a)

        def paint(surf, to_px):
            def P(u, v):
                u, v = u * scale, v * scale
                x, y = to_px(u * ca - v * sa, u * sa + v * ca)
                return round(x), round(y)

            def oval(u0, v0, ru, rv, color, n=20):
                pts = [P(u0 + math.cos(t) * ru, v0 + math.sin(t) * rv)
                       for t in (k * math.tau / n for k in range(n))]
                pygame.draw.polygon(surf, color, pts)

            def W(px):
                return max(1, round(scale * px))

            flash = palette.HIT_FLASH if hurt else None
            hide = flash or colors["hide"]
            shade = flash or colors["shade"]
            edge = colors["edge"]
            kneel = pose == "kneel"
            # A shadow on the ground (lower and smaller when kneeling).
            if "shadow" in colors:
                oval(-1, 3, 21 if not kneel else 18, 9, colors["shadow"])
            # Legs: long and pale, front pair and hind pair, alternating
            # with the walk frame; folded under when kneeling.
            for side in (-1, 1):
                for k, u0 in enumerate((11, -12)):
                    hind = k == 1
                    col = colors["leg"]
                    if kneel:
                        knee, foot = P(u0 + 3, side * 8.5), P(u0 - 2, side * 9)
                    elif pose == "kick" and hind:
                        col = palette.KICK_TELL[0]
                        knee, foot = P(u0 - 7, side * 7), P(u0 - 17, side * 6.5)
                    else:
                        # Striding along the body (from above a camel's legs
                        # swing fore and aft, peeking out past its sides).
                        step = 5.0 if (k + frame + (side > 0)) % 2 else -5.0
                        knee = P(u0 + step * 0.6, side * 8.2)
                        foot = P(u0 + step * 1.3, side * 9.2)
                    root = P(u0, side * 5.5)
                    pygame.draw.line(surf, edge, root, knee, W(2.6))
                    pygame.draw.line(surf, edge, knee, foot, W(2.6))
                    pygame.draw.line(surf, col, root, knee, W(1.5))
                    pygame.draw.line(surf, col, knee, foot, W(1.5))
                    pygame.draw.circle(surf, edge, foot, W(1.6))
            # Tail with a tuft.
            pygame.draw.line(surf, edge, P(-17, 0), P(-23, 2), W(1.4))
            pygame.draw.circle(surf, edge, P(-24, 2.5), W(1.6))
            # Body: long and narrow.
            oval(0, 0, 19, 7.5, edge)
            oval(0, 0, 18, 6.6, hide)
            oval(-1, 2.5, 16, 3.2, shade)                   # its shaded flank
            oval(0, -0.6, 17, 5.2, hide)
            for pu, pv, pr in colors.get("patches", ()):    # a mangy camel's bald patches
                oval(pu, pv, pr, pr * 0.8, colors["patch"], 10)
            # Ol' Spitter's saddle blanket, between his humps.
            if "blanket" in colors and len(humps) == 2:
                for v0 in (-7.6, 7.6):
                    for t in range(-3, 4):
                        pygame.draw.line(surf, colors["fringe"], P(t * 1.3 - 0.5, v0 * 0.86),
                                         P(t * 1.3 - 0.5, v0 * 1.05), W(0.8))
                oval(-0.5, 0, 4.2, 7.4, flash or colors["blanket"], 12)
                pygame.draw.line(surf, colors["fringe"], P(-0.5, -6.6), P(-0.5, 6.6), W(1.0))
            # Humps: mounds lit from the top left, sagging flat as they empty.
            spots = (6, -7) if len(humps) == 2 else (-1,)
            for u0, full in zip(spots, humps):
                r = 2.4 + 3.8 * full
                oval(u0, 0.4, r + 1.2, r * 0.9 + 1.0, edge)
                oval(u0, 0.4, r + 0.4, r * 0.9 + 0.3, shade)
                oval(u0 - r * 0.15, -r * 0.12, r * 0.8, r * 0.72, hide)
                if full > 0.15:
                    oval(u0 - r * 0.35, -r * 0.35, r * 0.4, r * 0.32, flash or colors["shine"], 10)
            # Neck and head (pulled back when rearing, down when kneeling).
            head_u = {"rear": 24, "kneel": 28}.get(pose, 32)
            neck0 = 15
            pygame.draw.line(surf, edge, P(neck0, 0), P(head_u - 4, 0), W(5.5))
            pygame.draw.line(surf, hide, P(neck0, 0), P(head_u - 4, 0), W(4.0))
            oval(head_u, 0, 7, 4.4, edge)
            oval(head_u, 0, 6.2, 3.7, hide)
            oval(head_u + 5.2, 0, 3.0, 3.2, edge, 12)       # drooping lips
            oval(head_u + 5.0, 0, 2.4, 2.6, flash or colors["muzzle"], 12)
            for side in (-1, 1):
                pygame.draw.line(surf, edge, P(head_u - 4, side * 3), P(head_u - 7, side * 5.5),
                                 W(1.4))
                pygame.draw.circle(surf, colors["eye"], P(head_u + 1, side * 2.4), W(1.0))
        return paint
    return for_angle


def _q(f: float) -> float:
    """A hump's fullness, rounded to the sizes that get baked."""
    return round(max(0.0, min(1.0, f)) * _HUMP_STEPS) / _HUMP_STEPS


_MANGY = dict(palette.MANGY_CAMEL, patches=((-6, 3, 2.6), (7, -3.5, 2.0), (-12, -2, 1.8)))


def draw_camel(text, bank: SpriteBank, camera: Camera, e) -> None:
    """A mangy camel or a mirage: one hump, head back and drooling while
    it's about to spit."""
    x, y = camera.world_to_px(e.x, e.y)
    mirage = getattr(e, "kind_key", "") == "mirage"
    pose = "rear" if e.rear > 0 else "walk"
    frame = int(e.phase) % 2
    hurt = e.hurt_flash > 0
    colors = palette.MIRAGE_CAMEL if mirage else _MANGY
    scale = MIRAGE_SCALE if mirage else CAMEL_SCALE
    humps = (0.8, 0.8) if mirage else (0.8,)
    sprite = bank.rotated(("camel", mirage, pose, frame, hurt), e.facing, 32,
                          _paint_camel(colors, scale, frame, hurt, humps, pose), 40 * scale)
    bank.draw(sprite, x, y)
    if e.rear > 0:
        batch = _Batch(text)
        d = e.hit_radius * config.TILE_PX_W * 0.9
        blink = int(e.rear * 12) % 2
        batch.put_c(x + math.cos(e.facing) * d, y + math.sin(e.facing) * d * 0.8 + 4, ",",
                    palette.SPITTER_TELL[blink])
        batch.flush()


def _paint_loogie(r_px: float):
    body, dark, shine = palette.LOOGIE

    def paint(surf, to_px):
        cx, cy = to_px(0, 0)
        c = (round(cx), round(cy))
        pygame.draw.circle(surf, dark, c, max(2, round(r_px)))
        pygame.draw.circle(surf, body, c, max(1, round(r_px - 2)))
        pygame.draw.circle(surf, shine, (round(cx - r_px * 0.35), round(cy - r_px * 0.35)),
                           max(1, round(r_px * 0.25)))
    return paint


def _dotted(batch, camera, x0, y0, x1, y1, col, mark: str | None = None, every: int = 4,
            step: float = 0.9) -> None:
    length = math.hypot(x1 - x0, y1 - y0)
    d = 0.6
    k = 0
    while d < length:
        f = d / length
        px, py = camera.world_to_px(x0 + (x1 - x0) * f, y0 + (y1 - y0) * f)
        batch.put_c(px, py, mark if mark and k % every == 0 else ".", col)
        d += step
        k += 1


def draw_ol_spitter(text, bank: SpriteBank, camera: Camera, boss) -> None:
    """Ol' Spitter, everything he's left about, and his tells."""
    batch = _Batch(text)
    blink = int(boss.time * 8) % 2
    tw = config.TILE_PX_W
    tell = boss.tell
    kind = tell[0] if tell is not None else None
    # On the ground: churned sand, aim lines, the kick's cone.
    radius, life, *_ = config.SPITTER_TRAIL
    for cx_, cy_, age in boss.trail:
        px, py = camera.world_to_px(cx_, cy_)
        col = palette.HOT_SAND[0 if age < life * 0.6 else 1]
        for dx, dy, glyph, c in _ring(6, radius * tw * 0.7, ":", col, cx_ + age):
            batch.put_c(px + dx, py + dy * 0.6, glyph, c)
        batch.put_c(px, py, ":", col)
    if kind == "gallop":
        x0, y0, x1, y1 = tell[1:5]
        _dotted(batch, camera, x0, y0, x1, y1, palette.KICK_TELL[blink], ">")
        px, py = camera.world_to_px(x1, y1)
        batch.put_c(px, py, "x", palette.KICK_TELL[blink])
    elif kind == "loogie":
        pts = tell[1]
        col = palette.SPITTER_TELL[blink]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            _dotted(batch, camera, x0, y0, x1, y1, col)
        for x, y in pts[1:-1]:
            px, py = camera.world_to_px(x, y)
            batch.put_c(px, py, "o", col)
    elif kind == "kick":
        _, reach, half, *_ = config.SPITTER_KICK
        back = boss.facing + math.pi
        col = palette.KICK_TELL[blink]
        for k in range(5):
            a = back + math.radians(half) * (k / 2 - 1)
            for d in (boss.hit_radius + 1.5, boss.hit_radius + reach * 0.6,
                      boss.hit_radius + reach):
                px, py = camera.world_to_px(boss.x + math.cos(a) * d, boss.y + math.sin(a) * d)
                batch.put_c(px, py, "x", col)
    batch.flush()

    # The stampede's ghosts.
    for g in boss.ghosts:
        px, py = camera.world_to_px(g[0], g[1])
        if g[4] < 0.15:
            batch = _Batch(text)
            batch.put_c(px, py, ".", palette.GHOST_CAMEL["shine"][:3])
            batch.flush()
            continue
        a = math.atan2(g[3], g[2])
        frame = int(g[4] * 8) % 2
        sprite = bank.rotated(("ghost_camel", frame), a, 32,
                              _paint_camel(palette.GHOST_CAMEL, GHOST_SCALE, frame, False,
                                           (0.7, 0.7)), 40 * GHOST_SCALE)
        bank.draw(sprite, px, py)

    # Him.
    x, y = camera.world_to_px(boss.x, boss.y)
    if boss.kneeling or (boss.dazed > 0 and boss.move == "drink"):
        pose = "kneel"
    elif boss.kicking:
        pose = "kick"
    elif boss.rear:
        pose = "rear"
    else:
        pose = "walk"
    frame = int(boss.legs) % 2
    hurt = boss.hurt_flash > 0
    front, back = (_q(f) for f in boss.hump_frac)
    sprite = bank.rotated(("ol_spitter", pose, frame, hurt, front, back), boss.facing, 32,
                          _paint_camel(palette.OL_SPITTER, SPITTER_SCALE, frame, hurt,
                                       (front, back), pose), 40 * SPITTER_SCALE)
    bank.draw(sprite, x, y)

    # His loogies (over him: they fly from his mouth).
    for g in boss.loogies:
        r_px = round(g[4] * tw * 0.8)
        px, py = camera.world_to_px(g[0], g[1])
        bank.draw(bank.static(f"loogie{r_px}", _paint_loogie(r_px), r_px + 2), px, py)

    batch = _Batch(text)
    mx, my = camera.world_to_px(*boss.mouth)
    if boss.rear:
        batch.put_c(mx, my + 6, ",", palette.SPITTER_TELL[blink])
        batch.put_c(mx + 3, my + 14, ".", palette.SPITTER_TELL[1 - blink])
    if kind == "drink":
        for dx, dy, glyph, c in _ring(6, 14 + 6 * blink, "o", palette.DRINK_SPLASH[blink],
                                      boss.time * 3):
            batch.put_c(mx + dx, my + dy * 0.6, glyph, c)
    elif kind == "bellow":
        r = 50 + (boss.time * 90) % 40
        for dx, dy, glyph, c in _ring(16, r, "O", palette.KICK_TELL[blink], boss.time):
            batch.put_c(x + dx, y + dy * 0.7, glyph, c)
    elif kind == "shimmer":
        for dx, dy, glyph, c in _ring(14, 70, "'", palette.MIRAGE_CAMEL["shine"][:3],
                                      boss.time * 4):
            batch.put_c(x + dx, y + dy * 0.6 + math.sin(boss.time * 9 + dx) * 4, glyph, c)
    if boss.dazed > 0:
        for k in range(3):
            a = boss.time * 4 + k * math.tau / 3
            batch.put_c(x + math.cos(a) * 30, y - 56 + math.sin(a) * 6, "*", palette.TOAST)
    batch.flush()
