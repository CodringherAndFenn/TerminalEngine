"""
render/relics.py -- what the desert's and the ruins' boss uniques put in
the world (M28.5b; design/GEAR.md 21), drawn for every living hero:

  Dung Ball        the ball ("@", ringed with "o" as it grows)
  Rod of Fission   the rod ("!" with a flicker of ".")
  Mr. Buttons      the bear at his hero's heels, an HP bar once hurt,
                   "zz" while he's down
  Bat Form Boots   a rolling hero as a cloud of bats (the body isn't drawn)
  Lace Parasol     its canopy in front while the attack is held
  Hourglass Ring   a slow ring of sand while shots crawl
  Hermit's Furs    frost circling a hero who's gathered it
M28.5c:
  Cleaver of Cuddles  the blade orbiting its hero
  Tripwire Boots   the wires (dotted lines)
  Rootbound Boots  roots under a hero rooted in; Heartwood Ring: leaves
                   while a tree heals you
  Phylactery       a shade's pale ring and the kills it still needs
  Lich's Gaze      the eye building on the enemy under your aim, then the mark
  on enemies       "?" tripped (Fly Agaric), "=" bound (the Wig's ink, a
                   tripwire), "%" inked (can't see), blighted thorns
(The Corpse Candle and the Mycelial Ring's spores are zones.)

(Sand Slippers' dunes are tiles; the Crown's black ice is a zone,
render/spell_fx.draw_summons.)
"""

from __future__ import annotations

import math

from .. import config, palette
from ..engine_ext.camera import Camera
from .ascii_fx import _Batch
from .characters import draw_character
from .sprites import SpriteBank

BEAR_SCALE = 3.0


