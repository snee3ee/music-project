"""Bounded CUE parsing and independently probed, authorized audio references."""

import codecs
import re
import unicodedata
from pathlib import Path, PureWindowsPath

from music_project.core.config import Settings
from music_project.core.models import AudioError
from music_project.core.probe import probe
from music_project.core.source_models import AudioSource, fingerprints


def cue_frames(value: str) -> int:
    if not re.fullmatch(r"\d{1,4}:\d{2}:\d{2}", value):
        raise AudioError("Invalid MM:SS:FF timestamp")
    m, s, f = map(int, value.split(":"))
    if s >= 60 or f >= 75:
        raise AudioError("Invalid CUE second/frame field")
    return (m * 60 + s) * 75 + f


def resolve_reference(cue: Path, name: str, authorized_roots=()) -> dict:
    if not name or "\0" in name or any(c in name for c in '*?<>|"'):
        return {"status": "Invalid", "valid": False, "exists": False}
    win = PureWindowsPath(name)
    if ":" in name and not win.drive or any(":" in part for part in win.parts[1:]):
        return {"status": "Invalid", "valid": False, "exists": False}
    parent = cue.parent.resolve()
    if any(not Path(p).is_absolute() for p in authorized_roots):
        raise AudioError("External CUE authorization requires absolute directory paths")
    target = Path(name.replace("\\", "/"))
    requested_name = target.name
    if win.drive and not target.is_absolute():
        return {"status": "Authorization required", "valid": False, "exists": False}
    target = (parent / target).resolve()
    roots = [parent, *(Path(p).resolve() for p in authorized_roots)]
    if not any(target.is_relative_to(p) for p in roots):
        return {"status": "Authorization required", "valid": False, "exists": False}
    # Exact spelling first. Fallback only to a unique normalized case match, never
    # to an extension or album-name guess. Do not scan outside authorized roots.
    if target.parent.is_dir():

        def norm(s):
            return unicodedata.normalize("NFC", s).casefold()

        matches = [p for p in target.parent.iterdir() if norm(p.name) == norm(requested_name)]
        exact = [p for p in matches if p.name == requested_name]
        if exact:
            matches = exact
        if len(matches) > 1:
            return {"status": "Ambiguous", "valid": False, "exists": False}
        if matches:
            target = matches[0].resolve()
    if not any(target.is_relative_to(p) for p in roots):
        return {"status": "Authorization required", "valid": False, "exists": False}
    exists = target.is_file()
    return {
        "status": "Resolved" if exists else "Missing",
        "valid": True,
        "exists": exists,
        "path": str(target),
    }


