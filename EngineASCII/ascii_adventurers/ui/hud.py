"""
ui/hud.py -- the status bar along the bottom of the screen.

Health bar first (it's what matters in a fight), then kills, where you are
(biome, distance from the start), the hero and their attack, the seed and
FPS (unless hidden in the settings).
"""

from __future__ import annotations

import math

import pygame

from engine import TextRenderer

from .. import config, palette
from ..entities.character import Character

HINTS = "WASD/Arrows walk   Mouse aim   Left click fire (hold)   M map   F11 window mode   ESC pause"
HINTS_SHORT = "WASD walk  Mouse aim  Click fire  M map  F11 window  ESC pause"
HP_BAR_CELLS = 20

# Dropped first when the screen is too narrow for every field, in this order.
_DROPPABLE = ("ATTACK", "HERO", "SEED")

# Health bar color by fraction left (fixed shades; see palette note).
_HP_COLORS = ((0.6, (90, 220, 110)), (0.3, (235, 190, 60)), (0.0, (235, 70, 60)))


# The last HUD drawn, reused while nothing on it changes: key -> image.
_cache: dict = {"key": None, "image": None}


def draw_hud(
    text: TextRenderer, cols: int, rows: int, hero: Character, world, spawn: tuple[float, float],
    fps: float | None, kills: int = 0,
) -> None:
    """fps=None hides the FPS readout (a setting)."""
    top = rows - config.HUD_ROWS
    frac = max(0.0, hero.hp / hero.max_hp)
    color = next(c for limit, c in _HP_COLORS if frac > limit or limit == 0.0)
    filled = math.ceil(frac * HP_BAR_CELLS) if hero.hp > 0 else 0

    biome_at = getattr(world, "biome_at", None)
    biome = biome_at(math.floor(hero.x), math.floor(hero.y)).name.upper() if biome_at else "TEST MAP"
    dist = math.hypot(hero.x - spawn[0], hero.y - spawn[1])
    fields = [
        ("KILLS", f"{kills:<3d}"),
        ("BIOME", f"{biome:<8}"),
        ("DIST", f"{dist:5.0f}"),
        ("HERO", hero.spec.name.upper()),
        ("ATTACK", hero.weapon.spec.name.upper()),
    ]
    seed = getattr(world, "seed", None)
    if seed is not None:
        fields.append(("SEED", str(seed)))
    if fps is not None:
        fields.append(("FPS", f"{fps:3.0f}"))

    # The HUD is ~250 glyphs; redraw it only when something on it changed.
    d = text.display
    area = pygame.Rect(0, top * d.cell_h, cols * d.cell_w, config.HUD_ROWS * d.cell_h)
    key = (id(text), cols, rows, d.cell_w, d.cell_h, filled, color,
           math.ceil(hero.hp), tuple(fields))
    if key == _cache["key"]:
        d.canvas.blit(_cache["image"], area)
        return

    # The smoothly scrolled map can spill partway into these rows; blank
    # them first so only the HUD shows.
    for r in range(top + 1, rows):
        text.put(0, r, " " * cols)
    text.put(0, top, "─" * cols, palette.HUD_RULE)

    # Health bar: block glyphs, color by how much is left.
    col = 2
    text.put(col, top + 1, "HP", palette.HUD_LABEL)
    col += 3
    text.put(col, top + 1, "█" * filled, color)
    text.put(col + filled, top + 1, "░" * (HP_BAR_CELLS - filled), palette.HUD_RULE)
    col += HP_BAR_CELLS + 1
    text.put(col, top + 1, f"{math.ceil(hero.hp):3d}", color)
    col += 7

    # Narrow screens: tighten the gaps, then drop the least useful fields.
    def width(fields, gap):
        return sum(len(label) + 1 + len(value) for label, value in fields) + gap * (len(fields) - 1)
    gap = 4
    while width(fields, gap) > cols - col - 1:
        if gap > 2:
            gap -= 1
        elif any(label in _DROPPABLE for label, _ in fields):
            drop = next(f for f in _DROPPABLE if f in [label for label, _ in fields])
            fields = [f for f in fields if f[0] != drop]
        else:
            break
    for label, value in fields:
        text.put(col, top + 1, label, palette.HUD_LABEL)
        col += len(label) + 1
        text.put(col, top + 1, value, palette.HUD_VALUE)
        col += len(value) + gap

    text.put(2, top + 2, HINTS if len(HINTS) <= cols - 3 else HINTS_SHORT, palette.HUD_HINT)
    _cache["key"], _cache["image"] = key, d.canvas.subsurface(area).copy()
