"""
render/pangaea.py -- Pangaea's land at work (M31.1, systems/pangaea.py): the
volcano's lava bombs (the ring marking where each will land, tightening and
flashing as it comes; the bomb itself falling out of the sky toward it) and
the bubbles round a hero sinking in tar. A bomb's burst is an effect
("lava_burst"), the burning rock it leaves a zone ("lava_splash",
render/spell_fx.py).

M31.2, its enemies (ai/pangaea.py; drawn by render/plains.draw_plains,
which calls `draw_beast` under the body and `draw_pangaea_tells` over it):
  * the echoes: in the moment before one plays, a ghost of the enemy (its
    own picture, faded) where it stood, and the shape of what's coming
    (the cone, the circle, the line or lane, where the shot flies, where
    the torch comes down), flashing faster as it comes; an echoed run is
    a ghost running the line; the shaman's spirits are the beasts in flat
    ochre;
  * the originals' tells: a mammoth herd's lanes, the trumpet's cone, a
    sabre-tooth's pounce line, a rhino's charge lane, a bear's swipe, the
    spirit being painted and its line; a "^" over a beast a fire-bearer
    drives at you, sparks where a hit glances off a rhino's front;
  * on the ground (`draw_pangaea`): the fires' flames, the traps' faint marks.
"""

from __future__ import annotations

import math

import pygame

from .. import config, palette
from ..ai.pangaea import (Beast, Bombardier, CaveBear, ClubTail, Dragonfly, Mammoth, Pterosaur,
                          Raptor, SabreTooth, SeaScorpion, Shaman, Tyrant, WoollyRhino)
from .ascii_fx import _Batch
from .characters import ART_H, ART_W, _picture, _walk_frame
from . import pangaea_art  # noqa: F401  (adds the pictures to ART)

_FALL_PX = 150              # how high above its mark a bomb shows first (canvas px)


def draw_pangaea(text, camera, volcano, heroes, land=None, clock: float = 0.0) -> None:
    if volcano is None:
        return
    batch = _Batch(text)
    if land is not None:
        _ground(batch, camera, land, clock)
    radius = config.LAVA_BOMB[3]
    tw, th = config.TILE_PX_W, config.TILE_PX_H
    for x, y, left, total in volcano.bombs:
        q = 1.0 - left / total if total > 0 else 1.0
        px, py = camera.world_to_px(x, y)
        hot = left < 0.6 and int(left * 10) % 2 == 0
        col = palette.LAVA_MARK[0 if hot else 1]
        r = radius * (1.15 - 0.15 * q)
        for k in range(14):
            a = k * math.tau / 14 + q
            batch.put_c(px + math.cos(a) * r * tw, py + math.sin(a) * r * th, "o" if k % 2 else ".", col)
        batch.put_c(px, py, "x", col)
        if q > 0.35:                                  # (the bomb, coming down)
            f = (q - 0.35) / 0.65
            batch.put_c(px + (1.0 - f) * 40, py - (1.0 - f) * _FALL_PX, "@", palette.LAVA_BOMB_FG)
    for h in heroes:
        if getattr(h, "tar_t", 0.0) > 0 and h.alive:
            x, y = camera.world_to_px(h.x, h.y)
            for k in range(3):
                a = k * math.tau / 3 + h.tar_t * 4
                batch.put_c(x + math.cos(a) * 12, y + 8 + math.sin(a) * 4, "o" if k else ".",
                            palette.TAR_SINK)
    batch.flush()


# --- M31.2: the ground, the enemies' tells, their echoes ---------------------------------------


def _ground(batch, camera, land, clock: float) -> None:
    """Flames dancing on the burning ferns; the traps' faint marks."""
    tx0, ty0, tx1, ty1 = camera.visible_tiles()
    tick = int(clock * 8)
    for (tx, ty) in land.fires:
        if tx0 <= tx <= tx1 and ty0 <= ty <= ty1:
            h = (tx * 7349 + ty * 1931 + tick) % 7
            if h < 3:
                px, py = camera.world_to_px(tx + 0.25 + h * 0.25, ty + 0.3)
                batch.put_c(px, py, "^" if h else "*", palette.FIRE_FLICKER[h])
    for x, y, kind, _, _ in land.traps:
        if tx0 <= x <= tx1 + 1 and ty0 <= y <= ty1 + 1:
            px, py = camera.world_to_px(x, y)
            batch.put_c(px, py, "_" if kind == "pit" else "o",
                        palette.TRAP_MARK[1 if kind == "pit" else 0])


def _dots(batch, camera, x0, y0, angle, length, col, step=1.0, off=0.0) -> None:
    ca, sa = math.cos(angle), math.sin(angle)
    k = step * 0.5
    while k <= length:
        px, py = camera.world_to_px(x0 + ca * k - sa * off, y0 + sa * k + ca * off)
        batch.put_c(px, py, ".", col)
        k += step


