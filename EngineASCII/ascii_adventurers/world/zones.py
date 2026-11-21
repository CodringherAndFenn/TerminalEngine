"""
world/zones.py -- the ocean zones' islands (M29, design/OCEAN.md 2).

Four islands out in the ocean, one due N/E/S/W of the centre (fixed places,
config.ZONE_PLACES), reached by water walking. Only the zones in
config.OCEAN_ZONES are built; the other places stay open sea.

A zone is one island ZONE_RADIUS tiles across (half), its coast wandering
by ZONE_COAST_AMPLITUDE (fBm, its own noise salt): a point belongs to it
when its distance from the zone's centre is under the coast radius there.
That's all the layout needs (world/layout.IslandLayout._classify paints
the zone's biome there); what grows on it is the zone's own plan
(world/paradise.py for Paradise).

Placement: each zone's centre lies on its compass line, far enough out that
its near shore is at least ZONE_GAP tiles past the main island's farthest
land within ZONE_FAN radians of that line. Measured from the actual coast
(it wanders by +-20% of the island's radius), so the crossing is about a
minute of water walking whatever the seed. Proof the rest of the island is
far enough too: land at angle t off the line and radius r is
sqrt(r^2 + D^2 - 2 r D cos t) >= D - r from the zone's centre (D out), so
inside the fan it's at least ZONE_GAP + the zone's radius away; outside the
fan, cos(ZONE_FAN) keeps it far further (about 1,600 tiles at the worst).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .. import config
from . import biomes
from .noise import fbm

_DIRS = {"N": (0.0, -1.0), "E": (1.0, 0.0), "S": (0.0, 1.0), "W": (-1.0, 0.0)}
_SALTS = {"paradise": 601, "hell": 607, "past": 613, "future": 617}


@dataclass
class Zone:
    key: str
    biome_id: int
    place: str                   # "N", "E", "S" or "W"
    cx: float                    # the island's centre
    cy: float
    seed: int
    radius: float = float(config.ZONE_RADIUS)
    plan: object = field(default=None, repr=False)   # its own layout (paradise.Plan), lazily

    @property
    def salt(self) -> int:
        return _SALTS.get(self.key, 619)

    @property
    def biome(self) -> biomes.Biome:
        return biomes.BY_ID[self.biome_id]

    @property
    def max_radius(self) -> float:
        """No point of the island is farther than this from its centre."""
        return self.radius * (1.0 + config.ZONE_COAST_AMPLITUDE) + 1.0

    @property
    def facing(self) -> tuple[float, float]:
        """The unit direction from the island toward the main island (its
        Gate's side)."""
        dx, dy = _DIRS[self.place]
        return -dx, -dy

    def coast(self, xs, ys) -> np.ndarray:
        """The coast's distance from the centre, at the given points."""
        return self.radius * (1.0 + config.ZONE_COAST_AMPLITUDE * 2.0 * (
            fbm(self.seed, self.salt, xs, ys, config.ZONE_COAST_SCALE, 4) - 0.5))

    def inside(self, xs, ys) -> np.ndarray:
        """True where the points are on the island (broadcasting xs, ys)."""
        xs, ys = np.broadcast_arrays(np.asarray(xs, dtype=np.float64),
                                     np.asarray(ys, dtype=np.float64))
        d = np.hypot(xs - self.cx, ys - self.cy)
        out = np.zeros(d.shape, dtype=bool)
        near = d < self.max_radius
        if near.any():
            out[near] = d[near] < self.coast(xs[near], ys[near])
        return out

    def near(self, x: float, y: float, margin: float = 0.0) -> bool:
        """(x, y) within the island's farthest reach plus `margin` tiles."""
        return math.hypot(x - self.cx, y - self.cy) < self.max_radius + margin

    def shore_along(self, ux: float, uy: float) -> float:
        """How far from the centre the shore is in direction (ux, uy): the
        farthest island point on that line, searched a tile at a time."""
        rs = np.arange(math.ceil(self.max_radius), -1, -1, dtype=np.float64)
        ins = self.inside(self.cx + ux * rs, self.cy + uy * rs)
        hit = np.flatnonzero(ins)
        return float(rs[hit[0]]) if hit.size else 0.0


def place_zones(layout) -> tuple[Zone, ...]:
    """The built zones (config.OCEAN_ZONES) for this layout. Called while
    the layout has no zones yet, so its biome queries see only the main
    island."""
    out = []
    for key in config.OCEAN_ZONES:
        place = config.ZONE_PLACES[key]
        dx, dy = _DIRS[place]
        far = _farthest_land(layout, math.atan2(dy, dx))
        z = Zone(key, biomes.ZONES[key].id, place, 0.0, 0.0, layout.seed)
        d = far + config.ZONE_GAP + z.max_radius
        z.cx, z.cy = round(dx * d), round(dy * d)
        out.append(z)
    return tuple(out)


def _farthest_land(layout, angle: float) -> float:
    """The main island's farthest land from the centre within ZONE_FAN of
    `angle` (13 rays, every 3 tiles from inside the coast's lowest reach
    out to the farthest any land can be)."""
    angles = angle + np.linspace(-config.ZONE_FAN, config.ZONE_FAN, 13)[:, None]
    r0 = layout.radius * (1.0 - config.COAST_AMPLITUDE) - config.BORDER_WOBBLE
    rs = np.arange(r0, layout.max_land_radius + 3, 3.0)[None, :]
    ids = layout.biome_ids(np.cos(angles) * rs, np.sin(angles) * rs)
    land = ids != biomes.OCEAN.id
    if not land.any():
        return r0
    return float(np.broadcast_to(rs, land.shape)[land].max())
