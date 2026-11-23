"""
render/gear_looks.py -- worn gear on the hero sprites (M28.6, design/GEAR.md
sec 22).

The heroes are 14 x 18 letter sprites (render/characters.ART). Three worn
slots change them:

  * HEAD: the piece's shape, taken from its name (hood, helm, crown, mask;
    the boss relics have their own: the Black Ice Crown, the Fly Agaric
    Cap, the Lawyer's Wig, the Lich's Gaze), drawn for every hero in
    HEADGEAR, tinted by the piece's element (HEAD_LOOKS). A hood, helm,
    crown or wig replaces the hero's own headgear; a mask sits on the face
    and keeps it.
  * CHEST: the body's two colours (the robe, tunic, gown, doublet, the
    dwarf's sleeves) take the piece's colours (CHEST_LOOKS); the shape
    stays.
  * MAIN HAND: the weapon's accent (the staff's orb, the axe head, the
    bow, the wand's star, the lute's body) takes the piece's colour
    (MAIN_LOOKS). The dwarf's thrown axes carry it too (render/ascii_fx).

A worn legendary head, chest or main-hand piece also blinks a glint on the
hero (SPARKLE, drawn by render/characters.draw_sparkles).

Drawing language (HEADGEAR rows, 14 characters each, from row `top`):
  " "  keep the hero's own pixel     "."  clear it
  "1"  the tint's light colour       "2"  its dark colour
  "3"  the accent (a gem, a brow ember, glowing eyes, a shine)
  "4"  a detail (hood: leeches, else like "1"; helm: a crest, else
       nothing; cap: the spots)
  "5"  a beak (masks: the Plaguebeak's; else kept)
  any other letter: that sprite colour (palette.SPRITE_COLORS).
Pixels of the weapon (WEAPON's box, where the hero has a pixel) are never
drawn over: the weapon is held in front.

Everything here is art: it feeds the art handoff (M36).
"""

from __future__ import annotations

from dataclasses import dataclass

from .. import palette

# --- The pieces' looks ------------------------------------------------------------------
# Head: key -> (shape, light, dark, accent[, detail[, beak]]).
HEAD_LOOKS: dict[str, tuple] = {
    "kindling": ("hood", "f", "F", "r"),              # Cinderveil Hood: an ember at the brow
    "wildfire": ("crown", "f", "F", "r"),             # Blazecrown
    "venom": ("mask", "g", "G", "y"),                 # Viper Mask
    "virulence": ("mask", "u", "U", "k", "u", "d"),   # Plaguebeak: dark goggles, a bone beak
    "frostbite": ("hood", "o", "O", "w"),             # Rime Hood
    "shatter": ("helm", "i", "I", "w"),               # Glassfrost Helm
    "static": ("helm", "y", "Y", "w", "f"),           # Stormvane Helm: a vane on top
    "serrated": ("helm", "M", "c", "m", "m"),         # Thornhelm: a spike on top
    "hemorrhage": ("hood", "r", "R", "R"),            # Bloodtrail Cowl
    "thermal_shock": ("crown", "w", "m", "o"),        # Steamcrown
    "toxic_current": ("mask", "q", "Q", "y"),         # Galvanic Mask
    # The boss relics (M28.5).
    "latch_hood": ("hood", "n", "N", "r", "C"),       # Latch Hood: leeches on it
    "black_ice_crown": ("icecrown", "c", "C", "o"),   # Black Ice Crown: ice spikes
    "fly_agaric_cap": ("cap", "r", "R", "w", "w"),    # Fly Agaric Cap: white spots
    "lawyers_wig": ("wig", "w", "m", "d"),            # Lawyer's Wig: white curls
    "lichs_gaze": ("lich", "c", "C", "o"),            # Lich's Gaze: a dark cowl, glowing eyes
    "crown_of_conquest": ("crown", "y", "Y", "r"),    # Crown of Conquest: gold, a red stone
}

# Chest: key -> (light, dark), the body's colours.
CHEST_LOOKS: dict[str, tuple[str, str]] = {
    "thorn_mail": ("u", "U"),        # Brambleguard: bramble olive
    "ward_charm": ("j", "J"),        # Wardweave Robe: ward blue
    "heavy_plate": ("m", "M"),       # Anvil Plate: steel
    "glass_cannon": ("i", "I"),      # Shattercoat: glass
    "retaliation": ("R", "C"),       # Grudge Mail: dark red
    "untouched": ("w", "m"),         # Spotless Tunic: white
    "berserker": ("n", "N"),         # Wolfpelt: fur
    "bulwark": ("M", "C"),           # Bastion Plate: dark iron
    "juggernaut": ("e", "E"),        # Mountainhide: hide
    "aegis": ("y", "Y"),             # Sunward Aegis: gold
    "phoenix": ("f", "F"),           # Phoenix Mantle: flame
    "bubble_belt": ("o", "O"),       # (froggy) bubbles
    "leechskin": ("N", "C"),         # (leech swarm) slick dark brown
    "engorged_mantle": ("p", "R"),   # (Proboscia) blood-swollen
    "scarab_carapace": ("q", "Q"),   # (Khepri) shell sheen
    "lead_apron": ("x", "X"),        # (the Fallout King) lead
    "hermits_furs": ("d", "D"),      # (the Frost Hermit) grey furs
    "pale_riders_cloak": ("i", "I"), # (the Four Horsemen) pale
    "gluttons_bib": ("w", "R"),      # (the Host of the Feast) a white bib, wine-stained
}

