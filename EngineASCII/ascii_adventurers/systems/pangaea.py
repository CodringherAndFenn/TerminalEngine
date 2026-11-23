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

The land's damage scales like an enemy's (`hazard`). Nothing here echoes
(the echoes are the enemies', M31.2). The scene keeps one `Volcano` (its
bombs in the air, each hero's next volley) and calls `step` once a step,
after the heroes have moved; render/pangaea.py draws the bombs.
"""

from __future__ import annotations

import math

from .. import config
from ..entities.effects import Effect
from ..world import tiles

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
    world = scene.world
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
