"""
world/rng.py -- deterministic integer hashing for reproducible worlds.

Python's built-in hash() is salted per process for strings, and the global
`random` module is shared state, so neither is safe for "same seed -> same
world". Everything that needs position-dependent randomness goes through
hash_coords() instead: a pure function of its integer inputs.
"""

from __future__ import annotations

_MASK = 0xFFFFFFFFFFFFFFFF  # work in unsigned 64-bit


def _mix64(z: int) -> int:
    """SplitMix64 finalizer: scrambles all 64 bits so nearby inputs give
    unrelated outputs."""
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9 & _MASK
    z = (z ^ (z >> 27)) * 0x94D049BB133111EB & _MASK
    return z ^ (z >> 31)


def hash_coords(*values: int) -> int:
    """Hash any number of integers (seed, x, y, salt...) to a 64-bit int."""
    h = 0x9E3779B97F4A7C15
    for v in values:
        h = _mix64((h ^ (v & _MASK)) + 0x9E3779B97F4A7C15 & _MASK)
    return h


def hash_unit(*values: int) -> float:
    """Like hash_coords, but a float in [0, 1)."""
    return (hash_coords(*values) >> 11) / float(1 << 53)
