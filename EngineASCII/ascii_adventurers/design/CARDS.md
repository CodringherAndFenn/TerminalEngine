# AsciiAdventurers — Card Catalog

Status: **rev 2, approved and BUILT in M16 (2026-10-01): all 101 cards. M18 (2026-10-02) added the dodge roll and 11 roll cards (section 6.10, 112 in all), gated Lingering, replaced three spell levels and added the archetype lean (section 14). M19 (2026-10-02) added multiple projectiles for every hero: 5 pattern cards, 4 hero cards (6.11, 121 in all) and the fan rule (section 15).** Rev 1's first 48 cards were built in M14. Rev 2 applies the "no repeating upgrades" rule (section 0, enforced by a test); every change is listed in section 12, and section 13 notes the choices made while building.

Based on `../../survivorlike_upgrade_design_guide.md` (section numbers below refer to it).

Build model (your choice): each hero has **one signature weapon**, plus up to **3 spells/items** that cards grant (a 4th slot can be bought in the Guild). Weapons and spells carry **tags**, so if extra weapon slots arrive later, every tag card already works with them.

---

## 0. The no-repeats rule (rev 2)

1. **Each plain stat is sold by exactly one card**: the generic card for it (section 6.1). "+armor" is only Thick Hide, "+attack speed" only Quick Hands, "+projectile" only Multishot, "+pierce" only Piercing, "+status chance" only Affliction.
2. **Hero cards change how that hero's weapon works**, never a plain stat (no more "beats reach 25% farther" next to Long Reach).
3. **Trade-offs, conditionals, scaling and triggers** may touch a stat only through their own condition or rule, and no two do the same thing.
4. **Every "×N damage"** has its own condition or cost (Heavy Axe: slower; Glass Cannon: less HP).
5. Cards *may* overlap with the Guild Hall: the hall makes heroes start stronger over time; cards shape the run.

## 1. Stat layer

These stats are the "nouns" every card modifies. Base values are per hero unless noted. A 🆕 marks a stat that doesn't exist in the code yet.

| Stat | Base | Cap / curve | Notes |
|---|---|---|---|
| damage % | +0% | — | additive bucket A (see 1.1) |
| attack speed % | +0% | interval ≥ 0.08 s | as now (`MIN_INTERVAL`) |
| 🆕 crit chance | 5% | 100% (overflow: K1) | crits never apply to status ticks |
| 🆕 crit damage | ×1.5 | — | |
| projectiles (pellets) | weapon | — | the fan widens with each one |
| pierce | weapon | — | axes pierce everything already |
| range % | +0% | — | shot range, pulse/melee reach |
| shot speed % | +0% | — | |
| 🆕 area % | +0% | ×3 | pulses, auras, explosions, novas |
| 🆕 duration % | +0% | — | statuses, spells, buffs |
| 🆕 status potency % | +0% | — | bucket S: status damage only |
| status chance | +0% | 100% | rev 2: each status you have rolls 10% + this, per hit (Affliction is the only card that raises it) |
| 🆕 spell cooldown % | +0% | −60% | |
| max HP | 100 (dwarf 120) | — | |
| 🆕 armor | 0 | reduction = a / (a + 40), so 40 armor = 50% | can go negative (more damage taken) |
| 🆕 evasion (was "dodge"; renamed in M18 for the dodge roll) | 0% | 60% | |
| regen | 0 HP/s | — | |
| lifesteal | 0% | 15% | |
| 🆕 shield | 0 | — | absorbs hits; recharges after 4 s without being hit |
| move speed % | +0% | +80% | |
| 🆕 pickup radius | 1.5 tiles | — | XP gems, later loot and items |
| 🆕 XP gain % | +0% | — | |
| 🆕 loot gain % | +0% | — | |
| 🆕 luck | 0 | — | shifts rarity odds (section 5) |
| 🆕 rerolls / banishes / skips | 3 / 0 / ∞ | — | per run; the Guild adds more |

### 1.1 Damage buckets (guide 3.2)

```
hit = weapon base
    × (1 + A)          A = all "+X% damage" cards, conditionals, scaling (they add)
    × (1 + T)          T = tag cards: "+X% fire / physical / arcane..." (they add)
    × crit             ×crit damage if the hit crits
    × M1 × M2 ...      every "×N damage" card multiplies on its own (rare+ only)
    × vulnerability    shocked (+15%), marked (×2)...

status tick = status base × (1 + S) × (1 + T)     no crit, no A
```

Card text keeps the buckets readable: **"+20% damage"** always means bucket A, and **"×1.3 damage"** always means its own multiplier. Statuses get their own bucket (S), as in DRG:S, which turns them into a real archetype that needs its own investment.

## 2. Tags

| Tag | Has it from the start |
|---|---|
| `projectile` | wizard, princess, huntress, dwarf |
| `area` | bard |
| `physical` | huntress, dwarf |
| `lightning` | wizard |
| `arcane` | princess, bard |
| `fire` `frost` `poison` | (only from cards/spells) |
| `summon` | (only from spells) |
| `orbit` | (only from spells) |

