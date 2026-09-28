"""
engine_ext/screen.py -- size the character grid to the player's screen.

The engine scales its fixed canvas to the window and letterboxes whatever
aspect ratio is left over. With a fixed grid preset that means black bars on
any screen whose shape differs from the preset (e.g. the 21:9 "ultrawide"
grid on a 16:9 laptop). Instead, the game keeps a fixed number of rows (so
text and tiles stay the same size on every screen) and picks the number of
columns that makes the canvas the same shape as the window:

    canvas width / canvas height = window width / window height
    cols * cell_w / (rows * cell_h) = win_w / win_h
    cols = rows * cell_h * win_w / (win_h * cell_w)

rounded to whole cells, so any remaining bar is thinner than one cell.
Uses only public engine API (Display.set_grid) and pygame's window size.
"""

from __future__ import annotations

import pygame

from engine import Display, DisplayMode

from .. import config


def fitted_cols(win_w: int, win_h: int, rows: int, cell_w: int, cell_h: int) -> int:
    """Columns that make a `rows`-tall grid match the window's aspect."""
    cols = round(rows * cell_h * win_w / (win_h * cell_w))
    return max(config.MIN_GRID_COLS, cols)


def fit_grid_to_monitor(display: Display) -> None:
    """Shape the grid like the monitor the window is on (call at startup,
    in any window mode). Borderless/fullscreen then have no bars, and a
    windowed window gets a screen-shaped canvas to size itself to."""
    monitors = display.available_monitors()
    mon_w, mon_h = monitors[min(display.monitor, len(monitors) - 1)]
    rows = config.GRID_ROWS
    display.set_grid(fitted_cols(mon_w, mon_h, rows, display.cell_w, display.cell_h), rows)


def fit_grid_to_window(display: Display) -> bool:
    """Make the canvas fill the window without bars.

    Borderless / fullscreen: the window is the whole screen, so the grid's
    column count is changed to match its shape.

    Windowed: it's the other way round -- the window is sized to the
    canvas's shape (the largest integer multiple of the canvas that fits
    within WINDOW_SCREEN_FRACTION of the monitor, or a smaller fractional
    fit on tiny screens). The grid isn't changed here: the engine's set_grid
    snaps a windowed window back to the canvas's 1:1 size, which would fight
    the player dragging the window edges.

    Returns True if the grid changed.
    """
    if display.mode is DisplayMode.WINDOWED:
        _fit_window_to_canvas(display)
        return False
    surface = pygame.display.get_surface()
    if surface is None:
        return False
    win_w, win_h = surface.get_size()
    rows = config.GRID_ROWS
    cols = fitted_cols(win_w, win_h, rows, display.cell_w, display.cell_h)
    if (cols, rows) == (display.cols, display.rows):
        return False
    display.set_grid(cols, rows)
    return True


def _fit_window_to_canvas(display: Display) -> None:
    monitors = display.available_monitors()
    mon_w, mon_h = monitors[min(display.monitor, len(monitors) - 1)]
    can_w, can_h = display.canvas.get_size()
    room_w = mon_w * config.WINDOW_SCREEN_FRACTION
    room_h = mon_h * config.WINDOW_SCREEN_FRACTION
    fit = min(room_w / can_w, room_h / can_h)
    # Whole-number scales keep every canvas pixel the same size on screen.
    scale = int(fit) if fit >= 1 else fit
    size = (round(can_w * scale), round(can_h * scale))
    surface = pygame.display.get_surface()
    if surface is None or surface.get_size() != size:
        display.set_windowed_resolution(*size)
