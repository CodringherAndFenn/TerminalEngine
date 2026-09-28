"""
ui/hud.py -- the status bar along the bottom of the screen.

Milestone 1 shows driving/aiming telemetry; health, ammo, score and distance
arrive with milestone 5.
"""

from __future__ import annotations

import math

from engine import TextRenderer

from .. import config, palette
from ..entities.tank import Tank

COMPASS8 = ("E", "SE", "S", "SW", "W", "NW", "N", "NE")

HINTS = "WASD/Arrows drive   Mouse aim   F11 window mode   ESC quit"


def _bearing_deg(angle: float) -> int:
    """World angle -> compass bearing (0 = north, clockwise)."""
    return round(math.degrees(angle) + 90) % 360


def draw_hud(text: TextRenderer, cols: int, rows: int, tank: Tank, fps: float) -> None:
    top = rows - config.HUD_ROWS
    # The smoothly scrolled map can spill partway into these rows; blank
    # them first so only the HUD shows.
    for r in range(top + 1, rows):
        text.put(0, r, " " * cols)
    text.put(0, top, "─" * cols, palette.HUD_RULE)

    fields = [
        ("HULL", f"{COMPASS8[tank.hull_dir8]:<2}"),
        ("TURRET", f"{_bearing_deg(tank.turret_angle):03d}"),
        ("SPEED", f"{tank.speed:+5.1f}"),
        ("POS", f"{tank.x:6.1f},{tank.y:6.1f}"),
        ("FPS", f"{fps:3.0f}"),
    ]
    col = 2
    for label, value in fields:
        text.put(col, top + 1, label, palette.HUD_LABEL)
        col += len(label) + 1
        text.put(col, top + 1, value, palette.HUD_VALUE)
        col += len(value) + 4

    text.put(2, top + 2, HINTS, palette.HUD_HINT)
