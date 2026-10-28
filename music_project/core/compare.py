import numpy as np
from scipy import signal

from music_project.core.decoder import PCMContext
from music_project.core.models import Finding
from music_project.core.pcm import db


def compare_pcm(a: PCMContext, b: PCMContext, max_offset_seconds: float = 2) -> Finding:
    limits = [
        "Сравнивается только перекрытие указанных фрагментов; это не whole-file identity.",
        "Нет resampling, time stretch, fractional-delay или drift compensation.",
        "Correlation похожих/периодических сигналов может давать неоднозначный Alignment.",
        "Глобальное усиление и полярность оцениваются одной МНК-моделью; субъективного ранжирования нет.",
    ]
    if a.info.sample_rate != b.info.sample_rate or a.info.channels != b.info.channels:
        return Finding(
            "Not applicable",
            "Для прямого сравнения нужны одинаковые Sample rate и Channels.",
            limitations=limits,
        )
    if a.info.channel_layout != b.info.channel_layout:
        return Finding(
            "Not applicable",
            "Channel layout различается; порядок каналов не установлен.",
            limitations=limits,
        )
    x, y = a.samples, b.samples
    n = min(len(x), len(y))
    if n < 256 or not np.any(x) or not np.any(y):
        return Finding("Ambiguous", "Тишина или недостаточно отсчётов.", limitations=limits)
    # Select the most energetic channel, never downmix opposite-polarity stereo.
    channel = int(np.argmax(np.mean(x[:n] ** 2, axis=0)))
    correlation = signal.correlate(y[:, channel], x[:, channel], mode="full", method="fft")
    lags = signal.correlation_lags(len(y), len(x), mode="full")
    max_lag = min(int(max_offset_seconds * a.info.sample_rate), n // 2)
    allowed = np.abs(lags) <= max_lag
    lag = int(lags[allowed][np.argmax(np.abs(correlation[allowed]))])
    peak = float(np.max(np.abs(correlation[allowed])))
    alternatives = allowed & (np.abs(lags - lag) > max(2, a.info.sample_rate // 1000))
    competitor = float(np.max(np.abs(correlation[alternatives]))) if np.any(alternatives) else 0
    uniqueness = 1 - competitor / peak if peak else 0
    start_x, start_y = max(0, -lag), max(0, lag)
    length = min(len(x) - start_x, len(y) - start_y)
    xx = x[start_x : start_x + length]
    yy = y[start_y : start_y + length]
    energy = float(np.sum(xx * xx))
    gain = float(np.sum(xx * yy) / energy)
    residual = yy - gain * xx
    normalized = float(np.sum(xx * yy) / np.sqrt(energy * np.sum(yy * yy)))
    same_prefix = x.shape == y.shape and np.array_equal(x, y)
    reliable = abs(normalized) >= 0.9 and abs(gain) > 1e-12 and (uniqueness >= 0.01 or same_prefix)
    return Finding(
        "Measured" if reliable else "Ambiguous",
        "Перекрытие после Alignment сравнено с компенсацией Gain и Polarity."
        if reliable
        else "Alignment не прошёл проверки надёжности; Null signal не интерпретируется.",
        {
            "offset_b_samples": lag,
            "offset_b_seconds": lag / a.info.sample_rate,
            "overlap_frames": length,
            "gain_b_over_a_db": db(abs(gain)),
            "polarity": "inverted" if gain < 0 else "same",
            "correlation": normalized,
            "identical_overlap": bool(np.array_equal(xx, yy)),
            "identical_prefix": bool(same_prefix),
            "alignment_peak_uniqueness": uniqueness,
            "alignment_reliable": bool(reliable),
            "residual_rms_dbfs_after_gain": db(float(np.sqrt(np.mean(residual**2))))
            if reliable
            else None,
            "residual_max_abs_after_gain": float(np.max(np.abs(residual))) if reliable else None,
            "resampled": False,
            "alignment_channel": channel,
            "max_offset_seconds": max_offset_seconds,
            "scope_a": a.scope,
            "scope_b": b.scope,
        },
        "Alignment через FFT cross-correlation с целым смещением; "
        "Gain по least squares; Correlation — нормированное скалярное произведение.",
        limits,
    )
