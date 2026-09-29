"""
meta/files.py -- where the save files live, and forgiving JSON I/O.

Where saves go:
  * running from source (development): ascii_adventurers/save/, so the
    game never writes outside its folder;
  * a packaged build (PyInstaller sets sys.frozen): the player's own data
    folder, since an installed game's folder may be read-only and is
    replaced on every update (Steam Cloud can sync this folder too):
      Windows  %APPDATA%\\AsciiAdventurers
      macOS    ~/Library/Application Support/AsciiAdventurers
      Linux    $XDG_DATA_HOME/AsciiAdventurers (~/.local/share/...)
  * ASCII_ADVENTURERS_SAVE_DIR, if set, overrides both (testing).
The folder is created on first save. Reads never fail: a missing,
unreadable or corrupt file gives {} and the caller falls back to defaults
field by field. Writes go to a temporary file that then replaces the real
one, so a crash mid-save can't corrupt it.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

APP_NAME = "AsciiAdventurers"


def user_data_dir(platform: str = sys.platform, env=os.environ, home: Path | None = None) -> Path:
    """The per-user data folder for this OS."""
    home = home if home is not None else Path.home()
    if platform.startswith("win"):
        base = env.get("APPDATA")
        return Path(base) / APP_NAME if base else home / "AppData" / "Roaming" / APP_NAME
    if platform == "darwin":
        return home / "Library" / "Application Support" / APP_NAME
    base = env.get("XDG_DATA_HOME")
    return (Path(base) if base else home / ".local" / "share") / APP_NAME


def save_dir(frozen: bool | None = None, env=os.environ) -> Path:
    override = env.get("ASCII_ADVENTURERS_SAVE_DIR")
    if override:
        return Path(override)
    if frozen if frozen is not None else getattr(sys, "frozen", False):
        return user_data_dir(env=env)
    return Path(__file__).resolve().parent.parent / "save"


SAVE_DIR = save_dir()


def read_json(path: Path) -> dict:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def write_json(path: Path, data: dict) -> bool:
    """Write `data`; returns False (and keeps going) if the disk refuses."""
    path = Path(path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        return False
    return True
