"""
world/pangaea.py -- Pangaea's land (M31.1, design/OCEAN.md 24).

The west zone's island (world/zones.py places it): deep time, jungle and
fire. RINGS OF AGES: walking inland goes back in time. A tile's depth is its
distance from the centre over the coast's there (`depth`), and the rings
are cut at PANGAEA_RINGS:

  * the shore ring, the youngest age: the great mammals' fern meadows, tall
    ferns, clumps of jungle trees, lone cycads and rocks; the painted caves
    (the early hunters' home); the sea-beast skeleton on the beach facing
    the main island, where you arrive (Paradise's Gate, Pandemonium's
    pier); the black-sand beach all round;
  * the middle ring, the dinosaurs' jungle: giant ferns, jungle trees,
    cycads; the great nest on its crag, the impact crater round the black
    stone, nests of eggs, giant bones (cover), tar pits (some with a beast
    half-sunk in them);
  * the heart, the oldest age: ash, horsetail groves and scale trees round
    steaming pools, amber outcrops (in the middle ring too), the volcano's
    cone of cinders, and inside its rim the caldera -- the Ancestor's arena
    (M31.4-5), sealed by a curtain of fire facing the main island.

Lava rivers run down from vents on the cone: the first all the way to the
sea (the sea steams at its mouth), the others into fields of cooled basalt
in the middle ring. Game trails (beaten earth) run from the skeleton to the
curtain, round the middle ring, and out to the landmarks, with crossings of
cooled rock where they meet the lava.

Worked out once per seed (zones.plan_of, cached on the zone). The big
things are ordinary world/landmarks.Landmark stamps (they stream, persist
and map like any other); the ground, lava, tar, pools, basalt, trails,
beach and steam are painted per chunk by `paint` (from
world/generator.build_chunk).
"""

from __future__ import annotations

import math
import random

import numpy as np

from .. import config
from . import biomes, tiles
from .noise import fbm
from .paradise import _ellipse_point, _line_dist, _meander, _nearest_on, _point_dist, _segments
from .rng import hash_coords

_TAU = 2.0 * math.pi
HEART, MIDDLE, SHORE = 0, 1, 2           # the rings of ages, oldest first


