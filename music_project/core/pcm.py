"""Conservative PCM measurements; historical provenance remains uncertain."""

import json
import math
import re

import numpy as np
from scipy import signal

from music_project.core.config import Settings
from music_project.core.decoder import PCMContext, input_args
from music_project.core.models import AudioError, AudioInfo, Finding
from music_project.core.subprocess_utils import run

SPECTRAL_LIMITS = [
    "Один спектральный признак не определяет исторический кодек или частоту источника.",
    "Фильтрация, инструменты и ограниченная полоса записи дают сходные признаки.",
    "Шум, dither и DSP могут скрыть границу; анализируется только указанная область.",
]


def db(value: float) -> float | None:
    return float(20 * np.log10(value)) if value > 0 else None


def peaks(context: PCMContext) -> Finding:
    x = context.samples
    absolute = np.abs(x)
    peak = float(absolute.max())
    rms = float(np.sqrt(np.mean(x * x)))
    bits = context.info.bit_depth
    threshold = 1 - 2 ** (1 - bits) if bits and bits <= 32 else 1.0
    counts = np.sum(absolute >= threshold, axis=0)
    return Finding(
        "Measured",
        "Sample Peak и RMS измерены в указанной области.",
        {
            "sample_peak_dbfs": db(peak),
            "rms_dbfs": db(rms),
            "crest_factor_db": db(peak / rms) if rms else None,
            "full_scale_samples_per_channel": counts.tolist(),
            "samples_above_1": int(np.sum(absolute > 1)),
            "full_scale_threshold": threshold,
        },
        "Максимум |sample|; RMS всех каналов; crest=20log10(peak/RMS).",
        [
            "Sample Peak около 0 dBFS и отсчёты у full scale сами по себе не доказывают clipping.",
            "Null для dB означает тишину (−∞ dB); RMS не равен воспринимаемой громкости.",
        ],
    )


def loudness(info: AudioInfo, settings: Settings = Settings()) -> Finding:
    if info.kind == "DSD":
        return Finding("Not applicable", "Native DSD требует явно заданного PCM-преобразования.")
    command = input_args(info, settings)
    command[command.index("error")] = "info"
    result = run(
        command + ["-af", "loudnorm=print_format=json", "-f", "null", "-"], timeout=settings.timeout
    )
    matches = re.findall(r'\{\s*"input_i".*?\}', result.stderr, re.S)
    if not matches:
        raise AudioError("FFmpeg не вернул loudnorm input measurements")
    data = json.loads(matches[-1])

    def finite(key):
        value = float(data[key])
        return value if math.isfinite(value) else None

    tp = finite("input_tp")
    return Finding(
        "Measured",
        "Громкость и True Peak измерены по всему первому аудиопотоку.",
        {
            "integrated_lufs": finite("input_i"),
            "lra_lu": finite("input_lra"),
            "true_peak_dbtp": tp,
            "true_peak_above_0_dbtp": tp is not None and tp > 0,
            "scope": "whole first audio stream",
        },
        "FFmpeg loudnorm input_i/input_lra/input_tp; dynamic analysis, 192 kHz TP pipeline.",
        [
            "Измеряется вход loudnorm; нормализованный выход отбрасывается, файл не меняется.",
            "LUFS может быть неопределён для тишины/очень короткого сигнала; LRA коротких записей ограничен.",
            "True Peak — оценка реконструированного пика, отличная от Sample Peak.",
        ],
    )


def quantization(context: PCMContext) -> Finding:
    info = context.info
    limits = [
        "Dither, gain, фильтры и DSP могут стереть структуру прежнего квантования.",
        "Энтропия не доказывает native 24-bit; число уровней не исключает обработанный 16-bit источник.",
        "Совместимость с сеткой 16-bit не устанавливает историю файла.",
    ]
    if info.kind != "PCM" or info.bit_depth != 24 or not info.lossless:
        return Finding(
            "Not applicable", "Метод применим к lossless integer PCM 24-bit.", limitations=limits
        )
    # Float64 exactly represents all 24-bit integers. Decode preserves native scale.
    values = np.rint(context.samples.ravel() * (1 << 23)).astype(np.int64)
    active = values[values != 0]
    active = active[:: max(1, math.ceil(active.size / 1_000_000))]
    if active.size < 1000:
        return Finding(
            "Ambiguous",
            "Недостаточно активных отсчётов (нужно ≥1000).",
            {"active_samples": int(active.size)},
            limitations=limits,
        )
    low = active & 255
    counts = np.bincount(low, minlength=256)
    p = counts[counts > 0] / active.size
    entropy = float(-np.sum(p * np.log2(p)))
    zero = float(np.mean(low == 0) * 100)
    distinct = int(np.unique(active).size)
    padded = bool(np.all(low == 0))
    return Finding(
        "Direct 16→24 padding evidence" if padded else "No direct-padding evidence",
        "Все активные отсчёты выборки лежат на сетке 16-bit. История неизвестна."
        if padded
        else "В выборке есть ненулевые младшие 8 бит. История bit-depth неизвестна.",
        {
            "zero_lower_byte_percent": zero,
            "distinct_lower_bytes": int(np.count_nonzero(counts)),
            "distinct_sample_values": distinct,
            "lower_byte_entropy_bits": entropy,
            "normalized_entropy": entropy / 8,
            "active_samples": int(active.size),
            "compatible_with_65536_output_levels": distinct <= 65536,
            "sampling": "nonzero interleaved samples, deterministic stride, max 1,000,000",
        },
        "Signed 24-bit = round(f64*2^23); low byte = integer & 255; H=-Σp log2(p).",
        limits,
        ["ZERO_LOW_BYTE_GRID"] if padded else [],
    )


