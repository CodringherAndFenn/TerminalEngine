"""
ui/quest_log.py -- the quest log (M17): a small panel under the HUD's
status panel, top-left. One line per quest, the main quest first:

    GLORY    guardians 0/5
    SWAMP    Psychedelic frogs 2/5

(label, what to do now). Finished quests turn green. The big map shows
the same lines (ui/maps.py).
"""

from __future__ import annotations

from engine import TextRenderer

from .. import palette
from .hud import PANEL_W

LABEL_W = 7


def draw_quest_log(text: TextRenderer, lines, row: int) -> None:
    """`lines`: (label, text, done) from systems/quests.Quests.log()."""
    if not lines:
        return
    width = max(PANEL_W, max(len(what) for _, what, _ in lines) + LABEL_W + 3)
    for i, (label, what, done) in enumerate(lines):
        r = row + i
        text.put(0, r, " " * width, palette.HUD_PANEL, palette.HUD_PANEL)
        text.put(1, r, label[:LABEL_W], palette.QUEST_TITLE, palette.HUD_PANEL)
        text.put(2 + LABEL_W, r, what[:width - LABEL_W - 3],
                 palette.QUEST_DONE if done else palette.QUEST_TEXT, palette.HUD_PANEL)
