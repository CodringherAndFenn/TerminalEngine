"""
text.py -- grid-based text/ASCII rendering, the typewriter effect, and a
minimal fade transition.

TextRenderer draws characters one cell at a time onto the Display's virtual
canvas. Per-cell blitting (rather than rendering whole strings) guarantees
strict grid alignment for box-drawing art, and a glyph cache keeps it cheap:
each (char, fg, bg) combination is rasterized once and reused.
"""

from __future__ import annotations

from pathlib import Path

import pygame

from . import colors
from .display import Display

# --- Procedural box-drawing glyphs ------------------------------------------
#
# Many fonts (including the bundled VT323) ship without the Unicode
# box-drawing and block-element glyphs, and even fonts that have them often
# leave gaps between cells. We therefore *always* synthesize these characters
# ourselves: each one is drawn as rectangles spanning the full cell, so
# borders join seamlessly across the grid regardless of font.
#
# Single-line box chars are described by which "arms" they extend from the
# cell center: U(p), D(own), L(eft), R(ight).
_BOX_ARMS = {
    "─": "LR", "│": "UD",
    "┌": "DR", "┐": "DL", "└": "UR", "┘": "UL",
    "├": "UDR", "┤": "UDL", "┬": "DLR", "┴": "ULR", "┼": "UDLR",
}
# Double-line chars are approximated by their single-line equivalents.
_BOX_ALIASES = {
    "═": "─", "║": "│", "╔": "┌", "╗": "┐", "╚": "└", "╝": "┘",
    "╠": "├", "╣": "┤", "╦": "┬", "╩": "┴", "╬": "┼",
}
# Block elements: fraction of the cell to fill (left, top, width, height in
# cell-relative units), or a dither density for the shade characters.
_BLOCK_RECTS = {
    "█": (0.0, 0.0, 1.0, 1.0),
    "▀": (0.0, 0.0, 1.0, 0.5),
    "▄": (0.0, 0.5, 1.0, 0.5),
    "▌": (0.0, 0.0, 0.5, 1.0),
    "▐": (0.5, 0.0, 0.5, 1.0),
}
_SHADE_DENSITY = {"░": 0.25, "▒": 0.5, "▓": 0.75}

SYNTHESIZED_CHARS = (
    set(_BOX_ARMS) | set(_BOX_ALIASES) | set(_BLOCK_RECTS) | set(_SHADE_DENSITY)
)


