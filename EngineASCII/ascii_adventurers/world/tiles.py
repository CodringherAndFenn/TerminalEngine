"""
world/tiles.py -- terrain tile types.

Each tile is drawn as CELLS_PER_TILE (2) characters. A type lists several
2-character glyph variants; which one a given tile shows is picked by a
position hash, so ground looks varied but stays stable as you scroll.

Destructible types have hit points (`hp` > 0), `wear` glyph sets shown as
they take damage, and `becomes`: the (passable) tile left once destroyed.

Only ASCII and the engine's synthesized box/block glyphs are used (VT323 has
no other symbols -- see CLAUDE.md).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from .. import config, palette
from .rng import hash_coords


class Damage(Enum):
    """Outcome of a world's damage_tile()."""

    NONE = "none"            # not destructible (rock, void, open ground)
    DAMAGED = "damaged"      # lost hit points, still standing
    DESTROYED = "destroyed"  # replaced by its rubble


@dataclass(frozen=True)
class TileType:
    name: str
    glyphs: tuple[str, ...]      # 2-char variants
    fg: tuple
    bg: tuple
    solid: bool = False          # blocks walking
    blocks_shots: bool = False   # stops projectiles
    hp: int = 0                  # 0 = indestructible
    # Glyph variant sets for increasing damage: wear[0] = lightly damaged,
    # wear[-1] = nearly destroyed. Empty = looks intact until destroyed.
    wear: tuple[tuple[str, ...], ...] = ()
    becomes: TileType | None = None  # what's left when destroyed

    @property
    def destructible(self) -> bool:
        return self.hp > 0

    def glyph_at(self, tx: int, ty: int, hp_left: int | None = None) -> str:
        """Glyph for the tile at (tx, ty), given its remaining hit points
        (None = undamaged). Any damage shows wear[0]; the fraction of hp lost
        picks later stages evenly (a 4 hp wall with 2 stages: 3-2 hp ->
        wear[0], 1 hp -> wear[1])."""
        variants = self.glyphs
        if hp_left is not None and self.wear and hp_left < self.hp:
            lost = 1.0 - hp_left / self.hp                 # 0 < lost < 1
            stage = min(len(self.wear), max(1, math.ceil(lost * len(self.wear) - 1e-9)))
            variants = self.wear[stage - 1]
        return variants[hash_coords(tx, ty, 0x71E) % len(variants)]


GROUND = TileType(
    "ground", ("  ", "  ", "  ", ". ", " .", " '", "` "), palette.GROUND_FG, palette.GROUND_BG,
)
GRASS = TileType(
    "grass", ('" ', ' "', "''", ", ", " ,"), palette.GRASS_FG, palette.GROUND_BG,
)
RUBBLE = TileType(
    "rubble", (".:", ":.", ";,", ",;"), palette.RUBBLE_FG, palette.GROUND_BG,
)
SPLINTERS = TileType(
    # What a destroyed tree leaves: passable, like rubble.
    "splinters", ("_,", ",_", "._", "_."), palette.SPLINTER_FG, palette.GROUND_BG,
)
TREE = TileType(
    "tree", ("^^", "^A", "A^", "^^"), palette.TREE_FG, palette.TREE_BG,
    solid=True, blocks_shots=True, hp=config.TREE_HP,
    wear=(("^,", ",^", "^."),),
    becomes=SPLINTERS,
)
WALL = TileType(
    "wall", ("██",), palette.WALL_FG, palette.WALL_BG,
    solid=True, blocks_shots=True, hp=config.WALL_HP,
    # Shade glyphs get sparser as the wall crumbles: cracked, then breaking up.
    wear=(("▓▒", "▒▓", "▓▓"), ("░▒", "▒░", "░ ", " ░")),
    becomes=RUBBLE,
)
ROCK = TileType(
    "rock", ("▓▓", "▓▒", "▒▓"), palette.ROCK_FG, palette.ROCK_BG,
    solid=True, blocks_shots=True,
)
WATER = TileType(
    # VT323's "~" renders like an "N", so water is a sparse dither instead.
    "water", ("░ ", " ░", "  ", "  ", "▒░"), palette.WATER_FG, palette.WATER_BG,
    solid=True,  # can't be crossed on foot, but shots fly over it
)
VOID = TileType(
    "void", ("  ",), palette.VOID_FG, palette.VOID_BG,
    solid=True, blocks_shots=True,
)


# --- Biome tiles (milestone 3) -------------------------------------------------------
# Every destroyed thing leaves passable debris matching its biome's ground.

# Plains: wide open grassland (the start area).
PLAINS = TileType(
    "plains", ("  ", "  ", "  ", ". ", " '", "  "), palette.PLAINS_GRASS, palette.PLAINS_BG,
)
TALL_GRASS = TileType(
    "tall grass", ('" ', ' "', '""', "',"), palette.PLAINS_GRASS, palette.PLAINS_BG,
)
FLOWERS = TileType(
    "flowers", ("* ", " *", ".*"), palette.PLAINS_FLOWER, palette.PLAINS_BG,
)

# Forest: dense pines with clearings.
FOREST_FLOOR = TileType(
    "forest floor", (", ", " ,", "  ", ". "), palette.FOREST_FLOOR, palette.FOREST_BG,
)
PINE_DEBRIS = TileType(
    "splinters", ("_,", ",_", "._"), palette.SPLINTER_FG, palette.FOREST_BG,
)
PINE = TileType(
    "pine", ("/\\", "^^", "A^", "^A"), palette.PINE_FG, palette.PINE_BG,
    solid=True, blocks_shots=True, hp=config.TREE_HP,
    wear=(("/.", ".\\", "^."),),
    becomes=PINE_DEBRIS,
)

# Haunted forest (M21; replaced the pine thickets, which walled you in):
# dead leaves underfoot, drifting fog, and big gnarled trees standing well
# apart -- only a tree's trunk blocks; its crown of twisted branches and its
# roots are drawn on walkable tiles round it (world/generator._haunt). Old
# stumps and fallen logs are the cover (and can be broken); the trees
# themselves are ancient and can't.
DEAD_LEAVES = TileType(
    "dead leaves", (". ", " ,", "  ", "` ", "  ", ", "), palette.HAUNT_LEAF, palette.HAUNT_BG,
)
FOG = TileType(
    # Just a look: walkable, under everything (it never hides a bullet).
    "fog", ("░ ", " ░", "  ", "░ ", ". ", " ░"), palette.HAUNT_FOG, palette.HAUNT_BG,
)
BARK = TileType(
    "bark", ("_,", ",_", "._"), palette.HAUNT_BARK, palette.HAUNT_BG,
)
GNARLED_TRUNK = TileType(
    "gnarled tree", ("▐▌",), palette.HAUNT_TRUNK, palette.HAUNT_BG,
    solid=True, blocks_shots=True,
)
STUMP = TileType(
    "stump", ("▄_", "_▄"), palette.HAUNT_STUMP, palette.HAUNT_BG,
    solid=True, blocks_shots=True, hp=config.STUMP_HP, becomes=BARK,
)
LOG_LEFT = TileType(
    "log", ("(=",), palette.HAUNT_LOG, palette.HAUNT_BG,
    solid=True, blocks_shots=True, hp=config.LOG_HP, becomes=BARK,
)
LOG_MID = TileType(
    "log", ("==",), palette.HAUNT_LOG, palette.HAUNT_BG,
    solid=True, blocks_shots=True, hp=config.LOG_HP, becomes=BARK,
)
LOG_RIGHT = TileType(
    "log", ("=)",), palette.HAUNT_LOG, palette.HAUNT_BG,
    solid=True, blocks_shots=True, hp=config.LOG_HP, becomes=BARK,
)


def _crown(glyph: str, fg) -> TileType:
    return TileType("branches", (glyph,), fg, palette.HAUNT_BG)


# A tree's walkable crown and roots, by offset from the trunk (dx, dy):
# twigs on top, branches spreading to the sides, roots below.
CROWN = {
    (-1, -2): _crown(" ,", palette.HAUNT_TWIG), (0, -2): _crown(r"\/", palette.HAUNT_TWIG),
    (1, -2): _crown(". ", palette.HAUNT_TWIG),
    (-1, -1): _crown(r"\_", palette.HAUNT_BRANCH), (0, -1): _crown(r"\/", palette.HAUNT_BRANCH),
    (1, -1): _crown("_/", palette.HAUNT_BRANCH),
    (-1, 0): _crown("-\\", palette.HAUNT_BRANCH), (1, 0): _crown("/-", palette.HAUNT_BRANCH),
    (-1, 1): _crown(" _", palette.HAUNT_ROOT), (0, 1): _crown("┘└", palette.HAUNT_ROOT),
    (1, 1): _crown("_ ", palette.HAUNT_ROOT),
}

# Desert: sand, dunes, cacti and mesa rock.
SAND = TileType(
    "sand", ("  ", ". ", " .", "  ", "  "), palette.SAND_FG, palette.SAND_BG,
)
DUNE = TileType(
    "dunes", ("--", "-.", ".-", "_-"), palette.DUNE_FG, palette.SAND_BG,
)
# M28.5b: Sand Slippers' dune: walked over, but shots stop at it.
SAND_HEAP = TileType(
    "sand heap", ("/\\", "^^"), palette.SAND_HEAP_FG, palette.SAND_BG,
    blocks_shots=True,
)
CACTUS_DEBRIS = TileType(
    "cactus pulp", ("_.", "._", ",."), palette.CACTUS_FG, palette.SAND_BG,
)
CACTUS = TileType(
    "cactus", ("Y ", " Y", "Y'", "'Y"), palette.CACTUS_FG, palette.SAND_BG,
    solid=True, blocks_shots=True, hp=config.CACTUS_HP,
    becomes=CACTUS_DEBRIS,
)
MESA = TileType(
    "mesa rock", ("▓▓", "▓▒", "▒▓"), palette.MESA_FG, palette.MESA_BG,
    solid=True, blocks_shots=True,
)

# Ruins: concrete lots and broken buildings (built from WALL / RUBBLE).
CONCRETE = TileType(
    "concrete", ("  ", ". ", " .", "  ", ":."), palette.CONCRETE_FG, palette.CONCRETE_BG,
)

# Swamp: mud, reeds, bog pools (like water: can't be walked through, shots fly over)
# and mangroves.
MUD = TileType(
    "mud", ("  ", ", ", " .", "  "), palette.MUD_FG, palette.MUD_BG,
)
# P11: a lizardman's javelin stuck in the ground: in the way for a few s
# (systems/combat._shot_ends plants it; the zone it leaves puts the ground
# back, systems/zones.update_zones).
STUCK_JAVELIN = TileType(
    "stuck javelin", ("/ ", " /", "\\ ", " \\"), palette.JAVELIN_FG, palette.MUD_BG,
    solid=True, blocks_shots=False, hp=12,
)
REEDS = TileType(
    "reeds", ("|'", "'|", "||", "|,"), palette.REED_FG, palette.MUD_BG,
)
BOG = TileType(
    "bog", ("░ ", " ░", "  ", "  "), palette.BOG_FG, palette.BOG_BG,
    solid=True,
)
MANGROVE_ROOTS = TileType(
    "roots", ("_,", ",_", "._"), palette.MANGROVE_FG, palette.MUD_BG,
)
MANGROVE = TileType(
    "mangrove", ("%%", "%&", "&%"), palette.MANGROVE_FG, palette.MANGROVE_BG,
    solid=True, blocks_shots=True, hp=config.MANGROVE_HP,
    wear=(("%.", ".%"),),
    becomes=MANGROVE_ROOTS,
)

