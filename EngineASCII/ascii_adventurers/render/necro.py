"""
render/necro.py -- the plains boss, More than Life / More than Death, and
everything in his necropolis: corpses (glowing green before they rise, red
before they burst), the bone walls' cracks, death's gaze, the legion's
volleys and phalanx, the soul storm and harvest, possession, the bone cage,
skull fire, grasping hands and the reap; the risen dead's picture (M27).

He's painted (render/painted.paint_necro, "life" or "lich"). His tells, in
green (design/BOSSES.md 5.3):
  * cast (spears, skulls, storm, possession): staff raised, a glowing hand;
  * gaze: eyes blazing, the beam's start shown dim, then the beam;
  * hands: rings of "v" where the hands will burst;
  * reap: his shadow ("( )") where he'll blink to;
  * corpses glowing green (rising) or red (bursting), "!" over them;
  * cracks (":") where bone walls will rise;
  * volley: rings of "|" where the arrows fall; the phalanx marches in;
  * bone cage: rib shadows round you.
"""

from __future__ import annotations

import math

from .. import config, palette
from ..engine_ext.camera import Camera
from .ascii_fx import _Batch, _ring
from .characters import ART, draw_character
from .magus import _dotted, _px_ring
from .plains_art import _pad
from .sprites import SpriteBank

SCALE = 6

ART["risen_dead"] = _pad([
    "...kkkk",
    "..kddddk",
    "..kdkdkdk",
    "..kddddk",
    "...kdddk",
    ".kkdkdkdkk",
    "kd.kdddk.dk",
    "kd.kdkdk.dk",
    "...kdddk",
    "...kd.dk",
    "..kdk.kdk",
    "..kk...kk",
])


def _pose(boss) -> str:
    kind = boss.tell[0] if boss.tell is not None else None
    life = "lich" if boss.lich else "life"
    if boss.reviving:
        act = "ritual"
    elif boss.gaze is not None:
        act = "gaze"
    elif kind == "reap" or boss.arc is not None:
        act = "reap"
    elif boss.raise_glow > 0:
        act = "raise"
    elif kind == "cast":
        act = "cast"
    else:
        act = ""
    return f"{life}:{act}"


