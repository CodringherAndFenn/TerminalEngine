"""
ui/logo.py -- the title logo in big block letters.

Letters are 5 x 5 pixel bitmaps; each pixel is one grid cell drawn as the
full-block glyph (synthesized by the engine, so it works with any font).
A half-row shadow under the letters gives them depth.
"""

from __future__ import annotations

from engine import TextRenderer

_FONT = {
    "A": (".###.", "#...#", "#####", "#...#", "#...#"),
    "C": (".####", "#....", "#....", "#....", ".####"),
    "D": ("####.", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "####.", "#....", "#####"),
    "I": ("#####", "..#..", "..#..", "..#..", "#####"),
    "N": ("#...#", "##..#", "#.#.#", "#..##", "#...#"),
    "R": ("####.", "#...#", "####.", "#..#.", "#...#"),
    "S": (".####", "#....", ".###.", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", ".#.#.", "..#.."),
    " ": (".....",) * 5,
}
LETTER_W = 6      # 5 cells + 1 gap
LETTER_H = 5


def word_width(word: str) -> int:
    return len(word) * LETTER_W - 1


def draw_word(text: TextRenderer, col: int, row: int, word: str, color: tuple,
              shadow: tuple | None = None) -> None:
    lit = set()
    for i, ch in enumerate(word):
        for r, line in enumerate(_FONT[ch]):
            for c, px in enumerate(line):
                if px == "#":
                    lit.add((col + i * LETTER_W + c, row + r))
    for x, y in lit:
        text.put(x, y, "█", color, None)
    if shadow is not None:
        # A half-row drop shadow under each lit cell that has nothing below.
        for x, y in lit:
            if (x, y + 1) not in lit:
                text.put(x, y + 1, "▀", shadow, None)


def draw_logo(text: TextRenderer, row: int, color: tuple, shadow: tuple) -> int:
    """ASCII over ADVENTURERS, centred; returns the row below the logo."""
    cols = text.display.cols
    for word in ("ASCII", "ADVENTURERS"):
        draw_word(text, (cols - word_width(word)) // 2, row, word, color, shadow)
        row += LETTER_H + 1
    return row
