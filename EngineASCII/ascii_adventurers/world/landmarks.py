"""
world/landmarks.py -- fixed structures stamped into the island (M17).

A landmark is a rectangle of hand-placed tiles laid over whatever the biome
generated there: a quest giver's camp, a boss's lair. Each ring biome's
quest (config.QUESTS) names a camp and a lair builder; the run's landmarks
are placed once per seed (IslandLayout.landmarks, built on first use) and
every chunk that overlaps one has its tiles replaced by the generator
(world/generator.py), so they stream, persist and show on the maps like
any other terrain.

Placement is a pure function of the seed: the builder walks along the
middle of the biome's slice (angles nudged either way, since slice borders
bend) until its whole footprint, plus a margin, lies inside that biome.
  * camps sit just past the plains border, so they're early, easy finds;
  * lairs sit half way out across the ring.

The swamp's two:
  * the frog hunter's camp: a big bog (an oval of pools, reeds and lily
    pads, ringed by a walkable mud edge) with the hunter's hut on a deck
    at the edge facing the plains. He stands at his door. The quest's
    psychedelic frogs live at `spots` in the bog.
  * Froggy's pond: an oval arena of LAIR_RADII (about 3 x 3 screens) ringed
    by standing stones, with a gate in the ring facing the plains and a
    mud causeway leading up to it. Inside: mud, pools (the boss dives
    between them; `spots` are their centres, the first is the middle
    one he sleeps in), lily pads round the pools, stone pillars for cover
    spread over the whole floor, reeds. `gate` lists the gap's tiles, which
    the quest system fills with thorns to seal the fight.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

import numpy as np

from .. import config
from . import biomes, tiles
from .noise import fbm
from .rng import hash_coords
from .tiles import TileType

_SALT_BOG = 401
_SALT_REEDS = 409


@dataclass
class Landmark:
    key: str                     # its builder ("frog_camp", "pond_lair")
    kind: str                    # "camp" | "lair"
    biome: str
    name: str                    # shown on the big map
    x0: int                      # the stamp's top-left tile
    y0: int
    rows: list                   # rows of TileType | None (None: keep the generated tile)
    cx: float = 0.0              # its centre (where the map pin goes)
    cy: float = 0.0
    npc: tuple[float, float] | None = None   # camps: where the quest giver stands
    spots: list = field(default_factory=list)  # camps: quest targets; lairs: pool centres
    gate: list = field(default_factory=list)   # lairs: the gap's tiles (sealed in a fight)
    radii: tuple[float, float] = (0.0, 0.0)    # lairs: the arena oval (inside the stones)

    @property
    def w(self) -> int:
        return len(self.rows[0]) if self.rows else 0

    @property
    def h(self) -> int:
        return len(self.rows)

    def contains(self, x: float, y: float, margin: float = 0.0) -> bool:
        """(x, y) inside the stamp's rectangle (grown by `margin` tiles)."""
        return (self.x0 - margin <= x < self.x0 + self.w + margin
                and self.y0 - margin <= y < self.y0 + self.h + margin)

    def inside(self, x: float, y: float, shrink: float = 0.0) -> bool:
        """Lairs: (x, y) on the arena floor (inside the stones, less
        `shrink` tiles)."""
        a, b = self.radii[0] - shrink, self.radii[1] - shrink
        if a <= 0 or b <= 0:
            return False
        return ((x - self.cx) / a) ** 2 + ((y - self.cy) / b) ** 2 < 1.0

    def tile_at(self, tx: int, ty: int) -> TileType | None:
        if 0 <= ty - self.y0 < self.h and 0 <= tx - self.x0 < self.w:
            return self.rows[ty - self.y0][tx - self.x0]
        return None

    def stamp(self, grid: list, cx: int, cy: int, n: int) -> bool:
        """Lay this landmark over chunk (cx, cy)'s tile list (row-major,
        n x n). Returns whether it touched the chunk."""
        x0, y0 = cx * n, cy * n
        lx0, lx1 = max(x0, self.x0), min(x0 + n, self.x0 + self.w)
        ly0, ly1 = max(y0, self.y0), min(y0 + n, self.y0 + self.h)
        if lx0 >= lx1 or ly0 >= ly1:
            return False
        for ty in range(ly0, ly1):
            row = self.rows[ty - self.y0]
            base = (ty - y0) * n - x0
            for tx in range(lx0, lx1):
                t = row[tx - self.x0]
                if t is not None:
                    grid[base + tx] = t
        return True


