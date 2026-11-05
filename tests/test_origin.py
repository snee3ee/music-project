"""Ground-truth measurements and ambiguity controls, never provenance labels."""

import json
from dataclasses import replace

import numpy as np
import pytest
from dsd_fixtures import dff, dsf
from scipy.signal import firwin, lfilter, resample_poly, welch

from music_project.core.analysis import analyze
from music_project.core.dsd_container import inspect_dsd
from music_project.core.dsd_decoder import convert_window
from music_project.core.dsd_native import native_blocks, native_spectra
from music_project.core.dsd_spectrum import StreamingWelch
from music_project.core.models import AudioError, AudioInfo
from music_project.core.origin import investigate_origin
from music_project.core.origin_calibration import (
    CANDIDATES,
    CONTROL_FREQUENCIES,
    boundary_chain_valid,
    calibrate_response,
    controlled_bandwidth,
    generate_controls,
    response_key,
)
from music_project.core.origin_features import boundary_features, noise_features
from music_project.core.origin_reference import investigate_reference
from music_project.core.origin_temporal import OriginCollector
from music_project.core.probe import probe
from tools.validate_origin import write_pdm


def native_info(path, rate=2822400, channels=2, container="dsf"):
    return AudioInfo(
        str(path),
        container,
        "dsd_lsbf_planar" if container == "dsf" else "dsd_msbf",
        "DSD",
        rate,
        channels,
        "stereo" if channels == 2 else "mono",
        None,
        None,
        path.stat().st_size,
        None,
        False,
    )


@pytest.mark.parametrize("candidate", CANDIDATES)
def test_six_boundaries_have_numerical_evidence(candidate):
    f = np.arange(0, 160001, 50.0)
    p = np.where(f < candidate, 1e-9, 1e-13)
    b = next(
        b
        for b in boundary_features(f, np.column_stack((p, p / 2)))
        if b["candidate_hz"] == candidate
    )
    for c in b["channels"]:
        assert c["eligible"] and c["detected"]
        assert c["attenuation_db"] == pytest.approx(40)
        assert c["local_slope_db_per_khz"] < 0
        assert c["transition_width_hz"] == 0
        assert c["transition_uncertainty_hz"] == 100
        assert c["above_boundary_power_fs2"] > 0
    json.dumps(b, allow_nan=False)


@pytest.mark.parametrize("control", ["flat", "silence", "tiny", "unexcited", "tone", "rising"])
def test_adversarial_controls_do_not_force_a_boundary(control):
    f = np.arange(0, 160001, 50.0)
    p = np.full(len(f), 1e-9)
    if control == "silence":
        p *= 0
    if control == "tiny":
        p = np.where(f < 24000, 1e-25, 1e-29)
    if control == "unexcited":
        p = np.where(f < 10000, 1e-5, np.where(f < 24000, 1e-14, 1e-18))
    if control == "tone":
        p *= 1e-12
        p[np.argmin(abs(f - 23000))] = 1e-4
    if control == "rising":
        p *= (1 + f / 20000) ** 4
    assert not any(c["detected"] for b in boundary_features(f, p) for c in b["channels"])


def test_analog_filter_can_mimic_pcm_boundary_without_pcm_history():
    # Frequency response squared of an 80th-order analog Butterworth low-pass.
    f = np.arange(0, 160001, 50.0)
    p = 1e-9 / (1 + (f / 24000) ** 160)
    b = next(b for b in boundary_features(f, p) if b["candidate_hz"] == 24000)
    assert b["channels"][0]["detected"]  # Explicit false positive for a PCM-identity classifier.
    assert b["channels"][0]["transition_width_hz"] > 0


def test_zero_above_band_is_explicit_and_json_finite():
    f = np.arange(0, 100001, 50.0)
    p = np.where(f < 24000, 1e-9, 0)
    b = next(b for b in boundary_features(f, p) if b["candidate_hz"] == 24000)
    assert b["channels"][0]["attenuation_state"] == "positive infinity"
    json.dumps(b, allow_nan=False)
    assert boundary_features(f[:20], p[:20])[0]["status"] == "Unsupported"
    with pytest.raises(ValueError):
        boundary_features(f, p * np.nan)


