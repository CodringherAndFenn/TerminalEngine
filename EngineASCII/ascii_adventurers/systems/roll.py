"""
systems/roll.py -- the dodge roll (M18): every hero's quick evasive dash.

Shift (gamepad B or LB) rolls ROLL_DISTANCE tiles in ROLL_TIME s, in the
direction the hero is walking -- or toward the aim when standing still.
For the whole roll the hero can't be hit (entities/character.py: not
hittable, and take_damage ignores everything), but walls still stop it.

Charges. A hero has ROLL_CHARGES (+ Extra Roll) charges; a roll spends
one, and spent charges come back one at a time, each after ROLL_COOLDOWN
s (Quick Recovery shortens it). The clock toward the next charge starts
as soon as a roll does, and Close Call winds it on.

Roll cards (config.CARDS section 6.10):
  Riposte         the first attack within RIPOSTE_WINDOW s of a roll's start
                  is a sure crit (systems/run_rules.attack_mods);
  Slipstream      faster walking for a while after the roll;
  Close Call      every enemy shot that passes through the rolling hero
                  winds the recharge on by CLOSE_CALL s (each shot once);
  Scorched Trail  burning patches (systems/zones.py "trail") every
                  TRAIL_SPACING tiles along the roll;
  Blink (wizard)  no slide: the hero is there at once (as far as walls
                  allow) and a shock nova goes off where they land -- the
                  i-frames still last ROLL_TIME;
  Backflip (huntress)  a fan of arrows toward the aim as the roll starts;
  Shoulder Charge (dwarf)  enemies the roll runs into are hit and shoved
                  along the roll, each once per roll;
  Pirouette (princess, P4)  a ring of her colors all round her as the
                  roll starts;
  Drop the Beat (bard)  a free, stronger beat as the roll ends.

The feet gear's tricks (M28.2c, design/GEAR.md 17.3) live here too, by
the piece: Fencer's Boots (Riposte's count), Windrunners (Jet stream,
Afterimage), Hairsbreadth (Graze, Deflect, Untouchable), Ashwalkers
(Bellows, Firewalk; Creeping fire is run_rules), Wingheel (Quickstep's
speed), Phasewalkers (Displacement, Swap, Blink storm), Ramhorn (Bowling,
Battering ram, Rampage), Tumbler (Double flip, Quick draw, Aerial's
timer), Dancing Slippers (Encore spin, Dizzy, Prima) and Stompers (Double
drop, Crowd surf, Amplifier).

Everything here runs inside the simulation step and stays deterministic
(randomness from the hero's seeded dice).
"""

from __future__ import annotations

import math

from .. import config
from ..entities.actor import Actor
from ..entities.effects import Effect
from .collision import hull_hits_solid
from .combat import (_may_hurt, attack, crush_tile, fire, push, segment_circle_t, strike,
                     volley)
from .statuses import has, inflict
from .zones import Zone

ROLL_SOUND = "swing"          # a soft whoosh
BLINK_SOUND = "zap"


class Afterimage(Actor):
    """Windrunners +6: an image of the hero left where a roll started.
    Enemies go for it instead (ai/brain.Brain._pick_player); shots that
    reach it stop there, harmlessly."""
    faction = "player"

    def __init__(self, hero, life: float) -> None:
        super().__init__(1, hero.hit_radius)
        self.x, self.y = hero.x, hero.y
        self.hero = hero
        self.left = life
        self.invulnerable = True
        self.vx = self.vy = 0.0

    @property
    def alive(self) -> bool:
        return self.left > 0


def roll_direction(hero, move_x: float, move_y: float) -> tuple[float, float]:
    """Where a roll goes: the walking direction, else the aim."""
    n = math.hypot(move_x, move_y)
    if n > 1e-6:
        return move_x / n, move_y / n
    return math.cos(hero.aim_angle), math.sin(hero.aim_angle)


