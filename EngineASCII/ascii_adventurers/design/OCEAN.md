# AsciiAdventurers — The Ocean Zones

Status: **rev 0 — M29 (Paradise) DRAFTED with the user, 2026-11-21. M29.1 BUILT (2026-11-21, section 8). M29.2 BUILT (2026-11-21, section 9). M29.3 BUILT (2026-11-21, section 10). M29.4 BUILT (2026-11-22, section 11). M29.5 BUILT but for its relics (2026-11-22, section 12).** These are M29-M32 in `BOSSES.md` section 8. The user may change anything here after playing it ("leave the design docs so I can change them later after testing"). Picks are the user's unless marked **(mine)**: routine calls made where the user said nothing, open to change.

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
| M29.3 | **The other 8 enemies:** Trumpeter, Censer-bearer, Bowl-bearer, Chorister, Weeping Saint, Martyr, Behemoth, Leviathan. **Built, section 10** |
| M29.4 | **The quest + form 1:** the seven seals (**and the sky reddening, seal by seal**), the fallen angel, waking and sealing the court; the serene cavalry (4 phases, 4 signatures, 4 moves), always riding. **Built, section 11** |
| M29.5 | **Form 2:** the Four Horsemen (16 abilities), inheritance, the bot benchmark; then the 4 relics drafted with the user. **Built but for the relics, section 12** |

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

## 10. Built: M29.3 (2026-11-21) -- the other eight enemies

