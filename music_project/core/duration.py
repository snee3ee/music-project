"""Sourced DSF/DFF duration selection, separate from backend bitrate estimates."""

import math
from dataclasses import asdict, dataclass, replace

from music_project.core.dsd_container import DSDContainer
from music_project.core.models import AudioInfo

DURATION_POLICY_VERSION = "dsd-duration-2026.11-v1"


@dataclass(frozen=True)
class DurationSelection:
    seconds: float | None
    source: str
    status: str
    ffprobe_seconds: float | None
    container_seconds: float | None
    decoded_seconds: float | None = None
    full_decode_reached_eof: bool = False
    decode_status: str = "Not run"
    rounding_tolerance_seconds: float | None = None
    padding_tolerance_seconds: float = 0
    ffprobe_minus_container_seconds: float | None = None
    decoded_minus_container_seconds: float | None = None
    consistency: str = "Not checked"
    policy_version: str = DURATION_POLICY_VERSION


def ffprobe_duration(info: AudioInfo) -> float | None:
    """Legacy records used AudioInfo.duration for the unqualified ffprobe value."""
    if info.ffprobe_duration is not None:
        return info.ffprobe_duration
    return info.duration if info.duration_source == "ffprobe" else None


def select_dsd_duration(
    info: AudioInfo,
    structure: DSDContainer,
    *,
    decoded_seconds: float | None = None,
    full_decode_reached_eof: bool = False,
    decode_status: str = "Not run",
    pcm_rate: int | None = None,
) -> DurationSelection:
    estimate = ffprobe_duration(info)
    header = structure.duration if structure.status == "Passed" else None
    source = (
        "DSF sample count / native rate"
        if structure.container == "DSF"
        else (
            "DFF payload length / channels / native rate"
            if structure.container == "DFF"
            else "Unknown"
        )
    )
    status = (
        "Derived"
        if header is not None
        else ("Unsupported" if structure.status == "Unsupported" else "Unknown")
    )
    seconds = header
    rounding = 2 / pcm_rate if pcm_rate and pcm_rate > 0 else None
    invalid_decoded = decoded_seconds is not None and (
        not math.isfinite(decoded_seconds) or decoded_seconds < 0
    )
    if invalid_decoded:
        decoded_seconds = None
    difference = (
        decoded_seconds - header
        if full_decode_reached_eof and decoded_seconds is not None and header is not None
        else None
    )
    consistency = "Not checked"
    if (
        full_decode_reached_eof
        and header is not None
        and (decoded_seconds is not None or invalid_decoded)
        and rounding is not None
    ):
        compatible = not invalid_decoded and (
            -rounding <= difference <= rounding + structure.padding_tolerance_seconds
        )
        consistency = "Passed" if compatible else "Failed"
        if compatible and decode_status == "Passed":
            status = "Verified"
        elif not compatible:
            seconds, status = None, "Ambiguous"
    return DurationSelection(
        seconds=seconds,
        source=source if header is not None else "Unknown",
        status=status,
        ffprobe_seconds=estimate,
        container_seconds=header,
        decoded_seconds=decoded_seconds,
        full_decode_reached_eof=full_decode_reached_eof,
        decode_status=decode_status,
        rounding_tolerance_seconds=rounding,
        padding_tolerance_seconds=structure.padding_tolerance_seconds,
        ffprobe_minus_container_seconds=estimate - header
        if estimate is not None and header is not None
        else None,
        decoded_minus_container_seconds=difference,
        consistency=consistency,
    )


def with_duration(info: AudioInfo, selection: DurationSelection) -> AudioInfo:
    return replace(
        info,
        duration=selection.seconds,
        duration_source=selection.source,
        duration_status=selection.status,
        ffprobe_duration=selection.ffprobe_seconds,
        duration_details=asdict(selection),
    )
