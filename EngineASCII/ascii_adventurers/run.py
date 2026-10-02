#!/usr/bin/env python3
"""
run.py -- AsciiAdventurers launcher.

    ascii_adventurers/.venv/bin/python ascii_adventurers/run.py     (from anywhere)
    ... run.py --ghosts 2      debug: two bot players roam the island too
    ... run.py --dev           developer mode: max loot, L levels up (see App)

Wires the game onto the engine without modifying it:
  1. Redirects Python's bytecode cache into ascii_adventurers/.cache/. The
     engine's __pycache__ files are tracked in git, so letting Python rewrite
     them would leave changes outside this folder.
  2. Puts narrative_engine/ (for `import engine`) and the project root (for
     `import ascii_adventurers`) on sys.path.
  3. Loads the player's own settings, records and guild (loot, upgrades)
     from ascii_adventurers/save/
     (created on first save; defaults work on any machine), builds the
     Display/Audio/SceneManager from them and opens the title screen. The
     engine's settings.json is not used.
"""

import argparse
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent          # .../EngineASCII/ascii_adventurers
PROJECT_ROOT = HERE.parent                      # .../EngineASCII

if not getattr(sys, "frozen", False):
    # Running from source. (A packaged build -- see packaging/ -- carries
    # its modules precompiled and already importable.)
    # Must happen before any other import that might compile a module.
    sys.pycache_prefix = str(HERE / ".cache" / "pycache")

    # Drop this script's own directory from the path: our subpackage names
    # (e.g. `scenes`) would otherwise shadow top-level modules of the same name.
    if sys.path and Path(sys.path[0]).resolve() == HERE:
        sys.path.pop(0)
    sys.path.insert(0, str(PROJECT_ROOT / "narrative_engine"))
    sys.path.insert(0, str(PROJECT_ROOT))

import pygame  # noqa: E402

from engine import Audio, Display, DisplayMode, SceneManager  # noqa: E402

from ascii_adventurers import config  # noqa: E402
from ascii_adventurers.app import App  # noqa: E402
from ascii_adventurers.engine_ext.screen import apply_window, fit_grid_to_monitor  # noqa: E402
from ascii_adventurers.meta.guild import Guild  # noqa: E402
from ascii_adventurers.meta.records import Records  # noqa: E402
from ascii_adventurers.meta.settings import GameSettings  # noqa: E402
from ascii_adventurers.scenes.title import TitleScene  # noqa: E402


def build_display(settings: GameSettings) -> Display:
    """Create the window/canvas from the player's settings, fitted to their
    screen."""
    display = Display(
        config.MIN_GRID_COLS, config.GRID_ROWS,
        font_size=24,
        title=config.WINDOW_TITLE,
        monitor=settings.monitor,
        # No vsync on SDL's headless "dummy" driver: it has no real renderer,
        # and SDL intermittently crashes (bus error) when it rebuilds a vsync
        # window there. Headless runs have no screen to sync to anyway.
        vsync=settings.vsync and os.environ.get("SDL_VIDEODRIVER") != "dummy",
    )
    # Grid shaped like the monitor, then the window (windowed: the player's
    # size, or fitted to the screen) or grid (borderless/fullscreen) fitted
    # so there are no bars.
    fit_grid_to_monitor(display)
    if settings.window_mode != "windowed":
        display.set_mode(DisplayMode(settings.window_mode))
    apply_window(display, settings.window_size)
    return display


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AsciiAdventurers")
    parser.add_argument("--ghosts", type=int, default=0, metavar="N",
                        help="debug: add N bot players that roam the island on their own "
                             "(F10 in game switches the view between players)")
    parser.add_argument("--smoke", type=float, default=0.0, metavar="SECONDS",
                        help="test: start a run straight away, play SECONDS without input, "
                             "quit and report (checks a build really works); saves nothing")
    parser.add_argument("--boss", metavar="KEY", default=None,
                        help="test: make every run use the quest of this boss in its biome "
                             "(e.g. froggy, leech_swarm, proboscia) instead of the seed's pick")
    parser.add_argument("--dev", action="store_true",
                        help="developer mode: the guild purse is full (nothing bought is "
                             "saved) and L levels you up in a run; records aren't saved")
    return parser.parse_args(argv)


def force_boss(boss: str | None) -> None:
    """--boss: the quest leading to that boss replaces its biome's pick."""
    if not boss:
        return
    from ascii_adventurers import config
    quest = next((k for k, q in config.QUESTS.items() if q.boss == boss), None)
    if quest is None:
        sys.exit(f"--boss: no quest leads to {boss!r} "
                 f"(try: {', '.join(sorted({q.boss for q in config.QUESTS.values()}))})")
    config.QUEST_OVERRIDE[config.QUESTS[quest].biome] = quest


def main() -> None:
    args = parse_args(sys.argv[1:])
    force_boss(args.boss)
    if args.smoke > 0:
        sys.exit(smoke(args))
    # The game's own settings and records (ascii_adventurers/save/). The
    # engine's settings.json is never read: it belongs to the engine demo.
    settings = GameSettings.load()
    display = build_display(settings)
    audio = Audio()
    # None (the default) follows the OS's default output, so plugging in
    # headphones or switching output in the system settings just works. A
    # device the player picked that isn't there falls back to the default.
    audio.init(device=settings.audio_device, volume=settings.volume)
    if not audio.available and settings.audio_device is not None:
        audio.init(device=None, volume=settings.volume)
    manager = SceneManager(display, settings, audio)
    manager.app = App(audio, settings, Records.load(), ghosts=max(0, min(3, args.ghosts)),
                      guild=Guild.load(), dev=args.dev)
    if getattr(manager.app.guild, "migrated", False):
        manager.app.save_guild()          # retired upgrades refunded: keep it that way
    manager.run(TitleScene())


def smoke(args: argparse.Namespace) -> int:
    """Play a run for a while with default settings, touching no save files;
    exit code 0 if the game ran and nothing went wrong."""
    import time

    from ascii_adventurers.scenes.game import GameScene

    settings = GameSettings()
    display = build_display(settings)
    audio = Audio()
    audio.init(device=None, volume=0.0)
    manager = SceneManager(display, settings, audio)
    manager.app = App(audio, settings, Records(), persist=False,
                      ghosts=max(0, min(3, args.ghosts)))
    scene = GameScene()
    pygame.time.set_timer(pygame.QUIT, int(args.smoke * 1000), loops=1)
    started = time.perf_counter()
    manager.run(scene)
    wall = time.perf_counter() - started
    print(f"smoke ok: {scene.steps} steps ({scene.steps / config.SIM_HZ:.1f} s of game) "
          f"in {wall:.1f} s, {len(scene.players)} player(s), {len(scene.enemies)} enemies "
          f"awake, {getattr(scene.world, 'loaded_chunks', 0)} chunks loaded")
    return 0 if scene.steps > 0 else 1


if __name__ == "__main__":
    main()
