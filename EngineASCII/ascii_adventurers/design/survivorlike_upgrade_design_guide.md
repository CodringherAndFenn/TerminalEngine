# Designing Upgrade Cards for a Survivor-like

A reference for building a 50–100 card level-up pool, based on the patterns shared by *Vampire Survivors*, *Brotato*, *Deep Rock Galactic: Survivor* and similar games.

---

## Part 1 — How a developer thinks about upgrade cards

### 1.1 The card is a *decision*, not a reward
Every level-up pauses the game and asks the player a question. A good pool keeps that question interesting for the entire run. The developer's real goal is not "make 100 cards"; it is "make most level-up screens contain at least one choice the player has to think about."

A level-up screen is interesting when:
- There is **tension** (two cards are both good for different reasons).
- The player's **past choices matter** (the best card depends on what they already have).
- The choice **shapes the future** (taking this card changes what they'll want next).

A screen is boring when one card is always correct, or when all cards are interchangeable +5% stats.

### 1.2 The run is a story of increasing specialization
Almost every survivor-like follows the same arc:

| Phase | Player's situation | What cards should do |
|---|---|---|
| Early (levels 1–10) | Weak, few weapons, few options | Offer broad, obviously useful cards. Help the player survive and pick a direction. |
| Mid (10–30) | A build is emerging | Reward commitment. Synergy cards and tag cards start appearing. |
| Late (30+) | Build is defined | Offer multipliers, capstones, rule-breakers. Make the build feel absurd. |

Design implication: some cards should be **great early and weak late** (flat HP, flat damage), and some **weak early and great late** (percentage multipliers, "per X" scaling, synergy cards). This naturally changes what a "good pick" is across a run.

### 1.3 The power fantasy is the product
Players come to this genre to go from "barely surviving" to "screen-clearing god." The developer deliberately designs for **exponential player power against roughly polynomial enemy scaling**, then tunes difficulty so that bad builds fall behind and good builds break away. It's fine (desirable, even) for a finished build to feel overpowered. What matters is that it felt *earned* through choices.

### 1.4 Three questions to ask about every card
1. **Who wants this?** Which archetype or situation is this card for? If the answer is "everyone," it's a generic stat card (fine, but you only need a few). If the answer is "no one," cut it.
2. **What does it combine with?** A card that multiplies with nothing is a dead end. The best cards have 2–3 obvious partners.
3. **When is it good?** Early, late, or always? Try to have a mix.

---

## Part 2 — Taxonomy of card types

These are the building blocks. Almost every card in the genre is one of these, or a combination.

### 2.1 Generic stat cards
Flat or percentage increases to a global stat: damage, attack speed, max HP, move speed, armor, crit chance, pickup radius, XP gain, luck.

- **Role:** Filler that's never useless. Provides a baseline so no level-up is wasted.
- **Rule of thumb:** ~25–35% of your pool. Too many and the game becomes a spreadsheet; too few and players get "no good options" screens.

### 2.2 Weapon-specific cards
Upgrade one weapon: its damage, fire rate, projectile count, area, pierce, duration.

- **Role:** Deepens individual weapons; rewards focusing on a favorite.
- **DRG:S approach:** Generic weapon cards (damage, reload, fire rate) are offered *for a specific weapon* and raise that weapon's level. Levels unlock bigger rewards (overclocks).
- **Vampire Survivors approach:** Each weapon has its own fixed upgrade path (level 1–8) and picking the weapon again advances it.

### 2.3 Tag / synergy cards
Upgrade every weapon sharing a tag: all fire weapons, all projectiles, all drones, all melee.

- **Role:** The main engine of builds. Rewards collecting weapons that share properties.
- **Gating trick:** DRG:S only offers these once you hold two or more weapons with the tag. This keeps them relevant and prevents clutter.
- **Brotato version:** Weapon classes give *set bonuses* for holding multiple weapons of the same class.

### 2.4 Conditional cards
Bonuses that apply only under a condition.
- "+30% damage while above 80% HP"
- "+20% damage to enemies that are burning"
- "+crit chance while standing still"
- "+damage for each enemy within 3m"

- **Role:** Create playstyle, not just stats. They change *how the player moves and positions*.

### 2.5 Trade-off cards (double-edged)
A big bonus with a real downside.
- "+40% damage, −20% max HP"
- "+2 projectiles, −30% damage per projectile"
- "+25% XP gain, enemies +10% faster"

- **Role:** Force commitment and produce memorable builds. Brotato is built heavily on these; almost every item has a downside.
- **Rule:** The downside must *actually matter to some builds and not others.* "−armor" is a real cost to a tank and irrelevant to a dodge build. That asymmetry is where the design value lives.

### 2.6 Scaling cards ("per X")
Bonuses that grow with something else.
- "+1% damage per 10 max HP"
- "+damage for every enemy killed this stage"
- "+damage per weapon owned"
- "+1% crit per 5% move speed"

- **Role:** Create *conversion* builds, where one stat becomes another. Extremely strong for build identity because they make "useless" stats valuable.

### 2.7 Trigger cards ("when X, do Y")
On-event effects.
- On kill: explode, heal, spawn a projectile, gain gold.
- On hit: chance to chain lightning, apply status.
- On taking damage: release a shockwave.
- On reload / every Nth shot: special effect.
- On level-up / on pickup: temporary buff.

- **Role:** Adds visual chaos and emergent chains ("kills trigger explosions, explosions kill, which trigger explosions").
- **Watch out for:** Infinite loops and performance. Add internal cooldowns or proc-chance caps.

### 2.8 Economy cards
Affect resources: XP gain, gold, pickup radius, luck, shop prices, rerolls, extra choices on level-up.

- **Role:** "Greed" picks. Weaker now, stronger later. Good for creating the classic *invest vs. survive* tension.
- **Rule:** Economy cards must pay off before the run ends, or skilled players will learn to ignore them.

### 2.9 Defensive / sustain cards
Max HP, armor, dodge, regen, lifesteal, shields, invulnerability frames, thorns.

- **Role:** Survival. Needed so players can recover from a bad start and so tank builds exist.
- **Rule:** Offer multiple defensive *layers* (HP, damage reduction, avoidance, recovery). Each works differently, and combinations between them are part of the build space.

### 2.10 Utility / quality-of-life cards
Movement speed, pickup radius, projectile speed, area size, duration.

- **Role:** Make the game *feel* better. Players undervalue some of these (pickup radius, speed) and learn their importance over many runs, which is a good kind of mastery.

### 2.11 Rule-breakers / transformations
Cards that change how a mechanic works.
- "Projectiles bounce between enemies instead of piercing"
- "Your crits now apply burn"
- "Overheal becomes a shield"
- "Reloading is instant but you lose 1 HP"
- "Your orbitals now fire projectiles"

- **Role:** Capstones. Rare, memorable, build-defining. Usually legendary rarity or unlocked after a weapon reaches a threshold.
- **Rule:** Keep these to ~5–10% of the pool. They're the moments players remember.

### 2.12 Evolution / combination cards
Two things combine into a stronger thing.
- **Vampire Survivors:** a maxed weapon + a specific passive item = an evolved weapon.
- **DRG:S:** weapon levels 6/12/18 unlock overclock choices.

- **Role:** Long-term goals within a run. Gives players a "recipe" to chase.
- **Rule:** Make recipes discoverable (hint at them in the UI or in a codex) — hidden recipes are fun for a while, then frustrating.

---

## Part 3 — The stat layer

Before designing cards, define your stats. Cards are just modifications to these.

### 3.1 Common stat list

**Offensive**
- Damage (global, and per damage type or tag)
- Attack speed / fire rate / cooldown reduction
- Crit chance
- Crit damage (multiplier)
- Projectile count ("amount")
- Area / size
- Pierce / bounce
- Duration (for lasting effects)
- Range
- Status potency / status damage (burn, poison, shock, freeze, bleed)
- Reload speed (if your weapons reload)

**Defensive**
- Max HP
- Armor (flat or % damage reduction)
- Dodge / evasion
- HP regen
- Lifesteal / heal on kill
- Shields
- Revival / extra lives

**Utility & economy**
- Move speed
- Pickup radius (magnet)
- XP gain
- Gold / currency gain
- Luck (affects rarity rolls, drop chances)
- Rerolls, banishes, skips
- Curse (more enemies/difficulty for more reward — Vampire Survivors)

### 3.2 Additive vs multiplicative buckets
This is the single most important piece of math in the genre.

A typical damage formula:

```
Final damage = Base
             × (1 + sum of all additive % damage bonuses)
             × crit multiplier (if crit)
             × (1 + sum of tag bonuses)          ← a separate bucket
             × other independent multipliers
```

**Why it matters:**
- Bonuses *inside the same bucket* add. Stacking five +20% damage cards = +100%, which is 2×.
- Bonuses *in different buckets* multiply. +50% damage × +50% crit damage × +50% fire damage = 3.375×.
- Players quickly learn that **diversifying across buckets beats stacking one stat**. That's the hidden logic of most "good builds."

DRG:S, for example, states that stacking level-up bonuses is additive, while crit chance and crit damage act as separate multipliers.

**Design lever:** You decide which bonuses share a bucket. Put too much in separate buckets and the game explodes. Put everything in one bucket and each new card feels weaker than the last (diminishing relative value).

### 3.3 Diminishing returns and caps
Stats that must be capped or softened:
- **Dodge/evasion:** Without a cap, 100% = invincible. Brotato caps dodge; most games do.
- **Damage reduction / armor:** Use a curve like `reduction = armor / (armor + K)` so it approaches but never reaches 100%.
- **Cooldown reduction / attack speed:** Cap to avoid performance and readability issues.
- **Crit chance:** Either cap at 100% or let excess convert to something (bonus crit damage, "super crits") — overflow conversion is a great rule-breaker card.
- **Move speed:** Too high breaks controls and camera.

---

## Part 4 — Build archetypes

These are the recurring "builds" players form. Your pool should support **8–12 of these clearly**, with overlap between them.

For each archetype: the *core idea*, the *engine stats*, *signature cards*, and *natural partners*.

### 4.1 Crit build
- **Idea:** Rare huge hits.
- **Engine:** Crit chance + crit damage (two multiplicative stats).
- **Signature cards:** "+crit damage per crit chance above 50%", "crits explode", "crits reduce cooldowns".
- **Partners:** Precision/single-shot weapons, high fire rate (more rolls).

### 4.2 Status / damage-over-time (DoT)
- **Idea:** Apply burn/poison/shock/bleed and let it tick.
- **Engine:** Status potency (stacks), status damage, duration.
- **Signature cards:** "+damage to burning enemies", "burn spreads on death", "poison stacks have no cap".
- **Partners:** Area weapons, fast-hitting weapons (more applications).
- **Design note:** DRG:S separates status damage from direct damage — status damage can't crit and isn't boosted by generic damage cards. That separation *creates* the archetype, because it needs its own investment.

### 4.3 Projectile spam / "bullet count"
- **Idea:** Fill the screen with projectiles.
- **Engine:** Projectile count, fire rate, pierce.
- **Signature cards:** "+1 projectile", "projectiles split on hit", "every 5th shot fires a volley".
- **Partners:** On-hit trigger cards (more hits = more procs).

### 4.4 Big single hit ("sniper")
- **Idea:** Few shots, enormous damage.
- **Engine:** Flat and % damage, crit damage, pierce.
- **Signature cards:** "+damage, −fire rate", "overkill damage carries to next enemy" (DRG:S Sharpshooter does something like this).
- **Partners:** Crit, pierce, on-kill triggers.

### 4.5 Area / explosion
- **Idea:** Everything explodes.
- **Engine:** Area size, explosion damage, on-kill explosion chance.
- **Signature cards:** "kills explode", "+explosion radius", "explosions apply burn".
- **Partners:** DoT (explosions spread status), crowd density (curse).

### 4.6 Summoner / turrets / drones
- **Idea:** Your minions fight for you.
- **Engine:** Summon count, summon damage, summon duration. Brotato uses "Engineering" as a separate stat for structures.
- **Signature cards:** "+1 turret", "turrets inherit X% of your crit", "drones orbit you".
- **Partners:** Tank/defensive builds (you survive, they kill), area cards.
- **Design note:** Having a separate "summon" stat makes this archetype clearly its own lane rather than just "more of your damage."

### 4.7 Orbit / aura / close range
- **Idea:** Damage around the player; walk into enemies.
- **Engine:** Area, duration, orbit count, move speed.
- **Signature cards:** "+aura radius", "damage increases the closer the enemy", "orbitals knock back".
- **Partners:** Tank/regen (you'll get hit), speed.

### 4.8 Tank / thorns
- **Idea:** Take hits, reflect damage, never die.
- **Engine:** Max HP, armor, regen, thorns.
- **Signature cards:** "deal damage equal to X% of max HP on hit", "+damage per 10 max HP", "armor also adds damage".
- **Partners:** Aura, melee, "per HP" scaling cards.

### 4.9 Speed / kiting
- **Idea:** Never get touched.
- **Engine:** Move speed, dodge, pickup radius.
- **Signature cards:** "+damage per % move speed", "dodging triggers an attack", "leave a damaging trail".
- **Partners:** Trail/groundzone weapons, dodge.

### 4.10 Sustain / vampiric
- **Idea:** Heal through everything.
- **Engine:** Lifesteal, heal on kill, regen.
- **Signature cards:** "overheal becomes shield", "+damage while at full HP", "healing deals damage nearby".
- **Partners:** Tank, high fire rate (lifesteal procs).

### 4.11 Economy / greed / XP rush
- **Idea:** Sacrifice early power to snowball later.
- **Engine:** XP gain, gold gain, luck, pickup radius, interest.
- **Signature cards:** "+XP, −damage", "gold interest between waves", "extra card choice on level-up".
- **Partners:** Anything — it's an accelerator, not a finisher.

### 4.12 Luck / rarity manipulation
- **Idea:** Roll better cards.
- **Engine:** Luck, rerolls, banish.
- **Signature cards:** "+luck", "first reroll each level is free", "legendary cards are twice as strong".
- **Partners:** Everything (meta archetype).

### 4.13 Glass cannon / risk
- **Idea:** Maximum damage, minimal defense.
- **Engine:** Trade-off cards, "while at low HP" conditionals.
- **Signature cards:** "+damage per missing HP", "you have 1 HP but +200% damage" (a classic challenge-run card).
- **Partners:** Dodge, speed.

### 4.14 Elemental combos
- **Idea:** Different statuses react with each other.
- **Engine:** Two or more status types.
- **Signature cards:** "frozen enemies shatter when burned", "shocked enemies spread poison".
- **Partners:** DoT, area.
- **Design note:** Combos between two archetypes are the richest design space in the genre; they make players *want to mix*.

### 4.15 Focus vs. generalist
Two meta-archetypes that cut across all others:
- **Focus:** One weapon, everything into it. Supported by weapon-specific cards and level thresholds (overclocks, evolutions).
- **Generalist:** Many weapons sharing tags. Supported by tag cards and "per weapon owned" scaling.

Support both. DRG:S does this with weapon cards (focus) and tag mastery cards (generalist).

---

## Part 5 — Rules of the pool

### 5.1 Offer size and control
- **Offer 3 cards** per level-up (4 with luck or an upgrade). 3 is the genre standard: enough to choose, few enough to decide quickly.
- **Give players control tools:** reroll (reroll the offer), banish (remove a card from the pool for this run), skip (take a small bonus instead). Vampire Survivors uses all three. These dramatically reduce frustration from bad RNG.
- **Increasing reroll cost** (DRG:S's reroll gets more expensive each time) keeps rerolls meaningful.

### 5.2 Rarity
- Typical tiers: Common / Uncommon / Rare / Epic / Legendary.
- **Two ways to use rarity:**
  1. *Same card, bigger numbers* (DRG:S: Bigger Cogs is +10/15/25/35/50% depending on rarity).
  2. *Different cards per tier* (rule-breakers only at legendary).
  Most games mix both.
- **Luck** shifts the rarity distribution. Make it a real stat that players can invest in.
- **Some cards should skip low tiers entirely** (a "+1 projectile" card at common rarity is too strong; make it rare-and-up only).

### 5.3 Weighting and gating
Not every card should be equally likely.
- **Gate by ownership:** Tag cards only after owning 2+ matching weapons. Weapon cards only for owned weapons.
- **Gate by level/time:** Rule-breakers only after level 15, etc.
- **Weight by relevance:** Increase the chance of cards that match the player's current build (a subtle "smart RNG"). Many games do this quietly.
- **Exclude dead cards:** Never offer "+burn damage" to a player with no fire source. Dead offers make players feel cheated.

### 5.4 Slot limits
Vampire Survivors limits the player to a fixed number of weapon slots and passive slots. Limits:
- Force decisions (which 6 weapons?).
- Prevent late-game pool dilution (once slots are full, only upgrades for owned things appear, which feels great).
- Make each new weapon a big commitment.

### 5.5 Pacing
- **Early levels should come fast.** First 5 level-ups within the first minute or two.
- **XP curve should slow down**, but not so much that late levels feel absent.
- **Mix sources of upgrades:** level-ups, shop between waves (Brotato, DRG:S), chests/elites. Different sources can offer different card types (e.g., shops sell economy/defense, level-ups offer weapon upgrades).

### 5.6 Power budget per card
Assign each card a rough "power value" to balance against others at the same rarity.
- Example: at Common, a card is worth ~+10% of the player's current effectiveness.
- A trade-off card can have a bigger upside if its downside costs ~half that value *for a typical build*.
- Conditional cards can be ~1.5–2× stronger than unconditional ones because they're not always active.

### 5.7 Readability
- **One idea per card.** If it needs two sentences, it's probably two cards.
- **Consistent vocabulary.** Always "damage," never alternating with "power." Always "%" for percent.
- **Show the result, not the formula**, where possible ("Fire rate: 2.1 → 2.5/s").
- **Icons and colors per archetype** help players scan quickly.

---

## Part 6 — Synergy design patterns

These are the "mechanics behind the builds" in practice. Each is a reusable template.

| Pattern | How it works | Example |
|---|---|---|
| **Shared tag** | Many weapons share a property; tag cards boost all | "+20% fire damage" |
| **Set bonus** | Owning N of a type gives a bonus | "Own 3 drone weapons: +1 drone each" |
| **Conversion** | Stat A adds to stat B | "+1% damage per 1% move speed" |
| **Multiplicative stacking** | Cards in different buckets | crit chance × crit damage × tag damage |
| **Trigger chain** | Event A causes event B | kill → explosion → kill → explosion |
| **Threshold** | Bonus at a breakpoint | "at 10+ armor, reflect damage" |
| **Enabler + payoff** | One card enables, another rewards | "attacks burn" + "+damage to burning enemies" |
| **Evolution** | Two items combine | maxed weapon + passive = evolved weapon |
| **Overflow** | Capped stat converts excess | "crit over 100% becomes crit damage" |
| **Anti-synergy by design** | Trade-off that hurts one build but not another | "−armor, +dodge" |

**The most important pattern is enabler + payoff.** Nearly every archetype needs:
1. An **enabler** that gives access (a fire weapon, an "attacks burn" card).
2. **Payoffs** that reward having it ("+damage vs burning," "burn spreads").
3. A **capstone** that transforms it ("burning enemies explode on death").

If you design your archetypes in these three layers, the build logic writes itself.

---

## Part 7 — Budgeting a 50–100 card pool

### 7.1 Suggested split (for ~80 cards)

| Category | Count | % |
|---|---|---|
| Generic stat cards (offense, defense, utility) | 20–25 | ~28% |
| Weapon-specific cards (generic templates applied per weapon) | 8–10 templates | ~12% |
| Tag / synergy cards | 15–20 | ~22% |
| Conditional & scaling cards | 10–12 | ~14% |
| Trade-off cards | 6–8 | ~9% |
| Trigger cards | 6–8 | ~9% |
| Rule-breakers / capstones | 5–8 | ~7% |

### 7.2 Archetype coverage check
Make a grid: archetypes as rows, card categories as columns. Every archetype you want to support should have:
- at least **1 enabler**,
- **2–4 payoffs**,
- **1 capstone**,
- and **overlap with at least 2 other archetypes** (shared cards).

Any archetype with fewer cards than that will feel unreliable; players won't be able to assemble it often.

### 7.3 Start small, then expand
A practical approach:
1. Define ~15 stats and ~6 tags.
2. Build ~30 cards covering 5–6 archetypes.
3. Playtest. Note which picks feel exciting and which feel dead.
4. Add cards where builds feel thin; cut cards that are never picked or always picked.
5. Grow to 60–100 over iterations.

Weapon-specific templates multiply your effective pool without extra design work: 8 templates × 20 weapons = 160 offerable cards.

---

## Part 8 — Card templates

A starter set of reusable card patterns, by category. Replace names/numbers with your own.

**Generic stat**
- +X% damage
- +X% attack speed
- +X max HP
- +X armor
- +X% move speed
- +X% pickup radius
- +X% crit chance
- +X% crit damage
- +X% area
- +X% duration
- +X luck
- +X% XP gain

**Weapon-specific (applied to one weapon)**
- +X% damage
- +X% fire rate
- +X% reload speed
- +1 projectile (rare+)
- +X pierce
- +X% area
- +X weapon levels (fast-track to overclock/evolution)

**Tag**
- +X% [tag] damage
- +X% [tag] fire rate
- +X% [tag] area / radius
- +X [tag] duration
- +1 [tag] summon/projectile (legendary)

**Conditional**
- +X% damage while above Y% HP
- +X% damage while moving / while still
- +X% damage vs [status] enemies
- +X% damage vs elites/bosses
- +X armor when surrounded

**Scaling**
- +1% damage per X max HP
- +X% damage per weapon owned
- +X% damage per level
- +damage per enemy killed this stage (resets)
- +X% crit per Y move speed

**Trade-off**
- +big damage, −HP
- +projectiles, −damage per projectile
- +XP gain, +enemy speed
- +attack speed, −range
- +dodge, −armor

**Trigger**
- On kill: X% chance to explode
- On hit: X% chance to chain to Y enemies
- On damage taken: shockwave
- Every Nth attack: special effect
- On level-up: heal X / temporary buff

**Economy**
- +X% gold
- Interest: earn X% of banked gold per wave
- +1 reroll
- +1 card choice
- Heal on pickup

**Rule-breakers / capstones**
- Crit overflow converts to crit damage
- Status effects spread on death
- Projectiles bounce instead of pierce
- Overheal becomes shield
- All damage becomes [element]
- Summons copy your weapon upgrades

---

## Part 9 — Common mistakes

- **Must-pick cards.** If a card is always correct, players stop thinking. Nerf it, gate it, or make it a trade-off.
- **Dead cards.** Offering synergy cards without the enabler. Always gate.
- **Too many small generic stats.** "+3% damage" at level 40 feels like nothing. Scale numbers with rarity and time, or cut.
- **One-bucket math.** If everything adds together, each new card feels weaker than the last. Use multiple buckets.
- **Uncapped defensive stats.** 100% dodge or 100% damage reduction breaks the game.
- **Archetypes with no payoff.** "Speed build" needs cards that *reward* speed, not just more speed.
- **Hidden rules.** If players can't see why their build works, they can't learn. Show numbers, tags, and recipes.
- **Too much text.** Players make dozens of choices per run in the middle of action. Keep cards short.
- **No way out of bad RNG.** Provide rerolls, banishes, or skips.

---

## Part 10 — Checklist for each new card

- [ ] Which archetype(s) is this for?
- [ ] Is it an enabler, payoff, capstone, or filler?
- [ ] Which bucket does it affect (additive or multiplicative)?
- [ ] Is it gated so it's never offered as a dead pick?
- [ ] Is it good early, late, or always?
- [ ] Which rarity tiers can it appear at?
- [ ] Does it have 2–3 obvious synergy partners?
- [ ] Can the effect be explained in one short line?
- [ ] Does it risk infinite loops, uncapped stats, or performance issues?
- [ ] Would a player remember picking it?