def spectrum(context: PCMContext) -> tuple[np.ndarray, np.ndarray]:
    x = context.samples
    n = min(8192, len(x))
    if n < 256:
        raise AudioError("Для спектра нужно не менее 256 кадров")
    frequencies, power = signal.welch(
        x,
        fs=context.info.sample_rate,
        window="hann",
        nperseg=n,
        noverlap=n // 2,
        axis=0,
        scaling="density",
    )
    # Mean channel power prevents cancellation of opposite-polarity stereo.
    return frequencies, np.mean(power, axis=1)


def spectral_findings(context: PCMContext) -> tuple[Finding, Finding]:
    info = context.info
    method = "Welch PSD: Hann 8192 (or available), overlap 50%, mean channel power; v1."
    if info.kind != "PCM" or not info.lossless:
        na = Finding("Not applicable", "Спектральные эвристики: только lossless PCM.")
        return na, na
    try:
        f, power = spectrum(context)
    except AudioError as exc:
        amb = Finding("Ambiguous", str(exc), limitations=SPECTRAL_LIMITS)
        return amb, amb
    ref_mask = (f >= 1000) & (f <= 8000)
    reference = float(np.mean(power[ref_mask])) if np.any(ref_mask) else 0
    if reference <= 1e-16 or len(context.samples) < info.sample_rate:
        amb = Finding(
            "Ambiguous",
            "Тишина, короткая запись или недостаточная энергия 1–8 kHz.",
            method=method,
            limitations=SPECTRAL_LIMITS,
        )
        return amb, (
            amb
            if info.sample_rate > 48000
            else Finding("Not applicable", "Нужна PCM sample rate >48 kHz.")
        )
    relative = 10 * np.log10(np.maximum(power, 1e-30) / reference)
    occupancy = float(np.mean(relative[ref_mask] > -30))

    def band(a, b):
        selected = relative[(f >= a) & (f <= b)]
        return float(np.median(selected)) if selected.size >= 3 else None

    def boundary(c):
        below, above = band(c - 1200, c - 300), band(c + 300, c + 1200)
        if below is None or above is None:
            return None
        return {
            "boundary_hz": c,
            "below_db_relative": below,
            "above_db_relative": above,
            "drop_db": below - above,
            "adjacent_slope_db_per_khz": (below - above) / 1.5,
        }

    candidates = [
        m
        for c in range(14000, 21001, 1000)
        if c + 1200 < info.sample_rate / 2 and (m := boundary(c))
    ]
    best = max(candidates, key=lambda m: m["drop_db"], default=None)
    useful = occupancy >= 0.5
    evidence = bool(
        useful
        and best
        and best["below_db_relative"] > -35
        and best["drop_db"] >= 20
        and best["above_db_relative"] <= -40
    )
    loss = Finding(
        "Medium suspicion" if evidence else "Ambiguous",
        "Резкая граница полосы совместима с lossy-кодированием или фильтрацией."
        if evidence
        else "Недостаточно специфичных признаков для вывода о lossy-истории.",
        {
            "candidate": best,
            "reference_occupancy": occupancy,
            "thresholds": {
                "drop_db_min": 20,
                "above_db_max": -40,
                "below_db_min": -35,
                "reference_occupancy_min": 0.5,
            },
        },
        method,
        SPECTRAL_LIMITS,
        ["BAND_LIMIT"] if evidence else [],
    )
    if info.sample_rate <= 48000:
        return loss, Finding("Not applicable", "Нужна PCM sample rate >48 kHz.")
    boundaries = [m for c in (22050, 24000) if (m := boundary(c))]
    detected = [
        m
        for m in boundaries
        if useful
        and m["below_db_relative"] > -35
        and m["drop_db"] >= 20
        and m["above_db_relative"] <= -40
    ]
    up = Finding(
        "Medium suspicion" if detected else "Ambiguous",
        "Граница около исторического Nyquist совместима с ограниченным по полосе источником."
        if detected
        else "Историческая частота источника не установлена.",
        {
            "boundaries": boundaries,
            "band_22300_23700_db": band(22300, 23700),
            "above_24k_db": band(25000, info.sample_rate / 2 - 500),
            "source_rate": "Unknown",
            "thresholds": loss.measurements["thresholds"],
        },
        method,
        SPECTRAL_LIMITS
        + ["Энергия >22.05 kHz может быть шумом/результатом DSP и не доказывает 48 kHz origin."],
        ["NYQUIST_BOUNDARY"] if detected else [],
    )
    return loss, up


def spectrogram(context: PCMContext):
    n = min(2048, len(context.samples))
    if n < 64:
        raise AudioError("Недостаточно кадров для spectrogram")
    f, t, p = signal.spectrogram(
        context.samples,
        fs=context.info.sample_rate,
        window="hann",
        nperseg=n,
        noverlap=n // 2,
        axis=0,
        scaling="density",
        mode="psd",
    )
    # scipy returns frequency, channel, time for a frame-by-channel input.
    p = np.mean(p, axis=1)
    return f, t, 10 * np.log10(np.maximum(p, 1e-20))
