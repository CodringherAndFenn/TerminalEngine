"""
ui/gear_stats.py -- the gear screen's STATS page (design/GEAR.md 8, 9;
M28.3a): each weapon and spell's damage worked out through the buckets
(players/stats.py), then every total stat.

`damage_lines(hero)` and `total_lines(hero)` are plain (text, colour)
lines, so tests can read them; GearScreen draws them in two columns.

A hit is base x (1 + A damage) x (1 + T tag damage) x M (the "xN" cards).
Bonuses that only count sometimes (Point Blank up close, Wildfire on a
burning enemy, Hunter's Mark...) aren't in the numbers: a note says so.
"""

from __future__ import annotations

from .. import config, palette
from ..players.stats import spell_params

HEAD = palette.CARD_TITLE
TEXT = palette.CARD_TEXT
NOTE = palette.CARD_TAG

# What one of a weapon's shots is called, by its look.
_UNIT = {"dart": "dart", "longarrow": "arrow", "prism": "color", "axe": "axe"}
# A spell's numbers worth showing besides its damage, and how to say them.
_EVERY = ("interval", "bite", "rehit")


def hit(stats, base: float, tags) -> tuple[float, str]:
    """(damage, how it's worked out) of one hit of `base` with `tags`."""
    a, t, m = stats.damage, stats.tag_bonus(tags), stats.damage_mult
    parts = [f"{base:g}"]
    if abs(a) > 1e-9:
        parts.append(f"(1 + {a:.2f} damage)")
    if abs(t) > 1e-9:
        named = [g for g in tags if stats.tag_damage.get(g)]
        parts.append(f"(1 + {t:.2f} {'/'.join(named)})")
    if abs(m - 1) > 1e-9:
        parts.append(f"{m:.2f}")
    value = base * (1 + a) * (1 + t) * m
    return value, (" x ".join(parts) + f" = {value:.1f}" if len(parts) > 1 else f"{value:.1f}")


def _crit(stats, value: float) -> str:
    chance = max(0.0, min(1.0, stats.crit_chance))
    return f"  crit {chance:.0%}: x{stats.crit_damage:.2f} = {value * stats.crit_damage:.1f}"


def damage_lines(hero) -> list[tuple[str, tuple]]:
    stats = hero.stats
    spec = hero.weapon.spec
    out: list[tuple[str, tuple]] = [("DAMAGE", HEAD)]
    rate = 1 / max(1e-6, spec.fire_interval)
    if spec.kind == "pulse":
        out.append((f"{spec.name}: a beat every {spec.fire_interval:.2f} s, "
                    f"reach {spec.reach:.1f}", TEXT))
        value, how = hit(stats, spec.damage, spec.tags)
    else:
        shell = spec.shell
        unit = _UNIT.get(shell.look, "shot")
        n = max(1, spec.pellets)
        out.append((f"{spec.name}: {n} {unit}{'s' if n > 1 else ''}, {rate:.1f} a s", TEXT))
        value, how = hit(stats, shell.damage, spec.tags)
        how += f" a {unit}"
    out.append(("  " + how, TEXT))
    out.append((_crit(stats, value), TEXT))
    for key, level in sorted(stats.spells.items()):
        out += _spell(stats, key, level)
    if stats.sources:
        s = stats.status_scale("")
        line = f"statuses: {', '.join(sorted(stats.sources))}"
        out.append((line, TEXT))
        extra = f"  x{s:.2f} damage" if abs(s - 1) > 1e-9 else "  plain damage"
        if stats.statuses:
            chance = config.STATUS_BASE_CHANCE + stats.status_chance
            extra += f", {chance:.0%} of hits"
        out.append((extra, TEXT))
    out.append(("", TEXT))
    out.append(("bonuses that only count sometimes", NOTE))
    out.append(("(up close, on burning enemies...) come on top", NOTE))
    return out


def _spell(stats, key: str, level: int) -> list[tuple[str, tuple]]:
    spec = config.SPELLS[key]
    p = spell_params(key, level, stats.spell_boost.get(key, 0.0))
    roman = ("I", "II", "III", "IV", "V")[min(level, 5) - 1]
    head = f"{spec.name} {roman}"
    every = next((p[k] for k in _EVERY if isinstance(p.get(k), (int, float)) and p[k] > 0), None)
    if every is not None:
        head += f", every {every * stats.cooldown_scale:.2f} s"
    if isinstance(p.get("radius"), (int, float)):
        head += f", {p['radius'] * stats.area_scale:.1f} tiles"
    out = [(head, TEXT)]
    dmg = p.get("damage")
    if key == "split_arrow":
        out.append((f"  each split arrow x{dmg:.2f} of the arrow", TEXT))
    elif isinstance(dmg, (int, float)) and dmg > 0:
        value, how = hit(stats, dmg, spec.tags)
        out.append(("  " + how + " a hit", TEXT))
    for name, label in (("heal", "heals"), ("shield", "shield")):
        if isinstance(p.get(name), (int, float)) and p[name] > 0:
            out.append((f"  {label} {p[name]:.1f}", TEXT))
    if key == "thorn_mail":
        out.append((f"  reflects {p['flat']:g} + {p['share']:.0%} of each hit", TEXT))
    return out


def total_lines(hero) -> list[tuple[str, tuple]]:
    st = hero.stats
    armor = st.armor
    cut = armor / (abs(armor) + config.ARMOR_K) if armor else 0.0
    out: list[tuple[str, tuple]] = [("STATS", HEAD)]
    rows = [
        f"max HP {round(hero.max_hp)}",
        f"armor {armor:g}" + (f" ({'-' if cut >= 0 else '+'}{abs(cut):.0%} taken)" if armor else ""),
        f"move {_pct(st.move)}",
        f"attack speed {_pct(st.attack_speed)}"
        + (f", x{st.interval_mult:.2f} wait" if abs(st.interval_mult - 1) > 1e-9 else ""),
        f"crit {max(0.0, min(1.0, st.crit_chance)):.0%}, x{st.crit_damage:.2f}",
        f"area {_pct(st.area)}",
        f"duration {_pct(st.duration)}",
        f"pickup {st.pickup_radius:.1f} tiles",
        f"rolls {st.max_rolls}, back in {st.roll_recharge:.1f} s",
    ]
    extra = [
        (st.evasion, f"evasion {st.evasion:.0%}"),
        (st.regen, f"regen {st.regen:.1f} HP a s"),
        (st.lifesteal, f"lifesteal {st.lifesteal:.0%}"),
        (st.spell_cooldown, f"spell cooldowns -{st.spell_cooldown:.0%}"),
        (st.pellets, f"projectiles +{round(st.pellets)}"),
        (st.pierce, f"pierce +{round(st.pierce)}"),
        (st.range, f"range {_pct(st.range)}"),
        (st.shot_speed, f"shot speed {_pct(st.shot_speed)}"),
        (st.status_power, f"status damage {_pct(st.status_power)}"),
        (st.status_chance, f"status chance +{st.status_chance:.0%}"),
        (st.xp, f"XP {_pct(st.xp)}"),
        (st.loot, f"loot {_pct(st.loot)}"),
        (st.luck, f"luck {_pct(st.luck)}"),
        (st.soul_harvest, f"{st.soul_harvest:g} HP a kill"),
    ]
    rows += [text for value, text in extra if value]
    for tag, value in sorted(st.tag_damage.items()):
        if value:
            rows.append(f"{tag} damage {_pct(value)}")
    out += [(r, TEXT) for r in rows]
    return out


def _pct(v: float) -> str:
    return f"{'+' if v >= 0 else '-'}{abs(v):.0%}"
