"""Deterministic original synthetic PCM; no downloaded or user-owned recordings."""

import wave
from pathlib import Path

import numpy as np
from scipy import signal

from music_project.core.subprocess_utils import run


def encoder_capabilities(settings):
    text = run([settings.require("ffmpeg"), "-hide_banner", "-encoders"]).text
    names = {
        parts[1]
        for line in text.splitlines()
        if len(parts := line.split()) > 2 and parts[0].startswith("A")
    }
    result = {"mp3": "libmp3lame" in names, "aac": "aac" in names}
    for codec, encoder, option in [("mp3", "libmp3lame", "-joint_stereo"), ("aac", "aac", "fast")]:
        help_text = (
            run([settings.require("ffmpeg"), "-hide_banner", "-h", "encoder=" + encoder]).text
            if result[codec]
            else ""
        )
        result[codec + "_alternate_configuration"] = option in help_text
    return result


def original(rate, content="broadband", seconds=12, seed=12026):
    rng = np.random.default_rng(seed)
    t = np.arange(round(rate * seconds)) / rate
    x = rng.normal(0, 0.025, (len(t), 2))
    if content == "tonal":
        x *= 1e-5
        for ch in range(2):
            for f, a in [(440, 0.08), (997, 0.05), (3001, 0.01)]:
                x[:, ch] += a * np.sin(2 * np.pi * f * t + ch * 0.3)
    elif content == "transient":
        x *= 0.01
        for start in np.arange(0.5, seconds, 1.0):
            envelope = np.exp(-np.maximum(0, t - start) * 100) * (t >= start) * (t < start + 0.1)
            x += rng.normal(0, 0.2, x.shape) * envelope[:, None]
    else:
        # Continuous broadband plus tonal/time-varying content, not a codec model.
        x += (0.03 * np.sin(2 * np.pi * 997 * t) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.5 * t)))[
            :, None
        ]
    return x


def write_pcm(path, x, rate, bits=24):
    x = np.asarray(x)
    if x.ndim == 1:
        x = x[:, None]
    integers = np.clip(
        np.rint(x * 2 ** (bits - 1)), -(2 ** (bits - 1)), 2 ** (bits - 1) - 1
    ).astype("<i4")
    packed = (
        np.ascontiguousarray(integers)
        .view(np.uint8)
        .reshape(-1, 4)[:, : bits // 8]
        .copy()
        .tobytes()
    )
    with wave.open(str(path), "wb") as f:
        f.setnchannels(x.shape[1])
        f.setsampwidth(bits // 8)
        f.setframerate(rate)
        f.writeframes(packed)
    return Path(path)


def convert(settings, source, target, *options):
    run(
        [
            settings.require("ffmpeg"),
            "-hide_banner",
            "-v",
            "error",
            "-nostdin",
            "-y",
            "-i",
            str(source),
            *options,
            str(target),
        ],
        timeout=60,
    )
    return Path(target)


def lossy_chain(settings, source, folder, name, codec, bitrate, *, configuration="default"):
    encoded = folder / (name + (".mp3" if codec == "mp3" else ".m4a"))
    options = ["-c:a", "libmp3lame" if codec == "mp3" else "aac", "-b:a", f"{bitrate}k"]
    if codec == "mp3":
        options += ["-joint_stereo", "0" if configuration == "independent-stereo" else "1"]
    elif configuration == "fast":
        options += ["-aac_coder", "fast"]
    convert(settings, source, encoded, *options)
    target = convert(settings, encoded, folder / (name + ".flac"), "-c:a", "flac")
    return target


def negative(x, rate, kind):
    if kind == "band-limited":
        return signal.lfilter(signal.firwin(1025, 16000, fs=rate), [1], x, axis=0)
    if kind == "analog-style":
        return signal.sosfilt(signal.bessel(6, 14000, fs=rate, output="sos"), x, axis=0)
    if kind == "equalized":
        return x + 0.5 * signal.sosfilt(
            signal.butter(2, 3000, fs=rate, btype="high", output="sos"), x, axis=0
        )
    if kind == "hf-poor":
        return signal.sosfilt(signal.butter(8, 4000, fs=rate, output="sos"), x, axis=0)
    if kind == "limited":
        return np.tanh(x * 30) * 0.5
    if kind == "clipped":
        return np.clip(x * 50, -0.9, 0.9)
    if kind == "noisy":
        return x + np.random.default_rng(99).normal(0, 0.06, x.shape)
    if kind == "mono":
        return x[:, :1]
    if kind == "linear-phase":
        return signal.fftconvolve(
            x, signal.firwin(1025, 17000, fs=rate)[:, None], mode="same", axes=0
        )
    raise ValueError(kind)
