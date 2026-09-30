"""
config.py -- every tunable number in AsciiAdventurers, in one place.

Units:
  * distances are in WORLD TILES. One tile is drawn as 2 grid cells side by
    side (20x24 px with the default font), which is close to square, so the
    same number means the same on-screen distance horizontally and vertically.
  * times are in seconds, speeds in tiles/second, angles in radians unless a
    name says _DEG.
"""

import math

from .specs import CardSpec, CharacterSpec, EnemySpec, ShellSpec, WeaponSpec

# --- Display / layout --------------------------------------------------------

WINDOW_TITLE = "AsciiAdventurers"

# Grid cells per world tile, horizontally. Vertically a tile is always 1 row.
CELLS_PER_TILE = 2

# A world tile's size in pixels, used where game logic needs real on-screen
# proportions (collision boxes, aiming angles). Matches the default
# 10x24 px font cell.
TILE_PX_W = 20
TILE_PX_H = 24

# Sync frames to the monitor refresh (engine Display(vsync=...)): each frame
# is shown exactly once, which removes the periodic micro-stutter of a
# timer-paced loop. Falls back automatically where unsupported. This is the
# default for a new player; the Settings screen changes it.
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

# Rows reserved at the bottom of the screen for the HUD. 0: the HUD sits in
# the corners over the world (ui/hud.py), which fills the whole screen.
HUD_ROWS = 0

# --- Maps (ui/maps.py) ---
# Minimap: MINIMAP_COLS x MINIMAP_ROWS cells in the top-right corner (each
# cell shows 2 map pixels stacked), MINIMAP_TILES_PER_PIXEL tiles per map
# pixel -- so it covers COLS*k x ROWS*2*k tiles (28*5 x 16*5 = 140 x 80,
# vs. the screen's 86 x 27). MARGIN / MARGIN_TOP: cells from the edges.
MINIMAP_COLS = 28
MINIMAP_ROWS = 8
MINIMAP_TILES_PER_PIXEL = 5
MINIMAP_MARGIN = 1
MINIMAP_MARGIN_TOP = 0
# Big map (M): zooms from the whole island in to this many tiles per map
# pixel; each mouse-wheel notch zooms by MAP_ZOOM_STEP; WASD pans at
# MAP_PAN_SPEED map pixels per second (same on-screen speed at any zoom).
MAP_MIN_TILES_PER_PIXEL = 1.0
MAP_ZOOM_STEP = 1.25
MAP_PAN_SPEED = 60.0

# Largest step for things still paced by the real frame time (the big map's
# panning, menus).
MAX_DT = 0.05

# --- Simulation clock ----------------------------------------------------------
#
# The game world advances in fixed steps of 1/SIM_HZ seconds, however fast the
# screen refreshes: every machine computes the same steps from the same
# inputs (needed for online co-op, and for repeatable runs). Drawing happens
# every frame, blending positions between the last two steps, so motion stays
# smooth on 60, 120 or 144 Hz monitors alike.
SIM_HZ = 60
# After a long hitch (window drag, alt-tab), at most this many steps are run
# in one frame to catch up; the rest of the lost time is dropped, so the
# game slows down briefly instead of freezing to catch up.
MAX_STEPS_PER_FRAME = 5

# --- Players --------------------------------------------------------------------

# One color per player slot (map markers now; co-op HUDs later).
PLAYER_COLORS = [(255, 255, 255), (90, 200, 255), (255, 120, 200), (255, 210, 80)]
# Gamepad aiming: the aim point sits this many tiles out along the right stick.
PAD_AIM_DISTANCE = 7.0
# Enemies stay on the hero they're after unless another is this many tiles
# closer (stops them flip-flopping between two players at similar range).
TARGET_SWITCH_MARGIN = 4.0
# Debug ghost players (run.py --ghosts N): how far they see enemies to shoot.
GHOST_SIGHT = 14.0

# --- Camera -------------------------------------------------------------------

# How quickly the camera catches up with the hero, per second. Higher = tighter
# (hero stays closer to center); lower = floatier. 0 = locked to the hero.
CAMERA_FOLLOW_RATE = 8.0
# The camera never trails the hero by more than this many tiles.
CAMERA_MAX_LAG_TILES = 3.0

