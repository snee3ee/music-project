"""Known properties and counterexamples, never source-history authentication."""

import numpy as np
import pytest
from scipy import signal

from music_project.core.pcm import quantization, spectral_findings


@pytest.mark.parametrize("decoy", ["unexcited", "upper-too-loud"])
def test_eligible_boundary_is_not_hidden_by_a_larger_ineligible_drop(
    make_context, monkeypatch, decoy
):
    f = np.arange(0, 48001, 10.0)
    p = np.where(f < 20000, 1e-12, 1e-18)
    # A separate low-energy notch has a larger local ratio, but fails the lower-side
    # excitation criterion. It must not hide the evaluable 20 kHz boundary.
    p[(f >= 12800) & (f <= 13700)] = 1e-16 if decoy == "unexcited" else 1e-7
    p[(f >= 14300) & (f <= 15200)] = 1e-28 if decoy == "unexcited" else 1e-15
    monkeypatch.setattr("music_project.core.pcm.spectrum", lambda c: (f, p))
    context = make_context(np.ones(96000 * 2))
    cutoff, _ = spectral_findings(context)
    assert cutoff.observations[0].status == "Detected"
    assert cutoff.measurements["candidate"]["boundary_hz"] == 20000
    assert cutoff.status == "Medium suspicion"  # Experimental compatibility only.


def test_periodic_off_grid_samples_are_not_hidden_by_entropy_sampling(make_context):
    # More than the budget forces stride2. Every odd sample is off-grid; a stride
    # that starts at0 sees only 16-bit-compatible samples. Exact grid checking must
    # cover the decoded prefix, even when entropy/unique-count evidence is sampled.
    values = np.tile([256, 257], 500_001)
    result = quantization(make_context(values / 2**23))
    assert result.status == "No direct-padding evidence"
    assert result.measurements["zero_lower_byte_percent"] == 50


@pytest.mark.parametrize("seed", [7, 101, 1770])
@pytest.mark.parametrize(
    "case",
    ["full-band", "lossless-filter", "sharp-upsample", "upsample-plus-noise", "broad-upsample"],
)
def test_ground_truth_bandwidth_discrimination_and_counterexamples(make_context, seed, case):
    rng = np.random.default_rng(seed)
    x = rng.normal(0, 0.05, 96000 * 2)
    if case == "lossless-filter":
        # Never encoded using a lossy codec, yet it has the tested cutoff feature.
        transformed = np.fft.rfft(x)
        transformed[np.fft.rfftfreq(len(x), 1 / 96000) > 16000] = 0
        x = np.fft.irfft(transformed, n=len(x))
    elif "upsample" in case:
        original = rng.normal(0, 0.05, 48000 * 2)
        x = (
            signal.resample_poly(original, 2, 1)
            if case == "broad-upsample"
            else signal.resample(original, len(x))
        )
        if case == "upsample-plus-noise":
            x += rng.normal(0, 0.005, len(x))
    cutoff, upsample = spectral_findings(make_context(np.column_stack((x, -x))))
    if case == "lossless-filter":
        assert cutoff.observations[0].status == "Detected"
        assert cutoff.status == "Medium suspicion"
        assert "Experimental" in cutoff.measurements["validation_status"]
    elif case == "sharp-upsample":
        assert upsample.observations[0].status == "Detected"
    else:
        assert cutoff.status == upsample.status == "Ambiguous"
    assert upsample.measurements["source_rate"] == "Unknown"


@pytest.mark.parametrize("seed", [7, 101, 1770])
def test_high_entropy_dithered_16_bit_origin_is_not_native_24_proof(make_context, seed):
    rng = np.random.default_rng(seed)
    source = rng.integers(-30000, 30000, 20000) * 256
    with_dither = source + rng.integers(-255, 256, len(source))
    result = quantization(make_context(with_dither / 2**23))
    assert result.status == "No direct-padding evidence"
    assert result.measurements["lower_byte_entropy_bits"] > 7.9
    assert any("не доказывает native 24-bit" in line for line in result.limitations)
