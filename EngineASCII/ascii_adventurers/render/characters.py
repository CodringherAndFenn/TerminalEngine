"""
render/characters.py -- pixel-art heroes and shooting enemies.

Every character is a small hand-drawn picture: 14 x 18 pixels, seen from
above at an angle, facing right. Each letter is one pixel, colored from
palette.SPRITE_COLORS ("." = transparent). A character is drawn at
`sprite_scale` screen pixels per art pixel (3: 42 x 54 px, about a tile
wide and two tall; the ogre and tower use 4).

Frames are made from the one picture, then baked once into images
through the SpriteBank (render/sprites.py) and drawn at the character's
exact pixel position:
  * facing: mirrored when the character aims left;
  * walking: a 4-frame cycle -- stand, hop up one pixel with the back foot
    still planted, stand, hop with the other foot planted -- advanced by
    distance walked (config.WALK_STEPS_PER_TILE);
  * hit: every color washed toward white for a moment after taking damage.

A few big figures are painted from shapes instead (render/painted.PAINTED:
the Snow King, Fragile, Mr. Buttons); draw_character() draws those too,
by the same name.

Worn gear shows on a hero (M28.6, render/gear_looks.py): the picture is
dressed in its `look` (head shape, chest colours, weapon accent) before it
is baked, and a worn legendary blinks a glint (draw_sparkles).
"""

from __future__ import annotations

import math

import pygame

from .. import config, palette
from .gear_looks import SPARKLE, Look, dress
from .painted import PAINTED, painter
from .sprites import SpriteBank