def test_noise_regime_is_measured_but_smooth_slope_is_not_split():
    f = np.arange(0, 160001, 50.0)
    smooth = 1e-12 * np.maximum(f, 1) ** 2 / 20000**2
    result = noise_features(f, smooth)
    assert result["channels"][0]["regime_change"] is None
    assert result["channels"][0]["whole_slope_db_per_decade"] == pytest.approx(20, abs=0.02)
    piecewise = 1e-12 * np.where(f < 60000, 1, np.maximum(f, 1) ** 6 / 60000**6)
    result = noise_features(f, piecewise)
    change = result["channels"][0]["regime_change"]
    assert change and change["low_hz"] < 65000 and change["high_hz"] > 55000
    assert result["channels"][0]["plateaus_hz"]
    assert noise_features(f, np.zeros_like(f))["channels"][0]["status"] == "Unknown"
    assert noise_features(f, piecewise, maximum_hz=24000)["status"] == "Unsupported"


def test_channel_disagreement_and_rising_onset_remain_explicit():
    f = np.arange(0, 160001, 50.0)
    p = np.column_stack((np.where(f < 24000, 1e-9, 1e-13), np.full(len(f), 1e-9)))
    b = next(b for b in boundary_features(f, p) if b["candidate_hz"] == 24000)
    assert b["channels"][0]["detected"] and not b["channels"][1]["detected"]
    rising = 1e-14 * (np.maximum(f, 1) / 20000) ** 12
    n = noise_features(f, np.column_stack((rising, np.full(len(f), 1e-12))))
    assert n["channels"][0]["rising_onset_hz"] is not None
    assert n["channels"][1]["rising_onset_hz"] is None


@pytest.mark.parametrize("bit_order", [1, 8])
def test_direct_dsf_bits_channel_layout_offset_and_padding(tmp_path, bit_order):
    path = dsf(tmp_path / "bits.dsf", rate=2822400, seconds=0.02, bit_order=bit_order)
    info = native_info(path)
    structure = inspect_dsd(info)
    original = path.read_bytes()
    actual = np.concatenate(list(native_blocks(info, structure, 0, 1)))
    expected = (
        np.unpackbits(np.array([0x69], np.uint8), bitorder="little" if bit_order == 1 else "big")
        * 1.0
    )
    assert len(actual) == structure.samples_per_channel
    assert np.array_equal(actual[:, 0], np.resize(expected * 2 - 1, len(actual)))
    # Different bytes in each channel expose planar/interleaved confusion.
    raw = bytearray(original)
    offset = structure.audio_data_offset
    raw[offset : offset + 4096] = b"\x55" * 4096
    raw[offset + 4096 : offset + 8192] = b"\xf0" * 4096
    path.write_bytes(raw)
    x = np.concatenate(
        list(native_blocks(info, inspect_dsd(info), 13 / info.sample_rate, 101 / info.sample_rate))
    )
    assert x.shape == (101, 2)
    for ch, value in enumerate([0x55, 0xF0]):
        e = np.unpackbits(np.array([value], np.uint8), bitorder=structure.bit_order) * 2.0 - 1
        assert np.array_equal(x[:, ch], np.resize(e, 120)[13:114])


def test_direct_dff_bit_order_and_no_cross_channel_mix(tmp_path):
    path = dff(tmp_path / "bits.dff", seconds=0.02)
    info = native_info(path, container="dff")
    s = inspect_dsd(info)
    raw = bytearray(path.read_bytes())
    raw[s.audio_data_offset : s.audio_data_offset + 16] = b"\x55\xf0" * 8
    path.write_bytes(raw)
    x = np.concatenate(list(native_blocks(info, s, 3 / info.sample_rate, 31 / info.sample_rate)))
    for ch, value in enumerate([0x55, 0xF0]):
        e = np.unpackbits(np.array([value], np.uint8)) * 2.0 - 1
        assert np.array_equal(x[:, ch], np.resize(e, 40)[3:34])
    path.write_bytes(raw[: s.audio_data_offset + 2])
    with pytest.raises(AudioError, match="Truncated"):
        list(native_blocks(info, s, 0, 0.01))


