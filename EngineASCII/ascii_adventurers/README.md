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
  Shoulder Charge, huntress Backflip, princess Prism Dash (Pirouette since P4), bard Drop the
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
  Double Rainbow (princess) and Twin Axes (dwarf) (P4 replaced both). See `design/CARDS.md`
  sections 6.11 and 15.

- the wizard's arcane missiles (M20): 3 darts that fan out, then home on
  the enemy nearest your reticle. His old shock bolt is now his spell,
  Chain Lightning, and the lightning cards upgrade it. New cards: Seeker,
  Resonance, Mana Burst (Implosion since P4), Orbiting Darts and the capstone Arcane Storm. The
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
  The quests are hidden: nothing is pinned until a boss wakes (since P2 the
  givers are pinned from the start), and doing a
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
  Her own moves: rings of rose petals, a parasol throw that comes back,
  slashes, a hypnotic gaze that pulls you in (break line of sight or
  stand in the sun), mist steps, thralls from her coffins (stake them shut) and
  falling chandeliers. Beaten, she sits down and cries. Give her back
  Mr. Buttons for five level-ups (`design/BOSSES.md` section 20).

- Art pass (M24.4). The Snow King is now the Frost Hermit: hunched in grey
  furs, eyes glowing in a pointed cowl, a braided frost beard, an ice-root
  staff and an iron-and-ice crown. Fragile, her wolf form and her crying
  pose are repainted too: white hair, a black gothic gown, and a black
  lace parasol instead of her bass-axe.
  These figures are painted from shapes like the camels
  (`render/painted.py`). Mr. Buttons rides on his carrier's head
  until he's given back, then Fragile hugs him (`design/BOSSES.md`
  section 21).

- Boss movement (M24.5). The Snow King glides round his hall on the ice,
  and Fragile circles you. They keep moving between moves and, slower,
  during most of them (`design/BOSSES.md` section 22).

- Nettle, the Blighted (M25.1), the haunted forest's first boss. A hedge
  witch asks you to cleanse the forest's blighted shrines: stand in a
  shrine's ring (it tightens as it cleans) while blighted sprites attack.
  Four clean, and the corrupted pixie waits in her withered glade, ringed
  with giant toadstools. She gains one signature per phase, keeping the
  earlier ones:
  - glamour: she splits into copies that fly and cast with her; only she
    casts a shadow, and a hit pops a copy into dust;
  - shrinking dust: linger in her dust and you shrink (faster, weaker,
    knocked about) until you stand on a growcap;
  - blight: rot seeds spread a patch that hurts you and heals her; pull
    them.
  Her own moves: glitter spirals, homing hex sparks, thorn lines, a
  bramble cage, rot moths, dive-bombs, flung wisps and nettle rain
  (`design/BOSSES.md` section 23).

- Playtest pass, P1 + P2 (`design/BOSSES.md` section 24):
  - a smaller island: the radius is 20% shorter (2761 -> 2209 tiles, ~36%
    less land; ~4.3 min from the centre to the coast). Same shape, every
    biome smaller by the same share;
  - 4x the quest targets: every quest that needs a number of things puts
    out four times that many (5 golden scarabs needed -> 20 out there;
    any 5 do);
  - every quest giver is on the map from the start: a round pin in its
    biome's colour (swamp lime, desert amber, ruins ice blue, forest mint,
    mushroom pink), named on the big map, grey once its boss is beaten.
    The minimap shows a giver when it's inside the box. Arenas are still
    pinned when their boss wakes. Map labels no longer overlap;
  - a taken quest's targets show on the minimap and the big map once
    you're in their general area: within 250 tiles of you (was 160).
- Playtest pass, P3 (`design/BOSSES.md` section 24.2): XP gems are pulled
  in from 3.75 tiles (was 1.5; Magnet cards and the Lodestone still add
  their % on top), and every level past the first adds 1% move speed, up
  to +20% at level 21 (it adds to Swift Boots and the Cobbler).
