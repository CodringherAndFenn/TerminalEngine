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

from .specs import (BossPhase, BossSpec, CardSpec, CharacterSpec, EnemySpec, GearSpec, PactSpec,
                    QuestSpec,
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
    # P8: the haunted forest. The ghost woodcutter's axe comes back to him;
    # the apprentice's cursed orb splits in four when it hits anything
    # (systems/combat._shot_ends); the giant spider's web blob leaves a
    # sticky patch.
    "ghost_axe": WeaponSpec(
        name="ghost axe", fire_interval=2.6,
        shell=ShellSpec(speed=13.0, damage=11, max_range=10.0, damages_terrain=False,
                        look="ghost_axe", sound="axe", returns=True),
    ),
    "curse": WeaponSpec(
        name="cursed orb", fire_interval=3.2,
        shell=ShellSpec(speed=6.5, damage=10, max_range=16.0, damages_terrain=False,
                        look="curse_orb", sound="hex"),
    ),
    "web_spit": WeaponSpec(
        name="web", fire_interval=2.6,
        shell=ShellSpec(speed=11.0, damage=4, max_range=13.0, damages_terrain=False,
                        look="web", sound="orb"),
    ),
    # P9: the desert. The glass mage's shards glance off walls twice; the
    # cactus golem's spines (it fires them itself, ai/desert.py).
    "glass_shards": WeaponSpec(
        name="glass shards", fire_interval=2.4, pellets=3, spread_deg=28.0,
        shell=ShellSpec(speed=16.0, damage=6, max_range=20.0, damages_terrain=False,
                        look="glass", sound="spark", bounces=2),
    ),
    "cactus_spines": WeaponSpec(
        name="spines", fire_interval=1.0,
        shell=ShellSpec(speed=12.0, damage=4, max_range=7.0, damages_terrain=False,
                        look="spine", sound="bow"),
    ),
    # M28.4c: the mimic's coins, spat in a fan.
    # M28.5c: the Acorn Bandolier's acorns (lobbed; burst where they land).
    "acorn_lob": WeaponSpec(
        name="acorns", fire_interval=1.0,
        shell=ShellSpec(speed=12.0, damage=8, max_range=9.0, damages_terrain=False,
                        look="acorn", sound="fizzle", lob=True, blast_radius=1.5),
    ),
    # M28.5b: the Spittoon's glob (a hero's relic; ricochets off walls).
    "dancing_cutlery": WeaponSpec(     # (M30.5: the Dancing Shoes' spin)
        name="cutlery", fire_interval=1.0,
        shell=ShellSpec(speed=12.0, damage=10, max_range=9.0, damages_terrain=False,
                        look="cutlery", sound="axe"),
    ),
    "spittoon_glob": WeaponSpec(
        name="glob", fire_interval=4.0,
        shell=ShellSpec(speed=13.0, damage=20, max_range=26.0, damages_terrain=False,
                        look="spit", sound="fizzle", bounces=3),
    ),
    "mimic_coins": WeaponSpec(
        name="coins", fire_interval=1.0,
        shell=ShellSpec(speed=11.0, damage=9, max_range=9.0, damages_terrain=False,
                        look="coin", sound="spark"),
    ),
    # P10: the ruins. The clockwork sentry's bolts (a sweep of five), the
    # crossbow sniper's bolt (through everything in its line).
    "clock_bolts": WeaponSpec(
        name="clockwork bolts", fire_interval=3.5,
        shell=ShellSpec(speed=20.0, damage=6, max_range=18.0, damages_terrain=False,
                        look="clock_bolt", sound="bolt"),
    ),
    "heavy_bolt": WeaponSpec(
        name="heavy bolt", fire_interval=4.0,
        shell=ShellSpec(speed=42.0, damage=20, max_range=26.0, damages_terrain=False,
                        look="heavy_bolt", sound="bow", pierce=99),
    ),
    # P11: the swamp. The lizardman's javelin (sticks in the ground where
    # it stops, systems/combat._shot_ends).
    "javelin": WeaponSpec(
        name="javelin", fire_interval=2.8,
        shell=ShellSpec(speed=17.0, damage=9, max_range=14.0, damages_terrain=False,
                        look="javelin", sound="bow"),
    ),
    # P12: the mushroom biome. The cordyceps hunter's spore dart.
    "spore_dart": WeaponSpec(
        name="spore dart", fire_interval=2.2,
        shell=ShellSpec(speed=18.0, damage=8, max_range=18.0, damages_terrain=False,
                        look="spore_dart", sound="orb"),
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
    # P12
    "cordyceps": CharacterSpec(
        name="cordyceps hunter", weapon="spore_dart", sprite="cordyceps", max_speed=4.4,
        accel=18.0, brake=30.0, size_px=24, aim_turn_speed=math.radians(130),
    ),
    # P11
    "lizardman": CharacterSpec(
        name="lizardman javelineer", weapon="javelin", sprite="lizardman", max_speed=4.6,
        accel=18.0, brake=30.0, size_px=24, aim_turn_speed=math.radians(130),
    ),
    # P9
    "glass_mage": CharacterSpec(
        name="glass mage", weapon="glass_shards", sprite="glass_mage", max_speed=4.2,
        accel=16.0, brake=30.0, size_px=24, aim_turn_speed=math.radians(100),
    ),
    # P8
    "woodcutter": CharacterSpec(
        name="ghost woodcutter", weapon="ghost_axe", sprite="woodcutter", max_speed=4.2,
        accel=16.0, brake=30.0, size_px=24, aim_turn_speed=math.radians(120),
    ),
    "apprentice": CharacterSpec(
        name="witch's apprentice", weapon="curse", sprite="apprentice", max_speed=4.4,
        accel=16.0, brake=30.0, size_px=24, aim_turn_speed=math.radians(100),
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
    # M28.4c: a chest with teeth (systems/chests.py wakes one; never rostered).
    "mimic": EnemySpec(
        name="mimic", kind="mimic", sprite="mimic_forest", scale=4, elite=True,
        max_hp=420, sight=16, biomes=(), weight=0, speed=3.6,
        damage=18, attack_radius=1.6, windup=0.55, cooldown=1.2, size_px=36, xp=30,
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
    # --- P8: the haunted forest (design/BOSSES.md 24.6; ai/forest.py) -----------------
    # Simple chasers.
    "skeleton": EnemySpec(
        name="skeleton", kind="skeleton", sprite="skeleton",
        max_hp=30, sight=14, biomes=("forest",), weight=3, speed=3.8,
        damage=9, attack_radius=1.2, windup=0.4, cooldown=1.2, size_px=20, xp=4,
    ),
    "risen_skeleton": EnemySpec(        # (one that pulled itself back together: no pile again)
        name="skeleton", kind="skeleton", sprite="skeleton",
        max_hp=30, sight=14, biomes=(), speed=3.8,
        damage=9, attack_radius=1.2, windup=0.4, cooldown=1.2, size_px=20, xp=2,
    ),
    "bone_pile": EnemySpec(
        name="bone pile", kind="bone_pile", sprite="bone_pile",
        max_hp=15, sight=1, biomes=(), speed=0.0, damage=0, size_px=18, xp=0,
    ),
    "woodsman": EnemySpec(
        name="rotting woodsman", kind="chaser", sprite="woodsman",
        max_hp=80, sight=12, biomes=("forest",), weight=3, speed=2.4,
        damage=13, attack_radius=1.4, windup=0.6, cooldown=1.5, size_px=22, xp=5,
    ),
    "spiderling": EnemySpec(
        name="spiderling", kind="chaser", sprite="spiderling", scale=2, group=(5, 8),
        max_hp=6, sight=14, biomes=("forest",), weight=3, speed=6.5,
        damage=3, attack_radius=0.8, windup=0.2, cooldown=0.8, size_px=10, xp=1,
    ),
    "bat": EnemySpec(
        name="bat", kind="bat", sprite="bat", scale=2, group=(4, 4),
        max_hp=10, sight=18, biomes=("forest",), weight=2, speed=7.0,
        damage=4, attack_radius=0.8, windup=0.15, cooldown=0.9, size_px=12, xp=1,
    ),
    # Spirits and the restless dead.
    "banshee": EnemySpec(
        name="banshee", kind="banshee", sprite="banshee",
        max_hp=45, sight=16, biomes=("forest",), weight=2, speed=3.6,
        damage=14, attack_radius=7.0, windup=0.9, cooldown=4.0, size_px=22, xp=7,
    ),
    "phantom": EnemySpec(
        name="phantom", kind="phantom", sprite="phantom",
        max_hp=40, sight=16, biomes=("forest",), weight=2, speed=3.2,
        damage=8, attack_radius=0.6, cooldown=0.8, size_px=22, xp=6,
    ),
    "grave_digger": EnemySpec(
        name="grave digger", kind="grave_digger", sprite="grave_digger",
        max_hp=60, sight=16, biomes=("forest",), weight=1, speed=3.0,
        damage=0, windup=1.0, size_px=22, xp=7,
    ),
    "headless_knight": EnemySpec(
        name="headless knight", kind="headless_knight", sprite="headless_knight", scale=4,
        elite=True, max_hp=380, sight=14, biomes=("forest",), weight=1, speed=2.6,
        damage=22, attack_radius=2.2, windup=0.7, cooldown=2.4, size_px=36, xp=22,
    ),
    "knight_head": EnemySpec(
        name="the knight's head", kind="knight_head", sprite="knight_head", scale=2,
        max_hp=999, sight=1, biomes=(), speed=0.0, damage=0, size_px=14, xp=0,
    ),
    # Beasts.
    "centipede": EnemySpec(
        name="giant centipede", kind="centipede", sprite="centipede_head", scale=2,
        max_hp=20, sight=16, biomes=("forest",), weight=2, speed=4.6,
        damage=10, attack_radius=1.0, windup=0.35, cooldown=1.1, size_px=16, xp=2,
    ),
    "giant_spider": EnemySpec(
        name="giant spider", kind="giant_spider", sprite="giant_spider",
        max_hp=70, sight=16, biomes=("forest",), weight=2, speed=4.0,
        damage=0, windup=0.4, size_px=26, xp=8,
    ),
    # Folk of the dark wood (the woodcutter and apprentice are Characters).
    "woodcutter": EnemySpec(
        name="ghost woodcutter", kind="archer", body="woodcutter", max_hp=50, sight=16,
        biomes=("forest",), weight=2, preferred_range=(5.0, 8.0), xp=6,
    ),
    "cultist": EnemySpec(
        name="cultist", kind="cultist", sprite="cultist",
        max_hp=55, sight=16, biomes=("forest",), weight=1, speed=3.4,
        damage=0, windup=1.2, size_px=22, xp=8,
    ),
    "candle": EnemySpec(
        name="ritual candle", kind="candle", sprite="candle", scale=2,
        max_hp=6, sight=1, biomes=(), speed=0.0, damage=0, size_px=10, xp=0,
    ),
    "apprentice": EnemySpec(
        name="witch's apprentice", kind="archer", body="apprentice", max_hp=40, sight=16,
        biomes=("forest",), weight=2, preferred_range=(6.0, 10.0), xp=6,
    ),
    "wendigo": EnemySpec(
        name="wendigo", kind="wendigo", sprite="wendigo", scale=4, elite=True,
        max_hp=300, sight=18, biomes=("forest",), weight=1, speed=6.0,
        damage=20, attack_radius=6.0, windup=0.4, cooldown=2.2, size_px=34, xp=20,
    ),
    # --- P9: the desert (design/BOSSES.md 24.7; ai/desert.py) -------------------------
    # Simple chasers.
    "fire_ant": EnemySpec(
        name="fire ant", kind="chaser", sprite="fire_ant", scale=2, group=(6, 9),
        max_hp=6, sight=14, biomes=("desert",), weight=3, speed=6.0,
        damage=4, attack_radius=0.8, windup=0.2, cooldown=0.8, size_px=10, xp=1,
    ),
    "husk": EnemySpec(
        name="dried husk", kind="chaser", sprite="husk",
        max_hp=75, sight=12, biomes=("desert",), weight=3, speed=2.5,
        damage=13, attack_radius=1.4, windup=0.65, cooldown=1.5, size_px=22, xp=5,
    ),
    "sand_imp": EnemySpec(
        name="sand imp", kind="hopper", sprite="sand_imp", scale=2,
        max_hp=16, sight=14, biomes=("desert",), weight=3, speed=9.0,
        damage=5, attack_radius=0.9, windup=0.2, cooldown=0.9, size_px=12, xp=2,
    ),
    "jackal": EnemySpec(
        name="desert jackal", kind="chaser", sprite="jackal",
        max_hp=28, sight=16, biomes=("desert",), weight=2, speed=8.0,
        damage=7, attack_radius=1.0, windup=0.25, cooldown=1.0, size_px=18, xp=3,
    ),
    # Beasts.
    "scorpion": EnemySpec(
        name="giant scorpion", kind="scorpion", sprite="scorpion", scale=4, elite=True,
        max_hp=340, sight=14, biomes=("desert",), weight=1, speed=3.4,
        damage=14, attack_radius=2.0, windup=0.35, cooldown=1.8, size_px=36, xp=20,
    ),
    "vulture": EnemySpec(
        name="vulture", kind="vulture", sprite="vulture", group=(2, 3),
        max_hp=30, sight=22, biomes=("desert",), weight=2, speed=6.5,
        damage=10, attack_radius=1.0, windup=0.6, cooldown=1.0, size_px=20, xp=4,
    ),
    "basilisk": EnemySpec(
        name="basilisk lizard", kind="basilisk", sprite="basilisk",
        max_hp=55, sight=16, biomes=("desert",), weight=2, speed=6.0,
        damage=6, attack_radius=9.0, windup=0.8, cooldown=4.0, size_px=20, xp=7,
    ),
    "rattlesnake": EnemySpec(
        name="rattlesnake", kind="rattlesnake", sprite="rattlesnake",
        max_hp=35, sight=10, biomes=("desert",), weight=2, speed=3.5,
        damage=14, attack_radius=4.0, windup=0.6, cooldown=1.5, size_px=18, xp=5,
    ),
    # Folk (the glass mage is a Character).
    "mummy": EnemySpec(
        name="mummy", kind="mummy", sprite="mummy", scale=4, elite=True,
        max_hp=360, sight=14, biomes=("desert",), weight=1, speed=2.2,
        damage=26, attack_radius=7.0, windup=0.8, cooldown=3.0, size_px=34, xp=20,
    ),
    "fire_dancer": EnemySpec(
        name="fire dancer", kind="fire_dancer", sprite="fire_dancer",
        max_hp=50, sight=16, biomes=("desert",), weight=2, speed=5.5,
        damage=12, attack_radius=4.0, windup=0.6, cooldown=2.4, size_px=22, xp=7,
    ),
    "glass_mage": EnemySpec(
        name="glass mage", kind="archer", body="glass_mage", max_hp=40, sight=18,
        biomes=("desert",), weight=2, preferred_range=(8.0, 12.0), xp=6,
    ),
    "dune_raider": EnemySpec(
        name="dune raider", kind="dune_raider", sprite="dune_raider",
        max_hp=55, sight=16, biomes=("desert",), weight=2, speed=6.0,
        damage=10, attack_radius=1.4, windup=0.2, cooldown=1.5, size_px=22, xp=6,
    ),
    # Odd ones.
    "tumbleweed": EnemySpec(
        name="tumbleweed", kind="tumbleweed", sprite="tumbleweed", scale=2, group=(3, 5),
        max_hp=12, sight=1, biomes=("desert",), weight=2, speed=5.0,
        damage=6, size_px=14, xp=1,
    ),
    "cactus_golem": EnemySpec(
        name="cactus golem", kind="cactus_golem", sprite="cactus_golem", scale=4,
        max_hp=150, sight=12, biomes=("desert",), weight=2, speed=2.0,
        damage=20, attack_radius=1.8, windup=0.8, cooldown=2.0, size_px=32, xp=10,
    ),
    "djinn_lamp": EnemySpec(
        name="djinn lamp", kind="djinn_lamp", sprite="djinn_lamp",
        max_hp=60, sight=16, biomes=("desert",), weight=1, speed=2.0,
        damage=8, size_px=22, xp=8,
    ),
    # --- P10: the ruins (design/BOSSES.md 24.8; ai/ruins.py) --------------------------
    # Simple chasers.
    "gnoll": EnemySpec(
        name="gnoll", kind="chaser", sprite="gnoll", group=(2, 3),
        max_hp=40, sight=14, biomes=("ruins",), weight=3, speed=4.5,
        damage=10, attack_radius=1.3, windup=0.45, cooldown=1.3, size_px=22, xp=4,
    ),
    "stone_imp": EnemySpec(
        name="stone imp", kind="chaser", sprite="stone_imp", scale=2,
        max_hp=25, sight=14, biomes=("ruins",), weight=3, speed=7.5,
        damage=6, attack_radius=0.9, windup=0.2, cooldown=0.9, size_px=12, xp=2,
    ),
    "crawling_hand": EnemySpec(
        name="crawling hand", kind="chaser", sprite="crawling_hand", scale=2, group=(6, 8),
        max_hp=6, sight=12, biomes=("ruins",), weight=3, speed=5.0,
        damage=3, attack_radius=0.8, windup=0.2, cooldown=0.8, size_px=10, xp=1,
    ),
    "lost_soldier": EnemySpec(
        name="lost soldier", kind="chaser", sprite="lost_soldier",
        max_hp=85, sight=12, biomes=("ruins",), weight=3, speed=2.4,
        damage=14, attack_radius=1.5, windup=0.6, cooldown=1.6, size_px=22, xp=5,
    ),
    # Constructs.
    "gargoyle": EnemySpec(
        name="gargoyle", kind="gargoyle", sprite="gargoyle",
        max_hp=60, sight=9, biomes=("ruins",), weight=2, speed=4.0,
        damage=14, attack_radius=1.0, windup=0.5, cooldown=1.5, size_px=22, xp=7,
    ),
    "clockwork": EnemySpec(
        name="clockwork sentry", kind="clockwork", sprite="clockwork",
        max_hp=55, sight=16, biomes=("ruins",), weight=2, speed=3.6,
        damage=0, windup=0.8, cooldown=3.5, size_px=22, xp=7,
    ),
    "colossus": EnemySpec(
        name="colossus", kind="colossus", sprite="colossus", scale=4, elite=True,
        max_hp=450, sight=16, biomes=("ruins",), weight=1, speed=1.8,
        damage=24, attack_radius=6.0, windup=1.0, cooldown=3.5, size_px=40, xp=24,
    ),
    "rubble_crab": EnemySpec(
        name="rubble crab", kind="rubble_crab", sprite="rubble_crab",
        max_hp=40, sight=12, biomes=("ruins",), weight=2, speed=2.6,
        damage=11, attack_radius=1.2, windup=0.45, cooldown=1.4, size_px=24, xp=7,
    ),
    # Scavengers and soldiers.
    "gem_thief": EnemySpec(
        name="gem thief", kind="gem_thief", sprite="gem_thief",
        max_hp=30, sight=20, biomes=("ruins",), weight=2, speed=6.5,
        damage=0, size_px=20, xp=5,
    ),
    "sniper": EnemySpec(
        name="crossbow sniper", kind="sniper", sprite="sniper",
        max_hp=40, sight=26, biomes=("ruins",), weight=2, speed=3.6,
        damage=0, windup=1.2, cooldown=4.0, size_px=22, xp=7,
    ),
    "flail_brute": EnemySpec(
        name="flail brute", kind="flail_brute", sprite="flail_brute", scale=4, elite=True,
        max_hp=360, sight=14, biomes=("ruins",), weight=1, speed=3.0,
        damage=12, attack_radius=5.0, windup=1.4, cooldown=2.6, size_px=34, xp=20,
    ),
    # Haunts.
    "rune_mine": EnemySpec(
        name="rune mine", kind="rune_mine", sprite="rune_mine", scale=2,
        max_hp=20, sight=14, biomes=("ruins",), weight=2, speed=2.2,
        damage=20, attack_radius=2.2, windup=1.0, size_px=14, xp=3,
    ),
    "haunted_blade": EnemySpec(
        name="haunted blade", kind="haunted_blade", sprite="haunted_blade", group=(3, 3),
        max_hp=25, sight=16, biomes=("ruins",), weight=2, speed=6.0,
        damage=9, attack_radius=1.0, windup=0.2, cooldown=1.0, size_px=14, xp=3,
    ),
    "bell_ghost": EnemySpec(
        name="bell ghost", kind="bell_ghost", sprite="bell_ghost",
        max_hp=35, sight=18, biomes=("ruins",), weight=1, speed=3.5,
        damage=4, size_px=22, xp=7,
    ),
    # --- P11: the swamp (design/BOSSES.md 24.9; ai/swamp.py) --------------------------
    # Simple chasers.
    "bog_zombie": EnemySpec(
        name="bog zombie", kind="chaser", sprite="bog_zombie",
        max_hp=80, sight=12, biomes=("swamp",), weight=3, speed=2.4,
        damage=13, attack_radius=1.4, windup=0.6, cooldown=1.5, size_px=22, xp=5,
    ),
    "newt": EnemySpec(
        name="newt", kind="chaser", sprite="newt", scale=2, group=(5, 8),
        max_hp=6, sight=14, biomes=("swamp",), weight=3, speed=6.0,
        damage=3, attack_radius=0.8, windup=0.2, cooldown=0.8, size_px=10, xp=1,
    ),
    "gator_hatchling": EnemySpec(
        name="gator hatchling", kind="chaser", sprite="gator_hatchling", scale=2, group=(3, 4),
        max_hp=14, sight=14, biomes=("swamp",), weight=3, speed=6.5,
        damage=5, attack_radius=0.9, windup=0.2, cooldown=0.9, size_px=12, xp=2,
    ),
    "mudskipper": EnemySpec(
        name="mudskipper", kind="hopper", sprite="mudskipper", scale=2,
        max_hp=16, sight=14, biomes=("swamp",), weight=2, speed=8.5,
        damage=5, attack_radius=0.9, windup=0.2, cooldown=0.9, size_px=12, xp=2,
    ),
    # Beasts.
    "crocodile": EnemySpec(
        name="bog crocodile", kind="crocodile", sprite="crocodile", scale=4, elite=True,
        max_hp=360, sight=14, biomes=("swamp",), weight=1, speed=3.0,
        damage=9, attack_radius=5.0, windup=0.5, cooldown=3.0, size_px=34, xp=20,
    ),
    "turtle": EnemySpec(
        name="snapping turtle", kind="turtle", sprite="turtle", scale=3,
        max_hp=120, sight=12, biomes=("swamp",), weight=2, speed=2.0,
        damage=18, attack_radius=1.2, windup=0.5, cooldown=1.6, size_px=26, xp=8,
    ),
    "heron": EnemySpec(
        name="heron", kind="heron", sprite="heron",
        max_hp=40, sight=16, biomes=("swamp",), weight=2, speed=4.0,
        damage=14, attack_radius=3.5, windup=0.5, cooldown=1.8, size_px=20, xp=6,
    ),
    # Folk (the lizardman is a Character).
    "swamp_hag": EnemySpec(
        name="swamp hag", kind="swamp_hag", sprite="swamp_hag",
        max_hp=50, sight=16, biomes=("swamp",), weight=2, speed=3.2,
        damage=0, windup=1.0, cooldown=4.0, size_px=22, xp=7,
    ),
    "lizardman": EnemySpec(
        name="lizardman javelineer", kind="archer", body="lizardman", group=(2, 2),
        max_hp=40, sight=16, biomes=("swamp",), weight=2, preferred_range=(7.0, 11.0), xp=5,
    ),
    "marsh_light": EnemySpec(
        name="marsh light", kind="marsh_light", sprite="marsh_light", scale=2,
        max_hp=30, sight=16, biomes=("swamp",), weight=2, speed=3.0,
        damage=5, attack_radius=6.0, cooldown=2.5, size_px=14, xp=6,
    ),
    "marsh_light_fake": EnemySpec(      # (one of its two illusions: never hit, never killed)
        name="marsh light", kind="marsh_light", sprite="marsh_light", scale=2,
        max_hp=30, sight=16, biomes=(), speed=3.0,
        damage=5, attack_radius=6.0, cooldown=2.5, size_px=14, xp=0,
    ),
    # Rot and muck.
    "bloated_corpse": EnemySpec(
        name="bloated corpse", kind="bloated_corpse", sprite="bloated_corpse",
        max_hp=60, sight=12, biomes=("swamp",), weight=2, speed=2.2,
        damage=0, attack_radius=1.2, size_px=24, xp=5,
    ),
    "sludge": EnemySpec(
        name="sludge", kind="sludge", sprite="sludge", scale=4,
        max_hp=90, sight=12, biomes=("swamp",), weight=2, speed=2.2,
        damage=12, attack_radius=1.6, windup=0.5, cooldown=1.5, size_px=30, xp=4,
    ),
    "sludge_mid": EnemySpec(
        name="sludge", kind="sludge", sprite="sludge_mid", scale=3,
        max_hp=40, sight=12, biomes=(), speed=3.0,
        damage=8, attack_radius=1.2, windup=0.4, cooldown=1.3, size_px=22, xp=2,
    ),
    "sludge_small": EnemySpec(
        name="sludge", kind="sludge", sprite="sludge_small", scale=2,
        max_hp=15, sight=12, biomes=(), speed=4.2,
        damage=4, attack_radius=0.9, windup=0.3, cooldown=1.0, size_px=14, xp=1,
    ),
    # --- P12: the mushroom biome (design/BOSSES.md 24.10; ai/mushroom.py) --------------
    # Simple chasers.
    "sporeling": EnemySpec(
        name="sporeling", kind="chaser", sprite="sporeling", scale=2, group=(5, 8),
        max_hp=6, sight=14, biomes=("mushroom",), weight=3, speed=6.0,
        damage=3, attack_radius=0.8, windup=0.2, cooldown=0.8, size_px=10, xp=1,
    ),
    "fungus_gnat": EnemySpec(
        name="fungus gnat", kind="bat", sprite="fungus_gnat", scale=2, group=(6, 6),
        max_hp=5, sight=18, biomes=("mushroom",), weight=2, speed=7.0,
        damage=2, attack_radius=0.7, windup=0.15, cooldown=0.7, size_px=10, xp=1,
    ),
    "shroomling": EnemySpec(
        name="shroomling", kind="chaser", sprite="shroomling", group=(2, 3),
        max_hp=30, sight=14, biomes=("mushroom",), weight=3, speed=4.8,
        damage=8, attack_radius=1.0, windup=0.3, cooldown=1.1, size_px=18, xp=3,
    ),
    "mold_zombie": EnemySpec(
        name="mold zombie", kind="chaser", sprite="mold_zombie",
        max_hp=80, sight=12, biomes=("mushroom",), weight=3, speed=2.4,
        damage=13, attack_radius=1.4, windup=0.6, cooldown=1.5, size_px=22, xp=5,
    ),
    # Fungal folk (the cordyceps hunter is a Character).
    "myconid": EnemySpec(
        name="myconid shaman", kind="myconid", sprite="myconid",
        max_hp=50, sight=16, biomes=("mushroom",), weight=1, speed=3.4,
        damage=0, cooldown=5.0, size_px=22, xp=7,
    ),
    "cordyceps": EnemySpec(
        name="cordyceps hunter", kind="cordyceps", body="cordyceps", max_hp=45, sight=18,
        biomes=("mushroom",), weight=2, preferred_range=(7.0, 11.0), xp=6,
    ),
    "fungal_brute": EnemySpec(
        name="fungal brute", kind="fungal_brute", sprite="fungal_brute", scale=4, elite=True,
        max_hp=340, sight=14, biomes=("mushroom",), weight=1, speed=2.6,
        damage=26, attack_radius=2.0, windup=0.8, cooldown=2.0, size_px=36, xp=20,
    ),
    "rootweaver": EnemySpec(
        name="rootweaver", kind="rootweaver", sprite="rootweaver",
        max_hp=55, sight=16, biomes=("mushroom",), weight=2, speed=3.4,
        damage=12, cooldown=4.0, size_px=22, xp=7,
    ),
    # Critters.
    "giant_snail": EnemySpec(
        name="giant snail", kind="giant_snail", sprite="giant_snail",
        max_hp=110, sight=12, biomes=("mushroom",), weight=2, speed=1.6,
        damage=12, attack_radius=1.3, windup=0.6, cooldown=1.6, size_px=26, xp=7,
    ),
    "pillbug": EnemySpec(
        name="pillbug", kind="pillbug", sprite="pillbug",
        max_hp=60, sight=14, biomes=("mushroom",), weight=2, speed=2.5,
        damage=10, windup=0.4, size_px=22, xp=6,
    ),
    "mantis": EnemySpec(
        name="mantis", kind="mantis", sprite="mantis", scale=4, elite=True,
        max_hp=280, sight=16, biomes=("mushroom",), weight=1, speed=4.5,
        damage=20, attack_radius=7.0, windup=0.5, cooldown=2.0, size_px=32, xp=20,
    ),
    # Strange growths.
    "fairy_ring": EnemySpec(            # (its middle: unseen; its caps are what you break)
        name="fairy ring", kind="fairy_ring", sprite="fairy_cap", scale=2,
        max_hp=1, sight=14, biomes=("mushroom",), weight=1, speed=0.0,
        damage=0, size_px=10, xp=8,
    ),
    "fairy_cap": EnemySpec(
        name="fairy cap", kind="fairy_cap", sprite="fairy_cap", scale=2,
        max_hp=8, sight=1, biomes=(), speed=0.0, damage=0, size_px=10, xp=0,
    ),
    "mold_core": EnemySpec(
        name="mold core", kind="mold_core", sprite="mold_core",
        max_hp=120, sight=14, biomes=("mushroom",), weight=1, speed=0.0,
        damage=3, size_px=26, xp=8,
    ),
    # --- M29.2: Paradise (design/OCEAN.md 4; ai/paradise.py) ---------------------------
    # Every one unveils on its own (ai/paradise.Angel): `speed` and `damage`
    # are the unveiled ones; serene they move at x UNVEIL[3] and their slow
    # hymn-like attacks use PARADISE_SHOTS. On top of these: ZONE_TOUGH.
    # Angels.
    "cherub": EnemySpec(
        name="cherub", kind="cherub", sprite="cherub", group=(1, 2),
        max_hp=60, sight=16, biomes=("paradise",), weight=3, speed=5.5,
        damage=14, attack_radius=1.3, windup=0.35, cooldown=1.2, size_px=24, xp=10,
    ),
    "seraph": EnemySpec(
        name="seraph", kind="seraph", sprite="seraph", scale=4, elite=True,
        max_hp=320, sight=18, biomes=("paradise",), weight=1, speed=3.0,
        damage=0, windup=0.5, cooldown=4.5, size_px=36, xp=35,
    ),
    "ophan": EnemySpec(
        name="ophan", kind="ophan", sprite="ophan",
        max_hp=70, sight=16, biomes=("paradise",), weight=2, speed=4.0,
        damage=16, windup=0.5, size_px=24, xp=10,
    ),
    "watcher": EnemySpec(
        name="watcher", kind="watcher", sprite="watcher",
        max_hp=110, sight=18, biomes=("paradise",), weight=2, speed=0.0,
        damage=20, windup=0.9, cooldown=3.2, size_px=26, xp=12,
    ),
    # Chasers.
    "lamb": EnemySpec(
        name="the Lamb", kind="lamb", sprite="lamb", group=(2, 3),
        max_hp=50, sight=16, biomes=("paradise",), weight=3, speed=4.5,
        damage=18, attack_radius=10.0, windup=0.6, cooldown=1.4, size_px=22, xp=8,
    ),
    "dove": EnemySpec(
        name="dove", kind="dove", sprite="dove", scale=2, group=(5, 7),
        max_hp=10, sight=18, biomes=("paradise",), weight=2, speed=6.0,
        damage=7, attack_radius=0.8, windup=0.2, cooldown=2.0, size_px=12, xp=2,
    ),
    "locust": EnemySpec(
        name="locust", kind="locust", sprite="locust", scale=2, group=(6, 9),
        max_hp=7, sight=16, biomes=("paradise",), weight=2, speed=7.5,
        damage=4, attack_radius=0.7, windup=0.15, cooldown=0.6, size_px=10, xp=1,
    ),
    "halo": EnemySpec(
        name="halo", kind="halo", sprite="halo", scale=2,
        max_hp=40, sight=16, biomes=("paradise",), weight=2, speed=8.5,
        damage=5, size_px=16, xp=8,
    ),
    # M29.3. Heralds. (Serene, all but the trumpeter and the chorister are
    # harmless.) The choristers live at the choir rings (CHORISTER), not
    # rolled at random.
    "trumpeter": EnemySpec(
        name="trumpeter", kind="trumpeter", sprite="trumpeter", scale=4, elite=True,
        max_hp=300, sight=18, biomes=("paradise",), weight=1, speed=2.6,
        damage=14, windup=0.7, cooldown=5.0, size_px=34, xp=35,
    ),
    "censer_bearer": EnemySpec(
        name="censer-bearer", kind="censer_bearer", sprite="censer_bearer",
        max_hp=65, sight=16, biomes=("paradise",), weight=2, speed=3.4,
        damage=10, windup=0.4, cooldown=2.4, size_px=22, xp=10,
    ),
    "bowl_bearer": EnemySpec(
        name="bowl-bearer", kind="bowl_bearer", sprite="bowl_bearer",
        max_hp=70, sight=16, biomes=("paradise",), weight=2, speed=3.2,
        damage=4, windup=0.9, cooldown=4.0, size_px=22, xp=10,
    ),
    "chorister": EnemySpec(
        name="chorister", kind="chorister", sprite="chorister",
        max_hp=55, sight=16, biomes=(), speed=3.0,
        damage=0, windup=0.5, cooldown=3.5, size_px=22, xp=10,
    ),
    # Saints and beasts. The leviathans live in the river of blood
    # (LEVIATHAN), not rolled at random.
    "weeping_saint": EnemySpec(
        name="weeping saint", kind="weeping_saint", sprite="weeping_saint",
        max_hp=80, sight=16, biomes=("paradise",), weight=2, speed=2.4,
        damage=12, windup=0.5, cooldown=2.8, size_px=22, xp=11,
    ),
    "martyr": EnemySpec(
        name="martyr", kind="martyr", sprite="martyr",
        max_hp=75, sight=16, biomes=("paradise",), weight=2, speed=3.0,
        damage=0, windup=0.45, cooldown=1.6, size_px=22, xp=11,
    ),
    "behemoth": EnemySpec(
        name="behemoth", kind="behemoth", sprite="behemoth", scale=4, elite=True,
        max_hp=420, sight=16, biomes=("paradise",), weight=1, speed=2.8,
        damage=30, attack_radius=14.0, windup=0.8, cooldown=2.0, size_px=40, xp=40,
    ),
    "leviathan": EnemySpec(
        name="leviathan", kind="leviathan", sprite="leviathan", scale=4, elite=True,
        max_hp=380, sight=20, biomes=(), speed=11.0,
        damage=16, windup=0.4, cooldown=1.6, size_px=36, xp=40,
    ),
    # M29.4: Paradise's boss, form 1 (OCEAN.md 6.1): one cavalry of four
    # riders sharing this health (ai/bosses.Cavalry); its light lances'
    # pillars (break one to open a cage).
    "cavalry": EnemySpec(
        name="the Serene Cavalry", kind="cavalry", max_hp=12000, sight=400,
        biomes=(), size_px=60, xp=1500,
    ),
    "light_pillar": EnemySpec(
        name="pillar of light", kind="light_pillar", sprite="light_pillar", scale=3,
        max_hp=100, sight=1, biomes=(), speed=0.0, damage=0, size_px=20, xp=0,
    ),
    # M29.5: form 2, the Four Horsemen (OCEAN.md 6.2; ai/horsemen.py), each
    # with its own health; Conquest's banner; the dead risen (Death's power).
    "conquest": EnemySpec(
        name="Conquest", kind="conquest", max_hp=6000, sight=400, biomes=(), size_px=56, xp=400,
    ),
    "war": EnemySpec(
        name="War", kind="war", max_hp=6000, sight=400, biomes=(), size_px=56, xp=400,
    ),
    "famine": EnemySpec(
        name="Famine", kind="famine", max_hp=6000, sight=400, biomes=(), size_px=56, xp=400,
    ),
    "death": EnemySpec(
        name="Death", kind="death", max_hp=6000, sight=400, biomes=(), size_px=56, xp=400,
    ),
    "conquest_banner": EnemySpec(
        name="Conquest's banner", kind="conquest_banner", sprite="conquest_banner", scale=3,
        max_hp=300, sight=1, biomes=(), speed=0.0, damage=6, size_px=20, xp=0,
    ),
    "pale_shade": EnemySpec(
        name="pale shade", kind="pale_shade", sprite="pale_shade",
        max_hp=30, sight=40, biomes=(), speed=4.5,
        damage=5, attack_radius=1.1, windup=0.3, cooldown=1.0, size_px=20, xp=0,
    ),
    "pale_rider": EnemySpec(
        name="pale rider", kind="pale_shade", sprite="pale_rider", scale=4,
        max_hp=300, sight=40, biomes=(), speed=8.5,
        damage=14, attack_radius=1.8, windup=0.35, cooldown=1.0, size_px=34, xp=0,
    ),
    # --- M30.2: Pandemonium's revellers (design/OCEAN.md 14-15; ai/pandemonium.py) -------
    # They live where they feast, drink, dance and play: residents round the
    # banquet tables and bandstands (ai/pandemonium.residents), never rolled
    # at random. In the trance they ignore you (moving at x REVEL[4]); a
    # group frenzies as one. `speed` and `damage` are frenzied. On top of
    # these: ZONE_TOUGH.
    # Feasters and drinkers.
    "glutton": EnemySpec(
        name="glutton", kind="glutton", sprite="glutton", scale=4,
        max_hp=150, sight=16, biomes=(), speed=2.4,
        damage=18, attack_radius=1.4, windup=0.6, cooldown=3.0, size_px=30, xp=14,
    ),
    "drunkard": EnemySpec(
        name="drunkard", kind="drunkard", sprite="drunkard",
        max_hp=70, sight=16, biomes=(), speed=3.6,
        damage=12, windup=0.4, cooldown=2.2, size_px=22, xp=10,
    ),
    "toastmaster": EnemySpec(
        name="toastmaster", kind="toastmaster", sprite="toastmaster", scale=4, elite=True,
        max_hp=300, sight=18, biomes=(), speed=3.0,
        damage=16, windup=0.8, cooldown=5.0, size_px=32, xp=35,
    ),
    "ravenous": EnemySpec(
        name="the Ravenous", kind="ravenous", sprite="ravenous",
        max_hp=45, sight=16, biomes=(), speed=7.2,
        damage=5, attack_radius=0.8, windup=0.0, cooldown=0.6, size_px=20, xp=8,
    ),
    # Dancers and musicians.
    "dancer": EnemySpec(
        name="dancer", kind="dancer", sprite="dancer",
        max_hp=60, sight=16, biomes=(), speed=6.5,
        damage=11, attack_radius=1.0, windup=0.35, cooldown=0.6, size_px=22, xp=10,
    ),
    "masked_dancer": EnemySpec(
        name="masked dancer", kind="masked_dancer", sprite="masked_dancer",
        max_hp=65, sight=16, biomes=(), speed=5.0,
        damage=16, attack_radius=1.2, windup=0.3, cooldown=3.5, size_px=22, xp=12,
    ),
    "band_drummer": EnemySpec(
        name="band drummer", kind="band_drummer", sprite="band_drummer",
        max_hp=90, sight=16, biomes=(), speed=0.0,
        damage=14, windup=0.0, cooldown=1.25, size_px=24, xp=10,
    ),
    "piper": EnemySpec(
        name="piper", kind="piper", sprite="piper", scale=4, elite=True,
        max_hp=280, sight=18, biomes=(), speed=2.6,
        damage=0, windup=0.6, cooldown=6.0, size_px=30, xp=35,
    ),
    # M30.3. The vain and the greedy (revellers, in the trance like the rest).
    "vain": EnemySpec(
        name="the Vain", kind="vain", sprite="vain",
        max_hp=70, sight=16, biomes=(), speed=3.4,
        damage=0, windup=0.8, cooldown=4.0, size_px=22, xp=12,
    ),
    "gilded_reveller": EnemySpec(
        name="gilded reveller", kind="gilded_reveller", sprite="gilded_reveller",
        max_hp=140, sight=16, biomes=(), speed=1.8,
        damage=26, windup=0.7, cooldown=2.6, size_px=24, xp=14,
    ),
    "hoarder": EnemySpec(
        name="hoarder", kind="hoarder", sprite="hoarder",
        max_hp=75, sight=16, biomes=(), speed=3.2,
        damage=8, windup=0.3, cooldown=2.4, size_px=22, xp=10,
    ),
    "beloved": EnemySpec(
        name="the Beloved", kind="beloved", sprite="beloved", scale=4, elite=True,
        max_hp=260, sight=18, biomes=(), speed=2.8,
        damage=0, windup=0.5, cooldown=3.5, size_px=30, xp=35,
    ),
    # The demon hosts: never in the trance -- always alert, at their posts
    # by the groups (ai/pandemonium.residents).
    "cupbearer": EnemySpec(
        name="cupbearer", kind="cupbearer", sprite="cupbearer",
        max_hp=90, sight=16, biomes=(), speed=4.2,
        damage=8, windup=0.4, cooldown=2.6, size_px=24, xp=12,
    ),
    "carver": EnemySpec(
        name="carver", kind="carver", sprite="carver",
        max_hp=130, sight=16, biomes=(), speed=3.8,
        damage=18, attack_radius=1.4, windup=0.45, cooldown=3.0, size_px=26, xp=14,
    ),
    "bouncer": EnemySpec(
        name="bouncer", kind="bouncer", sprite="bouncer", scale=4,
        max_hp=240, sight=16, biomes=(), speed=2.6,
        damage=22, windup=0.7, cooldown=4.0, size_px=32, xp=18,
    ),
    "master_of_revels": EnemySpec(
        name="Master of Revels", kind="master_of_revels", sprite="master_of_revels", scale=4,
        elite=True, max_hp=320, sight=18, biomes=(), speed=2.8,
        damage=16, windup=1.0, cooldown=4.0, size_px=30, xp=40,
    ),
    # M30.4: Pandemonium's boss, form 1 (OCEAN.md 17.1; ai/feast.FeastHost).
    "host_of_feast": EnemySpec(
        name="the Host of the Feast", kind="host_of_feast", sprite="host_of_feast", scale=6,
        max_hp=12000, sight=400, biomes=(), size_px=64, xp=1500,
    ),
    # M30.5: form 2's demon waiters, bringing him a course (ai/hunger.Waiter).
    "feast_waiter": EnemySpec(
        name="demon waiter", kind="feast_waiter", sprite="feast_waiter",
        max_hp=60, sight=1, biomes=(), speed=3.2, damage=0, size_px=22, xp=4,
    ),
    # --- M31.2: Pangaea's shore ring (design/OCEAN.md 26; ai/pangaea.py) ---------------
    # Every attack echoes ECHO[0] s later (ai/pangaea.Beast). Each is rolled
    # only on its own ring (PANGAEA_RING_OF). On top of these: ZONE_TOUGH.
    # The great mammals.
    "mammoth": EnemySpec(
        name="mammoth", kind="mammoth", sprite="mammoth", scale=5, elite=True, group=(2, 3),
        max_hp=260, sight=18, biomes=("pangaea",), weight=1, speed=2.6,
        damage=26, attack_radius=3.0, windup=0.6, cooldown=2.4, size_px=40, xp=30,
    ),
    "sabre_tooth": EnemySpec(
        name="sabre-tooth", kind="sabre_tooth", sprite="sabre_tooth", scale=4,
        max_hp=110, sight=18, biomes=("pangaea",), weight=3, speed=4.6,
        damage=16, attack_radius=1.0, windup=0.7, cooldown=3.0, size_px=28, xp=14,
    ),
    "woolly_rhino": EnemySpec(
        name="woolly rhino", kind="woolly_rhino", sprite="woolly_rhino", scale=4,
        max_hp=200, sight=16, biomes=("pangaea",), weight=2, speed=2.8,
        damage=24, windup=0.8, cooldown=1.0, size_px=34, xp=18,
    ),
    "cave_bear": EnemySpec(
        name="cave bear", kind="cave_bear", sprite="cave_bear", scale=4,
        max_hp=220, sight=16, biomes=("pangaea",), weight=2, speed=3.6,
        damage=20, attack_radius=3.0, windup=0.8, cooldown=2.6, size_px=32, xp=18,
    ),
    # The early hunters (from the painted caves).
    "spear_hunter": EnemySpec(
        name="spear hunter", kind="spear_hunter", sprite="spear_hunter", group=(1, 2),
        max_hp=70, sight=18, biomes=("pangaea",), weight=3, speed=4.0,
        damage=0, windup=0.5, cooldown=2.2, size_px=22, xp=10,
    ),
    "trapper": EnemySpec(
        name="trapper", kind="trapper", sprite="trapper",
        max_hp=65, sight=16, biomes=("pangaea",), weight=2, speed=4.2,
        damage=0, windup=0.4, cooldown=3.4, size_px=22, xp=10,
    ),
    "fire_bearer": EnemySpec(
        name="fire-bearer", kind="fire_bearer", sprite="fire_bearer",
        max_hp=75, sight=16, biomes=("pangaea",), weight=2, speed=3.8,
        damage=14, attack_radius=2.4, windup=0.5, cooldown=3.8, size_px=22, xp=12,
    ),
    "shaman": EnemySpec(
        name="shaman", kind="shaman", sprite="shaman", scale=4, elite=True,
        max_hp=280, sight=18, biomes=("pangaea",), weight=1, speed=2.8,
        damage=0, windup=1.1, cooldown=5.5, size_px=28, xp=35,
    ),
    # --- M31.3: Pangaea's middle ring and heart (OCEAN.md 26; ai/pangaea.py) -------------
    # The dinosaurs (the middle ring).
    "raptor": EnemySpec(
        name="raptor", kind="raptor", sprite="raptor", group=(3, 4),
        max_hp=55, sight=18, biomes=("pangaea",), weight=3, speed=6.0,
        damage=14, windup=0.5, cooldown=1.0, size_px=22, xp=8,
    ),
    "tyrant": EnemySpec(
        name="the Tyrant", kind="tyrant", sprite="tyrant", scale=6, elite=True,
        max_hp=520, sight=20, biomes=("pangaea",), weight=1, speed=2.6,
        damage=30, attack_radius=3.6, windup=0.5, cooldown=1.6, size_px=46, xp=50,
    ),
    "club_tail": EnemySpec(
        name="club-tail", kind="club_tail", sprite="club_tail", scale=4,
        max_hp=240, sight=16, biomes=("pangaea",), weight=2, speed=2.2,
        damage=26, attack_radius=3.6, windup=0.7, cooldown=2.2, size_px=34, xp=20,
    ),
    "pterosaur": EnemySpec(
        name="pterosaur", kind="pterosaur", sprite="pterosaur", scale=4,
        max_hp=80, sight=22, biomes=("pangaea",), weight=2, speed=6.0,
        damage=12, windup=0.7, cooldown=2.5, size_px=26, xp=12,
    ),
    # The giant insects and the earliest life (the heart).
    "dragonfly": EnemySpec(
        name="giant dragonfly", kind="dragonfly", sprite="dragonfly", group=(3, 3),
        max_hp=35, sight=18, biomes=("pangaea",), weight=2, speed=9.0,
        damage=10, windup=0.45, size_px=18, xp=6,
    ),
    "bombardier_beetle": EnemySpec(
        name="bombardier beetle", kind="bombardier_beetle", sprite="bombardier_beetle",
        max_hp=120, sight=16, biomes=("pangaea",), weight=3, speed=3.2,
        damage=24, windup=0.6, cooldown=2.5, size_px=24, xp=12,
    ),
    "ant_mound": EnemySpec(
        name="ant mound", kind="ant_mound", sprite="ant_mound", scale=4,
        max_hp=300, sight=18, biomes=("pangaea",), weight=2, speed=0.0,
        damage=0, size_px=32, xp=20,
    ),
    "giant_ant": EnemySpec(                      # (sent out by its mound, never rolled)
        name="giant ant", kind="giant_ant", sprite="giant_ant", scale=2,
        max_hp=30, sight=18, biomes=(), speed=3.6,
        damage=8, attack_radius=1.0, windup=0.3, cooldown=0.9, size_px=14, xp=3,
    ),
    "sea_scorpion": EnemySpec(                   # (lives in the steaming pools: residents)
        name="sea scorpion", kind="sea_scorpion", sprite="sea_scorpion", scale=5, elite=True,
        max_hp=380, sight=16, biomes=(), speed=3.5,
        damage=22, windup=0.6, cooldown=1.6, size_px=38, xp=40,
    ),
    "hatchling": EnemySpec(                      # (out of a broken egg, never rolled)
        name="hatchling", kind="hatchling", sprite="hatchling", scale=2,
        max_hp=14, sight=16, biomes=(), speed=6.5,
        damage=5, attack_radius=0.9, windup=0.25, cooldown=0.8, size_px=12, xp=2,
    ),
    # M31.4: Pangaea's boss, form 1: the ages (OCEAN.md 28.1; ai/ancestor.py).
    # Its picture and body change with its age (the mammal, the lizard, the
    # insect); this is the mammal's.
    "ancestor": EnemySpec(
        name="the Ancestor", kind="ancestor", sprite="ancestor_mammal", scale=7,
        max_hp=12000, sight=400, biomes=(), windup=0.8, size_px=64, xp=1500,
    ),
    # M31.5: form 2's first life, crawling out of the sea (ai/first_life.py):
    # left alone, a blob evolves into a crawler, then into one of the
    # island's beasts (LIFE_BEASTS). Never rolled.
    "first_blob": EnemySpec(
        name="first life", kind="first_blob", sprite="first_blob", scale=2,
        max_hp=16, sight=40, biomes=(), speed=1.8, damage=0, size_px=12, xp=2,
    ),
    "first_crawler": EnemySpec(
        name="first crawler", kind="first_crawler", sprite="first_crawler", scale=3,
        max_hp=32, sight=40, biomes=(), speed=3.4, damage=10, attack_radius=1.0,
        windup=0.35, cooldown=1.0, size_px=18, xp=4,
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
    # M25.2: the forester's "destroy" quest and Love & Cuddles. Rabid
    # squirrels guard its nut caches and pour out of the trees at its call.
    "rabid_squirrel": EnemySpec(
        name="rabid squirrel", kind="chaser", sprite="rabid_squirrel", scale=2,
        max_hp=22, sight=18, biomes=(), speed=7.5,
        damage=5, attack_radius=0.9, windup=0.2, cooldown=0.8, size_px=12, xp=2,
    ),
    "love_cuddles": EnemySpec(
        name="Love & Cuddles", kind="love_cuddles", max_hp=8000, sight=400,
        biomes=(), size_px=56, xp=400,
    ),
    # M25.3: the lumberjack's "fell" quest and The Fallen. Mimic saplings
    # rip free of some marked trees; bark beetles crawl out of its bark.
    "mimic_sapling": EnemySpec(
        name="mimic sapling", kind="chaser", sprite="mimic_sapling", scale=3,
        max_hp=90, sight=20, biomes=(), speed=4.2,
        damage=10, attack_radius=1.3, windup=0.45, cooldown=1.2, size_px=24, xp=5,
    ),
    "bark_beetle": EnemySpec(
        name="bark beetle", kind="chaser", sprite="bark_beetle", scale=2,
        max_hp=16, sight=24, biomes=(), speed=6.5,
        damage=4, attack_radius=0.8, windup=0.2, cooldown=0.8, size_px=12, xp=1,
    ),
    "the_fallen": EnemySpec(
        name="The Fallen", kind="the_fallen", max_hp=8000, sight=400,
        biomes=(), size_px=60, xp=400,
    ),
    # M26.1: Mycelium, the fly agaric (amanita muscaria). Every Mycelium is
    # called just "Mycelium". Its warts and its flies are bodies too
    # (ai/bosses.MycoPart: part of it, worth nothing).
    "mycelium_amanita": EnemySpec(
        name="Mycelium", kind="mycelium_amanita", max_hp=8000, sight=400,
        biomes=(), size_px=60, xp=400,
    ),
    "amanita_wart": EnemySpec(
        name="wart", kind="myco_part", max_hp=60, sight=400, biomes=(), size_px=10, xp=0,
    ),
    "myco_fly": EnemySpec(
        name="fly", kind="myco_part", max_hp=6, sight=400, biomes=(), size_px=8, xp=0,
    ),
    # M26.2: Mycelium, the shaggy ink cap. Its ink-cap sprouts are parts of
    # it (MycoPart); its scrawled letters may rise as ink imps.
    "mycelium_inkcap": EnemySpec(
        name="Mycelium", kind="mycelium_inkcap", max_hp=8000, sight=400,
        biomes=(), size_px=60, xp=400,
    ),
    "ink_sprout": EnemySpec(
        name="ink cap", kind="myco_part", max_hp=30, sight=400, biomes=(), size_px=14, xp=0,
    ),
    "ink_imp": EnemySpec(
        name="ink imp", kind="chaser", sprite="ink_imp", scale=2,
        max_hp=14, sight=24, biomes=(), speed=6.8,
        damage=4, attack_radius=0.8, windup=0.2, cooldown=0.8, size_px=12, xp=1,
    ),
    # M26.3: Mycelium, the giant puffball. Its little puffball mines are
    # parts of it (MycoPart); split, its two halves are bodies that pass
    # their hits on to it (ai/bosses.PuffHalf).
    "mycelium_puffball": EnemySpec(
        name="Mycelium", kind="mycelium_puffball", max_hp=8000, sight=400,
        biomes=(), size_px=70, xp=400,
    ),
    "puff_mine": EnemySpec(
        name="puffball", kind="myco_part", max_hp=1, sight=400, biomes=(), size_px=12, xp=0,
    ),
    "puff_half": EnemySpec(
        name="Mycelium", kind="puff_half", max_hp=1, sight=400, biomes=(), size_px=26, xp=0,
    ),
    # M27: the plains boss -- More than Life, the necromancer, who rises
    # again as More than Death, the lich. His risen dead, his legion's
    # shields and his bone cage's ribs are bodies too.
    "necromancer": EnemySpec(
        name="More than Life", kind="necromancer", max_hp=8000, sight=400,
        biomes=(), size_px=64, xp=1200,
    ),
    "risen_dead": EnemySpec(
        name="risen dead", kind="chaser", sprite="risen_dead", scale=2,
        max_hp=30, sight=40, biomes=(), speed=4.6,
        damage=7, attack_radius=1.0, windup=0.3, cooldown=1.0, size_px=14, xp=1,
    ),
    "legion_shield": EnemySpec(
        name="shield skeleton", kind="legion_part", max_hp=40, sight=400, biomes=(),
        size_px=16, xp=0,
    ),
    "cage_rib": EnemySpec(
        name="bone rib", kind="myco_part", max_hp=25, sight=400, biomes=(), size_px=12, xp=0,
    ),
}

# M31.4: the great hunt's seven great beasts (design/OCEAN.md 27): the
# quest's targets, one at each of its spots (world/pangaea.Plan.hunt), out
# from the start of the run. Each is one of the island's own beasts grown old
# and huge, and named: the same behaviour (its kind's), never rolled.
# GREAT_BEASTS: (key, name, its kind's key, the ring it lives on: 2 the
# shore, 1 the middle, 0 the heart). GREAT: x max HP, x damage, + picture
# scale, x body size, + sight, x xp (mine). On top: ZONE_TOUGH, like any.
GREAT_BEASTS = (
    ("old_tusk", "Old Tusk", "mammoth", 2),
    ("broken_horn", "Broken Horn", "woolly_rhino", 2),
    ("long_fang", "Long Fang", "sabre_tooth", 2),
    ("thunderfoot", "Thunderfoot", "tyrant", 1),
    ("stoneback", "Stoneback", "club_tail", 1),
    ("glasswing", "Glasswing", "dragonfly", 0),
    ("deep_claw", "Deep Claw", "sea_scorpion", 0),
)
GREAT = (3.0, 1.25, 1, 1.25, 4, 6)
GREAT_APART = 50.0           # tiles between their spots, where the island has room
for _key, _name, _base, _ring in GREAT_BEASTS:
    _b = ENEMIES[_base]
    ENEMIES[_key] = replace(
        _b, name=_name, max_hp=round(_b.max_hp * GREAT[0]), damage=round(_b.damage * GREAT[1]),
        scale=_b.scale + GREAT[2], size_px=round(_b.size_px * GREAT[3]), sight=_b.sight + GREAT[4],
        xp=_b.xp * GREAT[5], biomes=(), weight=0, elite=True, group=(1, 1))
GREAT_KEYS = frozenset(k for k, *_ in GREAT_BEASTS)
# M31.5: what the first life evolves into last: a sabre-tooth cub (a small
# sabre-tooth) or a raptor (LIFE_BEASTS).
ENEMIES["sabre_cub"] = replace(ENEMIES["sabre_tooth"], name="sabre-tooth cub", scale=3,
                               max_hp=40, damage=10, size_px=22, sight=40, xp=6, biomes=(),
                               weight=0)

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

# M29.2: Paradise's enemies (ai/paradise.py; design/OCEAN.md 4).
# THE UNVEILING (user): serene first, each unveils on its own once it's hurt
# below UNVEIL[0] of its max HP or a hero comes within UNVEIL[1] tiles
# (mine: 5), after a tell of UNVEIL[2] s (mine: 0.6) that can't be stopped
# or undone. Serene, it moves at x UNVEIL[3] of its speed.
UNVEIL = (0.7, 5.0, 0.6, 0.45)
# The fonts (mine): an unveiled enemy under FONT[0] of its max HP goes to a
# blood font within FONT[1] tiles; within FONT[2] of its middle it drinks,
# healing FONT[3] x max HP a second until it's back to FONT[4]. It gives up
# on a font it hasn't reached in FONT[5] s.
FONT = (0.4, 30.0, 3.6, 0.06, 0.9, 12.0)
# Blood (user: unveiled angels bleed a trail and the stains stay): a stain
# every STAIN[0] tiles an unveiled enemy moves (a STAIN[1] chance), one by it
# for each hit it takes (chance STAIN[2]), and a pool where it dies (STAIN[3]
# tiles round, plus half its body's radius). Stained cloud stained again soaks (world/tiles.STAINS).
STAIN = (1.5, 0.6, 0.35, 1.3)
# The zones' toughness (OCEAN.md 2; numbers mine, from the user's "endgame
# tough"): enemies woken on a zone have x ZONE_TOUGH[0] max HP and x [1]
# damage, on top of the level scaling; packs are x [2] bigger and elites
# x [3] as likely.
ZONE_TOUGH = (2.5, 1.5, 4 / 3, 2.0)
# The landmarks on a zone that keep enemies off (LANDMARK_QUIET): the Gate
# where you land, the giver's stairway and the boss's court. The fonts,
# statues, choir rings and the cathedral are the angels' own.
ZONE_QUIET_MARKS = ("paradise_gate", "paradise_stairway", "paradise_court",
                    "pandemonium_pier", "pandemonium_hall",
                    "pangaea_skeleton", "pangaea_caves", "pangaea_caldera")
# --- M30.2: Pandemonium's trance (design/OCEAN.md 14; ai/pandemonium.py) ---------------
# The revellers live in groups (a table's, a bandstand's, the endless
# banquet's, the hall of mirrors'). A group frenzies as one -- the user's
# one-way frenzy -- once a hero comes within REVEL[0] tiles of any of them
# (x REVEL[1] where the music plays: a bandstand's group, and any within
# REVEL[2] tiles of a bandstand) or anyone hits one; a bandstand group's
# frenzy carries to every group within REVEL[2] tiles. The turn is a tell of
# REVEL[3] s (they freeze, heads snapping round); in the trance they move at
# x REVEL[4]. (Numbers mine, from OCEAN.md 14.) Frenzied, under FONT[0] of
# their max HP they go to drink at the wine fountains (FONT, like
# Paradise's blood fonts).
REVEL = (6.0, 0.5, 25.0, 0.6, 0.35)
# Who lives where (mine): REVEL_TABLE[0]-[1] feasters and drinkers at each
# banquet table (picked by REVEL_FEAST's weights), and a toastmaster at
# every REVEL_TABLE[2]-th table; at each bandstand its piper, REVEL_BAND[0]
# drummers, REVEL_BAND[1] pairs of dancers dancing round it and
# REVEL_BAND[2] masked dancers; REVEL_BANQUET[0] feasters along each side of
# the endless banquet's table and REVEL_BANQUET[1] toastmasters; in the hall
# of mirrors REVEL_MIRRORS[0] pairs of dancers and REVEL_MIRRORS[1] masked.
REVEL_TABLE = (4, 6, 3)
REVEL_FEAST = {"glutton": 2, "drunkard": 3, "ravenous": 2}
REVEL_BAND = (2, 2, 1)
REVEL_BANQUET = (7, 1)
REVEL_MIRRORS = (3, 2)
# TEMPTATION (user: the trance reaches you too). Within TEMPT[1] tiles of a
# banquet table, a bandstand or a wine fountain the meter (0..TEMPT[0])
# fills -- faster the closer: TEMPT[2] s from empty right next to one,
# nothing at TEMPT[1] -- and once clear of them it drains in TEMPT[3] s (x
# TEMPT[4] as fast while you're hitting something). Full, you're entranced
# for TEMPT[5] s: you drift toward the nearest lure at x TEMPT[6] of your
# speed and can't attack; a roll snaps you out. (Numbers mine.)
TEMPT = (100.0, 8.0, 6.0, 3.0, 2.0, 2.0, 0.55)
# The glutton: belly-slams when a hero is within GLUTTON[0] tiles (a ring
# GLUTTON[1] tiles out at GLUTTON[2] tiles/s); under GLUTTON[3] of its max
# HP, passing within GLUTTON[4] tiles of a banquet table, it stops GLUTTON[5]
# s to gorge, healing GLUTTON[6] x max HP; then not again for GLUTTON[7] s.
GLUTTON = (3.2, 5.5, 10.0, 0.85, 2.5, 1.2, 0.12, 6.0)
# The drunkard: weaves up to DRUNKARD[0] tiles to either side every
# DRUNKARD[1] s, keeping DRUNKARD[2]-[3] tiles away; its bottles fly
# DRUNKARD[4] s and shatter into a wine puddle DRUNKARD[5] tiles across that
# lasts DRUNKARD[6] s: it slows to x DRUNKARD[7] and fills DRUNKARD[8]
# temptation a second.
DRUNKARD = (1.3, 1.6, 4.0, 8.0, 0.9, 1.4, 6.0, 0.6, 12.0)
# The toastmaster: keeps TOAST[0]-[1] tiles away; a toast speeds every
# frenzied reveller within TOAST[2] tiles x TOAST[3] for TOAST[4] s, and a
# wave of wine rolls out TOAST[5] tiles at TOAST[6] tiles/s, adding TOAST[7]
# temptation to whoever it hits.
TOAST = (6.0, 9.0, 10.0, 1.5, 3.0, 7.0, 9.0, 18.0)
# The Ravenous: latched on, it bites every RAVENOUS[0] s and slows you to x
# RAVENOUS[1]; at most RAVENOUS[2] on a hero; a roll throws them off
# RAVENOUS[3] tiles, dazed RAVENOUS[4] s.
RAVENOUS = (0.6, 0.65, 3, 2.5, 1.2)
# The (revel) dancer's steps (they repeat): circling you DANCE_STEPS[0]
# tiles out for DANCE_STEPS[1] s one way, a dash through you (its line shows
# DANCE_STEPS[2] s, then DANCE_STEPS[3] s at DANCE_STEPS[4] tiles/s),
# circling back the other way, a dash.
DANCE_STEPS = (3.2, 1.1, 0.4, 0.45, 12.0)
# The masked dancer: swaps places with another dancer within MASKED[0]
# tiles, then a stab (its line shows MASKED[1] s) MASKED[2] tiles long at
# MASKED[3] tiles/s.
MASKED = (14.0, 0.35, 3.0, 14.0)
# A band drummer's beat: every BEAT[0] s a ring BEAT[1] tiles out at BEAT[2]
# tiles/s (roll through it on the beat).
BEAT = (1.25, 8.0, 12.0)
# The piper: keeps PIPER[0]-[1] tiles away; its song (a PIPER[2]-degree
# cone PIPER[3] tiles long) plays PIPER[4] s, rests PIPER[5] s, and fills
# PIPER[6] temptation a second; every PIPER[7] s it plays the frenzy on to
# the nearest group still in the trance within PIPER[8] tiles.
PIPER = (6.0, 10.0, 60.0, 9.0, 2.5, 2.0, 30.0, 6.0, 25.0)
# --- M30.3: the vain, the greedy and the demon hosts (OCEAN.md 15) ----------------------
# Who lives where (mine): the vanity statues are the vain's and the greedy's
# homes -- REVEL_STATUE[0] of the Vain admiring each and a hoarder counting
# coins; a gilded reveller posing as a second statue at every
# REVEL_STATUE[1]-th; at every REVEL_STATUE[2]-th the Beloved, with
# REVEL_STATUE[3] of the Vain admiring it (and the hall of mirrors has one
# too). The hosts guard the groups (OCEAN.md 14): a cupbearer at every
# REVEL_HOSTS[0]-th table, a carver at every [1]-th, a bouncer at every
# [2]-th, a master of revels at every [3]-th bandstand; at the endless
# banquet a bouncer by its west door and two carvers; a bouncer in the hall
# of mirrors.
REVEL_STATUE = (1, 2, 4, 3)
REVEL_HOSTS = (2, 3, 4, 2)
# The Vain: keeps VAIN[0]-[1] tiles away; every cooldown its mirror's cone
# (VAIN[2] degrees, VAIN[3] tiles: marked for its windup) flashes: whoever's
# in it is dazzled VAIN[4] s (their aim wavers up to VAIN[5] rad), and
# shots in it turn back at their shooter at x VAIN[6] damage.
VAIN = (5.0, 8.0, 50.0, 8.0, 2.0, 0.5, 0.6)
# The gilded reveller: a gold shell of GILDED[0] x its max HP soaks hits
# until it cracks off (then it moves x GILDED[4]); within GILDED[1] tiles it
# slams: a ring GILDED[2] tiles out at GILDED[3] tiles/s.
GILDED = (0.6, 2.2, 2.8, 8.0, 1.6)
# The hoarder: keeps HOARD[0]-[1] tiles away; a fistful is HOARD[2] coins in
# a HOARD[3]-degree spread, flying HOARD[4] s; where each lands it hurts,
# and coins lie HOARD[5] tiles round for HOARD[6] s: stepping on them, you
# stumble (x HOARD[7] for HOARD[8] s).
HOARD = (4.0, 7.0, 5, 50.0, 0.55, 0.6, 7.0, 0.15, 0.35)
# The Beloved: keeps BELOVED[0]-[1] tiles away; a fan of BELOVED[2] glitter
# shots over BELOVED[3] degrees every cooldown; its admirers (its group's
# Vain) circle it BELOVED[4] tiles out and take its hits while within
# BELOVED[5] tiles; while it lives its group moves x BELOVED[6].
BELOVED = (6.0, 9.0, 5, 40.0, 2.2, 4.0, 1.25)
# The cupbearer: goes to a frenzied reveller within CUPBEARER[0] tiles under
# CUPBEARER[1] of its max HP and pours CUPBEARER[2] s, healing it
# CUPBEARER[3] x its max (then not for CUPBEARER[4] s); otherwise keeps
# CUPBEARER[5]-[6] from you, throwing wine that adds CUPBEARER[7] temptation.
CUPBEARER = (10.0, 0.75, 1.0, 0.3, 4.0, 5.0, 8.0, 20.0)
# The carver: within CARVER[0] tiles a lunging cleave (CARVER[1] tiles at
# CARVER[2] tiles/s, its line shown for its windup); otherwise every cooldown
# a cleaver flies out CARVER[3] s at CARVER[4] tiles/s, curving CARVER[5]
# rad/s, then comes back to it.
CARVER = (3.5, 3.0, 12.0, 0.8, 9.0, 1.6)
# The bouncer: within BOUNCER[0] tiles it charges along a shown line
# (BOUNCER[1] tiles at BOUNCER[2] tiles/s); caught, you're thrown BOUNCER[3]
# tiles toward the nearest group still in the trance; a wall dazes it
# BOUNCER[4] s.
BOUNCER = (12.0, 10.0, 14.0, 6.0, 0.6)
# The master of revels: rings its bell (every MASTER[1] s): every group
# within MASTER[0] tiles frenzies, and every entranced hero there snaps out;
# keeps MASTER[2]-[3] away; fireworks: MASTER[4] circles MASTER[5] tiles
# across, marked MASTER[6] s, up to MASTER[7] tiles round you.
MASTER = (22.0, 10.0, 7.0, 10.0, 3, 1.5, 1.2, 2.5)

# M31.2: Pangaea's enemies (ai/pangaea.py; design/OCEAN.md 25-26, 28.3).
# THE ECHOES (user): ECHO[0] s after an enemy attacks, a faded echo plays
# the same attack again from the same spot at full damage; its tell shows
# again first, for as long as the attack's own windup (at least ECHO[1] s,
# at most [2]). Killing the enemy cancels its echoes; an echo never echoes;
# players and the land don't echo.
ECHO = (3.0, 0.35, 0.9)
# Which ring each is rolled on (world/pangaea.Plan.ring_at: 0 the heart, 1
# the middle, 2 the shore; mine, from the draft: mammals and hunters on the
# shore, dinosaurs in the middle, insects at the heart).
PANGAEA_RING_OF = {
    "mammoth": 2, "sabre_tooth": 2, "woolly_rhino": 2, "cave_bear": 2,
    "spear_hunter": 2, "trapper": 2, "fire_bearer": 2, "shaman": 2,
    "raptor": 1, "tyrant": 1, "club_tail": 1, "pterosaur": 1,          # (M31.3)
    "dragonfly": 0, "bombardier_beetle": 0, "ant_mound": 0,
}
# The mammoth (elite, herds): every MAMMOTH[0] s it trumpets (a [1] s
# windup, trunk up): a cone [2] degrees, [3] tiles, pushing [4] tiles (x [5]
# of its damage); then every mammoth of its herd within [6] tiles takes a
# lane -- parallel lanes [7] tiles apart, shown [8] s -- and they stampede
# along them at [9] tiles/s for [10] tiles. Close in, a tusk sweep (spec
# windup): a cone [11] degrees out to the spec's attack radius, pushing [12].
MAMMOTH = (8.0, 0.9, 70.0, 8.0, 3.0, 0.4, 16.0, 3.6, 1.1, 11.0, 18.0, 120.0, 1.5)
# The sabre-tooth: in tall ferns only its eyes show (still shootable). It
# stalks you at x SABRE[0] and pounces from [1]-[2] tiles: it crouches
# (spec windup; the line shows) and leaps at [3] tiles/s; caught, you're
# pinned -- bitten for [4] every [5] s -- until you roll free (or [6] s);
# thrown off, it's dazed [7] s.
SABRE = (0.6, 5.0, 11.0, 18.0, 9.0, 0.5, 3.0, 1.2)
# The woolly rhino: hits from within RHINO[0] degrees of its front do x [1].
# It scrapes (spec windup; its line shows) and charges at [2] tiles/s for [3]
# tiles, skids [4] s, then turns slowly ([5] rad/s) toward you; caught,
# you're tossed [6] tiles. A wall dazes it [7] s.
RHINO = (60.0, 0.25, 13.0, 14.0, 0.7, 1.3, 3.0, 1.2)
# The cave bear: it rears up (spec windup), swipes twice ([0] degrees out
# to the spec's attack radius, [1] s apart), and slams down [2] tiles ahead
# (radius [3], x [4] its damage); then it's open [5] s. Its roar (on first
# sight, then every [6] s) wakes every enemy within [7] tiles.
BEAR = (150.0, 0.35, 1.4, 2.6, 1.4, 1.2, 14.0, 18.0)
# The spear hunter keeps SPEAR[0]-[1] tiles off; a spear every spec cooldown
# (spec windup), leading you by x [2] of its flight; one that lands on open
# ground sticks there [3] s (a stake: it stops you, not shots).
SPEAR = (8.0, 13.0, 0.5, 4.0)
# The trapper keeps TRAPPER[0]-[1] off and lays a trap where it stands every
# [2] s (at most [3] laid, each lasting [4] s; [5] of them pits), [6] round
# its home to start with. A snare holds you [7] s; a pit drops you in for
# [8] s and hurts [9]; a roll carries you over both. Bolas every spec
# cooldown: tangled, x [10] for [11] s.
TRAPPER = (6.0, 11.0, 2.6, 5, 40.0, 0.4, 3, 1.0, 1.3, 18.0, 0.3, 1.8)
# The fire-bearer keeps FIREB[0]-[1] off; a torch every spec cooldown, lobbed
# ([2] s, marked where it lands): it bursts ([3] tiles) and sets the ferns
# alight (a blaze of [4] tiles at most). Close in, a torch swing (a cone [5]
# degrees). Every [6] s it beats: every beast within [7] tiles comes for
# you, x [8] as fast for [9] s.
FIREB = (5.0, 9.0, 0.9, 1.6, 40, 110.0, 7.0, 16.0, 1.4, 4.0)
# The shaman (elite) keeps SHAMAN[0]-[1] off; every spec cooldown it paints
# (spec windup; the spirit's line shows) a beast that comes alive and charges
# once along it, then fades: a mammoth spirit ([2] tiles/s, [3] across, [4]
# damage) or a sabre-tooth's ([5], [6], [7]), [8] tiles. While it lives no
# fire within [9] tiles of it burns out.
SHAMAN = (8.0, 13.0, 13.0, 1.4, 26.0, 19.0, 0.8, 18.0, 18.0, 12.0)
# Fire in the ferns (the land's: it doesn't echo). A burning tile burns
# FIRE[0] s (then it's scorched for good), every [1] s trying to light each
# of its neighbours that burns (PANGAEA_FLAMMABLE: the chance); standing in
# it burns [2] every [3] s (scaled like the land's other dangers; never the
# fire-bearer or the shaman). Fires [4] tiles from every hero go out. A lava
# bomb's splash lights [5] tiles at most.
FIRE = (6.0, 0.5, 6.0, 0.3, 70.0, 10)
# M31.3, the middle ring's dinosaurs. Raptors (packs) circle you RAPTOR[0]
# tiles out (x [1] their speed), then one at a time go round behind you,
# crouch (spec windup; the line shows) and leap through you at [2] tiles/s,
# [3] tiles past; the next goes [4] s after one lands; each waits [5] s
# (give or take) before its own next leap.
RAPTOR = (6.0, 0.8, 16.0, 3.0, 0.8, (2.5, 4.0))
# The Tyrant (elite): turns at most TYRANT[0] rad/s. Every [1] s it roars
# ([2] s windup): a cone [3] degrees, [4] tiles, x [5] of its damage, and
# whoever it catches is rooted in fear [6] s (a roll: it can't touch you).
# It bites what's ahead (a cone [7] degrees out to the spec's attack radius)
# and sweeps its tail at what's behind it (a cone [8] degrees, [9] tiles,
# throwing you [10]; a [11] s windup). Every [12] tiles it walks, the ground
# shakes: whoever's within [13] tiles stumbles (x [14] for [15] s; no harm).
TYRANT = (1.8, 9.0, 0.9, 70.0, 10.0, 0.3, 1.2, 60.0, 150.0, 4.2, 3.0, 0.6, 1.6, 3.5, 0.6, 0.35)
# The club-tail: hits from within CLUB[0] degrees of its head do full damage,
# anywhere else x [1]. It turns at most [2] rad/s: from afar it comes head
# first; within [3] tiles it turns its back to you and swings its tail (spec
# windup): a cone [4] degrees behind it out to the spec's attack radius,
# throwing you [5] tiles.
CLUB = (50.0, 0.2, 1.6, 5.0, 160.0, 4.5)
# The pterosaur (it flies): circles you PTERO[0] tiles out, swoops along a
# shown line (spec windup) at [1] tiles/s, [2] tiles past you; catching
# you, it carries you [3] tiles at [4] tiles/s and drops you (x [5] of its
# damage), then climbs away [6] s.
PTERO = (8.0, 15.0, 4.0, 4.0, 9.0, 0.6, 1.0)
# M31.3, the heart. Dragonflies (groups) hover (spec windup; the next dart's
# line shows), then dart DRAGONFLY[0] tiles at [1] tiles/s at a spot up to
# [2] tiles off you, turning sharply between darts.
DRAGONFLY = (7.0, 20.0, 1.5)
# The bombardier beetle comes to BEETLE[0] tiles, turns its back to you ([1]
# rad/s; [2] while it aims), and sprays (spec windup): a cone [3] degrees
# out of its back, [4] tiles. Get round to its front.
BEETLE = (4.5, 3.0, 1.0, 70.0, 5.0)
# The ant mound sends an ant every ANTS[0] s while it sees a hero (at most [1]
# of its own out): they march in a column, [2] tiles apart, the first at
# you at x [4] (the rest catch up). Hurt one, or the first reach you, and
# the whole column swarms you (x [3] as fast, biting). Collapse the mound
# and no more come.
ANTS = (0.9, 8, 1.1, 1.5, 0.8)
# The sea scorpion (elite) lives in the steaming pools (one in every
# SEA_SCORPION[0]th) and never leaves its pool. It grabs with its claws (spec
# windup; the line shows) out to [1] tiles: caught, you're dragged into the
# pool over [2] s and held there, scalding, until you roll (or [3] s). Every
# [4] s it stabs its tail spike at a marked spot up to [5] tiles off ([6] s
# marked, radius [7], x [8] of its damage).
SEA_SCORPION = (2, 3.2, 1.0, 2.5, 3.0, 6.0, 0.6, 1.2, 1.3)
# The steaming pools scald whoever stands in them (water walkers): PANGAEA_SCALD
# [0] every [1] s, scaled like the land's other dangers.
PANGAEA_SCALD = (5.0, 0.3)
# Nests (OCEAN.md 24): break an egg and NEST_HATCH[0] hatchlings come out of
# it ([1] out of each piece of a giant egg); the first egg broken calls the
# nest's parent, which comes from [2] tiles off, driven at you for [3] s:
# one of NEST_PARENTS by the seed (the great nest's: two pterosaurs).
NEST_HATCH = (2, 1, 18.0, 8.0)
NEST_PARENTS = {"tyrant": 1, "club_tail": 2, "raptor": 2}
# Amber: breaking into an outcrop frees what's in it, once an outcrop: loot
# AMBER_FREE[0] of the time (gems worth [1] in all, and a piece of gear [2]
# of those times), else a fight -- what was frozen in it, by the ring
# (AMBER_FIGHTS: (key, how many)).
AMBER_FREE = (0.4, 40.0, 0.35)
AMBER_FIGHTS = {0: (("dragonfly", 3), ("bombardier_beetle", 1)), 1: (("raptor", 2), ("hatchling", 4))}

# M31.4: THE ANCESTOR, form 1: the ages (design/OCEAN.md 28-28.1;
# ai/ancestor.py). Its three ages, a third of its health each (100-67-33%):
# the great mammal, the tyrant lizard, the giant insect. Everything it does
# echoes ECHO[0] s later (OCEAN.md 28), so its patterns are sparser than
# other tier III bosses' (its own, smaller combo chances). Numbers mine.
# Damages per hit at level 1 (x the enemy damage scaling, BOSS_DMG_MULT).
ANCESTOR_AGES = ("the great mammal", "the tyrant lizard", "the giant insect", "the first life")
ANCESTOR_HIT_RADIUS = (2.6, 2.6, 2.0)          # by age
ANCESTOR_COMBO = ((0.0, 0), (0.25, 1), (0.35, 1))
# Moving like its age (always moving; only the roar and the eruption plant
# it): the mammal gallops round you (speed, the round's radius, turning at
# most this many rad/s); the lizard stalks (speed, keeping this far, s
# between lunges, a lunge's tiles, its speed: a lunge only moves it); the
# insect flits and hovers (s hovering, flit speed, hovering this far from
# you, a flit at most this many tiles).
ANCESTOR_GALLOP = (7.0, 11.0, 2.4)
ANCESTOR_STALK = (2.8, 8.0, 2.6, 4.0, 14.0)
ANCESTOR_FLIT = (1.1, 16.0, 9.0, 10.0)
# A moult (at each third): MOULT[0] s bursting out of its skin (it can't be
# hurt meanwhile); the husk it leaves is cover (an oval of HUSK tiles, [1] x
# [2] tiles either way) and echoes one of the old age's attacks every [3] s
# (its tell [4] s), crumbling [5] s after the moult (OCEAN.md 28.3).
ANCESTOR_MOULT = (1.4, 2.6, 1.8, 5.0, 0.8, 20.0)
# Signature 1, the stampede (the mammal, then every age): it bellows [0] s,
# then the lanes of a spirit herd show [1] s across the caldera ([2] lanes,
# [3] tiles apart, a spirit [4] tiles either side of its lane's line: gaps
# of ~1.7 tiles to stand in), and the spirits run them at [5] tiles/s for
# [6] each (pushing [7] tiles), setting off within [8] s of each other.
ANCESTOR_STAMPEDE = (0.9, 1.4, 7, 5.0, 1.2, 12.0, 30, 2.5, 0.35)
ANCESTOR_STAMPEDE_REACH = 24.0     # a lane runs at most this far either side of your line
# Signature 2, the roar (the lizard on): [0] s shown, a cone [1] degrees
# wide, [2] tiles long; caught (unless mid-roll) you're rooted in fear [3]
# s and hit for [4]. It shakes the rim: rocks fall onto marked spots all
# over the caldera (ROCKS: how many, of them round each hero, s marked,
# radius, damage, within this far of you).
ANCESTOR_ROAR = (1.0, 100, 16.0, 1.2, 10)
ANCESTOR_ROCKS = (12, 3, 1.6, 1.6, 26, 5.0)
# Signature 3, the swarm (the insect): rivers of insects pour across the
# caldera ([0] of them, shown [1] s, stinging [2] s, [3] tiles either side
# of their line, drifting sideways at up to [4] tiles/s, swaying [5] tiles;
# [6] a sting, every [7] s you're in one).
ANCESTOR_SWARM = (3, 1.1, 5.0, 1.7, 1.4, 3.0, 9, 0.45)
# The moves, each its age's way. The charge along a marked line (per age:
# s shown, tiles, tiles/s, half-width -- at least its body's --, damage,
# push): tusks, a lunging bite
# (ending in a bite: BITE degrees, reach), a dive (it's in the air until it
# comes down the line).
ANCESTOR_CHARGE = ((0.9, 22.0, 16.0, 1.8, 34, 3.0), (0.7, 9.0, 18.0, 1.6, 30, 2.0),
                   (0.8, 14.0, 20.0, 1.4, 26, 1.5))
ANCESTOR_BITE = (70, 3.8)
# Spit fan (per age: shot, how many, spread degrees, s shown): bone shards,
# boiling spit, acid (PANGAEA_SHOTS).
ANCESTOR_SPIT = (("bone_shard", 7, 60, 0.7), ("boiling_spit", 5, 50, 0.7),
                 ("acid_spit", 9, 80, 0.7))
# The eruption: it stomps [0] s and lava bombs fall onto [1] marked circles
# round you (marked [2] s, radius [3], [4] damage, within [5] tiles of you).
ANCESTOR_ERUPTION = (0.8, 6, 1.6, 2.2, 26, 6.0)
# The sweep, behind it (per age: degrees, reach, damage, push, s shown): a
# hind kick, a tail sweep, a stinger. It backs up to you first (at most
# SWEEP_CLOSE[0] s at x[1] its speed).
ANCESTOR_SWEEP = ((140, 4.6, 30, 3.5, 0.7), (180, 6.0, 28, 4.0, 0.7), (100, 5.4, 32, 2.0, 0.6))
ANCESTOR_SWEEP_CLOSE = (1.0, 2.0)

# M31.5: THE ANCESTOR, form 2: the first life (design/OCEAN.md 28.2-28.3;
# ai/first_life.py). At 0 the giant insect's skin splits too (a third husk)
# and for FIRST_LIFE_RISE s it can't be hit while the caldera floods with
# the first sea, from the rim in (the lava lakes quench into rocks); then
# the first life, at full health (x FIRST_LIFE_HP: 14,000 of 12,000), with
# four phases (100-75-50-25%). Numbers mine; damages per hit at level 1.
FIRST_LIFE_HP = 14000 / 12000
DRAIN_PER_STEP = 600               # tiles of the first sea going back a step when it falls
FIRST_LIFE_RISE = 3.0
FIRST_LIFE_HIT_RADIUS = 3.0
# It swims round you, through everything (tiles/s in the deep, in the
# shallows; circling this far off; turning at most this many rad/s).
FIRST_LIFE_SWIM = (9.0, 5.5, 9.0, 2.2)
# The tide (OCEAN.md 28.2): [0] s low (shallows you walk), rising [1] s
# (the deep creeping in from the rim), [2] s high, falling [3] s; in the
# deep you wade at x[4] (a roll still carries you its full length).
TIDE = (8.0, 3.0, 6.0, 3.0, 0.5)
# The rocks that stand above it: a jittered grid ([0] tiles apart, jitter
# [1]) of round rocks [2] tiles in radius.
TIDE_ROCKS = (13.0, 3.5, (2.0, 3.6))
# Signature 1, life evolves (the whole form): every [0] s, [1] of the first
# life crawl out of the sea [2] tiles from you (at most [3] alive); left
# alone, each evolves after [4] s: a blob, then a crawler (LIFE_STAGES),
# then one of the island's beasts (LIFE_BEASTS).
LIFE_EVOLVE = (14.0, 2, (8.0, 16.0), 5, 8.0)
LIFE_STAGES = ("first_blob", "first_crawler")
LIFE_BEASTS = ("raptor", "sabre_cub")
# Signature 2, echoes of the ages (75%): the three husks wake as echoes
# (standing for the rest of the fight) and each replays its age's signature
# from where it lies every [0] s, a third of that apart, the first [1] s
# in: the mammal's stampede, the lizard's roar, the insect's swarm. Each
# echoes once, like everything (an echo never echoes).
HUSK_WAKE = (18.0, 2.0)
# Signature 3, tentacles (50%): [0] arms burst out of the sea on spots
# marked [1] s, [2]-[3] tiles from you (the burst [4] tiles round, [5]
# damage); then each sweeps an arc of [6] degrees, [7] tiles long, in [8] s:
# caught (unless mid-roll) you're held [9] s, squeezed [11] times for [10]
# (roll free).
TENTACLES = (3, 1.1, 4.0, 8.0, 1.4, 16, 110, 9.0, 0.8, 1.4, 10, 3)
# Signature 4, the tidal wave (25%): it rears up [0] s while the wave's
# front shows, [1] tiles before you; it rolls [2] tiles past you at [3]
# tiles/s, hitting for [4] and carrying you along [5] s (roll through it).
TIDAL_WAVE = (1.3, 16.0, 20.0, 12.0, 22, 0.9)
# Its moves. Dive and surface: it sinks [0] s, then its spot swells under
# you [1] s (following you the first [2] of them) and it bursts up: [3]
# tiles round for [4], and a ring of [5] spray shots.
DIVE = (0.6, 1.3, 0.6, 2.8, 26, 10)
# Whirlpool: on you, shown [0] s, spinning [1] s, [2] tiles round: it drags
# you round at [3] tiles/s and in at [4] (not mid-roll); in its eye ([5]
# tiles) it hurts [6] every [7] s.
WHIRLPOOL = (1.0, 3.5, 8.0, 5.0, 2.6, 1.6, 12, 0.5)
# Boiling bubbles: [0] chains of [1] through where you are (from [2] tiles
# off, a bubble every [3] tiles), shown [4] s, bursting [5] s apart down a
# chain ([6] tiles round, [7] damage).
BUBBLES = (3, 5, 7.0, 2.4, 0.9, 0.16, 1.6, 20)
# Arm lash: [0] arms fanned [1] degrees at you, [2] tiles long, shown [3] s,
# whipping out at [4] tiles/s ([5] tiles either side); caught (unless
# mid-roll) you're dragged in at [6] tiles/s to [7] tiles from it and
# bitten for [8] (roll free).
ARM_LASH = (3, 36, 14.0, 0.8, 30.0, 0.8, 10.0, 4.0, 26)
PANGAEA_FLAMMABLE = {"tall ferns": 0.55, "jungle ferns": 0.55, "fern meadow": 0.2,
                     "giant fern": 0.45, "cycad": 0.35, "trampled ferns": 0.3,
                     "horsetails": 0.35, "twigs": 0.5}
CHERUB = (7.0, 2.2, 3, 0.25, 14.0, 4.0, 4.0, 0.5, 5.0, 60.0, 1.5)
                             # serene: keeps this far, plinks every this many s a run of this
                             # many notes, s apart; unveiled: lunges at this speed for up to
                             # this many tiles; roars every this many s (this windup) when
                             # within this far, a cone this many degrees, pushing this far
SERAPH = (9.0, 3.0, 12, 7.0, 1.8, 0.12, 4, 0.35)
                             # serene: keeps this far, a ring of light every this many s of
                             # this many shots; unveiled: keeps this far, spins a spiral
                             # (every spec cooldown, after its windup) for this many s, a
                             # burst every this many s of this many shots, turning this much
OPHAN = (6, 1.0, 13.0, 2.2, 1.0, 0.8, 0.6, 4.0, 0.25)
                             # serene: a bump this hard every this many s; unveiled: races at
                             # this speed for this many s, then rests this long, hurting the
                             # same body at most every this many s; its slick slows to x this
                             # for this many s, a patch every this many s of racing
WATCHER = (2.6, 14.0, 50.0, 1.0, 0.3, 0.5)
                             # serene: an orb every this many s; unveiled: the gaze reaches
                             # this far, sweeps this many degrees over this many s; its aim
                             # line stops following you this many s before; the beam's
                             # half-width
LAMB = (14.0, 12.0, 1.0, 0.8, 5)
                             # unveiled: charges at this speed this far, dazed this long by
                             # what stops it, this long getting its footing back; serene: a
                             # butt this hard
DOVES = (5.0, 16.0, 1.0, (0.6, 1.6), 3, 0.25)
                             # unveiled: circle this far out, dive at this speed, climbing
                             # away this long, s between one dove's dive and the next;
                             # serene: a peck this hard; a dove's bleeding x this
LOCUSTS = (1.0, 2, 0.3)      # wobble (radians); serene: a sting this hard; bleeding x this
HALO = (2.6, 0.3, 4, 1.0, 0.3)  # unveiled: turns this many rad/s, saws every this many s;
                             # serene: a touch this hard every this many s; bleeding x this
# M29.3 (OCEAN.md 4): the heralds, the saints and the beasts.
TRUMPET = (9.0, 3.5, 6.0, 1.5, 4.0, 1.2, 10, 1.2, 1.0)
                             # keeps this far; serene: a long note every this many s pushes
                             # heroes within this far this far back; unveiled: each blast
                             # calls a plague over this many tiles round you, marked this many
                             # s, then this many strikes of fire and blood over this many s,
                             # each this wide
CENSER = (7.0, 1.2, 2, 0.8, 1.2, 3.0)
                             # unveiled: keeps this far; serene: a puff of harmless incense
                             # every this many s; unveiled: coals a throw, in the air this many
                             # s, landing this far apart, their fire lasting this many s
BOWL = (5.0, 1.0, 2.0, 6.0, 0.6, 0.5)
                             # unveiled: keeps this far; the pool it pours starts this wide,
                             # grows x(1 + this) over its life of this many s, slows to x
                             # this, hurts every this many s (the spec's damage)
CHORISTER = (6.0, 0.03, 3, 3, 16, 0.35)
                             # serene: its hymn heals angels within this far x this max HP a
                             # second; this many live at each choir ring; unveiled: shrieks
                             # this many rings of this many shots, this many s apart
SAINT = (8.0, 3, 0.9, 1.5, 1.2, 5.0, 0.7)
                             # unveiled: keeps this far; lobs this many tears a volley, in the
                             # air this many s, landing this far apart; each leaves a pool this
                             # wide for this many s that slows to x this
MARTYR = (10, 15, 5, 36.0, 7.0)
                             # arrows in it at first, at most (each hit from a hero sticks one
                             # more in); unveiled: throws this many a volley over this many
                             # degrees; keeps this far
BEHEMOTH = (15.0, 16.0, 3, 0.5, 1.6, 0.5, 60.0, 2.0)
                             # unveiled: charges at this speed this far, this many in a row,
                             # turning this many s between, dazed this long by what doesn't
                             # break; its bone plates take x this from within this many degrees
                             # of its front; a goring shoves this far
LEVIATHAN = (3, 2.0, 18.0, 3, 30.0, 1.0, 6.0)
                             # this many live along each river of blood; serene: swims this
                             # fast within this far of home; unveiled: surges (spec speed) to
                             # the stretch nearest you and spits this many in a fan this many
                             # degrees; bites what's on top of it every this many s; spits
                             # once it's within this far of that stretch

# P12 enemy behaviour (ai/mushroom.py; design/BOSSES.md 24.10).
POLLEN = (9.0, 2.5, 5.0, 0.04, 0.5)  # the shaman keeps this far; its cloud: radius, s,
                             # x max HP healed, every s (enemies only)
REGROW = (3.0, 0.04)         # the fungal brute regrows after this many s unhit, x max HP a s
ROOTS = (9.0, 12.0, 8.0, 0.8, 0.35, 0.8)  # the rootweaver keeps this far; roots run this far at
                             # this many tiles/s, a root every this far, bursting this many s
                             # after the crack reaches it, this wide
SNAIL = (0.5, 0.8, 0.5, 4.0)  # x damage to its shell (from behind); slime every this many s,
                             # slowing to x this, lasting this long
PILLBUG = (2.0, 9.0, 3.0, 0.2, 0.8)  # s resting; rolls at this speed for this long; x damage
                             # while rolled up; s before it hurts the same body again
MANTIS = (18.0, 0.35, 1.8, 0.15)  # leap speed; s with the scythes up; slash radius, s apart
FAIRY = (6, 2.5, 3, 2.5, 6)  # caps, ring radius; break this many to undo it; a sporeling every
                             # this many s while a hero is inside, at most this many about
MOLD = (3.0, 6, 5.0, 1.2, 3.0, 0.5)  # a patch every this many s, at most this many, within
                             # this far; its radius, damage, every s
MOLD_LIFE = 25.0             # s a mold patch lasts (it withers at once if the core breaks)

# P11 enemy behaviour (ai/swamp.py; design/BOSSES.md 24.9).
CROC = (14.0, 4.0, 1.4, 2.0, 0.33)   # lunge speed, tiles; clamp s, tiles it drags you, s between bites
TURTLE = (0.3, 2.0)          # retreats into its shell for every this share of max HP lost; s inside
HERON = (3.0, 2.0, 5.0)      # tiles it keeps; flaps off if you're this close; this far
HAG = (9.0, 1.3, 1.0, 1.0)   # tiles it keeps; its curse's radius, s it grows, s you're rooted
JAVELIN_STUCK = 4.0          # s a stuck javelin stands in the way
MARSH_LIGHTS = (3, 2.5)      # lights in a group (one real); tiles they drift apart
CORPSE_GAS = (2.4, 5.0, 4.0, 0.5)  # its cloud: radius, s it lingers, damage, every s

# P10 enemy behaviour (ai/ruins.py; design/BOSSES.md 24.8).
GARGOYLE = (8.0, 10.0, 16.0, 1.5)   # wakes within this far; dives this far at this speed; then
                             # this many s as stone (nothing hurts it)
CLOCK_SWEEP = (5, 60.0, 0.08)   # bolts in a sweep, over this many degrees, s apart
COLOSSUS_RING = (9.0, 7.0, 0.6)  # its stomp's ring: how far it rolls, tiles/s, how thick
CRAB_SHELL = (80, 6.0)       # the rubble shell's HP; how fast the bare crab runs
THIEF = (20.0, 0.8, 25.0, 12.0)  # looks for gems this far, scoops within this, gone once this far
                             # from every hero... after this many s running
SNIPER = (12.0, 16.0, 0.3)   # tiles it keeps; the line stops following you this many s before
FLAIL = (1.0, 3.0, 0.4, 7.0, 24, 1.0)  # ring from this radius to this while it winds up, hitting
                             # every this many s; then thrown this far for this much;
                             # s to pull it back
BLADE_ORBIT = 3.0            # tiles the haunted blades circle at
BELL = (8.0, 20.0, 6.0, 1.5, 9.0)  # rings every this many s: wakes enemies this far; heroes this
                             # close are knocked back this far; keeps this far from heroes

# P9 enemy behaviour (ai/desert.py; design/BOSSES.md 24.7).
FIRE_PATCH = (5.0, 0.5)      # burning ground (a straw golem's, a fire dancer's): damage, every s
HOP = (0.25, 0.35)           # a sand imp: s hopping, s still
SCORPION = (0.5, 2, 0.3, 0.6, 3.5)  # x damage to its front; pincer snaps, s apart; s the tail
                             # rises; tiles the stab reaches
VULTURE_HUNGRY = 0.5         # vultures dive only at heroes under this share of their HP
BASILISK = (1.0, 0.8, 7.0)   # s turned to stone; s between darts; tiles it keeps
SNAKE = (2.5, 14.0, 1.2)     # tiles a strike covers, its speed, s slithering off after
MUMMY = (12.0, 0.7, 1.5, 0.3, 1.6)  # pull speed, longest pull s, close enough, s to the blow,
                             # its radius
DANCER = (3.0, 1.2, 50.0, 4.0)  # tiles it closes to, s between fire patches, cone degrees,
                             # patch life s
RAIDER = (8.0, 1.5, 13.0, 0.25)  # tiles it waits at, s it waits, dash speed, s between slashes
TUMBLE_WIND = 0.35           # radians (east = 0) the wind rolls tumbleweeds, +- a little each
TUMBLE_EVERY = 1.0           # s before a tumbleweed hurts the same body again
CACTUS = (8, 0.5)            # spines all round per volley, s between volleys
LAMP = (6.0, 5.0, 2.2, 1.8, 0.8)  # tiles it keeps, vortex radius, pull tiles/s, zap reach,
                             # s between zaps

# P8 enemy behaviour (ai/forest.py; design/BOSSES.md 24.6).
BONE_REBUILD = 4.0           # s a skeleton's bone pile takes to pull itself back together
BAT_WOBBLE = 0.9             # radians a bat's line wobbles either way
BANSHEE = (5.0, 60.0, 2.5, 2.0)   # tiles it closes to, cone degrees, push tiles, s drifting off after
PHANTOM = (2.0, 1.0, 0.7, 1.0)    # s solid, s faded, how much its touch slows you, for this many s
DIGGER = (6.0, 2.5, 4, 7.0)  # digs every this many s, this far toward you, while fewer than this many
                             # skeletons are about; keeps this far from heroes
KNIGHT_COMBO = (3, 0.35)     # swings in a row, s between them
KNIGHT_HEAD = (1.6, 1.5, 1.5, 5.0)  # the floating head circles this far out; a hit on it does
                             # x this to the knight and staggers him this many s (at most
                             # once every this many s)
KNIGHT_HEAD_TURN = 1.5       # rad/s the head circles the knight
CENTIPEDE = (8, 0.7, 0.6)    # segments, tiles between them, how much its crawl wobbles (radians)
SPIDER_RANGE = (6.0, 10.0)   # tiles the giant spider keeps from its target...
SPIDER_EVERY = 2.6           # ...spitting a web this often
WEB = (1.2, 6.0, 0.45)       # a web patch's radius, s it lasts, how much it slows (speed x)
CULTIST = (5, 2.0, 5.0, 3, 10.0, (8.0, 12.0))   # candles, ring radius, a skeleton every this
                             # many s, at most this many, s before a new ring, range kept
CURSE_SPLIT = (4, 0.5, 9.0)  # a cursed orb splits into this many, x damage, their speed
WENDIGO_LUNGE = (5.0, 16.0, 0.3)  # tiles a lunge covers, its speed, s between the pair
WENDIGO_HOWL = (10.0, 9.0, 1.0, 0.6, 3.0)  # every this many s, within this far: rears up this
                             # long, then heroes are slowed to x this for this many s

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
    # T11 Arcane Mastery and T12 Weapons Master were cut in M28.1 (design/GEAR.md
    # section 8, user: "simplify" -- only "+damage" and "+elemental damage").
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
    # --- Boss uniques (M28.5; GEAR.md 21.2). unlock "U:<boss>": never offered. ---
    "tongue_lasher": CardSpec(
        "Tongue Lasher", "every 6th attack also lashes a tongue 7 tiles along the aim that pulls "
        "the first enemy hit to you", (("tongue_lasher", "flag", 1), ("tongue_lasher", "power", 7.0)),
        rarity="legendary", max_stacks=1, unlock="U:froggy", code="U01"),
    "bubble_belt": CardSpec(
        "Bubble Belt", "when hit, a bubble wraps you for 1 s: enemy shots bounce off it (once "
        "every 8 s)", (("bubble_belt", "flag", 1), ("bubble_belt", "power", 1.0)),
        rarity="legendary", max_stacks=1, unlock="U:froggy", code="U02"),
    "frogskin_boots": CardSpec(
        "Frogskin Boots", "your roll is a leap: 50% farther, landing with a splash that pushes "
        "enemies within 2 tiles away", (("frogskin_boots", "flag", 1), ("frogskin_boots", "power", 0.5)),
        rarity="legendary", max_stacks=1, unlock="U:froggy", code="U03"),
    "leechskin": CardSpec(
        "Leechskin", "a fifth of every hit you take is drunk back: it returns as HP over 5 s, "
        "unless you're hit again", (("leechskin", "flag", 1), ("leechskin", "power", 0.2)),
        rarity="legendary", max_stacks=1, unlock="U:leech_swarm", code="U04"),
    "latch_hood": CardSpec(
        "Latch Hood", "your hits latch: the 5th hit in a row on one enemy makes it bleed 3% of "
        "its max HP a second until it's out of your sight",
        (("latch_hood", "flag", 1), ("latch_hood", "power", 0.03)),
        rarity="legendary", max_stacks=1, unlock="U:leech_swarm", code="U05"),
    "bloated_charm": CardSpec(
        "Bloated Charm", "a leechling clings to the enemy you hit last, draining 2% of its max "
        "HP a second and healing you for half of that",
        (("bloated_charm", "flag", 1), ("bloated_charm", "power", 0.02)),
        rarity="legendary", max_stacks=1, unlock="U:leech_swarm", code="U06"),
    "proboscis_ring": CardSpec(
        "Proboscis Ring", "hits on bleeding enemies heal 1 HP (once per enemy a second)",
        (("proboscis_ring", "flag", 1), ("proboscis_ring", "power", 1.0)),
        rarity="legendary", max_stacks=1, unlock="U:proboscia", code="U07"),
    "engorged_mantle": CardSpec(
        "Engorged Mantle", "healing engorges you: +1% damage for every 5 HP healed, up to +30%; "
        "a hit taken bleeds it all out",
        (("engorged_mantle", "flag", 1), ("engorged_mantle", "power", 0.30)),
        rarity="legendary", max_stacks=1, unlock="U:proboscia", code="U08"),
    "dung_ball": CardSpec(
        "Dung Ball", "a ball rolls ahead of you (10 damage), growing with each enemy it flattens "
        "(+5 damage, +0.2 tiles, up to 3 tiles); it bursts on a wall and rolls anew after 4 s",
        (("dung_ball", "flag", 1), ("dung_ball", "power", 10.0)),
        rarity="legendary", max_stacks=1, unlock="U:khepri", code="U09"),
    "scarab_carapace": CardSpec(
        "Scarab Carapace", "hits from behind you do half damage (you can't be flanked)",
        (("scarab_carapace", "flag", 1), ("scarab_carapace", "power", 0.5)),
        rarity="legendary", max_stacks=1, unlock="U:khepri", code="U10"),
    "spittoon": CardSpec(
        "Spittoon", "every 4 s, spits a ricocheting glob (20 damage, bounces off walls 3 times) "
        "at the nearest enemy", (("spittoon", "flag", 1), ("spittoon", "power", 20.0)),
        rarity="legendary", max_stacks=1, unlock="U:ol_spitter", code="U11"),
    "hump_pack": CardSpec(
        "Hump Pack", "every 5th attack fires two extra shots behind you that bounce off walls once",
        (("hump_pack", "flag", 1), ("hump_pack", "power", 1.0)),
        rarity="legendary", max_stacks=1, unlock="U:ol_spitter", code="U12"),
    "hourglass_ring": CardSpec(
        "Hourglass Ring", "every 20 s, enemy shots within 6 tiles of you slow to a crawl for 2 s",
        (("hourglass_ring", "flag", 1), ("hourglass_ring", "power", 2.0)),
        rarity="legendary", max_stacks=1, unlock="U:nameless_magus", code="U13"),
    "sand_slippers": CardSpec(
        "Sand Slippers", "your roll raises a dune where it started: 3 tiles wide, it blocks "
        "shots for 2 s", (("sand_slippers", "flag", 1), ("sand_slippers", "power", 2.0)),
        rarity="legendary", max_stacks=1, unlock="U:nameless_magus", code="U14"),
    "lead_apron": CardSpec(
        "Lead Apron", "stand still 1 s and you take 40% less damage",
        (("lead_apron", "flag", 1), ("lead_apron", "power", 0.4)),
        rarity="legendary", max_stacks=1, unlock="U:fallout_king", code="U15"),
    "geiger_ring": CardSpec(
        "Geiger Ring", "enemies within 4 tiles of you take 1% of their max HP a second as rads "
        "(0.2% bosses)", (("geiger_ring", "flag", 1), ("geiger_ring", "power", 0.01)),
        rarity="legendary", max_stacks=1, unlock="U:fallout_king", code="U16"),
    "rod_of_fission": CardSpec(
        "Rod of Fission", "a rod planted where you stand pulses every 2 s: 10 damage within 3 "
        "tiles, and irradiated enemies take +10% damage for 3 s; replanted when you're 8 tiles "
        "away", (("rod_of_fission", "flag", 1), ("rod_of_fission", "power", 10.0)),
        rarity="legendary", max_stacks=1, unlock="U:fallout_king", code="U17"),
    "black_ice_crown": CardSpec(
        "Crown of Black Ice", "hits chill; chilled enemies leave black ice where they walk (3 s), "
        "and enemies on it are chilled too",
        (("black_ice_crown", "flag", 1), ("black_ice_crown", "power", 3.0)),
        rarity="legendary", max_stacks=1, unlock="U:snow_king", code="U18"),
    "hermits_furs": CardSpec(
        "Hermit's Furs", "stand still 2 s and frost gathers: the next enemy to hit you is frozen "
        "for 3 s", (("hermits_furs", "flag", 1), ("hermits_furs", "power", 3.0)),
        rarity="legendary", max_stacks=1, unlock="U:snow_king", code="U19"),
    "parasol": CardSpec(
        "Black Lace Parasol", "blocks enemy shots coming from in front of you (55 degrees either "
        "side of the aim) while you hold the attack",
        (("parasol", "flag", 1), ("parasol", "power", 55.0)),
        rarity="legendary", max_stacks=1, unlock="U:fragile", code="U20"),
    "mr_buttons": CardSpec(
        "Mr. Buttons", "the bear follows you; enemies would rather attack him (200 HP; he mends "
        "10 HP a second while nobody hits him, and stands up again 10 s after falling)",
        (("mr_buttons", "flag", 1), ("mr_buttons", "power", 200.0)),
        rarity="legendary", max_stacks=1, unlock="U:fragile", code="U21"),
    "bat_form": CardSpec(
        "Bat Form Boots", "your roll turns you into bats: you fly over everything, untouchable, "
        "50% farther", (("bat_form", "flag", 1), ("bat_form", "power", 0.5)),
        rarity="legendary", max_stacks=1, unlock="U:fragile", code="U22"),
    "shrinking_dust": CardSpec(
        "Shrinking Dust", "rolls shrink you for 2 s: +35% speed and a smaller body",
        (("shrinking_dust", "flag", 1), ("shrinking_dust", "power", 0.35)),
        rarity="legendary", max_stacks=1, unlock="U:nettle", code="U23"),
    "blight_thorn_ring": CardSpec(
        "Blightthorn Ring", "an enemy that hurts you is blighted: it takes +25% damage from "
        "everyone for 4 s", (("blight_thorn_ring", "flag", 1), ("blight_thorn_ring", "power", 0.25)),
        rarity="legendary", max_stacks=1, unlock="U:nettle", code="U24"),
    "cleaver_of_cuddles": CardSpec(
        "Cleaver of Cuddles", "a cleaver orbits you (15 damage), spinning faster with each kill "
        "(+5% a kill, up to x2; it slows back over 10 s)",
        (("cleaver_of_cuddles", "flag", 1), ("cleaver_of_cuddles", "power", 15.0)),
        rarity="legendary", max_stacks=1, unlock="U:love_cuddles", code="U25"),
    "acorn_bandolier": CardSpec(
        "Acorn Bandolier", "every 4th attack also lobs 3 acorns that burst where they land (8 "
        "damage within 1.5 tiles)", (("acorn_bandolier", "flag", 1), ("acorn_bandolier", "power", 8.0)),
        rarity="legendary", max_stacks=1, unlock="U:love_cuddles", code="U26"),
    "tripwire_boots": CardSpec(
        "Tripwire Boots", "your roll lays a tripwire along its path for 5 s: the first enemy to "
        "cross it is knocked down for 1.5 s",
        (("tripwire_boots", "flag", 1), ("tripwire_boots", "power", 1.5)),
        rarity="legendary", max_stacks=1, unlock="U:love_cuddles", code="U27"),
    "rootbound_boots": CardSpec(
        "Rootbound Boots", "stand still to root in and grow a shield (5 a second, up to 25% of "
        "max HP); walk on and it fades over 3 s",
        (("rootbound_boots", "flag", 1), ("rootbound_boots", "power", 5.0)),
        rarity="legendary", max_stacks=1, unlock="U:the_fallen", code="U28"),
    "heartwood_ring": CardSpec(
        "Heartwood Ring", "within 2 tiles of a tree you regain 2 HP a second",
        (("heartwood_ring", "flag", 1), ("heartwood_ring", "power", 2.0)),
        rarity="legendary", max_stacks=1, unlock="U:the_fallen", code="U29"),
    "mycelial_ring": CardSpec(
        "Mycelial Ring", "kills leave a spore patch (2 tiles, 5 s) that poisons",
        (("mycelial_ring", "flag", 1), ("mycelial_ring", "power", 5.0)),
        rarity="legendary", max_stacks=1, unlock="U:mycelium_amanita", code="U30"),
    "fly_agaric_cap": CardSpec(
        "Fly Agaric Cap", "hits have a 10% chance to trip the enemy: it wanders aimlessly for 2 s "
        "(a boss stumbles)", (("fly_agaric_cap", "flag", 1), ("fly_agaric_cap", "power", 0.10)),
        rarity="legendary", max_stacks=1, unlock="U:mycelium_amanita", code="U31"),
    "inkwell_charm": CardSpec(
        "Inkwell Charm", "every 5 s an ink blot falls on the nearest enemy: 15 damage, and it "
        "can't see you for 2 s", (("inkwell_charm", "flag", 1), ("inkwell_charm", "power", 15.0)),
        rarity="legendary", max_stacks=1, unlock="U:mycelium_inkcap", code="U32"),
    "lawyers_wig": CardSpec(
        "Lawyer's Wig", "hits scrawl on the enemy; the 5th scrawl binds it in ink: rooted 2 s "
        "(bosses 0.5 s)", (("lawyers_wig", "flag", 1), ("lawyers_wig", "power", 2.0)),
        rarity="legendary", max_stacks=1, unlock="U:mycelium_inkcap", code="U33"),
    "puffball_sandals": CardSpec(
        "Puffball Sandals", "your roll bursts a spore cloud where it started: 20 damage and "
        "poison within 2 tiles", (("puffball_sandals", "flag", 1), ("puffball_sandals", "power", 20.0)),
        rarity="legendary", max_stacks=1, unlock="U:mycelium_puffball", code="U34"),
    "spore_wind_band": CardSpec(
        "Spore Wind Band", "every 12 s a gust pushes enemies within 4 tiles 4 tiles away and "
        "makes their statuses last 2 s longer",
        (("spore_wind_band", "flag", 1), ("spore_wind_band", "power", 2.0)),
        rarity="legendary", max_stacks=1, unlock="U:mycelium_puffball", code="U35"),
    "phylactery": CardSpec(
        "Phylactery", "once a run, on death, you rise as a shade for 10 s (untouchable, half "
        "damage); kill 10 enemies to come back at 30% HP, or fall",
        (("phylactery", "flag", 1), ("phylactery", "power", 0.30)),
        rarity="legendary", max_stacks=1, unlock="U:necromancer", code="U36"),
    "lichs_gaze": CardSpec(
        "Lich's Gaze", "keep an enemy under your aim within 6 tiles for 1.5 s and it's marked: "
        "your next hit on it does x2", (("lichs_gaze", "flag", 1), ("lichs_gaze", "power", 2.0)),
        rarity="legendary", max_stacks=1, unlock="U:necromancer", code="U37"),
    "corpse_candle": CardSpec(
        "Corpse Candle", "every kill lights a candle at the body for 6 s: enemies in its light (2 "
        "tiles) burn 8 a second, and you heal 3 a second standing in it",
        (("corpse_candle", "flag", 1), ("corpse_candle", "power", 8.0)),
        rarity="legendary", max_stacks=1, unlock="U:necromancer", code="U38"),
    # M29.5: the Four Horsemen's (the Serene Cavalry's) relics, one per Horseman
    # (user's picks, 2026-11-22).
    "crown_of_conquest": CardSpec(
        "Crown of Conquest", "your hits crown enemies: a crowned enemy deals half damage for 4 s "
        "(bosses 25% less), once per enemy every 8 s",
        (("crown_of_conquest", "flag", 1), ("crown_of_conquest", "power", 4.0)),
        rarity="legendary", max_stacks=1, unlock="U:cavalry", code="U39"),
    "ring_of_blood": CardSpec(
        "Ring of Blood", "every 20 s, a ring of blood closes round you and the nearest elite or "
        "boss for 6 s: inside it you both deal double damage",
        (("ring_of_blood", "flag", 1), ("ring_of_blood", "power", 6.0)),
        rarity="legendary", max_stacks=1, unlock="U:cavalry", code="U40"),
    "black_scales": CardSpec(
        "The Black Scales", "every 8 s, weighs you against the nearest enemy: whichever has less "
        "health (as a share of max) loses 3% of its max HP to the other (bosses 0.5%)",
        (("black_scales", "flag", 1), ("black_scales", "power", 0.03)),
        rarity="legendary", max_stacks=1, unlock="U:cavalry", code="U41"),
    "pale_riders_cloak": CardSpec(
        "Pale Rider's Cloak", "enemies you kill rise once as pale shades that fight for you for "
        "6 s (at most 3 at a time)",
        (("pale_riders_cloak", "flag", 1), ("pale_riders_cloak", "power", 6.0)),
        rarity="legendary", max_stacks=1, unlock="U:cavalry", code="U42"),
    # M30.5: the Host of the Feast's relics, one per pleasure he plays on
    # (user's picks, 2026-11-23).
    "gluttons_bib": CardSpec(
        "Glutton's Bib", "your kills leave a scrap of the feast for 8 s: walk over it to eat it -- "
        "heal 3% of your max HP and +5% damage for 10 s (up to 5 at once)",
        (("gluttons_bib", "flag", 1), ("gluttons_bib", "power", 0.05)),
        rarity="legendary", max_stacks=1, unlock="U:host_of_feast", code="U43"),
    "hosts_goblet": CardSpec(
        "The Host's Goblet", "every 12 s you raise a toast: a wave of wine floods 8 tiles out (20 "
        "damage, a push) and the enemies it touches are drunk for 3 s: slowed 40%, missing 30% "
        "of their attacks", (("hosts_goblet", "flag", 1), ("hosts_goblet", "power", 20.0)),
        rarity="legendary", max_stacks=1, unlock="U:host_of_feast", code="U44"),
    "dancing_shoes": CardSpec(
        "Dancing Shoes", "your roll is a grand spin: as it ends it flings a ring of 8 pieces of "
        "cutlery (10 damage each) all round you",
        (("dancing_shoes", "flag", 1), ("dancing_shoes", "power", 10.0)),
        rarity="legendary", max_stacks=1, unlock="U:host_of_feast", code="U45"),
    "gilded_ring": CardSpec(
        "Gilded Ring", "hitting an elite or a boss tosses a coin out (every 6 s at most): catch it "
        "to be gilded, +25% damage for 4 s",
        (("gilded_ring", "flag", 1), ("gilded_ring", "power", 0.25)),
        rarity="legendary", max_stacks=1, unlock="U:host_of_feast", code="U46"),
    # M31.5: the Ancestor's relics, one per age and one for the first life
    # (user's picks, 2026-11-25).
    "spirit_herd": CardSpec(
        "Spirit Herd", "every 10 s (once an enemy is within 10 tiles) an ochre spirit mammoth "
        "charges from behind you along your aim: 30 damage to each enemy it runs through, "
        "pushing them aside", (("spirit_herd", "flag", 1), ("spirit_herd", "power", 30.0)),
        rarity="legendary", max_stacks=1, unlock="U:ancestor", code="U47"),
    "tyrant_skull": CardSpec(
        "Tyrant Skull", "every 15 s (once an enemy is within 6 tiles) you roar: enemies in a wide "
        "cone ahead take 20 and freeze in fear for 1.5 s (bosses 0.5 s)",
        (("tyrant_skull", "flag", 1), ("tyrant_skull", "power", 20.0)),
        rarity="legendary", max_stacks=1, unlock="U:ancestor", code="U48"),
    "swarm_ring": CardSpec(
        "Swarm Ring", "every 12 s a river of stinging insects pours from you along your aim for "
        "3 s: enemies in it take 6 every 0.5 s",
        (("swarm_ring", "flag", 1), ("swarm_ring", "power", 6.0)),
        rarity="legendary", max_stacks=1, unlock="U:ancestor", code="U49"),
    "echo_conch": CardSpec(
        "Echo Conch", "your attacks echo: 3 s after each one, a faded echo of it fires again from "
        "where you stood, at 40% damage",
        (("echo_conch", "flag", 1), ("echo_conch", "power", 0.4)),
        rarity="legendary", max_stacks=1, unlock="U:ancestor", code="U50"),
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

# --- Gear (players/gear.py; design/GEAR.md, M28.1) -----------------------------------
#
# The cards became gear (user, 2026-10-13/18). A hero starts a run with
# nothing worn and every level is one gear pick: GEAR_OFFER_SIZE pieces
# (CARD_OFFER_SIZE, kept for Fortune / Encore Tour), each a new piece for an
# empty slot, +1 to a piece you wear, or a swap for a full slot -- or
# UPGRADE: +1 to any worn piece instead. Swapped-out pieces go to the bag.
#
# Slots: one each of these, GEAR_RINGS rings, and as many trinkets as the
# hero's spell slots (SPELL_SLOTS, the Guild's Arcane Wing adds one).
GEAR_SLOTS = ("main", "off", "head", "chest", "feet", "ring", "trinket")
GEAR_SLOT_NAMES = {"main": "MAIN HAND", "off": "OFF-HAND", "head": "HEAD", "chest": "CHEST",
                   "feet": "FEET", "ring": "RING", "trinket": "TRINKET"}
GEAR_SLOT_SHORT = {"main": "M", "off": "O", "head": "H", "chest": "C", "feet": "F",
                   "ring": "R", "trinket": "T"}
GEAR_RINGS = 2
GEAR_MAX_LEVEL = 9
# Each +1 adds GEAR_LEVEL_GROWTH of the power's main number (a "mul" grows
# its distance from 1); a spell's first +4 are its own levels II-V, then
# GEAR_LEVEL_GROWTH of its SPELL_GROW number a level. Powers with no number
# grow GEAR_FLAT_GROWTH damage a level (bucket A). (GEAR.md 15.3)
GEAR_LEVEL_GROWTH = 0.10
GEAR_FLAT_GROWTH = 0.05
# Rarity makes the power stronger too (M28.3a, GEAR.md 7): the main number
# x GEAR_RARITY_POWER on top of the level's growth (they multiply); a power
# with no number gets GEAR_RARITY_FLAT of the rarity's extra as damage
# (legendary +50%); a spell's SPELL_GROW number grows by it, a radius by its
# square root (the area grows by it). A shrinking "mul" (Focus) goes no
# lower than GEAR_MUL_FLOOR. Trick numbers don't grow.
GEAR_RARITY_POWER = {"common": 1.0, "uncommon": 1.15, "rare": 1.3, "epic": 1.5, "legendary": 2.0}
GEAR_RARITY_FLAT = 0.5
GEAR_MUL_FLOOR = 0.1
SPELL_GROW = {"daggers": "damage", "ember_aura": "radius", "frost_nova": "damage",
              "spirit_wolf": "damage", "rune_trap": "damage", "poison_flask": "radius",
              "storm_cloud": "damage", "healing_totem": "heal", "ward_charm": "shield",
              "fire_wand": "damage", "bone_turret": "damage", "thorn_mail": "share",
              "chain_lightning": "damage", "split_arrow": "damage"}
# Affixes: the plain stat cards as lines on a piece, sized by the card's
# tier for the piece's rarity (fixed cards: their own value, only on pieces
# of their rarity or better). GEAR_AFFIXES lines by rarity; no two alike on
# one piece; across everything worn a stat counts at most its card's
# max_stacks lines. AFFIX_SLOTS: affixes that only roll in those slots.
AFFIXES = ("sharpened", "quick_hands", "iron_skin", "swift_boots", "long_reach", "keen_eye",
           "brutal", "broad_strokes", "lingering", "thick_hide", "nimble", "second_wind",
           "vampiric", "magnet", "scholar", "lucky_charm", "piercing", "potency", "quickened",
           "multishot", "affliction", "elementalist", "prospector", "quick_recovery",
           "extra_roll")
GEAR_AFFIXES = {"common": 0, "uncommon": 1, "rare": 2, "epic": 3, "legendary": 3}
AFFIX_SLOTS = {"quick_recovery": ("feet",), "extra_roll": ("feet",)}
# Offers: once GEAR_LEAN_FILLED slots are filled, swaps get x GEAR_SWAP_WEIGHT
# (user, N6: "more swaps than +1, since we have the upgrade button"). The
# run's first offer always holds a main-hand piece (N7).
GEAR_LEAN_FILLED = 6
GEAR_SWAP_WEIGHT = 1.5
GEAR_BAG = 3
# Salvage: loot = GEAR_SALVAGE[rarity] x (1 + GEAR_SALVAGE_LEVEL x level).
GEAR_SALVAGE = {"common": 20, "uncommon": 40, "rare": 80, "epic": 160, "legendary": 320}
GEAR_SALVAGE_LEVEL = 0.5
# Drops (M28.4a, GEAR.md 4.2): an elite's kill drops a piece ELITE_DROP of
# the time (seeded by the kill), rolled like an offer's new piece for the
# killer. A piece lies where it fell with its rarity's glow; a hero within
# GEAR_DROP_RADIUS tiles opens the pickup panel (wear / bag / salvage /
# leave); its name shows within GEAR_DROP_LABEL tiles; it's pinned on the
# maps once a hero came within GEAR_DROP_SEEN tiles.
ELITE_DROP = 0.15
GEAR_DROP_RADIUS = 1.4
GEAR_DROP_LABEL = 9.0
GEAR_DROP_SEEN = 26.0
# Chests (M28.4b, GEAR.md 4.2): CHESTS_PER_BIOME (low, high) per ring biome
# at scattered clearings (world/landmarks.py). CHEST_GUARDED of them are
# guarded: CHEST_GUARDS of one of CHEST_GUARD_KINDS[biome] stand round it
# (CHEST_GUARD_RING tiles out) and it opens once they're dead. CHEST_MIMIC
# of them are mimics (M28.4c): touched, an elite with teeth (ENEMIES
# "mimic") bites, and drops an epic or better piece when beaten. A hero
# within CHEST_RADIUS tiles opens one; its piece rolls with CHEST_LUCK
# extra luck. Chests are looked at within CHEST_LOOK tiles of a hero (their
# chunks are loaded) and pinned once one came within CHEST_SEEN.
CHESTS_PER_BIOME = (6, 8)
CHEST_GUARDED = 0.5
CHEST_MIMIC = 0.1
CHEST_GUARDS = 4
CHEST_GUARD_RING = 3.2
CHEST_GUARD_KINDS = {"forest": ("skeleton", "boar", "centipede"),
                     "desert": ("jackal", "sand_imp", "husk"),
                     "ruins": ("gnoll", "stone_imp", "lost_soldier"),
                     "swamp": ("bog_zombie", "newt", "lizardman"),
                     "mushroom": ("sporeling", "shroomling", "mold_zombie")}
CHEST_RADIUS = 1.9
CHEST_LUCK = 10
CHEST_LOOK = 40.0
CHEST_SEEN = 26.0
# The mimic (ai/mimic.py): it hops after you (MIMIC_HOP: s moving, s
# still), and, off cooldown (MIMIC_COOLDOWNS: lunge, tongue, spit):
#   lunges (MIMIC_LUNGE: tell s, tiles/s, tiles, x damage; a bite on
#   whatever it meets, once a lunge, stopped by walls);
#   lashes its tongue (MIMIC_TONGUE: tell s, reach tiles, tiles you're
#   dragged toward it, x damage) along a line that shows;
#   spits coins (MIMIC_SPIT: tell s, coins, fan degrees; WEAPONS
#   "mimic_coins") when you're MIMIC_SPIT_RANGE[0]..[1] tiles off.
MIMIC_HOP = (0.35, 0.3)
MIMIC_LUNGE = (0.55, 13.0, 6.0, 1.5)
MIMIC_TONGUE = (0.5, 7.0, 3.0, 0.6)
MIMIC_SPIT = (0.4, 3, 40.0)
MIMIC_SPIT_RANGE = (4.0, 12.0)
MIMIC_COOLDOWNS = (3.0, 4.5, 3.5)

# --- Boss uniques (M28.5; design/GEAR.md 21) ---------------------------------------
# A boss's relics: legendary-only pieces with a power of their own (a
# "power" mod holds the main number, +10% a level) and three fixed affixes
# (GEAR[key].affixes). One drops by the body when the boss falls, once a
# run per player (scenes/game.py _drop_unique); they're never offered.
# The swamp's (M28.5a):
U_TONGUE = (6, 0.9, 1.0)       # Tongue Lasher: every Nth attack; the line's half-width; a boss is pulled this far
U_BUBBLE = 8.0                 # Bubble Belt: s between bubbles (the bubble's length is the power)
U_FROGSKIN = (2.0, 1.5)        # Frogskin Boots: the splash's radius; how far it pushes
U_LEECHSKIN = 5.0              # Leechskin: s the drunk-back share of a hit returns over
U_LATCH = (5, 0.01, 0.5, 16.0) # Latch Hood: hits in a row; a boss's share a second; s between bleeds; "in sight" = within this many tiles, no wall between
U_BLOATED = (0.005, 0.5, 0.5)  # Bloated Charm: a boss's share a second; the share healed; s between bites
U_PROBOSCIS = 1.0              # Proboscis Ring: s between sips of one enemy
U_ENGORGED = 5.0               # Engorged Mantle: HP healed per +1% damage
# The desert's and the ruins' (M28.5b):
U_DUNG_BALL = (6.0, 0.6, 5.0, 0.2, 3.0, 0.4, 12.0, 4.0)   # tiles/s; radius at first; +damage and +radius a kill; the most radius; s between hits on one enemy; tiles it rolls before bursting; s before it rolls anew (the power: its damage)
U_SPITTOON = (4.0, 10.0, 3)    # s between globs; tiles it looks for an enemy; bounces (the power: the glob's damage)
U_HUMP_PACK = (5, 2, 0.12)     # every Nth attack; shots; radians either side of straight back (the power: x their damage)
U_HOURGLASS = (20.0, 6.0, 0.15)  # s between; tiles round you; shots crawl at x this (the power: s it lasts)
U_SAND_SLIPPERS = 3            # tiles wide (the power: s the dune stands)
U_LEAD_APRON = 1.0             # s standing still (the power: the share of damage not taken)
U_GEIGER = (4.0, 0.002, 0.5)   # tiles round you; a boss's share a second; s between ticks (the power: the share a second)
U_FISSION = (2.0, 3.0, 3.0, 0.10, 8.0)   # s between pulses; tiles; s irradiated; +damage taken; tiles off before it's replanted (the power: the pulse's damage)
U_BLACK_ICE = (0.5, 0.8, 1.0, 40)   # tiles a chilled enemy walks per patch; a patch's radius; s between its chills; most patches a hero has down (the oldest melt first) (the power: s a patch lasts)
U_HERMITS_FURS = (2.0, 0.5)    # s standing still; s a boss is frozen (the power: s the attacker is frozen)
U_PARASOL = 1.0                # (the power: degrees either side of the aim it blocks)
U_BUTTONS = (10.0, 1.0, 10.0, 1.5, 8.0)   # HP he mends a second; s since a hit before he mends; s down before he stands again; tiles behind you he keeps; px half-size (the power: his max HP)
U_BAT_FORM = 1.0               # (the power: the roll's extra distance, x)
# (M28.5c)
U_SHRINKING_DUST = (2.0, 0.6)  # s shrunk; x your body (the power: +speed)
U_BLIGHT_THORN = 4.0           # s blighted (the power: +damage it takes from heroes)
U_CLEAVER = (2.0, 2.5, 0.05, 2.0, 10.0, 0.5, 0.6)   # tiles out; rad/s; +spin a kill; the most x; s to slow back from the most; s between hits on one enemy; the blade's reach (tiles) (the power: its damage)
U_ACORNS = (4, 3, 6.0, 0.35, 1.5)   # every Nth attack; acorns; tiles out; rad between; burst radius (the power: their damage)
U_TRIPWIRE = (5.0, 0.5)        # s it lasts; s a boss is knocked down (the power: s knocked down)
U_ROOTBOUND = (0.25, 3.0)      # the most shield, x max HP; s it fades over once you walk (the power: shield a second)
U_HEARTWOOD = (2.0, 0.25)      # tiles from a tree; s between looks (the power: HP a second)
U_MYCELIAL = (2.0, 1.0)        # the patch's radius; s between its poisons (the power: s it lasts)
U_FLY_AGARIC = (2.0, 0.5, 4.0) # s wandering; s a boss stumbles; s before a boss can stumble again (the power: the chance)
U_INKWELL = (5.0, 2.0, 10.0)   # s between blots; s it can't see you; tiles it looks for an enemy (the power: the damage)
U_WIG = (5, 0.5)               # scrawls; s a boss is bound (the power: s bound)
U_PUFFBALL = 2.0               # the cloud's radius (the power: its damage)
U_SPORE_WIND = (12.0, 4.0, 4.0)   # s between gusts; tiles round you; tiles pushed (the power: s added to statuses)
U_PHYLACTERY = (10.0, 10, 0.5) # s as a shade; kills to come back; x your damage as a shade (the power: x max HP you come back with)
U_LICHS_GAZE = (6.0, 1.5, 0.5) # tiles; s under the aim; tiles off the aim line that still count (the power: x the next hit)
U_CANDLE = (6.0, 2.0, 3.0, 0.5, 12)   # s lit; tiles of light; HP a second healed; s between burns; most candles a hero (the power: burn a second)

# --- Tricks: +3 / +6 / +9 (players/gear.py; design/GEAR.md 17, M28.2) ---------------
# Each built piece's three tricks: (name, what it does), unlocked at +3, +6
# and +9 on top of the +10% a level. A worn piece at those levels gives the
# flags "<key>+3" / "+6" / "+9" (HeroStats.flags), which the game reads.
# Pieces not listed get their tricks in later M28.2 steps.
GEAR_TRICK_LEVELS = (3, 6, 9)
GEAR_TRICKS = {
    # M28.2a: the off-hand (GEAR.md 17.1).
    "cross_fire": (("Needle", "each cross turns 45 degrees from the last, so they alternate + and x"),
                   ("North star", "cross shots destroy the first enemy shot they touch"),
                   ("Cardinal", "the cross comes every 2nd attack")),
    "starburst": (("Pinwheel", "the burst's shots curve as they fly, sweeping like a pinwheel"),
                  ("Pain turns the wheel", "every hit you take counts as 2 attacks toward the next burst"),
                  ("Corona", "a second ring of 8 fires 0.3 s later, set between the first ring's shots")),
    "rear_guard": (("Over the shoulder", "the rear shot aims at the nearest enemy in your back half"),
                   ("Watchful", "an enemy within 2 tiles behind you is shot at once (once a second at most)"),
                   ("Eyes in the back", "the rear shot is a full copy of your attack at 100%")),
    "spiral": (("Growing shell", "the spiral shot grows as it flies: x2 size and +30% damage at the end of its range"),
               ("Double helix", "two spiral shots, turning opposite ways"),
               ("Golden angle", "the spiral turns 137.5 degrees a shot, +1 shot for every 3 enemies within 8 tiles (up to +3)")),
    "twin_lanes": (("Linked", "twins that hit two different enemies link them for 2 s: damage one takes, the other takes 25% of"),
                   ("Drift", "the twins drift apart as they fly, from 0.5 to 2 tiles"),
                   ("Triplets", "every shot flies as three lanes")),
    "echo": (("Reverb", "the echo goes at the nearest enemy that isn't the one you aimed at"),
             ("Rolling echo", "a kill by an echo brings the next echo 1 attack sooner"),
             ("Canyon", "every echo comes three times: the attack, its echo, and an echo of the echo at 60%")),
    "frenzy": (("Drumroll", "each kill during a frenzy adds 1 s to it (up to 6 s)"),
               ("Unshaken", "in a frenzy you can't be slowed or rooted"),
               ("War dance", "the -20% range is gone, and each frenzy starts with a drum beat that dazes enemies within 3 tiles for 0.5 s")),
    "spray_and_pray": (("Second barrel", "the halves split once more, at three-quarter range"),
                       ("Powder flash", "each split flashes: enemies within 1 tile of it take 30% of the shot"),
                       ("Buckshot", "the -25% range is gone, and each later piece of a shot that hits an enemy it already hit deals +25%")),
    # M28.2b: the head (GEAR.md 17.2).
    "kindling": (("Kindle", "your 4th hit in a row on one enemy always burns"),
                 ("Smoke", "burning enemies can't see you past 6 tiles: they stop shooting and walk closer"),
                 ("Pyre", "an enemy reaching 5 burn stacks burns twice as fast for 3 s")),
    "wildfire": (("Fanned flames", "your hits on a burning enemy restart its burn's clock"),
                 ("Heat haze", "burning enemies' shots fly 25% slower"),
                 ("Bonfire", "the bonus grows with the fire: +10% per burn stack (up to +50%) instead of +30%")),
    "venom": (("Fang", "your crits poison with 2 stacks"),
              ("Toxic blood", "an enemy that hits you takes 2 poison stacks"),
              ("Neurotoxin", "an enemy at 5 poison stacks is rooted for 1 s (once every 4 s; not bosses)")),
    "virulence": (("Incubation", "at 8 or more stacks, poison ticks 50% faster"),
                  ("Plague doctor", "toxic ground can't hurt you: toxic clouds, mold, the Fallout King's goo"),
                  ("Black death", "at 10 stacks, poison also takes 5% of the enemy's HP a second (1% for bosses)")),
    "frostbite": (("Cold snap", "your first hit on each enemy always chills"),
                  ("Hoarfrost", "frozen enemies can't be pushed and block enemy shots like a wall"),
                  ("Permafrost", "a frozen enemy chills every enemy touching it, 1 stack a second")),
    "shatter": (("Brittle", "chilled enemies (not frozen yet) take x1.15 from you"),
                ("Splinters", "the burst also throws 6 ice shards that fly 5 tiles and chill what they hit"),
                ("Shatterpoint", "hitting a frozen enemy shatters it: it takes the hit again and throws its shards")),
    "static": (("Build-up", "each hit on a shocked enemy adds +5% to its shock, up to +30% more"),
               ("Ground fault", "a shocked enemy standing in water, a bog or mud takes 20 a second"),
               ("Tempest", "an enemy shocked 3 times within 6 s is struck from the sky: 60 to it and all within 1.5 tiles")),
    "serrated": (("Rend", "the first time an enemy reaches 5 bleed stacks, it takes 40 at once"),
                 ("Open wounds", "bleeding enemies can't heal"),
                 ("Exsanguinate", "a bleeding enemy below 15% HP dies at once (a boss takes 200 instead, once every 10 s)")),
    "hemorrhage": (("Panic", "bleeding enemies below half HP run from you for 1 s (once each)"),
                   ("Spurt", "a bleeding enemy that dashes, leaps or charges takes its bleed x4 while it does"),
                   ("Bloodhound", "bleed ticks x3 while the enemy moves, and bleeding enemies show on your minimap")),
    "thermal_shock": (("Scald", "everything the burst hits gets 1 burn stack"),
                      ("Pressure", "the burst is 0.5 tiles wider for every burn stack it used"),
                      ("Geyser", "the burst no longer uses up the chill: an enemy can burst every 2 s while it burns and is chilled")),
    "toxic_current": (("Live wire", "the spread poison also shocks what it lands on"),
                      ("Battery", "each spread gives you a charge (up to 5); at 5, your next attack shocks everything it hits"),
                      ("Galvanize", "the poison spreads to every enemy within 3 tiles")),
    # M28.2c: the feet (GEAR.md 17.3).
    "riposte": (("Disarm", "the riposte hit cancels that enemy's next attack (a wind-up in progress stops)"),
                ("Second thrust", "the first two attacks after a roll crit, not one"),
                ("En garde", "a riposte crit that kills gives the roll charge back at once")),
    "slipstream": (("Draft", "while slipstreaming, bosses' bodies don't shove you and bumping enemies pass through you"),
                   ("Afterimage", "each roll leaves an image of you for 1 s; enemies attack it instead"),
                   ("Jet stream", "the slipstream lasts as long as you keep moving, ending 0.5 s after you stop")),
    "close_call": (("Graze", "each shot you roll through heals you 1 HP"),
                   ("Deflect", "shots you roll through fly back at whoever shot them, at 50% of their damage"),
                   ("Untouchable", "a roll through 5 or more shots keeps you untouchable 1 s after it ends")),
    "scorched_trail": (("Creeping fire", "each patch lights one more next to it, once, toward the nearest enemy"),
                       ("Bellows", "a roll across one of your old patches makes it flare: 30 to everything on it"),
                       ("Firewalk", "rolls go 50% farther and leave a solid line of fire, each patch lasting 5 s")),
    "momentum": (("Charge", "after 2 s of walking without stopping, your next attack deals +40%"),
                 ("Hoofbeats", "every 10 tiles you walk, the ground cracks under the nearest enemy within 6 tiles: 25 damage"),
                 ("Full gallop", "the bonus counts your whole move speed bonus, not half, and riding counts as +50%")),
    "fleet_strike": (("Quickstep", "each crit gives +10% move speed for 1 s (stacks to +30%)"),
                     ("Featherweight", "pushes and pulls on you are halved"),
                     ("Air step", "at +40% move speed or more you skim the ground: shockwaves, pools, stomps and other ground attacks miss you")),
    "blink": (("Displacement", "the spot you left gets a nova too, at 50%"),
              ("Swap", "blinking onto an enemy (landing within 1 tile of it) swaps you two"),
              ("Blink storm", "one roll can blink up to 3 times within 1 s, each with its nova, before the cooldown starts")),
    "shoulder_charge": (("Bowling", "an enemy shoved into another knocks it too: both take 25"),
                        ("Battering ram", "the charge breaks walls, trees and crates it runs into"),
                        ("Rampage", "each enemy the charge hits carries it 1 tile farther (up to +4)")),
    "backflip": (("Double flip", "a second fan comes as the roll ends"),
                 ("Quick draw", "backflip arrows have double your crit chance"),
                 ("Aerial", "while you roll and 0.5 s after, your bow fires twice as fast")),
    "pirouette": (("Encore spin", "a second, smaller ring (5 shots) comes as the roll ends"),
                  ("Dizzy", "enemies hit by the ring aim 90 degrees off with their next shot"),
                  ("Prima", "the ring has 1 more shot for every enemy within 5 tiles (up to 20)")),
    "drop_the_beat": (("Double drop", "the free beat also comes as the roll starts"),
                      ("Crowd surf", "each enemy you roll past adds +10% to the free beat (up to +50%)"),
                      ("Amplifier", "the free beat leaves an amp on the ground for 4 s; your beats go off from it too, at 60%")),
    # M28.2d: the chest (GEAR.md 17.4).
    "thorn_mail": (("Barbs", "an enemy your thorns hurt bleeds (1 stack)"),
                   ("Overgrowth", "stand still 1 s and a bramble ring grows round you (1.5 tiles): 10 a second to enemies in it"),
                   ("Wild hedge", "thorns also hurt every enemy within 2 tiles of the attacker")),
    "ward_charm": (("Static weave", "when the shield breaks, it shocks everything within 2 tiles"),
                   ("Overcharge", "while the shield is full, your attacks deal +15%"),
                   ("Second ward", "once the shield has been full for 3 s, a second layer (half its size) forms on top")),
    "heavy_plate": (("Tempered", "each hit the plate caps gives +1 armor for 5 s (up to +10)"),
                    ("Lighter steel", "the -15% move is gone"),
                    ("Anvil stance", "after standing still 0.5 s, hits are capped at 5% instead of 10%")),
    "glass_cannon": (("Crystal clear", "you see where enemy shots will go, a faint line 0.3 s ahead of each"),
                     ("Prism skin", "after 6 s without being hit, the next hit is blocked completely"),
                     ("Diamond", "the multiplier is x1.6 (not x1.4) while you haven't been hit for 5 s")),
    "retaliation": (("Recoil", "the shockwave also throws you 1 tile away from whoever hit you"),
                    ("Rising grudge", "each hit you take while it's cooling down adds +10 to the next shockwave (up to +50)"),
                    ("Seething", "no cooldown, but it only goes off on hits of 10 or more")),
    "untouched": (("Clean getaway", "dropping below 90% HP gives +30% move speed for 2 s"),
                  ("Dress code", "above 90% HP, you take 25% less from the ground: zones, stomps, eruptions, pools"),
                  ("Immaculate", "between 50% and 90% HP the bonus still counts, at half")),
    "berserker": (("Thick fur", "below 50% HP you take 10% less damage"),
                  ("Bloodrage", "below 30% HP you attack 30% faster"),
                  ("Last stand", "below 15% HP you can't drop under 1 HP for 3 s (once every 30 s)")),
    "bulwark": (("Fortify", "every 10 max HP above your hero's base also gives 0.1 HP a second"),
                ("Garrison", "within 2 tiles of a wall, you deal +20%"),
                ("Citadel", "your shield counts as max HP for the bonus")),
    "juggernaut": (("Glance", "enemy shots that hit you glance off 1% of the time per armor (up to 30%)"),
                   ("Tremor", "your steps shake the ground: 5 a second to enemies within 1.5 tiles while you walk"),
                   ("Peak", "armor counts twice for the damage bonus")),
    "aegis": (("Radiant", "while you have a shield, enemies within 1.5 tiles burn (1 stack a second)"),
              ("Corona burst", "when your shield breaks, it bursts for its full size as damage within 3 tiles"),
              ("Eternal day", "your shield slowly fills itself (2% of max HP a second) up to a quarter of your max HP")),
    "phoenix": (("Ashes", "rising leaves a ring of burning ground round you for 6 s"),
                ("Rebirth", "after rising you're untouchable for 2 s"),
                ("Undying flame", "you rise twice a run, not once")),
    # M28.2e: the rings (GEAR.md 17.5).
    "volatile": (("Big bang", "elites and bigger always explode"),
                 ("Short fuse", "each kill that doesn't explode adds +5% to the next one's chance (back to 15% on a bang)"),
                 ("Powder keg", "an explosion deals 40% of the killing hit plus 10% of the enemy's max HP")),
    "chain_reaction": (("Fuse line", "chain explosions go off 0.1 s apart, each +10% bigger than the last"),
                       ("Clean sweep", "a chain of 5 or more drops a gem worth 5 kills' XP"),
                       ("Domino effect", "an enemy hit by 2 explosions of one chain explodes too, dead or not")),
    "soul_harvest": (("Reap", "elite kills heal 10"),
                     ("Grim", "kills within 1 s of the last one heal double"),
                     ("Reaper", "kills heal 1% of your max HP if that's more than 1")),
    "surge": (("Rising", "the blast also deals 10 per level you have"),
              ("Ascend", "an UPGRADE pick sets off a surge too"),
              ("Apotheosis", "every 5th level also gives a free extra gear pick")),
    "bloodlust": (("Feeding frenzy", "a kill in one hit (an enemy at full HP) counts twice"),
                  ("Slow fade", "after the 10 s, the stacks fall off one a second instead of all at once"),
                  ("Apex", "the cap is +50%, and at the cap your hits make enemies bleed")),
    "giant_slayer": (("Long odds", "+1% more for every 100 HP the enemy has over you (up to +30% more)"),
                     ("Toppled giant", "a big enemy you kill drops a loot cache worth 5 kills"),
                     ("Goliath's bane", "against bosses the bonus is doubled (+80%)")),
    "veteran": (("Hard-won", "from level 20 on, each level counts twice"),
                ("Drilled", "every 10th level also gives a free UPGRADE (it doesn't cost the pick)"),
                ("Legend", "+1% max HP per level too")),
    "golden_hoard": (("Miser", "loot from salvaging gear counts double for the hoard"),
                     ("Golden armor", "every 500 loot of the hoard gives +1 armor (up to +10)"),
                     ("Dragon's hoard", "no cap")),
    "bounty": (("Big game", "a cache from an elite kill is worth double"),
               ("Hunter's pay", "a cache holds a piece of gear 10% of the time (it goes in your bag)"),
               ("Dead or alive", "the enemy speed-up is gone")),
    "beacon": (("Rally", "the extra enemies drop 50% more XP"),
               ("Moth to flame", "the extra enemies run straight at you, archers included"),
               ("Lighthouse", "every 60 s a wave comes for you; clear it within 20 s for a free gear pick")),
    "fortune": (("Clover", "one piece of every offer is rare or better"),
                ("Charmed", "+1 reroll for every 5 levels you gain"),
                ("Four leaves", "offers hold 5 pieces")),
    "overflow": (("Brim", "a crit on an enemy at full HP applies crit damage twice"),
                 ("Splash", "crits splash 25% of their damage onto enemies within 1 tile"),
                 ("Deluge", "each crit adds +2% crit damage for 5 s (up to +50%)")),
    "pandemic": (("Airborne", "the spread reaches enemies up to 5 tiles away"),
                 ("Mutation", "each spread adds 1 stack"),
                 ("Plague", "statuses spread while the enemy lives too, to 1 nearby every 3 s")),
    "pack_leader": (("Alpha", "your summons deal +25% to enemies you hit in the last 2 s"),
                    ("Loyal", "a turret whose time runs out stands again 3 s later, once"),
                    ("The pack", "+1 more wolf and turret; when you're hit, your wolves rush whoever hit you")),
    # Trinkets (M28.2f, GEAR.md 17.6): on top of the spell's levels.
    "chain_lightning": (("Grounding", "a bolt with nobody left to jump to strikes the ground: a 1.5-tile burst at 50%"),
                        ("Overload", "every 5th cast jumps twice as many times"),
                        ("Eternal arc", "bolts may jump back to an enemy they already hit, once each")),
    "daggers": (("Fling", "when you roll, the daggers shoot out along it and come back"),
                ("Breathing ring", "every 3 s the orbit swells to twice its width and back"),
                ("Blade storm", "+2 daggers, in two rings turning opposite ways")),
    "ember_aura": (("Warmth", "each pulse heals you 1 HP for every 5 enemies it burns"),
                   ("Flare-up", "every 5th pulse is a blast of 3 stacks"),
                   ("Sunfire", "the aura grows 0.2 tiles for every enemy burning in it (up to +2)")),
    "frost_nova": (("Cold heart", "when you're hit, the next nova comes 1 s sooner"),
                   ("Ice armor", "each nova gives you 5 shield for every enemy it chills (up to 25)"),
                   ("Avalanche", "every 3rd nova is twice as wide and freezes at once (not bosses)")),
    "spirit_wolf": (("Scent", "wolves go for the enemy you hit last"),
                    ("Howl", "every 10 s: enemies within 4 tiles of a wolf deal 20% less for 3 s"),
                    ("Dire wolves", "wolves twice as big, bite twice as hard, and make their prey bleed")),
    "rune_trap": (("Rune lines", "runes within 3 tiles link with a line; enemies crossing it take 10"),
                  ("Seeking runes", "runes drift toward the nearest enemy within 4 tiles"),
                  ("Runeburst", "when you roll, every rune bursts at once")),
    "poison_flask": (("Bubbling", "the pool grows 50% over its life"),
                     ("Witch's brew", "one flask in 4 is a random brew: fire, frost or shock"),
                     ("Cauldron", "pools that touch merge into one, lasting as long as the newest")),
    "storm_cloud": (("Downpour", "the cloud rains: the ground under it is a puddle"),
                    ("Thunderhead", "the cloud strikes whoever hit you last, first"),
                    ("Eye of the storm", "a second cloud circles you, striking 0.75 s after the first")),
    "healing_totem": (("Cleansing light", "stepping into its ring ends slows, stone, rads, ice and shrinking"),
                      ("Carried", "the totem follows you slowly instead of staying put"),
                      ("Tree of life", "the totem stays until the next one is planted")),
    "fire_wand": (("Glow", "an enemy hit by a bolt lights up: +10% crit chance against it for 2 s"),
                  ("Moth", "bolts go for burning enemies first"),
                  ("Will-o'-wisps", "every 5th bolt leaves a wisp for 3 s, burning all within 1.5 tiles")),
    "bone_turret": (("Ossuary", "turrets rise from the body of your last kill, not next to you"),
                    ("Calcify", "when a turret's time ends, it bursts into 8 bone shards (15 each)"),
                    ("Bone legion", "+1 turret at a time, and turrets stay until replaced")),
    # The wizard's main hand (M28.2g, GEAR.md 17.7).
    "storm_caller": (("Conducting darts", "a dart on an enemy your bolt hit in the last 2 s jumps on once, at 50%"),
                     ("Through walls", "lightning may jump to enemies out of sight"),
                     ("Thunderlord", "+1 jump; a bolt that jumps 5+ times strikes all it hit again, at 30%")),
    "conductor": (("Resistor", "the first jump doesn't fade at all"),
                  ("Overcurrent", "a jump to an enemy near the end of its reach deals +40%"),
                  ("Superconductor", "jumps never fade")),
    "supercell": (("Charged air", "your darts deal +10% to shocked enemies"),
                  ("Downdraft", "with 3+ shocked enemies within 5 tiles, Chain Lightning casts twice"),
                  ("Superstorm", "each bolt hit also shocks every enemy within 1.5 tiles of it")),
    "ball_lightning": (("Sticky", "the crackle clings to the enemy it hit and moves with it"),
                       ("Crackling chain", "every jump leaves a crackle, not just the first hit"),
                       ("Thunderball", "every 5th cast, a big ball rolls along the bolt's path for 3 s")),
    "phase_darts": (("Haunt", "a dart that went through a wall deals +25%"),
                    ("Spectral", "darts go through shields and armoured fronts"),
                    ("Ghost sight", "enemies behind walls show; darts with nothing near the aim go for them")),
    "seeker": (("Persistence", "a dart that loses its target flies 30% faster from then on"),
               ("Hunter-seeker", "darts go for the enemy with the least HP in reach"),
               ("Endless hunt", "a dart goes on to a new target after its hit: 3 hits (70% after the 1st)")),
    "resonance": (("Sustain", "the window is 2 s, not 1"),
                  ("Resonant ring", "at +60%, the enemy gives off a ring: 30 to all within 2 tiles (1 a s)"),
                  ("Perfect pitch", "the cap is +120%")),
    "implosion": (("Crush", "enemies dragged into each other take 10"),
                  ("Event horizon", "enemy shots within 1.5 tiles of the hit are dragged in too"),
                  ("Singularity", "every 6th cast's first hit opens a well that pulls for 1.5 s")),
    "arcane_storm": (("Squall", "the new dart goes for the enemy nearest to you"),
                     ("Tempest", "up to 5 new darts a cast"),
                     ("Maelstrom", "new darts fire new darts too, with no cap; each 80% of the last")),
    "orbiting_darts": (("Planets", "swinging darts hit the enemies they pass on the way round"),
                       ("Epicycle", "they try twice, not once"),
                       ("Gravity assist", "a dart that swung round you comes back 50% faster, +50% damage")),
    # The dwarf's and the huntress's main hands (M28.2h, GEAR.md 17.8).
    "ricochet": (("Bank shot", "each bounce adds +20% damage"),
                 ("Pinball", "axes also bounce off big enemies (elites, bosses), once a throw"),
                 ("Carom", "5 bounces, and after the last the axe flies straight home")),
    "hang_time": (("Saw", "each hit while hovering adds +10% to the next"),
                  ("Hold it there", "while you hold the attack, a hovering axe stays up to 2 s longer"),
                  ("Buzzsaw", "the hovering axe hits everything within 1.5 tiles")),
    "homeward_fury": (("Homing", "on the way back, the axe bends toward enemies within 2 tiles of its path"),
                      ("Welcome home", "each catch: +10% attack speed for 2 s (up to +30%)"),
                      ("Hearth", "the way back always crits")),
    "tether": (("Taut", "the chain deals 40% while its axe is near full range"),
               ("Shackle", "the first enemy the chain touches each throw is dragged with the axe for 0.5 s"),
               ("Flail", "the axe swings once round you on its chain before coming back")),
    "cyclone": (("Spin cycle", "the rethrow goes for the enemy with the most HP in reach"),
                ("Gale force", "up to twice a throw"),
                ("Eye of the cyclone", "each rethrow also throws a second axe at the next enemy")),
    "splitting_axe": (("Reunite", "pieces that meet on the way back become one axe, +30%"),
                      ("Crossing", "the halves cross over once on the way back, in an X"),
                      ("Quartering", "the axe splits into four quarters at 40% instead")),
    "arrow_rain": (("Monsoon", "the rain falls round the enemy nearest your aim"),
                   ("Thunder rain", "+20% to a rain arrow for each other one landing within 1 tile"),
                   ("Squall line", "every 5th shot rains twice, 0.4 s apart")),
    "broadhead": (("Gathering speed", "each enemy passed makes the arrow 10% faster"),
                  ("Run-through", "an arrow that passes 4+ enemies comes back once along its path"),
                  ("Broadside", "+30% per enemy passed, not 15%")),
    "hunters_mark": (("Old scent", "the last mark stays 2 s after the next one, so two are marked"),
                     ("Next quarry", "killing the mark marks the enemy nearest to where it fell"),
                     ("Pack hunt", "when the mark dies, enemies within 3 tiles of it are marked for 3 s")),
    "steady_aim": (("Held breath", "after 1 s still, your next arrow flies twice as fast"),
                   ("Zen", "after 2 s still, crits deal +50% crit damage"),
                   ("Still waters", "Steady Aim holds for 1 s after you start moving")),
    "deadeye": (("Follow-through", "a crit that pierces 3+ enemies makes your next arrow come at once"),
                ("Second sight", "every 6th arrow is a sure crit"),
                ("Lightning arrow", "crit arrows strike at once: no flight time")),
    "split_arrow": (("Canopy", "the split arrows go for the nearest enemies instead of a fan"),
                    ("Bough", "arrows split on walls too"),
                    ("Seed storm", "every split throws 3 seeds that sprout thorns for 2 s: 10 a s")),
    # The princess's and the bard's main hands (M28.2i, GEAR.md 17.9).
    "prism": (("Full spectrum", "a hit by every color of one shot is a crit"),
              ("Afterglow", "the bonus stays on the enemy 1 s, for your next shot"),
              ("Rainbow's end", "+30% for each other color")),
    "focus": (("Lens", "the middle color deals +25%"),
              ("Pinpoint", "the fan keeps narrowing while you stand still, down to half"),
              ("Beam", "after 1 s still, the fan is one beam of every color, through enemies")),
    "spectrum": (("Saturated", "each color's chance is 30%"),
                 ("Color theory", "enemies with 2 or more of your colors' statuses take +15%"),
                 ("Chromatic", "each color's hit gives its status twice")),
    "point_blank": (("Face to face", "within 2 tiles, +20% more on top"),
                    ("Duel", "the first enemy hit up close is your duelist: +25% from you, 25% less to you"),
                    ("Bladework", "point blank reaches 6 tiles and gives +60%")),
    "refraction": (("Shards of light", "the split pieces go for the nearest enemies"),
                   ("Radiant split", "split pieces are 50% bigger"),
                   ("Infinite mirror", "split pieces that hit split again into 2, up to 3 times")),
    "converge": (("Focal point", "enemies at the crossing take +40%"),
                 ("Second crossing", "after crossing, the colors curve back and cross again 3 tiles on"),
                 ("Lockstep", "the crossing follows the enemy nearest your aim")),
    "crescendo": (("Fermata", "a miss drops it one step instead of resetting"),
                  ("Climax", "at +50%, beats reach 25% farther"),
                  ("Forte", "the cap is +100%")),
    "lullaby": (("Lullabied", "an enemy hit by 5 beats in a row sleeps up to 3 s (bosses don't)"),
                ("Nothing wasted", "heal a beat can't give adds +4% per HP to the next beat"),
                ("Mother's song", "2 HP per enemy, up to 10")),
    "syncopation": (("Swing", "the loud beat comes 20% sooner after a soft one"),
                    ("Polyrhythm", "every 3rd beat is both at once"),
                    ("The drop", "the loud beat is x2.2")),
    "dissonance": (("Clash", "an enemy pushed into a wall takes 15"),
                   ("Tritone", "chilled enemies are pushed twice as far"),
                   ("Shriek", "beats chill twice (2 stacks)")),
    "grand_finale": (("Overture", "the first beat after 5 s without hitting anything is a finale"),
                     ("Curtain call", "dropping below 30% HP sets off a finale at once (every 20 s)"),
                     ("Magnum opus", "every 6th beat, not 8th")),
    "sheet_music": (("Birdsong", "notes curve round walls to their target"),
                    ("Chorus", "every 4th beat flings twice as many notes"),
                    ("Aria", "each note hits everything within 1 tile of where it lands")),
}
# A power's downside (its negative numbers) is gone from this level on.
GEAR_DROP_DOWNSIDE = {"frenzy": 9, "spray_and_pray": 9, "heavy_plate": 6}
# M28.3c: the legendary tricks (design/GEAR.md 19): a legendary piece's
# rule-breaker, on from +0 (flag "<key>+L"). Only the built ones are listed.
GEAR_LEGENDARY = {
    "overflow": ("Spillover", "when a crit kills, the damage left over hits the nearest enemy "
                              "within 3 tiles (it can crit and spill on)"),
    "pandemic": ("Miasma", "a dying enemy with statuses leaves a cloud for 4 s: enemies in it "
                           "catch them, 1 stack a second"),
    "pack_leader": ("In my image", "turrets fire a copy of your attack (50%); wolves bite for "
                                   "your attack's hit if that's more"),
    "juggernaut": ("Stoneskin", "a hit no bigger than half your armor does nothing"),
    "aegis": ("Daybreak", "healing while you're hurt also fills the shield, by half as much"),
    "phoenix": ("Ever-burning", "a used rise comes back after 150 kills"),
    "arcane_storm": ("Storm's mark", "an enemy your dart hit in the last 2 s fires a new dart "
                                     "when it dies, whatever killed it"),
    "cyclone": ("Dust devil", "at the end of each throw the axe leaps to the nearest enemy "
                              "within 5 tiles, then comes home"),
    "deadeye": ("Farsight", "the view leans toward your aim, and crit arrows fly on to the "
                            "edge of the screen"),
    "refraction": ("Prism ward", "your colors hit enemy shots, splitting them into 3 of "
                                 "your colors"),
    "grand_finale": ("Big finish", "each beat banks 20% of its damage; the finale adds the "
                                   "bank, shared over what it hits"),
    # M28.3d: the off-hand (GEAR.md 19.2).
    "cross_fire": ("Wind rose", "the cross also fires on its own every 1 s"),
    "starburst": ("Sunspot", "the burst rides the 10th attack: it goes off from the first "
                             "enemy that attack hits (or where it ends)"),
    "rear_guard": ("Flanking", "the rear shot starts 3 tiles past the enemy nearest your aim "
                               "and flies at its back"),
    "spiral": ("Spiral arm", "the spiral shot sweeps out round you in a widening spiral, "
                             "gone after 3 hits"),
    "twin_lanes": ("Perfect pair", "the twins are whole: 100% each"),
    "echo": ("Last word", "an enemy an echo kills dies twice: everything a kill sets off "
                          "happens twice"),
    "frenzy": ("Warpath", "a frenzy also runs your spells, summons and roll charges twice "
                          "as fast"),
    "spray_and_pray": ("Hair trigger", "each new attack splits every shot of yours still "
                                       "in flight, pieces too (down to eighths)"),
    # M28.3e: the head (GEAR.md 19.3).
    "kindling": ("Brushfire", "a burning enemy sets the ground it walks over alight (2 s)"),
    "wildfire": ("Radiant heat", "enemies within 2 tiles of a burning enemy count as "
                                 "burning for the bonus"),
    "venom": ("Venom sacs", "poison ticks can crit, with your crit chance and damage"),
    "virulence": ("Pestilence", "poison has no stack cap; past 10, each stack ticks at half"),
    "frostbite": ("Deep freeze", "bosses can freeze too: 10 chill stacks freeze one for "
                                 "0.5 s (once every 15 s)"),
    "shatter": ("Flash freeze", "an enemy that dies chilled shatters as if it were frozen"),
    "static": ("Short circuit", "every other hit a shocked enemy lands on you fizzles "
                                "(not bosses)"),
    "serrated": ("Bloodletting", "each bleed tick heals you 1 HP, up to 5 HP a second"),
    "hemorrhage": ("Blood rush", "your bleeds also tick x2 while YOU move"),
    "thermal_shock": ("Volatile mix", "any two statuses on an enemy set off the burst, "
                                      "using one of them up"),
    "toxic_current": ("Full current", "shocking spreads every status the enemy has, not "
                                      "just poison"),
    # M28.3f: the feet (GEAR.md 19.4).
    "riposte": ("Counterattack", "being hit readies a riposte too: your next attack crits "
                                 "(once every 2 s)"),
    "slipstream": ("Tailwind", "while slipstreaming, your move speed bonus is attack "
                               "speed too"),
    "close_call": ("Near miss", "a shot passing within 1 tile of you counts too, rolling "
                                "or not"),
    "scorched_trail": ("Fire wall", "enemy shots that cross your fire burn up"),
    "momentum": ("Iron hooves", "the bonus also cuts the damage you take, by as much "
                                "(up to 30%)"),
    "fleet_strike": ("Blur", "while you move, a hit that doesn't crit rolls for a crit "
                             "once more"),
    "blink": ("Mind's eye", "the blink goes where you aim (up to 8 tiles), not where "
                            "you're moving"),
    "shoulder_charge": ("Mountain mover", "bosses are shoved too (1 tile) and take double"),
    "backflip": ("Vault", "the roll carries you over walls, trees, water and enemies"),
    "pirouette": ("Ballet", "standing still 2 s spins the ring too, every 2 s you stay"),
    "drop_the_beat": ("Ground wave", "the free beat runs on along the roll's line as a "
                                     "wave, 5 tiles past its reach"),
    # M28.3g: the chest (GEAR.md 19.5).
    "thorn_mail": ("Bramble wall", "enemies within 1 tile take your thorns once a second, "
                                   "hit or not"),
    "ward_charm": ("Last thread", "the shield always takes a whole hit: one bigger than "
                                  "what's left is stopped, then it breaks"),
    "heavy_plate": ("Anvil", "you never lose more than 20% of your max HP in any one second"),
    "glass_cannon": ("Lightweight", "+1% move speed and +1% attack speed for each 1% of max "
                                    "HP the coat takes"),
    "retaliation": ("Long memory", "the shockwave also goes off round whoever hit you, "
                                   "wherever it is"),
    "untouched": ("Clean slate", "a kill below 90% HP heals you back to 90% (once every 10 s)"),
    "berserker": ("Scars", "healing doesn't take the bonus away at once: it falls 1% a second"),
    "bulwark": ("Ramparts", "every 25 max HP also gives 1 armor"),
    # M28.3h: the rings (GEAR.md 19.6).
    "volatile": ("Primed", "every 10th hit you land on one enemy makes it explode while it "
                           "lives (it takes the blast too)"),
    "chain_reaction": ("Firecracker", "an explosion that kills nothing jumps once to the "
                                      "nearest enemy within 3 tiles and goes off there"),
    "soul_harvest": ("Harvest", "every 10 kills give +1 max HP for the rest of the run"),
    "surge": ("Ascent", "a half surge at every quarter of the XP bar"),
    "bloodlust": ("Thirst", "damage to elites and bosses builds stacks: one for every 2% "
                            "of its max HP"),
    "giant_slayer": ("Outnumbered", "with 8 or more enemies within 6 tiles, the bonus counts "
                                    "against all of them"),
    "veteran": ("Battle-scarred", "drop below 25% HP and live 5 s: +2% damage for the run "
                                  "(once every 30 s)"),
    "golden_hoard": ("Old gold", "the Guild's purse counts too: +1% per 1000 loot in it"),
    "bounty": ("Wanted", "every 60 s the toughest enemy near you is wanted: kill it in 20 s "
                         "for a cache worth 25 kills"),
    "beacon": ("Bright beacon", "1 in 5 of the extra enemies comes as an elite"),
    "fortune": ("Foresight", "see your next offer early on the gear screen, and keep one of "
                             "its pieces through rerolls"),
    # M28.3i: the trinkets (GEAR.md 19.7).
    "chain_lightning": ("Conduit", "your crits also cast a bolt, from the enemy they hit (at "
                                   "most 3 a second)"),
    "daggers": ("Satellite", "the daggers circle the enemy you hit last (back to you when it "
                             "dies or after 3 s without a hit)"),
    "ember_aura": ("Afterburn", "when you roll, the aura stays behind for 3 s, burning on, and "
                                "a new one comes with you"),
    "frost_nova": ("Black ice", "the nova leaves its ring icy for 3 s: 1 chill stack a second "
                                "to enemies on it"),
    "spirit_wolf": ("Spirit pack", "wolves run through walls, trees and water"),
    "rune_trap": ("Rekindled", "a rune that bursts comes back 2 s later where it was, once"),
    "poison_flask": ("Lingering", "a pool stays as long as an enemy stands in it (up to 10 s)"),
    "storm_cloud": ("Storm front", "the cloud drifts ahead toward your aim, up to 5 tiles out, "
                                   "and strikes from there"),
    "healing_totem": ("Lifeline", "away from the totem you still get half its healing"),
    "fire_wand": ("Firefly", "a bolt that hits stays, buzzing round its enemy for 1.5 s and "
                             "burning it every 0.5 s"),
    "bone_turret": ("Walking dead", "turrets walk after the nearest enemy (1 tile a second)"),
    # M28.3j: the wizard's main hand (GEAR.md 19.8).
    "storm_caller": ("Forked lightning", "the first jump forks to the 2 nearest enemies, and each "
                                         "goes on with the rest of the jumps"),
    "conductor": ("Long line", "a jump with nobody in reach goes to the nearest enemy on "
                               "screen, however far"),
    "supercell": ("Ionized", "shocks from your bolts never wear off"),
    "ball_lightning": ("Static darts", "your darts crackle where they hit too (smaller, 1 s)"),
    "phase_darts": ("Possession", "a dart that kills raises the enemy's ghost, which fights for "
                                  "you for 5 s (not elites or bosses)"),
    "seeker": ("Relentless", "a dart with a target has no range: it flies on until it hits"),
    "resonance": ("Harmonics", "the count is shared: darts on enemies within 3 tiles of each "
                               "other count together"),
    "implosion": ("Gather", "the drag pulls toward where you aim, not toward the hit, so you "
                            "herd enemies to a point"),
    "orbiting_darts": ("Clockwork", "missed darts stay in orbit round you (up to 6) until an "
                                    "enemy comes within 4 tiles, then fly at it"),
    # M28.3k: the dwarf's and the huntress's main hands (GEAR.md 19.9).
    "ricochet": ("Trick shot", "a bounce goes toward the nearest enemy, not off at the mirror "
                               "angle"),
    "hang_time": ("Drifting saw", "the hovering axe drifts after the nearest enemy, 2 tiles a "
                                  "second"),
    "homeward_fury": ("Steered", "on the way back the axe flies through your aim point first, "
                                 "then on to you, so you steer the way back"),
    "tether": ("Chain gang", "every two axes in flight have a chain between them too"),
    "splitting_axe": ("Wide arc", "the halves swing out wide on the way home, 3 tiles to each "
                                  "side, sweeping all between"),
    "arrow_rain": ("Overcast", "where the rain fell it keeps raining for 3 s, 2 arrows a second"),
    "broadhead": ("Widening", "each enemy passed also makes the arrow 0.3 tiles wider"),
    "hunters_mark": ("Called shot", "a roll marks the enemy nearest your aim at once (it counts "
                                    "as the next mark)"),
    "steady_aim": ("Current", "moving in a straight line for 1 s counts as standing still"),
    "split_arrow": ("Recurve", "split arrows curve round after 3 tiles and come back toward you, "
                               "sweeping the way back"),
    # M28.3l: the princess's and the bard's main hands (GEAR.md 19.10).
    "prism": ("Overlap", "every hit of one shot counts, not just every colour: split pieces, "
                         "crossings and second passes add to the bonus"),
    "focus": ("Autofocus", "the fan narrows to a line when one enemy is in front of you and "
                           "opens up to its full width for a crowd"),
    "spectrum": ("Ultraviolet", "a sixth colour joins every shot: violet, which bleeds (20%)"),
    "point_blank": ("Lunge", "each attack carries you 0.5 tiles toward the enemy nearest your aim "
                             "(never into it)"),
    "converge": ("Burn-in", "the crossing point glows for 1.5 s; enemies there take 20% of the "
                            "shot every 0.25 s"),
    "crescendo": ("Tutti", "the crescendo counts for your spells and summons too"),
    "lullaby": ("Serenade", "enemies within twice the beat's reach count for the healing too, "
                            "hit or not"),
    "syncopation": ("Rubato", "you choose: holding the attack plays loud beats, letting go plays "
                              "soft ones"),
    "dissonance": ("Undertow", "every 3rd beat pulls enemies in instead of pushing them out (it "
                               "still chills)"),
    "sheet_music": ("Earworm", "each note that hits makes the enemy take +5% from your beats for "
                               "3 s (up to +25%)"),
}
SPILLOVER = 3.0              # Brimful Ring (L): tiles the leftover reaches
MIASMA = (0.75, 4.0, 1.0)    # Contagion Ring (L): the cloud's radius (1.5 wide), s, s a stack
IN_MY_IMAGE = 0.5            # Packmaster Ring (L): x a turret's copy of your attack
STONESKIN = 0.5              # Mountainhide (L): a hit up to this x your armor does nothing
DAYBREAK = 0.5               # Sunward Aegis (L): x healing (while hurt) that fills the shield
EVER_BURNING = 150           # Phoenix Mantle (L): kills for a used rise to come back
STORMS_MARK = 2.0            # Stormheart Staff (L): s a dart's hit marks an enemy
DUST_DEVIL = 5.0             # Whirlwind Axe (L): tiles from the axe's turn it leaps
FARSIGHT = (1 / 3, 0.35)     # Farsight Bow (L): most lean (x the view), x the way to the aim
                             # (the aim moves with the view: 0.35 settles at ~half the mouse's
                             # offset from the screen's middle)
PRISM_WARD = 3               # Kaleido Scepter (L): your colors an enemy shot splits into
BIG_FINISH = 0.2             # Showstopper Lute (L): x each beat's damage banked
WIND_ROSE = 1.0              # Compass Orb (L): s between the crosses it fires on its own
FLANKING = 3.0               # Hindsight Orb (L): tiles past the enemy the rear shot starts
SPIRAL_ARM = (1.0, 6.0, 1.5, 3)   # Nautilus Shell (L): the spiral's first and last radius
                             # (tiles), its turns, and the hits before it's gone
PERFECT_PAIR = 1.0           # Twinned Quiver (L): x damage each twin
LAST_WORD = 2                # Canyon Horn (L): times an echo's kill sets things off
WARPATH = 2.0                # War Drum (L): x the clocks of spells, summons, roll charges
HAIR_TRIGGER = 3             # Pepperbox (L): pieces of pieces split up to this deep (eighths)
BRUSHFIRE = 2.0              # Cinderveil Hood (L): s each burning tile lasts
RADIANT_HEAT = 2.0           # Blazecrown (L): tiles from a burning enemy that count as burning
PESTILENCE = 0.5             # Plaguebeak (L): x a poison stack past Virulence's 10
DEEP_FREEZE = (10, 0.5, 15.0)   # Rime Hood (L): chill stacks on a boss, s frozen, s between
SHORT_CIRCUIT = 2            # Stormvane Helm (L): every Nth hit of a shocked enemy fizzles
BLOODLETTING = (1.0, 5)      # Thornhelm (L): HP a bleed tick heals, most ticks a second
BLOOD_RUSH = 2.0             # Bloodtrail Cowl (L): x bleed ticks while you move
COUNTERATTACK = 2.0          # Fencer's Boots (L): s between riposte-readying hits
NEAR_MISS = 1.0              # Hairsbreadth (L): tiles from you a passing shot counts
IRON_HOOVES = 0.30           # Gallopers (L): the most the damage you take is cut
MINDS_EYE = 8.0              # Phasewalkers (L): the farthest an aimed blink goes
MOUNTAIN_MOVER = (1.0, 2.0)  # Ramhorn Boots (L): tiles a boss is shoved, x its damage
VAULT = 2.0                  # Tumbler Boots (L): tiles past the roll it may go to land clear
BALLET = 2.0                 # Dancing Slippers (L): s still for each ring
GROUND_WAVE = (5.0, 0.8, 30.0)   # Stompers (L): tiles the wave runs past the beat, half-width, tiles/s
BRAMBLE_WALL = (1.0, 1.0)    # Brambleguard (L): tiles from you, s between thorns
ANVIL = (0.20, 1.0)          # Anvil Plate (L): the most HP lost (x max HP) in this many s
CLEAN_SLATE = 10.0           # Spotless Tunic (L): s between heals to UNTOUCHED_HP
SCARS = 0.01                 # Wolfpelt (L): the bonus falls this much a second
RAMPARTS = 25                # Bastion Plate (L): max HP for each point of armor
PRIMED = 10                  # Powderkeg Ring (L): hits on one enemy for a live blast
FIRECRACKER = 3.0            # Domino Ring (L): tiles a blast that killed nothing jumps
REAPERS_HARVEST = 10         # Reaper's Band (L): kills for each +1 max HP
ASCENT = (4, 0.5)            # Ascendant Band (L): surges a level (the bar's quarters), x
THIRST = 0.02                # Fang Ring (L): a stack for each of this x an elite's max HP
OUTNUMBERED = (8, 6.0)       # Slingstone Ring (L): enemies, within tiles
BATTLE_SCARRED = (0.25, 5.0, 30.0, 0.02)   # Grizzled Signet (L): below x max HP, s to live,
                             # s between, + damage each
OLD_GOLD = 1000              # Hoarder's Ring (L): purse loot for each +1%
WANTED = (60.0, 20.0)        # Bountymark Ring (L): s between, s to kill it
BRIGHT_BEACON = 0.2          # Beckoning Ring (L): share of the extras that come as elites
CONDUIT = 3                  # Chainbolt Charm (L): the most bolts from crits a second
SATELLITE = (3.0, 0.25)      # Bladewheel Charm (L): s without a hit before the daggers come
                             # home; tiles out from the enemy's body they circle
AFTERBURN = 3.0              # Ember Amulet (L): s the aura left behind burns on
BLACK_ICE = (3.0, 1.0)       # Winterheart (L): s the ice lasts, s between its chill stacks
REKINDLED = 2.0              # Runestone Pouch (L): s before a burst rune comes back
LINGERING = (10.0, 0.5)      # Witch's Flask (L): the longest a pool lasts; s it stays once left
STORM_FRONT = (5.0, 8.0)     # Stormjar (L): tiles ahead at most, tiles/s the cloud drifts
LIFELINE = 0.5               # Mender's Totem (L): x the healing away from the totem
FIREFLY = (1.5, 0.5)         # Firefly Lantern (L): s a bolt stays, s between its burns
WALKING_DEAD = (1.0, 1.0)    # Skull Sentry (L): tiles/s a turret walks, tiles it stops short
# M28.3j: the wizard's main hand (GEAR.md 19.8).
FORKED_LIGHTNING = 2         # Stormcaller Rod (L): the first jump forks to this many enemies
STATIC_DARTS = (0.5, 1.0)    # Crackle Staff (L): x Ball Lightning's radius, s a dart's crackle lasts
POSSESSION = 5.0             # Ghostwood Staff (L): s a ghost fights for you
HARMONICS = 3.0              # Humming Staff (L): tiles apart enemies share the count
CLOCKWORK = (6, 4.0, 1.5, 3.0)   # Orrery Staff (L): darts kept at most, tiles an enemy comes
                             # within to set them off, the orbit's radius (tiles), rad/s round you
# M28.3k: the dwarf's and the huntress's main hands (GEAR.md 19.9).
DRIFTING_SAW = 2.0           # Hoverhead Axe (L): tiles/s the hovering axe drifts
STEERED = 0.6                # Homesick Axe (L): tiles from the aim point that count as through it
WIDE_ARC = 3.0               # Doublebit Axe (L): tiles to each side the halves swing out
OVERCAST = (3.0, 2.0)        # Cloudburst Bow (L): s it keeps raining, arrows a second
WIDENING = 0.3               # Broadleaf Bow (L): tiles wider for each enemy passed
STILL_CURRENT = (1.0, 10.0)  # Stillwater Bow (L): s in a straight line, degrees it may waver
RECURVE = (3.0, 30.0, 0.8)   # Splitbranch Bow (L): tiles out, rad/s it turns, tiles from you it ends
# M28.3l: the princess's and the bard's main hands (GEAR.md 19.10).
AUTOFOCUS = (3, 30.0)        # Spyglass Wand (L): enemies in front for the full fan, degrees
                             # either side of the aim that count as in front
LUNGE = (0.5, 0.2)           # Duelist's Wand (L): tiles an attack carries you, tiles kept off its body
BURN_IN = (1.5, 0.25, 0.20)  # Crossbeam Wand (L): s it glows, s a tick, x the shot's damage
SERENADE = 2.0               # Cradlesong Lute (L): x the beat's reach that counts for the heal
UNDERTOW = 3                 # Sourstring Lute (L): every Nth beat pulls
EARWORM = (0.05, 3.0, 5)     # Songbird Lute (L): + damage from your beats a note, s, notes at most
# The off-hand tricks' numbers.
NEEDLE_TURN = 45.0           # Compass Orb +3: degrees each cross turns from the last
CARDINAL_EVERY = 2           # Compass Orb +9: the cross every Nth attack
NORTH_STAR_RADIUS = 0.45     # Compass Orb +6: how close an enemy shot must come to be cut
PINWHEEL_TURN = 0.09         # Sunwheel +3: radians the burst's shots turn per tile flown
PAIN_WHEEL = 2               # Sunwheel +6: attacks each hit you take counts as
CORONA = 0.3                 # Sunwheel +9: s before the second ring
WATCHFUL = (2.0, 1.0)        # Hindsight Orb +6: tiles behind you, s between shots
GROWING_SHELL = (0.35, 0.30)  # Nautilus Shell +3: tiles of hit radius added, +damage, at full range
GOLDEN_ANGLE = 137.5         # Nautilus Shell +9
GOLDEN_EXTRA = (3, 8.0, 3)   # ...+1 shot per this many enemies within this many tiles, up to
LINKED = (2.0, 0.25)         # Twinned Quiver +3: s a link lasts, share of the damage passed on
DRIFT_APART = 2.0            # Twinned Quiver +6: tiles between the twins at the end of their range
ECHO_THIRD = 0.6             # Canyon Horn +9: x damage of the echo's echo
DRUMROLL = (1.0, 6.0)        # War Drum +3: s a kill adds, most s
WAR_DANCE = (3.0, 0.5)       # War Drum +9: daze radius (tiles), s
POWDER_FLASH = (1.0, 0.30)   # Pepperbox +6: radius, x the shot's damage
BUCKSHOT = 0.25              # Pepperbox +9: + damage of a later piece on an enemy already hit
# The head tricks' numbers (M28.2b).
KINDLE = 4                   # Cinderveil Hood +3: the Nth hit in a row on one enemy burns
SMOKE = 6.0                  # Cinderveil Hood +6: tiles a burning enemy can still see you
PYRE = (2.0, 3.0)            # Cinderveil Hood +9: x burn speed, s
HEAT_HAZE = 0.75             # Blazecrown +6: x speed of a burning enemy's shots
BONFIRE = (0.10, 0.50)       # Blazecrown +9: bonus per burn stack, most (at +0; they grow with Wildfire's +10%)
FANG = 2                     # Viper Mask +3: poison stacks a crit puts on
TOXIC_BLOOD = 2              # Viper Mask +6: poison stacks on an enemy that hits you
NEUROTOXIN = (5, 1.0, 4.0)   # Viper Mask +9: poison stacks, s rooted, s before it can be again
INCUBATION = (8, 1.5)        # Plaguebeak +3: poison stacks, x tick speed
PLAGUE_DOCTOR = ("gas", "mold")   # Plaguebeak +6: enemy zones that can't hurt you (and goo)
BLACK_DEATH = (10, 0.05, 0.01)   # Plaguebeak +9: poison stacks, x current HP a second (bosses)
PERMAFROST = (1.0, 0.15)     # Rime Hood +9: s between chills, tiles of gap that count as touching
BRITTLE = 1.15               # Glassfrost Helm +3: x damage on chilled (not frozen) enemies
SPLINTERS = (6, 5.0)         # Glassfrost Helm +6: shards, tiles they fly (damage: SHATTER[2])
ICE_SHARD_SHOT = ShellSpec(speed=14.0, damage=15, max_range=5.0, damages_terrain=False,
                           look="shard", sound="fizzle")
BUILD_UP = (0.05, 0.30)      # Stormvane Helm +3: + shock a hit, most
GROUND_FAULT = 20.0          # Stormvane Helm +6: damage a second (x your status strength)
WET_TILES = ("water", "bog", "pond", "mud", "reeds", "lily pads", "scum", "stagnant water",
             "blood pool", "clots", "oasis")
TEMPEST = (3, 6.0, 60, 1.5)  # Stormvane Helm +9: shocks, within s; damage, radius
REND = (5, 40)               # Thornhelm +3: bleed stacks, damage (x your status strength)
EXSANGUINATE = (0.15, 200, 10.0)  # Thornhelm +9: HP fraction; a boss's damage, s between
PANIC = (0.5, 1.0)           # Bloodtrail Cowl +3: HP fraction, s it runs
SPURT = (4.0, 1.6)           # Bloodtrail Cowl +6: x bleed; moving faster than x its walk is a dash
BLOODHOUND = 3.0             # Bloodtrail Cowl +9: x bleed while moving (not x2)
SCALD = 1                    # Steamcrown +3: burn stacks
PRESSURE = 0.5               # Steamcrown +6: tiles wider per burn stack
GEYSER = 2.0                 # Steamcrown +9: s between one enemy's bursts
BATTERY = 5                  # Galvanic Mask +6: charges for a shocking attack
GALVANIZE = 3.0              # Galvanic Mask +9: tiles
# The feet tricks' numbers (M28.2c).
DISARM = 3.0                 # Fencer's Boots +3: s a disarmed enemy waits to waste its next attack
SECOND_THRUST = 2            # Fencer's Boots +6: sure crits after a roll
AFTERIMAGE = 1.0             # Windrunners +6: s the image lasts
JET_STREAM = 0.5             # Windrunners +9: s the slipstream lasts after you stop
GRAZE = 1.0                  # Hairsbreadth +3: HP per shot rolled through
DEFLECT = 0.5                # Hairsbreadth +6: x a deflected shot's damage
UNTOUCHABLE = (5, 1.0)       # Hairsbreadth +9: shots in one roll, s untouchable after it
CREEPING_FIRE = (0.5, 8.0)   # Ashwalkers +3: s before a patch creeps, tiles it looks for an enemy
BELLOWS = 30.0               # Ashwalkers +6: damage of a flare
FIREWALK = (1.5, 5.0)        # Ashwalkers +9: x roll distance, s each patch lasts
CHARGE = (2.0, 0.40)         # Gallopers +3: s of walking, + damage of the next attack
HOOFBEATS = (10.0, 6.0, 25.0)   # Gallopers +6: tiles walked, reach, damage
FULL_GALLOP = 0.5            # Gallopers +9: move bonus a mount counts as
QUICKSTEP = (0.10, 1.0, 3)   # Wingheel +3: + move speed a crit, s, most stacks
FEATHERWEIGHT = 0.5          # Wingheel +6: x pushes and pulls on you
AIR_STEP = 0.40              # Wingheel +9: move speed bonus needed
DISPLACEMENT = 0.5           # Phasewalkers +3: x the nova at the spot you left
SWAP = 1.0                   # Phasewalkers +6: tiles from the landing an enemy is swapped from
BLINK_STORM = (3, 1.0)       # Phasewalkers +9: blinks in a roll, s to use them
BOWLING = 25.0               # Ramhorn Boots +3: damage to both
BATTERING_RAM = 10000.0      # Ramhorn Boots +6: damage the charge does to what it runs into
RAMPAGE = (1.0, 4)           # Ramhorn Boots +9: tiles per enemy hit, most
QUICK_DRAW = 2.0             # Tumbler Boots +6: x crit chance of backflip arrows
AERIAL = (2.0, 0.5)          # Tumbler Boots +9: x fire speed, s after the roll
ENCORE_SPIN = 5              # Dancing Slippers +3: shots in the second ring
DIZZY = (90.0, 3.0)          # Dancing Slippers +6: degrees off, s it lasts unused
PRIMA = (5.0, 20)            # Dancing Slippers +9: tiles, most shots in the ring
CROWD_SURF = (1.0, 0.10, 0.50)   # Stompers +6: tiles you pass within, + per enemy, most
AMPLIFIER = (4.0, 0.6)       # Stompers +9: s the amp lasts, x its beats
# The chest tricks' numbers (M28.2d).
STILL_SPEED = 0.1            # tiles/s: slower than this counts as standing still
BARBS = 1                    # Brambleguard +3: bleed stacks
OVERGROWTH = (1.0, 1.5, 10.0)   # Brambleguard +6: s still, radius, damage a second
WILD_HEDGE = 2.0             # Brambleguard +9: tiles round the attacker
STATIC_WEAVE = 2.0           # Wardweave Robe +3: tiles
OVERCHARGE = 0.15            # Wardweave Robe +6: + damage
SECOND_WARD = (3.0, 0.5)     # Wardweave Robe +9: s full, x the shield on top
TEMPERED = (1.0, 5.0, 10)    # Anvil Plate +3: armor a capped hit, s, most
ANVIL_STANCE = (0.5, 0.05)   # Anvil Plate +9: s still, cap (x max HP)
CRYSTAL_CLEAR = 0.3          # Shattercoat +3: s of flight shown ahead
PRISM_SKIN = 6.0             # Shattercoat +6: s unhit
DIAMOND = (5.0, 1.6 / 1.4)   # Shattercoat +9: s unhit, x on top of Glass Cannon's x1.4
RECOIL = 1.0                 # Grudge Mail +3: tiles
RISING_GRUDGE = (10.0, 50.0)   # Grudge Mail +6: + damage a hit, most
SEETHING = 10.0              # Grudge Mail +9: smallest hit that sets it off
CLEAN_GETAWAY = (0.30, 2.0)  # Spotless Tunic +3: + move speed, s
DRESS_CODE = 0.75            # Spotless Tunic +6: x ground damage
IMMACULATE = 0.5             # Spotless Tunic +9: HP fraction it still counts down to (at half)
THICK_FUR = (0.5, 0.9)       # Wolfpelt +3: below this HP, x damage taken
BLOODRAGE = (0.3, 1.3)       # Wolfpelt +6: below this HP, x attack speed
LAST_STAND = (0.15, 3.0, 30.0)   # Wolfpelt +9: HP fraction, s, s between
FORTIFY = 0.1                # Bastion Plate +3: HP a second per 10 max HP above the base
GARRISON = (2.0, 0.20)       # Bastion Plate +6: tiles from a wall, + damage
GLANCE = (0.01, 0.30)        # Mountainhide +3: chance per armor, most
TREMOR = (5.0, 1.5)          # Mountainhide +6: damage a second, radius
RADIANT = (1.5, 1.0)         # Sunward Aegis +3: radius, s between burn stacks
CORONA_BURST = 3.0           # Sunward Aegis +6: radius
ETERNAL_DAY = (0.02, 0.25)   # Sunward Aegis +9: x max HP a second, up to x max HP
ASHES = (10, 2.5, 6.0)       # Phoenix Mantle +3: patches, ring radius, s
REBIRTH = 2.0                # Phoenix Mantle +6: s untouchable
# The ring tricks' numbers (M28.2e).
SHORT_FUSE = 0.05            # Powderkeg Ring +6: + chance a kill that didn't explode
POWDER_KEG = 0.10            # Powderkeg Ring +9: + x the enemy's max HP
FUSE_LINE = (0.1, 0.10)      # Domino Ring +3: s between a chain's explosions, + size each
CLEAN_SWEEP = (5, 5)         # Domino Ring +6: explosions in a chain, kills' XP in the gem
REAP = 10.0                  # Reaper's Band +3: HP an elite kill heals
GRIM = (1.0, 2.0)            # Reaper's Band +6: s since the last kill, x heal
REAPER = 0.01                # Reaper's Band +9: x max HP a kill heals (if more than the power's)
RISING = 10.0                # Ascendant Band +3: damage per level
APOTHEOSIS = 5               # Ascendant Band +9: every Nth level, +1 gear pick
APEX = (50, 1)               # Fang Ring +9: most stacks, bleed stacks a hit at the cap
SLOW_FADE = 1.0              # Fang Ring +6: s between stacks falling off
LONG_ODDS = (100.0, 0.01, 0.30)   # Slingstone Ring +3: per HP over you, +, most
TOPPLED_GIANT = 5            # Slingstone Ring +6: kills a cache is worth
GOLIATH = 2.0                # Slingstone Ring +9: x the bonus on bosses
HARD_WON = 20                # Grizzled Signet +3: from this level on, levels count twice
DRILLED = 10                 # Grizzled Signet +6: every Nth level, a free UPGRADE
LEGEND = 0.01                # Grizzled Signet +9: + max HP per level
MISER = 2.0                  # Hoarder's Ring +3: x salvage loot for the hoard
GOLDEN_ARMOR = (500.0, 10)   # Hoarder's Ring +6: hoard per armor, most
HUNTERS_PAY = 0.10           # Bountymark Ring +6: chance a cache holds a piece
BIG_GAME = 2                 # Bountymark Ring +3: x an elite's cache
RALLY = 1.5                  # Beckoning Ring +3: x the extra enemies' XP
MOTH = (1.0, 2.0)            # Beckoning Ring +6: the tiles the extra enemies keep from you
LIGHTHOUSE = (60.0, 20.0, 6, (9.0, 13.0))   # Beckoning Ring +9: s between waves, s to clear, size, tiles away
CHARMED = 5                  # Fourleaf Ring +6: every Nth level, +1 reroll
BRIM_HP = 1.0                # Brimful Ring +3: "at full HP" (fraction)
SPLASH = (0.25, 1.0)         # Brimful Ring +6: x the crit, tiles
DELUGE = (0.02, 5.0, 0.50)   # Brimful Ring +9: + crit damage a crit, s, most
AIRBORNE = 5.0               # Contagion Ring +3: tiles the spread reaches
MUTATION = 1                 # Contagion Ring +6: + stacks a spread
PLAGUE = (3.0, 1)            # Contagion Ring +9: s between, enemies
ALPHA = (2.0, 0.25)          # Packmaster Ring +3: s since your hit, + summon damage
LOYAL = 3.0                  # Packmaster Ring +6: s before a turret stands again
PACK_RUSH = 5.0              # Packmaster Ring +9: s the wolves go for whoever hit you
# The trinkets' tricks (M28.2f, GEAR.md 17.6).
GROUNDING = (1.5, 0.50)      # Chainbolt Charm +3: burst radius (tiles), x the bolt's damage
OVERLOAD = 5                 # Chainbolt Charm +6: every Nth cast jumps twice as many times
FLING = (6.0, 0.6)           # Bladewheel Charm +3: tiles out along the roll, s out and back
BREATHING = (3.0, 1.0, 2.0)  # Bladewheel Charm +6: every s, a swell lasting s, to x the width
BLADE_STORM = (2, 1.5)       # Bladewheel Charm +9: + daggers, the outer ring at x the radius
WARMTH = 5                   # Ember Amulet +3: 1 HP a pulse for every N enemies burned
FLARE_UP = (5, 3)            # Ember Amulet +6: every Nth pulse, stacks
SUNFIRE = (0.2, 2.0)         # Ember Amulet +9: + tiles per burning enemy in it, up to
COLD_HEART = 1.0             # Winterheart +3: s off the next nova when you're hit
ICE_ARMOR = (5.0, 25.0)      # Winterheart +6: shield per enemy chilled, up to (over the ward)
AVALANCHE = (3, 2.0)         # Winterheart +9: every Nth nova, x its width (freezes at once)
HOWL = (10.0, 4.0, 0.80, 3.0)   # Wolfcall +6: every s, tiles round a wolf, x their damage, s
DIRE_WOLVES = (2.0, 2.0, 1)  # Wolfcall +9: x size, x bite, bleed stacks
RUNE_LINES = (3.0, 10.0, 1.0)   # Runestone +3: link within tiles, damage, s before it hurts the same enemy again
SEEKING_RUNES = (4.0, 2.0)   # Runestone +6: tiles it notices an enemy in, tiles/s it drifts
BUBBLING = 0.50              # Witch's Flask +3: the pool grows this much over its life
WITCHS_BREW = (4, ("burn", "chill", "shock"))   # Witch's Flask +6: one flask in N
CAULDRON_MAX = 3.0           # Witch's Flask +9: a merged pool's radius, at most x the pool's
DOWNPOUR = 2.5               # Stormjar +3: the puddle's radius (tiles)
EYE_OF_THE_STORM = (0.75, 2.5, 1.5)   # Stormjar +9: s after the first, orbit tiles, rad/s
CARRIED = 1.5                # Mender's Totem +6: tiles/s it follows you at
GLOW = (0.10, 2.0)           # Firefly Lantern +3: + crit chance, s
WISPS = (5, 3.0, 1.5)        # Firefly Lantern +9: every Nth bolt, s, radius
OSSUARY_REACH = 15.0         # Skull Sentry +3: the last kill counts this close to you (tiles)
CALCIFY = (8, 15.0)          # Skull Sentry +6: shards, damage each
BONE_LEGION = 1              # Skull Sentry +9: + turrets at a time
# The wizard's main-hand tricks (M28.2g, GEAR.md 17.7).
CONDUCTING = (2.0, 0.50)     # Stormcaller +3: s since your bolt hit it, x the dart's damage
THUNDERLORD = (1, 5, 0.30)   # Stormcaller +9: + jumps, jumps for the strike again, x the bolt's damage
OVERCURRENT = (0.75, 0.40)   # Copperwire +6: past this share of the reach, + damage
CHARGED_AIR = 0.10           # Thunderhead +3: + dart damage to shocked enemies
DOWNDRAFT = (3, 5.0)         # Thunderhead +6: shocked enemies, within tiles of you
SUPERSTORM = 1.5             # Thunderhead +9: tiles round a bolt's hit that get shocked
THUNDERBALL = (5, 3.0, 2.5)  # Crackle Staff +9: every Nth cast, s rolling, radius
HAUNT = 0.25                 # Ghostwood +3: + damage after going through a wall
GHOSTWOOD_SIGHT = 12.0       # Ghostwood +9: tiles round you
PERSISTENCE = 1.3            # Wyrmseeker +3: x speed once its target is lost
ENDLESS_HUNT = (3, 0.70, 8.0)   # Wyrmseeker +9: hits, x damage after the first, tiles more flight
SUSTAIN = 2.0                # Humming Staff +3: the window (s)
RESONANT_RING = (30.0, 2.0, 1.0)   # Humming Staff +6: damage, radius, s between rings per enemy
PERFECT_PITCH = 8            # Humming Staff +9: darts counted at most (x RESONANCE[1])
CRUSH = 10.0                 # Gravewell +3: damage
EVENT_HORIZON = 1.5          # Gravewell +6: enemy shots this close to the hit
SINGULARITY = (6, 1.5, 2.0)  # Gravewell +9: every Nth cast, s, tiles/s pulled
STORM_TEMPEST = 5            # Stormheart +6: new darts a cast
MAELSTROM = 0.80             # Stormheart +9: x the damage of the dart before
EPICYCLE = 2                 # Orrery +6: swings at most
GRAVITY_ASSIST = (1.5, 0.50) # Orrery +9: x speed, + damage
# The dwarf's and the huntress's main-hand tricks (M28.2h, GEAR.md 17.8).
BANK_SHOT = 0.20             # Rebound Axe +3: + damage a bounce
CAROM = 5                    # Rebound Axe +9: bounces, then home
SAW = 0.10                   # Hoverhead +3: + damage for each hit while hovering
HOLD_IT = 2.0                # Hoverhead +6: s more it may hover while you hold the attack
BUZZSAW = 1.5                # Hoverhead +9: tiles round the hovering axe
HOMING_BACK = 2.0            # Homesick +3: tiles off its way home it bends for
WELCOME_HOME = (0.10, 2.0, 3)   # Homesick +6: + attack speed a catch, s, most
TAUT = (0.8, 0.40)           # Chainlink +3: this share of its range from you, x the axe's damage
SHACKLE = 0.5                # Chainlink +6: s dragged
GALE_FORCE = 2               # Whirlwind +6: rethrows a throw
REUNITE = (0.5, 0.30)        # Doublebit +3: tiles apart they meet at, + damage
CROSSING = 3.0               # Doublebit +6: tiles apart the halves start, crossing over
QUARTERING = (4, 0.40)       # Doublebit +9: pieces, x damage each
THUNDER_RAIN = (1.0, 0.20)   # Cloudburst +6: tiles, + damage per other arrow that close
SQUALL_LINE = 0.4            # Cloudburst +9: s before the second rain
GATHERING_SPEED = 1.10       # Broadleaf +3: x speed per enemy passed
RUN_THROUGH = 4              # Broadleaf +6: enemies passed
OLD_SCENT = 2.0              # Bloodhound +3: s the last mark stays
PACK_HUNT = (3.0, 3.0)       # Bloodhound +9: tiles round the fallen mark, s marked
HELD_BREATH = (1.0, 2.0)     # Stillwater +3: s still, x arrow speed
ZEN = (2.0, 0.50)            # Stillwater +6: s still, + crit damage
STILL_WATERS = 1.0           # Stillwater +9: s Steady Aim holds after you move
FOLLOW_THROUGH = 3           # Farsight +3: enemies a crit passes
SECOND_SIGHT = 6             # Farsight +6: every Nth arrow
LIGHTNING_ARROW = 60.0       # Farsight +9: x a crit arrow's speed (across its range in a frame)
SEED_STORM = (3, 2.0, 1.0, 10.0, 1.5)   # Splitbranch +9: seeds, s, radius, damage/s, tiles thrown
# The princess's and the bard's main-hand tricks (M28.2i, GEAR.md 17.9).
FULL_SPECTRUM = 5            # Prismatic +3: colors (or all of a smaller shot's) on one enemy -> crit
AFTERGLOW = 1.0              # Prismatic +6: s the bonus stays on the enemy
RAINBOWS_END = 1.5           # Prismatic +9: x the Prism bonus (+30% for +20%)
LENS = 0.25                  # Spyglass +3: + damage of the middle color
PINPOINT = (2.0, 0.5)        # Spyglass +6: s still to narrow fully, x the fan at the narrowest
BEAM = (1.0, 0.2)            # Spyglass +9: s still, s the beam shows
SATURATED = 0.30             # Chroma +3: a color's status chance
COLOR_THEORY = (2, 0.15)     # Chroma +6: your statuses on it, + damage
CHROMATIC = 2                # Chroma +9: stacks a color gives
FACE_TO_FACE = (2.0, 0.20)   # Duelist's +3: tiles, + damage on top
DUEL = (0.25, 0.75)          # Duelist's +6: + damage to the duelist, x damage it deals you
BLADEWORK = (6.0, 1.5)       # Duelist's +9: tiles, x the Point Blank bonus (+60% for +40%)
RADIANT_SPLIT = 0.25         # Kaleido +6: tiles a split piece's hit reach grows (half a color)
INFINITE_MIRROR = (2, 3, 25.0)   # Kaleido +9: pieces, times, degrees apart
FOCAL_POINT = (1.5, 0.40)    # Crossbeam +3: tiles round the crossing, + damage
SECOND_CROSSING = 3.0        # Crossbeam +6: tiles past the first crossing
CLIMAX = 1.25                # Fortissimo +6: x reach at the top of the crescendo
FORTE = 10                   # Fortissimo +9: beats in a row (+100%)
LULLABIED = (5, 3.0)         # Cradlesong +3: beats in a row, s asleep at most
NOTHING_WASTED = 0.04        # Cradlesong +6: + damage of the next beat per HP not healed
MOTHERS_SONG = (2, 10)       # Cradlesong +9: HP per enemy, at most this many HP a beat
SWING_BEAT = 0.20            # Offbeat +3: share of the wait cut before the loud beat
POLYRHYTHM = 3               # Offbeat +6: every Nth beat is both
THE_DROP = 2.2               # Offbeat +9: x damage of the loud beat
CLASH = 15.0                 # Sourstring +3: damage pushed into a wall
TRITONE = 2.0                # Sourstring +6: x push on chilled enemies
SHRIEK = 2                   # Sourstring +9: chill stacks a beat
OVERTURE = 5.0               # Showstopper +3: s without hitting anything
CURTAIN_CALL = (0.30, 20.0)  # Showstopper +6: HP share, s between
MAGNUM_OPUS = 6              # Showstopper +9: every Nth beat
BIRDSONG = 16.0              # Songbird +3: tiles of path a note may fly round walls
CHORUS = (4, 2)              # Songbird +6: every Nth beat, x notes
ARIA = 1.0                   # Songbird +9: tiles round where a note lands

# The 100 bases (GEAR.md 15.6). Keys are the card keys whose effect each
# one's power is; the card's name stays as the power's name.
_W = "main"
GEAR = {
    # Main hand: the hero's own weapon line (hero-only: the card's `heroes`).
    "storm_caller": GearSpec("Stormcaller Rod", _W),
    "conductor": GearSpec("Copperwire Staff", _W),
    "supercell": GearSpec("Thunderhead Rod", _W),
    "phase_darts": GearSpec("Ghostwood Staff", _W),
    "ball_lightning": GearSpec("Crackle Staff", _W),
    "seeker": GearSpec("Wyrmseeker Staff", _W),
    "resonance": GearSpec("Humming Staff", _W),
    "implosion": GearSpec("Gravewell Staff", _W),
    "arcane_storm": GearSpec("Stormheart Staff", _W),
    "orbiting_darts": GearSpec("Orrery Staff", _W),
    "ricochet": GearSpec("Rebound Axe", _W),
    "hang_time": GearSpec("Hoverhead Axe", _W),
    "homeward_fury": GearSpec("Homesick Axe", _W),
    "tether": GearSpec("Chainlink Axe", _W),
    "cyclone": GearSpec("Whirlwind Axe", _W),
    "splitting_axe": GearSpec("Doublebit Axe", _W),
    "arrow_rain": GearSpec("Cloudburst Bow", _W),
    "broadhead": GearSpec("Broadleaf Bow", _W),
    "hunters_mark": GearSpec("Bloodhound Bow", _W),
    "steady_aim": GearSpec("Stillwater Bow", _W),
    "deadeye": GearSpec("Farsight Bow", _W),
    "split_arrow": GearSpec("Splitbranch Bow", _W),
    "prism": GearSpec("Prismatic Wand", _W),
    "focus": GearSpec("Spyglass Wand", _W),
    "spectrum": GearSpec("Chroma Wand", _W),
    "point_blank": GearSpec("Duelist's Wand", _W),
    "refraction": GearSpec("Kaleido Scepter", _W),
    "converge": GearSpec("Crossbeam Wand", _W),
    "crescendo": GearSpec("Fortissimo Lute", _W),
    "lullaby": GearSpec("Cradlesong Lute", _W),
    "syncopation": GearSpec("Offbeat Lute", _W),
    "dissonance": GearSpec("Sourstring Lute", _W),
    "grand_finale": GearSpec("Showstopper Lute", _W),
    "sheet_music": GearSpec("Songbird Lute", _W),
    # Off-hand: shot patterns and attack rhythm.
    "cross_fire": GearSpec("Compass Orb", "off"),
    "starburst": GearSpec("Sunwheel", "off"),
    "rear_guard": GearSpec("Hindsight Orb", "off"),
    "spiral": GearSpec("Nautilus Shell", "off"),
    "twin_lanes": GearSpec("Twinned Quiver", "off"),
    "echo": GearSpec("Canyon Horn", "off"),
    "frenzy": GearSpec("War Drum", "off"),
    "spray_and_pray": GearSpec("Pepperbox", "off"),
    # Head: statuses and elements.
    "kindling": GearSpec("Cinderveil Hood", "head"),
    "wildfire": GearSpec("Blazecrown", "head"),
    "venom": GearSpec("Viper Mask", "head"),
    "virulence": GearSpec("Plaguebeak", "head"),
    "frostbite": GearSpec("Rime Hood", "head"),
    "shatter": GearSpec("Glassfrost Helm", "head"),
    "static": GearSpec("Stormvane Helm", "head"),
    "serrated": GearSpec("Thornhelm", "head"),
    # Serrated (bleed) is its only source and shares the head slot, so the
    # cowl brings its own bleed (M28.1).
    "hemorrhage": GearSpec("Bloodtrail Cowl", "head", mods=(("bleed", "status", 1),), needs=()),
    "thermal_shock": GearSpec("Steamcrown", "head"),
    "toxic_current": GearSpec("Galvanic Mask", "head"),
    # Chest: defence and trade-offs.
    "thorn_mail": GearSpec("Brambleguard", "chest"),
    "ward_charm": GearSpec("Wardweave Robe", "chest"),
    "heavy_plate": GearSpec("Anvil Plate", "chest"),
    "glass_cannon": GearSpec("Shattercoat", "chest"),
    "retaliation": GearSpec("Grudge Mail", "chest"),
    "untouched": GearSpec("Spotless Tunic", "chest"),
    "berserker": GearSpec("Wolfpelt", "chest"),
    "bulwark": GearSpec("Bastion Plate", "chest"),
    "juggernaut": GearSpec("Mountainhide", "chest"),
    "aegis": GearSpec("Sunward Aegis", "chest"),
    "phoenix": GearSpec("Phoenix Mantle", "chest", grow="damage"),   # one revival, always
    # Feet: movement and the roll (the hero rolls are hero-only).
    "riposte": GearSpec("Fencer's Boots", "feet"),
    "slipstream": GearSpec("Windrunners", "feet"),
    "close_call": GearSpec("Hairsbreadth", "feet"),
    "scorched_trail": GearSpec("Ashwalkers", "feet"),
    "momentum": GearSpec("Gallopers", "feet"),
    "fleet_strike": GearSpec("Wingheel Sandals", "feet"),
    "blink": GearSpec("Phasewalkers", "feet"),
    "shoulder_charge": GearSpec("Ramhorn Boots", "feet"),
    "backflip": GearSpec("Tumbler Boots", "feet"),
    "pirouette": GearSpec("Dancing Slippers", "feet"),
    "drop_the_beat": GearSpec("Stompers", "feet"),
    # Rings: triggers, scaling and the economy.
    "volatile": GearSpec("Powderkeg Ring", "ring"),
    "chain_reaction": GearSpec("Domino Ring", "ring"),
    "soul_harvest": GearSpec("Reaper's Band", "ring"),
    "surge": GearSpec("Ascendant Band", "ring"),
    "bloodlust": GearSpec("Fang Ring", "ring"),
    "giant_slayer": GearSpec("Slingstone Ring", "ring"),
    "veteran": GearSpec("Grizzled Signet", "ring"),
    "golden_hoard": GearSpec("Hoarder's Ring", "ring"),
    "bounty": GearSpec("Bountymark Ring", "ring"),
    "beacon": GearSpec("Beckoning Ring", "ring"),
    "fortune": GearSpec("Fourleaf Ring", "ring", grow="damage"),     # one extra card, always
    "overflow": GearSpec("Brimful Ring", "ring"),
    "pandemic": GearSpec("Contagion Ring", "ring"),
    "pack_leader": GearSpec("Packmaster Ring", "ring"),
    # Trinkets: the spells. Chain Lightning is the wizard's (its four payoffs
    # are main-hand pieces, so it can't share their slot; M28.1).
    "chain_lightning": GearSpec("Chainbolt Charm", "trinket"),
    "daggers": GearSpec("Bladewheel Charm", "trinket"),
    "ember_aura": GearSpec("Ember Amulet", "trinket"),
    "frost_nova": GearSpec("Winterheart", "trinket"),
    "spirit_wolf": GearSpec("Wolfcall Whistle", "trinket"),
    "rune_trap": GearSpec("Runestone Pouch", "trinket"),
    "poison_flask": GearSpec("Witch's Flask", "trinket"),
    "storm_cloud": GearSpec("Stormjar", "trinket"),
    "healing_totem": GearSpec("Mender's Totem", "trinket"),
    "fire_wand": GearSpec("Firefly Lantern", "trinket"),
    "bone_turret": GearSpec("Skull Sentry", "trinket"),
    # --- Boss uniques (M28.5; GEAR.md 21): `unique` = the boss, three fixed affixes ---
    "tongue_lasher": GearSpec("Tongue Lasher", "off", unique="froggy",
                              affixes=("long_reach", "quick_hands", "brutal")),
    "bubble_belt": GearSpec("Bubble Belt", "chest", unique="froggy",
                            affixes=("thick_hide", "nimble", "second_wind")),
    "frogskin_boots": GearSpec("Frogskin Boots", "feet", unique="froggy",
                               affixes=("swift_boots", "quick_recovery", "extra_roll")),
    "leechskin": GearSpec("Leechskin", "chest", unique="leech_swarm",
                          affixes=("vampiric", "thick_hide", "second_wind")),
    "latch_hood": GearSpec("Latch Hood", "head", unique="leech_swarm",
                           affixes=("affliction", "lingering", "keen_eye")),
    "bloated_charm": GearSpec("Bloated Charm", "trinket", unique="leech_swarm",
                              affixes=("vampiric", "potency", "quickened")),
    "proboscis_ring": GearSpec("Proboscis Ring", "ring", unique="proboscia",
                               affixes=("vampiric", "affliction", "lucky_charm")),
    "engorged_mantle": GearSpec("Engorged Mantle", "chest", unique="proboscia",
                                affixes=("sharpened", "iron_skin", "second_wind")),
    # (M28.5b: the desert's and the ruins')
    "dung_ball": GearSpec("Dung Ball", "trinket", unique="khepri",
                          affixes=("broad_strokes", "sharpened", "swift_boots")),
    "scarab_carapace": GearSpec("Scarab Carapace", "chest", unique="khepri",
                                affixes=("iron_skin", "thick_hide", "nimble")),
    "spittoon": GearSpec("Spittoon", "trinket", unique="ol_spitter",
                         affixes=("quickened", "potency", "long_reach")),
    "hump_pack": GearSpec("Hump Pack", "off", unique="ol_spitter",
                          affixes=("multishot", "quick_hands", "piercing")),
    "hourglass_ring": GearSpec("Hourglass Ring", "ring", unique="nameless_magus",
                               affixes=("nimble", "quick_recovery", "keen_eye")),
    "sand_slippers": GearSpec("Sand Slippers", "feet", unique="nameless_magus",
                              affixes=("swift_boots", "extra_roll", "thick_hide")),
    "lead_apron": GearSpec("Lead Apron", "chest", unique="fallout_king",
                           affixes=("iron_skin", "thick_hide", "scholar")),
    "geiger_ring": GearSpec("Geiger Ring", "ring", unique="fallout_king",
                            affixes=("affliction", "potency", "prospector")),
    "rod_of_fission": GearSpec("Rod of Fission", "trinket", unique="fallout_king",
                               affixes=("broad_strokes", "elementalist", "quickened")),
    "black_ice_crown": GearSpec("Black Ice Crown", "head", unique="snow_king",
                                mods=(("chill", "status", 1),), needs=(),
                                affixes=("affliction", "lingering", "elementalist")),
    "hermits_furs": GearSpec("Hermit's Furs", "chest", unique="snow_king",
                             affixes=("thick_hide", "second_wind", "iron_skin")),
    "parasol": GearSpec("Lace Parasol", "off", unique="fragile",
                        affixes=("nimble", "keen_eye", "brutal")),
    "mr_buttons": GearSpec("Mr. Buttons", "trinket", unique="fragile",
                           affixes=("thick_hide", "second_wind", "lucky_charm")),
    "bat_form": GearSpec("Bat Form Boots", "feet", unique="fragile",
                         affixes=("swift_boots", "quick_recovery", "nimble")),
    # (M28.5c: the forest's, Mycelium's and the necromancer's)
    "shrinking_dust": GearSpec("Shrinking Dust", "feet", unique="nettle",
                               affixes=("swift_boots", "nimble", "quick_recovery")),
    "blight_thorn_ring": GearSpec("Blightthorn Ring", "ring", unique="nettle",
                                  affixes=("sharpened", "affliction", "thick_hide")),
    "cleaver_of_cuddles": GearSpec("Cuddles' Cleaver", "trinket", unique="love_cuddles",
                                   affixes=("broad_strokes", "brutal", "vampiric")),
    "acorn_bandolier": GearSpec("Acorn Bandolier", "off", unique="love_cuddles",
                                affixes=("broad_strokes", "quick_hands", "long_reach")),
    "tripwire_boots": GearSpec("Tripwire Boots", "feet", unique="love_cuddles",
                               affixes=("swift_boots", "extra_roll", "lingering")),
    "rootbound_boots": GearSpec("Rootbound Boots", "feet", unique="the_fallen",
                                affixes=("thick_hide", "iron_skin", "second_wind")),
    "heartwood_ring": GearSpec("Heartwood Ring", "ring", unique="the_fallen",
                               affixes=("second_wind", "iron_skin", "magnet")),
    "mycelial_ring": GearSpec("Mycelial Ring", "ring", unique="mycelium_amanita",
                              affixes=("potency", "lingering", "broad_strokes")),
    "fly_agaric_cap": GearSpec("Fly Agaric Cap", "head", unique="mycelium_amanita",
                               affixes=("affliction", "keen_eye", "lucky_charm")),
    "inkwell_charm": GearSpec("Inkwell Charm", "trinket", unique="mycelium_inkcap",
                              affixes=("quickened", "keen_eye", "scholar")),
    "lawyers_wig": GearSpec("Lawyer's Wig", "head", unique="mycelium_inkcap",
                            affixes=("quick_hands", "lingering", "scholar")),
    "puffball_sandals": GearSpec("Puffball Sandals", "feet", unique="mycelium_puffball",
                                 affixes=("extra_roll", "potency", "quick_recovery")),
    "spore_wind_band": GearSpec("Spore Wind Band", "ring", unique="mycelium_puffball",
                                affixes=("lingering", "affliction", "nimble")),
    "phylactery": GearSpec("Phylactery", "ring", unique="necromancer",
                           affixes=("iron_skin", "vampiric", "prospector")),
    "lichs_gaze": GearSpec("Lich's Gaze", "head", unique="necromancer",
                           affixes=("brutal", "keen_eye", "long_reach")),
    "corpse_candle": GearSpec("Corpse Candle", "trinket", unique="necromancer",
                              affixes=("elementalist", "second_wind", "broad_strokes")),
    # (M29.5: the Four Horsemen's, dropped by the cavalry -- Paradise's boss)
    "crown_of_conquest": GearSpec("Conquest's Crown", "head", unique="cavalry",
                                  affixes=("brutal", "keen_eye", "lingering")),
    "ring_of_blood": GearSpec("Ring of Blood", "ring", unique="cavalry",
                              affixes=("sharpened", "vampiric", "brutal")),
    "black_scales": GearSpec("The Black Scales", "trinket", unique="cavalry",
                             affixes=("second_wind", "potency", "lucky_charm")),
    "pale_riders_cloak": GearSpec("Pale Rider Cloak", "chest", unique="cavalry",
                                  affixes=("thick_hide", "iron_skin", "second_wind")),
    # (M30.5: the Host of the Feast's -- Pandemonium's boss -- one per pleasure)
    "gluttons_bib": GearSpec("Glutton's Bib", "chest", unique="host_of_feast",
                             affixes=("thick_hide", "second_wind", "magnet")),
    "hosts_goblet": GearSpec("Host's Goblet", "trinket", unique="host_of_feast",
                             affixes=("broad_strokes", "lingering", "potency")),
    "dancing_shoes": GearSpec("Dancing Shoes", "feet", unique="host_of_feast",
                              affixes=("swift_boots", "extra_roll", "quick_recovery")),
    "gilded_ring": GearSpec("Gilded Ring", "ring", unique="host_of_feast",
                            affixes=("brutal", "keen_eye", "prospector")),
    # (M31.5: the Ancestor's -- Pangaea's boss -- one per age, one for the first life)
    "spirit_herd": GearSpec("Spirit Herd", "trinket", unique="ancestor",
                            affixes=("broad_strokes", "brutal", "second_wind")),
    "tyrant_skull": GearSpec("Tyrant Skull", "head", unique="ancestor",
                             affixes=("iron_skin", "brutal", "long_reach")),
    "swarm_ring": GearSpec("Swarm Ring", "ring", unique="ancestor",
                           affixes=("affliction", "lingering", "quickened")),
    "echo_conch": GearSpec("Echo Conch", "off", unique="ancestor",
                           affixes=("quick_hands", "keen_eye", "sharpened")),
}
# Each boss's relics, in a fixed order (the drop picks by index).
BOSS_UNIQUES: dict = {}
for _key, _g in GEAR.items():
    if _g.unique is not None:
        BOSS_UNIQUES.setdefault(_g.unique, []).append(_key)
BOSS_UNIQUES = {b: tuple(ks) for b, ks in BOSS_UNIQUES.items()}

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
    "missiles": ("W4", "W8", "W9", "W10", "W11", "W12", "G20"),
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
    "saddlebags": UpgradeSpec("Saddlebags", "+1 bag space for spare gear", (("bag", "add", 1),),
                              max_level=2, base_cost=800, growth=1.8),          # (M28.4d)
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
    # P8: the haunted forest
    "skeleton": (500, "Falls into a bone pile that pulls itself together. Break the pile."),
    "woodsman": (500, "Slow, tough, walks straight at you with a rusty hatchet."),
    "spiderling": (300, "Swarms of tiny spiders. Quick, weak, many."),
    "bat": (400, "Flutters at you on a wobbly line, over everything."),
    "banshee": (900, "Breathes in, then screams in a cone that pushes you back."),
    "phantom": (900, "Drifts through trees. Only solid when it glows: hit it then."),
    "grave_digger": (900, "The ground cracks where he's about to dig up a skeleton."),
    "headless_knight": (1500, "Three wide swings in a row. Hit the floating head to stagger him."),
    "centipede": (1000, "Shoot it apart and each half crawls on as its own centipede."),
    "giant_spider": (900, "Keeps back and spits webs that stick: don't walk through them."),
    "woodcutter": (800, "Throws an axe that comes back to him. Dodge it twice."),
    "cultist": (1000, "Skeletons rise from its candle ring. Shoot the candles out."),
    "apprentice": (800, "Its cursed orb splits in four when it hits anything."),
    "wendigo": (1500, "Lunges twice, fast. It rears up before it howls: the howl slows you."),
    # P9: the desert
    "fire_ant": (300, "Swarms of them. Quick, weak, many."),
    "husk": (500, "Slow, tough, walks straight at you."),
    "sand_imp": (400, "Hops straight at you in quick bursts."),
    "jackal": (400, "A fast runner and a quick bite."),
    "scorpion": (1500, "Armoured in front. Two pincer snaps, then the tail: step off its line."),
    "vulture": (700, "Circles high and waits for you to be hurt. Then it dives."),
    "basilisk": (900, "Flares its frill and stares down a line: caught in it, you're stone for a moment."),
    "rattlesnake": (600, "Rattles when you're close, then strikes and slithers off."),
    "mummy": (1500, "Its bandages lash out and drag you in. Roll to break free."),
    "fire_dancer": (900, "Breathes a cone of flame and leaves fire where it danced."),
    "glass_mage": (800, "Its shards glance off walls twice. Mind narrow places."),
    "dune_raider": (800, "Dashes in, slashes twice, dashes away. Again."),
    "tumbleweed": (300, "Rolls with the wind, hurting what it bumps into."),
    "cactus_golem": (900, "Every hit you land, it shoots spines all round. Hit it from far."),
    "djinn_lamp": (900, "Its vortex drags you toward it; close in, it zaps."),
    # P10: the ruins
    "gnoll": (500, "Packs of hyena-men with clubs."),
    "stone_imp": (400, "Small, fast, tougher than it looks."),
    "crawling_hand": (300, "Swarms of creeping hands. Weak, many."),
    "lost_soldier": (500, "Slow, armoured, a rusty spear. Soaks shots."),
    "gargoyle": (900, "Swoops when you come near, then sits as stone: nothing hurts it then."),
    "clockwork": (800, "Winds its key, then sweeps five bolts across you."),
    "colossus": (1500, "Its stomp rolls a ring along the ground: roll through it."),
    "rubble_crab": (800, "Break the rubble shell first; bare, it runs."),
    "gem_thief": (900, "Runs off with your XP gems. Kill it to get them back."),
    "sniper": (900, "A long aiming line, then a bolt through everything in it."),
    "flail_brute": (1500, "A spinning flail that grows, then flies. Get close between spins."),
    "rune_mine": (600, "Drifts at you; in its ring it glows, then blows. Shoot it first."),
    "haunted_blade": (800, "Three swords circling; they thrust one at a time."),
    "bell_ghost": (900, "Its bell wakes everything around and knocks you back."),
    # P11: the swamp
    "bog_zombie": (500, "Slow, tough, dripping, straight at you."),
    "newt": (300, "Swarms of little newts. Quick, weak, many."),
    "gator_hatchling": (400, "Packs of baby gators: quick nippers."),
    "mudskipper": (400, "Hops at you across the mud."),
    "crocodile": (1500, "Eyes above the bog. It lunges, clamps on and drags you: roll to break free."),
    "turtle": (900, "Snaps hard. Hurt enough, it hides in its shell: wait it out."),
    "heron": (800, "Stabs a line with its beak from 3 tiles. Flaps off if you close in."),
    "swamp_hag": (900, "Curses the ground under you: step out of the puddle or be rooted."),
    "lizardman": (700, "Throws javelins that stick in the ground as obstacles."),
    "marsh_light": (900, "Three lights, one real. Shoot the real one and the others go out."),
    "bloated_corpse": (700, "Bursts into a lingering toxic cloud. Kill it from far."),
    "sludge": (700, "Splits in two when it dies, and again. Three sizes."),
    # P12: the mushroom biome
    "sporeling": (300, "Swarms of tiny walking spores."),
    "fungus_gnat": (300, "Clouds of gnats over everything."),
    "shroomling": (400, "Little mushroom men with a headbutt."),
    "mold_zombie": (500, "Slow, tough, overgrown, straight at you."),
    "myconid": (900, "Its pollen cloud heals the enemies in it. Pull the fight away or kill it."),
    "cordyceps": (800, "Spits spore darts. When it dies, sporelings crawl out."),
    "fungal_brute": (1500, "Regrows fast unless you keep hitting it."),
    "rootweaver": (900, "A line of cracks races at you; roots burst along it. Step off the line."),
    "giant_snail": (700, "Its shell takes half. Its slime trail slows you."),
    "pillbug": (700, "Rolls at you as a ball (hard to hurt), then uncurls to rest: hit it then."),
    "mantis": (1500, "Leaps at you, raises both scythes, then an X-slash. Dodge the leap."),
    "fairy_ring": (900, "Step inside and sporelings rise. Break three of its caps."),
    "mold_core": (900, "Spreads mold patches that hurt. Break the core and they wither."),
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
    # M25.2
    "rabid_squirrel": (1500, "Guards the nut caches, and drops out of the trees in gangs."),
    "love_cuddles": (5000, "Steal its acorns. Shake its tree. Shoot the wires. Wait out the frenzy."),
    # M25.3
    "mimic_sapling": (1500, "Hides among the lumberjack's marked trees. Chop one and it may bite."),
    "bark_beetle": (800, "Crawls out of The Fallen's bark."),
    "the_fallen": (5000, "Watch for the blinking eye. Stand by the fires. Stuff its maw or hold fire."),
    # M26.1
    "mycelium_amanita": (5000, "The fly agaric. Shoot its warts off; cut its network; roll off a trip."),
    # M26.2
    "mycelium_inkcap": (5000, "The shaggy ink cap. Watch where it bubbles; roll off blots; read fast."),
    "ink_imp": (800, "A letter of Mycelium's scrawl, risen and running."),
    # M26.3
    "mycelium_puffball": (5000, "The giant puffball. Pop its mines next to it; mind the wind."),
    # M27
    "necromancer": (10000, "Twice-living. Crush the corpses; hide from his gaze; find the one he hides in."),
    "risen_dead": (1500, "Raised by More than Life from whatever falls in his necropolis."),
    # M28.4c
    "mimic": (1200, "A chest with teeth. It lunges, lashes a tongue that drags you in and spits "
                    "coins. Beaten, it coughs up the best of what it ate."),
    # M29.2: Paradise (all unveil: hurt below 70%, or come close)
    "cherub": (2500, "Plinks slow notes. Unveiled: four faces; it lunges, bites and roars you back."),
    "seraph": (4000, "Rings of light. Unveiled: a burning eye spinning spirals of blood and fire."),
    "ophan": (2500, "A rolling halo. Unveiled: wheels of eyes racing and bouncing; mind the slick."),
    "watcher": (2500, "Never moves. Unveiled: its gaze sweeps along the line it shows first."),
    "lamb": (2000, "Seven horns, seven eyes: it charges along the line it shows. Walls daze it."),
    "dove": (1500, "A flock. Unveiled, they circle and dive at you one after another."),
    "locust": (1500, "Crowned, with human faces. Unveiled, a stinging swarm."),
    "halo": (2000, "Drifts at you. Unveiled, a buzzsaw that turns wide: step aside and it overshoots."),
    # M29.3
    "trumpeter": (4000, "Its notes push you back. Unveiled, each blast calls a hail of fire and blood "
                        "on the ground it marks."),
    "censer_bearer": (2500, "Harmless incense. Unveiled, it hurls burning coals: watch where they'll land."),
    "bowl_bearer": (2500, "Unveiled, it pours its bowl where you stand: a spreading pool of blood."),
    "chorister": (2500, "Sings at the choir rings, healing the angels near it. Unveiled, it shrieks in rings."),
    "weeping_saint": (2500, "Unveiled, it lobs arcs of blood tears that leave pools."),
    "martyr": (2500, "Every hit sticks another arrow in it, and unveiled it throws them back."),
    "behemoth": (4000, "Unveiled, it charges through columns. Its bone plates shrug off hits from "
                       "the front."),
    "leviathan": (4000, "Lives in the river of blood. Unveiled, it surges along it and spits at you."),
    # M29.4
    "cavalry": (10000, "Four white riders, one life. Read the lanes; split them when they sing; "
                       "break a pillar to open the cage. Then they unveil: the Four Horsemen."),
    # M29.5
    "conquest": (5000, "Its arrows crown you: half damage until you roll. Break its banners."),
    "war": (5000, "Slashes send waves of blood. In its duel ring both of you hit twice as hard."),
    "famine": (5000, "Keep it hurt: its scales take from whoever is healthier. No healing near it."),
    "death": (5000, "Hades follows it: stay out of the dark. Whatever dies in the court rises once."),
    "pale_shade": (1000, "Something slain in the Horsemen's court, risen for a few seconds."),
    # M30.2: Pandemonium's revellers (a group frenzies as one)
    "glutton": (2500, "Feasts at the tables. Frenzied, it belly-slams a ring; hurt, it gorges to heal."),
    "drunkard": (2000, "Weaves where you can't predict it. Its bottles leave wine that slows and tempts."),
    "toastmaster": (4000, "Its toasts speed up every reveller near it and send a wave of wine. Kill it first."),
    "ravenous": (1500, "Never full. It latches on and bites; roll to throw it off."),
    "dancer": (2000, "Its steps repeat: round you, a dash through, round the other way, a dash."),
    "masked_dancer": (2000, "Swaps places with another dancer in a flash, then stabs."),
    "band_drummer": (2000, "Never leaves its drums. Every beat sends a ring: roll through it."),
    "piper": (4000, "Its song tempts you in a cone, and it carries the frenzy to the next group."),
    # M30.3
    "vain": (2000, "Its mirror's flash dazzles you and turns your shots back. Mind the marked cone."),
    "gilded_reveller": (2500, "Looks like a statue until its group wakes. Break its gold shell first."),
    "hoarder": (2000, "Throws fistfuls of coins; the coins stay on the floor and trip you."),
    "beloved": (4000, "Its admirers circle it and take its hits. Break the ring to reach it."),
    "cupbearer": (2500, "Never in the trance. Refills the hurt revellers and throws tempting wine."),
    "carver": (2500, "Never in the trance. Lunging cleaves; its cleavers fly out and come back."),
    "bouncer": (3000, "Never in the trance. Charges along a shown line and throws you at the nearest feast."),
    "master_of_revels": (5000, "Its bell wakes every group near it -- and snaps you out of a trance."),
    # M30.4
    "host_of_feast": (10000, "Never stops dancing; his charm sweeps you into his dance. Then the mask "
                             "cracks: clear the food and kill his guests before he eats them and grows."),
    # M30.5
    "feast_waiter": (1500, "The Host's servant, bringing him a course. Kill it before he eats it."),
    # M31.2: Pangaea (every attack echoes 3 s later; kill it and its echoes stop)
    "mammoth": (4000, "Herds. It trumpets you back, then the herd stampedes down shown lanes: "
                      "stand in a gap."),
    "sabre_tooth": (2500, "Only its eyes show in the ferns. It pounces along a shown line and "
                          "pins you: roll free."),
    "woolly_rhino": (2500, "Its front shrugs off shots. It charges, skids and turns slowly: "
                           "hit its side."),
    "cave_bear": (2500, "Rears up, swipes twice and slams down. Its roar wakes the beasts."),
    "spear_hunter": (2000, "Spears fly fast and far, and stick where they land, fencing you in."),
    "trapper": (2000, "Snares and pits, faintly marked: roll over them. Its bolas tangle your legs."),
    "fire_bearer": (2000, "Its torches set the ferns alight, and it drives the beasts at you."),
    "shaman": (4000, "Its painted beasts come alive and charge. While it lives, no fire near it "
                     "goes out."),
    # M31.3
    "raptor": (2000, "Packs circle you, then leap in one at a time from behind, each leap marked."),
    "tyrant": (5000, "Its roar roots you in fear unless you roll. It bites ahead, sweeps its tail "
                     "behind, and the ground shakes as it walks."),
    "club_tail": (3000, "Shots glance off its back: hit its head. Its club tail throws you."),
    "pterosaur": (2500, "Swoops along a shown line; caught, you're carried off and dropped."),
    "dragonfly": (1500, "Darts in straight lines, each marked a beat ahead."),
    "bombardier_beetle": (2000, "Turns its back and sprays boiling spray: get round to its front."),
    "ant_mound": (2500, "Sends ants marching in a column. Break the column and they swarm. "
                        "Collapse the mound."),
    "giant_ant": (1000, "Marches in a column from its mound; hurt one and they all swarm you."),
    "sea_scorpion": (5000, "Lurks in the steaming pools: its claws drag you into the scalding water. "
                           "Roll free. Mind its tail spike."),
    "hatchling": (800, "Out of a broken egg. The parent is coming."),
    # M31.4
    "ancestor": (10000, "The beast all beasts come from: it walks back through the ages as you "
                        "hurt it. Everything it does echoes. Mind the husks it leaves."),
    # M31.5
    "first_blob": (800, "The first life, crawling out of the first sea. Left alone it evolves."),
    "first_crawler": (1000, "A blob that was left alone. Kill it before it becomes a beast."),
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
    "love_cuddles": "defeat Love & Cuddles",
    "the_fallen": "defeat The Fallen",
    "mycelium_amanita": "defeat Mycelium (the fly agaric)",
    "mycelium_inkcap": "defeat Mycelium (the shaggy ink cap)",
    "mycelium_puffball": "defeat Mycelium (the giant puffball)",
    "necromancer": "defeat More than Death",
    "cavalry": "break the seven seals and defeat the Four Horsemen",
    "host_of_feast": "silence the seven bandstands and defeat the Host of the Feast",
    "ancestor": "hunt the seven great beasts and defeat the Ancestor",
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
                       "swamp": 0.9, "mushroom": 1.1,
                       "paradise": 1.0,     # (M29.2, mine; packs are bigger there: ZONE_TOUGH)
                       "pangaea": 1.0}      # (M31.2, mine; each type on its own ring)
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
# (M29: a built zone is placed from the actual coast instead, below; this
# is still where the unbuilt ones are reserved.)
CARDINAL_REGION_DISTANCE = 1.35

# --- The ocean zones (M29, design/OCEAN.md) --------------------------------------
# Four islands out in the ocean, one due N/E/S/W, reached by water walking
# (Adventurer's Glory). Fixed places (user): Paradise north, Pandemonium (hell) south,
# Pangaea (the past: deep time, M31) west, the Future east. Only the zones listed in OCEAN_ZONES are
# built; the others' places stay open sea.
ZONE_PLACES = {"paradise": "N", "pandemonium": "S", "pangaea": "W", "future": "E"}
OCEAN_ZONES = ("paradise", "pandemonium", "pangaea")
# Each zone is one island ZONE_RADIUS tiles across (half: about 40 s to
# cross), its coast wandering by up to ZONE_COAST_AMPLITUDE of that (fBm,
# ZONE_COAST_SCALE tiles across). Its centre is put far enough out that its
# near shore is at least ZONE_GAP tiles past the main island's farthest
# land within ZONE_FAN radians of its direction (about a minute of water
# walking at 8.5 tiles/s).
ZONE_RADIUS = 350
ZONE_COAST_AMPLITUDE = 0.15
ZONE_COAST_SCALE = 260
ZONE_GAP = 500
ZONE_FAN = 0.45
# A zone is hidden on the maps until a player has been this many tiles from
# its shore (user: "hidden until found"); then its outline and name show.
ZONE_FOUND_RANGE = 120
# The banner the first time a player sets foot on a zone: its name, and this.
ZONE_ARRIVAL = {"paradise": "where the angels sing",
                "pandemonium": "where the feast never ends",
                "pangaea": "where the world began"}

# Paradise (M29.1, OCEAN.md 3). Its land: soft cloud ground, puffier drifts
# where the detail field is above PARADISE_DRIFT_MIN, blossom trees in
# clumps, marble columns standing and fallen (chances per tile).
PARADISE_DRIFT_MIN = 0.70
PARADISE_TREE_MIN = 0.67          # detail below 1 - this: a blossom grove ...
PARADISE_TREE_CHANCE = 0.4        # ... where this many tiles are trees
PARADISE_COLUMN_CHANCE = 0.004
PARADISE_FALLEN_CHANCE = 0.003
# The ocean round it fades into a cloud bank this many tiles wide.
PARADISE_CLOUD_BANK = 22
# The summit court (the boss's arena, sealed until the seventh seal): an
# oval of these radii at the island's centre, walled, its gate facing the
# Gate; terraces (rings of marble steps) round it this many tiles out.
PARADISE_COURT_RADII = (92, 62)
PARADISE_COURT_GATE = 7           # the gate's width, tiles
PARADISE_TERRACES = (10, 22, 34)
# Marble roads (half-width, tiles) lined with gold posts every
# PARADISE_POST_EVERY tiles; the main road meanders by up to
# PARADISE_ROAD_SWAY tiles between the Gate and the court.
PARADISE_ROAD_W = 1.6
PARADISE_POST_EVERY = 8
PARADISE_ROAD_SWAY = 18
# The river of blood (half-width) from the court down to the sea.
PARADISE_RIVER_W = 2.6
PARADISE_RIVER_SWAY = 26
# How many of each landmark, and their spacing (tiles between footprints).
PARADISE_CHOIRS = 5
PARADISE_FONTS = 10
PARADISE_STATUES = 14
PARADISE_SITE_GAP = 14

# Pandemonium (M30.1, OCEAN.md 13): black obsidian veined with gold. Its
# ground: gold veins where the detail field is within PANDEMONIUM_VEIN of
# its middle (thin wandering lines), coin heaps in clumps (detail above
# PANDEMONIUM_HEAP_MIN, that share of tiles) with loose coins round them,
# lone braziers and crimson banners (chances per tile).
PANDEMONIUM_VEIN = 0.012
PANDEMONIUM_HEAP_MIN = 0.74
PANDEMONIUM_HEAP_CHANCE = 0.3
PANDEMONIUM_COINS_MIN = 0.69
PANDEMONIUM_BRAZIER_CHANCE = 0.003
PANDEMONIUM_BANNER_CHANCE = 0.002
# The sea round it turns wine-dark this many tiles out, and the land's
# last PANDEMONIUM_BEACH tiles are a beach of gold coins.
PANDEMONIUM_WINE_SEA = 22
PANDEMONIUM_BEACH = 4
# The palace's great hall (the boss's arena, sealed until the seventh
# bandstand falls silent, M30.4): an oval of these radii at the bottom of
# the pit, walled, its gate facing the pier; the wine lake round it this
# many tiles wide; gold-leaf terrace edges stepping up out of the pit this
# many tiles out from the wall (the ground is darker below
# PANDEMONIUM_DEEP, the pit's floor).
PANDEMONIUM_HALL_RADII = (76, 50)
PANDEMONIUM_HALL_GATE = 7
PANDEMONIUM_LAKE = 14
PANDEMONIUM_TERRACES = (22, 48, 80, 118, 160)
PANDEMONIUM_DEEP = 48
# Gilded avenues (half-width) lit by lanterns every PANDEMONIUM_LANTERN_EVERY
# tiles; the avenue from the pier meanders by up to PANDEMONIUM_ROAD_SWAY;
# the ring avenue runs just outside this terrace (index into the above).
PANDEMONIUM_ROAD_W = 1.6
PANDEMONIUM_LANTERN_EVERY = 9
PANDEMONIUM_ROAD_SWAY = 20
PANDEMONIUM_RING_TERRACE = 2
# The river of wine (half-width): from the wine press down into the lake.
PANDEMONIUM_RIVER_W = 2.4
PANDEMONIUM_RIVER_SWAY = 22
# How many of each, and the spacing (tiles between footprints). The seven
# bandstands keep PANDEMONIUM_BANDSTAND_GAP apart (like the seven seals).
PANDEMONIUM_TABLES = 22
PANDEMONIUM_FOUNTAINS = 10
PANDEMONIUM_STATUES = 16
PANDEMONIUM_BANDSTANDS = 7
PANDEMONIUM_BANDSTAND_GAP = 60
PANDEMONIUM_SITE_GAP = 12

# Pangaea (M31.1, OCEAN.md 24): deep time, jungle and fire. RINGS OF AGES
# (user): walking inland goes back in time. A tile's depth is its distance
# from the centre over the coast's there (0 at the centre, 1 at the shore),
# wobbled by up to PANGAEA_RING_WOBBLE (fBm, PANGAEA_RING_SCALE tiles
# across); under PANGAEA_RINGS[0] it's the heart (the oldest age: ash,
# horsetails and scale trees round steaming pools, under the volcano),
# under [1] the middle (the dinosaurs' jungle), past it the shore ring (the
# great mammals' fern meadows). Each ring's name comes up the first time a
# player walks into it (PANGAEA_AGES: title, subtitle; the shore's is the
# island's arrival banner).
PANGAEA_RINGS = (0.36, 0.68)
PANGAEA_RING_WOBBLE = 0.035
PANGAEA_RING_SCALE = 90
PANGAEA_AGES = (("THE FIRST AGE", "where the oldest things still crawl"),
                ("THE AGE OF GIANTS", "the dinosaurs' jungle"),
                ("THE AGE OF BEASTS", "the great mammals' meadows"))
# Its ground, ring by ring (the detail field: PANGAEA_DETAIL_SCALE tiles
# across). Shore: fern meadow, tall ferns where the detail field is above
# [0], jungle trees in clumps above [1] (that share of tiles [2]), lone
# cycads [3] and rocks [4]. Middle: jungle floor, tall ferns above [0],
# giant ferns above [1] ([2] of them), jungle trees above [3] ([4]), lone
# cycads [5]. Heart: ash, horsetail groves above [0], scale trees above
# [1] ([2]); cinders and basalt boulders ([3] of tiles) on the volcano's
# cone. Amber outcrops: where a small-scale field is above PANGAEA_AMBER[0]
# in the heart and the middle ring, [1] of those tiles (clusters of a few).
PANGAEA_DETAIL_SCALE = 26
PANGAEA_SHORE = (0.62, 0.73, 0.35, 0.004, 0.003)
PANGAEA_MIDDLE = (0.55, 0.60, 0.32, 0.68, 0.30, 0.008)
PANGAEA_HEART = (0.60, 0.70, 0.22, 0.02)
PANGAEA_AMBER = (0.87, 0.55, 7)
# The land's last PANGAEA_BEACH tiles are a black-sand beach.
PANGAEA_BEACH = 5
# The caldera (the Ancestor's arena, sealed by a curtain of fire until the
# seventh great beast falls, M31.4): an oval of these radii at the centre,
# inside the volcano's rim (PANGAEA_RIM tiles thick) with its gate (the
# curtain, this wide) facing the main island; lava lakes inside (how many,
# their radius range); the cone's cinder slopes PANGAEA_CONE tiles out past
# the rim.
PANGAEA_CALDERA_RADII = (70, 52)
PANGAEA_RIM = 4
PANGAEA_CALDERA_GATE = 7
PANGAEA_CALDERA_LAKES = (4, (4.0, 7.0))
PANGAEA_CONE = 26
# Lava rivers: PANGAEA_LAVA_RIVERS run down from vents on the cone (the
# first all the way to the sea, the others ending in fields of cooled
# basalt in the middle ring), meandering by PANGAEA_LAVA_SWAY; molten
# (impassable; shots fly over it) out to PANGAEA_LAVA_W[0] tiles from its
# line, a burning crust out to [1]. Where a trail crosses it, a crossing of
# cooled rock. The sea steams within PANGAEA_STEAM tiles of its mouth.
PANGAEA_LAVA_RIVERS = 3
PANGAEA_LAVA_SWAY = 34
PANGAEA_LAVA_W = (1.9, 3.1)
PANGAEA_BASALT_FIELD = (9.0, 14.0)
PANGAEA_STEAM = 14
# Game trails (half-width, beaten earth): from the sea-beast skeleton to the
# caldera's curtain (meandering by PANGAEA_TRAIL_SWAY), a ring trail at
# depth PANGAEA_RING_TRAIL, spurs to the landmarks.
PANGAEA_TRAIL_W = 1.4
PANGAEA_TRAIL_SWAY = 24
PANGAEA_RING_TRAIL = 0.52
# How many of each, and the spacing (tiles between footprints): nests and
# bones (giant ribcages and skulls, cover), tar pits (some with a beast
# half-sunk in them: PANGAEA_TAR_BONES of them), steaming pools.
PANGAEA_NESTS = 10
PANGAEA_BONES = 14
PANGAEA_TAR_PITS = 14
PANGAEA_TAR_BONES = 0.4
PANGAEA_POOLS = 10
PANGAEA_SITE_GAP = 12
# The land's dangers (systems/pangaea.py; numbers mine). A hero standing on
# the lava's crust burns: PANGAEA_CRUST[0] damage every [1] s (an enemy
# too, not a boss). Tar: a hero sinks in, slowed from x TAR[0] when they
# step in to x [1] after [2] s in it (a roll carries you out at full
# length); an enemy in it runs at x [3] (its whole clock).
PANGAEA_CRUST = (7.0, 0.25)
TAR = (0.55, 0.22, 1.6, 0.45)
# Lava bombs: the volcano lobs a volley at a hero in the heart every
# LAVA_BOMB_EVERY[0] s (in the middle ring [1]; never on the shore ring or in
# the caldera), give or take [2]. A volley (LAVA_BOMB) is [0] bombs -- one
# where the hero stands, the rest [1] tiles round -- marked [2] s before
# they land: each a blast of radius [3] for [4], leaving a splash of burning
# rock (radius [5], [6] s, [7] every 0.5 s). Damage scales like an enemy's
# (the players' level, the difficulty, the zone's toughness).
LAVA_BOMB_EVERY = (9.0, 16.0, 3.0)
LAVA_BOMB = (3, (3.0, 7.0), 1.8, 2.2, 22.0, 1.5, 4.0, 4.0)
# Pangaea's enemies' shots (M31.2, ai/pangaea.py); each "_echo" is the same
# shot played again by an echo, drawn faded.
PANGAEA_SHOTS = {
    "spear": ShellSpec(speed=20.0, damage=14, max_range=17.0, damages_terrain=False,
                       look="spear", sound="bow"),
    "spear_echo": ShellSpec(speed=20.0, damage=14, max_range=17.0, damages_terrain=False,
                            look="spear_echo", sound="bow"),
    "bolas": ShellSpec(speed=12.0, damage=8, max_range=14.0, damages_terrain=False,
                       look="bolas", sound="bow"),
    "bolas_echo": ShellSpec(speed=12.0, damage=8, max_range=14.0, damages_terrain=False,
                            look="bolas_echo", sound="bow"),
    # M31.4: the Ancestor's spit fans, an age each (and their echoes, faded).
    "bone_shard": ShellSpec(speed=13.0, damage=16, max_range=22.0, damages_terrain=False,
                            look="bone_shard", sound="bow"),
    "bone_shard_echo": ShellSpec(speed=13.0, damage=16, max_range=22.0, damages_terrain=False,
                                 look="bone_shard_echo", sound="bow"),
    "boiling_spit": ShellSpec(speed=10.0, damage=20, max_range=18.0, damages_terrain=False,
                              look="boiling_spit", sound="orb"),
    "boiling_spit_echo": ShellSpec(speed=10.0, damage=20, max_range=18.0, damages_terrain=False,
                                   look="boiling_spit_echo", sound="orb"),
    "acid_spit": ShellSpec(speed=15.0, damage=12, max_range=22.0, damages_terrain=False,
                           look="acid_spit", sound="orb"),
    "acid_spit_echo": ShellSpec(speed=15.0, damage=12, max_range=22.0, damages_terrain=False,
                                look="acid_spit_echo", sound="orb"),
    # M31.5: the first life's ring of spray as it bursts up (DIVE).
    "spray": ShellSpec(speed=11.0, damage=12, max_range=11.0, damages_terrain=False,
                       look="spray", sound="orb"),
    "spray_echo": ShellSpec(speed=11.0, damage=12, max_range=11.0, damages_terrain=False,
                            look="spray_echo", sound="orb"),
}
# The angels' shots (M29.2, ai/paradise.py): serene, slow notes, rings and
# orbs of light; unveiled, the seraph's spirals of blood and fire.
# The Beloved's glitter (M30.3, ai/pandemonium.py).
PANDEMONIUM_SHOTS = {
    "glitter": ShellSpec(speed=7.0, damage=8, max_range=14.0, damages_terrain=False,
                         look="revel_glitter", sound="orb"),
}
PARADISE_SHOTS = {
    "note": ShellSpec(speed=6.0, damage=6, max_range=16.0, damages_terrain=False,
                      look="lyre", sound="orb"),
    "light": ShellSpec(speed=4.5, damage=7, max_range=18.0, damages_terrain=False,
                       look="light", sound="orb"),
    "orb": ShellSpec(speed=5.0, damage=8, max_range=20.0, damages_terrain=False,
                     look="light", sound="orb"),
    "blood": ShellSpec(speed=7.0, damage=8, max_range=20.0, damages_terrain=False,
                       look="blood", sound="fizzle"),
    "fire": ShellSpec(speed=7.0, damage=8, max_range=20.0, damages_terrain=False,
                      look="ember", sound="fizzle"),
    # M29.3: a martyr's arrows thrown back, a chorister's shriek, a leviathan's spit.
    "arrow": ShellSpec(speed=14.0, damage=7, max_range=18.0, damages_terrain=False,
                       look="arrow", sound="bow"),
    "shriek": ShellSpec(speed=6.5, damage=7, max_range=14.0, damages_terrain=False,
                        look="shriek", sound="orb"),
    "spit": ShellSpec(speed=9.0, damage=9, max_range=18.0, damages_terrain=False,
                      look="blood", sound="fizzle"),
}

# M29.4: the quest (OCEAN.md 5). The seven seals: each in a clearing of
# marble (SEVEN_SEAL_CLEARING tiles across, half) spread over the island at
# least SEVEN_SEAL_GAP tiles apart; stand within SEVEN_SEAL_RADIUS of one for
# SEVEN_SEAL_TIME s in all to break it (user: ~8 s); with nobody there it
# mends at x SEVEN_SEAL_HEAL. Every SEVEN_SEAL_WAVE s of it, a wave of
# SEVEN_SEAL_WAVE_SIZE angels (SEVEN_SEAL_ANGELS) comes at you from
# SEVEN_SEAL_WAVE_RANGE tiles out, unveiling as they come; SEVEN_SEAL_GUARDS
# serene ones stand round each seal from the start.
SEVEN_SEAL_CLEARING = 6
SEVEN_SEAL_GAP = 60
SEVEN_SEAL_RADIUS = 3.5
SEVEN_SEAL_TIME = 8.0
SEVEN_SEAL_HEAL = 0.5
SEVEN_SEAL_WAVE = 2.7
SEVEN_SEAL_WAVE_SIZE = (2, 3)
SEVEN_SEAL_WAVE_RANGE = (9.0, 13.0)
SEVEN_SEAL_ANGELS = ("cherub", "lamb", "halo", "ophan", "censer_bearer", "dove", "dove")
SEVEN_SEAL_GUARDS = 3
SEVEN_SEAL_GUARD_ANGELS = ("cherub", "lamb", "watcher", "martyr", "bowl_bearer")
# Each broken seal turns the sky a shade redder (user; mine: the whole view
# over Paradise is multiplied by this colour, a step per seal).
SKY_TINT_STEP = (0, 7, 9)          # off green and blue per seal (of 255)

# M30.4: Pandemonium's quest (OCEAN.md 16). Silence the seven bandstands:
# stand within BANDSTAND_RADIUS of a stage's instruments for BANDSTAND_TIME s
# in all to smash them (user: ~8 s); step off and the smashing pauses (the
# seals' survive circle; mine: it doesn't mend). The moment you start, its
# group frenzies and the song carries the frenzy one last time (REVEL[2]).
# A silenced stage plays no more: it carries no frenzy, doesn't double how
# close you may come, doesn't tempt, and its lanterns go out; and for each
# silenced stage your temptation fills SILENCE_TEMPT slower (user: the island
# quieter, temptation slower; mine: 10% each).
BANDSTAND_RADIUS = 3.5
BANDSTAND_TIME = 8.0
SILENCE_TEMPT = 0.10

# M30.4: THE HOST OF THE FEAST, form 1: the gracious host (OCEAN.md 17.1;
# ai/feast.py). The hall is a new room each phase (100-67-33%): the banquet,
# the ballroom, the vault. He dances the whole fight: a waltz round his
# partner (HOST_WALTZ: speed, the round's radii (x, y), a turn's radius,
# turns a s, s before he reverses, how fast the round's middle follows his
# partner -- faster, tiles/s per tile, while he's far: the hall is 152 x 100
# tiles); only the toast and the beckoning plant him. Damages per hit at
# level 1 (x the enemy damage scaling, BOSS_DMG_MULT). Numbers mine.
HOST_HIT_RADIUS = 2.2
HOST_WALTZ = (5.5, (13.0, 8.0), 1.2, 0.7, 9.0, 3.0, 0.6)
# His charm (user: ~6 tiles): within HOST_CHARM[0] your temptation fills
# (full in HOST_CHARM[1] s right beside him); full, you're swept into his
# dance (TEMPT[5] s): drifting at him, and if you reach him before you roll
# out he spins you away with a free hit (HOST_CHARM[2] damage, HOST_CHARM[3]
# tiles away).
HOST_CHARM = (6.0, 3.0, 30, 4.0)
# Courses served (the banquet's signature): HOST_COURSES[0] dishes a serving,
# HOST_COURSES[1] s apart, sliding at [2] tiles/s for at most [3] s (or to
# where you were), [4] damage if one runs into you; in the later rooms
# demon waiters bring them in from [5] tiles out. Soup: a scald pool
# (radius from, x grown over its life, life, s between ticks, damage);
# roast: a ring of bones; jellies: blobs hopping at you (blobs, hops each,
# s a hop, tiles a hop, landing radius, damage); the cake tower topples along
# a line (length, s shown, half-width, damage).
HOST_COURSES = (3, 0.55, 11.0, 2.2, 8, 16.0)
HOST_SOUP = (1.2, 2.0, 6.0, 0.4, 6)
HOST_ROAST = 12
HOST_JELLY = (3, 3, 0.75, 3.0, 1.3, 12)
HOST_CAKE = (9.0, 0.8, 1.2, 22)
# The dance floor (the ballroom's): HOST_DANCE[0] beats, [1] s each; squares
# of [2] tiles, the floor [3] x the hall across; each beat's step pattern
# shows a beat ahead, and when it lands every unlit square burns ([4]).
HOST_DANCE = (6, 1.25, 4, (0.8, 0.72), 18)
# The vault's gold: heaps sliding in like walls from both sides of you,
# closing your lane (heaps a slide, length, speed, half-thickness, damage on
# contact, tiles out they start), coins pouring onto
# marked circles (circles, s shown, radius, damage), and gold tossed to you
# (coins, s they lie there, s of the gilding, x your damage, temptation each).
HOST_WALLS = (2, 11.0, 4.0, 1.0, 10, 14.0)
HOST_POUR = (6, 1.0, 1.6, 16)
HOST_TOSS = (3, 6.0, 5.0, 1.5, 25.0)
# Toasts (every room): planted, the glass raised HOST_TOAST[0] s, then a wave
# of wine floods out ([1] tiles at [2] tiles/s; [3] damage, [4] temptation:
# roll through it) and every guest in the hall frenzies.
HOST_TOAST = (1.0, 32.0, 10.0, 14, 15.0)
# The four dance figures. Grand spin: a spinning glide (s, speed, s a turn,
# cutlery a turn). The beckoning: a bow (s), the pull (s, reach, tiles/s;
# walk or roll against it), then a sweeping slash (reach, half-angle deg,
# damage). Carving set: fans that curve across each other (volleys, knives a
# fan, fan's degrees, curve rad a tile, s between). Chandeliers: dropped on
# marked spots (drops, s shown, radius, damage), leaving broken glass that
# cuts (radius, s, s between ticks, damage).
HOST_SPIN = (3.0, 9.0, 0.45, 10)
HOST_BECKON = (0.7, 1.1, 14.0, 4.5, 5.5, 70.0, 30)
HOST_CARVING = (2, 7, 80.0, 0.07, 0.6)
HOST_CHANDELIERS = (6, 1.2, 1.8, 26, 1.6, 4.0, 0.5, 6)
# The guests: a group at each room's edges in the trance (feasters in the
# banquet, dancers in the ballroom, hoarders in the vault; user). They wake
# if you go near, or when his toast frenzies the hall; each room's group
# leaves with the room and a new one sits down (mine).
HOST_GUESTS = (("glutton", "glutton", "drunkard", "drunkard", "ravenous", "ravenous"),
               ("dancer", "dancer", "dancer", "dancer", "masked_dancer", "masked_dancer"),
               ("hoarder", "hoarder", "hoarder", "hoarder", "gilded_reveller"))

# M30.5: form 2, THE HUNGER (OCEAN.md 17.2; ai/hunger.py). At 0 the mask
# cracks (HUNGER_CRACK s: he can't be hit while the hall falls into the wine
# round him) and he's back with x HUNGER_HP his health (17.3: 14,000 of the
# gracious host's 12,000): four phases (100-75-50-25%), a signature added in
# each -- devour, the maw, teeth in the floor, spilled feast. No charm (user).
# Damages at level 1, x the enemy scaling and his growth. Numbers mine.
HUNGER_CRACK = 3.0
HUNGER_HP = 14000 / 12000
HUNGER_HIT_RADIUS = 2.6
# The hall falls into the wine (user): islands of table, floor and gold
# (centres HUNGER_ISLANDS[0] tiles apart, jittered up to [1], radii [2]) in
# spilt wine that heroes wade at x [3] (user: slowly); he moves through it
# freely.
HUNGER_ISLANDS = (12.0, 3.0, (3.5, 5.5), 0.5)
# He prowls round his prey (tiles/s, about [1] tiles off, turning about now
# and then) -- unless a meal is within [2] tiles: then he goes for it at [3].
HUNGER_PROWL = (4.5, 6.0, 12.0, 5.5)
# Devour (user): whatever he reaches (within [0] of his body) he eats -- his
# guests, the feast's scraps, his own waiters -- and stops to chew it for [4]
# s (mine: time to clear the next one). Each meal heals [1] of his max and
# makes him [2] bigger and stronger, up to [3] meals (17.3); past those he
# still eats, but gains nothing.
HUNGER_DEVOUR = (1.0, 0.03, 0.05, 10, 1.2)
# What there is to eat (mine): HUNGER_FEAST[0] scraps of the collapsed table
# scattered on the islands 6 to [1] tiles from him; HUNGER_GUESTS in pairs
# on the islands [2] tiles out, feasting (in the trance); and every [3] s
# [4] demon waiters bring him a course from [5] tiles out. Walk into a scrap
# or shoot it and it's knocked into the wine.
HUNGER_FEAST = (8, 22.0, (10.0, 20.0), 18.0, 2, 18.0)
HUNGER_GUESTS = ("glutton", "glutton", "ravenous", "ravenous", "drunkard", "drunkard")
# The maw (phase 2 on): a cone shown [0] s, then he inhales for [1] s,
# pulling everything in the cone ([2] tiles, [3] degrees either side) at
# [4] tiles/s. Reach his mouth and you're swallowed: [5] bites of [6] over
# [7] s, then spat out [8] tiles across the hall (in HUNGER_SPAT s).
HUNGER_MAW = (1.0, 1.6, 14.0, 32.0, 6.0, 3, 15, 1.2, 13.0)
HUNGER_SPAT = 0.5
# Teeth in the floor (phase 3 on): [0] waves of [1] lines crossing near you
# ([2] tiles long; one right through you), each shown [3] s, then snapping
# shut ([4] damage within [5] tiles of a line); waves [6] s apart.
HUNGER_TEETH = (3, 3, 22.0, 1.1, 26, 1.0, 0.9)
# Spilled feast (phase 4): [0] gobbets heaved in arcs onto marked spots (one
# on you; [1] s in the air), landing as rotting pools ([2] radius, [3] s)
# that slow (x [4]), burn ([5] every [6] s), fill your temptation ([7] a
# tick) and frenzy the guests within [8] tiles of them.
HUNGER_SPILL = (5, 1.1, 2.4, 8.0, 0.6, 6, 0.5, 3.0, 4.0)
# Lunge bite: a marked line ([0] s, at most [2] tiles), a lunge along it at
# [1] tiles/s (hurting [5] whoever's within [3] of his way), ending in a
# bite ([4] tiles round his mouth, [6] damage).
HUNGER_LUNGE = (0.7, 28.0, 18.0, 1.4, 3.0, 14, 34)
# Tongue lash: aimed ([0] s), it shoots out at [1] tiles/s up to [2] tiles;
# what it catches (within [5]) is dragged back at [3] tiles/s and bitten
# ([4]) -- unless a roll pulls you free. A meal it catches, he eats.
HUNGER_TONGUE = (0.6, 30.0, 16.0, 9.0, 30, 0.8)
# Belly quake: planted [0] s, then [1] shockwave rings [2] s apart rolling
# out at [3] tiles/s to [4] tiles ([5] damage; roll through them).
HUNGER_QUAKE = (0.9, 3, 0.6, 9.0, 26.0, 16)
# Bone scraps: [0] fans of [1] bones ([2] degrees), [3] s apart; where a bone
# comes down it lies as clutter you trip over ([4] radius, [5] s, x [6]
# speed), at most HUNGER_CLUTTER of them about.
HUNGER_BONES = (3, 7, 70.0, 0.5, 0.9, 10.0, 0.65)
HUNGER_CLUTTER = 40
FEAST_SHOTS = {
    "cutlery": ShellSpec(speed=7.5, damage=9, max_range=20.0, damages_terrain=False,
                         look="cutlery", sound="axe"),
    "bone": ShellSpec(speed=7.0, damage=8, max_range=12.0, damages_terrain=False,
                      look="bone", sound="axe"),
    "carving": ShellSpec(speed=8.0, damage=12, max_range=24.0, damages_terrain=False,
                         look="carving", sound="swing"),
    "scrap": ShellSpec(speed=9.0, damage=10, max_range=13.0, damages_terrain=False,
                       look="bone", sound="axe"),        # (M30.5: the hunger's bone scraps)
}

# M29.4: the Serene Cavalry (OCEAN.md 6.1; ai/bosses.Cavalry). Four riders
# on one health bar, always riding: they gallop round you (a circle, a
# figure-eight, crossing lanes; a new pattern every CAV_RIDE[3] s) at
# CAV_RIDE[0] tiles/s, slowed to x CAV_RIDE[1] in a move but never stopped;
# the ride's middle follows the target at CAV_RIDE[2] tiles/s. A rider that
# runs into a hero tramples it (CAV_GALLOP: damage, push, at most every s).
# Damages are per hit at level 1 (x the enemy damage scaling, BOSS_DMG_MULT).
CAV_RIDE = (11.0, 0.6, 4.0, 7.0, (15.0, 9.0))   # speed, x in a move, middle's speed,
                                                # s per pattern, the ride's radii (x, y)
CAV_HIT_RADIUS = 1.4               # tiles: a rider and its horse
CAV_GALLOP = (8, 1.5, 1.2)        # trampled: damage, push tiles, s apart
CAV_FORMATION = (1.3, 24.0, 30.0, 4.0, 22, 2.0)   # lanes shown s, charge speed, lane length,
                                                  # lanes apart, damage, push
CAV_LANCES = (0.8, 7.0, 5.0, 12.0, 14, 0.5, 1.2)  # in the air s, the cage's half-width and
                                                  # half-height round you, s a pillar stands,
                                                  # a fence's sting, s apart, push back tiles
CAV_HYMN = (7.0, 0.3, 0.003, 6.0, 0.015, 4.0, 2.5)  # s, x damage taken while together, x max
                                                    # HP healed a s, "together" within this of
                                                    # the middle; the lead singer's chord breaks
                                                    # after this x max HP; a hero this close
                                                    # pulls a rider away; s it's thrown out
CAV_WINDS = (4, 1.4, 0.5, 5.0, 2, 1.6, (13.0, 8.0))  # gusts, s each, s shown before, push
                                                     # tiles/s, calm spots, their radius, the
                                                     # riders' corners round you
CAV_CAROUSEL = (3.2, 14.0, 4.0, 0.7)   # s, radius from, to, s between each rider's shots
CAV_HOOFS = (4.0, 0.9, 10)              # s, s between rings, shots a ring
CAV_HALOS = (1.0, 8, 1.6, 2, 0.6, 14)   # marked s, halos a volley, their radius, volleys,
                                        # s between, damage
CAV_TRAMPLE = (0.8, 24.0, 26.0, 24, 2.5)  # line shown s, speed, length, damage, push
CAV_SHOTS = {
    "light": ShellSpec(speed=8.0, damage=9, max_range=22.0, damages_terrain=False,
                       look="light", sound="orb"),
    "hoof": ShellSpec(speed=5.5, damage=8, max_range=14.0, damages_terrain=False,
                      look="light", sound="orb"),
}

# M29.5: form 2, THE FOUR HORSEMEN (OCEAN.md 6.2; ai/horsemen.py). At 0 the
# cavalry unveils (HORSEMEN_UNVEIL s) into four, each with its own health
# (config.ENEMIES; user's proposal: 6,000 each) and kit; a fallen one's kit
# passes to the others. Numbers mine, per hit at level 1 (x the enemy damage
# scaling, BOSS_DMG_MULT). The cavalry still rides them (CAV_RIDE).
HORSEMEN_UNVEIL = 2.5
HORSEMEN = (1.6,)                  # a Horseman's hit radius, tiles
HORSEMEN_SHOTS = {
    "crown": ShellSpec(speed=18.0, damage=10, max_range=24.0, damages_terrain=False,
                       look="crown", sound="bow"),
    "arrow": ShellSpec(speed=16.0, damage=7, max_range=22.0, damages_terrain=False,
                       look="longarrow", sound="bow"),
    "wave": ShellSpec(speed=9.0, damage=10, max_range=14.0, damages_terrain=False,
                      look="blood", sound="fizzle"),
    "scythe": ShellSpec(speed=10.0, damage=10, max_range=16.0, damages_terrain=False,
                        look="slash", sound="bow"),
}
# Conquest.
CROWN = (0.5, 3, 16.0)             # tell s, arrows, over this many degrees
CROWN_MULT = 0.5                   # crowned, your hits do x this (a roll knocks it off)
FANS = (5.0, 3, 30.0, 18.0)        # (passive) a fan every this many s, arrows, degrees, at
                                   # a hero within this far
BANNER = (0.8, 2.5, 0.35, 7.0, 0.7, 6, 2)   # planting s; its burning ground from this radius,
                                         # growing this many tiles/s up to this; burns every
                                         # this many s (the banner spec's damage x its owner's);
                                         # at most this many standing (a new one: the oldest falls)
LAP = (4.0, 15.0, 22.0, 0.8, 2)    # s, the lap's radius round you, speed, s between
                                   # volleys, arrows a volley
# War.
SWEEP = (0.5, 3, 4.5, 120.0, 22, 7)      # tell s, slashes, reach, arc degrees, damage,
                                         # shots in each wave of blood
BLOOD_CHARGE = (0.8, 22.0, 16.0, 3, 20, 1.5, 0.12, 5.0)  # line shown s, speed, length,
                                         # charges, damage, push, s between burning patches,
                                         # their life s
STRIFE = (18.0, 3, 6)              # (passive) a wave of unveiled angels every this many s,
                                   # this many, while fewer than this many of its are about
HM_DUEL = (0.8, 6.0, 8.0, 2.0, 18, 1.6)    # tell s, the ring's radius (at least), s, x damage
                                         # both ways inside, the sting breaking out, s between
                                         # its slashes
# Famine.
SCALES = (8.0, 0.03, 20.0)         # (passive) weighs you every this many s: the lighter (less
                                   # health as a share of max) loses this share of its max HP
                                   # to the other (who gains just that); heroes within this far
HUNGER = 8.0                       # (passive) no healing within this far of it
WEIGHTS = (1.2, 3, 5.0, 1.4, 22)   # marked s, weights, spread tiles, crush radius, damage
HM_PLAGUE = (0.6, 6, 18)          # tell s, locusts, at most this many about
# Death.
HADES = (0.4, 1.8, 6.0, 1.5)       # (passive) a pool of darkness every this many s behind it:
                                   # radius, life s, pull tiles/s (and no healing in it)
QUARTER = (2.0, 16.0, 28)          # each quarter darkened this many s; radius; damage
HM_REAP = (3.0, 7.0, 4.2, 22, 0.5, 3)  # s, the scythe's spin rad/s, reach, damage, s before the
                                    # same hero again, crescents thrown each half-turn
SHADE_LIFE = 10.0                  # (passive, the dead rise) a pale shade lasts this long...
SHADES_MOST = 6                    # ...and no more than this many are up at once
# Their relics (M29.5; the powers grow +10% a level, GEAR.md 21.1).
U_CONQUEST = (8.0, 0.5, 0.75)      # Crown of Conquest: s before the same enemy again; a crowned
                                   # enemy deals x this (a boss x this)
U_BLOOD_RING = (20.0, 10.0, 5.0)   # Ring of Blood: every s, at an elite or boss within this far,
                                   # the ring's radius (at least)
U_SCALES = (8.0, 10.0, 0.5 / 3)    # The Black Scales: every s, the nearest enemy within this far;
                                   # a boss weighs x this of the power
U_PALE = (3, 15, 6.0, 0.8)         # Pale Rider's Cloak: shades at most, their bite, speed, s
                                   # between bites
# M30.5: the Host of the Feast's relics (the powers grow +10% a level).
U_BIB = (0.03, 10.0, 5, 8.0, 0.9, 12)   # Glutton's Bib: heal (x max HP) a scrap; s a stack lasts;
                                        # stacks at most; s a scrap lies; reach to eat it; at most
                                        # this many lying
U_GOBLET = (12.0, 8.0, 16.0, 3.0, 0.6, 0.3, 1.0)   # The Host's Goblet: every s (when an enemy is
                                        # within reach); reach; tiles/s; s drunk (bosses half);
                                        # x a drunk enemy's clock; its miss chance; push
U_SHOES = 8                             # Dancing Shoes: pieces of cutlery a spin
U_GILDED = (6.0, 4.0, 6.0, 0.9, (2.0, 4.0))   # Gilded Ring: s between coins; s gilded; s a coin
                                        # lies; reach to catch it; how far it's tossed
# M31.5: the Ancestor's relics (the powers grow +10% a level).
U_HERD = (10.0, 10.0, 3.0, 14.0, 14.0, 1.4, 2.0)   # Spirit Herd: every s (once an enemy is within
                                        # this far); it sets off this far behind you, runs this
                                        # far past you at this tiles/s, this wide; pushes aside
U_SKULL = (15.0, 6.0, 100, 8.0, 1.5, 0.5)   # Tyrant Skull: every s (once an enemy is within this
                                        # far); a cone this many degrees, this long; s frozen in
                                        # fear (a boss: held this long)
U_SWARM = (12.0, 12.0, 12.0, 1.5, 3.0, 0.5)   # Swarm Ring: every s (once an enemy is within this
                                        # far); the river this long, this far either side, this
                                        # many s; a sting every s
U_CONCH = (3.0, 12)                     # Echo Conch: s later; attacks waiting at most

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
# The words every Mycelium quest shares (M26): nothing in them tells which
# mushroom waits.
MYCELIUM_LINES = (
    ("offer", ("Something's growing under the whole biome.",
               "Threads. Miles of them. All one thing.",
               "Mycelium, the old folk call it.",
               "The nodes pulse where the threads meet.",
               "Stand on one till it's dug out. Sever four.",
               "The sporelings will come up the threads at you.")),
    ("progress", ("{left} more nodes to sever.",
                  "Hold your ground on the node. It takes a while.")),
    ("done", ("Four! It felt that. It's coming up.",
              "Where? Where it fruits. Look for MYCELIUM on your map.",
              "What does it look like? Nobody who's seen it says.",
              "Watch what the nodes spilled, maybe.")),
    ("fight", ("Mycelium's up! Go!",)),
    ("cleared", ("It's quiet down there now.",
                 "There's more than one, you know. There always is.")),
)

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
    # M25.2: a "destroy" quest (systems/quests._break_caches): the camp's
    # spots hold nut caches, each at the end of a trail of nut shells and
    # guarded by rabid squirrels; break one (it's a tile: shoot it, hit
    # it) to count it. The lair is the hollow oak (world/landmarks._hollow_oak).
    "forester": QuestSpec(
        title="Break the Caches", biome="forest", giver="forester",
        giver_sprite="forester", camp="forester_camp", lair="hollow_oak",
        target="rabid_squirrel", count=4, boss="love_cuddles", goal="Caches broken {n}/{count}",
        camp_name="FORESTER", lair_name="THE HOLLOW OAK", kind="destroy",
        lines=(
            ("offer", ("You there. Seen a squirrel? Pink. Fluffy. A bow.",
                       "Cutest thing in the wood. Don't let it near you.",
                       "It hoards. Nuts, mostly. Also my cleaver.",
                       "Follow the nut shells to its caches and smash them.",
                       "Break four and it'll come out of the hollow oak.",
                       "The squirrels guarding them bite. Hard.")),
            ("progress", ("{left} more caches to break.",
                          "Follow the shells. Squirrels are messy eaters.")),
            ("done", ("Four! Hear that screech? It's coming out.",
                      "The hollow oak. Big trees all round it.",
                      "It buries acorns. Steal them before it digs them up.",
                      "Up a tree? Shoot the trunk till it falls out.",
                      "And mind the wires that glint between the trees.")),
            ("fight", ("Don't let it hug you!",)),
            ("cleared", ("It's... gone? Good. Good.",
                         "I'm sleeping with the lights on anyway.")),
        ),
    ),
    # M25.3: a "fell" quest (systems/quests._fell_trees): the camp's spots
    # hold trees marked with red paint; fell one (shoot it, chop it) to
    # count it -- unless it was a mimic sapling, which rips free and must be
    # killed. The lair is the still grove (world/landmarks._still_grove).
    "lumberjack": QuestSpec(
        title="Fell the Marked Trees", biome="forest", giver="lumberjack",
        giver_sprite="lumberjack", camp="lumber_camp", lair="still_grove",
        target="mimic_sapling", count=4, boss="the_fallen", goal="Marked trees felled {n}/{count}",
        camp_name="LUMBERJACK", lair_name="THE STILL GROVE", kind="fell",
        lines=(
            ("offer", ("Trees in this wood move when you don't look.",
                       "I marked the wrong ones. Red paint, see?",
                       "Fell them. Four will do.",
                       "Some aren't trees at all. Saplings, with teeth.",
                       "If one rips free, finish it.")),
            ("progress", ("{left} more to fell.",
                          "Red paint. You can't miss it.")),
            ("done", ("That's four. Now the big one's awake.",
                      "The Fallen. In the still grove. It looks like a tree.",
                      "It hides among the others. Watch for the eye.",
                      "Its roots crawl under the leaves. Fire keeps them off.",
                      "And when its trunk opens up, think before you shoot.")),
            ("fight", ("Find the eye!",)),
            ("cleared", ("Timber! Ha. Felled at last.",
                         "The grove's just trees again. Probably.")),
        ),
    ),
    # M26: the three Mycelium quests are one "sever" quest (systems/quests
    # ._hold_seals, like "cleanse"), word for word; only the giver differs,
    # and what a severed node spills (the quest's skin: M26.1 red specks).
    # Mycelium nodes pulse under the mushroom biome; stand on one until it's
    # dug out while sporelings crawl up the threads. The lair is just
    # "MYCELIUM" on the map.
    "truffle_hunter": QuestSpec(
        title="Sever the Network", biome="mushroom", giver="truffle hunter",
        giver_sprite="truffle_hunter", camp="spore_camp", lair="amanita_ring",
        target="sporeling", count=4, boss="mycelium_amanita", goal="Nodes severed {n}/{count}",
        camp_name="TRUFFLE HUNTER", lair_name="MYCELIUM", kind="sever", skin="amanita",
        lines=MYCELIUM_LINES,
    ),
    # M26.2: the same quest; its severed nodes spill ink stains.
    "mycologist": QuestSpec(
        title="Sever the Network", biome="mushroom", giver="mycologist",
        giver_sprite="mycologist", camp="spore_camp", lair="inkcap_ring",
        target="sporeling", count=4, boss="mycelium_inkcap", goal="Nodes severed {n}/{count}",
        camp_name="MYCOLOGIST", lair_name="MYCELIUM", kind="sever", skin="inkcap",
        lines=MYCELIUM_LINES,
    ),
    # M26.3: the same quest; its severed nodes spill puffs of dust.
    "forager": QuestSpec(
        title="Sever the Network", biome="mushroom", giver="forager",
        giver_sprite="forager", camp="spore_camp", lair="puffball_field",
        target="sporeling", count=4, boss="mycelium_puffball", goal="Nodes severed {n}/{count}",
        camp_name="FORAGER", lair_name="MYCELIUM", kind="sever", skin="puffball",
        lines=MYCELIUM_LINES,
    ),
    # M27: the main quest's last step -- the plains boss. No giver: his
    # necropolis (world/landmarks._necropolis) stands at the island's centre,
    # its gate sealed with bone until a guardian has fallen in each of the
    # GUARDIANS ring biomes ("finale": systems/quests). Beaten, he gives
    # Adventurer's Glory (end the run from the pause menu) and water walking.
    "necropolis": QuestSpec(
        title="Gain Adventurer's Glory", biome="plains", giver="", giver_sprite="",
        camp="none", lair="necropolis", target="risen_dead", count=5, boss="necromancer",
        goal="Guardians {n}/{count}", camp_name="", lair_name="THE NECROPOLIS",
        kind="finale", lines=(),
    ),
    # M29.4: Paradise's quest (design/OCEAN.md 5), a "seals" quest: the seven
    # seals lie in guarded clearings across the island (world/paradise.Plan);
    # stand at one SEVEN_SEAL_TIME s while angels come at you, unveiling.
    # Its camp is the stairway to nowhere (the fallen angel chained at its
    # foot), its lair the summit court, sealed with golden bars until the
    # seventh seal breaks. Its lines are mine.
    "seven_seals": QuestSpec(
        title="Break the Seven Seals", biome="paradise", giver="fallen angel",
        giver_sprite="fallen_angel", camp="zone", lair="zone", target="cherub", count=7,
        boss="cavalry", goal="Seals broken {n}/{count}",
        camp_name="THE FALLEN ANGEL", lair_name="THE SUMMIT COURT", kind="seals",
        skin="paradise",
        lines=(
            ("offer", ("Another one up the stairs. Look at me.",
                       "Yes. A wing nailed to a post. Their mercy.",
                       "I asked what the white was for. Once.",
                       "Seven seals lie across this island.",
                       "Stand at each until it breaks. It takes a while.",
                       "They'll come for you. Pretty, then not.",
                       "Every seal you break, the sky shows its colour.",
                       "Seven, and the throne has to answer.")),
            ("progress", ("{left} seals still hold.",
                          "Stand in the ring. Step out and it mends.")),
            ("done", ("Seven. Now you see the sky as it is.",
                      "The court at the summit is open.",
                      "Four riders, white as a lie.",
                      "When they sing together, pull them apart.",
                      "And when they plant their lances... run.")),
            ("fight", ("The riders are out! The summit! Go!",)),
            ("cleared", ("The white came off them, didn't it.",
                         "Leave me the post. I'm used to it.")),
        ),
    ),
    # M30.4: Pandemonium's (OCEAN.md 16). The sober man hides under the
    # gilded pier (the camp; its spots are the seven bandstands); the palace
    # is the lair. His lines are mine (the doc gives his character).
    "silence_bandstands": QuestSpec(
        title="Silence the Seven Bands", biome="pandemonium", giver="sober man",
        giver_sprite="sober_man", camp="zone", lair="zone", target="piper", count=7,
        boss="host_of_feast", goal="Bands silenced {n}/{count}",
        camp_name="THE SOBER MAN", lair_name="THE PALACE", kind="bandstands",
        skin="pandemonium",
        lines=(
            ("offer", ("Don't offer me anything. It all turns to ash.",
                       "I woke up. Nobody else ever has.",
                       "Seven bands play out there. The music holds them.",
                       "Stand on a stage and smash the instruments.",
                       "It takes a while. They'll all come for you.",
                       "Every band you silence, the pull gets weaker.",
                       "Silence all seven and he'll have to come out.")),
            ("progress", ("{left} bands still play.",
                          "Stay on the stage. Step off and it stops.")),
            ("done", ("Listen. Nothing. I'd forgotten what that was.",
                      "He's awake, and he's angry. The palace is open.",
                      "He'll smile. He'll pour for you. Don't drink.",
                      "There's a white island up north. Paradise.",
                      "This is its mirror. Same hunger. Better wine.")),
            ("fight", ("He's dancing. Go. Don't let him lead.",)),
            ("cleared", ("Bread. It tastes of bread.",
                         "I'll sit here a while. Thank you.")),
        ),
    ),
    # M31.4: Pangaea's (OCEAN.md 27), a "hunt" with a different great beast
    # at each spot (GREAT_BEASTS, world/pangaea.Plan.hunt). The old painter
    # sits by the fire in the painted caves (the camp); each kill is painted
    # on the deepest wall, and the seventh parts the caldera's curtain of
    # fire (the lair). Her lines are mine (the doc gives what she knows).
    "great_hunt": QuestSpec(
        title="The Great Hunt", biome="pangaea", giver="old painter",
        giver_sprite="old_painter", camp="zone", lair="zone", target="old_tusk", count=7,
        boss="ancestor", goal="Great beasts {n}/{count}",
        camp_name="THE OLD PAINTER", lair_name="THE CALDERA", kind="hunt",
        skin="pangaea", targets=tuple(k for k, *_ in GREAT_BEASTS),
        lines=(
            ("offer", ("Sit. My legs gave up the hunt long ago. My hands didn't.",
                       "Look at the wall. Seven great beasts. Older than the rest.",
                       "Old Tusk. Broken Horn. Long Fang, in the ferns.",
                       "Thunderfoot and Stoneback where the giants walk.",
                       "Glasswing and Deep Claw down by the fire mountain.",
                       "Hunt them. Each one you kill, I paint.",
                       "When the seventh is on the wall, the fire will open.")),
            ("progress", ("{left} great beasts still walk.",
                          "The deep wall waits for them.")),
            ("done", ("Seven. The wall is full.",
                      "Do you hear it? The island remembers. Everything twice.",
                      "That is what the echoes are. Memory.",
                      "The fire mountain is open. The first beast waits there.",
                      "It walks back through the ages as you wound it.",
                      "Look at the deepest wall. I painted the end already.")),
            ("fight", ("It is awake. Go. Strike once, it strikes twice.",)),
            ("cleared", ("You walked to the beginning and back.",
                         "Let me paint you on the wall. Hold still.")),
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
CAMP_FORESTER_RADII = (20, 9)   # the forester's camp: a log pond, woodpiles (M25.2)
# "destroy" quests (M25.2): a nut cache (tiles.NUT_CACHE, CACHE_HP) at each
# spot, at the end of a trail of nut shells CACHE_TRAIL = (fewest, most
# tiles long) winding in from wherever, and CARGO_GUARDS of the quest's
# target round it. Breaking one lets CACHE_BURST more out.
CACHE_HP = 160
CACHE_TRAIL = (30, 46)
CACHE_BURST = 2
CACHE_LOOK = 40.0         # (tiles from a hero: a cache is checked)
CAMP_LUMBER_RADII = (20, 9)     # the lumberjack's camp: a pond, sawhorses (M25.3)
# "fell" quests (M25.3): a marked tree (tiles.MARKED_TREE, MARKED_HP) at each
# spot; 1 in SAPLING_EVERY of them (by the seed) is a mimic sapling that rips
# free when felled and counts once it's dead.
MARKED_HP = 120
SAPLING_EVERY = 3
CAMP_SPORE_RADII = (20, 9)      # a Mycelium quest giver's camp (M26)
# "sever" quests (M26): a Mycelium node (tiles.MYC_NODE) at each spot. Stand
# within SEVER_RADIUS tiles of it SEVER_TIME s (in total; nobody on it, it
# heals back SEVER_HEAL x as fast); every SEVER_WAVE s of it, SEVER_WAVE_SIZE
# of the quest's enemies crawl up SEVER_WAVE_RANGE tiles out.
SEVER_RADIUS = 3.2
SEVER_TIME = 16.0
SEVER_HEAL = 0.5
SEVER_WAVE = 5.0
SEVER_WAVE_SIZE = (3, 5)
SEVER_WAVE_RANGE = (6.0, 10.0)

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
# Love & Cuddles' hollow oak (M25.2, world/landmarks._hollow_oak): the oval
# in a wall of oak roots round dead leaves; the great hollow oak in the
# middle (OAK_HOLLOW tiles, w x h); OAK_TREES big climbing oaks (2 x 2
# trunks, a crown round each) on a ring OAK_RING of the way out, never
# within OAK_GATE_GAP tiles of the gate (props["trees"], their middles);
# OAK_STUMPS stumps.
OAK_HOLLOW = (8, 4)
OAK_TREES = 10
OAK_RING = (0.42, 0.72)
OAK_GATE_GAP = 22
OAK_STUMPS = 22
# The Fallen's still grove (M25.3, world/landmarks._still_grove): the oval in
# a thicket round dead leaves and fog; a great fallen trunk across the middle
# (GROVE_LOG tiles long, 2 high, cover); GROVE_TREES lookalike trees at least
# GROVE_TREE_GAP tiles apart (props["trees"]: where each stands, its trunk the
# tile 2 below); GROVE_FIRES fire bowls (props["fires"]); GROVE_STUMPS stumps.
GROVE_LOG = 22
GROVE_TREES = 40
GROVE_TREE_GAP = 9.0
GROVE_FIRES = 8
GROVE_STUMPS = 12
# Mycelium the fly agaric's fruiting ring (M26.1, world/landmarks._amanita_ring):
# the oval in a wall of giant mushrooms round mycelium and spores; NET_RINGS
# fruiting rings (props["rings"]: their nodes; the middle one first, the
# rest round it on a ring NET_RING of the way out), joined by threads
# (props["threads"]: index pairs -- the middle to each, and each to the next
# round); AMANITA_SHROOMS giant mushrooms for cover.
NET_RINGS = 7
NET_RING = 0.55
AMANITA_SHROOMS = 18
# Mycelium the shaggy ink cap's lair (M26.2, world/landmarks._inkcap_ring):
# the oval in a wall of giant mushrooms round mycelium, with patches of old
# cracked paving (ink caps push up through stone) and ink stains, and
# INKCAP_SHROOMS giant mushrooms for cover.
INKCAP_SHROOMS = 16
# Mycelium the giant puffball's lair (M26.3, world/landmarks._puffball_field):
# the oval in a wall of giant mushrooms round mycelium and drifts of spore
# dust, PUFF_BOULDERS clusters of boulders for cover (from the wind and the
# bursts) and PUFF_SHROOMS giant mushrooms.
PUFF_BOULDERS = 12
PUFF_SHROOMS = 8
# More than Life's necropolis (M27, world/landmarks._necropolis): at the
# island's centre, NECRO_RADII (twice a ring lair), its gate to the south
# (runs start NECRO_START tiles below its wall, in sight of the gate). Grave soil and bone litter;
# NECRO_GRAVES gravestones in rows (cover from his gaze), NECRO_TOMBS
# mausoleums (5 x 3), a ritual ring in the middle, NECRO_CORPSES old corpses
# lying about (props["corpses"]); props["graves"]: every gravestone.
NECRO_RADII = (250, 100)
NECRO_START = 9
NECRO_GRAVES = 24                # rows of graves (each 4-7 stones)
NECRO_TOMBS = 10
NECRO_CORPSES = 28
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
    # M25.2 (ai/bosses.LoveCuddles, design/BOSSES.md section 25): the hoard
    # (burying acorns, "bury") runs on a timer all fight; the treetops
    # ("treetop") on one from phase 2; tripwires ("string") on one and the
    # frenzy (a meter) in phase 3.
    "love_cuddles": BossSpec(
        name="Love & Cuddles",
        phases=(
            BossPhase(1.0, (("spin", 2), ("barrage", 3), ("pinecones", 2), ("gang", 1)),
                      rest=1.0),
            BossPhase(0.6, (("spin", 2), ("barrage", 3), ("pinecones", 2), ("gang", 1)),
                      rest=0.85),
            BossPhase(0.3, (("spin", 2), ("barrage", 3), ("pinecones", 2), ("gang", 1)),
                      rest=0.6),
        ),
        loot=2500, achievement="love_cuddles", pages=("love_cuddles", "rabid_squirrel"),
    ),
    # M25.3 (ai/bosses.TheFallen, design/BOSSES.md section 26): it hides
    # among its lookalike trees ("hide") on a timer all fight; its roots
    # ("roots") on one from phase 2; its maw ("maw") on one in phase 3.
    "the_fallen": BossSpec(
        name="The Fallen",
        phases=(
            BossPhase(1.0, (("sweep", 3), ("uproot", 2), ("leaves", 3), ("sap", 2)), rest=1.0),
            BossPhase(0.6, (("sweep", 3), ("uproot", 2), ("leaves", 3), ("sap", 2)), rest=0.85),
            BossPhase(0.3, (("sweep", 3), ("uproot", 2), ("leaves", 3), ("sap", 2)), rest=0.6),
        ),
        loot=2500, achievement="the_fallen", pages=("the_fallen", "mimic_sapling", "bark_beetle"),
    ),
    # M26.1 (ai/bosses.Amanita, design/BOSSES.md section 27): it regrows its
    # warts ("drink") on a timer all fight; travels its network ("network")
    # on one from phase 2; puffs trip spores ("trip") and lures flies
    # ("flies") on timers in phase 3.
    "mycelium_amanita": BossSpec(
        name="Mycelium",
        phases=(
            BossPhase(1.0, (("slam", 2), ("spores", 3), ("sprouts", 2), ("spin", 2)), rest=1.0),
            BossPhase(0.6, (("slam", 2), ("spores", 3), ("sprouts", 2), ("spin", 2)), rest=0.85),
            BossPhase(0.3, (("slam", 2), ("spores", 3), ("sprouts", 2), ("spin", 2)), rest=0.6),
        ),
        loot=2500, achievement="mycelium_amanita", pages=("mycelium_amanita", "sporeling"),
    ),
    # M26.2 (ai/bosses.InkCap, design/BOSSES.md section 28): it melts into
    # ink ("melt") on a timer all fight; throws ink blots ("blots") on one
    # from phase 2; scrawls ("scrawl") and pushes up ink-cap clusters
    # ("clusters") on timers in phase 3.
    "mycelium_inkcap": BossSpec(
        name="Mycelium",
        phases=(
            BossPhase(1.0, (("scales", 2), ("spray", 2), ("burst", 2), ("shake", 2)), rest=1.0),
            BossPhase(0.6, (("scales", 2), ("spray", 2), ("burst", 2), ("shake", 2)), rest=0.85),
            BossPhase(0.3, (("scales", 2), ("spray", 2), ("burst", 2), ("shake", 2)), rest=0.6),
        ),
        loot=2500, achievement="mycelium_inkcap",
        pages=("mycelium_inkcap", "sporeling", "ink_imp"),
    ),
    # M26.3 (ai/bosses.Puffball, design/BOSSES.md section 29): it scatters
    # mines ("mines") on a timer all fight; bounds ("bound") between moves
    # from phase 2; breathes spores on the wind ("breath") and splits
    # ("split") on timers in phase 3.
    "mycelium_puffball": BossSpec(
        name="Mycelium",
        phases=(
            BossPhase(1.0, (("roll", 2), ("rings", 2), ("mortars", 2), ("squash", 2)), rest=1.0),
            BossPhase(0.6, (("roll", 2), ("rings", 2), ("mortars", 2), ("squash", 2)), rest=0.85),
            BossPhase(0.3, (("roll", 2), ("rings", 2), ("mortars", 2), ("squash", 2)), rest=0.6),
        ),
        loot=2500, achievement="mycelium_puffball", pages=("mycelium_puffball", "sporeling"),
    ),
    # M27 (ai/bosses.Necromancer, design/BOSSES.md section 30): two lives.
    # "necromancer" is More than Life (life 1): raise the dead + corpse
    # explosion all life; bone walls + death's gaze from phase 2; the legion
    # in phase 3. "necromancer_lich" is More than Death (life 2): all of
    # those (slower), plus soul storm + soul harvest, then possession, then
    # the bone cage. The reward and pages are the first spec's.
    "necromancer": BossSpec(
        name="More than Life",
        phases=(
            BossPhase(1.0, (("spears", 3), ("skulls", 2), ("hands", 2), ("reap", 2)), rest=0.9),
            BossPhase(0.66, (("spears", 3), ("skulls", 2), ("hands", 2), ("reap", 2)), rest=0.8),
            BossPhase(0.33, (("spears", 3), ("skulls", 2), ("hands", 2), ("reap", 2)), rest=0.7),
        ),
        loot=8000, achievement="necromancer", pages=("necromancer", "risen_dead"),
    ),
    "necromancer_lich": BossSpec(
        name="More than Death",
        phases=(
            BossPhase(1.0, (("spears", 3), ("skulls", 2), ("hands", 2), ("reap", 2)), rest=0.7),
            BossPhase(0.66, (("spears", 3), ("skulls", 2), ("hands", 2), ("reap", 2)), rest=0.6),
            BossPhase(0.33, (("spears", 3), ("skulls", 2), ("hands", 2), ("reap", 2)), rest=0.5),
        ),
        loot=0, achievement="necromancer", pages=(),
    ),
    # M29.4: Paradise's boss, form 1 (OCEAN.md 6.1; ai/bosses.Cavalry). Four
    # phases, a signature added in each: the formation charge, then the
    # light lances, the hymn, the four winds. Its moves: carousel, hoof
    # rings, halo rain, trample. (Form 2, the Four Horsemen: M29.5.)
    "cavalry": BossSpec(
        name="The Serene Cavalry",
        phases=(
            BossPhase(1.0, (("formation", 3), ("carousel", 2), ("hoofs", 2), ("halos", 2),
                            ("trample", 2)), rest=1.0),
            BossPhase(0.75, (("formation", 2), ("lances", 3), ("carousel", 2), ("hoofs", 2),
                             ("halos", 2), ("trample", 2)), rest=0.9),
            BossPhase(0.5, (("formation", 2), ("lances", 2), ("hymn", 2), ("carousel", 2),
                            ("hoofs", 1), ("halos", 2), ("trample", 2)), rest=0.8),
            BossPhase(0.25, (("formation", 2), ("lances", 2), ("hymn", 2), ("winds", 3),
                             ("carousel", 2), ("hoofs", 1), ("halos", 2), ("trample", 2)),
                      rest=0.7),
        ),
        loot=10000, achievement="cavalry",
        pages=("cavalry", "conquest", "war", "famine", "death", "pale_shade"),
    ),
    # M29.5: form 2, the Four Horsemen (ai/horsemen.py). Each picks among its
    # own kit's moves and its fallen brothers'; past half its health it
    # rests less between them.
    "conquest": BossSpec(
        name="Conquest",
        phases=(BossPhase(1.0, (("crown", 2), ("banner", 1), ("lap", 1)), rest=1.4),
                BossPhase(0.5, (("crown", 2), ("banner", 1), ("lap", 1)), rest=1.1)),
        loot=0, achievement="cavalry", pages=(),
    ),
    "war": BossSpec(
        name="War",
        phases=(BossPhase(1.0, (("sweep", 2), ("bloodcharge", 1), ("duel", 1)), rest=1.4),
                BossPhase(0.5, (("sweep", 2), ("bloodcharge", 1), ("duel", 1)), rest=1.1)),
        loot=0, achievement="cavalry", pages=(),
    ),
    "famine": BossSpec(
        name="Famine",
        phases=(BossPhase(1.0, (("weights", 2), ("locusts", 1)), rest=2.2),
                BossPhase(0.5, (("weights", 2), ("locusts", 1)), rest=1.8)),
        loot=0, achievement="cavalry", pages=(),
    ),
    "death": BossSpec(
        name="Death",
        phases=(BossPhase(1.0, (("quarter", 1), ("reap", 2)), rest=1.4),
                BossPhase(0.5, (("quarter", 1), ("reap", 2)), rest=1.1)),
        loot=0, achievement="cavalry", pages=(),
    ),
    # M30.4: Pandemonium's boss, form 1 (OCEAN.md 17.1; ai/feast.FeastHost).
    # Three phases, three rooms (100-67-33%): the banquet (courses served),
    # the ballroom (+ the dance floor), the vault (+ the vault's gold); toasts
    # in every room. His dance figures: grand spin, the beckoning, the
    # carving set, chandeliers. (M30.5: rests cut by 0.2 after the bot
    # benchmark: ~500 damage a minute was under the necromancer's.)
    "host_of_feast": BossSpec(
        name="The Host of the Feast",
        phases=(
            BossPhase(1.0, (("courses", 3), ("toast", 2), ("spin", 2), ("beckon", 2),
                            ("carving", 2), ("chandeliers", 2)), rest=0.8),
            BossPhase(0.67, (("dance", 3), ("courses", 2), ("toast", 2), ("spin", 2),
                             ("beckon", 2), ("carving", 2), ("chandeliers", 2)), rest=0.7),
            BossPhase(0.33, (("gold", 3), ("dance", 2), ("courses", 2), ("toast", 2),
                             ("spin", 2), ("beckon", 2), ("carving", 2), ("chandeliers", 2)),
                      rest=0.6),
        ),
        loot=10000, achievement="host_of_feast",
        pages=("host_of_feast", "feast_waiter"),
    ),
    # M30.5: form 2, the hunger (OCEAN.md 17.2; ai/hunger.py). Four phases, a
    # signature added in each: devour (all the form: not a move), then the
    # maw, teeth in the floor, spilled feast. His moves: lunge bite, tongue
    # lash, belly quake, bone scraps. The reward and pages are form 1's.
    "host_hunger": BossSpec(
        name="The Hunger",
        phases=(
            BossPhase(1.0, (("lunge", 3), ("tongue", 2), ("quake", 2), ("bones", 2)), rest=1.0),
            BossPhase(0.75, (("maw", 3), ("lunge", 2), ("tongue", 2), ("quake", 2), ("bones", 2)),
                      rest=0.9),
            BossPhase(0.5, (("teeth", 3), ("maw", 2), ("lunge", 2), ("tongue", 2), ("quake", 2),
                            ("bones", 2)), rest=0.8),
            BossPhase(0.25, (("spill", 3), ("teeth", 2), ("maw", 2), ("lunge", 2), ("tongue", 2),
                             ("quake", 2), ("bones", 2)), rest=0.7),
        ),
        loot=0, achievement="host_of_feast", pages=(),
    ),
    # M31.4: Pangaea's boss, form 1, the ages (OCEAN.md 28.1; ai/ancestor.py).
    # Three ages (100-67-33%), a signature added in each: the stampede (the
    # great mammal), the roar (the tyrant lizard), the swarm (the giant
    # insect). Its moves, each its age's way: the charge, the spit fan, the
    # eruption, the sweep. Sparser than other tier III bosses' (longer rests):
    # every move echoes.
    "ancestor": BossSpec(
        name="The Ancestor",
        phases=(
            BossPhase(1.0, (("stampede", 3), ("charge", 2), ("spit", 2), ("eruption", 2),
                            ("sweep", 2)), rest=1.2),
            BossPhase(0.67, (("roar", 3), ("stampede", 2), ("charge", 2), ("spit", 2),
                             ("eruption", 2), ("sweep", 2)), rest=1.1),
            BossPhase(0.33, (("swarm", 3), ("roar", 2), ("stampede", 2), ("charge", 2),
                             ("spit", 2), ("eruption", 1), ("sweep", 2)), rest=1.0),
        ),
        loot=10000, achievement="ancestor", pages=("ancestor", "first_blob", "first_crawler"),
    ),
    # M31.5: form 2, the first life (OCEAN.md 28.2; ai/first_life.py). Four
    # phases, a signature added in each: life evolves (all the form: not a
    # move), the husks wake as echoes of the ages (not a move either), then
    # tentacles, the tidal wave. Its moves: dive and surface, whirlpool,
    # boiling bubbles, arm lash. The reward and pages are form 1's.
    "ancestor_first_life": BossSpec(
        name="The First Life",
        phases=(
            BossPhase(1.0, (("dive", 2), ("whirlpool", 2), ("bubbles", 2), ("lash", 2)), rest=1.6),
            BossPhase(0.75, (("dive", 2), ("whirlpool", 2), ("bubbles", 2), ("lash", 2)),
                      rest=1.5),
            BossPhase(0.5, (("tentacles", 3), ("dive", 2), ("whirlpool", 2), ("bubbles", 2),
                            ("lash", 2)), rest=1.4),
            BossPhase(0.25, (("wave", 3), ("tentacles", 2), ("dive", 2), ("whirlpool", 2),
                             ("bubbles", 2), ("lash", 2)), rest=1.3),
        ),
        loot=0, achievement="ancestor", pages=(),
    ),
}
BOSS_KEYS = tuple(BOSSES)         # (M28.5: a stable order for the relic drop's seed)

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
# Love & Cuddles (ai/bosses.LoveCuddles, M25.2): a fluffy pink squirrel
# with a cleaver behind its back, in the hollow oak. It scuttles round its
# target LOVE_SCUTTLE = (nearest, farthest tiles, (s, s) between turning
# about, tiles/s, x that speed during its moves). Damages are per hit at
# level 1 (x the enemy damage scaling).
# Signature 1, THE HOARD (all fight): every HOARD_EVERY s it buries
# HOARD_MOUNDS acorns (HOARD_TELL s digging; mounds HOARD_NEAR tiles from
# its target; at most HOARD_MOUNDS_MAX). Between moves it goes for the
# nearest mound and digs it up (HOARD_DIG s, standing still): one more
# acorn held (at most HOARD_MAX): +HOARD_DMG damage and +HOARD_SPEED speed
# per acorn. A hero within HOARD_STEAL tiles of a mound steals it (and
# heals HOARD_HEAL). Shaken out of a tree or collapsing after its frenzy,
# it spills HOARD_SPILL of its hoard (rounded up).
# Signature 2, TREETOPS (phase 2+): every TREE_EVERY s it scurries
# (TREE_RUN tiles/s) up the nearest big oak: out of reach, pelting acorns
# (TREE_PELT = s between volleys, acorns a volley, fan degrees) and every
# TREE_LEAP[0] s leaping to another oak (a TREE_LEAP[1] s line first,
# TREE_LEAP[2] tiles/s). Damage its tree (its trunk: shots, hits; a shot
# into its crown, TREE_CROWN tiles round the trunk, counts too) for
# TREE_SHAKE x its max HP (kept as it leaps) and it falls out: TREE_FALL x
# its max HP lost and
# dazed TREE_DAZE s. After TREE_STAY s it comes down by itself, pouncing on
# its target (TREE_POUNCE = ring (tell) s, damage, radius).
# Signature 3, TRIPWIRES (phase 3): every WIRE_EVERY s (a WIRE_TELL s tell)
# it strings WIRES glinting wires between oaks near its target (at most
# WIRE_MAX). A hero walking across one (not rolling) trips it: a log
# swings down along it (WIRE_LOG = creak (tell) s, tiles/s, damage, width).
# A hero's shot crossing a wire within WIRE_CUT tiles cuts it.
# Signature 4, FRENZY (phase 3): a madness meter (0..1) fills FRENZY_FILL a
# second, FRENZY_HIT for each hit it lands and FRENZY_HURT x (damage taken
# / max HP). Full: FRENZY_DASH = (line (tell) s, dashes, tiles/s, longest,
# damage, width) zigzag cleaver dashes, then it collapses panting
# FRENZY_PANT s, taking FRENZY_VULN x damage.
LOVE_HIT_RADIUS = 2.0
LOVE_SCUTTLE = (7.0, 11.0, (3.0, 6.0), 5.0, 0.5)
HOARD_EVERY = 13.0
HOARD_TELL = 0.8
HOARD_MOUNDS = 3
HOARD_MOUNDS_MAX = 6
HOARD_NEAR = (5.0, 13.0)
HOARD_DIG = 1.3
HOARD_STEAL = 1.6
HOARD_HEAL = 8
HOARD_MAX = 8
HOARD_DMG = 0.07
HOARD_SPEED = 0.05
HOARD_SPILL = 0.5
TREE_EVERY = 20.0
TREE_RUN = 13.0
TREE_PELT = (0.6, 3, 24.0)
TREE_LEAP = (6.0, 0.7, 26.0)
TREE_SHAKE = 0.02
TREE_CROWN = 3.6
TREE_FALL = 0.03
TREE_DAZE = 4.0
TREE_STAY = 13.0
TREE_POUNCE = (0.8, 18, 2.6)
WIRE_EVERY = 16.0
WIRE_TELL = 0.8
WIRES = 3
WIRE_MAX = 6
WIRE_LOG = (0.5, 34.0, 18, 1.3)
WIRE_CUT = 0.6
FRENZY_FILL = 0.015         # (was FRENZY_TIME, which overwrote the War Drum's 3 s until M28.2a)
FRENZY_HIT = 0.05
FRENZY_HURT = 6.0
FRENZY_DASH = (0.45, 5, 32.0, 24.0, 16, 1.4)
FRENZY_PANT = 4.5
FRENZY_VULN = 1.5
# Its moves.
LOVE_SPIN = (0.6, 6, 2.8, 2.6, 7.5, 12, 0.7)  # cleaver up (tell) s, blades, ring radius, s
                                         # scuttling, tiles/s, damage, s between hits
LOVE_BARRAGE = (0.7, 3, 7, 50.0, 0.28, 14.0)  # cheeks puffed (tell) s, fans, acorns a fan,
                                         # fan degrees, s between fans, degrees each turns
LOVE_CONES = (1.1, 4, 2.0, 15, 6, 7.0)   # flight (tell) s, pinecones, burst radius, damage,
                                         # splinters each, spread round the target
LOVE_GANG = (0.8, (4, 6), 10)            # tell s, squirrels (fewest, most), most alive
LOVE_SHOTS = {
    "acorn": ShellSpec(speed=12.0, damage=9, max_range=30.0, damages_terrain=False,
                       look="acorn", sound="fizzle"),
    "splinter": ShellSpec(speed=10.0, damage=6, max_range=9.0, damages_terrain=False,
                          look="splinter", sound="fizzle"),
    "cleaver": ShellSpec(speed=11.0, damage=10, max_range=16.0, damages_terrain=False,
                         look="cleaver", sound="fizzle"),
}
# The Fallen (ai/bosses.TheFallen, M25.3): a tall, thin, branchy tree with
# one big eye, in the still grove among lookalike trees. It stalks round its
# target FALLEN_STALK = (nearest, farthest tiles, (s, s) between turning
# about, tiles/s, x that speed during its moves). Damages are per hit at
# level 1 (x the enemy damage scaling).
# The grove's trees (props["trees"]) are solid at the foot (a trunk tile)
# and catch any hero's shot that flies into them (TREE_BODY: the tiles round
# the line from its top to its foot).
# Signature 1, WHICH TREE? (all fight): every HIDE_EVERY s (a HIDE_TELL s
# tell, then a flurry of leaves over every tree near its target) it becomes
# one of the HIDE_AMONG trees nearest its target (none within HIDE_CLEAR of
# a hero): it can't be hit, and every HIDE_LASH s one of those trees (it or
# a fake) lashes a fan of HIDE_FAN splinters at the nearest hero. Its tell:
# its eye opens for HIDE_BLINK[0] s every HIDE_BLINK[1] s (give or take
# HIDE_BLINK[2]). A shot into a fake makes it spit HIDE_SPIT splinters back
# at the shooter (once a HIDE_SPIT_GAP s per tree). A hit on its tree drags
# it out: HIDE_FOUND x its max HP lost, dazed HIDE_STUN s. Not found after
# HIDE_TIME s, it bursts out: HIDE_BURST = (ring shards, blast radius, damage).
# Signature 2, ROOT WEB (phase 2+): every ROOT_EVERY s (a ROOT_TELL s tell)
# ROOT_LINES roots grow from its feet (one at its target, the rest spread
# ROOT_SPREAD degrees apart) at ROOT_GROW tiles/s up to ROOT_LEN tiles, and
# stay ROOT_LIFE s. A hero (not rolling) within ROOT_WIDTH of a root is
# grabbed: held ROOT_HOLD s, squeezed ROOT_SQUEEZE every 0.5 s, then free
# from roots for ROOT_IMMUNE s. A shot at the root holding someone cuts it.
# A root reaching within FIRE_SEAR tiles of a fire bowl burns away there.
# Signature 3, SWALLOW & SPIT (phase 3): every MAW_EVERY s its trunk splits
# open (MAW_TELL s) for MAW_OPEN s: shots that hit it are swallowed (no
# damage; its SAP fills by their damage). Stuffed with MAW_CHOKE x its max
# HP it chokes: dazed MAW_STUN s, coughing a few back at random. Otherwise
# it spits them all back: MAW_SPIT = (fewest, most shots, fans, fan degrees).
FALLEN_HIT_RADIUS = 1.6
FALLEN_STALK = (6.0, 10.0, (3.0, 6.0), 3.6, 0.5)
TREE_BODY = 0.9
HIDE_EVERY = 24.0
HIDE_TELL = 0.8
HIDE_AMONG = 7
HIDE_CLEAR = 5.0
HIDE_TIME = 12.0
HIDE_LASH = 1.6
HIDE_FAN = 4
HIDE_BLINK = (0.4, 2.2, 0.6)
HIDE_SPIT = 3
HIDE_SPIT_GAP = 0.8
HIDE_FOUND = 0.04
HIDE_STUN = 3.5
HIDE_BURST = (14, 3.2, 16)
ROOT_EVERY = 12.0
ROOT_TELL = 0.6
ROOT_LINES = 4
ROOT_SPREAD = 50.0
ROOT_GROW = 12.0
ROOT_LEN = 30.0
ROOT_LIFE = 9.0
ROOT_WIDTH = 0.55
ROOT_HOLD = 1.5
ROOT_SQUEEZE = 6
ROOT_IMMUNE = 2.0
FIRE_SEAR = 3.0
MAW_EVERY = 15.0
MAW_TELL = 0.7
MAW_OPEN = 4.0
MAW_CHOKE = 0.02
MAW_STUN = 3.5
MAW_SPIT = (8, 28, 3, 50.0)
# Its moves.
FALLEN_SWEEP = (0.7, 8.0, 65.0, 16, 0.25, 7.0)  # arm drawn back (tell) s, reach, half arc
                                         # degrees, damage, s the sweep takes (phase 3: two
                                         # arms), tiles/s it strides in during the tell
FALLEN_CHARGE = (0.7, 20.0, 26.0, 14, 1.6, 3.2, 12, 10)  # line (tell) s, tiles/s, longest,
                                         # damage, width, landing radius, landing damage, shards
FALLEN_LEAVES = (0.6, 3, 2.4, 0.12, 2.0, 3, 5, 40.0)  # tell s, arms, lasts s, s between,
                                         # turn rad/s, splinter fans, a fan, fan degrees
FALLEN_SAP = (1.0, 3, 2.4, 7.0, 0.45, 6.0, (3, 4), 8)  # flight (tell) s, globs, radius, lasts s,
                                         # your speed x in it, spread, beetles, most beetles
FALLEN_SHOTS = {
    "leaf": ShellSpec(speed=10.0, damage=8, max_range=30.0, damages_terrain=False,
                      look="leaf", sound="fizzle"),
    "splinter": ShellSpec(speed=12.0, damage=8, max_range=22.0, damages_terrain=False,
                          look="splinter", sound="fizzle"),
    "spit": ShellSpec(speed=13.0, damage=8, max_range=30.0, damages_terrain=False,
                      look="sap_spit", sound="fizzle"),
}
# Mycelium, the fly agaric (ai/bosses.Amanita, M26.1): a huge red-capped
# toadstool on root-threads, in its fruiting ring. It waddles round its
# target AMANITA_WALK = (nearest, farthest tiles, (s, s) between turning
# about, tiles/s, x that speed during its moves). Its body (AMANITA_HIT_RADIUS)
# is its stem; its cap's warts are their own bodies. Damages are per hit at
# level 1 (x the enemy damage scaling).
# Signature 1, WARTS (all fight): WART_SPOTS warts on its cap (tiles from
# its middle), each a body with WART_HP x (its max HP / 8000) HP. While n of
# the N are on, it takes WART_ARMOR + (1 - WART_ARMOR) x (1 - n / N) of any
# hit. A wart shot off falls as a little toadstool that puffs WART_SPROUT =
# (s later, spores, radius, damage). Every WART_REGROW[0] s, missing warts,
# it drinks from the ground (WART_REGROW[1] s, standing still) and regrows
# WART_REGROW[2].
# Signature 2, MYCELIAL NETWORK (phase 2+): every NET_EVERY s it sinks (can't
# be hit) and travels the threads -- to its nearest live ring, along the
# threads, to the ring nearest its target -- the whole path lit NET_TELL s
# first, at NET_SPEED tiles/s, and erupts there (NET_ERUPT = radius, damage,
# spores). A lit thread burns: NET_BURN = (width, damage, s between). A ring's
# node (NODE_HP) can be broken: that ring's out of the network until it
# regrows NODE_REGROW s later.
# Signature 3, TRIP SPORES (phase 3): every TRIP_EVERY s (a TRIP_TELL s
# tell) TRIP_CLOUDS clouds (TRIP_CLOUD = radius, lasts s) on and round its
# target. TRIP_IN s in one and you trip for TRIP_TIME s: you drift sideways
# (TRIP_DRIFT tiles/s, turning) and see fake shots beside its real ones
# (see-through, flickering, harmless). A roll clears your head.
# Signature 4, FLY LURE (phase 3): every FLY_EVERY s (a FLY_TELL s stench)
# FLIES flies (at most FLY_MAX) circle it (FLY_ORBIT = radius, rad/s),
# soaking up shots. Every FLY_DROP[0] s one drops dead, bursting (radius,
# damage).
AMANITA_HIT_RADIUS = 1.4
AMANITA_WALK = (6.0, 10.0, (3.0, 6.0), 3.2, 0.5)
WART_SPOTS = ((-1.7, -1.3), (-1.1, -1.9), (-0.4, -2.2), (0.4, -2.2), (1.1, -1.9), (1.7, -1.3),
              (-0.8, -1.5), (0.8, -1.5))
WART_HP = 45
WART_ARMOR = 0.4
WART_SPROUT = (3.0, 4, 1.4, 7)
WART_REGROW = (20.0, 1.5, 2)
NET_EVERY = 14.0
NET_TELL = 0.9
NET_SPEED = 22.0
NET_BURN = (0.7, 5, 0.5)
NET_ERUPT = (3.0, 16, 12)
NODE_HP = 150
NODE_REGROW = 30.0
TRIP_EVERY = 13.0
TRIP_TELL = 0.7
TRIP_CLOUDS = 3
TRIP_CLOUD = (2.6, 7.0)
TRIP_IN = 0.6
TRIP_TIME = 5.0
TRIP_DRIFT = 2.2
FLY_EVERY = 18.0
FLY_TELL = 0.8
FLIES = 12
FLY_MAX = 16
FLY_ORBIT = (3.2, 2.2)
FLY_DROP = (1.5, 1.4, 6)
# Its moves.
AMANITA_SLAM = (0.9, 3.0, 12, 10, 8)    # up in the air (tell) s, blast radius, damage,
                                         # spores in the first ring, in the second
AMANITA_SPORES = (0.6, 3, 7, 50.0, 0.3, 3, 2.4, 0.12, 2.2)  # tell s, fans, spores a fan, fan
                                         # degrees, s between fans; spiral arms, lasts s,
                                         # s between, turn rad/s
AMANITA_SPROUTS = (0.8, 3, 18.0, 1.8, 0.06, 0.5, 1.4, 9, 24.0)  # cracks (tell) s, lines,
                                         # length, spacing, s between sprouts, s before each
                                         # pops, radius, damage, degrees between lines
AMANITA_SPIN = (0.6, 3.0, 6.5, 0.25, 3, 8, 0.6)  # tell s, lasts s, tiles/s, s between spore
                                         # bursts, spores a burst, contact damage, s between hits
AMANITA_SHOTS = {
    "spore": ShellSpec(speed=10.0, damage=6, max_range=30.0, damages_terrain=False,
                       look="red_spore", sound="fizzle"),
    "white": ShellSpec(speed=8.0, damage=5, max_range=22.0, damages_terrain=False,
                       look="white_spore", sound="fizzle"),
}
# Mycelium, the shaggy ink cap (ai/bosses.InkCap, M26.2): a tall white
# shaggy cap whose hem melts into black ink, in its ring. It stalks round its
# target INKCAP_WALK = (nearest, farthest tiles, (s, s) between turning
# about, tiles/s, x that speed during its moves). Damages are per hit at
# level 1 (x the enemy damage scaling).
# Ink on the floor -- puddles and pools -- slows whoever's in it (x INK_SLOW)
# and stings (INK_STING every INK_TICK s).
# Signature 1, INK POOLS (all fight): every POOL_EVERY s it melts (POOL_TELL
# s) into a pool (POOL_RADIUS; can't be hit) and flows at POOL_SPEED tiles/s
# to where it'll reform -- a bubbling spot POOL_AWAY tiles beside its target,
# shown from the start -- leaving puddles (PUDDLE = radius, lasts s) every
# PUDDLE_GAP tiles; it reforms there in a splash of POOL_SPLASH ink drops.
# Signature 2, INK BLOTS (phase 2+): every BLOT_EVERY s (a BLOT_TELL s tell)
# BLOTS blots are lobbed (BLOT_FLIGHT s, rings where they land) onto and
# round its target (BLOT_RADIUS, lasting BLOT_LIFE s). In one, you're inked:
# blind beyond INK_SIGHT tiles for INKED s (kept up while you stand in it).
# A roll wipes it off.
# Signature 3, SCRAWL (phase 3): every SCRAWL_EVERY s it writes one of
# SCRAWL_WORDS across the floor through its target, a letter every
# SCRAWL_PEN s, SCRAWL_GAP tiles apart; SCRAWL_HOLD s after the last, the
# letters burst in order (SCRAWL_BURST = s apart, radius, damage) -- or, every
# other word, rise as ink imps (at most SCRAWL_IMPS out).
# Signature 4, INK-CAP CLUSTERS (phase 3): every CLUSTER_EVERY s (a
# CLUSTER_TELL s tell) CLUSTER ink-cap sprouts (bodies, CLUSTER_HP x its
# max HP / 8000) push up CLUSTER_NEAR tiles round its target. Not broken in
# CLUSTER_GROW s, each melts into a spreading pool (CLUSTER_POOL = radius
# it grows to, s it lasts).
INKCAP_HIT_RADIUS = 1.5
INKCAP_WALK = (6.0, 10.0, (3.0, 6.0), 3.4, 0.5)
INK_SLOW = 0.55
INK_STING = 3
INK_TICK = 0.6
POOL_EVERY = 14.0
POOL_TELL = 0.8
POOL_RADIUS = 2.2
POOL_SPEED = 7.0
POOL_AWAY = (5.0, 8.0)
POOL_SPLASH = 12
PUDDLE = (1.4, 8.0)
PUDDLE_GAP = 2.0
BLOT_EVERY = 12.0
BLOT_TELL = 0.6
BLOTS = 3
BLOT_FLIGHT = 0.9
BLOT_RADIUS = 2.6
BLOT_LIFE = 8.0
INK_SIGHT = 4.5
INKED = 2.0
SCRAWL_EVERY = 13.0
SCRAWL_WORDS = ("GROW", "ROT", "SPORE", "DEEPER", "HUNGER", "MYCELIUM", "SEEP")
SCRAWL_PEN = 0.12
SCRAWL_GAP = 2.4
SCRAWL_HOLD = 0.7
SCRAWL_BURST = (0.1, 1.5, 12)
SCRAWL_IMPS = 6
CLUSTER_EVERY = 15.0
CLUSTER_TELL = 0.5
CLUSTER = 5
CLUSTER_HP = 30
CLUSTER_NEAR = (4.0, 9.0)
CLUSTER_GROW = 6.0
CLUSTER_POOL = (3.0, 10.0)
# Its moves.
INKCAP_SCALES = (0.6, 3, 7, 50.0, 0.3, 2, 1.8, 0.15, 2.4)  # tell s, fans, scales a fan, fan
                                         # degrees, s between fans; spiral arms, lasts s,
                                         # s between, turn rad/s
INKCAP_SPRAY = (1.0, 4, 1.5, 10, 6.0)    # flight (tell) s, globs, splash radius, damage, spread
INKCAP_BURST = (1.0, 2.8, 12, 10)        # cracks (tell) s, blast radius, damage, ink drops
INKCAP_SHAKE = (0.6, 3, 14, 40.0, 0.35)  # tell s, rings, scales a ring, gap degrees,
                                         # s between rings
INKCAP_SHOTS = {
    "scale": ShellSpec(speed=11.0, damage=5, max_range=28.0, damages_terrain=False,
                       look="scale", sound="fizzle"),
    "ink": ShellSpec(speed=9.0, damage=6, max_range=20.0, damages_terrain=False,
                     look="ink_drop", sound="fizzle"),
}
# Mycelium, the giant puffball (ai/bosses.Puffball, M26.3): a huge round
# white puffball, cracking open as the fight goes on, in its field. It rolls
# round its target PUFF_WALK = (nearest, farthest tiles, (s, s) between
# turning about, tiles/s, x that speed during its moves). Damages are per hit
# at level 1 (x the enemy damage scaling).
# Spore clouds (mortars', its breath's) choke whoever's in one: CLOUD_CHOKE
# every CLOUD_TICK s. Clouds that drift into something solid stop there.
# Signature 1, PUFFBALL MINEFIELD (all fight): every MINE_EVERY s (a
# MINE_TELL s tell) it scatters MINES little puffballs (bodies, 1 HP) round
# its target (MINE_NEAR tiles; at most MINE_MAX). A hero within MINE_TRIGGER
# lights one's fuse (MINE_FUSE s); a shot pops one at once. A pop: MINE_BURST
# = (radius, damage), and every mine within MINE_CHAIN tiles pops MINE_GAP s
# later. A pop within MINE_STAGGER tiles of it: MINE_HURT x its max HP, and
# it's dazed MINE_DAZE s.
# Signature 2, BOUNDING (phase 2+): between moves it bounds every BOUND_EVERY
# s: a shadow where it'll land (BOUND_TELL s in the air, can't be hit),
# BOUND_NEAR tiles from its target; landing, BOUND_LAND = (radius, damage,
# spores).
# Signature 3, SPORE WIND (phase 3): a wind blows (WIND_SPEED tiles/s), turning
# WIND_TURN degrees every WIND_EVERY s. Every BREATH_EVERY s (a BREATH_TELL s
# tell) it breathes out BREATH_CLOUDS clouds (BREATH_CLOUD = radius, lasts s)
# that drift with the wind.
# Signature 4, SPLIT (phase 3): every SPLIT_EVERY s (a SPLIT_TELL s tell) it
# splits into two halves (PuffHalf bodies, hit radius SPLIT_HALF[0]) that
# bound on their own (every SPLIT_HALF[1] s, landing SPLIT_HALF[2] radius,
# SPLIT_HALF[3] damage, SPLIT_HALF[4] spores), sharing its health; after
# SPLIT_TIME s they roll back together (SPLIT_JOIN tiles/s) and merge.
PUFF_HIT_RADIUS = 1.8
PUFF_WALK = (6.0, 10.0, (3.0, 6.0), 3.4, 0.5)
CLOUD_CHOKE = 4
CLOUD_TICK = 0.5
MINE_EVERY = 12.0
MINE_TELL = 0.6
MINES = 8
MINE_NEAR = (3.5, 11.0)
MINE_MAX = 18
MINE_TRIGGER = 1.4
MINE_FUSE = 0.45
MINE_BURST = (2.0, 10)
MINE_CHAIN = 3.6
MINE_GAP = 0.15
MINE_STAGGER = 3.6
MINE_HURT = 0.006
MINE_DAZE = 1.5
BOUND_EVERY = 2.2
BOUND_TELL = 0.65
BOUND_NEAR = (5.0, 9.0)
BOUND_LAND = (2.4, 12, 6)
WIND_SPEED = 3.0
WIND_EVERY = 10.0
WIND_TURN = 90.0
BREATH_EVERY = 9.0
BREATH_TELL = 0.6
BREATH_CLOUDS = 5
BREATH_CLOUD = (2.4, 7.0)
SPLIT_EVERY = 22.0
SPLIT_TELL = 0.8
SPLIT_TIME = 12.0
SPLIT_HALF = (1.2, 1.8, 2.0, 10, 5)
SPLIT_JOIN = 8.0
# Its moves.
PUFF_ROLL = (0.6, 16.0, 30.0, 14, 1.8)   # line (tell) s, tiles/s, how far, damage, width
PUFF_RINGS = (0.6, 3, 16, 40.0, 0.5)     # tell s, rings, puffs a ring, gap degrees, s between
PUFF_MORTARS = (1.0, 4, 1.6, 8, 2.2, 5.0, 6.0)  # flight (tell) s, mortars, burst radius,
                                         # damage, cloud radius, cloud lasts s, spread
PUFF_SQUASH = (0.7, 3.2, 14, 14)         # squashed (tell) s, blast radius, damage, spores
PUFF_SHOTS = {
    "puff": ShellSpec(speed=6.0, damage=6, max_range=26.0, damages_terrain=False,
                      look="puff", sound="fizzle"),
    "spore": ShellSpec(speed=10.0, damage=6, max_range=24.0, damages_terrain=False,
                       look="dust_spore", sound="fizzle"),
}
# More than Life / More than Death (ai/bosses.Necromancer, M27): the plains
# boss, much harder than the ring bosses -- by having many more abilities.
# Two lives of NECRO_HP_LIVES x the usual health each. Life 1 walks round its
# target NECRO_WALK = (nearest, farthest, (s, s), tiles/s, x during moves);
# life 2 floats (over graves) NECRO_FLOAT likewise. Life 2's signature timers
# are NECRO_LICH_SLOW x longer (it has so many more). Damages are per hit at
# level 1 (x the enemy damage scaling).
# DYING the first time: at 1 HP he can't be hurt; his body falls, his soul
# tears free and rises (NECRO_RITUAL s, every corpse raised round it), and he
# comes back as the lich with full health.
# RAISE THE DEAD (life 1 on): whatever dies in the arena leaves a corpse
# (the arena starts with some). Stand CORPSE_STOMP[0] tiles from one for
# CORPSE_STOMP[1] s to crush it. Every RAISE_EVERY s (a RAISE_TELL s glow)
# up to RAISE_MAX corpses within RAISE_RANGE of him rise as risen dead (at
# most MINION_MAX out), plus RAISE_GRAVES from graves near his target.
# CORPSE EXPLOSION (life 1 on): every BLAST_EVERY s the corpses within
# BLAST_NEAR tiles of a hero glow (BLAST_TELL s) and burst (BLAST = radius,
# damage).
# BONE WALLS (phase 2 on): every WALL_EVERY s (WALL_TELL s of cracks)
# WALL_LINES walls of bone (WALL_LEN tiles, through and round his target)
# rise; they crumble WALL_LIFE s later (tiles.BONE_WALL, breakable).
# DEATH'S GAZE (phase 2 on): every GAZE_EVERY s (a GAZE_TELL s glow) a beam
# (GAZE_LEN tiles, stopped by anything that stops shots: hide behind graves)
# sweeps once round him in GAZE_TIME s, from his target: GAZE_HIT every
# GAZE_TICK s to whoever it's on (GAZE_WIDTH).
# THE LEGION (phase 3 on): every LEGION_EVERY s, by turns: an archer volley
# (VOLLEY = zones, radius, rings (tell) s, damage) on and round heroes, or a
# phalanx (PHALANX = shields, spacing, gap slots, tiles/s, how far, contact
# damage) marching through its target, shields to the front (they take no
# harm from in front).
# SOUL STORM (lich): every STORM_EVERY s (STORM_TELL s) for STORM_TIME s
# heroes within STORM_REACH are pulled toward him (STORM_PULL tiles/s) while
# STORM_SOULS souls circle him (STORM_RING = nearest, farthest, rad/s),
# cutting (STORM_HIT every 0.5 s).
# SOUL HARVEST (lich): each hit of his that lands spills a soul that drifts to
# him (HARVEST = tiles/s, grab radius, heal); each he swallows (at most
# HARVEST_MAX) powers his next move (+HARVEST_POWER damage each).
# POSSESSION (lich phase 2 on): every POSSESS_EVERY s (POSSESS_TELL s) he
# hides in one of his risen dead (raising up to POSSESS_HOSTS first): his
# body still and shielded; the host's eyes flash (POSSESS_BLINK = on s,
# every s). Kill it: he's back, dazed POSSESS_STUN s, losing POSSESS_HURT x
# max HP. Not found in POSSESS_TIME s: he's back in a ring of POSSESS_NOVA
# souls.
# BONE CAGE (lich phase 3): every CAGE_EVERY s (rib shadows, CAGE_TELL s)
# CAGE_RIBS ribs (bodies, CAGE_HP x max HP / 8000) round his target, who
# can't walk; they close in from CAGE_RADIUS[0] to [1] over CAGE_TIME s and
# crush (CAGE_CRUSH). Break one rib to break the cage.
NECRO_HP_LIVES = 1.0
NECRO_HIT_RADIUS = 1.6
NECRO_WALK = (7.0, 12.0, (3.0, 6.0), 3.4, 0.5)
NECRO_FLOAT = (7.0, 12.0, (3.0, 6.0), 4.6, 0.6)
NECRO_LICH_SLOW = 1.35
NECRO_RITUAL = 6.0
NECRO_DMG = 1.25
CORPSE_STOMP = (1.1, 0.5)
RAISE_EVERY = 11.0
RAISE_TELL = 1.0
RAISE_RANGE = 30.0
RAISE_MAX = 4
RAISE_GRAVES = 1
MINION_MAX = 7
BLAST_EVERY = 9.0
BLAST_NEAR = 8.0
BLAST_TELL = 1.0
BLAST = (2.4, 15)
WALL_EVERY = 15.0
WALL_TELL = 1.0
WALL_LINES = 2
WALL_LEN = 18
WALL_LIFE = 12.0
NECRO_BONE_WALL_HP = 80
GAZE_EVERY = 20.0
GAZE_TELL = 1.2
GAZE_LEN = 70.0
GAZE_TIME = 5.0
GAZE_HIT = 7
GAZE_TICK = 0.25
GAZE_WIDTH = 0.9
LEGION_EVERY = 16.0
VOLLEY = (3, 3.2, 1.3, 14)
PHALANX = (12, 1.6, 2, 4.0, 34.0, 12)
STORM_EVERY = 16.0
STORM_TELL = 0.8
STORM_TIME = 6.0
STORM_REACH = 20.0
STORM_PULL = 3.0
STORM_SOULS = 10
STORM_RING = (4.0, 9.0, 1.6)
STORM_HIT = 8
HARVEST = (8.0, 1.3, 3)
HARVEST_MAX = 12
HARVEST_POWER = 0.05
POSSESS_EVERY = 30.0
POSSESS_TELL = 0.8
POSSESS_HOSTS = 6
POSSESS_BLINK = (0.4, 2.0)
POSSESS_STUN = 4.0
POSSESS_HURT = 0.03
POSSESS_TIME = 10.0
POSSESS_NOVA = 16
CAGE_EVERY = 13.0
CAGE_TELL = 0.9
CAGE_RIBS = 10
CAGE_HP = 25
CAGE_RADIUS = (2.2, 0.9)
CAGE_TIME = 5.0
CAGE_CRUSH = 28
# Its moves.
NECRO_SPEARS = (0.6, 7, 40.0, 6, 0.08, 0.35)  # tell s, spears a fan, fan degrees, spears in
                                         # the line, s between them, s between volleys
NECRO_SKULLS = (0.7, 4, 1.2, 9.0, 2.0, 6.0, 12)  # tell s, skulls, s circling first, speed,
                                         # turn rad/s, life s, damage
NECRO_HANDS = (1.0, 8, 3.2, 1.3, 10, 1.0)  # rings (tell) s, hands round the middle, ring
                                         # radius, hit radius, damage, s rooted
NECRO_REAP = (0.7, 0.25, 4.5, 75.0, 18)  # shadow (tell) s, wind-up s, reach, half arc
                                         # degrees, damage
NECRO_SHOTS = {
    "spear": ShellSpec(speed=15.0, damage=8, max_range=32.0, damages_terrain=False,
                       look="bone_spear", sound="fizzle"),
    "soul": ShellSpec(speed=9.0, damage=8, max_range=30.0, damages_terrain=False,
                      look="soul", sound="fizzle"),
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
