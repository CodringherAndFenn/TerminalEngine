"""
systems/pangaea.py -- the dangers of Pangaea's land (M31.1, design/OCEAN.md 24).

  * lava crust: a hero (or an enemy, not a boss) standing on a lava river's
    crust burns, PANGAEA_CRUST[0] every [1] s. The molten middle is solid
    (world/tiles.LAVA): nobody walks it;
  * tar: a hero who steps in sinks, slowed from x TAR[0] to x TAR[1] over
    TAR[2] s (a roll carries them out at full length: rolls ignore slows);
    an enemy in it runs at x TAR[3] (its whole clock: Statuses.tarred);
  * lava bombs: the volcano lobs a volley at a hero in the heart every
    LAVA_BOMB_EVERY[0] s (in the middle ring [1]; not on the shore ring, not
    in the caldera), each bomb marked where it will land, then a blast and
    a splash of burning rock (a zone, "lava_splash"). They hurt anyone.

M31.2, what the hunters leave on the ground (`Land`, one per world: `land`):
  * fire in the ferns: a fire-bearer's torch (or a lava bomb's splash)
    sets the ferns alight (`ignite`); each burning tile burns FIRE[0] s and
    spreads to the ferns round it (PANGAEA_FLAMMABLE: the chances), up to
    its blaze's size, then it's scorched for good. Standing in it burns
    (never the fire-bearer or the shaman). While a shaman lives, no fire
    within SHAMAN[9] tiles of it burns out;
  * stuck spears: a spear hunter's spear that lands on open ground sticks
    there SPEAR[3] s (a tile that stops you, not shots: `stick_spear`);
  * traps: a trapper's snares and pits, faintly marked (`lay_trap`); a
    hero who walks onto one is held (a pit also hurts); a roll carries you
    over. Beasts are caught too (the hunters hunt them).

M31.3: the steaming pools scald a hero standing in them (PANGAEA_SCALD);
breaking things (`breaks`, from world.broke): an egg hatches (NEST_HATCH:
hatchlings, and the first egg of a nest calls its parent), and breaking
into an amber outcrop frees what's in it once (AMBER_FREE: loot or a fight).

The land's damage scales like an enemy's (`hazard`). Nothing here echoes
(the echoes are the enemies': ai/pangaea.py). The scene keeps one
`Volcano` (its bombs in the air, each hero's next volley) and calls `step`
once a step, after the heroes have moved; render/pangaea.py draws the
bombs, the fires' flames and the traps.
"""

from __future__ import annotations

import math
import random

from .. import config
from ..entities.effects import Effect
from ..world import tiles
from ..world.rng import hash_coords

_SINK_EVERY = 0.15          # how long a step in tar keeps its slow on (s)


class Volcano:
    """The volcano's bombs in the air, and when each hero gets the next."""

    def __init__(self) -> None:
        self.bombs: list[list[float]] = []      # [x, y, left, total]
        self.next: dict[int, float] = {}        # player index -> s until their next volley


def _plan(scene):
    """Pangaea's plan, if this world has the zone (or None)."""
    layout = getattr(scene.world, "layout", None)
    z = layout.zone("pangaea") if layout is not None and hasattr(layout, "zone") else None
    if z is None:
        return None
    from ..world.zones import plan_of
    return plan_of(layout, z)


def _on_pangaea(scene, x: float, y: float) -> bool:
    biome_at = getattr(scene.world, "biome_at", None)
    return biome_at is not None and biome_at(math.floor(x), math.floor(y)).name == "pangaea"


def hazard(scene, base: float) -> float:
    """`base` damage from the land, as hard as an enemy woken here would hit:
    the players' level, the difficulty, the zone's toughness."""
    sp = getattr(scene, "spawner", None)
    if sp is None:
        return base
    level = max(1, min(config.MAX_LEVEL, sp.level + sp.level_bonus))
    mult = config.ENEMY_DAMAGE_MULTIPLIER * (1 + config.ENEMY_DAMAGE_PER_LEVEL * (level - 1))
    return base * mult * (1 + sp.damage_bonus) * sp.damage_mult * config.ZONE_TOUGH[1]


