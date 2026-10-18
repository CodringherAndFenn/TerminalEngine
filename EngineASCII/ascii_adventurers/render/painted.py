"""
render/painted.py -- big figures painted from shapes instead of a pixel
grid: the Snow King (the Frost Hermit), Fragile's three looks (the girl,
the wolf, beaten and crying / hugging her bear) and Mr. Buttons (M24.4),
Nettle, the Blighted (M25.1), Love & Cuddles (M25.2), The Fallen (M25.3) and Mycelium the fly
agaric (M26.1), the shaggy ink cap (M26.2) and the giant puffball (M26.3), and the
plains boss, More than Life / More than Death (M27).

A 14 x 18 pixel picture (render/characters.ART) drawn 5-6x is too coarse
for a boss up close, so these are painted like the camels (render/camel.py):
polygons and ovals with a dark outline, a shaded side and highlights,
in "art units" -- the same 14 x 18 box as a character picture (x right =
the way they face, y down, the origin at the picture's centre), times the
draw scale in screen pixels. So a figure drawn at scale 6 is the size its
old picture was, and draw_character() draws either kind
(characters.PAINTED).

Each figure is a function (pen, frame, pose); `frame` is the 4-step walk
or idle cycle, `pose` a few named stances (a staff raised to cast, the parasol
thrown, ...). A hit washes every color but the outline toward white, like
the pixel pictures.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

import pygame

from .. import palette

_HIT_MIX = 0.65          # hit flash: this far toward white (as characters._HIT_MIX)


class Pen:
    """Paints in art units onto a sprite surface: mirrored when facing
    left, scaled, and washed white while hurt."""

    def __init__(self, surf, to_px, scale: float, flip: bool, hurt: bool,
                 edge=(10, 10, 16)) -> None:
        self.surf, self.to_px, self.s, self.flip, self.hurt = surf, to_px, scale, flip, hurt
        self.edge = edge
        self.dv = 0.0                     # shifts everything painted down this far

    def P(self, u: float, v: float) -> tuple[int, int]:
        v += self.dv
        x, y = self.to_px((-u if self.flip else u) * self.s, v * self.s)
        return round(x), round(y)

    def W(self, w: float) -> int:
        return max(1, round(w * self.s))

    def c(self, color):
        if not self.hurt or color == self.edge:
            return color
        out = tuple(round(v + (255 - v) * _HIT_MIX) for v in color[:3])
        return out + tuple(color[3:])

    def poly(self, pts, fill, edge: bool = True) -> None:
        pts = [self.P(u, v) for u, v in pts]
        pygame.draw.polygon(self.surf, self.c(fill), pts)
        if edge:
            pygame.draw.polygon(self.surf, self.edge, pts, self.W(0.2))

    def oval(self, u, v, ru, rv, fill, edge: bool = True, n: int = 24, tilt: float = 0.0) -> None:
        ct, st = math.cos(tilt), math.sin(tilt)
        pts = []
        for t in (k * math.tau / n for k in range(n)):
            a, b = math.cos(t) * ru, math.sin(t) * rv
            pts.append((u + a * ct - b * st, v + a * st + b * ct))
        self.poly(pts, fill, edge)

    def line(self, a, b, w: float, color) -> None:
        pygame.draw.line(self.surf, self.c(color), self.P(*a), self.P(*b), self.W(w))

    def lines(self, pts, w: float, color, edge: bool = False) -> None:
        """A polyline; with `edge`, outlined (drawn twice, the outline wider)."""
        pts = [self.P(u, v) for u, v in pts]
        if edge:
            pygame.draw.lines(self.surf, self.edge, False, pts, self.W(w) + 2)
            for p in (pts[0], pts[-1]):
                pygame.draw.circle(self.surf, self.edge, p, (self.W(w) + 2) // 2)
        pygame.draw.lines(self.surf, self.c(color), False, pts, self.W(w))

    def dot(self, u, v, r: float, color) -> None:
        pygame.draw.circle(self.surf, self.c(color), self.P(u, v), max(1, round(r * self.s)))

    def shadow(self, u, v, ru, rv) -> None:
        self.oval(u, v, ru, rv, palette.FIGURE_SHADOW, edge=False)


def _jagged(x0: float, x1: float, y: float, depth: float, step: float, sway: float = 0.0):
    """Tufted fur hanging along a hem from x0 to x1: points alternating down
    `depth` every half `step`."""
    n = max(1, round(abs(x1 - x0) / step))
    out = []
    for k in range(2 * n + 1):
        u = x0 + (x1 - x0) * k / (2 * n)
        out.append((u + (sway if k % 2 else 0.0), y + (depth if k % 2 else 0.0)))
    return out


def _bob(frame: int) -> float:
    """The walk cycle's hop (as characters._walk_frame): up on frames 1 and 3."""
    return -0.3 if frame % 2 else 0.0


# --- The Snow King: the Frost Hermit ----------------------------------------------------------

# Where his crown sits on his hood, in art units (render/snowking.py
# draws the crown on its own so it can come off).
HERMIT_CROWN = (0.6, -9.4)
# The ice shard on his staff (his casting tells glow there).
HERMIT_SHARD = (5.9, -9.9)          # (raised HERMIT_LIFT while casting)
HERMIT_LIFT = -2.1


def paint_hermit(pen: Pen, frame: int, pose: str) -> None:
    """Hunched and hooded in layered grey furs, frost on every edge; two
    eyes glowing in the dark of a pointed cowl, a long braided frost beard
    ending in an ice bead, and a gnarled staff of ice roots holding a
    shard. Poses: "" (walking), "cast" (staff raised, the shard and his
    eyes blazing), "down" (crown knocked off: slumped, eyes squeezed shut,
    the staff leaning)."""
    c = palette.HERMIT
    pen.edge = c["edge"]
    cast, down = pose == "cast", pose == "down"
    b = _bob(frame)
    hb = b + (0.7 if down else 0.0)                          # his head sags when down
    sway = 0.25 * math.sin(frame * math.pi / 2)
    pen.shadow(0.3, 8.7, 6.9, 1.3)

    # His fur boots under the hem, stepping.
    for k, u in enumerate((-2.3, 1.9)):
        lift = -0.5 if (frame in (1, 3) and (frame == 1) == (k == 0)) else 0.0
        pen.oval(u, 8.3 + lift, 1.3, 0.65, c["boot"])
    # The coat: heavy dark fur, tufted at the hem, a hump of a back.
    hem_v = 7.5 + b * 0.3
    hem = _jagged(5.9, -6.9, hem_v, 0.8, 0.95, sway)
    pen.poly([(-3.6, -4.4 + b), (-5.6, -2.4 + b), (-6.5, 2.6 + b), (-6.9, hem_v)]
             + hem[::-1][1:-1] + [(5.9, hem_v), (5.0, 2.4 + b), (4.2, -1.6 + b),
                                  (3.4, -3.2 + b)], c["fur_dark"])
    pen.poly([(-5.4, -1.0 + b), (-6.3, 2.8 + b), (-6.8, hem_v - 0.2), (-4.6, hem_v - 0.1),
              (-4.4, 2.6 + b)], c["fur_deep"], edge=False)            # his shaded back
    for u in (-5.4, -2.6, 0.4, 3.6):                                 # frost on the hem
        pen.line((u, hem_v - 0.9), (u + 0.5, hem_v - 0.2), 0.14, c["frost"])
    # The coat's fur-trimmed front with ice toggles.
    pen.lines([(2.7, 0.6 + b), (2.9, 4.0 + b), (3.0, hem_v + 0.1)], 0.55, c["fur_light"])
    for v in (3.2, 4.8, 6.4):
        pen.oval(3.5, v + b, 0.35, 0.22, c["ice"], n=10)
    # The mantle over his hunched shoulders: lighter furs, tufts, icicles.
    tufts = _jagged(-6.6, 4.9, 1.2 + b, 0.95, 1.05, -sway)
    pen.poly([(-2.0, -5.0 + b), (-4.6, -4.4 + b), (-6.2, -2.4 + b), (-6.6, -0.2 + b)] + tufts
             + [(4.7, -1.8 + b), (3.6, -3.2 + b)], c["fur"])
    pen.oval(-3.2, -3.4 + b, 2.6, 1.0, c["fur_light"], edge=False, tilt=-0.45)
    for k in (1, 4, 7, 9):
        u, v = tufts[k] if k < len(tufts) else tufts[-2]
        if v > 1.6 + b:
            pen.poly([(u - 0.28, v - 0.15), (u + 0.28, v - 0.15), (u, v + 0.75)], c["ice"])
    # The cowl: rising to a soft point at the back, drooping forward over
    # his face, a ruff of pale fur round its opening.
    pen.poly([(4.4, -4.6 + hb), (3.6, -7.2 + hb), (2.0, -8.7 + hb), (0.2, -9.0 + hb),
              (-1.8, -8.5 + hb), (-3.4, -7.0 + hb), (-3.9, -5.0 + hb), (-3.2, -3.0 + hb),
              (0.0, -2.4 + hb), (3.6, -2.6 + hb)], c["fur"])
    pen.poly([(-1.8, -8.5 + hb), (-3.4, -7.0 + hb), (-3.9, -5.0 + hb), (-3.2, -3.0 + hb),
              (-1.6, -2.6 + hb), (-2.2, -5.2 + hb)], c["fur_deep"], edge=False)
    pen.oval(0.4, -7.6 + hb, 2.0, 0.7, c["fur_light"], edge=False, tilt=-0.15)
    for k in range(6):                                       # frost speckles
        pen.dot(-2.2 + k * 0.85, -8.0 + hb + 0.4 * math.sin(k * 2.3) + abs(k - 2.5) * 0.25,
                0.12, c["frost"])
    hv = -5.0 + hb
    pen.oval(2.45, hv, 2.15, 2.35, c["fur_light"], n=20)
    pen.oval(2.6, hv + 0.1, 1.7, 1.95, c["face"], edge=False, n=20)
    # His eyes in the dark: two cold lights (squeezed shut when down).
    eye = c["eye_cast"] if cast else c["eye"]
    for u, w in ((1.95, 0.45), (3.25, 0.38)):
        if down:
            pen.line((u - w, hv - 0.2), (u + w, hv + 0.1), 0.18, c["eye_dim"])
        else:
            if cast:
                pen.oval(u, hv - 0.3, w + 0.35, 0.55, c["eye_glow"], edge=False, n=12)
            pen.oval(u, hv - 0.3, w, 0.28, eye, edge=False, n=12)
    # The beard: one long frosty braid swinging with his step, tapering to
    # an ice bead, and the moustache's wisps.
    bx = 2.7
    for k in range(9):
        v = hv + 1.9 + k * 0.82
        u = bx + 0.05 * k + sway * k / 8
        w = 0.72 - 0.035 * k
        left = k % 2 == 0
        pen.oval(u + (-0.15 if left else 0.15), v, w, 0.5, c["beard"] if left else c["beard_shade"],
                 n=12, tilt=0.55 if left else -0.55)
    tip = (bx + 0.45 + sway, hv + 1.9 + 9 * 0.82)
    pen.oval(tip[0], tip[1], 0.5, 0.68, c["ice"], n=12)
    pen.dot(tip[0] - 0.15, tip[1] - 0.25, 0.13, c["frost"])
    for side in (-1, 1):
        pen.lines([(bx, hv + 1.3), (bx + side * 1.2, hv + 1.7), (bx + side * 1.6, hv + 2.6)],
                  0.4, c["beard"], edge=True)
    # The staff: gnarled ice roots, a shard of ice held in their curl.
    lift = -2.1 if cast else 0.0
    lean = 1.4 if down else 0.0
    root = [(5.9 + lean, -8.4 + lift), (5.6 + lean * 0.8, -6.4 + lift),
            (5.8 + lean * 0.6, -4.2 + lift), (5.5 + lean * 0.4, -1.6 + lift),
            (5.7 + lean * 0.2, 1.6 + lift), (5.4, 4.6 + lift), (5.6, 8.0 + lift * 0.3)]
    pen.lines(root, 0.6, c["staff"], edge=True)
    pen.lines([(u - 0.12, v) for u, v in root[:-1]], 0.18, c["staff_hi"])
    tx, ty = root[0]
    for side in (-1, 1):
        pen.lines([(tx, ty), (tx + side * 0.95, ty - 0.8), (tx + side * 0.75, ty - 1.9)], 0.3,
                  c["staff"], edge=True)
    sy = ty - 1.5
    if cast:
        pen.oval(tx, sy, 1.6, 1.8, c["glow"], edge=False, n=16)
    pen.poly([(tx, sy - 1.3), (tx + 0.6, sy), (tx, sy + 1.0), (tx - 0.6, sy)],
             c["shard_cast"] if cast else c["ice"])
    pen.poly([(tx - 0.05, sy - 0.9), (tx + 0.25, sy - 0.1), (tx - 0.05, sy + 0.3)], c["frost"],
             edge=False)
    # His front arm: a wide fur sleeve from under the mantle, a mitten
    # gripping the staff (higher while he casts).
    hy = 1.8 + lift + (0.5 if down else 0.0)
    hx = 5.55 + lean * 0.2
    pen.poly([(2.6, 0.6 + b), (4.0, 0.0 + b), (hx, hy - 0.9), (hx - 0.3, hy + 0.9),
              (3.0, 2.6 + b)], c["fur_dark"])
    pen.oval(hx - 0.7, hy, 0.5, 0.95, c["fur_light"], n=14, tilt=0.3)
    pen.oval(hx, hy, 0.72, 0.78, c["boot"], n=14)


