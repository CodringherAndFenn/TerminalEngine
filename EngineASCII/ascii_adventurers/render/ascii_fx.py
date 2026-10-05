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
from .glyphs import NOTE, images_for, loot_glyph, note_glyph

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
    "wisp": ("*", (".", "."), palette.SHOT_WISP),
    "acid": ("o", (".", ","), palette.SHOT_ACID),
    "spore": ("o", (".", "."), palette.SHOT_SPORE),
    "bomb": ("@", (None, None), None),       # lobbed: drawn by _draw_lobbed
    "sand": ("*", (".", "."), palette.SHOT_SAND),
    "axe": (None, (".", "."), palette.SHOT_AXE),    # head: spins (AXE_SPIN)
    "ember": ("*", ("'", "."), palette.SHOT_EMBER),  # Fire Wand
    "bone": ("o", (".", "."), palette.SHOT_BONE),    # Bone Turret
    # M17: quest enemies and bosses.
    "wobble": ("@", (".", "."), palette.SHOT_WOBBLE),     # psychedelic frog
    "tadpole": ("@", (",", "."), palette.SHOT_TADPOLE),  # Froggy's tadpoles (tail behind)
    "bubble": ("O", (".", "."), palette.SHOT_BUBBLE),
    "ripple": ("o", (".", "."), palette.SHOT_RIPPLE),
    "psy": ("@", (".", "."), "psy"),          # colors: palette.PSY_SHOTS by p.tint
    # M19
    "note": (NOTE, ("'", "."), palette.SHOT_NOTE),   # Sheet Music (a painted glyph)
    # M20
    "dart": ("*", ("+", "."), palette.SHOT_DART),    # the wizard's arcane missiles
    # M22
    "blood": ("o", (".", "."), palette.SHOT_BLOOD),  # the leech swarm's drops
    # M22.2: Lady Proboscia's needles and the buzz rings' sound pulses.
    "needle": ("+", ("-", "."), palette.SHOT_NEEDLE),
    "buzz": ("z", (".", "."), palette.SHOT_BUZZ),
    # M23.1: Khepri's kicked sand, his dust storm, and his ball's clods.
    "sand": (":", (".", "."), palette.SHOT_SAND),
    "dust": ("%", (".", "."), palette.SHOT_DUST),
    "clod": ("o", (".", "."), palette.SHOT_CLOD),
}
# A thrown axe's head turns through these glyphs, one step every
# AXE_SPIN_TILES of flight (so faster throws spin faster).
AXE_SPIN = "/-\\|"
AXE_SPIN_TILES = 0.35
BOMB_ARC_PX = 46          # how high a lobbed bomb flies at the top of its arc


def _draw_lobbed(batch, camera: Camera, p: Projectile) -> None:
    """A bomb in the air: its shadow on the ground, the bomb above it on
    an arc (highest half way), and a ring on the ground where it'll land --
    blinking faster as it comes down."""
    f = p.travelled / p.flight if p.flight > 0 else 1.0
    gx, gy = camera.world_to_px(p.x, p.y)
    batch.put_c(gx, gy, ".", palette.BOMB_SHADOW)
    height = 4 * BOMB_ARC_PX * f * (1 - f)
    batch.put_c(gx, gy - height, "@", palette.BOMB)
    batch.put_c(gx + 4, gy - height - 10, "'", palette.BOMB_FUSE)
    tx, ty = camera.world_to_px(*p.target)
    blink = int(p.travelled * (4 + 10 * f)) % 2 == 0
    color = palette.BOMB_MARK[0 if blink else 1]
    r = p.spec.blast_radius
    for dx, dy, glyph, _ in _ring(10, 1.0, ".", color):
        batch.put_c(tx + dx * r * config.TILE_PX_W, ty + dy * r * config.TILE_PX_H, glyph, color)
    batch.put_c(tx, ty, "x", color)