def test_native_psd_matches_independent_scipy_normalization(tmp_path):
    path = dsf(tmp_path / "native.dsf", rate=2822400, seconds=0.12)
    info = native_info(path)
    s = inspect_dsd(info)
    result = native_spectra(info, s)
    w = result["windows"][0]
    x = np.concatenate(list(native_blocks(info, s, w["start_seconds"], w["duration_seconds"])))
    f, p = welch(
        x,
        info.sample_rate,
        window="hann",
        nperseg=result["nfft"],
        noverlap=result["nfft"] // 2,
        detrend=False,
        axis=0,
    )
    selected = f <= 160000
    np.testing.assert_allclose(w["density_fs2_per_hz"], p[selected], atol=1e-23, rtol=1e-10)
    assert w["one_fraction_per_channel"] == [0.5, 0.5]


def test_temporal_collector_reuses_fft_and_is_bounded():
    collector = OriginCollector(48000, 1, 4096)
    estimator = StreamingWelch(48000, 1, 4096, segment_consumer=collector.consume)
    collector.start_window(0)
    rng = np.random.default_rng(321)
    for _ in range(10):
        estimator.consume(rng.normal(size=(48000, 1)))
    estimator.end_window()
    collector.end_window()
    assert collector.result()["new_fft_computations"] == 0
    assert sum(c["fft_segments"] for c in collector.cells) == estimator.segments
    collector.target = 1
    for _ in range(140):
        collector.consume(np.full((2049, 1), 1e-10))
    result = collector.result()
    assert result["retained_cells"] <= 64 < result["measured_cells"]


@pytest.mark.parametrize("rate", [2822400, 5644800, 11289600, 22579200])
@pytest.mark.parametrize("output", [176400, 352800])
def test_actual_backend_response_at_all_dsd_and_output_rates(tmp_path, settings, rate, output):
    s = replace(settings, origin_cache_dir=str(tmp_path), dsd_pcm_rate=output)
    profile = calibrate_response(rate, s, "actual backend test")
    assert profile["status"] == "Measured"
    assert profile["output_header"]["sample_rate_hz"] == output
    assert [c["frequency_hz"] for c in profile["controls"]] == CONTROL_FREQUENCIES
    assert profile["controls"][0]["output_amplitude"] == pytest.approx(0.1, abs=0.015)
    assert boundary_chain_valid(profile, 24000)
    if output == 176400:
        assert not boundary_chain_valid(profile, 96000)
    assert controlled_bandwidth(profile) < output / 2
    assert calibrate_response(rate, s, "actual backend test") == profile
    assert response_key(rate, s, "changed version") != profile["key"]
    json.dumps(profile, allow_nan=False)


def test_actual_dsd512_origin_end_to_end(tmp_path, settings):
    p = tmp_path / "generated512.dsf"
    generate_controls(p, 22579200)
    before = p.read_bytes()
    result, context = analyze(
        p, replace(settings, dsd_mode="full", origin_cache_dir=str(tmp_path / "cache"))
    )
    report = result.findings["origin_investigation"]
    assert context is None and result.scope["complete_file"]
    assert (
        result.findings["dsd_evidence"]
        .measurements["experimental_origin_detection"]
        .startswith("Executed: Measured")
    )
    assert result.findings["dsd_conversion"].measurements["response_profile_status"] == "Measured"
    assert report.status == "Measured", report.summary
    r = report.measurements
    assert len(r["hypotheses"]) == 6
    assert len(r["native"]["windows"]) == 3
    assert r["scope"]["temporal"]["measured_cells"] >= 3
    assert r["historical_source"] == "Unknown"
    assert p.read_bytes() == before
    json.dumps(result.to_dict(), allow_nan=False)


