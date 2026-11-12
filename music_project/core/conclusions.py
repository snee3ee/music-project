"""Deterministic versioned conclusion orchestration; no UI or audio decoding."""

from music_project.core.conclusion_evidence import _integrity_conclusions, _origin_conclusions
from music_project.core.conclusion_lossy import lossy_conclusions
from music_project.core.conclusion_loudness import loudness_rules
from music_project.core.conclusion_models import Conclusion, ReferenceProfile
from music_project.core.conclusion_peaks import peak_rules
from music_project.core.conclusion_reference import reference_rules
from music_project.core.conclusion_utils import number, same_scope, scope_text
from music_project.core.models import AudioInfo, Finding


def build_conclusions(
    info: AudioInfo,
    scope: dict,
    findings: dict[str, Finding],
    reference: ReferenceProfile | None = None,
) -> list[Conclusion]:
    ref = reference or ReferenceProfile()
    peak_key = "full_peaks" if "full_peaks" in findings else "peaks"
    for value in (ref.loudness_lufs, ref.peak_ceiling_dbtp):
        if value is not None and not number(value):
            raise ValueError("Reference values must be finite")
    result = []

    def add(
        cid,
        category,
        title,
        statement,
        stype,
        ids,
        values,
        units,
        area,
        rule,
        *,
        limitations=(),
        validation="Deterministic rule; tested controls documented",
        reference_values=None,
        severity=None,
    ):
        ids = [i.replace("full_peaks", peak_key, 1) for i in ids]
        result.append(
            Conclusion(
                cid,
                category,
                title,
                statement,
                stype,
                ids,
                values,
                units,
                area if isinstance(area, dict) else {"status": "Unknown"},
                rule,
                "Only the stated measurement domain and coverage",
                validation,
                list(limitations),
                reference_values,
                ref.source if reference_values else None,
                severity,
            )
        )

    for rule in (loudness_rules, peak_rules, reference_rules):
        rule(info, scope, findings, ref, add)
    _integrity_conclusions(info, scope, findings, add)
    _origin_conclusions(findings, add)
    lossy_conclusions(findings, add)
    return result


__all__ = ["build_conclusions", "same_scope", "scope_text"]