ART: dict[str, list[str]] = {
    # --- Heroes -------------------------------------------------------------------
    "wizard": [
        "......kk......",
        ".....kbBk.....",
        "....kbbbBk....",
        "...kbbybbBk...",
        "..kkkkkkkkkk..",
        "....kssssk..ko",
        "....kswwsk.kOo",
        "...kbwwwwbk.kt",
        "..kbbbwwbbBkst",
        "..kbbbbbbbBk.t",
        "..kbbbybbbBk.t",
        "..kbbbbbbbBk.t",
        "..kbbbbbbbBk.t",
        "...kbbbbbBk..t",
        "...kbbbbbBk..t",
        "....kk..kk...T",
        "..............",
        "..............",
    ],
    "dwarf": [
        "..............",
        "....kkkkkk....",
        "...kmmmmmMk...",
        "..kmmmyymmMk.m",
        "..kkkkkkkkkkmm",
        "...ksksskSk.tM",
        "..kaassssaAkt.",
        "..kaaaaaaaAkt.",
        ".kRkaaaaaaAkrk",
        ".kRraaaaaaArrk",
        ".ksraaaaaaArsk",
        "..kkraaaaArkk.",
        "..kTTTyyTTTk..",
        "..krRRk.krRRk.",
        "..kTTTk.kTTTk.",
        "..kkkkk.kkkkk.",
        "..............",
        "..............",
    ],
    "bard": [
        "......kkk.....",
        "....kkgggk.kr.",
        "...kgggggGkrk.",
        "..kkkkkkkkkk..",
        "....khssshk...",
        "....khsssSk...",
        ".....kssSk....",
        "...kvvkkvvk...",
        "..kvvyvvvvVk..",
        "..kvkttTkvVk..",
        "..kkttkTTkVk..",
        "..ksktTtkkVk..",
        "...kkttkvvk...",
        "...kvkkvvVk...",
        "...kVk.kVVk...",
        "...kkk.kkk....",
        "..............",
        "..............",
    ],
    "princess": [
        ".....y.y.y....",
        ".....yyyyy....",
        "....kHHHHHk...",
        "...kHHssssHk..",
        "...kHssssSHk..",
        "...kHHssSHHky.",
        "...kHkkkkkHkYy",
        "...kkppppkkkd.",
        "..kppwppppPkd.",
        "..ksppppppPsk.",
        "..kkppppppPkk.",
        ".kpppppppppPk.",
        ".kpppwppppppPk",
        "kppppppppppPPk",
        "kpppppppppPPPk",
        ".kkkkkkkkkkkk.",
        "..............",
        "..............",
    ],
    "huntress": [
        "....kkkk...k..",
        "...khhhhk.kt..",
        "..khhhhhhkkt..",
        "..khsssshk.t..",
        "..khssssSk..t.",
        "..khhssSk...t.",
        ".khhkggkk...t.",
        ".khkgggGGk..t.",
        ".kkgggyggGksk.",
        "..kgggggGGk.t.",
        "..kgGggggGk.t.",
        "..kkggggGk.t..",
        "...kGGkGGk.t..",
        "...khhkhhk.k..",
        "...kTTkTTk....",
        "...kkk.kkk....",
        "..............",
        "..............",
    ],
    # --- Enemies that shoot --------------------------------------------------------
    "goblin": [
        "..............",
        "..............",
        "....kkkkk.....",
        "..kgkgggGkgk..",
        "..kggkggkgGk.k",
        "...kgrggrGk.kt",
        "...kgggggGk.t.",
        "....kGkkGk.kt.",
        "...khhhhhhk.t.",
        "..kghhhhhhGkt.",
        "..kgkhhhhkgst.",
        "...kkhhhhk..t.",
        "....khkkhk..k.",
        "....kGk.kGk...",
        "....kkk.kkk...",
        "..............",
        "..............",
        "..............",
    ],
    "ogre": [
        "....kkkkkk....",
        "...keeeeeek...",
        "..keereereek..",
        "..keeeeeeeek..",
        "..kewkkkkwek..",
        "...keeeeeek...",
        ".kkkhhhhhhkkk.",
        "keekhhhhhhkeek",
        "keekhhyhhhkeek",
        "keekhhhhhhkeek",
        "keEkhhhhhhkEek",
        ".kkkhhhhhhkkk.",
        "...khhkkhhk...",
        "...keek.keek..",
        "...keek.keek..",
        "...kkkk.kkkk..",
        "..............",
        "..............",
    ],
    "warlock": [
        "......kkk.....",
        ".....kVVVk.kk.",
        "....kVvvvVkkrk",
        "...kVvvvvvVkrk",
        "...kVkrkrkVkt.",
        "...kVkkkkkVkt.",
        "....kVVVVVk.t.",
        "..kvvvvvvvVkt.",
        "..kvvyvvvvVst.",
        "..kvvvvvvvVkt.",
        "..kVvvvvvvVkt.",
        "..kVvvvvvvVkt.",
        "..kVVvvvvVVkt.",
        "...kVVVVVVk.t.",
        "...kkkkkkkk.T.",
        "..............",
        "..............",
        "..............",
    ],
    "tower": [
        "......kk......",
        ".....kppk.....",
        "....kpwppk....",
        "....kpppPk....",
        ".....kPPk.....",
        "....kkkkkk....",
        "...kMmmmmMk...",
        "...kmMmmmmk...",
        "...kmmmpmmk...",
        "...kmmpppmk...",
        "...kmmmpmmk...",
        "...kMmmmmMk...",
        "..kmmMmmmmmk..",
        "..kmmmmmMmmk..",
        ".kMmmmmmmmmMk.",
        ".kkkkkkkkkkkk.",
        "..............",
        "..............",
    ],
    # --- M12 ------------------------------------------------------------------------
    "wisp": [                # a floating eye in a cold glow
        "..............",
        ".....oooo.....",
        "...ooOOOOoo...",
        "..oOOwwwwOOo..",
        "..oOwwwwwwOo..",
        ".oOwwkkkkwwOo.",
        ".oOwwkrrkwwOo.",
        ".oOwwkrrkwwOo.",
        ".oOwwkkkkwwOo.",
        "..oOwwwwwwOo..",
        "..oOOwwwwOOo..",
        "...ooOOOOoo...",
        ".....oooo.....",
        "......oo......",
        ".......o......",
        "......o.......",
        "..............",
        "..............",
    ],
    "toad": [                # squat, warty, mouth open
        "..............",
        "..............",
        "..............",
        "..............",
        "..............",
        "..............",
        "......kkkk....",
        "....kkggggkk..",
        "...kggggkwkgk.",
        "..kgggggkkkggk",
        ".kgggyggggggGk",
        ".kgggggggrrrrk",
        ".kGggggggggGGk",
        "..kGGggggGGGk.",
        ".kgGk.kkk.kGgk",
        ".kkkk.....kkkk",
        "..............",
        "..............",
    ],
    "spitter": [             # a red-capped mushroom with a face
        "..............",
        "....kkkkkk....",
        "..kkrrwrrrkk..",
        ".krrrrrrwrrrk.",
        "krrwrrrrrrrwrk",
        "krrrrrwrrrrrRk",
        "kRRRRRRRRRRRRk",
        ".kkkkkkkkkkkk.",
        "....kwwwwk....",
        "....kwkkwk....",
        "....kwwwwk....",
        "....kwwwmk....",
        "...kwwwwwmk...",
        "...kmwwwwmk...",
        "..kkkkkkkkkk..",
        "..............",
        "..............",
        "..............",
    ],
    # --- The Guild Hall's people (M15) ---------------------------------------------
    "guildmaster": [
        "..............",
        ".....kkkk.....",
        "....kvvvvk....",
        "...kvvyvvVk...",
        "...kkkkkkkk...",
        "....kssssk....",
        "....kskksk....",
        "...kwwwwwwk...",
        "..kvwwwwwwVk..",
        "..kvvwwwwvVk..",
        "..kvvvwwvvVk..",
        "..kvvvyyvvVk..",
        "..kvvvvvvvVk..",
        "..kvvvyvvvVk..",
        "...kvvvvvVk...",
        "...kvvvvvVk...",
        "....kk..kk....",
        "..............",
    ],
    "trainer": [
        "......rr......",
        ".....kRrk.....",
        "....kmmmmk....",
        "...kmMmmmMk...",
        "...kmkkkkmk..k",
        "...kmsssskk.km",
        "....kssssk..km",
        "...kmmmmmmk.km",
        "..kmmmmmmmMkkm",
        "..kMmmyymmMksk",
        "..kMmmmmmmMk.t",
        "..kkMmmmmMkk..",
        "...kTTyyTTk...",
        "...kmMk.kmMk..",
        "...kmMk.kmMk..",
        "...kkkk.kkkk..",
        "..............",
        "..............",
    ],
    "archivist": [
        "......kk......",
        ".....kgGk.....",
        "....kgggGk....",
        "...kgggggGk...",
        "...kgkkkkGk...",
        "...kgsssskk...",
        "...kgswwsGk...",
        "...kggssggGk..",
        "..kgggggggGk..",
        "..kggkkkkgGk..",
        "..kggkyyykGk..",
        "..kggkkkkgGk..",
        "..kgggggggGk..",
        "..kgggggggGk..",
        "...kgggggGk...",
        "...kgggggGk...",
        "....kk..kk....",
        "..............",
    ],
    # --- Quest givers (M17) ---------------------------------------------------------
    "frog_hunter": [         # wide-brimmed hat, green coat, waders, a frog net
        "..............",
        ".....kkkk.....",
        "....khhhhk....",
        "...khhhhhhk...",
        ".kkTTTTTTTTkk.",
        "...kssssssk...",
        "...kskssksk..t",
        "...kssssssk.tw",
        "..kgkSSSSkgktw",
        ".kgggggggggktk",
        ".kggyggggggkt.",
        ".kgggggggggkt.",
        "..kgggggggkkt.",
        "..kTTTTTTTk.t.",
        "..kTTk.kTTk.t.",
        "..kTTk.kTTk...",
        "..kkkk.kkkk...",
        "..............",
    ],
    "leech_doctor": [        # M22: deep red hood and cloak, white apron, a jar with a leech
        "..............",
        ".....kkkk.....",
        "....kRRRRk....",
        "...kRRRRRRk...",
        "...kRkssskRk..",
        "...kRskskskk..",
        "...kRsssssk...",
        "..kRRkSSSkRk..",
        ".kRRrwwwwwrRk.",
        ".kRrrwwwwwrrk.",
        ".kRrrwwwwwrkmk",
        ".kRrrwwrwwrkok",
        "..kRrwwwwwrkrk",
        "..kRrrwwwrrkmk",
        "..kRRrrrrrRk..",
        "..kRRk.kRRk...",
        "..kkkk.kkkk...",
        "..............",
    ],
    "scarab_collector": [    # M23.1: a sand-coloured headwrap and robe, a gold scarab
                             # amulet, a jar with a golden scarab in it
        "..............",
        ".....kkkk.....",
        "....kHHHHk....",
        "...kHHHHHHk...",
        "...kHkssskHk..",
        "...kHskskskk..",
        "...kEsssssk...",
        "..kEEkSSSkEk..",
        ".keeeeeyeeeek.",
        ".keeeeyyyeeek.",
        ".keEeeeyeeekmk",
        ".keEeeeeeeekyk",
        "..keEeeeeeekmk",
        "..keEeeeeeek..",
        "..keeEEEEeek..",
        "..kEEk.kEEk...",
        "..kkkk.kkkk...",
        "..............",
    ],
    "caravan_master": [      # M23.2: an indigo turban, a black beard, a striped robe with a
                             # gold sash, and his camel stick
        "...........t..",
        ".....kkkk..t..",
        "....kBbbBk.t..",
        "...kbBbbBbkt..",
        "...kBksssBkt..",
        "...kkskskskt..",
        "....khhhhhkt..",
        "..kRRkhhkRRk..",
        ".kRrRrRrRrRrk.",
        ".kRrRrRrRrRsk.",
        ".kyyyyyyyyyyk.",
        ".kRrRrRrRrRrk.",
        "..kRrRrRrRrk..",
        "..kRrRrRrRrk..",
        "..kRRrRrRRRk..",
        "..kTTk.kTTk...",
        "..kkkk.kkkk...",
        "..............",
    ],
    "nameless_magus": [  # M23.3: a violet hooded robe, a white beard, a gold sash, his
                             # staff with its sun lens
        "...........oo.",
        ".....kkkk..oo.",
        "....kVVVVk..t.",
        "...kVvvvvVk.t.",
        "...kVkssskVkt.",
        "...kVsksksVkt.",
        "....kwwwwwk.t.",
        "..kVVkwwwkVVt.",
        ".kVvvvwwwvvVs.",
        ".kVvvvvwvvvVt.",
        ".kyyyyyyyyyyt.",
        ".kVvvvvvvvvkt.",
        "..kVvvvvvvVkt.",
        "..kVvvvvvvVkt.",
        "..kVVvvvvVVkt.",
        "..kVVVVVVVVkt.",
        "..kkkkkkkkkkt.",
        "..............",
    ],
    "runaway_apprentice": [  # M23.3: young, red-haired, a blue robe, clutching a star book
        "..............",
        ".....kkkk.....",
        "....kaaaak....",
        "...kaaaaaak...",
        "...kakssskak..",
        "...kasksksak..",
        "....kssssk....",
        "..kbbkSSkbbk..",
        ".kbbbbbbbbbbk.",
        ".kbBbbbbwwwwk.",
        ".kbBbbbbwkwwk.",
        ".kbBbbbbwwwwk.",
        "..kbBbbbbbbk..",
        "..kbBbbbbbbk..",
        "..kbbBBBBbbk..",
        "..kbbk.kbbk...",
        "..kkkk.kkkk...",
        "..............",
    ],
    "fallout_king": [  # M24.1: a hulking green ghoul-king, a skull face, a cracked
                             # reactor core glowing in his plated chest
        "..............",
        "....kkkkkk....",
        "...kGggggGk...",
        "...kgwkkwgk...",
        "...kgwkkwgk...",
        "...kGgwwgGk...",
        "..kkkGwwGkkk..",
        ".kGggMMMMggGk.",
        "kGgggMooMgggGk",
        "kGggMooooMggGk",
        "kGggMMooMMggGk",
        "kGg.kGggGk.gGk",
        "kgk.kGggGk.kgk",
        "kgk.kGggGk.kgk",
        "....kGkkGk....",
        "...kGgkkgGk...",
        "...kkkk.kkk...",
        "..............",
    ],
    "hazmat_scavenger": [  # M24.1: a yellow hazmat suit, a glass visor, a geiger counter
        "..............",
        ".....kkkk.....",
        "....kyyyyk....",
        "...kyoooooyk..",
        "...kyoooooyk..",
        "...kyyyyyyyk..",
        "....kyyyyyk...",
        "..kyykMMkyyk..",
        ".kyyyyyyyyyyk.",
        ".kyYyyyyykmmk.",
        ".kyYyyyyykmmk.",
        ".kyYyyyyyyyyk.",
        "..kyYyyyyyyk..",
        "..kyYyyyyyyk..",
        "..kyyYYYYyyk..",
        "..kMMk.kMMk...",
        "..kkkk.kkkk...",
        "..............",
    ],
    "searching_sister": [  # M24.2: a grey winter hood and cloak over blue
        "..............",
        ".....kkkk.....",
        "....kMMMMk....",
        "...kMhhhhMk...",
        "...kMksskMk...",
        "...kMskskMk...",
        "....kssssk....",
        "..kMMkMMkMMk..",
        ".kMbbbbbbbbMk.",
        ".kMbbbbbbbbMk.",
        ".kMbbbrrbbbMk.",
        ".kMbbbbbbbbMk.",
        "..kMbbbbbbMk..",
        "..kMbbbbbbMk..",
        "..kMMbbbbMMk..",
        "..kMMk.kMMk...",
        "..kkkk.kkkk...",
        "..............",
    ],
    "captive": [  # M24.2: a captive thawing out of the ice (frosty blue clothes)
        "..............",
        ".....kkkk.....",
        "....khhhhk....",
        "...khhhhhhk...",
        "...khksskhk...",
        "...khskskhk...",
        "....kssssk....",
        "..kooksskook..",
        ".koooooooooook",
        ".koOoooooooOok",
        ".koOoooooooOok",
        ".kooooooooook.",
        "..koOoooooOok.",
        "..kooooooook..",
        "..koooooooook.",
        "..kook.kook...",
        "..kkkk.kkkk...",
        "..............",
    ],
    "pawn_dealer": [  # M24.3: a shifty pawn dealer: a flat cap, a striped vest, a sack
        "..............",
        ".....kkkk.....",
        "...kkTTTTkk...",
        "....kTTTTk....",
        "...kskssksk...",
        "...ksSsssSk...",
        "....kShhSk....",
        "..kttkSSktkk..",
        ".kthththththk.",
        ".kthththththkH",
        ".kHHHHHHHHHHkH",
        ".kthththththkH",
        "..ktttttttk...",
        "..ktttttttk...",
        "..kTTTTTTTk...",
        "..kMMk.kMMk...",
        "..kkkk.kkkk...",
        "..............",
    ],
    "thrall": [  # M24.3: a pale thrall in rags
        "..............",
        ".....kkkk.....",
        "....kmmmmk....",
        "...kmrmmrmk...",
        "...kmmmmmmk...",
        "....kmmmmk....",
        "..kkkVVVVkkk..",
        ".kmkVVVVVVkmk.",
        ".kmkVVVVVVkmk.",
        ".kk.VVVVVV.kk.",
        "....VVVVVV....",
        "....kVVVVk....",
        "....kV.kVk....",
        "....kV.kVk....",
        "....kk.kkk....",
        "..............",
        "..............",
        "..............",
    ],
    "forager": [             # M26.3: a green hood, a leather jerkin, a basket on the arm
        "..............",
        ".....kkkk.....",
        "...kkGGGGkk...",
        "..kGGGGGGGGk..",
        "...kssssssk...",
        "...kskssksk...",
        "...kssSsssk...",
        "....kssssk....",
        "..khHhHhHhHk..",
        ".khHhHhHhHhHk.",
        ".kshHhHhHhHsk.",
        "..khHhHhHhHk.t",
        "..kNNNNNNNNktt",
        "..knnnnnnnnkTt",
        "..knnnkknnnk..",
        "..kTTk..kTTk..",
        "..kkkk..kkkk..",
        "..............",
    ],
    "mycologist": [          # M26.2: blonde, round spectacles, a violet coat, a glass vial
        "..............",
        "....kkkkkk....",
        "...kHHHHHHk...",
        "...kssssssk...",
        "..kmmskkmmsk..",
        "..kmwmssmwmk..",
        "...kssSsssk...",
        "....kssssk....",
        "..kvVvVvVvVk..",
        ".kvVvVvVvVvVk.",
        ".ksVvVvvVvVsk.",
        "..kVvVvVvVvk.o",
        "..kVvVvVvVvkoO",
        "..kVvVvVvVvk.t",
        "..kVVVkkVVVk.t",
        "..kTTk..kTTk..",
        "..kkkk..kkkk..",
        "..............",
    ],
    "truffle_hunter": [      # M26: a brown hat, a green coat, a truffle pig at heel
        "..............",
        "....kkkkkk....",
        "...kNNNNNNk...",
        "..kNNNNNNNNk..",
        "...kssssssk...",
        "...kskssksk...",
        "...ksSssSsk...",
        "....kssssk....",
        "..kgGgGgGgGk..",
        ".kgGgGgGgGgGk.",
        ".ksGgGgGgGgsk.",
        "..kgGgGgGgGk..",
        "..knnnnnnnnk..",
        "..knnnnnnnnk.p",
        "..knnnkknnnkpP",
        "..kTTk..kTTk.p",
        "..kkkk..kkkk..",
        "..............",
    ],
    "lumberjack": [          # M25.3: a red knit cap, a white beard, blue overalls, a saw
        "..............",
        "....kkkkkk....",
        "...kRRRRRRk...",
        "..kRRRRRRRRk..",
        "...kssssssk...",
        "...kskssksk...",
        "...kwsSsswk...",
        "...kwwwwwwk...",
        "..kbBkwwkBbk.m",
        ".kbbBwwwwBbbkm",
        ".ksbBbbbbBbskt",
        "..kbBbbbbBbkt.",
        "..kbbbbbbbbkt.",
        "..kBBBBBBBBk..",
        "..kBBBkkBBBk..",
        "..kTTk..kTTk..",
        "..kkkk..kkkk..",
        "..............",
    ],
    "forester": [            # M25.2: a green cap, a bushy beard, a red check shirt, an axe
        "..............",
        "....kkkkk..mm.",
        "...kGGGGGkmMMm",
        "..kkGGGGGkkmm.",
        "...kssssssk.t.",
        "...kskssksk.t.",
        "...khsSsshk.t.",
        "...khhhhhhk.t.",
        "..krRrRrRrRkt.",
        ".krRrRrRrRrks.",
        ".ksRrRrRrRrk..",
        "..kRrRrRrRrk..",
        "..kTTTTTTTTk..",
        "..kBBBBBBBBk..",
        "..kBBBkkBBBk..",
        "..kTTk..kTTk..",
        "..kkkk..kkkk..",
        "..............",
    ],
    "hedge_witch": [         # M25.1: a mossy green shawl, grey hair, a crooked hat, herbs
        "......kk......",
        ".....kGGk.....",
        "....kGgGGk....",
        "..kkGGGGGGkk..",
        "...kmmmmmmk...",
        "...kmskkskk...",
        "...kmsSsssk...",
        "....kssSsk....",
        "..kGgGgGgGgk..",
        ".kGgGgGgGgGGk.",
        ".kGVVVVVVVVGkg",
        ".ksVVVVVVVVskg",
        "..kVVVVVVVVkt.",
        "..kVVVVVVVVkt.",
        "..kVVVVVVVVkt.",
        "..kTTk..kTTkt.",
        "..kkkk..kkkk..",
        "..............",
    ],
    "smoke_keeper": [        # M22.2: a soot-grey hood and robe, a smoking censer on a chain
        "...........mm.",
        ".....kkkk..m..",
        "....kMMMMk....",
        "...kMMMMMMk...",
        "...kMkssskMk..",
        "...kMskskskk..",
        "...kMsssssk...",
        "..kMMkSSSkMk..",
        ".kMMmmmmmmMMk.",
        ".kMmmmmmmmmMk.",
        ".kMmmmhhmmmkm.",
        ".kMmmmmmmmmkm.",
        "..kMmmmmmmkkm.",
        "..kMmmmmmmMkyk",
        "..kMMmmmmMMktk",
        "..kMMk.kMMk.k.",
        "..kkkk.kkkk...",
        "..............",
    ],
}

