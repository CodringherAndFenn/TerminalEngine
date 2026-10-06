"""
render/snowking.py -- the Snow King, King of Loneliness, his crown, black
ice, tells, penguins and snowballs, the hall's markers, the frost wraiths
and the sister's captives (M24.2).

The King is the Frost Hermit (render/painted.paint_hermit, M24.4): hunched
in grey furs, eyes glowing in a pointed cowl, a braided frost beard, an
ice-root staff. His crown (black iron, ice gems) sits on the cowl; knocked
off, it spins on the floor, labelled. His tells, in ice blue (design/BOSSES.md 5.3):
  * his staff raised before shards, spikes and snowballs (its shard and
    his eyes blaze, "*" round the shard);
  * frost breath: a wedge of dots, then the cone itself;
  * icicles: blinking shadows where they'll fall;
  * freeze: frost spreading from where the sheets will grow;
  * whistle (penguins): a pulsing ring; gust (blizzard): arrows the way
    the wind will blow, then snow streaming across the whole screen.
Black ice is a pale ring with glints. Between moves he glides round the
hall (M24.5), leaving a short trail of frost (","). Markers (what to run to): FIRE
over each brazier (and a lighting bar), CROWN - KICK IT! over the loose
crown, the ice block round an encased hero with "ROLL x/3", and an arrow
at the screen's edge to the crown, or to a fire when you're on ice or
your chill is high.
"""

from __future__ import annotations

import math

import pygame

from .. import config, palette
from ..engine_ext.camera import Camera
from .ascii_fx import _Batch, _ring
from .characters import draw_character
from .fallout import _bar, _hash01, _nearest, draw_vault_marks
from . import painted
from .magus import _dotted, _px_ring
from .sprites import SpriteBank

KING_SCALE = 6


def _paint_crown(spin: int):
    def paint(surf, to_px):
        painted.paint_crown(painted.Pen(surf, to_px, KING_SCALE, False, False), spin)
    return paint


def _paint_penguin(frame: int, left: bool):
    p = palette.PENGUIN
    k = -1 if left else 1

    def paint(surf, to_px):
        cx, cy = to_px(0, 0)
        pygame.draw.ellipse(surf, p["body"], pygame.Rect(round(cx - 12), round(cy - 6), 24, 12))
        pygame.draw.ellipse(surf, p["belly"], pygame.Rect(round(cx - 8), round(cy - 3), 16, 7))
        pygame.draw.circle(surf, p["body"], (round(cx + 11 * k), round(cy - 1)), 5)
        pygame.draw.polygon(surf, p["beak"], [(round(cx + 15 * k), round(cy - 2)),
                                              (round(cx + 20 * k), round(cy)),
                                              (round(cx + 15 * k), round(cy + 1))])
        fy = 4 if frame else -4
        pygame.draw.line(surf, p["beak"], (round(cx - 12 * k), round(cy + fy)),
                         (round(cx - 16 * k), round(cy + fy * 1.5)), 2)
    return paint


def _paint_snowball(r_px: int):
    def paint(surf, to_px):
        cx, cy = to_px(0, 0)
        pygame.draw.circle(surf, palette.SNOWBALL[1], (round(cx), round(cy)), r_px)
        pygame.draw.circle(surf, palette.SNOWBALL[0], (round(cx - 1), round(cy - 1)),
                           max(1, r_px - 2))
    return paint