# Mushroom: purple mycelium, glowing spores, giant mushrooms.
MYCELIUM = TileType(
    "mycelium", ("  ", ". ", " ,", "  "), palette.MYCELIUM_FG, palette.MYCELIUM_BG,
)
SPORES = TileType(
    "spores", ("o ", " o", ".o", "o."), palette.SPORE_FG, palette.MYCELIUM_BG,
)
SHROOM_MUSH = TileType(
    "mush", ("..", ".,", ",."), palette.SHROOM_FG, palette.MYCELIUM_BG,
)
GIANT_SHROOM = TileType(
    "giant mushroom", ("()", "{}", "()"), palette.SHROOM_FG, palette.SHROOM_BG,
    solid=True, blocks_shots=True, hp=config.SHROOM_HP,
    wear=((") ", " (", "(."),),
    becomes=SHROOM_MUSH,
)


# --- Landmarks (M17, world/landmarks.py) -----------------------------------------------
# Hand-placed structures stamped over the generated biome. None of their
# walls can be destroyed: quest places must survive the fight.

# A boss lair's ring of standing stones, and the thorn gate that seals it.
LAIR_STONE = TileType(
    "standing stones", ("▓▓", "█▓", "▓█"), palette.LAIR_STONE_FG, palette.LAIR_STONE_BG,
    solid=True, blocks_shots=True,
)
THORN_GATE = TileType(
    "thorn gate", ("><", "}{", "X>", "<X"), palette.THORN_FG, palette.THORN_BG,
    solid=True, blocks_shots=True,
)
# Froggy's pools: like bog (can't be walked through, shots fly over), and
# the boss dives into them.
POND = TileType(
    "pond", ("░ ", " ░", "  ", "▒░"), palette.POND_FG, palette.POND_BG,
    solid=True,
)
LILY_PADS = TileType(
    "lily pads", ("o ", " o", "  ", "o."), palette.LILY_FG, palette.MUD_BG,
)
# The leech doctor's quest (M22): her bog and the Blood Mire are the frog
# hunter's and the pond's layouts in blood (world/landmarks.SKINS).
BLOOD_POOL = TileType(
    "blood pool", ("░ ", " ░", "  ", "▒░"), palette.BLOOD_FG, palette.BLOOD_BG,
    solid=True,
)
CLOTS = TileType(
    "clots", ("o ", " o", "  ", "o."), palette.CLOT_FG, palette.MUD_BG,
)
# The smoke keeper's quest (M22.2): her bog and the Stagnant Court are the
# same layouts gone stagnant (world/landmarks.SKINS); her braziers stand
# at the quest's spots, lit one by one (systems/quests.py).
STAGNANT = TileType(
    "stagnant water", ("░ ", " ░", "  ", "▒░"), palette.STAGNANT_FG, palette.STAGNANT_BG,
    solid=True,
)
SCUM = TileType(
    "scum", (", ", " ,", "  ", ".,"), palette.SCUM_FG, palette.MUD_BG,
)
BRAZIER = TileType(
    "cold brazier", ("[]",), palette.BRAZIER_FG, palette.BRAZIER_BG,
    solid=True,
)
BRAZIER_LIT = TileType(
    "smoking brazier", ("[]",), palette.BRAZIER_LIT_FG, palette.BRAZIER_LIT_BG,
    solid=True,
)
# The frog hunter's hut on its deck.
PLANK_WALL = TileType(
    "plank wall", ("||", "|:", ":|"), palette.PLANK_FG, palette.PLANK_BG,
    solid=True, blocks_shots=True,
)
DECK = TileType(
    "deck", ("==", "=-", "-="), palette.DECK_FG, palette.DECK_BG,
)
DRYING_RACK = TileType(
    "drying rack", ("TT", "T'", "'T"), palette.RACK_FG, palette.DECK_BG,
    solid=True,
)
# Where a quest giver stands (on the deck, so nobody walks through them).
HUNTER_POST = TileType(
    "hunter's post", ("==",), palette.DECK_FG, palette.DECK_BG,
    solid=True,
)
# The desert's landmarks (M23.1, world/landmarks.py): the scarab collector's
# tent by an oasis, and the Dung Pit -- a sunken arena walled and pillared
# in sandstone (solid: Khepri's ball shatters on it), with sand pits.
SANDSTONE = TileType(
    "sandstone", ("▓▓", "▓▒", "▒▓"), palette.SANDSTONE_FG, palette.SANDSTONE_BG,
    solid=True, blocks_shots=True,
)
SAND_PIT = TileType(
    "sand pit", ("..", ": ", " :", ".:"), palette.SAND_PIT_FG, palette.SAND_PIT_BG,
)
OASIS = TileType(
    "oasis", ("░ ", " ░", "  ", "▒░"), palette.OASIS_FG, palette.OASIS_BG,
    solid=True,
)
PALM = TileType(
    "palm", ("T ", " T", "Y'"), palette.PALM_FG, palette.SAND_BG,
    solid=True, blocks_shots=True,
)
TENT = TileType(
    "tent", ("/\\", "\\/", "/\\"), palette.TENT_FG, palette.TENT_BG,
    solid=True, blocks_shots=True,
)
RUG = TileType(
    "rug", (". ", " .", "  ", "  "), palette.RUG_FG, palette.RUG_BG,
)
STALL = TileType(
    "collector's stall", ("oo", "o:", ":o"), palette.STALL_FG, palette.RUG_BG,
    solid=True,
)
NOMAD_POST = TileType(
    "collector's post", ("##",), palette.RUG_FG, palette.RUG_BG,
    solid=True,
)
# Ol' Spitter's caravanserai (M23.2, world/landmarks._caravanserai): a ring
# of mud brick round a flagstone yard, arcades of brick arches (cover; his
# loogies bounce off them), stone water troughs he drinks from (smash one
# while he drinks and he chokes: they're the only tiles here you can
# break), tethering posts and hay. The caravan master's lost cargo
# bundles sit in the quest's clearings, and crates stand at his camp.
MUDBRICK = TileType(
    "mud brick", ("▓▓", "▓▒", "▒▓", "▓▓"), palette.MUDBRICK_FG, palette.MUDBRICK_BG,
    solid=True, blocks_shots=True,
)
FLAGSTONE = TileType(
    "flagstones", ("  ", "_ ", " _", "  ", ". "), palette.FLAGSTONE_FG, palette.FLAGSTONE_BG,
)
ARCH = TileType(
    "brick arch", ("██", "▓█", "█▓"), palette.ARCH_FG, palette.ARCH_BG,
    solid=True, blocks_shots=True,
)
TROUGH_BROKEN = TileType(
    "broken trough", (".,", ",.", ":."), palette.TROUGH_BROKEN_FG, palette.FLAGSTONE_BG,
)
TROUGH = TileType(
    "water trough", ("==",), palette.TROUGH_FG, palette.TROUGH_BG,
    solid=True, blocks_shots=True, hp=config.TROUGH_HP,
    wear=(("=:", ":="),), becomes=TROUGH_BROKEN,
)
TETHER_POST = TileType(
    "tethering post", ("||", "|'", "'|"), palette.POST_FG, palette.FLAGSTONE_BG,
    solid=True,
)
HAY = TileType(
    "hay", ("\"'", "'\"", ",'"), palette.HAY_FG, palette.FLAGSTONE_BG,
)
CARGO = TileType(
    "cargo bundle", ("[#",), palette.CARGO_FG, palette.CARGO_BG,
    solid=True,
)
# M28.4b: a chest of gear (systems/chests.py), shut and opened. A mimic
# looks exactly like a shut one until it's touched.
CHEST = TileType(
    "chest", ("[$",), palette.CHEST_FG, palette.CHEST_BG,
    solid=True,
)
CHEST_OPEN = TileType(
    "open chest", ("[_",), palette.CHEST_OPEN_FG, palette.CHEST_OPEN_BG,
    solid=True,
)
CRATES = TileType(
    "crates", ("[]", "#]", "[#"), palette.CRATES_FG, palette.RUG_BG,
    solid=True,
)
# The Nameless Magus's sunken observatory (M23.3, world/landmarks.
# _observatory) and the runaway apprentice's star circles. His dune walls
# (he raises them in the fight) are solid sand you can shoot through.
GLAZED = TileType(
    "glazed stone", ("▓▓", "▓▒", "▒▓"), palette.GLAZED_FG, palette.GLAZED_BG,
    solid=True, blocks_shots=True,
)
SLABS = TileType(
    "sandstone slabs", ("  ", ". ", "  ", "_ ", " ."), palette.SLAB_FG, palette.SLAB_BG,
)
STAR_CHART = TileType(
    "star chart", ("* ", " .", "  ", ". ", " +", "  "), palette.CHART_FG, palette.CHART_BG,
)
COLUMN = TileType(
    "column", ("██", "▓█", "█▓"), palette.COLUMN_FG, palette.COLUMN_BG,
    solid=True, blocks_shots=True,
)
BROKEN_COLUMN = TileType(
    "broken column", ("o.", ".o", "oo"), palette.COLUMN_FG, palette.SLAB_BG,
)
BRASS = TileType(
    "brass telescope", ("==", "=O", "O="), palette.BRASS_FG, palette.BRASS_BG,
    solid=True, blocks_shots=True,
)
DRIFT = TileType(
    "sand drift", ("..", ".:", ":."), palette.DRIFT_FG, palette.SLAB_BG,
)
STAR_RING = TileType(
    "star ring", ("* ", " *", "+ ", " +"), palette.STAR_RING_FG, palette.SAND_BG,
)
SEAL = TileType(
    "seal", ("<>",), palette.SEAL_FG, palette.SAND_BG,
)
SEAL_BROKEN = TileType(
    "broken seal", ("><",), palette.SEAL_BROKEN_FG, palette.SAND_BG,
)
DUNE_WALL = TileType(
    "sand wall", ("▒▒", "▒░", "░▒"), palette.DUNE_WALL_FG, palette.DUNE_WALL_BG,
    solid=True, blocks_shots=True, hp=config.DUNE_HP, becomes=SLABS,
)
SCROLLS = TileType(
    "scroll rack", ("=]", "[=", "=="), palette.SCROLLS_FG, palette.RUG_BG,
    solid=True,
)
# The Fallout King's reactor vault (M24.1, world/landmarks._reactor_vault)
# and the hazmat scavenger's scrap camp and beacon sites.
VAULT_WALL = TileType(
    "vault wall", ("▓▓", "▓▒", "▒▓"), palette.VAULT_WALL_FG, palette.VAULT_WALL_BG,
    solid=True, blocks_shots=True,
)
REACTOR = TileType(    # (a low, cracked housing: shots fly over it, nobody walks through)
    "reactor", ("██", "▓█", "█▓", "▒█"), palette.REACTOR_FG, palette.REACTOR_BG,
    solid=True,
)
CONC_PILLAR = TileType(
    "concrete pillar", ("██", "▓█", "█▓"), palette.PILLAR_FG, palette.PILLAR_BG,
    solid=True, blocks_shots=True,
)
PIPE = TileType(
    "pipe", ("==", "=+", "+="), palette.PIPE_FG, palette.PIPE_BG,
    solid=True,
)
VALVE = TileType(
    "coolant valve", ("@=",), palette.VALVE_FG, palette.PIPE_BG,
    solid=True,
)
VALVE_SHUT = TileType(
    "shut valve", ("@=",), palette.VALVE_SHUT_FG, palette.PIPE_BG,
    solid=True,
)
SHOWER = TileType(
    "shower", ("::", ".:", ":."), palette.SHOWER_FG, palette.CONCRETE_BG,
)
SHOWER_OFF = TileType(
    "dry shower", ("..",), palette.SHOWER_OFF_FG, palette.CONCRETE_BG,
)
LEAD = TileType(
    "lead wall", ("██", "▓█"), palette.LEAD_FG, palette.LEAD_BG,
    solid=True, blocks_shots=True,
)
GRATE = TileType(
    "sewer grate", ("##",), palette.GRATE_FG, palette.CONCRETE_BG,
)
BEACON_SITE = TileType(
    "beacon site", ("[]",), palette.BEACON_FG, palette.CONCRETE_BG,
)
BEACON = TileType(
    "beacon", ("|*",), palette.BEACON_FG, palette.CONCRETE_BG,
    solid=True,
)
SLUDGE = TileType(
    "sludge", ("░ ", " ░", "  ", "▒░"), palette.SLUDGE_FG, palette.SLUDGE_BG,
    solid=True,
)
PLATES = TileType(
    "metal plates", ("[]", "  ", "_ "), palette.PLATES_FG, palette.PLATES_BG,
)
SCRAP_WALL = TileType(
    "scrap wall", ("#]", "[#", "##"), palette.SCRAP_FG, palette.SCRAP_BG,
    solid=True, blocks_shots=True,
)
SCRAP_POST = TileType(
    "scavenger's post", ("##",), palette.PLATES_FG, palette.PLATES_BG,
    solid=True,
)
# The Snow King's frozen throne hall (M24.2, world/landmarks._throne_hall)
# and the searching sister's captives (ice blocks you shatter).
ICE_WALL = TileType(
    "ice wall", ("▓▓", "▓▒", "▒▓"), palette.ICE_WALL_FG, palette.ICE_WALL_BG,
    solid=True, blocks_shots=True,
)
FROST_STONE = TileType(
    "frost stone", ("  ", "  ", ". ", "  ", " ."), palette.FROST_FG, palette.FROST_BG,
)
THRONE = TileType(
    "ice throne", ("██", "▓█", "█▓"), palette.THRONE_FG, palette.THRONE_BG,
    solid=True, blocks_shots=True,
)
ICE_PILLAR = TileType(
    "ice pillar", ("██", "▓█", "█▓"), palette.ICE_PILLAR_FG, palette.ICE_PILLAR_BG,
    solid=True, blocks_shots=True, hp=config.ICE_PILLAR_HP,
    wear=(("▓▒", "▒▓"),), becomes=FROST_STONE,
)
FIRE_BOWL = TileType(
    "fire brazier", ("[]",), palette.FIRE_FG, palette.FROST_BG,
    solid=True,
)
FIRE_BOWL_LIT = TileType(
    "lit fire brazier", ("[]",), palette.FIRE_LIT_FG, palette.FROST_BG,
    solid=True,
)
STATUE = TileType(
    "frozen statue", ("&&", "&@", "@&"), palette.STATUE_FG, palette.STATUE_BG,
    solid=True, blocks_shots=True,
)
SNOWDRIFT = TileType(
    "snowdrift", ("..", ".:", ":."), palette.SNOWDRIFT_FG, palette.FROST_BG,
)
SLUSH = TileType(
    "slush", (". ", " ,", ".,"), palette.SLUSH_FG, palette.CONCRETE_BG,
)
ICE_BLOCK = TileType(
    "ice block", ("[]", "[]"), palette.ICE_BLOCK_FG, palette.ICE_BLOCK_BG,
    solid=True, blocks_shots=True, hp=config.RESCUE_BLOCK_HP,
    wear=(("[:", ":]"), (":.", ".:")), becomes=SLUSH,
)
FROZEN_POND = TileType(
    "frozen pond", ("░ ", " ░", "  ", "▒░"), palette.FROZEN_POND_FG, palette.FROZEN_POND_BG,
    solid=True,
)
# Fragile's ruined ballroom (M24.3, world/landmarks._ballroom) and the
# pawn dealer's quest (the pieces of Mr. Buttons).
CASTLE_WALL = TileType(
    "castle wall", ("▓▓", "▓▒", "▒▓"), palette.CASTLE_FG, palette.CASTLE_BG,
    solid=True, blocks_shots=True,
)
PARQUET = TileType(
    "parquet", ("  ", "_ ", "  ", " _", "  "), palette.PARQUET_FG, palette.PARQUET_BG,
)
SHUTTER = TileType(
    "shuttered window", ("##", "#|", "|#"), palette.SHUTTER_FG, palette.SHUTTER_BG,
    solid=True, blocks_shots=True,
)
WINDOW_OPEN = TileType(
    "open window", ("░░", "▒░", "░▒"), palette.WINDOW_OPEN_FG, palette.WINDOW_OPEN_BG,
    solid=True, blocks_shots=True,
)
LEVER = TileType(
    "lever", ("/_",), palette.LEVER_FG, palette.PARQUET_BG,
)
MARBLE = TileType(
    "marble pillar", ("██", "▓█", "█▓"), palette.MARBLE_FG, palette.MARBLE_BG,
    solid=True, blocks_shots=True,
)
COFFIN = TileType(
    "coffin", ("[]", "[+"), palette.COFFIN_FG, palette.COFFIN_BG,
    solid=True,
)
COFFIN_STAKED = TileType(
    "staked coffin", ("[X",), palette.MAP_TILE["staked coffin"], palette.COFFIN_BG,
    solid=True,
)
VELVET_THRONE = TileType(
    "velvet throne", ("██", "▓█"), palette.VELVET_FG, palette.VELVET_BG,
    solid=True, blocks_shots=True,
)
MIRROR = TileType(
    "cracked mirror", ("|/", "/|", "||"), palette.MIRROR_FG, palette.CASTLE_BG,
    solid=True, blocks_shots=True,
)
CHANDELIER_RUBBLE = TileType(
    "fallen chandelier", ("*#", "#*", "**"), palette.CHANDELIER_FG, palette.PARQUET_BG,
    solid=True, blocks_shots=True, hp=60, becomes=PARQUET,
)
BEAR_PIECE = TileType(
    "bear piece", ("@,",), palette.PIECE_FG, palette.CONCRETE_BG,
    solid=True,
)