def paint_crown(pen: Pen, spin: int) -> None:
    """The hermit's crown: a band of black iron with ice gems -- seen face
    on, or edge on (spin 1) as it tumbles across the floor."""
    c = palette.HERMIT
    pen.edge = c["rime"]                # a pale rim, so it shows on dark stone and on ice
    w = 2.3 if spin % 2 == 0 else 1.3
    pen.poly([(-w, -0.2), (w, -0.2), (w, 1.0), (-w, 1.0)], c["iron"])
    for k in (-1, 0, 1):
        u = k * w * 0.72
        h = 2.2 if k == 0 else 1.6
        pen.poly([(u - 0.5, -0.2), (u + 0.5, -0.2), (u, -0.2 - h)], c["iron"])
        pen.dot(u, -0.2 - h, 0.22, c["ice"])
    pen.line((-w + 0.2, 0.1), (w - 0.2, 0.1), 0.12, c["iron_hi"])
    pen.poly([(0, -0.1), (0.42, 0.42), (0, 0.95), (-0.42, 0.42)], c["ice"])


# --- Fragile ----------------------------------------------------------------------------------

# Her parasol while she holds it (art units): the hand on its handle and
# the way its shaft points, per pose. Open, it rests on her shoulder behind
# her head (twirled for the petals); "raise": furled, lifted to throw.
_PARASOL = {"": ((2.2, -0.3), (-0.3, -0.954)),
            "twirl": ((2.2, -0.3), (-0.3, -0.954)),
            "raise": ((3.4, -6.6), (0.3, -0.954))}


def _parasol(pen: Pen, c: dict, hand, d, spin: float = 0.0, furled: bool = False) -> None:
    """Her black lace parasol, from the handle in her hand up the shaft:
    open, a dome with ribs and a scalloped red lace trim (the ribs turn
    with `spin`); furled, a slim black spindle with a red band."""
    (hx, hy), (dx, dy) = hand, d
    nx, ny = -dy, dx

    def L(a, b):
        return (hx + dx * a + nx * b, hy + dy * a + ny * b)

    # The crook of the handle below her hand, and the shaft.
    pen.lines([L(0.8, 0), L(-0.8, 0), L(-1.4, 0.35), L(-1.5, 0.9), L(-1.1, 1.2)], 0.36,
              c["handle"], edge=True)
    if furled:
        pen.lines([L(0.0, 0), L(5.4, 0)], 0.28, c["handle"], edge=True)
        pen.poly([L(1.2, 0), L(2.4, -0.9), L(4.4, -0.45), L(5.0, 0), L(4.4, 0.45), L(2.4, 0.9)],
                 c["canopy"])
        pen.line(L(2.4, -0.85), L(2.4, 0.85), 0.25, c["lace"])
        pen.dot(*L(5.6, 0), 0.22, c["tip"])
        return
    base, height, half = 8.4, 2.8, 5.0
    pen.lines([L(0.0, 0), L(base + 1.0, 0)], 0.26, c["handle"], edge=True)

    def rim(t):          # the canopy's edge, t = -1..1 across
        return L(base + 0.5 * (1 - t * t), half * t)

    dome = [L(base + 0.4 + height * (1 - t * t) ** 0.6, half * t)
            for t in (k / 10 - 1 for k in range(21))]
    edge = [rim(t) for t in (1 - k / 10 for k in range(21))]
    pen.poly(dome + edge, c["canopy"])
    pen.poly([L(base + 0.6 + (height - 0.5) * (1 - t * t) ** 0.6, half * 0.9 * t)
              for t in (k / 8 - 1 for k in range(17))]
             + [L(base + 1.2, half * 0.9 * t) for t in (1 - k / 8 for k in range(17))],
             c["canopy_hi"], edge=False)
    for k in range(5):                                  # the ribs, turning
        t = math.sin(((k + spin) / 5) * math.pi * 2 - math.pi / 2) * 0.95
        pen.line(L(base + height + 0.3, 0), rim(t), 0.1, c["rib"])
    for k in range(9):                                  # the scalloped lace trim
        t = -1 + k / 4
        u, v = rim(t)
        pen.oval(u - dx * 0.25, v - dy * 0.25, 0.55, 0.55, c["lace"], n=10)
    pen.dot(*L(base + height + 0.9, 0), 0.25, c["tip"])


def paint_fragile(pen: Pen, frame: int, pose: str) -> None:
    """Floating a little off the floor: hair to her knees swaying behind
    her (white), grey-blue skin, red eyes and fangs, a black gothic gown
    (a red-laced corset, a lace collar, a flared skirt with a ruffled
    red-trimmed hem), and a black lace parasol (she's a vampire: it keeps the sun
    off). Poses: "" (resting on her shoulder), "twirl" (spun, for the
    petals), "raise" (furled and lifted to throw), "bare" (it's out
    spinning)."""
    c = palette.FRAGILE
    pen.edge = c["edge"]
    float_ = -0.35 * math.sin(frame * math.pi / 2) - 0.2
    sway = 0.35 * math.sin(frame * math.pi / 2 + 0.8)
    pen.shadow(0.3, 8.6, 3.0 + float_ * 0.8, 0.7)
    b = float_
    held = _PARASOL.get(pose)
    open_ = held is not None and pose != "raise"
    if open_:                       # the open parasol behind her head
        hand, d = held
        _parasol(pen, c, (hand[0], hand[1] + b), d, spin=frame * 1.25 if pose == "twirl" else 0.0)

    # Her hair behind her, down to her knees, its ends swaying.
    pen.poly([(-0.6, -8.7 + b), (1.6, -8.6 + b), (3.0, -7.3 + b), (3.2, -5.2 + b), (2.5, -3.4 + b),
              (1.8, 0.4 + b), (1.0, 3.6 + b), (0.0 + sway, 5.4 + b), (-1.1, 4.4 + b),
              (-2.0 + sway, 6.0 + b), (-2.9, 4.3 + b), (-4.1 + sway, 5.3 + b), (-4.0, 1.4 + b),
              (-3.7, -2.6 + b), (-3.3, -6.1 + b), (-2.1, -8.0 + b)], c["hair"])
    for k, u in enumerate((-3.0, -2.0, -0.9)):
        pen.lines([(u + 0.4, -6.2 + b), (u - 0.2, -2.0 + b), (u + 0.1 + sway * 0.6, 2.8 + b)],
                  0.16, c["hair_hi"])
    # Boot tips under the hem, toes pointing down (she floats).
    for u0, v0 in ((-0.5, 6.3), (1.0, 6.1)):
        pen.poly([(u0 - 0.45, v0 + b), (u0 + 0.5, v0 + b), (u0 + 0.35, v0 + 1.3 + b),
                  (u0 - 0.05, v0 + 1.5 + b)], c["boot"])
    # Her back arm, behind, hanging in a long black sleeve.
    pen.lines([(-1.2, -2.4 + b), (-1.6, -0.2 + b), (-1.3, 1.4 + b)], 0.6, c["dress_dark"],
              edge=True)
    pen.oval(-1.3, 1.7 + b, 0.38, 0.38, c["skin_dark"], n=10)
    # The gown: a long skirt flaring from the waist, a ruffled hem trimmed
    # with red lace, its folds swaying.
    hem = _jagged(3.3, -3.1, 6.3 + b, 0.55, 0.8, sway * 0.4)
    pen.poly([(-1.5, 0.3 + b), (1.8, 0.3 + b), (2.6, 3.0 + b), (3.3, 6.3 + b)] + hem[1:-1]
             + [(-3.1, 6.3 + b), (-2.4, 3.0 + b)], c["dress"])
    pen.poly([(-1.5, 0.3 + b), (-0.3, 0.3 + b), (-0.9, 6.4 + b), (-3.1, 6.3 + b),
              (-2.4, 3.0 + b)], c["dress_dark"], edge=False)
    for u0, u1 in ((0.4, 0.9), (1.2, 2.2), (-0.2, -1.2)):         # folds
        pen.line((u0, 1.0 + b), (u1 + sway * 0.3, 6.0 + b), 0.14, c["dress_hi"])
    for k in range(0, len(hem), 2):                                # lace trim
        u, v = hem[k]
        pen.oval(u, v + 0.15, 0.32, 0.26, c["lace"], edge=False, n=8)
    # The bodice: a black corset laced up the front in red; a waist sash.
    pen.poly([(-1.75, -2.9 + b), (2.0, -2.9 + b), (1.75, 0.5 + b), (-1.5, 0.5 + b)], c["dress"])
    pen.poly([(-1.75, -2.9 + b), (-0.6, -2.9 + b), (-0.5, 0.5 + b), (-1.5, 0.5 + b)],
             c["dress_dark"], edge=False)
    for k in range(4):
        v = -2.4 + k * 0.7 + b
        pen.line((0.6, v), (1.4, v + 0.45), 0.1, c["lace"])
        pen.line((1.4, v), (0.6, v + 0.45), 0.1, c["lace"])
    pen.poly([(-1.5, 0.2 + b), (1.8, 0.2 + b), (1.8, 0.75 + b), (-1.5, 0.75 + b)], c["lace"])
    # A high lace collar.
    pen.poly(_jagged(-0.3, 1.6, -3.0 + b, -0.45, 0.4) + [(1.5, -2.7 + b), (-0.2, -2.7 + b)],
             c["lace"])
    # Neck and head: grey-blue skin, a pointed ear, red eyes, fangs.
    pen.poly([(0.0, -3.6 + b), (1.1, -3.6 + b), (1.1, -2.7 + b), (0.0, -2.7 + b)], c["skin_dark"],
             edge=False)
    hv = -5.6 + b
    pen.oval(0.75, hv, 1.95, 2.2, c["skin"])
    pen.oval(-0.2, hv + 0.3, 0.9, 1.6, c["skin_dark"], edge=False)
    pen.poly([(-0.9, hv - 0.4), (-2.0, hv - 1.6), (-1.0, hv + 0.6)], c["skin"])
    for u, w in ((1.0, 0.36), (2.2, 0.3)):
        pen.oval(u, hv - 0.05, w, 0.3, c["eye"], edge=False, n=10)
        pen.line((u - w - 0.1, hv - 0.45), (u + w, hv - 0.5), 0.12, c["edge"])
    pen.line((1.3, hv + 1.35), (2.2, hv + 1.25), 0.1, c["mouth"])
    for u in (1.5, 2.0):
        pen.poly([(u - 0.13, hv + 1.3), (u + 0.13, hv + 1.3), (u, hv + 1.75)], c["fang"],
                 edge=False)
    # Bangs, and a long lock falling in front of her shoulder.
    pen.poly([(-1.2, hv - 0.6), (-0.7, hv - 2.3), (1.2, hv - 2.7), (2.9, hv - 1.6), (2.9, hv - 0.5),
              (2.2, hv - 1.1), (1.6, hv - 0.5), (0.8, hv - 1.2), (0.0, hv - 0.2)], c["hair"])
    pen.lines([(-0.6, hv - 0.4), (-0.9, hv + 2.8), (-0.6 + sway * 0.5, hv + 5.2)], 0.45, c["hair"],
              edge=True)
    # Her front arm: on the parasol's handle (raised with it, furled, to
    # throw), or hanging empty.
    if held is not None:
        hand, d = held
        hand = (hand[0], hand[1] + b)
        if not open_:
            _parasol(pen, c, hand, d, furled=True)
            pen.lines([(1.5, -2.5 + b), (3.3, -4.2 + b), hand], 0.6, c["dress_hi"], edge=True)
        else:
            pen.lines([(1.5, -2.5 + b), (2.5, -1.2 + b), hand], 0.6, c["dress_hi"], edge=True)
        pen.oval(*hand, 0.42, 0.42, c["skin"], n=10)
    else:
        pen.lines([(1.5, -2.5 + b), (2.0, -0.4 + b), (2.1, 1.3 + b)], 0.6, c["dress_hi"], edge=True)
        pen.oval(2.1, 1.6 + b, 0.4, 0.4, c["skin"], n=10)


