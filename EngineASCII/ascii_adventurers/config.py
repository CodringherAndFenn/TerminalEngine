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
from dataclasses import replace

from .specs import (BossPhase, BossSpec, CardSpec, CharacterSpec, EnemySpec, PactSpec, QuestSpec,
                    ShellSpec, SpellSpec, StatusSpec, UpgradeSpec, WeaponSpec)

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
    # Rough damage per second against one target, for comparison: arcane
    # missiles ~60 (all 3 darts on one enemy), longbow ~50 (+ pierce), rainbow up to ~80 point blank
    # (all 5 colors), throwing axes ~40 per leg (every enemy in the path, out
    # and back), lute ~13 (every enemy around, automatically). Balance comes later.
    # The wizard's since M20: 3 darts fan out, then each curves onto the
    # enemy nearest the reticle (see ShellSpec seek_*), so near misses land.
    "arcane_missiles": WeaponSpec(
        name="arcane missiles", fire_interval=0.45, pellets=3, spread_deg=50.0,
        shell=ShellSpec(speed=24.0, damage=9, max_range=22.0, look="dart", sound="bolt",
                        seek_turn=7.0, seek_after=2.0, seek_radius=6.0),
        blurb="3 arcane darts that fan out, then home on what you aim at",
        tags=("projectile", "arcane"),
    ),
    # The wizard's weapon until M20; now Chain Lightning's bolt (SPELL_SHELLS)
    # and kept for tests and tools.
    "shock_bolt": WeaponSpec(
        name="shock bolt", fire_interval=0.35,
        shell=ShellSpec(speed=34.0, damage=20, max_range=30.0, look="spark", sound="spark",
                        chain=2, chain_range=5.0, chain_falloff=0.7),
        blurb="lightning bolts that jump to 2 more enemies nearby",
        tags=("projectile", "lightning"),
    ),
    "longbow": WeaponSpec(
        name="longbow", fire_interval=0.4,
        shell=ShellSpec(speed=45.0, damage=16, max_range=40.0, look="longarrow", sound="bow",
                        pierce=2),
        blurb="fast, long-range arrows that pierce through 2 enemies",
        tags=("projectile", "physical"),
    ),
    "rainbow": WeaponSpec(
        name="rainbow", fire_interval=0.5, pellets=5, spread_deg=34.0,
        shell=ShellSpec(speed=28.0, damage=8, max_range=13.0, look="prism", sound="chime"),
        blurb="a fan of 5 colors: deadly up close, weak far away",
        tags=("projectile", "arcane"),
    ),
    "throwing_axe": WeaponSpec(
        name="throwing axes", fire_interval=0.55,
        shell=ShellSpec(speed=22.0, damage=22, max_range=11.0, look="axe", sound="axe",
                        returns=True),
        blurb="axes that cut through everything and come back",
        tags=("projectile", "physical"),
    ),
    # The knight's sword (no hero has it since the dwarf replaced the knight
    # on 2026-10-01; kept for a future extra weapon or boss, and for tests).
    "sword": WeaponSpec(
        name="sword", kind="melee", fire_interval=0.42, damage=30, reach=5, arc_deg=150.0,
        blurb="a wide swing hitting everything in front; chops trees",
        tags=("physical",),
    ),
    "lute": WeaponSpec(
        name="lute", kind="pulse", fire_interval=1.2, damage=16, reach=8, auto=True,
        blurb="plays on its own: every beat hurts everything around",
        tags=("area", "arcane"),
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
    # M12 enemies.
    "wisp_bolt": WeaponSpec(
        name="wisp bolt", fire_interval=1.3,
        shell=ShellSpec(speed=18.0, damage=5, max_range=20.0, damages_terrain=False,
                        look="wisp", sound="orb"),
    ),
    "acid_spit": WeaponSpec(
        name="acid spit", fire_interval=1.6, pellets=3, spread_deg=36.0,
        shell=ShellSpec(speed=9.0, damage=7, max_range=12.0, damages_terrain=False,
                        look="acid", sound="orb"),
    ),
    # M17: the psychedelic frogs' weaving spit (quest-only enemy).
    "psy_spit": WeaponSpec(
        name="psychedelic spit", fire_interval=1.4, pellets=2, spread_deg=24.0,
        shell=ShellSpec(speed=10.0, damage=8, max_range=16.0, damages_terrain=False,
                        look="wobble", sound="orb", wobble=0.45, wobble_tiles=3.0),
    ),
    "sand_fling": WeaponSpec(      # the dust devil's pellets (fired by its own AI)
        name="sand fling", fire_interval=1.8,
        shell=ShellSpec(speed=9.0, damage=5, max_range=10.0, damages_terrain=False,
                        look="sand", sound="fizzle"),
    ),
    "spore_ring": WeaponSpec(
        name="spore ring", fire_interval=2.2, pellets=8, spread_deg=315.0,   # 8 evenly all round
        shell=ShellSpec(speed=7.5, damage=6, max_range=14.0, damages_terrain=False,
                        look="spore", sound="orb"),
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
    "wizard": CharacterSpec(name="wizard", sprite="wizard", weapon="arcane_missiles", **_HERO),
    # The dwarf: a little slower, a little tougher.
    "dwarf": CharacterSpec(name="dwarf", sprite="dwarf", weapon="throwing_axe",
                           **dict(_HERO, max_speed=7.8, max_hp=120)),
    "bard": CharacterSpec(name="bard", sprite="bard", weapon="lute", **_HERO),
    "princess": CharacterSpec(name="princess", sprite="princess", weapon="rainbow", **_HERO),
    "huntress": CharacterSpec(name="huntress", sprite="huntress", weapon="longbow", **_HERO),
}
# Of a melee swing's reach, the part that also chops terrain (trees, walls):
# a sword clears what's right in front, not the whole arc.
MELEE_TERRAIN_REACH = 0.7
# A pulse (the bard's beat) also wears down walls, trees and other
# destructible tiles in its reach that it can "see", at this fraction of its
# damage to enemies.
PULSE_TERRAIN_FACTOR = 0.25
# Returning shots (the dwarf's axes, ShellSpec.returns): caught when they get
# this close to the thrower on the way back (tiles). One that hasn't made it
# back after RETURN_GIVE_UP x its range in total (a thrower outrunning it)
# drops.
RETURN_CATCH_RADIUS = 0.8
RETURN_GIVE_UP = 4.0
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
    "wisp": CharacterSpec(
        name="sentry wisp", weapon="wisp_bolt", sprite="wisp", max_speed=5.0,
        accel=12.0, brake=12.0, size_px=22, aim_turn_speed=math.radians(200), hold_px=10,
    ),
    "toad": CharacterSpec(
        name="bog toad", weapon="acid_spit", sprite="toad", max_speed=10.0,
        accel=80.0, brake=60.0, size_px=24, aim_turn_speed=math.radians(140), hold_px=14,
    ),
    "psyfrog": CharacterSpec(      # M17 (drawn in shifting colors, render/enemies_sprite.py)
        name="psychedelic frog", weapon="psy_spit", sprite="toad", max_speed=11.0,
        accel=80.0, brake=60.0, size_px=24, aim_turn_speed=math.radians(160), hold_px=14,
    ),
    "spitter": CharacterSpec(
        name="spore spitter", weapon="spore_ring", sprite="spitter", max_speed=0.0,
        accel=0.0, brake=0.0, size_px=30, hold_px=12,
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
    # M12. No ambushers: every one of these can be seen and hit from range.
    "dust_devil": EnemySpec(
        name="dust devil", kind="devil", max_hp=40, sight=16,
        biomes=("desert", "plains"), weight=2, speed=5.0,
        damage=5,            # the sting when it brushes you (every DEVIL_STING_INTERVAL)
        cooldown=1.8,        # seconds between sand spirals
        size_px=24, xp=6,
    ),
    "wisp": EnemySpec(
        name="sentry wisp", kind="wisp", body="wisp", max_hp=35, sight=18,
        biomes=("ruins",), weight=3, preferred_range=(7.0, 11.0), xp=7,
    ),
    "toad": EnemySpec(
        name="bog toad", kind="toad", body="toad", max_hp=45, sight=14,
        biomes=("swamp",), weight=4, preferred_range=(5.0, 9.0), xp=6,
    ),
    "spitter": EnemySpec(
        name="spore spitter", kind="spitter", body="spitter", max_hp=70, sight=13,
        biomes=("mushroom",), weight=3, xp=8,
    ),
    "boar": EnemySpec(
        name="thornback boar", kind="boar", max_hp=80, sight=16,
        biomes=("forest",), weight=3, speed=4.5,
        damage=22, attack_radius=9.0,   # charges from up to this far away
        windup=0.7, cooldown=1.8, size_px=28, xp=9,
    ),
    # M17: quest enemies and bosses. Empty `biomes`: the spawner never rolls
    # them -- the quest system (systems/quests.py) places them.
    "psy_frog": EnemySpec(
        name="psychedelic frog", kind="psyfrog", body="psyfrog", max_hp=110, sight=20,
        biomes=(), preferred_range=(8.0, 13.0), xp=25,
    ),
    "froggy": EnemySpec(
        name="Froggy McFrogface", kind="froggy", max_hp=6000, sight=400,
        biomes=(), size_px=96, xp=400,
    ),
}

# M12 enemy behaviour.
DEVIL_ORBIT = 3.5            # tiles: how close a dust devil circles you
DEVIL_SPIN_SPEED = 5.0       # radians/s it turns (the spiral of its flings follows)
DEVIL_PELLETS = 3            # sand pellets per fling, evenly round
DEVIL_STING_INTERVAL = 0.6   # seconds between stings while it touches you
WISP_SWEEP_SPEED = 1.1       # radians/s the searchlight's back-and-forth advances
WISP_SWEEP_DEG = 45          # how far either side of you the light swings
WISP_CONE_DEG = 22           # the light's width
WISP_LIGHT_RANGE = 12.0      # tiles the light reaches
WISP_LIT_INTERVAL = 0.22     # seconds between bolts while you're in the light
TOAD_HOP_TIME = 0.28         # seconds a leap lasts
TOAD_REST = (0.5, 1.1)       # seconds it sits between leaps
SPITTER_RING_TURN_DEG = 22.5 # each ring of spores is turned this much from the last
BOAR_CHARGE_SPEED = 14.0     # tiles/s
BOAR_CHARGE_TIME = 1.1       # longest charge, seconds
BOAR_DAZE_TIME = 1.3         # dazed after slamming into something
BOAR_WALL_DAMAGE = 40        # what the slam does to a tree or wall

# --- Experience (players/progress.py) ---------------------------------------------
# Each enemy's `xp` above drops as a gem where it falls (see XP gems below).
# XP from level n to n+1 = LEVEL_XP_BASE * LEVEL_XP_GROWTH ** (n - 1):
# 12, 16, 22, 30, 40, 54 ... Every level gained is one card pick.
LEVEL_XP_BASE = 12
LEVEL_XP_GROWTH = 1.35
MAX_LEVEL = 100

# Enemies get tougher as the players level up: an enemy waking up gets
# +ENEMY_HP_PER_LEVEL max HP and +ENEMY_DAMAGE_PER_LEVEL damage for every
# level above 1 of the highest-level human player (so at level 100: x3.48
# HP, x2.49 damage, times ENEMY_DAMAGE_MULTIPLIER). Enemies already awake
# keep what they woke with.
ENEMY_HP_PER_LEVEL = 0.025      # (was 0.03 before the 2026-09-30 difficulty cut)
ENEMY_DAMAGE_PER_LEVEL = 0.015  # (was 0.02)

# --- XP gems (entities/gems.py) ---------------------------------------------------
# A kill drops a gem worth the enemy's `xp` where it fell (kills by other
# monsters drop nothing). A hero whose pickup radius reaches a gem pulls it
# in: it flies to them, speeding up, and is collected on touch.
PICKUP_RADIUS = 1.5          # tiles, before Magnet cards
GEM_PULL_SPEED = (10.0, 32.0)   # tiles/s a pulled gem flies at: start, top
GEM_PULL_ACCEL = 60.0        # tiles/s^2
GEM_CATCH_RADIUS = 0.5       # collected this close to the hero
GEM_LIFETIME = 180.0         # seconds a gem lies there before fading away
GEM_MAX = 300                # more than this: the oldest merges into its nearest neighbour
GEM_TIERS = (10, 25)         # value below the first: small, below the second: medium, else big

# --- Cards (players/cards.py, players/stats.py; catalog: design/CARDS.md) ------------
#
# Every level gained is one card pick: CARD_OFFER_SIZE cards come up big in
# the middle of the screen (single player pauses). Each slot first rolls a
# rarity (CARD_RARITY_WEIGHT, shifted by luck), then a card that can appear
# at that rarity. Rerolls / banishes per run start at CARD_REROLLS /
# CARD_BANISHES (plus the Guild's upgrades); skipping is always allowed
# and heals SKIP_HEAL of max HP. Cards whose `unlock` isn't "start" are
# only offered once bought in the Guild Hall (or earned, "A:").
RARITIES = ("common", "uncommon", "rare", "epic", "legendary")
CARD_RARITY_WEIGHT = {"common": 100, "uncommon": 45, "rare": 18, "epic": 6, "legendary": 2}
# Each point of luck multiplies a rarity's weight by (1 + LUCK_STEP) once
# per step above common: 20 luck = rare x1.44, legendary x2.07.
LUCK_STEP = 0.01
CARD_OFFER_SIZE = 3
CARD_SYNERGY_WEIGHT = 1.5    # a card sharing a tag with your build is this much likelier
CARD_REROLLS = 3
CARD_BANISHES = 0
SKIP_HEAL = 0.15

# --- The stat layer (players/stats.py) -----------------------------------------------
BASE_CRIT_CHANCE = 0.05
BASE_CRIT_DAMAGE = 1.5
ARMOR_K = 40.0               # damage taken x (1 - a / (a + ARMOR_K)): 40 armor halves it
MAX_EVASION = 0.60          # passive chance to shrug off a hit (Nimble)
MAX_LIFESTEAL = 0.15
MAX_MOVE_BONUS = 0.80
MAX_AREA_BONUS = 2.0         # area x3 at most
MAX_SPELL_COOLDOWN = 0.60    # spells at most 60% faster
MIN_ATTACK_INTERVAL = 0.08   # fastest attack cadence any stack of cards can reach
STEADY_SPEED = 0.3           # tiles/s: below this the hero counts as standing still
SHIELD_RECHARGE_DELAY = 4.0  # seconds without being hit before a shield refills...
SHIELD_RECHARGE_RATE = 0.5   # ...at this fraction of its size per second

# --- Dodge roll (systems/roll.py, M18) ------------------------------------------------
# Shift / gamepad B or LB: a quick roll in the direction you walk (toward
# your aim when standing still). The hero is untouchable for the whole roll
# (shots, blasts and bodies pass through) but still stops at walls. A roll
# uses a charge; a spent charge comes back after ROLL_COOLDOWN s (one at a
# time, starting as soon as the roll does).
ROLL_DISTANCE = 4.0          # tiles
ROLL_TIME = 0.25             # seconds (also how long the i-frames last)
ROLL_COOLDOWN = 5.0          # seconds per charge
ROLL_CHARGES = 1
MAX_ROLL_COOLDOWN = 0.60     # Quick Recovery: charges at most 60% faster
ROLL_DUST_EVERY = 2          # simulation steps between dust puffs behind a roll
# Roll cards.
RIPOSTE_WINDOW = 1.5         # Riposte: the first attack this long after a roll start always crits
SLIPSTREAM = (0.30, 2.0)     # Slipstream: +move speed, for this many s after a roll
CLOSE_CALL = 0.1             # Close Call: s of cooldown back per enemy shot rolled through
TRAIL_SPACING = 0.8          # Scorched Trail / Prism Dash: tiles between trail patches...
TRAIL_RADIUS = 0.9           # ...each this big...
TRAIL_LIFE = 2.5             # ...lasting this long...
TRAIL_EVERY = 0.5            # ...applying its status this often
PRISM_DASH_STATUSES = ("burn", "chill", "poison", "shock")   # one at random per patch
BLINK = (5.0, 2.5, 20.0)     # Blink: teleport distance, shock nova radius, nova damage
BLINK_STEP = 0.25            # tiles: the teleport is checked against walls this finely
BACKFLIP = (5, 40.0, 0.6)    # Backflip: arrows, fan degrees, x damage each
SHOULDER_CHARGE = (25.0, 0.6, 2.5)   # Shoulder Charge: damage, reach past the body, push tiles
DROP_THE_BEAT = 1.5          # Drop the Beat: x damage of the free beat at the end of a roll

# Hero cards (catalog 6.2) and the rules they bring.
POINT_BLANK_RANGE = 4.0      # tiles (Point Blank)
SUPERCELL_BONUS = 0.25       # chain jumps vs shocked enemies (Supercell)
OVERLOAD_EVERY = 5           # every Nth attack is overloaded...
OVERLOAD_MULT = 3.0          # ...for this much damage (M20: no more extra jumps)
# Arcane missile cards (M20).
SEEKER = 2.0                 # Seeker: darts turn this much faster (and retarget)
RESONANCE = (1.0, 0.15, 4)   # Resonance: window s, +damage per dart in it, most darts counted
MANA_BURST = (1.0, 0.5)      # Mana Burst: radius, x the dart's damage to all others in it
ARCANE_STORM = (3, 8.0)      # Arcane Storm: new darts per cast at most, how far they look
ORBIT_REACH = 12.0           # Orbiting Darts: a missed dart looks this far round you
MARK_INTERVAL = 4.0          # Hunter's Mark picks a new target this often
MARK_MULT = 2.0
DISSONANCE_PUSH = 1.2        # tiles a beat pushes enemies back (Dissonance)
SPECTRUM_CHANCE = 0.20       # Spectrum: chance a color applies its status
# Spectrum: rainbow pellet color (palette.RAINBOW_SHOTS order) -> status.
SPECTRUM_STATUS = ("burn", None, "shock", "poison", "chill")
RICOCHET_BOUNCES = 2         # Ricochet: wall bounces before an axe turns home
VOLLEY_EVERY = 4             # Volley: every Nth shot...
VOLLEY_ARROWS = 5            # ...is this many arrows...
VOLLEY_SPREAD = 30.0         # ...fanned over this many degrees
CRESCENDO_STEP = 0.10        # Crescendo: per beat in a row that hits
CRESCENDO_MAX = 5
LULLABY_HEAL = (1, 5)        # Lullaby: HP per enemy a beat hits, at most this many
SYNCOPATION = ((0.6, 1.6), (1.3, 0.7))   # (reach, damage) of the loud / the soft beat
BALL_LIGHTNING_TIME = 2.0    # Ball Lightning: seconds a bolt crackles where it hit...
BALL_LIGHTNING_RADIUS = 1.5  # ...hitting everything this close...
BALL_LIGHTNING_EVERY = 0.25  # ...this often...
BALL_LIGHTNING_DAMAGE = 0.3  # ...for this fraction of the bolt's damage
REFRACTION_SPLIT = 3         # Refraction: a color that hits splits into this many...
REFRACTION_DAMAGE = 0.5      # ...each doing this fraction...
REFRACTION_SPREAD = 50.0     # ...fanned over this many degrees
GRAND_FINALE = (8, 4.0, 2.0) # Grand Finale: every Nth beat, x damage, x reach

# Conditionals, trade-offs, triggers (catalog 6.5-6.7).
UNTOUCHED_HP = 0.9
BLOODLUST_TIME = 10.0
BLOODLUST_MAX = 30
GIANT_SLAYER = 0.40
SPLIT_DAMAGE = 0.6           # Spray and Pray: each half of a split shot
SPLIT_SPREAD = 24.0          # degrees between the halves
FRENZY_TIME = 3.0            # Frenzy: seconds of double attack speed after a kill
BOUNTY_EVERY = 25            # Bounty: every Nth kill drops a cache...
HASTE_BOUNTY = 0.15          # ...and enemies are this much faster
BEACON_SPAWNS = 0.30         # Beacon: this many more enemies
VOLATILE_CHANCE = 0.15       # Volatile: kills explode this often...
VOLATILE_DAMAGE = 0.40       # ...for this fraction of the killing hit...
VOLATILE_RADIUS = 1.5        # ...this far
RETALIATION = (30, 2.5, 3.0, 1.5)   # damage, radius, cooldown s, push tiles
SURGE_HEAL = 0.20            # Surge: on level-up, heal this much...
SURGE_PUSH = (4.0, 3.0)      # ...and push enemies within 4 tiles 3 tiles away
ECHO_EVERY = 6               # Echo: every Nth attack happens twice...
ECHO_DELAY = 0.15            # ...this much later...
ECHO_ANGLE = 10.0            # ...turned this many degrees off the aim (left and right in turn)

# --- Multiple projectiles (M19) -------------------------------------------------------
# Every projectile beyond a weapon's own adds at least MIN_PELLET_GAP degrees
# to its fan (Multishot, Quiver, Volley, Twin Axes...), so extra shots always
# fan out visibly instead of flying as one line. A weapon's own fan (the
# rainbow's 5 colors over 34 degrees) is left as it is.
MIN_PELLET_GAP = 12.0
CROSS_FIRE_EVERY = 4         # Cross Fire: every Nth attack also goes off at 90/180/270 degrees
STARBURST = (10, 8)          # Starburst: every Nth attack, this many single shots all round
REAR_GUARD = 0.6             # Rear Guard: x damage of the shot fired behind you
SPIRAL_STEP = 37.0           # Spiral: degrees the extra shot turns further each attack
TWIN_LANES = (0.5, 0.65)     # Twin Lanes: tiles between the two lanes, x damage of each
DOUBLE_RAINBOW = (3, 0.08)   # Double Rainbow: every Nth shot, a 2nd fan this many s later
TWIN_AXES = (3, 30.0)        # Twin Axes: every Nth throw is 2 axes this many degrees apart
SHEET_MUSIC = 3              # Sheet Music: notes flung per beat (+1 per Multishot)...
SHEET_MUSIC_DAMAGE = 9.0     # ...each this much (hero buckets apply)...
SHEET_MUSIC_REACH = 12.0     # ...aimed at enemies this close (else spread all round)
GOLDEN_HOARD = (50, 0.50)    # +1% damage per this much loot, up to +50%
WILDFIRE = 0.30
SHATTER = (1.5, 2.0, 15)     # Shatter: x damage vs frozen; death burst radius, damage
THERMAL_SHOCK = (10, 2.0)    # damage per burn stack, radius
TOXIC_CURRENT = (2, 3.0)     # enemies the poison spreads to, how far
PANDEMIC = (2, 4.0)          # enemies an enemy's statuses spread to on death, how far
AEGIS_MAX = 0.5              # Aegis: shield from overhealing, up to this x max HP
JUGGERNAUT = 0.02            # +damage per armor
PHOENIX = (0.5, 3.0, 60)     # revive HP fraction, blast radius, blast damage
CAPSTONE_LEVEL = 15          # capstones are offered from this level on

# --- Statuses (systems/statuses.py) -----------------------------------------------
# Status damage is its own bucket (S): base x (1 + status damage) x (1 + tag
# damage); it never crits. Damage-over-time is dealt every STATUS_TICK s.
# Every status your cards give you is rolled on each hit: STATUS_BASE_CHANCE
# plus your status chance (Affliction).
STATUS_TICK = 0.5
STATUS_BASE_CHANCE = 0.10
STATUSES = {
    "burn": StatusSpec("burn", "fire", duration=3.0, max_stacks=5, dps=4.0),
    "poison": StatusSpec("poison", "poison", duration=6.0, max_stacks=5, dps=2.0),
    "bleed": StatusSpec("bleed", "physical", duration=4.0, max_stacks=5, dps=3.0),
    "chill": StatusSpec("chill", "frost", duration=3.0, max_stacks=5, slow=0.10),
    "shock": StatusSpec("shock", "lightning", duration=2.0, vulnerability=0.15),
}
FREEZE_TIME = 1.5            # 5 chill stacks: frozen solid this long (can't act)
VIRULENCE = (10, 1.5)        # Virulence: poison stacks up to, x duration

# --- Spells and items (systems/spells.py) ------------------------------------------
# Granted by cards; picking the card again levels the spell up (to 5).
SPELL_SLOTS = 3              # the Guild's Arcane Wing adds a 4th
SPELL_MAX_LEVEL = 5
SPELLS = {
    "daggers": SpellSpec(
        "Orbiting Daggers", "DAGGERS", "orbit", ("physical", "orbit"),
        base=dict(count=2, damage=12.0, radius=2.2, turn=3.4, rehit=0.5),
        levels=(("+1 dagger", (("count", "add", 1),)),
                ("+30% dagger damage", (("damage", "mul", 1.3),)),
                ("+1 dagger", (("count", "add", 1),)),
                ("wider and faster orbit", (("radius", "mul", 1.25), ("turn", "mul", 1.25)))),
        text="2 daggers circle you, 12 damage each"),
    "ember_aura": SpellSpec(
        "Ember Aura", "EMBER", "aura", ("fire", "area"),
        base=dict(radius=2.5, interval=0.5, stacks=1, inflicts="burn"),
        levels=(("+20% aura size", (("radius", "mul", 1.2),)),
                ("2 burn stacks per pulse", (("stacks", "add", 1),)),
                ("+20% aura size", (("radius", "mul", 1.2),)),
                ("pulses 30% faster", (("interval", "mul", 0.7),))),
        text="burns enemies within 2.5 tiles of you"),
    "frost_nova": SpellSpec(
        "Frost Nova", "NOVA", "nova", ("frost", "area"),
        base=dict(radius=4.0, interval=4.0, stacks=2, damage=8.0, inflicts="chill"),
        levels=(("15% faster", (("interval", "mul", 0.85),)),
                ("+25% nova size", (("radius", "mul", 1.25),)),
                ("+1 chill stack", (("stacks", "add", 1),)),
                ("double damage, 15% faster", (("damage", "mul", 2.0), ("interval", "mul", 0.85)))),
        text="every 4 s: chill everything within 4 tiles twice"),
    "spirit_wolf": SpellSpec(
        "Spirit Wolf", "WOLF", "wolf", ("summon", "physical"),
        base=dict(count=1, damage=15.0, bite=0.8, speed=9.0, sight=12.0),
        levels=(("+30% bite damage", (("damage", "mul", 1.3),)),
                ("+1 wolf", (("count", "add", 1),)),
                ("bites 25% faster", (("bite", "mul", 0.75),)),
                ("+1 wolf", (("count", "add", 1),))),
        text="a wolf hunts the nearest enemy, 15 damage bites"),
    "rune_trap": SpellSpec(
        "Rune Trap", "RUNES", "rune", ("arcane", "area"),
        base=dict(interval=3.0, damage=40.0, radius=1.5, trigger=0.9, life=12.0, max=5),
        levels=(("+30% rune damage", (("damage", "mul", 1.3),)),
                ("runes come 25% faster", (("interval", "mul", 0.75),)),
                ("+30% burst size", (("radius", "mul", 1.3),)),
                ("+3 runes at once, +30% damage", (("max", "add", 3), ("damage", "mul", 1.3)))),
        text="drops a rune every 3 s: it bursts for 40 when stepped on"),
    "poison_flask": SpellSpec(
        "Poison Flask", "FLASK", "flask", ("poison", "area"),
        base=dict(interval=3.0, radius=1.5, life=3.0, stacks=1, reach=10.0, flight=0.6,
                  inflicts="poison", count=1),
        # (M18: level 3 was "pools last 2 s longer", (("life", "add", 2.0),).)
        levels=(("+25% pool size", (("radius", "mul", 1.25),)),
                ("throws 2 flasks at once", (("count", "add", 1),)),
                ("thrown 25% faster", (("interval", "mul", 0.75),)),
                ("2 poison stacks per tick", (("stacks", "add", 1),))),
        text="lobs a flask at an enemy: a pool of poison for 3 s"),
    "storm_cloud": SpellSpec(
        "Storm Cloud", "STORM", "cloud", ("lightning", "area"),
        base=dict(interval=1.5, damage=20.0, reach=8.0, strikes=1, inflicts="shock"),
        levels=(("+30% strike damage", (("damage", "mul", 1.3),)),
                ("strikes 25% faster", (("interval", "mul", 0.75),)),
                ("2 strikes at a time", (("strikes", "add", 1),)),
                ("+40% damage, +30% reach", (("damage", "mul", 1.4), ("reach", "mul", 1.3)))),
        rarity="rare", text="a cloud follows you, striking and shocking an enemy every 1.5 s"),
    "healing_totem": SpellSpec(
        "Healing Totem", "TOTEM", "totem", ("summon",),
        base=dict(interval=12.0, heal=3.0, radius=3.0, life=6.0, chill=0, chill_every=1.0),
        # (M18: level 3 was "lasts 3 s longer", (("life", "add", 3.0),).)
        levels=(("+30% healing", (("heal", "mul", 1.3),)),
                ("also chills enemies near it", (("chill", "add", 1),)),
                ("planted 25% sooner", (("interval", "mul", 0.75),)),
                ("+40% healing, +30% size", (("heal", "mul", 1.4), ("radius", "mul", 1.3)))),
        rarity="rare", text="plants a totem every 12 s: 3 HP/s around it for 6 s"),
    "ward_charm": SpellSpec(
        "Ward Charm", "WARD", "ward", (),
        base=dict(shield=25.0),
        levels=(("+15 shield", (("shield", "add", 15.0),)),
                ("+15 shield", (("shield", "add", 15.0),)),
                ("+20 shield", (("shield", "add", 20.0),)),
                ("+25 shield", (("shield", "add", 25.0),))),
        text="a 25 HP shield that refills after 4 s unhurt"),
    "fire_wand": SpellSpec(
        "Fire Wand", "WAND", "wand", ("fire", "projectile"),
        base=dict(interval=1.2, damage=10.0, reach=12.0, stacks=1, inflicts="burn"),
        levels=(("+30% bolt damage", (("damage", "mul", 1.3),)),
                ("fires 25% faster", (("interval", "mul", 0.75),)),
                ("bolts burn twice", (("stacks", "add", 1),)),
                ("+40% damage, 20% faster", (("damage", "mul", 1.4), ("interval", "mul", 0.8)))),
        text="fires a burning bolt at the nearest enemy every 1.2 s"),
    "bone_turret": SpellSpec(
        "Bone Turret", "TURRET", "turret", ("summon", "projectile"),
        base=dict(count=1, interval=10.0, life=8.0, fire=0.5, damage=8.0, reach=10.0, pierce=0),
        # (M18: level 3 was "turrets last 4 s longer", (("life", "add", 4.0),).)
        levels=(("+30% bolt damage", (("damage", "mul", 1.3),)),
                ("bolts pierce +1 enemy", (("pierce", "add", 1),)),
                ("shoots 25% faster", (("fire", "mul", 0.75),)),
                ("2 turrets at a time", (("count", "add", 1),))),
        rarity="rare", text="places a turret every 10 s that shoots for 8 s"),
    "thorn_mail": SpellSpec(
        "Thorn Mail", "THORNS", "thorns", ("physical",),
        base=dict(flat=5.0, share=0.30),
        levels=(("+5 thorn damage", (("flat", "add", 5.0),)),
                ("+15% reflected", (("share", "add", 0.15),)),
                ("+10 thorn damage", (("flat", "add", 10.0),)),
                ("+25% reflected", (("share", "add", 0.25),))),
        text="attackers take 5 + 30% of the damage back"),
    # M20: the wizard's old shock bolt, now his spell (his card only). The
    # lightning cards (Storm Caller, Conductor, Supercell, Ball Lightning)
    # are offered once he has it and work on its bolts.
    "chain_lightning": SpellSpec(
        "Chain Lightning", "CHAIN", "chain", ("lightning", "projectile"),
        base=dict(interval=1.5, damage=20.0, reach=14.0, jumps=0),
        levels=(("+30% bolt damage", (("damage", "mul", 1.3),)),
                ("casts 25% faster", (("interval", "mul", 0.75),)),
                ("+1 jump", (("jumps", "add", 1),)),
                ("+40% damage, 20% faster", (("damage", "mul", 1.4), ("interval", "mul", 0.8)))),
        text="every 1.5 s a bolt at the nearest enemy, jumping to 2 more"),
    # M19: the huntress's own power (her card only; it takes a spell slot).
    # Passive: her arrows split on hitting (systems/combat._split_arrow).
    "split_arrow": SpellSpec(
        "Split Arrow", "SPLIT", "split_arrow", ("physical", "projectile"),
        base=dict(count=3, spread=40.0, damage=0.5, every=0),
        levels=(("+1 arrow in the split", (("count", "add", 1),)),
                ("+30% split damage", (("damage", "mul", 1.3),)),
                ("arrows split on every enemy they pass", (("every", "add", 1),)),
                ("+2 arrows, wider fan", (("count", "add", 2), ("spread", "add", 20.0)))),
        text="an arrow's first hit splits it into a fan of 3 (50% each)"),
}

# Shots that spells fire (damage comes from the spell's level).
SPELL_SHELLS = {
    # Chain Lightning's bolt (M20): the shock bolt's (damage from the spell).
    "chain": ShellSpec(speed=34.0, damage=0, max_range=16.0, damages_terrain=False,
                       look="spark", sound="spark", chain=2, chain_range=5.0, chain_falloff=0.7),
    # Sheet Music's notes (M19; damage comes from SHEET_MUSIC_DAMAGE).
    "note": ShellSpec(speed=20.0, damage=0, max_range=11.0, damages_terrain=False,
                      look="note", sound="pulse"),
    "wand": ShellSpec(speed=22.0, damage=0, max_range=14.0, damages_terrain=False,
                      look="ember", sound="spark"),
    "turret": ShellSpec(speed=26.0, damage=0, max_range=12.0, damages_terrain=False,
                        look="bone", sound="bolt"),
}

# Cards (design/CARDS.md rev 2). See specs.CardSpec for the fields and
# players/stats.py for the stats. "+X% damage" is always bucket A (they
# add up); "xN damage" is its own multiplier (rare and up only). Each
# plain stat is sold by exactly one card (the catalog's no-repeats rule).
_T = 5          # copies of a tiered generic card one hero can take
_CAP = dict(rarity="legendary", max_stacks=1, min_level=CAPSTONE_LEVEL, unlock="L:6000")


def _spell_card(key: str, code: str, unlock: str = "start") -> CardSpec:
    s = SPELLS[key]
    return CardSpec(s.name, "", ((key, "spell", 1),), rarity=s.rarity, max_stacks=SPELL_MAX_LEVEL,
                    tags=s.tags, unlock=unlock, code=code)


def _enabler(name: str, status: str, verb: str, tag: str, code: str) -> CardSpec:
    return CardSpec(name, f"10% of your hits {verb}", ((status, "status", 1),),
                    rarity="uncommon", max_stacks=1, tags=(tag,), code=code)


CARDS = {
    # --- 6.1 Generic stats (tiered: the number grows with the rarity rolled) ---
    "sharpened": CardSpec("Sharpened", "+{X}% damage", (("damage", "add", "X"),),
                          tiers=(10, 15, 22, 30, 40), max_stacks=_T, code="G01"),
    "quick_hands": CardSpec("Quick Hands", "+{X}% attack speed", (("attack_speed", "add", "X"),),
                            tiers=(8, 12, 17, 23, 30), max_stacks=_T, code="G02"),
    "iron_skin": CardSpec("Iron Skin", "+{X} max HP", (("max_hp", "add", "X"),),
                          tiers=(15, 25, 35, 50, 70), x_scale=1, max_stacks=_T, code="G03"),
    "swift_boots": CardSpec("Swift Boots", "+{X}% move speed", (("move", "add", "X"),),
                            tiers=(5, 8, 11, 15, 20), max_stacks=_T, code="G04"),
    "long_reach": CardSpec("Long Reach", "+{X}% range", (("range", "add", "X"),),
                           tiers=(10, 15, 20, 28, 35), max_stacks=_T, code="G05"),
    "keen_eye": CardSpec("Keen Eye", "+{X}% crit chance", (("crit_chance", "add", "X"),),
                         tiers=(3, 5, 7, 10, 14), max_stacks=_T, code="G06"),
    "brutal": CardSpec("Brutal", "+{X}% crit damage", (("crit_damage", "add", "X"),),
                       tiers=(15, 25, 35, 50, 70), max_stacks=_T, code="G07"),
    "broad_strokes": CardSpec("Broad Strokes", "+{X}% area", (("area", "add", "X"),),
                              tiers=(8, 12, 17, 23, 30), max_stacks=_T, code="G08"),
    # Lingering is only offered once something lasts (M18): a status, or a
    # spell whose things last (DURATION_SPELLS). Its old place in everyone's
    # pool went to the dodge roll cards (6.10).
    "lingering": CardSpec("Lingering", "+{X}% duration", (("duration", "add", "X"),),
                          tiers=(10, 15, 22, 30, 40), max_stacks=_T, needs=("duration",),
                          code="G09"),
    "thick_hide": CardSpec("Thick Hide", "+{X} armor", (("armor", "add", "X"),),
                           tiers=(3, 5, 8, 12, 16), x_scale=1, max_stacks=_T, code="G10"),
    "nimble": CardSpec("Nimble", "+{X}% evasion", (("evasion", "add", "X"),),
                       tiers=(3, 5, 7, 9, 12), max_stacks=_T, code="G11"),
    "second_wind": CardSpec("Second Wind", "regain {X} HP per second", (("regen", "add", "X"),),
                            tiers=(0.4, 0.7, 1, 1.5, 2), x_scale=1, max_stacks=_T, code="G12"),
    "vampiric": CardSpec("Vampiric", "heal {X}% of damage dealt", (("lifesteal", "add", "X"),),
                         tiers=(None, 1, 2, 3, 4), max_stacks=_T, code="G13"),
    "magnet": CardSpec("Magnet", "+{X}% pickup radius", (("pickup", "add", "X"),),
                       tiers=(20, 30, 45, 60, 80), max_stacks=_T, code="G14"),
    "scholar": CardSpec("Scholar", "+{X}% XP", (("xp", "add", "X"),),
                        tiers=(8, 12, 17, 23, 30), max_stacks=_T, code="G15"),
    "lucky_charm": CardSpec("Lucky Charm", "+{X} luck", (("luck", "add", "X"),),
                            tiers=(5, 8, 12, 16, 20), x_scale=1, max_stacks=_T, code="G16"),
    "piercing": CardSpec("Piercing", "shots pass through +1 enemy", (("pierce", "add", 1),),
                         rarity="uncommon", heroes=("wizard", "huntress", "princess"),
                         code="G17"),
    "potency": CardSpec("Potency", "+{X}% status damage", (("status_power", "add", "X"),),
                        tiers=(10, 15, 22, 30, 40), max_stacks=_T, needs=("status",),
                        code="G18"),
    "quickened": CardSpec("Quickened", "spells {X}% faster", (("spell_cooldown", "add", "X"),),
                          tiers=(6, 9, 12, 16, 20), max_stacks=_T, needs=("spell",),
                          code="G19"),
    # M19: for everyone with a projectile (Sheet Music's notes, Fire Wand
    # and Bone Turret count), in the pool from the start; the fan comes from
    # MIN_PELLET_GAP.
    "multishot": CardSpec("Multishot", "+1 projectile", (("pellets", "add", 1),),
                          rarity="rare", needs=("projectile",), tags=("projectile",),
                          code="G20"),
    "affliction": CardSpec("Affliction", "+{X}% chance for each of your statuses",
                           (("status_chance", "add", "X"),), tiers=(5, 8, 12, 16, 20),
                           max_stacks=_T, needs=("status",), code="G21"),
    # --- 6.2 Wizard (redone in M20 for the arcane missiles) ---
    # The lightning cards now upgrade Chain Lightning (his spell, W7) and are
    # only offered with it.
    "storm_caller": CardSpec("Storm Caller", "lightning jumps to +1 enemy", (("chain", "add", 1),),
                             rarity="rare", heroes=("wizard",), needs=("chain_lightning",),
                             tags=("lightning",), code="W1"),
    "conductor": CardSpec("Conductor", "jumps reach 30% farther and fade less",
                          (("chain_range", "add", 0.3), ("chain_falloff", "add", 0.08)),
                          heroes=("wizard",), needs=("chain_lightning",), tags=("lightning",),
                          code="W2"),
    "supercell": CardSpec("Supercell",
                          "bolts shock; jumps go for shocked enemies, +25% damage to them",
                          (("supercell", "flag", 1), ("shock", "source", 1)),
                          rarity="uncommon", max_stacks=1, heroes=("wizard",),
                          needs=("chain_lightning",), tags=("lightning",), code="W3"),
    "overload": CardSpec("Overload", "every 5th cast: x3 damage",
                         (("overload", "flag", 1),), rarity="rare", max_stacks=1,
                         heroes=("wizard",), tags=("arcane",), unlock="L:2000", code="W4"),
    # (Was the wizard's capstone; with lightning a spell it's an epic upgrade.)
    "ball_lightning": CardSpec("Ball Lightning",
                               "bolts crackle where they hit for 2 s, hurting all around",
                               (("ball_lightning", "flag", 1),), rarity="epic", max_stacks=1,
                               heroes=("wizard",), needs=("chain_lightning",),
                               tags=("lightning", "area"), unlock="L:6000", code="W5"),
    "chain_lightning": replace(_spell_card("chain_lightning", "W7"), heroes=("wizard",)),
    "seeker": CardSpec("Seeker", "darts turn twice as fast and find a new target",
                       (("seeker", "flag", 1),), max_stacks=1, heroes=("wizard",),
                       tags=("arcane",), code="W8"),
    "resonance": CardSpec("Resonance", "darts on one enemy within 1 s: +15% each, up to +60%",
                          (("resonance", "flag", 1),), rarity="uncommon", max_stacks=1,
                          heroes=("wizard",), tags=("arcane",), code="W9"),
    "mana_burst": CardSpec("Mana Burst", "darts burst on hit: 50% to all within 1 tile",
                           (("mana_burst", "flag", 1),), rarity="rare", max_stacks=1,
                           heroes=("wizard",), tags=("arcane", "area"), code="W10"),
    "arcane_storm": CardSpec("Arcane Storm", "a dart that kills fires a new one (3 per cast)",
                             (("arcane_storm", "flag", 1),), heroes=("wizard",),
                             tags=("arcane",), code="W11", **_CAP),
    "orbiting_darts": CardSpec("Orbiting Darts", "darts that miss swing round you and try again",
                               (("orbiting_darts", "flag", 1),), rarity="rare", max_stacks=1,
                               heroes=("wizard",), tags=("arcane", "projectile"), code="W12"),
    # --- Dwarf ---
    "ricochet": CardSpec("Ricochet", "axes bounce off walls and fly on (2 bounces)",
                         (("ricochet", "flag", 1),), rarity="rare", max_stacks=1,
                         heroes=("dwarf",), tags=("projectile",), code="D1"),
    "heavy_axe": CardSpec("Heavy Axe", "x1.35 damage, attacks 10% slower",
                          (("damage_mult", "mul", 1.35), ("interval_mult", "mul", 1.1)),
                          rarity="rare", heroes=("dwarf",), tags=("physical",), code="D2"),
    "homeward_fury": CardSpec("Homeward Fury", "axes deal +50% on the way back",
                              (("homeward", "add", 0.5),), max_stacks=2, heroes=("dwarf",),
                              code="D3"),
    "cleave": CardSpec("Cleave", "axes make enemies bleed",
                       (("cleave", "flag", 1), ("bleed", "source", 1)), rarity="uncommon",
                       max_stacks=1, heroes=("dwarf",), tags=("physical",), code="D4"),
    "cyclone": CardSpec("Cyclone", "a caught axe flies straight back out at the nearest enemy",
                        (("cyclone", "flag", 1),), heroes=("dwarf",), tags=("physical",),
                        code="D5", **_CAP),
    # --- Huntress ---
    "volley": CardSpec("Volley", "every 4th shot looses 5 arrows in a fan",
                       (("volley", "flag", 1),), rarity="epic", max_stacks=1,
                       heroes=("huntress",), tags=("projectile",), code="H1"),
    "broadhead": CardSpec("Broadhead", "+15% damage for each enemy the arrow has passed",
                          (("broadhead", "add", 0.15),), rarity="uncommon",
                          heroes=("huntress",), tags=("physical",), code="H2"),
    "hunters_mark": CardSpec("Hunter's Mark",
                             "every 4 s the toughest enemy in view is marked: x2 damage from you",
                             (("hunters_mark", "flag", 1),), rarity="rare", max_stacks=1,
                             heroes=("huntress",), unlock="L:2000", code="H3"),
    "steady_aim": CardSpec("Steady Aim", "+25% crit chance while standing still",
                           (("steady_crit", "add", 0.25),), rarity="uncommon", max_stacks=2,
                           heroes=("huntress",), code="H4"),
    "deadeye": CardSpec("Deadeye", "crits pierce every enemy and fly twice as far",
                        (("deadeye", "flag", 1),), heroes=("huntress",), code="H5", **_CAP),
    # --- Princess ---
    "prism": CardSpec("Prism", "colors hitting the same enemy: +20% for each other color",
                      (("prism", "add", 0.2),), rarity="rare", heroes=("princess",),
                      tags=("projectile",), code="P1"),
    "focus": CardSpec("Focus", "the fan narrows by 30%", (("spread_mult", "mul", 0.7),),
                      max_stacks=2, heroes=("princess",), code="P2"),
    "spectrum": CardSpec("Spectrum",
                         "red burns, blue chills, green poisons, yellow shocks (20%)",
                         (("spectrum", "flag", 1), ("burn", "source", 1), ("chill", "source", 1),
                          ("poison", "source", 1), ("shock", "source", 1)),
                         rarity="rare", max_stacks=1, heroes=("princess",),
                         tags=("fire", "frost", "poison", "lightning"), unlock="L:2500",
                         code="P3"),
    "point_blank": CardSpec("Point Blank", "+40% damage to enemies within 4 tiles",
                            (("point_blank", "add", 0.4),), rarity="uncommon", max_stacks=2,
                            heroes=("princess",), code="P4"),
    "refraction": CardSpec("Refraction", "each color splits into 3 when it hits an enemy",
                           (("refraction", "flag", 1),), heroes=("princess",),
                           tags=("projectile",), code="P5", **_CAP),
    # --- Bard ---
    "crescendo": CardSpec("Crescendo", "each beat in a row that hits: +10% damage, up to +50%",
                          (("crescendo", "flag", 1),), max_stacks=1, heroes=("bard",),
                          tags=("area",), code="B1"),
    "lullaby": CardSpec("Lullaby", "each beat heals you 1 HP per enemy it hits (up to 5)",
                        (("lullaby", "flag", 1),), rarity="rare", max_stacks=1,
                        heroes=("bard",), code="B2"),
    "syncopation": CardSpec("Syncopation",
                            "beats alternate: short and loud (x1.6), wide and soft (x0.7)",
                            (("syncopation", "flag", 1),), rarity="uncommon", max_stacks=1,
                            heroes=("bard",), tags=("area",), code="B3"),
    "dissonance": CardSpec("Dissonance", "beats push enemies back and chill them",
                           (("dissonance", "flag", 1), ("chill", "source", 1)),
                           rarity="uncommon", max_stacks=1, heroes=("bard",),
                           tags=("frost",), unlock="L:1500", code="B4"),
    "grand_finale": CardSpec("Grand Finale", "every 8th beat: x4 damage, x2 reach",
                             (("grand_finale", "flag", 1),), heroes=("bard",), tags=("area",),
                             code="B5", **_CAP),
    # --- 6.3 Tags and statuses ---
    "kindling": _enabler("Kindling", "burn", "burn", "fire", "T01"),
    "wildfire": CardSpec("Wildfire", "+30% damage to burning enemies", (("wildfire", "add", 0.3),),
                         rarity="uncommon", max_stacks=1, needs=("burn",), tags=("fire",),
                         code="T02"),
    "venom": _enabler("Venom", "poison", "poison", "poison", "T03"),
    "virulence": CardSpec("Virulence", "poison stacks to 10 and lasts 50% longer",
                          (("virulence", "flag", 1),), rarity="rare", max_stacks=1,
                          needs=("poison",), tags=("poison",), unlock="L:2000", code="T04"),
    "frostbite": _enabler("Frostbite", "chill", "chill", "frost", "T05"),
    "shatter": CardSpec("Shatter", "frozen enemies take x1.5 damage and burst into ice on death",
                        (("shatter", "flag", 1),), rarity="rare", max_stacks=1,
                        needs=("chill",), tags=("frost",), unlock="L:2500", code="T06"),
    "static": _enabler("Static", "shock", "shock", "lightning", "T07"),
    "serrated": _enabler("Serrated", "bleed", "bleed", "physical", "T08"),
    "hemorrhage": CardSpec("Hemorrhage", "bleeding hurts twice as fast while the enemy moves",
                           (("hemorrhage", "flag", 1),), rarity="rare", max_stacks=1,
                           needs=("bleed",), tags=("physical",), unlock="L:2000", code="T09"),
    "elementalist": CardSpec("Elementalist", "+{X}% fire, frost, poison and lightning damage",
                             (("tag:fire", "add", "X"), ("tag:frost", "add", "X"),
                              ("tag:poison", "add", "X"), ("tag:lightning", "add", "X")),
                             tiers=(10, 15, 22, 30, 40), max_stacks=_T,
                             needs=("element",), code="T10"),
    "arcane_mastery": CardSpec("Arcane Mastery", "+{X}% arcane damage",
                               (("tag:arcane", "add", "X"),), tiers=(10, 15, 22, 30, 40),
                               max_stacks=_T, needs=("arcane",), tags=("arcane",), code="T11"),
    "weapons_master": CardSpec("Weapons Master", "+{X}% physical damage",
                               (("tag:physical", "add", "X"),), tiers=(10, 15, 22, 30, 40),
                               max_stacks=_T, needs=("physical",), tags=("physical",),
                               code="T12"),
    "thermal_shock": CardSpec("Thermal Shock",
                              "burning and chilled enemies explode (10 per burn stack)",
                              (("thermal_shock", "flag", 1),), rarity="epic", max_stacks=1,
                              needs=("burn", "chill"), tags=("fire", "frost"), unlock="L:3500",
                              code="T13"),
    "toxic_current": CardSpec("Toxic Current", "shocking a poisoned enemy spreads its poison to 2",
                              (("toxic_current", "flag", 1),), rarity="epic", max_stacks=1,
                              needs=("shock", "poison"), tags=("lightning", "poison"),
                              unlock="L:3500", code="T14"),
    # --- 6.4 Spells (the first copy grants it, the next ones level it up) ---
    "daggers": _spell_card("daggers", "S01"),
    "ember_aura": _spell_card("ember_aura", "S02"),
    "frost_nova": _spell_card("frost_nova", "S03"),
    "spirit_wolf": _spell_card("spirit_wolf", "S04"),
    "rune_trap": _spell_card("rune_trap", "S05"),
    "poison_flask": _spell_card("poison_flask", "S06"),
    "storm_cloud": _spell_card("storm_cloud", "S07", "L:2500"),
    "healing_totem": _spell_card("healing_totem", "S08", "L:2500"),
    "ward_charm": _spell_card("ward_charm", "S09", "L:1000"),
    "fire_wand": _spell_card("fire_wand", "S10"),
    "bone_turret": _spell_card("bone_turret", "S11", "L:2500"),
    "thorn_mail": _spell_card("thorn_mail", "S12"),
    # --- 6.5 Conditional and scaling ---
    "untouched": CardSpec("Untouched", "+30% damage while above 90% HP",
                          (("untouched", "add", 0.3),), rarity="uncommon", max_stacks=1,
                          code="C01"),
    "berserker": CardSpec("Berserker", "+1% damage for every 1% of HP you're missing",
                          (("berserker", "flag", 1),), rarity="rare", max_stacks=1,
                          unlock="L:2000", code="C02"),
    "bulwark": CardSpec("Bulwark", "+1% damage per 10 max HP", (("bulwark", "flag", 1),),
                        rarity="rare", max_stacks=1, unlock="L:2000", code="C03"),
    "momentum": CardSpec("Momentum", "+damage equal to half your move speed bonus",
                         (("momentum", "flag", 1),), rarity="uncommon", max_stacks=1,
                         code="C04"),
    "fleet_strike": CardSpec("Fleet Strike", "+1% crit chance per 4% move speed bonus",
                             (("fleet_strike", "flag", 1),), rarity="rare", max_stacks=1,
                             unlock="L:2000", code="C05"),
    "bloodlust": CardSpec("Bloodlust", "each kill: +1% damage for 10 s (up to +30%)",
                          (("bloodlust", "flag", 1),), rarity="uncommon", max_stacks=1,
                          code="C06"),
    "giant_slayer": CardSpec("Giant Slayer", "+40% damage to enemies with more max HP than you",
                             (("giant_slayer", "flag", 1),), rarity="uncommon", max_stacks=1,
                             code="C07"),
    "veteran": CardSpec("Veteran", "+1% damage per level", (("veteran", "flag", 1),),
                        rarity="rare", max_stacks=1, unlock="L:1500", code="C08"),
    # --- 6.6 Trade-offs ---
    "glass_cannon": CardSpec("Glass Cannon", "x1.4 damage, -30% max HP",
                             (("damage_mult", "mul", 1.4), ("max_hp_mult", "mul", 0.7)),
                             rarity="rare", max_stacks=1, unlock="L:2000", code="X01"),
    "heavy_plate": CardSpec("Heavy Plate", "no hit takes over 10% of your max HP; -15% move",
                            (("hit_cap", "flag", 1), ("move", "add", -0.15)),
                            rarity="uncommon", max_stacks=1, code="X02"),
    "spray_and_pray": CardSpec("Spray and Pray", "shots split in two at half range; -25% range",
                               (("split", "flag", 1), ("range", "add", -0.25)), rarity="rare",
                               max_stacks=1, kinds=("shot",), tags=("projectile",), code="X03"),
    "frenzy": CardSpec("Frenzy", "attack twice as fast for 3 s after a kill; -20% range",
                       (("frenzy", "flag", 1), ("range", "add", -0.2)), rarity="uncommon",
                       max_stacks=1, code="X04"),
    "bounty": CardSpec("Bounty", "every 25th kill drops a loot cache; enemies 15% faster",
                       (("bounty", "flag", 1),), rarity="rare", max_stacks=1, code="X05"),
    "beacon": CardSpec("Beacon", "30% more enemies come for you", (("beacon", "flag", 1),),
                       rarity="rare", max_stacks=1, unlock="L:2000", code="X06"),
    # --- 6.7 Triggers ---
    "volatile": CardSpec("Volatile", "kills have a 15% chance to explode",
                         (("volatile", "flag", 1),), rarity="uncommon", max_stacks=1,
                         tags=("area",), code="R01"),
    "chain_reaction": CardSpec("Chain Reaction", "enemies killed by an explosion explode too",
                               (("chain_reaction", "flag", 1),), rarity="rare", max_stacks=1,
                               needs=("volatile",), tags=("area",),
                               unlock="A:chain_reaction", code="R02"),
    "retaliation": CardSpec("Retaliation", "when hit: a shockwave deals 30 and pushes (3 s)",
                            (("retaliation", "flag", 1),), rarity="uncommon", max_stacks=1,
                            code="R03"),
    "soul_harvest": CardSpec("Soul Harvest", "kills heal 1 HP", (("soul_harvest", "add", 1),),
                             max_stacks=3, code="R04"),
    "surge": CardSpec("Surge", "level-ups heal 20% and blast enemies away",
                      (("surge", "flag", 1),), rarity="uncommon", max_stacks=1,
                      unlock="L:1000", code="R05"),
    "echo": CardSpec("Echo", "every 6th attack happens twice", (("echo", "flag", 1),),
                     rarity="uncommon", max_stacks=1, code="R06"),
    # --- 6.8 Economy ---
    "prospector": CardSpec("Prospector", "+{X}% loot", (("loot", "add", "X"),),
                           tiers=(10, 15, 22, 30, 40), max_stacks=_T, code="E01"),
    "fortune": CardSpec("Fortune", "+1 card in every offer", (("offer_size", "add", 1),),
                        rarity="epic", max_stacks=1, unlock="L:3500", code="E02"),
    "golden_hoard": CardSpec("Golden Hoard", "+1% damage per 50 loot this run (up to +50%)",
                             (("golden_hoard", "flag", 1),), rarity="rare", max_stacks=1,
                             unlock="L:2500", code="E03"),
    # --- 6.9 Capstones and rule-breakers ---
    "overflow": CardSpec("Overflow", "crit chance over 100% becomes double crit damage",
                         (("overflow", "flag", 1),), needs=("stat:crit_chance",), code="K01",
                         **dict(_CAP, unlock="A:crit_75")),
    "pandemic": CardSpec("Pandemic", "a dying enemy's statuses spread to 2 nearby",
                         (("pandemic", "flag", 1),), needs=("status",), code="K02", **_CAP),
    "aegis": CardSpec("Aegis", "healing past full HP becomes shield (up to half your HP)",
                      (("aegis", "flag", 1),), needs=("heal",), code="K03", **_CAP),
    "pack_leader": CardSpec("Pack Leader", "summons use your crits and statuses; +1 of each",
                            (("pack_leader", "flag", 1),), needs=("summon",), tags=("summon",),
                            code="K04", **_CAP),
    "juggernaut": CardSpec("Juggernaut", "+2% damage per armor; you can't evade",
                           (("juggernaut", "flag", 1),), needs=("stat:armor",), code="K05",
                           **_CAP),
    "phoenix": CardSpec("Phoenix", "once per run: rise again at 50% HP in a burst of fire",
                        (("phoenix", "add", 1),), code="K06", **dict(_CAP, unlock="A:level_30")),
    # --- 6.10 Dodge roll (M18; the roll itself: systems/roll.py) ---
    "quick_recovery": CardSpec("Quick Recovery", "rolls recharge {X}% faster",
                               (("roll_cooldown", "add", "X"),), tiers=(8, 12, 16, 20, 25),
                               max_stacks=_T, tags=("roll",), code="V01"),
    "extra_roll": CardSpec("Extra Roll", "+1 roll charge", (("roll_charges", "add", 1),),
                           rarity="rare", max_stacks=1, tags=("roll",), code="V02"),
    "riposte": CardSpec("Riposte", "your first attack after a roll always crits",
                        (("riposte", "flag", 1),), rarity="uncommon", max_stacks=1,
                        tags=("roll",), code="V03"),
    "slipstream": CardSpec("Slipstream", "+30% move speed for 2 s after a roll",
                           (("slipstream", "flag", 1),), rarity="uncommon", max_stacks=1,
                           tags=("roll",), code="V04"),
    "close_call": CardSpec("Close Call", "each shot you roll through: 0.1 s off the cooldown",
                           (("close_call", "flag", 1),), rarity="uncommon", max_stacks=1,
                           tags=("roll",), code="V05"),
    "scorched_trail": CardSpec("Scorched Trail", "rolls leave a trail of fire that burns",
                               (("scorched_trail", "flag", 1), ("burn", "source", 1)),
                               rarity="uncommon", max_stacks=1, tags=("roll", "fire"),
                               code="V06"),
    # One per hero: each hero's roll gets a trick of its own.
    "blink": CardSpec("Blink", "your roll is a teleport ending in a shocking nova",
                      (("blink", "flag", 1), ("shock", "source", 1)), rarity="uncommon",
                      max_stacks=1, heroes=("wizard",), tags=("roll", "lightning"), code="W6"),
    "shoulder_charge": CardSpec("Shoulder Charge", "rolling into enemies hits and knocks them back",
                                (("shoulder_charge", "flag", 1),), rarity="uncommon",
                                max_stacks=1, heroes=("dwarf",), tags=("roll", "physical"),
                                code="D6"),
    "backflip": CardSpec("Backflip", "rolling looses 5 arrows at your aim",
                         (("backflip", "flag", 1),), rarity="uncommon", max_stacks=1,
                         heroes=("huntress",), tags=("roll", "projectile"), code="H6"),
    "prism_dash": CardSpec("Prism Dash", "rolls leave a rainbow: each patch a random status",
                           (("prism_dash", "flag", 1),
                            *((s, "source", 1) for s in PRISM_DASH_STATUSES)),
                           rarity="uncommon", max_stacks=1, heroes=("princess",),
                           tags=("roll",), code="P6"),
    "drop_the_beat": CardSpec("Drop the Beat", "a free x1.5 beat as each roll ends",
                              (("drop_the_beat", "flag", 1),), rarity="uncommon", max_stacks=1,
                              heroes=("bard",), tags=("roll", "area"), code="B6"),
    # --- 6.11 Projectile patterns (M19): every hero whose attack shoots, the
    # bard through Sheet Music ("shots" gate) ---
    "cross_fire": CardSpec("Cross Fire", "every 4th attack also fires sideways and behind",
                           (("cross_fire", "flag", 1),), rarity="uncommon", max_stacks=1,
                           needs=("shots",), tags=("projectile",), code="M01"),
    "starburst": CardSpec("Starburst", "every 10th attack: 8 shots all around you",
                          (("starburst", "flag", 1),), rarity="rare", max_stacks=1,
                          needs=("shots",), tags=("projectile",), code="M02"),
    "rear_guard": CardSpec("Rear Guard", "every attack also fires a shot behind you (60%)",
                           (("rear_guard", "flag", 1),), rarity="uncommon", max_stacks=1,
                           needs=("shots",), tags=("projectile",), code="M03"),
    "spiral": CardSpec("Spiral", "an extra shot each attack, turning further around you",
                       (("spiral", "flag", 1),), rarity="uncommon", max_stacks=1,
                       needs=("shots",), tags=("projectile",), code="M04"),
    "twin_lanes": CardSpec("Twin Lanes", "every shot flies as two side by side (65% each)",
                           (("twin_lanes", "flag", 1),), rarity="rare", max_stacks=1,
                           needs=("shots",), tags=("projectile",), code="M05"),
    # Hero projectile cards (the wizard's is Orbiting Darts, W12, with his cards).
    "sheet_music": CardSpec("Sheet Music", "each beat flings 3 notes at the nearest enemies",
                            (("sheet_music", "flag", 1),), rarity="uncommon", max_stacks=1,
                            heroes=("bard",), tags=("projectile", "arcane"), code="B7"),
    "split_arrow": replace(_spell_card("split_arrow", "H7"), heroes=("huntress",)),
    "double_rainbow": CardSpec("Double Rainbow", "every 3rd shot: a second fan right behind",
                               (("double_rainbow", "flag", 1),), rarity="rare", max_stacks=1,
                               heroes=("princess",), tags=("projectile",), code="P7"),
    "twin_axes": CardSpec("Twin Axes", "every 3rd throw is two axes in a V",
                          (("twin_axes", "flag", 1),), rarity="rare", max_stacks=1,
                          heroes=("dwarf",), tags=("projectile", "physical"), code="D7"),
}

# Spells whose things last a while, so Lingering (+duration) does something
# for them (statuses count too, see players/cards._gate_met).
DURATION_SPELLS = ("poison_flask", "healing_totem", "bone_turret")

# Archetypes (design/CARDS.md section 7), by catalog code: once a build holds
# ARCHETYPE_MIN cards (copies count, spell levels too) of one archetype, its
# leading archetype gets ARCHETYPE_SLOTS of every offer's slots (when it has
# an eligible card). Ties go to the archetype listed first.
ARCHETYPE_MIN = 2
ARCHETYPE_SLOTS = 1
ARCHETYPES = {
    "crit": ("G06", "G07", "H4", "W4", "C05", "H3", "K01", "H5", "V03"),
    "burn": ("T01", "S02", "S10", "P3", "T02", "G18", "T10", "T13", "K02", "V06"),
    "poison": ("T03", "S06", "P3", "T04", "G18", "T10", "T14", "K02"),
    "frost": ("T05", "S03", "B4", "P3", "T06", "G09", "T13"),
    "shock": ("W3", "T07", "S07", "W1", "W2", "W5", "W7", "T14", "W6"),
    "missiles": ("W4", "W8", "W9", "W10", "W11", "W12", "G20", "T11"),
    "bleed": ("D4", "T08", "T09", "G18", "D5", "K02"),
    "volley": ("G20", "D1", "H1", "P1", "X03", "R06", "C06", "G02", "P5", "D5", "H6",
               "M01", "M02", "M03", "M04", "M05", "B7", "H7", "P7", "D7"),
    "sniper": ("D2", "H2", "C07", "H3", "G07", "G17", "H5"),
    "area": ("R01", "S05", "R02", "G08", "B3", "X06", "B5", "W5", "B1", "B6", "W10"),
    "summoner": ("S04", "S11", "S08", "G19", "G09", "K04"),
    "tank": ("G10", "G03", "S12", "X02", "C03", "R03", "S09", "K05", "K03", "D6"),
    "speed": ("G04", "G11", "C04", "C05", "C01", "K06", "V04"),
    "sustain": ("G12", "G13", "R04", "S08", "B2", "R05", "K03"),
    "greed": ("G15", "E01", "X05", "X06", "E03", "G14", "E02"),
    "glass": ("X01", "C01", "C02", "S09", "K06"),
    "roll": ("V01", "V02", "V03", "V04", "V05", "V06", "W6", "D6", "H6", "P6", "B6", "G11"),
}

# --- Loot and the Guild Hall (meta/guild.py, scenes/guild_hall.py) ----------------
# design/GUILD.md rev 2. Every kill a hero makes (or their statuses /
# spells) is worth loot at once: the enemy's xp x LOOT_PER_XP x (1 + loot
# bonus) x (1 + the active pacts' bonus). The run's loot is kept in full
# however the run ends and goes to the guild's purse, which buys the
# upgrades below, card unlocks, pacts and bestiary pages.
# Nothing repeats inside the hall: no effect is sold by the guildmaster and
# a trainer, or by two heroes' trainers.
LOOT_PER_XP = 1.0
# Developer mode (run.py --dev): the purse holds this much (never saved).
DEV_LOOT = 9_999_999

# The guildmaster: every hero gets these.
GUILD_UPGRADES = {
    "whetstone": UpgradeSpec("Whetstone", "+2% damage", (("damage", "add", 0.02),),
                             max_level=15, base_cost=150, growth=1.2),
    "drill_yard": UpgradeSpec("Drill Yard", "+1.5% attack speed",
                              (("attack_speed", "add", 0.015),), max_level=15, base_cost=150,
                              growth=1.2),
    "infirmary": UpgradeSpec("Infirmary", "+5 max HP", (("max_hp", "add", 5),), max_level=20,
                             base_cost=100, growth=1.18),
    "armory": UpgradeSpec("Armory", "+1 armor", (("armor", "add", 1),), max_level=15,
                          base_cost=150, growth=1.2),
    "cobbler": UpgradeSpec("Cobbler", "+1% move speed", (("move", "add", 0.01),), max_level=10,
                           base_cost=200, growth=1.25),
    "old_maps": UpgradeSpec("Old Maps", "+3% XP", (("xp", "add", 0.03),), max_level=10,
                            base_cost=150, growth=1.25),
    "treasure_map": UpgradeSpec("Treasure Map", "+4% loot", (("loot", "add", 0.04),),
                                max_level=15, base_cost=200, growth=1.2),
    "lodestone": UpgradeSpec("Lodestone", "+10% pickup radius", (("pickup", "add", 0.10),),
                             max_level=10, base_cost=100, growth=1.25),
    "lucky_shrine": UpgradeSpec("Lucky Shrine", "+2 luck", (("luck", "add", 2),), max_level=15,
                                base_cost=200, growth=1.2),
    "fortune_teller": UpgradeSpec("Fortune Teller", "+1 reroll each run",
                                  (("rerolls", "add", 1),), max_level=5, base_cost=400,
                                  growth=1.8),
    "exile_ledger": UpgradeSpec("Exile Ledger", "+1 banish each run", (("banishes", "add", 1),),
                                max_level=5, base_cost=600, growth=1.8),
    "recruits_kit": UpgradeSpec("Recruit's Kit", "start runs a level higher (+1 card pick)",
                                (("start_level", "add", 1),), max_level=3, base_cost=1500,
                                growth=2.0),
    "second_chance": UpgradeSpec("Second Chance", "once per run, rise at 30% HP when you fall",
                                 (("revives", "add", 1),), max_level=2, base_cost=3000,
                                 growth=2.5),
    "arcane_wing": UpgradeSpec("Arcane Wing", "+1 spell slot", (("spell_slots", "add", 1),),
                               max_level=1, base_cost=8000),
}
SECOND_CHANCE_HP = 0.30

# The trainer: each hero's own tree, only about their weapon or trick.
_BIG = dict(max_level=2, base_cost=1200, growth=2.0)     # the "+1 of my weapon's thing"
# Hero upgrades that were removed: (base cost, growth, max level) per key, so
# a save's levels in them are refunded once (meta/guild.Guild.load).
RETIRED_UPGRADES = {"wizard": {"forked_bolt": (1200, 2.0, 2), "long_arc": (150, 1.3, 5),
                               "grounding": (150, 1.3, 5)}}
_LADDER = dict(max_level=5, base_cost=150, growth=1.3)
_TRICK = dict(max_level=3, base_cost=400, growth=1.6)
HERO_UPGRADES = {
    "wizard": {
        # M20: the lightning ladders (Forked Bolt, Long Arc, Grounding) became
        # missile ones; levels bought in them are refunded (RETIRED_UPGRADES).
        "extra_dart": UpgradeSpec("Extra Dart", "+1 dart per cast",
                                  (("pellets", "add", 1),), **_BIG),
        "swift_darts": UpgradeSpec("Swift Darts", "darts fly 6% faster",
                                   (("shot_speed", "add", 0.06),), **_LADDER),
        "tracking": UpgradeSpec("Tracking", "darts turn 10% faster",
                                (("seek_turn", "add", 0.10),), **_LADDER),
        "capacitor": UpgradeSpec("Capacitor", "first cast after 2 s idle: +50% damage",
                                 (("capacitor", "add", 0.5),), **_TRICK),
    },
    "dwarf": {
        "axe_juggler": UpgradeSpec("Axe Juggler", "+1 axe per throw",
                                   (("pellets", "add", 1), ("spread", "add", 16)), **_BIG),
        "strong_arm": UpgradeSpec("Strong Arm", "axes fly 6% farther", (("range", "add", 0.06),),
                                  **_LADDER),
        "quick_catch": UpgradeSpec("Quick Catch", "axes fly home 10% faster, caught from farther",
                                   (("return_speed", "add", 0.1),), **_LADDER),
        "homecoming": UpgradeSpec("Homecoming", "+15% axe damage on the way back",
                                  (("homeward", "add", 0.15),), **_TRICK),
    },
    "huntress": {
        "barbed_tips": UpgradeSpec("Barbed Tips", "arrows pierce +1 enemy",
                                   (("pierce", "add", 1),), **_BIG),
        "eagle_eye": UpgradeSpec("Eagle Eye", "+3% crit chance", (("crit_chance", "add", 0.03),),
                                 **_LADDER),
        "fletcher": UpgradeSpec("Fletcher", "arrows fly 8% faster", (("shot_speed", "add", 0.08),),
                                **_LADDER),
        "quiver": UpgradeSpec("Quiver", "every 8th arrow has a twin (7th, 6th...)",
                              (("quiver", "add", 1),), **_TRICK),
    },
    "princess": {
        "coronation": UpgradeSpec("Coronation", "+1 color in the fan",
                                  (("pellets", "add", 1), ("spread", "add", 6)), **_BIG),
        "royal_grace": UpgradeSpec("Royal Grace", "+3% evasion", (("evasion", "add", 0.03),),
                                   **_LADDER),
        "bright_colors": UpgradeSpec("Bright Colors", "colors are 10% bigger",
                                     (("shot_size", "add", 0.1),), **_LADDER),
        "royal_decree": UpgradeSpec("Royal Decree", "start with a rare card (then epic, legendary)",
                                    (("royal_decree", "add", 1),), **_TRICK),
    },
    "bard": {
        "resonance": UpgradeSpec("Resonance", "+5% area", (("area", "add", 0.05),), **_LADDER),
        "soothing_strings": UpgradeSpec("Soothing Strings", "regain 0.2 HP per second",
                                        (("regen", "add", 0.2),), **_LADDER),
        "opening_act": UpgradeSpec("Opening Act", "beats deal x2 for the first 60 s of a run",
                                   (("opening_act", "add", 60.0),), **_TRICK),
        "encore_tour": UpgradeSpec("Encore Tour", "every 5th level-up offers 4 cards (then 4th)",
                                   (("encore_tour", "add", 1),), **_BIG),
    },
}
CAPACITOR_IDLE = 2.0         # seconds without attacking that charge the Capacitor
QUIVER_EVERY = 8             # Quiver: a twin every Nth arrow, one sooner per level after the first
SHOT_SIZE_PX = 6             # Bright Colors: a colour's hit radius grows by this x its bonus (px)

# The archivist's pacts: bought once, switched on at the dungeon gate.
# They're there to make the game insanely hard; each also pays a little
# more loot. More will come (~20 in all).
PACTS = {
    "blood": PactSpec("Pact of Blood", "enemies deal +25% damage", 0.20, 1500,
                      enemy_damage=0.25),
    "horde": PactSpec("Pact of the Horde", "30% more enemies", 0.20, 1500, enemy_count=0.30),
    "haste": PactSpec("Pact of Haste", "enemies move and attack 15% faster", 0.20, 2500,
                      enemy_haste=0.15),
    "famine": PactSpec("Pact of Famine", "no regeneration; skipping a card doesn't heal", 0.15,
                       2500, famine=True),
    "glass": PactSpec("Pact of Glass", "you have 40% less max HP", 0.40, 4000, hero_hp=-0.40),
    "veteran": PactSpec("Pact of the Veteran", "enemies are 10 levels tougher", 0.30, 5000,
                        enemy_levels=10),
}

# The archivist's bestiary: a page per enemy. Readable after BESTIARY_KILLS
# kills of it, or bought; either way you deal +BESTIARY_BONUS to its kind.
BESTIARY_KILLS = 25
BESTIARY_BONUS = 0.10
BESTIARY = {
    "goblin_archer": (500, "Keeps its distance and looses slow arrows. Flees when hurt badly."),
    "warlock": (900, "A red beam marks where its hex will strike: step out of the line."),
    "spell_tower": (900, "Never moves; fires bursts of three orbs. Ruins only."),
    "ogre": (1500, "Armored in front (hits there do a third). Throws rocks that break walls."),
    "burrower": (800, "Swims under the sand and erupts beneath you. Desert only."),
    "puffer": (500, "Swells, then bursts in a spore cloud that hurts everything near."),
    "warrior": (700, "Charges with sidesteps, raises its blade, then swings."),
    "dust_devil": (700, "Circles close, flinging sand in spirals and stinging on touch."),
    "wisp": (900, "Fires much faster while its searchlight is on you."),
    "toad": (600, "Hops between rests and spits a fan of acid."),
    "spitter": (800, "Rooted; fires a ring of spores that turns each volley."),
    "boar": (1000, "Scrapes the ground, then charges in a line. Dodge: it stuns itself on walls."),
    # M17: filled in by beating the swamp's boss (or bought).
    "psy_frog": (1500, "They hide out across the swamp. Keeps away, spits weaving globs."),
    "froggy": (5000, "Dives between pools, lashes its tongue, belly-flops. Hit it while it's dazed."),
}

# Achievements (they unlock "A:" cards).
ACHIEVEMENTS = {
    "chain_reaction": "kill 15 enemies within 1 second",
    "crit_75": "reach 75% crit chance",
    "level_30": "reach level 30",
    "froggy": "defeat Froggy McFrogface",
}
ACHIEVEMENT_BURST = (15, 1.0)   # chain_reaction: this many kills within this many seconds

# Rev 1 (M15) prices, to refund upgrades bought before rev 2 (meta/guild.py).
# (base, growth, max level); levels past a rev-1 maximum are never refunded.
REV1_PRICES = {
    "guild": {"whetstone": (80, 1.6, 5), "drill_yard": (80, 1.6, 5), "infirmary": (60, 1.6, 5),
              "armory": (100, 1.6, 5), "cobbler": (100, 1.6, 3), "old_maps": (80, 1.6, 5),
              "treasure_map": (100, 1.6, 5), "lodestone": (60, 1.6, 3),
              "lucky_shrine": (120, 1.6, 5), "fortune_teller": (150, 2.0, 3),
              "exile_ledger": (200, 2.0, 3), "arcane_wing": (1500, 1.6, 1)},
    # every other rev-1 hero upgrade: 100, 1.6, 3 levels
    "hero": {"mastery": (60, 1.6, 5), "toughness": (50, 1.6, 5)},
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
# 2.0 on 2026-09-30 (user: "increase around 2x"), then 1.6 the same day
# (user: "a bit too hard, dial down the difficulty a bit").
ENEMY_DENSITY_MULTIPLIER = 1.6
# Every enemy attack's damage is multiplied by this (before level scaling).
ENEMY_DAMAGE_MULTIPLIER = 0.85
# No enemies spawn within this many tiles of the start.
ENEMY_FREE_RADIUS = 55
# Nor on a landmark (a quest camp or boss lair), or within this many tiles of one.
LANDMARK_QUIET = 10
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
# ~5.4 min of straight walking from the centre to the coast (radius / 8.5 / 60).
# M12 (2026-09-30) doubled the plains' AREA and grew the island by the same
# amount so the biome ring kept its width:
#   plains radius 510 -> 510 * sqrt(2) = 721;   ring width 2550 - 510 = 2040;
#   island radius 721 + 2040 = 2761;   plains fraction 721 / 2761 = 0.2612.
WORLD_RADIUS = 2761
# The coastline wanders in and out by up to this fraction of WORLD_RADIUS
# (fBm noise; COAST_SCALE is the size of its biggest bays and capes, and
# COAST_OCTAVES adds ever smaller wiggles down to ~COAST_SCALE / 2**(n-1)).
COAST_AMPLITUDE = 0.2
COAST_SCALE = 2400
COAST_OCTAVES = 6
# The central plains reach this fraction of WORLD_RADIUS, their edge
# wandering by PLAINS_EDGE_AMPLITUDE (fraction of the plains radius).
PLAINS_RADIUS_FRACTION = 0.2612
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

# --- Quests, landmarks and bosses (M17, design/BOSSES.md) ---------------------------
#
# Each ring biome draws a quest (one per biome for now). Its giver waits at
# a camp just past the plains border, pinned on the maps from the start;
# talking to them starts the quest, finishing it wakes the biome's boss at
# its lair. The 5 ring bosses ("guardians") unlock the plains boss, whose
# Adventurer's Glory can end the run (later milestones).

QUESTS = {
    "swamp": QuestSpec(
        title="Bad Trip", biome="swamp", giver="frog hunter", giver_sprite="frog_hunter",
        camp="frog_camp", lair="pond_lair", target="psy_frog", count=5, boss="froggy",
        goal="Psychedelic frogs {n}/{count}",
        lines=(
            ("offer", ("Oi! Adventurer! Over here!",
                       "The frogs in my bog went all funny colours.",
                       "Glowing, hopping, spitting rainbows at me.",
                       "Now they've hopped off all over the swamp!",
                       "Squash five of 'em for me, will you?",
                       "Get close and you'll spot the glow.")),
            ("progress", ("{left} more of them glowing frogs.",
                          "They hopped off all over the swamp.",
                          "Get close and you'll spot the glow.")),
            ("done", ("That's five! But... hear that croak?",
                      "Something BIG woke up at the old pond.",
                      "I've marked it on your map. Go careful!")),
            ("fight", ("Froggy's awake! The old pond, quick!",)),
            ("cleared", ("Froggy McFrogface, beaten! Ha!",
                         "The bog will sleep easy tonight. Thank you!")),
        ),
    ),
}
# The main quest: beat this many ring-biome bosses ("guardians"), then the
# plains boss, for Adventurer's Glory.
GUARDIANS = 5

# Quest givers: how close you must stand to talk (E / gamepad A), and how
# long each line they say stays over their head.
TALK_RADIUS = 3.0
SPEECH_LINE_TIME = 2.6

# The frog hunter's camp (world/landmarks.py): a bog oval of these radii
# (tiles) with his hut on the side facing the plains, CAMP_BORDER_GAP tiles
# past the plains border. Pools where the bog's noise field is above
# CAMP_POOL_MIN (higher: fewer, smaller pools).
CAMP_BOG_RADII = (34, 15)
CAMP_BORDER_GAP = 30
CAMP_POOL_MIN = 0.58

# A quest's targets (the psychedelic frogs) are scattered over the whole
# biome (world/landmarks._scatter), not left at the camp: QUEST_SPOT_EXTRA
# more than the quest needs (any `count` of them will do), at least
# QUEST_SPOT_SEPARATION tiles apart (less if the biome is too small) and
# QUEST_SPOT_CAMP_GAP from the giver, at least QUEST_SPOT_EDGE tiles inside
# the biome, each in a mud clearing of radius QUEST_SPOT_CLEARING tiles.
# Picked from QUEST_SPOT_CANDIDATES random points. (One screen: ~86 x 30.)
QUEST_SPOT_EXTRA = 3
QUEST_SPOT_SEPARATION = 350
QUEST_SPOT_CAMP_GAP = 200
QUEST_SPOT_EDGE = 16
QUEST_SPOT_CLEARING = 4
QUEST_SPOT_CANDIDATES = 400
# A living target shows on the maps only within this many tiles of you
# (the minimap then points the way in).
QUEST_TARGET_PIN_RADIUS = 160

# A boss lair: an oval arena LAIR_RADII tiles (half-width, half-height) --
# one screen shows ~86 x 30 tiles, so 125 x 50 is about 3 x 3 screens (room
# for co-op players to spread out) -- inside a LAIR_WALL-tile ring of
# standing stones, with a LAIR_GATE_WIDTH-tile gate facing the plains and a
# LAIR_MARGIN-tile clearing all round. LAIR_POOLS pools (one in the middle)
# and LAIR_PILLARS stone pillars for cover, spread over the whole floor.
LAIR_RADII = (125, 50)
LAIR_WALL = 3
LAIR_GATE_WIDTH = 7
LAIR_MARGIN = 12
LAIR_POOLS = 9
LAIR_PILLARS = 30
# The gate seals (thorns) once a player is this far inside the stones, and
# opens again when the boss falls.
LAIR_SEAL_DEPTH = 6

# Bosses. HP and damage grow with the players' level like any enemy's
# (ENEMY_HP_PER_LEVEL / ENEMY_DAMAGE_PER_LEVEL), and HP by coop_hp per
# extra player. Fight-length target for a ring boss: ~2 min at the power
# you usually have when you get there (design/BOSSES.md 5.4).
BOSS_BANNER_TIME = 3.5          # the boss's name across the screen when it wakes
# Chill and freeze slow a boss's clock at most down to this (no freeze-lock).
BOSS_MIN_TIME_SCALE = 0.5
# Most boss shots alive at once, per player in the arena (design/BOSSES.md 5.4).
BOSS_MAX_SHOTS = 150
# A boss's card reward: one extra card offer of at least this rarity.
BOSS_CARD_RARITY = "rare"

BOSSES = {
    "froggy": BossSpec(
        name="Froggy McFrogface",
        phases=(
            BossPhase(1.0, (("fan", 3), ("stream", 3), ("tongue", 2), ("flop", 3)), rest=1.1),
            BossPhase(0.6, (("fan", 2), ("tongue", 2), ("flop", 2), ("spiral", 3), ("dive", 2),
                            ("summon", 1)), rest=0.9),
            BossPhase(0.25, (("tongue", 1), ("flop", 2), ("spiral", 2), ("dive", 2),
                             ("rain", 3), ("ring", 3)), rest=0.55),
        ),
        loot=2500, achievement="froggy", pages=("froggy", "psy_frog"),
    ),
}

# Froggy McFrogface's moves (ai/bosses.py). Damages are per hit at level 1
# (x the enemy damage scaling), speeds in tiles/s.
FROGGY_HIT_RADIUS = 2.3         # tiles (its body is ~5 x 3 tiles)
FROGGY_TELL = 0.55              # wind-up before the tadpoles / spirals / croak
FROGGY_FAN = (7, 60.0, 3, 0.35)         # tadpoles per volley, fan degrees, volleys, gap s
FROGGY_STREAM = (5, 0.22)               # bubbles in a stream, s between them
FROGGY_TONGUE = (0.8, 16.0, 0.9, 14, 5.0)  # aim time, reach, width, damage, pull (tiles)
FROGGY_FLOP = (1.0, 34.0, 4.0, 15, 16, 1.5)  # flight s, max leap, blast radius, damage,
                                            # ripples on landing, dazed s (the melee window)
FROGGY_SPIRAL = (3.0, 0.12, 2.2)        # seconds, s between bubbles, arm turn rad/s
FROGGY_DIVE = (0.5, 0.6, 1.3, 22)       # hop in, under, ripples (tell) s, ring on surfacing
FROGGY_SUMMON = (3, 4)                  # toads per croak, most alive at once
FROGGY_RAIN = (4.0, 0.3, 3.0, 7.0, 20.0)  # seconds, s between rows, column gap, hole width,
                                          # half-width of the curtain (tiles)
FROGGY_RING = (22, 10.0, 0.7, 2, 0.9)   # bullets, radius, hold s (tell), rings, s between
FROGGY_FAR = 40.0               # farther than this from its target: it leaps closer
# Its shots (enemy damage scaling applies).
FROGGY_SHOTS = {
    "tadpole": ShellSpec(speed=12.0, damage=9, max_range=34.0, damages_terrain=False,
                         look="tadpole", sound="orb"),
    "bubble": ShellSpec(speed=7.0, damage=8, max_range=30.0, damages_terrain=False,
                        look="bubble", sound="fizzle"),
    "stream": ShellSpec(speed=13.0, damage=8, max_range=34.0, damages_terrain=False,
                        look="bubble", sound="fizzle"),
    "ripple": ShellSpec(speed=8.0, damage=10, max_range=22.0, damages_terrain=False,
                        look="ripple", sound="fizzle"),
    "rain": ShellSpec(speed=9.0, damage=8, max_range=40.0, damages_terrain=False,
                      look="psy", sound="orb"),
    "ring": ShellSpec(speed=7.0, damage=10, max_range=20.0, damages_terrain=False,
                      look="psy", sound="orb"),
}
