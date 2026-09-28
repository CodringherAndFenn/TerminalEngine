# Engine Changes

A log of every approved change made to the engine (`narrative_engine/`) or
other files outside `terminal_tank/` while building Terminal Tank. Each
entry lists what changed, why, the files touched, how to use it, and how to
revert it.

---

## 2026-09-27 — `Display.window_to_canvas`: sub-cell mouse mapping

**What / why.** Added `Display.window_to_canvas(px, py)`, which maps an
OS-window pixel to a *fractional canvas pixel*. It uses the same inverse
transform as `window_to_cell()` (undo letterbox offset, undo scale), but
doesn't floor the result to a cell. Terminal Tank aims its turret at the true
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
(or `git checkout` both files from before this change). Terminal Tank is the
only caller: `terminal_tank/engine_ext/input.py`.

---

## 2026-09-28 — `TextRenderer.register_glyph`: custom procedural glyphs

**What / why.** Added `TextRenderer.register_glyph(char, painter)` and
`TextRenderer.unregister_glyph(char)`. A registered character is drawn by
calling `painter(cell, fg)` on a blank cell-sized SRCALPHA Surface (already
filled with `bg` unless `bg` is None), and the result goes through the normal
`(char, fg, bg)` glyph cache and `put()` path. Custom glyphs take priority
over the font and the built-in box/block set, and they can paint any colors.

Terminal Tank needs this because the tank drew badly with characters alone.
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

In Terminal Tank, `terminal_tank/render/sprites.py` (`SpriteBank`) uses this.

**Revert.** In `narrative_engine/engine/text.py`, remove the `GlyphPainter`
alias, the `Callable` import, the `_custom` dict, the `register_glyph`,
`unregister_glyph` and `_drop_cached` methods, and the
`painter = self._custom.get(char)` branch in `_glyph` (so `if char in
SYNTHESIZED_CHARS:` is the first branch again). Also remove the added
sentence in `CLAUDE.md`. Terminal Tank's tank sprite depends on this method.

---

## 2026-09-28 — `TextRenderer.put_px`: pixel-positioned text

**What / why.** Added `TextRenderer.put_px(x, y, text, fg, bg)`. It works like
`put()`, but the string's top-left goes at any canvas pixel instead of a grid
cell. Characters are still cell-sized and one cell apart, and they use the
same glyph cache, including custom glyphs from `register_glyph`. Coordinates
are rounded to whole pixels. Glyphs past the canvas edge are clipped, and
glyphs straddling the edge are drawn partially.

Terminal Tank needs this for smooth scrolling. Before this change the camera
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

In Terminal Tank, `terminal_tank/render/terrain.py` and
`terminal_tank/render/sprites.py` (`SpriteBank.draw`) use this.

**Revert.** Delete the `put_px` method from `narrative_engine/engine/text.py`
and the added sentence in `CLAUDE.md`. Terminal Tank's camera and sprites
depend on this method.

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

Terminal Tank needs this for smooth motion. The old loop slept with
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

In Terminal Tank, `terminal_tank/run.py` passes `vsync=config.VSYNC`.

**Revert.** In `display.py`, remove the `vsync` parameter, its docstring
entry and the two attributes. Restore `_apply_mode` to the body now in
`_set_mode`, without the `vsync=` arguments, and delete `_set_mode`. In
`scene.py`, remove `import time` and the `fps` keyword and attribute, and
restore the loop header to `dt = clock.tick(60) / 1000.0`. Revert the two
`CLAUDE.md` edits. Terminal Tank passes `vsync=` to `Display`, so after
reverting, also drop that argument from `terminal_tank/run.py`.