# --- Nettle's withered glade and the hedge witch's shrines (M25.1) ----------------------

SHRINE = TileType(
    "blighted shrine", ("[]",), palette.SHRINE_FG, palette.HAUNT_BG,
)
SHRINE_CLEAN = TileType(
    "cleansed shrine", ("[]",), palette.SHRINE_CLEAN_FG, palette.HAUNT_BG,
)
ROT_RING = TileType(
    # The ring you stand in to cleanse a shrine.
    "rot ring", ("; ", " ;", "' ", " '"), palette.ROT_RING_FG, palette.HAUNT_BG,
)
BRAMBLE_WALL = TileType(
    "bramble", ("#%", "%#", "##", "%%"), palette.BRAMBLE_FG, palette.BRAMBLE_BG,
    solid=True, blocks_shots=True,
)
TOADSTOOL = TileType(
    # A giant toadstool: cover (Nettle flies over them; her shots don't).
    "giant toadstool", ("nn", "Nn", "nN"), palette.TOADSTOOL_FG, palette.TOADSTOOL_BG,
    solid=True, blocks_shots=True,
)
HOLLOW_TREE = TileType(
    "hollow tree", ("██", "▓█", "█▓"), palette.HOLLOW_TREE_FG, palette.HAUNT_BG,
    solid=True, blocks_shots=True,
)
GROWCAP = TileType(
    # Glowing: stand on one to grow back from Nettle's dust.
    "growcap", ("n'", "'n"), palette.GROWCAP_FG, palette.HAUNT_BG,
)
GROWCAP_SPENT = TileType(
    "spent growcap", ("n.", ".n"), palette.GROWCAP_SPENT_FG, palette.HAUNT_BG,
)

# --- Love & Cuddles' hollow oak and the forester's nut caches (M25.2) --------------------

NUT_SHELLS = TileType(
    # A trail of nut shells leading to a cache (just a look: walkable).
    "nut shells", ("c ", " c", "c,", ",c"), palette.NUT_SHELL_FG, palette.HAUNT_BG,
)
NUT_SPILL = TileType(
    "spilt nuts", ("c.", ".c", "c:"), palette.NUT_SHELL_FG, palette.HAUNT_BG,
)
NUT_CACHE = TileType(
    # A squirrel's hoard in a hollow log: break it (a "destroy" quest).
    "nut cache", ("(@",), palette.NUT_CACHE_FG, palette.NUT_CACHE_BG,
    solid=True, blocks_shots=True, hp=config.CACHE_HP, wear=(("(.",), ("..",)),
    becomes=NUT_SPILL,
)
WOODPILE = TileType(
    "woodpile", ("==", "=o", "o="), palette.WOODPILE_FG, palette.DECK_BG,
    solid=True,
)
OAK_ROOTS = TileType(
    "oak roots", ("&#", "#&", "##", "&&"), palette.OAK_ROOTS_FG, palette.OAK_ROOTS_BG,
    solid=True, blocks_shots=True,
)
OAK_TRUNK = TileType(
    # A big climbing oak's trunk. "Destructible" only so a shot or a hit on
    # it is counted (world.hp_at): Love & Cuddles up in it is shaken out
    # once enough lands. It never breaks.
    "climbing oak", ("██", "▓█", "█▓"), palette.OAK_TRUNK_FG, palette.HAUNT_BG,
    solid=True, blocks_shots=True, hp=10 ** 9,
)
OAK_CROWN = TileType(
    # The oak's crown, drawn on the ground round its trunk (a look: walkable).
    "oak crown", ("&%", "%&", "&&", "& "), palette.OAK_CROWN_FG, palette.HAUNT_BG,
)

# --- The Fallen's still grove and the lumberjack's marked trees (M25.3) ------------------

FELLED = TileType(
    # What a felled marked tree leaves: a stump with red paint (walkable).
    "felled tree", ("_.", "._"), palette.MARKED_FG, palette.HAUNT_BG,
)
MARKED_TREE = TileType(
    # A tree marked with red paint: fell it (a "fell" quest).
    "marked tree", ("Ax",), palette.MARKED_FG, palette.HAUNT_BG,
    solid=True, blocks_shots=True, hp=config.MARKED_HP, wear=(("A.",), ("a.",)),
    becomes=FELLED,
)
SAWHORSE = TileType(
    "sawhorse", ("XX", "X=", "=X"), palette.WOODPILE_FG, palette.DECK_BG,
    solid=True,
)
THICKET = TileType(
    "thicket", ("Y#", "#Y", "YY", "##"), palette.THICKET_FG, palette.THICKET_BG,
    solid=True, blocks_shots=True,
)
GROVE_TRUNK = TileType(
    # The foot of one of the still grove's trees (painted over by the tree,
    # render/fallen.py). "Destructible" only so a hit on it is counted
    # (world.hp_at); it never breaks.
    "grove tree", ("▐▌",), palette.HAUNT_TRUNK, palette.HAUNT_BG,
    solid=True, blocks_shots=True, hp=10 ** 9,
)
FALLEN_TRUNK = TileType(
    # The great fallen trunk across the grove (cover).
    "fallen trunk", ("==", "=#", "#="), palette.FALLEN_TRUNK_FG, palette.HAUNT_BG,
    solid=True, blocks_shots=True,
)
GROVE_FIRE = TileType(
    # A fire bowl: The Fallen's roots burn away near one.
    "fire bowl", ("[]",), palette.FIRE_LIT_FG, palette.HAUNT_BG,
    solid=True,
)

# --- Mycelium: the "sever" quests' nodes (M26) and the fly agaric's fruiting ring (M26.1) ---

