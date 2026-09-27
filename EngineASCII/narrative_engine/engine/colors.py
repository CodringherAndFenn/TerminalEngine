"""
colors.py -- the engine's named color palette.

Everything that draws should take its colors from here, so re-theming the
whole game later means editing this one file (or swapping the PALETTE dict
for another theme).

Colors are plain (r, g, b) tuples, which is what pygame expects everywhere.
"""

# --- Core terminal palette -------------------------------------------------

# True black: used for letterbox/pillarbox bars so they read as "outside the
# screen" rather than part of the scene.
BLACK = (0, 0, 0)

# The canvas background. Very slightly green-tinted dark grey, like a CRT
# that's powered on but idle. Distinct from BLACK on purpose: it makes the
# virtual canvas visibly distinct from the letterbox bars while testing.
BACKGROUND = (10, 14, 10)

# Classic P1-phosphor green, the default "ink".
GREEN = (51, 255, 102)
GREEN_DIM = (22, 120, 48)      # de-emphasized text, hints, borders

# Amber terminal accent (P3 phosphor).
AMBER = (255, 176, 0)
AMBER_DIM = (130, 90, 0)

# Near-white for emphasis. Slightly warm so it doesn't glare against GREEN.
WHITE = (230, 230, 220)
GREY = (130, 135, 130)

# Sparing-use accents (warnings, highlights).
RED = (255, 80, 80)
CYAN = (90, 220, 220)

# Color of the bars added when the scaled canvas doesn't fill the window.
LETTERBOX = BLACK

# --- UI / widget colors ----------------------------------------------------

# The highlighted (focused/hovered) row in a menu or settings list: bright
# green fill with dark ink, i.e. an inverted terminal cursor bar.
SELECT_BG = GREEN
SELECT_FG = BACKGROUND

# A row that exists but can't be interacted with right now (e.g. the monitor
# selector when only one display is attached).
DISABLED = (70, 78, 70)

# --- Named palette ---------------------------------------------------------

# Name -> color lookup, for data-driven theming later (e.g. a script file
# saying `color: amber`). Code can use the constants above directly.
PALETTE = {
    "black": BLACK,
    "background": BACKGROUND,
    "green": GREEN,
    "green_dim": GREEN_DIM,
    "amber": AMBER,
    "amber_dim": AMBER_DIM,
    "white": WHITE,
    "grey": GREY,
    "red": RED,
    "cyan": CYAN,
    "select_bg": SELECT_BG,
    "select_fg": SELECT_FG,
    "disabled": DISABLED,
}
