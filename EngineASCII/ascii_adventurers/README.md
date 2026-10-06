# AsciiAdventurers

A top-down ASCII adventure roguelike on one huge island, built on the
narrative engine (`narrative_engine/`). Everything for the game lives in
this folder.

**Status:** Milestones 1-22 and "Adventurers" are done:
- keyboard walking, mouse aiming, a smooth scrolling camera;
- shooting, spells and destructible terrain;
- a seeded, chunk-streamed world with six biomes;
- enemies and combat, with 100 hp;
- the island (M5): open plains in the middle, the other five biomes
  (haunted forest, desert, ruins, swamp, mushroom) as equal slices of a ring around
  them, then the coast and endless ocean. The ring is dealt and rotated
  differently every run;
- maps (M6): a minimap in the top-right corner and a big map on M. Explored
  ground shows real terrain; the rest of the island shows as a dimmed biome
  outline;
- adventurers: you play a hero (wizard, dwarf, bard, princess or
  huntress);
- performance (M7): terrain is drawn from cached pre-drawn blocks, sprites
  are single images, and shots, effects, HUD and minimap draw in batches
  or from cache. Measured headless on the 172-column grid: ~1 ms a frame
  in normal play (was ~7 ms), ~8 ms with 300 enemies fighting on screen;
- menus (M8): a title screen over a drifting island, hero select with an
  optional island seed, a settings screen, a pause menu (ESC), and a
  game-over screen with the run's stats and your records (NEW RECORD
  highlights). Settings and records are saved per player in `save/`;
- multiplayer-ready core (M9): the game runs a list of players, each with
  their own hero, controls and camera, free to roam the island apart. The
  world streams, and enemies wake and choose targets, around every player.
  The world advances in fixed 1/60 s steps (drawing blends between steps,
  so it's smooth at any refresh rate), and the same inputs give the same
  game at any frame rate. Gamepads work everywhere (twin-stick in play).
  Solo play looks the same as before; co-op itself comes later;
- hero weapons (M10), each hero their own:
  - wizard, arcane missiles (since M20; it was the shock bolt): 3 darts
    fan out, then curve onto the enemy nearest your reticle;
  - huntress, longbow: fast, long-range arrows that pierce 2 enemies;
  - princess, rainbow: a fan of 5 colored shots, deadly up close;
  - dwarf, throwing axes: spin out through every enemy in the way and come
    back to him, hitting again (they bounce off walls);
  - bard, lute: plays by itself, every beat hurts everything around him.
  Heroes never hurt each other (ready for co-op); monsters still do.

The look: heroes and enemies are pixel-art sprites; everything that flies
or pops up (bolts, arrows, hits, damage numbers, health bars) is drawn with
text characters, like the terrain.

The enemies:
- goblin archer, warlock (red aiming beam before it casts), spell tower
  (ruins), and ogre (armored front, throws rocks that break walls);
- burrower (desert), spore puffer (mushroom), fallen warrior (plains);
- dust devil, sentry wisp, bog toad, spore spitter, thornback boar.

Enemies use Noita-style clumsy AI, and friendly fire and infighting are on.
- XP and cards (M11): kills give XP; every level is a card pick. Three
  big cards come up in the middle of the screen and the game pauses (in
  multiplayer it will keep running); choose with left / right and take one
  with Enter, or with the mouse. Several level-ups in a row come one offer
  after another. 19 placeholder cards (a full set is coming): damage,
  attack speed, HP, speed, range, regeneration, lifesteal for everyone;
  extra/piercing/faster shots for shooters; and each hero's own (the
  wizard's lightning jumps farther, the huntress's volley, the princess's
  extra colors, the dwarf's extra axes, the bard's louder beat). The
  new "corners" HUD: HP, level/XP, kills and the run's clock top-left; the
  world fills the screen; seed, biome and distance are in the pause menu.

- bigger plains, more enemies (M12): the plains have twice the area (the
  island grew to keep the biome ring as wide). Five new enemies, none of
  them ambushers: dust devil (desert, plains; a whirlwind that circles
  close, flinging spirals of sand and stinging on touch), sentry wisp (ruins; steady bolts, and
  much faster while its sweeping searchlight is on you), bog toad (swamp;
  hops, spits a fan of acid), spore spitter (mushroom; a ring of spores all
  round, turning each volley), thornback boar (forest; scrapes, then
  charges in a line -- dodge and it slams into a wall, dazed).

