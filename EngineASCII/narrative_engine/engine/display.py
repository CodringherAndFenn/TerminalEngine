"""
display.py -- window management and the fixed-resolution virtual canvas.

The core idea: all game drawing happens on `Display.canvas`, a pygame
Surface whose pixel size is (cols * cell_w) x (rows * cell_h) and never
changes. Once per frame, `Display.present()` scales that canvas to the real
window, preserving aspect ratio and filling any leftover space with
letterbox/pillarbox bars.

Two ways to get it on screen (``Display.gpu`` says which is in effect):

  * GPU (the default when there's a hardware renderer): the canvas is
    uploaded to a texture and the graphics chip scales it. At whole-number
    scales (2x, 3x) that's plain nearest-neighbor. At any other scale it is
    "sharp bilinear": nearest-neighbor up to the next whole number (1.5x
    -> 2x, into a render target), then smoothed down to the window. Plain
    nearest-neighbor at 1.5x draws canvas pixels alternately 1 and 2 screen
    pixels wide, so anything thin flickers as it scrolls; sharp bilinear
    gives every canvas pixel the same 1.5 pixels, crisp but for a soft
    half-pixel edge.
  * CPU (headless drivers, no hardware renderer, gpu=False, or the GPU path
    failing): the window's own surface, scaled with nearest-neighbor by
    pygame.transform.scale -- exactly the engine's original path.

Game code therefore never thinks about window size at all -- it only ever
addresses a fixed character grid.
"""

from __future__ import annotations

import enum
import math
import os
import time
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

