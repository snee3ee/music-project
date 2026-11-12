from collections.abc import Callable
from pathlib import Path

from music_project.core.conclusions import build_conclusions
from music_project.core.config import Settings
from music_project.core.decoder import PCMContext
from music_project.core.dsd import diagnose_dsd
from music_project.core.duration import DurationSelection, with_duration
from music_project.core.files import signature
from music_project.core.lossy import investigate_context, unavailable
from music_project.core.models import Analysis, AudioError, Finding
from music_project.core.origin import investigate_origin, investigate_pcm_context, origin_finding
from music_project.core.origin_calibration import calibrate_response, controlled_bandwidth
from music_project.core.origin_models import ORIGIN_VERSION
from music_project.core.origin_temporal import OriginCollector
from music_project.core.pcm import peaks, quantization, spectral_findings
from music_project.core.probe import probe
from music_project.core.subprocess_utils import backend_versions
from music_project.core.technical_analysis import measure_technical


def analyze(
    path: Path | str,
    settings: Settings = Settings(),
    *,
    progress: Callable[[float], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> tuple[Analysis, PCMContext | None]:
    source = Path(path).resolve(strict=True)
    before = signature(source)
    try:
        info = probe(source, settings)
    except AudioError as exc:
        raise AudioError(f"Контейнер/метаданные (ffprobe): проверка не выполнена. {exc}") from exc
    versions = backend_versions(settings)
    if info.kind == "DSD":
        try:
            profile = calibrate_response(
                info.sample_rate, settings, versions.get("ffmpeg", "Unknown"), cancelled=cancelled
            )
        except (AudioError, ValueError, OSError) as exc:
            profile = {"status": "Unsupported", "reason": str(exc)}
        collector = (
            OriginCollector(
                settings.dsd_pcm_rate, info.channels, maximum_noise_hz=controlled_bandwidth(profile)
            )
            if settings.dsd_pcm_rate in (176400, 352800) and info.channels in (1, 2)
            else None
        )
        findings, scope = diagnose_dsd(
            info, settings, progress=progress, cancelled=cancelled, origin_collector=collector
        )
        findings["lossy_source"] = unavailable(
            "PCM-only lossy investigation; native DSD is not converted for this test"
        )
        info = with_duration(info, DurationSelection(**scope["duration"]))
        try:
            report = investigate_origin(
                info,
                findings,
                scope,
                collector.result() if collector else {},
                settings,
                versions,
                cancelled=cancelled,
                measured_profile=profile,
            )
            findings["origin_investigation"] = origin_finding(report)
            findings["dsd_evidence"].measurements.update(
                classifier="No historical identity classifier; compatibility hypotheses in origin_investigation",
                experimental_origin_detection=f"Executed: {report.status}; see origin_investigation ({ORIGIN_VERSION})",
            )
            findings["dsd_conversion"].measurements.update(
                response_profile_status=report.measurement_chain["status"],
                highest_consecutive_passing_control_hz=controlled_bandwidth(
                    report.measurement_chain
                ),
                effective_native_dsd_bandwidth="Unknown; discrete response controls do not certify continuous native bandwidth",
            )
        except (AudioError, ValueError, OSError) as exc:
            findings["origin_investigation"] = Finding(
                "Unknown", str(exc), method_version=ORIGIN_VERSION
            )
        if before != signature(source):
            raise AudioError("Файл изменился во время анализа; повторите проверку")
        result = Analysis(info, scope, findings, versions)
        result.conclusions = build_conclusions(info, scope, findings)
        return result, None
    context = PCMContext.load(info, settings)
    cutoff, upsampling = spectral_findings(context)
    findings = {
        "peaks": peaks(context),
        "lossy_history": cutoff,
        "upsampling": upsampling,
        "quantization": quantization(context),
    }
    try:
        findings.update(measure_technical(info, settings, progress=progress, cancelled=cancelled))
    except (AudioError, ValueError, OSError) as exc:
        findings["loudness"] = Finding("Unknown", str(exc))
        findings["lossy_source"] = investigate_context(
            context, reason="Technical pass unavailable: " + str(exc)
        )
        status = (
            "Unsupported"
            if "Backend unavailable" in str(exc) or "Unsupported" in str(exc)
            else "Partial"
            if "Cancelled" in str(exc) or "время ожидания" in str(exc)
            else "Failed"
        )
        findings["pcm_integrity"] = Finding(
            status,
            str(exc),
            {
                "complete_file": False,
                "warnings_retained": False,
                "reason": str(exc),
                "fatal_error": str(exc) if status == "Failed" else None,
            },
        )
    try:
        findings["origin_investigation"] = investigate_pcm_context(context, settings, versions)
    except (AudioError, ValueError, OSError) as exc:
        findings["origin_investigation"] = Finding(
            "Unknown", str(exc), method_version=ORIGIN_VERSION
        )
    if before != signature(source):
        raise AudioError("Файл изменился во время анализа; повторите проверку")
    result = Analysis(info, context.scope, findings, versions)
    result.conclusions = build_conclusions(info, context.scope, findings)
    return result, context
