"""Small reproducible local synthetic scan benchmark; never reads a music collection."""

import json
import tempfile
import time
import wave
from pathlib import Path

import numpy as np

from music_project.core.library import Library

project = Path(__file__).resolve().parents[1]
data = project / "data"
data.mkdir(exist_ok=True)
rng = np.random.default_rng(20261028)
pcm = rng.integers(-20000, 20000, 48000 * 3, dtype=np.int16).astype("<i2").tobytes()
with tempfile.TemporaryDirectory(prefix="synthetic-benchmark-", dir=data) as temporary:
    root = Path(temporary) / "audio"
    root.mkdir()
    for index in range(32):
        with wave.open(str(root / f"synthetic-{index:02d}.wav"), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(48000)
            output.writeframes(pcm)
    library = Library(Path(temporary) / "benchmark.sqlite3")
    start = time.perf_counter()
    initial = library.scan(root)
    initial_seconds = time.perf_counter() - start
    start = time.perf_counter()
    incremental = library.scan(root)
    incremental_seconds = time.perf_counter() - start
    report = {
        "fixture": "32 generated mono WAV, 48 kHz 16 bit, 3 s each, identical bytes",
        "initial_scan_seconds": initial_seconds,
        "incremental_scan_seconds": incremental_seconds,
        "initial_result": initial,
        "incremental_result": incremental,
        "limits": "Small warm-filesystem synthetic workload; not a large-library benchmark.",
    }
    (data / "benchmark.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
