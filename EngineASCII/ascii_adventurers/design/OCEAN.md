# AsciiAdventurers — The Ocean Zones

Status: **rev 0 — M29 (Paradise) DRAFTED with the user, 2026-11-21; not built.** These are M29-M32 in `BOSSES.md` section 8. The user may change anything here after playing it ("leave the design docs so I can change them later after testing"). Picks are the user's unless marked **(mine)**: routine calls made where the user said nothing, open to change.

---

## 1. The four zones (user)

Four islands out in the ocean, reached by **water walking** (Adventurer's Glory, M27). **Fixed places, not shuffled:**

| Place | Zone | The idea (user's words, condensed) |
|-------|------|-----------------------------------|
| **North** | **Paradise** (heaven) | A white, heaven-like island with a twist: "biblically accurate" horror angels and Bible-inspired monsters that look pretty at first and turn into extremely bloody monsters. Blood is a big theme; **white and red** are the colours. **M29.** |
| **South** | Hell | Hell twisted toward excess: the humans there aren't tortured, all their pleasures are indulged (the opposite of the torturous heaven), but the trance makes them mad, so they're still aggressive. **Revellers in groups:** they feast, drink and dance lost in the trance, ignore you until you come close or hit one, then the whole group frenzies. Kept to feasts, wine, music, dance, gold and vanity, with our own names. Drafted later |
| **West** | The Past | To draft (ask what "the past" means) |
| **East** | The Future | To draft (ask what "the future" means) |

Heaven against Hell and the Past against the Future are natural pairs for M33's kill order.

## 2. The region framework (user, M29 round 1)

- **One island per zone, ~350 tiles in radius** (about 40 s to cross, a seventh of a ring biome), with its own coast. **(mine)** Its centre sits due N/E/S/W, far enough out that its near shore is about **a minute of water walking** (~500 tiles) past the main island's coast in that direction (the coast wanders, so it's measured from the actual coast, not `CARDINAL_REGION_DISTANCE`).
- **Hidden until found:** nothing on the big map or the minimap until a player comes near. **(mine)** "Near" = within 120 tiles of its shore; from then on its outline shows (dimmed, like the island's biomes) with its name.
- **Endgame tough:** on top of the level scaling (`ENEMY_HP_PER_LEVEL`...), the zone's ordinary enemies get **x2.5 HP and x1.5 damage**, packs about a third bigger and elites more often **(numbers mine, from the user's pick)**.
- The HUD shows the zone's name on arrival, like a biome. The water between is empty ocean.
- Each zone: its own terrain and landmarks, its own enemies, a giver and a quest that summons its **tier III** boss ("absolutely crazy", BOSSES.md section 2), arena sealed until then.

## 3. Paradise (north): the land

**Name: PARADISE.** **Look: marble and clouds** — soft white cloud ground, paved marble roads lined with gold posts, white blossom trees, marble columns standing and fallen. The ocean round it fades into a **cloud bank** instead of a beach. Red comes only from blood.

**Blood on the land (all four):**
- **Blood fonts:** marble basins of blood. Unveiled angels go to them to drink and heal, so you fight them away from the fonts. **(mine)** An unveiled enemy under 40% HP heads for a font within 30 tiles and heals while it stands at it.
- **Weeping statues:** statues of saints crying red tears; blood trickles away from them over the marble.
- **Stains from fights:** an unveiled angel bleeds a red trail where it moves, and the stains stay: the island gets redder the more you fight on it.
- **A river of blood** winds across the island down from the boss's arena (the Leviathan lives in it).

**Landmarks (all four):**
- **The Gate:** a great gold-and-pearl gate, half open, on the shore facing the main island, a broken wall running off either side.
- **The stairway to nowhere:** a white staircase climbing out of the island and ending in the air. The giver is chained at its foot.
- **Choir rings:** circles of singing statues; angels (Choristers) gather round them.
- **The fallen cathedral:** a broken nave — rows of pillars, an altar, shattered rose windows on the floor.
- **(mine)** The island rises gently toward its centre, where the boss's court stands (section 6).

## 4. Paradise: the enemies (all 16 picked)

**The unveiling (user):** every one of them unveils on its own. Serene first: white, a gold halo, slow hymn-like attacks. **Hurt below ~70%, or approached closely** (**(mine)** within 5 tiles), it unveils: wings split into eyes, the halo becomes a wheel, it bleeds — faster and deadlier. Killing them before they unveil is the skill. **(mine)** The unveiling takes a short tell (~0.6 s) and can't be undone.

| Group | Enemy | Serene | Unveiled |
|-------|-------|--------|----------|
| Angels | **Cherub** | a winged putto plinking a lyre (slow notes) | the true cherub: four faces (man, lion, ox, eagle) on a body of eyed wings; lunges and bites, roars a short cone |
| | **Seraph** (elite) | a tall figure hidden in six white wings, singing slow rings of light | the wings open on a burning, eyed core that spins spiral rings of blood and fire |
| | **Ophan** | a gold halo rolling gently | wheels within wheels rimmed with eyes; races in straight lines, bounces off walls, leaves blood |
| | **Watcher** | a veiled white pillar | opens a hundred eyes; sweeps a gaze beam (its line shows before it fires) |
| Heralds | **Trumpeter** (elite) | long notes that gently push you back | each blast calls a plague: a hail of fire and blood over a marked area |
| | **Censer-bearer** | swings a censer: harmless incense haze | hurls burning coals that leave fire patches |
| | **Bowl-bearer** | carries a gold bowl | pours it: a pool of blood spreads where you stand (slows you, you bleed) |
| | **Chorister** | sings at the choir rings; its hymn heals angels near it | shrieks: expanding rings |
| Saints and beasts | **Weeping Saint** | a praying marble saint | bleeds from its eyes; lobs arcs of blood tears that leave pools |
| | **Martyr** | kneels, pierced with arrows | rips the arrows out and throws them back in volleys |
| | **Behemoth** (elite) | a huge white ox, grazing | hide splits on bone plates; charges in lines, breaks the columns it hits |
| | **Leviathan** (elite) | a white serpent in the river of blood | surges along the river, spits blood at you from it |
| Chasers | **The Lamb** | a fluffy white lamb | seven horns and seven eyes (Revelation); charges straight at you |
| | **Doves** | a flock of white doves | bloody beaks; dive at you one after another |
| | **Locusts** | Revelation's locusts: golden crowns, human faces | a stinging swarm |
| | **Halo** | a lone halo drifting toward you | spins up into a buzzsaw |

## 5. Paradise: the quest (user)

**Break the seven seals.** Seven seals lie across Paradise, each in a guarded clearing (out from the start; every one counts, quest taken or not, like the ring quests). Stand at one while it breaks (**~8 s**) as angels unveil and come at you (**(mine)** built on the survive-circle code: leave the circle and the breaking pauses). **Each broken seal turns the sky a shade redder** (**(mine)** the island's whites tint toward red, seal by seal). The **seventh wakes the boss**.

**The giver: a fallen angel**, cast out and chained by one wing at the foot of the stairway to nowhere. Bitter, wants the throne to fall; the only one who tells you the truth about Paradise.

## 6. Paradise: the boss — THE FOUR HORSEMEN (user)

**Arena: the throne at the summit.** Paradise climbs gently to its centre; the arena is a vast marble court on top, with the river of blood pouring down from it. Sealed until the seventh seal breaks.

**Two forms, like the necromancer's two lives, each a full kit.**

**Movement: always riding.** They gallop round the court the whole fight (circles, figure-eights, crossing lanes), slow down but never stop for their moves. Only a few moves plant them, with a clear tell.

### 6.1 Form 1: the serene cavalry

Four radiant white knights on white horses, riding as **one cavalry with one shared health bar**.

**Signatures (all four), one added per phase** — **(mine)** four phases (100-75-50-25-0%), since four were picked:
1. **Formation charge:** lanes of light mark where they'll ride, then all four charge through in a formation (a line, a wedge, or a cross from four sides). Read the lanes, roll through the gaps.
2. **Light lances:** each rider throws a gleaming lance that sticks in the marble as a pillar of light; pillars join into fences of light that cage you. Break a pillar to open the cage.
3. **The hymn:** while the four ride close together they sing in harmony: shielded, and slowly healing. Split them up (hit the lead singer hard, or pull one away) to break the chord.
4. **The four winds:** each rider takes a corner and the winds blow from all four (Revelation 7): you're pushed toward the lances. Plant your feet in the calm spots.

**Moves (all four):** **carousel** (they circle you at a tightening radius, throwing light inward; out through the gaps), **hoof rings** (rings of light from their hooves as they gallop), **halo rain** (gold halos fall into marked circles), **trample** (one rider breaks off along a shown line, then rejoins).

### 6.2 Form 2: the Four Horsemen, unveiled

At 0 the cavalry unveils into **the Four Horsemen**, each with **its own health bar and kit**. **When one dies, the others take its power** (its kit joins theirs), so the last one standing has all four.

**Look: Bible colours, bloody.** Conquest on the white horse (crowned, a bow); War on the red (a great sword); Famine on the black (a pair of scales); Death on the pale horse with Hades, a dark maw, following behind. Each horse flayed and bleeding, the riders covered in eyes.

| Horseman | Kit (all four picked for each) |
|----------|--------------------------------|
| **Conquest** | **Crowning arrows** (a hit puts a crown on you: while crowned you're "conquered" and deal half damage; a roll knocks it off); **arrow fans** while galloping; **banners** (claim a circle of ground that burns heroes and keeps spreading until the banner is broken); **victor's lap** (the court's rim at full speed, volleys inward; the safe lane is right behind it) |
| **War** | **Sweeping blade** (wide crescent slashes, each sending a wave of blood rolling on); **blood charge** (along a shown line, turn, again, up to 3, leaving a burning river of blood); **strife** (calls unveiled angels into the court in waves while it lives); **duel ring** (plants its sword; a ring of blood closes round you and it; inside you both deal double damage until 8 s pass or you break out) |
| **Famine** | **The scales** (every few seconds it weighs you against itself: whoever has more health, as a share of max, loses some to the other — keep it hurt and you're safe); **hunger** (within 8 tiles no healing works: no regen, lifesteal or pickups); **weights** (heavy black weights, marked first, crush where they land and stay as obstacles); **locust plague** (swarms of Locusts pour from its saddlebags) |
| **Death** | **Hades follows** (a pool of darkness trails its path and lingers; inside you can't heal and are slowly pulled to its centre); **a fourth of the earth** (the court splits into four quarters; one at a time darkens for 2 s, then is struck — a visible wave); **reaping** (wide spinning scythe arcs as it rides); **the dead rise** (anything slain in the court rises once as a pale shade for 10 s, a fallen Horseman too) |

### 6.3 Numbers (mine, to tune with the bot and then in play)

- Tier III sits above the necromancer (8,000 a life, bot 5:52-7:36). **Proposed:** the cavalry 12,000; each Horseman 6,000 (inheritance makes the later ones much harder); all scaled like every boss. Policy: no HP cut below these on bot numbers alone.
- Target length (bot): the cavalry ~3 min, the Horsemen ~5 min.
- Relics: like every boss, 2-3 uniques (GEAR.md 21.1); **(mine)** one per Horseman (4), drafted with the user when the boss is built.

## 7. Build plan (mine; each step: tests, a headless screenshot, a report, a stop)

| Step | Content |
|------|---------|
| M29.1 | **The region framework + Paradise's land:** placing the four zone islands (only Paradise generated; the others stay ocean), Paradise's terrain (cloud ground, cloud-bank shore, marble roads, gold posts, blossom trees, columns), the river of blood, fonts, weeping statues, the four landmarks, the summit court (sealed shell), hidden-until-found on the big map and the minimap, the HUD name, blood stains (the ground layer that keeps them), the sky's red tint by seals broken |
| M29.2 | **The unveiling + the first 8 enemies:** the shared serene/unveiled framework (tells, blood trails, fonts healing), endgame toughness; Cherub, Seraph, Ophan, Watcher, the Lamb, Doves, Locusts, Halo |
| M29.3 | **The other 8 enemies:** Trumpeter, Censer-bearer, Bowl-bearer, Chorister, Weeping Saint, Martyr, Behemoth, Leviathan |
| M29.4 | **The quest + form 1:** the seven seals, the fallen angel, waking and sealing the court; the serene cavalry (4 phases, 4 signatures, 4 moves), always riding |
| M29.5 | **Form 2:** the Four Horsemen (16 abilities), inheritance, the bot benchmark; then the 4 relics drafted with the user |
