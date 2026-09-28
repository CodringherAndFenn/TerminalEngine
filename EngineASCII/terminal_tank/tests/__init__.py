"""
Terminal Tank tests (stdlib unittest, no display needed).

Run from the project root (EngineASCII/):

    terminal_tank/.venv/bin/python -m unittest discover -s terminal_tank/tests -t .

This package sets up the same import environment as run.py: the bytecode
cache is redirected into terminal_tank/.cache/ (so the engine's tracked
__pycache__ files are never rewritten) and narrative_engine/ goes on
sys.path for `import engine`.
"""

import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.pycache_prefix = str(_HERE.parent / ".cache" / "pycache")
_ENGINE = str(_HERE.parent.parent / "narrative_engine")
if _ENGINE not in sys.path:
    sys.path.insert(0, _ENGINE)

# Headless-safe: nothing here opens a window, but pygame is imported.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
