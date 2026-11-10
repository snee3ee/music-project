"""No shell, explicit UTF-8 diagnostics and bounded streaming binary output."""

import subprocess
import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from music_project.core.models import AudioError, DecoderError


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
    cancelled: Callable[[], bool] | None = None,
    consume_stderr: Callable[[bytes], None] | None = None,
) -> CommandResult:
    if timeout <= 0 or max_bytes < 0:
        raise AudioError("Некорректный лимит subprocess")
    try:
        process = subprocess.Popen(
            list(command),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except FileNotFoundError as exc:
        raise AudioError(f"Backend unavailable: {command[0]}") from exc
    except OSError as exc:
        raise AudioError(f"Не удалось запустить backend: {exc}") from exc
    expired = threading.Event()
    stopped = threading.Event()
    done = threading.Event()
    diagnostics = bytearray()
    stderr_errors = []

    def drain_errors():
        assert process.stderr is not None
        while chunk := process.stderr.read(8192):
            if consume_stderr and not stderr_errors:
                try:
                    consume_stderr(chunk)
                except Exception as exc:
                    stderr_errors.append(exc)
                    try:
                        process.kill()
                    except OSError:
                        pass
            diagnostics.extend(chunk)
            if len(diagnostics) > 65536:
                del diagnostics[:-65536]

    reader = threading.Thread(target=drain_errors, daemon=True)
    reader.start()

    def check_cancellation():
        while not done.wait(0.1):
            if cancelled and cancelled():
                stopped.set()
                try:
                    process.kill()
                except OSError:
                    pass
                return

    watcher = threading.Thread(target=check_cancellation, daemon=True) if cancelled else None
    if watcher:
        watcher.start()

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
        done.set()
        timer.cancel()
        if process.poll() is None:
            process.kill()
        process.wait()
        if process.stdout:
            process.stdout.close()
        reader.join()
        if process.stderr:
            process.stderr.close()
        if watcher:
            watcher.join()
    if expired.is_set():
        raise AudioError(f"Превышено время ожидания ({timeout:g} с)")
    if stopped.is_set():
        raise AudioError("Cancelled: декодирование остановлено")
    diagnostic = diagnostics.decode("utf-8", errors="replace")
    if stderr_errors:
        raise AudioError(
            f"Некорректные потоковые измерения: {stderr_errors[0]}"
        ) from stderr_errors[0]
    if process.returncode:
        raise DecoderError(
            f"Ошибка декодера ({process.returncode}): {diagnostic[-3000:]}", diagnostic
        )
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
