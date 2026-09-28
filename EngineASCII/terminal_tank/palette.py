"""
palette.py -- Terminal Tank's colors.

The engine's `colors` module stays the source for shared UI colors (HUD text,
menus); everything specific to the game world lives here.

Keep the number of distinct colors small and fixed: the engine's glyph cache
is keyed by (char, fg, bg) and never evicts, so computed per-frame colors
(e.g. smooth gradients) would grow it without bound. Effects that fade should
step through a short list of precomputed shades instead.
"""

from engine import colors

BACKGROUND = colors.BACKGROUND

# --- Terrain -------------------------------------------------------------------

GROUND_FG = (70, 82, 60)
GROUND_BG = (16, 20, 14)
GRASS_FG = (60, 130, 60)
TREE_FG = (40, 190, 70)
TREE_BG = (12, 34, 14)
WALL_FG = (150, 150, 140)
WALL_BG = (60, 60, 56)
ROCK_FG = (120, 105, 90)
ROCK_BG = (40, 34, 30)
RUBBLE_FG = (110, 100, 88)
WATER_FG = (70, 140, 220)
WATER_BG = (14, 30, 60)
VOID_FG = (30, 30, 30)
VOID_BG = (0, 0, 0)

# --- Player tank ------------------------------------------------------------------

TANK_TREAD = (70, 90, 60)
TANK_TREAD_DARK = (40, 52, 34)
TANK_OUTLINE = (14, 20, 12)
TANK_BODY = (120, 190, 90)
TANK_FRONT = (190, 240, 140)   # lighter strip marking the hull's front edge
TANK_TURRET = (165, 220, 125)   # dome, a shade off the barrel so both read
TANK_BARREL = (230, 255, 200)

# --- UI ------------------------------------------------------------------------------

RETICLE = colors.AMBER            # ring at the exact mouse point
TILE_MARKER = colors.AMBER_DIM    # corner brackets on the tile under the mouse
RETICLE_SHADOW = (20, 14, 0)      # dark edge so the reticle reads on any terrain
HUD_LABEL = colors.GREEN_DIM
HUD_VALUE = colors.GREEN
HUD_HINT = colors.GREY
HUD_RULE = colors.GREEN_DIM