# Main hand: key -> (light, dark), the weapon's accent.
MAIN_LOOKS: dict[str, tuple[str, str]] = {
    # The wizard's staffs: the orb.
    "storm_caller": ("y", "Y"), "conductor": ("a", "A"), "supercell": ("j", "J"),
    "phase_darts": ("i", "I"), "ball_lightning": ("w", "y"), "seeker": ("g", "G"),
    "resonance": ("q", "Q"), "implosion": ("v", "V"), "arcane_storm": ("p", "P"),
    "orbiting_darts": ("H", "Y"),
    # The dwarf's axes: the head.
    "ricochet": ("j", "J"), "hang_time": ("i", "I"), "homeward_fury": ("r", "R"),
    "tether": ("M", "c"), "cyclone": ("q", "Q"), "splitting_axe": ("y", "Y"),
    # The huntress's bows: the wood.
    "arrow_rain": ("j", "J"), "broadhead": ("g", "G"), "hunters_mark": ("r", "R"),
    "steady_aim": ("o", "O"), "deadeye": ("y", "Y"), "split_arrow": ("d", "D"),
    # The princess's wands: the star.
    "prism": ("w", "m"), "focus": ("H", "Y"), "spectrum": ("p", "P"),
    "point_blank": ("r", "R"), "refraction": ("o", "O"), "converge": ("v", "V"),
    # The bard's lutes: the body.
    "crescendo": ("r", "R"), "lullaby": ("j", "J"), "syncopation": ("g", "G"),
    "dissonance": ("u", "U"), "grand_finale": ("y", "Y"), "sheet_music": ("d", "D"),
}

# --- The heroes -------------------------------------------------------------------------
# The body's colours (what a chest piece recolours) and from which row.
BODY: dict[str, tuple[str, str, int]] = {
    "wizard": ("b", "B", 7), "dwarf": ("r", "R", 6), "bard": ("v", "V", 7),
    "princess": ("p", "P", 7), "huntress": ("g", "G", 6),
}

# The weapon: its box (x0, y0, x1, y1, inclusive) and which of its letters
# are the accent ("1" light, "2" dark).
WEAPON: dict[str, tuple[tuple[int, int, int, int], dict[str, str]]] = {
    "wizard": ((11, 5, 13, 6), {"o": "1", "O": "2"}),        # the staff's orb
    "dwarf": ((12, 3, 13, 7), {"m": "1", "M": "2"}),         # the axe on his shoulder
    "bard": ((3, 9, 8, 12), {"t": "1", "T": "2"}),           # the lute's body
    "princess": ((12, 4, 13, 8), {"y": "1", "Y": "2"}),      # the wand's star
    "huntress": ((10, 0, 13, 13), {"t": "1"}),               # the bow
}

# Where a legendary piece's glint blinks, in art pixels (facing right).
SPARKLE: dict[str, dict[str, tuple[int, int]]] = {
    "wizard": {"head": (6, 2), "chest": (5, 10), "main": (13, 5)},
    "dwarf": {"head": (5, 2), "chest": (2, 9), "main": (13, 4)},
    "bard": {"head": (6, 1), "chest": (4, 8), "main": (5, 10)},
    "princess": {"head": (7, 1), "chest": (5, 12), "main": (13, 5)},
    "huntress": {"head": (5, 1), "chest": (4, 9), "main": (12, 6)},
}

