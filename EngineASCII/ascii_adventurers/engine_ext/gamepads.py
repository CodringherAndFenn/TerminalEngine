"""
engine_ext/gamepads.py -- gamepads through SDL's GameController API.

SDL maps every known pad (Xbox, PlayStation, Switch Pro, Steam Deck, and
anything Steam Input presents) onto one standard layout: A/B/X/Y, a d-pad,
two sticks, two shoulders, two triggers, Start and Back. So the game only
ever deals with that layout.

Two jobs:
  * the pads themselves: opened at startup and when plugged in, closed when
    unplugged (Gamepads.handle_event), and read by the players' controls
    (players/controls.py) -- sticks as -1..1, triggers as 0..1;
  * menus: pad input becomes the keyboard keys the menus already know
    (menu_keys): d-pad / left stick -> arrows, A -> Enter, B -> Esc,
    Start -> Esc, Back -> M. The stick fires one arrow when it crosses
    MENU_STICK_ON and must come back under MENU_STICK_OFF before the next,
    so holding it doesn't scroll wildly.

Without a controller subsystem (or pads), everything is a harmless no-op.
"""

from __future__ import annotations

import pygame

try:
    from pygame._sdl2 import controller as _sdl_controller
except ImportError:   # very old pygame: no gamepad support
    _sdl_controller = None

AXIS_MAX = 32767.0
STICK_DEADZONE = 0.22       # stick deflection ignored (worn sticks drift)
TRIGGER_THRESHOLD = 0.35    # how far a trigger must be pulled to count
MENU_STICK_ON = 0.6
MENU_STICK_OFF = 0.35

_BUTTON_KEYS = {
    "CONTROLLER_BUTTON_DPAD_UP": pygame.K_UP,
    "CONTROLLER_BUTTON_DPAD_DOWN": pygame.K_DOWN,
    "CONTROLLER_BUTTON_DPAD_LEFT": pygame.K_LEFT,
    "CONTROLLER_BUTTON_DPAD_RIGHT": pygame.K_RIGHT,
    "CONTROLLER_BUTTON_A": pygame.K_RETURN,
    "CONTROLLER_BUTTON_B": pygame.K_ESCAPE,
    "CONTROLLER_BUTTON_START": pygame.K_ESCAPE,
    "CONTROLLER_BUTTON_BACK": pygame.K_m,
}
BUTTON_KEYS = {getattr(pygame, name): key for name, key in _BUTTON_KEYS.items()
               if hasattr(pygame, name)}
BUTTON_A = getattr(pygame, "CONTROLLER_BUTTON_A", -1)
BUTTON_B = getattr(pygame, "CONTROLLER_BUTTON_B", -1)
BUTTON_START = getattr(pygame, "CONTROLLER_BUTTON_START", -1)
BUTTON_BACK = getattr(pygame, "CONTROLLER_BUTTON_BACK", -1)
BUTTON_LB = getattr(pygame, "CONTROLLER_BUTTON_LEFTSHOULDER", -1)
BUTTON_RB = getattr(pygame, "CONTROLLER_BUTTON_RIGHTSHOULDER", -1)
BUTTON_Y = getattr(pygame, "CONTROLLER_BUTTON_Y", -1)
AXIS_LX = getattr(pygame, "CONTROLLER_AXIS_LEFTX", 0)
AXIS_LY = getattr(pygame, "CONTROLLER_AXIS_LEFTY", 1)
AXIS_RX = getattr(pygame, "CONTROLLER_AXIS_RIGHTX", 2)
AXIS_RY = getattr(pygame, "CONTROLLER_AXIS_RIGHTY", 3)
AXIS_LT = getattr(pygame, "CONTROLLER_AXIS_TRIGGERLEFT", 4)
AXIS_RT = getattr(pygame, "CONTROLLER_AXIS_TRIGGERRIGHT", 5)
EV_ADDED = getattr(pygame, "CONTROLLERDEVICEADDED", -1)
EV_REMOVED = getattr(pygame, "CONTROLLERDEVICEREMOVED", -1)
EV_BUTTON = getattr(pygame, "CONTROLLERBUTTONDOWN", -1)
EV_AXIS = getattr(pygame, "CONTROLLERAXISMOTION", -1)