def test_actual_dsd_boundary_from_filter_without_low_rate_pcm_history(tmp_path, settings):
    x = np.random.default_rng(790).normal(0, 0.1, round(352800 * 2.2))
    x = lfilter(firwin(1025, 22050, fs=352800, window=("kaiser", 8.6)), [1], x)
    p = write_pdm(tmp_path / "filtered.dsf", x, 352800, native_rate=11289600)
    result, _ = analyze(p, replace(settings, dsd_mode="full"))
    r = result.findings["origin_investigation"].measurements
    boundary = next(b for b in r["boundaries"] if b["candidate_hz"] == 22050)
    assert boundary["historical_compatibility_evidence"]
    assert boundary["channels"][0]["attenuation_db"] > 30
    assert boundary["temporal"]["detected_cells"] >= 2
    assert len(boundary["temporal"]["native_detected_window_ids"]) == 3
    h = next(h for h in r["hypotheses"] if h["code"] == "pcm-bandwidth-44100")
    assert h["status"] == "Compatible but not distinguishable"
    assert r["historical_source"] == "Unknown"  # The control never had a 44.1k PCM stage.


def test_actual_dff_and_dsf_tone_origin_pipeline_agree(tmp_path, settings):
    rate = 2822400
    x = 0.2 * np.sin(2 * np.pi * 24000 * np.arange(round(rate * 0.3)) / rate)
    a = dsf(tmp_path / "tone.dsf", rate=rate, samples=np.column_stack((x, x / 2)))
    info = native_info(a)
    bits = np.concatenate(list(native_blocks(info, inspect_dsd(info), 0, 1)))
    guard = round(0.04 * rate)
    phase = np.exp(-2j * np.pi * 24000 * np.arange(guard, len(bits)) / rate)
    actual_amplitudes = abs(np.sum(bits[guard:] * phase[:, None], axis=0))
    actual_ratio = 20 * np.log10(actual_amplitudes[0] / actual_amplitudes[1])
    packed = np.packbits(((bits + 1) / 2).astype(np.uint8), axis=0, bitorder="big").tobytes()
    b = dff(tmp_path / "tone.dff", rate=rate, seconds=0.3)
    dff_info = native_info(b, container="dff")
    raw = bytearray(b.read_bytes())
    offset = inspect_dsd(dff_info).audio_data_offset
    assert len(raw) - offset == len(packed)
    raw[offset:] = packed
    b.write_bytes(raw)
    reports = []
    for path in [a, b]:
        result, _ = analyze(path, replace(settings, dsd_mode="full"))
        assert result.findings["dsd_integrity"].status == "Passed"
        report = result.findings["origin_investigation"]
        assert report.status == "Measured" and report.measurements["native"]["status"] == "Measured"
        reports.append(result.findings["dsd_audible"].measurements["spectrum"])
    for spectrum in reports:
        f = np.array(spectrum["frequencies_hz"])
        p = np.array(spectrum["density_fs2_per_hz"])
        assert f[np.argmax(p[:, 0])] == pytest.approx(24000, abs=30)
        assert 10 * np.log10(np.max(p[:, 0]) / np.max(p[:, 1])) == pytest.approx(
            actual_ratio, abs=0.1
        )


def test_independent_fir_conversion_control_agrees_in_passband(tmp_path, settings):
    path = tmp_path / "independent.dsf"
    tones = [1000, 24000, 48000, 96000]
    generate_controls(path, 11289600, tones)
    info = probe(path, settings)
    bits = np.concatenate(list(native_blocks(info, inspect_dsd(info), 0, 1)))
    independent = resample_poly(bits, 1, 32, window=("kaiser", 8.6), axis=0)[:, 0]
    parts = []
    attempt = convert_window(
        info, replace(settings, dsd_pcm_rate=352800), 0, None, lambda x: parts.append(x.copy())
    )
    assert attempt.status == "Passed"
    ffmpeg = np.concatenate(parts)[:, 0]
    ratios = []
    for i, frequency in enumerate(tones):
        first, last = round((i * 0.12 + 0.04) * 352800), round((i + 1) * 0.12 * 352800)
        phase = np.exp(-2j * np.pi * frequency * np.arange(first, last) / 352800)
        aa = abs(np.sum(independent[first:last] * phase))
        bb = abs(np.sum(ffmpeg[first:last] * phase))
        ratios.append(20 * np.log10(bb / aa))
    assert np.max(np.abs(np.array(ratios) - ratios[0])) < 0.1


