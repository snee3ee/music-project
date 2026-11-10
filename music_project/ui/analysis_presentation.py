"""Pure, lossless presentation transformations. No audio analysis or Streamlit calls."""

import re
from dataclasses import dataclass, field
from typing import Any

from music_project.core.duration import ffprobe_duration
from music_project.core.models import Analysis
from music_project.ui.presentation import duration_text

MODULES = {
    "overview": "Обзор",
    "integrity": "Целостность",
    "measurements": "Спектр и уровни",
    "provenance": "Origin Investigator",
    "dsd": "DSD Diagnostics",
    "appendix": "Техническое приложение",
}
CATEGORIES = {
    "Measured": "Измерено",
    "Verified": "Проверено",
    "Derived": "Рассчитано",
    "Inferred": "Вывод по правилу",
    "Unknown": "Неизвестно",
    "Ambiguous": "Неоднозначно",
    "Not applicable": "Не применяется",
    "Unsupported": "Не поддерживается",
    "Not validated": "Не валидировано",
}


@dataclass
class WarningGroup:
    message: str
    summary: str
    events: int = 0
    intervals: list[int] = field(default_factory=list)
    raw_events: list[dict[str, Any]] = field(default_factory=list)


def decoder_warnings(result: Analysis) -> list[WarningGroup]:
    groups: dict[str, WarningGroup] = {}
    finding = result.findings.get("dsd_integrity")
    pcm = result.findings.get("pcm_integrity")
    attempts = (
        finding.measurements.get("attempts", [])
        if finding
        else [{"warnings": pcm.measurements.get("warnings", [])}]
        if pcm
        else []
    )
    for index, attempt in enumerate(attempts, 1):
        for raw in attempt.get("warnings", []):
            message = re.sub(r"\[[^\]]+ @ (?:0x)?[0-9a-fA-F]+\]\s*", "", raw).strip()
            message = re.sub(r"^\[warning\]\s*", "", message)
            summary = (
                "Длительность оценена декодером по bitrate; точность этой оценки ограничена."
                if "Estimating duration from bitrate" in message
                else "Нефатальное предупреждение декодера; исходный текст в приложении."
            )
            group = groups.setdefault(message, WarningGroup(message, summary))
            group.events += 1
            if index not in group.intervals:
                group.intervals.append(index)
            group.raw_events.append({"interval": index, "message": raw})
    return list(groups.values())


def available_modules(result: Analysis) -> list[str]:
    keys = ["overview", "integrity"]
    if (
        "peaks" in result.findings
        or result.findings.get("dsd_audible")
        and (result.findings["dsd_audible"].status == "Measured")
    ):
        keys.append("measurements")
    if any(
        key in result.findings
        for key in ("lossy_history", "upsampling", "quantization", "dsd_evidence")
    ):
        keys.append("provenance")
    if result.info.kind == "DSD":
        keys.append("dsd")
    return keys + ["appendix"]


def declared_duration(result: Analysis) -> float | None:
    if result.info.duration_details:
        return result.info.duration
    container = result.findings.get("dsd_container")
    if container and container.status == "Passed":
        return container.measurements.get("expected_duration_seconds")
    return result.info.duration if result.info.kind != "DSD" else None


def duration_display(result: Analysis) -> tuple[str, str]:
    seconds = declared_duration(result)
    if result.info.kind != "DSD":
        return "Длительность · ffprobe", duration_text(seconds)
    if seconds is None:
        return "Длительность аудио · не установлена", "Не установлена"
    label = (
        "Длительность аудио · проверено"
        if result.info.duration_status == "Verified"
        else "Длительность аудио · расчёт"
    )
    return label, duration_text(seconds)


def duration_sources(result: Analysis) -> list[dict[str, Any]]:
    rows = [
        {
            "source": "ffprobe metadata",
            "seconds": ffprobe_duration(result.info),
            "category": "Unknown",
        }
    ]
    container = result.findings.get("dsd_container")
    if container:
        rows.append(
            {
                "source": "DSF sample count / native rate"
                if container.measurements.get("container") == "DSF"
                else "DFF payload length / channels / native rate",
                "seconds": container.measurements.get("expected_duration_seconds"),
                "category": "Derived",
            }
        )
        integrity = result.findings.get("dsd_integrity")
        if integrity:
            rows.append(
                {
                    "source": "Decoded PCM frames / verified PCM rate",
                    "seconds": integrity.measurements.get("successfully_decoded_seconds"),
                    "category": "Derived",
                    "complete_file": result.scope.get("complete_file", False),
                }
            )
    return rows


def integrity_summary(result: Analysis) -> dict[str, Any]:
    integrity = result.findings.get("dsd_integrity")
    container = result.findings.get("dsd_container")
    if integrity:
        attempts = integrity.measurements.get("attempts", [])
        groups = decoder_warnings(result)
        return {
            "container_status": container.status if container else "Unknown",
            "decode_status": integrity.status,
            "complete_file": result.scope.get("complete_file", False),
            "intervals": len(result.scope.get("ranges", [])),
            "decoded_seconds": result.scope.get("decoded_seconds", 0),
            "warning_events": sum(g.events for g in groups),
            "warning_groups": groups,
            "fatal_errors": [
                a["fatal_error"]
                for a in attempts
                if a.get("fatal_error") and a["status"] == "Failed"
            ],
            "container_errors": container.measurements.get("errors", []) if container else [],
            "container_warnings": container.measurements.get("warnings", []) if container else [],
        }
    pcm = result.findings.get("pcm_integrity")
    if pcm:
        m = pcm.measurements
        return {
            "container_status": "Not performed",
            "decode_status": m.get("decode_status", pcm.status),
            "complete_file": bool(m.get("complete_file")),
            "intervals": 1,
            "decoded_seconds": m.get("decoded_seconds", 0),
            "warning_events": m.get("warning_events"),
            "warning_groups": decoder_warnings(result),
            "fatal_errors": [m["fatal_error"]] if m.get("fatal_error") else [],
            "container_errors": [],
            "container_warnings": [],
        }
    # Legacy results distinguish a missing check from warnings which were not retained.
    return {
        "container_status": "Unknown",
        "decode_status": "Partial",
        "complete_file": False,
        "intervals": 1,
        "decoded_seconds": result.scope.get("decoded_seconds", 0),
        "warning_events": None,
        "warning_groups": [],
        "fatal_errors": [],
        "container_errors": [],
        "container_warnings": [],
    }


def band_rows(bands: list[dict], *, measured_only: bool = True) -> list[dict[str, Any]]:
    """Rounded dB power for display. Exact linear values stay in results/appendix."""
    rows = []
    for band in bands:
        if measured_only and band["status"] != "Measured":
            continue
        row = {
            "Полоса, kHz": f"{band['low_hz'] / 1000:g}–{band['high_hz'] / 1000:g}",
            "Статус": band["status"],
        }
        powers = band.get("power_db_re_fs2")
        if powers is not None:
            for channel, value in enumerate(powers, 1):
                row[f"Канал {channel}, dB re FS²"] = f"{value:.1f}" if value is not None else "−∞"
            if len(powers) == 2:
                delta = band.get("left_minus_right_db")
                row["L−R, dB"] = f"{delta:.1f}" if delta is not None else "Не определено"
        rows.append(row)
    return rows
