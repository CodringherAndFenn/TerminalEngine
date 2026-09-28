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

from .specs import EnemySpec, ShellSpec, TankSpec, WeaponSpec

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

# --- Tanks & weapons ---------------------------------------------------------------
#
# Tanks and guns are data (see specs.py). Add entries here to create new tank
# types or weapons; START_TANK picks the one you play (a menu will choose it
# in a later milestone). Sizes are canvas pixels: 1 tile = 20 x 24 px.

#
# Damage and hit points use one scale for everything (player, enemies, terrain).

WEAPONS = {
    # The player's gun.
    "cannon": WeaponSpec(
        name="cannon",
        fire_interval=0.35,       # hold left click: ~3 shots/s
        shell=ShellSpec(speed=36.0, damage=20, max_range=30.0),
    ),
    # Enemy guns. Only the heavy tank's shells damage terrain.
    "light_cannon": WeaponSpec(
        name="light cannon", fire_interval=1.6,
        shell=ShellSpec(speed=24.0, damage=8, max_range=22.0, damages_terrain=False,
                        length_px=7, width_px=3),
    ),
    "sniper_rifle": WeaponSpec(
        name="sniper rifle", fire_interval=3.5,
        shell=ShellSpec(speed=70.0, damage=30, max_range=45.0, damages_terrain=False,
                        length_px=14, width_px=3),
    ),
    "turret_gun": WeaponSpec(
        name="turret gun", fire_interval=2.4, burst=3, burst_gap=0.14,
        shell=ShellSpec(speed=30.0, damage=6, max_range=24.0, damages_terrain=False,
                        length_px=6, width_px=3),
    ),
    "heavy_cannon": WeaponSpec(
        name="heavy cannon", fire_interval=2.8,
        shell=ShellSpec(speed=22.0, damage=25, max_range=24.0, damages_terrain=True,
                        length_px=12, width_px=6),
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
        max_hp=100,
    ),
    # Enemy vehicles.
    "tankette": TankSpec(
        name="tankette", weapon="light_cannon", max_speed=5.5, reverse_speed=4.0,
        accel=12.0, brake=20.0, hull_turn_speed=math.radians(220),
        hull_length_px=38, hull_width_px=30, turret_radius_px=7,
        barrel_length_px=30, barrel_width_px=4,
        turret_turn_speed=math.radians(160), colors="rust",
    ),
    "sniper": TankSpec(
        name="sniper", weapon="sniper_rifle", max_speed=5.0, reverse_speed=4.5,
        accel=10.0, brake=20.0, hull_turn_speed=math.radians(180),
        hull_length_px=44, hull_width_px=32, turret_radius_px=7,
        barrel_length_px=58, barrel_width_px=3,
        turret_turn_speed=math.radians(70), colors="sand",
    ),
    "heavy": TankSpec(
        name="heavy", weapon="heavy_cannon", max_speed=3.2, reverse_speed=2.2,
        accel=6.0, brake=14.0, hull_turn_speed=math.radians(90),
        hull_length_px=70, hull_width_px=54, turret_radius_px=13,
        barrel_length_px=54, barrel_width_px=9,
        turret_turn_speed=math.radians(55), colors="steel",
        front_armor=0.35,         # hits on its front do a third of the damage
    ),
    "turret": TankSpec(
        name="turret", weapon="turret_gun", max_speed=0.0, reverse_speed=0.0,
        accel=0.0, brake=0.0, hull_turn_speed=0.0,
        hull_length_px=44, hull_width_px=44, turret_radius_px=11,
        barrel_length_px=36, barrel_width_px=5,
        turret_turn_speed=math.radians(60), colors="concrete", hull_style="bunker",
    ),
}

START_TANK = "standard"

# --- Enemies ---------------------------------------------------------------------------
#
# Few but dangerous. Every enemy type is data here; its behaviour lives in
# ai/ (picked by `kind`). hp/damage share the damage scale above: the player
# has 100 hp and deals 20 per shell.

