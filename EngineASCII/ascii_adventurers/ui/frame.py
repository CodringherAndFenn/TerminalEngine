"""
ui/frame.py -- framed boxes and centred text for menus and overlays.
"""

from __future__ import annotations

import pygame

from engine import TextRenderer, colors

from .. import palette


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


def glint(text: TextRenderer, left: int, top: int, width: int, height: int, bg,
          t: float | None = None) -> None:
    """A legendary's frame (M28.3a): starred corners, and a spark running
    round the edge (GLINT_SPEED cells a second, by the wall clock so it
    moves while the game is paused)."""
    if t is None:
        t = pygame.time.get_ticks() / 1000.0
    edge = ([(left + i, top, "─") for i in range(1, width - 1)]
            + [(left + width - 1, top + j, "│") for j in range(1, height - 1)]
            + [(left + width - 2 - i, top + height - 1, "─") for i in range(width - 2)]
            + [(left, top + height - 2 - j, "│") for j in range(height - 2)])
    for col, row in ((left, top), (left + width - 1, top), (left, top + height - 1),
                     (left + width - 1, top + height - 1)):
        text.put(col, row, "*", palette.LEGEND_GLINT[1], bg)
    if not edge:
        return
    head = int(t * GLINT_SPEED) % len(edge)
    for k, shade in enumerate(palette.LEGEND_GLINT):
        col, row, ch = edge[(head - k) % len(edge)]
        text.put(col, row, ch, shade, bg)


GLINT_SPEED = 24.0


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
