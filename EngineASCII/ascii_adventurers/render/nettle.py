"""
render/nettle.py -- Nettle, the Blighted, her glamour copies, her dust,
blight, thorns, sparks and wisps, the glade's markers, and her rot moths
and the shrines' blighted sprites (M25.1).

She's painted (render/painted.paint_nettle): a moth-winged pixie, wings
flapping fast. Only she casts a SHADOW (an oval on the ground under her)
and has a faint glitter about her; her copies (ai/bosses.Glamour) are the
same picture without either, flickering as they're about to fade. Her
tells, in rot green (design/BOSSES.md 5.3):
  * shimmer (she's about to split): "%" pulsing round her;
  * cast (spiral, sparks, cage, dust): her arms up, glows in her hands,
    "*" round her;
  * cracks (thorn lines): ":" along the lines the thorns will burst on;
  * dive: a dotted line with ">" along it;
  * gather (wisp lure): the wisps drifting in to her;
  * nettles: blinking rings on the ground with "v" in the middle;
  * seeds: blinking "x" rings where they'll land;
  * call (moths): a pulsing ring.
Dust clouds are a dotted rim (":") round a haze of twinkling dust; blight is "%" over the
ground round a seed ("@", blinking) with PULL and a bar. Growcaps get a
ring and GROWCAP while a hero is tiny, and an arrow points to the nearest
one; while she drinks the blight, an arrow points to the nearest seed.
"""

from __future__ import annotations

import math

import pygame

from .. import config, palette
from ..engine_ext.camera import Camera
from .ascii_fx import _Batch, _ring, draw_hp_bar
from .characters import draw_character
from .fallout import _bar, _hash01, _nearest
from .magus import _dotted, _px_ring
from .sprites import SpriteBank

SCALE = 5
HOVER = 10           # px she floats above her shadow


def _paint_shadow(w: int):
    """Her shadow: dark, with a moonlit rim so it shows on the dark leaves."""
    def paint(surf, to_px):
        cx, cy = to_px(0, 0)
        rect = pygame.Rect(round(cx - w), round(cy - w * 0.3), 2 * w, round(w * 0.6))
        pygame.draw.ellipse(surf, palette.NETTLE_SHADOW[0], rect)
        pygame.draw.ellipse(surf, palette.NETTLE_SHADOW[1], rect, 2)
    return paint


def _pose(boss) -> str:
    kind = boss.tell[0] if boss.tell is not None else None
    if boss.dashing or kind == "dive":
        return "dive"
    if kind in ("cast", "shimmer", "gather", "call", "seeds"):
        return "cast"
    return ""


def _figure(bank: SpriteBank, x: float, y: float, boss, body, hurt: bool) -> None:
    frame = int(boss.time * 14 + body.x) % 4
    bob = math.sin(boss.time * 3 + body.x) * 3
    draw_character(bank, x, y - HOVER + bob, "nettle", SCALE, math.cos(body.facing) < 0, frame,
                   hurt, _pose(boss))


