"""
render/bosses.py -- bosses, their telegraphs, quest givers and the boss
banner (M17).

Readability first (design/BOSSES.md 5.3): every boss attack shows before
it lands, in glyphs that nothing else uses --
  * tongue: a blinking dotted aim line, then the tongue itself;
  * belly flop: a blinking ring where it'll land, its shadow sliding there;
  * dive: rings of ripples on the pool it'll come up from;
  * a wide-open mouth before tadpoles, bubbles, rain and rings;
  * stars over its head while it's dazed (the time to hit it).
Its psychedelic phase cycles its colors; that never touches the bullets'
readability (they keep their own bright heads).

Froggy is a 30 x 18 pixel picture at 4 screen px per pixel (6 x 3 tiles),
baked once per pose / hue / hit flash by the SpriteBank.

Quest givers are character sprites with their name above them and what
they're saying above that, on a dark strip so it reads over any ground.
"""

from __future__ import annotations

import math

import pygame

from .. import config, palette
from ..engine_ext.camera import Camera
from .ascii_fx import _Batch, _ring
from .characters import PSY_HUES, draw_character
from .sprites import SpriteBank

FROGGY_SCALE = 4
AIR_PX = 70                  # how high a leap goes at its top, px

_FROGGY = [
    "..............................",
    ".....kkkkk..........kkkkk.....",
    "....kwwwwwk........kwwwwwk....",
    "...kwwkkkwwk......kwwkkkwwk...",
    "...kwwkykwwk......kwwkykwwk...",
    "...kgwkkkwgkkkkkkkkgwkkkwgk...",
    "..kggggggggggggggggggggggggk..",
    ".kgggyggggggggggggggggggyggGk.",
    ".kggggggggggyggggggyggggggggk.",
    "kgggggggggggggggggggggggggggGk",
    "kgkkkkkkkkkkkkkkkkkkkkkkkkkkgk",
    "kggggggggggggggggggggggggggGGk",
    "kGgggwwwwwwwwwwwwwwwwwwwgggGGk",
    ".kGgwwwwwwwwwwwwwwwwwwwwwgGGk.",
    ".kGGgwwwwwwwwwwwwwwwwwwwgGGGk.",
    "kggGGkGGGGGGGGGGGGGGGGGGkGGggk",
    "kgggkk.kkkkkkkkkkkkkkkk.kkgggk",
    "kkkkk....................kkkkk",
]
_MOUTH = {10: "kgkrrrrrrrrrrrrrrrrrrrrrrrrkgk", 11: "kggkRRRRRRRRRRRRRRRRRRRRRRkGGk"}
_DAZED_EYES = {4: "...kwwkkkwwk......kwwkkkwwk..."}
_HIT_MIX = 0.65


def _froggy_art(mouth: bool, dazed: bool, hue: int | None) -> list[str]:
    rows = list(_FROGGY)
    if mouth:
        for i, r in _MOUTH.items():
            rows[i] = r
    if dazed:
        for i, r in _DAZED_EYES.items():
            rows[i] = r
    if hue is not None:
        light, dark = PSY_HUES[hue % len(PSY_HUES)]
        table = str.maketrans({"g": light, "G": dark})
        rows = [r.translate(table) for r in rows]
    return rows


def _paint_froggy(rows: list[str], hurt: bool):
    def paint(surf, to_px):
        w, h = len(rows[0]), len(rows)
        img = pygame.Surface((w, h), pygame.SRCALPHA)
        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                if ch == ".":
                    continue
                c = palette.SPRITE_COLORS[ch]
                if hurt and ch != "k":
                    c = tuple(round(v + (255 - v) * _HIT_MIX) for v in c)
                img.set_at((x, y), c)
        img = pygame.transform.scale(img, (w * FROGGY_SCALE, h * FROGGY_SCALE))
        x, y = to_px(-w * FROGGY_SCALE / 2, -h * FROGGY_SCALE / 2)
        surf.blit(img, (round(x), round(y)))
    return paint


