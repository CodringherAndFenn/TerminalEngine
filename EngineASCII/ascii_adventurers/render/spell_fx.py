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
                from ..systems.spells import aura_radius
                r = aura_radius(hero, s)
                hx, hy = camera.world_to_px(hero.x, hero.y)
                n = max(10, int(r * 6))
                turn = steps * 0.01
                for k in range(n):
                    a = turn + k * math.tau / n
                    col = palette.EMBER[(k + steps // 6) % 3]
                    batch.put_c(hx + math.cos(a) * r * config.TILE_PX_W,
                                hy + math.sin(a) * r * config.TILE_PX_H,
                                "'" if (k + steps // 10) % 2 else ".", col)
                for x, y, left in s.left:               # (M28.3i Afterburn: left behind)
                    lx, ly = camera.world_to_px(x, y)
                    for k in range(0, n, 2):
                        a = -turn + k * math.tau / n
                        batch.put_c(lx + math.cos(a) * r * config.TILE_PX_W,
                                    ly + math.sin(a) * r * config.TILE_PX_H,
                                    "." if left < 1.0 and k % 4 else "'",
                                    palette.EMBER[1 + (k + steps // 6) % 2])
        for foe, left, _, _ in hero.fireflies:          # (M28.3i Firefly: buzzing round it)
            if not foe.alive:
                continue
            fx, fy = camera.world_to_px(foe.x, foe.y)
            a = steps * 0.35 + left * 3.0
            r = (foe.hit_radius + 0.3) * config.TILE_PX_W
            batch.put_c(fx + math.cos(a) * r, fy + math.sin(a) * r * 0.7, "*",
                        palette.EMBER[(steps // 3) % 2])
    batch.flush()


def draw_summons(text, camera: Camera, players, zones, steps: int) -> None:
    """What spells leave in the world (wolves, runes, flasks, the storm
    cloud, totems, turrets) and the zones on the ground (poison pools,
    Ball Lightning's crackle, roll trails)."""
    from ..systems.spells import cloud_position, dire, eye_position, rune_links
    batch = _Batch(text)
    tw, th = config.TILE_PX_W, config.TILE_PX_H
    for z in zones:
        x, y = camera.world_to_px(z.x, z.y)
        if z.kind == "pool":
            # (M28.2f: a Witch's brew pool takes its status's colors.)
            cols = palette.POOL if z.inflicts in (None, "poison") else \
                palette.TRAIL.get(z.inflicts, palette.POOL)
            n = max(8, int(z.radius * 7))
            for k in range(n):
                a = k * math.tau / n + steps * 0.004
                rr = z.radius * (0.35 + 0.65 * ((k * 7) % 5) / 4)
                batch.put_c(x + math.cos(a) * rr * tw, y + math.sin(a) * rr * th,
                            "o" if k % 3 == 0 else ".", cols[k % 2])
        elif z.kind == "miasma":
            # M28.3c Miasma: a dying enemy's statuses, a drifting cloud of
            # their colours, thinning as it ends.
            cols = palette.TRAIL.get(z.inflicts, palette.POOL)
            fade = 1.0 - z.age / z.life
            for k in range(7):
                a = k * math.tau / 7 + z.age * 0.8 + len(z.inflicts or "")
                rr = z.radius * (0.3 + 0.7 * ((k * 3) % 4) / 3)
                batch.put_c(x + math.cos(a) * rr * tw, y + math.sin(a) * rr * th - z.age * 2,
                            "o" if k % 3 == 0 and fade > 0.4 else ".", cols[k % 2])
        elif z.kind == "ice":
            # M28.3i Black ice: the nova's ring, frosted over, thinning as it melts.
            n = max(10, int(z.radius * 8))
            fade = 1.0 - z.age / z.life
            for k in range(n):
                if fade < 0.4 and k % 2:
                    continue
                a = k * math.tau / n
                rr = z.radius * (0.55 + 0.45 * ((k * 5) % 7) / 6)
                batch.put_c(x + math.cos(a) * rr * tw, y + math.sin(a) * rr * th,
                            "*" if k % 3 == 0 else ".", palette.FROZEN[k % 2])
        elif z.kind == "puddle":
            # M28.2f Downpour: rain rings on the ground under the storm cloud.
            n = max(6, int(z.radius * 4))
            for k in range(n):
                a = k * math.tau / n + k * 0.9
                rr = z.radius * (0.2 + 0.75 * ((k * 0.37) % 1.0))
                batch.put_c(x + math.cos(a) * rr * tw, y + math.sin(a) * rr * th,
                            "o" if (k + steps // 9) % 4 == 0 else ".", palette.PUDDLE[k % 2])
        elif z.kind == "wisp":
            # M28.2f Will-o'-wisps: a bobbing flame, sparks round it.
            bob = math.sin(steps * 0.15 + z.x) * 3
            batch.put_c(x, y - 8 + bob, "*", palette.EMBER[(steps // 5) % 2])
            for k in range(5):
                a = k * math.tau / 5 + z.age * 2.0
                batch.put_c(x + math.cos(a) * z.radius * tw * 0.7,
                            y + math.sin(a) * z.radius * th * 0.7,
                            "'" if (k + steps // 6) % 2 else ".", palette.EMBER[1 + k % 2])
        elif z.kind == "ball":
            # M28.2g Thunderball: a big rolling ball of sparks.
            spin = z.age * 9.0
            batch.put_c(x, y, "@", palette.CRACKLE[(steps // 3) % 2])
            for ring, n in ((0.45, 6), (1.0, 10)):
                for k in range(n):
                    a = k * math.tau / n + spin * (1 if ring < 1 else -0.6)
                    batch.put_c(x + math.cos(a) * z.radius * ring * tw * 0.8,
                                y + math.sin(a) * z.radius * ring * th * 0.8,
                                "*" if (k + steps // 3) % 2 else "+", palette.CRACKLE[k % 2])
        elif z.kind == "well":
            # M28.2g Singularity: a dark spiral turning in on itself.
            for k in range(14):
                f = ((k / 14) + z.age * 1.5) % 1.0
                a = k * 2.4 + z.age * 6.0
                rr = z.radius * (1.0 - f)
                batch.put_c(x + math.cos(a) * rr * tw, y + math.sin(a) * rr * th,
                            "." if f < 0.6 else "o", palette.SHOT_DART[1][1 if f < 0.6 else 0])
            batch.put_c(x, y, "@", palette.SHOT_DART[0])
        elif z.kind == "thorns":
            # M28.2h Seed storm: a sprouting tuft of thorns, wilting at the end.
            grow = min(1.0, z.age / 0.25)
            col = palette.LEAF_FLURRY[0 if z.age < z.life * 0.7 else 2]
            batch.put_c(x, y, "Y", col)
            for k in range(5):
                a = k * math.tau / 5 + 0.3
                batch.put_c(x + math.cos(a) * z.radius * grow * tw * 0.8,
                            y + math.sin(a) * z.radius * grow * th * 0.8,
                            "^" if k % 2 else "v", palette.THORN_TELL[k % 2])
        elif z.kind == "curse":
            # P11: a swamp hag's curse: a dark puddle growing to its edge.
            grow = min(1.0, z.age / z.life)
            col = palette.CURSE[0 if int(z.age * 10) % 2 else 1]
            for k in range(10):
                a = k * math.tau / 10
                batch.put_c(x + math.cos(a) * z.radius * grow * tw,
                            y + math.sin(a) * z.radius * grow * th, ":", col)
            batch.put_c(x, y, "@", col)
        elif z.kind == "gas":
            # P11: a bloated corpse's cloud, drifting puffs.
            col = palette.GAS[0 if z.age < z.life * 0.7 else 1]
            for k in range(8):
                a = k * math.tau / 8 + z.age * 0.6
                rr = z.radius * (0.35 + 0.6 * ((k * 0.37) % 1.0))
                batch.put_c(x + math.cos(a) * rr * tw, y + math.sin(a) * rr * th,
                            "o" if k % 2 else ".", col)
        elif z.kind in ("pollen", "slime", "mold"):
            # P12: the myconid's healing pollen, a snail's slime, a core's mold.
            cols = {"pollen": palette.POLLEN, "slime": palette.SLIME, "mold": palette.MOLD}[z.kind]
            glyph = {"pollen": "*", "slime": ",", "mold": "%"}[z.kind]
            col = cols[0 if z.age < z.life * 0.75 else 1]
            n = 8 if z.kind == "pollen" else 5
            for k in range(n):
                a = k * math.tau / n + (z.age * 0.5 if z.kind == "pollen" else 0.0)
                rr = z.radius * (0.3 + 0.65 * ((k * 0.41) % 1.0))
                batch.put_c(x + math.cos(a) * rr * tw, y + math.sin(a) * rr * th,
                            glyph if k % 2 else ".", col)
        elif z.kind == "stake":
            pass                               # (the javelin is the tile itself)
        elif z.kind == "web":
            # P8: a giant spider's sticky patch: strands across it, fading at the end.
            col = palette.WEB[0 if z.age < z.life * 0.75 else 1]
            for k in range(6):
                a = k * math.tau / 6
                for rr in (0.45, 0.9):
                    batch.put_c(x + math.cos(a) * z.radius * rr * tw,
                                y + math.sin(a) * z.radius * rr * th, "+" if rr < 0.5 else ".", col)
            batch.put_c(x, y, "#", col)
        elif z.kind == "burn_in":
            # M28.3l Burn-in: the colors' crossing glowing in turn, fading.
            fade = z.age >= z.life * 0.6
            for k in range(5):
                a = k * math.tau / 5 + z.age * 4.0
                head, trail = palette.RAINBOW_SHOTS[(k + steps // 4) % 5]
                batch.put_c(x + math.cos(a) * z.radius * tw * 0.7,
                            y + math.sin(a) * z.radius * th * 0.7, "*" if k % 2 else "+",
                            trail[0] if fade else head)
            batch.put_c(x, y, "o", palette.RAINBOW_SHOTS[(steps // 3) % 5][0])
        elif z.kind == "trail":
            # A roll's trail patch (M18): flickering, fading as it runs out.
            cols = palette.TRAIL.get(z.inflicts, palette.TRAIL["burn"])
            fresh = z.age < z.life * 0.6
            glyphs = ("^", "*", "'") if z.inflicts == "burn" else ("*", "+", ".")
            for k in range(3):
                a = k * math.tau / 3 + (k * 1.7 + steps * 0.15)
                rr = z.radius * 0.45
                batch.put_c(x + math.cos(a) * rr * tw, y + math.sin(a) * rr * th,
                            glyphs[(k + steps // 6) % 3], cols[0 if fresh and k != 2 else 1])
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
            if kind == "rune":
                # M28.2f Rune lines: dots between linked runes.
                for r1, r2 in rune_links(hero, s):
                    n = max(2, int(math.hypot(r2["x"] - r1["x"], r2["y"] - r1["y"]) * 2))
                    for k in range(1, n):
                        f = k / n
                        x, y = camera.world_to_px(r1["x"] + (r2["x"] - r1["x"]) * f,
                                                  r1["y"] + (r2["y"] - r1["y"]) * f)
                        batch.put_c(x, y, ".", palette.RUNE[(k + steps // 8) % 2])
            for t in s.things:
                if kind == "wolf":
                    x, y = camera.world_to_px(t["x"], t["y"])
                    left = math.cos(t["facing"]) < 0
                    if dire(hero) > 1:                  # (M28.2f Dire wolves: twice the size)
                        batch.put_c(x, y - 12, "/\\_" if left else "_/\\", palette.WOLF[1])
                        batch.put_c(x, y + 4, "<WW" if left else "WW>", palette.WOLF[0])
                    else:
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
                if hero.stats is not None and hero.stats.has("storm_cloud+9"):
                    x, y = camera.world_to_px(*eye_position(hero, s))   # (Eye of the storm)
                    batch.put_c(x, y - 6, "(@)", shade)
                    batch.put_c(x, y + 10, "'" if (steps // 8) % 2 else ".", palette.CRACKLE[0])
    batch.flush()


def draw_statuses(text, camera: Camera, enemies, marked, duels=(), wanted=()) -> None:
    """Pips over every enemy with a status (one per status, in a row), ice
    round a frozen one, "z"s over a sleeping one (Cradlesong +3), brackets
    round each hero's marked target, "x"s by each duelist (M28.2i) and "$"s
    over each wanted enemy (Bountymark Ring (L), M28.3h)."""
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
        if st.asleep > 0:
            bob = (st.asleep * 10) % 6
            for k in range(2):
                batch.put_c(x + 8 + k * 9, top - 10 - k * 10 - bob, "z", palette.SLEEP)
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
    for e in duels:
        if not e.alive:
            continue
        x, y = camera.world_to_px(e.x, e.y)
        r = e.hit_radius * config.TILE_PX_W + 14
        batch.put_c(x - r, y - 12, "x", palette.DUEL)
        batch.put_c(x + r, y - 12, "x", palette.DUEL)
    for e in wanted:
        if not e.alive:
            continue
        x, y = camera.world_to_px(e.x, e.y)
        top = y - e.hit_radius * config.TILE_PX_H - 34
        for k in (-1, 0, 1):
            batch.put_c(x + k * 10, top, "$", palette.WANTED)
    batch.flush()


def draw_overcast(text, camera: Camera, players, steps: int) -> None:
    """Cloudburst Bow (L), Overcast (M28.3k): a grey cloud of "~"s over
    each spot still raining."""
    batch = _Batch(text)
    r = config.ARROW_RAIN[2]
    for p in players:
        for x, y, *_ in p.hero.overcast:
            cx, cy = camera.world_to_px(x, y)
            for k in range(-2, 3):
                drift = ((steps // 10 + k) % 2) * 3
                batch.put_c(cx + k * r * config.TILE_PX_W / 2.5 + drift,
                            cy - r * config.TILE_PX_H - 6, "~", palette.OVERCAST[k % 2])
    batch.flush()


def draw_possessed(text, camera: Camera, enemies, steps: int) -> None:
    """Ghostwood Staff (L), Possession (M28.3j): a ghost fighting for you
    gets a flickering ghostly outline and "~"s over its head."""
    batch = _Batch(text)
    col = palette.HAUNT_WISP[(steps // 6) % 2]
    for e in enemies:
        if not e.alive or getattr(e, "possessed", None) is None:
            continue
        x, y = camera.world_to_px(e.x, e.y)
        rx = e.hit_radius * config.TILE_PX_W + 8
        ry = e.hit_radius * config.TILE_PX_H + 6
        for gx, gy, g in ((-rx, 0, "("), (rx, 0, ")"), (-10, -ry - 12, "~"), (0, -ry - 16, "~"),
                          (10, -ry - 12, "~")):
            batch.put_c(x + gx, y + gy, g, col)
    batch.flush()


def draw_ghost_sight(text, camera: Camera, world, players, enemies, steps: int) -> None:
    """Ghostwood Staff +9 (Ghost sight): enemies a wall hides from a hero
    wearing it, within GHOSTWOOD_SIGHT tiles, get a ghostly outline -- what
    their darts go after when nothing is near the aim."""
    from ..systems.raycast import first_hit
    seers = [p.hero for p in players
             if p.hero.stats is not None and p.hero.stats.has("phase_darts+9")]
    if not seers:
        return
    batch = _Batch(text)
    col = palette.HAUNT_WISP[(steps // 8) % 2]
    for e in enemies:
        if not e.alive or not e.hittable:
            continue
        for h in seers:
            if math.hypot(e.x - h.x, e.y - h.y) <= config.GHOSTWOOD_SIGHT \
                    and first_hit(world.tile_at, h.x, h.y, e.x, e.y) is not None:
                x, y = camera.world_to_px(e.x, e.y)
                rx = e.hit_radius * config.TILE_PX_W + 8
                ry = e.hit_radius * config.TILE_PX_H + 6
                for gx, gy, g in ((-rx, -ry, "."), (rx, -ry, "."), (-rx, ry, "'"), (rx, ry, "'"),
                                  (-rx, 0, "("), (rx, 0, ")")):
                    batch.put_c(x + gx, y + gy, g, col)
                break
    batch.flush()