# --- Heroes & weapons ---------------------------------------------------------------
#
# Heroes, enemy bodies and weapons are data (see specs.py). START_HERO is
# the hero picked for a brand-new player (the new-run screen chooses after
# that, and remembers the choice). Sizes are
# canvas pixels: 1 tile = 20 x 24 px. Sprites are 14 x 18 pixel art
# (render/characters.py) drawn at `sprite_scale` screen px per pixel.
#
# Damage and hit points use one scale for everything (player, enemies, terrain).

WEAPONS = {
    # --- Hero weapons (one per hero; cards will upgrade them) -------------------
    # Rough damage per second against one target, for comparison: shock bolt
    # ~57 (+ jumps), longbow ~50 (+ pierce), rainbow up to ~80 point blank
    # (all 5 colors), sword ~71 (every enemy in the arc), lute ~13 (every
    # enemy around, automatically). Balance comes later.
    "shock_bolt": WeaponSpec(
        name="shock bolt", fire_interval=0.35,
        shell=ShellSpec(speed=34.0, damage=20, max_range=30.0, look="spark", sound="spark",
                        chain=2, chain_range=5.0, chain_falloff=0.7),
        blurb="lightning bolts that jump to 2 more enemies nearby",
    ),
    "longbow": WeaponSpec(
        name="longbow", fire_interval=0.4,
        shell=ShellSpec(speed=45.0, damage=16, max_range=40.0, look="longarrow", sound="bow",
                        pierce=2),
        blurb="fast, long-range arrows that pierce through 2 enemies",
    ),
    "rainbow": WeaponSpec(
        name="rainbow", fire_interval=0.5, pellets=5, spread_deg=34.0,
        shell=ShellSpec(speed=28.0, damage=8, max_range=13.0, look="prism", sound="chime"),
        blurb="a fan of 5 colors: deadly up close, weak far away",
    ),
    "sword": WeaponSpec(
        name="sword", kind="melee", fire_interval=0.42, damage=30, reach=5, arc_deg=150.0,
        blurb="a wide swing hitting everything in front; chops trees",
    ),
    "lute": WeaponSpec(
        name="lute", kind="pulse", fire_interval=1.2, damage=16, reach=8, auto=True,
        blurb="plays on its own: every beat hurts everything around",
    ),
    # The pre-M10 placeholder all heroes shared (kept for tests and tools).
    "magic_bolt": WeaponSpec(
        name="magic bolt",
        fire_interval=0.35,       # hold left click: ~3 shots/s
        shell=ShellSpec(speed=36.0, damage=20, max_range=30.0, look="bolt"),
    ),
    # Enemy weapons. Only the ogre's rocks damage terrain.
    "goblin_bow": WeaponSpec(
        name="goblin bow", fire_interval=1.6,
        shell=ShellSpec(speed=14.0, damage=8, max_range=22.0, damages_terrain=False,
                        look="arrow", sound="bow"),
    ),
    "hex": WeaponSpec(
        name="hex", fire_interval=3.5,
        shell=ShellSpec(speed=45.0, damage=30, max_range=45.0, damages_terrain=False,
                        look="hex", sound="hex"),
    ),
    "tower_orbs": WeaponSpec(
        name="tower orbs", fire_interval=2.4, burst=3, burst_gap=0.14,
        shell=ShellSpec(speed=17.0, damage=6, max_range=24.0, damages_terrain=False,
                        look="orb", sound="orb"),
    ),
    "boulder": WeaponSpec(
        name="boulder", fire_interval=2.8,
        shell=ShellSpec(speed=11.0, damage=25, max_range=24.0, damages_terrain=True,
                        look="boulder", sound="boulder"),
    ),
}

# The playable heroes: same body, each with their own weapon.
_HERO = dict(max_speed=8.5, accel=40.0, brake=50.0, size_px=26, max_hp=100)
HEROES = {
    "wizard": CharacterSpec(name="wizard", sprite="wizard", weapon="shock_bolt", **_HERO),
    "knight": CharacterSpec(name="knight", sprite="knight", weapon="sword", **_HERO),
    "bard": CharacterSpec(name="bard", sprite="bard", weapon="lute", **_HERO),
    "princess": CharacterSpec(name="princess", sprite="princess", weapon="rainbow", **_HERO),
    "huntress": CharacterSpec(name="huntress", sprite="huntress", weapon="longbow", **_HERO),
}
# Of a melee swing's reach, the part that also chops terrain (trees, walls):
# a sword clears what's right in front, not the whole arc.
MELEE_TERRAIN_REACH = 0.7
START_HERO = "wizard"

