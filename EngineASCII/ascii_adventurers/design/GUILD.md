# AsciiAdventurers — Loot and the Guild Hall

Status: **rev 2, approved and BUILT in M16 (2026-10-01).** Rev 1 (built in M15) was a first pass; this revision follows your notes:
- **Nothing repeats inside the hall.** No stat or effect is sold by two places (guildmaster vs trainer) or by two heroes' trainers. Cards *may* overlap with the hall (that's how "your hero starts stronger over time" works).
- **Longer ladders, bigger prices.** Upgrades go to 10-20 levels; a full hall is a long-term goal.
- **The archivist grows with the game.** Its shelves get new sections and entries every milestone.

All numbers live in `config.py` (`GUILD_UPGRADES`, `HERO_UPGRADES`, `PACTS`, `BESTIARY`, `ACHIEVEMENTS`); tune freely. Section 6 notes the choices made while building.

---

## 1. Loot

Unchanged from M15, except the rate:
- A kill by a hero (weapon, statuses, spells) is worth loot at once: enemy XP × **LOOT_PER_XP** × (1 + loot bonus). Rune shards fly from the body to the hero.
- It's kept in full however the run ends.
- **Proposal: LOOT_PER_XP 0.5 → 1.0**, because the prices below are ~10× rev 1. An enemy averages ~7 XP:

| Run | Kills (rough) | Loot (rate 1.0) |
|---|---|---|
| 5 min, early death | 150 | ~1,000 |
| 15 min | 450 | ~3,000 |
| 30 min | 900+ | ~6,500+ |

Pacts (section 4.3) add +15% to +40% on top.

**Pacing target:** the first purchase after your first run; something worth buying after almost every run; the whole hall in roughly **40-60 runs**. The total cost of everything below is ~230,000 loot.

## 2. The guildmaster: shared ladders

Each line is the **only** place in the hall that sells its effect. A level costs `base × growth^(levels owned)`.

| Upgrade | Per level | Levels | Max total | First → last price | Ladder total |
|---|---|---|---|---|---|
| Whetstone | +2% damage | 15 | +30% | 150 → 1,926 | 10,805 |
| Drill Yard | +1.5% attack speed | 15 | +22.5% | 150 → 1,926 | 10,805 |
| Infirmary | +5 max HP | 20 | +100 HP | 100 → 2,321 | 14,663 |
| Armory | +1 armor | 15 | +15 (≈27% less damage) | 150 → 1,926 | 10,805 |
| Cobbler | +1% move speed | 10 | +10% | 200 → 1,490 | 6,650 |
| Old Maps | +3% XP | 10 | +30% | 150 → 1,118 | 4,988 |
| Treasure Map | +4% loot | 15 | +60% | 200 → 2,568 | 14,408 |
| Lodestone | +10% pickup radius | 10 | +100% | 100 → 745 | 3,324 |
| Stable (P6) | +5% riding speed, mount back 1 s sooner after a fall | 5 | +25%, 5 s | 250 → 714 | 2,261 |
| Lucky Shrine | +2 luck | 15 | +30 | 200 → 2,568 | 14,408 |
| Fortune Teller | +1 reroll a run | 5 | 8 rerolls | 400 → 4,199 | 8,948 |
| Exile Ledger | +1 banish a run | 5 | 5 banishes | 600 → 6,299 | 13,422 |
| Recruit's Kit 🆕 | start runs one level higher (one free card pick) | 3 | level 4 | 1,500 → 6,000 | 10,500 |
| Second Chance 🆕 | once per run, revive at 30% HP when you fall | 2 | 2 revives | 3,000 → 7,500 | 10,500 |
| Arcane Wing | +1 spell slot (the 4th) | 1 | 4 slots | 8,000 | 8,000 |

Guildmaster total: **~142,000**.

## 3. The trainer: one tree per hero, no two alike

Rev 1 gave every hero the same Mastery (+damage) and Toughness (+HP), which repeat the guildmaster. Rev 2 trees only touch **that hero's own weapon or trick**. No effect appears in two heroes' trees or in the guildmaster's list. 4 upgrades per hero, ~8,400 loot per hero to max, **~42,000** in all.

