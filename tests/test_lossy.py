"""Measurement correctness and abstention, not artificial provenance ground truth."""

import json
from dataclasses import asdict, replace

import numpy as np
import pytest
from scipy import signal

from music_project.core.analysis import analyze
from music_project.core.lossy import LossyCollector, investigate_context
from music_project.core.lossy_spectrum import band_measurements


def noise(rate, seconds=8, seed=91):
    return np.random.default_rng(seed).normal(0, 0.03, (round(rate * seconds), 2))


def collect(info, values, *, chunk=7919):
    info = replace(
        info,
        sample_rate=44100 if info.sample_rate == 0 else info.sample_rate,
        duration=len(values) / info.sample_rate,
        channels=values.shape[1],
    )
    collector = LossyCollector(info)
    for i in range(0, len(values), chunk):
        collector.consume(values[i : i + chunk])
    return collector.finish(complete_decode=True)


@pytest.mark.parametrize("rate", [32000, 44100, 48000, 88200, 96000, 176400, 192000])
def test_full_band_lossless_measurement_independent_of_high_res(info, rate):
    x = noise(rate)
    result = collect(replace(info, sample_rate=rate), x).measurements
    assert result["performed"]
    assert result["counts"]["eligible_windows"] == 4
    assert result["classification"] == "No evaluated indicators detected"
    assert result["historical_codec"] == "Unknown"
    assert result["bands"][-1]["high_hz"] == rate / 2
    assert result["scope"]["analyzed_seconds"] == 8
    assert result["scope"]["complete_file"]
    assert result["parameters"]["frequency_step_hz"] == rate / 8192
    assert all(r["status"] == "Unsupported" for r in result["additional_indicators"])
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("cutoff", [15555, 18750, 20550])
def test_noninteger_boundary_is_measured_but_lossless_filter_is_not_lossy_proof(info, cutoff):
    rate = 44100
    x = noise(rate)
    # A legitimate FIR filter, not a fixture shaped around the runtime rule.
    filtered = signal.lfilter(signal.firwin(1025, cutoff, fs=rate), [1], x, axis=0)
    report = collect(replace(info, sample_rate=rate), filtered).measurements
    found = [b for b in report["candidates"] if any(c["detected"] for c in b["channels"])]
    assert found
    assert min(abs(b["candidate_hz"] - cutoff) for b in found) < 650
    assert report["classification"] == "Inconclusive"
    assert any(s["recurrent"] for b in found for s in b["stability"])
    assert report["historical_codec"] == "Unknown"


