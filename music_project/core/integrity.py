import re
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath, PureWindowsPath

from music_project import METHOD_VERSION, __version__
from music_project.core.files import file_hash, signature, walk_files
from music_project.core.models import AudioError


def safe_relative(root: Path, name: str) -> Path:
    windows = PureWindowsPath(name)
    posix = PurePosixPath(name)
    if (
        not name
        or windows.drive
        or windows.is_absolute()
        or posix.is_absolute()
        or ".." in windows.parts
        or ".." in posix.parts
        or "\\" in name
        or ":" in name
        or "\0" in name
    ):
        raise AudioError(f"Небезопасный относительный путь: {name!r}")
    target = root.joinpath(*posix.parts).resolve()
    if not target.is_relative_to(root.resolve()) or target == root.resolve():
        raise AudioError("Путь выходит за корень архива")
    return target


def create_manifest(root: Path | str) -> dict:
    folder = Path(root).resolve(strict=True)
    entries = []
    for path in walk_files(folder, audio_only=False):
        before = signature(path)
        digest = file_hash(path)
        if before != signature(path):
            raise AudioError(f"Файл изменился во время хеширования: {path.name}")
        entries.append(
            {"path": path.relative_to(folder).as_posix(), "size": before[0], "sha256": digest}
        )
    return {
        "schema": "music-project-sha256-v1",
        "app_version": __version__,
        "method_version": METHOD_VERSION,
        "created_utc": datetime.now(UTC).isoformat(),
        "scope": "all regular files, excluding symlinks and junctions",
        "files": entries,
    }


def verify_manifest(root: Path | str, manifest: dict) -> list[dict]:
    folder = Path(root).resolve(strict=True)
    if (
        not isinstance(manifest, dict)
        or manifest.get("schema") != "music-project-sha256-v1"
        or not isinstance(manifest.get("files"), list)
    ):
        raise AudioError("Unsupported manifest schema")
    expected = {}
    for entry in manifest["files"]:
        if (
            not isinstance(entry, dict)
            or not isinstance(entry.get("path"), str)
            or not isinstance(entry.get("size"), int)
            or entry["size"] < 0
            or not isinstance(entry.get("sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", entry["sha256"])
        ):
            raise AudioError("Некорректная запись манифеста")
        target = safe_relative(folder, entry["path"])
        key = str(target).casefold()
        if key in expected:
            raise AudioError("Повторяющийся путь в манифесте")
        expected[key] = entry
    results = []
    seen = set()
    for path in walk_files(folder, audio_only=False):
        key = str(path.resolve()).casefold()
        seen.add(key)
        entry = expected.get(key)
        name = path.relative_to(folder).as_posix()
        if entry is None:
            results.append({"path": name, "status": "New"})
            continue
        try:
            before = signature(path)
            digest = file_hash(path)
            if before != signature(path):
                raise AudioError("Файл изменился во время проверки")
            status = (
                "Unchanged"
                if digest == entry["sha256"]
                else ("Modified" if before[0] != entry["size"] else "Hash mismatch")
            )
            results.append({"path": name, "status": status})
        except (OSError, AudioError) as exc:
            results.append({"path": name, "status": "Unreadable", "error": str(exc)})
    results.extend(
        {"path": e["path"], "status": "Missing"} for k, e in expected.items() if k not in seen
    )
    return results