def _shape(batch, camera, shape, x, y, angle, reach, half, col) -> None:
    """The outline of an area (ai/pangaea.inside's shapes)."""
    tw, th = config.TILE_PX_W, config.TILE_PX_H
    if shape == "circle":
        n = max(8, int(reach * 6))
        px, py = camera.world_to_px(x, y)
        for k in range(n):
            a = k * math.tau / n
            batch.put_c(px + math.cos(a) * reach * tw, py + math.sin(a) * reach * th, "o", col)
        return
    if shape == "cone":
        for side in (-1, 1):
            _dots(batch, camera, x, y, angle + side * half, reach, col)
        n = max(3, int(reach * half * 3))
        px, py = camera.world_to_px(x, y)
        for k in range(n + 1):
            a = angle - half + 2 * half * k / n
            batch.put_c(px + math.cos(a) * reach * tw, py + math.sin(a) * reach * th, "o", col)
        return
    for side in (-1, 1):                                  # (a line: its two rails)
        _dots(batch, camera, x, y, angle, reach, col, off=side * max(0.3, half))


def _blink(left: float, cols) -> tuple:
    return cols[0 if int(left * (8 if left > 0.3 else 16)) % 2 == 0 else 1]


def _tinted(name: str, scale: int, flip: bool, frame: int, mode: str):
    """A painter for picture `name` as an echo's ghost (its own colours,
    washed out and faded) or a shaman's spirit (flat ochre)."""
    def paint(surf, to_px):
        base = _picture(name, False)
        img = pygame.Surface(base.get_size(), pygame.SRCALPHA)
        w, h = base.get_size()
        mix, wash = palette.ECHO_MIX, palette.ECHO_WASH
        for py in range(h):
            for px in range(w):
                c = base.get_at((px, py))
                if c.a == 0:
                    continue
                if mode == "ghost":
                    rgb = tuple(round(v + (u - v) * mix) for v, u in zip(c[:3], wash))
                    img.set_at((px, py), (*rgb, palette.ECHO_ALPHA))
                elif mode == "husk":                     # (M31.4: a moulted skin, dry and dull)
                    lum = (c.r + c.g + c.b) / 3
                    img.set_at((px, py), (round(40 + lum * 0.5), round(32 + lum * 0.44),
                                          round(24 + lum * 0.34), 255))
                else:
                    lum = (c.r + c.g + c.b) / 3
                    img.set_at((px, py), (*palette.OCHRE[0 if lum < 40 else 1 if lum < 130 else 2], 235))
        img = _walk_frame(img, frame)
        if flip:
            img = pygame.transform.flip(img, True, False)
        img = pygame.transform.scale(img, (ART_W * scale, ART_H * scale))
        x, y = to_px(-ART_W * scale / 2, -ART_H * scale / 2)
        surf.blit(img, (round(x), round(y)), special_flags=pygame.BLEND_RGBA_MAX)
    return paint


def _scale(sprite: str, own: int) -> int:
    """How big a picture is drawn: a beast's own size (a shaman's spirits are
    a mammoth's and a sabre-tooth's; the Ancestor's spirit herd mammoths'
    and rhinos')."""
    if sprite.startswith("mammoth"):
        return config.ENEMIES["mammoth"].scale
    if sprite.startswith("sabre_tooth"):
        return config.ENEMIES["sabre_tooth"].scale
    if sprite.startswith("woolly_rhino"):
        return config.ENEMIES["woolly_rhino"].scale
    return own


def _figure(bank, camera, x, y, sprite, scale, left, mode, frame=0) -> None:
    px, py = camera.world_to_px(x, y)
    key = f"pangaea:{mode}:{sprite}:{scale}:{int(left)}:{frame}"
    reach = max(ART_W, ART_H) * scale / 2 + 1
    bank.draw(bank.static(key, _tinted(sprite, scale, left, frame, mode), reach), px, py)


def lob_radius(what: str) -> float:
    """How wide what's thrown or falling lands (its ring shown meanwhile)."""
    if what == "rock":
        return config.ANCESTOR_ROCKS[3]
    if what == "bomb":
        return config.ANCESTOR_ERUPTION[3]
    return config.FIREB[3]


def draw_beast(text, bank, camera, e) -> None:
    """Under a Pangaean enemy's body: its echoes about to play (a ghost
    where it stood, the shape coming), its runners (echoed runs, painted
    spirits), its hits, what it threw."""
    if isinstance(e, Beast):
        draw_echoes(text, bank, camera, e, e.espec.scale)


