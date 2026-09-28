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

# --- Display / layout --------------------------------------------------------

WINDOW_TITLE = "Terminal Tank"

# Grid cells per world tile, horizontally. Vertically a tile is always 1 row.
CELLS_PER_TILE = 2

# Sync frames to the monitor refresh (engine Display(vsync=...)): each frame
# is shown exactly once, which removes the periodic micro-stutter of a
# timer-paced loop. Falls back automatically where unsupported.
VSYNC = True

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

TANK_MAX_SPEED = 7.0        # forward top speed, tiles/s
TANK_REVERSE_SPEED = 4.5    # top speed backing up, tiles/s
TANK_ACCEL = 16.0           # tiles/s^2 when speeding up
TANK_BRAKE = 24.0           # tiles/s^2 when slowing / no input
HULL_TURN_SPEED = math.radians(260)   # hull rotation rate, rad/s

# In "direct" mode the tank only reaches full speed once the hull points
# (nearly) where you're steering; while turning it's scaled by
# cos(angle error), and not driven at all past this angle.
DIRECT_MAX_DRIVE_ERROR = math.radians(80)

# Turret traverse rate in rad/s. 0 = the turret snaps to the cursor instantly
# (shells always go exactly where you point).
TURRET_TURN_SPEED = 0.0

# Collision box half-extents in tiles (axis-aligned, doesn't rotate). Sized
# to the unrotated hull (HULL_LENGTH_PX x HULL_WIDTH_PX, about 2.7 x 1.75
# tiles); at diagonal headings the drawn corners can poke slightly past it.
TANK_HALF_W = 1.15
TANK_HALF_H = 0.9

# --- Rendering ------------------------------------------------------------------

# The tank is painted as rotated shapes (render/sprites.py), measured in
# canvas pixels (one grid cell = 10 x 24 px, one world tile = 20 x 24 px).
HULL_LENGTH_PX = 54
HULL_WIDTH_PX = 42
TURRET_RADIUS_PX = 10
BARREL_LENGTH_PX = 44     # from turret center, drawn along the true aim angle
BARREL_WIDTH_PX = 6

# Screen pixels per sprite pixel (w, h). (1, 1) = smooth shapes; (2, 2) =
# chunky retro pixels that match the block glyphs. w must divide the cell
# width (10) and h the cell height (24).
SPRITE_PIXEL = (1, 1)

# Rotation steps baked per full turn. Fine steps make rotation look
# continuous: 720 = 0.5 degree, which moves the barrel tip well under a pixel
# per step. (Coarse steps made the barrel snap visibly while driving.)
HULL_ANGLE_STEPS = 360
TURRET_ANGLE_STEPS = 720

# Most sprite glyphs kept baked at once (rotated sprites are cached per angle,
# least recently used evicted first). ~1 KB each, twice (ours + engine cache).
SPRITE_GLYPH_BUDGET = 3000

# --- Test map (milestone 1) -----------------------------------------------------

TEST_MAP_FILE = "test_map.txt"   # under terminal_tank/assets/maps/
