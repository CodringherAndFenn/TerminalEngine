# AsciiAdventurers — Gear

Status: **rev 2, a DRAFT to work on together (2026-10-18).** Nothing here is built. It is M28 in `BOSSES.md` section 8. The card system (`CARDS.md`) stays as it is until this doc is agreed.
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
| **Main hand** | 1 | **The hero's own weapon line, hero-only.** Everything that changes how that hero's weapon works (CARDS 6.2 and the hero rows of 6.11), and the hero spells Chain Lightning and Split Arrow | 35 | wizard: staffs, dwarf: axe heads, huntress: bows, princess: wands, bard: lutes |
| **Off-hand** | 1 | **Shot patterns and attack rhythm:** Cross Fire, Spiral, Rear Guard, Twin Lanes, Starburst, Echo, Frenzy, Spray and Pray | 8 | quiver, tome, orb, a second axe, a songbook |
| **Head** | 1 | **Statuses and elements:** Kindling, Venom, Frostbite, Static, Serrated, Wildfire, Shatter, Hemorrhage, Virulence, Thermal Shock, Toxic Current | 11 | cap, helmet, hood, tiara, hat (the same piece looks different on each hero) |
| **Chest** | 1 | **Defence and trade-offs:** Thorn Mail, Ward Charm, Heavy Plate, Glass Cannon, Retaliation, Untouched, Berserker, Bulwark, Juggernaut, Aegis, Phoenix | 11 | robe, plate, leathers, gown, doublet |
| **Feet** | 1 | **Movement and the roll:** Riposte, Slipstream, Close Call, Scorched Trail, the 5 hero rolls (Blink, Shoulder Charge, Backflip, Pirouette, Drop the Beat), Momentum, Fleet Strike; new trails like the **boots of freezing** | 11 | boots |
| **Rings** | 2 | **Triggers, scaling and the economy:** Volatile, Chain Reaction, Soul Harvest, Surge, Bloodlust, Giant Slayer, Veteran, Overflow, Pandemic, Pack Leader, Fortune, Golden Hoard, Bounty, Beacon | 14 | (HUD only) |
| **Trinkets** | 3 (4th from the Guild's Arcane Wing) | **The spells:** Orbiting Daggers, Ember Aura, Frost Nova, Spirit Wolf, Rune Trap, Poison Flask, Storm Cloud, Healing Totem, Fire Wand, Bone Turret | 10 | (HUD only; the wolf and the turret show in the world) |

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
| M28.1 | The data model and the ten slots. Every card turned into gear with **its current numbers**. The picker shows pieces (empty slot / +1 / swap with compare) plus UPGRADE. The bag and salvage. The HUD row. Arcane Mastery and Weapons Master cut. The game plays like today, just worn |
| M28.2 | Levels +0 to +9: the number rules and the +3/+6/+9 tricks for every piece, drafted with the user slot by slot |
| M28.3 | Affixes and rarity (section 7), legendary tricks; the gear screen and the damage breakdown |
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