On the same unveiling as section 9 (`ai/paradise.Angel`). **(mine)** Where section 4 gives a serene form only a look (the censer's haze, the bowl, the praying saint, the kneeling martyr, the grazing ox, the white serpent), it's harmless while serene: killing it before it unveils costs you nothing. The trumpeter pushes and the chorister heals while serene.

| Enemy | Serene | Unveiled |
|-------|--------|----------|
| **Trumpeter** (elite, 300) | keeps 9 back; a long note every 3.5 s pushes heroes within 6 tiles 1.5 back (no damage) | each blast (0.7 s tell) calls a plague: a 4-tile circle round you is marked for 1.2 s (orange ring), then 10 strikes fall in it over 1.2 s, fire (leaving a burning patch) and blood (leaving stains) in turn. The plague falls even if the trumpeter goes off to drink |
| **Censer-bearer** (65) | follows you swinging its censer: puffs of harmless incense | keeps 7 back; every 2.4 s hurls 2 burning coals in an arc (a mark where each will land); they burst and leave fire (burning) for 3 s |
| **Bowl-bearer** (70) | follows you with its gold bowl (harmless) | keeps 5 back; every 4 s marks where you stand (a growing ring, 0.9 s) and pours: a pool of blood that spreads from 1 to 3 tiles over 6 s, slows you (x0.6) and bleeds you; the ground under it stains |
| **Chorister** (55) | **lives at the choir rings, 3 to a ring** (mine); lingers there singing, healing every angel within 6 tiles 3% of its max HP a second (not itself; gold notes rise while it heals) | keeps 4-7 back; shrieks (0.5 s tell) 3 rings of 16 shots, each turned half a gap from the last |
| **Weeping Saint** (80) | kneels where it is, praying (harmless) | bleeds from its eyes; keeps 8 back; every 2.8 s lobs 3 tears (marks where they land) that burst and leave pools of blood (slow x0.7, 5 s) |
| **Martyr** (75) | kneels, pierced with 10 arrows (harmless) | **every hit from a hero sticks another arrow in it, up to 15** (mine); keeps 7 back and every 1.6 s rips out up to 5 and throws them back in a fan. Out of arrows, it throws nothing: shooting it feeds it |
| **Behemoth** (elite, 420) | a huge white ox grazing round where it lives (harmless) | bone plates: hits from within 60 degrees of its front do half. Within 14 tiles it scrapes (its line shows) and charges 16 tiles at 15 tiles/s, three charges in a row, **trampling columns, fallen columns and blossom trees** (they break), goring and shoving; pearl walls, statues and the like daze it 1.6 s |
| **Leviathan** (elite, 380) | **lives in the river of blood, 3 to the river** (mine); a white serpent swimming lazily within 18 tiles of home (harmless) | surges along the river (11 tiles/s) to the stretch nearest you and spits 3 gobs of blood in a 30-degree fan every 1.6 s; bites whoever stands on it. It never leaves the river (it moves along the river's line) and never goes to the fonts |

**Residents** (`systems/spawner`): the choristers and the leviathans aren't rolled at random (`biomes=()`); `ai/paradise.residents` puts them at their places and the spawner adds them to their chunk's roster (ids from `RESIDENT_ID`), so they wake, sleep and stay dead like any other. The other 14 are rolled across the island as before.

**Look:** 16 new pictures (`render/paradise_art.py`): the trumpeter with its long gold trumpet (unveiled: the bell gapes, eyes down its wings), the censer-bearer (unveiled: coals burning in the censer), the bowl-bearer (the bowl brimming with blood), the chorister with its open book (unveiled: its mouth torn wide), the grey kneeling saint (red tears), the martyr full of arrows (the wounds open), the white ox (bone plates and raw red), the serpent rising out of the blood (eyed, fanged). Tells (`render/paradise.py`): the arcs and landing marks of coals and tears, the plague ring, the bowl's ring, the behemoth's charge line, the chorister's notes. Zones: incense, blood pools. Shots: a martyr's arrows, a chorister's shrieks (pale red), a leviathan's spit.

**Code:** `ai/paradise.py` (Trumpeter, CenserBearer, BowlBearer, Chorister, WeepingSaint, Martyr, Behemoth, Leviathan; Angel gains `lob`/`landed`, `always` and `drinks`; `rivers`, `residents`); config `TRUMPET`, `CENSER`, `BOWL`, `CHORISTER`, `SAINT`, `MARTYR`, `BEHEMOTH`, `LEVIATHAN`, three more `PARADISE_SHOTS`; `systems/spawner` (residents). **Tests:** `tests/test_m29_3.py` (19); two `test_m29_2` checks widened (Paradise has more than the first eight now).

## 11. Built: M29.4 (2026-11-22) -- the seven seals, the fallen angel, the summit court, the Serene Cavalry

**The quest** (`config.QUESTS["seven_seals"]`, a new quest kind "seals" in `systems/quests.py`, built on the survive circles as drafted in section 5):
- **The seven seals** lie in clearings across Paradise (`world/paradise.Plan.seals`, at least 60 tiles apart): a marble disc, a gold ring of 3.5 tiles (stand inside it), a great seal of red wax stamped in gold in the middle. **Three serene angels stand guard at each from the start** (mine: picked from cherub, lamb, watcher, martyr, bowl-bearer). Stand in the ring 8 s in all to break it; step out and it mends at half speed. Every 2.7 s of it, 2-3 angels come at you from 9-13 tiles out, **already unveiling** (cherubs, lambs, halos, ophans, censer-bearers, doves). Every seal counts, quest taken or not.
- **The sky reddens** seal by seal: over Paradise the whole view is tinted toward red (green and blue down 7 and 9 of 255 a seal; mine). My first try was twice as strong and turned everything muddy brown at seven.
- **The fallen angel** (the giver, `fallen_angel`): chained by one wing at the stairway's chain post, bitter, the only one who tells the truth. Her lines are mine (OCEAN's draft gave her character, not her words): she asked what the white was for; the riders are "white as a lie"; split them when they sing; when they plant their lances, run.
- **Hidden until found** like the island: her pin and the quest's other pins show only once Paradise is found. Paradise's boss **isn't one of the GUARDIANS** for Adventurer's Glory (that's the ring biomes').
- **The summit court** is the quest's lair: its golden bars open when the seventh seal breaks ("SOMETHING STIRS..."), close behind you when you walk in (the fight: "THE SERENE CAVALRY -- on the summit of Paradise"), and open again when it's won ("THE SERENE CAVALRY IS DEFEATED -- Paradise falls silent").
- Under the hood: Paradise's plan builds the quest's camp (the stairway, its spots the seals), its lair (the court) and the seals' clearings, and the ring biomes' placer skips the zones' quests. Dev keys: F5 picks the quest, F6 the giver, F7 breaks all seven, F8 the court's gate, F9 the nearest seal (a jump onto a zone gives water walking).

**The Serene Cavalry** (`ai/cavalry.py`): **one health bar (12,000), four bodies.** The cavalry itself has no body; its four riders (white knights on white horses with gold manes) are what you hit, and every hit goes to the shared bar. It's exempt from the zone's toughness (a boss has its own numbers); its pillars aren't.
- **Always riding:** they gallop round you at 11 tiles/s -- a circle, a figure-eight or crossing lanes, a new one every 7 s, round a middle that follows their target -- slowed (x0.6) in some moves but never stopped. A rider running into you tramples you (and shoves you out of its way). **(mine)** They ride through the court's columns (radiant, not solid); the columns stay your cover against their shots.
- **Four phases (100-75-50-25%), a signature added in each**, as drafted:
  1. **Formation charge:** lanes of light (four dotted lines) mark where they'll ride; they take their lanes; then all four charge through together at 24 tiles/s -- a line abreast, a wedge, or a cross from four sides -- trampling and shoving whoever they run through. The lanes shown are exactly the lanes run.
  2. **Light lances:** each rider throws a lance (marked where it'll stick) to a corner of a box round you; they stand as pillars of light (12 s), joined by fences of light that sting and throw you back the way you came. Break a pillar (it has health of its own) and its two fences go.
  3. **The hymn:** they gather close and sing (a gold ring round them): x0.3 damage and healing 0.3% of max HP a second while together, drifting away from you, for 7 s. One is the lead singer (glowing): hurt it enough (1.5% of max HP) and the chord breaks, the lead thrown out; or come within 4 tiles of a rider and it breaks off at you -- the chord breaks too. **(mine, after the first fight test)** the healing halved and the lead easier to break: at 0.6% a second it out-healed a weak hero.
  4. **The four winds:** a cage of lances round you, the four riders at the corners, and the winds blow from each corner in turn (the next one flashes first), pushing you across into the fences; two calm spots (blue rings) where no wind reaches.
- **Moves** (all phases): **carousel** (they circle you, the ring tightening from 14 to 4 tiles over 3.2 s, each throwing light inward; get out through the gaps), **hoof rings** (rings of 10 slow light shots from each rider as they gallop), **halo rain** (8 marked gold circles round you, one on you, then halos strike; twice), **trample** (one rider wheels round, its line shows, then it runs it and rejoins).
- **Its shots and halos pass its own riders.** Beaten (for now: form 2 is M29.5), the riders burst in light and feathers and the quest is won: loot, a rare+ card, the achievement ("break the seven seals and defeat the Serene Cavalry").
- **Numbers** (`CAV_*` in config.py) are first guesses; the bot benchmark comes with form 2 (M29.5). A first fight test (a level-1 wizard standing still, firing): about half its bar in 2 minutes, every move and three phases seen, no errors.

**Code:** `ai/cavalry.py` (Cavalry, Rider), `ai/paradise.LightPillar`, `render/cavalry.py`, art (`fallen_angel`, `white_knight`, `light_pillar`, the `white_horse` mount) in `render/paradise_art.py`; `world/paradise` (seals, the camp and lair), `world/landmarks` (zones' quests skipped), tiles `SEVEN_SEAL`, `SEVEN_SEAL_BROKEN` (212 of 255 map classes); `systems/quests` (kind "seals", guards, waves, the barred lair, pins, guardians, `broken_seals`); `systems/spawner` (bosses keep their own numbers); `scenes/game._sky`; `render/magus.draw_seals`. **Tests:** `tests/test_m29_4.py` (23); `test_m29_1` (the court is the quest's lair now); `test_m17`, `test_p2`, `test_m22_5`, `test_m27` (a zone's quest: pinned once found, exactly seven spots, not a guardian); `test_m28_5` (the cavalry's relics come with M29.5). Full suite 1805 OK after those.

## 12. Built: M29.5 (2026-11-22) -- the Four Horsemen (the relics still to draft)

**The unveiling** (`ai/cavalry.py`): at 0 the Serene Cavalry doesn't fall. Its riders flicker for 2.5 s (they can't be hit, everything it was doing stops, its cages fall) under the banner **THE FOUR HORSEMEN -- the cavalry unveils**, then each rider becomes a Horseman where it was: Conquest, War, Famine, Death (`ai/horsemen.py`), **6,000 health each** (as proposed; scaled like every boss). The boss bar becomes four bars under one ("THE FOUR HORSEMEN"). The cavalry still rides them (always riding: they slow but never stop; only the banner and the duel plant them, with a "!"), and the fight is won when the last one falls ("THE FOUR HORSEMEN ARE DEFEATED").

**When one falls, the others take its power**: its kit (moves and passives) joins each survivor's -- "X FALLS - ITS POWER PASSES ON" -- so the last one standing has all four. Each picks its own kit's moves more often than inherited ones.

**The kits**, as drafted in section 6.2 (numbers mine, `config.py` `CROWN`...`SHADE_LIFE`):
- **Conquest:** **crowning arrows** (an aim line, then 3 gold arrows; a hit crowns you -- a gold crown over your head -- and while crowned your hits do half; a roll knocks it off: "CROWN OFF"); **arrow fans** (passive: 3 arrows every 5 s while it gallops); **banners** (it rides to a spot near you and plants: the banner's burning ground spreads from 2.5 to 7 tiles until it's broken; at most 2 stand -- a third topples the oldest); **victor's lap** (a lap round you at full speed, 2 arrows every 0.8 s aimed inward and ahead: the safe lane is right behind it).
- **War:** **sweeping blade** (three wide 120-degree slashes, each shown first, each sending a fan of blood rolling on); **blood charge** (a shown line, a charge, a turn -- up to three -- leaving burning blood); **strife** (passive: 3 unveiled angels into the court every 18 s, at most 6 of them about); **duel ring** (it plants its sword; a ring of blood closes round you both; inside, you both deal double damage for 8 s; step out and it stings, and the duel's over -- "DUEL!", "BROKE OUT!").
- **Famine:** **the scales** (passive, every 8 s: see below); **hunger** (passive: no healing within 8 tiles of it -- a dark ring round it, a struck "+" over you); **weights** (3 black weights marked 1.2 s, crushing where they land and staying as solid iron blocks, breakable); **locust plague** (6 unveiled locusts from its saddlebags, at most 18 about).
- **Death:** **Hades follows** (passive: a dark maw rides behind it; pools of darkness trail it for 6 s: inside you can't heal and you're pulled toward the middle); **a fourth of the earth** (four quarters round you, one at a time darkened for 2 s, then struck); **reaping** (3 s of a spinning scythe, hitting what it sweeps, a fan of crescents off every half-turn); **the dead rise** (passive: anything slain in the court rises once as a pale shade for 10 s, at most 6 at once; a fallen Horseman rises as a pale rider while any survivor has the power).

**The scales -- a call to check.** Section 6.2 says "whoever has more health, as a share of max, loses some to the other -- keep it hurt and you're safe": the two halves contradict (if the one with more loses, keeping it hurt makes *you* lose). Built as the second half says: **the lighter one (less health as a share) loses 3% of its own max to the other**, who gains just that. Keep Famine's share below yours and it bleeds (and you heal -- unless you're inside its hunger); let it get ahead of you and you bleed. Flip it in `Horseman._weigh` (one comparison) if the first half was meant. (My first try had the winner gain 8% of its own max: Famine out-healed the bot for 20 minutes.)

**The bot benchmark** (rebuilt: a level-1 wizard that can't die, circle-strafing at 8 tiles, firing at adds within 6 tiles first, else the nearest rider/Horseman; held at 60% health so the scales can tip either way; seeds 31/7/12):

| | Cavalry | Horsemen | Both | Damage taken a minute |
|-|---------|----------|------|-----------------------|
| Seed 31 | 4:52 | 7:20 | 12:12 | 895 / 1,029 |
| Seed 7 | 4:55 | 6:59 | 11:54 | 868 / 1,276 |
| Seed 12 | 4:56 | 7:41 | 12:37 | 780 / 1,540 |
| More than Life + Death (reference) | | | 7:30 | 727 |

Above the necromancer on both counts, as tier III should be. Longer than my targets (~3 and ~5 min), but by policy no health is cut on bot numbers alone. **What I lowered instead** (first run: 1,086 and ~2,700 damage a minute, the Horsemen never finished): trampling 12 -> 8 every 1.2 s; the carousel's light every 0.7 s; halo damage 14; arrow fans 3 every 5 s; the lap's volleys 2 every 0.8 s; banners capped at 2; strife every 18 s, 6 at most; at most 6 shades, slower and weaker; weights 3 of 22, marked 1.2 s, Famine resting longer between moves; the scales as above. The bot never steps out of a marked area, so weights, quarters and halos hurt it far more than a player.

**Look:** the four (`render/paradise_art.py`): Conquest crowned with a bow on the white horse, War in red armour with a great sword on the red, Famine hooded in black holding the scales on the black, Death a pale skull with a scythe on the pale -- the riders covered in eyes, the horses flayed and bleeding (red mixed into their shading). Hades: a dark maw drawn behind Death. Pale shades and pale riders, Conquest's banner. Tells: `render/horsemen.py`.

**Code:** `ai/horsemen.py` (Horseman and its 16 abilities, ConquestBanner, PaleShade), `ai/cavalry.py` (form 2: the unveiling, riding the four, strife, the dead rising, inheritance; its health the four's), `render/horsemen.py`; the crown and the duel in `systems/combat.strike`, a shot's `on_hit` (`entities/projectile`, `combat._hit_actor`), the roll knocking the crown off (`systems/roll.start`), no healing while starved (`Character.heal`), the HUD's four bars (`ui/hud`), tile `WEIGHT` (213 of 255 map classes), zones `hades`, `blood_fire`. **Tests:** `tests/test_m29_5.py` (22); `test_m29_4`'s whole-quest test now finishes the Horsemen too; `test_m28_5` counts the four Horsemen as the cavalry's (they drop its relics). Full suite 1826 OK (after renaming three numbers that clashed with older ones: `HM_DUEL`, `HM_PLAGUE`, `HM_REAP`). The bench: scratchpad `bench.py` (`BENCH_QUEST`, `BENCH_MIN`, `BENCH_HP`).

**Still to do for M29.5: the relics** -- one per Horseman (section 6.3), drafted with the user. Until then `test_m28_5` exempts the cavalry from "every boss has its relics".
