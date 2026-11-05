"""Russian UI wording and values; engineering terms remain in English."""

import re
from typing import Any

STATUS = {
    "Passed": "Проверка пройдена",
    "Failed": "Проверка не пройдена",
    "Partial": "Частичная проверка",
    "Inferred": "Выведено по правилу",
    "Derived": "Рассчитано",
    "Experimental": "Экспериментально",
    "Not validated": "Не валидировано",
    "Measured": "Измерено",
    "Verified": "Проверено",
    "Ambiguous": "Недостаточно признаков",
    "Unknown": "Нет подтверждённых данных",
    "Not applicable": "Не применяется",
    "Unsupported": "Не поддерживается",
    "Detected": "Обнаружено",
    "Not detected": "Не обнаружено по заданным порогам",
    "Insufficient data": "Недостаточно данных",
    "Above threshold": "Выше порога",
    "Below threshold": "Не выше порога",
    "Medium suspicion": "Среднее подозрение — эвристика",
    "Direct 16→24 padding evidence": "Обнаружен 16-bit grid",
    "No direct-padding evidence": "Прямой 16→24 Padding не обнаружен",
    "Indexed": "В индексе",
    "Unreadable/unsupported": "Не читается или не поддерживается",
    "Removed": "Больше нет в папке",
    "Unchanged": "Без изменений",
    "Modified": "Изменён",
    "Hash mismatch": "SHA-256 не совпадает",
    "New": "Новый",
    "Missing": "Отсутствует",
    "Unreadable": "Не читается",
    "Compatible": "Соответствует профилю",
    "Incompatible": "Не соответствует профилю",
}

LABELS = {
    "sample_peak_dbfs": "Sample Peak, dBFS",
    "rms_dbfs": "RMS, dBFS",
    "crest_factor_db": "Crest factor, dB",
    "full_scale_samples_per_channel": "Full-scale samples по Channels",
    "samples_above_1": "Samples выше цифрового full scale",
    "full_scale_threshold": "Порог full scale",
    "integrated_lufs": "Integrated loudness, LUFS",
    "integrated_lufs_state": "Состояние Integrated loudness",
    "lra_lu": "Loudness Range, LU",
    "true_peak_dbtp": "True Peak, dBTP",
    "true_peak_state": "Состояние True Peak",
    "true_peak_above_0_dbtp": "True Peak выше 0 dBTP",
    "scope": "Область измерения",
    "candidate": "Кандидат Cutoff",
    "reference_occupancy": "Доля FFT bins с достаточной энергией в 1–8 kHz",
    "thresholds": "Пороги метода",
    "checked_boundaries_hz": "Проверенные границы Cutoff, Hz",
    "drop_db_min": "Минимальный спад, dB",
    "above_db_max": "Максимальный уровень над границей, dB",
    "below_db_min": "Минимальный уровень под границей, dB",
    "reference_occupancy_min": "Минимальная доля FFT bins",
    "boundary_hz": "Граница, Hz",
    "below_db_relative": "Median PSD под границей, dB rel.",
    "above_db_relative": "Median PSD над границей, dB rel.",
    "drop_db": "Спад, dB",
    "adjacent_slope_db_per_khz": "Оценка крутизны, dB/kHz",
    "boundaries": "Nyquist boundaries",
    "band_22300_23700_db": "Median PSD 22.3–23.7 kHz, dB rel.",
    "above_24k_db": "Median PSD выше 25 kHz, dB rel.",
    "source_rate": "Историческая Source rate",
    "zero_lower_byte_percent": "Нулевой lower byte, %",
    "distinct_lower_bytes": "Различных lower bytes",
    "distinct_sample_values": "Различных PCM levels",
    "lower_byte_entropy_bits": "Lower-byte entropy, bits",
    "normalized_entropy": "Normalized entropy",
    "active_samples": "Активных samples в выборке",
    "compatible_with_65536_output_levels": "Не более 65 536 выходных PCM levels",
    "sampling": "Способ выборки",
    "offset_b_samples": "Смещение B, samples",
    "offset_b_seconds": "Смещение B, s",
    "overlap_frames": "Перекрытие, frames",
    "gain_b_over_a_db": "Gain B относительно A, dB",
    "polarity": "Polarity",
    "correlation": "Correlation",
    "identical_overlap": "PCM в выровненном перекрытии совпадает",
    "identical_prefix": "Проверенные фрагменты совпадают полностью",
    "alignment_peak_uniqueness": "Разделение пиков Alignment",
    "alignment_reliable": "Alignment прошёл проверки",
    "residual_rms_dbfs_after_gain": "Residual RMS после Gain, dBFS",
    "residual_max_abs_after_gain": "Максимальный Residual после Gain",
    "resampled": "Выполнялся Resampling",
    "alignment_channel": "Channel для Alignment (с нуля)",
    "max_offset_seconds": "Диапазон поиска смещения, s",
    "scope_a": "Фрагмент A",
    "scope_b": "Фрагмент B",
    "strategy": "Область",
    "start_seconds": "Начало, s",
    "decoded_seconds": "Проверено, s",
    "frames": "Frames",
    "channels": "Channels",
    "format": "Формат декодирования",
    "complete_file": "Проверен весь файл",
    "native_rate_hz": "Native DSD rate, Hz",
    "dsd_family": "Семейство DSD",
    "title": "Название",
    "performer": "Исполнитель",
    "profile": "Профиль устройства",
    "new": "Новых файлов",
    "modified": "Изменённых файлов",
    "unchanged": "Без повторного анализа",
    "removed": "Отсутствуют в папке",
    "errors": "Требуют проверки",
    "cancelled": "Сканирование отменено",
    "name": "Название",
    "codecs": "Codec",
    "max_pcm_rate": "Максимальная PCM Sample rate, Hz",
    "bit_depths": "Bit depth",
    "max_channels": "Максимум Channels",
    "dsd_rates": "DSD rates, Hz",
}