# SDL_WINDOWPOS_CENTERED_DISPLAY(n) is this OR'd with the display index.
_CENTERED_ON_DISPLAY = 0x2FFF0000
# Video drivers that never have a hardware renderer (tests, CI).
_HEADLESS_DRIVERS = ("dummy", "offscreen")
# A vsync'd present takes a whole refresh (>= ~2.8 ms even at 360 Hz). If
# presents come back faster than this, the driver ignored vsync, and the
# main loop must cap the frame rate itself.
_VSYNC_MIN_GAP = 0.002


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
    vsync:
        Ask for the window to sync presentation to the monitor refresh, so
        every frame is shown exactly once (no doubled/skipped frames, no
        tearing). Off by default. If the platform refuses, the window falls
        back to no vsync; ``self.vsync`` reports what's actually in effect.
    gpu:
        Scale on the graphics chip when there is a hardware renderer (see
        the module docstring); on by default. False keeps the CPU path.
        ``self.gpu`` reports what's actually in effect: False on headless
        drivers, without a hardware renderer, or once the GPU path has
        failed (it then stays on the CPU path for good).
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
        vsync: bool = False,
        gpu: bool = True,
    ) -> None:
        pygame.init()
        pygame.display.set_caption(title)
        self.title = title

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

        # vsync: what was requested, and what the last window actually got
        # (updated by _apply_mode on every window rebuild).
        self._vsync_requested = vsync
        self.vsync = False

        # The GPU path's window, renderer and textures (all None on the CPU
        # path, where self._screen is the window's surface instead).
        self._gpu_requested = gpu
        self.gpu = False
        self._window = None
        self._renderer = None
        self._tex = None          # the canvas, uploaded each frame (nearest)
        self._big = None          # render target: the canvas at k x (smoothed down)
        self._big_k = 0
        self._screen = None

        self.mode = DisplayMode.WINDOWED
        self._screen = self._apply_mode(self.mode)

    # --- Window mode handling ------------------------------------------

    def _apply_mode(self, mode: DisplayMode) -> pygame.Surface | None:
        """(Re)create the OS window for the given mode on self.monitor.

        The GPU path first, if wanted and possible (it returns None: there
        is no window surface); if it fails, the CPU path, now and from then
        on. Requests vsync if enabled; if SDL refuses it for this window,
        retries without so a missing capability never stops the window
        opening.
        """
        if self._gpu_requested and pygame.display.get_driver() not in _HEADLESS_DRIVERS:
            try:
                self._open_gpu(mode)
                self.gpu = True
                return None
            except Exception:              # (pygame.error, or no _sdl2 at all)
                self._close_gpu()
                self._gpu_requested = False
        self.gpu = False
        if self._vsync_requested:
            try:
                screen = self._set_mode(mode, vsync=1)
                self.vsync = True
                return screen
            except pygame.error:
                pass
        self.vsync = False
        return self._set_mode(mode, vsync=0)

    def _set_mode(self, mode: DisplayMode, vsync: int) -> pygame.Surface:
        display = self.monitor
        if mode is DisplayMode.WINDOWED:
            return pygame.display.set_mode(
                self._windowed_size, pygame.RESIZABLE, display=display, vsync=vsync
            )
        if mode is DisplayMode.BORDERLESS:
            # A frameless window at exactly the desktop resolution: looks
            # like fullscreen but doesn't grab the display mode, so alt-tab
            # stays instant. Use the chosen monitor's own desktop size.
            desktop = pygame.display.get_desktop_sizes()[display]
            return pygame.display.set_mode(
                desktop, pygame.NOFRAME, display=display, vsync=vsync
            )
        # True fullscreen at the current desktop resolution ((0, 0) asks
        # SDL to use the native mode rather than switching resolutions).
        return pygame.display.set_mode(
            (0, 0), pygame.FULLSCREEN, display=display, vsync=vsync
        )

    def _open_gpu(self, mode: DisplayMode) -> None:
        """The GPU path's window (the same three modes as _set_mode, on
        self.monitor) with a hardware renderer. Raises if there's none:
        accelerated=1 never settles for SDL's software renderer, which
        would be slower than the CPU path."""
        from pygame._sdl2.video import Renderer

        self._close_gpu()
        desktop = pygame.display.get_desktop_sizes()[self.monitor]
        if mode is DisplayMode.WINDOWED:
            kw = dict(size=self._windowed_size, resizable=True)
        elif mode is DisplayMode.BORDERLESS:
            kw = dict(size=desktop, borderless=True)
        else:
            kw = dict(size=desktop, fullscreen=True)   # exclusive, at the native mode
        self._window = pygame.Window(self.title, position=_CENTERED_ON_DISPLAY | self.monitor, **kw)
        self._renderer = Renderer(self._window, accelerated=1, vsync=self._vsync_requested)
        self.vsync = self._vsync_requested and self._presents_wait()

    def _close_gpu(self) -> None:
        """Drop the GPU path's textures, renderer and window (in that order)."""
        self._tex = self._big = None
        self._big_k = 0
        self._renderer = None
        if self._window is not None:
            self._window.destroy()
            self._window = None
        self.gpu = False

    def _presents_wait(self) -> bool:
        """Whether a present really waits for the monitor (vsync honoured):
        a few blank presents, timed."""
        r = self._renderer
        r.draw_color = (*colors.LETTERBOX, 255)
        stamps = []
        for _ in range(4):
            r.clear()
            r.present()
            stamps.append(time.perf_counter())
        gaps = [b - a for a, b in zip(stamps, stamps[1:])]
        return sum(gaps) / len(gaps) >= _VSYNC_MIN_GAP

    def _texture(self, size: tuple[int, int], smooth: bool, **kw):
        """A texture of the renderer's, filtered nearest or linear. (SDL
        takes a texture's filter from SDL_RENDER_SCALE_QUALITY when it's
        created; the variable is put back afterwards.)"""
        from pygame._sdl2.video import Texture

        old = os.environ.get("SDL_RENDER_SCALE_QUALITY")
        os.environ["SDL_RENDER_SCALE_QUALITY"] = "linear" if smooth else "nearest"
        try:
            return Texture(self._renderer, size, **kw)
        finally:
            if old is None:
                del os.environ["SDL_RENDER_SCALE_QUALITY"]
            else:
                os.environ["SDL_RENDER_SCALE_QUALITY"] = old

    def window_size(self) -> tuple[int, int]:
        """The OS window's size in pixels (on either path)."""
        if self._window is not None:
            return tuple(self._window.size)
        return self._screen.get_size()

    def cycle_mode(self) -> DisplayMode:
        """Switch windowed -> borderless -> fullscreen -> windowed."""
        self.set_mode(self.mode.next())
        return self.mode

    def set_mode(self, mode: DisplayMode) -> None:
        if mode is self.mode:
            return
        # Leaving windowed mode: remember the current size for the trip back.
        if self.mode is DisplayMode.WINDOWED:
            self._windowed_size = self.window_size()
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
        elif event.type == pygame.RENDER_DEVICE_RESET:
            # (GPU path: the graphics device was reset -- Direct3D can, e.g.
            # on alt-tab from fullscreen -- and every texture with it; the
            # next present makes new ones. A lost render target needs
            # nothing: it's redrawn every frame.)
            self._tex = self._big = None
            self._big_k = 0

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

    def window_to_canvas(self, px: int, py: int) -> tuple[float, float] | None:
        """Map an OS-window pixel (e.g. a mouse position) to a canvas pixel,
        keeping sub-cell precision.

        Same inverse transform as window_to_cell(), but the result is left
        as fractional canvas pixels instead of being floored to a cell --
        for anything that needs finer resolution than the grid, such as
        aiming at an exact point. Divide by cell_w / cell_h to get
        fractional grid coordinates. Returns None when the point lands in
        a letterbox bar or outside the canvas.
        """
        if self._scale <= 0:
            return None
        off_x, off_y = self._dst_offset
        cx = (px - off_x) / self._scale
        cy = (py - off_y) / self._scale
        can_w, can_h = self.canvas.get_size()
        if 0 <= cx < can_w and 0 <= cy < can_h:
            return (cx, cy)
        return None

    # --- Per-frame presentation ----------------------------------------

    def present(self) -> None:
        """Scale the canvas to the window and show it.

        Uses the largest scale that fits the window while keeping the
        canvas aspect ratio exact, then centers the result. Leftover space
        becomes solid letterbox/pillarbox bars. On the GPU path the scaling
        is the graphics chip's (sharp bilinear at a fractional scale); on the
        CPU path it's pygame.transform.scale (nearest-neighbor).
        """
        if self.gpu:
            try:
                self._present_gpu()
                return
            except pygame.error:
                # The GPU path broke mid-game: the CPU path from now on.
                self._close_gpu()
                self._gpu_requested = False
                self._screen = self._apply_mode(self.mode)
        self._present_cpu()

    def _fit(self, win_w: int, win_h: int) -> tuple[int, int, int, int]:
        """(dst_w, dst_h, off_x, off_y): the canvas scaled to fit, centered."""
        can_w, can_h = self.canvas.get_size()
        scale = min(win_w / can_w, win_h / can_h)
        # Never collapse to zero if the window is squashed smaller than one
        # canvas pixel in some dimension.
        dst_w = max(1, int(can_w * scale))
        dst_h = max(1, int(can_h * scale))
        return dst_w, dst_h, (win_w - dst_w) // 2, (win_h - dst_h) // 2

    def _present_gpu(self) -> None:
        r = self._renderer
        out_w, out_h = r.get_viewport().size      # (the renderer's pixels)
        if out_w <= 0 or out_h <= 0:
            return                                # (minimized)
        can_w, can_h = self.canvas.get_size()
        dst_w, dst_h, off_x, off_y = self._fit(out_w, out_h)

        # Cache the transform (in window coordinates, which mouse events
        # use -- the same as the renderer's unless the OS scales the window)
        # so window_to_cell() can invert it for mouse input.
        win_w, win_h = self._window.size
        fx, fy = win_w / out_w, win_h / out_h
        self._scale = dst_w / can_w * fx
        self._dst_offset = (off_x * fx, off_y * fy)

        if self._tex is None or (self._tex.width, self._tex.height) != (can_w, can_h):
            self._tex = self._texture((can_w, can_h), smooth=False, streaming=True)
            self._big, self._big_k = None, 0
        self._tex.update(self.canvas)

        # A whole-number scale is exact with nearest-neighbor alone. Any
        # other: nearest-neighbor up to k = the next whole number, then the
        # GPU's bilinear filter down to the window (sharp bilinear).
        k = max(1, math.ceil(dst_w / can_w - 1e-9))
        sharp = (dst_w, dst_h) != (can_w * k, can_h * k)
        if sharp and self._big_k != k:
            self._big = self._texture((can_w * k, can_h * k), smooth=True, target=True)
            self._big_k = k
        if sharp:
            r.target = self._big
            self._tex.draw(dstrect=(0, 0, can_w * k, can_h * k))
            r.target = None
        r.draw_color = (*colors.LETTERBOX, 255)
        r.clear()
        (self._big if sharp else self._tex).draw(dstrect=(off_x, off_y, dst_w, dst_h))
        r.present()

    def _present_cpu(self) -> None:
        win_w, win_h = self._screen.get_size()
        can_w, can_h = self.canvas.get_size()
        dst_w, dst_h, off_x, off_y = self._fit(win_w, win_h)

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
