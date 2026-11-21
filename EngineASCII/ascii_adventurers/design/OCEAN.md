# AsciiAdventurers — The Ocean Zones

Status: **rev 0 — M29 (Paradise) DRAFTED with the user, 2026-11-21. M29.1 BUILT (2026-11-21, section 8). M29.2 BUILT (2026-11-21, section 9).** These are M29-M32 in `BOSSES.md` section 8. The user may change anything here after playing it ("leave the design docs so I can change them later after testing"). Picks are the user's unless marked **(mine)**: routine calls made where the user said nothing, open to change.

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
| M29.1 | **The region framework + Paradise's land:** placing the four zone islands (only Paradise generated; the others stay ocean), Paradise's terrain (cloud ground, cloud-bank shore, marble roads, gold posts, blossom trees, columns), the river of blood, fonts, weeping statues, the four landmarks, the summit court (sealed shell), hidden-until-found on the big map and the minimap, the HUD name. **Built, section 8** (the blood stains moved to M29.2 and the sky's tint to M29.4: they need the enemies and the seals) |
| M29.2 | **The unveiling + the first 8 enemies:** the shared serene/unveiled framework (tells, blood trails **and the stains they leave, kept on the ground**, fonts healing), endgame toughness; Cherub, Seraph, Ophan, Watcher, the Lamb, Doves, Locusts, Halo. **Built, section 9** |
| M29.3 | **The other 8 enemies:** Trumpeter, Censer-bearer, Bowl-bearer, Chorister, Weeping Saint, Martyr, Behemoth, Leviathan |
| M29.4 | **The quest + form 1:** the seven seals (**and the sky reddening, seal by seal**), the fallen angel, waking and sealing the court; the serene cavalry (4 phases, 4 signatures, 4 moves), always riding |
| M29.5 | **Form 2:** the Four Horsemen (16 abilities), inheritance, the bot benchmark; then the 4 relics drafted with the user |

## 8. Built: M29.1 (2026-11-21) -- the zone framework and Paradise's land

**The framework** (`world/zones.py`): `config.OCEAN_ZONES` lists the built zones (Paradise only); `ZONE_PLACES` fixes N/S/W/E. A zone is one island (`ZONE_RADIUS` 350, its coast wandering 15%); the layout paints its biome over the ocean (`IslandLayout._classify`, a bounding-box test first so the rest of the world pays nothing). Its centre is placed from the actual coast: the main island's farthest land within `ZONE_FAN` of its compass line, plus `ZONE_GAP` (500 tiles, about a minute of water walking), plus its own radius. Over five seeds Paradise sits 3,150-3,400 tiles north. The other three places stay open sea (`cardinal_sites` still reserves them).
- **Hidden until found:** `world.found_zones`; a player within `ZONE_FOUND_RANGE` (120) tiles of the shore adds it. Until then the maps show open sea there (`ui/maps.map_pixels`); after, its outline, its name on the big map, and the big map's zoom reaches it (`IslandLayout.view_radius`).
- **Arrival:** the first time a player sets foot on it, a banner: **PARADISE -- "where the angels sing"** (`config.ZONE_ARRIVAL`; once a run).
- **Dev mode: F3** jumps just inside the next zone's Gate, walking on water (on the dev bar).

**Paradise's land** (`world/paradise.py`: a `Plan` per seed, cached on the zone, ~60 ms). As drafted (section 3), plus these calls of mine:
- **A ring road round the summit**, past the outermost terrace: spur roads to the landmarks leave from whichever is nearer, the main road or the ring (spurs from the main road alone ran under the court's wall).
- **The ground is the lightest in the game** (a pale lavender-grey with sparse white specks; marble roads and floors lighter still; the cloud bank lightest): the first, darker try read as a starry night, not a white island. Shots still read on it (checked with the wizard's bolts and darts).
- **The court:** an oval of 92 x 62 tiles walled in pearl (3 thick), its gate (golden bars, 7 wide) facing the Gate; gold inlay rings; eight columns for cover; the throne (9 x 3, gold) at the far side with a step before it; a thin channel of blood from the throne's foot to the wall on the river's side (the wall stays whole; the river runs on outside). Three terraces of marble steps round it (10, 22, 34 tiles out).
- **The Gate:** gold pillars 4 tall, the left half of the opening shut with bars, the right half open, the right leaf swung inland; the pearl wall runs 40 tiles each way along the shore, more broken toward its ends, only on land.
- **The river:** from the court's side (100-140 degrees round from the gate), meandering out to the sea; marble bridges where roads cross it.
- **The cathedral** (46 x 22, its door to the west): broken pearl walls with gaps, two rows of columns (some fallen or rubble), the gold altar at the east end with steps, the rose window shattered on the floor (red, blue and gold glass).
- **The stairway:** a landing, 26 white steps between balustrades climbing outward, the last five fading, a puff of cloud past the end; the chain post at the landing's corner (the giver stands by it, M29.4).
- **Choir rings:** marble discs, 8 statues round each, a gold inlay cross in the middle. **Fonts:** a marble plaza, a rim, 3 x 2 tiles of blood. **Weeping statues:** on a plinth, a 6-10 tile trickle of blood running away from the summit.
- **Ground:** cloud; puffier drifts; blossom groves in clumps (felled: petals); lone columns standing and fallen (breakable). The land's last tiles go soft (drifts) and the sea within 22 tiles turns to a thinning cloud bank. Blood river, fonts and the cloud bank are watery: only water walkers cross them (heroes there always are).
- **No enemies yet** (`BIOME_ENEMY_DENSITY` has no "paradise"): M29.2.

**For later:** the explored map keeps one byte per tile type; with Paradise there are 205 of 255. Hell, the Past and the Future will need it widened (16-bit) or tile types sharing a map class. And the spawner's `LANDMARK_QUIET` will keep enemies off Paradise's many landmarks (the fonts, the choir rings) unless M29.2 excepts them.

**Code:** `world/zones.py`, `world/paradise.py`; `world/layout` (`zones`, `zone_at`, `zone_near_rect`, `view_radius`, `_classify`, `all_ocean`); `world/generator` (`_paradise`, the plan's `paint`); `world/landmarks.build_landmarks` (the zones' marks); `world/biomes.PARADISE`; tiles (31 new) and palette; `systems/collision.WATERY`; `ui/maps`; `scenes/game` (`_zones_near`, `_dev_zone`). **Tests:** `tests/test_m29_1.py` (21); `test_world`'s far-ocean and cardinal-site tests and `test_m17`'s camp/lair spacing test now leave the zones out. Full suite 1736 OK.

## 9. Built: M29.2 (2026-11-21) -- the unveiling and the first eight enemies

**The unveiling** (`ai/paradise.Angel`, as drafted in section 4): every one starts serene (white, a gold halo, moving at x0.45, slow hymn-like attacks) and unveils on its own when hurt below 70% of its max HP or when a hero comes within 5 tiles: a 0.6 s tell (it flickers between its two looks, faster and faster, with the red "!"; nothing stops it and it can't be undone), a burst of eyes, and then the horror at full speed with its own attacks. Killed during the tell, it still dies serene. **(mine)** A serene one dies clean, in a puff of feathers; an unveiled one bursts in blood.
- **Blood (the stains stay):** unveiled, it leaves a stain every 1.5 tiles it moves (60% chance; the small fliers much less, the ophan more), some where it's hit, and a pool where it dies. Stains are tiles set for good (`ChunkedWorld.set_tile`, re-applied when a chunk reloads), so the island gets redder the more you fight on it, on the minimap too. Cloud stains, then soaks; marble roads, floors and steps stain (`world/tiles.STAINS`). Drops fall off unveiled ones as they go.
- **The fonts:** an unveiled one under 40% goes to the nearest blood font within 30 tiles and drinks there (a red "+" rising), healing 6% of its max HP a second until it's back to 90%; it gives up on a font it can't reach in 12 s. Watchers never move, so never drink.
- **Endgame tough** (`ZONE_TOUGH`, `systems/spawner`): anything woken on a zone has x2.5 max HP and x1.5 damage on top of the level scaling (bosses' adds too); packs are a third bigger and elites twice as likely. **(mine)** Paradise's density is 1.0 (like the forest's), with bigger packs.
- **Where they spawn:** on a zone only the Gate, the giver's stairway and the court keep enemies off (`ZONE_QUIET_MARKS`); the fonts, statues, choir rings and the cathedral are the angels' own.

**The eight** (numbers in `config.py`: `CHERUB`, `SERAPH`, `OPHAN`, `WATCHER`, `LAMB`, `DOVES`, `LOCUSTS`, `HALO`; base HP before the zone's x2.5):

| Enemy | Serene | Unveiled |
|-------|--------|----------|
| **Cherub** (60) | keeps 7 tiles back, plinks a run of 3 slow lyre notes every 2.2 s | four faces (man, lion, ox, eagle) on eyed wings: chases; crouches (its line shows) and lunges up to 4 tiles, biting; every 4 s within 5 tiles, roars a 60-degree cone that pushes you back |
| **Seraph** (elite, 320) | hidden in six wings; keeps 9 back, a ring of 12 slow shots of light every 3 s | the wings open on a burning eye: keeps 7 back; every 4.5 s its wings flare (the tell) and it spins a 1.8 s spiral, bursts of 4 turning each time, blood and fire in turn |
| **Ophan** (70) | a gold halo rolling gently at you, bumping | wheels within wheels rimmed with eyes: rests 1 s, lines up (its line shows), races at 13 tiles/s for 2.2 s bouncing off walls, hurting what it runs through and leaving a slick of blood that slows you (x0.6) |
| **Watcher** (110) | a veiled pillar; never moves; an orb of light every 2.6 s | a hundred eyes: fixes its gaze (a dotted line following you, then holding still for the last 0.3 s), then a beam that burns 1 s, sweeping 50 degrees the way you were going; blocked by anything that stops shots |
| **The Lamb** (50, 2-3) | ambles at you and butts | seven horns, seven eyes: scrapes (the charge line shows) and charges 12 tiles at 14 tiles/s, goring and shoving; a column or wall dazes it |
| **Doves** (10, flocks of 5-7) | peck lazily | bloody beaks: circle you and dive through one at a time |
| **Locusts** (7, swarms of 6-9) | crowned, with human faces; drift and sting now and then | a fast weaving stinging swarm |
| **Halo** (40) | drifts at you; a touch hurts a little | a buzzsaw: full speed, turning at most 2.6 rad/s (so it overshoots and comes round), sawing what it touches |

**Look** (`render/paradise_art.py`, two pictures each; the ophan's wheels turn and the halo spins): serene ones white and gold with a halo; unveiled ones eyes (white with black or red), red and clotted blood (new sprite letters `z`, `Z` holy light). Shots: lyre notes (gold), light (white-gold), blood, fire. Tells: `render/paradise.py`.

**Code:** `ai/paradise.py` (Angel and the eight; `stain`, `pool`, `fonts`), `render/paradise_art.py`, `render/paradise.py`; config `UNVEIL`, `FONT`, `STAIN`, `ZONE_TOUGH`, `ZONE_QUIET_MARKS`, the eight's tuples, `PARADISE_SHOTS`; `systems/spawner` (toughness, packs, elites, the quiet marks); tiles `STAINED_CLOUD`, `SOAKED_CLOUD`, `STAINED_ROAD`, `STAINED_FLOOR`, `STAINED_STEP` (210 of 255 map classes now); effects `unveil`, `feathers`, `gore`; zone `blood_slick`. **Tests:** `tests/test_m29_2.py` (28); `test_m29_1`'s "no enemies yet" now checks there are; `test_m17`'s "no random enemies on landmarks" leaves out a zone's own landmarks (only `ZONE_QUIET_MARKS` stay clear).

**For later:** the density, the toughness and every enemy's numbers want a play test (and the bot, once the Horsemen exist). M29.3 adds the other eight (the heralds, the saints and beasts); the Choristers will gather at the choir rings.

**NEXT: M29.3, the other eight enemies.**
