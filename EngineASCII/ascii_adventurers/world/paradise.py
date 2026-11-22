"""
world/paradise.py -- Paradise's land (M29.1, design/OCEAN.md 3).

The north zone's island (world/zones.py places it): marble and clouds. Its
own plan, worked out once per seed (plan_of, cached on the zone):

  * the summit court at the centre: the boss's arena, an oval of
    PARADISE_COURT_RADII walled in pearl, its gate (golden bars: sealed
    until the seventh seal, M29.4) facing the main island, a throne at the
    far side, columns, gold inlay rings, and the channel where the river of
    blood starts. Terraces (rings of marble steps) round it: the island
    climbs gently to its centre;
  * the Gate on the shore facing the main island: gold pillars, one leaf
    shut, the other swung open, a broken pearl wall running off along the
    shore;
  * the main marble road from the Gate up to the court, meandering; a
    ring road round the summit past the terraces; spur roads (from
    whichever is nearer) to the cathedral, the stairway and the choir
    rings; gold posts along every road;
  * the river of blood from the court's side down to the sea (bridges
    where roads cross it);
  * the fallen cathedral, the stairway to nowhere (the fallen angel's
    chain post at its foot), PARADISE_CHOIRS choir rings,
    PARADISE_FONTS blood fonts and PARADISE_STATUES weeping statues,
    placed at random spots clear of the court, the main road, the river
    and each other.

The landmarks are ordinary world/landmarks.Landmark stamps (built into the
layout's landmark list, so they stream, persist and map like any other).
The roads, the river, the posts, the terraces and the cloud bank are
painted per chunk by `paint` (from world/generator.build_chunk): distances
to the road and river polylines, worked out with numpy for the whole chunk.
"""

from __future__ import annotations

import math
import random

import numpy as np

from .. import config
from . import biomes, tiles
from .rng import hash_coords

_TAU = 2.0 * math.pi


# --- Geometry helpers -------------------------------------------------------------------


def _meander(p0, p1, sway: float, rng: random.Random, n: int) -> list[tuple[float, float]]:
    """A wandering line from p0 to p1: n inner points along the straight
    line, each pushed sideways by up to `sway` tiles (smoothed with its
    neighbours, and fading to nothing at both ends)."""
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy) or 1.0
    px, py = -dy / length, dx / length
    raw = [rng.uniform(-1.0, 1.0) for _ in range(n + 2)]
    smooth = [(raw[max(0, i - 1)] + 2 * raw[i] + raw[min(n + 1, i + 1)]) / 4 for i in range(n + 2)]
    pts = [p0]
    for k in range(1, n + 1):
        t = k / (n + 1)
        off = smooth[k] * sway * math.sin(math.pi * t)
        pts.append((x0 + dx * t + px * off, y0 + dy * t + py * off))
    pts.append(p1)
    return pts


def _segments(lines) -> list[tuple[float, float, float, float]]:
    return [(*a, *b) for line in lines for a, b in zip(line, line[1:])]


def _line_dist(xs, ys, segs, pad: float) -> np.ndarray:
    """Each point's distance to the nearest segment (inf where none is
    within `pad` of the points' bounding box)."""
    xs, ys = np.broadcast_arrays(np.asarray(xs, dtype=np.float64),
                                 np.asarray(ys, dtype=np.float64))
    best = np.full(xs.shape, np.inf)
    lo_x, hi_x, lo_y, hi_y = xs.min() - pad, xs.max() + pad, ys.min() - pad, ys.max() + pad
    for ax, ay, bx, by in segs:
        if max(ax, bx) < lo_x or min(ax, bx) > hi_x or max(ay, by) < lo_y or min(ay, by) > hi_y:
            continue
        dx, dy = bx - ax, by - ay
        ll = dx * dx + dy * dy or 1e-9
        t = np.clip(((xs - ax) * dx + (ys - ay) * dy) / ll, 0.0, 1.0)
        best = np.minimum(best, np.hypot(xs - (ax + t * dx), ys - (ay + t * dy)))
    return best


