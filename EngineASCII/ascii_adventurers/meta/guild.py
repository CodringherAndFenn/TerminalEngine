"""
meta/guild.py -- meta progression: the loot purse and what it has bought
(save/guild.json).

Loot found in a run is kept in full however the run ends and lands in the
purse (bank_run). The purse buys, in the Guild Hall (scenes/guild_hall.py,
design/GUILD.md):
  * guild upgrades (config.GUILD_UPGRADES), shared by every hero;
  * hero upgrades (config.HERO_UPGRADES), one tree per hero;
  * from the archivist: card unlocks (cards whose `unlock` is "L:<price>"
    join the offer pool), pacts (config.PACTS; `active_pacts` are the ones
    switched on at the dungeon gate) and bestiary pages (config.BESTIARY;
    a page is also yours after BESTIARY_KILLS kills of that enemy, which
    `kills` counts over all runs).
Achievement cards ("A:<name>") unlock when `achievements` holds the name.

Rev 2 (M16) changed the upgrades and their prices. A save from before it
(no "version") has every upgrade level refunded into the purse, at what
it cost then (config.REV1_PRICES); cards bought stay bought.

A run starts from meta_steps(hero): every upgrade level owned, as the same
(stat, op, value) steps cards use, so players/cards.build_loadout stacks
them with the run's cards.

Loading never fails: unknown keys and bad values are dropped, levels are
clamped to each upgrade's max (so retuned data can't break a save).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .. import config
from .files import SAVE_DIR, read_json, write_json
from .run_stats import RunStats

PATH = SAVE_DIR / "guild.json"
VERSION = 2


def card_price(key: str) -> int | None:
    """Loot price of a card that's bought, or None (start / achievement)."""
    unlock = config.CARDS[key].unlock
    return int(unlock[2:]) if unlock.startswith("L:") else None


