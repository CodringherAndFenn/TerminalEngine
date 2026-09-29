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
