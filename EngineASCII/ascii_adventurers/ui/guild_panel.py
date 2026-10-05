"""
ui/guild_panel.py -- the Guild Hall's shops and the dungeon gate: a
framed list of rows, opened by talking to one of the guild's people.

  "guild"    the guildmaster: upgrades every hero shares;
  "hero"     the trainer: one hero's own upgrades (Left / Right: which hero);
  "archive"  the archivist's shelves (Left / Right: which shelf): cards,
             spells, pacts, bestiary, and the journal (M22.6: every quest
             whose boss you've beaten, "???" for the rest; nothing to buy);
  "gate"     the dungeon gate: switch owned pacts on or off, then enter.

Up / Down (or the mouse) choose a row, Enter or a click acts on it (buy,
switch, enter); Esc closes (the scene handles that). Long lists scroll.
Each row: name, a short column (level pips, whose card, kills...), what
it does, and its price -- dim when you can't afford it, or a state word
(MAX, OWNED, KNOWN, ON / OFF) once there's nothing to buy. The highlighted
row is described in full under the list; the purse sits top right.
Buying calls `on_buy(ok)` so the scene can play a sound and save.
"""

from __future__ import annotations

import textwrap
from dataclasses import dataclass
from typing import Callable

import pygame

from engine import TextRenderer, colors

from .. import config, palette
from ..meta.guild import Guild, card_price
from ..players.cards import card_text, rarities_of, spell_of
from ..render.glyphs import loot_glyph
from ..systems.run_rules import pact_totals
from .frame import center, draw_box

TITLES = {"guild": "THE GUILDMASTER", "hero": "THE TRAINER", "archive": "THE ARCHIVE",
          "gate": "THE DUNGEON GATE"}
BLURBS = {"guild": "Upgrades for every adventurer of the guild.",
          "hero": "Training for one hero.",
          "archive": "Knowledge, bought with loot.",
          "gate": "Pacts make the dungeon far deadlier, for a little more loot."}
SHELVES = ("cards", "spells", "pacts", "bestiary", "journal")
SHELF_BLURBS = {"cards": "Cards bought here can be offered on level-ups.",
                "spells": "Spells bought here can be offered on level-ups.",
                "pacts": "Buy a pact here; switch it on at the dungeon gate.",
                "bestiary": f"A page is yours after {config.BESTIARY_KILLS} kills, or bought: "
                            f"+{round(config.BESTIARY_BONUS * 100)}% damage to that enemy.",
                "journal": "Every quest whose guardian you have beaten."}
_UP = (pygame.K_UP, pygame.K_w)
_DOWN = (pygame.K_DOWN, pygame.K_s)
_LEFT = (pygame.K_LEFT, pygame.K_a)
_RIGHT = (pygame.K_RIGHT, pygame.K_d)
_ENTER = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)
WIDTH = 78
NAME_W = 18


@dataclass
class Row:
    key: str
    name: str
    column: str              # pips / whose / kills...
    info: str                # what it does, short
    price: int | None        # None: nothing to buy
    state: str = ""          # shown instead of a price
    describe: str = ""       # the full line under the list
    pips: tuple[int, int] | None = None    # (owned, max): drawn as blocks
    column_color: tuple | None = None


