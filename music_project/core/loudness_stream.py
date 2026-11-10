"""Incremental FFmpeg EBU frame metadata; complete-window extrema and bounded plots."""

import math
import re

import numpy as np


def finite(value):
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except (TypeError, ValueError):
        return None


class LoudnessMetadata:
    def __init__(self, rate):
        self.rate = rate
        self.buffer = b""
        self.current = {}
        self.time = None
        self.last = {}
        self.rows = []
        self.count = 0
        self.above_gate = 0
        self.warnings = []
        self.warning_count = 0
        self.maximum_m = None
        self.maximum_s = None
        self.minimum_s = None
        self.histogram = np.zeros(3001, dtype=np.int64)
        self.outside_histogram = 0
        self.gating = {
            "absolute_lufs": -70.0,
            "integrated_relative_lu": -10.0,
            "lra_relative_lu": -20.0,
        }
        self.section = None

    def feed(self, chunk):
        self.buffer += chunk
        if len(self.buffer) > 262144 and b"\n" not in self.buffer:
            raise ValueError("Meter diagnostic line exceeds limit")
        lines = self.buffer.split(b"\n")
        self.buffer = lines.pop()
        for raw in lines:
            self._line(raw.decode("utf-8", errors="replace").strip())

    def _line(self, line):
        if "[warning]" in line or "[error]" in line:
            self.warning_count += 1
            if len(self.warnings) < 128:
                self.warnings.append(line)
        match = re.search(r"frame:\s*\d+.*pts_time:([\d.e+\-]+)", line)
        if match:
            self._flush()
            self.time = float(match[1])
            self.current = {}
            return
        if line.startswith("lavfi.r128.") and "=" in line:
            key, value = line.split("=", 1)
            self.current[key.removeprefix("lavfi.r128.")] = finite(value)
        if "Integrated loudness:" in line:
            self.section = "integrated"
        if "Loudness range:" in line:
            self.section = "lra"
        match = re.search(r"Threshold:\s*([\d.+\-]+) LUFS", line)
        if match and self.section:
            self.gating[self.section + "_final_threshold_lufs"] = float(match[1])

    def _flush(self):
        if self.time is None or not self.current:
            return
        end = self.time + max(1, self.rate // 10) / self.rate
        m = self.current.get("M") if end >= 0.4 - 1 / self.rate else None
        s = self.current.get("S") if end >= 3 - 1 / self.rate else None
        if m is not None:
            if m >= -70:
                self.above_gate += 1
            if self.maximum_m is None or m > self.maximum_m["lufs"]:
                self.maximum_m = {"lufs": m, "start_seconds": max(0, end - 0.4), "end_seconds": end}
        if s is not None:
            if self.maximum_s is None or s > self.maximum_s["lufs"]:
                self.maximum_s = {"lufs": s, "start_seconds": max(0, end - 3), "end_seconds": end}
            if self.minimum_s is None or s < self.minimum_s["lufs"]:
                self.minimum_s = {"lufs": s, "start_seconds": max(0, end - 3), "end_seconds": end}
            index = round((s + 200) * 10)
            if 0 <= index < len(self.histogram):
                self.histogram[index] += 1
            else:
                self.outside_histogram += 1
        self.last = self.current.copy()
        self.count += 1
        self.rows.append(
            {
                "start_seconds": self.time,
                "end_seconds": end,
                "momentary_min_lufs": m,
                "momentary_max_lufs": m,
                "short_term_min_lufs": s,
                "short_term_max_lufs": s,
            }
        )
        if len(self.rows) > 2048:
            merged = []
            for i in range(0, len(self.rows) - 1, 2):
                a, b = self.rows[i : i + 2]
                row = {"start_seconds": a["start_seconds"], "end_seconds": b["end_seconds"]}
                for key in (
                    "momentary_min_lufs",
                    "momentary_max_lufs",
                    "short_term_min_lufs",
                    "short_term_max_lufs",
                ):
                    values = [v[key] for v in (a, b) if v[key] is not None]
                    row[key] = (min(values) if "min" in key else max(values)) if values else None
                merged.append(row)
            if len(self.rows) % 2:
                merged.append(self.rows[-1])
            self.rows = merged

    def finish(self):
        if self.buffer:
            self._line(self.buffer.decode("utf-8", errors="replace").strip())
            self.buffer = b""
        self._flush()
        self.current = {}
        self.time = None
        distribution = [
            {"lufs": i / 10 - 200, "count": int(n)} for i, n in enumerate(self.histogram) if n
        ]
        quantiles = {}
        n = int(self.histogram.sum())
        if n and not self.outside_histogram:
            cumulative = np.cumsum(self.histogram)
            for q in (0.1, 0.5, 0.9):
                quantiles[f"p{round(q * 100)}_lufs"] = (
                    int(np.searchsorted(cumulative, max(1, math.ceil(q * n)))) / 10 - 200
                )
        return {
            "integrated_lufs": self.last.get("I") if self.above_gate else None,
            "integrated_lufs_state": "finite"
            if self.above_gate and self.last.get("I") is not None
            else "undefined below gate or too short",
            "lra_lu": self.last.get("LRA") if self.maximum_s and self.above_gate else None,
            "maximum_momentary": self.maximum_m,
            "maximum_short_term": self.maximum_s,
            "minimum_short_term": self.minimum_s,
            "short_term_distribution": distribution,
            "short_term_quantiles": quantiles,
            "distribution_resolution_lu": 0.1,
            "distribution_rule": "all finite complete3s windows; ungated, not the gated LRA distribution",
            "distribution_out_of_range": self.outside_histogram,
            "metadata_frames": self.count,
            "gating": self.gating,
            "timeline": self.rows,
            "timeline_method": "100ms metadata; >2048 points merge adjacent min/max envelopes; no invented interpolated measurements",
            "warnings": self.warnings,
            "warning_events": self.warning_count,
            "metadata_precision_lu": 0.001,
        }
