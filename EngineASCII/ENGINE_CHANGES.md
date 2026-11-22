# Engine Changes

A log of every approved change made to the engine (`narrative_engine/`) or
other files outside `ascii_adventurers/` while building AsciiAdventurers. Each
entry lists what changed, why, the files touched, how to use it, and how to
revert it.

---

## 2026-09-27 — `Display.window_to_canvas`: sub-cell mouse mapping

**What / why.** Added `Display.window_to_canvas(px, py)`, which maps an
OS-window pixel to a *fractional canvas pixel*. It uses the same inverse
transform as `window_to_cell()` (undo letterbox offset, undo scale), but
doesn't floor the result to a cell. AsciiAdventurers aims its turret at the true
angle from the tank to the mouse. With 10×24 px cells, whole-cell precision
could put the aim off by about 10° at close range, so the game needs the exact
point. This is a general-purpose engine feature and has nothing specific to
the game.

**Files touched.**
- `narrative_engine/engine/display.py` — new method `Display.window_to_canvas`
  (added after `window_to_cell`; existing code is unchanged).
- `CLAUDE.md` — one sentence in the `engine/display.py` architecture paragraph
  mentioning `window_to_cell` / `window_to_canvas`.

**Usage.**

```python
pos = display.window_to_canvas(*pygame.mouse.get_pos())
if pos is not None:                      # None == over a letterbox bar
    px, py = pos                         # canvas pixels, e.g. (803.5, 311.25)
    col_f = px / display.cell_w          # fractional grid column
    row_f = py / display.cell_h          # fractional grid row
```

**Revert.** Delete the `window_to_canvas` method from
`narrative_engine/engine/display.py` and the added sentence in `CLAUDE.md`
(or `git checkout` both files from before this change). AsciiAdventurers is the
only caller: `ascii_adventurers/engine_ext/input.py`.

---

## 2026-09-28 — `TextRenderer.register_glyph`: custom procedural glyphs

**What / why.** Added `TextRenderer.register_glyph(char, painter)` and
`TextRenderer.unregister_glyph(char)`. A registered character is drawn by
calling `painter(cell, fg)` on a blank cell-sized SRCALPHA Surface (already
filled with `bg` unless `bg` is None), and the result goes through the normal
`(char, fg, bg)` glyph cache and `put()` path. Custom glyphs take priority
over the font and the built-in box/block set, and they can paint any colors.

AsciiAdventurers needs this because the tank drew badly with characters alone.
A cell is 10×24 px and the finest block glyph is 10×12, so a hull rotated 45°
collapsed into a thin blob, and `/` has one fixed slope, so barrels at other
angles came out as staircases. The game now paints the hull and barrel as
rotated shapes, slices them into cell-sized pieces, and registers each piece
as a custom glyph. The shape is exact at any angle, and the sprite stays
aligned to the grid. The feature is general-purpose: it covers icons, custom
UI glyphs, and multi-cell sprites.

Registering a character again replaces its painter and drops that character's
cached images.

**Files touched.**
- `narrative_engine/engine/text.py`:
  - a `typing.Callable` import;
  - a `GlyphPainter` type alias;
  - a `_custom` dict in `TextRenderer.__init__`;
  - new methods `register_glyph`, `unregister_glyph` and `_drop_cached`;
  - a custom-painter lookup at the top of the drawing branch in `_glyph`.

  Existing glyph drawing is unchanged.
- `CLAUDE.md` — one sentence in the `engine/text.py` architecture paragraph.

**Usage.**

```python
BADGE = "\ue000"  # Private Use Area: can never collide with real text

def paint_badge(cell, fg):
    w, h = cell.get_size()
    pygame.draw.circle(cell, fg, (w // 2, h // 2), w // 2 - 1)
    pygame.draw.circle(cell, (255, 255, 255), (w // 2, h // 2), 2)  # any color

text.register_glyph(BADGE, paint_badge)
text.put(10, 5, BADGE, colors.AMBER, None)  # bg=None: draws over the cell
```

In AsciiAdventurers, `ascii_adventurers/render/sprites.py` (`SpriteBank`) used
this until M7 (2026-09-29). Since then sprites are blitted as whole images
(faster with hundreds of enemies), and the game doesn't call
`register_glyph` any more. The method stays as a general engine feature.

