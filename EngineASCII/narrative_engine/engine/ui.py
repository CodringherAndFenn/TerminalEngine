"""
ui.py -- grid widgets with keyboard *and* mouse support.

Each widget occupies one row of the character grid and knows how to draw
itself (focused or not), react to activation, and (for value widgets) adjust
left/right. A ``WidgetList`` holds a column of widgets, moves focus with the
arrow keys, routes mouse hover/clicks to the widget under the cursor, and skips
disabled rows.

Mouse support leans entirely on ``Display.window_to_cell`` to turn a window
pixel into a grid cell, so hit-testing stays correct at any window size or
letterbox.

Styling convention:
  * Buttons (menus) invert the whole row when focused -- a classic cursor bar.
  * Value rows (settings) mark focus with a ``>`` gutter and brighter ink,
    leaving the value legible instead of inverting its color.
"""

from __future__ import annotations

from typing import Callable

import pygame

from . import colors
from .display import Display
from .text import TextRenderer

# Width of the value field ("< value >") reserved on the right of a settings row.
_VALUE_FIELD = 22
# Width of a volume slider's bar, in cells.
_BAR_WIDTH = 20


class Widget:
    """One row on the grid. Subclasses override draw/activate/adjust/click."""

    def __init__(self, col: int, row: int, width: int) -> None:
        self.col = col
        self.row = row
        self.width = width
        self.enabled = True

    def hit(self, col: int, row: int) -> bool:
        """True if a grid cell falls on this (enabled) widget's row."""
        return self.enabled and row == self.row and self.col <= col < self.col + self.width

    def draw(self, text: TextRenderer, focused: bool) -> None:  # pragma: no cover
        raise NotImplementedError

    def activate(self) -> None:
        """Enter / click on the body."""

    def adjust(self, delta: int) -> None:
        """Left (-1) / Right (+1)."""

    def click(self, col: int, row: int) -> None:
        """Mouse click at a cell within the widget; defaults to activate."""
        self.activate()


class Button(Widget):
    """A labelled action. Inverts the whole row when focused."""

    def __init__(
        self,
        col: int,
        row: int,
        width: int,
        label: str,
        on_activate: Callable[[], None],
    ) -> None:
        super().__init__(col, row, width)
        self.label = label
        self.on_activate = on_activate

    def activate(self) -> None:
        self.on_activate()

    def draw(self, text: TextRenderer, focused: bool) -> None:
        line = self.label.center(self.width)
        if focused:
            text.put(self.col, self.row, line, colors.SELECT_FG, colors.SELECT_BG)
        else:
            text.put(self.col, self.row, line, colors.GREEN, colors.BACKGROUND)


class OptionSelector(Widget):
    """A label plus a value cycled with Left/Right or the ``<`` / ``>`` arrows.

    ``values`` is any list; ``formatter`` turns a value into display text.
    Cycling wraps around. An empty ``values`` list renders disabled as "N/A".
    """

    def __init__(
        self,
        col: int,
        row: int,
        width: int,
        label: str,
        values: list,
        *,
        index: int = 0,
        on_change: Callable[[object], None] | None = None,
        formatter: Callable[[object], str] = str,
    ) -> None:
        super().__init__(col, row, width)
        self.label = label
        self.values = values
        self.index = index if values and 0 <= index < len(values) else 0
        self.on_change = on_change
        self.formatter = formatter
        # Filled in by draw(), read by click() for arrow hit-testing.
        self._left_col = col
        self._right_col = col + width - 1
        if not values:
            self.enabled = False

    @property
    def value(self):
        return self.values[self.index] if self.values else None

    def select_value(self, value) -> None:
        """Move to ``value`` if present, without firing on_change."""
        if value in self.values:
            self.index = self.values.index(value)

    def adjust(self, delta: int) -> None:
        if not self.enabled or not self.values:
            return
        self.index = (self.index + delta) % len(self.values)
        if self.on_change is not None:
            self.on_change(self.values[self.index])

    def activate(self) -> None:
        self.adjust(1)

    def click(self, col: int, row: int) -> None:
        if col <= self._left_col:
            self.adjust(-1)
        else:
            self.adjust(1)

    def draw(self, text: TextRenderer, focused: bool) -> None:
        if not self.enabled:
            label_fg, value_fg, marker = colors.DISABLED, colors.DISABLED, " "
            value_str = self.formatter(self.value) if self.values else "N/A"
        else:
            label_fg = colors.WHITE if focused else colors.GREEN
            value_fg = colors.AMBER if focused else colors.AMBER_DIM
            marker = ">" if focused else " "
            value_str = self.formatter(self.value)

        text.put(self.col, self.row, marker, colors.AMBER, colors.BACKGROUND)
        text.put(self.col + 2, self.row, self.label, label_fg, colors.BACKGROUND)

        field = f"< {value_str} >"
        start = self.col + self.width - len(field)
        self._left_col = start
        self._right_col = start + len(field) - 1
        text.put(start, self.row, field, value_fg, colors.BACKGROUND)


