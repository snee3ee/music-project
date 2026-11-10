"""Portable scope, reference and conclusion contracts; no UI or model-generated text."""

from dataclasses import asdict, dataclass, field
from typing import Any

CONCLUSIONS_VERSION = "conclusions-2026.11-v1"
TECHNICAL_VERSION = "technical-pcm-2026.11-v1"


@dataclass(frozen=True)
class MeasurementScope:
    start_seconds: float
    end_seconds: float
    analyzed_seconds: float
    total_seconds: float | None
    complete_file: bool
    frames: int
    sample_rate_hz: int
    channels: int
    domain: str = "PCM"
    processing: str = "Native rate/channel order, decoded float64; no gain"
    ranges: list[dict[str, float]] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class ReferenceProfile:
    name: str = "No reference"
    loudness_lufs: float | None = None
    peak_ceiling_dbtp: float | None = None
    source: str = "Custom user-selected reference"


@dataclass(frozen=True)
class Conclusion:
    conclusion_id: str
    category: str
    title: str
    statement: str
    statement_type: str
    measurement_ids: list[str]
    measured_values: dict[str, Any]
    measurement_units: dict[str, str]
    analysis_scope: dict[str, Any]
    rule_id: str
    applicability: str
    validation_status: str
    limitations: list[str] = field(default_factory=list)
    reference_value: dict[str, float] | None = None
    reference_source: str | None = None
    severity: str | None = None
    suggested_next_action: str | None = None
    rule_version: str = CONCLUSIONS_VERSION
