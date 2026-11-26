"""
systems/relics.py -- the boss uniques that need a thing in the world or a
clock of their own (M28.5; design/GEAR.md 21). run_rules.RunRules calls
`tick` every step for every living hero; combat / character / roll hold the
one-line hooks (a hit, a roll, a hit taken).

  Dung Ball (Khepri)        a Ball rolling ahead of you (hero.ball)
  Spittoon (Ol' Spitter)    a ricocheting glob at the nearest enemy
  Hourglass Ring (Magus)    enemy shots near you crawl for a while
  Geiger Ring (the King)    rads to every enemy near you
  Rod of Fission (the King) a rod planted at your feet (hero.rod)
  Mr. Buttons (Fragile)     the bear (a decoy with HP) at your heels
  Crown of Black Ice (the Snow King)  chilled enemies leave black ice
  Hermit's Furs (the Snow King)       frost gathers while you stand still
  Sand Slippers (Magus)     a dune where a roll starts (roll.start)
  Bat Form Boots (Fragile)  a roll as bats, over everything (roll.start)

M28.5c (the forest, Mycelium, the necromancer):
  Shrinking Dust (Nettle)   a roll shrinks you (roll.start; speed in move)
  Cleaver of Cuddles        a cleaver orbiting you, quicker with kills
  Tripwire Boots            a wire along the roll (roll._ended) that trips
  Rootbound Boots (Fallen)  standing still grows a shield
  Heartwood Ring (Fallen)   trees near heal you
  Mycelial Ring / Corpse Candle   a patch where a kill fell (on_kill)
  Inkwell Charm             an ink blot on the nearest enemy (blinds it)
  Puffball Sandals          a spore burst where a roll starts (roll.start)
  Spore Wind Band           a gust that pushes and lengthens statuses
  Phylactery                a shade's 10 s after a fall (RunRules.revive)
  Lich's Gaze               the enemy kept under the aim is marked
M29.5 (the Four Horsemen's):
  Ring of Blood             a duel ring round you and an elite or boss (x2 both ways)
  The Black Scales          the lighter of you and the nearest enemy gives to the other
  Pale Rider's Cloak        your kills rise as pale shades that bite for you (on_kill)
  (Crown of Conquest: a hit crowns the enemy -- combat._relic_on_hit -- and a
  crowned enemy deals less: combat.strike)
M30.5 (the Host of the Feast's):
  Glutton's Bib             your kills leave scraps; eat one for health and a
                            stack of damage (on_kill; the stacks in combat.strike)
  The Host's Goblet         a toast: a wave of wine that makes enemies drunk
                            (Statuses.drunk: slow, and misses in Character.take_damage)
  Dancing Shoes             a roll ends in a ring of cutlery (roll._ended)
  Gilded Ring               hits on elites and bosses toss out coins; catch one
                            to be gilded (combat._relic_on_hit, combat.strike)
M31.5 (the Ancestor's, one per age and one for the first life):
  Spirit Herd               an ochre spirit mammoth charges through enemies
  Tyrant Skull              a roar: a cone that hurts and freezes in fear
  Swarm Ring                a river of stinging insects along your aim
  Echo Conch                your attacks fire again 3 s later, faded, from
                            where you stood (conch_record: GameScene._attack)
M32.5 (the Overseer's, one per thing it does to you):
  Overseer's Eye            a searchlight sweeps along your aim: the enemies it
                            lights are SEEN, taking more from you (combat.strike)
  Cell Key                  your next hit locks the enemy in a cell of laser
                            bars (the hit: combat._relic_on_hit; the cell here)
  Black Box                 it records what hurts you (Character.take_damage)
                            and rewinds: heals a share of it back
  Scrap Plating             kills bolt plates on (on_kill); each blocks a hit
                            (Character.take_damage) and adds damage (combat.strike)
And per hit (combat._relic_on_hit): the Fly Agaric Cap's trip (wander) and
the Lawyer's Wig's scrawls (bound); the scene moves wandering enemies and
holds bound ones (wander, after flee; `Statuses.bound`).

The rest are one-liners elsewhere: Scarab Carapace, Lead Apron and the
frost's bite in Character.take_damage, Hump Pack in RunRules.patterns, the
Lace Parasol in combat (an enemy shot reaching its hero), the fission's
+damage in combat.strike.
"""

from __future__ import annotations

import math

from .. import config
from ..entities.actor import Actor
from ..entities.effects import Effect
from ..entities.projectile import Projectile
from .collision import hull_hits_solid, move_hull
from .combat import push, strike
from .statuses import daze, inflict, statuses_of
from . import combat
from .zones import Zone


class Ball:
    """Khepri's dung ball: rolls from the hero along `angle`, flattening
    what it meets (a hit every U_DUNG_BALL[5] s per enemy), growing with
    each kill; a wall or U_DUNG_BALL[6] tiles bursts it."""

    def __init__(self, x: float, y: float, angle: float, damage: float) -> None:
        self.x, self.y = x, y
        self.angle = angle
        self.damage = damage
        self.radius = config.U_DUNG_BALL[1]
        self.rolled = 0.0
        self.hits: dict = {}            # id(enemy) -> the hero's time of the last hit
        self.alive = True


class Bear(Actor):
    """Mr. Buttons: follows the hero U_BUTTONS[3] tiles behind; enemies go
    for him first (an AIContext decoy); mends while unhurt; down for
    U_BUTTONS[2] s when his HP runs out, then up again."""
    faction = "player"
    bear = True                         # (bosses pay him no mind: ai/brain._pick_player)

    def __init__(self, hero, max_hp: float) -> None:
        super().__init__(round(max_hp), 0.55)
        self.x, self.y = hero.x, hero.y
        self.hero = hero
        self.half = config.U_BUTTONS[4]
        self.since_hit = 99.0
        self.down = 0.0                 # s left on the ground
        self.vx = self.vy = 0.0

    def take_damage(self, amount, source, from_angle):
        self.since_hit = 0.0
        dealt = super().take_damage(amount, source, from_angle)
        if not self.alive:
            self.down = config.U_BUTTONS[2]
        return dealt