def test_failed_conversion_calibration_prevents_historical_attribution(
    tmp_path, settings, monkeypatch
):
    from music_project.core.models import Finding

    path = dsf(tmp_path / "chain.dsf", seconds=1.2, rate=2822400)
    info = native_info(path)
    f = np.arange(0, 160001, 50.0)
    p = np.where(f < 24000, 1e-9, 1e-13)
    boundaries = boundary_features(f, np.column_stack((p, p)))
    cells = [{"boundaries": boundaries, "noise": {"status": "Unknown"}} for _ in range(3)]
    finding = Finding(
        "Measured",
        "generated",
        {
            "spectrum": {
                "status": "Measured",
                "frequencies_hz": f.tolist(),
                "density_fs2_per_hz": np.column_stack((p, p)).tolist(),
            }
        },
    )
    r = investigate_origin(
        info,
        {"dsd_audible": finding},
        {},
        {"cells": cells},
        settings,
        {},
        measured_profile={"status": "Unsupported", "reason": "control failed"},
    )
    assert not any(b["historical_compatibility_evidence"] for b in r.boundaries)
    assert r.noise["status"] == "Unsupported"


def test_pcm_bandwidth_hypotheses_are_compatibility_not_identity(settings, info):
    f = np.arange(0, 160001, 50.0)
    p = np.where(f < 24000, 1e-9, 1e-13)
    boundaries = boundary_features(f, p)
    cells = [{"boundaries": boundaries, "noise": {"status": "Unknown"}} for _ in range(3)]
    scope = {
        "origin_pcm_spectrum": {
            "status": "Measured",
            "frequencies_hz": f.tolist(),
            "density_fs2_per_hz": p.tolist(),
        }
    }
    r = investigate_origin(info, {}, scope, {"cells": cells}, settings, {})
    h = next(h for h in r.hypotheses if h.code == "pcm-bandwidth-48000")
    assert h.status == "Compatible but not distinguishable"
    assert h.supporting_evidence and h.alternatives and h.assumptions
    assert r.historical_source == "Unknown"


def test_reference_actual_alignment_gain_polarity_and_identity(tmp_path, write_wav, settings):
    rng = np.random.default_rng(51)
    x = rng.normal(0, 0.05, 48000 * 2)
    a = write_wav(tmp_path / "a.wav", x, bits=24)
    y = np.r_[np.zeros(480), -0.5 * x[:-480]]
    b = write_wav(tmp_path / "b.wav", y, bits=24)
    r = investigate_reference(
        a, b, settings, verify_identity=True, chronology_note="Unverified fixture note"
    )
    m = r["alignment"]["measurements"]
    assert r["status"] == "Measured"
    assert m["offset_b_samples"] == 480 and m["polarity"] == "inverted"
    assert m["gain_b_over_a_db"] == pytest.approx(-6.0206, abs=0.001)
    assert abs(m["correlation"]) > 0.999
    assert not r["byte_identity_verified"]
    assert r["conversion_direction"] == "Unknown" and not r["reference_authenticated"]
    same = investigate_reference(a, a, settings, verify_identity=True)
    assert same["decoded_audio_identity"] == "Verified" and same["byte_identity_verified"]
    assert same["same_mastering"] == "Unknown"
    json.dumps(r, allow_nan=False)


def test_reference_periodic_alignment_remains_ambiguous(tone, tmp_path, write_wav, settings):
    t = np.arange(48000 * 3) / 48000
    b = write_wav(tmp_path / "shift.wav", 0.1 * np.sin(2 * np.pi * 1000 * (t + 0.0002)))
    r = investigate_reference(tone, b, settings)
    assert r["status"] == "Ambiguous" and r["same_recording"] == "Inconclusive"
