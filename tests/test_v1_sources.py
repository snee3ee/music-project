"""Sample-exact multirate logical sources, including nonintegral 75 fps grids."""

import wave
from pathlib import Path

import numpy as np
import pytest

from music_project.core.cue import open_cue, track_source
from music_project.core.decoder import PCMContext
from music_project.core.files import file_hash
from music_project.core.probe import probe
from music_project.core.source_extract import prepare_cue_track
from music_project.core.sources import analyze_source


@pytest.mark.parametrize("rate", [32000, 44100, 88200, 96000])
@pytest.mark.parametrize("codec", ["flac", "float64"])
def test_nonintegral_cue_grid_preserves_exact_native_samples(
    tmp_path, settings, encode, rate, codec
):
    rng = np.random.default_rng(7500 + rate)
    values = rng.integers(-30000, 30000, size=(rate * 5, 2), dtype=np.int16)
    wav = tmp_path / "источник 日本語.wav"
    with wave.open(str(wav), "wb") as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(rate)
        f.writeframes(values.astype("<i2").tobytes())
    options = ["-c:a", "flac"] if codec == "flac" else ["-c:a", "pcm_f64le"]
    audio = encode(wav, tmp_path / ("source.flac" if codec == "flac" else "float.wav"), *options)
    cue = tmp_path / "boundaries.cue"
    cue.write_text(
        f'FILE "{audio.name}" WAVE\nTRACK 01 AUDIO\nINDEX 01 00:00:00\n'
        "TRACK 02 AUDIO\nINDEX 01 00:03:01\nTRACK 03 AUDIO\nINDEX 01 00:04:02\n",
        encoding="utf-8",
    )
    original = file_hash(audio)
    tracks = open_cue(cue, settings)["tracks"]
    source = track_source(tracks[1])
    folder = tmp_path / "selected"
    folder.mkdir()
    target, extraction = prepare_cue_track(source, probe(audio, settings), folder, settings)
    first, last = (226 * rate + 74) // 75, (302 * rate + 74) // 75
    actual = PCMContext.load(probe(target, settings), settings)
    assert extraction["first_native_frame"] == first
    assert extraction["last_native_frame_exclusive"] == last
    np.testing.assert_array_equal(actual.samples, values[first:last] / 32768)
    assert file_hash(audio) == original
    if rate == 32000:
        result, context = analyze_source(source, settings)
        np.testing.assert_array_equal(context.samples, values[first:last] / 32768)
        assert result.scope["source_start_seconds"] == first / rate
        assert result.findings["pcm_integrity"].status == "Passed"
        assert not Path(result.info.raw["format"]["filename"]).exists()