def step(scene, living, dt: float) -> None:
    """One step of the land's dangers for everyone on Pangaea."""
    world = scene.world
    broke = getattr(world, "broke", None)              # (M31.3: eggs hatch, amber frees)
    if broke:
        got = broke[:]
        broke.clear()
        breaks(scene, got)
    ground = getattr(world, "pangaea_land", None)      # (fires, spears, traps: wherever
    if ground is not None and ground.busy:             # Pangaea's enemies made them)
        ground.step(scene, [p.hero for p in living], dt)
    plan = _plan(scene)
    if plan is None:
        return
    vol = scene.volcano
    here = [p for p in living if _on_pangaea(scene, p.hero.x, p.hero.y)]
    for p in living:
        if p not in here:
            p.hero.tar_t = 0.0
    if not here and not vol.bombs:
        return
    for p in here:
        _underfoot(scene, p.hero, world.tile_at(math.floor(p.hero.x), math.floor(p.hero.y)), dt)
    if here:
        for e in scene.enemies:
            if e.alive and not getattr(e, "boss", False) and not getattr(e, "flies", False):
                _enemy_underfoot(scene, e, world.tile_at(math.floor(e.x), math.floor(e.y)), dt)
    _bombs(scene, plan, vol, here, dt)


def _underfoot(scene, h, tile, dt: float) -> None:
    from .combat import skims, strike
    if tile is tiles.TAR and not skims(h):
        h.tar_t = getattr(h, "tar_t", 0.0) + dt
        sink, deep, full = config.TAR[0], config.TAR[1], config.TAR[2]
        h.slowed(sink + (deep - sink) * min(1.0, h.tar_t / full), _SINK_EVERY)
    else:
        h.tar_t = 0.0
    if tile is tiles.LAVA_CRUST and not skims(h):
        h.crust_t = getattr(h, "crust_t", 0.0) - dt
        if h.crust_t <= 0:
            h.crust_t = config.PANGAEA_CRUST[1]
            strike(h, hazard(scene, config.PANGAEA_CRUST[0]), None, None, scene.effects)
    else:
        h.crust_t = 0.0
    if tile is tiles.HOT_SPRING:                       # (M31.3: the pools scald)
        h.scald_t = getattr(h, "scald_t", 0.0) - dt
        if h.scald_t <= 0:
            h.scald_t = config.PANGAEA_SCALD[1]
            strike(h, hazard(scene, config.PANGAEA_SCALD[0]), None, None, scene.effects)
    else:
        h.scald_t = 0.0


def _enemy_underfoot(scene, e, tile, dt: float) -> None:
    from .combat import strike
    from .statuses import statuses_of
    if tile is tiles.TAR:
        st = statuses_of(e)
        st.tarred = max(st.tarred, _SINK_EVERY)
    if tile is tiles.LAVA_CRUST:
        e.crust_t = getattr(e, "crust_t", 0.0) - dt
        if e.crust_t <= 0:
            e.crust_t = config.PANGAEA_CRUST[1]
            strike(e, hazard(scene, config.PANGAEA_CRUST[0]), None, None, scene.effects)
    else:
        e.crust_t = 0.0


