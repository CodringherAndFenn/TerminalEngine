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