def tick(scene, p, dt: float) -> None:
    hero, st = p.hero, p.hero.stats
    if st.has("dung_ball"):
        _ball(scene, hero, st, dt)
    elif hero.ball is not None:
        hero.ball = None
    if st.has("spittoon"):
        _spittoon(scene, hero, st, dt)
    if st.has("hourglass_ring"):
        _hourglass(scene, hero, st, dt)
    elif hero.hourglass_t > 0:
        _unslow(hero)
    if st.has("geiger_ring"):
        _geiger(scene, hero, st, dt)
    if st.has("rod_of_fission"):
        _rod(scene, hero, st, dt)
    elif hero.rod is not None:
        hero.rod = None
    if st.has("mr_buttons"):
        _bear(scene, hero, st, dt)
    elif hero.bear is not None:
        hero.bear = None
    if st.has("black_ice_crown"):
        _black_ice(scene, hero, st)
    hero.frost = st.has("hermits_furs") and (hero.frost or hero.still_t >= config.U_HERMITS_FURS[0])
    if hero.dunes:
        _settle(scene, hero, dt)
    # (M28.5c)
    _dust(hero, dt)
    if st.has("cleaver_of_cuddles"):
        _cleaver(scene, hero, st, dt)
    elif hero.cleaver is not None:
        hero.cleaver = None
    if hero.wires:
        _wires(scene, hero, st, dt)
    if st.has("rootbound_boots") or hero.roots > 0:
        _roots(hero, st, dt)
    if st.has("heartwood_ring"):
        _heartwood(scene, hero, st, dt)
    if st.has("inkwell_charm"):
        _inkwell(scene, hero, st, dt)
    if st.has("spore_wind_band"):
        _spore_wind(scene, hero, st, dt)
    if st.has("lichs_gaze"):
        _gaze(scene, hero, st, dt)
    if st.has("corpse_candle"):
        _candlelight(scene, hero, dt)
    if hero.shade > 0:
        _shade(scene, p, dt)
    # (M29.5: the Four Horsemen's)
    if st.has("ring_of_blood") or hero.blood_ring is not None:
        _blood_ring(scene, hero, st, dt)
    if st.has("black_scales"):
        _black_scales(scene, hero, st, dt)
    if hero.weighed is not None:
        foe, lost, left = hero.weighed
        hero.weighed = (foe, lost, left - dt) if left > dt else None
    if hero.pale:
        _pale_shades(scene, hero, dt)
    # (M30.5: the Host of the Feast's)
    if hero.bib_scraps or hero.feasted:
        _bib(scene, hero, dt)
    if st.has("hosts_goblet") or hero.goblet_waves:
        _goblet(scene, hero, st, dt)
    if hero.ring_coins:
        _gilded(scene, hero, dt)
    # (M31.5: the Ancestor's)
    if st.has("spirit_herd") or hero.herd:
        _herd(scene, hero, st, dt)
    if st.has("tyrant_skull"):
        _skull(scene, hero, st, dt)
    if st.has("swarm_ring") or hero.swarms:
        _swarm_ring(scene, hero, st, dt)
    if hero.conch:
        _conch(scene, hero, st, dt)
    # (M32.5: the Overseer's)
    if st.has("overseers_eye") or hero.eye_sweep > 0:
        _overseers_eye(scene, hero, st, dt)
    if st.has("cell_key") or hero.cell_lock is not None:
        _cell_key(scene, hero, st, dt)
    if st.has("black_box"):
        _black_box(scene, hero, st, dt)
    elif hero.box_log:
        hero.box_log = []
    if hero.plate_lost:
        scene.effects.append(Effect("toast", hero.x, hero.y - 2.0, label="PLATE OFF!"))
        scene.effects.append(Effect("debris", hero.x, hero.y))
        hero.plate_lost = 0
    if hero.scrap_plates and not st.has("scrap_plating"):
        hero.scrap_plates = 0


# --- The dung ball ---------------------------------------------------------------------

def _ball(scene, hero, st, dt: float) -> None:
    speed, r0, plus_dmg, plus_r, r_max, gap, reach, wait = config.U_DUNG_BALL
    b = hero.ball
    if b is None or not b.alive:
        hero.ball_t -= dt
        if hero.ball_t > 0:
            return
        a = hero.aim_angle
        x, y = hero.x + math.cos(a) * 1.0, hero.y + math.sin(a) * 1.0
        b = hero.ball = Ball(x, y, a, st.uniques.get("dung_ball", 10.0))
        hero.ball_t = wait
        return
    step = speed * dt
    nx, ny = b.x + math.cos(b.angle) * step, b.y + math.sin(b.angle) * step
    half = b.radius * config.TILE_PX_W * 0.7
    if hull_hits_solid(scene.world, nx, ny, 0.0, half, half) or b.rolled + step >= reach:
        b.alive = False
        scene.effects.append(Effect("debris", b.x, b.y))
        scene.effects.append(Effect("nova", b.x, b.y, size=b.radius))
        return
    b.x, b.y, b.rolled = nx, ny, b.rolled + step
    for e in scene.enemies:
        if not e.alive or not e.hittable or getattr(e, "faction", None) != "enemy":
            continue
        if math.hypot(e.x - b.x, e.y - b.y) > b.radius + e.hit_radius:
            continue
        if hero.time - b.hits.get(id(e), -1e9) < gap:
            continue
        b.hits[id(e)] = hero.time
        strike(e, b.damage, hero, b.angle, scene.effects, pet=True)
        if not e.alive:
            b.damage += plus_dmg
            b.radius = min(r_max, b.radius + plus_r)


# --- The spittoon ----------------------------------------------------------------------

def _spittoon(scene, hero, st, dt: float) -> None:
    every, reach, bounces = config.U_SPITTOON
    hero.spit_t -= dt
    if hero.spit_t > 0:
        return
    near = [e for e in scene.enemies if e.alive and e.hittable
            and getattr(e, "faction", None) == "enemy"
            and math.hypot(e.x - hero.x, e.y - hero.y) <= reach]
    if not near:
        return
    hero.spit_t = every
    e = min(near, key=lambda e: math.hypot(e.x - hero.x, e.y - hero.y))
    a = math.atan2(e.y - hero.y, e.x - hero.x)
    shell = config.WEAPONS["spittoon_glob"].shell
    q = Projectile(hero.x + math.cos(a) * 0.8, hero.y + math.sin(a) * 0.8, a, shell, owner=hero,
                   damage=st.uniques.get("spittoon", 20.0))
    q.tags = ("poison",)
    scene.projectiles.append(q)
    scene.effects.append(Effect("muzzle", q.x, q.y, a))


# --- The hourglass ---------------------------------------------------------------------

def _hourglass(scene, hero, st, dt: float) -> None:
    every, radius, crawl = config.U_HOURGLASS
    if hero.hourglass_t > 0:
        hero.hourglass_t -= dt
        if hero.hourglass_t <= 0:
            _unslow(hero)
            return
        for q in scene.projectiles:
            if not q.alive or getattr(q.owner, "faction", None) == "player":
                continue
            if math.hypot(q.x - hero.x, q.y - hero.y) <= radius:
                if q.time_scale > crawl:
                    hero.slowed_shots.append(q)
                q.time_scale = crawl
        return
    hero.hourglass_cd -= dt
    if hero.hourglass_cd > 0:
        return
    # (Ready, it waits for an enemy shot to come within reach: a crawl
    # nobody sees would waste it.)
    if any(q.alive and getattr(q.owner, "faction", None) != "player"
           and math.hypot(q.x - hero.x, q.y - hero.y) <= radius for q in scene.projectiles):
        hero.hourglass_cd = every
        hero.hourglass_t = st.uniques.get("hourglass_ring", 2.0)
        scene.effects.append(Effect("nova", hero.x, hero.y, size=radius))


def _unslow(hero) -> None:
    for q in hero.slowed_shots:
        q.time_scale = 1.0
    hero.slowed_shots = []
    hero.hourglass_t = 0.0


# --- The Geiger ring -------------------------------------------------------------------

def _geiger(scene, hero, st, dt: float) -> None:
    radius, boss_share, every = config.U_GEIGER
    share = st.uniques.get("geiger_ring", 0.01)
    hero.geiger_t -= dt
    due = hero.geiger_t <= 0
    if due:
        hero.geiger_t += every
    for e in scene.enemies:
        if not e.alive or not e.hittable or getattr(e, "faction", None) != "enemy":
            continue
        if math.hypot(e.x - hero.x, e.y - hero.y) > radius + e.hit_radius:
            continue
        owed = e.__dict__.get("rads_owed", 0.0) + e.max_hp * (
            boss_share if getattr(e, "boss", False) else share) * dt
        if due:
            dealt = e.take_damage(owed, hero, None)
            owed = 0.0
            if dealt > 0:
                scene.effects.append(Effect("number", e.x, e.y - e.hit_radius,
                                            value=max(1, round(dealt)), tone="poison"))
        e.rads_owed = owed


