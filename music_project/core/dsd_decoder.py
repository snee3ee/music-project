"""Streaming FFmpeg DSD conversion with output-header validation and no audio files."""

import math
import struct
from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np

from music_project.core.config import Settings
from music_project.core.decoder import input_args
from music_project.core.models import AudioError, AudioInfo, DecoderError
from music_project.core.subprocess_utils import run

PCM_RATES = (176400, 352800)
PREROLL_SECONDS = 0.25
RESAMPLE = "aresample={rate}:resampler=swr:filter_size=32:phase_shift=10:linear_interp=0:cutoff=0.97:dither_method=none"


def quick_windows(duration: float | None, width: float = 5) -> list[tuple[float, float]]:
    if not math.isfinite(width) or width <= 0:
        raise AudioError("Invalid quick window width")
    if duration is None or not math.isfinite(duration) or duration <= 0:
        raise AudioError("Unknown duration: deterministic DSD windows unavailable")
    if duration <= 3 * width:
        return [(0.0, duration)]
    return [(0.0, width), ((duration - width) / 2, width), (duration - width, width)]


class FloatWaveStream:
    """Parse RIFF/WAVE float32 incrementally, including WAVEFORMATEXTENSIBLE."""

    def __init__(self, rate: int, channels: int, consume: Callable[[np.ndarray], None]):
        self.rate, self.channels, self.consume = rate, channels, consume
        self.pending = b""
        self.riff_seen = False
        self.format_verified = False
        self.in_data = False
        self.frames = 0
        self.header: dict = {}
        self.data_bytes: int | None = None
        self.received_bytes = 0

    def feed(self, block: bytes):
        data = self.pending + block
        self.pending = b""
        if not self.in_data:
            if not self.riff_seen:
                if len(data) < 12:
                    self.pending = data
                    return
                if data[:4] != b"RIFF" or data[8:12] != b"WAVE":
                    raise AudioError("Conversion output is not RIFF/WAVE")
                self.riff_seen = True
                data = data[12:]
            while len(data) >= 8:
                tag, n = struct.unpack("<4sI", data[:8])
                if tag == b"data":
                    if not self.format_verified:
                        raise AudioError("PCM data before validated output format")
                    self.in_data = True
                    self.data_bytes = n if n != 0xFFFFFFFF else None
                    data = data[8:]
                    break
                if n > 65536:
                    raise AudioError("Conversion output header exceeds bounded limit")
                end = 8 + n + n % 2
                if len(data) < end:
                    break
                if tag == b"fmt ":
                    self._format(data[8 : 8 + n])
                data = data[end:]
            if not self.in_data:
                self.pending = data
                return
        frame_bytes = 4 * self.channels
        count = len(data) // frame_bytes * frame_bytes
        if count:
            self.received_bytes += count
            if self.data_bytes is not None and self.received_bytes > self.data_bytes:
                raise AudioError("Unexpected bytes after converted PCM data")
            samples = np.frombuffer(data[:count], dtype="<f4").reshape(-1, self.channels)
            if not np.isfinite(samples).all():
                raise AudioError("Converted PCM contains NaN/Infinity")
            self.consume(samples)
            self.frames += len(samples)
        self.pending = data[count:]

    def _format(self, data: bytes):
        if len(data) < 16 or self.format_verified:
            raise AudioError("Invalid/duplicate converted WAV format")
        tag, channels, rate, byte_rate, align, bits = struct.unpack("<HHIIHH", data[:16])
        mask = None
        if tag == 0xFFFE:
            if len(data) < 40 or data[24:40] != bytes.fromhex("0300000000001000800000aa00389b71"):
                raise AudioError("Output is not extensible IEEE float PCM")
            valid_bits, mask = struct.unpack("<HI", data[18:24])
            if valid_bits != 32 or mask != (4 if channels == 1 else 3):
                raise AudioError("Converted PCM channel layout/valid bits mismatch")
        elif tag != 3:
            raise AudioError("Output is not IEEE float PCM")
        if (channels, rate, bits, align, byte_rate) != (
            self.channels,
            self.rate,
            32,
            channels * 4,
            rate * channels * 4,
        ):
            raise AudioError("Actual converted sample rate/channels/format mismatch")
        self.header = {
            "sample_rate_hz": rate,
            "channels": channels,
            "bits": bits,
            "channel_mask": mask,
            "channel_layout_verification": "WAVE extensible mask"
            if mask
            else "count only; explicit backend layout requested",
        }
        self.format_verified = True

    def finish(self):
        if (
            not self.in_data
            or not self.frames
            or self.pending
            or (self.data_bytes is not None and self.received_bytes != self.data_bytes)
        ):
            raise AudioError("Empty/truncated converted PCM stream")


@dataclass
class ConversionAttempt:
    start_seconds: float
    requested_seconds: float | None
    command: list[str] = field(default_factory=list)
    status: str = "Unknown"
    frames: int = 0
    output_header: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    fatal_error: str | None = None


def convert_window(
    info: AudioInfo,
    settings: Settings,
    start: float,
    duration: float | None,
    consume: Callable[[np.ndarray], None],
    *,
    progress: Callable[[float], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> ConversionAttempt:
    result = ConversionAttempt(start, duration)
    rate = settings.dsd_pcm_rate
    parser = FloatWaveStream(rate, info.channels, consume)
    try:
        if info.kind != "DSD" or not info.codec.startswith("dsd_"):
            raise AudioError("Unsupported: only verified uncompressed DSD decoder family")
        if rate not in PCM_RATES or info.channels not in (1, 2):
            raise AudioError("Unsupported: conversion requires mono/stereo and 176400/352800 Hz")
        if (
            not math.isfinite(start)
            or start < 0
            or duration is not None
            and (not math.isfinite(duration) or duration <= 0)
        ):
            raise AudioError("Invalid conversion range")
        command = input_args(info, settings)
        command[command.index("error")] = "level+warning"
        if start:
            seek = max(0, start - PREROLL_SECONDS)
            index = command.index("-i")
            command[index:index] = ["-ss", f"{seek:.9f}"]
            command += ["-ss", f"{start - seek:.9f}"]
        if duration is not None:
            command += ["-t", f"{duration:.9f}"]
        command += [
            "-af",
            RESAMPLE.format(rate=rate),
            "-ar",
            str(rate),
            "-ac",
            str(info.channels),
            "-channel_layout",
            "mono" if info.channels == 1 else "stereo",
            "-c:a",
            "pcm_f32le",
            "-f",
            "wav",
            "pipe:1",
        ]
        result.command = command

        def feed(block):
            if cancelled and cancelled():
                raise AudioError("Cancelled: декодирование остановлено")
            parser.feed(block)
            if progress:
                progress(parser.frames / rate)

        output = run(command, timeout=settings.timeout, consume=feed, cancelled=cancelled)
        result.warnings = output.stderr.splitlines()
        parser.finish()
        result.status = "Passed"
    except AudioError as exc:
        if isinstance(exc, DecoderError):
            result.warnings = [line for line in exc.diagnostics.splitlines() if "[warning]" in line]
        result.fatal_error = str(exc)
        result.status = (
            "Unsupported"
            if str(exc).startswith(("Unsupported", "Backend unavailable"))
            else "Failed"
        )
        if str(exc).startswith("Cancelled") or "время ожидания" in str(exc):
            result.status = "Partial"
    result.frames, result.output_header = parser.frames, parser.header
    return result
