"""
world/layout.py -- the island's large-scale plan: which biome is where.

Every point's biome is a pure function of (seed, x, y), evaluated with numpy
on whole arrays of points, so one call covers a chunk (generator.py), a
single tile (spawner, HUD) or a zoomed-out map (ui/maps.py), and they
all agree exactly. Nothing is precomputed, which is why the island can be
huge for free.

The maths, for a point at distance r and angle theta from the centre:

  * j, the border offset: a smooth meander of up to +-BORDER_WOBBLE tiles
    (fBm, BORDER_WOBBLE_SCALE across) plus small-scale jitter of up to
    +-BIOME_BORDER_JITTER tiles. It's added to every border test below, so
    all borders wander (headlands, inlets) and are ragged in clumps rather
    than smooth curves.
  * ocean  if r > coast radius. The coast radius is WORLD_RADIUS scaled by
    1 +- COAST_AMPLITUDE, following a many-octave fBm (big bays and capes
    with smaller wiggles on top).
  * plains if r < plains radius: WORLD_RADIUS * PLAINS_RADIUS_FRACTION,
    wobbling by +-PLAINS_EDGE_AMPLITUDE of itself.
  * otherwise the ring. theta is bent by a smooth noise field (up to
    +-BIOME_WARP radians) so slice borders curve; the jitter is converted
    from tiles to an angle (jitter / r) so the raggedness has the same size
    in tiles everywhere. The bent angle, minus the ring's rotation, picks
    one of len(BIOME_RING) equal slices, and the run's slice order says
    which biome that is.

The noise fields are fBm, whose values bunch around 0.5 (averaging octaves
pulls them toward the middle), so "(v - 0.5) * 2" is roughly -0.5..0.5 in
practice -- the amplitudes are upper bounds, not typical swings.
"""

from __future__ import annotations

import math
import random

import numpy as np

from .. import config
from . import biomes
from .noise import fbm, value_noise
from .rng import hash_coords

_TAU = 2.0 * math.pi

# Noise salts (distinct from the generator's).
_SALT_JITTER = 79
_SALT_COAST = 211
_SALT_PLAINS = 223
_SALT_WARP = 227
_SALT_WOBBLE = 229


