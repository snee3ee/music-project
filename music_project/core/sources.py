"""Analyze logical sources through the existing PCM/DSD engine, with safe cleanup."""

import hashlib
import json
import tempfile
from dataclasses import replace
from pathlib import Path

from music_project.core.config import Settings
from music_project.core.models import AudioError, Finding
from music_project.core.probe import probe
from music_project.core.source_extract import prepare_cue_track
from music_project.core.source_models import AudioSource


def analyze_source(source: AudioSource, settings=Settings(), *, progress=None, cancelled=None):
    from music_project.core.analysis import analyze
    from music_project.core.conclusions import build_conclusions

    source.verify()
    original_info = probe(source.audio_path, settings) if source.kind == "cue" else None
    with tempfile.TemporaryDirectory(prefix="music-project-track-") as temporary:
        folder = Path(temporary)
        if source.kind == "cue":
            path, extraction = prepare_cue_track(
                source, original_info, folder, settings, cancelled=cancelled
            )
        elif source.kind == "sacd":
            from music_project.core.sacd import extract_track

            path, extraction = extract_track(source, folder, settings, cancelled=cancelled)
        else:
            raise AudioError("Unsupported logical source")
        source.verify()
        result, context = analyze(path, settings, progress=progress, cancelled=cancelled)
        actual = result.info.duration
        tolerance = max(1 / 75 if source.kind == "sacd" else 0, 1 / (result.info.sample_rate or 1))
        if actual is None or abs(actual - source.duration_seconds) > tolerance + 1e-8:
            raise AudioError(
                f"Selected-track duration mismatch: expected {source.duration_seconds}, obtained {actual}"
            )
        start_seconds = (
            extraction["first_native_frame"] / original_info.sample_rate
            if source.kind == "cue"
            else source.start_75 / 75
        )
        mapping = {
            "source_identity": hashlib.sha256(
                json.dumps(source.to_dict(), sort_keys=True).encode()
            ).hexdigest(),
            "time_origin": "selected track; t=0 at selected track audio start",
            "source_start_seconds": start_seconds,
            "source_end_seconds": start_seconds + actual,
            "declared_start_seconds": source.start_75 / 75,
            "source_time_grid_seconds": 1 / original_info.sample_rate if original_info else 1 / 75,
            "mapping_rule": "source_seconds = track_seconds + source_start_seconds",
            "complete_file_means": "Complete selected track, not complete CUE album/ISO/source file",
        }
        for finding in result.findings.values():
            for key in ("scope", "integrated_scope", "true_peak_scope"):
                if isinstance(finding.measurements.get(key), dict):
                    finding.measurements[key] = {**finding.measurements[key], **mapping}
        result.scope.update(mapping)
        evidence = {
            **source.to_dict(),
            **mapping,
            "extraction": extraction,
            "temporary_container": result.info.container,
            "temporary_codec": result.info.codec,
            "native_rate_hz": result.info.sample_rate,
            "original_audio": {
                "container": original_info.container,
                "codec": original_info.codec,
                "duration": original_info.duration,
            }
            if original_info
            else None,
            "cleanup": "Temporary selected-track representation removed before returning result",
        }
        result.findings["logical_source"] = Finding(
            "Derived",
            "Измерена выбранная дорожка; временные метки отсчитываются от её начала.",
            evidence,
            method_version=source.method_version,
        )
        if source.kind == "cue" and "pcm_integrity" in result.findings:
            result.findings["pcm_integrity"].measurements["source_verification"] = (
                "Selected track only; original source FLAC digest/container not independently checked"
            )
        result.info = replace(
            result.info,
            path=source.audio_path,
            container=original_info.container if original_info else "SACD ISO",
            codec=original_info.codec if original_info else result.info.codec,
            size=Path(source.audio_path).stat().st_size,
            tags={**result.info.tags, "title": source.title, "artist": source.performer},
            raw={**result.info.raw, "logical_source": evidence},
        )
        if context is not None:
            context.info = result.info
        result.conclusions = build_conclusions(result.info, result.scope, result.findings)
        source.verify()
    return result, context
