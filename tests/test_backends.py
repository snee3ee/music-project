import sys
from dataclasses import replace

import numpy as np
import pytest

from music_project.core.analysis import analyze
from music_project.core.config import Settings
from music_project.core.decoder import PCMContext, canonical_hash, verify_decode
from music_project.core.models import AudioError
from music_project.core.pcm import loudness, spectral_findings
from music_project.core.probe import probe
from music_project.core.subprocess_utils import run


def test_unicode_probe_and_loudness(tone, settings):
    info = probe(tone, settings)
    assert info.sample_rate == 48000 and info.bit_depth == 16 and info.channels == 1
    context = PCMContext.load(info, settings)
    assert len(context.samples) == 144000
    measured = loudness(info, settings)
    assert measured.measurements["true_peak_dbtp"] == pytest.approx(-12.04, abs=0.1)
    assert measured.measurements["integrated_lufs"] == pytest.approx(-15.1, abs=0.4)


@pytest.mark.parametrize(
    "extension,options,codec",
    [
        ("flac", ["-c:a", "flac"], "flac"),
        ("mp3", ["-c:a", "libmp3lame", "-b:a", "128k"], "mp3"),
        ("m4a", ["-c:a", "alac"], "alac"),
        ("aiff", ["-c:a", "pcm_s16be"], "pcm_s16be"),
        ("ogg", ["-c:a", "libvorbis"], "vorbis"),
        ("opus", ["-c:a", "libopus"], "opus"),
    ],
)
def test_verified_formats(tone, tmp_path, encode, settings, extension, options, codec):
    target = encode(tone, tmp_path / f"audio.{extension}", *options)
    info = probe(target, settings)
    assert info.codec == codec
    verify_decode(info, settings)
    assert PCMContext.load(info, settings).samples.size > 0


def test_hash_pcm_identity(tone, tmp_path, encode, settings):
    flac = encode(tone, tmp_path / "different-tags.flac", "-metadata", "title=Другое имя")
    assert canonical_hash(probe(tone), settings) == canonical_hash(probe(flac), settings)


@pytest.mark.parametrize("case", ["invalid", "truncated"])
def test_invalid_audio(tone, tmp_path, settings, case):
    target = tmp_path / "broken.wav"
    target.write_bytes(b"not audio" if case == "invalid" else tone.read_bytes()[:1000])
    with pytest.raises(AudioError):
        verify_decode(probe(target, settings), settings)


def test_missing_backend(tone):
    with pytest.raises(AudioError, match="Backend unavailable"):
        probe(tone, Settings(ffprobe="not-installed-ffprobe"))


def test_binary_diagnostics_and_timeout():
    result = run(
        [
            sys.executable,
            "-c",
            "import sys; sys.stdout.buffer.write(bytes([0,255])); "
            "sys.stderr.buffer.write(bytes([255,254]))",
        ]
    )
    assert result.stdout == bytes([0, 255])
    assert "\ufffd" in result.stderr
    with pytest.raises(AudioError, match="время"):
        run([sys.executable, "-c", "import time; time.sleep(10)"], timeout=0.1)
    with pytest.raises(AudioError, match="лимит"):
        run([sys.executable, "-c", "print('x'*1000)"], max_bytes=20)


def test_bounded_scope_and_analysis(tone, settings):
    settings = replace(settings, analysis_seconds=1)
    result, context = analyze(tone, settings)
    assert not result.scope["complete_file"]
    assert context.samples.shape == (48000, 1)
    assert result.findings["loudness"].status == "Measured"
    assert result.to_dict()["method_version"]


@pytest.mark.parametrize("bitrate", [128, 320])
def test_mp3_to_flac_has_uncertain_provenance(tmp_path, write_wav, encode, settings, bitrate):
    rng = np.random.default_rng(999)
    original = write_wav(tmp_path / "original.wav", rng.normal(0, 0.12, 44100 * 3), rate=44100)
    compressed = encode(original, tmp_path / "compressed.mp3", "-b:a", f"{bitrate}k")
    transcoded = encode(compressed, tmp_path / "transcoded.flac")
    context = PCMContext.load(probe(transcoded), settings)
    loss, _up = spectral_findings(context)
    assert loss.status in {"Medium suspicion", "Ambiguous"}
    assert loss.limitations
    # A 320k encode may have no usable boundary: no forced classification.
