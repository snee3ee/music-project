from pathlib import Path

from music_project.core.config import Settings
from music_project.core.decoder import PCMContext
from music_project.core.models import Analysis, AudioError, Finding, Observation
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
            "Measured" if info.sample_rate else "Unknown",
            "Прочитаны метаданные Native DSD. PCM-проверки к этому сигналу не применяются.",
            {
                "native_rate_hz": info.sample_rate,
                "dsd_family": f"DSD{info.sample_rate // 44100}"
                if info.sample_rate in (2822400, 5644800, 11289600, 22579200)
                else "Unknown",
            },
            "Метаданные ffprobe: packed-byte rate ×8 для dsd_* Codecs.",
            ["DSD-to-PCM измерения и DST native rate ещё не валидированы."],
            observations=[
                Observation(
                    "DSD_RATE",
                    "Measured" if info.sample_rate else "Insufficient data",
                    f"Native DSD rate: {info.sample_rate / 1_000_000:g} MHz."
                    if info.sample_rate
                    else "Native DSD rate: этот DST-вариант пока не проверен; значение не предполагается.",
                    info.sample_rate or None,
                    "Hz",
                )
            ],
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
