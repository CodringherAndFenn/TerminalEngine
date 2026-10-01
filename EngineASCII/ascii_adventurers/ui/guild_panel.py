"""
ui/guild_panel.py -- the Guild Hall's shops: a framed list of things to
buy with loot, opened by talking to one of the guild's people.

  "guild"  the guildmaster: upgrades every hero shares;
  "hero"   the trainer: one hero's own upgrades (Left / Right: which hero);
  "cards"  the archivist: cards to add to the offer pool.

Up / Down (or the mouse) choose a row, Enter or a click buys it; Esc
closes (the scene handles that). Each row: name, level pips, what a level
does, and the price (dim when you can't afford it; MAX / OWNED once
there's nothing left to buy). The purse sits in the top-right corner.
Buying calls `on_buy(ok)` so the scene can play a sound and save.
"""

from __future__ import annotations

import textwrap
from typing import Callable

import pygame

from engine import TextRenderer, colors

from .. import config, palette
from ..meta.guild import Guild, card_price
from ..players.cards import card_text, rarities_of
from ..render.glyphs import loot_glyph
from .frame import center, draw_box

TITLES = {"guild": "THE GUILDMASTER", "hero": "THE TRAINER", "cards": "THE ARCHIVE"}
BLURBS = {"guild": "Upgrades for every adventurer of the guild.",
          "hero": "Training for one hero.",
          "cards": "Cards bought here can be offered on level-ups."}
_UP = (pygame.K_UP, pygame.K_w)
_DOWN = (pygame.K_DOWN, pygame.K_s)
_LEFT = (pygame.K_LEFT, pygame.K_a)
_RIGHT = (pygame.K_RIGHT, pygame.K_d)
_ENTER = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)
WIDTH = 78


