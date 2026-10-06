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
"""

from __future__ import annotations

import pygame

from .. import config, palette
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
        "..kmmmyymmMk..",
        "..kkkkkkkkkk..",
        "...ksksskSk...",
        "..kaassssaAk..",
        "..kaaaaaaaAk..",
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
        "...kHHssSHHk..",
        "...kHkkkkkHk..",
        "...kkppppkkk..",
        "..kppwppppPk..",
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


def _picture(name: str, hurt: bool) -> pygame.Surface:
    colors = palette.SPRITE_COLORS
    surf = pygame.Surface((ART_W, ART_H), pygame.SRCALPHA)
    for y, row in enumerate(ART[name]):
        for x, ch in enumerate(row):
            if ch == ".":
                continue
            c = colors[ch]
            if hurt and ch != "k":
                c = tuple(round(v + (255 - v) * _HIT_MIX) for v in c)
            surf.set_at((x, y), c)
    return surf


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


def _painter(name: str, scale: int, flip: bool, frame: int, hurt: bool):
    def paint(surf, to_px):
        img = _walk_frame(_picture(name, hurt), frame)
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
                   facing_left: bool, frame: int, hurt: bool, pose: str = "") -> None:
    """Draw a character centred on canvas pixel (x, y). Each (sprite, facing,
    frame, hurt) combination is baked once and kept. A painted figure
    (render/painted.PAINTED) is drawn the same way, and can take a `pose`."""
    fig = PAINTED.get(sprite)
    if fig is not None:
        key = f"paint:{sprite}:{pose}:{scale}:{int(facing_left)}:{frame}:{int(hurt)}"
        bank.draw(bank.static(key, painter(sprite, scale, facing_left, frame, hurt, pose),
                              fig.reach * scale), x, y)
        return
    key = f"char:{sprite}:{scale}:{int(facing_left)}:{frame}:{int(hurt)}"
    reach = max(ART_W, ART_H) * scale / 2 + 1
    sprite = bank.static(key, _painter(sprite, scale, facing_left, frame, hurt), reach)
    bank.draw(sprite, x, y)


def body_scale(c) -> int:
    """How big a Character is drawn: its spec's scale, a size smaller while
    Nettle's dust has it shrunk (M25.1)."""
    scale = c.spec.sprite_scale
    return max(1, scale - 1) if getattr(c, "shrunk", 0) > 0 else scale


def draw_body(bank: SpriteBank, camera, c) -> None:
    """Draw a Character (the hero or a shooting enemy) at its world spot."""
    x, y = camera.world_to_px(c.x, c.y)
    draw_character(bank, x, y, c.spec.sprite, body_scale(c), c.facing_left,
                   walk_frame(c), c.hurt_flash > 0)
