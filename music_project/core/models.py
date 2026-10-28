from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from music_project import METHOD_VERSION, __version__


class AudioError(Exception):
    """Expected input/backend failure safe to display without a traceback."""


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

    @property
    def name(self) -> str:
        return Path(self.path).name


@dataclass
class Finding:
    status: str
    summary: str
    measurements: dict[str, Any] = field(default_factory=dict)
    method: str = ""
    limitations: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    method_version: str = METHOD_VERSION


@dataclass
class Analysis:
    info: AudioInfo
    scope: dict[str, Any]
    findings: dict[str, Finding]
    backends: dict[str, str]
    app_version: str = __version__
    method_version: str = METHOD_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
