"""
app.py -- the game's long-lived services, shared by every scene.

The engine's SceneManager owns the display, text renderer and audio; the
game adds its own: the player's settings (meta/settings.py), their records
(meta/records.py), the sound effects and the gamepads. run.py creates one App and
attaches it to the manager; scenes reach it with app_of(manager).

persist=False keeps everything in memory (tests, tools): nothing is
written to save/.
"""

from __future__ import annotations

from .engine_ext.gamepads import Gamepads
from .engine_ext.sfx import Sfx
from .meta.records import Records
from .meta.settings import GameSettings


class App:
    def __init__(self, audio, settings: GameSettings | None = None,
                 records: Records | None = None, persist: bool = True,
                 ghosts: int = 0) -> None:
        self.persist = persist
        self.settings = settings if settings is not None else GameSettings()
        self.records = records if records is not None else Records()
        self.sfx = Sfx(audio, self.settings.sfx_volume)
        self.pads = Gamepads()
        # Debug: extra bot players roaming the island (run.py --ghosts N).
        self.ghosts = ghosts
        # Vsync is only set when the window is made: remember what this
        # session started with, so a changed setting can say "after restart".
        self.vsync_at_start = self.settings.vsync

    def ui_sound(self) -> None:
        """The menu blip, at the same loudness as the game's sounds."""
        self.sfx.play("ui")

    def save_settings(self) -> None:
        if self.persist:
            self.settings.save()

    def save_records(self) -> None:
        if self.persist:
            self.records.save()


def app_of(manager) -> App:
    """The manager's App; one with defaults and no saving is made on the
    fly for managers built without run.py (tests)."""
    app = getattr(manager, "app", None)
    if app is None:
        app = manager.app = App(manager.audio, persist=False)
    return app