class GuildPanel:
    def __init__(self, manager, guild: Guild, mode: str, hero: str,
                 on_buy: Callable[[bool], None] = lambda ok: None,
                 enter: Callable[[], None] | None = None) -> None:
        self.manager = manager
        self.guild = guild
        self.mode = mode
        self.hero = hero
        self.on_buy = on_buy
        self.enter = enter                 # the gate: off to the dungeon
        self.shelf = 0
        self.index = 0
        self.top = 0                       # first row shown (scrolling)

    # --- Rows ---------------------------------------------------------------------------

    def rows(self) -> list[Row]:
        if self.mode in ("guild", "hero"):
            return self._upgrade_rows()
        if self.mode == "gate":
            return self._gate_rows()
        return getattr(self, "_" + SHELVES[self.shelf] + "_rows")()

    def keys(self) -> list[str]:
        return [r.key for r in self.rows()]

    def _hero_arg(self) -> str | None:
        return self.hero if self.mode == "hero" else None

    def _upgrade_rows(self) -> list[Row]:
        hero = self._hero_arg()
        specs = config.GUILD_UPGRADES if hero is None else config.HERO_UPGRADES[hero]
        out = []
        for key, spec in specs.items():
            lv = self.guild.level(key, hero)
            out.append(Row(key, spec.name, "", spec.text, self.guild.next_cost(key, hero),
                           "MAX", f"{spec.name}: {spec.text} per level "
                                  f"(level {lv} of {spec.max_level})",
                           pips=(lv, spec.max_level)))
        return out

    def _card_rows(self, spells: bool) -> list[Row]:
        out = []
        for key, c in config.CARDS.items():
            if card_price(key) is None or (spell_of(c) is not None) != spells:
                continue
            rarity = rarities_of(c)[0]
            name, effect = card_text(key, rarity)
            who = c.heroes[0].upper() if len(c.heroes) == 1 else "ANYONE"
            owned = self.guild.unlocked(key)
            out.append(Row(key, name, who, effect, None if owned else card_price(key), "OWNED",
                           f"{name} ({rarity}): {effect}",
                           column_color=palette.CARD_RARITY[rarity]))
        return out

    def _cards_rows(self) -> list[Row]:
        return self._card_rows(spells=False)

    def _spells_rows(self) -> list[Row]:
        return self._card_rows(spells=True)

    def _pacts_rows(self) -> list[Row]:
        out = []
        for key, pact in config.PACTS.items():
            owned = key in self.guild.pacts
            bonus = f"+{round(pact.loot * 100)}% loot"
            out.append(Row(key, pact.name, bonus, pact.text, None if owned else pact.price,
                           "OWNED", f"{pact.name}: {pact.text}; {bonus} while it's on"))
        return out

    def _bestiary_rows(self) -> list[Row]:
        out = []
        for key, (price, notes) in config.BESTIARY.items():
            spec = config.ENEMIES[key]
            known = self.guild.known(key)
            kills = self.guild.kills.get(key, 0)
            column = f"{min(kills, config.BESTIARY_KILLS)}/{config.BESTIARY_KILLS}"
            info = notes if known else "???"
            describe = (f"{spec.name.upper()}: {spec.max_hp} HP. {notes}" if known
                        else f"Slay {config.BESTIARY_KILLS} or buy the page to read it.")
            out.append(Row(key, spec.name.title(), column, info, None if known else price,
                           "KNOWN", describe))
        return out

    def _journal_rows(self) -> list[Row]:
        out = []
        for key, q in config.QUESTS.items():
            e = self.guild.journal.get(key)
            if e is None:
                out.append(Row(key, "???", q.biome.upper(), "???", None, "",
                               f"Not completed yet. Somewhere in the {q.biome}, someone needs "
                               f"help."))
                continue
            boss = config.BOSSES[q.boss].name
            best = e["best"]
            fastest = f"   fastest {int(best // 60)}:{int(best % 60):02d}" if best else ""
            heroes = ", ".join(h.upper() for h in e["heroes"])
            story = " ".join(q.say("offer"))
            out.append(Row(key, q.title, q.biome.upper(), f"{boss}{fastest}", None,
                           f"x{e['wins']}",
                           f"The {q.giver}: \"{story}\" Beaten by: {heroes}."))
        return out

    def _gate_rows(self) -> list[Row]:
        total = pact_totals(self.guild.active_pacts)["loot"]
        rows = [Row("enter", "Enter the dungeon", "", f"loot +{round(total * 100)}%"
                    if total else "", None, ">>", "Choose your hero and island, then go.")]
        for key in config.PACTS:
            if key in self.guild.pacts:
                pact = config.PACTS[key]
                on = key in self.guild.active_pacts
                rows.append(Row(key, pact.name, f"+{round(pact.loot * 100)}%", pact.text, None,
                                "ON" if on else "OFF", f"{pact.name}: {pact.text}"))
        return rows

    # --- Acting -------------------------------------------------------------------------

    def price(self, key: str) -> int | None:
        row = next((r for r in self.rows() if r.key == key), None)
        return None if row is None else row.price

    def buy(self, index: int | None = None) -> bool:
        rows = self.rows()
        if not rows:
            return False
        key = rows[self.index if index is None else index].key
        g = self.guild
        if self.mode == "gate":
            if key == "enter":
                if self.enter is not None:
                    self.enter()
                return True
            g.toggle_pact(key)
            self.on_buy(True)
            return True
        if self.mode in ("guild", "hero"):
            ok = g.buy_upgrade(key, self._hero_arg())
        else:
            shelf = SHELVES[self.shelf]
            if shelf == "journal":
                return False                   # (only to read)
            ok = (g.buy_pact(key) if shelf == "pacts" else g.buy_page(key) if shelf == "bestiary"
                  else g.buy_card(key))
        self.on_buy(ok)
        return ok

    # --- Layout -------------------------------------------------------------------------

    @property
    def list_top(self) -> int:
        """First row of the list, from the box top (below any tabs)."""
        return 5 if self.mode in ("hero", "archive") else 3

    @property
    def journal(self) -> bool:
        return self.mode == "archive" and SHELVES[self.shelf] == "journal"

    @property
    def desc_lines(self) -> int:
        """Lines for the highlighted row's description (a journal entry's
        story needs more)."""
        return 4 if self.journal else 2

    def visible_rows(self) -> int:
        d = self.manager.display
        return max(3, min(len(self.rows()), d.rows - 4 - self.list_top - 5 - self.desc_lines))

    def geometry(self) -> tuple[int, int, int, int]:
        d = self.manager.display
        width = min(WIDTH, d.cols - 2)
        height = self.list_top + self.visible_rows() + 5 + self.desc_lines
        return (d.cols - width) // 2, max(0, (d.rows - height) // 2), width, height

    def _scroll(self) -> None:
        n, vis = len(self.rows()), self.visible_rows()
        self.index = max(0, min(self.index, n - 1))
        if self.index < self.top:
            self.top = self.index
        elif self.index >= self.top + vis:
            self.top = self.index - vis + 1
        self.top = max(0, min(self.top, max(0, n - vis)))

    def row_at(self, col: int, row: int) -> int | None:
        left, top, width, _ = self.geometry()
        i = row - (top + self.list_top)
        if 0 <= i < self.visible_rows() and left < col < left + width - 1 \
                and self.top + i < len(self.rows()):
            return self.top + i
        return None

    # --- Input --------------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        n = len(self.rows())
        if event.type == pygame.KEYDOWN:
            if event.key in _UP and n:
                self.index = (self.index - 1) % n
            elif event.key in _DOWN and n:
                self.index = (self.index + 1) % n
            elif event.key in _LEFT + _RIGHT:
                step = -1 if event.key in _LEFT else 1
                if self.mode == "hero":
                    heroes = list(config.HERO_UPGRADES)
                    self.hero = heroes[(heroes.index(self.hero) + step) % len(heroes)]
                elif self.mode == "archive":
                    self.shelf = (self.shelf + step) % len(SHELVES)
                    self.index = self.top = 0
            elif event.key in _ENTER:
                self.buy()
            self._scroll()
            return
        if event.type == pygame.MOUSEWHEEL and n:
            self.index = max(0, min(n - 1, self.index - event.y))
            self._scroll()
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
        self._scroll()
        left, top, width, height = self.geometry()
        icon = loot_glyph(text)
        draw_box(text, left, top, width, height, palette.HUB_LABEL, TITLES[self.mode],
                 palette.HUB_LABEL)
        purse = f"LOOT {icon} {self.guild.loot}"
        text.put(left + width - len(purse) - 2, top + 1, purse, palette.LOOT_TEXT)
        blurb = SHELF_BLURBS[SHELVES[self.shelf]] if self.mode == "archive" else BLURBS[self.mode]
        text.put(left + 2, top + 1, _fit(blurb, width - len(purse) - 6), colors.GREY)
        if self.mode in ("hero", "archive"):
            tabs = list(config.HERO_UPGRADES) if self.mode == "hero" else list(SHELVES)
            on = self.hero if self.mode == "hero" else SHELVES[self.shelf]
            line = "  ".join(f"[{t.upper()}]" if t == on else t.upper() for t in tabs)
            center(text, top + 3, line, colors.AMBER, left, width)
        rows = self.rows()
        vis = self.visible_rows()
        for i, r in enumerate(rows[self.top:self.top + vis]):
            self._row(text, left + 1, top + self.list_top + i, width - 2, r,
                      self.top + i == self.index, icon)
        if self.top > 0:                       # more above / below: marks on the frame
            text.put(left + width - 1, top + self.list_top, "^", palette.HUB_LABEL)
        if self.top + vis < len(rows):
            text.put(left + width - 1, top + self.list_top + vis - 1, "v", palette.HUB_LABEL)
        if rows:
            n = self.desc_lines
            for j, line in enumerate(textwrap.wrap(rows[self.index].describe, width - 4)[:n]):
                center(text, top + height - 3 - n + j, line, palette.CARD_TEXT, left, width)
        elif self.mode == "gate":
            center(text, top + height - 5, "no pacts yet", colors.GREY, left, width)
        hint = "Up/Down choose   Enter or click: " + ("go / switch" if self.mode == "gate"
                                                     else "buy") + "   Esc: leave"
        if self.mode == "hero":
            hint = "Left/Right: hero   " + hint
        elif self.journal:
            hint = "Left/Right: shelf   Up/Down choose   Esc: leave"
        elif self.mode == "archive":
            hint = "Left/Right: shelf   " + hint
        center(text, top + height - 2, hint, colors.GREY, left, width)

    def _row(self, text: TextRenderer, col: int, row: int, width: int, r: Row, selected: bool,
             icon: str) -> None:
        bg = palette.CARD_BG_SELECTED if selected else None
        if selected:
            text.put(col, row, " " * width, colors.WHITE, bg)
        text.put(col + 1, row, _fit(r.name, NAME_W - 1), palette.CARD_TITLE, bg)
        c = col + NAME_W + 1
        if r.pips is not None:
            lv, top = r.pips
            shown = min(top, 10)               # long ladders: one block per 10%
            full = round(lv / top * shown) if top else 0
            text.put(c, row, "█" * full, palette.LOOT, bg)
            text.put(c + full, row, "░" * (shown - full), palette.PIP_EMPTY, bg)
            text.put(c + shown + 1, row, f"{lv}/{top}", colors.GREY, bg)
            info_col = c + 17
        else:
            text.put(c, row, _fit(r.column, 10), r.column_color or palette.CARD_TAG, bg)
            info_col = c + 11
        if r.price is None:
            label, fg = r.state, (palette.LOOT_TEXT if r.state == "ON" else colors.GREY)
        else:
            label = f"{icon} {r.price}"
            fg = palette.LOOT_TEXT if r.price <= self.guild.loot else palette.CARD_TAG
        text.put(info_col, row, _fit(r.info, col + width - info_col - len(label) - 3),
                 palette.CARD_TEXT, bg)
        text.put(col + width - len(label) - 1, row, label, fg, bg)


def _fit(s: str, width: int) -> str:
    return s if len(s) <= width else s[: max(0, width - 2)] + ".."