def draw_nettle(text, bank: SpriteBank, camera: Camera, boss) -> None:
    """Her, and everything she's put on the field."""
    batch = _Batch(text)
    blink = int(boss.time * 8) % 2
    x0, y0 = camera.canvas_to_world(0, 0)
    x1, y1 = camera.canvas_to_world(camera.view_w, camera.view_h)
    # The blight: "%" over the ground round each seed.
    for s in boss.seeds:
        r = boss.seed_radius(s)
        n = int(r * r * 3)
        for k in range(n):
            a = _hash01(k, round(s[0]), 3) * math.tau
            d = math.sqrt(_hash01(k, round(s[1]), 5)) * r
            wx, wy = s[0] + math.cos(a) * d, s[1] + math.sin(a) * d
            if x0 - 1 <= wx <= x1 + 1 and y0 - 1 <= wy <= y1 + 1:
                px, py = camera.world_to_px(wx, wy)
                batch.put_c(px, py, "%", palette.BLIGHT_FG[k % 2])
        px, py = camera.world_to_px(s[0], s[1])
        batch.put_c(px, py, "@", palette.BLIGHT_SEED_FG if blink else palette.BLIGHT_FG[0])
    # Dust clouds: a dotted rim and a haze of twinkling dust inside.
    for c in boss.clouds:
        fade = c[2] / config.NETTLE_DUST[3]
        col = palette.DUST_CLOUD[min(2, int(fade * 3))]
        _px_ring(batch, camera, c[0], c[1], config.NETTLE_DUST[2], 18, ":", col, boss.time * 0.5)
        for k in range(22):
            a = _hash01(k, round(c[0] * 7)) * math.tau + boss.time * 0.6
            d = math.sqrt(_hash01(k, round(c[1] * 7))) * config.NETTLE_DUST[2] * 0.9
            px, py = camera.world_to_px(c[0] + math.cos(a) * d, c[1] + math.sin(a) * d)
            batch.put_c(px, py, "'" if (k + int(boss.time * 6)) % 3 else ":",
                        palette.DUST_CLOUD[(k + int(boss.time * 4)) % 2] if fade < 0.66 else col)
    # The thorn lines' cracks, the thorns out, the nettles' shadows.
    for x, y in boss.cracks:
        px, py = camera.world_to_px(x, y)
        batch.put_c(px, py, ":", palette.THORN_TELL[blink])
    for x, y, age in boss.spikes:
        px, py = camera.world_to_px(x, y)
        batch.put_c(px, py - age * 10, "^^", palette.SHOT_THORN[0])
    for x, y in boss.shadows:
        _px_ring(batch, camera, x, y, config.NETTLE_NETTLES[2], 12, "o", palette.TELEGRAPH[blink])
        px, py = camera.world_to_px(x, y)
        batch.put_c(px, py, "v", palette.NETTLE_TELL[0])
    for x, y in boss.falling:
        _px_ring(batch, camera, x, y, 1.5, 10, "x", palette.BLIGHT_SEED_FG if blink
                 else palette.TELEGRAPH[1])
    tell = boss.tell
    kind = tell[0] if tell is not None else None
    if kind == "dive":
        _dotted(batch, camera, *tell[1:5], palette.NETTLE_TELL[blink], mark=">")
    for w in boss.gather:
        px, py = camera.world_to_px(w[0], w[1])
        batch.put_c(px, py, "o", palette.WISP_COL[blink])
    # Sparks and wisps in flight.
    for m in boss.homers:
        px, py = camera.world_to_px(m[0], m[1])
        tx, ty = px - math.cos(m[2]) * 12, py - math.sin(m[2]) * 12
        if m[7] == "spark":
            batch.put_c(tx, ty, "'", palette.SPARK_COL[1])
            batch.put_c(px, py, "x", palette.SPARK_COL[0])
        else:
            batch.put_c(tx, ty, ":", palette.WISP_COL[1])
            batch.put_c(px, py, "o", palette.WISP_COL[0])
    batch.flush()

    # Her: a shadow on the ground (her copies have none), and a glitter.
    x, y = camera.world_to_px(boss.x, boss.y)
    bank.draw(bank.static("nettle_shadow", _paint_shadow(22), 26), x, y + 26)
    _figure(bank, x, y, boss, boss, boss.hurt_flash > 0)
    batch = _Batch(text)
    for k in range(3):
        a = boss.time * 3 + k * math.tau / 3
        batch.put_c(x + math.cos(a) * 30, y - HOVER + math.sin(a) * 26, "'",
                    palette.NETTLE_GLOW[k % 2])
    _cast_tells(batch, x, y, boss, kind, blink)
    if boss.healing:
        for k in range(4):
            a = boss.time * 5 + k * math.tau / 4
            batch.put_c(x + math.cos(a) * 20, y + 18 + math.sin(a) * 6, "+", palette.BLIGHT_FG[0])
    batch.flush()


def _cast_tells(batch, x: float, y: float, boss, kind, blink: int) -> None:
    """The tells round her body -- and round every copy's too, so only her
    shadow and her glitter give her away."""
    if kind in ("cast", "seeds"):
        for dx, dy, glyph, c in _ring(8, 34 + 4 * blink, "*", palette.NETTLE_TELL[0],
                                      boss.time * 6):
            batch.put_c(x + dx, y - HOVER + dy, glyph, c)
    elif kind == "shimmer" or boss.shimmer > 0:
        for dx, dy, glyph, c in _ring(12, 36 + 8 * blink, "%", palette.NETTLE_TELL[blink],
                                      boss.time * 8):
            batch.put_c(x + dx, y - HOVER + dy, glyph, c)
    elif kind == "call":
        rr = 40 + (boss.time * 80) % 30
        for dx, dy, glyph, c in _ring(16, rr, "o", palette.NETTLE_TELL[blink], boss.time):
            batch.put_c(x + dx, y + dy * 0.8, glyph, c)


def draw_glamour(text, bank: SpriteBank, camera: Camera, d) -> None:
    """One of her copies: her picture and her tells, but no shadow and no
    glitter; it flickers out over its last 2 s."""
    boss = d.part_of
    if boss is None:
        return
    if config.DECOY_LIFE - d.age < 2.0 and int(d.age * 12) % 2:
        return
    x, y = camera.world_to_px(d.x, d.y)
    _figure(bank, x, y, boss, d, d.hurt_flash > 0)
    batch = _Batch(text)
    kind = boss.tell[0] if boss.tell is not None else None
    _cast_tells(batch, x, y, boss, kind, int(boss.time * 8) % 2)
    batch.flush()