class IslandLayout:
    def __init__(self, seed: int, radius: float | None = None) -> None:
        self.seed = seed
        self.radius = float(radius if radius is not None else config.WORLD_RADIUS)
        rng = random.Random(hash_coords(seed, 0x1A7))
        order = [biomes.BY_NAME[name] for name in config.BIOME_RING]
        if config.BIOME_RING_SHUFFLE:
            rng.shuffle(order)
        self.ring: tuple[biomes.Biome, ...] = tuple(order)
        self.rotation = rng.uniform(0.0, _TAU) if config.BIOME_RING_ROTATE else 0.0
        self._ring_ids = np.array([b.id for b in self.ring], dtype=np.uint8)
        self.plains_radius = self.radius * config.PLAINS_RADIUS_FRACTION
        # No point can be land beyond this (every wobble at its maximum).
        self.max_land_radius = (self.radius * (1 + config.COAST_AMPLITUDE)
                                + config.BORDER_WOBBLE + config.BIOME_BORDER_JITTER + 1)
        # Found once, when the run starts (~20 ms), not in the middle of
        # generating a chunk.
        self.spawn: tuple[int, int] = self._find_spawn()
        self._landmarks = None

    @property
    def landmarks(self) -> list:
        """The quest camps and boss lairs (world/landmarks.py), placed on
        first use (a few tens of ms) and the same for every use after."""
        if self._landmarks is None:
            from .landmarks import build_landmarks
            self._landmarks = build_landmarks(self)
        return self._landmarks

    def landmark(self, key: str):
        """The landmark built by `key` ("frog_camp", ...), or None."""
        return next((m for m in self.landmarks if m.key == key), None)

    # --- Queries ------------------------------------------------------------------------

    def biome_ids(self, xs, ys, jitter: bool = True) -> np.ndarray:
        """Biome ids (uint8) at world points; xs and ys broadcast. jitter=False
        leaves out the small ragged-edge noise (borders still meander, but
        aren't ragged)."""
        fields = self._fields(xs, ys)
        return self._classify(*fields, jitter=self._jitter(fields[0], fields[1]) if jitter else None)

    def biome_ids_both(self, xs, ys) -> tuple[np.ndarray, np.ndarray]:
        """(ragged, smooth) biome ids at once -- the chunk builder needs both
        and they share all the expensive fields."""
        fields = self._fields(xs, ys)
        jit = self._jitter(fields[0], fields[1])
        return self._classify(*fields, jitter=jit), self._classify(*fields, jitter=None)

    def _jitter(self, xs, ys) -> np.ndarray:
        """Small-scale ragged-edge offset, +-BIOME_BORDER_JITTER tiles."""
        return (value_noise(self.seed, _SALT_JITTER, xs, ys, config.BIOME_BORDER_SCALE) - 0.5) \
            * 2.0 * config.BIOME_BORDER_JITTER

    def _fields(self, xs, ys):
        """The smooth large-scale fields every biome decision uses."""
        xs = np.asarray(xs, dtype=np.float64)
        ys = np.asarray(ys, dtype=np.float64)
        seed = self.seed
        r = np.hypot(xs, ys)
        wobble = (fbm(seed, _SALT_WOBBLE, xs, ys, config.BORDER_WOBBLE_SCALE, 4) - 0.5) \
            * 2.0 * config.BORDER_WOBBLE
        coast = self.radius * (1.0 + config.COAST_AMPLITUDE * 2.0 * (
            fbm(seed, _SALT_COAST, xs, ys, config.COAST_SCALE, config.COAST_OCTAVES) - 0.5))
        plains = self.plains_radius * (1.0 + config.PLAINS_EDGE_AMPLITUDE * 2.0 * (
            fbm(seed, _SALT_PLAINS, xs, ys, config.PLAINS_EDGE_SCALE, 3) - 0.5))
        bend = config.BIOME_WARP * 2.0 * (
            fbm(seed, _SALT_WARP, xs, ys, config.BIOME_WARP_SCALE, 3) - 0.5)
        return xs, ys, r, wobble, coast, plains, bend

    def _classify(self, xs, ys, r, wobble, coast, plains, bend, jitter) -> np.ndarray:
        j = wobble if jitter is None else wobble + jitter
        theta = np.arctan2(ys, xs) + bend + j / np.maximum(r, 1.0) - self.rotation
        n = len(self.ring)
        sector = (np.floor(np.mod(theta, _TAU) / (_TAU / n)).astype(np.int64)) % n
        ids = self._ring_ids[sector]
        ids = np.where(r + j < plains, np.uint8(biomes.PLAINS.id), ids)
        ids = np.where(r + j > coast, np.uint8(biomes.OCEAN.id), ids)
        return ids.astype(np.uint8)

    def biome_at(self, x: float, y: float) -> biomes.Biome:
        """The biome at one world point (exactly what the generated tile
        there says)."""
        return biomes.BY_ID[int(self.biome_ids(x, y))]

    def all_ocean(self, x0: float, y0: float, x1: float, y1: float) -> bool:
        """True if the rect [x0, x1] x [y0, y1] is certainly all ocean (its
        nearest point is past the farthest the coast can reach)."""
        nx = min(max(0.0, x0), x1)
        ny = min(max(0.0, y0), y1)
        return math.hypot(nx, ny) > self.max_land_radius

    # --- The start -----------------------------------------------------------------------

    # `spawn` (set in __init__) is the start tile: the one nearest the centre
    # (tried on a spiral, SPAWN_SEARCH_STEP tiles apart) that isn't in a lake
    # and from which dry land connects out to SPAWN_ESCAPE_RADIUS tiles
    # away. Lakes are the only big obstacles in the plains that can't be shot
    # away, so checking the lake field is enough to guarantee you can drive
    # off. The generator clears SPAWN_CLEAR_RADIUS around it.

    def lake_mask(self, xs, ys, smooth_ids=None) -> np.ndarray:
        """True where the generator puts a lake: the lake field is above
        LAKE_MIN (two octaves, so shores are irregular rather than perfect
        ovals), in a biome that has lakes. That's decided by the *smooth*
        biome (no ragged jitter), so a lake never gets sprinkled along a
        ragged biome border."""
        from .generator import LAKE_BIOMES, SALT_LAKE   # (generator imports us)
        lake = fbm(self.seed, SALT_LAKE, xs, ys, config.LAKE_SCALE) > config.LAKE_MIN
        if smooth_ids is None:
            smooth_ids = self.biome_ids(xs, ys, jitter=False)
        return lake & np.isin(smooth_ids, LAKE_BIOMES)

    def _find_spawn(self) -> tuple[int, int]:
        step = config.SPAWN_SEARCH_STEP
        for ring in range(0, 60):
            # Candidates on the square ring `ring` steps out, nearest first.
            pts = {(x * step, y * step)
                   for x in range(-ring, ring + 1) for y in range(-ring, ring + 1)
                   if max(abs(x), abs(y)) == ring}
            for x, y in sorted(pts, key=lambda p: (p[0] ** 2 + p[1] ** 2, p)):
                if self._can_escape(x, y):
                    return x, y
        return 0, 0   # nothing found (can't happen with sane settings)

    def _can_escape(self, cx: int, cy: int) -> bool:
        """Flood-fill dry tiles from (cx, cy) within a square of radius
        SPAWN_ESCAPE_RADIUS; True if it reaches the square's edge. The fill
        is done on whole arrays: each pass grows the reached area by one
        tile in the four directions (and stays on dry tiles)."""
        r = config.SPAWN_ESCAPE_RADIUS
        c = config.SPAWN_CLEAR_RADIUS
        # The start itself must be dry (not a cleared islet in a lake).
        # Checked first on its own: it's small, and rules out most candidates.
        near = np.arange(-c, c + 1) + 0.5
        if self.lake_mask((near + cx)[None, :], (near + cy)[:, None]).any():
            return False
        xs = (np.arange(cx - r, cx + r + 1) + 0.5)[None, :]
        ys = (np.arange(cy - r, cy + r + 1) + 0.5)[:, None]
        dry = ~self.lake_mask(xs, ys)
        reached = np.zeros_like(dry)
        reached[r, r] = True
        while True:
            grown = reached.copy()
            grown[1:, :] |= reached[:-1, :]
            grown[:-1, :] |= reached[1:, :]
            grown[:, 1:] |= reached[:, :-1]
            grown[:, :-1] |= reached[:, 1:]
            grown &= dry
            if grown[0, :].any() or grown[-1, :].any() or grown[:, 0].any() or grown[:, -1].any():
                return True
            if (grown == reached).all():
                return False
            reached = grown

    def cardinal_sites(self) -> dict[str, tuple[float, float]]:
        """Centres of the four ocean regions reserved for a later milestone."""
        d = self.radius * config.CARDINAL_REGION_DISTANCE
        return {"N": (0.0, -d), "E": (d, 0.0), "S": (0.0, d), "W": (-d, 0.0)}