TEXT = {
    "whole first audio stream": "Весь первый аудиопоток",
    "prefix": "Начальный фрагмент",
    "metadata only": "Только метаданные",
    "Unknown": "Нет подтверждённых данных",
    "same": "Без инверсии",
    "inverted": "Инвертирована",
    "negative infinity": "−∞",
    "finite": "Конечное значение",
    "undefined": "Backend не вернул значение",
    "nonzero interleaved samples, deterministic stride, max 1,000,000": "Ненулевые samples всех Channels; равномерный шаг; максимум 1 000 000",
    "f64le, native sample rate and channel order; no downmix": "f64 PCM; исходная Sample rate и порядок Channels; без Downmix",
}


def status_text(value: str) -> str:
    return STATUS.get(value, value)


def format_value(value: Any, key: str = "") -> str:
    if value is None:
        if key in {"sample_peak_dbfs", "rms_dbfs", "crest_factor_db"}:
            return "−∞ (тишина)" if key != "crest_factor_db" else "Не применяется к тишине"
        return "Нет значения в результате"
    if isinstance(value, bool):
        return "Да" if value else "Нет"
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".")
    if isinstance(value, int):
        return f"{value:,}".replace(",", " ")
    if isinstance(value, list):
        return "; ".join(format_value(item, key) for item in value)
    return TEXT.get(str(value), str(value))


def measurement_rows(values: dict, prefix: str = "") -> list[dict[str, str]]:
    rows = []
    for key, value in values.items():
        label = LABELS.get(key, key.replace("_", " "))
        label = f"{prefix} · {label}" if prefix else label
        if isinstance(value, dict):
            rows.extend(measurement_rows(value, label))
        elif isinstance(value, list) and value and isinstance(value[0], dict):
            for index, item in enumerate(value, 1):
                rows.extend(measurement_rows(item, f"{label} {index}"))
        else:
            state_key = {
                "true_peak_dbtp": "true_peak_state",
                "integrated_lufs": "integrated_lufs_state",
            }.get(key)
            if value is None and state_key and values.get(state_key) == "negative infinity":
                formatted = "−∞"
            elif key.startswith("residual_") and value is None:
                formatted = (
                    "−∞ (Residual равен нулю)"
                    if values.get("alignment_reliable")
                    else "Не интерпретируется: Alignment не прошёл проверки"
                )
            else:
                formatted = format_value(value, key)
            rows.append({"Показатель": label, "Значение": formatted})
    return rows


def duration_text(seconds: float | None) -> str:
    if seconds is None:
        return "Длительность не указана в метаданных"
    minutes, remainder = divmod(seconds, 60)
    hours, minutes = divmod(int(minutes), 60)
    return f"{hours}:{minutes:02d}:{remainder:05.2f}" if hours else f"{minutes}:{remainder:05.2f}"


def codec_text(codec: str) -> str:
    if codec.startswith("pcm_"):
        return "PCM (float)" if codec.startswith("pcm_f") else "PCM (integer)"
    if codec.startswith("dsd_"):
        return "DSD"
    return {
        "flac": "FLAC",
        "alac": "ALAC",
        "mp3": "MP3",
        "aac": "AAC",
        "opus": "Opus",
        "vorbis": "Vorbis",
        "wavpack": "WavPack",
        "dst": "DST",
        "ape": "Monkey’s Audio",
        "tak": "TAK",
        "tta": "TTA",
    }.get(codec, codec)


def container_text(container: str) -> str:
    return {
        "mov,mp4,m4a,3gp,3g2,mj2": "семейство MP4 / M4A",
        "matroska,webm": "семейство Matroska / WebM",
        "dsdiff": "DSDIFF (DFF)",
    }.get(container, container.upper())


def metadata_text(text: str) -> str:
    if text.startswith("Missing "):
        return "Не заполнен tag " + text.removeprefix("Missing ")
    if text.startswith("Album differs: "):
        field = text.removeprefix("Album differs: ")
        return "Различается " + {
            "sample_rate": "Sample rate",
            "bit_depth": "Bit depth",
            "channels": "Channels",
            "channel_layout": "Channel layout",
            "codec": "Codec",
        }.get(field, field)
    return {"Duplicate disc/track numbers": "Повторяются номера Disc / Track"}.get(text, text)


def cue_issue_text(text: str) -> str:
    if match := re.fullmatch(r"FILE line (\d+): invalid/missing reference (.*)", text):
        return f"Строка {match[1]}: ссылка недопустима или файл отсутствует — {match[2]}"
    if match := re.fullmatch(r"(INDEX|TRACK) line (\d+): (.*)", text):
        reason = {
            "invalid timestamp/context": "неверное время или положение INDEX",
            "unresolved FILE": "не указан допустимый FILE",
        }.get(match[3], match[3])
        return f"Строка {match[2]}: {match[1]} — {reason}."
    if match := re.fullmatch(r"Track (\d+): (.*)", text):
        reason = {
            "missing INDEX 01": "не указан INDEX 01",
            "non-increasing INDEX 01": "INDEX 01 не следует за предыдущим Track",
            "INDEX 00 after INDEX 01": "INDEX 00 расположен после INDEX 01",
        }.get(match[2], match[2])
        return f"Track {match[1]}: {reason}."
    if text.startswith("Duplicate track number "):
        return "Повторяется номер Track " + text.removeprefix("Duplicate track number ")
    return {"No AUDIO tracks": "В CUE нет Tracks типа AUDIO."}.get(text, text)
