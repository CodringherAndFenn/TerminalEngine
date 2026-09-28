"""
scene.py -- the scene abstraction and the application loop that drives it.

A ``Scene`` is one screen of the game (intro, menu, settings, ...). The
``SceneManager`` owns the window, renderer, fade, audio, and settings, runs the
fixed 60 fps loop, and swaps scenes with a fade transition. Scenes stay simple:
they react to events, update, and draw, and ask the manager to navigate.

Transition model: ``switch_to`` fades the current scene to black, swaps in the
new one, then fades back up -- reusing the existing Fade. Input to the scene is
suspended while a transition runs, so clicks mid-fade can't fire twice.
"""

from __future__ import annotations

import time

import pygame

from .audio import Audio
from .display import Display
from .settings import Settings
from .text import Fade, TextRenderer


class Scene:
    """Base class for a screen. Override the hooks you need.

    ``self.manager`` is set by the SceneManager before ``on_enter`` and gives
    access to ``display``, ``text``, ``audio``, ``settings``, and ``fade``.
    """

    manager: "SceneManager"

    def on_enter(self) -> None:
        """Called once when this scene becomes active."""

    def handle_event(self, event: pygame.event.Event) -> None:
        """Handle one input/window event (skipped during transitions)."""

    def update(self, dt: float) -> None:
        """Advance animation/logic by dt seconds."""

    def draw(self, text: TextRenderer) -> None:
        """Redraw the whole scene onto the virtual canvas."""

    def on_exit(self) -> None:
        """Called once when this scene is replaced."""


class SceneManager:
    """Owns shared services and runs the main loop.

    Parameters
    ----------
    display, settings, audio:
        Shared, long-lived services. The manager creates its own
        TextRenderer and Fade over the display.
    fps:
        Frame-rate cap used when the display has no vsync. With vsync the
        monitor paces the loop instead (see run()).
    """

    def __init__(
        self, display: Display, settings: Settings, audio: Audio, *, fps: int = 60
    ) -> None:
        self.display = display
        self.fps = fps
        self.settings = settings
        self.audio = audio
        self.text = TextRenderer(display)
        self.fade = Fade(display, duration=0.4)

        self.scene: Scene | None = None
        self._pending: Scene | None = None
        self._transition: str | None = None  # None | "out" | "in"
        self._running = False

    # --- Navigation ------------------------------------------------------

    def switch_to(self, scene: Scene, *, fade: bool = True) -> None:
        """Make ``scene`` active. With fade (default), runs black-out/in around
        the swap; without, swaps immediately."""
        if not fade:
            self._set_scene(scene)
            return
        if self._transition is not None:
            return  # ignore navigation requests while already transitioning
        self._pending = scene
        self.fade.start(Fade.OUT)
        self._transition = "out"

    def quit(self) -> None:
        """Stop the main loop after the current frame."""
        self._running = False

    def _set_scene(self, scene: Scene) -> None:
        if self.scene is not None:
            self.scene.on_exit()
        scene.manager = self
        self.scene = scene
        scene.on_enter()

    # --- Main loop -------------------------------------------------------

    def run(self, initial: Scene) -> None:
        """Enter ``initial`` (fading up from black) and run until quit."""
        self._set_scene(initial)
        self.fade.start(Fade.IN)  # open on black, fade the first scene up
        self._transition = "in"
        self._running = True

        # Frame pacing. With vsync, flip() inside present() blocks until the
        # monitor's next refresh, so the monitor sets the rate and every
        # frame is shown exactly once; the clock only measures. Without
        # vsync, the clock sleeps to cap the rate at self.fps.
        # dt comes from perf_counter (sub-microsecond) rather than the
        # clock's whole milliseconds, so motion advances by the real elapsed
        # time instead of alternating 16/17 ms steps.
        clock = pygame.time.Clock()
        last = time.perf_counter()
        while self._running:
            if self.display.vsync:
                clock.tick()
            else:
                clock.tick(self.fps)
            now = time.perf_counter()
            dt = now - last
            last = now

            for event in pygame.event.get():
                self.display.handle_event(event)
                if event.type == pygame.QUIT:
                    self.quit()
                elif self._transition is None and self.scene is not None:
                    self.scene.handle_event(event)

            if self.scene is not None:
                self.scene.update(dt)
                self._advance_transition(dt)
                self.scene.draw(self.text)

            self.fade.draw()
            self.display.present()

        self.audio.quit()
        pygame.quit()

    def _advance_transition(self, dt: float) -> None:
        """Drive the fade and swap scenes at the black midpoint."""
        if self._transition is None:
            return
        self.fade.update(dt)
        if self.fade.active:
            return
        if self._transition == "out":
            # Fully black now: swap, then fade the new scene up.
            self._set_scene(self._pending)  # type: ignore[arg-type]
            self._pending = None
            self.fade.start(Fade.IN)
            self._transition = "in"
        else:  # "in" completed
            self._transition = None
