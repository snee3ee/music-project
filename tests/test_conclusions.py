import json
from dataclasses import asdict, replace

import numpy as np
import pytest
from scipy.signal import resample_poly

from music_project.core.analysis import analyze
from music_project.core.conclusion_models import MeasurementScope, ReferenceProfile
from music_project.core.conclusions import build_conclusions
from music_project.core.models import Finding
from music_project.core.pcm import loudness
from music_project.core.peak_measurements import PeakMeasurements
from music_project.core.probe import probe
from music_project.core.technical_analysis import measure_technical


def tone_samples(rate, seconds=1, frequency=1000, amplitude=0.25, phase=0):
    return amplitude * np.sin(
        2 * np.pi * frequency * np.arange(round(rate * seconds)) / rate + phase
    )


def tapered(x, rate):
    n = round(0.01 * rate)
    x = x.copy()
    x[:n] *= np.linspace(0, 1, n)
    x[-n:] *= np.linspace(1, 0, n)
    return x


@pytest.mark.parametrize("rate", [44100, 48000, 88200, 96000, 176400, 192000])
@pytest.mark.parametrize(
    "divisor,phase,amplitude,expected",
    [
        (4, 0, 0.5, -6.0206),
        (4, 45, 0.5, -6.0206),
        (6, 60, 0.5, -6.0206),
        (8, 67.5, 0.5, -6.0206),
        (4, 45, 1.41, 2.9844),
    ],
)
def test_reconstructed_peaks_selected_ebu3341_15_to_19_controls(
    rate, divisor, phase, amplitude, expected
):
    x = tapered(
        tone_samples(rate, frequency=rate / divisor, amplitude=amplitude, phase=np.deg2rad(phase)),
        rate,
    )
    meter = PeakMeasurements(rate, 2, None)
    xx = np.column_stack((x, x / 2))
    for first in range(0, len(xx), 7919):
        meter.consume(xx[first : first + 7919])
    result = meter.finish()
    tp = result["true_peak"]
    assert expected - 0.4 <= tp["true_peak_dbtp"] <= expected + 0.2
    assert tp["true_peak_per_channel_dbtp"][0] - tp["true_peak_per_channel_dbtp"][
        1
    ] == pytest.approx(6.0206, abs=0.001)
    # Independent high-resolution reconstruction; same finite record and zero extension.
    independent = resample_poly(x, 32, 1, window=("kaiser", 12.0))
    measured = 20 * np.log10(np.max(abs(independent)))
    assert tp["true_peak_dbtp"] == pytest.approx(measured, abs=0.4)
    assert tp["output_rate_hz"] >= 192000
    assert 0 <= tp["time_seconds_per_channel"][0] <= 1


def test_peak_observations_runs_cross_blocks_exact_rails_and_natural_plateaus():
    x = np.zeros((100, 2))
    rail = 32767 / 32768
    x[11:15, 0] = rail
    x[20:22, 0] = -1
    x[25, 0] = -rail
    x[30:40, 1] = 0.95  # A deliberately rectangular waveform, not proof of clipping.
    a = PeakMeasurements(48000, 2, 16, -1)
    for start, end in [(0, 12), (12, 14), (14, 33), (33, 100)]:
        a.consume(x[start:end])
    r = a.finish()
    assert r["full_scale_samples_per_channel"] == [6, 0]
    assert r["rail_runs"][0]["count"] == 2
    assert r["rail_runs"][0]["longest"]["frames"] == 4
    assert r["possible_flat_top_runs"][1]["count"] == 1
    assert r["sample_peak_time_seconds"][0] == 20 / 48000
    assert r["near_ceiling_samples_per_channel"] == [7, 10]
    assert r["rms_dbfs"] == pytest.approx(20 * np.log10(np.sqrt(np.mean(x * x))))
    assert r["crest_factor_db"] == pytest.approx(-r["rms_dbfs"])
    b = PeakMeasurements(48000, 2, 16, -1)
    b.consume(x)
    rr = b.finish()
    for key in [
        "rail_runs",
        "possible_flat_top_runs",
        "full_scale_samples_per_channel",
        "true_peak",
    ]:
        assert r[key] == rr[key]


