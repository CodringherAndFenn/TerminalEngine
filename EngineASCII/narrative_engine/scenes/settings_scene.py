"""
scenes/settings_scene.py -- the settings screen.

A WidgetList of rows: Monitor, Resolution, Window Mode, Scaling (grid), Master
Volume, Audio Device, and Back. Every change applies live -- display changes
call straight into the Display, audio changes into the Audio manager -- and each
change plays a blip so it's audible. Leaving (Back or Esc) writes settings.json.

Two changes resize things the layout depends on: switching the grid rebuilds
the virtual canvas, and switching monitor changes which resolutions fit. Both
set a dirty flag so the widget list is rebuilt (positions recomputed) on the
next update, preserving the focused row.
"""

from __future__ import annotations

import pygame

from engine import (
    Button,
    DisplayMode,
    GRID_PRESETS,
    OptionSelector,
    Scene,
    Slider,
    TextRenderer,
    WidgetList,
    WINDOW_MODES,
    colors,
)

from .common import draw_screen

# Grid presets in the order the selector cycles through them.
GRID_NAMES = ["ultrawide", "wide", "classic"]


class SettingsScene(Scene):
    def on_enter(self) -> None:
        self._dirty = False
        self._ui: WidgetList | None = None
        self._build()

    # --- Layout ----------------------------------------------------------

    def _build(self) -> None:
        """(Re)construct the widget rows from the current display/settings."""
        d = self.manager.display
        s = self.manager.settings
        cols, rows = d.cols, d.rows
        width = min(60, cols - 8)
        col = (cols - width) // 2
        r = max(5, rows // 2 - 7)
        step = 2
        widgets = []

        # Monitor -- disabled when there's only one display.
        monitors = d.available_monitors()
        mon_values = list(range(len(monitors)))
        monitor_sel = OptionSelector(
            col, r, width, "Monitor", mon_values,
            index=min(s.monitor, len(mon_values) - 1),
            formatter=lambda i: f"Display {i + 1} ({monitors[i][0]}x{monitors[i][1]})",
            on_change=self._on_monitor,
        )
        monitor_sel.enabled = len(mon_values) > 1
        widgets.append(monitor_sel)
        r += step

        # Resolution (windowed window size). Ensure the current value appears.
        res_values = d.available_resolutions(d.monitor)
        if tuple(s.resolution) not in res_values:
            res_values = sorted(set(res_values + [tuple(s.resolution)]))
        res_sel = OptionSelector(
            col, r, width, "Resolution", res_values,
            formatter=lambda wh: f"{wh[0]} x {wh[1]}",
            on_change=self._on_resolution,
        )
        res_sel.select_value(tuple(s.resolution))
        widgets.append(res_sel)
        r += step

        # Window mode.
        mode_sel = OptionSelector(
            col, r, width, "Window Mode", list(WINDOW_MODES),
            formatter=lambda m: m.capitalize(),
            on_change=self._on_mode,
        )
        mode_sel.select_value(s.window_mode)
        widgets.append(mode_sel)
        r += step

        # Scaling / grid preset.
        grid_sel = OptionSelector(
            col, r, width, "Scaling (grid)", GRID_NAMES,
            formatter=lambda n: f"{n.capitalize()} ({GRID_PRESETS[n][0]}x{GRID_PRESETS[n][1]})",
            on_change=self._on_grid,
        )
        grid_sel.select_value(s.grid)
        widgets.append(grid_sel)
        r += step

        # Master volume.
        widgets.append(
            Slider(col, r, width, "Master Volume", value=s.volume, on_change=self._on_volume)
        )
        r += step

        # Audio output device (None == system default, shown first).
        devices = [None] + self.manager.audio.list_devices()
        dev_sel = OptionSelector(
            col, r, width, "Audio Device", devices,
            formatter=self._format_device,
            on_change=self._on_device,
        )
        dev_sel.select_value(s.audio_device)
        widgets.append(dev_sel)
        r += step + 1

        widgets.append(Button(col, r, width, "Back", self._back))

        prev_index = self._ui.index if self._ui is not None else 0
        self._ui = WidgetList(widgets)
        self._ui.index = min(prev_index, len(widgets) - 1)

    @staticmethod
    def _format_device(dev: str | None) -> str:
        if dev is None:
            return "Default"
        return dev if len(dev) <= 16 else dev[:14] + ".."

    # --- Change handlers (live-apply) ------------------------------------

    def _on_monitor(self, index: int) -> None:
        self.manager.display.set_monitor(index)
        self.manager.settings.monitor = self.manager.display.monitor
        self.manager.audio.play_blip()
        self._dirty = True  # available resolutions depend on the monitor

    def _on_resolution(self, wh: tuple[int, int]) -> None:
        self.manager.display.set_windowed_resolution(*wh)
        self.manager.settings.resolution = tuple(wh)
        self.manager.audio.play_blip()

    def _on_mode(self, mode: str) -> None:
        self.manager.display.set_mode(DisplayMode(mode))
        self.manager.settings.window_mode = mode
        self.manager.audio.play_blip()

    def _on_grid(self, name: str) -> None:
        self.manager.display.set_grid(*GRID_PRESETS[name])
        self.manager.settings.grid = name
        self.manager.audio.play_blip()
        self._dirty = True  # canvas resized -> relayout the rows

    def _on_volume(self, v: float) -> None:
        self.manager.audio.set_volume(v)
        self.manager.settings.volume = v
        self.manager.audio.play_blip()

    def _on_device(self, dev: str | None) -> None:
        self.manager.audio.set_device(dev)
        # Record the device actually in use (a failed choice falls back).
        self.manager.settings.audio_device = self.manager.audio.device
        self.manager.audio.play_blip()

    # --- Scene hooks -----------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._back()
            return
        assert self._ui is not None
        self._ui.handle_event(event, self.manager.display)

    def update(self, dt: float) -> None:
        if self._dirty:
            self._dirty = False
            self._build()

    def draw(self, text: TextRenderer) -> None:
        cols, rows = self.manager.display.cols, self.manager.display.rows
        draw_screen(text, cols, rows, "SETTINGS")
        assert self._ui is not None
        self._ui.draw(text)
        hint = "Arrows: move & change   Enter: select   Esc: back & save"
        text.put((cols - len(hint)) // 2, rows - 2, hint, colors.GREY)

    def _back(self) -> None:
        from .menu import MenuScene  # lazy import avoids a cycle

        self.manager.settings.save()
        self.manager.switch_to(MenuScene())
