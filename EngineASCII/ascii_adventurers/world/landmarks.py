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

Two layouts in a style per biome (CAMP_STYLES, LAIR_STYLES), and the
caravanserai (M23.2: _caravanserai, Ol' Spitter's walled yard with
troughs, arcades and posts; it shares the arena's oval and gate,
_arena_shell) and the sunken observatory (M23.3: _observatory, the
Nameless Magus's, with a star chart, rings of columns and a fallen
telescope), and the reactor vault (M24.1: _reactor_vault, the Fallout
King's, with a reactor ring, valves, showers, lead walls and grates), and
the frozen throne hall (M24.2: _throne_hall, the Snow King's, with his
throne, ice pillars, fire braziers and frozen statues), and the ruined
ballroom (M24.3: _ballroom, Fragile's, with shuttered windows and levers,
coffins, marble pillars and chandeliers), and the withered glade (M25.1:
_glade, Nettle's, in bramble, with a hollow tree, a ring of giant
toadstools, growcaps and stumps). The swamp's (the desert's, M23.1, are the same shapes in
sand: a nomad tent by an oasis, and the Dung Pit -- sandstone walls,
taller pillars, sand pits for pools):
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
    props: dict = field(default_factory=dict)  # a lair's named fixtures (M24.1: the vault's
                                               # valves, showers, lead walls, grates)

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
    "caravan": {tiles.STALL: tiles.CRATES},       # M23.2: the caravan master's crates
    "apprentice": {tiles.STALL: tiles.SCROLLS},   # M23.3: the apprentice's scroll racks
    "frost": {tiles.SLUDGE: tiles.FROZEN_POND, tiles.RUBBLE: tiles.SNOWDRIFT},   # M24.2
    "pawn": {tiles.CRATES: tiles.STALL},          # M24.3: the pawn dealer's wares
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
    # (the plains boss's necropolis first: it has a fixed place, the centre)
    order = sorted(quests, key=lambda kq: kq[1].kind != "finale")
    for which in ("lair", "camp"):
        for key, q in order:
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
        for k, (x, y) in enumerate(camp.spots):
            spot = _clearing(q.biome, x, y, centre=SPOT_CENTRE.get(q.kind))
            spot.quest = key
            out.append(spot)
            if q.kind == "destroy":
                # (first in the list: stamped under everything else, so a
                # trail never cuts into a camp or a lair)
                trail = _nut_trail(q.biome, x, y, random.Random(hash_coords(layout.seed, 0x7A11, k)))
                trail.quest = key
                out.insert(0, trail)
    return out


def quest_marks(layout, quest: str) -> tuple[Landmark | None, Landmark | None]:
    """(camp, lair) built for config.QUESTS[quest]."""
    camp = next((m for m in layout.landmarks if m.quest == quest and m.kind == "camp"), None)
    lair = next((m for m in layout.landmarks if m.quest == quest and m.kind == "lair"), None)
    return camp, lair


def spot_count(quest) -> int:
    """How many target spots a quest gets (P2: QUEST_SPOT_FACTOR x its count)."""
    return quest.count * config.QUEST_SPOT_FACTOR


def _scatter(layout, quest, camp, marks, others, rng: random.Random) -> list[tuple[float, float]]:
    """Where a quest's targets live: quest.count * QUEST_SPOT_FACTOR spots
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
    # (numpy from here on: P2's 4x targets made the plain loops ~1 s.)
    c = np.asarray(cands, dtype=np.float64)
    keep = _fits_many(layout, biome_id, cands, e, e)
    keep &= np.hypot(c[:, 0] - camp.cx, c[:, 1] - camp.cy) >= config.QUEST_SPOT_CAMP_GAP
    for m in marks:
        if m.kind != "spot":
            keep &= ~((m.x0 - e <= c[:, 0]) & (c[:, 0] < m.x0 + m.w + e)
                      & (m.y0 - e <= c[:, 1]) & (c[:, 1] < m.y0 + m.h + e))
    if others:
        o = np.asarray(others, dtype=np.float64)
        near = np.hypot(c[:, None, 0] - o[None, :, 0], c[:, None, 1] - o[None, :, 1])
        keep &= (near >= config.QUEST_SPOT_OTHERS).all(axis=1)
    c = c[keep]
    want = spot_count(quest)
    sep = config.QUEST_SPOT_SEPARATION
    while True:
        taken: list[int] = []
        room = np.ones(len(c), dtype=bool)          # not taken, and `sep` from every one taken
        while len(taken) < want:
            free = np.flatnonzero(room)
            if not free.size:
                break
            i = int(free[0])                        # the first in order that has room
            taken.append(i)
            room &= np.hypot(c[:, 0] - c[i, 0], c[:, 1] - c[i, 1]) >= sep
            room[i] = False
        if len(taken) == want or sep < 1:           # (sep < 1: no room at all, fewer)
            return [(float(c[i, 0]), float(c[i, 1])) for i in taken]
        sep *= 0.8


# The ground of a quest spot's clearing, per biome.
CLEARING = {"swamp": tiles.MUD, "desert": tiles.SAND, "ruins": tiles.CONCRETE,
            "forest": tiles.DEAD_LEAVES, "mushroom": tiles.MYCELIUM}
# What stands in the middle of a quest spot's clearing, per quest kind: a
# "light" quest's cold brazier (M22.2), a "collect" quest's bundle (M23.2).
SPOT_CENTRE = {"light": tiles.BRAZIER, "collect": tiles.CARGO, "survive": tiles.SEAL,
               "escort": tiles.BEACON_SITE, "rescue": tiles.ICE_BLOCK,
               "fetch": tiles.BEAR_PIECE, "cleanse": tiles.SHRINE, "destroy": tiles.NUT_CACHE,
               "fell": tiles.MARKED_TREE, "sever": tiles.MYC_NODE}


def _clearing(biome: str, x: float, y: float, centre: TileType | None = None) -> Landmark:
    """A small round patch of open ground at a quest target's spot, so it
    never wakes up stuck in a mangrove or a wall. Only the circle is laid
    (None round it), so it blends into the generated terrain. `centre`
    (a brazier, a cargo bundle) goes in the middle."""
    r = config.QUEST_SPOT_CLEARING
    tx, ty = math.floor(x), math.floor(y)
    ground = CLEARING.get(biome, tiles.MUD)
    rows = [[ground if (i - r) ** 2 + (j - r) ** 2 <= r * r + r else None
             for i in range(2 * r + 1)] for j in range(2 * r + 1)]
    if centre is not None:
        rows[r][r] = centre
    if centre is tiles.MYC_NODE:
        # A node's threads (M26): spores sprinkled round it (every Mycelium's
        # look the same; only what it spills, severed, differs).
        for j in range(2 * r + 1):
            for i in range(2 * r + 1):
                if rows[j][i] is ground and (i * 7 + j * 3) % 5 == 0 and (i, j) != (r, r):
                    rows[j][i] = tiles.SPORES
    if centre is tiles.SEAL or centre is tiles.SHRINE:
        # A star circle (M23.3) / a blighted shrine's ring of rot (M25.1),
        # as wide as the circle you stand in to break / cleanse it.
        ring = tiles.STAR_RING if centre is tiles.SEAL else tiles.ROT_RING
        for j in range(2 * r + 1):
            for i in range(2 * r + 1):
                d = math.hypot(i - r, (j - r) * 1.0)
                if abs(d - (r - 0.5)) < 0.55 and (i + j) % 2 == 0:
                    rows[j][i] = ring
    return Landmark("quest_spot", "spot", biome, "", tx - r, ty - r, rows, cx=x, cy=y)


def _nut_trail(biome: str, x: float, y: float, rng: random.Random) -> Landmark:
    """A "destroy" quest's trail of nut shells (M25.2): CACHE_TRAIL tiles
    long, wandering in to the cache at (x, y) from a random way, a shell
    on most of its tiles (only those are laid: it blends into the wood)."""
    n = rng.randint(*config.CACHE_TRAIL)
    a = rng.uniform(0, math.tau)
    px, py = x, y
    pts = []
    for k in range(n):
        a += rng.uniform(-0.35, 0.35)
        px, py = px + math.cos(a), py + math.sin(a) * 0.7
        if k > config.QUEST_SPOT_CLEARING and rng.random() < 0.75:
            pts.append((math.floor(px), math.floor(py)))
    xs = [p[0] for p in pts] or [math.floor(x)]
    ys = [p[1] for p in pts] or [math.floor(y)]
    x0, y0 = min(xs), min(ys)
    rows = [[None] * (max(xs) - x0 + 1) for _ in range(max(ys) - y0 + 1)]
    for tx, ty in pts:
        rows[ty - y0][tx - x0] = tiles.NUT_SHELLS
    return Landmark("nut_trail", "spot", biome, "", x0, y0, rows, cx=x, cy=y)


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
    # M24.1: the hazmat scavenger's camp in the ruins -- a sludge pit ringed
    # with rubble, a scrap shack on metal plates.
    "scrap_camp": dict(radii=config.CAMP_SCRAP_RADII, ground=tiles.CONCRETE, pool=tiles.SLUDGE,
                       pool_edge=tiles.RUBBLE, plants=tiles.RUBBLE, plant_min=0.66, core=0.3,
                       floor=tiles.PLATES, wall=tiles.SCRAP_WALL, post=tiles.SCRAP_POST,
                       rack=tiles.CRATES),
    # M25.1: the hedge witch's camp in the haunted forest -- a black pond in
    # the fog, her plank hut with herbs drying on racks.
    "witch_camp": dict(radii=config.CAMP_WITCH_RADII, ground=tiles.DEAD_LEAVES, pool=tiles.POND,
                       pool_edge=tiles.FOG, plants=tiles.BARK, plant_min=0.6, core=0.3,
                       floor=tiles.DECK, wall=tiles.PLANK_WALL, post=tiles.HUNTER_POST,
                       rack=tiles.DRYING_RACK),
    # M25.2: the forester's camp -- a log pond, his cabin, woodpiles.
    "forester_camp": dict(radii=config.CAMP_FORESTER_RADII, ground=tiles.DEAD_LEAVES,
                          pool=tiles.POND, pool_edge=tiles.BARK, plants=tiles.STUMP,
                          plant_min=0.66, core=0.3, floor=tiles.DECK, wall=tiles.PLANK_WALL,
                          post=tiles.HUNTER_POST, rack=tiles.WOODPILE),
    # M25.3: the lumberjack's camp -- a pond, his cabin, sawhorses.
    "lumber_camp": dict(radii=config.CAMP_LUMBER_RADII, ground=tiles.DEAD_LEAVES,
                        pool=tiles.POND, pool_edge=tiles.FELLED, plants=tiles.STUMP,
                        plant_min=0.6, core=0.3, floor=tiles.DECK, wall=tiles.PLANK_WALL,
                        post=tiles.HUNTER_POST, rack=tiles.SAWHORSE),
    # M26: a Mycelium quest giver's camp in the mushroom biome -- a pond in
    # the spores, giant mushrooms, a plank hut with drying racks.
    "spore_camp": dict(radii=config.CAMP_SPORE_RADII, ground=tiles.MYCELIUM, pool=tiles.POND,
                       pool_edge=tiles.SPORES, plants=tiles.GIANT_SHROOM, plant_min=0.64, core=0.3,
                       floor=tiles.DECK, wall=tiles.PLANK_WALL, post=tiles.HUNTER_POST,
                       rack=tiles.DRYING_RACK),
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


@dataclass
class _Shell:
    """An arena's oval and gate, before its insides (_arena_shell)."""

    rows: list
    x0: int
    y0: int
    cx: int
    cy: int
    inner: np.ndarray            # per tile: (x / a)^2 + (y / b)^2 (< 1: the floor)
    ex: float                    # the gate's middle on the inner edge (from the centre)
    ey: float
    gate: list

    @property
    def W(self) -> int:
        return len(self.rows[0])

    @property
    def H(self) -> int:
        return len(self.rows)

    def put(self, i: int, j: int, tile: TileType, over: TileType) -> bool:
        """Arena tile (i, j) (from the centre) becomes `tile` if it's
        `over` now; True if it did."""
        ii, jj = self.cx + i - self.x0, self.cy + j - self.y0
        if 0 <= jj < self.H and 0 <= ii < self.W and self.rows[jj][ii] is over:
            self.rows[jj][ii] = tile
            return True
        return False


