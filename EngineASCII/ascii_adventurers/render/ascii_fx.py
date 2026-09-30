"""
render/ascii_fx.py -- everything that flies or pops up, drawn with font
glyphs: shots, muzzle flashes, impacts, debris, death bursts, spore clouds,
damage numbers, enemy health bars and the warlock's aiming beam.

Characters and creatures are pixel sprites; the action around them is text,
like the terrain. Every glyph is centred on an exact canvas pixel (so shots
move smoothly, not cell by cell) over whatever is underneath, looking just
as the engine's put_px(..., bg=None) would draw it. For speed the strings
come pre-rendered from render/glyphs.py and each draw_* call blits all of
its glyphs in one batch. Only ASCII and the synthesized block glyphs are
used (VT323 has no other symbols -- see CLAUDE.md).

Animated effects are a few fixed frames picked by the effect's progress,
each a list of (dx px, dy px, glyph, color) offsets from its centre, in
fixed palette colors -- so the engine's glyph cache stays bounded.

Directional glyphs (arrow heads and shafts, the slash arc) pick one of 8
characters by the direction's *on-screen* angle: tiles are 20 x 24 px, so
world and screen angles differ slightly.
"""

from __future__ import annotations

import math

from engine import TextRenderer

from .. import config, palette
from ..engine_ext.camera import Camera
from ..entities.effects import Effect
from ..entities.projectile import Projectile
from ..systems.collision import screen_angle
from ..systems.raycast import first_hit
from .glyphs import images_for

# Octant of an on-screen direction: 0 = east, then clockwise (y is down).
_HEAD = (">", "\\", "v", "/", "<", "\\", "^", "/")
_LINE = ("-", "\\", "|", "/", "-", "\\", "|", "/")


def _octant(world_angle: float) -> int:
    return round(screen_angle(world_angle) / (math.pi / 4)) % 8


class _Batch:
    """Glyph strings to draw, blitted together by flush() (in order)."""

    def __init__(self, text: TextRenderer) -> None:
        self.images = images_for(text)
        self.canvas = text.display.canvas
        self.cw, self.ch = text.display.cell_w, text.display.cell_h
        self.blits: list = []

    def put_c(self, x: float, y: float, s: str, color: tuple) -> None:
        """String `s` centred on canvas pixel (x, y), transparent background."""
        self.blits.append((self.images.get(s, color),
                           (round(x - len(s) * self.cw / 2), round(y - self.ch / 2))))

    def put_px(self, x: float, y: float, s: str, fg: tuple, bg: tuple | None) -> None:
        """Like TextRenderer.put_px (top-left at (x, y))."""
        self.blits.append((self.images.get(s, fg, bg), (round(x), round(y))))

    def flush(self) -> None:
        if self.blits:
            self.canvas.fblits(self.blits)
            self.blits = []


# --- Shots ------------------------------------------------------------------------------

# look -> (head glyph or None for "by direction", trail glyphs (None = by
# direction), colors). Trail glyphs sit TRAIL_TILES behind the head.
TRAIL_TILES = (0.45, 0.9)
SHOT_LOOKS = {
    "bolt": ("*", ("o", "."), palette.SHOT_BOLT),
    "arrow": (None, (None, None), palette.SHOT_ARROW),
    "hex": ("%", (":", "."), palette.SHOT_HEX),
    "orb": ("o", (".", "."), palette.SHOT_ORB),
    "boulder": ("O", (".", ","), palette.SHOT_BOULDER),
    "spark": ("*", ("+", "."), palette.SHOT_SPARK),
    "longarrow": (None, (None, None), palette.SHOT_LONGARROW),
    "prism": ("o", (".", "."), None),        # colors: palette.RAINBOW_SHOTS by pellet
}


def draw_projectiles(text: TextRenderer, camera: Camera, projectiles: list[Projectile]) -> None:
    batch = _Batch(text)
    for p in projectiles:
        head, trail, cols = SHOT_LOOKS[p.spec.look]
        if cols is None:                     # the rainbow: one color per pellet
            cols = palette.RAINBOW_SHOTS[p.variant % len(palette.RAINBOW_SHOTS)]
        head_col, trail_cols = cols
        octant = _octant(p.angle)
        # Trail: only along the stretch the shot has actually flown.
        for k, dist in enumerate(TRAIL_TILES):
            if p.travelled >= dist:
                x, y = camera.world_to_px(p.x - p.dir_x * dist, p.y - p.dir_y * dist)
                batch.put_c(x, y, trail[k] or _LINE[octant], trail_cols[k])
        x, y = camera.world_to_px(p.x, p.y)
        batch.put_c(x, y, head or _HEAD[octant], head_col)
    batch.flush()