# The head shapes, per hero: (first row, rows). See the module docstring.
HEADGEAR: dict[str, dict[str, tuple[int, tuple[str, ...]]]] = {
    "wizard": {
        "hood": (0, ("..............",
                     "......kk......",
                     ".....k11k.....",
                     "....k1111k....",
                     "...k113112k...",
                     "...k4ssss2k   ",
                     "...k1swws4k   ")),
        "lich": (0, ("..............",
                     "......kk......",
                     ".....k11k.....",
                     "....k1111k....",
                     "...k111112k...",
                     "...k13CC32k   ",
                     "...k1CwwC2k   ")),
        "helm": (0, ("..............",
                     "......44......",
                     ".....kkkk.....",
                     "....k3112k....",
                     "...k111112k...",
                     "...k2ssss2k   ")),
        "crown": (0, ("..............",
                      "..............",
                      "....1.11.1....",
                      "....131131....",
                      "....kwwwwk....")),
        "icecrown": (0, ("..............",
                         "....3.33.3....",
                         "....1.11.1....",
                         "....111111....",
                         "....kwwwwk....")),
        "cap": (0, ("..............",
                    "....kkkkkk....",
                    "...k141114k...",
                    "..k11141141k..",
                    "..k22222222k..")),
        "wig": (0, ("..............",
                    "..............",
                    ".....kkkk.....",
                    "....k1211k....",
                    "...k121121k...",
                    "...k1ssss1k   ",
                    "...k2swws2k   ",
                    "    1    1    ")),
        "mask": (5, ("    k3113k    ",
                     "    k2ww2k5   ")),
    },
    "dwarf": {
        "hood": (0, ("..............",
                     "......kk......",
                     ".....k11k.....",
                     "....k1111k....",
                     "...k111412k...",
                     "..k11131112k..",
                     "..k4sksskS2k..")),
        "lich": (0, ("..............",
                     "......kk......",
                     ".....k11k.....",
                     "....k1111k....",
                     "...k111112k...",
                     "..k11111112k..",
                     "..k13CCCC32k..")),
        "helm": (0, ("......44......",
                     "....kkkkkk....",
                     "...k311112k...",
                     "..k11111112k..",
                     "..kkkkkkkkkk..")),
        "crown": (0, ("..............",
                      "..............",
                      "...1.1..1.1...",
                      "...13111131...",
                      "...kaaaaaak...")),
        "icecrown": (0, ("..............",
                         "...3.3..3.3...",
                         "...1.1..1.1...",
                         "...11111111...",
                         "...kaaaaaak...")),
        "cap": (0, ("..............",
                    "....kkkkkk....",
                    "...k141141k...",
                    "..k14111141k..",
                    "..k22222222k..")),
        "wig": (0, ("..............",
                    "..............",
                    "....kkkkkk....",
                    "...k121121k...",
                    "..k12111121k..",
                    "..k1sksskS1k..",
                    "   2      2   ")),
        "mask": (5, ("   k131131k5  ",
                     "     2222     ")),
    },
    "bard": {
        "hood": (0, ("..............",
                     "......kk......",
                     ".....k11k.....",
                     "....k11311k...",
                     "...k4hsssh2k..",
                     "...k1hsssS4k..")),
        "lich": (0, ("..............",
                     "......kk......",
                     ".....k11k.....",
                     "....k11111k...",
                     "...k13CCC32k..",
                     "...k1CCCCC2k..",
                     ".....kCCCk....")),
        "helm": (0, ("..............",
                     "......44......",
                     ".....kkkkk....",
                     "....k31112k...",
                     "...k2hsssh2k..")),
        "crown": (0, ("..............",
                      ".....1.1.1....",
                      ".....13131....",
                      "....khhhhhk...")),
        "icecrown": (0, (".....3.3.3....",
                         ".....1.1.1....",
                         ".....11111....",
                         "....khhhhhk...")),
        "cap": (0, (".....kkkkk....",
                    "....k14141k...",
                    "...k1411141k..",
                    "...k2222222k..")),
        "wig": (0, ("..............",
                    ".....kkkkk....",
                    "....k12121k...",
                    "...k1211121k..",
                    "...k11sss11k..",
                    "...k21sssS2k..",
                    "    2     2   ")),
        "mask": (4, ("    kh313hk   ",
                     "    kh222Sk5  ")),
    },
    "princess": {
        "hood": (0, ("......kkk.....",
                     ".....k111k....",
                     "....k11311k...",
                     "..k1HHssssH2k.",
                     "..k4HssssSH2k.",
                     "..k1HHssSHH4k.",
                     "..k1HkkkkkH2k.")),
        "lich": (0, ("......kkk.....",
                     ".....k111k....",
                     "....k11111k...",
                     "..k1HH3CC3H2k.",
                     "..k1HCCCCCH2k.",
                     "..k1HHCCCHH2k.",
                     "..k1HkkkkkH2k.")),
        "helm": (0, ("......44......",
                     "....kkkkkkk...",
                     "...k3111112k..")),
        "crown": (0, (".....1.1.1....",
                      ".....13131....")),
        "icecrown": (0, (".....3.3.3....",
                         ".....1.1.1....",
                         "....k11111k...")),
        "cap": (0, (".....kkkkk....",
                    "...k1414141k..",
                    "..k222222222k.")),
        "wig": (0, ("..............",
                    ".....kkkkk....",
                    "....k12121k...",
                    "...k12ssss1k..",
                    "...k2ssssS2k..",
                    "...k12ssS21k..",
                    "...k2kkkkk1k..")),
        "mask": (3, ("   kHH3113Hk  ",
                     "   kH2222SHk5 ")),
    },
    "huntress": {
        "hood": (0, ("....kkkk..    ",
                     "...k1141k.    ",
                     "..k113112k    ",
                     "..k1ssss2k    ",
                     "..k4ssssSk    ",
                     "..k11ssSk     ",
                     ".k12kggkk     ")),
        "lich": (0, ("....kkkk..    ",
                     "...k1111k.    ",
                     "..k111112k    ",
                     "..k13CC32k    ",
                     "..k1CCCCCk    ",
                     "..k11CCCk     ",
                     ".k12kggkk     ")),
        "helm": (0, ("....kkkk..    ",
                     "...k3112k.    ",
                     "..k111112k    ",
                     "..k2ssss2k    ")),
        "crown": (0, ("...1.11.1.    ",
                      "...131131.    ")),
        "icecrown": (0, ("...3.33.3.    ",
                         "...1.11.1.    ",
                         "..k111111k    ")),
        "cap": (0, ("...kkkkkk.    ",
                    "..k141141k    ",
                    ".k22222222k   ")),
        "wig": (0, ("....kkkk..    ",
                    "...k1211k.    ",
                    "..k121121k    ",
                    "..k1ssss1k    ",
                    "..k2ssssSk    ",
                    "..k12ssSk     ",
                    ".k21kggkk     ")),
        "mask": (3, ("  kh3113hk    ",
                     "  kh2222Sk5   ")),
    },
}