# --- The rod of fission ----------------------------------------------------------------

def _rod(scene, hero, st, dt: float) -> None:
    every, radius, seconds, more, away = config.U_FISSION
    rod = hero.rod
    if rod is None or math.hypot(rod[0] - hero.x, rod[1] - hero.y) >= away:
        hero.rod = [hero.x, hero.y, every]
        return
    rod[2] -= dt
    if rod[2] > 0:
        return
    rod[2] = every
    scene.effects.append(Effect("nova", rod[0], rod[1], size=radius))
    for e in scene.enemies:
        if not e.alive or not e.hittable or getattr(e, "faction", None) != "enemy":
            continue
        if math.hypot(e.x - rod[0], e.y - rod[1]) <= radius + e.hit_radius:
            strike(e, st.uniques.get("rod_of_fission", 10.0), hero, None, scene.effects, pet=True)
            e.fissioned = hero.time + seconds


# --- Mr. Buttons -----------------------------------------------------------------------

def _bear(scene, hero, st, dt: float) -> None:
    mend, calm, down, behind, half = config.U_BUTTONS
    b = hero.bear
    top = round(st.uniques.get("mr_buttons", 200.0))
    if b is None:
        b = hero.bear = Bear(hero, top)
    if b.max_hp != top:                          # (the piece levelled up)
        b.hp = b.hp * top / b.max_hp
        b.max_hp = top
    if not b.alive:
        b.down -= dt
        if b.down <= 0:
            b.hp = float(b.max_hp)
            b.x, b.y = hero.x, hero.y
            b.since_hit = 99.0
        return
    b.since_hit += dt
    if b.since_hit >= calm and b.hp < b.max_hp:
        b.hp = min(float(b.max_hp), b.hp + mend * dt)
    way = hero.heading if hero.heading is not None else hero.aim_angle
    gx = hero.x - math.cos(way) * behind
    gy = hero.y - math.sin(way) * behind
    dx, dy = gx - b.x, gy - b.y
    d = math.hypot(dx, dy)
    if d < 0.3:
        return
    speed = hero.spec.max_speed * 1.2
    step = min(d, speed * dt)
    if d > 12.0:                                 # (left far behind: he catches up)
        b.x, b.y = hero.x, hero.y
        return
    b.x, b.y, _, _ = move_hull(scene.world, b.x, b.y, 0.0, half, half, dx / d * step, dy / d * step)


# --- The crown of black ice ------------------------------------------------------------

def _black_ice(scene, hero, st) -> None:
    """Every U_BLACK_ICE[0] tiles a chilled enemy walks, a patch of black
    ice (the power's s) chills whoever stands on it, once every [2] s. A
    hero keeps at most [3] patches down (the oldest melt first)."""
    step, radius, every, most = config.U_BLACK_ICE
    life = st.uniques.get("black_ice_crown", 3.0)
    for e in scene.enemies:
        if not e.alive or getattr(e, "faction", None) != "enemy":
            continue
        s = e.status
        if s is None or not s.has("chill"):
            e.__dict__.pop("iced_at", None)
            continue
        last = e.__dict__.get("iced_at")
        if last is None:
            e.iced_at = (e.x, e.y)
            continue
        if math.hypot(e.x - last[0], e.y - last[1]) < step:
            continue
        e.iced_at = (e.x, e.y)
        z = Zone("black_ice", e.x, e.y, radius, life, every, 0.0, hero, ("cold",), "chill", 1)
        z.timer = every                           # (it's chilled already)
        scene.zones.append(z)
        mine = [q for q in scene.zones if q.kind == "black_ice" and q.source is hero]
        for old in mine[:max(0, len(mine) - most)]:
            old.age = old.life                    # (melts: update_zones drops it)


# --- The hermit's furs -----------------------------------------------------------------

def frost_bite(hero, enemy) -> None:
    """Hermit's Furs: the gathered frost freezes the enemy that hit the
    hero, the power's s (a boss U_HERMITS_FURS[1] s), and is spent."""
    hero.frost = False
    hero.still_t = 0.0
    seconds = config.U_HERMITS_FURS[1] if getattr(enemy, "boss", False) \
        else hero.stats.uniques.get("hermits_furs", 3.0)
    s = statuses_of(enemy)
    s.frozen = max(s.frozen, seconds)
    s.frozen_by = hero


# --- The sand slippers -----------------------------------------------------------------

def raise_dune(scene, hero) -> None:
    """Sand Slippers: a dune U_SAND_SLIPPERS tiles wide across the roll's
    line where it started, standing the power's s: sand heaps you walk
    over but shots stop at. Only on open ground (nothing solid, nothing
    that already stops shots: water is solid)."""
    world = scene.world
    if not hasattr(world, "set_tile"):
        return
    from ..world import tiles
    dx, dy = hero.roll_dir
    nx, ny = -dy, dx                              # (across the roll)
    half = (config.U_SAND_SLIPPERS - 1) / 2        # (centre to the last tile's middle)
    cells = []
    k = -half
    while k <= half + 1e-9:
        cell = (math.floor(hero.x + nx * k), math.floor(hero.y + ny * k))
        if cell not in cells:
            cells.append(cell)
        k += 0.5
    laid = []
    for tx, ty in cells:
        was = world.tile_at(tx, ty)
        if was.solid or was.blocks_shots or was is tiles.SAND_HEAP \
                or was.name == "void":
            continue
        world.set_tile(tx, ty, tiles.SAND_HEAP)
        laid.append((tx, ty, was))
    if laid:
        hero.dunes.append([hero.stats.uniques.get("sand_slippers", 2.0), laid])
        scene.effects.append(Effect("debris", hero.x, hero.y))


def _settle(scene, hero, dt: float) -> None:
    """The dunes' clocks: a dune whose time is up sinks back (only where
    it's still sand heap)."""
    from ..world import tiles
    keep = []
    for d in hero.dunes:
        d[0] -= dt
        if d[0] > 0:
            keep.append(d)
            continue
        for tx, ty, was in d[1]:
            if scene.world.tile_at(tx, ty) is tiles.SAND_HEAP:
                scene.world.set_tile(tx, ty, was)
    hero.dunes = keep


def flatten_dunes(scene, hero) -> None:
    """Every dune of the hero's sinks at once (the run's end, a fall)."""
    for d in hero.dunes:
        d[0] = 0.0
    _settle(scene, hero, 0.0)


# --- Bat form --------------------------------------------------------------------------

def bat_roll(scene, hero) -> None:
    """Bat Form Boots: the roll goes the power farther (as speed over the
    same time) and over everything (Tumbler Boots (L)'s vault: walls,
    water, enemies -- never out of a lair or over the edge); the hero is
    a cloud of bats till it ends."""
    from .roll import _vault
    hero.roll_speed *= 1 + hero.stats.uniques.get("bat_form", 0.5)
    if hero.vault is None:
        _vault(scene, hero)
    hero.bats = True


# === M28.5c ============================================================================

def _foes(scene):
    return [e for e in scene.enemies if e.alive and e.hittable
            and getattr(e, "faction", None) == "enemy"]