# Bodies of the enemies that shoot (their behaviour: ai/shooters.py).
BODIES = {
    "goblin_archer": CharacterSpec(
        name="goblin archer", weapon="goblin_bow", sprite="goblin", max_speed=5.5,
        accel=20.0, brake=30.0, size_px=24, aim_turn_speed=math.radians(160),
    ),
    "warlock": CharacterSpec(
        name="warlock", weapon="hex", sprite="warlock", max_speed=5.0,
        accel=16.0, brake=30.0, size_px=24, aim_turn_speed=math.radians(70),
    ),
    "ogre": CharacterSpec(
        name="ogre", weapon="boulder", sprite="ogre", max_speed=3.2,
        accel=8.0, brake=16.0, size_px=40, sprite_scale=4, hold_px=26,
        aim_turn_speed=math.radians(55),
        front_armor=0.35,         # hits on the side it faces do a third of the damage
    ),
    "spell_tower": CharacterSpec(
        name="spell tower", weapon="tower_orbs", sprite="tower", max_speed=0.0,
        accel=0.0, brake=0.0, size_px=40, sprite_scale=4, hold_px=10,
        aim_turn_speed=math.radians(60),
    ),
}

# --- Enemies ---------------------------------------------------------------------------
#
# Few but dangerous. Every enemy type is data here; its behaviour lives in
# ai/ (picked by `kind`). hp/damage share the damage scale above: the player
# has 100 hp and deals 20 per bolt.

ENEMIES = {
    "goblin_archer": EnemySpec(
        name="goblin archer", kind="archer", body="goblin_archer", max_hp=40, sight=16,
        biomes=("plains", "forest", "desert", "ruins", "swamp", "mushroom"), weight=3,
        preferred_range=(7.0, 11.0), xp=4,
    ),
    "warlock": EnemySpec(
        name="warlock", kind="warlock", body="warlock", max_hp=50, sight=34,
        biomes=("desert", "plains", "ruins"), weight=2,
        preferred_range=(18.0, 28.0),
        windup=1.1,               # aiming-beam time before the hex flies
        xp=8,
    ),
    "spell_tower": EnemySpec(
        name="spell tower", kind="tower", body="spell_tower", max_hp=80, sight=20,
        biomes=("ruins",), weight=4, xp=10,
    ),
    "ogre": EnemySpec(
        name="ogre", kind="ogre", body="ogre", max_hp=200, sight=18,
        biomes=("plains", "forest", "desert", "ruins", "swamp"), weight=1,
        preferred_range=(6.0, 12.0), xp=14,
    ),
    "burrower": EnemySpec(
        name="burrower", kind="burrower", max_hp=60, sight=22,
        biomes=("desert",), weight=4, speed=6.5,
        damage=22, attack_radius=2.2, windup=0.7, cooldown=1.6, size_px=26, xp=7,
    ),
    "puffer": EnemySpec(
        name="spore puffer", kind="puffer", max_hp=10, sight=18,
        biomes=("mushroom",), weight=5, speed=1.8,
        damage=30, attack_radius=2.6, windup=0.6, size_px=22, xp=3,
    ),
    "warrior": EnemySpec(
        name="fallen warrior", kind="warrior", max_hp=50, sight=14,
        biomes=("plains", "forest"), weight=3, speed=4.2,
        damage=18, attack_radius=1.7, windup=0.45, cooldown=1.1, size_px=24, xp=6,
    ),
}

# --- Experience (players/progress.py) ---------------------------------------------
# Each enemy's `xp` above goes to the player who lands the killing blow.
# XP from level n to n+1 = LEVEL_XP_BASE * LEVEL_XP_GROWTH ** (n - 1):
# 12, 16, 22, 30, 40, 54 ... Every level gained is one card pick.
LEVEL_XP_BASE = 12
LEVEL_XP_GROWTH = 1.35

