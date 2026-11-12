"""Lossy investigation contracts: measurements never authenticate encoding history."""

from dataclasses import asdict, dataclass, field
from typing import Literal

LOSSY_VERSION = "lossy-investigation-2026.11-v1"
LossyClassification = Literal[
    "Indicators detected", "No evaluated indicators detected", "Inconclusive", "Not evaluated"
]


@dataclass
class LossyReport:
    classification: LossyClassification = "Not evaluated"
    performed: bool = False
    reason: str = ""
    scope: dict = field(default_factory=dict)
    parameters: dict = field(default_factory=dict)
    windows: list[dict] = field(default_factory=list)
    bands: list[dict] = field(default_factory=list)
    candidates: list[dict] = field(default_factory=list)
    spectrum: dict = field(default_factory=dict)
    counts: dict = field(default_factory=dict)
    additional_indicators: list[dict] = field(default_factory=list)
    historical_codec: str = "Unknown"
    source_authenticity: str = "Not established"
    method_version: str = LOSSY_VERSION
    limitations: list[str] = field(
        default_factory=lambda: [
            "Cutoff and spectral suppression also result from non-lossy filtering and bandwidth-limited signals.",
            "High-bitrate coding, noise, EQ and resampling may erase or weaken the evaluated observations.",
            "Synthetic validation does not establish real-music detection accuracy or historical authenticity.",
        ]
    )

    def to_dict(self):
        return asdict(self)
