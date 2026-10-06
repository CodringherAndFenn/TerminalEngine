"""
render/fragile.py -- Fragile, The Misunderstood: the sun through her
shutters, her three forms, her tells, her mist and bass-axe, the
chandeliers, the ballroom's markers and the metronome, her bats and
thralls, and Mr. Buttons carried and dropped (M24.3).

She's a character picture (render/characters.ART["fragile"], drawn big),
or the wolf picture, or a cloud of bats. Her tells, in her own red
(design/BOSSES.md 5.3):
  * strum (riff): notes circling her; axe: the axe raised over her;
  * gaze: a red wedge, then the cone itself;
  * mist step: a shimmer where she'll appear; swoop/charge: a dotted
    line (">" for the wolf);
  * coffins creaking; chandelier shadows; a window flashing before she
    slams it; a screech or a howl (rings); a shift (her outline flickers).
Markers: OPEN over each closed shutter's lever (with a bar while pulled),
STAKE over unstaked coffins, the sun shafts themselves, an arrow to the
nearest closed lever while she's near you, and in phase 3 a metronome
across the bottom of the screen that flashes on every beat.
"""

from __future__ import annotations

import math

import pygame

from .. import config, palette
from ..engine_ext.camera import Camera
from .ascii_fx import _Batch, _ring
from .characters import draw_character
from .fallout import _bar, _hash01, _nearest
from .magus import _dotted, _px_ring
from .sprites import SpriteBank

SCALE = 5


def _paint_axe(spin: int):
    def paint(surf, to_px):
        cx, cy = to_px(0, 0)
        a = spin * math.pi / 4
        ca, sa = math.cos(a), math.sin(a)
        pts = [(cx + ca * 14, cy + sa * 14), (cx - ca * 14, cy - sa * 14)]
        pygame.draw.line(surf, (140, 30, 40), *[(round(x), round(y)) for x, y in pts], 4)
        hx, hy = cx + ca * 12, cy + sa * 12
        pygame.draw.circle(surf, (210, 40, 60), (round(hx), round(hy)), 6)
        pygame.draw.circle(surf, (240, 200, 200), (round(hx), round(hy)), 2)
    return paint


