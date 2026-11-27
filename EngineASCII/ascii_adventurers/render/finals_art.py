"""
render/finals_art.py -- the final bosses' pictures (M33, design/FINALS.md),
drawn like the heroes (render/plains_art.py has the format), facing right.
Importing this adds them to render/characters.ART.

M33.1, the Fossil Angel, form 1 (its bones walk): a skeleton of old bone
(d/D) with eyes of fire (f/F), lumps of amber in it (a/A), jungle vines
round its bones (g/G); its stone wings (m/M feathers edged in bone, drawn
either side of the body by render/fossil_angel.py, folded or beating up).
Its trophy for the Guild hall: a stone feather set in amber on a gold cup
(y/Y).

M33.2, form 2 (the first angel unveils): the same bones with their flesh
grown back, red and raw (7/8), the old bone showing (d/D), eyes of holy
light (Z), clotted blood where the vines were (z); its wings the stone
wings' shape in raw flesh with white feathers (7/8/w). A drop of its blood
(r/R), crawling.
"""

from __future__ import annotations

from .characters import ART
from .plains_art import _pad

FINALS_ART = {
    # --- M33.1: the Fossil Angel ----------------------------------------------------------
    "fossil_angel": _pad([          # its bones walk: a skull aflame, ribs, amber, vines
        "....kkkkk",
        "...kddddDk",
        "...kdfkfdk",
        "...kDdddDk",
        "....kdkdk",
        "..kkkdDdkkk",
        ".kdDkdkdkDdk",
        "kdk.kdddk.kdk",
        "kdk.kDkDk.kgk",
        "kak.kdadk.kgk",
        "kAk.kaAak.kdk",
        ".k..kdddk..k",
        "....kDkDk",
        "...kdk.kdk",
        "...kgk.kak",
        "..kddk.kddk",
    ]),
    "fossil_angel_beat": _pad([     # its arms raised (beating its wings, weeping, calling)
        "kdk.kkkkk.kdk",
        "kdkkddddDkkdk",
        ".kdkdfkfdkdk",
        "..kkDdddDkk",
        "....kdkdk",
        "..kkkdDdkkk",
        "...kkdkdkk",
        "....kdddk",
        "....kDkDk",
        "....kdadk",
        "....kaAak",
        "....kdddk",
        "....kDkDk",
        "...kdk.kdk",
        "...kgk.kak",
        "..kddk.kddk",
    ]),
    # Its right wing (the left is this mirrored), folded at its side...
    "fossil_wing": [
        "..............",
        "..............",
        "..............",
        "..............",
        "kkk...........",
        "kmmkk.........",
        "kmMmmkk.......",
        ".kmmdmmkk.....",
        ".kmMmmMmmkk...",
        "..kmmdmmdmmk..",
        "..kmMmmMmmMk..",
        "...kmmdmmdk...",
        "...kmMmmMk....",
        "....kmmdk.....",
        "....kmMk......",
        ".....kk.......",
        "..............",
        "..............",
    ],
    # ...and beating up.
    "fossil_wing_up": [
        ".........kk...",
        ".......kkmmk..",
        ".....kkmMmmk..",
        "....kmmdmmk...",
        "...kmMmmMk....",
        "..kmmdmmdk....",
        ".kmMmmMmk.....",
        "kmmdmmdk......",
        "kmMmmk........",
        "kmmdk.........",
        ".kkk..........",
        "..............",
        "..............",
        "..............",
        "..............",
        "..............",
        "..............",
        "..............",
    ],
    # Its trophy (the Guild hall, scenes/guild_hall.py).
    "trophy_fossil_angel": _pad([
        "......kk",
        ".....kddk",
        "....kdmmdk",
        "....kmdmMk",
        "...kmMdmmk",
        "...kdmmdMk",
        "....kmdmk",
        "....kaAak",
        "...kaAAAak",
        "...kaAfAak",
        "....kaAak",
        ".....kyk",
        "....kyyyk",
        "...kyYyYyk",
        "....kyyyk",
        "..kkyYYYykk",
    ]),
}

# M33.2: form 2 -- the same shapes, their flesh grown back.
_FLESH = str.maketrans({"d": "7", "D": "8", "f": "Z", "F": "Z", "a": "d", "A": "D", "g": "z",
                        "G": "z"})
_FLESH_WING = str.maketrans({"m": "7", "M": "8", "d": "w"})
for _src, _dst, _tr in (("fossil_angel", "fossil_angel_flesh", _FLESH),
                        ("fossil_angel_beat", "fossil_angel_flesh_beat", _FLESH),
                        ("fossil_wing", "flesh_wing", _FLESH_WING),
                        ("fossil_wing_up", "flesh_wing_up", _FLESH_WING)):
    FINALS_ART[_dst] = [row.translate(_tr) for row in FINALS_ART[_src]]
FINALS_ART["blood_drop"] = _pad([   # a drop of its blood, crawling
    "....kkk",
    "..kkrrrk",
    ".krRrrwrk",
    ".krrRrrrk",
    "..kkrrrkk",
    "...k...k",
])

assert all(len(r) == 14 for name, rows in FINALS_ART.items() for r in rows), "rows are 14 wide"
assert all(len(rows) == 18 for rows in FINALS_ART.values()), "pictures are 18 tall"
ART.update(FINALS_ART)