def draw_snow_king(text, bank: SpriteBank, camera: Camera, boss) -> None:
    batch = _Batch(text)
    blink = int(boss.time * 8) % 2
    for s in boss.sheets:
        r = boss._sheet_r(s)
        _px_ring(batch, camera, s["x"], s["y"], r, max(14, int(r * 6)), "o",
                 palette.ICE_SHEET[blink if s["age"] < 1.0 else 1], 0.0)
        for k in range(int(r * 4)):
            hx, hy = _hash01(k, round(s["x"])), _hash01(k, round(s["y"]) + 7)
            a, d = hx * math.tau, math.sqrt(hy) * r * 0.9
            px, py = camera.world_to_px(s["x"] + math.cos(a) * d, s["y"] + math.sin(a) * d)
            batch.put_c(px, py, "-" if k % 3 else "/", palette.ICE_SHEET[0])
    for tx, ty, age in boss.trail:            # frost where he's glided (M24.5)
        px, py = camera.world_to_px(tx, ty)
        fade = age / config.SNOW_TRAIL[1]
        batch.put_c(px, py, ",," if fade < 0.5 else ",", palette.ICE_SHEET[0 if fade < 0.5 else 1])
    tell = boss.tell
    kind = tell[0] if tell is not None else None
    if kind == "wedge":
        _, a0, cone, reach = tell
        for k in range(7):
            a = a0 + cone * (k / 6 - 0.5)
            _dotted(batch, camera, boss.x, boss.y, boss.x + math.cos(a) * reach,
                    boss.y + math.sin(a) * reach, palette.SNOW_TELL[blink], step=1.4)
    elif kind == "freeze":
        for x, y in tell[1]:
            rr = config.ICE_RADIUS[0] * (0.4 + 0.6 * ((boss.time * 1.5) % 1.0))
            _px_ring(batch, camera, x, y, rr, 16, "*", palette.SNOW_TELL[blink], boss.time)
    elif kind == "gust":
        h = tell[1]
        for k in range(10):
            px = camera.view_w * (0.1 + 0.08 * k)
            py = camera.view_h * (0.2 + 0.6 * _hash01(k, 3))
            glyph = {0: ">", 1: "v"}.get(round(math.sin(h)) if abs(math.sin(h)) > 0.5 else 0, ">")
            if math.cos(h) < -0.5:
                glyph = "<"
            elif math.sin(h) < -0.5:
                glyph = "^"
            batch.put_c(px, py, glyph * 3, palette.SNOW_TELL[blink])
    for x, y in boss.icicles:
        _px_ring(batch, camera, x, y, config.SNOW_ICICLES[2], 12, "o", palette.TELEGRAPH[blink])
        px, py = camera.world_to_px(x, y)
        batch.put_c(px, py, "v", palette.SNOW_TELL[0])
    if boss.breath is not None:
        a0, cone, reach = boss.breath
        for k in range(30):
            a = a0 + cone * (_hash01(k, 1) - 0.5)
            d = reach * ((_hash01(k, 2) + boss.time * 1.7) % 1.0)
            px, py = camera.world_to_px(boss.x + math.cos(a) * d, boss.y + math.sin(a) * d)
            batch.put_c(px, py, "*" if k % 3 else "o", palette.SNOW_TELL[k % 2])
    batch.flush()

    for p in boss.penguins:
        px, py = camera.world_to_px(p[0], p[1])
        frame = int(boss.time * 8) % 2
        left = p[2] < 0
        bank.draw(bank.static(f"penguin{frame}{left}", _paint_penguin(frame, left), 24), px, py)
    for b in boss.snowballs:
        r_px = max(4, round(b[4] * config.TILE_PX_W * 0.8))
        px, py = camera.world_to_px(b[0], b[1])
        bank.draw(bank.static(f"snowball{r_px}", _paint_snowball(r_px), r_px + 2), px, py)

    x, y = camera.world_to_px(boss.x, boss.y)
    down = boss.crownless
    left = math.cos(boss.facing) < 0
    sx = -1 if left else 1
    cast = kind in ("cast", "whistle")
    pose = "down" if down else ("cast" if cast else "")
    frame = int(boss.waddle if down else boss.walked * 1.5) % 4
    draw_character(bank, x, y, "snow_king", KING_SCALE, left, frame, boss.hurt_flash > 0, pose)
    cu, cv = painted.HERMIT_CROWN
    crown_x, crown_y = x + sx * cu * KING_SCALE, y + (cv + (0.7 if down else 0)) * KING_SCALE
    if boss.crown_on and boss.donning <= 0:
        bank.draw(bank.static("crown0", _paint_crown(0), 30), crown_x, crown_y)
    else:
        cx, cy = camera.world_to_px(boss.crown[0], boss.crown[1])
        spin = int(boss.time * 10) % 2 if math.hypot(boss.crown[2], boss.crown[3]) > 1 else 0
        if boss.donning > 0:
            cx, cy = crown_x, crown_y - 30 * boss.donning / config.CROWN_DON
        bank.draw(bank.static(f"crown{spin}", _paint_crown(spin), 30), cx, cy)
    batch = _Batch(text)
    if cast:                                # the shard on his staff blazing
        su, sv = painted.HERMIT_SHARD
        tip_x, tip_y = x + sx * su * KING_SCALE, y + (sv + painted.HERMIT_LIFT) * KING_SCALE
        for dx, dy, glyph, c in _ring(8, 14 + 4 * blink, "*", palette.SNOW_KING["glow"],
                                      boss.time * 6):
            batch.put_c(tip_x + dx, tip_y + dy, glyph, c)
        if kind == "whistle":
            rr = 50 + (boss.time * 80) % 30
            for dx, dy, glyph, c in _ring(16, rr, "o", palette.SNOW_TELL[blink], boss.time):
                batch.put_c(x + dx, y + dy * 0.8, glyph, c)
    if down:
        for k in range(3):
            a = boss.time * 4 + k * math.tau / 3
            batch.put_c(crown_x + math.cos(a) * 26, crown_y + math.sin(a) * 6, "?", palette.TOAST)
    batch.flush()