def on_kill(scene, p, enemy) -> None:
    """What a hero's kill sets off (RunRules._kill_effects): the cleaver
    spins up, a spore patch (Mycelial Ring), a candle (Corpse Candle), a
    shade's count toward coming back (Phylactery)."""
    hero, st = p.hero, p.hero.stats
    if st.has("cleaver_of_cuddles") and hero.cleaver is not None:
        _, _, plus, most, _, _, _ = config.U_CLEAVER
        hero.cleaver[1] = min(most, hero.cleaver[1] + plus)
    if st.has("mycelial_ring"):
        radius, every = config.U_MYCELIAL
        z = Zone("pool", enemy.x, enemy.y, radius, st.uniques.get("mycelial_ring", 5.0), every,
                 0.0, hero, (config.STATUSES["poison"].tag,), "poison", 1)
        scene.zones.append(z)
    if st.has("corpse_candle"):
        life, radius, _, every, most = config.U_CANDLE
        z = Zone("candle", enemy.x, enemy.y, radius, life, every,
                 st.uniques.get("corpse_candle", 8.0) * every, hero, ("fire",))
        scene.zones.append(z)
        mine = [q for q in scene.zones if q.kind == "candle" and q.source is hero]
        for old in mine[:max(0, len(mine) - most)]:
            old.age = old.life
    if st.has("pale_riders_cloak") and not getattr(enemy, "boss", False) \
            and getattr(enemy, "kind_key", "") != "pale_shade" \
            and len(hero.pale) < config.U_PALE[0]:     # (M29.5: it rises for you)
        hero.pale.append({"x": enemy.x, "y": enemy.y, "facing": 0.0, "walked": 0.0,
                          "life": st.uniques.get("pale_riders_cloak", 6.0), "bite": 0.0})
        scene.effects.append(Effect("unveil", enemy.x, enemy.y, size=1.0))
    if st.has("scrap_plating") and hero.scrap_plates < config.U_PLATES:   # (M32.5: a plate)
        hero.scrap_plates += 1
        scene.effects.append(Effect("spark_burst", hero.x, hero.y, size=0.8))
    if st.has("gluttons_bib") and not getattr(enemy, "boss", False):   # (M30.5: a scrap)
        hero.bib_scraps = (hero.bib_scraps + [[enemy.x, enemy.y, config.U_BIB[3]]])[
            -config.U_BIB[5]:]
    if hero.shade > 0:
        hero.shade_kills += 1
        if hero.shade_kills >= config.U_PHYLACTERY[1]:
            hero.shade = 0.0
            hero.untouchable = 0.0
            hero.hp = max(hero.hp, hero.max_hp * min(1.0, st.uniques.get("phylactery", 0.3)))
            scene.effects.append(Effect("toast", hero.x, hero.y - 2, label="BACK FROM THE GRAVE!"))
            scene.effects.append(Effect("nova", hero.x, hero.y, size=2.0))


# --- Shrinking dust --------------------------------------------------------------------

def dust(hero) -> None:
    """Shrinking Dust: a roll shrinks the hero for U_SHRINKING_DUST[0] s."""
    hero.dusted = config.U_SHRINKING_DUST[0]
    hero.hit_radius = hero.body_r * config.U_SHRINKING_DUST[1]


def _dust(hero, dt: float) -> None:
    if hero.dusted > 0:
        hero.dusted = max(0.0, hero.dusted - dt)
        if hero.dusted <= 0:
            hero.hit_radius = hero.body_r


# --- The cleaver of cuddles ------------------------------------------------------------

def cleaver_spot(hero) -> tuple[float, float]:
    r = config.U_CLEAVER[0]
    a = hero.cleaver[0]
    return hero.x + math.cos(a) * r, hero.y + math.sin(a) * r


def _cleaver(scene, hero, st, dt: float) -> None:
    """The Cleaver of Cuddles: orbits the hero, cutting what the blade
    passes (each enemy at most every U_CLEAVER[5] s); kills spin it up
    (on_kill), and it slows back to x1 over U_CLEAVER[4] s from the most."""
    radius, turn, plus, most, slow, gap, reach = config.U_CLEAVER
    c = hero.cleaver
    if c is None:
        c = hero.cleaver = [hero.aim_angle, 1.0, {}]
    c[1] = max(1.0, c[1] - (most - 1.0) / slow * dt)
    c[0] = (c[0] + turn * c[1] * dt) % math.tau
    bx, by = cleaver_spot(hero)
    for e in _foes(scene):
        if math.hypot(e.x - bx, e.y - by) > reach + e.hit_radius:
            continue
        if hero.time - c[2].get(id(e), -1e9) < gap:
            continue
        c[2][id(e)] = hero.time
        strike(e, st.uniques.get("cleaver_of_cuddles", 15.0), hero, c[0] + math.pi / 2,
               scene.effects, pet=True)


# --- The acorn bandolier ---------------------------------------------------------------

def acorns(scene, hero, aim: float) -> None:
    """Acorn Bandolier: U_ACORNS[1] acorns lobbed U_ACORNS[2] tiles out,
    U_ACORNS[3] rad apart round the aim, bursting where they land."""
    _, n, out, apart, _ = config.U_ACORNS
    shell = config.WEAPONS["acorn_lob"].shell
    dmg = hero.stats.uniques.get("acorn_bandolier", 8.0)
    for k in range(n):
        a = aim + apart * (k - (n - 1) / 2)
        q = Projectile(hero.x, hero.y, a, shell, owner=hero, damage=dmg)
        q.flight = out
        q.target = (hero.x + math.cos(a) * out, hero.y + math.sin(a) * out)
        scene.projectiles.append(q)


# --- Tripwire boots --------------------------------------------------------------------

def lay_wire(hero) -> None:
    """Tripwire Boots: a wire from where the roll started to where it
    ended, for U_TRIPWIRE[0] s."""
    x0, y0 = hero.roll_from
    if math.hypot(hero.x - x0, hero.y - y0) < 0.5:
        return
    hero.wires.append([x0, y0, hero.x, hero.y, config.U_TRIPWIRE[0]])


def _off_segment(px, py, x0, y0, x1, y1) -> float:
    dx, dy = x1 - x0, y1 - y0
    n = dx * dx + dy * dy
    t = 0.0 if n <= 1e-12 else max(0.0, min(1.0, ((px - x0) * dx + (py - y0) * dy) / n))
    return math.hypot(px - (x0 + dx * t), py - (y0 + dy * t))


def _wires(scene, hero, st, dt: float) -> None:
    """The first enemy across a wire is knocked down (dazed the power's s;
    a boss bound U_TRIPWIRE[1] s), and the wire is spent."""
    keep = []
    for w in hero.wires:
        w[4] -= dt
        if w[4] <= 0:
            continue
        hit = next((e for e in _foes(scene)
                    if _off_segment(e.x, e.y, *w[:4]) <= e.hit_radius + 0.1), None)
        if hit is None:
            keep.append(w)
            continue
        if getattr(hit, "boss", False):
            s = statuses_of(hit)
            s.bound = max(s.bound, config.U_TRIPWIRE[1])
        else:
            daze(hit, st.uniques.get("tripwire_boots", 1.5) if st is not None else 1.5)
        scene.effects.append(Effect("toast", hit.x, hit.y - 1.5, label="TRIPPED!"))
    hero.wires = keep


# --- Rootbound boots -------------------------------------------------------------------

def _roots(hero, st, dt: float) -> None:
    """Standing still (0.5 s on) grows a shield, the power a second, up to
    U_ROOTBOUND[0] of max HP; walking fades what the roots grew over
    U_ROOTBOUND[1] s. (Hits eat it like any shield.)"""
    share, fade = config.U_ROOTBOUND
    cap = hero.max_hp * share
    hero.roots = min(hero.roots, hero.shield)
    if st.has("rootbound_boots") and hero.still_t >= 0.5 and not hero.rolling:
        add = min(st.uniques.get("rootbound_boots", 5.0) * dt, max(0.0, cap - hero.roots))
        hero.shield += add
        hero.roots += add
    elif hero.still_t <= 0 or not st.has("rootbound_boots"):
        cut = min(hero.roots, cap / fade * dt)
        hero.roots -= cut
        hero.shield = max(0.0, hero.shield - cut)


