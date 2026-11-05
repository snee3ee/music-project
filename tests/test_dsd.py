import json
import os
import struct
from dataclasses import replace

import numpy as np
import pytest
from dsd_fixtures import dff, dsf
from scipy.signal import welch

from music_project.core.analysis import analyze
from music_project.core.dsd import diagnose_dsd
from music_project.core.dsd_container import inspect_dsd
from music_project.core.dsd_decoder import convert_window, quick_windows
from music_project.core.dsd_spectrum import StreamingWelch
from music_project.core.models import AudioError, AudioInfo
from music_project.core.probe import probe
from music_project.core.subprocess_utils import CommandResult


def container_info(path, rate=11289600, codec="dsd_lsbf_planar", channels=2):
    return AudioInfo(
        str(path),
        "dsf",
        codec,
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


@pytest.mark.parametrize("rate", [2822400, 5644800, 11289600])
@pytest.mark.parametrize("output_rate", [176400, 352800])
def test_actual_dsf_decode(tmp_path, settings, rate, output_rate):
    path = dsf(tmp_path / "синтетический.dsf", rate=rate)
    original = path.read_bytes()
    info = probe(path, settings)
    assert info.sample_rate == rate and info.bit_depth is None
    findings, scope = diagnose_dsd(
        info, replace(settings, dsd_mode="full", dsd_pcm_rate=output_rate)
    )
    assert findings["dsd_container"].status == "Passed"
    assert findings["dsd_integrity"].status == "Passed", findings["dsd_integrity"].measurements
    assert findings["dsd"].measurements["nominal_native_bitrate_bps"] == rate * 2
    if rate == 11289600:
        assert findings["dsd"].measurements["dsd_family"] == "DSD256"
        assert rate * 2 / 1000 == 22579.2
    assert findings["dsd"].measurements["dst_processing"] == "Not applicable"
    assert scope["complete_file"]
    assert findings["dsd_evidence"].status == "Ambiguous"
    header = findings["dsd_integrity"].measurements["attempts"][0]["output_header"]
    assert header["sample_rate_hz"] == output_rate and header["channels"] == 2
    assert findings["dsd_audible"].status == "Measured"
    assert path.read_bytes() == original
    json.dumps({k: v.measurements for k, v in findings.items()}, allow_nan=False)


def test_actual_dff_decode(tmp_path, settings):
    path = dff(tmp_path / "synthetic.dff")
    findings, scope = diagnose_dsd(probe(path, settings), replace(settings, dsd_mode="full"))
    assert findings["dsd_container"].status == findings["dsd_integrity"].status == "Passed"
    assert scope["complete_file"]


def test_actual_mono_decode(tmp_path, settings):
    path = dsf(tmp_path / "mono.dsf", channels=1)
    findings, scope = diagnose_dsd(probe(path, settings), replace(settings, dsd_mode="full"))
    assert findings["dsd_integrity"].status == "Passed"
    assert scope["complete_file"]


def test_actual_backend_rejects_invalid_input(tmp_path, settings):
    path = tmp_path / "broken.dsf"
    path.write_bytes(b"not a DSD audio stream")
    attempt = convert_window(container_info(path), settings, 0, None, lambda x: None)
    assert attempt.status == "Failed" and attempt.fatal_error


def test_warning_retained_on_fatal_decoder_error(tmp_path, settings, monkeypatch):
    from music_project.core.models import DecoderError

    path = dsf(tmp_path / "generated.dsf")

    def fail(*args, **kwargs):
        raise DecoderError(
            "fatal decoder failure", "[warning] decoder warning\n[error] fatal failure"
        )

    monkeypatch.setattr("music_project.core.dsd_decoder.run", fail)
    result = convert_window(container_info(path), settings, 0, None, lambda x: None)
    assert result.status == "Failed"
    assert result.warnings == ["[warning] decoder warning"]


@pytest.mark.parametrize("bits", [1, 8])
def test_actual_known_pulse_density_tone(tmp_path, settings, bits):
    rate = 2822400
    t = np.arange(int(rate * 0.25)) / rate
    x = 0.2 * np.sin(2 * np.pi * 2000 * t)
    path = dsf(
        tmp_path / "tone.dsf", rate=rate, samples=np.column_stack((x, x / 2)), bit_order=bits
    )
    findings, _ = diagnose_dsd(probe(path, settings), replace(settings, dsd_mode="full"))
    spectrum = findings["dsd_audible"].measurements["spectrum"]
    p = np.array(spectrum["density_fs2_per_hz"])
    f = np.array(spectrum["frequencies_hz"])
    assert f[np.argmax(p[:, 0])] == pytest.approx(2000, abs=spectrum["frequency_step_hz"])
    band = next(b for b in spectrum["bands"] if b["low_hz"] == 2000)
    assert band["left_minus_right_db"] == pytest.approx(6.0206, abs=0.15)


@pytest.mark.parametrize(
    "change,status",
    [
        ("truncate", "Failed"),
        ("samples", "Failed"),
        ("size", "Failed"),
        ("pointer", "Failed"),
        ("channels", "Failed"),
        ("version", "Unsupported"),
        ("bits", "Unsupported"),
        ("block", "Unsupported"),
    ],
)
def test_dsf_invalid_structures(tmp_path, change, status):
    path = dsf(tmp_path / "bad.dsf")
    data = bytearray(path.read_bytes())
    if change == "truncate":
        data = data[:-10]
    else:
        offset, fmt, value = {
            "samples": (64, "<Q", 0),
            "size": (12, "<Q", 999),
            "pointer": (20, "<Q", 90),
            "channels": (52, "<I", 0),
            "version": (40, "<I", 2),
            "bits": (60, "<I", 9),
            "block": (72, "<I", 0),
        }[change]
        struct.pack_into(fmt, data, offset, value)
    path.write_bytes(data)
    result = inspect_dsd(container_info(path))
    assert result.status == status


def test_truncated_dff_and_dst(tmp_path):
    path = dff(tmp_path / "bad.dff")
    info = container_info(path, 2822400, "dsd_msbf")
    data = path.read_bytes()
    path.write_bytes(data[:-1])
    assert inspect_dsd(info).status == "Failed"
    path = dff(path, compression=b"DST ")
    info = container_info(path, 0, "dst")
    findings, scope = diagnose_dsd(info)
    assert findings["dsd_container"].measurements["compression"] == "DST"
    assert findings["dsd_integrity"].status == "Unsupported"
    assert findings["dsd"].measurements["dst_processing"] == "Unsupported"
    assert not scope["complete_file"]


def test_quick_windows_and_actual_seek(tmp_path, settings):
    assert quick_windows(235.88) == [(0, 5), (115.44, 5), (230.88, 5)]
    assert quick_windows(12) == [(0, 12)]
    path = dsf(tmp_path / "long.dsf", rate=2822400, seconds=20)
    findings, scope = diagnose_dsd(probe(path, settings), settings)
    assert findings["dsd_integrity"].status == "Partial", findings["dsd_integrity"].measurements
    assert not scope["complete_file"]
    assert scope["decoded_seconds"] == pytest.approx(15, abs=1 / settings.dsd_pcm_rate)
    assert len(scope["ranges"]) == 3
    assert len(findings["dsd_integrity"].measurements["attempts"]) == 3


@pytest.mark.parametrize("duration", [None, 0, -1, float("inf"), float("nan")])
def test_unknown_quick_duration(duration):
    with pytest.raises(AudioError):
        quick_windows(duration)


def test_missing_decoder_and_no_provenance(tmp_path, settings):
    path = dsf(tmp_path / "generated.dsf")
    f, scope = diagnose_dsd(container_info(path), replace(settings, ffmpeg="absent-ffmpeg"))
    assert f["dsd_integrity"].status == "Unsupported"
    assert f["dsd_evidence"].status == "Unknown"
    assert not scope["complete_file"]
    assert f["dsd_container"].status == "Passed"


def wave_bytes(rate=352800, channels=2, frames=20000):
    data = np.zeros((frames, channels), dtype="<f4").tobytes()
    fmt = struct.pack("<HHIIHH", 3, channels, rate, rate * channels * 4, channels * 4, 32)
    return (
        b"RIFF"
        + struct.pack("<I", 36 + len(data))
        + b"WAVEfmt "
        + struct.pack("<I", 16)
        + fmt
        + b"data"
        + struct.pack("<I", len(data))
        + data
    )


@pytest.mark.parametrize("failure", ["rate", "channels", "fatal", "empty", "short", "nan"])
def test_controlled_conversion_failures(tmp_path, settings, monkeypatch, failure):
    path = dsf(tmp_path / "generated.dsf")

    def fake_run(command, **kwargs):
        if failure == "fatal":
            raise AudioError("Decoder failure")
        data = wave_bytes(
            rate=176400 if failure == "rate" else 352800, channels=1 if failure == "channels" else 2
        )
        if failure == "empty":
            data = b""
        if failure == "short":
            data = data[:-1]
        if failure == "nan":
            data = data[:44] + np.full(40000, np.nan, dtype="<f4").tobytes()
        for i in range(0, len(data), 19):
            kwargs["consume"](data[i : i + 19])
        return CommandResult(b"", "a non-fatal warning")

    monkeypatch.setattr("music_project.core.dsd_decoder.run", fake_run)
    attempt = convert_window(container_info(path), settings, 0, 1, lambda x: None)
    assert attempt.status == "Failed" and attempt.fatal_error


def test_output_header_chunked_and_warnings(tmp_path, settings, monkeypatch):
    path = dsf(tmp_path / "generated.dsf")
    data = wave_bytes()

    def fake_run(command, **kwargs):
        for i in range(0, len(data), 7):
            kwargs["consume"](data[i : i + 7])
        return CommandResult(b"", "warning only")

    monkeypatch.setattr("music_project.core.dsd_decoder.run", fake_run)
    attempt = convert_window(container_info(path), settings, 0, 1, lambda x: None)
    assert attempt.status == "Passed" and attempt.warnings == ["warning only"]
    assert attempt.frames == 20000


def test_premature_successful_eof_is_failure(tmp_path, settings, monkeypatch):
    path = dsf(tmp_path / "generated.dsf")

    def fake_run(command, **kwargs):
        kwargs["consume"](wave_bytes(frames=20000))
        return CommandResult(b"", "")

    monkeypatch.setattr("music_project.core.dsd_decoder.run", fake_run)
    f, scope = diagnose_dsd(container_info(path), replace(settings, dsd_mode="full"))
    assert f["dsd_integrity"].status == "Failed"
    assert not scope["complete_file"]


@pytest.mark.parametrize("amplitude", [0, 1, 1e-100])
def test_streaming_welch_matches_scipy(amplitude):
    x = np.random.default_rng(137).normal(0, 0.1, (120000, 2)) * amplitude
    estimator = StreamingWelch(176400, 2)
    for i in range(0, len(x), 137):
        estimator.consume(x[i : i + 137])
    estimator.end_window()
    result = estimator.result()
    f, expected = welch(
        x,
        176400,
        window="hann",
        nperseg=16384,
        noverlap=8192,
        detrend=False,
        scaling="density",
        axis=0,
    )
    np.testing.assert_allclose(result["density_fs2_per_hz"], expected, rtol=1e-12, atol=0)
    assert result["frequencies_hz"] == f.tolist()
    assert result["max_buffer_frames"] < 32768
    json.dumps(result, allow_nan=False)


def test_tone_power_stereo_and_band_availability():
    rate, n = 176400, 16384
    t = np.arange(n * 8) / rate
    x = 0.5 * np.sin(2 * np.pi * (128 * rate / n) * t)
    estimator = StreamingWelch(rate, 2)
    estimator.consume(np.column_stack((x, -x / 2)))
    result = estimator.result()
    psd = np.array(result["density_fs2_per_hz"])
    np.testing.assert_allclose(psd.sum(axis=0) * rate / n, [0.125, 0.03125], atol=1e-14)
    band = next(b for b in result["bands"] if b["low_hz"] == 200)
    assert band["power_fs2"][0] == pytest.approx(0.125)
    assert band["left_minus_right_db"] == pytest.approx(6.0206, abs=1e-4)
    assert result["bands"][-1]["status"] == "Unsupported"
    assert result["bands"][-1]["power_fs2"] is None


def test_disjoint_windows_do_not_join_fft():
    s = StreamingWelch(352800, 1)
    for _ in range(10):
        s.consume(np.zeros((9000, 1)))
        s.end_window()
    assert s.result()["status"] == "Unknown"


def test_analysis_integration(tmp_path, settings):
    path = dsf(tmp_path / "generated.dsf")
    result, context = analyze(path, settings)
    assert context is None
    assert "dsd_audible" in result.findings
    assert "quantization" not in result.findings
    json.dumps(result.to_dict(), allow_nan=False)


def test_real_dsd256_recording(settings):
    path = os.environ.get("MUSIC_PROJECT_DSD_FIXTURE")
    if not path:
        pytest.skip("No user-supplied real DSD recording; real DSD256 validation pending")
    result, context = analyze(path, replace(settings, dsd_mode="full", timeout=600))
    assert result.info.kind == "DSD" and result.info.sample_rate == 11289600
    assert context is None
    assert result.findings["dsd_integrity"].status == "Passed"
    assert result.scope["complete_file"]


def test_actual_seek_selects_signal_position(tmp_path, settings):
    rate = 2822400
    path = dsf(tmp_path / "changing.dsf", rate=rate, seconds=2)
    # Positive bit density in first half, negative in second; chunk writes stay bounded.
    with path.open("r+b") as output:
        for index in range((path.stat().st_size - 92) // 8192):
            output.seek(92 + index * 8192)
            output.write((b"\xff" if index * 32768 / rate < 1 else b"\x00") * 8192)
    info = probe(path, settings)
    means = []
    for start in (0.4, 1.4):
        totals = [0.0, 0]

        def consume(samples, totals=totals):
            totals[0] += float(samples.sum())
            totals[1] += samples.size

        attempt = convert_window(info, settings, start, 0.2, consume)
        assert attempt.status == "Passed"
        means.append(totals[0] / totals[1])
    assert means[0] > 0.5 and means[1] < -0.5


def test_cancel_dsd_and_bad_settings_preserve_metadata(tmp_path, settings):
    path = dsf(tmp_path / "generated.dsf")
    findings, scope = diagnose_dsd(container_info(path), settings, cancelled=lambda: True)
    assert findings["dsd_integrity"].status == "Partial"
    assert not scope["complete_file"]
    findings, _ = diagnose_dsd(container_info(path), replace(settings, dsd_pcm_rate=0))
    assert findings["dsd_conversion"].status == "Unsupported"


def test_known_output_length_detects_whole_frame_truncation():
    from music_project.core.dsd_decoder import FloatWaveStream

    parser = FloatWaveStream(352800, 2, lambda x: None)
    parser.feed(wave_bytes()[:-8])
    with pytest.raises(AudioError, match="truncated"):
        parser.finish()
