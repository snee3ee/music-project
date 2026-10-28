import json
import sqlite3
from collections import Counter, defaultdict
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from music_project import METHOD_VERSION
from music_project.core.config import Settings
from music_project.core.decoder import canonical_hash, verify_decode
from music_project.core.files import file_hash, signature, walk_files
from music_project.core.models import AudioError
from music_project.core.probe import probe


class Library:
    def __init__(self, database: Path | str):
        self.path = Path(database)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1):
                raise AudioError(f"Unsupported database schema version: {version}")
            db.execute("""CREATE TABLE IF NOT EXISTS files (
                root TEXT NOT NULL, path TEXT NOT NULL, size INTEGER, mtime_ns INTEGER,
                status TEXT NOT NULL, payload TEXT NOT NULL, scanned TEXT NOT NULL,
                method TEXT NOT NULL, PRIMARY KEY(root,path))""")
            db.execute("PRAGMA user_version=1")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def records(self, root: str | None = None, include_removed: bool = False) -> list[dict]:
        query = "SELECT * FROM files WHERE 1=1"
        args = []
        if root:
            query += " AND root=?"
            args.append(str(Path(root).resolve()))
        if not include_removed:
            query += " AND status!='Removed'"
        with self.connect() as db:
            rows = db.execute(query + " ORDER BY path", args).fetchall()
        return [{**dict(row), **json.loads(row["payload"])} for row in rows]

    def scan(
        self,
        root: Path | str,
        settings: Settings = Settings(),
        *,
        audio_hash: bool = True,
        force: bool = False,
        progress: Callable[[int, str], None] | None = None,
        cancelled: Callable[[], bool] | None = None,
    ) -> dict:
        folder = Path(root).resolve(strict=True)
        old = {r["path"]: r for r in self.records(str(folder), include_removed=True)}
        seen = set()
        counts = Counter(new=0, modified=0, unchanged=0, removed=0, errors=0)
        now = datetime.now(UTC).isoformat()
        for path in walk_files(folder):
            if cancelled and cancelled():
                return {**counts, "cancelled": True}
            key = str(path)
            seen.add(key)
            if progress:
                progress(len(seen), key)
            previous = old.get(key)
            payload = {"hash_requested": audio_hash}
            try:
                before = signature(path)
                if (
                    not force
                    and previous
                    and previous["status"] != "Removed"
                    and (previous["size"], previous["mtime_ns"]) == before
                    and previous["method"] == METHOD_VERSION
                    and previous.get("hash_requested") == audio_hash
                ):
                    counts["unchanged"] += 1
                    continue
                payload = {"sha256": file_hash(path), "hash_requested": audio_hash}
                if path.suffix.lower() == ".cue":
                    from music_project.core.disc import parse_cue

                    payload["cue"] = parse_cue(path)
                    if payload["cue"]["issues"]:
                        raise AudioError("; ".join(payload["cue"]["issues"]))
                elif path.suffix.lower() == ".iso":
                    from music_project.core.disc import inspect_iso

                    payload["disc"] = inspect_iso(path, settings)
                else:
                    info = probe(path, settings)
                    payload["info"] = asdict(info)
                    if audio_hash and info.lossless and info.bit_depth in (8, 16, 24, 32):
                        try:
                            payload["pcm_sha256"] = canonical_hash(info, settings)
                        except AudioError as exc:
                            if not str(exc).startswith(("Not applicable", "Unsupported")):
                                raise
                            payload["pcm_hash_status"] = str(exc)
                            verify_decode(info, settings)
                    else:
                        verify_decode(info, settings)
                    payload["integrity"] = "Full decode completed"
                if signature(path) != before:
                    raise AudioError("Файл изменился во время сканирования; повторите проверку")
                status = "Indexed"
            except (AudioError, OSError, ValueError) as exc:
                # A decoder failure does not invalidate a completed file-byte hash.
                payload.pop("pcm_sha256", None)
                payload.update({"error": str(exc), "hash_requested": audio_hash})
                status = "Unreadable/unsupported"
                counts["errors"] += 1
                try:
                    after = signature(path)
                    if payload.get("sha256") and before != after:
                        payload.pop("sha256", None)
                    before = after
                except OSError:
                    before = (0, 0)
            counts["modified" if previous and previous["status"] != "Removed" else "new"] += 1
            with self.connect() as db:
                db.execute(
                    "INSERT OR REPLACE INTO files VALUES (?,?,?,?,?,?,?,?)",
                    (
                        str(folder),
                        key,
                        *before,
                        status,
                        json.dumps(payload, ensure_ascii=False),
                        now,
                        METHOD_VERSION,
                    ),
                )
        with self.connect() as db:
            for key in old.keys() - seen:
                if old[key]["status"] != "Removed":
                    db.execute(
                        "UPDATE files SET status='Removed',scanned=? WHERE root=? AND path=?",
                        (now, str(folder), key),
                    )
                    counts["removed"] += 1
        return {**counts, "cancelled": False}