# --- Cards (players/cards.py) ------------------------------------------------------
#
# Every level gained is one card pick: 3 cards are offered (drawn by rarity
# weight from those the hero can take and hasn't maxed), and you pick one
# with 1 / 2 / 3 (gamepad: d-pad left / up / right) while playing -- the
# game doesn't pause. Picks bank up if you're busy.
#
# mods: (stat, "add" | "mul", value), applied once per copy taken, adds
# before multiplies, on top of the hero's base stats. Stats:
#   damage        shot / swing / pulse damage
#   interval      seconds between attacks (mul 0.87 = attacks ~15% faster)
#   range         shot range, or swing / pulse reach
#   pellets, spread (degrees), pierce, chain, chain_range, chain_falloff,
#   shot_speed    shots only
#   arc           swing width (degrees, up to 360)
#   max_hp, move (movement speed), regen (hp per second), lifesteal
#   (fraction of damage dealt healed)
CARD_RARITY_WEIGHT = {"common": 10, "rare": 4, "epic": 1}
CARD_OFFER_SIZE = 3

CARDS = {
    # For everyone.
    "sharpened": CardSpec("Sharpened", "+20% damage", (("damage", "mul", 1.2),), max_stacks=5),
    "quick_hands": CardSpec("Quick Hands", "attack 15% faster", (("interval", "mul", 0.87),),
                            max_stacks=5),
    "iron_skin": CardSpec("Iron Skin", "+20 max HP", (("max_hp", "add", 20),), max_stacks=5),
    "swift_boots": CardSpec("Swift Boots", "move 10% faster", (("move", "mul", 1.1),)),
    "long_reach": CardSpec("Long Reach", "+20% range", (("range", "mul", 1.2),)),
    "second_wind": CardSpec("Second Wind", "regain 1 HP per second", (("regen", "add", 1.0),),
                            rarity="rare"),
    "vampiric": CardSpec("Vampiric", "heal 5% of damage dealt", (("lifesteal", "add", 0.05),),
                         rarity="rare"),
    # Any hero who shoots.
    "twin_shot": CardSpec("Twin Shot", "+1 projectile",
                          (("pellets", "add", 1), ("spread", "add", 8)), rarity="rare",
                          kinds=("shot",), heroes=("wizard", "huntress")),
    "piercing": CardSpec("Piercing", "shots pass through +1 enemy", (("pierce", "add", 1),),
                         kinds=("shot",)),
    "velocity": CardSpec("Velocity", "shots fly 25% faster", (("shot_speed", "mul", 1.25),),
                         max_stacks=2, kinds=("shot",)),
    # Wizard.
    "storm_caller": CardSpec("Storm Caller", "lightning jumps +1 more", (("chain", "add", 1),),
                             rarity="rare", heroes=("wizard",)),
    "conductor": CardSpec("Conductor", "jumps reach farther, fade less",
                          (("chain_range", "mul", 1.3), ("chain_falloff", "add", 0.08)),
                          heroes=("wizard",)),
    # Huntress.
    "volley": CardSpec("Volley", "+2 arrows in a fan",
                       (("pellets", "add", 2), ("spread", "add", 14)), rarity="epic",
                       max_stacks=2, heroes=("huntress",)),
    # Princess.
    "prism": CardSpec("Prism", "+2 colors in the fan",
                      (("pellets", "add", 2), ("spread", "add", 8)), rarity="rare",
                      heroes=("princess",)),
    "focus": CardSpec("Focus", "tighter fan, 25% more range",
                      (("spread", "mul", 0.7), ("range", "mul", 1.25)), max_stacks=2,
                      heroes=("princess",)),
    # Knight.
    "whirlwind": CardSpec("Whirlwind", "swing 60 degrees wider", (("arc", "add", 60),),
                          rarity="rare", max_stacks=4, heroes=("knight",)),
    "heavy_blade": CardSpec("Heavy Blade", "+35% damage, 10% slower",
                            (("damage", "mul", 1.35), ("interval", "mul", 1.1)),
                            heroes=("knight",)),
    # Bard.
    "crescendo": CardSpec("Crescendo", "the beat reaches 25% farther",
                          (("range", "mul", 1.25),), heroes=("bard",)),
    "encore": CardSpec("Encore", "+30% beat damage, +1.5 HP/s",
                       (("damage", "mul", 1.3), ("regen", "add", 1.5)), rarity="rare",
                       heroes=("bard",)),
}

