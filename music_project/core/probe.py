import json
import math
import re
from pathlib import Path

from music_project.core.config import Settings
from music_project.core.dsd_container import inspect_dsd
from music_project.core.duration import select_dsd_duration, with_duration
from music_project.core.models import AudioError, AudioInfo
from music_project.core.subprocess_utils import run

LOSSLESS = {"flac", "alac", "wavpack", "ape", "tta", "tak", "mlp", "truehd"}


def number(value, cast=float):
    try:
        result = cast(value)
        return result if math.isfinite(result) and result >= 0 else None
    except (ValueError, TypeError, OverflowError):
        return None


def probe(path: Path | str, settings: Settings = Settings()) -> AudioInfo:
    source = Path(path).resolve(strict=True)
    if not source.is_file():
        raise AudioError("Ожидался локальный файл")
    if source.suffix.lower() in {".cue", ".iso"}:
        raise AudioError("CUE/ISO требует специализированного обработчика")
    result = run(
        [
            settings.require("ffprobe"),
            "-v",
            "error",
            "-protocol_whitelist",
            "file,pipe",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(source),
        ],
        timeout=min(settings.timeout, 60),
    )
    try:
        raw = json.loads(result.text)
        streams = [s for s in raw.get("streams", []) if s.get("codec_type") == "audio"]
        if not streams:
            raise AudioError("Аудиопоток не найден")
        stream = streams[0]
        fmt = raw.get("format", {})
        codec = stream.get("codec_name", "unknown")
        dsd = codec.startswith("dsd_") or codec == "dst"
        rate = number(stream.get("sample_rate"), int) or 0
        # FFmpeg DSD decoder sample_rate counts packed bytes (8 DSD bits each).
        if dsd and codec.startswith("dsd_"):
            rate *= 8
        elif codec == "dst":
            rate = 0  # Backend stream rate has not been validated as native DST/DSD rate.
        bits = number(stream.get("bits_per_raw_sample"), int)
        bits = bits or number(stream.get("bits_per_sample"), int)
        integer_pcm = bool(re.match(r"pcm_[su]\d+", codec))
        # WavPack can be hybrid/lossy; ffprobe codec name alone does not establish mode.
        lossless = (codec in LOSSLESS - {"wavpack"}) or integer_pcm or codec.startswith("pcm_f")
        tags = {str(k).lower(): str(v) for k, v in fmt.get("tags", {}).items()}
        tags.update({str(k).lower(): str(v) for k, v in stream.get("tags", {}).items()})
        channels = number(stream.get("channels"), int) or 0
        layout = stream.get("channel_layout") or "Unknown"
        layout_source = "metadata" if layout != "Unknown" else "not provided"
        if layout == "Unknown" and channels == 1:
            layout, layout_source = "mono", "channel count"
        elif layout == "Unknown" and channels == 2 and fmt.get("format_name") in {"wav", "aiff"}:
            layout, layout_source = "stereo", "container convention"
        info = AudioInfo(
            str(source),
            fmt.get("format_name", "unknown"),
            codec,
            "DSD" if dsd else "PCM" if lossless else "Lossy/other",
            rate,
            channels,
            layout,
            bits if not dsd and lossless and (integer_pcm or codec in LOSSLESS) else None,
            number(stream.get("duration")) or number(fmt.get("duration")),
            source.stat().st_size,
            number(stream.get("bit_rate"), int) or number(fmt.get("bit_rate"), int),
            lossless and not dsd,
            tags,
            raw,
            layout_source,
        )
        if info.kind == "DSD":
            info = with_duration(info, select_dsd_duration(info, inspect_dsd(info)))
        return info
    except (ValueError, KeyError, TypeError) as exc:
        raise AudioError("Некорректный JSON ffprobe") from exc
