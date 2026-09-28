#!/usr/bin/env python3
"""
run.py -- Terminal Tank launcher.

    terminal_tank/.venv/bin/python terminal_tank/run.py     (from anywhere)

Wires the game onto the engine without modifying it:
  1. Redirects Python's bytecode cache into terminal_tank/.cache/. The
     engine's __pycache__ files are tracked in git, so letting Python rewrite
     them would leave changes outside this folder.
  2. Puts narrative_engine/ (for `import engine`) and the project root (for
     `import terminal_tank`) on sys.path.
  3. Loads the engine's settings.json READ-ONLY (so the window matches your
     display preferences; the game never writes it) and builds the
     Display/Audio/SceneManager exactly as the engine's own main.py does.
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent          # .../EngineASCII/terminal_tank
PROJECT_ROOT = HERE.parent                      # .../EngineASCII

# Must happen before any other import that might compile a module.
sys.pycache_prefix = str(HERE / ".cache" / "pycache")

# Drop this script's own directory from the path: our subpackage names
# (e.g. `scenes`) would otherwise shadow top-level modules of the same name.
if sys.path and Path(sys.path[0]).resolve() == HERE:
    sys.path.pop(0)
sys.path.insert(0, str(PROJECT_ROOT / "narrative_engine"))
sys.path.insert(0, str(PROJECT_ROOT))

from engine import Audio, Display, DisplayMode, SceneManager, Settings  # noqa: E402

from terminal_tank import config  # noqa: E402
from terminal_tank.scenes.game import GameScene  # noqa: E402


def build_display(settings: Settings) -> Display:
    """Create the window/canvas per the engine's saved settings."""
    cols, rows = settings.grid_size()
    display = Display(
        cols, rows,
        font_size=24,
        title=config.WINDOW_TITLE,
        monitor=settings.monitor,
        vsync=config.VSYNC,
    )
    display.set_windowed_resolution(*settings.resolution)
    if settings.window_mode != "windowed":
        display.set_mode(DisplayMode(settings.window_mode))
    return display


def main() -> None:
    settings = Settings.load()  # read-only: never call settings.save() here
    display = build_display(settings)
    audio = Audio()
    audio.init(device=settings.audio_device, volume=settings.volume)
    SceneManager(display, settings, audio).run(GameScene())


if __name__ == "__main__":
    main()