def recharge(hero, dt: float) -> None:
    """Spent charges come back one at a time."""
    st = hero.stats
    most = st.max_rolls if st is not None else config.ROLL_CHARGES
    every = st.roll_recharge if st is not None else config.ROLL_COOLDOWN
    if hero.roll_charges >= most:
        hero.roll_charges = most
        hero.roll_recharge = 0.0
        return
    if getattr(hero, "storm_t", 0.0) > 0:       # (Phasewalkers +9: not while a storm's on)
        return
    # Irradiated (M24.1, the Fallout King): it recharges slower.
    hero.roll_recharge += dt * (config.IRRADIATED[3] if getattr(hero, "irradiated", 0) > 0 else 1.0)
    while hero.roll_recharge >= every and hero.roll_charges < most:
        hero.roll_recharge -= every
        hero.roll_charges += 1
    if hero.roll_charges >= most:
        hero.roll_recharge = 0.0


def recharge_frac(hero) -> float:
    """0..1 toward the next charge (1 when every charge is ready)."""
    st = hero.stats
    most = st.max_rolls if st is not None else config.ROLL_CHARGES
    if hero.roll_charges >= most:
        return 1.0
    every = st.roll_recharge if st is not None else config.ROLL_COOLDOWN
    return min(1.0, hero.roll_recharge / every) if every > 0 else 1.0


def step(scene, p, inp, dt: float) -> None:
    """One simulation step of a living player's roll: recharge, maybe start
    one (the player pressed roll), and the roll cards' timers. Runs before
    the hero moves; the slide itself is Character.move."""
    hero = p.hero
    st = hero.stats
    hero.storm_t = max(0.0, hero.storm_t - dt)
    if hero.storm_t <= 0:
        hero.storm_blinks = 0
    recharge(hero, dt)
    hero.riposte = max(0.0, hero.riposte - dt)
    if hero.riposte <= 0:
        hero.riposte_left = 0
    hero.untouchable = max(0.0, hero.untouchable - dt)
    hero.aerial = max(0.0, hero.aerial - dt)
    hero.quick = [t - dt for t in hero.quick if t - dt > 0]
    hero.slipstream = max(0.0, hero.slipstream - dt)
    if hero.slipstream > 0 and st is not None and st.has("slipstream+9") \
            and math.hypot(inp.move_x, inp.move_y) > 1e-6:
        hero.slipstream = max(hero.slipstream, config.JET_STREAM)   # Jet stream
    hero.speed_mult = (1 + config.SLIPSTREAM[0] if hero.slipstream > 0 else 1.0) \
        + config.QUICKSTEP[0] * len(hero.quick)                       # (Quickstep)
    if hero.getaway > 0:
        hero.speed_mult += config.CLEAN_GETAWAY[0]                    # (Spotless Tunic +3)
    for im in hero.images:
        im.left -= dt
    hero.images = [im for im in hero.images if im.alive]
    for amp in hero.amps:
        amp[2] -= dt
    hero.amps = [a for a in hero.amps if a[2] > 0]
    if getattr(hero, "encased", 0) > 0:       # (M24.2: frozen solid -- a roll breaks the ice)
        if inp.roll:
            hero.encase_breaks += 1
        return
    if inp.roll and not hero.rolling and (hero.roll_charges > 0 or hero.storm_blinks > 0):
        start(scene, p, inp.move_x, inp.move_y)
    elif hero.rolling and st is not None:
        _during(scene, p)