MYC_NODE = TileType(
    # A Mycelium node pulsing under the ground: stand on it to sever it.
    "mycelium node", ("{}",), palette.MYC_NODE_FG, palette.MYCELIUM_BG,
)
NODE_SPILL_RED = TileType(
    # A severed node, spilling red-and-white specks (the fly agaric's hint).
    "severed node", ("*.", ".*", ":*"), palette.SPILL_RED_FG, palette.MYCELIUM_BG,
)
SHROOM_WALL = TileType(
    "mushroom thicket", ("()", "{}", ")(", "()"), palette.SHROOM_WALL_FG, palette.SHROOM_BG,
    solid=True, blocks_shots=True,
)
RING_SHROOMS = TileType(
    # A fruiting ring's little mushrooms (a look: walkable).
    "fruiting ring", ("n ", " n", "n."), palette.RING_SHROOM_FG, palette.MYCELIUM_BG,
)
NET_NODE_DEAD = TileType(
    "broken node", (":.", ".:"), palette.MYCELIUM_FG, palette.MYCELIUM_BG,
)
NET_NODE = TileType(
    # A fruiting ring's node: Mycelium travels the threads between them.
    # Break it and that ring's cut out (it regrows: ai/bosses.Amanita).
    "network node", ("@@",), palette.NET_NODE_FG, palette.SHROOM_BG,
    solid=True, blocks_shots=True, hp=config.NODE_HP, wear=(("@.",),), becomes=NET_NODE_DEAD,
)

# --- Mycelium the shaggy ink cap (M26.2) --------------------------------------------------

NODE_SPILL_INK = TileType(
    # A severed node, spilling black ink (the shaggy ink cap's hint).
    "inky node", ("%.", ".%", "%:"), palette.SPILL_INK_FG, palette.MYCELIUM_BG,
)
OLD_PAVING = TileType(
    # Old cracked paving the ink caps push up through (walkable).
    "old paving", ("_|", "|_", "__", "_ "), palette.PAVING_FG, palette.PAVING_BG,
)
INK_STAIN = TileType(
    "ink stain", (";.", ".;", ";;"), palette.SPILL_INK_FG, palette.MYCELIUM_BG,
)

# --- Mycelium the giant puffball (M26.3) --------------------------------------------------

NODE_SPILL_DUST = TileType(
    # A severed node, puffing olive-brown dust (the giant puffball's hint).
    "dusty node", ("``", "` ", " `"), palette.SPILL_DUST_FG, palette.MYCELIUM_BG,
)
SPORE_DUST = TileType(
    # Drifts of olive-brown spore dust on the floor (walkable).
    "spore dust", ("` ", " `", ". ", "``"), palette.SPILL_DUST_FG, palette.MYCELIUM_BG,
)

# --- More than Life's necropolis (M27) ----------------------------------------------------

GRAVE_SOIL = TileType(
    "grave soil", (". ", " .", "  ", ", "), palette.GRAVE_SOIL_FG, palette.GRAVE_SOIL_BG,
)
BONE_LITTER = TileType(
    "bone litter", ("_ ", " _", "  ", ". "), palette.BONE_LITTER_FG, palette.GRAVE_SOIL_BG,
)
RITUAL_RING = TileType(
    "ritual ring", ("::", ": ", " :"), palette.RITUAL_FG, palette.GRAVE_SOIL_BG,
)
GRAVESTONE = TileType(
    # A grave: cover from his gaze and his shots.
    "gravestone", ("▐▌", "▄▄", "▐▌"), palette.GRAVESTONE_FG, palette.GRAVE_SOIL_BG,
    solid=True, blocks_shots=True,
)
MAUSOLEUM = TileType(
    "mausoleum", ("██", "▓█", "█▓"), palette.MAUSOLEUM_FG, palette.GRAVE_SOIL_BG,
    solid=True, blocks_shots=True,
)
CRYPT_WALL = TileType(
    "crypt wall", ("▓▓", "▓▒", "▒▓"), palette.CRYPT_FG, palette.CRYPT_BG,
    solid=True, blocks_shots=True,
)
SEALED_GATE = TileType(
    # The necropolis gate, sealed with bone until the guardians fall.
    "bone gate", ("##", "#=", "=#"), palette.BONE_FG, palette.CRYPT_BG,
    solid=True, blocks_shots=True,
)
BONE_WALL = TileType(
    # A wall of bone he raises in the fight; it crumbles (or shoot it down).
    "bone wall", ("#%", "%#", "##"), palette.BONE_FG, palette.GRAVE_SOIL_BG,
    solid=True, blocks_shots=True, hp=config.NECRO_BONE_WALL_HP, becomes=BONE_LITTER,
)


# --- Paradise (M29.1, design/OCEAN.md 3) ---------------------------------------------
# Marble and clouds: soft cloud ground, marble roads lined with gold posts,
# white blossom trees, marble columns standing and fallen, a cloud bank
# instead of a beach. Red comes only from blood: the river, the fonts, the
# weeping statues' tears. (Ground stays dark so shots read on it; the white
# is in the glyphs.)
CLOUD = TileType(
    "cloud", ("  ", "  ", "  ", "  ", ". ", " '"), palette.CLOUD_FG, palette.CLOUD_BG,
)
CLOUD_DRIFT = TileType(
    "cloud drift", ("░ ", " ░", "  ", "░░", "  "), palette.CLOUD_DRIFT_FG, palette.CLOUD_BG,
)
PETALS = TileType(
    # What a felled blossom tree leaves.
    "petals", (", ", "'.", ".,", " '"), palette.PETALS_FG, palette.CLOUD_BG,
)
BLOSSOM = TileType(
    "blossom tree", ("**", "*@", "@*", "@@"), palette.BLOSSOM_FG, palette.BLOSSOM_BG,
    solid=True, blocks_shots=True, hp=config.TREE_HP,
    wear=(("*,", ",*", "@."),),
    becomes=PETALS,
)
MARBLE_RUBBLE = TileType(
    "marble rubble", (".:", ":.", ";.", ".;"), palette.MARBLE_RUBBLE_FG, palette.CLOUD_BG,
)
MARBLE_COLUMN = TileType(
    # A standing column: a white shaft in the middle of the tile. The
    # Behemoth breaks them (M29.3); so can you.
    "marble column", ("▐▌",), palette.MARBLE_COLUMN_FG, palette.CLOUD_BG,
    solid=True, blocks_shots=True, hp=config.WALL_HP,
    wear=(("▐▒", "▒▌"),),
    becomes=MARBLE_RUBBLE,
)
FALLEN_COLUMN = TileType(
    # A column lying on its side: low cover, like the forest's logs.
    "fallen column", ("▄▄",), palette.FALLEN_COLUMN_FG, palette.CLOUD_BG,
    solid=True, blocks_shots=True, hp=config.LOG_HP,
    becomes=MARBLE_RUBBLE,
)
MARBLE_ROAD = TileType(
    "marble road", ("  ", ". ", " .", "_.", "  "), palette.MARBLE_ROAD_FG, palette.MARBLE_ROAD_BG,
)
GOLD_POST = TileType(
    # The roads' posts: they stop you, not shots.
    "gold post", ("| ", " |"), palette.GOLD, palette.CLOUD_BG,
    solid=True,
)
STEP = TileType(
    # The terraces round the summit (Paradise climbs gently to its centre).
    "marble step", ("__",), palette.STEP_FG, palette.STEP_BG,
)
BLOOD_RIVER = TileType(
    # Watery: only water walkers cross it (heroes here always are).
    "blood river", ("░ ", " ░", "  ", "▒░", "  "), palette.PARADISE_BLOOD_FG, palette.PARADISE_BLOOD_BG,
    solid=True,
)
MARBLE_BRIDGE = TileType(
    "marble bridge", ("==",), palette.BRIDGE_FG, palette.BRIDGE_BG,
)
CLOUD_BANK = TileType(
    # The sea round Paradise, turned to cloud: watery, like the ocean.
    "cloud bank", ("░░", "▒░", "░▒", "░ ", " ░"), palette.CLOUD_BANK_FG, palette.CLOUD_BANK_BG,
    solid=True,
)
MARBLE_FLOOR = TileType(
    "marble floor", ("  ", ". ", "  ", " ."), palette.MARBLE_FLOOR_FG, palette.MARBLE_FLOOR_BG,
)
GOLD_INLAY = TileType(
    "gold inlay", ("::", ".:", ":."), palette.GOLD, palette.MARBLE_FLOOR_BG,
)
PEARL_WALL = TileType(
    "pearl wall", ("██", "▓█", "█▓"), palette.PEARL, palette.PEARL_BG,
    solid=True, blocks_shots=True,
)
GATE_PILLAR = TileType(
    "gate pillar", ("██",), palette.GOLD, palette.GOLD_DARK,
    solid=True, blocks_shots=True,
)
GATE_BARS = TileType(
    # Golden bars: the Gate's closed leaf, and the summit court's seal
    # (until the seventh seal breaks, M29.4). They stop you, not shots.
    "golden bars", ("||",), palette.GOLD, palette.MARBLE_FLOOR_BG,
    solid=True,
)
GOLD_THRONE = TileType(
    "throne", ("██", "▓▓"), palette.GOLD, palette.PEARL_BG,
    solid=True, blocks_shots=True,
)
ALTAR = TileType(
    "altar", ("##",), palette.GOLD, palette.PEARL_BG,
    solid=True, blocks_shots=True,
)
CHOIR_STATUE = TileType(
    # A choir ring's singing statue.
    "statue", ("&&",), palette.CHOIR_STATUE_FG, palette.CHOIR_STATUE_BG,
    solid=True, blocks_shots=True,
)
WEEPING_STATUE = TileType(
    # A saint crying red tears; its blood trickles away over the marble.
    "weeping statue", ("&,", ",&"), palette.CHOIR_STATUE_FG, palette.PARADISE_BLOOD_BG,
    solid=True, blocks_shots=True,
)
BLOOD_TRICKLE = TileType(
    "blood trickle", (",.", ".,", ";,", ",;"), palette.BLOOD_TRICKLE_FG, palette.BLOOD_TRICKLE_BG,
)
BLOOD_FONT = TileType(
    # A marble basin's blood: unveiled angels drink here to heal (M29.2).
    "blood font", ("▒▒", "▓▒", "▒▓"), palette.PARADISE_BLOOD_FG, palette.PARADISE_BLOOD_BG,
    solid=True,
)
FONT_RIM = TileType(
    "font rim", ("[]",), palette.FONT_RIM_FG, palette.FONT_RIM_BG,
    solid=True,
)
STAIR = TileType(
    # The stairway to nowhere: white steps climbing out of the island.
    "white stair", ("==",), palette.STAIR_FG, palette.STAIR_BG,
)
STAIR_END = TileType(
    # Its last steps, fading into the air.
    "white stair", ("=-", "-=", "- "), palette.STAIR_FG, palette.CLOUD_BG,
)
BALUSTRADE = TileType(
    "balustrade", ("::",), palette.CHOIR_STATUE_FG, palette.CLOUD_BG,
    solid=True,
)
CHAIN_POST = TileType(
    # Where the fallen angel is chained (the giver, M29.4).
    "chain post", ("8|",), palette.CHAIN_FG, palette.CLOUD_BG,
    solid=True, blocks_shots=True,
)
GLASS_RED = TileType(
    # The fallen cathedral's shattered rose window, on the floor.
    "rose glass", ("*.", ".*", ",*"), palette.GLASS["red"], palette.MARBLE_FLOOR_BG,
)
GLASS_BLUE = TileType(
    "rose glass", ("*.", ".*", "*,"), palette.GLASS["blue"], palette.MARBLE_FLOOR_BG,
)
GLASS_GOLD = TileType(
    "rose glass", (".*", "*.", "*'"), palette.GLASS["gold"], palette.MARBLE_FLOOR_BG,
)


