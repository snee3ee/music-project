"""Opt-in real local CUE/ISO validation. Writes reports, never copies recordings.

Paths must be explicitly supplied by the owner. No uploads or backend installation.
"""

import argparse
import json
import time
from pathlib import Path

from music_project import METHOD_VERSION, __version__
from music_project.core.config import Settings
from music_project.core.cue import open_cue, track_source
from music_project.core.files import file_hash, signature
from music_project.core.sacd import open_sacd
from music_project.core.sources import analyze_source


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cue", type=Path)
    parser.add_argument("--iso", type=Path)
    parser.add_argument("--cue-track", type=int, choices=range(1, 100), default=4)
    parser.add_argument("--iso-track", type=int, choices=range(1, 256), default=4)
    parser.add_argument("--output", type=Path, default=Path("data/cue-sacd-validation"))
    args = parser.parse_args()
    if not args.cue and not args.iso:
        parser.error("Supply an explicitly authorized --cue or --iso path")
    settings = Settings(timeout=600, dsd_mode="full")
    out = args.output
    out.mkdir(exist_ok=True, parents=True)
    report = {
        "app_version": __version__,
        "method_version": METHOD_VERSION,
        "catalogs": {},
        "analysis": [],
    }
    paths = set()
    if args.cue:
        c = open_cue(args.cue, settings)
        report["catalogs"]["cue"] = c
        paths.add(args.cue)
        paths.update(Path(f["path"]) for f in c["files"] if f.get("exists"))
    if args.iso:
        report["catalogs"]["sacd"] = open_sacd(args.iso, settings)
        paths.add(args.iso)
    before = {
        str(p): {"size": p.stat().st_size, "signature": signature(p), "sha256": file_hash(p)}
        for p in paths
    }
    selections = []
    if args.cue:
        tracks = report["catalogs"]["cue"]["tracks"]
        chosen = next((t for t in tracks if t["number"] == args.cue_track), None)
        if chosen is None:
            parser.error("Requested CUE track number is absent")
        selections.append(("cue", chosen))
    if args.iso:
        selections.append(
            (
                "sacd",
                next(
                    t
                    for a in report["catalogs"]["sacd"]["areas"]
                    if a["kind"] == "stereo"
                    for t in a["tracks"]
                    if t["number"] == args.iso_track
                ),
            )
        )
    for kind, t in selections:
        source = track_source(t)
        start = time.perf_counter()
        r, ctx = analyze_source(source, settings)
        row = {
            "kind": kind,
            "track": source.track,
            "title": source.title,
            "seconds": time.perf_counter() - start,
            "duration_seconds": r.info.duration,
            "decode_status": r.findings["dsd_integrity"].status,
            "conclusion_count": len(r.conclusions),
            "logical_source": r.findings["logical_source"].measurements,
        }
        report["analysis"].append(row)
        (out / f"{kind}-track-{source.track}-analysis.json").write_text(
            json.dumps(r.to_dict(), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8"
        )
        print(
            kind,
            source.track,
            r.info.duration,
            row["decode_status"],
            f"{row['seconds']:.3f}s",
            flush=True,
        )
    report["source_preservation"] = [
        {
            "file": Path(p).name,
            **v,
            "sha256_after": file_hash(Path(p)),
            "stat_unchanged": tuple(v["signature"]) == signature(Path(p)),
        }
        for p, v in before.items()
    ]
    for r in report["source_preservation"]:
        r["sha256_unchanged"] = r["sha256"] == r["sha256_after"]
    (out / "real-validation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8"
    )
    print(
        "Source preservation",
        [
            (r["file"], r["sha256_unchanged"], r["stat_unchanged"])
            for r in report["source_preservation"]
        ],
        flush=True,
    )


if __name__ == "__main__":
    main()