def after_move(scene, p, was_rolling: bool, x0: float, y0: float) -> None:
    """After the hero moved this step (from (x0, y0)): the roll cards that
    act along the path, and those that act as a roll ends."""
    hero = p.hero
    st = hero.stats
    if not was_rolling:
        return
    if hero.roll_steps % config.ROLL_DUST_EVERY == 0:
        scene.effects.append(Effect("roll_dust", hero.x, hero.y + hero.hit_radius * 0.5))
    hero.roll_steps += 1
    if st is None:
        return
    if st.has("scorched_trail"):
        _trail(scene, p, math.hypot(hero.x - x0, hero.y - y0))
        if st.has("scorched_trail+6"):
            _bellows(scene, p)
    if st.has("drop_the_beat+6"):                # Crowd surf: who it rolls past
        reach = config.CROWD_SURF[0]
        for a in scene.enemies:
            if a.alive and a.hittable and math.hypot(a.x - hero.x, a.y - hero.y) \
                    <= reach + a.hit_radius + hero.hit_radius:
                hero.surfed.add(id(a))
    if not hero.rolling:                         # it ended this step
        _ended(scene, p)


def _ended(scene, p) -> None:
    """The roll cards (and feet tricks) that act as a roll ends."""
    hero = p.hero
    st = hero.stats
    sounds = []
    if st.has("slipstream"):
        hero.slipstream = config.SLIPSTREAM[1]
    if st.has("close_call+9") and hero.roll_grazes >= config.UNTOUCHABLE[0]:
        hero.untouchable = config.UNTOUCHABLE[1]                      # Untouchable
    if st.has("backflip+3"):
        sounds += _backflip(scene, p)                                 # Double flip
    if st.has("backflip+9"):
        hero.aerial = config.AERIAL[1]                                # Aerial
    if st.has("pirouette+3"):
        sounds += _pirouette(scene, p, config.ENCORE_SPIN)            # Encore spin
    if st.has("drop_the_beat") and hero.weapon.spec.kind == "pulse":
        surf = 0.0
        if st.has("drop_the_beat+6"):                                 # Crowd surf
            _, per, most = config.CROWD_SURF
            surf = min(most, per * len(hero.surfed))
        sounds += attack(hero, scene.world, scene.projectiles, scene.effects, scene._actors(),
                         mult=config.DROP_THE_BEAT * (1 + surf))
        if st.has("drop_the_beat+9"):                                 # Amplifier
            hero.amps.append([hero.x, hero.y, config.AMPLIFIER[0]])
    if p.local:
        scene._sounds.extend(sounds)


def start(scene, p, move_x: float, move_y: float) -> None:
    hero = p.hero
    st = hero.stats
    storm = hero.storm_blinks > 0                # (Phasewalkers +9: a free blink)
    if storm:
        hero.storm_blinks -= 1
    else:
        hero.roll_charges -= 1
    hero.roll_dir = roll_direction(hero, move_x, move_y)
    hero.roll_t = config.ROLL_TIME
    hero.roll_speed = config.ROLL_DISTANCE / config.ROLL_TIME
    if st is not None and st.has("scorched_trail+9"):
        hero.roll_speed *= config.FIREWALK[0]                         # Firewalk
    hero.roll_passed = set()
    hero.roll_trail = 0.0
    hero.roll_steps = 0
    hero.rolls += 1
    hero.roll_grazes = 0
    hero.rampage = 0.0
    hero.surfed = set()
    scene.effects.append(Effect("roll_dust", hero.x, hero.y + hero.hit_radius * 0.5))
    sounds = [ROLL_SOUND]
    if st is not None:
        if st.has("riposte"):
            hero.riposte = config.RIPOSTE_WINDOW
            hero.riposte_left = config.SECOND_THRUST if st.has("riposte+6") else 1
        if st.has("slipstream+6"):                                    # Afterimage
            hero.images.append(Afterimage(hero, config.AFTERIMAGE))
        if st.has("backflip"):
            sounds += _backflip(scene, p)
        if st.has("blink"):
            sounds += _blink(scene, p)
            if st.has("blink+9") and not storm:                       # Blink storm
                hero.storm_blinks, hero.storm_t = config.BLINK_STORM[0] - 1, config.BLINK_STORM[1]
        if st.has("pirouette"):
            n = config.PIROUETTE[0]
            if st.has("pirouette+9"):                                 # Prima
                reach, most = config.PRIMA
                n = min(most, n + sum(1 for a in scene.enemies if a.alive and a.hittable
                                      and math.hypot(a.x - hero.x, a.y - hero.y) <= reach))
            sounds += _pirouette(scene, p, n)
        if st.has("drop_the_beat+3") and hero.weapon.spec.kind == "pulse":   # Double drop
            sounds += attack(hero, scene.world, scene.projectiles, scene.effects, scene._actors(),
                             mult=config.DROP_THE_BEAT)
    if p.local:
        scene._sounds.extend(sounds)


