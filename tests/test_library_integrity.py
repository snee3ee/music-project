import copy
import shutil

import pytest

from music_project.core.integrity import create_manifest, verify_manifest
from music_project.core.library import Library, audit_metadata, duplicate_groups, overview
from music_project.core.models import AudioError


def test_recursive_incremental_duplicates_and_removed(tone, tmp_path, encode, settings):
    root = tmp_path / "collection"
    root.mkdir()
    nested = root / "Album"
    nested.mkdir()
    source = nested / tone.name
    shutil.copyfile(tone, source)
    exact = nested / "exact.wav"
    shutil.copyfile(tone, exact)
    flac = encode(
        source,
        root / "tagged.flac",
        "-metadata",
        "album=Тест",
        "-metadata",
        "track=1",
        "-metadata",
        "title=Один",
        "-metadata",
        "artist=Автор",
    )
    (root / "broken.flac").write_bytes(b"broken")
    library = Library(tmp_path / "index.sqlite3")
    progress = []
    first = library.scan(root, settings, progress=lambda n, p: progress.append(n))
    assert first["new"] == 4 and first["errors"] == 1
    assert progress == [1, 2, 3, 4]
    rows = library.records()
    assert len(duplicate_groups(rows)) == 1
    assert duplicate_groups(rows)[0]["redundant_bytes"] == tone.stat().st_size
    assert duplicate_groups(rows, "pcm_sha256")[0]["count"] == 3
    assert overview(rows)["errors"] == 1
    assert audit_metadata(rows)
    assert library.scan(root, settings)["unchanged"] == 4
    with exact.open("ab") as stream:
        stream.write(b"changed")
    flac.unlink()  # Generated temporary fixture, never user audio.
    change = library.scan(root, settings)
    assert change["modified"] == 1 and change["removed"] == 1
    assert len(library.records()) == 3
    assert len(library.records(include_removed=True)) == 4
    assert Library(tmp_path / "index.sqlite3").records() == library.records()


def test_cancellation_does_not_remove_records(tone, tmp_path, settings):
    root = tmp_path / "audio"
    root.mkdir()
    shutil.copyfile(tone, root / "one.wav")
    lib = Library(tmp_path / "index.sqlite3")
    lib.scan(root, settings)
    assert lib.scan(root, settings, cancelled=lambda: True)["cancelled"]
    assert len(lib.records()) == 1


def test_manifest_transfer_and_changes(tmp_path):
    original, transferred = tmp_path / "old", tmp_path / "new"
    original.mkdir()
    (original / "unchanged.txt").write_text("same", encoding="utf-8")
    (original / "missing.txt").write_text("remove", encoding="utf-8")
    (original / "modified.txt").write_text("initial", encoding="utf-8")
    (original / "mismatch.txt").write_text("abc", encoding="utf-8")
    manifest = create_manifest(original)
    shutil.copytree(original, transferred)
    assert all(r["status"] == "Unchanged" for r in verify_manifest(transferred, manifest))
    (transferred / "missing.txt").unlink()
    (transferred / "modified.txt").write_text("longer now", encoding="utf-8")
    (transferred / "mismatch.txt").write_text("xyz", encoding="utf-8")
    (transferred / "new.txt").write_text("new", encoding="utf-8")
    assert {r["status"] for r in verify_manifest(transferred, manifest)} == {
        "Unchanged",
        "Missing",
        "Modified",
        "Hash mismatch",
        "New",
    }
    assert (original / "mismatch.txt").read_text() == "abc"


@pytest.mark.parametrize(
    "path",
    [
        "../outside.wav",
        "C:/private.wav",
        "\\\\server\\file",
        "/outside.wav",
        "folder/../../outside",
        "file:stream",
        "",
    ],
)
def test_manifest_rejects_unsafe_paths(tmp_path, path):
    manifest = {
        "schema": "music-project-sha256-v1",
        "files": [{"path": path, "size": 1, "sha256": "0" * 64}],
    }
    with pytest.raises(AudioError):
        verify_manifest(tmp_path, manifest)


def test_manifest_duplicate_and_invalid_hash(tmp_path):
    (tmp_path / "file").write_bytes(b"x")
    manifest = create_manifest(tmp_path)
    invalid = copy.deepcopy(manifest)
    invalid["files"][0]["sha256"] = "invalid"
    with pytest.raises(AudioError):
        verify_manifest(tmp_path, invalid)
    manifest["files"] *= 2
    with pytest.raises(AudioError):
        verify_manifest(tmp_path, manifest)


def test_album_consistency():
    def row(name, rate):
        return {
            "path": f"album/{name}",
            "info": {
                "sample_rate": rate,
                "channels": 2,
                "bit_depth": 24,
                "codec": "flac",
                "channel_layout": "stereo",
                "tags": {"album": "A", "artist": "X", "title": name, "track": "1"},
            },
        }

    issues = audit_metadata([row("a.flac", 48000), row("b.flac", 96000)])
    assert any("sample_rate" in r["finding"] for r in issues)
    assert any("Duplicate" in r["finding"] for r in issues)
