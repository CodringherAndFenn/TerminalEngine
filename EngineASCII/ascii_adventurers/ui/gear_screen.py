"""
ui/gear_screen.py -- the hero's gear: the ten slots, the bag, and each
piece's card (design/GEAR.md 15.5, M28.1).

One screen, four uses (`mode`):
  "browse"   Tab (pad X) or the pause menu: look at what you wear; ENTER on
             a bagged piece wears it (what was in its slot goes to the bag),
             ENTER on a worn one or X on any salvages it into loot (asks
             once more first). No wearing inside a boss arena (`locked`).
  "upgrade"  the level-up picker's UPGRADE: choose a worn piece for +1.
  "slot"     a swap whose slot kind has more than one slot (rings,
             trinkets): which one to replace.
  "drop"     the bag is full: which piece to salvage (the bag's, or the
             one coming off).
In browse mode I (pad Y) flips to the STATS page (M28.3a, ui/gear_stats.py:
each weapon and spell's damage worked out, then the totals), given the
`hero`; UP / DOWN scroll it when it doesn't fit. With the Fourleaf Ring's
Foresight (M28.3h) there's a NEXT OFFER page too (N, or I again): the next
level's offer, drawn early; ENTER keeps the focused piece (act(("keep",
i))), so it stays through that offer's rerolls.
The screen only shows and chooses: it calls `done(choice)` (a slot id, a
bag index...) or `act(action)` in browse mode, and `cancel()` on
ESC / Tab / BACK; the game applies the change and calls refresh().

Layout: the paper doll (head; main hand, chest, off-hand; feet; the rings;
the trinkets), the bag under it, the focused piece's card on the right
(below the doll on narrow screens). Arrows move by rows and columns.
"""

from __future__ import annotations

import textwrap
from typing import Callable

import pygame

from engine import TextRenderer, colors

from .. import config, palette
from ..players.gear import (Equipment, Piece, legendary_trick, next_level_text, next_trick,
                            power_name, power_text, salvage_value, slot_kind, affix_text, tricks)
from .frame import center, draw_box, glint
from .gear_stats import damage_lines, total_lines

BOX_W = 20
BOX_H = 3
DETAIL_W = 34
_LEFT = (pygame.K_LEFT, pygame.K_a)
_RIGHT = (pygame.K_RIGHT, pygame.K_d)
_UP = (pygame.K_UP, pygame.K_w)
_DOWN = (pygame.K_DOWN, pygame.K_s)
_TAKE = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)
_CLOSE = (pygame.K_ESCAPE, pygame.K_TAB)
_STATS = (pygame.K_i,)
_NEXT = (pygame.K_n,)

_TITLES = {"browse": "GEAR", "upgrade": "UPGRADE: choose a piece for +1",
           "slot": "SWAP: which one does it replace?",
           "drop": "THE BAG IS FULL: salvage which?"}


def slot_label(slot: str) -> str:
    kind = slot_kind(slot)
    name = config.GEAR_SLOT_NAMES[kind]
    return f"{name} {slot[len(kind):]}" if slot != kind else name


def wrap(s: str, width: int) -> list[str]:
    return textwrap.wrap(s, max(8, width)) or [""]


