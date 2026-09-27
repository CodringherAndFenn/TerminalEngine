"""
audio.py -- the audio manager: mixer lifecycle, master volume, output-device
selection, and a synthesized UI "blip".

There are no audio assets yet, so the blip is generated in pure Python (a
short enveloped square wave) into a raw PCM buffer that matches whatever
format the mixer actually opened with, then wrapped in a pygame Sound. This
keeps the audio settings testable -- changing the volume or the output device
plays an audible blip -- without adding a numpy dependency or bundling files.

Everything is defensive: a machine with no usable audio device still runs; the
manager just reports itself unavailable and every call becomes a no-op.
"""

from __future__ import annotations

import array
import math

import pygame

# Mixer format we request. -16 == signed 16-bit; 2 == stereo. We read the
# actually-opened format back from pygame.mixer.get_init() before building the
# blip, in case SDL hands us something different.
_FREQUENCY = 44100
_SIZE = -16
_CHANNELS = 2

_BLIP_HZ = 660.0     # pitch of the test blip
_BLIP_SECONDS = 0.07  # short and unobtrusive


class Audio:
    """Owns the pygame mixer and the synthesized blip.

    Usage:
        audio = Audio()
        audio.init(device=settings.audio_device)
        audio.set_volume(settings.volume)
        audio.play_blip()
    """

    def __init__(self) -> None:
        self.available = False
        self.device: str | None = None
        self.volume = 1.0
        self._blip: pygame.mixer.Sound | None = None

    # --- Lifecycle -------------------------------------------------------

    def init(self, device: str | None = None, volume: float = 1.0) -> bool:
        """Open the mixer on ``device`` (None == system default).

        Returns True on success. On failure the manager stays usable but
        silent (``available`` is False).
        """
        self.volume = max(0.0, min(1.0, volume))
        try:
            pygame.mixer.quit()  # harmless if not initialized
            pygame.mixer.init(
                frequency=_FREQUENCY,
                size=_SIZE,
                channels=_CHANNELS,
                devicename=device,
            )
        except pygame.error:
            self.available = False
            self.device = None
            self._blip = None
            return False
        self.available = True
        self.device = device
        self._blip = self._make_blip()
        return True

    def set_device(self, device: str | None) -> bool:
        """Switch the output device, rebuilding the blip for the new mixer.

        Falls back to the default device if the requested one won't open, so
        the setting can never wedge audio permanently.
        """
        if device == self.device and self.available:
            return True
        if self.init(device, self.volume):
            return True
        # Requested device failed: retry the system default so we don't end
        # up silent because of one bad choice.
        return self.init(None, self.volume)

    def set_volume(self, volume: float) -> None:
        """Set master volume (0.0 .. 1.0), applied to the blip on next play."""
        self.volume = max(0.0, min(1.0, volume))
        if self._blip is not None:
            self._blip.set_volume(self.volume)

    # --- Enumeration -----------------------------------------------------

    @staticmethod
    def list_devices() -> list[str]:
        """Names of available playback devices, or [] if none/unsupported."""
        try:
            from pygame._sdl2 import audio as sdl2_audio

            return list(sdl2_audio.get_audio_device_names(False))
        except (ImportError, pygame.error, AttributeError):
            return []

    # --- Playback --------------------------------------------------------

    def play_blip(self) -> None:
        """Play the UI blip at the current master volume; no-op if silent."""
        if not self.available or self._blip is None:
            return
        self._blip.set_volume(self.volume)
        self._blip.play()

    # --- Synthesis -------------------------------------------------------

    def _make_blip(self) -> pygame.mixer.Sound | None:
        """Render a short enveloped square wave into a Sound, matching the
        mixer's actual (frequency, size, channels)."""
        init = pygame.mixer.get_init()
        if init is None:
            return None
        freq, size, channels = init
        n = int(freq * _BLIP_SECONDS)
        amplitude = 2 ** (abs(size) - 1) - 1  # peak for the sample depth
        period = freq / _BLIP_HZ

        # 'h' (signed 16-bit) covers the common -16 format; fall back to 'b'
        # for 8-bit. Unsigned formats are rare with our request, so we only
        # handle the signed cases and bail otherwise.
        typecode = {16: "h", 8: "b"}.get(abs(size))
        if typecode is None:
            return None

        samples = array.array(typecode)
        attack = int(n * 0.15)  # short fades kill the click at start/end
        release = int(n * 0.30)
        for i in range(n):
            square = 1.0 if (i % period) < (period / 2) else -1.0
            # Linear attack/release envelope.
            if i < attack:
                env = i / attack
            elif i > n - release:
                env = (n - i) / release
            else:
                env = 1.0
            value = int(square * env * amplitude * 0.6)
            for _ in range(channels):  # same value to every channel
                samples.append(value)

        sound = pygame.mixer.Sound(buffer=samples.tobytes())
        sound.set_volume(self.volume)
        return sound

    def quit(self) -> None:
        """Release the mixer (call on shutdown)."""
        if self.available:
            pygame.mixer.quit()
            self.available = False
