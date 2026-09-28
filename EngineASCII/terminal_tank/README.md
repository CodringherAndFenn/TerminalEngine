# Terminal Tank

An infinite, top-down ASCII tank roguelike built on the narrative engine
(`narrative_engine/`). Everything for the game lives in this folder.

**Status:** Milestones 1-4 of 6 are done:
- keyboard driving, mouse turret aiming, a smooth scrolling camera;
- shooting, shells and destructible terrain;
- an infinite, seeded, chunk-streamed world with six biomes (plains, forest,
  desert, ruins, swamp, mushroom);
- enemies and combat, with 100 hp and a simple death and restart.

The enemies:
- tankette, sniper (red laser before it fires), turret emplacement, and
  heavy tank (armored front, breaks walls);
- burrower (desert), spore puffer (mushroom), fallen warrior (plains).

Enemies use Noita-style clumsy AI, and friendly fire and infighting are on.
Pickups, upgrades, score and menus come next.

## Setup (once)

From the project root (`EngineASCII/`):

```sh
python3 -m venv terminal_tank/.venv
terminal_tank/.venv/bin/pip install pygame-ce
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

Each run is a new world. The seed is shown in the HUD; set `SEED` in
`config.py` to replay a world. Set `WORLD_MODE = "test"` to play on the
hand-made test map instead: drive east out of the starting compound's gate
to reach its shooting range.

### Controls

| Input          | Action                                                   |
|----------------|----------------------------------------------------------|
| WASD / Arrows  | drive (hull turns toward the direction; backs up if it's behind you) |
| Left click     | fire (hold to keep firing); ammo is unlimited             |
| Mouse          | aim turret (true angle; the amber ring is the exact aim point, brackets mark the tile under it) |
| R / click      | after your tank is destroyed: start a new run            |
| F11            | cycle window mode                                        |
| ESC            | quit                                                     |

Set `DRIVE_MODE = "tank"` in `config.py` for classic tank controls
(W/S throttle, A/D rotate).

## Tuning

Every number is in **`config.py`**:
- tank types and weapons (`TANKS`, `WEAPONS`, `START_TANK`, defined as data
  via `specs.py`);
- terrain hit points, effect timings, sound volume, `VSYNC`;
- camera smoothing (`CAMERA_FOLLOW_RATE`);
- sprite look (`SPRITE_PIXEL`, rotation steps);
- the world: chunk size, load/unload margins, generation time budget, the
  spawn area, the difficulty ramp, the biome rules, and every feature
  density (trees, cacti, bogs, mushrooms, buildings...);
- enemies (`ENEMIES`): hp, sight, speed, damage, wind-up times, which biomes
  each spawns in and how often;
- spawn density and difficulty scaling, hearing radius, reaction time, aim
  error, and the infighting threshold.

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
specs.py        TankSpec / WeaponSpec / ShellSpec data records
engine_ext/     camera.py (smooth pixel scrolling), input.py, sfx.py
                (synthesized sounds), screen.py (grid fitted to the screen)
world/          chunked.py (infinite world, streaming, damage memory),
                generator.py (chunk generation), biomes.py, noise.py
                (seeded value noise), rng.py (deterministic hashing),
                tiles.py, test_map.py
entities/       actor.py (anything with hp), tank.py, weapon.py,
                projectile.py, effects.py
ai/             brain.py (senses, memory, infighting), steering.py (clumsy
                obstacle avoidance), pathing.py (small local search when
                stuck), vehicles.py, creatures.py
systems/        collision.py (rotated hull vs tiles), raycast.py (grid walk
                for shells), combat.py (shots, hits, blasts, friendly fire),
                spawner.py (per-chunk enemy rosters, kills remembered)
render/         terrain.py, sprites.py (rotated shapes baked into custom
                cell glyphs), tank_sprite.py, enemies_sprite.py,
                effects_sprite.py
ui/             hud.py, crosshair.py, death.py
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