def _backflip(scene, p) -> list[str]:
    """Backflip: a fan of arrows toward the aim (Tumbler Boots +6, Quick
    draw: with double the crit chance)."""
    hero = p.hero
    if hero.weapon.spec.shell is None:
        return []
    n, fan, mult = config.BACKFLIP
    before = len(scene.projectiles)
    sounds = fire(hero, scene.world, scene.projectiles, scene.effects, mult=mult,
                  extra_pellets=max(0, n - hero.weapon.spec.pellets),
                  spread_add=max(0.0, fan - hero.weapon.spec.spread_deg))
    if hero.stats.has("backflip+6"):
        for q in scene.projectiles[before:]:
            q.crit_x = config.QUICK_DRAW
    return sounds


def _pirouette(scene, p, n: int) -> list[str]:
    """Pirouette (P4): a ring of `n` of her colors, in turn, all round her
    (Dancing Slippers +6, Dizzy: what they hit aims off)."""
    hero = p.hero
    spec = hero.weapon.spec
    if spec.shell is None or spec.shell.look != "prism":
        return []
    before = len(scene.projectiles)
    sounds = volley(hero, scene.world, scene.projectiles, scene.effects,
                    hero.aim_angle, n, 360.0 * (n - 1) / n, spec.shell, spec.tags,
                    mult=config.PIROUETTE[1])
    if hero.stats.has("pirouette+6"):
        for q in scene.projectiles[before:]:
            q.dizzy = True
    return sounds


def _blink(scene, p) -> list[str]:
    """Blink: arrive at once, as far along the roll as walls allow (checked
    every BLINK_STEP tiles, so it never jumps a thin wall), then a shock
    nova where the hero lands."""
    hero = p.hero
    dist, radius, damage = config.BLINK
    dx, dy = hero.roll_dir
    scene.effects.append(Effect("blink", hero.x, hero.y, size=1.0))
    x, y = hero.x, hero.y
    steps = max(1, math.ceil(dist / config.BLINK_STEP))
    for i in range(1, steps + 1):
        nx, ny = hero.x + dx * dist * i / steps, hero.y + dy * dist * i / steps
        if hull_hits_solid(scene.world, nx, ny, 0.0, hero.half, hero.half):
            break
        x, y = nx, ny
    x0, y0 = hero.x, hero.y
    hero.walked += math.hypot(x - hero.x, y - hero.y)
    hero.roll_speed = 0.0                        # already there
    st = hero.stats
    if st.has("blink+6"):                        # Swap: onto an enemy, change places
        near = [a for a in scene.enemies if a.alive and a.hittable and not getattr(a, "boss", False)
                and math.hypot(a.x - x, a.y - y) <= config.SWAP + a.hit_radius]
        if near:
            e = min(near, key=lambda a: math.hypot(a.x - x, a.y - y))
            if not hull_hits_solid(scene.world, e.x, e.y, 0.0, hero.half, hero.half):
                x, y = e.x, e.y
                e.x, e.y = x0, y0
                scene.effects.append(Effect("blink", x0, y0, size=1.0))
    hero.x, hero.y = x, y
    _nova(scene, hero, x, y, radius, damage)
    if st.has("blink+3"):                        # Displacement
        _nova(scene, hero, x0, y0, radius, damage * config.DISPLACEMENT)
    return [BLINK_SOUND]


