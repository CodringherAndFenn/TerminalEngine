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
from .progress import Progress


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
    progress: Progress = field(default_factory=Progress)    # level, XP, cards
    regen: float = 0.0                # hp per second (cards)
    spells: dict = field(default_factory=dict)  # spell key -> systems/spells.SpellState
    mark_timer: float = 0.0           # Hunter's Mark: seconds to the next mark
    called: int = 0                   # M28.3k, Called shot: the hero's rolls already seen
    meta: list = field(default_factory=list)    # Guild upgrades, as card steps (meta/guild.py)
    loadout_level: int = 1            # the level the hero's loadout was built for (P3 speed)
    unlocked: set | None = None       # cards this player may be offered (None: all)
    # Card / guild state of the run (systems/run_rules.py)
    frenzy: float = 0.0               # Frenzy: seconds of double attack speed left
    echo_timer: float = 0.0           # Echo: the repeated attack comes in this many s
    # M28.2a, the off-hand's tricks (systems/run_rules.py): attacks toward
    # the next echo, which echo is coming (1 its echo, 2 Canyon's third) and
    # at what x damage; the Starburst meter (attacks and, with Pain turns
    # the wheel, hits taken) and the hits already counted; crosses fired
    # (Needle); Corona's second ring (s left, its angle, the attack's
    # keywords); Watchful's cooldown.
    echo_count: int = 0
    echo_stage: int = 0
    echo_mult: float = 1.0
    burst_meter: float = 0.0
    hits_seen: int = 0
    crosses: int = 0
    corona: tuple | None = None
    rose_t: float = 0.0               # M28.3d: Compass Orb (L), Wind rose's clock
    attack_shots: list = field(default_factory=list)   # the last attack's own shots (Sunspot)
    watch_cd: float = 0.0
    retaliate_cd: float = 0.0         # Retaliation's cooldown
    bounty: int = 0                   # kills toward Bounty's next cache
    # M28.2e, the rings' tricks (systems/run_rules.py): Short fuse's added
    # chance; the last kill's time (Grim); loot from salvaging (Miser);
    # Lighthouse's clock and its wave (deadline, the wave's enemies);
    # Fuse line's explosions waiting to go off.
    fuse: float = 0.0
    last_kill: float = -1e9
    salvaged: float = 0.0
    lighthouse_t: float = 0.0
    wave: tuple | None = None
    fuses: list = field(default_factory=list)
    kill_times: list = field(default_factory=list)   # recent kills (achievement)
    phoenix_used: int = 0
    phoenix_kills: int = 0            # M28.3c: Phoenix Mantle (L), toward a used rise's return
    # M28.3h, the rings' legendary tricks: kills toward the next +1 max HP
    # and the max HP grown (Reaper's Band); the level and the XP bar's
    # quarters reached in it (Ascendant Band); the wanted enemy, until when,
    # and s to the next (Bountymark Ring).
    harvest_kills: int = 0
    harvest: int = 0
    ascent: tuple = (1, 0)
    wanted: object = None
    wanted_until: float = 0.0
    wanted_t: float = 0.0
    revives_used: int = 0             # Second Chance
    glory: bool = False               # M27: Adventurer's Glory (may end the run as a victory)

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