def _point_dist(x: float, y: float, segs) -> float:
    """_line_dist for one point, every segment in one numpy call (the
    same sums, so the same distance)."""
    if not segs:
        return math.inf
    ax, ay, bx, by = np.asarray(segs, dtype=np.float64).T
    dx, dy = bx - ax, by - ay
    ll = dx * dx + dy * dy
    ll[ll == 0] = 1e-9
    x, y = np.float64(x), np.float64(y)
    t = np.clip(((x - ax) * dx + (y - ay) * dy) / ll, 0.0, 1.0)
    return float(np.hypot(x - (ax + t * dx), y - (ay + t * dy)).min())


def _nearest_on(x: float, y: float, line) -> tuple[float, float]:
    """The point on polyline `line` nearest (x, y)."""
    best, at = math.inf, line[0]
    for (ax, ay), (bx, by) in zip(line, line[1:]):
        dx, dy = bx - ax, by - ay
        ll = dx * dx + dy * dy or 1e-9
        t = min(1.0, max(0.0, ((x - ax) * dx + (y - ay) * dy) / ll))
        px, py = ax + t * dx, ay + t * dy
        d = math.hypot(x - px, y - py)
        if d < best:
            best, at = d, (px, py)
    return at


def _ellipse_point(cx, cy, a, b, ux, uy, grow: float = 0.0) -> tuple[float, float]:
    """Where the ray from the centre in direction (ux, uy) meets the oval
    of radii (a + grow, b + grow)."""
    a, b = a + grow, b + grow
    t = 1.0 / math.sqrt((ux / a) ** 2 + (uy / b) ** 2)
    return cx + ux * t, cy + uy * t


def _rotate(ux: float, uy: float, ang: float) -> tuple[float, float]:
    c, s = math.cos(ang), math.sin(ang)
    return ux * c - uy * s, ux * s + uy * c


def _axis(ux: float, uy: float) -> tuple[int, int]:
    """The compass direction nearest (ux, uy)."""
    if abs(ux) >= abs(uy):
        return (1 if ux > 0 else -1), 0
    return 0, (1 if uy > 0 else -1)


# --- The plan ------------------------------------------------------------------------------