def paint_wolf(pen: Pen, frame: int, pose: str) -> None:
    """A big black wolf side on, bristling: red eyes, bared fangs, a bushy
    tail, and a torn strip of her gown's red lace knotted round its neck."""
    c = palette.FRAGILE_WOLF
    pen.edge = c["edge"]
    step = math.sin(frame * math.pi / 2)
    pen.shadow(-0.4, 6.9, 7.4, 1.2)
    # Tail, swishing (lowered with the body: see `low` below).
    pen.dv = 0.9
    t = 0.5 * step
    pen.poly([(-4.8, -1.8), (-6.4, -3.0 + t), (-8.2, -3.3 + t), (-9.2, -2.4 + t),
              (-8.4, -1.9 + t), (-9.0, -1.0 + t), (-7.8, -0.5 + t), (-8.2, 0.2 + t),
              (-6.4, 0.0 + t), (-4.9, 0.4)], c["fur"])
    pen.lines([(-5.2, -1.1), (-7.8, -1.6 + t)], 0.18, c["fur_hi"])
    pen.dv = 0.0
    # Far legs (darker), then the body, then the near legs. The legs run
    # from its hips (moved down with the body by `low`) to the floor.
    low = 0.9

    def leg(hx, hy, off, col, w):
        s = 0.9 * step * off
        hy += low
        knee = (hx - 0.8 + s, hy + 2.0) if hx < 0 else (hx + 0.2 + s, hy + 2.1)
        paw = (hx + 0.1 + s, 6.3)
        pen.lines([(hx, hy), knee, paw], w, col, edge=True)
        pen.oval(paw[0] + 0.35, 6.4, 0.75, 0.4, c["fur_dark"], n=10)

    leg(-3.2, 1.0, -1, c["fur_dark"], 0.8)
    leg(2.9, 1.0, 1, c["fur_dark"], 0.8)
    pen.dv = low
    pen.poly([(4.1, -2.0), (3.3, -3.4), (2.0, -3.9), (0.4, -3.3), (-1.4, -2.9), (-3.4, -3.1),
              (-4.8, -2.6), (-5.6, -1.2), (-5.4, 0.6), (-4.4, 2.0), (-3.0, 1.7), (-1.6, 1.0),
              (0.2, 1.1), (1.8, 2.0), (3.0, 2.5), (4.2, 1.2)], c["fur"])
    pen.oval(-1.2, -2.0, 3.0, 0.7, c["fur_hi"], edge=False, tilt=0.05)
    for k in range(5):                                       # hackles up along its back
        u = 3.1 - k * 0.85
        v = -3.5 + 0.12 * k + (0.25 if k == 0 else 0.0)
        pen.poly([(u + 0.45, v + 0.4), (u - 0.6, v - 0.75 + 0.1 * k), (u - 0.4, v + 0.5)],
                 c["fur_dark"])
    pen.lines([(-2.6, -1.6), (-3.6, -1.9), (-4.6, -1.2), (-5.0, 0.2)], 0.16, c["fur_hi"])  # haunch
    pen.lines([(3.2, -1.4), (2.4, -1.7), (1.8, -0.8)], 0.16, c["fur_hi"])                  # shoulder
    pen.dv = 0.0
    leg(-4.0, 1.0, 1, c["fur"], 0.95)
    leg(2.4, 1.2, -1, c["fur"], 0.95)
    pen.dv = low
    # Chest ruff and the head: ears up, snout out, fangs bared.
    pen.poly(_jagged(1.6, 4.4, -2.6, 0.0, 1.0) + [(4.6, 0.8), (3.6, 2.6), (2.7, 1.6),
                                                     (1.8, 2.4), (1.4, 0.0)], c["fur"])
    hx, hy = 5.2, -3.7
    pen.poly([(hx - 0.9, hy - 1.0), (hx - 0.6, hy - 3.6), (hx + 0.5, hy - 1.4)], c["fur_dark"])
    pen.oval(hx, hy, 2.25, 1.9, c["fur"])
    pen.poly([(hx - 0.2, hy - 1.2), (hx + 0.6, hy - 3.4), (hx + 1.3, hy - 1.0)], c["fur"])
    pen.poly([(hx + 0.4, hy - 1.5), (hx + 0.65, hy - 2.7), (hx + 0.95, hy - 1.4)], c["ear"],
             edge=False)
    jaw = 0.25 if pose == "howl" else 0.0
    pen.poly([(hx + 1.2, hy - 0.9), (hx + 3.8, hy - 0.2), (hx + 3.9, hy + 0.5), (hx + 1.4, hy + 0.9)],
             c["fur"])
    pen.poly([(hx + 1.3, hy + 0.9), (hx + 3.0, hy + 0.7 + jaw), (hx + 2.8, hy + 1.3 + jaw),
              (hx + 1.0, hy + 1.6)], c["fur_dark"])
    pen.line((hx + 1.4, hy + 0.85), (hx + 3.2, hy + 0.6 + jaw), 0.14, c["mouth"])
    for u in (hx + 2.0, hx + 2.8):
        pen.poly([(u - 0.15, hy + 0.55), (u + 0.15, hy + 0.55), (u, hy + 1.05)], c["fang"],
                 edge=False)
    pen.oval(hx + 3.85, hy - 0.05, 0.32, 0.28, c["nose"], edge=False, n=10)
    pen.oval(hx + 0.6, hy - 0.5, 0.75, 0.4, c["eye_glow"], edge=False, n=12)
    pen.oval(hx + 0.65, hy - 0.5, 0.45, 0.2, c["eye"], edge=False, n=10)
    # The torn strip of her gown's red lace, knotted round its neck, an end flapping.
    pen.poly([(2.6, -3.0), (3.6, -3.2), (4.0, 0.2), (3.0, 0.4)], c["collar"])
    pen.poly([(2.8, -1.4), (1.4, -0.8 + 0.3 * step), (0.6, 0.2 + 0.3 * step), (1.6, -0.3),
              (2.7, -0.6)], c["collar"])


def paint_fragile_sitting(pen: Pen, frame: int, pose: str) -> None:
    """Beaten, sitting on the floor in a pool of her own hair: knees up,
    hugging them, her face down, crying. Pose "hug": Mr. Buttons back in
    her arms, her head up, eyes closed, smiling."""
    c = palette.FRAGILE
    pen.edge = c["edge"]
    hug = pose == "hug"
    pen.shadow(-0.6, 6.4, 5.6, 1.1)
    # Her hair pooled round her on the floor, and down her back.
    pen.poly([(-1.4, -6.6), (-3.6, -4.4), (-4.6, 0.6), (-5.8, 4.6), (-6.2, 6.2), (-3.0, 6.7),
              (0.4, 6.4), (2.0, 6.0), (-0.4, 4.4), (-1.4, 1.4)], c["hair"])
    for u in (-5.0, -3.8, -2.6):
        pen.lines([(u + 1.4, -2.6), (u + 0.6, 2.0), (u, 5.6)], 0.16, c["hair_hi"])
    # Her gown: the corset leaning over her knees, the skirt spread on the
    # floor round her, red lace at its hem.
    pen.poly([(-4.4, 6.4), (-3.4, 3.8), (-1.0, 3.4), (2.6, 4.2), (4.2, 5.4), (4.4, 6.4)],
             c["dress_dark"])
    for k in range(9):
        pen.oval(-4.2 + k * 1.05, 6.45, 0.34, 0.26, c["lace"], edge=False, n=8)
    pen.poly([(-2.6, -2.4), (0.4, -3.0), (1.4, 0.6), (0.6, 4.6), (-2.4, 4.6)], c["dress"])
    pen.poly([(-2.6, -2.4), (-1.4, -2.7), (-1.0, 4.6), (-2.4, 4.6)], c["dress_dark"], edge=False)
    pen.poly([(-2.5, 3.2), (0.9, 3.2), (0.8, 3.8), (-2.4, 3.8)], c["lace"])
    # Knees up under the skirt, a boot toe on the floor.
    pen.poly([(-0.6, 3.6), (2.0, 0.4), (3.4, 0.6), (3.9, 5.6), (0.6, 5.4)], c["dress"])
    pen.line((2.4, 1.2), (3.0, 5.2), 0.14, c["dress_hi"])
    pen.poly([(3.6, 5.2), (4.9, 5.5), (4.8, 6.0), (3.6, 6.0)], c["boot"])
    if hug:
        bear = (1.9, -0.6)
        paint_bear(Pen(pen.surf, pen.to_px, pen.s, pen.flip, pen.hurt), *bear, 0.42)
        hv = -4.7
        pen.oval(0.0, hv, 1.9, 2.1, c["skin"])
        pen.oval(-0.9, hv + 0.3, 0.9, 1.5, c["skin_dark"], edge=False)
        pen.poly([(-1.7, hv - 0.4), (-2.8, hv - 1.6), (-1.8, hv + 0.6)], c["skin"])
        for u in (0.3, 1.4):                               # eyes closed, happy
            pen.lines([(u - 0.35, hv + 0.1), (u, hv - 0.25), (u + 0.35, hv + 0.1)], 0.13,
                      c["edge"])
        pen.oval(1.5, hv + 0.75, 0.35, 0.18, c["blush"], edge=False, n=10)
        pen.lines([(0.5, hv + 1.2), (0.9, hv + 1.45), (1.4, hv + 1.2)], 0.12, c["mouth"])
        pen.poly([(-1.9, hv - 0.6), (-1.3, hv - 2.3), (0.4, hv - 2.7), (2.1, hv - 1.6),
                  (2.1, hv - 0.4), (1.4, hv - 1.1), (0.8, hv - 0.5), (0.0, hv - 1.2),
                  (-0.8, hv - 0.2)], c["hair"])
        # Her arms round the bear.
        pen.lines([(-1.6, -2.0), (0.0, 0.6), (1.4, 0.2)], 0.55, c["dress_dark"], edge=True)
        pen.lines([(0.2, -2.6), (2.0, -1.0), (3.0, -1.4)], 0.55, c["dress_hi"], edge=True)
        return
    # Her arms round her knees, her face buried on them.
    pen.lines([(-0.4, -2.4), (1.6, 0.0), (3.2, 0.8)], 0.55, c["dress_hi"], edge=True)
    hv = -3.7
    pen.oval(1.2, hv, 1.9, 2.0, c["skin"])
    pen.oval(0.2, hv - 0.2, 1.0, 1.5, c["skin_dark"], edge=False)
    for u in (1.5, 2.5):                                    # eyes squeezed shut
        pen.line((u - 0.35, hv + 0.3), (u + 0.3, hv + 0.15), 0.13, c["edge"])
    pen.poly([(-0.7, hv - 0.5), (-0.3, hv - 2.3), (1.6, hv - 2.4), (3.2, hv - 1.0), (3.0, hv + 0.2),
              (2.4, hv - 0.6), (1.8, hv - 0.1), (1.0, hv - 0.8), (0.2, hv + 0.4)], c["hair"])
    for u in (1.6, 2.6):                                    # tears
        pen.lines([(u, hv + 0.5), (u + 0.1, hv + 1.6)], 0.14, c["tear"])
        pen.oval(u + 0.15, hv + 2.4 + 0.3 * (frame % 2), 0.2, 0.3, c["tear"], edge=False, n=8)


# --- Mr. Buttons ------------------------------------------------------------------------------