| Hero | Upgrade | Per level | Levels | Base / growth |
|---|---|---|---|---|
| **wizard** | Extra Dart (M20; was Forked Bolt) | +1 dart per cast | 2 | 1,200 / 2.0 |
| | Swift Darts (M20; was Long Arc) | darts fly +6% faster | 5 | 150 / 1.3 |
| | Tracking (M20; was Grounding) | darts turn 10% faster | 5 | 150 / 1.3 |
| | Capacitor | the first cast after 2 s without casting deals +50% | 3 | 400 / 1.6 |

M20: levels bought in Forked Bolt, Long Arc or Grounding are refunded once, at what they cost.
| **dwarf** | Axe Juggler | +1 axe per throw | 2 | 1,200 / 2.0 |
| | Strong Arm | axes fly +6% farther | 5 | 150 / 1.3 |
| | Quick Catch | axes fly back 10% faster and are caught from farther | 5 | 150 / 1.3 |
| | Homecoming | +15% axe damage on the way back | 3 | 400 / 1.6 |
| **huntress** | Barbed Tips | arrows pierce +1 enemy | 2 | 1,200 / 2.0 |
| | Eagle Eye | +3% crit chance | 5 | 150 / 1.3 |
| | Fletcher | arrows fly 8% faster | 5 | 150 / 1.3 |
| | Quiver | every 8th arrow is free: two fly at once (−1 per level after the first) | 3 | 400 / 1.6 |
| **princess** | Coronation | +1 color in the fan | 2 | 1,200 / 2.0 |
| | Royal Grace | +3% evasion | 5 | 150 / 1.3 |
| | Bright Colors | colors are 10% bigger (easier to hit with) | 5 | 150 / 1.3 |
| | Royal Decree | start every run with one rare card of your choice from three | 3 (2nd: epic, 3rd: legendary) | 400 / 1.6 |
| **bard** | Resonance | +5% area | 5 | 150 / 1.3 |
| | Lullaby | regain 0.2 HP per second | 5 | 150 / 1.3 |
| | Opening Act | for the first 60 s of a run, beats deal ×2 | 3 (+60 s per level) | 400 / 1.6 |
| | Encore Tour | every 5th level-up offers 4 cards instead of 3 (every 4th at level 2) | 2 | 1,200 / 2.0 |

> The bard was the hard one: his lute has no projectiles, range or crit hook of its own. An alternative 4th is **Fan Club** (allies within his reach regain HP, for co-op).
>
> **Question:** each hero's first upgrade is a "+1 of my weapon's thing" (jump, axe, pierce, color). They're different effects, but the same pattern. Keep, or swap some for other tricks?
ANSWER: keep them

Uniqueness check: crit only in Eagle Eye; evasion only in Royal Grace; area only in Resonance; regen only in Lullaby. None of those are in the guildmaster's list, and no hero repeats another's trick.

## 4. The archivist: a library that grows

The archive becomes a set of **shelves (tabs)**. Each milestone adds entries; new shelves open as the game grows. Left/Right switches shelf.

### 4.1 Cards (M16)

Every catalog card marked `L:`, the ~32 "payoff/capstone" cards (see `CARDS.md`). Prices are **raised** with the bigger economy:

