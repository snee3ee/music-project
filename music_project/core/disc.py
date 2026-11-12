from pathlib import Path

from music_project.core.config import Settings
from music_project.core.cue import parse_cue as parse_cue
from music_project.core.models import AudioError


def inspect_iso(path: Path, settings: Settings = Settings()) -> dict:
    with path.open("rb") as stream:
        stream.seek(510 * 2048)
        sacd = stream.read(8) == b"SACDMTOC"
        stream.seek(16 * 2048 + 1)
        iso9660 = stream.read(5) == b"CD001"
    try:
        backend = settings.require("sacd_extract")
    except AudioError as exc:
        backend = str(exc)
    return {
        "type": "SACD signature detected"
        if sacd
        else "ISO9660; SACD not established"
        if iso9660
        else "Unknown disc image",
        "backend": backend,
        "size": path.stat().st_size,
        "limitations": "Signature only; raw-sector images, encryption and TOC validity unverified."
        " Track/area listing requires a validated sacd_extract backend.",
    }


def sacd_command(
    source: Path,
    output: Path,
    tracks: list[int],
    *,
    multichannel: bool = False,
    settings: Settings = Settings(),
) -> list[str]:
    """Command plan only. Execution intentionally deferred pending backend validation."""
    if not tracks or any(type(t) is not int or not 1 <= t <= 255 for t in tracks):
        raise AudioError("SACD track numbers must be 1..255")
    source = source.resolve(strict=True)
    if inspect_iso(source, settings)["type"] != "SACD signature detected":
        raise AudioError("SACD signature not detected")
    if output.resolve() == source.parent:
        raise AudioError("Extraction requires a separate controlled output directory")
    return [
        settings.require("sacd_extract"),
        "-m" if multichannel else "-2",
        "-s",
        "-c",
        "-t",
        ",".join(map(str, sorted(set(tracks)))),
        "-i",
        str(source),
        "-o",
        str(output),
    ]
