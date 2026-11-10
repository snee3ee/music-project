import hashlib
import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path

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
    dsd_mode: str = "quick"
    dsd_pcm_rate: int = 352800
    origin_cache_dir: str = "data/origin-calibration"
    near_ceiling_dbfs: float = -1.0
    technical_mode: str = "full"

    def require(self, name: str) -> str:
        candidate = getattr(self, name)
        resolved = shutil.which(candidate)
        if not resolved:
            raise AudioError(f"Backend unavailable: {name} ({candidate})")
        return resolved


def backend_identity(settings: Settings) -> str:
    """Settings and executable path/size/mtime identity, without launching decoders."""
    identities = {}
    for name in ("ffmpeg", "ffprobe", "sacd_extract", "fpcalc"):
        try:
            path = Path(settings.require(name))
            stat = path.stat()
            identities[name] = (str(path), stat.st_size, stat.st_mtime_ns)
        except (AudioError, OSError) as exc:
            identities[name] = str(exc)
    value = {"settings": asdict(settings), "executables": identities}
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
