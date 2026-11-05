"""Portable origin investigation results; no UI dependencies or probability scores."""

from dataclasses import asdict, dataclass, field
from typing import Any

ORIGIN_VERSION = "origin-2026.11-v1"


@dataclass
class Hypothesis:
    code: str
    title: str
    status: str
    supporting_evidence: list[str]
    contradicting_evidence: list[str]
    measurement_ids: list[str]
    assumptions: list[str]
    alternatives: list[str]
    applicability: str


@dataclass
class OriginReport:
    status: str
    current_format: dict[str, Any]
    scope: dict[str, Any]
    measurement_chain: dict[str, Any]
    boundaries: list[dict[str, Any]] = field(default_factory=list)
    noise: dict[str, Any] = field(default_factory=dict)
    native: dict[str, Any] = field(default_factory=dict)
    hypotheses: list[Hypothesis] = field(default_factory=list)
    discoveries: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    method_version: str = ORIGIN_VERSION
    historical_source: str = "Unknown"
    independently_verified_identity: str = "Not established"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
