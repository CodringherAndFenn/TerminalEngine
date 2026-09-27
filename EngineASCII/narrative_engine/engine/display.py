"""
display.py -- window management and the fixed-resolution virtual canvas.

The core idea: all game drawing happens on `Display.canvas`, a pygame
Surface whose pixel size is (cols * cell_w) x (rows * cell_h) and never
changes. Once per frame, `Display.present()` scales that canvas to the real
window with nearest-neighbor filtering, preserving aspect ratio and filling
any leftover space with letterbox/pillarbox bars.

Game code therefore never thinks about window size at all -- it only ever
addresses a fixed character grid.
"""

from __future__ import annotations

import enum
from pathlib import Path

import pygame

from . import colors

# Font bundled with the project (assets/ sits next to engine/).
# Resolved with pathlib so it works identically on Linux and Windows.
ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
DEFAULT_FONT = ASSETS_DIR / "fonts" / "VT323-Regular.ttf"

# Grid presets (cols, rows). With the default font's 10x24px cell:
#   CLASSIC   -> 800x576   (~4:3, the traditional terminal look)
#   WIDE      -> 1280x720  (exactly 16:9, fills 16:9 monitors edge-to-edge)
#   ULTRAWIDE -> 1720x720  (exactly 43:18 -- scales 2x pixel-perfect to a
#                           3440x1440 ultrawide: integer scale, no bars)
# If you change the font or font_size the pixel sizes shift, but the bars
# added by present() keep every grid correct on every screen regardless.
GRID_CLASSIC = (80, 24)
GRID_WIDE = (128, 30)
GRID_ULTRAWIDE = (172, 30)


class DisplayMode(enum.Enum):
    """The three supported window modes, in cycle order."""

    WINDOWED = "windowed"        # resizable OS window
    BORDERLESS = "borderless"    # desktop-sized window, no chrome
    FULLSCREEN = "fullscreen"    # true (exclusive) fullscreen

    def next(self) -> "DisplayMode":
        order = list(DisplayMode)
        return order[(order.index(self) + 1) % len(order)]


