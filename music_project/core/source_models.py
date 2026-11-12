"""Immutable logical sources and cheap, explicit cache fingerprints."""

import math
from dataclasses import asdict, dataclass
from pathlib import Path

from music_project.core.files import signature
from music_project.core.models import AudioError

SOURCE_VERSION = "logical-source-2026.11-v1"


def fingerprints(paths) -> tuple[tuple[str, int, int], ...]:
    return tuple(
        (str(p.resolve(strict=True)), *signature(p)) for p in dict.fromkeys(map(Path, paths))
    )


@dataclass(frozen=True)
class AudioSource:
    kind: str
    origin: str
    audio_path: str
    track: int
    title: str
    performer: str
    start_75: int
    end_75: int | None
    duration_seconds: float
    area: str = ""
    fingerprints: tuple[tuple[str, int, int], ...] = ()
    method_version: str = SOURCE_VERSION

    def verify(self):
        if (
            not self.fingerprints
            or not math.isfinite(self.duration_seconds)
            or self.duration_seconds <= 0
            or self.start_75 < 0
            or self.end_75 is not None
            and self.end_75 <= self.start_75
        ):
            raise AudioError("Invalid logical source or unknown track duration")
        recorded = {p for p, _size, _mtime in self.fingerprints}
        if (
            str(Path(self.audio_path).resolve()) not in recorded
            or str(Path(self.origin).resolve()) not in recorded
        ):
            raise AudioError("Logical source paths are not covered by its fingerprint")
        for name, size, mtime in self.fingerprints:
            if signature(Path(name)) != (size, mtime):
                raise AudioError("Источник изменился; откройте альбом повторно")

    def to_dict(self):
        return asdict(self)