@dataclass(frozen=True)
class Look:
    """What a hero wears that shows: the head, chest and main-hand bases
    (None: nothing there) and which of those slots hold a legendary."""

    head: str | None = None
    chest: str | None = None
    main: str | None = None
    legend: tuple[str, ...] = ()

    @property
    def key(self) -> str:
        """Names the baked sprite (the glints aren't baked)."""
        return f"{self.head or ''}|{self.chest or ''}|{self.main or ''}"


def look_of(eq) -> Look | None:
    """The Look of an Equipment (players/gear.py): its worn head, chest and
    main-hand pieces that have a look here. None when nothing shows."""
    worn = eq.worn
    picks = {}
    legend = []
    for slot, table in (("head", HEAD_LOOKS), ("chest", CHEST_LOOKS), ("main", MAIN_LOOKS)):
        p = worn.get(slot)
        if p is not None and p.key in table:
            picks[slot] = p.key
            if p.rarity == "legendary":
                legend.append(slot)
    if not picks:
        return None
    return Look(picks.get("head"), picks.get("chest"), picks.get("main"), tuple(legend))


def axe_head_color(owner, default: tuple) -> tuple:
    """The colour of a thrown axe's head: its thrower's main-hand accent
    (MAIN_LOOKS), else `default`."""
    look = getattr(owner, "look", None)
    if look is None or look.main is None:
        return default
    return palette.SPRITE_COLORS[MAIN_LOOKS[look.main][0]]


def _in_box(box, x: int, y: int) -> bool:
    x0, y0, x1, y1 = box
    return x0 <= x <= x1 and y0 <= y <= y1


def dress(hero: str, rows: list[str], look: Look | None) -> list[str]:
    """The hero's art `rows` with `look` put on: the head shape, the body's
    colours, the weapon's accent. Heroes without HEADGEAR (or no look) come
    back as they are."""
    if look is None or hero not in HEADGEAR:
        return rows
    grid = [list(r) for r in rows]
    box, accent = WEAPON[hero]
    if look.chest is not None:
        light, dark, first = BODY[hero]
        new = dict(zip((light, dark), CHEST_LOOKS[look.chest]))
        for y in range(first, len(grid)):
            for x, ch in enumerate(grid[y]):
                if ch in new:
                    grid[y][x] = new[ch]
    if look.main is not None:
        tint = dict(zip("12", MAIN_LOOKS[look.main]))
        for y in range(len(grid)):
            for x, ch in enumerate(grid[y]):
                if _in_box(box, x, y) and ch in accent:
                    grid[y][x] = tint[accent[ch]]
    if look.head is not None:
        spec = HEAD_LOOKS[look.head]
        shape, light, dark, extra = spec[0], spec[1], spec[2], spec[3]
        detail = spec[4] if len(spec) > 4 else (light if shape == "hood" else ".")
        beak = spec[5] if len(spec) > 5 else " "
        ink = {"1": light, "2": dark, "3": extra, "4": detail, "5": beak}
        top, drawing = HEADGEAR[hero][shape]
        for dy, line in enumerate(drawing):
            y = top + dy
            for x, ch in enumerate(line):
                ch = ink.get(ch, ch)
                if ch == " " or (_in_box(box, x, y) and grid[y][x] != "."):
                    continue                  # kept, or the weapon in front
                grid[y][x] = ch
    return ["".join(r) for r in grid]
