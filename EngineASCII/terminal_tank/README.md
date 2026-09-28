# Terminal Tank

An infinite, top-down ASCII tank roguelike built on the narrative engine
(`narrative_engine/`). Everything for the game lives in this folder.

**Status:** Milestone 1 of 6 is done: keyboard driving, mouse turret aiming and
a scrolling camera on a static test map.

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

This works from any working directory. The window uses the engine's
`settings.json` (grid, window mode, monitor, volume). Change those with the
engine's own settings screen (`narrative_engine/main.py`). The game only
*reads* that file.

### Controls

| Input          | Action                                                   |
|----------------|----------------------------------------------------------|
| WASD / Arrows  | drive (hull turns toward the direction; backs up if it's behind you) |
| Mouse          | aim turret (true angle; the amber ring is the exact aim point, brackets mark the tile under it) |
| F11            | cycle window mode                                        |
| ESC            | quit                                                     |

Set `DRIVE_MODE = "tank"` in `config.py` for classic tank controls
(W/S throttle, A/D rotate).

## Tuning

Every speed, size and rate is in **`config.py`**, including `VSYNC` (on by
default for smooth motion), camera smoothing
(`CAMERA_FOLLOW_RATE`: higher = tighter, 0 = locked to the tank), the tank's
drawn size (`HULL_*_PX`, `BARREL_*_PX`), `SPRITE_PIXEL` ((1, 1) smooth, (2, 2)
chunky retro pixels), and how many rotation steps are baked. Colors are in
`palette.py`. The test map is plain text: `assets/maps/test_map.txt` (legend
in `world/test_map.py`).

## Tests

```sh
terminal_tank/.venv/bin/python -m unittest discover -s terminal_tank/tests -t .
```

(Run from `EngineASCII/`. The tests need no display.)

## Layout

```
run.py          launcher (path setup, bytecode-cache redirect, engine wiring)
config.py       all tunables            palette.py   game colors
engine_ext/     camera.py (smooth pixel scrolling, world<->screen), input.py
world/          tiles.py, rng.py (deterministic hashing), test_map.py
entities/       tank.py (driving + aiming)
systems/        collision.py (box vs tile grid, wall sliding)
render/         terrain.py, sprites.py (rotated shapes baked into custom
                cell glyphs), tank_sprite.py
ui/             hud.py, crosshair.py
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