# --- Heartwood ring --------------------------------------------------------------------

TREES = frozenset(("tree", "pine", "gnarled tree", "hollow tree", "marked tree", "grove tree"))


def _heartwood(scene, hero, st, dt: float) -> None:
    reach, every = config.U_HEARTWOOD
    hero.tree_t -= dt
    if hero.tree_t <= 0:
        hero.tree_t = every
        r = math.ceil(reach)
        hero.near_tree = any(
            scene.world.tile_at(tx, ty).name in TREES
            for tx in range(math.floor(hero.x) - r, math.floor(hero.x) + r + 1)
            for ty in range(math.floor(hero.y) - r, math.floor(hero.y) + r + 1)
            if math.hypot(tx + 0.5 - hero.x, ty + 0.5 - hero.y) <= reach + 0.5)
    if hero.near_tree:
        hero.heal(st.uniques.get("heartwood_ring", 2.0) * dt)


# --- The inkwell charm -----------------------------------------------------------------

def _inkwell(scene, hero, st, dt: float) -> None:
    """Every U_INKWELL[0] s (waiting for an enemy within [2] tiles) an ink
    blot falls on the nearest: the power's damage, and it can't see this
    hero for [1] s (ai/brain.Brain.smoked)."""
    every, blind, reach = config.U_INKWELL
    hero.ink_t -= dt
    if hero.ink_t > 0:
        return
    near = [e for e in _foes(scene) if math.hypot(e.x - hero.x, e.y - hero.y) <= reach]
    if not near:
        return
    hero.ink_t = every
    e = min(near, key=lambda e: math.hypot(e.x - hero.x, e.y - hero.y))
    scene.effects.append(Effect("nova", e.x, e.y, size=0.9))
    strike(e, st.uniques.get("inkwell_charm", 15.0), hero, None, scene.effects, pet=True)
    e.ink_blot = (hero, hero.time + blind)


# --- The spore wind band ---------------------------------------------------------------

def _spore_wind(scene, hero, st, dt: float) -> None:
    """Every U_SPORE_WIND[0] s (waiting for an enemy within [1] tiles) a
    gust pushes the enemies round you [2] tiles away; their statuses last
    the power's s longer."""
    every, radius, shove = config.U_SPORE_WIND
    hero.gust_t -= dt
    if hero.gust_t > 0:
        return
    near = [e for e in _foes(scene)
            if math.hypot(e.x - hero.x, e.y - hero.y) <= radius + e.hit_radius]
    if not near:
        return
    hero.gust_t = every
    more = st.uniques.get("spore_wind_band", 2.0)
    scene.effects.append(Effect("pulse", hero.x, hero.y, size=radius))
    for e in near:
        d = math.hypot(e.x - hero.x, e.y - hero.y)
        a = math.atan2(e.y - hero.y, e.x - hero.x) if d > 1e-6 else hero.aim_angle
        push(e, scene.world, math.cos(a) * shove, math.sin(a) * shove)
        if e.status is not None:
            for s in e.status.active.values():
                s.left += more


# --- The phylactery --------------------------------------------------------------------

def rise_as_shade(scene, p) -> bool:
    """The Phylactery (RunRules.revive): once a run, a fallen hero rises as
    a shade with 1 HP, untouchable, at half damage, for U_PHYLACTERY[0]
    s; U_PHYLACTERY[1] kills bring them back (on_kill), or they fall."""
    hero, st = p.hero, p.hero.stats
    if st is None or not st.has("phylactery") or p.phylactery_used:
        return False
    p.phylactery_used = True
    seconds = config.U_PHYLACTERY[0]
    hero.hp = 1.0
    hero.shade, hero.shade_kills = seconds, 0
    hero.untouchable = max(hero.untouchable, seconds)
    scene.effects.append(Effect("toast", hero.x, hero.y - 2,
                                label=f"A SHADE: KILL {config.U_PHYLACTERY[1]}!"))
    return True


def _shade(scene, p, dt: float) -> None:
    hero = p.hero
    hero.shade = max(0.0, hero.shade - dt)
    if hero.shade <= 0:
        hero.untouchable = 0.0
        hero.hp = 0.0                            # (too few: the hero falls after all)
        scene.effects.append(Effect("toast", hero.x, hero.y - 2, label="THE SHADE FADES"))


# --- Lich's gaze -----------------------------------------------------------------------

def _gaze(scene, hero, st, dt: float) -> None:
    """The nearest enemy on the aim line (within U_LICHS_GAZE[2] tiles of
    it, [0] tiles out): kept there [1] s, it's marked for this hero (the
    next hit does x the power: combat.strike)."""
    reach, hold, slack = config.U_LICHS_GAZE
    ca, sa = math.cos(hero.aim_angle), math.sin(hero.aim_angle)
    best, best_along = None, reach + 1
    for e in _foes(scene):
        rx, ry = e.x - hero.x, e.y - hero.y
        along = rx * ca + ry * sa
        if along <= 0 or along > reach + e.hit_radius or along >= best_along:
            continue
        if abs(-rx * sa + ry * ca) > slack + e.hit_radius:
            continue
        best, best_along = e, along
    if best is None or best is not hero.gaze:
        hero.gaze, hero.gaze_t = best, 0.0
        return
    hero.gaze_t += dt
    marks = best.__dict__.setdefault("lich_marks", set())
    if hero.gaze_t >= hold and id(hero) not in marks:
        marks.add(id(hero))
        scene.effects.append(Effect("toast", best.x, best.y - 1.5, label="MARKED"))


def gaze_mult(victim, source) -> float:
    """combat.strike: a hero's hit on an enemy their gaze marked does x the
    power, once."""
    marks = victim.__dict__.get("lich_marks")
    if not marks or id(source) not in marks:
        return 1.0
    marks.discard(id(source))
    return source.stats.uniques.get("lichs_gaze", 2.0)


# --- The corpse candle -----------------------------------------------------------------

def _candlelight(scene, hero, dt: float) -> None:
    """Standing in one of your candles' light heals U_CANDLE[2] HP a second
    (one candle's worth, however many)."""
    if any(z.kind == "candle" and z.source is hero
           and math.hypot(hero.x - z.x, hero.y - z.y) <= z.radius for z in scene.zones):
        hero.heal(config.U_CANDLE[2] * dt)


# --- Hits: the fly agaric cap and the lawyer's wig -------------------------------------

def on_hit(victim, source, stats) -> None:
    """A hero's own hit landing (combat._relic_on_hit; not a summon's)."""
    boss = getattr(victim, "boss", False)
    if stats.has("fly_agaric_cap") and source.rng.random() < stats.uniques.get("fly_agaric_cap", 0.1):
        seconds, stumble, gap = config.U_FLY_AGARIC
        s = statuses_of(victim)
        if boss:
            if source.time - victim.__dict__.get("stumbled", -1e9) >= gap:
                victim.stumbled = source.time
                s.bound = max(s.bound, stumble)
        elif s.wander <= 0:
            s.wander = seconds
            s.wander_dir = source.rng.random() * math.tau
    if stats.has("lawyers_wig"):
        marks = victim.__dict__.setdefault("wig_marks", {})   # (not "scrawls": the ink cap has those)
        n = marks.get(id(source), 0) + 1
        if n >= config.U_WIG[0]:
            n = 0
            s = statuses_of(victim)
            s.bound = max(s.bound, config.U_WIG[1] if boss
                          else stats.uniques.get("lawyers_wig", 2.0))
        marks[id(source)] = n