def _nova(scene, hero, x: float, y: float, radius: float, damage: float) -> None:
    scene.effects.append(Effect("blink", x, y, size=radius))
    for a in scene._actors():
        if not a.hittable or not _may_hurt(hero, a):
            continue
        if math.hypot(a.x - x, a.y - y) > radius + a.hit_radius:
            continue
        strike(a, damage, hero, math.atan2(a.y - y, a.x - x), scene.effects,
               ("lightning", "arcane"))
        if a.alive:
            inflict(a, "shock", hero)


def _during(scene, p) -> None:
    """Mid-roll cards that act before the slide (Shoulder Charge)."""
    hero = p.hero
    st = hero.stats
    if not st.has("shoulder_charge"):
        return
    damage, reach, shove = config.SHOULDER_CHARGE
    dx, dy = hero.roll_dir
    if st.has("shoulder_charge+6") and hero.roll_speed > 0:
        _ram(scene, p)                                                # Battering ram
    actors = scene._actors()
    for a in actors:
        if id(a) in hero.roll_passed or not a.hittable or not _may_hurt(hero, a):
            continue
        if math.hypot(a.x - hero.x, a.y - hero.y) > hero.hit_radius + reach + a.hit_radius:
            continue
        hero.roll_passed.add(id(a))
        strike(a, damage, hero, math.atan2(dy, dx), scene.effects, ("physical",))
        scene.effects.append(Effect("impact", a.x, a.y, math.atan2(dy, dx)))
        if a.alive:
            push(a, scene.world, dx * shove, dy * shove)
            if st.has("shoulder_charge+3"):
                _bowl(scene, hero, a, actors, dx * shove, dy * shove)  # Bowling
        if st.has("shoulder_charge+9") and hero.rampage < config.RAMPAGE[1] \
                and hero.roll_speed > 0:                              # Rampage
            hero.rampage += 1
            hero.roll_t += config.RAMPAGE[0] / hero.roll_speed
        if p.local:
            scene._sounds.append("hit")


def _bowl(scene, hero, a, actors, sx: float, sy: float) -> None:
    """Bowling: an enemy shoved into others knocks them on too; both take
    BOWLING (each pin once a roll)."""
    for b in actors:
        if b is a or not b.hittable or not _may_hurt(hero, b) or ("bowl", id(b)) in hero.roll_passed:
            continue
        if math.hypot(b.x - a.x, b.y - a.y) > a.hit_radius + b.hit_radius + 0.2:
            continue
        hero.roll_passed.add(("bowl", id(b)))
        angle = math.atan2(sy, sx)
        for victim in (a, b):
            if victim.alive:
                strike(victim, config.BOWLING, hero, angle, scene.effects, ("physical",),
                       on_hit=False)
        scene.effects.append(Effect("impact", b.x, b.y, angle))
        if b.alive:
            push(b, scene.world, sx, sy)


def _ram(scene, p) -> None:
    """Battering ram: whatever breakable stands just ahead of the charge
    (walls, trees, crates) is smashed before the hero gets there."""
    hero = p.hero
    dx, dy = hero.roll_dir
    hw, hh = hero.half / config.TILE_PX_W, hero.half / config.TILE_PX_H   # (half is pixels)
    reach = abs(dx) * hw + abs(dy) * hh
    ahead = reach + hero.roll_speed / config.SIM_HZ + 0.1
    seen = set()
    for side in (-0.98, -0.5, 0.0, 0.5, 0.98):            # (across the hull's whole width)
        px = hero.x + dx * ahead - dy * hw * side
        py = hero.y + dy * ahead + dx * hh * side
        tx, ty = math.floor(px), math.floor(py)
        if (tx, ty) in seen:
            continue
        seen.add((tx, ty))
        tile = scene.world.tile_at(tx, ty)
        if tile.solid and tile.destructible:
            sound = crush_tile(scene.world, tx, ty, config.BATTERING_RAM, scene.effects)
            if sound and p.local:
                scene._sounds.append(sound)


