"""
world/noise.py -- seeded, smooth "value noise" for terrain generation (numpy).

What it is: imagine a grid of random heights, one per lattice point, spaced
`scale` tiles apart. The noise value at any point is a smooth blend of the
four lattice heights around it, so it varies gently and continuously -- big
`scale` gives continent-sized patterns (the coastline), small gives local
detail (tree clumps, pools). Several layers ("octaves") at halving scales are
added with halving weights to get natural-looking, not-too-regular shapes
(fBm).

Why it's seamless across chunks: lattice heights come from a hash of
(seed, salt, lattice x, lattice y) -- a pure function of global coordinates --
so two neighbouring chunks see exactly the same lattice along their shared
edge, whatever order they're generated in. The hash is the same SplitMix64
chain as world/rng.hash_coords, done on uint64 arrays (numpy wraps on
overflow, which is exactly the mod 2**64 arithmetic we want).

Every function takes coordinate *arrays* that broadcast together (e.g. xs of
shape (1, w) and ys of shape (h, 1) give an (h, w) field), so a whole chunk
-- or a whole map -- is one call. When the points are dense relative to the
lattice (a chunk, at any scale), only the lattice box covering them is
hashed and then indexed; for sparse points (a zoomed-out map at a small
scale) the four corners of each point are hashed directly.
"""

from __future__ import annotations

import numpy as np

_GOLDEN = np.uint64(0x9E3779B97F4A7C15)
_M1 = np.uint64(0xBF58476D1CE4E5B9)
_M2 = np.uint64(0x94D049BB133111EB)
_S30, _S27, _S31, _S11 = np.uint64(30), np.uint64(27), np.uint64(31), np.uint64(11)
_INV53 = 1.0 / float(1 << 53)


def _mix64(z: np.ndarray) -> np.ndarray:
    z = (z ^ (z >> _S30)) * _M1
    z = (z ^ (z >> _S27)) * _M2
    return z ^ (z >> _S31)


def _as_u64(v) -> np.ndarray:
    """Two's-complement view, same as Python's `v & 0xFFFF_FFFF_FFFF_FFFF`."""
    return np.asarray(v, dtype=np.int64).astype(np.uint64)


def lattice(seed: int, salt: int, ix, iy) -> np.ndarray:
    """Random height in [0, 1) at integer lattice points (arrays broadcast).
    Equal to rng.hash_unit(seed, salt, ix, iy)."""
    with np.errstate(over="ignore"):
        h = _mix64((_GOLDEN ^ _as_u64(seed)) + _GOLDEN)
        h = _mix64((h ^ _as_u64(salt)) + _GOLDEN)
        h = _mix64((h ^ _as_u64(ix)) + _GOLDEN)
        h = _mix64((h ^ _as_u64(iy)) + _GOLDEN)
    return (h >> _S11).astype(np.float64) * _INV53


def _smooth(t):
    """Smoothstep: eases the blend so there are no visible grid creases."""
    return t * t * (3.0 - 2.0 * t)


def value_noise(seed: int, salt: int, xs, ys, scale: float) -> np.ndarray:
    """Noise in [0, 1) at world points (xs, ys), one lattice cell every
    `scale` tiles. xs and ys broadcast; the result has their joint shape."""
    fx = np.asarray(xs, dtype=np.float64) / scale
    fy = np.asarray(ys, dtype=np.float64) / scale
    fx0, fy0 = np.floor(fx), np.floor(fy)
    tx, ty = _smooth(fx - fx0), _smooth(fy - fy0)
    ix, iy = fx0.astype(np.int64), fy0.astype(np.int64)

    x_lo, x_hi = int(ix.min()), int(ix.max()) + 1
    y_lo, y_hi = int(iy.min()), int(iy.max()) + 1
    box = (x_hi - x_lo + 1) * (y_hi - y_lo + 1)
    if box <= max(4096, 4 * np.broadcast(ix, iy).size):
        # Dense: hash the lattice box once, then look corners up in it.
        lat = lattice(seed, salt,
                      np.arange(x_lo, x_hi + 1)[None, :],
                      np.arange(y_lo, y_hi + 1)[:, None])
        cx, cy = ix - x_lo, iy - y_lo
        a, b = lat[cy, cx], lat[cy, cx + 1]
        c, d = lat[cy + 1, cx], lat[cy + 1, cx + 1]
    else:
        a, b = lattice(seed, salt, ix, iy), lattice(seed, salt, ix + 1, iy)
        c, d = lattice(seed, salt, ix, iy + 1), lattice(seed, salt, ix + 1, iy + 1)
    top = a + (b - a) * tx
    bot = c + (d - c) * tx
    return top + (bot - top) * ty


def fbm(seed: int, salt: int, xs, ys, scale: float, octaves: int = 2) -> np.ndarray:
    """Fractal (multi-octave) value noise, normalized back to roughly [0, 1).
    Each octave halves the scale and the weight."""
    total, amp, norm = 0.0, 1.0, 0.0
    for o in range(octaves):
        total = total + value_noise(seed, salt + 101 * o, xs, ys, scale / (2 ** o)) * amp
        norm += amp
        amp *= 0.5
    return total / norm


def chunk_axes(x0: int, y0: int, w: int, h: int) -> tuple[np.ndarray, np.ndarray]:
    """Tile-center coordinates of a w x h block starting at (x0, y0), shaped
    to broadcast into an (h, w) grid: xs (1, w), ys (h, 1)."""
    xs = (np.arange(w, dtype=np.float64) + (x0 + 0.5))[None, :]
    ys = (np.arange(h, dtype=np.float64) + (y0 + 0.5))[:, None]
    return xs, ys


def value_noise_grid(seed: int, salt: int, x0: int, y0: int, w: int, h: int,
                     scale: float) -> np.ndarray:
    """value_noise over the w x h tiles starting at (x0, y0), sampled at
    tile centers. Returns an (h, w) array (index [y][x])."""
    return value_noise(seed, salt, *chunk_axes(x0, y0, w, h), scale)


def fbm_grid(seed: int, salt: int, x0: int, y0: int, w: int, h: int, scale: float,
             octaves: int = 2) -> np.ndarray:
    return fbm(seed, salt, *chunk_axes(x0, y0, w, h), scale, octaves)


def value_noise_at(seed: int, salt: int, x: float, y: float, scale: float) -> float:
    """Single-point value noise (same field as value_noise_grid)."""
    return float(value_noise(seed, salt, x, y, scale))


def fbm_at(seed: int, salt: int, x: float, y: float, scale: float, octaves: int = 2) -> float:
    """Single-point version of fbm_grid (same field)."""
    return float(fbm(seed, salt, x, y, scale, octaves))