def stick(x: float, y: float) -> tuple[float, float]:
    """Raw stick values (-1..1) with a radial deadzone, rescaled so motion
    starts smoothly just past it."""
    mag = (x * x + y * y) ** 0.5
    if mag <= STICK_DEADZONE:
        return 0.0, 0.0
    scale = min(1.0, (mag - STICK_DEADZONE) / (1.0 - STICK_DEADZONE)) / mag
    return x * scale, y * scale


class Pad:
    """One open controller. `device` is anything with get_axis/get_button
    (an SDL Controller, or a stand-in in tests)."""

    def __init__(self, device, instance_id: int) -> None:
        self.device = device
        self.instance_id = instance_id
        self.menu_axes: dict[int, int] = {}   # axis -> -1/0/1 latch for menu repeat

    def axis(self, axis: int) -> float:
        try:
            return max(-1.0, min(1.0, self.device.get_axis(axis) / AXIS_MAX))
        except pygame.error:
            return 0.0

    def button(self, button: int) -> bool:
        try:
            return bool(self.device.get_button(button))
        except pygame.error:
            return False

    def left_stick(self) -> tuple[float, float]:
        return stick(self.axis(AXIS_LX), self.axis(AXIS_LY))

    def right_stick(self) -> tuple[float, float]:
        return stick(self.axis(AXIS_RX), self.axis(AXIS_RY))

    def trigger(self, axis: int) -> bool:
        return self.axis(axis) >= TRIGGER_THRESHOLD


class Gamepads:
    """All connected pads, in the order they were connected."""

    def __init__(self) -> None:
        self.pads: list[Pad] = []
        self.available = False
        if _sdl_controller is None:
            return
        try:
            _sdl_controller.init()
            self.available = True
            for i in range(_sdl_controller.get_count()):
                self._open(i)
        except pygame.error:
            self.available = False

    def _open(self, device_index: int) -> None:
        try:
            if not _sdl_controller.is_controller(device_index):
                return
            dev = _sdl_controller.Controller(device_index)
            iid = dev.as_joystick().get_instance_id()
        except (pygame.error, AttributeError):
            return
        if all(p.instance_id != iid for p in self.pads):
            self.pads.append(Pad(dev, iid))

    def by_instance(self, instance_id: int) -> Pad | None:
        return next((p for p in self.pads if p.instance_id == instance_id), None)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Hot-plugging. True if the event was a device change."""
        if event.type == EV_ADDED and self.available:
            self._open(event.device_index)
            return True
        if event.type == EV_REMOVED:
            self.pads = [p for p in self.pads if p.instance_id != event.instance_id]
            return True
        return False

    def menu_keys(self, event: pygame.event.Event) -> list[pygame.event.Event]:
        """The keyboard events a pad event stands for in menus ([] if none)."""
        if event.type == EV_BUTTON and event.button in BUTTON_KEYS:
            return [_key(BUTTON_KEYS[event.button])]
        if event.type == EV_AXIS and event.axis in (AXIS_LX, AXIS_LY):
            pad = self.by_instance(getattr(event, "instance_id", -1))
            latch = pad.menu_axes if pad is not None else {}
            v = event.value / AXIS_MAX
            state = latch.get(event.axis, 0)
            if state == 0 and abs(v) >= MENU_STICK_ON:
                latch[event.axis] = 1 if v > 0 else -1
                if event.axis == AXIS_LX:
                    return [_key(pygame.K_RIGHT if v > 0 else pygame.K_LEFT)]
                return [_key(pygame.K_DOWN if v > 0 else pygame.K_UP)]
            if state != 0 and abs(v) <= MENU_STICK_OFF:
                latch[event.axis] = 0
        return []


def _key(key: int) -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN, key=key, unicode="", mod=0, from_pad=True)
