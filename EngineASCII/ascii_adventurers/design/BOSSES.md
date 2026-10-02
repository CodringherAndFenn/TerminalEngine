# AsciiAdventurers — Quests, Bosses and Landmarks

Status: **rev 1 — the framework and the swamp are BUILT in M17 (2026-10-01).** Rev 1 applies the user's answers to the rev 0 questions (section 9). What M17 built, and where it differs from the draft below, is in section 10. The user decides every boss; this doc holds the shared rules, the vocabulary to build bosses from (like the card archetypes in CARDS.md), and the first quest + boss to prove the framework. Open questions are in section 9. **2026-10-02:** the user set the boss roster (section 11, three per ring biome) and the roadmap was redone (section 8).

---

## 1. Run structure (what quests are for)

1. Each run draws **one quest per ring biome** from that biome's quest list. Finishing it **summons that biome's boss**. Since 2026-10-02 each ring biome has **three bosses** (section 11), and the run's seed picks one of them, together with the quest that leads to it.
2. Beating all 5 ring bosses unlocks the **plains boss**.
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
| Collect | gather 3 relic shards | pickups placed at points of interest |
| Visit / activate | light 4 ruin beacons | uses landmarks (section 4) |
| Escort / defend | keep an NPC alive for 60 s | later; needs co-op-safe rules |
| Survive | hold a ritual circle while waves come | later |

### 3.2 Quest rules

- **No ambush targets** (standing rule): quest enemies must be visible and shootable from range, like every other enemy.
- **Quests come from NPCs.** The biome quest starts when you talk to its quest giver; until then the boss can't be summoned.
- **Quest givers are pinned on the map from the run start** (minimap edge arrow + big map icon), so players never wander looking for them. Their quest area sits next to them.
- Quest targets are **findable**: they live in the landmark's area, and the HUD shows progress (`Frogs 2/5`). A future Archivist "Charts" shelf could reveal more (e.g. the targets themselves).
- Progress is **per run** and shared by all players in co-op.
- When a quest completes, the boss is summoned **at its lair** (a landmark), not on top of the player — the player chooses when to walk in.

### 3.3 Quest log

- A small HUD line per active quest, plus a quest page on the big map (M key).
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

1. **Everything is telegraphed** (wind-up glyph, aim line, landing circle, sound) at least ~0.5 s ahead. Damage you couldn't see coming is a bug.
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
| **M22** | **Boss pools**: 3 bosses per biome, the seed picks one per run, each with its own quest; the boss's real kind can be hidden behind one name (Mycelium); per-boss bestiary pages and achievements. Froggy is the swamp's first; proven with the second swamp boss |
| M22.1 | Swamp: **leech swarm** |
| M22.2 | Swamp: **mosquito** |
| M23.1-3 | Desert: **beetle**, **spitting camel**, **nomad sand wizard** |
| M24.1-3 | Ruins: **radioactive monster**, **ice wizard**, **vampire girl** |
| M25.1-3 | Forest: **corrupted pixie**, **mad murderer squirrel**, **mimic tree** |
| M26.1-3 | Mushroom: **Mycelium** (three variants: amanita muscaria + two more) |
| M27 | Plains boss (not designed yet) + Adventurer's Glory + "end run" victory (+ water movement) |
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

Three bosses per ring biome. Each run meets one of them, picked by the seed (section 1; confirmed by the user). All three in a biome are tier I: about equal strength, different playstyles.

| Biome | Bosses | Notes |
|-------|--------|-------|
| Swamp | **Froggy McFrogface** (built), a **leech swarm**, a **mosquito** | the swarm is many bodies with one shared health bar (a new boss shape); the mosquito is fast, flies, drains blood |
| Desert | a **beetle**, a **spitting camel**, a **nomad sand wizard** | |
| Ruins | a **radioactive monster**, an **ice wizard**, a **vampire girl** | Adventure Time nods (the glowing lich-like monster, the ice king, the vampire queen). Use our own names and looks so the built game doesn't copy the show (the user will rename them) |
| Haunted forest (M21) | a **corrupted pixie**, a **mad murderer squirrel**, a **mimic tree** | the mimic hides among ordinary trees |
| Mushroom | **Mycelium**, always: one of three real mushrooms (**amanita muscaria** + two others), but the name, quest and HUD always say just "Mycelium", so you only find out which one in the fight | the other two (user, 2026-10-02): **shaggy ink cap** (melts into ink pools) and **giant puffball** (spore bursts) |
| Plains (tier II) | not decided | |
