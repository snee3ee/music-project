import hashlib
import json
from dataclasses import dataclass

import numpy as np

from music_project.core.config import Settings
from music_project.core.models import AudioError, AudioInfo
from music_project.core.subprocess_utils import run


def input_args(info: AudioInfo, settings: Settings) -> list[str]:
    return [
        settings.require("ffmpeg"),
        "-hide_banner",
        "-nostdin",
        "-v",
        "error",
        "-xerror",
        "-err_detect",
        "explode",
        "-protocol_whitelist",
        "file,pipe",
        "-i",
        info.path,
        "-map",
        "0:a:0",
        "-vn",
    ]


@dataclass
class PCMContext:
    info: AudioInfo
    samples: np.ndarray
    seconds_limit: float

    @classmethod
    def load(cls, info: AudioInfo, settings: Settings = Settings()):
        if info.kind == "DSD":
            raise AudioError("Native DSD: PCM-анализ неприменим без явного преобразования")
        if not (0 < info.sample_rate <= 768000 and 0 < info.channels <= 32):
            raise AudioError("Unsupported: частота или число каналов вне лимита анализа")
        limit = min(
            settings.analysis_seconds,
            settings.max_pcm_bytes / (info.sample_rate * info.channels * 8),
        )
        if limit <= 0:
            raise AudioError("Некорректная длительность анализа")
        data = run(
            input_args(info, settings)
            + ["-t", str(limit), "-f", "f64le", "-acodec", "pcm_f64le", "-"],
            timeout=settings.timeout,
            max_bytes=settings.max_pcm_bytes,
        ).stdout
        frame_bytes = info.channels * 8
        if not data or len(data) % frame_bytes:
            raise AudioError("Пустой или неполный декодированный PCM")
        samples = np.frombuffer(data, dtype="<f8").reshape(-1, info.channels)
        if not np.isfinite(samples).all():
            raise AudioError("PCM содержит NaN/Infinity")
        return cls(info, samples, limit)

    @property
    def scope(self) -> dict:
        return {
            "strategy": "prefix",
            "start_seconds": 0,
            "decoded_seconds": len(self.samples) / self.info.sample_rate,
            "frames": len(self.samples),
            "channels": self.info.channels,
            "format": "f64le, native sample rate and channel order; no downmix",
            "complete_file": bool(
                self.info.duration is not None
                and len(self.samples) / self.info.sample_rate
                >= self.info.duration - 1 / self.info.sample_rate
            ),
        }


def verify_decode(info: AudioInfo, settings: Settings = Settings()) -> None:
    run(input_args(info, settings) + ["-f", "null", "-"], timeout=settings.timeout)


def canonical_hash(info: AudioInfo, settings: Settings = Settings()) -> str:
    """Exact integer lossless PCM only, no rate/channel conversion or normalization."""
    if not info.lossless or info.kind == "DSD" or info.bit_depth not in (8, 16, 24, 32):
        raise AudioError("Not applicable: canonical hash требует lossless integer PCM <=32 bit")
    if not 0 < info.channels <= 32 or info.sample_rate <= 0:
        raise AudioError("Unsupported: invalid PCM sample rate/channel count")
    if info.codec.startswith("pcm_f") or info.codec in {"wavpack"}:
        raise AudioError("Unsupported: float/hybrid WavPack identity не валидирована")
    # A single channel has no ordering ambiguity. Do not infer unknown multichannel layouts.
    layout = "mono" if info.channels == 1 else info.channel_layout
    if layout == "Unknown" and info.channels == 2 and info.container in {"wav", "aiff"}:
        layout = "stereo"  # Standard stereo order in these conventional PCM containers.
    header = {
        "version": "pcm-s32le-v1",
        "rate": info.sample_rate,
        "channels": info.channels,
        "layout": layout,
    }
    digest = hashlib.sha256(json.dumps(header, sort_keys=True).encode() + b"\0")
    count = 0

    def consume(block: bytes):
        nonlocal count
        count += len(block)
        digest.update(block)

    run(
        input_args(info, settings) + ["-f", "s32le", "-acodec", "pcm_s32le", "-"],
        timeout=settings.timeout,
        consume=consume,
    )
    if not count or count % (info.channels * 4):
        raise AudioError("Пустой/неполный поток canonical PCM")
    return digest.hexdigest()