def draw_fragile(text, bank: SpriteBank, camera: Camera, boss) -> None:
    batch = _Batch(text)
    blink = int(boss.time * 8) % 2
    x0, y0 = camera.canvas_to_world(0, 0)
    x1, y1 = camera.canvas_to_world(camera.view_w, camera.view_h)
    # The sun: each open shaft as warm glyphs across the floor.
    w = config.SHAFT_WIDTH
    for i in boss.open:
        sx0, sy0, sx1, sy1 = boss.shaft(i)
        length = math.hypot(sx1 - sx0, sy1 - sy0)
        ux, uy = (sx1 - sx0) / length, (sy1 - sy0) / length
        nx, ny = -uy, ux
        d = 0.5
        k = 0
        while d < length:
            for s_ in (-w / 2, -w / 4, 0.0, w / 4, w / 2):
                x, y = sx0 + ux * d + nx * s_, sy0 + uy * d + ny * s_
                if x0 - 1 <= x <= x1 + 1 and y0 - 1 <= y <= y1 + 1:
                    px, py = camera.world_to_px(x, y)
                    edge = abs(s_) == w / 2
                    batch.put_c(px, py, "|" if edge else ("/" if (k + int(s_ * 4)) % 3 else "."),
                                palette.SUN[0 if edge else 1])
            d += 1.3
            k += 1
    for mx, my, age in boss.mist:
        _px_ring(batch, camera, mx, my, config.FRAGILE_MIST[5], 10, "%", palette.MIST[age > 2.0],
                 age)
    # Chandeliers overhead (and their shadows before they fall).
    for i, (cx, cy) in enumerate(boss.props.get("chandeliers", [])):
        if i in boss.fallen:
            continue
        px, py = camera.world_to_px(cx, cy)
        batch.put_c(px, py - 30, "\\*/", palette.CHANDELIER_FG)
    for cx, cy in boss.shadows:
        _px_ring(batch, camera, cx, cy, config.FRAGILE_CHANDELIER[1], 16, "o",
                 palette.TELEGRAPH[blink])
    tell = boss.tell
    kind = tell[0] if tell is not None else None
    if kind == "wedge":
        _, a0, cone, reach = tell
        for k in range(7):
            a = a0 + cone * (k / 6 - 0.5)
            _dotted(batch, camera, boss.x, boss.y, boss.x + math.cos(a) * reach,
                    boss.y + math.sin(a) * reach, palette.GAZE[blink], step=1.4)
    elif kind in ("swoop", "charge"):
        _dotted(batch, camera, *tell[1:5], palette.FRAGILE_TELL[blink],
                mark=">" if kind == "charge" else None)
    elif kind == "mist":
        px, py = camera.world_to_px(tell[1], tell[2])
        for dx, dy, glyph, c in _ring(10, 28, "%", palette.MIST[0], boss.time * 5):
            batch.put_c(px + dx, py + dy, glyph, c)
    elif kind == "creak":
        for cx, cy in tell[1]:
            px, py = camera.world_to_px(cx, cy)
            batch.put_c(px + math.sin(boss.time * 40) * 3, py - 18, "!!", palette.FRAGILE_TELL[blink])
    elif kind == "slam":
        px, py = camera.world_to_px(tell[1], tell[2])
        batch.put_c(px, py + 20, "SLAM!", palette.FRAGILE_TELL[blink])
    if boss.gaze is not None:
        a0, cone, reach = boss.gaze
        for k in range(26):
            a = a0 + cone * (_hash01(k, 3) - 0.5)
            d = reach * ((_hash01(k, 4) - boss.time * 1.2) % 1.0)
            px, py = camera.world_to_px(boss.x + math.cos(a) * d, boss.y + math.sin(a) * d)
            batch.put_c(px, py, "<" if math.cos(a) > 0 else ">", palette.GAZE[k % 2])
    batch.flush()

    if boss.axe is not None:
        px, py = camera.world_to_px(boss.axe[0], boss.axe[1])
        spin = int(boss.time * 16) % 8
        bank.draw(bank.static(f"bassaxe{spin}", _paint_axe(spin), 18), px, py)

    x, y = camera.world_to_px(boss.x, boss.y)
    hurt = boss.hurt_flash > 0
    left = math.cos(boss.facing) < 0
    batch = _Batch(text)
    if boss.form == "bat":
        for k in range(16):
            a = boss.time * 3 + k * 0.39 + math.sin(boss.time * 7 + k) * 0.3
            r = 14 + (k % 4) * 9
            batch.put_c(x + math.cos(a) * r, y + math.sin(a) * r * 0.8,
                        "^v^" if (k + int(boss.time * 10)) % 2 else "vVv",
                        palette.HIT_FLASH if hurt else palette.BAT_COL[k % 2])
    else:
        art = "fragile_wolf" if boss.form == "wolf" else "fragile"
        draw_character(bank, x, y, art, SCALE, left, 0, hurt)
    if kind == "strum":
        for dx, dy, glyph, c in _ring(8, 40 + 4 * blink, "o", palette.SHOT_RIFF[0], boss.time * 4):
            batch.put_c(x + dx, y + dy * 0.8, glyph, c)
    elif kind in ("axe", "claw"):
        batch.put_c(x, y - 56, "!" if kind == "claw" else "/!\\", palette.FRAGILE_TELL[blink])
    elif kind in ("screech", "howl"):
        rr = 46 + (boss.time * 80) % 30
        for dx, dy, glyph, c in _ring(16, rr, "o", palette.FRAGILE_TELL[blink], boss.time):
            batch.put_c(x + dx, y + dy * 0.8, glyph, c)
    elif kind == "shift":
        for dx, dy, glyph, c in _ring(12, 34, "%" if tell[1] == "bat" else "#",
                                      palette.FRAGILE_TELL[blink], boss.time * 6):
            batch.put_c(x + dx, y + dy, glyph, c)
    if boss.dazed > 0:
        for k in range(3):
            a = boss.time * 4 + k * math.tau / 3
            batch.put_c(x + math.cos(a) * 26, y - 54 + math.sin(a) * 6, "*", palette.TOAST)
    batch.flush()


