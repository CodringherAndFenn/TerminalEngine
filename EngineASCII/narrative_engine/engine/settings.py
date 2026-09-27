"""
settings.py -- the user-configurable settings model and its JSON persistence.

A single ``Settings`` dataclass holds everything the settings screen can
change: the scaling controls that already existed (grid preset, window mode)
plus resolution, monitor, master volume, and audio-device choice. It loads
from / saves to a ``settings.json`` at the repo root, resolved with pathlib so
it behaves the same on Linux and Windows (mirroring how the bundled font is
found).

Validation is deliberately forgiving: a missing, unreadable, or partially
corrupt file falls back to sensible defaults field by field, so the game
always starts.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .display import GRID_CLASSIC, GRID_ULTRAWIDE, GRID_WIDE

# settings.json lives at the repo root (two levels up from this file:
# engine/ -> narrative_engine/ -> repo root).
DEFAULT_PATH = Path(__file__).resolve().parent.parent.parent / "settings.json"

# Grid preset name <-> (cols, rows). Names are what gets stored on disk.
GRID_PRESETS: dict[str, tuple[int, int]] = {
    "ultrawide": GRID_ULTRAWIDE,
    "wide": GRID_WIDE,
    "classic": GRID_CLASSIC,
}

WINDOW_MODES = ("windowed", "borderless", "fullscreen")


@dataclass
class Settings:
    """All persisted user settings, with defaults tuned for the primary
    (ultrawide) target display."""

    grid: str = "ultrawide"
    window_mode: str = "windowed"
    monitor: int = 0
    resolution: tuple[int, int] = (1280, 720)
    volume: float = 0.7
    audio_device: str | None = None  # None == system default output

    def grid_size(self) -> tuple[int, int]:
        """The (cols, rows) for the selected grid preset."""
        return GRID_PRESETS.get(self.grid, GRID_ULTRAWIDE)

    # --- Persistence -----------------------------------------------------

    @classmethod
    def load(cls, path: Path | str = DEFAULT_PATH) -> "Settings":
        """Load settings from JSON, falling back to defaults on any problem."""
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cls()
        if not isinstance(data, dict):
            return cls()
        return cls._coerce(data)

    @classmethod
    def _coerce(cls, data: dict) -> "Settings":
        """Build a Settings from raw JSON, validating each field on its own so
        one bad value never discards the rest."""
        s = cls()
        if data.get("grid") in GRID_PRESETS:
            s.grid = data["grid"]
        if data.get("window_mode") in WINDOW_MODES:
            s.window_mode = data["window_mode"]
        if isinstance(data.get("monitor"), int) and data["monitor"] >= 0:
            s.monitor = data["monitor"]
        res = data.get("resolution")
        if (
            isinstance(res, (list, tuple))
            and len(res) == 2
            and all(isinstance(v, int) and v > 0 for v in res)
        ):
            s.resolution = (int(res[0]), int(res[1]))
        if isinstance(data.get("volume"), (int, float)):
            s.volume = max(0.0, min(1.0, float(data["volume"])))
        dev = data.get("audio_device")
        if dev is None or isinstance(dev, str):
            s.audio_device = dev
        return s

    def save(self, path: Path | str = DEFAULT_PATH) -> None:
        """Write settings to JSON (pretty-printed). Resolution is stored as a
        list since JSON has no tuple type."""
        payload = {
            "grid": self.grid,
            "window_mode": self.window_mode,
            "monitor": self.monitor,
            "resolution": list(self.resolution),
            "volume": self.volume,
            "audio_device": self.audio_device,
        }
        Path(path).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