**Revert.** In `narrative_engine/engine/text.py`, remove the `GlyphPainter`
alias, the `Callable` import, the `_custom` dict, the `register_glyph`,
`unregister_glyph` and `_drop_cached` methods, and the
`painter = self._custom.get(char)` branch in `_glyph` (so `if char in
SYNTHESIZED_CHARS:` is the first branch again). Also remove the added
sentence in `CLAUDE.md`. Since M7 no game code depends on this method, but
revert change B2 (below) first: it extends `_drop_cached`.

---

## 2026-09-28 — `TextRenderer.put_px`: pixel-positioned text

**What / why.** Added `TextRenderer.put_px(x, y, text, fg, bg)`. It works like
`put()`, but the string's top-left goes at any canvas pixel instead of a grid
cell. Characters are still cell-sized and one cell apart, and they use the
same glyph cache, including custom glyphs from `register_glyph`. Coordinates
are rounded to whole pixels. Glyphs past the canvas edge are clipped, and
glyphs straddling the edge are drawn partially.

AsciiAdventurers needs this for smooth scrolling. Before this change the camera
could only scroll by whole cells: 10 px horizontally but 24 px vertically.
Moving up/down or diagonally therefore jumped visibly (measured: 24 px jumps
on about 8 frames per second, standing still on the rest). The game now
draws its terrain and sprites at the camera's pixel offset, so the view moves
at most about 3 px per frame, every frame. The feature is general-purpose:
any scrolling map, moving sprite or projectile needs it.

**Files touched.**
- `narrative_engine/engine/text.py` — new method `TextRenderer.put_px`, placed
  after `put()`. `put()` and all existing drawing are unchanged.
- `CLAUDE.md` — one sentence in the `engine/text.py` architecture paragraph.

**Usage.**

```python
# Scroll a row of map text by a fractional camera offset:
text.put_px(col * cell_w - cam_px, row * cell_h - cam_py, "..##..", fg, bg)

# Draw a moving glyph exactly where an object is:
text.put_px(shell_x_px - cell_w / 2, shell_y_px - cell_h / 2, "*", colors.AMBER, None)
```

In AsciiAdventurers, `ascii_adventurers/render/glyphs.py` uses this: it
pre-renders glyph strings into images with `put_px`, and the terrain, shots
and effects blit those images. Sprites were drawn with it until M7.

**Revert.** Delete the `put_px` method from `narrative_engine/engine/text.py`
and the added sentence in `CLAUDE.md`. AsciiAdventurers' terrain, shots and
effects depend on this method (through `render/glyphs.py`).

---

## 2026-09-28 — Vsync option and precise frame timing

**What / why.** Two coupled changes to frame pacing:
1. `Display(..., vsync=False)` has a new keyword. When it's true, every window
   (re)build asks SDL for vsync, so `present()`'s `flip()` waits for the
   monitor refresh. If SDL refuses, the window is created without vsync and
   nothing breaks. `display.vsync` reports what is actually in effect.
2. `SceneManager(..., fps=60)` has a new keyword, and `run()` paces frames
   differently. With vsync the monitor sets the rate: the clock only
   measures and never sleeps. Without vsync it caps at `fps`, as before.
   `dt` is now measured with `time.perf_counter()` instead of the clock's
   whole milliseconds.

AsciiAdventurers needs this for smooth motion. The old loop slept with
`clock.tick(60)` and never synchronized with the display. Measured on a
59.96 Hz panel, it actually ran at about 62 fps (frame times 14.8–17.3 ms),
so about twice a second a frame was shown twice or skipped. That reads as a
micro-stutter in smooth scrolling and was most visible on the tank barrel.
With vsync, frame times measured 16.65 ms ± 0.09 ms, with no frame more
than 1 ms off.

**Defaults keep old behavior.** `vsync` defaults to False and `fps` to 60,
so `main.py` and `demo.py` are unaffected, apart from `dt` now being precise
instead of rounded to whole milliseconds.

**Files touched.**
- `narrative_engine/engine/display.py`:
  - `vsync` parameter and docstring;
  - the `self.vsync` and `_vsync_requested` attributes;
  - `_apply_mode` now tries vsync and falls back;
  - the per-mode `set_mode` calls moved unchanged into a new `_set_mode`
    helper that passes `vsync=`.
- `narrative_engine/engine/scene.py`:
  - `import time`;
  - the `fps` keyword on `SceneManager.__init__`;
  - frame pacing and `dt` measurement at the top of the `run()` loop.
- `CLAUDE.md` — one sentence in the `display.py` paragraph; the `scene.py`
  paragraph's "60fps loop" wording updated.

