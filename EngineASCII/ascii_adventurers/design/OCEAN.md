# AsciiAdventurers — The Ocean Zones

Status: **rev 0 — M29 (Paradise) DRAFTED with the user, 2026-11-21. M29.1 BUILT (2026-11-21, section 8). M29.2 BUILT (2026-11-21, section 9). M29.3 BUILT (2026-11-21, section 10). M29.4 BUILT (2026-11-22, section 11). M29.5 BUILT (2026-11-22, section 12). M29 (Paradise) COMPLETE. M30 (Pandemonium, the south) DRAFTED 2026-11-22 (sections 13-18). M30.1 BUILT (2026-11-22, section 19). M30.2 BUILT (2026-11-23, section 20). M30.3 BUILT (2026-11-23, section 21). M30.4 BUILT (2026-11-23, section 22). M30.5 BUILT (2026-11-23, section 23: the hunger and his relics). M30 (Pandemonium) COMPLETE. M31 (Pangaea, the west) DRAFTED 2026-11-23 (sections 24-29). M31.1 BUILT (2026-11-23, section 30). M31.2 BUILT (2026-11-24, section 31).** These are M29-M32 in `BOSSES.md` section 8. The user may change anything here after playing it ("leave the design docs so I can change them later after testing"). Picks are the user's unless marked **(mine)**: routine calls made where the user said nothing, open to change.

---

## 1. The four zones (user)

