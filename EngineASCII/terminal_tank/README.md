# Terminal Tank

A top-down ASCII adventure roguelike on one huge island, built on the
narrative engine (`narrative_engine/`). Everything for the game lives in
this folder. (It started out as a tank game, hence the name.)

**Status:** Milestones 1-6 and "Adventurers" are done:
- keyboard walking, mouse aiming, a smooth scrolling camera;
- shooting, spells and destructible terrain;
- a seeded, chunk-streamed world with six biomes;
- enemies and combat, with 100 hp and a simple death and restart;
- the island (M5): open plains in the middle, the other five biomes
  (forest, desert, ruins, swamp, mushroom) as equal slices of a ring around
  them, then the coast and endless ocean. The ring is dealt and rotated
  differently every run;
- maps (M6): a minimap in the top-right corner and a big map on M. Explored
  ground shows real terrain; the rest of the island shows as a dimmed biome
  outline;
- adventurers: you play a hero (wizard, knight, bard, princess or
  huntress; the wizard by default, `START_HERO` in `config.py`). All share
  a placeholder magic bolt for now; each gets their own attack later.

The look: heroes and enemies are pixel-art sprites; everything that flies
or pops up (bolts, arrows, hits, damage numbers, health bars) is drawn with
text characters, like the terrain.

The enemies:
- goblin archer, warlock (red aiming beam before it casts), spell tower
  (ruins), and ogre (armored front, throws rocks that break walls);
- burrower (desert), spore puffer (mushroom), fallen warrior (plains).

Enemies use Noita-style clumsy AI, and friendly fire and infighting are on.
Next up: performance work (M7), then menus (M8).

## Setup (once)

From the project root (`EngineASCII/`):

```sh
python3 -m venv terminal_tank/.venv
terminal_tank/.venv/bin/pip install pygame-ce numpy
```

## Run

```sh
terminal_tank/.venv/bin/python terminal_tank/run.py
```

This works from any working directory.
- **Screen:** the grid is fitted to your screen's shape, so borderless and
  fullscreen have no black bars.
- **Sound:** always plays on your operating system's default output device.
- **Saved settings:** window mode, monitor and volume still come from the
  engine's `settings.json`, which the game only reads. The game gets its own
  settings file and screen in a later milestone.

Each run is a new island. The seed is shown in the HUD; set `SEED` in
`config.py` to replay a world. Set `WORLD_MODE = "test"` to play on the
hand-made test map instead: walk east out of the starting compound's gate
to reach its shooting range.

### Controls

| Input          | Action                                                   |
|----------------|----------------------------------------------------------|
| WASD / Arrows  | walk (8 directions, same speed every way)                |
| Left click     | attack (hold to keep firing); unlimited                  |
| Mouse          | aim (true angle; the amber ring is the exact aim point, brackets mark the tile under it); you face the mouse |
| M              | big map (pauses): wheel zoom, drag or WASD pan, C centre on you, M/ESC close |
| R / click      | after you fall: start a new run                          |
| F11            | cycle window mode                                        |
| ESC            | quit                                                     |

## Tuning

Every number is in **`config.py`**:
- heroes, enemy bodies and weapons (`HEROES`, `START_HERO`, `BODIES`,
  `WEAPONS`, defined as data via `specs.py`), walk animation speed;
- terrain hit points, effect timings, sound volume, `VSYNC`;
- camera smoothing (`CAMERA_FOLLOW_RATE`);
- maps: minimap size and zoom (`MINIMAP_*`), big map zoom limit, zoom step
  and pan speed (`MAP_*`);
- sprite look (`SPRITE_PIXEL`); the pixel art itself is in
  `render/characters.py`;
- the island: `WORLD_RADIUS`, coastline and border shapes, the plains'
  size, the biome ring (`BIOME_RING`; set `BIOME_RING_SHUFFLE` and
  `BIOME_RING_ROTATE` to False for a fixed layout), and every feature
  density (trees, cacti, bogs, mushrooms, buildings...);
- streaming: chunk size, load/unload margins, generation time budget;
- enemies (`ENEMIES`): hp, sight, speed, damage, wind-up times, which biomes
  each spawns in and how often;
- enemy density per biome (`BIOME_ENEMY_DENSITY`; difficulty is per biome),
  hearing radius, reaction time, aim error, and the infighting threshold.

Colors are in `palette.py`.

## Tests

```sh
terminal_tank/.venv/bin/python -m unittest discover -s terminal_tank/tests -t .
```

(Run from `EngineASCII/`. The tests need no display.)

## Layout

```
run.py          launcher (path setup, bytecode-cache redirect, engine wiring)
config.py       all tunables            palette.py   game colors
specs.py        CharacterSpec / WeaponSpec / ShellSpec / EnemySpec data records
engine_ext/     camera.py (smooth pixel scrolling), input.py, sfx.py
                (synthesized sounds), screen.py (grid fitted to the screen)
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
render/         terrain.py, sprites.py (pictures baked into custom cell
                glyphs), characters.py (pixel-art heroes and enemies, walk
                frames), enemies_sprite.py (creatures, tells),
                ascii_fx.py (shots, effects, numbers, bars as glyphs)
ui/             hud.py, crosshair.py, death.py, maps.py (minimap + big map)
scenes/         game.py
assets/maps/    test_map.txt
tests/          unittest suite
```

## Removing the game

1. Delete this folder: `rm -rf terminal_tank/`. The venv, bytecode cache and
   save data are all inside it, so nothing is left behind.
2. Optionally revert the engine additions made for the game. They are listed
   with revert steps in `../ENGINE_CHANGES.md`. They're general-purpose, so
   the engine keeps working if you leave them in.

The game never writes outside this folder: Python's bytecode cache is
redirected to `terminal_tank/.cache/`, and the engine's `settings.json` is
opened read-only.
