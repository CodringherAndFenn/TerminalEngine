#!/usr/bin/env python3
"""
main.py -- game entry point.

Loads persisted settings, builds the Display and Audio to match, then runs the
scene flow starting at the intro:  Intro -> Menu -> (New Game placeholder |
Settings).

Run with:  python main.py   (from this directory)
"""

from engine import Audio, Display, DisplayMode, SceneManager, Settings
from scenes import IntroScene


def build_display(settings: Settings) -> Display:
    """Create the window/canvas sized and placed per the saved settings."""
    cols, rows = settings.grid_size()
    display = Display(
        cols, rows,
        font_size=24,
        title="Narrative Engine",
        monitor=settings.monitor,
    )
    # Apply the saved windowed size, then the window mode on top of it.
    display.set_windowed_resolution(*settings.resolution)
    if settings.window_mode != "windowed":
        display.set_mode(DisplayMode(settings.window_mode))
    return display


def main() -> None:
    settings = Settings.load()

    display = build_display(settings)

    audio = Audio()
    audio.init(device=settings.audio_device, volume=settings.volume)

    manager = SceneManager(display, settings, audio)
    manager.run(IntroScene())


if __name__ == "__main__":
    main()