def paint_bear(pen: Pen, u0: float, v0: float, k: float) -> None:
    """Mr. Buttons, sitting, `k` art units a bear unit, centred on (u0, v0):
    tan, sewn back together (stitched seams, a purple patch), one bead eye
    and one big blue button eye, a red bow (hers)."""
    c = palette.MR_BUTTONS
    pen.edge = c["edge"]

    def U(u, v):
        return u0 + u * k, v0 + v * k

    def O(u, v, ru, rv, col, edge=True, n=16):
        pen.oval(*U(u, v), ru * k, rv * k, col, edge, n)

    for side in (-1, 1):
        O(side * 2.6, -4.2, 1.3, 1.25, c["fur"])
        O(side * 2.6, -4.1, 0.6, 0.55, c["inner"], edge=False, n=10)
    for side in (-1, 1):
        O(side * 2.8, 1.5, 1.05, 1.5, c["fur"])
    O(0, 2.3, 2.6, 2.4, c["fur"])
    O(-0.6, 2.8, 1.6, 1.4, c["shade"], edge=False)
    for side in (-1, 1):
        O(side * 1.6, 4.4, 1.35, 1.0, c["fur"])
        O(side * 1.6 + side * 0.15, 4.5, 0.65, 0.5, c["inner"], edge=False, n=10)
    pen.poly([U(0.7, 1.9), U(2.0, 1.9), U(2.0, 3.2), U(0.7, 3.2)], c["patch"])
    O(0, -2.2, 3.0, 2.6, c["fur"])
    O(0, -1.2, 1.35, 0.95, c["muzzle"], edge=False)
    O(0, -1.6, 0.5, 0.33, c["edge"], edge=False, n=10)
    O(-1.25, -2.7, 0.45, 0.45, c["edge"], edge=False, n=10)          # the bead eye
    O(1.3, -2.75, 0.85, 0.85, c["button"], n=12)                     # the button eye
    pen.dot(*U(1.1, -2.8), max(0.05, 0.16 * k), c["edge"])
    pen.dot(*U(1.5, -2.7), max(0.05, 0.16 * k), c["edge"])
    # Seams where the pieces were sewn together.
    pen.line(U(-0.2, 0.4), U(0.1, 4.4), 0.12 * k, c["stitch"])
    pen.line(U(-2.2, -4.0), U(-0.9, -1.0), 0.12 * k, c["stitch"])
    # Her red bow at his neck.
    pen.poly([U(0, 0.25), U(-1.3, -0.45), U(-1.3, 0.95)], c["bow"])
    pen.poly([U(0, 0.25), U(1.3, -0.45), U(1.3, 0.95)], c["bow"])
    O(0, 0.25, 0.4, 0.4, c["bow"], n=10)


def paint_bear_figure(pen: Pen, frame: int, pose: str) -> None:
    """Mr. Buttons alone (on a hero's head, or dropped on the floor)."""
    paint_bear(pen, 0.0, 0.0, 1.0)


# --- Nettle, the Blighted (M25.1) -------------------------------------------------------------

def paint_nettle(pen: Pen, frame: int, pose: str) -> None:
    """A corrupted pixie hovering, seen front on: tattered grey-violet moth
    wings with rot-green eye spots (flapping over the 4 frames), wild dark
    green hair stuck with twigs, pale green-grey skin, glowing eyes, and a
    ragged dress of dead leaves. Poses: "" (hovering), "cast" (arms up,
    a glow in each hand), "dive" (wings swept back, arms back). Her
    shadow is drawn by render/nettle.py (her copies have none)."""
    c = palette.NETTLE
    pen.edge = c["edge"]
    cast, dive = pose == "cast", pose == "dive"
    flap = (1.0, 0.72, 0.45, 0.72)[frame % 4] * (0.55 if dive else 1.0)
    lift = (0.0, -0.25, -0.4, -0.25)[frame % 4]

    # The wings, behind her: upper pair big, lower pair small, tattered.
    for side in (-1, 1):
        def W(u, v, k=flap):
            u, v = u * 1.3, (v + 2.0) * 1.3 - 2.0          # (big wings for a little pixie)
            return (side * (0.6 + (u - 0.6) * k), v + (lift if u > 2 else 0.0)
                    + (1.2 if dive and u > 2 else 0.0))
        upper = [W(0.6, -3.2), W(3.0, -6.6), W(5.6, -8.0), W(6.4, -7.0), W(7.2, -5.4),
                 W(6.2, -4.6), W(6.8, -3.4), W(5.0, -2.2), W(2.4, -1.8), W(0.8, -1.8)]
        pen.poly(upper, c["wing"])
        pen.poly([W(1.0, -2.6), W(3.4, -5.6), W(5.4, -6.8), W(5.6, -5.2), W(4.2, -3.0)],
                 c["wing_hi"], edge=False)
        lower = [W(0.7, -1.4), W(3.6, -0.6), W(5.0, 1.2), W(4.6, 3.4), W(3.6, 2.6), W(2.6, 3.2),
                 W(1.0, 0.6)]
        pen.poly(lower, c["wing_dark"])
        eu, ev = W(4.8, -5.4)
        pen.oval(eu, ev, 1.0 * max(0.5, flap), 0.9, c["spot"], n=14)
        pen.oval(eu, ev, 0.45 * max(0.5, flap), 0.42, c["edge"], edge=False, n=10)
        for root, tip in ((W(0.8, -2.2), W(5.6, -7.6)), (W(0.8, -2.0), W(6.6, -4.4)),
                          (W(0.9, -1.0), W(4.4, 2.6))):
            pen.line(root, tip, 0.1, c["vein"])
    # Legs dangling, toes pointed down.
    for u, k in ((-0.45, 0), (0.45, 1)):
        sw = 0.25 * math.sin(frame * math.pi / 2 + k * math.pi)
        pen.lines([(u, 2.6), (u + sw, 4.8), (u + sw * 1.4, 6.2)], 0.38, c["skin_dark"] if k == 0
                  else c["skin"], edge=True)
    # Her dress of dead leaves: a ragged skirt of points, a bodice.
    pen.poly([(-1.2, -2.6), (1.2, -2.6), (1.4, 0.0), (2.6, 2.4), (1.8, 2.0), (1.6, 3.4), (0.8, 2.4),
              (0.2, 3.6), (-0.5, 2.4), (-1.2, 3.4), (-1.5, 2.0), (-2.5, 2.6), (-1.4, 0.0)],
             c["leaf"])
    pen.poly([(-1.4, 0.0), (-2.5, 2.6), (-1.5, 2.0), (-1.2, 3.4), (-0.5, 2.4), (-0.4, 0.0)],
             c["leaf_dark"], edge=False)
    for u, v in ((0.6, -1.6), (-0.6, 0.8), (1.2, 1.6)):
        pen.oval(u, v, 0.35, 0.22, c["rot"], edge=False, n=8)
    pen.line((0.0, -2.4), (0.0, 0.4), 0.1, c["leaf_dark"])
    # Arms: up with a glow in each hand to cast, swept back to dive.
    for side in (-1, 1):
        if cast:
            hand = (side * 3.2, -6.0)
            pen.lines([(side * 1.1, -2.4), (side * 2.2, -3.8), hand], 0.36, c["skin"], edge=True)
            pen.oval(*hand, 0.9, 0.9, c["glow"], edge=False, n=12)
            pen.dot(*hand, 0.3, c["eye"])
        elif dive:
            pen.lines([(side * 1.1, -2.4), (side * 2.0, -1.0), (side * 2.6, 0.2)], 0.36, c["skin"],
                      edge=True)
        else:
            pen.lines([(side * 1.1, -2.4), (side * 1.9, -0.8), (side * 1.6, 0.8)], 0.36, c["skin"],
                      edge=True)
    # Head: pointed ears, glowing eyes, a sly little mouth.
    hv = -4.6
    for side in (-1, 1):
        pen.poly([(side * 1.2, hv - 0.2), (side * 3.0, hv - 1.4), (side * 1.4, hv + 0.6)], c["skin"])
    pen.oval(0.0, hv, 1.5, 1.7, c["skin"])
    pen.oval(-0.6, hv + 0.3, 0.7, 1.1, c["skin_dark"], edge=False, n=12)
    for u in (-0.55, 0.55):
        pen.oval(u, hv - 0.1, 0.42, 0.3, c["eye_glow"], edge=False, n=10)
        pen.oval(u, hv - 0.1, 0.26, 0.2, c["eye"], edge=False, n=10)
    pen.lines([(-0.4, hv + 0.9), (0.1, hv + 1.05), (0.5, hv + 0.8)], 0.1, c["edge"])
    # Wild hair stuck with twigs and thorns.
    hair = [(-1.8, hv + 0.4), (-2.4, hv - 1.0), (-1.9, hv - 1.4), (-2.4, hv - 2.4), (-1.2, hv - 2.2),
            (-1.0, hv - 3.2), (-0.2, hv - 2.4), (0.4, hv - 3.4), (0.8, hv - 2.3), (1.8, hv - 2.9),
            (1.6, hv - 1.8), (2.4, hv - 1.4), (1.8, hv - 0.8), (1.9, hv + 0.4), (1.2, hv - 0.8),
            (0.4, hv - 1.2), (-0.6, hv - 0.7), (-1.3, hv - 0.9)]
    pen.poly(hair, c["hair"])
    for (u0, v0), (u1, v1) in (((-0.8, -2.0), (-1.8, -3.6)), ((0.6, -2.2), (1.4, -3.9)),
                               ((1.4, -1.6), (2.8, -2.6))):
        pen.line((u0, hv + v0), (u1, hv + v1), 0.14, c["twig"])
    for u, v in ((-1.6, -3.0), (1.1, -3.3), (2.3, -2.3)):
        pen.dot(u, hv + v, 0.14, c["thorn"])


# --- The registry draw_character() reads ------------------------------------------------------

# --- Love & Cuddles (M25.2) -------------------------------------------------------------


def _heart(pen: Pen, u: float, v: float, r: float, color) -> None:
    """A little heart (two dots and a point), for its bow."""
    pen.dot(u - r * 0.5, v, r * 0.6, color)
    pen.dot(u + r * 0.5, v, r * 0.6, color)
    pen.poly([(u - r * 1.05, v + r * 0.15), (u + r * 1.05, v + r * 0.15), (u, v + r * 1.4)],
             color, edge=False)


def _cleaver(pen: Pen, c, hand, angle: float, size: float, bloody: int) -> None:
    """Its cleaver: a wooden handle from `hand`, a broad blade beyond it
    (turned to `angle`, art radians: 0 = forward), a hole in the corner,
    blood on it from the second look on."""
    ca, sa = math.cos(angle), math.sin(angle)

    def R(a, b):                       # (a along the handle, b across it)
        return hand[0] + a * ca - b * sa, hand[1] + a * sa + b * ca
    pen.lines([R(-0.4, 0), R(1.4 * size, 0)], 0.42, c["handle"], edge=True)
    blade = [R(1.3 * size, -0.4), R(4.3 * size, -0.4), R(4.3 * size, 2.3 * size),
             R(1.6 * size, 2.3 * size), R(1.3 * size, 1.4 * size)]
    pen.poly(blade, c["blade"])
    pen.line(R(1.5 * size, 2.15 * size), R(4.2 * size, 2.15 * size), 0.18, c["blade_hi"])
    pen.dot(*R(3.7 * size, 0.3), 0.22, c["edge"])
    for k in range(bloody * 2):
        pen.dot(*R((2.0 + 0.7 * k) * size, (0.6 + 0.5 * (k % 2)) * size), 0.28 + 0.06 * k,
                c["blood"])