# --- Placement ------------------------------------------------------------------------


def _slice_angle(layout, biome: str) -> float | None:
    """The middle angle of `biome`'s slice of the ring (None: not on it)."""
    names = [b.name for b in layout.ring]
    if biome not in names:
        return None
    i = names.index(biome)
    return layout.rotation + (i + 0.5) * math.tau / len(names)


def _fits(layout, biome_id: int, cx: float, cy: float, hw: float, hh: float) -> bool:
    """The whole rectangle (centre, half-sizes in tiles) lies in the biome
    (sampled on a grid ~8 tiles apart, smooth borders)."""
    nx, ny = max(3, int(hw / 8) + 2), max(3, int(hh / 8) + 2)
    xs = cx + np.linspace(-hw, hw, nx)[None, :]
    ys = cy + np.linspace(-hh, hh, ny)[:, None]
    return bool((layout.biome_ids(xs, ys, jitter=False) == biome_id).all())


def _find_site(layout, biome: str, radii, hw: float, hh: float, rng: random.Random,
               ) -> tuple[float, float] | None:
    """A centre for a hw x hh (half-size) footprint in `biome`: the first
    radius in `radii` (tiles from the island centre) at the slice's middle
    angle, or nudged either way, where it fits. Candidates are tested in
    batches with one numpy call each (one at a time took most of a second
    for a camp)."""
    mid = _slice_angle(layout, biome)
    if mid is None:
        return None
    biome_id = biomes.BY_NAME[biome].id
    span = math.tau / len(layout.ring)
    nudges = [0.0]
    for k in range(1, 9):
        nudges += [k * span * 0.05, -k * span * 0.05]
    jitter = rng.uniform(-0.08, 0.08) * span
    cands = [(math.cos(mid + jitter + d) * r, math.sin(mid + jitter + d) * r)
             for r in radii for d in nudges]
    nx, ny = max(3, int(hw / 8) + 2), max(3, int(hh / 8) + 2)    # ~8 tiles apart
    gx = np.linspace(-hw, hw, nx)[None, None, :]
    gy = np.linspace(-hh, hh, ny)[None, :, None]
    for i in range(0, len(cands), 96):
        batch = np.array(cands[i:i + 96])
        xs = batch[:, 0][:, None, None] + gx
        ys = batch[:, 1][:, None, None] + gy
        ok = (layout.biome_ids(xs, ys, jitter=False) == biome_id).all(axis=(1, 2))
        if ok.any():
            x, y = batch[int(np.argmax(ok))]
            return round(x), round(y)
    return None


def build_landmarks(layout) -> list[Landmark]:
    """Every quest's camp and lair for this island (config.QUESTS)."""
    out = []
    for q in config.QUESTS.values():
        rng = random.Random(hash_coords(layout.seed, 0x1A4D, biomes.BY_NAME[q.biome].id))
        for key in (q.camp, q.lair):
            mark = BUILDERS[key](layout, q, rng)
            if mark is not None:
                out.append(mark)
    return out


# --- The frog hunter's camp -------------------------------------------------------------