def wander(scene, e, dt: float) -> bool:
    """A tripped enemy (the Fly Agaric Cap) drifts about at half its speed
    instead of thinking. Bosses stumble instead (bound)."""
    st = e.status
    if st is None or st.wander <= 0 or getattr(e, "boss", False):
        return False
    speed = getattr(getattr(e, "espec", None), "speed", 0.0)
    if speed <= 0:
        return False
    st.wander_dir += (e.rng.random() - 0.5) * 6.0 * dt if hasattr(e, "rng") else 0.0
    step = speed * 0.5 * dt * st.time_scale
    push(e, scene.world, math.cos(st.wander_dir) * step, math.sin(st.wander_dir) * step)
    return True


# --- Puffball sandals ------------------------------------------------------------------

def puff(scene, hero) -> None:
    """Puffball Sandals: a spore burst where the roll starts -- the power's
    damage and a poison within U_PUFFBALL tiles."""
    r = config.U_PUFFBALL
    scene.effects.append(Effect("nova", hero.x, hero.y, size=r))
    dmg = hero.stats.uniques.get("puffball_sandals", 20.0)
    for e in _foes(scene):
        if math.hypot(e.x - hero.x, e.y - hero.y) <= r + e.hit_radius:
            strike(e, dmg, hero, None, scene.effects, (config.STATUSES["poison"].tag,), on_hit=False)
            if e.alive:
                inflict(e, "poison", hero)


# === M29.5: the Four Horsemen's relics ====================================================

def _blood_ring(scene, hero, st, dt: float) -> None:
    """Ring of Blood: every U_BLOOD_RING[0] s, a ring of blood round you and
    the nearest elite or boss (within U_BLOOD_RING[1]): for its power in s
    you're in a duel with it -- both of you deal double damage
    (combat.strike) -- until it ends, it dies, or you step out."""
    every, reach, radius = config.U_BLOOD_RING
    r = hero.blood_ring
    if r is not None:
        r["left"] -= dt
        foe = r["foe"]
        out = math.hypot(hero.x - r["x"], hero.y - r["y"]) > r["r"]
        if r["left"] <= 0 or not foe.alive or out or not st.has("ring_of_blood"):
            if hero.duel is foe:
                hero.duel = None
            hero.blood_ring = None
            hero.blood_ring_t = every
        return
    hero.blood_ring_t -= dt
    if hero.blood_ring_t > 0:
        return
    foes = [e for e in _foes(scene) if (e.espec.elite or getattr(e, "boss", False))
            and math.hypot(e.x - hero.x, e.y - hero.y) <= reach]
    if not foes:
        hero.blood_ring_t = 1.0
        return
    foe = min(foes, key=lambda e: math.hypot(e.x - hero.x, e.y - hero.y))
    d = math.hypot(foe.x - hero.x, foe.y - hero.y)
    hero.blood_ring = {"x": (hero.x + foe.x) / 2, "y": (hero.y + foe.y) / 2,
                       "r": max(radius, d / 2 + 2.0), "foe": foe,
                       "left": st.uniques.get("ring_of_blood", 6.0)}
    hero.duel = foe
    scene.effects.append(Effect("toast", hero.x, hero.y - 2, label="RING OF BLOOD!"))


def _black_scales(scene, hero, st, dt: float) -> None:
    """The Black Scales: every U_SCALES[0] s, you against the nearest enemy
    (within U_SCALES[1]): whichever has less health as a share of its max
    loses the power x its own max to the other (a boss x U_SCALES[2] of
    that)."""
    every, reach, boss_x = config.U_SCALES
    hero.scales_t -= dt
    if hero.scales_t > 0:
        return
    hero.scales_t = every
    near = [e for e in _foes(scene) if math.hypot(e.x - hero.x, e.y - hero.y) <= reach]
    if not near or hero.max_hp <= 0:
        return
    foe = min(near, key=lambda e: math.hypot(e.x - hero.x, e.y - hero.y))
    share = st.uniques.get("black_scales", 0.03)
    mine, theirs = hero.hp / hero.max_hp, foe.hp / foe.max_hp if foe.max_hp else 0.0
    if theirs < mine:
        cut = share * (boss_x if getattr(foe, "boss", False) else 1.0)
        lost = foe.take_damage(foe.max_hp * cut, hero, None)
        hero.heal(lost)
        scene.effects.append(Effect("toast", foe.x, foe.y - 2, label="FOUND WANTING!"))
    else:
        lost = hero.take_damage(hero.max_hp * share, foe, None)
        foe.hp = min(float(foe.max_hp), foe.hp + lost)
        scene.effects.append(Effect("toast", hero.x, hero.y - 2, label="WEIGHED!"))
    hero.weighed = (foe, theirs >= mine, 1.2)


def _pale_shades(scene, hero, dt: float) -> None:
    """Pale Rider's Cloak: your risen shades go for the nearest enemy and
    bite it (U_PALE: damage, every s), till their time is up."""
    most, bite, speed, every = config.U_PALE
    foes = _foes(scene)
    for s in hero.pale:
        s["life"] -= dt
        s["bite"] -= dt
        t = min(foes, key=lambda e: math.hypot(e.x - s["x"], e.y - s["y"]), default=None)
        if t is None:
            continue
        dx, dy = t.x - s["x"], t.y - s["y"]
        d = math.hypot(dx, dy)
        if d > 1.1 + t.hit_radius:
            step = min(d, speed * dt)
            s["x"] += dx / d * step
            s["y"] += dy / d * step
            s["walked"] += step
            s["facing"] = math.atan2(dy, dx)
        elif s["bite"] <= 0:
            s["bite"] = every
            strike(t, bite, hero, math.atan2(dy, dx), scene.effects, pet=True)
    hero.pale = [s for s in hero.pale if s["life"] > 0]


# === M30.5: the Host of the Feast's relics ================================================

def _bib(scene, hero, dt: float) -> None:
    """Glutton's Bib: eat a scrap your kill left (walk over it): heal
    U_BIB[0] of your max HP and a stack of damage for U_BIB[1] s (at most
    U_BIB[2]; combat.strike counts them)."""
    heal, last, most, _, reach, _ = config.U_BIB
    hero.feasted = [t for t in hero.feasted if t > hero.time]
    keep = []
    for s in hero.bib_scraps:
        s[2] -= dt
        if hero.alive and math.hypot(hero.x - s[0], hero.y - s[1]) <= reach + hero.hit_radius:
            hero.heal(hero.max_hp * heal)
            hero.feasted = sorted(hero.feasted + [hero.time + last])[-most:]
            scene.effects.append(Effect("spill", s[0], s[1], size=0.8))
            scene.effects.append(Effect("toast", hero.x, hero.y - 2,
                                        label=f"FEASTED x{len(hero.feasted)}"))
            continue
        if s[2] > 0:
            keep.append(s)
    hero.bib_scraps = keep