# --- Blood on Paradise (M29.2, design/OCEAN.md 3) ------------------------------------
# Unveiled angels bleed where they go, where they're hit and where they die,
# and the stains stay (ChunkedWorld.set_tile): the island gets redder the
# more you fight on it. Ground only; walls, posts and the blood itself keep
# their look. Cloud stained again soaks through.
SOAKED_CLOUD = TileType(
    "soaked cloud", (";,", ",;", ":.", ".:", ";."), palette.SOAKED_CLOUD_FG, palette.SOAKED_CLOUD_BG,
)
STAINED_CLOUD = TileType(
    "stained cloud", (", ", " ,", ".,", ", "), palette.STAINED_CLOUD_FG, palette.STAINED_CLOUD_BG,
)
STAINED_ROAD = TileType(
    "stained marble", (",.", ".,", ", "), palette.STAINED_ROAD_FG, palette.STAINED_ROAD_BG,
)
STAINED_FLOOR = TileType(
    "stained marble", (", ", " ,", ",."), palette.STAINED_ROAD_FG, palette.STAINED_FLOOR_BG,
)
STAINED_STEP = TileType(
    "stained step", ("_,", ",_"), palette.STAINED_ROAD_FG, palette.STAINED_STEP_BG,
)
# The seven seals (M29.4): a great seal of red wax stamped in gold, in the
# middle of its clearing; broken, it lies cracked open.
SEVEN_SEAL = TileType(
    "seal", ("@@",), palette.GOLD, palette.SEAL_WAX,
)
SEVEN_SEAL_BROKEN = TileType(
    "broken seal", ("%,", ",%"), palette.SEAL_WAX_BROKEN, palette.BLOOD_TRICKLE_BG,
)
# Famine's weights (M29.5): they crush where they land and stay there,
# heavy black iron, until broken.
WEIGHT = TileType(
    "weight", ("[]",), palette.WEIGHT_FG, palette.WEIGHT_BG,
    solid=True, blocks_shots=True, hp=config.WALL_HP * 2, becomes=MARBLE_RUBBLE,
)
# What a stain turns each ground into (by tile name; anything else stays).
STAINS: dict[str, TileType] = {
    "cloud": STAINED_CLOUD, "cloud drift": STAINED_CLOUD, "petals": STAINED_CLOUD,
    "marble rubble": STAINED_CLOUD, "stained cloud": SOAKED_CLOUD,
    "marble road": STAINED_ROAD, "marble floor": STAINED_FLOOR, "marble step": STAINED_STEP,
}


# --- Pandemonium (M30.1, design/OCEAN.md 13) ------------------------------------------
# Black obsidian veined with gold: gold-leaf terraces stepping down into a
# pit, crimson velvet, braziers and lanterns, a beach of gold coins sliding
# into a wine-dark sea. Wine runs from the press down into a lake round the
# palace. (Ground stays dark so shots read on it; the gold is in the glyphs.)
OBSIDIAN = TileType(
    "obsidian", ("  ", "  ", "  ", ". ", " '", "  "), palette.OBSIDIAN_FG, palette.OBSIDIAN_BG,
)
OBSIDIAN_DEEP = TileType(
    # The pit's floor, round the lake: the same stone, darker down there.
    "deep obsidian", ("  ", "  ", ". ", "  ", " ."), palette.OBSIDIAN_DEEP_FG, palette.OBSIDIAN_DEEP_BG,
)
GOLD_VEIN = TileType(
    "gold vein", ("─ ", " ─", "─.", ".─", "──"), palette.GOLD_VEIN_FG, palette.OBSIDIAN_BG,
)
COINS = TileType(
    # Loose coins: round the heaps, and what a broken heap or statue leaves.
    "coins", ("o ", " o", ".o", "o.", " ."), palette.COIN_FG, palette.OBSIDIAN_BG,
)
COIN_HEAP = TileType(
    # A heap of gold: low cover, like the forest's logs.
    "coin heap", ("▄▄", "▄o", "o▄"), palette.COIN_FG, palette.COIN_HEAP_BG,
    solid=True, blocks_shots=True, hp=config.LOG_HP,
    wear=(("o.", ".o"),),
    becomes=COINS,
)
COIN_BEACH = TileType(
    "coin beach", (". ", " .", "o ", "  ", ".o", " o"), palette.COIN_BEACH_FG, palette.COIN_BEACH_BG,
)
FIRE_BRAZIER = TileType(
    # A burning brazier on a stand: it stops you, not shots.
    "brazier", ("()",), palette.PAND_BRAZIER_FG, palette.PAND_BRAZIER_BG,
    solid=True,
)
VELVET_BANNER = TileType(
    "crimson banner", ("|>",), palette.CRIMSON, palette.OBSIDIAN_BG,
    solid=True,
)
LANTERN = TileType(
    # The avenues' lanterns (Paradise's gold posts): they stop you, not shots.
    "lantern", ("i ", " i"), palette.LANTERN_FG, palette.OBSIDIAN_BG,
    solid=True,
)
GILT_ROAD = TileType(
    "gilded avenue", ("  ", ". ", " .", "_.", "  "), palette.GILT_ROAD_FG, palette.GILT_ROAD_BG,
)
GOLD_STAIRS = TileType(
    # Where an avenue goes down a terrace.
    "gold stairs", ("__",), palette.GILT_ROAD_FG, palette.TERRACE_BG,
)
GILT_BRIDGE = TileType(
    "gilded bridge", ("==",), palette.GILT_ROAD_FG, palette.WINE_BG,
)
TERRACE_EDGE = TileType(
    # A gold-leaf terrace's edge: the island steps down into the pit.
    "gold-leaf terrace", ("__", "_.", "._"), palette.TERRACE_FG, palette.TERRACE_BG,
)
WINE = TileType(
    # The river, the lake round the palace, a vat's insides. Watery: only
    # water walkers cross it (heroes out here always are).
    "wine", ("░ ", " ░", "  ", "▒░", "  "), palette.WINE_FG, palette.WINE_BG,
    solid=True,
)
WINE_FOUNTAIN = TileType(
    "wine fountain", ("▒▒", "░▒", "▒░"), palette.WINE_FOUNTAIN_FG, palette.WINE_FOUNTAIN_BG,
    solid=True,
)
WINE_SEA = TileType(
    # The sea round Pandemonium, wine-dark near the shore: watery.
    # (The ocean's own dither, wine-dark, so the sea seems to darken into wine.)
    "wine sea", ("░ ", " ░", "  ", "  ", "▒░"), palette.WINE_SEA_FG, palette.WINE_SEA_BG,
    solid=True,
)
PALACE_WALL = TileType(
    "palace wall", ("██", "▓█", "█▓"), palette.PALACE_WALL_FG, palette.PALACE_WALL_BG,
    solid=True, blocks_shots=True,
)
PALACE_GATE = TileType(
    # The great hall's gilded gate: sealed until the seventh bandstand falls
    # silent (M30.4). It stops you, not shots.
    "gilded gate", ("||",), palette.GOLD, palette.HALL_FLOOR_BG,
    solid=True,
)
HALL_FLOOR = TileType(
    # (polished black stone with a glint of gold here and there: calm, so
    # the fight on it reads)
    "hall floor", ("  ", "  ", ". ", " .", "  ", "' "), palette.HALL_FLOOR_FG, palette.HALL_FLOOR_BG,
)
HOST_SEAT = TileType(
    "host's seat", ("██", "▓▓"), palette.CRIMSON, palette.PALACE_WALL_BG,
    solid=True, blocks_shots=True,
)
FOUNTAIN_RIM = TileType(
    "fountain rim", ("▓▓", "██"), palette.GOLD, palette.COIN_HEAP_BG,
    solid=True,
)
GILT_FLOOR = TileType(
    "gilded floor", ("  ", ". ", " .", "  "), palette.GILT_FLOOR_FG, palette.GILT_FLOOR_BG,
)
CARPET = TileType(
    "crimson carpet", ("  ", ". ", " .", "  "), palette.CRIMSON, palette.PAND_VELVET_BG,
)
SPILLED_FEAST = TileType(
    # A banquet table knocked over: food and drink across the carpet.
    "spilled feast", (", ", ".%", "%.", " ,"), palette.SPILLED_FG, palette.PAND_VELVET_BG,
)
BANQUET_TABLE = TileType(
    # Heaped with food. It stops you, not shots; knock it over and the
    # feast spills.
    "banquet table", ("oo", "%o", "o%", "@o", "o@"), palette.TABLE_FG, palette.TABLE_BG,
    solid=True, hp=config.LOG_HP,
    wear=(("o.", ".o", "%."),),
    becomes=SPILLED_FEAST,
)
GILDED_STATUE = TileType(
    # A reveller cast in gold, admiring itself (some are revellers frozen
    # mid-pose, M30.3). Broken, it's loose coins.
    "gilded statue", ("▐▌",), palette.STATUE_GOLD, palette.GILT_FLOOR_BG,
    solid=True, blocks_shots=True, hp=config.WALL_HP,
    wear=(("▐▒", "▒▌"),),
    becomes=COINS,
)
BANDSTAND = TileType(
    "bandstand", ("__", "  ", "_ "), palette.STAGE_FG, palette.STAGE_BG,
)
INSTRUMENT = TileType(
    # The bandstands' drums and harps. Only the quest smashes them (M30.4:
    # stand on the stage), so they can't be shot or hacked away.
    "instrument", ("()", "[]", "|)"), palette.GOLD, palette.STAGE_BG,
    solid=True,
)
SMASHED_INSTRUMENT = TileType(
    # M30.4: a silenced bandstand's drums and harps, in pieces.
    "smashed instrument", ("/.", ".\\", "x,", ",x"), palette.SMASHED_FG, palette.STAGE_BG,
)
LANTERN_OUT = TileType(
    # M30.4: a silenced bandstand's lanterns, gone dark.
    "dark lantern", ("i ", " i"), palette.LANTERN_OUT_FG, palette.OBSIDIAN_BG,
    solid=True,
)
HOST_TABLE = TileType(
    # M30.4: the banquet room's long table down the middle of the palace hall
    # (the Host's dishes slide along it). It stops you, not shots, and it
    # doesn't break: the hall itself changes.
    "the host's table", ("oo", "%o", "o%", "@o", "o@", "&o"), palette.TABLE_FG, palette.TABLE_BG,
    solid=True,
)
DANCE_FLOOR = TileType(
    # M30.4: the ballroom's floor (its steps light up: ai/feast.py).
    "dance floor", ("  ", "  ", ". ", " ."), palette.DANCE_FLOOR_FG, palette.DANCE_FLOOR_BG,
)
MIRROR_PANEL = TileType(
    # M30.4: the ballroom's mirrors at the foot of the hall's wall. Floor,
    # not wall: the room changes under whoever stands there.
    "mirror panel", ("||", "|/", "/|"), palette.REVEL_MIRROR[1], palette.HALL_FLOOR_BG,
)
HALL_WINE = TileType(
    # M30.5: the hall fallen into the wine (the hunger, ai/hunger.py): shallow,
    # so you can wade it -- slowly. Walkable, unlike the lake round the palace.
    "spilt wine", ("░ ", " ░", "  ", "▒░", "  "), palette.WINE_FG, palette.WINE_BG,
)
TABLE_WRECK = TileType(
    # M30.5: an island of the collapsed banquet table, its planks in the wine.
    "broken table", ("==", "=-", "-=", "%=", "=%"), palette.TABLE_FG, palette.TABLE_BG,
)
PIER_DECK = TileType(
    # The gilded pier's planks, out over the wine-dark sea.
    "gilded pier", ("──", "─ ", " ─"), palette.PIER_FG, palette.PIER_BG,
)
BARGE = TileType(
    "barge", ("██", "▓█", "█▓"), palette.BARGE_FG, palette.BARGE_BG,
    solid=True, blocks_shots=True,
)
WELCOME_ARCH = TileType(
    "arch", ("██",), palette.GOLD, palette.GOLD_DARK,
    solid=True, blocks_shots=True,
)
HALL_MIRROR = TileType(
    "mirror", ("▐▌", "▌▐", "██"), palette.PAND_MIRROR_FG, palette.MIRROR_BG,
    solid=True, blocks_shots=True,
)
BALLROOM_FLOOR = TileType(
    "ballroom floor", ("  ", "░ ", "  ", " ░", "  "), palette.BALLROOM_FG, palette.BALLROOM_BG,
)
CHANDELIER = TileType(
    # Overhead: it lights the floor under it (walkable).
    "chandelier", ("**",), palette.PAND_CHANDELIER_FG, palette.BALLROOM_BG,
)
VINE_STAKES = TileType(
    "vine stakes", ("| ", " |", ". "), palette.STAKE_FG, palette.OBSIDIAN_BG,
)
VINES = TileType(
    # A row of grapevines on the press's terraced vineyards: low cover.
    "vines", ("%%", "%&", "&%"), palette.VINE_FG, palette.VINE_BG,
    solid=True, hp=config.TREE_HP,
    becomes=VINE_STAKES,
)
WINE_PRESS = TileType(
    "wine press", ("##", "▓▓"), palette.PRESS_FG, palette.PRESS_BG,
    solid=True, blocks_shots=True,
)
VAT = TileType(
    "vat", ("▓▓", "██"), palette.PRESS_FG, palette.PRESS_BG,
    solid=True,
)