def _bombs(scene, plan, vol: Volcano, here, dt: float) -> None:
    """Count down each hero's next volley (in the heart and the middle ring,
    out of the caldera), lob it, and land what's in the air."""
    from .combat import blast
    from .zones import Zone
    every_heart, every_mid, jitter = config.LAVA_BOMB_EVERY
    count, spread, marked, radius, damage, s_rad, s_life, s_dmg = config.LAVA_BOMB
    for p in here:
        h = p.hero
        if p.ghost or plan.in_caldera(h.x, h.y, plan.RIM + 2):
            continue
        if scene.steps % 10 == 0 or not hasattr(p, "pangaea_ring"):
            p.pangaea_ring = plan.ring_at(h.x, h.y)       # (the noise isn't free: now and then)
        ring = p.pangaea_ring
        if ring >= 2:
            vol.next.pop(p.index, None)                 # (none on the shore ring)
            continue
        base = every_heart if ring == 0 else every_mid
        if p.index not in vol.next:
            vol.next[p.index] = base + h.rng.uniform(-jitter, jitter)
        # (walked deeper in: the heart's shorter wait, at most)
        vol.next[p.index] = min(vol.next[p.index], base + jitter) - dt
        if vol.next[p.index] > 0:
            continue
        vol.next[p.index] = base + h.rng.uniform(-jitter, jitter)
        spots = [(h.x, h.y)]
        for _ in range(count - 1):
            a, d = h.rng.uniform(0, math.tau), h.rng.uniform(*spread)
            spots.append((h.x + math.cos(a) * d, h.y + math.sin(a) * d))
        for k, (x, y) in enumerate(spots):
            vol.bombs.append([x, y, marked + k * 0.18, marked + k * 0.18])
    landed = []
    for b in vol.bombs:
        b[2] -= dt
        if b[2] <= 0:
            landed.append(b)
    if not landed:
        return
    vol.bombs = [b for b in vol.bombs if b[2] > 0]
    actors = scene._actors()
    for x, y, _, _ in landed:
        blast(x, y, radius, hazard(scene, damage), None, actors, effects=scene.effects, ground=True)
        scene.effects.append(Effect("lava_burst", x, y, size=radius))
        scene.zones.append(Zone("lava_splash", x, y, s_rad, s_life, 0.5,
                                hazard(scene, s_dmg), None))
        scene._sounds.append("boulder")
        ignite(scene.world, x, y, config.FIRE[5])          # (M31.2: the ferns catch)


def ring_banner(scene, p, plan) -> None:
    """The first time a player walks into the middle ring or the heart, its
    age comes up as a banner (the shore ring's is the island's own arrival
    banner, systems/../scenes/game._zones_near)."""
    if scene.steps % 15:
        return
    h = p.hero
    ring = plan.ring_at(h.x, h.y)
    key = f"pangaea:{ring}"
    if key in scene.arrived:
        return
    scene.arrived.add(key)
    if ring < 2:
        from .quests import Banner
        title, sub = config.PANGAEA_AGES[ring]
        scene.quests.banner = Banner(title, sub)


# --- M31.2: what the hunters leave on the ground -----------------------------------------


_NEXT = ((1, 0), (-1, 0), (0, 1), (0, -1))


