"""
ui/settings_panel.py -- the settings box, used from the title screen and
from the pause menu.

Every change applies at once and is saved straight away (save/settings.json
via the App), except vsync, which the engine only sets when the window is
created: it's marked "after restart" until the next start.

Display changes can reshape the grid (the game fits its columns to the
screen), so the panel re-lays itself out whenever the grid size changes.
"""

from __future__ import annotations

from typing import Callable

import pygame

from engine import Button, DisplayMode, OptionSelector, Slider, TextRenderer, WidgetList, colors

from ..app import app_of
from ..engine_ext.screen import apply_window, fit_grid_to_monitor
from ..meta.settings import WINDOW_MODES
from .frame import center, draw_box

WIDTH = 64
HINT = "Up/Down: choose   Left/Right: change   Esc: back"


def _on_off(v: bool) -> str:
    return "On" if v else "Off"


class SettingsPanel:
    def __init__(self, manager, on_back: Callable[[], None]) -> None:
        self.manager = manager
        self.app = app_of(manager)
        self.on_back = on_back
        self._ui: WidgetList | None = None
        self._shape = None

    # --- Layout ---------------------------------------------------------------------

    def _layout(self) -> tuple[int, int, int, int]:
        d = self.manager.display
        width = min(WIDTH, d.cols - 4)
        height = 22
        return (d.cols - width) // 2, max(0, (d.rows - height) // 2), width, height

    def _build(self) -> None:
        d = self.manager.display
        s = self.app.settings
        left, top, width, _ = self._layout()
        col, w = left + 3, width - 6
        r = top + 2
        widgets = []

        def row(widget):
            nonlocal r
            widgets.append(widget)
            r += 2

        row(OptionSelector(col, r, w, "Window mode", list(WINDOW_MODES),
                           index=WINDOW_MODES.index(d.mode.value),
                           formatter=str.capitalize, on_change=self._on_mode))
        monitors = d.available_monitors()
        mon = OptionSelector(col, r, w, "Monitor", list(range(len(monitors))),
                             index=min(d.monitor, len(monitors) - 1),
                             formatter=lambda i: f"{i + 1}: {monitors[i][0]}x{monitors[i][1]}",
                             on_change=self._on_monitor)
        mon.enabled = len(monitors) > 1
        row(mon)
        sizes = [None] + d.available_resolutions(d.monitor)
        if s.window_size is not None and tuple(s.window_size) not in sizes:
            sizes.append(tuple(s.window_size))
        size_sel = OptionSelector(col, r, w, "Window size", sizes,
                                  formatter=lambda v: "Fit to screen" if v is None else f"{v[0]} x {v[1]}",
                                  on_change=self._on_size)
        size_sel.select_value(None if s.window_size is None else tuple(s.window_size))
        size_sel.enabled = d.mode is DisplayMode.WINDOWED
        row(size_sel)
        row(OptionSelector(col, r, w, "Vsync", [True, False], index=0 if s.vsync else 1,
                           formatter=lambda v: _on_off(v) + ("  (after restart)" if v != self.app.vsync_at_start else ""),
                           on_change=self._on_vsync))
        row(Slider(col, r, w, "Master volume", value=s.volume, on_change=self._on_volume))
        row(Slider(col, r, w, "Effects volume", value=s.sfx_volume, on_change=self._on_sfx))
        devices = [None] + self.manager.audio.list_devices()
        dev = OptionSelector(col, r, w, "Audio output", devices,
                             formatter=lambda v: "System default" if v is None else
                             (v if len(v) <= 24 else v[:22] + ".."),
                             on_change=self._on_device)
        dev.select_value(s.audio_device)
        row(dev)
        row(OptionSelector(col, r, w, "Show FPS", [True, False], index=0 if s.show_fps else 1,
                           formatter=_on_off, on_change=self._on_fps))
        widgets.append(Button(col, r, w, "Back", self.on_back))

        prev = self._ui.index if self._ui is not None else 0
        self._ui = WidgetList(widgets)
        self._ui.index = min(prev, len(widgets) - 1)
        self._shape = (d.cols, d.rows, d.monitor, d.mode)

    def _ensure(self) -> WidgetList:
        d = self.manager.display
        if self._ui is None or self._shape != (d.cols, d.rows, d.monitor, d.mode):
            self._build()
        return self._ui

    # --- Changes (applied live, saved at once) --------------------------------------

    def _changed(self) -> None:
        self.app.save_settings()
        self.manager.audio.play_blip()

    def _on_mode(self, mode: str) -> None:
        d = self.manager.display
        d.set_mode(DisplayMode(mode))
        apply_window(d, self.app.settings.window_size)
        self.app.settings.window_mode = mode
        self._changed()

    def _on_monitor(self, index: int) -> None:
        d = self.manager.display
        d.set_monitor(index)
        fit_grid_to_monitor(d)
        # A size picked for the old monitor may not fit the new one.
        self.app.settings.window_size = None
        apply_window(d, None)
        self.app.settings.monitor = d.monitor
        self._changed()

    def _on_size(self, size) -> None:
        self.app.settings.window_size = size
        apply_window(self.manager.display, size)
        self._changed()

    def _on_vsync(self, on: bool) -> None:
        self.app.settings.vsync = on
        self._changed()

    def _on_volume(self, v: float) -> None:
        self.manager.audio.set_volume(v)
        self.app.settings.volume = v
        self._changed()

    def _on_sfx(self, v: float) -> None:
        self.app.settings.sfx_volume = v
        self.app.sfx.volume = v
        self.app.save_settings()
        self.app.sfx.play("hit")         # hear the new effects level

    def _on_device(self, dev: str | None) -> None:
        audio = self.manager.audio
        audio.set_device(dev)
        # A device that won't open falls back to the default: save what's in use.
        self.app.settings.audio_device = audio.device
        self.app.sfx.rebuild()
        self._changed()

    def _on_fps(self, on: bool) -> None:
        self.app.settings.show_fps = on
        self._changed()

    # --- Events / drawing -------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.on_back()
            return
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER,
                                                          pygame.K_SPACE):
            self.manager.audio.play_blip()
        self._ensure().handle_event(event, self.manager.display)

    def draw(self, text: TextRenderer) -> None:
        ui = self._ensure()
        left, top, width, height = self._layout()
        draw_box(text, left, top, width, height, colors.GREEN_DIM, "SETTINGS")
        ui.draw(text)
        center(text, top + height - 2, HINT, colors.GREY, left, width)
