# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running

```sh
# The game (intro → menu → settings), from inside narrative_engine/:
../.venv/bin/python main.py

# The display-layer test harness:
../.venv/bin/python demo.py
```

Both must run with `narrative_engine/` as the working directory (or on
`PYTHONPATH`) so `import engine` / `import scenes` resolve. The venv is at the
repo root. Dependency: `pygame-ce` (install with `.venv/bin/pip install pygame-ce`).

`main.py` loads `settings.json` (repo root, written by the settings screen),
builds the `Display`/`Audio` to match, and runs `IntroScene`. For headless
smoke tests set `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy`.

### Demo controls

| Key | Action |
|-----|--------|
| F11 | cycle window mode: windowed → borderless → fullscreen |
| W | cycle grid: ultrawide → classic → wide |
| SPACE | skip typewriter / replay once finished |
| T | fade to black and back |
| ESC / Q | quit |

FPS and debug info print to the console once per second.

## Architecture

The engine has one layer: a fixed-resolution virtual canvas that scales to any real window via nearest-neighbor + letterboxing. Game code addresses a character grid; it never deals with window size.

**`engine/display.py`** — `Display` owns the OS window and virtual canvas. `Display.canvas` is a pygame Surface `(cols * cell_w) × (rows * cell_h)`. `Display.present()` scales it to the window each frame, centering with pillarbox/letterbox bars. `DisplayMode` (WINDOWED / BORDERLESS / FULLSCREEN) cycles via `Display.cycle_mode()`. `Display.set_grid(cols, rows)` switches presets at runtime without changing font or cell size.

**`engine/text.py`** — `TextRenderer` draws characters one cell at a time with a `(char, fg, bg) → Surface` glyph cache. Box-drawing and block-element glyphs (`─ │ ┌ ┐ └ ┘ ├ ┤ ┬ ┴ ┼ █ ▀ ▄ ▌ ▐ ░ ▒ ▓` and double-line aliases) are synthesized procedurally — they never come from the font file — so they join seamlessly and work with any font. `Typewriter` reveals a string character-by-character over time. `Fade` draws a black alpha overlay for fade-in/out transitions.

**`engine/colors.py`** — all named colors as `(r, g, b)` tuples. Single source of truth for the palette; re-theme by editing here. `SELECT_*`/`DISABLED` are the UI widget colors.

**`engine/scene.py`** — `Scene` (base: `on_enter`/`handle_event`/`update`/`draw`/`on_exit`) and `SceneManager`, which owns the shared services (`display`, `text`, `audio`, `settings`, `fade`), runs the 60fps loop, and does fade-through transitions in `switch_to`. Scenes reach services via `self.manager`.

**`engine/ui.py`** — grid widgets with keyboard **and** mouse: `Button`, `OptionSelector` (cycles a value list), `Slider` (0–1 bar), and `WidgetList`/`Menu` containers that move focus and route mouse events. Mouse hit-testing relies entirely on `Display.window_to_cell(px, py)` (the inverse of `present()`'s scale+letterbox transform).

**`engine/settings.py`** — `Settings` dataclass (grid, window_mode, monitor, resolution, volume, audio_device) with forgiving JSON `load`/`save` to a repo-root `settings.json`. Grid names map to presets via `GRID_PRESETS`.

**`engine/audio.py`** — `Audio` wraps the pygame mixer: device enumeration (`pygame._sdl2.audio.get_audio_device_names`), volume, and a **numpy-free** synthesized "blip" (`pygame.mixer.Sound(buffer=...)`) so audio settings are testable without assets. All calls degrade to no-ops if no device opens.

**`scenes/`** — concrete scenes: `IntroScene` (fade + typewriter, auto-advances), `MenuScene`/`PlaceholderScene` (`menu.py`), `SettingsScene` (`settings_scene.py`, applies each change live and rebuilds its layout when the grid/monitor changes). `common.py` holds the shared bordered-background helper.

**`main.py`** — entry point wiring settings → Display/Audio → `SceneManager.run(IntroScene())`.

**`engine/__init__.py`** — re-exports the full public API so callers can `from engine import Display, SceneManager, Settings, ui, ...`.

## Gotchas

- **UI text must use ASCII or the synthesized box/block glyphs only.** VT323 has no arrow (`←↑→↓`) or guaranteed punctuation glyphs, so hint strings use words and selectors use `<`/`>`. The procedurally-drawn set is `─│┌┐└┘├┤┬┴┼ █▀▄▌▐ ░▒▓` (+ double-line aliases).
- **Changing the grid resizes the canvas**, which invalidates any absolute widget positions. `SettingsScene` handles this by setting a dirty flag and rebuilding its `WidgetList` on the next `update`.
- Switching the audio device quits and re-inits the mixer and rebuilds the blip; a failed device falls back to the system default.

## Grid presets

Three presets ship in `display.py`, sized for a 10×24px cell (VT323 at `font_size=24`):

| Constant | Grid | Canvas pixels | Target |
|----------|------|---------------|--------|
| `GRID_ULTRAWIDE` | 172×30 | 1720×720 | **Primary**: 2× integer scale to 3440×1440 ultrawide, zero bars |
| `GRID_WIDE` | 128×30 | 1280×720 | 16:9 |
| `GRID_CLASSIC` | 80×24 | 800×576 | ~4:3 traditional terminal |

`set_grid()` accepts any `(cols, rows)` pair; bars compensate on all screens.

## Font handling

VT323-Regular.ttf is bundled under `narrative_engine/assets/fonts/` and resolved with `pathlib` relative to the package, so there are no system-font or OS-specific paths. Cell size is derived from the font's metrics at the configured `font_size`; `cell_width`/`cell_height` can override it explicitly.