| Card kind | Old price | New price |
|---|---|---|
| hero payoffs (Phase Darts, Hunter's Mark...) | 250-400 | 1,500-2,500 |
| tag payoffs, combos (Virulence, Thermal Shock...) | 300-600 | 2,000-4,000 |
| capstones (legendary) | 1,000 | 6,000 |

About **70,000** for every card.

### 4.2 Spells (M16)

The 4 locked spells (Storm Cloud, Healing Totem, Ward Charm, Bone Turret): 2,000-3,000 each.

### 4.3 Pacts 🆕 (M16)

Run modifiers for more loot: buy a pact once, then switch it on or off at the **dungeon gate** before a run. They stack.

| Pact | Effect | Loot bonus | Price |
|---|---|---|---|
| Pact of Blood | enemies deal +25% damage | +20% | 1,500 |
| Pact of the Horde | +30% more enemies | +20% | 1,500 |
| Pact of Haste | enemies move and attack 15% faster | +20% | 2,500 |
| Pact of Famine | no regen; skipping a card doesn't heal | +15% | 2,500 |
| Pact of Glass | you have −40% max HP | +40% | 4,000 |
| Pact of the Veteran | enemies start 10 levels tougher | +30% | 5,000 |

PACT CHANGE: pacts should cost money, and we will add about 14 more with time. they are just a way for the game to be played at an insane difficulty level

### 4.4 Bestiary 🆕 (M16)

One entry per enemy type (12 now, more with every new enemy and boss).
- An entry becomes **readable** after you've slain 25 of that enemy. same effect as buying
- **Buying** it (500-1,500) shows its notes (HP, damage, behaviour, weak side) and gives **+10% damage against that enemy type** for good. 

A natural "many things over time" shelf: every new monster adds a page.

### 4.4b Journal 🆕 (M22.6, 2026-10-05)

The archivist's fifth shelf. Nothing to buy: one row per quest (`config.QUESTS`), written when you beat that quest's boss (`Guild.record_quest`, saved as `journal` in guild.json).
- A row shows the quest's title, its biome, the boss, your fastest fight and how many times you've beaten it (`x3`).
- The highlighted row adds the giver's story (their offer lines) and every hero who has beaten it.
- A co-op kill counts as one win, with every hero who was there.
- Quests not completed yet show as `???` with their biome, so you can see how many are left.

### 4.5 Later shelves (proposals, not M16) Keep the shelves ideas in memory as possible future milestones, but for now do not implement

| Shelf | Opens with | What |
|---|---|---|
| Charts | M17 quests | reveal where each biome's quest and boss lair are on the big map |
| Relics | M17-18 bosses | bosses drop relic fragments; the archivist restores them into permanent once-per-run powers |
| Wardrobe | any time (cheap) | colour variants for each hero (2-3 each), shot trail colours |
| Heroes | when new heroes arrive | recruit new adventurers |
| Lore | any time | short tales of the island, unlocked by exploring biomes (cosmetic, a loot sink) |

## 5. What changes from rev 1 (already built in M15)

- Guildmaster: same 12 ideas, longer ladders, smaller steps, bigger prices; **+ Recruit's Kit, Second Chance**.
- Trainer: Mastery and Toughness are **removed** (they repeated Whetstone and Infirmary). Stonehide (armor = Armory), Fleet Foot (move = Cobbler), Static Focus (crit = Eagle Eye) and Radiance are **replaced** with hero-trick upgrades.
- Archivist: tabs; card prices ×5-6; **+ spells, pacts, bestiary**.
- `LOOT_PER_XP` 0.5 → 1.0.
- Saves: any rev-1 levels bought are refunded into the purse when M16 loads an old save, so nothing is lost.

## 6. M16 implementation notes

- The bard's regen upgrade is called **Soothing Strings** (the card B2 is already "Lullaby").
- **Royal Decree:** your first offer of a run (an extra pick) only holds cards of that rarity or better: rare, then epic, then legendary.
- **Encore Tour:** level 1 makes every 5th offer 4 cards; level 2 every 4th. Stacks with Fortune.
- **Quiver:** level 1 every 8th arrow has a twin, level 2 every 7th, level 3 every 6th.
- **Bright Colors:** each level (+10%) widens a color's hit circle by 0.6 px (6 px at +100%).
- **Capacitor:** +50% per level on the first attack after 2 s without attacking (any weapon, but it's the wizard's).
- **Pacts:** the loot bonus is kept (switch any on for more loot; they're there for brutal difficulty). Pact of the Horde adds enemies to chunks rostered from then on; Haste, Blood and the Veteran apply to enemies as they wake.
- **Bestiary:** kills are counted over all runs (dev mode doesn't save them). A page known before a run gives its +10% at once; one that reaches 25 kills during a run turns on immediately.
- **Old saves:** a save from before rev 2 gets every upgrade level refunded at rev-1 prices; cards bought stay bought.
- The archive scrolls (mouse wheel too); the gate panel lists only pacts you own.
