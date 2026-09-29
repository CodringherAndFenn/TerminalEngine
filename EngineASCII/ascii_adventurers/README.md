# AsciiAdventurers

A top-down ASCII adventure roguelike on one huge island, built on the
narrative engine (`narrative_engine/`). Everything for the game lives in
this folder.

**Status:** Milestones 1-8 and "Adventurers" are done:
- keyboard walking, mouse aiming, a smooth scrolling camera;
- shooting, spells and destructible terrain;
- a seeded, chunk-streamed world with six biomes;
- enemies and combat, with 100 hp;
- the island (M5): open plains in the middle, the other five biomes
  (forest, desert, ruins, swamp, mushroom) as equal slices of a ring around
  them, then the coast and endless ocean. The ring is dealt and rotated
  differently every run;
- maps (M6): a minimap in the top-right corner and a big map on M. Explored
  ground shows real terrain; the rest of the island shows as a dimmed biome
  outline;
- adventurers: you play a hero (wizard, knight, bard, princess or
  huntress). All share a placeholder magic bolt for now; each gets their
  own attack later;
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
  Solo play looks the same as before; co-op itself comes later.

The look: heroes and enemies are pixel-art sprites; everything that flies
or pops up (bolts, arrows, hits, damage numbers, health bars) is drawn with
text characters, like the terrain.

The enemies:
- goblin archer, warlock (red aiming beam before it casts), spell tower
  (ruins), and ogre (armored front, throws rocks that break walls);
- burrower (desert), spore puffer (mushroom), fallen warrior (plains).

Enemies use Noita-style clumsy AI, and friendly fire and infighting are on.
Next up: hero weapons (M10), then XP and cards (M11).

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
meet; F10 in game switches the view between players, and other players
show as coloured dots on the minimap and big map.
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
| Left click     | attack (hold to keep firing); unlimited                  |
| Mouse          | aim (true angle; the amber ring is the exact aim point, brackets mark the tile under it); you face the mouse |
| M              | big map (pauses): wheel zoom, drag or WASD pan, C centre on you, M/ESC close |
| ESC            | pause menu: resume, settings, abandon run, quit          |
| R              | after you fall: go again (same hero, same seed if you chose one) |
| F11            | cycle window mode (everywhere; saved)                    |

**Gamepad** (any pad SDL knows, e.g. Xbox, PlayStation, Switch Pro, Steam
Deck): left stick walks, right stick aims (the reticle sits a few tiles out
that way and stays when you let go), right trigger or right shoulder
fires, Start pauses, Back opens the map (left stick pans, shoulders zoom).
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
  `WEAPONS`, defined as data via `specs.py`), walk animation speed;
- terrain hit points, effect timings, sound volume, `VSYNC`;
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
                gamepad, auto-switching, debug ghost bot)
world/          layout.py (the island plan: which biome is where),
                explored.py (what you've seen, for the maps),
                chunked.py (the island world, streaming, damage memory),
                generator.py (chunk generation), biomes.py, noise.py
                (seeded value noise, numpy), rng.py (deterministic hashing),
                tiles.py, test_map.py
entities/       actor.py (anything with hp), character.py (walking body
                with a weapon: hero and shooting enemies), weapon.py,
                projectile.py, effects.py
ai/             brain.py (senses, memory, infighting), steering.py (clumsy
                obstacle avoidance), pathing.py (small local search when
                stuck), shooters.py (archer, warlock, ogre, tower),
                creatures.py
systems/        collision.py (box vs tiles), raycast.py (grid walk for
                shots), combat.py (shots, hits, blasts, friendly fire,
                damage numbers), spawner.py (per-chunk enemy rosters)
render/         terrain.py (cached pre-drawn terrain blocks), glyphs.py
                (text pre-rendered to images for batched drawing),
                sprites.py (baked pictures, per angle), characters.py
                (pixel-art heroes and enemies, walk frames),
                enemies_sprite.py (creatures, tells), ascii_fx.py (shots,
                effects, numbers, bars as glyphs)
ui/             hud.py, crosshair.py, maps.py (minimap + big map),
                overlays.py (pause menu, game over), settings_panel.py,
                widgets.py (hero picker, seed field), logo.py, frame.py
scenes/         title.py, new_run.py (hero select), settings.py, game.py,
                common.py (menu backdrop, F11, gamepad events)
meta/           settings.py (save/settings.json), records.py
                (save/records.json), run_stats.py, files.py
app.py          services shared by the scenes (settings, records, sounds, pads)
save/           the player's settings and records (not in git)
assets/maps/    test_map.txt
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
