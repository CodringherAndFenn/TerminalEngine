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

from .specs import (CardSpec, CharacterSpec, EnemySpec, ShellSpec, SpellSpec, StatusSpec,
                    UpgradeSpec, WeaponSpec)

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
    # (all 5 colors), throwing axes ~40 per leg (every enemy in the path, out
    # and back), lute ~13 (every enemy around, automatically). Balance comes later.
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
    "wizard": CharacterSpec(name="wizard", sprite="wizard", weapon="shock_bolt", **_HERO),
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
MAX_DODGE = 0.60
MAX_LIFESTEAL = 0.15
MAX_MOVE_BONUS = 0.80
MAX_AREA_BONUS = 2.0         # area x3 at most
MAX_SPELL_COOLDOWN = 0.60    # spells at most 60% faster
MIN_ATTACK_INTERVAL = 0.08   # fastest attack cadence any stack of cards can reach
STEADY_SPEED = 0.3           # tiles/s: below this the hero counts as standing still
POINT_BLANK_RANGE = 4.0      # tiles (Point Blank)
SUPERCELL_BONUS = 0.25       # chain jumps vs shocked enemies (Supercell)
OVERLOAD_EVERY = 5           # every Nth attack is overloaded...
OVERLOAD_MULT = 3.0          # ...for this much damage...
OVERLOAD_CHAIN = 3           # ...and this many extra jumps
MARK_INTERVAL = 4.0          # Hunter's Mark picks a new target this often
MARK_MULT = 2.0
DISSONANCE_PUSH = 1.2        # tiles a beat pushes enemies back (Dissonance)
SPECTRUM_CHANCE = 0.20       # Spectrum: chance a color applies its status
# Spectrum: rainbow pellet color (palette.RAINBOW_SHOTS order) -> status.
SPECTRUM_STATUS = ("burn", None, "shock", "poison", "chill")

# --- Statuses (systems/statuses.py) -----------------------------------------------
# Status damage is its own bucket (S): base x (1 + status damage) x (1 + tag
# damage); it never crits. Damage-over-time is dealt every STATUS_TICK s.
STATUS_TICK = 0.5
STATUSES = {
    "burn": StatusSpec("burn", "fire", duration=3.0, max_stacks=5, dps=4.0),
    "poison": StatusSpec("poison", "poison", duration=6.0, max_stacks=5, dps=2.0),
    "bleed": StatusSpec("bleed", "physical", duration=4.0, max_stacks=5, dps=3.0),
    "chill": StatusSpec("chill", "frost", duration=3.0, max_stacks=5, slow=0.10),
    "shock": StatusSpec("shock", "lightning", duration=2.0, vulnerability=0.15),
}
FREEZE_TIME = 1.5            # 5 chill stacks: frozen solid this long (can't act)

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
}