class Land:
    """Pangaea's ground at work: the fires in the ferns, the spears stuck in
    it, the trappers' traps (see the module's docstring)."""

    def __init__(self, seed: int = 0) -> None:
        self.fires: dict = {}        # (tx, ty) -> [s left, s to its next spread, blaze]
        self.blazes: dict = {}       # blaze -> tiles it may still light
        self.blaze_n = 0
        self.spears: dict = {}       # (tx, ty) -> [s left, the tile it stuck in]
        self.traps: list = []        # [x, y, "snare" | "pit", s left, who laid it (id)]
        self.rng = random.Random(seed ^ 0x5A17)
        self.burn_t: dict = {}       # id(actor) -> s to its next burn
        self.parents: set = set()    # (M31.3) the nests whose parent has been called
        self.opened: set = set()     # (M31.3) the amber outcrops already broken into

    @property
    def busy(self) -> bool:
        return bool(self.fires or self.spears or self.traps)

    # --- Fire -------------------------------------------------------------------------

    def light(self, world, tx: int, ty: int, blaze: int) -> bool:
        """Set one tile alight (if it burns and its blaze has room left)."""
        if (tx, ty) in self.fires or self.blazes.get(blaze, 0) <= 0:
            return False
        if world.tile_at(tx, ty).name not in config.PANGAEA_FLAMMABLE:
            return False
        world.set_tile(tx, ty, tiles.BURNING_FERNS)
        self.fires[(tx, ty)] = [config.FIRE[0], self.rng.uniform(0.3, 1.0) * config.FIRE[1], blaze]
        self.blazes[blaze] -= 1
        return True

    def _fires(self, world, heroes, keepers, dt: float) -> None:
        burn, every, _, _, far, _ = config.FIRE
        out, lit = [], []
        for (tx, ty), f in self.fires.items():
            x, y = tx + 0.5, ty + 0.5
            if not any(abs(h.x - x) < far and abs(h.y - y) < far for h in heroes):
                out.append((tx, ty))                      # (nobody near: it goes out)
                continue
            if not any(abs(kx - x) <= r and abs(ky - y) <= r and math.hypot(kx - x, ky - y) <= r
                       for kx, ky, r in keepers):
                f[0] -= dt                                # (a shaman near keeps it burning)
            if f[0] <= 0:
                out.append((tx, ty))
                continue
            f[1] -= dt
            if f[1] <= 0:
                f[1] += every
                for dx, dy in _NEXT:
                    name = world.tile_at(tx + dx, ty + dy).name
                    chance = config.PANGAEA_FLAMMABLE.get(name)
                    if chance and self.rng.random() < chance:
                        lit.append((tx + dx, ty + dy, f[2]))
        for key in out:
            del self.fires[key]
            world.set_tile(*key, tiles.SCORCHED)
        for tx, ty, blaze in lit:
            self.light(world, tx, ty, blaze)
        live = {f[2] for f in self.fires.values()}
        self.blazes = {b: n for b, n in self.blazes.items() if b in live}

    def _burn(self, scene, a, dt: float) -> None:
        """Anyone standing in a fire burns, FIRE[2] every FIRE[3] s."""
        from .combat import skims, strike
        key = id(a)
        tile = scene.world.tile_at(math.floor(a.x), math.floor(a.y))
        if tile is not tiles.BURNING_FERNS or skims(a):
            self.burn_t.pop(key, None)
            return
        left = self.burn_t.get(key, 0.0) - dt
        if left <= 0:
            left = config.FIRE[3]
            strike(a, hazard(scene, config.FIRE[2]), None, None, scene.effects)
        self.burn_t[key] = left

    # --- Spears and traps -------------------------------------------------------------

    def _spears(self, world, dt: float) -> None:
        done = []
        for key, s in self.spears.items():
            s[0] -= dt
            if s[0] <= 0:
                done.append(key)
        for key in done:
            _, old = self.spears.pop(key)
            if world.tile_at(*key) is tiles.STUCK_SPEAR:
                world.set_tile(*key, old)

    def _traps(self, scene, heroes, dt: float) -> None:
        from .combat import skims, strike
        from .statuses import statuses_of
        _, _, _, _, _, _, _, snare, pit, hurt = config.TRAPPER[:10]
        beasts = [e for e in scene.enemies
                  if e.alive and getattr(e, "beast", False) and not getattr(e, "flies", False)
                  and not getattr(e, "boss", False)]
        kept = []
        for t in self.traps:
            t[3] -= dt
            if t[3] <= 0:
                continue
            caught = None
            for h in heroes:
                if h.alive and not h.rolling and not skims(h) \
                        and math.hypot(h.x - t[0], h.y - t[1]) <= 0.45 + h.hit_radius * 0.5:
                    caught = h
                    break
            if caught is not None:
                hold = pit if t[2] == "pit" else snare
                caught.slowed(0.0, hold)
                if t[2] == "pit":
                    strike(caught, hazard(scene, hurt), None, None, scene.effects)
                scene.effects.append(Effect("toast", caught.x, caught.y - 1.5,
                                            label="IN A PIT!" if t[2] == "pit" else "SNARED!"))
                scene._sounds.append("hit")
                continue
            for e in beasts:
                reach = 0.45 + e.hit_radius * 0.5
                if abs(e.x - t[0]) <= reach and abs(e.y - t[1]) <= reach \
                        and math.hypot(e.x - t[0], e.y - t[1]) <= reach:
                    caught = e
                    break
            if caught is not None:                 # (the hunters' traps catch the beasts too)
                st = statuses_of(caught)
                st.rooted = max(st.rooted, (pit if t[2] == "pit" else snare) * 2)
                if t[2] == "pit":
                    strike(caught, hazard(scene, hurt), None, None, scene.effects)
                continue
            kept.append(t)
        self.traps = kept

    def step(self, scene, heroes, dt: float) -> None:
        world = scene.world
        if self.fires:
            r = config.SHAMAN[9]
            keepers = [(e.x, e.y, r) for e in scene.enemies
                       if e.alive and getattr(e, "kind_key", "") == "shaman"]
            self._fires(world, heroes, keepers, dt)
            if self.fires:                    # (only who's in the fires' box can be in one)
                xs = [k[0] for k in self.fires]
                ys = [k[1] for k in self.fires]
                x0, x1, y0, y1 = min(xs) - 1, max(xs) + 2, min(ys) - 1, max(ys) + 2
                for a in heroes + scene.enemies:
                    if not a.alive or not (x0 <= a.x <= x1 and y0 <= a.y <= y1) \
                            or getattr(a, "fire_proof", False) or getattr(a, "boss", False) \
                            or getattr(a, "flies", False):
                        self.burn_t.pop(id(a), None)
                        continue
                    self._burn(scene, a, dt)
            else:
                self.burn_t.clear()
        if self.spears:
            self._spears(world, dt)
        if self.traps:
            self._traps(scene, heroes, dt)