class Display:
    """Owns the OS window, the virtual canvas, and the scaling between them.

    Parameters
    ----------
    cols, rows:
        Size of the character grid.
    font_size:
        Pixel size the bundled font is loaded at. Unless overridden, the
        cell size is derived from the font's own metrics at this size, so
        glyphs fill their cells exactly.
    cell_width, cell_height:
        Optional explicit cell size in canvas pixels. Normally left as None.
    font_path:
        Path to a monospace TTF. Defaults to the bundled VT323.
    """

    def __init__(
        self,
        cols: int = 80,
        rows: int = 24,
        *,
        font_size: int = 24,
        cell_width: int | None = None,
        cell_height: int | None = None,
        font_path: Path | str = DEFAULT_FONT,
        title: str = "Narrative Engine",
        monitor: int = 0,
    ) -> None:
        pygame.init()
        pygame.display.set_caption(title)

        self.cols = cols
        self.rows = rows

        # Which physical display the window lives on (index into
        # pygame.display.get_desktop_sizes()). Clamped to what's attached.
        self.monitor = min(monitor, pygame.display.get_num_displays() - 1)

        # The font lives on Display (not TextRenderer) because it defines
        # the cell geometry, and the canvas size depends on that.
        self.font = pygame.font.Font(str(font_path), font_size)

        # Derive cell size from the font: advance width of a glyph, and the
        # font's line height. For a monospace font every glyph has the same
        # advance, so any character works as the probe.
        self.cell_w = cell_width if cell_width is not None else self.font.size("M")[0]
        self.cell_h = cell_height if cell_height is not None else self.font.get_height()

        # The fixed-resolution virtual canvas. All drawing targets this.
        self.canvas = pygame.Surface((cols * self.cell_w, rows * self.cell_h))
        self.canvas.fill(colors.BACKGROUND)

        # Remember the windowed-mode size so cycling back from fullscreen
        # restores what the user had (starts at 1:1 canvas scale).
        self._windowed_size = self.canvas.get_size()

        # Present-transform cache, kept fresh by present() and read back by
        # window_to_cell() for mouse hit-testing. Start at a 1:1, unoffset
        # mapping so hit-testing is valid before the first present().
        self._scale = 1.0
        self._dst_offset = (0, 0)

        self.mode = DisplayMode.WINDOWED
        self._screen = self._apply_mode(self.mode)

    # --- Window mode handling ------------------------------------------

    def _apply_mode(self, mode: DisplayMode) -> pygame.Surface:
        """(Re)create the OS window for the given mode on self.monitor."""
        display = self.monitor
        if mode is DisplayMode.WINDOWED:
            return pygame.display.set_mode(
                self._windowed_size, pygame.RESIZABLE, display=display
            )
        if mode is DisplayMode.BORDERLESS:
            # A frameless window at exactly the desktop resolution: looks
            # like fullscreen but doesn't grab the display mode, so alt-tab
            # stays instant. Use the chosen monitor's own desktop size.
            desktop = pygame.display.get_desktop_sizes()[display]
            return pygame.display.set_mode(desktop, pygame.NOFRAME, display=display)
        # True fullscreen at the current desktop resolution ((0, 0) asks
        # SDL to use the native mode rather than switching resolutions).
        return pygame.display.set_mode((0, 0), pygame.FULLSCREEN, display=display)

    def cycle_mode(self) -> DisplayMode:
        """Switch windowed -> borderless -> fullscreen -> windowed."""
        self.set_mode(self.mode.next())
        return self.mode

    def set_mode(self, mode: DisplayMode) -> None:
        if mode is self.mode:
            return
        # Leaving windowed mode: remember the current size for the trip back.
        if self.mode is DisplayMode.WINDOWED:
            self._windowed_size = self._screen.get_size()
        self.mode = mode
        self._screen = self._apply_mode(mode)

    def set_monitor(self, index: int) -> None:
        """Move the window to a different physical display.

        No-op if the index is out of range or already current. Recreates the
        window in the current mode on the target monitor.
        """
        index = max(0, min(index, pygame.display.get_num_displays() - 1))
        if index == self.monitor:
            return
        self.monitor = index
        self._screen = self._apply_mode(self.mode)

    def set_windowed_resolution(self, width: int, height: int) -> None:
        """Set the size of the OS window used in windowed mode.

        The virtual canvas is untouched -- this only changes how large the
        window is (and thus how much the canvas is scaled up inside it). Takes
        effect immediately in windowed mode; otherwise it's remembered for the
        next return to windowed mode.
        """
        self._windowed_size = (width, height)
        if self.mode is DisplayMode.WINDOWED:
            self._screen = self._apply_mode(self.mode)

    # --- Monitor / resolution enumeration --------------------------------

    @staticmethod
    def available_monitors() -> list[tuple[int, int]]:
        """Desktop pixel size of each attached display, indexed by display."""
        return pygame.display.get_desktop_sizes()

    # A curated set of common 16:9 / 21:9 window sizes. Only those that fit
    # within the target monitor are offered, so the selector stays short.
    _RESOLUTION_CHOICES = [
        (1280, 720), (1600, 900), (1920, 1080), (2560, 1080), (3440, 1440),
    ]

    @classmethod
    def available_resolutions(cls, monitor: int = 0) -> list[tuple[int, int]]:
        """Windowed-mode resolutions that fit on the given monitor.

        Always includes the monitor's own desktop size so the list is never
        empty on unusual displays.
        """
        sizes = pygame.display.get_desktop_sizes()
        dw, dh = sizes[monitor] if monitor < len(sizes) else sizes[0]
        fitting = [(w, h) for (w, h) in cls._RESOLUTION_CHOICES if w <= dw and h <= dh]
        if (dw, dh) not in fitting:
            fitting.append((dw, dh))
        return sorted(set(fitting))

    def handle_event(self, event: pygame.event.Event) -> None:
        """Feed window-related events here from the main loop.

        With a RESIZABLE window, pygame resizes the display surface for us;
        we only track the new size so mode round-trips restore it. Scaling
        itself needs no bookkeeping -- present() measures the window every
        frame.
        """
        if event.type == pygame.VIDEORESIZE and self.mode is DisplayMode.WINDOWED:
            self._windowed_size = (event.w, event.h)

    def set_grid(self, cols: int, rows: int) -> None:
        """Switch to a different character grid (e.g. classic <-> widescreen).

        Rebuilds the virtual canvas at the new size; cell size and font are
        unchanged. The new canvas starts blank, so callers should redraw
        their scene afterwards. In windowed mode the window is resized to
        the new canvas's 1:1 size; other modes just re-letterbox via
        present().
        """
        if (cols, rows) == (self.cols, self.rows):
            return
        self.cols = cols
        self.rows = rows
        self.canvas = pygame.Surface((cols * self.cell_w, rows * self.cell_h))
        self.canvas.fill(colors.BACKGROUND)
        if self.mode is DisplayMode.WINDOWED:
            self._windowed_size = self.canvas.get_size()
            self._screen = self._apply_mode(self.mode)

    # --- Grid helpers ----------------------------------------------------

    def cell_rect(self, col: int, row: int) -> pygame.Rect:
        """Canvas-pixel rect of one grid cell (handy for cursors, boxes)."""
        return pygame.Rect(col * self.cell_w, row * self.cell_h, self.cell_w, self.cell_h)

    def window_to_cell(self, px: int, py: int) -> tuple[int, int] | None:
        """Map an OS-window pixel (e.g. a mouse position) to a grid cell.

        Inverts the transform present() applies: undo the letterbox offset,
        undo the scale, then convert canvas pixels to cell coordinates.
        Returns None when the point lands in a letterbox bar or outside the
        grid -- so callers can treat "no cell" as "clicked nothing".
        """
        if self._scale <= 0:
            return None
        off_x, off_y = self._dst_offset
        cx = (px - off_x) / self._scale
        cy = (py - off_y) / self._scale
        if cx < 0 or cy < 0:
            return None
        col = int(cx // self.cell_w)
        row = int(cy // self.cell_h)
        if 0 <= col < self.cols and 0 <= row < self.rows:
            return (col, row)
        return None

    # --- Per-frame presentation ----------------------------------------

    def present(self) -> None:
        """Scale the canvas to the window and flip.

        Uses the largest scale that fits the window while keeping the
        canvas aspect ratio exact, then centers the result. Leftover space
        becomes solid letterbox/pillarbox bars. pygame.transform.scale is
        nearest-neighbor, so glyph pixels stay hard-edged at any size.
        """
        win_w, win_h = self._screen.get_size()
        can_w, can_h = self.canvas.get_size()

        scale = min(win_w / can_w, win_h / can_h)
        # Never collapse to zero if the window is squashed smaller than one
        # canvas pixel in some dimension.
        dst_w = max(1, int(can_w * scale))
        dst_h = max(1, int(can_h * scale))
        off_x = (win_w - dst_w) // 2
        off_y = (win_h - dst_h) // 2

        # Cache the transform so window_to_cell() can invert it for mouse input.
        self._scale = dst_w / can_w
        self._dst_offset = (off_x, off_y)

        self._screen.fill(colors.LETTERBOX)
        if (dst_w, dst_h) == (can_w, can_h):
            scaled = self.canvas  # 1:1, skip the scale pass
        else:
            scaled = pygame.transform.scale(self.canvas, (dst_w, dst_h))
        self._screen.blit(scaled, (off_x, off_y))
        pygame.display.flip()
