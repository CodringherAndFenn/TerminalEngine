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
  3. Loads the engine's settings.json READ-ONLY for window/grid/volume (the
     game never writes it) and builds the Display/Audio/SceneManager the way
     the engine's own main.py does -- except audio, which always uses the
     OS default output device.
"""

import os
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
from terminal_tank.engine_ext.screen import fit_grid_to_monitor, fit_grid_to_window  # noqa: E402
from terminal_tank.scenes.game import GameScene  # noqa: E402


def build_display(settings: Settings) -> Display:
    """Create the window/canvas, fitted to the player's screen."""
    display = Display(
        config.MIN_GRID_COLS, config.GRID_ROWS,
        font_size=24,
        title=config.WINDOW_TITLE,
        monitor=settings.monitor,
        # No vsync on SDL's headless "dummy" driver: it has no real renderer,
        # and SDL intermittently crashes (bus error) when it rebuilds a vsync
        # window there. Headless runs have no screen to sync to anyway.
        vsync=config.VSYNC and os.environ.get("SDL_VIDEODRIVER") != "dummy",
    )
    # Size everything to *this* screen instead of the saved grid preset and
    # windowed resolution: grid shaped like the monitor, then the window
    # (windowed) or grid (borderless/fullscreen) fitted so there are no bars.
    fit_grid_to_monitor(display)
    if settings.window_mode != "windowed":
        display.set_mode(DisplayMode(settings.window_mode))
    fit_grid_to_window(display)
    return display


def main() -> None:
    settings = Settings.load()  # read-only: never call settings.save() here
    display = build_display(settings)
    audio = Audio()
    # Always play on the OS's default output (device=None) rather than a
    # device name saved in settings.json: players' machines have their own
    # devices, and following the OS default means plugging in headphones or
    # switching output in the system settings just works.
    audio.init(device=None, volume=settings.volume)
    SceneManager(display, settings, audio).run(GameScene())


if __name__ == "__main__":
    main()