def parse_cue(path: Path, *, encoding=None, authorized_roots=()) -> dict:
    path = Path(path).resolve(strict=True)
    if path.stat().st_size > 2 * 1024 * 1024:
        raise AudioError("CUE превышает лимит 2 MiB")
    data = path.read_bytes()
    if encoding:
        used = encoding
    elif data.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        used = "utf-16"
    else:
        used = "utf-8-sig"
    try:
        text = data.decode(used)
    except LookupError as exc:
        raise AudioError("Unsupported CUE encoding") from exc
    except UnicodeDecodeError:
        if encoding:
            raise AudioError("CUE cannot be decoded using the selected encoding") from None
        used = "cp1251"
        try:
            text = data.decode(used)
        except UnicodeDecodeError as exc:
            raise AudioError(
                "CUE encoding is unresolved; select an explicit supported encoding"
            ) from exc
    result = {
        "path": str(path),
        "encoding": used,
        "metadata": {},
        "files": [],
        "tracks": [],
        "issues": [],
        "diagnostics": [],
        "encoding_note": "cp1251 fallback; verify metadata"
        if used == "cp1251"
        else "Explicit/BOM/UTF-8",
        "boundary_policy": "INDEX01 to next INDEX01 in the same FILE; INDEX00 pregap belongs to preceding interval; initial pregap excluded",
    }
    current_file = track = None
    blocking_global = False

    def issue(code, line, message, status="Invalid", blocking=True):
        nonlocal blocking_global
        result["issues"].append(message)
        result["diagnostics"].append(
            {
                "code": code,
                "line": line,
                "status": status,
                "message": message,
                "track": track["number"] if track else None,
            }
        )
        if track is not None and blocking:
            track["status"] = status
        elif track is None and blocking and code != "reference":
            blocking_global = True

    for line_number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or re.match(r"REM(?:\s|$)", line, re.I):
            continue
        if match := re.fullmatch(r'FILE\s+(?:"([^"]+)"|(\S+))\s+(\S+)', line, re.I):
            if len(result["files"]) >= 99:
                raise AudioError("CUE FILE limit exceeded (99)")
            name = match[1] or match[2]
            resolved = resolve_reference(path, name, authorized_roots)
            current_file = len(result["files"])
            track = None
            result["files"].append({"reference": name, "declaration": match[3], **resolved})
            if resolved["status"] != "Resolved":
                issue(
                    "reference",
                    line_number,
                    f"FILE line {line_number}: {resolved['status']}: {name}",
                    resolved["status"],
                )
        elif match := re.fullmatch(r"TRACK\s+(\d+)\s+(\S+)", line, re.I):
            if len(result["tracks"]) >= 99:
                raise AudioError("CUE TRACK limit exceeded (99)")
            track = {
                "number": int(match[1]),
                "file_index": current_file,
                "file": result["files"][current_file]["reference"]
                if current_file is not None
                else None,
                "indexes": {},
                "status": "Parsed",
                "mode": match[2].upper(),
            }
            result["tracks"].append(track)
            if match[2].upper() != "AUDIO" or not 1 <= track["number"] <= 99:
                issue(
                    "track-mode",
                    line_number,
                    f"TRACK line {line_number}: unsupported mode/number",
                    "Unsupported",
                )
            if current_file is None:
                issue("missing-file", line_number, f"TRACK line {line_number}: unresolved FILE")
        elif match := re.fullmatch(r"INDEX\s+(\d{2})\s+(\S+)", line, re.I):
            try:
                if track is None or match[1] in track["indexes"]:
                    raise AudioError("Invalid INDEX context/duplicate")
                track["indexes"][match[1]] = cue_frames(match[2])
                if match[1] not in {"00", "01"}:
                    issue(
                        "extra-index",
                        line_number,
                        "Additional INDEX retained; no subtrack selection",
                        "Unsupported",
                        False,
                    )
            except AudioError as exc:
                issue("index", line_number, f"INDEX line {line_number}: {exc}")
        elif match := re.fullmatch(r'(TITLE|PERFORMER)\s+(?:"(.*)"|(\S+))', line, re.I):
            (track if track is not None else result["metadata"])[match[1].lower()] = (
                match[2] if match[2] is not None else match[3]
            ).strip()
        else:
            directive = line.split()[0].upper()
            if directive == "FILE":
                current_file = track = None
            issue(
                "unsupported",
                line_number,
                f"Line {line_number}: unsupported {directive}",
                "Unsupported",
                directive not in {"FLAGS", "ISRC", "CATALOG", "CDTEXTFILE"},
            )
    previous, numbers = {}, set()
    for t in result["tracks"]:
        track = t
        if blocking_global:
            t["status"] = "Unsupported"
        start = t["indexes"].get("01")
        if start is None:
            issue("missing-index", None, f"Track {t['number']}: missing INDEX 01")
        elif start <= previous.get(t["file"], -1):
            issue("order", None, f"Track {t['number']}: non-increasing INDEX 01")
        else:
            previous[t["file"]] = start
        if t["number"] in numbers or numbers and t["number"] <= max(numbers):
            issue("track-order", None, f"Duplicate/non-increasing track number {t['number']}")
        numbers.add(t["number"])
        if t["indexes"].get("00", 0) > (start if start is not None else 0):
            issue("pregap", None, f"Track {t['number']}: INDEX 00 after INDEX 01")
    if not result["tracks"]:
        issue("no-tracks", None, "No AUDIO tracks")
    result["scope"] = (
        "CUE declarations and resolved paths; audio format/bounds require independent probe"
    )
    return result