Four islands out in the ocean, reached by **water walking** (Adventurer's Glory, M27). **Fixed places, not shuffled:**

| Place | Zone | The idea (user's words, condensed) |
|-------|------|-----------------------------------|
| **North** | **Paradise** (heaven) | A white, heaven-like island with a twist: "biblically accurate" horror angels and Bible-inspired monsters that look pretty at first and turn into extremely bloody monsters. Blood is a big theme; **white and red** are the colours. **M29.** |
| **South** | **Pandemonium** (hell) | Hell twisted toward excess: the humans there aren't tortured, all their pleasures are indulged (the opposite of the torturous heaven), but the trance makes them mad, so they're still aggressive. **Revellers in groups:** they feast, drink and dance lost in the trance, ignore you until you come close or hit one, then the whole group frenzies. Kept to feasts, wine, music, dance, gold and vanity, with our own names. **M30** (section 13 on). |
| **West** | **Pangaea** (the past) | **Deep time:** a primeval island from before people's history: giant ferns, tar pits, a smoking volcano, amber; great mammals, dinosaurs, giant insects and a tribe of early hunters. **Its twist: echoes:** every attack repeats a few seconds later. **M31** (section 24 on). |
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
| M29.5 | **Form 2:** the Four Horsemen (16 abilities), inheritance, the bot benchmark; then the 4 relics drafted with the user. **Built, section 12** |

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

## 12. Built: M29.5 (2026-11-22) -- the Four Horsemen and their relics

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

**The relics** (drafted with the user, 2026-11-22: the recommended one of three for each Horseman; GEAR.md 21.1's rules -- legendary only, the power +10% a level, one dropped once a run per player when the Horsemen fall):

| Horseman | Relic | Slot | Power (at +0) |
|----------|-------|------|---------------|
| Conquest | **Crown of Conquest** | head | your hits crown enemies: a crowned enemy deals half damage for 4 s (bosses 25% less), once per enemy every 8 s (a gold crown shows over it) |
| War | **Ring of Blood** | ring | every 20 s, a ring of blood closes round you and the nearest elite or boss (within 10 tiles) for 6 s: inside it you both deal double damage (step out and it's over) |
| Famine | **The Black Scales** | trinket | every 8 s, weighs you against the nearest enemy (within 10 tiles): whichever has less health as a share of max loses 3% of its max to the other (a boss 0.5%) |
| Death | **Pale Rider's Cloak** | chest | enemies you kill rise once as pale shades that fight for you (15 a bite) for 6 s, at most 3 at a time |

On the gear (16 letters at most) they're "Conquest's Crown" and "Pale Rider Cloak", like the Crown of Black Ice's "Black Ice Crown". The power that grows is the crown's time, the ring's time, the scales' share and the shades' time. Looks (M28.6): the crown gold with a red stone, the cloak pale. Affixes: Crown -- brutal, keen eye, lingering; Ring -- sharpened, vampiric, brutal; Scales -- second wind, potency, lucky charm; Cloak -- thick hide, iron skin, second wind. Code: `systems/relics.py` (`_blood_ring`, `_black_scales`, `_pale_shades`, `on_kill`), `combat._relic_on_hit` and `combat.strike` (the crown; the Ring of Blood's duel shares War's: x2 both ways), config `U_CONQUEST`, `U_BLOOD_RING`, `U_SCALES`, `U_PALE`. 42 boss uniques now.

**M29 (Paradise) is complete. NEXT: M30, Hell** (the south zone; the Slaanesh-like revellers in groups, drafted with the user first).

---

## 13. Pandemonium (south): the land (user, M30 round 1, 2026-11-22)

**Name: PANDEMONIUM** (Milton's capital of Hell, *Paradise Lost*: public domain; it pairs with Paradise). **(mine)** The arrival banner: "where the feast never ends".

**Look: black and gold.** Polished black obsidian ground veined with gold, gold-leaf terraces, crimson velvet awnings and banners, braziers and lanterns everywhere. **The shore is a beach of gold coins** sliding into a dark, wine-red sea (instead of Paradise's cloud bank). The dark mirror of Paradise's white and red; it stays clear of the mushroom biome's purple and the desert's sandy gold.

**The excess on the land (all four)** -- the counterpart of Paradise's blood:
- **Wine fountains and a river of wine:** gilded fountains of wine; frenzied revellers run to them to drink and heal, so you fight them away from the fountains (**(mine)** like Paradise's fonts: under 40% HP, a fountain within 30 tiles). A **river of wine** runs from the wine press down the terraces into a wine lake round the palace (round 2).
- **Banquet tables:** long tables heaped with food all over the island, each with a group of revellers feasting at it -- that's where the groups are. Tables you knock over spill food and drink.
- **Gold and vanity statues:** heaps of coins, and gilded statues of the revellers admiring their own faces. Some statues are revellers frozen mid-pose, who wake with their group.
- **Music that carries:** bandstands of endless players. The music feeds the trance: near a stage, revellers notice you later, but once a group there frenzies, the song carries the frenzy to the groups nearby.

**Landmarks (all four):**
- **The gilded pier:** on the shore facing the main island, a long golden jetty with pleasure barges moored, lanterns and a welcome arch: where you arrive (Paradise's Gate).
- **The endless banquet hall:** a roofless hall with one table running its whole length and revellers along both sides, a feast that never ends.
- **The hall of mirrors:** a ballroom of mirrors and chandeliers where dancers whirl forever; the mirrors show the dancers (and you) many times over.
- **The wine press:** terraced vineyards round a giant press and its vats; the river of wine starts here.

**The shape (round 2): terraces down into a pit.** Paradise climbs; Pandemonium sinks. Gold-leaf terraces step down to **the boss's palace at the bottom of the pit**. The river of wine starts at the wine press near the rim and runs down the terraces into **a wine lake round the palace**.

## 14. Pandemonium: the trance (user, M30 round 2)

**Who lives there:** mostly **human revellers in groups** (feasters, drinkers, dancers, musicians, the vain), plus **demon hosts** who serve them (cupbearers, carvers, a master of revels). The hosts are **never in the trance**: always alert, they guard the groups. **(mine)** 16 enemies, like Paradise.

**The frenzy is one-way.** A group in its trance feasts, drinks and dances and ignores you until you come close or hit one of them. Then **the whole group turns at once** after a short tell (they freeze, heads snap toward you, **(mine)** ~0.6 s) and **stays frenzied until it dies**: faster, harder hits, chasing you. The skill is choosing which group to wake, and where (away from the fountains and bandstands). **(mine)** "Close" = 6 tiles from any member (Paradise's unveiling is 5); near a bandstand it's half that, and a frenzy at a bandstand spreads to every group within 25 tiles of it (section 13's music).

**Temptation: the trance reaches you too.** Standing near feasts, bandstands or fountains fills a **TMP meter** on the HUD (like the Fallout King's rads and the Snow King's chill). **Full, you're entranced for ~2 s**: you drift toward the nearest table or stage and can't attack; **a roll snaps you out**. Fighting and moving on drain it. **(mine)** Fills within 8 tiles of a table, bandstand or fountain (faster the closer, ~6 s from empty when right next to one); drains in ~3 s once you're clear, and twice as fast while you're hitting something.

## 15. Pandemonium: the enemies (all 16 picked, M30 round 3)

Revellers are in the trance until their group frenzies (section 14); the demon hosts are always alert.

| Group | Enemy | In the trance | Frenzied |
|-------|-------|---------------|----------|
| Feasters and drinkers | **Glutton** | stuffing itself at the table | lumbers after you, belly-slams a shockwave ring; stops to gorge at any table it passes and heals |
| | **Drunkard** | swaying with a goblet | staggers in a weaving, hard-to-predict walk; hurls bottles that shatter into wine puddles (slow you, fill your temptation) |
| | **Toastmaster** (elite) | on its feet, goblet raised | calls toasts: each gives every frenzied reveller nearby a burst of speed and splashes a wave of wine outward. Kill it first |
| | **The Ravenous** | gaunt guests who eat and are never full | sprint in and latch onto you, biting and slowing you until a roll shakes them off |
| Dancers and musicians | **Dancer** | twirling in pairs | whirls along curving dance-step paths, slashing with ribbon blades; the steps repeat, so the pattern can be read |
| | **Masked Dancer** | a masquerade guest | swaps places with other dancers in a flash (you lose track of who's who), then stabs from where it lands |
| | **Drummer** | drumming on a bandstand | every beat sends a shockwave ring out on a steady rhythm; roll through on the beat |
| | **Piper** (elite) | leads the bandstand's tune | its song fills your temptation fast in a cone, and every few seconds it plays the frenzy on to the next group in range. Silence it or the whole quarter wakes |
| The vain and the greedy | **The Vain** | admiring itself in a hand mirror | flashes the mirror: a blinding cone (marked first) that also turns your shots back at you |
| | **Gilded Reveller** | looks exactly like a vanity statue | wakes with its group in a gold shell that soaks hits until it cracks off; slow, heavy slams |
| | **Hoarder** | sitting on a coin heap, counting | throws fistfuls of coins in shotgun spreads; the coins stay on the floor and trip you (a short stumble) |
| | **The Beloved** (elite) | the centre of its group's admiration | its admirers orbit it as a living shield and take its hits; while it lives its group is faster. Break the ring to reach it |
| Demon hosts (always alert) | **Cupbearer** | -- | carries wine jugs round the groups: refills frenzied revellers (heals them), throws wine at you that fills your temptation. A priority target |
| | **Carver** | -- | a butcher-chef demon: lunging cleaves; spinning cleavers thrown out that curve back to it |
| | **Bouncer** | -- | a huge doorman demon guarding a group: shoulder charges along a shown line; if it catches you it throws you toward the nearest group (waking it) |
| | **Master of Revels** (elite) | -- | rings a hand bell: every group within range frenzies at once; calls fireworks onto marked circles. Its bell also ends your temptation trance (an opening) |

## 16. Pandemonium: the quest (user, M30 round 4)

**Silence the seven bandstands.** Seven bandstands carry the music that holds the trance (**(mine)** out from the start, every one counts, quest taken or not, like the seven seals). **Smash each one's instruments: stand at it ~8 s** while its group, and any group the song reaches, frenzies at you (**(mine)** the seals' survive-circle code: leave the circle and the smashing pauses). **Each silenced stage thins the music:** the island gets quieter and **your temptation fills slower** (**(mine)** 10% slower per silenced stage). **The seventh silence wakes the host of the feast in a rage.**

**The giver: the sober man.** The only reveller who ever woke up: haggard and starving in the middle of plenty (the food turns to ash in his mouth), hiding under the gilded pier. He wants it to end, and he's the only one who tells you what the feast really is: the mirror of Paradise's fallen angel.

## 17. Pandemonium: the boss -- THE HOST OF THE FEAST (user, M30 round 5)

**Who:** a vast demon prince, gracious and smiling, who throws the endless party. Every attack is hospitality: courses served, wine poured, toasts, dances. Under the charm is a hunger that eats the guests.

**Arena: a hall that changes.** The palace's great hall at the bottom of the pit turns into a new room each phase: **the banquet** (a long table down the middle), **the ballroom** (a dance floor that lights up in steps, mirrors on the walls), then **the vault** (heaps of shifting gold). The wine lake rings it all. Sealed until the seventh silence.

**Two forms** (like the Horsemen and the necromancer), each a full kit: **the gracious host**, then at 0 **the hunger**: the mask cracks, the table collapses, and he becomes a devouring thing that eats the feast and the guests to grow.

**Movement: he dances.** Always moving: he waltzes round the hall the whole fight, and his moves are dance figures (spins, glides, a partner he sweeps along). Only a few moves plant him, with a clear tell.

### 17.1 Form 1: the gracious host (user, M30 round 6)

**Phases = rooms:** the banquet, the ballroom, the vault (**(mine)** 100-67-33-0%: the hall changes at each threshold). One signature comes with each room and keeps going in the rooms after it; **Toasts** (the fourth pick) plays in every room.

**Signatures (all four):**
1. **Courses served** (from the banquet): he sends dishes sliding down the table and across the floor, each a hazard read by its look: **soup** (a spreading scald pool), **the roast** (bursts into a ring of bones), **jellies** (bouncing blobs), **the cake tower** (topples along a line). In the later rooms demon waiters bring them in.
2. **The dance floor** (from the ballroom): the tiles light a step pattern a beat ahead; when the beat lands, every unlit tile burns. Follow the steps while he waltzes across the floor.
3. **The vault's gold** (the vault): heaps of gold slide across the floor like walls closing lanes; coins pour from the ceiling onto marked circles. He tosses you gold too: **catch a coin for a burst of damage, but each one fills your temptation.**
4. **Toasts** (every room): he raises his glass and the hall toasts: a wave of wine floods out from him (roll through it), and every guest in the hall frenzies.

**Moves (all four dance figures):** **grand spin** (a long spinning glide, a ring of cutlery flung each turn), **the beckoning** (he bows and beckons: you're pulled toward him for a second -- walk or roll against it -- then a sweeping slash in a cone), **carving set** (carving knives fanned in arcs that cross; the gaps are where they cross), **chandeliers** (dropped onto marked spots, leaving broken glass that cuts for a few seconds).

**His charm pulls:** within ~6 tiles of him your **temptation fills**. Full, you're **swept into his dance for ~2 s**: you drift toward him and he gets a free hit unless you roll out. Fight from range or keep stepping out.

**Guests in each room:** a group at the room's edges, in the trance -- **feasters** in the banquet, **dancers** in the ballroom, **hoarders** in the vault. They wake if you go near them, or when his toast frenzies the hall. **(mine)** Each room's group leaves with the room (the hall changes), and a new one sits down.

### 17.2 Form 2: the hunger (user, M30 round 7)

At 0 the mask cracks, the table collapses, and he becomes a devouring thing that eats the feast and the guests to grow.

**Arena: the hall falls into the wine.** At the change the floor breaks up into **islands of table, floor and gold in the wine lake**. He moves through the wine freely; you wade it slowly, so you fight from island to island.

**Signatures (all four), one added per phase** (**(mine)** four phases, 100-75-50-25-0%, as with the Serene Cavalry):
1. **Devour:** he eats whatever he reaches -- guests, dishes, his own servants. Each meal heals him and makes him **bigger and stronger** (a growth count shows on his bar). Kill the guests and clear the food before he gets there.
2. **The maw:** he opens his maw and inhales: a strong pull across a cone (shown first). Caught, you're swallowed: heavy damage, then spat out across the hall.
3. **Teeth in the floor:** the broken hall grows mouths: rows of teeth burst up and snap shut along lines he marks first; the lines cross and change.
4. **Spilled feast:** he heaves up half-eaten feast in long arcs; it lands as rotting pools that slow and burn, and spreads the guests' frenzy to anything near.

**Moves (all four):** **lunge bite** (a fast lunge along a marked line, ending in a bite), **tongue lash** (a long tongue grabs you and drags you toward his mouth unless you roll free), **belly quake** (shockwave rings rolling out across the hall), **bone scraps** (the bones of his meals flung in fans; they stay on the floor as clutter you trip over).

**The charm breaks:** no temptation from him in the second form; the danger is his hunger and growth. (His spilled feast can still fill it.)

### 17.3 Numbers (mine, to tune with the bot and then in play)

- Tier III, like the Horsemen (the cavalry 12,000, each Horseman 6,000). **Proposed:** the gracious host **12,000**; the hunger **14,000**, growing with every meal (**(mine)** each meal +3% of his max back and +5% size and damage, up to 10 meals). All scaled like every boss. Policy: no HP cut below these on bot numbers alone.
- Target length (bot): the gracious host ~3 min, the hunger ~5 min.
- Relics: like every boss, uniques drafted with the user once he's built (GEAR.md 21.1); **(mine)** one per pleasure he plays on is the obvious set (feast, wine, dance, gold).

## 18. M30 build plan (mine; each step: tests, a headless screenshot, a report, a stop)

| Step | Content |
|------|---------|
| M30.1 | **Pandemonium's land:** the south zone (Paradise's framework), black obsidian and gold, gold-leaf terraces stepping down into the pit, the coin beach and the wine-red sea, the river of wine and the wine lake, the fountains, banquet tables (where the groups sit), coin heaps and vanity statues, the seven bandstands, the four landmarks (gilded pier, endless banquet hall, hall of mirrors, wine press), the palace hall (sealed shell), the HUD name and banner |
| M30.2 | **The trance + the first 8 enemies:** groups in the trance, the one-way frenzy and its tell, bandstands spreading it, the temptation meter (TMP, the entrancement, a roll breaks it), fountains healing, endgame toughness; Glutton, Drunkard, Toastmaster, the Ravenous, Dancer, Masked Dancer, Drummer, Piper |
| M30.3 | **The other 8:** the Vain, Gilded Reveller, Hoarder, the Beloved, Cupbearer, Carver, Bouncer, Master of Revels |
| M30.4 | **The quest + form 1:** silencing the bandstands (the island quieting, temptation slower), the sober man, waking and sealing the hall; the gracious host (three rooms, four signatures, four moves, his charm, the guests) |
| M30.5 | **Form 2:** the hunger (the hall in the wine, devour and growth, the maw, teeth in the floor, spilled feast, four moves), the bot benchmark; then the relics drafted with the user. **Built, section 23** |

## 19. Built: M30.1 (2026-11-22) -- Pandemonium's land

**The zone:** `config.OCEAN_ZONES` is now Paradise and Pandemonium (the zone key `pandemonium`, south; it was `hell` in `ZONE_PLACES` until now). Over five seeds it sits 3,000-3,350 tiles south. Everything else is M29.1's framework: hidden until found, the arrival banner **PANDEMONIUM -- "where the feast never ends"**, F3 in dev mode now jumps to each zone in turn. Each zone has its own shore band out at sea (`Zone.shore_band`: Paradise's cloud bank, Pandemonium's wine-dark sea), and `zones.plan_of` builds each zone's own plan.

**The land** (`world/pandemonium.py`, a `Plan` per seed, ~50 ms), as drafted, plus these calls of mine:
- **The pit:** the palace's great hall at the centre is an oval of 76 x 50 tiles (Paradise's court is 92 x 62), walled in black marble trimmed with gold, its gilded gate (7 wide) facing the pier; inside, polished black floor, a gilded band along the wall, a crimson carpet from the gate to **the host's seat** at the far side. Kind "court" until M30.4 makes it the quest's lair (as Paradise's was). The **wine lake** rings it, 14 tiles wide. **Five gold-leaf terrace edges** step up out of the pit, 22, 48, 80, 118 and 160 tiles out from the wall (Paradise's three are close round the court; Pandemonium's span most of the island, so it reads as a pit), the stone darker below the second.
- **The avenues:** the avenue from the pier's plaza meanders down to the hall's gate, with **gold stairs** where it crosses each terrace edge and **a causeway** (gilded bridge) over the lake; a ring avenue just outside the third terrace; spurs to the banquet hall, the hall of mirrors, the wine press and every bandstand; **lanterns** along all of them (Paradise's gold posts), none over the lake.
- **The wine press** stands near the rim (past the outermost terrace, off to a side of the pier): vineyard rows (breakable: vine stakes), its yard, the press, four vats of wine. **The river of wine** runs from its spout toward the pit and into the lake.
- **The gilded pier:** a plaza at its root (braziers at the corners), a welcome arch of gold with crimson banners, a jetty 35 tiles out over the sea with lanterns, a landing at its end, and three gilded barges moored alongside.
- **The endless banquet hall** (66 x 18): a roofless black-marble hall, doors at both ends and two on each side, one table running its whole length heaped with food, crimson carpets along both sides, braziers along the walls. **The hall of mirrors** (42 x 24): walls of mirrors, a gilded band inside them, a black ballroom floor under rows of chandeliers, doors at both ends.
- **Seven bandstands** (at least 60 tiles apart, like the seals): a round crimson stage, drums and harps in the middle (breakable: M30.4 smashes them), lanterns round it. **22 banquet tables** (a table heaped with food on a crimson carpet, braziers at two corners: where the revellers' groups will sit, M30.2), **10 wine fountains**, **16 gilded statues** on plinths (breakable: they're loose coins inside).
- **Ground:** black obsidian with sparse glints; thin gold veins where the detail field crosses its middle; coin heaps in clumps (low cover, breakable: loose coins) with loose coins round them; lone braziers and crimson banners. The land's last ~4 tiles are a **coin beach**; the sea within 22 tiles turns **wine-dark** (solid for the first half, then thinning), drawn with the ocean's own dither so the water seems to darken into wine. Wine, wine fountains and the wine-dark sea are watery: water walkers cross them.
- **Tables break into a spilled feast** (they stop you, not shots).
- **No enemies yet** (`BIOME_ENEMY_DENSITY` has no "pandemonium"): M30.2.

**Also fixed (found while adding the colours):** names defined twice at module level silently replace the first everywhere. Since M29.1, Paradise's `STATUE`, `THRONE` and `COLUMN` had replaced the Snow King's frozen statues and ice throne and the Magus observatory's columns (which had become breakable marble columns), and Paradise's blood, statue and column colours had replaced the older ones. Older duplicates too: the basilisk and Fragile drew in the Watcher's gaze colours, and the relics' roots in the rootweaver's. Each now has its own name (`MARBLE_COLUMN`, `GOLD_THRONE`, `CHOIR_STATUE`, `PARADISE_BLOOD_*`, `FRAGILE_GAZE`, `WATCHER_GAZE`, `ROOTBOUND`...); two dead first definitions (`RUNE`'s purple, `SHOT_SAND`) were removed, so their looks don't change. `tests/test_m30_1.DefinedOnceTest` now fails on any name defined twice in `palette.py` or `world/tiles.py` (config already had one).

**The explored map is 16-bit now** (2 bytes a tile, ~2 KB a chunk): with Pandemonium there are 254 map classes, one short of 8 bits' 255 (M30.2's enemies' stains and spills, the Past and the Future will add more).

**Code:** `world/pandemonium.py`; `world/zones.py` (`plan_of`, `shore_band`); `world/layout.py` (the shore band); `world/generator` (`_pandemonium`, 15 tiles); `world/landmarks` (each zone's own plan); `world/biomes.PANDEMONIUM` (id 8); `world/tiles.py` (38 new) and `palette.py`; `world/explored.py` (16-bit); `systems/collision.WATERY`; `scenes/game._dev_zone`. **Tests:** `tests/test_m30_1.py` (25); `test_m29_1` (only E and W stay open sea now), `test_m17` and `test_p2` leave the new zone out like M29.1's tests did.

## 20. Built: M30.2 (2026-11-23) -- the trance, temptation and the first eight revellers

**Where they live** (`ai/pandemonium.residents`, rostered with their chunks like Paradise's choristers; never rolled at random, so `BIOME_ENEMY_DENSITY` has no "pandemonium"). **(mine)** 4-6 feasters and drinkers seated round each banquet table (glutton, drunkard, ravenous by weight; a toastmaster at every third table); at each bandstand its band on the stage -- the piper in front, two drummers behind the drums, two pairs of dancers and a masked dancer round them; 7 guests along each side of the endless banquet's table, one of them a toastmaster; three pairs of dancers and two masked dancers in the hall of mirrors. About 190 on the island; only those near a player are awake.

**The trance** (`Reveller`, built on Paradise's unveiling: in the trance = serene, frenzied = unveiled). As drafted, with my numbers from section 14: a group wakes when a hero comes within 6 tiles of any of them -- 3 where the music plays (a bandstand's group, and any group within 25 tiles of a bandstand) -- or anyone hits one (killing one in the trance counts); they all freeze and flicker for 0.6 s with the red "!", then come at full speed, for good (the frenzy is remembered per group, so a group you left frenzied is still frenzied when you come back). A bandstand group's frenzy carries to every group within 25 tiles. In the trance they move at x0.35 (dancers twirl, the rest sit). Frenzied and under 40% they drink at the nearest wine fountain within 30 tiles (Paradise's `FONT` numbers).

**Temptation** (`systems/temptation.py`; the TMP meter on the HUD, after RAD and CHL): it fills within 8 tiles of a banquet table, a bandstand, a wine fountain or the endless banquet's table (6 s from empty right beside one), drains in 3 s clear of them (twice as fast within half a second of hitting something). Full: **ENTRANCED!** for 2 s -- sparkles round the hero, no attacks, drifting toward the nearest lure at x0.55; **a roll snaps you out**. Drunkards' wine puddles, toasts' waves and the piper's song add to it. The Mender's Totem's cleansing light clears it.

**The eight** (numbers in `config.py`: `GLUTTON`, `DRUNKARD`, `TOAST`, `RAVENOUS`, `DANCE_STEPS`, `MASKED`, `BEAT`, `PIPER`; base HP before the zone's x2.5):

| Enemy | Frenzied |
|-------|----------|
| **Glutton** (150) | lumbers after you; within 3.2 tiles it winds up 0.6 s and belly-slams a ring out 5.5 tiles; under 85%, passing within 2.5 tiles of a banquet table, it gorges 1.2 s (heals 12% of its max; then not for 6 s) |
| **Drunkard** (70) | weaves 1.3 tiles either side (with a stagger on top), keeping 4-8 tiles off; lobs a bottle every 2.2 s (where it'll land shows): it hurts where it lands and leaves a wine puddle (1.4 tiles, 6 s) that slows to x0.6 and tempts |
| **Toastmaster** (elite, 300) | keeps 6-9 back; every 5 s raises its goblet (0.8 s) -- **A TOAST!**: every frenzied reveller within 10 tiles is x1.5 as fast for 3 s, and a wave of wine rolls out 7 tiles (hurts and tempts) |
| **The Ravenous** (45) | sprints at 7.2 tiles/s and latches on (at most 3 on a hero): bites every 0.6 s and slows you to x0.65; a roll throws them off 2.5 tiles, dazed 1.2 s (**SHAKEN OFF!**) |
| **Dancer** (60) | its steps repeat: circling you 3.2 tiles out one way (1.1 s), a dash through you (its line shows 0.4 s), circling back the other way, a dash; its ribbons cut whoever it touches |
| **Masked dancer** (65) | every 3.5 s swaps places with another dancer within 14 tiles (its own group's first) in a white flash -- with none near, it flashes to just past you -- then stabs (its line shows 0.35 s) 3 tiles |
| **Band drummer** (90) | never leaves its drums; every 1.25 s a ring goes out 8 tiles at 12 tiles/s (**roll through it**: mid-roll it can't touch you) |
| **Piper** (elite, 280) | keeps 6-10 back; plays 2.5 s, rests 2 s: a 60-degree cone 9 tiles long, following you slowly, fills temptation 30 a second (a fan of notes); every 6 s it plays the frenzy on to the nearest group still in the trance within 25 tiles (**THE SONG CARRIES**) |

**Look** (`render/pandemonium_art.py`, two pictures each): the glutton in a crimson coat with a drumstick, the drunkard in purple velvet with a goblet, the toastmaster in a black tailcoat raising a gold goblet, the Ravenous gaunt and grey, the dancer in a pink gown, the masked dancer in a gold mask and dark gown, the drummer behind a gold-rimmed drum, the piper in green with a long gold pipe; frenzied, red eyes, open mouths and wine stains, the blades, the dagger and the bottle out. Effects: the turn (a ring of "!" and gold), a death (wine and feast spilling), the three rings (`belly_slam`, `beat`, `wine_wave`: they last reach / speed, so the ring drawn is where it hits), the masked dancer's flash; the wine puddle. Tells (`render/pandemonium.py`): bottles in the air, the dash and stab lines, the piper's notes, drinking and gorging.

**Measured:** with 24 revellers awake (the endless banquet's guests and a table), a game step takes 0.65 ms in the trance and 1.0 ms frenzied; drawing 2.1 ms.

**Code:** `ai/pandemonium.py` (sites, fountains, lures, frenzy, wake_reach, residents, home_of; `Reveller` and the eight); `systems/temptation.py`; `ai/paradise.Angel.find_font` (a hook: revellers drink at the wine fountains); `systems/zones.Zone.tempt`; `systems/spawner` (each zone's residents); `entities/character` (`temptation`, `entranced`, `struck_at`); `systems/combat.strike` (`struck_at`); `scenes/game` (the step, no attacks entranced, the TMP meter, the sparkles); effects and their drawing; config `REVEL*`, `TEMPT` and the eight's tuples (`DANCE_STEPS`: `DANCER` was the fire dancer's); bestiary pages. **Tests:** `tests/test_m30_2.py` (22); `test_m30_1`'s "no enemies yet" now checks the residents. Full suite 1859 OK.

**For later:** every number wants a play test, especially the temptation's pace and the bandstands' spreading (a frenzied piper can wake a whole quarter). M30.3 adds the other eight: the vain and the greedy, and the demon hosts (who are never in the trance).

## 21. Built: M30.3 (2026-11-23) -- the other eight: the vain, the greedy and the demon hosts

**Where they live** (my calls; the doc says the hosts "guard the groups", so none roam): the **gilded statues are the vain's and the greedy's homes** -- each statue's plinth grew to 7 x 5 for them. At most statues a Vain admires it and a hoarder counts coins; at every second a gilded reveller poses beside it as a second statue; at every fourth (the first included) the Beloved stands there instead, admired by three of the Vain. The hall of mirrors has a Beloved too, with three admirers. The **demon hosts are posted by the groups**: a cupbearer at every second banquet table, a carver at every third, a bouncer at every fourth; a master of revels at every second bandstand; a bouncer by the endless banquet's west door and two carvers inside; a bouncer in the hall of mirrors. Hosts are **never in the trance**: alert from the start, they come for you on sight, and go back to their posts when you're gone; they don't drink at the fountains.

| Enemy | Base HP | In the trance | Frenzied / on sight |
|-------|---------|---------------|---------------------|
| **The Vain** | 70 | admiring itself in a hand mirror | keeps 5-8 back; every 4 s its mirror's cone (50 degrees, 8 tiles) is marked for 0.8 s, then flashes: whoever's in it is **DAZZLED!** 2 s (your aim wavers up to 0.5 rad), and your shots in it turn back at you at x0.6 damage. With its Beloved alive it circles it instead |
| **Gilded reveller** | 140 | looks exactly like a gilded statue | a gold shell of 60% of its max HP soaks every hit until it cracks off (a shower of gold flakes; then it moves x1.6); within 2.2 tiles a 0.7 s windup and a heavy slam ring 2.8 tiles out |
| **Hoarder** | 75 | counting coins | keeps 4-7 back; every 2.4 s a fistful of 5 coins thrown in a 50-degree spread: each hurts where it lands and the coins lie there 7 s -- step on them and you stumble (x0.15 for a moment) |
| **The Beloved** (elite) | 260 | the centre of admiration | its admirers (its group's Vain) circle it 2.2 tiles out, and while one is within 4 tiles **it takes the Beloved's hits**; while it lives its whole group moves x1.25; a fan of 5 glitter shots every 3.5 s |
| **Cupbearer** (host) | 90 | -- | goes to a frenzied reveller within 10 tiles under 75% and pours for 1 s, healing it 30% of its max (then not for 4 s); otherwise keeps 5-8 back and throws wine (hurts, +20 temptation) |
| **Carver** (host) | 130 | -- | within 3.5 tiles a lunging cleave (its line shows); otherwise a cleaver that flies out 0.8 s curving, then comes back to its hand, cutting whoever it passes both ways |
| **Bouncer** (host) | 240 | -- | within 12 tiles a shoulder charge along a shown line (10 tiles at 14 tiles/s); caught, you're hurt and **THROWN!** 6 tiles toward the nearest group still in the trance; a wall dazes it 0.6 s |
| **Master of Revels** (elite host) | 320 | -- | rings its bell (a 1 s tell, then every 10 s): **every group within 22 tiles frenzies, and every entranced hero there snaps out** (the opening); keeps 7-10 back; fireworks: 3 circles marked 1.2 s (one right on you), then they burst |

**Look** (`render/pandemonium_art.py`): the Vain a dandy in pink velvet with a hand mirror (frenzied, the mirror flashing); the gilded reveller a gold statue-figure, then a moving gold shell, then flesh under flakes of gold; the hoarder hunched over a heap of coins, then up with a fistful; the Beloved radiant in white and gold with a gold laurel crown; the hosts red demons with horns and black eyes (one picture each) -- the cupbearer with a wine jug, the carver in a butcher's apron with a cleaver, the bouncer huge in a black suit, the master of revels a ringmaster in a top hat and red coat with a gold bell. Effects: the mirror's flash (a cone of light), the gold shell cracking, the gilded slam's and the bell's rings, fireworks; zone `loose_coins`; tells: the Vain's cone, the bouncer's and the carver's lines, spinning cleavers, the firework circles, a dazzled hero's white sparkles.

**Measured:** with 28 awake (the endless banquet with its hosts), a game step takes 0.9 ms in the trance (the hosts are always about), 1.2 ms frenzied; drawing 2.5 ms.

**Also fixed:** the Beloved's shot look was first added as `"glitter"`, a key Nettle's shots (M25.1) already had: in a dict literal the second silently replaces the first. It's `"revel_glitter"` now, and an older duplicate came to light the same way (two `"sand"` shot looks; the first, dead since M23.1, is gone, so nothing changes on screen). `test_m30_1.DefinedOnceTest` now fails on any dict literal that repeats a key in config, the palette, the effects, the shot looks or the enemy registry.

**Code:** `ai/pandemonium.py` (`Vain`, `GildedReveller`, `Hoarder`, `Beloved`; `Host` and `Cupbearer`, `Carver`, `Bouncer`, `MasterOfRevels`; the statue sites; `_statues`, `_hosts`); `world/pandemonium.py` (the bigger plinths); `entities/character.dazzled` and its aim wobble in `scenes/game` (the cleansing light clears it); config `VAIN`, `GILDED`, `HOARD`, `BELOVED`, `CUPBEARER`, `CARVER`, `BOUNCER`, `MASTER`, `REVEL_STATUE`, `REVEL_HOSTS`, `PANDEMONIUM_SHOTS`; effects, looks, tells, bestiary pages. **Tests:** `tests/test_m30_3.py` (16); `test_m30_2`'s group counts leave the hosts out. Full suite 1876 OK.

**For later:** play-test the numbers, especially the bell (one master can wake everything within 22 tiles) and the bouncer's throw. All sixteen of Pandemonium's enemies exist now; next is M30.4, the quest (silencing the bandstands, the sober man) and the Host of the Feast's first form.

## 22. Built: M30.4 (2026-11-23) -- silencing the bandstands, the sober man, the palace, the Host of the Feast (form 1)

**The quest** (`config.QUESTS["silence_bandstands"]`, a new quest kind "bandstands" in `systems/quests.py`, built on the seals' survive circles as drafted):
- **Stand on a stage within 3.5 tiles of its instruments for 8 s in all** to smash them. Step off and the smashing **pauses** (mine: it doesn't mend, unlike the seals). The moment you start, the stage's band turns on you ("THE BAND TURNS ON YOU!") and the song carries the frenzy to every group within 25 tiles one last time. No extra waves rise: the band and the groups its song reaches are the fight. Every stage counts, quest taken or not.
- **The song falters as soon as you start smashing** (mine, after the first screenshot): a stage is a lure, and standing on one filled your temptation in 6 s, so every smash ended with you entranced on the stage. Now a stage you've started on no longer tempts.
- **A silenced stage plays no more:** its drums and harps lie in pieces, its eight lanterns go dark, it no longer tempts, its song no longer carries a frenzy, and the groups near it no longer wake from twice as far. **For every silenced stage your temptation fills 10% slower** (30% of the rate with all seven), from the island's lures; not from the Host's charm, which is his own. The game has no music to turn down, so the "island gets quieter" shows as stages going dark.
- **The instruments can't be shot or hacked away any more** (M30.1 had made them breakable): only standing on the stage smashes them, so nobody wonders why shooting them does nothing.
- **The sober man** (`sober_man`, the giver): haggard, in rags, on the coin beach beside the gilded pier's jetty (the pier is the quest's camp; its spots are the seven bandstands). His lines are mine: the food turns to ash; he woke up, nobody else ever has; seven bands, the music holds them; stand on a stage and smash the instruments; every band you silence, the pull gets weaker; and at the end, "There's a white island up north. Paradise. This is its mirror. Same hunger. Better wine." Hidden on the maps until Pandemonium is found, like the fallen angel. His map pin is gold on wine.
- **The seventh silence:** "THE MUSIC STOPS -- the Host of the Feast wakes in a rage -- The Palace is open". The palace hall is the quest's lair now: its gilded gate opens, closes behind you for the fight ("THE HOST OF THE FEAST -- at the bottom of Pandemonium"), and opens again when it's won ("THE HOST OF THE FEAST IS DEFEATED -- Pandemonium falls silent"). He rises in front of his seat.

**The Host of the Feast, form 1: the gracious host** (`ai/feast.py`, 12,000 HP, exempt from the zone's toughness like the cavalry; his guests aren't):
- **He dances** (the user's always-moving). Mine: a waltz round **his partner**, not round the hall. The palace hall turned out to be **152 x 100 tiles** (M30.1 used the draft's "76 x 50" as radii), so a waltz round the whole hall kept him 40 tiles away, mostly off screen. Now he dances a 13 x 8 tile round whose middle follows his target across the hall, turning as he goes and reversing every 9 s; far off, he glides over fast. **The toast and the beckoning plant him** (with a "!" tell); the grand spin carries him.
- **His charm:** within 6 tiles your temptation fills (full in 3 s right beside him); a faint rose ring shows its reach. Full: **"SWEPT INTO HIS DANCE!"**, and you drift at him for 2 s. **Reach him before you roll out and he spins you away** ("SPUN AWAY!", 30 damage, thrown 4 tiles). A roll snaps you out, as with every trance.
- **The hall changes room each phase (100-67-33%)**, a banner at each change ("THE BALLROOM -- follow the lit steps", "THE VAULT -- heaps of gold"):
  - **The banquet:** a long table across the middle of the hall (it stops you, not shots; gaps at the carpet and two more). **Courses served:** 3 dishes a serving, sent sliding off the table near you and across the floor at you (8 damage if one runs into you), each read by its look: **soup** `u` (a scalding pool that spreads to 3x its size over 6 s), **the roast** `@` (bursts into a ring of 12 bones), **jellies** `o` (three blobs hopping at you three times each, where each will land shown), **the cake tower** `A` (its fall line shown 0.8 s, then it topples along it). In the later rooms a **demon waiter** brings each dish in from 16 tiles out.
  - **The ballroom:** a dance floor over the hall and mirrors round the wall. **The dance floor:** squares of 4 tiles; each beat's step pattern (checkerboard, rows, columns, or rings round him) is lit dim a beat ahead, then bright. When the beat lands, every unlit square burns (18), 6 beats of 1.25 s, while he waltzes on. Drawn as light added to the floor, so the floor still shows through (my first try with "+" marks read as noise).
  - **The vault:** heaps of gold on the floor (low cover). **The vault's gold:** two heaps slide in from both sides of you like walls, closing your lane (they push, and hurt once); coins pour onto 6 marked circles (one on you); and **he tosses you 3 coins**: walk over one to catch it, **"GILDED!": x1.5 damage for 5 s, but +25 temptation** each.
- **Toasts** (every room): planted, glass raised 1 s ("A TOAST!"), then a wave of wine floods 32 tiles out at 10 tiles/s (14 damage, +15 temptation; roll through it), and **every guest in the hall frenzies**.
- **His dance figures** (every room): **grand spin** (a 3 s spinning glide across the hall, a ring of 10 pieces of cutlery flung every 0.45 s); **the beckoning** ("MAY I HAVE THIS DANCE?": a bow, then 1.1 s pulling you at him from up to 14 tiles, walk or roll against it, then a 140-degree slash, its arc shown the whole time); **carving set** (two fans of 7 knives curving across each other, twice); **chandeliers** (6 marked spots, one on you, then they crash and leave broken glass that cuts for 4 s).
- **The guests:** at each room's long sides, in the trance (`pandemonium.Reveller`s whose home is the room): 2 gluttons, 2 drunkards and 2 ravenous at the banquet; 2 dancing pairs and 2 masked dancers in the ballroom; 4 hoarders and a gilded reveller in the vault. They wake if you go near (or are hit), or at his toast. **Each room's group leaves with the room** (gone in a puff, no kill) and the next sits down.
- **Numbers** (`HOST_*` in config.py) are first guesses; the bot benchmark comes with form 2 (M30.5). Beaten for now (form 2 is M30.5), the quest is won: loot, a rare+ card, the achievement ("silence the seven bandstands and defeat the Host of the Feast"). His relics are drafted with you after form 2.

**Measured:** in the fight a game step takes 0.85 ms and a frame draws in 2.2-2.5 ms.

**Code:** `ai/feast.py` (FeastHost); `render/feast.py` (him, the floor, the dishes and everything he puts down; the swept and gilded marks on heroes); art in `render/pandemonium_art.py` (`sober_man`, `host_of_feast` standing, toasting, bowing, spinning); `ai/pandemonium` (`silence`, `silenced`, `falter`: lures, the song's carry and reach skip silenced stages); `systems/quests` (kind "bandstands": `_smash_band`, the band waking, the banner, the dev finish; the pit's fight banner); `systems/temptation` (the silence slowdown, `charmer`, being swept); `systems/combat` (the gilding); `world/pandemonium` (the hall is the lair, the pier the camp); tiles `SMASHED_INSTRUMENT`, `LANTERN_OUT`, `HOST_TABLE`, `DANCE_FLOOR`, `MIRROR_PANEL`; config `BANDSTAND_*`, `SILENCE_TEMPT`, `HOST_*`, `FEAST_SHOTS`, the quest, the boss. **Tests:** `tests/test_m30_4.py` (19); `test_m30_1` (the hall is the lair now), `test_m28_5` (the Host's relics come with M30.5). Full suite 1895 OK.

**For later:** play-test the numbers, especially how strong his charm is (3 s to fill at his side) and the dance floor's 1.25 s beat; the bot benchmark comes with form 2. Next is M30.5: the hunger (the hall falls into the wine, devour and growth, the maw, teeth in the floor, spilled feast, four moves), then his relics drafted with you.

## 23. Built: M30.5 (2026-11-23) -- the hunger, the Host of the Feast's second form

**The mask cracks** (`ai/hunger.py`, a mix-in of `ai/feast.FeastHost`: one body, two forms, like the necromancer's two lives). At 0 the gracious host doesn't fall: whatever he was doing stops, his hospitality is cleared away (dishes, jellies, gold, coins, chandeliers, the dance floor), his charm lets go of you, and for 3 s he can't be hit while his face splits (a cracked picture, flickering) under the banner **THE MASK CRACKS -- the hall falls into the wine**. The hall breaks up round him as it happens, the middle first. Then: **THE HUNGER -- kill his guests and clear the food before he eats them**, back at full health, **14,000** (as drafted, 17.3; scaled like every boss). The boss bar reads "The Hunger", then "The Hunger - fed 3" as he eats.

**The hall in the wine** (user): islands of table, floor and gold in spilt wine. Mine: a jittered grid of round islands 12 tiles apart (radius 3.5-5.5), each broken table (`TABLE_WRECK`), floor (the hall's own, carpet and all) or gold (coins); between them spilt wine (`HALL_WINE`, walkable) that **heroes wade at half speed** (a roll still carries you full length). He moves through it freely. About 6,100 tiles of wine and 2,900 of island in the 152 x 100 hall. When he falls the wine drains: the hall is as it was.

**He prowls** (mine: he no longer dances): round his prey 6 tiles off, turning about every 4-7 s, straight at you if you're far -- **unless a meal is within 12 tiles: then he goes for it**.

**Signatures, one added per phase (100-75-50-25%):**
1. **Devour** (the whole form): whatever he reaches he eats -- his guests, scraps of the feast, his own waiters -- and **stops to chew it for 1.2 s** (mine, after the first try: he ate 7 meals in 2 s, faster than anyone could clear them). **Each meal heals 3% of his max and makes him 5% bigger and stronger** (his body, his picture and his damage), **up to 10 meals** (17.3); past ten he still eats but gains nothing (mine). Eaten guests and waiters are no kill.
   - **What there is to eat** (mine): the collapsed table's feast, **8 scraps** scattered on the islands 6-22 tiles from him (soup, roast, jelly, cake, on plates); **his new guests**, 2 gluttons, 2 ravenous and 2 drunkards sitting down in pairs on the islands 10-20 tiles out, still feasting in the trance (each pair a group of its own, a scrap in front of it; the vault's guests leave); and **every 18 s, "MORE!": two demon waiters** come in from 18 tiles out carrying a course straight to him (`feast_waiter`: they never fight; kill them first). **Walk into a scrap, or shoot it, and it's knocked into the wine.**
2. **The maw** (75%): "HE OPENS HIS MAW!" -- a 64-degree cone 14 tiles long shown 1 s, then he inhales for 1.6 s: everything in the cone is pulled at him at 6 tiles/s, the feast too (and he eats what reaches him). **Reach his mouth and you're swallowed** ("SWALLOWED!"): hidden inside him, unable to attack or roll, chewed 3 times for 15 over 1.2 s, then **spat out 13 tiles across the hall**, toward its middle ("SPAT OUT!").
3. **Teeth in the floor** (50%): three waves, 0.9 s apart, of three lines of teeth 22 tiles long crossing near you (one right through where you'll be), each marked "v v v" for 1.1 s, then snapping shut ("W M W", 26 within a tile of the line; two crossing lines bite once). A roll dodges them.
4. **Spilled feast** (25%): he heaves up five gobbets in arcs onto marked spots (one on you, 1.1 s in the air): **rotting pools** (2.4 tiles, 8 s) that **slow you to 60%, burn (6 every 0.5 s), fill your temptation (3 a tick) and frenzy any guests within 4 tiles** of them, for as long as they rot.

**His moves (all four, every phase):** **lunge bite** (a marked line up to 18 tiles, 0.7 s; a lunge along it at 28 tiles/s, 14 to whoever's in the way, ending in a bite 3 tiles round his mouth for 34); **tongue lash** (aimed 0.6 s; it shoots out 16 tiles at 30 tiles/s; caught, "CAUGHT!", you're dragged back at 9 tiles/s and bitten for 30 -- **roll and you pull free**, "PULLED FREE!"; a meal it catches, he eats); **belly quake** (planted 0.9 s, then three shockwave rings 0.6 s apart rolling out to 26 tiles at 9 tiles/s, 16 each; roll through them); **bone scraps** (three fans of seven bones; **where each comes down it lies as clutter for 10 s that trips you**, 65% speed; at most 40 about).

**No charm** (user): `charm_at` is 0 in this form and he's nobody's partner any more.

**The bot benchmark** (M29.5's bot: a level-1 wizard that can't die, held at 60% health, circle-strafing at 8 tiles, shooting adds within 6 tiles first, else the boss; it never rolls and never clears food; seeds 31/7/12):

| | The gracious host | The hunger | Both | Damage taken a minute |
|-|-------------------|------------|------|-----------------------|
| Seed 31 | 3:33 | 4:34 | 8:07 | 531 / 797 |
| Seed 7 | 3:36 | 4:24 | 8:00 | 402 / 1,029 |
| Seed 12 | 3:38 | 4:28 | 8:07 | 480 / 874 |
| The Four Horsemen (reference) | 4:52-4:56 | 6:59-7:41 | 11:54-12:37 | ~850 / ~1,280 |
| More than Life + Death (reference) | | | 7:30 | 727 |

Close to the targets (~3 and ~5 min) and longer than the necromancer, as tier III should be; shorter than the Horsemen. In every run the hunger reached his 10 meals (the bot never clears food) and ate about 40 things. **What I changed:** the chewing (above); fewer scraps, farther out; he smells a meal from 12 tiles, not 16, and goes for it at 5.5 tiles/s, not 7.5; **form 1 rests 0.2 s less between moves** (0.8/0.7/0.6). **To play-test:** form 1 still deals less to the bot (400-530 a minute) than the necromancer (727) or the cavalry (~880): the bot circles at 8 tiles, outside his charm's 6, and walks out of most of his marked hazards without trying; his real threat, the charm, never touches it. The bench also caught a bot dying inside one step (100 max HP held at 60, then two hits in one step), now fixed in the bench (scratchpad `bench_host.py`).

**Measured:** a game step takes about 0.67 ms in form 2 and a frame draws in about 1.7 ms; the hall falling costs about a row a step (the worst step of the crack about 5 ms).

**Look** (`render/pandemonium_art.py`, `render/feast.py`): the hunger is a horned red thing with the cracked gold mask, a band of teeth and a dark maw across its middle; its maw opens wide (a tongue inside) for the maw, the tongue, the quake and the spilled feast, and works while he chews. He's drawn bigger with every meal (scale 6 to 9). The demon waiter: a small red demon in a black waistcoat carrying a covered gold dish. The maw's cone in red, the air streaming in while he inhales; the lunge's dashed line and bite ring; the pink tongue; teeth marked dim "v", then white "W M"; gobbets "&" arcing to marked rings; rotting pools (green-brown, `rot`), bone clutter (`bone_clutter`), the quake's rings (`belly_quake`); a "!" over him while someone struggles inside.

**Code:** `ai/hunger.py` (HungerForm: the crack and the islands, prowling, devour and growth, the waiters, the maw and swallowing, teeth, spilled feast, his four moves; `Waiter`); `ai/feast.py` (FeastHost takes the mix-in: two forms); `render/feast.py` (form 2's tells, his growing picture); art in `render/pandemonium_art.py` (`host_of_feast_crack`, `host_hunger`, `host_hunger_maw`, `feast_waiter`); a swallowed hero isn't drawn, can't attack (`scenes/game.py`) or roll (`systems/roll.py`); tiles `HALL_WINE`, `TABLE_WRECK`; zone looks `rot`, `bone_clutter` (`render/spell_fx.py`); effect `belly_quake`; config `HUNGER_*`, `FEAST_SHOTS["scrap"]`, the waiter, the boss spec `host_hunger` (added last, so the relic drop's seeds stay put). **Tests:** `tests/test_m30_5.py` (21); `test_m30_4`'s quest test now beats both forms; `test_m28_5` counts `host_hunger` as the Host's. Full suite 1916 OK.

### 23.1 The Host of the Feast's relics (user's picks, 2026-11-23)

One per pleasure he plays on, each the recommended one of three proposals (GEAR.md 21.1's rules: legendary only, the power +10% a level, one of them dropped once a run per player when he falls -- the hunger is him, so it's his drop):

| Pleasure | Relic | Slot | Power (at +0) |
|----------|-------|------|---------------|
| Feast | **Glutton's Bib** | chest | your kills (not bosses) leave a scrap of the feast for 8 s: walk over it to eat it -- heal 3% of your max HP and +5% damage for 10 s, up to 5 stacks at once ("FEASTED x3") |
| Wine | **The Host's Goblet** | trinket | every 12 s (once an enemy is within 8 tiles) you raise a toast ("A TOAST!"): a wave of wine rolls 8 tiles out at 16 tiles/s, 20 damage and a 1-tile push to each enemy it reaches, who's then **drunk** for 3 s (a boss 1.5 s): its clock runs at 60% (it moves, aims and attacks slower) and 30% of its hits on heroes miss. A "~" reels over a drunk enemy |
| Dance | **Dancing Shoes** | feet | your roll ends in a grand spin: a ring of 8 pieces of cutlery flung all round you, 10 damage each (9 tiles) |
| Gold | **Gilded Ring** | ring | hitting an elite or a boss tosses a coin out toward you (every 6 s at most; it lies 6 s): walk over it to be **gilded**, +25% damage for 4 s (a gold "$" over you) |

On the gear (16 letters at most) the goblet is "Host's Goblet". The power that grows: the bib's damage a stack, the goblet's damage, the cutlery's damage, the gilding's bonus. Look (M28.6): the bib turns your body white, wine-stained. Affixes: Bib -- thick hide, second wind, magnet; Goblet -- broad strokes, lingering, potency; Shoes -- swift boots, extra roll, quick recovery; Ring -- brutal, keen eye, prospector. Code: `systems/relics.py` (`_bib`, `_goblet`, `spin_out`, `toss_coin`, `_gilded`, `on_kill`), `combat.strike` (the bib's stacks, the gilding) and `combat._relic_on_hit` (the coin), `Statuses.drunk` (`systems/statuses.py`: the slow) and `Character.take_damage` (the misses), `roll._ended` (the spin), `render/feast.py` (`draw_feast_marks`: scraps, coins, the gilded "$"; `draw_drunk`), effect `goblet_wave`, config `U_BIB`, `U_GOBLET`, `U_SHOES`, `U_GILDED`, `WEAPONS["dancing_cutlery"]`. 46 boss uniques now (U43-U46). **Tests:** `tests/test_m30_5.py` (30 in all, 9 for the relics); `test_cards` and `test_m28_5` count them.

**M30 (Pandemonium) is complete. NEXT: M31, the west zone (the Past), drafted with the user first.**

---

## 24. Pangaea (west): the land (user, M31 rounds 1-3, 2026-11-23)

**What the past means: deep time** -- a primeval island from before people's history (nothing on the main island is prehistoric; the desert's mummies, the ruins' old soldiers and the forest's skeletons are a younger past). It's the clean opposite of the Future (the east, M32).

**Name: PANGAEA** ("all the land", the first supercontinent; it starts with P like Paradise and Pandemonium). **(mine)** The arrival banner: "where the world began".

**Look: jungle and fire.** Giant ferns and cycads, deep green on dark volcanic soil, black basalt, glowing orange lava and drifting ash. **The shore is a black-sand beach**, steaming where the lava meets the sea (Paradise's cloud bank, Pandemonium's coin beach). The green is darker and wilder than the swamp's; the orange is new to the game.

**The land's dangers (all four)** -- the counterpart of Paradise's blood and Pandemonium's excess:
- **The volcano and its lava:** a smoking volcano at the heart. Lava rivers run down from it, burning and closing lanes, and now and then it throws **lava bombs** onto marked spots.
- **Tar pits:** black tar pools that slow you badly and hold you; enemies stuck in them are easy prey. Some hold the half-sunk skeletons of giant beasts.
- **Amber:** golden amber outcrops with things frozen inside, from insects to small beasts. Breaking one frees what's in it: loot or a fight.
- **Giant bones and nests:** huge ribcages and skulls to fight among (cover), and nests of eggs: break the eggs and the parent comes while the hatchlings swarm.

**Landmarks (all four):**
- **The sea-beast skeleton:** the bones of a giant sea monster beached on the shore facing the main island, its ribs an arch you walk through: where you arrive (Paradise's Gate, Pandemonium's gilded pier).
- **The painted caves:** a cave mouth in a hill, its walls painted with hunts of the island's beasts, round a fire pit: the early hunters' home.
- **The great nest:** a giant ring of branches and bones on a crag, with eggs the size of a man.
- **The impact crater:** a glass-floored crater round a strange black stone: the star that will end the age of the giants.

**The shape (round 3): rings of ages.** Paradise climbs, Pandemonium sinks; on Pangaea **walking inland goes back in time**. The shore ring is the youngest age (the great mammals and the early hunters), the middle ring the dinosaurs, the heart the oldest (giant insects round steaming pools) under the volcano. The enemies change ring by ring.

## 25. Pangaea: the echoes (user, M31 rounds 1 and 3)

**The past repeats.** About **3 s** after an enemy attacks (shots, slams, charges, anything that hurts), **a faded echo plays the same attack again from the same spot, at full damage**. You saw it once, so you can read it, but you dodge everything twice. **Killing the enemy cancels its echoes that haven't played yet** (so killing fast is still the skill, as with Paradise's unveiling, but for a different reason).

**Only enemies echo:** your own attacks don't, so your damage is the same as everywhere else.

**Who lives there (round 3):** four groups of four, as on the other islands: **great mammals**, **dinosaurs**, **giant insects and the earliest life**, and **a tribe of early hunters** (spears, traps, fire) who hunt the beasts and you. **(mine)** By ring: mammals and hunters on the shore ring, dinosaurs in the middle, insects at the heart.

## 26. Pangaea: the enemies (all 16 picked, M31 round 4)

Every attack below echoes about 3 s later (section 25). One elite in each group.

| Group (ring) | Enemy | Behaviour |
|--------------|-------|-----------|
| Great mammals (shore) | **Mammoth** (elite) | walks in herds of 2-3; trumpets (a cone that pushes you back), then the whole herd stampedes in parallel lanes shown first: roll through the gaps |
| | **Sabre-tooth** | stalks hidden in the tall ferns, only its eyes showing; pounces from far off along a marked line and pins you, biting, until you roll free |
| | **Woolly rhino** | its armoured front shrugs off shots; it charges, skids and turns slowly, so you hit it from the side or behind |
| | **Cave bear** | rears up on its hind legs (the tell), swipes twice in a wide arc and slams down; its roar wakes the beasts nearby |
| Dinosaurs (middle) | **Raptor pack** | packs of 3-4 that circle you at a distance, then leap in one after another from behind you, each leap marked |
| | **The Tyrant** (elite) | a huge king lizard: its roar is a cone that roots you in fear for a moment unless you roll; it bites ahead and sweeps its tail behind; each footstep shakes the ground |
| | **Club-tail** | armoured all over its back (shots glance off everywhere but its head); swings a club tail in a wide arc behind it that throws you |
| | **Pterosaur** | circles overhead, then swoops along a shown line; if it catches you it carries you a few tiles and drops you, perhaps into tar or lava |
| Giant insects and the earliest life (heart) | **Giant dragonfly** | groups of 3, darting in fast straight lines (marked a beat ahead), turning sharply between darts |
| | **Bombardier beetle** | turns its back to you, then sprays a cone of boiling spray behind it: get round to its front |
| | **Giant ants** | march in a column from a mound; break the column and they swarm you; the mound keeps sending more until you collapse it |
| | **Sea scorpion** (elite) | a huge armoured hunter in the steaming pools: grabs you with its claws from the pool's edge and drags you into the scalding water; stabs with its tail spike |
| Early hunters (shore, from the painted caves) | **Spear hunter** | throws spears with a spear-thrower, fast and far; they stick in the ground where they land, fencing lanes for a few seconds |
| | **Trapper** | lays snares and covered pits, only faintly marked (a snare holds you a second, a pit drops you in for a moment); throws bolas that tangle your legs |
| | **Fire-bearer** | waves torches and sets the ferns alight: the fire spreads through the jungle; drives the beasts toward you like a beater |
| | **Shaman** (elite) | paints on the rock: the painted beasts come alive as flat ochre spirits (a mammoth, a sabre-tooth) that charge once and fade; keeps the tribe's fires burning |

## 27. Pangaea: the quest (user, M31 round 5)

**The great hunt.** The cave wall shows **seven great beasts**, and they roam the island: each bigger than the rest of its kind and named (**(mine)** quest-only variants of the island's beasts, the framework's hunt kind -- e.g. Old Tusk the mammoth, Broken Horn the rhino; one or two per ring). **Track them and kill them**; each kill is painted on the wall, and **the seventh wakes the boss**. You hunt instead of standing still (the seals and the bandstands are both "stand at it ~8 s"). **(mine)** Out from the start, every kill counts, quest taken or not (like the seals); visible and shootable from range like any enemy (the no-ambush rule, BOSSES.md 3.2), so the sabre-tooth's variant shows its eyes from far off.

**The giver: the old painter.** The tribe's painter, too old to hunt, by the fire in the painted caves. She paints what will be: **the deepest wall already shows the end of the age**. She is the one who remembers: she knows **the echoes are the island remembering** (Paradise's fallen angel tells the truth, Pandemonium's sober man woke; she remembers).

## 28. Pangaea: the boss -- THE ANCESTOR (user, M31 rounds 6-7)

**Who:** the beast all beasts come from. **It walks back in time as you hurt it**, like the island's rings: a great mammal, then a tyrant lizard, then a giant insect, then the first life crawling out of the sea, each age with its own kit.

**Arena: the caldera.** At the heart (the oldest place), inside the volcano's rim: a floor of cooling black rock between lava lakes, **sealed by a curtain of fire until the seventh great beast falls**.

**Two forms** (like the Horsemen and the Host of the Feast), each a full kit:
- **Form 1, the ages:** it changes shape at each third of its health: **great mammal, tyrant lizard, giant insect**. Each shape brings a signature that carries on into the shapes after it (like the Host's rooms).
- **Form 2, the first life:** at 0 the first life rises, **a vast primordial thing in a sea that floods the caldera**.

**It moults:** each older shape bursts out of the last one's skin and leaves the old body as **a husk on the floor**. The husk is cover, and **for a while it echoes the old shape's attacks**.

**Its echoes:** its attacks echo 3 s later at full damage like everyone's on Pangaea. **(mine, from the user's pick)** Its patterns are sparser and easier to read than other tier III bosses', so the echo doubles them into a fair, dense fight.

**Movement: like its age.** Always moving in its shape's way: the mammal charges round the caldera, the lizard stalks and lunges, the insect flits and hovers, the first life swims through the flood. Only a few moves plant it, with a clear tell.

### 28.1 Form 1: the ages (user, M31 round 8)

**Phases = ages:** the great mammal, the tyrant lizard, the giant insect (**(mine)** 100-67-33-0%, a moult at each threshold). One signature comes with each age and keeps going in the ages after it:
1. **The stampede** (the great mammal): it bellows, and **spirit herds** (mammoths, rhinos) stampede across the caldera in lanes marked first, with gaps to stand in. The later ages keep calling them.
2. **The roar** (the tyrant lizard): a huge roar in a wide cone **roots you in fear** for a moment unless you roll, and shakes the rim so **rocks fall onto marked spots** all over the caldera.
3. **The swarm** (the giant insect): clouds of small insects pour out of it and fly across the caldera in **shifting rivers that sting** what they pass through; you move with the gaps.

**Moves (all four; each shape does them its own way):**
- **The charge:** along a marked line -- tusks for the mammal, a lunging bite for the lizard, a dive for the insect.
- **Spit fan:** a fan of shots -- bone shards, then boiling spit, then acid.
- **The eruption:** it shakes the volcano, and lava bombs fall onto marked circles around you.
- **The sweep:** a wide arc behind it -- a hind kick, then a tail sweep, then a stinger.

### 28.2 Form 2: the first life (user, M31 round 9)

At 0 the giant insect's skin splits too, and **the first life rises**: the caldera floods with a warm primordial sea.

**Look: a vast sea-thing**, the oldest hunter of the first seas: a huge segmented body with grasping arms and a round mouth ringed with teeth, many-eyed, glowing faintly.

**Arena: the tide.** The sea **rises and falls**: at low tide the floor is open; at high tide only the rocks and the husks stand above it, and **you wade slowly while it swims freely**. **(mine)** A tide every ~20 s (rising over 3 s, shown first by the water creeping in), wading at half speed like the hunger's wine; a roll still carries you its full length.

**Signatures (all four), one added per phase** (**(mine)** four phases, 100-75-50-25-0%, like the hunger):
1. **Life evolves:** small first life crawls out of the sea and **evolves if left alone**: a blob becomes a crawler, then a small beast. Kill them before they grow up. **(mine)** ~8 s a stage; the evolved beast is one of the island's (a raptor, a sabre-tooth cub...).
2. **Echoes of the ages:** the three husks from form 1 **wake as echoes**, and each replays its age's signature on its own: the mammal's stampede, the lizard's roar, the insect's swarm.
3. **Tentacles:** its arms burst out of the sea on marked spots, sweep along lines and grab you if you're slow. **(mine)** These are its arms reaching up through the sea far from its body; the arm lash (below) is the reach from its body.
4. **Tidal wave:** it rears up and **a great wave rolls across the caldera**, pushing you; roll through it.

**Moves (all four):** **dive and surface** (it sinks out of sight and surfaces under you, its spot shown by a swelling ripple, bursting up with a ring of spray), **whirlpool** (a spinning current that drags you round toward its centre; walk or roll out), **boiling bubbles** (bubbles of boiling gas rise and burst on marked spots in quick chains), **arm lash** (its long arms lash along shown lines, then grab and pull you closer).

Everything it does echoes 3 s later (section 28), and so do the husks' echoed signatures **(mine: once; an echo is never echoed again)**.

### 28.3 Numbers and rules (mine, to tune with the bot and then in play)

- Tier III, like the Host of the Feast (12,000 + 14,000). **Proposed:** the ages **12,000** (4,000 an age); the first life **14,000**. All scaled like every boss. Policy: no HP cut below these on bot numbers alone.
- Target length (bot): the ages ~3 min (about a minute an age), the first life ~5 min.
- **The echo, exactly (mine):** an enemy's attack is whatever it fires or drops that can hurt (shots, zones, rings, slams, bites); a charge or a pounce echoes as a faded copy of the body running the same path. The echo is drawn faded (a ghost of the enemy's colours) and shows the same tell again, a beat ahead, so it's as readable as the first. An echo never echoes, and the land itself (lava bombs, tar, fire in the ferns) doesn't echo: only enemies. Killing an enemy cancels its waiting echoes; a husk's echoes stop when the husk crumbles (**(mine)** ~20 s after the moult in form 1).
- Relics: like every boss, uniques drafted with the user once it's built (GEAR.md 21.1); **(mine)** one per age is the obvious set (mammal, lizard, insect, the first life).

## 29. M31 build plan (mine; each step: tests, a headless screenshot, a report, a stop)

| Step | Content |
|------|---------|
| M31.1 | **Pangaea's land:** the west zone (Paradise's framework), jungle and fire, the black-sand beach, the rings of ages (shore, middle, heart), the volcano and its lava rivers and lava bombs, tar pits, amber outcrops, giant bones and nests, the four landmarks (sea-beast skeleton, painted caves, great nest, impact crater), the caldera (sealed shell, the curtain of fire), the HUD name and banner. **Built, section 30** |
| M31.2 | **The echoes + the shore ring's 8:** recording and replaying attacks (faded, cancelled on death), endgame toughness; the great mammals (mammoth, sabre-tooth, woolly rhino, cave bear) and the early hunters (spear hunter, trapper, fire-bearer, shaman); fire spreading through the ferns. **Built, section 31** |
| M31.3 | **The middle and the heart, 8 more:** raptor pack, the Tyrant, club-tail, pterosaur; giant dragonfly, bombardier beetle, giant ants (and their mounds), sea scorpion; nests (eggs, the parent, hatchlings) and amber (breaking it frees what's inside) |
| M31.4 | **The quest + form 1:** the great hunt (the seven named great beasts, the painted wall), the old painter, waking and sealing the caldera; the ages (the mammal, the lizard, the insect, the moults and their echoing husks, three signatures, four moves) |
| M31.5 | **Form 2:** the first life (the tide, life evolving, the husks' echoes, tentacles, the tidal wave, four moves), the bot benchmark; then the relics drafted with the user |

## 30. Built: M31.1 (2026-11-23) -- Pangaea's land

**The zone:** `config.OCEAN_ZONES` is now Paradise, Pandemonium and Pangaea (the zone key `pangaea`, west; it was `past` in `ZONE_PLACES` until now). Over five seeds it sits 3,030-3,320 tiles west. Everything else is M29.1's framework: hidden until found, the arrival banner **PANGAEA -- "where the world began"**, F3 in dev mode jumps to each zone in turn (Pangaea third). Only the east stays open sea.

**The land** (`world/pangaea.py`, a `Plan` per seed, ~85 ms; chunks ~4.5 ms each, Pandemonium's ~7), as drafted, plus these calls of mine:
- **The rings of ages:** a tile's depth is its distance from the centre over the coast's there (0 at the centre, 1 at the shore), wobbled a little so the edges wander; **the heart under 0.42, the middle under 0.72, the shore ring past it** (`PANGAEA_RINGS`). **Each ring's name comes up as a banner the first time you walk into it** (mine): **THE AGE OF GIANTS** -- "the dinosaurs' jungle" (the middle), **THE FIRST AGE** -- "where the oldest things still crawl" (the heart); the shore ring's is the island's own arrival banner. On the maps each ring has its own ground colour, so the rings show.
- **The ground, ring by ring:** the shore ring is **fern meadow** (lighter green) with patches of tall ferns (walkable: the sabre-tooth's cover, M31.2), clumps of teal jungle trees, lone cycads and rocks; the middle is **dark jungle floor** with tall jungle ferns, giant ferns (bright green cover, breakable), jungle trees and cycads; the heart is **grey ash** with groves of horsetails (walkable) and scale trees (tan, breakable). **Amber** outcrops (gold, an insect's shape in some) in the heart and the middle, a few tiles each, breakable into shards (what's inside: M31.3).
- **The volcano:** the caldera at the centre, an oval of 70 x 52 tiles inside a rim 4 thick (Pandemonium's hall is 76 x 50); its **curtain of fire** (7 wide) faces the main island. Inside, **four lava lakes** with burning crust round them, clear of the middle (where it sleeps) and the curtain. Kind "court" until M31.4 makes it the quest's lair. Round the rim, the **cone**: cinders with embers and basalt boulders, 16 tiles out.
- **The lava rivers:** three, from vents on the cone: the first off to one side of the trail all the way to the sea (the sea **steams** at its mouth for 14 tiles), the second behind the volcano and the third to the other side, each ending in a **field of cooled basalt** in the middle ring. Molten down the middle (1.9 tiles either side of its line): **solid and not watery**, so nobody crosses it, water walkers neither; shots fly over. A **crust** either side out to 3.1 tiles: walkable, it burns.
- **Game trails** (beaten earth; Paradise's roads, Pandemonium's avenues): from the skeleton to the curtain, a **ring trail round the middle** (depth 0.57; every river crosses it), spurs to the caves' mouth, the great nest's ramp and the crater's rim. Where a trail meets lava, **a crossing of cooled rock**.
- **The sea-beast skeleton:** its tail's vertebrae in the surf, its **spine overhead** (walkable: you walk under it) running 34 tiles inland between **eight pairs of ribs** (longest in the middle; cover), its skull at the inland end off to one side, empty-eyed, teeth toward the ribs.
- **The painted caves** (shore ring): a hill of rock, a chamber inside it walled with **red-ochre paintings of hunts**, the hunters' **fire pit** in the middle, the mouth toward the nearest trail. Kept for M31.4: where the painter stands (behind the fire), and **the deepest wall** (the painted tiles away from the mouth: where the great hunt's kills will be painted).
- **The great nest** (middle ring): a crag of sheer rock (a ramp up it toward the trail), on top a ring of branches and bones round **four giant eggs** (2 x 2 each). **The impact crater** (middle ring): thrown-up rock round a floor melted to glass, **the black stone** (violet glint) in the middle.
- **Ten nests** (middle ring: a ring of branches, 3-5 eggs, breakable), **fourteen giant bones** (shore and middle: a ribcage, a horned skull or a pair of tusks, any way round; cover that never breaks), **fourteen tar pits** (shore and middle; four in ten have a beast's bones half-sunk in them), **ten steaming pools** (the heart; watery, like the fonts and fountains).
- **The black-sand beach:** the land's last ~5 tiles.

**The land's dangers** (`systems/pangaea.py`; numbers mine, `PANGAEA_CRUST`, `TAR`, `LAVA_BOMB_EVERY`, `LAVA_BOMB`):
- **Lava crust burns:** 7 every 0.25 s while you stand on it (an enemy too, not a boss).
- **Tar sinks you:** stepping in slows you to x0.55, sinking to x0.22 over 1.6 s; **a roll carries you out at full length** (rolls ignore slows); bubbles round you while you're in it. An enemy in tar runs at half speed, its whole clock (`Statuses.tarred`).
- **Lava bombs:** in the heart the volcano lobs a volley at you every ~9 s (in the middle ring ~16 s; never on the shore ring or in the caldera), give or take 3: **three bombs**, one where you stand and two 3-7 tiles round, **each marked 1.8 s** (an orange ring tightening, flashing at the end, the bomb falling out of the sky onto it), then a blast (radius 2.2, 22) and a **splash of burning rock** (4 s). Walking deeper in cuts your wait to the heart's.
- All of it **scales like the zone's enemies' damage** (the players' level, the difficulty, x1.5 for the zone). The land doesn't echo (section 28.3).

**Not yet:** no enemies (`BIOME_ENEMY_DENSITY` has no "pangaea": M31.2-M31.3); breaking amber or eggs frees nothing yet (M31.3); the caldera and the caves are shells until the quest (M31.4).

**Code:** `world/pangaea.py`; `world/zones.py` (`plan_of`, `shore_band`, the key `pangaea`); `world/generator` (`_pangaea`, 22 tiles); `world/biomes.PANGAEA` (id 9); `world/tiles.py` (45 new) and `palette.py`; `systems/collision.WATERY` (the springs, the steaming sea; never the lava); `systems/pangaea.py` (`Volcano`, `step`, `hazard`, `ring_banner`); `systems/statuses` (`tarred`); `scenes/game` (`volcano`, the step, `_zones_near`'s ring banners); `render/pangaea.py` (the bombs, the tar's bubbles), effect `lava_burst`, zone `lava_splash` (`render/spell_fx.py`). **Tests:** `tests/test_m31_1.py` (26); `test_m29_1` (only the east stays open sea now) and `test_m30_1` (three zones) updated.


## 31. Built: M31.2 (2026-11-24) -- the echoes and the shore ring's eight

**The echoes** (`ai/pangaea.Beast`), as drafted (sections 25 and 28.3), with these calls of mine:
- **What echoes:** a Pangaean enemy attacks through four kinds of thing, and those are what play again: a hit on an area (a cone, a circle or a line: swipes, slams, bites, the trumpet), shots (spears, bolas), a run (a charge, a stampede, a pounce, a painted spirit's charge) and something thrown in an arc (a torch). **3 s later** (`ECHO[0]`) the same thing plays again from the same spot with the same damage it had the first time.
- **Its tell:** for as long as the attack's own windup (at least 0.35 s, at most 0.9 s) before it plays, **a ghost of the enemy** (its own picture, washed pale and see-through) stands where it stood, facing the way it faced, and **the shape of what's coming is marked**: the cone, the circle, the line, a run's lane, a dotted line where each shot will fly, the ring where a torch will come down -- flashing faster at the end. An echoed run is a ghost running the same line (through everything: it's a line already run); an echoed shot is the same shot, drawn faded.
- **An echo never echoes. Killing the enemy cancels all of its echoes**, waiting or running (a ghost already running stops too: it goes with its enemy, so killing fast always pays). What's already in the air (a thrown torch, shots) still comes down.
- **Nothing else echoes:** not the players; not the land (lava bombs, tar, fire); not what the hunters leave lying (stuck spears, traps: laid, not thrown -- an echo would lay the same trap on the same spot); not a bear's roar or a fire-bearer's beat (they hurt nobody). **An echoed torch hurts where it lands but lights no ferns** (the fire is the land's).
- **Holds don't echo as holds:** an echoed pounce is a ghost leaping the same line and hitting what it touches; the bites while it held you echo as bites on the spot where you were.

**Where they live:** each type is rolled only on its own ring (`config.PANGAEA_RING_OF`: the chunk's middle picks from that ring's types, and the spot must be on that ring too). So far only the shore ring has any: **the middle ring and the heart stay empty until M31.3**. Density 1.0, like Paradise's, and endgame tough like every zone's (`ZONE_TOUGH`: x2.5 HP, x1.5 damage, packs a third bigger, elites twice as likely). Over one seed's shore ring there are about 140; mammoth herds (3-4 out here) and hunting parties are the most.

**The eight** (numbers in `config.py`: `MAMMOTH`, `SABRE`, `RHINO`, `BEAR`, `SPEAR`, `TRAPPER`, `FIREB`, `SHAMAN`; base HP before the zone's x2.5):

| Enemy | Base HP | What it does |
|-------|---------|--------------|
| **Mammoth** (elite, herds of 2-3) | 260 | walks at you; every 8 s it **trumpets** (0.9 s, trunk up, its cone shown: 70 degrees, 8 tiles, pushing you 3 back for 0.4 of its damage); then **every mammoth of its herd** within 16 tiles takes a lane -- parallel, 3.6 tiles apart, the trumpeter's through you, shown 1.1 s while they shuffle into place -- and they **stampede** 18 tiles at 11 tiles/s, trampling whatever breaks (a wall dazes one). Close in, a tusk sweep (120 degrees, 3 tiles) |
| **Sabre-tooth** | 110 | stalks you at x0.6, circling at its distance; on tall ferns, jungle ferns or horsetails **only its eyes show** (it can still be shot, and its health bar shows); from 5-11 tiles it crouches 0.7 s (its line shows) and leaps at 18 tiles/s; caught, **you're pinned** (you can't walk) and bitten for 9 every 0.5 s until you **roll free** (**ROLLED FREE!**: it's thrown off and dazed 1.2 s) or 3 s pass |
| **Woolly rhino** | 200 | hits from within 60 degrees of its front do x0.25 (sparks fly); it scrapes 0.8 s (its lane shows), charges 14 tiles at 13 tiles/s, skids 0.7 s, then **turns back toward you slowly** (1.3 rad/s): hit it from the side then. Caught, you're tossed 3 tiles |
| **Cave bear** | 220 | **rears up** 0.8 s (the swipe's cone shows), swipes twice (150 degrees, 3 tiles, 0.35 s apart), slams down 1.4 tiles ahead (radius 2.6, x1.4), then stands open 1.2 s. **Its roar** (on first sight, then every 14 s) tells every enemy within 18 tiles where you are |
| **Spear hunter** (parties of 1-2) | 70 | keeps 8-13 tiles off; a spear every 2.2 s (0.5 s windup), leading you by half its flight, 20 tiles/s out to 17; one that comes down on open ground **sticks there 4 s**: a stake that stops you, not shots (never inside someone, never on lava) |
| **Trapper** | 65 | lays 3 traps round its home, then one where it stands every 2.6 s while it fights (at most 5 of its own, each lasting 40 s; 4 in 10 are pits), **only faintly marked**: a snare holds you 1 s, a pit holds you 1.3 s and hurts 18; **a roll carries you over**. They catch beasts too (held twice as long), never the hunters. **Bolas** every 3.4 s: tangled, x0.3 for 1.8 s |
| **Fire-bearer** | 75 | keeps 5-9 off; a torch every 3.8 s, lobbed 0.9 s (where it lands shows): it bursts (1.6 tiles) and **sets the ferns alight**; close in, a torch swing (110 degrees). Every 7 s **it beats the bush**: every beast within 16 tiles knows where you are and comes x1.4 as fast for 4 s (a "^" over it) |
| **Shaman** (elite) | 280 | keeps 8-13 off; every 5.5 s it paints (1.1 s, an ochre hand out): beside it a beast comes in, flat ochre, and its line shows; then **the spirit charges once**, 18 tiles through everything, and fades -- a mammoth's (13 tiles/s, 1.4 tiles across, 26) or a sabre-tooth's (19, 0.8, 18). **While it lives, no fire within 12 tiles of it burns out** |

**Fire in the ferns** (`systems/pangaea.Land`, numbers mine: `FIRE`, `PANGAEA_FLAMMABLE`): the ferns burn -- tall ferns and jungle ferns most, the meadow least; giant ferns, cycads, horsetails and twigs too. A burning tile burns 6 s, every 0.5 s trying to light its four neighbours, until its blaze has lit its size (a torch's 40 tiles; **a lava bomb's splash lights the ferns too**, 10), then it's **scorched ground for good** (like Paradise's stains, the island blackens the more you fight on it). Standing in it burns 6 every 0.3 s, scaled like the land's other dangers; never the fire-bearer or the shaman. A fire 70 tiles from every hero goes out.

**Look** (`render/pangaea_art.py`, 13 pictures): the mammoth dark and shaggy with curling ivory tusks (and trumpeting, trunk up), the tawny sabre-tooth with its long fangs (leaping; and just two gold eyes in the ferns), the woolly rhino with its great horn, the dark-brown cave bear (and reared up, claws out); the hunters in hides -- the spear hunter with a flint-tipped spear, the trapper in a fur cap with rope and bolas, the fire-bearer with a torch in each hand, the shaman in a crown of feathers with ochre on its face and a staff (and painting, an ochre hand out). `render/pangaea.py`: the ghosts (any picture washed toward pale blue and see-through, baked once), the spirits (any picture in flat ochre by its own shading), the shapes and tells (the herd's lanes, the trumpet's cone, the pounce line, the rhino's lane, the bear's swipe, a spirit's lane, a torch's ring), a hit's flash, the flames on burning ferns, the traps' faint marks; tiles `BURNING_FERNS`, `SCORCHED`, `STUCK_SPEAR`; shots `spear`, `bolas` and their faded `_echo` looks; effect `beast_roar`.

**Measured:** with 28 awake on the shore ring (a fight with all eight, the rest of their chunks woken round it; fires burning, ghosts running), a game step takes 1.4 ms and drawing 2.1 ms (Pandemonium's: 1.2 and 2.5). Each ghost and spirit picture is baked once. A chunk's roster on Pangaea takes ~0.9 ms (the ring is looked up per spot).

**Also changed:** `test_m31_1`'s "nobody lives here yet" now checks somebody does.

**Code:** `ai/pangaea.py` (`Echo`, `Runner`, `Beast` -- `area`, `throw`, `record_run`, `ram`, `lob`, `play_echoes` -- and `Mammoth`, `SabreTooth`, `WoollyRhino`, `CaveBear`, `Hunter`, `SpearHunter`, `Trapper`, `FireBearer`, `Shaman`); `systems/pangaea.py` (`Land`, `land`, `ignite`, `stick_spear`, `lay_trap`; lava bombs light the ferns); `systems/spawner` (the rings: `_ring`); `render/pangaea.py` (`draw_beast`, `draw_pangaea_tells`, `draw_spirit_painting`; the fires and traps in `draw_pangaea`), `render/plains.py` (calls them), `render/pangaea_art.py`; config `ECHO`, `PANGAEA_RING_OF`, the eight's tuples, `FIRE`, `PANGAEA_FLAMMABLE`, `PANGAEA_SHOTS`, `BIOME_ENEMY_DENSITY["pangaea"]`, bestiary pages; palette (sprite letters `K` ochre and `W` dark fur, the ghosts', the spirits', the fire's). **Tests:** `tests/test_m31_2.py` (29).

**For later:** every number wants a play test, the echoes' readability most of all (a ghost and its shape are drawn for 0.35-0.9 s before each echo plays). M31.3 brings the middle ring's dinosaurs and the heart's insects, with the nests and the amber.