def duplicate_groups(records: list[dict], kind: str = "sha256") -> list[dict]:
    if kind not in {"sha256", "pcm_sha256"}:
        raise ValueError("Unknown duplicate category")
    groups = defaultdict(dict)
    for record in records:
        valid = record["status"] == "Indexed" or (
            kind == "sha256" and record["status"] != "Removed"
        )
        if record.get(kind) and valid:
            groups[record[kind]][record["path"]] = record
    result = []
    for digest, by_path in groups.items():
        rows = list(by_path.values())
        if len(rows) > 1:
            sizes = [r["size"] for r in rows]
            result.append(
                {
                    "hash": digest,
                    "paths": list(by_path),
                    "count": len(rows),
                    "total_bytes": sum(sizes),
                    "redundant_bytes": sum(sizes) - min(sizes),
                }
            )
    return result


def audit_metadata(records: list[dict]) -> list[dict]:
    issues = []
    albums = defaultdict(list)
    for row in records:
        info = row.get("info")
        if not info:
            continue
        tags = info["tags"]
        for tag in ("artist", "album", "title", "track"):
            if not tags.get(tag):
                issues.append({"path": row["path"], "finding": f"Missing {tag}"})
        # Folder grouping avoids merging unrelated editions with equal titles.
        albums[(str(Path(row["path"]).parent), tags.get("album", "Unknown"))].append(row)
    for (folder, _album), rows in albums.items():
        for field in ("sample_rate", "bit_depth", "channels", "channel_layout", "codec"):
            if len({r["info"].get(field) for r in rows}) > 1:
                issues.append({"path": folder, "finding": f"Album differs: {field}"})
        for tag in ("album_artist", "albumartist", "date", "disc"):
            values = {r["info"]["tags"].get(tag) for r in rows}
            if len(values - {None, ""}) > 1:
                issues.append({"path": folder, "finding": f"Album differs: {tag}"})
        tracks = [
            r["info"]["tags"].get("disc", "1") + ":" + r["info"]["tags"].get("track", "")
            for r in rows
            if r["info"]["tags"].get("track")
        ]
        if len(tracks) != len(set(tracks)):
            issues.append({"path": folder, "finding": "Duplicate disc/track numbers"})
    return issues


def overview(records: list[dict]) -> dict:
    unique = list({r["path"]: r for r in records}.values())
    infos = [r["info"] for r in unique if r.get("info")]
    codec_bytes = defaultdict(int)
    album_bytes = defaultdict(int)
    for row in unique:
        codec_bytes[row.get("info", {}).get("codec", "Unknown")] += row["size"]
        album_bytes[str(Path(row["path"]).parent)] += row["size"]
    return {
        "files": len(unique),
        "bytes": sum(r["size"] for r in unique),
        "duration_seconds": sum(i["duration"] or 0 for i in infos),
        "albums": len({(str(Path(i["path"]).parent), i["tags"].get("album")) for i in infos}),
        "artists": len({i["tags"]["artist"] for i in infos if i["tags"].get("artist")}),
        "codecs": dict(Counter(i["codec"] for i in infos)),
        "sample_rates": dict(Counter(str(i["sample_rate"]) for i in infos)),
        "bit_depths": dict(Counter(str(i["bit_depth"]) for i in infos if i["kind"] == "PCM")),
        "dsd_files": sum(i["kind"] == "DSD" for i in infos),
        "errors": sum(r["status"] == "Unreadable/unsupported" for r in unique),
        "exact_duplicate_groups": len(duplicate_groups(unique)),
        "decoded_duplicate_groups": len(duplicate_groups(unique, "pcm_sha256")),
        "metadata_findings": len(audit_metadata(unique)),
        "storage_by_codec": dict(codec_bytes),
        "storage_by_album_folder": dict(album_bytes),
    }
