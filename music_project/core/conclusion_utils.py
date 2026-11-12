"""Shared deterministic validity/scope helpers; no decoding or presentation state."""

import math


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def same_scope(a, b):
    keys = (
        "start_seconds",
        "end_seconds",
        "frames",
        "sample_rate_hz",
        "channels",
        "domain",
        "processing",
    )
    if a and b and ("source_identity" in a or "source_identity" in b):
        keys += ("source_identity", "source_start_seconds")
    return bool(a and b and all(k in a and k in b and a[k] == b[k] for k in keys))


def scope_text(scope):
    if not isinstance(scope, dict) or not number(scope.get("analyzed_seconds")):
        return "область измерения не установлена"
    if scope.get("complete_file"):
        if "source_start_seconds" in scope:
            return f"вся выбранная дорожка, {scope['analyzed_seconds']:.3f} s"
        return f"весь декодированный аудиопоток, {scope['analyzed_seconds']:.3f} s"
    if len(scope.get("ranges", [])) > 1:
        return f"{len(scope['ranges'])} выбранных интервала, суммарно {scope['analyzed_seconds']:.3f} s; весь файл не проверен"
    return f"интервал {scope.get('start_seconds', 0):.3f}–{scope.get('end_seconds', 0):.3f} s; весь файл не проверен"


def measurement_inputs(findings: dict) -> tuple[dict, dict, dict, dict]:
    loudness = findings.get("loudness")
    peaks = findings.get("full_peaks", findings.get("peaks"))
    lm = loudness.measurements if loudness and loudness.status == "Measured" else {}
    pm = peaks.measurements if peaks and peaks.status == "Measured" else {}
    return lm, pm, lm.get("scope", {}), pm.get("scope", {})
