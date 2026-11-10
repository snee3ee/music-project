"""Bounded PCM observations: exact rails, runs, extrema, RMS and time envelopes."""

import numpy as np

from music_project.core.pcm import db
from music_project.core.true_peak import TP_RATES, TruePeak


class Runs:
    def __init__(self, rate, near, *, flat=False):
        self.rate, self.near, self.flat = rate, near, flat
        self.previous = None
        self.start = self.length = self.frames = self.count = self.total_frames = 0
        self.longest = None
        self.events = []

    def _record(self, values, starts, lengths):
        keep = (lengths >= (3 if self.flat else 1)) & (abs(values) >= self.near)
        ids = np.flatnonzero(keep)
        self.count += len(ids)
        self.total_frames += int(lengths[ids].sum())
        if not len(ids):
            return
        max_id = ids[np.argmax(lengths[ids])]

        def event(i):
            return {
                "start_seconds": float(starts[i] / self.rate),
                "end_seconds": float((starts[i] + lengths[i]) / self.rate),
                "frames": int(lengths[i]),
                "sample_value" if self.flat else "rail_sign_code": float(values[i]),
            }

        if self.longest is None or lengths[max_id] > self.longest["frames"]:
            self.longest = event(max_id)
        self.events.extend(event(i) for i in ids[: max(0, 128 - len(self.events))])

    def consume(self, x):
        starts = np.r_[0, np.flatnonzero(x[1:] != x[:-1]) + 1]
        lengths = np.diff(np.r_[starts, len(x)])
        values = x[starts]
        absolute_starts = starts + self.frames
        if self.length:
            if x[0] == self.previous:
                absolute_starts[0] = self.start
                lengths[0] += self.length
            else:
                self._record(
                    np.array([self.previous]), np.array([self.start]), np.array([self.length])
                )
        self._record(values[:-1], absolute_starts[:-1], lengths[:-1])
        self.previous = float(values[-1])
        self.start = int(absolute_starts[-1])
        self.length = int(lengths[-1])
        self.frames += len(x)

    def finish(self):
        if self.length:
            self._record(np.array([self.previous]), np.array([self.start]), np.array([self.length]))
            self.length = 0
        return {
            "count": self.count,
            "frames_in_runs": self.total_frames,
            "longest": self.longest,
            "events": self.events,
            "retention": "first128 qualifying events; total count and longest cover all samples",
            "rule": "exact equal samples, at least3, absolute level >= selected threshold"
            if self.flat
            else "consecutive samples at the same positive or negative digital rail",
        }


