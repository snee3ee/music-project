import numpy as np
import pytest
from scipy import signal

from music_project.core.pcm import peaks, quantization, spectral_findings, spectrogram


def test_direct_padding(make_context):
    rng = np.random.default_rng(42)
    x = rng.integers(-30000, 30000, size=100000) / 32768
    result = quantization(make_context(x))
    assert result.status == "Direct 16→24 padding evidence"
    assert result.measurements["zero_lower_byte_percent"] == 100
    assert result.measurements["lower_byte_entropy_bits"] == 0


@pytest.mark.parametrize("processing", ["native_like", "dither", "gain", "filter"])
def test_processing_does_not_establish_native_bitdepth(make_context, processing):
    rng = np.random.default_rng(93)
    x = rng.integers(-30000, 30000, size=150000) / 32768
    if processing == "native_like":
        x = rng.integers(-8_000_000, 8_000_000, size=150000) / 2**23
    elif processing == "dither":
        x = x + (rng.random(len(x)) - rng.random(len(x))) / 32768
    elif processing == "gain":
        x = x * 0.7131
    else:
        x = signal.sosfilt(signal.butter(4, 0.6, output="sos"), x)
    result = quantization(make_context(x))
    assert result.status == "No direct-padding evidence"
    assert result.measurements["distinct_lower_bytes"] > 1
    assert result.measurements["lower_byte_entropy_bits"] > 1
    assert "native 24-bit" in " ".join(result.limitations)


@pytest.mark.parametrize("x", [np.zeros(3000), np.ones(500) / 2])
def test_quantization_ambiguous(make_context, x):
    assert quantization(make_context(x)).status == "Ambiguous"


@pytest.mark.parametrize("kind,bits", [("DSD", 24), ("PCM", 16), ("Lossy/other", None)])
def test_quantization_routing(make_context, kind, bits):
    assert (
        quantization(make_context(np.ones(5000), kind=kind, bit_depth=bits)).status
        == "Not applicable"
    )


def test_peaks_and_silence(make_context):
    measured = peaks(make_context(np.array([0.5, -0.5])))
    assert measured.measurements["sample_peak_dbfs"] == pytest.approx(-6.0206, abs=0.001)
    assert measured.measurements["crest_factor_db"] == 0
    silent = peaks(make_context(np.zeros(1000)))
    assert silent.measurements["rms_dbfs"] is None
    assert silent.measurements["full_scale_samples_per_channel"] == [0]


@pytest.mark.parametrize("boundary", [22050, 24000])
@pytest.mark.parametrize("pipeline", ["sharp_fft", "broad_polyphase"])
def test_upsampled_broadband_boundary(make_context, boundary, pipeline):
    rng = np.random.default_rng(100)
    source_rate = 2 * boundary
    original = rng.normal(0, 0.1, source_rate * 3)
    divisor = np.gcd(source_rate, 96000)
    upsampled = (
        signal.resample(original, 96000 * 3)
        if pipeline == "sharp_fft"
        else signal.resample_poly(original, 96000 // divisor, source_rate // divisor)
    )
    _loss, up = spectral_findings(make_context(upsampled))
    assert up.status == ("Medium suspicion" if pipeline == "sharp_fft" else "Ambiguous")
    assert up.measurements["source_rate"] == "Unknown"


def test_native_like_spectrum_and_phase_inversion(make_context):
    x = np.random.default_rng(1).normal(0, 0.1, 96000 * 2)
    mono = spectral_findings(make_context(x))
    stereo = spectral_findings(make_context(np.column_stack([x, -x])))
    assert mono[0].status == mono[1].status == "Ambiguous"
    assert stereo[1].measurements["band_22300_23700_db"] == pytest.approx(
        mono[1].measurements["band_22300_23700_db"]
    )


@pytest.mark.parametrize("control", ["silence", "tone", "short", "lowpass"])
def test_spectral_negative_and_ambiguous_controls(make_context, control):
    t = np.arange(96000 * 2) / 96000
    x = np.sin(2 * np.pi * 1000 * t) * 0.1
    if control == "silence":
        x *= 0
    elif control == "short":
        x = x[:100]
    elif control == "lowpass":
        x = signal.sosfilt(
            signal.butter(8, 4000, fs=96000, output="sos"),
            np.random.default_rng(2).normal(0, 0.1, len(t)),
        )
    loss, up = spectral_findings(make_context(x))
    assert loss.status == "Ambiguous"
    assert up.status == "Ambiguous"


def test_spectral_applicability(make_context):
    x = np.random.default_rng(1).normal(0, 0.1, 96000)
    assert spectral_findings(make_context(x, rate=48000))[1].status == "Not applicable"
    assert spectral_findings(make_context(x, kind="DSD"))[0].status == "Not applicable"


def test_spectrogram_axis_and_frequency(make_context):
    t = np.arange(48000) / 48000
    x = np.sin(2 * np.pi * 6000 * t) * 0.1
    f, times, p = spectrogram(make_context(np.column_stack([x, -x]), rate=48000))
    assert p.shape == (len(f), len(times))
    assert f[np.argmax(p.mean(axis=1))] == pytest.approx(6000, abs=24)
