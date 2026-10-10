"""
render/plains_art.py -- the plains' new enemies (P7), drawn like the heroes:
14 x 18 letter pictures (palette.SPRITE_COLORS, "." = transparent),
facing right, feet on row 15. Each is written as just its visible rows
and padded here: rows go to the bottom (two empty rows under the feet,
like every character), each row to 14 wide.

Importing this adds them to render/characters.ART (and the lancer's horse
to render/mounts.MOUNTS), so draw_character draws them like any other.
"""

from __future__ import annotations

from .characters import ART, ART_H, ART_W
from .mounts import MOUNTS, Mount


def _pad(rows: list[str]) -> list[str]:
    assert all(len(r) <= ART_W for r in rows), rows
    body = [r.ljust(ART_W, ".") for r in rows]
    return ["." * ART_W] * (ART_H - 2 - len(body)) + body + ["." * ART_W] * 2


PLAINS_ART = {
    # --- Simple chasers --------------------------------------------------------------
    "field_rat": [
        "........kk",
        "....kkkkknkk",
        "...knnnnnnnkk",
        "kk.knnnnnnnkrk",
        ".kkknnnnnnnnkk",
        "....kNk..kNk",
        "....kk....kk",
    ],
    "farmhand": [
        "...kkkkkk",
        ".kklllllllkk",
        "...kuuuuUk.m.m",
        "...kukuuUk.mmm",
        "....kuUUk...t",
        "...kNnnnNk..t",
        "..knNnnnNnk.t",
        "..kunnnnnNkuk",
        "..kkNnnnNkkt",
        "...kbbbbBk..t",
        "...kbbkbBk..t",
        "...kbk.kBk..t",
        "...kUk.kUk",
        "...kkk.kkk",
    ],
    "goose": [
        ".........kk",
        "........kwwk",
        "........kwkaak",
        "........kwk",
        "........kwk",
        "..kkkkkkkwk",
        ".kwwwwwwwwk",
        "kwwmwwwwwwk",
        ".kwwmmwwwk",
        "...kaak.kaak",
    ],
    # --- Beasts ---------------------------------------------------------------------
    "hound": [
        "...........kk",
        "..........knk",
        ".........knnnk",
        "k........knkwk",
        "nk.kkkkkknnnnk",
        ".knnnnnnnnnNk",
        "..knnnnnnnNk",
        "..knNkkkknNk",
        "..kNk....kNk",
        "..kk.....kk",
    ],
    "hawk": [
        "kk..........kk",
        "knk........knk",
        ".knk......knk",
        "..knnk..knnk",
        "...knnkknnk",
        "....knnnnkkk",
        "....knwwnkyk",
        ".....knnk",
        "......kk",
    ],
    "molehill": [
        "....kkkkk",
        "..kknnnnnkk",
        ".knnnNkkNnnnk",
        ".knNnkCCknNnk",
        "knnnnnNNnnnNnk",
        "kNnnNnnnnNnnNk",
        "kkkkkkkkkkkkkk",
    ],
    "mole_rat": [
        "..kkkkkkkk",
        ".kppppppppkk",
        "kpppPpppppwkk",
        ".kPpppPpppPk",
        "..kPk..kPk",
    ],
    "bull": [
        "..........w..w",
        ".........kwkkw",
        "........knnnnk",
        "k.kkkkkknnknnk",
        "nkNNNNNNNnnnnk",
        ".kNNNNNNNNnyk",
        ".kNNNNNNNNNk",
        ".kNNNNNNNNNk",
        "..kNkkkkkNk",
        "..kNk...kNk",
        "..kkk...kkk",
    ],
    # --- Bandits and folk -----------------------------------------------------------
    "bandit": [
        "....kkkkk",
        "...kNNNNNk",
        "..kNNssssNk",
        "..kNrrrrrNk",
        "...kNNNNNk",
        "..kgggNgggk..k",
        ".kgggggggGk.kh",
        ".ksgggggGGksh",
        "..kkgggggkk",
        "...knnnnnk",
        "...knnknnk",
        "...kNk.kNk",
        "...kkk.kkk",
    ],
    "shieldbearer": [
        "....kkkkk",
        "...kmmmmMk",
        "...kmkkkMk",
        "...kmssmMk",
        "..kkkmmMk.kkk",
        ".kmrrrrMkktttk",
        ".kmrrrrMktTmtk",
        ".kmrrrrMktmmTk",
        ".kmrrrrMktTmtk",
        "..krrrrkktttk",
        "..kmmmmMk.kkk",
        "..kmk.kMk",
        "..kkk.kkk",
    ],
    "priest": [
        "....kkkk",
        "...kwwwwk..kgk",
        "..kwssssk..kgk",
        "..kwsssSk...t",
        "...kwwwk....t",
        "..kwwywwwk.st",
        ".kwwwyywwwkkt",
        ".kwwwywwwwk.t",
        ".kwwwwwwwwk.t",
        ".kwwwwwwwwk.t",
        "..kwwwwwwk..t",
        "..kkkkkkkk..T",
    ],
    # --- Haunted farmland and odd ones ------------------------------------------------
    "scarecrow": [
        ".....kkkk",
        "...kkllllkk",
        "..klllllllllk",
        "....knnnnk",
        "....kknnkk",
        "....knkknk",
        "kkkkkkgggkkkkk",
        "llkggggggggkll",
        "..kgggrgggk",
        "..kggggggGk",
        "...kggggGk",
        "....kttk",
        "....kttk",
        "....kttk",
        "...kkkkkk",
    ],
    "straw_golem": [
        ".....kkkk",
        "...kkllllkk",
        "..klllLlllllk",
        ".kllLlllllLllk",
        ".kllllrLLrlllk",
        "kllLlllllllLlk",
        "klllllLlllllLk",
        "kLlllllllLlllk",
        "kllllLllllllLk",
        ".kLlllllLllLk",
        ".kllLllllllk",
        "..kLlk..kLlk",
        "..kkkk..kkkk",
    ],
    "drummer": [
        "....kkkk",
        "...krrrrk",
        "...kyyyyk",
        "...kssssk",
        "....kssk",
        "..krrrrrrk.k",
        ".ksrrrrrrsk.t",
        ".kkwwwwwwkkt",
        ".kyrrrrrrykk",
        ".kyrRrRrRyk",
        ".kkwwwwwwkk",
        "...kbk.kbk",
        "...kkk.kkk",
    ],
    "crow": [
        "..k.......k",
        ".kck.....kck",
        ".kcck...kcck",
        "..kcccccck",
        "...kccccckkk",
        "....kcccckyk",
        ".....kkkkk",
    ],
}

for _name, _rows in PLAINS_ART.items():
    ART[_name] = _pad(_rows)

# The lancer's horse: the pony's shape in browns, with a dark mane.
_HORSE = str.maketrans({"w": "n", "m": "N", "p": "k", "P": "k"})
MOUNTS["horse"] = Mount(tuple(tuple(row.translate(_HORSE) for row in frame)
                              for frame in MOUNTS["pony"].frames), MOUNTS["pony"].seat)