def draw_ballroom_marks(text, bank: SpriteBank, camera: Camera, boss, hero, time: float) -> None:
    """Levers (OPEN, a bar while pulled), coffins (STAKE, a bar), an arrow to
    the nearest closed lever while she's within 14 tiles of you, and the
    metronome in phase 3."""
    from .bosses import draw_pointer
    batch = _Batch(text)
    blink = int(time * 6) % 2
    cw, ch = text.display.cell_w, text.display.cell_h
    levers = boss.props.get("levers", [])
    for i, (lx, ly) in enumerate(levers):
        px, py = camera.world_to_px(lx, ly)
        if not (-60 <= px <= camera.view_w + 60 and -60 <= py <= camera.view_h + 60):
            continue
        if i in boss.open:
            s = f"SUN {math.ceil(boss.open[i])}"
            batch.put_px(px - len(s) * cw / 2, py - 34, s, palette.SUN[0], palette.HUD_PANEL)
            continue
        _px_ring(batch, camera, lx, ly, config.LEVER_REACH, 12, "+",
                 palette.PIN_LEVER[0] if blink else palette.LEVER_FG, time)
        s = "OPEN"
        batch.put_px(px - len(s) * cw / 2, py - 34, s, palette.PIN_LEVER[0], palette.HUD_PANEL)
        t = boss.pull.get(i, 0.0)
        if t > 0:
            _bar(batch, px, py - 52, cw, t / config.LEVER_TIME, 6, "", palette.SUN[0],
                 palette.HUD_EMPTY)
    for i, (cx, cy) in enumerate(boss.props.get("coffins", [])):
        if i in boss.staked:
            continue
        px, py = camera.world_to_px(cx, cy)
        if not (-60 <= px <= camera.view_w + 60 and -60 <= py <= camera.view_h + 60):
            continue
        s = "STAKE"
        batch.put_px(px - len(s) * cw / 2, py - 30, s, palette.PIN_COFFIN[0], palette.HUD_PANEL)
        t = boss.stake_t.get(i, 0.0)
        if t > 0:
            _bar(batch, px, py - 48, cw, t / config.STAKE_TIME, 6, "", palette.PIN_COFFIN[0],
                 palette.HUD_EMPTY)
    if boss.phase >= 2:                                   # the metronome
        ph = boss.beat_phase() / boss.period
        on = min(ph, 1 - ph) * boss.period <= config.BEAT_PERFECT
        y = camera.view_h - ch * 2.5
        width = 21
        left = camera.view_w / 2 - width * cw / 2
        line = "".join("|" if k in (0, width - 1) else "-" for k in range(width))
        batch.put_px(left, y, line, palette.BEAT_COL[1], palette.HUD_PANEL)
        pos = round(ph * (width - 1))
        batch.put_px(left + pos * cw, y, "O", palette.BEAT_COL[0], palette.HUD_PANEL)
        s = " ROLL NOW! " if on else " ROLL ON THE BEAT "
        batch.put_px(camera.view_w / 2 - len(s) * cw / 2, y - ch,
                     s, palette.BEAT_COL[0] if on else palette.BEAT_COL[1], palette.HUD_PANEL)
    batch.flush()
    if math.hypot(boss.x - hero.x, boss.y - hero.y) <= 14 and not boss.open:
        closed = [lv for i, lv in enumerate(levers) if i not in boss.open]
        target = _nearest(closed, hero.x, hero.y)
        if target is not None:
            draw_pointer(text, bank, camera, *target,
                         f"LEVER {math.hypot(target[0] - hero.x, target[1] - hero.y):.0f}", 20,
                         palette.PIN_LEVER[0])


def draw_bat(text, camera: Camera, e) -> None:
    batch = _Batch(text)
    x, y = camera.world_to_px(e.x, e.y)
    flap = int(getattr(e, "phase", 0.0) * 1.5) % 2
    batch.put_c(x, y, "^v^" if flap else "vVv", palette.BAT_COL[1])
    if getattr(e, "windup", 0) > 0:
        batch.put_c(x, y - 14, "!", palette.FRAGILE_TELL[0])
    batch.flush()


def draw_carried(text, camera: Camera, quests, players) -> None:
    """Mr. Buttons' pieces and the bear himself: a little bear by whoever
    carries them (with how many pieces), and on the ground where dropped."""
    batch = _Batch(text)
    for s in quests.states.values():
        if s.spec.kind != "fetch":
            continue
        for p in players:
            if not p.alive:
                continue
            n = s.carry.get(p.index, 0)
            px, py = camera.world_to_px(p.hero.x, p.hero.y)
            if s.bear == p.index:
                batch.put_c(px + 18, py - 4, "(@)", palette.PIECE_FG)
            elif n:
                batch.put_c(px + 16, py - 4, f"@x{n}", palette.PIECE_FG)
        for x, y, what in s.drops:
            px, py = camera.world_to_px(x, y)
            batch.put_c(px, py, "(@)" if what == "bear" else "@,", palette.PIECE_FG)
    batch.flush()
