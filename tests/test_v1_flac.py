"""Actual native FLAC decoding versus independent known PCM/digests at8/16/24/32."""

import hashlib
from dataclasses import replace

import numpy as np
import pytest
from flac_fixtures import verbatim_flac

from music_project.core.decoder import PCMContext
from music_project.core.probe import probe
from music_project.core.technical_analysis import measure_technical


@pytest.mark.parametrize("bits", [8, 16, 24, 32])
@pytest.mark.parametrize("channels", [1, 2])
def test_independently_generated_flac_exact_pcm_md5_and_count(tmp_path, settings, bits, channels):
    rng = np.random.default_rng(9639 + bits)
    values = rng.integers(
        -(1 << (bits - 1)), 1 << (bits - 1), size=(8192, channels), dtype=np.int64
    )
    values[:5] = np.array([-(1 << (bits - 1)), (1 << (bits - 1)) - 1, -1, 0, 1])[:, None]
    path, pcm = verbatim_flac(tmp_path / f"native-{bits}.flac", values, bits)
    original = path.read_bytes()
    info = probe(path, settings)
    assert info.bit_depth == bits and info.channels == channels
    decoded = PCMContext.load(info, settings)
    np.testing.assert_array_equal(decoded.samples, values / 2 ** (bits - 1))
    result = measure_technical(info, settings)
    digest = result["pcm_integrity"].measurements["flac_md5"]
    assert digest["status"] == digest["md5_status"] == digest["frame_count_status"] == "Verified"
    assert digest["calculated_md5"] == hashlib.md5(pcm, usedforsecurity=False).hexdigest()
    assert digest["decoded_frames"] == len(values)
    assert path.read_bytes() == original


@pytest.mark.parametrize("bits", [8, 32])
def test_new_depths_do_not_verify_missing_mismatched_or_partial_digests(tmp_path, settings, bits):
    values = np.random.default_rng(32).integers(-120, 120, size=(8192, 1), dtype=np.int64)
    path, _ = verbatim_flac(tmp_path / "digest.flac", values, bits)
    info = probe(path, settings)
    original = bytearray(path.read_bytes())
    bad = original.copy()
    bad[26] ^= 1
    path.write_bytes(bad)
    actual = measure_technical(probe(path, settings), settings)["pcm_integrity"]
    assert actual.status == "Failed"
    assert actual.measurements["flac_md5"]["md5_status"] == "Failed"
    bad[26:42] = bytes(16)
    path.write_bytes(bad)
    missing = measure_technical(probe(path, settings), settings)["pcm_integrity"]
    assert missing.measurements["flac_md5"]["md5_status"] == "Unknown"
    path.write_bytes(original)
    partial = measure_technical(
        info, replace(settings, technical_mode="prefix", analysis_seconds=0.05)
    )
    assert partial["pcm_integrity"].measurements["flac_md5"]["md5_status"] == "Partial"


@pytest.mark.parametrize("bits", [8, 32])
def test_whole_flac_frame_removed_at_clean_boundary_fails_count_check(tmp_path, settings, bits):
    values = np.random.default_rng(9639).integers(-120, 120, size=(8192, 1), dtype=np.int64)
    path, _ = verbatim_flac(tmp_path / "truncated.flac", values, bits)
    # Keep exactly one valid verbatim frame, with correct CRC; retain the original
    # STREAMINFO count/digest. EOF without a damaged frame must not verify integrity.
    frame_bytes = 6 + 1 + 4096 * (bits // 8) + 2
    path.write_bytes(path.read_bytes()[: 42 + frame_bytes])
    finding = measure_technical(probe(path, settings), settings)["pcm_integrity"]
    check = finding.measurements["flac_md5"]
    assert finding.status == check["status"] == check["frame_count_status"] == "Failed"
    assert check["decoded_frames"] == 4096 and check["expected_frames"] == 8192