def draw_echoes(text, bank, camera, e, scale: int) -> None:
    """Any echoing enemy's echoes about to play, runners, hits and what it
    threw (ai/pangaea.Echoing: a beast's, the Ancestor's)."""
    batch = _Batch(text)
    for ech in e.echoes:
        if ech.t > ech.tell:
            continue
        col = _blink(ech.t, palette.ECHO_TELL)
        d = ech.data
        gx, gy, face = ech.x, ech.y, ech.facing
        if ech.kind == "area":
            _shape(batch, camera, d["shape"], d["x"], d["y"], d["angle"], d["reach"], d["half"], col)
        elif ech.kind == "shots":
            gx, gy, face = d["shots"][0][0], d["shots"][0][1], d["shots"][0][2]
            for x, y, angle, *_ in d["shots"]:
                _dots(batch, camera, x, y, angle, 5.0, col)
        elif ech.kind == "run":
            gx, gy, face = d["x0"], d["y0"], d["angle"]
            for side in (-1, 1):
                _dots(batch, camera, d["x0"], d["y0"], d["angle"], d["length"], col,
                      off=side * d["radius"])
        elif ech.kind == "lob":
            gx, gy = d["x0"], d["y0"]
            _shape(batch, camera, "circle", d["x1"], d["y1"], 0.0, lob_radius(d["what"]), 0.0, col)
        elif ech.kind == "lobs":                          # (M31.4: rocks, bombs: where they'll fall)
            for _, _, x1, y1 in d["spots"]:
                _shape(batch, camera, "circle", x1, y1, 0.0, lob_radius(d["what"]), 0.0, col)
        elif ech.kind not in ("area",):                   # (another kind: its own drawer's)
            continue
        sprite = d["sprite"] if ech.kind == "run" else ech.sprite   # (a spirit's: the spirit)
        _figure(bank, camera, gx, gy, sprite, _scale(sprite, scale), math.cos(face) < 0, "ghost")
    for r in e.runners:
        frame = int(r.done * config.WALK_STEPS_PER_TILE) % 4
        _figure(bank, camera, r.x, r.y, r.sprite, _scale(r.sprite, scale), math.cos(r.angle) < 0,
                r.look, frame)
    for (shape, x, y, angle, reach, half), left, echo in e.flashes:
        cols = palette.ECHO_TELL if echo else palette.BEAST_HIT
        _shape(batch, camera, shape, x, y, angle, reach, half, cols[0 if left > 0.12 else 1])
    for x0, y0, x1, y1, s, flight, what, echo in e.lobs:
        q = min(1.0, s / flight)
        cols = palette.ECHO_TELL if echo else palette.BEAST_TELL
        _shape(batch, camera, "circle", x1, y1, 0.0, lob_radius(what), 0.0, _blink(flight - s, cols))
        if what in ("rock", "bomb"):                      # (M31.4: falling out of the sky)
            if q > 0.3:
                f = (q - 0.3) / 0.7
                px, py = camera.world_to_px(x1, y1)
                col = palette.ECHO_TELL[0] if echo else (
                    palette.ANCESTOR_ROCK if what == "rock" else palette.LAVA_BOMB_FG)
                batch.put_c(px + (1.0 - f) * 30, py - (1.0 - f) * _FALL_PX, "@", col)
            continue
        px, py = camera.world_to_px(x0 + (x1 - x0) * q, y0 + (y1 - y0) * q)
        batch.put_c(px, py - math.sin(q * math.pi) * 40, "*",
                    palette.ECHO_TELL[0] if echo else palette.FIRE_FLICKER[int(s * 12) % 2])
    batch.flush()


