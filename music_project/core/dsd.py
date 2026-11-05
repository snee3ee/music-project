"""DSD diagnostics orchestration; measurable evidence, without an origin classifier."""

from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path

from music_project.core.config import Settings
from music_project.core.dsd_container import inspect_dsd
from music_project.core.dsd_decoder import PCM_RATES, convert_window, quick_windows
from music_project.core.dsd_spectrum import StreamingWelch
from music_project.core.duration import ffprobe_duration, select_dsd_duration
from music_project.core.files import signature
from music_project.core.models import AudioError, AudioInfo, Finding

DSD_METHOD_VERSION = "dsd-2026.11-v2"
DERIVED = "Derived from DSD-to-PCM conversion."
LIMITS = [
    DERIVED,
    "Контрольные частоты конвертера исследуются отдельно в Origin Investigator; его статус и область указаны в отчёте.",
    "Эта группа содержит PCM-derived спектр; независимый native DSD PSD находится в Origin Investigator, если выполнен.",
    "Ultrasonic energy может содержать noise shaping; это не показатель fidelity или музыкальной информации.",
    "Декодирование и спектр не устанавливают историческое происхождение записи.",
]


def _finding(
    status: str,
    summary: str,
    measurements: dict | None = None,
    method: str = "",
    limitations: list[str] | None = None,
) -> Finding:
    return Finding(
        status,
        summary,
        measurements or {},
        method,
        limitations or [],
        method_version=DSD_METHOD_VERSION,
    )


