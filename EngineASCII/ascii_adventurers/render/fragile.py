"""
render/fragile.py -- Fragile, The Misunderstood: the sun through her
shutters, her three forms, her tells, her mist and parasol, the
chandeliers, the ballroom's markers and the metronome, her bats and
thralls, and Mr. Buttons carried, dropped, and riding on a head (M24.3).

She's painted (render/painted.py, M24.4): a girl hovering off the floor
with her black lace parasol (on her shoulder, twirled for the petals,
furled and raised to throw, gone while it spins), a
black wolf in a torn strip of her red top, or a cloud of bats. Mr.
Buttons rides on his carrier's head until he's given back. Her tells, in her own red
(design/BOSSES.md 5.3):
  * twirl (petals): petals circling her; parasol: it furled and raised,
    "/!\\" over her;
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

SCALE = 6


def _paint_parasol(spin: int):
    """Her thrown parasol seen from above, open and spinning: a black
    canopy, its ribs turning, a scalloped red lace rim, a silver tip."""
    c = palette.FRAGILE

    def paint(surf, to_px):
        cx, cy = to_px(0, 0)
        r = 15
        rim = []
        for k in range(16):                         # scallops: in, out, in, ...
            a = k * math.tau / 16
            rr = r if k % 2 == 0 else r - 2.5
            rim.append((round(cx + math.cos(a) * rr), round(cy + math.sin(a) * rr * 0.8)))
        pygame.draw.polygon(surf, c["lace"], rim)
        pygame.draw.ellipse(surf, c["canopy"], pygame.Rect(round(cx - r + 3), round(cy - (r - 3) * 0.8),
                                                           2 * (r - 3), round(2 * (r - 3) * 0.8)))
        for k in range(8):
            a = (k + spin / 2) * math.tau / 8
            pygame.draw.line(surf, c["rib"], (round(cx), round(cy)),
                             (round(cx + math.cos(a) * (r - 3)),
                              round(cy + math.sin(a) * (r - 3) * 0.8)), 1)
        pygame.draw.circle(surf, c["tip"], (round(cx), round(cy)), 2)
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

    if boss.parasol is not None:
        px, py = camera.world_to_px(boss.parasol[0], boss.parasol[1])
        spin = int(boss.time * 16) % 8
        bank.draw(bank.static(f"parasol{spin}", _paint_parasol(spin), 18), px, py)

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
    elif boss.form == "wolf":
        draw_character(bank, x, y, "fragile_wolf", SCALE, left, int(boss.walked * 1.2) % 4, hurt,
                       "howl" if kind == "howl" else "")
    else:
        # She hovers (the 4-step cycle bobs her), her parasol on her
        # shoulder: twirled for the petals, furled and raised before she
        # throws it, and gone while it's out spinning.
        pose = ("bare" if boss.parasol is not None else "raise" if kind == "parasol"
                else "twirl" if kind == "twirl" else "")
        draw_character(bank, x, y, "fragile", SCALE, left, int(boss.time * 3) % 4, hurt, pose)
    if kind == "twirl":
        for dx, dy, glyph, c in _ring(8, 40 + 4 * blink, "*", palette.SHOT_PETAL[0], boss.time * 4):
            batch.put_c(x + dx, y + dy * 0.8, glyph, c)
    elif kind in ("parasol", "claw"):
        batch.put_c(x, y - 64, "!" if kind == "claw" else "/!\\", palette.FRAGILE_TELL[blink])
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
            batch.put_c(x + math.cos(a) * 26, y - 62 + math.sin(a) * 6, "*", palette.TOAST)
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


def draw_carried(text, bank: SpriteBank, camera: Camera, quests, players) -> None:
    """Mr. Buttons' pieces by whoever carries them (with how many), and
    the pieces and the bear on the ground where they were dropped. (The
    bear himself rides on his carrier's head: draw_bear_riders.)"""
    batch = _Batch(text)
    bears = []
    for s in quests.states.values():
        if s.spec.kind != "fetch":
            continue
        for p in players:
            n = s.carry.get(p.index, 0)
            if p.alive and n:
                px, py = camera.world_to_px(p.hero.x, p.hero.y)
                batch.put_c(px + 16, py - 4, f"@x{n}", palette.PIECE_FG)
        for x, y, what in s.drops:
            px, py = camera.world_to_px(x, y)
            if what == "bear":
                bears.append((px, py))
            else:
                batch.put_c(px, py, "@,", palette.PIECE_FG)
    batch.flush()
    for px, py in bears:
        draw_character(bank, px, py - 6, "mr_buttons", BEAR_SCALE, False, 0, False)


BEAR_SCALE = 2.2             # Mr. Buttons: ~20 px tall, sitting on a head


def draw_bear_riders(bank: SpriteBank, camera: Camera, quests, players) -> None:
    """Mr. Buttons sitting on top of the head of whoever carries him (drawn
    after the heroes), bobbing with their step, until he's given back."""
    from .characters import ART, ART_H, body_scale, walk_frame
    for s in quests.states.values():
        if s.spec.kind != "fetch" or s.bear is None:
            continue
        p = next((p for p in players if p.index == s.bear and p.alive), None)
        if p is None:
            continue
        h = p.hero
        spec = h.spec
        rows = ART.get(spec.sprite, ())
        top = next((r for r, row in enumerate(rows) if row.strip(".")), 0)
        frame = walk_frame(h)
        px, py = camera.world_to_px(h.x, h.y)
        scale = body_scale(h)
        head = py + (top - ART_H / 2) * scale - (scale if frame % 2 else 0)
        # The bear's seat (his legs' bottom) is 5.4 bear units below his
        # centre; sink him a couple of pixels into the hair (or hat).
        draw_character(bank, px + (3 if h.facing_left else -3),
                       head - 5.4 * BEAR_SCALE + 3, "mr_buttons", BEAR_SCALE, h.facing_left, 0,
                       False)