def piece_lines(key: str, rarity: str, level: int, affixes, width: int, kind: str | None = None,
                capped=frozenset(), slot: str | None = None,
                full: bool = False, legend: bool = True) -> list[tuple[str, tuple]]:
    """A piece's card as (line, colour): rarity and slot, name, power, its
    tricks (M28.2: the unlocked ones' names -- in `full`, their text and the
    next one to come; a legendary's own trick, in full unless not
    `legend` -- then its name only, M28.3c), affixes (greyed "(max)" past their cap), and for a
    +1 what it adds."""
    c = config.CARDS[key]
    out = [(f"{rarity.upper()}  {config.GEAR_SLOT_NAMES[config.GEAR[key].slot]}",
            palette.CARD_RARITY[rarity]), ("", palette.CARD_TEXT)]
    name = config.GEAR[key].name + (f" +{level}" if level and kind != "plus" else "")
    out.append((name, palette.CARD_TITLE))
    out.append((power_name(key), palette.CARD_TAG))
    for line in wrap(power_text(key, level, rarity), width):
        out.append((line, palette.CARD_TEXT))
    got = [t for t in tricks(key) if t[0] <= level]
    if got and full:
        out.append(("", palette.CARD_TEXT))
        for t, name, text in got:
            out += [(ln, palette.CARD_SELECTED if i == 0 else palette.CARD_TEXT)
                    for i, ln in enumerate(wrap(f"+{t} {name.upper()}: {text}", width))]
    elif got:
        out += [(ln, palette.CARD_SELECTED)
                for ln in wrap(", ".join(f"+{t} {name}" for t, name, _ in got), width)]
    trick = legendary_trick(key) if rarity == "legendary" else None
    if trick is not None:                       # (M28.3c: on from +0)
        said = f"LEGENDARY {trick[0].upper()}" + (f": {trick[1]}" if legend else "")
        out += [(ln, palette.CARD_RARITY["legendary"]) for ln in wrap(said, width)]
    coming = next_trick(key, level)
    if full and coming is not None:
        out += [(ln, palette.CARD_TAG) for ln in wrap(f"at +{coming[0]}: {coming[1]}", width)]
    if affixes:
        out.append(("", palette.CARD_TEXT))
    for a in affixes:
        if (slot, a) in capped:
            out.append((affix_text(a, rarity) + " (max)", palette.CARD_TAG))
        else:
            out.append((affix_text(a, rarity), palette.CARD_TEXT))
    if kind == "plus":
        out.append(("", palette.CARD_TEXT))
        out.append((f"+{level} -> +{level + 1}", palette.CARD_SELECTED))
        for line in wrap(next_level_text(key, level, rarity), width):
            out.append((line, palette.CARD_SELECTED))
    if c.heroes and len(c.heroes) == 1:
        out.append(("", palette.CARD_TEXT))
        out.append((c.heroes[0].upper(), palette.CARD_TAG))
    return out


