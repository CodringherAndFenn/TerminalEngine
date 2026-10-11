"""
render/swamp_art.py -- the swamp's new enemies (P11), drawn like the heroes
(see render/plains_art.py for the format). Importing this adds them to
render/characters.ART.
"""

from __future__ import annotations

from .characters import ART
from .plains_art import _pad

SWAMP_ART = {
    # --- Simple chasers --------------------------------------------------------------
    "bog_zombie": [
        "...kkkkk",
        "..kgGgggk",
        "..kgkgkgk",
        "..kgggGgk",
        "...kGGGk",
        "..kNnNnNk",
        ".kgNnNnNgk",
        ".kgkNnNnkgk",
        "..kkNNNNkk",
        "...kGGGGk",
        "...kgkkgk",
        "...kGk.kGk",
        "...kkk.kkk",
    ],
    "newt": [
        ".........kk",
        ".kkkkkkkkaak",
        "kaaAaaAaakak",
        ".kkkaakkkk",
        "...k..k",
    ],
    "gator_hatchling": [
        "..........kk",
        "....kkkkkkGGk",
        "..kkgGgGgggwgk",
        "kkgggggggggggk",
        ".kkkGkkkkGkkk",
        "....kk...kk",
    ],
    "mudskipper": [
        "......kk",
        "....kknnkk",
        "..kknnnwnnk",
        "kknnnnnnnnk",
        ".kNkkNNkkk",
        "..k...kk",
    ],
    # --- Beasts --------------------------------------------------------------------
    "crocodile": [
        "............kk",
        "....kkkkkkkkwk",
        ".kkGgGgGgGgggk",
        "kGgGgGgGgGgrgk",
        "Ggggggggggggkk",
        "kkkGkkkkkGkwwk",
        "...kk....kk",
    ],
    "croc_lurk": [
        ".........kk.kk",
        ".......kkrkkrk",
        ".....kkGgggggk",
        "...kkkGGkkkkkk",
    ],
    "turtle": [
        "...kkkkkk",
        ".kkGgGgGgkk",
        "kGgGGgGGgGk.kk",
        "kGgGgGgGgGkkgk",
        "kGGGGGGGGGkgkk",
        ".kgk.kgk.kgk",
        ".kk..kk..kk",
    ],
    "turtle_shell": [
        "....kkkkkk",
        "..kkGgGgGgkk",
        ".kGgGGgGGgGk",
        "kGgGgGgGgGgGk",
        "kGGGGGGGGGGGk",
        ".kkkkkkkkkkk",
    ],
    "heron": [
        ".........kk",
        "........kwwkyy",
        "...........kwk",
        "...........kwk",
        "..........kwk",
        "...kkkkkkkwk",
        "..kmmwwwwwwk",
        ".kmmmwwwwwk",
        "..kkmmmmkk",
        ".....kyk",
        ".....kyk",
        ".....kyk",
        "....kkkkk",
    ],
    # --- Folk ---------------------------------------------------------------------
    "swamp_hag": [
        "....kkkkk",
        "..kkGGGGGkk",
        "..kGkgggkGk",
        "...kgkgkgk",
        "...kgggggk..v",
        "....kgggk..kvk",
        "..kNNNNNNk..t",
        ".kgNNNNNNNk.t",
        ".kgkNNNNNkgkt",
        "..kNNNNNNNk.t",
        "..kNNNNNNNk.t",
        "..kkkkkkkkk.T",
    ],
    "lizardman": [
        "...kkkk",
        "..kgggGk",
        ".kgkggggkk",
        ".kggggggrk",
        "..kGGGGGk....m",
        "..kgggggk...kt",
        ".kgNNNNNgk.kt",
        ".kgNNyNNgkkt",
        "..kNNNNNkt",
        "...kgggk",
        "...kgkgk",
        "..kgk.kgk",
        "..kkk.kkk",
    ],
    "marsh_light": [
        "....kk",
        "...kook",
        "..koiook",
        "..koiiok",
        "...kook",
        "....kk",
    ],
    # --- Rot and muck --------------------------------------------------------------
    "bloated_corpse": [
        "....kkkk",
        "...kuuuuk",
        "...kukuuk",
        "..kkuuuukk",
        ".kuUuuuuUuk",
        "kuuuGuuGuuuk",
        "kuUuuuuuuUuk",
        "kuuuuGuuuuuk",
        ".kuUuuuuUuk",
        "..kkuuuukk",
        "...kuk.kuk",
        "...kkk.kkk",
    ],
    "sludge": [
        "....kkkkkk",
        "..kkGgGgGgkk",
        ".kGggkgggkgGk",
        "kGggggggggggGk",
        "kGgGggGgggGgGk",
        "kkkkkkkkkkkkkk",
    ],
}
SWAMP_ART["sludge_mid"] = SWAMP_ART["sludge"]
SWAMP_ART["sludge_small"] = SWAMP_ART["sludge"]

for _name, _rows in SWAMP_ART.items():
    ART[_name] = _pad(_rows)