# The psychedelic frogs (M17): the bog toad in each of the psychedelic hues,
# "psyfrog0".."psyfrog7" (light and dark sprite colors swapped in for its
# greens).
PSY_HUES = (("r", "R"), ("a", "A"), ("y", "Y"), ("g", "G"), ("o", "O"), ("b", "B"),
            ("v", "V"), ("p", "P"))
for _i, (_light, _dark) in enumerate(PSY_HUES):
    ART[f"psyfrog{_i}"] = [row.translate(str.maketrans({"g": _light, "G": _dark}))
                           for row in ART["toad"]]

ART_W, ART_H = 14, 18
_HIT_MIX = 0.65          # hit flash: this far toward white


def _picture(name: str, hurt: bool, look: Look | None = None) -> pygame.Surface:
    colors = palette.SPRITE_COLORS
    surf = pygame.Surface((ART_W, ART_H), pygame.SRCALPHA)
    for y, row in enumerate(dress(name, ART[name], look)):
        for x, ch in enumerate(row):
            if ch == ".":
                continue
            c = colors[ch]
            if hurt and ch != "k":
                c = tuple(round(v + (255 - v) * _HIT_MIX) for v in c)
            surf.set_at((x, y), c)
    return surf


def dressed_picture(name: str, look: Look | None = None) -> pygame.Surface:
    """A hero's picture (ART_W x ART_H art pixels, facing right) in `look`:
    for the gear screen's figure (M28.6)."""
    return _picture(name, False, look)