def draw_necro(text, bank: SpriteBank, camera: Camera, boss) -> None:
    """Him, and everything he's put on the field."""
    batch = _Batch(text)
    t = boss.time
    blink = int(t * 8) % 2
    raising = boss.raising() if boss.raise_glow > 0 else []
    x0, y0 = camera.canvas_to_world(0, 0)
    x1, y1 = camera.canvas_to_world(camera.view_w, camera.view_h)

    def seen(x, y, m=3):
        return x0 - m <= x <= x1 + m and y0 - m <= y <= y1 + m

    for c in boss.corpses:                         # (corpses: bones on the ground)
        if not seen(c[0], c[1]):
            continue
        px, py = camera.world_to_px(c[0], c[1])
        col = palette.CORPSE_COL[0]
        if c in raising:
            col = palette.NECRO_GLOW[blink]
        elif c in boss.blasting and boss.blast_glow > 0:
            col = palette.NECRO_GLOW[2] if blink else palette.CORPSE_COL[0]
        batch.put_c(px, py, "x_x" if (round(c[0]) + round(c[1])) % 2 else "%_%", col)
        if col is not palette.CORPSE_COL[0]:
            batch.put_c(px, py - 16, "!", col)
        if c[2] > 0:
            batch.put_c(px, py + 12, "." * (1 + int(c[2] / config.CORPSE_STOMP[1] * 3)),
                        palette.BONE_FG)
    for tx, ty in boss.cracks:                     # (bone walls to come)
        px, py = camera.world_to_px(tx + 0.5, ty + 0.5)
        batch.put_c(px, py, ":", palette.TELEGRAPH[blink])
    for z in boss.volley:                          # (arrows to fall)
        r = config.VOLLEY[1]
        _px_ring(batch, camera, z[0], z[1], r, 16, "|", palette.TELEGRAPH[blink], t)
        if z[2] < 0.35:
            for k in range(8):
                a = k * 0.8 + t * 3
                px, py = camera.world_to_px(z[0] + math.cos(a) * r * 0.6,
                                            z[1] + math.sin(a) * r * 0.5)
                batch.put_c(px, py - z[2] * 120, "|", palette.BONE_FG)
    for s in boss.shields:                         # (the phalanx: shield skeletons)
        if not s.alive:
            continue
        px, py = camera.world_to_px(s.x, s.y)
        d = round(s.march / (math.pi / 2)) % 4
        shield = ("]", "-", "[", "-")[d]
        batch.put_c(px, py - 10, "o", palette.BONE_FG)
        batch.put_c(px, py + 4, "#" + shield, palette.BONE_FG if not s.hurt_flash else (255, 255, 255))
    for x, y in boss.hands:                        # (grasping hands to come)
        _px_ring(batch, camera, x, y, config.NECRO_HANDS[3], 8, "v", palette.TELEGRAPH[blink], t)
    if boss.reap_at is not None:
        px, py = camera.world_to_px(*boss.reap_at)
        batch.put_c(px, py, "( )", palette.NECRO_TELL[blink])
    if boss.cage_tell is not None:                 # (rib shadows round you)
        cx, cy = boss.cage_tell[0], boss.cage_tell[1]
        _px_ring(batch, camera, cx, cy, config.CAGE_RADIUS[0], config.CAGE_RIBS, ")(",
                 palette.TELEGRAPH[blink], 0.0)
    for rib in boss.ribs:
        if rib.alive:
            px, py = camera.world_to_px(rib.x, rib.y)
            batch.put_c(px, py - 8, ")" if rib.x < boss.cage_x else "(", palette.BONE_FG)
            batch.put_c(px, py + 6, "|", palette.BONE_FG)
    # Death's gaze: the start shown dim (the tell), then the beam.
    if boss.gaze is not None:
        if boss.gaze_on and boss.gaze_end is not None:
            _dotted(batch, camera, boss.x, boss.y, *boss.gaze_end, palette.GAZE_COL[0],
                    glyph="#", step=0.5)
            _dotted(batch, camera, boss.x, boss.y, *boss.gaze_end, palette.GAZE_COL[1],
                    glyph="=", step=0.5)
        else:
            a = boss.gaze
            _dotted(batch, camera, boss.x, boss.y, boss.x + math.cos(a) * 20,
                    boss.y + math.sin(a) * 20, palette.GAZE_COL[blink], glyph=".", step=0.8)
    if boss.storm > 0:                             # (the soul storm)
        for x, y in boss.storm_souls():
            px, py = camera.world_to_px(x, y)
            batch.put_c(px, py, "@", palette.SOUL_COL[blink])
        for k in range(14):
            a = -t * 3 + k * math.tau / 14
            r = 12 + (k % 3) * 4
            px, py = camera.world_to_px(boss.x + math.cos(a) * r, boss.y + math.sin(a) * r * 0.7)
            batch.put_c(px, py, ">" if math.cos(a) < 0 else "<", palette.SOUL_COL[1])
    for w in boss.wisps:                           # (souls drifting to him)
        px, py = camera.world_to_px(w[0], w[1])
        batch.put_c(px, py, "o", palette.SOUL_COL[blink])
    for m in boss.homers:                          # (skull fire)
        px, py = camera.world_to_px(m[0], m[1])
        batch.put_c(px, py, "@", palette.NECRO_GLOW[0])
        batch.put_c(px - math.cos(m[2]) * 12, py - math.sin(m[2]) * 12, "*", palette.NECRO_GLOW[1])
    host = boss.host                               # (possession: the host's eyes flash)
    if host is not None and host.alive and boss.blink > 0:
        px, py = camera.world_to_px(host.x, host.y)
        batch.put_c(px, py - 14, "o o", palette.NECRO_GLOW[0])
    batch.flush()

    # Him.
    x, y = camera.world_to_px(boss.x, boss.y)
    frame = int(t * 3) % 4 if boss.lich else int(boss.walked * 1.2) % 4
    still = boss.host is not None
    draw_character(bank, x, y - SCALE, "necromancer", SCALE, math.cos(boss.facing) < 0,
                   0 if still else frame, boss.hurt_flash > 0, _pose(boss))
    batch = _Batch(text)
    if still:                                      # (his body, shielded while he hides)
        for dx, dy, glyph, c in _ring(12, 44, "+", palette.SOUL_COL[1], t * 2):
            batch.put_c(x + dx, y - 10 + dy, glyph, c)
    if boss.reviving:                              # (his soul tearing free)
        for k in range(10):
            a = t * 4 + k * math.tau / 10
            batch.put_c(x + math.cos(a) * (20 + (t * 30) % 40), y - 40 - (t * 25) % 80,
                        "*", palette.SOUL_COL[k % 2])
    if boss.arc is not None:                       # (the reap's sweep)
        a, reach, half = boss.arc
        for k in range(11):
            aa = a - half + 2 * half * k / 10
            px, py = camera.world_to_px(boss.x + math.cos(aa) * reach, boss.y + math.sin(aa) * reach)
            batch.put_c(px, py, ")" if math.cos(aa) > 0 else "(", palette.NECRO_GLOW[0])
    if boss.dazed > 0:
        for dx, dy, glyph, c in _ring(5, 22, "*", palette.NECRO_TELL[0], t * 4, 0.4):
            batch.put_c(x + dx, y - 70 + dy, glyph, c)
    batch.flush()


def draw_necro_marks(text, bank: SpriteBank, camera: Camera, boss, hero, time: float) -> None:
    """CRUSH over corpses near you (and STOMP progress), FIND HIM while he
    hides, BREAK A RIB while you're caged."""
    batch = _Batch(text)
    cw = text.display.cell_w
    for c in boss.corpses:
        if math.hypot(c[0] - hero.x, c[1] - hero.y) > 7:
            continue
        px, py = camera.world_to_px(c[0], c[1])
        s = "CRUSH"
        batch.put_px(px - len(s) * cw / 2, py - 36, s, palette.BONE_FG, palette.HUD_PANEL)
    if boss.caged is hero:
        hx, hy = camera.world_to_px(hero.x, hero.y)
        s = "CAGED! BREAK A RIB"
        batch.put_px(hx - len(s) * cw / 2, hy - 70, s, palette.BONE_FG, palette.HUD_PANEL)
    batch.flush()