# --- How many enemies, and which --------------------------------------------------
#
# The island is cut into chunks of 32 x 32 tiles (CHUNK_SIZE). One screen
# of the 172-column ultrawide grid shows 86 x 27 tiles, about 2.3 chunks.
#
# 1. HOW MANY. Each chunk gets
#        BIOME_ENEMY_DENSITY[biome at the chunk's centre] * ENEMY_DENSITY_MULTIPLIER
#    enemies on average: the whole part always spawns, the fraction is a
#    chance for one more. 1.3 -> one enemy, plus a 30% chance of a second;
#    0.35 -> a 35% chance of one. 0 -> none.
#
# 2. WHICH. Every enemy is rolled separately among the ENEMIES whose
#    `biomes` include that biome, in proportion to their `weight`: its
#    chance is weight / (sum of weights of all types allowed there). With
#    the numbers above, the plains roll goblin archer 3, warlock 2, ogre 1,
#    warrior 3 -> 33% / 22% / 11% / 33%. To make a type rarer or more
#    common, change its weight; to keep it out of a biome, remove the biome
#    from its `biomes`.
#
# 3. WHERE. Up to 12 random spots in the chunk are tried; each must be that
#    enemy's own biome, fit its body, and (spell towers) be next to a ruined
#    wall. If none works, that enemy is skipped -- so chunks on a biome
#    border, or towers in chunks with few walls, come out a bit sparser.
#    Nothing spawns within ENEMY_FREE_RADIUS of the start.
#
# 4. WHEN. Placement is fixed per seed. Enemies sleep until their spot
#    comes within ENEMY_WAKE_MARGIN tiles of the screen, and go back to
#    sleep (to wake again at their spot) past ENEMY_DESPAWN_MARGIN. Killed
#    enemies stay dead for the rest of the run.
#
# WHAT IT FEELS LIKE (measured: straight driving at top speed, 8.5 tiles/s,
# on the 172-column screen): density 1.0 wakes about 55-80 enemies per
# minute -- roughly one per chunk you pass near. Driving north/south sweeps
# a wider band than east/west (the screen is wider than tall), so meets
# more. With the values below: plains ~28/min, swamp ~52, forest ~59,
# mushroom ~72, desert ~77, ruins ~100. Doubling a density doubles its rate.
BIOME_ENEMY_DENSITY = {"plains": 0.35, "forest": 1.0, "desert": 1.0, "ruins": 1.3,
                       "swamp": 0.9, "mushroom": 1.1}
# Scales every biome at once (0.5 = half as many enemies everywhere).
ENEMY_DENSITY_MULTIPLIER = 1.0
# No enemies spawn within this many tiles of the start.
ENEMY_FREE_RADIUS = 55
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
AIM_ERROR = 0.06             # radians of random aim error (shooters)
FLEE_HP_FRACTION = 0.3       # archers/warlocks retreat below this much hp
# Friendly fire is always on. An enemy only turns on another enemy once
# it has taken this fraction of its max hp from it.
INFIGHT_AGGRO_FRACTION = 0.35

# Ogres smash destructible terrain they push against (hp per second).
OGRE_CRUSH_DPS = 30

# --- Player -------------------------------------------------------------------------

# Walk animation: steps per tile walked (each step is one frame of the
# 4-frame cycle in render/characters.py).
WALK_STEPS_PER_TILE = 2.5

# --- Terrain durability --------------------------------------------------------------
# Hit points per destructible tile type (shot damage is in WEAPONS above).
# 0 = indestructible. Destroyed walls leave rubble, trees leave splinters;
# both are passable.

WALL_HP = 80         # 4 bolts
TREE_HP = 40         # trees and pines: 2 bolts
CACTUS_HP = 20
MANGROVE_HP = 40
SHROOM_HP = 40

# --- Effects (seconds) ----------------------------------------------------------------

MUZZLE_FLASH_TIME = 0.07
IMPACT_TIME = 0.22
FIZZLE_TIME = 0.3          # a shot reaching max range: little dust puff
TILE_FLASH_TIME = 0.08     # a hit tile blinks bright
NUMBER_TIME = 0.7          # damage numbers float up for this long

# --- Sound ------------------------------------------------------------------------------

# Default loudness of synthesized effects relative to master volume (0..1);
# players change it in Settings ("Effects volume").
SFX_VOLUME = 0.5

# --- Rendering ------------------------------------------------------------------

# Screen pixels per sprite pixel (w, h). (1, 1) = smooth shapes; (2, 2) =
# chunky retro pixels that match the block glyphs. w must divide the cell
# width (10) and h the cell height (24).
SPRITE_PIXEL = (1, 1)

# Most rotated sprites kept baked at once (cached per angle, least recently
# used evicted first). A few KB each.
SPRITE_CACHE_SIZE = 600

# --- World ------------------------------------------------------------------------

