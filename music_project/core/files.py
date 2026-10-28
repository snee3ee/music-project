import hashlib
import os
from pathlib import Path

from music_project.core.models import AudioError

AUDIO_EXTENSIONS = {
    ".flac",
    ".wav",
    ".wave",
    ".bwf",
    ".rf64",
    ".aif",
    ".aiff",
    ".aifc",
    ".m4a",
    ".alac",
    ".wv",
    ".ape",
    ".tak",
    ".tta",
    ".caf",
    ".mka",
    ".mkv",
    ".mp3",
    ".aac",
    ".opus",
    ".ogg",
    ".wma",
    ".dsf",
    ".dff",
    ".dsdiff",
    ".cue",
    ".iso",
}


def walk_files(root: Path, audio_only: bool = True):
    """Never follow directory/file links or Windows junctions."""
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise AudioError("Укажите существующую папку")

    def failed(error):
        # Aborting prevents incorrectly marking inaccessible subtrees removed.
        raise AudioError(f"Не удалось прочитать каталог: {error}")

    for parent, dirs, names in os.walk(root, followlinks=False, onerror=failed):
        dirs[:] = sorted(
            d
            for d in dirs
            if not (Path(parent) / d).is_symlink() and not (Path(parent) / d).is_junction()
        )
        for name in sorted(names):
            path = Path(parent) / name
            if path.is_symlink() or not path.is_file():
                continue
            if not audio_only or path.suffix.lower() in AUDIO_EXTENSIONS:
                yield path


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def signature(path: Path) -> tuple[int, int]:
    stat = path.stat()
    return stat.st_size, stat.st_mtime_ns
