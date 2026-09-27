#!/usr/bin/env python3
"""
demo.py -- test harness for the narrative engine display layer.

Run with:  python demo.py   (from this directory)

What it exercises:
  * the fixed 80x24 virtual canvas, scaled with letterboxing to any window
  * box-drawn ASCII art, palette colors, and the typewriter effect
  * window mode cycling and live resizing
  * fade-to-black / fade-from-black transition

Controls:
  F11 .... cycle window mode (windowed -> borderless -> fullscreen -> ...)
  W ...... cycle grid preset: ultrawide (21:9) -> classic (80x24) -> wide (16:9)
  SPACE .. skip the typewriter, or replay it once finished
  T ...... fade out / fade back in
  ESC / Q  quit

FPS and debug info go to the console, not the screen.
"""

import pygame

from engine import (
    GRID_CLASSIC,
    GRID_ULTRAWIDE,
    GRID_WIDE,
    Display,
    DisplayMode,
    Fade,
    TextRenderer,
    Typewriter,
    colors,
)

# W cycles through these. Ultrawide first: it's the primary target display
# (3440x1440), and the demo starts on it.
GRID_PRESETS = [GRID_ULTRAWIDE, GRID_CLASSIC, GRID_WIDE]

# Box-drawn placeholder logo. The border characters are synthesized by the
# renderer, so they connect seamlessly cell-to-cell.
LOGO = """\
┌──────────────────────────────────────┐
│  ▓▓░░                          ░░▓▓  │
│        N A R R A T I V E             │
│            E N G I N E               │
│  ▓▓░░                          ░░▓▓  │
└──────────────────────────────────────┘"""

STORY_TEXT = (
    "The terminal hums to life. Pale green light spills\n"
    "across the desk, and a cursor blinks, patient,\n"
    "as if it has been waiting for you all along.\n"
    "\n"
    "Somewhere behind the glass, a story is loading..."
)


def draw_static_scene(text: TextRenderer) -> None:
    """Everything except the typewriter: logo, labels, key hints.

    Positions are computed from the current grid size so the scene lays
    itself out correctly on both the classic and widescreen grids.
    """
    cols, rows = text.display.cols, text.display.rows
    text.clear()

    # Logo, centered horizontally (its widest line is 40 cells).
    text.put_block((cols - 40) // 2, 1, LOGO, colors.AMBER)

    # Section label above the typewriter area.
    text.put(4, 9, "// incoming transmission", colors.GREEN_DIM)

    # A strip showing the palette and shade glyphs, for eyeballing colors.
    for i, color in enumerate([colors.GREEN, colors.AMBER, colors.WHITE, colors.RED, colors.CYAN]):
        text.put(4 + i * 5, rows - 6, "░▒▓█", color)

    # Key hints along the bottom row.
    text.put(2, rows - 2, "F11 mode   W grid   SPACE skip/replay   T fade   ESC quit", colors.GREY)


def print_grid_info(display: Display) -> None:
    print(f"[demo] canvas {display.canvas.get_size()} = "
          f"{display.cols}x{display.rows} cells of {display.cell_w}x{display.cell_h}px")


def main() -> None:
    display = Display(*GRID_PRESETS[0], font_size=24, title="Narrative Engine — display demo")
    text = TextRenderer(display)
    fade = Fade(display, duration=0.6)

    typewriter = Typewriter(STORY_TEXT, 4, 11, fg=colors.GREEN, chars_per_second=40)

    print_grid_info(display)
    print(f"[demo] mode: {display.mode.value}")

    clock = pygame.time.Clock()
    fps_timer = 0.0
    fading_out = False  # tracks whether the current fade should bounce back in
    running = True

    while running:
        # dt in seconds; tick(60) caps the frame rate at 60 fps.
        dt = clock.tick(60) / 1000.0

        # --- Events ---------------------------------------------------
        for event in pygame.event.get():
            display.handle_event(event)

            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.VIDEORESIZE:
                print(f"[demo] window resized to {event.w}x{event.h}")

            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif event.key == pygame.K_F11:
                    mode = display.cycle_mode()
                    print(f"[demo] mode: {mode.value}")
                elif event.key == pygame.K_w:
                    current = (display.cols, display.rows)
                    index = GRID_PRESETS.index(current) if current in GRID_PRESETS else -1
                    display.set_grid(*GRID_PRESETS[(index + 1) % len(GRID_PRESETS)])
                    print_grid_info(display)
                elif event.key == pygame.K_SPACE:
                    if typewriter.done:
                        typewriter.reset()
                    else:
                        typewriter.skip()
                elif event.key == pygame.K_t and not fade.active:
                    fade.start(Fade.OUT)
                    fading_out = True

        # --- Update ----------------------------------------------------
        typewriter.update(dt)
        fade.update(dt)
        # When the fade-out completes, immediately fade back in so the
        # demo shows the full round trip.
        if fading_out and not fade.active:
            fade.start(Fade.IN)
            fading_out = False

        # --- Draw (full redraw of the virtual canvas every frame) ------
        draw_static_scene(text)
        typewriter.draw(text)
        fade.draw()          # transition overlay goes on top of the scene
        display.present()    # scale to window with letterboxing and flip

        # --- Console FPS readout, once per second ----------------------
        fps_timer += dt
        if fps_timer >= 1.0:
            fps_timer = 0.0
            win_w, win_h = pygame.display.get_surface().get_size()
            print(f"[demo] {clock.get_fps():5.1f} fps | "
                  f"mode={display.mode.value} | window {win_w}x{win_h}")

    pygame.quit()


if __name__ == "__main__":
    main()
