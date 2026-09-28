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
SPLINTER_FG = (120, 95, 60)
WATER_FG = (70, 140, 220)
WATER_BG = (14, 30, 60)
VOID_FG = (30, 30, 30)
VOID_BG = (0, 0, 0)

# --- Biome terrain (milestone 3) -------------------------------------------------

# Plains
PLAINS_BG = (16, 22, 13)
PLAINS_GRASS = (78, 140, 62)
PLAINS_FLOWER = (190, 175, 90)
# Forest
FOREST_BG = (10, 20, 11)
FOREST_FLOOR = (46, 92, 46)
PINE_FG = (34, 150, 70)
PINE_BG = (8, 30, 14)
# Desert
SAND_BG = (38, 32, 18)
SAND_FG = (150, 128, 80)
DUNE_FG = (190, 165, 105)
CACTUS_FG = (90, 170, 80)
MESA_FG = (170, 110, 70)
MESA_BG = (80, 44, 28)
# Ruins
CONCRETE_BG = (24, 24, 24)
CONCRETE_FG = (95, 95, 92)
# Swamp
MUD_BG = (20, 22, 12)
MUD_FG = (70, 80, 40)
REED_FG = (120, 140, 60)
BOG_FG = (60, 110, 80)
BOG_BG = (14, 34, 26)
MANGROVE_FG = (80, 130, 60)
MANGROVE_BG = (22, 30, 14)
# Mushroom
MYCELIUM_BG = (22, 14, 26)
MYCELIUM_FG = (110, 80, 130)
SPORE_FG = (200, 150, 230)
SHROOM_FG = (230, 110, 170)
SHROOM_BG = (70, 24, 60)

# --- Player tank ------------------------------------------------------------------

TANK_TREAD = (70, 90, 60)
TANK_TREAD_DARK = (40, 52, 34)
TANK_OUTLINE = (14, 20, 12)
TANK_BODY = (120, 190, 90)
TANK_FRONT = (190, 240, 140)   # lighter strip marking the hull's front edge
TANK_TURRET = (165, 220, 125)   # dome, a shade off the barrel so both read
TANK_BARREL = (230, 255, 200)

# Color schemes for every tank-like thing (TankSpec.colors picks one). The
# player is green; enemies are warm/grey so friend and foe read instantly.
TANK_COLORS = {
    "player": dict(tread=TANK_TREAD, tread_dark=TANK_TREAD_DARK, outline=TANK_OUTLINE,
                   body=TANK_BODY, front=TANK_FRONT, turret=TANK_TURRET, barrel=TANK_BARREL),
    "rust": dict(tread=(90, 60, 45), tread_dark=(52, 34, 26), outline=(20, 12, 8),
                 body=(175, 90, 55), front=(225, 140, 90), turret=(200, 110, 70),
                 barrel=(235, 190, 160)),
    "sand": dict(tread=(100, 88, 60), tread_dark=(60, 52, 34), outline=(22, 18, 10),
                 body=(190, 165, 105), front=(230, 210, 150), turret=(170, 145, 90),
                 barrel=(240, 225, 190)),
    "steel": dict(tread=(60, 62, 70), tread_dark=(34, 36, 42), outline=(10, 10, 14),
                  body=(110, 116, 132), front=(170, 176, 196), turret=(130, 136, 152),
                  barrel=(200, 205, 220)),
    "concrete": dict(tread=(80, 80, 76), tread_dark=(50, 50, 48), outline=(16, 16, 14),
                     body=(120, 118, 110), front=(160, 158, 150), turret=(150, 70, 60),
                     barrel=(215, 200, 190)),
    # Blink shown for a moment when anything tank-like takes a hit.
    "hit": dict(tread=(200, 190, 180), tread_dark=(150, 140, 130), outline=(60, 20, 20),
                body=(255, 235, 220), front=(255, 250, 240), turret=(255, 240, 230),
                barrel=(255, 255, 255)),
}

# --- Enemies -----------------------------------------------------------------------

LASER = (255, 60, 60)              # sniper aim line
LASER_DIM = (210, 45, 45)
LASER_CORE = (255, 210, 200)
HP_BAR = (220, 70, 60)
HP_BAR_BG = (60, 20, 18)
BURROW_DUST = ((170, 145, 95), (130, 110, 70))
WORM_BODY = (170, 120, 90)
WORM_DARK = (110, 70, 50)
WORM_MOUTH = (240, 200, 170)
PUFFER_BODY = (200, 140, 220)
PUFFER_SPOTS = (250, 220, 255)
PUFFER_DARK = (110, 60, 130)
SPORE_CLOUD = ((210, 160, 235), (160, 110, 190), (110, 70, 140))
WARRIOR_ARMOR = (150, 150, 165)
WARRIOR_DARK = (70, 70, 84)
WARRIOR_EYES = (255, 90, 60)
WARRIOR_BLADE = (230, 230, 240)
DEATH_FIRE = ((255, 230, 140), (255, 140, 40), (140, 60, 20))

# --- Shells & effects -------------------------------------------------------------
# Fixed shades only (see the glyph-cache note at the top of this file).

SHELL_CORE = (255, 244, 190)
SHELL_GLOW = (255, 165, 40)
TRAIL = ((235, 150, 50), (170, 100, 35), (110, 66, 25))   # nearest -> farthest
FLASH_HOT = (255, 250, 215)
FLASH = (255, 190, 60)
FLASH_EDGE = (220, 110, 30)
SPARK_HOT = (255, 235, 170)
SPARK = (255, 160, 50)
DEBRIS = (150, 135, 110)
DUST = ((150, 140, 120), (105, 98, 85))
TILE_FLASH_FG = (255, 255, 235)

# --- UI ------------------------------------------------------------------------------

RETICLE = colors.AMBER            # ring at the exact mouse point
TILE_MARKER = colors.AMBER_DIM    # corner brackets on the tile under the mouse
RETICLE_SHADOW = (20, 14, 0)      # dark edge so the reticle reads on any terrain
HUD_LABEL = colors.GREEN_DIM
HUD_VALUE = colors.GREEN
HUD_HINT = colors.GREY
HUD_RULE = colors.GREEN_DIM