def _walk_frame(base: pygame.Surface, frame: int) -> pygame.Surface:
    """Frames 0 and 2: standing. Frames 1 and 3: the body hops up one pixel
    while one foot (left half of the bottom row, then the right half) stays
    planted -- a small step without drawing separate legs per character."""
    if frame % 2 == 0:
        return base
    out = pygame.Surface(base.get_size(), pygame.SRCALPHA)
    out.blit(base, (0, -1))
    rect = base.get_bounding_rect()
    bottom = rect.bottom - 1
    half = ART_W // 2
    x0, x1 = (0, half) if frame == 1 else (half, ART_W)
    out.blit(base, (x0, bottom), pygame.Rect(x0, bottom, x1 - x0, 1))
    return out


def _painter(name: str, scale: int, flip: bool, frame: int, hurt: bool,
             look: Look | None = None):
    def paint(surf, to_px):
        img = _walk_frame(_picture(name, hurt, look), frame)
        if flip:
            img = pygame.transform.flip(img, True, False)
        img = pygame.transform.scale(img, (ART_W * scale, ART_H * scale))
        x, y = to_px(-ART_W * scale / 2, -ART_H * scale / 2)
        surf.blit(img, (round(x), round(y)))
    return paint


def walk_frame(character) -> int:
    """Animation frame from distance walked (standing still: frame 0)."""
    if character.speed < 0.5:
        return 0
    return int(character.walked * config.WALK_STEPS_PER_TILE) % 4