def _goblet(scene, hero, st, dt: float) -> None:
    """The Host's Goblet: every U_GOBLET[0] s (with an enemy in reach), a
    toast: a wave of wine rolls out at U_GOBLET[2] tiles/s to U_GOBLET[1],
    the power's damage and a push to each enemy it reaches, who's then drunk
    (U_GOBLET[3] s, half for a boss: Statuses.drunk)."""
    every, reach, speed, drunk, _, _, shove = config.U_GOBLET
    foes = _foes(scene)
    for w in hero.goblet_waves:
        w[2] += speed * dt
        for e in foes:
            if id(e) in w[3] or math.hypot(e.x - w[0], e.y - w[1]) - e.hit_radius > w[2]:
                continue
            w[3].add(id(e))
            a = math.atan2(e.y - w[1], e.x - w[0])
            strike(e, st.uniques.get("hosts_goblet", 20.0), hero, a, scene.effects, on_hit=False)
            if e.alive:
                push(e, scene.world, math.cos(a) * shove, math.sin(a) * shove)
                s = statuses_of(e)
                s.drunk = max(s.drunk, drunk * (0.5 if getattr(e, "boss", False) else 1.0))
    hero.goblet_waves = [w for w in hero.goblet_waves if w[2] < reach]
    if not st.has("hosts_goblet"):
        return
    hero.goblet_t -= dt
    if hero.goblet_t > 0:
        return
    if not any(math.hypot(e.x - hero.x, e.y - hero.y) <= reach for e in foes):
        hero.goblet_t = 1.0                             # (nobody to toast: soon again)
        return
    hero.goblet_t = every
    hero.goblet_waves.append([hero.x, hero.y, 0.0, set()])
    scene.effects.append(Effect("goblet_wave", hero.x, hero.y, size=reach))
    scene.effects.append(Effect("toast", hero.x, hero.y - 2, label="A TOAST!"))


def spin_out(scene, hero) -> None:
    """Dancing Shoes: the roll ends in a grand spin: U_SHOES pieces of
    cutlery flung all round, the power's damage each."""
    shell = config.WEAPONS["dancing_cutlery"].shell
    dmg = hero.stats.uniques.get("dancing_shoes", 10.0)
    n = config.U_SHOES
    turn = hero.heading if hero.heading is not None else hero.aim_angle
    for k in range(n):
        a = turn + k * math.tau / n
        scene.projectiles.append(Projectile(hero.x + math.cos(a) * 0.6, hero.y + math.sin(a) * 0.6,
                                            a, shell, owner=hero, damage=dmg))
    scene.effects.append(Effect("swing", hero.x, hero.y, angle=turn, size=1.6, value=360))


def toss_coin(hero, victim) -> None:
    """Gilded Ring: a hit on an elite or a boss tosses a coin out toward
    you (at most every U_GILDED[0] s), to lie U_GILDED[2] s."""
    every, _, life, _, (lo, hi) = config.U_GILDED
    if hero.time - hero.coin_t < every:
        return
    hero.coin_t = hero.time
    a = math.atan2(hero.y - victim.y, hero.x - victim.x) + hero.rng.uniform(-0.9, 0.9)
    r = victim.hit_radius + hero.rng.uniform(lo, hi)
    hero.ring_coins.append([victim.x + math.cos(a) * r, victim.y + math.sin(a) * r, life])


def _gilded(scene, hero, dt: float) -> None:
    """Gilded Ring: walk over a coin to catch it: gilded for U_GILDED[1] s
    (+the power's damage: combat.strike)."""
    _, gilt, _, reach, _ = config.U_GILDED
    keep = []
    for c in hero.ring_coins:
        c[2] -= dt
        if hero.alive and math.hypot(hero.x - c[0], hero.y - c[1]) <= reach + hero.hit_radius:
            hero.ring_gilt_until = hero.time + gilt
            scene.effects.append(Effect("toast", hero.x, hero.y - 2, label="GILDED!"))
            scene._sounds.append("chime")
            continue
        if c[2] > 0:
            keep.append(c)
    hero.ring_coins = keep



# === M31.5: the Ancestor's relics ===========================================================

def _due(scene, hero, attr: str, every: float, reach: float, dt: float) -> bool:
    """A relic's clock (`hero.<attr>`): True when it goes off -- once its
    time is up and an enemy is within `reach` (else it tries again in 1 s)."""
    left = getattr(hero, attr) - dt
    setattr(hero, attr, left)
    if left > 0:
        return False
    if not any(math.hypot(e.x - hero.x, e.y - hero.y) <= reach for e in _foes(scene)):
        setattr(hero, attr, 1.0)
        return False
    setattr(hero, attr, every)
    return True


def _herd(scene, hero, st, dt: float) -> None:
    """Spirit Herd: every U_HERD[0] s (an enemy within [1]), an ochre spirit
    mammoth sets off [2] tiles behind you and charges along your aim to [3]
    tiles past you at [4] tiles/s: the power's damage to each enemy it runs
    through ([5] tiles either side), shoving them [6] tiles aside."""
    every, reach, behind, past, speed, half, shove = config.U_HERD
    foes = _foes(scene)
    for r in hero.herd:
        x0, y0, a = r[0], r[1], r[2]
        r[3] += speed * dt
        ca, sa = math.cos(a), math.sin(a)
        x, y = x0 + ca * r[3], y0 + sa * r[3]
        for e in foes:
            if id(e) in r[4] or math.hypot(e.x - x, e.y - y) > half + e.hit_radius:
                continue
            r[4].add(id(e))
            strike(e, st.uniques.get("spirit_herd", 30.0), hero, a, scene.effects, on_hit=False)
            if e.alive:
                side = 1.0 if (e.x - x0) * -sa + (e.y - y0) * ca >= 0 else -1.0
                push(e, scene.world, -sa * side * shove, ca * side * shove)
            scene.effects.append(Effect("debris", e.x, e.y))
    hero.herd = [r for r in hero.herd if r[3] < behind + past]
    if st.has("spirit_herd") and _due(scene, hero, "herd_t", every, reach, dt):
        a = hero.aim_angle
        hero.herd.append([hero.x - math.cos(a) * behind, hero.y - math.sin(a) * behind, a, 0.0,
                          set()])
        scene._sounds.append("boulder")


def _skull(scene, hero, st, dt: float) -> None:
    """Tyrant Skull: every U_SKULL[0] s (an enemy within [1]) you roar: the
    enemies in a [2]-degree cone along your aim, [3] tiles out, take the
    power's damage and freeze in fear [4] s (a boss is held [5] s)."""
    every, reach, deg, long, fear, held = config.U_SKULL
    if not _due(scene, hero, "skull_t", every, reach, dt):
        return
    a, half = hero.aim_angle, math.radians(deg) / 2
    for e in _foes(scene):
        d = math.hypot(e.x - hero.x, e.y - hero.y)
        if d > long + e.hit_radius:
            continue
        off = (math.atan2(e.y - hero.y, e.x - hero.x) - a + math.pi) % math.tau - math.pi
        if d > e.hit_radius + 0.5 and abs(off) > half:
            continue
        strike(e, st.uniques.get("tyrant_skull", 20.0), hero, a + off, scene.effects, on_hit=False)
        if not e.alive:
            continue
        if getattr(e, "boss", False):
            s = statuses_of(e)
            s.bound = max(s.bound, held)
        else:
            daze(e, fear)
        scene.effects.append(Effect("toast", e.x, e.y - e.hit_radius - 1.0, label="FEAR!"))
    scene.effects.append(Effect("skull_roar", hero.x, hero.y, angle=a, size=long, value=deg))
    scene.effects.append(Effect("toast", hero.x, hero.y - 2, label="ROAR!"))
    scene._sounds.append("boulder")


