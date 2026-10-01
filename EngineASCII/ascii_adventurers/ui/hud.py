"""
ui/hud.py -- the heads-up display ("corners" layout, M11).

No bar across the screen: the world fills it. What's always there sits in
the corners, each on a small dark panel so it reads over any terrain:

  top-left     HP bar, level + XP bar, kills, loot found and the run's
               clock, and
               the hero's spells with their levels (once they have any)
  top-right    the minimap (ui/maps.py)
  top-centre   a boss's name and health, during a boss fight
  bottom-right FPS, when enabled in Settings

Seed, biome, distance, hero and attack moved off the HUD: the pause menu
and the big map show them.

The top-left panel is ~80 glyphs; it's redrawn only when something on it
changes, otherwise its last image is blitted back.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import pygame

from engine import TextRenderer

from .. import palette
from ..render.glyphs import loot_glyph
from ..meta.run_stats import format_time

BAR = 24                 # HP / XP bar cells
PANEL_W = BAR + 9        # "HP " + bar + " 100" + margins

# Health bar color by fraction left.
_HP_COLORS = ((0.6, palette.HUD_HP_GOOD), (0.3, palette.HUD_HP_WARN), (0.0, palette.HUD_HP_LOW))


@dataclass
class HudInfo:
    hp: float
    max_hp: float
    level: int
    xp_frac: float           # progress to the next level, 0..1
    kills: int
    time: float              # seconds into the run
    fps: float | None = None     # None: hidden (a setting)
    boss: tuple[str, float] | None = None   # (name, health fraction) during a boss fight
    spells: tuple = ()           # (HUD label, level) of each spell the hero has
    loot: int = 0                # found this run
    shield: float = 0.0          # Ward Charm / Aegis: shown in blue after the HP


# The last top-left panel drawn: key -> image.
_cache: dict = {"key": None, "image": None}


def _panel(text: TextRenderer, col: int, row: int, width: int, height: int) -> None:
    for r in range(height):
        text.put(col, row + r, " " * width, palette.HUD_PANEL, palette.HUD_PANEL)


def _bar(text: TextRenderer, col: int, row: int, width: int, frac: float, full: tuple,
         empty: tuple, fill: str = "█", rest: str = "░") -> None:
    n = max(0, min(width, round(frac * width)))
    text.put(col, row, fill * n, full, palette.HUD_PANEL)
    text.put(col + n, row, rest * (width - n), empty, palette.HUD_PANEL)


def draw_hud(text: TextRenderer, info: HudInfo) -> None:
    d = text.display
    cols, rows = d.cols, d.rows
    _draw_status(text, info)
    if info.boss is not None:
        draw_boss_bar(text, *info.boss)
    if info.fps is not None:
        s = f"{info.fps:3.0f} FPS"
        text.put(cols - len(s) - 1, rows - 1, s, palette.HUD_LABEL, None)


def _draw_status(text: TextRenderer, info: HudInfo) -> None:
    """The top-left panel: HP, level/XP, kills and clock."""
    d = text.display
    frac = max(0.0, info.hp / info.max_hp) if info.max_hp else 0.0
    hp_color = next(c for limit, c in _HP_COLORS if frac > limit or limit == 0.0)
    hp_cells = math.ceil(frac * BAR) if info.hp > 0 else 0
    shield_cells = min(BAR - hp_cells, math.ceil(info.shield / info.max_hp * BAR)) \
        if info.shield > 0 and info.max_hp else 0
    xp_cells = round(max(0.0, min(1.0, info.xp_frac)) * BAR)
    clock = format_time(info.time)
    rows = 4 if info.spells else 3
    area = pygame.Rect(0, 0, PANEL_W * d.cell_w, rows * d.cell_h)
    key = (id(text), d.cell_w, d.cell_h, hp_cells, hp_color, math.ceil(info.hp),
           info.level, xp_cells, info.kills, clock, info.spells, info.loot, shield_cells)
    if key == _cache["key"]:
        d.canvas.blit(_cache["image"], area)
        return
    _panel(text, 0, 0, PANEL_W, rows)
    text.put(1, 0, "HP", palette.HUD_LABEL, palette.HUD_PANEL)
    text.put(4, 0, "█" * hp_cells, hp_color, palette.HUD_PANEL)
    text.put(4 + hp_cells, 0, "█" * shield_cells, palette.HUD_SHIELD, palette.HUD_PANEL)
    text.put(4 + hp_cells + shield_cells, 0, "░" * (BAR - hp_cells - shield_cells),
             palette.HUD_EMPTY, palette.HUD_PANEL)
    text.put(PANEL_W - 4, 0, f"{math.ceil(max(0.0, info.hp)):3d}", hp_color, palette.HUD_PANEL)
    text.put(1, 1, "LV", palette.HUD_LABEL, palette.HUD_PANEL)
    # XP as a half-height bar: it reads as secondary to HP.
    text.put(4, 1, "▀" * xp_cells, palette.HUD_XP, palette.HUD_PANEL)
    text.put(4 + xp_cells, 1, "▀" * (BAR - xp_cells), palette.HUD_XP_EMPTY, palette.HUD_PANEL)
    text.put(PANEL_W - 4, 1, f"{info.level:3d}", palette.HUD_XP, palette.HUD_PANEL)
    kills = f"KILLS {info.kills}"
    text.put(1, 2, kills, palette.HUD_LABEL, palette.HUD_PANEL)
    text.put(len(kills) + 3, 2, loot_glyph(text) + f" {info.loot}", palette.LOOT_TEXT,
             palette.HUD_PANEL)
    text.put(PANEL_W - 1 - len(clock), 2, clock, palette.HUD_VALUE, palette.HUD_PANEL)
    if info.spells:
        line = "  ".join(f"{name} {level}" for name, level in info.spells)
        text.put(1, 3, line[:PANEL_W - 2], palette.HUD_SPELL, palette.HUD_PANEL)
    _cache["key"], _cache["image"] = key, d.canvas.subsurface(area).copy()


def draw_boss_bar(text: TextRenderer, name: str, frac: float) -> None:
    """A boss's name and health bar, top centre, between the status panel
    and the minimap."""
    from .. import config
    cols = text.display.cols
    room = cols - PANEL_W - (config.MINIMAP_COLS + 2 + config.MINIMAP_MARGIN) - 4
    width = max(10, min(60, room))
    left = PANEL_W + 2 + (room - width) // 2
    label = name.upper()
    text.put(left + (width - len(label)) // 2, 0, label, palette.HUD_BOSS_NAME, None)
    _bar(text, left, 1, width, frac, palette.HUD_BOSS, palette.HUD_BOSS_EMPTY)