class Plan:
    """Where everything on Pangaea is, for one seed. `marks` are its
    landmarks; the rest is painted per chunk."""

    RIM = config.PANGAEA_RIM              # the caldera's rim, tiles thick

    def __init__(self, layout, zone) -> None:
        from .landmarks import Landmark   # (landmarks imports the zones' plans)
        self._Landmark = Landmark
        self.zone = zone
        self.seed = layout.seed
        rng = random.Random(hash_coords(layout.seed, 0x9A6E, zone.salt))
        cx, cy = float(zone.cx), float(zone.cy)
        a, b = config.PANGAEA_CALDERA_RADII
        w = self.RIM
        self.caldera = (cx, cy, float(a), float(b))
        gx, gy = zone.facing
        self.facing = (gx, gy)
        self.cone = w + config.PANGAEA_CONE                # the cone's foot, past the oval
        shore = zone.shore_along(gx, gy)
        # The skeleton's tail, on the beach a few tiles in from the shore.
        self.gate = (round(cx + gx * (shore - 4)), round(cy + gy * (shore - 4)))
        self.curtain = _ellipse_point(cx, cy, a, b, gx, gy, w / 2)

        # The lava rivers (before everything else is placed round them): the
        # first runs off to one side of the trail all the way to the sea, the
        # second behind the volcano, the third to the other side.
        face = math.atan2(gy, gx)
        side = rng.choice((-1.0, 1.0))
        angles = [face + side * rng.uniform(1.2, 1.65), face + math.pi + rng.uniform(-0.35, 0.35),
                  face - side * rng.uniform(1.9, 2.4)][:config.PANGAEA_LAVA_RIVERS]
        self.rivers: list[list[tuple[float, float]]] = []
        self.fields: list[tuple[float, float, float]] = []    # cooled basalt where a river ends
        self.mouth: tuple[float, float] | None = None
        for k, ang in enumerate(angles):
            ux, uy = math.cos(ang), math.sin(ang)
            start = _ellipse_point(cx, cy, a, b, ux, uy, w + 2)
            if k == 0:
                far = zone.shore_along(ux, uy)
                end = (cx + ux * (far + 8), cy + uy * (far + 8))
                self.mouth = (cx + ux * far, cy + uy * far)
            else:
                ex, ey = self._at_depth(np.array([ux]), np.array([uy]), rng.uniform(0.6, 0.66))
                end = (float(ex[0]), float(ey[0]))
                self.fields.append((*end, rng.uniform(*config.PANGAEA_BASALT_FIELD)))
            self.rivers.append(_meander(start, end, config.PANGAEA_LAVA_SWAY, rng, 9))
        self._lava_segs = _segments(self.rivers)

        # The trails: the skeleton to the curtain, a ring round the middle.
        start = _ellipse_point(cx, cy, a, b, gx, gy, w + 1)
        end = (self.gate[0] - gx * 40, self.gate[1] - gy * 40)
        main = _meander(start, end, config.PANGAEA_TRAIL_SWAY, rng, 7)
        ks = np.arange(72) * _TAU / 72
        rx, ry = self._at_depth(np.cos(ks), np.sin(ks), config.PANGAEA_RING_TRAIL)
        ring = list(zip(rx.tolist(), ry.tolist()))
        ring.append(ring[0])
        self.trails: list[list[tuple[float, float]]] = [main, ring]

        # The landmarks' spots, the biggest first.
        # (the skeleton: 40 tiles inland from its tail, 12 either side)
        along, across = 24.0, 12.0
        self._placed: list[tuple[float, float, float, float]] = [
            (self.gate[0] - gx * 18, self.gate[1] - gy * 18,
             along * abs(gx) + across * abs(gy), along * abs(gy) + across * abs(gx))]
        avoid = _segments([main, ring]) + self._lava_segs
        self.caves = self._site(rng, 16, 13, (SHORE,), avoid)
        self.great_nest = self._site(rng, 15, 15, (MIDDLE,), avoid)
        self.crater = self._site(rng, 21, 21, (MIDDLE,), avoid)
        self.nests = [s for s in (self._site(rng, 5, 5, (MIDDLE,), avoid)
                                  for _ in range(config.PANGAEA_NESTS)) if s]
        self.bones = [s for s in (self._site(rng, 8, 7, (SHORE, MIDDLE), avoid)
                                  for _ in range(config.PANGAEA_BONES)) if s]
        self.tar_pits = [(*s, rng.uniform(4.0, 7.5)) for s in (
            self._site(rng, 8, 8, (SHORE, MIDDLE), avoid) for _ in range(config.PANGAEA_TAR_PITS)) if s]
        self.pools = [(*s, rng.uniform(2.6, 4.8)) for s in (
            self._site(rng, 6, 6, (HEART,), avoid) for _ in range(config.PANGAEA_POOLS)) if s]
        self.quest = next((k for k, q in config.QUESTS.items() if q.biome == zone.key), "")

        # Spurs from the nearer trail to the caves' mouth, the great nest's
        # ramp and the crater's rim.
        self._mouth_dir = {}
        ends = []
        for name, at, reach in (("caves", self.caves, 15.0), ("great_nest", self.great_nest, 15.5),
                                ("crater", self.crater, 20.0)):
            if at is None:
                continue
            near = min((_nearest_on(at[0], at[1], line) for line in (main, ring)),
                       key=lambda q: math.hypot(at[0] - q[0], at[1] - q[1]))
            d = math.hypot(near[0] - at[0], near[1] - at[1]) or 1.0
            ux, uy = (near[0] - at[0]) / d, (near[1] - at[1]) / d
            self._mouth_dir[name] = (ux, uy)               # (the cave's mouth, the ramp: toward it)
            ends.append(((at[0] + ux * reach, at[1] + uy * reach), near))
        for (ex, ey), near in ends:
            if math.hypot(ex - near[0], ey - near[1]) > 4:
                self.trails.append(_meander(near, (ex, ey), 6.0, rng, 3))
        self._trail_segs = _segments(self.trails)
        self.marks = self._build_marks(rng)

    # --- The rings ------------------------------------------------------------------------

    def depth(self, xs, ys) -> np.ndarray:
        """How far in from the shore (0: the centre, 1: the coast), wobbled
        so the rings' edges wander."""
        z = self.zone
        xs, ys = np.broadcast_arrays(np.asarray(xs, dtype=np.float64), np.asarray(ys, dtype=np.float64))
        d = np.hypot(xs - z.cx, ys - z.cy) / z.coast(xs, ys)
        wob = fbm(self.seed, z.salt + 3, xs, ys, config.PANGAEA_RING_SCALE, 3) - 0.5
        return d + wob * 2.0 * config.PANGAEA_RING_WOBBLE

    def ring_at(self, x: float, y: float) -> int:
        """Which ring of ages (x, y) is in: HEART, MIDDLE or SHORE."""
        u = float(self.depth(np.array([x]), np.array([y]))[0])
        return int(np.digitize(u, config.PANGAEA_RINGS))

    def in_caldera(self, x: float, y: float, grow: float = 0.0) -> bool:
        return self._ellipse(x, y, grow) < 1.0

    def _at_depth(self, ux: np.ndarray, uy: np.ndarray, u: float) -> tuple[np.ndarray, np.ndarray]:
        """The points in directions (ux, uy) from the centre at depth u
        (unwobbled; the coast field's value there settles in a few steps)."""
        z = self.zone
        r = np.full(ux.shape, u * z.radius)
        for _ in range(4):
            r = u * z.coast(z.cx + ux * r, z.cy + uy * r)
        return z.cx + ux * r, z.cy + uy * r

    # --- Placement ---------------------------------------------------------------------

    def _ellipse(self, x: float, y: float, grow: float) -> float:
        """Where (x, y) sits against the caldera's oval grown by `grow` (< 1:
        inside)."""
        cx, cy, a, b = self.caldera
        return ((x - cx) / (a + grow)) ** 2 + ((y - cy) / (b + grow)) ** 2

    def _site(self, rng: random.Random, hw: float, hh: float, rings, avoid, tries: int = 768,
              apart=None) -> tuple[int, int] | None:
        """A random centre for a (2hw x 2hh) footprint: on the island with 4
        tiles to spare, in one of `rings`, off the volcano's cone, clear of
        the trails and the lava, and PANGAEA_SITE_GAP from every spot taken.
        (Candidates are drawn 32 at a time and the noise-heavy tests -- the
        coast, the ring -- run on all of them at once.)"""
        z = self.zone
        cx, cy = self.caldera[0], self.caldera[1]
        gap = config.PANGAEA_SITE_GAP
        reach = math.hypot(hw, hh) + 5
        grid_x = np.linspace(-hw - 4, hw + 4, 5)
        grid_y = np.linspace(-hh - 4, hh + 4, 5)
        for _ in range(tries // 32):
            pts = []
            for _ in range(32):
                r = math.sqrt(rng.random()) * z.radius
                ang = rng.uniform(0.0, _TAU)
                pts.append((round(cx + math.cos(ang) * r), round(cy + math.sin(ang) * r)))
            pts = [(x, y) for x, y in pts if self._ellipse(x, y, self.cone + max(hw, hh) + 4) >= 1.0
                   and not any(abs(x - px) < hw + phw + gap and abs(y - py) < hh + phh + gap
                               for px, py, phw, phh in self._placed)]
            if not pts:
                continue
            px_ = np.array([p[0] for p in pts], dtype=np.float64)
            py_ = np.array([p[1] for p in pts], dtype=np.float64)
            on = z.inside(px_[:, None, None] + grid_x[None, None, :],
                          py_[:, None, None] + grid_y[None, :, None]).all(axis=(1, 2))
            ring = np.digitize(self.depth(px_, py_), config.PANGAEA_RINGS)
            for (x, y), good, rg in zip(pts, on.tolist(), ring.tolist()):
                if not good or rg not in rings:
                    continue
                if _point_dist(x, y, avoid) < reach:
                    continue
                if apart is not None and any(math.hypot(x - qx, y - qy) < apart[1]
                                             for qx, qy in apart[0]):
                    continue
                self._placed.append((x, y, hw, hh))
                return x, y
        return None

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
        return self._Landmark(key, kind, "pangaea", name, x0, y0, rows, cx=cx, cy=cy, **kw)

    def _build_marks(self, rng: random.Random) -> list:
        out = [self._caldera(rng), self._skeleton(rng)]
        if self.caves is not None:
            out.append(self._caves(rng))
        if self.great_nest is not None:
            out.append(self._great_nest(rng))
        if self.crater is not None:
            out.append(self._crater(rng))
        out += [self._nest(x, y, rng) for x, y in self.nests]
        out += [self._bones(x, y, rng) for x, y in self.bones]
        # (a beast half-sunk in some of the tar pits)
        out += [self._bones(round(x), round(y), rng, sunk=True) for x, y, r in self.tar_pits
                if rng.random() < config.PANGAEA_TAR_BONES]
        return [m for m in out if m is not None]

    def _caldera(self, rng: random.Random):
        """The caldera: the Ancestor's arena (M31.4-5), inside the volcano's
        rim; lava lakes on its floor of cooling black rock; the curtain of
        fire across its gate (sealed until the seventh great beast falls)."""
        cx, cy, a, b = self.caldera
        w = self.RIM
        gx, gy = self.facing
        x0, x1 = math.floor(cx - a - w - 1), math.ceil(cx + a + w + 1)
        y0, y1 = math.floor(cy - b - w - 1), math.ceil(cy + b + w + 1)
        X = np.arange(x0, x1 + 1)[None, :] + 0.5
        Y = np.arange(y0, y1 + 1)[:, None] + 0.5
        e_in = ((X - cx) / a) ** 2 + ((Y - cy) / b) ** 2
        e_out = ((X - cx) / (a + w)) ** 2 + ((Y - cy) / (b + w)) ** 2
        inside = e_in < 1.0
        wall = (~inside) & (e_out < 1.0)
        across = np.abs((X - cx) * -gy + (Y - cy) * gx)
        along = (X - cx) * gx + (Y - cy) * gy
        gate = wall & (across <= config.PANGAEA_CALDERA_GATE / 2) & (along > 0)
        # Lava lakes, clear of the middle (where it sleeps) and of the curtain.
        n, (r0, r1) = config.PANGAEA_CALDERA_LAKES
        lakes: list[tuple[float, float, float]] = []
        for _ in range(200):
            if len(lakes) >= n:
                break
            ang, f = rng.uniform(0, _TAU), rng.uniform(0.35, 0.72)
            lx, ly = cx + math.cos(ang) * a * f, cy + math.sin(ang) * b * f
            rr = rng.uniform(r0, r1)
            if math.hypot(lx - cx, ly - cy) < 16 + rr:
                continue
            if math.hypot(lx - self.curtain[0], ly - self.curtain[1]) < 20 + rr:
                continue
            if any(math.hypot(lx - qx, ly - qy) < rr + qr + 8 for qx, qy, qr in lakes):
                continue
            lakes.append((lx, ly, rr))
        lava = np.zeros(inside.shape, dtype=bool)
        crust = np.zeros(inside.shape, dtype=bool)
        for lx, ly, rr in lakes:
            d = np.hypot(X - lx, (Y - ly) * 1.15)
            lava |= inside & (d < rr)
            crust |= inside & (d < rr + 1.3)
        js, is_ = np.nonzero(inside | wall)
        cells: dict = {}
        gate_tiles = []
        for j, i in zip(js.tolist(), is_.tolist()):
            p = (x0 + i, y0 + j)
            if gate[j, i]:
                cells[p] = tiles.FIRE_CURTAIN
                gate_tiles.append(p)
            elif wall[j, i]:
                cells[p] = tiles.CALDERA_RIM
            elif lava[j, i]:
                cells[p] = tiles.LAVA
            elif crust[j, i]:
                cells[p] = tiles.LAVA_CRUST
            else:
                cells[p] = tiles.CALDERA_FLOOR
        # (kind "court" until M31.4 makes it the quest's lair, as with
        # Paradise's court and Pandemonium's hall)
        return self._mark("pangaea_caldera", "court", "The Caldera", cells, cx, cy,
                          gate=gate_tiles, radii=(a, b), floor=tiles.CALDERA_FLOOR,
                          props={"seal": tiles.FIRE_CURTAIN, "barred": True, "facing": (gx, gy),
                                 "lakes": lakes})

    def _skeleton(self, rng: random.Random):
        """The sea-beast skeleton beached on the shore facing the main
        island. Local frame: i along the shore, j out to sea (0: on land, a
        few tiles in; the shore about 4 out). Its tail trails into the surf,
        its spine runs inland overhead (you walk under it, between its ribs),
        its skull lies at the inland end, off to one side."""
        gcx, gcy = self.gate
        vx, vy = self.facing                   # out to sea
        ux, uy = -vy, vx                       # along the shore
        cells: dict = {}

        def at(i: int, j: int, t) -> None:
            cells[(round(gcx + ux * i + vx * j), round(gcy + uy * i + vy * j))] = t

        for j in range(-34, 7):                             # the spine, overhead
            at(0, j, tiles.SPINE)
        for j in (2, 5):                                    # the tail's vertebrae in the surf
            at(-1, j, tiles.GIANT_BONE)
            at(1, j, tiles.GIANT_BONE)
        ribs = list(range(-5, -30, -3))
        for k, j in enumerate(ribs):                        # the ribs, longest in the middle
            length = 2 + round(2.5 * math.sin(math.pi * (k + 0.5) / len(ribs)))
            for s in (-1, 1):
                for q in range(length + 1):
                    at(s * (4 + q), j - q // 2, tiles.GIANT_BONE)
        side = rng.choice((-1, 1))                          # the skull, inland, to one side
        for j in range(-40, -30):
            for i in range(2, 12):
                if ((i - 6.5) / 5.0) ** 2 + ((j + 35.5) / 4.0) ** 2 < 1.0:
                    at(side * i, j, tiles.GIANT_BONE)
        for i in (5, 8):                                    # its empty eyes
            cells.pop((round(gcx + ux * side * i + vx * -36), round(gcy + uy * side * i + vy * -36)), None)
        for i in range(3, 11, 2):                           # its teeth, toward the ribs
            at(side * i, -30, tiles.GIANT_BONE)
        return self._mark("pangaea_skeleton", "zone", "The Sea-Beast's Bones", cells,
                          gcx + 0.5, gcy + 0.5, land_only=True)

    def _caves(self, rng: random.Random):
        """The painted caves: a hill of rock, a chamber inside it walled with
        paintings of the island's hunts round the hunters' fire, its mouth
        toward the trail (M31.4: the old painter's, the great hunt painted on
        its deepest wall)."""
        hx, hy = self.caves
        mx, my = self._mouth_dir.get("caves", (1.0, 0.0))
        salt = self.zone.salt + 11
        cells: dict = {}
        deep: list[tuple[int, int]] = []
        wobs = fbm(self.seed, salt, np.arange(hx - 16, hx + 17)[None, :] + 0.5,
                   np.arange(hy - 13, hy + 14)[:, None] + 0.5, 6, 2)
        for j in range(-13, 14):
            for i in range(-16, 17):
                x, y = hx + i, hy + j
                wob = float(wobs[j + 13, i + 16])
                hill = (i / 15.0) ** 2 + (j / 12.0) ** 2 < 0.72 + 0.5 * wob
                room = (i / 8.5) ** 2 + (j / 5.5) ** 2 < 1.0
                rim = (i / 10.0) ** 2 + (j / 7.0) ** 2 < 1.0
                along = i * mx + j * my
                across = abs(-i * my + j * mx)
                mouth = along > 0 and across <= 1.5
                if room or (mouth and hill):
                    cells[(x, y)] = tiles.CAVE_FLOOR
                elif rim:
                    cells[(x, y)] = tiles.PAINTED_WALL
                    if along < -4:
                        deep.append((x, y))                 # (the deepest wall, away from the mouth)
                elif hill:
                    cells[(x, y)] = tiles.CAVE_ROCK
        cells[(hx, hy)] = tiles.FIRE_PIT
        cells[(hx + 1, hy)] = tiles.FIRE_PIT
        npc = (hx - mx * 3 + 0.5, hy - my * 3 + 0.5)
        return self._mark("pangaea_caves", "zone", "The Painted Caves", cells, hx + 0.5, hy + 0.5,
                          npc=npc, props={"fire": (hx + 1.0, hy + 0.5), "deep_wall": deep,
                                          "mouth": (mx, my)})

    def _great_nest(self, rng: random.Random):
        """The great nest: sheer crag round a flat top (a ramp up it, toward
        the trail), a giant ring of branches and bones on top, eggs the size
        of a man inside."""
        nx, ny = self.great_nest
        mx, my = self._mouth_dir.get("great_nest", (1.0, 0.0))
        cells: dict = {}
        for j in range(-15, 16):
            for i in range(-15, 16):
                r = math.hypot(i, j)
                along = i * mx + j * my
                ramp = along > 0 and abs(-i * my + j * mx) <= 1.5
                if r < 10.5 or (ramp and r < 15.0):
                    t = tiles.CRAG_TOP
                    if 5.6 <= r < 7.2 and not (ramp and along > 0):
                        t = tiles.GIANT_BONE if (round(math.atan2(j, i) * 4) % 5 == 0) else tiles.NEST
                    elif r < 5.6:
                        t = tiles.TWIGS
                    cells[(nx + i, ny + j)] = t
                elif r < 14.2 + 0.8 * math.sin(math.atan2(j, i) * 5 + nx):
                    cells[(nx + i, ny + j)] = tiles.CRAG
        for ex, ey in ((-3, -2), (1, -3), (-2, 1), (2, 1)):         # 2 x 2 each
            for dj in (0, 1):
                for di in (0, 1):
                    cells[(nx + ex + di, ny + ey + dj)] = tiles.GIANT_EGG
        return self._mark("pangaea_great_nest", "zone", "The Great Nest", cells, nx + 0.5, ny + 0.5,
                          props={"eggs": [(nx + ex + 1.0, ny + ey + 1.0) for ex, ey in
                                          ((-3, -2), (1, -3), (-2, 1), (2, 1))]})

    def _crater(self, rng: random.Random):
        """The impact crater: thrown-up rock round a floor melted to glass,
        the strange black stone in the middle."""
        kx, ky = self.crater
        cells: dict = {}
        for j in range(-20, 21):
            for i in range(-20, 21):
                r = math.hypot(i, j * 1.1)
                wob = 0.9 * math.sin(math.atan2(j, i) * 7 + kx * 0.3)
                if r < 2.3:
                    cells[(kx + i, ky + j)] = tiles.STAR_STONE
                elif r < 15.0 + wob:
                    cells[(kx + i, ky + j)] = tiles.IMPACT_GLASS
                elif r < 19.0 + wob:
                    cells[(kx + i, ky + j)] = (tiles.BASALT_BOULDER if rng.random() < 0.05
                                               else tiles.CRATER_RIM)
        return self._mark("pangaea_crater", "zone", "The Impact Crater", cells, kx + 0.5, ky + 0.5)

    def _nest(self, x: int, y: int, rng: random.Random):
        """A nest: a ring of branches round a few eggs (break them and the
        parent comes, M31.3)."""
        cells: dict = {}
        for j in range(-4, 5):
            for i in range(-4, 5):
                r = math.hypot(i, j)
                if r < 2.6:
                    cells[(x + i, y + j)] = tiles.TWIGS
                elif r < 3.7:
                    cells[(x + i, y + j)] = tiles.NEST
        spots = [(-1, -1), (1, -1), (0, 1), (-1, 1), (1, 0)]
        rng.shuffle(spots)
        eggs = spots[:rng.randint(3, 5)]
        for i, j in eggs:
            cells[(x + i, y + j)] = tiles.EGG
        return self._mark("pangaea_nest", "zone", "Nest", cells, x + 0.5, y + 0.5,
                          props={"eggs": [(x + i + 0.5, y + j + 0.5) for i, j in eggs]})

    def _bones(self, x: int, y: int, rng: random.Random, sunk: bool = False):
        """A giant beast's bones (cover): a ribcage, a horned skull or a pair
        of tusks, lying any way round. Sunk: half of it, sticking out of a
        tar pit."""
        kind = rng.choice(("ribcage", "skull", "tusks"))
        pts: list[tuple[int, int]] = []
        if kind == "ribcage":
            for k, i in enumerate(range(-6, 7, 3)):
                length = 2 + (1 if abs(i) < 4 else 0)
                for s in (-1, 1):
                    for q in range(length + 1):
                        pts.append((i - q // 2, s * (2 + q)))
        elif kind == "skull":
            for j in range(-3, 4):
                for i in range(-4, 5):
                    if (i / 4.5) ** 2 + (j / 3.2) ** 2 < 1.0 and (i, j) not in ((-2, -1), (1, -1)):
                        pts.append((i, j))
            for q in range(1, 5):                           # horns
                pts.append((-4 - q // 2, -3 - q))
                pts.append((4 + q // 2, -3 - q))
        else:
            for s in (-1, 1):                               # two tusks, curving in
                for q in range(9):
                    pts.append((q - 4, s * (3 - round(2.2 * math.sin(math.pi * q / 8)))))
        swap = rng.random() < 0.5
        flip = rng.choice((-1, 1))
        cells: dict = {}
        for i, j in pts:
            if sunk and rng.random() < 0.5:
                continue
            i, j = (j, i * flip) if swap else (i * flip, j)
            cells[(x + i, y + j)] = tiles.GIANT_BONE
        return self._mark("pangaea_bones", "zone", "Giant Bones", cells, x + 0.5, y + 0.5)

    # --- Per chunk ------------------------------------------------------------------------

    def paint(self, x0: int, y0: int, xs, ys, ids, biome_ids, r1, T) -> None:
        """Lay one chunk's ground ring by ring, the volcano's cone, amber,
        tar pits, steaming pools, the lava and its basalt fields, the trails
        and their crossings, the black-sand beach and the steaming sea into
        its tile indices (`T`: tile -> index)."""
        z = self.zone
        X, Y = np.broadcast_arrays(xs, ys)
        land = biome_ids == z.biome_id
        n = X.shape
        if land.any():
            dice = np.random.default_rng(hash_coords(self.seed, 0xC5, x0, y0)).random(n)
            ring = np.digitize(self.depth(X, Y), config.PANGAEA_RINGS)
            det = fbm(self.seed, z.salt + 5, X, Y, config.PANGAEA_DETAIL_SCALE, 3)
            s = config.PANGAEA_SHORE
            shore = np.select(
                [det > s[1], det > s[0], dice < s[3], dice > 1.0 - s[4]],
                [np.where(r1 < s[2], T(tiles.JUNGLE_TREE), T(tiles.TALL_FERNS)), T(tiles.TALL_FERNS),
                 T(tiles.CYCAD), T(tiles.ROCK)], T(tiles.FERN_MEADOW))
            m = config.PANGAEA_MIDDLE
            middle = np.select(
                [(det > m[3]) & (r1 < m[4]), (det > m[1]) & (r1 < m[2]), det > m[0], dice < m[5]],
                [T(tiles.JUNGLE_TREE), T(tiles.GIANT_FERN), T(tiles.TALL_JUNGLE_FERNS), T(tiles.CYCAD)],
                T(tiles.JUNGLE_FLOOR))
            h = config.PANGAEA_HEART
            heart = np.select([(det > h[1]) & (r1 < h[2]), det > h[0]],
                              [T(tiles.SCALE_TREE), T(tiles.HORSETAILS)], T(tiles.ASH))
            out = np.where(ring == SHORE, shore, np.where(ring == MIDDLE, middle, heart))
            # Amber outcrops in the heart and the middle ring.
            am_min, am_share, am_scale = config.PANGAEA_AMBER
            amber = (ring < SHORE) & (fbm(self.seed, z.salt + 7, X, Y, am_scale, 2) > am_min) \
                & (dice < am_share)
            out = np.where(amber, T(tiles.AMBER), out)
            # The volcano's cone: cinders and boulders round the rim.
            cx, cy, a, b = self.caldera
            cone = ((X - cx) / (a + self.cone)) ** 2 + ((Y - cy) / (b + self.cone)) ** 2 < 1.0
            out = np.where(cone, np.where(dice < h[3], T(tiles.BASALT_BOULDER), T(tiles.CINDERS)), out)
            # Tar pits and steaming pools (blobs round their sites, edges wobbling).
            for (px, py, pr), tile in ([(q, tiles.TAR) for q in self.tar_pits]
                                       + [(q, tiles.HOT_SPRING) for q in self.pools]):
                if px + pr + 3 < x0 or px - pr - 3 > x0 + n[1] or py + pr + 3 < y0 or py - pr - 3 > y0 + n[0]:
                    continue
                blob = np.hypot(X - px, (Y - py) * 1.2) < pr * (0.85 + 0.3 * det)
                out = np.where(blob, T(tile), out)
            # The lava: molten down the middle, a burning crust either side;
            # vents where each river starts; basalt where the others end.
            d_lava = _line_dist(X, Y, self._lava_segs, 8)
            core, edge = config.PANGAEA_LAVA_W
            for line in self.rivers:
                d_lava = np.minimum(d_lava, np.hypot(X - line[0][0], Y - line[0][1]) - 1.6)
            molten = d_lava < core
            crust = (d_lava < edge) & ~molten
            out = np.where(crust, T(tiles.LAVA_CRUST), np.where(molten, T(tiles.LAVA), out))
            for fx, fy, fr in self.fields:                # (the river's end cooled into it)
                if abs(fx - x0 - n[1] / 2) < fr + n[1] and abs(fy - y0 - n[0] / 2) < fr + n[0]:
                    field = np.hypot(X - fx, Y - fy) < fr * (0.8 + 0.4 * det)
                    out = np.where(field, np.where(dice < 0.04, T(tiles.BASALT_BOULDER), T(tiles.BASALT)), out)
                    molten &= ~field
                    crust &= ~field
            # The trails: beaten earth through it all, cooled rock over the lava.
            trail = _line_dist(X, Y, self._trail_segs, 8) < config.PANGAEA_TRAIL_W
            wet = np.isin(out, (T(tiles.TAR), T(tiles.HOT_SPRING)))
            out = np.where(trail & (molten | crust), T(tiles.LAVA_CROSSING),
                           np.where(trail & ~wet, T(tiles.GAME_TRAIL), out))
            ids[land] = out[land]
        # The black-sand beach, and the sea steaming where the lava runs in.
        sea = biome_ids == biomes.OCEAN.id
        if sea.any() or land.any():
            d = np.hypot(X - z.cx, Y - z.cy)
            near = d < z.max_radius + config.PANGAEA_STEAM
            if near.any():
                off = np.full(d.shape, np.inf)
                off[near] = d[near] - z.coast(X[near], Y[near])
                hot = (T(tiles.LAVA), T(tiles.LAVA_CRUST), T(tiles.LAVA_CROSSING))
                beach = land & (off > -config.PANGAEA_BEACH * (0.55 + 0.45 * r1)) & ~np.isin(ids, hot)
                ids[beach] = T(tiles.BLACK_SAND)
                if self.mouth is not None:
                    band = config.PANGAEA_STEAM
                    far = np.hypot(X - self.mouth[0], Y - self.mouth[1])
                    thick = np.clip(1.6 * (1.0 - far / band), 0.0, 1.0)
                    ids[sea & (off > 0) & (r1 < thick)] = T(tiles.STEAMING_SEA)
