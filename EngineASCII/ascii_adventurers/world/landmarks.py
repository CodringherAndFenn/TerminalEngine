"""
world/landmarks.py -- fixed structures stamped into the island (M17).

A landmark is a rectangle of hand-placed tiles laid over whatever the biome
generated there: a quest giver's camp, a boss's lair. Every quest in
config.QUESTS is in every run (M22.5: all of a biome's bosses exist at
once). Each names a camp and a lair builder, its names on the map and a tile skin
(SKINS: the leech doctor's quest reuses the frog hunter's and the pond's
layouts in blood, the smoke keeper's gone stagnant); the run's landmarks
are placed once per seed (IslandLayout.landmarks, built on first use) and
every chunk that overlaps one has its tiles replaced by the generator
(world/generator.py), so they stream, persist and show on the maps like
any other terrain.

Placement is a pure function of the seed (M22.5): each lair, then each
camp, goes at a random spot anywhere in its biome's slice of the ring where
its whole footprint (plus a margin) lies inside that biome and it keeps
QUEST_SITE_GAP tiles from every landmark placed before it (_random_site).
So boss arenas and quest givers move from run to run. Then each quest's
target spots are scattered over the biome (_scatter), clear of all of them.

Two layouts so far, each in a style per biome (CAMP_STYLES, LAIR_STYLES);
the swamp's (the desert's, M23.1, are the same shapes in sand: a nomad
tent by an oasis, and the Dung Pit -- sandstone walls, taller pillars,
sand pits for pools):
  * the frog hunter's camp: a big bog (an oval of pools, reeds and lily
    pads, ringed by a walkable mud edge) with the hunter's hut on a deck
    at the edge facing the plains. He stands at his door. The quest's
    psychedelic frogs live at `spots`, scattered over the whole swamp
    (_scatter), each in a little mud clearing of its own.
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
    key: str                     # its builder ("frog_camp", "pond_lair", "quest_spot")
    kind: str                    # "camp" | "lair" | "spot" (a quest target's clearing)
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
    quest: str = ""              # the config.QUESTS key it was built for
    floor: TileType | None = None  # lairs: the arena's ground (the gate reopens to it)

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


def _fits_many(layout, biome_id: int, centres, hw: float, hh: float) -> np.ndarray:
    """_fits for many centres at once (one numpy call): a bool per centre."""
    nx, ny = max(3, int(hw / 8) + 2), max(3, int(hh / 8) + 2)
    gx = np.linspace(-hw, hw, nx)[None, None, :]
    gy = np.linspace(-hh, hh, ny)[None, :, None]
    c = np.asarray(centres, dtype=np.float64).reshape(-1, 2)
    xs = c[:, 0][:, None, None] + gx
    ys = c[:, 1][:, None, None] + gy
    return (layout.biome_ids(xs, ys, jitter=False) == biome_id).all(axis=(1, 2))


def _ring_radii(layout) -> tuple[float, float]:
    """The ring's inner and outer radius, safely clear of the plains'
    wobbly edge and the coast."""
    r0 = layout.plains_radius * (1 + config.PLAINS_EDGE_AMPLITUDE) + config.BORDER_WOBBLE
    r1 = layout.radius * (1 - config.COAST_AMPLITUDE)
    return r0, r1


def _random_site(layout, biome: str, hw: float, hh: float, rng: random.Random,
                 avoid: list) -> tuple[int, int] | None:
    """A random centre for a hw x hh (half-size) footprint anywhere in
    `biome`'s slice of the ring: the footprint lies inside the biome, and
    its rectangle keeps QUEST_SITE_GAP tiles from every landmark in `avoid`.
    QUEST_SITE_TRIES random points (uniform by area: r = sqrt of a uniform
    between the squared radii), tested in batches with one numpy call each;
    the first that fits wins. None: nowhere fits."""
    mid = _slice_angle(layout, biome)
    if mid is None:
        return None
    biome_id = biomes.BY_NAME[biome].id
    span = math.tau / len(layout.ring)
    r0, r1 = _ring_radii(layout)
    gap = config.QUEST_SITE_GAP

    def clear(x: float, y: float) -> bool:
        return all(abs(x - (m.x0 + m.w / 2)) >= hw + m.w / 2 + gap
                   or abs(y - (m.y0 + m.h / 2)) >= hh + m.h / 2 + gap for m in avoid)

    cands = []
    for _ in range(config.QUEST_SITE_TRIES):
        a = mid + rng.uniform(-0.5, 0.5) * span
        r = math.sqrt(rng.uniform(r0 * r0, r1 * r1))
        x, y = round(math.cos(a) * r), round(math.sin(a) * r)
        if clear(x, y):
            cands.append((x, y))
    for i in range(0, len(cands), 64):
        batch = cands[i:i + 64]
        ok = _fits_many(layout, biome_id, batch, hw, hh)
        if ok.any():
            return batch[int(np.argmax(ok))]
    return None


# Tile swaps that give a shared camp / lair layout a quest's own look.
SKINS = {
    "blood": {tiles.BOG: tiles.BLOOD_POOL, tiles.POND: tiles.BLOOD_POOL,
              tiles.LILY_PADS: tiles.CLOTS},
    "stagnant": {tiles.BOG: tiles.STAGNANT, tiles.POND: tiles.STAGNANT,
                 tiles.LILY_PADS: tiles.SCUM},
}


def _skin(mark: Landmark | None, skin: str) -> None:
    swap = SKINS.get(skin)
    if mark is None or not swap:
        return
    mark.rows = [[swap.get(t, t) for t in row] for row in mark.rows]


def build_landmarks(layout) -> list[Landmark]:
    """Every quest's camp and lair (M22.5: all of them, every run), plus a
    small clearing at each of its target spots (camp.spots). The big lairs
    are placed first (they're the hardest to fit), then the camps, then the
    spots; nothing overlaps."""
    out: list[Landmark] = []
    quests = list(config.QUESTS.items())
    rngs = {key: random.Random(hash_coords(layout.seed, 0x1A4D, i + 1))
            for i, (key, _) in enumerate(quests)}
    marks: dict[str, dict[str, Landmark | None]] = {}
    for which in ("lair", "camp"):
        for key, q in quests:
            mark = BUILDERS[getattr(q, which)](layout, q, rngs[key], out)
            if mark is not None:
                mark.quest = key
                _skin(mark, q.skin)
                out.append(mark)
            marks.setdefault(key, {})[which] = mark
    spots: list[tuple[float, float]] = []
    for key, q in quests:
        camp, lair = marks[key]["camp"], marks[key]["lair"]
        if camp is None:
            continue
        camp.spots = _scatter(layout, q, camp, out, spots, rngs[key])
        spots += camp.spots
        for x, y in camp.spots:
            spot = _clearing(q.biome, x, y, brazier=q.kind == "light")
            spot.quest = key
            out.append(spot)
    return out


def quest_marks(layout, quest: str) -> tuple[Landmark | None, Landmark | None]:
    """(camp, lair) built for config.QUESTS[quest]."""
    camp = next((m for m in layout.landmarks if m.quest == quest and m.kind == "camp"), None)
    lair = next((m for m in layout.landmarks if m.quest == quest and m.kind == "lair"), None)
    return camp, lair


def _scatter(layout, quest, camp, marks, others, rng: random.Random) -> list[tuple[float, float]]:
    """Where a quest's targets live: quest.count + QUEST_SPOT_EXTRA spots
    spread over the whole of its biome, so finding enough means travelling
    it (any `count` of them finish the hunt).

    QUEST_SPOT_CANDIDATES random points in the biome's slice of the ring
    (uniform by area: r = sqrt of a uniform between the squared radii) are
    kept if a QUEST_SPOT_EDGE-tile square round them is all that biome and
    they're QUEST_SPOT_CAMP_GAP tiles from the camp, clear of every camp
    and lair in `marks`, and QUEST_SPOT_OTHERS tiles from the other quests'
    spots (`others`).
    Then, in random order, a point is taken if it's at least `sep` tiles
    from every one already taken; `sep` starts at QUEST_SPOT_SEPARATION and
    shrinks until there are enough (a small or oddly-shaped biome)."""
    biome_id = biomes.BY_NAME[quest.biome].id
    mid = _slice_angle(layout, quest.biome)
    span = math.tau / len(layout.ring)
    r0, r1 = _ring_radii(layout)
    cands = []
    for _ in range(config.QUEST_SPOT_CANDIDATES):
        a = mid + rng.uniform(-0.5, 0.5) * span
        r = math.sqrt(rng.uniform(r0 * r0, r1 * r1))
        cands.append((math.floor(math.cos(a) * r) + 0.5, math.floor(math.sin(a) * r) + 0.5))
    e = config.QUEST_SPOT_EDGE
    ok = _fits_many(layout, biome_id, cands, e, e)
    cands = [c for c, good in zip(cands, ok) if good
             and math.hypot(c[0] - camp.cx, c[1] - camp.cy) >= config.QUEST_SPOT_CAMP_GAP
             and not any(m.contains(*c, e) for m in marks if m.kind != "spot")
             and all(math.hypot(c[0] - x, c[1] - y) >= config.QUEST_SPOT_OTHERS
                     for x, y in others)]
    sep = config.QUEST_SPOT_SEPARATION
    while True:
        spots = []
        for c in cands:
            if all(math.hypot(c[0] - x, c[1] - y) >= sep for x, y in spots):
                spots.append(c)
                if len(spots) == quest.count + config.QUEST_SPOT_EXTRA:
                    return spots
        if sep < 1:
            return spots                        # (no room at all: fewer targets)
        sep *= 0.8


# The ground of a quest spot's clearing, per biome.
CLEARING = {"swamp": tiles.MUD, "desert": tiles.SAND}


def _clearing(biome: str, x: float, y: float, brazier: bool = False) -> Landmark:
    """A small round patch of open ground at a quest target's spot, so it
    never wakes up stuck in a mangrove or a wall. Only the circle is laid
    (None round it), so it blends into the generated terrain. A "light"
    quest's (M22.2) has a cold brazier in the middle."""
    r = config.QUEST_SPOT_CLEARING
    tx, ty = math.floor(x), math.floor(y)
    ground = CLEARING.get(biome, tiles.MUD)
    rows = [[ground if (i - r) ** 2 + (j - r) ** 2 <= r * r + r else None
             for i in range(2 * r + 1)] for j in range(2 * r + 1)]
    if brazier:
        rows[r][r] = tiles.BRAZIER
    return Landmark("quest_spot", "spot", biome, "", tx - r, ty - r, rows, cx=x, cy=y)


# --- Camps: the frog hunter's bog, the scarab collector's oasis -------------------------

# A camp is an oval of water and plants with the giver's hut (or tent) on
# the side facing the island's centre. Its style says which tiles: "ground"
# (the walkable edge and floor), "pool" where the noise field is high or
# within `core` of the middle (an oasis is one round pond), "pool_edge"
# round it, "plants" where another noise is high, and the hut's "floor",
# "wall", "post" (under the giver) and "rack" (two props).
CAMP_STYLES = {
    "frog_camp": dict(radii=config.CAMP_BOG_RADII, ground=tiles.MUD, pool=tiles.BOG,
                      pool_edge=tiles.LILY_PADS, plants=tiles.REEDS, plant_min=0.62, core=0.0,
                      floor=tiles.DECK, wall=tiles.PLANK_WALL, post=tiles.HUNTER_POST,
                      rack=tiles.DRYING_RACK),
    "oasis_camp": dict(radii=config.CAMP_OASIS_RADII, ground=tiles.SAND, pool=tiles.OASIS,
                       pool_edge=tiles.SAND, plants=tiles.PALM, plant_min=0.7, core=0.35,
                       floor=tiles.RUG, wall=tiles.TENT, post=tiles.NOMAD_POST,
                       rack=tiles.STALL),
}


def _camp(layout, quest, rng: random.Random, avoid: list, key: str) -> Landmark | None:
    st = CAMP_STYLES[key]
    biome = quest.biome
    bw, bh = st["radii"]
    hut_w, hut_h = 20, 11                       # the deck the hut stands on
    reach_x = bw + hut_w + 4                    # the camp's half-size, whichever
    reach_y = bh + hut_h + 4                    # side of the bog the hut is on
    half = max(reach_x, reach_y)
    site = _random_site(layout, biome, half + 6, half + 6, rng, avoid)
    if site is None:
        return None
    bx, by = site

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
                rows[j][i] = st["ground"]
            elif e < st["core"] or pool[j, i] > config.CAMP_POOL_MIN:
                rows[j][i] = st["pool"]
            elif pool[j, i] > config.CAMP_POOL_MIN - 0.04:
                rows[j][i] = st["pool_edge"]
            elif reed[j, i] > st["plant_min"]:
                rows[j][i] = st["plants"]
            else:
                rows[j][i] = st["ground"]

    # The hut: a deck, a plank hut with a doorway toward the plains, two
    # drying racks, and the hunter at his door.
    dx0, dy0 = hx - hut_w // 2, hy - hut_h // 2
    for j in range(hut_h):
        for i in range(hut_w):
            rows[dy0 - y0 + j][dx0 - x0 + i] = st["floor"]
    wx0, wy0, ww, wh = dx0 + 5, dy0 + 2, 10, 6            # the hut's walls
    door = {"w": [(wx0, wy0 + 2), (wx0, wy0 + 3)], "e": [(wx0 + ww - 1, wy0 + 2),
                                                          (wx0 + ww - 1, wy0 + 3)],
            "n": [(wx0 + 4, wy0), (wx0 + 5, wy0)], "s": [(wx0 + 4, wy0 + wh - 1),
                                                         (wx0 + 5, wy0 + wh - 1)]}[side]
    for j in range(wh):
        for i in range(ww):
            if i in (0, ww - 1) or j in (0, wh - 1):
                if (wx0 + i, wy0 + j) not in door:
                    rows[wy0 + j - y0][wx0 + i - x0] = st["wall"]
    out_x = {"w": -2, "e": 2, "n": 0, "s": 0}[side]
    out_y = {"w": 0, "e": 0, "n": -2, "s": 2}[side]
    npc_tx, npc_ty = door[0][0] + out_x, door[0][1] + out_y
    rows[npc_ty - y0][npc_tx - x0] = st["post"]
    for rx, ry in ((dx0 + 1, dy0 + 1), (dx0 + hut_w - 2, dy0 + hut_h - 2)):
        rows[ry - y0][rx - x0] = st["rack"]

    return Landmark(key, "camp", biome, quest.camp_name or "CAMP", x0, y0, rows,
                    cx=npc_tx + 0.5, cy=npc_ty + 0.5, npc=(npc_tx + 0.5, npc_ty + 0.5))


# --- Lairs: Froggy's pond, the Dung Pit -------------------------------------------------

# A lair is an oval arena ringed by a "wall", its "floor" inside, with
# "pools" (`spots`: the middle one is where the boss sleeps) edged by
# "pool_edge" at random, `pillars` blocks of "pillar" (pillar_h tiles tall)
# for cover, and "decor" scattered over the floor (looks only).
LAIR_STYLES = {
    "pond_lair": dict(floor=tiles.MUD, wall=tiles.LAIR_STONE, pool=tiles.POND,
                      pool_edge=tiles.LILY_PADS, pillar=tiles.LAIR_STONE,
                      pillars=config.LAIR_PILLARS, pillar_h=2, decor=tiles.REEDS),
    "sand_lair": dict(floor=tiles.SAND, wall=tiles.SANDSTONE, pool=tiles.SAND_PIT,
                      pool_edge=tiles.DUNE, pillar=tiles.SANDSTONE,
                      pillars=config.SAND_LAIR_PILLARS, pillar_h=3, decor=tiles.DUNE),
}


def _lair(layout, quest, rng: random.Random, avoid: list, key: str) -> Landmark | None:
    st = LAIR_STYLES[key]
    floor = st["floor"]
    biome = quest.biome
    a, b = config.LAIR_RADII
    t = config.LAIR_WALL
    margin = config.LAIR_MARGIN
    site = _random_site(layout, biome, a + t + margin, b + t + margin, rng, avoid)
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
                rows[j][i] = floor
            elif outer[j, i] < 1.0:
                rows[j][i] = st["wall"]

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
                if rows[j][i] is st["wall"]:
                    gate.append((i + x0, j + y0))
                rows[j][i] = floor

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
                if not (0 <= jj < H and 0 <= ii < W) or rows[jj][ii] is not floor:
                    continue
                e = ((i + 0.5 - px) / rx) ** 2 + ((j + 0.5 - py) / ry) ** 2
                if e < 1.0:
                    rows[jj][ii] = st["pool"]
                elif e < 1.6 and rng.random() < 0.55:
                    rows[jj][ii] = st["pool_edge"]

    # Pillars: 2 x 1 tile blocks of standing stone, spread over the floor
    # (rejection sampling: clear of pools, the gate path, and each other).
    pillars: list[tuple[float, float]] = []
    tries = 0
    while len(pillars) < st["pillars"] and tries < 4000:
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
            for dj in range(st["pillar_h"]):
                ii, jj = cx + math.floor(px) + di - x0, cy + math.floor(py) + dj - y0
                if rows[jj][ii] is floor:
                    rows[jj][ii] = st["pillar"]

    # Decor scattered over the open floor (reeds, dunes: looks only, they
    # don't block).
    for j in range(H):
        for i in range(W):
            if rows[j][i] is floor and inner[j, i] < 0.97 and rng.random() < 0.035:
                rows[j][i] = st["decor"]

    spots = [(cx + px, cy + py) for px, py, _, _ in pools]
    return Landmark(key, "lair", biome, quest.lair_name or "LAIR", x0, y0, rows,
                    cx=cx, cy=cy, spots=spots, gate=gate, radii=(float(a), float(b)),
                    floor=floor)


BUILDERS = {key: (lambda layout, q, rng, avoid, key=key: _camp(layout, q, rng, avoid, key))
            for key in CAMP_STYLES}
BUILDERS.update({key: (lambda layout, q, rng, avoid, key=key: _lair(layout, q, rng, avoid, key))
                 for key in LAIR_STYLES})
