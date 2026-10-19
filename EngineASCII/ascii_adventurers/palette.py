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
# Haunted forest (M21): cold, desaturated violets and greys.
HAUNT_BG = (14, 12, 20)
HAUNT_LEAF = (78, 66, 84)
HAUNT_FOG = (36, 38, 54)
HAUNT_BARK = (96, 78, 66)
HAUNT_TRUNK = (88, 70, 66)
HAUNT_STUMP = (110, 86, 66)
HAUNT_LOG = (118, 92, 70)
HAUNT_TWIG = (84, 78, 96)
HAUNT_BRANCH = (110, 100, 112)
HAUNT_ROOT = (92, 76, 70)
HAUNT_WISP = ((170, 255, 215), (110, 200, 170), (200, 170, 255))   # floating lights
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
JAVELIN_FG = (196, 160, 100)        # P11: a lizardman's javelin stuck in the mud
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
    "a": (214, 112, 52), "A": (150, 72, 32),         # dwarf's ginger beard
    # P7 (the plains' new enemies)
    "n": (128, 94, 62), "N": (84, 60, 40),           # brown fur, dirt
    "u": (150, 168, 120), "U": (98, 112, 78),        # undead skin
    "c": (64, 62, 74), "C": (38, 36, 46),            # crow / charcoal black
    "l": (226, 196, 110), "L": (170, 140, 64),       # straw
    # P8 (the haunted forest's new enemies)
    "i": (200, 236, 240), "I": (120, 170, 190),      # ghostly pale
    "d": (214, 206, 186), "D": (150, 142, 124),      # old bone
    "f": (255, 196, 80), "F": (230, 110, 40),        # flame, lantern light
    # P12 (the mushroom biome's new enemies; no red-and-white caps: that's Mycelium's)
    "j": (110, 150, 230), "J": (66, 92, 160),        # blue cap
    "q": (110, 190, 160), "Q": (60, 120, 100),       # mold teal
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
    "forest": (72, 62, 96),          # the haunted forest (M21)
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
    "gnarled tree": (50, 40, 46), "branches": (88, 80, 100), "stump": (110, 86, 66),
    "log": (118, 92, 70), "fog": (84, 84, 110),
    "tall grass": (110, 155, 70), "flowers": (120, 150, 70), "dunes": (205, 178, 110),
    "reeds": (105, 120, 55), "spores": (150, 95, 165),
}
MAP_TILE_BIOME = {   # ground-like tiles -> the biome whose color they take
    "ground": "plains", "grass": "plains", "plains": "plains",
    "forest floor": "forest", "dead leaves": "forest", "bark": "forest", "sand": "desert", "cactus pulp": "desert",
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
SHOT_AXE = ((225, 230, 240), ((150, 155, 170), (100, 104, 118)))   # the dwarf's axes
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
# The dodge roll's meter (M18): charging, all charges ready, empty.
HUD_ROLL = (110, 170, 200)
HUD_ROLL_READY = (170, 235, 255)
HUD_ROLL_EMPTY = (30, 48, 58)
LEVEL_UP = (255, 220, 110)          # "LEVEL UP!" over the hero

# --- Cards (milestone 11) --------------------------------------------------------------
CARD_RARITY = {"common": (185, 185, 175), "uncommon": (110, 220, 120), "rare": (100, 170, 255),
               "epic": (215, 120, 255), "legendary": (255, 170, 60)}
CARD_TITLE = (255, 220, 120)
LEGEND_GLINT = ((255, 250, 220), (255, 215, 110), (225, 150, 50))   # M28.3a: a legendary's spark, head first
CARD_TEXT = (205, 205, 195)
CARD_KEY = (255, 255, 255)
CARD_TAG = (130, 130, 120)          # "WIZARD" on a hero's own cards
CARD_SELECTED = (255, 210, 90)      # the highlighted card's frame and bars
CARD_BG_SELECTED = (28, 34, 26)

# --- M12 enemies ------------------------------------------------------------------------
SHOT_WISP = ((235, 250, 255), ((150, 225, 255), (90, 150, 210)))
SHOT_ACID = ((200, 255, 90), ((140, 200, 60), (90, 140, 40)))
SHOT_SPORE = ((240, 190, 255), ((190, 130, 220), (130, 90, 160)))
BOMB = (205, 205, 215)              # the bomb in the air (light: it must show over dark ground)
BOMB_FUSE = (255, 200, 80)
BOMB_SHADOW = (20, 22, 18)
BOMB_MARK = ((255, 90, 70), (170, 50, 40))    # where it will land: bright, dim
WISP_LIGHT = (240, 230, 150)        # the searchlight cone
WISP_LIGHT_HOT = (255, 250, 200)    # ...while it's on you
BOAR_HIDE = (120, 80, 55)
BOAR_DARK = (70, 45, 30)
BOAR_TUSK = (245, 240, 220)
BOAR_EYE = (255, 80, 60)
DAZE = (255, 230, 120)              # stars over a dazed boar
SCRAPE_DUST = ((170, 150, 110), (120, 105, 80))
DEVIL = ((220, 195, 140), (175, 150, 100), (120, 100, 70))   # dust devil: light, mid, dark
SHOT_SAND = ((235, 210, 150), ((190, 165, 115), (140, 120, 85)))

# --- M14: cards 2.0 ----------------------------------------------------------------------
# Damage numbers by tone: crits, and status damage over time (bright -> faded).
NUMBER_TONES = {
    "crit": ((255, 225, 60), (190, 160, 40)),
    "burn": ((255, 140, 50), (180, 95, 35)),
    "poison": ((150, 230, 80), (100, 160, 55)),
    "bleed": ((230, 50, 60), (150, 35, 40)),
}
# Status pips over an enemy, and the frozen / marked looks.
STATUS_PIP = {"burn": (255, 130, 40), "poison": (140, 230, 70), "bleed": (230, 45, 55),
              "chill": (140, 200, 255), "shock": (255, 240, 90)}
FROZEN = ((200, 235, 255), (120, 180, 240))
MARK = (255, 70, 60)
DUEL = (255, 200, 90)              # M28.2i: the Duelist's Wand's duelist, crossed blades
SLEEP = (170, 190, 255)            # M28.2i: "z"s over an enemy Lullabied asleep
EVADE = (190, 230, 255)
SHOT_NOTE = ((255, 225, 120), ((235, 170, 90), (150, 110, 70)))   # Sheet Music's notes
SHOT_DART = ((245, 210, 255), ((200, 120, 255), (120, 70, 190)))  # arcane missiles
# The leech swarm and its mire (M22).
BLOOD_FG = (150, 30, 40)
BLOOD_BG = (60, 8, 14)
CLOT_FG = (120, 30, 36)
LEECH = ((70, 32, 36), (120, 50, 52), (190, 70, 70))   # body, belly, gorged (latched)
LEECH_TELL = ((230, 60, 60), (120, 30, 30))           # surge line / whirlpool / nest ripples
SHOT_BLOOD = ((230, 60, 70), ((160, 30, 40), (90, 20, 26)))
# Lady Proboscia and the smoke keeper's quest (M22.2).
STAGNANT_FG = (96, 110, 60)
STAGNANT_BG = (34, 40, 22)
SCUM_FG = (130, 150, 70)
BRAZIER_FG = (150, 150, 160)
BRAZIER_BG = (40, 38, 40)
BRAZIER_LIT_FG = (255, 170, 70)
BRAZIER_LIT_BG = (80, 34, 18)
SMOKE = ((190, 190, 190), (130, 130, 135), (85, 85, 90))   # fresh, drifting, thin
FLAME = ((255, 220, 120), (255, 130, 40))
HEAT_BAR = ((255, 160, 60), (70, 60, 55))                  # filled, empty
MOSQUITO = {
    "body": (58, 52, 50), "stripe": (225, 225, 230), "eye": (200, 40, 40),
    "wing": (200, 220, 235, 110), "wing_edge": (220, 235, 250, 170),
    "belly": ((96, 80, 72), (150, 60, 58), (190, 40, 46), (230, 30, 40)),  # by gulps
    "glow": (255, 110, 110), "nose": (40, 32, 30), "nose_hot": (255, 90, 80),
}
MOSQUITO_TELL = ((255, 90, 70), (160, 50, 40))
FEVER = ((170, 200, 80), (110, 140, 50))
POP_BAR = ((255, 80, 90), (70, 30, 34))
SHOT_NEEDLE = ((240, 240, 250), ((200, 60, 60), (110, 40, 40)))
SHOT_BUZZ = ((230, 230, 150), ((160, 160, 100), (100, 100, 70)))
# The dodge roll (M18): dust kicked up behind it (fresh, settling), Blink's
# flash, and a trail patch's two shades per status (Scorched Trail, Prism Dash).
ROLL_DUST = ((200, 190, 165), (130, 122, 105))
BLINK = ((255, 250, 170), (170, 140, 255))
TRAIL = {"burn": ((255, 150, 50), (200, 70, 30)), "chill": ((170, 220, 255), (100, 160, 230)),
         "poison": ((150, 230, 80), (90, 160, 50)), "shock": ((255, 240, 100), (200, 170, 60))}
# XP gems: small, medium, big (bright, dark).
GEM = (((110, 190, 255), (60, 110, 200)), ((120, 240, 140), (60, 160, 80)),
       ((255, 110, 110), (190, 50, 60)))
# Spells.
DAGGER = (220, 225, 235)
HUD_SPELL = (170, 200, 255)         # the spells line on the HUD
EMBER = ((255, 170, 60), (230, 100, 40), (150, 60, 30))
NOVA = ((225, 245, 255), (150, 210, 255), (90, 150, 220))

# --- M15: loot (rune shards) and the Guild Hall ------------------------------------------
LOOT = (90, 215, 200)
LOOT_LIGHT = (190, 255, 240)
LOOT_DARK = (40, 120, 120)
LOOT_RUNE = (255, 210, 90)
LOOT_TEXT = (120, 230, 210)          # loot amounts in text
HUB_WOOD_FG = (92, 66, 44)
HUB_WOOD_BG = (46, 32, 22)
HUB_STONE_FG = (84, 84, 90)
HUB_STONE_BG = (50, 50, 56)
HUB_CARPET_FG = (150, 40, 44)
HUB_CARPET_BG = (110, 26, 32)
HUB_WALL_FG = (118, 116, 126)
HUB_WALL_BG = (62, 60, 70)
HUB_BOOKS_FG = (210, 170, 100)
HUB_BOOKS_BG = (70, 40, 24)
HUB_COUNTER_FG = (160, 108, 62)
HUB_COUNTER_BG = (96, 62, 34)
HUB_BANNER = (190, 40, 52)
HUB_TORCH = (255, 180, 60)
HUB_DUMMY = (200, 160, 90)
HUB_GATE_FG = (140, 140, 150)
HUB_GATE_BG = (16, 14, 18)
HUB_PEDESTAL = (160, 158, 170)
HUB_LABEL = (255, 220, 140)          # names over the guild's people
HUB_PROMPT = (255, 255, 255)
PIP_EMPTY = (70, 70, 78)             # levels not bought yet
DEV_TAG = (255, 120, 220)            # developer mode marker

# --- M16: more spells, toasts -----------------------------------------------------------
SHOT_EMBER = ((255, 190, 80), ((255, 120, 40), (170, 70, 30)))
SHOT_BONE = ((235, 230, 210), ((180, 175, 160), (120, 115, 105)))
TOAST = (255, 235, 140)
TOAST_DIM = (180, 160, 90)
RUNE = ((190, 140, 255), (120, 90, 190))
WOLF = ((190, 220, 255), (110, 150, 210))     # spirit wolf: body, dim
POOL = ((120, 200, 70), (70, 130, 45))
CLOUD = ((170, 175, 195), (110, 115, 135))
TOTEM = ((120, 230, 140), (200, 170, 110))
TURRET = ((230, 225, 205), (150, 140, 120))
CRACKLE = ((255, 250, 150), (150, 200, 255))
PUDDLE = ((120, 170, 230), (80, 120, 180))     # M28.2f Downpour's rain puddle
HUD_SHIELD = (120, 190, 255)

# --- M17: landmarks, quests, bosses ------------------------------------------------------
# Landmark tiles (world/landmarks.py).
LAIR_STONE_FG = (150, 160, 130)      # the lair's ring of standing stones
LAIR_STONE_BG = (52, 58, 44)
THORN_FG = (170, 120, 70)            # the thorn gate that seals the lair
THORN_BG = (48, 30, 20)
POND_FG = (70, 150, 120)             # Froggy's pools (like bog, a bit brighter)
POND_BG = (16, 48, 42)
LILY_FG = (110, 200, 90)             # lily pads round the pools
PLANK_FG = (150, 110, 70)            # the frog hunter's hut
PLANK_BG = (70, 48, 30)
DECK_FG = (120, 88, 56)
DECK_BG = (44, 32, 20)
RACK_FG = (190, 160, 110)            # his drying racks
# Map colors for the new tiles.
MAP_TILE.update({
    "standing stones": (165, 170, 150), "thorn gate": (190, 120, 60), "pond": (40, 95, 90),
    "plank wall": (150, 110, 70), "drying rack": (150, 110, 70),
})
MAP_TILE_BIOME.update({"lily pads": "swamp", "deck": "swamp", "hunter's post": "swamp",
                       "clots": "swamp"})
MAP_TILE["blood pool"] = (110, 24, 30)
MAP_TILE.update({"stagnant water": (70, 82, 44), "cold brazier": (150, 150, 160),   # M22.2
                 "smoking brazier": (255, 160, 70)})
MAP_TILE_BIOME["scum"] = "swamp"
MAP_TILE_BIOME["stuck javelin"] = "swamp"          # P11
# The desert's landmarks (M23.1): the scarab collector's oasis camp and
# the Dung Pit (a sunken sandstone arena).
SANDSTONE_FG = (196, 160, 104)
SANDSTONE_BG = (110, 82, 46)
SAND_PIT_FG = (120, 96, 56)
SAND_PIT_BG = (30, 24, 12)
OASIS_FG = (110, 190, 200)
OASIS_BG = (24, 70, 84)
PALM_FG = (90, 170, 70)
TENT_FG = (220, 200, 160)
TENT_BG = (130, 60, 40)
RUG_FG = (180, 70, 60)
RUG_BG = (90, 34, 30)
STALL_FG = (240, 200, 70)
# Khepri the Dung Emperor, his ball and the scarabs (render/beetle.py).
KHEPRI = {
    "shell": (52, 44, 40), "shine": (130, 118, 96), "edge": (24, 20, 18),
    "leg": (40, 34, 30), "horn": (70, 60, 50), "wing": (200, 190, 150, 120),
    "eye": (230, 170, 60),
}
DUNG = ((112, 78, 44), (84, 56, 30), (150, 112, 66), (180, 160, 90))   # base, dark, light, straw
KHEPRI_TELL = ((255, 120, 60), (160, 70, 30))
GOLD_SCARAB = {"shell": (240, 196, 60), "shine": (255, 245, 180), "edge": (120, 84, 20),
               "leg": (90, 64, 20)}
SCARAB = {"shell": (40, 110, 120), "shine": (120, 210, 200), "edge": (14, 40, 46),
          "leg": (20, 50, 54)}
SHOT_SAND = ((240, 210, 140), ((190, 160, 100), (120, 100, 60)))
SHOT_DUST = ((220, 200, 160), ((160, 140, 110), (100, 90, 70)))
SHOT_CLOD = ((170, 120, 70), ((120, 84, 50), (80, 56, 34)))
# Map pins (quest givers, lairs): (fill, edge).
PIN_QUEST = ((255, 220, 90), (60, 40, 0))
PIN_LAIR = ((255, 90, 70), (60, 10, 0))
PIN_TARGET = ((225, 120, 255), (45, 10, 60))
PIN_DONE = ((150, 150, 150), (40, 40, 40))
# Quest givers (P2, user-picked): a ROUND pin in its biome's colour, always
# on the maps. Not the terrain colours (forest and mushroom are both purple
# there, the ruins grey like PIN_DONE). Plains: the old gold PIN_QUEST.
PIN_GIVER = {
    "swamp": ((150, 220, 60), (30, 50, 10)),       # lime
    "desert": ((255, 170, 40), (70, 40, 0)),       # amber
    "ruins": ((120, 200, 255), (20, 45, 70)),      # ice blue
    "forest": ((90, 255, 170), (10, 60, 35)),      # ghost mint
    "mushroom": ((255, 100, 200), (70, 15, 50)),   # hot pink
    "plains": PIN_QUEST,
}
# A fight's fixtures on the maps (M24.1, the Fallout King's vault).
PIN_SHOWER = ((120, 220, 255), (20, 50, 70))
PIN_DRY = ((90, 100, 110), (30, 30, 34))
PIN_VALVE = ((255, 140, 60), (70, 30, 10))
PIN_LEAD = ((170, 176, 210), (40, 40, 60))
PIN_CORE = ((200, 255, 110), (40, 70, 20))
# Quest log (ui/quest_log.py).
QUEST_TITLE = (255, 220, 140)
QUEST_TEXT = (210, 210, 190)
QUEST_DONE = (120, 200, 120)
SPEECH = (245, 240, 220)             # an NPC's words over their head
SPEECH_NAME = (255, 220, 140)
# Bosses: banner text, off-screen arrow, telegraphs.
BOSS_BANNER = (255, 120, 90)
BOSS_BANNER_SUB = (255, 210, 160)
BOSS_ARROW = (255, 90, 70)
TELEGRAPH = ((255, 90, 70), (160, 50, 40))       # aim lines, landing rings: bright, dim
RIPPLE = ((150, 230, 220), (80, 150, 150))       # where a diving boss comes up
TONGUE = ((255, 120, 160), (190, 70, 110))
# Boss shots: (head, (trail near, trail far)).
SHOT_TADPOLE = ((40, 40, 40), ((90, 120, 80), (60, 80, 55)))
SHOT_BUBBLE = ((200, 245, 255), ((120, 190, 220), (80, 130, 160)))
SHOT_RIPPLE = ((150, 230, 220), ((90, 170, 170), (60, 110, 110)))
SHOT_WOBBLE = ((255, 140, 255), ((200, 90, 220), (130, 60, 150)))
# The psychedelic colors (frogs, Froggy's last phase, rainbow rain), in hue order.
PSYCHEDELIC = ((255, 85, 85), (255, 165, 60), (255, 235, 90), (115, 230, 115),
               (90, 220, 230), (105, 165, 255), (190, 110, 255), (255, 120, 210))
PSY_SHOTS = tuple(
    (c, (tuple(round(v * 0.72) for v in c), tuple(round(v * 0.45) for v in c))) for c in PSYCHEDELIC
)
MAP_TILE.update({"sandstone": (196, 160, 104), "oasis": (60, 150, 170), "palm": (70, 140, 60),
                 "tent": (170, 80, 50), "collector's stall": (240, 200, 70)})   # M23.1
MAP_TILE_BIOME.update({"sand pit": "desert", "rug": "desert", "collector's post": "desert"})
# Ol' Spitter's caravanserai and the caravan master's quest (M23.2): a
# ring of mud brick, a flagstone yard, arcades of brick arches, stone
# water troughs (smashable), tethering posts, hay; the lost cargo bundles.
MUDBRICK_FG = (200, 150, 100)
MUDBRICK_BG = (120, 76, 46)
FLAGSTONE_FG = (130, 112, 84)
FLAGSTONE_BG = (52, 44, 32)
ARCH_FG = (226, 186, 130)
ARCH_BG = (146, 98, 58)
TROUGH_FG = (120, 200, 230)
TROUGH_BG = (96, 92, 84)
TROUGH_BROKEN_FG = (100, 140, 150)
POST_FG = (150, 100, 56)
HAY_FG = (220, 190, 90)
CARGO_FG = (240, 200, 120)
CARGO_BG = (110, 64, 30)
CRATES_FG = (200, 150, 80)
MAP_TILE.update({"mud brick": (190, 140, 90), "brick arch": (226, 186, 130),
                 "water trough": (90, 170, 200), "tethering post": (150, 100, 56),
                 "cargo bundle": (240, 200, 120), "crates": (200, 150, 80)})
MAP_TILE_BIOME.update({"flagstones": "desert", "hay": "desert", "broken trough": "desert"})
# Ol' Spitter and the camels (render/camel.py). Colors: hide, its shade,
# the humps' shine, the legs and outline, the muzzle.
OL_SPITTER = {"hide": (206, 160, 100), "shade": (156, 112, 64), "shine": (240, 210, 156),
              "edge": (62, 40, 22), "muzzle": (130, 92, 56), "eye": (30, 18, 10),
              "leg": (176, 132, 82), "shadow": (24, 20, 14), "blanket": (176, 48, 40),
              "fringe": (240, 196, 80)}
MANGY_CAMEL = {"hide": (170, 136, 92), "shade": (124, 96, 62), "shine": (200, 172, 128),
               "edge": (56, 40, 22), "muzzle": (104, 78, 48), "eye": (30, 18, 10),
               "leg": (150, 116, 76), "shadow": (24, 20, 14), "patch": (112, 88, 62)}
MIRAGE_CAMEL = {"hide": (170, 220, 255, 140), "shade": (120, 180, 230, 130),
                "shine": (225, 245, 255, 170), "edge": (80, 130, 200, 150),
                "muzzle": (120, 170, 220, 140), "eye": (50, 80, 130, 190),
                "leg": (150, 200, 245, 140)}
GHOST_CAMEL = {"hide": (205, 232, 255, 175), "shade": (150, 195, 240, 165),
               "shine": (240, 252, 255, 200), "edge": (100, 145, 210, 185),
               "muzzle": (150, 190, 230, 175), "eye": (70, 100, 150, 210),
               "leg": (180, 215, 250, 170)}
SPITTER_TELL = ((150, 255, 90), (80, 170, 50))   # his aim lines, rings: bright, dim
KICK_TELL = ((255, 90, 70), (170, 50, 40))       # his hind legs flashing, the kick's cone
DRINK_SPLASH = ((150, 220, 255), (90, 160, 210))
LOOGIE = ((170, 230, 90), (110, 170, 60), (220, 255, 170))   # body, dark, shine
SHOT_SPIT = ((190, 255, 120), ((130, 200, 80), (80, 140, 50)))
SHOT_LOB_SPIT = ((170, 240, 100), (90, 140, 50), ((150, 255, 90), (80, 170, 50)))
HOT_SAND = ((255, 190, 90), (200, 130, 60))      # the gallop's trail of churned, stinging sand
# The Nameless Magus's sunken observatory and the apprentice's star
# circles (M23.3): blue-glazed walls, sandstone slabs, a star-chart
# mosaic, broken columns, a fallen brass telescope, sand drifts; walls of
# sand he raises.
GLAZED_FG = (110, 170, 230)
GLAZED_BG = (34, 70, 120)
SLAB_FG = (150, 128, 90)
SLAB_BG = (66, 54, 36)
CHART_FG = (240, 210, 120)
CHART_BG = (30, 40, 86)
COLUMN_FG = (230, 214, 176)
COLUMN_BG = (150, 130, 96)
BRASS_FG = (240, 196, 90)
BRASS_BG = (130, 90, 30)
DRIFT_FG = (200, 172, 112)
STAR_RING_FG = (150, 200, 255)
SEAL_FG = (255, 230, 120)
SEAL_BROKEN_FG = (120, 110, 90)
DUNE_WALL_FG = (226, 196, 130)
DUNE_WALL_BG = (170, 136, 80)
SCROLLS_FG = (230, 220, 180)
MAP_TILE.update({"glazed stone": (90, 150, 210), "column": (230, 214, 176),
                 "brass telescope": (240, 196, 90), "sand wall": (226, 196, 130),
                 "scroll rack": (230, 220, 180)})
MAP_TILE_BIOME.update({"sandstone slabs": "desert", "star chart": "desert", "sand drift": "desert",
                       "broken column": "desert", "star ring": "desert", "seal": "desert",
                       "broken seal": "desert"})
# The Magus (render/magus.py): robe, its shade, sash, skin, beard, staff,
# its lens; his runes, beams and time zones.
MAGUS = {"robe": (70, 60, 120), "shade": (44, 36, 84), "sash": (230, 180, 70),
         "skin": (190, 150, 110), "beard": (230, 228, 220), "staff": (120, 84, 46),
         "lens": (160, 230, 255), "edge": (20, 16, 30), "hood": (52, 44, 96)}
RUNE = ((255, 200, 90), (200, 120, 40), (120, 80, 30))     # charged, charging, dim
RUNE_SCUFFED = (110, 96, 70)
LANCE = ((255, 250, 200), (255, 220, 120))                 # the beam's core, its glow
LANCE_TELL = ((255, 230, 120), (170, 140, 60))
SERPENT = ((210, 170, 100), (150, 110, 60))
TIME_SLOW_ZONE = ((120, 170, 255), (70, 110, 190))
TIME_FAST_ZONE = ((255, 210, 90), (190, 140, 50))
QUICKSAND_COL = ((200, 160, 90), (140, 106, 58))
VORTEX_COL = ((230, 200, 140), (170, 140, 90))
HOURGLASS_COL = {"frame": (170, 120, 50), "glass": (190, 230, 255), "sand": (240, 200, 110),
                 "edge": (40, 28, 12)}
ELEMENTAL = ((220, 190, 120), (170, 140, 80), (255, 240, 190))   # body, dark, eyes
GOLEM = {"body": (186, 150, 96), "dark": (126, 96, 58), "eye": (255, 160, 60)}
SIGIL = ((255, 210, 110), (200, 140, 50))
SHOT_BLADE = ((255, 236, 170), ((210, 180, 110), (150, 120, 70)))
SHOT_TIME = ((180, 220, 255), ((120, 170, 230), (80, 110, 170)))
# The Fallout King's reactor vault and the scavenger's scrap camp (M24.1).
VAULT_WALL_FG = (150, 150, 140)
VAULT_WALL_BG = (70, 72, 68)
REACTOR_FG = (120, 255, 120)
REACTOR_BG = (40, 60, 44)
PILLAR_FG = (176, 176, 166)
PILLAR_BG = (100, 100, 94)
PIPE_FG = (190, 150, 90)
PIPE_BG = (60, 54, 44)
VALVE_FG = (255, 80, 60)
VALVE_SHUT_FG = (90, 220, 255)
SHOWER_FG = (120, 220, 255)
SHOWER_OFF_FG = (80, 90, 100)
LEAD_FG = (120, 126, 150)
LEAD_BG = (56, 58, 76)
GRATE_FG = (110, 110, 100)
BEACON_FG = (255, 230, 80)
SLUDGE_FG = (140, 255, 90)
SLUDGE_BG = (40, 80, 30)
PLATES_FG = (130, 130, 120)
PLATES_BG = (54, 54, 50)
SCRAP_FG = (180, 140, 90)
SCRAP_BG = (90, 66, 44)
MAP_TILE.update({"vault wall": (150, 150, 140), "reactor": (120, 255, 120),
                 "concrete pillar": (176, 176, 166), "pipe": (190, 150, 90),
                 "coolant valve": (255, 80, 60), "shut valve": (90, 220, 255),
                 "lead wall": (120, 126, 150), "sludge": (110, 200, 70),
                 "scrap wall": (180, 140, 90), "beacon": (255, 230, 80)})
MAP_TILE_BIOME.update({"shower": "ruins", "dry shower": "ruins", "sewer grate": "ruins",
                       "beacon site": "ruins", "metal plates": "ruins", "scavenger's post": "ruins"})
# The Fallout King (render/fallout.py) and his glow.
KING = {"skin": (110, 190, 90), "dark": (60, 110, 50), "glow": (190, 255, 120),
        "core": (230, 255, 160), "plate": (90, 96, 88), "edge": (20, 34, 18),
        "eye": (255, 255, 200)}
KING_TELL = ((190, 255, 90), (110, 170, 50))
GAMMA = ((220, 255, 160), (140, 230, 90))
GOO = ((140, 230, 80), (90, 160, 50))
FALLOUT_COL = ((170, 255, 100), (90, 170, 60))
RADS_BAR = ((150, 255, 90), (255, 220, 60), (255, 90, 60))   # low, high, irradiated
GHOUL = {"body": (140, 200, 110), "dark": (70, 110, 60), "eye": (240, 255, 160)}
ROD = {"rod": (200, 255, 140), "dark": (70, 120, 50), "cap": (150, 150, 140)}
BARREL = {"body": (210, 190, 60), "band": (60, 50, 20), "goo": (140, 230, 80)}
SKULL = ((220, 255, 150), (120, 200, 80))
SHOT_GLOW = ((200, 255, 130), ((130, 210, 90), (80, 140, 60)))
SHOT_EMP = ((150, 220, 255), ((90, 160, 230), (60, 100, 170)))
# The Snow King's frozen throne hall and the sister's captives (M24.2).
ICE_WALL_FG = (200, 235, 255)
ICE_WALL_BG = (90, 140, 190)
FROST_FG = (170, 200, 220)
FROST_BG = (40, 54, 70)
THRONE_FG = (230, 250, 255)
THRONE_BG = (120, 170, 220)
ICE_PILLAR_FG = (220, 245, 255)
ICE_PILLAR_BG = (110, 170, 220)
FIRE_FG = (150, 110, 70)
FIRE_LIT_FG = (255, 170, 60)
STATUE_FG = (200, 220, 240)
STATUE_BG = (80, 100, 130)
SNOWDRIFT_FG = (230, 240, 250)
ICE_BLOCK_FG = (200, 240, 255)
ICE_BLOCK_BG = (100, 160, 210)
SLUSH_FG = (150, 170, 180)
FROZEN_POND_FG = (180, 220, 240)
FROZEN_POND_BG = (70, 110, 150)
MAP_TILE.update({"ice wall": (200, 235, 255), "ice throne": (230, 250, 255),
                 "ice pillar": (200, 235, 255), "fire brazier": (200, 120, 60),
                 "lit fire brazier": (255, 170, 60), "frozen statue": (200, 220, 240),
                 "ice block": (200, 240, 255), "frozen pond": (150, 200, 230)})
MAP_TILE_BIOME.update({"frost stone": "ruins", "snowdrift": "ruins", "slush": "ruins"})
PIN_FIRE = ((255, 160, 60), (70, 30, 10))
PIN_BLOOD = ((220, 40, 50), (60, 0, 5))         # M28.2b: Bloodhound's bleeding enemies
AMP = (255, 200, 120)                           # M28.2c: Stompers +9, an amp on the ground
BRAMBLE = (120, 170, 80)                        # M28.2d: Brambleguard +6's ring
SHOT_PATH = (110, 70, 70)                       # M28.2d: Shattercoat +3, where a shot is going
PIN_FIRE_LIT = ((255, 230, 120), (90, 50, 10))
PIN_CROWN = ((160, 225, 255), (20, 50, 80))     # his crown is iron and ice (M24.4)
# The Snow King (render/snowking.py).
SNOW_KING = {"crown": (255, 215, 70), "gem": (120, 220, 255), "ice": (200, 240, 255),
             "glow": (160, 220, 255)}
SNOW_TELL = ((160, 230, 255), (90, 150, 200))
ICE_SHEET = ((200, 240, 255), (130, 190, 230))
PENGUIN = {"body": (30, 34, 44), "belly": (240, 244, 250), "beak": (255, 170, 40)}
SNOWBALL = ((245, 250, 255), (190, 210, 230))
CHILL_BAR = ((150, 220, 255), (255, 255, 255), (120, 160, 255))   # low, high, encased
MOUNT_BAR = ((190, 150, 95), (240, 205, 130), (240, 205, 130))    # P6: the mount's wait
# P7: the plains' new enemies (render/plains.py).
PLAINS_TELL = ((255, 80, 60), (230, 120, 80))     # the "!" over a wind-up; a charge line
DRUM_RING = ((255, 200, 120), (170, 120, 70))     # the war drummer's ring: on the beat, between
ELITE_STAR = (255, 210, 80)                       # over an elite
HEAL_BEAM = ((140, 255, 140), (80, 190, 90))      # the field priest's heal
SHOT_PEBBLE = ((200, 196, 186), ((140, 136, 128), (100, 98, 92)))   # the bandit's sling
# P8: the haunted forest (render/forest.py).
SHOT_GHOST_AXE = ((200, 236, 240), ((120, 170, 190), (80, 110, 130)))
SHOT_CURSE = ((210, 120, 255), ((150, 70, 200), (90, 40, 130)))
SHOT_WEB = ((235, 235, 235), ((170, 170, 175), (120, 120, 126)))
WEB = ((225, 225, 230), (140, 140, 150))          # a web patch: strands, faded
SCREAM = ((200, 236, 240), (120, 170, 190))
HOWL = ((190, 200, 230), (110, 120, 160))
DIG_CRACK = ((150, 120, 80), (100, 80, 50))
RITUAL = ((255, 120, 90), (160, 60, 50))          # the cultist's ring between the candles
# P9: the desert (render/desert.py).
SHOT_GLASS = ((210, 245, 255), ((150, 210, 230), (100, 150, 170)))
SHOT_SPINE = ((180, 220, 120), ((120, 160, 80), (80, 110, 50)))
GAZE = ((200, 200, 190), (130, 130, 120))         # the basilisk's stare
BANDAGE = ((226, 218, 196), (160, 150, 130))      # the mummy's lash
FLAMES = ((255, 210, 90), (240, 110, 40))
VORTEX = ((230, 200, 130), (170, 140, 80))        # the djinn lamp's sand
STONE = (150, 150, 140)                           # a hero turned to stone
# P10: the ruins (render/ruins.py).
SHOT_CLOCK_BOLT = ((255, 220, 120), ((200, 160, 60), (140, 110, 40)))
SHOT_HEAVY_BOLT = ((235, 235, 245), ((160, 120, 70), (110, 80, 50)))
SNIPER_LINE = ((255, 90, 70), (255, 220, 120))    # following you / locked
STOMP = (190, 180, 160)                           # the colossus's ring
FLAIL = (200, 205, 215)
CRAB_SHELL_BAR = (170, 170, 160)
# P11: the swamp.
SHOT_JAVELIN = ((220, 200, 160), ((150, 120, 80), (110, 85, 55)))
CURSE = ((120, 60, 150), (70, 30, 90))            # a hag's curse puddle
GAS = ((150, 190, 80), (100, 130, 60))            # a bloated corpse's cloud
MARSH_REAL = (190, 255, 255)                      # the real marsh light's glint
# P12: the mushroom biome.
SHOT_SPORE_DART = ((200, 170, 120), ((140, 110, 70), (100, 80, 50)))
POLLEN = ((240, 230, 140), (170, 160, 90))        # the myconid's healing cloud
SLIME = ((170, 200, 170), (110, 140, 110))        # the snail's trail
MOLD = ((110, 190, 160), (60, 120, 100))          # a mold core's patches
ROOTS = ((200, 160, 90), (120, 90, 50))           # the rootweaver's roots / cracks
FAIRY_DOTS = (150, 170, 240)
WRAITH = ((190, 230, 255), (110, 160, 210))
SHOT_SHARD = ((220, 245, 255), ((150, 210, 240), (100, 150, 200)))
SHOT_SPIKE = ((200, 240, 255), ((140, 190, 230), (90, 130, 180)))
SHOT_SNOW = ((245, 250, 255), ((200, 215, 230), (150, 165, 185)))
# Fragile's ruined ballroom and the pawn dealer's quest (M24.3).
CASTLE_FG = (150, 140, 160)
CASTLE_BG = (60, 52, 70)
PARQUET_FG = (150, 100, 70)
PARQUET_BG = (60, 38, 28)
SHUTTER_FG = (120, 80, 50)
SHUTTER_BG = (40, 26, 18)
WINDOW_OPEN_FG = (255, 240, 170)
WINDOW_OPEN_BG = (200, 170, 90)
LEVER_FG = (200, 170, 90)
MARBLE_FG = (230, 225, 235)
MARBLE_BG = (150, 140, 160)
COFFIN_FG = (140, 40, 50)
COFFIN_BG = (50, 20, 24)
VELVET_FG = (200, 40, 60)
VELVET_BG = (90, 20, 30)
MIRROR_FG = (200, 210, 230)
CHANDELIER_FG = (230, 190, 90)
PIECE_FG = (210, 150, 90)
MAP_TILE.update({"castle wall": (150, 140, 160), "shuttered window": (120, 80, 50),
                 "open window": (255, 240, 170), "marble pillar": (230, 225, 235),
                 "coffin": (140, 40, 50), "staked coffin": (90, 70, 60),
                 "velvet throne": (200, 40, 60), "cracked mirror": (200, 210, 230),
                 "fallen chandelier": (230, 190, 90)})
MAP_TILE_BIOME.update({"parquet": "ruins", "lever": "ruins", "bear piece": "ruins"})
PIN_LEVER = ((255, 220, 120), (80, 60, 20))
PIN_SUN = ((255, 250, 200), (110, 90, 30))
PIN_COFFIN = ((220, 80, 90), (60, 20, 24))
PIN_BEAR = ((210, 150, 90), (60, 40, 20))
# Fragile (render/fragile.py).
SUN = ((255, 240, 160), (230, 200, 110))
FRAGILE_TELL = ((255, 70, 110), (170, 40, 70))
GAZE = ((255, 60, 90), (150, 30, 50))
MIST = ((190, 180, 220), (130, 120, 160))
BAT_COL = ((70, 50, 90), (130, 100, 160))
BEAT_COL = ((255, 120, 180), (110, 60, 90))
SHOT_PETAL = ((255, 120, 150), ((210, 50, 90), (130, 30, 60)))   # her rose petals (was the riff's notes)
SHOT_SLASH = ((255, 70, 90), ((200, 40, 60), (130, 30, 40)))
SHOT_BAT = ((150, 110, 180), ((100, 70, 130), (60, 40, 80)))
# Nettle's withered glade and the hedge witch's shrines (M25.1).
SHRINE_FG = (150, 200, 90)
SHRINE_CLEAN_FG = (240, 230, 170)
ROT_RING_FG = (120, 170, 70)
BRAMBLE_FG = (100, 120, 60)
BRAMBLE_BG = (22, 26, 16)
TOADSTOOL_FG = (220, 70, 70)
TOADSTOOL_BG = (70, 24, 30)
HOLLOW_TREE_FG = (80, 64, 60)
GROWCAP_FG = (150, 255, 170)
GROWCAP_SPENT_FG = (70, 96, 74)
MAP_TILE.update({"blighted shrine": (150, 200, 90), "cleansed shrine": (240, 230, 170),
                 "bramble": (100, 120, 60), "giant toadstool": (220, 70, 70),
                 "hollow tree": (80, 64, 60), "growcap": (150, 255, 170),
                 "spent growcap": (70, 96, 74)})
MAP_TILE_BIOME.update({"rot ring": "forest"})
PIN_GROWCAP = ((150, 255, 170), (20, 60, 30))
PIN_SEED = ((170, 110, 200), (50, 20, 60))
# Nettle (render/nettle.py).
NETTLE_TELL = ((200, 255, 120), (110, 170, 60))      # her tells: bright, dim
NETTLE_GLOW = ((210, 255, 150), (140, 220, 90))
DUST_CLOUD = ((255, 240, 160), (220, 190, 120), (170, 140, 100))
NETTLE_SHADOW = ((0, 0, 0, 150), (120, 130, 150, 200))   # fill, moonlit rim
BLIGHT_FG = ((110, 150, 60), (80, 110, 40))
BLIGHT_SEED_FG = (200, 120, 230)
SPARK_COL = ((220, 140, 255), (150, 90, 200))
WISP_COL = ((190, 255, 225), (120, 210, 180))
THORN_TELL = ((160, 120, 80), (110, 80, 50))
SHOT_GLITTER = ((255, 245, 170), ((230, 200, 110), (170, 140, 80)))
SHOT_THORN = ((170, 200, 110), ((120, 150, 70), (80, 100, 50)))
MOTH_COL = ((170, 160, 120), (120, 110, 84))
SPRITE_COL = ((150, 230, 110), (90, 160, 70))
# Love & Cuddles' hollow oak and the forester's nut caches (M25.2).
NUT_SHELL_FG = (176, 136, 88)
NUT_CACHE_FG = (226, 176, 100)
NUT_CACHE_BG = (64, 42, 24)
WOODPILE_FG = (170, 116, 62)
OAK_ROOTS_FG = (128, 96, 64)
OAK_ROOTS_BG = (30, 22, 16)
OAK_TRUNK_FG = (124, 94, 66)
OAK_CROWN_FG = (84, 104, 70)
MAP_TILE.update({"nut shells": (176, 136, 88), "spilt nuts": (176, 136, 88),
                 "nut cache": (226, 176, 100), "woodpile": (170, 116, 62),
                 "oak roots": (128, 96, 64), "climbing oak": (124, 94, 66),
                 "oak crown": (84, 104, 70)})
PIN_MOUND = ((236, 176, 96), (70, 40, 10))
PIN_OAK = ((150, 220, 120), (30, 60, 20))
# Mycelium (M26): the sever quests' nodes, the fly agaric's fruiting ring.
MYC_NODE_FG = (210, 130, 255)
SPILL_RED_FG = (236, 70, 70)
SHROOM_WALL_FG = (190, 90, 150)
RING_SHROOM_FG = (236, 96, 96)
NET_NODE_FG = (240, 180, 255)
MAP_TILE.update({"mycelium node": (210, 130, 255), "severed node": (236, 70, 70),
                 "mushroom thicket": (190, 90, 150), "fruiting ring": (236, 96, 96),
                 "broken node": (110, 80, 130), "network node": (240, 180, 255)})
PIN_NODE = ((240, 180, 255), (60, 20, 70))
# More than Life's necropolis (M27; render/necro.py).
GRAVE_SOIL_FG = (84, 78, 70)
GRAVE_SOIL_BG = (18, 16, 18)
BONE_FG = (214, 206, 184)
BONE_LITTER_FG = (128, 120, 104)
RITUAL_FG = (110, 230, 140)
GRAVESTONE_FG = (150, 150, 160)
MAUSOLEUM_FG = (96, 96, 108)
CRYPT_FG = (70, 72, 82)
CRYPT_BG = (26, 26, 32)
MAP_TILE.update({"grave soil": (84, 78, 70), "bone litter": (214, 206, 184),
                 "ritual ring": (110, 230, 140), "gravestone": (150, 150, 160),
                 "mausoleum": (96, 96, 108), "crypt wall": (70, 72, 82),
                 "bone gate": (214, 206, 184), "bone wall": (214, 206, 184)})
NECRO_TELL = ((140, 255, 160), (80, 170, 100))     # his tells: bright, dim
NECRO_GLOW = ((150, 255, 170), (90, 200, 120), (255, 90, 90))   # green, deep, red (blast)
GAZE_COL = ((180, 255, 190), (60, 200, 100))
SOUL_COL = ((190, 255, 220), (120, 220, 170))
CORPSE_COL = ((200, 192, 170), (140, 132, 112))
SHOT_BONE_SPEAR = ((236, 228, 206), ((180, 172, 150), (120, 114, 100)))
SHOT_SOUL = ((170, 255, 200), ((110, 210, 150), (70, 150, 100)))
# The giant puffball (M26.3; render/puffball.py).
SPILL_DUST_FG = (150, 140, 90)
MAP_TILE.update({"dusty node": (150, 140, 90), "spore dust": (150, 140, 90)})
DUST_COL = ((170, 160, 100), (120, 112, 70), (210, 200, 150))   # dust, deep, light
PUFF_TELL = ((255, 250, 220), (190, 180, 140))
WIND_COL = (110, 120, 140)
MINE_COL = ((246, 244, 232), (255, 120, 90))            # a mine, its fuse lit
SHOT_PUFF = ((236, 230, 200), ((180, 172, 130), (130, 124, 90)))
SHOT_DUST_SPORE = ((200, 186, 110), ((150, 140, 80), (100, 94, 56)))
# The shaggy ink cap (M26.2; render/inkcap.py).
SPILL_INK_FG = (90, 96, 160)
PAVING_FG = (120, 110, 128)
PAVING_BG = (40, 34, 46)
MAP_TILE.update({"inky node": (90, 96, 160), "old paving": (120, 110, 128),
                 "ink stain": (90, 96, 160)})
INK_COL = ((70, 76, 140), (30, 32, 60), (130, 140, 220))   # ink, deep ink, glint
INKCAP_TELL = ((210, 220, 255), (120, 130, 190))
SCRAWL_COL = ((150, 160, 255), (220, 228, 255))
INK_DARK = (6, 6, 14, 236)
SHOT_SCALE = ((236, 226, 206), ((190, 176, 150), (130, 120, 100)))
SHOT_INK_DROP = ((110, 120, 220), ((70, 76, 150), (40, 44, 90)))
# The fly agaric (render/amanita.py).
AMANITA_TELL = ((255, 150, 150), (180, 80, 80))     # its tells: bright, dim
THREAD_COL = ((90, 60, 110), (240, 170, 255), (255, 120, 220))   # thread, lit, burning
TRIP_COL = ((255, 120, 200), (160, 230, 255), (255, 240, 120), (170, 255, 150))
TRIP_CLOUD_COL = ((240, 120, 140), (250, 220, 220), (170, 100, 120))
FLY_COL = ((170, 190, 150), (110, 130, 100))
WART_COL = ((250, 248, 236), (200, 196, 186))
SHOT_RED_SPORE = ((240, 70, 70), ((200, 50, 60), (130, 30, 40)))
SHOT_WHITE_SPORE = ((250, 246, 236), ((210, 206, 196), (150, 146, 140)))
# The Fallen's still grove and the lumberjack's marked trees (M25.3).
MARKED_FG = (214, 70, 60)
THICKET_FG = (70, 92, 70)
THICKET_BG = (18, 24, 18)
FALLEN_TRUNK_FG = (112, 90, 72)
MAP_TILE.update({"felled tree": (150, 80, 60), "marked tree": (214, 70, 60),
                 "sawhorse": (170, 116, 62), "thicket": (70, 92, 70),
                 "grove tree": (88, 70, 66), "fallen trunk": (112, 90, 72),
                 "fire bowl": (255, 170, 60)})
# The Fallen (render/fallen.py).
FALLEN_TELL = ((190, 255, 150), (110, 170, 90))      # its tells: bright, dim
LEAF_FLURRY = ((150, 170, 90), (110, 120, 70), (170, 120, 70))
ROOT_COL = ((150, 230, 120), (90, 140, 70), (60, 80, 50))   # growing tip, live, fading
ROOT_HELD = (255, 120, 90)
SAP_COL = ((220, 170, 60), (150, 110, 40))
MAW_COL = ((255, 90, 70), (150, 40, 40))
SHOT_LEAF = ((150, 200, 90), ((110, 150, 70), (80, 100, 50)))
SHOT_SAP_SPIT = ((240, 190, 70), ((190, 140, 50), (130, 90, 30)))
# Love & Cuddles (render/squirrel.py).
LOVE_TELL = ((255, 150, 200), (190, 90, 140))       # its tells: bright, dim
MADNESS_COL = ((255, 60, 80), (130, 30, 44))
MOUND_COL = ((150, 106, 64), (236, 176, 96))        # dirt, the acorn peeking out
WIRE_COL = ((230, 236, 248), (150, 160, 178))       # glint, wire
LOG_COL = ((160, 112, 64), (100, 70, 40))
LOVE_SHADOW = (0, 0, 0, 110)
SHOT_ACORN = ((222, 160, 86), ((160, 110, 56), (110, 76, 40)))
SHOT_SPLINTER = ((226, 196, 146), ((166, 136, 96), (116, 96, 66)))
SHOT_CLEAVER = ((232, 238, 248), ((176, 180, 196), (116, 120, 136)))

# The painted figures (render/painted.py, M24.4): a soft shadow under them,
# then each figure's colors.
FIGURE_SHADOW = (0, 0, 0, 90)
HERMIT = {"edge": (16, 20, 30), "fur": (124, 132, 150), "fur_light": (178, 186, 202),
          "fur_dark": (72, 82, 106), "fur_deep": (54, 60, 80), "frost": (226, 242, 255),
          "ice": (150, 225, 255), "face": (12, 14, 24), "eye": (140, 230, 255),
          "eye_cast": (235, 252, 255), "eye_glow": (90, 180, 240), "eye_dim": (90, 140, 180),
          "beard": (236, 244, 252), "beard_shade": (172, 196, 224), "boot": (70, 64, 70),
          "staff": (48, 76, 112), "staff_hi": (110, 160, 210), "shard_cast": (235, 252, 255),
          "glow": (150, 225, 255, 110), "iron": (56, 60, 72), "iron_hi": (130, 138, 158),
          "rime": (196, 236, 255)}
FRAGILE = {"edge": (14, 10, 18), "hair": (236, 234, 244), "hair_hi": (170, 166, 196),
           "skin": (158, 172, 196), "skin_dark": (120, 132, 160), "eye": (240, 40, 70),
           "mouth": (90, 30, 50), "fang": (250, 250, 255), "dress": (40, 28, 48),
           "dress_dark": (24, 16, 30), "dress_hi": (78, 58, 92), "boot": (20, 16, 24), "handle": (76, 44, 32),
           "canopy": (30, 22, 38), "canopy_hi": (66, 50, 84), "rib": (110, 96, 130),
           "lace": (200, 34, 60), "tip": (220, 220, 230), "tear": (150, 210, 255),
           "blush": (220, 120, 150)}
FRAGILE_WOLF = {"edge": (6, 6, 10), "fur": (36, 32, 48), "fur_hi": (78, 72, 104),
                "fur_dark": (20, 18, 28), "ear": (90, 50, 70), "eye": (255, 230, 230),
                "eye_glow": (255, 40, 70), "mouth": (150, 20, 40), "fang": (250, 250, 255),
                "nose": (10, 10, 14), "collar": (204, 34, 56)}
NETTLE = {"edge": (14, 16, 12), "aura": (170, 255, 110, 34), "wing": (150, 140, 172, 225),
          "wing_hi": (190, 182, 210, 200), "wing_dark": (100, 92, 124, 230),
          "spot": (140, 200, 80), "vein": (110, 150, 70), "skin": (178, 198, 168),
          "skin_dark": (140, 160, 132), "eye": (240, 255, 170), "eye_glow": (150, 230, 80),
          "leaf": (150, 92, 52), "leaf_dark": (100, 60, 36), "rot": (110, 150, 60),
          "hair": (40, 84, 54), "twig": (110, 80, 50), "thorn": (200, 220, 160),
          "glow": (210, 255, 140, 170)}
NECROMANCER = {"edge": (8, 6, 12), "robe": (62, 46, 84), "robe_hi": (96, 74, 124),
               "robe_dark": (40, 30, 56), "trim": (150, 100, 190), "hood": (50, 38, 68),
               "face": (6, 6, 10), "eye": (150, 255, 170), "eye_hot": (220, 255, 230),
               "bone": (216, 208, 186), "bone_dark": (160, 150, 128), "staff": (70, 56, 46),
               "blade": (180, 190, 200), "glow": (120, 255, 150), "flame": (110, 255, 140),
               "flame_hi": (220, 255, 210), "skin": (150, 150, 140)}
PUFFBALL = {"edge": (60, 54, 40), "skin": (246, 242, 230), "skin_hi": (255, 255, 248),
            "skin_shade": (214, 206, 186), "skin_dark": (180, 170, 146), "crack": (90, 80, 50),
            "dust": (150, 136, 80), "dust_hi": (190, 176, 110), "eye": (40, 34, 26),
            "mouth": (70, 60, 40), "shine": (255, 255, 255)}
INKCAP = {"edge": (24, 22, 30), "cap": (240, 236, 226), "cap_shade": (206, 198, 186),
          "scale": (190, 170, 140), "scale_dark": (150, 130, 104), "ink": (34, 34, 52),
          "ink_hi": (90, 96, 160), "stem": (236, 232, 222), "stem_shade": (196, 190, 180),
          "face": (40, 36, 46), "eye": (180, 190, 255), "mouth": (20, 18, 26),
          "base": (210, 204, 194)}
AMANITA = {"edge": (40, 12, 16), "cap": (214, 36, 40), "cap_hi": (244, 90, 80),
           "cap_dark": (150, 20, 30), "cap_rim": (236, 200, 170), "gills": (226, 206, 180),
           "gills_dark": (70, 40, 40), "stem": (240, 232, 214), "stem_shade": (196, 186, 168),
           "skirt": (250, 246, 236), "bulb": (226, 214, 192), "thread": (200, 170, 220),
           "vein": (190, 120, 230), "eye": (255, 230, 120), "eye_red": (255, 70, 60),
           "pore": (255, 220, 220)}
THE_FALLEN = {"edge": (14, 12, 14), "bark": (92, 80, 74), "bark_hi": (128, 114, 102),
              "bark_dark": (58, 50, 48), "lichen": (150, 168, 140), "moss": (78, 102, 66),
              "hollow": (18, 12, 14), "eye": (255, 200, 70), "eye_hot": (255, 120, 40),
              "pupil": (30, 16, 10), "lid": (70, 60, 56), "twig": (76, 66, 62),
              "leaf": (96, 112, 70), "leaf_dark": (66, 80, 52), "maw": (120, 24, 30),
              "maw_deep": (40, 8, 12), "tooth": (220, 210, 180), "sap": (230, 170, 60),
              "glow": (255, 170, 60)}
LOVE_CUDDLES = {"edge": (56, 26, 44), "fur": (248, 194, 214), "fur_hi": (255, 226, 236),
                "fur_shade": (222, 154, 186), "fur_dark": (184, 116, 150),
                "matted": (196, 140, 160), "belly": (255, 238, 224), "cheek": (255, 128, 160),
                "eye": (34, 22, 44), "shine": (255, 255, 255), "eye_red": (236, 30, 44),
                "nose": (224, 92, 126), "mouth": (110, 24, 46), "teeth": (255, 250, 236),
                "bow": (255, 96, 156), "bow_dark": (210, 60, 116), "heart": (196, 18, 60),
                "blade": (204, 210, 222), "blade_hi": (244, 248, 255), "handle": (110, 70, 40),
                "blood": (156, 12, 28), "blood_dark": (104, 6, 18), "claw": (90, 50, 60)}
MR_BUTTONS = {"edge": (60, 36, 20), "fur": (200, 146, 88), "shade": (160, 110, 64),
              "inner": (232, 186, 150), "muzzle": (236, 206, 160), "button": (90, 140, 225),
              "patch": (150, 104, 160), "stitch": (90, 56, 30), "bow": (214, 36, 58)}
