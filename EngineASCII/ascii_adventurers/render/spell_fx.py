"""
render/spell_fx.py -- the card system's visuals (M14): XP gems on the
ground, the heroes' spells (orbiting daggers, the ember aura), and what's
wrong with an enemy (status pips, frozen, Hunter's Mark).

Text glyphs like the rest of render/ascii_fx.py, batched the same way.
Animation reads the simulation step counter (`steps`) only, never the
clock, and never changes game state.
"""

from __future__ import annotations

import math

from .. import config, palette
from ..engine_ext.camera import Camera
from ..systems.collision import screen_angle
from .ascii_fx import _LINE, _Batch

# Glyph per status pip.
_PIP = {"burn": "^", "poison": "o", "bleed": ",", "chill": "*", "shock": "!"}
_PIP_ORDER = ("burn", "poison", "bleed", "chill", "shock")
_GEM_GLYPH = ("+", "*", "@")


def draw_gems(text, camera: Camera, gems, steps: int) -> None:
    """A gem twinkles between its bright and dark shade; one that's about
    to fade blinks."""
    if not gems:
        return
    batch = _Batch(text)
    x0, y0 = camera.canvas_to_world(0, 0)
    x1, y1 = camera.canvas_to_world(camera.view_w, camera.view_h)
    for i, g in enumerate(gems):
        if not (x0 - 1 <= g.x <= x1 + 1 and y0 - 1 <= g.y <= y1 + 1):
            continue
        if g.target is None and g.age > config.GEM_LIFETIME - 5 and (steps // 8) % 2:
            continue
        bright, dark = palette.GEM[g.tier]
        x, y = camera.world_to_px(g.x, g.y)
        batch.put_c(x, y, _GEM_GLYPH[g.tier], bright if (steps // 20 + i) % 3 else dark)
    batch.flush()


def draw_spells(text, camera: Camera, players, steps: int) -> None:
    batch = _Batch(text)
    for p in players:
        hero = p.hero
        for s in p.spells.values():
            kind = s.spec.kind
            if kind == "orbit":
                for x, y, facing in s.dagger_positions(hero):
                    px, py = camera.world_to_px(x, y)
                    oct_ = round(screen_angle(facing) / (math.pi / 4)) % 8
                    batch.put_c(px, py, _LINE[oct_], palette.DAGGER)
            elif kind == "aura":
                # A slow ring of embers at the aura's edge, flickering.
                r = s.params["radius"] * (hero.stats.area_scale if hero.stats else 1.0)
                hx, hy = camera.world_to_px(hero.x, hero.y)
                n = max(10, int(r * 6))
                turn = steps * 0.01
                for k in range(n):
                    a = turn + k * math.tau / n
                    col = palette.EMBER[(k + steps // 6) % 3]
                    batch.put_c(hx + math.cos(a) * r * config.TILE_PX_W,
                                hy + math.sin(a) * r * config.TILE_PX_H,
                                "'" if (k + steps // 10) % 2 else ".", col)
    batch.flush()


def draw_statuses(text, camera: Camera, enemies, marked) -> None:
    """Pips over every enemy with a status (one per status, in a row), ice
    round a frozen one, and brackets round each hero's marked target."""
    batch = _Batch(text)
    x0, y0 = camera.canvas_to_world(0, 0)
    x1, y1 = camera.canvas_to_world(camera.view_w, camera.view_h)
    for e in enemies:
        st = e.status
        if st is None or not e.alive or not (x0 - 2 <= e.x <= x1 + 2 and y0 - 2 <= e.y <= y1 + 2):
            continue
        x, y = camera.world_to_px(e.x, e.y)
        top = y - e.hit_radius * config.TILE_PX_H - 22
        pips = [n for n in _PIP_ORDER if st.has(n)]
        for i, name in enumerate(pips):
            batch.put_c(x + (i - (len(pips) - 1) / 2) * 10, top, _PIP[name],
                        palette.STATUS_PIP[name])
        if st.frozen > 0:
            r = e.hit_radius * config.TILE_PX_W + 4
            for k in range(6):
                a = k * math.tau / 6
                batch.put_c(x + math.cos(a) * r, y + math.sin(a) * r * 1.1, "#" if k % 2 else "*",
                            palette.FROZEN[k % 2])
    for e in marked:
        if not e.alive:
            continue
        x, y = camera.world_to_px(e.x, e.y)
        r = e.hit_radius * config.TILE_PX_W + 8
        batch.put_c(x - r, y, "[", palette.MARK)
        batch.put_c(x + r, y, "]", palette.MARK)
    batch.flush()
