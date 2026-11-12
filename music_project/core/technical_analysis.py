"""One full streaming decode for PCM metering, sample observations and FLAC MD5."""

import math

from music_project.core.conclusion_models import TECHNICAL_VERSION, MeasurementScope
from music_project.core.decoder import input_args
from music_project.core.dsd_decoder import FloatWaveStream
from music_project.core.flac_integrity import FlacMD5
from music_project.core.lossy import LossyCollector
from music_project.core.loudness_stream import LoudnessMetadata
from music_project.core.models import AudioError, Finding
from music_project.core.peak_measurements import PeakMeasurements
from music_project.core.subprocess_utils import run

LAYOUT_MASKS = {"mono": 4, "stereo": 3, "5.1": 63, "5.1(side)": 1551, "5.0": 55, "5.0(side)": 1543}


def measure_technical(info, settings, *, progress=None, cancelled=None):
    if info.kind == "DSD":
        raise AudioError("Native DSD is not applicable to this PCM measurement pipeline")
    if info.channel_layout not in LAYOUT_MASKS:
        raise AudioError("Unsupported full metering: channel order not validated")
    if (
        settings.technical_mode not in {"full", "prefix"}
        or not math.isfinite(settings.near_ceiling_dbfs)
        or not -60 <= settings.near_ceiling_dbfs <= 0
        or settings.technical_mode == "prefix"
        and (not math.isfinite(settings.analysis_seconds) or settings.analysis_seconds <= 0)
    ):
        raise AudioError("Invalid technical measurement scope/near-ceiling threshold")
    samples = PeakMeasurements(
        info.sample_rate, info.channels, info.bit_depth, settings.near_ceiling_dbfs
    )
    metadata = LoudnessMetadata(info.sample_rate)
    md5 = FlacMD5(info)
    investigation = LossyCollector(
        info,
        min(settings.analysis_seconds, info.duration)
        if settings.technical_mode == "prefix" and info.duration is not None
        else settings.analysis_seconds
        if settings.technical_mode == "prefix"
        else None,
    )

    def consume(x):
        samples.consume(x)
        md5.consume(x)
        investigation.consume(x)
        if progress and info.duration:
            progress(min(0.99, samples.frames / info.sample_rate / info.duration))

    parser = FloatWaveStream(
        info.sample_rate,
        info.channels,
        consume,
        bits=64,
        expected_mask=LAYOUT_MASKS[info.channel_layout],
    )
    command = input_args(info, settings)
    command[command.index("error")] = "level+info"
    meter_filter = (
        "ebur128=metadata=1:peak=none:framelog=verbose,ametadata=mode=print:file='pipe\\:2'"
    )
    if settings.technical_mode == "prefix":
        command += ["-t", str(settings.analysis_seconds)]
        # Output -t alone runs filters on extra decoded input before trimming WAV.
        # Trim before the meter so metadata and native sample observations share scope.
        frame_limit = round(settings.analysis_seconds * info.sample_rate)
        meter_filter = f"atrim=end_sample={frame_limit}," + meter_filter
    command += [
        "-af",
        meter_filter,
        "-ar",
        str(info.sample_rate),
        "-ac",
        str(info.channels),
        "-channel_layout",
        info.channel_layout,
        "-c:a",
        "pcm_f64le",
        "-f",
        "wav",
        "pipe:1",
    ]
    run(
        command,
        timeout=settings.timeout,
        consume=parser.feed,
        consume_stderr=metadata.feed,
        cancelled=cancelled,
    )
    parser.finish()
    levels = samples.finish()
    meter = metadata.finish()
    complete = settings.technical_mode == "full"
    scope = MeasurementScope(
        0,
        parser.frames / info.sample_rate,
        parser.frames / info.sample_rate,
        info.duration,
        complete,
        parser.frames,
        info.sample_rate,
        info.channels,
    ).to_dict()
    levels["scope"] = scope
    levels["output_header"] = parser.header
    tp = levels["true_peak"]
    meter.update(
        scope=scope,
        integrated_scope=scope,
        true_peak_scope=scope,
        true_peak_dbtp=tp.get("true_peak_dbtp"),
        true_peak_state=tp.get("state", "undefined"),
        true_peak_above_0_dbtp=tp.get("true_peak_dbtp") > 0
        if tp.get("true_peak_dbtp") is not None
        else False
        if tp.get("state") == "negative infinity"
        else None,
        true_peak_method=tp,
        command=command,
        backend_meter="FFmpeg ebur128; native-rate output; independent reconstructed-peak estimator",
    )
    meter["validation_status"] = (
        "Generated controls documented; full ITU/EBU certification not asserted"
    )
    integrity = {
        "scope": scope,
        "complete_file": complete,
        "decoded_seconds": scope["analyzed_seconds"],
        "warnings": meter["warnings"],
        "warning_events": meter["warning_events"],
        "command": command,
        "flac_md5": md5.result(complete),
        "container_status": "Not independently checked",
        "decode_status": "Passed" if complete else "Partial",
        "warning_retention": "first128 warning/error lines; total events counted while streaming",
    }
    return {
        "lossy_source": investigation.finish(complete_decode=complete),
        "full_peaks": Finding(
            "Measured",
            "Пики, RMS и события измерены в указанной области.",
            levels,
            method_version=TECHNICAL_VERSION,
        ),
        "loudness": Finding(
            "Measured" if meter["metadata_frames"] or tp.get("state") else "Unknown",
            "Громкость измерена по указанной области; True Peak — реконструированная оценка.",
            meter,
            method_version=TECHNICAL_VERSION,
        ),
        "pcm_integrity": Finding(
            "Failed"
            if integrity["flac_md5"]["status"] == "Failed"
            else "Passed"
            if complete
            else "Partial",
            "Поток полностью декодирован." if complete else "Декодирован выбранный фрагмент.",
            integrity,
            method_version=TECHNICAL_VERSION,
        ),
    }
