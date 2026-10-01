"""
ui/maps.py -- the minimap (top-right corner) and the big map (M key).

Both draw the island the same way:
  * the map is a grid of "map pixels", each covering k x k world tiles and
    colored by the tile at its centre;
  * explored land (world/explored.py: every chunk ever generated) shows each
    tile type's color -- ground, trees, water, walls, rubble...;
  * unexplored land shows its biome from the island layout, dimmed, so the
    island's outline and the biome slices are always visible;
  * each character cell holds two map pixels stacked vertically, drawn with
    the half-block "▀" (foreground = top pixel, background = bottom). A cell
    is 10 x 24 px, so a map pixel is 10 x 12 px -- the same shape as a world
    tile (20 x 24) -- and the island isn't stretched at any zoom.

The player is a small arrow pointing where the hero aims, baked by the
SpriteBank (the font has no arrow characters).

Map pixels are recomputed only when what they show changes (the view moved,
the zoom changed, or new ground was explored); every frame just draws them.
The minimap draws them as one pre-made picture that slides smoothly under
a centred arrow (see Minimap).
"""

from __future__ import annotations

import math

import numpy as np
import pygame

from engine import TextRenderer

from .. import config, palette
from ..render.sprites import SpriteBank
from ..world import biomes
from ..world.explored import MAP_TILES, UNSEEN

# --- Colors: explored classes first, then the dimmed biome outline --------------


def _tile_color(tile) -> tuple:
    if tile.name in palette.MAP_TILE:
        return palette.MAP_TILE[tile.name]
    return palette.MAP_BIOME[palette.MAP_TILE_BIOME[tile.name]]


def _dim(c: tuple) -> tuple:
    return tuple(round(v * palette.MAP_DIM) for v in c)


_COLORS: list[tuple] = [_tile_color(t) for t in MAP_TILES]
_DIM_OFFSET = len(_COLORS)
# The ocean isn't dimmed: explored or not, water is water (so nothing out at
# sea gives itself away before it's found).
_COLORS += [palette.MAP_BIOME["ocean"] if b is biomes.OCEAN else _dim(palette.MAP_BIOME[b.name])
            for b in biomes.BY_ID]


def map_pixels(world, cx: float, cy: float, k: float, w: int, h: int) -> np.ndarray:
    """Color indices (h, w) for a map centred on world point (cx, cy), with
    k tiles per map pixel. Pixel (i, j) shows the tile at
    (cx + (i - w/2 + 0.5) * k, cy + (j - h/2 + 0.5) * k)."""
    xs = cx + (np.arange(w) - w / 2 + 0.5) * k
    ys = cy + (np.arange(h) - h / 2 + 0.5) * k
    txs = np.floor(xs).astype(np.int64)[None, :]
    tys = np.floor(ys).astype(np.int64)[:, None]
    cls = world.explored.sample(txs, tys).astype(np.int64)
    unseen = cls == UNSEEN
    if unseen.any():
        outline = world.layout.biome_ids(txs + 0.5, tys + 0.5, jitter=False).astype(np.int64)
        cls = np.where(unseen, outline + _DIM_OFFSET, cls)
    return cls


