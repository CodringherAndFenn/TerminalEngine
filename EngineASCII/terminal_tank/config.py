"""
config.py -- every tunable number in Terminal Tank, in one place.

Units:
  * distances are in WORLD TILES. One tile is drawn as 2 grid cells side by
    side (20x24 px with the default font), which is close to square, so the
    same number means the same on-screen distance horizontally and vertically.
  * times are in seconds, speeds in tiles/second, angles in radians unless a
    name says _DEG.
"""

import math

from .specs import ShellSpec, TankSpec, WeaponSpec

# --- Display / layout --------------------------------------------------------

WINDOW_TITLE = "Terminal Tank"

# Grid cells per world tile, horizontally. Vertically a tile is always 1 row.
CELLS_PER_TILE = 2

# A world tile's size in pixels, used where game logic needs real on-screen
# proportions (rotated hull collision, sprite angles). Matches the default
# 10x24 px font cell.
TILE_PX_W = 20
TILE_PX_H = 24

# Sync frames to the monitor refresh (engine Display(vsync=...)): each frame
# is shown exactly once, which removes the periodic micro-stutter of a
# timer-paced loop. Falls back automatically where unsupported.
VSYNC = True

# The grid always has GRID_ROWS rows (so text and tiles are the same size on
# every screen); the number of columns is picked to match the screen's shape
# (engine_ext/screen.py), so there are no letterbox bars: 128 columns on
# 16:9, 172 on 21:9, 115 on 16:10.
GRID_ROWS = 30
MIN_GRID_COLS = 80
# In windowed mode, the window is the canvas's shape and at most this much of
# the monitor (width and height).
WINDOW_SCREEN_FRACTION = 0.9

# Rows reserved at the bottom of the screen for the HUD (incl. separator line).
HUD_ROWS = 3

# Largest simulation step we accept. A long frame (window drag, alt-tab) is
# clamped to this so the tank can't tunnel through walls on a hitch.
MAX_DT = 0.05

# --- Camera -------------------------------------------------------------------

# How quickly the camera catches up with the tank, per second. Higher = tighter
# (tank stays closer to center); lower = floatier. 0 = locked to the tank.
CAMERA_FOLLOW_RATE = 8.0
# The camera never trails the tank by more than this many tiles.
CAMERA_MAX_LAG_TILES = 3.0

# --- Tank driving -------------------------------------------------------------

# "direct": WASD/arrows give the direction to drive in (the hull turns toward
#           it, reversing instead of spinning around when that's shorter).
# "tank":   W/S = forward/reverse, A/D = rotate the hull (classic tank controls).
DRIVE_MODE = "direct"

# In "direct" mode the tank only reaches full speed once the hull points
# (nearly) where you're steering; while turning it's scaled by
# cos(angle error), and not driven at all past this angle.
DIRECT_MAX_DRIVE_ERROR = math.radians(80)

# Turret traverse rate in rad/s. 0 = the turret snaps to the cursor instantly
# (shells always go exactly where you point).
TURRET_TURN_SPEED = 0.0

# --- Tanks & weapons ---------------------------------------------------------------
#
# Tanks and guns are data (see specs.py). Add entries here to create new tank
# types or weapons; START_TANK picks the one you play (a menu will choose it
# in a later milestone). Sizes are canvas pixels: 1 tile = 20 x 24 px.

WEAPONS = {
    "cannon": WeaponSpec(
        name="cannon",
        fire_interval=0.35,       # hold left click: ~3 shots/s
        shell=ShellSpec(speed=36.0, damage=1, max_range=30.0),
    ),
}

TANKS = {
    "standard": TankSpec(
        name="standard",
        weapon="cannon",
        max_speed=7.0,
        reverse_speed=4.5,
        accel=16.0,
        brake=24.0,
        hull_turn_speed=math.radians(260),
        hull_length_px=54,
        hull_width_px=42,
        turret_radius_px=10,
        barrel_length_px=44,
        barrel_width_px=6,
    ),
}

START_TANK = "standard"

# Collision: the hull is a rotated rectangle (hull_length_px x hull_width_px
# at its true heading). If a turn would push a corner into a wall, the tank
# is nudged up to this far (tiles) away from it; if no nudge fits, the turn
# waits. Makes turning next to walls feel like shoving rather than sticking.
TURN_NUDGE_MAX = 0.2

# --- Terrain durability --------------------------------------------------------------
# Hit points per destructible tile type (shell damage is in WEAPONS above).
# 0 = indestructible. Destroyed walls leave rubble, trees leave splinters;
# both are passable.

WALL_HP = 4
TREE_HP = 2

# --- Effects (seconds) ----------------------------------------------------------------

MUZZLE_FLASH_TIME = 0.07
IMPACT_TIME = 0.22
FIZZLE_TIME = 0.3          # shell reaching max range: little dust puff
TILE_FLASH_TIME = 0.08     # a hit tile blinks bright
SHELL_TRAIL = (0.35, 0.7, 1.05)   # trail dot distances behind a shell, tiles

# --- Sound ------------------------------------------------------------------------------

# Loudness of synthesized effects relative to master volume (0..1).
SFX_VOLUME = 0.5

# --- Rendering ------------------------------------------------------------------

# Screen pixels per sprite pixel (w, h). (1, 1) = smooth shapes; (2, 2) =
# chunky retro pixels that match the block glyphs. w must divide the cell
# width (10) and h the cell height (24).
SPRITE_PIXEL = (1, 1)

# Rotation steps baked per full turn. Fine steps make rotation look
# continuous: 720 = 0.5 degree, which moves the barrel tip well under a pixel
# per step. (Coarse steps made the barrel snap visibly while driving.)
HULL_ANGLE_STEPS = 360
TURRET_ANGLE_STEPS = 720
SHELL_ANGLE_STEPS = 90     # small sprites: a coarser step is invisible
FLASH_ANGLE_STEPS = 72

# Most sprite glyphs kept baked at once (rotated sprites are cached per angle,
# least recently used evicted first). ~1 KB each, twice (ours + engine cache).
SPRITE_GLYPH_BUDGET = 3000

# --- Test map (milestones 1-2) -----------------------------------------------------

TEST_MAP_FILE = "test_map.txt"   # under terminal_tank/assets/maps/
