"""
narrative_engine.engine -- display layer + scene/UI/audio for the game.

Public API re-exports so callers can do:

    from engine import Display, TextRenderer, Typewriter, Fade
    from engine import Scene, SceneManager, Settings, Audio
    from engine import colors, ui
"""

from . import colors, ui
from .audio import Audio
from .display import Display, DisplayMode, GRID_CLASSIC, GRID_WIDE, GRID_ULTRAWIDE
from .scene import Scene, SceneManager
from .settings import GRID_PRESETS, Settings, WINDOW_MODES
from .text import TextRenderer, Typewriter, Fade
from .ui import Button, Menu, OptionSelector, Slider, Widget, WidgetList

__all__ = [
    "colors",
    "ui",
    "Display",
    "DisplayMode",
    "GRID_CLASSIC",
    "GRID_WIDE",
    "GRID_ULTRAWIDE",
    "TextRenderer",
    "Typewriter",
    "Fade",
    "Scene",
    "SceneManager",
    "Settings",
    "GRID_PRESETS",
    "WINDOW_MODES",
    "Audio",
    "Widget",
    "WidgetList",
    "Button",
    "Menu",
    "OptionSelector",
    "Slider",
]