def _trail(scene, p, moved: float) -> None:
    """Scorched Trail: a burning patch every TRAIL_SPACING tiles rolled
    (`moved`: this step's distance), the first one straight away."""
    hero = p.hero
    st = hero.stats
    hero.roll_trail -= moved
    if hero.roll_trail > 1e-9 and hero.roll_steps > 1:
        return
    hero.roll_trail = config.TRAIL_SPACING
    life = config.FIREWALK[1] if st.has("scorched_trail+9") else config.TRAIL_LIFE
    z = Zone("trail", hero.x, hero.y, config.TRAIL_RADIUS, life * st.duration_scale,
             config.TRAIL_EVERY, 0.0, hero, (config.STATUSES["burn"].tag,), "burn")
    z.roll = hero.rolls                          # (Bellows: which roll laid it)
    z.crept = False                              # (Creeping fire: not yet)
    scene.zones.append(z)


def _bellows(scene, p) -> None:
    """Bellows: rolling across one of your patches from an earlier roll
    makes it flare -- BELLOWS to everything on it (each patch once a roll)."""
    hero = p.hero
    for z in scene.zones:
        if z.kind != "trail" or z.source is not hero or getattr(z, "roll", hero.rolls) == hero.rolls \
                or z.age >= z.life or id(z) in hero.roll_passed:
            continue
        if math.hypot(z.x - hero.x, z.y - hero.y) > z.radius + hero.hit_radius:
            continue
        hero.roll_passed.add(id(z))
        scene.effects.append(Effect("explosion", z.x, z.y))
        for a in scene._actors():
            if a.hittable and _may_hurt(hero, a) \
                    and math.hypot(a.x - z.x, a.y - z.y) <= z.radius + a.hit_radius:
                strike(a, config.BELLOWS, hero, None, scene.effects, ("fire",), on_hit=False)


def close_calls(players, projectiles, dt: float) -> None:
    """Close Call: every enemy shot that passed through a rolling hero this
    step (its path since the last step crossed the hero) winds the
    recharge on, each shot once per roll."""
    for p in players:
        hero = p.hero
        if not (p.alive and hero.rolling and hero.stats is not None
                and hero.stats.has("close_call")):
            continue
        for s in projectiles:
            if not s.alive or s.spec.lob or s.hold > 0 or id(s) in hero.roll_passed:
                continue
            owner = s.owner
            if owner is None or getattr(owner, "faction", "") == "player":
                continue
            back = s.spec.speed * dt
            x0, y0 = s.x - s.dir_x * back, s.y - s.dir_y * back
            if segment_circle_t(x0, y0, s.x - x0, s.y - y0, hero.x, hero.y,
                                hero.hit_radius + s.size) is None:
                continue
            hero.roll_passed.add(id(s))
            hero.roll_recharge += config.CLOSE_CALL
            recharge(hero, 0.0)
            hero.roll_grazes += 1                      # (Hairsbreadth +9 counts them)
            st = hero.stats
            if st.has("close_call+3"):
                hero.heal(config.GRAZE)                # Graze
            if st.has("close_call+6"):
                _deflect(s, hero)                      # Deflect


def _deflect(s, hero) -> None:
    """Deflect: the shot turns round at whoever fired it, as the hero's,
    at DEFLECT of its damage (plain damage: none of the hero's bonuses)."""
    shooter = s.owner
    if getattr(shooter, "alive", False):
        angle = math.atan2(shooter.y - s.y, shooter.x - s.x)
        reach = math.hypot(shooter.x - s.x, shooter.y - s.y) + 2.0
    else:
        angle, reach = s.angle + math.pi, s.max_range
    s.owner = hero
    s.angle = s.base_angle = angle
    s.dir_x, s.dir_y = math.cos(angle), math.sin(angle)
    s.damage *= config.DEFLECT
    s.plain = True
    s.travelled = 0.0
    s.max_range = max(reach, s.spec.max_range * 0.5)
    s.hit = set()
    s.seek_turn = 0.0
    s.curve = 0.0
