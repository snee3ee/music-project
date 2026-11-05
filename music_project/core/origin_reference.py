"""Opt-in reference investigation, scoped to explicit transformed PCM excerpts."""

from dataclasses import asdict, replace
from pathlib import Path

import numpy as np
from scipy.signal import welch

from music_project.core.compare import compare_pcm
from music_project.core.config import Settings
from music_project.core.decoder import PCMContext, canonical_hash, input_args
from music_project.core.dsd_decoder import RESAMPLE, FloatWaveStream
from music_project.core.files import file_hash, signature
from music_project.core.models import AudioError, AudioInfo
from music_project.core.origin_models import ORIGIN_VERSION
from music_project.core.probe import probe
from music_project.core.subprocess_utils import run


def reference_prefix(info: AudioInfo, settings: Settings, seconds=8.0, rate=48000):
    if info.channels not in (1, 2) or info.channel_layout not in {"mono", "stereo"}:
        raise AudioError("Reference comparison requires known mono/stereo order")
    duration = min(seconds, settings.max_pcm_bytes / (rate * info.channels * 8 * 4))
    parts = []
    frames = 0

    def consume(samples):
        nonlocal frames
        frames += len(samples)
        if frames > round(duration * rate) + 2:
            raise AudioError("Reference output exceeds fixed prefix budget")
        parts.append(samples.astype(np.float64))

    parser = FloatWaveStream(rate, info.channels, consume)
    command = input_args(info, settings)
    command[command.index("error")] = "level+warning"
    command += [
        "-t",
        str(duration),
        "-af",
        RESAMPLE.format(rate=rate),
        "-ar",
        str(rate),
        "-ac",
        str(info.channels),
        "-channel_layout",
        info.channel_layout,
        "-c:a",
        "pcm_f32le",
        "-f",
        "wav",
        "pipe:1",
    ]
    result = run(command, timeout=settings.timeout, consume=parser.feed)
    parser.finish()
    samples = np.concatenate(parts)
    converted = replace(
        info, sample_rate=rate, kind="PCM", codec="pcm_f32le", bit_depth=None, lossless=False
    )
    return PCMContext(converted, samples, duration), {
        "command": command,
        "header": parser.header,
        "warnings": result.stderr.splitlines(),
        "requested_seconds": duration,
        "decoded_seconds": len(samples) / rate,
        "domain": "explicit resampled float32 PCM, not original decoded-audio identity",
    }


def investigate_reference(
    source: Path | str,
    reference: Path | str,
    settings: Settings = Settings(),
    *,
    verify_identity=False,
    chronology_note="",
) -> dict:
    first, second = Path(source).resolve(strict=True), Path(reference).resolve(strict=True)
    before_a, before_b = signature(first), signature(second)
    a, b = probe(first, settings), probe(second, settings)
    result = {
        "method_version": ORIGIN_VERSION,
        "source": a.path,
        "reference": b.path,
        "reference_authenticated": False,
        "chronology_note": chronology_note,
        "chronology_status": "User-supplied statement, not independently verified"
        if chronology_note
        else "Unknown",
        "same_recording": "Inconclusive",
        "same_mastering": "Unknown",
        "different_mastering": "Not established",
        "decoded_audio_identity": "Not verified",
        "conversion_direction": "Unknown",
    }
    if a.channels != b.channels or a.channel_layout != b.channel_layout:
        result.update(status="Not applicable", reason="Different channel count/order")
        return result
    x, params_a = reference_prefix(a, settings)
    y, params_b = (x, params_a) if first == second else reference_prefix(b, settings)
    comparison = compare_pcm(x, y)
    result.update(
        status=comparison.status,
        alignment=asdict(comparison),
        conversion_a=params_a,
        conversion_b=params_b,
        duration_a=a.duration,
        duration_b=b.duration,
        duration_difference_seconds=a.duration - b.duration
        if a.duration is not None and b.duration is not None
        else None,
    )
    measurements = comparison.measurements
    if comparison.status == "Measured" and abs(measurements.get("correlation", 0)) >= 0.995:
        result["same_recording"] = (
            "Compatible recording content within aligned excerpts; not whole-recording identity"
        )
    if comparison.status == "Measured":
        lag = measurements["offset_b_samples"]
        size = measurements["overlap_frames"]
        gain = 10 ** (measurements["gain_b_over_a_db"] / 20) * (
            -1 if measurements["polarity"] == "inverted" else 1
        )
        xx = x.samples[max(0, -lag) : max(0, -lag) + size]
        yy = y.samples[max(0, lag) : max(0, lag) + size] / gain
        n = min(8192, size)
        f, pa = welch(xx, 48000, nperseg=n, noverlap=n // 2, axis=0, scaling="density")
        _, pb = welch(yy, 48000, nperseg=n, noverlap=n // 2, axis=0, scaling="density")
        result["spectral_comparison"] = {
            "frequencies_hz": f.tolist(),
            "source_density_fs2_per_hz": pa.tolist(),
            "reference_density_after_gain_fs2_per_hz": pb.tolist(),
            "normalization": "Welch density, Hann, mean power per channel; reference gain compensated",
            "scope": "aligned overlap only",
            "nfft": n,
        }
    if verify_identity:
        result["byte_hash_source"] = file_hash(first)
        result["byte_hash_reference"] = (
            result["byte_hash_source"] if first == second else file_hash(second)
        )
        result["byte_identity_verified"] = (
            result["byte_hash_source"] == result["byte_hash_reference"]
        )
        try:
            ha = canonical_hash(a, settings)
            hb = ha if first == second else canonical_hash(b, settings)
            result["canonical_source_sha256"], result["canonical_reference_sha256"] = ha, hb
            result["decoded_audio_identity"] = (
                "Verified" if ha == hb else "Different under canonical PCM representation"
            )
        except AudioError as exc:
            result["decoded_audio_identity"] = "Unsupported"
            result["identity_limitation"] = str(exc)
    if before_a != signature(first) or before_b != signature(second):
        raise AudioError("File changed during reference investigation")
    result["limitations"] = [
        "Strong correlation does not authenticate the reference or establish conversion direction.",
        "Comparison uses bounded prefixes after explicit resampling; periodic signals and processing can make alignment ambiguous.",
        "Identical or different sampled mastering characteristics are not a verified mastering history.",
    ]
    return result
