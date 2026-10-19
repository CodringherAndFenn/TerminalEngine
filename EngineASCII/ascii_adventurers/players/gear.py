"""
players/gear.py -- what a hero wears: slots, pieces, the bag, and the
level-up gear picks (design/GEAR.md, M28.1).

A Piece is a base (config.GEAR, keyed like the card whose effect is its
power), a rarity, a level (+0..GEAR_MAX_LEVEL) and its affixes (plain stat
cards, config.AFFIXES). Equipment holds the worn pieces by slot id -- "main",
"off", "head", "chest", "feet", "ring1", "ring2", "trinket1".. -- and the bag
of spares. Equipment.steps() is everything worn as (stat, op, value) steps
for players/cards.loadout_from_steps, so the effects are the cards' own.

Levels (GEAR.md 15.3): a +1 adds GEAR_LEVEL_GROWTH of the power's main
number (its first helpful "add", or a "mul"'s distance from 1); a spell's
first four +1s are its levels II-V, then its SPELL_GROW number grows; a
power with no number (or GearSpec.grow == "damage") gets GEAR_FLAT_GROWTH
damage a level. Rarity (M28.3a) multiplies on top: GEAR_RARITY_POWER of the
main number, or GEAR_RARITY_FLAT of its extra as damage (power_scale,
flat_damage, spell_boost).

Offers (draw_offer). Each piece is a base the hero may get (gates, hero,
unlock met), weighted by its minimum rarity -- its old card rarity -- in the
card weights (luck lifts the rare ones), so strong powers stay rare to
find; then a new piece rolls its rarity like a card did, raised to that
minimum (a legendary stays ~1 in 85). (A single
rarity roll first, as the cards did, left only ~6 common bases for 58% of
the rolls once the plain stats became affixes, M28.1.) A
base you wear comes as +1 (keeping your piece's rarity and affixes), one
whose slot has room as a new piece, otherwise as a swap. Once
GEAR_LEAN_FILLED slots are filled, swaps weigh GEAR_SWAP_WEIGHT; bases
sharing a tag with the build CARD_SYNERGY_WEIGHT; the archetype lean
(config.ARCHETYPES) holds one place; the run's first offer holds a
main-hand piece. Seeded by (seed, player, offer number) like the cards.
"""

from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass, field

from .. import config
from ..specs import WeaponSpec
from ..world.rng import hash_coords
from .cards import (ARCHETYPE_CARDS, ROMAN, build_tags, card_steps, gate_met,
                    leading_archetype, rarity_weights, spell_of)
from .stats import HeroStats

_RANK = {r: i for i, r in enumerate(config.RARITIES)}


def base_slot(key: str) -> str:
    return config.GEAR[key].slot


def slot_kind(slot_id: str) -> str:
    """"ring2" -> "ring", "main" -> "main"."""
    return slot_id.rstrip("0123456789")


def min_rarity(key: str) -> str:
    """The lowest rarity a base drops at: its card's."""
    return config.CARDS[key].rarity


@dataclass
class Piece:
    key: str
    rarity: str
    level: int = 0
    affixes: tuple[str, ...] = ()

    @property
    def name(self) -> str:
        return config.GEAR[self.key].name

    @property
    def slot(self) -> str:
        return base_slot(self.key)


@dataclass(frozen=True)
class Offer:
    """One card in a gear pick: `kind` is "new" (an empty slot), "plus"
    (+1 to the worn piece of this base) or "swap" (its slot is full)."""

    key: str
    rarity: str
    affixes: tuple[str, ...]
    kind: str

    def piece(self) -> Piece:
        return Piece(self.key, self.rarity, 0, self.affixes)


# --- What a piece does ----------------------------------------------------------------


def _main_mod(key: str) -> int | None:
    """Index of the mod a +1 grows, or None (the flat damage rule)."""
    if config.GEAR[key].grow == "damage":
        return None
    for i, (stat, op, val) in enumerate(config.CARDS[key].mods):
        if op == "add" and isinstance(val, (int, float)) and val > 0:
            return i
        if op == "mul":
            return i
    return None


def trick_flags(key: str, level: int) -> list[tuple[str, str, float]]:
    """The flags of the tricks a piece has unlocked: "<key>+3" and so on
    (only for pieces whose tricks are built, config.GEAR_TRICKS)."""
    if key not in config.GEAR_TRICKS:
        return []
    return [(f"{key}+{t}", "flag", 1) for t in config.GEAR_TRICK_LEVELS if level >= t]


