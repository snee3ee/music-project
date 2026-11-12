"""Generated controls, actual conclusions and streaming memory/time observations.

No private recordings. Files live in ignored data/. Use --durations 20 240 for
performance observations; measurements are not a standards certification.
"""

import argparse
import json
import platform
import subprocess
import time
import tracemalloc
import wave
from dataclasses import asdict
from pathlib import Path

import numpy as np

from music_project.core.analysis import analyze
from music_project.core.conclusion_models import ReferenceProfile
from music_project.core.conclusions import build_conclusions
from music_project.core.config import Settings
from music_project.core.files import file_hash
from music_project.core.pcm import loudness
from music_project.core.probe import probe
from music_project.core.technical_analysis import measure_technical


def write_control(path, seconds, kind):
    rate = 48000
    frames = round(seconds * rate)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(3)
        output.setframerate(rate)
        for first in range(0, frames, 48000):
            indices = np.arange(first, min(first + 48000, frames))
            t = indices / rate
            if kind == "intersample":
                x = 1.1 * np.sin(2 * np.pi * 12000 * t + np.pi / 4)
                x *= np.minimum(1, indices / (0.01 * rate)) * np.minimum(
                    1, (frames - 1 - indices) / (0.01 * rate)
                )
            elif kind == "levels":
                gain = np.where(t < seconds / 2, 10 ** (-20 / 20), 10 ** (-30 / 20))
                x = gain * np.sin(2 * np.pi * 1000 * t)
            elif kind == "plateau":
                x = np.where(np.sin(2 * np.pi * 10 * t) >= 0, 0.96, -0.96)
            else:
                x = 10 ** (-23 / 20) * np.sin(2 * np.pi * 1000 * t)
            samples = np.repeat(x[:, None], 2, axis=1)
            pcm = np.rint(samples * 2**23).astype("<i4").view(np.uint8).reshape(-1, 4)[:, :3].copy()
            output.writeframesraw(pcm.tobytes())
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--durations", type=float, nargs="*", default=[20, 240])
    parser.add_argument("--output", type=Path, default=Path("data/conclusion-validation"))
    args = parser.parse_args()
    root = args.output
    root.mkdir(parents=True, exist_ok=True)
    settings = Settings(timeout=600)
    report = {"platform": platform.platform(), "cases": [], "performance": []}
    for kind, duration in [("anchor", 20), ("intersample", 4), ("levels", 40), ("plateau", 4)]:
        path = write_control(root / f"{kind}.wav", duration, kind)
        if kind == "anchor":
            flac = path.with_suffix(".flac")
            subprocess.run(
                [
                    settings.require("ffmpeg"),
                    "-v",
                    "error",
                    "-nostdin",
                    "-y",
                    "-i",
                    str(path),
                    "-c:a",
                    "flac",
                    str(flac),
                ],
                check=True,
            )
            path = flac
        before = file_hash(path)
        start = time.perf_counter()
        result, _ = analyze(path, settings)
        reference = ReferenceProfile("Explicit custom reference", -14, -1)
        conclusions = build_conclusions(result.info, result.scope, result.findings, reference)
        row = {
            "generated_fixture": kind,
            "path": str(path),
            "seconds": time.perf_counter() - start,
            "scope": result.findings["full_peaks"].measurements["scope"],
            "source_unchanged": before == file_hash(path),
            "reference": asdict(reference),
            "conclusions": [asdict(c) for c in conclusions],
            "loudness": {
                k: v
                for k, v in result.findings["loudness"].measurements.items()
                if k not in ["timeline", "short_term_distribution"]
            },
            "integrity": result.findings["pcm_integrity"].measurements,
        }
        report["cases"].append(row)
        (root / f"{kind}-analysis.json").write_text(
            json.dumps(result.to_dict(), ensure_ascii=False, indent=2, allow_nan=False),
            encoding="utf-8",
        )
        print(
            kind, "unchanged", row["source_unchanged"], "conclusions", len(conclusions), flush=True
        )
    for duration in args.durations:
        if not 0 < duration <= 3600:
            raise ValueError("Generated duration outside (0,3600]")
        path = write_control(root / f"benchmark-{duration:g}s.wav", duration, "anchor")
        info = probe(path, settings)
        tracemalloc.start()
        start = time.perf_counter()
        loudness(info, settings)
        legacy_seconds = time.perf_counter() - start
        _, legacy_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        tracemalloc.start()
        start = time.perf_counter()
        measured = measure_technical(info, settings)
        seconds = time.perf_counter() - start
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        p = measured["full_peaks"].measurements
        meter = measured["loudness"].measurements
        row = {
            "duration": duration,
            "input_mib": path.stat().st_size / 2**20,
            "legacy_loudnorm_seconds": legacy_seconds,
            "legacy_python_allocator_peak_mib": legacy_peak / 2**20,
            "new_stream_seconds_with_tracemalloc": seconds,
            "python_allocator_peak_mib": peak / 2**20,
            "retained_peak_rows": len(p["timeline"]),
            "retained_loudness_rows": len(meter["timeline"]),
            "warning": "Both paths use tracemalloc; legacy is a component, not the whole previous application. No speedup claim. Allocator peak excludes FFmpeg/RSS.",
        }
        report["performance"].append(row)
        print(row, flush=True)
    (root / "validation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8"
    )
    print("Saved", root / "validation.json", flush=True)


if __name__ == "__main__":
    main()