class PeakMeasurements:
    def __init__(self, rate, channels, bits, near_dbfs=-1.0):
        self.rate, self.channels = rate, channels
        self.near_dbfs = near_dbfs
        self.near = 10 ** (near_dbfs / 20)
        self.positive = 1 - 2.0 ** (1 - bits) if bits in (8, 16, 24, 32) else 1.0
        self.peak = np.zeros(channels)
        self.peak_frames = np.zeros(channels, dtype=np.int64)
        self.positive_peak = np.zeros(channels)
        self.negative_peak = np.zeros(channels)
        self.squares = np.zeros(channels)
        self.full = np.zeros(channels, dtype=np.int64)
        self.near_count = np.zeros(channels, dtype=np.int64)
        self.frames = self.zero_frames = self.above_one = 0
        self.rails = [Runs(rate, 1) for _ in range(channels)]
        self.flats = [Runs(rate, self.near, flat=True) for _ in range(channels)]
        self.tp = TruePeak(rate, channels) if rate in TP_RATES else None
        self.bin_frames = max(1, round(rate * 0.1))
        self.bin_count = 0
        self.bin_peak = np.zeros(channels)
        self.bin_squares = np.zeros(channels)
        self.rows = []
        self.timeline_frames = 0

    def _flush_bin(self):
        if not self.bin_count:
            return
        end = self.timeline_frames + self.bin_count
        self.timeline_frames = end
        self.rows.append(
            {
                "start_seconds": (end - self.bin_count) / self.rate,
                "end_seconds": end / self.rate,
                "frames": self.bin_count,
                "peak_linear": self.bin_peak.tolist(),
                "sum_squares": self.bin_squares.tolist(),
            }
        )
        if len(self.rows) > 2048:
            merged = []
            for i in range(0, len(self.rows) - 1, 2):
                a, b = self.rows[i : i + 2]
                merged.append(
                    {
                        "start_seconds": a["start_seconds"],
                        "end_seconds": b["end_seconds"],
                        "frames": a["frames"] + b["frames"],
                        "peak_linear": np.maximum(a["peak_linear"], b["peak_linear"]).tolist(),
                        "sum_squares": (np.array(a["sum_squares"]) + b["sum_squares"]).tolist(),
                    }
                )
            if len(self.rows) % 2:
                merged.append(self.rows[-1])
            self.rows = merged
        self.bin_peak.fill(0)
        self.bin_squares.fill(0)
        self.bin_count = 0

    def consume(self, x):
        a = abs(x)
        squares = x * x
        if not np.isfinite(squares).all():
            raise ValueError("PCM energy overflow")
        for ch in range(self.channels):
            i = int(np.argmax(a[:, ch]))
            value = float(a[i, ch])
            if value > self.peak[ch]:
                self.peak[ch] = value
                self.peak_frames[ch] = self.frames + i
            labels = np.where(x[:, ch] >= self.positive, 1, np.where(x[:, ch] <= -1, -1, 0))
            self.rails[ch].consume(labels)
            self.flats[ch].consume(x[:, ch])
        self.positive_peak = np.maximum(self.positive_peak, np.max(x, axis=0))
        self.negative_peak = np.maximum(self.negative_peak, -np.min(x, axis=0))
        self.squares += squares.sum(axis=0)
        self.full += np.sum((x >= self.positive) | (x <= -1), axis=0)
        self.near_count += np.sum(a >= self.near, axis=0)
        self.zero_frames += int(np.sum(np.all(x == 0, axis=1)))
        self.above_one += int(np.sum(a > 1))
        if self.tp:
            self.tp.consume(x)
        first = 0
        while first < len(x):
            take = min(self.bin_frames - self.bin_count, len(x) - first)
            self.bin_peak = np.maximum(self.bin_peak, np.max(a[first : first + take], axis=0))
            self.bin_squares += squares[first : first + take].sum(axis=0)
            self.bin_count += take
            first += take
            if self.bin_count == self.bin_frames:
                self._flush_bin()
        self.frames += len(x)

    def finish(self):
        self._flush_bin()
        if not self.frames:
            raise ValueError("No PCM frames measured")
        rms = np.sqrt(self.squares / self.frames)
        pooled = float(np.sqrt(self.squares.sum() / (self.frames * self.channels)))
        result = {
            "sample_peak_dbfs": db(float(max(self.peak))),
            "sample_peak_per_channel_dbfs": [db(p) for p in self.peak],
            "sample_peak_time_seconds": (self.peak_frames / self.rate).tolist(),
            "rms_dbfs": db(pooled),
            "rms_per_channel_dbfs": [db(r) for r in rms],
            "crest_factor_db": db(float(max(self.peak)) / pooled) if pooled else None,
            "full_scale_samples_per_channel": self.full.tolist(),
            "positive_rail": self.positive,
            "negative_rail": -1.0,
            "near_ceiling_dbfs": self.near_dbfs,
            "near_ceiling_samples_per_channel": self.near_count.tolist(),
            "near_ceiling_density_per_channel": (self.near_count / self.frames).tolist(),
            "rail_runs": [r.finish() for r in self.rails],
            "possible_flat_top_runs": [r.finish() for r in self.flats],
            "positive_peak_linear": self.positive_peak.tolist(),
            "negative_peak_magnitude": self.negative_peak.tolist(),
            "exact_zero_frames": self.zero_frames,
            "exact_zero_seconds": self.zero_frames / self.rate,
            "samples_above_1": self.above_one,
            "timeline": self.rows,
            "timeline_method": "100ms native-frame bins; merged bins retain maximum peak and exact summed energy, at most2048 rows",
            "frames": self.frames,
        }
        if self.tp:
            tp = self.tp.finish()
            peaks = np.maximum(tp["peak_linear_per_channel"], self.peak)
            times = [
                tp["time_seconds_per_channel"][ch]
                if tp["peak_linear_per_channel"][ch] > self.peak[ch]
                else self.peak_frames[ch] / self.rate
                for ch in range(self.channels)
            ]
            result["true_peak"] = tp | {
                "peak_linear_per_channel": peaks.tolist(),
                "time_seconds_per_channel": times,
                "true_peak_dbtp": db(float(max(peaks))),
                "true_peak_per_channel_dbtp": [db(float(p)) for p in peaks],
                "state": "finite" if max(peaks) > 0 else "negative infinity",
            }
        else:
            result["true_peak"] = {
                "status": "Not validated",
                "reason": "Native sample rate outside tested True Peak configurations",
            }
        return result