def land(world) -> Land:
    """This world's Land (made the first time it's asked for)."""
    got = getattr(world, "pangaea_land", None)
    if got is None:
        got = Land(getattr(world, "seed", 0))
        try:
            world.pangaea_land = got
        except AttributeError:
            pass
    return got


def ignite(world, x: float, y: float, size: int) -> int:
    """Set the ferns at (x, y) alight -- the tile and the ones round it --
    as a new blaze that may light `size` tiles in all. How many it lit."""
    if getattr(world, "set_tile", None) is None:
        return 0
    g = land(world)
    g.blaze_n += 1
    g.blazes[g.blaze_n] = size
    tx, ty = math.floor(x), math.floor(y)
    n = 0
    for dx, dy in ((0, 0),) + _NEXT:
        n += g.light(world, tx + dx, ty + dy, g.blaze_n)
    if not n:
        del g.blazes[g.blaze_n]
    return n


def stick_spear(world, x: float, y: float, actors) -> bool:
    """A spear that came down at (x, y) sticks in the ground there for
    SPEAR[3] s -- on open ground, clear of everyone (it never traps a body)."""
    if getattr(world, "set_tile", None) is None:
        return False
    tx, ty = math.floor(x), math.floor(y)
    g = land(world)
    old = world.tile_at(tx, ty)
    if old.solid or (tx, ty) in g.spears or (tx, ty) in g.fires or old is tiles.LAVA_CRUST:
        return False
    cx, cy = tx + 0.5, ty + 0.5
    if any(abs(a.x - cx) <= a.hit_radius + 0.75 and abs(a.y - cy) <= a.hit_radius + 0.75
           for a in actors if a.alive):
        return False
    world.set_tile(tx, ty, tiles.STUCK_SPEAR)
    g.spears[(tx, ty)] = [config.SPEAR[3], old]
    return True


def lay_trap(world, x: float, y: float, kind: str, who) -> None:
    """A snare or a pit at (x, y), laid by `who` (a trapper)."""
    land(world).traps.append([x, y, kind, config.TRAPPER[4], id(who)])


# --- M31.3: eggs and amber ------------------------------------------------------------------


def breaks(scene, broke) -> None:
    """What the world reported broken (world.broke): eggs hatch, amber
    frees what's in it."""
    plan = _plan(scene)
    g = land(scene.world)
    for tx, ty, tile in broke:
        if tile is tiles.AMBER:
            _amber(scene, plan, g, tx, ty)
        else:
            _hatch(scene, plan, g, tx, ty, tile)


def _wake(scene, key: str, x: float, y: float, rng: random.Random):
    """One of the land's enemies woken at the nearest open spot to (x, y),
    as tough as any (spawner.wake), alert."""
    from ..ai import make_enemy
    from .quests import free_spot
    spec = config.ENEMIES[key]
    x, y = free_spot(scene.world, x, y, spec.size_px / 2 + 1)
    sp = getattr(scene, "spawner", None)
    e = sp.wake(key, x, y, None, random.Random(rng.random())) if sp is not None else \
        make_enemy(key, x, y, random.Random(rng.random()))
    e.alert = True
    scene.enemies.append(e)
    return e


def _nearest_hero(scene, x: float, y: float):
    heroes = [p.hero for p in getattr(scene, "players", ()) if p.alive] or \
        [h for h in getattr(scene, "heroes", ()) if h.alive]
    return min(heroes, key=lambda h: math.hypot(h.x - x, h.y - y)) if heroes else None