class Slider(Widget):
    """A 0..1 value shown as a block-glyph bar. Left/Right step; click sets."""

    def __init__(
        self,
        col: int,
        row: int,
        width: int,
        label: str,
        *,
        value: float = 0.5,
        steps: int = 20,
        on_change: Callable[[float], None] | None = None,
    ) -> None:
        super().__init__(col, row, width)
        self.label = label
        self.value = max(0.0, min(1.0, value))
        self.steps = steps
        self.on_change = on_change
        self._bar_start = col + width - _BAR_WIDTH

    def _set(self, v: float) -> None:
        v = max(0.0, min(1.0, v))
        if v != self.value:
            self.value = v
            if self.on_change is not None:
                self.on_change(v)
        elif self.on_change is not None:
            # Fire even when clamped equal so a click always "blips".
            self.on_change(v)

    def adjust(self, delta: int) -> None:
        self._set(self.value + delta * (1.0 / self.steps))

    def click(self, col: int, row: int) -> None:
        if col < self._bar_start:
            return
        pos = col - self._bar_start
        self._set(pos / max(1, _BAR_WIDTH - 1))

    def draw(self, text: TextRenderer, focused: bool) -> None:
        label_fg = colors.WHITE if focused else colors.GREEN
        marker = ">" if focused else " "
        text.put(self.col, self.row, marker, colors.AMBER, colors.BACKGROUND)
        text.put(self.col + 2, self.row, self.label, label_fg, colors.BACKGROUND)

        filled = round(self.value * _BAR_WIDTH)
        pct = f"{round(self.value * 100):3d}% "
        self._bar_start = self.col + self.width - _BAR_WIDTH
        text.put(self._bar_start - len(pct), self.row, pct, colors.AMBER, colors.BACKGROUND)
        text.put(self._bar_start, self.row, "█" * filled, colors.AMBER, colors.BACKGROUND)
        text.put(
            self._bar_start + filled, self.row,
            "░" * (_BAR_WIDTH - filled), colors.GREEN_DIM, colors.BACKGROUND,
        )


class WidgetList:
    """A column of widgets with keyboard focus and mouse routing.

    Feed it events via ``handle_event(event, display)`` and draw with
    ``draw(text)``. Focus skips disabled widgets.
    """

    def __init__(self, widgets: list[Widget]) -> None:
        self.widgets = widgets
        self.index = self._first_enabled()

    def _first_enabled(self) -> int:
        for i, w in enumerate(self.widgets):
            if w.enabled:
                return i
        return 0

    @property
    def focused(self) -> Widget | None:
        return self.widgets[self.index] if self.widgets else None

    def move(self, delta: int) -> None:
        """Move focus by delta, skipping disabled widgets (no wrap)."""
        i = self.index
        for _ in range(len(self.widgets)):
            i = (i + delta) % len(self.widgets)
            if self.widgets[i].enabled:
                self.index = i
                return

    def _widget_at(self, col: int, row: int) -> int | None:
        for i, w in enumerate(self.widgets):
            if w.hit(col, row):
                return i
        return None

    def handle_event(self, event: pygame.event.Event, display: Display) -> None:
        if event.type == pygame.KEYDOWN:
            self._handle_key(event.key)
        elif event.type == pygame.MOUSEMOTION:
            cell = display.window_to_cell(*event.pos)
            if cell is not None:
                i = self._widget_at(*cell)
                if i is not None:
                    self.index = i
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            cell = display.window_to_cell(*event.pos)
            if cell is not None:
                i = self._widget_at(*cell)
                if i is not None:
                    self.index = i
                    self.widgets[i].click(*cell)

    def _handle_key(self, key: int) -> None:
        focused = self.focused
        if key in (pygame.K_UP, pygame.K_w):
            self.move(-1)
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.move(1)
        elif key in (pygame.K_LEFT, pygame.K_a):
            if focused is not None:
                focused.adjust(-1)
        elif key in (pygame.K_RIGHT, pygame.K_d):
            if focused is not None:
                focused.adjust(1)
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            if focused is not None:
                focused.activate()

    def draw(self, text: TextRenderer) -> None:
        for i, w in enumerate(self.widgets):
            w.draw(text, focused=(i == self.index and w.enabled))


class Menu(WidgetList):
    """Convenience: a vertical, horizontally-centered list of Buttons built
    from ``(label, callback)`` pairs."""

    def __init__(
        self,
        items: list[tuple[str, Callable[[], None]]],
        *,
        top_row: int,
        cols: int,
        width: int = 24,
        spacing: int = 2,
    ) -> None:
        col = (cols - width) // 2
        buttons = [
            Button(col, top_row + i * spacing, width, label, cb)
            for i, (label, cb) in enumerate(items)
        ]
        super().__init__(buttons)
