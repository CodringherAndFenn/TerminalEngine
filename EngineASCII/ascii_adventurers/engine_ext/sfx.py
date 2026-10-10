"""
engine_ext/sfx.py -- synthesized sound effects (no asset files).

The engine's Audio owns the mixer (device, master volume) but only plays its
UI blip, so game sounds are generated here with the same numpy-free
approach: samples computed in pure Python into a raw PCM buffer matching
the mixer's actual format, wrapped in pygame.mixer.Sound. If the engine has
no working audio device, every call is a silent no-op.

Levels. Every recipe is first normalized to the same loudness (RMS), then
scaled by its entry in MIX -- so how loud each sound is relative to the
others is decided in one table, not by accident of how it was synthesized.

Variety. Each sound is rendered in VARIANTS slightly different pitches
(resampled +-7%), and each play picks one at random with a small random
volume change, so a weapon firing over and over doesn't hammer the exact
same sample. (Sound only -- this randomness never touches the game.)

Recipes (deterministic -- the noise uses a fixed seed):
  bolt     soft "pew": a sine sweeping down            (placeholder magic bolt)
  spark    electric crackle over a falling whine       (wizard's shock bolt)
  bow      plucked string twang with a click           (huntress, goblin archers)
  chime    bright three-note bell                      (princess's rainbow)
  hex      dark swoop down with hiss                   (warlock)
  orb      bubbly upward bloop                         (spell tower)
  boulder  noise burst + low thump                     (ogre's rock)
  hit      short low-passed noise tick
  break    longer, darker rumble (a tile being destroyed)
  fizzle   very quiet soft puff
  zap      buzzy square wave (lightning jumping between enemies)
  swing    soft airy whoosh (a sword; no hero uses one now)
  axe      whirring whoosh, pulsing as it spins     (dwarf's throwing axes)
  pulse    soft plucked major chord (the bard's lute)
  ui       short soft sine blip (menus; replaces the engine's louder blip)
"""

from __future__ import annotations

import array
import math
import random

import pygame

from engine import Audio

from .. import config

TARGET_RMS = 0.16          # every sound is levelled to this before MIX
VARIANTS = (0.93, 1.0, 1.07)   # pitch factors rendered per sound
VOLUME_JITTER = 0.1        # +-10% loudness per play

# Relative loudness of each sound (1.0 = TARGET_RMS). The one place to
# balance the mix.
MIX = {
    "bolt": 0.8, "spark": 0.75, "bow": 0.85, "chime": 0.7, "hex": 0.8, "orb": 0.7,
    "boulder": 1.0, "hit": 0.75, "break": 1.0, "fizzle": 0.2, "zap": 0.55,
    "swing": 0.6, "axe": 0.6, "pulse": 0.8, "ui": 0.55, "whistle": 0.5,
}


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


def _level(samples: list[float], gain: float) -> list[float]:
    """Scale to TARGET_RMS * gain, but never past full scale."""
    rms = math.sqrt(sum(v * v for v in samples) / max(1, len(samples)))
    peak = max((abs(v) for v in samples), default=0.0)
    if rms <= 0:
        return samples
    k = min(TARGET_RMS * gain / rms, 0.98 / peak)
    return [v * k for v in samples]


def _repitch(samples: list[float], factor: float) -> list[float]:
    """Resample by `factor` (>1 = higher and shorter), linear interpolation."""
    if factor == 1.0:
        return samples
    n = int(len(samples) / factor)
    out = []
    last = len(samples) - 1
    for i in range(n):
        x = i * factor
        j = int(x)
        f = x - j
        out.append(samples[j] * (1 - f) + samples[min(j + 1, last)] * f)
    return out


