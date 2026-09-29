"""
ui/frame.py -- framed boxes and centred text for menus and overlays.
"""

from __future__ import annotations

import pygame

from engine import TextRenderer, colors


def draw_box(text: TextRenderer, left: int, top: int, width: int, height: int,
             color: tuple = colors.GREEN_DIM, title: str = "",
             title_color: tuple = colors.AMBER) -> None:
    """A single-line frame, cleared inside, with an optional title set into
    the top edge."""
    text.put(left, top, "┌" + "─" * (width - 2) + "┐", color)
    for r in range(top + 1, top + height - 1):
        text.put(left, r, "│" + " " * (width - 2) + "│", color)
    text.put(left, top + height - 1, "└" + "─" * (width - 2) + "┘", color)
    if title:
        label = f" {title} "
        text.put(left + (width - len(label)) // 2, top, label, title_color)


def center(text: TextRenderer, row: int, s: str, fg: tuple, left: int = 0,
           width: int | None = None, bg: tuple | None = colors.BACKGROUND) -> None:
    """Draw `s` centred in columns [left, left + width) (default: the grid)."""
    if width is None:
        width = text.display.cols - left
    text.put(left + (width - len(s)) // 2, row, s, fg, bg)


_shade: dict = {}


def dim_canvas(text: TextRenderer, alpha: int = 150) -> None:
    """Darken everything drawn so far (behind an overlay)."""
    canvas = text.display.canvas
    key = (canvas.get_size(), alpha)
    surf = _shade.get(key)
    if surf is None:
        _shade.clear()
        surf = _shade[key] = pygame.Surface(canvas.get_size())
        surf.fill((0, 0, 0))
        surf.set_alpha(alpha)
    canvas.blit(surf, (0, 0))