def draw_character(bank: SpriteBank, x: float, y: float, sprite: str, scale: int,
                   facing_left: bool, frame: int, hurt: bool, pose: str = "",
                   look: Look | None = None) -> None:
    """Draw a character centred on canvas pixel (x, y). Each (sprite, look,
    facing, frame, hurt) combination is baked once and kept. A painted
    figure (render/painted.PAINTED) is drawn the same way, and can take a
    `pose`. `look`: a hero's worn gear (M28.6)."""
    fig = PAINTED.get(sprite)
    if fig is not None:
        key = f"paint:{sprite}:{pose}:{scale}:{int(facing_left)}:{frame}:{int(hurt)}"
        bank.draw(bank.static(key, painter(sprite, scale, facing_left, frame, hurt, pose),
                              fig.reach * scale), x, y)
        return
    dressed = f":{look.key}" if look is not None else ""
    key = f"char:{sprite}{dressed}:{scale}:{int(facing_left)}:{frame}:{int(hurt)}"
    reach = max(ART_W, ART_H) * scale / 2 + 1
    sprite = bank.static(key, _painter(sprite, scale, facing_left, frame, hurt, look), reach)
    bank.draw(sprite, x, y)


# A worn legendary's glint (M28.6): each slot's blinks SPARKLE_ON of every
# SPARKLE_PERIOD s, the slots a third of a period apart.
SPARKLE_PERIOD = 1.8
SPARKLE_ON = 0.16
SPARKLE_COLOR = (255, 250, 220)
_SPARKLE_PHASE = {"head": 0.0, "chest": 1 / 3, "main": 2 / 3}


