import numpy as np
import pytest
from scipy import signal

from music_project.core.compare import compare_pcm


@pytest.mark.parametrize("case", ["identity", "gain", "polarity", "offset", "eq", "clipped"])
def test_comparison(make_context, case):
    x = np.random.default_rng(55).normal(0, 0.1, 96000)
    y = x.copy()
    if case == "gain":
        y *= 0.5
    elif case == "polarity":
        y *= -1
    elif case == "offset":
        y = np.concatenate([np.zeros(701), x])
    elif case == "eq":
        y = signal.sosfilt(signal.butter(2, 10000, fs=96000, output="sos"), x)
    elif case == "clipped":
        y = np.clip(x, -0.12, 0.12)
    result = compare_pcm(make_context(x), make_context(y))
    metrics = result.measurements
    if case == "identity":
        assert metrics["identical_prefix"]
        assert metrics["residual_max_abs_after_gain"] == 0
    elif case == "gain":
        assert metrics["gain_b_over_a_db"] == pytest.approx(-6.0206, abs=0.001)
    elif case == "polarity":
        assert metrics["polarity"] == "inverted"
        assert metrics["residual_max_abs_after_gain"] == 0
    elif case == "offset":
        assert metrics["offset_b_samples"] == 701
        assert metrics["identical_overlap"] and not metrics["identical_prefix"]
    else:
        assert not metrics["identical_overlap"]


def test_comparison_inapplicable_and_silent(make_context):
    x = np.ones(1000) * 0.1
    assert compare_pcm(make_context(x), make_context(x, rate=48000)).status == "Not applicable"
    assert compare_pcm(make_context(np.zeros(1000)), make_context(x)).status == "Ambiguous"


def test_unrelated_audio_has_no_null_claim(make_context):
    rng = np.random.default_rng(8)
    result = compare_pcm(
        make_context(rng.normal(0, 0.1, 96000)), make_context(rng.normal(0, 0.1, 96000))
    )
    assert result.status == "Ambiguous"
    assert result.measurements["residual_rms_dbfs_after_gain"] is None