Tag cards are offered only once you own something with that tag (a weapon or spell), so an offer is never dead.

## 3. Statuses

All status damage is bucket S. Stacks refresh the duration. Bosses take statuses at half strength and can't be frozen (they're slowed instead).

| Status | Tag | Effect (base) |
|---|---|---|
| **Burn** | fire | 4 dmg/s per stack, 3 s, up to 5 stacks |
| **Poison** | poison | 2 dmg/s per stack, 6 s, up to 5 stacks (more with Virulence) |
| **Chill** | frost | −10% move/attack speed per stack. 5 stacks turn into **Freeze** (1.5 s, can't act) |
| **Shock** | lightning | takes +15% damage from everything, 2 s |
| **Bleed** | physical | 3 dmg/s per stack, 4 s, up to 5. Ticks ×2 while the enemy moves (Hemorrhage) |

**Elemental combos** (guide 4.14), unlocked by combo cards:
- **Thermal Shock:** an enemy that is burning and chilled at once bursts for 10 damage per burn stack (bucket S) in a 2-tile radius; this uses up its chill.
- **Toxic Current:** shock spreads poison stacks to 2 nearby enemies.

## 4. Spells / items (granted by cards)

A spell card is an **enabler**. Its first pick grants the spell; picking it again levels it up (up to 5). Each level gives one of: +damage, +count, +area or −cooldown, shown on the card. You have 3 slots (4 via the Guild). Once they're full, only spells you own are offered.

| Spell | Tags | Level 1 | Fits |
|---|---|---|---|
| Orbiting Daggers | physical, orbit | 2 daggers circle you, 12 dmg | close range, dwarf, speed |
| Ember Aura | fire, area | burns enemies within 2.5 tiles every 0.5 s | burn, tank, bard |
| Frost Nova | frost, area | every 4 s, chills everything within 4 tiles ×2 | frost, kiting |
| Spirit Wolf | summon, physical | a wolf hunts the nearest enemy, 15 dmg bites | summoner |
| Rune Trap | arcane, area | drops a rune every 3 s; it bursts for 40 when stepped on | area, kiting |
| Poison Flask | poison, area | lobs a flask (reuses the old lob code), leaving a 3 s poison pool | poison, area |
| Storm Cloud | lightning, area | a cloud follows you and strikes a random enemy every 1.5 s, shocking it | shock, wizard |
| Healing Totem | summon | planted every 12 s: heals 3 HP/s within 3 tiles for 6 s | sustain, co-op |
| Ward Charm | — | +25 shield | tank, glass cannon |
| Fire Wand | fire, projectile | auto-fires a burning bolt at the nearest enemy every 1.2 s | burn, bard (who doesn't aim) |
| Bone Turret | summon, projectile | placed every 10 s, shoots for 8 s | summoner, sniper |
| Thorn Mail | physical | attackers take 5 + 30% of the damage back | tank/thorns |

## 5. Pool rules (guide part 5)

- **3 cards per offer** (4 with Fortune).
- **Reroll** (3 per run at the start), **banish** (removes a card for the run; 0 at the start) and **skip** (always available; heals 15% of max HP) are all bought up via the Guild.
- **Rarity:** common / uncommon / rare / epic / legendary. Base weights are 100 / 45 / 18 / 6 / 2; each point of luck moves weight 1% upward.
- **Tiered cards (★):** the same card rolls a rarity and gets bigger numbers (guide 5.2, option 1). Their values are listed as C/U/R/E/L. Every other card has a fixed rarity.
- **Gating:**
  - tag/status cards need their tag or status source;
  - spell level-ups need the spell;
  - capstones need level 15+ and at least one card of their archetype;
  - every "×" multiplier is rare or higher.
- **No dead offers:** the bard is never offered shot-speed cards, and burn payoffs never come without a fire source.
- **Smart weighting** (light): cards that share a tag with something you own get ×1.5 weight.
- **Archetype lean** (M18): once your build holds 2+ cards of one archetype (section 7; copies and spell levels count), 1 slot of every offer comes from that archetype's eligible cards. See section 14.
- **Determinism:** offers stay seeded by (seed, player, offer number), as they are now.

## 6. Catalog (100 cards)

**Avail.:** `start` means it's in the pool from the first run. `L:n` means you buy it in the Guild Hall's archive for n loot (rev 2 prices: rev 1 × 6, rounded; capstones 6,000). `A:...` means an achievement unlocks it. Loot prices are placeholders until M15 sets the drop rates.

**Role:** **E** enabler, **P** payoff, **C** capstone, **F** filler/generic.

### 6.1 Generic stats (21) — all ★ tiered, everyone

| # | Card | Text | Values C/U/R/E/L | Archetypes | Avail. |
|---|---|---|---|---|---|
| G01 | Sharpened | +X% damage | 10/15/22/30/40 | all | start |
| G02 | Quick Hands | +X% attack speed | 8/12/17/23/30 | all, crit, volley | start |
| G03 | Iron Skin | +X max HP | 15/25/35/50/70 | tank, bulwark | start |
| G04 | Swift Boots | +X% move speed | 5/8/11/15/20 | speed | start |
| G05 | Long Reach | +X% range | 10/15/20/28/35 | sniper, bard | start |
| G06 | Keen Eye | +X% crit chance | 3/5/7/10/14 | crit | start |
| G07 | Brutal | +X% crit damage | 15/25/35/50/70 | crit, sniper | start |
| G08 | Broad Strokes | +X% area | 8/12/17/23/30 | area, bard, aura | start |
| G09 | Lingering | +X% duration (M18: only once you have a status or Poison Flask / Healing Totem / Bone Turret) | 10/15/22/30/40 | status, spells | start |
| G10 | Thick Hide | +X armor | 3/5/8/12/16 | tank | start |
| G11 | Nimble | +X% evasion | 3/5/7/9/12 | speed, glass | start |
| G12 | Second Wind | +X HP/s | 0.4/0.7/1/1.5/2 | sustain, tank | start |
| G13 | Vampiric | heal X% of damage dealt (uncommon+) | —/1/2/3/4 | sustain | start |
| G14 | Magnet | +X% pickup radius | 20/30/45/60/80 | greed | start |
| G15 | Scholar | +X% XP | 8/12/17/23/30 | greed | start |
| G16 | Lucky Charm | +X luck | 5/8/12/16/20 | luck | start |
| G17 | Piercing | +1 pierce (not axes, which pierce everything) | fixed uncommon | sniper, volley | start |
| G18 | Potency | +X% status damage (needs a status) | 10/15/22/30/40 | all statuses | start |
| G19 | Quickened | −X% spell cooldown (needs a spell) | 6/9/12/16/20 | summoner, spells | start |
| G20 | Multishot | +1 projectile (the only "+projectile" card). M19: for anyone with a projectile (Sheet Music's notes, Fire Wand and Bone Turret count), in the pool from the start | fixed rare | volley | start |
| G21 🆕 | Affliction | +X% status chance (needs a status) | 5/8/12/16/20 | all statuses | start |

### 6.2 Hero cards (25) — 5 per hero, the 5th is that hero's capstone

| # | Hero | Card | Text | Rarity | Role / archetype | Avail. |
|---|---|---|---|---|---|---|
| W1 | wizard | Storm Caller | lightning jumps to +1 enemy | rare | P shock | start |
| W2 | wizard | Conductor | jumps reach 30% farther and fade less | common | P shock | start |
| W3 | wizard | Supercell | bolts shock; jumps prefer shocked enemies and deal +25% to them | uncommon | E shock | start |
| W4 | wizard | Overload | every 5th bolt: ×3 damage, +3 jumps | rare | P crit/shock | L:2000 |
| W5 | wizard | Ball Lightning | bolts stop at the first enemy and crackle there for 2 s, hitting everything around | legendary | C shock/area | L:6000 |
| D1 | dwarf | Ricochet | axes bounce off walls and fly on (up to 2 bounces) instead of turning back | rare | P volley | start |
| D2 | dwarf | Heavy Axe | ×1.35 damage, attacks 10% slower | rare | P sniper | start |
| D3 | dwarf | Homeward Fury | axes deal +50% on the way back | common | P | start |
| D4 | dwarf | Cleave | axes make enemies bleed | uncommon | E bleed | start |
| D5 | dwarf | Cyclone | a caught axe is thrown again at once at the nearest enemy (once per throw) | legendary | C volley/bleed | L:6000 |
| H1 | huntress | Volley | every 4th shot looses 5 arrows in a fan | epic | P volley | start |
| H2 | huntress | Broadhead | +15% damage for each enemy the arrow has already passed | uncommon | P sniper | start |
| H3 | huntress | Hunter's Mark | every 4 s, mark the toughest enemy in view: ×2 damage from you | rare | P sniper/crit | L:2000 |
| H4 | huntress | Steady Aim | +25% crit chance while standing still | uncommon | P crit | start |
| H5 | huntress | Deadeye | crits pierce every enemy and never fall short | legendary | C crit/sniper | L:6000 |
| P1 | princess | Prism | colors that hit the same enemy in one shot deal +20% for each other color that hit it | rare | P close range | start |
| P2 | princess | Focus | the fan narrows by 30% | common | F | start |
| P3 | princess | Spectrum | colors carry statuses: red burns, blue chills, green poisons, yellow shocks (20% each) | rare | E all statuses | L:2500 |
| P4 | princess | Point Blank | +40% damage to enemies within 4 tiles | uncommon | P close range | start |
| P5 | princess | Refraction | each color splits into 3 when it hits an enemy | legendary | C volley/status | L:6000 |
| B1 | bard | Crescendo | each beat in a row that hits something: +10% damage, up to +50% (a miss resets it) | common | P area | start |
| B2 | bard | Lullaby | every beat heals you 1 HP per enemy it hits (up to 5) | rare | P sustain | start |
| B3 | bard | Syncopation | beats alternate: a short loud one (60% reach, ×1.6) and a wide soft one (130% reach, ×0.7) | uncommon | P area | start |
| B4 | bard | Dissonance | beats push enemies back and chill them | uncommon | E frost/control | L:1500 |
| B5 | bard | Grand Finale | every 8th beat: ×4 damage, ×2 reach | legendary | C area | L:6000 |

### 6.3 Tags and statuses (14)

| # | Card | Text | Rarity | Role | Gate | Avail. |
|---|---|---|---|---|---|---|
| T01 | Kindling | 10% of your hits burn (Affliction raises every status's chance) | uncommon | E burn | — | start |
| T02 | Wildfire | +30% damage to burning enemies | uncommon | P burn | burn | start |
| T03 | Venom | 10% of your hits poison (Affliction raises every status's chance) | uncommon | E poison | — | start |
| T04 | Virulence | poison stacks to 10 and lasts 50% longer | rare | P poison | poison | L:2000 |
| T05 | Frostbite | 10% of your hits chill (Affliction raises every status's chance) | uncommon | E frost | — | start |
| T06 | Shatter | frozen enemies take ×1.5 damage and burst into ice shards on death | rare | P/C frost | chill | L:2500 |
| T07 | Static | 10% of your hits shock (Affliction raises every status's chance) | uncommon | E shock | — | start |
| T08 | Serrated | 10% of your hits bleed (Affliction raises every status's chance) | uncommon | E bleed | — | start |
| T09 | Hemorrhage | bleed ticks ×2 while the enemy moves | rare | P bleed | bleed | L:2000 |
| T10 | Elementalist ★ | +X% fire, frost, poison and lightning damage | 10/15/22/30/40 | P elements | element | start |
| T11 | Arcane Mastery ★ | +X% arcane damage | 10/15/22/30/40 | P | arcane | start |
| T12 | Weapons Master ★ | +X% physical damage | 10/15/22/30/40 | P | physical | start |
| T13 | Thermal Shock | burning + chilled enemies explode (combo, section 3) | epic | C fire+frost | burn & chill | L:3500 |
| T14 | Toxic Current | shock spreads poison to 2 nearby enemies (combo) | epic | C shock+poison | shock & poison | L:3500 |

### 6.4 Spells (12) — see section 4

| # | Card | Rarity | Avail. |
|---|---|---|---|
| S01 | Orbiting Daggers | uncommon | start |
| S02 | Ember Aura | uncommon | start |
| S03 | Frost Nova | uncommon | start |
| S04 | Spirit Wolf | uncommon | start |
| S05 | Rune Trap | uncommon | start |
| S06 | Poison Flask | uncommon | start |
| S07 | Storm Cloud | rare | L:2500 |
| S08 | Healing Totem | rare | L:2500 |
| S09 | Ward Charm | uncommon | L:1000 |
| S10 | Fire Wand | uncommon | start |
| S11 | Bone Turret | rare | L:2500 |
| S12 | Thorn Mail | uncommon | start |

Level-ups for an owned spell are offered as "Ember Aura II" and so on, at the spell's rarity. They don't count toward the 100.

### 6.5 Conditional and scaling (8)

| # | Card | Text | Rarity | Archetype | Avail. |
|---|---|---|---|---|---|
| C01 | Untouched | +30% damage while above 90% HP | uncommon | glass, speed | start |
| C02 | Berserker | +1% damage per 1% HP missing | rare | glass, tank | L:2000 |
| C03 | Bulwark | +1% damage per 10 max HP | rare | tank | L:2000 |
| C04 | Momentum | +damage equal to half your move speed bonus | uncommon | speed | start |
| C05 | Fleet Strike | +1% crit chance per 4% move speed bonus | rare | speed, crit | L:2000 |
| C06 | Bloodlust | each kill: +1% damage for 10 s (up to +30%) | uncommon | volley, area | start |
| C07 | Giant Slayer | +40% damage to enemies with more max HP than you | uncommon | sniper, bosses | start |
| C08 | Veteran | +1% damage per level | rare | late game | L:1500 |

### 6.6 Trade-offs (6)

| # | Card | Text | Rarity | Who wants it | Avail. |
|---|---|---|---|---|---|
| X01 | Glass Cannon | ×1.4 damage, −30% max HP | rare | glass, dodge | L:2000 |
| X02 | Heavy Plate | no single hit can take more than 10% of your max HP; −15% move speed | uncommon | tank (bad for speed) | start |
| X03 | Spray and Pray | shots split in two at half range (60% damage each); −25% range | rare | volley, on-hit statuses | start |
| X04 | Frenzy | for 3 s after a kill you attack twice as fast; −20% range | uncommon | close range, princess, bard | start |
| X05 | Bounty | every 25th kill drops a loot cache worth 25 kills; enemies are 15% faster | rare | greed | start |
| X06 | Beacon | 30% more enemies spawn (more kills, gems and loot) | rare | greed, area | L:2000 |

### 6.7 Triggers (6)

| # | Card | Text | Rarity | Archetype | Avail. |
|---|---|---|---|---|---|
| R01 | Volatile | kills have a 15% chance to explode (40% of the killing hit, 1.5 tiles) | uncommon | E explosion | start |
| R02 | Chain Reaction | explosions can set off explosions (once per chain link) | rare | P explosion | A: kill 15 enemies within 1 s |
| R03 | Retaliation | when hit, a shockwave pushes back and deals 30 (3 s cooldown) | uncommon | tank, thorns | start |
| R04 | Soul Harvest | kills heal 1 HP | common | sustain | start |
| R05 | Surge | on level-up, heal 20% and blast enemies around you away | uncommon | all | L:1000 |
| R06 | Echo | every 6th attack happens twice | uncommon | volley, bard | start |

### 6.8 Economy (3)

| # | Card | Text | Rarity | Avail. |
|---|---|---|---|---|
| E01 | Prospector ★ | +X% loot | 10/15/22/30/40 | start |
| E02 | Fortune | +1 card per offer (max 1) | epic | L:3500 |
| E03 | Golden Hoard | +1% damage per 50 loot picked up this run (max +50%) | rare | L:2500 |

### 6.9 Capstones and rule-breakers (6) — legendary, level 15+

| # | Card | Text | Archetype | Avail. |
|---|---|---|---|---|
| K01 | Overflow | crit chance above 100% becomes crit damage (×2 rate) | crit | A: reach 75% crit chance |
| K02 | Pandemic | on death, an enemy's statuses spread to 2 nearby enemies | all statuses | L:6000 |
| K03 | Aegis | healing past full HP becomes shield (up to 50% max HP) | sustain, tank | L:6000 |
| K04 | Pack Leader | summons use your crit and statuses; +1 wolf and +1 turret | summoner | L:6000 |
| K05 | Juggernaut | +2% damage per armor; you can't evade | tank | L:6000 |
| K06 | Phoenix | once per run: on death, revive at 50% HP and explode | glass, all | A: reach level 30 |

**Totals:** 21 + 25 + 14 + 12 + 8 + 6 + 6 + 3 + 6 = **101**. Of these, **66 are in the pool from the start** and **35 are unlockable** (32 with loot, 3 by achievement). M18 adds the 11 cards of section 6.10, all in the pool from the start: **112**.

### 6.10 Dodge roll (11, M18) — the roll itself is every hero's (Shift / pad B or LB)

The roll: ~4 tiles in 0.25 s toward where you walk (your aim if standing still), untouchable the whole time (shots, blasts and bodies pass through), stopped by walls, 1 charge back every 5 s. Shown on the HUD as ROLL.

| # | Card | Text | Rarity | Archetype |
|---|---|---|---|---|
| V01 | Quick Recovery ★ | rolls recharge X% faster (cap 60%) | 8/12/16/20/25 | roll |
| V02 | Extra Roll | +1 roll charge (they come back one at a time) | rare | roll |
| V03 | Riposte | the first attack within 1.5 s of a roll's start always crits | uncommon | roll, crit |
| V04 | Slipstream | +30% move speed for 2 s after a roll | uncommon | roll, speed |
| V05 | Close Call | each enemy shot you roll through takes 0.1 s off the cooldown | uncommon | roll |
| V06 | Scorched Trail | rolls leave burning patches (one every 0.8 tiles, 2.5 s) | uncommon | roll, burn |
| W6 | Blink (wizard) | the roll is a teleport (5 tiles, never through walls) ending in a shock nova (20, 2.5 tiles) | uncommon | roll, shock |
| D6 | Shoulder Charge (dwarf) | enemies the roll runs into take 25 and are shoved 2.5 tiles along it | uncommon | roll, tank |
| H6 | Backflip (huntress) | starting a roll looses 5 arrows (×0.6) in a 40° fan at your aim | uncommon | roll, volley |
| P6 | Prism Dash (princess) | a trail like Scorched Trail, each patch a random burn / chill / poison / shock | uncommon | roll, statuses |
| B6 | Drop the Beat (bard) | a free ×1.5 beat as each roll ends | uncommon | roll, area |

Dropped from the M18 proposal (your call): Long Roll, Afterimage.

### 6.11 Projectile patterns (9, M19)

Pattern cards need an attack that shoots: every hero but the bard, and the bard once he has Sheet Music. Each one fires shots of the hero's own weapon, so the rainbow's are whole fans, the axes come home and the bolts still jump. The bard's are notes.

| # | Card | Text | Rarity | Archetype |
|---|---|---|---|---|
| M01 | Cross Fire | every 4th attack also fires at 90°, 180° and 270° | uncommon | volley |
| M02 | Starburst | every 10th attack: 8 single shots all around | rare | volley |
| M03 | Rear Guard | every attack also fires one shot behind you (60%) | uncommon | volley |
| M04 | Spiral | an extra shot each attack, 37° further round each time | uncommon | volley |
| M05 | Twin Lanes | every shot flies as two, half a tile apart (65% each) | rare | volley |
| B7 | Sheet Music (bard) | each beat flings 3 notes (9 each) at the nearest enemies in sight; +1 note per Multishot; with nobody near they spread all round | uncommon | volley |
| H7 | Split Arrow (huntress) | **her power: a spell, uses a slot, levels I-V.** I: an arrow's first hit splits it into a 3-arrow fan (50% each, 40°); II +1 arrow; III +30% split damage; IV splits on every enemy it passes; V +2 arrows, wider fan. Split arrows don't split again | uncommon | volley, sniper |
| P7 | Double Rainbow (princess) | every 3rd shot, a second fan 0.08 s behind, turned half a color | rare | volley |
| D7 | Twin Axes (dwarf) | every 3rd throw is two axes in a V (30° apart); both come home | rare | volley |

Dropped (your call): Barrage. Multishot is the one plain "+1 projectile" card. The wizard's projectile cards come with his new weapon (M20).

## 7. Archetype coverage (guide 7.2)

Each row should have an enabler, 2-4 payoffs, a capstone and overlap with at least 2 others.

| Archetype | Enabler(s) | Payoffs | Capstone | Overlaps |
|---|---|---|---|---|
| Crit | G06, G07 | H4, W4, C05, H3 | K01, H5 | sniper, speed |
| Burn | T01, S02, S10, P3 | T02, G18, T10 | T13, K02 | area, frost |
| Poison | T03, S06, P3 | T04, G18, T10 | T14, K02 | shock, area |
| Frost / control | T05, S03, B4, P3 | T06, G09 | T13 | burn, kiting |
| Shock / chain | W3, T07, S07 | W1, W2, W4 | W5, T14 | crit, area |
| Bleed | D4, T08 | T09, G18 | D5, K02 | volley, physical |
| Volley | G20, D1, H1, P1, X03 | R06, C06, G02 | P5, D5 | statuses (more hits) |
| Sniper / big hit | D2, H2 | C07, H3, G07, G17 | H5 | crit |
| Area / explosion | R01, bard, S05 | R02, G08, B3, X06 | B5, W5 | burn, poison |
| Summoner | S04, S11, S08 | G19, G09 | K04 | tank |
| Tank / thorns | G10, G03, S12, X02 | C03, R03, S09 | K05, K03 | summoner, aura |
| Speed / kiting | G04, G11 | C04, C05, C01 | (K06) | crit, frost |
| Sustain | G12, G13, R04, S08 | B2, R05 | K03 | tank |
| Greed | G15, E01, X05, X06 | E03, G14 | E02 | everything |
| Glass cannon | X01, C01 | C02, S09 | K06 | crit, speed |
| Roll (M18) | V01, V02, G11 | V03-V06, the hero rolls (W6 D6 H6 P6 B6) | — | speed, crit, burn |

M18 also added V03 Riposte to Crit, V06 Scorched Trail to Burn, W6 to Shock, H6 to Volley, B6 to Area, D6 to Tank and V04 to Speed. `config.ARCHETYPES` holds this table as code lists.

**Per-hero leanings:**
- **wizard:** shock, crit, area (W5).
- **dwarf:** bleed, tank, volley; tough body plus axes that pass through crowds twice.
- **huntress:** sniper, crit, pierce.
- **princess:** every status (P3), volley, close range.
- **bard:** area, frost/control, sustain; spells matter most because his attack is automatic.

## 8. How the 19 current cards map in

| Now | Becomes |
|---|---|
| sharpened, quick_hands, iron_skin, swift_boots, long_reach, second_wind, vampiric | G01, G02, G03, G04, G05, G12, G13 (tiered) |
| twin_shot | G20 Multishot |
| piercing | G17 |
| velocity | retired (folded into D3 and spell levels) |
| storm_caller, conductor | W1, W2 |
| volley | H1 |
| prism, focus | P1, P2 |
| crescendo, encore | B1, B2 |
| ricochet, heavy_axe (dwarf, added in M13) | D1, D2 |

## 9. Build order

- **M14 (done):** the stat layer, buckets, crit, statuses, spell slots, 5 rarities, tiered cards, reroll/banish/skip; 45 cards + 3 spells.
- **M15 (done):** loot, the walkable Guild Hall, card unlocks.
- **M16 (proposal, after this review):**
  1. rev 2 rules: change the 15 cards in section 12 (9 of them are already built), add Affliction;
  2. Guild Hall rev 2 (`GUILD.md`): new ladders and prices, unique trainer trees, archivist shelves (cards, spells, pacts, bestiary);
  3. **batch 2:** the other 9 spells, conditionals, trade-offs, triggers, economy (~35 cards);
  4. **batch 3:** status payoffs, combos, all capstones, and the 3 achievements (~18 cards).

  That's big. If you'd rather, split it: **M16** = steps 1-3, **M16b** = step 4.

## 10. Answers (2026-10-01)

1. **XP:** kills drop **gems** you pick up; pickup radius (Magnet) pulls them in.
2. **Skip reward:** heals 15% of max HP.
3. **Co-op:** still open; every card is personal for now.

## 11. M14 implementation notes

Choices made where the catalog left room:
- **Status chance (rev 1, replaced by rev 2: each status rolls 10% + Affliction):** one roll per hit; on success, one stack of *every* status your enablers list (Kindling, Venom...). Hero-card statuses (Supercell, Cleave, Spectrum, Dissonance) and spells apply theirs without that roll.
- **Status damage** is dealt every 0.5 s as one number (colored by status). Chill slows an enemy's whole clock (moving, aiming, cooldowns); the 5th stack freezes it for 1.5 s and uses the chill up.
- **Rarity roll per slot:** each offer slot rolls a rarity first, then a card that exists at that rarity (falling back to the nearest lower rarity, then higher). Luck multiplies each step above common by (1 + 1% x luck).
- **Spell levels:** Orbiting Daggers II +1 dagger, III +30% damage, IV +1 dagger, V wider/faster orbit. Ember Aura II +20% size, III 2 burn stacks per pulse, IV +20% size, V pulses 30% faster. Frost Nova II 15% faster, III +25% size, IV +1 chill stack, V double damage and 15% faster. Frost Nova also deals 8 damage.
- **Bard reach** grows with range *and* area (added together).
- **Tempo** and **Heavy Axe** change the attack interval directly (x0.85 / x1.1), separate from attack speed %.
- **Hunter's Mark** picks the enemy with the most max HP on the huntress's screen, every 4 s or when the mark dies.
- **Spectrum colors:** red burn, orange nothing, yellow shock, green poison, blue chill.
- **Gems** fade after 3 minutes; above 300 on the ground, the oldest merges into its nearest neighbour (no XP lost). Only kills by a hero (or their statuses/spells) drop gems.

## 12. Rev 2 changes (2026-10-01)

| # | Card | Rev 1 | Rev 2 | Why |
|---|---|---|---|---|
| G20 | Multishot | wizard/huntress only | everyone who shoots | the only "+projectile" card |
| G21 | Affliction 🆕 | — | +X% status chance | the only "+status chance" card |
| T01-T08 | enablers | +15% status chance each | "10% of your hits burn / poison..." | status chance was sold 5 times |
| D1 | Ricochet | +1 axe | axes bounce off walls and fly on | +projectile = Multishot |
| D3 | Long Haul → Homeward Fury | +30% range, +20% speed | +50% damage on the way back | range = Long Reach |
| H1 | Volley | +2 arrows | every 4th shot is a 5-arrow fan | +projectile = Multishot |
| H2 | Broadhead | +2 pierce, +15%/enemy passed | +15%/enemy passed only | pierce = Piercing |
| P1 | Prism | +2 colors | colors on the same enemy boost each other | +projectile = Multishot |
| P2 | Focus | tighter fan, +25% range | tighter fan only | range = Long Reach |
| B1 | Crescendo | +25% reach | builds +10% per beat that hits, up to +50% | reach = Long Reach |
| B2 | Encore → Lullaby | +30% damage, +1.5 HP/s | heal 1 HP per enemy a beat hits | damage = Sharpened, regen = Second Wind |
| B3 | Tempo → Syncopation | beats 15% sooner | short loud / wide soft beats alternate | attack speed = Quick Hands |
| X02 | Heavy Plate | +12 armor, −15% move | no hit takes more than 10% max HP, −15% move | armor = Thick Hide |
| X03 | Spray and Pray | +2 projectiles, ×0.75 | shots split in two at half range, −25% range | +projectile = Multishot |
| X04 | Frenzy | +30% attack speed, −20% range | double attack speed for 3 s after a kill, −20% range | attack speed = Quick Hands |
| X05 | Bounty | +35% loot, faster enemies | every 25th kill: a loot cache; faster enemies | loot = Prospector |
| X06 | Beacon | +40% XP, more enemies | more enemies only | XP = Scholar |
| R05 | Surge | heal + 50% attack speed on level-up | heal + blast enemies away on level-up | temporary attack speed = Frenzy |
| all `L:` | prices | 200-1,000 | ×6 (1,000-3,500), capstones 6,000 | the bigger economy in `GUILD.md` rev 2 |

Unchanged on purpose: W1 Storm Caller (+1 jump) and W2 Conductor are the only cards touching lightning jumps; D2 Heavy Axe and X01 Glass Cannon are both "×damage" but each with its own cost (rule 4).

## 13. M16 implementation notes

- **Status chance:** every status your cards give rolls on each hit: 10% + Affliction. Statuses a card or spell applies by itself (Supercell, Cleave, Spectrum, Dissonance, Ember Aura, Frost Nova, Fire Wand...) don't roll.
- **Every Nth attack** (Overload, Volley, Grand Finale, Echo, Syncopation's alternation, Quiver) counts every attack the hero makes.
- **Volley** tops the shot up to 5 arrows (with Multishot you already have 2, so +3).
- **Crescendo** grows +10% for each beat in a row that hit something; the current beat uses the streak before it.
- **Refraction** children fly the rest of the color's range; **Spray and Pray** halves split at half range (axes never split); neither split again.
- **Deadeye:** a crit makes that arrow pierce everything and doubles its range.
- **Cyclone:** a caught axe flies out again at the nearest enemy within its range (the re-throw can't re-throw).
- **Ball Lightning:** a bolt's direct hit leaves a 2 s crackle (1.5 tiles, 30% of the bolt every 0.25 s); the jumps still happen.
- **Summons** (wolves, turrets) never crit or roll your statuses unless you have Pack Leader (which also adds a wolf and a turret).
- **Volatile:** 40% of the killing hit, 1.5 tiles. **Chain Reaction:** a body killed by an explosion always explodes.
- **Pandemic** copies the dying enemy's statuses (stacks too) to the 2 nearest enemies within 4 tiles. **Shatter's** burst: 15 damage + 1 chill within 2 tiles.
- **Bounty's** cache is worth 25 of the kill that triggered it. Bounty and Beacon change the spawner for the whole run (enemies already awake keep their speed).
- **Phoenix** comes before the Guild's Second Chance; it blasts 60 fire damage + 3 burn within 3 tiles.
- **Heavy Plate** caps a hit after armor, before the shield. **Thorn Mail** reflects flat + share of what got past the shield.
- **Capstones** (and K cards) need level 15 and their gate: Overflow a crit card, Pandemic a status, Aegis some healing, Pack Leader a summon, Juggernaut armor.
- **Achievements:** chain_reaction (15 kills within 1 s), crit_75 (75% crit chance in a build), level_30. They unlock Chain Reaction, Overflow and Phoenix.

## 14. M18 changes (2026-10-02)

- **"dodge" is now "evasion"** (the passive chance a hit misses): Nimble gives +X% evasion, Royal Grace +3% evasion, Juggernaut "you can't evade". The roll works with Juggernaut.
- **Lingering** is only offered once something lasts: any status source, or Poison Flask, Healing Totem or Bone Turret (`config.DURATION_SPELLS`). Its place in everyone's pool went to the roll cards.
- **Spell level-ups that were only "lasts longer"** (each was level III) are replaced. The old entries are kept as comments in `config.SPELLS`, and the `life` numbers still scale with duration:
  - Poison Flask III: pools last 2 s longer → **throws 2 flasks at once** (at the 2 nearest enemies, or beside the only one);
  - Healing Totem III: lasts 3 s longer → **also chills enemies near it** (1 stack a second; it counts as a chill source);
  - Bone Turret III: turrets last 4 s longer → **bolts pierce +1 enemy**.
- **Archetype lean:** the build's leading archetype is the one with the most cards taken (copies and spell levels count), once it reaches `ARCHETYPE_MIN` = 2. That archetype then gets `ARCHETYPE_SLOTS` = 1 slot of every offer. That slot is drawn first, the usual way (rarity roll, synergy weight) but only among that archetype's eligible cards, and then shuffled in among the others. Ties go to the archetype listed first in `config.ARCHETYPES`. A build without a lean draws exactly as before. Example: two Spirit Wolf picks mean every offer has a summoner card (Bone Turret, Healing Totem, Quickened, Lingering, Pack Leader, or a wolf level).

## 15. M19 changes (2026-10-02)

- **Fan rule:** every projectile beyond a weapon's own adds at least 12° (`MIN_PELLET_GAP`) to the fan. This covers Multishot, Coronation, Quiver, Volley, Backflip and Twin Axes. One Multishot gives the wizard two bolts 12° apart. A weapon's own fan is kept (the rainbow's 5 colors over 34°; with one Multishot, 6 over 46°). Focus still narrows the result.
- **Echo** repeats the attack 10° off the aim, left and right in turn, so the repeat doesn't fly down the same line.
- **Multishot** is in the pool from the start (it was 2,000 loot). It's for anyone with a projectile, and Fire Wand and Bone Turret fire one more bolt per copy (12° apart). Its old "+10° spread" is replaced by the fan rule.
- **Split Arrow** is a spell (huntress-only card, own spell slot, HUD "SPLIT"), as the user asked: "a power that levels like a spell".
- `config.ARCHETYPES["volley"]` now includes M01-M05, B7, H7, P7 and D7.
- The synergy test now compares the same pool with and without the frost tag. A real frost source (Frost Nova) also opens Potency, Affliction and Lingering, and those crowd Frostbite out more than the ×1.5 weight lifts it.