def _hatch(scene, plan, g, tx: int, ty: int, tile) -> None:
    """An egg broke: hatchlings out of it; the first of its nest's eggs
    calls the parent (NEST_HATCH, NEST_PARENTS)."""
    per_egg, per_giant, far, angry = config.NEST_HATCH
    seed = getattr(scene.world, "seed", 0) or 0
    rng = random.Random(hash_coords(seed, 0xE66, tx, ty))
    x, y = tx + 0.5, ty + 0.5
    for _ in range(per_giant if tile is tiles.GIANT_EGG else per_egg):
        _wake(scene, "hatchling", x + rng.uniform(-0.8, 0.8), y + rng.uniform(-0.8, 0.8), rng)
    scene.effects.append(Effect("debris", x, y))
    nests = []
    if plan is not None:
        nests = [("nest", nx, ny) for nx, ny in plan.nests]
        if plan.great_nest is not None:
            nests.append(("great", *plan.great_nest))
    near = [n for n in nests if math.hypot(n[1] - x, n[2] - y) <= 12]
    kind, nx, ny = min(near, key=lambda n: math.hypot(n[1] - x, n[2] - y)) if near else \
        ("nest", tx // 8 * 8 + 4, ty // 8 * 8 + 4)
    key = (round(nx), round(ny))
    if key in g.parents:
        return
    g.parents.add(key)
    prng = random.Random(hash_coords(seed, 0x9A4E, *key))
    if kind == "great":
        parents = ["pterosaur", "pterosaur"]
    else:
        names = list(config.NEST_PARENTS)
        parents = [prng.choices(names, [config.NEST_PARENTS[n] for n in names])[0]]
    h = _nearest_hero(scene, x, y)
    for name in parents:
        a = prng.uniform(0, math.tau)
        e = _wake(scene, name, nx + math.cos(a) * far, ny + math.sin(a) * far, prng)
        e.driven = angry
        if h is not None:
            e.last_known = (h.x, h.y)
            e.forget_timer = config.FORGET_TIME
    scene.effects.append(Effect("toast", x, y - 1.5, label="THE PARENT COMES!"))


def _outcrop(world, tx: int, ty: int) -> tuple[int, int]:
    """The outcrop a broken piece of amber was part of, named by its first
    tile (the amber and the shards round it, joined)."""
    seen = {(tx, ty)}
    todo = [(tx, ty)]
    while todo and len(seen) < 80:
        x, y = todo.pop()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                q = (x + dx, y + dy)
                if q not in seen and world.tile_at(*q) in (tiles.AMBER, tiles.AMBER_SHARDS):
                    seen.add(q)
                    todo.append(q)
    return min(seen)


def _amber(scene, plan, g, tx: int, ty: int) -> None:
    """Breaking into an amber outcrop frees what's in it, once: loot, or
    what was frozen in it, waking (AMBER_FREE, AMBER_FIGHTS)."""
    key = _outcrop(scene.world, tx, ty)
    if key in g.opened:
        return
    g.opened.add(key)
    loot, value, piece = config.AMBER_FREE
    seed = getattr(scene.world, "seed", 0) or 0
    rng = random.Random(hash_coords(seed, 0xA3B, *key))
    x, y = tx + 0.5, ty + 0.5
    scene.effects.append(Effect("nova", x, y, size=1.5))
    if rng.random() < loot:
        from ..entities.gems import drop
        gems = getattr(scene, "gems", None)
        if gems is not None:
            for k in range(3):
                drop(gems, x + rng.uniform(-0.8, 0.8), y + rng.uniform(-0.8, 0.8), value / 3)
        if rng.random() < piece and hasattr(scene, "_drop_piece"):
            h = _nearest_hero(scene, x, y)
            p = next((p for p in scene.players if p.hero is h), None)
            if p is not None:
                scene._drop_piece(p, x, y)
        return
    ring = plan.ring_at(x, y) if plan is not None else 0
    name, n = rng.choice(config.AMBER_FIGHTS.get(ring, config.AMBER_FIGHTS[0]))
    for _ in range(n):
        _wake(scene, name, x + rng.uniform(-1.0, 1.0), y + rng.uniform(-1.0, 1.0), rng)
    scene.effects.append(Effect("toast", x, y - 1.5, label="IT LIVES!"))
