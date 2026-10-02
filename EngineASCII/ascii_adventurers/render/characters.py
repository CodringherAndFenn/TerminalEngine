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
"""

from __future__ import annotations

import pygame

from .. import config, palette
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
                   facing_left: bool, frame: int, hurt: bool) -> None:
    """Draw a character centred on canvas pixel (x, y). Each (sprite, facing,
    frame, hurt) combination is baked once and kept."""
    key = f"char:{sprite}:{scale}:{int(facing_left)}:{frame}:{int(hurt)}"
    reach = max(ART_W, ART_H) * scale / 2 + 1
    sprite = bank.static(key, _painter(sprite, scale, facing_left, frame, hurt), reach)
    bank.draw(sprite, x, y)


def draw_body(bank: SpriteBank, camera, c) -> None:
    """Draw a Character (the hero or a shooting enemy) at its world spot."""
    x, y = camera.world_to_px(c.x, c.y)
    draw_character(bank, x, y, c.spec.sprite, c.spec.sprite_scale, c.facing_left,
                   walk_frame(c), c.hurt_flash > 0)