@dataclass
class Guild:
    loot: int = 0                    # the purse
    total_loot: int = 0              # found over all runs
    guild: dict = field(default_factory=dict)       # upgrade key -> level
    heroes: dict = field(default_factory=dict)      # hero -> {upgrade key -> level}
    cards: set = field(default_factory=set)         # card keys bought
    achievements: set = field(default_factory=set)
    pacts: set = field(default_factory=set)         # pacts bought
    active_pacts: set = field(default_factory=set)  # ...and switched on
    pages: set = field(default_factory=set)         # bestiary pages bought
    kills: dict = field(default_factory=dict)       # enemy key -> kills over all runs

    # --- Save file ----------------------------------------------------------------------

    @classmethod
    def load(cls, path: Path | str = PATH) -> "Guild":
        data = read_json(Path(path))
        g = cls()
        for name in ("loot", "total_loot"):
            v = data.get(name)
            if isinstance(v, int) and not isinstance(v, bool) and v >= 0:
                setattr(g, name, v)
        g.guild = _levels(data.get("guild"), config.GUILD_UPGRADES)
        heroes = data.get("heroes") if isinstance(data.get("heroes"), dict) else {}
        # (A pre-rev-2 save gets everything refunded below instead.)
        g.migrated = data.get("version") == VERSION and g.refund_retired(heroes) > 0
        g.heroes = {h: lv for h in config.HERO_UPGRADES
                    if (lv := _levels(heroes.get(h), config.HERO_UPGRADES[h]))}
        cards = data.get("cards") if isinstance(data.get("cards"), list) else []
        g.cards = {k for k in cards if k in config.CARDS}
        ach = data.get("achievements") if isinstance(data.get("achievements"), list) else []
        g.achievements = {a for a in ach if isinstance(a, str)}
        g.pacts = _keys(data.get("pacts"), config.PACTS)
        g.active_pacts = _keys(data.get("active_pacts"), config.PACTS) & g.pacts
        g.pages = _keys(data.get("pages"), config.BESTIARY)
        kills = data.get("kills") if isinstance(data.get("kills"), dict) else {}
        g.kills = {k: v for k, v in kills.items()
                   if k in config.BESTIARY and isinstance(v, int) and not isinstance(v, bool)
                   and v > 0}
        if data and data.get("version") != VERSION:
            g.refund_rev1(data)
        return g

    def refund_retired(self, heroes: dict) -> int:
        """Give back what a save spent on hero upgrades that no longer exist
        (config.RETIRED_UPGRADES: the wizard's lightning ladders, M20). They
        aren't loaded, so once the guild is saved again they're gone and
        this can't pay twice (run.py saves straight away when it paid)."""
        refund = 0
        for hero, retired in config.RETIRED_UPGRADES.items():
            levels = heroes.get(hero)
            if not isinstance(levels, dict):
                continue
            for key, (base, growth, top) in retired.items():
                lv = levels.get(key)
                if isinstance(lv, int) and not isinstance(lv, bool) and lv > 0:
                    refund += sum(round(base * growth ** n) for n in range(min(lv, top)))
        self.loot += refund
        return refund

    def refund_rev1(self, data: dict) -> int:
        """Give back what a pre-rev-2 save spent on upgrades (they changed),
        and clear them. Returns the refund."""
        refund = 0

        def spent(levels, prices, default=None):
            total = 0
            if isinstance(levels, dict):
                for key, lv in levels.items():
                    price = prices.get(key, default)
                    if price and isinstance(lv, int) and not isinstance(lv, bool) and lv > 0:
                        base, growth, top = price
                        total += sum(round(base * growth ** n) for n in range(min(lv, top)))
            return total

        refund += spent(data.get("guild"), config.REV1_PRICES["guild"])
        heroes = data.get("heroes")
        if isinstance(heroes, dict):
            for levels in heroes.values():
                refund += spent(levels, config.REV1_PRICES["hero"], (100, 1.6, 3))
        self.guild, self.heroes = {}, {}
        self.loot += refund
        return refund

    def save(self, path: Path | str = PATH) -> bool:
        return write_json(Path(path), {
            "version": VERSION, "loot": self.loot, "total_loot": self.total_loot,
            "guild": self.guild, "heroes": self.heroes, "cards": sorted(self.cards),
            "achievements": sorted(self.achievements), "pacts": sorted(self.pacts),
            "active_pacts": sorted(self.active_pacts), "pages": sorted(self.pages),
            "kills": self.kills})

    # --- Levels and prices --------------------------------------------------------------

    def level(self, key: str, hero: str | None = None) -> int:
        """Levels owned of a guild upgrade (hero=None) or a hero's upgrade."""
        if hero is None:
            return self.guild.get(key, 0)
        return self.heroes.get(hero, {}).get(key, 0)

    @staticmethod
    def spec(key: str, hero: str | None = None):
        return config.GUILD_UPGRADES[key] if hero is None else config.HERO_UPGRADES[hero][key]

    def next_cost(self, key: str, hero: str | None = None) -> int | None:
        """Price of the next level, or None once maxed."""
        spec, lv = self.spec(key, hero), self.level(key, hero)
        return None if lv >= spec.max_level else spec.cost(lv)

    def buy_upgrade(self, key: str, hero: str | None = None) -> bool:
        cost = self.next_cost(key, hero)
        if cost is None or cost > self.loot:
            return False
        self.loot -= cost
        levels = self.guild if hero is None else self.heroes.setdefault(hero, {})
        levels[key] = levels.get(key, 0) + 1
        return True

    def unlocked(self, key: str) -> bool:
        unlock = config.CARDS[key].unlock
        if unlock == "start":
            return True
        if unlock.startswith("A:"):
            return unlock[2:] in self.achievements
        return key in self.cards

    def buy_card(self, key: str) -> bool:
        price = card_price(key)
        if price is None or self.unlocked(key) or price > self.loot:
            return False
        self.loot -= price
        self.cards.add(key)
        return True

    # --- The archivist's pacts and bestiary -----------------------------------------------

    def buy_pact(self, key: str) -> bool:
        price = config.PACTS[key].price
        if key in self.pacts or price > self.loot:
            return False
        self.loot -= price
        self.pacts.add(key)
        return True

    def toggle_pact(self, key: str) -> bool:
        """Switch an owned pact on or off; returns whether it's on."""
        if key not in self.pacts:
            return False
        self.active_pacts ^= {key}
        return key in self.active_pacts

    def known(self, kind: str) -> bool:
        """A bestiary page is yours: bought, or enough of them slain."""
        return kind in self.pages or self.kills.get(kind, 0) >= config.BESTIARY_KILLS

    def buy_page(self, kind: str) -> bool:
        price = config.BESTIARY[kind][0]
        if self.known(kind) or price > self.loot:
            return False
        self.loot -= price
        self.pages.add(kind)
        return True

    def known_pages(self) -> set[str]:
        return {k for k in config.BESTIARY if self.known(k)}

    def unlocked_cards(self) -> set[str]:
        return {k for k in config.CARDS if self.unlocked(k)}

    # --- Runs ---------------------------------------------------------------------------

    def meta_steps(self, hero: str) -> list[tuple[str, str, float]]:
        """Everything bought, as card-style steps for the run's hero."""
        steps = []
        for key, lv in sorted(self.guild.items()):
            steps += list(config.GUILD_UPGRADES[key].mods) * lv
        for key, lv in sorted(self.heroes.get(hero, {}).items()):
            steps += list(config.HERO_UPGRADES[hero][key].mods) * lv
        return steps

    def bank_run(self, run: RunStats) -> int:
        """Put a finished run's loot in the purse; returns how much."""
        found = int(run.loot)
        self.loot += found
        self.total_loot += found
        return found


def _levels(data, specs: dict) -> dict:
    if not isinstance(data, dict):
        return {}
    out = {}
    for key, v in data.items():
        if key in specs and isinstance(v, int) and not isinstance(v, bool) and v > 0:
            out[key] = min(v, specs[key].max_level)
    return out


def _keys(data, registry: dict) -> set:
    return {k for k in data if k in registry} if isinstance(data, list) else set()