def paint_love(pen: Pen, frame: int, pose: str) -> None:
    """Love & Cuddles: a round, fluffy pastel-pink squirrel seen 3/4 on --
    a huge curled tail behind it, a cream belly, big shiny eyes, rosy
    cheeks, a pink bow with red hearts between its ears, and a cleaver
    hidden behind its back (just the blade peeking out).

    `pose` is "<look>:<action>". The look (0, 1, 2: its phase) goes from
    adorable to not: 1 -- fur matted and blood-spattered, its front eye
    twitching red, a grin with teeth; 2 -- spikier fur, more blood, the
    bow torn, both eyes wrong and the grin ear to ear. Actions: "" (the
    cleaver behind it), "cleaver" (raised high), "frenzy" (held out in
    front), "puff" (cheeks stuffed), "dig" (paws down, digging), "pant"
    (slumped, tongue out, the cleaver dropped), "call" (a paw to its mouth,
    whistling), "throw" (a pinecone held back to throw)."""
    c = palette.LOVE_CUDDLES
    pen.edge = c["edge"]
    look, _, act = pose.partition(":")
    look = int(look or 0)
    pant, dig, puff = act == "pant", act == "dig", act == "puff"
    b = _bob(frame) * (0.4 if pant else 1.0)
    sway = 0.35 * math.sin(frame * math.pi / 2)
    hv = -3.4 + b + (1.4 if pant else 0.0) + (0.9 if dig else 0.0)   # the head's middle
    hu = 1.0 + (0.8 if dig else 0.0)
    pen.shadow(0.0, 8.6, 6.4, 1.3)

    # The tail: a big fluffy S curling up behind it, tufts along it.
    tail = [(-3.0, 5.0, 2.4), (-5.0, 3.0, 2.6), (-6.1, 0.0, 2.5), (-6.0, -3.0, 2.3),
            (-4.9, -5.6, 2.1), (-3.2, -7.2, 1.8), (-1.6, -7.4, 1.3)]
    # (one outline round the whole plume: outline ovals a little bigger
    # first, then the fur over them without edges)
    out = 0.22
    for k, (u, v, r) in enumerate(tail):
        w = sway * k / len(tail)
        pen.oval(u + w, v + b * 0.5, r + out, r * 0.95 + out, c["edge"], edge=False, n=18)
    for k, (u, v, r) in enumerate(tail):
        w = sway * k / len(tail)
        pen.oval(u + w, v + b * 0.5, r, r * 0.95, c["fur_shade"], edge=False, n=18)
    for k, (u, v, r) in enumerate(tail[1:-1]):
        w = sway * (k + 1) / len(tail)
        pen.oval(u + w + 0.5, v + b * 0.5 - 0.2, r * 0.62, r * 0.6, c["fur"], edge=False, n=14)
    for k, (u, v, r) in enumerate(tail[2:]):     # (fur strokes down the plume)
        w = sway * (k + 2) / len(tail)
        pen.line((u + w - r * 0.5, v + b * 0.5 + r * 0.3), (u + w - r * 0.1, v + b * 0.5 - r * 0.2),
                 0.14, c["fur_dark"])
    if look:
        for k, (u, v, r) in enumerate(tail[:-1]):
            w = sway * k / len(tail)
            pen.poly([(u + w - r * 0.9, v - r * 0.2), (u + w - r * 1.35 - look * 0.3, v - r * 0.5),
                      (u + w - r * 0.8, v + r * 0.3)], c["matted"])
    # The cleaver behind its back: just the blade peeking out.
    if act in ("", "puff", "call", "dig"):
        _cleaver(pen, c, (-1.2, 3.4 + b), math.pi * 0.62, 1.0, look)
    elif pant:
        _cleaver(pen, c, (5.4, 7.6), 0.15, 0.9, look)
    # Feet.
    for u in (-1.6, 2.4):
        pen.oval(u + (0.8 if dig else 0.0), 7.7, 1.4, 0.65, c["fur_dark"])
    # The body: round as a ball, a cream belly.
    bu, bv = 0.4, 3.0 + b + (0.7 if pant else 0.0)
    if look:                           # (matted: tufts poking out round it)
        for k in range(7 + 3 * look):
            a = -2.6 + k * 4.6 / (6 + 3 * look)
            r = 4.5 + (0.6 if k % 2 else 0.2) * look
            pen.poly([(bu + math.cos(a - 0.12) * 4.2, bv + math.sin(a - 0.12) * 4.3),
                      (bu + math.cos(a) * r, bv + math.sin(a) * (r + 0.2)),
                      (bu + math.cos(a + 0.12) * 4.2, bv + math.sin(a + 0.12) * 4.3)],
                     c["matted"])
    pen.oval(bu, bv, 4.4, 4.6 - (0.5 if pant else 0.0), c["fur"])
    pen.oval(bu - 1.6, bv + 0.6, 2.2, 3.2, c["fur_shade"], edge=False, n=16)
    pen.oval(bu + 1.0, bv + 0.6, 2.6, 3.3, c["belly"], edge=False, n=18)
    pen.oval(bu + 1.6, bv - 1.6, 1.0, 0.6, c["fur_hi"], edge=False, n=10)
    if look:
        for k, (u, v, r) in enumerate(((1.8, 2.4, 0.45), (0.4, 4.6, 0.3), (2.6, 4.0, 0.35),
                                       (1.0, 1.2, 0.25), (3.0, 1.8, 0.3), (-0.4, 3.0, 0.4))):
            if k < 3 * look:
                pen.dot(u, v + b, r, c["blood"] if k % 2 else c["blood_dark"])
    # Arms and whatever its paws hold.
    shoulder = (bu + 2.0, bv - 2.6)
    arm = 1.0
    if act == "cleaver":
        hand = (4.6, -3.6 + b)
        pen.lines([shoulder, (4.2, -1.6 + b), hand], arm, c["fur"], edge=True)
        _cleaver(pen, c, hand, -math.pi / 2 + 0.15, 1.15, look)
        pen.oval(*hand, 0.75, 0.65, c["fur_hi"])
    elif act == "frenzy":
        hand = (4.3, 0.6 + b)
        pen.lines([shoulder, hand], arm, c["fur"], edge=True)
        _cleaver(pen, c, hand, -0.2, 0.95, max(1, look))
        pen.oval(*hand, 0.75, 0.65, c["fur_hi"])
    elif act == "throw":
        hand = (-0.4, -6.4 + b)
        pen.lines([shoulder, (0.6, -4.4 + b), hand], arm, c["fur"], edge=True)
        pen.oval(hand[0], hand[1] - 0.8, 0.9, 1.2, c["handle"])
        for k in range(3):
            pen.line((hand[0] - 0.8, hand[1] - 1.4 + k * 0.6), (hand[0] + 0.8, hand[1] - 1.0 + k * 0.6),
                     0.12, c["claw"])
    elif act == "call":
        hand = (hu + 2.8, hv + 1.6)
        pen.lines([shoulder, (3.6, 0.0 + b), hand], arm, c["fur"], edge=True)
        pen.oval(*hand, 0.75, 0.65, c["fur_hi"])
    elif dig:
        for hand in ((4.2, 4.0 + (frame % 2) * 0.6), (3.4, 4.6 + ((frame + 1) % 2) * 0.6)):
            pen.lines([shoulder, hand], arm, c["fur"], edge=True)
            pen.oval(*hand, 0.75, 0.55, c["fur_hi"])
        for k in range(3):
            pen.dot(5.6 + k * 0.6, 6.0 - (frame + k) % 3 * 0.7, 0.25, c["claw"])
    elif pant:
        pen.lines([shoulder, (3.4, 4.4)], arm, c["fur"], edge=True)
    else:                              # (paws behind its back, hiding the cleaver)
        pen.lines([shoulder, (1.6, 1.6 + b)], arm, c["fur"], edge=True)

    # The head: ears with tufts, then a big round face.
    for (u0, v0), (u1, v1), (u2, v2) in (((-1.4, -2.2), (-2.0, -6.2), (0.2, -2.8)),
                                         ((2.2, -2.8), (3.6, -6.0), (3.9, -2.0))):
        droop = 1.2 if pant else 0.0
        pen.poly([(hu + u0 - 1.0, hv + v0 + 0.4), (hu + u1 - 1.0 - droop, hv + v1 + droop),
                  (hu + u2 - 1.0, hv + v2 + 0.4)], c["fur"])
        pen.poly([(hu + u0 - 0.8, hv + v0 + 0.2), (hu + u1 - 0.95 - droop, hv + v1 + 1.0 + droop),
                  (hu + u2 - 1.15, hv + v2 + 0.2)], c["cheek"], edge=False)
    rw = 3.7 + (0.5 if puff else 0.0)
    pen.oval(hu, hv, rw, 3.2, c["fur"])
    pen.oval(hu - 1.4, hv + 0.6, 1.6, 2.2, c["fur_shade"], edge=False, n=14)
    pen.oval(hu + 1.6, hv + 1.2, 2.1, 1.6, c["belly"], edge=False, n=16)
    if look:                           # (blood on its face)
        pen.dot(hu - 1.8, hv - 1.0, 0.35, c["blood"])
        if look >= 2:
            pen.dot(hu + 0.4, hv - 2.2, 0.3, c["blood_dark"])
            pen.dot(hu + 3.0, hv + 0.2, 0.25, c["blood"])
    # Cheeks: rosy (stuffed full to puff).
    for u, r in ((-1.9, 0.75), (2.5, 0.85)):
        if puff:
            pen.oval(hu + u * 1.15, hv + 1.1, r * 1.9, r * 1.4, c["fur"], n=16)
            pen.oval(hu + u * 1.15, hv + 1.2, r * 1.2, r * 0.8, c["cheek"], edge=False, n=12)
        else:
            pen.oval(hu + u, hv + 1.2, r, r * 0.6, c["cheek"], edge=False, n=12)
    # Eyes: huge and shiny -- then the front one twitches red, then both go wrong.
    twitch = look >= 1 and frame % 2 == 1
    for k, (u, ru) in enumerate(((-0.8, 1.0), (1.8, 1.05))):
        ex, ey = hu + u, hv - 0.4
        if pant:
            pen.lines([(ex - 0.8, ey + 0.1), (ex, ey - 0.3), (ex + 0.8, ey + 0.1)], 0.22,
                      c["eye"])
            continue
        rv = 1.25 * (0.55 if (twitch and k == 1) else 1.0)
        pen.oval(ex, ey, ru, rv, c["eye"], n=18)
        if look >= 1 and (k == 1 or look >= 2):
            pen.oval(ex + 0.1, ey + 0.1, ru * 0.55, rv * 0.5, c["eye_red"], edge=False, n=12)
            pen.dot(ex + 0.15, ey + 0.1, 0.18, c["eye"])
        if look >= 2:                  # (dark rings under them)
            pen.line((ex - ru * 0.8, ey + rv + 0.15), (ex + ru * 0.8, ey + rv + 0.15), 0.2,
                     c["fur_dark"])
        pen.dot(ex - ru * 0.35, ey - rv * 0.4, 0.38, c["shine"])
        pen.dot(ex + ru * 0.3, ey + rv * 0.3, 0.16, c["shine"])
    # Nose and mouth: a little smile, then teeth, then ear to ear.
    nx, ny = hu + 3.3, hv + 0.6
    pen.oval(nx, ny, 0.5, 0.38, c["nose"], n=10)
    if pant:
        pen.oval(hu + 2.2, hv + 2.0, 0.9, 0.7, c["mouth"], n=12)
        pen.oval(hu + 2.4, hv + 2.8, 0.45, 0.8, c["cheek"], n=10)
    elif puff:
        pen.lines([(hu + 1.8, hv + 1.7), (hu + 2.6, hv + 1.9)], 0.15, c["edge"])
    elif look == 0:
        pen.lines([(hu + 1.9, hv + 1.4), (hu + 2.4, hv + 1.8), (nx, ny + 0.5), (hu + 3.4, hv + 1.8),
                   (hu + 3.8, hv + 1.4)], 0.14, c["edge"])
    else:
        left = hu + (0.9 if look == 1 else -1.6)
        mid_v = hv + (2.4 if look == 1 else 2.9)
        grin = [(left, hv + 1.3), (hu + 1.4, hv + 1.6), (hu + 3.9, hv + 1.2),
                (hu + 3.2, mid_v - 0.4), (hu + 1.6, mid_v), (left + 0.5, hv + 2.0)]
        pen.poly(grin, c["mouth"])
        for k in range(4 + 2 * look):
            u = left + 0.45 + k * (hu + 3.6 - left - 0.45) / (4 + 2 * look)
            pen.poly([(u, hv + 1.45), (u + 0.32, hv + 1.45), (u + 0.16, hv + 2.0)], c["teeth"],
                     edge=False)
    # The bow between its ears, hearts on its loops (one torn in look 2).
    bx, by = hu - 0.6, hv - 3.1
    torn = look >= 2
    pen.poly([(bx, by), (bx - 2.0, by - 1.3), (bx - 2.3, by + 0.6)], c["bow"])
    if torn:
        pen.poly([(bx, by), (bx + 1.0, by + 1.6), (bx + 1.8, by + 2.4), (bx + 0.6, by + 0.8)],
                 c["bow_dark"])
    else:
        pen.poly([(bx, by), (bx + 2.0, by - 1.4), (bx + 2.3, by + 0.5)], c["bow"])
    pen.oval(bx, by, 0.55, 0.5, c["bow_dark"], n=10)
    _heart(pen, bx - 1.5, by - 0.5, 0.35, c["heart"])
    if not torn:
        _heart(pen, bx + 1.5, by - 0.6, 0.35, c["heart"])
    if pant:                           # (sweat flying off it)
        for k in range(3):
            pen.dot(hu - 3.0 - k * 0.4, hv - 2.0 - (frame + k) % 4 * 0.5, 0.22, c["shine"])


