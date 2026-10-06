# AsciiAdventurers — Quests, Bosses and Landmarks

Status: **rev 1 — the framework and the swamp are BUILT in M17 (2026-10-01).** Rev 1 applies the user's answers to the rev 0 questions (section 9). What M17 built, and where it differs from the draft below, is in section 10. The user decides every boss; this doc holds the shared rules, the vocabulary to build bosses from (like the card archetypes in CARDS.md), and the first quest + boss to prove the framework. Open questions are in section 9. **2026-10-02:** the user set the boss roster (section 11, three per ring biome) and the roadmap was redone (section 8). **2026-10-05:** every boss now exists in every run, in an arena at a random spot in its biome, and any boss can be started without its NPC (section 1, M22.5 in section 8). This replaces "one boss per biome per run".

---

## 1. Run structure (what quests are for)

1. **Every boss exists in every run (user, 2026-10-05).** Each ring biome has three bosses (section 11), and **all three** are in it every run, each in its own arena (lair). The seed places each arena **at a random spot in its biome**, so boss locations change from run to run. (Until 2026-10-05 the seed picked one boss per biome per run; that's retired.)
   - **Quests are hidden (user, 2026-10-05).** Nothing is pinned or listed until a boss wakes: not the givers' camps (they're anywhere in the biome too), not the arenas, not the quests.
   - **NPCs still give the quests, as hints.** Talking to a giver tells you what to do (speech lines) and *takes* the quest: it gets a small counter on the HUD (`SWAMP Frogs 2/5`; the HUD can be hidden from the settings later), and its targets get a pin once you're near one. The arena is still only pinned when the boss wakes.
   - **Freedom: the NPC is optional.** Players who find the quest targets themselves and complete the quest (kill the frogs, light the braziers...) trigger the boss without ever talking to its giver. The boss wakes at its arena as usual. Walking into an arena whose boss isn't awake yet does nothing special; the quest is the key, and the NPC is just the guide to it.
2. Beating **one boss in each of the 5 ring biomes** unlocks the **plains boss** (user, 2026-10-05). The other bosses are optional: extra loot, card offers and their own achievements. The Glory quest line counts biomes, e.g. `Defeat a guardian in each land (2/5)`, and a biome counts once whichever of its bosses falls.
3. The plains boss drops **Adventurer's Glory** — the main quest, "Gain Adventurer's Glory". Holding it, the player **may end the run** (a victory) or keep going.
4. Later: the plains boss also grants water movement → 4 cardinal ocean regions → cardinal bosses → kill order picks the final boss (unchanged from the vision).

Framework first: **M17 ships one quest and one boss (swamp)**. Every other biome waits until the framework has been played.

## 2. Difficulty tiers

| Tier | Who | Rule |
|------|-----|------|
| I | 5 ring-biome bosses | **Roughly equal strength, different playstyles.** No "easy biome" — the order you take them in shouldn't matter. |
| II | Plains boss | **Stronger than any ring boss.** It's the gate to the ending. |
| III | Cardinal ocean bosses (later) | **Absolutely crazy.** Optional-feeling endgame for strong builds. |
| IV | Final bosses (later) | Map-wide fights, decided by the cardinal kill order. |

Strength is budgeted with the numbers in section 5.4, not by feel, so tiers stay comparable as cards and Guild upgrades grow.

## 3. Quests

### 3.1 Quest kinds (the framework supports these; each biome picks from them)