def draw_relics(text, bank: SpriteBank, camera: Camera, players, enemies, steps: int) -> None:
    batch = _Batch(text)
    tw, th = config.TILE_PX_W, config.TILE_PX_H
    bears = []
    for p in players:
        h = p.hero
        st = h.stats
        if st is None:
            continue
        b = h.ball
        if b is not None and b.alive:
            x, y = camera.world_to_px(b.x, b.y)
            batch.put_c(x, y, "@", palette.DUNG_BALL[0])
            if b.radius > 0.7:
                n = max(6, int(b.radius * 6))
                turn = b.rolled * 0.8
                for k in range(n):
                    a = turn + k * math.tau / n
                    batch.put_c(x + math.cos(a) * b.radius * tw * 0.8,
                                y + math.sin(a) * b.radius * th * 0.8,
                                "o" if k % 2 else ".", palette.DUNG_BALL[k % 2])
        if h.rod is not None and st.has("rod_of_fission"):
            x, y = camera.world_to_px(h.rod[0], h.rod[1])
            hot = h.rod[2] < 0.4
            batch.put_c(x, y, "!", palette.FISSION_ROD[0 if hot or (steps // 8) % 2 else 1])
            if hot:
                for k in range(4):
                    a = k * math.tau / 4 + steps * 0.2
                    batch.put_c(x + math.cos(a) * tw * 0.7, y + math.sin(a) * th * 0.5, ".",
                                palette.FISSION_ROD[0])
        bear = h.bear
        if bear is not None and st.has("mr_buttons"):
            x, y = camera.world_to_px(bear.x, bear.y)
            if bear.alive:
                bears.append((x, y, h.x < bear.x, bear.hurt_flash > 0))
                if bear.hp < bear.max_hp:
                    _bar(batch, x, y - 32, bear.hp / bear.max_hp)
            else:
                batch.put_c(x, y, "zz" if (steps // 20) % 2 else "z.", palette.BEAR_DOWN)
        if h.bats:
            for k in range(5):
                a = k * math.tau / 5 + steps * 0.35
                r = 0.5 + 0.25 * ((k * 3) % 4) / 3
                flap = (steps // 4 + k) % 2
                x, y = camera.world_to_px(h.x + math.cos(a) * r, h.y + math.sin(a) * r * 0.7)
                batch.put_c(x, y, "^v^" if flap else "vVv", palette.BAT_SWARM[k % 2])
        if h.trigger and st.has("parasol") and not h.bats:
            half = math.radians(min(90.0, st.uniques.get("parasol", 55.0)))
            r = h.hit_radius + 0.9
            n = 7
            for k in range(n):
                a = h.aim_angle - half + 2 * half * k / (n - 1)
                x, y = camera.world_to_px(h.x + math.cos(a) * r, h.y + math.sin(a) * r)
                edge = k in (0, n - 1)
                batch.put_c(x, y, "'" if edge else ("=" if k % 2 else "-"),
                            palette.PARASOL[1 if edge or k % 2 else 0])
        if h.hourglass_t > 0:
            r = config.U_HOURGLASS[1]
            for k in range(24):
                a = k * math.tau / 24 + steps * 0.004
                x, y = camera.world_to_px(h.x + math.cos(a) * r, h.y + math.sin(a) * r)
                batch.put_c(x, y, ":" if k % 3 == 0 else ".", palette.HOURGLASS)
        if h.frost:
            r = h.hit_radius + 0.5
            for k in range(6):
                a = k * math.tau / 6 - steps * 0.03
                x, y = camera.world_to_px(h.x + math.cos(a) * r, h.y + math.sin(a) * r * 0.8)
                batch.put_c(x, y, "*" if (k + steps // 10) % 2 else "+", palette.FROST_GATHER)
        _draw_5c(batch, camera, h, st, steps)
        _draw_swarms(batch, camera, h, steps)
        _draw_overseers(batch, camera, h, st, steps)
        _draw_fossil(batch, camera, h, st, steps)
    _draw_marks(batch, camera, players, enemies, steps)
    batch.flush()
    for x, y, left, hurt in bears:
        draw_character(bank, x, y - 6, "mr_buttons", BEAR_SCALE, left, 0, hurt)
    for p in players:                                  # (M31.5: the Spirit Herd's mammoths)
        for x0, y0, a, done, _ in p.hero.herd:
            from .pangaea import _figure
            x, y = x0 + math.cos(a) * done, y0 + math.sin(a) * done
            frame = int(done * config.WALK_STEPS_PER_TILE) % 4
            _figure(bank, camera, x, y, "mammoth", config.ENEMIES["mammoth"].scale,
                    math.cos(a) < 0, "ochre", frame)


def _draw_swarms(batch, camera: Camera, h, steps: int) -> None:
    """Swarm Ring (M31.5): its river of insects streaming out along its
    line, in three rows."""
    long, half = config.U_SWARM[2], config.U_SWARM[3]
    t = steps / 60
    for x0, y0, a, left, _ in h.swarms:
        ca, sa = math.cos(a), math.sin(a)
        for row, (glyph, col) in enumerate(((".", palette.SWARM[1]), (":", palette.SWARM[0]),
                                            ("'", palette.SWARM[2]))):
            off = (row - 1) * half * 0.6 + math.sin(t * 5 + row * 2.1) * 0.25
            k = (t * 7.0 + row * 0.4) % 1.0
            while k <= long:
                x, y = x0 + ca * k - sa * off, y0 + sa * k + ca * off
                px, py = camera.world_to_px(x, y)
                batch.put_c(px, py, glyph, col)
                k += 1.0


def _bar(batch, x: float, y: float, frac: float) -> None:
    """A little HP bar centred on (x, y): 6 cells, "=" for what's left."""
    n = 6
    full = max(0, min(n, round(frac * n)))
    x0, y0 = x - n * batch.cw / 2, y - batch.ch / 2
    if full:
        batch.put_px(x0, y0, "=" * full, palette.HP_BAR_FULL, None)
    if full < n:
        batch.put_px(x0 + full * batch.cw, y0, "." * (n - full), palette.HP_BAR_EMPTY, None)


_BLADE = ("-", "\\", "|", "/")


def _draw_5c(batch, camera: Camera, h, st, steps: int) -> None:
    tw, th = config.TILE_PX_W, config.TILE_PX_H
    if h.cleaver is not None and st.has("cleaver_of_cuddles"):
        from ..systems.relics import cleaver_spot
        bx, by = cleaver_spot(h)
        x, y = camera.world_to_px(bx, by)
        k = round((h.cleaver[0] % math.pi) / (math.pi / 4)) % 4
        batch.put_c(x, y, _BLADE[k], palette.CLEAVER[0])
        if h.cleaver[1] > 1.2:                      # (spun up: a red streak behind)
            a = h.cleaver[0] - 0.35
            r = config.U_CLEAVER[0]
            x2, y2 = camera.world_to_px(h.x + math.cos(a) * r, h.y + math.sin(a) * r)
            batch.put_c(x2, y2, ".", palette.CLEAVER[1])
    for w in h.wires:
        x0, y0, x1, y1, left = w
        n = max(2, int(math.hypot(x1 - x0, y1 - y0) * 2))
        if left < 1.0 and (steps // 6) % 2:
            continue                                # (about to snap: it blinks)
        for k in range(n + 1):
            f = k / n
            x, y = camera.world_to_px(x0 + (x1 - x0) * f, y0 + (y1 - y0) * f)
            batch.put_c(x, y, "+" if k in (0, n) else ".", palette.TRIPWIRE)
    if st.has("rootbound_boots") and h.roots > 0:
        x, y = camera.world_to_px(h.x, h.y + h.hit_radius)
        batch.put_c(x, y + 4, "vVv" if h.still_t >= 0.5 else "v v", palette.ROOTBOUND[0])
    if h.near_tree and st.has("heartwood_ring") and h.hp < h.max_hp:
        a = steps * 0.04
        x, y = camera.world_to_px(h.x + math.cos(a) * 0.8, h.y - 0.6 + math.sin(a) * 0.3)
        batch.put_c(x, y, "*", palette.ROOTBOUND[1])
    if h.shade > 0:
        for k in range(8):
            a = k * math.tau / 8 + steps * 0.05
            x, y = camera.world_to_px(h.x + math.cos(a) * 1.0, h.y + math.sin(a) * 0.8)
            batch.put_c(x, y, ".", palette.SHADE[k % 2])
        x, y = camera.world_to_px(h.x, h.y - h.hit_radius - 1.2)
        need = max(0, config.U_PHYLACTERY[1] - h.shade_kills)
        batch.put_c(x, y, f"{need} KILLS {h.shade:.0f}s", palette.SHADE[0])
    g = h.gaze
    if g is not None and g.alive and st.has("lichs_gaze") \
            and id(h) not in g.__dict__.get("lich_marks", ()):
        hold = config.U_LICHS_GAZE[1]
        x, y = camera.world_to_px(g.x, g.y - g.hit_radius - 0.9)
        batch.put_c(x, y, "o" if h.gaze_t < hold / 2 else "O", palette.LICH[1])


def _draw_marks(batch, camera: Camera, players, enemies, steps: int) -> None:
    """The relics' marks on enemies."""
    me = [p.hero for p in players]
    if not me:
        return
    now = me[0].time
    for e in enemies:
        if not e.alive:
            continue
        x, y = camera.world_to_px(e.x, e.y)
        top = y - (e.hit_radius + 0.8) * config.TILE_PX_H
        s = e.status
        if s is not None and s.wander > 0:
            batch.put_c(x, top - (2 if (steps // 8) % 2 else 0), "?", palette.TRIPPED)
        if s is not None and s.bound > 0:
            batch.put_c(x, y + e.hit_radius * config.TILE_PX_H * 0.6, "===", palette.INK)
        ink = e.__dict__.get("ink_blot")
        if ink is not None and ink[1] > now:
            batch.put_c(x + 10, top, "%", palette.INK)
        blight = e.__dict__.get("blighted")
        if blight is not None and blight[0] > now:
            batch.put_c(x - 10, top, "*" if (steps // 10) % 2 else "+", palette.BLIGHT)
        marks = e.__dict__.get("lich_marks")
        if marks and any(id(h) in marks for h in me):
            batch.put_c(x, top - 8, "<O>", palette.LICH[0])
        seen = e.__dict__.get("seen_by")                 # (M32.5: the Overseer's Eye: SEEN)
        if seen and any(seen.get(id(h), -1.0) > h.time for h in me):
            batch.put_c(x, top - 16, "(o)", palette.SEEN_MARK[(steps // 12) % 2])


def _draw_overseers(batch, camera: Camera, h, st, steps: int) -> None:
    """M32.5: the Overseer's relics on a hero: the searchlight sweeping
    along the aim (the Overseer's Eye), the Cell Key ready (a key by you),
    the Black Box recording (a red dot while it holds what hurt you), the
    Scrap Plating's plates round you."""
    tw, th = config.TILE_PX_W, config.TILE_PX_H
    if h.eye_sweep > 0:
        _, _, _, deg, long, _, _ = config.U_EYE
        half = math.radians(deg) / 2
        for side in (-1, 1):
            a = h.aim_angle + side * half
            for k in range(1, int(long / 1.2) + 1):
                d = k * 1.2
                x, y = camera.world_to_px(h.x + math.cos(a) * d, h.y + math.sin(a) * d)
                batch.put_c(x, y, ".", palette.RELIC_SEARCHLIGHT[0])
        n = 10
        for k in range(n + 1):
            a = h.aim_angle - half + 2 * half * k / n
            x, y = camera.world_to_px(h.x + math.cos(a) * long, h.y + math.sin(a) * long)
            batch.put_c(x, y, "o" if k % 2 else ".", palette.RELIC_SEARCHLIGHT[1])
    x, y = camera.world_to_px(h.x, h.y)
    if h.cell_ready and st.has("cell_key"):
        batch.put_c(x + tw * 0.9, y - th * 1.1, "o-", palette.CELL_KEY_READY)
    if h.box_log and st.has("black_box"):
        batch.put_c(x - tw * 0.9, y - th * 1.1, "*" if (steps // 15) % 2 else ".", palette.BLACK_BOX_REC[0])
    for k in range(h.scrap_plates):
        a = k * math.tau / max(1, h.scrap_plates) + steps * 0.02
        batch.put_c(x + math.cos(a) * tw * 1.0, y + math.sin(a) * th * 0.7, "[#]",
                    palette.SCRAP_PLATE[k % 2])


def _draw_fossil(batch, camera: Camera, h, st, steps: int) -> None:
    """M33.2: the Fossil Angel's relics on a hero: Feather Ward ready (a
    stone feather by you), sealed in amber (a ring of it round you, Amber
    Heart), the eyes open on you (Eyes in the Flesh, a row over your head).
    The feathers and boulders they put up are tiles."""
    tw, th = config.TILE_PX_W, config.TILE_PX_H
    x, y = camera.world_to_px(h.x, h.y)
    if st.has("feather_ward") and h.ward_t <= 0:
        batch.put_c(x - tw * 0.9, y - th * 0.2, "/|", palette.FEATHER_SPIKE_FG)
    if h.sealed > 0:
        r = h.hit_radius + 0.35
        for k in range(12):
            a = k * math.tau / 12
            batch.put_c(x + math.cos(a) * r * tw, y + math.sin(a) * r * th * 0.9,
                        "#" if k % 2 else "=", palette.AMBER_WALL_FG if k % 2 else palette.RESIN_FG)
    n = h.flesh_eyes
    for k in range(n):
        batch.put_c(x + (k - (n - 1) / 2) * 9, y - th * 1.3, "o",
                    palette.FOSSIL_EYE[1] if (k + steps // 20) % 3 else palette.FOSSIL_EYE[0])