- the dwarf (M13) replaced the knight, and the card catalog was written
  (`design/CARDS.md`, 100 cards, reviewed and approved).
- cards 2.0 (M14), the first 48 cards of the catalog:
  - a stat layer: damage %, attack speed, crit chance (5% to start) and
    crit damage, area, duration, status damage and chance, spell
    cooldown, armor, evasion (was "dodge"), regen, lifesteal, move speed, pickup radius,
    XP, luck. "+X% damage" cards add up; "xN damage" cards multiply;
  - five rarities (common, uncommon, rare, epic, legendary). Generic
    cards are tiered: the same card rolls a rarity and its number grows
    with it. Luck makes the rare ones likelier;
  - statuses: burn, poison and bleed hurt over time, chill slows (five
    stacks freeze), shock makes the enemy take 15% more from everything.
    Pips over an enemy show what it has;
  - spells from cards, up to 3, each levelling up to V: Orbiting Daggers,
    Ember Aura, Frost Nova (shown on the HUD);
  - four new cards per hero (the wizard's bolts can shock, the dwarf's
    axes bleed, the huntress marks the toughest enemy, the princess's
    colors carry statuses, the bard's beats push and chill);
  - REROLL (3 a run), BANISH (none yet: the Guild will sell them) and
    SKIP (heals 15%) under the cards: R / B / X, or Down then Enter;
  - XP now drops as gems where enemies fall: walk near to pull them in
    (Magnet widens the reach).

- loot and the Guild Hall (M15): every kill is worth loot (rune shards,
  shown flying into you), kept in full however the run ends. Spend it in
  the Guild Hall (title screen, or the game-over box): walk up to the
  guildmaster (upgrades for everyone), the trainer (each hero's own), the
  archivist (card unlocks) or a hero's statue (play as them), and leave
  through the dungeon gate. Prices and numbers: `design/GUILD.md`.

- the full card catalog and Guild Hall rev 2 (M16): all 101 cards of
  `design/CARDS.md` (12 spells and items -- wolves, runes, flasks, a storm
  cloud, totems, turrets, wards, thorns...; conditionals, trade-offs,
  triggers, combos and capstones), with no plain stat sold by two cards.
  The Guild Hall has long upgrade ladders and a tree of tricks for each
  hero; the archivist's shelves sell cards, spells, pacts (switched on at
  the dungeon gate, for a brutal run) and bestiary pages (or slay 25 of an
  enemy: +10% damage to its kind). Three achievements unlock cards.

- quests and the first boss (M17, `design/BOSSES.md`): every ring biome
  will have a quest whose giver waits at a camp, pinned on the minimap
  and big map from the start; finishing it wakes the biome's boss
  ("guardian") in its lair. Beat all 5 for the main quest, "Gain
  Adventurer's Glory" (the plains boss and its Glory come later). Built so
  far: the swamp. Walk up to the **frog hunter** (his hut sits just past
  the plains border) and press E (gamepad A); squash the five
  **psychedelic frogs** in his bog; then go to **Froggy's Pond**, a walled
  arena about 3 x 3 screens. Step in and the gate fills with thorns:
  **Froggy McFrogface** rises, a bullet-hell boss in three phases --
  tadpole fans, a tongue lash (red dotted aim line), belly flops (red
  landing ring; it sits dazed after each, the time to get close), then
  bubble spirals, dives between the pools (ripples show where it comes
  up) and croaking up toads, and finally a psychedelic phase of rainbow
  rain and closing rings. An arrow at the screen's edge points to it when
  it's off screen. Beating it opens the gate and pays out: 2,500 loot, a
  rare-or-better card offer, an achievement and two bestiary pages. The
  quest log sits under the HUD's top-left panel.

- the dodge roll (M18): every hero rolls on **Shift** (gamepad **B** or
  **LB**), about 4 tiles in a quarter second, toward where you walk (or
  your aim when standing still). Nothing can hit you mid-roll, but walls
  still stop you. One charge comes back every 5 s (the HUD's ROLL bar).
  Eleven roll cards: Quick Recovery, Extra Roll, Riposte, Slipstream,
  Close Call, Scorched Trail, and one per hero (wizard Blink, dwarf
  Shoulder Charge, huntress Backflip, princess Prism Dash, bard Drop the
  Beat). The old passive "dodge" stat is now **evasion**. Lingering only
  comes up once something of yours lasts. Three "lasts longer" spell
  levels became real ones (2 flasks, a chilling totem, piercing turret
  bolts). Once your build has 2 cards of one archetype, one card of
  every offer is from it (`design/CARDS.md` sections 6.10 and 14).

- multiple projectiles for every hero (M19): extra shots always fan out
  (at least 12° each), Echo's repeat comes out at an angle, Multishot is
  in the pool from the start and adds bolts to Fire Wand and Bone Turret.
  New cards: Cross Fire, Starburst, Rear Guard, Spiral, Twin Lanes, plus
  Sheet Music (the bard's beats fling notes, so the patterns work for him
  too), Split Arrow (the huntress's power, levels I-V like a spell),
  Double Rainbow (princess) and Twin Axes (dwarf). See `design/CARDS.md`
  sections 6.11 and 15.

- the wizard's arcane missiles (M20): 3 darts that fan out, then home on
  the enemy nearest your reticle. His old shock bolt is now his spell,
  Chain Lightning, and the lightning cards upgrade it. New cards: Seeker,
  Resonance, Mana Burst, Orbiting Darts and the capstone Arcane Storm. The
  trainer's lightning upgrades became missile ones, and anything you'd
  bought in them is refunded (`design/CARDS.md` section 16).

- the haunted forest (M21) replaces the old forest, whose pine thickets
  walled you in. Big gnarled trees stand apart, and only their trunks
  block; you walk under their branches. Stumps and fallen logs are the
  cover, over dead leaves, faint fog and floating wisp lights.

- boss pools and the Leech Swarm (M22): each biome's quest is now picked
  per run from its pool. The swamp has two: the frog hunter's (Froggy) and
  the leech doctor's (a stand-in quest: pop 5 bloated leeches). The **Leech
  Swarm** is 120 leeches with one health bar. They thin out as you hurt
  them, latch on and drain you if they reach you, and a **dodge roll
  shakes them all off**. It surges, splits and circles, spits blood, nests
  in the pools and, at the end, rings you in a tightening whirlpool
  (`design/BOSSES.md` section 12).

- Lady Proboscia (M22.2), the swamp's third boss. The smoke keeper wants
  4 of her old braziers lit around the swamp: stand by one for 5 seconds
  while mosquitoes swarm you, and it smokes for good. The **Lady** is a giant
  mosquito who flies over everything. Each bite that lands, and each sip
  at a pool, fills her belly. Full, she's **engorged**: slower, glowing,
  with a bar under her. Hit her hard enough before she digests it and she
  **POPS** (a big chunk of health, a ring of blood, stunned on the ground).
  She dive-bites, fans needles, rings you in closing buzz rings, calls
  mosquitoes, and at the end chains three dives that leave fever clouds
  (`design/BOSSES.md` section 13).

- harder bosses (2026-10-05): bosses lead their aim (some shots go where
  you're heading, so change direction), chain moves into combos from the
  second phase, and telegraph and rest less as the fight goes on. Lady
  Proboscia is much bigger and the Leech Swarm has 120 leeches crawling
  over each other (`design/BOSSES.md` section 5.6).

- every boss in every run (M22.5): all three swamp bosses are out there
  each run, their givers' camps and arenas at random spots in the swamp.
  The quests are hidden: nothing is pinned until a boss wakes, and doing a
  quest's job without ever meeting its giver wakes the boss too. A giver
  explains their quest and puts a counter for it on the HUD. One beaten
  boss per biome counts toward Glory; the others are bonus loot and
  achievements (`design/BOSSES.md` section 14).

- the journal (M22.6): the archivist's fifth shelf. Every quest whose boss
  you've beaten, with the giver's story, the boss, how many times, your
  fastest fight and the heroes who did it; `???` for the rest
  (`design/GUILD.md` 4.4b).

- Khepri the Dung Emperor (M23.1), the desert's first boss. Somewhere in
  the desert a scarab collector camps by an oasis; his golden scarabs run
  from you and dig in if you're too slow. Catch five and Khepri wakes in
  the Dung Pit, a sunken sandstone arena. He rolls a dung ball at you that
  grows as it goes: get a pillar between you and him and it shatters,
  stunning him. He also charges, burrows up under you, blows dust storms
  and calls scarabs (`design/BOSSES.md` section 15).

- Ol' Spitter, the Unmannered One (M23.2), the desert's second boss. A
  caravan master lost his cargo when his lead camel bolted, and mangy
  camels now sit on every bundle: run them off and take five bundles
  (the first "collect" quest). Ol' Spitter wakes in the caravanserai, a
  mud-brick yard with arcades, posts and stone water troughs. His humps
  hold his spit and shrink as he uses it. When they're dry he kneels at a
  trough to drink: hit him hard then, and smash the trough under his nose
  to make him choke. Smash them all and he's parched: no more drinking,
  but no more openings either. His ricochet loogie bounces off walls,
  arches and posts, splitting as it goes. He also spits fans and mortar
  loogies and gallops through the yard. Linger behind him and he kicks.
  Later he calls a stampede of ghost camels and sends heat-haze mirages
  of himself (`design/BOSSES.md` section 16).

- The Nameless Magus, Holder of Time (M23.3), the desert's third boss. His
  runaway apprentice wants his years back: the Magus hides behind sealed
  star circles scattered over the desert. Stand in a circle for 30 s to
  break its seal while sand elementals rise round you (the first
  "survive" quest). Break four and he comes up in the sunken
  observatory. He gains one signature per phase and keeps the earlier ones:
  - sand runes: run through one, or roll through it, to scuff it out.
    Scuff a whole batch and he's drained, kneeling;
  - shifting dunes: walls of sand and quicksand;
  - his hourglass: time zones that slow or speed everything but him.
    Shatter the glass before the sand runs out, or it's TIME'S UP.
  He also fires a sun lance (columns block it), sends homing sigils with
  blade fans, blinks, conjures a pulling vortex and calls a sand serpent
  (`design/BOSSES.md` section 17).

- The Fallout King (M24.1), the ruins' first boss, sized like the Magus
  (your difficulty target). A hazmat scavenger in the ruins needs four
  sensor beacons planted. Take her quest and she follows you to the sites
  and plants them, while glowing ghouls come for you; she can't be hurt
  (the first "escort" quest). He wakes in the reactor vault, and gains
  one signature per phase, keeping the earlier ones:
  - rads: a RAD meter on your HUD fills near him and from his attacks.
    Full, you're irradiated (a burn, no regen, a slow roll), so run for a
    decontamination shower;
  - fallout: patches you clear by smashing their isotope rods;
  - his meltdown core: shut all four coolant valves to expose it for
    triple damage, or hide behind a lead wall when it blows. The boss bar
    shows the core and the countdown.
  He also fires a turning gamma cross, hurls toxic barrels that leave
  slowing goo, calls ghouls, pulses EMP rings, sends homing skulls and dives
  between sewer grates (`design/BOSSES.md` section 18).

- The Snow King, King of Loneliness (M24.2), the ruins' second boss. A
  searching sister's people were frozen into ice blocks all over the
  ruins. Shatter a block, then stay close while the captive thaws, as
  frost wraiths drift in to re-freeze them (the first "rescue" quest).
  Four free, and he waits in his frozen throne hall. He gains one
  signature per phase, keeping the earlier ones:
  - his crown: burst him with damage and it flies off. Crownless he can't
    attack and takes extra damage, so kick it away to keep it that way;
  - black ice: you slide on it. Light the hall's fire braziers to melt it;
  - flash freeze: a CHL meter fills while you stand still or take his
    frost. Full, you're encased; roll three times to break out.
  He also fires shard fans and closing spike rings, sends penguin squads
  sliding past, breathes sweeping frost, drops icicles, and later calls a
  blizzard and rolls snowballs. The fires and the loose crown are pinned
  on the map, labelled, and pointed at (`design/BOSSES.md` section 19).

- Fragile, The Misunderstood (M24.3), the ruins' third boss. A pawn
  dealer stole her old teddy bear, Mr. Buttons, and lost him in four
  pieces, each guarded by vampire bats. Carry the pieces back to his stall
  and he sews the bear whole. It stays with you (the first "fetch"
  quest), and you carry it into her ruined ballroom. She gains one
  signature per phase, keeping the earlier ones:
  - sunlight: pull a lever to open a shutter. She burns in the shaft and
    is stunned if it catches her; she slams shutters closed;
  - shapeshift: a bat swarm (half damage except from the bard's pulse), a
    wolf (charges, howls, claws), or herself;
  - on the beat: a metronome; roll right on a beat to stagger her.
  Her own moves: riff rings, a bass-axe throw that comes back, slashes, a
  hypnotic gaze that pulls you in (break line of sight or stand in the
  sun), mist steps, thralls from her coffins (stake them shut) and
  falling chandeliers. Beaten, she sits down and cries. Give her back
  Mr. Buttons for five level-ups (`design/BOSSES.md` section 20).

Next up (agreed order, `design/BOSSES.md` section 8): the haunted forest's
bosses, haunted forest and
mushroom bosses one at a time, M27 the plains boss and the victory, and M28 an art spec so
custom pixel art can replace the drawn sprites.

## Setup (once)

From the project root (`EngineASCII/`):

```sh
python3 -m venv ascii_adventurers/.venv
ascii_adventurers/.venv/bin/pip install pygame-ce numpy
```

## Run

```sh
ascii_adventurers/.venv/bin/python ascii_adventurers/run.py
```

This works from any working directory. Debug: `run.py --ghosts N` (N up
to 3) adds bot players that wander off on their own and fight what they
meet; `run.py --dev --boss leech_swarm` (or `froggy`, `proboscia`, `khepri`, `ol_spitter`, `nameless_magus`, `fallout_king`, `snow_king`, `fragile`) points
the dev keys below at that boss's quest; F10 in game switches the view between players, and other players
show as coloured dots on the minimap and big map.
Developer mode: `run.py --dev` fills the guild purse (999,999 loot) and
in a run L levels you up on the spot (one card pick per press); F6 jumps
next to the dev quest's giver (the `--boss` one, else the first quest not
beaten), F7 finishes that quest (its boss wakes), F8 jumps outside its
boss's lair (walk in to start the fight). After a
boss falls, dev mode prints how long the fight took to the console. Nothing
bought and no records are saved in dev mode, so your real save stays as
it was.
- **Screen:** the grid is fitted to your screen's shape, so borderless and
  fullscreen have no black bars.
- **Sound:** plays on your operating system's default output device, unless
  you pick another one in Settings.
- **Saved data:** `ascii_adventurers/save/settings.json` (your settings,
  last hero and seed) and `save/records.json` (your best runs). Both are
  created on first use and ignored by git; delete them to start fresh.
  Broken or missing values fall back to defaults. The engine's own
  `settings.json` is not used.

Each run is a new island unless you type a seed on the hero screen; the
seed is shown in the HUD and on the game-over screen. Set `WORLD_MODE =
"test"` in `config.py` to play on the hand-made test map instead: walk
east out of the starting compound's gate to reach its shooting range.

### Controls

| Input          | Action                                                   |
|----------------|----------------------------------------------------------|
| WASD / Arrows  | walk (8 directions, same speed every way)                |
| Shift          | dodge roll: untouchable for the roll, 5 s per charge (gamepad: B or LB) |
| Left click     | attack (hold to keep attacking; the bard plays by himself) |
| Mouse          | aim (true angle; the amber ring is the exact aim point, brackets mark the tile under it); you face the mouse |
| E              | talk to a quest giver standing next to you (gamepad: A)  |
| M              | big map (pauses): wheel zoom, drag or WASD pan, C centre on you, M/ESC close; lists your quests |
| ESC            | pause menu: resume, settings, abandon run, quit          |
| R              | after you fall: go again (same hero, same seed if you chose one) |
| Left / Right, Enter | choose and take a level-up card (or hover and click)  |
| F11            | cycle window mode (everywhere; saved)                    |

**Gamepad** (any pad SDL knows, e.g. Xbox, PlayStation, Switch Pro, Steam
Deck): left stick walks, right stick aims (the reticle sits a few tiles out
that way and stays when you let go), right trigger or right shoulder
fires, B or the left shoulder rolls, Start pauses, Back opens the map
(left stick pans, shoulders zoom).
In menus the d-pad or left stick moves, A selects, B goes back. The game
switches between mouse and stick aiming by whichever you touched last.

Menus work with the keyboard (Up/Down, Left/Right, Enter, Esc), the mouse
and a gamepad. On the hero screen, Left/Right picks the hero and typing digits
sets the island seed (Backspace/Delete to go back to random).

## Building a standalone copy

```sh
ascii_adventurers/.venv/bin/pip install -r ascii_adventurers/requirements-dev.txt
ascii_adventurers/.venv/bin/python ascii_adventurers/packaging/build.py
ascii_adventurers/dist/AsciiAdventurers/AsciiAdventurers --smoke 8   # quick check
```

This makes `ascii_adventurers/dist/AsciiAdventurers/`, a folder (~90 MB)
with the game, the Python runtime and everything it needs. Players install
nothing. `--smoke N` starts a run, plays N seconds and quits with a report.
It never touches save files.

- **Saves:** a packaged game saves to the player's data folder
  (`%APPDATA%\AsciiAdventurers` on Windows, `~/.local/share/AsciiAdventurers`
  on Linux, `~/Library/Application Support/AsciiAdventurers` on macOS)
  instead of `save/`. Set `ASCII_ADVENTURERS_SAVE_DIR` to use another folder.
- **Each OS builds its own copy:** build on Windows for Windows, on Linux
  for Linux and the Steam Deck. GitHub Actions does both on every push to
  `main` (`.github/workflows/ascii-adventurers.yml`, logged in
  `ENGINE_CHANGES.md`). Download the results from the run's *Artifacts*.
- **Linux releases:** a Linux build only runs on systems whose glibc is at
  least as new as the one its Python was built against. This machine's
  Python needs glibc 2.44, which the Steam Deck and most distros don't
  have. Build releases with the portable Python instead:

  ```sh
  python3 ascii_adventurers/packaging/release_python.py     # once
  ascii_adventurers/.release/venv/bin/python ascii_adventurers/packaging/build.py
  ```

  That build needs only glibc 2.27 (2018). The build prints what it needs
  and leaves out the C++ runtime (`libstdc++`, `libgcc_s`), which every
  system has.

## Tuning

Every number is in **`config.py`**:
- heroes, enemy bodies and weapons (`HEROES`, `START_HERO`, `BODIES`,
  `WEAPONS`, defined as data via `specs.py`: shots with pellets/spread,
  pierce and chain; melee reach and arc; pulses), walk animation speed;
- terrain hit points, effect timings, sound volume, `VSYNC`;
- cards (`CARDS`: name, text, rarity, stack limit, which heroes, and the
  stat changes), rarity weights, XP per enemy and the level curve;
- camera smoothing (`CAMERA_FOLLOW_RATE`); the simulation clock
  (`SIM_HZ`, `MAX_STEPS_PER_FRAME`); players (`PLAYER_COLORS`, gamepad aim
  distance `PAD_AIM_DISTANCE`, enemy target stickiness
  `TARGET_SWITCH_MARGIN`);
- maps: minimap size and zoom (`MINIMAP_*`), big map zoom limit, zoom step
  and pan speed (`MAP_*`);
- sprite look (`SPRITE_PIXEL`); the pixel art itself is in
  `render/characters.py`;
- the island: `WORLD_RADIUS`, coastline and border shapes, the plains'
  size, the biome ring (`BIOME_RING`; set `BIOME_RING_SHUFFLE` and
  `BIOME_RING_ROTATE` to False for a fixed layout), and every feature
  density (trees, cacti, bogs, mushrooms, buildings...);
- streaming: chunk size, load/unload margins, generation time budget;
- drawing caches: terrain block size, how many blocks are kept and
  pre-drawn per frame (`TERRAIN_*`), rotated sprites kept (`SPRITE_CACHE_SIZE`);
- enemies (`ENEMIES`): hp, sight, speed, damage, wind-up times, which biomes
  each spawns in and how often;
- enemy density per biome (`BIOME_ENEMY_DENSITY`; difficulty is per biome),
  hearing radius, reaction time, aim error, and the infighting threshold.
- bosses: every boss's health and damage (`BOSS_HP_MULT`,
  `BOSS_DMG_MULT`), aim lead, combos, and per-phase tell/rest speed-up
  (`BOSS_LEAD*`, `BOSS_COMBO*`, `BOSS_TELL_SCALE`, `BOSS_REST_SCALE`);
  each boss's own moves are under its name (`FROGGY_*`, `LEECH*`,
  `PROBOSCIA_*`).

Colors are in `palette.py`.

## Tests

```sh
ascii_adventurers/.venv/bin/python -m unittest discover -s ascii_adventurers/tests -t .
```

(Run from `EngineASCII/`. The tests need no display.)

## Layout

```
run.py          launcher (path setup, bytecode-cache redirect, engine wiring)
config.py       all tunables            palette.py   game colors
specs.py        CharacterSpec / WeaponSpec / ShellSpec / EnemySpec data records
engine_ext/     camera.py (smooth pixel scrolling), input.py, sfx.py
                (synthesized sounds), screen.py (grid fitted to the screen),
                gamepads.py (SDL game controllers, menu keys)
players/        player.py (a player: hero, controls, camera, stats; the
                area kept alive around them), controls.py (keyboard+mouse,
                gamepad, auto-switching, debug ghost bot), progress.py
                (level, XP, rerolls), cards.py (offers and card effects),
                stats.py (the stat layer and damage buckets)
world/          layout.py (the island plan: which biome is where), hub.py
                (the Guild Hall's tiles and people),
                explored.py (what you've seen, for the maps),
                chunked.py (the island world, streaming, damage memory),
                generator.py (chunk generation), biomes.py, noise.py
                (seeded value noise, numpy), rng.py (deterministic hashing),
                tiles.py, test_map.py, landmarks.py (quest camps and boss
                lairs, stamped into the generated island)
entities/       actor.py (anything with hp), character.py (walking body
                with a weapon: hero and shooting enemies), weapon.py,
                projectile.py, effects.py, gems.py (XP gems)
ai/             brain.py (senses, memory, infighting), steering.py (clumsy
                obstacle avoidance), pathing.py (small local search when
                stuck), shooters.py (archer, warlock, ogre, tower),
                creatures.py, bosses.py (the boss framework: phases and
                moves; Froggy McFrogface)
systems/        collision.py (box vs tiles), raycast.py (grid walk for
                shots), combat.py (shots, pierce, chain lightning, melee
                swings, pulses, blasts, friendly fire, damage numbers),
                spawner.py (per-chunk enemy rosters), statuses.py (burn,
                poison, bleed, chill, shock), spells.py (card spells),
                zones.py (crackles, poison pools), run_rules.py (cards that
                react to kills, level-ups, hits; revives; pacts),
                quests.py (quest stages, givers, the sealed boss fight,
                rewards), patterns.py (boss bullet patterns)
render/         terrain.py (cached pre-drawn terrain blocks), glyphs.py
                (text pre-rendered to images for batched drawing),
                sprites.py (baked pictures, per angle), characters.py
                (pixel-art heroes and enemies, walk frames),
                enemies_sprite.py (creatures, tells), ascii_fx.py (shots,
                effects, numbers, bars as glyphs), spell_fx.py (gems,
                spells, status pips), bosses.py (bosses and their tells,
                quest givers, the boss banner and pointer)
ui/             hud.py, quest_log.py, card_picker.py, guild_panel.py (the hall's shops),
                crosshair.py, maps.py (minimap + big map),
                overlays.py (pause menu, game over), settings_panel.py,
                widgets.py (hero picker, seed field), logo.py, frame.py
scenes/         title.py, new_run.py (hero select), settings.py, game.py,
                guild_hall.py (the walkable hub),
                common.py (menu backdrop, F11, gamepad events)
meta/           settings.py (save/settings.json), guild.py (loot purse,
                upgrades, unlocks: save/guild.json), records.py
                (save/records.json), run_stats.py, files.py
app.py          services shared by the scenes (settings, records, sounds, pads)
save/           the player's settings and records (not in git)
assets/maps/    test_map.txt
design/         CARDS.md (the card catalog), GUILD.md (loot, upgrades,
                prices), BOSSES.md (quests, bosses, landmarks), the
                upgrade design guide
tests/          unittest suite
```

## Removing the game

1. Delete this folder: `rm -rf ascii_adventurers/`. The venv, bytecode cache and
   save data are all inside it, so nothing is left behind.
2. Optionally revert the engine additions made for the game. They are listed
   with revert steps in `../ENGINE_CHANGES.md`. They're general-purpose, so
   the engine keeps working if you leave them in.

The game never writes outside this folder: Python's bytecode cache is
redirected to `ascii_adventurers/.cache/`, saves go to
`ascii_adventurers/save/`, and the engine's `settings.json` isn't touched.
