"""No shell, explicit UTF-8 diagnostics and bounded streaming binary output."""

import subprocess
import tempfile
import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from music_project.core.models import AudioError


@dataclass(frozen=True)
class CommandResult:
    stdout: bytes
    stderr: str

    @property
    def text(self) -> str:
        return self.stdout.decode("utf-8", errors="replace")


def run(
    command: Sequence[str],
    *,
    timeout: float = 300,
    max_bytes: int = 4 * 1024 * 1024,
    consume: Callable[[bytes], None] | None = None,
) -> CommandResult:
    if timeout <= 0 or max_bytes < 0:
        raise AudioError("Некорректный лимит subprocess")
    # stderr cannot block stdout: it goes to a separate disk-backed stream.
    # PCM is consumed in blocks without a whole-file RAM/disk copy.
    with tempfile.TemporaryFile() as errors:
        try:
            process = subprocess.Popen(
                list(command),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=errors,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except FileNotFoundError as exc:
            raise AudioError(f"Backend unavailable: {command[0]}") from exc
        except OSError as exc:
            raise AudioError(f"Не удалось запустить backend: {exc}") from exc
        expired = threading.Event()

        def kill_on_timeout():
            expired.set()
            try:
                process.kill()
            except OSError:
                pass

        timer = threading.Timer(timeout, kill_on_timeout)
        timer.daemon = True
        timer.start()
        data = bytearray()
        try:
            assert process.stdout is not None
            while block := process.stdout.read(1024 * 1024):
                if consume:
                    consume(block)
                else:
                    if len(data) + len(block) > max_bytes:
                        raise AudioError("Вывод backend превышает лимит; уменьшите область анализа")
                    data.extend(block)
            process.wait()
        finally:
            timer.cancel()
            if process.poll() is None:
                process.kill()
            process.wait()
            if process.stdout:
                process.stdout.close()
        if expired.is_set():
            raise AudioError(f"Превышено время ожидания ({timeout:g} с)")
        errors.seek(0, 2)
        errors.seek(max(0, errors.tell() - 65536))
        diagnostic = errors.read().decode("utf-8", errors="replace")
        if process.returncode:
            raise AudioError(f"Ошибка декодера ({process.returncode}): {diagnostic[-3000:]}")
        return CommandResult(bytes(data), diagnostic)


def backend_versions(settings) -> dict[str, str]:
    versions = {}
    for name in ("ffmpeg", "ffprobe", "fpcalc", "sacd_extract"):
        try:
            path = settings.require(name)
            if name in ("ffmpeg", "ffprobe"):
                versions[name] = run([path, "-version"], timeout=10).text.splitlines()[0]
            else:
                versions[name] = f"Available: {path}; version unverified"
        except AudioError as exc:
            versions[name] = str(exc)
    return versions
