"""
AsciiAdventurers tests (stdlib unittest, no display needed).

Run from the project root (EngineASCII/), on every core at once:

    ascii_adventurers/.venv/bin/python -m ascii_adventurers.tests.parallel

or in one process, the plain unittest way (also for one module or test):

    ascii_adventurers/.venv/bin/python -m unittest discover -s ascii_adventurers/tests -t .

This package sets up the same import environment as run.py: the bytecode
cache is redirected into ascii_adventurers/.cache/ (so the engine's tracked
__pycache__ files are never rewritten) and narrative_engine/ goes on
sys.path for `import engine`. It also makes worlds share one island build
per seed (tests/islands.py).
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

from ascii_adventurers.tests import islands  # noqa: E402  (after the path setup)

islands.install()


def timed(test):
    """Mark a test that measures wall-clock time. tests/parallel.py runs
    these on their own after everything else, so the other workers can't
    slow them down (a plain unittest run is one process anyway)."""
    test.timed = True
    return test