def _blizzard(text, camera: Camera, heading: float, time: float) -> None:
    """Snow streaming across the whole screen the way the wind blows."""
    batch = _Batch(text)
    hx, hy = math.cos(heading), math.sin(heading)
    w, h = camera.view_w, camera.view_h
    for k in range(160):
        u, v = _hash01(k, 11), _hash01(k, 12)
        speed = 0.5 + _hash01(k, 13)
        px = (u * w + hx * time * 420 * speed) % w
        py = (v * h + hy * time * 420 * speed) % h
        batch.put_c(px, py, "-" if abs(hx) > 0.5 else "|", palette.SNOWBALL[k % 2])
    batch.flush()


def draw_hall_marks(text, bank: SpriteBank, camera: Camera, boss, hero, time: float) -> None:
    """What the Snow King's fight asks you to find, marked (see the module
    docstring)."""
    from .bosses import draw_pointer
    if boss.wind is not None:
        _blizzard(text, camera, boss.wind, time)
    batch = _Batch(text)
    blink = int(time * 6) % 2
    cw = text.display.cell_w
    braziers = boss.props.get("braziers", [])
    for i, (bx, by) in enumerate(braziers):
        px, py = camera.world_to_px(bx, by)
        if not (-60 <= px <= camera.view_w + 60 and -60 <= py <= camera.view_h + 60):
            continue
        lit = i in boss.lit
        if lit:
            for dx, dy, glyph, c in _ring(6, 8 + 3 * blink, "*", palette.FIRE_LIT_FG, time * 5):
                batch.put_c(px + dx, py - 10 + dy, glyph, c)
            s = f"FIRE {math.ceil(boss.lit[i])}"
            batch.put_px(px - len(s) * cw / 2, py - 40, s, palette.FIRE_LIT_FG, palette.HUD_PANEL)
        else:
            _px_ring(batch, camera, bx, by, config.FIRE_REACH, 12, "+",
                     palette.PIN_FIRE[0] if blink else palette.FIRE_FG, time)
            s = "LIGHT ME"
            batch.put_px(px - len(s) * cw / 2, py - 40, s, palette.PIN_FIRE[0], palette.HUD_PANEL)
            k = boss.kindle.get(i, 0.0)
            if k > 0:
                _bar(batch, px, py - 58, cw, k / config.BRAZIER_KINDLE, 6, "",
                     palette.FIRE_LIT_FG, palette.HUD_EMPTY)
    if boss.crownless:
        px, py = camera.world_to_px(boss.crown[0], boss.crown[1])
        s = " CROWN - KICK IT! "
        batch.put_px(px - len(s) * cw / 2, py - 34, s, palette.PIN_CROWN[0], palette.HUD_PANEL)
    for h in boss.ctx.players if boss.ctx is not None else ():
        if h.encased > 0 and h.alive:
            px, py = camera.world_to_px(h.x, h.y)
            for dx, dy, glyph, c in _ring(12, 20, "#", palette.ICE_BLOCK_FG, 0.0):
                batch.put_c(px + dx, py + dy * 1.2, glyph, c)
            s = f" ROLL! {h.encase_breaks}/{config.ENCASE[1]} "
            batch.put_px(px - len(s) * cw / 2, py - 46, s, palette.ICE_BLOCK_FG, palette.HUD_PANEL)
    batch.flush()

    want = None
    if boss.crownless:
        want = ((boss.crown[0], boss.crown[1]), "CROWN", palette.PIN_CROWN[0])
    elif boss.on_ice(hero.x, hero.y) or hero.chill >= 60:
        lit = [braziers[i] for i in boss.lit]
        target = _nearest(lit or braziers, hero.x, hero.y)
        want = (target, "FIRE", palette.FIRE_LIT_FG)
    if want is not None and want[0] is not None:
        (tx, ty), name, col = want
        draw_pointer(text, bank, camera, tx, ty,
                     f"{name} {math.hypot(tx - hero.x, ty - hero.y):.0f}", 20, col)


