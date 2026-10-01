"""
meta/guild.py -- meta progression: the loot purse and what it has bought
(save/guild.json).

Loot found in a run is kept in full however the run ends and lands in the
purse (bank_run). The purse buys, in the Guild Hall (scenes/guild_hall.py):
  * guild upgrades (config.GUILD_UPGRADES), shared by every hero;
  * hero upgrades (config.HERO_UPGRADES), one tree per hero;
  * card unlocks: cards whose `unlock` is "L:<price>" join the offer pool.
Achievement cards ("A:<name>") unlock when `achievements` holds the name.

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
        g.heroes = {h: lv for h in config.HERO_UPGRADES
                    if (lv := _levels(heroes.get(h), config.HERO_UPGRADES[h]))}
        cards = data.get("cards") if isinstance(data.get("cards"), list) else []
        g.cards = {k for k in cards if k in config.CARDS}
        ach = data.get("achievements") if isinstance(data.get("achievements"), list) else []
        g.achievements = {a for a in ach if isinstance(a, str)}
        return g

    def save(self, path: Path | str = PATH) -> bool:
        return write_json(Path(path), {
            "loot": self.loot, "total_loot": self.total_loot, "guild": self.guild,
            "heroes": self.heroes, "cards": sorted(self.cards),
            "achievements": sorted(self.achievements)})

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
