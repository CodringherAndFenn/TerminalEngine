"""
render/glyphs.py -- text strings pre-rendered to images, for batched drawing.

The engine draws text one character per put_px()/put() call, which is fine
for menus but adds up to thousands of Python calls a frame for terrain,
shots and effects. GlyphImages renders a (string, fg, bg) once into its own
Surface -- through the engine's put_px itself, so the pixels are exactly
what put_px would draw (font, synthesized block glyphs, custom glyphs) --
and callers blit those images, many at a time with Surface.fblits.

bg=None gives a transparent image, like put_px(..., bg=None).

Keep the set of strings and colors fixed (as with the engine's own glyph
cache): images are never evicted.
"""

from __future__ import annotations

import weakref

import pygame

from engine import TextRenderer


class GlyphImages:
    def __init__(self, text: TextRenderer) -> None:
        self.text = text
        self.cell = (text.display.cell_w, text.display.cell_h)
        self._images: dict[tuple[str, tuple, tuple | None], pygame.Surface] = {}

    def get(self, s: str, fg: tuple, bg: tuple | None = None) -> pygame.Surface:
        key = (s, fg, bg)
        img = self._images.get(key)
        if img is None:
            display = self.text.display
            size = (len(s) * display.cell_w, display.cell_h)
            img = pygame.Surface(size, pygame.SRCALPHA) if bg is None else pygame.Surface(size)
            # Point the engine's canvas at this image for one put_px call.
            canvas = display.canvas
            display.canvas = img
            try:
                self.text.put_px(0, 0, s, fg, bg)
            finally:
                display.canvas = canvas
            self._images[key] = img
        return img

    def clear(self) -> None:
        self._images.clear()

    def __len__(self) -> int:
        return len(self._images)


_shared: GlyphImages | None = None


def images_for(text: TextRenderer) -> GlyphImages:
    """The GlyphImages shared by everything drawing with this renderer
    (rebuilt if the renderer or the cell size changes)."""
    global _shared
    d = text.display
    cell = (d.cell_w, d.cell_h)
    if _shared is None or _shared.text is not text or _shared.cell != cell:
        _shared = GlyphImages(text)
    return _shared


# --- The loot icon -----------------------------------------------------------------------
# Loot isn't coins: it's rune shards, a glowing crystal splinter with a
# golden rune in it. One custom glyph (engine register_glyph, a Private
# Use Area character), so it can sit in any text: the HUD, menus, effects.
LOOT = ""
_SHARD = ("..L..",
          ".LlL.",
          "LlrlL",
          "LlrlD",
          "LlrlD",
          ".LlD.",
          "..D..")
_registered: "weakref.WeakSet[TextRenderer]" = weakref.WeakSet()


def _paint_shard(cell: pygame.Surface, fg) -> None:
    from .. import palette
    colors = {"L": palette.LOOT_LIGHT, "l": palette.LOOT, "D": palette.LOOT_DARK,
              "r": palette.LOOT_RUNE}
    w, h = cell.get_size()
    px = max(1, min(w // len(_SHARD[0]), h // len(_SHARD)))
    x0 = (w - px * len(_SHARD[0])) // 2
    y0 = (h - px * len(_SHARD)) // 2
    for y, row in enumerate(_SHARD):
        for x, ch in enumerate(row):
            if ch != ".":
                cell.fill(colors[ch], (x0 + x * px, y0 + y * px, px, px))


def loot_glyph(text: TextRenderer) -> str:
    """The loot icon's character, registered on this renderer if needed."""
    register = getattr(text, "register_glyph", None)    # (test recorders have none)
    if register is not None and text not in _registered:
        register(LOOT, _paint_shard)
        _registered.add(text)
    return LOOT


# --- The music note (M19: Sheet Music's notes) -------------------------------------------
# VT323 has no note symbol, so it's painted: an eighth note in the glyph's
# own colour (fg), so one glyph serves every shade.
NOTE = ""
_NOTE = ("...XX.",
         "...XXX",
         "...X.X",
         "...X..",
         "...X..",
         ".XXX..",
         "XXXX..",
         ".XX...")
_notes: "weakref.WeakSet[TextRenderer]" = weakref.WeakSet()


def _paint_note(cell: pygame.Surface, fg) -> None:
    w, h = cell.get_size()
    px = max(1, min(w // len(_NOTE[0]), h // len(_NOTE)))
    x0 = (w - px * len(_NOTE[0])) // 2
    y0 = (h - px * len(_NOTE)) // 2
    for y, row in enumerate(_NOTE):
        for x, ch in enumerate(row):
            if ch == "X":
                cell.fill(fg, (x0 + x * px, y0 + y * px, px, px))


def note_glyph(text: TextRenderer) -> str:
    """The note's character, registered on this renderer if needed."""
    register = getattr(text, "register_glyph", None)
    if register is not None and text not in _notes:
        register(NOTE, _paint_note)
        _notes.add(text)
    return NOTE