def _arena_shell(layout, quest, rng: random.Random, avoid: list, floor: TileType,
                 wall: TileType, site: tuple[int, int] | None = None,
                 radii: tuple[int, int] | None = None,
                 gate_dir: float | None = None) -> _Shell | None:
    """A boss arena's shell: a random site in the quest's biome, an oval of
    `floor` LAIR_RADII tiles ringed by LAIR_WALL tiles of `wall`, and the
    gate -- a gap in the ring facing the island's centre, with a path of
    floor out through the LAIR_MARGIN clearing round it. (M27: `site`,
    `radii` and `gate_dir` -- the gate's parameter angle -- can be given.)"""
    biome = quest.biome
    a, b = radii or config.LAIR_RADII
    t = config.LAIR_WALL
    margin = config.LAIR_MARGIN
    if site is None:
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
                rows[j][i] = wall

    # The gate: the stones' gap facing the island's centre, and a mud
    # causeway out through the margin.
    g = math.atan2(-cy / b, -cx / a) if gate_dir is None else gate_dir   # (the oval's angle)
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
                if rows[j][i] is wall:
                    gate.append((i + x0, j + y0))
                rows[j][i] = floor
    return _Shell(rows, x0, y0, cx, cy, inner, ex, ey, gate)


def _lair(layout, quest, rng: random.Random, avoid: list, key: str) -> Landmark | None:
    st = LAIR_STYLES[key]
    floor = st["floor"]
    shell = _arena_shell(layout, quest, rng, avoid, floor, st["wall"])
    if shell is None:
        return None
    a, b = config.LAIR_RADII
    rows, x0, y0, cx, cy = shell.rows, shell.x0, shell.y0, shell.cx, shell.cy
    W, H, inner, ex, ey = shell.W, shell.H, shell.inner, shell.ex, shell.ey

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
    return Landmark(key, "lair", quest.biome, quest.lair_name or "LAIR", x0, y0, rows,
                    cx=cx, cy=cy, spots=spots, gate=shell.gate, radii=(float(a), float(b)),
                    floor=floor)


# --- The caravanserai (M23.2) -------------------------------------------------------------

# Where its troughs go, as fractions of the arena's radii: two either side
# of the middle yard, four out toward the ends (between the arcades).
_TROUGHS = ((-0.32, 0.0), (0.32, 0.0), (-0.56, -0.5), (0.56, -0.5), (-0.56, 0.5),
            (0.56, 0.5))
_ARCADE_ROWS = (-0.72, -0.3, 0.3, 0.72)        # the arcades' rows (fractions of b)
TROUGH_W = 6                                   # a trough: 6 x 1 tiles


def trough_tiles(x: float, y: float) -> list[tuple[int, int]]:
    """The tiles of the trough whose middle is (x, y) (a lair spot)."""
    tx0, ty = math.floor(x) - TROUGH_W // 2, math.floor(y)
    return [(tx0 + k, ty) for k in range(TROUGH_W)]