# --- Effects -------------------------------------------------------------------------------


def _ring(n: int, r: float, glyph: str, color: tuple, turn: float = 0.0,
          squash: float = 1.0) -> list:
    """n glyphs evenly round a circle of radius r px."""
    return [(math.cos(turn + k * math.tau / n) * r, math.sin(turn + k * math.tau / n) * r * squash,
             glyph, color) for k in range(n)]


def _frame(e: Effect) -> list:
    """The glyphs of effect `e` at its current progress."""
    p = e.progress
    if e.kind == "muzzle":
        return [(0, 0, "*", palette.FLASH_HOT)] if p < 0.5 else [(0, 0, "+", palette.FLASH)]
    if e.kind == "impact":
        f = min(2, int(p * 3))
        return ([(0, 0, "*", palette.SPARK_HOT)] + _ring(4, 9, ".", palette.SPARK, 0.4),
                [(0, 0, "+", palette.SPARK)] + _ring(6, 13, ".", palette.DEBRIS, 0.2),
                _ring(3, 8, ".", palette.DUST[1], 1.0))[f]
    if e.kind == "debris":
        f = min(2, int(p * 3))
        return ([(0, 0, "#", palette.DEBRIS)] + _ring(6, 11, ":", palette.DEBRIS),
                _ring(8, 15, ",", palette.DUST[0], 0.3),
                _ring(6, 19, ".", palette.DUST[1], 0.6))[f]
    if e.kind == "fizzle":
        return ([(-3, 0, ".", palette.DUST[0]), (4, 2, ",", palette.DUST[0])]
                if p < 0.5 else [(0, 2, ".", palette.DUST[1])])
    if e.kind == "explosion":
        hot, fire, ember = palette.DEATH_FIRE
        f = min(3, int(p * 4))
        return ([(0, 0, "@", hot)] + _ring(6, 12, "*", fire),
                [(0, 0, "*", fire)] + _ring(8, 18, "*", hot, 0.3),
                _ring(8, 22, "+", ember, 0.1),
                _ring(8, 26, ".", palette.DUST[1], 0.5))[f]
    if e.kind == "slash":
        out = []
        for k in range(5):
            t = e.angle - 1.1 + k * 2.2 / 4
            glyph = _LINE[_octant(t + math.pi / 2)]     # along the arc's tangent
            sx = math.cos(screen_angle(t)) * 18
            sy = math.sin(screen_angle(t)) * 18
            out.append((sx, sy, glyph, palette.WARRIOR_BLADE))
        return out
    if e.kind == "swing":
        return []           # drawn as a picture: render/slash.py
    if e.kind == "pulse":
        r = e.size * (0.25 + 0.75 * p)
        col = palette.PULSE[min(2, int(p * 3))]
        return [(math.cos(k * math.tau / 16) * r * config.TILE_PX_W,
                 math.sin(k * math.tau / 16) * r * config.TILE_PX_H,
                 "*" if k % 2 else "o", col) for k in range(16)]
    if e.kind == "spores":
        f = min(2, int(p * 3))
        r = (18, 34, 48)[f]
        col = palette.SPORE_CLOUD[f]
        return ([(0, 0, "O", col)] + _ring(10, r, "o", col, f * 0.35, 0.8)
                + _ring(6, r * 0.55, ".", col, 0.5, 0.8))
    if e.kind == "eruption":
        f = min(2, int(p * 3))
        r = (14, 26, 38)[f]
        c0, c1 = palette.BURROW_DUST
        return [(dx, dy, ";" if k % 2 else ",", c0 if k % 2 else c1)
                for k, (dx, dy, _, _) in enumerate(_ring(12, r, "", c0, f * 0.2, 0.8))]
    if e.kind == "burrow":
        return [(0, 0, "." if p < 0.5 else ",", palette.BURROW_DUST[0 if p < 0.5 else 1])]
    return []


