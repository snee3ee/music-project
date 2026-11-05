"""Conservative PCM measurements; historical provenance remains uncertain."""

import json
import math
import re
from dataclasses import replace

import numpy as np
from scipy import signal

from music_project.core.config import Settings
from music_project.core.decoder import PCMContext, input_args
from music_project.core.models import AudioError, AudioInfo, Finding, Observation
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
        observations=[
            Observation(
                "FULL_SCALE_SAMPLES",
                "Detected" if np.any(counts) else "Not detected",
                f"Full-scale samples: {int(counts.sum()):,} в проверенном фрагменте.",
                int(counts.sum()),
                "samples",
            )
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
    try:
        raw = json.loads(matches[-1])
        data = {key: float(raw[key]) for key in ("input_i", "input_lra", "input_tp")}
    except (ValueError, TypeError, KeyError) as exc:
        raise AudioError("FFmpeg вернул некорректные loudnorm measurements") from exc

    def finite(key):
        value = float(data[key])
        return value if math.isfinite(value) else None

    def value_state(key):
        value = float(data[key])
        return (
            "negative infinity"
            if value == -math.inf
            else "finite"
            if math.isfinite(value)
            else "undefined"
        )

    tp = finite("input_tp")
    tp_state = value_state("input_tp")
    return Finding(
        "Measured",
        "Громкость и True Peak измерены по всему первому аудиопотоку.",
        {
            "integrated_lufs": finite("input_i"),
            "integrated_lufs_state": value_state("input_i"),
            "lra_lu": finite("input_lra"),
            "true_peak_dbtp": tp,
            "true_peak_state": tp_state,
            "true_peak_above_0_dbtp": tp > 0
            if tp is not None
            else False
            if tp_state == "negative infinity"
            else None,
            "scope": "whole first audio stream",
        },
        "Входные измерения FFmpeg loudnorm; True Peak оценивается через pipeline 192 kHz.",
        [
            "Измеряется вход loudnorm; нормализованный выход отбрасывается, файл не меняется.",
            "LUFS может быть неопределён для тишины/очень короткого сигнала; LRA коротких записей ограничен.",
            "True Peak — оценка реконструированного пика, отличная от Sample Peak.",
        ],
        observations=[
            Observation(
                "TRUE_PEAK_OVER",
                "Insufficient data"
                if tp is None and tp_state != "negative infinity"
                else "Detected"
                if tp is not None and tp > 0
                else "Not detected",
                "True Peak: −∞ dBTP (нулевой пик по FFmpeg); превышений нет."
                if tp_state == "negative infinity"
                else "FFmpeg не вернул значение True Peak."
                if tp is None
                else "True Peak превышает 0 dBTP."
                if tp > 0
                else "Превышений True Peak выше 0 dBTP не обнаружено по оценке FFmpeg.",
                tp,
                "dBTP",
            )
        ],
    )


def quantization(context: PCMContext) -> Finding:
    info = context.info
    limits = [
        "Dither, Gain, фильтры и DSP могут стереть прежний Quantization grid.",
        "Lower-byte entropy не доказывает native 24-bit; число PCM levels не исключает обработанный 16-bit источник.",
        "Совместимость с 16-bit grid не устанавливает историю файла.",
    ]
    if info.kind != "PCM" or info.bit_depth != 24 or not info.lossless:
        return Finding(
            "Not applicable",
            "Метод применим к lossless integer PCM 24-bit.",
            limitations=limits,
            observations=[
                Observation(
                    "PADDING_GRID",
                    "Not applicable",
                    "16→24 Padding: проверка применяется только к lossless integer PCM 24-bit.",
                )
            ],
        )
    # Float64 exactly represents all 24-bit integers. Decode preserves native scale.
    budget = max(1, 1_000_000 // info.channels)
    selected = []
    for channel in context.samples.T:
        values = np.rint(channel * (1 << 23)).astype(np.int64)
        nonzero = values[values != 0]
        selected.append(nonzero[:: max(1, math.ceil(nonzero.size / budget))])
    active = np.concatenate(selected)
    if active.size < 1000:
        return Finding(
            "Ambiguous",
            "Недостаточно активных отсчётов (нужно ≥1000).",
            {"active_samples": int(active.size)},
            limitations=limits,
            observations=[
                Observation(
                    "PADDING_GRID",
                    "Insufficient data",
                    f"16-bit grid: доступно {active.size} активных samples; для проверки нужно ≥1000.",
                )
            ],
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
        "Все активные samples выборки лежат на 16-bit grid; это совместимо с 16→24 Padding."
        if padded
        else "В выборке есть ненулевые младшие 8 bits: прямой 16→24 Padding не описывает всю выборку.",
        {
            "zero_lower_byte_percent": zero,
            "distinct_lower_bytes": int(np.count_nonzero(counts)),
            "distinct_sample_values": distinct,
            "lower_byte_entropy_bits": entropy,
            "normalized_entropy": entropy / 8,
            "active_samples": int(active.size),
            "compatible_with_65536_output_levels": distinct <= 65536,
            "sampling": "nonzero samples per channel, deterministic stride, total max 1,000,000",
        },
        "Samples представлены как signed 24-bit; lower byte — младшие 8 bits; "
        "Shannon entropy вычисляется по распределению lower bytes.",
        limits,
        ["ZERO_LOW_BYTE_GRID"] if padded else [],
        observations=[
            Observation(
                "PADDING_GRID",
                "Detected" if padded else "Not detected",
                "16-bit grid обнаружен: младшие 8 bits нулевые у всех активных samples выборки."
                if padded
                else f"16-bit grid отсутствует у части samples: нулевой lower byte у {zero:.2f}%.",
                zero,
                "%",
            )
        ],
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
    method = "Welch PSD: Window Hann, FFT 8192 или доступное число frames, Overlap 50%; "
    method += "усредняется мощность Channels, Downmix не выполняется."
    if info.kind != "PCM" or not info.lossless:
        return tuple(
            Finding(
                "Not applicable",
                "Спектральные эвристики: только lossless PCM.",
                observations=[
                    Observation(
                        code, "Not applicable", f"{label}: проверка рассчитана на lossless PCM."
                    )
                ],
            )
            for code, label in (("CUTOFF", "Cutoff"), ("NYQUIST_BOUNDARY", "Nyquist boundary"))
        )
    if info.sample_rate / 2 <= 15200:
        # The first candidate is 14 kHz and needs a complete upper band to 15.2 kHz.
        return (
            Finding(
                "Not applicable",
                "Доступная полоса не вмещает проверяемые Cutoff bands.",
                observations=[
                    Observation(
                        "CUTOFF",
                        "Not applicable",
                        f"Cutoff: Nyquist равен {info.sample_rate / 2000:g} kHz; "
                        "для метода нужна полная полоса вокруг хотя бы одной границы 14–21 kHz.",
                    )
                ],
            ),
            Finding(
                "Not applicable",
                "Нужна PCM Sample rate >48 kHz.",
                observations=[
                    Observation(
                        "NYQUIST_BOUNDARY",
                        "Not applicable",
                        f"Upsampling: Sample rate {info.sample_rate / 1000:g} kHz; метод применяется выше 48 kHz.",
                    )
                ],
            ),
        )
    try:
        f, power = spectrum(context)
    except AudioError as exc:
        return tuple(
            Finding(
                "Ambiguous",
                str(exc),
                limitations=SPECTRAL_LIMITS,
                observations=[Observation(code, "Insufficient data", str(exc))],
            )
            for code in ("CUTOFF", "NYQUIST_BOUNDARY")
        )
    ref_mask = (f >= 1000) & (f <= 8000)
    reference = float(np.mean(power[ref_mask])) if np.any(ref_mask) else 0
    if reference <= 1e-16 or len(context.samples) < info.sample_rate:
        amb = Finding(
            "Ambiguous",
            "Тишина, короткая запись или недостаточная энергия 1–8 kHz.",
            method=method,
            limitations=SPECTRAL_LIMITS,
            observations=[
                Observation(
                    "CUTOFF",
                    "Insufficient data",
                    "Cutoff: для проверки нужен фрагмент ≥1 s с измеримой энергией в 1–8 kHz.",
                )
            ],
        )
        return amb, (
            replace(
                amb,
                observations=[
                    Observation(
                        "NYQUIST_BOUNDARY",
                        "Insufficient data",
                        "Nyquist boundary: для проверки нужен фрагмент ≥1 s с измеримой энергией в 1–8 kHz.",
                    )
                ],
            )
            if info.sample_rate > 48000
            else Finding(
                "Not applicable",
                "Нужна PCM Sample rate >48 kHz.",
                observations=[
                    Observation(
                        "NYQUIST_BOUNDARY",
                        "Not applicable",
                        f"Upsampling: Sample rate {info.sample_rate / 1000:g} kHz; метод применяется выше 48 kHz.",
                    )
                ],
            )
        )
    relative = 10 * np.log10(np.maximum(power, 1e-30) / reference)
    occupancy = float(np.mean(relative[ref_mask] > -30))

    def band(a, b):
        selected = relative[(f >= a) & (f <= b)]
        return float(np.median(selected)) if selected.size >= 3 else None

    def boundary(c):
        if c + 1200 >= info.sample_rate / 2:
            return None
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
    cutoff_evaluable = bool(useful and best and best["below_db_relative"] > -35)
    cutoff_observation = Observation(
        "CUTOFF",
        "Detected" if evidence else "Not detected" if cutoff_evaluable else "Insufficient data",
        (
            f"Cutoff около {best['boundary_hz'] / 1000:g} kHz: спад {best['drop_db']:.1f} dB; "
            "выполнены пороги резкой границы."
        )
        if evidence
        else (
            f"Cutoff по заданным порогам не обнаружен среди проверенных границ "
            f"{candidates[0]['boundary_hz'] / 1000:g}–{candidates[-1]['boundary_hz'] / 1000:g} kHz "
            "с шагом 1 kHz."
        )
        if cutoff_evaluable
        else "Cutoff: недостаточная ширина или уровень спектра для проверки границы в 14–21 kHz.",
        best["boundary_hz"] if evidence else None,
        "Hz",
    )
    loss = Finding(
        "Medium suspicion" if evidence else "Ambiguous",
        "Резкая граница полосы совместима с lossy-кодированием или фильтрацией."
        if evidence
        else "Недостаточно специфичных признаков для вывода о lossy-истории.",
        {
            "candidate": best,
            "reference_occupancy": occupancy,
            "checked_boundaries_hz": [m["boundary_hz"] for m in candidates],
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
        observations=[cutoff_observation],
    )
    if info.sample_rate <= 48000:
        return loss, Finding(
            "Not applicable",
            "Нужна PCM Sample rate >48 kHz.",
            observations=[
                Observation(
                    "NYQUIST_BOUNDARY",
                    "Not applicable",
                    f"Upsampling: Sample rate {info.sample_rate / 1000:g} kHz; метод применяется выше 48 kHz.",
                )
            ],
        )
    boundaries = [m for c in (22050, 24000) if (m := boundary(c))]
    detected = [
        m
        for m in boundaries
        if useful
        and m["below_db_relative"] > -35
        and m["drop_db"] >= 20
        and m["above_db_relative"] <= -40
    ]
    evaluable = any(useful and m["below_db_relative"] > -35 for m in boundaries)
    nyquist_observation = Observation(
        "NYQUIST_BOUNDARY",
        "Detected" if detected else "Not detected" if evaluable else "Insufficient data",
        "Nyquist boundary: признак около "
        + ", ".join(f"{m['boundary_hz'] / 1000:g} kHz" for m in detected)
        + "."
        if detected
        else "Nyquist boundary по заданным порогам не обнаружен около "
        + " / ".join(f"{m['boundary_hz'] / 1000:g} kHz" for m in boundaries)
        + "."
        if evaluable
        else "Nyquist boundary: уровень около 22.05 / 24 kHz недостаточен для проверки границы.",
    )
    upper_band = band(22300, 23700)
    above_24 = band(25000, info.sample_rate / 2 - 500)

    def psd_observation(code, label, level):
        if level is None:
            return Observation(
                code, "Insufficient data", f"{label}: полоса недоступна при этой Sample rate."
            )
        above = level > -40
        return Observation(
            code,
            "Above threshold" if above else "Below threshold",
            f"{label}: {level:.1f} dB относительно 1–8 kHz; "
            f"{'выше' if above else 'не выше'} порога −40 dB.",
            level,
            "dB rel. 1–8 kHz",
        )

    up = Finding(
        "Medium suspicion" if detected else "Ambiguous",
        "Граница около исторического Nyquist совместима с ограниченным по полосе источником."
        if detected
        else "Историческая частота источника не установлена.",
        {
            "boundaries": boundaries,
            "band_22300_23700_db": upper_band,
            "above_24k_db": above_24,
            "source_rate": "Unknown",
            "thresholds": loss.measurements["thresholds"],
        },
        method,
        SPECTRAL_LIMITS
        + ["Энергия >22.05 kHz может быть шумом/результатом DSP и не доказывает 48 kHz origin."],
        ["NYQUIST_BOUNDARY"] if detected else [],
        observations=[
            nyquist_observation,
            psd_observation("PSD_22300_23700", "Median PSD 22.3–23.7 kHz", upper_band),
            psd_observation("PSD_ABOVE_24K", "Median PSD выше 25 kHz", above_24),
        ],
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
