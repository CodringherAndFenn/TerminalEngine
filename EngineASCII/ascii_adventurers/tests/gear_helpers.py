"""Test helpers for the gear era (M28.1): the older milestone tests check
what a card's effect does, so they put cards straight on the hero, and ask
"could this be offered" across bases and affixes alike."""

from collections import Counter

from ascii_adventurers import config
from ascii_adventurers.players import cards, gear
from ascii_adventurers.players.stats import HeroStats


def use_cards(s, *taken, player=None):
    """Add these (card key, rarity) effects to the hero, ignoring slots
    (two head powers at once, a stat card six times...); like taking the
    cards did, each call adds to the last."""
    p = player or s.me
    held = getattr(p, "_test_cards", [])
    held += list(taken)
    p._test_cards = held
    lo = cards.build_loadout(p.stats.hero, held, p.meta, p.progress.level)
    s._use_loadout(p, lo)


def offerable(hero, weapon, taken=None, stats=None, banished=(), level=None):
    """What the cards' eligible() answered: the bases the hero may be
    offered (wearing every base in `taken`) plus the affixes some piece may
    roll (any slot, at the rarity each first shows)."""
    stats = stats if stats is not None else HeroStats()
    taken = taken if taken is not None else Counter()
    eq = gear.Equipment()
    for key in taken:
        if key in config.GEAR and eq.free(gear.base_slot(key)) is not None:
            eq.take(gear.Offer(key, config.CARDS[key].rarity, (), "new"))
    out = gear.eligible(hero, weapon, eq, stats, banished, level=level)
    w = weapon
    for slot_key in ("seeker", "riposte"):              # any slot, and the boots
        for rarity in ("uncommon", "rare", "legendary"):
            for a in gear.affix_pool(slot_key, rarity, hero, w, stats, eq.counts()):
                if a not in out and a not in banished:
                    out.append(a)
    return out