| Kind | Example | Notes |
|------|---------|-------|
| **Hunt** | kill 5 psychedelic frogs | special quest-only enemy variants; the M17 kind |
| Collect | gather 3 relic shards | pickups placed at points of interest; built in M23.2 (the caravan master's cargo, guarded) |
| Visit / activate | light 4 ruin beacons | uses landmarks (section 4) |
| Escort / defend | keep an NPC alive for 60 s | built in M24.1 as an escort (the scavenger follows you and can't be hurt; the ghouls come for the players) |
| Survive | hold a ritual circle while waves come | built in M23.3 (the apprentice's star circles) |

### 3.2 Quest rules

- **No ambush targets** (standing rule): quest enemies must be visible and shootable from range, like every other enemy.
- **Quests are hidden, and the NPC is optional (user, 2026-10-05; built in M22.5).** Every quest's targets are out from the start of the run and every kill or brazier counts, quest taken or not, silently. Finishing a quest wakes its boss: "SOMETHING STIRS..." and the arena is pinned. Talking to the giver takes the quest: their lines explain it, the HUD shows its counter, and its targets are pinned once you're within QUEST_TARGET_PIN_RADIUS of one.
- **Nothing is pinned from the start** (M22.5): givers' camps and arenas sit at random spots in their biome and are found by exploring (the minimap shows them once seen). An arena gets its pin when its boss wakes.
- Quest targets are **findable**: they're scattered over the biome, each in a clearing. A future Archivist "Charts" shelf could reveal more (e.g. the targets themselves).
- Progress is **per run** and shared by all players in co-op.
- When a quest completes, the boss is summoned **at its lair** (a landmark), not on top of the player — the player chooses when to walk in.

### 3.3 Quest log

- The HUD shows the main quest (GLORY) and a small counter for each quest taken from a giver, until its boss falls (M22.5). Quests nobody took never show. The big map shows the same list.
- Later: a **journal** in the Guild hall lists the quests you've completed (user, 2026-10-05; its own milestone, after M22.5).
- Main quest "Gain Adventurer's Glory" is always listed: `Defeat the 5 guardians (1/5)` → `Defeat the plains boss` → `Glory obtained — end the run at any time`.

## 4. Landmarks (fixed structures in the biomes)

Hand-made map pieces (like `guild_hall.txt`) stamped into the generated world each run, at a seeded spot inside their biome.

- Each ring biome gets at least: **a quest landmark** (where targets live) and **a boss lair** (an arena).
- Some landmarks have **NPCs**. NPCs can give the biome quest, flavour, and later their own **side quests** (optional, small rewards: loot, a free reroll, a card offer).
- NPCs are not attackable and enemies ignore them (simplest; revisit for escort quests).
- Landmarks are revealed on the minimap when seen, and get a name on the big map.

**Swamp (M17):** a **frog hunter's hut** on stilts at the edge of a **big bog** (a larger, wetter swamp patch than normal terrain), placed **close to the plains border** so it's an early, easy find. The hunter is pinned on the map from the start and gives the frog quest; the psychedelic frogs live in and around the bog. The boss lair is a lily-pad pond deeper in the swamp.

## 5. Boss design vocabulary

Same idea as the card archetypes: a fixed list of building blocks, so each boss is a **combination** of a few, and no two bosses share their signature.

### 5.1 Bullet patterns (the "bullet hell" part)

| # | Pattern | Reads as | Counter-play |
|---|---------|----------|--------------|
| P1 | Radial burst | ring of shots from the boss | stand between shots / back off |
| P2 | Spiral | rotating stream | circle with it |
| P3 | Aimed fan | 3–7 shots spread at the player | sidestep wide |
| P4 | Wall with a gap | line of shots sweeping across | find the gap |
| P5 | Contracting ring | ring closing in on the player | dash out before it closes |
| P6 | Slow homing | a few slow seekers | outrun / shoot them down |
| P7 | Telegraphed beam | laser after a visible aim line | leave the line |
| P8 | Lobbed / mortar | marked landing circles | leave the circles |
| P9 | Bouncers | shots that reflect off the arena walls | watch angles |
| P10 | Curtain / rain | dense slow field from one side | weave through |

### 5.2 Boss behaviours

| # | Behaviour | Example |
|---|-----------|---------|
| B1 | Charge / leap | crosses the arena, shockwave on landing |
| B2 | Summons adds | spawns small enemies (counts for XP, but capped) |
| B3 | Hazard zones | leaves lingering ground damage (uses systems/zones.py) |
| B4 | Arena change | water rises, walls appear, safe area shrinks |
| B5 | Vulnerable window | weak point / armour off only during a move |
| B6 | Shield / phase immunity | must break adds or pillars first |
| B7 | Teleport / clones | real one + decoys |
| B8 | Pull / push | sucks the player in or blows them back |
| B9 | Status on player | slow, confuse, blind (sparingly — see 5.3) |
| B10 | Enrage | faster and denser below a HP threshold |

### 5.3 Rules every boss follows

1. **Everything is telegraphed** (wind-up glyph, aim line, landing circle, sound) at least ~0.5 s ahead in the first phase. Later phases shorten tells (5.6), never under 0.3 s. Damage you couldn't see coming is a bug.
2. **Readable in ASCII**: boss shots use their own glyphs and colours that never match enemy or player shots. Screen effects (like "psychedelic") never hide the player or the bullets.
3. **One signature mechanic** per boss that no other boss uses as its centrepiece.
4. **2–3 phases** at HP thresholds; each phase adds or swaps one pattern instead of only speeding up.
5. **Breathing room**: every pattern sequence has a gap where the player can attack freely.
6. **No ambush starts**: the boss is visible when the fight begins; entering the lair starts it.
7. **Arena**: the lair **seals on entry** (no leaving mid-fight; dying ends the run as usual), and it **spans several screens** (user, 2026-10-01: built for co-op, where players spread out with their own cameras). One screen shows ~86×30 tiles (172×30 cells, 2 cells per tile), so the target is an oval of **~250×100 tiles: about 3 screens wide and 3 tall**. Consequences:
   - The boss **moves around the arena** (leaps, dives, charges) rather than sitting in the middle, so the whole space gets used.
   - Patterns spawn **around the boss or around a targeted player**, never "fill the whole arena": every bullet that can hit you started somewhere you could see.
   - An **off-screen boss arrow** (with distance) at the screen edge, and the boss HP bar is always shown inside the arena.
   - Arena terrain (lily pads, pillars, water) has cover and safe spots spread across all of it, not just near the centre.
   - The bullets-alive budget (5.4) counts per player-view area, so it scales with the number of players spread around.
8. **Co-op scaling**: HP scales with player count; patterns target the nearest/random player, never "all at once" multiplied.
9. **Melee heroes must be viable** (dwarf, bard aura): each boss has windows where standing close is safe.

### 5.4 Balance budget (targets, tuned in play)

| | Ring boss (I) | Plains boss (II) |
|---|---|---|
| Fight length at expected power | ~2 min | ~3–4 min |
| Damage per hit to the player | 8–15 (of 100) | 12–20 |
| Max boss bullets alive | ~150 | ~250 |
| Phases | 2–3 | 3–4 |

Boss HP is set from the time-to-kill target using the measured DPS of an average build at the level you usually reach the boss (dev-mode tool to measure it). All five ring bosses use the same budget row.

### 5.6 Shared difficulty rules (2026-10-05)

The user found the swamp bosses too easy. These rules apply to every boss (`ai/bosses.Boss`; numbers in `config.BOSS_*`):

- **Predictive aim** (`Boss.lead` / `Boss.aim`). Some shots and lunges aim where the target will be if it keeps moving: ahead by the shot's flight time, or by the move's wind-up, × `BOSS_LEAD` (0.85), at most `BOSS_LEAD_MAX` tiles. Each move mixes these with shots aimed straight at you, so neither circle-strafing nor standing still dodges everything; changing direction does. Moves that lead:
  - fans: volleys 2+ (Froggy's tadpoles, Proboscia's needles);
  - Froggy's stream: every other bubble;
  - Froggy's tongue and flop landing;
  - the leech surge line;
  - Proboscia's bite dive.
- **Combos** (`BOSS_COMBO`, per phase: chance, most extra moves). From phase 2, after a move the boss may start the next one `BOSS_COMBO_GAP` s later instead of resting. The first move's shots are still flying, and the next move's tell still shows. The phase's rest comes after the combo (rule 5 still holds). Phase 2: 45%, at most 1 extra move; phase 3: 65%, at most 2.
- **Faster pace by phase**: tells × `BOSS_TELL_SCALE` (1 / 0.85 / 0.7), never under `BOSS_MIN_TELL` (0.3 s); rests × `BOSS_REST_SCALE` (1 / 0.85 / 0.7).
- **Global knobs**: `BOSS_HP_MULT` (1.0) and `BOSS_DMG_MULT` (1.2) multiply every boss's health and damage, on top of the level and co-op scaling.

Also on 2026-10-05:
- Lady Proboscia is bigger: sprite ×2.2 (was 1.3), hit radius 3.0 (was 1.9), bite width 1.8, hovering 13 tiles away.
- The Leech Swarm has 120 leeches (was 40). They crawl over each other: no separation, just a small wander round each goal.

**Measured** (headless wizard bot that never dies, circle-strafing, seeds 31/7/12, old → new). The bot is weaker than the one in sections 12–13, so compare the two columns, not the earlier numbers:

| Boss | Fight time | Damage taken per min |
|---|---|---|
| Froggy | 1:52 / 2:00 / 2:19 → 1:55 / 2:15 / 2:09 | 233 / 230 / 318 → 411 / 236 / 332 |
| Leech Swarm | 3:04 / 2:48 / 3:03 → 3:20 / 3:18 / 3:19 | 231 / 234 / 305 → 410 / 413 / 421 |
| Lady Proboscia | 4:02 / 3:25 / 3:03 → 2:56 / 5:23 / 3:31 | 130 / 168 / 176 → 435 / 383 / 342 |

Proboscia's fights get longer when her bites land, because every bite heals her (`PROBOSCIA_DRINK`). HP numbers are unchanged.

### 5.5 Framework pieces (code)

- `BossSpec` (data, config.py): hp, phases, pattern list per phase, arena, music/sound, drops.
- Pattern library (`systems/patterns.py`): every P/B entry above as a reusable, data-driven pattern.
- Boss HP bar (big, bottom-centre) + name banner on entry.
- Lair/landmark stamping into the world gen; quest state (`systems/quests.py`) on the run.
- Rewards (in the run): a loot burst and a guaranteed rare+ card offer.
- Rewards (in the Guild): a per-boss **achievement**, a **bestiary entry** for the boss and its quest enemy, and a boss loot bonus banked like other loot. The Relics shelf (boss fragments → once-per-run powers) stays a later idea.
- Stress test: bullets-alive budget at target FPS.

## 6. First boss: Froggy McFrogface (swamp) — built in M17 (see section 10)

**Quest — "Bad Trip"** (frog hunter): find and kill **5 psychedelic frogs** in and around the big bog.
- Psychedelic frog: a quest-only bog toad variant, rainbow colour-cycling, a bit tankier, hops away from the player and spits a small wobbly shot. Visible from range (not an ambusher). Only 5 exist; they don't respawn.
- Killing the 5th: the swamp shakes, "Froggy McFrogface awakens" banner, lair marked on the map.

**Boss — Froggy McFrogface**, a giant frog (multi-cell sprite) in a lily-pad pond.
Signature (no other boss gets it): **the pond** — Froggy dives under and resurfaces elsewhere, and lily pads are the safe ground.

| Phase | HP | Patterns (draft) |
|-------|----|------------------|
| 1 | 100–60% | P3 tadpole fans; P3 bubble stream (5 aimed bubbles one after another, added after the first playtest: phase 1 was too easy); **tongue lash** (P7-style telegraphed line that pulls the player, B8); B1 belly-flop leap with P1 ripple ring on landing |
| 2 | 60–25% | adds P2 **bubble spirals**; dives (B7-lite: ripples show where it will surface); B2 a few small frogs |
| 3 | 25–0% | **psychedelic phase**: colours shift (never hiding bullets, rule 2), P10 rainbow rain from one side + P5 contracting lily ring; B10 enrage |

Melee window: after each belly-flop it sits stunned for ~1.5 s.
Drop: loot burst, card offer, achievement + bestiary entries, and swamp marked "cleared" toward the 5/5.

## 7. Biome changes

- **Built in M21 (2026-10-02): the haunted forest** (the user's choice over the leprechaun idea below). Big gnarled trees stand at least 3 tiles apart; only the 1-tile trunk blocks (and it can't be broken), while the crown of twisted branches and the roots round it are walkable. Old stumps (sparse) and fallen logs (2-3 tiles) are the cover, and both can be broken. The ground is dead leaves with faint fog patches, and wisp lights float and flicker over it (drawing only). Players see "haunted forest"; inside it's still `forest`, so enemy tables and saved records keep working. Blocking tiles went from ~46% of the forest (pine thickets) to ~3% (plus lakes, unchanged). The enemies stay as they were (the boar included); haunted enemies come with the forest bosses. Numbers are `HAUNT_*` in `config.py`; trees are placed on a global 5-tile grid so they're seamless across chunk edges (`world/generator._haunt`).
- *(Superseded)* **Forest → leprechaun biome (working name, decided).** The forest is too bushy: it plays like a jungle you can't move through, and it doesn't feel different enough from the plains. It's replaced by a green biome that **reuses the forest/plains assets** but is **open to move through**:
  - mostly walkable clover/meadow ground, with tree *clumps* and hedges instead of a solid canopy — clear lanes everywhere;
  - something that tells it apart from the plains at a glance (e.g. rolling hills, rings of mushrooms/stones, pots of gold, a rainbow tint); theme is not fixed, we pick it when we build it;
  - the **thornback boar carries over** (its charges suit open ground); fallen warriors stay plains-only or carry over too, to decide when we build it.
- The other 4 bosses are **yours to design**; when we get to each one we take it slowly, the way the cards were done: pick a signature from section 5, then 2–3 supporting patterns, then a draft table like section 6 for review.

Suggested angles only (to keep playstyles different — change freely):
- desert: movement-heavy (burrowing, sand walls, B4)
- ruins: geometry (beams, bouncers, P7/P9)
- mushroom: zones and spores (B3, B9)
- leprechaun: tricks and greed (B7 decoys, gold that baits you)
- plains (tier II): a "best of" fight that tests everything, own signature on top

## 8. Roadmap (redone 2026-10-02)

| Milestone | Content |
|-----------|---------|
| M17 (built) | Quest framework, landmarks, quest log, boss framework, swamp: frog hunter, **Froggy McFrogface** |
| M17.1 (built) | Froggy's phase-1 bubble stream |
| M18 (built) | Dodge roll + 11 roll cards, evasion rename, Lingering gate, spell levels, archetype lean |
| M19 (built) | Multiple projectiles for every hero (section 8.1; as built: `CARDS.md` 6.11 and 15) |
| M20 (built) | Wizard's arcane missiles; the shock bolt became his spell Chain Lightning; wizard cards and trainer redone (`CARDS.md` section 16) |
| M21 (built) | **Haunted forest** replaces the bushy forest (section 7) |
| M22 (built) | Boss pools (the seed picks one quest per biome per run; `run.py --boss KEY` forces one) + the swamp's **Leech Swarm** (section 12). Hidden names (Mycelium) need nothing extra: a boss shows its spec's name, so the three Mycelium variants simply share it |
| M22.2 (built) | Swamp: **Lady Proboscia**, the mosquito, and the smoke keeper's "light" quest (section 13) |
| M22.5 (built) | **Every boss in every run** (section 14). All three swamp quests exist at once, their camps and arenas at random spots in the swamp; the quests are hidden, finishable without their giver; several fights at once; one guardian per biome counts |
| M22.6 (built) | **Guild hall journal**: the archivist's fifth shelf lists every quest whose boss you've beaten (story, boss, wins, fastest fight, heroes), `???` for the rest (`GUILD.md` 4.4b) |
| M23.1 (built) | Desert: **Khepri the Dung Emperor**, the beetle, and the scarab collector's golden scarab hunt; the desert's camp (oasis tent) and arena (the Dung Pit) (section 15) |
| M23.2 (built) | Desert: **Ol' Spitter, the Unmannered One**, the spitting camel, and the caravan master's "collect" quest (lost cargo); the caravanserai arena (section 16) |
| M23.3 (built) | Desert: **the Nameless Magus, Holder of Time**, the nomad sand wizard, and the runaway apprentice's "survive" quest (star circles); the sunken observatory (section 17) |
| M24.1 (built) | Ruins: **the Fallout King**, the radioactive monster, and the hazmat scavenger's "escort" quest; the reactor vault (section 18) |
| M24.2 (built) | Ruins: **the Snow King, King of Loneliness**, the ice wizard, and the searching sister's "rescue" quest; the frozen throne hall (section 19) |
| M24.3 (built) | Ruins: **Fragile, The Misunderstood**, the vampire girl, and the pawn dealer's "fetch" quest (Mr. Buttons); the ruined ballroom (section 20) |
| M25.1-3 | Forest: **corrupted pixie**, **mad murderer squirrel**, **mimic tree** |
| M26.1-3 | Mushroom: **Mycelium** (three variants: amanita muscaria + two more) |
| M27 | Plains boss (not designed yet) + Adventurer's Glory + "end run" victory (+ water movement) |
| M28 | **Art handoff spec** (user, 2026-10-05; much later, after the content is in). A document with the exact pixel-art specs, so the user can draw their own models for chosen things (arenas, bosses, enemies, heroes, NPCs, tiles) and drop them in. It covers: the grid and tile size (a tile is 20×24 px, 2 text cells of 10×24); canvas sizes per thing (body sizes like Froggy's ~5×3 tiles, a leech's 14 px); top-down vs. the 3/4 view; which things rotate (baked by angle, drawn facing +x) and which use frames (walk, wind-up, hurt flash, dazed/engorged states); frame counts; the palette and the reserved colors (telegraph red, hit flash); transparency; file format and folder layout (PNG under `assets/`); and how arenas are made (the tile map text format like `guild_hall.txt`, or a picture). Plus a loader that uses a provided PNG when there is one and the procedural painter otherwise, so art can arrive one piece at a time |
| later | NPC side quests, cardinal regions + tier III bosses, kill order + finals, co-op, balance |

Each boss is still drafted first and reviewed before it's built, one at a time: signature, 2-3 supporting patterns, a phase table like section 6.

### 8.1 M19: multiple projectiles, every hero

- **Real fans:** each extra projectile adds at least ~12 degrees of spread, so Multishot visibly fans even on single-shot weapons. Echo and Quiver repeats come out offset or side by side, not stacked in one line.
- **Pattern cards (everyone who shoots):** Cross Fire (every Nth attack also fires at 90/180/270 degrees), Starburst (every 10th attack in 8 directions), Rear Guard (one extra shot behind you), Twin Lanes (two parallel shots), Spiral (an extra shot that turns further round you each attack), Barrage (+2 projectiles, less damage each).
- **Weapon versions:** bow, rainbow and axe each get one of their own (e.g. a split arrow, a double rainbow, juggled axes).
- **Every hero, the bard too:** the dwarf's axes already count as projectiles (an extra axe fans out and each one comes home). The bard's beat isn't a projectile, so he gets a bard card that makes beats fling notes outward (e.g. "Sheet Music": each beat throws 3 notes). Multishot and the pattern cards then work on those notes, so no hero is left out of the projectile archetype.
- Spells that shoot (Fire Wand, Bone Turret) pick up the extra projectiles too, so a summoner/spell build can use the archetype.
- Numbers, names and the final list are reviewed before building, like M18's roll cards.

## 9. Answers (user, 2026-10-01)

1. **Leprechaun biome:** replaces the forest. The name/theme isn't fixed — it was suggested because it's green and can reuse assets. The point is to differ from the plains while not being bushy. The boar carries over.
2. **Quest pickup:** the frog hunter gives you the quest. His bog is close to the plains border, and he's pinned on the map so players don't wander.
3. **Arena:** seals on entry, and spans several screens for co-op (~250×100 tiles, see 5.3 rule 7).
4. **Glory:** "end the run" can be used any time after receiving it (for now).
5. **Boss rewards** also feed the Guild.
6. **One quest per biome** for now; more later.

Still open (decide while building M17): Froggy's exact numbers, the psychedelic frog's look, the hunter's dialogue.

## 10. Built in M17 (2026-10-01)

**Code:** `world/landmarks.py` (camps and lairs stamped into chunks), `systems/quests.py` (stages, givers, sealing, rewards), `systems/patterns.py` (P1 radial, P2 spiral via radial, P3 fan, P5 ring_in, P10 curtain; line attacks use `point_segment_distance`), `ai/bosses.py` (Boss: phases + moves as generators; Froggy), `render/bosses.py`, `ui/quest_log.py`, map pins in `ui/maps.py`. Data: `config.QUESTS`, `config.BOSSES` (`BossSpec` / `BossPhase` in specs.py), `FROGGY_*`, `LAIR_*`, `CAMP_*`. Tests: `tests/test_m17.py`.

**Quest stages:** offered (giver pinned) → hunt (talk: E / pad A within 3 tiles) → awake (all targets dead; lair pinned) → fight (a player 6 tiles inside the stones: the gate fills with thorns tile by tile, the boss rises in the middle pool, its name across the screen) → cleared (gate opens, rewards). Quest targets are fixed spawns: they sleep/wake like any enemy, may appear on screen (with a puff — you're often standing at the bog when you take the quest), and any death counts, whoever caused it (no soft-lock from infighting).

**Swamp numbers as built:**
- Camp: bog oval 34 × 15 tiles, hut deck 20 × 11 on the side facing the plains, about 30 tiles past the plains border (10–75 tiles past it on the seeds tested). The 5 frog spots are spread round the bog.
- Lair: oval 125 × 50 half-axes (250 × 100 tiles, ~3 × 3 screens), 3-tile stone ring, 7-tile gate facing the plains with a mud causeway, 9 pools (one in the middle), 30 stone pillars (cover), reeds. Stays loaded during the fight wherever the players are.
- Psychedelic frog: 110 HP, 25 XP, keeps 8–13 tiles away, 2 weaving globs (8 dmg).
- Froggy: 6,000 HP at level 1 (+2.5%/level like every enemy; +70% per extra player), 400 XP. Hits: tadpoles 9, bubbles 8, ripples 10, rain 8, ring 10, tongue 14 (+ pull 5 tiles), belly flop 15. Bullets alive ≤ 150 per player in the arena. Phases at 60% / 25%; rests 1.1 / 0.9 / 0.55 s between moves.
- Rewards: 2,500 loot each, one card offer of rare or better, achievement "defeat Froggy McFrogface", bestiary pages for Froggy and the psychedelic frog.

**Differences from the draft:**
1. *Lily pads* are only decoration round the pools (walkable). The signature is the pools themselves: Froggy hops into the nearest, ripples rise on the one nearest its target, and it bursts up there in two staggered ripple rings.
2. *Psychedelic phase* recolours only Froggy and its shots (cycling hues); no screen tint, so nothing can hide a bullet.
3. Its body **shoves heroes out** (landing on you knocks you aside, and you can't stand inside it) — needed because shots from inside a body are hard to read.
4. The rainbow rain falls over where the target stood when it began (rows 40 tiles wide with a drifting 7-tile hole): weave through the hole or run out of it.
5. If the target is more than 40 tiles away, Froggy's next move is a leap toward them (it never sits out of reach in the big arena). An arrow at the screen's edge points to it when it's off screen.
6. Chill / freeze slow a boss's clock to at most half (no freeze-lock).

**Measured (headless, seed 31, a level-2 wizard bot with perfect aim, invulnerable):** the whole fight took ~2:05–2:20 and used every move in all three phases. A bot that barely dodges would have taken ~370 damage a minute. Step + draw stayed under ~3 ms with 150 boss bullets on screen (128-column grid). **The HP and damage still need tuning in real play** — a carded hero at a typical level should be much stronger than the bot, so 6,000 may be low.

**Known limits (for later):**
- Co-op: the gate seals as soon as the first player is 6 tiles in; anyone still outside is locked out of the fight. Revisit with local co-op.
- One quest per biome; only the swamp exists. The main quest's line counts guardians toward 5, so the run can't be "won" yet (plains boss + Glory are M19).
- Boss sounds reuse the existing synthesized effects (sound polish is deferred).

**Developer mode** (`run.py --dev`): F6 jumps to the quest giver, F7 finishes the hunt, F8 jumps outside the lair's gate; the fight's length is printed to the console when the boss falls.

## 11. Boss roster (user, 2026-10-02)

Three bosses per ring biome. Since 2026-10-05 all three are in every run, each in its own arena at a random spot in the biome (section 1). Until then, each run met one of them, picked by the seed. All three in a biome are tier I: about equal strength, different playstyles.

| Biome | Bosses | Notes |
|-------|--------|-------|
| Swamp | **Froggy McFrogface** (built), a **leech swarm** (built), a **mosquito** (built: Lady Proboscia) | the swarm is many bodies with one shared health bar (a new boss shape); the mosquito is fast, flies, drains blood |
| Desert | a **beetle** (built: Khepri the Dung Emperor), a **spitting camel** (built: Ol' Spitter, the Unmannered One), a **nomad sand wizard** (built: the Nameless Magus, Holder of Time) | |
| Ruins | a **radioactive monster** (built: the Fallout King), an **ice wizard** (built: the Snow King, King of Loneliness), a **vampire girl** (built: Fragile, The Misunderstood) | Adventure Time nods (the glowing lich-like monster, the ice king, the vampire queen). Use our own names and looks so the built game doesn't copy the show (the user will rename them) |
| Haunted forest (M21) | a **corrupted pixie**, a **mad murderer squirrel**, a **mimic tree** | the mimic hides among ordinary trees |
| Mushroom | **Mycelium**, always: one of three real mushrooms (**amanita muscaria** + two others), but the name, quest and HUD always say just "Mycelium", so you only find out which one in the fight. With all three in every run (M22.5), there are three "Mycelium" arenas, and you don't know which mushroom is in which | the other two (user, 2026-10-02): **shaggy ink cap** (melts into ink pools) and **giant puffball** (spore bursts) |
| Plains (tier II) | not decided | |

## 12. The Leech Swarm (swamp, built in M22, 2026-10-02)

**Pools.** `config.QUESTS` is keyed by quest name, each with its biome. Per run the seed picks one quest per biome (`world/landmarks.pick_quests`), and only that quest's camp, lair and targets are built. Quests can share camp and lair layouts: `camp_name`/`lair_name` label them and `skin` swaps their tiles (`landmarks.SKINS`). `run.py --boss leech_swarm` (or `froggy`) forces a boss for testing, and `config.QUEST_OVERRIDE` does the same in code. **Superseded in M22.5 (section 14):** every quest gets its camp, lair and targets, and `--boss` / `config.QUEST_FOCUS` only picks which quest the dev keys act on.

**Quest: "Bad Blood"** (the leech doctor). **A stand-in:** the user will give the real quest later. Pop 5 **bloated leeches** (120 HP; they crawl at you and bite) scattered over the swamp. Each one bursts into 3 **leechlings** (18 HP, fast). The doctor's camp and **The Blood Mire** are the frog hunter's camp and Froggy's pond in blood (blood pools, clots).

**Boss: The Leech Swarm.** 120 leeches (40 before 2026-10-05, see 5.6) with one health bar (8,500 at level 1, scaled like every boss). Each leech is a real enemy body holding an equal share. The swarm's health is the sum, so it thins out as it's hurt, and area attacks are strong against it by design. Its leeches aren't kills (no XP or loot each); the swarm is, when its last leech dies.

**Signature: latching.** A leech that touches a hero who isn't rolling latches on, at most 8 per hero. It rides along, draining 2.5 HP/s (in 0.5 s ticks) and healing itself by twice what it drains. A dodge roll throws every leech off that hero ("SHAKEN OFF!"): they're flung 2.5 tiles and lie stunned for 1 s. Nothing latches mid-roll.

| Phase | HP | Moves |
|-------|----|-------|
| 1 | 100–60% | the flock drifts after its target between moves; **surge** (a red line, 0.8 s, then the free leeches dash along it); **split** (3 groups circle the target, then close in) |
| 2 | 60–25% | adds **spit** (the swarm bunches and pulses, then 3 rings of 16 blood drops) and **nest** (into the nearest pool, can't be hit, ripples on the pool nearest you, bursts out of it with a ring of drops) |
| 3 | 25–0% | **frenzy** (everything 1.4× faster) and **whirlpool** (a ring of leeches round you, tightening from 11 to 2 tiles over 3 s, with a 50° gap: get out through it, or roll through the ring) |

**Measured (headless, seed 31, a level-1 wizard bot with perfect aim and two cards, invulnerable, rolling whenever latched):** with 6,500 HP the fight took 1:24 and used every move. It thinned from 40 leeches steadily (36 at 60% health, 15 at 14%). Health was raised to 8,500 for about 2 minutes. **Tune in real play**, like Froggy. Numbers: `LEECH*`, `LATCH_*` in `config.py`.

**How it's built:** `ai/bosses.LeechSwarm` is the "core", a point at the leeches' middle that can't be hit; it runs the moves and steers the leeches. `LeechPart` is each leech (an Actor; it never sleeps, and its damage counts toward the swarm). The swarm's own drops pass through its leeches (`combat._may_hurt`). Leeches swim over everything inside the arena (no walls for them). The quest adds the leeches to the enemies when the fight starts. Drawing is in `render/leeches.py`.

## 13. Lady Proboscia (swamp, built in M22.2, 2026-10-02)

The user's picks from the draft: the **Engorge** signature, all four extra moves (needle fan, buzz ring, swarm call, fever clouds + frenzy), the **bait-trail** quest given by an NPC, and the name **Lady Proboscia**.

**Quest: "Smoke Signals"** (the smoke keeper). A new quest kind, `"light"` (`QuestSpec.kind`). The camp's spots hold **braziers** instead of enemies (cold: a `[]` tile in the spot's clearing). Stand within 3 tiles of one for 5 s and it catches: it smokes for good, and the tile turns into a lit brazier. With nobody there its heat falls back at half speed. As the heat passes 0% and 50%, 3 **mosquitoes** come buzzing in each time (once per brazier). Light 4 of the 7 to wake her. The keeper's camp and **The Stagnant Court** are the frog hunter's camp and Froggy's pond, gone stagnant (`landmarks.SKINS["stagnant"]`: stagnant water, scum). Numbers: `BRAZIER_*` in `config.py`.

**Mosquito** (15 HP, 2 XP): flies over everything, buzzing at you on a wobbly line. In reach it hovers still for 0.3 s (the tell), stings for 4, then darts off sideways. Its sting hits heroes only (otherwise a cloud of them stings itself to death).

**Boss: Lady Proboscia.** 8,000 HP at level 1 (scaled like every boss). She flies over walls, pillars and pools, circling her target about 11 tiles out and always facing it. Her body doesn't shove you.

**Signature: Engorge.** Each bite that lands and each **sip** at a pool puts a gulp of blood in her belly (her abdomen swells and reddens). A bite also heals her by 3× the damage it did. With 3 gulps she's **engorged** for 6 s: 0.55× speed, a blinking belly, and a bar under her. Deal 3.5% of her max HP in that time and she **POPS**: 8% of her max HP more damage, a ring of 20 blood drops, and she drops to the ground stunned for 2.5 s (the melee window). If the time runs out, she **digests** it and heals 4%. Sipping is the other melee window: she lands at the nearest pool for 2.4 s, low and still. Deal 3% of her max HP and she's shooed off without her gulp.

| Phase | HP | Moves |
|-------|----|-------|
| 1 | 100–60% | **bite** (a red dotted line through you, 0.65 s, then a lunge along it; she hangs still for 0.6 s after), **fan** (stops, the proboscis glows, then 3 fans of 5 needles, repositioning between them), **sip** |
| 2 | 60–25% | adds **buzz** (a whine, then 2 rings of 26 sound pulses round you that hang for 0.8 s and close, each with a 55° gap) and **call** (4 mosquitoes, at most 8 alive) |
| 3 | 25–0% | **frenzy** (1.3× speed); a bite is **three dives in a row** (0.4 s tells after the first), each leaving **fever clouds** (every 3 tiles, radius 1.8, 4 s, 4 damage every 0.5 s) |

She never sips with a full belly and never calls with 8 mosquitoes already out.

**Measured (headless, seeds 31/7/12, a level-1 wizard bot without cards: perfect aim, circle-strafing, shooting mosquitoes within 6 tiles first, healed every step so her bites land):** fights took 1:58–2:36, with 1–3 pops and 0–2 digests each, and the bot took ~95–190 damage a minute. The first try (7,000 HP, 6 mosquitoes per call, at most 12, a 6% digest) stalled on one seed: the bot's missiles hit a wall of mosquitoes while she kept digesting. Hence the smaller calls, the smaller digest heal, and an easier pop (3.5%). **Tune in real play**, like the other two.

**How it's built:** `ai/bosses.Proboscia` (her `take_damage` counts damage toward the pop and toward shooing her off a sip; a pop aborts the current move), `ai/creatures.Mosquito`, `systems/quests.py` (`_tend_braziers`, `_swarm`, and the shared `_found`), `systems/patterns.ring_in(gap_deg=, gap_at=)`, `render/mosquito.py` (her, her tells and clouds, the mosquitoes, the braziers' smoke and heat bar), tiles `STAGNANT`/`SCUM`/`BRAZIER`/`BRAZIER_LIT`, NPC art `smoke_keeper`. `run.py --boss proboscia` forces her.

## 14. Every boss in every run (built in M22.5, 2026-10-05)

**What the user asked for:**
- All bosses exist in their biomes every run, with arenas at random places.
- NPCs still give the quests, but players can also trigger a boss by doing its quest without talking to anyone.

The user's answers on the details:
- camps anywhere in the biome, unpinned;
- quests hidden until the boss wakes;
- arenas pinned only when their boss wakes;
- a HUD counter only for quests taken from a giver;
- GLORY stays on the HUD;
- the journal comes later (built in M22.6, `GUILD.md` 4.4b).

**Placement** (`world/landmarks.build_landmarks`, `_random_site`):
- Every quest in `config.QUESTS` gets a camp and a lair. Lairs are placed first (they're the biggest), then camps.
- Each goes at a random point anywhere in its biome's slice of the ring: up to `QUEST_SITE_TRIES` points, uniform by area. It must fit inside the biome and keep `QUEST_SITE_GAP` tiles from every landmark already placed.
- Then each quest's target spots are scattered over the biome, clear of every camp and lair, and `QUEST_SPOT_OTHERS` tiles from other quests' spots.
- Each quest has its own dice (seed + its index), so the layout is the same for a seed.
- Landmarks record their `quest`, and `landmarks.quest_marks(layout, key)` finds a quest's camp and lair. About 165 ms at the start of a run for the swamp's three.

**Quests** (`systems/quests.py`):
- `states` is keyed by quest. Every quest starts in "hunt", with its targets placed when the run starts.
- `taken` is set when someone talks to the giver. It turns on the log counter, the progress toasts and the nearby target pins.
- The last target wakes the boss for everyone, taken or not.
- Quest enemy spawn ids carry the quest's id (`quest_id`: its place in `config.QUESTS`), not the biome's.
- `fights` lists every fight in progress. `fight_for(hero)` picks the one for the boss bar and pointer: the arena you're in, else the nearest. Every fighting arena stays loaded.
- `guardians` counts biomes with a beaten boss. A second boss in the same biome still pays its loot, card offer and achievement, and its banner says it's a bonus kill.

**Dev:** F6/F7/F8 act on `config.QUEST_FOCUS` (`run.py --boss KEY`), else the first quest not beaten yet.

**Fixed along the way:** place names in sentences used `str.title()` ("Froggy'S Pond"); now `quests.place_name`.

## 15. Khepri the Dung Emperor (desert, built in M23.1, 2026-10-05)

**The user's picks:**
- Signature: the dung ball.
- Supporting moves: all four (charge + sand spray, burrow eruption, dust storm, scarab swarm).
- Quest: the golden scarab hunt.
- Landmarks: new desert layouts.

**Quest: "Golden Touch"** (the scarab collector).
- Five **golden scarabs** (45 HP, harmless) are scattered over the desert, each in a sandy clearing.
- A scarab runs from you once you're within 11 tiles, jinking side to side. It's a bit slower than a hero, so you can chase it down.
- If it's still being chased after 4.5 s, it digs in. For 0.9 s it can still be hit (the last chance), then it's gone and comes back up at its home spot 10 s later.
- If the hero stops chasing and falls out of range, it calms down and potters home.

**Landmarks:** the swamp's camp and lair builders now take a style (`world/landmarks.CAMP_STYLES`, `LAIR_STYLES`). The desert's:
- `oasis_camp`: a round oasis pond (solid), a few palms, and the collector's tent on a rug with two stalls.
- `sand_lair`, **the Dung Pit**:
  - sandstone walls and 36 sandstone pillars, 3 tiles tall (taller than the swamp's 2, so they're clear targets for the ball);
  - sand pits for pools (Khepri sleeps in the middle one), with dunes for decor.
- Quest spots' clearings are the biome's ground (`landmarks.CLEARING`).
- A lair remembers its `floor`, so the gate reopens to sand.

**Boss: Khepri the Dung Emperor** (8,000 HP like the others; HP numbers wait for the balance milestone).
- Hit radius 2.6. The sprite is a top-down beetle about 115 px long (`render/beetle.py`).
- **Signature, the dung ball:** it sits in front of him.
  - The **roll**: an orange lane as wide as the ball (the tell), aimed where you're going, then he pushes the ball along it at 15 tiles/s.
  - The ball grows as it rolls, from 1.3 to 3.2 tiles across. It hits for 12–24 by size and knocks you 4 tiles aside.
  - Anything solid (a pillar, the arena wall, the sealed gate) **shatters** it: a ring of 10–22 clods, "SPLAT!", and he's stunned for 3 s (the melee window). Then he rolls up a new small ball (0.9 s).
  - So: **stand behind a pillar.**
- **Charge:** he leaves the ball, shows a ">" line, and charges for 14 damage. When he stops, he kicks a 7-pellet sand fan at you. If he hits a pillar on the way, he's dazed for 0.8 s instead. He walks back to his ball before the next roll, or makes a new one if it's more than 3 s away.
- **Burrow:** he digs in (can't be hit). A "^" ripple chases you for 1.6 s, then a blinking ring shows where he'll come up. He erupts there: a 3.5-tile blast for 15 damage and a ring of 16 sand shots.
- **Dust storm** (phase 2+): wings out (the tell), then rows of dust blow across where you stood for 3.5 s, with a drifting hole to weave through.
- **Scarab swarm** (phase 2+): a clicking call brings 4 scarabs (30 HP, they nip for 5), at most 8 alive.
- **Phase 3:** rolls 1.25× faster, two in a row (the second tell is shorter).

| Phase | Health | Moves |
|---|---|---|
| 1 | 100–60% | roll ×4, charge ×2, burrow ×2 |
| 2 | 60–25% | roll ×3, charge ×2, burrow ×2, storm ×2, swarm ×1 |
| 3 | 25–0% | roll ×4, charge ×1, burrow ×2, storm ×2, swarm ×1 |

**Measured** (headless wizard bot that never dies and doesn't try to bait pillars; seeds 31/7/12): 2:40 / 4:53 / 3:53, taking 298 / 296 / 226 damage per minute. That's about the swamp bosses' range with the same bot.
- With 44 pillars, seed 31 took 6:58: the pillars ate the bot's shots. 36 is about as many as the arena layout fits anyway.
- Real players who bait shatters get 3-second melee windows, so they should be faster.

**Readability:** VT323 draws `~` like an "N", so the oasis is a block-shade dither, the dust shots are `%` and the burrow ripple is `^`.

## 16. Ol' Spitter, the Unmannered One (desert, built in M23.2, 2026-10-06)

**The user's picks:**
- Signature: humps and thirst, **and** the ricochet loogie.
- Supporting moves: all of them (spit fan + mortar loogie, rear kick + gallop, stampede **and** mirage, spray spiral).
- Quest: collect the lost cargo.
- Arena: a new caravanserai.
- Name: Ol' Spitter, the Unmannered One (the user's).

**Quest: "Lost Cargo"** (the caravan master; the first `kind="collect"` quest, `systems/quests.py`).
- His lead camel bolted and scattered his cargo over the desert. Five bundles finish the quest, out of 8 spots (`count` + `QUEST_SPOT_EXTRA`).
- Each bundle (a `CARGO` tile in the middle of the spot's sandy clearing) is guarded by `CARGO_GUARDS` (3) **mangy camels**, placed round it as fixed spawns `(QUEST_SID, quest, spot, 1..3)`.
- A mangy camel (90 HP) keeps 7–11 tiles from you, drifting round you. Every ~2.2 s it stops, rears its head back (the 0.5 s tell, with green drool) and spits a fan of 3 globs. With nobody to chase, it stays within `CAMEL_LEASH` (9) tiles of its bundle.
- When all of a bundle's guards are dead, walk within ~3.6 tiles of it to take it. While any are alive, walking up says "THE CAMELS WON'T BUDGE!", once per approach.
- Pins (taken quest) say CARGO. The dev finish (F7) also clears the guards and the bundles.
- Camp: the oasis layout with the `caravan` skin (crates instead of the collector's stalls). The caravan master wears an indigo turban and carries a camel stick.

**Arena: the caravanserai** (`world/landmarks._caravanserai`). The arena's oval and gate are now shared with the pond/pit builder (`_arena_shell`). Inside:
- A ring of **mud brick** round a **flagstone** yard.
- An open middle yard with hay heaped round it, where he sleeps (`spots[0]`).
- Six stone **water troughs** (6×1 tiles each, `spots[1:]` are their middles, `trough_tiles` gives their tiles): two beside the middle, four out toward the ends. They're the only tiles here you can break (`TROUGH_HP` 160 a tile; heroes' shots break them, his own don't).
- Four rows of **brick arches** (3×2 tiles, up to 9 a row) for cover. His loogies bounce off them.
- 26 **tethering posts**, and hay.

**Boss** (8,000 HP like the others; HP waits for the balance milestone). Hit radius 2.4. The sprite is a top-down two-humped camel with a red saddle blanket, about 130 px long (`render/camel.py`). He turns slowly (`SPITTER_TURN`, 1.6 rad/s) and can only spit within 70° of his nose.
- **Signature 1, humps and thirst.** His humps hold `HUMP_WATER` (10) sips of spit. They shrink as he spends it: the front hump empties first, then the back one, and the blanket shows between them.
  - Costs: fan 2, mortar 2, loogie 3, spiral 3. The gallop, kick, stampede and mirage are free.
  - When he can't afford a spit move, he trots to the nearest whole trough (14 tiles/s) and kneels to drink for 4 s, taking **1.5× damage**: the melee window. "HE STOPS TO DRINK!", with splashes at his mouth. He gets up full.
  - Smash the trough he's drinking from and he **chokes**: stunned for 3 s, keeping only what he'd drunk so far. "HE CHOKES! HIT HIM!"
  - With every trough smashed he's **parched**: he can't drink, so his spit costs nothing. He moves 0.85× as fast and rests 0.75× as long between moves: slower but angrier. So smashing troughs early is a trade, because you lose the drinking windows.
- **Signature 2, the ricochet loogie.**
  - The tell: a 0.8 s green dotted line through its first two bounces, with "o" at each bounce.
  - Then a big gob (1.2 tiles) flies at 14 tiles/s and bounces off anything solid (walls, arches, posts, the sealed gate).
  - At each of its first 3 bounces it splits in two, 28° apart and 0.75× the size. At the next bounce it pops.
  - It hits for 14 / 11 / 9 / 7 by generation and pops on the hit. It lasts at most 7 s.
- **Spit fan:** head back (0.6 s), then 3 volleys of 5 globs over 50° (the first aimed at you, the rest leading you).
- **Mortar loogies:** 3 lobbed loogies, each with a blinking green landing ring. Each lands for 12 in a 2.4-tile blast, then splashes 6 drops out from the edge of the blast.
- **Gallop:** a red ">" line, then he gallops at 22 tiles/s for up to 36 tiles. He tramples for 14 and shoves you aside, and leaves churned sand behind (patches that sting for 5 every 0.5 s, for 3 s). Running into anything solid dazes him for 0.8 s.
- **Kick:** not in the phase lists. If someone stays in the 55° cone behind him (within ~6 tiles) for 0.5 s, his hind legs flash red with a cone of "x" (0.45 s), then he bucks for 16 and throws you 6 tiles. Because he turns slowly, standing behind him is safe from his spit but not for long.
- **Stampede** (phase 2+): a bellow (pulsing rings, 0.9 s), then 3 rows of ghost camels charge across where you stood, 1.1 s apart. Each row has a 7-tile gap. The ghosts pass through everything, fade in harmless for 0.35 s, and trample once each for 10. In phase 3 every other row comes from the side (those start closer, so they begin on screen).
- **Mirage** (phase 3): a shimmer, then 2 see-through doubles of him (at most 2 alive). They walk and spit like camels and pop at any hit.
- **Spray spiral** (phase 3): head back, then he spins for 3 s, spraying 3 arms of spit.

| Phase | Health | Moves |
|---|---|---|
| 1 | 100–60% | fan ×3, mortar ×2, loogie ×3, gallop ×2 |
| 2 | 60–25% | fan ×2, mortar ×2, loogie ×3, gallop ×2, stampede ×2 |
| 3 | 25–0% | fan ×1, mortar ×2, loogie ×3, gallop ×1, stampede ×2, mirage ×1, spiral ×3 |

Plus the kick whenever someone lingers behind him, and a drink whenever he's dry. If his target is more than 30 tiles away, he gallops to close in.

**Measured** (the headless wizard bot that never dies, circle-strafes and doesn't dodge; seeds 31/7/12):
- Fight times: 2:31 / 2:17 / 3:01.
- Damage taken per minute: 370 / 376 / 324.
- He drank 6–8 times per fight. The bot never choked him, and broke 1–3 troughs by accident.
- The first build hit for ~650 a minute. Half of that was the mortar: its splash ring spawned on the landing point, so standing on the mark took the blast and the whole ring. The ring now starts at the blast's edge. The fan went from 7 globs to 5, and the ghosts from 12 to 10 damage.
- What's left is mostly the mortar's blast (26–36%), which the bot never steps out of.

## 17. The Nameless Magus, Holder of Time (desert, built in M23.3, 2026-10-06)

**The user's picks:**
- Signatures: all three offered (sand runes, shifting dunes, the hourglass). "Other bosses will also get more abilities in the future."
- Phases: "one in phase one, two in phase 2, all 3 in phase 3. trust me on the difficulty curve". I put them in the order runes, then dunes, then the hourglass.
- Supporting moves: all four (sun lance, sigils + blade fan, blink + vortex, quicksand + serpent).
- Quest: survive at the star circles.
- Arena: a new sunken observatory.
- Name: the user's.

**Quest: "Broken Seals"** (the runaway apprentice; the first `kind="survive"` quest, `systems/quests._hold_seals`).
- The Magus took the apprentice's years for his hourglass and hides behind seals. Each spot's clearing has a seal (`<>`) in the middle, ringed with stars.
- Stand within `SEAL_RADIUS` (4) tiles of a seal: it wears down, with a bar over it. After `SEAL_TIME` (30) s in total, it breaks. With nobody inside it heals back at half speed.
- Every `SEAL_WAVE` (8) s of wear, a wave of 2–3 **sand elementals** rises 8–12 tiles out, each wave once.
- Four seals of 7 finish it. The dev finish (F7) breaks them all.
- Sand elemental (60 HP): it keeps its distance and throws sand bolts (a 0.45 s tell, with a "!" over it). Every few seconds it blinks: gone 0.25 s, then back 4–7 tiles to one side.
- Camp: the oasis layout with the `apprentice` skin (scroll racks).

**Arena: the sunken observatory** (`world/landmarks._observatory`, on the shared `_arena_shell`):
- blue-glazed stone round a floor of sandstone slabs;
- a round star chart in the middle (14 tiles across), where he sleeps;
- three rings of 2×2 columns (10, 14 and 18 columns), a quarter of them fallen (walkable rubble). They're cover from his sun lance;
- a fallen 12-tile brass telescope;
- sand drifts.

**Boss** (8,000 HP; hit radius 1.6). He's drawn as a big pixel-art character, a violet hooded robe with a white beard and a staff with a sun lens (`render/magus.py`, art in `render/characters.py`). The lens blazes while he casts. He's never slowed by his own time zones.

**Signature 1, sand runes** (phase 1+).
- He raises his staff (0.7 s), and 2 / 3 / 4 runes (by phase) appear 8–18 tiles from his target, at least 9 apart.
- Each charges for 4 s, its ring lighting up and blinking at the end. Then it fires:
  - **firestorm** (`*`, 45%): a 3.5-tile blast for 16, plus 12 sand shots;
  - **blade ring** (`x`, 35%): 2 rings of 14 blades;
  - **golem** (`#`, 20%): a sand golem climbs out (220 HP, plods at you, raises its fists for 0.7 s and slams in a 2.4-tile blast for 14; at most 2 alive, otherwise it's a firestorm).
- **Scuffing:** stand in a rune for 0.4 s, or roll through it, and it's gone.
- Scuff out every rune of a batch and he's **drained**: kneeling for 4 s with stars over his head ("HE'S DRAINED! HIT HIM!").

**Signature 2, shifting dunes** (phase 2+).
- He collapses the walls he raised before. Then the sand ripples (0.9 s) along 3–5 lines 5–16 tiles from the target, each 8–14 tiles long and set across the line toward you.
- **Walls** rise there: 2 tiles thick, `DUNE_HP` 60 a tile, so you can shoot through them. They block shots both ways, including his lance. They never rise on anyone or in the gate.
- 2 **quicksand** pits come with them: half walking speed and a 1 tile/s drag toward the middle. A roll isn't slowed.
- After 12 s (or at his next dunes) the walls collapse, throwing sand both ways along them, and the floor comes back.

**Signature 3, the hourglass** (phase 3).
- He plants it 9–16 tiles to one side of the target, so it's on screen. It's an enemy with 320 HP and a bar.
- 2–3 **time zones** open, 6 tiles across, never overlapping:
  - SLOW (blue `o`): heroes walk, shots fly and his adds act at 0.5×;
  - FAST (gold `+`): shots and adds go 2×, heroes walk 1.5×.
  - They never affect him.
  - Hooks: `Character.time_mult`, `Projectile.time_scale`, and an enemy's `time_mult` in the game loop.
- **Shatter it** and he's stunned for 4 s ("TIME STANDS STILL!").
- After 12 s it's **TIME'S UP**: 3 rings of 28 time shots from the glass (0.6 s apart, each with a 50° gap), and every rune on the field fires at once.

**Supporting moves:**
- **Sun lance** (P7, the first beam): a 0.8 s gold aim line from his lens, starting a little behind you. Then the beam burns for 1.5 s, sweeping 40° the way you're moving. It's stopped by columns, walls and the arena's edge, and hits once for 15.
- **Sigils and blade fan:** 4 sand sigils (homing glyphs that drift after you through everything and burst for 10; one hit of anything pops one; at most 6, gone after 8 s), plus a 7-blade fan over 70°.
- **Blink:** a shimmer for 0.6 s where he'll be (14–26 tiles off, at least 7 from you), then he's there in a puff of 8 sand shots.
- **Vortex** (phase 2+): a marked whirl (0.7 s) 6–9 tiles from you, then for 4 s it drags heroes within 12 tiles toward it at 2.5 tiles/s (a roll breaks free) and sprays a 2-arm spiral.
- **Sand serpent:** a blinking `^` line 44 tiles long through you (0.9 s), then the serpent races along it at 30 tiles/s, hitting once for 16.

| Phase | Health | Signatures | Moves |
|---|---|---|---|
| 1 | 100–60% | runes | runes ×3, lance ×2, sigils ×3, blink ×2, serpent ×2 |
| 2 | 60–25% | runes, dunes | the same, plus dunes ×2 and vortex ×2 |
| 3 | 25–0% | runes, dunes, hourglass | the same, plus hourglass ×2 (one at a time) |

**Measured** (the headless wizard bot that never dies, circle-strafes, doesn't dodge and never scuffs runes; seeds 31/7/12):
- Fight times: 2:59 / 3:04 / 2:54.
- Damage taken per minute: 257 / 226 / 163.
- Most of it comes from the sigils' blade fans, the vortex spiral, the serpent and the lance.
- The bot never gets the drained windows, so players who scuff runes should be faster.

## 18. The Fallout King (ruins, built in M24.1, 2026-10-06)

**The user's picks:**
- The difficulty target from now on is the Nameless Magus ("basically the difficulty curve im looking for"), so this boss is sized to him.
- Signatures, one per phase, kept: rads, then fallout, then the meltdown core.
- Moves: all four (gamma cross, toxic barrels, ghoul horde + EMP, skull volley + grate dive).
- Quest: an escort "but the npc is invulnerable to damage", and the ghouls "target you instead".
- Arena: the reactor vault.
- Name: The Fallout King (the user picked it from the draft).

**Quest: "Geiger Readings"** (the hazmat scavenger; the first `kind="escort"` quest, `systems/quests._escort`).
- Talk to her and she follows the nearest player within 30 tiles, 2.5 tiles behind, at 9 tiles/s. She slides round obstacles, and catches up if she's stuck for 1.5 s.
- Lead her within 3 tiles of a beacon site (7 sites in the ruins) and she plants a beacon over 10 s, with a bar over the site.
- Waves of 3 glowing ghouls come at 0, 3.5 and 7 s into each setup, for the players. She isn't an actor: nothing can hurt her.
- Four beacons wake him.
- **Unlike the other quests, this one can't be done without her** (she's the one planting). F7 plants them all.
- Camp: a new `scrap_camp` style: a sludge pit ringed with rubble, a scrap shack on metal plates, crates.

**Arena: the reactor vault** (`world/landmarks._reactor_vault`, on `_arena_shell`):
- concrete vault walls round a concrete floor;
- a cracked reactor ring in the middle, with four openings. He sleeps inside. It's low, so shots fly over it;
- round the edge, 4 coolant valves and 4 decontamination showers (2×2 pads);
- through the room, 4 lead walls (4×2) and 6 sewer grates;
- 28 concrete pillars and 6 pipe runs, clear of all of it.
- The fixtures are in `Landmark.props` (new: a lair's named fixtures).

**Boss** (8,000 HP since the playtest, see the end; hit radius 2.4). He's a big pixel-art character: a green ghoul-king with a skull face and a reactor core glowing in his plated chest (`render/fallout.py`, art in `render/characters.py`).
- **HP is calibrated, not the usual 8,000.** With the same bot, his ghouls, rods and barrels soak up about a quarter of your damage. At 8,000 HP his fight took 4:16–5:15 against the Magus's 3:03–3:30.
- A faint dotted ring shows how far his glow reaches.

**Signature 1, rads** (all fight).
- A meter on each hero (`Character.rads`, the RAD row on the HUD while above 0).
- **What fills it:** 6 a second within 7 tiles of his body; 8 per hit of his (including his shots, through the new `on_shot_hit` hook in `combat`); 15 a second in goo; 12 a second in fallout.
- It drains on its own at 2 a second.
- **At 100 you're irradiated for 6 s:** 4 damage every 0.5 s, no regen, and the roll recharges at half speed. Then the meter drops back to 50.
- **Showers:** stand under one for 1.5 s and it's wiped; that shower is then dry for 20 s.
- So melee and close range cost you trips to the showers. Ranged players can stay outside his glow.

**Signature 2, fallout** (phase 2+).
- **The stomp:** rings mark the landing spots for 0.8 s. Then 2–3 blasts (3 tiles across, 12 damage) land round you, the first within 4 tiles.
- Each blast leaves a patch growing from 4 to 7 tiles across over 10 s. A patch burns for 3 a second and builds rads.
- An **isotope rod** (60 HP) stands in each patch's middle. Smash it and the patch clears. At most 6 patches; the oldest fades.

**Signature 3, the meltdown core** (phase 3).
- The heat climbs from 0 to 100 over 35 s. The boss bar reads "CORE 80%", so everyone can see it wherever he is.
- **Shut a valve:** stand within 2.6 tiles of it for 2 s. Shut all four and the core is **exposed**: 3× damage for 5 s, and the heat goes back to 0.
- **Meltdown:** at 100, a 3 s countdown ("MELTDOWN IN 2 - HIDE BEHIND LEAD!" on the boss bar). Then 45 damage and +50 rads to every hero in the vault who isn't shielded (the first thing on the line from him to you is a lead wall).

**Supporting moves:**
- **Gamma cross:** four dotted aim lines (0.8 s), then four beams for 3 s, turning at 0.6 rad/s (in phase 3, one way then back). Each tick is 5 damage every 0.3 s, plus rads. Pillars and walls stop the beams.
- **Toxic barrels:** he heaves (0.6 s), then throws 3 barrels 0.4 s apart. Each flies 1.2 s with a landing ring and lands as a 3-tile goo puddle for 8 s (0.6× walking speed, plus rads). Since the playtest, nothing can hit a barrel in the air (the user: "the barrels shouldnt be destroyable while in the air, that would make the fight even harder which is ok for now"). Dodge the rings.
- **Ghouls:** a roar, then 2 glowing ghouls (40 HP, fast bites; they burst green when they die, 6 damage). At most 4 alive.
- **EMP:** a crackle (0.8 s), then 2 rings of 40 shots, 0.5 s apart, each with a 40° gap near you.
- **Skulls:** 4 homing skulls (one hit pops one; at most 6).
- **Grate dive:** he sinks into the nearest grate (can't be hit), the grate nearest you rattles (1 s), and he bursts out: a 3-tile blast for 14 and a ring of 12 glow shots.

| Phase | Health | Signatures | Moves |
|---|---|---|---|
| 1 | 100–60% | rads | gamma ×2, barrels ×3, skulls ×2, ghouls ×2, grate ×2, EMP ×2 |
| 2 | 60–25% | rads, fallout | the same, plus stomp ×3 |
| 3 | 25–0% | rads, fallout, core | the same; the core heats in the background |

**Measured** (the wizard bot that never dies and doesn't dodge; for this boss it showers when its rads pass 70 and circles just outside his glow; seeds 31/7/12):
- 3:41 / 4:04 / 4:08, taking 192 / 132 / 140 damage per minute. The Magus with the same circling distance: 3:03–3:30.
- The bot never shuts the valves, so it never gets the 3× windows.

**Tuning on the way** (from a first measurement of 5:07–5:32 and about 520 a minute, before the bot showered):
- ghouls from 4 a call (8 max) down to 2 (4 max), and their burst from 8 to 6;
- skulls from 5 (8 max) to 4 (6 max);
- the glow from 8 rads a second to 6, and hits from 10 rads to 8;
- rods from 150 HP to 60; the gamma beams from 6 every 0.25 s to 5 every 0.3 s; EMP shots from 10 to 8;
- HP from 8,000 to 6,500.

**Also fixed:** the Magus's time zones reset walking speed for every hero, even ones fighting in another arena. Both bosses now touch only heroes in their own arena (`Boss.in_arena`).

**After the user's playtest (2026-10-06):**
- Feedback: "the meltdown ... its like getting hit by air"; "i almost killed the boss as a level 1 character"; "i dont see the core im supposed to hit or the showers, i think they need to be marked on the map during the fight".
- **The meltdown is now a wave** (`MELTDOWN_SPEED`, 70 tiles/s) racing out from him across the vault. It's drawn screen-wide by `render/fallout.draw_meltdown`: a flash, the front, its wake, sparks settling. **It hits each hero when it reaches them**, and the lead check is made then, so you can still duck behind a wall as it comes. During the countdown, radiation motes rise all over the vault.
- **Marked during the fight** (`FalloutKing.map_marks`, `render/fallout.draw_vault_marks`):
  - on the minimap and the big map: SHOWER (cyan; grey "DRY" while it recovers); from phase 3 the open VALVEs (orange); LEAD walls during a countdown; the CORE (him) while it's exposed;
  - in the world: rings and labels over showers ("DRY 12" while dry), valves and lead walls ("HIDE BEHIND"), and "HIT THE CORE!" with a target ring on him while it's exposed;
  - an arrow at the screen's edge to what you need now: the nearest running shower when your rads are 60+, the nearest open valve in phase 3, the nearest lead wall in a countdown;
  - the boss bar: "CORE 40% - SHUT THE VALVES 1/4", "CORE EXPOSED - HIT HIM NOW!", "MELTDOWN IN 2 - HIDE BEHIND LEAD!".
- **Harder** (the user's pick: "back to 8,000 HP, hit harder"):
  - HP back to 8,000;
  - glow 8 rads a second, hits 10 rads;
  - meltdown 60 damage (was 45);
  - gamma 7 a tick (was 5); EMP 11 (was 8); glow shots 10 (was 8);
  - ghouls 3 a call, 5 alive.
- Bot after the changes: 4:21–5:59 at 147–225 damage per minute. The bot is slower than a person here (a level-1 player nearly beat the old version), so the playtest outranks it for this boss.

## 19. The Snow King, King of Loneliness (ruins, built in M24.2, 2026-10-06)

**The user's picks:**
- Signatures by phase, kept: knock off his crown, then black ice, then flash freeze.
- Moves: all four sets (shard fan + spike ring, penguin squad, frost breath + icicles, blizzard + snowballs).
- Quest: rescue the captives.
- Arena: the frozen throne hall.
- Name: the user's.
- They passed on "frozen reflections" (ice copies replaying you) for now and asked to keep it for later (it's in the memory backlog).

Built to the playtest lessons from the start: everything the fight needs you to find is marked (map pins, labels in the world, an edge arrow, the boss bar), and big effects are visible.

**Quest: "Cold Hearts"** (the searching sister; the first `kind="rescue"` quest, `systems/quests._rescue`).
- Seven captives frozen in **ice blocks** (`tiles.ICE_BLOCK`, 200 HP: every hero's attack wears terrain, the bard's pulse too).
- Shatter one and the captive stands there shivering (drawn by `render/snowking.draw_captives`). They thaw over 8 s, but only while a hero is within 3 tiles; a bar shows it.
- Waves of 2 **frost wraiths** (30 HP; they drift through walls) come at 0, 3 and 6 s and make for the captive. One that touches them knocks 30% of the thaw back and fades.
- Four freed wake him. Only spots within 40 tiles of a hero are looked at (far chunks may not be loaded). F7 frees them all.
- The camp is the scrap camp with a `frost` skin (a frozen pond, snowdrifts).

**Arena: the frozen throne hall** (`world/landmarks._throne_hall`):
- ice walls round frost-stone;
- his ice throne across from the gate; he sleeps in front of it;
- three rows of 2×2 ice pillars (120 HP a tile; he regrows a shattered one 20 s later if nobody's in the way);
- 4 fire braziers, 10 frozen statues, snowdrifts.
- The fixtures are in `props`.

**Boss** (8,000 HP; hit radius 2.2). He's a big pixel-art king in a blue robe with a white beard, wearing a gold crown (drawn on its own, so it can come off).

**Signature 1, the crown** (all fight).
- Deal 6% of his HP within 4 s and it flies off at 22 tiles/s, slowing to a stop (about 13 tiles away from you) and bouncing off walls. The boss bar shows "CROWN 60%" as you build toward it.
- **Crownless:** he can't attack. He waddles after it at 6 tiles/s with "?" over his head, and takes 1.6× damage.
- **Kick it:** touch the crown to kick it on (16 tiles/s, each player every 2 s).
- **Back on** (0.8 s): "HOW DARE YOU!", a ring of 20 shards, and 15 s before it can come off again.
- Marked: a CROWN map pin, "CROWN - KICK IT!" over it, an edge arrow, and "CROWNLESS - HIT HIM! KICK THE CROWN AWAY!" on the boss bar.

**Signature 2, black ice** (phase 2+).
- His freeze: frost spreads from 2–3 spots for 1 s (one right by you), then sheets grow from 4 to 8 tiles across over 3 s. They last 30 s, at most 6.
- **On ice:** your speeding up and stopping are 0.15× (`Character.traction`, a new hook in `move`), and your top speed is 1.15×. A roll is unaffected. Penguins slide twice as far on ice, snowballs roll 1.5× as fast.
- **Fire braziers:** stand within 2.5 tiles for 2 s to light one. It burns 20 s and melts every sheet whose middle is within 9 tiles.
- Marked: map pins (FIRE? unlit, FIRE lit), "LIGHT ME" or "FIRE 12" over them with a lighting bar, and an edge arrow to a fire (a lit one first) while you're on ice.

**Signature 3, flash freeze** (phase 3).
- **Chill** (`Character.chill`, the HUD's CHL row; the HUD's extra row is now a general `meter`, shared with rads).
- **What fills it:** +12 per frost hit (shots, breath ticks +6, icicles, penguins, snowballs) and +6 a second standing still.
- **What drains it:** −4 a second moving, −25 a second near a lit fire.
- **Full: encased** for up to 4 s. You can't move or attack (hooks in `move` and the game step). 3 roll presses break out (`roll.step`), or a partner's shots chip the ice (60 HP).
- His hits on an encased hero do 1.5×, and icicles always fall on encased heroes.
- Marked: an ice block round you with "ROLL! 1/3", and an arrow to a fire once your chill reaches 60.

**Supporting moves:**
- **Shards:** staff raised (0.6 s), then 3 fans of 6 shards over 60°.
- **Spikes:** a ring of 22 ice spikes round you that hangs 0.8 s, then closes, with a 45° gap.
- **Penguins:** a whistle (0.8 s), then a row of up to 9 penguins sliding across where you stood at 14 tiles/s, with a 7-tile gap. They hit for 10 and shove.
- **Breath:** a wedge of aim lines (0.8 s), then a 50° cone that sweeps 40° the way you're moving for 1.6 s: 4 damage a tick, +6 chill, and slowed to 0.6× for 1 s.
- **Icicles:** blinking shadows (1 s) on you, around you and on any encased hero. Each falls in a 1.6-tile blast for 14, plus 4 shards.
- **Blizzard** (phase 2+): arrows show the wind (0.7 s), then for 4 s it shoves everyone at 3 tiles/s (a roll is unaffected). Snow streams across the whole screen, and curtain rows of snow blow through with a drifting hole.
- **Snowballs** (phase 2+): 2 snowballs that grow from 1 to 2.5 tiles over 6 s. They hit for 10–18 by size and burst into shards.

| Phase | Health | Signatures | Moves |
|---|---|---|---|
| 1 | 100–60% | crown | shards ×3, spikes ×2, breath ×2, icicles ×2, penguins ×2 |
| 2 | 60–25% | crown, ice | the same, plus freeze ×3, blizzard ×2, snowballs ×2 |
| 3 | 25–0% | crown, ice, freeze | the same; chill builds in the background |

**Measured** (the wizard bot: it doesn't dodge, light fires or kick the crown, and it rolls out of ice; seeds 31/7/12):
- 3:25 / 2:42 / 2:46, taking 295 / 282 / 343 damage per minute.
- That's the Magus's fight length, with more damage than the hardened Fallout King (147–225). It's left on the hard side for the user's playtest.
- Tuned once on the way: blizzard rows 0.3 → 0.4 s apart, snow 8 → 7, spikes 11 → 9, shard fans 7 → 6.

## 20. Fragile, The Misunderstood (ruins, built in M24.3, 2026-10-06)

**The user's picks:**
- Signatures by phase, kept: sunlight shutters, then shapeshift, then on the beat.
- Moves: all four sets (riff rings + axe throw, bat curtain + mist step, hypnotic gaze + slashes, thralls + chandeliers).
- Quest: her stolen teddy bear.
- Arena: the ruined ballroom.
- Name: the user's. The bear is "Mr. Buttons" (my placeholder).
- The user's change to the draft: "the bear should be with me even after being sewn, i take it to the ballroom, if she is defeated she start crying and i can give her the bear. giving her the bear is 5 level ups."

**Quest: "Mr. Buttons"** (the pawn dealer; the first `kind="fetch"` quest, `systems/quests._fetch`).
- **Pieces:** 4 bear pieces out of 7 spots (`tiles.BEAR_PIECE`), each guarded by 3 **vampire bats**. Bats are the mosquito's flier: 35 HP, they bite for 6.
- **Carrying:** with a piece's guards dead, walk up to take it. You carry it (`QuestState.carry`; a "@x2" by your hero), and an edge arrow points to the STALL.
- **Delivering:** come within 3.5 tiles of the dealer and each piece is sewn in. The last one makes **Mr. Buttons whole, and he stays with you** (`QuestState.bear`; "(@)" by your hero). Her ballroom is then pinned and the quest says to take him there.
- **Falling:** a downed carrier drops the pieces and the bear where they fell (`drops`, pinned as PIECE / MR. BUTTONS). Anyone walking over them picks them up.
- **After the fight:** she doesn't die. She sits where she fell, crying, and becomes an NPC (`QuestState.crying`, art `fragile_crying`; the quest log says "give Fragile her bear").
- **The gift:** talk to her while carrying the bear and every player gains **`FRAGILE_GIFT_LEVELS` (5) levels**, each with its card pick. Without the bear she just sobs for Mr. Buttons.
- Like the escort, this quest needs its giver. F7 hands you the finished bear.
- The camp is the scrap camp with a `pawn` skin (stalls of wares).

**Arena: the ruined ballroom** (`world/landmarks._ballroom`):
- castle stone round a parquet floor;
- 3 shuttered windows along each long wall (one is dropped if it would sit at the gate), each with a **lever** below it;
- her velvet throne across from the gate, 5 coffins behind it;
- two rows of marble pillars (cover from the gaze), 4 chandeliers overhead, cracked mirrors.
- The fixtures are in `props`.

**Boss** (8,000 HP; hit radius 1.6, 2.1 as a bat or wolf). She's a big pixel-art vampire with long black hair and a red bass-axe; the wolf has its own picture, and the bats are a swirling cloud of glyphs (`render/fragile.py`).
- Between moves she keeps 9–12 tiles from her target and out of the light.

**Signature 1, sunlight** (all fight).
- **Open a shutter:** stand within 2.2 tiles of a lever for 1.5 s. The window opens and a slanted shaft of sun (5 tiles wide, 60 long) falls across the floor for 15 s.
- **In the light:** she takes **3× damage**. A shaft opening on her, or her running into one, **stuns her for 2.5 s** (once per opening).
- **She fights back:** every 20 s she slams the nearest open shutter (a "SLAM!" tell at the window, 1 s).
- Heroes in the light are immune to her gaze.
- Marked: "OPEN" with a pull bar over closed levers, "SUN 12" over open ones, LEVER / SUN map pins, an edge arrow to the nearest closed lever while she's within 14 tiles of you, and "SHE BURNS IN THE SUN!" on the boss bar.

**Signature 2, shapeshift** (phase 2+).
- Every 15 s she becomes another form (a 1 s flicker tell); the boss bar shows it ("- BATS", "- WOLF").
- **Bats:** fast, flying over everything. Half damage from everything except the bard's pulse (the game can't tell area hits from shots; a change from the draft). Moves: the bat curtain (rows of bats with a drifting hole), swoops, mist steps.
- **Wolf:** charges along a ">" line (16 damage; into sunlight, it's stunned), a howl (throws you 5 tiles, plus a ring of slashes), claw fans.
- **Herself:** her own moves below.

**Signature 3, on the beat** (phase 3).
- A metronome at 100 bpm, rising to 140 as she nears 0 HP. It's drawn across the bottom of the screen ("ROLL NOW!" on the beat).
- Every tell is stretched to end exactly on a beat (`tell_s`).
- **Perfect roll:** a roll started within 0.12 s of a beat is "PERFECT!" and staggers her for 1.2 s (at most every 5 s).

**Her own moves:**
- **Riff:** a strum, then 3 rings of 24 notes, each with a gap.
- **Axe throw:** the axe raised, then the bass-axe flies out 22 tiles on a curve and back to her, hitting for 14 on each leg.
- **Slashes:** 3 fans of 5 red crescents.
- **Gaze:** a red wedge (0.8 s), then for 2.5 s heroes in the 40° cone (within 16 tiles, with line of sight) are pulled toward her at 3 tiles/s. Rolling, the sun, or anything blocking sight stops it.
- **Mist step:** a shimmer where she'll appear, then she's there, leaving a mist trail that slows you to 0.6× for 4 s.
- **Thralls:** her coffins creak, then 2 thralls (80 HP) climb out of the ones not staked, at most 4 alive. Stand at a coffin for 2 s to stake it shut for good ("STAKE" marks and pins).
- **Chandeliers** (phase 2+): shadows under the 2 nearest you, then they crash (2.5 tiles, 18 damage) and stay as rubble cover.

| Phase | Health | Signatures | Her own moves |
|---|---|---|---|
| 1 | 100–60% | sun | riff ×3, axe ×2, slashes ×3, gaze ×2, mist ×2, thralls ×1 |
| 2 | 60–25% | sun, forms | the same, plus chandeliers ×2; bat and wolf forms have their own moves |
| 3 | 25–0% | sun, forms, beat | the same, all ending on the beat |

**Measured** (the wizard bot: it doesn't dodge, pull levers, stake coffins or roll on the beat; seeds 31/7/12):
- 2:48 / 2:43 / 3:04, taking 285 / 350 / 270 damage per minute. That's in line with the Snow King. Left for the user's playtest.

**Fixed along the way:**
- A stun from inside one of her own moves (the wolf charging into the sun) tried to close the move that was calling it.
- A quest hook placed in the middle of an `if`/`elif` chain stopped her fight from ever starting.
- The talk prompt now says "talk to Fragile" for named characters, not "talk to the Fragile".