# Cards. See specs.CardSpec for the fields and players/stats.py for the
# stats. "+X% damage" is always bucket A (they add up); "xN damage" is its
# own multiplier (rare and up only).
_T = 5          # copies of a tiered generic card one hero can take
CARDS = {
    # --- Generic stats (tiered: the number grows with the rarity rolled) ---
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
    "lingering": CardSpec("Lingering", "+{X}% duration", (("duration", "add", "X"),),
                          tiers=(10, 15, 22, 30, 40), max_stacks=_T, code="G09"),
    "thick_hide": CardSpec("Thick Hide", "+{X} armor", (("armor", "add", "X"),),
                           tiers=(3, 5, 8, 12, 16), x_scale=1, max_stacks=_T, code="G10"),
    "nimble": CardSpec("Nimble", "+{X}% dodge", (("dodge", "add", "X"),),
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
    "multishot": CardSpec("Multishot", "+1 projectile",
                          (("pellets", "add", 1), ("spread", "add", 8)), rarity="rare",
                          heroes=("wizard", "huntress"), tags=("projectile",),
                          unlock="L:300", code="G20"),
    # --- Wizard ---
    "storm_caller": CardSpec("Storm Caller", "lightning jumps to +1 enemy", (("chain", "add", 1),),
                             rarity="rare", heroes=("wizard",), tags=("lightning",), code="W1"),
    "conductor": CardSpec("Conductor", "jumps reach 30% farther and fade less",
                          (("chain_range", "add", 0.3), ("chain_falloff", "add", 0.08)),
                          heroes=("wizard",), tags=("lightning",), code="W2"),
    "supercell": CardSpec("Supercell",
                          "bolts shock; jumps go for shocked enemies, +25% damage to them",
                          (("supercell", "flag", 1), ("shock", "source", 1)),
                          rarity="uncommon", max_stacks=1, heroes=("wizard",),
                          tags=("lightning",), code="W3"),
    "overload": CardSpec("Overload", "every 5th bolt: x3 damage and +3 jumps",
                         (("overload", "flag", 1),), rarity="rare", max_stacks=1,
                         heroes=("wizard",), tags=("lightning",), unlock="L:300", code="W4"),
    # --- Dwarf ---
    "ricochet": CardSpec("Ricochet", "+1 axe per throw",
                         (("pellets", "add", 1), ("spread", "add", 16)), rarity="rare",
                         heroes=("dwarf",), tags=("projectile",), code="D1"),
    "heavy_axe": CardSpec("Heavy Axe", "x1.35 damage, attacks 10% slower",
                          (("damage_mult", "mul", 1.35), ("interval_mult", "mul", 1.1)),
                          rarity="rare", heroes=("dwarf",), tags=("physical",), code="D2"),
    "long_haul": CardSpec("Long Haul", "axes fly 30% farther and 20% faster",
                          (("range", "add", 0.3), ("shot_speed", "add", 0.2)),
                          heroes=("dwarf",), code="D3"),
    "cleave": CardSpec("Cleave", "axes make enemies bleed",
                       (("cleave", "flag", 1), ("bleed", "source", 1)), rarity="uncommon",
                       max_stacks=1, heroes=("dwarf",), tags=("physical",), code="D4"),
    # --- Huntress ---
    "volley": CardSpec("Volley", "+2 arrows in a fan",
                       (("pellets", "add", 2), ("spread", "add", 14)), rarity="epic",
                       max_stacks=2, heroes=("huntress",), tags=("projectile",), code="H1"),
    "broadhead": CardSpec("Broadhead", "+2 pierce; +15% damage per enemy already passed",
                          (("pierce", "add", 2), ("broadhead", "add", 0.15)),
                          rarity="uncommon", heroes=("huntress",), tags=("physical",),
                          code="H2"),
    "hunters_mark": CardSpec("Hunter's Mark",
                             "every 4 s the toughest enemy in view is marked: x2 damage from you",
                             (("hunters_mark", "flag", 1),), rarity="rare", max_stacks=1,
                             heroes=("huntress",), unlock="L:300", code="H3"),
    "steady_aim": CardSpec("Steady Aim", "+25% crit chance while standing still",
                           (("steady_crit", "add", 0.25),), rarity="uncommon", max_stacks=2,
                           heroes=("huntress",), code="H4"),
    # --- Princess ---
    "prism": CardSpec("Prism", "+2 colors in the fan",
                      (("pellets", "add", 2), ("spread", "add", 8)), rarity="rare",
                      heroes=("princess",), tags=("projectile",), code="P1"),
    "focus": CardSpec("Focus", "tighter fan, +25% range",
                      (("spread_mult", "mul", 0.7), ("range", "add", 0.25)), max_stacks=2,
                      heroes=("princess",), code="P2"),
    "spectrum": CardSpec("Spectrum",
                         "red burns, blue chills, green poisons, yellow shocks (20%)",
                         (("spectrum", "flag", 1), ("burn", "source", 1), ("chill", "source", 1),
                          ("poison", "source", 1), ("shock", "source", 1)),
                         rarity="rare", max_stacks=1, heroes=("princess",),
                         tags=("fire", "frost", "poison", "lightning"), unlock="L:400",
                         code="P3"),
    "point_blank": CardSpec("Point Blank", "+40% damage to enemies within 4 tiles",
                            (("point_blank", "add", 0.4),), rarity="uncommon", max_stacks=2,
                            heroes=("princess",), code="P4"),
    # --- Bard ---
    "crescendo": CardSpec("Crescendo", "beats reach 25% farther", (("range", "add", 0.25),),
                          heroes=("bard",), tags=("area",), code="B1"),
    "encore": CardSpec("Encore", "+30% beat damage, +1.5 HP/s",
                       (("damage", "add", 0.3), ("regen", "add", 1.5)), rarity="rare",
                       heroes=("bard",), code="B2"),
    "tempo": CardSpec("Tempo", "beats come 15% sooner", (("interval_mult", "mul", 0.85),),
                      rarity="uncommon", heroes=("bard",), tags=("area",), code="B3"),
    "dissonance": CardSpec("Dissonance", "beats push enemies back and chill them",
                           (("dissonance", "flag", 1), ("chill", "source", 1)),
                           rarity="uncommon", max_stacks=1, heroes=("bard",),
                           tags=("frost",), unlock="L:250", code="B4"),
    # --- Status enablers ---
    "kindling": CardSpec("Kindling", "+15% status chance; your hits can burn",
                         (("status_chance", "add", 0.15), ("burn", "status", 1)),
                         rarity="uncommon", tags=("fire",), code="T01"),
    "venom": CardSpec("Venom", "+15% status chance; your hits can poison",
                      (("status_chance", "add", 0.15), ("poison", "status", 1)),
                      rarity="uncommon", tags=("poison",), code="T03"),
    "frostbite": CardSpec("Frostbite", "+15% status chance; your hits can chill",
                          (("status_chance", "add", 0.15), ("chill", "status", 1)),
                          rarity="uncommon", tags=("frost",), code="T05"),
    "static": CardSpec("Static", "+15% status chance; your hits can shock",
                       (("status_chance", "add", 0.15), ("shock", "status", 1)),
                       rarity="uncommon", tags=("lightning",), code="T07"),
    "serrated": CardSpec("Serrated", "+15% status chance; your hits can bleed",
                         (("status_chance", "add", 0.15), ("bleed", "status", 1)),
                         rarity="uncommon", tags=("physical",), code="T08"),
    # --- Spells (the first copy grants it, the next ones level it up) ---
    "daggers": CardSpec("Orbiting Daggers", "", (("daggers", "spell", 1),), rarity="uncommon",
                        max_stacks=5, tags=("physical", "orbit"), code="S01"),
    "ember_aura": CardSpec("Ember Aura", "", (("ember_aura", "spell", 1),), rarity="uncommon",
                           max_stacks=5, tags=("fire", "area"), code="S02"),
    "frost_nova": CardSpec("Frost Nova", "", (("frost_nova", "spell", 1),), rarity="uncommon",
                           max_stacks=5, tags=("frost", "area"), code="S03"),
}

# --- Loot and the Guild Hall (meta/guild.py, scenes/guild_hall.py) ----------------
# Every kill a hero makes (or their statuses / spells) is worth loot at
# once: the enemy's xp x LOOT_PER_XP x (1 + loot bonus). The run's loot is
# kept in full however the run ends (death, abandon, quit) and goes to the
# guild's purse, which buys the upgrades below and card unlocks.
LOOT_PER_XP = 0.5
# Developer mode (run.py --dev): the purse holds this much (never saved).
DEV_LOOT = 999_999

# Shared upgrades: every hero gets them.
GUILD_UPGRADES = {
    "whetstone": UpgradeSpec("Whetstone", "+4% damage", (("damage", "add", 0.04),),
                             base_cost=80),
    "drill_yard": UpgradeSpec("Drill Yard", "+3% attack speed", (("attack_speed", "add", 0.03),),
                              base_cost=80),
    "infirmary": UpgradeSpec("Infirmary", "+8 max HP", (("max_hp", "add", 8),), base_cost=60),
    "armory": UpgradeSpec("Armory", "+2 armor", (("armor", "add", 2),), base_cost=100),
    "cobbler": UpgradeSpec("Cobbler", "+3% move speed", (("move", "add", 0.03),),
                           max_level=3, base_cost=100),
    "old_maps": UpgradeSpec("Old Maps", "+5% XP", (("xp", "add", 0.05),), base_cost=80),
    "treasure_map": UpgradeSpec("Treasure Map", "+6% loot", (("loot", "add", 0.06),),
                                base_cost=100),
    "lodestone": UpgradeSpec("Lodestone", "+15% pickup radius", (("pickup", "add", 0.15),),
                             max_level=3, base_cost=60),
    "lucky_shrine": UpgradeSpec("Lucky Shrine", "+3 luck", (("luck", "add", 3),),
                                base_cost=120),
    "fortune_teller": UpgradeSpec("Fortune Teller", "+1 reroll each run",
                                  (("rerolls", "add", 1),), max_level=3, base_cost=150,
                                  growth=2.0),
    "exile_ledger": UpgradeSpec("Exile Ledger", "+1 banish each run", (("banishes", "add", 1),),
                                max_level=3, base_cost=200, growth=2.0),
    "arcane_wing": UpgradeSpec("Arcane Wing", "+1 spell slot", (("spell_slots", "add", 1),),
                               max_level=1, base_cost=1500),
}
# Each hero's own: two shared kinds plus two of their own.
_MASTERY = UpgradeSpec("Mastery", "+4% damage", (("damage", "add", 0.04),), base_cost=60)
_TOUGHNESS = UpgradeSpec("Toughness", "+8 max HP", (("max_hp", "add", 8),), base_cost=50)
HERO_UPGRADES = {
    "wizard": {"mastery": _MASTERY, "toughness": _TOUGHNESS,
               "conductor_rod": UpgradeSpec("Conductor's Rod", "jumps reach 10% farther",
                                            (("chain_range", "add", 0.1),), max_level=3),
               "static_focus": UpgradeSpec("Static Focus", "+3% crit chance",
                                           (("crit_chance", "add", 0.03),), max_level=3)},
    "dwarf": {"mastery": _MASTERY, "toughness": _TOUGHNESS,
              "strong_arm": UpgradeSpec("Strong Arm", "axes fly 10% farther and faster",
                                        (("range", "add", 0.1), ("shot_speed", "add", 0.1)),
                                        max_level=3),
              "stonehide": UpgradeSpec("Stonehide", "+2 armor", (("armor", "add", 2),),
                                       max_level=3)},
    "huntress": {"mastery": _MASTERY, "toughness": _TOUGHNESS,
                 "eagle_eye": UpgradeSpec("Eagle Eye", "+3% crit chance",
                                          (("crit_chance", "add", 0.03),), max_level=3),
                 "fleet_foot": UpgradeSpec("Fleet Foot", "+3% move speed",
                                           (("move", "add", 0.03),), max_level=3)},
    "princess": {"mastery": _MASTERY, "toughness": _TOUGHNESS,
                 "radiance": UpgradeSpec("Radiance", "+8% range", (("range", "add", 0.08),),
                                         max_level=3),
                 "royal_grace": UpgradeSpec("Royal Grace", "+3% dodge", (("dodge", "add", 0.03),),
                                            max_level=3)},
    "bard": {"mastery": _MASTERY, "toughness": _TOUGHNESS,
             "resonance": UpgradeSpec("Resonance", "+6% area", (("area", "add", 0.06),),
                                      max_level=3),
             "lullaby": UpgradeSpec("Lullaby", "regain 0.3 HP per second",
                                    (("regen", "add", 0.3),), max_level=3)},
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