def tricks(key: str) -> list[tuple[int, str, str]]:
    """(level, name, text) of a piece's built tricks."""
    return [(t, name, text) for t, (name, text)
            in zip(config.GEAR_TRICK_LEVELS, config.GEAR_TRICKS.get(key, ()))]


def next_trick(key: str, level: int) -> tuple[int, str, str] | None:
    return next((t for t in tricks(key) if t[0] > level), None)


def power_steps(key: str, level: int, rarity: str = "common") -> list[tuple[str, str, float]]:
    """The (stat, op, value) steps of a base's power at `level` and
    `rarity`, with its unlocked tricks' flags (M28.2)."""
    return _power(key, level, rarity) + trick_flags(key, level)


def power_scale(level: int, rarity: str = "common") -> float:
    """x the power's main number: the level's growth times the rarity's
    (M28.3a)."""
    return (1 + config.GEAR_LEVEL_GROWTH * level) * config.GEAR_RARITY_POWER[rarity]


def flat_damage(level: int, rarity: str = "common") -> float:
    """A power with no number: the damage its level and rarity give."""
    return config.GEAR_FLAT_GROWTH * level \
        + (config.GEAR_RARITY_POWER[rarity] - 1) * config.GEAR_RARITY_FLAT


def spell_boost(spell: str, level: int, rarity: str = "common") -> float:
    """How much a trinket's SPELL_GROW number grows: past level V, +10% a
    level; times the rarity's (for a radius its square root, so the area
    grows by it)."""
    r = config.GEAR_RARITY_POWER[rarity]
    if config.SPELL_GROW[spell] == "radius":
        r = r ** 0.5
    past = max(0, level + 1 - config.SPELL_MAX_LEVEL)
    return (1 + config.GEAR_LEVEL_GROWTH * past) * r - 1


def _power(key: str, level: int, rarity: str = "common") -> list[tuple[str, str, float]]:
    c = config.CARDS[key]
    extra = list(config.GEAR[key].mods)
    spell = spell_of(c)
    if spell is not None:
        steps = [(spell, "spell", 1)] * min(level + 1, config.SPELL_MAX_LEVEL)
        boost = spell_boost(spell, level, rarity)
        if boost > 1e-9:
            steps.append((spell, "spell_boost", boost))
        return steps + extra
    steps = card_steps(key, c.rarity)
    drop = config.GEAR_DROP_DOWNSIDE.get(key)
    if drop is not None and level >= drop:              # (a trick: the downside is gone)
        steps = [st for st in steps if not (st[1] == "add" and isinstance(st[2], (int, float))
                                             and st[2] < 0)]
    if level <= 0 and rarity == "common":
        return steps + extra
    main = _main_mod(key)
    if main is None:
        return steps + extra + [("damage", "add", flat_damage(level, rarity))]
    stat, op, val = steps[main]
    scale = power_scale(level, rarity)
    if op == "add":
        val *= scale
    else:
        val = max(config.GEAR_MUL_FLOOR, 1 + (val - 1) * scale)
    steps[main] = (stat, op, val)
    return steps + extra


def affix_steps(key: str, rarity: str) -> list[tuple[str, str, float]]:
    c = config.CARDS[key]
    return card_steps(key, rarity if c.tiered else c.rarity)


def affix_text(key: str, rarity: str) -> str:
    c = config.CARDS[key]
    return c.label(rarity) if c.tiered else c.text


def power_name(key: str) -> str:
    """The power's name: the card's (CARDS.md still reads right)."""
    c = config.CARDS[key]
    spell = spell_of(c)
    return config.SPELLS[spell].name if spell is not None else c.name


def power_text(key: str, level: int = 0, rarity: str = "common") -> str:
    """What the power does, at `level` and `rarity`."""
    c = config.CARDS[key]
    spell = spell_of(c)
    if spell is not None:
        s = config.SPELLS[spell]
        lv = min(level + 1, config.SPELL_MAX_LEVEL)
        text = s.text if lv == 1 else f"{s.text} (level {ROMAN[lv - 1]})"
        boost = spell_boost(spell, level, rarity)
        if boost > 1e-9:
            text += f", +{round(boost * 100)}% {config.SPELL_GROW[spell]}"
        return text
    text = c.label(c.rarity)
    for stat, op, _ in config.GEAR[key].mods:          # a status it brings (the cowl's bleed)
        if op == "status":
            text = _STATUS_TEXT.get(stat, stat) + "; " + text
    if level > 0 or rarity != "common":
        if _main_mod(key) is None:
            text += f"; +{round(flat_damage(level, rarity) * 100)}% damage"
        else:
            text += f" (power +{round((power_scale(level, rarity) - 1) * 100)}%)"
    return text


