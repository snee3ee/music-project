"""Reproducible controls and optional read-only real-file performance validation.

Run with .venv/Scripts/python.exe tools/validate_origin.py [--real test_audio/file.dsf].
Generated fixtures are temporary. Output is numerical evidence, not historical truth.
"""

import argparse
import json
import math
import struct
import tempfile
import time
import tracemalloc
from dataclasses import replace
from pathlib import Path

import numpy as np
from scipy.signal import butter, resample_poly, sosfilt

from music_project.core.analysis import analyze
from music_project.core.config import Settings
from music_project.core.dsd import diagnose_dsd
from music_project.core.files import file_hash
from music_project.core.origin_reference import reference_prefix
from music_project.core.probe import probe
from music_project.core.subprocess_utils import backend_versions


def write_pdm(path, pcm, source_rate, native_rate=2822400, dither=False):
    """Known first-order accumulator, no claim to emulate commercial modulators."""
    divisor = math.gcd(source_rate, native_rate)
    x = resample_poly(pcm, native_rate // divisor, source_rate // divisor, window=("kaiser", 8.6))
    count = len(x)
    payload = math.ceil(count / 32768) * 4096
    rng = np.random.default_rng(834)
    with path.open("wb") as out:
        out.write(b"DSD " + struct.pack("<QQQ", 28, 92 + payload, 0))
        out.write(
            b"fmt " + struct.pack("<QIIIIIIQII", 52, 1, 0, 1, 1, native_rate, 1, count, 4096, 0)
        )
        out.write(b"data" + struct.pack("<Q", 12 + payload))
        carry = previous = 0.0
        written = 0
        for first in range(0, count, 65536):
            values = x[first : first + 65536]
            if dither:
                values = values + rng.uniform(-0.002, 0.002, len(values))
            if np.max(abs(values)) >= 1:
                raise ValueError("Generated modulator input overload")
            cumulative = np.cumsum((values + 1) / 2) + carry
            floors = np.floor(cumulative)
            bits = np.diff(np.r_[previous, floors]).astype(np.uint8)
            encoded = np.packbits(bits, bitorder="little").tobytes()
            out.write(encoded)
            written += len(encoded)
            carry, previous = float(cumulative[-1]), float(floors[-1])
        out.write(b"\x69" * (payload - written))
    return path


def measured(path, settings):
    tracemalloc.start()
    start = time.perf_counter()
    result, _ = analyze(path, settings)
    elapsed = time.perf_counter() - start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    origin = result.findings["origin_investigation"]
    report = origin.measurements
    return result, {
        "seconds": elapsed,
        "python_allocator_peak_mib": peak / 2**20,
        "memory_scope": "Python/NumPy allocator only; excludes FFmpeg and is not RSS",
        "duration": result.info.duration,
        "duration_status": result.info.duration_status,
        "decoded_seconds": result.scope.get("decoded_seconds"),
        "integrity": result.findings.get("dsd_integrity").status,
        "origin_status": origin.status,
        "discoveries": report.get("discoveries", []),
        "converted_noise_range_hz": report.get("noise", {}).get("range_hz"),
        "converted_noise_channels": report.get("noise", {}).get("channels", []),
        "native_noise_channels": report.get("native", {}).get("noise", {}).get("channels", []),
        "boundaries": [
            {
                "candidate_hz": b["candidate_hz"],
                "channel_stability": b["channel_stability"],
                "global_attenuation_db": [c["attenuation_db"] for c in b["channels"]],
                "chain_usable": b["converted_chain_usable"],
                "compatibility_evidence": b["historical_compatibility_evidence"],
            }
            for b in report.get("boundaries", [])
        ],
        "hypotheses": [
            {"code": h["code"], "status": h["status"]} for h in report.get("hypotheses", [])
        ],
        "temporal_measured": report.get("scope", {}).get("temporal", {}).get("measured_cells"),
        "temporal_retained": report.get("scope", {}).get("temporal", {}).get("retained_cells"),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--real", type=Path)
    parser.add_argument("--output", default="data/origin-validation.json")
    args = parser.parse_args()
    settings = Settings(timeout=600, dsd_mode="full")
    report = {
        "backends": backend_versions(settings),
        "controls": [],
        "real": {},
        "control_limitations": "First-order generated modulator and Kaiser polyphase resampling; not all professional production chains. No historical rate classifier is validated.",
    }
    with tempfile.TemporaryDirectory(prefix="origin-known-chains-") as directory:
        folder = Path(directory)
        first_dsd = None
        for source_rate, style in [
            (44100, "pcm"),
            (48000, "pcm"),
            (96000, "pcm"),
            (352800, "pcm"),
            (352800, "analog-like filter"),
            (48000, "input dither"),
        ]:
            rng = np.random.default_rng(789 + source_rate)
            pcm = rng.normal(0, 0.05, round(source_rate * 2.2))
            if style == "analog-like filter":
                pcm = sosfilt(butter(12, 23000, fs=source_rate, output="sos"), pcm)
            path = write_pdm(
                folder / f"generated-{source_rate}-{len(report['controls'])}.dsf",
                pcm,
                source_rate,
                dither=style == "input dither",
            )
            if first_dsd is None:
                first_dsd = path
            _, row = measured(path, settings)
            row.update(
                chain=f"{source_rate} Hz {style} -> scipy resample_poly Kaiser8.6 -> first-order pulse density DSD64",
                seed=789 + source_rate,
            )
            report["controls"].append(row)
            print(row["chain"], row["origin_status"], round(row["seconds"], 3), flush=True)
        prefix, _ = reference_prefix(probe(first_dsd, settings), settings, seconds=2.2, rate=352800)
        cascaded = write_pdm(folder / "cascaded.dsf", prefix.samples[:, 0], 352800, 5644800)
        _, row = measured(cascaded, settings)
        row["chain"] = (
            "44.1k PCM -> DSD64 -> FFmpeg 352800 float32 -> first-order pulse density DSD128"
        )
        report["controls"].append(row)
    if args.real:
        before = file_hash(args.real)
        info = probe(args.real, settings)
        # Same container/decoder/PSD engine without new collection/native investigation.
        for mode in ("quick", "full"):
            selected = replace(settings, dsd_mode=mode)
            tracemalloc.start()
            start = time.perf_counter()
            diagnose_dsd(info, selected)
            baseline = time.perf_counter() - start
            _, baseline_peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            result, row = measured(args.real, selected)
            row["dsd_core_without_origin_seconds"] = baseline
            row["dsd_core_without_origin_allocator_peak_mib"] = baseline_peak / 2**20
            report["real"][mode] = row
            Path(f"data/origin-real-{mode}.json").write_text(
                json.dumps(result.to_dict(), ensure_ascii=False, allow_nan=False), encoding="utf-8"
            )
            print("real", mode, round(baseline, 3), round(row["seconds"], 3), flush=True)
        report["real"]["sha256_before"] = before
        report["real"]["sha256_after"] = file_hash(args.real)
        report["real"]["source_unchanged"] = before == report["real"]["sha256_after"]
    Path(args.output).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8"
    )
    print("Saved", args.output, flush=True)


if __name__ == "__main__":
    main()