class Plan:
    """Where everything on Paradise is, for one seed. `marks` are its
    landmarks; `roads`, `river` and `posts` are painted per chunk."""

    WALL = 3                         # the court's wall, tiles thick

    def __init__(self, layout, zone) -> None:
        from .landmarks import Landmark   # (landmarks imports this module's builders)
        self._Landmark = Landmark
        self.zone = zone
        rng = random.Random(hash_coords(layout.seed, 0x9A4A, zone.salt))
        cx, cy = float(zone.cx), float(zone.cy)
        a, b = config.PARADISE_COURT_RADII
        self.court = (cx, cy, float(a), float(b))
        gx, gy = zone.facing
        self.facing = (gx, gy)
        self.court_gate = _ellipse_point(cx, cy, a, b, gx, gy, self.WALL / 2)
        shore = zone.shore_along(gx, gy)
        self.gate = (round(cx + gx * (shore - 3)), round(cy + gy * (shore - 3)))

        # The main road: out of the court's gate, down to just inside the Gate.
        start = _ellipse_point(cx, cy, a, b, gx, gy, self.WALL + 2)
        end = (self.gate[0] - gx * 6, self.gate[1] - gy * 6)
        main = _meander(start, end, config.PARADISE_ROAD_SWAY, rng, 7)
        # A ring road round the summit, just past the outermost terrace.
        grow = self.WALL + config.PARADISE_TERRACES[-1] + 8
        ring = [(cx + math.cos(k * _TAU / 72) * (a + grow), cy + math.sin(k * _TAU / 72) * (b + grow))
                for k in range(73)]
        self.roads: list[list[tuple[float, float]]] = [main, ring]

        # The river of blood: from the court's side, out and down to the sea.
        side = rng.choice((-1, 1))
        ux, uy = _rotate(gx, gy, side * rng.uniform(1.75, 2.45))
        self.river_dir = (ux, uy)
        r_start = _ellipse_point(cx, cy, a, b, ux, uy, self.WALL + 1)
        ex, ey = _rotate(ux, uy, side * rng.uniform(-0.2, 0.35))
        reach = zone.shore_along(ex, ey) + 10
        r_end = (cx + ex * reach, cy + ey * reach)
        self.river = _meander(r_start, r_end, config.PARADISE_RIVER_SWAY, rng, 9)
        self.river_spout = _ellipse_point(cx, cy, a, b, ux, uy, -1)   # inside the wall

        # The landmarks' spots, the biggest first.
        self._placed: list[tuple[float, float, float, float]] = []
        self._placed.append((*self.gate, 44.0, 8.0))      # (the Gate along the shore)
        avoid = _segments([main, ring, self.river])
        self.cathedral = self._site(rng, 25, 13, avoid)
        stair_c = self._site(rng, 15, 15, avoid)
        self.stair = None
        if stair_c is not None:
            o = _axis(stair_c[0] - cx, stair_c[1] - cy)     # climbing outward
            self.stair = (round(stair_c[0] - o[0] * 14), round(stair_c[1] - o[1] * 14), o)
        self.choirs = [s for s in (self._site(rng, 9, 9, avoid)
                                   for _ in range(config.PARADISE_CHOIRS)) if s]
        self.fonts = [s for s in (self._site(rng, 5, 4, avoid)
                                  for _ in range(config.PARADISE_FONTS)) if s]
        self.statues = [s for s in (self._site(rng, 7, 7, avoid)
                                    for _ in range(config.PARADISE_STATUES)) if s]
        # The seven seals (M29.4), each in its clearing, spread over the island.
        self.seals: list[tuple[int, int]] = []
        c = config.SEVEN_SEAL_CLEARING
        for _ in range(7):
            at = self._site(rng, c, c, avoid, apart=(self.seals, config.SEVEN_SEAL_GAP))
            if at is not None:
                self.seals.append(at)
        self.quest = next((k for k, q in config.QUESTS.items() if q.biome == zone.key), "")

        # Spur roads from the main road to the cathedral's door, the
        # stairway's foot and each choir ring.
        ends = []
        if self.cathedral is not None:
            ends.append((self.cathedral[0] - 25, self.cathedral[1] + 0.5))
        if self.stair is not None:
            sx, sy, (ox, oy) = self.stair
            ends.append((sx - ox * 3 + 0.5, sy - oy * 3 + 0.5))
        for qx, qy in self.choirs:
            ends.append((qx + 0.5, qy + 0.5))
        for ex2, ey2 in ends:
            near = min((_nearest_on(ex2, ey2, line) for line in (main, ring)),
                       key=lambda q: math.hypot(ex2 - q[0], ey2 - q[1]))
            if math.hypot(ex2 - near[0], ey2 - near[1]) > 4:
                self.roads.append(_meander(near, (ex2, ey2), 6.0, rng, 3))

        self._road_segs = _segments(self.roads)
        self._river_segs = _segments([self.river])
        self.posts = self._posts()
        self.marks = self._build_marks(rng)

    # --- Placement ---------------------------------------------------------------------

    def _site(self, rng: random.Random, hw: float, hh: float, avoid,
              tries: int = 600, apart=None) -> tuple[int, int] | None:
        """A random centre for a (2hw x 2hh) footprint: on the island with
        4 tiles to spare, clear of the court and its terraces, of the main
        road and the river, and PARADISE_SITE_GAP from every spot taken
        (`apart`: (points, d) -- and at least d from each of those)."""
        z = self.zone
        cx, cy, a, b = self.court
        t = config.PARADISE_TERRACES[-1] + 8
        gap = config.PARADISE_SITE_GAP
        reach = math.hypot(hw, hh) + 5
        for _ in range(tries):
            r = math.sqrt(rng.random()) * z.radius
            ang = rng.uniform(0.0, _TAU)
            x, y = round(cx + math.cos(ang) * r), round(cy + math.sin(ang) * r)
            if ((x - cx) / (a + t + hw)) ** 2 + ((y - cy) / (b + t + hh)) ** 2 < 1.0:
                continue
            if any(abs(x - px) < hw + phw + gap and abs(y - py) < hh + phh + gap
                   for px, py, phw, phh in self._placed):
                continue
            gx = x + np.linspace(-hw - 4, hw + 4, 5)[None, :]
            gy = y + np.linspace(-hh - 4, hh + 4, 5)[:, None]
            if not z.inside(gx, gy).all():
                continue
            if _point_dist(x, y, avoid) < reach:
                continue
            if apart is not None and any(math.hypot(x - px, y - py) < apart[1]
                                         for px, py in apart[0]):
                continue                     # (the seals keep well apart)
            self._placed.append((x, y, hw, hh))
            return x, y
        return None

    def _posts(self) -> dict[tuple[int, int], list[tuple[int, int]]]:
        """Gold posts every PARADISE_POST_EVERY tiles along every road, on
        both sides, by chunk (none in the court or its gate's way)."""
        out: dict[tuple[int, int], list[tuple[int, int]]] = {}
        cx, cy, a, b = self.court
        off = config.PARADISE_ROAD_W + 1.2
        every = config.PARADISE_POST_EVERY
        n = config.CHUNK_SIZE
        for line in self.roads:
            carried = every / 2
            for (ax, ay), (bx, by) in zip(line, line[1:]):
                seg = math.hypot(bx - ax, by - ay)
                if seg <= 0:
                    continue
                ux, uy = (bx - ax) / seg, (by - ay) / seg
                d = carried
                while d < seg:
                    px, py = ax + ux * d, ay + uy * d
                    for s in (-1, 1):
                        tx, ty = math.floor(px - uy * off * s), math.floor(py + ux * off * s)
                        if ((tx + 0.5 - cx) / (a + 12)) ** 2 + ((ty + 0.5 - cy) / (b + 12)) ** 2 < 1:
                            continue
                        out.setdefault((tx // n, ty // n), []).append((tx, ty))
                    d += every
                carried = d - seg
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
        return self._Landmark(key, kind, "paradise", name, x0, y0, rows, cx=cx, cy=cy, **kw)

    def _build_marks(self, rng: random.Random) -> list:
        out = [self._court(), self._gate(rng)]
        if self.cathedral is not None:
            out.append(self._cathedral(rng))
        if self.stair is not None:
            out.append(self._stairway(rng))
        out += [self._choir(x, y) for x, y in self.choirs]
        out += [self._font(x, y) for x, y in self.fonts]
        out += [self._weeping(x, y, rng) for x, y in self.statues]
        out += [self._seal(x, y) for x, y in self.seals]
        return [m for m in out if m is not None]

    def _court(self):
        cx, cy, a, b = self.court
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
        # The gate: wall tiles within half its width of the line out to the Gate.
        across = np.abs((X - cx) * -gy + (Y - cy) * gx)
        gate = wall & (across <= config.PARADISE_COURT_GATE / 2) & ((X - cx) * gx + (Y - cy) * gy > 0)
        ring = np.sqrt(e_in)
        inlay = inside & ((np.abs(ring - 0.36) * b < 0.5) | (np.abs(ring - 0.72) * b < 0.5))
        cells: dict = {}
        gate_tiles = []
        H, W = e_in.shape
        for j in range(H):
            for i in range(W):
                t = None
                if gate[j, i]:
                    t = tiles.GATE_BARS
                    gate_tiles.append((x0 + i, y0 + j))
                elif wall[j, i]:
                    t = tiles.PEARL_WALL
                elif inlay[j, i]:
                    t = tiles.GOLD_INLAY
                elif inside[j, i]:
                    t = tiles.MARBLE_FLOOR
                if t is not None:
                    cells[(x0 + i, y0 + j)] = t
        # Columns: eight round the middle, for cover (not on the gate's way,
        # the throne's or the channel's).
        ux, uy = self.river_dir
        for k in range(8):
            ang = (k + 0.5) * _TAU / 8
            px, py = cx + math.cos(ang) * a * 0.55, cy + math.sin(ang) * b * 0.55
            for dx, dy in ((0, 0), (1, 0)):
                cells[(math.floor(px) + dx, math.floor(py) + dy)] = tiles.COLUMN
        # The throne at the far side, steps before it.
        tx, ty = cx - gx * b * 0.78, cy - gy * b * 0.78
        vx, vy = -gy, gx                                  # along the throne
        throne = []
        for s in range(-4, 5):
            for d in range(0, 3):
                p = (math.floor(tx + vx * s - gx * d), math.floor(ty + vy * s - gy * d))
                cells[p] = tiles.THRONE
                throne.append(p)
            cells[(math.floor(tx + vx * s + gx * 1), math.floor(ty + vy * s + gy * 1))] = tiles.STEP
        # The channel: the river's start, from the throne's foot to the wall
        # (the wall stays whole: the river goes on outside it).
        sx, sy = tx + gx * 2, ty + gy * 2
        ex, ey = self.river_spout
        steps = int(math.hypot(ex - sx, ey - sy))
        for k in range(steps):
            p = (math.floor(sx + (ex - sx) * k / steps), math.floor(sy + (ey - sy) * k / steps))
            if cells.get(p) in (tiles.MARBLE_FLOOR, tiles.GOLD_INLAY):
                cells[p] = tiles.BLOOD_RIVER
        # (the quest's lair, M29.4: its bars open when the seventh seal
        # breaks, close behind you for the fight, open when it's won)
        return self._mark("paradise_court", "lair", "The Summit Court", cells, cx, cy,
                          gate=gate_tiles, radii=(a, b), floor=tiles.MARBLE_FLOOR,
                          props={"throne": (tx, ty), "seal": tiles.GATE_BARS, "barred": True},
                          quest=self.quest, spots=[(cx, cy)])

    def _gate(self, rng: random.Random):
        """The Gate on the shore facing the main island. Local frame: i
        along the shore, j inland (j 0-1: the wall's rows)."""
        gcx, gcy = self.gate
        gx, gy = self.facing
        vx, vy = -gx, -gy                       # inland
        ux, uy = -vy, vx                        # along the shore
        cells: dict = {}

        def at(i: int, j: int, t) -> None:
            cells[(round(gcx + ux * i + vx * j), round(gcy + uy * i + vy * j))] = t

        for i in range(-40, 41):
            ai = abs(i)
            for j in (0, 1):
                if ai in (4, 5):
                    continue
                if ai >= 6:
                    gone = 0.22 + max(0, ai - 28) * 0.06      # more broken toward its ends
                    r = rng.random()
                    if r < gone * 0.5:
                        continue
                    at(i, j, tiles.MARBLE_RUBBLE if r < gone else tiles.PEARL_WALL)
                elif i <= 0:
                    at(i, j, tiles.GATE_BARS)                 # the shut leaf
                else:
                    at(i, j, tiles.MARBLE_ROAD)               # the open half
        for i in (-5, -4, 4, 5):
            for j in range(-1, 3):
                at(i, j, tiles.GATE_PILLAR)
        for j in range(3, 7):
            at(4, j, tiles.GATE_BARS)                         # the leaf, swung open inland
        for i in range(-3, 4):
            for j in range(2, 7):
                if (round(gcx + ux * i + vx * j), round(gcy + uy * i + vy * j)) not in cells:
                    at(i, j, tiles.MARBLE_ROAD)
        return self._mark("paradise_gate", "zone", "The Gate", cells, gcx, gcy, land_only=True)

    def _cathedral(self, rng: random.Random):
        sx, sy = self.cathedral
        w, h = 46, 22
        x0, y0 = sx - w // 2, sy - h // 2
        cells: dict = {}
        mid = h // 2
        breaks = set()
        for _ in range(3):                                  # big gaps in the walls
            if rng.random() < 0.5:
                j = rng.choice((0, h - 1))
                i0 = rng.randrange(4, w - 10)
                breaks.update((i, j) for i in range(i0, i0 + rng.randint(3, 6)))
            else:
                i = w - 1
                j0 = rng.randrange(3, h - 8)
                breaks.update((i, j) for j in range(j0, j0 + rng.randint(3, 5)))
        for j in range(h):
            for i in range(w):
                edge = i in (0, w - 1) or j in (0, h - 1)
                if not edge:
                    t = tiles.MARBLE_FLOOR
                elif i == 0 and mid - 2 <= j <= mid + 1:
                    t = tiles.MARBLE_FLOOR                  # the west door
                elif (i, j) in breaks or rng.random() < 0.18:
                    t = tiles.MARBLE_RUBBLE
                else:
                    t = tiles.PEARL_WALL
                cells[(x0 + i, y0 + j)] = t
        for j in (6, h - 7):                                # the nave's two rows of pillars
            for i in range(7, w - 9, 5):
                r = rng.random()
                if r < 0.22:
                    for k in range(rng.randint(2, 3)):
                        cells[(x0 + i + k, y0 + j)] = tiles.FALLEN_COLUMN
                elif r < 0.36:
                    cells[(x0 + i, y0 + j)] = tiles.MARBLE_RUBBLE
                else:
                    cells[(x0 + i, y0 + j)] = tiles.COLUMN
        for i in range(w - 6, w - 2):                       # the altar, and steps before it
            for j in (mid - 1, mid):
                cells[(x0 + i, y0 + j)] = tiles.ALTAR
        for j in range(mid - 3, mid + 3):
            cells[(x0 + w - 8, y0 + j)] = tiles.STEP
        glass = (tiles.GLASS_RED, tiles.GLASS_BLUE, tiles.GLASS_GOLD)
        for j in range(1, h - 1):                           # the rose window, shattered
            for i in range(1, 14):
                if math.hypot(i - 6, j - mid + 0.5) <= 6 and rng.random() < 0.42 \
                        and cells.get((x0 + i, y0 + j)) is tiles.MARBLE_FLOOR:
                    cells[(x0 + i, y0 + j)] = rng.choice(glass)
        return self._mark("paradise_cathedral", "zone", "The Fallen Cathedral", cells, sx, sy)

    def _stairway(self, rng: random.Random):
        """The stairway to nowhere: a landing at its foot (the chain post
        beside it), white steps climbing out for 26 tiles, the last ones
        fading into a puff of cloud. Local frame: i across, j along."""
        sx, sy, (ox, oy) = self.stair
        ux, uy = -oy, ox
        cells: dict = {}
        length = 26

        def at(i: int, j: int, t) -> None:
            cells[(sx + ux * i + ox * j, sy + uy * i + oy * j)] = t

        for j in range(-3, 0):                              # the landing
            for i in range(-3, 4):
                at(i, j, tiles.MARBLE_FLOOR)
        for j in range(0, length):
            fade = j >= length - 5
            for i in range(-1, 2):
                at(i, j, tiles.STAIR_END if fade else tiles.STAIR)
            if j < length - 3:
                at(-2, j, tiles.BALUSTRADE)
                at(2, j, tiles.BALUSTRADE)
        for j in range(length, length + 3):
            for i in range(-1, 2):
                if rng.random() < 0.6:
                    at(i, j, tiles.CLOUD_DRIFT)
        at(-4, -2, tiles.CHAIN_POST)
        npc = (sx + ux * -3 + ox * -2 + 0.5, sy + uy * -3 + oy * -2 + 0.5)
        # (the quest's camp, M29.4: the fallen angel is chained here; its
        # spots are the seven seals)
        return self._mark("paradise_stairway", "camp", "The Stairway to Nowhere", cells,
                          sx + 0.5, sy + 0.5, npc=npc, quest=self.quest,
                          spots=[(x + 0.5, y + 0.5) for x, y in self.seals])

    def _choir(self, x: int, y: int):
        cells: dict = {}
        for j in range(-7, 8):
            for i in range(-7, 8):
                if i * i + j * j <= 7.3 * 7.3:
                    cells[(x + i, y + j)] = tiles.MARBLE_FLOOR
        for k in range(8):
            ang = k * _TAU / 8
            cells[(x + round(math.cos(ang) * 6), y + round(math.sin(ang) * 6))] = tiles.STATUE
        for i, j in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            cells[(x + i, y + j)] = tiles.GOLD_INLAY
        return self._mark("paradise_choir", "zone", "Choir Ring", cells, x + 0.5, y + 0.5)

    def _font(self, x: int, y: int):
        cells: dict = {}
        for j in range(-3, 3):
            for i in range(-3, 4):
                rim = abs(i) == 2 and -2 <= j <= 1 or j in (-2, 1) and abs(i) <= 2
                inner = abs(i) <= 1 and -1 <= j <= 0
                t = tiles.BLOOD_FONT if inner else tiles.FONT_RIM if rim else tiles.MARBLE_FLOOR
                cells[(x + i, y + j)] = t
        return self._mark("paradise_font", "zone", "Blood Font", cells, x + 0.5, y)

    def _weeping(self, x: int, y: int, rng: random.Random):
        """A weeping statue on a plinth; its blood trickles away downhill
        (away from the summit), wandering a little."""
        cells: dict = {}
        for j in range(-1, 2):
            for i in range(-1, 2):
                cells[(x + i, y + j)] = tiles.MARBLE_FLOOR
        cells[(x, y)] = tiles.WEEPING_STATUE
        cx, cy = self.court[0], self.court[1]
        d = math.hypot(x - cx, y - cy) or 1.0
        ux, uy = (x - cx) / d, (y - cy) / d
        px, py = x + 0.5 + ux * 2, y + 0.5 + uy * 2
        for _ in range(rng.randint(6, 10)):
            side = rng.uniform(-0.8, 0.8)
            px += ux - uy * side
            py += uy + ux * side
            p = (math.floor(px), math.floor(py))
            if p not in cells:
                cells[p] = tiles.BLOOD_TRICKLE
        return self._mark("paradise_statue", "zone", "Weeping Statue", cells, x + 0.5, y + 0.5)

    def _seal(self, x: int, y: int):
        """A seal's clearing (M29.4): a marble disc, a gold ring at
        SEVEN_SEAL_RADIUS (stand inside it), the seal in the middle."""
        cells: dict = {}
        c = config.SEVEN_SEAL_CLEARING
        ring = config.SEVEN_SEAL_RADIUS
        for j in range(-c, c + 1):
            for i in range(-c, c + 1):
                d = math.hypot(i, j)
                if d <= c + 0.3:
                    cells[(x + i, y + j)] = (tiles.GOLD_INLAY if abs(d - ring) < 0.5
                                             else tiles.MARBLE_FLOOR)
        cells[(x, y)] = tiles.SEVEN_SEAL
        return self._mark("paradise_seal", "spot", "A Seal", cells, x + 0.5, y + 0.5,
                          quest=self.quest)

    # --- Per chunk ------------------------------------------------------------------------

    def paint(self, x0: int, y0: int, xs, ys, ids, biome_ids, r1, T) -> None:
        """Lay the roads, the river, the posts, the terraces and the cloud
        bank into one chunk's tile indices (`T`: tile -> index)."""
        z = self.zone
        X, Y = np.broadcast_arrays(xs, ys)
        land = biome_ids == z.biome_id
        if land.any():
            cx, cy, a, b = self.court
            for off in config.PARADISE_TERRACES:
                e = np.sqrt(((X - cx) / (a + self.WALL + off)) ** 2
                            + ((Y - cy) / (b + self.WALL + off)) ** 2)
                ring = land & (np.abs(e - 1.0) * (b + self.WALL + off) < 0.55)
                ids[ring] = T(tiles.STEP)
            river = land & (_line_dist(X, Y, self._river_segs, 8) < config.PARADISE_RIVER_W)
            road = land & (_line_dist(X, Y, self._road_segs, 8) < config.PARADISE_ROAD_W)
            ids[river & ~road] = T(tiles.BLOOD_RIVER)
            ids[road & ~river] = T(tiles.MARBLE_ROAD)
            ids[road & river] = T(tiles.MARBLE_BRIDGE)
            n = config.CHUNK_SIZE
            blocked = (T(tiles.MARBLE_ROAD), T(tiles.BLOOD_RIVER), T(tiles.MARBLE_BRIDGE))
            for tx, ty in self.posts.get((x0 // n, y0 // n), ()):
                i, j = tx - x0, ty - y0
                if land[j, i] and ids[j, i] not in blocked:
                    ids[j, i] = T(tiles.GOLD_POST)
        # The cloud bank: the sea within PARADISE_CLOUD_BANK of the shore
        # turns to cloud, thinning out the farther it is.
        sea = biome_ids == biomes.OCEAN.id
        if sea.any() or land.any():
            d = np.hypot(X - z.cx, Y - z.cy)
            near = d < z.max_radius + config.PARADISE_CLOUD_BANK
            if near.any():
                out = np.full(d.shape, np.inf)
                out[near] = d[near] - z.coast(X[near], Y[near])
                bank = config.PARADISE_CLOUD_BANK
                thick = np.clip(1.0 - out / bank, 0.0, 1.0) ** 0.8
                ids[sea & (out > 0) & (r1 < thick)] = T(tiles.CLOUD_BANK)
                # The land's very edge goes soft too.
                edge = land & (out > -2.5) & (r1 < 0.7) & (ids == T(tiles.CLOUD))
                ids[edge] = T(tiles.CLOUD_DRIFT)


def plan_of(layout, zone) -> Plan:
    """The zone's plan (built on first use, kept on the zone)."""
    if zone.plan is None:
        zone.plan = Plan(layout, zone)
    return zone.plan