@pytest.mark.parametrize("level", [-23, -33])
def test_actual_ebu3341_stereo_anchor(tmp_path, write_wav, settings, level):
    x = tone_samples(48000, 20, amplitude=10 ** (level / 20))
    p = write_wav(tmp_path / "ebu-anchor.wav", np.column_stack((x, x)), bits=24)
    r = measure_technical(probe(p, settings), settings)
    meter = r["loudness"].measurements
    assert meter["integrated_lufs"] == pytest.approx(level, abs=0.1)
    assert meter["maximum_momentary"]["lufs"] == pytest.approx(level, abs=0.1)
    assert meter["maximum_short_term"]["lufs"] == pytest.approx(level, abs=0.1)
    legacy = loudness(probe(p, settings), settings).measurements
    assert meter["integrated_lufs"] == pytest.approx(legacy["integrated_lufs"], abs=0.1)
    assert meter["true_peak_dbtp"] == pytest.approx(legacy["true_peak_dbtp"], abs=0.2)


@pytest.mark.parametrize("duration", [0.05, 0.3, 2, 4])
def test_actual_silence_and_short_programs(tmp_path, write_wav, settings, duration):
    p = write_wav(tmp_path / "silence.wav", np.zeros(round(48000 * duration)))
    r = measure_technical(probe(p, settings), settings)
    m = r["loudness"].measurements
    assert m["integrated_lufs"] is None
    assert m["lra_lu"] is None
    assert m["true_peak_state"] == "negative infinity"
    assert r["full_peaks"].measurements["exact_zero_seconds"] == pytest.approx(duration)
    assert r["pcm_integrity"].status == "Passed"
    json.dumps({k: asdict(v) for k, v in r.items()}, allow_nan=False)


@pytest.mark.parametrize(
    "levels,expected",
    [([-20, -30], 10), ([-20, -15], 5), ([-40, -20], 20), ([-50, -35, -20, -35, -50], 15)],
)
def test_actual_ebu3342_synthetic_lra_cases(tmp_path, write_wav, settings, levels, expected):
    x = np.concatenate([tone_samples(48000, 20, amplitude=10 ** (level / 20)) for level in levels])
    p = write_wav(tmp_path / "lra.wav", np.column_stack((x, x)), bits=24)
    m = measure_technical(probe(p, settings), settings)["loudness"].measurements
    assert m["lra_lu"] == pytest.approx(expected, abs=1)
    assert m["gating"]["lra_relative_lu"] == -20
    assert m["maximum_short_term"]["lufs"] > m["minimum_short_term"]["lufs"]


def test_actual_relative_and_absolute_gating(tmp_path, write_wav, settings):
    x = np.concatenate(
        [
            tone_samples(48000, s, amplitude=10 ** (level / 20))
            for s, level in [(10, -72), (10, -36), (60, -23), (10, -36), (10, -72)]
        ]
    )
    p = write_wav(tmp_path / "gated.wav", np.column_stack((x, x)), bits=24)
    m = measure_technical(probe(p, settings), settings)["loudness"].measurements
    assert m["integrated_lufs"] == pytest.approx(-23, abs=0.1)
    assert m["gating"]["integrated_relative_lu"] == -10
    assert m["gating"]["absolute_lufs"] == -70


@pytest.mark.parametrize(
    "segments,kind", [([(1.34, -20), (1.66, -30)] * 5, "S"), ([(0.18, -20), (0.22, -30)] * 25, "M")]
)
def test_actual_ebu3341_changing_window_controls(tmp_path, write_wav, settings, segments, kind):
    x = np.concatenate(
        [tone_samples(48000, seconds, amplitude=10 ** (level / 20)) for seconds, level in segments]
    )
    p = write_wav(tmp_path / "windows.wav", np.column_stack((x, x)), bits=24)
    m = measure_technical(probe(p, settings), settings)["loudness"].measurements
    key = "maximum_short_term" if kind == "S" else "maximum_momentary"
    assert m[key]["lufs"] == pytest.approx(-23, abs=0.1)