def draw_effects(text: TextRenderer, camera: Camera, world, effects: list[Effect]) -> None:
    batch = _Batch(text)
    for e in effects:
        if e.kind == "tile_flash":
            # Redraw the hit tile's own glyph in a hot color for a moment.
            tx, ty = int(e.x), int(e.y)
            tile = world.tile_at(tx, ty)
            x, y = camera.tile_to_px(tx, ty)
            batch.put_px(x, y, world.glyph_at(tx, ty), palette.TILE_FLASH_FG, tile.bg)
            continue
        x, y = camera.world_to_px(e.x, e.y)
        if e.kind == "arc":
            _lightning(batch, e, (x, y), camera.world_to_px(e.x2, e.y2))
            continue
        if e.kind == "levelup":
            batch.put_c(x, y - 34 - 22 * e.progress, "LEVEL UP!", palette.LEVEL_UP)
            continue
        if e.kind == "number":
            # Floats up and fades: bright, then a dimmer shade.
            colors = palette.NUMBER_PLAYER if e.player else palette.NUMBER_ENEMY
            batch.put_c(x, y - 20 - 26 * e.progress, f"-{e.value}",
                  colors[0] if e.progress < 0.6 else colors[1])
            continue
        for dx, dy, glyph, color in _frame(e):
            batch.put_c(x + dx, y + dy, glyph, color)
    batch.flush()


def _lightning(batch, e: Effect, start, end) -> None:
    """A jagged bolt between two points: glyphs every ~10 px along the
    line, knocked sideways by alternating amounts that re-roll a few times
    during its short life, so it crackles."""
    (x0, y0), (x1, y1) = start, end
    length = math.hypot(x1 - x0, y1 - y0)
    if length < 1:
        return
    ux, uy = (x1 - x0) / length, (y1 - y0) / length
    glyph = _LINE[round(math.atan2(uy, ux) / (math.pi / 4)) % 8]
    flicker = int(e.t * 60)
    n = max(2, int(length / 10))
    for k in range(n + 1):
        f = k / n
        wobble = 0.0 if k in (0, n) else ((k * 7 + flicker * 3) % 5 - 2) * 2.5
        color = palette.ARC[(k + flicker) % 2]
        batch.put_c(x0 + ux * length * f - uy * wobble, y0 + uy * length * f + ux * wobble,
                    glyph, color)


# --- Enemy tells ----------------------------------------------------------------------------

HP_BAR_CELLS = 4


def draw_hp_bar(text: TextRenderer, x: float, y: float, frac: float) -> None:
    """A small "==--" bar centred on (x, y): filled part bright, rest dim."""
    full = max(1, min(HP_BAR_CELLS, round(frac * HP_BAR_CELLS)))
    s = "=" * full + "-" * (HP_BAR_CELLS - full)
    batch = _Batch(text)
    left = x - HP_BAR_CELLS * batch.cw / 2
    batch.put_px(left, y - batch.ch / 2, s[:full], palette.HP_BAR_FULL, None)
    if full < HP_BAR_CELLS:
        batch.put_px(left + full * batch.cw, y - batch.ch / 2, s[full:], palette.HP_BAR_EMPTY, None)
    batch.flush()


BEAM_STEP_PX = 14


def draw_beam(text: TextRenderer, camera: Camera, world, w) -> None:
    """The warlock's aiming beam: dots from it along its aim, stopping at the
    first wall. Steady while it locks on; in the last third it flickers
    brighter -- the hex is coming."""
    t = w.target
    max_len = w.espec.sight if t is None else math.hypot(t.x - w.x, t.y - w.y) + 3
    ex = w.x + math.cos(w.aim_angle) * max_len
    ey = w.y + math.sin(w.aim_angle) * max_len
    hit = first_hit(world.tile_at, w.x, w.y, ex, ey)
    if hit is not None:
        ex, ey = hit.x, hit.y
    x0, y0 = camera.world_to_px(w.x, w.y)
    x1, y1 = camera.world_to_px(ex, ey)
    length = math.hypot(x1 - x0, y1 - y0)
    if length < 1:
        return
    ux, uy = (x1 - x0) / length, (y1 - y0) / length
    final = w.beam >= w.espec.windup * 0.66
    bright = final and int(w.beam * 14) % 2 == 0
    glyph, color = (":", palette.BEAM) if bright else (".", palette.BEAM if final else palette.BEAM_DIM)
    d = w.spec.hold_px
    batch = _Batch(text)
    while d < length:
        batch.put_c(x0 + ux * d, y0 + uy * d, glyph, color)
        d += BEAM_STEP_PX
    batch.flush()
