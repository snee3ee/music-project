"""Reproducible generated DSD benchmark; no user audio or external dependencies.

Windows RSS is sampled for Python plus spawned backends (5 ms, not an exact peak).
tracemalloc is the Python/NumPy allocator peak and excludes FFmpeg. No speedup claim.
"""

import argparse
import ctypes
import json
import os
import struct
import subprocess
import tempfile
import threading
import time
import tracemalloc
from ctypes import wintypes
from pathlib import Path
from unittest.mock import patch

from music_project.core.config import Settings
from music_project.core.subprocess_utils import backend_versions
from music_project.ui.shared import cached_analysis, clear_analysis_cache


class Counters(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
        (name, ctypes.c_size_t)
        for name in (
            "PeakWorkingSetSize",
            "WorkingSetSize",
            "QuotaPeakPagedPoolUsage",
            "QuotaPagedPoolUsage",
            "QuotaPeakNonPagedPoolUsage",
            "QuotaNonPagedPoolUsage",
            "PagefileUsage",
            "PeakPagefileUsage",
        )
    ]


def working_set(process):
    if os.name != "nt":
        return None

    handle = process._handle if process else ctypes.windll.kernel32.GetCurrentProcess()
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    get_info = ctypes.windll.psapi.GetProcessMemoryInfo
    get_info.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    if get_info(handle, ctypes.byref(counters), counters.cb):
        return counters.WorkingSetSize
    return None


def make_dsf(path, seconds, rate=11289600):
    block, channels = 4096, 2
    samples = int(seconds * rate)
    blocks = (samples + block * 8 - 1) // (block * 8)
    payload = blocks * block * channels
    with path.open("wb") as output:
        output.write(b"DSD " + struct.pack("<QQQ", 28, 92 + payload, 0))
        output.write(
            b"fmt " + struct.pack("<QIIIIIIQII", 52, 1, 0, 2, channels, rate, 1, samples, block, 0)
        )
        output.write(b"data" + struct.pack("<Q", 12 + payload))
        for _ in range(blocks):
            output.write(b"\x69" * (block * channels))


def measure(path, mode):
    settings = Settings(timeout=600, dsd_mode=mode)
    stat = path.stat()
    processes = []
    original = subprocess.Popen

    def counted(*args, **kwargs):
        process = original(*args, **kwargs)
        processes.append((process, args[0]))
        return process

    done = threading.Event()
    rss = [working_set(None) or 0]

    def sample():
        while not done.wait(0.005):
            parent = working_set(None) or 0
            children = sum(working_set(p) or 0 for p, _ in list(processes) if p.poll() is None)
            rss[0] = max(rss[0], parent + children)

    sampler = threading.Thread(target=sample, daemon=True)
    sampler.start()
    tracemalloc.start()
    start = time.perf_counter()
    with patch("subprocess.Popen", counted):
        result, _ = cached_analysis(str(path), stat.st_size, stat.st_mtime_ns, settings)
    seconds = time.perf_counter() - start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    done.set()
    sampler.join()
    attempts = result.findings["dsd_integrity"].measurements["attempts"]
    return {
        "mode": mode,
        "seconds": seconds,
        "python_allocator_peak_mib": peak / 2**20,
        "sampled_python_plus_children_rss_peak_mib": max(rss) / 2**20 if os.name == "nt" else None,
        "subprocess_invocations": len(processes),
        "decode_invocations": sum("-i" in command for _, command in processes),
        "successful_decode_seconds": result.scope["decoded_seconds"],
        "files_per_second": 1 / seconds,
        "integrity_status": result.findings["dsd_integrity"].status,
        "complete_file": result.scope["complete_file"],
        "fft_segments": result.findings["dsd_audible"].measurements["spectrum"]["segments"],
        "warnings": [warning for a in attempts for warning in a["warnings"]],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", nargs="+", type=float, default=[20, 240])
    parser.add_argument("--output", default="data/dsd-benchmark.json")
    parser.add_argument(
        "--rate", type=int, default=11289600, choices=[2822400, 5644800, 11289600, 22579200]
    )
    args = parser.parse_args()
    if any(not 0 < seconds <= 3600 for seconds in args.seconds):
        parser.error("generated durations must be in (0, 3600]")
    report = {
        "fixture": f"generated {args.rate} Hz DSD stereo repeated 0x69, 352800 Hz PCM analysis",
        "rss_method": "5 ms sampled sum of Python and active backend working sets; warm filesystem",
        "backends": backend_versions(Settings()),
        "cases": [],
    }
    for seconds in args.seconds:
        with tempfile.TemporaryDirectory(prefix="generated-dsd-benchmark-") as temporary:
            path = Path(temporary) / "generated.dsf"
            make_dsf(path, seconds, args.rate)
            clear_analysis_cache()
            case = {"duration_seconds": seconds, "file_mib": path.stat().st_size / 2**20}
            case["quick"] = measure(path, "quick")
            case["quick_cached"] = measure(path, "quick")
            case["full"] = measure(path, "full")
            report["cases"].append(case)
            print(json.dumps(case, ensure_ascii=True), flush=True)
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")


if __name__ == "__main__":
    main()