def draw_pangaea_tells(batch, camera, e) -> None:
    """Over a Pangaean enemy: the tells of what it's about to do."""
    if not isinstance(e, Beast):
        return
    if isinstance(e, Mammoth) and e.state == "lane":
        col = _blink(e.timer, palette.BEAST_TELL)
        for side in (-1, 1):
            _dots(batch, camera, e.x, e.y, e.aim, config.MAMMOTH[10], col, off=side * e.hit_radius)
    if isinstance(e, Mammoth) and e.state == "trumpet":
        _shape(batch, camera, "cone", e.x, e.y, e.facing, config.MAMMOTH[3],
               math.radians(config.MAMMOTH[2]) / 2, _blink(e.timer, palette.BEAST_TELL))
    if isinstance(e, SabreTooth) and e.state == "crouch":
        _dots(batch, camera, e.x, e.y, e.aim, e.length, _blink(e.timer, palette.BEAST_TELL), 0.8)
    if isinstance(e, WoollyRhino) and e.state == "scrape":
        col = _blink(e.timer, palette.BEAST_TELL)
        for side in (-1, 1):
            _dots(batch, camera, e.x, e.y, e.aim, config.RHINO[3], col, off=side * e.hit_radius)
    if isinstance(e, CaveBear) and e.state == "rear":
        _shape(batch, camera, "cone", e.x, e.y, e.facing, e.espec.attack_radius,
               math.radians(config.BEAR[0]) / 2, _blink(e.timer, palette.BEAST_TELL))
    if isinstance(e, Shaman) and e.painting:
        col = _blink(e.windup, palette.BEAST_TELL)
        rad = config.SHAMAN[3] if e.painting == "mammoth" else config.SHAMAN[6]
        for side in (-1, 1):
            _dots(batch, camera, *e.spot, e.aim, config.SHAMAN[8], col, off=side * rad)
    _tells_m313(batch, camera, e)
    x, y = camera.world_to_px(e.x, e.y)
    top = y - e.espec.scale * 9 - 10
    if e.driven > 0:
        batch.put_c(x + 10, top, "^", palette.DRIVEN)
    if getattr(e, "kind_key", "") in config.GREAT_KEYS:    # (M31.4: a great beast, by name)
        batch.put_c(x, top - 24, e.espec.name.upper(), palette.GREAT_NAME)
    if e.glanced > 0:
        for k in (-1, 1):
            gx, gy = camera.world_to_px(e.x + math.cos(e.facing) * e.hit_radius + k * 0.3,
                                        e.y + math.sin(e.facing) * e.hit_radius - 0.3)
            batch.put_c(gx, gy, "*", palette.GLANCE)


def draw_spirit_painting(bank, camera, e) -> None:
    """A shaman's spirit being painted: the beast in ochre, coming in."""
    if isinstance(e, Shaman) and e.painting and int(e.windup * 10) % 2 == 0:
        sprite = "mammoth" if e.painting == "mammoth" else "sabre_tooth_pounce"
        _figure(bank, camera, *e.spot, sprite, _scale(sprite, 4), math.cos(e.aim) < 0, "ochre")


def _tells_m313(batch, camera, e) -> None:
    """The middle ring's and the heart's tells (M31.3)."""
    if e.flies:                                       # (a shadow on the ground under it)
        x, y = camera.world_to_px(e.x, e.y)
        batch.put_c(x, y + e.espec.scale * 6, "_", palette.BOMB_SHADOW)
    if isinstance(e, Raptor) and e.state == "crouch":
        _dots(batch, camera, e.x, e.y, e.aim, e.length, _blink(e.timer, palette.BEAST_TELL), 0.8)
    elif isinstance(e, Tyrant) and e.state in ("roar", "bite", "tail"):
        _, _, _, cone, reach, _, _, bite, tail, tail_reach = config.TYRANT[:10]
        col = _blink(e.timer, palette.BEAST_TELL)
        if e.state == "roar":
            _shape(batch, camera, "cone", e.x, e.y, e.facing, reach, math.radians(cone) / 2, col)
        elif e.state == "bite":
            _shape(batch, camera, "cone", e.x, e.y, e.facing, e.espec.attack_radius,
                   math.radians(bite) / 2, col)
        else:
            _shape(batch, camera, "cone", e.x, e.y, e.facing + math.pi, tail_reach,
                   math.radians(tail) / 2, col)
    elif isinstance(e, ClubTail) and e.state == "swing":
        _shape(batch, camera, "cone", e.x, e.y, e.facing + math.pi, e.espec.attack_radius,
               math.radians(config.CLUB[4]) / 2, _blink(e.timer, palette.BEAST_TELL))
    elif isinstance(e, Pterosaur) and e.state == "mark":
        _dots(batch, camera, e.x, e.y, e.aim, e.length, _blink(e.timer, palette.BEAST_TELL), 0.9)
    elif isinstance(e, Dragonfly) and e.state == "hover" and e.aimed:
        _dots(batch, camera, e.x, e.y, e.aim, config.DRAGONFLY[0], _blink(e.timer, palette.BEAST_TELL))
    elif isinstance(e, Bombardier) and e.state == "aim":
        _shape(batch, camera, "cone", e.x, e.y, e.facing + math.pi, config.BEETLE[4],
               math.radians(config.BEETLE[3]) / 2, _blink(e.timer, palette.BEAST_TELL))
    elif isinstance(e, SeaScorpion) and e.state == "claw":
        col = _blink(e.timer, palette.BEAST_TELL)
        for side in (-1, 1):
            _dots(batch, camera, e.x, e.y, e.aim, config.SEA_SCORPION[1] + 1.0, col, off=side * 0.7)
    elif isinstance(e, SeaScorpion) and e.state == "sting":
        _shape(batch, camera, "circle", *e.sting_at, 0.0, config.SEA_SCORPION[7], 0.0,
               _blink(e.timer, palette.BEAST_TELL))
