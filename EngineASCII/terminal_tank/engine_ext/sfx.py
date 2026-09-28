"""
engine_ext/sfx.py -- synthesized sound effects (no asset files).

The engine's Audio owns the mixer (device, master volume) but only plays its
UI blip, so game sounds are generated here with the same numpy-free
approach: samples computed in pure Python into a raw PCM buffer matching
the mixer's actual format, wrapped in pygame.mixer.Sound. If the engine has
no working audio device, every call is a silent no-op.

Recipes (all deterministic -- the noise uses a fixed seed):
  shot    white noise burst + a low sine "thump" sweeping 90 -> 40 Hz
  hit     short low-passed noise tick
  break   longer, darker rumble (a tile being destroyed)
  fizzle  very quiet soft puff
"""

from __future__ import annotations

import array
import math
import random

import pygame

from engine import Audio

from .. import config


def _render(duration: float, sample_fn, freq: int) -> list[float]:
    n = int(freq * duration)
    return [sample_fn(i / freq, i / n) for i in range(n)]


def _lowpass(samples: list[float], alpha: float) -> list[float]:
    """One-pole low-pass: y += alpha * (x - y). Smaller alpha = darker."""
    out, y = [], 0.0
    for x in samples:
        y += alpha * (x - y)
        out.append(y)
    return out


def _recipes(freq: int) -> dict[str, list[float]]:
    rng = random.Random(0x7A4C)

    def noise() -> float:
        return rng.uniform(-1.0, 1.0)

    def shot(t, u):
        env = math.exp(-t / 0.045)
        f = 40 + 50 * math.exp(-t / 0.05)             # pitch sweeps down
        thump = math.sin(2 * math.pi * f * t) * math.exp(-t / 0.09)
        return 0.55 * noise() * env + 0.75 * thump

    hit = _lowpass(_render(0.09, lambda t, u: noise() * math.exp(-t / 0.025), freq), 0.35)
    brk = _lowpass(_render(0.3, lambda t, u: noise() * math.exp(-t / 0.08), freq), 0.12)
    fizzle = _lowpass(_render(0.12, lambda t, u: 0.25 * noise() * (1 - u), freq), 0.2)
    return {
        "shot": _render(0.22, shot, freq),
        "hit": [v * 1.6 for v in hit],
        "break": [v * 2.4 for v in brk],
        "fizzle": fizzle,
    }


class Sfx:
    def __init__(self, audio: Audio) -> None:
        self.audio = audio
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        if audio.available:
            self._build()

    def _build(self) -> None:
        init = pygame.mixer.get_init()
        if init is None:
            return
        freq, size, channels = init
        typecode = {16: "h", 8: "b"}.get(abs(size))
        if typecode is None:
            return
        peak = 2 ** (abs(size) - 1) - 1
        for name, samples in _recipes(freq).items():
            buf = array.array(typecode)
            for v in samples:
                s = int(max(-1.0, min(1.0, v)) * peak * 0.8)
                for _ in range(channels):
                    buf.append(s)
            self._sounds[name] = pygame.mixer.Sound(buffer=buf.tobytes())

    # Events that reuse another sound at a lower volume.
    _ALIASES = {"thud": ("hit", 0.45)}   # a shell sparking off terrain it can't hurt

    def play(self, name: str) -> None:
        """Play a named effect at master volume x SFX_VOLUME (no-op if silent)."""
        name, gain = self._ALIASES.get(name, (name, 1.0))
        sound = self._sounds.get(name)
        if sound is None or not self.audio.available:
            return
        sound.set_volume(self.audio.volume * config.SFX_VOLUME * gain)
        sound.play()
