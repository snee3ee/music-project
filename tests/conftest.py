import shutil
import wave
from dataclasses import replace

import numpy as np
import pytest

from music_project.core.config import Settings
from music_project.core.models import AudioInfo
from music_project.core.subprocess_utils import run


@pytest.fixture(scope="session")
def settings():
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("FFmpeg/ffprobe unavailable")
    return Settings(timeout=60, analysis_seconds=3)


@pytest.fixture
def write_wav():
    def write(path, samples, rate=48000, bits=16):
        x = np.asarray(samples)
        if x.ndim == 1:
            x = x[:, None]
        integers = np.clip(
            np.rint(x * 2 ** (bits - 1)), -(2 ** (bits - 1)), 2 ** (bits - 1) - 1
        ).astype(np.int32)
        if bits == 24:
            packed = (
                np.column_stack(
                    [
                        integers.ravel() & 255,
                        (integers.ravel() >> 8) & 255,
                        (integers.ravel() >> 16) & 255,
                    ]
                )
                .astype(np.uint8)
                .tobytes()
            )
        else:
            packed = integers.astype("<i2").tobytes()
        with wave.open(str(path), "wb") as stream:
            stream.setnchannels(x.shape[1])
            stream.setsampwidth(bits // 8)
            stream.setframerate(rate)
            stream.writeframes(packed)
        return path

    return write


@pytest.fixture
def tone(tmp_path, write_wav):
    t = np.arange(48000 * 3) / 48000
    return write_wav(tmp_path / "тест 日本語.wav", 0.25 * np.sin(2 * np.pi * 1000 * t))


@pytest.fixture
def encode(settings):
    def convert(source, target, *options):
        run(
            [
                settings.ffmpeg,
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
        return target

    return convert


@pytest.fixture
def info():
    return AudioInfo(
        "synthetic.wav", "wav", "pcm_s24le", "PCM", 96000, 1, "mono", 24, 3, 0, None, True
    )


@pytest.fixture
def make_context(info):
    from music_project.core.decoder import PCMContext

    def make(samples, rate=96000, **changes):
        x = np.asarray(samples, dtype=np.float64)
        if x.ndim == 1:
            x = x[:, None]
        return PCMContext(replace(info, sample_rate=rate, channels=x.shape[1], **changes), x, 3)

    return make
