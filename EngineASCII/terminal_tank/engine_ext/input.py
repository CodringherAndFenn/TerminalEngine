"""
engine_ext/input.py -- polled input helpers on top of the engine.

The engine delivers discrete pygame events to Scene.handle_event(). Driving
needs *held* keys, which we poll each frame with pygame.key.get_pressed()
instead (that also stays correct across scene transitions, when the engine
withholds events). The mouse is read through the engine's
Display.window_to_canvas(), so aiming respects its scaling and letterboxing.
"""

from __future__ import annotations

import pygame

from engine import Display

_UP = (pygame.K_w, pygame.K_UP)
_DOWN = (pygame.K_s, pygame.K_DOWN)
_LEFT = (pygame.K_a, pygame.K_LEFT)
_RIGHT = (pygame.K_d, pygame.K_RIGHT)


def _any(keys, codes) -> bool:
    return any(keys[c] for c in codes)


def move_axes() -> tuple[int, int]:
    """Held movement keys as (x, y) in {-1, 0, 1}; y is +1 for down."""
    keys = pygame.key.get_pressed()
    x = int(_any(keys, _RIGHT)) - int(_any(keys, _LEFT))
    y = int(_any(keys, _DOWN)) - int(_any(keys, _UP))
    return x, y


class Mouse:
    """Tracks the mouse position on the canvas.

    When the pointer is over a letterbox bar (or outside the window),
    window_to_canvas returns None; we keep the last on-canvas position so the
    turret doesn't snap somewhere odd.
    """

    def __init__(self, display: Display) -> None:
        self.display = display
        w, h = display.canvas.get_size()
        self.canvas_pos: tuple[float, float] = (w / 2, h / 2)

    @staticmethod
    def left_held() -> bool:
        """Left button currently down (polled, so holding keeps firing)."""
        return pygame.mouse.get_pressed()[0]

    def poll(self) -> tuple[float, float]:
        pos = self.display.window_to_canvas(*pygame.mouse.get_pos())
        if pos is not None:
            self.canvas_pos = pos
        return self.canvas_pos
