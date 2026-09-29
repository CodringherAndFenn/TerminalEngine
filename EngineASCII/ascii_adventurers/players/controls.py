"""
players/controls.py -- where a player's intentions come from.

Once per simulation step, the game asks each player's control source for a
PlayerInput: which way to walk, where to aim (a world point), and whether
the trigger is held. The game never reads the keyboard, mouse or a pad
directly, so a player can just as well be driven by a gamepad, a bot (the
debug ghost below) or, later, a network connection.

Sources:
  * KeyboardMouse -- WASD/arrows, mouse aim through the player's camera,
    left button fires.
  * PadControls -- twin-stick: left stick walks, right stick aims (the aim
    point sits AIM_DISTANCE tiles out that way and stays put when the stick
    is let go), right trigger or right shoulder fires.
  * AutoControls -- the solo player: keyboard+mouse and every pad at once;
    whichever was touched last aims (so the reticle doesn't jump between
    the mouse and the stick), and any of them can walk or fire.
  * GhostControls -- a debug bot (run.py --ghosts N): wanders off on its
    own and shoots what it sees, to exercise the world around more than
    one player.

After a menu closes, `block_fire()` ignores a held trigger until it's let
go, so the click that closed the menu doesn't fire.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

import pygame

from .. import config
from ..engine_ext.gamepads import AXIS_RT, BUTTON_RB, Gamepads, Pad
from ..engine_ext.input import Mouse, move_axes
from ..systems.raycast import first_hit


@dataclass
class PlayerInput:
    move_x: float = 0.0          # -1..1 (any length; the hero normalizes)
    move_y: float = 0.0
    aim: tuple[float, float] | None = None   # world point; None: keep aiming as before
    fire: bool = False


class Controls:
    """Base: produces a PlayerInput per step. `camera` is the player's view
    (for turning the mouse into a world point)."""

    def __init__(self) -> None:
        self._fire_blocked = False

    def block_fire(self) -> None:
        self._fire_blocked = True

    def _gate_fire(self, held: bool) -> bool:
        if self._fire_blocked:
            if held:
                return False
            self._fire_blocked = False
        return held

    def read(self, hero, camera, world, enemies=()) -> PlayerInput:  # pragma: no cover
        raise NotImplementedError

    @property
    def uses_mouse(self) -> bool:
        """True while the mouse is the aiming device (the OS cursor is
        replaced by the reticle at the mouse)."""
        return False


class KeyboardMouse(Controls):
    def __init__(self, mouse: Mouse) -> None:
        super().__init__()
        self.mouse = mouse

    def read(self, hero, camera, world, enemies=()) -> PlayerInput:
        mx, my = move_axes()
        px, py = self.mouse.poll()
        return PlayerInput(mx, my, camera.canvas_to_world(px, py),
                           self._gate_fire(self.mouse.left_held()))

    @property
    def uses_mouse(self) -> bool:
        return True


class PadControls(Controls):
    def __init__(self, pad: Pad) -> None:
        super().__init__()
        self.pad = pad
        self.aim_dir: tuple[float, float] | None = None

    def active(self) -> bool:
        """Anything on the pad being used right now."""
        lx, ly = self.pad.left_stick()
        rx, ry = self.pad.right_stick()
        return bool(lx or ly or rx or ry or self._fire_held())

    def _fire_held(self) -> bool:
        return self.pad.trigger(AXIS_RT) or self.pad.button(BUTTON_RB)

    def read(self, hero, camera, world, enemies=()) -> PlayerInput:
        lx, ly = self.pad.left_stick()
        rx, ry = self.pad.right_stick()
        if rx or ry:
            n = math.hypot(rx, ry)
            self.aim_dir = (rx / n, ry / n)
        elif self.aim_dir is None and (lx or ly):
            n = math.hypot(lx, ly)       # no aim yet: face where you walk
            self.aim_dir = (lx / n, ly / n)
        aim = None
        if self.aim_dir is not None:
            d = config.PAD_AIM_DISTANCE
            aim = (hero.x + self.aim_dir[0] * d, hero.y + self.aim_dir[1] * d)
        return PlayerInput(lx, ly, aim, self._gate_fire(self._fire_held()))


class AutoControls(Controls):
    """Keyboard+mouse plus every connected pad (see module docstring)."""

    def __init__(self, mouse: Mouse, pads: Gamepads) -> None:
        super().__init__()
        self.kbm = KeyboardMouse(mouse)
        self.pads = pads
        self._pad_controls: dict[int, PadControls] = {}
        self.using_pad = False
        self._last_mouse = None

    def _pad_list(self) -> list[PadControls]:
        live = {p.instance_id for p in self.pads.pads}
        for iid in list(self._pad_controls):
            if iid not in live:
                del self._pad_controls[iid]
        for p in self.pads.pads:
            if p.instance_id not in self._pad_controls:
                self._pad_controls[p.instance_id] = PadControls(p)
        return list(self._pad_controls.values())

    def block_fire(self) -> None:
        super().block_fire()
        self.kbm.block_fire()
        for pc in self._pad_list():
            pc.block_fire()

    def read(self, hero, camera, world, enemies=()) -> PlayerInput:
        k = self.kbm.read(hero, camera, world, enemies)
        mouse_now = pygame.mouse.get_pos()
        mouse_moved = self._last_mouse is not None and mouse_now != self._last_mouse
        self._last_mouse = mouse_now
        if mouse_moved or k.fire:
            self.using_pad = False
        out = PlayerInput(k.move_x, k.move_y, None if self.using_pad else k.aim, k.fire)
        for pc in self._pad_list():
            if pc.active():
                self.using_pad = True
            p = pc.read(hero, camera, world, enemies)
            if p.move_x or p.move_y:
                out.move_x, out.move_y = p.move_x, p.move_y
            if self.using_pad and p.aim is not None:
                out.aim = p.aim
            out.fire = out.fire or p.fire
        return out

    @property
    def uses_mouse(self) -> bool:
        return not self.using_pad


class GhostControls(Controls):
    """A wandering, shooting bot. Seeded, so a ghost's run is repeatable."""

    def __init__(self, seed: int) -> None:
        super().__init__()
        self.rng = random.Random(seed)
        self.heading = self.rng.uniform(0, math.tau)
        self.turn_timer = 0.0
        self.stuck = 0.0

    def read(self, hero, camera, world, enemies=()) -> PlayerInput:
        step = 1.0 / config.SIM_HZ
        self.turn_timer -= step
        self.stuck = self.stuck + step if hero.last_blocked else 0.0
        if self.turn_timer <= 0 or self.stuck > 0.4:
            self.heading += self.rng.uniform(-2.0, 2.0) if self.stuck <= 0.4 else math.pi / 2
            self.turn_timer = self.rng.uniform(4.0, 10.0)
            self.stuck = 0.0
        target = None
        best = config.GHOST_SIGHT
        for e in enemies:
            d = math.hypot(e.x - hero.x, e.y - hero.y)
            if e.hittable and d < best and first_hit(world.tile_at, hero.x, hero.y, e.x, e.y) is None:
                target, best = e, d
        aim = (target.x, target.y) if target is not None else None
        return PlayerInput(math.cos(self.heading), math.sin(self.heading), aim, target is not None)