# --- Pangaea (M31.1, design/OCEAN.md 24): deep time, jungle and fire ------------------
# Rings of ages: the great mammals' fern meadows on the shore ring, the
# dinosaurs' jungle in the middle, ash, horsetails and steaming pools at the
# heart under the volcano. Lava runs down from the cone (molten: nobody
# crosses; its crust burns), tar pits hold what steps in, amber holds what
# it caught long ago. A black-sand beach, steaming where the lava meets the
# sea. (Ground stays dark so shots read on it.)
FERN_MEADOW = TileType(
    "fern meadow", ("  ", ", ", " ,", "  ", "' ", " '"), palette.MEADOW_FG, palette.MEADOW_BG,
)
TALL_FERNS = TileType(
    # Walkable (the sabre-tooth stalks in them, M31.2): only a look.
    "tall ferns", ('"v', 'v"', '""', "v,"), palette.FERNS_FG, palette.MEADOW_BG,
)
JUNGLE_FLOOR = TileType(
    "jungle floor", ("  ", ". ", " ,", "  ", ", "), palette.JUNGLE_FG, palette.JUNGLE_BG,
)
TALL_JUNGLE_FERNS = TileType(
    "jungle ferns", ('"v', 'v"', '""', ",v"), palette.FERNS_FG, palette.JUNGLE_BG,
)
TRAMPLED_FERNS = TileType(
    # What a broken fern or cycad leaves.
    "trampled ferns", (",.", ".,", "_,", ",_"), palette.TRAMPLED_FG, palette.JUNGLE_BG,
)
GIANT_FERN = TileType(
    # The jungle's cover: it stops you and shots, and breaks.
    "giant fern", ("YY", "Yv", "vY"), palette.GIANT_FERN_FG, palette.GIANT_FERN_BG,
    solid=True, blocks_shots=True, hp=config.TREE_HP,
    wear=(("Y,", ",Y", "v."),),
    becomes=TRAMPLED_FERNS,
)
CYCAD = TileType(
    "cycad", ("T ", " T", "T,"), palette.CYCAD_FG, palette.JUNGLE_BG,
    solid=True, blocks_shots=True, hp=config.TREE_HP,
    wear=(("t,", ",t"),),
    becomes=TRAMPLED_FERNS,
)
JUNGLE_SPLINTERS = TileType(
    "splinters", ("_,", ",_", "._", "_."), palette.SPLINTER_FG, palette.JUNGLE_BG,
)
JUNGLE_TREE = TileType(
    "jungle tree", ("&&", "&%", "%&", "@&"), palette.JUNGLE_TREE_FG, palette.JUNGLE_TREE_BG,
    solid=True, blocks_shots=True, hp=config.TREE_HP,
    wear=(("&,", ",&", "%."),),
    becomes=JUNGLE_SPLINTERS,
)
ASH = TileType(
    # The heart's ground: the oldest age, under the volcano's fall of ash.
    "ash", ("  ", ". ", " .", "  ", "' ", "  "), palette.ASH_FG, palette.ASH_BG,
)
CINDERS = TileType(
    # The volcano's cone: ash and cinders, embers in it.
    "cinders", (". ", " :", ":.", "' ", " .", ".'"), palette.CINDER_FG, palette.CINDER_BG,
)
HORSETAILS = TileType(
    # Groves of giant horsetails round the pools: walkable, a look.
    "horsetails", ("||", "|:", ":|", "!|"), palette.HORSETAIL_FG, palette.ASH_BG,
)
ASH_DEBRIS = TileType(
    "ashy splinters", ("_.", "._", ",."), palette.SPLINTER_FG, palette.ASH_BG,
)
SCALE_TREE = TileType(
    # The first forests' trees, scaled like a lizard's skin.
    "scale tree", ("#|", "|#", "##"), palette.SCALE_TREE_FG, palette.SCALE_TREE_BG,
    solid=True, blocks_shots=True, hp=config.TREE_HP,
    wear=(("#.", ".#"),),
    becomes=ASH_DEBRIS,
)
HOT_SPRING = TileType(
    # The heart's steaming pools (the sea scorpion's, M31.3). Watery: only
    # water walkers cross them (heroes out here always are).
    "hot spring", ("░ ", " ░", "▒░", "░▒", "  "), palette.SPRING_FG, palette.SPRING_BG,
    solid=True,
)
BASALT = TileType(
    # Cooled lava: where a river ends, its crossings, the caldera's islands.
    "basalt", ("  ", ". ", " _", "_ ", "  "), palette.BASALT_FG, palette.BASALT_BG,
)
BASALT_BOULDER = TileType(
    "basalt boulder", ("▓▓", "▓▒", "▒▓"), palette.BOULDER_FG, palette.BOULDER_BG,
    solid=True, blocks_shots=True,
)
LAVA = TileType(
    # Molten: nobody walks it, water walkers neither (it isn't watery); shots
    # fly over it.
    "lava", ("▒▓", "▓▒", "░▓", "▓░", "▒▒"), palette.LAVA_FG, palette.LAVA_BG,
    solid=True,
)
LAVA_CRUST = TileType(
    # A lava river's edge: you can walk it, and it burns (systems/pangaea.py).
    "lava crust", (".:", ":.", "*.", ".*", ": "), palette.CRUST_FG, palette.CRUST_BG,
)
LAVA_CROSSING = TileType(
    # Where a trail crosses the lava: a causeway of cooled rock.
    "cooled crossing", ("==", "=_", "_="), palette.CROSSING_FG, palette.BASALT_BG,
)
TAR = TileType(
    # A tar pit: it slows you badly and holds you (systems/pangaea.py).
    "tar", ("  ", "o ", " .", "  ", ". ", " o"), palette.TAR_FG, palette.TAR_BG,
)
GAME_TRAIL = TileType(
    # Beaten earth: the beasts' trails (Paradise's roads, Pandemonium's avenues).
    "game trail", ("  ", ". ", " .", ",.", "  "), palette.TRAIL_FG, palette.TRAIL_BG,
)
BLACK_SAND = TileType(
    "black sand", (". ", " .", "  ", ".'", " :"), palette.BLACK_SAND_FG, palette.BLACK_SAND_BG,
)
STEAMING_SEA = TileType(
    # The sea where a lava river runs into it: watery, steaming.
    "steaming sea", ("░ ", " ░", "▒░", "░▒", "  "), palette.STEAM_FG, palette.STEAM_BG,
    solid=True,
)
GIANT_BONE = TileType(
    # A giant beast's ribs, skull or tusks: cover that never breaks.
    "giant bone", ("()", "((", "))", "=="), palette.GIANT_BONE_FG, palette.GIANT_BONE_BG,
    solid=True, blocks_shots=True,
)
SPINE = TileType(
    # The sea-beast's spine, overhead: you walk under it through its ribs.
    "spine", ("o=", "=o", "oo"), palette.GIANT_BONE_FG, palette.SPINE_BG,
)
TWIGS = TileType(
    "twigs", (",'", "',", "/,", ",\\"), palette.TWIG_FG, palette.JUNGLE_BG,
)
NEST = TileType(
    # A nest's ring of branches and bones: low cover (it stops you, not shots).
    "nest", ("##", "#/", "\\#", "#x"), palette.NEST_FG, palette.NEST_BG,
    solid=True, hp=config.LOG_HP,
    becomes=TWIGS,
)
EGGSHELL = TileType(
    "eggshell", ("c ", " c", ".c", "c."), palette.EGG_FG, palette.NEST_BG,
)
EGG = TileType(
    # Break the eggs and the parent comes (M31.3).
    "egg", ("()", "0 ", " 0"), palette.EGG_FG, palette.NEST_BG,
    solid=True, hp=config.STUMP_HP,
    becomes=EGGSHELL,
)
GIANT_EGG = TileType(
    # The great nest's eggs, the size of a man.
    "giant egg", ("██", "▓█", "█▓"), palette.EGG_FG, palette.EGG_SHADE,
    solid=True, blocks_shots=True, hp=config.WALL_HP,
    wear=(("▓▒", "▒▓"),),
    becomes=EGGSHELL,
)
AMBER_SHARDS = TileType(
    "amber shards", ("'.", ".'", ",'", "' "), palette.AMBER_FG, palette.ASH_BG,
)
AMBER = TileType(
    # Golden amber with things frozen inside (M31.3: breaking it frees what's
    # in it). It stops you and shots.
    "amber", ("▓▓", "▒▓", "▓%", "%▓", "▓▒"), palette.AMBER_FG, palette.AMBER_BG,
    solid=True, blocks_shots=True, hp=config.WALL_HP,
    wear=(("▒░", "░▒"),),
    becomes=AMBER_SHARDS,
)
CAVE_ROCK = TileType(
    "cave rock", ("▓▓", "▓▒", "▒▓", "██"), palette.CAVE_ROCK_FG, palette.CAVE_ROCK_BG,
    solid=True, blocks_shots=True,
)
PAINTED_WALL = TileType(
    # The painted caves' walls: hunts of the island's beasts in ochre.
    "painted wall", ("mm", "m>", "<m", "/\\", "h ", " h", ">>"), palette.PAINT_FG, palette.CAVE_WALL_BG,
    solid=True, blocks_shots=True,
)
CAVE_FLOOR = TileType(
    "cave floor", ("  ", ". ", " .", "  "), palette.CAVE_FLOOR_FG, palette.CAVE_FLOOR_BG,
)
FIRE_PIT = TileType(
    # The hunters' fire: it stops you, not shots.
    "fire pit", ("()", "**", "^^"), palette.FIRE_PIT_FG, palette.FIRE_PIT_BG,
    solid=True,
)
CRAG = TileType(
    # The great nest's crag: sheer rock.
    "crag", ("██", "▓█", "█▓", "▓▓"), palette.CRAG_FG, palette.CRAG_BG,
    solid=True, blocks_shots=True,
)
CRAG_TOP = TileType(
    "crag top", ("  ", ". ", " .", "  "), palette.CRAG_TOP_FG, palette.CRAG_TOP_BG,
)
CRATER_RIM = TileType(
    # The impact crater's ejecta: broken rock thrown up round it.
    "crater rim", ("::", ".:", ":.", ". "), palette.CRATER_FG, palette.CRATER_BG,
)
IMPACT_GLASS = TileType(
    # The crater's floor, melted to glass by the star's fall.
    "impact glass", ("  ", "/ ", " \\", "- ", "  "), palette.GLASS_FG, palette.GLASS_BG,
)
STAR_STONE = TileType(
    # The strange black stone: the star that will end the age of giants.
    "black stone", ("██", "▓█", "█▓"), palette.STAR_STONE_FG, palette.STAR_STONE_BG,
    solid=True, blocks_shots=True,
)
CALDERA_FLOOR = TileType(
    # Cooling black rock, red glowing in its cracks: the Ancestor's floor
    # (calm, so the fight on it reads).
    "caldera floor", ("  ", "  ", ". ", " '", "  ", "_ "), palette.CALDERA_FG, palette.CALDERA_BG,
)
CALDERA_RIM = TileType(
    "caldera rim", ("██", "▓█", "█▓"), palette.RIM_FG, palette.RIM_BG,
    solid=True, blocks_shots=True,
)
FIRE_CURTAIN = TileType(
    # The caldera's gate: a curtain of fire, sealed until the seventh great
    # beast falls (M31.4). It stops you, not shots.
    "curtain of fire", ("^^", "*^", "^*"), palette.CURTAIN_FG, palette.CURTAIN_BG,
    solid=True,
)
# M31.2: what the hunters leave on Pangaea (systems/pangaea.py). Ferns on
# fire (walkable: it burns), what they leave for good, and a spear stuck in
# the ground for a few seconds (it stops you, not shots).
BURNING_FERNS = TileType(
    "burning ferns", ("^^", "*^", "^*", "^'"), palette.BURNING_FG, palette.BURNING_BG,
)
SCORCHED = TileType(
    "scorched ground", ("  ", ". ", " ,", "' ", "  "), palette.SCORCHED_FG, palette.SCORCHED_BG,
)
STUCK_SPEAR = TileType(
    "stuck spear", ("/ ", " /", "\\ ", " \\"), palette.STUCK_SPEAR_FG, palette.SCORCHED_BG,
    solid=True,
)