def test_actual_multichannel_51_and_lfe_exclusion(tmp_path, write_wav, encode, settings):
    amplitudes = [-28, -28, -24, None, -30, -30]
    channels = [
        np.zeros(48000 * 20)
        if level is None
        else tone_samples(48000, 20, amplitude=10 ** (level / 20))
        for level in amplitudes
    ]
    x = np.column_stack(channels)
    source = write_wav(tmp_path / "six-source.wav", x, bits=24)
    p = encode(source, tmp_path / "six.wav", "-channel_layout", "5.1", "-c:a", "pcm_s24le")
    m = measure_technical(probe(p, settings), settings)
    assert m["loudness"].measurements["integrated_lufs"] == pytest.approx(-23, abs=0.1)
    assert len(m["full_peaks"].measurements["sample_peak_per_channel_dbfs"]) == 6
    x[:, 3] = tone_samples(48000, 20, frequency=100, amplitude=0.5)
    source = write_wav(tmp_path / "lfe-source.wav", x, bits=24)
    p = encode(source, tmp_path / "lfe.wav", "-channel_layout", "5.1", "-c:a", "pcm_s24le")
    ll = measure_technical(probe(p, settings), settings)["loudness"].measurements
    assert ll["integrated_lufs"] == pytest.approx(
        m["loudness"].measurements["integrated_lufs"], abs=0.01
    )


def test_envelopes_and_event_storage_are_bounded():
    meter = PeakMeasurements(48000, 1, 16)
    x = np.tile(np.r_[np.ones(4) * 0.99, np.zeros(4)], 6000)[:, None]
    for _ in range(210):
        meter.consume(x)
    m = meter.finish()
    assert len(m["timeline"]) <= 2048
    assert m["timeline"][-1]["end_seconds"] == 210
    assert sum(r["frames"] for r in m["timeline"]) == 48000 * 210
    assert len(m["possible_flat_top_runs"][0]["events"]) <= 128
    assert m["possible_flat_top_runs"][0]["count"] == 6000 * 210


def test_conclusion_measurement_references_resolve_against_actual_result(tone, settings):
    result, _ = analyze(tone, settings)
    root = {key: value.measurements for key, value in result.findings.items()} | {
        "analysis": {"scope": result.scope}
    }
    for conclusion in result.conclusions:
        for identifier in conclusion.measurement_ids:
            node = root
            for segment in identifier.split("."):
                node = node[int(segment)] if isinstance(node, list) else node[segment]


def test_stderr_callback_failure_and_bounded_tail():
    import sys

    from music_project.core.models import AudioError
    from music_project.core.subprocess_utils import run

    received = []
    result = run(
        [sys.executable, "-c", "import sys;sys.stderr.write('x'*100000);print('done')"],
        consume_stderr=lambda b: received.append(len(b)),
    )
    assert sum(received) == 100000 and len(result.stderr) <= 65536

    def fail(chunk):
        raise ValueError("bad measurement")

    with pytest.raises(AudioError, match="bad measurement"):
        run([sys.executable, "-c", "import sys;sys.stderr.write('invalid')"], consume_stderr=fail)