def draw_glade_marks(text, bank: SpriteBank, camera: Camera, boss, hero, time: float) -> None:
    """Growcaps (a ring and GROWCAP while a hero is tiny), rot seeds (PULL,
    a bar), and an arrow to the nearest growcap while you're tiny, or to the
    nearest seed while she's drinking the blight."""
    from .bosses import draw_pointer
    batch = _Batch(text)
    blink = int(time * 6) % 2
    cw = text.display.cell_w
    caps = boss.props.get("growcaps", [])
    tiny = any(h.alive and h.shrunk > 0 for h in boss.ctx.players) if boss.ctx else False
    for i, (gx, gy) in enumerate(caps):
        px, py = camera.world_to_px(gx, gy)
        if not (-60 <= px <= camera.view_w + 60 and -60 <= py <= camera.view_h + 60):
            continue
        if i in boss.spent:
            if tiny:
                s = f"REGROWS {math.ceil(boss.spent[i])}"
                batch.put_px(px - len(s) * cw / 2, py - 30, s, palette.GROWCAP_SPENT_FG,
                             palette.HUD_PANEL)
            continue
        _px_ring(batch, camera, gx, gy, config.GROWCAP_REACH, 10, "+",
                 palette.PIN_GROWCAP[0] if blink or not tiny else palette.GROWCAP_SPENT_FG, time)
        if tiny:
            s = "GROWCAP"
            batch.put_px(px - len(s) * cw / 2, py - 30, s, palette.PIN_GROWCAP[0],
                         palette.HUD_PANEL)
    for s in boss.seeds:
        px, py = camera.world_to_px(s[0], s[1])
        if not (-60 <= px <= camera.view_w + 60 and -60 <= py <= camera.view_h + 60):
            continue
        label = "PULL"
        batch.put_px(px - len(label) * cw / 2, py - 30, label, palette.BLIGHT_SEED_FG,
                     palette.HUD_PANEL)
        if s[3] > 0:
            _bar(batch, px, py - 48, cw, s[3] / config.BLIGHT_PULL, 6, "", palette.BLIGHT_SEED_FG,
                 palette.HUD_EMPTY)
    batch.flush()
    want = None
    if hero.shrunk > 0:
        ready = [c for i, c in enumerate(caps) if i not in boss.spent]
        want = (_nearest(ready, hero.x, hero.y), "GROWCAP", palette.PIN_GROWCAP[0])
    elif boss.healing and boss.seeds:
        want = (_nearest([(s[0], s[1]) for s in boss.seeds], hero.x, hero.y), "SEED",
                palette.BLIGHT_SEED_FG)
    if want is not None and want[0] is not None:
        (tx, ty), name, col = want
        draw_pointer(text, bank, camera, tx, ty,
                     f"{name} {math.hypot(tx - hero.x, ty - hero.y):.0f}", 20, col)


# --- Her moths, the shrines' sprites -------------------------------------------------------


def draw_moth(text, camera: Camera, e) -> None:
    batch = _Batch(text)
    x, y = camera.world_to_px(e.x, e.y)
    flap = int(getattr(e, "phase", 0.0) * 2) % 2
    batch.put_c(x, y, "}o{" if flap else ")o(", palette.MOTH_COL[0])
    if getattr(e, "windup", 0) > 0:
        batch.put_c(x, y - 14, "!", palette.NETTLE_TELL[0])
    batch.flush()
    if e.hp < e.max_hp:
        draw_hp_bar(text, x, y - 18, e.hp / e.max_hp)


def draw_sprite(text, camera: Camera, e) -> None:
    """A blighted sprite: a sickly green light with a flicker round it."""
    batch = _Batch(text)
    x, y = camera.world_to_px(e.x, e.y)
    blink = int(getattr(e, "phase", 0.0) * 2) % 2
    batch.put_c(x, y, "<*>" if blink else ">*<", palette.SPRITE_COL[0])
    for dx, dy, glyph, c in _ring(3, 13 + 2 * blink, "'", palette.SPRITE_COL[1],
                                  getattr(e, "phase", 0.0) * 3):
        batch.put_c(x + dx, y + dy, glyph, c)
    if getattr(e, "windup", 0) > 0:
        batch.put_c(x, y - 14, "!", palette.NETTLE_TELL[0])
    batch.flush()
    if e.hp < e.max_hp:
        draw_hp_bar(text, x, y - 18, e.hp / e.max_hp)