# --- The Fallen (M25.3) -----------------------------------------------------------------


def paint_fallen(pen: Pen, frame: int, pose: str) -> None:
    """The Fallen: a tall, thin tree, more branches than trunk -- a crown of
    bare branches with a few clumps of leaves, two long grasping branch-arms
    ending in twig fingers, one big eye in a hollow, and roots for legs.

    `pose` is "<look>:<action>"; the look (0, 1, 2: its phase) adds roots
    glowing faintly, then cracks of glowing sap -- except posing as a tree
    ("still", "blink"), which every lookalike in its grove shares exactly
    (arms raised as branches, roots planted, the eye shut -- or, "blink",
    open: its tell). Actions: "" (stalking on its roots), "sweep" (an arm
    drawn back), "swing" (it lashed out), "charge" (leaning in, roots up),
    "cast" (arms up and wide), "maw" (its trunk split into a toothy maw),
    "stun" (slumped, the eye half shut)."""
    c = palette.THE_FALLEN
    pen.edge = c["edge"]
    look, _, act = pose.partition(":")
    still = act in ("still", "blink")
    look = 0 if still else int(look or 0)
    stun, maw, charge = act == "stun", act == "maw", act == "charge"
    lean = 1.0 if charge else (-0.6 if stun else 0.0)
    sag = 0.6 if stun else 0.0
    pen.shadow(0.0, 8.6, 5.2, 1.0)

    # Roots for legs: splayed, stepping (planted when it poses as a tree,
    # bunched up mid-charge).
    for k, (u, spread) in enumerate(((-1.0, -3.6), (-0.4, -1.6), (0.4, 1.4), (1.0, 3.4))):
        step = 0.0 if still else 0.5 * math.sin(frame * math.pi / 2 + k * 1.7)
        tip_u = u + spread * (0.55 if charge else 1.0)
        tip_v = 8.4 - (0.9 if charge and k % 2 else 0.0) - max(0.0, step)
        pen.lines([(u * 0.8, 5.6), (u + spread * 0.5, 7.0 - abs(step) * 0.4), (tip_u, tip_v)],
                  0.42, c["bark_dark"] if k % 2 else c["bark"], edge=True)
        if look >= 1:
            pen.line((u + spread * 0.5, 7.0), (tip_u, tip_v), 0.12, c["moss"])

    def B(u, v):                       # (the trunk leans from the roots up)
        return u + lean * (5.6 - v) / 10, v + sag * (5.6 - v) / 10

    # The far arm, behind the trunk.
    if still:
        far = [B(-0.7, -0.8), B(-3.1, -4.0), B(-3.9, -6.6)]
    elif act == "cast":
        far = [B(-0.7, -0.8), B(-3.6, -3.4), B(-5.6, -5.8)]
    elif stun:
        far = [B(-0.7, 0.2), B(-2.4, 2.8), B(-2.8, 5.6)]
    else:
        far = [B(-0.7, 0.0), B(-3.2, 1.6), B(-4.4, 4.0)]
    pen.lines(far, 0.5, c["bark_dark"], edge=True)
    _twigs(pen, c, far[-1], far[-2], c["bark_dark"])
    # The trunk: thin and tall, a hollow for its eye.
    bulge = 0.9 if maw else 0.0
    trunk = [B(-1.4, 6.0), B(1.4, 6.0), B(1.0 + bulge, 2.6), B(1.3 + bulge * 0.6, -0.8),
             B(0.9, -4.2), B(-0.9, -4.2), B(-1.3 - bulge * 0.6, -0.8), B(-1.0 - bulge, 2.6)]
    pen.poly(trunk, c["bark"])
    pen.poly([B(-1.4, 6.0), B(-0.4, 6.0), B(-0.5, -0.8), B(-0.4, -4.2), B(-0.9, -4.2),
              B(-1.3 - bulge * 0.6, -0.8), B(-1.0 - bulge, 2.6)], c["bark_dark"], edge=False)
    for u, v in ((0.5, 4.4), (-0.2, 1.8), (0.6, -2.6), (-0.6, 3.2)):
        pen.dot(*B(u, v), 0.22, c["lichen"])
    pen.line(B(0.5, 5.4), B(0.3, 3.4), 0.12, c["bark_hi"])
    if look >= 2:                      # (cracks of glowing sap)
        pen.lines([B(0.2, 5.2), B(-0.3, 3.8), B(0.4, 2.6), B(-0.1, 1.2)], 0.14, c["sap"])
        pen.lines([B(-0.5, -2.0), B(0.1, -3.0), B(-0.2, -3.9)], 0.12, c["sap"])
    if maw:                            # (its trunk split into a maw)
        pen.oval(*B(0.0, 2.6), 1.5, 2.1, c["maw"], n=20)
        pen.oval(*B(0.1, 2.8), 0.9, 1.4, c["maw_deep"], edge=False, n=16)
        for k in range(5):
            v = 1.0 + k * 0.75
            for side in (-1, 1):
                w = 1.25 * math.sqrt(max(0.0, 1 - ((v - 2.6) / 2.1) ** 2))
                pen.poly([B(side * w, v - 0.25), B(side * w, v + 0.25), B(side * (w - 0.6), v)],
                         c["tooth"], edge=False)
    # The crown: bare branches, a few clumps of leaves.
    sway = 0.15 * math.sin(frame * math.pi / 2) if not still else 0.0
    for (u0, v0), (u1, v1), (u2, v2) in (((0.0, -4.0), (-2.6, -6.6), (-4.6, -7.6)),
                                         ((0.0, -4.1), (-0.9, -7.2), (-1.4, -9.2)),
                                         ((0.2, -4.1), (1.3, -7.0), (2.0, -9.0)),
                                         ((0.3, -4.0), (2.8, -6.0), (4.8, -7.0))):
        pts = [B(u0, v0), B(u1 + sway, v1), B(u2 + sway * 2, v2)]
        pen.lines(pts, 0.55, c["bark"], edge=True)
        fork = B((u1 + u2) / 2 + sway + (0.9 if u2 >= 0 else -0.9), v1 - 0.9)
        pen.lines([B(u1 + sway, v1), fork], 0.3, c["bark"], edge=True)
        pen.line(fork, (fork[0] + (0.6 if u2 >= 0 else -0.6), fork[1] - 0.7), 0.14, c["twig"])
    for u, v, r in ((-3.6, -7.5, 1.4), (1.9, -8.3, 1.3), (4.2, -6.7, 1.2), (-1.0, -8.8, 1.1),
                    (3.4, -8.6, 0.8)):
        pen.oval(*B(u + sway, v), r, r * 0.7, c["leaf"], n=14)
        pen.oval(*B(u + sway - 0.25, v + 0.2), r * 0.55, r * 0.35, c["leaf_dark"], edge=False,
                 n=10)
    # The eye in its hollow: shut (a lid), open (amber, a slit), half shut
    # (dazed); hotter as the fight goes on.
    ex, ey = B(0.15, -1.4)
    pen.oval(ex, ey, 1.0, 1.25, c["hollow"], n=18)
    if act == "still" or (stun and frame % 2):
        pen.lines([(ex - 0.7, ey + 0.1), (ex, ey + 0.3), (ex + 0.7, ey + 0.1)], 0.22, c["lid"])
    else:
        hot = c["eye_hot"] if look >= 1 and not still else c["eye"]
        rv = 0.45 if stun else 0.85
        pen.oval(ex, ey, 0.72, rv, hot, edge=False, n=16)
        look_u = 0.2 if not stun else 0.0
        pen.oval(ex + look_u, ey, 0.16, rv * 0.8, c["pupil"], edge=False, n=10)
        pen.dot(ex - 0.3, ey - 0.35, 0.14, c["glow"])
    # The near arm, in front: long, with twig fingers.
    if still:
        near = [B(0.7, -0.8), B(3.2, -3.9), B(4.2, -6.5)]
    elif act == "sweep":               # (drawn right back over its shoulder)
        near = [B(0.7, -0.4), B(-1.6, -3.4), B(-4.4, -4.6)]
    elif act == "swing":               # (lashed out in front)
        near = [B(0.7, -0.2), B(3.8, -0.6), B(6.6, 0.2)]
    elif act == "cast":
        near = [B(0.7, -0.8), B(3.6, -3.4), B(5.6, -5.8)]
    elif charge:
        near = [B(0.7, 0.0), B(2.8, 1.2), B(5.2, 0.8)]
    elif stun:
        near = [B(0.7, 0.2), B(2.2, 2.8), B(2.6, 5.6)]
    else:
        near = [B(0.7, 0.0), B(3.3, 1.4), B(4.8, 3.8)]
    pen.lines(near, 0.55, c["bark"], edge=True)
    _twigs(pen, c, near[-1], near[-2], c["twig"])


def _twigs(pen: Pen, c, tip, before, color) -> None:
    """Three twig fingers spreading from the end of a branch-arm."""
    a = math.atan2(tip[1] - before[1], tip[0] - before[0])
    for k in (-0.6, 0.0, 0.6):
        pen.line(tip, (tip[0] + math.cos(a + k) * 1.2, tip[1] + math.sin(a + k) * 1.2), 0.16,
                 color)


# --- Mycelium: the fly agaric (M26.1) ---------------------------------------------------


def paint_amanita(pen: Pen, frame: int, pose: str) -> None:
    """Mycelium, the fly agaric: a huge toadstool -- a wide red cap (its
    white warts are drawn over it by render/amanita.py: each is a body that
    can be shot off), a pale stem with a frilly ring, a bulb at the base,
    and root-threads it waddles on. Its face is only two eyes glowing in
    the shadow of its gills.

    `pose` is "<look>:<action>"; the look (0, 1, 2: its phase) adds purple
    mycelium veins up its stem, then a torn cap and red eyes. Actions: ""
    (waddling), "hop" (stretched, up), "slam" (squashed flat), "spin" (its
    cap tilted like a blade), "drink" (threads glowing into the ground, its
    eyes shut), "puff" (pores open, spores rising), "stun"."""
    c = palette.AMANITA
    pen.edge = c["edge"]
    look, _, act = pose.partition(":")
    look = int(look or 0)
    sx, sy = {"hop": (0.9, 1.08), "slam": (1.15, 0.82)}.get(act, (1.0, 1.0))

    def T(u, v):
        return u * sx, 6.5 - (6.5 - v) * sy

    tilt = 0.4 * math.sin(frame * math.pi / 2 + 0.6) + 0.15 if act == "spin" else 0.0

    def C(u, v):                       # (the cap: tilted when it spins)
        u0, v0 = 0.0, -3.6
        du, dv = u - u0, v - v0
        ca, sa = math.cos(tilt), math.sin(tilt)
        return T(u0 + du * ca - dv * sa, v0 + du * sa + dv * ca)

    pen.shadow(0.0, 8.6, 5.8 * sx, 1.2)
    # Root-threads: wiggling as it waddles; glowing into the ground as it drinks.
    for k, u in enumerate((-2.2, -1.1, 0.0, 1.1, 2.2)):
        sway = 0.0 if act in ("drink", "slam") else 0.4 * math.sin(frame * math.pi / 2 + k * 1.3)
        tip = (u * 1.5 + sway, 8.5 if act != "hop" else 8.0)
        col = c["vein"] if act == "drink" else c["thread"]
        pen.lines([T(u * 0.7, 6.8), T(u * 1.1 + sway * 0.5, 7.7), T(*tip)], 0.24, col, edge=True)
    # The bulb and the stem.
    pen.oval(*T(0.0, 6.2), 2.6 * sx, 1.5 * sy, c["bulb"])
    stem = [T(-1.6, 6.0), T(1.6, 6.0), T(1.25, 1.5), T(1.3, -3.4), T(-1.3, -3.4), T(-1.25, 1.5)]
    pen.poly(stem, c["stem"])
    pen.poly([T(-1.6, 6.0), T(-0.6, 6.0), T(-0.5, -3.4), T(-1.3, -3.4), T(-1.25, 1.5)],
             c["stem_shade"], edge=False)
    if look >= 1:                      # (mycelium veins up its stem)
        pen.lines([T(0.4, 5.6), T(-0.2, 3.6), T(0.5, 1.8), T(0.0, -0.6)], 0.14, c["vein"])
        pen.lines([T(-0.9, 5.2), T(-0.6, 3.0), T(-1.0, 1.4)], 0.12, c["vein"])
    # The ring (skirt), frilly.
    skirt = [T(-1.4, -1.4), T(1.4, -1.4)]
    for k in range(9):
        u = 2.5 - k * 5.0 / 8
        skirt.append(T(u, 0.6 if k % 2 == 0 else 0.15))
    pen.poly(skirt, c["skirt"])
    # The gills' shadow under the cap, and its eyes in it.
    pen.poly([C(-5.6, -3.6), C(5.6, -3.6), C(3.6, -2.4), C(-3.6, -2.4)], c["gills_dark"])
    for k in range(9):
        u = -4.4 + k * 1.1
        pen.line(C(u, -3.5), C(u * 0.75, -2.55), 0.1, c["gills"])
    shut = act in ("drink",) or (act == "stun" and frame % 2)
    for u in (-1.1, 1.1):
        ex, ey = C(u, -2.95)
        if shut:
            pen.line((ex - 0.35, ey), (ex + 0.35, ey), 0.14, c["eye"])
        else:
            pen.oval(ex, ey, 0.55, 0.42, c["eye_red"] if look >= 2 else c["eye"], edge=False, n=12)
            pen.dot(ex + 0.12, ey - 0.08, 0.13, c["pore"])
    # The cap: a wide red dome, a pale rim, a highlight.
    dome = []
    for k in range(17):
        t = math.pi + k * math.pi / 16
        dome.append((math.cos(t) * 6.6, -3.7 + math.sin(t) * 5.0))
    if look >= 2:                      # (torn: a bite out of its rim)
        dome[2] = (dome[2][0] + 0.6, dome[2][1] + 0.9)
        dome[3] = (dome[3][0] + 0.2, dome[3][1] + 1.3)
    pen.poly([C(u, v) for u, v in dome], c["cap"])
    pen.poly([C(u, v) for u, v in dome[:5]] + [C(-4.4, -3.7)], c["cap_dark"], edge=False)
    pen.lines([C(-6.4, -3.7), C(0.0, -3.4), C(6.4, -3.7)], 0.28, c["cap_rim"])
    pen.oval(*C(-2.2, -7.0), 1.8, 0.8, c["cap_hi"], edge=False, n=14, tilt=-0.3)
    if act == "puff":                  # (pores open: spores rising)
        for k in range(6):
            u = -4.0 + k * 1.6
            rise = (frame + k) % 4 * 0.5
            pen.dot(*C(u, -8.2 - rise + abs(u) * 0.45), 0.22, c["pore"])


