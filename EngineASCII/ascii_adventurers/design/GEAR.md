# AsciiAdventurers — Gear

Status: **rev 2; M28.1 BUILT (2026-10-18, section 16).** It is M28 in `BOSSES.md` section 8. The cards (`CARDS.md`) are now the powers and plain stats of gear; M28.2-M28.6 are still to come.
- Rev 0 drafted the system.
- Rev 1 applies the user's answers to its ten questions (Q1-Q10, section 13).
- Rev 2 applies the answers to the follow-ups (N1-N8, section 13).
- What's still open is in section 14. Every proposal can change.

What the user asked for (2026-10-13):
- "The whole card system will be adapted/reworked into kind of the same system but based on gear."
- "Our adventurers will have gear slots, and the abilities and effects gained will be from that."
- "You start with no gear and you slowly start getting gear with each level, or maybe even quests and bosses."
- Examples: **boots of freezing** (they make an ice path); a **helmet or a wizard cap, depending on the hero, that gives arcane missiles**.
- Gear "goes +1", and "there are so many of them".
- "This system will be much more thought through, but these are the basics."

---

## 1. Goals

1. **Same depth as the cards, but things you wear.** The build is what's on your hero, not a list of cards you can't see. A gear screen shows the whole build.
2. **Keep what works.** The 127 cards already hold the effects, the statuses, the damage buckets, the archetypes and the gating rules (CARDS.md sections 1-5). Most cards become a piece of gear (or an affix on one) with the **same code underneath**. So M28 is mostly a new layer on top, not a rewrite of the effects.
3. **Gear comes from the world too.** Level-ups give most of it, but elites, chests and bosses drop it as well. Exploring and boss fights get rewards worth chasing.
4. **Clear choices.** Each slot holds one piece, so a choice is "this or what I wear", and stats stop piling up invisibly.
5. **Not locked in by a mistake** (user, Q5): a bag of spares lets you swap back.
6. **It works in co-op** (later): each player gets their own pieces, like today's cards and loot.

## 2. Slots (user, Q2 + Q3: ten slots, fixed homes)

**Every hero keeps their signature weapon** (user, Q1). The wizard always has arcane missiles, the dwarf his axes, and so on. Gear changes and adds to it.

**Every power lives in exactly one slot** (user, Q3: "fixed homes"). Boots are always about movement, a chest piece is always defence. That's easy to learn and to balance; the cost is that two strong powers for the same slot shut each other out, which is the choice.

