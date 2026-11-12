"""Opt-in actual local DSD full analyses; no uploads or backend installation."""

import argparse
import json
import time
from dataclasses import asdict
from pathlib import Path

from music_project import METHOD_VERSION, __version__
from music_project.core.analysis import analyze
from music_project.core.config import Settings
from music_project.core.files import file_hash, signature


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("audio", type=Path, help="Explicitly authorized local DSF/DFF")
    parser.add_argument(
        "--rates", type=int, choices=[176400, 352800], nargs="+", default=[176400, 352800]
    )
    parser.add_argument("--output", type=Path, default=Path("data/v1-validation/dsd"))
    args = parser.parse_args()
    audio = args.audio.resolve(strict=True)
    args.output.mkdir(parents=True, exist_ok=True)
    before = {"signature": signature(audio), "sha256": file_hash(audio)}
    report = {
        "app_version": __version__,
        "method_version": METHOD_VERSION,
        "source": str(audio),
        "analyses": [],
    }
    for rate in dict.fromkeys(args.rates):
        start = time.perf_counter()
        result, _ = analyze(audio, Settings(timeout=600, dsd_mode="full", dsd_pcm_rate=rate))
        if result.info.kind != "DSD":
            raise ValueError("This validator requires actual DSD, not a renamed PCM file")
        row = {
            "pcm_rate_hz": rate,
            "seconds": time.perf_counter() - start,
            "audio_info": asdict(result.info),
            "container": asdict(result.findings["dsd_container"]),
            "integrity": asdict(result.findings["dsd_integrity"]),
            "duration": result.scope["duration"],
            "origin_historical_source": result.findings.get(
                "origin_investigation"
            ).measurements.get("historical_source"),
            "backends": result.backends,
        }
        report["analyses"].append(row)
        (args.output / f"analysis-{rate}.json").write_text(
            json.dumps(result.to_dict(), ensure_ascii=False, allow_nan=False, indent=2),
            encoding="utf-8",
        )
        print(
            rate,
            row["integrity"]["status"],
            result.info.duration,
            f"{row['seconds']:.3f}s",
            flush=True,
        )
    report["source_preservation"] = {
        **before,
        "sha256_after": file_hash(audio),
        "signature_after": signature(audio),
    }
    report["source_preservation"].update(
        sha256_unchanged=before["sha256"] == report["source_preservation"]["sha256_after"],
        stat_unchanged=before["signature"] == report["source_preservation"]["signature_after"],
    )
    (args.output / "real-validation.json").write_text(
        json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2), encoding="utf-8"
    )
    print(
        "Source SHA-256/stat unchanged:",
        report["source_preservation"]["sha256_unchanged"],
        report["source_preservation"]["stat_unchanged"],
        flush=True,
    )
    if any(row["integrity"]["status"] != "Passed" for row in report["analyses"]) or not all(
        report["source_preservation"][key] for key in ("sha256_unchanged", "stat_unchanged")
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