class GuildPanel:
    def __init__(self, manager, guild: Guild, mode: str, hero: str,
                 on_buy: Callable[[bool], None] = lambda ok: None) -> None:
        self.manager = manager
        self.guild = guild
        self.mode = mode
        self.hero = hero
        self.on_buy = on_buy
        self.index = 0

    # --- What's for sale ----------------------------------------------------------------

    def keys(self) -> list[str]:
        if self.mode == "guild":
            return list(config.GUILD_UPGRADES)
        if self.mode == "hero":
            return list(config.HERO_UPGRADES[self.hero])
        return [k for k in config.CARDS if card_price(k) is not None]

    def price(self, key: str) -> int | None:
        """What the row costs now; None: nothing left to buy."""
        if self.mode == "cards":
            return None if self.guild.unlocked(key) else card_price(key)
        return self.guild.next_cost(key, self._hero_arg())

    def _hero_arg(self) -> str | None:
        return self.hero if self.mode == "hero" else None

    def buy(self, index: int | None = None) -> bool:
        keys = self.keys()
        if not keys:
            return False
        key = keys[self.index if index is None else index]
        if self.mode == "cards":
            ok = self.guild.buy_card(key)
        else:
            ok = self.guild.buy_upgrade(key, self._hero_arg())
        self.on_buy(ok)
        return ok

    # --- Layout -------------------------------------------------------------------------

    @property
    def list_top(self) -> int:
        """First row of the list, from the box top (below the hero tabs)."""
        return 5 if self.mode == "hero" else 3

    def geometry(self) -> tuple[int, int, int, int]:
        d = self.manager.display
        width = min(WIDTH, d.cols - 2)
        height = self.list_top + len(self.keys()) + 7
        return (d.cols - width) // 2, max(0, (d.rows - height) // 2), width, height

    def row_at(self, col: int, row: int) -> int | None:
        left, top, width, _ = self.geometry()
        i = row - (top + self.list_top)
        if 0 <= i < len(self.keys()) and left < col < left + width - 1:
            return i
        return None

    # --- Input --------------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        n = len(self.keys())
        if event.type == pygame.KEYDOWN:
            if event.key in _UP and n:
                self.index = (self.index - 1) % n
            elif event.key in _DOWN and n:
                self.index = (self.index + 1) % n
            elif event.key in _LEFT + _RIGHT and self.mode == "hero":
                heroes = list(config.HERO_UPGRADES)
                step = -1 if event.key in _LEFT else 1
                self.hero = heroes[(heroes.index(self.hero) + step) % len(heroes)]
                self.index = min(self.index, len(self.keys()) - 1)
            elif event.key in _ENTER:
                self.buy()
            return
        if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
            cell = self.manager.display.window_to_cell(*event.pos)
            i = self.row_at(*cell) if cell is not None else None
            if i is None:
                return
            self.index = i
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.buy(i)

    # --- Drawing ------------------------------------------------------------------------

    def draw(self, text: TextRenderer) -> None:
        left, top, width, height = self.geometry()
        icon = loot_glyph(text)
        draw_box(text, left, top, width, height, palette.HUB_LABEL, TITLES[self.mode],
                 palette.HUB_LABEL)
        purse = f"LOOT {icon} {self.guild.loot}"
        text.put(left + width - len(purse) - 2, top + 1, purse, palette.LOOT_TEXT)
        text.put(left + 2, top + 1, BLURBS[self.mode], colors.GREY)
        if self.mode == "hero":
            tabs = "  ".join(f"[{h.upper()}]" if h == self.hero else h.upper()
                             for h in config.HERO_UPGRADES)
            center(text, top + 3, tabs, colors.AMBER, left, width)
        for i, key in enumerate(self.keys()):
            self._row(text, left + 1, top + self.list_top + i, width - 2, key, i == self.index,
                      icon)
        keys = self.keys()
        if keys:
            for j, line in enumerate(textwrap.wrap(self.describe(keys[self.index]), width - 4)[:2]):
                center(text, top + height - 5 + j, line, palette.CARD_TEXT, left, width)
        hint = "Up/Down choose   Enter or click: buy   Esc: leave"
        if self.mode == "hero":
            hint = "Left/Right: hero   " + hint
        center(text, top + height - 2, hint, colors.GREY, left, width)

    def describe(self, key: str) -> str:
        """The highlighted row in full, under the list."""
        if self.mode == "cards":
            c = config.CARDS[key]
            name, effect = card_text(key, rarities_of(c)[0])
            return f"{name}: {effect}"
        spec = self.guild.spec(key, self._hero_arg())
        lv = self.guild.level(key, self._hero_arg())
        return f"{spec.name}: {spec.text} per level (now level {lv} of {spec.max_level})"

    def _row(self, text: TextRenderer, col: int, row: int, width: int, key: str, selected: bool,
             icon: str) -> None:
        bg = palette.CARD_BG_SELECTED if selected else None
        if selected:
            text.put(col, row, " " * width, colors.WHITE, bg)
        price = self.price(key)
        if self.mode == "cards":
            c = config.CARDS[key]
            rarity = rarities_of(c)[0]
            name, effect = card_text(key, rarity)
            who = c.heroes[0].upper() if len(c.heroes) == 1 else "ANYONE"
            text.put(col + 1, row, f"{name:<16}", palette.CARD_TITLE, bg)
            text.put(col + 18, row, f"{who:<9}", palette.CARD_TAG, bg)
            text.put(col + 27, row, f"{rarity:<10}", palette.CARD_RARITY[rarity], bg)
            text.put(col + 38, row, _fit(effect, width - 38 - 10), palette.CARD_TEXT, bg)
            done = "OWNED"
        else:
            spec = self.guild.spec(key, self._hero_arg())
            lv = self.guild.level(key, self._hero_arg())
            text.put(col + 1, row, f"{spec.name:<16}", palette.CARD_TITLE, bg)
            text.put(col + 18, row, "█" * lv, palette.LOOT, bg)
            text.put(col + 18 + lv, row, "░" * (spec.max_level - lv), palette.PIP_EMPTY, bg)
            text.put(col + 25, row, f"{lv}/{spec.max_level}", colors.GREY, bg)
            text.put(col + 30, row, _fit(spec.text + " per level", width - 30 - 9),
                     palette.CARD_TEXT, bg)
            done = "MAX"
        if price is None:
            label, fg = done, colors.GREY
        else:
            label = f"{icon} {price}"
            fg = palette.LOOT_TEXT if price <= self.guild.loot else palette.CARD_TAG
        text.put(col + width - len(label) - 1, row, label, fg, bg)


def _fit(s: str, width: int) -> str:
    return s if len(s) <= width else s[: max(0, width - 2)] + ".."
