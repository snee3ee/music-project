import shutil
from dataclasses import dataclass

from music_project.core.models import AudioError


@dataclass(frozen=True)
class Settings:
    ffmpeg: str = "ffmpeg"
    ffprobe: str = "ffprobe"
    sacd_extract: str = "sacd_extract"
    fpcalc: str = "fpcalc"
    timeout: float = 300
    analysis_seconds: float = 30
    max_pcm_bytes: int = 128 * 1024 * 1024

    def require(self, name: str) -> str:
        candidate = getattr(self, name)
        resolved = shutil.which(candidate)
        if not resolved:
            raise AudioError(f"Backend unavailable: {name} ({candidate})")
        return resolved