@pytest.mark.parametrize("bits", [16, 24])
def test_actual_flac_md5_valid_mismatch_and_missing(tmp_path, write_wav, encode, settings, bits):
    x = np.random.default_rng(17).uniform(-0.3, 0.3, (48000, 2))
    source = write_wav(tmp_path / "original.wav", x, bits=bits)
    p = encode(source, tmp_path / "generated.flac", "-c:a", "flac")
    info = probe(p, settings)
    findings = measure_technical(info, settings)
    assert findings["pcm_integrity"].measurements["flac_md5"]["status"] == "Verified"
    original = p.read_bytes()
    frame_mismatch = bytearray(original)
    value = int.from_bytes(frame_mismatch[18:26], "big")
    frame_mismatch[18:26] = (value + 1).to_bytes(8, "big")
    p.write_bytes(frame_mismatch)
    wrong_count = measure_technical(probe(p, settings), settings)["pcm_integrity"].measurements[
        "flac_md5"
    ]
    assert wrong_count["md5_status"] == "Verified" and wrong_count["frame_count_status"] == "Failed"
    assert wrong_count["status"] == "Failed"
    changed = bytearray(original)
    changed[26] ^= 1
    p.write_bytes(changed)
    failed = measure_technical(probe(p, settings), settings)
    assert failed["pcm_integrity"].measurements["flac_md5"]["status"] == "Failed"
    assert failed["pcm_integrity"].status == "Failed"
    changed[26:42] = b"\0" * 16
    p.write_bytes(changed)
    missing = measure_technical(probe(p, settings), settings)
    assert missing["pcm_integrity"].measurements["flac_md5"]["status"] == "Unknown"
    partial = measure_technical(
        info, replace(settings, technical_mode="prefix", analysis_seconds=0.2)
    )
    assert not partial["pcm_integrity"].measurements["complete_file"]


def test_reference_math_and_scope_mismatch_from_reported_observations(info):
    whole = MeasurementScope(0, 317.76, 317.76, 317.76, True, 15252480, 48000, 2).to_dict()
    prefix = MeasurementScope(0, 30, 30, 317.76, False, 1440000, 48000, 2).to_dict()
    # Supplied observations, not an independently accessed Sad Girl recording.
    f = {
        "loudness": Finding(
            "Measured",
            "reported",
            {"scope": whole, "integrated_lufs": -9.75, "true_peak_dbtp": -0.82, "lra_lu": 8.60},
        ),
        "full_peaks": Finding(
            "Measured",
            "reported",
            {
                "scope": prefix,
                "sample_peak_dbfs": -1.1,
                "rms_dbfs": -15.81,
                "crest_factor_db": 14.71,
            },
        ),
    }
    before = json.dumps({k: asdict(v) for k, v in f.items()})
    c = build_conclusions(info, {}, f, ReferenceProfile("custom", -14, -1))
    gain = next(c for c in c if c.conclusion_id == "reference.gain-plan")
    assert gain.measured_values["difference_lu"] == 4.25
    assert gain.measured_values["target_gain_db"] == -4.25
    assert gain.measured_values["predicted_true_peak_dbtp"] == pytest.approx(-5.07)
    assert any(c.conclusion_id == "peaks.scope-mismatch" for c in c)
    assert next(c for c in c if c.conclusion_id == "dynamics.plr").measured_values[
        "plr_db"
    ] == pytest.approx(8.93)
    assert json.dumps({k: asdict(v) for k, v in f.items()}) == before
    assert build_conclusions(info, {}, f, ReferenceProfile("custom", -14, -1)) == c
    assert not any(c.category == "reference" for c in build_conclusions(info, {}, f))
    with pytest.raises(ValueError):
        build_conclusions(info, {}, f, ReferenceProfile("bad", np.nan))
    f["loudness"].measurements["true_peak_scope"] = prefix
    mismatched = build_conclusions(info, {}, f, ReferenceProfile("custom", -14, -1))
    assert not any(c.conclusion_id == "dynamics.plr" for c in mismatched)
    gain = next(c for c in mismatched if c.conclusion_id == "reference.gain-plan")
    assert "predicted_true_peak_dbtp" not in gain.measured_values