def _swarm_ring(scene, hero, st, dt: float) -> None:
    """Swarm Ring: every U_SWARM[0] s (an enemy within [1]) a river of
    insects pours from you along your aim, [2] tiles long and [3] either
    side, for [4] s: the power's damage to an enemy in it every [5] s."""
    every, reach, long, half, lasts, sting = config.U_SWARM
    foes = _foes(scene)
    for r in hero.swarms:
        r[3] -= dt
        ca, sa = math.cos(r[2]), math.sin(r[2])
        cds = r[4]
        for k in list(cds):
            cds[k] -= dt
        for e in foes:
            dx, dy = e.x - r[0], e.y - r[1]
            along = dx * ca + dy * sa
            if along < 0 or along > long or abs(-dx * sa + dy * ca) > half + e.hit_radius:
                continue
            if cds.get(id(e), 0.0) > 0:
                continue
            cds[id(e)] = sting
            strike(e, st.uniques.get("swarm_ring", 6.0), hero, r[2], scene.effects, on_hit=False)
    hero.swarms = [r for r in hero.swarms if r[3] > 0]
    if st.has("swarm_ring") and _due(scene, hero, "swarm_t", every, reach, dt):
        hero.swarms.append([hero.x, hero.y, hero.aim_angle, lasts, {}])
        scene._sounds.append("fizzle")


def conch_record(hero, shots, kw: dict) -> None:
    """Echo Conch: the attack just made, to fire again U_CONCH[0] s later
    from where it was made: its shots, or (a pulse weapon) its burst."""
    later, most = config.U_CONCH
    if len(hero.conch) >= most:
        return
    got = [(q.x, q.y, q.angle, q.spec, q.damage, q.mult, q.max_range, q.variant)
           for q in shots if q.alive and not q.conch]
    burst = None
    if hero.weapon is not None and hero.weapon.spec.kind == "pulse":
        burst = (hero.x, hero.y, kw.get("mult", 1.0), kw.get("reach_mult", 1.0))
    if got or burst:
        hero.conch.append([later, got, burst])


def _conch(scene, hero, st, dt: float) -> None:
    """Echo Conch: an attack's echo comes due: its shots again from where
    they left, faded, at the power x their damage (an echo never echoes)."""
    power = st.uniques.get("echo_conch", 0.4) if st is not None else 0.4
    keep = []
    for c in hero.conch:
        c[0] -= dt
        if c[0] > 0:
            keep.append(c)
            continue
        if not hero.alive:
            continue
        for x, y, a, spec, damage, mult, reach, variant in c[1]:
            q = Projectile(x, y, a, spec, owner=hero, damage=damage * power)
            q.mult, q.max_range, q.variant, q.conch = mult, reach, variant, True
            scene.projectiles.append(q)
        if c[2] is not None:
            x, y, mult, reach_mult = c[2]
            combat.pulse(hero, scene.world, scene._actors(), scene.effects, mult=mult * power,
                         reach_mult=reach_mult, origin=(x, y))
    hero.conch = keep


# --- M32.5: the Overseer's relics --------------------------------------------------------

def _overseers_eye(scene, hero, st, dt: float) -> None:
    """Overseer's Eye: every U_EYE[0] s (an enemy within [1]) a searchlight
    sweeps along your aim for [2] s, a cone [3] degrees and [4] tiles long;
    every enemy it lights (nothing between) is SEEN [5] s: it takes the
    power's share more from you (a boss x[6] of it: combat.strike)."""
    from .raycast import first_hit
    every, reach, secs, deg, long, seen_s, _ = config.U_EYE
    if hero.eye_sweep > 0:
        hero.eye_sweep = max(0.0, hero.eye_sweep - dt)
        half = math.radians(deg) / 2
        until = hero.time + seen_s
        for e in _foes(scene):
            if math.hypot(e.x - hero.x, e.y - hero.y) > long + e.hit_radius:
                continue
            off = (math.atan2(e.y - hero.y, e.x - hero.x) - hero.aim_angle + math.pi) % math.tau - math.pi
            if abs(off) > half or first_hit(scene.world.tile_at, hero.x, hero.y, e.x, e.y) is not None:
                continue
            e.__dict__.setdefault("seen_by", {})[id(hero)] = until
        return
    if st.has("overseers_eye") and _due(scene, hero, "eye_t", every, reach, dt):
        hero.eye_sweep = secs
        scene._sounds.append("hex")


def _cell_key(scene, hero, st, dt: float) -> None:
    """Cell Key: every U_CELL[0] s it's ready, and your next hit (combat.
    _relic_on_hit) locks the enemy in a closed square ring of laser bars
    [1] tiles round ([2] for one bigger than [3] tiles) for the power's s:
    it can't get out, nothing gets in (the bars never land on anyone). A
    boss is held in place [4] s."""
    every, small, big, bigger, hold = config.U_CELL
    e = hero.cell_lock
    if e is not None:
        hero.cell_lock = None
        if e.alive:
            _lock_up(scene, hero, e, st)
    if not hero.cell_ready and st.has("cell_key"):
        hero.cell_t -= dt
        if hero.cell_t <= 0:
            hero.cell_ready = True
            hero.cell_t = every


def _lock_up(scene, hero, e, st) -> None:
    every, small, big, bigger, hold = config.U_CELL
    if getattr(e, "boss", False):
        s = statuses_of(e)
        s.bound = max(s.bound, hold)
        scene.effects.append(Effect("toast", e.x, e.y - e.hit_radius - 1.0, label="HELD!"))
        return
    from ..ai.panopticon import _ring_tiles
    from ..world import tiles
    w = scene.world
    if not hasattr(w, "set_tile"):
        return
    n = big if e.hit_radius > bigger else small
    actors = [p.hero for p in scene.players if p.alive] + [q for q in scene.enemies if q.alive]
    life = st.uniques.get("cell_key", 3.0) if st is not None else 3.0
    for tx, ty in _ring_tiles(w, e.x, e.y, n, actors):
        old = w.tile_at(tx, ty)
        w.set_tile(tx, ty, tiles.CELL_BARS)
        scene.zones.append(Zone("stake", tx + 0.5, ty + 0.5, 0.0, life, 999.0, 0.0, None,
                                restore=(tx, ty, old)))
    scene.effects.append(Effect("toast", e.x, e.y - 1.5, label="LOCKED UP!"))
    scene._sounds.append("zap")


def _black_box(scene, hero, st, dt: float) -> None:
    """Black Box: it keeps what hurt you in the last U_BOX[1] s (Character.
    take_damage); every [0] s -- or at once when you drop below [2] of your
    max HP (if it hasn't rewound in the last [1] s), the clock starting
    again -- it rewinds: you heal the power's share of it (once: what's
    healed is forgotten)."""
    every, window, low = config.U_BOX
    hero.box_log = [(t, a) for t, a in hero.box_log if hero.time - t <= window]
    below = hero.hp < hero.max_hp * low
    dropped = below and not hero.box_low and hero.box_t <= every - window
    hero.box_low = below
    hero.box_t -= dt
    if hero.box_t > 0 and not dropped:
        return
    hero.box_t = every
    got = sum(a for _, a in hero.box_log)
    hero.box_log = []
    if got <= 0:
        return
    healed = hero.heal(got * st.uniques.get("black_box", 0.4))
    if healed > 0:
        scene.effects.append(Effect("toast", hero.x, hero.y - 2.0, label=f"REWIND +{round(healed)}"))
        scene.effects.append(Effect("spark_burst", hero.x, hero.y, size=1.0))
