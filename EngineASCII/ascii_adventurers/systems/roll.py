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
  Prism Dash (princess)  a trail like Scorched Trail, each patch a random
                  status;
  Drop the Beat (bard)  a free, stronger beat as the roll ends.

Everything here runs inside the simulation step and stays deterministic
(randomness from the hero's seeded dice).
"""

from __future__ import annotations

import math

from .. import config
from ..entities.effects import Effect
from .collision import hull_hits_solid
from .combat import _may_hurt, attack, fire, push, segment_circle_t, strike
from .statuses import inflict
from .zones import Zone

ROLL_SOUND = "swing"          # a soft whoosh
BLINK_SOUND = "zap"


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
    recharge(hero, dt)
    hero.riposte = max(0.0, hero.riposte - dt)
    hero.slipstream = max(0.0, hero.slipstream - dt)
    hero.speed_mult = 1 + config.SLIPSTREAM[0] if hero.slipstream > 0 else 1.0
    if getattr(hero, "encased", 0) > 0:       # (M24.2: frozen solid -- a roll breaks the ice)
        if inp.roll:
            hero.encase_breaks += 1
        return
    if inp.roll and not hero.rolling and hero.roll_charges > 0:
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
    if st.has("scorched_trail") or st.has("prism_dash"):
        _trail(scene, p, math.hypot(hero.x - x0, hero.y - y0))
    if not hero.rolling:                         # it ended this step
        if st.has("slipstream"):
            hero.slipstream = config.SLIPSTREAM[1]
        if st.has("drop_the_beat") and hero.weapon.spec.kind == "pulse":
            sounds = attack(hero, scene.world, scene.projectiles, scene.effects, scene._actors(),
                            mult=config.DROP_THE_BEAT)
            if p.local:
                scene._sounds.extend(sounds)


def start(scene, p, move_x: float, move_y: float) -> None:
    hero = p.hero
    st = hero.stats
    hero.roll_charges -= 1
    hero.roll_dir = roll_direction(hero, move_x, move_y)
    hero.roll_t = config.ROLL_TIME
    hero.roll_speed = config.ROLL_DISTANCE / config.ROLL_TIME
    hero.roll_passed = set()
    hero.roll_trail = 0.0
    hero.roll_steps = 0
    scene.effects.append(Effect("roll_dust", hero.x, hero.y + hero.hit_radius * 0.5))
    sounds = [ROLL_SOUND]
    if st is not None:
        if st.has("riposte"):
            hero.riposte = config.RIPOSTE_WINDOW
        if st.has("backflip") and hero.weapon.spec.shell is not None:
            n, fan, mult = config.BACKFLIP
            sounds += fire(hero, scene.world, scene.projectiles, scene.effects, mult=mult,
                           extra_pellets=max(0, n - hero.weapon.spec.pellets),
                           spread_add=max(0.0, fan - hero.weapon.spec.spread_deg))
        if st.has("blink"):
            sounds += _blink(scene, p)
    if p.local:
        scene._sounds.extend(sounds)


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
    hero.walked += math.hypot(x - hero.x, y - hero.y)
    hero.x, hero.y = x, y
    hero.roll_speed = 0.0                        # already there
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
    return [BLINK_SOUND]


def _during(scene, p) -> None:
    """Mid-roll cards that act before the slide (Shoulder Charge)."""
    hero = p.hero
    if not hero.stats.has("shoulder_charge"):
        return
    damage, reach, shove = config.SHOULDER_CHARGE
    dx, dy = hero.roll_dir
    for a in scene._actors():
        if id(a) in hero.roll_passed or not a.hittable or not _may_hurt(hero, a):
            continue
        if math.hypot(a.x - hero.x, a.y - hero.y) > hero.hit_radius + reach + a.hit_radius:
            continue
        hero.roll_passed.add(id(a))
        strike(a, damage, hero, math.atan2(dy, dx), scene.effects, ("physical",))
        scene.effects.append(Effect("impact", a.x, a.y, math.atan2(dy, dx)))
        if a.alive:
            push(a, scene.world, dx * shove, dy * shove)
        if p.local:
            scene._sounds.append("hit")


def _trail(scene, p, moved: float) -> None:
    """Scorched Trail / Prism Dash: a patch every TRAIL_SPACING tiles
    rolled (`moved`: this step's distance), the first one straight away."""
    hero = p.hero
    st = hero.stats
    hero.roll_trail -= moved
    if hero.roll_trail > 1e-9 and hero.roll_steps > 1:
        return
    hero.roll_trail = config.TRAIL_SPACING
    kinds = []
    if st.has("scorched_trail"):
        kinds.append("burn")
    if st.has("prism_dash"):
        options = config.PRISM_DASH_STATUSES
        kinds.append(options[int(hero.rng.random() * len(options)) % len(options)])
    for status in kinds:
        scene.zones.append(Zone("trail", hero.x, hero.y, config.TRAIL_RADIUS,
                                config.TRAIL_LIFE * hero.stats.duration_scale, config.TRAIL_EVERY,
                                0.0, hero, (config.STATUSES[status].tag,), status))


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
