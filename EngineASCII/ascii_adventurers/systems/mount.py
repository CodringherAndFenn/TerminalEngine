"""
systems/mount.py -- riding (P6, design/BOSSES.md 24.4).

Every hero can whistle for their own mount (config.HERO_MOUNTS: the
wizard's flying carpet, the dwarf's war ram, the bard's donkey, the
princess's pony, the huntress's stag) with the mount key (Q / gamepad Y):

  calling   MOUNT_CALL_TIME s after the whistle it's there and the hero is
            riding. Attacking or rolling meanwhile calls it off.
  riding    MOUNT_SPEED faster (plus the Stable's levels), on top of
            everything else that makes the hero faster. It's for travel:
            attacking or rolling hops the hero off (the attack or roll
            still happens); a hero whose weapon plays by itself (the bard)
            stays quiet while riding. Spells keep going.
            The mount key again: off, and it can be called straight back.
  thrown    any hit throws the hero off; the mount can't be called again
            for MOUNT_THROWN s (less with the Stable).
  arenas    no riding in a boss's arena: entering one hops the hero off,
            and the mount can't be called in one.

All of it is per hero and runs inside the simulation step (deterministic).
Drawing: render/mounts.py.
"""

from __future__ import annotations

from .. import config
from ..entities.effects import Effect


def mount_of(hero) -> str:
    """The mount this hero calls (by its sprite: every hero has one), or ""
    with mounts switched off (config.MOUNTS_ON)."""
    return config.HERO_MOUNTS.get(hero.spec.sprite, "") if config.MOUNTS_ON else ""


def thrown_cooldown(hero) -> float:
    st = hero.stats
    less = st.mount_cooldown if st is not None else 0.0
    return max(config.MOUNT_MIN_COOLDOWN, config.MOUNT_THROWN - less)


def riding_mult(hero) -> float:
    st = hero.stats
    return 1 + config.MOUNT_SPEED + (st.mount_speed if st is not None else 0.0)


def in_arena(scene, hero) -> bool:
    quests = getattr(scene, "quests", None)
    if quests is None:
        return False
    return any(s.lair is not None and s.lair.inside(hero.x, hero.y)
               for s in quests.states.values())


def dismount(scene, p, cooldown: float = 0.0, label: str = "") -> None:
    hero = p.hero
    if not hero.mount and hero.mount_call <= 0:
        return
    riding = bool(hero.mount)
    hero.mount = ""
    hero.mount_call = 0.0
    hero.mount_mult = 1.0
    hero.mount_cd = max(hero.mount_cd, cooldown)
    if riding:
        scene.effects.append(Effect("roll_dust", hero.x, hero.y + hero.hit_radius * 0.5))
    if label:
        scene.effects.append(Effect("toast", hero.x, hero.y - 2, label=label))


def step(scene, p, inp, dt: float) -> None:
    """One step of a living player's mount, before the roll and the move:
    the key, the whistle's countdown, being thrown, arenas, the speed."""
    hero = p.hero
    hero.mount_cd = max(0.0, hero.mount_cd - dt)
    hit = hero.since_hit < hero.mount_seen       # (since_hit only ever drops on a hit)
    hero.mount_seen = hero.since_hit
    kind = mount_of(hero)
    if not kind:
        return
    arena = in_arena(scene, hero)
    if hero.mount:
        if hit:
            dismount(scene, p, thrown_cooldown(hero), "THROWN!")
        elif arena:
            dismount(scene, p, 0.0, "NO MOUNTS IN HERE")
        elif inp.mount:
            dismount(scene, p)
        elif inp.roll or (inp.fire and not hero.weapon.spec.auto):
            dismount(scene, p)                   # (the roll or attack goes ahead)
    elif hero.mount_call > 0:
        if inp.mount or inp.roll or inp.fire or hit or arena:
            dismount(scene, p, thrown_cooldown(hero) if hit else 0.0)
        else:
            hero.mount_call -= dt
            if hero.mount_call <= 0:
                hero.mount_call = 0.0
                hero.mount = kind
                scene.effects.append(Effect("roll_dust", hero.x, hero.y + hero.hit_radius * 0.5))
    elif inp.mount:
        if hero.mount_cd > 0:
            scene.effects.append(Effect("toast", hero.x, hero.y - 2,
                                        label=f"MOUNT IN {hero.mount_cd:.0f}s"))
        elif arena:
            scene.effects.append(Effect("toast", hero.x, hero.y - 2, label="NO MOUNTS IN HERE"))
        else:
            hero.mount_call = config.MOUNT_CALL_TIME
            if p.local:
                scene._sounds.append("whistle")
    hero.mount_mult = riding_mult(hero) if hero.mount else 1.0
    if abs(hero.vx) > 0.5:                    # (up/down or standing: keeps its last way)
        hero.mount_left = hero.vx < 0
    elif not hero.mount:
        hero.mount_left = hero.facing_left


def meter(hero) -> tuple | None:
    """The HUD's meter row for the mount: the whistle's wait, or the wait
    after a throw (label, 0..1 full, alarm), or None."""
    if hero.mount_call > 0:
        return ("MNT", 1 - hero.mount_call / config.MOUNT_CALL_TIME, False)
    if hero.mount_cd > 0 and not hero.mount:
        return ("MNT", 1 - hero.mount_cd / thrown_cooldown(hero), False)
    return None
