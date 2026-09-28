"""
ui/death.py -- the overlay shown when the player's tank is destroyed.

A simple framed box over the (still running) world: what happened, how far
you got, and how to go again. The full game-over screen with run stats and
score comes in milestone 5.
"""

from __future__ import annotations

from engine import TextRenderer, colors


def draw_death_overlay(
    text: TextRenderer, cols: int, view_rows: int, distance: float, kills: int,
    seed: int | None, can_restart: bool,
) -> None:
    lines = [
        ("YOUR TANK WAS DESTROYED", colors.RED),
        ("", colors.GREY),
        (f"distance {distance:.0f}    kills {kills}" + (f"    seed {seed}" if seed else ""),
         colors.WHITE),
        ("", colors.GREY),
        ("R or click: new run      ESC: quit" if can_restart else "", colors.AMBER),
    ]
    width = max(len(s) for s, _ in lines) + 6
    height = len(lines) + 2
    left = (cols - width) // 2
    top = (view_rows - height) // 2
    text.put(left, top, "┌" + "─" * (width - 2) + "┐", colors.RED)
    for i, (s, c) in enumerate(lines):
        row = top + 1 + i
        text.put(left, row, "│" + " " * (width - 2) + "│", colors.RED)
        text.put(left + (width - len(s)) // 2, row, s, c)
    text.put(left, top + height - 1, "└" + "─" * (width - 2) + "┘", colors.RED)
