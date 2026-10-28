import re
from pathlib import Path, PureWindowsPath

from music_project.core.config import Settings
from music_project.core.models import AudioError


def parse_cue(path: Path) -> dict:
    if path.stat().st_size > 2 * 1024 * 1024:
        raise AudioError("CUE превышает лимит 2 MiB")
    data = path.read_bytes()
    try:
        text = data.decode("utf-8-sig")
        encoding = "utf-8"
    except UnicodeDecodeError:
        text = data.decode("cp1251")
        encoding = "cp1251 (fallback; verify metadata)"
    result = {"encoding": encoding, "metadata": {}, "files": [], "tracks": [], "issues": []}
    current_file = None
    track = None
    for line_number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if match := re.fullmatch(r'FILE\s+(?:"([^"]+)"|(\S+))\s+\S+', line, re.I):
            name = match[1] or match[2]
            win = PureWindowsPath(name)
            normalized = name.replace("\\", "/")
            # Reject absolute/UNC/drive references before any filesystem resolution.
            valid = not (
                win.drive
                or win.is_absolute()
                or ".." in win.parts
                or name.startswith(("/", "\\"))
                or ":" in name
                or "\0" in name
            )
            target = (path.parent / normalized).resolve() if valid else path.parent
            valid = valid and target.is_relative_to(path.parent.resolve())
            current_file = normalized if valid else None
            track = None
            result["files"].append(
                {"reference": name, "valid": valid, "exists": valid and target.is_file()}
            )
            if not valid or not target.is_file():
                result["issues"].append(
                    f"FILE line {line_number}: invalid/missing reference {name}"
                )
        elif match := re.fullmatch(r"TRACK\s+(\d+)\s+AUDIO", line, re.I):
            track = {"number": int(match[1]), "file": current_file, "indexes": {}}
            result["tracks"].append(track)
            if not current_file:
                result["issues"].append(f"TRACK line {line_number}: unresolved FILE")
        elif match := re.fullmatch(r"INDEX\s+(\d+)\s+(\d+):(\d+):(\d+)", line, re.I):
            minute, second, frame = map(int, match.group(2, 3, 4))
            if not track or second >= 60 or frame >= 75:
                result["issues"].append(f"INDEX line {line_number}: invalid timestamp/context")
            else:
                track["indexes"][match[1]] = (minute * 60 + second) * 75 + frame
        elif match := re.fullmatch(r'(TITLE|PERFORMER)\s+"(.*)"', line, re.I):
            (track if track is not None else result["metadata"])[match[1].lower()] = match[2]
    previous = {}
    numbers = set()
    for track in result["tracks"]:
        start = track["indexes"].get("01")
        if start is None:
            result["issues"].append(f"Track {track['number']}: missing INDEX 01")
        elif start <= previous.get(track["file"], -1):
            result["issues"].append(f"Track {track['number']}: non-increasing INDEX 01")
        else:
            previous[track["file"]] = start
        if track["number"] in numbers:
            result["issues"].append(f"Duplicate track number {track['number']}")
        numbers.add(track["number"])
        if "00" in track["indexes"] and start is not None and track["indexes"]["00"] > start:
            result["issues"].append(f"Track {track['number']}: INDEX 00 after INDEX 01")
    if not result["tracks"]:
        result["issues"].append("No AUDIO tracks")
    result["scope"] = "CUE metadata/boundaries only; timestamps in 1/75 s; no audio decoding"
    return result


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