class GearScreen:
    def __init__(self, manager, progress, mode: str = "browse",
                 done: Callable[[object], None] | None = None,
                 cancel: Callable[[], None] | None = None,
                 act: Callable[[object], None] | None = None,
                 kind: str | None = None, outgoing: Piece | None = None, pauses: bool = True,
                 locked: bool = False, hero=None) -> None:
        self.manager = manager
        self.mode = mode
        self.done = done or (lambda choice: None)
        self.cancel = cancel or (lambda: None)
        self.act = act or (lambda action: None)
        self.kind = kind                 # "slot" mode: the slot kind to choose in
        self.outgoing = outgoing         # "drop" mode: the piece coming off
        self.pauses = pauses
        self.locked = locked             # inside a boss arena: no wearing from the bag
        self.hero = hero                 # browse: whose STATS page (None: no page)
        self.page = "gear"               # "gear", "stats" or "next" (Foresight)
        self.next_focus = 0              # the NEXT OFFER page's focused piece
        self.scroll = 0                  # the STATS page's first line
        self.focus = 0
        self.confirm = None              # the cell a salvage waits on a second press for
        self.message = ""
        self.sub: GearScreen | None = None   # browse: wearing a ring/trinket asks which slot
        self.refresh(progress)
        self.focus = self._first_enabled()

    def refresh(self, progress) -> None:
        self.eq: Equipment = progress.gear
        self.next_offer = list(getattr(progress, "next_offer", None) or [])
        self.kept = getattr(progress, "kept", None)
        self.next_level = getattr(progress, "level", 0) + 1
        self.next_focus = min(self.next_focus, max(0, len(self.next_offer) - 1))
        if self.page == "next" and not self.next_offer:
            self.page = "gear"
        self.capped = self.eq.capped()
        if self.sub is not None:
            self.sub.refresh(progress)
        cells = self.cells()
        self.focus = min(self.focus, len(cells) - 1)

    # --- Cells ------------------------------------------------------------------------

    def rows(self) -> list[list[object]]:
        """Cell ids by row: slot ids, ("bag", i), and "out" (drop mode: the
        piece coming off)."""
        eq = self.eq
        ids = eq.slot_ids()
        rows = [["head"], ["main", "chest", "off"], ["feet"],
                [s for s in ids if slot_kind(s) == "ring"],
                [s for s in ids if slot_kind(s) == "trinket"]]
        bag = [("bag", i) for i in range(config.GEAR_BAG)]
        if self.mode == "drop":
            bag.append("out")
        rows.append(bag)
        return rows

    def cells(self) -> list[object]:
        return [c for row in self.rows() for c in row]

    def piece_at(self, cell) -> Piece | None:
        if isinstance(cell, tuple):
            i = cell[1]
            return self.eq.bag[i] if i < len(self.eq.bag) else None
        if cell == "out":
            return self.outgoing
        return self.eq.worn.get(cell)

    def enabled(self, cell) -> bool:
        p = self.piece_at(cell)
        if self.mode == "upgrade":
            return not isinstance(cell, tuple) and p is not None and p.level < config.GEAR_MAX_LEVEL
        if self.mode == "slot":
            return not isinstance(cell, tuple) and cell != "out" and slot_kind(cell) == self.kind
        if self.mode == "drop":
            return (isinstance(cell, tuple) and p is not None) or cell == "out"
        return True

    def _first_enabled(self) -> int:
        for i, c in enumerate(self.cells()):
            if self.enabled(c) and (self.mode != "browse" or self.piece_at(c) is not None):
                return i
        return 0

    # --- Layout -----------------------------------------------------------------------

    def _wide(self) -> bool:
        return self.manager.display.cols >= 4 * (BOX_W + 1) + DETAIL_W + 8

    def _box_w(self) -> int:
        d = self.manager.display
        return BOX_W if self._wide() or d.cols >= 4 * (BOX_W + 1) + 6 else (d.cols - 9) // 4

    def geometry(self) -> tuple[int, int, int, int]:
        """(left, top, width, height) of the whole frame."""
        d = self.manager.display
        bw = self._box_w()
        doll_w = 4 * (bw + 1) + 1
        rows = len(self.rows())
        h = 3 + rows * BOX_H + 1 + 2 + (0 if self._wide() else 6)
        w = doll_w + 4 + (DETAIL_W + 2 if self._wide() else 0)
        w, h = min(w, d.cols), min(h, d.rows)
        return (d.cols - w) // 2, max(0, (d.rows - h) // 2), w, h

    def _cell_rects(self) -> dict:
        left, top, _, _ = self.geometry()
        bw = self._box_w()
        doll_w = 4 * (bw + 1) - 1
        out = {}
        for r, row in enumerate(self.rows()):
            n = len(row)
            span = n * bw + (n - 1)
            col = left + 2 + (doll_w - span) // 2
            for i, cell in enumerate(row):
                out[cell] = (col + i * (bw + 1), top + 2 + r * BOX_H, bw)
        return out

    def cell_at(self, col: int, row: int):
        for cell, (c, r, w) in self._cell_rects().items():
            if c <= col < c + w and r <= row < r + BOX_H:
                return cell
        return None

    # --- Input ------------------------------------------------------------------------

    def _move(self, dr: int, dc: int) -> None:
        rows = self.rows()
        cur = self.cells()[self.focus]
        r = next(i for i, row in enumerate(rows) if cur in row)
        c = rows[r].index(cur)
        if dc:
            c = (c + dc) % len(rows[r])
        else:                            # keep roughly the same place across
            frac = (c + 0.5) / len(rows[r])
            r = (r + dr) % len(rows)
            c = min(len(rows[r]) - 1, int(frac * len(rows[r])))
        self.focus = self.cells().index(rows[r][c])
        self.confirm = None

    def _press(self, cell) -> None:
        """ENTER / click on a cell."""
        if not self.enabled(cell):
            return
        if self.mode in ("upgrade", "slot"):
            self.done(cell)
            return
        if self.mode == "drop":
            self.done(len(self.eq.bag) if cell == "out" else cell[1])
            return
        p = self.piece_at(cell)
        if p is None:
            return
        if isinstance(cell, tuple):                      # wear a bagged piece
            if self.locked:
                self.message = "Not inside a boss arena."
                return
            slots = self.eq.slots_of(p.slot)
            free = self.eq.free(p.slot)
            if free is not None or len(slots) == 1:
                self._wear(cell[1], free or slots[0])
            else:
                self.sub = GearScreen(self.manager, _Prog(self.eq), "slot", kind=p.slot,
                                      done=lambda s, i=cell[1]: self._wear(i, s),
                                      cancel=self._close_sub, pauses=self.pauses)
            return
        self._salvage(cell)

    def _wear(self, index: int, slot: str) -> None:
        self.sub = None
        if not self.eq.can_wear(index, slot):
            self.message = "You already wear that."
            return
        self.message = ""
        self.act(("wear", index, slot))

    def _salvage(self, cell) -> None:
        p = self.piece_at(cell)
        if p is None or self.mode != "browse":
            return
        if self.confirm != cell:
            self.confirm = cell
            self.message = f"Salvage {p.name} for {salvage_value(p)} loot? Press again."
            return
        self.confirm = None
        self.message = ""
        if isinstance(cell, tuple):
            self.act(("salvage", "bag", cell[1]))
        else:
            self.act(("salvage", "worn", cell))

    def _close_sub(self) -> None:
        self.sub = None

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.sub is not None:
            self.sub.handle_event(event)
            return
        cells = self.cells()
        if event.type == pygame.KEYDOWN and self.mode == "browse" and (
                event.key in _STATS or event.key in _NEXT):
            pages = ["gear"] + (["stats"] if self.hero is not None else []) \
                + (["next"] if self.next_offer else [])
            if event.key in _NEXT:
                page = "gear" if self.page == "next" else "next"
            else:
                page = pages[(pages.index(self.page) + 1) % len(pages)]
            if page in pages:
                self.page = page
                self.scroll, self.confirm, self.message = 0, None, ""
            return
        if self.page == "next":
            if event.type == pygame.KEYDOWN:
                if event.key in _CLOSE:
                    self.cancel()
                elif event.key in _LEFT + _UP:
                    self.next_focus = (self.next_focus - 1) % len(self.next_offer)
                elif event.key in _RIGHT + _DOWN:
                    self.next_focus = (self.next_focus + 1) % len(self.next_offer)
                elif event.key in _TAKE:
                    self.act(("keep", self.next_focus))
            return
        if self.page == "stats":
            if event.type == pygame.KEYDOWN:
                if event.key in _CLOSE:
                    self.cancel()
                elif event.key in _UP:
                    self.scroll = max(0, self.scroll - 1)
                elif event.key in _DOWN:
                    self.scroll += 1
            return
        if event.type == pygame.KEYDOWN:
            if event.key in _CLOSE:
                self.cancel()
            elif event.key in _LEFT:
                self._move(0, -1)
            elif event.key in _RIGHT:
                self._move(0, 1)
            elif event.key in _UP:
                self._move(-1, 0)
            elif event.key in _DOWN:
                self._move(1, 0)
            elif event.key in _TAKE:
                self._press(cells[self.focus])
            elif event.key == pygame.K_x and self.mode == "browse":
                self._salvage(cells[self.focus])
            return
        if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
            cell = self.manager.display.window_to_cell(*event.pos)
            hit = self.cell_at(*cell) if cell is not None else None
            if hit is None:
                return
            if cells.index(hit) != self.focus:
                self.focus = cells.index(hit)
                self.confirm = None
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._press(hit)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                self._salvage(hit)

    # --- Drawing ----------------------------------------------------------------------

    def draw(self, text: TextRenderer) -> None:
        if self.sub is not None:
            self.sub.draw(text)
            return
        left, top, w, h = self.geometry()
        if self.page == "stats":
            self._draw_stats(text, left, top, w, h)
            return
        if self.page == "next":
            self._draw_next(text, left, top, w, h)
            return
        draw_box(text, left, top, w, h, palette.CARD_TAG, _TITLES[self.mode], palette.CARD_TITLE)
        bag_row = len(self.rows()) - 1
        cells = self.cells()
        focus = cells[self.focus]
        for cell, (col, row, bw) in self._cell_rects().items():
            self._box(text, col, row, bw, cell, cell == focus)
        _, bag_top, _ = self._cell_rects()[("bag", 0)]
        text.put(left + 2, bag_top + 1, "BAG", palette.CARD_TAG)
        # The focused piece's card.
        p = self.piece_at(focus)
        if self._wide():
            dl, dt, dw = left + w - DETAIL_W - 2, top + 2, DETAIL_W
            room = h - 6
        else:
            dl, dt, dw = left + 2, top + 2 + (bag_row + 1) * BOX_H, w - 4
            room = h - (dt - top) - 3
        if p is not None:
            slot = None if isinstance(focus, tuple) or focus == "out" else focus
            lines = piece_lines(p.key, p.rarity, p.level, p.affixes, dw - 2, capped=self.capped,
                                slot=slot, full=True)
            if self.mode == "upgrade" and p.level < config.GEAR_MAX_LEVEL:
                lines += [("", colors.GREY), (f"+{p.level} -> +{p.level + 1}", palette.CARD_SELECTED)]
                more = next_level_text(p.key, p.level, p.rarity)
                lines += [(s, palette.CARD_SELECTED) for s in wrap(more, dw - 2)]
            lines += [("", colors.GREY), (f"salvage: {salvage_value(p)} loot", palette.LOOT_TEXT)]
            for i, (line, fg) in enumerate(lines[:room]):
                text.put(dl, dt + i, line[:dw], fg)
        elif not isinstance(focus, tuple) and focus != "out":
            text.put(dl, dt, slot_label(focus) + ": empty", colors.GREY)
        hint = {"browse": "ENTER wear / salvage   X salvage   "
                          + ("I stats   " if self.hero is not None else "")
                          + ("N next offer   " if self.next_offer else "") + "TAB close",
                "upgrade": "ENTER give it +1   ESC back",
                "slot": "ENTER replace this one   ESC back",
                "drop": "ENTER salvage this one   ESC back"}[self.mode]
        if self.message:
            center(text, top + h - 3, self.message[:w - 4], palette.CARD_SELECTED, left, w, None)
        center(text, top + h - 2, hint[:w - 4], colors.GREY, left, w, None)

    def _box(self, text: TextRenderer, col: int, row: int, bw: int, cell, focused: bool) -> None:
        p = self.piece_at(cell)
        on = self.enabled(cell)
        if isinstance(cell, tuple):
            label = f"BAG {cell[1] + 1}"
        elif cell == "out":
            label = "COMING OFF"
        else:
            label = slot_label(cell)
        edge = palette.CARD_SELECTED if focused else \
            (palette.CARD_RARITY[p.rarity] if p is not None and on else palette.CARD_TAG)
        bg = palette.CARD_BG_SELECTED if focused else palette.HUD_PANEL
        top_line = "┌" + f" {label} "[:bw - 2].ljust(bw - 2, "─") + "┐"
        text.put(col, row, top_line, edge, bg)
        if p is None:
            body, fg = "-", palette.CARD_TAG
        else:
            lv = f" +{p.level}" if p.level else ""
            body = p.name[:bw - 2 - len(lv)] + lv
            fg = palette.CARD_RARITY[p.rarity] if on else palette.CARD_TAG
        text.put(col, row + 1, "│" + body.center(bw - 2)[:bw - 2] + "│", edge, bg)
        text.put(col + 1, row + 1, body.center(bw - 2)[:bw - 2], fg, bg)
        text.put(col, row + 2, "└" + "─" * (bw - 2) + "┘", edge, bg)
        if p is not None and p.rarity == "legendary":
            glint(text, col, row, bw, BOX_H, bg)             # (M28.3a: the legendary look)

    def _draw_next(self, text: TextRenderer, left: int, top: int, w: int, h: int) -> None:
        """Fourleaf Ring (L), Foresight: the next level's offer, and the
        focused piece's card."""
        draw_box(text, left, top, w, h, palette.CARD_TAG,
                 f"NEXT OFFER (level {self.next_level})", palette.CARD_TITLE)
        rows = next_lines(self.next_offer, self.kept, self.next_focus)
        for i, (line, fg) in enumerate(rows):
            text.put(left + 2, top + 2 + i, line[:w - 4], fg)
        o = self.next_offer[self.next_focus]
        level = 0
        if o.kind == "plus":
            worn = self.eq.wearing(o.key)
            level = self.eq.worn[worn].level if worn is not None else 0
        dt = top + 3 + len(rows)
        room = h - (dt - top) - 3
        for i, (line, fg) in enumerate(piece_lines(o.key, o.rarity, level, o.affixes, w - 6,
                                                   kind=o.kind, full=True)[:room]):
            text.put(left + 2, dt + i, line[:w - 4], fg)
        hint = "ENTER keep / unkeep   N gear   TAB close"
        center(text, top + h - 3, "The kept piece stays through rerolls."[:w - 4], colors.GREY,
               left, w, None)
        center(text, top + h - 2, hint[:w - 4], colors.GREY, left, w, None)

    def stat_columns(self) -> tuple[list, list]:
        """The STATS page's two columns: damage, then the totals."""
        return damage_lines(self.hero), total_lines(self.hero)

    def _draw_stats(self, text: TextRenderer, left: int, top: int, w: int, h: int) -> None:
        draw_box(text, left, top, w, h, palette.CARD_TAG, "GEAR: STATS", palette.CARD_TITLE)
        dmg, totals = self.stat_columns()
        room = h - 5
        inner = w - 4
        if inner >= 2 * 40 + 3:                          # two columns side by side
            right_w = max(30, inner // 3)
            cols = [(left + 2, inner - right_w - 3, dmg), (left + w - 2 - right_w, right_w, totals)]
            longest = max(len(dmg), len(totals))
        else:                                            # one, scrolling
            cols = [(left + 2, inner, dmg + [("", colors.GREY)] + totals)]
            longest = len(cols[0][2])
        self.scroll = max(0, min(self.scroll, longest - room))
        for col, width, lines in cols:
            for i, (line, fg) in enumerate(lines[self.scroll:self.scroll + room]):
                text.put(col, top + 2 + i, line[:width], fg)
        hint = ("I next offer" if self.next_offer else "I gear") + "   TAB close" \
            + ("   UP / DOWN scroll" if longest > room else "")
        center(text, top + h - 2, hint[:w - 4], colors.GREY, left, w, None)


def next_lines(offer, kept, focus: int) -> list[tuple[str, tuple]]:
    """The NEXT OFFER page's list: a line a piece, "[*]" on the kept one,
    ">" on the focused one."""
    out = []
    for i, o in enumerate(offer):
        mark = "[*]" if i == kept else "[ ]"
        name = config.GEAR[o.key].name + (" +1" if o.kind == "plus" else "")
        out.append((f"{'>' if i == focus else ' '} {mark} {name}  {o.rarity}",
                    palette.CARD_SELECTED if i == focus else palette.CARD_RARITY[o.rarity]))
    return out


class _Prog:
    """A stand-in progress for a sub-screen (it only reads .gear)."""

    def __init__(self, eq: Equipment) -> None:
        self.gear = eq