# --- Mycelium: the shaggy ink cap, "the Lawyer" (M26.2) -----------------------------------


def paint_inkcap(pen: Pen, frame: int, pose: str) -> None:
    """Mycelium, the shaggy ink cap ("the Lawyer"): a tall white cylinder of
    a cap, all shaggy scales, its hem fraying into black ink that drips as
    it moves; a long thin stem; a gaunt face peering out under the fringe.

    `pose` is "<look>:<action>"; the look (0, 1, 2: its phase) turns more of
    the cap to ink, from the hem up. Actions: "" (stalking), "melt"
    (slumping into its ink), "rear" (tilted back, about to fling), "write"
    (leaning in, an ink tendril reaching to the ground), "shake" (its cap
    shaking, scales flying), "sink" (half gone into the ground)."""
    c = palette.INKCAP
    pen.edge = c["edge"]
    look, _, act = pose.partition(":")
    look = int(look or 0)
    sx, sy = {"melt": (1.35, 0.55), "sink": (1.1, 0.7)}.get(act, (1.0, 1.0))
    lean = {"write": 0.45, "rear": -0.3}.get(act, 0.0)
    jig = 0.25 * math.sin(frame * math.pi) if act == "shake" else 0.0
    sway = 0.2 * math.sin(frame * math.pi / 2)

    def T(u, v):                       # (squashed toward the ground, leaning)
        v2 = 8.0 - (8.0 - v) * sy
        return u * sx + lean * (8.0 - v2) * 0.35 + (jig if v < 0 else 0.0), v2

    pen.shadow(0.0, 8.6, 3.8 * sx, 1.0)
    # Ink pooled round its foot (more as it melts).
    pool = 1.2 + look * 0.5 + (2.0 if act in ("melt", "sink") else 0.0)
    pen.oval(0.0, 8.2, pool, pool * 0.3, c["ink"], n=20)
    # The stem: long and thin, a little bulb at the foot.
    pen.oval(*T(0.0, 7.6), 1.2 * sx, 0.6, c["base"])
    pen.poly([T(-0.8 + sway * 0.3, 7.4), T(0.8 + sway * 0.3, 7.4), T(0.7, 0.0), T(-0.7, 0.0)],
             c["stem"])
    pen.poly([T(-0.8 + sway * 0.3, 7.4), T(-0.3, 7.4), T(-0.3, 0.0), T(-0.7, 0.0)],
             c["stem_shade"], edge=False)
    # The cap: a tall shaggy cylinder, rounded on top, its hem in ink.
    cap = [T(-3.3, -0.4), T(-3.4, -3.0), T(-3.1, -6.0), T(-2.4, -8.3), T(-1.2, -9.3),
           T(0.0, -9.5), T(1.2, -9.3), T(2.4, -8.3), T(3.1, -6.0), T(3.4, -3.0), T(3.3, -0.4)]
    pen.poly(cap + [T(0.0, -0.2)], c["cap"])
    pen.poly([T(-3.3, -0.4), T(-3.4, -3.0), T(-3.1, -6.0), T(-2.4, -8.3), T(-1.6, -8.9),
              T(-1.9, -6.0), T(-2.2, -3.0), T(-2.0, -0.4)], c["cap_shade"], edge=False)
    # Shaggy scales, in staggered rows.
    for row in range(6):
        v = -8.4 + row * 1.35
        w = 2.9 if row else 2.0
        for k in range(4 + (row % 2)):
            u = -w + (k + (0.5 if row % 2 else 0.0)) * (2 * w / (3.5 + row % 2))
            if abs(u) > 3.0:
                continue
            pen.lines([T(u - 0.35, v), T(u, v + 0.45), T(u + 0.35, v)], 0.16,
                      c["scale_dark"] if (row + k) % 2 else c["scale"])
    # The hem melting into ink, higher each phase, dripping.
    top = -0.4 - (0.7, 2.6, 4.6)[min(look, 2)]
    ink = [T(-3.3, -0.4), T(-3.35, top + 0.3), T(-1.8, top), T(-0.6, top + 0.4), T(0.8, top - 0.1),
           T(2.2, top + 0.3), T(3.35, top), T(3.3, -0.4)]
    pen.edge = c["ink_hi"]             # (a pale rim, so the ink shows on dark ground)
    pen.poly(ink, c["ink"])
    pen.edge = c["edge"]
    pen.lines([T(-3.0, top + 0.5), T(-1.4, top + 0.2), T(0.4, top + 0.5), T(2.6, top + 0.2)],
              0.12, c["ink_hi"])
    for k, u in enumerate((-2.8, -1.7, -0.6, 0.5, 1.6, 2.8)):
        drip = 0.6 + ((frame + k * 3) % 4) * 0.35 + look * 0.3
        pen.lines([T(u, -0.5), T(u + 0.05, -0.5 + drip)], 0.32, c["ink"], edge=False)
        pen.dot(*T(u + 0.05, -0.4 + drip), 0.22, c["ink"])
    # The face, gaunt, peering out under the fringe.
    pen.oval(*T(0.15, 0.9), 1.25, 0.85, c["face"], n=14)
    for u in (-0.35, 0.6):
        pen.oval(*T(u, 0.75), 0.26, 0.2, c["eye"], edge=False, n=8)
    pen.line(T(-0.25, 1.3), T(0.55, 1.35), 0.1, c["mouth"])
    if act == "write":                 # (an ink tendril, its pen)
        pen.lines([T(2.8, -0.6), T(4.6, 2.0), T(5.6, 5.4), T(6.0, 8.0)], 0.3, c["ink"], edge=True)
        pen.dot(6.0, 8.0, 0.35, c["ink_hi"])
    if act == "shake":                 # (scales flying off)
        for k in range(5):
            a = frame * 0.9 + k * 1.3
            pen.dot(math.cos(a) * 4.6, -4.5 + math.sin(a) * 3.4, 0.2, c["scale"])


# --- Mycelium: the giant puffball (M26.3) ------------------------------------------------


def paint_puffball(pen: Pen, frame: int, pose: str) -> None:
    """Mycelium, the giant puffball: a huge round white ball, smooth and
    lumpy, with a crack of a mouth and two little dark eyes.

    `pose` is "<look>:<action>"; the look (0, 1, 2: its phase) cracks it
    open, olive-brown spore dust showing through (and puffing out, in the
    last). Actions: "" (wobbling), "squash" (flat, about to spring), "air"
    (stretched, mid-leap), "roll" (its face turning round as it rolls;
    `frame` is how far round), "breath" (puffed up, mouth open), "split"
    (pinched in two), "dizzy" (staggered, eyes crossed)."""
    c = palette.PUFFBALL
    pen.edge = c["edge"]
    look, _, act = pose.partition(":")
    look = int(look or 0)
    wob = 0.04 * math.sin(frame * math.pi / 2)
    sx, sy = {"squash": (1.3, 0.62), "air": (0.9, 1.12), "breath": (1.08, 1.08)}.get(
        act, (1.0 + wob, 1.0 - wob))
    cy0 = 7.4 - 6.0 * sy                            # (it sits on the ground)
    pen.shadow(0.0, 8.0, 5.6 * sx, 1.1)

    def ball(u0: float, r: float, seed: float) -> list:
        pts = []
        for k in range(30):
            t = k * math.tau / 30
            rr = r * (1 + 0.04 * math.sin(5 * t + seed) + 0.025 * math.sin(9 * t + seed * 2))
            pts.append((u0 + math.cos(t) * rr * sx, cy0 + math.sin(t) * rr * sy))
        return pts

    if act == "split":                              # (pinched in two)
        for u0 in (-2.6, 2.6):
            pen.poly(ball(u0, 4.0, u0), c["skin"])
            pen.oval(u0 + 0.8, cy0 + 1.4, 2.2, 1.6, c["skin_shade"], edge=False, n=16)
            pen.oval(u0 - 1.3, cy0 - 1.8, 1.0, 0.6, c["skin_hi"], edge=False, n=12)
        return
    pen.poly(ball(0.0, 6.0, 0.0), c["skin_shade"])
    pen.poly([(u * 0.9 - 0.5, (v - cy0) * 0.88 + cy0 - 0.55) for u, v in ball(0.0, 6.0, 0.0)],
             c["skin"], edge=False)
    pen.oval(-2.2 * sx, cy0 - 3.0 * sy, 1.8, 1.0, c["skin_hi"], edge=False, n=16, tilt=-0.4)
    for u, v in ((-3.0, 1.0), (2.6, -2.4), (1.0, 3.2), (-1.4, -4.0)):
        pen.dot(u * sx, cy0 + v * sy, 0.25, c["skin_dark"])
    # Cracks, olive dust showing through.
    if look >= 1:
        for (u0, v0), (u1, v1), (u2, v2) in (((-4.6, -2.2), (-3.2, -1.2), (-2.6, -2.6)),
                                             ((3.8, 1.6), (2.4, 2.4), (2.0, 1.0))):
            pts = [(u0 * sx, cy0 + v0 * sy), (u1 * sx, cy0 + v1 * sy), (u2 * sx, cy0 + v2 * sy)]
            pen.poly(pts, c["dust"], edge=False)
            pen.lines(pts, 0.14, c["crack"])
    if look >= 2:
        for (u0, v0), (u1, v1), (u2, v2) in (((-1.0, -5.6), (0.6, -4.4), (1.8, -5.4)),
                                             ((-4.8, 2.8), (-3.6, 4.2), (-2.2, 3.4))):
            pts = [(u0 * sx, cy0 + v0 * sy), (u1 * sx, cy0 + v1 * sy), (u2 * sx, cy0 + v2 * sy)]
            pen.poly(pts, c["dust"], edge=False)
            pen.lines(pts, 0.16, c["crack"])
        for k in range(4):
            rise = ((frame + k) % 4) * 0.6
            pen.dot((-2.0 + k * 1.3) * sx, cy0 - 6.4 * sy - rise, 0.3 + 0.08 * k, c["dust_hi"])
    # The face (it turns round as it rolls).
    turn = (frame % 4) * 1.4 - 2.1 if act == "roll" else 0.0
    fu = turn * sx
    for u in (-1.3, 1.3):
        ex, ey = (u + fu) * sx, cy0 + 0.2 * sy
        if abs(u + fu) > 4.6:
            continue
        if act == "dizzy":
            pen.line((ex - 0.35, ey - 0.35), (ex + 0.35, ey + 0.35), 0.14, c["eye"])
            pen.line((ex - 0.35, ey + 0.35), (ex + 0.35, ey - 0.35), 0.14, c["eye"])
        else:
            pen.oval(ex, ey, 0.42, 0.55, c["eye"], edge=False, n=10)
            pen.dot(ex - 0.12, ey - 0.18, 0.12, c["shine"])
    if abs(fu) < 3.5:
        my = cy0 + 2.1 * sy
        if act == "breath":
            pen.oval(fu * sx, my, 0.9, 0.8, c["mouth"], n=14)
        else:
            pen.lines([((-1.6 + fu) * sx, my), ((-0.8 + fu) * sx, my + 0.35), (fu * sx, my - 0.1),
                       ((0.8 + fu) * sx, my + 0.35), ((1.6 + fu) * sx, my)], 0.16, c["mouth"])
    if act == "dizzy":
        for k in range(3):
            a = frame * 0.8 + k * math.tau / 3
            pen.dot(math.cos(a) * 3.0, cy0 - 7.2 + math.sin(a) * 0.8, 0.28, c["dust_hi"])


