from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from music_project import METHOD_VERSION, __version__
from music_project.core.conclusion_models import Conclusion


class AudioError(Exception):
    """Expected input/backend failure safe to display without a traceback."""


class DecoderError(AudioError):
    """Retain bounded backend diagnostics separately from the fatal outcome."""

    def __init__(self, message: str, diagnostics: str):
        super().__init__(message)
        self.diagnostics = diagnostics


@dataclass(frozen=True)
class AudioInfo:
    path: str
    container: str
    codec: str
    kind: str
    sample_rate: int
    channels: int
    channel_layout: str
    bit_depth: int | None
    duration: float | None
    size: int
    bitrate: int | None
    lossless: bool
    tags: dict[str, str] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)
    channel_layout_source: str = "metadata"
    ffprobe_duration: float | None = None
    duration_source: str = "ffprobe"
    duration_status: str = "Unknown"
    duration_details: dict[str, Any] = field(default_factory=dict)

    @property
    def name(self) -> str:
        return Path(self.path).name


@dataclass
class Observation:
    """A scoped signal observation, separate from a historical inference."""

    code: str
    status: str
    summary: str
    value: float | int | None = None
    unit: str = ""


@dataclass
class Finding:
    status: str
    summary: str
    measurements: dict[str, Any] = field(default_factory=dict)
    method: str = ""
    limitations: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    method_version: str = METHOD_VERSION
    observations: list[Observation] = field(default_factory=list)


@dataclass
class Analysis:
    info: AudioInfo
    scope: dict[str, Any]
    findings: dict[str, Finding]
    backends: dict[str, str]
    app_version: str = __version__
    method_version: str = METHOD_VERSION
    conclusions: list[Conclusion] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