# "10% of your hits bleed": the text of the card that gives just that status.
_STATUS_TEXT = {c.mods[0][0]: c.text for c in config.CARDS.values()
                if len(c.mods) == 1 and c.mods[0][1] == "status"}


def next_level_text(key: str, level: int, rarity: str = "common") -> str:
    """What the next +1 adds (and the trick it unlocks, if it does)."""
    text = _next_growth(key, level, rarity)
    t = next_trick(key, level)
    if t is not None and t[0] == level + 1:
        text += f", and {t[1].upper()}: {t[2]}"
    return text


def _next_growth(key: str, level: int, rarity: str = "common") -> str:
    c = config.CARDS[key]
    spell = spell_of(c)
    if spell is not None and level + 1 < config.SPELL_MAX_LEVEL:
        return config.SPELLS[spell].levels[level][0]
    if spell is not None:
        more = spell_boost(spell, level + 1, rarity) - spell_boost(spell, level, rarity)
        return f"+{round(more * 100)}% {config.SPELL_GROW[spell]}"
    if _main_mod(key) is None:
        return f"+{round(config.GEAR_FLAT_GROWTH * 100)}% damage"
    more = power_scale(level + 1, rarity) - power_scale(level, rarity)
    return f"power +{round(more * 100)}%"


def salvage_value(piece: Piece) -> int:
    return round(config.GEAR_SALVAGE[piece.rarity] * (1 + config.GEAR_SALVAGE_LEVEL * piece.level))


# --- Equipment ------------------------------------------------------------------------


@dataclass
class Equipment:
    trinkets: int = config.SPELL_SLOTS          # trinket slots (spell slots: the Arcane Wing)
    worn: dict = field(default_factory=dict)     # slot id -> Piece
    bag: list = field(default_factory=list)      # spare Pieces (GEAR_BAG)

    def slot_ids(self) -> list[str]:
        out = []
        for kind in config.GEAR_SLOTS:
            n = config.GEAR_RINGS if kind == "ring" else self.trinkets if kind == "trinket" else 1
            out += [kind] if n == 1 and kind not in ("ring", "trinket") else \
                [f"{kind}{i + 1}" for i in range(n)]
        return out

    def slots_of(self, kind: str) -> list[str]:
        return [s for s in self.slot_ids() if slot_kind(s) == kind]

    def free(self, kind: str) -> str | None:
        return next((s for s in self.slots_of(kind) if s not in self.worn), None)

    def wearing(self, key: str) -> str | None:
        return next((s for s, p in self.worn.items() if p.key == key), None)

    @property
    def filled(self) -> int:
        return len(self.worn)

    def pieces(self) -> list[tuple[str, Piece]]:
        """(slot id, piece) worn, in slot order."""
        return [(s, self.worn[s]) for s in self.slot_ids() if s in self.worn]

    def counts(self) -> Counter:
        """Worn bases (level + 1 each) and affix lines: the gates' "you took
        it" and the archetype lean read this."""
        c: Counter = Counter()
        for _, p in self.pieces():
            c[p.key] += p.level + 1
            for a in p.affixes:
                c[a] += 1
        return c

    def capped(self) -> set[tuple[str, str]]:
        """(slot id, affix) lines past their stat's cap: they show greyed
        out with "(max)" and do nothing."""
        seen: Counter = Counter()
        out = set()
        for slot, p in self.pieces():
            for a in p.affixes:
                seen[a] += 1
                if seen[a] > config.CARDS[a].max_stacks:
                    out.add((slot, a))
        return out

    def steps(self) -> list[tuple[str, str, float]]:
        out = []
        capped = self.capped()
        for slot, p in self.pieces():
            out += power_steps(p.key, p.level, p.rarity)
            for a in p.affixes:
                if (slot, a) not in capped:
                    out += affix_steps(a, p.rarity)
        return out

    # --- Changes (each returns the pieces salvaged, for their loot) ----------------

    def default_slot(self, kind: str) -> str:
        """Where a swap goes when nobody chose: the weakest piece of that kind."""
        return min(self.slots_of(kind), key=lambda s: (_RANK[self.worn[s].rarity],
                                                        self.worn[s].level))

    def _to_bag(self, piece: Piece, drop: int | None) -> list[Piece]:
        """Put a piece in the bag; when it's over GEAR_BAG, `drop` (an index
        into the bag, the new piece last) is salvaged -- the new one if
        None."""
        self.bag.append(piece)
        if len(self.bag) <= config.GEAR_BAG:
            return []
        i = drop if drop is not None and 0 <= drop < len(self.bag) else len(self.bag) - 1
        return [self.bag.pop(i)]

    def stash(self, piece: Piece) -> list[Piece]:
        """A piece straight into the bag (Bountymark Ring +6); a full bag
        salvages it."""
        return self._to_bag(piece, None)

    def take(self, offer: Offer, slot: str | None = None, drop: int | None = None) -> list[Piece]:
        kind = base_slot(offer.key)
        if offer.kind == "plus":
            worn = self.worn[self.wearing(offer.key)]
            worn.level = min(config.GEAR_MAX_LEVEL, worn.level + 1)
            return []
        free = self.free(kind)
        if free is not None:
            self.worn[free] = offer.piece()
            return []
        if slot is None or slot_kind(slot) != kind or slot not in self.worn:
            slot = self.default_slot(kind)
        old = self.worn[slot]
        self.worn[slot] = offer.piece()
        return self._to_bag(old, drop)

    def upgrade(self, slot: str) -> bool:
        p = self.worn.get(slot)
        if p is None or p.level >= config.GEAR_MAX_LEVEL:
            return False
        p.level += 1
        return True

    def can_wear(self, index: int, slot: str) -> bool:
        if not 0 <= index < len(self.bag):
            return False
        p = self.bag[index]
        if slot_kind(slot) != p.slot or slot not in self.slot_ids():
            return False
        other = self.wearing(p.key)
        return other is None or other == slot

    def wear(self, index: int, slot: str) -> bool:
        """A bagged piece into `slot`; what was there takes its place in the bag."""
        if not self.can_wear(index, slot):
            return False
        p = self.bag.pop(index)
        old = self.worn.get(slot)
        self.worn[slot] = p
        if old is not None:
            self.bag.insert(index, old)
        return True

    def salvage(self, where: str, which) -> Piece | None:
        """Take a piece out for good: ("worn", slot id) or ("bag", index)."""
        if where == "worn":
            return self.worn.pop(which, None)
        if where == "bag" and isinstance(which, int) and 0 <= which < len(self.bag):
            return self.bag.pop(which)
        return None


