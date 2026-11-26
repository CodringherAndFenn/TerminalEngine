"""
world/panopticon.py -- Panopticon's land (M32.1, design/OCEAN.md 35).

The east zone's island (world/zones.py places it): the machine city, chrome
and neon. WEDGES ROUND THE TOWER (Bentham's plan):

  * the watchtower at the centre, its hall of cells inside -- the
    Overseer's arena (M32.4-5): a round hall walled with tiers of cell doors
    and screens, pillars for cover, blast doors facing the sea wall (sealed
    until the seventh eye goes dark). A plaza round it;
  * four wedge districts round the plaza, one per compass quarter: the
    docks facing the main island, then the factory, the scrapyard behind the
    tower and the kept homes (which side the factory takes is the seed's).
    District walls run along the diagonals between them, from the plaza out
    to the sea, with gates (a blinking laser fence across each);
  * each district a grid of streets (glowing cyan lines down their middles)
    between tall blocks that break line of sight -- the docks' warehouses,
    the factory's sheds (conveyor belts down every other cross street, a
    press on them every other block), the homes' flats, the scrapyard's
    heaps of broken machines -- a main avenue down its middle (pylons along
    both edges), neon signs, empty lots;
  * the landmarks: the sea wall along the shore facing the main island (its
    lock gate where you arrive; the voice's cracked screen in the lock
    house, M32.4), the factory, the scrapyard, the kept homes, each in its
    own district; the seven camera masts (at least one in every district),
    each on a pad with three pylons round it;
  * live power: lines of pylons along the avenues and some streets, cables
    on the ground between them, puddles by some; laser fences across the
    gates, the avenues (sweeping) and some streets;
  * a steel quay all round, oily black water over drowned plating.

Worked out once per seed (zones.plan_of, cached on the zone). The big
buildings are ordinary world/landmarks.Landmark stamps; the grid, walls,
plazas, masts, power, fences, belts and presses, the quay and the oily sea
are painted per chunk by `paint` (from world/generator.build_chunk). The
dangers' timing lives in systems/panopticon.py; what's where is here
(`fences`, `presses`, `spans`, `lanes_near`).
"""

from __future__ import annotations

import math
import random

import numpy as np

from .. import config
from . import biomes, tiles
from .paradise import _ellipse_point
from .rng import hash_coords

_TAU = 2.0 * math.pi
DOCKS, FACTORY, SCRAPYARD, HOMES, TOWER = "docks", "factory", "scrapyard", "homes", "tower"
_STYLE = {   # each district's blocks: (facade, roof)
    DOCKS: (tiles.WAREHOUSE_WALL, tiles.WAREHOUSE_ROOF),
    FACTORY: (tiles.SHED_WALL, tiles.SHED_ROOF),
    SCRAPYARD: (tiles.LOOSE_SCRAP, tiles.SCRAP_HEAP),
    HOMES: (tiles.FLAT_WALL, tiles.FLAT_ROOF),
}
_DIR_BELT = {(1, 0): tiles.BELT_E, (-1, 0): tiles.BELT_W, (0, -1): tiles.BELT_N, (0, 1): tiles.BELT_S}


class Fence:
    """A laser fence: its beam from (x0, y0) to (x1, y1). "blink": on and
    off in a pattern; "sweep": always on, sliding `span` tiles along (nx, ny)
    and back. Timed by systems/panopticon.fence_now."""

    __slots__ = ("kind", "x0", "y0", "x1", "y1", "nx", "ny", "span", "phase")

    def __init__(self, kind, x0, y0, x1, y1, nx=0.0, ny=0.0, span=0.0, phase=0.0) -> None:
        self.kind, self.x0, self.y0, self.x1, self.y1 = kind, x0, y0, x1, y1
        self.nx, self.ny, self.span, self.phase = nx, ny, span, phase


def _mix(h):
    """A cheap integer hash (numpy int64 arrays or ints) -> [0, 1)."""
    h = (h ^ (h >> 15)) & 0xFFFFFFFF
    h = (h * 0x2C1B3C6D) & 0xFFFFFFFF
    h = (h ^ (h >> 12)) & 0xFFFFFFFF
    h = (h * 0x297A2D39) & 0xFFFFFFFF
    h = h ^ (h >> 15)
    return (h & 0xFFFF) / 65536.0