# M31.4: the great hunt painted on the deepest wall of the painted caves (a
# kill each, in fresh white and red), and the end of the age painted there
# already (the falling star). The husk the Ancestor leaves when it moults:
# cover for a while (it crumbles: ai/ancestor.py puts the old tiles back).
HUNT_MURAL = TileType(
    "fresh painting", ("M>", "<M", "m>", "<m", "/\\"), palette.HUNT_MURAL_FG, palette.CAVE_WALL_BG,
    solid=True, blocks_shots=True,
)
STAR_MURAL = TileType(
    "star painting", ("*.", ".*", "*'", "'*"), palette.STAR_MURAL_FG, palette.CAVE_WALL_BG,
    solid=True, blocks_shots=True,
)
HUSK = TileType(
    "husk", ("()", "%%", "))", "((", "%("), palette.HUSK_FG, palette.HUSK_BG,
    solid=True, blocks_shots=True,
)

# M33.1: what the Fossil Angel leaves (ai/fossil_angel.py, design/FINALS.md
# 9.1). A stone feather stuck in the ground: cover (it breaks; it smashes
# through them). Resin running out of it: you can walk it, but it holds you
# (the angel's step). Amber walls where the resin hardened: they stop you
# and shots, and break (nothing frozen in these: not REPORT_BREAKS).
FEATHER_SPIKE = TileType(
    "stone feather", ("/|", "|\\", "/'", "'|"), palette.FEATHER_SPIKE_FG, palette.FEATHER_SPIKE_BG,
    solid=True, blocks_shots=True, hp=config.WALL_HP,
    wear=(("/.", ".|"),),
    becomes=MARBLE_RUBBLE,
)
RESIN = TileType(
    "resin", ("=-", "-=", "--", "= "), palette.RESIN_FG, palette.RESIN_BG,
)
AMBER_WALL = TileType(
    "amber wall", ("▓▓", "▒▓", "▓▒"), palette.AMBER_WALL_FG, palette.AMBER_WALL_BG,
    solid=True, blocks_shots=True, hp=config.WALL_HP,
    wear=(("▒░", "░▒"),),
    becomes=AMBER_SHARDS,
)

# M33.2: the first angel's red amber (ai/first_angel.py, design/FINALS.md
# 9.2): its blood pooling (the blood rain's; you walk it, but it slows you
# and, from the third phase, holds you: the angel's step) and walls of it
# rising across your path (they stop you and shots, and break; cover from
# the first word).
RED_RESIN = TileType(
    "red resin", ("-=", "=-", "░-", "-░"), palette.RED_RESIN_FG, palette.RED_RESIN_BG,
)
RED_AMBER = TileType(
    "red amber", ("▓▓", "▒▓", "▓▒"), palette.RED_AMBER_FG, palette.RED_AMBER_BG,
    solid=True, blocks_shots=True, hp=config.WALL_HP,
    wear=(("▒░", "░▒"),),
    becomes=BLOOD_TRICKLE,
)

# M31.5: the first sea flooding the caldera (ai/first_life.py): shallows at
# low tide (you walk them), the deep at high tide (you wade it slowly: it
# swims), the rocks that stand above it (the lava lakes quenched among them).
TIDE_SHALLOWS = TileType(
    "shallows", ("  ", "  ", "_ ", " _", "  ", ", "), palette.TIDE_SHALLOW_FG, palette.TIDE_SHALLOW_BG,
)
TIDE_SEA = TileType(
    "first sea", ("░ ", " ░", "  ", "▒░", "  "), palette.TIDE_SEA_FG, palette.TIDE_SEA_BG,
)
TIDE_ROCK = TileType(
    "rock in the tide", ("  ", "_ ", " _", "  ", "=_"), palette.TIDE_ROCK_FG, palette.TIDE_ROCK_BG,
)

