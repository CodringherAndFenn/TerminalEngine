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


def draw_summons(text, camera: Camera, players, zones, steps: int) -> None:
    """What spells leave in the world (wolves, runes, flasks, the storm
    cloud, totems, turrets) and the zones on the ground (poison pools,
    Ball Lightning's crackle)."""
    from ..systems.spells import cloud_position
    batch = _Batch(text)
    tw, th = config.TILE_PX_W, config.TILE_PX_H
    for z in zones:
        x, y = camera.world_to_px(z.x, z.y)
        if z.kind == "pool":
            n = max(8, int(z.radius * 7))
            for k in range(n):
                a = k * math.tau / n + steps * 0.004
                rr = z.radius * (0.35 + 0.65 * ((k * 7) % 5) / 4)
                batch.put_c(x + math.cos(a) * rr * tw, y + math.sin(a) * rr * th,
                            "o" if k % 3 == 0 else ".", palette.POOL[k % 2])
        else:
            for k in range(6):
                a = k * math.tau / 6 + steps * 0.3
                batch.put_c(x + math.cos(a) * z.radius * tw * 0.6,
                            y + math.sin(a) * z.radius * th * 0.6,
                            "*" if (k + steps // 4) % 2 else "+", palette.CRACKLE[k % 2])
    for p in players:
        hero = p.hero
        for s in p.spells.values():
            kind = s.spec.kind
            for t in s.things:
                if kind == "wolf":
                    x, y = camera.world_to_px(t["x"], t["y"])
                    left = math.cos(t["facing"]) < 0
                    batch.put_c(x, y, "<w" if left else "w>", palette.WOLF[0])
                elif kind == "rune":
                    x, y = camera.world_to_px(t["x"], t["y"])
                    batch.put_c(x, y, "#" if (steps // 15) % 2 else "+", palette.RUNE[0])
                elif kind == "flask":
                    f = min(1.0, t["t"] / t["flight"])
                    gx = t["x0"] + (t["x1"] - t["x0"]) * f
                    gy = t["y0"] + (t["y1"] - t["y0"]) * f
                    x, y = camera.world_to_px(gx, gy)
                    batch.put_c(x, y - 40 * 4 * f * (1 - f), "o", palette.POOL[0])
                elif kind == "totem":
                    x, y = camera.world_to_px(t["x"], t["y"])
                    batch.put_c(x, y - 12, "+", palette.TOTEM[0])
                    batch.put_c(x, y, "||", palette.TOTEM[1])
                elif kind == "turret":
                    x, y = camera.world_to_px(t["x"], t["y"])
                    batch.put_c(x, y - 10, "o", palette.TURRET[0])
                    batch.put_c(x, y + 4, "/\\", palette.TURRET[1])
            if kind == "cloud":
                x, y = camera.world_to_px(*cloud_position(hero))
                shade = palette.CLOUD[(steps // 20) % 2]
                batch.put_c(x, y - 6, "(@@)", shade)
                batch.put_c(x, y + 10, "' '" if (steps // 8) % 2 else " ' ", palette.CRACKLE[0])
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