@pytest.mark.parametrize("case", ["silence", "near-silence", "tone", "short"])
def test_ineligible_support_is_explicit(info, case):
    rate = 48000
    x = noise(rate, seconds=4)
    if case == "silence":
        x *= 0
    if case == "near-silence":
        x *= 1e-5
    if case == "tone":
        x[:] = (0.1 * np.sin(2 * np.pi * 997 * np.arange(len(x)) / rate))[:, None]
    if case == "short":
        x = x[: rate // 10]
    report = collect(replace(info, sample_rate=rate), x).measurements
    assert report["counts"]["eligible_windows"] == 0
    assert report["classification"] in {"Inconclusive", "Not evaluated"}
    assert report["counts"]["discarded_windows"] > 0
    if case != "short":
        assert report["counts"]["discard_reasons"]


def test_stereo_disagreement_time_sampling_and_repeated_chunks(info):
    rate = 44100
    x = noise(rate, 10)
    x[:, 0] = signal.lfilter(signal.firwin(1025, 16000, fs=rate), [1], x[:, 0])
    a = collect(replace(info, sample_rate=rate), x)
    b = collect(replace(info, sample_rate=rate), x, chunk=50003)
    aa, bb = a.measurements, b.measurements
    # FFT accumulation is identical: external chunk boundaries do not alter windows.
    assert aa == collect(replace(info, sample_rate=rate), x).measurements
    assert aa["candidates"] == bb["candidates"] and aa["spectrum"] == bb["spectrum"]
    for arow, brow in zip(aa["windows"], bb["windows"], strict=True):
        for ach, bch in zip(arow["channels"], brow["channels"], strict=True):
            assert ach["rms_dbfs"] == pytest.approx(bch["rms_dbfs"], abs=1e-12)
    found = [v for v in aa["candidates"] if v["channels"][0]["detected"]]
    assert found and not any(v["channels"][1]["detected"] for v in found)
    assert aa["scope"]["ranges"][-1]["end_seconds"] == 10


def test_uniform_plan_memory_is_bounded_and_reaches_late_regions(info):
    rate = 44100
    c = LossyCollector(replace(info, sample_rate=rate, duration=3600))
    assert len(c.plan) == 32
    assert c.plan[0][0] == 0 and c.plan[-1][1] == rate * 3600
    assert c.total.nbytes == 4097 * 8 * info.channels
    assert all(a[1] <= b[0] for a, b in zip(c.plan, c.plan[1:], strict=False))


def test_band_energy_and_floor_proxy_match_independent_psd_integration():
    f = np.arange(0, 24001, 10.0)
    p = np.column_stack((np.ones(len(f)) * 1e-9, np.ones(len(f)) * 1e-10))
    bands = band_measurements(f, p)
    for ch, level in [(1, 1e-9), (2, 1e-10)]:
        own = [b for b in bands if b["channel"] == ch]
        assert sum(b["power_fs2"] for b in own) == pytest.approx(p[:, ch - 1].sum() * 10)
        assert sum(b["fraction_of_measured_power"] for b in own) == pytest.approx(1)
        assert all(b["median_density_fs2_per_hz"] == pytest.approx(level) for b in own)


def test_existing_pcm_context_fallback_and_dsd_not_evaluated(make_context):
    context = make_context(noise(48000, 4), rate=48000)
    assert investigate_context(context).measurements["scope"]["fallback_reason"]
    context.info = replace(context.info, kind="DSD")
    assert investigate_context(context).measurements["classification"] == "Not evaluated"


def test_actual_flac_integrity_and_lossy_are_independent(tmp_path, write_wav, encode, settings):
    x = noise(44100, 4)
    path = encode(
        write_wav(tmp_path / "original.wav", x, rate=44100),
        tmp_path / "original.flac",
        "-c:a",
        "flac",
    )
    result, _ = analyze(path, settings)
    assert result.findings["pcm_integrity"].measurements["flac_md5"]["status"] == "Verified"
    report = result.findings["lossy_source"].measurements
    assert report["performed"] and report["historical_codec"] == "Unknown"
    assert any(c.conclusion_id == "origin.lossy-investigation" for c in result.conclusions)
    before = asdict(result.findings["lossy_source"])
    from music_project.core.conclusions import build_conclusions

    result.findings["loudness"].measurements.update(integrated_lufs=-6.98, true_peak_dbtp=0.74)
    build_conclusions(result.info, result.scope, result.findings)
    assert asdict(result.findings["lossy_source"]) == before


def test_boundary_in_later_windows_is_not_lost_in_full_band_average(info):
    rate = 44100
    x = noise(rate, 8)
    x[4 * rate :] = signal.lfilter(signal.firwin(1025, 16000, fs=rate), [1], x[4 * rate :], axis=0)
    r = collect(replace(info, sample_rate=rate), x).measurements
    assert r["classification"] == "Inconclusive"
    assert any(s["detected_windows"] >= 2 for b in r["candidates"] for s in b["stability"])
    assert not any(c["detected"] for b in r["candidates"] for c in b["channels"])


@pytest.mark.parametrize("codec", ["mp3", "aac"])
@pytest.mark.parametrize("rate", [44100, 48000])
def test_actual_known_lossy_to_flac_chain_retains_integrity_and_abstains(
    tmp_path, settings, codec, rate
):
    from tools.lossy_dataset import encoder_capabilities, lossy_chain, original, write_pcm

    if not encoder_capabilities(settings)[codec]:
        pytest.skip(f"Actual {codec} encoder unavailable")
    source = write_pcm(tmp_path / "reference.wav", original(rate, seconds=4), rate)
    final = lossy_chain(settings, source, tmp_path, "transcoded", codec, 128)
    r, _ = analyze(final, settings)
    assert r.findings["pcm_integrity"].measurements["flac_md5"]["status"] == "Verified"
    m = r.findings["lossy_source"].measurements
    assert m["performed"] and m["bands"] and m["windows"]
    assert m["classification"] in {"Inconclusive", "No evaluated indicators detected"}
    assert m["historical_codec"] == "Unknown"


def test_fallback_preserves_original_duration_and_reports_partial_scope(make_context):
    c = make_context(noise(48000, 4), rate=48000, duration=140)
    m = investigate_context(c).measurements
    assert m["scope"]["total_seconds"] == 140
    assert m["scope"]["analyzed_seconds"] == 4
    assert not m["scope"]["complete_file"]