def open_cue(path: Path, settings=Settings(), *, encoding=None, authorized_roots=()) -> dict:
    result = parse_cue(path, encoding=encoding, authorized_roots=authorized_roots)
    infos = {}
    for i, f in enumerate(result["files"]):
        if f["status"] != "Resolved":
            continue
        try:
            info = probe(f["path"], settings)
            f["audio"] = {
                "container": info.container,
                "codec": info.codec,
                "kind": info.kind,
                "rate": info.sample_rate,
                "channels": info.channels,
                "duration": info.duration,
            }
            infos[i] = info
        except (AudioError, OSError) as exc:
            f.update(status="Unsupported", error=str(exc))
    seen = {}
    for i, f in enumerate(result["files"]):
        key = str(Path(f["path"]).resolve()).casefold() if f.get("exists") else None
        if key in seen:
            prior = seen[key]
            for index in (prior, i):
                infos.pop(index, None)
                result["files"][index].update(
                    status="Ambiguous",
                    error="Repeated FILE resolves to the same audio; overlapping album coverage is not guessed",
                )
        elif key is not None:
            seen[key] = i
    for position, t in enumerate(result["tracks"]):
        t["performer"] = t.get("performer", result["metadata"].get("performer", ""))
        info = infos.get(t["file_index"])
        if t["status"] != "Parsed" or info is None:
            if t["status"] == "Parsed":
                t["status"] = (
                    result["files"][t["file_index"]]["status"]
                    if t["file_index"] is not None
                    else "Invalid"
                )
            continue
        if (
            info.codec == "dst"
            or info.kind == "DSD"
            and info.channels not in (1, 2)
            or info.kind != "DSD"
            and not info.lossless
        ):
            t.update(
                status="Unsupported",
                error="CUE track extraction supports lossless PCM or mono/stereo uncompressed native DSD; DFF DST not validated",
            )
            continue
        start = t["indexes"]["01"]
        next_track = (
            result["tracks"][position + 1] if position + 1 < len(result["tracks"]) else None
        )
        end = (
            next_track["indexes"].get("01")
            if next_track and next_track["file_index"] == t["file_index"]
            else None
        )
        if next_track and next_track["file_index"] == t["file_index"] and end is None:
            t.update(status="Invalid", error="Next track has no valid INDEX01; end not guessed")
            continue
        stop = end / 75 if end is not None else info.duration
        if (
            stop is None
            or info.duration is None
            or not 0 <= start / 75 < stop <= info.duration + 1e-7
        ):
            t.update(status="Invalid", error="Unknown/out-of-source/non-increasing boundary")
            continue
        t.update(
            status="Ready",
            start_seconds=start / 75,
            end_seconds=stop,
            duration_seconds=stop - start / 75,
            pregap_seconds=(start - t["indexes"].get("00", start)) / 75,
        )
        t["source"] = AudioSource(
            "cue",
            result["path"],
            info.path,
            t["number"],
            t.get("title", f"Track {t['number']}"),
            t["performer"],
            start,
            end,
            t["duration_seconds"],
            fingerprints=fingerprints([path, info.path]),
        ).to_dict()
    return result


def track_source(track: dict) -> AudioSource:
    if track.get("status") != "Ready":
        raise AudioError("Дорожка недоступна: " + track.get("status", "Unknown"))
    values = dict(track["source"])
    values["fingerprints"] = tuple(tuple(x) for x in values["fingerprints"])
    return AudioSource(**values)