# --- Who may be offered what ----------------------------------------------------------


def eligible(hero_key: str, weapon: WeaponSpec, eq: Equipment, stats: HeroStats | None = None,
             banished=(), unlocked: set | None = None, level: int | None = None) -> list[str]:
    """Bases the hero may be offered: their own (hero-only pieces), unlocked,
    not banished, past their level (capstones), not maxed if worn, and --
    for a base not worn yet -- their gates met."""
    stats = stats if stats is not None else HeroStats()
    tags = build_tags(weapon, stats)
    taken = eq.counts()
    out = []
    for key, g in config.GEAR.items():
        c = config.CARDS[key]
        if key in banished:
            continue
        if c.heroes and hero_key not in c.heroes:
            continue
        if c.kinds and weapon.kind not in c.kinds:
            continue
        if unlocked is not None and key not in unlocked:
            continue
        if level is not None and level < c.min_level:
            continue
        worn = eq.wearing(key)
        if worn is not None:
            if eq.worn[worn].level >= config.GEAR_MAX_LEVEL:
                continue
        elif not all(gate_met(n, stats, tags, taken, weapon)
                     for n in (g.needs if g.needs is not None else c.needs)):
            continue
        out.append(key)
    return out


def affix_pool(key: str, rarity: str, hero_key: str, weapon: WeaponSpec, stats: HeroStats,
               taken: Counter | None = None, unlocked: set | None = None) -> list[str]:
    """Affixes a piece of this base and rarity may roll."""
    tags = build_tags(weapon, stats)
    taken = taken if taken is not None else Counter()
    slot = base_slot(key)
    rank = _RANK[rarity]
    out = []
    for a in config.AFFIXES:
        c = config.CARDS[a]
        if c.tiered:
            if c.tiers[rank] is None:
                continue
        elif rank < _RANK[c.rarity]:
            continue
        if a in config.AFFIX_SLOTS and slot not in config.AFFIX_SLOTS[a]:
            continue
        if c.heroes and hero_key not in c.heroes:
            continue
        if c.kinds and weapon.kind not in c.kinds:
            continue
        if unlocked is not None and a not in unlocked:
            continue
        if not all(gate_met(n, stats, tags, taken, weapon) for n in c.needs):
            continue
        out.append(a)
    return out