# --- Panopticon (M32.1, design/OCEAN.md 35): the machine city, chrome and neon ----------
# Black steel streets with glowing cyan lines between tall blocks that break
# line of sight (each district's its own: the docks' warehouses, the
# factory's sheds, the homes' flats, the scrapyard's heaps), magenta neon
# signs; district walls with gates; the watchtower and its hall of cells at
# the centre. The land's dangers (systems/panopticon.py): laser fences
# (their posts and tracks: the beam is drawn when it's on), conveyors and
# presses, live power (pylons, cables and puddles: dead once their pylon
# breaks). A steel quay all round, oily black water over drowned plating.
# (Ground stays dark so shots read on it.)
STREET = TileType(
    "street", ("  ", "  ", "  ", ". ", " .", "  "), palette.STREET_FG, palette.STREET_BG,
)
LANE_LINE = TileType(
    # A street's glowing middle line.
    "lane line", ("--", "- ", " -"), palette.LANE_LINE_FG, palette.STREET_BG,
)
PAVEMENT = TileType(
    "pavement", ("  ", "_ ", " _", "  "), palette.PAVEMENT_FG, palette.PAVEMENT_BG,
)
PLAZA = TileType(
    # The tower's plaza, the gates', the landmarks' forecourts.
    "plaza", ("  ", ". ", " .", "  ", "' "), palette.PLAZA_FG, palette.PLAZA_BG,
)
LOT = TileType(
    # An empty block: open ground among the buildings.
    "empty lot", ("  ", ". ", ",.", " '", "_ "), palette.LOT_FG, palette.LOT_BG,
)
QUAY = TileType(
    "quay", ("  ", ": ", " :", "_ ", "  "), palette.QUAY_FG, palette.QUAY_BG,
)
OILY_SEA = TileType(
    # Oily black water over drowned steel plating: watery (water walkers
    # cross it).
    "oily sea", ("  ", "░ ", " ░", "= ", "  "), palette.OILY_FG, palette.OILY_BG,
    solid=True,
)
WAREHOUSE_WALL = TileType(
    # The docks' blocks: warehouses.
    "warehouse wall", ("[]", "[]", "||", "]["), palette.WAREHOUSE_FG, palette.WAREHOUSE_BG,
    solid=True, blocks_shots=True,
)
WAREHOUSE_ROOF = TileType(
    "warehouse roof", ("▓▓", "▓▒", "▒▓"), palette.WAREHOUSE_ROOF_FG, palette.WAREHOUSE_ROOF_BG,
    solid=True, blocks_shots=True,
)
SHED_WALL = TileType(
    # The factory's blocks (and the factory's own walls): sheds.
    "factory shed", ("##", "#|", "|#"), palette.SHED_FG, palette.SHED_BG,
    solid=True, blocks_shots=True,
)
SHED_ROOF = TileType(
    "shed roof", ("▒▒", "▒░", "░▒", "o▒"), palette.SHED_ROOF_FG, palette.SHED_ROOF_BG,
    solid=True, blocks_shots=True,
)
FLAT_WALL = TileType(
    # The homes' blocks: flats, their windows lit for nobody.
    "apartment block", ("::", ": ", " :", "''"), palette.FLAT_FG, palette.FLAT_BG,
    solid=True, blocks_shots=True,
)
FLAT_ROOF = TileType(
    "rooftop", ("▓▓", "▓▒", "▒▓", "▓▓"), palette.FLAT_ROOF_FG, palette.FLAT_ROOF_BG,
    solid=True, blocks_shots=True,
)
NEON_SIGN = TileType(
    "neon sign", ("[]", "==", "##"), palette.NEON_FG, palette.NEON_BG,
    solid=True, blocks_shots=True,
)
SCRAP_BITS = TileType(
    "scrap bits", (",.", ".,", "_,", ",_"), palette.SCRAP_BITS_FG, palette.LOT_BG,
)
SCRAP_HEAP = TileType(
    # The scrapyard's blocks: mountains of broken machines.
    "scrap heap", ("%#", "#%", "&%", "%&"), palette.HEAP_FG, palette.HEAP_BG,
    solid=True, blocks_shots=True,
)
LOOSE_SCRAP = TileType(
    "loose scrap", ("%,", ",%", "&."), palette.LOOSE_SCRAP_FG, palette.LOOSE_SCRAP_BG,
    solid=True, blocks_shots=True, hp=config.WALL_HP,
    wear=((",.", ".,"),),
    becomes=SCRAP_BITS,
)
CITY_WALL = TileType(
    # The district walls (their gates are gaps).
    "district wall", ("██", "▓█", "█▓"), palette.CITY_WALL_FG, palette.CITY_WALL_BG,
    solid=True, blocks_shots=True,
)
LASER_POST = TileType(
    # A laser fence's post: it stops you, not shots.
    "laser post", ("[]", "|]", "[|"), palette.LASER_POST_FG, palette.LASER_POST_BG,
    solid=True,
)
LASER_TRACK = TileType(
    # Where a fence's beam runs (drawn over it while it's on).
    "laser track", (". ", " .", ".."), palette.LASER_TRACK_FG, palette.STREET_BG,
)
BELT_E = TileType("conveyor belt", (">>", "> ", " >"), palette.BELT_FG, palette.BELT_BG)
BELT_W = TileType("conveyor belt", ("<<", "< ", " <"), palette.BELT_FG, palette.BELT_BG)
BELT_N = TileType("conveyor belt", ("^^", "^ ", " ^"), palette.BELT_FG, palette.BELT_BG)
BELT_S = TileType("conveyor belt", ("vv", "v ", " v"), palette.BELT_FG, palette.BELT_BG)
BELTS = {BELT_E: (1, 0), BELT_W: (-1, 0), BELT_N: (0, -1), BELT_S: (0, 1)}
PRESS_BED = TileType(
    # Where a press slams down (its shadow shows first).
    "press bed", ("==", "=_", "_="), palette.PRESS_BED_FG, palette.PRESS_BED_BG,
)
PRESS_FRAME = TileType(
    "press frame", ("||", "]["), palette.PRESS_FRAME_FG, palette.PRESS_FRAME_BG,
    solid=True, blocks_shots=True,
)
PYLON_STUMP = TileType(
    "broken pylon", ("._", "_.", ".."), palette.STUMP_PYLON_FG, palette.STREET_BG,
)
PYLON = TileType(
    # Break it and its lines go dead (systems/panopticon.py).
    "pylon", ("/\\", "|\\", "/|"), palette.PYLON_FG, palette.PYLON_BG,
    solid=True, blocks_shots=True, hp=config.WALL_HP,
    wear=(("/.", ".\\"),),
    becomes=PYLON_STUMP,
)
CABLE = TileType(
    # A live cable on the ground: it shocks.
    "live cable", ("=-", "-=", ":="), palette.CABLE_FG, palette.STREET_BG,
)
DEAD_CABLE = TileType(
    "dead cable", ("=-", "-=", ":="), palette.DEAD_CABLE_FG, palette.STREET_BG,
)
PUDDLE = TileType(
    # An electrified puddle by a live cable.
    "live puddle", ("░░", "▒░", "░▒"), palette.PUDDLE_FG, palette.PUDDLE_BG,
)
DEAD_PUDDLE = TileType(
    "puddle", ("░░", "▒░", "░▒"), palette.DEAD_PUDDLE_FG, palette.DEAD_PUDDLE_BG,
)
TOWER_WALL = TileType(
    "tower wall", ("██", "▓█", "█▓"), palette.TOWER_FG, palette.TOWER_BG,
    solid=True, blocks_shots=True,
)
CELL_DOOR = TileType(
    # The hall of cells' walls: tiers of cell doors and screens.
    "cell door", ("||", "|#", "#|"), palette.CELL_DOOR_FG, palette.CELL_DOOR_BG,
    solid=True, blocks_shots=True,
)
CELL_SCREEN = TileType(
    "screen", ("[]", "[=", "=]"), palette.SCREEN_FG, palette.SCREEN_BG,
    solid=True, blocks_shots=True,
)
CELL_FLOOR = TileType(
    # The hall's floor (calm, so the fight on it reads).
    "hall of cells floor", ("  ", "  ", ". ", " '", "  "), palette.CELL_FLOOR_FG, palette.CELL_FLOOR_BG,
)
HALL_PILLAR = TileType(
    "pillar", ("██", "▓▓"), palette.HALL_PILLAR_FG, palette.HALL_PILLAR_BG,
    solid=True, blocks_shots=True,
)
BLAST_DOOR = TileType(
    # The hall's gate, sealed until the seventh eye goes dark (M32.4).
    "blast door", ("##", "=#", "#="), palette.BLAST_DOOR_FG, palette.BLAST_DOOR_BG,
    solid=True, blocks_shots=True,
)
SEA_WALL = TileType(
    "sea wall", ("██", "▓█", "█▓"), palette.SEA_WALL_FG, palette.SEA_WALL_BG,
    solid=True, blocks_shots=True,
)
LOCK_FLOOR = TileType(
    # The sea wall's lock gate, open: where you walk in.
    "lock", ("==", "=_", "_="), palette.LOCK_FG, palette.LOCK_BG,
)
VOICE_SCREEN = TileType(
    # A cracked screen in the lock house: the voice in the screens (M32.4).
    "cracked screen", ("[/", "/]", "[\\"), palette.VOICE_FG, palette.VOICE_BG,
    solid=True, blocks_shots=True,
)
FACTORY_FLOOR = TileType(
    "factory floor", ("  ", ". ", " .", "_ ", "  "), palette.FACTORY_FLOOR_FG, palette.FACTORY_FLOOR_BG,
)
ROBOT_ARM = TileType(
    # An assembly arm by a belt: it stops you, not shots.
    "robot arm", ("Y-", "-Y", "Y|"), palette.ROBOT_ARM_FG, palette.FACTORY_FLOOR_BG,
    solid=True,
)
CHASSIS = TileType(
    # A half-built robot on the line (some start moving, M32.2-3).
    "half-built robot", ("[]", "[o", "o]"), palette.CHASSIS_FG, palette.CHASSIS_BG,
    solid=True, blocks_shots=True,
)
CHAIN_FENCE = TileType(
    # The scrapyard's fence: it stops you, not shots.
    "chain fence", ("xx", "XX", "xX"), palette.CHAIN_FENCE_FG, palette.YARD_BG,
    solid=True,
)
YARD_DIRT = TileType(
    "oily dirt", (". ", " ,", "  ", ",.", "  "), palette.YARD_FG, palette.YARD_BG,
)
BROKEN_CRATE = TileType(
    # M32.2: a hauler's thrown crate, burst where it landed: cover (it breaks).
    "broken crate", ("#]", "[#", "%]"), palette.CRATE_FG, palette.CRATE_BG,
    solid=True, blocks_shots=True, hp=config.WALL_HP // 2,
    wear=((",#", "#,"),),
    becomes=SCRAP_BITS,
)
CUT_WIRE = TileType(
    # M32.3: thorned wire cut through.
    "cut wire", ("x.", ".x", "  "), palette.THORN_WIRE_FG, palette.LAWN_BG,
)
THORN_WIRE = TileType(
    # M32.3: a gardener's hedge of thorned wire grown round you: it stops you,
    # not shots, until you cut through (it withers in a while).
    "thorned wire", ("XX", "xX", "Xx"), palette.THORN_WIRE_FG, palette.THORN_WIRE_BG,
    solid=True, hp=30, becomes=CUT_WIRE,
)
BROKEN_PEN = TileType(
    "broken bars", ("/.", ".\\", "  "), palette.PEN_FG, palette.HOME_FLOOR_BG,
)
PLAYPEN = TileType(
    # M32.3: a nanny's playpen round you (TIME OUT): break a bar to get out.
    "playpen", ("||", "|#", "#|"), palette.PEN_FG, palette.PEN_BG,
    solid=True, hp=40, becomes=BROKEN_PEN,
)
WRECK = TileType(
    # A dead machine (some aren't quite dead, M32.3): cover.
    "wreck", ("[%", "%]", "&]"), palette.WRECK_FG, palette.WRECK_BG,
    solid=True, blocks_shots=True,
)
A_MESS = TileType(
    # What a broken thing in the kept homes leaves (the housekeepers mind, M32.3).
    "a mess", (",'", "'.", ".,"), palette.MESS_FG, palette.HOME_FLOOR_BG,
)
HOME_WALL = TileType(
    "home wall", ("▓▓", "▓█", "█▓"), palette.HOME_WALL_FG, palette.HOME_WALL_BG,
    solid=True, blocks_shots=True,
)
HOME_FLOOR = TileType(
    "clean floor", ("  ", "  ", ". ", "  "), palette.HOME_FLOOR_FG, palette.HOME_FLOOR_BG,
)
SET_TABLE = TileType(
    # A table set for dinner: it stops you, not shots, and breaks.
    "set table", ("o=", "=o", "=="), palette.SET_TABLE_FG, palette.SET_TABLE_BG,
    solid=True, hp=config.STUMP_HP,
    becomes=A_MESS,
)
MADE_BED = TileType(
    "made bed", ("[=", "=]", "=="), palette.BED_FG, palette.BED_BG,
    solid=True, hp=config.STUMP_HP,
    becomes=A_MESS,
)
LAWN = TileType(
    "lawn", ('" ', ' "', "  ", "''"), palette.LAWN_FG, palette.LAWN_BG,
)
HEDGE = TileType(
    # A trimmed hedge in front of a home: it stops you, not shots.
    "trimmed hedge", ("mm", "MM", "mM"), palette.HEDGE_FG, palette.HEDGE_BG,
    solid=True, hp=config.TREE_HP,
    becomes=LAWN,
)
MAST_BASE = TileType(
    # A great camera mast's foot (blinded in M32.4's quest).
    "camera mast", ("[]", "##", "[#"), palette.MAST_FG, palette.MAST_BG,
    solid=True, blocks_shots=True,
)
MAST_STUMP = TileType(
    # M32.4: a blinded mast's foot, the mast torn down.
    "fallen mast", ("%#", "#%", "%."), palette.MAST_STUMP_FG, palette.MAST_BG,
    solid=True, blocks_shots=True,
)
HALL_PYLON = TileType(
    # M32.4: a live pylon at the hall of cells' edge (the eye's arcs leap to it).
    "hall pylon", ("/\\", "|\\", "/|"), palette.PYLON_FG, palette.CELL_FLOOR_BG,
    solid=True, blocks_shots=True,
)
CELL_BARS = TileType(
    # M32.4: laser bars round you: the eye has locked you in a cell.
    "laser bars", ("||", "|!", "!|"), palette.CELL_BARS_FG, palette.CELL_FLOOR_BG,
    solid=True,
)
MAST_PAD = TileType(
    "mast pad", ("  ", ". ", "_ ", "  "), palette.MAST_PAD_FG, palette.MAST_PAD_BG,
)
# M32.5: the hall's walls come down (the walking city tears itself free).
BROKEN_FLOOR = TileType(
    # Where the walls stood (and the plaza they fell on).
    "torn floor", ("  ", ". ", ".,", " ;", "  ", ":."), palette.BROKEN_FLOOR_FG, palette.BROKEN_FLOOR_BG,
)
BROKEN_CELL = TileType(
    # Broken cells from the torn walls: cover (it breaks).
    "broken cells", ("|%", "%|", "#/"), palette.BROKEN_CELL_FG, palette.BROKEN_CELL_BG,
    solid=True, blocks_shots=True, hp=config.WALL_HP,
    wear=((".%", "%."),),
    becomes=BROKEN_FLOOR,
)
BROKEN_PILLAR = TileType(
    # A piece the walking city threw, broken where it landed: cover.
    "broken pillar", ("▓%", "%▓", "▓▓"), palette.HALL_PILLAR_FG, palette.BROKEN_CELL_BG,
    solid=True, blocks_shots=True, hp=config.WALL_HP,
    wear=(("%.", ".%"),),
    becomes=BROKEN_FLOOR,
)
RUBBLE_HEAP = TileType(
    # The rim of rubble the walls fell into.
    "rubble heap", ("▓▒", "▒▓", "▓▓", "▒░"), palette.RUBBLE_HEAP_FG, palette.RUBBLE_HEAP_BG,
    solid=True, blocks_shots=True,
)
BREACH = TileType(
    # A breach in the rubble: the watch pours in from the streets there.
    "breach", ("/\\", "\\/", "^."), palette.BREACH_FG, palette.RUBBLE_HEAP_BG,
    solid=True, blocks_shots=True,
)
DEAD_JUNCTION = TileType(
    "cut junction", ("[x", "x]", "[."), palette.DEAD_JUNCTION_FG, palette.BROKEN_FLOOR_BG,
    solid=True, blocks_shots=True,
)
JUNCTION = TileType(
    # One of the grid's junctions in the broken walls: the walking city plugs
    # into them. Shoot it and its cables go dead.
    "junction", ("[#", "#]", "[="), palette.JUNCTION_FG, palette.JUNCTION_BG,
    solid=True, blocks_shots=True, hp=config.JUNCTION_HP,
    wear=(("[x", "x]"),),
    becomes=DEAD_JUNCTION,
)

# M31.3: the tiles whose breaking the world reports (world.broke, taken by
# systems/pangaea.step): an egg hatches, amber frees what's in it. M32.1: a
# pylon's lines go dead (systems/panopticon.step takes those).
REPORT_BREAKS = frozenset((EGG, GIANT_EGG, AMBER, PYLON,
                           SET_TABLE, MADE_BED, HEDGE))     # (M32.3: a mess in the kept homes)