def draw_pixels(text: TextRenderer, col0: int, row0: int, idx: np.ndarray) -> None:
    """Draw an (h, w) color-index image (h even) as half-block cells with
    their top-left at grid cell (col0, row0), in runs of equal colors."""
    h, w = idx.shape
    for r in range(h // 2):
        top, bot = idx[2 * r].tolist(), idx[2 * r + 1].tolist()
        start, key = 0, (top[0], bot[0])
        for c in range(1, w + 1):
            nxt = (top[c], bot[c]) if c < w else None
            if nxt != key:
                text.put(col0 + start, row0 + r, "▀" * (c - start),
                         _COLORS[key[0]], _COLORS[key[1]])
                start, key = c, nxt


# --- The player marker ----------------------------------------------------------------


def _paint_arrow(angle: float):
    """A long, narrow triangle pointing along screen angle `angle` (its one
    sharp corner is the tip, so the direction reads at a glance), dark-edged
    so it shows on any map color."""

    def paint(surf, to_px):
        ca, sa = math.cos(angle), math.sin(angle)

        def pt(u, v):
            return to_px(u * ca - v * sa, u * sa + v * ca)

        for color, grow in ((palette.MAP_PLAYER_EDGE, 2.0), (palette.MAP_PLAYER, 0.0)):
            pygame.draw.polygon(surf, color, [pt(9 + grow * 1.5, 0), pt(-6 - grow, 4.5 + grow),
                                              pt(-6 - grow, -4.5 - grow)])

    return paint


def draw_arrow(bank: SpriteBank, world_angle: float, x: float, y: float) -> None:
    sprite = bank.rotated(("map_arrow",), world_angle, 32, _paint_arrow, 12)
    bank.draw(sprite, x, y)


def _paint_mate(color: tuple):
    def paint(surf, to_px):
        cx, cy = to_px(0, 0)
        pygame.draw.circle(surf, palette.MAP_PLAYER_EDGE, (round(cx), round(cy)), 6)
        pygame.draw.circle(surf, color, (round(cx), round(cy)), 4)
    return paint


def draw_mate(bank: SpriteBank, color: tuple, x: float, y: float) -> None:
    """Another player on a map: a dot in their color."""
    bank.draw(bank.static(f"map_mate{color}", _paint_mate(color), 7), x, y)


_PIN_COLORS = {"quest": palette.PIN_QUEST, "lair": palette.PIN_LAIR, "done": palette.PIN_DONE}


def _paint_pin(kind: str):
    """A map pin (M17): a diamond, gold for a quest giver, red for a boss's
    lair, grey once done."""
    fill, edge = _PIN_COLORS[kind]

    def paint(surf, to_px):
        for color, r in ((edge, 7), (fill, 5)):
            pts = [to_px(0, -r), to_px(r, 0), to_px(0, r), to_px(-r, 0)]
            pygame.draw.polygon(surf, color, pts)
    return paint


def draw_pin(bank: SpriteBank, kind: str, x: float, y: float) -> None:
    bank.draw(bank.static(f"map_pin_{kind}", _paint_pin(kind), 8), x, y)


# --- Minimap ------------------------------------------------------------------------


class Minimap:
    """A box in the top-right corner: MINIMAP_COLS x MINIMAP_ROWS cells of
    map around the player, MINIMAP_TILES_PER_PIXEL tiles per map pixel.

    The player's arrow stays in the centre and the map glides under it,
    one canvas pixel at a time (a map pixel is 10 x 12 canvas px for k
    tiles, so one tile walked moves the map ~2 px).

    How: the map pixels are aligned to a fixed grid (multiples of k tiles)
    and rendered, with a one-pixel margin all round, into one picture. That
    picture only changes -- and is only recomputed -- when the player
    crosses into the next map pixel or new ground gets explored. Every frame
    it is blitted, clipped to the box, offset by where exactly the player
    is, so the margin covers the edges as it slides."""

    def __init__(self) -> None:
        self._key = None
        self._pic: pygame.Surface | None = None
        self._frame_key = None
        self._frame: pygame.Surface | None = None

    def _picture(self, world, bx: int, by: int, w: int, h: int, pw: int, ph: int) -> None:
        """Map pixels (bx0 .. bx0 + w + 1) x (by0 .. by0 + h + 1) on the
        fixed grid, as one image, pw x ph canvas px per map pixel."""
        k = config.MINIMAP_TILES_PER_PIXEL
        bx0, by0 = bx - w // 2 - 1, by - h // 2 - 1
        W, H = w + 2, h + 2
        # map_pixels samples pixel i at cx + (i - W/2 + 0.5) * k; this cx
        # puts it at (bx0 + i + 0.5) * k, the centre of grid pixel bx0 + i.
        idx = map_pixels(world, (bx0 + W / 2) * k, (by0 + H / 2) * k, k, W, H)
        rgb = np.asarray(_COLORS, dtype=np.uint8)[idx]          # (H, W, 3)
        small = pygame.surfarray.make_surface(rgb.transpose(1, 0, 2))
        self._pic = pygame.transform.scale(small, (W * pw, H * ph))   # nearest
        self._origin = (bx0, by0)

    def draw(self, text: TextRenderer, bank: SpriteBank, world, x: float, y: float,
             facing: float, others=(), pins=()) -> None:
        """`others`: other players as (x, y, color), drawn as dots when
        they're inside the box. `pins`: quest pins (x, y, kind, label),
        drawn where they are -- or, when they're off the box, on its edge
        in their direction, so you always know which way to go."""
        w, rows = config.MINIMAP_COLS, config.MINIMAP_ROWS
        h, k = rows * 2, config.MINIMAP_TILES_PER_PIXEL
        d = text.display
        cw, ch = d.cell_w, d.cell_h
        pw, ph = cw, ch // 2                            # one map pixel, canvas px
        left = d.cols - w - 2 - config.MINIMAP_MARGIN   # frame's left column
        top = config.MINIMAP_MARGIN_TOP

        # The frame: drawn once per position/size, then blitted back.
        area = pygame.Rect(left * cw, top * ch, (w + 2) * cw, (rows + 2) * ch)
        frame_key = (area.topleft, area.size, id(text))
        if frame_key == self._frame_key:
            d.canvas.blit(self._frame, area)
        else:
            frame = palette.MAP_FRAME
            text.put(left, top, "┌" + "─" * w + "┐", frame)
            for r in range(rows):
                text.put(left, top + 1 + r, "│", frame)
                text.put(left + w + 1, top + 1 + r, "│", frame)
            text.put(left, top + rows + 1, "└" + "─" * w + "┘", frame)
            self._frame = d.canvas.subsurface(area).copy()
            self._frame_key = frame_key

        # The player's map pixel on the fixed grid.
        bx, by = math.floor(x / k), math.floor(y / k)
        key = (bx, by, world.explored.version, pw, ph)
        if key != self._key:
            self._picture(world, bx, by, w, h, pw, ph)
            self._key = key

        # Inside the frame, the player sits at the centre; picture pixel i
        # (grid pixel bx0 + i) lies (bx0 + i - x/k) map pixels from it.
        inner = pygame.Rect((left + 1) * cw, (top + 1) * ch, w * cw, rows * ch)
        mx, my = inner.x + w * pw / 2, inner.y + h * ph / 2
        bx0, by0 = self._origin
        old_clip = d.canvas.get_clip()
        d.canvas.set_clip(inner)
        d.canvas.blit(self._pic, (round(mx + (bx0 - x / k) * pw), round(my + (by0 - y / k) * ph)))
        for ox, oy, color in others:
            px, py = mx + (ox - x) / k * pw, my + (oy - y) / k * ph
            if inner.x + 4 <= px < inner.right - 4 and inner.y + 4 <= py < inner.bottom - 4:
                draw_mate(bank, color, px, py)
        for ox, oy, kind, _ in pins:
            px, py = mx + (ox - x) / k * pw, my + (oy - y) / k * ph
            # Off the box: slide it in along the line from the centre.
            dx, dy = px - mx, py - my
            lim_x, lim_y = inner.width / 2 - 6, inner.height / 2 - 6
            f = max(abs(dx) / lim_x if lim_x else 0.0, abs(dy) / lim_y if lim_y else 0.0, 1.0)
            draw_pin(bank, kind, mx + dx / f, my + dy / f)
        d.canvas.set_clip(old_clip)
        draw_arrow(bank, facing, mx, my)


# --- Big map ------------------------------------------------------------------------


class BigMap:
    """The whole-view map (M). The game is paused while it's open.

    Mouse wheel zooms around the cursor, from the whole island down to
    MAP_MIN_TILES_PER_PIXEL; dragging with the left button or WASD pans;
    C re-centres on the player. Biome names sit on their slices, N/E/S/W on
    the frame, and the title shows how far you are from the island's
    centre."""

    def __init__(self, world) -> None:
        self.world = world
        self.layout = world.layout
        self.is_open = False
        self.cx = self.cy = 0.0
        self.k = 1.0
        self._drag: tuple[float, float] | None = None
        self._key = None
        self._idx: np.ndarray | None = None
        self._size = (1, 2)
        self._labels = self._place_labels()

    # --- Geometry (in map pixels; see map_pixels for the mapping) -----------------

    def _fit_k(self) -> float:
        """Tiles per pixel that shows the whole island."""
        w, h = self._size
        return 2 * self.layout.max_land_radius * 1.04 / min(w, h)

    def _clamp(self) -> None:
        self.k = min(max(self.k, config.MAP_MIN_TILES_PER_PIXEL), self._fit_k())
        lim = self.layout.max_land_radius
        self.cx = min(max(self.cx, -lim), lim)
        self.cy = min(max(self.cy, -lim), lim)

    def _canvas_to_pixel(self, px: float, py: float, cw: int, ch: int) -> tuple[float, float]:
        """Canvas pixel -> map pixel coordinates (fractional)."""
        return px / cw - 1, py / (ch / 2) - 2

    def _pixel_to_world(self, i: float, j: float) -> tuple[float, float]:
        w, h = self._size
        return self.cx + (i - w / 2) * self.k, self.cy + (j - h / 2) * self.k

    def _world_to_canvas(self, x: float, y: float, cw: int, ch: int) -> tuple[float, float]:
        w, h = self._size
        i = (x - self.cx) / self.k + w / 2
        j = (y - self.cy) / self.k + h / 2
        return (1 + i) * cw, ch + j * ch / 2

    def _place_labels(self) -> list[tuple[str, float, float]]:
        """World positions for the biome names: plains at the centre, each
        ring biome half way out along the middle of its slice (nudged along
        the ring until it's really inside that biome, since slice borders
        bend)."""
        lay = self.layout
        out = [("PLAINS", 0.0, -lay.plains_radius * 0.35)]
        n = len(lay.ring)
        r = (lay.plains_radius + lay.radius) / 2
        for i, b in enumerate(lay.ring):
            base = lay.rotation + (i + 0.5) * 2 * math.pi / n
            for d in (0, 0.1, -0.1, 0.2, -0.2, 0.3, -0.3):
                a = base + d
                x, y = r * math.cos(a), r * math.sin(a)
                if lay.biome_at(x, y) is b:
                    break
            out.append((b.name.upper(), x, y))
        return out

    # --- Control -------------------------------------------------------------------

    def open(self, x: float, y: float) -> None:
        self.is_open = True
        self.cx, self.cy = x, y
        self.k = self._fit_k()   # the whole island (re-fitted to the view on draw)
        self._drag = None

    def close(self) -> None:
        self.is_open = False
        self._drag = None

    def handle_event(self, event: pygame.event.Event, canvas_pos, cell_w: int, cell_h: int,
                     player: tuple[float, float]) -> None:
        if event.type == pygame.MOUSEWHEEL and canvas_pos is not None:
            # Zoom around the cursor: the world point under it stays put.
            i, j = self._canvas_to_pixel(*canvas_pos, cell_w, cell_h)
            wx, wy = self._pixel_to_world(i, j)
            self.k *= config.MAP_ZOOM_STEP ** (-event.y)
            self._clamp()
            w, h = self._size
            self.cx = wx - (i - w / 2) * self.k
            self.cy = wy - (j - h / 2) * self.k
            self._clamp()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and canvas_pos:
            self._drag = canvas_pos
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._drag = None
        elif event.type == pygame.MOUSEMOTION and self._drag and canvas_pos:
            dx, dy = canvas_pos[0] - self._drag[0], canvas_pos[1] - self._drag[1]
            self.cx -= dx / cell_w * self.k
            self.cy -= dy / (cell_h / 2) * self.k
            self._drag = canvas_pos
            self._clamp()
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_c:
            self.cx, self.cy = player
            self._clamp()

    def pan(self, ax: float, ay: float, dt: float) -> None:
        """WASD panning, MAP_PAN_SPEED map pixels per second at any zoom."""
        if not (ax or ay):
            return
        step = config.MAP_PAN_SPEED * self.k * dt
        self.cx += ax * step
        self.cy += ay * step
        self._clamp()

    # --- Drawing -------------------------------------------------------------------

    def draw(self, text: TextRenderer, bank: SpriteBank, view_rows: int,
             player: tuple[float, float], facing: float, others=(), pins=(),
             quests=()) -> None:
        """`others`: other players as (x, y, color); `pins`: quest pins (x, y,
        kind, label); `quests`: the quest log's lines (label, text, done),
        listed in the top-left corner."""
        cols = text.display.cols
        cw, ch = text.display.cell_w, text.display.cell_h
        w, rows = cols - 2, view_rows - 2
        if self._size != (w, rows * 2):
            refit = self.k >= self._fit_k()   # was showing the whole island
            self._size = (w, rows * 2)
            if refit:
                self.k = self._fit_k()
        self._clamp()
        key = (self.cx, self.cy, self.k, self._size, self.world.explored.version)
        if key != self._key:
            self._idx = map_pixels(self.world, self.cx, self.cy, self.k, *self._size)
            self._key = key
        draw_pixels(text, 1, 1, self._idx)

        # Frame, compass letters, title and help.
        frame, title = palette.MAP_FRAME, palette.MAP_TITLE
        text.put(0, 0, "┌" + "─" * w + "┐", frame)
        for r in range(rows):
            text.put(0, 1 + r, "│", frame)
            text.put(w + 1, 1 + r, "│", frame)
        text.put(0, rows + 1, "└" + "─" * w + "┘", frame)
        text.put(1 + w // 2, 0, "N", title)
        text.put(1 + w // 2, rows + 1, "S", title)
        text.put(0, 1 + rows // 2, "W", title)
        text.put(w + 1, 1 + rows // 2, "E", title)
        dist = math.hypot(*player)
        text.put(2, 0, f" ISLAND MAP   {dist:.0f} tiles from the centre   "
                       f"zoom {self.k:.0f} tiles/px ", title)
        text.put(2, rows + 1, " wheel/LB/RB zoom   drag, WASD or stick pan   C centre on you   M/ESC close ",
                 title)

        # Biome names (only where the whole name fits inside the frame).
        for name, x, y in self._labels:
            px, py = self._world_to_canvas(x, y, cw, ch)
            col, row = round(px / cw - len(name) / 2), int(py // ch)
            if 1 <= col and col + len(name) <= w + 1 and 1 <= row <= rows:
                text.put(col, row, name, palette.MAP_LABEL, None)

        for ox, oy, kind, label in pins:
            px, py = self._world_to_canvas(ox, oy, cw, ch)
            if cw <= px < (w + 1) * cw and ch <= py < (rows + 1) * ch:
                draw_pin(bank, kind, px, py)
                col, row = round(px / cw - len(label) / 2), int(py // ch) + 1
                if 1 <= col and col + len(label) <= w + 1 and 1 <= row <= rows:
                    text.put(col, row, label, _PIN_COLORS[kind][0], palette.HUD_PANEL)
        if quests:
            width = max(len(f"{a:7} {b}") for a, b, _ in quests) + 2
            text.put(2, 2, " QUESTS".ljust(width), palette.QUEST_TITLE, palette.HUD_PANEL)
            for i, (label, what, done) in enumerate(quests):
                line = f" {label:7} {what}".ljust(width)
                text.put(2, 3 + i, line, palette.QUEST_DONE if done else palette.QUEST_TEXT,
                         palette.HUD_PANEL)

        for ox, oy, color in others:
            px, py = self._world_to_canvas(ox, oy, cw, ch)
            if cw <= px < (w + 1) * cw and ch <= py < (rows + 1) * ch:
                draw_mate(bank, color, px, py)
        px, py = self._world_to_canvas(*player, cw, ch)
        if cw <= px < (w + 1) * cw and ch <= py < (rows + 1) * ch:
            draw_arrow(bank, facing, px, py)
