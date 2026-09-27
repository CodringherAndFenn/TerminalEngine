# Narrative Engine — display layer

Retro terminal-style display foundation for a text-heavy narrative game.
Everything renders to a fixed-resolution character-grid canvas (default
80x24), which is scaled each frame to the real window with nearest-neighbor
filtering and letterbox/pillarbox bars — so the game looks identical at any
window size or aspect ratio.

## Setup & run

```sh
python3 -m venv .venv
.venv/bin/pip install pygame-ce

cd narrative_engine
../.venv/bin/python demo.py
```

(Or activate the venv first and just run `python demo.py`.)

### Demo controls

| Key   | Action                                                 |
|-------|--------------------------------------------------------|
| F11   | cycle window mode: windowed → borderless → fullscreen  |
| W     | cycle grid: ultrawide (21:9) → classic → wide (16:9)   |
| SPACE | skip typewriter / replay once finished                 |
| T     | fade to black, then back in                            |
| ESC/Q | quit                                                   |

FPS and debug info print to the console once per second.

## Layout

```
narrative_engine/
  engine/
    display.py   # window modes, virtual canvas, scaling/letterboxing
    text.py      # grid text renderer, ASCII art, typewriter, fade
    colors.py    # named terminal palette (theme in one place)
  assets/fonts/  # bundled VT323 (SIL OFL — license included)
  demo.py        # test harness
```

## Notes

- **Fonts are bundled** (`assets/fonts/`), resolved with `pathlib` relative
  to the package — no system fonts or OS-specific paths, so it runs the
  same on Linux and Windows.
- VT323 lacks Unicode box-drawing/block glyphs, so the renderer draws
  `─ │ ┌ ┐ └ ┘ ├ ┤ ┬ ┴ ┼` (and `═ ║ ╔ …` as single-line aliases) plus
  `█ ▀ ▄ ▌ ▐ ░ ▒ ▓` **procedurally**, spanning the full cell so borders
  join seamlessly — this works with any font you swap in.
- Cell size is derived from the font's metrics at the configured
  `font_size`, or can be overridden explicitly via `cell_width`/`cell_height`.
- Three grid presets ship in `engine.display`, sized so the default
  10×24px cell hits exact aspect ratios:
  - `GRID_ULTRAWIDE` (172×30 → 1720×720) — **the primary target**: exactly
    43:18, scales 2× pixel-perfect to a 3440×1440 ultrawide (integer
    scale, zero bars)
  - `GRID_WIDE` (128×30 → 1280×720) — exactly 16:9
  - `GRID_CLASSIC` (80×24 → 800×576) — ~4:3 traditional terminal

  `Display.set_grid(cols, rows)` switches grids at runtime; any other size
  works too, letterboxing keeps it correct on every screen.