**Usage.**

```python
display = Display(172, 30, font_size=24, vsync=True)
print(display.vsync)                  # True if the platform granted it
manager = SceneManager(display, settings, audio)          # vsync-paced
manager = SceneManager(display, settings, audio, fps=30)  # used only without vsync
```

In AsciiAdventurers, `ascii_adventurers/run.py` passes `vsync=config.VSYNC`.

**Revert.** In `display.py`, remove the `vsync` parameter, its docstring
entry and the two attributes. Restore `_apply_mode` to the body now in
`_set_mode`, without the `vsync=` arguments, and delete `_set_mode`. In
`scene.py`, remove `import time` and the `fps` keyword and attribute, and
restore the loop header to `dt = clock.tick(60) / 1000.0`. Revert the two
`CLAUDE.md` edits. AsciiAdventurers passes `vsync=` to `Display`, so after
reverting, also drop that argument from `ascii_adventurers/run.py`.

---

## 2026-09-29 — B2: glyph-cache index for `register_glyph` / `unregister_glyph`

**What / why.** `TextRenderer` now keeps `_keys_by_char`, which maps each
character to its keys in the glyph cache. `_drop_cached(char)` runs when a
custom glyph is registered again or unregistered. It used to scan the whole
cache for that character's `(char, fg, bg)` keys; now it deletes exactly the
indexed keys. Measured with ~3,200 cached glyphs: 88 µs → 0.6 µs per
register/unregister.

AsciiAdventurers needed this because its sprite cache recycled custom glyphs
as rotated sprites came and went. Each recycle scanned the full cache, and
dozens in one frame showed up as frame spikes. (Later in M7 the game stopped
using custom glyphs for sprites; see the `register_glyph` entry. The index is
still the right behavior for any engine user that redefines glyphs.)

Behavior is otherwise unchanged. The same entries are dropped as before, and
glyphs of other characters are untouched. The cost is one list append each
time a new glyph is rasterized.

**Files touched.**
- `narrative_engine/engine/text.py`:
  - the `_keys_by_char` dict in `TextRenderer.__init__`;
  - `_drop_cached` pops from it instead of scanning;
  - `_glyph` records each new key in it.

**Usage.** Nothing new to call. `register_glyph` / `unregister_glyph` work
as before, just in constant time.

**Revert.** In `narrative_engine/engine/text.py`, delete the `_keys_by_char`
lines from `__init__` and `_glyph`, and restore `_drop_cached` to:

```python
for key in [k for k in self._glyph_cache if k[0] == char]:
    del self._glyph_cache[key]
```

---

## 2026-09-29 — CI workflow for game builds (outside the engine)

**What / why.** Added `.github/workflows/ascii-adventurers.yml` at the
repository root (`TerminalEngine/`). It isn't an engine change, but it's a
file outside `ascii_adventurers/`, so it's logged here. Approved by the
user as the way to get Windows builds: PyInstaller can't cross-compile, so
a Windows copy has to be built on Windows.

On every push to `main` that touches `EngineASCII/` (and on demand from the
GitHub Actions tab), a Windows and a Linux runner each:
1. set up Python. Windows uses 3.14 from `actions/setup-python`. Linux uses
   the portable Python from `packaging/release_python.py`, so the build
   runs on the Steam Deck and older distros;
2. install `ascii_adventurers/requirements-dev.txt`;
3. run the unit tests;
4. build with `ascii_adventurers/packaging/build.py`;
5. run the built game with `--smoke 5 --ghosts 1`;
6. upload `dist/AsciiAdventurers/` as a downloadable artifact
   (`AsciiAdventurers-windows` / `AsciiAdventurers-linux`, kept 14 days).

**Files touched.** `.github/workflows/ascii-adventurers.yml` (new). Nothing
in `narrative_engine/` changed.

**Usage.** Push to `main`, or open the repository's Actions tab → *AsciiAdventurers
build* → *Run workflow*. Download the builds from the finished run's
*Artifacts* section.

