"""
render/painted.py -- big figures painted from shapes instead of a pixel
grid: the Snow King (the Frost Hermit), Fragile's three looks (the girl,
the wolf, beaten and crying / hugging her bear) and Mr. Buttons (M24.4),
and Nettle, the Blighted (M25.1).

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
}


def painter(name: str, scale: float, flip: bool, frame: int, hurt: bool, pose: str = ""):
    """The SpriteBank painter for one frame of a painted figure."""
    fig = PAINTED[name]

    def paint(surf, to_px):
        fig.paint(Pen(surf, to_px, scale, flip, hurt), frame, pose)
    return paint
