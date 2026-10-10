"""
ui/overlays.py -- boxes drawn over the game: the pause menu (ESC) and the
game-over screen with the run's stats and the player's records.

Both are a framed box with engine Buttons in a WidgetList (keyboard and
mouse), re-laid out whenever the grid size changes.
"""

from __future__ import annotations

from collections import Counter
from typing import Callable

import pygame

from engine import Button, TextRenderer, WidgetList, colors

from .. import config, palette
from ..app import app_of
from ..meta.records import Records
from ..meta.run_stats import RunStats, format_time
from ..render.glyphs import loot_glyph
from ..world import biomes as biomes_mod
from .frame import center, draw_box

_ENTER = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)

# What players call each biome (the haunted forest is "forest" inside).
_BIOME_TITLES = {b.name: b.title for b in biomes_mod.BY_ID}


class _Box:
    """A centred box of `height` rows with buttons stacked from `button_row`
    (relative to the box top), two rows apart."""

    width = 44
    height = 14
    button_row = 4

    def __init__(self, manager, buttons: list[tuple[str, Callable[[], None]]]) -> None:
        self.manager = manager
        self.buttons = buttons
        self._ui: WidgetList | None = None
        self._shape = None

    def geometry(self) -> tuple[int, int, int, int]:
        d = self.manager.display
        view_rows = d.rows - config.HUD_ROWS    # above any HUD rows
        width = min(self.width, d.cols - 4)
        return (d.cols - width) // 2, max(0, (view_rows - self.height) // 2), width, self.height

    def ui(self) -> WidgetList:
        d = self.manager.display
        if self._ui is None or self._shape != (d.cols, d.rows):
            left, top, width, _ = self.geometry()
            bw = min(30, width - 6)
            col = left + (width - bw) // 2
            index = self._ui.index if self._ui is not None else 0
            self._ui = WidgetList([Button(col, top + self.button_row + 2 * i, bw, label, cb)
                                   for i, (label, cb) in enumerate(self.buttons)])
            self._ui.index = index
            self._shape = (d.cols, d.rows)
        return self._ui

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key in _ENTER:
            app_of(self.manager).ui_sound()
        self.ui().handle_event(event, self.manager.display)


class PauseMenu(_Box):
    height = 14
    width = 52

    def __init__(self, manager, stats: RunStats, *, resume, settings, abandon, quit_game,
                 details=None) -> None:
        super().__init__(manager, [("Resume", resume), ("Settings", settings),
                                   ("Abandon run", abandon), ("Quit game", quit_game)])
        self.stats = stats
        self.details = details        # () -> str: where you are (biome, distance, seed)

    def draw(self, text: TextRenderer) -> None:
        left, top, width, height = self.geometry()
        draw_box(text, left, top, width, height, colors.GREEN_DIM, "PAUSED")
        s = self.stats
        info = f"{s.hero.upper()}   {format_time(s.time)}   kills {s.total_kills}"
        center(text, top + 1, info, colors.WHITE, left, width)
        if self.details is not None:
            center(text, top + 2, self.details(), colors.GREY, left, width)
        self.ui().draw(text)
        center(text, top + height - 2, "Esc: resume", colors.GREY, left, width)


class GameOverPanel(_Box):
    width = 76
    height = 25
    button_row = 15

    def __init__(self, manager, stats: RunStats, records: Records, broken: set[str], *,
                 again, change_hero, title, guild_hall=None, purse: int | None = None) -> None:
        buttons = [("Go again  (R)", again)]
        if guild_hall is not None:
            buttons.append(("Guild Hall", guild_hall))
        buttons += [("Change hero", change_hero), ("Title screen", title)]
        super().__init__(manager, buttons)
        self.purse = purse            # the guild's loot after this run was banked
        self.stats = stats
        self.records = records
        self.broken = broken

    def _row(self, text, row, left, label, value, record: str | None) -> None:
        text.put(left + 4, row, f"{label:<22}", colors.GREEN)
        text.put(left + 26, row, value, colors.WHITE)
        if record in self.broken:
            text.put(left + 44, row, "NEW RECORD!", palette.RECORD)

    def draw(self, text: TextRenderer) -> None:
        left, top, width, height = self.geometry()
        draw_box(text, left, top, width, height, colors.RED, "YOU HAVE FALLEN", colors.RED)
        s, rec = self.stats, self.records
        island = f"island {s.seed}" if s.seed is not None else "test map"
        center(text, top + 2, f"{s.hero.upper()} on {island}, {config.DIFFICULTIES[s.difficulty]}",
               colors.AMBER, left, width)
        biomes = ", ".join(_BIOME_TITLES.get(b, b) for b in s.biomes) if s.biomes else "-"
        self._row(text, top + 4, left, "Time survived", format_time(s.time), "longest_time")
        self._row(text, top + 5, left, "Enemies defeated", str(s.total_kills), "most_kills")
        self._row(text, top + 6, left, "Furthest from start", f"{s.furthest:.0f} tiles", "furthest")
        self._row(text, top + 7, left, "Biomes found", str(len(s.biomes)), "most_biomes")
        text.put(left + 4, top + 9, _fit("Biomes: " + biomes, width - 8), colors.GREY)
        kills = ", ".join(f"{n} {name}" for name, n in s.kills.most_common())
        text.put(left + 4, top + 10, _fit("Defeated: " + (kills or "nobody"), width - 8), colors.GREY)
        taken = Counter(s.cards)
        cards = ", ".join(config.CARDS[k].name + (f" x{n}" if n > 1 else "")
                          for k, n in taken.items() if k in config.CARDS)
        text.put(left + 4, top + 11, _fit("Cards: " + (cards or "none"), width - 8), colors.GREY)
        best = (f"Best: {format_time(rec.longest_time)}   {rec.most_kills} kills   "
                f"{rec.furthest:.0f} tiles   {rec.most_biomes} biomes   ({rec.runs} runs)")
        center(text, top + 12, _fit(best, width - 4), colors.AMBER_DIM, left, width)
        loot = f"Loot found: {loot_glyph(text)} {int(s.loot)} (kept)"
        if self.purse is not None:
            loot += f"    guild purse: {loot_glyph(text)} {self.purse}"
        center(text, top + 13, loot, palette.LOOT_TEXT, left, width)
        self.ui().draw(text)
        center(text, top + height - 2, "R: go again", colors.GREY, left, width)


def _fit(s: str, width: int) -> str:
    return s if len(s) <= width else s[: width - 2] + ".."