def draw_projectiles(text: TextRenderer, camera: Camera, projectiles: list[Projectile]) -> None:
    note_glyph(text)                         # (registered once per renderer)
    batch = _Batch(text)
    for p in projectiles:
        if p.spec.lob:
            _draw_lobbed(batch, camera, p)
            continue
        head, trail, cols = SHOT_LOOKS[p.spec.look]
        if cols is None:                     # the rainbow: one color per pellet
            cols = palette.RAINBOW_SHOTS[p.variant % len(palette.RAINBOW_SHOTS)]
        elif cols == "psy":                  # psychedelic: each shot its own hue
            cols = palette.PSY_SHOTS[p.tint % len(palette.PSY_SHOTS)]
        elif p.tint and p.owner is not None and getattr(p.owner, "psychedelic", False):
            cols = palette.PSY_SHOTS[p.tint % len(palette.PSY_SHOTS)]
        head_col, trail_cols = cols
        octant = _octant(p.angle)
        # Trail: only along the stretch the shot has actually flown.
        for k, dist in enumerate(TRAIL_TILES):
            if p.travelled >= dist:
                x, y = camera.world_to_px(p.x - p.dir_x * dist, p.y - p.dir_y * dist)
                batch.put_c(x, y, trail[k] or _LINE[octant], trail_cols[k])
        x, y = camera.world_to_px(p.x, p.y)
        if p.spec.look == "axe":
            head = AXE_SPIN[int(p.travelled / AXE_SPIN_TILES) % len(AXE_SPIN)]
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
    if e.kind == "nova":
        r = e.size * (0.2 + 0.8 * p)
        col = palette.NOVA[min(2, int(p * 3))]
        n = 24
        return [(math.cos(k * math.tau / n) * r * config.TILE_PX_W,
                 math.sin(k * math.tau / n) * r * config.TILE_PX_H,
                 "*" if k % 3 == 0 else ".", col) for k in range(n)]
    if e.kind == "rune_burst":
        r = e.size * (0.3 + 0.7 * p)
        col = palette.RUNE[min(1, int(p * 2))]
        return [(math.cos(k * math.tau / 12) * r * config.TILE_PX_W,
                 math.sin(k * math.tau / 12) * r * config.TILE_PX_H,
                 "+" if k % 2 else "x", col) for k in range(12)] + [(0, 0, "#", col)]
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
    if e.kind == "roll_dust":
        col = palette.ROLL_DUST[0 if p < 0.5 else 1]
        return ([(-5, 0, "o", col), (5, 2, ".", col), (0, -3, ",", col)] if p < 0.5
                else [(-7, 2, ".", col), (7, 0, ".", col)])
    if e.kind == "blink":
        r = max(0.6, e.size) * (0.3 + 0.7 * p)
        col = palette.BLINK[min(1, int(p * 2))]
        n = 10 if e.size <= 1.0 else 18
        return [(math.cos(k * math.tau / n) * r * config.TILE_PX_W,
                 math.sin(k * math.tau / n) * r * config.TILE_PX_H,
                 "*" if k % 2 else "+", col) for k in range(n)]
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
            # Floats up and fades: bright, then a dimmer shade. Crits and
            # status damage have their own colors; a crit gets a "!".
            colors = palette.NUMBER_PLAYER if e.player else \
                palette.NUMBER_TONES.get(e.tone, palette.NUMBER_ENEMY)
            label = f"-{e.value}!" if e.tone == "crit" else f"-{e.value}"
            batch.put_c(x, y - 20 - 26 * e.progress, label,
                        colors[0] if e.progress < 0.6 else colors[1])
            continue
        if e.kind == "loot":
            # Pops up off the body, then arcs into the hero (wherever
            # they've gone) and is gone.
            f = e.progress
            hx, hy = (camera.world_to_px(e.target.x, e.target.y) if e.target is not None
                      else (x, y - 40))
            ease = f * f
            lx, ly = x + (hx - x) * ease, y + (hy - y) * ease - 36 * math.sin(math.pi * f)
            batch.put_c(lx, ly, loot_glyph(text), palette.LOOT)
            if f < 0.5:
                batch.put_c(x, y - 26 - 30 * f, f"+{e.value}", palette.LOOT_TEXT)
            continue
        if e.kind == "toast":
            batch.put_c(x, y - 60 - 24 * e.progress, e.label,
                        palette.TOAST if e.progress < 0.75 else palette.TOAST_DIM)
            continue
        if e.kind == "evade":
            batch.put_c(x, y - 20 - 20 * e.progress, "evade", palette.EVADE)
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


def draw_searchlight(text: TextRenderer, camera: Camera, w) -> None:
    """A sentry wisp's light: a thin cone of dots from the wisp, brighter
    (':') while it's on its target -- that's when it fires fast."""
    half = math.radians(config.WISP_CONE_DEG) / 2
    reach = config.WISP_LIGHT_RANGE
    color = palette.WISP_LIGHT_HOT if w.lit else palette.WISP_LIGHT
    glyph = ":" if w.lit else "."
    batch = _Batch(text)
    for side in (-1.0, 0.0, 1.0):
        a = w.light + side * half
        n = 7 if side else 5
        for k in range(1, n + 1):
            d = reach * k / n
            x, y = camera.world_to_px(w.x + math.cos(a) * d, w.y + math.sin(a) * d)
            batch.put_c(x, y, glyph, color)
    batch.flush()


def draw_boar_tell(text: TextRenderer, camera: Camera, b) -> None:
    """Scraping: dust kicked up behind it and dots along the line it's
    about to charge. Charging: speed streaks behind. Dazed: stars over it."""
    batch = _Batch(text)
    ca, sa = math.cos(b.facing), math.sin(b.facing)
    if b.state == "scrape":
        for k in range(1, 9):                     # the charge line
            x, y = camera.world_to_px(b.x + ca * k * 1.4, b.y + sa * k * 1.4)
            batch.put_c(x, y, ".", palette.BOAR_EYE)
        flick = int(b.timer * 20) % 2
        for dv in (-0.5, 0.5):
            x, y = camera.world_to_px(b.x - ca * 1.2 - sa * dv, b.y - sa * 1.2 + ca * dv)
            batch.put_c(x, y, "," if flick else ".", palette.SCRAPE_DUST[flick])
    elif b.state == "charge":
        glyph = _LINE[_octant(b.facing)]
        for k in (1.3, 2.0):
            x, y = camera.world_to_px(b.x - ca * k, b.y - sa * k)
            batch.put_c(x, y, glyph, palette.SCRAPE_DUST[0 if k < 1.5 else 1])
    elif b.state == "dazed":
        x, y = camera.world_to_px(b.x, b.y)
        spin = b.timer * 6
        for k in range(3):
            a = spin + k * math.tau / 3
            batch.put_c(x + math.cos(a) * 12, y - 26 + math.sin(a) * 4, "*", palette.DAZE)
    batch.flush()


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