| Slot | How many | Home: what its pieces do (today's cards) | Pieces | Looks per hero |
|------|---------:|------------------------------------------|-------:|----------------|
| **Main hand** | 1 | **The hero's own weapon line, hero-only.** Everything that changes how that hero's weapon works (CARDS 6.2 and the hero rows of 6.11), and the huntress's spell Split Arrow. (Chain Lightning moved to the trinkets in M28.1, section 16) | 34 | wizard: staffs, dwarf: axe heads, huntress: bows, princess: wands, bard: lutes |
| **Off-hand** | 1 | **Shot patterns and attack rhythm:** Cross Fire, Spiral, Rear Guard, Twin Lanes, Starburst, Echo, Frenzy, Spray and Pray | 8 | quiver, tome, orb, a second axe, a songbook |
| **Head** | 1 | **Statuses and elements:** Kindling, Venom, Frostbite, Static, Serrated, Wildfire, Shatter, Hemorrhage, Virulence, Thermal Shock, Toxic Current | 11 | cap, helmet, hood, tiara, hat (the same piece looks different on each hero) |
| **Chest** | 1 | **Defence and trade-offs:** Thorn Mail, Ward Charm, Heavy Plate, Glass Cannon, Retaliation, Untouched, Berserker, Bulwark, Juggernaut, Aegis, Phoenix | 11 | robe, plate, leathers, gown, doublet |
| **Feet** | 1 | **Movement and the roll:** Riposte, Slipstream, Close Call, Scorched Trail, the 5 hero rolls (Blink, Shoulder Charge, Backflip, Pirouette, Drop the Beat), Momentum, Fleet Strike; new trails like the **boots of freezing** | 11 | boots |
| **Rings** | 2 | **Triggers, scaling and the economy:** Volatile, Chain Reaction, Soul Harvest, Surge, Bloodlust, Giant Slayer, Veteran, Overflow, Pandemic, Pack Leader, Fortune, Golden Hoard, Bounty, Beacon | 14 | (HUD only) |
| **Trinkets** | 3 (4th from the Guild's Arcane Wing) | **The spells:** Orbiting Daggers, Ember Aura, Frost Nova, Spirit Wolf, Rune Trap, Poison Flask, Storm Cloud, Healing Totem, Fire Wand, Bone Turret, and the wizard's Chain Lightning (M28.1) | 11 | (HUD only; the wolf and the turret show in the world) |

**100 pieces** from today's cards, plus the new ones (section 6). Main-hand pieces are hero-only, so each hero has about 7 of them (the wizard 11); every other piece fits everyone.

```
      [HEAD]
[MAIN HAND] [CHEST] [OFF-HAND]
      [FEET]
[RING] [RING]
[TRINKET] [TRINKET] [TRINKET] (+1 from the Guild)
```

## 3. What a piece of gear is

| Part | What it is | Comes from |
|------|------------|------------|
| **Base** | Its name and slot, e.g. *Seeker's Staff*, *Frostwalkers*, *Ember Amulet* | one per card that becomes gear (section 5), plus new ones (section 6) |
| **Power** | Its one main effect: what the card did | the card's effect, same code |
| **Level** | **+0 to +9** (user, Q7): ten steps. **+1, +2, +4, +5, +7, +8 grow the numbers; +3, +6 and +9 each add a new trick** to the power | the same base again, or an upgrade pick (section 4.1) |
| **Rarity** | common / uncommon / rare / epic / legendary, same colours and odds as cards (luck still shifts them) | rolled when the piece drops; section 7 |
| **Affixes** | Plain stat lines such as *+12% attack speed* or *+25 max HP* | the generic stat cards (section 5) |

A piece reads like this:

```
 EPIC  Frostwalkers +4                       FEET
 Each step leaves ice for 3.6 s. Enemies on it are
 chilled; you slide 24% faster on it.
   +15% move speed
   +9% evasion
   +1 roll charge
 next, +5: the ice lasts 4 s
 at +6: frozen enemies on the ice shatter
```

**The no-repeats rule (CARDS.md section 0) still holds:**
- a plain stat only ever comes from its affix (and the Guild);
- every power does something different;
- every power has exactly one home slot.

**Damage buckets** (CARDS 1.1): "+X% damage" affixes are bucket A, the element lines are bucket T, "×N damage" powers are their own multiplier and rare or higher. Arcane and physical are gone as bonuses (section 8).

## 4. Getting gear (user, Q6: level-ups, elites, bosses, chests)

### 4.1 Level-ups (the main source)

**A hero starts the run with no gear.** Each level gives one gear pick, in the same picker as today's cards (single player pauses). The picker shows **3 rolled pieces**; each one is one of:
- a **new piece for an empty slot**;
- **+1 to a piece you're wearing**, shown as "Frostwalkers +2 -> +3";
- a **different piece for a filled slot**, shown next to what you wear (a side-by-side compare). Taking it moves the old piece into your **bag** (4.3).

Below the three: **UPGRADE**, REROLL, BANISH, SKIP.
- **UPGRADE** (user, Q4: "you can also choose on level up to upgrade an existing piece rather than choose another rolled one"; N2): instead of the three, pick **any piece you're wearing** below +9 and give it +1. It costs the whole pick. Bagged pieces can't be upgraded.

**What the three lean toward** (user, N6):
- **Level 2:** one of the three is always a **main-hand piece**, so the hero's own line shows from the first pick (N7).
- **Early:** mostly new pieces for empty slots.
- **Late (6+ slots filled): more swaps than +1s.** The user: "more swaps than +1, since we have the upgrade button for +1". Proposal: swaps ×1.5, +1s at normal weight.

The rules from CARDS.md section 5 carry over:
- the gating ("needs a status", "needs a spell", capstones at level 15+);
- "no dead offers";
- smart weighting (sharing a tag with what you wear: ×1.5);
- the archetype lean, now counting worn pieces and their levels;
- determinism (seeded by seed, player and offer number).

### 4.2 Drops: elites and chests

- **Elites** have a chance (proposal: 15%) to drop a piece.
- **Chests** (new, user Q6 + N3): **about 6-8 per ring biome**, at landmarks, ruins and camps. Each holds one piece, a bit better than an elite drop (luck +10 for its roll). A chest is pinned on the map once you've seen it.
  - **Half open when touched.**
  - **Half are guarded:** a pack stands round it and the chest opens when the pack is dead (a counter shows on it).
  - **Mimics** (user: "add mimic chance, it's cute"): about **1 chest in 10 is a mimic**. It bites when you touch it and becomes a mini-fight (an elite-sized chest with teeth: lunges, a tongue, coins spat as shots). Beaten, it drops an **epic or better** piece. A biome's mimic matches the biome (a sandy chest in the desert, a mossy one in the forest...).
- A dropped piece lies on the ground with a glow in its rarity's colour and a label, like the loot shards. Walking over it opens the compare panel: **wear it** (a swap or a +1), **bag it**, or **salvage it**.
- In co-op, each player sees their own drops. Drops follow the gating like offers do, and they're seeded.

### 4.3 The bag (user, Q5)

- The bag holds **3 spare pieces**; a Guild ladder adds up to 2 more (N1; section 10). A piece you swap out goes there; so can a drop you don't want to wear yet.
- From the gear screen you can swap a bagged piece back in **anywhere except inside a sealed boss arena** (N1). That's what keeps a mistake from locking you into a build.
- **Salvage:** any piece, worn or bagged, can be salvaged into loot (rune shards, by rarity and level) at any time. The bag left at the end of a run is salvaged automatically.
- If the bag is full when a piece would go in, you choose which one to salvage.

### 4.4 Bosses

- Beating a boss gives **one extra gear pick of rare or better** (today: an extra card offer of at least rare, `config.BOSS_CARD_RARITY`).
- It also drops **one of that boss's unique legendary pieces**, every kill (once a run per player). Each has a fixed power and fixed affixes that no other piece has.
- **Every boss has 2-3 uniques, in different slots** (user, N5: "several per boss"); one of them drops per kill. A found unique shows on the armory shelf.
- The first unique of each boss is below: proposals, to trim and rename together. Each one fits its slot's home. The other 1-2 per boss get drafted in M28.5, e.g. for the Fallout King: Lead Apron (chest) / Geiger Ring (ring) / Rod of Fission (trinket).

| Boss | Unique | Slot | Power |
|------|--------|------|-------|
| Froggy McFrogface | Tongue Lasher | off-hand | every 6th attack also lashes a tongue that pulls the first enemy hit to you |
| the Leech Swarm | Leechskin | chest | lifesteal works on status ticks too |
| Lady Proboscia | Proboscis Ring | ring | hits on bleeding enemies heal 1 HP (once per enemy a second) |
| Khepri | Dung Ball | trinket | a ball rolls ahead of you, growing with each enemy it flattens |
| Ol' Spitter | Spittoon | trinket | every 4 s, spits a ricocheting glob at the nearest enemy |
| the Nameless Magus | Hourglass Ring | ring | every 20 s, enemy shots near you slow to a crawl for 2 s |
| the Fallout King | Lead Apron | chest | stand still 1 s and you take 40% less damage |
| the Snow King | Crown of Black Ice | head | hits chill; chilled enemies leave black ice where they walk, and enemies on it slide |
| Fragile | Black Lace Parasol | off-hand | blocks shots from in front while you aim |
| Nettle | Shrinking Dust | feet | rolls shrink you for 2 s (+35% speed, a smaller hitbox) |
| Love & Cuddles | Cleaver of Cuddles | trinket | a cleaver orbits you, spinning faster as you kill |
| The Fallen | Rootbound Boots | feet | stand still to root in and grow a shield; walk to uproot |
| Mycelium (each variant) | Mycelial Ring | ring | kills leave a spore patch that poisons |
| More than Life / Death | Phylactery | ring | once a run, on death, you rise as a shade for 10 s; kill 10 enemies to come back at 30% HP |

The main-hand slot has no boss uniques, since its pieces are hero-only. Uniques need their own art and code, so they come late in the build (M28.5).

## 5. Turning the cards into gear

Every one of the 127 cards has a home:

| Card family (CARDS.md) | Cards | Becomes |
|------------------------|------:|---------|
| Generic stats (6.1) | 21 | **affixes**, not pieces |
| Hero cards (6.2, 6.10, 6.11) | 40 | **main hand**, hero-only (35); the 5 hero rolls go to **feet** |
| Tags and statuses (6.3) | 14 | **head** (11). Elementalist becomes an affix. **Arcane Mastery and Weapons Master are cut** (user, Q9; section 8) |
| Spells (6.4) | 12 | **trinkets** (10); Thorn Mail and Ward Charm go to **chest** |
| Conditional and scaling (6.5) | 8 | **chest** (Untouched, Berserker, Bulwark), **feet** (Momentum, Fleet Strike), **rings** (Bloodlust, Giant Slayer, Veteran) |
| Trade-offs (6.6) | 6 | **chest** (Glass Cannon, Heavy Plate), **off-hand** (Spray and Pray, Frenzy), **rings** (Bounty, Beacon) |
| Triggers (6.7) | 6 | **rings**; Retaliation goes to **chest**, Echo to **off-hand** |
| Economy (6.8) | 3 | **rings** (Fortune, Golden Hoard); Prospector becomes an affix |
| Capstones (6.9) | 6 | **legendary-only** pieces (level 15+), each in its home slot: Overflow, Pandemic, Pack Leader in rings; Aegis, Juggernaut, Phoenix in chest |
| Dodge roll, the 6 shared (6.10) | 6 | **feet** (4); Extra Roll and Quick Recovery become affixes found only on boots |
| Projectile patterns, the 5 shared (6.11) | 5 | **off-hand** |

Totals: 100 pieces, 25 affixes, 2 cut = 127.

**Ten levels per piece** means writing steps:
- Spells already have five levels; the "+X per copy" cards (Hang Time, Extra Roll...) already scale.
- Every piece needs **three new tricks** (+3, +6, +9) and number steps in between.
- Number steps follow one rule per piece (e.g. "+8% to the power's main number"), so only the tricks are written by hand: about 300 for 100 pieces.
- That's the biggest writing job in M28. I draft them slot by slot for the user to trim, the way the cards were done.

## 6. New pieces

The ones the user described, and a few more in their spirit. More get drafted with the user per slot:

| Piece | Slot | Power |
|-------|------|-------|
| **Frostwalkers** | feet | the boots of freezing: each step leaves ice for 3 s; enemies on it are chilled, you slide faster on it |
| **Emberstriders** | feet | burning footprints while you walk (Scorched Trail stays the roll's version) |
| **Gale Boots** | feet | each roll leaves a gust that pushes enemies away |

The user's other example (a cap or helmet that gives arcane missiles) is covered by Q1's answer: the wizard always has his missiles, and the head is now the element slot. If missiles for other heroes are still wanted, that's an open idea (N8).

## 7. Rarity (user, Q8: "more affixes, but also a stronger power; legendaries should feel LEGENDARY")

- **Odds:** the same rarity weights as cards (100 / 45 / 18 / 6 / 2), with the same luck rule.
- **What rarity changes** (user, N4: the steeper numbers; tuned again in M35):

| Rarity | Affixes | Power | Extra |
|--------|--------:|------:|-------|
| common | 0 | ×1.0 | |
| uncommon | 1 | ×1.15 | |
| rare | 2 | ×1.3 | |
| epic | 3 | ×1.5 | |
| legendary | 3, rolled at the top | ×2.0 | a **legendary trick** of its own, on top of the +3/+6/+9 ones, and a look of its own: a gold frame in the picker, a glow on the ground, a sound when it drops |

- The level is what grows a piece over a run, so a common +6 can still beat an epic +0.
- **Legendary** pieces are the capstones (6) and the boss uniques (4.4, 2-3 per boss). Any other base can also roll legendary, and gets its legendary trick then.

## 8. Damage types (user, Q9; settles balance item B4)

Today there are three kinds of damage upgrade (plain, arcane, physical), and nobody can tell them apart. The user picked: **simplify**.
- **Two kinds only:** *+X% damage* (everything) and *+X% elemental damage* (fire, frost, poison, lightning: the Elementalist affix). Arcane Mastery and Weapons Master are cut.
- The `arcane` and `physical` tags stay on weapons and spells only where something checks them (CARDS section 2). They're never a damage bonus any more.
- **The gear screen shows a damage breakdown** per weapon and spell, e.g. "arcane missiles: base 14 × (1 + 0.30 damage) = 18.2 per dart". The buckets stop being hidden.

## 9. The gear screen and the HUD

- **Gear screen** (Tab, or the pause menu):
  - the hero in the middle with the ten slots round them (the layout in section 2), and the bag beside it;
  - each piece's card on hover or focus;
  - the damage breakdown (section 8) and the total stats;
  - swap from the bag, salvage.
  - It works with the mouse, the keys and the pad, like the card picker.
- **HUD:** a small row of slot icons (rarity colour, +level) under the HP bar, replacing the spell row.
- **On the hero:** at least the head and chest show on the painted hero figures (`render/painted.py`): the cap or helmet, and the colour of the robe. The main hand changes the weapon's look if it reads at this size. This feeds the art handoff (M36).

## 10. The Guild and saves

| Today | With gear |
|-------|-----------|
| The guildmaster's ladders (Whetstone, Infirmary...) | **Unchanged.** Heroes still start stronger over time; the hall may overlap with affixes (CARDS rule 5) |
| Fortune Teller (+1 reroll), Exile Ledger (+1 banish) | Unchanged; they work on gear picks |
| Recruit's Kit (start a level higher: a free card pick) | a free gear pick |
| Arcane Wing (4th spell slot) | the 4th trinket slot |
| The trainer's per-hero trees | Unchanged. Royal Decree ("start with a rare card") becomes "start with a rare piece of your choice from three"; Encore Tour ("4 cards every 5th level") becomes "4 pieces" |
| The archivist's card shelf (unlock cards for loot) | **The armory shelf:** unlock gear bases for loot, same prices. Cards already unlocked unlock their piece; loot spent on Arcane Mastery or Weapons Master is refunded |
| (new) | **Saddlebags** (guildmaster): +1 bag space a level, 2 levels (N1) |
| Pacts, bestiary, journal | Unchanged; mimics get bestiary pages |
| `guild.json` unlocked card keys | Migrated once to gear keys (the old `RENAMED_CARDS` way); nothing a player bought is lost |

## 11. Code plan (how it maps onto what's built)

- **`config.GEAR`**: one `GearSpec` per base. It holds the slot, the power key, tags, the gate, the number rule, the +3/+6/+9 tricks and the legendary trick. Each points at the same effect hooks the cards use (`HeroStats` fields, `card_steps`), so the effects don't change.
- **`players/gear.py`** replaces `players/cards.py`:
  - `Equipment`: the slots, the bag, and pieces with their level, rarity and affixes;
  - `draw_offer`: the same gating, weighting and seeding;
  - `build_loadout` from equipment instead of the taken cards.
- **`ui/card_picker.py` -> `ui/gear_picker.py`**: the same layout plus the compare panel and UPGRADE. A new `ui/gear_screen.py`.
- **Drops** go through the existing pickup code (gems, loot), with a new `GearDrop` and its compare panel. **Chests** are a new landmark piece (`world/landmarks.py`); mimics are elites in `ai/` with one body per biome.
- **Tests:** the no-repeats test moves over (plus "one home per power"). The old card tests become gear tests with the same numbers, so an Ember Aura trinket at the matching level deals what Ember Aura V does today.

## 12. Build plan (M28.x)

| Step | Content |
|------|---------|
| M28.1 | **(Drafted in section 15.)** The data model and the ten slots. Every card turned into gear with **its current numbers**. The picker shows pieces (empty slot / +1 / swap with compare) plus UPGRADE. The bag and salvage. The HUD row. Arcane Mastery and Weapons Master cut. **Moved in from M28.3 (user):** affixes and the shared +1 rule. The game plays like today, just worn |
| M28.2 | Levels +0 to +9: the number rules and the +3/+6/+9 tricks for every piece, drafted with the user slot by slot |
| M28.3 | Affixes and rarity (section 7), legendary tricks; the gear screen and the damage breakdown. **Split (user, 2026-10-19):** M28.3a the systems (rarity power, the legendary look, the STATS page; **built**, section 18), then the 100 legendary tricks drafted with the user slot by slot (M28.3b onward), like M28.2 |
| M28.4 | Drops: elites, chests in the world (open, guarded, mimics), the boss rare+ pick; the Guild (Saddlebags) and the save migration (section 10) |
| M28.5 | The boss uniques (4.4, 2-3 per boss) and the new pieces (section 6) |
| M28.6 | Gear on the painted heroes (head, chest, main hand) |

Each step is drafted with the user before it's built, like the bosses.

## 13. Answered (user, 2026-10-18)

| # | Question | Answer |
|---|----------|--------|
| Q1 | Does a hero start with their weapon? | **Yes, the signature weapon is innate**; gear changes and adds to it |
| Q2 | How many slots? | **Nine, with the gloves split into main hand + off-hand** ("hand and offhand, not just hands"): ten in all |
| Q3 | What goes where? | First: "I haven't decided yet if gear pieces will have preset archetypes... we need to dive a bit deeper." Then: **fixed homes**, each power in one slot; **main hand = the hero line (hero-only), head = statuses and elements, off-hand = patterns and rhythm** |
| Q4 | How do you get +1? | **The same base again**, from a drop or an offer; "you can also choose on level up to upgrade an existing piece rather than choose another rolled one" (UPGRADE, 4.1) |
| Q5 | What happens to a swapped-out piece? | **A small bag of spares.** "The bag gets salvaged into loot at the end of a run, or you can choose to do so at any time per item. This is a way for players to not be locked into their build if they made a mistake" |
| Q6 | Where does gear come from? | **Level-ups (main), elites (~15%), bosses (a rare+ pick and a unique), and chests in the world** |
| Q7 | Highest level? | **+9**: numbers on most steps, a new trick at +3, +6, +9 |
| Q8 | What does rarity change? | **More and bigger affixes, "but also stronger power; legendaries should feel LEGENDARY"** |
| Q9 | Should arcane vs physical matter? | **Simplify**: only "+damage" and "+elemental damage" |
| Q10 | Mount gear? | **Not in M28** |
| N1 | The bag | **3 spares, +2 from a Guild ladder; swap anywhere except a sealed boss arena** |
| N2 | What can UPGRADE do? | **+1 to any worn piece** (below +9); it costs the whole pick |
| N3 | Chests | (no option picked) "add mimic chance, it's cute": **6-8 per biome, half guarded, plus mimics** (~1 in 10, a mini-fight, epic+ drop) |
| N4 | Rarity numbers | **The steeper set: ×1.0 / 1.15 / 1.3 / 1.5 / 2.0** |
| N5 | Boss uniques | **Several per boss** (2-3, different slots), one drops per kill |
| N6 | Offer mix | Lean late, but "**more swaps than +1, since we have the upgrade button for +1**" |
| N7 | Main hand early? | **Guaranteed among the three at level 2** |
| N8 | Other heroes' attacks as gear? | **Not in M28** (parked: "borrowed attacks") |

## 14. Still open

Nothing blocking: the next questions come with each build step (M28.1's draft first). Small numbers to settle on the way: the elite drop chance (15%), the chests' luck bonus, the mimic's chance and its moves, the Saddlebags' prices, the number rule per piece.

## 15. M28.1 draft (2026-10-18; waiting for the user's OK)

**Scope answers (user):**
1. **Affixes come in M28.1**, so plain stats don't vanish. The rarity power boost (×1.15-×2.0), legendary tricks and the full gear screen stay in M28.3.
2. **Levels use a shared +1 rule now** (15.3); M28.2 adds the +3/+6/+9 tricks on top.
3. **A base's old card rarity is its minimum** (15.2).
4. **Hand-made names now** (15.6, to trim).
5. **The picker:** "I will be wearing multiple pieces, so displaying just one worn piece underneath is not enough; the upgrade screen should be separate." So: a "now wearing" strip under **each** offer card, and **UPGRADE opens its own screen** (15.4).
6. **A basic gear screen on Tab** (15.5).

### 15.1 What M28.1 builds

- `config.GEAR`: the 100 bases (15.6). Each keeps its card's key, so `guild.json` unlocks, banishes and the bestiary need no migration. Arcane Mastery and Weapons Master are removed; both were in the pool from the start, so there's nothing to refund.
- `players/gear.py` in place of `players/cards.py`: `Equipment` (ten slots, the bag), `Piece` (base, level, rarity, affixes), the offer draw, `build_loadout` from what's worn.
- The level-up picker (15.4), the UPGRADE screen, the gear screen with the bag (15.5), the HUD slot row (replacing the spell row).
- Everything else plays as today: the same effects, the same numbers at +0, the same XP curve and pick count.

### 15.2 Offers

1. **Roll a rarity** (the card weights 100/45/18/6/2, luck shifts them).
2. **Pick a base** that can appear at that rarity: its **minimum** is its old card rarity (Kindling uncommon+, Glass Cannon rare+, capstones legendary only), the gates are met, it's unlocked and not banished, and it's the hero's own (main-hand pieces and the 5 hero rolls are hero-only). Weighted ×1.5 when it shares a tag with what you wear (as now).
3. **What it becomes:** a new piece for an empty slot, +1 to the same base if you wear it, or a swap if its slot is full. No two cards in one offer are the same base.
4. **Lean** (N6): once 6+ slots are filled, swaps ×1.5. The archetype lean stays, counting worn pieces and their levels.
5. **Level 2** (N7): one of the three is always a main-hand piece.
6. **Affixes are rolled** when the piece is drawn (15.3), seeded like the offer.
- **Rings and trinkets:** if every ring or trinket slot is full, taking one asks which to replace (the old one goes to the bag).
- BANISH removes that base for the run; SKIP still heals 15%; REROLL is the next draw; Fortune adds a 4th card; Encore Tour, Royal Decree ("a rare piece or better"), Recruit's Kit and Arcane Wing (the 4th trinket) work as their card versions did.

### 15.3 Levels and affixes

**Levels** (a shared rule until M28.2):
- Each +1 adds **+10% of the power's main number** (Broadhead's +15% per enemy passed becomes +16.5% at +1, +21% at +4; Frostwalkers' 3 s of ice becomes 3.3 s).
- **Spells** use their real levels first: trinket +0..+4 = spell I..V, then +10% damage per level to +9.
- **Pieces whose power has no number** (Phase Darts, Phoenix, Overflow...) get **+5% damage per level** (bucket A) instead.
- Each piece's main number is one line in `config.GEAR`, so any can be retuned.

**Affixes** (the generic cards, CARDS 6.1):
- How many: common 0, uncommon 1, rare 2, epic 3, legendary 3.
- How big: the card's C/U/R/E/L value at the piece's rarity.
- No two lines on one piece are the same stat.
- **Gated like the cards:** Potency and Affliction need a status; Quickened needs a spell; Lingering needs something that lasts; Elementalist needs an element. The gate is checked when the piece is drawn.
- **Some only roll at some rarities:** Vampiric uncommon+; Piercing uncommon+ and never for the dwarf or bard; Multishot rare+.
- **Boots only:** Quick Recovery and Extra Roll.
- **Capped like the card stacks:** a stat counts at most as many lines across everything you wear as the card's old max copies (5 for most; Piercing and Multishot 3; Extra Roll 1). Extra lines show greyed out with "(max)".
- Prospector (loot) and Elementalist are affixes too.

**Salvage** (proposal): loot = 20 / 40 / 80 / 160 / 320 by rarity × (1 + 0.5 × level). A rare +2 gives 160.

### 15.4 The picker and the UPGRADE screen

```
+--------------+  +--------------+  +--------------+
| RARE    FEET |  | UNCOMMON HEAD|  | EPIC TRINKET |
| Windrunners  |  | Cinderveil   |  | Ember Amulet |
| +30% speed   |  | 10% of hits  |  | Ember Aura:  |
| 2 s after a  |  | burn         |  | burns within |
| roll         |  |              |  | 2.5 tiles    |
| +11% move    |  | +25 max HP   |  | +17% atk spd |
| +5% evasion  |  |              |  | +3 armor     |
|              |  |              |  | +12% area    |
+--------------+  +--------------+  +--------------+
 wearing:          wearing:          wearing:
 Ashwalkers +2     EMPTY             2 of 3 trinkets
 (swap: to bag)                      (fills slot 3)
  [UPGRADE...]   [REROLL 3]   [BANISH 0]   [SKIP]
```

- Each card: the slot and rarity at the top (the frame in the rarity's colour), the name, the power, the affixes, and "+2 -> +3" when it's a +1.
- Under **each** card, its own **wearing** strip: what's in that slot now (name, +level), EMPTY, or how many ring/trinket slots are free. A swap says "(swap: to bag)".
- **UPGRADE...** opens a separate screen: every worn piece in the ten-slot layout, each with its "+N -> +N+1" line and what it adds. Picking one spends the level-up; **Back** returns to the offer. Pieces at +9 are greyed.
- The same keys, mouse and pad as today; hotkeys R / B / X stay, **U** for UPGRADE.
- Single player pauses while it's up; in multiplayer it doesn't (as now).

### 15.5 The gear screen (Tab)

- **Tab** (pad: Back/Select) or the pause menu opens it. Single player pauses; multiplayer doesn't.
- It shows the ten slots in the paper-doll layout (section 2) and the 3-space bag, with each piece's full card on focus.
- **Swap in** a bagged piece (the worn one goes to the bag), or **salvage** any piece (it shows the loot first). There's no swapping inside a sealed boss arena (N1).
- If the bag is full when a piece would go in, this screen comes up to choose what to salvage.
- The damage breakdown and the total-stats page come in M28.3.

### 15.6 Names (draft: to trim)

**Main hand** (hero-only):

| Hero | Card -> piece |
|------|---------------|
| wizard (staffs) | Storm Caller -> **Stormcaller Rod**; Conductor -> **Copperwire Staff**; Supercell -> **Thunderhead Rod**; Phase Darts -> **Ghostwood Staff**; Ball Lightning -> **Crackle Staff**; Chain Lightning -> **Chainbolt Staff**; Seeker -> **Wyrmseeker Staff**; Resonance -> **Humming Staff**; Implosion -> **Gravewell Staff**; Arcane Storm (legendary) -> **Stormheart Staff**; Orbiting Darts -> **Orrery Staff** |
| dwarf (axes) | Ricochet -> **Rebound Axe**; Hang Time -> **Hoverhead Axe**; Homeward Fury -> **Homesick Axe**; Tether -> **Chainlink Axe**; Cyclone (legendary) -> **Whirlwind Axe**; Splitting Axe -> **Doublebit Axe** |
| huntress (bows) | Arrow Rain -> **Cloudburst Bow**; Broadhead -> **Broadleaf Bow**; Hunter's Mark -> **Bloodhound Bow**; Steady Aim -> **Stillwater Bow**; Deadeye (legendary) -> **Farsight Bow**; Split Arrow -> **Splitbranch Bow** |
| princess (wands) | Prism -> **Prismatic Wand**; Focus -> **Spyglass Wand**; Spectrum -> **Chroma Wand**; Point Blank -> **Duelist's Wand**; Refraction (legendary) -> **Kaleido Scepter**; Converge -> **Crossbeam Wand** |
| bard (lutes) | Crescendo -> **Fortissimo Lute**; Lullaby -> **Cradlesong Lute**; Syncopation -> **Offbeat Lute**; Dissonance -> **Sourstring Lute**; Grand Finale (legendary) -> **Showstopper Lute**; Sheet Music -> **Songbird Lute** |

**Off-hand:** Cross Fire -> **Compass Orb**; Starburst -> **Sunwheel**; Rear Guard -> **Hindsight Orb**; Spiral -> **Nautilus Shell**; Twin Lanes -> **Twinned Quiver**; Echo -> **Canyon Horn**; Frenzy -> **War Drum**; Spray and Pray -> **Pepperbox**

**Head:** Kindling -> **Cinderveil Hood**; Wildfire -> **Blazecrown**; Venom -> **Viper Mask**; Virulence -> **Plaguebeak**; Frostbite -> **Rime Hood**; Shatter -> **Glassfrost Helm**; Static -> **Stormvane Helm**; Serrated -> **Thornhelm**; Hemorrhage -> **Bloodtrail Cowl**; Thermal Shock -> **Steamcrown**; Toxic Current -> **Galvanic Mask**

**Chest:** Thorn Mail -> **Brambleguard**; Ward Charm -> **Wardweave Robe**; Heavy Plate -> **Anvil Plate**; Glass Cannon -> **Shattercoat**; Retaliation -> **Grudge Mail**; Untouched -> **Spotless Tunic**; Berserker -> **Wolfpelt**; Bulwark -> **Bastion Plate**; Juggernaut (legendary) -> **Mountainhide**; Aegis (legendary) -> **Sunward Aegis**; Phoenix (legendary) -> **Phoenix Mantle**

**Feet:** Riposte -> **Fencer's Boots**; Slipstream -> **Windrunners**; Close Call -> **Hairsbreadth**; Scorched Trail -> **Ashwalkers**; Momentum -> **Gallopers**; Fleet Strike -> **Wingheel Sandals**. Hero-only: Blink (wizard) -> **Phasewalkers**; Shoulder Charge (dwarf) -> **Ramhorn Boots**; Backflip (huntress) -> **Tumbler Boots**; Pirouette (princess) -> **Dancing Slippers**; Drop the Beat (bard) -> **Stompers**

**Rings:** Volatile -> **Powderkeg Ring**; Chain Reaction -> **Domino Ring**; Soul Harvest -> **Reaper's Band**; Surge -> **Ascendant Band**; Bloodlust -> **Fang Ring**; Giant Slayer -> **Slingstone Ring**; Veteran -> **Grizzled Signet**; Golden Hoard -> **Hoarder's Ring**; Bounty -> **Bountymark Ring**; Beacon -> **Beckoning Ring**; Fortune -> **Fourleaf Ring**. Legendary: Overflow -> **Brimful Ring**; Pandemic -> **Contagion Ring**; Pack Leader -> **Packmaster Ring**

**Trinkets:** Orbiting Daggers -> **Bladewheel Charm**; Ember Aura -> **Ember Amulet**; Frost Nova -> **Winterheart**; Spirit Wolf -> **Wolfcall Whistle**; Rune Trap -> **Runestone Pouch**; Poison Flask -> **Witch's Flask**; Storm Cloud -> **Stormjar**; Healing Totem -> **Mender's Totem**; Fire Wand -> **Firefly Lantern**; Bone Turret -> **Skull Sentry**

The card's own name stays as the name of its **power**, so CARDS.md still reads right: Wyrmseeker Staff, power "Seeker".

### 15.7 Tests and docs

- Card tests become gear tests with the same numbers; new tests for:
  - one home per base, and the no-repeats rule over affixes;
  - the offer kinds (new / +1 / swap) and the level-2 main-hand rule;
  - UPGRADE, the bag, salvage, the affix caps;
  - the +1 rule, and a trinket at +4 matching the spell at V.
- `CARDS.md` gets a note that it now describes the powers; `GEAR.md` and the README describe the gear.
- No engine changes.

## 16. Built: M28.1 (2026-10-18)

Everything in section 15, with these changes found while building:

- **Chain Lightning is a wizard-only trinket** (the Chainbolt Charm), not a main-hand piece. Its four payoffs (Stormcaller Rod, Copperwire Staff, Thunderhead Rod, Crackle Staff) are main-hand pieces and need it worn, so in the same slot they could never come up. Main hand 34 pieces, trinkets 11.
- **The Bloodtrail Cowl (Hemorrhage) brings its own bleed** (10% of hits). Serrated (the Thornhelm) is the only other bleed source, and it shares the head slot, so Hemorrhage could never come up. `GearSpec.mods` / `needs` carry this; a test checks no power needs a piece only its own slot holds.
- **How an offer picks a base** (the "old rarity = minimum" answer, kept): the base is drawn first, weighted by its minimum rarity's weight (100/45/18/6/2, luck lifting the rare ones), then a new piece rolls its rarity like a card did and is raised to that minimum. Drawing the rarity first, as the cards did, left only ~6 common bases for 58% of the rolls once the plain stats became affixes, so Seeker or Soul Harvest came up in half the offers. With bases first, across five heroes x 60 picks the new pieces came out about 56% uncommon, 31% rare, 8% epic, 4% common, 2% legendary, and over those 60 picks the offers were about 20% new pieces, 60% swaps and 20% +1s.
- **The pause menu** got a "Gear (Tab)" button, after Settings. **The pad's X** opens the gear screen in play.
- **Salvage** credits the run's loot at once (a shard flies to the hero). At the run's end the bag is salvaged and what was worn is listed on the summary ("Gear: ...", `RunStats.gear`).
- **The +1 rule's "main number"** is the card's first helpful number. Phoenix (one revival) and Fortune (one extra card) grow +5% damage a level instead. Heavy Plate, Spray and Pray and Frenzy have only a downside number, so they grow damage too; their downsides never grow.
- **Code:**
  - `config.GEAR` (100 `GearSpec`s) and `GEAR_*`, `AFFIXES`, `SPELL_GROW`;
  - `players/gear.py` (`Piece`, `Offer`, `Equipment`, `draw_offer`, `eligible`, `affix_pool`);
  - `players/cards.py` keeps the effect layer (`card_steps`, `gate_met`, `loadout_from_steps`);
  - `Progress.gear` replaces the card list;
  - `ui/gear_picker.py` replaces `ui/card_picker.py`; `ui/gear_screen.py` is new;
  - spells past +4 grow through `HeroStats.spell_boost` / `spell_params(boost)`;
  - the HUD's spell row became the gear row.
- **Tests:** `tests/test_m28_1.py`. The older milestone tests that checked card effects now put the cards straight on the hero (`tests/gear_helpers.py`).


## 17. M28.2: the +3 / +6 / +9 tricks (2026-10-18; all 9 batches APPROVED as written, not built yet)

**Rules (user, 2026-10-18):**
1. **Twist, twist, mastery.** +3 is a small twist on how the power plays, +6 a second twist, and +9 a big MASTERY that makes the piece feel finished. Tricks are new behaviour; the numbers already grow +10% a level.
2. **Never a repeat.** A trick never does what another piece's power, an affix, a boss unique or another trick already does.
3. **The +10% stays.** The +3, +6 and +9 levels also give their +10% (or a spell level); the trick comes on top.
4. **One slot at a time:** off-hand, head, feet, chest, rings, trinkets, then the main hand hero by hero. The user reviews each batch before the next.

Tricks name their numbers so they can be built as written; every number becomes a `config` line.

### 17.1 Batch 1: off-hand (8 pieces, 24 tricks) -- APPROVED as written (user, 2026-10-18)

| Piece (power) | +3 twist | +6 twist | +9 MASTERY |
|---------------|----------|----------|------------|
| **Compass Orb** (Cross Fire: every 4th attack also fires at 90°, 180°, 270°) | **Needle:** each cross turns 45° from the last, so they alternate + and × | **North star:** cross shots destroy the first enemy shot they touch | **Cardinal:** the cross comes every 2nd attack |
| **Sunwheel** (Starburst: every 10th attack, 8 shots all round) | **Pinwheel:** the burst's shots curve as they fly, sweeping like a pinwheel | **Pain turns the wheel:** every hit you take counts as 2 attacks toward the next burst | **Corona:** a second ring of 8 fires 0.3 s later, set between the first ring's shots |
| **Hindsight Orb** (Rear Guard: every attack also fires one shot behind you, 60%) | **Over the shoulder:** the rear shot aims at the nearest enemy in your back half, not straight back | **Watchful:** an enemy that comes within 2 tiles behind you is shot at once, out of turn (at most once a second) | **Eyes in the back:** the rear shot becomes a full copy of your attack at 100%: every projectile, the fan, and every effect on it |
| **Nautilus Shell** (Spiral: an extra shot each attack, 37° further round each time) | **Growing shell:** the spiral shot grows as it flies, reaching ×2 size and +30% damage at the end of its range | **Double helix:** two spiral shots, turning opposite ways | **Golden angle:** the spiral turns 137.5° a shot, and fires 1 more for every 3 enemies within 8 tiles (up to +3) |
| **Twinned Quiver** (Twin Lanes: every shot flies as two, half a tile apart, 65% each) | **Linked:** twins that hit two different enemies link them for 2 s; damage one takes, the other takes 25% of | **Drift:** the twins drift apart as they fly, from 0.5 to 2 tiles, sweeping a wider lane | **Triplets:** every shot flies as three lanes (65% each) |
| **Canyon Horn** (Echo: every 6th attack happens twice) | **Reverb:** the echo goes at a different target, the nearest enemy that isn't the one you aimed at | **Rolling echo:** a kill by an echo brings the next echo 1 attack sooner | **Canyon:** every echo comes three times: the attack, its echo, and an echo of the echo at 60% |
| **War Drum** (Frenzy: attack twice as fast for 3 s after a kill; -20% range) | **Drumroll:** each kill during a frenzy adds 1 s to it (up to 6 s) | **Unshaken:** in a frenzy you can't be slowed or rooted (webs, curses, chill, mud...) | **War dance:** the -20% range is gone, and each frenzy starts with a drum beat that dazes enemies within 3 tiles for 0.5 s (bosses aren't dazed) |
| **Pepperbox** (Spray and Pray: shots split in two at half range, 60% each; -25% range) | **Second barrel:** the halves split once more, at three-quarter range | **Powder flash:** each split gives off a flash: enemies within 1 tile of it take 30% of the shot | **Buckshot:** the -25% range is gone, and pieces of one shot that hit the same enemy count as one hit with +25% |

**New things these bring** (each lives on one trick only):
- cancelling enemy shots (Compass Orb +6);
- shots that grow as they fly (Nautilus Shell +3);
- linking two enemies (Twinned Quiver +3);
- shrugging off slows and roots (War Drum +6);
- dazing (War Drum +9);
- hits you take counting toward your attacks (Sunwheel +6).

### 17.2 Batch 2: head (11 pieces, 33 tricks) -- APPROVED as written (user, 2026-10-18)

**Two changed when built (user, 2026-10-18; see 17.12):** Plague doctor (Plaguebeak +6) is "toxic ground can't hurt you", and Splinters (Glassfrost Helm +6) throws 6 ice shards.

The statuses, as built (CARDS.md section 3):
- burn: 4/s a stack, 3 s, up to 5;
- poison: 2/s a stack, 6 s, up to 5;
- chill: -10% speed a stack; 5 stacks freeze for 1.5 s;
- shock: +15% damage taken, 2 s;
- bleed: 3/s a stack, 4 s, up to 5.

Bosses take statuses at half strength and are never frozen.

| Piece (power) | +3 twist | +6 twist | +9 MASTERY |
|---------------|----------|----------|------------|
| **Cinderveil Hood** (Kindling: 10% of hits burn) | **Kindle:** your 4th hit in a row on one enemy always burns | **Smoke:** burning enemies can't see you past 6 tiles: they stop shooting and walk closer | **Pyre:** an enemy at 5 burn stacks burns twice as fast for 3 s |
| **Blazecrown** (Wildfire: +30% damage to burning enemies) | **Fanned flames:** your hits on a burning enemy restart its burn's clock | **Heat haze:** burning enemies' shots fly 25% slower | **Bonfire:** the bonus grows with the fire: +10% per burn stack on the enemy (up to +50%) instead of a flat +30% |
| **Viper Mask** (Venom: 10% of hits poison) | **Fang:** your crits poison with 2 stacks | **Toxic blood:** an enemy that hits you takes 2 poison stacks | **Neurotoxin:** an enemy at 5 poison stacks is rooted for 1 s (once every 4 s per enemy; bosses aren't rooted) |
| **Plaguebeak** (Virulence: poison stacks to 10 and lasts 50% longer) | **Incubation:** at 8 or more stacks, poison ticks 50% faster | **Plague doctor:** enemy poison can't stick to you | **Black death:** at 10 stacks, poison also takes 5% of the enemy's current HP each second (1% for bosses) |
| **Rime Hood** (Frostbite: 10% of hits chill) | **Cold snap:** your first hit on each enemy always chills | **Hoarfrost:** frozen enemies can't be pushed and block enemy shots like a wall | **Permafrost:** a frozen enemy chills every enemy touching it, 1 stack a second |
| **Glassfrost Helm** (Shatter: frozen enemies take x1.5 and burst into ice shards on death) | **Brittle:** chilled enemies (not frozen yet) take x1.15 from you | **Splinters:** the ice shards chill what they hit (1 stack) | **Shatterpoint:** hitting a frozen enemy ends the freeze with a shatter: it takes the hit again and throws its shards (bosses aren't frozen, so never) |
| **Stormvane Helm** (Static: 10% of hits shock) | **Build-up:** each hit on a shocked enemy adds +5% to its shock, up to +30% on top of the +15% | **Ground fault:** a shocked enemy standing in water, a bog or a puddle takes 20 a second | **Tempest:** an enemy shocked 3 times within 6 s is struck from the sky: 60 to it and everything within 1.5 tiles |
| **Thornhelm** (Serrated: 10% of hits bleed) | **Rend:** the first time an enemy reaches 5 bleed stacks, it takes 40 at once | **Open wounds:** bleeding enemies can't heal (shaman pollen, regrowth, a boss's drink) | **Exsanguinate:** a bleeding enemy below 15% HP dies at once (a boss takes 200 instead, once every 10 s) |
| **Bloodtrail Cowl** (Hemorrhage: its own 10% bleed; bleed ticks x2 while the enemy moves) | **Panic:** bleeding enemies below half HP run from you for 1 s (once each) | **Spurt:** a bleeding enemy that dashes, leaps or charges (boar, bull, mantis...) takes its bleed x4 while it does | **Bloodhound:** bleed ticks x3 while the enemy moves (not x2), and bleeding enemies show on your minimap |
| **Steamcrown** (Thermal Shock: burning + chilled enemies burst, 10 per burn stack, 2 tiles; uses up the chill) | **Scald:** everything the burst hits gets 1 burn stack | **Pressure:** the burst is 0.5 tiles wider for every burn stack it used | **Geyser:** the burst no longer uses up the chill: an enemy can burst again every 2 s while it burns and is chilled |
| **Galvanic Mask** (Toxic Current: shocking a poisoned enemy spreads its poison to 2 nearby) | **Live wire:** the spread poison also shocks what it lands on | **Battery:** each spread gives you a charge (up to 5); with 5, your next attack shocks everything it hits | **Galvanize:** the poison spreads to every enemy within 3 tiles, at its full stacks |

**New things these bring** (one trick each): blinding (Cinderveil +6), status immunity for you (Plaguebeak +6), frozen enemies as cover (Rime Hood +6), percent-of-HP damage (Plaguebeak +9), water conducting shock (Stormvane +6), stopping enemy healing (Thornhelm +6), executes (Thornhelm +9), fear (Bloodtrail +3), lightning from the sky (Stormvane +9).

**Watch for:** Kindle (+3, 4th hit always burns) and Cold snap (+3, first hit always chills) are both "a sure status"; their triggers differ. Pyre, Neurotoxin and Rend all fire at 5 stacks, each with a different effect.

### 17.3 Batch 3: feet (11 pieces, 33 tricks) -- APPROVED as written (user, 2026-10-18)

**Four settled when built (user, 2026-10-18; see 17.13):** Draft (Windrunners +3) is boss bodies and bumping enemies; Aerial (Tumbler +9) is double fire speed while rolling and 0.5 s after; Crowd surf (Stompers +6) is just the +10% per enemy; Air step (Wingheel +9) covers every enemy ground zone and every ground attack, bosses' included.

The roll, as built: about 4 tiles in 0.25 s, untouchable the whole way, one charge back every 5 s. The last five pieces are each one hero's own.

| Piece (power) | +3 twist | +6 twist | +9 MASTERY |
|---------------|----------|----------|------------|
| **Fencer's Boots** (Riposte: the first attack within 1.5 s of a roll's start always crits) | **Disarm:** the riposte hit cancels that enemy's next attack (a wind-up in progress stops) | **Second thrust:** the first two attacks after a roll crit, not one | **En garde:** a riposte crit that kills gives the roll charge back at once |
| **Windrunners** (Slipstream: +30% move speed for 2 s after a roll) | **Draft:** while slipstreaming you pass through enemies' bodies | **Afterimage:** each roll leaves an image of you for 1 s; enemies attack it instead | **Jet stream:** the slipstream lasts as long as you keep moving, ending 0.5 s after you stop |
| **Hairsbreadth** (Close Call: each enemy shot you roll through takes 0.1 s off the roll's cooldown) | **Graze:** each shot you roll through heals you 1 HP | **Deflect:** shots you roll through fly back at whoever shot them, at 50% of their damage | **Untouchable:** a roll through 5 or more shots keeps you untouchable 1 s after it ends |
| **Ashwalkers** (Scorched Trail: rolls leave burning patches) | **Creeping fire:** each patch lights one more next to it, once, toward the nearest enemy | **Bellows:** a roll across one of your old patches makes it flare: 30 to everything on it | **Firewalk:** rolls go 50% farther and leave a solid line of fire, no gaps, each patch lasting 5 s |
| **Gallopers** (Momentum: + damage equal to half your move speed bonus) | **Charge:** after 2 s of walking without stopping, your next attack deals +40% | **Hoofbeats:** every 10 tiles you walk, the ground cracks under the nearest enemy within 6 tiles: 25 damage | **Full gallop:** the bonus counts your whole move speed bonus, not half, and riding a mount counts as +50% |
| **Wingheel Sandals** (Fleet Strike: +1% crit chance per 4% move speed bonus) | **Quickstep:** each crit gives +10% move speed for 1 s (stacks to +30%) | **Featherweight:** pushes and pulls on you are halved | **Air step:** at +40% move speed or more you skim above the ground: shockwaves, pools, stomps and other ground attacks miss you |
| **Phasewalkers** (wizard: Blink, the roll is a 5-tile teleport ending in a shock nova) | **Displacement:** the spot you left gets a nova too, at 50% | **Swap:** blinking onto an enemy (landing within 1 tile of it) swaps you two | **Blink storm:** one roll can blink up to 3 times within 1 s, each with its nova, before the cooldown starts |
| **Ramhorn Boots** (dwarf: Shoulder Charge, enemies the roll runs into take 25 and are shoved 2.5 tiles) | **Bowling:** an enemy shoved into another knocks it too: both take 25 | **Battering ram:** the charge breaks walls, trees and crates it runs into | **Rampage:** each enemy the charge hits carries it 1 tile farther (up to +4) |
| **Tumbler Boots** (huntress: Backflip, starting a roll looses 5 arrows at 60% in a 40° fan) | **Double flip:** a second fan comes as the roll ends | **Quick draw:** backflip arrows have double your crit chance | **Aerial:** you keep shooting while you roll |
| **Dancing Slippers** (princess: Pirouette, starting a roll spins a ring of 10 shots of her colours) | **Encore spin:** a second, smaller ring (5 shots) comes as the roll ends | **Dizzy:** enemies hit by the ring aim 90° off with their next shot | **Prima:** the ring has 1 more shot for every enemy within 5 tiles (up to 20) |
| **Stompers** (bard: Drop the Beat, a free x1.5 beat as each roll ends) | **Double drop:** the free beat also comes as the roll starts | **Crowd surf:** enemies don't stop your roll; each one you pass adds +10% to the free beat (up to +50%) | **Amplifier:** the free beat leaves an amp on the ground for 4 s; your beats go off from it too, at 60% |

**New things these bring** (one trick each):
- interrupting attacks (Fencer's +3);
- passing through bodies (Windrunners +3);
- decoys (Windrunners +6);
- throwing shots back (Hairsbreadth +6);
- fire that creeps (Ashwalkers +3);
- distance walked as a trigger (Gallopers +6);
- mounts counting (Gallopers +9);
- resisting pushes and pulls (Wingheel +6);
- dodging ground attacks (Wingheel +9);
- swapping places (Phasewalkers +6);
- breaking terrain with the roll (Ramhorn +6);
- attacking while rolling (Tumbler +9);
- confusing aim (Slippers +6);
- a second place your attack comes from (Stompers +9).

**Watch for:**
- Fencer's +9 is the only trick that gives a roll back.
- Firewalk (+9) makes rolls longer. The planned Emberstriders (section 6: burning footprints while you *walk*) stay a separate piece.

### 17.4 Batch 4: chest (11 pieces, 33 tricks) -- APPROVED as written (user, 2026-10-18)

**Four changed or settled when built (user, 2026-10-18; see 17.14):** Bedrock (Mountainhide +3) became Glance; Dress code (Spotless +6) covers every ground attack; Ashes (Phoenix +3) leaves a ring of fire; Eternal day (Aegis +9) is just the slow fill.

Brambleguard and the Wardweave Robe are spells (levels II-V on +1..+4). Mountainhide, the Sunward Aegis and the Phoenix Mantle only come as legendaries (level 15+).

| Piece (power) | +3 twist | +6 twist | +9 MASTERY |
|---------------|----------|----------|------------|
| **Brambleguard** (Thorn Mail: attackers take 5 + 30% of the hit back) | **Barbs:** an enemy your thorns hurt bleeds (1 stack) | **Overgrowth:** stand still 1 s and a bramble ring grows round you (1.5 tiles): 10 a second to enemies in it | **Wild hedge:** thorns also hurt every enemy within 2 tiles of the attacker |
| **Wardweave Robe** (Ward Charm: a 25 shield, back after 4 s without a hit) | **Static weave:** when the shield breaks, it shocks everything within 2 tiles | **Overcharge:** while the shield is full, your attacks deal +15% | **Second ward:** once the shield has been full for 3 s, a second layer (half its size) forms on top |
| **Anvil Plate** (Heavy Plate: no hit takes more than 10% of your max HP; -15% move) | **Tempered:** each hit the plate caps gives +1 armor for 5 s (up to +10) | **Lighter steel:** the -15% move is gone | **Anvil stance:** after standing still 0.5 s, hits are capped at 5% instead of 10% |
| **Shattercoat** (Glass Cannon: x1.4 damage, -30% max HP) | **Crystal clear:** you see where enemy shots will go, a faint line 0.3 s ahead of each | **Prism skin:** after 6 s without being hit, the next hit is blocked completely | **Diamond:** the multiplier is x1.6 while you haven't been hit for 5 s |
| **Grudge Mail** (Retaliation: when hit, a shockwave deals 30 and pushes, every 3 s at most) | **Recoil:** the shockwave also throws you 1 tile away from whoever hit you | **Rising grudge:** each hit you take while it's cooling down adds +10 to the next shockwave (up to +50) | **Seething:** no cooldown, but it only goes off on hits of 10 or more |
| **Spotless Tunic** (Untouched: +30% damage while above 90% HP) | **Clean getaway:** dropping below 90% HP gives +30% move speed for 2 s | **Dress code:** above 90% HP, you take 25% less from status ticks and the ground (burns, poison, pools) | **Immaculate:** between 50% and 90% HP the bonus still counts, at half (+15%) |
| **Wolfpelt** (Berserker: +1% damage per 1% HP missing) | **Thick fur:** below 50% HP you take 10% less damage | **Bloodrage:** below 30% HP you attack 30% faster | **Last stand:** below 15% HP you can't drop under 1 HP for 3 s (once every 30 s) |
| **Bastion Plate** (Bulwark: +1% damage per 10 max HP) | **Fortify:** every 10 max HP above your hero's base also gives 0.1 HP a second | **Garrison:** within 2 tiles of a wall, you deal +20% | **Citadel:** your shield counts as max HP for the bonus |
| **Mountainhide** (Juggernaut: +2% damage per armor; you can't evade) | **Bedrock:** armor also cuts the damage of statuses on you | **Tremor:** your steps shake the ground: 5 a second to enemies within 1.5 tiles while you walk | **Peak:** armor counts twice for the damage bonus |
| **Sunward Aegis** (Aegis: healing past full HP becomes shield, up to half your max HP) | **Radiant:** while that shield holds, enemies within 1.5 tiles burn (1 stack a second) | **Corona burst:** when that shield breaks, it bursts for its full size as damage within 3 tiles | **Eternal day:** the shield never fades, and slowly fills itself up to a quarter of your max HP |
| **Phoenix Mantle** (Phoenix: once a run, rise at 50% HP in a burst of fire) | **Ashes:** the burst gives everything it hits 3 burn stacks | **Rebirth:** after rising you're untouchable for 2 s | **Undying flame:** you rise twice a run, not once |

**New things these bring** (one trick each):
- a second bleed source (Brambleguard +3);
- seeing shots ahead (Shattercoat +3);
- blocking a whole hit (Shattercoat +6);
- throwing yourself clear (Grudge Mail +3);
- protection from the ground (Spotless +6);
- cheating death without dying (Wolfpelt +9);
- fighting near walls (Bastion +6);
- an aura from walking (Mountainhide +6).

**Watch for:** Anvil Plate +6 and Shattercoat's Diamond touch their own downside or multiplier. That's growing their own power, not another piece's.

### 17.5 Batch 5: rings (14 pieces, 42 tricks) -- APPROVED as written (user, 2026-10-18)

**Three changed when built (user, 2026-10-18; see 17.15):** Legend (Grizzled +9) is +1% max HP a level; Loyal (Packmaster +6) brings a turret back; Hunter's pay (Bountymark +6) puts the piece in your bag.

The Brimful, Contagion and Packmaster rings only come as legendaries (level 15+).

| Piece (power) | +3 twist | +6 twist | +9 MASTERY |
|---------------|----------|----------|------------|
| **Powderkeg Ring** (Volatile: kills have a 15% chance to explode, 40% of the killing hit, 1.5 tiles) | **Big bang:** elites and bigger always explode | **Short fuse:** each kill that doesn't explode adds +5% to the next one's chance (back to 15% on a bang) | **Powder keg:** an explosion deals 40% of the killing hit plus 10% of the enemy's max HP |
| **Domino Ring** (Chain Reaction: enemies killed by an explosion explode too) | **Fuse line:** chain explosions go off 0.1 s apart, each +10% bigger than the last | **Clean sweep:** a chain of 5 or more drops a gem worth 5 kills' XP | **Domino effect:** an enemy hit by 2 explosions of one chain explodes too, dead or not |
| **Reaper's Band** (Soul Harvest: kills heal 1 HP) | **Reap:** elite kills heal 10 | **Grim:** kills within 1 s of the last one heal double | **Reaper:** kills heal 1% of your max HP if that's more than 1 |
| **Ascendant Band** (Surge: level-ups heal 20% and blast enemies away) | **Rising:** the blast also deals 10 per level you have | **Ascend:** an UPGRADE pick sets off a surge too | **Apotheosis:** every 5th level also gives a free extra gear pick |
| **Fang Ring** (Bloodlust: each kill +1% damage for 10 s, up to +30%) | **Feeding frenzy:** a kill in one hit (an enemy at full HP) counts twice | **Slow fade:** after the 10 s, the stacks fall off one a second instead of all at once | **Apex:** the cap is +50%, and at the cap your hits make enemies bleed |
| **Slingstone Ring** (Giant Slayer: +40% damage to enemies with more max HP than you) | **Long odds:** +1% more for every 100 HP the enemy has over you (up to +30% more) | **Toppled giant:** a big enemy you kill drops a loot cache worth 5 kills | **Goliath's bane:** against bosses the bonus is doubled (+80%) |
| **Grizzled Signet** (Veteran: +1% damage per level) | **Hard-won:** from level 20 on, each level counts twice | **Drilled:** every 10th level also gives an UPGRADE pick on top of the gear pick | **Legend:** the bonus also counts for your spells and summons |
| **Hoarder's Ring** (Golden Hoard: +1% damage per 50 loot this run, up to +50%) | **Miser:** loot from salvaging gear counts double for the hoard | **Golden armor:** every 500 loot this run gives +1 armor (up to +10) | **Dragon's hoard:** no cap |
| **Bountymark Ring** (Bounty: every 25th kill drops a cache worth 25 kills; enemies are 15% faster) | **Big game:** a cache from an elite kill is worth double | **Hunter's pay:** a cache holds a piece of gear 10% of the time | **Dead or alive:** the enemy speed-up is gone |
| **Beckoning Ring** (Beacon: 30% more enemies come for you) | **Rally:** the extra enemies drop 50% more XP | **Moth to flame:** the extra enemies run straight at you, archers included | **Lighthouse:** every 60 s a wave comes for you; clear it within 20 s for a free gear pick |
| **Fourleaf Ring** (Fortune: +1 card in every offer) | **Clover:** one piece of every offer is rare or better | **Charmed:** +1 reroll for every 5 levels you gain | **Four leaves:** offers hold 5 pieces |
| **Brimful Ring** (Overflow: crit chance over 100% becomes crit damage, x2) | **Brim:** a crit on an enemy at full HP applies crit damage twice | **Splash:** crits splash 25% of their damage onto enemies within 1 tile | **Deluge:** each crit adds +2% crit damage for 5 s (up to +50%) |
| **Contagion Ring** (Pandemic: a dying enemy's statuses spread to 2 nearby) | **Airborne:** the spread reaches enemies up to 5 tiles away | **Mutation:** each spread adds 1 stack | **Plague:** statuses spread while the enemy lives too, to 1 nearby every 3 s |
| **Packmaster Ring** (Pack Leader: summons use your crits and statuses; +1 wolf, +1 turret) | **Alpha:** your summons deal +25% to enemies you hit in the last 2 s | **Loyal:** a summon that dies comes back 3 s later | **The pack:** +1 more wolf and +1 more turret, and when you're hit your wolves rush whoever hit you |

**New things these bring** (one trick each):
- gem rewards (Domino +6);
- gear picks from levels and waves (Ascendant +9, Grizzled +6, Lighthouse +9);
- gear in loot caches (Bountymark +6);
- armor from loot (Hoarder's +6);
- enemies that close in (Beckoning +6);
- returning summons (Packmaster +6).

**Watch for:**
- Several rings give a gear or UPGRADE pick; they're spread over different triggers (levels, waves).

### 17.6 Batch 6: trinkets (11 pieces, 33 tricks) -- APPROVED as written (user, 2026-10-18)

A trinket's +1 to +4 are its spell's levels II-V (shown in brackets). The tricks at +3 (with level IV), +6 and +9 come on top. The Chainbolt Charm is the wizard's.

**One changed when built (user, 2026-10-19; see 17.16):** heroes never carry statuses, so Cleansing light (Mender's +3) ends what enemies and bosses put on you instead: slows and roots, stone, rads, the Snow King's chill and ice, shrinking.

| Piece (spell; its levels II-V) | +3 twist | +6 twist | +9 MASTERY |
|--------------------------------|----------|----------|------------|
| **Chainbolt Charm** (Chain Lightning: every 1.5 s a bolt jumping to 2 more; +30% damage, 25% faster, +1 jump, +40% and 20% faster) | **Grounding:** a bolt with nobody left to jump to strikes the ground: a 1.5-tile burst at 50% | **Overload:** every 5th cast jumps twice as many times | **Eternal arc:** bolts may jump back to an enemy they already hit, once each |
| **Bladewheel Charm** (Orbiting Daggers: 2 daggers circle you, 12 each; +1 dagger, +30%, +1 dagger, wider and faster) | **Fling:** when you roll, the daggers shoot out along it and come back | **Breathing ring:** every 3 s the orbit swells to twice its width and back | **Blade storm:** +2 daggers, in two rings turning opposite ways |
| **Ember Amulet** (Ember Aura: burns enemies within 2.5 tiles; +20% size, 2 stacks a pulse, +20% size, 30% faster) | **Warmth:** each pulse heals you 1 HP for every 5 enemies it burns | **Flare-up:** every 5th pulse is a blast of 3 stacks | **Sunfire:** the aura grows 0.2 tiles for every enemy burning in it (up to +2 tiles) |
| **Winterheart** (Frost Nova: every 4 s chills everything within 4 tiles twice; 15% faster, +25% size, +1 stack, double damage and 15% faster) | **Cold heart:** when you're hit, the next nova comes 1 s sooner | **Ice armor:** each nova gives you 5 shield for every enemy it chills (up to 25) | **Avalanche:** every 3rd nova is twice as wide and freezes at once (not bosses) |
| **Wolfcall Whistle** (Spirit Wolf: a wolf hunts the nearest enemy, 15 a bite; +30%, +1 wolf, 25% faster, +1 wolf) | **Scent:** wolves go for the enemy you hit last | **Howl:** every 10 s the wolves howl: enemies within 4 tiles of a wolf deal 20% less damage for 3 s | **Dire wolves:** the wolves are twice as big, bite twice as hard, and make their prey bleed (1 stack) |
| **Runestone Pouch** (Rune Trap: a rune every 3 s bursts for 40 when stepped on; +30%, 25% faster, +30% size, +3 runes and +30%) | **Rune lines:** runes within 3 tiles of each other link with a line; enemies crossing it take 10 | **Seeking runes:** runes drift toward the nearest enemy within 4 tiles | **Runeburst:** when you roll, every rune bursts at once |
| **Witch's Flask** (Poison Flask: a pool of poison for 3 s; +25% size, 2 flasks, 25% faster, 2 stacks a tick) | **Bubbling:** the pool grows 50% over its life | **Witch's brew:** one flask in 4 is a random brew: fire, frost or shock instead of poison | **Cauldron:** pools that touch merge into one, lasting as long as the newest |
| **Stormjar** (Storm Cloud: a cloud follows you, striking and shocking an enemy every 1.5 s; +30%, 25% faster, 2 strikes, +40% and +30% reach) | **Downpour:** the cloud rains: the ground under it is a puddle | **Thunderhead:** the cloud strikes whoever hit you last, first | **Eye of the storm:** a second cloud circles you, striking 0.75 s after the first |
| **Mender's Totem** (Healing Totem: every 12 s a totem heals 3 HP a second round it for 6 s; +30%, chills enemies, 25% sooner, +40% and +30% size) | **Cleansing light:** stepping into the totem's ring ends the statuses on you | **Carried:** the totem follows you slowly instead of staying put | **Tree of life:** the totem stays until the next one is planted, so one is always up |
| **Firefly Lantern** (Fire Wand: a burning bolt at the nearest enemy every 1.2 s; +30%, 25% faster, burns twice, +40% and 20% faster) | **Glow:** an enemy hit by a bolt lights up: your crit chance against it is +10% for 2 s | **Moth:** bolts go for burning enemies first | **Will-o'-wisps:** every 5th bolt leaves a wisp where it lands for 3 s, burning everything within 1.5 tiles |
| **Skull Sentry** (Bone Turret: a turret every 10 s shoots for 8 s; +30%, pierce +1, 25% faster, 2 turrets) | **Ossuary:** turrets rise from the body of your last kill, not next to you | **Calcify:** when a turret's time ends, it bursts into 8 bone shards (15 each) | **Bone legion:** +1 turret at a time, and turrets stay until replaced |

**New things these bring** (one trick each):
- weakening enemy damage (Wolfcall +6);
- links between your traps (Runestone +3);
- traps that move (Runestone +6);
- mixed brews (Witch's Flask +6);
- puddles you make, which work with the Stormvane Helm's Ground fault (Stormjar +3);
- cleansing (Mender's +3);
- a totem that follows you (Mender's +6);
- spell targets that answer whoever hit you (Stormjar +6).

**Watch for:** Cold heart (Winterheart +3) and Thunderhead (Stormjar +6) both react to being hit, with different effects.

### 17.7 Batch 7: the wizard's main hand (10 pieces, 30 tricks) -- APPROVED as written (user, 2026-10-18)

Arcane missiles: 3 darts that fan out, then home on what you aim at. The first four pieces need the Chainbolt Charm worn (a trinket). The Stormheart Staff only comes as a legendary.

| Piece (power) | +3 twist | +6 twist | +9 MASTERY |
|---------------|----------|----------|------------|
| **Stormcaller Rod** (Storm Caller: lightning jumps to +1 enemy) | **Conducting darts:** a dart hitting an enemy your bolt shocked jumps once to the nearest other enemy, at 50% | **Through walls:** jumps may go to enemies out of sight | **Thunderlord:** +1 more jump; a bolt that jumps 5+ times strikes everything it hit once more, at 30% |
| **Copperwire Staff** (Conductor: jumps reach 30% farther and fade less) | **Resistor:** the first jump doesn't fade at all | **Overcurrent:** a jump to an enemy near the end of its reach deals +40% | **Superconductor:** jumps never fade |
| **Thunderhead Rod** (Supercell: bolts shock; jumps go for shocked enemies, +25% to them) | **Charged air:** your darts deal +10% to shocked enemies | **Downdraft:** with 3 or more shocked enemies within 5 tiles, Chain Lightning casts twice | **Superstorm:** each bolt hit also shocks every enemy within 1.5 tiles of the one it hit |
| **Crackle Staff** (Ball Lightning: bolts crackle where they hit for 2 s) | **Sticky:** the crackle clings to the enemy it hit and moves with it | **Crackling chain:** every jump leaves a crackle, not just the first hit | **Thunderball:** every 5th cast sends a big ball rolling along the bolt's path for 3 s, crackling whatever it touches |
| **Ghostwood Staff** (Phase Darts: darts fly through walls and trees) | **Haunt:** a dart that went through a wall deals +25% | **Spectral:** darts go through enemy shields and armoured fronts (the ogre's front, the shieldbearer's shield) | **Ghost sight:** you see enemies through walls within 12 tiles, and your darts home on them |
| **Wyrmseeker Staff** (Seeker: darts turn twice as fast and find a new target when theirs dies) | **Persistence:** a dart that loses its target flies 30% faster from then on | **Hunter-seeker:** darts go for the enemy with the least HP in reach | **Endless hunt:** a dart goes on after its hit to a new target, up to 3 hits (70% after the first) |
| **Humming Staff** (Resonance: each earlier dart on the same enemy within 1 s: +15%, up to +60%) | **Sustain:** the window is 2 s, not 1 | **Resonant ring:** at +60%, the enemy gives off a ring: 30 to everything within 2 tiles | **Perfect pitch:** the cap is +120% |
| **Gravewell Staff** (Implosion: a dart's hit drags enemies within 2.5 tiles 0.8 tiles toward it) | **Crush:** enemies dragged into each other take 10 | **Event horizon:** enemy shots within 1.5 tiles of the hit are dragged in too | **Singularity:** every 6th cast's first hit opens a well that keeps pulling for 1.5 s (bosses aren't moved) |
| **Stormheart Staff** (Arcane Storm: a dart that kills fires a new one at the next enemy, 3 per cast) | **Squall:** the new dart goes for the enemy nearest to you | **Tempest:** up to 5 new darts a cast | **Maelstrom:** new darts can fire new darts too, with no cap a cast; each is 80% of the one before |
| **Orrery Staff** (Orbiting Darts: a dart that misses swings round you and tries again, once) | **Planets:** swinging darts hit the enemies they pass on the way round | **Epicycle:** they try twice, not once | **Gravity assist:** a dart that swung round you comes back 50% faster with +50% damage |

**New things these bring** (one trick each):
- a bonus for long reach (Copperwire +6), the far-range opposite of Point Blank;
- going through shields and armoured fronts (Ghostwood +6);
- dragging enemy shots (Gravewell +6);
- going for the weakest enemy (Wyrmseeker +6).

### 17.8 Batch 8: the dwarf's and the huntress's main hands (12 pieces, 36 tricks) -- APPROVED as written (user, 2026-10-18)

The dwarf throws axes that pierce everything and fly back to him. The huntress's longbow fires single arrows. The Whirlwind Axe and the Farsight Bow only come as legendaries; the Splitbranch Bow is the huntress's spell (levels II-V on +1..+4).

| Piece (power) | +3 twist | +6 twist | +9 MASTERY |
|---------------|----------|----------|------------|
| **Rebound Axe** (Ricochet: axes bounce off walls and fly on, 2 bounces, instead of turning back) | **Bank shot:** each bounce adds +20% damage | **Pinball:** axes also bounce off big enemies (elites, bosses), once | **Carom:** 5 bounces, and after the last the axe flies straight home |
| **Hoverhead Axe** (Hang Time: where a throw ends, the axe hovers 0.4 s, hitting all it touches every 0.2 s) | **Saw:** each hit while hovering adds +10% to the next | **Hold it there:** the axe keeps hovering for as long as you hold the attack | **Buzzsaw:** the hovering axe hits everything within 1.5 tiles |
| **Homesick Axe** (Homeward Fury: axes deal +50% on the way back) | **Homing:** on the way back, the axe bends toward enemies within 2 tiles of its path | **Welcome home:** each catch gives +10% attack speed for 2 s (up to +30%) | **Hearth:** the way back always crits |
| **Chainlink Axe** (Tether: a chain to each axe in flight cuts all it crosses, 25%, every 0.3 s) | **Taut:** the chain deals 40% while its axe is at full range | **Shackle:** the first enemy the chain touches each throw is dragged along with the axe for 0.5 s | **Flail:** the axe swings once round you on its chain before coming back |
| **Whirlwind Axe** (Cyclone: a caught axe is thrown again at once at the nearest enemy, once a throw) | **Spin cycle:** the rethrow goes for the enemy with the most HP in reach | **Gale force:** up to twice a throw | **Eye of the cyclone:** each rethrow also throws a second axe at the second-nearest enemy |
| **Doublebit Axe** (Splitting Axe: as an axe turns home it splits into two halves, 60% each) | **Reunite:** halves that meet again on the way back become one axe with +30% | **Crossing:** the halves cross over once on the way back, in an X | **Quartering:** each half splits again, into four quarters at 40% |
| **Cloudburst Bow** (Arrow Rain: every 5th shot also rains 6 arrows within 3 tiles of your aim, 70%) | **Monsoon:** the rain falls round the enemy nearest your aim, not the aim itself | **Thunder rain:** each rain arrow that lands within 1 tile of another adds +20% to it | **Squall line:** every 5th shot rains twice, 0.4 s apart |
| **Broadleaf Bow** (Broadhead: +15% damage for each enemy the arrow has passed) | **Gathering speed:** each enemy passed makes the arrow 10% faster | **Run-through:** an arrow that passes 4 or more enemies comes back once along its path | **Broadside:** +30% per enemy passed |
| **Bloodhound Bow** (Hunter's Mark: every 4 s the toughest enemy in view is marked: x2 damage from you) | **Old scent:** the last mark stays 2 s after the next is placed, so two are marked | **Next quarry:** killing the marked enemy places the next mark at once | **Pack hunt:** your summons and allies deal x2 to the mark too |
| **Stillwater Bow** (Steady Aim: +25% crit chance while standing still) | **Held breath:** after 1 s still, your next arrow flies twice as fast | **Zen:** after 2 s still, crits deal +50% crit damage | **Still waters:** Steady Aim holds for 1 s after you start moving |
| **Farsight Bow** (Deadeye: crits pierce every enemy and fly twice as far) | **Follow-through:** a crit that pierces 3 or more enemies makes your next arrow come at once | **Second sight:** every 6th arrow is a sure crit | **Lightning arrow:** crit arrows strike at once: no flight time |
| **Splitbranch Bow** (Split Arrow: an arrow's first hit splits it into a 3-arrow fan at 50%; levels: +1 arrow, +30%, splits on every enemy, +2 arrows) | **Canopy:** the split arrows go for the 3 nearest enemies instead of a fan | **Bough:** arrows split on walls too | **Seed storm:** every split also throws 3 seeds that sprout thorns for 2 s: 10 a second within 1 tile |

**New things these bring** (one trick each):
- holding the attack to keep an axe up (Hoverhead +6);
- a chain that drags (Chainlink +6);
- shots with no flight time (Farsight +9);
- splitting on walls (Splitbranch +6).

**Watch for:** Quartering (Doublebit +9) splits the halves again. It's the axe's own split, on its way home, so it isn't the Pepperbox's second barrel.

### 17.9 Batch 9: the princess's and the bard's main hands (12 pieces, 36 tricks) -- APPROVED as written (user, 2026-10-18)

The princess fires a fan of rainbow colours. The bard's lute beats all round him (pulses). The Kaleido Scepter and the Showstopper Lute only come as legendaries.

| Piece (power) | +3 twist | +6 twist | +9 MASTERY |
|---------------|----------|----------|------------|
| **Prismatic Wand** (Prism: colours that hit the same enemy in one shot: +20% for each other colour) | **Full spectrum:** a hit by every colour of one shot is a crit | **Afterglow:** the bonus stays on the enemy 1 s, for your next shot | **Rainbow's end:** +30% for each other colour |
| **Spyglass Wand** (Focus: the fan narrows by 30%) | **Lens:** the middle colour deals +25% | **Pinpoint:** the fan keeps narrowing while you stand still, down to half | **Beam:** after 1 s still, the fan becomes one beam of every colour at once |
| **Chroma Wand** (Spectrum: red burns, blue chills, green poisons, yellow shocks, 20% each) | **Saturated:** each colour's chance is 30% | **Colour theory:** enemies carrying 2 or more of your colours' statuses take +15% from you | **Chromatic:** each colour's hit gives its status twice |
| **Duelist's Wand** (Point Blank: +40% damage to enemies within 4 tiles) | **Face to face:** within 2 tiles, +20% more on top | **Duel:** the first enemy you hit up close becomes your duelist: it takes +25% from you and deals you 25% less, until one of you falls | **Bladework:** point blank reaches 6 tiles and gives +60% |
| **Kaleido Scepter** (Refraction: each colour splits into 3 when it hits an enemy) | **Shards of light:** the split pieces go for the nearest enemies | **Radiant split:** split pieces are 50% bigger | **Infinite mirror:** split pieces that hit split again into 2, up to 3 times |
| **Crossbeam Wand** (Converge: your colours curve in and cross where you aim, then spread) | **Focal point:** enemies at the crossing take +40% | **Second crossing:** after crossing, the colours curve back and cross again 3 tiles on | **Lockstep:** the crossing point follows the enemy nearest your aim |
| **Fortissimo Lute** (Crescendo: each beat in a row that hits: +10%, up to +50%; a miss resets it) | **Fermata:** a miss drops it one step instead of resetting | **Climax:** at +50%, beats reach 25% farther | **Forte:** the cap is +100% |
| **Cradlesong Lute** (Lullaby: each beat heals 1 HP per enemy it hits, up to 5) | **Lullabied:** an enemy hit by 5 beats in a row falls asleep: it stands still until something hits it (bosses don't sleep) | **Duet:** your beats heal allies in their reach too (co-op) | **Mother's song:** 2 HP per enemy, up to 10 |
| **Offbeat Lute** (Syncopation: beats alternate, short and loud x1.6, wide and soft x0.7) | **Swing:** the loud beat comes 20% sooner after a soft one | **Polyrhythm:** every 3rd beat is both at once | **The drop:** the loud beat is x2.2 |
| **Sourstring Lute** (Dissonance: beats push enemies back and chill them) | **Clash:** an enemy pushed into a wall takes 15 | **Tritone:** chilled enemies are pushed twice as far | **Shriek:** beats chill twice (2 stacks) |
| **Showstopper Lute** (Grand Finale: every 8th beat x4 damage, x2 reach) | **Overture:** the first beat of a fight (after 5 s without hitting anything) is a finale | **Curtain call:** dropping below 30% HP sets off a finale at once (every 20 s at most) | **Magnum opus:** every 6th beat, not 8th |
| **Songbird Lute** (Sheet Music: each beat flings 3 notes, 9 each, at the nearest enemies in sight) | **Birdsong:** notes curve round walls to their target | **Chorus:** every 4th beat flings twice as many notes | **Aria:** each note hits everything within 1 tile of where it lands |

**New things these bring** (one trick each):
- a beam (Spyglass +9);
- a duel (Duelist +6);
- sleep, which breaks on any hit, unlike the War Drum's daze (Cradlesong +3);
- healing allies (Cradlesong +6);
- shots curving round walls (Songbird +3).

**Watch for:** Infinite mirror (Kaleido +9) splits pieces again on a hit. The Pepperbox splits at a distance, so they differ by trigger.

With this batch, all 100 pieces have their three tricks: **300 in all**.

### 17.10 Build plan (user, 2026-10-18: "slot by slot, test each")

| Step | Content |
|------|---------|
| M28.2a (**built** 2026-10-18, 17.11) | Off-hand: 24 tricks (17.1). Also the shared framework: a trick unlocks at its level, the picker and gear screen show "+3: Needle" and the next trick to come, every number in `config` |
| M28.2b (**built** 2026-10-18, 17.12) | Head: 33 (17.2) |
| M28.2c (**built** 2026-10-18, 17.13) | Feet: 33 (17.3) |
| M28.2d (**built** 2026-10-18, 17.14) | Chest: 33 (17.4) |
| M28.2e (**built** 2026-10-18, 17.15) | Rings: 42 (17.5) |
| M28.2f (**built** 2026-10-19, 17.16) | Trinkets: 33 (17.6) |
| M28.2g (**built** 2026-10-19, 17.17) | The wizard's main hand: 30 (17.7) |
| M28.2h (**built** 2026-10-19, 17.18) | The dwarf's and the huntress's: 36 (17.8) |
| M28.2i (**built** 2026-10-19, 17.19) | The princess's and the bard's: 36 (17.9) |

Each step comes with tests for every trick, a headless check, a report, and a stop for the user to playtest.

### 17.11 Built: M28.2a (2026-10-18)

The off-hand's 24 tricks and the shared groundwork, as approved, with these notes:

- **How tricks work:** a worn piece at +3 / +6 / +9 gives the flags `<key>+3` / `+6` / `+9` (`gear.trick_flags`). The names and texts are in `config.GEAR_TRICKS`, and every number is a `config` line (`NEEDLE_TURN`, `PINWHEEL_TURN`, `WATCHFUL`, `LINKED`, `DRUMROLL`, `WAR_DANCE`, `POWDER_FLASH`, `BUCKSHOT`...). `config.GEAR_DROP_DOWNSIDE` removes a power's negative numbers from a level on (the War Drum's and the Pepperbox's -range at +9).
- **On screen:**
  - the gear screen lists the unlocked tricks in full and "at +6: North star" for the next one;
  - a picker card lists the unlocked tricks' names;
  - a +1 that reaches a trick says so ("+5% damage, and NORTH STAR: ...").
- **Bug found and fixed:** `config.FRENZY_TIME` was defined twice. The squirrel boss's madness fill rate (0.015, M25.2) overwrote the War Drum's 3 s, so **since M25.2 a Frenzy lasted 0.015 s after a kill**. The boss's constant is now `FRENZY_FILL`, and a scan found no other name defined twice in `config.py`.
- **Second barrel (Pepperbox +3):** a split half's flight starts over at the split, as it always has (so the halves fly a full range again). "Three-quarter range" of the shot is therefore a quarter of the way into the half's own flight.
- **Buckshot (Pepperbox +9), as built:** each later piece of the same shot that hits an enemy it already hit deals +25%.
- **North star (Compass Orb +6)** checks along the whole step, with the other shot's own step added, so two fast shots can't slip through each other between frames.
- **Echo** now has its own count (`Player.echo_count`; echoes count toward it, as before), so Rolling echo can move it. Echo shots and kills are marked in `GameScene._attack`.
- **Starburst** now runs on a meter (`Player.burst_meter`: +1 an attack, the same rhythm as before), so Pain turns the wheel can add the hits you take (`Character.hits_taken`).
- **New pieces of the engine** (inside ascii_adventurers):
  - `systems/statuses.daze` (an enemy's clock stops; never a boss);
  - `Character.unshaken` (slows, roots and time-slow zones don't hold);
  - projectile fields `cancels`, `grow`, `drift`, `twin`, `gen`, `family`, `echo`;
  - links between enemies, in `combat.strike`.
- **Tests:** `tests/test_m28_2a.py`, 30 tests, at least one per trick.

### 17.12 Built: M28.2b (2026-10-18)

The head's 33 tricks, as approved, with these changes and notes:

- **Changed (user, 2026-10-18), because as written they did nothing or repeated the power:**
  - **Plague doctor (Plaguebeak +6):** heroes never carry statuses, so "enemy poison can't stick to you" had nothing to act on. Now: **toxic ground can't hurt you**. The bloated corpse's toxic cloud and the mold core's patches deal you no damage (`config.PLAGUE_DOCTOR`, zone kinds), and the Fallout King's toxic goo gives you no rads and no slow. His other rads (glow, hits, fallout) still count.
  - **Splinters (Glassfrost Helm +6):** the Shatter burst has always chilled 1 stack, so "the shards chill" repeated the power. Now: **the burst also throws 6 ice shards** (`SPLINTERS`, `ICE_SHARD_SHOT`) that fly 5 tiles, each hitting once for the burst's damage (`SHATTER[2]`) and chilling 1 stack. Like the burst, they don't crit or roll your statuses. Shatterpoint (+9) throws them too.
- **Whose trick it is:** a status trick belongs to the hero who applied the status (its `source`). The exceptions are Smoke (the hero the burning enemy is looking at) and Toxic blood (the hero being hit).
- **Pyre (+9 Cinderveil):** it starts when the burn *reaches* 5 stacks, not on every hit while at 5. It starts again only after the burn drops below 5.
- **Smoke (+6 Cinderveil):** the enemy's sight check fails past 6 tiles (`Brain.smoked`). It goes to where it last saw or heard you (that's "walks closer"); hitting it still tells it where you are.
- **Bonfire (+9 Blazecrown):** the 10% per stack and the 50% cap grow with Wildfire's +10% a level, like the flat 30% did.
- **Neurotoxin (+9 Viper Mask):** rooted, an enemy still thinks, aims and shoots, but its position is put back after its turn.
- **Ground fault (+6 Stormvane):** "water, a bog or a puddle" is any of `config.WET_TILES` under the enemy (water, bog, pond, mud, reeds, lily pads, scum, stagnant water, blood pool, clots, oasis). The game has no puddle tile, so the in-game text says "water, a bog or mud". The 20 a second scales with your status strength, and the shock's own +15% applies to it.
- **Rend (+3 Thornhelm):** the 40 scales with your status strength (physical). "The first time" is once per enemy, ever.
- **Open wounds (+6 Thornhelm):** it blocks `Actor.heal` and the four places that set HP directly: the myconid shaman's pollen, the fungal brute's regrowth, the field priest's heal and Nettle's healing on her blight.
- **Panic (+3 Bloodtrail):** a scared enemy skips its turn and walks straight away at its walking speed. Bosses and things that can't walk (towers, turrets) aren't scared.
- **Spurt (+6 Bloodtrail):** a "dash" is any step faster than 1.6x the enemy's walking speed (`SPURT[1]`), so it catches charges, leaps and dashes of every kind without a list. A strong knockback can count too.
- **Bloodhound (+9 Bloodtrail):** bleeding enemies are red diamonds on your minimap (`palette.PIN_BLOOD`), only those your own bleeds are on.
- **Geyser (+9 Steamcrown):** each enemy has a 2 s cooldown. While it burns and is chilled, a burst comes every 2 s from the burn and chill alone, with no new hit needed.
- **Live wire (+3 Galvanic Mask):** the shock it puts on can't set off another spread. Otherwise one spread would bounce round a crowd for ever.
- **Battery (+6 Galvanic Mask):** a charge comes from each spread that reaches at least one enemy. The charged attack's own hits (melee and pulses) and all its projectiles shock.
- **Galvanize (+9 Galvanic Mask):** the reach stays 3 tiles (the same as Toxic Current's); only the "2 nearest" limit goes.
- **New pieces of the engine** (inside ascii_adventurers):
  - `statuses.on_hero_hit` (the hit tricks);
  - `Statuses` fields `frozen_by`, `rooted`, `scared`, `cooldowns`, `shocks`, `pace`;
  - `Status.pyre` and `Status.extra` (Build-up, read by `vulnerability`);
  - `inflict(..., chain=False)`;
  - `RunRules.status_tricks` / `flee` / `enemy_shots`;
  - projectile fields `pace` (Heat haze) and `shocks` (Battery);
  - `Character.kindle` / `battery` / `shocking`.
- **Tests:** `tests/test_m28_2b.py`, 36 tests, at least one per trick. A scratch run with all 33 tricks on each hero against 14 real enemies of 10 kinds, 30 s each, ran clean. **Correction (found in M28.2d):** that run's tricks were dropped at the hero's first level-up (a loadout rebuild), a few seconds in. It was re-run in M28.2d with the tricks kept on for the whole 30 s, and it ran clean (17.14).

### 17.13 Built: M28.2c (2026-10-18)

The feet's 33 tricks, with these settled or noted:

- **Settled with the user (2026-10-18), because as written they were already true in the game:**
  - **Draft (Windrunners +3):** ordinary enemies have no solid bodies (you walk through them already). While slipstreaming, a **boss's body doesn't shove you** (`Boss.shove_heroes`), and **bumping enemies** (the tumbleweed, the pillbug) **pass through you**.
  - **Aerial (Tumbler Boots +9):** heroes could always attack mid-roll. Now **while you roll and 0.5 s after, your bow fires twice as fast** (`RunRules.weapon_dt`; it stacks with a Frenzy).
  - **Crowd surf (Stompers +6):** enemies never stopped a roll (only walls do), so it's just **+10% to the free beat for each enemy you roll past** (within 1 tile), up to +50%.
  - **Air step (Wingheel +9):** "+40% move speed" is your move speed stat plus Slipstream and Quickstep while they're on (`combat.move_bonus`). What it skims (`combat.skims`):
    - **every enemy zone:** toxic clouds, mold, burning straw and trails, webs, slime, the hag's curse and its root;
    - **ordinary enemies:** the colossus's stomp ring, the burrower's eruption, the sand golem's fist slam, the rootweaver's roots;
    - **bosses:** Froggy's belly flop landing; Khepri's burrow eruption; the Magus's fire runes; Proboscia's fever clouds; Ol' Spitter's churned-sand trail; the Fallout King's stomp, grate burst, fallout (burn and rads) and goo (rads and slow); Nettle's blight and thorn bursts; Love & Cuddles' tripwires (you don't trip them); The Fallen's root web, sap puddles and uproot landing; the fly agaric's slam, network eruption, toadstool lines and lit threads; the ink cap's pools, scrawl and burst; the puffball's mines, bound, squash, split landings and choking clouds; the necromancer's grasping hands and bone cage.
    - **Not counted:** things that fall from above (icicles, nettles, pinecones, mortars), bodies that ram you, thrown or lobbed shots, the Fallout King's meltdown wave (radiation that lead walls stop), and the Snow King's ice floor.
- **Disarm (Fencer's +3):** a riposte hit on an enemy that's winding up (`windup`) stops the wind-up. Otherwise the enemy's next attack within 3 s (`DISARM`) fizzles: its next volley of shots vanishes as it's fired, or its next hit on a hero does nothing. Bosses' wind-ups aren't stopped, but their next attack still fizzles. A riposte's shots carry it (`Projectile.riposte`), and so does a melee or pulse riposte.
- **Second thrust (+6):** both sure crits must come within Riposte's 1.5 s window.
- **Afterimage (Windrunners +6):** the image stands where the roll started (`roll.Afterimage`, a blinking copy). Enemies within sight go for it first (`AIContext.decoys`), and their shots stop on it. Bosses pick their own targets, so they aren't fooled.
- **Deflect (Hairsbreadth +6):** the shot becomes yours and flies straight back at whoever fired it, for 50% of its damage as plain damage (none of your bonuses, no crit).
- **Untouchable (+9):** it counts shots per roll, and the 1 s starts as the roll ends.
- **Creeping fire (Ashwalkers +3):** 0.5 s after a patch is laid, it lights one more next to it, toward the nearest enemy within 8 tiles (none near: no creep). The new patch doesn't creep.
- **Bellows (+6):** it works on any patch of yours from an earlier roll, once per patch per roll. The flare doesn't crit or roll statuses.
- **Firewalk (+9):** the patches already overlapped (0.8 tiles apart, 0.9 tiles big), so the line was already solid. Firewalk makes the roll 50% faster over the same 0.25 s, so it goes 6 tiles, and each patch lasts 5 s (x your duration bonus).
- **Charge (Gallopers +3):** walking counts while you move faster than 0.5 tiles/s. The charged attack resets the clock.
- **Hoofbeats (+6):** it counts the distance you walk (mounts and rolls included) and hits the nearest enemy within 6 tiles. The 25 doesn't crit or roll statuses.
- **Full gallop (+9):** a mount counts as +50% only for what hits while you ride (spells, summons), since you can't attack from the saddle.
- **Quickstep (Wingheel +3):** each crit adds a 1 s stack; with 3 already on, the oldest goes.
- **Featherweight (+6):** it halves every `combat.push` on you (shoves, knockbacks, pulls that use it). A boss's body putting you back outside it isn't halved (`push(full=True)`), so you can't end up inside a boss.
- **Swap (Phasewalkers +6):** it picks the enemy nearest the landing spot within 1 tile. You take its place and it takes yours. Bosses aren't swapped.
- **Blink storm (+9):** the 2 extra blinks cost no charge, and the roll's recharge waits while the 1 s window is open.
- **Bowling (Ramhorn +3):** an enemy that's charged into another (touching after the shove) knocks it on. Both take 25, and each pin is knocked once per roll.
- **Battering ram (+6):** anything solid and breakable just ahead of the charge breaks: walls, trees, crates, cactus, pillars that can be broken. Indestructible walls (rock, lair stone) still stop it.
- **Rampage (+9):** each enemy hit adds the time for 1 more tile to the roll, up to +4.
- **Quick draw (Tumbler +6):** it doubles the backflip arrows' crit chance (`strike(crit_x=)`).
- **Dizzy (Dancing Slippers +6):** an enemy hit by the ring has 3 s to fire. Its next volley turns 90 degrees, to one side or the other at random. Bosses aren't dizzied.
- **Prima (+9):** it counts enemies within 5 tiles as the roll starts.
- **Amplifier (Stompers +9):** the amp's beat has your beat's power and reach x 0.6. It doesn't count for Crescendo's streak or Lullaby's heal.
- **New pieces of the engine** (inside ascii_adventurers):
  - `combat.skims` / `drafting` / `move_bonus`;
  - `combat.blast(ground=)` and the bosses' `_blast(ground=)`;
  - `combat.push(full=)`;
  - `combat.pulse(origin=)`;
  - `strike(crit_x=)`;
  - projectile fields `riposte`, `plain`, `dizzy`, `crit_x`;
  - `Character` fields for each piece (`riposte_left`, `untouchable`, `walk_t`, `quick`, `storm_blinks`, `rampage`, `aerial`, `surfed`, `amps`, `images`...);
  - enemy `disarmed` / `dizzy`;
  - `RunRules.feet_tricks` (Creeping fire, the enemy clocks).
  - Drawing: `render/characters.draw_feet_marks` (afterimages, amps).
- **Tests:** `tests/test_m28_2c.py`, 36 tests, at least one per trick. Also two scratch runs:
  - every hero with all its feet tricks, rolling, against 16 real enemies for 30 s, ran clean. **Correction (found in M28.2d):** the tricks were dropped at the first level-up, a few seconds in; re-run in M28.2d with them kept on all the way, clean (17.14);
  - the boss and enemy tests (484) re-run with every hero skimming (Air step on everywhere) gave no errors. The 33 failures were all the ground attacks those tests expect to hit.

### 17.14 Built: M28.2d (2026-10-18)

The chest's 33 tricks, with these changed, settled or noted:

- **Changed or settled with the user (2026-10-18):**
  - **Bedrock -> Glance (Mountainhide +3):** heroes never carry statuses, and armor already cuts every hit a hero takes, ground ticks included, so neither "statuses" nor "ground damage" would change anything. Now: **enemy shots that hit you glance off harmlessly, 1% of the time per armor, up to 30%** (`GLANCE`; Tempered's armor counts). It's a way round Juggernaut's "can't evade", but only for shots.
  - **Dress code (Spotless Tunic +6):** there are no status ticks on heroes. Above 90% HP you take **25% less from every ground attack** (`combat.ground_cut`), the same list Air step skims (17.13): enemy zones, stomps, eruptions, shockwaves, pools, clouds, threads, roots, hands, the bone cage...
  - **Ashes (Phoenix Mantle +3):** the rising burst already gave 3 burn stacks. Now it **leaves a ring of 10 burning patches 2.5 tiles round you for 6 s** (`ASHES`).
  - **Eternal day (Sunward Aegis +9):** shields never fade in this game, so it's **just the slow fill: 2% of your max HP a second, up to a quarter of it** (`ETERNAL_DAY`).
- **"That shield":** the Ward Charm's and the Aegis's shields are one pool (`Character.shield`). So Radiant, Corona burst and Eternal day work on your shield whatever filled it, and Static weave and Corona burst both go off when it breaks.
- **Corona burst (+6):** "its full size" is what the shield held just before the hit that broke it. It's plain damage (no crit, no statuses).
- **Second ward (Wardweave +9):** after 3 s full, the shield jumps to 150% of the Ward Charm's size. The normal refill still only refills up to 100%.
- **Overcharge (+6):** it's +15% on your attacks (not spells), while the shield is at the Ward Charm's full size or more.
- **Tempered (Anvil +3):** each stack lasts its own 5 s (`Character.temper`). The armor counts for damage taken, Juggernaut and Glance.
- **Anvil stance (+9) and Overgrowth (Brambleguard +6):** standing still means slower than 0.1 tiles/s (`STILL_SPEED`; `Character.still_t`).
- **Overgrowth, Tremor:** every half second they deal half their damage a second, as your hits but without crits or statuses. The ring is drawn round you (`render/characters.draw_chest_marks`).
- **Wild hedge (+9):** the enemies round the attacker take what the thorns dealt to it, and Barbs makes them bleed too.
- **Crystal clear (Shattercoat +3):** a faint line from each enemy shot, as far as it'll fly in 0.3 s, drawn only for the hero wearing it. Lobbed shots aren't shown.
- **Prism skin (+6):** the blocked hit counts as being hit (the 6 s starts again). A "block" pops up, as it does for Glance.
- **Diamond (+9):** x1.6 / x1.4 on top, so the power's level growth still counts.
- **Recoil (Grudge +3):** "1 tile away" from where the hit came from, as a push that Featherweight doesn't halve.
- **Rising grudge (+6) and Seething (+9):** with +9 there's no cooldown left to build a grudge in, so the grudge only matters from +6 to +8. A hit of 10 or more is counted after armor and the plate, before the shield.
- **Clean getaway (+3):** it starts as HP drops from 90%-or-more to below (each time). Its +30% counts toward Air step.
- **Last stand (Wolfpelt +9):** the hit that would take you under 15% starts it if it's ready (and is capped at 1 HP if it would kill). For 3 s nothing takes you under 1 HP; then it waits 30 s.
- **Fortify (Bastion +3):** "your hero's base" is the hero's starting max HP (`config.HEROES`). The heal stops under the Famine pact and while irradiated, like regen.
- **Garrison (+6):** a "wall" is any solid tile that stops shots (walls, trees, rocks, crates), within 2 tiles of you; water doesn't count.
- **Undying flame (+9):** two Phoenix rises, then the Guild's Second Chance as before.
- **Lighter steel (Anvil +6):** `GEAR_DROP_DOWNSIDE` drops the -15% move from +6.
- **Tests:** `tests/test_m28_2d.py`, 35 tests, at least one per trick.
- **Scratch checks:**
  - The boss and enemy tests (484) re-run with Dress code always on gave no errors. 1 failure: a test that checks an exact damage number.
  - **A better stress harness** (`brawl.py`, scratch) keeps the powers and tricks on through the loadout rebuilds that level-ups cause, and checks every step that they're still there. It found that the M28.2b and M28.2c runs had lost their tricks at the first level-up. With it, every hero ran 30 s against 18 kinds of real enemies, all clean, with off-hand, head, feet and chest each worn at +9. A chest run with HP forced low each few seconds rose twice per hero (Undying flame) and exercised Last stand.

### 17.15 Built: M28.2e (2026-10-18)

The rings' 42 tricks, with these changed, settled or noted:

- **Changed with the user (2026-10-18):**
  - **Legend (Grizzled Signet +9):** "the bonus also counts for your spells and summons" was already true (their hits go through the same damage buckets). Now: **+1% max HP per level** (`LEGEND`), with Hard-won's double levels from 20.
  - **Loyal (Packmaster +6):** spirit wolves can't be hurt and turrets only run out of time, so nothing "dies". Now: **a turret whose time runs out stands again 3 s later where it stood, once** (`LOYAL`; `SpellState.waiting`).
  - **Hunter's pay (Bountymark +6):** there are no ground drops yet (M28.4). 10% of caches put **a piece rolled like an offer's straight into your bag**; a full bag salvages it into loot (`GameScene._bag_piece`, `Equipment.stash`).
- **"Elites and bigger", "elite kills"** (Big bang, Reap, Big game): an enemy with `espec.elite`, or a boss.
- **Big bang, Short fuse:** the luck roll still happens on every kill; a chain explosion or a big one counts as a bang for Short fuse.
- **A chain** (`run_rules.Chain`) is one Volatile explosion and everything it sets off. Each body bursts once a chain.
  - **Fuse line (+3):** each explosion of a chain waits 0.1 s after the chain's last one (`Player.fuses`), and is 1.1x the one before, in damage and radius.
  - **Clean sweep (+6):** once a chain, on its 5th explosion; the gem is worth 5x the XP of the enemy that started it.
  - **Domino effect (+9):** the living enemy's burst is 40% of the explosion hit it just took.
- **Reaper's Band:** Reap's 10 and Reaper's 1% replace the power's 1 HP, and Grim doubles that; the power's +10% a level counts on top of all three. "The last one" (Grim) is your last kill.
- **Rising (Ascendant +3):** area damage through your buckets (no crit, no statuses). **Ascend (+6):** any UPGRADE pick, the free ones too. **Apotheosis, Drilled, Charmed:** they count the level reached, so two levels at once still find the 5th or the 10th. The dev L key now sets off level-up tricks too (Surge did not go off on it before).
- **Feeding frenzy (Fang +3):** "in one hit" means the killing hit landed on an enemy at full HP (`Actor.one_hit`).
- **Slow fade (Fang +6):** each kill's stack still lasts its own 10 s; once stacks run out they go one a second at most (`Character.fade_t`).
- **Apex (Fang +9):** at 50 stacks your hits (the ones that apply statuses) put 1 bleed on.
- **Long odds (Slingstone +3)** adds to the 40% and isn't doubled by **Goliath's bane (+9)**, which doubles the 40% only. **Toppled giant (+6):** a "big enemy" is one Giant Slayer works on (more max HP than you); the cache is loot, like Bounty's.
- **Drilled (Grizzled +6):** the picker's button reads FREE UPGRADE while you have one, and using it doesn't spend the pick (`Progress.free_upgrades`). Unused, it waits for the next pick. If the free +1 maxes a piece the offer had a +1 for, the offer is redrawn.
- **Hoarder's Ring:** Miser adds the salvage loot to the hoard a second time (`Player.salvaged`). Golden armor counts the hoard (Miser's double included) and counts for damage taken, Juggernaut and Glance (`combat.bonus_armor`).
- **Dead or alive (Bountymark +9):** in co-op, enemies are faster while anyone wears Bountymark below +9.
- **Beckoning Ring:**
  - **"The extra enemies"** are the ones a chunk gets past what it would have without Beacon (`Spawner.beckoned`); the chunk rosters stay as they were.
  - **Rally (+3):** their gems are worth 1.5x, whoever kills them.
  - **Moth to flame (+6):** each is drawn to the nearest hero wearing it: it always knows where they are, and enemies that keep a distance (archers, camels...) keep 1-2 tiles instead (`drawn_to`, `MOTH`).
  - **Lighthouse (+9):** 6 of the biome's enemies come up 9-13 tiles round you, drawn to you; no waves in a boss arena. All of them dead within 20 s gives a gear pick (a toast says so).
- **Clover (Fourleaf +3):** if no piece of an offer is rare or better, the last one is redrawn as a new piece of rare or better. **Four leaves (+9):** 5 pieces, with Fortune's +1.
- **Brim (Brimful +3):** "full HP" before the hit; the crit multiplier is applied twice. **Splash (+6):** plain damage, after the hit. **Deluge (+9):** each crit adds its stack after it lands (up to 25 stacks, each lasting 5 s).
- **Plague (Contagion +9):** every 3 s an enemy carrying statuses from you spreads those (with Mutation's +1) to the nearest other enemy within reach.
- **Alpha (Packmaster +3):** "you hit" is your own attacks and spells, not summons. The +25% goes into the conditional bucket. **The pack (+9):** after a hit, your wolves go for whoever hit you for 5 s while it lives, wherever it is (`PACK_RUSH`).
- **Tests:** `tests/test_m28_2e.py`, 46 tests, at least one per trick.
- **Scratch check:** every hero wore all 14 rings at +9, plus the wolf, the turret and the ember aura, for 30 s against 18 kinds of real enemies, with the powers kept on through level-ups. It ran clean. Lighthouse waves came for each hero, two of them were cleared in time for the pick, and Hunter's pay bagged a piece.

### 17.16 Built: M28.2f (2026-10-19)

The trinkets' 33 tricks, with these changed, settled or noted:

- **Changed with the user (2026-10-19):** **Cleansing light (Mender's Totem +3):** heroes never carry statuses (only enemies do). Stepping into the ring now ends what enemies and bosses put on you: slows and roots (webs, howls, a hag's curse), stone, the Fallout King's rads, the Snow King's chill and ice, and Nettle's shrinking. It works on stepping in: standing in the ring doesn't clear what lands later, but stepping out and back in does. It works for every hero, as the healing does.
- **Chainbolt Charm:** the bolts carry `Projectile.charm` into `combat.chain_from`.
  - **Grounding (+3):** when no enemy is in reach for the next jump, the bolt bursts by the last enemy it hit, for 50% of that hit's damage (`GROUNDING`, x area). A bolt that used up all its jumps doesn't burst.
  - **Overload (+6):** every 5th cast's bolt has twice its total jumps.
  - **Eternal arc (+9):** new enemies are still picked first, and never the one the bolt is on.
- **Bladewheel Charm:**
  - **Fling (+3):** 6 tiles out along the roll and back over 0.6 s (`FLING`).
  - **Breathing ring (+6):** a 1 s swell every 3 s (`BREATHING`).
  - **Blade storm (+9):** the daggers split evenly into two rings. The outer one is 1.5x as wide and turns the other way.
- **Ember Amulet:**
  - **Flare-up (+6):** gives 3 stacks, or the pulse's own stacks if that's more, and shows a ring.
  - **Sunfire (+9):** counts the enemies burning inside the aura at each pulse. The growth lasts until the next pulse.
- **Winterheart:**
  - **Cold heart (+3):** 1 s comes off once per nova wait (the first hit), so a crowd can't set novas off back to back.
  - **Ice armor (+6):** the shield can go 25 over the Ward Charm's (`ICE_ARMOR`). It shares `Character.shield` with Ward and Aegis.
  - **Avalanche (+9):** freezes everything that isn't a boss by giving it full chill stacks. Bosses get the usual stacks.
- **Wolfcall Whistle:**
  - **Scent (+3):** "you hit" means your own attacks and spells, as with Alpha. The enemy has to be within the wolves' 12-tile sight of you. The pack's rush still comes first.
  - **Howl (+6):** cuts the damage those enemies deal heroes, in `Character.take_damage` before armor and shields (`Actor.howled`, `HOWL`).
  - **Dire wolves (+9):** twice the reach and collision size; drawn as a big wolf.
- **Runestone Pouch:**
  - **Rune lines (+3):** an enemy touching a line takes 10, at most once a second per line (`RUNE_LINES`). Runes have serials for this.
  - **Seeking runes (+6):** 2 tiles a second, stopped by walls.
  - **Runeburst (+9):** every rune bursts at the start of a roll.
- **Witch's Flask:**
  - **Bubbling (+3):** the radius grows evenly to 1.5x (`Zone.grow`).
  - **Witch's brew (+6):** every 4th flask thrown. The pool takes its status's colour and tag.
  - **Cauldron (+9):** only pools of the same brew merge. Their areas add up, the merged pool sits at their area-weighted centre, and it's capped at 3x a pool's radius (`CAULDRON_MAX`; without a cap a steady stream of flasks grows it forever). Its life is the newest pool's.
- **Stormjar:**
  - **Downpour (+3):** a "puddle" zone (2.5 tiles) on the ground under the cloud, moving with you. Enemies in it count as wet for Ground fault (Stormvane Helm +6; `statuses._wet`), and that's all a puddle does.
  - **Thunderhead (+6):** "whoever hit you last" is the last enemy whose hit got through (`Character.struck_by`). It's struck first while it's alive and within the cloud's reach.
  - **Eye of the storm (+9):** the second cloud circles you 2.5 tiles out and strikes 0.75 s after each of the first cloud's casts, with the same picking.
- **Mender's Totem:**
  - **Carried (+6):** 1.5 tiles a second, stopped by walls.
  - **Tree of life (+9):** a new totem replaces the old one; it never runs out.
- **Firefly Lantern:**
  - **Glow (+3):** the +10% counts for all your hits on the lit enemy, not only the bolts (`Actor.lit`).
  - **Moth (+6):** the nearest burning enemy in sight, else the nearest.
  - **Will-o'-wisps (+9):** counts bolts, Multishot's too. The wisp is a zone where the bolt stopped: burn every 0.5 s within 1.5 tiles (x area) for 3 s.
- **Skull Sentry:**
  - **Ossuary (+3):** the last kill's spot (`Character.kill_spot`) when it's within 15 tiles of you, else next to you.
  - **Calcify (+6):** also when a turret is replaced by a new one. The shards are summon shots.
  - **Bone legion (+9):** with Calcify, the replaced turret bursts.
- **Found, not fixed (ask):** `palette.py` defines `GAZE`, `RUNE` and `SHOT_SAND` twice; the later one wins. The spell rune (and its burst) is drawn in the Magus rune's orange, not the purple meant for it. Rune lines use the same `palette.RUNE`, so they match whatever is decided.
- **Tests:** `tests/test_m28_2f.py`, 36 tests, at least one per trick, plus a draw check of every trick's look.
- **Scratch check:** every hero wore every trinket at level V +9 (all 33 tricks) for 30 s against 18 kinds of real enemies, with the powers kept on through level-ups. It ran clean: no lost flags, no deaths.
  - All three brews came up, merged pools reached their cap, Ice armor reached 25 and Sunfire +2.
  - Howl caught 1-2 enemies each time.
  - Rune lines never formed while the bot rolled every 0.75 s, because Runeburst sets every rune off. Without rolls, a line was up a third of the time.

### 17.17 Built: M28.2g (2026-10-19)

The wizard's main hand's 30 tricks, with these changed, settled or noted:

- **Changed with the user (2026-10-19):**
  - **Ghost sight (Ghostwood Staff +9):** enemies are always drawn (there's no fog) and darts already home through walls, so it couldn't work as written. Now a dart that finds nothing near the aim homes on the nearest enemy within 12 tiles of you, walls or not (`combat._seek`, `GHOSTWOOD_SIGHT`). Enemies a wall hides from you within 12 tiles get a ghostly outline (`spell_fx.draw_ghost_sight`).
  - **Conducting darts (Stormcaller Rod +3):** Chain Lightning only shocks with Supercell (another main hand), so "an enemy your bolt shocked" is now "an enemy your bolt hit in the last 2 s" (`CONDUCTING`; `Actor.bolted`, set on the bolt's hit and every jump).
  - **Resonant ring (Humming Staff +6):** a dart hitting at +60% or more sets off the ring, at most once a second an enemy (`RESONANT_RING`). The ring hits the enemy itself too, and its radius grows with area.
- **Fixed (found here):** since M20, Storm Caller's "+1 jump" also went onto the wizard's darts (the weapon shell took `stats.chain`), so with the Stormcaller Rod every dart jumped once at 70%. Only a weapon that already chains gets the jumps now (`cards.build_loadout`); no hero's does since lightning became a spell. `tests/test_cards.py` had the old number and now expects 0.
- **Stormcaller Rod:**
  - **Conducting darts (+3):** the jump goes to the nearest other enemy within Chain Lightning's jump reach, with a clear line (unless +6), for 50% of the dart's damage as a lightning hit.
  - **Through walls (+6):** also for the Conducting jump.
  - **Thunderlord (+9):** "strikes everything it hit once more" is each enemy once, at 30% of the bolt's damage before any fading, with the arcs drawn again. The +1 jump comes before Overload doubles.
- **Copperwire Staff:**
  - **Overcurrent (+6):** "near the end of its reach" is past 75% of the jump reach. The +40% goes in bucket A, as Supercell's +25% does.
- **Thunderhead Rod:**
  - **Downdraft (+6):** the second bolt goes for another enemy if there is one, else the same. It doesn't count as a cast for Overload or Thunderball.
  - **Superstorm (+9):** on the bolt's first hit and every jump; 1.5 tiles, not grown by area.
- **Crackle Staff:**
  - **Sticky (+3):** when its enemy dies, the crackle stays where it fell (`Zone.follow`).
  - **Crackling chain (+6):** each jump's crackle is 30% of that jump's damage, as the first one is of the bolt's.
  - **Thunderball (+9):** the 5th cast's first bolt (not Multishot's extras) carries the path: where it was cast, where it hit, then each jump. When it ends, a "ball" zone (2.5 tiles) rolls the whole path end to end over 3 s, crackling as the crackle does (`Zone.path`, `zones.along`). A bolt that misses rolls from you to where it stopped.
- **Ghostwood Staff:**
  - **Haunt (+3):** any wall or tree the dart flew through on its way counts (`Projectile.haunted`).
  - **Spectral (+6):** the ogre's and the shieldbearer's fronts (`front_armor`) and the scorpion's front take a dart at full damage (`Character.spectral` during the hit). The snail's shell (its back) and the rubble crab's shell (it takes hits before its HP) aren't fronts and stay as they are.
- **Wyrmseeker Staff:**
  - **Persistence (+3):** once a dart, not again on every lost target.
  - **Hunter-seeker (+6):** "in reach" is the dart's own seek radius round the aim point.
  - **Endless hunt (+9):** the dart flies on through its target and seeks a new one it hasn't hit, with 8 tiles more flight at least (`ENDLESS_HUNT`). It works after any pierce the dart has.
- **Humming Staff:**
  - **Perfect pitch (+9):** 8 darts counted (8 x 15% = +120%). The ring's +60% mark stays the same.
- **Gravewell Staff:**
  - **Crush (+3):** an enemy the drag moved that ends up overlapping another body (another dragged one, or the enemy the dart hit) takes 10, and so does that body; each at most once a hit.
  - **Event horizon (+6):** enemy shots within 1.5 tiles move 0.8 tiles toward the hit (the drag's pull). Lobbed ones are in the air and stay.
  - **Singularity (+9):** "cast" is an attack (`Character.attacks`, which every-Nth cards count too). The well is the drag's 2.5 tiles and pulls 2 tiles a second (`SINGULARITY`, `Zone.pull`); bosses and things that never move stay put.
- **Stormheart Staff:**
  - **Squall (+3):** the enemy nearest you within 8 tiles of you; with nobody that close, the next one by the kill as before.
  - **Maelstrom (+9):** new darts could already fire new darts within the cap. Maelstrom lifts the cap and makes each new one 80% of the dart that fired it.
- **Orrery Staff:**
  - **Planets (+3):** while it swings toward its new target, a dart flies through the others it meets, hitting each once. A dart whose target died stops at the next one, as before.
  - **Epicycle (+6):** a dart that only hit enemies on the way round (Planets) may still swing again.
  - **Gravity assist (+9):** from its first swing on: 1.5x speed, and +50% damage in bucket A.
- **Caught in the full test run:** two of this step's new config names were already taken, `TEMPEST` (Stormvane Helm +9) and `GHOST_SIGHT` (the debug bots' sight). The later definition wins in Python, so both would have broken the old ones. They're now `STORM_TEMPEST` and `GHOSTWOOD_SIGHT`, and `config.py` has no duplicate names.
- **Tests:** `tests/test_m28_2g.py`, 35 tests, at least one per trick, plus a draw check of the new looks. `tests/test_m28_2a.py`'s "not built yet" check moved from the Wyrmseeker to a dwarf piece.
- **Scratch check:** the wizard wore all ten staffs' powers and all 30 tricks (ignoring slots) with Chain Lightning at V for 30 s against 19 kinds of real enemies, through level-ups. It ran clean: no lost flags, no errors.
  - Every trick went off except Downdraft, which needs 3 shocked enemies within 5 tiles. Things die too fast with all ten staffs on.
  - On the Thunderhead Rod alone, Downdraft went off once in 33 casts. Thunderlord went off 6 times in 33 casts on the Stormcaller Rod alone, and Planets 4 times on the Orrery Staff alone (darts seldom miss in a crowd).

### 17.18 Built: M28.2h (2026-10-19)

The dwarf's and the huntress's main hands' 36 tricks, with these changed, settled or noted:

- **Changed with the user (2026-10-19):**
  - **Hold it there (Hoverhead Axe +6):** holding the attack is how you fire, so every axe would hover for good in a fight. While you hold it, a hovering axe stays up to 2 s longer (`HOLD_IT`); let go and it comes home (`Character.trigger`, set from the input each step).
  - **Next quarry (Bloodhound Bow +6):** a dead mark was already replaced at once. Now killing the mark marks the enemy in view nearest where it fell, not the toughest.
  - **Pack hunt (Bloodhound Bow +9):** summons already dealt x2 to the mark (their hits are yours), and allies would only matter in co-op, which isn't designed yet. Now when the mark dies, every enemy within 3 tiles of it is marked for 3 s (`PACK_HUNT`, `Character.marks`, `combat.marked`).
- **Rebound Axe:**
  - **Bank shot (+3):** counts wall bounces and Pinball's bounce, in bucket A.
  - **Pinball (+6):** on the way out only. The axe glances off the body like off a wall, and what it already hit may be hit again (as Ricochet's wall bounces allow).
  - **Carom (+9):** the 5th bounce sends it straight home from the wall.
- **Hoverhead Axe:**
  - **Saw (+3):** +10% per hit so far in this hover, bucket A.
  - **Buzzsaw (+9):** 1.5 tiles, not grown by area.
- **Homesick Axe:**
  - **Homing (+3):** the axe heads for the first enemy along its way home that's within 2 tiles of the line and not hit yet this leg, then goes on home. It can only be caught while it's heading home.
  - **Welcome home (+6):** speeds up the weapon's clock, as Frenzy does (`RunRules.weapon_dt`, `Character.welcome`).
  - **Hearth (+9):** every hit on the way back is a sure crit.
- **Chainlink Axe:**
  - **Taut (+3):** "at full range" is 80% or more of the axe's range away from you.
  - **Shackle (+6):** the first enemy the chain cuts each throw follows the axe's movement for 0.5 s (`combat.push`: bosses and things that never move stay put).
  - **Flail (+9):** at the end of its throw, the axe circles you once at its distance, at its speed, over walls (it's on a chain), hitting each enemy once a swing. Then it comes home. Split pieces don't flail. With Hang Time on too, the hover comes first and the axe doesn't flail.
- **Whirlwind Axe:**
  - **Spin cycle (+3):** the enemy with the most HP left, within the axe's range of you.
  - **Gale force (+6):** a rethrown axe may be rethrown once more (`Projectile.spins`).
  - **Eye of the cyclone (+9):** the second axe goes for the next enemy by the same order, and isn't rethrown again.
- **Doublebit Axe:**
  - **Reunite (+3):** two pieces of one axe that come within 0.5 tiles on the way back become one. Their damage adds up, and its hits get +30% in bucket A, which doesn't stack. Halves meet about 40% of the way home.
  - **Crossing (+6):** the halves start 3 tiles apart and aim at the far side until a quarter of the way is left, so they cross half way. With Reunite on (it is at +6), they meet and fuse where they cross.
  - **Quartering (+9):** the axe splits into four quarters at 40% straight away, rather than halves that split again. With Crossing they all cross in the middle, and with Reunite they fuse there.
- **Cloudburst Bow:**
  - **Monsoon (+3):** the enemy nearest the aim point among those within the bow's range of you.
  - **Thunder rain (+6):** each arrow gets x(1 + 20% per other arrow of the same rain landing within 1 tile of it).
  - **Squall line (+9):** the second rain is thrown at once but waits 0.4 s before it flies, and isn't drawn while waiting (lobbed shots now honour `hold`).
- **Broadleaf Bow:**
  - **Gathering speed (+3):** x1.1 speed per enemy pierced.
  - **Run-through (+6):** the arrow turns round where it stops (the enemy that stopped it, a wall, or the end of its range). It flies back as far as it came, through what it passed, once. With the longbow's 2 pierces it needs Piercing affixes (up to 3) or a Deadeye crit to get through 4.
  - **Broadside (+9):** twice the piece's per-enemy bonus, so it grows +10% a level too.
- **Bloodhound Bow:**
  - **Old scent (+3):** only a mark that's still alive stays on.
  - Every mark gets the red brackets.
- **Stillwater Bow:**
  - **Held breath (+3):** a second's stillness readies one fast volley (the attack's own arrows). Then the breath starts over. Rolling or walking resets it.
  - **Zen (+6):** uses the same "still" as Anvil stance (`still_t`, under 0.1 tiles/s).
  - **Still waters (+9):** Steady Aim counts for 1 s after you were last steady (`Character.calm`).
- **Farsight Bow:**
  - **Follow-through (+3):** the weapon's cooldown is cleared once that arrow has gone through its 3rd enemy.
  - **Second sight (+6):** every 6th attack (`Character.attacks`) is a sure crit, so all its arrows are.
  - **Lightning arrow (+9):** a crit is only known when a hit lands, so each arrow's crit is rolled when it's fired. A crit flies at x60 speed, its whole range in one frame. The others can't crit later, and Glow's +10% doesn't count for them.
- **Splitbranch Bow:**
  - **Canopy (+3):** as many of the split arrows as there are enemies in their range go for the nearest ones; the rest keep the fan.
  - **Bough (+6):** the fan comes off the wall, turned the way a bounce would go.
  - **Seed storm (+9):** the three seeds land 1.5 tiles out, evenly round the split point. Fanned, they overlapped, and one enemy stood in all three patches. Each patch is 1 tile and deals 5 every 0.5 s.
- **Tests:** `tests/test_m28_2h.py`, 39 tests, at least one per trick, a draw check, and a check that no `config` name is defined twice (after M28.2g's clash). The "not built yet" checks in `test_m28_2a.py` and `test_m28_2g.py` moved to the princess's Prismatic Wand.
- **Scratch check:** each hero wore all six of their pieces' powers and all 18 tricks (ignoring slots), plus two Piercing affixes, for 30 s against 19 kinds of real enemies, through level-ups. Each axe was also run on its own, since all six at once hide some tricks: Hang Time takes the throw's end before Flail, and split pieces start new throws. Everything ran clean: no lost flags, no errors.
  - Every trick went off except Carom, which needs walls close by. Some counts: Pinball 32, Flail 54, Shackle about 1,400 steps, Gale force's second rethrows, 7 extra marks at once, 33 lightning arrows, Run-through 5, Squall line 96 arrows.

### 17.19 Built: M28.2i (2026-10-19)

The princess's and the bard's main hands' 36 tricks: with them every one of the 100 pieces has its three, **300 in all**. These were changed, settled or noted:

- **Changed with the user (2026-10-19):**
  - **Nothing wasted (Cradlesong Lute +6)** replaces Duet, which healed allies: co-op isn't designed yet. The healing a beat couldn't give you (you were full) adds +4% per HP to your next beat (`NOTHING_WASTED`, `Character.unspent`), up to +40% with Mother's song.
  - **Lullabied (Cradlesong Lute +3):** as written, the next beat (1.2 s later) would wake the enemy at once. Now your beats hurt a sleeper without waking it; anything else does. It sleeps 3 s at most, then needs another 5 beats in a row (`Statuses.asleep`, which stops its clock like a daze; `combat.strike` wakes it unless the hit is a beat, `Character.lulling`). Damage over time doesn't wake it either.
  - **Beam (Spyglass Wand +9):** goes through enemies. It crosses the wand's whole reach in a frame (each color pierces everything), and only walls stop it. Every enemy on its line takes every color.
- **Prismatic Wand:**
  - **Full spectrum (+3):** the color that makes it every color of the shot on that enemy (5, or all of a smaller shot's) is a sure crit, once a shot per enemy.
  - **Afterglow (+6):** the highest bonus the last shot reached on an enemy holds for 1 s, so every color of the next shot starts there. It doesn't add up shot after shot.
  - **Rainbow's end (+9):** x1.5 the Prism bonus, so it grows with the piece's level too.
- **Spyglass Wand:**
  - **Lens (+3):** the middle color (the middle two of an even fan) gets +25%, bucket A.
  - **Pinpoint (+6):** standing still (under 0.1 tiles/s, as for Anvil stance), the fan narrows to half over 2 s.
  - **Beam (+9):** after 1 s still. A beam has no Converge bend.
- **Chroma Wand:**
  - **Color theory (+6):** counts your burn, chill (or freeze), poison and shock on the enemy, in bucket A, for every hit of yours.
- **Duelist's Wand:**
  - **Face to face (+3):** bucket A, as Point Blank is.
  - **Duel (+6):** "up close" is within Point Blank's reach. The duelist takes +25% from you wherever it goes, and its hits, shots and ground deal you 25% less. The duel ends when it dies or you fall (`Character.duelist`; gold x's mark it).
  - **Bladework (+9):** x1.5 Point Blank's bonus, so it grows with the level. Face to face stays at 2 tiles.
- **Kaleido Scepter:**
  - **Shards of light (+3):** as many pieces as there are enemies within the pieces' reach go for the nearest ones; the rest keep the fan.
  - **Radiant split (+6):** a piece's hit reach grows by a quarter tile (half a color's width).
  - **Infinite mirror (+9):** a piece that hits splits into 2, 25 degrees apart, each with half its damage; pieces of pieces split too, 3 times at most.
  - A beam splits only on its first enemy, and its pieces are plain colors. The Spyglass and the Kaleido are both main hands, so this only matters if they ever meet.
- **Crossbeam Wand:**
  - **Focal point (+3):** within 1.5 tiles of a crossing (or the enemy Lockstep follows), bucket A.
  - **Second crossing (+6):** the second crossing is about 3.5 tiles on, not 3. Converge's bend turns once a frame, so its crossings come up to a step of flight early, the first one too.
  - **Lockstep (+9):** the enemy nearest the aim point among those within 90% of the colors' reach. The fan turns to it, and each frame each color bends on the arc through where it is now, until the colors pass it.
- **Fortissimo Lute:**
  - **Climax (+6):** "at +50%" means 5 or more beats in a row, so with Forte it holds above +50% too.
- **Cradlesong Lute:**
  - **Mother's song (+9):** 2 HP per enemy, 10 HP a beat at most (5 enemies' worth, as "up to 5" is for Lullaby).
  - A beat from an amp (Stompers +9), Polyrhythm's second ring or Curtain call doesn't count for Crescendo, Lullaby or sleep.
- **Offbeat Lute:**
  - **Swing (+3):** after a soft beat, the wait for the loud one is cut by 20% of the lute's beat interval.
  - **Polyrhythm (+6):** every 3rd beat, the other kind of ring goes off with it (with all of the beat's other changes, a finale too).
- **Sourstring Lute:**
  - **Clash (+3):** an enemy that moved less than 90% of its push takes 15. Bosses and things that never move aren't pushed, so they never clash.
  - **Tritone (+6):** chilled (or frozen) before the beat.
- **Showstopper Lute:**
  - **Overture (+3):** the first beat after 5 s without a beat that hit anything, the run's first beat too.
  - **Curtain call (+6):** a finale ring right where you are when your HP drops through 30%, once every 20 s at most.
- **Songbird Lute:**
  - **Birdsong (+3):** enemies behind walls become targets too, if a note can get round to them within 16 tiles. The shortest way round is cut down to its corners (`run_rules._flood`, `_corners`). A note flies corner to corner, then straight at its target.
  - **Chorus (+6):** each note goes twice at the same enemies.
  - **Aria (+9):** where a note lands (an enemy, a wall, the end of its flight), everything else within 1 tile takes its damage. It's a plain hit: no on-hit statuses.
- **Tests:** `tests/test_m28_2i.py`, 39 tests, at least one per trick, a draw check, and a check that all 100 pieces have their 300 tricks. The "not built yet" checks in `test_m28_2a.py` and `test_m28_2g.py` are gone (nothing is left unbuilt).
- **Scratch check:** each hero wore all six of their pieces' powers and all 18 tricks (ignoring slots) for 30 s against 19 kinds of real enemies, through level-ups. The Cradlesong, Showstopper and Sourstring Lutes also ran alone, since together Syncopation's short loud beat keeps enemies from taking 5 beats in a row. Everything ran clean: no lost flags, no errors.
  - Princess: 29 full-spectrum crits, 8 beams, 15 duelists, 217 refractions with 1,185 mirror splits, 78 crossings, Lockstep following on 2,216 steps.
  - Bard: crescendo up to 10 (Forte), 10 HP kept for the next beat, 14 swings, 9 polyrhythms, 3 clashes, 12 notes round walls, a curtain call. Alone, the Cradlesong put 3 enemies to sleep.

## 18. Built: M28.3a (2026-10-19)

**The user's picks (2026-10-19):**
- **Systems first:** rarity power, the legendary look and the STATS page now. The 100 legendary tricks come after, drafted slot by slot (M28.3b onward), like M28.2.
- **Rarity and level multiply:** the main number x (1 + 10% a level) x the rarity's x1.0 / 1.15 / 1.3 / 1.5 / 2.0. A legendary +9 Duelist's Wand: 40% x 1.9 x 2.0 = +152%.
- **Powers with no number** get half the rarity's extra as damage (bucket A): uncommon +7.5%, rare +15%, epic +25%, legendary +50%. It adds to the level's +5% a level.
- **A STATS page** on the gear screen: I (pad Y) flips to it.

**How it's built:**
- `config.GEAR_RARITY_POWER`, `GEAR_RARITY_FLAT`, `GEAR_MUL_FLOOR`; `players/gear.py` `power_scale`, `flat_damage`, `spell_boost`. `power_steps`, `power_text` and `next_level_text` take the rarity, and `Equipment.steps` passes each piece's.
- **Spells (trinkets):** the rarity grows the spell's SPELL_GROW number the way levels past V do, and the two multiply. For the two whose number is a radius (Ember Aura, Poison Flask) it's the area that grows by the rarity, so the radius grows by its square root (a legendary Ember Aura is 41% wider, not twice as wide).
- **A shrinking multiplier goes no lower than x0.1.** Only the Spyglass Wand's Focus has one: x0.7 would have reached x-0.14 at legendary +9.
- **What doesn't grow:** downsides (Frenzy's range, Heavy Plate's speed...), trick numbers, and affixes (they were already sized by rarity in M28.1).
- **Texts:** "(power +220%)" on the card (level and rarity together), and "+1 -> power +20%" for a legendary's next level.
- Some numbers at legendary +9, for M35: Stormcaller 4 jumps instead of 1, Steady Aim 95% crit while still, Glass Cannon x2.52, Point Blank +152%.

**The legendary look:** a legendary's frame gets starred corners and a spark that runs round its edge, on the level-up card and in its gear-screen slot. The engine's double-line glyphs draw as single lines, so a double frame wasn't an option. The glow on the ground and the drop sound come with drops (M28.4).

**The STATS page** (`ui/gear_stats.py`):
- **Damage:** the weapon (how many shots, how often) with one hit worked out through the buckets, e.g. "9 x (1 + 0.65 damage) = 14.8 a dart", and its crit. Then each spell: its level, how often, how far, and its hit worked out the same way. Then the statuses you can inflict, with their damage multiplier and the share of hits that roll them. A note says that bonuses which only count sometimes (Point Blank up close, Wildfire on burning enemies, Hunter's Mark...) come on top.
- **Stats:** max HP, armor (and how much less you take), move, attack speed, crit, area, duration, pickup, rolls, and any other stat that isn't zero (evasion, regen, pierce, tag damage...).
- Two columns on the wide screens, one scrolling column (UP / DOWN) on the classic 80-column grid. The level-up picker's sub-screens (UPGRADE, which slot, the full bag) don't have it.
- **Pad:** Y is now I in menus. Nothing else used Y there.

**Tests:** `tests/test_m28_3a.py`, 17 tests. Among them, the page's hit matches a real hit through `combat.strike` for all five heroes, and the page fits every screen size.