def roll_affixes(rng: random.Random, key: str, rarity: str, hero_key: str, weapon: WeaponSpec,
                 stats: HeroStats, taken: Counter | None = None,
                 unlocked: set | None = None) -> tuple[str, ...]:
    pool = affix_pool(key, rarity, hero_key, weapon, stats, taken, unlocked)
    n = min(config.GEAR_AFFIXES[rarity], len(pool))
    picked = rng.sample(pool, n)
    return tuple(a for a in config.AFFIXES if a in picked)


def kind_of(eq: Equipment, key: str) -> str:
    if eq.wearing(key) is not None:
        return "plus"
    return "new" if eq.free(base_slot(key)) is not None else "swap"


def draw_offer(hero_key: str, weapon: WeaponSpec, eq: Equipment, seed: int, player_index: int,
               draw_no: int, stats: HeroStats | None = None, banished=(),
               unlocked: set | None = None, level: int | None = None, size: int | None = None,
               min_rarity_: str | None = None, one_rare: bool = False) -> list[Offer]:
    """Up to `size` (default CARD_OFFER_SIZE + the build's extra cards)
    offers of different bases. `min_rarity_` (Royal Decree, a boss's
    reward) forces new pieces of that rarity or better and leaves out +1s.
    `one_rare` (Fourleaf Ring +3, Clover): if none is rare or better, the
    last free place is redrawn as a new piece of rare or better.
    The run's first draw (`draw_no` 0) holds a main-hand piece."""
    stats = stats if stats is not None else HeroStats()
    rng = random.Random(hash_coords(seed or 0, 0x6EA2, player_index, draw_no))
    pool = eligible(hero_key, weapon, eq, stats, banished, unlocked, level)
    tags = build_tags(weapon, stats)
    taken = eq.counts()
    weights = rarity_weights(stats.luck)
    n_rar = len(config.RARITIES)
    floor = _RANK[min_rarity_] if min_rarity_ is not None else 0
    if floor:
        weights = [w if i >= floor else 0.0 for i, w in enumerate(weights)]
        pool = [k for k in pool if eq.wearing(k) is None]
    if size is None:
        size = config.CARD_OFFER_SIZE + round(stats.offer_size)
    lean_swaps = eq.filled >= config.GEAR_LEAN_FILLED

    def draw(among: list[str]) -> Offer | None:
        """A base first, weighted by its minimum rarity's weight (luck lifts
        the rare ones; worn bases count at their own); then, for a new
        piece, its rarity: rolled like a card's, raised to its minimum."""
        if not among:
            return None
        w = []
        for k in among:
            x = weights[_RANK[min_rarity(k)]]
            if config.CARD_SYNERGY_WEIGHT and tags & set(config.CARDS[k].tags):
                x *= config.CARD_SYNERGY_WEIGHT
            if lean_swaps and kind_of(eq, k) == "swap":
                x *= config.GEAR_SWAP_WEIGHT
            w.append(x)
        if not any(w):
            w = [1.0] * len(among)
        key = rng.choices(among, w)[0]
        worn = eq.wearing(key)
        if worn is not None:
            p = eq.worn[worn]
            return Offer(key, p.rarity, p.affixes, "plus")
        rank = max(rng.choices(range(n_rar), weights)[0], _RANK[min_rarity(key)])
        rarity = config.RARITIES[rank]
        return Offer(key, rarity, roll_affixes(rng, key, rarity, hero_key, weapon, stats,
                                               taken, unlocked), kind_of(eq, key))

    offer: list[Offer] = []
    first: list[list[str]] = []
    if draw_no == 0:
        first.append([k for k in pool if base_slot(k) == "main"])
    lean = leading_archetype(taken)
    if lean is not None:
        first += [[k for k in pool if k in ARCHETYPE_CARDS[lean]]] * config.ARCHETYPE_SLOTS
    for among in first:
        if len(offer) >= size:
            break
        got = draw([k for k in among if k in pool])
        if got is not None:
            offer.append(got)
            pool.remove(got.key)
    placed = len(offer)
    while pool and len(offer) < size:
        got = draw(pool)
        if got is None:
            break
        offer.append(got)
        pool.remove(got.key)
    rare = _RANK["rare"]
    if one_rare and offer and not any(_RANK[o.rarity] >= rare for o in offer):
        weights = [w if i >= rare else 0.0 for i, w in enumerate(weights)]
        got = draw([k for k in pool if eq.wearing(k) is None])
        if got is not None:
            offer[-1] = got
    if placed:
        rng.shuffle(offer)          # the main-hand / archetype piece isn't always first
    return offer
