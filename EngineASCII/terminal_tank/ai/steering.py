"""
ai/steering.py -- deliberately simple, slightly clumsy obstacle avoidance.

There is no global pathfinding (A* etc.). Like Noita's creatures, enemies
only know what's right in front of them:

  1. Head straight for the goal if a probe a short way ahead is clear.
  2. If it's blocked, pick a side at random (left or right) and *commit* to
     it for a while, trying headings further and further round that side
     (30, 60, 90... degrees) until one is clear. Committing is what makes
     them slide along a wall instead of dithering at it.
  3. If the committed side dead-ends, try the other side.
  4. Stuck detection: if the body has barely moved for a while although it
     wants to, it backs off in a random direction for a moment and flips
     sides.
  5. Frustration: if it keeps moving but gets no closer to the goal (e.g.
     sliding back and forth along the closed end of a U-shaped ruin), it
     "thinks harder" -- a small local path search (ai/pathing.py, only the
     tiles around it) -- and follows that detour for a while, or wanders
     off randomly if even that finds nothing better. It still never knows
     the whole map.

The upshot: they usually get where they're going, sometimes take odd
routes, occasionally get fooled by a U-shaped obstacle, and the player can
use terrain to shake them off.
"""

from __future__ import annotations

import math
import random
from typing import Callable

from .pathing import local_path

PROBE_ANGLES = [math.radians(a) for a in (30, 60, 90, 120, 150)]
# Seconds of moving without getting any closer before planning a detour.
FRUSTRATION_TIME = 2.5


class Steering:
    def __init__(self, rng: random.Random, probe: float = 1.6) -> None:
        self.rng = rng
        self.probe = probe             # tiles ahead to test
        self.side = 0                  # -1 / +1 while committed to a side
        self.side_timer = 0.0
        self.unstick_timer = 0.0
        self.unstick_angle = 0.0
        self._window = 0.0             # stuck detection
        self._window_start = (0.0, 0.0)
        self._wanted = False
        self._best = math.inf          # frustration: closest we've got to the goal
        self._no_progress = 0.0
        self.route: list[tuple[float, float]] = []   # detour waypoints, when frustrated
        self.route_timer = 0.0

    def direction(
        self, x: float, y: float, gx: float, gy: float,
        passable: Callable[[float, float, float], bool], dt: float,
        world=None, clearance: int = 1,
    ) -> tuple[float, float]:
        """Unit direction to move in this frame to get from (x, y) toward the
        goal (gx, gy). `passable(px, py, heading)` says whether the body
        would fit at (px, py) facing `heading`. With `world` given, a
        frustrated body plans a short local route (ai/pathing.py) for a
        body needing `clearance` free tiles around its center."""
        self.side_timer -= dt
        self._track_stuck(x, y, dt)
        if self.unstick_timer > 0:
            self.unstick_timer -= dt
            return math.cos(self.unstick_angle), math.sin(self.unstick_angle)

        gx, gy = self._track_progress(x, y, gx, gy, dt, world, clearance)
        want = math.atan2(gy - y, gx - x)
        if self._clear(x, y, want, passable):
            if self.side_timer <= 0:
                self.side = 0
            return math.cos(want), math.sin(want)

        if self.side == 0 or self.side_timer <= 0:
            self.side = self.rng.choice((-1, 1))
            self.side_timer = self.rng.uniform(1.0, 2.5)
        for side in (self.side, -self.side):
            for off in PROBE_ANGLES:
                a = want + side * off
                if self._clear(x, y, a, passable):
                    if side != self.side:
                        self.side = side  # the other way was the open one
                    return math.cos(a), math.sin(a)
        return math.cos(want), math.sin(want)  # boxed in: push and hope

    def _clear(self, x, y, heading, passable) -> bool:
        return passable(x + math.cos(heading) * self.probe, y + math.sin(heading) * self.probe, heading)

    def _track_progress(self, x, y, gx, gy, dt, world, clearance) -> tuple[float, float]:
        """Returns the point to head for right now: the real goal, or the
        next waypoint of a detour after FRUSTRATION_TIME seconds without
        getting any closer."""
        if self.route:
            self.route_timer -= dt
            while self.route and math.hypot(self.route[0][0] - x, self.route[0][1] - y) < 0.9:
                self.route.pop(0)
            if self.route and self.route_timer > 0:
                return self.route[0]
            self.route = []
            self._best = math.inf
        d = math.hypot(gx - x, gy - y)
        if d < self._best - 0.5:
            self._best = d
            self._no_progress = 0.0
        else:
            self._no_progress += dt
        if self._no_progress > FRUSTRATION_TIME and d > 2.0:
            self._no_progress = 0.0
            self.side = self.rng.choice((-1, 1))
            if world is not None:
                self.route = local_path(world, x, y, gx, gy, clearance=clearance)
            if not self.route:
                # Nothing better nearby (or no map access): wander off
                # sideways/away for a moment and try again from there.
                a = math.atan2(y - gy, x - gx) + self.rng.uniform(-1.7, 1.7)
                r = self.rng.uniform(5, 10)
                self.route = [(x + math.cos(a) * r, y + math.sin(a) * r)]
            self.route_timer = self.rng.uniform(5.0, 8.0)
            return self.route[0]
        return gx, gy

    def note_intent(self, wants_to_move: bool) -> None:
        """Tell the stuck detector whether the body is trying to move."""
        self._wanted = wants_to_move

    def _track_stuck(self, x: float, y: float, dt: float) -> None:
        if not self._wanted:
            self._window = 0.0
            self._window_start = (x, y)
            return
        self._window += dt
        if self._window >= 0.9:
            sx, sy = self._window_start
            if math.hypot(x - sx, y - sy) < 0.3:
                # Stuck: back off somewhere random for a moment, other side next.
                self.unstick_angle = self.rng.uniform(-math.pi, math.pi)
                self.unstick_timer = self.rng.uniform(0.5, 1.0)
                self.side = -self.side if self.side else self.rng.choice((-1, 1))
                self.side_timer = self.rng.uniform(1.5, 3.0)
            self._window = 0.0
            self._window_start = (x, y)
