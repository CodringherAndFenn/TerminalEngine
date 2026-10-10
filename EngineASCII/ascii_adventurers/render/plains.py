"""
render/plains.py -- drawing the plains' P7 enemies (ai/plains.py): their
letter-art bodies (render/plains_art.py), walking by distance like the
heroes, and their tells:

  * a red "!" over the head while one winds up (it blinks faster as the
    attack nears) -- the chasers, the straw golem, the shieldbearer's bash;
  * a dotted line along a coming charge: the bull scraping, the lancer
    lowering its lance, the hawk lining up its dive;
  * the war drummer's ring (pulsing on the beat), and a gold star over the
    elites (the bull, the shieldbearer);
  * a hawk's shadow on the ground, under it.
"""

from __future__ import annotations

import math

from .. import config, palette
from ..ai.plains import Bull, Drummer, Hawk, Lancer, PlainsCreature
from .ascii_fx import _Batch, draw_hp_bar
from .characters import draw_character
from .mounts import draw_rider, gallop_frame
from . import plains_art  # noqa: F401  (adds the pictures to characters.ART)


def _frame(e) -> int:
    if not getattr(e, "moving", False):
        return 0
    return int(e.walked * config.WALK_STEPS_PER_TILE) % 4


def _line(batch, camera, x0, y0, angle, length, color, step=1.2) -> None:
    ca, sa = math.cos(angle), math.sin(angle)
    k = step
    while k <= length:
        x, y = camera.world_to_px(x0 + ca * k, y0 + sa * k)
        batch.put_c(x, y, ".", color)
        k += step


def draw_plains_tells(text, camera, e) -> None:
    """Tells for any P7 enemy (also the shieldbearer, a Character)."""
    batch = _Batch(text)
    x, y = camera.world_to_px(e.x, e.y)
    scale = e.espec.scale if not e.espec.body else config.BODIES[e.espec.body].sprite_scale
    top = y - scale * 9 - 10
    tell = getattr(e, "tell", 0.0)
    if tell > 0 and not isinstance(e, (Bull, Lancer, Hawk)):
        if int(tell * (8 if tell > 0.3 else 16)) % 2 == 0:
            batch.put_c(x, top, "!", palette.PLAINS_TELL[0])
    if isinstance(e, Bull) and e.state in ("scrape", "turn"):
        _line(batch, camera, e.x, e.y, e.facing, config.BULL_CHARGE, palette.PLAINS_TELL[1])
    if isinstance(e, Lancer) and e.state == "lower":
        _line(batch, camera, e.x, e.y, e.aim, e.length, palette.PLAINS_TELL[1])
    if isinstance(e, Hawk) and e.state == "mark":
        _line(batch, camera, e.x, e.y, e.aim, config.HAWK_DIVE_LENGTH, palette.PLAINS_TELL[1])
    if isinstance(e, Drummer):
        pulse = (e.beat * 2.5) % 1.0
        r = config.DRUM_RADIUS * (0.92 + 0.08 * pulse)
        color = palette.DRUM_RING[0 if pulse < 0.3 else 1]
        for k in range(28):
            a = k * math.tau / 28
            px, py = camera.world_to_px(e.x + math.cos(a) * r, e.y + math.sin(a) * r)
            batch.put_c(px, py, "." if k % 2 else "'", color)
    if e.espec.elite:
        batch.put_c(x, top - 12, "*", palette.ELITE_STAR)
    if getattr(e, "open", 0.0) > 0:                       # the shieldbearer, unguarded
        batch.put_c(x, top, "open", palette.PLAINS_TELL[1])
    batch.flush()


def draw_plains(text, bank, camera, e) -> None:
    """A P7 creature: body, tells, health bar."""
    x, y = camera.world_to_px(e.x, e.y)
    hurt = e.hurt_flash > 0
    scale = e.espec.scale
    if isinstance(e, Hawk):                              # its shadow on the ground
        batch = _Batch(text)
        batch.put_c(x, y + 22, "_", palette.BOMB_SHADOW)
        batch.flush()
        y -= 10
    if isinstance(e, Lancer):
        angle = e.aim if e.state in ("lower", "joust") else e.facing
        left = math.cos(angle) < 0
        draw_rider(bank, x, y, "bandit", "horse", scale, left,
                   gallop_frame(_Gait(e)), hurt)
        _lance(text, camera, e, angle)
    else:
        draw_character(bank, x, y, e.espec.sprite, scale, e.facing_left(), _frame(e), hurt)
    draw_plains_tells(text, camera, e)
    if e.hp < e.max_hp and e.hittable:
        draw_hp_bar(text, x, y - scale * 9 - 6, e.hp / e.max_hp)


class _Gait:
    """What gallop_frame needs from a rider, for the lancer."""

    def __init__(self, e) -> None:
        self.speed = 10.0 if e.moving else 0.0
        self.walked = e.walked


def _lance(text, camera, e, angle) -> None:
    """The lance: a pole pointing ahead, its steel tip LANCER_REACH out
    (level while it gallops through, raised otherwise)."""
    batch = _Batch(text)
    level = e.state in ("lower", "joust")
    reach = config.LANCER_REACH if level else 1.0
    lift = 0.0 if level else -0.9
    for k in (0.6, 1.0):
        px, py = camera.world_to_px(e.x + math.cos(angle) * reach * k,
                                    e.y + math.sin(angle) * reach * k + lift * k - 0.4)
        batch.put_c(px, py, "-" if k < 1 else ">" if math.cos(angle) >= 0 else "<",
                    palette.SHOT_ARROW[1][0] if k < 1 else palette.SHOT_ARROW[0])
    batch.flush()


def is_plains(e) -> bool:
    return isinstance(e, PlainsCreature)
