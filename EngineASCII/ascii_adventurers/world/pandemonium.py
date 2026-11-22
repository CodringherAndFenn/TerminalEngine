"""
world/pandemonium.py -- Pandemonium's land (M30.1, design/OCEAN.md 13).

The south zone's island (world/zones.py places it): black obsidian veined
with gold, sinking in gold-leaf terraces to the palace at the bottom of a
pit. Its own plan, worked out once per seed (zones.plan_of, cached on the
zone):

  * the palace's great hall at the centre: the boss's arena (the Host of
    the Feast, M30.4-5), an oval of PANDEMONIUM_HALL_RADII walled in black
    marble trimmed with gold, its gilded gate facing the pier (sealed until
    the seventh bandstand falls silent), the host's seat at the far side, a
    crimson carpet between. The wine lake rings it; gold-leaf terrace edges
    step up out of the pit round it (PANDEMONIUM_TERRACES), the stone
    darker on the pit's floor;
  * the gilded pier on the shore facing the main island, where you arrive
    (Paradise's Gate): a plaza, a welcome arch, a long jetty out over the
    wine-dark sea lit by lanterns, pleasure barges moored alongside;
  * the avenue from the pier down the terraces (gold stairs at each edge)
    and over the lake (a causeway) to the hall's gate; a ring avenue round
    the pit; spurs (from whichever is nearer) to the landmarks; lanterns
    along every avenue;
  * the wine press near the rim, among its terraced vineyards, and the
    river of wine from it down the terraces into the lake;
  * the endless banquet hall, the hall of mirrors, PANDEMONIUM_BANDSTANDS
    bandstands (kept well apart: the quest's, M30.4),
    PANDEMONIUM_TABLES banquet tables (where the revellers' groups sit,
    M30.2), PANDEMONIUM_FOUNTAINS wine fountains and PANDEMONIUM_STATUES
    gilded statues, at random spots clear of the pit, the avenue, the river
    and each other.

The landmarks are ordinary world/landmarks.Landmark stamps (they stream,
persist and map like any other). The avenues, lanterns, terraces, river,
lake, coin beach and wine-dark sea are painted per chunk by `paint` (from
world/generator.build_chunk).
"""

from __future__ import annotations

import math
import random

import numpy as np

from .. import config
from . import biomes, tiles
from .paradise import _ellipse_point, _line_dist, _meander, _nearest_on, _point_dist, _segments
from .rng import hash_coords

_TAU = 2.0 * math.pi


