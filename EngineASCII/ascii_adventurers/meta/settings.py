"""
meta/settings.py -- the player's settings (save/settings.json).

The defaults work on any machine: the primary monitor, a window sized to
fit the screen, the OS's default audio output, moderate volume. Nothing
from the developer's machine is ever baked in.

Every field is validated on its own when loading, so one bad value never
throws away the rest.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from .. import config
from .files import SAVE_DIR, read_json, write_json

PATH = SAVE_DIR / "settings.json"
WINDOW_MODES = ("windowed", "borderless", "fullscreen")


@dataclass
class GameSettings:
    window_mode: str = "windowed"
    monitor: int = 0
    # Windowed size in pixels, or None: fit the window to the screen.
    window_size: tuple[int, int] | None = None
    vsync: bool = config.VSYNC           # takes effect on the next start
    volume: float = 0.7                  # master
    sfx_volume: float = config.SFX_VOLUME
    audio_device: str | None = None      # None: follow the OS default output
    show_fps: bool = True
    hero: str = config.START_HERO        # last hero picked
    seed: int | None = None              # last custom seed (None: random)

    @classmethod
    def load(cls, path: Path | str = PATH) -> "GameSettings":
        data = read_json(Path(path))
        s = cls()
        if data.get("window_mode") in WINDOW_MODES:
            s.window_mode = data["window_mode"]
        if _is_int(data.get("monitor")) and data["monitor"] >= 0:
            s.monitor = data["monitor"]
        size = data.get("window_size")
        if (isinstance(size, list) and len(size) == 2
                and all(_is_int(v) and 100 <= v <= 20000 for v in size)):
            s.window_size = (size[0], size[1])
        if isinstance(data.get("vsync"), bool):
            s.vsync = data["vsync"]
        for name in ("volume", "sfx_volume"):
            v = data.get(name)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                setattr(s, name, max(0.0, min(1.0, float(v))))
        dev = data.get("audio_device")
        if dev is None or isinstance(dev, str):
            s.audio_device = dev
        if isinstance(data.get("show_fps"), bool):
            s.show_fps = data["show_fps"]
        if data.get("hero") in config.HEROES:
            s.hero = data["hero"]
        seed = data.get("seed")
        if seed is None or (_is_int(seed) and 0 < seed < 10**9):
            s.seed = seed
        return s

    def save(self, path: Path | str = PATH) -> bool:
        data = asdict(self)
        if self.window_size is not None:
            data["window_size"] = list(self.window_size)
        return write_json(Path(path), data)


def _is_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)
