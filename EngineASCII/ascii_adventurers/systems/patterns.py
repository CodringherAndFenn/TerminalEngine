"""
systems/patterns.py -- bullet patterns for bosses (design/BOSSES.md 5.1).

Each function spawns one volley of a pattern into `projectiles`; a boss's
moves (ai/bosses.py) call them on their own timing (a spiral is radial()
called again and again with the turn advancing, a curtain is rows of
curtain(), and so on). Shots are ordinary projectiles owned by the boss,
so they hit, fizzle and get drawn like any other; their damage is the
shell's times the boss's damage multiplier (enemy level scaling, pacts).

  P1 radial          a ring of shots out from a point
  P2 spiral          (radial, repeated with the turn advancing)
  P3 fan             shots spread around an aim
  P5 ring_in         a ring round a point that waits, then closes on it
  P10 curtain        a row of shots with a hole, sweeping across from one side
Line attacks (P7: tongues, beams) and blasts (P8: belly flops) aren't
shots; bosses do them with combat.blast / segment checks.
"""

from __future__ import annotations

import math

from ..entities.projectile import Projectile
from ..specs import ShellSpec


def shoot(owner, x: float, y: float, angle: float, shell: ShellSpec, projectiles: list,
          tint: int = 0) -> Projectile:
    """One shot from (x, y) along `angle`."""
    p = Projectile(x, y, angle, shell, owner=owner,
                   damage=shell.damage * getattr(owner, "damage_mult", 1.0))
    p.tint = tint
    projectiles.append(p)
    return p


def radial(owner, x: float, y: float, n: int, shell: ShellSpec, projectiles: list,
           turn: float = 0.0, tint: int = 0) -> None:
    """P1: n shots evenly all round, the first at angle `turn`."""
    for k in range(n):
        shoot(owner, x, y, turn + k * math.tau / n, shell, projectiles, tint + k)


def fan(owner, x: float, y: float, angle: float, n: int, spread_deg: float, shell: ShellSpec,
        projectiles: list, tint: int = 0) -> None:
    """P3: n shots spread evenly over `spread_deg`, centred on `angle`."""
    spread = math.radians(spread_deg)
    for k in range(n):
        a = angle + (spread * (k / (n - 1) - 0.5) if n > 1 else 0.0)
        shoot(owner, x, y, a, shell, projectiles, tint + k)


def ring_in(owner, cx: float, cy: float, radius: float, n: int, shell: ShellSpec,
            projectiles: list, hold: float, turn: float = 0.0, tint: int = 0) -> None:
    """P5: n shots on a circle round (cx, cy) that wait `hold` seconds (the
    tell: you see the ring before it moves), then fly in through the centre
    and out the other side (the shell's range should be ~2 x radius)."""
    for k in range(n):
        a = turn + k * math.tau / n
        p = shoot(owner, cx + math.cos(a) * radius, cy + math.sin(a) * radius, a + math.pi,
                  shell, projectiles, tint + k)
        p.hold = hold


def curtain(owner, cx: float, cy: float, heading: float, back: float, half_width: float,
            spacing: float, hole_at: float, hole: float, shell: ShellSpec, projectiles: list,
            tint: int = 0) -> None:
    """P10: a row of shots `back` tiles behind (cx, cy) as seen along
    `heading`, `half_width` tiles to either side, `spacing` apart, all
    flying along `heading` -- except a hole `hole` tiles wide centred
    `hole_at` tiles to the side. Called row after row with the hole
    drifting, it's a curtain to weave through."""
    hx, hy = math.cos(heading), math.sin(heading)
    sx, sy = -hy, hx                     # sideways
    ox, oy = cx - hx * back, cy - hy * back
    k = 0
    s = -half_width
    while s <= half_width + 1e-9:
        if abs(s - hole_at) > hole / 2:
            shoot(owner, ox + sx * s, oy + sy * s, heading, shell, projectiles, tint + k)
        s += spacing
        k += 1


def point_segment_distance(px: float, py: float, x0: float, y0: float, x1: float,
                           y1: float) -> float:
    """Distance from point (px, py) to the segment (x0, y0)-(x1, y1) (line
    attacks: a tongue, a beam)."""
    dx, dy = x1 - x0, y1 - y0
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - x0) * dx + (py - y0) * dy) / L2))
    return math.hypot(px - (x0 + dx * t), py - (y0 + dy * t))
