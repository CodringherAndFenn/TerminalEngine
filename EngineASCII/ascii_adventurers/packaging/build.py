#!/usr/bin/env python3
"""
packaging/build.py -- build a standalone copy of the game with PyInstaller.

    ascii_adventurers/.venv/bin/pip install -r ascii_adventurers/requirements-dev.txt
    ascii_adventurers/.venv/bin/python ascii_adventurers/packaging/build.py

Produces ascii_adventurers/dist/AsciiAdventurers/: a folder with the
AsciiAdventurers executable, the Python runtime, pygame-ce, numpy, the font
and the game's data. Players need nothing installed. A folder ("onedir")
rather than a single self-extracting file starts faster and is what Steam
expects to upload.

PyInstaller builds for the OS it runs on: build on Windows for Windows, on
Linux for Linux (and the Steam Deck). Intermediate files go to
ascii_adventurers/build/; both folders are ignored by git.

Linux release builds: run this with the portable Python from
release_python.py (ascii_adventurers/.release/venv/bin/python), so the
result runs on older systems too, not just ones as new as this machine.
The build prints the newest glibc it needs.

A packaged game saves to the player's data folder, not next to the
executable (see meta/files.py).
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent            # .../ascii_adventurers/packaging
GAME = HERE.parent                                # .../ascii_adventurers
# Keep bytecode out of the source tree (the engine's __pycache__ is tracked
# in git), as run.py does.
sys.pycache_prefix = str(GAME / ".cache" / "pycache")
ROOT = GAME.parent                                # .../EngineASCII
ENGINE = ROOT / "narrative_engine"
SEP = ";" if sys.platform.startswith("win") else ":"   # PyInstaller's --add-data separator
NAME = "AsciiAdventurers"


def data(src: Path, dest: str) -> list[str]:
    return ["--add-data", f"{src}{SEP}{dest}"]


def pyinstaller_args() -> list[str]:
    args = [
        str(GAME / "run.py"),
        "--name", NAME,
        "--noconfirm", "--clean",
        "--windowed",                         # no console window (Windows/macOS)
        "--distpath", str(GAME / "dist"),
        "--workpath", str(GAME / "build" / "pyinstaller"),
        "--specpath", str(GAME / "build"),
        # Where `import engine` and `import ascii_adventurers` come from.
        "--paths", str(ROOT),
        "--paths", str(ENGINE),
        # Imported by pygame at runtime, invisible to PyInstaller's scan.
        "--hidden-import", "pygame._sdl2.controller",
        "--hidden-import", "pygame._sdl2.audio",
        # Not part of the game.
        "--exclude-module", "ascii_adventurers.tests",
        "--exclude-module", "tkinter",
    ]
    # Files read at runtime. Paths mirror the source tree, because the code
    # finds them relative to its own modules (engine/display.py looks in
    # ../assets/fonts, world/test_map.py in ../assets/maps).
    args += data(ENGINE / "assets" / "fonts" / "VT323-Regular.ttf", "assets/fonts")
    args += data(ENGINE / "assets" / "fonts" / "OFL-VT323.txt", "assets/fonts")
    args += data(GAME / "assets" / "maps", "ascii_adventurers/assets/maps")
    return args


def main() -> int:
    try:
        import PyInstaller.__main__
    except ImportError:
        print("PyInstaller isn't installed: pip install -r ascii_adventurers/requirements-dev.txt")
        return 1
    PyInstaller.__main__.run(pyinstaller_args())
    exe = GAME / "dist" / NAME / (NAME + (".exe" if sys.platform.startswith("win") else ""))
    print(f"\nBuilt: {exe}")
    if sys.platform.startswith("linux"):
        drop_system_libs(GAME / "dist" / NAME)
        need = newest_glibc(GAME / "dist" / NAME)
        shown = f"{need[0]}.{need[1]}" if need else "?"
        print(f"Needs glibc {shown} or newer "
              f"(Steam Deck / Ubuntu 22.04 have 2.35+; aim for <= 2.31).")
        if need and need > (2, 31):
            print("WARNING: too new for many players -- build with the portable Python "
                  "(see packaging/release_python.py).")
    return 0


# The C++ runtime. PyInstaller copies this machine's, but every Linux system
# (SteamOS included) has its own, which is backward compatible; a copy
# newer than the player's glibc stops the game starting, and a bundled one
# can clash with the graphics driver's. So the player's own is used.
SYSTEM_LIBS = ("libstdc++.so.6", "libgcc_s.so.1")


def drop_system_libs(folder: Path) -> None:
    for name in SYSTEM_LIBS:
        for p in folder.rglob(name):
            p.unlink()
            print(f"Removed {p.relative_to(folder)} (the player's system copy is used)")


def newest_glibc(folder: Path) -> tuple[int, int] | None:
    """The newest GLIBC_x.y symbol version any bundled binary asks for
    (via objdump; None if objdump isn't available)."""
    import re
    import shutil
    import subprocess
    if shutil.which("objdump") is None:
        return None
    newest = None
    files = [p for p in folder.rglob("*") if p.is_file() and (".so" in p.name or p.name == NAME)]
    for f in files:
        out = subprocess.run(["objdump", "-T", str(f)], capture_output=True, text=True).stdout
        for major, minor in re.findall(r"GLIBC_(\d+)\.(\d+)", out):
            v = (int(major), int(minor))
            newest = v if newest is None or v > newest else newest
    return newest


if __name__ == "__main__":
    sys.exit(main())