- Playtest pass, P4 (`design/CARDS.md` section 17): no more doubles. Eight
  hero cards that did what a general card does are gone, each replaced by
  one only that hero could have:
  - dwarf: Hang Time (an axe hovers where its throw ends, hitting again),
    Tether (a chain to each axe in flight cuts what it crosses),
    Splitting Axe (the axe comes home as two halves);
  - princess: Converge (her colors curve in and cross at your aim),
    Pirouette (a roll spins a ring of 10 colored shots);
  - huntress: Arrow Rain (every 5th shot, 6 arrows rain where you aim);
  - wizard: Phase Darts (darts fly through walls and trees; a save that
    bought Overload gets it), Implosion (a dart's hit drags enemies in).
- Playtest pass, P5 (`design/BOSSES.md` section 24.3): difficulty levels,
  picked on the hero select under the heroes: Wanderer (the game as it
  was), Knight, Folk Hero, then Hero of Legend I-VIII. Each level makes
  every enemy and boss x1.3 tougher and x1.15 harder-hitting (compounding:
  x13.8 HP and x4 damage at the top), adds 20% more enemies and 40% more
  loot (x3 enemies, +400% loot at the top). It all comes on top of player
  levels, pacts, Beacon and Bounty. Beating any boss on a level opens the
  next (saved with the guild); `--dev` has them all open. The pause menu
  and the game-over screen show the run's level.
- Playtest pass, P6 (`design/BOSSES.md` section 24.4): mounts. Q (gamepad
  Y) whistles for your hero's own mount: the wizard's flying carpet, the
  dwarf's war ram, the bard's donkey, the princess's white pony, the
  huntress's stag. A second later you ride, 75% faster. It's for travel:
  attacking or rolling hops you off (the attack or roll still happens),
  the bard's lute stays quiet in the saddle, a hit throws you off (10 s
  before it comes back; the HUD's MNT bar shows the wait), Q again hops
  off, and there's no riding in a boss arena. The guild's Stable makes it
  faster and back sooner. `config.MOUNTS_ON = False` switches it all off.
- Playtest pass, P7 (`design/BOSSES.md` section 24.5): the plains go from
  5 enemy kinds to 19, all drawn like the heroes, every attack with a tell
  (a red "!" over a wind-up, a dotted line before a charge):
  - simple chasers: field rats (packs of 4-6), shambling farmhands, angry
    geese (gaggles of 3);
  - wild hounds (packs of 3, they circle and take turns darting in), the
    hawk (circles over everything, lines up, dives), the molehill (sends
    out mole rats until you break it), the rampaging bull (elite: charges
    through anything that breaks, again and again);
  - the bandit slinger (bursts of 3 stones), the lancer (a bandit on
    horseback who gallops through you), the shieldbearer (elite: nothing
    gets past the shield from the front; open after a bash), the field
    priest (heals the most hurt enemy near it);
  - the straw golem (dies in burning straw), the scarecrow (lets loose
    crows), the war drummer (everyone in its ring is faster and hits
    harder).
- Playtest pass, P8 (`design/BOSSES.md` section 24.6): the haunted forest
  goes from 4 enemy kinds to 18, drawn like the heroes, every attack with a
  tell:
  - simple chasers: skeletons (they fall into a bone pile that pulls itself
    back together once; break the pile), rotting woodsmen, spiderling
    swarms, bats (wobbly, over everything);
  - the banshee (breathes in, screams in a cone that pushes you back), the
    phantom (drifts through trees, only solid when it glows), the grave
    digger (the ground cracks where he's digging up a skeleton), the
    headless knight (elite: three swings in a row; hit its floating head
    to stagger it);
  - the giant centipede (shoot it apart and each half crawls on), the
    giant spider (spits webs that slow you);
  - the ghost woodcutter (an axe that comes back), the cultist (skeletons
    rise from its candle ring: shoot the candles), the witch's apprentice
    (an orb that splits in four), the wendigo (elite: lunges in pairs, a
    howl that slows you).
- Playtest pass, P9 (`design/BOSSES.md` section 24.7): the desert goes from
  5 enemy kinds to 20, drawn like the heroes, every attack with a tell:
  - simple chasers: fire ant swarms, dried husks, sand imps (they hop),
    desert jackals;
  - the giant scorpion (elite: armoured in front; two pincer snaps, then a
    long tail stab), vultures (circle until you're under half HP, then
    dive), the basilisk (stares down a line: caught in it, you're stone
    for a second), the rattlesnake (rattles when you're close, strikes,
    slithers off);
  - the mummy (elite: its bandages drag you in for a heavy blow; roll to
    break free), the fire dancer (a cone of flame, burning patches), the
    glass mage (shards that glance off walls), the dune raider (hit and
    run);
  - tumbleweeds (roll with the wind), the cactus golem (shoots spines back
    every time you hit it), the djinn lamp (its vortex drags you in; close
    up it zaps).
  Also fixed: the plains' straw golem's burning straw now hurts heroes (it
  only burned other enemies).
- Playtest pass, P10 (`design/BOSSES.md` section 24.8): the ruins go from
  5 enemy kinds to 19, drawn like the heroes, every attack with a tell:
  - simple chasers: gnoll packs, stone imps, crawling hand swarms, lost
    soldiers;
  - the gargoyle (swoops when you come near, then sits as stone: nothing
    hurts it), the clockwork sentry (winds its key, sweeps 5 bolts), the
    colossus (elite: its stomp rolls a ring along the ground; roll through
    it), the rubble crab (break its shell first; bare, it runs);
  - the gem thief (runs off with your XP gems; kill it to get them back),
    the crossbow sniper (a long aiming line, then a bolt through
    everything), the flail brute (elite: a spinning flail whose ring
    grows, then it flies);
  - the rune mine (drifts at you, glows, blows), haunted blades (three
    swords circling, thrusting one at a time), the bell ghost (its bell
    wakes everything around and knocks you back).
- Playtest pass, P11 (`design/BOSSES.md` section 24.9): the swamp goes from
  3 enemy kinds to 15, drawn like the heroes, every attack with a tell:
  - simple chasers: bog zombies, newt swarms, gator hatchling packs,
    mudskippers (they hop);
  - the bog crocodile (elite: lies with its eyes above the bog, lunges,
    clamps on and drags you; roll to break free), the snapping turtle
    (hides in its shell when hurt), the heron (stabs a line from 3 tiles,
    flaps off if you close in);
  - the swamp hag (curses the ground under you: step out of the puddle or
    be rooted), lizardman javelineers (their javelins stick in the ground
    as obstacles for a few seconds), marsh lights (three lights, one real:
    shoot it and the others go out);
  - the bloated corpse (bursts into a lingering toxic cloud), the sludge
    (splits in two when it dies, and again).
- Playtest pass, P12 (`design/BOSSES.md` section 24.10): the mushroom biome
  goes from 3 enemy kinds to 16 (no red-and-white caps: those are the
  Mycelium bosses'):
  - simple chasers: sporeling swarms, fungus gnat clouds, shroomlings, mold
    zombies;
  - the myconid shaman (its pollen cloud heals the enemies in it), the
    cordyceps hunter (spore darts; dead, two sporelings crawl out), the
    fungal brute (elite: regrows unless you keep hitting it), the
    rootweaver (a line of cracks races at you, roots burst along it);
  - the giant snail (its shell takes half; its slime slows you), the
    pillbug (rolls at you as a ball, barely hurt, then rests: hit it
    then), the mantis (elite: leaps at you, then an X-slash);
  - the fairy ring (step inside and sporelings rise; break three caps),
    the mold core (spreads mold patches that hurt; break it and they
    wither).
  That ends the playtest pass's enemy variety: 12 kinds that spawn became
  94 (the plains 19, the haunted forest 18, the desert 20, the ruins 19,
  the swamp 15, the mushroom biome 16).

- Love & Cuddles (M25.2), the haunted forest's second boss. A forester
  asks you to follow trails of nut shells to a squirrel's caches and smash
  four of them (rabid squirrels guard each, and more burst out). Then a
  round, fluffy pink squirrel with a heart-patterned bow -- and a cleaver
  behind its back -- comes out of the hollow oak. It gets less adorable as
  the fight goes on (matted fur, blood, a twitching red eye, a widening
  grin). Its signatures, kept as they stack:
  - the hoard (all fight): it buries acorns round you and runs back to dig
    them up; each one makes it faster and harder-hitting. Walk over a
    mound first to steal it;
  - treetops (phase 2): it climbs the big oaks, out of reach, pelting
    acorns and leaping tree to tree. Shoot its tree (trunk or crown) to
    shake it out, hurt and dazed;
  - tripwires and frenzy (phase 3): glinting wires between the oaks swing
    a log along them when you walk across (a roll hops them; a shot cuts
    them), and a madness meter that, full, sends it on zigzag cleaver
    dashes before it collapses, panting and wide open.
  Its own moves: the cleaver spin, acorn barrages, pinecone bombs and its
  squirrel gang (`design/BOSSES.md` section 25).

- The Fallen (M25.3), the haunted forest's third boss. A lumberjack asks
  you to fell the trees he marked with red paint; some are mimic saplings
  that rip free and fight. Four felled, and a tall, thin, branchy tree
  with one big eye waits in the still grove, among forty trees that look
  just like it. Its signatures, kept as they stack:
  - which tree? (all fight): it becomes one of the trees near you; find
    it by its eye opening now and then. Shoot a fake and it spits back;
    hit the real one and it's dragged out, dazed;
  - root web (phase 2): roots grow out in lines and grab whoever steps on
    one; shoot the root holding you, and keep near the fire bowls, which
    burn roots away;
  - swallow & spit (phase 3): its trunk splits into a maw that swallows
    your shots and spits them back, unless you stuff it until it chokes.
  Its own moves: branch sweeps, uproot charges, leaf storms, and sap
  puddles with bark beetles (`design/BOSSES.md` section 26).

- Mycelium (M26.1), the mushroom biome's boss -- always just "Mycelium",
  but really one of three mushrooms, and you only find out which in the
  fight. All three share one quest, word for word: sever four Mycelium
  nodes (stand on one while sporelings crawl up the threads); only what a
  severed node spills hints at what waits. The first, the **fly agaric**:
  a huge red-capped toadstool in its fruiting ring. Its signatures, kept
  as they stack:
  - warts (all fight): white warts armour its cap; shoot them off (each
    falls as a toadstool that puffs); it drinks from the ground to regrow
    them;
  - the mycelial network (phase 2): it sinks and travels the glowing
    threads between its rings (the way lit first; a lit thread burns),
    erupting near you; break a ring's node to cut it out for a while;
  - trip spores and the fly lure (phase 3): linger in its spores and you
    trip (you drift, and see fake shots; a roll clears it); flies circle it
    as a shield, bursting as they drop dead.
  Its own moves: cap slams, spore volleys, toadstool sprouts and the stem
  spin (`design/BOSSES.md` section 27).

- Mycelium, the shaggy ink cap (M26.2): the mycologist gives the same quest
  (its severed nodes spill ink). A tall white shaggy cap whose hem melts
  into black ink, more of it each phase. Its signatures, kept as they
  stack:
  - ink pools (all fight): it melts into a pool and flows to a bubbling
    spot (shown first), slowing and stinging what it runs over, leaving
    puddles;
  - ink blots (phase 2): stand in a blot and you can't see beyond a few
    tiles until you roll;
  - scrawl and clusters (phase 3): it writes a word across the floor
    through you, letter by letter -- then the letters burst in order, or
    rise as ink imps; little ink caps push up round you and melt into
    pools unless you break them.
  Its own moves: scale volleys, ink spray, bursting up under you and the
  shaggy shake (`design/BOSSES.md` section 28).

- Mycelium, the giant puffball (M26.3): the forager gives the same quest (its
  severed nodes puff dust). A huge round white puffball with a crack of a
  mouth, cracking open as it's hurt. Its signatures, kept as they stack:
  - the puffball minefield (all fight): little puffballs scattered round
    you; walk near one and its fuse lights, shoot one and it pops, in a
    chain -- and a pop next to it staggers it;
  - bounding (phase 2): it leaps about between its moves (a ring shows
    where it lands);
  - spore wind and split (phase 3): a turning wind drifts its breathed-out
    spore clouds across the field (stand upwind, or behind boulders); it
    splits in two, the halves bounding at you on one shared health bar,
    then rolls back together.
  Its own moves: rolls, puff rings, spore mortars and the squash
  (`design/BOSSES.md` section 29).

- The plains boss and the victory (M27). Every run now starts outside a
  walled necropolis at the island's centre, its gate sealed with bone. Beat
  a guardian in each of the five ring biomes and it opens: inside (500 x 200
  tiles) waits **More than Life**, a hooded necromancer, much harder than
  any ring boss -- and beaten once, he rises again as **More than Death**,
  the lich, with a full second life:
  - his first life: raised dead from every corpse (crush them first),
    corpses that burst, walls of bone round you, a death's gaze sweeping the
    graveyard (hide behind graves), and his legion -- archer volleys and a
    shielded phalanx marching through you;
  - his second life keeps all of that, and adds a soul storm that drags you
    in, souls spilled by your wounds that power him (grab them first),
    possession (find which of his dead he's hiding in) and bone cages.
  His moves: bone spears, skull fire, grasping hands, the scythe reap.
  Beaten for good, he gives **Adventurer's Glory**: end the run as a victory
  from the pause menu whenever you like, and walk on water
  (`design/BOSSES.md` section 30).
- **Gear, M28.1** (`design/GEAR.md`, section 15): the cards became gear.
  You start a run wearing nothing; every level is a gear pick: three
  pieces, each a new piece for an empty slot, +1 to one you wear, or a swap
  (what comes off goes to your bag) -- or UPGRADE (U): +1 to any piece you
  wear, on its own screen. Ten slots: main hand (your hero's own weapon
  line), off-hand (shot patterns), head (statuses), chest (defence), feet
  (the roll), two rings (triggers, economy) and three trinkets (spells; the
  Arcane Wing adds a fourth). A piece is a power -- a card's effect -- plus
  plain stat lines by rarity (the old stat cards), and grows to +9: each
  +1 adds 10% to its power (a spell's first four are its levels II-V).
  Tab (pad X, or the pause menu) opens your gear: wear a piece from the
  bag (not inside a boss arena), salvage anything for loot; the bag is
  salvaged when the run ends. Arcane Mastery and Weapons Master are gone:
  damage is "+damage" or "+elemental damage" now.
- **Tricks, M28.2a** (`design/GEAR.md` 17): a piece at +3, +6 and +9 learns a
  trick (+9 is its MASTERY). The off-hand's 24 are in: the Compass Orb's
  cross turns and cuts enemy shots, the Sunwheel's rings curve and come
  twice, the Hindsight Orb watches your back, the Nautilus Shell's spiral
  grows and doubles, the Twinned Quiver links enemies and drifts into three
  lanes, the Canyon Horn's echo picks its own target and comes three times,
  the War Drum shrugs off slows and dazes, the Pepperbox splits twice and
  flashes. Fixed: a Frenzy lasted 0.015 s instead of 3 s since M25.2.
- **Tricks, M28.2b** (`design/GEAR.md` 17.2, 17.12): the head's 33. Fire
  blinds and builds into a pyre, burning enemies' shots slow; poison roots,
  ticks faster and eats a share of HP, and toxic ground can't hurt you;
  frozen enemies become walls that chill their neighbours and shatter into
  flying shards; shock builds up, conducts through water and calls lightning
  from the sky; bleeds stop healing, execute, scare and show on the minimap;
  Thermal Shock bursts burn, widen and repeat; Toxic Current shocks, charges
  a shocking attack and spreads to everyone near.
- **Tricks, M28.2c** (`design/GEAR.md` 17.3, 17.13): the feet's 33, all on
  the roll. Ripostes disarm and kill for your roll back; slipstreams slip
  through bosses, leave a decoy and last while you run; rolling through
  shots heals you, throws them back and makes you untouchable; fire trails
  creep, flare and burn longer; walking charges your attacks and cracks the
  ground; crits speed you up and, fast enough, you skim over every ground
  attack; Blink leaves a nova behind, swaps places and storms three times;
  the dwarf's charge bowls enemies, breaks walls and rampages on; the
  huntress flips twice and shoots twice as fast mid-roll; the princess
  spins an encore and makes enemies miss; the bard drops two beats, surfs
  the crowd and leaves an amp behind.
- **Tricks, M28.2d** (`design/GEAR.md` 17.4, 17.14): the chest's 33. Thorns
  bleed, grow a bramble ring and spread to the crowd; the ward shocks when
  it breaks, overcharges you and doubles up; heavy plate tempers, sheds its
  weight and anchors; the glass coat shows where shots are going, blocks a
  hit and goes diamond; grudges throw you clear, build up and seethe; the
  spotless tunic gets you away, shrugs off the ground and stays half-clean;
  the wolfpelt thickens, rages and makes a last stand; the bastion heals,
  garrisons walls and counts your shield; Mountainhide glances shots and
  shakes the ground; the aegis radiates, bursts and refills; the phoenix
  leaves a ring of fire, rises untouchable, and rises twice.
- **Tricks, M28.2e** (`design/GEAR.md` 17.5, 17.15): the rings' 42. Kills
  go off with a bigger bang, in fuse lines and dominoes that leave gems;
  the reaper heals more for elites and streaks; level-ups hit, upgrades
  surge and every 5th level gives a pick; bloodlust feeds, fades slowly
  and makes you bleed them; the slingstone topples giants and bosses; the
  veteran's levels count twice, give free upgrades and max HP; the hoard
  counts salvage, buys armor and has no cap; bounties pay double for
  elites, bag gear and stop the haste; the beacon's extras give more XP
  and come straight at you, with a wave every minute for a pick; the
  fourleaf makes offers rare, rerolls and holds 5; crits brim, splash and
  pile up; statuses spread farther, stronger and from the living; and the
  pack hunts what you hit, its turrets come back, and the wolves defend you.
- **Tricks, M28.2f** (`design/GEAR.md` 17.6, 17.16): the trinkets' 33. The
  chain bolt grounds, overloads and arcs back; the daggers fling out on a
  roll, breathe and split into two rings; the ember aura warms you, flares
  and grows with the burning; the frost nova answers hits, armors you in ice
  and freezes in an avalanche; wolves follow your scent, howl enemies weak
  and grow dire; runes link up, seek and burst on a roll; flasks bubble,
  brew fire, frost or shock, and merge in a cauldron; the storm rains a
  puddle, strikes back at whoever hit you and brings a second cloud; the
  totem cleanses, follows you and stays; the lantern lights foes up, goes
  for the burning and leaves wisps; and turrets rise from your kills,
  burst into bone and stand as a legion.
- **Tricks, M28.2g** (`design/GEAR.md` 17.7, 17.17): the wizard's main hand,
  30. Darts conduct off what your bolt hit, lightning jumps through walls,
  never fades and strikes a long chain twice over; bolts shock round their
  hits and cast twice in a storm; crackles stick to enemies, follow every
  jump and roll as a thunderball; darts haunt through walls, slip past
  shields and see through walls; they speed on, hunt the weakest and hunt
  on; resonance lasts, rings and goes to +120%; the well crushes, drags
  shots and opens a singularity; the storm's new darts come for whoever's
  near you, five a cast or without end; and orbiting darts hit the
  planets they pass, swing twice and come back faster. (Also fixed: Storm
  Caller's extra jump no longer reaches the darts.)
- **Tricks, M28.2h** (`design/GEAR.md` 17.8, 17.18): the dwarf's and the
  huntress's main hands, 36. Axes bank harder off walls, pinball off big
  enemies and carom home; hovering axes saw, stay up while you hold the
  attack and buzz round; axes home in on the way back, quicken your
  throws and crit coming home; the chain pulls taut, shackles and flails
  round you; the whirlwind hunts the toughest, rethrows twice and throws
  two; split axes reunite, cross in an X and quarter. Arrow rain falls on
  the nearest enemy, thunders when it bunches and comes twice; broadheads
  speed up, run back through and hit harder; marks linger, jump to the
  next quarry and spread through the pack; standing still you hold your
  breath, find zen and keep your aim; crits follow through, come every
  6th arrow and strike like lightning; and split arrows seek, split on
  walls and sow thorns.
- **Tricks, M28.2i** (`design/GEAR.md` 17.9, 17.19): the princess's and
  the bard's main hands, 36, the last of the 300. A full spectrum crits,
  its bonus glows on and grows; the middle color hits harder, the fan
  narrows while you stand still and becomes a beam; colors' statuses come
  more often, twice, and hurt more together; up close hurts more, a duel
  begins and point blank reaches farther; split pieces seek, grow and
  split again; the colors' crossing hurts, comes twice and follows an
  enemy. The crescendo holds through a miss, reaches farther at the top
  and goes to +100%; five beats in a row put an enemy to sleep, healing
  you can't use powers the next beat, and the lullaby heals more; the
  loud beat comes sooner, every 3rd beat is both and the drop is bigger;
  pushes into walls hurt, chilled enemies fly farther and chill twice;
  finales open a fight, answer a drop below 30% HP and come every 6th
  beat; and notes fly round walls, come in a chorus and splash.
- **Rarity and the STATS page, M28.3a** (`design/GEAR.md` 7, 18): rarer
  pieces have stronger powers (x1.15 uncommon up to x2 legendary, on top
  of the level's growth; powers with no number get +7.5% to +50% damage).
  Legendaries sparkle. On the gear screen, I (pad Y) shows the STATS page:
  each weapon and spell's damage worked out step by step, then every
  total stat.
- **Legendary tricks, drafted (M28.3b)** (`design/GEAR.md` 19): each of
  the 100 pieces has a legendary trick that breaks one rule of its power,
  on from +0 when the piece is legendary. All approved; they're built
  slot by slot from M28.3c.
- **Legendary tricks, batch 1 (M28.3c)** (`design/GEAR.md` 19.12): the 11
  pieces that only come as legendaries have theirs. Crit kills spill
  their leftover damage on, dying enemies leave status clouds, turrets
  fire your own attack, small hits bounce off armor, healing fills the
  Aegis shield, a used Phoenix rise comes back after 150 kills, enemies
  your dart marked fire darts however they die, axes leap to an enemy
  before coming home, the Farsight Bow leans the view toward your aim,
  the princess's colours split enemy shots into her own, and the bard's
  finale cashes in what the beats banked.
- **Legendary tricks, the off-hand (M28.3d)** (`design/GEAR.md` 19.13): the
  cross fires on its own, the starburst goes off where the 10th attack
  lands, the rear shot comes from behind the enemy, the spiral shot sweeps
  round you, twin shots are whole, an echo's kills count twice, a frenzy
  speeds up spells, summons and rolls too, and each attack splits the
  shots still flying.
- **Legendary tricks, the head (M28.3e)** (`design/GEAR.md` 19.14):
  burning enemies leave fire where they walk, enemies near a burning one
  count as burning, poison ticks crit, poison stacks without a cap,
  bosses can freeze, chilled deaths shatter, shocked enemies' hits fizzle
  half the time, bleeds heal you, your moving speeds your bleeds, any two
  statuses burst, and a shock spreads every status.
- **Legendary tricks, the feet (M28.3f)** (`design/GEAR.md` 19.15):
  being hit readies a riposte, the slipstream's speed is attack speed too,
  shots passing near you count as close calls, your fire burns up enemy
  shots, speed cuts the damage you take, moving gives a second crit roll,
  blinks go where you aim, the dwarf's charge shoves bosses, the
  huntress's roll vaults walls and water, standing still spins the
  princess's ring, and the bard's free beat runs on as a wave.
- **Legendary tricks, the chest (M28.3g)** (`design/GEAR.md` 19.16):
  thorns hurt whatever presses close, the ward stops a whole hit, the
  anvil caps what you lose in a second, the glass coat's lost HP becomes
  speed, the grudge shockwave also goes off at the attacker, a kill heals
  you back to 90%, the berserker's bonus fades slowly, and max HP gives
  armor.
- **Legendary tricks, the rings (M28.3h)** (`design/GEAR.md` 19.17):
  enemies explode while alive after 10 hits, explosions that kill nothing
  jump, kills grow max HP, surges come at each quarter of the XP bar,
  elite and boss damage builds Bloodlust, crowds count as giants, close
  calls leave you stronger, the Guild's purse feeds the hoard, a wanted
  enemy pays a bounty, Beacon's extras come as elites, and the next
  level's offer can be seen (and a piece of it kept) early.
- **Legendary tricks, the trinkets (M28.3i)** (`design/GEAR.md` 19.18):
  crits cast chain bolts, the daggers circle your target, the ember aura
  stays behind when you roll, frost novas leave ice, wolves run through
  walls, runes come back, pools last while enemies stand in them, the
  storm cloud drifts ahead, the totem heals you from afar, fire bolts
  stay burning on their enemy, and turrets walk.
- **Legendary tricks, the wizard's staffs (M28.3j)** (`design/GEAR.md`
  19.19): lightning forks on its first jump and jumps any distance on
  screen, bolt shocks last for good, darts crackle where they hit, a
  dart's kill rises as a ghost that fights for you for 5 s, homing darts
  have no range, Resonance counts across a crowd, Implosion drags toward
  your aim, and missed darts wait in orbit for the next enemy.
- **Legendary tricks, the dwarf's axes and the huntress's bows (M28.3k)**
  (`design/GEAR.md` 19.20): bounces aim at enemies, the hovering axe
  drifts after them, you steer the axe home through your aim, axes in
  flight are chained to each other, split halves swing out wide, the rain
  keeps falling, arrows widen as they pierce, a roll calls the mark,
  moving straight counts as standing still, and split arrows curve back.
- **Legendary tricks, the princess's wands and the bard's lutes (M28.3l)**
  (`design/GEAR.md` 19.21; with these, all 100 pieces have one): Prism
  counts every hit of an attack, the fan sets its own width, a violet
  color bleeds, attacks carry the princess forward, the colors' crossing
  glows, the crescendo powers spells and summons, the lullaby heals for
  enemies near the beat, holding the attack plays loud beats, every 3rd
  dissonant beat pulls, and notes soften enemies for the beats.

Next up (agreed order, `design/BOSSES.md` section 8): the rest of M28, the
gear system (building the legendary tricks, drops from elites, chests and bosses,
boss uniques, gear on the heroes), M29-M32 the four ocean zones (each with its own enemies, quest
and boss), M33 the kill order and the final bosses, M34 extra quests (NPC
side quests, more ring quests), M35 a balance pass (known items in
`design/BOSSES.md` section 31), and last, M36 an art spec so custom pixel
art can replace the drawn sprites.

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
in a run L levels you up on the spot (one gear pick per press). The dev
keys act on the "dev quest", named on the DEV bar at the bottom: at first
the `--boss` one, else the first quest not beaten; F5 picks the next quest
(through all of them, then round again). F6 jumps next to its giver, F7
finishes it (its boss wakes), F8 jumps outside its boss's lair (walk in to
start the fight), F9 jumps to its nearest target still to do. F4 (also with
the big map open) switches on the big map's every-target view: every
quest's targets, anywhere (only the dev quest's are labelled). It's off at
first, so dev play's maps look like a normal run's. After a
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
| Q              | whistle for your mount / hop off (gamepad: Y)            |
| M              | big map (pauses): wheel zoom, drag or WASD pan, C centre on you, M/ESC close; lists your quests |
| ESC            | pause menu: resume, settings, gear, abandon run, quit    |
| Tab            | your gear: the ten slots and the bag (gamepad: X)         |
| R              | after you fall: go again (same hero, same seed if you chose one) |
| Left / Right, Enter | choose and take a level-up piece (or hover and click); U upgrade, R reroll, B banish, X skip |
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
- cards (`CARDS`: the powers and plain stats -- name, text, rarity, stack
  limit, which heroes, and the stat changes), gear (`GEAR`: each piece's
  name and slot; `GEAR_*` level growth, affixes by rarity, bag size,
  salvage), rarity weights, XP per enemy and the level curve;
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
                (level, XP, rerolls), gear.py (slots, pieces, the bag,
                gear offers), cards.py (the powers' effects and gates),
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
                painted.py (big figures painted from shapes: the Frost
                Hermit, Fragile, Mr. Buttons, Nettle, Love & Cuddles,
                The Fallen, the three Mycelium, More than Life),
                enemies_sprite.py (creatures, tells), ascii_fx.py (shots,
                effects, numbers, bars as glyphs), spell_fx.py (gems,
                spells, status pips), bosses.py (bosses and their tells,
                quest givers, the boss banner and pointer)
ui/             hud.py, quest_log.py, gear_picker.py (level-up picks),
                gear_screen.py (Tab: your gear), guild_panel.py (the hall's shops),
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
design/         CARDS.md (the card catalog: gear's powers), GEAR.md (gear), GUILD.md (loot, upgrades,
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