# --- The plains boss: More than Life / More than Death (M27) ---------------------------


def paint_necro(pen: Pen, frame: int, pose: str) -> None:
    """More than Life, the necromancer: tall and gaunt in a tattered
    black-and-violet robe, a pointed cowl hiding all but two green
    eye-lights, a necklace of little bones, a staff topped with a horned
    skull and a scythe's blade. As More than Death (the lich): the same robe
    in rags, floating, a bare skull crowned in green flame, ribs showing,
    the staff cracked and blazing.

    `pose` is "<life|lich>:<action>". Actions: "" (walking / floating),
    "cast" (staff raised, the other hand glowing), "gaze" (staff thrust
    forward, eyes blazing), "reap" (the scythe swept forward), "raise" (both
    arms up), "ritual" (fallen to his knees, the soul tearing free)."""
    c = palette.NECROMANCER
    pen.edge = c["edge"]
    life, _, act = pose.partition(":")
    lich = life == "lich"
    bob = (0.35 * math.sin(frame * math.pi / 2)) if lich else _bob(frame) * 0.6
    sway = 0.3 * math.sin(frame * math.pi / 2)
    kneel = 1.6 if act == "ritual" else 0.0
    if not lich:
        pen.shadow(0.0, 8.7, 4.4, 1.0)
    else:
        pen.oval(0.0, 8.9, 3.4, 0.8, (60, 255, 120, 40), edge=False)
    up = -1.0 if lich else 0.0                     # (the lich floats)
    dv = bob + up + kneel

    # The staff (behind the far arm when walking; in hand).
    if act == "cast" or act == "raise":
        sb, st = (3.0, 2.0 + dv), (4.2, -10.6 + dv)
    elif act == "gaze":
        sb, st = (-1.0, -2.0 + dv), (6.8, -4.4 + dv)
    elif act == "reap":
        sb, st = (-2.4, 1.2 + dv), (6.6, -1.6 + dv)
    elif act == "ritual":
        sb, st = (3.6, 8.4), (5.6, -4.0)
    else:
        sb, st = (3.4, 8.0 + dv * 0.3), (3.0, -9.2 + dv)
    pen.lines([sb, st], 0.32, c["staff"], edge=True)
    if lich:                                       # (cracked, blazing)
        pen.line(((sb[0] + st[0]) / 2, (sb[1] + st[1]) / 2),
                 ((sb[0] + st[0]) / 2 + 0.3, (sb[1] + st[1]) / 2 - 1.2), 0.12, c["flame"])
    ang = math.atan2(st[1] - sb[1], st[0] - sb[0])
    # The scythe's blade, curving off below the skull.
    bx, by = st[0] - math.cos(ang) * 0.9, st[1] - math.sin(ang) * 0.9
    side = ang + math.pi / 2
    blade = [(bx, by), (bx + math.cos(side) * 1.6 + math.cos(ang) * 0.4,
                        by + math.sin(side) * 1.6 + math.sin(ang) * 0.4),
             (bx + math.cos(side) * 3.4 - math.cos(ang) * 1.4,
              by + math.sin(side) * 3.4 - math.sin(ang) * 1.4),
             (bx + math.cos(side) * 1.4 - math.cos(ang) * 0.3,
              by + math.sin(side) * 1.4 - math.sin(ang) * 0.3)]
    pen.poly(blade, c["blade"])
    # The horned skull on top.
    pen.oval(*st, 0.9, 0.8, c["bone"])
    for k in (-1, 1):
        pen.lines([(st[0] + k * 0.6, st[1] - 0.4), (st[0] + k * 1.3, st[1] - 1.3),
                   (st[0] + k * 1.0, st[1] - 2.0)], 0.2, c["bone_dark"])
    pen.dot(st[0] - 0.3, st[1], 0.18, c["eye"])
    pen.dot(st[0] + 0.3, st[1], 0.18, c["eye"])
    if act in ("cast", "gaze", "raise") or lich:
        pen.oval(*st, 1.5, 1.4, (120, 255, 150, 90), edge=False)

    # The robe: long, flaring, ragged (in tatters for the lich).
    top = -3.0 + dv
    hem = 7.6 + (0 if not lich else -0.4) + (kneel * -0.6)
    robe = [(-2.2, top), (2.2, top), (3.9 + sway * 0.3, hem)]
    n = 7
    for k in range(n + 1):
        u = 3.9 - k * 7.8 / n + sway * 0.3
        deep = (1.4 if lich else 0.6) if k % 2 else 0.0
        robe.append((u, hem + deep))
    robe.append((-3.9 + sway * 0.3, hem))
    pen.poly(robe, c["robe"])
    pen.poly([(-2.2, top), (-0.6, top), (-1.2, hem), (-3.9 + sway * 0.3, hem)], c["robe_dark"],
             edge=False)
    pen.line((0.0, top + 0.4), (0.2, hem - 0.3), 0.14, c["trim"])
    if lich:                                       # (ribs through the rags)
        for k in range(4):
            v = top + 1.2 + k * 0.7
            pen.lines([(-1.1, v), (0.0, v + 0.25), (1.1, v)], 0.16, c["bone"])
        pen.line((0.0, top + 1.0), (0.0, top + 4.0), 0.18, c["bone_dark"])
    else:                                          # (a necklace of little bones)
        for k in range(5):
            u = -1.4 + k * 0.7
            pen.oval(u, top + 0.9 + abs(u) * -0.25, 0.22, 0.3, c["bone"], n=8)
    # Arms: sleeves, bony hands.
    if act in ("cast", "raise"):
        near = [(1.6, top + 0.6), (2.7, top - 1.8), (3.0, top - 4.2)]
        far = [(-1.6, top + 0.6), (-2.8, top - 1.6), (-3.4 if act == "raise" else -3.0,
                                                       top - 3.8)]
    elif act == "gaze":
        near = [(1.6, top + 0.6), (2.8, top + 0.4), (4.0, top + 0.6)]
        far = [(-1.6, top + 0.6), (-2.6, top + 1.8), (-2.4, top + 3.2)]
    elif act == "reap":
        near = [(1.6, top + 0.6), (3.0, top + 1.6), (4.4, top + 2.0)]
        far = [(-1.6, top + 0.6), (-2.4, top + 2.2), (-1.4, top + 3.4)]
    elif act == "ritual":
        near = [(1.6, top + 0.6), (2.8, top + 3.0), (3.4, top + 5.4)]
        far = [(-1.6, top + 0.6), (-2.8, top + 3.0), (-2.6, top + 5.4)]
    else:
        near = [(1.6, top + 0.6), (2.6, top + 3.0), (3.2, top + 5.6 + sway * 0.2)]
        far = [(-1.6, top + 0.6), (-2.5, top + 3.0), (-2.2, top + 5.4 - sway * 0.2)]
    for arm in (far, near):
        pen.lines(arm, 0.75, c["robe"] if arm is near else c["robe_dark"], edge=True)
        hx, hy = arm[-1]
        for k in (-0.5, 0.0, 0.5):
            pen.line((hx, hy), (hx + 0.5 * math.cos(k - 1.2), hy - 0.6), 0.1, c["bone"])
        if act in ("cast", "raise") and arm is far:
            pen.oval(hx, hy - 0.6, 0.8, 0.8, (120, 255, 150, 140), edge=False)
    # The head: a pointed cowl round a dark face -- or a bare flaming skull.
    hv = top - 2.2
    if lich:
        for k in range(5):                         # (green flame crown)
            u = -1.4 + k * 0.7
            tall = 1.6 + ((frame + k) % 3) * 0.5
            pen.poly([(u - 0.35, hv - 0.8), (u + 0.1, hv - 0.8 - tall), (u + 0.4, hv - 0.8)],
                     c["flame"], edge=False)
            pen.poly([(u - 0.15, hv - 0.8), (u + 0.1, hv - 0.8 - tall * 0.55), (u + 0.25, hv - 0.8)],
                     c["flame_hi"], edge=False)
        pen.oval(0.0, hv, 1.5, 1.6, c["bone"])
        pen.oval(0.1, hv + 1.2, 0.9, 0.6, c["bone_dark"])
        for u in (-0.55, 0.6):
            pen.oval(u, hv - 0.1, 0.45, 0.4, c["face"], edge=False, n=10)
            pen.dot(u, hv - 0.1, 0.18, c["eye_hot"])
        pen.line((-0.4, hv + 1.3), (0.6, hv + 1.3), 0.08, c["face"])
    else:
        pen.poly([(-2.0, top + 0.4), (-1.9, hv - 0.4), (-0.6, hv - 2.4), (0.4, hv - 2.8),
                  (1.6, hv - 1.2), (2.0, top + 0.4)], c["hood"])
        pen.oval(0.1, hv + 0.2, 1.1, 1.3, c["face"], edge=False, n=14)
        glow = c["eye_hot"] if act in ("gaze", "cast") else c["eye"]
        for u in (-0.4, 0.5):
            pen.oval(u, hv + 0.05, 0.22, 0.14, glow, edge=False, n=8)
        if act == "gaze":
            for u in (-0.4, 0.5):
                pen.line((u, hv + 0.05), (u + 1.6, hv + 0.05), 0.12, c["glow"])


@dataclass(frozen=True)
class Figure:
    paint: Callable[[Pen, int, str], None]
    reach: float              # art units from the centre the figure may reach


PAINTED: dict[str, Figure] = {
    "snow_king": Figure(paint_hermit, 13.5),
    "fragile": Figure(paint_fragile, 13.0),
    "fragile_wolf": Figure(paint_wolf, 10.5),
    "fragile_crying": Figure(paint_fragile_sitting, 9.5),
    "fragile_hugging": Figure(lambda pen, frame, pose: paint_fragile_sitting(pen, frame, "hug"),
                              9.5),
    "mr_buttons": Figure(paint_bear_figure, 6.5),
    "nettle": Figure(paint_nettle, 11.5),
    "love_cuddles": Figure(paint_love, 12.0),
    "the_fallen": Figure(paint_fallen, 12.0),
    "mycelium_amanita": Figure(paint_amanita, 12.0),
    "mycelium_inkcap": Figure(paint_inkcap, 12.0),
    "mycelium_puffball": Figure(paint_puffball, 12.0),
    "necromancer": Figure(paint_necro, 14.5),
}


def painter(name: str, scale: float, flip: bool, frame: int, hurt: bool, pose: str = ""):
    """The SpriteBank painter for one frame of a painted figure."""
    fig = PAINTED[name]

    def paint(surf, to_px):
        fig.paint(Pen(surf, to_px, scale, flip, hurt), frame, pose)
    return paint