**Revert.** Delete `.github/workflows/ascii-adventurers.yml` (and the
`.github/` folder if it's empty).

---

## 2026-11-22 — CI runs the tests on every core (outside the engine)

**What / why.** The Tests step of `.github/workflows/ascii-adventurers.yml`
now runs `ascii_adventurers/tests/parallel.py` instead of
`unittest discover`. The suite had grown to about 23 minutes on the Linux
runner and 33 on Windows, which was nearly the whole run (setup, build and
smoke together take under a minute). The new runner spreads the test
modules over one process per core (the runners have 4) and lists the
slowest tests at the end. It goes with a test-only island cache
(`tests/islands.py`), which removed most of the time. Both are inside
`ascii_adventurers/`. Asked for by the user ("make the tests and the
runners more efficient").

**Files touched.** `.github/workflows/ascii-adventurers.yml` (the Tests
step). Nothing in `narrative_engine/` changed.

**Usage.** Nothing changes: push to `main` as before. Locally:
`ascii_adventurers/.venv/bin/python -m ascii_adventurers.tests.parallel`.

**Revert.** Set the Tests step's `run:` back to
`$PY -m unittest discover -s ascii_adventurers/tests -t .` (that still
works, in one process).

---

## 2026-11-22 — GPU scaling in `Display.present()` (sharp bilinear), CPU fallback

**What / why.** At 1080p the game's 1280x720 canvas is shown at 1.5x. With
nearest-neighbor scaling a canvas pixel is alternately 1 and 2 screen
pixels wide, so as the world scrolls one pixel every thin stroke (water
waves, dithered ground) doubles and halves in width frame to frame: the
flicker the user saw "in almost every biome". (Measured: a 1-px line's
on-screen weight went 2, 1, 2, 1 as it scrolled.) Approved by the user
("go ahead with gpu scaling and the fallback"), with low-end devices as
the priority.

`Display` now opens its window with `pygame.Window` and a hardware
`pygame._sdl2.video.Renderer` when it can. `present()` uploads the canvas
to a texture each frame. At a whole-number scale it draws it with
nearest-neighbor, as before. At any other scale it draws it nearest-neighbor
into a render target at the next whole number (2x), and the GPU's bilinear
filter takes that down to the window ("sharp bilinear"). Every canvas
pixel then covers the same 1.5 screen pixels (the 1-px line stays at 1.50),
crisp but for a soft half-pixel edge. Measured on the dev laptop (Intel
UHD): `present()` 1.38 ms on the GPU against 3.36 ms on the old CPU path,
so it is cheaper as well as flicker-free. The CPU's share is the 3.7 MB
canvas upload, ~1 ms.

The CPU path is the engine's original code, unchanged, and is used:
- on headless video drivers (`dummy`, `offscreen`: the tests, CI);
- when there's no hardware renderer (`accelerated=1` never settles for
  SDL's software renderer, which would be slower);
- with `Display(gpu=False)`;
- for good, once anything on the GPU path raises (at a mode change or
  mid-game).
A vsync'd GPU window times a few presents; if the driver ignored vsync,
`display.vsync` is False, so the main loop keeps capping the frame rate
itself. `RENDER_DEVICE_RESET` (Direct3D on alt-tab) drops the textures, and
the next present makes new ones.

New public API: `Display(gpu=True)`, `display.gpu` (what's in effect),
`display.window_size()` (the window's pixel size on either path: there is
no `pygame.display` surface on the GPU path).

**Files touched.**
- `narrative_engine/engine/display.py`: the GPU path (`_open_gpu`,
  `_close_gpu`, `_presents_wait`, `_texture`, `_present_gpu`), the CPU path
  split out (`_present_cpu`, `_fit`), `window_size()`, the `gpu` flag and
  `RENDER_DEVICE_RESET` in `handle_event`.
- `narrative_engine/demo.py`: reads the window size with
  `display.window_size()`.
- `CLAUDE.md` (EngineASCII/): the `display.py` description.
- Game side (`ascii_adventurers/`): `engine_ext/screen.py` uses
  `display.window_size()`. `run.py` passes `gpu=` (`ASCII_ADVENTURERS_GPU=0`
  forces the CPU path) and the `--smoke` report says which path ran.
  `packaging/build.py` bundles `pygame._sdl2.video` explicitly (a build
  without it would quietly scale on the CPU).
  `tests/test_gpu_display.py` (10 tests, faked GPU) and README.

**Usage.**
```python
display = Display(128, 30, vsync=True)          # GPU when possible
display.gpu                                     # True: scaled on the GPU
display.window_size()                           # (1920, 1080)
Display(128, 30, gpu=False)                     # always the CPU path
```

**Revert.** In `Display.__init__` set `self._gpu_requested = False` (one
line: everything then takes the original CPU path). Or revert
`display.py` and change the three `display.window_size()` calls in
`ascii_adventurers/engine_ext/screen.py` back to
`pygame.display.get_surface().get_size()`.