def _caravanserai(layout, quest, rng: random.Random, avoid: list) -> Landmark | None:
    """Ol' Spitter's lair: the arena's oval in mud brick round a flagstone
    yard. Inside: an open yard in the middle where he sleeps (`spots[0]`),
    with hay; CARAVAN_TROUGHS stone water troughs round it (`spots[1:]`
    are their middles; trough_tiles gives their tiles); CARAVAN_ARCADES
    rows of brick arches (3 x 2 tiles, CARAVAN_ARCHES to a row) across the
    yard for cover -- his loogies bounce off them; and tethering posts
    scattered about (rejection sampling, clear of everything else)."""
    floor = tiles.FLAGSTONE
    shell = _arena_shell(layout, quest, rng, avoid, floor, tiles.MUDBRICK)
    if shell is None:
        return None
    a, b = config.LAIR_RADII
    ex, ey = shell.ex, shell.ey
    put = shell.put

    def near_gate(px: float, py: float, r: float) -> bool:
        return math.hypot(px - ex, py - ey) < r

    # Troughs.
    troughs = []
    for fx, fy in _TROUGHS[:config.CARAVAN_TROUGHS]:
        px, py = round(fx * a + rng.uniform(-4, 4)), round(fy * b)
        if near_gate(px, py, 20):
            px = -px                                # (the gate side: across instead)
        troughs.append((px, py))
        for k in range(TROUGH_W):
            put(px - TROUGH_W // 2 + k, py, tiles.TROUGH, floor)

    # Arcades: rows of arches, evenly spaced along each row, leaving the
    # middle yard, the troughs and the gate path clear.
    arches = []
    for fy in _ARCADE_ROWS:
        py = round(fy * b)
        half = 0.78 * a * math.sqrt(max(0.0, 1 - fy * fy))
        n = config.CARAVAN_ARCHES
        for k in range(n):
            px = round(-half + 2 * half * (k + 0.5) / n)
            if abs(px) < 16 and abs(py) < 12:
                continue
            if near_gate(px, py, 16) or any(abs(px - tx) < 9 and abs(py - ty) < 4
                                            for tx, ty in troughs):
                continue
            arches.append((px, py))
            for di in range(3):
                for dj in range(2):
                    put(px - 1 + di, py + dj, tiles.ARCH, floor)

    # Tethering posts.
    posts: list[tuple[int, int]] = []
    tries = 0
    while len(posts) < config.CARAVAN_POSTS and tries < 4000:
        tries += 1
        u, v = rng.uniform(-0.9, 0.9), rng.uniform(-0.88, 0.88)
        if u * u + v * v > 0.82:
            continue
        px, py = round(u * a), round(v * b)
        if (abs(px) < 14 and abs(py) < 8) or near_gate(px, py, 18):
            continue
        if any(abs(px - tx) < TROUGH_W + 3 and abs(py - ty) < 5 for tx, ty in troughs):
            continue
        if any(abs(px - qx) < 5 and abs(py - qy) < 4 for qx, qy in arches):
            continue
        if any(math.hypot((px - qx) / 2.0, py - qy) < 5 for qx, qy in posts):
            continue
        if put(px, py, tiles.TETHER_POST, floor):
            posts.append((px, py))

    # Hay: heaped round the middle yard, and strewn about.
    for j in range(shell.H):
        for i in range(shell.W):
            if shell.rows[j][i] is not floor or shell.inner[j, i] >= 0.97:
                continue
            u, v = i + shell.x0 - shell.cx, j + shell.y0 - shell.cy
            ring = abs(math.hypot(u / 2.0, v) - 7.0) < 1.0
            if (ring and rng.random() < 0.5) or rng.random() < 0.02:
                shell.rows[j][i] = tiles.HAY

    cx, cy = shell.cx, shell.cy
    spots = [(cx + 0.5, cy + 0.5)] + [(cx + px + 0.0, cy + py + 0.5) for px, py in troughs]
    return Landmark("caravanserai", "lair", quest.biome, quest.lair_name or "LAIR", shell.x0,
                    shell.y0, shell.rows, cx=cx, cy=cy, spots=spots, gate=shell.gate,
                    radii=(float(a), float(b)), floor=floor)


# --- The sunken observatory (M23.3) -------------------------------------------------------


def _observatory(layout, quest, rng: random.Random, avoid: list) -> Landmark | None:
    """The Nameless Magus's lair: the arena's oval in blue-glazed stone round
    a floor of sandstone slabs. In the middle a round star chart (where he
    sleeps, `spots[0]`); round it, broken columns in OBSERVATORY_RINGS rings
    (2 x 2 tiles, a quarter of them fallen to rubble you can walk over) --
    cover from his sun lance; a fallen brass telescope lying across the
    floor; sand drifts. Open enough for his runes and dune walls."""
    floor = tiles.SLABS
    shell = _arena_shell(layout, quest, rng, avoid, floor, tiles.GLAZED)
    if shell is None:
        return None
    a, b = config.LAIR_RADII
    ex, ey = shell.ex, shell.ey
    put = shell.put
    r = config.OBSERVATORY_CHART / 2
    for j in range(-math.ceil(r), math.ceil(r) + 1):
        for i in range(-math.ceil(r), math.ceil(r) + 1):
            if math.hypot(i + 0.5, j + 0.5) <= r:
                put(i, j, tiles.STAR_CHART, floor)

    # The telescope: a brass tube lying across the floor, between the
    # first two rings of columns, its wide end two tiles thick.
    side = rng.choice((-1, 1))
    tx0, ty0 = round(side * rng.uniform(0.38, 0.5) * a), round(rng.uniform(-0.15, 0.15) * b)
    if math.hypot(tx0 - ex, ty0 - ey) < 24:
        tx0 = -tx0
    tilt = rng.uniform(-0.25, 0.25)
    for k in range(12):
        i, j = tx0 + k - 6, ty0 + round((k - 6) * tilt)
        put(i, j, tiles.BRASS, floor)
        if k >= 9:
            put(i, j + 1, tiles.BRASS, floor)

    # Columns in rings.
    for frac, n in config.OBSERVATORY_RINGS:
        turn = rng.uniform(0, math.tau)
        for k in range(n):
            t = turn + k * math.tau / n + rng.uniform(-0.08, 0.08)
            px, py = round(math.cos(t) * frac * a), round(math.sin(t) * frac * b)
            if math.hypot(px - ex, py - ey) < 16:
                continue
            fallen = rng.random() < 0.25
            for di in (0, 1):
                for dj in (0, 1):
                    put(px + di, py + dj, tiles.BROKEN_COLUMN if fallen else tiles.COLUMN, floor)

    # Sand drifts.
    for j in range(shell.H):
        for i in range(shell.W):
            if shell.rows[j][i] is floor and shell.inner[j, i] < 0.97 and rng.random() < 0.04:
                shell.rows[j][i] = tiles.DRIFT

    cx, cy = shell.cx, shell.cy
    return Landmark("observatory", "lair", quest.biome, quest.lair_name or "LAIR", shell.x0,
                    shell.y0, shell.rows, cx=cx, cy=cy, spots=[(cx + 0.5, cy + 0.5)],
                    gate=shell.gate, radii=(float(a), float(b)), floor=floor)


# --- The reactor vault (M24.1) ------------------------------------------------------------


def _reactor_vault(layout, quest, rng: random.Random, avoid: list) -> Landmark | None:
    """The Fallout King's lair: the arena's oval in concrete vault walls.
    In the middle a cracked reactor ring with four openings (he sleeps
    inside, `spots[0]`). Round the edge, 4 coolant valves (props["valves"])
    and 4 decontamination showers (props["showers"], 2 x 2 pads); through
    the room, 4 lead walls (4 x 2: cover from the meltdown, props["leads"])
    and 6 sewer grates (props["grates"]: he dives between them); then
    VAULT_PILLARS concrete pillars and VAULT_PIPES pipe runs, clear of
    all of it."""
    floor = tiles.CONCRETE
    shell = _arena_shell(layout, quest, rng, avoid, floor, tiles.VAULT_WALL)
    if shell is None:
        return None
    a, b = config.LAIR_RADII
    ex, ey = shell.ex, shell.ey
    put = shell.put

    def clear(i0: int, j0: int, w: int, h: int, pad: int = 1) -> bool:
        for j in range(j0 - pad, j0 + h + pad):
            for i in range(i0 - pad, i0 + w + pad):
                ii, jj = shell.cx + i - shell.x0, shell.cy + j - shell.y0
                if not (0 <= jj < shell.H and 0 <= ii < shell.W) or shell.rows[jj][ii] is not floor:
                    return False
        return True

    def block(i0: int, j0: int, w: int, h: int, tile: TileType) -> None:
        for j in range(j0, j0 + h):
            for i in range(i0, i0 + w):
                put(i, j, tile, floor)

    # The reactor: a ring with an opening each way.
    for j in range(-8, 9):
        for i in range(-10, 11):
            d = math.hypot(i / 1.25, j)
            if 5.5 <= d <= 7.0 and abs(i) > 2 and abs(j) > 1:
                put(i, j, tiles.REACTOR, floor)

    def round_spot(frac: float, angle: float) -> tuple[int, int]:
        x, y = math.cos(angle) * frac * a, math.sin(angle) * frac * b
        if math.hypot(x - ex, y - ey) < 22:          # (keep the gate clear)
            angle += 0.45
            x, y = math.cos(angle) * frac * a, math.sin(angle) * frac * b
        return round(x), round(y)

    props: dict = {"valves": [], "showers": [], "leads": [], "grates": []}
    turn = rng.uniform(0, math.tau)
    for k in range(4):
        i, j = round_spot(0.82, turn + math.pi / 4 + k * math.pi / 2)
        put(i, j, tiles.VALVE, floor)
        props["valves"].append((shell.cx + i + 0.5, shell.cy + j + 0.5))
        i, j = round_spot(0.86, turn + k * math.pi / 2)
        block(i, j, 2, 2, tiles.SHOWER)
        props["showers"].append((shell.cx + i + 1.0, shell.cy + j + 1.0))
    for k in range(4):
        for _ in range(60):
            t = turn + math.pi / 4 + k * math.pi / 2 + rng.uniform(-0.3, 0.3)
            frac = rng.uniform(0.38, 0.55)
            i, j = round(math.cos(t) * frac * a) - 2, round(math.sin(t) * frac * b) - 1
            if clear(i, j, 4, 2, 2):
                block(i, j, 4, 2, tiles.LEAD)
                props["leads"].append((shell.cx + i + 2.0, shell.cy + j + 1.0))
                break
    tries = 0
    while len(props["grates"]) < 6 and tries < 2000:
        tries += 1
        u, v = rng.uniform(-0.8, 0.8), rng.uniform(-0.8, 0.8)
        if not 0.1 < u * u + v * v < 0.62:
            continue
        i, j = round(u * a), round(v * b)
        if math.hypot(i - ex, j - ey) < 16 or not clear(i, j, 2, 1, 2):
            continue
        if any(math.hypot(gx - shell.cx - i, gy - shell.cy - j) < 30 for gx, gy in props["grates"]):
            continue
        block(i, j, 2, 1, tiles.GRATE)
        props["grates"].append((shell.cx + i + 1.0, shell.cy + j + 0.5))

    # Pillars and pipe runs, clear of everything above.
    placed = tries = 0
    while placed < config.VAULT_PILLARS and tries < 4000:
        tries += 1
        u, v = rng.uniform(-0.9, 0.9), rng.uniform(-0.88, 0.88)
        if u * u + v * v > 0.8:
            continue
        i, j = round(u * a), round(v * b)
        if math.hypot(i - ex, j - ey) < 16 or math.hypot(i / 1.25, j) < 10:
            continue
        if clear(i, j, 2, 2, 3):
            block(i, j, 2, 2, tiles.CONC_PILLAR)
            placed += 1
    placed = tries = 0
    while placed < config.VAULT_PIPES and tries < 2000:
        tries += 1
        n = rng.randint(8, 14)
        i, j = round(rng.uniform(-0.75, 0.75) * a), round(rng.uniform(-0.7, 0.7) * b)
        if math.hypot(i - ex, j - ey) < 18 or math.hypot(i / 1.25, j) < 12:
            continue
        if clear(i, j, n, 1, 2):
            block(i, j, n, 1, tiles.PIPE)
            placed += 1

    # Rubble about.
    for j in range(shell.H):
        for i in range(shell.W):
            if shell.rows[j][i] is floor and shell.inner[j, i] < 0.97 and rng.random() < 0.03:
                shell.rows[j][i] = tiles.RUBBLE

    cx, cy = shell.cx, shell.cy
    return Landmark("reactor_vault", "lair", quest.biome, quest.lair_name or "LAIR", shell.x0,
                    shell.y0, shell.rows, cx=cx, cy=cy, spots=[(cx + 0.5, cy + 0.5)],
                    gate=shell.gate, radii=(float(a), float(b)), floor=floor, props=props)


# --- The frozen throne hall (M24.2) -------------------------------------------------------


def _throne_hall(layout, quest, rng: random.Random, avoid: list) -> Landmark | None:
    """The Snow King's lair: the arena's oval in ice walls round frost-stone.
    His ice throne at the far end from the gate (he sleeps before it,
    `spots[0]`); HALL_PILLAR_ROWS rows of 2 x 2 ice pillars (props
    ["pillars"]: their top-left tiles -- he regrows the shattered ones);
    4 fire braziers (props["braziers"]) spread round the hall; HALL_STATUES
    frozen statues; snowdrifts."""
    floor = tiles.FROST_STONE
    shell = _arena_shell(layout, quest, rng, avoid, floor, tiles.ICE_WALL)
    if shell is None:
        return None
    a, b = config.LAIR_RADII
    ex, ey = shell.ex, shell.ey
    put = shell.put

    def clear(i0: int, j0: int, w: int, h: int, pad: int = 1) -> bool:
        for j in range(j0 - pad, j0 + h + pad):
            for i in range(i0 - pad, i0 + w + pad):
                ii, jj = shell.cx + i - shell.x0, shell.cy + j - shell.y0
                if not (0 <= jj < shell.H and 0 <= ii < shell.W) or shell.rows[jj][ii] is not floor:
                    return False
        return True

    def block(i0: int, j0: int, w: int, h: int, tile: TileType) -> None:
        for j in range(j0, j0 + h):
            for i in range(i0, i0 + w):
                put(i, j, tile, floor)

    # The throne: across the hall from the gate.
    gl = math.hypot(ex, ey) or 1.0
    tx, ty = round(-ex / gl * a * 0.62), round(-ey / gl * b * 0.62)
    block(tx - 3, ty - 1, 7, 3, tiles.THRONE)
    sx, sy = tx + ex / gl * 5.0, ty + ey / gl * 4.0          # where he sleeps: before it

    props: dict = {"pillars": [], "braziers": []}
    for frac, n in config.HALL_PILLAR_ROWS:
        py = round(frac * b)
        half = 0.75 * a * math.sqrt(max(0.0, 1 - frac * frac))
        for k in range(n):
            px = round(-half + 2 * half * (k + 0.5) / n)
            if math.hypot(px - ex, py - ey) < 18 or math.hypot(px - tx, py - ty) < 12 \
                    or math.hypot(px - sx, py - sy) < 8:
                continue
            if clear(px, py, 2, 2, 1):
                block(px, py, 2, 2, tiles.ICE_PILLAR)
                props["pillars"].append((shell.cx + px, shell.cy + py))
    turn = rng.uniform(0, math.tau)
    for k in range(4):
        for _ in range(40):
            t = turn + k * math.pi / 2 + rng.uniform(-0.3, 0.3)
            frac = rng.uniform(0.45, 0.7)
            i, j = round(math.cos(t) * frac * a), round(math.sin(t) * frac * b)
            if math.hypot(i - ex, j - ey) > 18 and clear(i, j, 1, 1, 2):
                put(i, j, tiles.FIRE_BOWL, floor)
                props["braziers"].append((shell.cx + i + 0.5, shell.cy + j + 0.5))
                break
    placed = tries = 0
    while placed < config.HALL_STATUES and tries < 2000:
        tries += 1
        u, v = rng.uniform(-0.85, 0.85), rng.uniform(-0.85, 0.85)
        if u * u + v * v > 0.75:
            continue
        i, j = round(u * a), round(v * b)
        if math.hypot(i - ex, j - ey) < 18 or math.hypot(i - sx, j - sy) < 10:
            continue
        if clear(i, j, 1, 1, 3):
            put(i, j, tiles.STATUE, floor)
            placed += 1
    for j in range(shell.H):
        for i in range(shell.W):
            if shell.rows[j][i] is floor and shell.inner[j, i] < 0.97 and rng.random() < 0.035:
                shell.rows[j][i] = tiles.SNOWDRIFT

    cx, cy = shell.cx, shell.cy
    return Landmark("throne_hall", "lair", quest.biome, quest.lair_name or "LAIR", shell.x0,
                    shell.y0, shell.rows, cx=cx, cy=cy, spots=[(cx + sx + 0.5, cy + sy + 0.5)],
                    gate=shell.gate, radii=(float(a), float(b)), floor=floor, props=props)


# --- The ruined ballroom (M24.3) ----------------------------------------------------------


def _ballroom(layout, quest, rng: random.Random, avoid: list) -> Landmark | None:
    """Fragile's lair: the arena's oval in castle stone round a parquet
    floor. BALLROOM_WINDOWS shuttered windows along each long wall (the top
    and bottom of the oval: 2-tile slots in the stone, props["windows"]:
    (x, y, inward x, inward y) -- the shaft of sun falls in along it) with
    a lever below each (props["levers"]); her velvet throne at the far end
    from the gate (she sleeps before it, `spots[0]`) with coffins behind
    it (props["coffins"]); BALLROOM_PILLARS rows of marble pillars;
    chandeliers (props["chandeliers"]: where they hang); cracked mirrors."""
    floor = tiles.PARQUET
    shell = _arena_shell(layout, quest, rng, avoid, floor, tiles.CASTLE_WALL)
    if shell is None:
        return None
    a, b = config.LAIR_RADII
    ex, ey = shell.ex, shell.ey
    put = shell.put
    cx, cy = shell.cx, shell.cy

    def clear(i0: int, j0: int, w: int, h: int, pad: int = 1) -> bool:
        for j in range(j0 - pad, j0 + h + pad):
            for i in range(i0 - pad, i0 + w + pad):
                ii, jj = cx + i - shell.x0, cy + j - shell.y0
                if not (0 <= jj < shell.H and 0 <= ii < shell.W) or shell.rows[jj][ii] is not floor:
                    return False
        return True

    def set_at(i: int, j: int, tile: TileType) -> None:
        ii, jj = cx + i - shell.x0, cy + j - shell.y0
        if 0 <= jj < shell.H and 0 <= ii < shell.W:
            shell.rows[jj][ii] = tile

    props: dict = {"windows": [], "levers": [], "coffins": [], "chandeliers": []}
    n = config.BALLROOM_WINDOWS
    for side in (-1, 1):                         # top wall, bottom wall
        for k in range(n):
            fx = -0.55 + 1.1 * (k + 0.5) / n
            i = round(fx * a)
            j_edge = side * b * math.sqrt(max(0.0, 1 - fx * fx))
            if math.hypot(i - ex, j_edge - ey) < 20:
                continue
            # The window: two wall tiles just outside the floor's edge.
            j = round(j_edge) + (0 if side < 0 else -1)
            wy = j - side
            for di in (0, 1):
                set_at(i + di, wy, tiles.SHUTTER)
            slant = config.SHAFT_SLANT * (1 if k % 2 else -1)
            dx, dy = math.sin(slant), -side * math.cos(slant)
            props["windows"].append((cx + i + 1.0, cy + wy + 0.5, dx, dy))
            lj = j - side * 2
            put(i, lj, tiles.LEVER, floor)
            props["levers"].append((cx + i + 0.5, cy + lj + 0.5))

    # The throne and the coffins: across the hall from the gate.
    gl = math.hypot(ex, ey) or 1.0
    ux, uy = -ex / gl, -ey / gl
    tx, ty = round(ux * a * 0.72), round(uy * b * 0.72)
    for di in range(-2, 3):
        for dj in range(0, 2):
            put(tx + di, ty + dj, tiles.VELVET_THRONE, floor)
    for k in range(config.BALLROOM_COFFINS):
        off = (k - (config.BALLROOM_COFFINS - 1) / 2) * 5
        ci, cj = round(tx + ux * 7 - uy * off), round(ty + uy * 4 + ux * off)
        if clear(ci, cj, 1, 1, 0):
            put(ci, cj, tiles.COFFIN, floor)
            props["coffins"].append((cx + ci + 0.5, cy + cj + 0.5))
    sx, sy = tx - ux * 5.0, ty - uy * 4.0

    # Marble pillars, mirrors, chandeliers.
    for frac, cnt in config.BALLROOM_PILLARS:
        py = round(frac * b)
        half = 0.72 * a * math.sqrt(max(0.0, 1 - frac * frac))
        for k in range(cnt):
            px = round(-half + 2 * half * (k + 0.5) / cnt)
            if math.hypot(px - ex, py - ey) < 18 or math.hypot(px - tx, py - ty) < 12:
                continue
            if clear(px, py, 2, 2, 1):
                for di in (0, 1):
                    for dj in (0, 1):
                        put(px + di, py + dj, tiles.MARBLE, floor)
    placed = tries = 0
    while placed < 8 and tries < 1000:
        tries += 1
        t = rng.uniform(0, math.tau)
        i, j = round(math.cos(t) * (a - 2)), round(math.sin(t) * (b - 2))
        if math.hypot(i - ex, j - ey) > 20 and clear(i, j, 1, 1, 1):
            put(i, j, tiles.MIRROR, floor)
            placed += 1
    for k in range(config.BALLROOM_CHANDELIERS):
        fx = -0.6 + 1.2 * (k + 0.5) / config.BALLROOM_CHANDELIERS
        props["chandeliers"].append((cx + fx * a + rng.uniform(-4, 4), cy + rng.uniform(-6, 6)))

    return Landmark("ballroom", "lair", quest.biome, quest.lair_name or "LAIR", shell.x0,
                    shell.y0, shell.rows, cx=cx, cy=cy, spots=[(cx + sx + 0.5, cy + sy + 0.5)],
                    gate=shell.gate, radii=(float(a), float(b)), floor=floor, props=props)


# --- The withered glade (M25.1) -------------------------------------------------------------


def _glade(layout, quest, rng: random.Random, avoid: list) -> Landmark | None:
    """Nettle's lair: the arena's oval in bramble round dead leaves and
    fog. A dead hollow tree in the middle (GLADE_TREE); GLADE_TOADSTOOLS
    giant toadstools (2 x 1, cover) in a ring GLADE_RING of the way out;
    GLADE_GROWCAPS growcaps spread further out (props["growcaps"]); stumps
    (breakable cover) over the floor. She waits in front of the tree, on
    the gate's side (`spots[0]`)."""
    floor = tiles.DEAD_LEAVES
    shell = _arena_shell(layout, quest, rng, avoid, floor, tiles.BRAMBLE_WALL)
    if shell is None:
        return None
    a, b = config.LAIR_RADII
    ex, ey = shell.ex, shell.ey
    put = shell.put
    cx, cy = shell.cx, shell.cy

    # Fog over the floor where a slow noise is high (looks only).
    xs = (np.arange(shell.x0, shell.x0 + shell.W) + 0.5)[None, :]
    ys = (np.arange(shell.y0, shell.y0 + shell.H) + 0.5)[:, None]
    fog = fbm(layout.seed, _SALT_REEDS + 7, xs, ys, 9.0, 2)
    for j in range(shell.H):
        for i in range(shell.W):
            if shell.rows[j][i] is floor and shell.inner[j, i] < 0.97 and fog[j, i] > 0.6:
                shell.rows[j][i] = tiles.FOG

    def free(i0: int, j0: int, w: int, h: int, pad: int = 1) -> bool:
        for j in range(j0 - pad, j0 + h + pad):
            for i in range(i0 - pad, i0 + w + pad):
                ii, jj = cx + i - shell.x0, cy + j - shell.y0
                if not (0 <= jj < shell.H and 0 <= ii < shell.W) or \
                        shell.rows[jj][ii] not in (floor, tiles.FOG):
                    return False
        return True

    def lay(i: int, j: int, tile: TileType) -> None:
        put(i, j, tile, floor) or put(i, j, tile, tiles.FOG)

    # The dead hollow tree in the middle.
    tw, th = config.GLADE_TREE
    for dj in range(th):
        for di in range(tw):
            lay(di - tw // 2, dj - th // 2, tiles.HOLLOW_TREE)
    # The ring of giant toadstools.
    n = config.GLADE_TOADSTOOLS
    for k in range(n):
        t = (k + 0.5) / n * math.tau
        i, j = round(math.cos(t) * a * config.GLADE_RING), round(math.sin(t) * b * config.GLADE_RING)
        if math.hypot(i - ex * config.GLADE_RING, j - ey * config.GLADE_RING) < 6 or \
                not free(i, j, 2, 1, 0):
            continue
        for di in (0, 1):
            lay(i + di, j, tiles.TOADSTOOL)
    # Growcaps, spread round the outer part of the floor.
    props: dict = {"growcaps": []}
    m = config.GLADE_GROWCAPS
    for k in range(m):
        for _ in range(40):
            t = (k + rng.uniform(0.2, 0.8)) / m * math.tau
            f = rng.uniform(0.66, 0.82)
            i, j = round(math.cos(t) * a * f), round(math.sin(t) * b * f)
            if math.hypot(i - ex, j - ey) > 16 and free(i, j, 1, 1, 1):
                lay(i, j, tiles.GROWCAP)
                props["growcaps"].append((cx + i + 0.5, cy + j + 0.5))
                break
    # Stumps over the floor.
    placed = tries = 0
    while placed < config.GLADE_STUMPS and tries < 2000:
        tries += 1
        u, v = rng.uniform(-0.9, 0.9), rng.uniform(-0.9, 0.9)
        if u * u + v * v > 0.85 or abs(u * u + v * v - config.GLADE_RING ** 2) < 0.03:
            continue
        i, j = round(u * a), round(v * b)
        if math.hypot(i - ex, j - ey) > 18 and math.hypot(i, j * 2.5) > 12 and free(i, j, 1, 1, 1):
            lay(i, j, tiles.STUMP)
            placed += 1

    # She waits in front of the tree, toward the gate.
    gl = math.hypot(ex, ey) or 1.0
    sx, sy = ex / gl * 12.0, ey / gl * 5.0
    return Landmark("glade", "lair", quest.biome, quest.lair_name or "LAIR", shell.x0,
                    shell.y0, shell.rows, cx=cx, cy=cy, spots=[(cx + sx + 0.5, cy + sy + 0.5)],
                    gate=shell.gate, radii=(float(a), float(b)), floor=floor, props=props)


def _hollow_oak(layout, quest, rng: random.Random, avoid: list) -> Landmark | None:
    """Love & Cuddles' lair (M25.2): the arena's oval in a wall of oak roots
    round dead leaves and a little fog. The great hollow oak in the middle
    (OAK_HOLLOW); OAK_TREES big climbing oaks (2 x 2 trunks with a crown of
    leaves round each) spread over a ring OAK_RING of the way out
    (props["trees"]: each trunk's middle), none near the gate; stumps for
    cover. It waits in front of the hollow oak, toward the gate."""
    floor = tiles.DEAD_LEAVES
    shell = _arena_shell(layout, quest, rng, avoid, floor, tiles.OAK_ROOTS)
    if shell is None:
        return None
    a, b = config.LAIR_RADII
    ex, ey = shell.ex, shell.ey
    put = shell.put
    cx, cy = shell.cx, shell.cy

    xs = (np.arange(shell.x0, shell.x0 + shell.W) + 0.5)[None, :]
    ys = (np.arange(shell.y0, shell.y0 + shell.H) + 0.5)[:, None]
    fog = fbm(layout.seed, _SALT_REEDS + 11, xs, ys, 9.0, 2)
    for j in range(shell.H):
        for i in range(shell.W):
            if shell.rows[j][i] is floor and shell.inner[j, i] < 0.97 and fog[j, i] > 0.66:
                shell.rows[j][i] = tiles.FOG

    def free(i0: int, j0: int, w: int, h: int, pad: int = 1) -> bool:
        for j in range(j0 - pad, j0 + h + pad):
            for i in range(i0 - pad, i0 + w + pad):
                ii, jj = cx + i - shell.x0, cy + j - shell.y0
                if not (0 <= jj < shell.H and 0 <= ii < shell.W) or \
                        shell.rows[jj][ii] not in (floor, tiles.FOG):
                    return False
        return True

    def lay(i: int, j: int, tile: TileType) -> None:
        put(i, j, tile, floor) or put(i, j, tile, tiles.FOG)

    def crown(i0: int, j0: int, ru: float, rv: float) -> None:
        """Leaves on the ground round a trunk whose top-left is (i0, j0)."""
        for j in range(math.floor(-rv) - 1, math.ceil(rv) + 2):
            for i in range(math.floor(-ru) - 1, math.ceil(ru) + 2):
                if (i / ru) ** 2 + (j / rv) ** 2 <= 1.0:
                    lay(i0 + i, j0 + j, tiles.OAK_CROWN)

    # The great hollow oak.
    tw, th = config.OAK_HOLLOW
    for dj in range(th):
        for di in range(tw):
            lay(di - tw // 2, dj - th // 2, tiles.HOLLOW_TREE)
    crown(0, 0, tw * 0.9, th * 0.9)
    # The climbing oaks: spread round the ring by angle, each at its own
    # distance out.
    props: dict = {"trees": [], "oak": (cx + 0.5, cy + 0.5)}
    n = config.OAK_TREES
    lo, hi = config.OAK_RING
    for k in range(n):
        for _ in range(40):
            t = (k + rng.uniform(0.25, 0.75)) / n * math.tau
            f = rng.uniform(lo, hi)
            i, j = round(math.cos(t) * a * f), round(math.sin(t) * b * f)
            if math.hypot(i - ex, j - ey) > config.OAK_GATE_GAP and free(i - 3, j - 2, 8, 6, 0):
                for dj in (0, 1):
                    for di in (0, 1):
                        lay(i + di, j + dj, tiles.OAK_TRUNK)
                crown(i, j, 3.6, 2.2)
                props["trees"].append((cx + i + 1.0, cy + j + 1.0))
                break
    # Stumps over the floor.
    placed = tries = 0
    while placed < config.OAK_STUMPS and tries < 2000:
        tries += 1
        u, v = rng.uniform(-0.9, 0.9), rng.uniform(-0.9, 0.9)
        if u * u + v * v > 0.85:
            continue
        i, j = round(u * a), round(v * b)
        if math.hypot(i - ex, j - ey) > 18 and math.hypot(i, j * 2.5) > 12 and free(i, j, 1, 1, 1):
            lay(i, j, tiles.STUMP)
            placed += 1

    gl = math.hypot(ex, ey) or 1.0
    sx, sy = ex / gl * 12.0, ey / gl * 5.0
    return Landmark("hollow_oak", "lair", quest.biome, quest.lair_name or "LAIR", shell.x0,
                    shell.y0, shell.rows, cx=cx, cy=cy, spots=[(cx + sx + 0.5, cy + sy + 0.5)],
                    gate=shell.gate, radii=(float(a), float(b)), floor=floor, props=props)


def _still_grove(layout, quest, rng: random.Random, avoid: list) -> Landmark | None:
    """The Fallen's lair (M25.3): the arena's oval in a thicket round dead
    leaves and fog. A great fallen trunk across the middle (GROVE_LOG long,
    2 high: cover); GROVE_TREES lookalike trees, at least GROVE_TREE_GAP
    apart, none near the gate (props["trees"]: where each stands -- the
    figure is painted there, its trunk tile 2 below); GROVE_FIRES fire bowls
    (props["fires"]); stumps. It waits beside the fallen trunk, toward the
    gate."""
    floor = tiles.DEAD_LEAVES
    shell = _arena_shell(layout, quest, rng, avoid, floor, tiles.THICKET)
    if shell is None:
        return None
    a, b = config.LAIR_RADII
    ex, ey = shell.ex, shell.ey
    put = shell.put
    cx, cy = shell.cx, shell.cy

    xs = (np.arange(shell.x0, shell.x0 + shell.W) + 0.5)[None, :]
    ys = (np.arange(shell.y0, shell.y0 + shell.H) + 0.5)[:, None]
    fog = fbm(layout.seed, _SALT_REEDS + 13, xs, ys, 9.0, 2)
    for j in range(shell.H):
        for i in range(shell.W):
            if shell.rows[j][i] is floor and shell.inner[j, i] < 0.97 and fog[j, i] > 0.62:
                shell.rows[j][i] = tiles.FOG

    def free(i0: int, j0: int, w: int, h: int, pad: int = 1) -> bool:
        for j in range(j0 - pad, j0 + h + pad):
            for i in range(i0 - pad, i0 + w + pad):
                ii, jj = cx + i - shell.x0, cy + j - shell.y0
                if not (0 <= jj < shell.H and 0 <= ii < shell.W) or \
                        shell.rows[jj][ii] not in (floor, tiles.FOG):
                    return False
        return True

    def lay(i: int, j: int, tile: TileType) -> None:
        put(i, j, tile, floor) or put(i, j, tile, tiles.FOG)

    # The great fallen trunk, a little askew.
    n = config.GROVE_LOG
    for k in range(n):
        i = k - n // 2
        j = round(k * 0.12) - 1
        lay(i, j, tiles.FALLEN_TRUNK)
        lay(i, j + 1, tiles.FALLEN_TRUNK)
    props: dict = {"trees": [], "fires": []}
    # Fire bowls, spread round by angle.
    m = config.GROVE_FIRES
    for k in range(m):
        for _ in range(40):
            t = (k + rng.uniform(0.2, 0.8)) / m * math.tau
            f = rng.uniform(0.35, 0.75)
            i, j = round(math.cos(t) * a * f), round(math.sin(t) * b * f)
            if math.hypot(i - ex, j - ey) > 14 and free(i, j, 1, 1, 2):
                lay(i, j, tiles.GROVE_FIRE)
                props["fires"].append((cx + i + 0.5, cy + j + 0.5))
                break
    # The lookalike trees: each needs room for its figure (5 x 6 tiles round
    # its trunk) and keeps GROVE_TREE_GAP from the others.
    gap = config.GROVE_TREE_GAP
    tries = 0
    while len(props["trees"]) < config.GROVE_TREES and tries < 4000:
        tries += 1
        u, v = rng.uniform(-0.92, 0.92), rng.uniform(-0.92, 0.92)
        if u * u + v * v > 0.8:
            continue
        i, j = round(u * a), round(v * b)            # (its trunk tile)
        x, y = cx + i + 0.5, cy + j - 2 + 0.5
        if math.hypot(i - ex, j - ey) < config.OAK_GATE_GAP or not free(i - 2, j - 4, 5, 5, 0):
            continue
        if any(math.hypot(x - tx, y - ty) < gap for tx, ty in props["trees"]):
            continue
        if any(math.hypot(x - fx, y - fy) < 5.0 for fx, fy in props["fires"]):
            continue
        lay(i, j, tiles.GROVE_TRUNK)
        props["trees"].append((x, y))
    # Stumps over the floor.
    placed = tries = 0
    while placed < config.GROVE_STUMPS and tries < 2000:
        tries += 1
        u, v = rng.uniform(-0.9, 0.9), rng.uniform(-0.9, 0.9)
        if u * u + v * v > 0.85:
            continue
        i, j = round(u * a), round(v * b)
        if math.hypot(i - ex, j - ey) > 18 and free(i, j, 1, 1, 2) and \
                all(math.hypot(cx + i - tx, cy + j - ty) > 4 for tx, ty in props["trees"]):
            lay(i, j, tiles.STUMP)
            placed += 1

    gl = math.hypot(ex, ey) or 1.0
    sx, sy = ex / gl * 16.0, ey / gl * 6.0
    return Landmark("still_grove", "lair", quest.biome, quest.lair_name or "LAIR", shell.x0,
                    shell.y0, shell.rows, cx=cx, cy=cy, spots=[(cx + sx + 0.5, cy + sy + 0.5)],
                    gate=shell.gate, radii=(float(a), float(b)), floor=floor, props=props)


def _amanita_ring(layout, quest, rng: random.Random, avoid: list) -> Landmark | None:
    """Mycelium the fly agaric's lair (M26.1): the arena's oval in a wall of
    giant mushrooms round bare mycelium. NET_RINGS fruiting rings -- a node
    (solid, breakable) in a ring of little red mushrooms -- the middle one
    and the rest round it NET_RING of the way out, joined by threads
    (props["rings"], props["threads"]); AMANITA_SHROOMS giant mushrooms for
    cover, off the threads. It waits toward the gate."""
    from ..systems.patterns import point_segment_distance
    floor = tiles.MYCELIUM
    shell = _arena_shell(layout, quest, rng, avoid, floor, tiles.SHROOM_WALL)
    if shell is None:
        return None
    a, b = config.LAIR_RADII
    ex, ey = shell.ex, shell.ey
    put = shell.put
    cx, cy = shell.cx, shell.cy

    def lay(i: int, j: int, tile: TileType) -> None:
        put(i, j, tile, floor) or put(i, j, tile, tiles.RING_SHROOMS)

    # The rings: the middle, then the rest round it (pulled in if one
    # would sit by the gate).
    spots = [(0, 0)]
    n = config.NET_RINGS - 1
    turn = rng.uniform(0, math.tau)
    for k in range(n):
        t = turn + k * math.tau / n
        for f in (config.NET_RING, config.NET_RING * 0.75, config.NET_RING * 0.5):
            i, j = round(math.cos(t) * a * f), round(math.sin(t) * b * f)
            if math.hypot(i - ex, j - ey) > 18:
                break
        spots.append((i, j))
    for i, j in spots:
        for dj in range(-3, 4):
            for di in range(-5, 6):
                if abs(math.hypot(di / 1.7, dj) - 2.6) < 0.6:
                    put(i + di, j + dj, tiles.RING_SHROOMS, floor)
        put(i, j, tiles.NET_NODE, floor) or put(i, j, tiles.NET_NODE, tiles.RING_SHROOMS)
    rings = [(cx + i + 0.5, cy + j + 0.5) for i, j in spots]
    threads = [(0, k) for k in range(1, len(rings))] + \
        [(k, k % n + 1) for k in range(1, len(rings))]
    # Giant mushrooms: cover, off the threads and the rings.
    placed = tries = 0
    while placed < config.AMANITA_SHROOMS and tries < 3000:
        tries += 1
        u, v = rng.uniform(-0.9, 0.9), rng.uniform(-0.9, 0.9)
        if u * u + v * v > 0.85:
            continue
        i, j = round(u * a), round(v * b)
        x, y = cx + i + 0.5, cy + j + 0.5
        if math.hypot(i - ex, j - ey) < 18 or any(math.hypot(x - rx, y - ry) < 6
                                                  for rx, ry in rings):
            continue
        if any(point_segment_distance(x, y, *rings[p], *rings[q]) < 3 for p, q in threads):
            continue
        ii, jj = cx + i - shell.x0, cy + j - shell.y0
        if all(shell.rows[jj + dj][ii + di] is floor for dj in (-1, 0, 1) for di in (-1, 0, 1, 2)):
            lay(i, j, tiles.GIANT_SHROOM)
            lay(i + 1, j, tiles.GIANT_SHROOM)
            placed += 1

    gl = math.hypot(ex, ey) or 1.0
    sx, sy = ex / gl * 20.0, ey / gl * 8.0
    return Landmark("amanita_ring", "lair", quest.biome, quest.lair_name or "LAIR", shell.x0,
                    shell.y0, shell.rows, cx=cx, cy=cy, spots=[(cx + sx + 0.5, cy + sy + 0.5)],
                    gate=shell.gate, radii=(float(a), float(b)), floor=floor,
                    props={"rings": rings, "threads": threads})


def _inkcap_ring(layout, quest, rng: random.Random, avoid: list) -> Landmark | None:
    """Mycelium the shaggy ink cap's lair (M26.2): the arena's oval in a wall
    of giant mushrooms round mycelium, with patches of old cracked paving
    (ink caps push up through stone) and ink stains where a noise is high;
    INKCAP_SHROOMS giant mushrooms (2 wide) for cover. It waits toward the
    gate."""
    floor = tiles.MYCELIUM
    shell = _arena_shell(layout, quest, rng, avoid, floor, tiles.SHROOM_WALL)
    if shell is None:
        return None
    a, b = config.LAIR_RADII
    ex, ey = shell.ex, shell.ey
    cx, cy = shell.cx, shell.cy
    xs = (np.arange(shell.x0, shell.x0 + shell.W) + 0.5)[None, :]
    ys = (np.arange(shell.y0, shell.y0 + shell.H) + 0.5)[:, None]
    pave = fbm(layout.seed, _SALT_REEDS + 17, xs, ys, 14.0, 2)
    ink = fbm(layout.seed, _SALT_REEDS + 19, xs, ys, 6.0, 2)
    for j in range(shell.H):
        for i in range(shell.W):
            if shell.rows[j][i] is not floor or shell.inner[j, i] >= 0.97:
                continue
            if pave[j, i] > 0.6:
                shell.rows[j][i] = tiles.OLD_PAVING
            elif ink[j, i] > 0.72:
                shell.rows[j][i] = tiles.INK_STAIN
    placed = tries = 0
    while placed < config.INKCAP_SHROOMS and tries < 3000:
        tries += 1
        u, v = rng.uniform(-0.9, 0.9), rng.uniform(-0.9, 0.9)
        if u * u + v * v > 0.85:
            continue
        i, j = round(u * a), round(v * b)
        if math.hypot(i - ex, j - ey) < 18 or math.hypot(i, j * 2.5) < 14:
            continue
        ii, jj = cx + i - shell.x0, cy + j - shell.y0
        if all(shell.rows[jj + dj][ii + di] in (floor, tiles.OLD_PAVING, tiles.INK_STAIN)
               for dj in (-1, 0, 1) for di in (-1, 0, 1, 2)):
            shell.rows[jj][ii] = tiles.GIANT_SHROOM
            shell.rows[jj][ii + 1] = tiles.GIANT_SHROOM
            placed += 1
    gl = math.hypot(ex, ey) or 1.0
    sx, sy = ex / gl * 20.0, ey / gl * 8.0
    return Landmark("inkcap_ring", "lair", quest.biome, quest.lair_name or "LAIR", shell.x0,
                    shell.y0, shell.rows, cx=cx, cy=cy, spots=[(cx + sx + 0.5, cy + sy + 0.5)],
                    gate=shell.gate, radii=(float(a), float(b)), floor=floor, props={})


def _puffball_field(layout, quest, rng: random.Random, avoid: list) -> Landmark | None:
    """Mycelium the giant puffball's lair (M26.3): the arena's oval in a wall
    of giant mushrooms round mycelium with drifts of spore dust;
    PUFF_BOULDERS clusters of boulders (cover from its wind and its bursts)
    and PUFF_SHROOMS giant mushrooms. It waits toward the gate."""
    floor = tiles.MYCELIUM
    shell = _arena_shell(layout, quest, rng, avoid, floor, tiles.SHROOM_WALL)
    if shell is None:
        return None
    a, b = config.LAIR_RADII
    ex, ey = shell.ex, shell.ey
    cx, cy = shell.cx, shell.cy
    xs = (np.arange(shell.x0, shell.x0 + shell.W) + 0.5)[None, :]
    ys = (np.arange(shell.y0, shell.y0 + shell.H) + 0.5)[:, None]
    dust = fbm(layout.seed, _SALT_REEDS + 23, xs, ys, 10.0, 2)
    for j in range(shell.H):
        for i in range(shell.W):
            if shell.rows[j][i] is floor and shell.inner[j, i] < 0.97 and dust[j, i] > 0.62:
                shell.rows[j][i] = tiles.SPORE_DUST

    def free(i0: int, j0: int, w: int, h: int, pad: int = 1) -> bool:
        for j in range(j0 - pad, j0 + h + pad):
            for i in range(i0 - pad, i0 + w + pad):
                ii, jj = cx + i - shell.x0, cy + j - shell.y0
                if not (0 <= jj < shell.H and 0 <= ii < shell.W) or \
                        shell.rows[jj][ii] not in (floor, tiles.SPORE_DUST):
                    return False
        return True

    def lay(i: int, j: int, tile: TileType) -> None:
        ii, jj = cx + i - shell.x0, cy + j - shell.y0
        shell.rows[jj][ii] = tile

    # Boulder clusters: a lumpy 3-4 x 2 block each.
    placed = tries = 0
    while placed < config.PUFF_BOULDERS and tries < 3000:
        tries += 1
        u, v = rng.uniform(-0.85, 0.85), rng.uniform(-0.85, 0.85)
        if u * u + v * v > 0.75:
            continue
        i, j = round(u * a), round(v * b)
        w = rng.choice((3, 4))
        if math.hypot(i - ex, j - ey) < 20 or math.hypot(i, j * 2.5) < 14 or \
                not free(i, j, w, 2, 3):
            continue
        for dj in range(2):
            for di in range(w):
                if (di, dj) not in ((0, 1), (w - 1, 0)) or rng.random() < 0.5:
                    lay(i + di, j + dj, tiles.ROCK)
        placed += 1
    placed = tries = 0
    while placed < config.PUFF_SHROOMS and tries < 2000:
        tries += 1
        u, v = rng.uniform(-0.85, 0.85), rng.uniform(-0.85, 0.85)
        if u * u + v * v > 0.8:
            continue
        i, j = round(u * a), round(v * b)
        if math.hypot(i - ex, j - ey) < 18 or not free(i, j, 2, 1, 2):
            continue
        lay(i, j, tiles.GIANT_SHROOM)
        lay(i + 1, j, tiles.GIANT_SHROOM)
        placed += 1
    gl = math.hypot(ex, ey) or 1.0
    sx, sy = ex / gl * 20.0, ey / gl * 8.0
    return Landmark("puffball_field", "lair", quest.biome, quest.lair_name or "LAIR", shell.x0,
                    shell.y0, shell.rows, cx=cx, cy=cy, spots=[(cx + sx + 0.5, cy + sy + 0.5)],
                    gate=shell.gate, radii=(float(a), float(b)), floor=floor, props={})


def _necropolis(layout, quest, rng: random.Random, avoid: list) -> Landmark | None:
    """More than Life's necropolis (M27): at the island's centre, NECRO_RADII
    (twice a ring lair), walled in crypt stone, its gate to the south --
    sealed with bone until the guardians fall (Quests opens it). Grave soil
    and bone litter; rows of gravestones (cover: props["graves"]),
    mausoleums, a ritual ring in the middle where he waits, and old corpses
    lying about (props["corpses"])."""
    floor = tiles.GRAVE_SOIL
    a, b = config.NECRO_RADII
    shell = _arena_shell(layout, quest, rng, avoid, floor, tiles.CRYPT_WALL, site=(0, 0),
                         radii=(a, b), gate_dir=math.pi / 2)
    if shell is None:
        return None
    cx, cy = shell.cx, shell.cy
    ex, ey = shell.ex, shell.ey
    xs = (np.arange(shell.x0, shell.x0 + shell.W) + 0.5)[None, :]
    ys = (np.arange(shell.y0, shell.y0 + shell.H) + 0.5)[:, None]
    litter = fbm(layout.seed, _SALT_REEDS + 29, xs, ys, 8.0, 2)
    for j in range(shell.H):
        for i in range(shell.W):
            if shell.rows[j][i] is floor and shell.inner[j, i] < 0.97 and litter[j, i] > 0.72:
                shell.rows[j][i] = tiles.BONE_LITTER
    open_ = (floor, tiles.BONE_LITTER)

    def at(i: int, j: int):
        ii, jj = cx + i - shell.x0, cy + j - shell.y0
        if 0 <= jj < shell.H and 0 <= ii < shell.W:
            return shell.rows[jj][ii]
        return None

    def lay(i: int, j: int, tile: TileType) -> None:
        shell.rows[cy + j - shell.y0][cx + i - shell.x0] = tile

    def free(i0: int, j0: int, w: int, h: int, pad: int = 1) -> bool:
        return all(at(i, j) in open_ for j in range(j0 - pad, j0 + h + pad)
                   for i in range(i0 - pad, i0 + w + pad))

    # The ritual ring in the middle.
    for j in range(-6, 7):
        for i in range(-14, 15):
            if abs(math.hypot(i / 2.2, j) - 5.5) < 0.6:
                lay(i, j, tiles.RITUAL_RING)
    props: dict = {"graves": [], "corpses": []}
    # Mausoleums.
    placed = tries = 0
    while placed < config.NECRO_TOMBS and tries < 3000:
        tries += 1
        u, v = rng.uniform(-0.85, 0.85), rng.uniform(-0.85, 0.85)
        if u * u + v * v > 0.75:
            continue
        i, j = round(u * a), round(v * b)
        if math.hypot(i - ex, j - ey) < 30 or math.hypot(i / 2.2, j) < 14 or \
                not free(i, j, 5, 3, 3):
            continue
        for dj in range(3):
            for di in range(5):
                lay(i + di, j + dj, tiles.MAUSOLEUM)
        placed += 1
    # Rows of graves, a few tiles apart.
    placed = tries = 0
    while placed < config.NECRO_GRAVES and tries < 6000:
        tries += 1
        u, v = rng.uniform(-0.9, 0.9), rng.uniform(-0.9, 0.9)
        if u * u + v * v > 0.8:
            continue
        i, j = round(u * a), round(v * b)
        n = rng.randint(4, 7)
        step = rng.choice((3, 4))
        if math.hypot(i - ex, j - ey) < 24 or math.hypot(i / 2.2, j) < 10 or \
                not free(i, j, n * step, 1, 2):
            continue
        for k in range(n):
            lay(i + k * step, j, tiles.GRAVESTONE)
            props["graves"].append((cx + i + k * step + 0.5, cy + j + 0.5))
        placed += 1
    # Old corpses lying about (drawn; not tiles).
    tries = 0
    while len(props["corpses"]) < config.NECRO_CORPSES and tries < 3000:
        tries += 1
        u, v = rng.uniform(-0.85, 0.85), rng.uniform(-0.85, 0.85)
        if u * u + v * v > 0.7:
            continue
        i, j = round(u * a), round(v * b)
        if at(i, j) in open_ and math.hypot(i / 2.2, j) > 8:
            props["corpses"].append((cx + i + 0.5, cy + j + 0.5))
    # The gate, sealed with bone (Quests opens it once the guardians fall).
    for tx, ty in shell.gate:
        shell.rows[ty - shell.y0][tx - shell.x0] = tiles.SEALED_GATE
    return Landmark("necropolis", "lair", quest.biome, quest.lair_name or "LAIR", shell.x0,
                    shell.y0, shell.rows, cx=cx, cy=cy, spots=[(cx + 0.5, cy + 0.5)],
                    gate=shell.gate, radii=(float(a), float(b)), floor=floor, props=props)


BUILDERS = {key: (lambda layout, q, rng, avoid, key=key: _camp(layout, q, rng, avoid, key))
            for key in CAMP_STYLES}
BUILDERS.update({key: (lambda layout, q, rng, avoid, key=key: _lair(layout, q, rng, avoid, key))
                 for key in LAIR_STYLES})
BUILDERS["caravanserai"] = _caravanserai
BUILDERS["observatory"] = _observatory
BUILDERS["reactor_vault"] = _reactor_vault
BUILDERS["throne_hall"] = _throne_hall
BUILDERS["ballroom"] = _ballroom
BUILDERS["glade"] = _glade
BUILDERS["hollow_oak"] = _hollow_oak
BUILDERS["still_grove"] = _still_grove
BUILDERS["amanita_ring"] = _amanita_ring
BUILDERS["inkcap_ring"] = _inkcap_ring
BUILDERS["puffball_field"] = _puffball_field
BUILDERS["necropolis"] = _necropolis
BUILDERS["none"] = lambda layout, q, rng, avoid: None      # (M27: a quest with no camp)