def test_actual_32bit_pcm_stream_preserves_low_bits(tmp_path, settings, monkeypatch):
    import hashlib
    import wave

    from music_project.core.flac_integrity import FlacMD5

    integers = np.random.default_rng(42).integers(-(2**31), 2**31, size=(48000, 2), dtype=np.int32)
    raw = integers.astype("<i4").tobytes()
    p = tmp_path / "native32.wav"
    with wave.open(str(p), "wb") as stream:
        stream.setnchannels(2)
        stream.setsampwidth(4)
        stream.setframerate(48000)
        stream.writeframes(raw)
    expected = hashlib.md5(raw, usedforsecurity=False).hexdigest()
    recovered = hashlib.md5(usedforsecurity=False)
    original = PeakMeasurements.consume

    def inspect(self, x):
        recovered.update(np.rint(x * 2**31).astype("<i4").tobytes())
        original(self, x)

    monkeypatch.setattr(PeakMeasurements, "consume", inspect)
    info = probe(p, settings)
    assert info.bit_depth == 32
    measure_technical(info, settings)
    assert recovered.hexdigest() == expected
    # A header alone must never verify PCM. Actual 8/32-bit native FLAC decoding
    # and embedded MD5 are exercised by independent verbatim fixtures in test_v1_flac.
    packed = (48000 << 44) | (1 << 41) | (31 << 36) | 48000
    header = (
        b"fLaC"
        + bytes([128, 0, 0, 34])
        + bytes(10)
        + packed.to_bytes(8, "big")
        + bytes.fromhex(expected)
    )
    stub = tmp_path / "unsupported32.flac"
    stub.write_bytes(header)
    check = FlacMD5(replace(info, path=str(stub), codec="flac", container="flac"))
    assert check.result(False)["status"] == "Partial"


def test_reference_gain_constraint_and_invalid_values(info):
    scope = MeasurementScope(0, 4, 4, 4, True, 192000, 48000, 1).to_dict()
    findings = {
        "loudness": Finding(
            "Measured", "", {"integrated_lufs": -25, "true_peak_dbtp": -1, "scope": scope}
        ),
        "full_peaks": Finding("Measured", "", {"scope": scope, "sample_peak_dbfs": -2}),
    }
    c = build_conclusions(info, {}, findings, ReferenceProfile("custom", -14, -1))
    plan = next(c for c in c if c.conclusion_id == "reference.gain-plan").measured_values
    assert not plan["gain_only_target_achievable"] and plan["ceiling_constrained_gain_db"] == 0
    findings["loudness"].measurements["integrated_lufs"] = float("nan")
    assert not any(
        c.conclusion_id == "reference.gain-plan"
        for c in build_conclusions(info, {}, findings, ReferenceProfile("custom", -14))
    )


def test_actual_positive_intersample_and_machine_generated_conclusions(
    tmp_path, write_wav, settings
):
    x = tapered(tone_samples(48000, 4, frequency=12000, amplitude=1.1, phase=np.pi / 4), 48000)
    p = write_wav(tmp_path / "intersample.wav", np.column_stack((x, x)), bits=24)
    r, _ = analyze(p, settings)
    conclusions = {c.conclusion_id: c for c in r.conclusions}
    assert r.findings["full_peaks"].measurements["sample_peak_dbfs"] < 0
    assert r.findings["loudness"].measurements["true_peak_dbtp"] > 0
    assert conclusions["peaks.rails"].measured_values["count"] == 0
    assert (
        conclusions["peaks.intersample-difference"].measured_values["above_zero_intersample_db"] > 0
    )
    assert conclusions["peaks.true-peak"].measured_values["margin_to_zero_db"] < 0
    assert all(
        c.measurement_ids and c.rule_version and c.validation_status and c.analysis_scope
        for c in r.conclusions
    )
    assert not any(
        c.statement_type == "Verified fact" and c.category == "clipping" for c in r.conclusions
    )
    json.dumps(r.to_dict(), allow_nan=False)


def test_unvalidated_true_peak_rate_does_not_imply_headroom(tmp_path, write_wav, settings):
    p = write_wav(tmp_path / "rate32000.wav", tone_samples(32000, 4), rate=32000)
    r, _ = analyze(p, settings)
    c = build_conclusions(r.info, r.scope, r.findings, ReferenceProfile("custom", -14, -1))
    assert any(
        v.conclusion_id == "peaks.true-peak-unavailable" and v.statement_type == "Not validated"
        for v in c
    )
    assert not any(v.conclusion_id == "peaks.true-peak" for v in c)
    plan = next(v for v in c if v.conclusion_id == "reference.gain-plan")
    assert "predicted_true_peak_dbtp" not in plan.measured_values
