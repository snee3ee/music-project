from pathlib import Path

from music_project.core.config import Settings
from music_project.core.decoder import PCMContext
from music_project.core.models import Analysis, AudioError, Finding
from music_project.core.pcm import loudness, peaks, quantization, spectral_findings
from music_project.core.probe import probe
from music_project.core.subprocess_utils import backend_versions


def analyze(
    path: Path | str, settings: Settings = Settings()
) -> tuple[Analysis, PCMContext | None]:
    info = probe(path, settings)
    versions = backend_versions(settings)
    if info.kind == "DSD":
        finding = Finding(
            "Not applicable",
            "Native DSD: PCM-тесты не запускались.",
            {
                "native_rate_hz": info.sample_rate,
                "dsd_family": f"DSD{info.sample_rate // 44100}"
                if info.sample_rate in (2822400, 5644800, 11289600, 22579200)
                else "Unknown",
            },
            "ffprobe DSD metadata; packed-byte rate ×8 for dsd_* codecs.",
            ["DSD-to-PCM измерения и DST native rate ещё не валидированы."],
        )
        return Analysis(info, {"strategy": "metadata only"}, {"dsd": finding}, versions), None
    context = PCMContext.load(info, settings)
    cutoff, upsampling = spectral_findings(context)
    findings = {
        "peaks": peaks(context),
        "lossy_history": cutoff,
        "upsampling": upsampling,
        "quantization": quantization(context),
    }
    try:
        findings["loudness"] = loudness(info, settings)
    except AudioError as exc:
        findings["loudness"] = Finding("Unknown", str(exc))
    return Analysis(info, context.scope, findings, versions), context
