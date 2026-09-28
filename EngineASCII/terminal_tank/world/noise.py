"""
world/noise.py -- seeded, smooth "value noise" for terrain generation.

What it is: imagine a grid of random heights, one per lattice point, spaced
`scale` tiles apart. The noise value at any point is a smooth blend of the
four lattice heights around it, so it varies gently and continuously -- big
`scale` gives continent-sized patterns (biomes), small gives local detail
(tree clumps, pools). Several layers ("octaves") at halving scales are added
with halving weights to get natural-looking, not-too-regular shapes (fBm).

Why it's seamless across chunks: lattice heights come from
hash_coords(seed, salt, lattice x, lattice y) -- a pure function of global
coordinates -- so two neighbouring chunks see exactly the same lattice along
their shared edge, whatever order they're generated in.

Speed: hashing is the expensive part in pure Python, so noise is evaluated
for a whole chunk at once. The lattice points covering the chunk are hashed
once (a handful for large scales), then each tile only does a cheap blend.
"""

from __future__ import annotations

import math

from .rng import hash_coords

_INV53 = 1.0 / float(1 << 53)


def _lattice(seed: int, salt: int, ix: int, iy: int) -> float:
    return (hash_coords(seed, salt, ix, iy) >> 11) * _INV53   # [0, 1)


def _smooth(t: float) -> float:
    """Smoothstep: eases the blend so there are no visible grid creases."""
    return t * t * (3.0 - 2.0 * t)


def value_noise_grid(
    seed: int, salt: int, x0: int, y0: int, w: int, h: int, scale: float
) -> list[list[float]]:
    """Noise in [0, 1) for the w x h tiles starting at (x0, y0), sampled at
    tile centers, one lattice cell every `scale` tiles. Returns rows[y][x]."""
    inv = 1.0 / scale
    lx0 = math.floor((x0 + 0.5) * inv)
    ly0 = math.floor((y0 + 0.5) * inv)
    lx1 = math.floor((x0 + w - 0.5) * inv) + 1
    ly1 = math.floor((y0 + h - 0.5) * inv) + 1
    lat = [
        [_lattice(seed, salt, ix, iy) for ix in range(lx0, lx1 + 1)]
        for iy in range(ly0, ly1 + 1)
    ]
    # Per-column lattice index and eased blend weight (same for every row).
    cols = []
    for x in range(w):
        fx = (x0 + x + 0.5) * inv
        ix = math.floor(fx)
        cols.append((ix - lx0, _smooth(fx - ix)))
    out = []
    for y in range(h):
        fy = (y0 + y + 0.5) * inv
        iy = math.floor(fy)
        ty = _smooth(fy - iy)
        top, bot = lat[iy - ly0], lat[iy - ly0 + 1]
        row = []
        for ci, tx in cols:
            a = top[ci] + (top[ci + 1] - top[ci]) * tx
            b = bot[ci] + (bot[ci + 1] - bot[ci]) * tx
            row.append(a + (b - a) * ty)
        out.append(row)
    return out


def fbm_grid(
    seed: int, salt: int, x0: int, y0: int, w: int, h: int, scale: float, octaves: int = 2
) -> list[list[float]]:
    """Fractal (multi-octave) value noise, normalized back to roughly [0, 1).
    Each octave halves the scale and the weight."""
    total = [[0.0] * w for _ in range(h)]
    amp, norm = 1.0, 0.0
    for o in range(octaves):
        layer = value_noise_grid(seed, salt + 101 * o, x0, y0, w, h, scale / (2 ** o))
        for y in range(h):
            trow, lrow = total[y], layer[y]
            for x in range(w):
                trow[x] += lrow[x] * amp
        norm += amp
        amp *= 0.5
    inv = 1.0 / norm
    return [[v * inv for v in row] for row in total]


def fbm_at(seed: int, salt: int, x: float, y: float, scale: float, octaves: int = 2) -> float:
    """Single-point version of fbm_grid (same field)."""
    total, amp, norm = 0.0, 1.0, 0.0
    for o in range(octaves):
        total += value_noise_at(seed, salt + 101 * o, x, y, scale / (2 ** o)) * amp
        norm += amp
        amp *= 0.5
    return total / norm


def value_noise_at(seed: int, salt: int, x: float, y: float, scale: float) -> float:
    """Single-point value noise (same field as value_noise_grid)."""
    fx, fy = x / scale, y / scale
    ix, iy = math.floor(fx), math.floor(fy)
    tx, ty = _smooth(fx - ix), _smooth(fy - iy)
    a = _lattice(seed, salt, ix, iy)
    b = _lattice(seed, salt, ix + 1, iy)
    c = _lattice(seed, salt, ix, iy + 1)
    d = _lattice(seed, salt, ix + 1, iy + 1)
    top = a + (b - a) * tx
    bot = c + (d - c) * tx
    return top + (bot - top) * ty