class Plan:
    """Where everything on Panopticon is, for one seed. `marks` are its
    landmarks; the rest is painted per chunk."""

    WALL = config.PANOPTICON_TOWER_WALL      # the tower's wall, tiles thick

    def __init__(self, layout, zone) -> None:
        from .landmarks import Landmark   # (landmarks imports the zones' plans)
        self._Landmark = Landmark
        self.zone = zone
        self.seed = layout.seed
        rng = random.Random(hash_coords(layout.seed, 0x9A70, zone.salt))
        cx, cy = int(zone.cx), int(zone.cy)
        self.cx, self.cy = cx, cy
        a, b = config.PANOPTICON_HALL_RADII
        w = self.WALL
        self.hall = (float(cx), float(cy), float(a), float(b))
        gx, gy = zone.facing
        self.facing = (gx, gy)
        self.phi = math.atan2(gy, gx)
        self.plaza = w + config.PANOPTICON_PLAZA               # the plaza's reach past the hall

        # The districts, one per quarter: the docks facing the main island,
        # the scrapyard behind the tower, the factory and the homes either side.
        side = rng.choice((1, 3))
        names = [DOCKS, "", SCRAPYARD, ""]
        names[side], names[4 - side] = FACTORY, HOMES
        self.names = tuple(names)
        self.axes = tuple((round(math.cos(self.phi + k * math.pi / 2)),
                           round(math.sin(self.phi + k * math.pi / 2))) for k in range(4))
        self.k_of = {n: k for k, n in enumerate(self.names)}
        self.grid = tuple(config.PANOPTICON_GRID[n] for n in self.names)       # (block, street)
        self.pitch = tuple(bl + st for bl, st in self.grid)
        # Where each district's grid starts (its first cross street at the
        # plaza's edge) and how far out its avenue reaches.
        self.u0 = tuple(round((a if ax else b) + self.plaza) for ax, ay in self.axes)
        self.shore_u = tuple(zone.shore_along(ax, ay) for ax, ay in self.axes)

        # The sea wall's lock gate on the shore facing the main island.
        thick, inset = config.PANOPTICON_SEA_WALL[1], config.PANOPTICON_SEA_WALL[2]
        r_gate = self.shore_u[0]
        self.gate = (round(cx + gx * (r_gate - inset - (thick - 1) / 2)),
                     round(cy + gy * (r_gate - inset - (thick - 1) / 2)))
        self._lock_end = r_gate - inset - thick - 8              # (the lock house's inland end)

        # The district walls along the diagonals, from the plaza out to sea,
        # each with its gates.
        self.walls: list[tuple[float, float, float, float, list[float]]] = []
        for j in range(4):
            ang = self.phi + (2 * j + 1) * math.pi / 4
            wx, wy = math.cos(ang), math.sin(ang)
            px, py = _ellipse_point(0.0, 0.0, a, b, wx, wy, self.plaza)
            r0 = math.hypot(px, py) - 1.0
            r1 = zone.shore_along(wx, wy) + 3.0
            gates = [r0 + f * (r1 - 3.0 - r0) for f in config.PANOPTICON_WALL_GATES]
            self.walls.append((wx, wy, r0, r1, gates))

        # Open ground the grid leaves clear: (x, y, hw, hh, tile).
        self.reserved: list[tuple[float, float, float, float, object]] = []
        for wx, wy, _, _, gates in self.walls:
            for g in gates:
                self.reserved.append((cx + 0.5 + wx * g, cy + 0.5 + wy * g, 7.0, 7.0, tiles.PLAZA))
        lx, ly = self.gate[0] - gx * (thick + 15), self.gate[1] - gy * (thick + 15)
        self.reserved.append((lx + 0.5, ly + 0.5, 8.0, 8.0, tiles.PLAZA))     # (the docks' plaza)

        # The landmarks, each in its own district; then the seven masts.
        along = config.PANOPTICON_SEA_WALL[0]
        self._placed: list[tuple[float, float, float, float]] = [
            (self.gate[0] - gx * 12, self.gate[1] - gy * 12,
             20 * abs(gx) + (along + 4) * abs(gy), 20 * abs(gy) + (along + 4) * abs(gx))]
        self.factory = self._site(rng, self.k_of[FACTORY], 33, 19)
        self.scrapyard = self._site(rng, self.k_of[SCRAPYARD], 36, 27)
        self.homes = self._site(rng, self.k_of[HOMES], 27, 15)
        for at, (hw, hh) in ((self.factory, (33, 19)), (self.scrapyard, (36, 27)),
                             (self.homes, (27, 15))):
            if at is not None:
                self.reserved.append((at[0] + 0.5, at[1] + 0.5, hw + 3.0, hh + 3.0, tiles.PLAZA))
        self.masts: list[tuple[int, int, str]] = []
        counts = {DOCKS: 1, FACTORY: 2, SCRAPYARD: 2, HOMES: 2}
        for name in (FACTORY, SCRAPYARD, HOMES, DOCKS):
            for _ in range(counts[name]):
                if len(self.masts) >= config.PANOPTICON_MASTS:
                    break
                at = (self._site(rng, self.k_of[name], 12, 12,
                                 apart=([(x, y) for x, y, _ in self.masts], config.PANOPTICON_MAST_GAP))
                      or self._site(rng, self.k_of[name], 12, 12))
                if at is not None:
                    self.masts.append((at[0], at[1], name))
                    self.reserved.append((at[0] + 0.5, at[1] + 0.5, 12.0, 12.0, tiles.MAST_PAD))
        self.quest = next((k for k, q in config.QUESTS.items() if q.biome == zone.key), "")

        # What's painted on top of the grid, tile by tile (later claims win).
        self._claims: dict[tuple[int, int], object] = {}
        self.presses: list[tuple[float, float, float]] = []    # (x, y, phase)
        self.press_at: dict[tuple[int, int], int] = {}         # a bed's tiles -> its press
        self.fences: list[Fence] = []
        self.pylons: list[tuple[int, int]] = []
        self.pylon_at: dict[tuple[int, int], int] = {}
        self.spans: list[tuple[int, int, float, float, float, float]] = []   # (i, j or -1, ax, ay, bx, by)
        self.pylon_spans: dict[int, list[int]] = {}
        self.span_tiles: dict[int, list[tuple[int, int]]] = {}  # its cables and puddles
        prng = random.Random(hash_coords(layout.seed, 0x9A71, zone.salt))
        self._street_presses(prng)
        self.marks = self._build_marks(rng)                     # (the factory's presses too)
        self._fences(prng)
        self._power(prng)
        self._mast_bases()
        self._index()

    # --- Geometry -------------------------------------------------------------------------

    def _k(self, dx, dy):
        """The district index (0: the docks) of offsets (dx, dy) from the
        centre (arrays or floats)."""
        ang = np.arctan2(dy, dx) - self.phi
        return (np.round(((ang + math.pi) % _TAU - math.pi) / (math.pi / 2)).astype(np.int64)) % 4

    def _uv(self, k, dx, dy):
        ax = np.take(np.array([q[0] for q in self.axes]), k)
        ay = np.take(np.array([q[1] for q in self.axes]), k)
        return dx * ax + dy * ay, -dx * ay + dy * ax

    def _tile_of(self, k: int, u: float, v: float) -> tuple[int, int]:
        """The tile at grid coordinates (u, v) of district k."""
        ax, ay = self.axes[k]
        return self.cx + round(u * ax - v * ay), self.cy + round(u * ay + v * ax)

    def in_plaza(self, x, y, grow: float = 0.0):
        """(x, y) inside the tower's plaza (grown by `grow`), the tower too."""
        cx, cy, a, b = self.hall
        g = self.plaza + grow
        return ((x - cx) / (a + g)) ** 2 + ((y - cy) / (b + g)) ** 2 < 1.0

    def in_hall(self, x: float, y: float, grow: float = 0.0) -> bool:
        cx, cy, a, b = self.hall
        return ((x - cx) / (a + grow)) ** 2 + ((y - cy) / (b + grow)) ** 2 < 1.0

    def district_at(self, x: float, y: float) -> str:
        """Which district (x, y) is in, or TOWER on the tower's plaza."""
        if self.in_plaza(x, y):
            return TOWER
        return self.names[int(self._k(np.float64(x - self.cx - 0.5), np.float64(y - self.cy - 0.5)))]

    def _wall_dist(self, X, Y):
        """How far points (centred offsets from the middle) are from the
        nearest district wall's line (inf beyond its ends)."""
        out = np.full(np.shape(X), np.inf)
        for wx, wy, r0, r1, _ in self.walls:
            along = X * wx + Y * wy
            perp = np.abs(-X * wy + Y * wx)
            out = np.where((along > r0 - 2) & (along < r1 + 2), np.minimum(out, perp), out)
        return out

    def _open(self, txs, tys, k: int, margin: float = 1.0) -> np.ndarray:
        """Which tiles are fit for a pylon, a post, a press: on the island
        (3 to spare), in district k, off the tower's plaza, the reserved
        ground and the walls."""
        txs = np.asarray(txs, dtype=np.float64)
        tys = np.asarray(tys, dtype=np.float64)
        X, Y = txs + 0.5, tys + 0.5
        z = self.zone
        d = np.hypot(X - z.cx, Y - z.cy)
        ok = d < z.coast(X, Y) - 3 - config.PANOPTICON_QUAY
        ok &= ~self.in_plaza(X, Y, 2.0)
        ok &= self._k(X - self.cx - 0.5, Y - self.cy - 0.5) == k
        ok &= self._wall_dist(X - self.cx - 0.5, Y - self.cy - 0.5) > 2.5
        for rx, ry, hw, hh, _ in self.reserved:
            ok &= ~((np.abs(X - rx) <= hw + margin) & (np.abs(Y - ry) <= hh + margin))
        return ok

    def _site(self, rng: random.Random, k: int, hw: float, hh: float, tries: int = 640,
              apart=None) -> tuple[int, int] | None:
        """A random centre for a (2hw x 2hh) footprint in district k: on the
        island with room to spare, its corners in the district (clear of its
        walls), off the avenue and the tower's plaza, PANOPTICON_SITE_GAP
        from every spot taken (`apart`: (points, d) -- and at least d from
        each of those). Candidates are drawn 32 at a time."""
        z = self.zone
        ax, ay = self.axes[k]
        across = hh if ax else hw                       # (its half-extent across the axis)
        gap = config.PANOPTICON_SITE_GAP
        big = max(hw, hh)
        r_lo, r_hi = self.u0[k] + big + 8, self.shore_u[k] - big - 14
        if r_hi <= r_lo:
            return None
        gxs = np.linspace(-hw - 6, hw + 6, 5)
        gys = np.linspace(-hh - 6, hh + 6, 5)
        for _ in range(tries // 32):
            pts = []
            for _ in range(32):
                ang = self.phi + k * math.pi / 2 + rng.uniform(-0.72, 0.72)
                r = rng.uniform(r_lo, r_hi)
                pts.append((round(self.cx + math.cos(ang) * r), round(self.cy + math.sin(ang) * r)))
            keep = []
            for x, y in pts:
                v = -(x - self.cx) * ay + (y - self.cy) * ax
                if abs(v) - across < config.PANOPTICON_AVENUE + 4:
                    continue
                if any(abs(x - px) < hw + phw + gap and abs(y - py) < hh + phh + gap
                       for px, py, phw, phh in self._placed):
                    continue
                if apart is not None and any(math.hypot(x - qx, y - qy) < apart[1] for qx, qy in apart[0]):
                    continue
                keep.append((x, y))
            if not keep:
                continue
            px_ = np.array([p[0] for p in keep], dtype=np.float64)[:, None, None]
            py_ = np.array([p[1] for p in keep], dtype=np.float64)[:, None, None]
            CX, CY = px_ + gxs[None, None, :], py_ + gys[None, :, None]
            on = z.inside(CX, CY).all(axis=(1, 2))
            inside_k = (self._k(CX - self.cx, CY - self.cy) == k).all(axis=(1, 2))
            clear = (self._wall_dist(CX - self.cx, CY - self.cy) > 3).all(axis=(1, 2))
            free = ~(self.in_plaza(CX, CY, 4.0).any(axis=(1, 2)))
            for (x, y), good in zip(keep, (on & inside_k & clear & free).tolist()):
                if good:
                    self._placed.append((x, y, hw, hh))
                    return x, y
        return None

    def district_gates(self, name: str) -> list[int]:
        """The fences across a district's gates (M32.2: they seal round you
        in lockdown): those of the walls either side of it."""
        k = self.k_of.get(name)
        if k is None:
            return []
        return self.wall_fences[k] + self.wall_fences[(k - 1) % 4]

    def _closeness(self, X, Y):
        """1 at the tower's plaza's edge down to 0 at the shore (arrays)."""
        cx, cy, a, b = self.hall
        inner = (a + b) / 2 + self.plaza
        r = np.hypot(X - cx, Y - cy)
        return np.clip(1.0 - (r - inner) / max(1.0, self.zone.radius - inner), 0.0, 1.0)

    def _lot(self, k, u, v):
        """Is the block holding grid coordinates (u, v) of district k an
        empty lot (paint's own dice; arrays)?"""
        P = np.take(np.array(self.pitch), k)
        u0 = np.take(np.array(self.u0), k)
        bu = np.floor_divide(u - u0, P)
        bv = np.floor_divide(v, P)
        return _mix((bu * 0x9E3779B1 + bv * 0x85EBCA77 + k * 0xC2B2AE3D + self.seed * 31)
                    & 0xFFFFFFFF) < config.PANOPTICON_LOTS

    def _grid_spots(self, salt: int, pick):
        """Spots on every district's grid (M32.2): `pick(k, i, j, uc, vc,
        hu, hv, rng)` lists candidates (k, u, v, facing u, facing v) round
        crossing (i, j) (its centre (uc, vc), half-widths hu across the
        cross street, hv across the street along the axis); those on open
        ground are kept, by the PANOPTICON_CAMERAS-style chance the caller
        folds in. Returns [(x, y, fx, fy)] (tile middles, a unit facing)."""
        rng = random.Random(hash_coords(self.seed, salt, self.zone.salt))
        cand = []
        for k in range(4):
            p, street = self.pitch[k], self.grid[k][1]
            hu = street // 2
            n_u = int((self.shore_u[k] - self.u0[k]) / p) + 1
            for i in range(n_u):
                uc = self.u0[k] + i * p
                jn = int(uc / p) + 1
                for j in range(-jn, jn + 1):
                    hv = config.PANOPTICON_AVENUE if j == 0 else hu
                    cand += pick(k, i, j, uc, j * p, hu, hv, rng)
        if not cand:
            return []
        out = []
        for k in range(4):
            mine = [c for c in cand if c[0] == k]
            if not mine:
                continue
            ax, ay = self.axes[k]
            tx = np.array([self._tile_of(k, c[1], c[2])[0] for c in mine])
            ty = np.array([self._tile_of(k, c[1], c[2])[1] for c in mine])
            ok = self._open(tx, ty, k, margin=0.0)
            for c, x, y, good in zip(mine, tx.tolist(), ty.tolist(), ok.tolist()):
                if good and (x, y) not in self._claims:
                    fu, fv = c[3], c[4]
                    out.append((x + 0.5, y + 0.5, fu * ax - fv * ay, fu * ay + fv * ax))
        return out

    def camera_spots(self) -> list[tuple[float, float, float, float]]:
        """The cameras' poles (M32.2): at one corner of a street crossing, a
        chance of PANOPTICON_CAMERAS[0] by the plaza down to [1] at the
        shore; each faces the crossing (diagonally). Cached."""
        got = getattr(self, "_cameras", None)
        if got is not None:
            return got
        near, far = config.PANOPTICON_CAMERAS[0], config.PANOPTICON_CAMERAS[1]

        def pick(k, i, j, uc, vc, hu, hv, rng):
            x, y = self._tile_of(k, uc, vc)
            chance = far + (near - far) * float(self._closeness(np.float64(x), np.float64(y)))
            if rng.random() >= chance:
                return []
            su, sv = rng.choice((-1, 1)), rng.choice((-1, 1))
            return [(k, uc + su * hu, vc + sv * hv, -su / math.sqrt(2), -sv / math.sqrt(2))]

        self._cameras = self._grid_spots(0x9A72, pick)
        return self._cameras

    def turret_spots(self) -> list[tuple[float, float, float, float]]:
        """The turrets (M32.2): on the pavement against a block's wall
        (never an empty lot's), halfway along it, a chance of
        PANOPTICON_TURRETS[0] a side by the plaza down to [1] at the
        shore; each faces the street. Cached."""
        got = getattr(self, "_turrets", None)
        if got is not None:
            return got
        near, far = config.PANOPTICON_TURRETS[0], config.PANOPTICON_TURRETS[1]

        def pick(k, i, j, uc, vc, hu, hv, rng):
            p = self.pitch[k]
            out = []
            for s in (-1, 1):
                # along the axis street (j), the block's side between crossings i and i+1
                u, v = uc + p // 2, vc + s * hv
                if not bool(self._lot(np.int64(k), np.int64(u), np.int64(v + s))):
                    out.append((k, u, v, 0.0, -float(s)))
                # along the cross street (i), between crossings j and j+1
                u, v = uc + s * hu, vc + p // 2
                if not bool(self._lot(np.int64(k), np.int64(u + s), np.int64(v))):
                    out.append((k, u, v, -float(s), 0.0))
            keep = []
            for c in out:
                x, y = self._tile_of(k, c[1], c[2])
                chance = far + (near - far) * float(self._closeness(np.float64(x), np.float64(y)))
                if rng.random() < chance:
                    keep.append(c)
            return keep

        self._turrets = self._grid_spots(0x9A73, pick)
        return self._turrets

    def lanes_near(self, x: float, y: float) -> list[tuple[float, float, float, float, float]]:
        """The streets nearest (x, y) a sweeper could wash: (x, y) on its
        middle line near the point, the line's direction, its half-width --
        the two nearest along the district's axis and the two nearest across
        it (the trimming to the street's open length is the caller's)."""
        if self.in_plaza(x, y):
            return []
        dx, dy = math.floor(x) - self.cx, math.floor(y) - self.cy
        k = int(self._k(np.float64(dx), np.float64(dy)))
        ax, ay = self.axes[k]
        p, street = self.pitch[k], self.grid[k][1]
        u, v = dx * ax + dy * ay, -dx * ay + dy * ax
        out = []
        jv = v / p
        for j in sorted({math.floor(jv), math.ceil(jv)}):
            vc = j * p
            half = config.PANOPTICON_AVENUE + 0.5 if j == 0 else street / 2
            tx, ty = self._tile_of(k, u, vc)
            out.append((tx + 0.5, ty + 0.5, float(ax), float(ay), half))
        iu = (u - self.u0[k]) / p
        for i in sorted({math.floor(iu), math.ceil(iu)}):
            uc = self.u0[k] + i * p
            tx, ty = self._tile_of(k, uc, v)
            out.append((tx + 0.5, ty + 0.5, float(-ay), float(ax), street / 2))
        return out

    # --- Belts, presses, fences, power ----------------------------------------------------

    def _claim(self, tx: int, ty: int, tile, over: bool = True) -> None:
        if over or (tx, ty) not in self._claims:
            self._claims[(tx, ty)] = tile

    def _street_presses(self, rng: random.Random) -> None:
        """A press on the factory district's belts every other block: its
        bed across the belt (3 x 3), its frame on the pavement either side."""
        k = self.k_of[FACTORY]
        p = self.pitch[k]
        avenue = config.PANOPTICON_AVENUE
        n_u = int((self.shore_u[k] - self.u0[k]) / p)
        cand = []
        for ci in range(1, n_u + 1, 2):
            uc = self.u0[k] + ci * p
            for j in range(-ci - 2, ci + 3):
                if (ci + j) % 2:
                    continue
                vp = j * p + p // 2
                if abs(vp) <= avenue + 4:
                    continue
                cand.append((uc, vp))
        if not cand:
            return
        txy = [self._tile_of(k, u, v) for u, v in cand]
        ok = self._open([t[0] for t in txy], [t[1] for t in txy], k, margin=3.0)
        for (uc, vp), good in zip(cand, ok.tolist()):
            if not good:
                continue
            idx = len(self.presses)
            bed = [self._tile_of(k, uc + du, vp + dv) for du in (-1, 0, 1) for dv in (-1, 0, 1)]
            for t in bed:
                self._claim(*t, tiles.PRESS_BED)
                self.press_at[t] = idx
            for du in (-2, 2):
                for dv in (-1, 0, 1):
                    self._claim(*self._tile_of(k, uc + du, vp + dv), tiles.PRESS_FRAME)
            x, y = self._tile_of(k, uc, vp)
            self.presses.append((x + 0.5, y + 0.5, rng.uniform(0.0, config.PANOPTICON_PRESS[0])))

    def _track(self, x0: float, y0: float, x1: float, y1: float) -> None:
        n = max(1, int(math.hypot(x1 - x0, y1 - y0) * 2))
        for q in range(n + 1):
            f = q / n
            self._claim(math.floor(x0 + (x1 - x0) * f), math.floor(y0 + (y1 - y0) * f),
                        tiles.LASER_TRACK, over=False)

    def _fences(self, rng: random.Random) -> None:
        """A blinking fence across every district gate; two sweeping ones
        across every avenue; PANOPTICON_FENCES more across random streets."""
        laser = config.PANOPTICON_LASER
        period = laser[3] + laser[4]
        cx, cy = self.cx + 0.5, self.cy + 0.5
        half = config.PANOPTICON_GATE_W / 2
        self.wall_fences: list[list[int]] = []          # (M32.2: each wall's gates' fences)
        for wx, wy, _, _, gates in self.walls:
            self.wall_fences.append([])
            for g in gates:
                a0, a1 = g - half + 0.5, g + half - 0.5
                f = Fence("blink", cx + wx * a0, cy + wy * a0, cx + wx * a1, cy + wy * a1,
                          phase=rng.uniform(0, period))
                self.wall_fences[-1].append(len(self.fences))
                self.fences.append(f)
                self._track(f.x0, f.y0, f.x1, f.y1)
                for end in (g - half - 0.5, g + half + 0.5):
                    self._claim(math.floor(cx + wx * end), math.floor(cy + wy * end), tiles.LASER_POST)
        span, sweep_t = laser[5], laser[6]
        avenue = config.PANOPTICON_AVENUE
        self._avenue_fences: list[tuple[int, float]] = []
        for k in range(4):
            ax, ay = self.axes[k]
            u_end = self._avenue_end(k)
            for frac in (0.42, 0.68):
                uf = round(self.u0[k] + frac * (u_end - self.u0[k]))
                self._avenue_fences.append((k, uf))
                (t0, t1) = self._tile_of(k, uf, -avenue), self._tile_of(k, uf, avenue)
                f = Fence("sweep", t0[0] + 0.5 - ay * -0.5, t0[1] + 0.5 + ax * -0.5,
                          t1[0] + 0.5 - ay * 0.5, t1[1] + 0.5 + ax * 0.5,
                          float(ax), float(ay), span, rng.uniform(0, sweep_t))
                self.fences.append(f)
                for du in range(-round(span / 2), round(span / 2) + 1):
                    for dv in range(-avenue, avenue + 1):
                        self._claim(*self._tile_of(k, uf + du, dv), tiles.LASER_TRACK, over=False)
        for k in range(4):
            p, street = self.pitch[k], self.grid[k][1]
            sh = street // 2
            ax, ay = self.axes[k]
            n_u = int((self.shore_u[k] - self.u0[k]) / p)
            made = 0
            for _ in range(60):
                if made >= config.PANOPTICON_FENCES or n_u < 3:
                    break
                i = rng.randint(1, max(1, n_u - 2))
                j = rng.choice([q for q in range(-i, i + 1) if q != 0] or [1])
                uf, vc = self.u0[k] + i * p + p // 2, j * p
                blink = rng.random() < 0.5
                if blink:
                    pts = [self._tile_of(k, uf, vc + dv) for dv in range(-sh, sh + 1)]
                else:
                    pts = [self._tile_of(k, uf + du, vc + dv) for du in range(-round(span / 2),
                                                                             round(span / 2) + 1)
                           for dv in (-sh, sh)]
                ok = self._open([t[0] for t in pts], [t[1] for t in pts], k)
                if not ok.all() or any(t in self._claims for t in pts):
                    continue
                made += 1
                if blink:
                    a = self._tile_of(k, uf, vc - (sh - 1))
                    b = self._tile_of(k, uf, vc + (sh - 1))
                    f = Fence("blink", a[0] + 0.5 + ay * 0.5, a[1] + 0.5 - ax * 0.5,
                              b[0] + 0.5 - ay * 0.5, b[1] + 0.5 + ax * 0.5, phase=rng.uniform(0, period))
                    self._track(f.x0, f.y0, f.x1, f.y1)
                    self._claim(*self._tile_of(k, uf, vc - sh), tiles.LASER_POST)
                    self._claim(*self._tile_of(k, uf, vc + sh), tiles.LASER_POST)
                else:
                    a = self._tile_of(k, uf, vc - sh)
                    b = self._tile_of(k, uf, vc + sh)
                    f = Fence("sweep", a[0] + 0.5 + ay * 0.5, a[1] + 0.5 - ax * 0.5,
                              b[0] + 0.5 - ay * 0.5, b[1] + 0.5 + ax * 0.5,
                              float(ax), float(ay), span, rng.uniform(0, sweep_t))
                    for du in range(-round(span / 2), round(span / 2) + 1):
                        for dv in range(-sh, sh + 1):
                            self._claim(*self._tile_of(k, uf + du, vc + dv), tiles.LASER_TRACK, over=False)
                self.fences.append(f)

    def _avenue_end(self, k: int) -> float:
        """How far out district k's avenue runs (the docks': to the lock house)."""
        if k == 0:
            return self._lock_end - 2
        return self.shore_u[k] - config.PANOPTICON_QUAY - 4

    def _line(self, pts: list[tuple[int, int]], rng: random.Random, inward: tuple[float, float]) -> None:
        """A line of pylons through `pts` (in order), cables between them,
        a puddle by some spans (on the `inward` side)."""
        idx = []
        for t in pts:
            i = self.pylon_at.get(t)
            if i is None:
                i = len(self.pylons)
                self.pylons.append(t)
                self.pylon_at[t] = i
                self._claim(*t, tiles.PYLON)
            idx.append(i)
        for i, j in zip(idx, idx[1:]):
            self._span(i, j, *self.pylons[i], *self.pylons[j], rng, inward)

    def _span(self, i: int, j: int, ax: int, ay: int, bx: int, by: int, rng, inward) -> None:
        s = len(self.spans)
        self.spans.append((i, j, ax + 0.5, ay + 0.5, bx + 0.5, by + 0.5))
        self.pylon_spans.setdefault(i, []).append(s)
        if j >= 0:
            self.pylon_spans.setdefault(j, []).append(s)
        n = max(abs(bx - ax), abs(by - ay))
        mine = []
        for q in range(1, n):
            t = (ax + round((bx - ax) * q / n), ay + round((by - ay) * q / n))
            if t not in self._claims:
                self._claim(*t, tiles.CABLE)
                mine.append(t)
        if j >= 0 and rng.random() < config.PANOPTICON_PUDDLES and n > 3:
            mx = (ax + bx) / 2 + 0.5 + inward[0] * 1.6
            my = (ay + by) / 2 + 0.5 + inward[1] * 1.6
            r = rng.uniform(1.4, 2.2)
            for ty in range(math.floor(my - r), math.ceil(my + r) + 1):
                for tx in range(math.floor(mx - r), math.ceil(mx + r) + 1):
                    if math.hypot(tx + 0.5 - mx, ty + 0.5 - my) < r and (tx, ty) not in self._claims:
                        self._claim(tx, ty, tiles.PUDDLE)
                        mine.append((tx, ty))
        self.span_tiles[s] = mine

    def _power(self, rng: random.Random) -> None:
        """Pylons along both edges of every avenue, PANOPTICON_POWER_LINES
        more lines along random streets in each district (a few spans each),
        three round every mast."""
        every = config.PANOPTICON_PYLON_EVERY
        avenue = config.PANOPTICON_AVENUE
        span = config.PANOPTICON_LASER[5]
        for k in range(4):
            ax, ay = self.axes[k]
            fences = [uf for kk, uf in self._avenue_fences if kk == k]
            us = np.arange(self.u0[k] + 3, self._avenue_end(k), every)
            for s in (-1, 1):
                pts = [self._tile_of(k, float(u), s * avenue) for u in us]
                if not pts:
                    continue
                ok = self._open([t[0] for t in pts], [t[1] for t in pts], k, margin=0.0).tolist()
                for q, u in enumerate(us.tolist()):
                    if any(abs(u - uf) < span / 2 + 2 for uf in fences):
                        ok[q] = False
                self._runs(pts, ok, rng, (-s * -ay, -s * ax))
        for k in range(4):
            p, street = self.pitch[k], self.grid[k][1]
            sh = street // 2
            n_u = int((self.shore_u[k] - self.u0[k]) / p)
            made = 0
            for _ in range(40):
                if made >= config.PANOPTICON_POWER_LINES or n_u < 3:
                    break
                n = rng.randint(3, 6)
                s = rng.choice((-1, 1))
                i0 = rng.randint(1, max(1, n_u - 2))
                ax, ay = self.axes[k]
                if rng.random() < 0.5:                         # (along a street down the district)
                    j = rng.choice([q for q in range(-i0, i0 + 1) if q != 0] or [1])
                    u_s = self.u0[k] + i0 * p + sh + 1
                    pts = [self._tile_of(k, u_s + m * every, j * p + s * sh) for m in range(n + 1)]
                    inward = (-s * -ay, -s * ax)
                else:                                          # (along a cross street)
                    j0 = rng.randint(-i0, i0)
                    d = rng.choice((-1, 1))
                    uc = self.u0[k] + i0 * p + s * sh
                    pts = [self._tile_of(k, uc, j0 * p + sh + 1 + d * m * every) for m in range(n + 1)]
                    inward = (-s * ax, -s * ay)
                ok = self._open([t[0] for t in pts], [t[1] for t in pts], k, margin=0.0).tolist()
                ok = [good and t not in self._claims for t, good in zip(pts, ok)]
                if sum(ok) < 3:
                    continue
                made += 1
                self._runs(pts, ok, rng, inward)
        r = config.PANOPTICON_MAST_PYLONS
        for x, y, _ in self.masts:
            a0 = rng.uniform(0, _TAU)
            for q in range(3):
                ang = a0 + q * _TAU / 3
                t = (x + round(math.cos(ang) * r), y + round(math.sin(ang) * r))
                i = len(self.pylons)
                self.pylons.append(t)
                self.pylon_at[t] = i
                self._claim(*t, tiles.PYLON)
                ex, ey = x + round(math.cos(ang) * 2), y + round(math.sin(ang) * 2)
                self._span(i, -1, t[0], t[1], ex, ey, rng, (0.0, 0.0))

    def _runs(self, pts, ok, rng, inward) -> None:
        """Lines through each run of good points (two or more)."""
        run: list[tuple[int, int]] = []
        for t, good in zip(list(pts) + [None], list(ok) + [False]):
            if good:
                run.append(t)
                continue
            if len(run) >= 2:
                self._line(run, rng, inward)
            run = []

    def _mast_bases(self) -> None:
        for x, y, _ in self.masts:
            for j in (-1, 0, 1):
                for i in (-1, 0, 1):
                    self._claim(x + i, y + j, tiles.MAST_BASE)

    def _index(self) -> None:
        """Bucket the fences, the spans and the presses by chunk (for the
        dangers near a hero, and the drawing), and the painted tiles."""
        n = config.CHUNK_SIZE
        self._fence_idx: dict[tuple[int, int], list[int]] = {}
        for i, f in enumerate(self.fences):
            key = (math.floor((f.x0 + f.x1) / 2) // n, math.floor((f.y0 + f.y1) / 2) // n)
            self._fence_idx.setdefault(key, []).append(i)
        self._span_idx: dict[tuple[int, int], list[int]] = {}
        for s, (_, _, ax, ay, bx, by) in enumerate(self.spans):
            key = (math.floor((ax + bx) / 2) // n, math.floor((ay + by) / 2) // n)
            self._span_idx.setdefault(key, []).append(s)
        self._press_idx: dict[tuple[int, int], list[int]] = {}
        for i, (x, y, _) in enumerate(self.presses):
            self._press_idx.setdefault((math.floor(x) // n, math.floor(y) // n), []).append(i)
        self.press_beds: dict[int, list[tuple[int, int]]] = {}
        for t, i in self.press_at.items():
            self.press_beds.setdefault(i, []).append(t)
        self._points: dict[tuple[int, int], list[tuple[int, int, object]]] = {}
        for (tx, ty), t in self._claims.items():
            self._points.setdefault((tx // n, ty // n), []).append((tx, ty, t))
        # (each span's own tiles: those still its cable or puddle once
        # everything is painted)
        for s, mine in self.span_tiles.items():
            self.span_tiles[s] = [t for t in mine if self._claims.get(t) in (tiles.CABLE, tiles.PUDDLE)]

    def near(self, idx: dict, x: float, y: float, reach: int = 1) -> list[int]:
        """The items of a chunk index (`_fence_idx`, `_span_idx`,
        `_press_idx`) within `reach` chunks of (x, y)."""
        n = config.CHUNK_SIZE
        kx, ky = math.floor(x) // n, math.floor(y) // n
        out: list[int] = []
        for j in range(ky - reach, ky + reach + 1):
            for i in range(kx - reach, kx + reach + 1):
                out += idx.get((i, j), ())
        return out

    # --- Landmarks --------------------------------------------------------------------

    def _mark(self, key: str, kind: str, name: str, cells: dict, cx: float, cy: float,
              land_only: bool = False, **kw):
        """A Landmark from a {(tx, ty): tile} dict (None round them)."""
        if land_only and cells:
            pts = np.array(list(cells), dtype=np.float64)
            ok = self.zone.inside(pts[:, 0] + 0.5, pts[:, 1] + 0.5)
            cells = {p: cells[p] for p, good in zip(list(cells), ok.tolist()) if good}
        if not cells:
            return None
        xs = [p[0] for p in cells]
        ys = [p[1] for p in cells]
        x0, y0 = min(xs), min(ys)
        rows = [[None] * (max(xs) - x0 + 1) for _ in range(max(ys) - y0 + 1)]
        for (tx, ty), t in cells.items():
            rows[ty - y0][tx - x0] = t
        return self._Landmark(key, kind, "panopticon", name, x0, y0, rows, cx=cx, cy=cy, **kw)

    def _build_marks(self, rng: random.Random) -> list:
        out = [self._tower(), self._sea_wall()]
        if self.factory is not None:
            out.append(self._factory(rng))
        if self.scrapyard is not None:
            out.append(self._scrapyard(rng))
        if self.homes is not None:
            out.append(self._homes(rng))
        return [m for m in out if m is not None]

    def _tower(self):
        """The watchtower, the hall of cells inside it: the Overseer's arena
        (M32.4-5). Tiers of cell doors and screens round its wall, pillars
        for cover, blast doors facing the sea wall (sealed until the seventh
        eye goes dark)."""
        cx, cy, a, b = self.hall
        w = self.WALL
        gx, gy = self.facing
        x0, x1 = math.floor(cx - a - w - 1), math.ceil(cx + a + w + 1)
        y0, y1 = math.floor(cy - b - w - 1), math.ceil(cy + b + w + 1)
        X = np.arange(x0, x1 + 1)[None, :] + 0.5
        Y = np.arange(y0, y1 + 1)[:, None] + 0.5
        e_in = ((X - cx) / a) ** 2 + ((Y - cy) / b) ** 2
        e_out = ((X - cx) / (a + w)) ** 2 + ((Y - cy) / (b + w)) ** 2
        inside = e_in < 1.0
        wall = (~inside) & (e_out < 1.0)
        cells_ring = wall & (((X - cx) / (a + 1.5)) ** 2 + ((Y - cy) / (b + 1.5)) ** 2 < 1.0)
        across = np.abs((X - cx) * -gy + (Y - cy) * gx)
        along = (X - cx) * gx + (Y - cy) * gy
        gate = wall & (across <= config.PANOPTICON_HALL_GATE / 2) & (along > 0)
        tier = np.floor((np.arctan2(Y - cy, X - cx) + math.pi) / _TAU * 96).astype(np.int64)
        js, is_ = np.nonzero(inside | wall)
        cells: dict = {}
        gate_tiles = []
        for j, i in zip(js.tolist(), is_.tolist()):
            p = (x0 + i, y0 + j)
            if gate[j, i]:
                cells[p] = tiles.BLAST_DOOR
                gate_tiles.append(p)
            elif cells_ring[j, i]:
                cells[p] = tiles.CELL_SCREEN if tier[j, i] % 4 == 3 else tiles.CELL_DOOR
            elif wall[j, i]:
                cells[p] = tiles.TOWER_WALL
            else:
                cells[p] = tiles.CELL_FLOOR
        pillars = []
        n = config.PANOPTICON_HALL_PILLARS
        for q in range(n):
            ang = self.phi + (q + 0.5) * _TAU / n
            px, py = cx + math.cos(ang) * a * 0.55, cy + math.sin(ang) * b * 0.55
            for dj in (-1, 0, 1):
                for di in (-1, 0, 1):
                    cells[(math.floor(px) + di, math.floor(py) + dj)] = tiles.HALL_PILLAR
            pillars.append((math.floor(px) + 0.5, math.floor(py) + 0.5))
        # (the quest's lair, M32.4: the blast doors open when the seventh eye
        # goes dark, close behind you for the fight, open when it's won; the
        # eye hangs in the middle)
        return self._mark("panopticon_tower", "court", "The Watchtower", cells, cx, cy,
                          gate=gate_tiles, radii=(a, b), floor=tiles.CELL_FLOOR,
                          props={"seal": tiles.BLAST_DOOR, "barred": True, "facing": (gx, gy),
                                 "pillars": pillars},
                          quest=self.quest, spots=[(cx, cy)])

    def _sea_wall(self):
        """The sea wall along the shore facing the main island: steel, its
        lock gate open in the middle (where you arrive), the lock house
        behind it with the voice's cracked screen (M32.4)."""
        z = self.zone
        cx, cy = self.cx + 0.5, self.cy + 0.5
        gx, gy = self.facing
        along, thick, inset, gate_w = config.PANOPTICON_SEA_WALL
        r_mid = self.shore_u[0]
        offs = np.arange(-along, along + 0.25, 0.5)
        thetas = self.phi + offs / r_mid
        rs = np.arange(math.floor(r_mid - 50), math.ceil(z.max_radius) + 2, dtype=np.float64)
        X = cx + np.cos(thetas)[:, None] * rs[None, :]
        Y = cy + np.sin(thetas)[:, None] * rs[None, :]
        ins = z.inside(X, Y)
        cells: dict = {}
        for q, (off, t) in enumerate(zip(offs.tolist(), thetas.tolist())):
            hit = np.flatnonzero(ins[q])
            if not hit.size:
                continue
            shore = float(rs[hit[-1]])
            for d in range(thick):
                r = shore - inset - d
                p = (math.floor(cx + math.cos(t) * r), math.floor(cy + math.sin(t) * r))
                cells[p] = tiles.LOCK_FLOOR if abs(off) <= gate_w / 2 else tiles.SEA_WALL
        # The lock house: a walled chamber inland of the gate.
        gtx, gty = self.gate
        ux, uy = -gy, gx                                    # along the shore
        vx, vy = -gx, -gy                                   # inland
        half = gate_w // 2
        screen = None
        for d in range(2, 2 + 9):
            for i in range(-half - 1, half + 2):
                p = (gtx + ux * i + vx * d, gty + uy * i + vy * d)
                edge = abs(i) == half + 1
                cells[(round(p[0]), round(p[1]))] = tiles.SEA_WALL if edge else tiles.LOCK_FLOOR
            if d == 6:
                sp = (round(gtx + ux * -(half + 1) + vx * d), round(gty + uy * -(half + 1) + vy * d))
                cells[sp] = tiles.VOICE_SCREEN
                screen = (sp[0] + 0.5 + ux, sp[1] + 0.5 + uy)
        # (M32.4: the voice's camp: its screen in the lock house, the seven
        # masts its spots)
        return self._mark("panopticon_sea_wall", "zone", "The Sea Wall", cells, gtx + 0.5, gty + 0.5,
                          land_only=True, props={"screen": screen, "gate": self.gate})

    def _factory(self, rng: random.Random):
        """The factory: an assembly hall, belts along its length (presses on
        them, robot arms beside them), half-built robots at their ends and
        down the middle; doors on every side."""
        fx, fy = self.factory
        cells: dict = {}
        for j in range(-19, 19):
            for i in range(-33, 33):
                edge = i in (-33, 32) or j in (-19, 18)
                door = (j in (-19, 18) and abs(i) <= 2) or (i in (-33, 32) and -2 <= j <= 2)
                cells[(fx + i, fy + j)] = tiles.SHED_WALL if edge and not door else tiles.FACTORY_FLOOR
        rows = ((-14, -13), (-7, -6), (5, 6), (12, 13))
        chassis, arms = [], []
        for q, (r0, r1) in enumerate(rows):
            east = q % 2 == 0
            belt = tiles.BELT_E if east else tiles.BELT_W
            for i in range(-28, 29):
                for j in (r0, r1):
                    cells[(fx + i, fy + j)] = belt
            for pc in (-20, -8, 4, 16):
                idx = len(self.presses)
                for di in (-1, 0, 1):
                    for j in (r0, r1):
                        cells[(fx + pc + di, fy + j)] = tiles.PRESS_BED
                        self.press_at[(fx + pc + di, fy + j)] = idx
                    cells[(fx + pc + di, fy + r0 - 1)] = tiles.PRESS_FRAME
                    cells[(fx + pc + di, fy + r1 + 1)] = tiles.PRESS_FRAME
                self.presses.append((fx + pc + 0.5, fy + r1 + 0.0,
                                     rng.uniform(0.0, config.PANOPTICON_PRESS[0])))
            for ac in (-14, -2, 10, 22):
                up = (ac + q) % 2
                cells[(fx + ac, fy + (r0 - 1 if up else r1 + 1))] = tiles.ROBOT_ARM
                arms.append((fx + ac + 0.5, fy + (r0 - 2 if up else r1 + 2) + 0.5))   # (its welder's spot)
            end = 29 if east else -31
            for di in (0, 1):
                for j in (r0, r1):
                    cells[(fx + end + di, fy + j)] = tiles.CHASSIS
            chassis.append((fx + end + 1.0, fy + r1 + 0.0))
        for ic in (-24, -12, 0, 12, 24):
            for di in (0, 1):
                for j in (-1, 0):
                    cells[(fx + ic + di, fy + j)] = tiles.CHASSIS
            chassis.append((fx + ic + 1.0, fy + 0.0))
        return self._mark("panopticon_factory", "zone", "The Factory", cells, fx + 0.5, fy + 0.5,
                          props={"chassis": chassis, "arms": arms})

    def _scrapyard(self, rng: random.Random):
        """The scrapyard: a chain fence round a yard of oily dirt, mountains
        of broken machines in it (loose scrap round their feet), wrecks
        scattered between them; gates at either end."""
        sx, sy = self.scrapyard
        cells: dict = {}
        mounds = []
        for _ in range(200):
            if len(mounds) >= 7:
                break
            mx, my = rng.uniform(-26, 26), rng.uniform(-17, 17)
            r = rng.uniform(3.5, 6.5)
            if (mx / 34) ** 2 + (my / 25) ** 2 > 0.6 or abs(my) < r + 2.5:
                continue                                    # (off the lane between the gates)
            if any(math.hypot(mx - qx, my - qy) < r + qr + 3 for qx, qy, qr in mounds):
                continue
            mounds.append((mx, my, r))
        wrecks = []
        for j in range(-27, 28):
            for i in range(-36, 37):
                e_in = (i / 34.0) ** 2 + (j / 25.0) ** 2
                e_out = (i / 35.5) ** 2 + (j / 26.5) ** 2
                if e_out >= 1.0:
                    continue
                if e_in >= 1.0:
                    cells[(sx + i, sy + j)] = tiles.YARD_DIRT if abs(j) <= 3 else tiles.CHAIN_FENCE
                    continue
                t = tiles.YARD_DIRT
                for mx, my, r in mounds:
                    d = math.hypot(i - mx, (j - my) * 1.2)
                    if d < r - 1.3:
                        t = tiles.SCRAP_HEAP
                        break
                    if d < r:
                        t = tiles.LOOSE_SCRAP
                cells[(sx + i, sy + j)] = t
        for _ in range(60):
            if len(wrecks) >= 16:
                break
            i, j = rng.randint(-30, 29), rng.randint(-21, 20)
            spots = [(sx + i, sy + j), (sx + i + 1, sy + j)]
            if all(cells.get(p) is tiles.YARD_DIRT for p in spots) and abs(j) > 4 \
                    and (i / 34.0) ** 2 + (j / 25.0) ** 2 < 0.85:
                for p in spots:
                    cells[p] = tiles.WRECK
                wrecks.append((sx + i + 1.0, sy + j + 0.5))
        return self._mark("panopticon_scrapyard", "zone", "The Scrapyard", cells, sx + 0.5, sy + 0.5,
                          props={"wrecks": wrecks, "mounds": [(sx + mx, sy + my, r) for mx, my, r in mounds]})

    def _homes(self, rng: random.Random):
        """The kept homes: a clean street with five homes either side, front
        lawns behind trimmed hedges, each home spotless -- its table set for
        dinner, its bed made -- for people who never came back."""
        hx, hy = self.homes
        cells: dict = {}
        for j in range(-15, 16):
            for i in range(-27, 28):
                cells[(hx + i, hy + j)] = tiles.LAWN
        for j in range(-3, 3):
            for i in range(-27, 28):
                cells[(hx + i, hy + j)] = tiles.PAVEMENT
        homes, rooms, lawns = [], [], []
        for s in (-1, 1):
            for q in range(5):
                i0 = -26 + q * 11                               # (9 wide, a hedge between)
                j_front = -4 if s < 0 else 3                     # (the hedge in front)
                j0, j1 = (-14, -7) if s < 0 else (6, 13)
                door = (i0 + 3, i0 + 4)
                for i in range(i0, i0 + 9):
                    cells[(hx + i, hy + j_front)] = tiles.LAWN if i in door else tiles.HEDGE
                    for j in range(j0, j1 + 1):
                        edge = i in (i0, i0 + 8) or j in (j0, j1)
                        front = j == (j1 if s < 0 else j0)
                        if edge and not (front and i in door):
                            cells[(hx + i, hy + j)] = tiles.HOME_WALL
                        else:
                            cells[(hx + i, hy + j)] = tiles.HOME_FLOOR
                mid = (j0 + j1) // 2
                for i in (i0 + 3, i0 + 4):
                    cells[(hx + i, hy + mid)] = tiles.SET_TABLE
                back = j0 + 1 if s < 0 else j1 - 1
                for i in (i0 + 6, i0 + 7):
                    cells[(hx + i, hy + back)] = tiles.MADE_BED
                for j in range(j0, j1 + 1):                      # (a hedge between homes)
                    if q < 4:
                        cells[(hx + i0 + 10, hy + j)] = tiles.HEDGE
                homes.append((hx + i0 + 4.5, hy + mid + 0.5))
                rooms.append((hx + i0 + 1.5, hy + mid + 0.5))        # (M32.3: its housekeeper)
                lawns.append((hx + i0 + 6.5, hy + j_front + s + 0.5))   # (its gardener's lawn)
        return self._mark("panopticon_homes", "zone", "The Kept Homes", cells, hx + 0.5, hy + 0.5,
                          props={"homes": homes, "rooms": rooms, "lawns": lawns})

    # --- Per chunk ------------------------------------------------------------------------

    def paint(self, x0: int, y0: int, xs, ys, ids, biome_ids, r1, T) -> None:
        """Lay one chunk's street grid and blocks district by district, the
        avenues, the factory district's belts, the open ground, the tower's
        plaza, the district walls, the power, fences, presses and masts, the
        quay and the oily sea into its tile indices (`T`: tile -> index)."""
        z = self.zone
        X, Y = np.broadcast_arrays(xs, ys)
        land = biome_ids == z.biome_id
        n = X.shape
        if land.any():
            dx = (np.floor(X) - self.cx).astype(np.int64)
            dy = (np.floor(Y) - self.cy).astype(np.int64)
            k = self._k(dx + 0.0, dy + 0.0)
            u, v = self._uv(k, dx, dy)
            P = np.take(np.array(self.pitch), k)
            half = np.take(np.array([g[1] // 2 for g in self.grid]), k)
            u0 = np.take(np.array(self.u0), k)
            mu = (u - u0 + P // 2) % P - P // 2
            mv = (v + P // 2) % P - P // 2
            amu, amv = np.abs(mu), np.abs(mv)
            street = (amu <= half) | (amv <= half)
            facade = ~street & ((amu == half + 1) | (amv == half + 1))
            bu = np.floor_divide(u - u0, P)
            bv = np.floor_divide(v, P)
            lot = _mix((bu * 0x9E3779B1 + bv * 0x85EBCA77 + k * 0xC2B2AE3D + self.seed * 31)
                       & 0xFFFFFFFF) < config.PANOPTICON_LOTS
            walls_t = np.array([T(_STYLE[nm][0]) for nm in self.names])
            roofs_t = np.array([T(_STYLE[nm][1]) for nm in self.names])
            scrap = k == self.k_of[SCRAPYARD]
            dice = np.random.default_rng(hash_coords(self.seed, 0xC7, x0, y0)).random(n)
            out = np.where(facade, np.take(walls_t, k), np.take(roofs_t, k))
            out = np.where(facade & ~scrap & (dice < config.PANOPTICON_SIGNS), T(tiles.NEON_SIGN), out)
            out = np.where(~street & lot, np.where(scrap, np.where(dice < 0.03, T(tiles.WRECK),
                                                                     T(tiles.YARD_DIRT)), T(tiles.LOT)), out)
            line = ((mv == 0) & (amu > half) & (u % 4 < 2)) | ((mu == 0) & (amv > half) & (v % 4 < 2))
            pave = ((amv == half) & (amu > half)) | ((amu == half) & (amv > half))
            ground = np.where(line, T(tiles.LANE_LINE), np.where(pave, T(tiles.PAVEMENT), T(tiles.STREET)))
            out = np.where(street, ground, out)
            # The avenue down each district's middle.
            av = config.PANOPTICON_AVENUE
            avenue = np.abs(v) <= av
            ave = np.where((v == 0) & (u % 4 < 2), T(tiles.LANE_LINE),
                           np.where(np.abs(v) == av, T(tiles.PAVEMENT), T(tiles.STREET)))
            out = np.where(avenue, ave, out)
            # The factory district's belts down every other cross street.
            fk = self.k_of[FACTORY]
            ci = np.floor_divide(u - u0 + P // 2, P)
            belt = (k == fk) & (amu <= 1) & (ci % 2 == 1) & (np.abs(v) > av + 1)
            if belt.any():
                ax, ay = self.axes[fk]
                d0 = T(_DIR_BELT[(-ay, ax)])
                d1 = T(_DIR_BELT[(ay, -ax)])
                out = np.where(belt, np.where((ci // 2) % 2 == 0, d0, d1), out)
            # Open ground: round the gates, the landmarks, the masts.
            for rx, ry, hw, hh, tile in self.reserved:
                if rx + hw < x0 or rx - hw > x0 + n[1] or ry + hh < y0 or ry - hh > y0 + n[0]:
                    continue
                box = (np.abs(X - rx) <= hw) & (np.abs(Y - ry) <= hh)
                out = np.where(box, T(tile), out)
            # The tower's plaza.
            Xc, Yc = X - self.cx - 0.5, Y - self.cy - 0.5
            out = np.where(self.in_plaza(X, Y), T(tiles.PLAZA), out)
            # The district walls, gates open in them.
            gate_half = config.PANOPTICON_GATE_W / 2
            for wx, wy, r0, r1_, gates in self.walls:
                along = Xc * wx + Yc * wy
                wall = (np.abs(-Xc * wy + Yc * wx) < 1.05) & (along > r0) & (along < r1_)
                if not wall.any():
                    continue
                for g in gates:
                    wall &= np.abs(along - g) >= gate_half
                out = np.where(wall, T(tiles.CITY_WALL), out)
            # Power, fences, presses, masts.
            for tx, ty, tile in self._points.get((x0 // config.CHUNK_SIZE, y0 // config.CHUNK_SIZE), ()):
                out[ty - y0, tx - x0] = T(tile)
            ids[land] = out[land]
        # The steel quay, and the oily black water off it.
        sea = biome_ids == biomes.OCEAN.id
        if sea.any() or land.any():
            d = np.hypot(X - z.cx, Y - z.cy)
            near = d > z.radius * (1.0 - config.ZONE_COAST_AMPLITUDE) - config.PANOPTICON_QUAY - 3
            near &= d < z.max_radius + config.PANOPTICON_OIL
            if near.any():
                off = np.full(d.shape, -np.inf)
                off[near] = d[near] - z.coast(X[near], Y[near])
                band = config.PANOPTICON_OIL
                thick = np.clip(2.0 * (1.0 - off / band), 0.0, 1.0)
                ids[sea & (off > 0) & (r1 < thick)] = T(tiles.OILY_SEA)
                ids[land & (off > -config.PANOPTICON_QUAY)] = T(tiles.QUAY)