ENEMIES = {
    "tankette": EnemySpec(
        name="tankette", kind="tankette", tank="tankette", max_hp=40, sight=16,
        biomes=("plains", "forest", "desert", "ruins", "swamp", "mushroom"), weight=3,
        preferred_range=(7.0, 11.0),
    ),
    "sniper": EnemySpec(
        name="sniper", kind="sniper", tank="sniper", max_hp=50, sight=34,
        biomes=("desert", "plains", "ruins"), weight=2, min_difficulty=0.04,
        preferred_range=(18.0, 28.0),
        windup=1.1,               # laser aim time before the shot
    ),
    "turret": EnemySpec(
        name="turret", kind="turret", tank="turret", max_hp=80, sight=20,
        biomes=("ruins",), weight=4,
    ),
    "heavy": EnemySpec(
        name="heavy tank", kind="heavy", tank="heavy", max_hp=200, sight=18,
        biomes=("plains", "forest", "desert", "ruins", "swamp"), weight=1,
        min_difficulty=0.15, preferred_range=(6.0, 12.0),
    ),
    "burrower": EnemySpec(
        name="burrower", kind="burrower", max_hp=60, sight=22,
        biomes=("desert",), weight=4, speed=6.5,
        damage=22, attack_radius=2.2, windup=0.7, cooldown=1.6, size_px=26,
    ),
    "puffer": EnemySpec(
        name="spore puffer", kind="puffer", max_hp=10, sight=18,
        biomes=("mushroom",), weight=5, speed=1.8,
        damage=30, attack_radius=2.6, windup=0.6, size_px=22,
    ),
    "warrior": EnemySpec(
        name="fallen warrior", kind="warrior", max_hp=50, sight=14,
        biomes=("plains", "forest"), weight=3, speed=4.2,
        damage=18, attack_radius=1.7, windup=0.45, cooldown=1.1, size_px=24,
    ),
}

# Enemies expected per chunk: ENEMY_BASE_DENSITY at the start, rising by
# ENEMY_DENSITY_PER_DIFFICULTY at full difficulty. Plains is calmer.
ENEMY_BASE_DENSITY = 0.35
ENEMY_DENSITY_PER_DIFFICULTY = 1.3
BIOME_ENEMY_DENSITY = {"plains": 0.6, "forest": 1.0, "desert": 1.0, "ruins": 1.3,
                       "swamp": 0.9, "mushroom": 1.1}
# No enemies spawn this close to the start.
ENEMY_FREE_RADIUS = 55
# Enemy hp and damage grow with difficulty by up to these fractions.
ENEMY_HP_SCALING = 0.5
ENEMY_DAMAGE_SCALING = 0.3
# Sleeping enemies wake once their spawn point is within this many tiles of
# the view (inside LOAD_MARGIN, so their chunk is always generated).
ENEMY_WAKE_MARGIN = 28
# Enemies farther than this outside the view are put back to sleep (they'll
# reappear at their spawn point when you return; killed ones stay dead).
# Must stay well inside UNLOAD_MARGIN, so an awake enemy never stands in (or
# probes into) a chunk that has been unloaded.
ENEMY_DESPAWN_MARGIN = 44
# Enemies more than this far outside the view are frozen (don't think or
# move) -- nobody can see them, and it saves CPU. Together with the local
# path search radius (ai/pathing.py, 12 tiles) this must stay inside
# LOAD_MARGIN, so thinking enemies only ever touch generated chunks.
ENEMY_ACTIVE_MARGIN = 16

# Awareness.
HEARING_RADIUS = 26          # your gunfire alerts enemies this close
FORGET_TIME = 6.0            # seconds searching your last known spot before giving up
REACTION_TIME = 0.35         # delay between spotting you and first shot
AIM_ERROR = 0.06             # radians of random aim error (vehicles)
FLEE_HP_FRACTION = 0.3       # tankettes/snipers retreat below this much hp
# Friendly fire is always on. An enemy only turns on another enemy once
# it has taken this fraction of its max hp from it.
INFIGHT_AGGRO_FRACTION = 0.35

# Heavy tanks crush destructible terrain they push against (hp per second).
HEAVY_CRUSH_DPS = 30

# --- Player ---------------------------------------------------------------------------

PLAYER_HIT_RADIUS = 1.0      # tiles, for enemy shells and blasts

# Collision: the hull is a rotated rectangle (hull_length_px x hull_width_px
# at its true heading). If a turn would push a corner into a wall, the tank
# is nudged up to this far (tiles) away from it; if no nudge fits, the turn
# waits. Makes turning next to walls feel like shoving rather than sticking.
TURN_NUDGE_MAX = 0.2

# --- Terrain durability --------------------------------------------------------------
# Hit points per destructible tile type (shell damage is in WEAPONS above).
# 0 = indestructible. Destroyed walls leave rubble, trees leave splinters;
# both are passable.

WALL_HP = 80         # 4 player shells
TREE_HP = 40         # trees and pines: 2 shells
CACTUS_HP = 20
MANGROVE_HP = 40
SHROOM_HP = 40

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
# Enemies turn constantly and nobody follows their barrels pixel by pixel:
# coarser steps mean far fewer new angles to bake while fighting.
ENEMY_HULL_ANGLE_STEPS = 90
ENEMY_TURRET_ANGLE_STEPS = 180
SHELL_ANGLE_STEPS = 90     # small sprites: a coarser step is invisible
FLASH_ANGLE_STEPS = 72

