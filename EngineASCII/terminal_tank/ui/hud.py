"""
ui/hud.py -- the status bar along the bottom of the screen.

Health bar first (it's what matters in a fight), then kills, where you are
(biome, distance from the start), the gun, the seed and FPS. Score and the
message log arrive with milestone 5.
"""

from __future__ import annotations

import math

from engine import TextRenderer

from .. import config, palette
from ..entities.tank import Tank

HINTS = "WASD/Arrows drive   Mouse aim   Left click fire (hold)   F11 window mode   ESC quit"
HP_BAR_CELLS = 20

# Health bar color by fraction left (fixed shades; see palette note).
_HP_COLORS = ((0.6, (90, 220, 110)), (0.3, (235, 190, 60)), (0.0, (235, 70, 60)))


def draw_hud(
    text: TextRenderer, cols: int, rows: int, tank: Tank, world, spawn: tuple[float, float],
    fps: float, kills: int = 0,
) -> None:
    top = rows - config.HUD_ROWS
    # The smoothly scrolled map can spill partway into these rows; blank
    # them first so only the HUD shows.
    for r in range(top + 1, rows):
        text.put(0, r, " " * cols)
    text.put(0, top, "─" * cols, palette.HUD_RULE)

    # Health bar: block glyphs, color by how much is left.
    frac = max(0.0, tank.hp / tank.max_hp)
    color = next(c for limit, c in _HP_COLORS if frac > limit or limit == 0.0)
    filled = math.ceil(frac * HP_BAR_CELLS) if tank.hp > 0 else 0
    col = 2
    text.put(col, top + 1, "HP", palette.HUD_LABEL)
    col += 3
    text.put(col, top + 1, "█" * filled, color)
    text.put(col + filled, top + 1, "░" * (HP_BAR_CELLS - filled), palette.HUD_RULE)
    col += HP_BAR_CELLS + 1
    text.put(col, top + 1, f"{math.ceil(tank.hp):3d}", color)
    col += 7

    biome_at = getattr(world, "biome_at", None)
    biome = biome_at(math.floor(tank.x), math.floor(tank.y)).name.upper() if biome_at else "TEST MAP"
    dist = math.hypot(tank.x - spawn[0], tank.y - spawn[1])
    fields = [
        ("KILLS", f"{kills:<3d}"),
        ("BIOME", f"{biome:<8}"),
        ("DIST", f"{dist:5.0f}"),
        ("GUN", tank.weapon.spec.name.upper()),
    ]
    seed = getattr(world, "seed", None)
    if seed is not None:
        fields.append(("SEED", str(seed)))
    fields.append(("FPS", f"{fps:3.0f}"))
    for label, value in fields:
        text.put(col, top + 1, label, palette.HUD_LABEL)
        col += len(label) + 1
        text.put(col, top + 1, value, palette.HUD_VALUE)
        col += len(value) + 4

    text.put(2, top + 2, HINTS, palette.HUD_HINT)