def draw_sparkles(canvas: pygame.Surface, x: float, y: float, sprite: str, scale: int,
                  facing_left: bool, frame: int, look: Look | None, clock: float) -> None:
    """The glints of a hero's worn legendaries (head, chest, main hand),
    drawn over its sprite centred on canvas pixel (x, y): a bright pixel
    with a short cross round it, at render/gear_looks.SPARKLE's spot."""
    if look is None or not look.legend or sprite not in SPARKLE:
        return
    hop = 1 if frame % 2 == 1 else 0                 # the walk frame's hop (_walk_frame)
    for slot in look.legend:
        t = (clock / SPARKLE_PERIOD + _SPARKLE_PHASE[slot]) % 1.0
        if t >= SPARKLE_ON / SPARKLE_PERIOD:
            continue
        ax, ay = SPARKLE[sprite][slot]
        if facing_left:
            ax = ART_W - 1 - ax
        cx = round(x - ART_W * scale / 2 + (ax + 0.5) * scale)
        cy = round(y - ART_H * scale / 2 + (ay - hop + 0.5) * scale)
        arm = scale
        half = max(1, scale // 2)
        canvas.fill(SPARKLE_COLOR, pygame.Rect(cx - half, cy - half, 2 * half, 2 * half))
        canvas.fill(SPARKLE_COLOR, pygame.Rect(cx - arm - half, cy, 2 * (arm + half), 1))
        canvas.fill(SPARKLE_COLOR, pygame.Rect(cx, cy - arm - half, 1, 2 * (arm + half)))


def body_scale(c) -> int:
    """How big a Character is drawn: its spec's scale, a size smaller while
    Nettle's dust has it shrunk (M25.1)."""
    scale = c.spec.sprite_scale
    small = getattr(c, "shrunk", 0) > 0 or getattr(c, "dusted", 0) > 0   # (M28.5c too)
    return max(1, scale - 1) if small else scale


def draw_body(bank: SpriteBank, camera, c) -> None:
    """Draw a Character (the hero or a shooting enemy) at its world spot --
    on its mount while it rides (P6, render/mounts.py)."""
    if getattr(c, "mount", ""):
        from .mounts import draw_mounted
        draw_mounted(bank, camera, c, getattr(c, "time", 0.0))
        return
    x, y = camera.world_to_px(c.x, c.y)
    look = getattr(c, "look", None)
    frame, scale = walk_frame(c), body_scale(c)
    draw_character(bank, x, y, c.spec.sprite, scale, c.facing_left, frame, c.hurt_flash > 0,
                   look=look)
    if look is not None and look.legend:
        draw_sparkles(bank.text.display.canvas, x, y, c.spec.sprite, scale, c.facing_left,
                      frame, look, getattr(c, "time", 0.0))


def draw_feet_marks(text, bank: SpriteBank, camera, players, steps: int) -> None:
    """The feet gear's marks on the ground (M28.2c): a hero's afterimage
    (Windrunners +6, a blinking copy) and the bard's amps (Stompers +9)."""
    cw, ch = text.display.cell_w, text.display.cell_h
    for p in players:
        h = p.hero
        if (steps // 4) % 2 == 0:
            for im in h.images:
                x, y = camera.world_to_px(im.x, im.y)
                draw_character(bank, x, y, h.spec.sprite, body_scale(h), h.facing_left, 0, True,
                               look=h.look)
        for amp in h.amps:
            x, y = camera.world_to_px(amp[0], amp[1])
            text.put_px(x - 1.5 * cw, y - ch / 2, "(o)", palette.AMP, None)


def draw_chest_marks(text, camera, me, projectiles, steps: int) -> None:
    """The chest gear's marks (M28.2d): your bramble ring while it grows
    (Brambleguard +6), and where enemy shots are going (Shattercoat +3,
    a faint line CRYSTAL_CLEAR s ahead of each -- only for you)."""
    h = me.hero
    st = h.stats
    if st is None or not me.alive:
        return
    cw, ch = text.display.cell_w, text.display.cell_h
    if h.bubble > 0:                                   # (Bubble Belt, M28.5a)
        r = h.hit_radius + 0.7
        for k in range(10):
            a = steps * 0.05 + k * math.tau / 10
            x, y = camera.world_to_px(h.x + math.cos(a) * r, h.y + math.sin(a) * r * 0.8)
            text.put_px(x - cw / 2, y - ch / 2, "o" if k % 2 else ".", palette.SHOT_BOLT[0], None)
    t = h.leech_target
    if t is not None and t.alive and st.has("bloated_charm"):   # (the leechling)
        x, y = camera.world_to_px(t.x, t.y)
        wiggle = 2 if (steps // 6) % 2 else -2
        text.put_px(x + t.hit_radius * cw * 0.8, y - ch / 2 + wiggle, "e", palette.MIMIC_TONGUE[1],
                    None)
    if st.has("thorn_mail+6") and h.still_t >= config.OVERGROWTH[0]:
        r = config.OVERGROWTH[1]
        turn = steps * 0.02
        for k in range(12):
            a = turn + k * math.tau / 12
            x, y = camera.world_to_px(h.x + math.cos(a) * r, h.y + math.sin(a) * r)
            text.put_px(x - cw / 2, y - ch / 2, "*" if k % 2 else "x", palette.BRAMBLE, None)
    if st.has("glass_cannon+3"):
        canvas = text.display.canvas
        for q in projectiles:
            if not q.alive or q.spec.lob or q.hold > 0 or getattr(q.owner, "faction", None) == "player":
                continue
            ahead = q.spec.speed * q.time_scale * q.pace * config.CRYSTAL_CLEAR
            ahead = min(ahead, q.max_range - q.travelled)
            if ahead <= 0:
                continue
            x0, y0 = camera.world_to_px(q.x, q.y)
            x1, y1 = camera.world_to_px(q.x + q.dir_x * ahead, q.y + q.dir_y * ahead)
            pygame.draw.line(canvas, palette.SHOT_PATH, (round(x0), round(y0)), (round(x1), round(y1)))