# Most sprite glyphs kept baked at once (rotated sprites are cached per angle,
# least recently used evicted first). ~1 KB each, twice (ours + engine cache).
SPRITE_GLYPH_BUDGET = 3000

# --- World (milestone 3) -------------------------------------------------------------

# "infinite": the procedurally generated world. "test": the hand-made test
# map with the shooting range (assets/maps/test_map.txt).
WORLD_MODE = "infinite"
TEST_MAP_FILE = "test_map.txt"   # under terminal_tank/assets/maps/

# None = a new random world every run (the seed is shown in the HUD); set a
# number to replay the same world.
SEED = None

# Chunks are CHUNK_SIZE x CHUNK_SIZE tiles (must be a power of two).
CHUNK_SIZE = 32
# Chunks are generated this many tiles beyond the edges of the view, so
# they're ready before they scroll in...
LOAD_MARGIN = 32
# ...and dropped from memory once this far outside the view (larger than
# LOAD_MARGIN so a chunk doesn't load/unload repeatedly at a border).
UNLOAD_MARGIN = 64
# Chunks are generated in the background with the time left over in each
# frame: up to CHUNK_BUILD_BUDGET_MS, but only while the frame's own work
# (update + drawing) stays under FRAME_TARGET_MS (leaving room for the
# engine to scale and present the frame within 60 fps). At least
# CHUNK_BUILD_MIN_MS is always spent, so generation never stalls.
CHUNK_BUILD_BUDGET_MS = 3.0
CHUNK_BUILD_MIN_MS = 0.5
FRAME_TARGET_MS = 13.0

# Start area: guaranteed open plains out to this many tiles from the spawn,
# and completely clear of obstacles within SPAWN_CLEAR_RADIUS.
SPAWN_PLAINS_RADIUS = 70
SPAWN_CLEAR_RADIUS = 6

# Difficulty rises from 0 at the spawn to 1 at this many tiles away
# (terrain gets rockier; milestone 4 scales enemies with it).
DIFFICULTY_RAMP_TILES = 1500

# Biome map: two broad noise fields ("heat" and "wetness") plus two patchy
# ones for the rarer biomes. Scales are in tiles: bigger = larger regions.
# Rules, checked in order: mushroom if SHROOM_FIELD > MUSHROOM_MIN; ruins if
# RUINS_FIELD > RUINS_MIN; swamp if wet > SWAMP_WET and heat > SWAMP_HEAT;
# forest if wet > FOREST_WET; desert if heat > DESERT_HEAT and wet < DESERT_DRY;
# otherwise plains.
BIOME_HEAT_SCALE = 260
BIOME_WET_SCALE = 220
BIOME_RARE_SCALE = 170
MUSHROOM_MIN = 0.74
RUINS_MIN = 0.72
SWAMP_WET = 0.62
SWAMP_HEAT = 0.42
FOREST_WET = 0.55
DESERT_HEAT = 0.56
DESERT_DRY = 0.5
# Wobble added to the biome fields by a small-scale noise (BIOME_BORDER_SCALE
# tiles), so borders are ragged, clumpy edges instead of smooth curves.
BIOME_BORDER_JITTER = 0.06
BIOME_BORDER_SCALE = 5

# Feature densities (chance per tile, or noise thresholds 0..1 on a local
# detail field). Obstacles that can't be destroyed (rock, mesa, water, bog)
# stay in small clumps so the tank can always drive around them.
DETAIL_SCALE = 11
LAKE_SCALE = 75
LAKE_MIN = 0.72              # lakes (plains/forest/mushroom) where the lake field is above this
PLAINS_TREE_CHANCE = 0.004
PLAINS_ROCK_CHANCE = 0.002
PLAINS_TALL_GRASS = 0.62     # detail field above this -> tall grass
PLAINS_FLOWER_CHANCE = 0.01
FOREST_PINE_MIN = 0.42       # detail field above this -> pine clusters...
FOREST_PINE_DENSITY = 0.7    # ...filled this densely
DESERT_DUNE_BAND = (0.55, 0.62)
DESERT_CACTUS_CHANCE = 0.012
DESERT_MESA_MIN = 0.8
SWAMP_BOG_MIN = 0.63
SWAMP_REED_MIN = 0.53
SWAMP_MANGROVE_CHANCE = 0.05
MUSHROOM_SHROOM_MIN = 0.58
MUSHROOM_SHROOM_DENSITY = 0.55
MUSHROOM_SPORE_CHANCE = 0.06
RUINS_BUILDINGS = (1, 3)     # buildings per ruins chunk (min, max)
RUINS_WALL_GAP_CHANCE = 0.18 # wall segments already collapsed
RUINS_RUBBLE_CHANCE = 0.12