class TextRenderer:
    """Draws text on a Display's character grid."""

    def __init__(self, display: Display) -> None:
        self.display = display
        # (char, fg, bg) -> pre-rendered cell Surface. Text in a terminal UI
        # is highly repetitive, so this cache stays small and hot.
        self._glyph_cache: dict[tuple[str, tuple, tuple | None], pygame.Surface] = {}

    # --- Canvas-level operations ----------------------------------------

    def clear(self, color: tuple = colors.BACKGROUND) -> None:
        """Fill the whole virtual canvas with one color."""
        self.display.canvas.fill(color)

    # --- Character / string drawing --------------------------------------

    def _glyph(self, char: str, fg: tuple, bg: tuple | None) -> pygame.Surface:
        key = (char, fg, bg)
        cached = self._glyph_cache.get(key)
        if cached is not None:
            return cached

        cell_w, cell_h = self.display.cell_w, self.display.cell_h
        cell = pygame.Surface((cell_w, cell_h), pygame.SRCALPHA)
        if bg is not None:
            cell.fill(bg)

        if char in SYNTHESIZED_CHARS:
            self._draw_synthetic(cell, char, fg)
        else:
            # antialias=False keeps glyph edges hard, matching the
            # nearest-neighbor canvas scaling.
            rendered = self.display.font.render(char, False, fg)
            # Horizontally centered in case a glyph is narrower than the
            # cell; vertically top-aligned because cell height equals the
            # font's line height.
            cell.blit(rendered, ((cell_w - rendered.get_width()) // 2, 0))

        self._glyph_cache[key] = cell
        return cell

    def _draw_synthetic(self, cell: pygame.Surface, char: str, fg: tuple) -> None:
        """Draw a box-drawing/block character procedurally onto a cell."""
        w, h = cell.get_size()
        char = _BOX_ALIASES.get(char, char)

        if char in _BOX_ARMS:
            # Stroke thickness roughly matching VT323's stems at any size.
            t = max(2, h // 10)
            bar_x = (w - t) // 2  # left edge of the vertical stroke
            bar_y = (h - t) // 2  # top edge of the horizontal stroke
            arms = _BOX_ARMS[char]
            # Each arm runs from its cell edge through the center, so
            # neighboring cells' strokes connect with no gaps.
            if "U" in arms:
                cell.fill(fg, (bar_x, 0, t, bar_y + t))
            if "D" in arms:
                cell.fill(fg, (bar_x, bar_y, t, h - bar_y))
            if "L" in arms:
                cell.fill(fg, (0, bar_y, bar_x + t, t))
            if "R" in arms:
                cell.fill(fg, (bar_x, bar_y, w - bar_x, t))
        elif char in _BLOCK_RECTS:
            fx, fy, fw, fh = _BLOCK_RECTS[char]
            cell.fill(fg, (round(fx * w), round(fy * h), round(fw * w), round(fh * h)))
        elif char in _SHADE_DENSITY:
            # Ordered 2x2 dither: dot positions chosen per density level.
            density = _SHADE_DENSITY[char]
            pattern = {0.25: {(0, 0)}, 0.5: {(0, 0), (1, 1)}, 0.75: {(0, 0), (1, 0), (1, 1)}}[density]
            for y in range(0, h, 2):
                for x in range(0, w, 2):
                    for dx, dy in pattern:
                        if x + dx < w and y + dy < h:
                            cell.set_at((x + dx, y + dy), fg)

    def put(
        self,
        col: int,
        row: int,
        text: str,
        fg: tuple = colors.GREEN,
        bg: tuple | None = colors.BACKGROUND,
    ) -> None:
        """Draw a single-line string starting at grid cell (col, row).

        Characters outside the grid are clipped silently, so callers can
        print near edges without bounds arithmetic. ``bg=None`` draws the
        glyphs over whatever is already in those cells.
        """
        if not (0 <= row < self.display.rows):
            return
        for i, char in enumerate(text):
            c = col + i
            if c < 0:
                continue
            if c >= self.display.cols:
                break
            self.display.canvas.blit(
                self._glyph(char, fg, bg),
                (c * self.display.cell_w, row * self.display.cell_h),
            )

    def put_block(
        self,
        col: int,
        row: int,
        text: str,
        fg: tuple = colors.GREEN,
        bg: tuple | None = colors.BACKGROUND,
    ) -> None:
        """Draw a multi-line string (e.g. ASCII art) with (col, row) as its
        top-left corner. Lines are split on '\\n'."""
        for line_index, line in enumerate(text.splitlines()):
            self.put(col, row + line_index, line, fg, bg)

    def put_block_from_file(
        self,
        col: int,
        row: int,
        path: Path | str,
        fg: tuple = colors.GREEN,
        bg: tuple | None = colors.BACKGROUND,
    ) -> None:
        """Like put_block, but reads the art from a UTF-8 text file."""
        art = Path(path).read_text(encoding="utf-8")
        self.put_block(col, row, art, fg, bg)


class Typewriter:
    """Reveals a (possibly multi-line) string character by character.

    Usage per frame:
        tw.update(dt)        # advance by elapsed seconds
        tw.draw(renderer)    # draw the revealed portion

    ``skip()`` reveals everything at once (for impatient players later).
    Newlines count as instant -- they take a character "slot" of time but
    nothing visible happens, which reads naturally as a tiny line pause.
    """

    def __init__(
        self,
        text: str,
        col: int,
        row: int,
        *,
        fg: tuple = colors.GREEN,
        bg: tuple | None = colors.BACKGROUND,
        chars_per_second: float = 30.0,
    ) -> None:
        self.text = text
        self.col = col
        self.row = row
        self.fg = fg
        self.bg = bg
        self.chars_per_second = chars_per_second
        self._elapsed = 0.0
        self._shown = 0  # number of characters currently revealed

    @property
    def done(self) -> bool:
        return self._shown >= len(self.text)

    def update(self, dt: float) -> None:
        """Advance the reveal by dt seconds."""
        if self.done:
            return
        self._elapsed += dt
        self._shown = min(len(self.text), int(self._elapsed * self.chars_per_second))

    def skip(self) -> None:
        """Reveal the full text immediately."""
        self._shown = len(self.text)

    def reset(self) -> None:
        """Start the reveal over from zero characters."""
        self._elapsed = 0.0
        self._shown = 0

    def draw(self, renderer: TextRenderer) -> None:
        renderer.put_block(self.col, self.row, self.text[: self._shown], self.fg, self.bg)


class Fade:
    """Minimal fade-to-black / fade-from-black overlay for transitions.

    Drives a single alpha value over time; draw() lays a black rectangle of
    that alpha over the whole canvas. Call after all scene drawing, before
    Display.present(). An instant cut is just renderer.clear(colors.BLACK).
    """

    OUT = "out"   # scene -> black (alpha rises 0 -> 255)
    IN = "in"     # black -> scene (alpha falls 255 -> 0)

    def __init__(self, display: Display, duration: float = 0.5) -> None:
        self.display = display
        self.duration = duration
        self._overlay = pygame.Surface(display.canvas.get_size())
        self._overlay.fill(colors.BLACK)
        self._direction: str | None = None
        self._t = 0.0
        self.alpha = 0  # 0 = scene fully visible, 255 = fully black

    @property
    def active(self) -> bool:
        """True while a fade is running."""
        return self._direction is not None

    def start(self, direction: str) -> None:
        """Begin a fade; direction is Fade.OUT or Fade.IN."""
        self._direction = direction
        self._t = 0.0

    def update(self, dt: float) -> None:
        if self._direction is None:
            return
        self._t = min(self._t + dt, self.duration)
        progress = self._t / self.duration if self.duration > 0 else 1.0
        self.alpha = round(255 * progress) if self._direction == Fade.OUT else round(255 * (1.0 - progress))
        if self._t >= self.duration:
            self._direction = None  # hold the final alpha until next start()

    def draw(self) -> None:
        if self.alpha <= 0:
            return
        # The canvas may have been swapped for a different grid size
        # (Display.set_grid); rebuild the overlay to match if so.
        if self._overlay.get_size() != self.display.canvas.get_size():
            self._overlay = pygame.Surface(self.display.canvas.get_size())
            self._overlay.fill(colors.BLACK)
        self._overlay.set_alpha(self.alpha)
        self.display.canvas.blit(self._overlay, (0, 0))
