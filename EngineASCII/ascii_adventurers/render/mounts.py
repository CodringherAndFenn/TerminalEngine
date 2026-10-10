"""
render/mounts.py -- the heroes' mounts (P6), drawn like the heroes: small
hand-made pictures, one letter per pixel (palette.SPRITE_COLORS, "." =
transparent), facing right, seen from the side at the heroes' angle.

A riding hero is one picture: the hero's top MOUNT_RIDER_ROWS rows (head
and body; the legs are hidden) sitting at the mount's saddle, then the
mount drawn over them, so its back and neck come in front of the rider.
The whole thing mirrors when the mount goes left (it faces the way it's
going, not the aim; systems/mount.py keeps hero.mount_left) and washes white for a
moment when hit, like any character. Four-legged mounts gallop in two
frames as they move (stride, gathered); standing, they keep their legs
gathered. The wizard's carpet floats over its shadow and bobs instead.

Each mount: its frames, the saddle (column the rider is centred on, the
row the rider sits on), and whether it floats.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import pygame

from .. import config, palette
from .characters import ART, ART_W, _picture
from .sprites import SpriteBank


@dataclass(frozen=True)
class Mount:
    frames: tuple[tuple[str, ...], ...]
    seat: tuple[int, int]            # (column under the rider's middle, row the rider sits on)
    floats: bool = False


def _legs(body: list[str], *legs: list[str]) -> tuple[tuple[str, ...], ...]:
    return tuple(tuple(body + rows) for rows in legs)


# The white pony (the princess): a pink mane and tail.
_PONY = [
    "................kk....",
    "...............kwk....",
    "..............kpwwk...",
    ".............kppwwwwk.",
    ".............kppwkwwwk",
    ".............kpwwwwmmk",
    "...kkkkkkkkkkkpwwkkkk.",
    "..kwwwwwwwwwwwwwwk....",
    ".kpwwwwwwwwwwwwwmk....",
    "kppwwwwwwwwwwwwwmk....",
    "kp.kmwwwwwwwwwwmmk....",
]
_STRIDE = ["...kmk..kmk.kmk..kmk..",
           "..kmk....kmkkmk...kmk.",
           "..kk......kk.kk....kk."]
_GATHER = ["....kmkkmk...kmkkmk...",
           "....kmkkmk...kmkkmk...",
           "....kkkkkk...kkkkkk..."]

# The donkey (the bard): grey, long ears, a dark mane, saddlebags.
_DONKEY = [
    "..............kk.kk...",
    "..............kmkkmk..",
    "..............kmkkmk..",
    ".............kMmmmmmk.",
    ".............kMmmkmmmk",
    ".............kMmmmwwwk",
    "...kkkkkkkkkkkMmmkkkk.",
    "..kmmmmmmmmmmmmmmk....",
    ".kMmmkkkkkkmmmmmMk....",
    "kMkmmkhhhHkmmmmmMk....",
    "kk.kMkhhhHkmmmmMMk....",
]
_D_STRIDE = [row.replace("m", "M") for row in _STRIDE]
_D_GATHER = [row.replace("m", "M") for row in _GATHER]

# The stag (the huntress): tan, a white tail, antlers.
_STAG = [
    ".............k.k..k.k.",
    ".............kHkkkHk..",
    "..............kHHHk...",
    "...............kekk...",
    "..............keekeek.",
    "..............keeeeEEk",
    "...kkkkkkkkkkkeeekkkk.",
    "..kwkeeeeeeeeeeeek....",
    "..kweeeeeeeeeeeeEk....",
    "...keeeeeeeeeeeeEk....",
    "...kEwwwwwwwwwwEEk....",
]
_S_STRIDE = [row.replace("m", "E") for row in _STRIDE]
_S_GATHER = [row.replace("m", "E") for row in _GATHER]

# The war ram (the dwarf): woolly, a dark face, curled horns, short legs.
_RAM = [
    "..............kkkk....",
    ".............kYyyYk...",
    ".............kykkyMk..",
    "..............kYMMMMk.",
    "..kkkkkkkkkkkkkMMkMMk.",
    ".kwmwwmwwmwwmwkMMMMk..",
    "kwwwwwwwwwwwwwwkkkk...",
    "kmwwmwwmwwmwwmwk......",
    "kwwwwwwwwwwwwwwk......",
    ".kmwwmwwmwwmwwk.......",
]
_R_STRIDE = ["..kMk.kMk..kMk.kMk....",
             ".kMk...kMkkMk...kMk...",
             ".kk.....kk.kk....kk..."]
_R_GATHER = ["...kMkkMk...kMkkMk....",
             "...kMkkMk...kMkkMk....",
             "...kkkkkk...kkkkkk...."]

# The flying carpet (the wizard): red and gold, tasselled, floating.
_CARPET = (
    "..kkkkkkkkkkkkkkkkkk..",
    "yk.ryyryyryyryyryyrRky",
    "ykRRRRRRRRRRRRRRRRRRky",
    "..kkkkkkkkkkkkkkkkkk..",
)

MOUNTS: dict[str, Mount] = {
    "pony": Mount(_legs(_PONY, _STRIDE, _GATHER), (8, 7)),
    "donkey": Mount(_legs(_DONKEY, _D_STRIDE, _D_GATHER), (8, 7)),
    "stag": Mount(_legs(_STAG, _S_STRIDE, _S_GATHER), (8, 7)),
    "ram": Mount(_legs(_RAM, _R_STRIDE, _R_GATHER), (7, 5)),
    "carpet": Mount((_CARPET,), (10, 1), floats=True),
}
MOUNT_W = 22
SHADOW = (8, 6, 12, 110)            # a floating mount's shadow (with alpha)
FLOAT_GAP = 3                       # art pixels between a carpet and its shadow
_HIT_MIX = 0.65


def _mount_picture(art: tuple[str, ...], hurt: bool) -> pygame.Surface:
    colors = palette.SPRITE_COLORS
    surf = pygame.Surface((MOUNT_W, len(art)), pygame.SRCALPHA)
    for y, row in enumerate(art):
        for x, ch in enumerate(row):
            if ch == ".":
                continue
            c = colors[ch]
            if hurt and ch != "k":
                c = tuple(round(v + (255 - v) * _HIT_MIX) for v in c)
            surf.set_at((x, y), c)
    return surf


def rider_picture(hero_sprite: str, mount: str, frame: int, hurt: bool,
                  part: str = "all") -> pygame.Surface:
    """The hero on its mount, in art pixels (facing right). The rider bobs
    a pixel up on the gathered frame; a floating mount has its shadow
    FLOAT_GAP pixels under it. `part`: "all", or "rider" / "shadow" alone
    (same size and place, so a carpet can bob over a shadow that stays)."""
    m = MOUNTS[mount]
    art = m.frames[frame % len(m.frames)]
    rows = config.MOUNT_RIDER_ROWS
    sx, sy = m.seat
    top = max(0, rows - sy) + 1                   # room above the mount for the rider (+ bob)
    shadow = FLOAT_GAP + 2 if m.floats else 0
    surf = pygame.Surface((MOUNT_W, top + len(art) + shadow), pygame.SRCALPHA)
    if m.floats and part != "rider":
        y = top + len(art) + FLOAT_GAP
        pygame.draw.ellipse(surf, SHADOW, pygame.Rect(2, y, MOUNT_W - 4, 2))
    if part == "shadow":
        return surf
    rider = _picture(hero_sprite, hurt).subsurface(pygame.Rect(0, 0, ART_W, rows))
    bob = 1 if (frame % 2 == 1 and len(m.frames) > 1) else 0
    surf.blit(rider, (sx - ART_W // 2, top + sy - rows - bob))
    surf.blit(_mount_picture(art, hurt), (0, top))
    return surf


def _painter(hero_sprite: str, mount: str, scale: int, flip: bool, frame: int, hurt: bool,
             part: str = "all"):
    def paint(surf, to_px):
        img = rider_picture(hero_sprite, mount, frame, hurt, part)
        if flip:
            img = pygame.transform.flip(img, True, False)
        w, h = img.get_width() * scale, img.get_height() * scale
        img = pygame.transform.scale(img, (w, h))
        # The mount's feet (its picture's bottom, or the shadow) go where the
        # hero's feet would be: ART row 15 of 18, i.e. 6 pixels below the
        # middle of a standing hero.
        x, y = to_px(-w / 2, 6 * scale - h)
        surf.blit(img, (round(x), round(y)))
    return paint


def gallop_frame(hero) -> int:
    """Stride and gathered by distance ridden; gathered while standing."""
    if hero.speed < 0.5:
        return 1
    return int(hero.walked * config.MOUNT_STEPS_PER_TILE) % 2


def draw_rider(bank: SpriteBank, x: float, y: float, hero_sprite: str, mount: str,
               scale: int, facing_left: bool, frame: int, hurt: bool, bob: float = 0.0) -> None:
    """A hero on its mount, centred where the hero would stand at canvas
    pixel (x, y). A floating mount's shadow stays put while it bobs."""
    reach = (MOUNT_W + len(MOUNTS[mount].frames[0]) + len(ART[hero_sprite])) * scale / 2 + 8
    parts = ("shadow", "rider") if MOUNTS[mount].floats else ("all",)
    for part in parts:
        key = f"mount:{part}:{hero_sprite}:{mount}:{scale}:{int(facing_left)}:{frame}:{int(hurt)}"
        sprite = bank.static(key, _painter(hero_sprite, mount, scale, facing_left, frame, hurt,
                                           part), reach)
        bank.draw(sprite, x, y - (bob if part == "rider" else 0.0))


def draw_mounted(bank: SpriteBank, camera, hero, clock: float) -> None:
    """Draw a riding hero at its world spot (render/characters.draw_body
    calls this while hero.mount is set). A carpet bobs over its shadow."""
    x, y = camera.world_to_px(hero.x, hero.y)
    m = MOUNTS[hero.mount]
    bob = (math.sin(clock * config.MOUNT_FLOAT_BOB[0]) * config.MOUNT_FLOAT_BOB[1]
           * hero.spec.sprite_scale) if m.floats else 0.0
    draw_rider(bank, x, y, hero.spec.sprite, hero.mount, hero.spec.sprite_scale,
               hero.mount_left, gallop_frame(hero) if not m.floats else 0,
               hero.hurt_flash > 0, bob)
