"""
players/player.py -- one player: hero, controls, camera and run stats.

Every player has their own camera and can wander anywhere. The world
streams and enemies wake around each player's view (their "focus"), and
enemies pick targets among all players.

`local` players are shown on this machine (today: the one human player).
Ghosts (debug bots) and, later, remote players still have a camera --
it defines the area kept alive around them -- but nothing draws it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .. import config
from ..engine_ext.camera import Camera
from ..entities.character import Character
from ..meta.run_stats import RunStats
from ..ui.maps import Minimap
from .controls import Controls


@dataclass
class Focus:
    """An area kept alive around a player: centre and half-size, in tiles."""

    x: float
    y: float
    half_w: float
    half_h: float

    def near(self, x: float, y: float, margin: float) -> bool:
        return abs(x - self.x) <= self.half_w + margin and abs(y - self.y) <= self.half_h + margin


def near_any(foci: list[Focus], x: float, y: float, margin: float) -> bool:
    return any(f.near(x, y, margin) for f in foci)


@dataclass
class Player:
    index: int
    hero: Character
    controls: Controls
    camera: Camera
    stats: RunStats
    local: bool = True
    ghost: bool = False
    color: tuple = (255, 255, 255)
    minimap: Minimap | None = None
    dead_for: float = -1.0            # seconds since the hero fell; <0: alive
    aim: tuple[float, float] | None = field(default=None)   # last aim point (world)

    @property
    def alive(self) -> bool:
        return self.dead_for < 0

    def focus(self) -> Focus:
        """The area kept alive around this player: their screen's size,
        centred on the hero. (On the hero, not the eased camera, so the
        simulation depends only on game state, never on frame timing.)"""
        c = self.camera
        return Focus(self.hero.x, self.hero.y, c.view_w / c.tile_w / 2, c.view_h / c.tile_h / 2)


def player_color(index: int) -> tuple:
    return config.PLAYER_COLORS[index % len(config.PLAYER_COLORS)]