def _recipes(freq: int) -> dict[str, list[float]]:
    """Raw (un-levelled) samples of every sound."""
    rng = random.Random(0x7A4C)

    def noise() -> float:
        return rng.uniform(-1.0, 1.0)

    def sweep(f0: float, f1: float, tau: float):
        """Phase of a sine gliding from f0 toward f1 with time constant tau
        (integrated, so the glide has no clicks)."""
        def phase(t):
            return 2 * math.pi * (f1 * t + (f0 - f1) * tau * (1 - math.exp(-t / tau)))
        return phase

    pew = sweep(1100.0, 320.0, 0.05)

    def bolt(t, u):
        return math.sin(pew(t)) * math.exp(-t / 0.06)

    whine = sweep(2600.0, 900.0, 0.06)

    def spark(t, u):
        crackle = noise() * (1.0 if (int(t * 1400) * 7919) % 5 < 2 else 0.15)
        return (0.6 * crackle + 0.5 * math.sin(whine(t))) * math.exp(-t / 0.045)

    bend = sweep(230.0, 196.0, 0.03)

    def bow(t, u):
        string = math.sin(bend(t)) + 0.35 * math.sin(2 * bend(t)) + 0.15 * math.sin(3 * bend(t))
        click = noise() * math.exp(-t / 0.003)
        return string * math.exp(-t / 0.08) + 0.7 * click

    def chime(t, u):
        env = math.exp(-t / 0.11) * min(1.0, t / 0.002)
        return env * (math.sin(2 * math.pi * 1568 * t) + 0.7 * math.sin(2 * math.pi * 2093 * t)
                      + 0.45 * math.sin(2 * math.pi * 2637 * t) + 0.2 * math.sin(2 * math.pi * 4186 * t))

    # P6: calling the mount -- two quick whistled notes, the second higher.
    wh1, wh2 = sweep(1500.0, 1900.0, 0.04), sweep(1900.0, 2500.0, 0.04)

    def whistle(t, u):
        if t < 0.12:
            return math.sin(wh1(t)) * min(1.0, t / 0.01) * (1 - t / 0.12) ** 0.3
        t2 = t - 0.16
        if t2 < 0:
            return 0.0
        return math.sin(wh2(t2)) * min(1.0, t2 / 0.01) * math.exp(-t2 / 0.12)

    swoop = sweep(520.0, 150.0, 0.12)

    def hex_(t, u):
        return (math.sin(swoop(t)) * 0.8 + 0.25 * noise()) * math.sin(math.pi * u) ** 1.5

    rise = sweep(260.0, 700.0, 0.04)

    def orb(t, u):
        return math.sin(rise(t)) * math.exp(-t / 0.05) * min(1.0, t / 0.003)

    def boulder(t, u):
        env = math.exp(-t / 0.045)
        f = 40 + 50 * math.exp(-t / 0.05)             # pitch sweeps down
        thump = math.sin(2 * math.pi * f * t) * math.exp(-t / 0.09)
        return 0.55 * noise() * env + 0.75 * thump

    def zap(t, u):
        # Lightning jumping: a buzzy square wave at a jittering pitch.
        f = 900 + 500 * math.sin(2 * math.pi * 37 * t)
        square = 1.0 if math.sin(2 * math.pi * f * t) > 0 else -1.0
        return 0.35 * square * (1 - u) + 0.2 * noise() * math.exp(-t / 0.02)

    def pulse(t, u):
        # The bard's beat: a soft plucked major chord.
        env = math.exp(-t / 0.18)
        return env * sum(0.3 * math.sin(2 * math.pi * f * t) for f in (262.0, 330.0, 392.0))

    def ui(t, u):
        # Menu blip: a soft sine with a quick fade in/out. (The engine's own
        # blip is a full square wave at master volume -- ~5x louder than the
        # game's sounds -- so the game's menus use this one, which also
        # follows the effects volume.)
        env = min(1.0, t / 0.005) * (1 - u) ** 2
        return env * math.sin(2 * math.pi * 660 * t)

    # The sword: air, not metal -- noise darkened twice, swelling and fading
    # smoothly (no hard edges to grate when it repeats).
    whoosh = _lowpass(_lowpass(_render(0.2, lambda t, u: noise() * math.sin(math.pi * u) ** 2,
                                       freq), 0.09), 0.2)
    # A thrown axe: the same dark air, chopped by its spin (~24 turns/s).
    whirr = _lowpass(_lowpass(_render(
        0.24, lambda t, u: noise() * math.sin(math.pi * u) * (0.35 + 0.65 * abs(math.sin(math.pi * 24 * t))),
        freq), 0.12), 0.25)
    hit = _lowpass(_render(0.09, lambda t, u: noise() * math.exp(-t / 0.025), freq), 0.35)
    brk = _lowpass(_render(0.3, lambda t, u: noise() * math.exp(-t / 0.08), freq), 0.12)
    fizzle = _lowpass(_render(0.12, lambda t, u: noise() * (1 - u), freq), 0.2)
    return {
        "bolt": _render(0.12, bolt, freq),
        "spark": _render(0.14, spark, freq),
        "bow": _render(0.22, bow, freq),
        "chime": _render(0.3, chime, freq),
        "hex": _render(0.3, hex_, freq),
        "orb": _render(0.13, orb, freq),
        "boulder": _render(0.22, boulder, freq),
        "hit": hit,
        "break": brk,
        "fizzle": fizzle,
        "zap": _render(0.09, zap, freq),
        "swing": whoosh,
        "axe": whirr,
        "pulse": _render(0.45, pulse, freq),
        "ui": _render(0.08, ui, freq),
        "whistle": _render(0.42, whistle, freq),
    }


def mixed(freq: int) -> dict[str, list[list[float]]]:
    """name -> pitch variants, levelled per MIX (what gets played)."""
    out = {}
    for name, raw in _recipes(freq).items():
        base = _level(raw, MIX.get(name, 1.0))
        out[name] = [_repitch(base, f) for f in VARIANTS]
    return out


class Sfx:
    def __init__(self, audio: Audio, volume: float = config.SFX_VOLUME) -> None:
        self.audio = audio
        self.volume = volume          # effects volume, on top of the master volume
        self._sounds: dict[str, list[pygame.mixer.Sound]] = {}
        self._rng = random.Random()   # which variant / how loud: sound only
        if audio.available:
            self._build()

    def rebuild(self) -> None:
        """Re-make the sounds for the current mixer (after the output
        device changed, which re-opens the mixer in a maybe different
        format)."""
        self._sounds = {}
        if self.audio.available:
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
        for name, variants in mixed(freq).items():
            sounds = []
            for samples in variants:
                buf = array.array(typecode)
                for v in samples:
                    s = int(max(-1.0, min(1.0, v)) * peak)
                    for _ in range(channels):
                        buf.append(s)
                sounds.append(pygame.mixer.Sound(buffer=buf.tobytes()))
            self._sounds[name] = sounds

    # Events that reuse another sound at a lower volume.
    _ALIASES = {"thud": ("hit", 0.45),    # a shell sparking off terrain it can't hurt
                "shot": ("bolt", 1.0),    # older name for the generic shot
                "nova": ("pulse", 0.6)}   # Frost Nova (a softer beat)

    def play(self, name: str) -> None:
        """Play a named effect at master volume x effects volume (no-op if
        silent), in a random one of its variants."""
        name, gain = self._ALIASES.get(name, (name, 1.0))
        variants = self._sounds.get(name)
        if not variants or not self.audio.available:
            return
        sound = self._rng.choice(variants)
        jitter = 1.0 + self._rng.uniform(-VOLUME_JITTER, VOLUME_JITTER)
        sound.set_volume(min(1.0, self.audio.volume * self.volume * gain * jitter))
        sound.play()
