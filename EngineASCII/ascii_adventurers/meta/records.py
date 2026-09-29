"""
meta/records.py -- best-ever results across runs (save/records.json).

Each record is "the highest value any run reached". add_run() folds a
finished run in and returns which records it broke, for the NEW RECORD
highlights on the game-over screen.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from .files import SAVE_DIR, read_json, write_json
from .run_stats import RunStats

PATH = SAVE_DIR / "records.json"

# Record name -> how to read it off a run.
_FROM_RUN = {
    "longest_time": lambda r: r.time,
    "most_kills": lambda r: r.total_kills,
    "furthest": lambda r: r.furthest,
    "most_biomes": lambda r: len(r.biomes),
}


@dataclass
class Records:
    runs: int = 0
    total_kills: int = 0
    longest_time: float = 0.0
    most_kills: int = 0
    furthest: float = 0.0
    most_biomes: int = 0

    @classmethod
    def load(cls, path: Path | str = PATH) -> "Records":
        data = read_json(Path(path))
        r = cls()
        for name, default in asdict(r).items():
            v = data.get(name)
            if isinstance(v, (int, float)) and not isinstance(v, bool) and v >= 0:
                setattr(r, name, type(default)(v))
        return r

    def save(self, path: Path | str = PATH) -> bool:
        return write_json(Path(path), asdict(self))

    def add_run(self, run: RunStats) -> set[str]:
        """Fold a finished run in; returns the names of records it broke.
        (The very first run sets records without "breaking" them.)"""
        first = self.runs == 0
        self.runs += 1
        self.total_kills += run.total_kills
        broken = set()
        for name, read in _FROM_RUN.items():
            value = read(run)
            if value > getattr(self, name):
                setattr(self, name, type(getattr(self, name))(value))
                if not first:
                    broken.add(name)
        return broken
