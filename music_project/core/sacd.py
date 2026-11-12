"""Local SACD ISO adapter: bounded structure checks and optional sacd_extract CLI.

Sector fields checked against upstream Scarlet Book reader; not a full disc verifier.
Only the supplied backend's observed print/selection protocol is supported.
"""

import re
import struct
import tempfile
from pathlib import Path

from music_project.core.config import Settings
from music_project.core.cue import cue_frames
from music_project.core.dsd_container import inspect_dsd
from music_project.core.models import AudioError
from music_project.core.probe import probe
from music_project.core.source_extract import ensure_track_space
from music_project.core.source_models import AudioSource, fingerprints
from music_project.core.subprocess_utils import run


def iso_structure(path: Path) -> dict:
    size = path.stat().st_size
    if size % 2048 or size < 511 * 2048:
        raise AudioError("Unsupported: ISO is not a readable 2048-byte-sector SACD image")
    with path.open("rb") as f:
        f.seek(510 * 2048)
        master = f.read(2048)
        if master[:8] != b"SACDMTOC" or master[8] != 1 or master[9] > 20:
            raise AudioError("Invalid/unsupported SACD master TOC")
        pointers = struct.unpack_from(">4I", master, 64)
        lengths = struct.unpack_from(">2H", master, 84)
        areas = []
        for index, (lsn, length) in enumerate(
            zip((pointers[0], pointers[2]), lengths, strict=True)
        ):
            if not lsn:
                continue
            if not 1 <= length <= 96 or lsn * 2048 + length * 2048 > size:
                raise AudioError("Invalid SACD area bounds")
            f.seek(lsn * 2048)
            header = f.read(2048)
            kind = "stereo" if index == 0 else "multichannel"
            if (
                header[:8] != (b"TWOCHTOC" if index == 0 else b"MULCHTOC")
                or header[8] != 1
                or header[9] > 20
            ):
                raise AudioError("Invalid SACD area TOC signature/version")
            first, last = struct.unpack_from(">2I", header, 72)
            if not 0 < first <= last < size // 2048 or not 1 <= header[69] <= 255:
                raise AudioError("Invalid SACD track-sector bounds/count")
            encoding = {0: "DST", 2: "DSD", 3: "DSD"}.get(header[21] & 15, "Unsupported")
            areas.append(
                {
                    "kind": kind,
                    "lsn": lsn,
                    "toc_sectors": length,
                    "channels": header[32],
                    "track_count": header[69],
                    "native_rate_hz": 2822400 if header[20] == 4 else None,
                    "encoding": encoding,
                    "frame_format": header[21] & 15,
                    "first_audio_sector": first,
                    "last_audio_sector": last,
                }
            )
    if not areas:
        raise AudioError("SACD has no readable supported audio areas")
    return {
        "status": "Passed",
        "sector_bytes": 2048,
        "areas": areas,
        "scope": "Master/primary area headers and bounds only; not every sector or audio packet",
    }


def backend_capabilities(settings=Settings()) -> dict:
    executable = str(Path(settings.require("sacd_extract")).resolve())
    with tempfile.TemporaryDirectory(prefix="music-project-sacd-help-") as work:
        result = run([executable, "--help"], cwd=work, timeout=min(15, settings.timeout))
    text = result.text
    needed = (
        "--print",
        "--select-track",
        "--output-dsf",
        "--convert-dst",
        "--input",
        "--2ch-tracks",
        "--mch-tracks",
    )
    if not all(s in text for s in needed):
        raise AudioError(
            "Unsupported sacd_extract CLI: required print/single-track/native DSF options absent"
        )
    output = "-y" if "--output-dir-conc" in text else "-o" if "--output-dir" in text else None
    if output is None:
        raise AudioError("Unsupported backend: no controlled output-directory option")
    return {
        "executable": executable,
        "output_option": output,
        "status": "Capabilities checked",
        "version": "Unverified until disc invocation",
        "help": text,
    }


def parse_listing(text: str) -> dict:
    metadata, areas = {}, []
    area = track = None
    section = ""
    for raw in text.splitlines():
        line = raw.strip()
        if line in {"Album Information:", "Disc Information:"}:
            section = line
        if match := re.fullmatch(r"Area Information \[(\d+)\]:", line):
            area = {"index": int(match[1]), "tracks": []}
            areas.append(area)
            track = None
        elif match := re.fullmatch(r"(Title|Artist):\s*(.*)", line):
            if area is None and section == "Album Information:":
                metadata[match[1].lower()] = match[2].strip()
        elif area is not None:
            if match := re.fullmatch(r"Track Count:\s*(\d+)", line):
                area["track_count"] = int(match[1])
            elif match := re.fullmatch(r"Speaker config:\s*(\d+) Channel", line):
                area["channels"] = int(match[1])
            elif match := re.fullmatch(r"Title\[(\d+)\]:\s*(.*)", line):
                track = {"number": int(match[1]) + 1, "title": match[2].strip()}
                area["tracks"].append(track)
            elif match := re.fullmatch(r"Performer\[(\d+)\]:\s*(.*)", line):
                if track and track["number"] == int(match[1]) + 1:
                    track["performer"] = match[2].strip()
            elif match := re.fullmatch(
                r"Track_Start_Time_Code:\s*(\d+:\d+:\d+)\s*\[mins:secs:frames\]", line
            ):
                if track is None or "start_75" in track:
                    track = {"number": len(area["tracks"]) + 1, "title": ""}
                    area["tracks"].append(track)
                track["start_75"] = cue_frames(match[1])
            elif match := re.fullmatch(r"Duration:\s*(\d+:\d+:\d+)\s*\[mins:secs:frames\]", line):
                if track is None:
                    raise AudioError("Invalid backend track context")
                track["duration_75"] = cue_frames(match[1])
    if not areas or len(areas) > 2:
        raise AudioError("Unsupported/empty sacd_extract listing")
    for a in areas:
        if len(a["tracks"]) != a.get("track_count") or a.get("channels") not in (2, 5, 6):
            raise AudioError("Incomplete/unsupported SACD track listing")
        stop = -1
        for n, t in enumerate(a["tracks"], 1):
            if (
                t["number"] != n
                or t.get("start_75", -1) < 0
                or t.get("start_75", -1) < stop
                or t.get("duration_75", 0) <= 0
            ):
                raise AudioError("Invalid/incomplete/overlapping SACD track times")
            stop = t["start_75"] + t["duration_75"]
    version = re.search(r"sacd_extract client\s+([^\r\n]+)", text)
    return {
        "metadata": metadata,
        "areas": areas,
        "backend_version": version[1] if version else "Unknown",
    }