class Plan:
    """Where everything on Pandemonium is, for one seed. `marks` are its
    landmarks; `roads`, `river` and `lanterns` are painted per chunk."""

    WALL = 3                         # the hall's wall, tiles thick

    def __init__(self, layout, zone) -> None:
        from .landmarks import Landmark   # (landmarks imports the zones' plans)
        self._Landmark = Landmark
        self.zone = zone
        rng = random.Random(hash_coords(layout.seed, 0x9A4D, zone.salt))
        cx, cy = float(zone.cx), float(zone.cy)
        a, b = config.PANDEMONIUM_HALL_RADII
        w = self.WALL
        self.hall = (cx, cy, float(a), float(b))
        gx, gy = zone.facing
        self.facing = (gx, gy)
        self.lake_grow = w + config.PANDEMONIUM_LAKE      # the lake's outer edge
        shore = zone.shore_along(gx, gy)
        # The pier's root, on land a few tiles in from the shore (Paradise's Gate).
        self.gate = (round(cx + gx * (shore - 4)), round(cy + gy * (shore - 4)))
        self.hall_gate = _ellipse_point(cx, cy, a, b, gx, gy, w / 2)

        # The avenue: out of the hall's gate, over the lake, up the terraces
        # to the plaza at the pier's root.
        start = _ellipse_point(cx, cy, a, b, gx, gy, w + 1)
        end = (self.gate[0] - gx * 7, self.gate[1] - gy * 7)
        main = _meander(start, end, config.PANDEMONIUM_ROAD_SWAY, rng, 7)
        # The ring avenue round the pit, just outside one of the terraces.
        grow = w + config.PANDEMONIUM_TERRACES[config.PANDEMONIUM_RING_TERRACE] + 6
        ring = [(cx + math.cos(k * _TAU / 96) * (a + grow), cy + math.sin(k * _TAU / 96) * (b + grow))
                for k in range(97)]
        self.roads: list[list[tuple[float, float]]] = [main, ring]

        # The landmarks' spots, the biggest first. The wine press goes near
        # the rim (past the outermost terrace), off the avenue's side.
        self._placed: list[tuple[float, float, float, float]] = [(*self.gate, 14.0, 14.0)]
        self.press = self._site(rng, 16, 13, _segments([main, ring]), rim=True)
        self.river: list[tuple[float, float]] = []
        if self.press is not None:
            px, py = self.press
            d = math.hypot(px - cx, py - cy) or 1.0
            ux, uy = (cx - px) / d, (cy - py) / d             # toward the pit
            r_start = (px + ux * 9, py + uy * 9)              # out of the press's spout
            r_end = _ellipse_point(cx, cy, a, b, -ux, -uy, self.lake_grow - 3)
            self.river = _meander(r_start, r_end, config.PANDEMONIUM_RIVER_SWAY, rng, 9)
        avoid = _segments([main, ring] + ([self.river] if self.river else []))
        self.banquet = self._site(rng, 33, 10, avoid)
        self.mirrors = self._site(rng, 21, 13, avoid)
        self.bandstands: list[tuple[int, int]] = []
        for _ in range(config.PANDEMONIUM_BANDSTANDS):
            at = self._site(rng, 8, 8, avoid,
                            apart=(self.bandstands, config.PANDEMONIUM_BANDSTAND_GAP))
            if at is not None:
                self.bandstands.append(at)
        self.tables = [s for s in (self._site(rng, 7, 4, avoid)
                                   for _ in range(config.PANDEMONIUM_TABLES)) if s]
        self.fountains = [s for s in (self._site(rng, 4, 3, avoid)
                                      for _ in range(config.PANDEMONIUM_FOUNTAINS)) if s]
        self.statues = [s for s in (self._site(rng, 4, 3, avoid)
                                    for _ in range(config.PANDEMONIUM_STATUES)) if s]
        self.quest = next((k for k, q in config.QUESTS.items() if q.biome == zone.key), "")

        # Spurs from the nearer avenue to the banquet hall's west door, the
        # hall of mirrors' west door, the wine press and each bandstand.
        ends = []
        if self.banquet is not None:
            ends.append((self.banquet[0] - 34, self.banquet[1] + 0.5))
        if self.mirrors is not None:
            ends.append((self.mirrors[0] - 22, self.mirrors[1] + 0.5))
        if self.press is not None:
            ends.append((self.press[0] + 0.5, self.press[1] - 14))
        for qx, qy in self.bandstands:
            ends.append((qx + 0.5, qy + 0.5))
        for ex, ey in ends:
            near = min((_nearest_on(ex, ey, line) for line in (main, ring)),
                       key=lambda q: math.hypot(ex - q[0], ey - q[1]))
            if math.hypot(ex - near[0], ey - near[1]) > 4:
                self.roads.append(_meander(near, (ex, ey), 6.0, rng, 3))

        self._road_segs = _segments(self.roads)
        self._river_segs = _segments([self.river]) if self.river else []
        self.lanterns = self._lanterns()
        self.marks = self._build_marks(rng)

    # --- Placement ---------------------------------------------------------------------

    def _ellipse(self, x: float, y: float, grow: float) -> float:
        """Where (x, y) sits against the hall's oval grown by `grow` (< 1:
        inside)."""
        cx, cy, a, b = self.hall
        return ((x - cx) / (a + grow)) ** 2 + ((y - cy) / (b + grow)) ** 2

    def _site(self, rng: random.Random, hw: float, hh: float, avoid, tries: int = 600,
              apart=None, rim: bool = False) -> tuple[int, int] | None:
        """A random centre for a (2hw x 2hh) footprint: on the island with 4
        tiles to spare, out of the pit's first terrace (`rim`: past the
        outermost one, near the shore), clear of the avenues and the river,
        and PANDEMONIUM_SITE_GAP from every spot taken (`apart`: (points,
        d) -- and at least d from each of those)."""
        z = self.zone
        cx, cy = self.hall[0], self.hall[1]
        first = self.WALL + config.PANDEMONIUM_TERRACES[0] + 6
        last = self.WALL + config.PANDEMONIUM_TERRACES[-1] + 8
        gap = config.PANDEMONIUM_SITE_GAP
        reach = math.hypot(hw, hh) + 5
        fx, fy = self.facing
        for _ in range(tries):
            r = math.sqrt(rng.random()) * z.radius
            ang = rng.uniform(0.0, _TAU)
            x, y = round(cx + math.cos(ang) * r), round(cy + math.sin(ang) * r)
            if self._ellipse(x, y, first + max(hw, hh)) < 1.0:
                continue
            if rim:
                if self._ellipse(x, y, last + max(hw, hh)) < 1.0:
                    continue
                if (math.cos(ang) * fx + math.sin(ang) * fy) > 0.5:
                    continue                  # (not in front of the pier: off to a side)
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
                continue
            self._placed.append((x, y, hw, hh))
            return x, y
        return None

    def _lanterns(self) -> dict[tuple[int, int], list[tuple[int, int]]]:
        """Lanterns every PANDEMONIUM_LANTERN_EVERY tiles along every avenue,
        on both sides, by chunk (none over the lake or in the hall)."""
        out: dict[tuple[int, int], list[tuple[int, int]]] = {}
        off = config.PANDEMONIUM_ROAD_W + 1.2
        every = config.PANDEMONIUM_LANTERN_EVERY
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
                        if self._ellipse(tx + 0.5, ty + 0.5, self.lake_grow + 3) < 1.0:
                            continue
                        out.setdefault((tx // n, ty // n), []).append((tx, ty))
                    d += every
                carried = d - seg
        return out

    # --- Landmarks --------------------------------------------------------------------

    def _mark(self, key: str, kind: str, name: str, cells: dict, cx: float, cy: float, **kw):
        """A Landmark from a {(tx, ty): tile} dict (None round them)."""
        if not cells:
            return None
        xs = [p[0] for p in cells]
        ys = [p[1] for p in cells]
        x0, y0 = min(xs), min(ys)
        rows = [[None] * (max(xs) - x0 + 1) for _ in range(max(ys) - y0 + 1)]
        for (tx, ty), t in cells.items():
            rows[ty - y0][tx - x0] = t
        return self._Landmark(key, kind, "pandemonium", name, x0, y0, rows, cx=cx, cy=cy, **kw)

    def _build_marks(self, rng: random.Random) -> list:
        out = [self._hall(), self._pier(rng)]
        if self.press is not None:
            out.append(self._press(rng))
        if self.banquet is not None:
            out.append(self._banquet_hall())
        if self.mirrors is not None:
            out.append(self._mirror_hall(rng))
        out += [self._bandstand(x, y) for x, y in self.bandstands]
        out += [self._table(x, y, rng) for x, y in self.tables]
        out += [self._fountain(x, y) for x, y in self.fountains]
        out += [self._statue(x, y) for x, y in self.statues]
        return [m for m in out if m is not None]

    def _hall(self):
        """The palace's great hall: the boss's arena (sealed: M30.4)."""
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
        across = np.abs((X - cx) * -gy + (Y - cy) * gx)
        along = (X - cx) * gx + (Y - cy) * gy
        gate = wall & (across <= config.PANDEMONIUM_HALL_GATE / 2) & (along > 0)
        trim = inside & (np.sqrt(e_in) * b > b - 1.5)            # a gilded band inside the wall
        carpet = inside & (across <= 2.5)                         # the runner, gate to seat
        js, is_ = np.nonzero(inside | wall)
        cells: dict = {}
        gate_tiles = []
        for j, i in zip(js.tolist(), is_.tolist()):
            p = (x0 + i, y0 + j)
            if gate[j, i]:
                cells[p] = tiles.PALACE_GATE
                gate_tiles.append(p)
            elif wall[j, i]:
                cells[p] = tiles.PALACE_WALL
            elif carpet[j, i]:
                cells[p] = tiles.CARPET
            elif trim[j, i]:
                cells[p] = tiles.GILT_FLOOR
            else:
                cells[p] = tiles.HALL_FLOOR
        # The host's seat at the far side, a step of gold before it.
        sx, sy = cx - gx * b * 0.8, cy - gy * b * 0.8
        vx, vy = -gy, gx
        for s in range(-3, 4):
            for d in range(0, 2):
                cells[(math.floor(sx + vx * s - gx * d), math.floor(sy + vy * s - gy * d))] = tiles.HOST_SEAT
            cells[(math.floor(sx + vx * s + gx), math.floor(sy + vy * s + gy))] = tiles.GILT_FLOOR
        # (the quest's lair, M30.4: its gate opens when the seventh bandstand
        # falls silent, closes behind you for the fight, opens when it's won;
        # the Host of the Feast rises from his seat, ai/feast.py)
        return self._mark("pandemonium_hall", "lair", "The Palace", cells, cx, cy,
                          gate=gate_tiles, radii=(a, b), floor=tiles.HALL_FLOOR,
                          props={"seat": (sx, sy), "seal": tiles.PALACE_GATE, "barred": True,
                                 "facing": (gx, gy)},
                          quest=self.quest, spots=[(sx + gx * 4.0, sy + gy * 4.0)])

    def _pier(self, rng: random.Random):
        """The gilded pier. Local frame: i along the shore, j out to sea (0:
        its root, on land; the shore about 4 out)."""
        gcx, gcy = self.gate
        vx, vy = self.facing                   # out to sea
        ux, uy = -vy, vx                       # along the shore
        cells: dict = {}

        def at(i: int, j: int, t) -> None:
            cells[(round(gcx + ux * i + vx * j), round(gcy + uy * i + vy * j))] = t

        for j in range(-8, 1):                              # the plaza at its root
            for i in range(-6, 7):
                at(i, j, tiles.GILT_FLOOR)
        for i, j in ((-6, -8), (6, -8), (-6, 0), (6, 0)):
            at(i, j, tiles.FIRE_BRAZIER)
        for j in range(1, 36):                              # the jetty
            for i in range(-1, 2):
                at(i, j, tiles.PIER_DECK)
            if j % 4 == 0 and j < 32:
                at(-2, j, tiles.LANTERN)
                at(2, j, tiles.LANTERN)
        for j in range(32, 37):                             # the landing at its end
            for i in range(-3, 4):
                at(i, j, tiles.PIER_DECK)
        for j in (1, 2):                                    # the welcome arch
            at(-3, j, tiles.WELCOME_ARCH)
            at(3, j, tiles.WELCOME_ARCH)
        at(-4, 1, tiles.VELVET_BANNER)
        at(4, 1, tiles.VELVET_BANNER)
        for side, j0, j1 in ((1, 9, 19), (-1, 15, 25), (1, 23, 31)):   # barges moored alongside
            for j in range(j0, j1):
                for k in (4, 5, 6):
                    if (j in (j0, j1 - 1)) and k != 5:
                        continue                            # (tapered ends)
                    at(side * k, j, tiles.BARGE)
        # (the quest's camp, M30.4: the sober man hides beside the jetty's
        # root, under the pier; its spots are the seven bandstands)
        npc = (gcx + ux * -2 + vx * 2 + 0.5, gcy + uy * -2 + vy * 2 + 0.5)
        return self._mark("pandemonium_pier", "camp", "The Gilded Pier", cells, gcx + 0.5, gcy + 0.5,
                          npc=npc, quest=self.quest,
                          spots=[(x + 0.5, y + 0.5) for x, y in self.bandstands])

    def _press(self, rng: random.Random):
        """The wine press among its terraced vineyards (the river of wine
        starts at its spout, toward the pit)."""
        px, py = self.press
        cells: dict = {}
        for j in range(-12, 13):
            for i in range(-15, 16):
                yard = abs(i) <= 7 and abs(j) <= 5
                if yard:
                    cells[(px + i, py + j)] = tiles.GILT_FLOOR
                elif j % 3 == 0 and abs(i) > 1 and rng.random() > 0.06:
                    cells[(px + i, py + j)] = tiles.VINES
        for j in range(-2, 2):
            for i in range(-3, 3):
                cells[(px + i, py + j)] = tiles.WINE_PRESS
        for vx, vy in ((-6, -4), (5, -4), (-6, 3), (5, 3)):     # vats of wine
            for j in range(-1, 2):
                for i in range(-1, 2):
                    cells[(px + vx + i, py + vy + j)] = tiles.WINE if (i, j) == (0, 0) else tiles.VAT
        return self._mark("pandemonium_press", "zone", "The Wine Press", cells, px + 0.5, py + 0.5)

    def _banquet_hall(self):
        """The endless banquet: a roofless hall, one table running its whole
        length, carpets along both sides where the revellers sit."""
        sx, sy = self.banquet
        w, h = 66, 18
        x0, y0 = sx - w // 2, sy - h // 2
        mid = h // 2
        doors = set()
        for i in (w // 3, 2 * w // 3):
            for k in range(-1, 2):
                doors.add((i + k, 0))
                doors.add((i + k, h - 1))
        for j in range(mid - 1, mid + 1):
            doors.add((0, j))
            doors.add((w - 1, j))
        cells: dict = {}
        for j in range(h):
            for i in range(w):
                edge = i in (0, w - 1) or j in (0, h - 1)
                t = tiles.GILT_FLOOR
                if edge and (i, j) not in doors:
                    t = tiles.PALACE_WALL
                elif not edge and 3 <= i <= w - 4 and j in (mid - 3, mid - 2, mid + 1, mid + 2):
                    t = tiles.CARPET
                cells[(x0 + i, y0 + j)] = t
        for i in range(4, w - 4):
            for j in (mid - 1, mid):
                cells[(x0 + i, y0 + j)] = tiles.BANQUET_TABLE
        for i in range(6, w - 5, 10):                       # braziers along the walls
            cells[(x0 + i, y0 + 1)] = tiles.FIRE_BRAZIER
            cells[(x0 + i, y0 + h - 2)] = tiles.FIRE_BRAZIER
        return self._mark("pandemonium_banquet", "zone", "The Endless Banquet", cells, sx + 0.5, sy + 0.5)

    def _mirror_hall(self, rng: random.Random):
        """The hall of mirrors: a ballroom walled in mirrors under rows of
        chandeliers, doors at either end."""
        sx, sy = self.mirrors
        w, h = 42, 24
        x0, y0 = sx - w // 2, sy - h // 2
        mid = h // 2
        cells: dict = {}
        for j in range(h):
            for i in range(w):
                edge = i in (0, w - 1) or j in (0, h - 1)
                door = i in (0, w - 1) and mid - 2 <= j <= mid + 1
                if edge and not door:
                    t = tiles.HALL_MIRROR
                elif j in (1, h - 2) or i in (1, w - 2):
                    t = tiles.GILT_FLOOR                    # a gilded band along the mirrors
                else:
                    t = tiles.BALLROOM_FLOOR
                cells[(x0 + i, y0 + j)] = t
        for j in range(5, h - 3, 7):
            for i in range(6, w - 4, 8):
                cells[(x0 + i, y0 + j)] = tiles.CHANDELIER
        return self._mark("pandemonium_mirrors", "zone", "The Hall of Mirrors", cells, sx + 0.5, sy + 0.5)

    def _bandstand(self, x: int, y: int):
        """A round bandstand, its instruments in the middle, lanterns round
        it (one of the seven: the quest's, M30.4)."""
        cells: dict = {}
        for j in range(-7, 8):
            for i in range(-7, 8):
                if i * i + j * j <= 6.3 * 6.3:
                    cells[(x + i, y + j)] = tiles.BANDSTAND
        for i, j in ((-1, -1), (0, -1), (1, -1), (-2, 1), (2, 1)):
            cells[(x + i, y + j)] = tiles.INSTRUMENT
        for k in range(8):
            ang = (k + 0.5) * _TAU / 8
            cells[(x + round(math.cos(ang) * 7.6), y + round(math.sin(ang) * 7.6))] = tiles.LANTERN
        return self._mark("pandemonium_bandstand", "zone", "Bandstand", cells, x + 0.5, y + 0.5)

    def _table(self, x: int, y: int, rng: random.Random):
        """A banquet table on a crimson carpet (a revellers' group sits here,
        M30.2), braziers at two corners."""
        cells: dict = {}
        for j in range(-3, 4):
            for i in range(-6, 7):
                cells[(x + i, y + j)] = tiles.CARPET
        for j in (-1, 0):
            for i in range(-4, 5):
                cells[(x + i, y + j)] = tiles.BANQUET_TABLE
        s = rng.choice((-1, 1))
        cells[(x - 6 * s, y - 3)] = tiles.FIRE_BRAZIER
        cells[(x + 6 * s, y + 3)] = tiles.FIRE_BRAZIER
        return self._mark("pandemonium_table", "zone", "Banquet Table", cells, x + 0.5, y)

    def _fountain(self, x: int, y: int):
        cells: dict = {}
        for j in range(-3, 3):
            for i in range(-3, 4):
                rim = abs(i) == 2 and -2 <= j <= 1 or j in (-2, 1) and abs(i) <= 2
                inner = abs(i) <= 1 and -1 <= j <= 0
                t = tiles.WINE_FOUNTAIN if inner else tiles.FOUNTAIN_RIM if rim else tiles.GILT_FLOOR
                cells[(x + i, y + j)] = t
        return self._mark("pandemonium_fountain", "zone", "Wine Fountain", cells, x + 0.5, y)

    def _statue(self, x: int, y: int):
        """A gilded statue on its plinth, room round it for the vain and the
        greedy who gather there (M30.3)."""
        cells = {(x + i, y + j): tiles.GILT_FLOOR for j in range(-2, 3) for i in range(-3, 4)}
        cells[(x, y)] = tiles.GILDED_STATUE
        return self._mark("pandemonium_statue", "zone", "Gilded Statue", cells, x + 0.5, y + 0.5)

    # --- Per chunk ------------------------------------------------------------------------

    def paint(self, x0: int, y0: int, xs, ys, ids, biome_ids, r1, T) -> None:
        """Lay the pit's floor and terraces, the lake, the river, the
        avenues and their lanterns, the coin beach and the wine-dark sea
        into one chunk's tile indices (`T`: tile -> index)."""
        z = self.zone
        X, Y = np.broadcast_arrays(xs, ys)
        land = biome_ids == z.biome_id
        if land.any():
            cx, cy, a, b = self.hall
            w = self.WALL

            def oval(grow: float) -> np.ndarray:
                return np.sqrt(((X - cx) / (a + grow)) ** 2 + ((Y - cy) / (b + grow)) ** 2)

            deep = land & (oval(w + config.PANDEMONIUM_DEEP) < 1.0) & (ids == T(tiles.OBSIDIAN))
            ids[deep] = T(tiles.OBSIDIAN_DEEP)
            edge = np.zeros(X.shape, dtype=bool)
            for off in config.PANDEMONIUM_TERRACES:
                g = w + off
                edge |= land & (np.abs(oval(g) - 1.0) * (b + g) < 0.55)
            ids[edge] = T(tiles.TERRACE_EDGE)
            wet = land & (oval(self.lake_grow) < 1.0)
            if self._river_segs:
                wet |= land & (_line_dist(X, Y, self._river_segs, 8) < config.PANDEMONIUM_RIVER_W)
            road = land & (_line_dist(X, Y, self._road_segs, 8) < config.PANDEMONIUM_ROAD_W)
            ids[wet & ~road] = T(tiles.WINE)
            ids[road & ~wet & ~edge] = T(tiles.GILT_ROAD)
            ids[road & edge & ~wet] = T(tiles.GOLD_STAIRS)
            ids[road & wet] = T(tiles.GILT_BRIDGE)
            n = config.CHUNK_SIZE
            blocked = (T(tiles.GILT_ROAD), T(tiles.GOLD_STAIRS), T(tiles.WINE), T(tiles.GILT_BRIDGE))
            for tx, ty in self.lanterns.get((x0 // n, y0 // n), ()):
                i, j = tx - x0, ty - y0
                if land[j, i] and ids[j, i] not in blocked:
                    ids[j, i] = T(tiles.LANTERN)
        # The coin beach, and the sea within PANDEMONIUM_WINE_SEA of the
        # shore gone wine-dark, thinning out the farther it is.
        sea = biome_ids == biomes.OCEAN.id
        if sea.any() or land.any():
            d = np.hypot(X - z.cx, Y - z.cy)
            near = d < z.max_radius + config.PANDEMONIUM_WINE_SEA
            if near.any():
                out = np.full(d.shape, np.inf)
                out[near] = d[near] - z.coast(X[near], Y[near])
                band = config.PANDEMONIUM_WINE_SEA
                # (solid for the first half of the band, then thinning out)
                thick = np.clip(2.0 * (1.0 - out / band), 0.0, 1.0)
                ids[sea & (out > 0) & (r1 < thick)] = T(tiles.WINE_SEA)
                ground = np.isin(ids, (T(tiles.OBSIDIAN), T(tiles.GOLD_VEIN), T(tiles.COINS)))
                beach = land & ground & (out > -config.PANDEMONIUM_BEACH * (0.55 + 0.45 * r1))
                ids[beach] = T(tiles.COIN_BEACH)
