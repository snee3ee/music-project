"""Read-only presentation of saved facts. No metering or historical classification."""

import math

from music_project.ui.analysis_presentation import integrity_summary


def measured(result, key):
    finding = result.findings.get(key)
    return finding.measurements if finding and finding.status == "Measured" else {}


def signal_values(result):
    return measured(result, "loudness"), measured(result, "full_peaks") or measured(result, "peaks")


def number_text(values, key, *, zero_is_silence=False):
    value = values.get(key)
    if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
        return f"{value:.2f}"
    state_key = {
        "integrated_lufs": "integrated_lufs_state",
        "true_peak_dbtp": "true_peak_state",
    }.get(key)
    if values.get(state_key) == "negative infinity" or zero_is_silence:
        return "−∞"
    return "Не определено"


def scope_label(scope, *, logical=False):
    if not scope:
        return "Область не установлена"
    if scope.get("complete_file"):
        return (
            "Вся выбранная дорожка" if logical or "source_start_seconds" in scope else "Весь поток"
        )
    ranges = scope.get("ranges", [])
    seconds = scope.get("analyzed_seconds", scope.get("decoded_seconds"))
    if len(ranges) > 1:
        return (
            f"{len(ranges)} интервала · {seconds:.3f} s"
            if seconds is not None
            else "Выбранные интервалы"
        )
    if seconds is not None:
        start = scope.get("start_seconds", ranges[0].get("start_seconds", 0) if ranges else 0)
        return f"Интервал {start:g}–{start + seconds:g} s"
    return "Область не установлена"


def integrity_view(result):
    s = integrity_summary(result)
    pcm = result.findings.get("pcm_integrity")
    flac = pcm.measurements.get("flac_md5", {}) if pcm else {}
    md5 = flac.get("md5_status", flac.get("status"))
    frames = flac.get("frame_count_status")
    failed = bool(
        s["fatal_errors"]
        or s["container_errors"]
        or s["decode_status"] == "Failed"
        or md5 == "Failed"
        or frames == "Failed"
    )
    complete = s["complete_file"] and s["decode_status"] == "Passed"
    if failed:
        headline = "Проверка не пройдена"
    elif complete:
        headline = "Полное декодирование пройдено"
    elif s["decode_status"] in {"Unsupported", "Not validated"}:
        headline = "Декодирование недоступно"
    elif s["decode_status"] == "Partial" and s["decoded_seconds"] > 0:
        headline = "Фрагмент декодирован; весь поток не проверен"
    else:
        headline = "Полная проверка не выполнена"
    if complete and not failed and "logical_source" in result.findings:
        headline = "Выбранная дорожка полностью декодирована"
    detail = []
    if failed and s["decode_status"] == "Passed":
        detail.append("Декодирование завершено, но отдельная проверка выявила несоответствие.")
    if md5 == "Verified":
        detail.append("PCM MD5 совпал с FLAC.")
    elif md5 == "Failed":
        detail.append("PCM MD5 не совпал с FLAC.")
    if frames == "Failed":
        detail.append("Объявленное и декодированное число кадров различается.")
    area = pcm.measurements.get("scope", result.scope) if pcm else result.scope
    return {
        **s,
        "headline": headline,
        "detail": " ".join(detail),
        "failed": failed,
        "coverage": scope_label(area, logical="logical_source" in result.findings),
        "flac": flac,
    }


def provenance_status(result):
    finding = result.findings.get("origin_investigation")
    if not finding:
        return "Не исследовано"
    if finding.status == "Unsupported":
        return "Исследование недоступно"
    return "Исторический источник не установлен"