def _frog_camp(layout, quest, rng: random.Random) -> Landmark | None:
    biome = quest.biome
    bw, bh = config.CAMP_BOG_RADII
    hut_w, hut_h = 20, 11                       # the deck the hut stands on
    reach_x = bw + hut_w + 4                    # the camp's half-size, whichever
    reach_y = bh + hut_h + 4                    # side of the bog the hut is on
    half = max(reach_x, reach_y)
    start = layout.plains_radius * (1 - config.PLAINS_EDGE_AMPLITUDE) - config.BORDER_WOBBLE
    radii = [start + k * 8 for k in range(int(layout.plains_radius * 1.2 / 8))]
    # The first radius past the plains where the camp (and a margin) fits,
    # then CAMP_BORDER_GAP tiles further in.
    site = _find_site(layout, biome, radii, half + 6, half + 6, rng)
    if site is None:
        return None
    x, y = site
    r = math.hypot(x, y)
    k = (r + config.CAMP_BORDER_GAP) / max(r, 1.0)
    bx, by = round(x * k), round(y * k)
    if not _fits(layout, biomes.BY_NAME[biome].id, bx, by, half + 2, half + 2):
        bx, by = x, y

    # The hut goes on the side of the bog facing the island's centre.
    tx, ty = -bx, -by
    if abs(tx) * bh >= abs(ty) * bw:            # (compared in bog-radius units)
        side = "w" if tx < 0 else "e"
    else:
        side = "n" if ty < 0 else "s"
    if side in "we":
        hx = bx + (-1 if side == "w" else 1) * (bw + hut_w // 2 + 1)
        hy = by
    else:
        hx = bx
        hy = by + (-1 if side == "n" else 1) * (bh + hut_h // 2 + 1)

    x0 = min(bx - bw - 2, hx - hut_w // 2)
    y0 = min(by - bh - 2, hy - hut_h // 2)
    x1 = max(bx + bw + 3, hx + hut_w // 2 + 1)
    y1 = max(by + bh + 3, hy + hut_h // 2 + 1)
    w, h = x1 - x0, y1 - y0
    rows = [[None] * w for _ in range(h)]

    # The bog: pools where a clumpy noise field is high, reeds and lily
    # pads between, a ring of plain mud round the edge so you can walk all
    # the way round it.
    xs = (np.arange(x0, x1) + 0.5)[None, :]
    ys = (np.arange(y0, y1) + 0.5)[:, None]
    pool = fbm(layout.seed, _SALT_BOG, xs, ys, 7.0, 2)
    reed = fbm(layout.seed, _SALT_REEDS, xs, ys, 3.0, 1)
    ell = ((xs - bx - 0.5) / bw) ** 2 + ((ys - by - 0.5) / bh) ** 2
    for j in range(h):
        for i in range(w):
            e = ell[j, i]
            if e >= 1.0:
                continue
            if e > 0.8:
                rows[j][i] = tiles.MUD
            elif pool[j, i] > config.CAMP_POOL_MIN:
                rows[j][i] = tiles.BOG
            elif pool[j, i] > config.CAMP_POOL_MIN - 0.04:
                rows[j][i] = tiles.LILY_PADS
            elif reed[j, i] > 0.62:
                rows[j][i] = tiles.REEDS
            else:
                rows[j][i] = tiles.MUD

    # The hut: a deck, a plank hut with a doorway toward the plains, two
    # drying racks, and the hunter at his door.
    dx0, dy0 = hx - hut_w // 2, hy - hut_h // 2
    for j in range(hut_h):
        for i in range(hut_w):
            rows[dy0 - y0 + j][dx0 - x0 + i] = tiles.DECK
    wx0, wy0, ww, wh = dx0 + 5, dy0 + 2, 10, 6            # the hut's walls
    door = {"w": [(wx0, wy0 + 2), (wx0, wy0 + 3)], "e": [(wx0 + ww - 1, wy0 + 2),
                                                          (wx0 + ww - 1, wy0 + 3)],
            "n": [(wx0 + 4, wy0), (wx0 + 5, wy0)], "s": [(wx0 + 4, wy0 + wh - 1),
                                                         (wx0 + 5, wy0 + wh - 1)]}[side]
    for j in range(wh):
        for i in range(ww):
            if i in (0, ww - 1) or j in (0, wh - 1):
                if (wx0 + i, wy0 + j) not in door:
                    rows[wy0 + j - y0][wx0 + i - x0] = tiles.PLANK_WALL
    out_x = {"w": -2, "e": 2, "n": 0, "s": 0}[side]
    out_y = {"w": 0, "e": 0, "n": -2, "s": 2}[side]
    npc_tx, npc_ty = door[0][0] + out_x, door[0][1] + out_y
    rows[npc_ty - y0][npc_tx - x0] = tiles.HUNTER_POST
    for rx, ry in ((dx0 + 1, dy0 + 1), (dx0 + hut_w - 2, dy0 + hut_h - 2)):
        rows[ry - y0][rx - x0] = tiles.DRYING_RACK

    # Where the frogs live: open bog tiles spread over the bog (one per
    # sector of the oval, so they're not all in one corner).
    n = quest.count
    spots = []
    for s in range(n):
        for _ in range(60):
            a = (s + rng.uniform(0.15, 0.85)) * math.tau / n
            f = rng.uniform(0.2, 0.7)
            fx, fy = bx + math.cos(a) * bw * f, by + math.sin(a) * bh * f
            ti, tj = math.floor(fx) - x0, math.floor(fy) - y0
            ok = all(rows[tj + dj][ti + di] in (tiles.MUD, tiles.REEDS, tiles.LILY_PADS)
                     for dj in (-1, 0, 1) for di in (-1, 0, 1))
            if ok:
                spots.append((math.floor(fx) + 0.5, math.floor(fy) + 0.5))
                break
        else:                                   # no dry spot: clear one
            fx, fy = bx + math.cos(s * math.tau / n) * bw * 0.4, by + math.sin(s * math.tau / n) * bh * 0.4
            ti, tj = math.floor(fx) - x0, math.floor(fy) - y0
            for dj in (-1, 0, 1):
                for di in (-1, 0, 1):
                    rows[tj + dj][ti + di] = tiles.MUD
            spots.append((math.floor(fx) + 0.5, math.floor(fy) + 0.5))

    return Landmark("frog_camp", "camp", biome, "FROG HUNTER", x0, y0, rows,
                    cx=npc_tx + 0.5, cy=npc_ty + 0.5, npc=(npc_tx + 0.5, npc_ty + 0.5),
                    spots=spots)


# --- Froggy's pond ---------------------------------------------------------------------


def _pond_lair(layout, quest, rng: random.Random) -> Landmark | None:
    biome = quest.biome
    a, b = config.LAIR_RADII
    t = config.LAIR_WALL
    margin = config.LAIR_MARGIN
    mid_r = (layout.plains_radius + layout.radius) / 2
    radii = [mid_r * f for f in (1.0, 0.92, 1.08, 0.85, 1.15, 0.78, 1.22)]
    site = _find_site(layout, biome, radii, a + t + margin, b + t + margin, rng)
    if site is None:
        return None
    cx, cy = site
    W, H = 2 * (a + t + margin) + 1, 2 * (b + t + margin) + 1
    x0, y0 = cx - (a + t + margin), cy - (b + t + margin)
    rows = [[None] * W for _ in range(H)]
    xs = (np.arange(x0, x0 + W) + 0.5 - cx)[None, :]
    ys = (np.arange(y0, y0 + H) + 0.5 - cy)[:, None]
    inner = (xs / a) ** 2 + (ys / b) ** 2
    outer = (xs / (a + t)) ** 2 + (ys / (b + t)) ** 2
    for j in range(H):
        for i in range(W):
            if inner[j, i] < 1.0:
                rows[j][i] = tiles.MUD
            elif outer[j, i] < 1.0:
                rows[j][i] = tiles.LAIR_STONE

    # The gate: the stones' gap facing the island's centre, and a mud
    # causeway out through the margin.
    g = math.atan2(-cy / b, -cx / a)            # (the oval's parameter angle)
    gx, gy = math.cos(g), math.sin(g)
    gate = []
    half_gap = config.LAIR_GATE_WIDTH / 2
    # Unit direction along the oval's edge at the gate, and out of it.
    tx_, ty_ = -a * gy, b * gx
    tn = math.hypot(tx_, ty_)
    tx_, ty_ = tx_ / tn, ty_ / tn
    nx_, ny_ = gx / a, gy / b
    nn = math.hypot(nx_, ny_)
    nx_, ny_ = nx_ / nn, ny_ / nn
    ex, ey = gx * a, gy * b                      # the gate's middle, on the inner edge
    for j in range(H):
        for i in range(W):
            px, py = i + x0 + 0.5 - cx - ex, j + y0 + 0.5 - cy - ey
            along = px * tx_ + py * ty_
            out = px * nx_ + py * ny_
            if abs(along) <= half_gap and -1.0 <= out <= t + margin:
                if rows[j][i] is tiles.LAIR_STONE:
                    gate.append((i + x0, j + y0))
                rows[j][i] = tiles.MUD

    # Pools: one in the middle (the boss sleeps there), the others spread
    # in two staggered rows across the oval.
    pools = [(0.0, 0.0, 12.0, 5.0)]
    for k in range(config.LAIR_POOLS - 1):
        fx = -0.78 + 1.56 * k / max(1, config.LAIR_POOLS - 2)
        fy = (0.42 if k % 2 else -0.42) + rng.uniform(-0.08, 0.08)
        pools.append((fx * a + rng.uniform(-6, 6), fy * b, rng.uniform(8, 11), rng.uniform(3.5, 5)))
    for px, py, rx, ry in pools:
        for j in range(math.floor(py - ry - 2), math.ceil(py + ry + 2) + 1):
            for i in range(math.floor(px - rx - 2), math.ceil(px + rx + 2) + 1):
                ii, jj = cx + i - x0, cy + j - y0
                if not (0 <= jj < H and 0 <= ii < W) or rows[jj][ii] is not tiles.MUD:
                    continue
                e = ((i + 0.5 - px) / rx) ** 2 + ((j + 0.5 - py) / ry) ** 2
                if e < 1.0:
                    rows[jj][ii] = tiles.POND
                elif e < 1.6 and rng.random() < 0.55:
                    rows[jj][ii] = tiles.LILY_PADS

    # Pillars: 2 x 1 tile blocks of standing stone, spread over the floor
    # (rejection sampling: clear of pools, the gate path, and each other).
    pillars: list[tuple[float, float]] = []
    tries = 0
    while len(pillars) < config.LAIR_PILLARS and tries < 4000:
        tries += 1
        u, v = rng.uniform(-0.88, 0.88), rng.uniform(-0.85, 0.85)
        if u * u + v * v > 0.8:
            continue
        px, py = u * a, v * b
        if any(((px - qx) / (qrx + 5)) ** 2 + ((py - qy) / (qry + 4)) ** 2 < 1.0
               for qx, qy, qrx, qry in pools):
            continue
        if math.hypot(px - ex, py - ey) < 18:
            continue
        if any(math.hypot((px - ox) / 2.2, py - oy) < 7 for ox, oy in pillars):
            continue
        pillars.append((px, py))
        for di in (0, 1, 2, 3):
            for dj in (0, 1):
                ii, jj = cx + math.floor(px) + di - x0, cy + math.floor(py) + dj - y0
                if rows[jj][ii] is tiles.MUD:
                    rows[jj][ii] = tiles.LAIR_STONE

    # Reeds scattered over the open mud (looks only: they don't block).
    for j in range(H):
        for i in range(W):
            if rows[j][i] is tiles.MUD and inner[j, i] < 0.97 and rng.random() < 0.035:
                rows[j][i] = tiles.REEDS

    spots = [(cx + px, cy + py) for px, py, _, _ in pools]
    return Landmark("pond_lair", "lair", biome, "FROGGY'S POND", x0, y0, rows,
                    cx=cx, cy=cy, spots=spots, gate=gate, radii=(float(a), float(b)))


BUILDERS = {"frog_camp": _frog_camp, "pond_lair": _pond_lair}