# "island": the procedurally generated island (below). "test": the hand-made
# test map with the shooting range (assets/maps/test_map.txt).
WORLD_MODE = "island"
TEST_MAP_FILE = "test_map.txt"   # under ascii_adventurers/assets/maps/

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

# Terrain is drawn from cached pre-drawn blocks of TERRAIN_BLOCK_TILES x
# TERRAIN_BLOCK_TILES tiles (render/terrain.py). A block is 320 x 384 px
# (~0.5 MB); the full-width grid shows ~21 of them. Up to
# TERRAIN_CACHE_BLOCKS are kept (never fewer than two screens' worth of
# the view plus a one-block ring around it).
# The block size should divide CHUNK_SIZE.
TERRAIN_BLOCK_TILES = 16
TERRAIN_CACHE_BLOCKS = 64
# Blocks just outside the view pre-drawn per frame (~0.3 ms each).
TERRAIN_PREFETCH_BLOCKS = 2

# --- The island (milestone 5) ---
#
# The world is one big round island, Noita-style: open plains in the middle,
# the other five biomes as equal slices of a ring around them, then the
# coast, then ocean forever. Tiles are measured from the centre (0, 0),
# which is also where you start. Only the parts you drive near are ever
# generated, so the island's size costs no time or memory by itself.
#
# Radius of the island in tiles. At a hero's 8.5 tiles/s it's
# ~5 min of straight driving from the centre to the coast (radius / 8.5 / 60).
WORLD_RADIUS = 2550
# The coastline wanders in and out by up to this fraction of WORLD_RADIUS
# (fBm noise; COAST_SCALE is the size of its biggest bays and capes, and
# COAST_OCTAVES adds ever smaller wiggles down to ~COAST_SCALE / 2**(n-1)).
COAST_AMPLITUDE = 0.2
COAST_SCALE = 2400
COAST_OCTAVES = 6
# The central plains reach this fraction of WORLD_RADIUS, their edge
# wandering by PLAINS_EDGE_AMPLITUDE (fraction of the plains radius).
PLAINS_RADIUS_FRACTION = 0.2
PLAINS_EDGE_AMPLITUDE = 0.2
PLAINS_EDGE_SCALE = 900
# The ring: one equal slice per biome, in this order clockwise from east
# when the layout is fixed. BIOME_RING_SHUFFLE deals the biomes into the
# slices in a random (seeded) order each run; BIOME_RING_ROTATE turns the
# whole ring by a random angle. Set both False for the same layout every run.
BIOME_RING = ("forest", "desert", "ruins", "swamp", "mushroom")
BIOME_RING_SHUFFLE = True
BIOME_RING_ROTATE = True
# Slice borders bend by up to this angle (radians) either way, following a
# smooth noise field BIOME_WARP_SCALE tiles across, so they curve instead of
# being straight spokes.
BIOME_WARP = 0.3
BIOME_WARP_SCALE = 1600
# All borders (coast, plains edge, slices) also meander by up to
# BORDER_WOBBLE tiles following a smooth noise field BORDER_WOBBLE_SCALE
# tiles across (headlands, inlets, tongues of one biome into the next), and
# are made ragged by up to BIOME_BORDER_JITTER tiles of small-scale noise
# (BIOME_BORDER_SCALE tiles across), so they're clumpy edges rather than
# smooth curves.
BORDER_WOBBLE = 60.0
BORDER_WOBBLE_SCALE = 140
BIOME_BORDER_JITTER = 7.0
BIOME_BORDER_SCALE = 6
# Four regions out in the ocean, due N/E/S/W of the centre at this many
# island radii, are reserved for a later milestone. For now they're ocean.
CARDINAL_REGION_DISTANCE = 1.35

# Start: the tile nearest the centre (searched every SPAWN_SEARCH_STEP
# tiles) that isn't in a lake and has dry land connecting it to at least
# SPAWN_ESCAPE_RADIUS tiles away -- so you never start trapped by water.
# Completely clear of obstacles within SPAWN_CLEAR_RADIUS.
SPAWN_SEARCH_STEP = 8
SPAWN_ESCAPE_RADIUS = 80
SPAWN_CLEAR_RADIUS = 6

# Feature densities (chance per tile, or noise thresholds 0..1 on a local
# detail field). Obstacles that can't be destroyed (rock, mesa, water, bog)
# stay in small clumps so you can always walk around them.
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
