"""Independent 48 kHz BS.1770 calculation and actual backend scope controls."""

from dataclasses import replace

import numpy as np
import pytest
from scipy.signal import lfilter

from music_project.core.probe import probe
from music_project.core.technical_analysis import measure_technical


def independent_meter_48k(samples, weights):
    """Test-only BS.1770-5 tables1/2, equations2/4/5/6; EBU3342 section3.

    Does not call product meter code, FFmpeg, loudnorm or libebur128. Only complete
    windows are admitted. Published coefficients apply here only at 48 kHz.
    """
    stage1 = lfilter(
        [1.53512485958697, -2.69169618940638, 1.19839281085285],
        [1, -1.69065929318241, 0.73248077421585],
        samples,
        axis=0,
    )
    weighted = lfilter([1, -2, 1], [1, -1.99004745483398, 0.99007225036621], stage1, axis=0)
    energy = np.sum(weighted**2 * np.asarray(weights), axis=1)
    cumulative = np.r_[0, np.cumsum(energy)]

    def windows(seconds):
        width = round(seconds * 48000)
        ends = np.arange(width, len(energy) + 1, 4800)
        values = (cumulative[ends] - cumulative[ends - width]) / width
        return values[values > 0]

    def gate(power, relative):
        power = power[-0.691 + 10 * np.log10(power) >= -70]
        if not len(power):
            return power
        threshold = max(-70, -0.691 + 10 * np.log10(np.mean(power)) + relative)
        return power[-0.691 + 10 * np.log10(power) >= threshold]

    blocks = gate(windows(0.4), -10)
    short_term = gate(windows(3), -20)
    integrated = -0.691 + 10 * np.log10(np.mean(blocks)) if len(blocks) else None
    lra = (
        np.diff(np.percentile(-0.691 + 10 * np.log10(short_term), [10, 95]))[0]
        if len(short_term)
        else None
    )
    return integrated, lra


def test_prefix_meter_never_includes_samples_after_requested_interval(
    tmp_path, write_wav, settings
):
    rate, end = 48000, 2.05
    t = np.arange(round(rate * end)) / rate
    prefix = 0.02 * np.sin(2 * np.pi * 997 * t)
    following = 0.9 * np.sin(2 * np.pi * 997 * np.arange(rate) / rate)
    source = write_wav(tmp_path / "followed-by-loud.wav", np.r_[prefix, following], bits=24)
    reference = write_wav(tmp_path / "only-prefix.wav", prefix, bits=24)
    measured = measure_technical(
        probe(source, settings), replace(settings, technical_mode="prefix", analysis_seconds=end)
    )
    m = measured["loudness"].measurements
    expected = measure_technical(probe(reference, settings), settings)["loudness"].measurements
    assert m["scope"]["end_seconds"] == end
    assert m["timeline"][-1]["end_seconds"] <= end + 1 / rate
    assert m["metadata_frames"] == expected["metadata_frames"]
    assert m["integrated_lufs"] == expected["integrated_lufs"]
    assert m["maximum_momentary"] == expected["maximum_momentary"]
    assert measured["pcm_integrity"].status == "Partial"


@pytest.mark.parametrize("kind", ["broadband", "gated", "anti-phase", "surround-lfe"])
def test_independent_k_weighting_gates_lra_and_channel_weights(
    tmp_path, write_wav, encode, settings, kind
):
    rng = np.random.default_rng(17705)
    channels = 6 if kind == "surround-lfe" else 2
    levels = [-40, -23, -30, -20] if kind == "gated" else [-28, -23, -18, -23]
    x = np.concatenate(
        [rng.normal(size=(48000 * 8, channels)) * 10 ** (level / 20) for level in levels]
    )
    if kind == "anti-phase":
        x[:, 1] = -x[:, 0]
    weights = [1, 1, 1, 0, 1.41, 1.41] if channels == 6 else [1, 1]
    if channels == 6:
        x[:, 3] = 0.8 * np.sin(2 * np.pi * 100 * np.arange(len(x)) / 48000)
    # Reference uses the exact quantized samples supplied to the independent decoder.
    x = np.rint(x * 2**23) / 2**23
    path = write_wav(tmp_path / "reference-control.wav", x, bits=24)
    if channels == 6:
        path = encode(path, tmp_path / "layout.wav", "-channel_layout", "5.1", "-c:a", "pcm_s24le")
    integrated, lra = independent_meter_48k(x, weights)
    result = measure_technical(probe(path, settings), settings)
    m, p = result["loudness"].measurements, result["full_peaks"].measurements
    assert m["integrated_lufs"] == pytest.approx(integrated, abs=0.15)
    assert m["lra_lu"] == pytest.approx(lra, abs=0.25)
    assert p["sample_peak_dbfs"] == pytest.approx(20 * np.log10(np.max(abs(x))), abs=1e-10)
    rms = np.sqrt(np.mean(x**2))
    assert p["rms_dbfs"] == pytest.approx(20 * np.log10(rms), abs=1e-10)
    assert p["crest_factor_db"] == pytest.approx(20 * np.log10(np.max(abs(x)) / rms), abs=1e-10)