def _paint_shadow(surf, to_px):
    (x0, y0), (x1, y1) = to_px(-48, -12), to_px(48, 12)
    pygame.draw.ellipse(surf, (10, 14, 10), pygame.Rect(round(x0), round(y0),
                                                        round(x1 - x0), round(y1 - y0)))


def draw_froggy(text, bank: SpriteBank, camera: Camera, boss) -> None:
    """The boss and its tells."""
    batch = _Batch(text)
    blink = int(boss.time * 8) % 2
    tw, th = config.TILE_PX_W, config.TILE_PX_H
    # Telegraphs on the ground first.
    if boss.landing is not None:
        lx, ly, r = boss.landing
        cx, cy = camera.world_to_px(lx, ly)
        col = palette.TELEGRAPH[blink]
        n = max(12, int(r * 6))
        for k in range(n):
            a = k * math.tau / n
            batch.put_c(cx + math.cos(a) * r * tw, cy + math.sin(a) * r * th, "o", col)
        for k in range(n // 2):
            a = k * math.tau / (n // 2) + 0.3
            batch.put_c(cx + math.cos(a) * r * 0.5 * tw, cy + math.sin(a) * r * 0.5 * th, ".", col)
    if boss.ripples is not None:
        rx, ry = boss.ripples
        cx, cy = camera.world_to_px(rx, ry)
        for i, base in enumerate((1.2, 2.6, 4.0)):
            r = base + (boss.time * 2.0) % 1.4
            col = palette.RIPPLE[(i + blink) % 2]
            n = int(8 + r * 5)
            for k in range(n):
                a = k * math.tau / n + i * 0.4
                batch.put_c(cx + math.cos(a) * r * tw, cy + math.sin(a) * r * th * 0.8,
                            "o" if i % 2 == 0 else ".", col)
    tell = boss.tell
    if tell is not None and tell[0] == "tongue":
        _, a, reach = tell
        col = palette.TELEGRAPH[blink]
        d = 1.2
        while d <= reach:
            x, y = camera.world_to_px(boss.x + math.cos(a) * d, boss.y + math.sin(a) * d)
            batch.put_c(x, y, ".", col)
            d += 0.8
        x, y = camera.world_to_px(boss.x + math.cos(a) * reach, boss.y + math.sin(a) * reach)
        batch.put_c(x, y, "x", col)
    if boss.tongue is not None:
        a, reach, _ = boss.tongue
        d = 1.0
        while d <= reach:
            x, y = camera.world_to_px(boss.x + math.cos(a) * d, boss.y + math.sin(a) * d)
            batch.put_c(x, y, "o", palette.TONGUE[0] if int(d) % 2 else palette.TONGUE[1])
            d += 0.55
        x, y = camera.world_to_px(boss.x + math.cos(a) * reach, boss.y + math.sin(a) * reach)
        batch.put_c(x, y, "@", palette.TONGUE[0])
    if boss.submerged:
        cx, cy = camera.world_to_px(boss.x, boss.y)
        for dx, dy, glyph, col in _ring(8, 18, ".", palette.RIPPLE[1], boss.time, 0.6):
            batch.put_c(cx + dx, cy + dy, glyph, col)
        batch.flush()
        return
    batch.flush()

    # The body (raised while in the air, over its shadow).
    x, y = camera.world_to_px(boss.x, boss.y)
    lift = boss.airborne * AIR_PX
    if lift > 0:
        bank.draw(bank.static("froggy_shadow", _paint_shadow, 50), x, y + 24)
    hue = int(boss.hue) % len(PSY_HUES) if boss.psychedelic else None
    mouth = boss.mouth_open or boss.tongue is not None
    dazed = boss.dazed > 0
    hurt = boss.hurt_flash > 0
    key = ("froggy", mouth, dazed, hue, hurt)
    rows = _froggy_art(mouth, dazed, hue)
    reach = max(len(rows[0]), len(rows)) * FROGGY_SCALE / 2 + 2
    bank.draw(bank.static(key, _paint_froggy(rows, hurt), reach), x, y - lift)
    if dazed:
        batch = _Batch(text)
        for k in range(3):
            a = boss.time * 4 + k * math.tau / 3
            batch.put_c(x + math.cos(a) * 26, y - lift - 46 + math.sin(a) * 6, "*",
                        palette.TOAST)
        batch.flush()


# --- Quest givers -------------------------------------------------------------------------


def draw_npc(text, bank: SpriteBank, camera: Camera, npc, hero_x: float, near: bool) -> None:
    """A quest giver: their sprite (facing the hero), name, and words."""
    x, y = camera.world_to_px(npc.x, npc.y)
    draw_character(bank, x, y - 8, npc.sprite, 3, hero_x < npc.x, 0, False)
    cw = text.display.cell_w
    name = npc.name.upper()
    text.put_px(x - len(name) * cw / 2, y - 60, name, palette.HUB_LABEL if near
                else palette.SPEECH_NAME, None)
    line = npc.line
    if line:
        s = f" {line} "
        text.put_px(x - len(s) * cw / 2, y - 60 - text.display.cell_h, s, palette.SPEECH,
                    palette.HUD_PANEL)


# --- Banner and pointer -----------------------------------------------------------------


def draw_banner(text, banner) -> None:
    """Big text across the screen (a boss waking, falling, a quest
    turning). It fades in and out at the ends."""
    from ..ui.frame import center
    d = text.display
    f = banner.t / banner.duration
    if f > 0.85:
        title, sub = palette.TOAST_DIM, palette.TOAST_DIM
    else:
        title, sub = palette.BOSS_BANNER, palette.BOSS_BANNER_SUB
    row = d.rows // 3
    spaced = " ".join(banner.title)
    if len(spaced) + 4 > d.cols:
        spaced = banner.title
    center(text, row, f"  {spaced}  ", title, bg=palette.HUD_PANEL)
    if banner.sub:
        center(text, row + 1, f"  {banner.sub}  ", sub, bg=palette.HUD_PANEL)


def _paint_pointer(angle: float, color: tuple = palette.BOSS_ARROW):
    def paint(surf, to_px):
        def pt(u, v):
            return to_px(u * math.cos(angle) - v * math.sin(angle),
                         u * math.sin(angle) + v * math.cos(angle))
        pts = [pt(10, 0), pt(-6, -7), pt(-2, 0), pt(-6, 7)]
        pygame.draw.polygon(surf, (20, 10, 8), [pt(12, 0), pt(-8, -9), pt(-3, 0), pt(-8, 9)])
        pygame.draw.polygon(surf, color, pts)
    return paint


def draw_pointer(text, bank: SpriteBank, camera: Camera, x: float, y: float,
                 label: str, size: float = 60, color: tuple = palette.BOSS_ARROW) -> None:
    """An arrow at the screen's edge toward (x, y) when it's off screen
    (no part of a body `size` px across showing), with the distance --
    where the boss is in a big arena."""
    px, py = camera.world_to_px(x, y)
    w, h = camera.view_w, camera.view_h
    margin = 40
    if -size <= px <= w + size and -size <= py <= h + size:
        return
    cx, cy = w / 2, h / 2
    dx, dy = px - cx, py - cy
    k = min((w / 2 - margin) / abs(dx) if dx else math.inf,
            (h / 2 - margin) / abs(dy) if dy else math.inf)
    ax, ay = cx + dx * k, cy + dy * k
    angle = math.atan2(dy, dx)
    step = round(angle / (math.tau / 64)) % 64      # 64 baked directions
    bank.draw(bank.static(f"boss_ptr{step}{color}", _paint_pointer(step * math.tau / 64, color), 14),
              ax, ay)
    cw = text.display.cell_w
    tx = ax - math.cos(angle) * 30 - len(label) * cw / 2
    ty = ay - math.sin(angle) * 22 - text.display.cell_h / 2
    text.put_px(tx, ty, label, color, palette.HUD_PANEL)
