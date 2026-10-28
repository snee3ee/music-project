from dataclasses import asdict

import numpy as np
import pytest
from scipy import signal

from music_project.core.pcm import peaks, quantization, spectral_findings


def observations(finding):
    return {o.code: o for o in finding.observations}


def test_broadband_has_measured_negative_flags_without_origin_claim(make_context):
    x = np.random.default_rng(202).normal(0, 0.1, 96000 * 2)
    loss, up = spectral_findings(make_context(x))
    assert observations(loss)["CUTOFF"].status == "Not detected"
    flags = observations(up)
    assert flags["NYQUIST_BOUNDARY"].status == "Not detected"
    assert flags["PSD_22300_23700"].status == flags["PSD_ABOVE_24K"].status == "Above threshold"
    assert flags["PSD_22300_23700"].value == up.measurements["band_22300_23700_db"]
    assert up.measurements["source_rate"] == "Unknown"
    assert loss.status == up.status == "Ambiguous"


@pytest.mark.parametrize("source_rate", [44100, 48000])
def test_sharp_boundary_and_ultrasonic_attenuation(make_context, source_rate):
    x = np.random.default_rng(203).normal(0, 0.1, source_rate * 2)
    context = make_context(signal.resample(x, 96000 * 2))
    _loss, up = spectral_findings(context)
    flags = observations(up)
    assert flags["NYQUIST_BOUNDARY"].status == "Detected"
    assert flags["PSD_ABOVE_24K"].status == "Below threshold"
    if source_rate == 44100:
        assert flags["PSD_22300_23700"].status == "Below threshold"
    else:
        assert flags["PSD_22300_23700"].status == "Above threshold"
    assert up.measurements["source_rate"] == "Unknown"


@pytest.mark.parametrize("kind", ["silence", "short", "tone"])
def test_insufficient_data_is_not_negative_detection(make_context, kind):
    t = np.arange(96000 * 2) / 96000
    x = 0.1 * np.sin(2 * np.pi * 1000 * t)
    if kind == "silence":
        x *= 0
    elif kind == "short":
        x = x[:100]
    loss, up = spectral_findings(make_context(x))
    assert observations(loss)["CUTOFF"].status == "Insufficient data"
    assert observations(up)["NYQUIST_BOUNDARY"].status == "Insufficient data"


@pytest.mark.parametrize("rate", [16000, 44100, 48000])
def test_upsampling_applicability_has_specific_reason(make_context, rate):
    x = np.random.default_rng(204).normal(0, 0.1, rate * 2)
    _loss, up = spectral_findings(make_context(x, rate=rate))
    flag = observations(up)["NYQUIST_BOUNDARY"]
    assert flag.status == "Not applicable"
    assert f"{rate / 1000:g}" in flag.summary


def test_partial_nyquist_band_is_not_used(make_context):
    x = np.random.default_rng(205).normal(0, 0.1, 50000 * 2)
    _loss, up = spectral_findings(make_context(x, rate=50000))
    assert all(m["boundary_hz"] != 24000 for m in up.measurements["boundaries"])
    assert observations(up)["PSD_ABOVE_24K"].status == "Insufficient data"
    assert "24 kHz" not in observations(up)["NYQUIST_BOUNDARY"].summary


def test_low_rate_cutoff_is_not_applicable_instead_of_unknown(make_context):
    x = np.random.default_rng(207).normal(0, 0.1, 16000 * 2)
    loss, _up = spectral_findings(make_context(x, rate=16000))
    assert loss.status == "Not applicable"
    assert observations(loss)["CUTOFF"].status == "Not applicable"


def test_reported_cutoff_range_matches_actual_candidates(make_context):
    x = np.random.default_rng(208).normal(0, 0.1, 44100 * 2)
    loss, _up = spectral_findings(make_context(x, rate=44100))
    assert loss.measurements["checked_boundaries_hz"][-1] == 20000
    assert "14–20 kHz" in observations(loss)["CUTOFF"].summary


@pytest.mark.parametrize("kind", ["DSD", "Lossy/other"])
def test_inapplicable_signal_is_not_negative_detection(make_context, kind):
    x = np.ones(10000) * 0.1
    loss, up = spectral_findings(make_context(x, kind=kind))
    assert observations(loss)["CUTOFF"].status == "Not applicable"
    assert observations(up)["NYQUIST_BOUNDARY"].status == "Not applicable"


def test_padding_flag_and_serialization(make_context):
    rng = np.random.default_rng(206)
    x = rng.integers(-30000, 30000, 5000) / 32768
    finding = quantization(make_context(x))
    assert observations(finding)["PADDING_GRID"].status == "Detected"
    assert asdict(finding)["observations"][0]["value"] == 100
    processed = quantization(make_context(x * 0.7131))
    assert observations(processed)["PADDING_GRID"].status == "Not detected"


def test_full_scale_samples_are_not_clipping_verdict(make_context):
    measured = peaks(make_context([0.1, 0.2, -1.0, 0.3]))
    assert observations(measured)["FULL_SCALE_SAMPLES"].status == "Detected"
    assert observations(measured)["FULL_SCALE_SAMPLES"].value == 1
    assert any("не доказывают clipping" in text for text in measured.limitations)
    assert (
        observations(peaks(make_context([0.1, 0.2])))["FULL_SCALE_SAMPLES"].status == "Not detected"
    )
