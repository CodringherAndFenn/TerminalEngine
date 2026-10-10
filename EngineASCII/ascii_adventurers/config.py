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
    # P7: the bandit slinger's sling (a quick burst of three stones) and the
    # shieldbearer's shield bash.
    "sling": WeaponSpec(
        name="sling", fire_interval=2.4, burst=3, burst_gap=0.12,
        shell=ShellSpec(speed=20.0, damage=5, max_range=18.0, damages_terrain=False,
                        look="pebble", sound="bow"),
    ),
    "shield_bash": WeaponSpec(
        name="shield bash", kind="melee", fire_interval=2.6, damage=22, reach=1.9, arc_deg=110.0,
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
    # P7
    "bandit": CharacterSpec(
        name="bandit slinger", weapon="sling", sprite="bandit", max_speed=5.2,
        accel=20.0, brake=30.0, size_px=24, aim_turn_speed=math.radians(150),
    ),
    "shieldbearer": CharacterSpec(
        name="shieldbearer", weapon="shield_bash", sprite="shieldbearer", max_speed=2.6,
        accel=10.0, brake=20.0, size_px=34, sprite_scale=4, hold_px=20,
        aim_turn_speed=math.radians(90),
        front_armor=0.0,          # the shield: nothing gets through from the front
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
    # --- P7: the plains (design/BOSSES.md 24.5; ai/plains.py) --------------------------
    # Simple chasers (the user: "enemies that just go to the player without
    # complicated AI behaviour").
    "field_rat": EnemySpec(
        name="field rat", kind="chaser", sprite="field_rat", scale=2, group=(4, 6),
        max_hp=12, sight=14, biomes=("plains",), weight=3, speed=6.0,
        damage=4, attack_radius=0.8, windup=0.25, cooldown=0.9, size_px=12, xp=1,
    ),
    "farmhand": EnemySpec(
        name="shambling farmhand", kind="chaser", sprite="farmhand",
        max_hp=70, sight=12, biomes=("plains",), weight=3, speed=2.6,
        damage=12, attack_radius=1.4, windup=0.6, cooldown=1.5, size_px=22, xp=5,
    ),
    "goose": EnemySpec(
        name="angry goose", kind="chaser", sprite="goose", scale=2, group=(3, 3),
        max_hp=18, sight=14, biomes=("plains",), weight=2, speed=7.0,
        damage=4, attack_radius=0.9, windup=0.2, cooldown=0.8, size_px=14, xp=2,
    ),
    # Beasts.
    "hound": EnemySpec(
        name="wild hound", kind="hound", sprite="hound", group=(3, 3),
        max_hp=30, sight=16, biomes=("plains",), weight=2, speed=7.5,
        damage=8, attack_radius=1.0, windup=0.25, cooldown=1.2, size_px=18, xp=3,
    ),
    "hawk": EnemySpec(
        name="hawk", kind="hawk", sprite="hawk",
        max_hp=30, sight=18, biomes=("plains",), weight=2, speed=7.0,
        damage=12, attack_radius=1.0, windup=0.8, cooldown=1.0, size_px=20, xp=5,
    ),
    "molehill": EnemySpec(
        name="molehill", kind="molehill", sprite="molehill",
        max_hp=90, sight=14, biomes=("plains",), weight=1, speed=0.0,
        damage=0, size_px=26, xp=6,
    ),
    "mole_rat": EnemySpec(
        name="mole rat", kind="chaser", sprite="mole_rat", scale=2,
        max_hp=10, sight=16, biomes=(), speed=6.5,
        damage=4, attack_radius=0.8, windup=0.25, cooldown=1.0, size_px=12, xp=1,
    ),
    "bull": EnemySpec(
        name="rampaging bull", kind="bull", sprite="bull", scale=4, elite=True,
        max_hp=320, sight=18, biomes=("plains",), weight=1, speed=3.5,
        damage=32, attack_radius=11.0,   # charges from up to this far away
        windup=1.0, cooldown=3.0, size_px=40, xp=20,
    ),
    # Bandits and folk (the slinger and the shieldbearer are Characters).
    "slinger": EnemySpec(
        name="bandit slinger", kind="archer", body="bandit", max_hp=35, sight=16,
        biomes=("plains",), weight=3, preferred_range=(6.0, 10.0), xp=4,
    ),
    "lancer": EnemySpec(
        name="lancer", kind="lancer", sprite="bandit",
        max_hp=90, sight=18, biomes=("plains",), weight=2, speed=12.0,
        damage=18, attack_radius=1.0, windup=0.6, cooldown=0.8, size_px=30, xp=9,
    ),
    "shieldbearer": EnemySpec(
        name="shieldbearer", kind="shieldbearer", body="shieldbearer", elite=True,
        max_hp=240, sight=14, biomes=("plains",), weight=1, xp=16,
    ),
    "priest": EnemySpec(
        name="field priest", kind="priest", sprite="priest",
        max_hp=45, sight=16, biomes=("plains",), weight=1, speed=3.5,
        damage=0, size_px=22, xp=7,
    ),
    # Haunted farmland and odd ones.
    "straw_golem": EnemySpec(
        name="straw golem", kind="straw_golem", sprite="straw_golem", scale=4,
        max_hp=160, sight=12, biomes=("plains",), weight=2, speed=2.2,
        damage=24, attack_radius=2.0, windup=0.9, cooldown=2.0, size_px=34, xp=10,
    ),
    "scarecrow": EnemySpec(
        name="scarecrow", kind="scarecrow", sprite="scarecrow",
        max_hp=80, sight=16, biomes=("plains",), weight=2, speed=1.2,
        damage=0, size_px=22, xp=7,
    ),
    "crow": EnemySpec(
        name="crow", kind="crow", sprite="crow", scale=2,
        max_hp=8, sight=24, biomes=(), speed=6.5,
        damage=5, attack_radius=0.8, windup=0.2, cooldown=1.0, size_px=12, xp=0,
    ),
    "drummer": EnemySpec(
        name="war drummer", kind="drummer", sprite="drummer",
        max_hp=50, sight=16, biomes=("plains",), weight=1, speed=4.0,
        damage=0, size_px=22, xp=7,
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
    # M22: the leech doctor's quest and the swarm. A bloated leech crawls at
    # you and bites; popped, it bursts into LEECH_BROOD leechlings.
    "bloated_leech": EnemySpec(
        name="bloated leech", kind="leech", max_hp=120, sight=18, biomes=(), speed=3.0,
        damage=8, attack_radius=1.1, windup=0.35, cooldown=1.2, size_px=22, xp=25,
    ),
    "leechling": EnemySpec(
        name="leechling", kind="leech", max_hp=18, sight=16, biomes=(), speed=6.5,
        damage=4, attack_radius=0.8, windup=0.2, cooldown=0.9, size_px=10, xp=2,
    ),
    # The swarm's health is the sum of its leeches' (max_hp is the whole).
    "leech_swarm": EnemySpec(
        name="The Leech Swarm", kind="leech_swarm", max_hp=8500, sight=400,
        biomes=(), size_px=16, xp=400,
    ),
    # M22.2: the smoke keeper's quest and Lady Proboscia. Mosquitoes fly
    # over everything, buzz in, hover a moment (the tell) and sting, then
    # dart off. They swarm whoever lights a brazier, and the Lady calls them.
    "mosquito": EnemySpec(
        name="mosquito", kind="mosquito", max_hp=15, sight=22, biomes=(), speed=7.5,
        damage=4, attack_radius=0.9, windup=0.3, cooldown=1.0, size_px=12, xp=2,
    ),
    "proboscia": EnemySpec(
        name="Lady Proboscia", kind="proboscia", max_hp=8000, sight=400,
        biomes=(), size_px=130, xp=400,
    ),
    # M23.1: the scarab collector's quest and Khepri. A golden scarab is
    # harmless: it runs from you, and if you don't catch it in time it digs
    # in and comes up again at its home spot later (GOLDEN_SCARAB_*). Scarabs
    # are Khepri's adds: they scuttle at you and nip.
    "golden_scarab": EnemySpec(
        name="golden scarab", kind="golden_scarab", max_hp=45, sight=14, biomes=(), speed=7.0,
        size_px=14, xp=25,
    ),
    "scarab": EnemySpec(
        name="scarab", kind="scarab", max_hp=30, sight=20, biomes=(), speed=6.0,
        damage=5, attack_radius=0.9, windup=0.3, cooldown=1.0, size_px=14, xp=3,
    ),
    "khepri": EnemySpec(
        name="Khepri the Dung Emperor", kind="khepri", max_hp=8000, sight=400,
        biomes=(), size_px=110, xp=400,
    ),
    # M23.2: the caravan master's quest and Ol' Spitter. Mangy camels sit on
    # his lost cargo: they keep their distance, rear their heads (the tell)
    # and spit a little fan of globs (CAMEL_SPIT). A mirage is one of Ol'
    # Spitter's heat-haze decoys: it spits like a camel and pops at a touch.
    "mangy_camel": EnemySpec(
        name="mangy camel", kind="camel", max_hp=90, sight=18, biomes=(), speed=5.0,
        preferred_range=(7.0, 11.0), windup=0.5, cooldown=2.2, size_px=34, xp=20,
    ),
    "mirage": EnemySpec(
        name="mirage", kind="camel", max_hp=1, sight=30, biomes=(), speed=6.0,
        preferred_range=(6.0, 10.0), windup=0.5, cooldown=2.0, size_px=46, xp=1,
    ),
    "ol_spitter": EnemySpec(
        name="Ol' Spitter, the Unmannered One", kind="ol_spitter", max_hp=8000, sight=400,
        biomes=(), size_px=110, xp=400,
    ),
    # M23.3: the runaway apprentice's quest and the Nameless Magus. Sand
    # elementals rise round whoever holds a star circle (and serve the
    # Magus): they blink in short hops and throw sand bolts. His sand golems
    # climb out of golem runes, plod at you and slam the ground; his sigils
    # drift after you and burst on touch (one hit pops one); his hourglass
    # stands still and can be shattered.
    "sand_elemental": EnemySpec(
        name="sand elemental", kind="elemental", max_hp=60, sight=24, biomes=(), speed=6.0,
        preferred_range=(6.0, 10.0), windup=0.45, cooldown=1.6, size_px=22, xp=10,
    ),
    "sand_golem": EnemySpec(
        name="sand golem", kind="golem", max_hp=220, sight=30, biomes=(), speed=3.6,
        damage=14, attack_radius=2.4, windup=0.7, cooldown=1.8, size_px=34, xp=8,
    ),
    "sigil": EnemySpec(
        name="sand sigil", kind="sigil", max_hp=1, sight=60, biomes=(), speed=6.5,
        damage=10, attack_radius=1.2, size_px=14, xp=1,
    ),
    "hourglass": EnemySpec(
        name="the Magus's hourglass", kind="hourglass", max_hp=320, sight=0, biomes=(),
        speed=0.0, size_px=40, xp=1,
    ),
    "nameless_magus": EnemySpec(
        name="Nameless Magus, Holder of Time", kind="nameless_magus", max_hp=8000, sight=400,
        biomes=(), size_px=60, xp=400,
    ),
    # M24.1: the hazmat scavenger's escort and the Fallout King. Glowing
    # ghouls rush you (they come in waves while a beacon is set up, and at
    # the King's call) and burst green when they die. His isotope rods stand
    # in fallout; his barrels fly at you (they can't be hit in the air); his skulls
    # home in (a sigil's flight: one hit pops one).
    "glowing_ghoul": EnemySpec(
        name="glowing ghoul", kind="ghoul", max_hp=40, sight=26, biomes=(), speed=7.0,
        damage=7, attack_radius=1.0, windup=0.3, cooldown=0.9, size_px=18, xp=6,
    ),
    "isotope_rod": EnemySpec(
        name="isotope rod", kind="rod", max_hp=60, sight=0, biomes=(), speed=0.0,
        size_px=16, xp=2,
    ),
    "toxic_barrel": EnemySpec(
        name="toxic barrel", kind="barrel", max_hp=1, sight=0, biomes=(), speed=0.0,
        size_px=18, xp=1,
    ),
    "gamma_skull": EnemySpec(
        name="gamma skull", kind="sigil", max_hp=1, sight=60, biomes=(), speed=7.0,
        damage=9, attack_radius=1.1, size_px=14, xp=1,
    ),
    "fallout_king": EnemySpec(
        name="The Fallout King", kind="fallout_king", max_hp=8000, sight=400,
        biomes=(), size_px=90, xp=400,
    ),
    # M24.2: the searching sister's rescue and the Snow King. Frost wraiths
    # drift through walls to re-freeze a thawing captive (or after you).
    "frost_wraith": EnemySpec(
        name="frost wraith", kind="wraith", max_hp=30, sight=30, biomes=(), speed=4.5,
        damage=6, attack_radius=1.0, size_px=18, xp=6,
    ),
    "snow_king": EnemySpec(
        name="Snow King, King of Loneliness", kind="snow_king", max_hp=8000, sight=400,
        biomes=(), size_px=90, xp=400,
    ),
    # M24.3: the pawn dealer's fetch quest and Fragile. Vampire bats guard
    # the pieces of her bear (and fly at you); thralls climb out of her
    # coffins.
    "vampire_bat": EnemySpec(
        name="vampire bat", kind="mosquito", max_hp=35, sight=22, biomes=(), speed=8.0,
        damage=6, attack_radius=0.9, windup=0.25, cooldown=1.0, size_px=14, xp=8,
    ),
    "thrall": EnemySpec(
        name="thrall", kind="leech", max_hp=80, sight=30, biomes=(), speed=5.5,
        damage=10, attack_radius=1.2, windup=0.4, cooldown=1.2, size_px=22, xp=6,
    ),
    "fragile": EnemySpec(
        name="Fragile, The Misunderstood", kind="fragile", max_hp=8000, sight=400,
        biomes=(), size_px=70, xp=400,
    ),
    # M25.1: the hedge witch's "cleanse" quest and Nettle. Blighted sprites
    # rise round a shrine being cleansed; rot moths come at Nettle's call;
    # her glamour decoys are bodies too (ai/bosses.Glamour: one hit pops
    # one, and it's worth nothing).
    "blighted_sprite": EnemySpec(
        name="blighted sprite", kind="mosquito", max_hp=30, sight=24, biomes=(), speed=7.0,
        damage=6, attack_radius=0.9, windup=0.3, cooldown=1.1, size_px=14, xp=6,
    ),
    "rot_moth": EnemySpec(
        name="rot moth", kind="mosquito", max_hp=25, sight=30, biomes=(), speed=8.5,
        damage=5, attack_radius=0.9, windup=0.25, cooldown=1.0, size_px=14, xp=3,
    ),
    "glamour": EnemySpec(
        name="glamour", kind="glamour", max_hp=1, sight=400, biomes=(), size_px=50, xp=0,
    ),
    "nettle": EnemySpec(
        name="Nettle, the Blighted", kind="nettle", max_hp=8000, sight=400,
        biomes=(), size_px=50, xp=400,
    ),
}

# P7 enemy behaviour (ai/plains.py; design/BOSSES.md 24.5).
HOUND_ORBIT = 3.5            # tiles a hound circles its target at...
HOUND_WAIT = (1.0, 2.5)      # ...s between its darts (only one of a pack darts at a time)...
HOUND_DASH = 1.8             # ...darting this much faster...
HOUND_DASH_TIME = 1.0        # ...for at most this long
HAWK_ORBIT = 7.0             # tiles a hawk circles at
HAWK_CIRCLE = (2.5, 4.5)     # s circling between dives (it lines up for the spec's windup)
HAWK_DIVE_SPEED = 18.0       # tiles/s
HAWK_DIVE_LENGTH = 13.0      # tiles a dive covers
HAWK_CLIMB = 1.0             # s climbing away after
MOLEHILL = (3.5, 4, 14.0)    # a mole rat every this many s, at most this many about within this far
BULL_CHARGE_SPEED = 15.0     # tiles/s
BULL_CHARGE = 14.0           # tiles each charge runs
BULL_PASSES = 3              # charges before it rests
BULL_TURN = 0.6              # s wheeling round between charges
BULL_DAZE = 1.6              # s dazed after hitting something unbreakable
BULL_TRAMPLE = 999           # what it does to a breakable tile it runs into (flattened)
LANCER_START = 10.0          # tiles from its target it wheels out to...
LANCER_WHEEL = 4.0           # ...for at most this long, then turns in anyway
LANCER_OVERRUN = 6.0         # tiles it gallops on past the target's spot
LANCER_REACH = 1.6           # tiles ahead of it the lance tip hits
PRIEST = (2.5, 9.0, 0.20)    # heals every this many s, within this far, this share of max HP
PRIEST_RANGE = (8.0, 12.0)   # tiles it keeps from the heroes
GOLEM_FIRE = (5, 5.0, 0.9, 2.2)   # burning patches, s they burn, their radius, how far they spread
SCARECROW = (6.0, 3, 6.0, 6) # crows every this many s, this many, keeping this far, at most this many about
CROW_LIFE = 12.0             # s a crow stays before it flaps off
DRUM_RADIUS = 7.0            # tiles the drummer's ring reaches...
DRUM_TIME = 0.4              # ...each beat lasting this long on whoever is in it...
DRUM_HASTE = 0.30            # ...+ this much faster (move and attack)...
DRUM_DAMAGE = 0.25           # ...+ this much damage
DRUM_KEEP = 9.0              # tiles it keeps from the heroes
SHIELD_WINDUP = 0.8          # s the shieldbearer raises its shield before a bash...
SHIELD_SHOVE = 2.0           # ...which shoves who it hits this far...
SHIELD_OPEN = 1.4            # ...then it stands open (its front unguarded) this long

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
# P3 (2026-10-10, user: "movement speed needs to grow with level a bit"):
# every level past the first adds LEVEL_SPEED to the hero's move speed,
# up to LEVEL_SPEED_CAP (reached at level 21). It adds to Swift Boots and
# the Cobbler like any "move" bonus. Level 12 (a ~15 min run): +11%.
LEVEL_SPEED = 0.01
LEVEL_SPEED_CAP = 0.20

# Difficulty levels (P5, 2026-10-10; user: "a completely separate difficulty
# option, kind of like diablo torment levels, where you can choose how hard
# the map starts", additive to the other balancing). Picked on the hero
# select. Level 0 is today's game; level n multiplies every enemy's (and
# boss's) max HP by DIFFICULTY_HP ** n and its damage by DIFFICULTY_DAMAGE
# ** n (compounding: the user's "steep" pick), and adds DIFFICULTY_ENEMIES
# x n to how many spawn and DIFFICULTY_LOOT x n to the loot (added). All of
# it is on top of player levels, pacts, Beacon and Bounty. Beating any boss
# on a level opens the next (meta/guild.Guild.difficulty_open). Names: the
# user's.
#        HP     dmg    enemies  loot
#   0    x1     x1     x1       +0%     Wanderer
#   1    x1.3   x1.15  x1.2     +40%    Knight
#   3    x2.2   x1.5   x1.6     +120%   Hero of Legend I
#   5    x3.7   x2.0   x2.0     +200%   Hero of Legend III
#  10    x13.8  x4.0   x3.0     +400%   Hero of Legend VIII
DIFFICULTIES = ("Wanderer", "Knight", "Folk Hero",
                *(f"Hero of Legend {r}" for r in ("I", "II", "III", "IV", "V", "VI", "VII",
                                                  "VIII")))
DIFFICULTY_HP = 1.3
DIFFICULTY_DAMAGE = 1.15
DIFFICULTY_ENEMIES = 0.20
DIFFICULTY_LOOT = 0.40

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
PICKUP_RADIUS = 3.75         # tiles, before Magnet cards (P3, 2026-10-10: was 1.5; user: +150%)
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
TRAIL_SPACING = 0.8          # Scorched Trail: tiles between trail patches...
TRAIL_RADIUS = 0.9           # ...each this big...
TRAIL_LIFE = 2.5             # ...lasting this long...
TRAIL_EVERY = 0.5            # ...applying its status this often
PIROUETTE = (10, 1.0)        # Pirouette (P4): shots in the ring (colors in turn), x damage each
BLINK = (5.0, 2.5, 20.0)     # Blink: teleport distance, shock nova radius, nova damage
BLINK_STEP = 0.25            # tiles: the teleport is checked against walls this finely
BACKFLIP = (5, 40.0, 0.6)    # Backflip: arrows, fan degrees, x damage each
SHOULDER_CHARGE = (25.0, 0.6, 2.5)   # Shoulder Charge: damage, reach past the body, push tiles
DROP_THE_BEAT = 1.5          # Drop the Beat: x damage of the free beat at the end of a roll

# Hero cards (catalog 6.2) and the rules they bring.
POINT_BLANK_RANGE = 4.0      # tiles (Point Blank)
SUPERCELL_BONUS = 0.25       # chain jumps vs shocked enemies (Supercell)
# Arcane missile cards (M20).
SEEKER = 2.0                 # Seeker: darts turn this much faster (and retarget)
RESONANCE = (1.0, 0.15, 4)   # Resonance: window s, +damage per dart in it, most darts counted
IMPLOSION = (2.5, 0.8)       # Implosion (P4): radius, tiles each enemy in it is dragged in
ARCANE_STORM = (3, 8.0)      # Arcane Storm: new darts per cast at most, how far they look
ORBIT_REACH = 12.0           # Orbiting Darts: a missed dart looks this far round you
MARK_INTERVAL = 4.0          # Hunter's Mark picks a new target this often
MARK_MULT = 2.0
DISSONANCE_PUSH = 1.2        # tiles a beat pushes enemies back (Dissonance)
SPECTRUM_CHANCE = 0.20       # Spectrum: chance a color applies its status
# Spectrum: rainbow pellet color (palette.RAINBOW_SHOTS order) -> status.
SPECTRUM_STATUS = ("burn", None, "shock", "poison", "chill")
RICOCHET_BOUNCES = 2         # Ricochet: wall bounces before an axe turns home
# Arrow Rain (P4): every ARROW_RAIN[0]th shot also lobs ARROW_RAIN[1] arrows
# (+1 per extra projectile) at random spots within ARROW_RAIN[2] tiles of the
# aim point; each lands for ARROW_RAIN[3] x the bow's damage on everything
# within ARROW_RAIN_HIT tiles.
ARROW_RAIN = (5, 6, 3.0, 0.7)
ARROW_RAIN_HIT = 0.7
# Hang Time (P4): an axe hovers at the end of its throw HANG_TIME[0] s (+
# HANG_TIME[1] per copy past the first), hitting everything it touches again
# every HANG_TIME[2] s.
HANG_TIME = (0.4, 0.2, 0.2)
# Tether (P4): every TETHER[0] s, everything within TETHER[1] tiles of the
# line from the dwarf to each of his axes in flight takes TETHER[2] x the
# axe's damage.
TETHER = (0.3, 0.35, 0.25)
SPLITTING_AXE = (0.6, 1.2)   # Splitting Axe (P4): x damage of each half, tiles they start apart
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
# to its fan (Multishot, Quiver...), so extra shots always
# fan out visibly instead of flying as one line. A weapon's own fan (the
# rainbow's 5 colors over 34 degrees) is left as it is.
MIN_PELLET_GAP = 12.0
CROSS_FIRE_EVERY = 4         # Cross Fire: every Nth attack also goes off at 90/180/270 degrees
STARBURST = (10, 8)          # Starburst: every Nth attack, this many single shots all round
REAR_GUARD = 0.6             # Rear Guard: x damage of the shot fired behind you
SPIRAL_STEP = 37.0           # Spiral: degrees the extra shot turns further each attack
TWIN_LANES = (0.5, 0.65)     # Twin Lanes: tiles between the two lanes, x damage of each
CONVERGE_MIN = 3.0           # Converge (P4): tiles; the colors cross no nearer than this
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
    # Arrow Rain's arrows (P4): lobbed over everything, landing on whatever
    # is within ARROW_RAIN_HIT tiles (damage from the bow, x ARROW_RAIN[3]).
    "rain_arrow": ShellSpec(speed=30.0, damage=0, max_range=40.0, damages_terrain=False,
                            look="rain_arrow", sound="bow", lob=True,
                            blast_radius=ARROW_RAIN_HIT),
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
    # P4 (2026-10-10): Phase Darts took Overload's slot (W4; Overload did what
    # Echo does). A save that bought Overload gets it (RENAMED_CARDS).
    "phase_darts": CardSpec("Phase Darts", "darts fly through walls and trees",
                            (("phase_darts", "flag", 1),), rarity="rare", max_stacks=1,
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
    # P4: Implosion took Mana Burst's slot (W10; it was Volatile's double).
    "implosion": CardSpec("Implosion", "a dart's hit drags enemies within 2.5 tiles toward it",
                          (("implosion", "flag", 1),), rarity="rare", max_stacks=1,
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
    # P4: Hang Time took Heavy Axe's slot (D2; it was Glass Cannon's double).
    "hang_time": CardSpec("Hang Time", "axes hover at the end of their throw, hitting again",
                          (("hang_time", "add", 1),), rarity="rare",
                          heroes=("dwarf",), tags=("physical", "area"), code="D2"),
    "homeward_fury": CardSpec("Homeward Fury", "axes deal +50% on the way back",
                              (("homeward", "add", 0.5),), max_stacks=2, heroes=("dwarf",),
                              code="D3"),
    # P4: Tether took Cleave's slot (D4; it was a stronger Serrated).
    "tether": CardSpec("Tether", "a chain to each axe in flight cuts all it crosses",
                       (("tether", "flag", 1),), rarity="uncommon",
                       max_stacks=1, heroes=("dwarf",), tags=("physical", "area"), code="D4"),
    "cyclone": CardSpec("Cyclone", "a caught axe flies straight back out at the nearest enemy",
                        (("cyclone", "flag", 1),), heroes=("dwarf",), tags=("physical",),
                        code="D5", **_CAP),
    # --- Huntress ---
    # P4: Arrow Rain took Volley's slot (H1; Volley was Cross Fire's double).
    "arrow_rain": CardSpec("Arrow Rain", "every 5th shot also rains 6 arrows where you aim",
                           (("arrow_rain", "flag", 1),), rarity="epic", max_stacks=1,
                           heroes=("huntress",), tags=("projectile", "area"), code="H1"),
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
    # P4: Pirouette took Prism Dash's slot (P6; it was Scorched Trail's double).
    "pirouette": CardSpec("Pirouette", "rolling spins a ring of all your colors outward",
                          (("pirouette", "flag", 1),), rarity="uncommon", max_stacks=1,
                          heroes=("princess",), tags=("roll", "projectile"), code="P6"),
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
    # P4: Converge and Splitting Axe took Double Rainbow's and Twin Axes'
    # slots (P7, D7; they were Echo's and Twin Lanes' doubles).
    "converge": CardSpec("Converge", "your colors curve in and cross where you aim",
                         (("converge", "flag", 1),), rarity="rare", max_stacks=1,
                         heroes=("princess",), tags=("projectile",), code="P7"),
    "splitting_axe": CardSpec("Splitting Axe", "an axe splits in two as it turns for home",
                              (("splitting_axe", "flag", 1),), rarity="rare", max_stacks=1,
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
    "crit": ("G06", "G07", "H4", "C05", "H3", "K01", "H5", "V03"),
    "burn": ("T01", "S02", "S10", "P3", "T02", "G18", "T10", "T13", "K02", "V06"),
    "poison": ("T03", "S06", "P3", "T04", "G18", "T10", "T14", "K02"),
    "frost": ("T05", "S03", "B4", "P3", "T06", "G09", "T13"),
    "shock": ("W3", "T07", "S07", "W1", "W2", "W5", "W7", "T14", "W6"),
    "missiles": ("W4", "W8", "W9", "W10", "W11", "W12", "G20", "T11"),
    "bleed": ("T08", "T09", "G18", "D5", "K02"),
    "volley": ("G20", "D1", "H1", "P1", "X03", "R06", "C06", "G02", "P5", "D5", "H6",
               "M01", "M02", "M03", "M04", "M05", "B7", "H7", "P7", "D7", "P6"),
    "sniper": ("H2", "C07", "H3", "G07", "G17", "H5"),
    "area": ("R01", "S05", "R02", "G08", "B3", "X06", "B5", "W5", "B1", "B6", "W10",
             "D2", "D4", "H1"),
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
    "stable": UpgradeSpec("Stable", "+5% riding speed; mount back 1 s sooner after a fall",
                          (("mount_speed", "add", 0.05), ("mount_cooldown", "add", 1.0)),
                          max_level=5, base_cost=250, growth=1.3),           # (P6)
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
# Cards bought in the archive that were replaced by a card of the same
# price (P4, 2026-10-10): a save that bought the old one gets the new one.
RENAMED_CARDS = {"overload": "phase_darts"}
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
    # P7: the plains
    "field_rat": (300, "Comes in a pack, runs straight at you and nibbles. One hit each."),
    "farmhand": (500, "Slow, tough, walks straight at you with a pitchfork."),
    "goose": (400, "A honking gaggle of three. Fast, weak, very annoying."),
    "hound": (800, "Hunts in threes: they circle and dart in to bite one at a time."),
    "hawk": (800, "Circles over everything, lines up and dives. Step off the line."),
    "molehill": (700, "Sends out mole rats until you break it."),
    "mole_rat": (300, "Pops out of a molehill and nips."),
    "bull": (1500, "Charges through anything that breaks, again and again. Walls stop it."),
    "slinger": (500, "Keeps its distance and slings three stones at a time."),
    "lancer": (1000, "Rides wide, lowers the lance and gallops through. Sidestep the line."),
    "shieldbearer": (1500, "Nothing gets past the shield from the front. After a bash it's open."),
    "priest": (900, "Heals the most hurt enemy near it. Take it down first."),
    "straw_golem": (900, "Swings hard and slow; dies in a burst of burning straw."),
    "scarecrow": (800, "Shuffles along and lets loose crows."),
    "crow": (300, "The scarecrow's. Pecks, then flaps off after a while."),
    "drummer": (900, "Everyone in its ring is faster and hits harder. Runs from you."),
    # M17: filled in by beating the swamp's boss (or bought).
    "psy_frog": (1500, "They hide out across the swamp. Keeps away, spits weaving globs."),
    "froggy": (5000, "Dives between pools, lashes its tongue, belly-flops. Hit it while it's dazed."),
    # M22
    "bloated_leech": (1500, "Crawls at you and bites. Popped, it bursts into leechlings."),
    "leech_swarm": (5000, "A hundred and twenty leeches, one hunger. If they latch on, roll to shake them off."),
    # M22.2
    "mosquito": (800, "Buzzes in, hovers a moment, stings, darts off. Flies over everything."),
    "proboscia": (5000, "Dives to bite and drinks. Fat with blood she slows: hit hard and POP her."),
    # M23.1
    "golden_scarab": (1500, "Runs from you, and digs in if you're too slow. Worth its weight in gold."),
    "scarab": (800, "Scuttles out of the sand at Khepri's call and nips."),
    "khepri": (5000, "Rolls a dung ball that grows. Bait it into a pillar: it shatters, he's stunned."),
    # M23.2
    "mangy_camel": (1500, "Sits on lost cargo, keeps its distance and spits."),
    "mirage": (800, "Ol' Spitter's heat-haze double. Spits like him; one hit and it's gone."),
    "ol_spitter": (5000, "His humps hold his spit. Dry, he drinks: smash the trough and he chokes."),
    # M23.3
    "sand_elemental": (1500, "Rises from the sand round a star circle. Blinks about, throws sand bolts."),
    "sand_golem": (800, "Climbs out of the Magus's runes, plods at you and slams the ground."),
    "nameless_magus": (5000, "Scuff out his runes before they fire. Shatter his hourglass before time's up."),
    # M24.1
    "glowing_ghoul": (1500, "Rushes you in packs and bursts green when it dies."),
    "fallout_king": (5000, "Watch your rads. Smash the rods, shut the valves, hide behind lead."),
    # M24.2
    "frost_wraith": (1500, "Drifts through walls to freeze the thawing. Keep it off them."),
    "snow_king": (5000, "Knock off his crown and kick it away. Light the fires; keep moving."),
    # M24.3
    "vampire_bat": (1500, "Flits in to bite. Guarded Mr. Buttons' pieces for a pawn dealer."),
    "thrall": (800, "Climbs out of Fragile's coffins. Stake an empty one to keep it shut."),
    "fragile": (5000, "Open the shutters: she burns in the sun. Roll on the beat. Bring the bear."),
    # M25.1
    "blighted_sprite": (1500, "Rises round a blighted shrine to stop you cleansing it."),
    "rot_moth": (800, "Flutters in at Nettle's call and bites."),
    "nettle": (5000, "Only the real one casts a shadow. Growcaps undo her dust. Pull her seeds."),
}

# Achievements (they unlock "A:" cards).
ACHIEVEMENTS = {
    "chain_reaction": "kill 15 enemies within 1 second",
    "crit_75": "reach 75% crit chance",
    "level_30": "reach level 30",
    "froggy": "defeat Froggy McFrogface",
    "leech_swarm": "defeat the Leech Swarm",
    "proboscia": "defeat Lady Proboscia",
    "khepri": "defeat Khepri the Dung Emperor",
    "ol_spitter": "defeat Ol' Spitter, the Unmannered One",
    "nameless_magus": "defeat the Nameless Magus, Holder of Time",
    "fallout_king": "defeat the Fallout King",
    "snow_king": "defeat the Snow King, King of Loneliness",
    "fragile": "defeat Fragile, The Misunderstood",
    "nettle": "defeat Nettle, the Blighted",
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
# Mounts (P6, render/mounts.py): a riding hero shows its top MOUNT_RIDER_ROWS
# art rows; four-legged mounts change step every 1 / MOUNT_STEPS_PER_TILE
# tiles; a floating carpet bobs (radians/s, art pixels).
MOUNT_RIDER_ROWS = 11
# Riding (P6, systems/mount.py; user's picks: called every run, travel only,
# +75%, one look per hero). Q / gamepad Y whistles: MOUNT_CALL_TIME s later
# you're riding, MOUNT_SPEED faster. A hit throws you off, and it can't be
# called again for MOUNT_THROWN s (the Stable takes off up to the
# difference with MOUNT_MIN_COOLDOWN).
MOUNTS_ON = True              # False: no riding at all (the whole feature is off)
HERO_MOUNTS = {"wizard": "carpet", "dwarf": "ram", "bard": "donkey", "princess": "pony",
               "huntress": "stag"}
MOUNT_SPEED = 0.75
MOUNT_CALL_TIME = 1.0
MOUNT_THROWN = 10.0
MOUNT_MIN_COOLDOWN = 5.0
MOUNT_STEPS_PER_TILE = 1.6
MOUNT_FLOAT_BOB = (3.0, 2)

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
# P1 (2026-10-10, user: "the map is too big") cut the radius by 20%:
#   2761 * 0.8 = 2209 (area -36%); centre to coast ~4.3 min. The plains keep
#   their fraction, so every biome shrinks by the same share, and the noise
#   sizes below (COAST_SCALE, PLAINS_EDGE_SCALE, BIOME_WARP_SCALE) shrank by
#   the same 0.8, so it's the same-shaped island, smaller.
WORLD_RADIUS = 2209
# The coastline wanders in and out by up to this fraction of WORLD_RADIUS
# (fBm noise; COAST_SCALE is the size of its biggest bays and capes, and
# COAST_OCTAVES adds ever smaller wiggles down to ~COAST_SCALE / 2**(n-1)).
COAST_AMPLITUDE = 0.2
COAST_SCALE = 1920
COAST_OCTAVES = 6
# The central plains reach this fraction of WORLD_RADIUS, their edge
# wandering by PLAINS_EDGE_AMPLITUDE (fraction of the plains radius).
PLAINS_RADIUS_FRACTION = 0.2612
PLAINS_EDGE_AMPLITUDE = 0.2
PLAINS_EDGE_SCALE = 720
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
BIOME_WARP_SCALE = 1280
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
# Haunted forest (M21, world/generator._haunt). The ground is cut into
# HAUNT_CELL x HAUNT_CELL cells on the global grid; each cell rolls one
# thing: a gnarled tree (its trunk 1-3 tiles in from the cell's left edge and
# 2-3 from its top, so trunks stand at least 3 tiles apart and their crowns
# never overlap), else a fallen log, else a wisp light, else nothing.
HAUNT_CELL = 5
HAUNT_TREE_CHANCE = 0.55
HAUNT_LOG_CHANCE = 0.06
HAUNT_WISP_CHANCE = 0.05
HAUNT_STUMP_CHANCE = 0.012   # per tile: a lone stump
HAUNT_FOG_MIN = 0.64         # detail field above this -> fog patches
STUMP_HP = 30
LOG_HP = 60
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
# Every quest is in every run (M22.5): each biome has several, keyed by
# name, each with its own giver, camp and lair at random spots in the biome
# (P2: the givers are pinned from the start; the lairs once their boss
# wakes). The quests are hidden: their targets are out
# from the start and any player can finish one without its giver. Talking
# to the giver gives hints and a counter on the HUD. Finishing a quest wakes
# its boss at its lair (pinned from then on). A boss beaten in each of the
# 5 ring biomes ("guardians") unlocks the plains boss, whose Adventurer's
# Glory can end the run (later milestones).
QUESTS = {
    "bad_trip": QuestSpec(
        title="Bad Trip", biome="swamp", giver="frog hunter", giver_sprite="frog_hunter",
        camp="frog_camp", lair="pond_lair", target="psy_frog", count=5, boss="froggy",
        goal="Psychedelic frogs {n}/{count}", camp_name="FROG HUNTER", lair_name="FROGGY'S POND",
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
    # M22. A stand-in quest (the user will give the real one); the camp and
    # the lair reuse the frog hunter's and the pond's layouts, in blood.
    "leech_doctor": QuestSpec(
        title="Bad Blood", biome="swamp", giver="leech doctor", giver_sprite="leech_doctor",
        camp="frog_camp", lair="pond_lair", target="bloated_leech", count=5, boss="leech_swarm",
        goal="Bloated leeches {n}/{count}", camp_name="LEECH DOCTOR", lair_name="THE BLOOD MIRE",
        skin="blood",
        lines=(
            ("offer", ("Ah, a visitor. Do mind the jars.",
                       "My prize leeches got out. Fat, they are.",
                       "Gorged on something they shouldn't have.",
                       "Pop five of them before they breed.",
                       "Mind the little ones that come out.")),
            ("progress", ("{left} more bloated ones out there.",
                          "They're all over the swamp by now.")),
            ("done", ("Five! But listen... that squelching.",
                      "The mire. The whole brood is waking.",
                      "If they latch on, roll! Shake them off!")),
            ("fight", ("The swarm's up at the mire! Go!",)),
            ("cleared", ("The swarm, gone? Remarkable.",
                         "I'll start a new collection. Smaller ones.")),
        ),
    ),
    # M22.2. A "light" quest: stand by `count` of the smoke keeper's old
    # braziers (scattered over the swamp like hunt targets) until each
    # catches; the mosquitoes come for whoever is lighting one. The camp and
    # the lair are the frog hunter's and the pond's layouts, gone stagnant.
    "smoke_keeper": QuestSpec(
        title="Smoke Signals", biome="swamp", giver="smoke keeper", giver_sprite="smoke_keeper",
        camp="frog_camp", lair="pond_lair", target="", count=4, boss="proboscia",
        goal="Braziers lit {n}/{count}", camp_name="SMOKE KEEPER", lair_name="THE STAGNANT COURT",
        skin="stagnant", kind="light",
        lines=(
            ("offer", ("Hear that whine? That's HER brood.",
                       "Lady Proboscia. Drinks a cow dry by night.",
                       "Smoke drives the swarm home to her court.",
                       "Light four of my old braziers out there.",
                       "Stand by one a while and it'll catch.",
                       "The biters won't like it. Swat 'em.")),
            ("progress", ("{left} more braziers to light.",
                          "Stand close till the smoke rises.")),
            ("done", ("Smell that smoke? The swarm's flown home.",
                      "Her Ladyship's awake at the Stagnant Court.",
                      "When she's fat with blood, hit her HARD!")),
            ("fight", ("Her Ladyship's at court! Go!",)),
            ("cleared", ("Lady Proboscia, swatted! Ha!",
                         "I'll sleep without a net tonight.")),
        ),
    ),
    # M23.1: the desert. Golden scarabs flee and dig in (ai/creatures.
    # GoldenScarab); the camp is a nomad tent by an oasis and the lair a
    # sunken sandstone arena (world/landmarks.py), both shared by the
    # desert's bosses.
    "scarab_collector": QuestSpec(
        title="Golden Touch", biome="desert", giver="scarab collector",
        giver_sprite="scarab_collector", camp="oasis_camp", lair="sand_lair",
        target="golden_scarab", count=5, boss="khepri", goal="Golden scarabs {n}/{count}",
        camp_name="SCARAB COLLECTOR", lair_name="THE DUNG PIT",
        lines=(
            ("offer", ("Psst. You. Ever seen a GOLDEN scarab?",
                       "Worth a fortune. And skittish as sin.",
                       "They run when they see you coming.",
                       "Too slow, and they dig in and they're gone.",
                       "Bring down five. I'll make it worth it.")),
            ("progress", ("{left} more golden ones out there.",
                          "Corner them before they dig in!")),
            ("done", ("Five! But... the sand's shaking.",
                      "The gold is HIS. The Dung Emperor's.",
                      "Lure his ball into the pillars. Trust me.")),
            ("fight", ("Khepri's up at the Dung Pit! Go!",)),
            ("cleared", ("Khepri, beaten? The Emperor himself!",
                         "I'm rich! Well. You're rich. Mostly me.")),
        ),
    ),
    # M23.2: a "collect" quest. The caravan master's cargo bundles lie in
    # the quest's clearings, each guarded by CARGO_GUARDS mangy camels; with
    # the guards gone, walk up to a bundle to take it (systems/quests.py).
    # The camp is the oasis layout with crates; the lair, Ol' Spitter's
    # caravanserai (world/landmarks._caravanserai).
    "caravan_master": QuestSpec(
        title="Lost Cargo", biome="desert", giver="caravan master",
        giver_sprite="caravan_master", camp="oasis_camp", lair="caravanserai",
        target="mangy_camel", count=5, boss="ol_spitter", goal="Cargo bundles {n}/{count}",
        camp_name="CARAVAN MASTER", lair_name="THE CARAVANSERAI", skin="caravan",
        kind="collect",
        lines=(
            ("offer", ("Adventurer! A word, a word, please.",
                       "My lead camel threw a fit and bolted.",
                       "My cargo's scattered all over the desert.",
                       "Mangy strays sit on every bundle now.",
                       "Run them off and bring back five.")),
            ("progress", ("{left} more bundles out there.",
                          "The strays won't give them up kindly.")),
            ("done", ("Five! But... that bellow. Hear it?",
                      "That's HIM. Ol' Spitter. My lead camel.",
                      "He's holed up in the old caravanserai.",
                      "When his humps run dry, he drinks.",
                      "Smash his trough while he drinks!")),
            ("fight", ("Ol' Spitter's at the caravanserai! Go!",)),
            ("cleared", ("Ol' Spitter, tamed? I never thought...",
                         "Manners at last. Well. Fewer spits.")),
        ),
    ),
    # M23.3: a "survive" quest. The camp's spots hold sealed star circles;
    # stand in one SEAL_TIME s (in total) to break its seal while sand
    # elementals rise round you (systems/quests.py). The lair is the sunken
    # observatory (world/landmarks._observatory).
    "runaway_apprentice": QuestSpec(
        title="Broken Seals", biome="desert", giver="runaway apprentice",
        giver_sprite="runaway_apprentice", camp="oasis_camp", lair="observatory",
        target="sand_elemental", count=4, boss="nameless_magus", goal="Seals broken {n}/{count}",
        camp_name="RUNAWAY APPRENTICE", lair_name="THE SUNKEN OBSERVATORY", skin="apprentice",
        kind="survive",
        lines=(
            ("offer", ("You! You can see me? Good. Listen.",
                       "My old master has no name. Not any more.",
                       "He took my years for his hourglass.",
                       "He hides under the sand, behind seals.",
                       "Stars are drawn round each seal. Stand in one.",
                       "Hold it until the seal breaks. Four of them.",
                       "The sand will fight you. Hold anyway.")),
            ("progress", ("{left} more seals to break.",
                          "Stay in the circle. Leave and it heals.")),
            ("done", ("Four! He can't hide now. He's coming up.",
                      "The sunken observatory. That's his.",
                      "Scuff his runes out before they fire.",
                      "And if he turns the hourglass... break it.")),
            ("fight", ("The Magus is up! The observatory! Go!",)),
            ("cleared", ("He's gone? Then my years...",
                         "I feel them coming back. Thank you.")),
        ),
    ),
    # M24.1: an "escort" quest (systems/quests._escort). The scavenger
    # follows whoever took the quest to the beacon sites (the camp's spots)
    # and plants a beacon at each (ESCORT_SETUP s) while glowing ghouls pour
    # in -- for the players, not for her: she can't be hurt. She has to be
    # talked to first (she's the one doing it). The lair is the reactor
    # vault (world/landmarks._reactor_vault).
    "hazmat_scavenger": QuestSpec(
        title="Geiger Readings", biome="ruins", giver="hazmat scavenger",
        giver_sprite="hazmat_scavenger", camp="scrap_camp", lair="reactor_vault",
        target="glowing_ghoul", count=4, boss="fallout_king", goal="Beacons planted {n}/{count}",
        camp_name="HAZMAT SCAVENGER", lair_name="THE REACTOR VAULT", kind="escort",
        lines=(
            ("offer", ("Whoa. Don't touch anything. Glowing, see?",
                       "Something under these ruins is cooking.",
                       "I need sensor beacons out there. Four.",
                       "Walk me to the sites, I'll plant them.",
                       "The ghouls will come for you, not me.",
                       "This suit's seen worse. Lead the way!")),
            ("progress", ("{left} more beacons to plant.",
                          "Lead on. I'm right behind you.")),
            ("done", ("Readings are off the chart. It's HIM.",
                      "The Fallout King. In the old reactor vault.",
                      "Watch your rads. Use the showers.",
                      "And if his core heats up... hide behind lead.")),
            ("fight", ("The King's awake in the vault! Go!",)),
            ("cleared", ("The readings... they're dropping!",
                         "You did it. The ruins can breathe again.")),
        ),
    ),
    # M24.2: a "rescue" quest (systems/quests._rescue): the camp's spots
    # hold people frozen in ice blocks (destructible tiles). Shatter one and
    # the captive thaws over RESCUE_THAW s while a hero stands by them;
    # frost wraiths come to re-freeze them. The lair is the frozen throne
    # hall (world/landmarks._throne_hall).
    "searching_sister": QuestSpec(
        title="Cold Hearts", biome="ruins", giver="searching sister",
        giver_sprite="searching_sister", camp="scrap_camp", lair="throne_hall",
        target="frost_wraith", count=4, boss="snow_king", goal="Captives freed {n}/{count}",
        camp_name="SEARCHING SISTER", lair_name="THE FROZEN THRONE HALL", skin="frost",
        kind="rescue",
        lines=(
            ("offer", ("Please. Have you seen my sister?",
                       "The Snow King took her. Took lots of us.",
                       "He freezes people. Keeps them. For company.",
                       "Break the ice. Then stay with them, close,",
                       "until they thaw. Wraiths will try to stop you.",
                       "Free four and he'll come looking. He always does.")),
            ("progress", ("{left} more to free. She could be any of them.",
                          "Stay close while they thaw. Keep them warm.")),
            ("done", ("Four free! And... there. That cold wind.",
                      "He's in his frozen throne hall. Angry.",
                      "Knock his crown off: he's nothing without it.",
                      "And light the fires. Don't stand still.")),
            ("fight", ("The Snow King's in his hall! Go!",)),
            ("cleared", ("He's... crying? He just wanted friends.",
                         "My sister's home. Thank you. Truly.")),
        ),
    ),
    # M24.3: a "fetch" quest (systems/quests._fetch): the camp's spots hold
    # the pieces of Fragile's old bear, each guarded like the cargo; pick one
    # up and carry it to the dealer's stall. Sewn back together, Mr. Buttons
    # stays with whoever brought the last piece: carry him into the ruined
    # ballroom (world/landmarks._ballroom). Beaten, Fragile sits there crying
    # -- give her the bear (talk to her) for FRAGILE_GIFT_LEVELS levels.
    "pawn_dealer": QuestSpec(
        title="Mr. Buttons", biome="ruins", giver="pawn dealer", giver_sprite="pawn_dealer",
        camp="scrap_camp", lair="ballroom", target="vampire_bat", count=4, boss="fragile",
        goal="Mr. Buttons pieces sewn {n}/{count}", camp_name="PAWN DEALER",
        lair_name="THE RUINED BALLROOM", skin="pawn", kind="fetch",
        lines=(
            ("offer", ("Psst. Wanna buy a teddy bear? ...No?",
                       "Okay. I MAY have stolen it. From a vampire.",
                       "Mr. Buttons, she called him. Then he... tore.",
                       "Four pieces, all over the ruins. Bats on 'em.",
                       "Bring 'em here, I'll sew him back up.",
                       "Then maybe... you give him back? To her?")),
            ("progress", ("{left} more pieces of Mr. Buttons.",
                          "Bring every piece you find back here.")),
            ("done", ("Good as new! Well. Good as used.",
                      "Take him. She's in the old ballroom. Waiting.",
                      "She's... upset. Open the shutters. Sun burns her.",
                      "And when it's over... give him back. Please.")),
            ("fight", ("She's at the ballroom! Take Mr. Buttons!",)),
            ("cleared", ("You gave him back? She smiled? Huh.",
                         "Maybe I'll stop stealing from vampires.")),
        ),
    ),
    # M25.1: a "cleanse" quest (systems/quests._hold_seals, like "survive"):
    # the camp's spots hold blighted shrines; stand in one's ring to cleanse
    # it (the ring tightens as it cleans) while blighted sprites rise round
    # you. The lair is the withered glade (world/landmarks._glade).
    "hedge_witch": QuestSpec(
        title="Cleanse the Shrines", biome="forest", giver="hedge witch",
        giver_sprite="hedge_witch", camp="witch_camp", lair="glade", target="blighted_sprite",
        count=4, boss="nettle", goal="Shrines cleansed {n}/{count}", camp_name="HEDGE WITCH",
        lair_name="THE WITHERED GLADE", kind="cleanse",
        lines=(
            ("offer", ("Hush. Hear that? The trees are sick.",
                       "A pixie did it. Nettle. She was sweet once.",
                       "Something rotten got into her, and she spread it.",
                       "The old shrines keep this wood well. She blighted them.",
                       "Stand in a shrine's ring until it's clean.",
                       "Her sprites will come for you. Four shrines will do.")),
            ("progress", ("{left} more shrines to cleanse.",
                          "Stay in the ring. It tightens as it cleans.")),
            ("done", ("Four clean! She felt that. She's in her glade.",
                      "The withered glade, ringed with toadstools.",
                      "Her copies cast no shadow. Watch the ground.",
                      "Shrunk by her dust? Stand on a growcap.",
                      "And pull her seeds before the rot spreads.")),
            ("fight", ("Nettle's in the glade! Go!",)),
            ("cleared", ("The rot's lifting. Smell that? Moss.",
                         "Poor Nettle. Maybe she can heal too, now.")),
        ),
    ),
}
# Developer / test: the quest key the dev keys (F6 to its giver, F7 finish
# it, F8 to its lair) act on; run.py --boss sets it. None: the first quest
# not beaten yet.
QUEST_FOCUS: str | None = None
# The main quest: beat a boss ("guardian") in this many ring biomes -- one
# per biome counts; the other bosses are optional, for their loot and
# achievements (M22.5) -- then the plains boss, for Adventurer's Glory.
GUARDIANS = 5

# Quest givers: how close you must stand to talk (E / gamepad A), and how
# long each line they say stays over their head.
TALK_RADIUS = 3.0
SPEECH_LINE_TIME = 2.6

# The frog hunter's camp (world/landmarks.py): a bog oval of these radii
# (tiles) with his hut on the side facing the plains. Pools where the bog's
# noise field is above CAMP_POOL_MIN (higher: fewer, smaller pools).
CAMP_BOG_RADII = (34, 15)
CAMP_OASIS_RADII = (24, 11)     # the scarab collector's oasis (M23.1)
CAMP_POOL_MIN = 0.58
# Every quest's camp and lair go at random spots anywhere in their biome
# (M22.5, world/landmarks._random_site), from QUEST_SITE_TRIES random
# points, at least QUEST_SITE_GAP tiles from every other camp and lair.
QUEST_SITE_TRIES = 600
QUEST_SITE_GAP = 60

# A quest's targets (the psychedelic frogs) are scattered over the whole
# biome (world/landmarks._scatter), not left at the camp: QUEST_SPOT_FACTOR
# times as many as the quest needs (any `count` of them will do; P2,
# 2026-10-10, was count + 3: the user wants 3-4x, so 5 -> 20), at least
# QUEST_SPOT_SEPARATION tiles apart (less if the biome is too small) and
# QUEST_SPOT_CAMP_GAP from the giver, at least QUEST_SPOT_EDGE tiles inside
# the biome, each in a mud clearing of radius QUEST_SPOT_CLEARING tiles.
# Picked from QUEST_SPOT_CANDIDATES random points. (One screen: ~86 x 30.)
QUEST_SPOT_FACTOR = 4
QUEST_SPOT_SEPARATION = 220
QUEST_SPOT_CAMP_GAP = 200
QUEST_SPOT_EDGE = 16
QUEST_SPOT_CLEARING = 4
QUEST_SPOT_CANDIDATES = 1000
# ...and at least this far from another quest's spots.
QUEST_SPOT_OTHERS = 60
# A taken quest's living target shows on the maps (minimap and big map)
# only within this many tiles of you -- its "general area" -- and the
# minimap then points the way in. (P2 follow-up, user: "be generous";
# was 160, about 30 s of walking now.)
QUEST_TARGET_PIN_RADIUS = 250
# "light" quests (M22.2, systems/quests.py): a brazier catches after
# BRAZIER_LIGHT_TIME s with a hero within BRAZIER_RADIUS tiles of it; with
# nobody there its heat falls back BRAZIER_COOL x as fast. As its heat
# passes each fraction in BRAZIER_SWARMS, BRAZIER_SWARM_SIZE mosquitoes come
# buzzing in from BRAZIER_SWARM_RANGE tiles away (each wave once).
BRAZIER_LIGHT_TIME = 5.0
BRAZIER_RADIUS = 3.0
BRAZIER_COOL = 0.5
BRAZIER_SWARMS = (0.0, 0.5)
BRAZIER_SWARM_SIZE = 3
BRAZIER_SWARM_RANGE = (10.0, 13.0)
# "collect" quests (M23.2, systems/quests.py): CARGO_GUARDS of the quest's
# `target` enemy sit round each bundle (CARGO_GUARD_RING tiles out); once
# they're all dead, a hero within CARGO_RADIUS tiles of the bundle takes it.
CARGO_GUARDS = 3
CARGO_GUARD_RING = 3.0
CARGO_RADIUS = 2.6
# "survive" quests (M23.3, systems/quests.py): a hero inside a star circle
# (SEAL_RADIUS tiles of its middle) wears its seal down; SEAL_TIME s of it
# breaks it. With nobody inside, it heals back SEAL_HEAL x as fast. Every
# SEAL_WAVE s someone's inside, SEAL_WAVE_SIZE (low, high) of the quest's
# `target` enemies rise SEAL_WAVE_RANGE tiles from the middle.
SEAL_RADIUS = 4.0
SEAL_TIME = 30.0
SEAL_HEAL = 0.5
SEAL_WAVE = 8.0
SEAL_WAVE_SIZE = (2, 3)
SEAL_WAVE_RANGE = (8.0, 12.0)
# "escort" quests (M24.1, systems/quests._escort): once taken, the giver
# follows the nearest player within ESCORT_RANGE tiles, ESCORT_GAP behind,
# at ESCORT_SPEED tiles/s (a long way behind or stuck, she catches up). At
# a site (within ESCORT_SITE tiles of a spot) she plants a beacon over
# ESCORT_SETUP s; a wave of the quest's `target` enemies comes at each of
# ESCORT_WAVES s into it (ESCORT_WAVE_SIZE each, ESCORT_WAVE_RANGE tiles
# off), alert and after the players.
ESCORT_RANGE = 30.0
ESCORT_GAP = 2.5
ESCORT_SPEED = 9.0
ESCORT_SITE = 3.0
ESCORT_SETUP = 10.0
ESCORT_WAVES = (0.0, 3.5, 7.0)
ESCORT_WAVE_SIZE = 3
ESCORT_WAVE_RANGE = (10.0, 13.0)
CAMP_SCRAP_RADII = (22, 10)     # the scavenger's scrap camp (M24.1)
# "rescue" quests (M24.2, systems/quests._rescue): a captive's ice block
# (tiles.ICE_BLOCK, RESCUE_BLOCK_HP) shattered, they thaw while a hero is
# within RESCUE_WARM tiles: RESCUE_THAW s of it frees them. A wave of
# RESCUE_WAVE_SIZE of the quest's `target` comes at each RESCUE_WAVES mark
# (RESCUE_WAVE_RANGE tiles off), drifting at the captive; one that touches
# them knocks RESCUE_REFREEZE of the thaw back.
RESCUE_BLOCK_HP = 200
RESCUE_WARM = 3.0
RESCUE_THAW = 8.0
RESCUE_WAVES = (0.0, 3.0, 6.0)
RESCUE_WAVE_SIZE = 2
RESCUE_WAVE_RANGE = (10.0, 13.0)
RESCUE_REFREEZE = 0.3
# "fetch" quests (M24.3, systems/quests._fetch): FETCH guards round each
# piece like the cargo's (CARGO_GUARDS of the quest's `target`); with them
# dead, a hero within CARGO_RADIUS takes it. Carried pieces are delivered by
# coming within FETCH_DELIVER tiles of the giver. A downed hero drops what
# they carry (pieces, the bear) where they fell; any hero within
# FETCH_PICKUP tiles picks it up.
FETCH_DELIVER = 3.5
FETCH_PICKUP = 1.6
FRAGILE_GIFT_LEVELS = 5       # levels for giving Fragile her bear back (every player)
# "cleanse" quests (M25.1, systems/quests._hold_seals): a hero inside a
# blighted shrine's ring cleanses it; CLEANSE_TIME s of it and it's clean.
# The ring shrinks from CLEANSE_RADIUS[0] to [1] tiles as it cleans. With
# nobody inside, it slides back CLEANSE_HEAL x as fast. Every CLEANSE_WAVE s
# of cleansing, CLEANSE_WAVE_SIZE (low, high) of the quest's `target` rise
# CLEANSE_WAVE_RANGE tiles off.
CLEANSE_TIME = 20.0
CLEANSE_RADIUS = (4.5, 2.0)
CLEANSE_HEAL = 0.5
CLEANSE_WAVE = 5.0
CLEANSE_WAVE_SIZE = (2, 3)
CLEANSE_WAVE_RANGE = (8.0, 12.0)
CAMP_WITCH_RADII = (20, 9)      # the hedge witch's camp: a black pond in the fog

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
SAND_LAIR_PILLARS = 36          # the Dung Pit's: taller (Khepri's ball breaks on them)
# Ol' Spitter's caravanserai (M23.2, world/landmarks._caravanserai): the
# same oval and gate in mud brick, with CARAVAN_ARCADES rows of brick arches
# (CARAVAN_ARCHES each, 3 x 2 tiles) across the yard, CARAVAN_TROUGHS stone
# water troughs (6 x 1 tiles, TROUGH_HP each tile) round the middle, and
# CARAVAN_POSTS tethering posts.
CARAVAN_ARCADES = 4
CARAVAN_ARCHES = 9
CARAVAN_TROUGHS = 6
CARAVAN_POSTS = 26
TROUGH_HP = 160
# The Nameless Magus's sunken observatory (M23.3, world/landmarks.
# _observatory): the same oval and gate in blue-glazed stone round a
# sandstone floor; a round star chart (OBSERVATORY_CHART tiles across) in
# the middle; broken columns (2 x 2) in OBSERVATORY_RINGS rings round it,
# a fallen brass telescope, sand drifts.
OBSERVATORY_CHART = 14
OBSERVATORY_RINGS = ((0.32, 10), (0.58, 14), (0.84, 18))   # (oval fraction, columns)
# The Fallout King's reactor vault (M24.1, world/landmarks._reactor_vault):
# the oval and gate in concrete walls; a cracked reactor ring in the
# middle; VAULT_PILLARS concrete pillars, VAULT_PIPES pipe runs; round the
# edge 4 coolant valves and 4 decontamination showers; 4 lead walls (4 x 1)
# and 6 sewer grates through the room.
VAULT_PILLARS = 28
VAULT_PIPES = 6
# The Snow King's frozen throne hall (M24.2, world/landmarks._throne_hall):
# the oval and gate in ice walls round frost-stone; his throne at the north
# end; HALL_PILLAR_ROWS rows of ice pillars (2 x 2, ICE_PILLAR_HP a tile:
# shatter them, he regrows them ICE_PILLAR_REGROW s later); 4 fire
# braziers; HALL_STATUES frozen statues; snowdrifts.
HALL_PILLAR_ROWS = ((-0.45, 9), (0.0, 7), (0.45, 9))   # (fraction of b, pillars a row)
ICE_PILLAR_HP = 120
ICE_PILLAR_REGROW = 20.0
HALL_STATUES = 10
# Fragile's ruined ballroom (M24.3, world/landmarks._ballroom): the oval and
# gate in castle stone round a parquet floor; BALLROOM_WINDOWS shuttered
# windows a long wall (each with a lever below it: props["windows"],
# props["levers"]); coffins and her throne at the far end; BALLROOM_PILLARS
# rows of marble pillars; BALLROOM_CHANDELIERS chandeliers (props).
BALLROOM_WINDOWS = 3
BALLROOM_PILLARS = ((-0.35, 8), (0.35, 8))
BALLROOM_CHANDELIERS = 4
BALLROOM_COFFINS = 5
# Nettle's withered glade (M25.1, world/landmarks._glade): the oval and gate
# in bramble round a floor of dead leaves and fog; a dead hollow tree in the
# middle (GLADE_TREE tiles, w x h); GLADE_TOADSTOOLS giant toadstools in a
# ring GLADE_RING of the way out (cover); GLADE_GROWCAPS glowing growcaps
# further out (props["growcaps"]); GLADE_STUMPS stumps.
GLADE_TREE = (8, 4)
GLADE_TOADSTOOLS = 26
GLADE_RING = 0.5
GLADE_GROWCAPS = 6
GLADE_STUMPS = 24
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
# Boss difficulty (2026-10-05, design/BOSSES.md 5.6). Every boss's health
# and damage x these, on top of the level and co-op scaling.
BOSS_HP_MULT = 1.0
BOSS_DMG_MULT = 1.2
# Predictive aim: the shots and lunges that "lead" aim where the target will
# be if it keeps moving -- ahead by the shot's flight time (or the move's
# wind-up) x BOSS_LEAD, at most BOSS_LEAD_MAX tiles. Each move mixes them
# with shots straight at you, so neither circle-strafing nor standing still
# dodges everything: changing direction does.
BOSS_LEAD = 0.85
BOSS_LEAD_MAX = 10.0
# Combos, per phase: (chance, most extra moves). After a move the boss may
# go straight into another BOSS_COMBO_GAP s later -- the first one's shots
# still flying, the next one's tell still shown -- and rests after the combo.
BOSS_COMBO = ((0.0, 0), (0.45, 1), (0.65, 2))
BOSS_COMBO_GAP = 0.15
# Per phase: tells (wind-ups, aim lines, ripples) x BOSS_TELL_SCALE, never
# under BOSS_MIN_TELL s; the rest between moves x BOSS_REST_SCALE.
BOSS_TELL_SCALE = (1.0, 0.85, 0.7)
BOSS_REST_SCALE = (1.0, 0.85, 0.7)
BOSS_MIN_TELL = 0.3

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
    # M22 (ai/bosses.LeechSwarm, design/BOSSES.md section 12).
    "leech_swarm": BossSpec(
        name="The Leech Swarm",
        phases=(
            BossPhase(1.0, (("surge", 3), ("split", 2)), rest=1.0),
            BossPhase(0.6, (("surge", 2), ("split", 2), ("spit", 3), ("nest", 2)), rest=0.85),
            BossPhase(0.25, (("surge", 2), ("spit", 2), ("nest", 1), ("whirlpool", 3)), rest=0.6),
        ),
        loot=2500, achievement="leech_swarm", pages=("leech_swarm", "bloated_leech"),
    ),
    # M22.2 (ai/bosses.Proboscia, design/BOSSES.md section 13).
    "proboscia": BossSpec(
        name="Lady Proboscia",
        phases=(
            BossPhase(1.0, (("bite", 3), ("fan", 3), ("sip", 2)), rest=1.0),
            BossPhase(0.6, (("bite", 2), ("fan", 2), ("buzz", 3), ("call", 2), ("sip", 1)),
                      rest=0.85),
            BossPhase(0.25, (("bite", 3), ("fan", 1), ("buzz", 2), ("call", 1), ("sip", 1)),
                      rest=0.6),
        ),
        loot=2500, achievement="proboscia", pages=("proboscia", "mosquito"),
    ),
    # M23.1 (ai/bosses.Khepri, design/BOSSES.md section 15).
    "khepri": BossSpec(
        name="Khepri the Dung Emperor",
        phases=(
            BossPhase(1.0, (("roll", 4), ("charge", 2), ("burrow", 2)), rest=1.0),
            BossPhase(0.6, (("roll", 3), ("charge", 2), ("burrow", 2), ("storm", 2),
                            ("swarm", 1)), rest=0.85),
            BossPhase(0.25, (("roll", 4), ("charge", 1), ("burrow", 2), ("storm", 2),
                             ("swarm", 1)), rest=0.6),
        ),
        loot=2500, achievement="khepri", pages=("khepri", "golden_scarab"),
    ),
    # M23.2 (ai/bosses.OlSpitter, design/BOSSES.md section 16). His kick
    # isn't in the lists: he bucks whenever someone lingers behind him.
    "ol_spitter": BossSpec(
        name="Ol' Spitter, the Unmannered One",
        phases=(
            BossPhase(1.0, (("fan", 3), ("mortar", 2), ("loogie", 3), ("gallop", 2)), rest=1.0),
            BossPhase(0.6, (("fan", 2), ("mortar", 2), ("loogie", 3), ("gallop", 2),
                            ("stampede", 2)), rest=0.85),
            BossPhase(0.25, (("fan", 1), ("mortar", 2), ("loogie", 3), ("gallop", 1),
                             ("stampede", 2), ("mirage", 1), ("spiral", 3)), rest=0.6),
        ),
        loot=2500, achievement="ol_spitter", pages=("ol_spitter", "mangy_camel", "mirage"),
    ),
    # M23.3 (ai/bosses.Magus, design/BOSSES.md section 17). One signature
    # a phase, kept: runes; + dunes; + the hourglass (the user's curve).
    "nameless_magus": BossSpec(
        name="Nameless Magus, Holder of Time",
        phases=(
            BossPhase(1.0, (("runes", 3), ("lance", 2), ("sigils", 3), ("blink", 2),
                            ("serpent", 2)), rest=1.0),
            BossPhase(0.6, (("runes", 3), ("lance", 2), ("sigils", 3), ("blink", 2),
                            ("serpent", 2), ("dunes", 2), ("vortex", 2)), rest=0.85),
            BossPhase(0.25, (("runes", 3), ("lance", 2), ("sigils", 3), ("blink", 2),
                             ("serpent", 2), ("dunes", 2), ("vortex", 2), ("hourglass", 2)),
                      rest=0.6),
        ),
        loot=2500, achievement="nameless_magus",
        pages=("nameless_magus", "sand_elemental", "sand_golem"),
    ),
    # M24.1 (ai/bosses.FalloutKing, design/BOSSES.md section 18): rads all
    # fight; + fallout (the stomp); + the meltdown core (a gauge of its own).
    "fallout_king": BossSpec(
        name="The Fallout King",
        phases=(
            BossPhase(1.0, (("gamma", 2), ("barrels", 3), ("skulls", 2), ("ghouls", 2),
                            ("grate", 2), ("emp", 2)), rest=1.0),
            BossPhase(0.6, (("gamma", 2), ("barrels", 3), ("skulls", 2), ("ghouls", 2),
                            ("grate", 2), ("emp", 2), ("stomp", 3)), rest=0.85),
            BossPhase(0.25, (("gamma", 2), ("barrels", 3), ("skulls", 2), ("ghouls", 2),
                             ("grate", 2), ("emp", 2), ("stomp", 3)), rest=0.6),
        ),
        loot=2500, achievement="fallout_king", pages=("fallout_king", "glowing_ghoul"),
    ),
    # M24.2 (ai/bosses.SnowKing, design/BOSSES.md section 19): his crown all
    # fight; + black ice (the freeze); + flash freeze (a chill meter).
    "snow_king": BossSpec(
        name="Snow King, King of Loneliness",
        phases=(
            BossPhase(1.0, (("shards", 3), ("spikes", 2), ("breath", 2), ("icicles", 2),
                            ("penguins", 2)), rest=1.0),
            BossPhase(0.6, (("shards", 2), ("spikes", 2), ("breath", 2), ("icicles", 2),
                            ("penguins", 2), ("freeze", 3), ("blizzard", 2), ("snowballs", 2)),
                      rest=0.85),
            BossPhase(0.25, (("shards", 2), ("spikes", 2), ("breath", 2), ("icicles", 2),
                             ("penguins", 2), ("freeze", 3), ("blizzard", 2), ("snowballs", 2)),
                      rest=0.6),
        ),
        loot=2500, achievement="snow_king", pages=("snow_king", "frost_wraith"),
    ),
    # M24.3 (ai/bosses.Fragile, design/BOSSES.md section 20): the shutters all
    # fight; + shapeshifting (each form its own moves: FRAGILE_FORM_MOVES);
    # + on the beat. These lists are her own form's (the girl's).
    "fragile": BossSpec(
        name="Fragile, The Misunderstood",
        phases=(
            BossPhase(1.0, (("petals", 3), ("parasol", 2), ("slashes", 3), ("gaze", 2), ("mist", 2),
                            ("thralls", 1)), rest=1.0),
            BossPhase(0.6, (("petals", 2), ("parasol", 2), ("slashes", 2), ("gaze", 2), ("mist", 2),
                            ("thralls", 1), ("chandeliers", 2)), rest=0.85),
            BossPhase(0.25, (("petals", 2), ("parasol", 2), ("slashes", 2), ("gaze", 2), ("mist", 2),
                             ("thralls", 1), ("chandeliers", 2)), rest=0.6),
        ),
        loot=2500, achievement="fragile", pages=("fragile", "vampire_bat", "thrall"),
    ),
    # M25.1 (ai/bosses.Nettle, design/BOSSES.md section 23): her glamour
    # decoys come on a timer all fight (DECOY_EVERY); "dust" (her shrinking
    # dust) joins in phase 2; her blight seeds come on a timer in phase 3.
    "nettle": BossSpec(
        name="Nettle, the Blighted",
        phases=(
            BossPhase(1.0, (("spiral", 3), ("sparks", 2), ("thorns", 2), ("cage", 1),
                            ("moths", 1), ("dive", 2), ("wisps", 1), ("nettles", 2)), rest=1.0),
            BossPhase(0.6, (("spiral", 2), ("sparks", 2), ("thorns", 2), ("cage", 1),
                            ("moths", 1), ("dive", 2), ("wisps", 1), ("nettles", 2),
                            ("dust", 2)), rest=0.85),
            BossPhase(0.25, (("spiral", 2), ("sparks", 2), ("thorns", 2), ("cage", 1),
                             ("moths", 1), ("dive", 2), ("wisps", 1), ("nettles", 2),
                             ("dust", 2)), rest=0.6),
        ),
        loot=2500, achievement="nettle", pages=("nettle", "blighted_sprite", "rot_moth"),
    ),
}

# Khepri the Dung Emperor (ai/bosses.Khepri): a giant dung beetle with his
# ball. Damages are per hit at level 1 (x the enemy damage scaling).
# Signature, the DUNG BALL: it sits in front of him, and his "roll" sends it
# along a telegraphed line (aimed where you're going), him pushing behind.
# It grows as it rolls (DUNG_RADIUS[0] -> [1] tiles, DUNG_GROW per tile
# rolled), hitting harder the bigger it is (DUNG_DAMAGE, from smallest to
# biggest) and knocking you DUNG_PUSH tiles. If it runs into anything solid
# -- a sandstone pillar, the arena wall -- it SHATTERS: a ring of clods
# (DUNG_CLODS, more for a bigger ball) and he sits stunned for DUNG_STUN s
# (the melee window), then rolls up a new small one (DUNG_GATHER s).
KHEPRI_HIT_RADIUS = 2.6
DUNG_RADIUS = (1.3, 3.2)
DUNG_GROW = 0.045
DUNG_DAMAGE = (12, 24)
DUNG_PUSH = 4.0
DUNG_CLODS = (10, 22)
DUNG_STUN = 3.0
DUNG_GATHER = 0.9
KHEPRI_ROLL = (0.8, 15.0, 42.0)          # aim line (tell) s, rolling speed tiles/s, longest roll
KHEPRI_WALK = 7.0                        # tiles/s back to his ball
KHEPRI_CHARGE = (0.7, 24.0, 32.0, 14, 0.8)   # tell s, speed, longest, damage, dazed s if he
                                             # runs into a pillar
KHEPRI_SPRAY = (7, 70.0)                 # sand pellets kicked at you when he stops, fan degrees
KHEPRI_BURROW = (0.5, 1.6, 0.7, 3.5, 15, 16)  # dig in s, ripple chases you s, ripple stops (tell)
                                              # s, blast radius, blast damage, ring of sand
KHEPRI_STORM = (0.6, 3.5, 0.3, 3.2, 8.0, 22.0)  # wings (tell) s, seconds, s between rows, column
                                                # gap, hole width, half-width of the storm
KHEPRI_SWARM = (0.6, 4, 8)               # click (tell) s, scarabs per call, most alive at once
KHEPRI_FRENZY = 1.25                     # last phase: rolls this much faster, two in a row
KHEPRI_SHOTS = {
    "sand": ShellSpec(speed=13.0, damage=8, max_range=26.0, damages_terrain=False,
                      look="sand", sound="fizzle"),
    "dust": ShellSpec(speed=9.0, damage=8, max_range=40.0, damages_terrain=False,
                      look="dust", sound="fizzle"),
    "clod": ShellSpec(speed=9.0, damage=10, max_range=24.0, damages_terrain=False,
                      look="clod", sound="fizzle"),
}
# (2026-10-06: the Snow King and Fragile were taken down ~20% at the user's
# request -- their hits ~20% weaker, their openings more generous; the old
# numbers are in design/BOSSES.md sections 19 and 20.)
# Ol' Spitter, the Unmannered One (ai/bosses.OlSpitter, M23.2): a
# two-humped camel in his caravanserai. Damages are per hit at level 1 (x
# the enemy damage scaling).
# Signature, HUMPS AND THIRST: his humps hold HUMP_WATER sips of spit (half
# in each; they shrink as he spends it). Every spitting move costs
# HUMP_COST. Empty, he goes to the nearest unbroken trough and kneels to
# drink for DRINK[0] s, taking DRINK[1] x damage (the melee window), and
# gets up full. Smash the trough he's drinking from (TROUGH_HP a tile) and
# he CHOKES: stunned CHOKE_STUN s, with only what he'd drunk so far. With
# no trough left he's PARCHED, slower but angrier: no more drinking (and no
# more melee windows; his spit costs nothing), he walks and gallops x
# PARCHED[0] as fast and rests x PARCHED[1] as long between moves -- so
# smashing troughs early is a trade.
# His other signature move, the RICOCHET LOOGIE: a big gob that bounces
# off walls, arches and posts, splitting in two (LOOGIE_SPREAD degrees
# apart, x LOOGIE_SHRINK the size) at each of its first LOOGIE_SPLITS
# bounces and popping at the next; LOOGIE_DAMAGE per hit by generation.
SPITTER_HIT_RADIUS = 2.4
SPITTER_TURN = 1.6                       # rad/s he turns to face his target (slowly: a camel)
SPITTER_SPIT_ARC = 70.0                  # degrees either side of his nose he can spit
HUMP_WATER = 10
HUMP_COST = {"fan": 2, "mortar": 2, "loogie": 3, "spiral": 3}
DRINK = (4.0, 1.5, 14.0, 8.0)            # s drinking, damage taken x, walk speed, longest walk s
CHOKE_STUN = 3.0
PARCHED = (0.85, 0.75)
SPITTER_FAN = (0.6, 5, 50.0, 3, 0.45)    # rear (tell) s, globs, fan degrees, volleys, s between
SPITTER_MORTAR = (0.5, 3, 0.45, 6)       # tell s, loogies, s between, ring of spit each
                                         # (from the edge of its blast, flying out)
LOOGIE_TELL = 0.8
LOOGIE_SPEED = 14.0
LOOGIE_RADIUS = 1.2
LOOGIE_SHRINK = 0.75
LOOGIE_SPLITS = 3
LOOGIE_SPREAD = 28.0
LOOGIE_LIFE = 7.0
LOOGIE_DAMAGE = (14, 11, 9, 7)
SPITTER_GALLOP = (0.7, 22.0, 36.0, 14, 0.8)  # tell s, speed, longest, damage, dazed s if he
                                             # runs into something
SPITTER_TRAIL = (1.6, 3.0, 0.5, 5, 2.0)  # churned sand: radius, lasts s, s between stings,
                                         # damage a sting, tiles between patches
SPITTER_KICK = (0.5, 6.0, 55.0, 0.45, 16, 6.0)  # s someone stands behind him first, reach,
                                                # half-angle of the cone (deg), tell s,
                                                # damage, knockback tiles
SPITTER_STAMPEDE = (0.9, 3, 1.1, 18.0, 26.0, 3.2, 7.0, 10, 1.1, 26.0)
    # bellow (tell) s, rows, s between rows, ghost speed, row half-width, spacing,
    # gap width, damage, ghost hit radius, how far back the rows start
SPITTER_MIRAGE = (0.7, 2, 2)             # shimmer (tell) s, decoys per cast, most alive
SPITTER_SPIRAL = (0.7, 3.0, 0.12, 2.4, 3)    # rear-up (tell) s, seconds, s between, turn
                                             # rad/s, arms
CAMEL_SPIT = ShellSpec(speed=11.0, damage=7, max_range=20.0, damages_terrain=False,
                       look="spit", sound="fizzle")
CAMEL_FAN = (3, 30.0)                    # a mangy camel's spit: globs, fan degrees
CAMEL_LEASH = 9.0                        # tiles a mangy camel strays from its bundle
SPITTER_SHOTS = {
    "spit": ShellSpec(speed=12.0, damage=8, max_range=28.0, damages_terrain=False,
                      look="spit", sound="fizzle"),
    "lob": ShellSpec(speed=16.0, damage=12, max_range=34.0, damages_terrain=False,
                     look="lob_spit", sound="fizzle", lob=True, blast_radius=2.4),
    "splash": ShellSpec(speed=9.0, damage=7, max_range=14.0, damages_terrain=False,
                        look="spit", sound="fizzle"),
}
# The Nameless Magus, Holder of Time (ai/bosses.Magus, M23.3): a robed
# sand wizard in his sunken observatory. Damages are per hit at level 1 (x
# the enemy damage scaling).
# Signature 1, SAND RUNES (phase 1+): he draws RUNE_BATCH[phase] rune
# circles (RUNE_RADIUS tiles) RUNE_RANGE tiles from his target, at least
# RUNE_GAP apart. Each charges RUNE_CHARGE s, then fires: a firestorm (a
# RUNE_FIRE blast and a ring of sand), a blade ring, or a sand golem (at
# most RUNE_GOLEMS alive; else a firestorm). A hero inside one for
# RUNE_SCUFF s (or rolling through it) scuffs it out. Scuff a whole batch
# and he's DRAINED: kneeling RUNE_DRAIN s (the melee window).
# Signature 2, SHIFTING DUNES (phase 2+): DUNE_WALLS walls of sand rise
# near the target (DUNE_LEN tiles long, 2 thick, DUNE_HP a tile: shoot
# through them), blocking shots both ways, with DUNE_PITS quicksand pits;
# DUNE_LIFE s later (or at his next dunes) they collapse, each throwing
# sand outward. Quicksand: slows to QUICKSAND[1] x and drags toward the
# middle at QUICKSAND[2] tiles/s.
# Signature 3, THE HOURGLASS (phase 3): he plants it HOURGLASS[1] tiles from
# the target; its sand runs HOURGLASS[0] s. Meanwhile TIME_ZONES time zones
# (radius TIME_ZONE_RADIUS) open round it: slow ones (everything inside but
# him at TIME_SLOW x: heroes walk, shots fly, adds act) and fast ones
# (shots and adds TIME_FAST x, heroes walk TIME_FAST_HERO x). Shatter the
# glass (its HP: config.ENEMIES["hourglass"]) and he's stunned
# HOURGLASS[2] s. If the sand runs out: TIME'S UP -- HOURGLASS[3] rings of
# shots from the glass, each with a gap, and every rune on the field fires.
MAGUS_HIT_RADIUS = 1.6
RUNE_BATCH = (2, 3, 4)
RUNE_RADIUS = 2.5
RUNE_RANGE = (8.0, 18.0)
RUNE_GAP = 9.0
RUNE_CHARGE = 4.0
RUNE_SCUFF = 0.4
RUNE_DRAIN = 4.0
RUNE_DRAW = 0.7                          # s he spends drawing a batch (the tell)
RUNE_FIRE = (3.5, 16, 12)                # firestorm: blast radius, damage, ring of sand
RUNE_BLADES = (14, 2, 0.35)              # blade ring: blades a ring, rings, s between
RUNE_GOLEMS = 2
DUNE_WALLS = (3, 5)
DUNE_LEN = (8, 14)
DUNE_HP = 60
DUNE_PITS = 2
DUNE_LIFE = 12.0
DUNE_TELL = 0.9
DUNE_RANGE = (5.0, 16.0)                 # tiles from the target a wall's middle goes
QUICKSAND = (3.5, 0.5, 1.0)              # radius, walking speed x, drag tiles/s
HOURGLASS = (12.0, 13.0, 4.0, 3)         # sand runs s, tiles from the target, stun s, rings
TIME_ZONES = (2, 3)
TIME_ZONE_RADIUS = 6.0
TIME_SLOW = 0.5
TIME_FAST = 2.0
TIME_FAST_HERO = 1.5
TIMES_UP_RING = (28, 50.0, 0.6)          # shots a ring, gap degrees, s between rings
MAGUS_LANCE = (0.8, 1.5, 40.0, 40.0, 15, 0.7)   # aim line (tell) s, beam s, sweep degrees,
                                                # longest, damage, beam half-width tiles
MAGUS_SIGILS = (0.6, 4, 6, 7, 70.0)      # tell s, sigils a cast, most alive, blades, fan deg
MAGUS_BLINK = (0.6, 14.0, 26.0, 8)       # shimmer (tell) s, nearest / farthest hop, puff shots
MAGUS_VORTEX = (0.7, 4.0, 12.0, 2.5, 0.15, 2.2)  # tell s, lasts s, pull radius, pull
                                                 # tiles/s, s between spiral shots, turn rad/s
MAGUS_SERPENT = (0.9, 30.0, 1.4, 16, 44.0)       # tell s, speed, half-width, damage, length
SIGIL_LIFE = 8.0
MAGUS_SHOTS = {
    "sand": ShellSpec(speed=12.0, damage=8, max_range=26.0, damages_terrain=False,
                      look="sand", sound="fizzle"),
    "blade": ShellSpec(speed=13.0, damage=9, max_range=24.0, damages_terrain=False,
                       look="blade", sound="fizzle"),
    "time": ShellSpec(speed=9.0, damage=10, max_range=40.0, damages_terrain=False,
                      look="time", sound="fizzle"),
}
ELEMENTAL_BOLT = ShellSpec(speed=12.0, damage=7, max_range=20.0, damages_terrain=False,
                           look="sand", sound="fizzle")
ELEMENTAL_BLINK = (0.25, 4.0, 7.0)       # vanish s, shortest / longest hop
# The Fallout King (ai/bosses.FalloutKing, M24.1): a hulking irradiated
# monster in his reactor vault. Damages are per hit at level 1 (x the enemy
# damage scaling).
# Signature 1, RADS (all fight): each hero's meter (Character.rads, 0..
# RADS_FULL). It fills RADS_GLOW a second within RADS_GLOW_RANGE tiles of
# him, RADS_HIT per hit of his, RADS_GOO a second in toxic goo and
# RADS_FALLOUT in fallout, and drains RADS_DRAIN a second on its own. Full:
# IRRADIATED for IRRADIATED[0] s -- IRRADIATED[1] damage every IRRADIATED[2]
# s, no regen, the roll recharging x IRRADIATED[3] -- then back to
# IRRADIATED[4]. A decontamination shower (the lair's) wipes it after
# SHOWER[0] s under it, then is off for SHOWER[1] s.
# Signature 2, FALLOUT (phase 2+): his stomp throws FALLOUT_PATCHES[0..1]
# patches round the target, each growing FALLOUT_RADIUS[0] -> [1] tiles over
# FALLOUT_GROW s, burning FALLOUT_BURN a second (and rads), with an isotope
# rod in the middle (config.ENEMIES): smash it and the patch clears. At most
# FALLOUT_MOST (the oldest fades).
# Signature 3, the MELTDOWN CORE (phase 3): heat climbs 100 over CORE_HEAT s.
# Shut all 4 coolant valves (VALVE_TIME s at one) and his chest blows open:
# CORE_EXPOSED[1] x damage for CORE_EXPOSED[0] s, heat back to 0. At 100:
# MELTDOWN after a MELTDOWN[0] s countdown -- MELTDOWN[1] damage and
# MELTDOWN[2] rads to every hero in the arena not behind a lead wall.
KING_HIT_RADIUS = 2.4
RADS_FULL = 100.0
RADS_GLOW = 8.0
RADS_GLOW_RANGE = 7.0
RADS_HIT = 10.0
RADS_GOO = 15.0
RADS_FALLOUT = 12.0
RADS_DRAIN = 2.0
IRRADIATED = (6.0, 4, 0.5, 0.5, 50.0)
SHOWER = (1.5, 20.0, 1.6)                # s under it, s offline, reach (tiles)
FALLOUT_PATCHES = (2, 3)
FALLOUT_RADIUS = (2.0, 3.5)              # (radius, tiles: the draft's "4 -> 7 across")
FALLOUT_GROW = 10.0
FALLOUT_BURN = 3.0
FALLOUT_MOST = 6
FALLOUT_STOMP = (0.8, 6.0, 14.0, 3.0, 12)   # tell s, nearest / farthest from target, stomp
                                            # blast radius, damage
CORE_HEAT = 35.0
CORE_EXPOSED = (5.0, 3.0)
VALVE_TIME = 2.0
VALVE_REACH = 2.6
MELTDOWN = (3.0, 60, 50.0)
MELTDOWN_SPEED = 70.0                    # tiles/s the meltdown's wave races out (it hits
                                         # you when it gets to you)
KING_GAMMA = (0.8, 3.0, 0.6, 30.0, 7, 0.3, 0.7)  # aim (tell) s, burn s, turn rad/s,
                                                  # longest, damage a tick, s a tick,
                                                  # half-width
KING_BARRELS = (0.6, 3, 0.4, 1.2, 3.0, 8.0, 0.6)  # tell s, barrels, s between, flight s,
                                                  # goo radius, goo lasts s, slow x
KING_GHOULS = (0.7, 3, 5)                # roar (tell) s, ghouls a call, most alive
KING_EMP = (0.8, 40, 40.0, 2)            # charge (tell) s, shots a ring, gap degrees, rings
KING_SKULLS = (0.6, 4, 6)                # tell s, skulls a volley, most alive
KING_GRATE = (0.5, 1.0, 3.0, 14, 12)     # sink s, rattle (tell) s, burst radius, damage, ring
GHOUL_BURST = (1.5, 6)                   # a ghoul's death: radius, damage
KING_SHOTS = {
    "glow": ShellSpec(speed=12.0, damage=10, max_range=28.0, damages_terrain=False,
                      look="glow", sound="fizzle"),
    "emp": ShellSpec(speed=14.0, damage=11, max_range=36.0, damages_terrain=False,
                     look="emp", sound="fizzle"),
}
# The Snow King, King of Loneliness (ai/bosses.SnowKing, M24.2): a lonely
# frost wizard-king in his throne hall. Damages are per hit at level 1 (x
# the enemy damage scaling).
# Signature 1, THE CROWN (all fight): deal CROWN_KNOCK[0] x his max HP within
# CROWN_KNOCK[1] s and it flies off, skidding CROWN_FLY tiles/s (slowing at
# CROWN_FRICTION /s) away from you. CROWNLESS he can't attack, waddles
# after it at CROWN_CHASE tiles/s and takes CROWN_VULN x damage. A hero
# touching it kicks it on (CROWN_KICK tiles/s, each hero every
# CROWN_KICK_EVERY s). Back on his head (CROWN_DON s), an angry ring of
# CROWN_RAGE shards, and CROWN_COOLDOWN s before it can be knocked again.
# Signature 2, BLACK ICE (phase 2+): his freeze lays ICE_SHEETS sheets near
# the target, growing ICE_RADIUS[0] -> [1] tiles over ICE_GROW s, lasting
# ICE_LIFE s. On ice a hero's speeding up and stopping are x ICE_TRACTION,
# top speed x ICE_TOP (a roll is unaffected). A fire brazier (the lair's)
# lit by standing at it BRAZIER_KINDLE s burns FIRE_BURN s and melts every
# sheet whose middle is within FIRE_MELT tiles.
# Signature 3, FLASH FREEZE (phase 3): each hero's chill (Character.chill,
# 0..CHILL_FULL) fills CHILL_HIT per frost hit and CHILL_STILL a second
# standing still; drains CHILL_MOVING a second moving, CHILL_FIRE near a lit
# brazier. Full: ENCASED in ice up to ENCASE[0] s (can't move or attack;
# ENCASE[1] rolls break out; a partner's shots break it, ENCASE[2] HP), and
# his hits on you do ENCASE[3] x damage.
SNOW_HIT_RADIUS = 2.2
# M24.5: between moves he glides round the hall (ai/bosses.SnowKing._glide):
# SNOW_GLIDE = (tiles/s, nearest, farthest tiles from his target, (s, s)
# between turning about, how fast his heading turns (rad/s), x speed on his
# own black ice). SNOW_TRAIL = (tiles between frost marks, s they last).
SNOW_GLIDE = (4.5, 7.0, 12.0, (4.0, 8.0), 1.6, 1.5)
SNOW_TRAIL = (0.7, 1.4)
# He glides during his moves too, SNOW_IN_MOVE x as fast; during his frost
# breath he walks at you instead: SNOW_ADVANCE = (tiles/s, no closer than).
SNOW_IN_MOVE = 0.5
SNOW_ADVANCE = (1.5, 5.0)
CROWN_KNOCK = (0.05, 4.0)
CROWN_FLY = 22.0
CROWN_FRICTION = 18.0
CROWN_CHASE = 6.0
CROWN_VULN = 1.6
CROWN_KICK = 16.0
CROWN_KICK_EVERY = 2.0
CROWN_DON = 0.8
CROWN_RAGE = 16
CROWN_COOLDOWN = 12.0
ICE_SHEETS = (2, 3)
ICE_RADIUS = (4.0, 8.0)
ICE_GROW = 3.0
ICE_LIFE = 30.0
ICE_TELL = 1.0
ICE_TRACTION = 0.2
ICE_TOP = 1.15
BRAZIER_KINDLE = 2.0
FIRE_BURN = 20.0
FIRE_MELT = 9.0
FIRE_REACH = 2.5                         # tiles from a brazier you stand to light it
CHILL_FULL = 100.0
CHILL_HIT = 10.0
CHILL_STILL = 5.0
CHILL_MOVING = 4.0
CHILL_FIRE = 25.0
ENCASE = (3.5, 3, 50, 1.4)
SNOW_SHARDS = (0.6, 6, 60.0, 3, 0.4)     # raise (tell) s, shards, fan degrees, volleys, s between
SNOW_SPIKES = (0.5, 22, 8.0, 0.8, 45.0)  # tell s, spikes, ring radius, hold s, gap degrees
SNOW_PENGUINS = (0.8, 9, 3.2, 8.0, 14.0, 50.0, 8, 1.0)  # whistle s, penguins a row, spacing,
                                         # gap, speed, slide (tiles; x2 on ice), damage, radius
SNOW_BREATH = (0.8, 1.6, 50.0, 40.0, 15.0, 0.25, 3, 5.0, 0.7)  # wedge (tell) s, breath s,
                                         # cone degrees, sweep degrees, reach, s a tick,
                                         # damage a tick, chill a tick, walking speed x
SNOW_ICICLES = (1.0, 5, 1.6, 11, 4)      # shadows (tell) s, icicles, radius, damage, shards each
SNOW_BLIZZARD = (0.7, 4.0, 3.0, 0.4, 3.4, 8.0, 22.0)  # tell s, lasts s, wind tiles/s, s between
                                         # rows, row gap, hole, half-width
SNOW_SNOWBALLS = (0.6, 2, 10.0, (1.0, 2.5), (8, 14), 6.0, 1.5)  # tell s, snowballs, speed,
                                         # radius small..big, damage small..big, life s,
                                         # speed x on ice
SNOW_SHOTS = {
    "shard": ShellSpec(speed=13.0, damage=5, max_range=26.0, damages_terrain=False,
                       look="shard", sound="fizzle"),
    "spike": ShellSpec(speed=12.0, damage=7, max_range=18.0, damages_terrain=False,
                       look="spike", sound="fizzle"),
    "snow": ShellSpec(speed=9.0, damage=6, max_range=40.0, damages_terrain=False,
                      look="snow", sound="fizzle"),
}
# Fragile, The Misunderstood (ai/bosses.Fragile, M24.3): a vampire with a
# black lace parasol in her ruined ballroom (it was a bass-axe until M24.4). Damages are per hit at level 1 (x the
# enemy damage scaling).
# Signature 1, SUNLIGHT (all fight): a hero at a window's lever
# LEVER_TIME s opens its shutter for SHAFT_OPEN s: a shaft of sun
# SHAFT_WIDTH tiles wide, SHAFT_LEN long, slanting SHAFT_SLANT rad off
# straight in. In it she takes SUN_VULN x damage; a shaft opening on her or
# her running into one stuns her SUN_STUN s (once per opening). She keeps
# out of the light, and every SLAM_EVERY s slams the nearest open shutter
# (SLAM_TELL s). Heroes in the light are safe from her gaze.
# Signature 2, SHAPESHIFT (phase 2+): every FORM_TIME s (FORM_TELL s tell)
# she becomes another of FRAGILE_FORMS; the bat takes BAT_ARMOR x damage
# (not from the bard's pulse), and each form has its own moves.
# Signature 3, ON THE BEAT (phase 3): a metronome at BEAT_BPM (start ..
# at 0 HP); her tells end on beats; a hero who starts a roll within
# BEAT_PERFECT s of a beat stuns her PERFECT_STUN s (at most every
# PERFECT_EVERY s).
FRAGILE_HIT_RADIUS = 1.6
LEVER_TIME = 1.2
LEVER_REACH = 2.2
SHAFT_OPEN = 18.0
SHAFT_WIDTH = 5.0
SHAFT_LEN = 60.0
SHAFT_SLANT = 0.35
SUN_VULN = 3.0
SUN_STUN = 3.0
SLAM_EVERY = 25.0
SLAM_TELL = 1.0
FRAGILE_FORMS = ("girl", "bat", "wolf")
FRAGILE_FORM_MOVES = {
    "bat": (("curtain", 3), ("swoop", 3), ("mist", 1)),
    "wolf": (("charge", 3), ("howl", 2), ("claws", 3)),
}
FORM_TIME = 15.0
FORM_TELL = 1.0
BAT_ARMOR = 0.6
FORM_SPEED = {"girl": 6.0, "bat": 10.0, "wolf": 8.0}   # tiles/s she drifts between moves
BEAT_BPM = (100.0, 140.0)
BEAT_PERFECT = 0.15
PERFECT_STUN = 1.2
PERFECT_EVERY = 4.0
# M24.5: between moves she circles you (ai/bosses.Fragile._drift):
# FRAGILE_CIRCLE = (nearest, farthest tiles, (s, s) between turning about,
# x FORM_SPEED).
FRAGILE_CIRCLE = (8.0, 12.0, (4.0, 7.0), 0.8)
# ...and during her moves too, FRAGILE_IN_MOVE x as fast -- except these,
# which need her in place (and her dashes, which move her anyway).
FRAGILE_IN_MOVE = 0.5
FRAGILE_PLANTED = ("gaze", "mist", "swoop", "charge")
FRAGILE_PETALS = (0.6, 22, 50.0, 3, 0.5)  # twirl (tell) s, petals a ring, gap degrees, rings, s between
FRAGILE_PARASOL = (0.7, 18.0, 22.0, 11, 1.4)  # wind-up (tell) s, speed, reach, damage, hit radius
FRAGILE_SLASHES = (0.5, 5, 40.0, 3, 0.35)  # tell s, slashes a fan, degrees, volleys, s between
FRAGILE_GAZE = (0.8, 2.5, 40.0, 16.0, 2.4)  # wedge (tell) s, gaze s, cone degrees, reach, pull
                                            # tiles/s
FRAGILE_MIST = (0.6, 10.0, 22.0, 4.0, 0.6, 2.0)  # shimmer (tell) s, nearest / farthest hop, mist
                                                 # lasts s, walking speed x, mist radius
FRAGILE_THRALLS = (0.8, 2, 3)            # creak (tell) s, thralls a call, most alive
STAKE_TIME = 2.0
FRAGILE_CHANDELIER = (1.0, 2.5, 14)      # shadow (tell) s, crash radius, damage
FRAGILE_CURTAIN = (0.7, 3.5, 0.35, 3.2, 7.0, 22.0)  # bats: tell s, lasts s, s between rows, gap,
                                                    # hole, half-width
FRAGILE_SWOOP = (0.6, 26.0, 30.0, 10, 1.0)  # line (tell) s, speed, longest, damage, width
FRAGILE_CHARGE = (0.7, 26.0, 32.0, 13)   # line (tell) s, speed, longest, damage
FRAGILE_HOWL = (0.8, 8.0, 5.0, 12)       # tell s, push radius, push tiles, ring of shots
FRAGILE_CLAWS = (0.4, 5, 70.0, 2, 0.3)   # tell s, slashes, fan degrees, volleys, s between
FRAGILE_SHOTS = {
    "petal": ShellSpec(speed=11.0, damage=7, max_range=30.0, damages_terrain=False,
                       look="petal", sound="fizzle"),
    "slash": ShellSpec(speed=15.0, damage=8, max_range=24.0, damages_terrain=False,
                       look="slash", sound="fizzle"),
    "bat": ShellSpec(speed=10.0, damage=6, max_range=40.0, damages_terrain=False,
                     look="bat", sound="fizzle"),
}
# Nettle, the Blighted (ai/bosses.Nettle, M25.1): a corrupted pixie in her
# withered glade. She flies (over toadstools and stumps, never out of the
# glade), circling her target NETTLE_ORBIT = (nearest, farthest tiles, (s, s)
# between turning about, tiles/s, x that speed during her moves). Damages
# are per hit at level 1 (x the enemy damage scaling).
# Signature 1, GLAMOUR (all fight): every DECOY_EVERY s (a DECOY_TELL s
# shimmer) she splits into DECOYS[phase] copies besides herself, DECOY_SPREAD
# tiles about -- and she may come out of the shimmer as any of them. Copies
# fly and cast her spirals and sparks too (with DECOY_SHARE of the shots).
# Only she casts a shadow. A hit pops a copy into a ring of DECOY_POP dust
# shots; one not popped fades after DECOY_LIFE s.
# Signature 2, SHRINKING DUST (phase 2+): her "dust" move throws dust clouds
# (NETTLE_DUST); in phase 2+ her dives trail them too. DUST_SHRINK s in a
# cloud shrinks you (Character.shrunk): SHRINK = (s it lasts, your speed x,
# your damage x, tiles her hits knock you). Standing GROWCAP_TIME s within
# GROWCAP_REACH of a growcap grows you back; it regrows GROWCAP_REGROW s on.
# Signature 3, BLIGHT (phase 3): every BLIGHT_EVERY s she plants
# BLIGHT_SEEDS rot seeds (BLIGHT_TELL s falling; at most BLIGHT_MAX); each
# patch grows to BLIGHT_RADIUS over BLIGHT_GROW s. On one you take
# BLIGHT_DAMAGE every BLIGHT_TICK s; while she's over one she heals
# BLIGHT_HEAL HP a second -- and between her moves she flies back to the
# nearest patch to drink. BLIGHT_PULL s within BLIGHT_REACH of a seed pulls
# it (its patch goes with it).
NETTLE_HIT_RADIUS = 1.9
NETTLE_ORBIT = (9.0, 13.0, (4.0, 7.0), 4.5, 0.5)
DECOY_EVERY = 18.0
DECOY_TELL = 1.0
DECOYS = (2, 3, 4)
DECOY_SPREAD = 7.0
DECOY_SHARE = 0.5
DECOY_POP = 8
DECOY_LIFE = 14.0
NETTLE_DUST = (0.7, 3, 2.5, 6.0)          # tell s, clouds, radius, lasts s
DUST_SHRINK = 0.8
SHRINK = (15.0, 1.35, 0.6, 1.5)
GROWCAP_REACH = 1.8
GROWCAP_TIME = 0.4
GROWCAP_REGROW = 20.0
BLIGHT_EVERY = 16.0
BLIGHT_SEEDS = 2
BLIGHT_TELL = 1.0
BLIGHT_MAX = 5
BLIGHT_RADIUS = 6.0
BLIGHT_GROW = 10.0
BLIGHT_DAMAGE = 3
BLIGHT_TICK = 0.5
BLIGHT_HEAL = 30.0
BLIGHT_REACH = 1.8
BLIGHT_PULL = 1.5
# Her moves.
NETTLE_SPIRAL = (0.6, 2, 2.4, 0.1, 2.4)  # tell s, arms, lasts s, s between, turn rad/s
NETTLE_SPARKS = (0.6, 5, 7.0, 2.0, 5.0, 8, 50.0)  # tell s, sparks, speed, turn rad/s, life s,
                                         # damage, fan degrees
NETTLE_THORNS = (0.8, 3, 20.0, 1.6, 0.05, 1.3, 10, 22.0)  # cracks (tell) s, lines, length,
                                         # spacing, s between bursts, hit radius, damage,
                                         # degrees between lines
NETTLE_CAGE = (0.7, 22, 8.0, 0.7, 50.0)  # tell s, thorns, ring radius, hold s, gap degrees
NETTLE_MOTHS = (0.8, 4, 8)               # tell s, moths a call, most alive
NETTLE_DIVE = (0.5, 3, 24.0, 30.0, 9, 1.2, 4.0)  # line (tell) s, dives, speed, longest,
                                         # damage, width, tiles between trail clouds
NETTLE_WISPS = (1.2, 5, 6.0, 1.8, 7.0, 8, 12.0)  # gathering (tell) s, wisps, speed, turn
                                         # rad/s, life s, damage, from how far they drift in
NETTLE_NETTLES = (1.0, 9, 1.6, 11, 6.0)  # shadows (tell) s, nettles, radius, damage, spread
NETTLE_SHOTS = {
    "glitter": ShellSpec(speed=10.0, damage=6, max_range=30.0, damages_terrain=False,
                         look="glitter", sound="fizzle"),
    "pop": ShellSpec(speed=8.0, damage=5, max_range=10.0, damages_terrain=False,
                     look="glitter", sound="fizzle"),
    "thorn": ShellSpec(speed=12.0, damage=7, max_range=18.0, damages_terrain=False,
                       look="thorn", sound="fizzle"),
}
# The golden scarab (ai/creatures.GoldenScarab): spooked within
# GOLDEN_SCARAB[0] tiles, it flees; after GOLDEN_SCARAB[1] s of running it
# digs in (GOLDEN_SCARAB[2] s, still hittable: the last chance), and comes
# up again at its home spot GOLDEN_SCARAB[3] s later.
GOLDEN_SCARAB = (11.0, 4.5, 0.9, 10.0)

# Lady Proboscia (ai/bosses.Proboscia): a giant mosquito. She flies over
# everything, hovering PROBOSCIA_HOVER[1] tiles from her target between
# moves. Damages are per hit at level 1 (x the enemy damage scaling).
# Signature, ENGORGE: each bite that lands and each sip at a pool puts one
# gulp of blood in her belly (a bite also heals her PROBOSCIA_DRINK x the
# damage). ENGORGE_FULL gulps and she's engorged for ENGORGE_WINDOW s:
# slower (x ENGORGE_SLOW) and glowing. Deal ENGORGE_POP x her max HP in that
# time and she POPS: ENGORGE_BONUS x max HP more damage, a ring of
# ENGORGE_RING blood drops, and she's down for ENGORGE_STUN s (the melee
# window). Fail and she digests it: heals ENGORGE_DIGEST x max HP.
PROBOSCIA_HIT_RADIUS = 3.0     # (was 1.9 before the 2026-10-05 size-up; render LADY_SCALE)
PROBOSCIA_HOVER = (9.0, 13.0, 0.6)      # speed tiles/s, distance from the target, orbit rad/s
PROBOSCIA_BITE = (0.65, 34.0, 30.0, 1.8, 12, 0.6)  # tell s, dash speed, longest dash, width,
                                                   # damage, hovering still after (s)
PROBOSCIA_DRINK = 3.0
PROBOSCIA_FAN = (0.5, 5, 40.0, 3, 0.5)  # tell s, needles per volley, fan degrees, volleys, gap s
PROBOSCIA_BUZZ = (0.4, 26, 10.0, 0.8, 55.0, 2, 1.0)  # whine (tell) s, shots, radius, ring
                                                     # hold s, gap degrees, rings, s between
PROBOSCIA_CALL = (0.7, 4, 8)             # tell s, mosquitoes per call, most alive at once
PROBOSCIA_SIP = (2.4, 0.03, 14.0)       # seconds drinking, damage (x max HP) that shoos her
                                        # off it, flying speed to the pool
PROBOSCIA_FRENZY = (1.3, 3, 0.4)        # last phase: speed x, dives chained, tell s between
# Last phase: her dives leave fever clouds, one every FEVER_CLOUD[4] tiles
# of the dive: radius, seconds, tick s, damage per tick, spacing.
FEVER_CLOUD = (1.8, 4.0, 0.5, 4, 3.0)
ENGORGE_FULL = 3
ENGORGE_WINDOW = 6.0
ENGORGE_SLOW = 0.55
ENGORGE_POP = 0.035
ENGORGE_BONUS = 0.08
ENGORGE_RING = 20
ENGORGE_STUN = 2.5
ENGORGE_DIGEST = 0.04
PROBOSCIA_SHOTS = {
    "needle": ShellSpec(speed=15.0, damage=8, max_range=32.0, damages_terrain=False,
                        look="needle", sound="bow"),
    "buzz": ShellSpec(speed=7.0, damage=9, max_range=22.0, damages_terrain=False,
                      look="buzz", sound="orb"),
    "pop": ShellSpec(speed=8.0, damage=9, max_range=24.0, damages_terrain=False,
                     look="blood", sound="fizzle"),
}

# The Leech Swarm (ai/bosses.LeechSwarm). LEECHES bodies share the health
# (each holds its share; area hits are strong against it, by design), and
# drift as a flock toward the target between moves. A leech that touches a
# hero (who isn't rolling) latches on: it rides along, draining LATCH_DPS
# (x enemy damage scaling) and healing itself by LATCH_HEAL x what it drains,
# until a dodge roll throws every leech off that hero (stunned for
# LATCH_SHAKE[1] s, flung LATCH_SHAKE[0] tiles). At most LATCH_MAX per hero.
LEECHES = 120                   # (40 before 2026-10-05; they crawl over each other)
LEECH_RADIUS = 0.45             # tiles: a leech's body (hits, latching)
LEECH_FLOCK = (5.5, 0.6, 4.5)   # drift speed tiles/s, wander round its goal, spread round the centre
LATCH_DPS = 2.5
LATCH_HEAL = 2.0
LATCH_MAX = 8
LATCH_TICK = 0.5                # drain is dealt this often (one number, not a stream)
LATCH_SHAKE = (2.5, 1.0)
LEECH_SURGE = (0.8, 22.0, 0.6, 34.0)     # tell s, dash speed, dash s, line length
LEECH_SPLIT = (3, 10.0, 2.0, 1.0)        # groups, circle radius, circling s, closing s
LEECH_SPIT = (0.5, 3, 16, 0.35)          # tell s, rings, drops per ring, s between rings
LEECH_NEST = (0.8, 1.2, 18)              # swim to the pool s, ripples (tell) s, drops on surfacing
LEECH_WHIRL = (11.0, 2.0, 3.0, 50.0)     # ring radius, radius it closes to, seconds, gap degrees
LEECH_FRENZY = 1.4              # last phase: everything this much faster
LEECH_BROOD = 3                 # leechlings out of a popped bloated leech
LEECH_SHOTS = {
    "blood": ShellSpec(speed=8.0, damage=8, max_range=24.0, damages_terrain=False,
                       look="blood", sound="fizzle"),
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
