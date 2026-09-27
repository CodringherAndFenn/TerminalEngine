"""
scenes/common.py -- shared drawing helpers for the menu-style scenes.

Both the menu and settings screens want the same framed look: a single-line
box around the whole grid (drawn with the renderer's synthesized box glyphs, so
it joins seamlessly) plus a centered title. Kept here so the scenes don't
duplicate the border math.
"""

from __future__ import annotations

from engine import TextRenderer, colors


def draw_border(text: TextRenderer, cols: int, rows: int, color: tuple = colors.GREEN_DIM) -> None:
    """Draw a single-line box around the full cols x rows grid."""
    top = "┌" + "─" * (cols - 2) + "┐"
    bottom = "└" + "─" * (cols - 2) + "┘"
    text.put(0, 0, top, color)
    text.put(0, rows - 1, bottom, color)
    for row in range(1, rows - 1):
        text.put(0, row, "│", color)
        text.put(cols - 1, row, "│", color)


def draw_title(text: TextRenderer, cols: int, title: str, row: int, color: tuple = colors.AMBER) -> None:
    """Draw a title centered horizontally on the given row."""
    text.put((cols - len(title)) // 2, row, title, color)


def draw_screen(text: TextRenderer, cols: int, rows: int, title: str) -> None:
    """Clear to the background, draw the border, and place the title."""
    text.clear(colors.BACKGROUND)
    draw_border(text, cols, rows)
    draw_title(text, cols, title, row=2)