def diagnose_dsd(
    info: AudioInfo,
    settings: Settings = Settings(),
    *,
    progress: Callable[[float], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
    origin_collector=None,
) -> tuple[dict[str, Finding], dict]:
    before = signature(Path(info.path))
    structure = inspect_dsd(info)
    nominal = info.sample_rate * info.channels if info.sample_rate and info.channels else None
    findings = {
        "dsd": _finding(
            "Measured" if info.sample_rate else "Unknown",
            "Метаданные Native DSD.",
            {
                "native_rate_hz": info.sample_rate or None,
                "dsd_family": f"DSD{info.sample_rate // 44100}"
                if info.sample_rate in (2822400, 5644800, 11289600, 22579200)
                else "Unknown",
                "nominal_native_bitrate_bps": nominal,
                "container_bitrate_bps": info.bitrate,
                "ffprobe_duration_seconds": ffprobe_duration(info),
                "dst_processing": "Unsupported"
                if structure.compression == "DST" or info.codec == "dst"
                else "Not applicable"
                if structure.compression == "DSD"
                else "Unknown",
            },
            "Native nominal bitrate = однобитная частота × число каналов; без overhead/сжатия.",
        ),
        "dsd_container": _finding(
            structure.status,
            "Проверка структуры контейнера; без декодирования аудио.",
            asdict(structure) | {"expected_duration_seconds": structure.duration},
            "Read-only DSF/DFF chunk bounds, sample count, channel consistency.",
        ),
    }
    scope = {
        "strategy": settings.dsd_mode,
        "complete_file": False,
        "domain": DERIVED,
        "method_version": DSD_METHOD_VERSION,
        "expected_duration_seconds": structure.duration,
        "ranges": [],
        "decoded_seconds": 0.0,
    }
    attempts = []
    spectrum = None
    status = "Unknown"
    reason = "Декодирование не выполнено."
    reached_eof = False
    if structure.status != "Passed":
        status = "Unsupported" if structure.status == "Unsupported" else "Unknown"
        reason = "Декодирование не выполнялось: см. отдельный результат контейнерной проверки."
    elif settings.dsd_mode not in {"quick", "full"} or settings.dsd_pcm_rate not in PCM_RATES:
        status, reason = "Unsupported", "Неизвестный режим DSD."
    elif info.channels not in (1, 2) or info.channel_layout not in {"mono", "stereo"}:
        status, reason = (
            "Unsupported",
            "Преобразование валидируется только для известного mono/stereo layout.",
        )
    else:
        spectral = StreamingWelch(
            settings.dsd_pcm_rate,
            info.channels,
            segment_consumer=origin_collector.consume if origin_collector else None,
        )
        windows = (
            [(0.0, None)] if settings.dsd_mode == "full" else quick_windows(structure.duration)
        )
        completed = 0.0
        planned = structure.duration if settings.dsd_mode == "full" else sum(d for _, d in windows)
        for start, duration in windows:
            if origin_collector:
                origin_collector.start_window(start)
            if cancelled and cancelled():
                status, reason = "Partial", "Анализ отменён; оставшиеся интервалы не проверены."
                break

            def report(seconds, completed=completed):
                if progress and planned:
                    progress(min(0.999, (completed + seconds) / planned))

            attempt = convert_window(
                info,
                settings,
                start,
                duration,
                spectral.consume,
                progress=report,
                cancelled=cancelled,
            )
            attempts.append(asdict(attempt))
            decoded = attempt.frames / settings.dsd_pcm_rate
            completed += decoded
            scope["ranges"].append(
                {
                    "start_seconds": start,
                    "requested_seconds": duration,
                    "decoded_seconds": decoded,
                    "status": attempt.status,
                }
            )
            spectral.end_window()
            if origin_collector:
                origin_collector.end_window()
            status = attempt.status
            if settings.dsd_mode == "full" and status == "Passed":
                reached_eof = True
            if status != "Passed":
                reason = "Декодирование остановлено; см. fatal_error для интервала."
                break
            expected = structure.duration if duration is None else duration
            tolerance = 2 / settings.dsd_pcm_rate
            upper_tolerance = tolerance + (
                structure.padding_tolerance_seconds if duration is None else 0
            )
            if decoded < expected - tolerance or decoded > expected + upper_tolerance:
                status, reason = "Failed", "Декодированная длительность вне допустимых границ."
                attempts[-1]["status"] = "Failed"
                attempts[-1]["fatal_error"] = reason
                scope["ranges"][-1]["status"] = "Failed"
                break
        else:
            if settings.dsd_mode == "full":
                status, reason = (
                    "Passed",
                    "Весь аудиопоток декодирован до EOF; длительность согласована.",
                )
                scope["complete_file"] = True
            else:
                status, reason = (
                    "Partial",
                    "Выбранные интервалы декодированы; весь поток не проверялся.",
                )
        scope["decoded_seconds"] = completed
        spectrum = spectral.result()
        if progress:
            progress(
                1.0
                if scope["complete_file"]
                or status == "Partial"
                and attempts
                and all(a["status"] == "Passed" for a in attempts)
                else min(0.999, completed / planned)
            )
    selection = select_dsd_duration(
        info,
        structure,
        decoded_seconds=scope["decoded_seconds"] if attempts else None,
        full_decode_reached_eof=reached_eof,
        decode_status=status,
        pcm_rate=settings.dsd_pcm_rate,
    )
    scope["duration"] = asdict(selection)
    findings["dsd_duration"] = _finding(
        selection.status,
        "Длительность аудио подтверждена полным декодированием."
        if selection.status == "Verified"
        else "Длительность рассчитана по структуре контейнера; полный поток не подтверждён."
        if selection.status == "Derived"
        else "Надёжная длительность аудио не установлена.",
        asdict(selection),
        "DSF: sample count / native rate. Uncompressed DFF: payload bytes ×8 / channels / native rate. "
        "Полный decode проверяется в пределах двух PCM frames и точно вычисленного DSF padding.",
        [
            "ffprobe duration — вторичная оценка; ID3/artwork и block padding не являются действительными аудиоотсчётами."
        ],
    )
    findings["dsd_integrity"] = _finding(
        status,
        reason,
        {
            "attempts": attempts,
            "expected_duration_seconds": structure.duration,
            "successfully_decoded_seconds": scope["decoded_seconds"],
            "duration_difference_seconds": scope["decoded_seconds"] - structure.duration
            if scope["complete_file"]
            else None,
            "dsf_padding_tolerance_seconds": structure.padding_tolerance_seconds,
            "complete_file": scope["complete_file"],
            "failed_segments": [a for a in attempts if a["status"] != "Passed"],
        },
        "Strict FFmpeg decoding (-xerror -err_detect explode); converted frames counted after output-header validation.",
        [
            "DSD payload has no universal checksum; readable arbitrary bits need not be meaningful audio.",
            "Полная проверка не устанавливает историческую аутентичность; Quick не подтверждает полный файл.",
        ],
    )
    conversion_status = (
        "Measured" if attempts and all(a["status"] == "Passed" for a in attempts) else status
    )
    findings["dsd_conversion"] = _finding(
        conversion_status,
        DERIVED,
        {
            "requested_pcm_rate_hz": settings.dsd_pcm_rate,
            "output_headers": [a["output_header"] for a in attempts],
            "commands": [a["command"] for a in attempts],
            "validation_status": "Output rate/channels verified"
            if attempts and all(a["output_header"] for a in attempts)
            else "Not validated",
            "effective_native_dsd_bandwidth": "Unknown; conversion response Not validated",
        },
        "FFmpeg DSD decoder → explicit libswresample → IEEE float32 WAV pipe; no downmix.",
        LIMITS,
    )
    measured = spectrum is not None and spectrum["status"] == "Measured"
    for key, audible in (("dsd_audible", True), ("dsd_ultrasonic", False)):
        bands = (
            [b for b in spectrum["bands"] if (b["high_hz"] <= 20000) == audible] if measured else []
        )
        findings[key] = _finding(
            "Measured" if measured else "Unknown" if spectrum else status,
            DERIVED + (" Усреднённая PSD и энергия полос." if measured else " Спектр недоступен."),
            {"bands": bands, "spectrum": spectrum} if audible else {"bands": bands},
            "Welch: periodic Hann, N=16384, overlap=8192, no detrend, one-sided density; independent channels.",
            LIMITS,
        )
    findings["dsd_evidence"] = _finding(
        "Ambiguous" if measured else "Unknown",
        "Историческая цепочка PCM/DSD/analog/DXD не установлена.",
        {
            "origin": "Unknown",
            "classifier": "Not implemented: no validated origin rule",
            "native_bit_depth_tests": "Not applicable",
            "experimental_origin_detection": "Not implemented",
        },
        limitations=LIMITS,
    )
    if before != signature(Path(info.path)):
        raise AudioError("Файл изменился во время DSD-анализа; повторите проверку")
    return findings, scope