def draw_fight_marks(text, bank: SpriteBank, camera: Camera, boss, hero, time: float) -> None:
    """The markers for whichever boss's fixtures this is (M24.1 vault,
    M24.2 hall, M24.3 ballroom, M25.1 glade)."""
    from ..ai.bosses import FalloutKing, Fragile, Nettle, SnowKing
    from .fragile import draw_ballroom_marks
    from .nettle import draw_glade_marks
    if isinstance(boss, Nettle):
        draw_glade_marks(text, bank, camera, boss, hero, time)
    elif isinstance(boss, Fragile):
        draw_ballroom_marks(text, bank, camera, boss, hero, time)
    elif isinstance(boss, SnowKing):
        draw_hall_marks(text, bank, camera, boss, hero, time)
    elif isinstance(boss, FalloutKing):
        draw_vault_marks(text, bank, camera, boss, hero, time)


# --- The frost wraiths, the captives ----------------------------------------------------------


def draw_wraith(text, camera: Camera, e) -> None:
    batch = _Batch(text)
    x, y = camera.world_to_px(e.x, e.y)
    col = palette.WRAITH[int(e.phase * 2) % 2]
    batch.put_c(x, y - 8, "@", palette.WRAITH[0])
    batch.put_c(x, y + 4, "VV", col)
    for dx, dy, glyph, c in _ring(5, 13, "'", palette.WRAITH[1], e.phase):
        batch.put_c(x + dx, y + dy, glyph, c)
    batch.flush()


def draw_captives(text, bank: SpriteBank, camera: Camera, quests, time: float) -> None:
    """A thawing captive (block shattered, not yet freed): their picture,
    shivering, over the slush."""
    x0, y0 = camera.canvas_to_world(0, 0)
    x1, y1 = camera.canvas_to_world(camera.view_w, camera.view_h)
    for s in quests.states.values():
        if s.spec.kind != "rescue" or s.stage != "hunt":
            continue
        for i in s.opened:
            if i in s.lit:
                continue
            cx, cy = s.camp.spots[i]
            if x0 - 4 <= cx <= x1 + 4 and y0 - 4 <= cy <= y1 + 4:
                px, py = camera.world_to_px(cx, cy)
                draw_character(bank, px + math.sin(time * 30) * 1.5, py - 8, "captive", 3, False,
                               0, False)
