import hashlib
import json
import shutil
import sys
from dataclasses import replace

import numpy as np
import pytest
from scipy import signal

from music_project.core.analysis import analyze
from music_project.core.compare import compare_pcm
from music_project.core.decoder import PCMContext, canonical_hash
from music_project.core.library import Library, duplicate_groups
from music_project.core.pcm import spectral_findings
from music_project.core.probe import probe
from music_project.core.subprocess_utils import run


def test_streaming_does_not_collect_full_pcm():
    digest = hashlib.sha256()
    result = run(
        [sys.executable, "-c", "import sys; sys.stdout.buffer.write(b'x'*10000000)"],
        max_bytes=10,
        consume=digest.update,
    )
    assert not result.stdout
    assert digest.hexdigest() == hashlib.sha256(b"x" * 10000000).hexdigest()


def test_cutoff_is_also_caused_by_filtering(make_context):
    rng = np.random.default_rng(17)
    spectrum = np.fft.rfft(rng.normal(0, 0.1, 96000 * 2))
    frequencies = np.fft.rfftfreq(96000 * 2, 1 / 96000)
    spectrum[frequencies > 16000] = 0
    filtered = np.fft.irfft(spectrum)
    result, _up = spectral_findings(make_context(filtered))
    assert result.status == "Medium suspicion"
    assert result.evidence == ["BAND_LIMIT"]
    # This fixture has never had a lossy codec: evidence cannot prove a transcode.


def test_memory_budget_scope(tone, settings):
    info = probe(tone, settings)
    context = PCMContext.load(info, replace(settings, max_pcm_bytes=48000 * 8))
    assert context.samples.nbytes <= 48000 * 8
    assert context.scope["decoded_seconds"] == 1


def test_24bit_hash_preserves_padding_and_context(tmp_path, write_wav, settings):
    rng = np.random.default_rng(21)
    x = rng.integers(-32000, 32000, 48000) / 32768
    a = write_wav(tmp_path / "16.wav", x)
    b = write_wav(tmp_path / "24.wav", x, bits=24)
    assert canonical_hash(probe(a), settings) == canonical_hash(probe(b), settings)
    result, _context = analyze(b, settings)
    assert result.findings["quantization"].status == "Direct 16→24 padding evidence"
    json.dumps(result.to_dict(), allow_nan=False)


def test_periodic_alignment_is_ambiguous(make_context):
    t = np.arange(96000 * 2) / 96000
    x = np.sin(2 * np.pi * 1000 * t) * 0.1
    y = np.roll(x, 11)
    result = compare_pcm(make_context(x), make_context(y))
    assert result.status == "Ambiguous"
    assert result.measurements["residual_rms_dbfs_after_gain"] is None


def test_corrupted_exact_duplicates_still_reported(tmp_path, settings):
    root = tmp_path / "broken"
    root.mkdir()
    (root / "a.flac").write_bytes(b"broken")
    shutil.copyfile(root / "a.flac", root / "b.flac")
    lib = Library(tmp_path / "index.sqlite3")
    lib.scan(root, settings)
    assert len(duplicate_groups(lib.records())) == 1
    assert not duplicate_groups(lib.records(), "pcm_sha256")


def test_container_detection_does_not_trust_extension(tone, tmp_path, settings):
    renamed = tmp_path / "not-really-flac.flac"
    shutil.copyfile(tone, renamed)
    info = probe(renamed, settings)
    assert info.container == "wav" and info.codec == "pcm_s16le"


def test_stereo_wav_flac_canonical_order(tmp_path, write_wav, encode, settings):
    rng = np.random.default_rng(79)
    pcm = rng.normal(0, 0.1, (48000, 2))
    wav = write_wav(tmp_path / "stereo.wav", pcm)
    flac = encode(wav, tmp_path / "stereo.flac")
    assert canonical_hash(probe(wav), settings) == canonical_hash(probe(flac), settings)


def test_future_database_schema_preserved(tmp_path):
    import sqlite3

    database = tmp_path / "future.sqlite3"
    with sqlite3.connect(database) as db:
        db.execute("PRAGMA user_version=99")
    from music_project.core.models import AudioError

    with pytest.raises(AudioError, match="schema version"):
        Library(database)
    with sqlite3.connect(database) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 99


@pytest.mark.parametrize("transform", ["different", "eq"])
def test_nonidentical_pcm_not_grouped(tmp_path, write_wav, settings, transform):
    root = tmp_path / "collection"
    root.mkdir()
    rng = np.random.default_rng(7)
    x = rng.normal(0, 0.1, 48000)
    y = (
        rng.normal(0, 0.1, 48000)
        if transform == "different"
        else signal.lfilter([0.5, 0.5], [1], x)
    )
    write_wav(root / "a.wav", x)
    write_wav(root / "b.wav", y)
    lib = Library(tmp_path / "index.sqlite3")
    lib.scan(root, settings)
    assert not duplicate_groups(lib.records(), "pcm_sha256")
