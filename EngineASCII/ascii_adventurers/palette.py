"""
palette.py -- AsciiAdventurers' colors.

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

# --- Characters (render/characters.py) ------------------------------------------
# One letter per pixel in the pixel art; "." is transparent.

SPRITE_COLORS = {
    "k": (22, 18, 28),      # outline
    "s": (236, 192, 152),   # skin
    "S": (196, 150, 112),   # skin shade
    "w": (232, 232, 238),   # white
    "b": (70, 92, 200), "B": (44, 56, 138),          # wizard blue
    "y": (244, 204, 64), "Y": (180, 140, 30),        # gold
    "o": (150, 235, 255), "O": (80, 170, 230),       # magic glow
    "t": (136, 88, 46), "T": (92, 58, 30),           # wood
    "m": (182, 188, 202), "M": (112, 118, 134),      # steel / stone
    "r": (206, 52, 52), "R": (140, 30, 36),          # red
    "g": (70, 150, 70), "G": (40, 96, 46),           # green
    "p": (244, 132, 188), "P": (190, 80, 140),       # pink
    "h": (116, 72, 40), "H": (244, 214, 112),        # hair brown / blonde, leather
    "v": (140, 70, 170), "V": (96, 44, 120),         # violet
    "e": (150, 132, 96), "E": (110, 95, 66),         # ogre hide
}
# Creature sprites (warrior, worm) flash this for a moment when hit.
HIT_FLASH = (255, 235, 220)

# --- Enemies -----------------------------------------------------------------------

BEAM = (255, 70, 70)               # warlock aiming beam
BEAM_DIM = (170, 40, 40)
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

# --- Shots & effects (render/ascii_fx.py) ------------------------------------------
# Everything that flies or pops up is font glyphs. Fixed shades only (see
# the glyph-cache note at the top of this file).

# Shots: (head color, trail colors nearest -> farthest).
SHOT_BOLT = ((215, 245, 255), ((120, 200, 255), (70, 130, 210)))
SHOT_ARROW = ((190, 195, 210), ((150, 100, 55), (110, 72, 40)))
SHOT_HEX = ((230, 130, 255), ((160, 80, 210), (100, 50, 140)))
SHOT_ORB = ((255, 140, 205), ((200, 80, 150), (130, 50, 100)))
SHOT_BOULDER = ((175, 160, 135), ((120, 110, 92), (85, 78, 66)))
FLASH_HOT = (255, 250, 215)
FLASH = (255, 190, 60)
SPARK_HOT = (255, 235, 170)
SPARK = (255, 160, 50)
DEBRIS = (150, 135, 110)
DUST = ((150, 140, 120), (105, 98, 85))
TILE_FLASH_FG = (255, 255, 235)
NUMBER_ENEMY = ((255, 245, 200), (170, 160, 130))    # bright -> faded
NUMBER_PLAYER = ((255, 90, 70), (170, 60, 50))
HP_BAR_FULL = (230, 70, 55)
HP_BAR_EMPTY = (110, 50, 44)

# --- UI ------------------------------------------------------------------------------

RETICLE = colors.AMBER            # ring at the exact mouse point
TILE_MARKER = colors.AMBER_DIM    # corner brackets on the tile under the mouse
RETICLE_SHADOW = (20, 14, 0)      # dark edge so the reticle reads on any terrain
HUD_LABEL = colors.GREEN_DIM
HUD_VALUE = colors.GREEN
HUD_HINT = colors.GREY
HUD_RULE = colors.GREEN_DIM

# --- Maps (minimap and big map) ------------------------------------------------------
# Map pixels are half-block cells (fg = top pixel, bg = bottom), one flat
# color each. Explored land shows each tile type's color; unexplored land
# shows its biome, dimmed. Fixed colors only (glyph-cache note above).

# Biome colors: plain ground on the map, and (dimmed) the unexplored outline.
MAP_BIOME = {
    "plains": (95, 140, 60),
    "forest": (40, 100, 48),
    "desert": (190, 160, 90),
    "ruins": (110, 110, 106),
    "swamp": (86, 98, 50),
    "mushroom": (130, 80, 145),
    "ocean": (24, 52, 100),
}
MAP_DIM = 0.4        # unexplored land: biome color times this
# Explored tiles by TileType name; anything not listed uses its look-alike
# ground color from MAP_BIOME via MAP_TILE_BIOME.
MAP_TILE = {
    "water": MAP_BIOME["ocean"],
    "bog": (40, 80, 70),
    "tree": (30, 85, 36), "pine": (22, 72, 32), "mangrove": (60, 90, 40),
    "giant mushroom": (190, 80, 150), "cactus": (90, 150, 70),
    "rock": (120, 105, 90), "mesa rock": (150, 95, 60),
    "wall": (175, 175, 165), "void": (0, 0, 0),
    "rubble": (135, 125, 110), "splinters": (110, 90, 60),
    "tall grass": (110, 155, 70), "flowers": (120, 150, 70), "dunes": (205, 178, 110),
    "reeds": (105, 120, 55), "spores": (150, 95, 165),
}
MAP_TILE_BIOME = {   # ground-like tiles -> the biome whose color they take
    "ground": "plains", "grass": "plains", "plains": "plains",
    "forest floor": "forest", "sand": "desert", "cactus pulp": "desert",
    "concrete": "ruins", "mud": "swamp", "roots": "swamp",
    "mycelium": "mushroom", "mush": "mushroom",
}
MAP_FRAME = colors.GREEN_DIM
MAP_TITLE = colors.GREEN
MAP_LABEL = (235, 235, 220)
MAP_PLAYER = (255, 255, 255)
MAP_PLAYER_EDGE = (20, 20, 20)

# --- Menus (milestone 8) ------------------------------------------------------------
LOGO = (255, 190, 60)
LOGO_SHADOW = (110, 60, 10)
RECORD = (255, 220, 90)          # NEW RECORD highlights

# --- Hero weapons (milestone 10) -----------------------------------------------------
# (head, (trail near, trail far)) like the SHOT_* colors above.
SHOT_SPARK = ((255, 255, 200), ((150, 235, 255), (80, 170, 235)))
SHOT_LONGARROW = ((240, 242, 250), ((205, 165, 95), (150, 115, 65)))
# The princess's rainbow: one color set per pellet, fan order.
_RAINBOW = ((255, 85, 85), (255, 165, 60), (255, 235, 90), (115, 230, 115), (105, 165, 255))
RAINBOW_SHOTS = tuple(
    (c, (tuple(round(v * 0.72) for v in c), tuple(round(v * 0.45) for v in c))) for c in _RAINBOW
)
ARC = ((240, 252, 255), (140, 225, 255))       # lightning: bright core, cyan
SWING = ((240, 244, 255), (160, 170, 200))     # sword sweep: leading edge, trail
PULSE = ((255, 225, 130), (225, 160, 255), (140, 115, 200))   # bard ring, fading

# --- HUD, corners layout (milestone 11) -----------------------------------------------
HUD_PANEL = (10, 14, 10)            # the dark panels behind HUD text
HUD_HP_GOOD = (90, 220, 110)
HUD_HP_WARN = (235, 190, 60)
HUD_HP_LOW = (235, 70, 60)
HUD_EMPTY = (40, 60, 44)
HUD_XP = (255, 200, 70)
HUD_XP_EMPTY = (70, 58, 30)
HUD_BOSS = (230, 70, 60)
HUD_BOSS_EMPTY = (70, 30, 28)
HUD_BOSS_NAME = (255, 150, 130)
LEVEL_UP = (255, 220, 110)          # "LEVEL UP!" over the hero

# --- Cards (milestone 11) --------------------------------------------------------------
CARD_RARITY = {"common": (185, 185, 175), "rare": (100, 170, 255), "epic": (215, 120, 255)}
CARD_TITLE = (255, 220, 120)
CARD_TEXT = (205, 205, 195)
CARD_KEY = (255, 255, 255)
CARD_TAG = (130, 130, 120)          # "WIZARD" on a hero's own cards
CARD_SELECTED = (255, 210, 90)      # the highlighted card's frame and bars
CARD_BG_SELECTED = (28, 34, 26)