def open_sacd(path: Path, settings=Settings()) -> dict:
    path = Path(path).resolve(strict=True)
    before = fingerprints([path])
    structure = iso_structure(path)
    capability = backend_capabilities(settings)
    command = [capability["executable"], "-P", "-i", str(path)]
    with tempfile.TemporaryDirectory(prefix="music-project-sacd-list-") as work:
        result = run(command, cwd=work, timeout=min(settings.timeout, 60))
    listing = parse_listing(result.text)
    if len(listing["areas"]) != len(structure["areas"]):
        raise AudioError("SACD area listing disagrees with primary structure")
    for area, native in zip(listing["areas"], structure["areas"], strict=True):
        if (area["channels"], area["track_count"]) != (native["channels"], native["track_count"]):
            raise AudioError("SACD track/channel listing disagrees with area header")
        area.update(native)
        for t in area["tracks"]:
            t.update(
                status="Ready"
                if native["native_rate_hz"] and native["encoding"] in {"DSD", "DST"}
                else "Unsupported",
                duration_seconds=t["duration_75"] / 75,
                start_seconds=t["start_75"] / 75,
            )
            t["source"] = AudioSource(
                "sacd",
                str(path),
                str(path),
                t["number"],
                t.get("title") or f"Track {t['number']}",
                t.get("performer", listing["metadata"].get("artist", "")),
                t["start_75"],
                t["start_75"] + t["duration_75"],
                t["duration_seconds"],
                native["kind"],
                before,
            ).to_dict()
    if before != fingerprints([path]):
        raise AudioError("ISO changed during enumeration")
    return {
        "path": str(path),
        **listing,
        "structure": structure,
        "command": command,
        "diagnostics": result.stderr,
        "backend": capability["executable"],
        "validation": "Track metadata enumerated; decoding is a separate selected-track action",
    }


def extract_track(source: AudioSource, folder: Path, settings=Settings(), *, cancelled=None):
    source.verify()
    if any(folder.iterdir()):
        raise AudioError("Extraction requires an empty controlled temporary directory")
    listing = open_sacd(Path(source.audio_path), settings)
    area = next((a for a in listing["areas"] if a["kind"] == source.area), None)
    if area is None or not 1 <= source.track <= len(area["tracks"]):
        raise AudioError("SACD selected track/area unavailable")
    t = area["tracks"][source.track - 1]
    if t["source"] != source.to_dict():
        raise AudioError("SACD selection changed; reopen source")
    ensure_track_space(
        folder,
        round(source.duration_seconds * area["native_rate_hz"] * area["channels"] / 8) + 65536,
        settings,
    )
    capability = backend_capabilities(settings)
    command = [
        capability["executable"],
        "-m" if source.area == "multichannel" else "-2",
        "-s",
        "-c",
        "-t",
        str(source.track),
        "-i",
        source.audio_path,
        capability["output_option"],
        str(folder),
    ]
    result = run(command, cwd=folder, timeout=settings.timeout, cancelled=cancelled)
    files = []
    for p in folder.rglob("*"):
        if not p.resolve().is_relative_to(folder.resolve()) or p.is_symlink() or p.is_junction():
            raise AudioError("Unsafe extractor output")
        if p.is_file() and p.suffix.lower() == ".dsf":
            files.append(p)
    if len(files) != 1:
        raise AudioError(f"Expected one extracted DSF; obtained {len(files)}")
    info = probe(files[0], settings)
    structure = inspect_dsd(info)
    if (
        structure.status != "Passed"
        or info.kind != "DSD"
        or structure.compression != "DSD"
        or (info.sample_rate, info.channels) != (area["native_rate_hz"], area["channels"])
    ):
        raise AudioError("Extracted native DSD representation disagrees with SACD area")
    if (
        info.duration is None
        or abs(info.duration - source.duration_seconds) > 1 / 75 + 1 / info.sample_rate
    ):
        raise AudioError("Extractor duration differs from selected SACD TOC track")
    source.verify()
    return files[0], {
        "method": "Selected track only; sacd_extract native DSF output; DST decompression requested, no PCM conversion",
        "command": command,
        "backend_version": listing["backend_version"],
        "source_encoding": area["encoding"],
        "dst_decode_status": "Not applicable"
        if area["encoding"] == "DSD"
        else "Backend decompression executed; native DSF structure validated, no reference-bitstream identity check",
        "native_output_codec": info.codec,
        "temporary_bytes": files[0].stat().st_size,
        "stdout": result.text[-65536:],
        "stderr": result.stderr,
    }
